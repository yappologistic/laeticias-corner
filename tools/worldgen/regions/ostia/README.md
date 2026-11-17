# Layer `ostia`

Region: `ostia` (Ostia and Portus, world C 100..170, R 184..239, base level 1), `rome.md` §3.7.
The template waypoint town: copy its structure for other towns.

Status: first version (WG0).

Built:
- Coast from the base layer; water one level below land so banks and quays read as embankments.
- The Tiber from Rome's south edge (local (52, 0), matching the base's course) to its mouth at
  about (26, 46), quays with mooring posts on the Ostia bank, river lane `tiber_ostia`.
- Portus: `rome.portus_hexagon` (20 × 18) over a hexagonal basin with a quay ring, its mouth to
  Claudius's outer harbour, moles, `rome.portus_lighthouse` on the mole island, the Fossa Traiana
  canal to the Tiber, warehouses along a service street.
- Ostia: decumanus (the Via Ostiensis, leaving north-east to portal `ostiensis` at (63, 0)),
  cardo to the shore, lanes, forum with the Capitolium (`rome.r_temple` as kit) and statues,
  insulae, shop-houses, warehouses, shops and a bakery filled by `houses`, yards with amphorae,
  fountains and crossroads shrines.
- A road from Portus over the Tiber on bridge spans to Ostia; tombs and umbrella pines along the
  Via Ostiensis; market gardens east and north.

Missing / deviations:
- All `rome.*` ids are provisional (no `rome` set catalog or art yet); they draw as placeholders.
- `ostia_town` is a kit area in `rome.md`, built here from kit pieces; the Capitolium is the
  generic `rome.r_temple`, and the shipping guilds' square, the theatre and the barges (actors)
  are not built yet.
- Portal `ostiensis` needs Rome's layer to end its Via Ostiensis on (163, 183) next to it.
- No region file yet (theme, life, cards).
