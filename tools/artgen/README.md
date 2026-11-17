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

## Sets, big landmarks and people

- `setbuild.py` derives every key a set catalog implies (terrain, items with their layers,
  rotations and states, actors in both facings at the pose library's frame counts, edges,
  backdrops, effects), renders them with the set's package `sets/<set>/` (`LANDMARKS`,
  `ITEMS`, `STATES`, `FRAMES`, `actor_sprite`, `carry_at`, `flat`, `preview`), cuts large
  landmarks into pieces (walk tiles in runs of up to 8, the rest in rectangles of at most
  8 x 8), packs pages (kit and actors first, landmark pieces by district, shadows and glows on
  their own page when that costs no extra page) and writes the geometry file. `setvalidate.py`
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

## Conventions worth knowing

- Overlay masks only ever depend on each edge's own bit: an open edge is fully covered and every
  inset tapers to zero at a corner beside an open edge, so neighbours agree on shared edges.
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
