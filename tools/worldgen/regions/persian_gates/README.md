# The Persian Gates, spring c. 470 BC (docs/design/sets/world.md §4.3)

Status: complete

Waypoint layer of the connective world (`docs/design/sets/world.md` §4). Region `persian_gates`, set
`parsa`, base level 6, world rect C 1112..1127, R 330..345.

World rect C 1112..1127, R 330..345; local (c, r) = world (C - 1112, R - 330); local level 0 =
world level 6. A narrow defile: the road runs west to east along r 7..8, climbing two levels on
ramps from the west mouth (portal `gates_w`, world 4) to the east mouth (portal `gates_e`); cliffs
of limestone rise on both sides (+6..+9, impassable, snow on the tops, Persian oaks on ledges);
the walled station of the guards stands beside the road at the west mouth where the gorge widens
(north of the road rather than across it, so the road keeps its own line); a watchtower on a
ledge and a beacon above. A guarded pass on the road to Pārsa in 470 (the battle of 330 BC is
later; the site is debated).

- Portals: `gates_w`, `gates_e`.
- Ground: copied from the base below (`worldgen.waypoint.ground`), then shaped here; landmarks
  the city set has not drawn yet are provisional ids (`plan/provisional.py`) at their final
  footprint and draw as labelled placeholders.

Build: `tools/worldgen/build.sh persian_gates [--preview]`.
