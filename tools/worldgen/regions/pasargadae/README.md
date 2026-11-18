# Pasargadae, spring c. 470 BC (docs/design/sets/world.md §4.3)

Status: complete

Waypoint layer of the connective world (`docs/design/sets/world.md` §4). Region `pasargadae`, set
`parsa`, base level 5, world rect C 1176..1203, R 260..287.

World rect C 1176..1203, R 260..287; local (c, r) = world (C - 1176, R - 260); local level 0 =
world level 5. The tomb of Cyrus on its six steps (c 4..8, r 18..22) with the magi's guardhouse
beside it (Arrian 6.29); Palace P facing its garden of narrow stone channels and square basins
(c 12..23, r 4..13), cypresses and planes along the channels; the road from Pārsa comes in over
the south edge (portal `pasargadae_s`, c 14) and runs north to the garden; paths to the tomb.

- Portals: `pasargadae_s`.
- Ground: copied from the base below (`worldgen.waypoint.ground`), then shaped here; landmarks
  the city set has not drawn yet are provisional ids (`plan/provisional.py`) at their final
  footprint and draw as labelled placeholders.

Build: `tools/worldgen/build.sh pasargadae [--preview]`.
