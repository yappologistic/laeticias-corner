# Rome layer

Status: built. Every landmark with usable art stands at its bible rect and level; the six
listed under "Waiting on art" keep their footprints with stand-ins. Mark the layer complete
here once they are placed (V4 then makes a missing landmark an error).

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
`trajan_baths` (no art), `testaccio` (set footprint 12 × 11, bible 11 × 12: built as a terraced
mound of sherds). `tarpeian` is the tufa cliff itself (art: not a landmark). The Emporium item
covers the Horrea Galbana's rect, so a kit quay and warehouses stand in for it; the island and
the four bridges stand on mud until the set catalog marks them `on: water`.

Build: `tools/worldgen/build.sh rome [--preview]`.
