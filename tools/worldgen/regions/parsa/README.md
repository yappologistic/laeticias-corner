# Layer `parsa`

Region: `parsa` (Pārsa with Naqsh-e Rostam, world C 1136..1279, R 304..447, base level 4),
`docs/design/cities/persepolis.md`. Local coordinates and levels are the bible's.

Status: complete

Built, in order:
- Ground and elevation: the Marvdasht plain (level 0); Kuh-e Raḥmat behind the terrace (slope
  foot 7 with the fortification; limestone ridges stepping up to 11 at the east edge, cut by
  gullies every dozen rows with scree in them and fanning out at their feet, junipers, thorn
  and boulders; impassable above the wall), foothills north and south of the terrace in three
  benches; the terrace c 56..119, r 22..118 at 6 with
  `parsa.ashlar` faces, platforms for the Apadāna and Tripylon (7), the residential wing (7), the
  Tačara (8) and the Hadiš (9); quarry floor, cistern and a shrine ledge cut into the slope.
- Ways: the Royal Road (portal `royal_road_w`) into the gravel forecourt; the Pasargadae road
  past the glazed-brick gate, along the paradise wall and over the river by a ford (portal
  `pasargadae_n`); the town spur to the road station; terrace streets (landing → Gate → walled
  processional road → Hall forecourt; the street east of the Apadāna split round the Tripylon;
  courts north of the Hadiš and south of the Tačara; service streets; the haul road from the
  quarry through the wall and down a ramp to the masons' yard); the camp road; tracks.
- Water: the river along the north edge with willows and reeds, the canal from c 60 into the
  paradise, the garden's channels with basins and sluices, the channel along the terrace foot
  (fed by the terrace's drains, flowing south and west to the town canal), the town canal, field canals, the qanat line of shaft mounds.
- Landmarks at the bible's coordinates (V4), stairs as items with their levels checked (V3).
- Districts and fillers: paradise with the player's plot, forecourt, town (upper town, workers'
  quarter, craft quarter with brickfield, kilns, weavers, dyers, goldsmith, granary yard,
  Elamite shrine), village with threshing floors, fields, royal stables, station and caravan
  yard, cavalry and archery ground, the delegations' camp, southern pasture with folds, terrace
  detail (guards' braziers, banners, fire altars, incense, building-site stone, Hadiš kitchens,
  the archive corner), Naqsh-e Rostam with the Ka'ba and a fire altar.

Deviations from the bible (and why):
- `hall_100` is placed c 93..108, r 48..67: the set models the north portico (bible r 48..51)
  with the hall, so its footprint is 16 × 20 (V4 reports it as a warning).
- The south stair (rise 6) has no item in the set; it is built from six `parsa.stair_relief`
  flights climbing west along the south face (c 80..91, r 119..120), each landing a level higher,
  because `south_stores` (c 80..99, r 113..118) covers the bible's spot (c 84..88, r 118..121).
- The channel "along the terrace foot (c 50..51)" starts below the great stairway (c 49..55,
  r 37..54) instead of coming round it from the paradise, so no water and no crossing lie in
  the approach to the stair (the sightline `great_stair`, V15).
- The town spur runs at c 21..22 (bible c 22), leaving c 24 to the town canal beside it.
- The Apadāna's east stair is placed without a path (its portico is closed in the model); a
  short relief stair gives the west portico access from the terrace edge.
- Hadiš: only the west stair exists in the set (no north stair).
- The wall gates and openings in walls are gaps (`parsa.p_wall_gate` is not walkable).

- Field balks are grass and the Royal Road's last stretch has poplar rows, so roads read apart
  from field paths.
- `parsa.p_sledge` and `parsa.p_cart` are actors (world-tech §1.9), not items: the building site
  and the camp carry stacked drums, cranes and baggage instead.

The corridor c 99, r 86..103 down the residential wing's east side (the harem's walk tiles)
stays at the terrace's level 6, one below the wing's platform, with a street from the courts to
the Treasury's west door and its `gift_drop`/`guard` spots.

Art geometry this layer cannot fix (V7 warnings, listed in the report): the `treasurer`, the garrison's `drill` and the quarry's `cut` spots lie inside their own footprints
on tiles not declared walkable. The Tačara's south stair flights (c 64, c 69) do not line up with
its portico walk tiles (c 65, c 68); the stair's landing snaps to the nearest walk tile.

Previews draw split landmarks from the set's pieces; the throne stands on the Apadāna's walk tile
(2, 11) only when the geometry declares it walkable.
