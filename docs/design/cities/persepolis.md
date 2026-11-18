# Pārsa (Persepolis) · تخت جمشید · spring, c. 470 BC

Design bible for the Achaemenid city. Read `world.md` first for scale, plan coordinates, the
elevation model and the region data model. Evidence and links: `sources.md` (section "Pārsa").

Names. The city was **Pārsa** in Old Persian (the same word as the land, Fārs, and the people);
the Greeks called it *Persepolis*; the Elamite tablets write *Paršaš*. Medieval Persians named the
ruins **Takht-e Jamshid** (تخت جمشید, "Throne of Jamshid"), linking them to the legendary king Yima
/ Jamshid; this name is about 1,500 years later than our moment and appears in the game only on the
overview map subtitle and in one card that explains it. Key Old Persian forms used in cards:
Dārayavauš (Darius), Xšayāršā (Xerxes), Kūruš (Cyrus), Artaxšaça (Artaxerxes), Auramazdā,
Pārsa, Yaunā (Ionians), *dahyu* (land, people), *bāji* (tribute, share), *tačara* (palace; Darius's
word for his building), *hadiš* (palace; Xerxes's word for his), *duvarθi visadahyu* ("gate of all
lands", Xerxes's name for the Gate, inscription XPa). *Apadāna* is the term later kings used for a
columned hall (Artaxerxes II at Susa); scholars apply it to Darius's hall, and so does the game.
The mountain's name Kuh-e Raḥmat ("mount of mercy") is itself medieval: Shahbazi (Iranica,
"Persepolis") gives the older name as Kuh-e Mehr, "translated" as Raḥmat from the 13th century;
use it on maps only, never in a card voice set in 470 BC. [checked: Iranica "Persepolis"]

---

## 1. Identity

**The moment: around the spring equinox, c. 470 BC, sixteen years into the reign of Xšayāršā
(Xerxes I, r. 486–465).**

Why this moment:

- Darius I's plan is now complete and Xerxes has added his own buildings: the terrace, Apadāna,
  Tačara, Gate of All Lands and Hadiš all stand finished (Apadāna begun under Darius, completed under
  Xerxes; Gate and Hadiš are Xerxes's; Livius, ISAC, Iranica).
- The **Hall of a Hundred Columns is a building site**: begun by Xerxes, finished by Artaxerxes I.
  So the city has a live workshop of stonecutters, cranes and ox carts, which the economy tablets
  let us describe precisely.
- The **Treasury** has just been enlarged (480–470) and the **Treasury tablets** (492–458 BC) show
  workers paid partly in weighed silver in exactly these years; the **Fortification tablets**
  (509–493 BC) describe the ration system that still runs the region.
- The cliff behind the terrace is still **bare**: the two royal tombs cut into Kuh-e Raḥmat belong
  to Artaxerxes II and III, decades later. Darius I's tomb at Naqsh-e Rostam is finished.
- **Spring** is when the Marvdasht plain is green with young barley, the Zagros peaks still carry
  snow, almond and pomegranate gardens flower and the water channels run full. The Apadāna stair
  reliefs show gift-bearing delegations from 23 lands. Two things must be kept apart:
  (1) **a fact**: the administrative year used at Pārsa (the Babylonian-based calendar with Old
  Persian month names) began with the month *Ādukanaiša*, near the spring equinox; (2) **a
  hypothesis**: that the terrace was built for, or the reliefs show, a New Year festival. That
  hypothesis is held by Herzfeld, Krefter, Erdmann, Ghirshman and Porada and defended by the
  Iranian historian A. Sh. Shahbazi ("cannot be taken lightly"); Nylander, Calmeyer and Mousavi
  deny there is any evidence for it, and Root reads the reliefs as a timeless image of empire,
  not a record of one day. No Achaemenid text names such a festival, and the name Nowruz
  (Middle Persian *nōg rōz*) first appears in Pahlavi texts many centuries later. The game shows a
  **spring audience of delegations**, never calls it "Nowruz", and explains the debate in one
  card (§6.10). [checked: Iranica "Persepolis" (Shahbazi); Iranica "Nowruz i" (Boyce); Livius
  "Apadana" offers the link only as "perhaps", with "no hard evidence"]

**The feeling, in five sentences.**
You smell cold thin air off the snow, wet earth in the gardens, cedar and resin, incense smoke from
the stands before the king, and the warm dust of horses and barley chaff on the plain. You hear
water in stone channels, swallows and hoopoes, the low continuous ring of chisels from the
building site, horse bells and the measured tread of a delegation on the shallow steps. You see a
forest of slender grey columns, 19.5 m tall, standing on a stone platform against a bare mountain,
their capitals carrying paired bulls, with painted walls of red, blue and gold behind them. Below
lies a green plain with walled gardens, cypress rows and mudbrick villages under a huge clear sky.
Pārsa is most itself in the **early morning**, when the low sun turns the terrace honey-gold, the
mountain is still blue and the first delegation starts up the stairway.

**"Aroma" made visible.** Incense: thin blue smoke curls from bronze incense stands at the Apadāna
and the audience scene. Water: glints and small spray particles along channels. Spring: drifting
almond petals in the gardens. Work: pale stone dust motes around the building site. Night: the
orange of fire altars and torches against an enormous star field.

---

## 2. Map plan

### 2.1 Size, scope, orientation

- **Region: 144 × 144 tiles, world origin (1136, 304), base level 4** (`world.md` §3, §5).
  All coordinates in this file are **local** plan coordinates `c` (east) and `r` (south) from the
  region's north-west corner: world `C = 1136 + c`, `R = 304 + r`; world level = 4 + local level.
  The region fills the south-east corner of the world; its east edge is the world's east edge,
  where the backdrop of Kuh-e Raḥmat stands.
- **Camera:** the world view from the south-west (`world.md` §3.2). The plain and the stairway are
  in front, the terrace rises behind them and the mountain closes the picture. Faces turned south
  and west are seen: the great stairway, the Gate's west door with its bulls, the Apadāna's west
  portico, the Tačara's south front and relief stair, the Hadiš. Faces turned north and east are
  hidden (the Apadāna's north and east relief stairs, the Gate's east lamassu, the Hall of a Hundred
  Columns' portico); their cards describe them, and the optional view rotation shows them.
  Landmarks are modelled in their true compass orientation; the world mapping decides which
  rotation sprite is used.
- **Scale:** terrace and everything on it at `s = 0.85` (tile ≈ 4.7 m real; heights 8.5 px per
  real metre). The plain is compressed about 4 × so that town, gardens, fields, the road station and
  the Naqsh-e Rostam vignette fit.
- **In scope (region):** the whole terrace; the fortification and slope of Kuh-e Raḥmat behind it;
  the town of Pārsa and its gardens on the plain; fields, canals and a qanat line; a quarry; a
  royal-road station; a cavalry and archery ground; the Naqsh-e Rostam satellite; a stretch of
  river.
- **Persian-time waypoints outside the region** (§3.7, `world.md` §6): Pasargadae, the Persian
  Gates, Susa, Babylon, the Euphrates crossing, the Halys crossing, Gordion, Sidon and Sardis. They
  belong to the same moment (c. 470 BC) and use this file's kit.

### 2.2 Districts

| # | District | Plan area (c, r) | Level | Contents |
|---|---|---|---|---|
| D1 | Terrace (Takht) | c 56..119, r 22..118 | 6 (platforms 7–9) | the palaces, gate, halls, treasury, garrison |
| D2 | Mountain slope and fortification | c 120..143, r 0..143 | 7–9, backdrop beyond | wall with towers, rock-cut cistern, drainage outfalls, quarry face, a mountain shrine |
| D3 | Stairway forecourt and royal road | c 26..48, r 36..60 | 0 | arrival plaza, horse lines, the road from the west edge (enters at c 0, r 49..51 = world R 353..355, from the Persian Gates) |
| D4 | Town of Pārsa | c 0..48, r 62..112 | 0 | mudbrick courtyard houses, workshops, workers' quarters, granaries, kitchens, a small shrine |
| D5 | Paradise garden (*partetaš* in Elamite tablets; Old Persian \**paridaida*, reconstructed [checked: Iranica "Garden i" (Eilers); the late spelling *paradayadām* is debated]) | c 26..54, r 8..34, and a garden strip c 49..55, r 60..118 below the terrace | 0 | walled garden with stone channels, pavilion, cypress and plane rows, orchards; a glazed-brick gate (after Tol-e Ajori) |
| D6 | Fields, canals, village | c 26..56, r 0..7; c 0..25, r 21..61; c 0..19, r 113..143 | 0 | barley and wheat plots, threshing floor, canal, village, flocks |
| D7 | Royal-road station and caravan yard | c 20..34, r 113..126 | 0 | station with stables and storeroom, camel caravan, relay horses |
| D8 | Cavalry and archery ground | c 35..55, r 113..134 | 0 | riding track, archery butts, the guard at drill |
| D9 | Southern plain and qanat | c 20..119, r 135..143 | 0 | qanat shaft line along r 138..140 from the mountain foot to the fields; grazing |
| S1 | Satellite: Naqsh-e Rostam (real: 6 km NNW) | c 0..24, r 0..20, cut off by a band of rocky ground | 0–8 | the cliff with Darius I's cruciform tomb, the Ka'ba-ye Zartosht tower, a fire altar |

Satellite rule (`world.md` §6): a satellite is a compressed vignette separated from the city by a
strip of rough ground with no road. Naqsh-e Rostam's real tomb façades face south, and the camera
sees south faces, so it needs no turning. Pasargadae, 80 km north in reality, is a waypoint on the
world map 17 rows north of the region (§3.7).

### 2.3 Landmark placement (plan coordinates, inclusive)

Real terrace positions follow the Oriental Institute excavation plan (Schmidt, *Persepolis I*),
scaled by `0.85 / 4 m` per tile and then lightly adjusted so footprints do not touch.

| Id | Landmark | Footprint (c, r) | w × h | Level | Faces / notes |
|---|---|---|---|---|---|
| `terrace` | Terrace walls | outline c 56..119, r 22..118 | 64 × 97 | 6 | west face is the long visible cliff (`ashlar` edge, 6 levels). Stepped merlons along the top edge. A minor stair on the south side (the original access, Livius) at c 84..88, r 118..121 |
| `great_stair` | Great double stairway | c 49..55, r 37..54 | 7 × 18 | 0 → 6 | west face. Lower flights start side by side at the centre (r 45..46) and climb outward north and south to landings at r 37..39 and r 52..54, then upper flights turn back and climb inward to one top landing at c 55, r 43..48 |
| `gate_all_lands` | Gate of All Lands (Xerxes) | c 64..69, r 42..47 | 6 × 6 | 6 | doors on west (bulls), east (human-headed winged bulls) and south (to the Apadāna) |
| `apadana` | Apadāna with corner towers | c 60..83, r 54..77 | 24 × 24 | 7 | west portico (seen) looks over the plain; north stair c 65..78, r 51..53 and east stair c 84..86, r 60..71 carry the reliefs (faces hidden in the default view; cards, view rotation) |
| `tacara` | Tačara (palace of Darius) | c 63..70, r 82..91 | 8 × 10 | 8 | main portico and relief stair on the south (seen); west stair plain in 470 (the decorated west stair is later) |
| `hadish` | Hadiš (palace of Xerxes) | c 76..85, r 88..101 | 10 × 14 | 9 | highest platform; stairs on west and north |
| `tripylon` | Tripylon / central hall ("Council Hall") | c 87..93, r 71..78 | 7 × 8 | 7 | stair reliefs of Persian and Median nobles climbing |
| `hall_100` | Hall of a Hundred Columns, **under construction** | c 93..108, r 52..67 | 16 × 16 | 6 | north portico c 93..108, r 48..51 with two colossal bulls; forecourt c 90..110, r 36..47 |
| `treasury` | Treasury (enlarged by Xerxes) | c 100..116, r 79..108 | 17 × 30 | 6 | flat-roofed mudbrick, columned halls with wooden columns |
| `harem` | "Harem" of Xerxes (residential wing) | L-shape: c 86..98, r 86..107 plus c 86..99, r 104..112 | 13 × 27 | 7 | courtyard apartments |
| `garrison` | Garrison quarters and storerooms | c 96..119, r 22..34 | 24 × 13 | 6 | barracks of the guard; armoury; a mudbrick tower |
| `south_stores` | Southern storerooms | c 80..99, r 113..118 | 20 × 6 | 6 | |
| `gate_road` | Processional road Gate → Hall forecourt | c 70..92, r 43..46 | — | 6 | paved, walled on both sides |
| `fort_wall` | Fortification on the slope | c 119..124, r 10..130, towers every 8 rows | — | 7–9 | mudbrick on stone, square towers |
| `cistern` | Rock-cut cistern and channel | c 124..128, r 60..64 | 5 × 5 | 8 | feeds the drainage/water system cut into the rock |
| `quarry` | Limestone quarry face | c 126..140, r 100..118 | 15 × 19 | 7–9 | half-cut blocks, wedge holes, ramp down to the terrace road |
| `paradise_gate` | Glazed-brick garden gate (after Tol-e Ajori) | c 26..30, r 24..28 | 5 × 5 | 0 | real gate 3.5 km west, built under Cyrus/Cambyses c. 530s (Iranian-Italian mission); compressed into the garden wall |
| `pavilion` | Garden pavilion | c 32..37, r 12..17 | 6 × 6 | 0 | columned pavilion over the channel crossing |
| `road_station` | Royal-road station | c 20..28, r 114..121 | 9 × 8 | 0 | |
| `naqsh_cliff` | Naqsh-e Rostam cliff with Darius I's tomb | c 0..20, r 0..8 | 21 × 9 | 0–8 | the tomb façade faces south, toward the camera |
| `kaba` | Ka'ba-ye Zartosht tower | c 10..12, r 13..15 | 3 × 3 | 0 | date and purpose debated (Darius I or earlier; tomb, fire house, archive?) |
| `cyrus_tomb` | Tomb of Cyrus (Pasargadae waypoint) | world C 1187..1191, R 270..274 | 5 × 5 | world 5 | six-stepped plinth, gabled chamber (§3.7) |

### 2.4 Plan (north up, local coordinates, 1 character = 3 × 3 tiles)

Generated from the coordinate tables above; where footprints share a cell, the later one wins.

```
   c→ 0       24      48      72      96      120     
r  0  NNNNNNNNN~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~MMMMMMMM
r  3  NNNNNNNNN~~~~~~~~~~~~...................MMMMMMMM
r  6  NNNNNNNNNgggggggggg,,,,,,,,,,,,,,,,,,,,,MMMMMMMM
r  9  NNNNNNNNNgggggDDDDD,,,,,,,,,,,,,,,,,,,,WWMMMMMMM
r 12  NNNkkNNNNgPPPgDDDDD,,,,,,,,,,,,,,,,,,,,WWMMMMMMM
r 15  NNNkkNNNNgPPPgDDDDD,,,,,,,,,,,,,,,,,,,,WWMMMMMMM
r 18  NNNNNNNNNgggggDDDDD,,,,,,,,,,,,,,,,,,,,WWMMMMMMM
r 21  ffffffffggggggggggTTTTTTTTTTTTTTbbbbbbbbWMMMMMMM
r 24  ffffffffIIIgggggggTTTTTTTTTTTTTTbbbbbbbbWMMMMMMM
r 27  ffffffffIIIgggggggTTTTTTTTTTTTTTbbbbbbbbWMMMMMMM
r 30  ffffffffggggggggggTTTTTTTTTTTTTTbbbbbbbbWMMMMMMM
r 33  ffffffffggggggggggTTTTTTTTTTTTTTbbbbbbbbWMMMMMMM
r 36  ffffffff::::::::EEETTTTTTTTTTTTTTTTTTTTTWMMMMMMM
r 39  ffffffff::::::::EEETTTTTTTTTTTTTTTTTTTTTWMMMMMMM
r 42  ffffffff::::::::EEETTGGG=======TTTTTTTTTWMMMMMMM
r 45  ffffffff::::::::EEETTGGG=======TTTTTTTTTWMMMMMMM
r 48  ffffffff::::::::EEETTTTTTTTTTTTHHHHHHTTTWMMMMMMM
r 51  ffffffff::::::::EEETTAAAAAATTTTHHHHHHTTTWMMMMMMM
r 54  ffffffff::::::::EEETAAAAAAAATTTHHHHHHTTTWMMMMMMM
r 57  ffffffff:::::::::.TTAAAAAAAATTTHHHHHHTTTWMMMMMMM
r 60  hhhhhhhhhhhhhhhhhgTTAAAAAAAATTTHHHHHHTTTWooMMMMM
r 63  hhhhhhhhhhhhhhhhhgTTAAAAAAAATTTHHHHHHTTTWooMMMMM
r 66  hhhhhhhhhhhhhhhhhgTTAAAAAAAATTTHHHHHHTTTWMMMMMMM
r 69  hhhhhhhhhhhhhhhhhgTTAAAAAAAATtttTTTTTTTTWMMMMMMM
r 72  hhhhhhhhhhhhhhhhhgTTAAAAAAAATtttTTTTTTTTWMMMMMMM
r 75  hhhhhhhhhhhhhhhhhgTTAAAAAAAATtttTTTTTTTTWMMMMMMM
r 78  hhhhhhhhhhhhhhhhhgTTTTTTTTTTTtttTRRRRRRTWMMMMMMM
r 81  hhhhhhhhhhhhhhhhhgTTTcccTTTTTTTTTRRRRRRTWMMMMMMM
r 84  hhhhhhhhhhhhhhhhhgTTTcccTTTTmmmmmRRRRRRTWMMMMMMM
r 87  hhhhhhhhhhhhhhhhhgTTTcccTXXXmmmmmRRRRRRTWMMMMMMM
r 90  hhhhhhhhhhhhhhhhhgTTTcccTXXXmmmmmRRRRRRTWMMMMMMM
r 93  hhhhhhhhhhhhhhhhhgTTTTTTTXXXmmmmmRRRRRRTWMMMMMMM
r 96  hhhhhhhhhhhhhhhhhgTTTTTTTXXXmmmmmRRRRRRTWMMMMMMM
r 99  hhhhhhhhhhhhhhhhhgTTTTTTTXXXmmmmmRRRRRRTWMQQQQQM
r102  hhhhhhhhhhhhhhhhhgTTTTTTTTTTmmmmmmRRRRRTWMQQQQQM
r105  hhhhhhhhhhhhhhhhhgTTTTTTTTTTmmmmmmRRRRRTWMQQQQQM
r108  hhhhhhhhhhhhhhhhhgTTTTTTTTTTmmmmmmRRRRRTWMQQQQQM
r111  hhhhhhsssssaaaaaaaTTTTTTTTzzzzzzzzTTTTTTWMQQQQQM
r114  ffffffsssssaaaaaaaTTTTTTTTzzzzzzzzTTTTTTWMQQQQQM
r117  ffffffsssssaaaaaaaTTTTTTTTzzzzzzzzTTTTTTWMQQQQQM
r120  ffffffsssssaaaaaaaa....................WWMMMMMMM
r123  ffffffsssssaaaaaaaa....................WWMMMMMMM
r126  ffffffsssssaaaaaaaa....................WWMMMMMMM
r129  fffffff....aaaaaaaa....................WWMMMMMMM
r132  fffffff....aaaaaaaa.....................MMMMMMMM
r135  ffffff,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,MMMMMMMM
r138  ffffffqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqMMMMMMMM
r141  ffffff,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,MMMMMMMM
```

Legend: `N` Naqsh-e Rostam cliff, `k` Ka'ba-ye Zartosht, `~` river and canal, `f` fields, `,`
plain and pasture, `q` qanat line, `g` paradise garden, `P` pavilion, `I` glazed-brick gate, `D`
player's garden plot, `:` stairway plaza, `E` great stairway, `T` terrace (open courts), `G` Gate
of All Lands, `=` processional road, `A` Apadāna, `H` Hall of a Hundred Columns, `t` Tripylon, `c`
Tačara, `X` Hadiš, `m` residential wing, `R` Treasury, `b` garrison, `z` southern storerooms, `h`
town, `s` road station, `a` cavalry and archery ground, `W` fortification wall, `o` cistern, `Q`
quarry, `M` mountain slope (backdrop beyond the east edge).

(The ASCII is a reading aid; the tables above are authoritative.)

### 2.5 Streets, water, walls and gates

- **Royal road** enters at the west edge (c 0, r 49..51; world R 353..355, coming from the Persian
  Gates) and ends at the stairway plaza (c 26..48, r 36..60). Packed earth, 3 tiles wide. A spur
  runs south at c 22 through the town to the road station (D7).
- **Terrace streets** are paved courts and corridors between mudbrick walls: the Gate → Hall road
  (above); a north–south street east of the Apadāna (c 88..90, r 48..80); courts in front of the
  Tačara and Hadiš (r 78..87).
- **Water:** a main canal leaves the river at c 60, r 3, runs west along r 4..5 to the garden's
  north-east corner (c 54, r 8) and feeds the garden, where stone-lined channels about 25 cm wide (Pasargadae garden,
  Met essay) divide beds, with square basins at intervals. On the terrace, rock-cut drains run
  under the paving to outfalls in the west face (the terrace drainage system is well documented);
  show grated openings and, after rain, small waterfalls from the outfalls. From the garden a
  channel runs south along the terrace foot (c 50..51) to the town and the fields.
- **River:** a tributary of the Pulvar crosses the north edge (r 0..3), shallow, with willows,
  reeds and a ford.
- **Qanat:** a line of shaft mounds (ring of spoil around a hole every 2 tiles) runs from the
  mountain foot at c 119, r 139 west along r 138..140 to the fields at c 19, r 139, ending in an
  open channel. Achaemenid
  qanats are **debated** for Iran itself: Polybius 10.28 reports a local story that under Persian
  rule whoever brought water to dry land by underground channels might farm it for five
  generations. The firmest evidence is in Achaemenid **Egypt**: at ʿAyn Manawir (Kharga oasis) a
  qanat was in use by the second half of the 5th century BC, dated by Demotic ostraca of the reign
  of Artaxerxes I. No qanat at Pārsa is dated to 470. Keep it nice-to-have; the card says the
  technique was known in the empire and that this line is the game's choice. [checked: Polybius
  10.28 (Loeb, LacusCurtius); Wuttmann, Gonon & Thiers, "The Qanats of ʿAyn Manawir"]
- **Walls:** the terrace edge is a cliff of fitted grey limestone blocks; a mudbrick wall with
  towers crowns the mountain side. The town has no circuit wall in the game.

### 2.6 Elevation

Local levels; world level = 4 + local (the plain sits at world level 4, above Mesopotamia and
below the Zagros pass).

| Area | Level | Notes |
|---|---|---|
| Plain, town, gardens | 0 | |
| Terrace | 6 | real face 12–14 m at the stair. 6 levels × 16 px = 96 px of `ashlar` cliff |
| Apadāna and Tripylon platforms | 7 | 1-level stairs with relief fronts |
| Harem | 7 | |
| Tačara | 8 | |
| Hadiš | 9 | the highest building platform |
| Fortification, cistern, quarry | 7–9 | `rock` edge material |
| Kuh-e Raḥmat | backdrop | `backdrop/kuh_rahmat` behind the east edge, with snow streaks |
| Naqsh-e Rostam cliff | 0 base, cliff sprite to about 8 levels | landmark sprite, not tiles |

Stairs: `great_stair` (rise 6), Apadāna north stair (rise 1, double, relief front), Tačara west
stair (rise 2), Hadiš west stair (rise 3, from level 6), Tripylon stair (rise 1), quarry ramp (rise
2), south stair (rise 6, narrow).

---

## 3. Asset list

Legend: **M** must-have, **N** nice-to-have. **L** landmark (unique), **K** kit (reusable).
Heights in px at 64 × 32 from ground to top. Rotations: one sprite per landmark for the fixed
south-west view; all four if the optional view rotation is built (the voxel generator renders
them from the same model). Layers:
B base, S shadow, G glow.

### 3.1 Architectural facts every artist must get right (Pārsa)

- **Stone:** dense grey limestone from local quarries, cut to razor joints without mortar and
  polished to a dull sheen; iron/lead clamps hidden. Doorframes, window frames and niches are single
  massive stone pieces with **Egyptian-style cavetto ("gorge") cornices**. Walls between them are
  **mudbrick, plastered** and painted (lost today; that is why ruins show only stone frames).
- **Columns:** square two-step plinth or bell-shaped base carved with hanging petals; very slender
  fluted shaft (about 40–48 flutes); composite capital: a palm/bell element, then tall vertical
  double volutes, then **addorsed animal protomes** (two foreparts back to back) whose saddle holds
  the main roof beam. **Apadāna** [checked: Iranica "Apadāna" (Schmitt & Stronach) and
  "Persepolis" (Shahbazi)]: the hall and the north portico have the full composite capital with
  addorsed **bulls**; in the **west** and **east** porticoes the protome capital sits **directly on
  the fluted shaft**, without the bell and volute stages: **bulls on the west, lions on the east**.
  Griffin (eagle-headed) capitals are known at Pārsa, but a pair found north of the terrace had been
  discarded soon after carving; no portico in use is known to have carried them. Gate of All
  Lands: two addorsed kneeling bulls. Hall of a Hundred Columns' north portico: human-headed bulls.
- **Roofs:** flat, on cedar and other fine timbers (excavators found a burnt layer of cedar, ebony
  and teak 30–60 cm thick in the Apadāna, Livius), with earth/clay above and a parapet of **stepped
  merlons** (stone examples survive).
- **Colour:** reliefs and architectural stone were **painted** (Nagel's polychromy studies; traces
  of Egyptian blue, red, green and gilding): robes in patterned reds, blues and yellows, beards and
  hair dark blue-black, gold on crowns, jewellery and some details; backgrounds probably left as
  polished stone. Floors were plastered and painted dark red (hematite-rich layers, polychromy
  research). Doors were wood sheathed in bronze or gold foil. Glazed bricks carried some
  inscriptions (XPg) and ornament.
- **Inscriptions:** trilingual (Old Persian, Elamite, Babylonian) panels in cuneiform on gates,
  stairs and doorways: draw as fine, dense, rectangular panels of wedges, never as legible
  letters.
- **Reliefs:** processions of figures in profile, shoulder in frontal view, calm and orderly;
  guards with spears; delegations holding hands with their Persian or Median usher; lions attacking
  bulls in the stair triangles; rows of stylised cypress trees and 12-petalled rosettes as borders;
  the winged figure in a disc above central panels (identity debated: Auramazdā, or the royal
  *farnah*/fortune).

### 3.2 Landmarks

| Id | Name | Footprint | Height px | Layers | Anim | M/N | Look (what must be right) |
|---|---|---|---|---|---|---|---|
| `terrace` (edge set) | Terrace face and merlons | per tile | 96 (6 levels) | B,S | — | M | fitted polygonal-to-rectangular grey ashlar, huge blocks at the base, a stepped-merlon parapet along the top; drainage outfalls every 10 tiles |
| `great_stair` | Great double stairway | 7 × 18 | 100 | B,S | — | M | shallow broad steps (10 cm rise, 38 cm tread, 6.70 m wide; each side climbs **63 steps** to a landing, then **48 more** to the top: 111 per side, about 11 m of rise) [checked: Iranica "Persepolis" (Shahbazi); the earlier "31 cm, 6.9 m" came from a wiki mirror], low stone parapets, two lower flights diverging from the centre, square landings, two upper flights converging. Plain, no reliefs (the reliefs are on the Apadāna) |
| `gate_all_lands` | Gate of All Lands | 6 × 6 | 155 | B,S,G | torch flicker (G) | M | square hall with 4 columns "over 16.5 m" tall, capitals of two addorsed kneeling bulls [checked: Iranica "Persepolis"; Livius]; three doorways. West door: a pair of colossal **bulls** in profile, striding out; east door: colossal **human-headed winged bulls** (lamassu) with tall feathered crowns, curled beards, wings raised. Trilingual XPa panels above the bulls. Mudbrick walls painted, flat roof, merlons |
| `apadana` | Apadāna | 24 × 24 | 200 | B,S,G | incense smoke emitters | M | main hall 6 × 6 = 36 columns, 19.5 m tall (Shahbazi; Iranica "Apadāna": "more than 19 m"); porticoes on north, west and east, each 2 rows of 6 = 12 columns (72 in all); capitals as §3.1 (composite bulls in hall and north portico; bulls directly on the shaft in the **west** portico, which the default view shows; lions in the east portico); four square corner towers (mudbrick on stone, two storeys, merlons, small windows); south side closed by service rooms. Walls painted, glazed-brick panels. North stair (faces north: **hidden** in the default view, as §2.3 says): double stair, relief front in **three registers** each wing (guards, staff-bearers and nobles on one wing, the gift-bearing delegations on the other), lions attacking bulls in the triangles. Central panel **in 470: the audience scene** (the king enthroned under a canopy, the crown prince behind him, an official saluting with hand before mouth, incense stands). It was later removed (Shahbazi: under Artaxerxes I) to the Treasury, where Schmidt found it, and replaced by the panel of 8 guards under the winged disc and sphinxes seen today (Tilia). [checked: Iranica "Persepolis"; Livius "Apadana east stairs"]. Build so walkers enter the north portico (`walk` tiles) |
| `tacara` | Tačara | 8 × 10 | 120 | B,S,G | lamp glow | M | small palace of dark polished stone (the "hall of mirrors" sheen), hall of 12 columns (3 × 4) with 8-column portico (2 × 4) on the south; stone door and window frames with reliefs of the king under a parasol with attendants, heroes fighting monsters; DPa inscription "I built this *tačara*". West stair plain in 470 |
| `hadish` | Hadiš | 10 × 14 | 140 | B,S,G | lamp glow | M | hall of 36 columns (6 × 6) with a 12-column portico; on the highest platform; stair reliefs of servants carrying food, wineskins and kid goats; XPe-type inscriptions. Visible from the plain as the top of the terrace silhouette |
| `tripylon` | Tripylon | 7 × 8 | 110 | B,S | — | M | small 4-column hall with three doors; stair façade with Persian and Median nobles climbing, holding flowers, chatting, hands on each other's shoulders. Shahbazi attributes it to "Xerxes and Artaxerxes I", so in 470 it may still have been unfinished; showing it complete is a choice [checked: Iranica "Persepolis"] |
| `hall_100` | Hall of a Hundred Columns (building site) | 16 × 16 | 120 (finished columns); 40–110 (rising) | B,S | crane swing, chisel sparks | M | grid of 10 × 10 bases, columns "nearly 14 m" when finished (Shahbazi; built between 486 and about 450), about a third with full shafts, some with capitals, others shafts at mid-height with timber scaffolds and earth ramps; north portico of 16 columns, whose finished capitals are **double human-headed bulls** (Shahbazi); two colossal bulls flanking the portico, roughly blocked out; stacks of drums, a capital on rollers, ox sledges [checked: Iranica "Persepolis"; Livius] |
| `treasury` | Treasury | 17 × 30 | 80 | B,S | — | M | low, flat-roofed mudbrick complex, plastered walls, small high windows, many columned halls with **wooden columns plastered and painted** in patterns on stone bases; guarded doors |
| `harem` | Residential wing ("Harem") | L, 13 × 27 | 70 | B,S,G | lamp glow | M | rows of apartments around courts, small 4-column halls, stone door frames with royal reliefs |
| `garrison` | Garrison quarters | 24 × 13 | 70 | B,S,G | brazier | M | barracks rooms, armoury, a courtyard for drill, a gate tower |
| `south_stores` | Southern storerooms | 20 × 6 | 50 | B,S | — | N | |
| `fort_wall` | Mountain fortification | kit pieces, 1 × 1 straight, 2 × 2 tower | 60 / 100 | B,S,G | torches on towers | M | mudbrick on stone foot, square towers with merlons |
| `cistern` | Cistern | 5 × 5 | 20 | B,S | water ripple | N | rock-cut basin, channel mouth |
| `quarry` | Quarry face | 15 × 19 | 90 | B,S | dust | M | stepped cut faces, wedge slots, half-detached blocks, rubble ramps |
| `paradise_gate` | Glazed-brick gate | 5 × 5 | 110 | B,S | — | N | mudbrick gate faced with glazed bricks: blue ground with yellow-white bulls and dragons (*mušḫuššu*) in relief, after Tol-e Ajori and the Ishtar Gate type |
| `pavilion` | Garden pavilion | 6 × 6 | 90 | B,S,G | — | M | open columned pavilion (wooden or slender stone columns), flat roof, over the channel; carpets inside |
| `road_station` | Royal-road station | 9 × 8 | 60 | B,S,G | — | M | walled yard, stable range, storeroom, a room for the official; tethered horses |
| `naqsh_cliff` | Naqsh-e Rostam and Darius I's tomb | 21 × 9 | 230 | B,S | — | M | a pinkish-grey cliff; the tomb is a **cross-shaped** façade: lower arm blank; middle arm a palace front with 4 engaged columns (bull capitals) and a door; upper arm the king on a three-stepped dais before a **fire altar**, under the winged figure, on a throne-platform carried by 30 figures of the subject peoples; Gobryas (spear-bearer) and Aspathines (holding the king's battle-axe; his title *vaçabara* is usually rendered "bow-bearer", meaning debated) at the sides; DNa/DNb inscription panels [checked: Livius DNd] |
| `kaba` | Ka'ba-ye Zartosht | 3 × 3 | 120 | B,S | — | N | square stone tower about 12 m, dark limestone blind windows in contrasting stone, a stair to a single high door |
| `cyrus_tomb` | Tomb of Cyrus | 5 × 5 | 110 | B,S | — | M | six-stepped stone plinth carrying a small gabled chamber with a low, narrow door (about 0.78 × 1.40 m today; secondary sources put it on the north-west side, to confirm against Stronach 1978 before re-modelling) and a rosette in the gable; pale limestone; a grove and a channel (Arrian 6.29, after Aristobulus: a grove of all kinds of trees, watered, deep grass in the meadow; a small house of the magi who guarded it) [checked: Arrian 6.29 (Chinnock, Wikisource)] |

### 3.3 Kit: buildings, structures and props

| Id | Name | Footprint | Height px | Rot | Layers | Anim | M/N | Look |
|---|---|---|---|---|---|---|---|---|
| `p_house` | Mudbrick courtyard house | 3 × 3 | 60 | 4 | B,S,G | — | M | thick plastered mudbrick walls in warm buff, flat roof with a low parapet and a few poles, wooden door, tiny high windows, courtyard with a tree; G: doorway lamp |
| `p_house_small` | Small house / workers' block | 2 × 2 | 50 | 4 | B,S,G | — | M | as above, simpler; rows of identical cells (dependent workers' housing) |
| `p_granary` | Granary | 2 × 2 | 55 | 2 | B,S | — | M | domed or flat-roofed storehouse with sealed doors |
| `p_workshop` | Craft workshop yard | 3 × 2 | 45 | 4 | B,S,G | — | M | open shed of poles and reed matting over a work yard |
| `p_kiln` | Brick/pottery kiln | 1 × 1 | 40 | 1 | B,S,G | smoke, glow | M | domed clay kiln, fire mouth |
| `p_brickfield` | Mudbrick drying field | 2 × 2 | 6 | 1 | B | — | M | rows of square bricks drying, wooden moulds |
| `p_oven` | Bread oven (tanūr-type) | 1 × 1 | 24 | 1 | B,S,G | smoke | M | cylindrical clay oven sunk in the ground |
| `p_well` | Well with sweep | 1 × 1 | 50 | 2 | B,S | sweep anim | N | |
| `p_channel` | Stone water channel | 1 × 1 | 4 | connect | B | water shimmer | M | narrow dressed-stone channel; basin variant |
| `p_basin` | Square channel basin | 1 × 1 | 6 | 1 | B | ripple | M | |
| `p_qanat_shaft` | Qanat shaft mound | 1 × 1 | 10 | 1 | B | — | N | ring of spoil, wooden windlass on some |
| `p_fire_altar` | Fire altar | 1 × 1 | 40 | 1 | B,S,G | fire | M | stepped stone altar (three steps top and bottom, as on the tomb reliefs) with a bowl of fire |
| `p_incense` | Bronze incense burner | 1 × 1 | 32 | 1 | B,S,G | smoke | M | tall stand with conical lid, as in the audience relief |
| `p_brazier` | Brazier | 1 × 1 | 22 | 1 | B,S,G | fire | M | |
| `p_torch` | Wall torch | 1 × 1 | 30 | 4 | B,G | flame | M | |
| `p_parasol` | Royal parasol | 1 × 1 | 60 | 1 | B | — | M | carried prop for the king (see figures) |
| `p_throne` | Throne and footstool | 1 × 1 | 40 | 4 | B,S | — | M | lion-footed throne with high back; footstool |
| `p_crane` | Wooden lifting frame (shear legs) | 2 × 1 | 110 | 2 | B,S | swing | M | two timber legs, ropes, a block |
| `p_scaffold` | Timber scaffold around a column | 1 × 1 | 60–120 | 1 | B,S | — | M | lashed poles |
| `p_drum_stack` | Column drums and capital blocks | 1 × 1 | 24 | 2 | B,S | — | M | |
| `p_sledge` | Ox sledge with block | 2 × 1 | 30 | 4 | B,S | — | M | |
| `p_cart` | Two-wheeled cart | 2 × 1 | 32 | 4 | B,S | wheel | M | spoked wheels |
| `p_jars` | Storage jars | 1 × 1 | 22 | 2 | B,S | — | M | |
| `p_sacks` | Grain sacks and measures | 1 × 1 | 16 | 2 | B,S | — | M | |
| `p_scribe_desk` | Scribe's mat, tablet baskets | 1 × 1 | 14 | 4 | B | — | M | clay tablets drying on a board, a jar of clay, styluses, a leather scroll |
| `p_scales` | Balance with weights | 1 × 1 | 30 | 2 | B | — | M | duck-shaped weights, silver pieces |
| `p_tent` | Delegation tent | 2 × 2 | 50 | 2 | B,S,G | flap | N | wool tent for visiting envoys on the plain |
| `p_loom` | Upright loom | 1 × 1 | 40 | 2 | B | — | M | warp-weighted or two-beam loom with patterned cloth |
| `p_horse_line` | Horse line | 3 × 1 | 30 | 2 | B,S | — | M | posts and rope, feed baskets |
| `p_trough` | Stone trough | 1 × 1 | 12 | 2 | B | — | M | |
| `p_threshing` | Threshing floor | 3 × 3 | 4 | 1 | B | — | M | beaten earth circle, straw heaps |
| `p_dovecote` | Mudbrick dovecote | 1 × 1 | 50 | 1 | B,S | birds | N | |
| `p_carpet` | Spread carpet | 2 × 1 | 2 | 2 | B | — | N | knotted pile carpet (the Pazyryk carpet shows Achaemenid-period design: borders of riders and deer) |
| `p_archery_butt` | Archery target | 1 × 1 | 30 | 2 | B,S | — | M | straw butt |

### 3.4 Plants

| Id | Name | Footprint | Height px | Anim | M/N | Look / evidence |
|---|---|---|---|---|---|---|
| `t_cypress` | Cypress | 1 × 1 | 110 | sway | M | narrow dark green column; the schematic conifer of the reliefs |
| `t_plane` | Oriental plane | 1 × 1 | 120 | sway | M | broad crown, mottled trunk; native, prized in Persian gardens |
| `t_poplar` | White poplar | 1 × 1 | 110 | shimmer | M | tall, silvery leaves, along channels |
| `t_willow` | Willow | 1 × 1 | 80 | sway | M | by the river |
| `t_pomegranate` | Pomegranate | 1 × 1 | 55 | blossom | M | red-orange flowers in spring; pomegranates are a common Achaemenid motif (spear butts) |
| `t_almond` | Almond in blossom | 1 × 1 | 60 | petals | M | white-pink blossom, the spring signal |
| `t_vine` | Grapevine on trellis | 1 × 1 | 45 | — | M | wine was a major ration item |
| `t_date` | Date palm | 1 × 1 | 100 | sway | N | grows in the warm south of Fārs; a few in the garden |
| `t_fig` | Fig | 1 × 1 | 60 | — | N | |
| `p_barley` | Young barley (spring green) | 1 × 1 | 8 | ripple | M | barley was the main grain of the ration system |
| `p_wheat` | Wheat | 1 × 1 | 10 | ripple | M | |
| `p_lilies` | Lilies and wild tulips | 1 × 1 | 10 | — | M | spring flowers of the Zagros (tulips) |
| `p_rose` | Wild rose | 1 × 1 | 14 | — | N | |
| `p_reeds` | Reeds | 1 × 1 | 30 | sway | M | reuse corner reeds |
| `p_steppe` | Steppe tufts, wormwood | 1 × 1 | 8 | — | M | grey-green, on rough ground |

### 3.5 Terrain

`plain_grass` (spring green, base), `field_barley` (overlay), `garden_bed` (dark soil),
`packed_earth` (road), `paving_stone` (terrace courts, large grey slabs), `paving_red` (painted red
plaster floors inside porticoes), `gravel` (forecourt), `rock` (mountain, quarry), `water_channel`
(narrow, animated), `river` (animated), `rough_ground` (satellite separators).

### 3.6 Walkers (anonymous citizens) and animals

Each walker kind comes in 3–4 colour variants. Dress follows section 6.2.

| Kind | Variants | Anim | M/N |
|---|---|---|---|
| Persian noble (court robe) | 4 | walk, idle, talk | M |
| Median-dress official / usher | 4 | walk, idle, lead-by-hand | M |
| Guard with spear (Persian dress) | 3 | stand, walk | M |
| Guard / soldier (Median dress, bow case) | 3 | stand, walk | M |
| Scribe (Elamite tablet / Aramaic leather) | 3 | walk, write | M |
| Stonecutter / mason | 3 | chisel, carry | M |
| Labourer (rope team, carrier) | 4 | haul, carry | M |
| Woman worker (weaver, grinder) | 4 | weave, grind, carry jar | M |
| Woman overseer | 2 | stand, gesture | M |
| Child | 4 | run, play | M |
| Gardener | 3 | dig, water, prune | M |
| Farmer / herder | 4 | hoe, herd, thresh | M |
| Groom with horse | 3 | lead | M |
| Caravan driver with camels | 2 | lead | M |
| Royal-road courier (rider) | 1 | ride | M |
| Magus / priest | 2 | tend fire, chant | M |
| Cook / servant with dishes | 3 | carry | M |
| Musician (harp, pipes, drum) | 3 | play | N |
| Delegation members | 23 sets of 2–4 (section 6.6) | walk, carry gift, hold hands | M (8 sets) / N (the rest) |
| Horse (Nisaean type), camel (Bactrian and dromedary), donkey, mule, humped bull/zebu, ox, sheep, goat, dog, hunting hound | — | walk, idle, graze | M (horse, camel, donkey, ox, sheep, dog) |
| Lioness and cubs (Elamite gift, in a cage cart) | — | idle | N |
| Birds: swallows, hoopoe, house sparrows, storks, crows; insects: bees in the garden, butterflies; at night: owls, bats | — | fly | M (swallows, hoopoe, sparrows) |

### 3.7 Persian-time waypoints on the Royal Road (outside the region)

World coordinates (`world.md` §6). Same moment (c. 470 BC) and same kit as Pārsa (road station,
houses, walkers, caravans, plants); each adds a few unique landmarks at `s ≈ 0.5`.

| Waypoint (world rect) | Landmark id | Footprint | Height px | M/N | Look (what must be right) |
|---|---|---|---|---|---|
| **Pasargadae** (C 1176..1203, R 260..287) | `cyrus_tomb` | 5 × 5 | 110 | M | see §3.2 |
| | `pasargadae_garden` | 12 × 10 | 70 | M | Palace P: a columned hall facing a garden divided by narrow stone channels with square basins (Met essay); cypresses and planes |
| | `pasargadae_gate` | 6 × 6 | 90 | N | Gate R with the relief of a four-winged figure wearing an Egyptian-style crown (once inscribed "I, Cyrus the king, an Achaemenid", inscription CMa, which many scholars think was added under Darius; who the figure shows is debated) |
| **Persian Gates** (C 1112..1127, R 330..345) | `gates_station` | 8 × 6 | 60 | M | a narrow defile between cliffs (`rock` edges, levels 12–15), the road on a ledge, a walled station with guards and a beacon |
| **Susa** (C 1080..1103, R 315..340) | `susa_palace` | 14 × 12 | 150 | M | Darius's palace on the high citadel mound: an apadāna of 36 columns with bull capitals (like Pārsa) beside courtyard buildings of mudbrick faced with **glazed-brick friezes**: archers in patterned robes, lions, winged bulls, on blue and green grounds |
| | `susa_mound` (terrain set) | — | — | M | high earthen mound (`earth` edges), mudbrick town below, the Shaur river |
| **Babylon** (C 1036..1071, R 285..316) | `ishtar_gate` | 6 × 4 | 140 | M | double gate in **blue glazed brick** with alternating rows of yellow-brown aurochs and white-yellow *mušḫuššu* dragons in relief (Nebuchadnezzar II, c. 575 BC), crenellated towers |
| | `processional_way` | 2 × 14 | 60 | M | walled street lined with glazed-brick striding lions |
| | `etemenanki` | 12 × 12 | 260 | M | the stepped temple tower of Marduk: seven stepped stages in mudbrick with baked-brick facing, a long front stair, a shrine on top (proportions after the Esagila tablet; uncertain; Herodotus 1.181 counts eight towers including the base) [checked: Herodotus 1.181, 1.183 (Rawlinson, Wikisource)]. Its state under Xerxes is debated (Greek writers say he damaged Marduk's sanctuary after the revolts of 484; many historians doubt it). Shown standing |
| | `babylon_wall` (kit) | 1 × 1 / 2 × 2 tower | 70 / 100 | M | mudbrick double wall with towers |
| | `euphrates_bridge` | 10 × 2 | 30 | N | stone piers bound with iron and lead, with a timber deck laid by day and taken up at night against thieves (Herodotus 1.186) [checked] |
| **Euphrates crossing** (C 1008..1023, R 170..185) | `ferry_station` | 6 × 6 | 40 | M | landing stages on both banks, round hide-covered boats and log rafts on inflated skins, a station |
| **Halys crossing** (C 950..965, R 120..135) | `halys_gates` | 8 × 4 | 80 | M | a gate with towers and a guard post on the road before the river (Herodotus mentions gates and a fort here), timber bridge or ferry |
| **Gordion** (C 905..925, R 130..150) | `gordion_mound` | 10 × 10 | 70 | N | the great burial mound and the citadel walls of the old Phrygian capital |
| **Sidon / Byblos** (C 990..1007, R 300..340) | `phoenician_harbour` | 12 × 8 | 70 | N | quay, Phoenician ships with horse-head prows, cedar logs being floated; cedar loggers on the slope above |
| **Sardis** (C 860..879, R 200..219) | `sardis_acropolis` | 10 × 10 | 160 | M | steep eroded acropolis with walls; the satrap's residence below (N); the Paktolos stream with gold-washers |
| | `royal_road_head` | 4 × 4 | 60 | M | the first station of the Royal Road, a milestone-like stone and an Aramaic sign panel |

**Asset counts (Pārsa):** landmarks 21 (M 17 / N 4), kit 33 (M 28 / N 5), plants 15 (M 12 / N 3),
terrain 11 (M), walker kinds 19 (M 18 / N 1) plus delegation sets, animals 13 (M 6 / N 7).
Waypoints add 17 landmarks (M 12 / N 5). **Total about 129 entries: must-have about 104,
nice-to-have about 25.** The must-have set alone
builds a convincing city; the cut line is the N marks.

---

## 4. Figures

Presence types are defined in `world.md` §5. Sprites are about 40 px tall (heroes up to 52 px with
crowns or attributes). "How to recognise" lists what must survive at that size.

### 4.1 Heroes and notables

| # | Figure | Dates | Presence | Who they were | How to recognise (sprite) | Where / what they do | M/N |
|---|---|---|---|---|---|---|---|
| 1 | **Xšayāršā (Xerxes I)** | r. 486–465 BC | present | Son of Darius I and Atossa; finished his father's buildings and added the Gate of All Lands, the Hadiš and the Hall of a Hundred Columns. His inscriptions call him "great king, king of kings, king of lands". | tallest figure; long pleated court robe in deep red-purple with gold border; tall fluted crown; long squared beard; staff in right hand, lotus in left; an attendant holds a parasol over him | morning: enthroned in the Apadāna north portico during audiences; afternoon: walks the Hadiš terrace; rarely: inspects the Hall of a Hundred Columns site | M |
| 2 | **Amestris** | fl. 480–420s BC | present | Wife of Xerxes and mother of Artaxerxes I. She is known only from Greek authors (Herodotus, Ctesias), who paint her darkly; the game shows her as a royal householder, which is what Achaemenid royal women were in the tablets. | long robe, veil from a low crown down her back, jewelled collar; attendants | the residential wing courts and the garden pavilion; visits the weaving workshop of her household | N |
| 3 | **Artaxšaça (Artaxerxes), the young prince** | b. c. 480s?, r. 465–424 BC | present | Younger son of Xerxes who became king in 465 and finished the Hall of a Hundred Columns. In 470 he is a boy or a youth; his exact age is uncertain. | small court robe, simple cap, riding a pony with a groom | the cavalry ground learning to ride and shoot (Persian boys were taught "to ride, to shoot, to speak the truth", Herodotus 1.136, a Greek source) | N |
| 4 | **Mauš, treasurer** (Elamite spelling, also *Mawuš*; the Old Persian form is uncertain) | attested Xerxes years 12–19 (c. 474–467 BC) | present | The treasurer at Pārsa to whom the Treasury tablets of exactly our years are addressed: orders to pay workers partly in silver in place of rations. **Correction:** the bible first named Baradkama (Elamite *Baratkama*), but his tablets run only from Darius year 32 to Xerxes year 6 (490–480 BC); by 470 the letters go to Mauš, and from 467 to Ratininda. Baradkama may appear as a memory. [checked: CDLI catalogue of Cameron, *Persepolis Treasury Tablets* (OIP 65), nos. 1–22 and 27–48] | Median dress with a rounded cap, seal on a cord at his wrist, a scribe beside him | Treasury doorway: weighs silver, seals tablets, receives the delegations' gifts after the audience | M |
| 5 | **Artemisia I of Caria** | fl. 480 BC | present (visitor) | Queen of Halicarnassus, a Persian vassal, who commanded ships for Xerxes at Salamis (Herodotus). Her visit to Pārsa is the game's invention, framed as a vassal bringing gifts; whether she was still alive or ruling in 470 is not known. | Carian dress like the Lydians on the reliefs (long striped garment) with a wreath, plus a short cloak; two attendants with a bull and shield (the Carian gifts) | climbs the great stairway with the Carian delegation; later rests in the visitors' tents | N |
| 6 | **Kūruš (Cyrus II, "the Great")** | r. 559–530 BC | memory | Founder of the Achaemenid empire, conqueror of Media, Lydia and Babylon; buried at Pasargadae in the stepped tomb. His Babylonian cylinder is discussed in §6.10. | translucent; Elamite-style robe and a simple crown (we do not have a certain contemporary image; whether the winged figure of Gate R at Pasargadae represents him is debated, and the game does not use it as his portrait) | appears at dusk beside his tomb in the Pasargadae vignette; walks once around it and fades at dawn | M |
| 7 | **Dārayavauš (Darius I)** | r. 522–486 BC | relief + memory | Took the throne in 522 and recorded it at Bisitun; founded Pārsa (site chosen about 518) and began the Apadāna, reorganised the empire's satrapies, standardised weights and coinage, built roads and completed the Nile–Red Sea canal begun by the Egyptian king Necho II. [checked: Iranica "Persepolis"] | relief: the king on his tomb and in the audience panel; memory: like Xerxes but older, white beard | at dusk on the Tačara steps; his tomb at Naqsh-e Rostam is clickable | M |
| 8 | **Atossa (Old Persian probably *Utauθā*)** | c. 550–after 486 BC | memory | Daughter of Cyrus, wife of Darius, mother of Xerxes; very influential according to Herodotus. Some scholars find her in the tablets as "Udusana" (Henkelman); that identification is discussed, not certain. | memory; dignified older woman, veil and crown, a staff | residential-wing court at dusk | N |
| 9 | **Irtašduna (Artystone)** | fl. c. 500 BC | memory | A wife of Darius I, daughter of Cyrus. The Fortification tablets show her running her own estates, giving orders under her own seal and receiving wine and sheep from the palace stores. | memory; seated with a seal and a tablet; attendants with jars | at a garden table, giving instructions to an estate scribe | M |
| 10 | **Parnakka (Old Persian \**Farnaka*)** | fl. 506–497 BC | memory | Head of the institutional economy of Fārs in the Fortification tablets: he authorised rations, travel and payments across the region with his seals. Often called Darius's uncle (a son of Aršam); Henkelman doubts any kinship, so cards say only "a great Persian noble". [checked: Iranica "Persepolis administrative archives", via search summary only] | memory; Median dress, two seals, a stack of tablets | the granary scribes' yard at dusk, inspecting the tablets | M |
| 11 | **Gaubaruva (Gobryas), spear-bearer, and Aspačanā (Aspathines), bow-bearer** | fl. 520–490 BC | relief (clickable) | Two of Darius's highest courtiers, carved beside his tomb with trilingual labels naming their offices (DNc, DNd). Aspathines's label says he "holds the battle-axe" of Darius; his title *vaçabara* is usually translated "bow-bearer", but its meaning is debated. [checked: Livius DNd] | relief figures on the tomb façade | Naqsh-e Rostam vignette | N |
| 12 | **Auramazdā** | — | shrine | The great god of the royal inscriptions ("a great god is Auramazdā, who created this earth, who created yonder sky, who created man, who created happiness for man"). The winged figure in a disc above royal reliefs may represent him or the royal fortune: scholars disagree. | not a figure: the winged disc on reliefs and a fire altar | the fire altars on the terrace and before the tomb; the card explains what the inscriptions say | M |
| 13 | **Tištrya, the rain star** (rows 13–17: the Avesta was handed down orally and written down only in Sasanian times; whether these hymns were told at Pārsa in 470 in this form is not known, and the cards say so) | Avesta | shrine / apparition | The star Sirius, hymned in the Avesta's Tištar Yašt: as a white horse with golden ears he fights the drought demon Apaoša and brings rain to the lands. | a faint white horse with golden ears seen on the mountain ridge during a spring shower | appears only during the "spring shower" weather event | M |
| 14 | **Yima (later Jamshid)** | Avesta | storyteller tale | In the Avesta, the radiant king of a golden age without heat, cold, sickness or death, who built the *vara* enclosure. Persians of the Middle Ages credited the ruins to him (Takht-e Jamshid). | told by an old storyteller near the stairway at dusk; the tale appears as a faint golden silhouette over the terrace | dusk, stairway plaza | N |
| 15 | **Ərəxša (Arash) the archer** | Avesta | storyteller tale | The Tištar Yašt compares the rain star's flight to the arrow of Ərəxša, "the swiftest archer of the Aryans". The famous story of his arrow setting the frontier is told by much later writers. | storyteller tale; an archer silhouette and an arrow streak across the dusk sky | archery ground at dusk | N |
| 16 | **Θraētaona (later Fereydun)** | Avesta | storyteller tale | In the Avesta he is the hero who defeats the three-headed dragon Aži Dahāka. The Shahnameh retelling, with the tyrant Zahhak and the smith Kaveh, is 1,500 years later and is not used here. | tale silhouette: a hero with a mace and a three-headed dragon | dusk, stairway plaza | N |
| 17 | **Saēna, the great bird (later Simurgh)** | Avesta | apparition | The Avesta names the *saēna* bird; later Middle Persian and Persian texts make it the wise Simurgh nesting on the tree of all seeds. | a great bird shadow crossing the mountain at dawn, once per day | dawn | N |

### 4.2 Ordinary people (named)

Names are typical forms of the period (Old Persian, Elamite renderings in the tablets,
Babylonian, Egyptian, Greek, Lydian); the persons are invented. The Susa building inscription of
Darius (DSf) names which peoples did which crafts **for his palace at Susa** (stonecutters:
Ionians and Lydians; goldsmiths: Medes and Egyptians; woodworkers: Lydians and Egyptians; baked
brick: Babylonians; wall decorators: Medes and Egyptians), and the game follows it for Pārsa too;
cards say "at Susa" when they cite it. [checked: Livius DSf translation] The daughter's name
Udusana in the last row is also the Elamite name Henkelman proposes for Queen Atossa; renaming the
child would avoid confusing the two (owner's choice).

| Figure | Who | Where / routine | Card (40–60 words) |
|---|---|---|---|
| **Miθradāta**, scribe | Persian; writes Aramaic on leather and checks Elamite clay tablets | granary yard → treasury | "Miθradāta writes in two worlds: Aramaic in ink on soft leather, and checks the Elamite scribes pressing wedges into clay. Every jar of wine, every sack of barley and every traveller's meal on the royal road ends up on one of his tablets, sealed and filed." |
| **Ṛtakāmā**, overseer of weavers | Persian woman; head of a workshop of women weavers | weaving workshop in town | "Ṛtakāmā leads forty weavers. The tablets show women like her drawing the highest rations in their group, and mothers receiving extra grain after a birth. Her workshop's patterned cloth will become robes for the court and gifts for honoured guests." |
| **Hermon**, stonecutter | Ionian (*Yauna*); DSf says the stonecutters of Darius's Susa palace were Ionians and Lydians | quarry ↔ Hall of a Hundred Columns | "Hermon came from Ionia to cut stone for the king. He reads a block by the sound it makes under his hammer. Today he is shaping a column drum for the new hall; his pay comes partly in barley and partly in weighed silver." |
| **Bēl-iddin**, brickmaker | Babylonian; DSf says Babylonians made the baked bricks | brickfield and kiln in town | "Bēl-iddin's family has made bricks for generations, in Babylon and now in Pārsa. Mudbricks dry in the sun for walls; the best are fired and glazed in blue and yellow. He stamps each mould with a careful thumb." |
| **Pediese**, goldsmith | Egyptian; DSf names Egyptians and Medes as goldsmiths | workshop near the treasury | "Pediese beats gold into leaf thin enough to float, for door fittings and the edges of painted reliefs. He also makes armlets with griffin heads like the ones the Lydians bring as gifts." |
| **Manes**, carpenter | Lydian (Sardian); DSf names Sardians and Egyptians as woodworkers | roof of the new hall | "Manes fits cedar beams that travelled from Lebanon, across rivers and over mountains, to rest on the bull capitals. Up on the scaffold the whole plain lies below him." |
| **Farnadāta**, station master | Persian; keeps a royal-road station | road station | "Farnadāta checks every traveller's sealed travel document, then hands out flour, beer and fodder by the day. Express riders change horses here without stopping to talk." |
| **Irdumartiya**, farmer | Elamite rendering of the Old Persian name *Ṛtavardiya*; a farmer of the plain | fields and threshing floor | "Irdumartiya grows barley along the canal. A share of every harvest goes to the royal stores, and from there back out as rations for the workers on the terrace. When the water is his turn, he opens the channel at dawn." |
| **Daduš and Udusana**, two children | a worker's son and daughter | run between the brickfield, the canal and the stairway plaza | "Daduš and his sister count the delegations climbing the stairs: today the Lydians brought a chariot and the Elamites a lioness with two cubs. They are not allowed on the terrace. They watch from the plaza anyway." |

### 4.3 Hero cards (40–60 words each)

| Figure | Card title · epithet | Text |
|---|---|---|
| Xerxes | **Xšayāršā** · Great King, King of Kings | "Xerxes finished what his father began here and built the Gate of All Lands. His inscriptions say Auramazdā made him king. On the Apadāna stairs, the peoples of an empire from the Aegean to the Indus bring him gifts; here he receives them enthroned under a canopy among slender columns." [checked: "each spring" removed: no ancient text dates the audience; the audience relief shows a canopy, the parasol belongs to the walking king on the door reliefs] |
| Amestris | **Amestris** · Queen | "Wife of Xerxes and mother of the next king. Greek historians told dark stories about her; Persian records tell us more about how royal women lived: they owned estates, travelled with their own staff and sealed their own orders." |
| Artaxerxes | **Artaxšaça** · A young prince | "One day he will finish the Hall of a Hundred Columns. Today he is learning to ride and draw a bow on the plain below the terrace. Greek writers said Persian boys were taught three things: to ride, to shoot and to tell the truth." |
| Mauš (was Baradkama) | **Mauš** · Treasurer | "His name survives on the Treasury tablets of these very years, the receipts of a working empire. Orders reach him to pay craftsmen partly in weighed silver instead of barley; he seals each payment and files the record. The gifts the delegations bring this morning will pass through his doors." [checked: OIP 65 nos. 27–48, addressed to Mauš/Mawuš, Xerxes years 12–19] |
| Artemisia | **Artemisia of Caria** · Queen of Halicarnassus (a visit imagined) | "A Carian queen who commanded ships for Xerxes at Salamis, as Herodotus tells. Here we imagine her climbing the stairway with the Carians, who bring a bull, a shield and a spear on the Apadāna reliefs." |
| Cyrus | **Kūruš** · Founder (a memory) | "Cyrus joined Persians, Medes and Elamites into one empire and took Lydia and Babylon. He rests at Pasargadae in a small stone house on six steps, where magi kept watch, father to son. Two centuries later Alexander found it robbed and had it restored." [checked: Arrian 6.29: the tomb had been plundered; the magi guards had served since Cambyses] |
| Darius | **Dārayavauš** · Builder of Pārsa (a memory) | "Darius chose this mountain foot for a new royal city, raised the terrace and began the Apadāna. He reorganised the empire's satrapies, fixed weights and coinage and cut his story into the cliff at Bisitun in three languages." |
| Atossa | **Atossa** · Daughter of Cyrus (a memory) | "Daughter of one king, wife of another, mother of a third. Greek writers made her powerful and proud. Some scholars think the tablets mention her under the Elamite name Udusana; others are less sure." |
| Irtašduna | **Irtašduna** · Queen of estates (a memory) | "The Fortification tablets show this wife of Darius managing estates, workers and stores in her own name. One order from the king sends her two hundred jars of wine and a hundred sheep." [checked: Iranica "Persepolis Elamite tablets": 200 *marriš* of wine and 100 sheep, PF 1795; a *marriš* is a jar measure of about ten litres] |
| Parnakka | **Parnakka** · Head of the stores (a memory) | "For ten years his seal moved barley, wine, sheep and travellers across Fārs. The tens of thousands of clay tablets found in the fortification wall are largely the paperwork of his office: the most detailed record of daily life in the empire." [checked: Iranica gives "over 30,000 tablets, whole or fragmentary"] |
| Gobryas & Aspathines | **Gaubaruva and Aspačanā** · Spear-bearer and bow-bearer | "Carved beside Darius's tomb, each labelled by name and office in three languages: the king's spear-bearer and his bow-bearer, the closest companions of the throne." |
| Auramazdā | **Auramazdā** · The great god of the inscriptions | "Every royal inscription begins with him: creator of earth, sky, people and happiness. The tablets also show offerings to other gods, Iranian and Elamite. The winged figure in a disc above the reliefs may be him, or the king's fortune; scholars still debate it." |
| Tištrya | **Tištrya** · The rain star | "In the Avesta, the star Sirius takes the shape of a white horse with golden ears, fights the drought demon on the shore of the cosmic sea and wins rain for the lands. Watch the ridge when spring clouds gather." |
| Yima | **Yima** · King of the golden age | "The Avesta's Yima ruled when there was neither heat nor cold, sickness nor death. Medieval Persians, seeing these ruins, believed only he could have built them, and called them the Throne of Jamshid." |
| Ərəxša | **Ərəxša** · The swift archer | "One line of the Avesta remembers him as the swiftest archer of the Aryans, his arrow flying like the rain star. The story of the arrow that set the frontier was told by later writers." |
| Θraētaona | **Θraētaona** · Dragon-slayer | "In the Avesta, Θraētaona defeats Aži Dahāka, the three-headed dragon. Much later Ferdowsi retold the tale with new characters; the old hymn is short and fierce." |
| Saēna | **Saēna** · The great bird | "The Avesta names the *saēna* bird. Later Persian books made it the Simurgh, wise and healing, nesting in the tree of all seeds. At dawn, sometimes, a great shadow crosses the mountain." |
| Lamassu (landmark card) | **The guardians of the Gate** | "Human-headed winged bulls, an old Mesopotamian guardian, crown the east door of Xerxes's gate; plain bulls guard the west. The Persian kings borrowed and made their own the art of every people they ruled." |

---

## 5. Civilization: society in motion

Pārsa was not a city of nobles. The Persepolis Fortification tablets (tens of thousands of tablets
and fragments, mostly Elamite, plus Aramaic and a few in other languages) record rations for
tens of thousands of workers (*kurtaš*), men, women and children of many origins, alongside
travellers, priests, horses and royal women's households. The streets should show that
cross-section.

| Layer | Who you see | Share of walkers | Typical routine |
|---|---|---|---|
| King and royal family | Xerxes, the queen, princes, royal women with households | rare, on the terrace | audience in the morning, garden and hunt in the afternoon |
| Court nobles | Persian and Median-dress courtiers, ushers, the chamberlain | 5 % | arrive at the stairway on horseback, attend the audience, walk in pairs on the terrace |
| Administrators and scribes | Elamite and Aramaic scribes, storekeepers, treasurers, ration suppliers | 8 % | morning at granary and treasury; tablets dry in the sun at noon |
| Guards and soldiers | spearmen and archers of the royal guard, garrison soldiers, cavalry | 12 % | change of guard at dawn and dusk; drill on the plain; night watch with torches |
| Priests | magi (*makuš* in the tablets) and Elamite priests | 2 % | dawn fire at the altar, offerings at mountains and rivers, the *lan* offering |
| Craft workers (kurtaš) | stonecutters, masons, carpenters, brickmakers, goldsmiths, painters, weavers: Persians, Elamites, Ionians, Lydians, Egyptians, Babylonians, Bactrians and more | 30 % | sunrise to late afternoon, monthly ration days |
| Women workers | weavers, grinders, workers in mixed groups; female overseers | 12 % (part of the above) | workshop days; mothers receive extra rations after a birth (double for a boy in the tablets, a fact the card states without comment) |
| Farmers and herders | barley and wheat farmers, gardeners, shepherds, canal workers | 15 % | dawn to dusk in the fields; turns at the water |
| Travellers | royal-road couriers, caravan drivers, delegations, merchants, envoys | 10 % | arrive along the road, rest at the station, climb the stairway on audience days |
| Children | workers' children (the tablets list boys and girls with rations) | 6 % | play by the canal, help carry, learn crafts |

**Enslaved and dependent people.** The *kurtaš* were not all slaves: the tablets show many with
wages, families and regular rations, some deportees, some hired, some attached to estates. Their
legal status varied and is debated. The game shows them as working people with families and names,
never in chains, and the cards say that some had come far from home not by choice.

---

## 6. Civilization: dress, work and how Pārsa was run

### 6.1 Evidence for dress

Persepolis and Susa reliefs (Persian, Median and the 23 delegations); the Susa glazed-brick
archers (Louvre: patterned robes in yellow, brown, white and blue); Achaemenid seals and their
impressions on the Fortification tablets; the gold plaques of the Oxus treasure (a figure with
mouth-covering hood and bundle of twigs, often read as a priest); the Pazyryk carpet and textiles
(Achaemenid-period design from the Altai); Greco-Persian reliefs from Anatolia (Daskyleion) for
women and travel; Greek texts (Herodotus, Xenophon) for names and colours, used cautiously.
Women do not appear on the Persepolis reliefs at all; their dress is reconstructed from seals,
Anatolian Greco-Persian art and regional tradition and is marked **(weak evidence)**.

**Garment names.** Greek writers name a *kandys* (a coat with sleeves, often purple), a *sarapis*
(a royal tunic; Xenophon's king wears purple shot with white) and *anaxyrides* (trousers). The
prevailing view (Iranica, "Candys") is that kandys, sarapis and anaxyrides belong to the **Median
riding costume** and that the kandys is the coat worn over the shoulders with empty sleeves, as
on the reliefs. The Old Persian name of the long pleated **court robe** is unknown; we call it
"court robe". Headgear: the king's tall **fluted crown**; the nobles' straight **fluted felt cap**;
the Medes' **rounded felt cap**; the riding **hood** with side and neck flaps (Greek *kyrbasia*/
*tiara*; modern "bashlyk") that can cover the mouth.

### 6.2 Dress reference

| Kind of person | Garments | Fabric, colours, dyes, rules | Hair, beard | Headgear | Footwear | Jewellery | Carries | Draw at 16–24 px | Evidence |
|---|---|---|---|---|---|---|---|---|---|
| King | ankle-length court robe with wide pleated sleeves, girdle | fine wool or linen dyed purple-red and saffron, gold appliqué borders (Greek texts; Nagel) ; purple is royal | long squared beard in rows of curls; hair bunched at the nape | tall cylindrical fluted crown | low shoes with three straps | torque, bracelets, earrings | staff, lotus flower; parasol and fly-whisk held by attendants | tallest figure + crown + parasol | reliefs, tomb façades |
| Crown prince | as the king, slightly smaller | as king | as king | crown as king's | as king | as king | lotus | stands behind the throne | Treasury audience relief |
| Persian noble | court robe, pleats falling in a fan at the sides | wool/linen; red, blue, yellow, purple; patterned borders | full curled beard, hair bunched | straight fluted felt cap | strapped shoes | torque, bracelets, earrings | lotus, hand on companion's shoulder | long robe + straight cap | Apadāna and Tripylon stairs |
| Median-dress courtier, usher, official | knee-length belted long-sleeved tunic, trousers, kandys coat with empty sleeves over the shoulders | wool, dyed; coat often darker | curled beard | rounded felt cap with neck flap | laced ankle boots | torque, earrings | akinakes (short straight sword) on a strap at the right thigh, staff of office | short coat + trousers + round cap | Apadāna stairs |
| Spearman of the royal guard ("Immortals" is the Greek name; the Old Persian is unknown) | court robe | robes patterned with rosettes or square motifs in yellow, white, brown on blue (Susa bricks) | curled beard | twisted fillet or fluted cap | strapped shoes | earrings, bracelets | tall spear with ball- or pomegranate-shaped butt; bow and quiver on the back | spear twice his height + robe | Susa bricks, Apadāna, Herodotus 7.41 |
| Guard in Median dress | tunic, trousers, kandys | plain dyed wool | beard | rounded cap or hood | boots | — | bow case (gorytos) on the left hip, spear, sometimes a figure-of-eight shield | trousers + bow case | Apadāna stairs |
| Cavalryman | Median riding costume | wool, leather | beard | hood with flaps | boots | — | bow, javelins, horse with tied tail and topknot | rider on a horse with a bunched tail | seals, reliefs |
| Magus (priest) | Median dress | white or undyed wool (white is a later Zoroastrian norm; for 470 plain light colours) | beard | hood drawn over the mouth | boots | — | bundle of twigs (*barsom*), ladle for the fire | hood over the mouth + twig bundle | Oxus treasure plaques, seals |
| Elamite courtier (in the court) | long fringed robe | patterned wool | beard, a band around the head | headband | strapped shoes | — | — | fringe + headband | Apadāna Elamite delegation, Elamite tradition |
| Scribe | Median dress or simple tunic and trousers | undyed or blue wool | beard | rounded cap | boots | seal on a wrist cord | clay tablet and stylus; or pen, ink pot and leather | tablet in hand | tablets, seals, Assyrian reliefs of paired scribes (regional practice) |
| Craft worker (man) | knee-length belted tunic, sometimes trousers | undyed wool or linen, browns and greys | short beard | felt cap or bare head | bare feet or leather wraps | — | tools of the trade | short tunic + tool | delegation servants, regional practice |
| Royal woman (weak evidence) | long robe to the feet with sleeves, mantle | rich dyed wool, patterned borders, purple for royalty | long hair, a braid down the back | low crown or band with a veil falling down the back (not covering the face) | soft shoes | necklaces, earrings, bracelets | — | long veil down the back + crown | seals (royal women's seals in the tablets), Greco-Persian gems, Anatolian reliefs |
| Woman worker (weak evidence) | ankle-length tunic, belt, shawl | undyed wool or linen, earth colours | long hair tied | head cloth or veil down the back | bare feet or simple shoes | bead necklace | spindle, jar, basket | long tunic + head cloth | regional tradition; tablets for occupations only |
| Child | short tunic | undyed | short hair | bare head | bare feet | amulet | toy, small jar | half height, bare head | — |
| Farmer / herder | short tunic, cloak of felt in cold | undyed wool | beard | felt cap | bare feet, wraps | — | hoe, sickle, crook | cap + hoe | regional practice |
| Medes (delegation) | riding costume, kandys | — | beard | rounded cap (first) or hood | boots | — | pitcher, bowls, akinakes, rings, a cloak, coat and trousers | round cap + coat | Apadāna east stair (Livius) |
| Elamites | long cloaks | — | curly hair with a wreath, no hat | wreath | — | — | two bows, two daggers; a lioness and two cubs | wreath + lioness | as above |
| Armenians | riding costume | — | beard | hood with cheek flaps tied at the neck | boots | — | a bridled stallion; a vessel with griffin handles | horse + vessel | as above |
| Parthians | Median-style riding dress | — | beard | face-protecting hood | boots | — | two bowls, a Bactrian camel; last man in a feline skin | camel + hood | as above |
| Babylonians | long robe with tassels | — | beard | conical cap with tassels | — | — | shallow bowls, a fringed garment, a humped bull | conical tasselled cap + bull | as above |
| Lydians | long striped garment | — | beard | tall conical hat | pointed shoes | — | metal phials, bowls, griffin-headed armlets, a two-horse chariot | conical hat + chariot | as above |
| Arians (Haraiva) | short cloak, trousers | — | beard | dust-hood | boots | — | bowls, a camel | — | as above |
| Syrians (Livius's label; often "Assyrians" in other works) | ankle-length smooth cloak, belt | — | beard | wreath or band | low shoes | — | bowls, an ox-hide-shaped copper ingot, two rams, a tasselled garment | rams | as above |
| Cappadocians | riding costume with a fibula-pinned cloak | — | beard | tied hood | low shoes | — | a stallion, an overcoat, coat, trousers | cloak pin | as above |
| Saka (Scythians) | riding costume | — | beard | tall **pointed** hood | boots | — | a horse with a bell, decorated rings, an overcoat, coat, trousers; leader with sword and bow | pointed hat | as above |
| Egyptians | (relief damaged) linen kilt and shawl by Egyptian convention | white linen | — | — | — | — | (traces of a hippopotamus) | white linen | as above |
| Yaunā (Ionians, Greeks) | dressed like the Lydians, striped sleeves, no hat | — | beard | none | low shoes | — | ribbed metal cups, shallow bowls, folded cloth, a pair of balls of thread or round cakes (uncertain) | bare head + folded cloth | as above |
| Bactrians | Median-like riding dress with different trousers | — | knotted hair with wreath | wreath | boots | earrings | bowls, a Bactrian camel | camel + wreath | as above |
| Gandharans | short sleeveless tunic, cape | — | beard | — | — | — | a water buffalo, five lances, a shield | buffalo | as above |
| Arachosians | trousers, tunic | — | — | wreath with a tassel | — | earrings | a camel, bowls | — | as above |
| Sagartians | riding costume | — | — | face-protecting hood | boots | — | garments, a stallion | — | as above |
| Sogdians | (damaged) tight-fitting cap | — | — | tight cap | — | — | a sword, oblong rings, battle-axes, a stallion | axes | as above |
| Indians (Hindush) | short wrapped lower garment, bare upper body (by regional convention) | cotton | beard, long hair tied | — | barefoot | — | baskets of gold dust on a shoulder pole; a mule and axes | shoulder pole with two baskets | as above |
| Thracians (Skudra) | chiton | — | — | felt cap | — | — | spears, round shields, a stallion | — | as above |
| Arabs | long tasselled garment | — | — | no cap | — | — | a dromedary | dromedary | as above |
| Carians | Lydian-like, with a wreath | — | — | wreath | — | — | round shield, spear, a bull | — | as above |
| Libyans | (damaged) | — | — | no cap | — | — | an oryx (antelope), a chariot | oryx | as above |
| Kushites (Nubians) | wrapped garment | — | short curly hair | — | barefoot | — | an elephant tusk, an okapi (identification debated), a small lidded bowl | tusk | as above |

**Common mistakes to avoid (Pārsa).** Sasanian crowns with globes and fluttering ribbons
(800 years later). Turbans, Islamic-era robes or veils covering women's faces. Curved scimitars
(the Achaemenid sword is the short straight *akinakes*). Chain mail or plate armour on courtiers.
Greek hoplite gear on Persians. Clean-shaven Persian men. Everything gold: the court was colourful
textile first, gold second. Calling the winged disc "Faravahar" as if that were its ancient name
(the name comes from Middle Persian *fravahr* and was attached to the symbol in modern times;
cards may say "known in Iran today as the Faravahar", with respect: it is a cherished symbol). Masks or monstrous "Immortals". Persians in Median dress only (both
costumes appear side by side). Camels and elephants as ridden war animals in the city.

### 6.3 Occupations and work

| # | Job | Where (district / landmark) | Tools and materials | Steps (looping actions) | Hours / season | Who | Product → next |
|---|---|---|---|---|---|---|---|
| 1 | Quarryman | `quarry` | iron chisels, wedges, mallets, wooden levers | mark line → cut slot → drive wedges → lever block free | dawn to afternoon; dry seasons | kurtaš men; DSf: Ionians and Sardians cut stone | rough block → **ox sledge** |
| 2 | Ox driver / hauler | quarry ramp → terrace road | sledge, rollers, ox team, ropes | yoke → pull → set rollers → unload | daytime | labourers | block → **mason's yard** at `hall_100` |
| 3 | Mason / column setter | `hall_100` | shear-leg crane, ropes, dowels, lead | sling drum → hoist → guide → set on dowel | daytime | Ionian, Lydian, Persian masons | column → **sculptor** |
| 4 | Relief sculptor | stair façades, door frames | point, claw and flat chisels, drill, abrasive | sketch in red → rough out → model → smooth | daytime | specialists of many origins | relief → **painter** |
| 5 | Painter | reliefs, walls | pigment bowls (Egyptian blue, ochres, malachite), brushes, gold leaf | grind pigment → mix → paint → gild | daytime | specialists | finished façade |
| 6 | Carpenter | roofs, doors | cedar beams, adze, saw, bow drill | measure → saw → adze → fit beam | daytime | DSf: Sardians and Egyptians | roof/doors |
| 7 | Brickmaker | brickfield (town) | clay, straw, water, wooden moulds | mix → mould → stamp → dry in rows | spring–autumn | Babylonians (baked bricks, DSf), local workers | mudbricks → **walls**; good bricks → **kiln** |
| 8 | Kiln worker / glazer | kiln, town | glaze, fuel, kiln | load → fire → glaze → refire | daytime | Babylonian specialists | glazed bricks → **gates, inscriptions** |
| 9 | Plasterer | building walls | lime/clay plaster, red hematite paint | mix → spread → smooth → paint red | daytime | workers | finished walls, red floors |
| 10 | Goldsmith | workshop near `treasury` | gold sheet, punches, small anvil, crucible | melt → hammer → punch design → polish | daytime | DSf: Medes and Egyptians | foil, armlets, vessels → **treasury** |
| 11 | Weaver | weaving workshop | upright loom, wool, dyes | card → spin → weave → fold | daytime, all year | women and men; tablets list textile workers in large groups | cloth → **court robes, gifts** |
| 12 | Dyer | dye yard by the canal | vats, madder, indigo/woad, weld, alum | soak → dip → rinse → hang | daytime | workers | coloured yarn → **weavers** |
| 13 | Grain grinder | houses, granary | saddle quern, sieve | pour → grind → sift → bag | morning | mostly women | flour → **baker** |
| 14 | Baker / cook | royal kitchens (Hadiš service rooms), town ovens | tanūr oven, flour, fuel | knead → slap dough on oven wall → peel off → stack | dawn and before meals | men and women | bread → **meals, rations** |
| 15 | Brewer / wine steward | storerooms | jars, measures | measure → pour → seal → record | daily | workers, officials | beer and wine rations (tablets) |
| 16 | Elamite scribe | granary yard, treasury | clay, stylus, seal, tablet basket | knead clay → write → roll seal → dry | morning | trained scribes | tablet → **archive in the fortification** |
| 17 | Aramaic scribe | treasury, station | pen, ink, leather | write → seal → roll → file | morning | trained scribes | letters to satraps, accounts |
| 18 | Storekeeper / ration supplier | granary, storerooms | measures, sacks, seals | open store → measure → hand out → seal | monthly ration days | officials | rations → **workers** |
| 19 | Treasurer | `treasury` | balance, karša weights, silver | weigh → record → seal → store | daytime | high officials (Baradkama) | silver wages, gift inventory |
| 20 | Farmer | fields | ard plough, oxen, sickle, hoe | plough → sow → open water → reap | autumn sowing, early-summer harvest | farmers | grain → **threshing floor** |
| 21 | Thresher | threshing floor | threshing sledge or animals, forks | spread → drive animals → toss → bag | early summer | farm families | grain → **granary** |
| 22 | Canal worker | canals, qanat line | spades, baskets, windlass | dig silt → lift basket → empty → check flow | late winter | labour teams | water → **fields, gardens** |
| 23 | Gardener of the paradise | `pavilion`, garden | spade, pruning knife, water jar | dig → plant tree → water → prune | spring and autumn planting | gardeners (tablets mention fruit trees and work in paradises) | fruit → **royal table** |
| 24 | Shepherd | rough ground, steppe | crook, dog, sling | lead out → graze → water → fold | all day | herders | sheep → **meat rations, wool** |
| 25 | Groom / horse trainer | horse lines, cavalry ground | halter, brush, fodder | water → brush → exercise → feed | dawn and dusk | grooms | horses (horses get rations in the tablets) |
| 26 | Royal-road courier | road → station | horse, sealed document | ride in → hand over → change horse → ride out | any hour | express messengers (the tablets record them) | messages relayed station to station |
| 27 | Station master | `road_station` | sealed travel documents, rations | read seal → issue rations → log → send on | any hour | officials | travel supplies, records |
| 28 | Caravan driver | road, caravan yard | camels, donkeys, packs | load → lead → unload → water | day | traders, state carriers | goods → **storerooms** |
| 29 | Spearman of the guard | stairway top, gates, Apadāna | spear, bow, quiver | stand → present spear → march → relieve | shifts | guard (Persians) | security, ceremony |
| 30 | Archer / soldier | garrison, archery ground | bow, arrows, wicker shield | string bow → draw → loose → collect arrows | morning drill | soldiers | training |
| 31 | Magus | fire altars, mountain shrine | ladle, twig bundle, fuel | feed fire → chant → offer → bow | dawn and dusk | priests (*makuš*, tablets) | offerings (tablets record grain and wine for gods) |
| 32 | Elamite priest | small shrine in town | offering table | pour → offer bread → pray → clean | festival days | priests | offerings to Humban and other Elamite gods (tablets) |
| 33 | Usher / chamberlain | Apadāna north portico | staff | greet → lead delegation → present → bow (hand to mouth) | audience mornings | officials in Median dress | audience |
| 34 | Court musician | pavilion, residential wing | angular harp, pipes, frame drum | tune → play → rest → play | evenings | women and men (Greek writers mention many women singers at court) | music |
| 35 | Water carrier | channels, kitchens | jars, yoke | fill → carry → pour → return | morning | servants, children | water |

**Visible chains.**
quarry → sledge → mason → sculptor → painter → finished façade;
field → threshing floor → granary (scribe writes a tablet) → grinder → oven → workers' rations;
clay pit → brickfield → kiln → glazer → gate;
delegation on the road → station (travel seal checked) → stairway → audience → treasury (weigh,
record) → storerooms;
sheep → shearing → dyer → weaver → robe → noble on the terrace.

### 6.4 How Pārsa is run

| Area | How it worked | Where it is visible |
|---|---|---|
| Kingship and court | The king rules "by the favour of Auramazdā". The court travels between Susa, Ecbatana, Babylon and Pārsa through the year; at Pārsa the king receives nobles and delegations. | `apadana` audience (event); king on the Hadiš terrace |
| Administration of Fārs | A chief official (Parnakka in 506–497) heads the regional economy: grain, livestock, wine, workers and travellers, through a hierarchy of storekeepers, each with a seal. Orders and receipts were written on clay in Elamite, with Aramaic for many letters. | granary yard, treasury, scribes' tablet-drying racks; archive room in the `fort_wall` (where the tablets were found) |
| Satrapies and tribute | The empire is divided into satrapies, each owing tribute (*bāji*) in silver and goods; the Apadāna shows gifts brought in person, a ceremonial exchange that bound the peoples to the king. | stairway procession, treasury doorway, storerooms |
| Wages and rations | Workers receive monthly rations of barley (and wine, beer, sheep for higher grades); from the 490s part is paid in weighed silver (Treasury tablets). | monthly ration day event at the granary; silver weighed at the treasury |
| Law | Darius's inscriptions speak of his *dāta* (law) and of rewarding the loyal and punishing the liar; royal judges are mentioned by Greek writers. | a judge hearing a dispute in a portico (small scene, card) |
| Water | Canals, channels and gardens are managed estates; rock-cut drains carry water off the terrace. | channels, sluices opened at dawn, drains after rain |
| Roads and travel | The royal road with stations at fixed intervals; travellers carry sealed documents (*ḫalmi* in the tablets) entitling them to rations; express riders relay messages. | road station; courier riding through |
| Building works | Teams of workers from many lands under master craftsmen, organised and fed by the administration. | `hall_100` site, quarry, brickfield |
| Army | A standing royal guard, garrison troops on the terrace and cavalry. | garrison, stairway guards, cavalry ground |
| Religion | The state supplies offerings to Auramazdā and to other gods, Iranian and Elamite, and to mountains and rivers (tablets). | fire altars at dawn, a small Elamite shrine, offering at the river ford |
| Record-keeping | Tens of thousands of sealed clay tablets, stored in the fortification and the treasury. | the archive room: shelves of tablet baskets |

### 6.5 How the civilization lived (what to show)

| Topic | Accurate details | Shown as |
|---|---|---|
| Food and farming | Barley is the staple (bread, porridge, beer); wheat for the better-off; wine is a major ration; sesame oil, dates, figs, fruit, sheep and goats, poultry. Fields of the Marvdasht plain watered by canals from the Pulvar and Kur rivers. | fields, threshing floor, granary, ovens, ration day event |
| The king's table | Feasting was central to royal power; the king fed thousands daily (a Greek list preserved by Polyaenus itemises quantities of grain, animals, wine and spices). | kitchens of the Hadiš; servants carrying food up the stair (as on its reliefs) |
| Gardens (*paridaida*, *partetaš*) | Walled royal gardens and orchards with stone channels and pavilions; Greek *paradeisos* gave English "paradise". Tablets mention fruit trees and storage in such estates. | `pavilion`, channels, planting event |
| Crafts | Stonework, carpentry, glazed brick, goldwork, textiles, seal cutting, metal vessels (gold and silver phials, rhyta with animal foreparts). | workshops in D4; the goldsmith; a seal cutter |
| Trade goods | Cedar from Lebanon, gold from Sardis and Bactria, lapis lazuli and carnelian from Sogdiana and the east, ivory from Kush and India, silver from Egypt and Anatolia, ebony from Egypt (all listed as building materials in Darius's Susa charter, DSf). | caravan loads; storeroom labels; card on the Susa charter |
| Money | Silver weighed in shekels; 10 shekels = 1 *karša* (about 83 g). Darius introduced gold darics and silver sigloi (c. 500), but in Fārs weighed silver remained normal. Coins of Lydia and Greek cities were found in the Apadāna foundation deposit. | the treasurer's balance and karša weights |
| Writing | Elamite cuneiform on clay (most documents), Aramaic in ink on leather and clay, Old Persian cuneiform for royal inscriptions (one Old Persian administrative tablet is known), a few tablets in Greek and Phrygian. | scribes, tablet racks, inscription panels |
| Schooling | Scribes were trained by apprenticeship; noble boys trained in riding, archery and truthfulness (Greek report). | scribe teaching a boy; prince on the archery ground |
| Medicine | Egyptian and Greek physicians served at court (the Udjahorresnet inscription, an Egyptian source; Democedes, in Herodotus). | card only (N) |
| Religion and festivals | Fire altars (shown on royal tombs; Herodotus 1.131–132 claims the Persians used "no altar" and "no fire" in sacrifice, a Greek outsider's view that the Persian reliefs contradict, so the game follows the reliefs [checked: Herodotus 1.131–132, Rawlinson]); offerings of the *lan* type for Auramazdā; Elamite gods (Humban and others) also served; offerings to mountains and rivers; the month *Bāgayādi* ("worship of the gods"). Later sources mention an autumn festival of Miθra (Mithrakāna). | altars, priests, river offering, festival events |
| Music and dance | Harps, pipes and drums of a long Elamite and Mesopotamian tradition; women singers at court (Greek writers). | evening music in the pavilion |
| Death and burial | Kings in rock-cut tombs (Naqsh-e Rostam); Cyrus in a free-standing tomb. Burial customs of ordinary people varied; Herodotus reports that magi exposed the dead to birds and dogs, while Persians coated bodies in wax and buried them. | the two tomb vignettes; no burial scene in the city |
| Hunting and riding | Royal hunts in game parks; horse breeding (the Nisaean horses of Media). | riders on the plain; hounds |

### 6.6 The land beyond the walls (on this map)

| Element | On the main map or satellite | Plan coordinates | What it shows |
|---|---|---|---|
| Fields, canals, village | main map | D6 | spring barley, ploughing, threshing |
| Qanat line (N) | main map | c 20..119, r 138..140 | shafts, a windlass, the outflow |
| Quarry | main map | `quarry` | the start of every stone chain |
| Royal-road station and caravans | main map | D7 | couriers, camels, delegations arriving |
| Cavalry and archery ground ("Immortals' quarters" are the `garrison` on the terrace) | main map | D8 | drill, riding, archery |
| Paradise with the glazed gate | main map | D5 | gardens, pavilion, planting |
| Naqsh-e Rostam | satellite S1 | c 0..26, r 0..22 | Darius I's tomb, the tower, a fire altar |
| Pasargadae | waypoint north of the region | world C 1176..1203, R 260..287 | Cyrus's tomb, the palace garden channels, the gatehouse relief |
| Royal Road east to Sardis: Persian Gates, Susa, Babylon, the Euphrates and Halys crossings, Gordion, Sidon, Sardis | waypoints in the connective stretches | §3.7 and `world.md` §6 | the empire on the road: stations, caravans, delegations heading for Pārsa |

### 6.7 The empire at large

The 23 peoples of the Apadāna east stair (above) are the in-city presence of the empire. The game
shows them as:

- **Delegations** (event, §7): each set is a usher (alternating Persian and Median dress) holding
  the leader's hand, 2–4 members and their gifts, walking up the stairway in the order of the
  relief (Medes first, then Elamites, Armenians, Parthians, Babylonians, Lydians, Arians, Syrians,
  Cappadocians, Saka, Egyptians, Yaunā, Bactrians, Gandharans, Arachosians, Sagartians, Sogdians,
  Indians, Thracians, Arabs, Carians, Libyans, Kushites). Must-have sets: Medes, Elamites,
  Babylonians, Lydians, Saka, Yaunā, Indians, Arabs. [checked: Livius "Apadana east stairs" lists
  the same 23 peoples and gifts (in photo order, not procession order). The order above follows
  one modern numbering; Schmidt (1953) and Walser (1966) number and name some delegations
  differently, so cards never say "the fourth delegation" and mark doubtful names as "probably".]
- **Goods**: storeroom and caravan props labelled by origin (cedar from Lebanon, gold from
  Bactria and Sardis, lapis from Sogdiana, ivory from Kush, ebony from Egypt, silver, textiles).
- **World map labels**: satrapies named in Old Persian with English beneath (Māda, Ūja/Elam, Bābiruš,
  Sparda/Lydia, Yaunā, Mudrāya/Egypt, Bāxtriš, Gandāra, Hinduš, Arabāya, Kūšā), following the
  lists in Darius's inscriptions (DB, DNa, DSe). Lists differ slightly between inscriptions.
- **Cards**: one per delegation (gift, dress, homeland), unlocked by watching it climb.

### 6.8 A year in Pārsa

Old Persian month names are known from royal inscriptions (some reconstructed from Elamite forms).

| Season (month) | Work | Festival / event in game |
|---|---|---|
| Spring: *Ādukanaiša*, *Θūravāhara* (Mar–May) | canals full, gardens flower, delegations travel | **spring audience of delegations** (the game's moment); planting of fruit trees |
| Early summer: *Θāigarči*, *Garmapada* (May–July) | barley harvest and threshing | harvest offering at the threshing floor |
| Late summer (July–Sept) | heat, dust; the court has moved to cooler Ecbatana (Greek reports) | quiet terrace, building work continues |
| Autumn: *Bāgayādi* ("worship of the gods", Sept–Oct) | ploughing and sowing | offerings to the gods; (Mithrakāna, attested only in Greek texts, N) |
| Early winter: *Āçiyādiya* ("worship of fire"?, Nov–Dec; meaning debated) | wool work, repairs | fire-altar evening event |
| Winter: *Anāmaka*, *Viyaxna* (Dec–Mar) | cold, snow on the mountain, roads muddy (the tablets show fewer travellers) | snow event (N) |

The game is set in spring, but the clock's festival schedule can rotate through seasonal events
for variety (owner's choice). Default: spring only.

### 6.9 A day in Pārsa (schedule for ambient scenes)

| Time | Scene |
|---|---|
| Pre-dawn | stars; guards with torches; the magus rekindles the fire altar |
| Dawn | fire offering and chant; gardeners open the channels; grooms water horses; bakers fire ovens |
| Morning | change of guard; scribes at the granary; **audience** in the Apadāna (event every 12 in-game minutes, §7); masons start at the hall; caravans arrive |
| Midday | heat; tablets dry in rows; workers eat bread and drink beer in the shade; the court withdraws |
| Afternoon | quarry and building site busy; royal ride on the plain; archery practice; dyers rinse cloth |
| Dusk | the court dines (servants carry dishes up the Hadiš stair); lamps lit; change of guard; storyteller at the stairway plaza (myth cards); memories appear |
| Night | music in the pavilion; torches on the fortification; patrols; owls; the great star field; Sirius rising (Tištrya) |

### 6.10 Knowledge and ideas (met as places, people and cards)

| Idea | How the visitor meets it |
|---|---|
| **An empire of many peoples** | the delegations; the Susa charter card ("the stone-cutters were Ionians and Sardians…"); workers of many origins with names |
| **Administration and archives** | scribes, seals and tablets; the archive room; Parnakka's memory; the card "the most detailed paperwork of the ancient world" |
| **The royal road and relay riders** | the station and couriers; card quoting Herodotus's admiring description (that nothing mortal travels faster than these riders) as a Greek outsider's view |
| **Gardens and "paradise"** | the paradise with channels; card on the word |
| **Monumental art drawing on many peoples** | lamassu from Assyria, Egyptian cornices, Ionian stone techniques, all made Persian; card on the Gate |
| **The Cyrus Cylinder (careful)** | card attached to Cyrus's memory: "A clay cylinder written in Babylonian cuneiform after Cyrus, 'king of Anšan', took Babylon in 539 BC, and buried in the city's wall. In the manner of Mesopotamian kings, it says Marduk chose Cyrus, blames the previous king, and says Cyrus entered Babylon without battle, returned the images of gods to their shrines in a list of cities from Aššur and Susa to the Zagros, and gathered their people and gave them back their homes. It does not name the Jews; their return is told in the Hebrew Bible. Often called the first charter of human rights, and treasured in Iran today, it is to historians a royal proclamation of a policy of restoring local cults and peoples." [checked: Cylinder lines 12, 17, 20–21, 30–32 in the Livius translation (after Cogan and Schaudig)] |
| **A New Year at Pārsa? (careful)** | card at the great stairway, shown on the first audience: "The Persian year began with the month Ādukanaiša, near the spring equinox. Many scholars, among them the Iranian historian Shapur Shahbazi, think this terrace was built for the New Year, the festival later called Nowruz; others answer that no ancient text says so and that the reliefs show an ideal, timeless empire. The name Nowruz first appears centuries later, in Middle Persian. Whether today's Nowruz reaches back to these stairs, no one can yet prove." The word "Nowruz" appears only on this card, never as the name of the in-game event. [checked: see §1] |
| **Religion and its limits** | the Auramazdā card, plus a fair note: Xerxes's own "daiva inscription" says he destroyed a sanctuary of false gods, so royal tolerance had limits |
| **Standards** | the karša weight and the daric card; Darius's canal from the Nile to the Red Sea (his Suez inscriptions) as a card |

---

## 7. Ambient life and events

### 7.1 Walkers and routines

| Group | Count (day / night) | Path or zone | Routine |
|---|---|---|---|
| Nobles in pairs | 10 / 2 | stairway → Gate → Apadāna → Tripylon | walk, stop and talk (hand on shoulder, as on the Tripylon stair), climb |
| Guards | 16 / 12 | stairway top, Gate doors, Apadāna portico, Treasury, fortification | stand; shift change at dawn and dusk (march in pairs) |
| Scribes | 6 / 0 | granary yard ↔ treasury ↔ archive | carry tablet baskets, sit and write |
| Builders | 24 / 0 | quarry ↔ `hall_100` | chains in §6.3 |
| Weavers, grinders, dyers | 14 / 2 | town workshops | loop actions |
| Farmers, herders | 16 / 0 | fields, rough ground | plough, water, herd sheep home at dusk |
| Gardeners | 6 / 0 | paradise | plant, water, prune |
| Grooms and horses | 8 / 2 | horse lines, cavalry ground | water, lead, ride |
| Couriers | 1 every 3 min | west edge → station → stairway | ride in, change horse, ride out |
| Caravan | 1 every 6 min | west edge → caravan yard → storerooms | 4 camels, 2 drivers |
| Children | 8 / 0 | town, canal, plaza | run, play knucklebones, watch delegations |
| Magi | 2 / 1 | fire altars | tend fire |

### 7.2 Timed events

| Event | Trigger | Route and cast | Effects |
|---|---|---|---|
| **Audience of the delegations** (M) | every 12 in-game minutes in the morning | 3 delegation sets per audience (rotating through the 23) climb the great stairway, pass the Gate, cross to the Apadāna north stair, are presented by the usher to the king in the portico (bow with hand before mouth, as on the relief), then hand gifts to treasury officials | incense smoke, a soft drum and harp phrase, the crowd hushes; journal unlocks the delegation's card |
| Change of guard (M) | dawn and dusk | spearmen march from the garrison to the stairway and Gate | measured footsteps, a horn call |
| Ration day (M) | every 20 minutes | workers queue at the granary; scribes write; sacks handed out | busy chatter |
| Royal ride (N) | afternoon | king and escort ride down the south stair onto the plain and around the gardens | hoofbeats, dust |
| Spring shower (M) | weather, random | clouds over the mountain; rain; water runs from the drain outfalls; Tištrya apparition | rain bed, dripping, a rainbow after |
| Planting in the paradise (N) | once per in-game day | gardeners plant a young tree (player may help, §9) | |
| Storyteller at dusk (M) | dusk | an old man at the plaza; myth cards appear as faint silhouettes over the terrace | low harp, crickets |
| Arrival of a caravan from the Gulf (N) | random | camels with pearls, dates and incense jars | bells |

### 7.3 Birds, insects, small life

Swallows and swifts around the columns (morning, evening), house sparrows, a hoopoe in the garden,
crows on the fortification, white storks on the plain and nesting on a tower, rock doves at the
quarry, partridges (chukar) on the slope; bees and butterflies in the garden; owls and bats at
night; frogs by the canal after rain.

---

## 8. Light, weather and season

**Season:** early spring at 1,600 m altitude: crisp mornings, mild days (about 15–20 °C), cold
nights, clear air. Snow lingers on the Zagros ridges; the plain is new green; almond and pomegranate
blossom.

| Time | Sky (top → horizon) | Grading target | Light character |
|---|---|---|---|
| Dawn | `#2b3a67` → `#e8a87c` → `#f6d7a7` | warm gold highlights on stone, blue-violet shadows, mountain backdrop cold blue | long shadows, mist on the plain, stone glows honey-gold first on the Hadiš and Apadāna tops |
| Day | `#4a86c8` → `#9cc6e8` → `#e9eef0` | high clarity, slightly cool neutral, saturated greens, grey stone reads silver | almost no haze close up; distant mountains pale blue; crisp shadows |
| Dusk | `#3d2c5a` → `#c75b39` → `#f2b46d` | stone turns rose and copper, shadows purple | the mountain glows pink then grey; first torches |
| Night | `#0b1026` → `#1b2445` | deep blue, low saturation; warm pools of torch and fire light | very bright stars and the Milky Way (high, dry, no city glow); Sirius notably bright |

- **Haze:** light, cool, toward the west edge (the plain); the mountain backdrop has aerial
  perspective (paler with height).
- **Wind:** a steady breeze from the north-west in the afternoon, rippling barley and poplars.
- **Dust:** a dry "dust breeze" weather (pale ochre motes, slightly warmer grading) after several
  dry days.
- **Rain:** spring showers (rare, memorable): towering clouds build over the mountain, a short
  rain, the drains spout into the plain, a rainbow over the terrace.
- **What glows at night:** fire altars (strong orange), torches at the Gate, stairway and towers,
  braziers in the garrison, oil lamps in the residential wing and town doorways, lanterns in the
  pavilion. Glow layers: `gate_all_lands`, `apadana`, `tacara`, `hadish`, `harem`, `garrison`,
  `fort_wall`, `p_fire_altar`, `p_brazier`, `p_torch`, `p_house`, `pavilion`.

---

## 9. Sound and music direction

### 9.1 Ambience beds

| Bed | Content | Where |
|---|---|---|
| `amb/parsa_day.ogg` | thin dry wind, distant swallows, a far-off chisel ring (irregular, soft), horse snort and bell now and then, very faint voices | everywhere by day |
| `amb/parsa_channels.ogg` | close trickling water in narrow stone channels, frogs at the edges | garden zone, canal |
| `amb/parsa_site.ogg` | chisels, mallets on wedges, rope creak, ox lowing, workers' calls | `hall_100`, quarry |
| `amb/parsa_night.ogg` | crickets, a lone owl, wind over stone, a guard's footsteps, a fire crackle | everywhere at night |
| `amb/parsa_rain.ogg` | spring rain on stone and leaves, gurgling drains | rain weather |
| One-shots | distant horn call (guard change; a long natural horn), camel grunts, horse bells, hoopoe "hoo-poo-poo", stork bill-clatter | positional |

### 9.2 Music brief

**What is attested.** Almost nothing survives of Achaemenid music itself (Iranica's music
article; Farhat: the dynasty "has left us nothing to reveal the nature of its musical culture").
What we know: the long Elamite tradition of harp ensembles (the Assyrian palace relief of Elamite
musicians welcoming the victors at Madaktu, c. 653 BC, shows vertical and horizontal angular harps,
double pipes and a drum, with singers; the Kul-e Farah rock reliefs show Elamite harp ensembles);
long-necked lutes known in Mesopotamia since the second millennium; frame drums and small
cymbals; trumpets and horns for signals. Greek writers mention numerous women singers and
musicians at the Persian court (Xenophon; Athenaeus on the 329 musician women of Darius III) and
say that the magi chanted at sacrifices without pipes (Herodotus 1.132).

**What is not attested for 470 BC.** The *dastgāh* modal system and its instruments (*tār*,
*setār*, *santur*, *kamānche*) are much later; the short-necked *barbat* is Parthian/Sasanian;
the name *chang* for the angular harp is later (the instrument itself is ancient). Quarter-tone
intervals as a stylistic shorthand for "Persian" are a modern association. Avoid them as a
cliché.

**Evocative choice (modern, stated as such).** A small court ensemble: **angular harp** (the
central voice: plucked, bright, with gentle decay), **long-necked lute** (drone and ostinato),
**double pipe** (two reed pipes, one droning), **frame drum** and a soft **clapper**. Scales:
diatonic heptatonic modes built from tetrachords (pentatonic gestures on the harp, a whole-tone and
semitone tetrachord on the pipes), with long drones. No quarter tones.

| Piece | Tempo | Form | Mood | Synthesis notes |
|---|---|---|---|---|
| `music/parsa_day.ogg` (about 3 min loop) | 76–84 bpm, steady processional 4/4 with a lilting 6/8 middle section | harp arpeggio over a lute drone (D); pipes enter with a calm, stepwise melody; frame drum marks the processional walk; second section brighter on G | stately, open, sunlit, generous; the feeling of many peoples climbing the same stair | harp: plucked string (Karplus–Strong) with soft body resonance, slight inharmonicity; lute: brighter, more nasal plucks; pipes: reed model with breath noise, one pipe holding a drone; drum: low skin with finger rolls. Natural hall reverb (stone, 1.8 s) |
| `music/parsa_night.ogg` (about 3 min loop) | free tempo, about 56 bpm implied | solo harp with sparse pipe answers; a low hummed vocal drone (wordless, women's voices) | intimate, starry, slightly melancholy, a court asleep | longer decays, more space, quiet wind in the background |

The world-map motif: four rising harp notes D–E–F–A.

---

## 10. What the player does here

| Activity | What exactly | M/N |
|---|---|---|
| Wander and look | pan and zoom over the terrace, the plain, Naqsh-e Rostam, and along the Royal Road west to Sardis; time of day changes everything | M |
| Click figures and landmarks | cards (§4.3, landmark cards for every landmark); first click adds to the Pārsa journal | M |
| Journal | sections: Landmarks (21), People (17 heroes + 9 ordinary), Delegations (23), Things found (12: a karša weight, a sealed tablet, a griffin armlet, a pomegranate spear butt, a glazed brick, a column drum mark, a stonemason's mark, a pigment bowl, a lotus, a horse bell, a halmi travel seal, a cedar beam); progress shown on the overview map | M |
| Gentle tasks (optional, no timers) | 1. Watch all 23 delegations (spread over days). 2. Follow a stone from the quarry to the hall. 3. Open the garden channels at dawn (click three sluices, water flows). 4. Find the storyteller and hear four tales. 5. Find the Saēna bird's shadow at dawn. Each gives a small keepsake | M (1–3), N (4–5) |
| Decorate a garden plot | a walled plot in the paradise (c 44..54, r 9..19, 11 × 11) where the player plants cypresses, poplars, pomegranates, almonds, roses and lays channels with the corner's build tools (region-specific menu) | M |
| Keepsake for the corner | completing task 3 unlocks a small Persian-style channel and a pomegranate tree in the corner's build menu (no `region` tag, so it belongs to the corner) | N |
| Photo mode | as in the corner | M |

---

## 11. Uncertainties for a human to check

Status after the fact-check (`fact-check.md`, November 2026):

1. **Apadāna column height**: resolved: 19.5 m (Shahbazi, Iranica "Persepolis"; Iranica
   "Apadāna": "more than 19 m"). Livius's 25 m and Wikipedia's 24 m are unsupported.
2. **Great stairway**: resolved: 63 + 48 = 111 steps per side, 10 cm rise, 38 cm tread, 6.70 m wide
   (Shahbazi). Coste's 106 is an older count.
3. **Gate of All Lands column height**: "over 16.5 m" (Shahbazi; Livius).
4. **Which capitals stood where**: resolved: bulls (composite) in the hall and north portico, bulls
   directly on the shaft in the west portico, lions in the east portico; **no griffins** on the
   Apadāna.
5. **Hall of a Hundred Columns**: columns "nearly 14 m" (Shahbazi), built 486–c. 450; the exact
   state of the site in 470 is unknown (the building-site look is a reasoned choice).
6. **Tripylon date**: Shahbazi: Xerxes and Artaxerxes I. Possibly unfinished in 470; shown finished
   as a choice.
7. **Delegation identifications** follow Livius; several are debated (§6.7).
8. **Royal women's dress** is reconstructed (weak evidence).
9. **Atossa = Udusana** (Henkelman) is a proposal.
10. **Baradkama**: resolved: treasurer 490–480 only; the treasurer of 470 is **Mauš** (§4.1).
11. **Achaemenid qanats**: attested in Achaemenid Egypt (ʿAyn Manawir, 5th century BC), not dated
    at Pārsa; nice-to-have with a careful card.
12. **Orientation of Cyrus's tomb door**: north-west in secondary sources; confirm in Stronach 1978.
13. **The spring audience = New Year**: a hypothesis with serious supporters and critics; the game
    explains it in one card and never names the event Nowruz (§1, §6.10).
14. **Artemisia's visit** is invented (labelled in her card); her life after 480 is unknown.
