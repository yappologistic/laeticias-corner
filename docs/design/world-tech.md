# World tech: contracts and architecture for the one continuous world

Technical design for growing the game from one 40×40 corner into one continuous world of
**1280 × 448 tiles** holding the home region, Rome (AD 126), Athens (432 BC), Pārsa (c. 470 BC) and
the land and sea between them. It turns `cities/world.md`, the three city files, `living-world.md`
and `living-corner.md` into formats, file locations, lanes and an ordered task list. Where those
documents disagree or ask for something too expensive, this file decides and says so (§4.0).

Contents: 1 art contract for regions · 2 world data model · 3 world authoring pipeline (worldgen) ·
4 engine architecture · 5 work plan · 6 contract changes.

Conventions used throughout:

- **Grid** coordinates `(tx, ty)` are the engine's (`+x` down-right, `+y` down-left).
  **Plan** coordinates `(C, R)` are the city files' (north up). The mapping is fixed by
  `world.md` §3.2: `tx = R`, `ty = 1279 − C`. So `+x` = south, `+y` = west, `−x` = north,
  `−y` = east. Every format in this file stores **grid** coordinates; worldgen converts plan
  coordinates once, at authoring time.
- Pixel sizes are given at the catalog tile of 64 × 32 and scale with `tile.w / 64`. Nothing in a
  tool or the engine may hard-code them; they derive from `tile` in `assets/catalog.json`.

---

## 1. Art contract for regions

Everything here can be produced now, before the engine reads it. The engine work that consumes it
is in §4; until then the art tool's own preview (and worldgen's, §3.6) is how art is checked.

### 1.1 Sets, namespaces and ids

Art and content are grouped in **sets**. A set is a kit family that shares a palette, a look and
an atlas: one per historical moment, plus the shared set and the existing home set.

| Set | Contents | Regions and stretches that draw from it (plus `world`) |
|---|---|---|
| `home` | today's corner art (`assets/catalog.json`, `assets/atlas.png`), unchanged | `corner` |
| `world` | everything used by more than one moment: sea, coast, rivers, sand, rock, snow, steppe, generic stairs and ramps, cliff edges, backdrops, generic animals (sheep, goat, dog, ox, donkey, mule, horse, camel), birds, fish, dolphins, goods, the generic walker rig's shared kinds (traveller, shepherd, farmer, child), weather and effects | all |
| `rome` | Rome, Italy, the Tyrrhenian and Adriatic coasts, Roman waypoints (Tibur, Alban Mount, Capua, Beneventum, Brundisium, Ostia/Portus) | `rome`, `latium_italy`, `apennines`, `tyrrhenian`, `adriatic`, west half of `ionian_sea` |
| `athens` | Athens, mainland Greece, the Aegean, Ionian coast to Ephesus (Corcyra, Delphi, Olympia, Sparta, Corinth, Eleusis, the Academy, Delos, Ephesus, Thrace) | `athens`, `greece`, `arcadia`, `attica_north`, `saronic`, `aegean`, `thrace`, east half of `ionian_sea`, coast of `ionia_lydia` |
| `parsa` | Pārsa and every Persian-time place east of the Sardis seam (Sardis, Gordion, Halys, Euphrates crossing, Babylon, Susa, Persian Gates, Pasargadae, Sidon) | `parsa`, Lydia, `anatolia`, `taurus`, `east_med`, `mesopotamia`, `susiana`, `syrian_steppe`, `persian_gulf`, `zagros`, `iran_plateau` |

**Id rule.** Every id outside the home set is `<set>.<name>`: `parsa.apadana`, `athens.g_house`,
`rome.r_insula`, `world.sea`, `world.sheep`. `<name>` is `[a-z0-9_]+` and unique within its set.
Home ids keep their bare names (`oak`, `cottage`), so `assets/catalog.json`, the atlas and saves do
not change. The dot cannot appear in a home id, so ids never collide, and the set of any id is the
text before its first dot.

The city files' ids map by prefixing their set: `apadana` → `parsa.apadana`, `p_house` →
`parsa.p_house`, `t_cypress` (Pārsa) → `parsa.t_cypress`, `g_house` → `athens.g_house`,
`t_olive` (Athens) → `athens.t_olive`, `p_reeds` (Rome) → `rome.p_reeds`. A thing two city files
both list (cypress, plane, vine, reeds, olive) stays per set when the files describe different
looks, and moves to `world` only when one model serves all (reeds, plane, poplar: `world.t_reeds`,
`world.t_plane`, `world.t_poplar`). The set catalog (§1.12) is where that choice is written down.

Ids also apply to terrain (`parsa.paving_stone`), actor kinds (`parsa.usher`), goods
(`world.goods_bread`… see §1.9), audio is unaffected (paths, not ids).

### 1.2 Atlas pages

```
assets/atlas.png, assets/atlas.json      home set, unchanged (it stays the corner's page)
assets/atlas/<set>.<n>.png               page n (0, 1, …) of a set, RGBA8
assets/atlas/<set>.<n>.json              that page's manifest: today's schema exactly
assets/atlas/<set>.geom.json             per-item and per-actor geometry the art tool emits (§1.10)
```

- **Manifest schema** is unchanged: `{"version": 1, "image": "<set>.<n>.png", "sprites": {…}}`
  with `x, y, w, h, ox, oy` per key. A key appears on exactly one page across all sets; the engine
  loads a set's pages and treats them as one key space (the `Sprite` already carries its texture).
- **Page size:** at most **4096 × 4096**. Pages are packed full before a new one starts; the last
  page of a set is cut to the smallest height that is a multiple of 256. 4096 is the largest size
  every renderer the game uses supports (the software renderer and desktop GL both exceed it).
- **What goes on which page** (the packer's job, so draw calls stay low):
  1. `base` sprites of kit, plants, actors and goods first (page 0), then landmark `base` pieces
     grouped by district so neighbouring landmarks share a page;
  2. `shadow` and `glow` sprites last, on their own page(s) where possible: those layers are drawn
     in separate passes, so keeping them apart from `base` means no page switching inside a pass.
- **Budget per set at 64 × 32** (estimates from the city asset tables; §2.8 has the totals):
  `world` ≤ 1 page, `parsa` ≤ 2, `athens` ≤ 2, `rome` ≤ 3. A set that would need more must cut
  nice-to-have landmarks or lower their `scale`, not add pages.
- Generators stay deterministic: the same catalog and models give byte-identical pages.

### 1.3 Large landmarks: pieces

A footprint over 8 tiles on a side, or any footprint that walkers enter, is split into **pieces**.
A piece is a rectangle of whole tiles of the footprint, rendered as its own sprite and depth-sorted
by the engine like an ordinary item with that rectangle as its footprint. This is the whole trick
that lets figures walk between columns, under porticoes and behind stairways with the engine's
existing rectangle depth sort.

**How the art tool makes pieces (exact, no seams):** render the whole model once (so shading,
occlusion and cast shadows see the whole building), keep a per-pixel record of which footprint tile
the front-most voxel stands on, and give each pixel to the piece containing that tile. Pieces
partition the rendered pixels, so the atlas cost of a split landmark equals that of the unsplit
sprite plus trimming slack, and drawing the pieces in depth order reproduces the full image exactly.

**Where to split (the rule):**

1. Walkers may enter only **walk tiles**, declared by the model (§1.10). A walk tile holds **no
   geometry lower than the headroom** (48 px at 64 × 32 = `1.5 × tile.h`) above its floor.
   Columns, walls, piers and statues stand on non-walk tiles. The floor of a walk tile is ground
   terrain (paving), never part of the landmark, so walkers are always drawn over it.
2. Walk tiles form pieces of their own: single tiles, or straight runs of up to 8 walk tiles along
   one axis (1 × n). Such a piece is only "roof above you": the engine draws it after any actor
   standing on its tiles.
3. Non-walk tiles are grouped into rectangles of at most 8 × 8 (greedy: largest rectangle first,
   then row-major), never mixing walk and non-walk tiles.
4. Footprints of 8 × 8 or less with no walk tiles are not split.
5. The art tool's validator rejects a model with voxels below the headroom on a walk tile, or a
   walk tile not reachable from the footprint's edge through other walk tiles or stairs.

Consequences the modeller designs for: a colonnade puts each column on its own tile with walk tiles
between (one column per tile along a front is exactly `world.md` §2's scale); a gate's passage is a
1 × n walk run; a stair is its own item (§1.6), so walkers climb it and pass behind its parapets.

**Layers of a split landmark:** `base` is split into pieces. `shadow` and `glow` are **not**
split: shadows are composited as one ground layer and glows are drawn additively after grading,
so neither takes part in the depth sort. A glow is pre-occluded by the building (only visible
emissive pixels are kept).

### 1.4 Rotations

- **Kit** (`layout: "rotate"`): all four `r0..r3`, as today. Worldgen places kit in any rotation.
- **Landmarks** are modelled **in grid axes**: model `+x` is south, `+y` is west, up is up, so a
  landmark in its true compass orientation is always `r0` under the fixed camera. The catalog gives
  `"rotations": [0]` and only `r0` is rendered. A landmark reused at several orientations (a
  standard temple, a milestone, a relay station) is kit instead.
- **Variant** layouts and terrain are unaffected by rotation.
- **Ready for a later 90° view rotation** (out for the first version, §4.11): models must already be
  complete on all four sides (the hidden north and east faces modelled, not skipped), use no
  camera-specific cheats (no painted-on fake depth, no faces omitted because unseen), and keep
  emitters, slots, walk tiles and pieces derivable per rotation (they are: the tool computes them
  from the model for any `r<k>`). Turning it on later means rendering `r1..r3` for landmarks (about
  3 × the landmark atlas area), re-cutting pieces per rotation and nothing else in art.

### 1.5 Layers

Unchanged from `CLAUDE.md`: `base` (lit for neutral daylight, sun from the upper left), `shadow`
(ground only, black with alpha, optional), `glow` (emissive pixels only, alpha = halo strength).
The catalog lists which layers an item has: `"layers": ["base", "shadow", "glow"]` (default
`["base", "shadow"]`, and `glow` implied by today's `"glow": true`). Item states from
`living-world.md` §2.3 (`open`, `closed`, `unlit`, …) are extra layer names drawn instead of `base`:
`item/<id>/<state>/<variant>/f<n>`; the state `lit` needs no sprite (it gates `glow`).

### 1.6 Elevation in art

- **Level height = 16 px** at 64 × 32 (`tile.h / 2`), stated as `tile.level` in the catalog
  (§6). Tile levels are integers 0..15 (sea is 0).
- **Ground at a level** is the same terrain sprite drawn `level × 16` px higher; nothing new.
- **Faces:** `edge/<material>_<se|sw>/v<n>`: one level (16 px) of vertical face hanging under a
  tile's `+x` (`se`) or `+y` (`sw`) edge, `v0..v3` variants chosen by position hash, stacked by the
  engine for higher drops. Size 32 × 32 (half a tile wide, the 16 px face plus the 16 px slope of
  the edge), anchored at the top vertex of the tile the face hangs from, at the top of the band.
  The engine draws the bottom band with `…/v<n>` and every band above with the same sprites; an
  optional `edge/<material>_<side>/top` is drawn as the uppermost band (merlons, a kerb, grass lip).
  Materials: `world.rock`, `world.earth`, `world.snow`, `world.coast` (surf foam at the foot,
  animated `…/v<n>/f<k>`), `rome.tufa`, `rome.brick`, `athens.limestone`, `parsa.ashlar`. The id
  is a material, namespaced like everything else: key `edge/parsa.ashlar_se/v0`.
  The existing whole-island `edge/cliff_*` and `edge/fall_*` stay for the home set.
- **Stairs and ramps** are items: `"rise": n, "axis": "x" | "y"` (`world.md` §10). Their footprint
  tiles are at the stair's **lower** level; the high end abuts tiles at `lower + rise`. The sprite
  is anchored at the lower level and must cover the face the upper tile hangs over it. Generic kit:
  `world.stair_stone` (1 × 2, rise 1, rotate), `world.stair_earth` (1 × 2, rise 1), `world.ramp`
  (1 × 4, rise 1), plus per-set looks (`parsa.stair_relief`, `athens.stair_marble`,
  `rome.stair_travertine`). Grand stairs are landmarks with walk tiles (the great stairway's flights
  are walk runs; its parapets are non-walk tiles).
- **Terraces and platforms** are terrain levels plus edge faces; a landmark stands on flat ground
  (every footprint tile at one level). Retaining walls with special faces (the Pārsa terrace with
  its outfalls) are an edge material, not a landmark.

### 1.7 Terrain sets

Exactly the existing scheme: a **base** terrain is a full diamond with variants
(`terrain/<id>/v<n>`); an **overlay** has 16 masks (`terrain/<id>/m<mask>/f<k>`) of same-terrain
neighbours with edges facing other terrain rounded to transparent. New, one field: an overlay names
the base it is drawn over, `"under": "<base id>"`. Two different bases never touch (worldgen puts a
transition overlay between them, §3.5).

| Set | Base | Overlays |
|---|---|---|
| `world` | `world.sand` (beaches, desert edge), `world.steppe` (Anatolia, Syria), `world.alluvium` (Mesopotamia) | `world.sea` (animated 4 frames, under `world.sand`), `world.shallows` (lighter sea near coasts), `world.river` (animated, plus flow overlays §1.8), `world.rock`, `world.snow`, `world.marsh`, `world.road_earth`, `world.field`, `world.scree` |
| `rome` | `rome.grass_spring` | `rome.basalt_paving`, `rome.travertine_paving`, `rome.brick_ground`, `rome.packed_earth`, `rome.tufa_rock`, `rome.field_spring`, `rome.vineyard_soil`, `rome.river_tiber`, `rome.mud_bank` |
| `athens` | `athens.dry_grass` | `athens.rock_limestone`, `athens.marble_paving`, `athens.gravel`, `athens.packed_earth`, `athens.field_stubble`, `athens.olive_soil`, `athens.riverbed` (sand and sea come from `world`) |
| `parsa` | `parsa.plain_grass` | `parsa.field_barley`, `parsa.garden_bed`, `parsa.packed_earth`, `parsa.paving_stone`, `parsa.paving_red`, `parsa.gravel`, `parsa.water_channel`, `parsa.rough_ground` (rock and river from `world`) |

Terrain values are one byte per tile world-wide (255 ids with 255 = no ground), which this list
fits with room to spare (about 45 ids). Seasonal looks follow `living-corner.md` R4 (`…/autumn`,
`…/winter` segments) and are optional per terrain.

### 1.8 Water and coast

- **Sea** is `world.sea` at level 0. Depth tint is not art: the engine tints by a per-tile distance
  to the coast that worldgen stores (§2.2). `world.shallows` is an overlay drawn on the first two
  sea tiles off a beach.
- **Shore foam:** `terrain/world.sea/foam/m<mask>/f<k>` (4 frames) drawn on sea tiles, `mask` =
  bits of **land** neighbours (the inverse of the overlay mask), additive-free alpha sprite.
- **Sea cliffs** use the `world.coast` edge material (§1.6).
- **Rivers:** `world.river` overlay plus a scrolling flow overlay `terrain/world.river/flow_n/f<k>`
  and `…/flow_e/f<k>` (8 frames). The engine mirrors `flow_n` for west and `flow_e` for south.
  Fords, bridges, jetties, quays and moorings are items (`world.ford`, `rome.pons_*`,
  `world.jetty`, `rome.quay`, …) with `mooring` slots.
- **Whitecaps** `fx/world.whitecap/f<k>`, **wake** `fx/world.wake/f<k>`, **fish jump** and
  **dolphin** as fx (`living-world.md` §5).

### 1.9 Actors in art: walkers, figures, animals, ships, carts, goods

**One rig.** All human walkers and figures are built on one posed voxel body in artgen (the
`models/resident.py` approach generalised): shared parts and a shared **pose library**, so every
kind animates the same way at the same frame counts and the engine needs one animation table.
A kind adds a **dress** (garment shapes, headgear, footwear, beard, carried tool) and lists its
colour **variants** (palette ramps for garment, trim and headgear); variants are baked by the
generator, so they cost atlas space (about 36 k px per kind-variant) but stay palette-exact.

Keys:

```
walker/<kind>/v<k>/<anim>_<front|back>/f<n>         anonymous people (k < variants)
walker/<kind>/v<k>/<anim>_<front|back>/glow/f<n>    optional emissive layer (torch, lamp)
figure/<id>/<anim>_<front|back>/f<n>                named people (one look, no variants)
critter/<id>/<anim>_<front|back>/f<n>               animals, as today (optional v<k> segment)
ship/<kind>/v<k>/<anim>_<front|back>/f<n>           ships and boats
cart/<kind>/v<k>/<anim>_<front|back>/f<n>           carts, carriages, litters, sledges, with
                                                    their draught animals and drivers baked in
goods/<id>                                          a carried unit
goods/<id>/s1, s2, s3                               1–3 units stacked at a slot
```

`front` faces `+x`, `back` faces `−y`; the engine mirrors for `+y` and `−x` (as `CLAUDE.md`).
Riders on horses or camels are baked as one sprite (`walker/world.courier/…` with the horse in it);
caravans are groups of separate animals and a driver (formation `line`). Every walker anim exists
in both facings. Actors have no `shadow` layer: the engine draws its soft contact shadow.

**Standard pose library** (names are shared by every kind; a kind lists the ones it has in its
catalog entry; frames are fixed so the engine and the generator agree):

| Pose | Frames | Meaning (and the city files' names it covers) |
|---|---|---|
| `move` | 6 | walk (`walk`, `lead`, `herd` when moving) — **required** |
| `idle` | 2 | stand, breathe (`stand`) — **required** |
| `carry` | 6 | walk with goods held up; the engine draws `goods/<id>` at `carry_at` (§1.10) — required for carrying kinds |
| `carry_idle` | 2 | stand holding goods |
| `run` | 6 | children, couriers on foot |
| `sit` | 2 | seated (bench, step, mat) |
| `lie` / `sleep` | 2 | lying, asleep |
| `talk` | 4 | speaking, hand moving (`chant`, `teach`, `call` share it) |
| `gesture` | 4 | arm raised, pointing, directing (`overseer`, `usher`) |
| `bow` | 4 | bow, hand before the mouth (Pārsa audience) |
| `kneel` | 2 | kneeling work or prayer |
| `work_low` | 4 | dig, hoe, plant, weed, scatter seed, gather |
| `work_high` | 4 | hammer, chisel, prune, beat olive branches |
| `haul` | 4 | pull a rope, push a sledge |
| `stir` | 4 | stir, knead, grind, press, dye |
| `pour` | 4 | pour, water plants, fill a jar |
| `write` | 4 | write on a tablet, scroll or wax board |
| `play` | 4 | play an instrument (the instrument is part of the dress) |
| `throw` | 4 | throw pots on a wheel, spin, weave (seated hand work) |
| `serve` | 4 | hand something over a counter |
| `guard` | 2 | stand to attention with spear or staff |
| `march` | 6 | marching step |

A kind needing a pose outside the library (an athlete wrestling, a dancer) adds it under its own
name with 4 frames; the library grows only by a written addition to this table. `fps` is data in
the actor kind (`living-world.md` §2.2). Sizes: adults 38–42 px tall, children 26–30 px.

**Animals** use `critter/` keys with `move`, `idle` and up to two of `graze`, `sleep`, `flap`,
`peck`; generic farm and pack animals live in `world`. **Birds** in flocks (`world.crane`,
`world.swift`, `world.gull`, `world.pigeon`, `world.stork`) are critters with `move` (flying) and
optionally `idle` (perched), anchored at the bottom of the body like today's flyers.

**Ships** (`rome.merchantman`, `rome.barge`, `athens.trireme`, `athens.merchant`,
`world.fishing_boat`, `parsa.reed_boat`, `parsa.phoenician`): `move` (under sail, sail full),
`slack` (sail hanging), `row` (oars), `idle` (moored, sail furled), 4 frames each. Sails are drawn
blowing to screen right; the engine mirrors for wind with negative screen x (`living-world.md`
§6.2). A ship's depth footprint is its catalog `size` (§1.12).

**Carts** (`rome.cart`, `rome.carriage`, `athens.cart`, `parsa.p_cart`, `parsa.p_sledge` with ox
team, `rome.litter` with bearers): `move` and `idle`, 4 frames.

**Goods** are `world.goods_<name>` (shared: bread, grain_sacks, flour, amphorae, fish, water_jar,
olives, oil_jar, clay, pot_raw, pot_fired, block, cloth, fleece, gift_vessels, tablet, produce,
feed). Sprite sizes: carried 10–16 px, stacks up to 24 × 20 px.

### 1.10 Geometry the art tool emits: pieces, walk tiles, slots, emitters, carry points

The model file is the one place geometry is authored (where the door is, where the throne stands,
which tiles are portico). The art tool emits it, per rotation it renders, into
`assets/atlas/<set>.geom.json`; the engine and worldgen read it. **Behaviour** of slots (kind,
capacity, goods, states) stays in the set catalog (§1.12); the two are joined by item id and slot
id, and a coverage test fails if a catalog slot has no geometry or the reverse.

```json
{
  "version": 1,
  "set": "parsa",
  "tile": [64, 32],
  "items": {
    "parsa.p_house": {
      "r0": { "h": 60, "slots": { "door": [ { "t": [3, 1], "face": "-x" } ] } },
      "r1": { "h": 60, "slots": { "door": [ { "t": [1, 3], "face": "-y" } ] } },
      "r2": { "h": 60, "slots": { "door": [ { "t": [-1, 1], "face": "+x" } ] } },
      "r3": { "h": 60, "slots": { "door": [ { "t": [1, -1], "face": "+y" } ] } }
    },
    "parsa.p_fire_altar": {
      "r0": { "h": 40, "slots": { "tend": [ { "t": [1, 0], "face": "-x" } ] },
              "emitters": { "fire": [0, -36] } }
    }
  },
  "actors": {
    "parsa.labourer": {
      "carry_at": { "carry_front": [[3, -27], [3, -28], [3, -27], [3, -26], [3, -27], [3, -28]],
                    "carry_back":  [[-3, -27], [-3, -28], [-3, -27], [-3, -26], [-3, -27], [-3, -28]],
                    "carry_idle_front": [[3, -27], [3, -27]],
                    "carry_idle_back":  [[-3, -27], [-3, -27]] }
    }
  }
}
```

Per item and rotation (`r<k>`, only rotations that were rendered):

| Field | Meaning |
|---|---|
| `h` | measured height of the sprite above the anchor, px (picking, occluder fade, culling) |
| `pieces` | split items only: `[[dx, dy, w, h], …]` in rotated footprint coordinates; index `i` is the sprite segment `p<i>` (§1.11). Absent = not split |
| `walk` | walk tiles `[[dx, dy], …]` (rotated footprint coordinates) |
| `slots` | `{slot id: [spot, …]}`. A spot is `{"t": [dx, dy], "off": [ox, oy], "z": n, "face": "+x"\|"-x"\|"+y"\|"-y"}`: tile offset from the origin tile (may lie outside the footprint, e.g. a door step), optional pixel offset from that tile's centre, optional height in px above the ground (seats, perches, a throne dais), facing of the actor using it. A slot with `cap > 1` lists one spot per place |
| `emitters` | `{name: [ox, oy]}` pixel offsets from the anchor (smoke, incense, spray, fire); `smoke_at` in the home catalog is the same thing for home items |

Per actor kind: `carry_at`, the pixel offset from the actor's anchor to the bottom centre of the
carried goods sprite, one entry per frame of each carrying animation.

Slot geometry for the home set stays in `catalog.next.json` as written (`where: on | beside | tile`);
the engine reads both forms.

### 1.11 Key reference (additions to `CLAUDE.md`'s table)

| Key | Meaning |
|---|---|
| `item/<id>/<layer>/r<k>/p<i>/f<n>` | piece `i` of a split item (`base` only; `i` indexes `pieces`) |
| `item/<id>/<state>/<variant>/f<n>` | a slot state drawn instead of `base` |
| `edge/<material>_<se\|sw>/v<n>`, `…/top`, `…/v<n>/f<k>` | one level of face, cap band, animated face |
| `terrain/world.sea/foam/m<mask>/f<k>` | shore foam on sea tiles (mask = land neighbours) |
| `terrain/world.river/flow_<n\|e>/f<k>` | river flow overlay (mirrored for w, s) |
| `walker/<kind>/v<k>/<anim>_<front\|back>/f<n>`, `…/glow/f<n>` | anonymous people |
| `figure/<id>/<anim>_<front\|back>/f<n>` | named figures |
| `ship/<kind>/v<k>/<anim>_<front\|back>/f<n>`, `cart/…` | ships, carts |
| `goods/<id>`, `goods/<id>/s<1-3>` | carried goods, stacks |
| `backdrop/<id>/<day\|night\|winter>/v<n>` | backdrop strip segment behind the north or east world edge: a parallelogram 16 tiles of edge long (512 × up to 384 px), anchored at the top vertex of the first edge tile it covers |
| `weather/<kind>_v<n>` | cloud shadows, fog strips, dust (`living-world.md` §6) |
| `fx/<id>/f<n>` | effects; set effects are namespaced (`fx/parsa.incense/f0`) |

### 1.12 Set catalogs: what the art tool reads

```
assets/sets/<set>/catalog.json     one per set except home (home stays assets/catalog.json)
```

A set catalog has the **same schema as `assets/catalog.json`** for the sections it contains
(`terrain`, `items`, `audio`), plus `actors` and `goods` (shapes from `living-world.md` §2.2, §3.2)
and an `art` block for keys the catalog cannot imply. It has no `tile`, `map`, `categories` or
progression sections: those stay global. `assets/catalog.json` lists the sets the engine loads
(`"sets": ["world", "rome", "athens", "parsa"]`, §6), and ids are unique across the union. Set
items have no `category` (they are not in build menus) unless a decorate zone later says so.

New item fields (all optional):

| Field | Meaning |
|---|---|
| `layers` | layers to render (§1.5) |
| `landmark` | `true`: unique, clickable for a card, rendered `r0` only unless `rotations` says otherwise |
| `rotations` | rotations to render, e.g. `[0]`; default all four for `rotate`, `[0]` for landmarks |
| `scale` | landmark scale `s` (`world.md` §2): the generator models in metres at 8 voxels per metre × `s` horizontally (32 per tile edge at `s = 1`) and 10 per metre × `s` vertically |
| `height` | expected height in px from the city tables; the validator warns beyond ±15 % |
| `rise`, `axis` | stairs and ramps |
| `slots` | behaviour per slot id: `{"id", "kind", "cap", "holds", "states", "anim"}` (`living-world.md` §2.3 without the geometry, which comes from §1.10) |
| `emitters` | names of emitter points the model must provide, with effect: `{"incense_l": "parsa.incense"}` |
| `occluder` | fade to 35 % when the cursor or a followed actor is behind it |
| `card` | card id (text lives in the region data, §2.6) |
| `size` | actors only: depth footprint in tiles `[w, h]` (ships 3 × 1, carts 2 × 1, people omit it) |

`art` block:

```json
"art": {
  "edges": ["parsa.ashlar"],
  "backdrops": ["parsa.kuh_rahmat"],
  "fx": ["parsa.incense", "parsa.chisel_dust"]
}
```

Who writes it: set catalogs are contracts, written from the city files by the design lane (one
task per set, §5) and changed only by the orchestrator or a brief that says so. Art and worldgen
read them; an art agent who needs a field changed reports it. Until a set catalog exists, an art
agent may build against a draft at `docs/design/sets/<set>.json` with the same schema.

### 1.13 Worked example: the Apadāna

From `persepolis.md` §2.3 and §3.2: footprint c 60..83, r 54..77 (24 × 24), local level 7, height
200 px, layers B, S, G, incense smoke, `s = 0.85`, walkers enter the north portico.

**Placement.** World plan `C 1196..1219`, `R 358..381`; grid `tx = R`, `ty = 1279 − C`:
`tx 358..381`, `ty 60..83`. Origin tile (smallest `tx, ty`) = **(358, 60)**, the north-east corner.
World level 4 + 7 = **11**. Rotation **0** (modelled in grid axes). Inside the footprint `dx` runs
south and `dy` runs west, so the south-west corner `(23, 23)` is the corner nearest the camera.

**Plan in footprint coordinates** (`dx` south, `dy` west; inclusive):

| Part | dx | dy | Walk |
|---|---|---|---|
| NE tower | 0..4 | 0..4 | no |
| NW tower | 0..4 | 19..23 | no |
| SE tower | 19..23 | 0..4 | no |
| SW tower (nearest the camera) | 19..23 | 19..23 | no |
| North portico (hidden side): column rows at dx 1 and 3, columns at dy 6, 8, 10, 13, 15, 17 (a wider central bay dy 11..12 leads to the throne) | 0..4 | 5..18 | every tile except the 12 column tiles |
| East portico (hidden side, no route) | 5..18 | 0..4 | no |
| West portico (seen, over the plain): column rows at dy 20 and 22, columns at dx 6, 8, 10, 13, 15, 17 | 5..18 | 19..23 | every tile except the 12 column tiles |
| Hall, 6 × 6 columns, closed | 5..18 | 5..18 | no |
| South service rooms, closed | 19..23 | 5..18 | no |

The north stair (`persepolis.md`: c 65..78, r 51..53) is a separate item `parsa.apadana_stair_n`:
footprint 3 × 14 at grid origin (355, 65) (`dx` −3..−1 relative to the Apadāna, `dy` 5..18),
level 10, `rise 1`, `axis "x"`, its two flights walk runs, its relief front facing north (hidden;
card and later view rotation). The east stair is `parsa.apadana_stair_e` likewise.

**Pieces** (by the rule of §1.3; 76 in all):

- towers: 4 pieces of 5 × 5; hall: 4 pieces of 7 × 7; south rooms: 2 pieces of 5 × 7;
  east portico: 2 pieces of 7 × 5;
- each portico: 12 column pieces of 1 × 1; walk runs along the three walk rows (2 runs of 7 per
  row = 6 pieces) and the walk tiles between columns in the two column rows (7 runs per row:
  `5`, `7`, `9`, `11..12`, `14`, `16`, `18` → 14 pieces); 32 pieces per portico.

Excerpt of the emitted geometry:

```json
"parsa.apadana": {
  "r0": {
    "h": 200,
    "pieces": [ [0, 0, 5, 5], [0, 19, 5, 5], [19, 0, 5, 5], [19, 19, 5, 5],
                [5, 5, 7, 7], [5, 12, 7, 7], [12, 5, 7, 7], [12, 12, 7, 7],
                [19, 5, 5, 7], [19, 12, 5, 7], [5, 0, 7, 5], [12, 0, 7, 5],
                [5, 19, 7, 1], [12, 19, 7, 1], [6, 20, 1, 1], [5, 20, 1, 1], "…" ],
    "walk": [ [0, 5], [0, 6], "…", [5, 19], [6, 19], "…", [18, 23] ],
    "slots": {
      "audience": [ { "t": [0, 11], "face": "+x" }, { "t": [0, 12], "face": "+x" },
                    { "t": [1, 11], "face": "+x" }, { "t": [1, 12], "face": "+x" } ],
      "usher":    [ { "t": [2, 13], "face": "-y" } ],
      "guard":    [ { "t": [0, 9], "face": "-x" }, { "t": [0, 14], "face": "-x" },
                    { "t": [18, 23], "face": "+y" }, { "t": [5, 23], "face": "+y" } ],
      "stroll":   [ { "t": [11, 21] }, { "t": [7, 19] }, { "t": [15, 23] } ]
    },
    "emitters": { "incense_l": [-288, 160], "incense_r": [-384, 208] }
  }
}
```

(`"…"` marks elided entries; the real file lists every piece and walk tile.) The incense
emitters are the tops of two bronze stands modelled at the foot of the columns on tiles (1, 10) and
(1, 13), which flank the central bay. The throne is not part of the model: it is the kit item
`parsa.p_throne`, placed by worldgen on walk tile (2, 11), so it occupies that tile and carries its
own `seat` slot where Xerxes sits during the audience; furniture inside a landmark is always kit
placed this way.

**Set catalog entry** (`assets/sets/parsa/catalog.json`):

```json
{ "id": "parsa.apadana", "name": "Apadāna", "footprint": [24, 24], "layout": "rotate",
  "count": 4, "rotations": [0], "on": "land", "landmark": true, "scale": 0.85, "height": 200,
  "layers": ["base", "shadow", "glow"], "occluder": true, "card": "apadana",
  "emitters": { "incense_l": "parsa.incense", "incense_r": "parsa.incense" },
  "slots": [ { "id": "audience", "kind": "stand", "cap": 4 },
             { "id": "usher", "kind": "stand", "cap": 1 },
             { "id": "guard", "kind": "stand", "cap": 4 },
             { "id": "stroll", "kind": "stand", "cap": 3 } ] }
```

**Sprite keys:** `item/parsa.apadana/base/r0/p0/f0` … `p75/f0`, `item/parsa.apadana/shadow/r0/f0`,
`item/parsa.apadana/glow/r0/f0`, `fx/parsa.incense/f0..f5`.

**Expected sizes at 64 × 32:** whole sprite bounds `(24 + 24) × 32 = 1536` px wide by
`(24 + 24) × 16 + 200 = 968` px tall; opaque base pixels about 1.1 M after the pieces' trimming
(the diamond's empty corners drop out), about 7 % of a 4096² page; shadow about 0.4 M px (one
sprite, toward the lower right); glow under 20 k px (tower windows, door lamps). Tallest piece: a
walk run on the west portico, 32 px wide per tile of run plus 200 px of columns and roof above.
The hall pieces each about 448 × 424 px before trimming.

**Checks the art validator runs on it:** every walk tile has no voxels between 2 px and 48 px above
the floor; every walk tile connects to the footprint edge or to the stair; every catalog slot has
geometry; pieces partition the footprint; the measured `h` is within 15 % of 200.
