# The world: one continuous map from the corner to Pārsa

This is the master plan of the single, continuous game world: Laeticia's corner, Rome, Athens and
Pārsa, and the land and sea between them, on **one map the player can scroll across without a
loading break**. The overview map is a zoomed-out view of this same world used for fast travel.
Read this file first; the city files (`rome.md`, `athens.md`, `persepolis.md`) give each region's
detail in local coordinates on top of the region origins fixed here. Sources are in `sources.md`.

Contents: 1 regions and moments · 2 scale · 3 coordinates and camera · 4 elevation, coasts,
rivers · 5 the world plan · 6 the connective stretches · 7 the corner · 8 time on one map ·
9 region themes and blending · 10 data model · 11 shared art kinds · 12 civilization scope
(shared rules) · 13 overview map and fast travel · 14 engine capabilities · 15 respect and honesty.

---

## 1. Regions and their moments

| Region id | Name | Moment | Region size (tiles) | Mood in one line |
|---|---|---|---|---|
| `corner` | Laeticia's Corner | timeless | 96 × 112 (buildable plot 20 × 20) | a quiet green headland at the edge of the known world, where the roads begin |
| `rome` | Roma | April AD 126, under Hadrian | 176 × 160 | warm brick and gilded bronze in honeyed light; fountains, carts, a city of a million voices |
| `athens` | Athens · Ἀθῆναι (Athênai) | summer 432 BC, the last summer of peace | 160 × 160 | painted marble glittering above olive dust; cicadas, sea wind, the Parthenon just finished |
| `parsa` | Pārsa · تخت جمشید (Persepolis) | spring c. 470 BC, under Xšayāršā (Xerxes I) | 144 × 144 | a stone forest of columns against the mountain, snow on the peaks, water singing in channels |

Between them lie **connective stretches** (§6): Italy, the Ionian Sea, mainland Greece, the
Aegean, Ionia and Lydia, Anatolia, Mesopotamia, the Zagros, the Iranian plateau. Each stretch
belongs to the time of the nearest city (§8).

---

## 2. Scale: "true buildings, squeezed gaps"

| Quantity | Rule (64 × 32 px tiles) | Why |
|---|---|---|
| City architecture, horizontal | **1 tile edge = 4 m** at landmark scale `s = 1` (32 voxels per tile edge, 8 per metre) | the Parthenon becomes 8 × 17 tiles, one column per tile along its front |
| City architecture, vertical | **10 px per metre** | artgen draws one voxel of height as one pixel (0.82 of true 2:1 dimetric); 10 px/m = 1.25 × 8 restores true-looking proportions |
| Landmark scale `s` | per landmark; footprint and height both × `s` | only giants get `s < 1` (Colosseum, Circus Maximus, the Persepolis terrace) |
| Gaps inside a city | compressed 2.5–5 × (stated per city) | a whole walled city fits in 144–176 tiles |
| Connective land and sea | **symbolic: about 5–10 km per tile** | Rome to Pārsa is about 3,700 km; the journey becomes a sequence of short, rich set pieces with compressed country between |
| Waypoint towns (Brundisium, Corinth, Delos, Ephesus, Sardis, Babylon, Susa…) | 16–36 tiles each, landmark scale `s ≈ 0.5` | small set pieces, recognisable silhouettes, not full cities |
| People, animals, small props, houses, stalls | **toy scale**: an adult 38–42 px tall, house doors about 46 px, a horse about 44 px at the withers | matches the existing kit (cottage ridge about 76 px, cat 29 px) |
| Terrain relief | 1 level = **16 px**; real relief strongly compressed | hills read as hills without dwarfing buildings |

Heights in all asset tables are pixels from the ground under the footprint centre to the top of
the sprite at 64 × 32 (halve at 32 × 16).

---

## 3. Coordinates and the camera

### 3.1 World plan coordinates

All plans use **plan coordinates**, like a normal north-up map: `c` = column, increasing
**eastward**; `r` = row, increasing **southward**; one cell = one tile; ranges are inclusive;
`w × h` = east–west × north–south extent.

- **World size: 1280 columns (east–west) × 448 rows (north–south) = 573,440 tiles** (justified in
  §5.1).
- **Region origin + local coordinates.** Each city file uses local plan coordinates `(c, r)` from
  its region's north-west corner. World coordinates are `C = origin_c + c`, `R = origin_r + r`.
  Origins: corner (0, 0); Rome (96, 24); Athens (576, 220); Pārsa (1136, 304).

### 3.2 One camera orientation for the whole world

The engine grid has `+x` down-right and `+y` down-left; the visible walls of a building are those
facing `+x` and `+y`. One continuous world needs one orientation. We choose the camera **from the
south-west**:

**Grid mapping: `tx = R`, `ty = 1279 − C`.** So north is up-left on screen, east up-right, south
down-right, west down-left. Grid dimensions: `x` 0..447, `y` 0..1279. (The catalog's neighbour-mask
names N/E/S/W stay grid-relative labels; they are not compass directions.)

Why south-west: in each city it shows the façades that matter most and puts the mountains behind.

| City | Seen well (faces south or west) | Hidden (faces north or east), shown by card and by the optional view rotation |
|---|---|---|
| Athens | Propylaia and the Acropolis approach, Parthenon west front with the Athena–Poseidon pediment and south colonnade, Nike bastion, theatre of Dionysos seating, Stoa Poikile, Pnyx, Piraeus and the sea in the foreground | Parthenon east front, Hephaisteion front, Odeion's north side |
| Rome | Capitoline temple, Curia, Basilica Aemilia, Temple of Mars Ultor, Trajan's Markets, Theatre of Marcellus arcades, the Palatine palace above the Circus Maximus, the Colosseum | Pantheon portico (north), temples of Saturn, Concord and Castor fronts |
| Pārsa | great double stairway, the Gate's west door with its bulls, the Apadāna west portico, the Tačara's south front with its relief stair, the Hadiš; Kuh-e Raḥmat behind the terrace | Apadāna north and east relief stairs, the Gate's east lamassu, the Hall of a Hundred Columns portico |

The far edges of the world on screen are the **north and east** edges: distant mountains there are
drawn as backdrops (§11). The south and west edges are near and open (sea in the west and south).

Lighting stays screen-relative (art lit from the upper left), as in the corner; the sun is not tied
to the compass.

### 3.3 View rotation (strongly recommended)

The voxel generator renders any of the four rotations of a model at no modelling cost. A 90° view
rotation (four camera directions) would show every hidden façade above. It is listed as an engine
capability (§14, item 11) and costs atlas space (×4 for landmarks). The city files are written for
the south-west view; with rotation, nothing in them changes except which sprites are used.

---

## 4. Elevation, coasts and rivers

- **Sea level = level 0.** Sea tiles are `sea` terrain at level 0 (animated, depth tint by distance
  from coast). Lakes and rivers sit at the level of their banks minus 0 (rivers are terrain on
  land, not cut channels).
- **Coastal plains = level 1.** City bases: Rome 1 (forum valley), Athens 1 (Agora), Pārsa 4 (the
  Marvdasht plain lies at about 1,600 m; it sits higher than the Mesopotamian plain so the Zagros
  climb reads). A city's local level is added to its base: world level = base + local.
- **Hills 2–7, scenic mountains 8–15.** Mountain bands (Apennines, the mountains of Arcadia,
  Taurus, Zagros, the Iranian plateau's ranges) are high-level `rock`/`snow` tiles with peak
  sprites; they are **impassable** except at marked passes, and the camera may fly over them.
  Walkers never enter them.
- **Cliff faces** for each level of difference on a visible edge (`edge/<material>_se`/`_sw`,
  stacked). Materials: `rock`, `ashlar`, `earth`, `brick`, `snow`, `coast` (sea cliff with surf
  foam).
- **Ramps and stairs** are items with `rise` and `axis`; walkers interpolate height.
- **Rivers:** Tiber, Anio (Rome); Ilissos, Kephisos, Eridanos (Athens); Kaystros and Paktolos
  (Ionia–Lydia); Halys; Euphrates; Tigris; Karun/Shaur (Susa); Pulvar and Kur (Pārsa); plus the
  corner's stream. Width 2–8 tiles, animated flow, reed and tree margins, fords and bridges where
  roads cross.

Level budget: Athens up to 11 (Acropolis plateau), Rome up to 8 (Capitol), Pārsa up to 13 (Hadiš)
with the mountain behind at 11–15, Zagros 10–15.

---

## 5. The world plan

### 5.1 Size and why

- Real span: Rome (12.5° E, 41.9° N) to Pārsa (52.9° E, 29.9° N) is about 3,700 km east–west and
  about 1,300 km north–south. A 1280 × 448 world keeps the real 2.8 : 1 shape.
- The three city regions need 480 columns between them; the remaining 800 columns carry nine
  connective stretches of 32–128 columns each, enough for a road with set pieces, a sea crossing
  with islands, or a mountain band.
- Storage is small (2 bytes per tile for terrain and level, about 1.2 MB, plus sparse items), and
  32 × 32 chunks give 14 × 40 = 560 chunks, streamed around the camera (§14).
- Smaller (1024 × 512) would cramp the eastern half, where Anatolia, Mesopotamia, Susa and the
  Zagros all have to fit between Sardis and Pārsa. Larger would mostly add empty country.

### 5.2 Region and stretch layout (world plan coordinates)

```
 C:   0    96        272       408  448      576      736     832 880      1008   1104 1136     1279
R  0 +----+---------+---------+----+--------+--------+-------+---+--------+------+----+--------+
     |CORN| (hills)  Apennines  Adriatic Sea          Thrace & Hellespont  Anatolian plateau     |
  24 |ER  +---------+          \          \           (north)       |   Phrygia      Zagros  Iran |
     |    |  ROME   | Tibur     \  Adriatic \                       |   . Halys       |  plateau  |
 112 |    | (176 x  | Alban Mt   \__________\_______                |   Cappadocia    |  (scenic) |
     |~~~~|   160)  |  Appia ----- Capua -- Beneventum              |    \            |           |
 184 |~~~~+---------+    Vesuvius    \______ Brundisium  Corcyra    |  Euphrates      |  Pasargadae
     |~ Ostia/Portus      Tyrrhenian     ~~~ Ionian ~~~ Delphi        |  crossing       |    260-287
 220 | ~~~~~~~~~~~~~~ Sea ~~~~~~~~~~~~~~~~  Sea (seam) Gulf of   +-------+ Sardis    \    |           |
     | ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ Corinth  Corinth|ATHENS | Ephesus   Euphrates   |
 304 | ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~  Olympia       | (160 x| Delos  Taurus  \ Babylon  +--------+
     | ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~  Arcadia  Sparta|  160) | Aegean  Cyprus   Tigris |  PARSA |
 380 | ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ +-------+ ~~~~~ Levant  Susa  Gates (144 x |
 447 | ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ Persian Gulf |   144) |
     +--------------------------------------------------------------------------------------+--------+
```

(The diagram is schematic; the tables are authoritative.)

| Id | Region / stretch | World rect (C, R) | Base level | Time |
|---|---|---|---|---|
| `corner` | Laeticia's Corner | C 0..95, R 0..111 | 1 | timeless |
| `rome` | Roma | C 96..271, R 24..183 | 1 | AD 126 |
| `athens` | Athens with Piraeus, Eleusis and Pentelikon | C 576..735, R 220..379 | 1 | 432 BC |
| `parsa` | Pārsa with Naqsh-e Rostam | C 1136..1279, R 304..447 | 4 | c. 470 BC |
| `tyrrhenian` | Tyrrhenian Sea | C 0..300 south and west of Italy (R 112..447) | 0 | AD 126 |
| `latium_italy` | Italy: Latium, Campania, Samnium, Apulia | land C 140..407, R 0..290 (outside Rome) | 1–6 | AD 126 |
| `apennines` | Apennine band (scenic) | diagonal from C 240..300, R 0..30 to C 340..380, R 150..230 | 8–12 | AD 126 |
| `adriatic` | Adriatic Sea | C 300..447, R 0..230 (east of Italy's coast) | 0 | seam |
| `ionian_sea` | Ionian Sea (time seam) | C 408..471, R 180..447 | 0 | seam |
| `greece` | Mainland Greece: Epirus, Phocis, the Gulf of Corinth, the Peloponnese, Megara | land C 448..575, R 150..447 | 1–7 | 432 BC |
| `arcadia` | Mountains of Arcadia (scenic) | C 490..550, R 330..360 | 8–11 | 432 BC |
| `attica_north` | Northern Attica: Parnes, olive country, the Academy, Eleusis | C 556..735, R 150..219 (and Eleusis C 556..575, R 220..250) | 1–8 | 432 BC |
| `saronic` | Saronic Gulf with Aegina | C 560..735, R 380..447 | 0 | 432 BC |
| `aegean` | Aegean Sea and islands | C 736..831, R 150..447 | 0 | 432 BC |
| `thrace` | Thrace and the Hellespont | C 736..879, R 0..149 | 1–5 | 432 BC |
| `ionia_lydia` | Ionian coast and Lydia | C 832..879, R 150..300 | 1–4 | 432 BC (coast) / 470 BC (Sardis), seam between |
| `anatolia` | Anatolian plateau: Phrygia, the Halys, Cappadocia | C 880..1007, R 40..260 | 5–7 | 470 BC |
| `taurus` | Taurus band (scenic) | C 900..1000, R 240..280 | 10–14 | 470 BC |
| `east_med` | Eastern Mediterranean, Cyprus, the Levant coast | C 880..1007, R 280..447 | 0–3 | 470 BC |
| `mesopotamia` | Euphrates and Tigris plains, Babylon | C 1008..1079, R 160..400 | 1 | 470 BC |
| `susiana` | Susa and its plain | C 1080..1103, R 290..360 | 1–2 | 470 BC |
| `syrian_steppe` | Syrian steppe and desert edge | C 1008..1060, R 300..447 (south of the Euphrates) | 1–2 | 470 BC |
| `persian_gulf` | Head of the Persian Gulf | C 1050..1135, R 400..447 | 0 | 470 BC |
| `zagros` | Zagros band with the Persian Gates pass | C 1104..1135, R 120..399 | 10–15 | 470 BC |
| `iran_plateau` | Iranian plateau north of Pārsa (with Pasargadae) | C 1136..1279, R 0..303 | 4–12 | 470 BC |

### 5.3 Routes

| Route | Path (world C, R waypoints) | Carries |
|---|---|---|
| The corner's old road | corner jetty area (34, 96) → (95, 88) → Rome west gate area (100, 96) | walkers, a cart, sheep |
| The corner's sea lane | corner jetty (34, 108) → down the coast → Portus (124, 214) | a small coasting boat |
| Tiber | Rome (local 64, 159 → world 160, 183) → Portus/Ostia mouth (126, 226) | barges towed upstream |
| Via Appia (+ Via Traiana from Beneventum, built by Trajan in AD 109) | Rome SE (271, 168) → Alban hills (292, 160) → Capua (326, 206) → Beneventum (350, 214) → Brundisium (392, 262) | travellers, carriages, ox carts, milestones every 8 tiles |
| Roman sea lanes | Alexandria grain ships arrive from the south edge (200, 447) → Portus; Ostia → Brundisium round the toe of Italy (dotted, off the road) | merchantmen under sail |
| Ionian crossing (seam) | Brundisium (400, 270) → mist band (436, 270); Greek side: mist band (446, 250) → Corcyra (448, 212) → Gulf of Corinth (472, 276) → Lechaion (556, 284) | Roman ships on the west half, Greek ships on the east half (§8) |
| Isthmus and Saronic Gulf | Lechaion → diolkos (ship-trackway across the isthmus) → Kenchreai (572, 296) → Piraeus (Athens local 20, 140 → world 596, 360) | triremes, merchant ships, ox teams on the diolkos |
| Aegean lanes | Piraeus → Delos (782, 338) → Ephesus (840, 246); Piraeus → Hellespont (800, 80) | triremes, grain ships from the Black Sea |
| Royal Road (Herodotus 5.52–54: Sardis to Susa, 111 stations) | Sardis (870, 210) → Phrygia (912, 150) → Halys crossing (958, 128) → Cappadocia (985, 150) → Euphrates crossing (1015, 178) → along the Euphrates → Babylon (1054, 300) → Susa (1092, 326) → Persian Gates (1120, 338) → Pārsa (Pārsa local 0, 50 → world 1136, 354) | couriers, caravans, delegations, travellers with sealed documents. Herodotus's road ran from the Euphrates through Armenia and Matiene to Susa; the game's road follows the Euphrates through Babylon instead, which was also a main route (Cyrus the Younger's army marched it in 401 BC); the overview card says so |
| Pārsa–Pasargadae road | Pārsa north edge (1190, 304) → Pasargadae (1190, 286) | riders, carts |
| Gulf lane | Persian Gulf head (1080, 420) → Susiana canals | reed and plank boats with dates, pearls, timber |

---

## 6. The connective stretches

Each stretch is worth scrolling: a road or sea lane with life on it, a few tiny named waypoint set
pieces, farms or herds, a shrine, and a recognisable landscape. **M** = must-have, **N** = nice.

| Stretch | Landscape | Life along it | Waypoint set pieces (world rect) | M/N |
|---|---|---|---|---|
| Corner borderland | green hills, a dell with mist, hedgerows | shepherd, a wayside shrine (fictional, rustic), a milestone with no inscription | — | M |
| Latium and Tibur | rolling campagna, umbrella pines and cypresses, vineyards | villas, vine-dressers, an aqueduct arcade crossing the plain toward Rome | **Hadrian's Villa at Tibur** (under construction since c. AD 118: the Maritime Theatre, pools, workers) C 272..303, R 40..79 (N); **Alban Mount and lake** with the sanctuary of Jupiter Latiaris on the summit C 278..311, R 130..175 (M) | M |
| Via Appia and Campania | straight paved road (basalt polygons), tombs and pines at the roadside, milestones, Campanian farmland, the broken cone of Vesuvius after AD 79 on the horizon | carriages, mule drivers, a relay station (*mutatio*) with a change of mules, an inn (*caupona*) | **Capua** amphitheatre silhouette C 318..333, R 198..213 (N); **Beneventum** with Trajan's arch (AD 114) C 344..355, R 208..219 (N); **Brundisium** harbour with a marker column at the end of the Appia (two columns stand there today, one now in Lecce; their date is debated, so `rome.md` §3.7 shows one plain column [checked: consistency with rome.md]), warehouses, ships C 380..407, R 248..279 (M) | M |
| Apennines | scenic mountain band, beech and oak woods, snow on top in April | transhumant shepherds and flocks on the drove road | — | M |
| Ionian Sea (seam) | open sea with swell, the island of Corcyra (Kerkyra) | ships under sail, dolphins, gulls; a mist band at C 430..445 marks the seam of time (§8) | **Corcyra** town and harbour C 440..455, R 200..225 (N) | M |
| Western Greece and the Gulf | the long Gulf of Corinth between mountains; olive terraces, goat paths | fishing boats, a ferry, pilgrims to Delphi | **Delphi** on its mountainside: the 6th-century temple of Apollo, the Athenian treasury, the Sacred Way C 500..519, R 250..265 (M); **Olympia** with the Temple of Zeus (c. 456 BC) and the workshop where Pheidias made the Zeus statue C 470..491, R 320..340 (N); **Sparta**: villages along the Eurotas, no walls (Sparta was unwalled in the 5th century) C 515..535, R 360..385 (N); **Corinth**: archaic temple of Apollo, Acrocorinth, the diolkos, harbours of Lechaion and Kenchreai C 553..575, R 280..305 (M) | M |
| Northern Attica and the Saronic Gulf | olive country under Mount Parnes; the gulf with Aegina offshore | farmers, charcoal burners on the road from Acharnai; triremes and merchant ships in the gulf | **Eleusis**: the Telesterion of the Mysteries C 556..575, R 222..250 (M); **Academy** grove C 560..575, R 205..219 (N) | M |
| Aegean | deep blue sea, the Cyclades as small islands (Delos, Rheneia, Naxos, Paros, Tenos, Andros) | triremes, merchant ships, fishing boats; the meltemi wind whitening wave crests | **Delos**: the sacred lake, the Naxian lions, the sanctuary of Apollo C 775..790, R 330..345 (M) | M |
| Thrace and the Hellespont | northern coast, the narrow strait | grain ships coming from the Black Sea | — | N |
| Ionia and Lydia | river valleys of the Kaystros and Paktolos, fertile and green | the Royal Road begins | **Ephesus**: harbour, the archaic Artemision C 832..851, R 235..255 (M); **Sardis**: acropolis, the Paktolos with its gold-bearing sands, the satrap's palace, the first station of the Royal Road C 860..879, R 200..219 (M) | M |
| Anatolian plateau | broad uplands, steppe grass, distant volcanic cone of Mount Argaios (Erciyes) | Royal Road stations every 12 tiles, caravans of camels and donkeys, couriers relaying, shepherds | **Halys crossing**: guarded gates and a station (Herodotus) C 950..965, R 120..135 (M); **Gordion** mound and city silhouette C 905..925, R 130..150 (N) | M |
| Taurus | scenic snowy band | — | — | M |
| Eastern Mediterranean and Levant | coast, Cyprus offshore, cedar forests on the Lebanon mountains | Phoenician ships, loggers dragging cedar | **Sidon / Byblos harbour and cedar loggers** C 990..1007, R 300..340 (N) | N |
| Euphrates crossing and Mesopotamia | flat alluvial plain, date-palm groves, canals, reed marshes, mud-brick villages | boats and rafts, shadufs lifting water, ox ploughs, herons | **Euphrates crossing** by boats (Herodotus) C 1008..1023, R 170..185 (M); **Babylon**: the Ishtar Gate in blue glazed brick, the processional way, the ziggurat Etemenanki, the Euphrates bridge, Esagila C 1036..1071, R 285..316 (M) | M |
| Syrian steppe | dry grassland to desert, heat shimmer | Arab caravans with dromedaries | — | M |
| Susiana | lush irrigated plain | farms, canals | **Susa**: the citadel mound with Darius's palace and its own apadāna, glazed-brick friezes of archers and lions C 1080..1103, R 315..340 (M) | M |
| Zagros | high scenic band, oak woods, snow, gorges | road through the pass, a station | **Persian Gates** pass: a narrow defile, a station and guards C 1112..1127, R 330..345 (M) | M |
| Iranian plateau (north of Pārsa) | high plains and ranges | herders, horses | **Pasargadae**: tomb of Cyrus on six steps, the palace gardens with stone channels, the gatehouse with the four-winged figure relief C 1176..1203, R 260..287 (M) | M |
| Persian Gulf | shallow shimmering sea, palms on the shore | boats with dates, pearls and timber | — | N |

Waypoint set pieces use the same kit as their nearest city plus 1–3 unique landmarks each; their
landmarks are listed in the relevant city file (Rome: Tibur, Alban Mount, Capua, Beneventum,
Brundisium, Ostia/Portus; Athens: Eleusis, the Academy, Corcyra, Delphi, Olympia, Sparta,
Corinth, Delos, Ephesus;
Pārsa: Sardis, Halys, Gordion, Sidon, Euphrates crossing, Babylon, Susa, Persian Gates,
Pasargadae).

---

## 7. Laeticia's Corner in the world

- **Where:** the north-west corner of the world, C 0..95, R 0..111: a fictional green headland
  north-west of Rome, beyond the last named places. On screen it is the far-left corner of the
  world.
- **Why there:** the corner's kit is temperate and northern (oaks, pines, blossom trees, cottages,
  barns, ducks and hens); it belongs at the cool, green edge of the map, not in the Mediterranean
  sun. It is the place the player lives in, outside history and outside time. From it an **old
  road** runs south-east into Rome's region and a **jetty** sends a small boat down the coast to
  Portus: every journey starts at home.
- **Contents:** the buildable plot (C 38..57, R 44..63, 20 × 20, as in `catalog.json`), a
  prebuilt borderland around it (meadows, a stream to the sea, a beech wood, a few fictional
  farmsteads, the jetty at C 28..36, R 100..111, a wayside shrine with no named god, sheep on the
  hills), and the misty dell that forms the seam with Rome (C 88..103).
- **Bounding the buildable area:** a low dry-stone wall with a gate marks the plot; build tools
  work only inside it (and in the small decorate zones of each city). The engine stores the plot as
  the only editable tile range; everything outside is prebuilt and locked. The wall's gate faces the
  old road.
- **Feel:** quiet. No crowds, soft birdsong, the corner's own day and night music, gentle sea
  sound from the west.

---

## 8. Time on one map: a world of memories side by side

Rome stands in AD 126, Athens in 432 BC, Pārsa in 470 BC. The map shows each region at its own
moment, **laid side by side as memories**, and uses the natural borders (sea, mountains,
borderlands) as the seams where one time gives way to another.

| Seam | Between | Where | How it looks |
|---|---|---|---|
| Corner ↔ Rome | timeless ↔ AD 126 | the misty dell, C 88..103 | soft mist, a dry-stone stile |
| Italy ↔ Greece | AD 126 ↔ 432 BC (558 years) | the Ionian Sea, mist band at C 430..445 | a pale golden sea-mist bank; ships sail into it and fade, and new ones sail out on the other side |
| Greek world ↔ Persian world | 432 BC ↔ 470 BC (38 years) | the Ionian coast between Ephesus and Sardis (C 852..859) | a faint haze over the Kaystros hills |
| Within each time | — | — | stretches belong to the nearest city's moment: Italy to AD 126 (milestones of Hadrian), Greece and the Aegean to 432 BC, everything east of Sardis to 470 BC |

How it is told lightly:

- When the camera centre crosses a seam, a small caption fades in at the top of the screen for
  three seconds: "Roma · April, AD 126", "Ἀθῆναι · summer, 432 BC", "Pārsa · spring, c. 470 BC".
  For waypoint towns, the caption names the town in small type under the era.
- The seams carry a soft chime and a gentle shimmer in the mist; no text walls.
- The overview map tints each time band in a slightly different paper colour and labels it with
  its year.
- The first time the player crosses a seam, one line appears: "Each land here is remembered as it
  was in one moment. The sea keeps the years apart."
- Nothing crosses a seam: walkers, ships and caravans turn back or fade inside the mist band, so
  Roman ships never moor at Corinth in 432 BC.

---

## 9. Region themes and blending

### 9.1 Theme per region and stretch

Each region and stretch has a theme: four grading keyframes (dawn, day, dusk, night), sky
gradients, haze, wind, weather kinds, ambience beds and (for cities and the corner) music. City
themes are specified in each city file (§8–9 there); stretch themes:

| Stretch | Day grading | Haze | Weather kinds | Ambience bed | Music |
|---|---|---|---|---|---|
| Corner | as today | none | rain (toggle) | birds / crickets | corner day/night |
| Latium–Italy | warm green-gold, soft | light warm haze | spring shower, cloud shadows | larks, distant cowbells, cart wheels on stone, wind in pines | none (Rome's music fades out) |
| Apennines | cooler, bluer | cool haze in valleys | low cloud, snow flurries on tops | wind, a raven, sheep bells far off | none |
| Seas (Tyrrhenian, Adriatic, Ionian, Aegean, Gulf) | deep blue water, bright | sea haze toward the horizon | breeze, whitecaps (meltemi in the Aegean) | waves, wind in rigging, gulls, the creak of a hull when a ship passes | none; a single slow drone at the seam mist |
| Mainland Greece | bright, dry, saturated | thin, warm | heat shimmer | cicadas, goat bells, wind in olives | Athens music only within its region |
| Ionia–Lydia | lush, green | light | shower | river water, frogs, larks | none |
| Anatolian plateau | wide, pale gold, cool sky | distance haze | wind gusts, cloud shadows racing over the steppe | steady wind, larks, camel bells on the road | a shepherd's pipe phrase once in a while (N) |
| Mesopotamia | humid gold, soft contrast | heavy warm haze | dust haze, still heat | frogs, reed rustle, shaduf creak, distant voices | none |
| Syrian steppe | bleached, high contrast | heat shimmer | dust breeze | dry wind, grit | none |
| Zagros | crisp, cold blue shadows | clear | snow flurries, mist in gorges | cold wind, ravens, a stream in a gorge | none |
| Iranian plateau | clear, high, slightly cool | very light | breeze | wind over grass, horse bells | Pārsa music only within its region |

### 9.2 Cross-fading

- Every region and stretch has an **influence field**: full weight inside its core, falling to zero
  across a **blend margin** outside its rect (cities: 32 tiles; waypoint towns: 12; stretches: 24).
  Weights are normalised; a smoothstep shapes the falloff.
- **Grading, sky and haze** use the weights at the **camera centre** (one grade per frame: cheap,
  no seams on screen). Weather is chosen per stretch and fades in and out with the weight.
- **Ambience beds** are mixed by the same weights (each bed's gain = weight × its own level), plus
  positional zones inside cities (forum crowd, water channels).
- **Music** belongs only to cities and the corner. When the camera leaves a city, its music fades
  out over the blend margin; the stretches between have no music, only their ambience, so arriving
  in a city feels like walking into its song. Re-entering a city starts its piece from a phrase
  boundary with a 4 s fade-in.
- **Day and night:** one world clock for everyone; each region grades the same hour in its own way.
- **Seams:** in the mist bands all ambience dips by 6 dB and a soft sustained drone plays; the
  caption appears on the far side.

---

## 10. Data model: a region-based world

```
assets/world/
  world.json           # size, region list with rects and blend margins, stretch list, routes,
                       # seams, clock settings, overview-map style
  chunks/              # terrain id + level per tile, 32 x 32 tiles per chunk, binary, compressed
  items.json           # every prebuilt item: id, world (C, R), rotation, variant; split by chunk
  paths.json           # walker path graphs per region (nodes in world coordinates)
  regions/<id>.json    # theme, figures, cards, walkers, events, decorate zones, journal for that region
  atlas/<id>.png/.json # one or more atlas pages per region (corner pages = today's atlas)
  audio/<id>/          # each region's music and ambience
assets/catalog.json    # gains "regions"; items, terrain and visitors gain optional "region"
```

**Catalog additions.** `"regions": [ { "id": "rome", "name": "Roma", "native": "Roma",
"moment": "AD 126", "rect": [96, 24, 271, 183], "base_level": 1 } ]`; items, terrain and visitors
gain an optional `"region"` (absent = corner or shared). New item fields:

| Field | Meaning |
|---|---|
| `"landmark": true` | unique, not in any build menu, clickable for a card |
| `"scale": 0.7` | documentation of `s` (read by the art generator) |
| `"rise": 6, "axis": "x"` | stairs and ramps |
| `"walk": [[dx, dy], ...]` | footprint tiles walkers may cross (porticoes, gates, colonnades) |
| `"occluder": true` | fade to 35 % when the cursor or a followed figure is behind it |
| `"emitters": [...]` | named effect points (smoke, incense, spray, fire) per rotation, like `smoke_at` |
| `"card": "<id>"` | card shown on click |

**`regions/<id>.json` (sketch):**

```json
{
  "id": "parsa",
  "origin": [1136, 304], "base_level": 4,
  "theme": { "grading": {"dawn": {}, "day": {}, "dusk": {}, "night": {}},
             "sky": {}, "haze": {}, "weather": [], "wind": {},
             "ambience": { "beds": ["amb/parsa_day.ogg"], "zones": [] },
             "music": { "day": "music/parsa_day.ogg", "night": "music/parsa_night.ogg" } },
  "figures": [ { "id": "xerxes", "presence": "present", "time": "day", "route": "apadana_audience" } ],
  "walkers": [ { "kind": "gardener", "count": 6, "zone": "paradise", "time": "day" } ],
  "chains":  [ { "id": "stone", "stations": ["quarry", "sledge_road", "hall_100_yard"], "carry": "block" } ],
  "schedule": [ { "at": "dawn", "scene": "fire_offering" }, { "at": "morning", "scene": "audience", "every_min": 12 } ],
  "events":  [ { "id": "audience", "route": "stairway_to_apadana", "cast": ["delegation_*", "usher"] } ],
  "decorate_zones": [ { "rect": [36, 12, 48, 24], "menu": "parsa_garden" } ],
  "cards":   { "xerxes": { "title": "", "epithet": "", "text": "" } },
  "journal": ["landmark:*", "figure:*", "delegation:*", "find:*"]
}
```

Coordinates inside a region file are local (added to `origin`). `presence` is one of `present`,
`statue` (clickable statue or relief), `memory` (translucent figure appearing at dusk near their
monument, fading at dawn, never interacting with the living), `shrine` (a god or hero shown
through an altar, image or symbol, with occasional apparitions), `reenactor` (a citizen playing
the part at a festival). All user-visible strings live in the region files.

**Save:** one world save: the corner plot, decorate zones, the clock, camera, per-region journals
and keepsakes.

---

## 11. Shared art kinds

| Key | Meaning |
|---|---|
| `landmark/<id>/<layer>/r<k>/f<n>` | large unique structures; layers `base`, `shadow`, `glow`; may be split into one-tile-wide diagonal **slices** (`.../s<i>`) for depth sorting against walkers |
| `figure/<id>/<anim>/f<n>` | named figures; animations as critters plus optional `act` (speaking, writing, playing, sculpting, pouring) |
| `walker/<kind>/<variant>/<anim>/f<n>` | anonymous people in 3–4 colour variants per kind; plus `carry/<item>` overlay frames for production chains |
| `ship/<kind>/<anim>/f<n>`, `caravan/<kind>/...` | movers on long routes (Roman merchantman, Roman river barge, trireme, Greek merchant ship, fishing boat, Phoenician ship, reed boat; camel and donkey caravans) |
| `edge/<material>_se`, `_sw` | one level (16 px) of cliff, wall or coast per material |
| `backdrop/<id>` | wide painted strip behind the north or east world edge (Alps and northern hills behind the corner and Rome; Rhodope and the Black Sea shore; the Caucasus haze; Kuh-e Raḥmat and the Zagros behind Pārsa), with a night variant |

---

## 12. Civilization scope: shared rules

Each city file carries its **entire civilization**, not only monuments: society in motion, a dress
reference, an occupations-and-work reference with production chains, a page on how the place is
run, how people lived (food, crafts, trade, money, writing, schooling, medicine, law, religion,
festivals, entertainment, baths, music, burial), the land beyond the walls (on the region map and
in the connective stretches), the empire or league at large, a year and a day in the life, and
knowledge and ideas. Shared rules:

- **Walkers are a cross-section.** In every city, notables are at most 5–10 % of the people seen;
  most are workers, women, children, traders, soldiers, priests, enslaved and freed people.
- **Enslaved people are shown with dignity**: at work, with names and families where the sources
  allow, never in chains as decoration, never as spectacle. Cards state facts plainly.
- **Production chains are visible**: walkers carry goods between stations (quarry → cart →
  sculptor's yard → temple; field → threshing floor → mill → bakery → stall; clay pit → potter →
  kiln → painter → market → ship). The engine needs carry overlays and station-to-station routes
  (§14).
- **The day and the year drive scenes**: each city has a day schedule (dawn sacrifices, markets,
  midday rest, baths, dinners, night watch) and a festival calendar. The world clock schedules
  scenes; the festival calendar is a list of events the owner may enable.
- **Ordinary people have names** typical of the period, and cards; the person is invented unless
  stated.
- **Dress and work tables cite their evidence** (reliefs, vase painting, sculpture, wall
  painting, textiles, texts) and list common mistakes to avoid.

---

## 13. Overview map and fast travel

- **Look:** the overview is generated from the world itself: each tile coloured by terrain and
  level, rendered north-up (not isometric), then styled as a hand-drawn map on aged
  papyrus-coloured paper: sepia ink coastlines, faded blue sea with small drawn waves, mountains as
  shaded triangles, rivers as fine blue lines, roads as dotted lines, small drawn icons for the
  three cities, the waypoint towns and the corner. Names in the game's UI font with native forms
  beneath. Each time band has a slightly different paper tint and its year.
- **Markers:** the corner (a small cottage), Roma (the Pantheon dome and a column), Athens (the
  Acropolis), Pārsa (the double stairway and two columns), plus waypoint towns as small dots that
  become clickable once seen.
- **Fast travel:** click a marker or any point. For distances under 200 tiles: an eased camera
  flight (ease-in-out, about 1.5 s, zooming out at mid-flight). For longer distances: the camera
  zooms out into the overview, a small symbol travels the route (a ship on sea legs, a rider on the
  Royal Road), then the camera zooms into the destination, about 2.5 s in all, skippable. Chunks,
  atlas pages and audio of the destination are prefetched during the flight.
- **Hover text:** journal progress ("23 of 40 found").
- **Opening it:** a map button in the dock and the `M` key; scrolling out past the last zoom level
  also opens it.

---

## 14. Engine capabilities (ordered by importance)

| # | Capability | What exactly | Notes |
|---|---|---|---|
| 1 | **Streamed giant world** | 1280 × 448 tiles in 32 × 32 chunks; load/unload chunks in a ring around the camera; terrain stored as compact binary; items sparse and bucketed by chunk | replaces the 20 × 20 map; the corner plot becomes the editable range |
| 2 | **Culling and batching at scale** | visible-chunk culling, per-chunk prebuilt static geometry for ground tiles, items drawn by row within visible chunks | the frame budget (under 2 ms CPU) must hold over a busy city |
| 3 | **Elevation** | integer levels per tile, stacked cliff/coast faces, ramps and stairs, items on raised tiles, height-aware picking | |
| 4 | **Large multi-tile landmarks and depth sorting** | sprites up to about 2400 × 1200 px; per-slice sorting or occlusion masks so walkers pass correctly behind and in front of colonnades | |
| 5 | **Multiple atlas pages streamed by region** | shared page plus each region's pages, loaded when the region's influence reaches the camera, unloaded later | draw calls stay in the low tens: sort by page |
| 6 | **Region themes with cross-fades** | influence fields, weighted grading, sky, haze and weather at the camera centre; ambience bed mixing; music handover with fades and silent stretches | |
| 7 | **Clickable figures and landmarks, cards, journal** | hover highlight, click opens a card; per-region journal; keepsakes | the core "wonder" loop |
| 8 | **Walkers on path graphs, schedules and production chains** | authored path graphs per region; walkers with routines driven by the world clock; carry overlays; station-to-station chains | |
| 9 | **Overview map and fast travel** | generated north-up overview texture (rebuilt by a tool, plus live corner thumbnail), markers, eased camera flight or zoom-out–travel–zoom-in, prefetch | |
| 10 | **Long-route movers** | ships, caravans and couriers along route polylines; simulated abstractly as positions along the route, instantiated as sprites only near the view; they turn back or fade at seams | cheap if abstract |
| 11 | **View rotation by 90° (strongly recommended)** | rotate the grid mapping, swap to `r1..r3` sprites | shows the hidden façades (§3.2); ×4 landmark atlas |
| 12 | **Timed processions and events** | an ordered group follows a route with spacing, triggers sounds and effects at nodes, then disperses | Panathenaic procession, delegations, a Roman procession |
| 13 | **Locked prebuilt world with editable zones** | only the corner plot and small decorate zones accept the build tools; undo/redo inside them | |
| 14 | **Zoned and positional sound** | ambience zones by rectangle, one-shots at world positions with distance attenuation | |
| 15 | **Seam captions** | caption when the camera centre crosses a region or seam boundary | trivial once 6 exists |
| 16 | **Backdrops** | painted strips behind the north and east world edges with night variants | |
| 17 | **Glow layers in bulk** | hundreds of small night lights, batched additive | |
| 18 | **Optional: follow a figure** | camera gently tracks a clicked figure until the player pans | |

---

## 15. Respect and honesty rules (all regions)

- Present every culture from its own evidence first: inscriptions, archives, archaeology and art.
  Greek authors on Persia, and Roman authors on Greeks, are used with care and labelled.
- When something is uncertain or disputed, the files say so and name the chosen option. Cards
  never state a disputed thing as fact.
- People not alive at their city's moment never appear as living citizens: they are statues,
  reliefs, memories or festival roles, and the card says which.
- Gods and heroes are shown as their own people imagined them in images of the period; cards
  paraphrase ancient sources, never modern retellings.
- Nobody is a joke. Working, enslaved and foreign people appear with dignity and routines of their
  own.
- Everything in the game (art, music, names of things, card wording) is original. Ancient texts may
  be paraphrased; ancient melodies are evoked through their modes and instruments, not copied.
