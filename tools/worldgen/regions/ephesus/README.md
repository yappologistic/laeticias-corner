# Ephesus (Ephesos), summer 432 BC (docs/design/sets/world.md §4.2)

Status: complete

Waypoint layer of the connective world (`docs/design/sets/world.md` §4). Region `ephesus`, set
`athens`, base level 1, world rect C 832..851, R 235..255.

World rect C 832..851, R 235..255; local (c, r) = world (C - 832, R - 235); local level 0 = world
level 1. The harbour at the Kaystros mouth in the west (the lane `ephesus` meets the Aegean base
lane); the town on its slope in the north-east (+1..2) with the road east over the hills to
Sardis (portal `ephesus_e`); across the Kaystros on a timber bridge the archaic Artemision (c 2..17,
r 13..20, entrance west) in the wet plain, marsh and reeds round it.

- Portals: `ephesus_e`.
- Ground: copied from the base below (`worldgen.waypoint.ground`), then shaped here; landmarks
  the city set has not drawn yet are provisional ids (`plan/provisional.py`) at their final
  footprint and draw as labelled placeholders.

Build: `tools/worldgen/build.sh ephesus [--preview]`.
