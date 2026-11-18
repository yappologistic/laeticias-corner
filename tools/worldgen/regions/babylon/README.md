# Babylon, spring c. 470 BC (docs/design/sets/world.md §4.3)

Status: complete

Waypoint layer of the connective world (`docs/design/sets/world.md` §4). Region `babylon`, set
`parsa`, base level 1, world rect C 1036..1071, R 285..316.

World rect C 1036..1071, R 285..316; local (c, r) = world (C - 1036, R - 285); local level 0 =
world level 1. The Euphrates runs through from c 12, r 1 to c 20, r 27 (the base's river). On the
east bank the Royal Road comes in over the north edge (portal `babylon_n`) through the Ishtar Gate
(c 30..35, r 1..4) and down the processional way (c 32..33, r 5..18) toward Etemenanki (c 20..31,
r 17..28; shown standing, its state under Xerxes is debated); the inner wall runs west of the gate
(c 18..29, r 2..3) with towers every three tiles; houses of the east bank between them; the road
leaves east for Susa (portal `babylon_e`). On the west bank houses among date palms, groves north
of the wall, shadufs on the canal banks; river boats land at a quay (lane `babylon`); a
timber bridge stands in for the stone-piered bridge Herodotus describes (1.186).

- Portals: `babylon_n`, `babylon_e`.
- Ground: copied from the base below (`worldgen.waypoint.ground`), then shaped here; landmarks
  the city set has not drawn yet are provisional ids (`plan/provisional.py`) at their final
  footprint and draw as labelled placeholders.

Build: `tools/worldgen/build.sh babylon [--preview]`.
