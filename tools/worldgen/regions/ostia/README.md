# Ostia layer

Status: complete

Ostia and Portus, AD 126 (`rome.md` §3.7). World rect C 100..170, R 184..239; local (c, r) =
world (C − 100, R − 184); local level 0 = world level 1; sea, river and canals at local −1.

- `layout.py`: Claudius's outer harbour cut into the shore with its moles and the lighthouse
  island (`portus_lighthouse`), Trajan's hexagon (`portus_hexagon`, its own quays and
  warehouses) with its canal to the Tiber, the Fossa between the outer harbour and the Tiber,
  warehouses on Portus's service street; the Isola Sacra with its tombs and gardens; Ostia's
  decumanus, cardo, forum with the Capitolium (`ostia_capitolium`), the square of the shipping
  offices (`ostia_guilds`), river quays, insulae, warehouses, shops in lanes, salt pans; the Via
  Ostiensis between tombs and market gardens to portal `ostiensis` (63, 0). Shared helpers from
  `regions/rome/common.py`.
- `assets/regions/ostia.json`: theme, populations, lane tokens, cards.
- Lanes: `portus` (its first two points are the plan's sea-lane ends), `portus_canal`,
  `tiber_ostia` (meets Rome's `tiber` lane across the edge).
- Second pass: the town grown north along the river and the road to the Porta Romana (r 12),
  warehouses along the river, insulae, shops, bakeries and fulleries round the forum in lanes
  (the shared `quarter()` filler); the Capitolium at the forum's head across the decumanus, the
  theatre (`ostia_theatre`, once the set catalog carries it) on the decumanus with the guilds'
  square behind its stage; mooring posts on both moles of Claudius's harbour and along the river
  quay; the Via Portuensis from Rome over the north edge (portal `portuensis`, local (40, 0)).
- The bridges over the canals and the Tiber are `world.bridge_arch`.

Build: `tools/worldgen/build.sh ostia [--preview]`.

Life and text: `life.py` (built by `tools/worldgen/build.sh --city ostia`) writes `assets/regions/ostia.json`; the townsfolk and trades are Rome's, borrowed through `regions/rome/townlife.py`.
