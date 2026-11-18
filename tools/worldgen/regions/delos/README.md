# Delos, summer 432 BC (docs/design/sets/world.md §4.2)

Status: complete

Waypoint layer of the connective world (`docs/design/sets/world.md` §4). Region `delos`, set
`athens`, base level 1, world rect C 775..790, R 330..345.

World rect C 775..790, R 330..345; local (c, r) = world (C - 775, R - 330); local level 0 = world
level 1. The island (enlarged in the plan for its sanctuary) with the sacred harbour on its west
shore (moles; the lane `delos` meets the Aegean base lane), the sanctuary of Apollo (the old
poros temple, the unfinished marble temple, the Artemision: c 4..13, r 2..9), the terrace of the
Naxian lions facing the sacred lake, Kynthos rising in the east (+3). Graves are still on the
island in 432 (the purification of 426/5 moved them to Rheneia). Rows are two higher than the
design's plan so the lake stays inside the island.

- Portals: none (an island: its harbour lane meets the base lane).
- Ground: copied from the base below (`worldgen.waypoint.ground`), then shaped here; landmarks
  the city set has not drawn yet are provisional ids (`plan/provisional.py`) at their final
  footprint and draw as labelled placeholders.

Build: `tools/worldgen/build.sh delos [--preview]`.
