# Sardis, spring c. 470 BC (docs/design/sets/world.md §4.3)

Status: complete

Waypoint layer of the connective world (`docs/design/sets/world.md` §4). Region `sardis`, set
`parsa`, base level 2, world rect C 860..879, R 200..219.

World rect C 860..879, R 200..219; local (c, r) = world (C - 860, R - 200); local level 0 = world
level 2. The Hermos crosses the north (r 6..10) with the Lydian royal mounds beyond it (Bin
Tepe); the lower town of reed-roofed mudbrick houses (Herodotus 5.101) on the road; the Paktolos
(c 4) comes down from the acropolis to the Hermos, gold washers on its banks; the acropolis rises
in the south (+2..+7) with the fortification on its crest, its flanks too steep above +5; the
first station of the Royal Road (`royal_road_head`) where the road leaves east (portal
`sardis_e`). The road from Ephesus comes in from the west (portal `sardis_w`). The acropolis and
the road head stand two rows south and east of the design's plan so they do not overlap.

- Portals: `sardis_w`, `sardis_e`.
- Ground: copied from the base below (`worldgen.waypoint.ground`), then shaped here; landmarks
  the city set has not drawn yet are provisional ids (`plan/provisional.py`) at their final
  footprint and draw as labelled placeholders.

Build: `tools/worldgen/build.sh sardis [--preview]`.
