# Rome layer

Status: built. Every landmark with usable art stands at its bible rect and level (Saturn and the
Templum Pacis a tile off it, below); the five without art (`saepta`, `iseum`,
`stadium_domitian`, `pompey_theatre`, `trajan_baths`) are dressed as what stood there, not placed
as provisional placeholders, because a provisional entry draws nothing in the engine (QA4 V-B-001:
the Baths of Trajan read as an empty lawn); each is placed by itself once a real catalog entry
gives the bible's footprint. The island, bridges and Testaccio stand on their corrected art. Mark the layer complete here once they are
placed (V4 then makes a missing landmark an error).

Second pass (world-rome-connect): the Argiletum runs from the Forum past the Forum of Nerva's
east side into the Subura (the Templum Pacis moved a tile east); the Vicus Iugarius enters the
Forum between Saturn (moved a tile west) and the Basilica Iulia; mooring posts (`rome.quay`)
along the Emporium's wharf and the river road's embankment; the Via Portuensis to portal
`portuensis` (44, 159); the Via Aurelia crosses the Janiculum in a cutting at street level
between tufa faces (no ramps: `world.ramp` has no art and stood on the sightline, QA4 V-B-004); ways over the decks of the bridges and across the island once the art joins
them, the water left under them; the Via Ostiensis along the Emporium's wharf once the Porticus
reaches Testaccio. `quarter()` (the neighbourhood filler) lives in `common.py`, shared with
Ostia and Brundisium.

Rome on the Parilia, 21 April AD 126 (`docs/design/cities/rome.md`). World rect C 96..271,
R 24..183; local (c, r) = world (C − 96, R − 24); local level 0 = world level 1.

- `layout.py` builds the layer in stages: levels as one array (the Capitol and Arx, the
  Quirinal behind the Markets, the Velia, Oppian and Esquiline, the Palatine on brick
  substructures, the Aventine with the Servian wall's tufa face, the Caelian above the Appia,
  the Janiculum ridge, edges bent toward the world, stair runs carved in), ground, the Tiber,
  ways, landmarks, stair runs, districts, stand-ins for landmarks without usable art, the
  aqueduct, the Capitol, Forum, fora, Velia and Palatine detail, the quarters (lanes, insulae,
  domus, shops on the streets, yards), the Campus Martius, Transtiberim and the Janiculum, the
  river port, the Campagna, named nodes, finishing passes, previews.
- `common.py` holds the helpers the Roman layers share (stair runs, lanes, kit that opens on a
  street, meeting the world at the edges, clean-up of kit whose slots cannot be reached); the
  `ostia` layout loads it by path.
- `assets/regions/rome.json` is the region's life and text: theme, district populations,
  figures, groups, events with their routes over the named nodes, chains, lane tokens, cards.
- Portals: `aurelia_w` (0, 96) at the foot of the Via Aurelia's stair over the Janiculum,
  `appia_se` (175, 150), `ostiensis` carried across the south edge at (67, 159). Lane: `tiber`
  (from the Ostia edge up past the Emporium, the Forum Boarium and the island to the north edge).

Waiting on art (footprints kept, stand-ins built, placed automatically when the set catalog
holds them at the bible's footprint): `saepta`, `iseum`, `stadium_domitian`, `pompey_theatre`,
`trajan_baths` (no art: the Baths of Trajan are a paved block of vaulted halls with two exercise
yards, gardens and a ring of planes). `tarpeian` is the tufa cliff itself (art: not a landmark).
The Emporium item (corrected to 11 × 25) is not placed: its walk tiles split the wharf in two at
the crane (r 147..149), so the Via Ostiensis could not run along it; a kit quay with moorings and
warehouse rows stands in until the wharf is walkable from end to end.

Build: `tools/worldgen/build.sh rome [--preview]`.
