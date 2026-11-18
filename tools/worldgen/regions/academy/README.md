# The Academy (Akademeia), summer 432 BC (docs/design/sets/world.md §4.2; athens.md §3.7)

Status: complete

Waypoint layer of the connective world (`docs/design/sets/world.md` §4). Region `academy`, set
`athens`, base level 1, world rect C 560..575, R 205..219.

World rect C 560..575, R 205..219; local (c, r) = world (C - 560, R - 205); local level 0 = world
level 1, the grove's ground at local 1. The gymnasium in its grove of sacred olives and planes
(`academy_grove`, 12 x 10) with the altar of Prometheus where the torch races start; the road
from the Dipylon comes in over the east edge (portal `academy_e`, from Athens' `academy_road_n`
by the base) between grave stelai, as the public cemetery lined it.

- Portals: `academy_e`.
- Ground: copied from the base below (`worldgen.waypoint.ground`), then shaped here; landmarks
  the city set has not drawn yet are provisional ids (`plan/provisional.py`) at their final
  footprint and draw as labelled placeholders.

Build: `tools/worldgen/build.sh academy [--preview]`.
