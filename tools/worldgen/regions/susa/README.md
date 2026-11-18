# Susa, spring c. 470 BC (docs/design/sets/world.md §4.3)

Status: complete

Waypoint layer of the connective world (`docs/design/sets/world.md` §4). Region `susa`, set
`parsa`, base level 1, world rect C 1080..1103, R 315..340.

World rect C 1080..1103, R 315..340; local (c, r) = world (C - 1080, R - 315); local level 0 =
world level 1. The citadel mound (+4, earth faces, packed earth on top) carries Darius' palace
(c 0..13, r 2..13: the apadana of bull-capital columns beside courts faced with glazed-brick
archers, lions and winged bulls); a stepped way climbs its south flank; the Shaur (the base's
Karun) runs diagonally through c 14..18; the town of mudbrick houses south of the mound and on
the east bank; the Royal Road enters from the west (portal `susa_w`), crosses the Shaur on a
timber bridge and leaves east for the Persian Gates (portal `susa_e`); river boats from the
Gulf land at a quay (lane `susa`).

- Portals: `susa_w`, `susa_e`.
- Ground: copied from the base below (`worldgen.waypoint.ground`), then shaped here; landmarks
  the city set has not drawn yet are provisional ids (`plan/provisional.py`) at their final
  footprint and draw as labelled placeholders.

Build: `tools/worldgen/build.sh susa [--preview]`.
