# Corinth, summer 432 BC (docs/design/sets/world.md §4.2)

Status: complete

Waypoint layer of the connective world (`docs/design/sets/world.md` §4). Region `corinth`, set
`athens`, base level 1, world rect C 553..575, R 280..305.

World rect C 553..575, R 280..305; local (c, r) = world (C - 553, R - 280); local level 0 = world
level 1. Lechaion on the gulf in the north-west (moles, a beacon, the lane `lechaion` meets the
Ionian route's base lane); the town with the archaic temple of Apollo (c 4..15, r 10..15); the
diolkos (c 15..16, r 2..21), the paved ship trackway across the isthmus; Kenchreai on the
Saronic side (c 17..22, r 14..19; lane `kenchreai`); Acrocorinth as ground (c 0..10, r 16..25,
rising to +7) with the summit sanctuary on top and a stepped path up. The Megarid road arrives
over the north edge (portal `corinth_n`).

- Portals: `corinth_n`.
- Ground: copied from the base below (`worldgen.waypoint.ground`), then shaped here; landmarks
  the city set has not drawn yet are provisional ids (`plan/provisional.py`) at their final
  footprint and draw as labelled placeholders.

Build: `tools/worldgen/build.sh corinth [--preview]`.
