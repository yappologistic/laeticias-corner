# The world: places, world map, shared conventions

This file is the shared foundation for the three prebuilt ancient cities (`rome.md`, `athens.md`,
`persepolis.md`). Read it first. It fixes the scale, orientation and elevation rules every city
plan uses, proposes the data model for "places", describes the world map screen, and ranks the
engine capabilities the cities need. Sources are in `sources.md`.

## 1. The four places

| Place id | Name on the map | Moment | Map (tiles) | Mood in one line |
|---|---|---|---|---|
| `corner` | Laeticia's Corner | timeless | 20 × 20 | the little floating garden you build yourself |
| `athens` | Athens · Ἀθῆναι (Athênai) | summer 432 BC, the last summer of peace | 160 × 160 | white marble, painted, glittering: cicadas, olive dust, the sea in the haze |
| `parsa` | Pārsa · تخت جمشید (Persepolis) | spring c. 470 BC, under Xerxes I | 160 × 144 | a stone forest of columns against the mountain, snow on the peaks, water channels singing |
| `rome` | Roma | April AD 126, under Hadrian | 176 × 160 | warm brick and gilded bronze in honeyed light; fountains, carts, a city of a million voices |

Each moment is justified in its city file. The three moments are 600 years apart. The game never
pretends they are simultaneous: the world map is a map of *memories*, and each city is the day it
is most itself.

## 2. Scale: "true buildings, squeezed gaps"

Real cities are kilometres across; the diorama is not. Each city keeps its landmarks close to true
size and shape, and compresses the empty or repetitive ground between them, the way a model railway
does. Relative positions, alignments and orientations stay true.

| Quantity | Rule (at 64 × 32 px tiles) | Why |
|---|---|---|
| Horizontal, architecture | **1 tile edge = 4 m** at landmark scale `s = 1`. One tile edge is 32 voxels, so 8 voxels per metre | The Parthenon becomes 8 × 17 tiles, one column per tile along its fronts; the Apadana main hall becomes 15 × 15 |
| Vertical, architecture | **10 px per metre** | artgen maps one voxel of height to one pixel, which is 0.82 of true 2:1 dimetric height; 10 px/m (= 1.25 × 8) restores real-looking proportions |
| Landmark scale `s` | Each landmark lists `s`. Footprint and height are both multiplied by `s` (proportions stay true) | Only very large structures get `s < 1` (the Colosseum, the Circus Maximus, the Persepolis terrace) |
| Gaps between landmarks | compressed 2.5–5 ×, stated per city | Lets a whole walled city fit in 160 tiles |
| People, animals, small props, houses, stalls | **toy scale**: a standing adult is 38–42 px tall including headgear; doors of houses are about 46 px high; a horse is about 44 px at the withers | Matches the existing kit (cottage ridge about 76 px, cat 29 px). Monumental doorways at 10 px/m are already tall enough |
| Terrain relief | 1 elevation level = **16 px** of rise; real relief is compressed (Acropolis about 0.25 ×) | Hills must read as hills without dwarfing the buildings on them |

Heights in the asset tables are pixels from the ground under the footprint's centre to the top of
the sprite, at 64 × 32. At 32 × 16 halve everything. All numbers are targets for the modeller, not
hard limits; the silhouette and the historically correct details matter more than ±10 %.

## 3. Orientation: plan coordinates and the camera

The engine's grid has `+x` down-right and `+y` down-left on screen; the visible walls of any
building are the ones facing `+x` and `+y`. Every city plan is written in **plan coordinates**,
like a normal north-up map:

- `c` = column, increasing **eastward**, `r` = row, increasing **southward**, origin at the
  north-west corner of the map, each cell one tile.
- A footprint `c a..b, r p..q` is inclusive. `w × h` means east–west × north–south extent.

Each city then states how plan coordinates map to the engine grid. The mapping is chosen per city so
that the most important façades face the camera:

| City | Mapping | Compass on screen | Façades the camera sees | Why |
|---|---|---|---|---|
| Athens | `tx = c`, `ty = r` (standard; matches the catalog's neighbour bits N = `ty-1`) | north = up-right, east = down-right | east and south | Parthenon and Hephaisteion fronts (east), Stoa Poikile (faces south), theatre seating (faces south) |
| Rome | `tx = c`, `ty = r` (standard) | as Athens | east and south | Capitoline temple (faces south), the temples at the foot of the Capitol (face east), the Curia, Trajan's Forum, Trajan's Markets |
| Pārsa | `tx = 159 − c`, `ty = 143 − r` (turned 180°) | north = down-left, east = up-left | north and west | the great stairway (west face), the Gate of All Nations and the Apadana north stair (north faces), the bulls of the Hall of a Hundred Columns (north portico). The mountain then sits at the back |

Because Pārsa is turned 180°, every Pārsa landmark is drawn with rotation `r2` of its voxel model,
and its footprint origin (smallest `tx`, `ty`) is the plan's **south-east** corner of the
footprint. The plan tables give plan coordinates; the builder tool converts.

The one important façade no fixed view shows is the Pantheon's north-facing portico in Rome (the
camera sees the rotunda and dome from the south-east). Section 8 lists an optional 90° view
rotation that would fix this and every similar case; until then the Pantheon card says so.

Lighting stays as in the corner: the art is lit from the screen's upper left. The sun direction is
not tied to the compass.

## 4. Elevation model

- Every tile has an integer level `z` (0–15 in practice). The ground diamond is drawn raised by
  `16 × z` px. The rasterised diamond rule of `CLAUDE.md` is unchanged; only the vertical offset
  moves.
- Where a tile is higher than its `+x` or `+y` neighbour, the engine draws a **cliff face** sprite
  for each level of difference on that edge (`edge/<material>_se` / `_sw`, one sprite per level,
  stacked). Materials per city: `rock` (limestone outcrop), `ashlar` (cut stone terrace wall),
  `earth` (soft slope), `brick` (Roman retaining walls). The existing `edge/cliff_*` sprites are the
  `earth` material for the corner's rim.
- **Ramps and stairs** are prebuilt items with a `rise` (levels gained across the footprint) and an
  `axis`. Walkers on them interpolate height. Monumental stairs (the Persepolis great stairway, the
  Propylaia approach, the Capitoline stairs) are landmark items whose footprint covers both levels.
- Items placed on a raised tile are drawn at that tile's height. Multi-tile landmarks occupy tiles
  that all share one level (the builder flattens their footprint).
- Depth sorting uses `(tx + ty)` of the item's front-most footprint tile, then `z` (Section 8, item
  3).
- Steep mountains beyond the walkable area are **backdrop sprites**, not tiles (Section 6).

Level budget per city: Athens 0–10 (Acropolis plateau at 10), Rome 0–7 (Capitol and Palatine at 6–7),
Pārsa 0–9 (terrace at 6, Hadish platform at 9, mountain slope up to 9 then backdrop).

## 5. Data model for places

A place is a folder. The corner keeps working exactly as today; it is simply the place whose map is
editable and starts empty.

```
assets/places/<id>/
  place.json        # metadata, theme, figures, cards, events (schema below)
  map.json          # the prebuilt map: size, per-tile terrain + level, placed items, paths, zones
  atlas.png / atlas.json   # the place's own sprites (same manifest format as the main atlas)
  audio/            # the place's music and ambience (same rules as assets/audio)
assets/catalog.json # gains a "places" list and per-item "place" tags (see below)
```

**Catalog.** `assets/catalog.json` stays the single source of truth. New top-level list:

```json
"places": [
  { "id": "athens", "name": "Athens", "native": "Ἀθῆναι", "map": "places/athens/map.json",
    "atlas": "places/athens/atlas.json", "editable_zones": true, "unlock": "start" }
]
```

Items, terrain and visitors gain an optional `"place": "athens"` (absent = the corner / shared).
New optional item fields the cities need:

| Field | Meaning |
|---|---|
| `"landmark": true` | unique, not in any build menu, clickable for a card |
| `"scale": 0.7` | documentation of `s` (the art generator reads it; the engine does not need it) |
| `"rise": 6, "axis": "x"` | stairs/ramps: levels gained across the footprint along the axis |
| `"walk": [[dx,dy], ...]` | tiles of a large footprint that walkers may cross (porticoes, gates, colonnades, plazas inside a precinct) |
| `"occluder": true` | the engine fades this landmark to 35 % when the cursor or a followed figure is behind it |
| `"emitters": [...]` | named effect points (smoke, incense, fountain spray, fire) per rotation, like `smoke_at` |
| `"card": "<card id>"` | the card shown on click |

**`place.json` (sketch):**

```json
{
  "id": "parsa",
  "start_camera": { "c": 96, "r": 40, "zoom": 2 },
  "clock": { "start": "dawn", "day_length_s": 1440, "pin_allowed": true },
  "theme": {
    "grading": { "dawn": {...}, "day": {...}, "dusk": {...}, "night": {...} },
    "sky": { "dawn": ["#..", "#.."], "day": [...], "dusk": [...], "night": [...] },
    "haze": { "colour": "#d9c9a8", "strength": 0.25, "start_rows": 40 },
    "weather": [ { "id": "spring_shower", "weight": 1, "min_gap_s": 900 },
                 { "id": "dust_breeze", "weight": 2 } ],
    "wind": { "base": 0.3, "gusts": 0.5 },
    "ambience": { "day": ["amb/parsa_day.ogg"], "night": ["amb/parsa_night.ogg"],
                  "zones": [ { "id": "water", "file": "amb/parsa_channels.ogg", "rect": [..] } ] },
    "music": { "day": "music/parsa_day.ogg", "night": "music/parsa_night.ogg" }
  },
  "figures": [ { "id": "xerxes", "sprite": "figure/xerxes", "card": "xerxes",
                 "presence": "present", "time": "day", "route": "apadana_audience" } ],
  "walkers": [ { "kind": "gardener", "count": 6, "zone": "paradise", "time": "day" } ],
  "events":  [ { "id": "audience", "every_s": 720, "route": "stairway_to_apadana",
                 "cast": ["delegation_*", "guards_x8", "usher"] } ],
  "cards":   { "xerxes": { "title": "...", "epithet": "...", "text": "..." } },
  "journal": [ "landmark:*", "figure:*", "find:*" ]
}
```

`presence` is one of `present` (alive at the city's moment), `statue` (a clickable statue or
relief that "speaks" through its card), `memory` (a translucent figure who appears at dusk near
their monument, fades at dawn, never interacts with living figures), `shrine` (a god or hero shown
through an altar, image or symbol, with an occasional apparition during a festival) or
`reenactor` (a citizen playing the part during a festival). Every card states which.

**Strings.** All card texts, names and hints live in `place.json` (one place per city), honouring
the rule that user-visible strings live in one place.

## 6. Shared art kinds the cities add

Besides ordinary items, the cities need five new sprite families (all in each place's atlas):

| Key | Meaning |
|---|---|
| `landmark/<id>/<layer>/r<k>/f<n>` | large unique structures; same layers as items (`base`, `shadow`, `glow`); may be split into vertical **slices** (`.../s<i>`) one tile wide along the footprint's diagonal so the engine can depth-sort them against walkers (Section 8, item 3) |
| `figure/<id>/<anim>/f<n>` | named figures; same animation set as critters plus optional `act` (a looping gesture: speaking, writing, playing, sculpting, pouring) |
| `walker/<kind>/<variant>/<anim>/f<n>` | anonymous citizens in 3–4 colour variants per kind |
| `edge/<material>_se`, `edge/<material>_sw` | one level (16 px) of cliff or wall face per material |
| `backdrop/<id>` | a wide painted strip behind a far map edge: mountains, the sea, distant hills. Drawn first, scrolls with the map, has its own night-time version `backdrop/<id>_night` |

## 7. The world map screen

**Look.** A hand-drawn map on aged papyrus-coloured paper, framed like a scroll unrolled on a desk.
It runs from the Tyrrhenian Sea in the west to the Iranian plateau in the east: Italy, the Adriatic,
Greece and the Aegean, Anatolia, Cyprus, the Levant coast, Mesopotamia between its two rivers, the
Zagros, and Fārs with the Persian Gulf below. Coastlines in sepia ink, sea in faded blue wash with
small drawn waves and a few ships, mountains as little shaded triangles, rivers as fine blue lines
(Tiber, Euphrates, Tigris, Kur). No modern borders, no modern names. Place names in the same
original UI font, with the native form underneath in small type. The corner is drawn as a tiny
floating island in the top-left margin, outside the geography, joined to the map by a dotted line:
it is where the player lives.

**Places on the map.**

| Place | Marker | Shown beside it | Hover text |
|---|---|---|---|
| Laeticia's Corner | a small floating island with a cottage | the player's own diorama as a live thumbnail | "Home." |
| Roma | the Pantheon dome and a column | "Roma · AD 126 · in the time of Hadrian" | journal progress, e.g. "23 of 40 found" |
| Athens | the Acropolis with the Parthenon | "Ἀθῆναι · 432 BC · in the time of Pericles" | as above |
| Pārsa | the double stairway and two columns | "Pārsa · c. 470 BC · in the time of Xšayāršā (Xerxes)" | as above |

**Routes.** Faint ancient routes drawn as dotted lines: the sea lanes Ostia–Brundisium–Piraeus,
the Aegean crossing to Ionia, and the Achaemenid Royal Road from Sardis to Susa with a branch to
Pārsa. They are decoration and a hint of history (the Royal Road is attested in Herodotus and in
the Persepolis travel-ration tablets), not gameplay.

**Travel.** Click a place: the map zooms gently toward it while a small symbol travels the route
(a ship for sea legs, a horse rider for the Royal Road), about 2 seconds, skippable with a click.
Sound: paper rustle, a soft wind, then the destination's ambience fades in under a short four-note
motif from that city's day music. The city opens at its `start_camera` at dawn (or at the clock time
the player left it). No loading screen beyond a 0.4 s crossfade.

**Unlocking.** None required: all four places are open from the start, because the game has no
fail state or grind. A gentle suggestion instead: the first time the world map opens, a short line
says "Where would you like to wander first?" Each city remembers its own clock, camera and journal.
If the team wants a sense of journey, the optional order is corner → Athens → Pārsa → Rome (by
arriving at a city you receive a small keepsake for the corner, see each city's section 7).

## 8. Engine capabilities the cities need (ordered by importance)

| # | Capability | What exactly | Notes |
|---|---|---|---|
| 1 | **Places** | load/unload a place (map, atlas, theme, audio) and switch from the world map; one active place at a time; per-place save of clock, camera, journal, decorated zones | biggest structural change; the corner becomes one place among four |
| 2 | **Large maps and culling** | maps up to 176 × 160 (28 000 tiles), per-frame visible-tile culling, items bucketed by row so only visible rows are drawn | the frame budget (under 2 ms) must still hold at full zoom-out; consider chunked static geometry |
| 3 | **Large multi-tile landmarks and depth sorting** | sprites up to about 2400 × 1200 px; walkers must pass behind and in front of colonnades correctly. Use per-slice sorting (landmark split into one-tile-wide diagonal slices) or per-tile occlusion masks | without this, figures walking through porticoes will look wrong |
| 4 | **Elevation** | integer levels per tile, stacked cliff faces, stairs/ramps with height interpolation, items on raised tiles, picking (mouse to tile) that respects height | needed by all three cities |
| 5 | **Multiple atlases** | the shared atlas plus the active place's atlas, possibly more than one texture page per place (landmarks are big) | draw calls stay in the low tens: sort by texture page |
| 6 | **Non-buildable prebuilt maps with decorate zones** | prebuilt tiles and items are locked; marked zones accept a place-specific build menu (Section 7 of each city); undo/redo works inside zones | the corner's tools reused as-is |
| 7 | **Clickable figures and landmarks; cards; journal** | hover highlight, click opens a card (title, native name, epithet, 40–60 words, small portrait from the sprite); first click adds to the per-place journal | the core "wonder" loop |
| 8 | **Walkers on path graphs** | anonymous citizens follow a per-place path graph (nodes with time-of-day weights), stop at points of interest, avoid each other loosely | no pathfinding over the whole map needed: paths are authored |
| 9 | **Timed processions/events** | an ordered group follows a route at walking pace with spacing, triggers sounds and effects at nodes, then disperses | Panathenaic procession, gift delegations, a Roman pompa circensis |
| 10 | **Per-place theme: grading, sky, haze, weather** | four grading keyframes per place, distance haze toward far edges, place-specific weather kinds (rain, dust breeze, spring shower, summer storm with lightning flash, cloud shadows) | extends the existing day/night grading and rain |
| 11 | **Zoned ambience and positional sound** | ambience layers tied to rectangles (water channels, the forum crowd, the sea wind on the Acropolis), mixed by camera position; one-shot sounds at world positions with distance attenuation | |
| 12 | **Backdrops** | wide sprites behind far map edges, drawn first, with a night variant | mountains of Pārsa, the sea seen from Athens, the Alban hills from Rome |
| 13 | **Glow layers in bulk** | hundreds of small night lights (lamps, braziers) using the existing additive glow path, batched | cheap if batched |
| 14 | **Optional: view rotation by 90°** | the voxel generator renders all four rotations of every model; the engine rotates the grid mapping and swaps sprites | nice-to-have; atlas size × 4 for landmarks. Fixes the Pantheon portico and Tachara's south front |
| 15 | **Optional: follow a figure** | the camera gently tracks a clicked figure until the player pans | cosy and cheap once 8 exists |

## 9. Respect and honesty rules (all three cities)

- Present every culture from its own evidence first: its inscriptions, archives, archaeology and
  art. Greek authors on Persia, and Roman authors on Greeks, are used with care and labelled.
- When something is uncertain or disputed, the city file says so and names the chosen option. Cards
  never state a disputed thing as fact; they use words like "probably" or "tradition says".
- People who were not alive at the city's moment never appear as living citizens. They appear as
  statues, reliefs, memories or festival roles, and the card says which.
- Gods and heroes are shown as their own people imagined them in images of the period: the cards
  quote or paraphrase ancient sources, never modern retellings.
- Nobody is a joke. Enslaved and working people appear with dignity and their own routines; the
  cards mention them where the sources do (Persepolis tablets on workers' rations; the potters of
  the Kerameikos; Rome's freedmen).
- Everything in the game (art, music, names of things, card wording) is original. Ancient texts may
  be paraphrased; ancient melodies are evoked through their modes and instruments, not copied.
