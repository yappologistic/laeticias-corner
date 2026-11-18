# The Halys crossing, spring c. 470 BC (docs/design/sets/world.md §4.3; Herodotus 5.52)

Status: complete

Waypoint layer of the connective world (`docs/design/sets/world.md` §4). Region `halys`, set
`parsa`, base level 5, world rect C 950..965, R 120..135.

World rect C 950..965, R 120..135; local (c, r) = world (C - 950, R - 120); local level 0 = world
level 5. The river runs north (c 5..7); on its west bank the gates with their towers and guard
post straddle the Royal Road (c 0..3, r 6..13); a timber bridge carries the road over (r 9..10);
on the east bank a relay station (c 10..13, r 4..7) and a watchtower (c 12..13, r 11..12).

- Portals: `halys_w`, `halys_e`.
- Ground: copied from the base below (`worldgen.waypoint.ground`), then shaped here; landmarks
  the city set has not drawn yet are provisional ids (`plan/provisional.py`) at their final
  footprint and draw as labelled placeholders.

Build: `tools/worldgen/build.sh halys [--preview]`.
