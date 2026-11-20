# artgen

Deterministic generator for `assets/atlas.png` + `assets/atlas.json`.

```sh
tools/artgen/build.sh            # regenerate assets/atlas.{png,json} from assets/catalog.json
tools/artgen/build.sh --catalog docs/design/catalog.next.json --preview   # the batch-2 atlas
tools/artgen/build.sh --tile 32 --out out/artgen/lo --preview   # 32x16 tiles, elsewhere
tools/artgen/.venv/bin/python tools/artgen/validate.py --catalog assets/catalog.json --allow-extra
```

Art sets beyond the home region (world-tech.md §1) build on their own, from their set catalog
`assets/sets/<set>/catalog.json`, into `assets/atlas/<set>.<n>.png/json` plus
`assets/atlas/<set>.geom.json`; the home atlas is never touched:

```sh
tools/artgen/build.sh --set parsa --preview          # pages, geometry, validation, previews
tools/artgen/build.sh --set parsa --only apadana walker/parsa.usher   # a quick look, no geometry
tools/artgen/.venv/bin/python tools/artgen/setvalidate.py parsa
tools/artgen/build.sh --set athens --preview         # the Athens set
tools/artgen/build.sh --set athens --only parthenon --out out/artgen/athens/q   # quick look elsewhere
tools/artgen/.venv/bin/python -m sets.athens.preview out/artgen/athens/q parthenon  # (from tools/artgen)
```

The application icon builds on its own as well:

```sh
tools/artgen/build.sh --icon           # assets/icon/icon-<size>.png and laeticias-corner.ico
tools/artgen/build.sh --icon --check   # fails if a committed icon file differs (ctest: icon_fresh)
```

`--catalog` picks the catalog the required keys are derived from (default `assets/catalog.json`).
The standalone validator with `--allow-extra` checks that an atlas covers a catalog, so the
batch-2 atlas can be checked against the live catalog.

The tile size comes from `tile.w` in `assets/catalog.json` (`tile.h` is half of it) unless
`--tile` overrides it; it must be a multiple of 32. `--out` writes the atlas and the previews
to another directory (previews of finer tiles are written at 1x and, as `*_2x.png`, at 2x).

The first run creates `tools/artgen/.venv` from the pinned `requirements.txt`. The same input
always produces byte-identical output. The batch-2 atlas at 64x32 takes about a minute and a
half with the four worker processes the machine-courtesy rules allow.

## How it works

- `spec.py` lists every key the catalog implies (items, season looks, growth stages, the four
  base animations of every visitor) and parses the build options into a `Build`: catalog, tile
  width, output paths and `k`, the voxels per design unit.
- `art_list.json` holds the keys a catalog cannot imply (effects, rim edges, wild land, sky,
  interface, extra animations and season looks), in groups gated on what the catalog contains.
  `generate.py` turns the full key list into jobs; a key no builder makes is an error, and the
  validator checks every animation the catalog's activities and routines name has frames.
- `palette.py` holds the one curated palette (65 colours) and the material ramps built from it.
- `voxel.py` is the modelling toolkit: a material grid with per-voxel normals and tone, boolean
  shape helpers (boxes, ellipsoids, cylinders, cones, capsules, gables), seeded noise, rotation.
  Models are written in design units, 16 per tile edge, and sampled with `k` voxels per unit
  (`k = tile.w / 32`); one voxel of height is one pixel. `Model.fine` (k >= 2) gates detail
  smaller than a design unit (leaves, shingles, hinges, mullions): the coarse grid keeps its
  established look and the 32x16 atlas stays reproducible byte for byte.
- `render.py` ray-casts a model exactly into the 2:1 projection (pixel centres, so tiles
  partition the screen), shades it with one sun from the upper left, ambient occlusion, cast
  self-shadows and selective outlines, and quantises to the material's ramp with a restrained
  4x4 ordered dither. It also produces the ground `shadow` layer and the emissive `glow` layer.
- `models/resident.py` is Laeticia: one voxel figure built from parts evaluated in body space,
  posed per frame (a `Pose` per animation), so seated, kneeling and lying poses reuse the same
  parts; `models/wildlife.py` holds the rare visitors. `decor.py` draws the portrait, rainbow,
  title logotype and postcard frames at pixel scale; `fx.py` the effects.
- `models/` describe every item and the walking visitors as voxel models; the tiny flyers
  (butterfly, bee, firefly) are hand-drawn pixel stencils, since voxels would only make blobs at
  that size. Each stencil set is drawn for one pixel density (1 and 2 px per design unit, the
  finer set with distinct front and back drawings); a build uses the densest set dividing its
  own and enlarges it by the remaining whole factor. `terrain.py` and `fx.py` evaluate ground
  tiles, cliff faces, cursor diamonds and effects directly per pixel; grass marks and meadow
  flowers come in one table per detail level.
- Lengths that set the look (occlusion reach, contact shadow, crevice width) are in design
  units; pixel-sized things (outlines, dither, 1 px marks) stay pixel-sized, so finer tiles
  read as finer art, not as enlarged sprites.
- `pack.py` trims each sprite, shelf-packs them with a 1 px gutter and writes the manifest.
- `validate.py` checks keys, rects, anchors, frame counts and palette use.
- `preview.py` composes test scenes from the packed atlas the way the engine draws them.

## The application icon

`icon.py` draws the game's icon: the home corner as a block of grassy land with Laeticia's
red-roofed cottage (its gable window lit), its chimney and a round tree, in the 2:1 projection
and the home palette only. Every size up to 128 is its own drawing on its own grid: 32, 48, 64
and 128 from polygons in grid units (one unit 2 px across and 1 px down, heights in px) filled
at pixel centres, so every edge is a clean two-pixel step, with detail added as the size grows
(grass marks, then plinth, tile courses, flowers, path and shade, then tile joints); 16 and 24
are placed pixel by pixel over the land block the code draws (`HAND`), the same picture with
one window, one door and one crown. Each object lays a one-pixel ink ring round itself, so the
picture holds on light, dark and coloured backgrounds. 256 and 512 are the 128 drawing enlarged
2x and 4x by repeating pixels. The `.ico` holds 16, 24, 32, 48 and 64 as 32-bit bitmaps with
their mask and 256 as PNG; it is written by the script itself, byte for byte the same on every
run. The window takes the PNGs (`src/app/identity.cpp`), the Windows program embeds the `.ico`
and the Linux package ships the 256 picture beside its desktop file.

## Sets, big landmarks and people

- `setbuild.py` derives every key a set catalog implies (terrain, items with their layers,
  rotations and states, actors in both facings at the pose library's frame counts, edges,
  backdrops, effects), renders them with the set's package `sets/<set>/` (`LANDMARKS`,
  `ITEMS`, `STATES`, `FRAMES`, `actor_sprite`, `carry_at`, `flat`, `preview`), cuts large
  landmarks into pieces (walk tiles in runs of up to 8, the rest in rectangles of at most
  8 x 8), packs pages by what one view draws together (the city's people with its kit, plants
  and its own ground and faces on one page, since raised ground is drawn among the objects; each
  landmark district whole on one page, the busiest first; every glow of the set together; effects
  and backdrops fill the gaps), keeps shadows off the colour pages (they are on the half-size
  shadow page only) and writes the geometry file and the occlusion page. `setvalidate.py`
  checks keys, page limits, palette (`palette.palette_for(set)`: home colours plus the set's),
  diamonds, frame counts, piece partitions, walk-tile headroom and reachability, slot and
  emitter coverage, and warns when a measured height strays more than 15 % from the catalog's.
- `bigrender.py` renders models too big for one grid: a builder fills whatever box it is
  handed, every shape evaluating only where it meets that box (`Model.box_window`); pass one
  builds each 4 x 4 tile chunk for its solid mask, pass two shades each chunk against the
  assembled mask (so shadows and occlusion see the whole building), and chunks composite by
  depth into exactly the image of the whole model, with each pixel's footprint tile recorded
  for pieces. `render.py` is split into `shade` and `finish` for this; home output is
  unchanged byte for byte.
- `arch.py` holds the architectural primitives in grid axes with a landmark `Scale` (8 s
  voxels per metre across, 10 s up): fluted columns with bell or square bases and bull, lion
  or griffin protome capitals, flat roofs on cedar beams, stepped merlons, stone door and window
  frames with cavetto cornices, painted relief registers, rosette and cypress bands,
  inscription panels, glazed-brick panels, mudbrick walls on stone plinths, stairs with
  parapets, tents, awnings, and `field_fill` for rough rock with smooth normals.
- `rig.py` is the one walker rig: body types (man, woman, elder, child, king), the pose library
  of world-tech.md §1.9 (`POSES`, fixed frame counts) and a `Dress` as data (garment, colours,
  patterns, coat, cape, shawl, veil, headgear, hair, beard, footwear, jewellery, worn and held
  things, how things are held, a mount). A set's people are lists of dresses
  (`sets/parsa/people.py`); other sets reuse the rig with their own.
- `setpreview.py` composes scenes from a set's pages with levels and stacked edge faces.
- `greek.py` is Greek (and Roman) architecture as parameters: an `Order` (Doric or Ionic, in
  metres) drawn at a landmark `Scale`, columns with entasis and flutes (finished, unfluted,
  with lifting bosses, or as drums on a building site), crepidomas, marble and poros ashlar,
  house walls, the Doric entablature (taenia, regulae, triglyphs and figured metopes, geison),
  Ionic friezes, pediments with sculpture, akroteria, tiled gable, hipped and conical roofs
  with antefixes, `temple(Temple)` (peripteral, prostyle or in antis, porch grilles, friezes)
  and `stoa(Stoa)` (Doric front, Ionic inner row, painted panels, hanging shields), statues cast
  from rig dresses at any size (`statue_model`, `paste`), herms, stelai, bases, vases, painted
  motifs (meander, egg-and-dart, leaf, beads, palmette) and city walls.
- `relief_greek.py` poses 2D figures (people, horses, centaurs, chariots, the olive) and
  rasterises them into `relief` stencils at any height, so pediments, metopes, the Ionic
  frieze, painted panels and grave stelae compose from figures instead of hand-drawn text.

## Land, slopes and falling water

- `land.py` draws every natural face (rock, earth, snow, sea cliff) for all sets from a `Stone`
  material: one level of face with nothing tied to the level's top or foot, facets on a warped
  staggered lattice repeating every level and tile edge (the seam row common to every look), so
  stacked levels of random looks read as one cliff; `/top` rounds the lip; `wedge` is the level
  under a slope's falling edge. It also holds the face geometry (`face_grid`, `periodic`).
- `slopes.py` makes sloped ground: 21 shapes as nine heights on a 3 x 3 grid (corner masks,
  knoll, ridges), eight triangles fanned round the centre; a terrain's flat art is carried onto
  the mesh pixel by pixel (stretched rows take a neighbouring texel, never a repeated one), lit
  by the ground's soft response `ground_light` of a normal smoothed over the tile, in palette
  steps inside each colour's group with the fraction given to texels by their own lightness,
  and marked as its material wears a slope (`_details`: terracettes, rills, ledges, ripples,
  rock breaking through where steep). A set lists the terrains that slope in `art.slopes`; keys
  `terrain/<id>/slope/<shape>/v<n>`, two looks each.
- Ground that must not repeat per tile: bases have several looks that share only a fine field
  along the tile's edges (`terrain.broad`); overlays have interior looks (`m15/v<n>/f<k>`,
  each set's `ground.INTERIOR`), either the same paint on a shifted plane inside the tile
  (`terrain.interior_mix`) or detail each look owns entirely (the world's rock, scrub and
  hamada, `ground._cells`); `setvalidate.regularity` measures a shuffled field of looks.
- `waterworks.py` draws water inside items (basins and spouts) to the falls' standard: depth,
  contact line, rings and boil where streams land, glassy streams with travelling streaks.
- `falls.py` draws falling and stepping water (`edge/world.fall_<side>/<top|mid|foot|rapid>/e<n>/f<k>`),
  plunge foam and rapids, on the water's one 4-step loop; the world catalog's `art.falls` gives
  a shader the speed to scroll them.
- `landpreview.py` renders real places from the composed world as the engine draws them, with the
  slope rule (masonry faces stay flat), wedges, falls and interior looks; `--compare REV` draws
  slopes.py at a git revision beside the working copy (its slopes and grounds live), `--scales`
  and `--season` (by ramp states) as well; the contract is `out/reports/art-smooth-land.md`
  §3-§4.
- Every build writes a water page (`<set>.w.*`, home `atlas.w.*`): per item sprite holding
  water, a rectangle the size of its colour one with the water mask, depth from the rim and bed.

## Conventions worth knowing

- Overlay masks only ever depend on each edge's own bit: an open edge is fully covered and every
  inset tapers to zero at a corner beside an open edge, so neighbours agree on shared edges.
  The world's sea and rivers lie over a whole diamond of sand: their corners between two closed
  edges are mitred, not rounded (`ground.BEACH_CORNER`), so the beach keeps its width round a
  bend (a test in `tests/test_coverage.cpp` holds the pages to it).
- Joined items (`hedge`, `fence`) are modelled with the neighbours' arms as unseen context, so
  light, leaves and outlines continue across the tile edge without a seam.
- Rotatable pieces are modelled facing +y (the windmill faces +x so both rotations show sails).
- Trees are clumps studded with small leaf clusters (`leaf_mass`); each cluster shades as its own
  puff, so canopies read as lit tufts with dark crevices. Their crowns sway clump by clump. On
  fine grids a 3D Voronoi of single leaves (`cells3`) shades each leaf and frays the silhouette;
  hedges use a tile-periodic lattice so joins stay seamless.
- Lawn grass is flat; variants differ only in a few hand-shaped marks and clumps, so a field of
  randomly chosen variants shows gentle patches. Meadow and cliffs repeat exactly per tile, so
  their marks are dense or hand-placed and smooth to keep the repeat from reading as a pattern.
- Glow layers store halo strength in alpha; draw them with additive blending.
- Flying visitors are anchored at the bottom of the body; the engine adds the altitude.

## Data pages (the shader path's contract, graphics-plan §2)

Every build writes, beside each colour page, what the shader path reads instead of it; the
colour pages, their manifests and the key scheme are unchanged.

| File | What |
|---|---|
| `<page>.p.png` | The **packed page**: the colour page's size and rectangles, one 32-bit word per pixel |
| `<page>.p.json` | `{"version": 1, "packed": "<page>.p.png", "colour": "<page>.png", "ramps": "<path to ramps.json>", "colour_only": [keys]}` |
| `<set>.s.png` + `.json` (home: `atlas.s.*`) | The **shadow page**: every `…/shadow/…` sprite at half size, `"scale": 0.5`; `w`, `h`, `ox`, `oy` in half-size texels, drawn ×2 with linear filtering |
| `atlas/ramps.png` + `ramps.json` | The **ramp table**, shared by every set and the home atlas |
| `<set>.w.png` + `.json` (home: `atlas.w.*`) | The **water page**: every item sprite holding water, its colour rectangle's size and anchor; R water, G depth px, B bed |
| `<set>.o.png` + `.json` | The **occlusion page** (`occlusion.py`, realism.md §5.1): per item and look (`item/<id>/<look>`), a grid aligned with world X and Y at `texel` (4) art px; `ox`, `oy` the texel of the footprint origin; R top px / 2, G underside px / 2 (0: solid from the floor), B material code (`codes`), A coverage |

`<page>` is `assets/atlas/<set>.<n>` for a set and `assets/atlas` for the home atlas.

**The packed word.** RGBA8 read as `w = r | g << 8 | b << 16 | a << 24`, sampled nearest only:

| Bits | Field | Meaning |
|---|---|---|
| 0–2 | `step` | step on the ramp, 0 = darkest |
| 3–10 | `ramp` | ramp id 1–255 in `ramps.json`; 0 = no pixel. `ramps.png` at (`step`, `ramp`) is the pixel's exact colour |
| 11–15 | `nx` | world normal x as a code 0–30: `n = (code − 15) / 15` (axis normals exact; 31 unused) |
| 16–20 | `ny` | world normal y, the same; `nz = sqrt(max(0, 1 − nx² − ny²))`, z is up; x and y are the grid axes (+x down-right, +y down-left) |
| 21–29 | `h` | height above the anchor's ground in art px, 0–511 (one voxel of height is one px) |
| 30 | `lit` | 1 where the generator's sun reached the surface: its baked light was `0.42 + 0.58·max(0, N·S₀)·(lit ? 1 : 0.25)` times its occlusion, `S₀ = normalise(−0.45, 0.28, 0.85)` |
| 31 | `snow` | snow catcher: the stored normal has `nz > 0.55`, nothing above it up to the sky, its ramp is one snow lies on, and the sprite stands still (items, ground, faces; never people, animals, carts or goods) |

Flat sprites (ground and overlays drawn per pixel) face up at height 0, lit, catching snow. Faces
under tile edges (`edge/…_se…`, `edge/…_sw…`) face +x or +y; their height falls one px per px
from their top to 0 at each column's lowest pixel, so the engine adds the level of the face's
foot. A sprite the engine mirrors (the other two facings of people and carts) swaps `nx` and
`ny`. Colour-only sprites (`colour_only`: shadows, glows, effects, weather, sky, interface,
painted backdrops, the hand-drawn flyers, anything translucent such as foam, river flow and
falls) hold their RGBA unchanged on the packed page, so the packed page alone replaces the
colour page; their rectangles must be sampled as colour.

**The ramp table.** `ramps.png`: row = ramp id (row 0 empty), eight texels dark to light, alpha
0 past a ramp's last step. `ramps.json`: `{"version", "texture", "steps": 8, "classes", "states",
"ramps": [...]}`; per ramp `id`, `name`, `material` (a `palette.MATERIALS` ramp, what model
renders quantise to) or `group` (a `palette.GROUPS` ramp, what flat sprites resolve to) or
`state_of` + `state`, `steps`, `colours`, Oklab `L` per step, `class` (one of `classes`),
`shell` (px of thin-shell depth for the shadow march: foliage, grass and crops 6, cloth 2, skin
8, else 255), `porous` (wet darkening), `snow` (snow lies on it), `specular`, `sway` (foliage,
grass, crops, cloth: bends in the wind on static items), the realism study's responses
(`translucency` and `trans`, `wet_steps`, `gloss`, `sparkle`; on water ramps `bed` and
`absorb`, rgb per 70 px) and, on the green ramps, `states`
(`fresh`, `dry`, `dormant`, `turn` → the ramp id that state draws with: the same number of steps,
picked from one hue family by Oklab L, outlines kept). Ids are stable: a name keeps the id it has
in the committed `ramps.json`; new names take the next id; a retired id is never reused.

**Geometry additions** (`<set>.geom.json`, fields the engine's parser may ignore): `pass` per
crossing and water landmark (rows by dy: px a boat must stay under to pass the tile, 255 open,
0 nothing passes); `dir` and `cone` on door and window `lights`; per item
variant `lights` (`{"door_0": {"at": [x, y], "z": h}, "window_0": …}`: pixel offset from the
anchor and height in px of each door lamp and window, from the halos and marks the models give
a kind); per actor `hand_at` (`{"<anim>_<facing>": [[x, y, front], …]}` for `move`, `idle`,
`march`, `run`: the free hand, `front` 1 when it is nearer the camera than the body; mirrored
facings negate `x`) and, for actors whose frames hold something alight, `glow_at` (the glow's
centre per frame) beside their `…/glow/f<n>` frames. Carried lights are `prop/<set>.<lamp|torch|
lantern>/f<n>` with `…/glow/f<n>`, anchored at the grip, listed in the set catalog's `art.props`.

**Geometry for the draw order** (`docs/design/draw-order.md` §1.2, §3.4, §5.1), per item and
look in `<set>.geom.json`: `tops` (rows by `dy`, one value per footprint tile: the highest solid
voxel in px above the anchor's ground; a walk tile gives its floor), `roof` (`{"dx,dy": px}`:
over a walk tile, the top of what stands above the walker's headroom) and `under` (per piece of
an item with `pieces`, the most room under it on its walk and water tiles: a deck's underside
between the piers, an arch's crown; 0 for solid pieces; one value for an unsplit walkable kit
crossing). Kit items with walk tiles (the relay station, the sheepfold, the
aqueduct's arches) are cut into `pieces` like landmarks: walk tiles in runs of their own,
sprites `item/<id>/base/<look>/p<i>/f0` beside the whole sprite.

**Checks** (`datavalidate.py`, run by `validate.py` and `setvalidate.py`): the ramp table is well
formed and its ids stable against the committed one; every page has its packed twin of the same
size; no coloured pixel without data, no data outside a sprite or on a transparent pixel, ramp
and step inside the table, every decoded colour equal to the pixel's, normals on the unit sphere
within half a code, the snow bit only on snow ramps with `nz > 0.55`, heights consistent with
where each pixel sits on screen for its item's footprint (items, ground, people, carts); the
shadow page holds every shadow sprite at half size (and the colour pages none); the occlusion
page has every item look and its tops stand at or above every pixel the colour art draws over
them; for the draw order, every pixel's height
and screen place put it on one of its own piece's tiles (heights right at seams), walk floors
stand at `walk_z`, stair treads rise toward `climb`, and the rules P1–P3, W2–W4, S1 and O1 of
draw-order.md §5.1 hold (fixtures from the audit: `tests/test_datavalidate.py`, run as
`tools/artgen/.venv/bin/python tools/artgen/tests/test_datavalidate.py`). `datapreview.py` draws preview scenes from
the packed pages (normals, heights, classes, sun and snow bits, autumn and winter by ramp swap).
