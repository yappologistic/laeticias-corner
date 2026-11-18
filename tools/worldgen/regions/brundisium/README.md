# Brundisium layer

Status: complete

Brundisium, April AD 126 (`docs/design/sets/world.md` §4.1, `rome.md` §3.7). World rect
C 380..407, R 248..279; local (c, r) = world (C − 380, R − 248); local level 0 = world level 1,
the sea at −1 (world 0).

- `layout.py`: the Via Appia from portal `appia_brund_w` (c 0, r 18) to its end at the marker
  column (`rome.r_column_honor`, c 12, r 18; the surviving column's date is debated, so it is a
  plain one); the harbour (`brundisium_harbour`, c 8..23, r 6..17: a warehouse quay along its
  north side, the basin drawn south of it and open to the east) with a way along its quays over
  the geometry's walk tiles; open sea to the north and east; a
  mole off the fishermen's shore (c 6) and one closing the eastern arm (r 15) with its beacon;
  fish huts and drying racks on the west shore; the town south of the road (insulae, warehouses,
  domus, shops) in lanes off a cardo and a decumanus.
- The harbour lane `brundisium` runs from the basin out of its eastern mouth to the harbour mouth (local c 24, r 8 =
  world (404, 256)), where the base's `ostia_brundisium` lane ends and its `ionian_crossing`
  starts (port `brundisium`).
- Deviations from the plan: the plan's moles (c 0..7, r 10..11 and c 24..27, r 14..15) fall on
  land in the base's coast, so the west mole runs north into the sea at c 6 and the east one
  along r 15 off the harbour's eastern arm; the Ionian lane leaves from the harbour mouth
  (c 24, r 8), the plan's c 26, r 22 being land.
- Region file `assets/regions/brundisium.json` (written by `build.sh --life`).

Build: `tools/worldgen/build.sh brundisium [--preview]`.
