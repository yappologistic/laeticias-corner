# Alban Mount layer

Status: complete

The Alban Mount, April AD 126 (`docs/design/sets/world.md` §4.1, `rome.md` §3.7). World rect
C 278..311, R 130..175; local (c, r) = world (C − 278, R − 130); local level 0 = world level 2.

- `layout.py`: the mount as one level array (summit platform at +8 falling a level every three
  tiles, the crater rim at +4..5 round the lake at +3, the Liris' valley as the base carves it);
  the sanctuary of Jupiter Latiaris (`latiaris`, c 18..23, r 4..9) in its paved precinct with
  statues and an altar; the Via Sacra straight up the south face, a stone flight a level; the
  crater lake (still water) with reeds and poplars on its shore; oak and beech woods on the
  upper slopes; three villas on terraces above a track, vineyards behind them; the Via Appia at
  the foot (r 42..43) from portal `appia_alban_w` (world 1) up one ramp to `appia_alban_e`
  (world 2), over the Liris on stone arches, tombs, cypresses and milestones beside it.
- Shared helpers from `regions/rome/common.py` (levels, groves); waypoint helpers from
  `worldgen/waypoint.py`.
- Region file `assets/regions/alban_mount.json` (written by `build.sh --life`).

Build: `tools/worldgen/build.sh alban_mount [--preview]`.

Life and text: `life.py` (built by `tools/worldgen/build.sh --city alban_mount`) writes `assets/regions/alban_mount.json`; the townsfolk and trades are Rome's, borrowed through `regions/rome/townlife.py`.
