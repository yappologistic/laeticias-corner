# Delphi, summer 432 BC (docs/design/sets/world.md §4.2)

Status: complete

Waypoint layer of the connective world (`docs/design/sets/world.md` §4). Region `delphi`, set
`athens`, base level 3, world rect C 500..519, R 250..265.

World rect C 500..519, R 250..265; local (c, r) = world (C - 500, R - 250); local level 0 = world
level 3. The Phaedriades stand as cliffs along the north (r 0..3, +6..8, impassable); the temple
terrace (+2) holds the Alkmaeonid temple of Apollo (c 6..17, r 4..9, front east) behind its
polygonal wall; the Athenian treasury below it (+1); the Sacred Way comes up from the olive slope
(portal `delphi_s`, c 18, r 15), zigzags west, climbs to the treasury's level, runs back east
past statue bases and inscribed stelai and climbs to the temple's east front. No theatre: the
stone theatre is 4th century; its site is open slope.

- Portals: `delphi_s`.
- Ground: copied from the base below (`worldgen.waypoint.ground`), then shaped here; landmarks
  the city set has not drawn yet are provisional ids (`plan/provisional.py`) at their final
  footprint and draw as labelled placeholders.

Build: `tools/worldgen/build.sh delphi [--preview]`.
