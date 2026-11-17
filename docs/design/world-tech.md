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
- Kit models face `+y` in `r0` (the artgen convention) and each `k` turns them 90° clockwise seen
  from above, so in compass terms `r0` faces west, `r1` north, `r2` east and `r3` south. Worldgen
  takes compass facings and converts (§3.3).
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
      "r0": { "h": 60, "slots": { "door": [ { "t": [1, 3], "face": "-y" } ] } },
      "r1": { "h": 60, "slots": { "door": [ { "t": [-1, 1], "face": "+x" } ] } },
      "r2": { "h": 60, "slots": { "door": [ { "t": [1, -1], "face": "+y" } ] } },
      "r3": { "h": 60, "slots": { "door": [ { "t": [3, 1], "face": "-x" } ] } }
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

---

## 2. World data model

### 2.1 Principles

1. **Regions are the unit of authoring, theme and ownership.** Every city, stretch, waypoint town,
   seam band and the corner is a region with an id (`world.md` §5.2 ids, plus one per waypoint town
   and seam: `ostia`, `delphi`, `babylon`, `seam_ionian`, …). Every tile belongs to exactly one
   **district**, and every district to one region, so "which region am I in" is a tile lookup, not
   a test against overlapping rectangles (the stretch rects in `world.md` overlap and some are not
   rectangles).
2. **The world is layers.** A procedural **base** layer covers the whole map (sea, coasts, relief,
   rivers, country, roads). Each authored place (the corner, the three cities, each waypoint town)
   is a layer over its rect that replaces the base where it sets tiles. One builder agent owns one
   layer file, so builders never write the same file (§3.7), and a city that is not built yet simply
   shows the base.
3. **Prebuilt content is immutable and never saved.** The save holds the home region
   (home-relative, as `living-corner.md` §2.1 requires) and a handful of world-global facts.
4. **The whole tile world stays in memory** (§2.8: about 7 MB). Only textures, actors and audio
   stream. This replaces `world.md` §14 item 1's chunk streaming of tile data, which buys nothing at
   this size and costs a loader, a cache and their bugs.

### 2.2 Files

| Path | Format | Written by | Read by |
|---|---|---|---|
| `assets/catalog.json` | JSON | orchestrator | engine, generators: gains `tile.level`, `sets`, `world` (§6) |
| `assets/sets/<set>/catalog.json` | JSON | design lane (§1.12) | engine, artgen, audiogen, worldgen |
| `assets/world/world.json` | JSON | worldgen (from the plan) | engine, worldgen |
| `assets/world/layers/<layer>.lcw` | binary (§2.4) | worldgen, one builder per layer | engine, worldgen |
| `assets/world/layers/<layer>.graph.json` | JSON (§2.5) | worldgen, same builder | engine, worldgen |
| `assets/world/overview.png` | PNG, north-up map art | worldgen (§3.6) | engine |
| `assets/regions/<region>.json` | JSON (§2.6) | the builder of that region | engine, worldgen (validation) |
| `assets/atlas/…` | §1.2 | artgen | engine, worldgen previews |
| `assets/audio/<music\|amb\|sfx>/<set>/…` | as `CLAUDE.md` | audiogen | engine |

Every JSON file has `"version": 1`; readers refuse a newer version and log once. Grid coordinates
everywhere (the conventions at the top of this file). Lists of ids are strings, never indices,
except inside a layer file, whose own string tables make its indices local (adding an item to
Rome never renumbers Athens).

### 2.3 `world.json`

```json
{
  "version": 1,
  "grid": [448, 1280],
  "chunk": 32,
  "home": { "origin": [40, 1200], "size": [40, 40], "level": 2, "region": "corner" },
  "layers": [
    { "id": "base",   "file": "layers/base.lcw",   "graph": "layers/base.graph.json" },
    { "id": "corner", "file": "layers/corner.lcw", "graph": "layers/corner.graph.json" },
    { "id": "ostia",  "file": "layers/ostia.lcw",  "graph": "layers/ostia.graph.json" },
    { "id": "rome",   "file": "layers/rome.lcw",   "graph": "layers/rome.graph.json" }
  ],
  "regions": [
    { "id": "corner", "set": "home", "kind": "home",    "time": "timeless", "life": "regions/corner.json" },
    { "id": "latium_italy", "set": "rome", "kind": "stretch", "time": "rome", "life": "regions/latium_italy.json" },
    { "id": "ostia",  "set": "rome", "kind": "town",    "time": "rome", "life": "regions/ostia.json" },
    { "id": "rome",   "set": "rome", "kind": "city",    "time": "rome", "life": "regions/rome.json" },
    { "id": "seam_ionian", "set": "world", "kind": "seam", "time": "none", "life": "regions/seam_ionian.json" }
  ],
  "markers": [
    { "region": "corner", "at": [60, 1220], "icon": "home" },
    { "region": "rome",   "at": [104, 1100], "icon": "rome" },
    { "region": "ostia",  "at": [214, 1155], "icon": "town" }
  ]
}
```

- `grid` is `[x size, y size]`: 448 × 1280 tiles, 14 × 40 = 560 chunks.
- `layers` are composed in order; a missing file is skipped with one log line (the base shows).
- `regions[].kind` ∈ `home`, `city`, `town`, `stretch`, `seam`; it sets the blend radius and the
  caption style (§4.6). `time` names the moment (`rome`, `athens`, `parsa`, `timeless`, `none`);
  a caption shows when the dominant region's `time` changes (§4.8).
- `markers` are overview anchors (§4.7). All user-visible text (names, captions) lives in the
  region files, not here.

### 2.4 Layer file `.lcw`

Little-endian binary. A cell is either **transparent** (keeps the layer below) or fully set.

```
offset  type          field
0       char[4]       magic "LCWL"
4       u16           version = 1
6       u16           0 (reserved)
8       i16, i16      x0, y0: grid position of the layer's rect
12      u16, u16      w, h: rect size in tiles
16      u16 × 4       nTerrain, nDistrict, nItemId, 0
24      strings       nTerrain + nDistrict + nItemId strings, each u8 length + UTF-8 bytes:
                      terrain ids, district names ("rome/subura"), item ids
…       plane T       RLE over the w × h cells, x fastest: pairs (u8 value, u8 run − 1).
                      value = terrain table index; 0xFE = transparent; 0xFF = no ground
…       plane L       RLE as above: the level byte (below); ignored where T is transparent
…       plane D       RLE as above: district table index; ignored where T is transparent
…       u32           item count, then per item 8 bytes:
                      u16 id index, u16 x, u16 y (relative to x0, y0; origin tile), u8 variant
                      (rotation k or look), u8 flags (0; reserved)
end                   no trailing bytes
```

**Level byte:** bits 0–3 level 0..15; bits 4–5 `aux`, whose meaning depends on the terrain: sea →
depth band 0..3 (engine tint), river → flow direction (0 = `−y`, 1 = `+x`, 2 = `+y`, 3 = `−x`),
land → index into the terrain's `faces` list (which edge material its cliff faces use, §6); bit 6
**impassable** (scenic mountains, cliff tops no actor may enter); bit 7 reserved, 0.

**Composition rule:** layers apply in `world.json` order. A non-transparent cell overwrites the cell
below. An item of a lower layer whose footprint touches any non-transparent cell of a higher layer
is dropped (worldgen reports it as a warning when it composes; the engine silently drops it). The
home region (`world.home`) is applied last from the save or the starter scene (§4.1).

**Validation by the engine:** magic, version, sizes, every run inside the plane, rect inside the
grid, no trailing bytes. A failing layer is skipped whole with one log line; unknown terrain ids
draw the placeholder; unknown item ids are skipped with one log line each. Worldgen does the
semantic validation (§3.5).

Tiny valid example (a 2 × 1 layer at grid (10, 20): one grass tile at level 1 in district
`corner/meadow` with an oak on it, one transparent cell), as hex:

```
4C 43 57 4C  01 00  00 00  0A 00 14 00  02 00 01 00   magic, v1, x0=10 y0=20 w=2 h=1
01 00 01 00 01 00 00 00                               1 terrain, 1 district, 1 item id
05 67 72 61 73 73                                     "grass"
0D 63 6F 72 6E 65 72 2F 6D 65 61 64 6F 77             "corner/meadow"
03 6F 61 6B                                           "oak"
00 00  FE 00                                          T: grass ×1, transparent ×1
01 01                                                 L: level 1 ×2
00 01                                                 D: district 0 ×2
01 00 00 00  00 00 00 00 00 00 02 00                  1 item: oak at (0,0), variant 2, flags 0
```

### 2.5 Paths, roads and lanes: `<layer>.graph.json`

One graph per layer, merged at load. Node ids are local to the layer and become `<layer>:<id>`;
**portals** (`"kind": "portal"`) with the same id in two layers are the same node, which is how a
road out of Rome meets the base layer's Via Appia.

```json
{
  "version": 1,
  "layer": "rome",
  "nodes": [
    { "id": "forum_market", "at": [88, 1093], "kind": "dest" },
    { "id": "n12", "at": [92, 1090] },
    { "id": "appia_se", "at": [168, 1008], "kind": "portal" }
  ],
  "edges": [
    { "a": "forum_market", "b": "n12", "kind": "street" },
    { "a": "n12", "b": "appia_se", "kind": "road", "via": [[120, 1060], [150, 1030]] }
  ],
  "lanes": [
    { "id": "tiber_barge", "kind": "river", "points": [[183, 1119], [200, 1140], [226, 1153]],
      "ports": [ { "id": "emporium", "at": 0, "slot": "rome.quay:mooring" },
                 { "id": "portus", "at": 2 } ] }
  ]
}
```

- Node `kind` ∈ (absent: plain), `dest` (a destination with a next-hop table, at most 64 per
  region, `living-world.md` §7.6), `door`, `gate`, `station`, `portal`. Node level comes from the
  tile. Edge `kind` ∈ `street`, `road`, `track`, `stair`, `ramp`, `towpath`, `quay`, `bridge`,
  `ford`; length is computed from the points (`via` is the polyline between the end nodes).
- **Lanes** are polylines for ships and towed barges (`sea`, `river`, `towpath`), with ports at
  point indices; long land routes for tokens (caravans, couriers) are not lanes: they are the
  shortest graph path between two `dest` nodes, computed once at load into a polyline (§4.11).
- Worldgen derives almost everything here from street and road polylines (§3.3); builders name
  only the nodes the life data refers to.

### 2.6 Region file `assets/regions/<region>.json`

One per region: its theme, its life (`living-world.md` shapes, unchanged), its figures, cards and
text. Actor **kinds** live in set catalogs (a Persian scribe is the same kind in Pārsa, Susa and
Babylon); the region file says where and when they appear.

```json
{
  "version": 1,
  "id": "parsa",
  "name": "Pārsa", "native": "تخت جمشید", "caption": "Pārsa · spring, c. 470 BC",
  "theme": {
    "grading": { "dawn": [0.92, 0.84, 0.80], "day": [1.0, 0.98, 0.94],
                 "dusk": [0.95, 0.78, 0.66], "night": [0.42, 0.48, 0.66] },
    "haze": { "colour": [0.86, 0.82, 0.74], "strength": 0.15 },
    "climate": "parsa",
    "ambience": { "beds": [ { "file": "amb/parsa/plain_day.ogg", "hours": ["06:00", "18:00"] },
                            { "file": "amb/parsa/plain_night.ogg", "hours": ["18:00", "06:00"] } ],
                  "zones": [ { "rect": [312, 89, 338, 117], "file": "amb/parsa/channels.ogg", "gain": 0.7 } ] },
    "music": { "day": "music/parsa/day.ogg", "night": "music/parsa/night.ogg" }
  },
  "districts": [
    { "id": "terrace", "populations": [ { "actor": "parsa.guard", "density": "court", "max_per_chunk": 6 } ] },
    { "id": "town", "populations": [ { "actor": "parsa.woman_worker", "density": "daytime", "max_per_chunk": 8 } ] }
  ],
  "densities": { "daytime": [0,0,0,0,0,0.1,0.4,0.8,1,1,1,1,0.8,0.6,0.8,1,1,0.9,0.6,0.3,0.1,0,0,0],
                 "court":   [0.3,0.3,0.3,0.3,0.3,0.4,0.8,1,1,1,1,1,1,1,1,1,1,0.8,0.5,0.4,0.3,0.3,0.3,0.3] },
  "figures": [ { "actor": "parsa.xerxes", "presence": "present", "card": "xerxes" } ],
  "groups": [], "chains": [], "events": [], "lanes_tokens": [],
  "cards": { "xerxes": { "title": "Xšayāršā", "epithet": "Great King", "text": "…" },
             "apadana": { "title": "Apadāna", "epithet": "Hall of audience", "text": "…" } },
  "strings": { "first_visit": "…" },
  "journal": ["landmark:*", "figure:*", "delegation:*", "chain:*"]
}
```

- Rects in region files are grid `[x0, y0, x1, y1]`, inclusive (the zone above is the paradise
  garden).
- `theme.grading` keyframes are multipliers on the existing day/night grade (so the corner's
  `[1, 1, 1]` theme means "as today"). Stretches have no `music`; seams have `"seam": true` in their
  theme (ambience dip and drone, `world.md` §9.2).
- `districts[].id` matches the district names in the layers (`parsa/terrace` → `terrace`).
- `groups`, `chains`, `events`, `figures` take exactly the shapes in `living-world.md` §2–§5;
  `lanes_tokens` lists token actors with their lane or route (`{"actor": "rome.merchantman",
  "lane": "base:tyrrhenian_grain", "count": 3}`).
- This file is where a region's user-visible strings live (`CLAUDE.md` "one place each" becomes
  "one place per region", §6).

### 2.7 The save: what the player changes

Only the home region is editable in this version (decorate zones in cities are deferred, §5).
The world save is `living-corner.md` §2.4's layout, numbered **version 3** (the engine's chunked
format already took 2; the reader keeps reading 1 and 2), plus a `world` block:

```json
{
  "version": 3,
  "name": "Plum Hollow", "free_build": false, "created": "2026-11-17T10:42:00Z", "played": 5234.5,
  "clock": { "t": 0.31, "pin": "auto", "day": 7 }, "season_pin": "auto",
  "settings": { "rain": false },
  "progress": { "unlocked": ["oak"], "frames": ["plain"], "wishes": { "open": [], "done": [],
                "snoozed": {}, "last_offer": 0 }, "clues": [], "seen": ["duck"], "nooks": [],
                "harvests": 0, "last_harvest_day": 0, "new": [] },
  "home": { "map": { "w": 40, "h": 40 }, "palette": ["grass", "water"],
            "terrain": [[0, 1180], [1, 20], [0, 400]],
            "items": [ { "id": "oak", "x": 24, "y": 31, "v": 2 } ], "stage": 0 },
  "world": { "camera": { "at": [60.5, 1220.0], "zoom": 2 },
             "visited": ["corner", "rome"],
             "journal": { "rome": ["landmark:rome.colosseum", "figure:rome.hadrian"] },
             "followed_chains": ["rome_bread"], "flags": ["seam_explained"] }
}
```

- `home.terrain` is RLE `[palette index, run]` over 40 × 40, x fastest (the chunk encoding of
  today's v2, one chunk wide). Home coordinates are home-relative; the world origin of the home
  region comes from `world.json`, so moving the home in a later world revision never rewrites saves.
- `world.camera.at` is in grid tiles (fractional). If the world changes under it, it is clamped.
- `world.flags` holds one-time facts (the first seam crossing's line has been shown).
- Nothing else about the world is saved: actors, events, chains, weather and tokens are pure
  functions of the seed and the clock (`living-world.md` §7.4).

### 2.8 Sizes

**On disk** (committed, estimated from the city tables and today's atlas, whose 4096 × 1024 page
is 1.4 MB as PNG):

| What | Size |
|---|---|
| `base.lcw` (573 k cells, long runs at sea; about 30 k country items) | ≈ 0.6 MB |
| city layers: Rome (28 k cells, ≈ 9 k items) 0.1 MB, Athens 0.09, Pārsa 0.07, corner 0.03 | ≈ 0.3 MB |
| 20 waypoint town layers, ≈ 10 KB each | ≈ 0.2 MB |
| graphs (≈ 2 000 nodes per city, roads, lanes) | ≈ 0.6 MB |
| region files (cards and text dominate) | ≈ 1 MB |
| `overview.png` (2560 × 896) | ≈ 1.5 MB |
| atlas pages: world 1, Pārsa 2, Athens 2, Rome 3, at 4–6 MB each as PNG | ≈ 40 MB |
| audio: per city day and night music, 3–5 beds and 20–40 effects, plus stretch beds | ≈ 45 MB |
| **world data without art and audio** | **≈ 4 MB** |

**In memory:**

| What | Size |
|---|---|
| tile planes (terrain, level, district: 3 B per tile) | 1.7 MB |
| occupancy (4 B per tile, as today) | 2.3 MB |
| per-chunk tallies (terrain and item counts) | ≈ 1.5 MB |
| items (≈ 60 k × 12 B plus chunk indices) | ≈ 1 MB |
| graphs and next-hop tables (64 destinations × 2 000 nodes × 2 B per region) | ≈ 3 MB |
| region and set data as structs | ≈ 5 MB |
| actor pool (1 024 × 96 B), slot state, tokens | < 0.3 MB |
| **CPU total for the world** | **≈ 15 MB** |
| atlas pages resident (4096² RGBA = 64 MB each): home 16 + world 64 + one city set 128–192 | 210–270 MB GPU |
| ground cache (today's budget 128 MB; lower it to 96 MB) | 96 MB GPU |
| overview texture | 9 MB GPU |

The CPU copies of atlas pages are dropped after upload; the per-sprite data the engine needs from
pixels (luma, alpha centroid, a 1-bit hit mask for picking landmarks) is computed at load and kept
(≈ 2 MB per page).

---

## 3. World authoring pipeline: worldgen

### 3.1 What it is

`tools/worldgen/` is a deterministic Python 3 tool (pinned `requirements.txt`: numpy and Pillow;
local `.venv`, like artgen) that compiles **region sources** into the layer files, graphs and
overview of §2, validates them, and renders previews from the atlas pages without the engine.
Cities are literally built by agents writing region sources in a small layout language.

```
tools/worldgen/
  build.sh                     ./build.sh <layer>… | --all | --check | --preview <layer>
  worldgen/                    the library (owned by the worldgen-core task)
    dsl.py                     Layout API (§3.3)
    shapes.py raster.py        shapes, polyline and polygon rasterisation (exact, integer)
    catalog.py                 loads assets/catalog.json + every set catalog + geometry files
    layer.py graph.py          .lcw and .graph.json writers and readers
    compose.py                 base + layers → the composed world (same rule as the engine)
    validate.py                §3.5
    bible.py                   reads the landmark tables of docs/design/cities/*.md
    base.py                    the procedural base layer (§3.8)
    preview.py                 §3.6
    rng.py                     SplitMix64 streams keyed by strings (Python's hash() is not used)
  plan/
    world_plan.py              region and stretch extents, home origin, coast polygons, mountain
                               bands, rivers, routes and waypoints, seams (the world.md tables)
  regions/<layer>/layout.py    one per authored layer: corner, rome, athens, parsa, ostia, …
  regions/<layer>/README.md    what is built, what is missing, deviations from the city file
```

`./build.sh parsa` compiles only that layer, composes it with the committed other layers to
validate, and writes `assets/world/layers/parsa.lcw` and `parsa.graph.json`. Same inputs, same
bytes (a test builds twice and compares). A layer compiles in seconds; the base layer in under a
minute with numpy.

### 3.2 Coordinates

Region sources use the **city files' local plan coordinates** `(c, r)` (east, south, from the
region's north-west corner) so builders copy numbers straight from the tables. Rects are inclusive
`(c0, r0, c1, r1)`. `Layout` converts once: `C = origin_c + c`, `R = origin_r + r`, `tx = R`,
`ty = 1279 − C`. Levels are **local** (the city files' tables); the region's base level is added.
Facings are compass words (`"north"`, `"south"`, `"east"`, `"west"`), converted to `r<k>` by §1.4.
Landmark footprints in catalogs are in grid axes (`[x extent = north–south, y extent =
east–west]`), and `place(rect=…)` checks the plan rect against them after conversion.

### 3.3 The layout API

```python
class Layout:
    # identity (made by build.sh from world_plan.py; the source receives it)
    region: str; set: str; origin: tuple[int, int]; size: tuple[int, int]; base_level: int

    # ground
    def fill(self, terrain: str, level: int = 0, district: str | None = None) -> None
    def paint(self, shape: Shape, terrain: str) -> None
    def level(self, shape: Shape, level: int, face: str | None = None) -> None   # set local level
    def impassable(self, shape: Shape) -> None
    def district(self, name: str, shape: Shape) -> None                           # later calls win
    def transparent(self, shape: Shape) -> None        # leave the base layer showing (seams, edges)

    # things
    def place(self, item: str, *, rect: Rect | None = None, at: tuple[int, int] | None = None,
              face: str = "west", variant: int = 0, name: str | None = None) -> Placed
    def scatter(self, shape: Shape, items: dict[str, float], density: float, *, min_gap: int = 1,
                seed: str) -> list[Placed]                      # groves, rocks, steppe tufts
    def row(self, line: Line, item: str, every: int, *, face: str = "west", offset: int = 0) -> list[Placed]
    def houses(self, shape: Shape, kit: dict[str, float], *, front: list["Street"],
               gap: float = 0.1, seed: str) -> list[Placed]     # doors face the nearest front street
    def fields(self, shape: Shape, crop: str, *, plot: tuple[int, int] = (4, 3),
               path: str | None = None, seed: str) -> None
    def wall(self, line: Line, kit: str, *, tower: str | None = None, every: int = 8,
             gates: list[tuple[int, int, str]] = ()) -> None    # kit is a connect layout

    # ways and water (streets and roads also make graph nodes and edges)
    def street(self, points: list[tuple[int, int]], *, width: int, paving: str,
               kerb: str | None = None, kind: str = "street", portal: str | None = None) -> "Street"
    def stair(self, item: str, *, rect: Rect, face: str) -> Placed  # checks the levels at both ends
    def river(self, points: list[tuple[int, int]], *, width: int, terrain: str = "world.river",
              banks: dict[str, float] | None = None, seed: str = "") -> None   # flow follows points
    def channel(self, points: list[tuple[int, int]], *, terrain: str, width: int = 1) -> None
    def lane(self, lane_id: str, points: list[tuple[int, int]], *, kind: str,
             ports: dict[str, int]) -> None

    # graph names the life data refers to
    def node(self, node_id: str, at: tuple[int, int], *, kind: str = "dest") -> None
    def link(self, placed: Placed, slot: str, node_id: str) -> None   # slot spot ↔ node edge

    # checks and previews
    def expect(self, landmark: str, *, rect: Rect, level: int | None = None) -> None
    def view(self, name: str, rect: Rect) -> None                     # a named close-up (§3.6)
```

District names are written bare (`"town"`) and stored as `<region>/<name>` (`parsa/town`).
Shapes: `Rect(c0, r0, c1, r1)`, `Poly([(c, r), …])` (even-odd fill, exact integer rasterisation:
a tile is inside when its centre is), `Line([(c, r), …], width)` (tiles within `width / 2` of the
polyline, straight runs exact). `Placed` carries the item's grid rect and its slot spots (from the
geometry file, so `houses` can face doors to streets and validation can check slots).

**Order matters and is the only state:** later calls overwrite earlier ones on the same tiles,
except that `place` fails if the footprint is occupied or the ground under it is not flat and
valid; `houses`, `scatter`, `row` and `fields` skip tiles that are occupied or unsuitable instead.
Every random choice takes an explicit `seed` string; the stream is `SplitMix64(hash64(region,
seed))`.

`houses` is the district filler: it walks the frontage of the given streets, tries kit pieces in
weighted order with the door slot facing the street, keeps `gap` of frontage free as alleys and
courtyards, fills the block interior with smaller pieces whose doors reach an alley, and gives up
on tiles that cannot be reached. It never places a house whose door spot is not walkable.

### 3.4 Worked excerpt: Pārsa, the stairway forecourt, the town and the terrace front

From `persepolis.md` §2.2–2.6 (D3, D4, D7, the terrace, the great stairway, the Gate, the Apadāna):

```python
"""Pārsa: forecourt (D3), town (D4), road station (D7), terrace front. Local plan coordinates."""
from worldgen.dsl import Layout, Rect, Line


def build(L: Layout) -> None:
    L.fill("parsa.plain_grass", level=0, district="fields")
    L.district("forecourt", Rect(26, 36, 48, 60))
    L.district("town", Rect(0, 62, 48, 112))
    L.district("station", Rect(20, 113, 34, 126))
    L.district("terrace", Rect(56, 22, 119, 118))

    # The terrace: six levels of fitted ashlar on its visible west face, paved courts on top.
    L.level(Rect(56, 22, 119, 118), 6, face="parsa.ashlar")
    L.paint(Rect(56, 22, 119, 118), "parsa.paving_stone")
    L.level(Rect(60, 54, 83, 77), 7, face="parsa.ashlar")            # Apadāna platform
    L.paint(Rect(70, 43, 92, 46), "parsa.paving_stone")              # Gate → Hall road

    # Landmarks: each rect is checked against the catalog footprint and persepolis.md §2.3.
    stair = L.stair("parsa.great_stair", rect=(49, 37, 55, 54), face="west")   # rise 6
    L.place("parsa.gate_all_lands", rect=(64, 42, 69, 47))
    L.place("parsa.apadana", rect=(60, 54, 83, 77))
    L.stair("parsa.apadana_stair_n", rect=(65, 51, 78, 53), face="north")
    L.place("parsa.p_throne", at=(72, 56), face="north", name="throne")   # Apadāna tile (2, 11)

    # The royal road from the Persian Gates, three tiles of packed earth, into a gravel plaza.
    L.street([(0, 50), (26, 50)], width=3, paving="parsa.packed_earth", kind="road",
             portal="royal_road_w")
    L.paint(Rect(26, 36, 48, 60), "parsa.gravel")
    L.node("stair_foot", at=(48, 45))
    L.link(stair, "foot", "stair_foot")
    L.node("gate_all_lands", at=(63, 45))

    # The town: a spur south to the station, lanes every nine rows, courtyard houses between.
    spur = L.street([(22, 50), (22, 113)], width=2, paving="parsa.packed_earth")
    lanes = [L.street([(1, r), (47, r)], width=1, paving="parsa.packed_earth")
             for r in range(66, 112, 9)]
    L.houses(Rect(0, 62, 48, 112),
             kit={"parsa.p_house": 3, "parsa.p_house_small": 5, "parsa.p_workshop": 1,
                  "parsa.p_granary": 0.5},
             front=[spur, *lanes], gap=0.15, seed="town")
    L.scatter(Rect(0, 62, 48, 112), {"parsa.p_oven": 1, "parsa.p_jars": 2}, 0.01, seed="yards")
    L.place("parsa.road_station", rect=(20, 114, 28, 121))
    L.node("station", at=(24, 113))

    # Water along the terrace foot, cypresses beside it.
    L.channel([(50, 56), (50, 118)], terrain="parsa.water_channel", width=2)
    L.row(Line([(52, 60), (52, 118)], 1), "parsa.t_cypress", every=3)

    L.expect("great_stair", rect=(49, 37, 55, 54), level=0)
    L.view("forecourt", Rect(20, 30, 70, 64))
    L.view("town", Rect(0, 60, 48, 112))
```

### 3.5 Validation

`./build.sh --check` (and every build) runs these on the composed world; errors fail the build,
warnings are listed in `out/worldgen/<layer>/report.txt`.

| # | Check | Level |
|---|---|---|
| V1 | every terrain, item, actor, goods id exists in the union of catalogs; every district name is `region/name` of this region | error |
| V2 | no two items share a tile (within a layer; across layers only through the composition rule, reported) | error |
| V3 | every footprint tile has ground of the item's `on` kind, all at one level; stairs at their lower level with the high end abutting `lower + rise` | error |
| V4 | landmark rects and levels equal the city file's §2.3 table (parsed by `bible.py` from the table rows: id in backticks, name, `c a..b, r a..b`, `w × h`, level); a listed landmark missing from the layout is a warning, an error once the region's README marks it complete | error |
| V5 | walk steps: 4-adjacent walkable tiles differ in level only through a stair or ramp; walkers never cross impassable or water tiles except by bridge or ford items | error |
| V6 | the graph is connected inside the region; every portal exists in the layer it names; every `dest` node reaches every other | error |
| V7 | every slot spot of every placed item is a walkable, free tile reachable from the graph within 24 tiles (bounded BFS, as the engine's last-stretch search) | error |
| V8 | two different base terrains never touch (an overlay must sit between); seas are level 0; river flow never runs uphill | error |
| V9 | the layer rect lies inside its region's extent; districts cover every non-transparent tile | error |
| V10 | budgets: ≤ 1 200 items per chunk (the depth sort's budget, §4.14), ≤ 64 dest nodes per region, ≤ 254 districts world-wide, ≤ 40 items carrying `glow` per chunk | error |
| V11 | elevation readability: where a raised tile hides a walkable tile behind it (§4.3), at most 25 % of a region's walkable tiles are hidden this way | warning |
| V12 | every `card` an item names exists in the region file; every actor kind a region file uses exists | error |
| V13 | determinism: compile twice, compare bytes (in the test suite, not every build) | test |

### 3.6 Previews

Written under `out/worldgen/<layer>/` (scratch, deleted by the agent when done; never committed):

- `map.png`: the layer at 1 px per tile, north up, coloured by each terrain's mean colour (taken
  from its atlas sprite, or a fixed fallback), shaded by level, items as dots, streets and graph
  edges as lines, districts as faint outlines; 4 px per tile for a city (`map_4x.png`).
- `close_<view>.png`: isometric renders of each `view()` and of every landmark's surroundings, at
  1 × from the atlas pages and geometry files, drawn exactly as the engine draws (ground by
  diagonal rows with faces, items and pieces in rectangle depth order, occluders, shadows composited
  once, glow omitted), with placeholders for missing art (a grey box of the catalog `height` with
  the id written on it). At most 2048 × 2048 px each.
- `issues.png`: `map.png` with every error and warning location circled and numbered as in
  `report.txt`.
- `./build.sh --preview world` writes `world.png` (the composed world at 1 px per tile) and
  regenerates `assets/world/overview.png` (§4.7: the styled north-up map, 2 px per tile, paper
  colours per time band, coastlines in sepia, mountains as hatched triangles, roads dotted, city
  icons); only the worldgen-core owner commits that file.

The preview renderer reads only data files (pages, manifests, geometry, catalogs), never artgen or
engine code, so the lanes stay independent.

### 3.7 Several builders at once

- **One builder per layer.** A builder owns `tools/worldgen/regions/<layer>/`,
  `assets/world/layers/<layer>.*` and `assets/regions/<region>.json` for the regions inside that
  layer. Nobody else writes them.
- **The library and the plan** (`tools/worldgen/worldgen/`, `tools/worldgen/plan/`,
  `assets/world/world.json`, `layers/base.*`, `overview.png`) belong to the worldgen-core task;
  builders report needed changes instead of making them.
- A build validates against the **committed** other layers; layers overlap only through blend
  margins the plan assigns (a city's layer is its region rect; the base fills the rest), so two
  builders never fight over tiles. Portals named in `world_plan.py` are the agreed meeting points.
- Builders commit `layout.py`, the README, the layer files, the graph and the region file together,
  staging only those paths, in one commit per working step.

### 3.8 The connective land: procedural with authored waypoints

The base layer is generated by `worldgen/base.py` from `plan/world_plan.py`, which holds only
coarse authored data:

```python
COAST = {  # land polygons in world plan coordinates (C, R), a vertex every 8–20 tiles
    "italy": [(96, 0), (300, 0), (330, 60), (392, 250), (407, 279), (380, 290), (300, 230), …],
    "greece": […], "anatolia": […], "corner_headland": [(0, 0), (95, 0), (95, 111), (30, 111), …],
}
BANDS = [  # relief: polygon, level range, noise scale, terrain by height, impassable
    {"id": "apennines", "poly": […], "levels": (8, 12), "scale": 24, "terrain": ["world.rock", "world.snow"],
     "impassable": True, "passes": [(345, 175)]},
]
RIVERS = {"tiber": [(160, 183), (140, 205), (126, 226)], …}
ROUTES = {  # world.md §5.3; waypoints are portals of town layers or plain points
    "via_appia": {"points": ["rome:appia_se", (292, 160), "capua:north", (350, 214), "brundisium:west"],
                  "paving": "rome.basalt_paving", "width": 2, "kind": "road",
                  "every": {"rome.r_milestone": 8, "rome.r_tomb": 5}, "stations": {"rome.mutatio": 24}},
    "royal_road": {"points": ["sardis:east", (912, 150), "halys:west", …, "parsa:royal_road_w"],
                   "paving": "world.road_earth", "width": 2, "kind": "road",
                   "every": {}, "stations": {"parsa.road_station_small": 12}},
}
STRETCH_LOOK = {  # per stretch: base terrain, overlays by slope/moisture, plant sets, hamlet kit
    "latium_italy": {"base": "rome.grass_spring", "plants": {"world.t_stone_pine": 1, "rome.t_cypress": 1},
                     "density": 0.05, "hamlet": ["rome.r_villa_farm", "rome.r_shed"], "every": 40},
}
```

The generator, in order (each step seeded and deterministic):

1. Rasterise land polygons; displace their outlines by bounded noise (±2 tiles) for natural
   coasts; sea is level 0 with depth bands by distance to land (1, 3, 6 tiles).
2. Relief: coastal plains at the stretch's base level; bands add smooth noise relief clamped to
   their range; levels are smoothed so 4-neighbours differ by at most 2 except where a band says
   `cliffs`; coast tiles next to sea get `world.coast` faces where the land is above level 1.
3. Rivers: carve from source to mouth, levels forced non-increasing, flow written to `aux`.
4. Roads: A* over a cost grid (slope, rivers cost a bridge or ford, impassable forbidden except at
   `passes`) through each route's waypoints in order; paint paving, place milestones, stations
   and roadside kit at the given spacing on alternating sides; write graph edges and portals.
5. Country: terrain by stretch look and slope; fields and hamlets near roads every `every` tiles
   (a hamlet is 3–6 kit pieces around a yard, doors to a track joining the road); plants scattered
   by density, denser along rivers; mountain tops impassable.
6. Districts: one per stretch for land and one per sea, plus `<stretch>/road` along routes (so
   road traffic densities differ from fields), plus each seam band as its own region.
7. Validate (§3.5) and write `base.lcw` and `base.graph.json`.

Waypoint towns (Ostia/Portus, Brundisium, Delphi, Corinth, Delos, Ephesus, Sardis, Babylon, Susa,
Persian Gates, Pasargadae, …) are small authored layers like the cities, using their set's kit and
their landmarks from the city files' waypoint tables; routes meet them at their portals.

---

## 4. Engine architecture for the world

Built on what the foundation round committed: chunked `World` (32 × 32 chunks, per-chunk tallies,
items indexed by origin chunk), the per-chunk ground cache with an LRU slot budget, view-scaled
scene with a cached object region and the exact topological depth sort (`DepthSorter`), sprites
that carry their texture, tile size from the catalog, save format v2.

### 4.0 Reconciling the design documents

| Conflict or cost | Decision |
|---|---|
| `world.md` §7: buildable plot 20 × 20 inside a wall on a prebuilt headland; `living-corner.md`: a 40 × 40 home region opened in five stages ending at a road, wall and gate | **The 40 × 40 staged home region, exactly as `living-corner.md` designs it, is placed in the world** (§4.1). `world.md`'s plot (C 38..57, R 44..63) and its separate wall are dropped; the stage-4 wall and gate are the boundary |
| World size: `living-world.md` "up to 1024 × 512"; `world.md` 1280 × 448 | 1280 × 448 (grid 448 × 1280, 560 chunks). World pixel extents stay under 2^16 (about 55 000 × 27 600 px at 64 × 32), as `iso.hpp` assumes |
| `world.md` §14.1: chunks loaded and unloaded in a ring | Tile data is fully resident (≈ 7 MB). Streaming is for textures (atlas pages, ground cache slots), actors (tiers) and audio |
| `world.md` §10: `items.json`, `chunks/`, `paths.json`, `regions/<id>.json` | Layers (§2.4) and per-layer graphs (§2.5) so builders work in parallel; region files as `assets/regions/<id>.json` |
| `world.md` §9.2 influence fields from rects with blend margins | Weights from districts sampled around the camera (§4.6): same blend radii, no overlapping-rect rules |
| `world.md` §11 `landmark/<id>/…` keys and one-tile diagonal slices; §14.4 sprites up to 2400 × 1200 | Landmarks are catalog items; `base` split into rectangular **pieces** of at most 8 × 8 tiles (§1.3), which the existing rectangle sort handles |
| `world.md` §11 `walker/<kind>/<variant>/…` | `walker/<kind>/v<k>/<anim>_<facing>/f<n>` (§1.9) |
| Save: the engine's chunked v2 (absolute coordinates, `base`) vs `living-corner.md`'s v2 (`home` block, home-relative) | `living-corner.md`'s layout, numbered **3**, plus a `world` block (§2.7). The chunked v2 stays readable |
| `world.md` §3.3 "view rotation strongly recommended" | Out of the first version (§4.13); models built ready for it (§1.4) |
| `world.md` §13: flights under 200 tiles, a symbol travelling the route for longer ones | Eased flight up to 96 tiles inside one set; otherwise a short fade via the overview. The travelling symbol is nice-to-have |
| `living-world.md` §9.1: music crossfade over 8 tiles; `world.md` §9.2: music fades over the blend margin, silent stretches | `world.md`'s version (§4.6) |
| `world.md` §10: decorate zones in cities | Deferred: only the home region is editable in this version |
| `living-world.md` §1.2 liveliness probe: 10 simulated minutes at 4× per area kind | Default `ctest` runs a 2-game-hour probe on the fixture world; full probes per city run under `--bench` and gate the W6 tasks, not every build |
| Engine `kMaxFootprint = 8` | Items larger than 8 × 8 are also listed in every chunk they overlap (§4.2) |

### 4.1 The home region in the world

- **Placement:** grid origin **(40, 1200)**, size 40 × 40, i.e. world plan C 40..79, R 40..79,
  inside the corner region (C 0..95, R 0..111). Home `(x, y)` = grid `(40 + x, 1200 + y)`. Home
  `+x` is south, `+y` is west, so:
  - the **road** along home `y = 0` is the region's east side (C 79), running north–south; the
    **gate** at home (20, 1) is at C 78, R 60, facing east toward Rome;
  - **stage 0** (home x, y 20..39) is the south-west quarter (C 40..59, R 60..79), nearest the
    camera, exactly as `living-corner.md` R5.1 wants;
  - the **south-west rim** (home `y = 39`, C 40) faces the sea to the west: the west meadow's and
    the high wood's streams continue west as `world.river` to the coast and fall over the headland's
    sea cliff (the waterfall delight now uses the world's drop); the **south-east rim** (home
    `x = 39`, R 79) faces south: the far pond's creek runs south to the coast near R 100.
- **Levels:** the headland, the home region and the corner layer are world level 2 (flat inside
  the home region); the coast has a two-level `world.coast` cliff; the dell (C 88..103) steps down
  to level 1 with a ramp where the road crosses it.
- **The road out:** north from the gate along C 79 to a wayside shrine (C 79, R 20) and on to the
  world's north edge; south along C 79 to R 92, then east through the dell to Rome's Via Aurelia
  portal at plan (96, 120) (`rome.md` §2.5, c 0, r 96; this replaces `world.md` §5.3's (100, 96)).
  A track from (79, 92) runs west to the jetty (C 28..36, R 100..111) and its sea lane to Portus.
- **Composition:** the corner layer leaves the home rect transparent; the engine writes the home
  region from the save (or the starter scene) into the composed world last. Wild stages stay inside
  the home region as designed.
- **Editing:** build tools work only on open home tiles; anywhere else they refuse with the hint
  "This land belongs to the world" (a new string). Undo, conditions, wishes, nooks and visitor
  needs are evaluated over the home rect only (`living-corner.md` §2.1). Laeticia stays home.
- **No world data → today's island.** If `assets/world/world.json` is missing, the engine runs the
  40 × 40 floating island exactly as now, so every existing scripted test keeps working and the
  corner tasks never wait for the world.
- **Test:** unit: home↔grid mapping, editable-range refusal, conditions limited to the home rect;
  scripted: the home in the world at zoom 1 and 2 (shots), a build stroke crossing the boundary
  refused, save and reload keeping home-relative coordinates.

### 4.2 Loading and the resident world

- **At start:** parse `assets/catalog.json` and the set catalogs (ids must be unique; a clash is a
  load error naming both), every atlas **manifest** (JSON only, giving every key a `SpriteId`; the
  `u16` id space holds ≈ 15 000 keys), the geometry files, `world.json`, every layer and graph, the
  region files; compose (§2.4); apply the home; build graphs and next-hop tables (§4.10).
  Budget: ≤ 400 ms before the first frame on the owner's machine, logged by `--bench`.
- **Tile planes:** `World::Chunk` gains a `level` plane and a `district` plane beside `terrain`
  (3 B per tile). Terrain stays `u8`.
- **Big items:** an item whose footprint exceeds 8 × 8 is also referenced from a `big` list in
  every chunk it overlaps, and `forEachItemIn` visits those lists, so area queries stay local
  without widening every query by 24 tiles.
- **Landmark pieces** are a drawing concern: `World` holds the landmark as one item (occupancy,
  picking, slots, card); the scene expands it into its pieces from the geometry file.
- **Risks:** startup time with nlohmann on ≈ 3 MB of JSON (convert to structs once; measure);
  id clashes between catalogs (load error with both sources named).
- **Test:** unit: layer parser on the §2.4 hex example and on truncated and oversized files
  (rejected without a crash); composition rule (transparent cells, dropped items); big items found
  by area queries from any overlapped chunk.

### 4.3 Elevation

- **Data:** the level byte (§2.4). Level height `tile.level` px.
- **Drawing ground:** the ground cache draws each chunk's tiles in diagonal-row order, each tile's
  top raised by `level × tile.level` and its `+x` and `+y` faces stacked down to the neighbour's
  level (material from `aux` → terrain `faces`). Slot height grows by the chunk's maximum level.
- **Occluders:** a raised tile can hide things behind it that are lower. Tile `Q` hides tile `P`
  when `P` lies behind it (`P.x ≤ Q.x`, `P.y ≤ Q.y`), `ΔL = level(Q) − level(P) > 0` and the row
  distance `(Q.x − P.x) + (Q.y − P.y) ≤ ΔL + 1` (beyond that `Q` is drawn lower on screen than
  anything standing on `P`). When the scene builds its object region it marks every `Q` that hides
  a walkable tile or a tile holding an item, and adds `Q` (top and faces) to the depth sort as a 1 × 1
  element. Everything else about ground stays in the cache. On real maps this is a thin band along
  the back of hills (the Acropolis, the Capitol, the Palatine); worldgen's V11 keeps it thin.
- **Items and actors** are drawn at their tile's level; actors on a stair or ramp interpolate height
  along its axis. Walkers change level only along stair and ramp edges of the graph or across stair
  tiles in the grid search.
- **Picking:** for `L` from 15 down to 0, take the tile under the cursor shifted down by
  `L × tile.level` px; among tiles whose level is `L` (or whose stair height covers it), the visible
  one is the hit with the largest `x + y`. A face picks the tile it hangs from. 16 lookups.
- **Risks:** occluder counts on rough relief (worldgen smooths and V11 warns); slot memory on
  mountains (taller slots; ground budget covers it); stairs drawn over faces (the stair sprite must
  cover the face, §1.6, checked in art previews).
- **Test:** unit: occluder set of a fixture hill against a brute-force reference (render both into
  a small buffer and compare coverage); picking at faces, plateaus and stairs; stair height;
  walkability across levels. Scripted: a walker passing behind a 6-level hill and climbing a stair
  (shots). Bench: a mountain view keeps frame time inside §4.14.

### 4.4 Depth order with landmarks, occluders and pages

- **Elements:** items (pieces expanded), occluder tiles, actors. Each has a footprint rectangle and
  a screen box; `DepthSorter` orders them as today. Walk-run pieces carry a flag: on a tie with an
  actor standing on their tiles, the actor goes first (§1.3 rule 2).
- **Page-aware tie-breaking:** among elements whose predecessors are all drawn, prefer one on the
  texture page already bound before falling back to the depth key (a second key in the heap).
  This keeps page switches, and so draw calls, low when a city view mixes kit, landmarks, actors
  and the `world` page.
- **Static and moving parts:** the static order (items, pieces, occluders) is rebuilt only when the
  world changes or the view leaves the cached region, as today. Each frame, actors in view (≤ 120)
  are merged into it: an actor's constraints are only against static elements whose screen boxes
  overlap its own (a `ScreenGrid` query), so it is inserted after the last element behind it and
  before the first in front; actors overlapping each other sort by depth key.
- **Occluder fade:** items with `occluder: true` whose screen box covers the cursor or a followed
  actor that is behind them in the order are drawn at 35 % alpha (a vertex colour, no extra pass).
- **Risks:** cycles among large pieces (broken by the depth key, as today; pieces ≤ 8 × 8 keep them
  rare); the per-frame merge when many actors overlap one landmark (bounded by the 120 on-screen cap).
- **Test:** unit: a colonnade fixture (column pieces, walk runs) with an actor at every walk tile
  checked against a voxel reference order; page-aware sorting produces a valid order and fewer
  switches on a fixture; actor merge equals a full re-sort on random scenes. Scripted: walkers
  between the Apadāna's columns and under its portico (shots). Bench: draw calls ≤ 40 on a full
  city view.

### 4.5 Atlas pages by set

- **Data:** pages and manifests (§1.2); `world.json` regions name their set.
- **Approach:** the atlas keeps every manifest from the start; textures are per page with states
  unloaded → loading → resident. The **needed sets** are `home`, `world` and the sets of the regions
  found when sampling the district plane every 8 tiles over the view grown by 64 tiles. A loader
  thread decodes PNGs to surfaces (and computes luma, alpha centroids and the 1-bit hit mask); the
  main thread uploads at most one page per frame. Sets not needed for 10 s are evicted, oldest
  first, when over budget (320 MB of pages; in practice home + world + one city set).
- **Missing page at draw time:** the sprite is skipped for that frame (one debug log per page);
  nothing crashes and no placeholder flashes. In `--headless` and `--script` runs loading is
  synchronous, so screenshots are reproducible.
- **Risks:** an upload hitch of a 64 MB page (one per frame, mostly hidden by the 64-tile prefetch
  and by fast travel's fade); memory at seams where two city sets meet (seams are far apart: at most
  one city set is ever needed outside the Sardis haze, where both `athens` and `parsa` load).
- **Test:** unit: needed-set computation and eviction order as pure functions; scripted: a pan from
  the corner into Rome with `expect page_resident rome` and shots with no missing sprites; bench:
  the worst frame during a page load reported (`--renderer opengl`).

### 4.6 Region themes and cross-fades

- **Weights:** each frame, sample the district plane on a 9 × 9 grid at 8-tile spacing around the
  camera centre; each sample adds `smoothstep(1 − d / radius)` to its region, `radius` by region
  kind (city 32, town 12, stretch and home 24, seam 16); normalise; low-pass with a 1 s time
  constant (reset on fast travel). 81 lookups.
- **Grading, haze, sky:** weighted mix of the regions' keyframes, then today's clock grading.
- **Weather:** natural weather comes per region from `living-world.md` W3 cells; a region's weather
  kinds and climate come from its region file.
- **Ambience:** each region's beds play at `weight × level`; zones and emitters are positional
  (§4.12); seams duck all beds by 6 dB and add their drone by weight.
- **Music:** the **music region** is the city or the home region with weight > 0.5. When it changes,
  the old piece fades out over 4 s; the new one starts at a phrase boundary with a 4 s fade-in;
  stretches have none. The home region keeps its stems logic.
- **Risks:** weight flicker at boundaries (low-pass and the 0.5 threshold with a 0.1 hysteresis
  band for music and captions); decoding several beds at once (beds are short loops, decoded once,
  ≤ 6 playing).
- **Test:** unit: weights on fixture district maps, music state machine, hysteresis; scripted: a
  camera path across a seam logging weights and captured mixer gains (the mixer capture exists).
- **Budget:** ≤ 0.05 ms per frame.

### 4.7 Overview map and fast travel

- **Overview:** `assets/world/overview.png` (worldgen, §3.6), drawn full-screen in the glass UI with
  pan and zoom; markers from `world.json` with `ui/marker_<icon>` sprites; the live home thumbnail at
  the home marker; time-band labels and journal progress ("23 of 40 found") from the region files.
  Opened with `M`, the dock button, or zooming out past the last level.
- **Fast travel:** clicking a marker or land converts north-up map pixels to plan to grid. Within
  96 tiles and one set: an eased camera flight (1.5 s, ease-in-out, zooming out mid-way). Otherwise:
  fade to the map if not already there, pulse the destination while its set loads and its chunks
  materialise (`living-world.md` §7.4), fade in (≈ 1.2 s total, skippable). The animated symbol on
  the route is nice-to-have. Waypoint towns become clickable once visited; cities and home always.
- **Test:** scripted: open the map, click the Pārsa marker, shots before and after, `expect region
  parsa`; unit: map↔grid conversion, flight curve, the choice between flight and fade.

### 4.8 Era captions at the seams

- When the dominant region's `time` differs from the last captioned one (with the hysteresis of
  §4.6), the region file's `caption` fades in at the top for 3 s; a town adds its name below. The
  first seam crossing also shows the one-line explanation once (`world.flags`). Seams play a soft
  chime (an effect in the `world` audio set).
- **Test:** scripted shot at a seam; unit: caption trigger sequence on a camera path.

### 4.9 Figures, landmarks, cards and the journal

- **Hover and click:** actors are picked by sprite box; landmarks and items by their pieces' 1-bit
  hit masks, so clicking a column picks the Apadāna. Hover shows the name; click opens the card
  (glass panel: title, epithet, text, chain strip, Follow) from the region file.
- **Journal:** clicking or seeing (hovered for 1 s, or a figure in view during its event) records
  `landmark:<id>`, `figure:<id>`, `delegation:<id>`, `chain:<id>` in `world.journal[region]`; the
  sketchbook gains a tab per visited region (`living-corner.md` §13).
- **Test:** scripted: hover and click the Apadāna (card shot), a figure card, journal saved and
  restored; unit: hit-mask picking on pieces, journal de-duplication.

### 4.10 Actors at scale

`living-world.md` W4–W5 as specified there (tiers on 32 × 32 chunks, districts, materialisation,
tokens, road graphs with next-hop tables, cached A*, flow fields, follow camera, time speed, the
liveliness probe), with these concrete inputs from this design:

- kinds from set catalogs; districts from the district plane; densities from region files;
- the road graph is the union of layer graphs with portals merged; next-hop tables per region for
  its `dest` nodes, built at load (≈ 64 Dijkstras on ≤ 2 000 nodes per region, a few ms in all);
- slot geometry from the geometry files joined with catalog slot behaviour;
- the fixture world for tests is a worldgen layer set committed under
  `tools/worldgen/fixtures/testworld/` (a 256 × 256 world: two towns, a road with a stair, a sea lane,
  a field, a 6-level hill), loaded with `--world <dir>`.

Budgets and tests are `living-world.md` §7.5 and §10.

### 4.11 Ships, caravans and couriers on long routes

- **Tokens** (`living-world.md` §7.3): a lane token's position is a function of time along its lane;
  a route token (caravan, courier, mule train) moves along a polyline computed at load as the graph
  path between two `dest` nodes (the Royal Road from Sardis to Pārsa is one such path, ≈ 400 tiles).
- **Seams:** lanes and routes end at seam ports inside the mist band; tokens fade out over 3 s there
  and their phase wraps (Roman ships never reach Corinth).
- **Drawing:** a token entering a Warm chunk becomes a full actor (with its group); ships sort by
  their catalog `size` oriented to the heading; wakes are fx.
- **Test:** unit: token positions and port arrivals at given times, seam wrap; scripted: a ship
  arriving at Portus and mooring (shots). **Budget:** ≤ 256 tokens at 1 Hz, ≤ 0.02 ms per frame.

### 4.12 Positional ambience

- Zones (region-file rects) and emitters (items with loops tied to slot states, e.g. a fountain,
  a smithy while worked) play with the pan and distance gain of `living-world.md` §9.2; one-shots
  from animation frame events and steps. Budgets: 12 one-shots, 8 loops, farthest dropped first.
- **Test:** unit: pan and gain maths, budget drops; scripted: captured mixer output while panning
  past a fountain shows the expected gain curve.

### 4.13 View rotation: out of the first version

Cost if added later: art renders `r1..r3` for every landmark (≈ 3 × the landmark atlas: Rome
alone would grow from 3 to about 7 pages) and re-cuts pieces per rotation; the engine abstracts the
grid↔screen mapping behind a view rotation, recomputes terrain and item masks per view (masks are
grid-relative), flushes the ground cache on rotate, rotates picking, faces (which edges are visible
changes) and backdrops; worldgen previews and QA quadruple. One engine task, one art task per set
and ≈ 250 MB more of pages. The hidden façades are covered by cards meanwhile. Models are built
ready (§1.4), so nothing is lost by waiting.

### 4.14 Budgets

| Item | Budget |
|---|---|
| CPU per frame, update + draw submission (`CLAUDE.md`) | ≤ 2 ms: actors and simulation 0.6, gather and cull 0.2, sort merge 0.25, sprite emission 0.5, ground cache draw 0.1, themes, audio and streaming bookkeeping 0.1, UI 0.15 |
| Static depth sort rebuild (view leaves the cached region) | ≤ 3 ms, at most once every 30 frames while panning; ≤ 1 200 items per chunk (V10) |
| Draw calls, busiest city view at zoom 1 | ≤ 40: ground slots 4, shadows 2, depth pass ≤ 16, glow 2, UI and blur ≤ 16 |
| Startup to first frame | ≤ 400 ms plus the visible pages |
| CPU memory for the world | ≈ 15 MB (§2.8) |
| GPU memory | pages ≤ 320 MB, ground cache 96 MB, overview 9 MB, targets as today |
| Page loads | one upload per frame, prefetched 64 tiles ahead |

### 4.15 Headless testing

Everything above runs under the dummy video driver. New script commands (documented in
`src/app/script.hpp` by the engine): `world <dir>` (load a world, default the shipped one),
`camera <x> <y> <zoom>` in grid tiles, `travel <region>`, `expect region <id>`,
`expect page_resident <set>`, `expect lively`. New bench modes: `--bench --world` (camera sweep over
the fixture world, reporting frame times, draw calls, page loads), `--bench --region <id>` (busiest
hour in one region).

---

## 5. Work plan

### 5.1 How to read it

- One task = one agent, roughly 1–3 hours. **Lanes:** ENG (engine: `src/`, `tests/`; one at a
  time), ART (`tools/artgen`, `assets/atlas*`), AUD (`tools/audiogen`, `assets/audio`), WG
  (`tools/worldgen`, `assets/world`, `assets/regions`), DES (set catalogs; contracts, so the
  orchestrator applies or approves), QA (read-only runs and reports). Two or three agents at once:
  the ENG task plus one or two others.
- **M** must-have, **N** nice-to-have (cut first). Every task ends with a warning-free build and
  `ctest` passing under `release` and `asan` where it touches code, and with its previews or shots
  reviewed and its scratch output deleted.
- Order: the ENG column is the critical path and runs top to bottom; the others start as soon as
  their prerequisites are met. Milestones: **M1** home in the world (visible early: home, coast,
  road, Ostia/Portus, themed, scrollable); **M2** the world engine; **M3** Pārsa lit (pilot city:
  the smallest, most complete file, and the §1.13 example); **M4** Athens lit; **M5** Rome lit;
  **M6** the land and sea between; **M7** life everywhere. Each city can be lit independently of
  the others once M2's engine tasks exist; until then its art and layout are checked in previews.

### 5.2 The tasks

| ID | Lane | Task | Needs | Deliverable and acceptance | M/N |
|---|---|---|---|---|---|
| E1 | ENG | Catalog v2 and condition evaluator (`living-corner.md` task A items 1–2) | — | parse and validate every v2 section; conditions with waiting mode; task A's unit tests for these items | M |
| E2 | ENG | Saves version 3: profile, worlds folder, home block, `world` block, migration from v1 and v2, thumbnails (task A item 3, §2.7) | E1 | fixture migrations (v1 and v2 → v3), round trip, slug rules; never overwrites the old file | M |
| ART0 | ART | artgen for sets: `--set`, set catalogs or drafts, pages ≤ 4096 with the §1.2 grouping, geometry file (§1.10), piece cutter (§1.3), walk-tile and headroom validator, per-level edge faces, `tile.level` | §1 | a toy set (one 10 × 10 landmark with a portico, a house, a walker) builds deterministically; validator catches a column on a walk tile; pieces reassemble to the unsplit render pixel for pixel | M |
| WG0 | WG | worldgen core: DSL (§3.3), rasteriser, layer and graph writers and readers, composition, validators V1–V13, bible parser, previews, `build.sh` | §2, §3 | the §2.4 hex example round-trips; a toy layer validates and previews; deliberate errors trip each check; compile twice gives the same bytes | M |
| D1 | DES | `world` set catalog: terrain, edges, stairs and ramps, animals, birds, goods, shared walker kinds, fishing boat, fx, `art` block | §1 | `assets/sets/world/catalog.json` passes artgen's and worldgen's catalog checks | M |
| D2 | DES | `parsa` set catalog from `persepolis.md` §3 and §6 (ids mapped by §1.1, landmark footprints in grid axes, slots, emitters, actors with poses) | D1 | every M row of the Pārsa asset tables present; reviewed by the orchestrator | M |
| D4a | DES | `rome` set catalog, part 1: terrain, plants, edges, Latium and Ostia/Portus kit and landmarks | D1 | as D2 for those rows | M |
| ART1 | ART | world terrain and water: sea (masks, 4 frames), shallows, shore foam, river and flow, sand, steppe, alluvium, rock, snow, marsh, road earth, field, scree; edges rock, earth, snow, coast; generic stairs and ramps | ART0, D1 | `world.0` page; artgen previews of a coast with a 2-level cliff, a river delta and a stair | M |
| WG1 | WG | world plan and base v0: coasts, sea depth bands, relief bands, rivers, stretch and seam districts, `world.json` with every region, overview v0 | WG0, D1 | `base.lcw` validates; `world.png` shows the Mediterranean shape at the `world.md` scale; landmarks' region rects free for city layers | M |
| WG2 | WG | corner layer (borderland, headland cliffs, streams to the sea, wayside shrine, dell seam, road and jetty, §4.1) and the Ostia/Portus layer; the road from the home gate to Rome's portal; the jetty lane to Portus | WG1, D4a | both layers validate (V1–V12); close-ups of the gate, the jetty, the dell and Portus | M |
| ART5 | ART | Latium and Ostia/Portus art: `rome` terrain set, plants, milestone, roadside tombs, farm kit, Portus harbour pieces, lighthouse, quay with moorings | ART0, D4a | `rome.0` page part; previews of a stretch of road with pines and tombs and the harbour | M |
| AUD1 | AUD | world beds and seam sounds: open sea, coast, Latium countryside, harbour, mist drone, seam chime, gull and wave one-shots | §2.6 | files listed in the world set catalog; validator passes loudness and loop rules | M |
| E3 | ENG | World v0 (§4.1, §4.2): load world, layers, graphs (parsed), set catalogs and all their pages (no streaming yet), composition, big items, the home placed with its editable range, camera over the world, island fallback | E2, WG1, WG2, ART1 (fixtures until then) | scripted: the home in the world at zoom 1 and 2, the road to Rome's edge, Portus (shots); refusal outside the home; load ≤ 400 ms; frame budget on the full world | M |
| E4 | ENG | Themes and captions (§4.6, §4.8): weights, grading, beds by weight, music handover, seam ducking, captions | E3, AUD1 | unit tests of §4.6; scripted camera path across the dell with shots and logged weights | M |
| QA1 | QA | **M1 acceptance**: the home in the world | E4, ART5 | report with shots at fixed cameras, a save and reload, frame timings, a list of defects routed to owners | M |
| E5 | ENG | Unlocks, drawer, wishes, tray, ribbon (task A items 4–5) | E1 | task A tests for these items | M |
| E6 | ENG | Sketchbook, rare visitors, nooks (task A items 6–8) | E5 | task A tests for these items | M |
| E7 | ENG | Land stages inside the world-placed home (task A item 9; R5.7's world column) | E3, E6 | stage 1 opening in the world (shots mid-wave and after); streams continue into the world | M |
| E8 | ENG | Calendar, seasons, growth, harvest (task A items 10–11) | E7 | task A tests for these items | M |
| E9 | ENG | Music stems and tuned notes (task A item 12) | E8 | task A tests for this item | M |
| B1 | ENG | Front door and tour (task B items 4–5) | E9 | task B tests for these items | M |
| ART2 | ART | walker rig, pose library (§1.9), shared kinds (traveller, shepherd, farmer, child, each 3 variants), `carry_at`, goods | ART0, D1 | sprite sheets of every pose both facings; `carry_at` previews with goods in hand | M |
| ART3 | ART | world animals (sheep, goat, dog, ox, donkey, mule, horse, camel), birds (crane, swift, gull, pigeon, stork), fish jump, dolphin, fishing boat, whitecap, wake, `ui/marker_*` | ART0, D1 | sheets and a harbour preview | M |
| WG3 | WG | fixture test world (§4.10) under `tools/worldgen/fixtures/testworld/` | WG0, ART1 | validates; previews; used by E10 and W4 tests | M |
| E10 | ENG | Elevation (§4.3): levels in the ground cache, faces, occluders, picking, stairs, actor heights | E3, WG3 | §4.3 tests; scripted walker behind a hill and up a stair | M |
| E11 | ENG | W1 Actors (`living-world.md` §10) | E9 | W1's tests | M |
| E12 | ENG | W2 Laeticia and goods-lite | E11 | W2's tests | M |
| E13 | ENG | W3 Events, wind, weather, sound | E12 | W3's tests | M |
| ART-P1 | ART | Pārsa terrain, plants, `parsa.ashlar` edges with outfalls and merlon cap, relief stairs | ART0, D2 | `parsa` previews: terrace face with the plain in front | M |
| ART-P2 | ART | Pārsa kit buildings and props (`persepolis.md` §3.3, M rows) | ART-P1 | sheets; a town preview | M |
| ART-P3 | ART | Pārsa landmarks I: great stairway, Gate of All Lands, Apadāna with its two stairs, Tripylon (§1.13) | ART-P1 | pieces validate; close-up of the forecourt and portico with walkers between columns (artgen preview) | M |
| ART-P4 | ART | Pārsa landmarks II: Tačara, Hadiš, Hall of a Hundred Columns site, Treasury, Harem, Garrison | ART-P3 | as ART-P3; the terrace silhouette from the plain | M |
| ART-P5 | ART | Pārsa landmarks III: quarry, fortification kit, road station, pavilion, Naqsh-e Rostam cliff (M); Ka'ba, paradise gate, cistern, south stores (N) | ART-P3 | as ART-P3 | M |
| ART-P6 | ART | Pārsa walkers and figures (§3.6 M kinds, Xerxes and the named people), 8 delegation sets | ART2, D2 | sheets of every kind and pose; delegation line preview | M |
| WG-P1 | WG | Pārsa layout I: terrace, landmarks, forecourt, town, station, garden, fields, channels (§3.4 grown to the whole region) | WG1, D2 | V1–V12 pass, V4 with every M landmark of §2.3; close-ups of forecourt, terrace, town | M |
| WG-P2 | WG | Pārsa layout II and life: Naqsh-e Rostam satellite, qanat (N), region file (theme, districts, populations, figures, events P1–P12, chains C3–C6, cards from §4.3 of the city file) | WG-P1 | region file validates against catalogs and layout; cards present for every landmark and figure | M |
| AUD2 | AUD | Pārsa music (day, night), beds (plain, channels, terrace), effects (horn, chant, chisel, camel, harp phrase) | D2 | loudness and loop validation; files in the set catalog | M |
| E14 | ENG | Landmarks in the depth order (§4.4): pieces, walk-run ties, page-aware sort, actor merge, occluder fade | E10, E13, ART-P3 | §4.4 tests; scripted walkers in the Apadāna portico; ≤ 40 draw calls on the Pārsa terrace | M |
| E15 | ENG | Atlas streaming by set (§4.5) | E14 | §4.5 tests; pan corner → Rome edge with no missing sprites; page-load spike reported | M |
| E16 | ENG | Cards, hover, journal, region sketchbook tabs (§4.9) | E14 | §4.9 tests; Apadāna and Xerxes cards (shots) | M |
| E17 | ENG | Overview and fast travel (§4.7) | E15, WG4 | §4.7 tests; travel to every marker in a script | M |
| QA2 | QA | **M3 acceptance**: Pārsa lit | E16, ART-P1..P6, WG-P2, AUD2 | V4 report, close-up review against `persepolis.md` §3.1 facts, walk-through shots, card text check, frame timings at the terrace | M |
| WG4 | WG | routes and country v1: every `world.md` §5.3 route with milestones, stations, hamlets, fields; styled overview | WG1, ART5 | base validates; Via Appia and Royal Road close-ups; overview art reviewed | M |
| D3 | DES | `athens` set catalog | D1 | as D2 | M |
| D4b | DES | `rome` set catalog, part 2: city kit, landmarks, actors | D4a | as D2 | M |
| ART-A1 | ART | Athens terrain, plants, limestone and marble edges, stairs | D3 | previews | M |
| ART-A2 | ART | Athens kit (`athens.md` §3.3 M rows) | ART-A1 | sheets; Kerameikos street preview | M |
| ART-A3 | ART | Acropolis landmarks: Parthenon, Propylaia, Old Temple and Erechtheion area, Nike bastion, Promachos, Chalkotheke, Brauronion, Pandroseion | ART-A1 | pieces validate; the approach close-up | M |
| ART-A4 | ART | Agora and Kerameikos landmarks: stoas, Hephaisteion, tholos, bouleuterion, altar of the Twelve Gods, fountain house, Dipylon and Sacred Gate | ART-A1 | as ART-A3 | M |
| ART-A5 | ART | the rest: theatre, Odeion, Pnyx, walls and Long Walls kit, Piraeus harbour and shipsheds, Olympieion, Lyceum (N), quarry | ART-A3 | as ART-A3 | M |
| ART-A6 | ART | Athens walkers and figures | ART2, D3 | sheets | M |
| ART-A7 | ART | trireme, Greek merchant ship, Athens carts | ART0, D3 | sheets; a Piraeus preview | M |
| WG-A1 | WG | Athens layout I: Acropolis (levels 2–11), Agora, Kerameikos, walls, Panathenaic Way | D3, WG1 | V1–V12; close-ups | M |
| WG-A2 | WG | Athens layout II and life: Pnyx and hills, Ilissos, Piraeus, Long Walls, region file (events A1–A10, chains C7, C8, C12) | WG-A1 | as WG-P2 | M |
| AUD3 | AUD | Athens music, beds (agora, cicadas, sea wind on the Acropolis), effects | D3 | validation | M |
| QA3 | QA | **M4 acceptance**: Athens lit | E16, ART-A1..A7, WG-A2, AUD3 | as QA2 | M |
| ART-R2 | ART | Rome city kit (`rome.md` §3.3 M rows) | ART5, D4b | sheets; a Subura street preview | M |
| ART-R3 | ART | Forum and Capitol landmarks | ART5, D4b | pieces validate; Forum close-up | M |
| ART-R4 | ART | Palatine, Circus Maximus, Velia, Colosseum valley | ART-R3 | as ART-R3 | M |
| ART-R5 | ART | Campus Martius: Pantheon, theatres, baths, Saepta, stadium | ART-R3 | as ART-R3 | M |
| ART-R6 | ART | imperial fora, Trajan's Markets, Quirinal | ART-R3 | as ART-R3 | M |
| ART-R7 | ART | Tiber, bridges, Tiber Island, Emporium and horrea, Aventine, Aqua Claudia, Transtiberim | ART-R3 | as ART-R3 | M |
| ART-R8 | ART | Rome walkers and figures | ART2, D4b | sheets | M |
| ART-R9 | ART | Roman merchantman, barge, carts, carriage, litter | ART0, D4b | sheets | M |
| WG-R1 | WG | Rome layout I: Forum, Capitol, Palatine, Velia, Colosseum valley | D4b, WG1 | V1–V12; close-ups | M |
| WG-R2 | WG | Rome layout II: Campus Martius, Quirinal, Subura, imperial fora | WG-R1 | as WG-R1 | M |
| WG-R3 | WG | Rome layout III and life: river, Transtiberim, Aventine, Emporium, Caelian, Via Appia start, region file (events R1–R13, chains C9–C12) | WG-R2 | as WG-P2 | M |
| AUD4 | AUD | Rome music, beds (forum crowd, fountains, cart rumble at night), effects | D4b | validation | M |
| QA4 | QA | **M5 acceptance**: Rome lit | E16, ART-R2..R9, WG-R3, AUD4 | as QA2 | M |
| ART-P7 | ART | Persian-time waypoints: Pasargadae, Persian Gates, Susa, Babylon (Ishtar Gate, ziggurat), Euphrates crossing, Halys gates, Sardis (M); Gordion, Sidon (N); camel caravan, reed boat, Phoenician ship | ART-P2 | pieces validate; sheets | M |
| ART-A8 | ART | Greek waypoints: Eleusis, Delphi, Corinth with the diolkos, Delos, Ephesus (M); Olympia, Sparta, Corcyra, the Academy (N) | ART-A2 | as ART-P7 | M |
| ART-R10 | ART | Roman waypoints: Brundisium, Alban Mount (M); Tibur, Capua, Beneventum (N) | ART-R2 | as ART-P7 | M |
| WG-P3 | WG | Persian waypoint layers and the Royal Road stations | WG4, ART-P7 | each layer validates; road continuous Sardis → Pārsa | M |
| WG-A3 | WG | Greek waypoint layers | WG4, ART-A8 | as WG-P3 | M |
| WG-R4 | WG | Roman waypoint layers | WG4, ART-R10 | as WG-P3 | M |
| WG-S | WG | seas and lanes: every sea lane with ports and seam ports, token lists in the stretch region files | WG4 | lanes connect ports; seam ports inside mist bands | M |
| AUD5 | AUD | stretch beds: Apennines, Greek country, Anatolian steppe, Mesopotamia, Zagros, Iranian plateau, Syrian steppe | §2.6 | validation | M |
| ART-W4 | ART | backdrops behind the north and east edges with night and winter looks | ART0 | previews | N |
| QA5 | QA | **M6 acceptance**: a tour of the whole world | E17, WG-P3, WG-A3, WG-R4, WG-S | fast travel to every marker; a continuous pan Rome → Pārsa at zoom 1 with frame timings, page loads and memory | M |
| E18 | ENG | W4a Scale: tiers, districts and densities, materialisation, time speed and Hold | E14, WG3 | W4's tests for these parts | M |
| E19 | ENG | W4b Paths: graphs from layers, next-hop tables, cached A*, flow fields, follow camera, liveliness probe | E18 | W4's tests for these parts; probe on the fixture world | M |
| E20 | ENG | W4c Tokens: lanes, routes, ships, caravans, couriers, seam fades (§4.11) | E19 | §4.11 tests; ship arriving at Portus (shots) | M |
| E21 | ENG | W5 Chains and touches | E20 | W5's tests | M |
| AUD6 | AUD | life effects: goods changes (wood, cloth, clay, stone), vendor calls, hooves, cart rumble, ship bell, thunder | E13 | validation | M |
| W6a | WG | Pārsa life tuning: populations, schedules, events and chains against the liveliness probe at the busiest hour | E21, QA2 | `--bench --region parsa` probe passes; every event fires in a 2-day 4× run | M |
| W6b | WG | Athens life tuning | E21, QA3 | as W6a | M |
| W6c | WG | Rome life tuning, plus seas and roads | E21, QA4, WG-S | as W6a | M |
| B2 | ENG | Builder comforts (task B item 6) | B1 | task B tests for this item | M |
| B3 | ENG | Postcards (task B item 7) | B1 | task B tests for this item | M |
| E22 | ENG | Travel symbol on the overview route during long fast travel | E17 | scripted shots | N |
| E23 | ENG | Decorate zones in cities (an editable rect per city with its own menu, saved like the home) | E17 | — (to be specified) | N |

### 5.3 Lane queues

- **ENG** (one at a time): E1 → E2 → E3 → E4 → E5 → E6 → E7 → E8 → E9 → B1 → E10 → E11 → E12 →
  E13 → E14 → E15 → E16 → E17 → E18 → E19 → E20 → E21 → B2 → B3 (→ E22, E23).
- **Beside E1–E4** (making M1): ART0, WG0, D1 first; then ART1, WG1, D4a, AUD1; then WG2, ART5,
  WG3. M1 is visible after E4, roughly the fourth engine task.
- **Beside E5–E13**: D2, ART-P1…P6, WG-P1, WG-P2, AUD2, ART2, ART3, WG4, D3, D4b. Pārsa's art and
  layout are finished and checked in previews before E14 makes the engine draw them.
- **Beside E14–E21**: QA2, then Athens (D3 → ART-A* → WG-A* → AUD3 → QA3), then Rome, then the
  waypoints, seas and stretch beds, then W6a–c as each city's QA passes.

### 5.4 Cut and deferred

Cut from this version: the 90° view rotation (§4.13); decorate zones in cities (E23, N); the
travelling symbol (E22, N); backdrops (ART-W4, N); the N waypoints (Tibur, Capua, Beneventum,
Olympia, Sparta, Corcyra, the Academy, Gordion, Sidon) and N stretches (Thrace, the Levant coast,
the Persian Gulf get base-layer land and sea only, no set pieces); 15 of the 23 delegation sets;
the qanat. Replaced by cheaper designs: chunk streaming of tile data (everything resident),
diagonal slices (rectangular pieces), giant single sprites (pieces ≤ 8 × 8), rect influence fields
(district sampling), long eased flights (fade via the overview), per-region chunk files (layers).

**Too expensive as written, and the cheaper version:** Rome's 70 landmarks would need about four
pages and seven art tasks of landmarks alone; D4b should mark the city file's nice-to-have
landmarks N and apply `scale` below 1 to the largest complexes (as `rome.md` already does for the
Colosseum and Circus), keeping Rome within three pages. The liveliness probe at full length in
every `ctest` run would cost minutes; it runs short by default and in full under `--bench`.

---

## 6. Contract changes

Written out for the orchestrator to apply. Nothing here is applied by this document.

### 6.1 `CLAUDE.md`

**Layout and ownership table.** Replace the art row and add rows:

```markdown
| `tools/artgen/`, `assets/atlas.png`, `assets/atlas.json`, `assets/atlas/` | Sprite generator and its output: the home page, set pages, manifests, geometry | art |
| `tools/worldgen/worldgen/`, `tools/worldgen/plan/`, `tools/worldgen/fixtures/`, `tools/worldgen/build.sh`, `assets/world/world.json`, `assets/world/layers/base.*`, `assets/world/overview.png` | World authoring tool, world plan, base layer, overview, test world | worldgen core |
| `tools/worldgen/regions/<layer>/`, `assets/world/layers/<layer>.*`, `assets/regions/<region>.json` for the regions in that layer | One authored place: layout, graph, life and text | the builder of that layer (one agent per layer) |
| `assets/sets/<set>/catalog.json` | Set content contracts | orchestrator, or the agent whose brief says so |
| `docs/design/sets/` | Draft set catalogs | design |
```

**Machine courtesy**, add to the list of lanes that run beside the engine lane: "world building
(`tools/worldgen`, `assets/world`, `assets/regions`), one agent per layer". Add: "Worldgen previews
go to `out/worldgen/` and are deleted when done."

**Code standards**, change the last bullet to: "All user-visible strings and tunable numbers live
in one place each; a region's text lives in its file under `assets/regions/`."

**Game rules (v0)**, add after the first bullet: "When `assets/world/world.json` exists, the home
region is placed at grid (40, 1200) of a 448 × 1280-tile world (`docs/design/world-tech.md` §4.1);
only its open tiles are editable, and everything else is prebuilt and never saved."

**Content contract**, add after the Audio subsection:

```markdown
### Sets, ids and the world

Design and formats: `docs/design/world-tech.md`. In short:

- Content outside the home set lives in **sets** (`world`, `rome`, `athens`, `parsa`), each with a
  catalog `assets/sets/<set>/catalog.json` (same schema as `assets/catalog.json` plus `actors`,
  `goods` and `art`). `assets/catalog.json` lists them in `sets`. Every id outside the home set is
  `<set>.<name>`; home ids have no dot. Ids are unique across all catalogs.
- A set's art is on pages `assets/atlas/<set>.<n>.png` + `.json` (today's manifest schema, at most
  4096 × 4096 each) and its geometry in `assets/atlas/<set>.geom.json` (pieces, walk tiles, slot
  spots, emitters, carry points, per rendered rotation). Catalog slots give behaviour, geometry
  files give positions; both must cover each other.
- Footprints over 8 × 8, or with walk tiles, are split into rectangular **pieces** of at most
  8 × 8 tiles (`…/r<k>/p<i>/f<n>`), depth-sorted as items. Walk tiles carry nothing lower than
  `1.5 × tile.h` px above their floor. Landmarks are modelled in grid axes and use `r0`.
- Elevation: integer levels 0..15, `tile.level` px each; faces `edge/<material>_<se|sw>/v<n>`, one
  level tall, stacked. Stairs and ramps are items with `rise` and `axis`, footprint at the lower level.
- The world is `assets/world/world.json` plus layer files (`layers/<id>.lcw`, binary, composed in
  order) and graphs (`layers/<id>.graph.json`); region life, theme and text are
  `assets/regions/<region>.json`. All are generated or validated by `tools/worldgen`.
```

**Atlas key table**, add rows:

```markdown
| `item/<id>/<layer>/r<k>/p<i>/f<n>` | Piece `i` of a split item (`base` only) |
| `item/<id>/<state>/<variant>/f<n>` | A slot state drawn instead of `base` |
| `edge/<material>_<se\|sw>/v<n>` (`/top`, `/v<n>/f<k>`) | One level of face under a tile edge, a cap band, an animated face |
| `terrain/world.sea/foam/m<mask>/f<k>`, `terrain/world.river/flow_<n\|e>/f<k>` | Shore foam (mask = land neighbours), river flow (mirrored for w, s) |
| `walker/<kind>/v<k>/<anim>_<front\|back>/f<n>` (`/glow/f<n>`) | Anonymous people on the shared rig |
| `figure/<id>/<anim>_<front\|back>/f<n>` | Named people |
| `ship/<kind>/v<k>/<anim>_<front\|back>/f<n>`, `cart/…` | Ships, carts with their animals |
| `goods/<id>`, `goods/<id>/s<1-3>` | Carried goods, slot stacks |
| `backdrop/<id>/<day\|night\|winter>/v<n>` | Strip segments behind the north and east world edges |
| `weather/<kind>_v<n>`, `ui/marker_<icon>` | Weather sprites; overview markers |
```

**Running**, add:

```sh
tools/worldgen/build.sh parsa            # compile and validate one layer (previews: --preview parsa)
tools/worldgen/build.sh --check          # validate the composed world
tools/artgen/build.sh --set parsa        # build a set's pages and geometry
B=build/release/laeticias-corner; $B --script tests/scripts/world_tour.lcs --save-dir /tmp/lc
```

### 6.2 `assets/catalog.json` (and `docs/design/catalog.next.json`)

```json
"tile": { "w": 64, "h": 32, "level": 16 },
"sets": ["world", "rome", "athens", "parsa"],
"world": "world/world.json",
```

- `map` stays: it is the home region's size (40 × 40).
- Terrain entries gain optional `"under"` (overlays: the base drawn beneath) and `"faces"` (edge
  materials a raised tile of this terrain may use; the level byte's `aux` picks one). For the home
  set: `grass` gets `"faces": ["world.earth", "world.coast"]`; the overlays get `"under": "grass"`.
- Items gain the optional fields of §1.12 (`layers`, `landmark`, `rotations`, `scale`, `height`,
  `rise`, `axis`, `emitters`, `occluder`, `card`); actors gain `size`. Absent fields keep today's
  meaning, so the home catalog is valid unchanged apart from the three keys above.
- `sets` and `world` are ignored by the engine until it implements E3; the generators read `sets`
  from the start.

### 6.3 New set catalogs

`assets/sets/world/catalog.json`, `…/parsa/…`, `…/athens/…`, `…/rome/…`, written by tasks D1–D4b
(§5) with this skeleton:

```json
{
  "version": 1,
  "set": "parsa",
  "terrain": [ { "id": "parsa.plain_grass", "name": "Plain", "base": true, "variants": 4,
                 "faces": ["world.earth"] },
               { "id": "parsa.paving_stone", "name": "Paving", "edges": 16,
                 "under": "parsa.plain_grass", "faces": ["parsa.ashlar"] } ],
  "items": [ { "id": "parsa.p_house", "name": "Courtyard house", "footprint": [3, 3],
               "layout": "rotate", "count": 4, "on": "land", "layers": ["base", "shadow", "glow"],
               "height": 60, "slots": [ { "id": "door", "kind": "door" } ] } ],
  "actors": [ { "id": "parsa.labourer", "name": "Labourer", "sprite": "walker/parsa.labourer",
                "variants": 4, "anims": { "move": { "fps": 8 }, "idle": { "fps": 2 },
                "carry": { "fps": 8 }, "haul": { "fps": 6 } },
                "locomotion": { "mode": "walk", "speed": 0.9, "network": "roads" } } ],
  "goods": [],
  "audio": { "music": ["music/parsa/day.ogg", "music/parsa/night.ogg"],
             "ambience": ["amb/parsa/plain_day.ogg"], "sfx": ["sfx/parsa/horn.wav"] },
  "art": { "edges": ["parsa.ashlar"], "backdrops": [], "fx": ["parsa.incense"] }
}
```

### 6.4 Decisions for the orchestrator to confirm

1. The home region at grid (40, 1200) (plan C 40..79, R 40..79), world level 2, road on its east
   side, the old road meeting Rome's Via Aurelia at plan (96, 120) instead of `world.md`'s (100, 96).
2. The world save is numbered **3** (`living-corner.md`'s layout plus a `world` block); task A's
   "v2" becomes v3, and the engine keeps reading its chunked v2.
3. Whole tile world resident in memory; streaming only for pages, ground slots, actors, audio.
4. View rotation out of the first version.
5. Pārsa as the pilot city, then Athens, then Rome.
6. Page cap 4096 × 4096; budgets of 1 / 2 / 2 / 3 pages for world / Pārsa / Athens / Rome; Rome's
   nice-to-have landmarks marked N to stay inside them.
7. Walker colour variants baked by the generator (palette-exact) rather than tinted at runtime.
8. Region text in region files (an amendment of "one place" for strings).
9. Engine order: the first world task (E3) runs right after saves (E2), before the rest of the
   corner's task A, so the home in the world is visible early.
