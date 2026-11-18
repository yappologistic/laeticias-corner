# Eleusis, summer 432 BC (docs/design/sets/world.md §4.2; athens.md §3.7)

Status: complete

Waypoint layer of the connective world (`docs/design/sets/world.md` §4). Region `eleusis`, set
`athens`, base level 1, world rect C 556..575, R 222..250.

World rect C 556..575, R 222..250; local (c, r) = world (C - 556, R - 222); local level 0 = world
level 1. The acropolis hill in the north-west (+2..3, limestone); the Telesterion (10 x 10, the
Periclean rebuilding under way) on its terrace against it, inside the sanctuary wall; the gate
faces the Sacred Way, which arrives straight from Athens' Sacred Gate across the east edge
(portal `sacred_way_w`); the town below the sanctuary; the shore of the bay in the south; the
Megarid road leaves west (portal `eleusis_w`); stubble fields of the Thriasian plain.

- Portals: `sacred_way_w`, `eleusis_w`.
- Ground: copied from the base below (`worldgen.waypoint.ground`), then shaped here; landmarks
  the city set has not drawn yet are provisional ids (`plan/provisional.py`) at their final
  footprint and draw as labelled placeholders.

Build: `tools/worldgen/build.sh eleusis [--preview]`.
