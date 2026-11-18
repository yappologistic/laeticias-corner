# The Euphrates crossing, spring c. 470 BC (docs/design/sets/world.md §4.3)

Status: complete

Waypoint layer of the connective world (`docs/design/sets/world.md` §4). Region `euphrates_crossing`, set
`parsa`, base level 4, world rect C 1008..1023, R 170..185.

World rect C 1008..1023, R 170..185; local (c, r) = world (C - 1008, R - 170); local level 0 =
world level 4. The river (c 6..9) with landing stages on both banks (r 7..9) where round hide
boats (quffa, Herodotus 1.194) ferry goods across on their lane; a bridge of boats beside them
carries the Royal Road, so caravans and couriers cross on foot (the site and the means are
uncertain: Xenophon's army waded at Thapsacus); a relay station on the east bank (c 11..14,
r 3..6); a camp of tents on the west bank (c 0..3, r 10..13); tamarisks, reeds and poplars.

- Portals: `euph_w`, `euph_e`.
- Ground: copied from the base below (`worldgen.waypoint.ground`), then shaped here; landmarks
  the city set has not drawn yet are provisional ids (`plan/provisional.py`) at their final
  footprint and draw as labelled placeholders.

Build: `tools/worldgen/build.sh euphrates_crossing [--preview]`.
