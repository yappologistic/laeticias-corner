# Athens · Ἀθῆναι (Athênai) · summer 432 BC

Design bible for the Athens region and the Greek-time stretches around it. Read `world.md` first
(scale, coordinates, camera, elevation, data model). Evidence: `sources.md` (section "Athens").

Names. Greek forms with transliteration are used on cards: Ἀκρόπολις (Akropolis), Παρθενών
(Parthenōn), Προπύλαια (Propylaia), ἀγορά (agora), Στοὰ Ποικίλη (Stoa Poikilē, the Painted Stoa),
Ἡφαιστεῖον (Hēphaisteion), Πνύξ (Pnyx), Κεραμεικός (Kerameikos), Δίπυλον (Dipylon), Πειραιεύς
(Peiraieus), Ἀθηνᾶ (Athēna). Attic months and festivals keep their Greek names.

---

## 1. Identity

**The moment: the month Hekatombaion (high summer, July–August) of 432 BC, at the Panathenaia,
the last summer before the Peloponnesian War.**

Why this moment:

- **The Parthenon is complete.** Begun in 447, its cult statue (Pheidias's gold and ivory Athena
  Parthenos) was dedicated in 438 and the sculpture of the pediments was finished in 432.
- **The Propylaia stops.** Mnesikles's gateway, begun in 437, was left unfinished in 432; the
  lifting bosses still visible on its blocks today were never cut away. The city is at the very end
  of the Periclean building programme.
- **What does not yet exist**, and so is not shown: the Erechtheion (built 421–406), the Ionic
  temple of Athena Nike (420s), the Stoa of Zeus is only rising (c. 430–420), the New Bouleuterion
  (late 5th century), the Pompeion (c. 400), the stone theatre (4th century), the Pnyx's later
  remodelling (c. 404), and nothing Roman. The Theatre of Dionysos still has wooden seating.
- **Peace, just.** Athens is at the height of the Delian League's wealth; the war begins in spring
  431, the plague in 430 and Pericles dies in 429. 432 is a moment of full brilliance with a cloud
  on the horizon: the Megarian decree has just shut Megarian traders out of the Agora, and hoplites
  are sailing to besiege Potidaea. The cards mention this lightly; the city does not know.
- **The Panathenaia** gives the city its great procession every year (the Great Panathenaia fell
  in 434 and 430; 432 is the annual festival, still with a procession, a sacrifice and a new robe
  for Athena's old olive-wood statue).

**The feeling, in five sentences.**
You smell dry thyme and dust, hot pine resin, olive oil, charcoal smoke from the potters' kilns,
the salt of the sea when the afternoon wind comes in, and the burnt fat and incense of sacrifice
on festival days. You hear cicadas in a wall of sound, the clink of a hammer on marble, an aulos
from a courtyard, the bargaining in the Agora, goat bells on the hills and the wind on the rock.
You see painted marble glittering on the rock above a city of low pale houses, the bronze Athena
whose spear tip flashes in the sun, olive groves silvering in the wind and the blue Saronic Gulf
beyond the Long Walls. Athens is most itself in the **late afternoon**, when the sea breeze cools
the Agora, philosophers walk in the Painted Stoa and the light turns the Parthenon to honey.

**"Aroma" made visible.** Cicadas: a constant shimmer of sound and tiny insects on olive trunks.
Heat: shimmer above the Agora paving at midday. Kilns: thin grey smoke over the Kerameikos. Sea:
gulls and white sails at Piraeus. Dusk: Hymettos turning violet ("violet-crowned Athens", Pindar).

---

## 2. Map plan

### 2.1 Size, scope, orientation

- **Region: 160 × 160 tiles, world origin (576, 220), base level 1.** Local plan coordinates
  `c` (east) and `r` (south): world `C = 576 + c`, `R = 220 + r`; world level = 1 + local level.
- **Camera:** from the south-west (`world.md` §3.2). In view: the Acropolis approach, the
  Propylaia, the Nike bastion, the Parthenon's **west front** (with the pediment of Athena and
  Poseidon contesting the land) and its south colonnade, the theatre's seating on the south slope,
  the Stoa Poikile, the Pnyx, and Piraeus with the sea in the foreground. Hidden: the Parthenon's
  east front (main door; its pediment shows Athena's birth), the Hephaisteion's front, the Odeion's
  north side.
- **Scale:** monuments at `s = 1` (the Odeion at `s = 0.8`); gaps compressed about 4 × (one tile
  between monuments ≈ 16 m of real distance). The whole walled city fits.
- **In scope (region):** the Acropolis and its slopes; the Agora; the Areopagus; the Kerameikos
  with the Dipylon and Sacred Gate; the Pnyx, Hill of the Nymphs and Mouseion; the residential
  demes; the Theatre of Dionysos and the Odeion; the Ilissos with the Olympieion foundations; the
  city wall; the Long Walls; a **Piraeus** satellite; a **Pentelikon** quarry satellite; the Lyceum
  gymnasium.
- **Greek-time waypoints outside the region** (§3.7): Eleusis, the Academy, Corinth, Delphi,
  Olympia, Sparta, Corcyra, Delos, Ephesus.

### 2.2 Districts

| # | District | Plan area (c, r) | Level | Contents |
|---|---|---|---|---|
| D1 | Acropolis plateau | c 66..122, r 74..102 | 10 | sanctuaries and temples |
| D2 | Acropolis slopes | c 58..128, r 66..110 (outside D1) | 2–9 | cliffs, the approach ramp, caves on the north slope, the Klepsydra spring, the Peripatos path |
| D3 | Agora | c 20..52, r 26..62 | 0 | the civic square, stoas, council buildings, market stalls, plane trees |
| D4 | Kolonos Agoraios | c 6..19, r 32..58 | 2 | Hephaisteion on its hill |
| D5 | Kerameikos (inner and outer) | c 0..30, r 0..26 | 0 | potters' quarter, Dipylon, Sacred Gate, the Eridanos, cemetery outside the wall |
| D6 | Areopagus | c 44..56, r 70..80 | 5 | bare rock with rock-cut steps; the council of the Areopagus meets here |
| D7 | Pnyx, Hill of the Nymphs | c 4..30, r 70..104 | 4–6 | the assembly place, Meton's sundial |
| D8 | Mouseion hill | c 34..50, r 112..130 | 8 | open rocky hill, shepherds |
| D9 | Melite, Koile (residential, west and south-west) | c 20..44, r 64..84; c 30..60, r 104..111 | 0–2 | houses, workshops, shrines |
| D10 | Kollytos (residential, south) | c 58..104, r 111..130 | 0 | houses, taverns, the road to Phaleron |
| D11 | Kydathenaion, Skambonidai (residential, north and north-east) | c 54..134, r 26..66 | 0 | houses, workshops, small shrines, a fountain house |
| D12 | South slope sanctuary of Dionysos | c 100..136, r 102..126 | 0–6 | Theatre of Dionysos, old temple, Odeion of Pericles |
| D13 | Ilissos valley | c 104..159, r 118..159 | 0 | the river, plane trees, the Kallirrhoe spring, the Olympieion foundations, olive groves |
| D14 | East and Lyceum | c 136..159, r 26..112 | 0–2 | city wall with the Diochares gate; the Lyceum gymnasium outside it |
| D15 | Long Walls | c 0..20, r 106..131 | 0 | the North and Middle Long Walls with the road between them |
| S1 | Satellite: Piraeus (real: 6 km SW) | c 0..38, r 132..159 | 0–2 | Kantharos and Zea harbours, ship sheds, emporion, Hippodamian street grid, the sea |
| S2 | Satellite: Pentelikon quarries (real: 16 km NE) | c 136..159, r 0..24 | 6–9 | marble quarry faces, the quarry road down to the city |

### 2.3 Landmark placement (local plan coordinates, inclusive)

| Id | Landmark | Footprint (c, r) | w × h | Level | Notes |
|---|---|---|---|---|---|
| `parthenon` | Parthenon | c 96..112, r 90..97 | 17 × 8 | 10 | west front faces the camera; east front (main door) hidden |
| `old_temple` | Old Temple of Athena (foundations, rear part probably repaired) | c 88..98, r 79..84 | 11 × 6 | 10 | the state of this building after 480 is **debated**: some scholars think its western rooms were repaired and used until the 4th century, others that only foundations remained. Chosen: low foundations with a repaired, roofed western chamber |
| `pandroseion` | Pandroseion with the sacred olive | c 84..87, r 79..82 | 4 × 4 | 10 | walled court around Athena's olive tree; the tomb of Kekrops nearby |
| `promachos` | Bronze Athena (Promachos) | c 80..81, r 84..85 | 2 × 2 | 10 | colossal bronze by Pheidias, c. 460–450 |
| `propylaia` | Propylaia (unfinished) | central c 70..75, r 84..90; NW wing c 66..69, r 81..85; SW wing c 66..69, r 89..91 | 10 × 11 overall | 10 | west façade faces the camera |
| `nike_bastion` | Nike bastion (pyrgos) | c 62..65, r 91..95 | 4 × 5 | 9 | in 432 an older small shrine and altar, no Ionic temple yet |
| `approach` | Approach ramp | c 48..61, r 86..92 | 14 × 7 | 1 → 10 | broad ramp, then steps to the Propylaia |
| `brauronion` | Sanctuary of Artemis Brauronia | c 78..86, r 95..100 | 9 × 6 | 10 | stoa with two wings |
| `chalkotheke` | Chalkotheke (bronze store) | c 88..94, r 98..101 | 7 × 4 | 10 | |
| `great_altar` | Great Altar of Athena | c 114..116, r 84..86 | 3 × 3 | 10 | |
| `zeus_polieus` | Sanctuary of Zeus Polieus | c 116..120, r 79..83 | 5 × 5 | 10 | |
| `sculpt_yard` | Sculptors' and masons' yard | c 113..121, r 88..98 | 9 × 11 | 10 | east of the Parthenon: blocks, the last pediment scaffolds being taken down, a crane |
| `hephaisteion` | Hephaisteion | c 11..18, r 42..45 | 8 × 4 | 2 | front faces east (hidden); nearly finished, cult statues not yet made (421–415) |
| `royal_stoa` | Stoa Basileios (Royal Stoa) | c 20..21, r 31..35 | 2 × 5 | 0 | small Doric stoa facing east; the laws of Solon displayed here |
| `stoa_zeus` | Stoa of Zeus Eleutherios (building site) | c 20..23, r 38..48 | 4 × 11 | 0 | foundations and first columns, scaffolding |
| `old_bouleuterion` | Old Bouleuterion | c 20..25, r 50..55 | 6 × 6 | 0 | council house of the 500 |
| `tholos` | Tholos | c 21..25, r 57..61 | 5 × 5 | 0 | round dining hall of the 50 prytaneis on duty |
| `stoa_poikile` | Stoa Poikile (Painted Stoa) | c 30..39, r 26..28 | 10 × 3 | 0 | faces south onto the square (in view) |
| `twelve_gods` | Altar of the Twelve Gods | c 34..35, r 31..32 | 2 × 2 | 0 | fenced altar; the milestone point of Athens |
| `tyrannicides` | Statue group of Harmodios and Aristogeiton | c 40..41, r 40..41 | 2 × 2 | 0 | bronze group by Kritios and Nesiotes (477/6) |
| `se_fountain` | Southeast fountain house | c 46..49, r 58..61 | 4 × 4 | 0 | women fill hydriai |
| `lawcourt` | Rectangular enclosure (law court; identification debated) | c 30..36, r 57..62 | 7 × 6 | 0 | |
| `horos` | Agora boundary stone ("I am the boundary of the Agora") | c 26, r 62 | 1 × 1 | 0 | |
| `simon_shop` | Simon the shoemaker's house and shop | c 26..28, r 63..64 | 3 × 2 | 0 | a 5th-century house where hobnails and a cup inscribed SIMONOS were found |
| `eleusinion` | City Eleusinion | c 54..58, r 66..70 | 5 × 5 | 2 | sanctuary of Demeter and Kore on the Panathenaic Way |
| `dipylon` | Dipylon gate | c 8..14, r 6..12 | 7 × 7 | 0 | double gate with a court; the Panathenaic Way starts here |
| `sacred_gate` | Sacred Gate | c 2..6, r 14..18 | 5 × 5 | 0 | the Sacred Way to Eleusis leaves here beside the Eridanos |
| `pnyx` | Pnyx assembly place (phase I) | c 12..28, r 86..100 | 17 × 15 | 4–6 | natural slope falling north to the speakers' platform (bema) at c 19..21, r 86..87 |
| `meton_dial` | Meton's sundial (heliotropion) | c 26..27, r 101..102 | 2 × 2 | 6 | Meton observed the summer solstice in 432 BC (N) |
| `theatre` | Theatre of Dionysos (wooden seating) | cavea c 104..118, r 104..115; orchestra c 108..113, r 116..120 | 15 × 17 | 0–6 | seating faces south (in view) |
| `dionysos_temple` | Old temple of Dionysos Eleuthereus | c 106..112, r 121..124 | 7 × 4 | 0 | |
| `odeion` | Odeion of Pericles | c 120..132, r 102..115 | 13 × 14 | 0 | `s = 0.8`; forest of columns under a pyramidal roof |
| `olympieion` | Olympieion foundations (abandoned 6th-century temple) | c 134..152, r 128..138 | 19 × 11 | 0 | huge unfinished platform and column drums |
| `kallirrhoe` | Kallirrhoe spring | c 136..138, r 140..142 | 3 × 3 | 0 | |
| `lyceum` | Lyceum gymnasium | c 148..159, r 50..66 | 12 × 17 | 1 | outside the wall: track, grove, cavalry and hoplite drill |
| `city_wall` | Themistoclean wall (kit) | circuit, see §2.5 | — | 0–6 | |
| `long_walls` | North and Middle Long Walls (kit) | c 0..20, r 106..131 | — | 0 | |
| `piraeus_*` | Piraeus set: Kantharos harbour, Zea ship sheds, emporion stoa, grid | S1 | — | 0–2 | see §3.2 |
| `pentelikon_quarry` | Pentelikon quarry face | c 140..159, r 0..18 | 20 × 19 | 6–9 | road down along c 130..150 |

### 2.4 Plan

Local coordinates, north up, 1 character = 4 × 4 tiles; generated from the tables above (later
footprints win where they share a cell). Unlabelled `.` cells are lanes, gardens and open ground
inside the walls, or fields and the road to Phaleron outside them.

```
   c→ 0       32      64      96      128     
r  0  kkkkkkkk,,,,,,,,,,,,,,,,,,,,,,,,,,QQQQQQ
r  4  kkDD######################,,,,,,,,QQQQQQ
r  8  kkDDkkkk..........................QQQQQQ
r 12  GGDDkkkk..........................QQQQQQ
r 16  GG~~~~~~..........................QQQQQQ
r 20  #kkkkkkk..........................QQQQQQ
r 24  #kkkk::SSS::::hhhhhhhhhhhhhhhhhhhhQQQQQQ
r 28  #....r:STS~~~~hhhhhhhhhhhhhhhhhhhh..#,,,
r 32  #KKKKr::T:::::hhhhhhhhhhhhhhhhhhhh..#,,,
r 36  #KKKKx::::::::hhhhhhhhhhhhhhhhhhhh..#,,,
r 40  #KHHHx::::t:::hhhhhhhhhhhhhhhhhhhh..#,,,
r 44  #KHHHx::::::::hhhhhhhhhhhhhhhhhhhh..#,,,
r 48  #KKKKBB:::::::hhhhhhhhhhhhhhhhhhhh..#lll
r 52  #KKKKBB:::::::hhhhhhhhhhhhhhhhhhhh..#lll
r 56  #KKKKOOjjj:ff:hhhhhhhhhhhhhhhhhhhh..#lll
r 60  #....OOjjj:ff:hhhhhhhhhhhhhhhhhhhh..#lll
r 64  #....hhhdddd.eessssssssssssssssssh..#lll
r 68  #nnnnnnnddddaeessssssssssssssssss...#,,,
r 72  #nnnnnnnddddaass^^^^^^^^^^^^^^^ss...#,,,
r 76  #nnnnnnnddddaass^^^^^*ooo^^^^zzss...#,,,
r 80  #nnnnnnnhhhaaassYY^^^*ooo^^^^zzss...#,,,
r 84  #nnXXXXXhhhh////YYY^!^ooo^^^++^ss...#,,,
r 88  #nnXXXXX....////NYY^^^^^PPPPyyyss...#,,,
r 92  #nnXXXXX....////N^^bbb^^PPPPyyyss...#,,,
r 96  #nnXXXXX......ss^^^bbbccPPPPyyyss...#,,,
r100  #nnXXXXX......ss^^^bbbcc^^^^^^WWWW..#,,,
r104  LnnnnnnnhhhhhhssssssssssssVVVVWWWW..#,,,
r108  LLLLLL.hhhhhhhssssssssssssVVVVWWWW..#,,,
r112  LLLLLL..uuuuu.hhhhhhhhhhhhVVVVWWWW..,,,,
r116  LLLLLL..uuuuu.hhhhhhhhhhhhVVVV,,,,,,,~~~
r120  LLLLLL..uuuuu.hhhhhhhhhhhhvvvV,,,,,~~~~~
r124  LLLLLL..uuuuu.hhhhhhhhhhhhvvv,,,,,,~~~,,
r128  LLLLLL..uuuuu.hhhhhhhhhhhh,,,,,,~IIIIII,
r132  ZZZZZZZZZZ................,,,,,,~IIIIII,
r136  ZZZZZZZZZZ...################~~~~IIIIII,
r140  ZZZZZZZZZZ................,,,~~~,,,,,,,,
r144  ZZZZZZZZZZ................,,,~~~,,,,,,,,
r148  ZZZZZZZZZZ................,~~~~~,,,,,,,,
r152  ~~~~~~~~~~................,~~~,,,,,,,,,,
r156  ~~~~~~~~~~................,~~~,,,,,,,,,,
```

Legend: `k` Kerameikos, `D` Dipylon, `G` Sacred Gate, `#` city wall (simplified), `L` Long Walls,
`Z` Piraeus, `~` water (Eridanos, Ilissos, sea), `:` Agora, `S` Stoa Poikile, `T` Altar of the
Twelve Gods, `t` Tyrannicides, `r` Royal Stoa, `x` Stoa of Zeus (site), `B` Old Bouleuterion, `O`
Tholos, `j` law court, `f` fountain house, `K` Kolonos Agoraios, `H` Hephaisteion, `e` Eleusinion,
`a` Areopagus, `n` Pnyx and Hill of the Nymphs, `X` Pnyx assembly place, `u` Mouseion, `h`
houses, `d` player's courtyard house, `s` Acropolis slopes, `^` Acropolis plateau, `/` approach
ramp, `N` Nike bastion, `Y` Propylaia, `!` bronze Athena, `*` Pandroseion, `o` Old Temple, `P`
Parthenon, `b` Brauronion, `c` Chalkotheke, `+` Great Altar, `z` Zeus Polieus, `y` sculptors'
yard, `V` theatre, `v` old temple of Dionysos, `W` Odeion, `I` Olympieion foundations, `l`
Lyceum, `Q` Pentelikon quarry, `,` fields, olive groves and pasture.

### 2.5 Streets, water, walls and gates

- **Panathenaic Way** (the processional street, gravel, 3–4 tiles wide): Dipylon (c 11, r 12) →
  south-east through the Kerameikos and across the Agora diagonally → Eleusinion (c 56, r 68) →
  around the Areopagus' east side → the approach ramp (c 48, r 89) → Propylaia.
- **Sacred Way**: Sacred Gate (c 4, r 16) → west out of the region (world C 576, R 236) → Eleusis.
- **Peripatos**: a path around the Acropolis at mid-height (level 4–5) linking the north caves,
  the theatre and the approach.
- **Streets**: narrow unpaved lanes (1 tile) between house blocks, a few wider streets (2 tiles)
  to the gates. The street to Piraeus runs between the Long Walls.
- **Water**: the Eridanos (a small stream, partly channelled) from the east of the Agora (c 54,
  r 30) north-west to the Sacred Gate; the Ilissos (3 tiles wide, shallow in summer) from the
  east edge (c 159, r 120) south-west to the south edge (c 110, r 159); fountain houses (the
  south-east one in the Agora, one in Kydathenaion at c 88, r 50), wells in courtyards; the
  Klepsydra spring on the north-west slope (c 62, r 74).
- **City wall** (mudbrick on a stone base, towers every 6–8 tiles): Dipylon (c 8..14, r 6..12) →
  east along r 6..8 to c 100 → curve to c 146, r 22 → south along c 144..146 to r 110 (Diochares
  gate at c 144..146, r 58..62) → south-west to the Itonian gate near the Ilissos (c 126..130,
  r 128..132) → west along r 136..140 to c 52 → north-west over the Mouseion's west shoulder to the
  Melitides gate (c 26..30, r 106..110) and the junction with the Long Walls (c 8..20, r 104..110)
  → north along the west hills (c 2..4, r 30..104) with the Piraeus gate (c 2..4, r 64..68) → the
  Sacred Gate (c 2..6, r 14..18) → Dipylon. The real wall reused grave stelae in its foundations
  (Thucydides 1.93); show a few carved fragments in the base course near the Kerameikos.
- **Long Walls**: two parallel walls 8 tiles apart from the city wall (c 8..20, r 104..110) running
  south-west to Piraeus (c 4..30, r 131..132); road and carts between.

### 2.6 Elevation

Local levels; world level = 1 + local.

| Area | Level | Notes |
|---|---|---|
| Agora, Kerameikos, houses | 0 | |
| Kolonos Agoraios | 2 | stone steps up from the Agora |
| Eleusinion terrace | 2 | |
| Areopagus | 5 | rock-cut steps on its south-east side |
| Pnyx | 4 (bema) → 6 (top) | audience on the slope |
| Hill of the Nymphs | 6 | |
| Mouseion | 8 | |
| Acropolis slopes | 2–9 | `rock` edge material; vertical cliffs on north and south; the theatre and Odeion are cut into the south slope (cavea 0 → 6) |
| Acropolis plateau | 10 | `rock` with `ashlar` patches where the Periclean walls (the Kimonian south wall) face the cliff |
| Nike bastion | 9 | |
| Pentelikon quarry | 6–9 | |
| Piraeus | 0–2 | Mounychia hill 4 |

Stairs and ramps: `approach` (rise 9 + steps), Kolonos steps (rise 2), Areopagus steps (rise 5),
Pnyx path (rise 4), Peripatos ramps, quarry road (rise 6 over 30 tiles).

---

## 3. Asset list

Legend: **M** must-have, **N** nice-to-have. Heights in px at 64 × 32. One rotation per landmark
in the fixed view; four if the optional view rotation is built. Layers: B base, S shadow, G glow.

### 3.1 Architectural facts every artist must get right (Athens 432)

- **Material:** Pentelic marble (fine, white with a faint warm tone; weathers golden) for the
  Parthenon, Propylaia and Hephaisteion; grey Eleusinian limestone for accents (the Propylaia's dark
  course); poros limestone for older buildings and foundations; mudbrick on stone footings for
  houses and the city wall; terracotta roof tiles (Laconian or Corinthian type) on houses, marble
  tiles on the Parthenon.
- **Doric order** (Parthenon, Propylaia, Hephaisteion, stoa fronts): no column base, fluted shaft
  (20 flutes) with swelling (entasis), cushion capital (echinus) and square abacus; plain
  architrave; frieze of **triglyphs and metopes**; cornice; pediment. The Parthenon is **8 × 17
  columns** (46 outer columns) on a three-stepped base; inside, six-column porches at both ends
  and a continuous **Ionic frieze** around the cella (the procession).
- **Ionic order** (inside the Propylaia's central passage, the Parthenon's west room, the Stoa
  Poikile interior): moulded base, 24 flutes, volute capital.
- **Colour (temples were painted):** triglyphs dark blue-black, mouldings with red, blue and green
  egg-and-dart and meander; metope and frieze backgrounds blue (or red); sculptures painted (skin,
  hair, garments with patterned borders) with bronze attachments (spears, reins, wreaths) and
  gilding; acroteria and antefixes painted. Marble walls and columns left marble-coloured, perhaps
  toned with a wax/ochre wash. Never draw pure white temples.
- **Parthenon sculpture:** 92 metopes (east: gods vs. giants; west: Greeks vs. Amazons; north: the
  sack of Troy; south: Lapiths vs. centaurs); the frieze (the procession of horsemen, chariots,
  elders, musicians, water-carriers, animals for sacrifice, girls, gods seated, the folding of the
  robe); **west pediment** (in view): Athena and Poseidon contesting Attica, with chariots and
  Attic heroes; east pediment: the birth of Athena from Zeus's head.
- **Athena Parthenos** inside (seen through the east door at dawn when it opens; card): about
  11.5 m of gold and ivory on a wooden core, helmet with sphinx and pegasoi, Nike in her right hand,
  shield with the serpent at her side.
- **Propylaia:** a central gate-hall with a hexastyle Doric front to the west and east, a wide
  central ramp for animals and five doorways; the north-west wing (Pinakotheke, a picture gallery)
  and a truncated south-west wing; unfinished: **lifting bosses** left on many blocks, unfinished
  surfaces.
- **Houses:** courtyard houses, 1–2 storeys, mudbrick walls plastered and whitewashed or
  earth-coloured on stone footings, few small windows on the street, a single door, tiled roofs,
  an inner courtyard with an altar and a well or cistern, an andron (men's dining room) for
  symposia. No grand façades: Athenians said private houses were modest.

### 3.2 Landmarks

| Id | Name | Footprint | Height px | Layers | Anim | M/N | Look |
|---|---|---|---|---|---|---|---|
| `parthenon` | Parthenon | 17 × 8 | 190 | B,S,G | doors open at dawn, lamp glow inside at dusk | M | as §3.1: 8 × 17 Doric, three steps, painted frieze and metopes, west pediment figures, acroteria, marble roof tiles; columns 10.4 m (104 px) |
| `old_temple` | Old Temple (remains) | 11 × 6 | 45 | B,S | — | M | poros foundations, a repaired west chamber with a tiled roof (debated) |
| `pandroseion` | Pandroseion and olive | 4 × 4 | 60 | B,S | olive leaves shimmer | M | low wall, small stoa, the gnarled sacred olive |
| `promachos` | Athena (bronze) | 2 × 2 | 130 | B,S,G | spear-tip glint at noon | M | colossal standing Athena in helmet with shield and spear on a tall base, bronze with gilded details (height about 9 m: estimates vary) |
| `propylaia` | Propylaia | 10 × 11 | 140 | B,S | — | M | §3.1 |
| `nike_bastion` | Nike bastion | 4 × 5 | 40 (+bastion cliff) | B,S | — | M | poros bastion with a small old naiskos and an altar |
| `approach` | Approach ramp | 14 × 7 | ramp | B,S | — | M | broad gravel ramp with retaining walls |
| `brauronion` | Brauronion | 9 × 6 | 70 | B,S | — | N | |
| `chalkotheke` | Chalkotheke | 7 × 4 | 60 | B,S | — | N | |
| `great_altar` | Great Altar | 3 × 3 | 30 | B,S,G | fire on festival days | M | |
| `zeus_polieus` | Zeus Polieus | 5 × 5 | 40 | B,S | — | N | |
| `sculpt_yard` | Sculptors' yard | 9 × 11 | 100 | B,S | crane swing, dust | M | blocks, a crane (two-legged with a winch), scaffolds |
| `hephaisteion` | Hephaisteion | 8 × 4 | 100 | B,S,G | — | M | Doric, **6 × 13 columns**, Pentelic marble, sculptured metopes of Herakles and Theseus on the east front and the first metopes of the long sides |
| `royal_stoa` | Royal Stoa | 2 × 5 | 60 | B,S | — | M | small Doric stoa, terracotta acroteria, law boards and inscribed stones in front |
| `stoa_zeus` | Stoa of Zeus (site) | 4 × 11 | 50 | B,S | — | N | foundations, column drums, scaffolding |
| `old_bouleuterion` | Old Bouleuterion | 6 × 6 | 70 | B,S,G | — | M | square hall, tiled roof, benches inside |
| `tholos` | Tholos | 5 × 5 | 80 | B,S,G | kitchen smoke | M | round building, conical roof with lozenge-shaped tiles, a small kitchen annex; the 50 prytaneis eat and some sleep here |
| `stoa_poikile` | Stoa Poikile | 10 × 3 | 70 | B,S,G | — | M | long Doric colonnade, Ionic inside; on the back wall large painted wooden panels: Marathon, the Amazons, the fall of Troy, Oinoe; captured shields hanging |
| `twelve_gods` | Altar of the Twelve Gods | 2 × 2 | 20 | B,S | — | M | |
| `tyrannicides` | Tyrannicides | 2 × 2 | 60 | B,S | — | M | two striding bronze men, one bearded, one young, swords raised |
| `se_fountain` | SE fountain house | 4 × 4 | 50 | B,S | water spouts | M | Doric porch, spouts shaped as lion heads, basin |
| `lawcourt` | Law court enclosure | 7 × 6 | 30 | B,S | — | N | |
| `horos` | Boundary stone | 1 × 1 | 18 | B | — | M | inscribed marble post |
| `simon_shop` | Simon's shop | 3 × 2 | 50 | B,S,G | — | N | small house, workbench at the door |
| `eleusinion` | Eleusinion | 5 × 5 | 60 | B,S | — | N | walled sanctuary, small temple |
| `dipylon` | Dipylon | 7 × 7 | 110 | B,S,G | torches | M | two gate towers and an inner court, mudbrick on stone |
| `sacred_gate` | Sacred Gate | 5 × 5 | 90 | B,S | stream | M | the Eridanos flows through a channel beside the road |
| `pnyx` | Pnyx | 17 × 15 | 30 | B,S | — | M | natural rocky slope, a low retaining wall, a rock-cut bema with steps |
| `meton_dial` | Meton's sundial | 2 × 2 | 20 | B | shadow moves | N | |
| `theatre` | Theatre of Dionysos | 15 × 17 | 80 | B,S | — | M | **wooden bleacher seating (ikria)** on the slope, a round earth orchestra with an altar, a simple wooden stage building (skene) with painted panels |
| `dionysos_temple` | Old temple of Dionysos | 7 × 4 | 60 | B,S | — | N | small poros temple |
| `odeion` | Odeion of Pericles | 13 × 14 | 150 | B,S | — | M | a square hall with rows of interior columns under a **pyramidal roof** (Plutarch says it imitated the Persian king's tent) |
| `olympieion` | Olympieion foundations | 19 × 11 | 40 | B,S | — | N | vast abandoned platform, a few column drums lying in grass |
| `kallirrhoe` | Kallirrhoe spring | 3 × 3 | 20 | B | water | N | |
| `lyceum` | Lyceum | 12 × 17 | 40 | B,S | — | N | running track, plane grove, a small shrine of Apollo Lykeios |
| `piraeus_shipsheds` | Ship sheds of Zea | 16 × 6 | 70 | B,S | — | M | long rows of narrow roofed slipways sloping into the water, each holding a trireme (the naval inventories list 196 sheds at Zea in 330/29, later than our date) |
| `piraeus_harbour` | Kantharos harbour and emporion | 18 × 10 | 60 | B,S,G | — | M | quays, the long emporion stoas for merchants, moles with towers narrowing the harbour mouth |
| `piraeus_grid` | Hippodamian street grid (houses) | kit | — | — | — | M | straight streets at right angles, laid out by Hippodamos of Miletus |
| `pentelikon_quarry` | Pentelikon quarry | 20 × 19 | 120 | B,S | dust | M | bright white-gold stepped cut faces, wedge slots, a sledge ramp |

### 3.3 Kit: buildings, structures, props

| Id | Name | Footprint | Height px | Rot | Layers | Anim | M/N | Look |
|---|---|---|---|---|---|---|---|---|
| `g_house` | Courtyard house | 3 × 3 | 70 | 4 | B,S,G | — | M | §3.1; door lamp (G) |
| `g_house_small` | Small house / workshop-house | 2 × 2 | 60 | 4 | B,S,G | — | M | |
| `g_house_two` | Two-storey house | 3 × 2 | 85 | 4 | B,S,G | — | N | upper room with small balcony |
| `g_herm` | Herm | 1 × 1 | 36 | 4 | B | — | M | square pillar with a bearded head of Hermes and a phallus (as on real herms), at doorways and crossroads |
| `g_shrine` | Small shrine / altar | 1 × 1 | 30 | 2 | B,S,G | — | M | |
| `g_stall` | Market stall | 2 × 1 | 40 | 4 | B,S | awning flap | M | wooden trestle, wicker screens, goods by trade (variants: pottery, fish, garlands, figs and cheese, perfume, sandals) |
| `g_table_banker` | Money-changer's table | 1 × 1 | 20 | 2 | B | — | M | the *trapeza* with coins and scales |
| `g_kiln` | Potter's kiln | 1 × 1 | 45 | 1 | B,S,G | smoke, glow | M | domed updraught kiln |
| `g_wheel` | Potter's wheel | 1 × 1 | 16 | 2 | B | spin | M | heavy wheel turned by an assistant |
| `g_pots` | Pots drying, stacked amphorae | 1 × 1 | 24 | 2 | B | — | M | black-gloss and red-figure pots, transport amphorae |
| `g_forge` | Bronze smithy hearth | 1 × 1 | 35 | 2 | B,S,G | fire | M | |
| `g_loom` | Warp-weighted loom | 1 × 1 | 44 | 2 | B | — | M | upright, clay loom weights hanging |
| `g_press` | Olive press (beam press) | 2 × 1 | 50 | 2 | B,S | — | M | |
| `g_threshing` | Threshing floor | 3 × 3 | 4 | 1 | B | — | M | |
| `g_well` | Well head | 1 × 1 | 22 | 1 | B | — | M | |
| `g_grave_stele` | Grave stele and lekythos | 1 × 1 | 32 | 2 | B,S | — | M | painted relief stele; white-ground lekythos vases at graves |
| `g_grave_mound` | Grave mound | 2 × 2 | 24 | 1 | B | — | N | |
| `g_statue_base` | Statue on base (generic dedication) | 1 × 1 | 50 | 4 | B,S | — | M | |
| `g_stele_inscr` | Inscribed stele | 1 × 1 | 34 | 2 | B | — | M | decrees, tribute lists, building accounts: tall marble slab with fine letters (illegible at this size) |
| `g_crane` | Crane | 2 × 1 | 110 | 2 | B,S | swing | M | |
| `g_scaffold` | Scaffold | 1 × 1 | 60–110 | 1 | B,S | — | M | |
| `g_cart` | Ox cart with marble block | 2 × 1 | 36 | 4 | B,S | wheels | M | solid or spoked wheels, team of oxen |
| `g_brazier` | Brazier, torch | 1 × 1 | 26 | 2 | B,G | fire | M | |
| `g_lamp` | Oil lamp in niche | 1 × 1 | 8 | 4 | G | flicker | M | |
| `g_couch` | Dining couch and low table (andron) | 2 × 1 | 22 | 4 | B | — | N | |
| `g_trireme` | Trireme | 6 × 2 | 70 | 4 | B,S | oars | M | about 37 m long (`s ≈ 0.5`), three banks of oars (170 rowers), bronze ram, eyes painted on the bow, square sail and mast lowered in battle |
| `g_merchant` | Greek merchant ship | 4 × 2 | 80 | 4 | B,S | sail | M | round-hulled, single square sail, steering oars |
| `g_fishing` | Fishing boat | 2 × 1 | 30 | 4 | B | — | M | |
| `g_wall` | City wall straight / tower / gate | 1 × 1 / 2 × 2 | 70 / 100 | connect | B,S,G | torch | M | mudbrick on stone, whitewashed plaster, tiled tops on towers |
| `g_long_wall` | Long Wall segment | 1 × 1 | 60 | connect | B,S | — | M | |
| `g_running_track` | Gymnasium track markers | 1 × 1 | 6 | 2 | B | — | N | |

### 3.4 Plants

| Id | Name | Height px | Anim | M/N | Note |
|---|---|---|---|---|---|
| `t_olive` | Olive | 60 | silver shimmer | M | the tree of Athena; groves everywhere outside the walls, sacred olives (*moriai*) in the Academy |
| `t_plane` | Oriental plane | 110 | sway | M | Kimon planted planes in the Agora (Plutarch); also by the Ilissos |
| `t_cypress` | Cypress | 100 | sway | M | sanctuaries, cemeteries |
| `t_pine` | Aleppo pine | 90 | sway | M | hills, resin smell |
| `t_fig` | Fig | 55 | — | M | courtyards; Attic figs were famous |
| `t_vine` | Vine (low bush and pergola) | 30 | — | M | |
| `t_poplar` | White poplar | 100 | shimmer | N | Academy, Ilissos |
| `t_agnus` | Chaste tree (agnus castus) | 35 | — | N | by the Ilissos (the setting of Plato's *Phaedrus*) |
| `t_oleander` | Oleander | 30 | — | M | stream banks |
| `t_myrtle` | Myrtle | 25 | — | M | |
| `p_thyme` | Thyme and phrygana scrub | 8 | — | M | rocky hills, Hymettos honey |
| `p_barley` | Barley (stubble in summer) | 6 | — | M | harvested by July: golden stubble |
| `p_acanthus` | Acanthus | 12 | — | N | |
| `p_reeds` | Reeds | 30 | sway | M | |
| `p_asphodel` | Dry grass and asphodel stalks | 10 | — | M | summer-dry |

### 3.5 Terrain

`dry_grass` (base, summer gold-green), `rock_limestone` (Acropolis, hills), `marble_paving` (temple
platforms), `gravel` (Panathenaic Way, Agora), `packed_earth` (lanes), `field_stubble`, `olive_soil`
(red-brown under groves), `riverbed` (Ilissos, dry stones with a thin stream), `sand` (beach at
Phaleron, Piraeus shores), `sea` (shared).

### 3.6 Walkers and animals

| Kind | Variants | Anim | M/N |
|---|---|---|---|
| Citizen man in himation | 4 | walk, talk, sit | M |
| Old man with staff | 2 | walk, sit | M |
| Young man in chlamys and petasos | 3 | walk, ride | M |
| Citizen woman with veil (himation over the head) | 4 | walk, carry hydria | M |
| Working woman (seller, wool-worker) | 3 | sell, spin | M |
| Girl / boy | 4 | run, play knucklebones | M |
| Enslaved worker in exomis | 4 | carry, work | M |
| Enslaved woman (nurse, water carrier) | 3 | carry baby, carry hydria | M |
| Scythian archer (public slave, police) | 2 | stand, herd with red rope | M |
| Metic trader | 3 | walk, haggle | M |
| Hoplite | 3 | march, stand | M |
| Rower / sailor | 3 | row, haul rope | M |
| Potter, painter, smith, mason, sculptor | 2 each | loop actions (§6.3) | M |
| Farmer, shepherd, goatherd | 3 | hoe, herd | M |
| Priest / priestess | 2 | pray, pour | M |
| Philosopher / talker | 2 | walk, gesture | M |
| Athlete (nude, oiled) | 2 | run, wrestle, scrape with strigil | M |
| Aulos player, kithara player | 2 | play | M |
| Animals: donkey, mule, ox, horse, sheep, goats, dog (Laconian and Molossian types), pig, chickens and a rooster, owl (Athena's bird, common on the rock) | — | walk, idle | M (donkey, ox, horse, goats, dog, owl) |
| Birds and insects: swallows, swifts, sparrows, kestrels over the rock, gulls at Piraeus, cicadas (sound), bees by the thyme | — | — | M |

**Asset counts (Athens region):** landmarks 39 (M 26 / N 13), kit 31 (M 26 / N 5), plants 15
(M 11 / N 4), terrain 10 (M), walker kinds 19 (M), animals 10 (M 6 / N 4).

### 3.7 Greek-time waypoints outside the region

World coordinates (`world.md` §5–6). Same moment (summer 432 BC), Athens kit; unique landmarks at
`s ≈ 0.5`.

| Waypoint (world rect) | Landmark id | Footprint | Height px | M/N | Look (what must be right) |
|---|---|---|---|---|---|
| **Eleusis** (C 556..575, R 222..250; the Sacred Way arrives from Athens' Sacred Gate) | `telesterion` | 10 × 10 | 90 | M | the square hall of the Mysteries, rows of interior columns, stepped seating along the walls; Iktinos's Periclean rebuilding was under way (its progress in 432 is uncertain: show walls up, roof unfinished); sanctuary wall, the Kallichoron well |
| **Academy** (C 560..575, R 205..219) | `academy_grove` | 12 × 10 | 40 | N | gymnasium in a grove of sacred olives (*moriai*) and planes, a running track, an altar of Prometheus (start of torch races) |
| **Corinth** (C 553..575, R 280..305) | `corinth_apollo` | 6 × 12 | 90 | M | archaic Doric temple of Apollo (c. 540), stocky monolithic columns, 6 × 15 |
| | `acrocorinth` | 10 × 10 | 200 | M | the steep citadel mountain with a small temple of Aphrodite on top |
| | `diolkos` | 2 × 20 | 4 | M | the paved ship-trackway across the isthmus, a ship on a wheeled cradle hauled by men and oxen |
| | `lechaion_kenchreai` | kit | — | M | two small harbours on the two seas |
| **Delphi** (C 500..519, R 250..265) | `delphi_apollo` | 6 × 12 | 100 | M | Doric temple of Apollo (the Alkmaeonid temple, late 6th century, with a marble east front) on a terrace against cliffs (the Phaedriades) |
| | `athenian_treasury` | 2 × 3 | 50 | M | small Doric treasury with two columns between antae, Pentelic marble, metopes of Herakles and Theseus |
| | `serpent_column` | 1 × 1 | 70 | N | bronze column of three intertwined snakes that carried the gold tripod for Plataea (479) |
| | `castalian_spring` | 2 × 2 | 20 | N | rock-cut fountain |
| **Olympia** (C 470..491, R 320..340) | `olympia_zeus` | 7 × 15 | 110 | N | Doric temple of Zeus (finished c. 456), 6 × 13, with pediments of the chariot race of Pelops and the Lapiths and centaurs |
| | `pheidias_workshop` | 4 × 8 | 90 | N | a tall hall the same size as the temple cella, where the gold and ivory Zeus was made (its date, 430s, is debated) |
| | `olympia_stadium` | 4 × 20 | 10 | N | earth banks, stone start lines |
| **Sparta** (C 515..535, R 360..385) | `sparta_villages` | kit | — | N | four or five villages of plain houses by the Eurotas, the small acropolis with the sanctuary of Athena of the Bronze House, the sanctuary of Artemis Orthia; **no city wall** |
| **Corcyra** (C 440..455, R 200..225) | `corcyra_harbour` | kit | — | N | harbour with Corcyraean triremes (allied to Athens since 433) |
| **Delos** (C 775..790, R 330..345) | `naxian_lions` | 8 × 2 | 40 | M | row of marble lions (7th century) facing the sacred lake |
| | `delos_sanctuary` | 10 × 8 | 70 | M | temples of Apollo (the older poros temple; the large marble temple begun after 478 is unfinished), the sacred lake, the Artemision; the Delian League's treasury had moved to Athens in 454 |
| **Ephesus** (C 832..851, R 235..255) | `artemision` | 8 × 16 | 150 | M | the archaic temple of Artemis (begun c. 560), a huge Ionic dipteral temple with a double ring of columns, some with carved lower drums given by King Croesus of Lydia |
| | `ephesus_harbour` | kit | — | M | harbour, Ionian merchant ships |

**Asset counts (Athens with waypoints):** region landmarks 39 (M 27 / N 12) + waypoint landmarks
19 (M 11 / N 8) = 58; kit 31 (M 26 / N 5); plants 15 (M 11 / N 4); terrain 10 (M); walker kinds
19 (M); animals 10 (M 6 / N 4). **About 143 entries: must-have about 110, nice-to-have about 33.**

---

## 4. Figures

### 4.1 Heroes and notables

| # | Figure | Dates | Presence | Who they were | How to recognise | Where / what they do | M/N |
|---|---|---|---|---|---|---|---|
| 1 | **Pericles** (Περικλῆς) | c. 495–429 BC | present | General (*strategos*) re-elected year after year, the leading politician of democratic Athens and driving force of the building programme. | tall, dignified, grey beard, fine himation in deep blue; bronze Corinthian helmet pushed up on his head (as in his portrait type, which hid an unusually long head, Plutarch) | Pnyx on assembly days; Agora and Acropolis yard; at dusk with Aspasia at their house | M |
| 2 | **Aspasia** (Ἀσπασία) | c. 470–after 428 BC | present | From Miletus, a metic; Pericles's companion and mother of his son; famous for her conversation and intelligence (Plato, Xenophon, Plutarch); comic poets attacked her. | woman in a fine saffron chiton and patterned himation over her hair, earrings | their house in Kydathenaion; receives guests in the courtyard | M |
| 3 | **Socrates** (Σωκράτης) | 469–399 BC | present (aged 37) | Stonemason's son and philosopher, who wrote nothing and questioned everyone. He served as a hoplite (at Potidaea from 432). | snub nose, bald crown, bushy beard, **barefoot**, a worn coarse cloak (*tribon*) | walks the Agora and stoas asking questions; sits at Simon's shop; by the Ilissos under the plane tree | M |
| 4 | **Sophocles** (Σοφοκλῆς) | c. 497–406 BC | present | Tragic poet (the *Antigone* c. 441), general alongside Pericles in 441/440, priest of a healing hero. | elder with a fine white himation, wreath, staff | theatre, rehearsing a chorus; the Agora | M |
| 5 | **Euripides** (Εὐριπίδης) | c. 480–406 BC | present | Tragic poet; the *Medea* will be staged in spring 431. Tradition says he liked solitude and books. | thin, long beard, scroll | rehearses the *Medea* chorus in the theatre; reads on a bench in the Stoa | M |
| 6 | **Pheidias** (Φειδίας) | c. 490–430 BC | present (disputed) | Sculptor of the Athena Parthenos and the bronze Athena, overseer of the Parthenon's sculpture. He was accused of stealing gold or ivory, probably in 438 or 432, and worked at Olympia on the Zeus; whether he is in Athens in 432 is uncertain. | workman's short chiton, leather apron, a chisel and a small wax model | the sculptors' yard east of the Parthenon, first week of the game day; card states the uncertainty | M |
| 7 | **Mnesikles** (Μνησικλῆς) | fl. 437–432 BC | present | Architect of the Propylaia, whose work is being stopped. | himation, a measuring rod and a wax tablet | at the Propylaia, gazing at the unfinished bosses | N |
| 8 | **Protagoras** (Πρωταγόρας) | c. 490–420 BC | present (visiting) | The great sophist from Abdera, teacher for fees; "man is the measure of all things". Plato sets a famous dialogue with him in Athens around 433/432 at the house of the rich Kallias. | elegant travelling cloak, followers trailing behind him | walks in a courtyard with a crowd of pupils, turning about together (as Plato describes) | N |
| 9 | **Meton** (Μέτων) | fl. 432 BC | present | Astronomer who observed the summer solstice of 432 BC in Athens and proposed the 19-year lunisolar cycle. | himation, a rod, a sundial | Pnyx, at his sundial at dawn | N |
| 10 | **Alcibiades** (Ἀλκιβιάδης) | c. 450–404 BC | present (aged about 18) | Pericles's ward, rich, handsome and reckless; soon to serve at Potidaea, where Socrates saves his life. | youth in a purple chlamys, long hair, riding a horse | rides in the Panathenaic procession with the cavalry | N |
| 11 | **Solon** (Σόλων) | c. 640–560 BC | memory | Lawgiver and poet who cancelled debts and wrote laws that Athenians still displayed on wooden boards and stone in the Royal Stoa. | translucent old man in an archaic himation | appears at dusk in front of the Royal Stoa | M |
| 12 | **Harmodios and Aristogeiton** | d. 514 BC | statue | Killed the tyrant's brother in 514; honoured as liberators with a bronze group in the Agora (the Persians took the first group in 480; this one is by Kritios and Nesiotes, 477/6). | the bronze statue group | the Agora (clickable) | M |
| 13 | **Themistocles** (Θεμιστοκλῆς) | c. 524–459 BC | memory | Built the fleet and fortified Piraeus, victor at Salamis; later ostracised, he died in Persian service in Magnesia. | translucent, a general's cloak | dusk on a mole of Piraeus looking toward Salamis | N |
| 14 | **Athena** (Ἀθηνᾶ) | goddess | shrine | Virgin goddess of the city, of crafts and of wisdom, who gave Athens the olive and won the land from Poseidon. Worshipped as Polias (the old olive-wood statue), Parthenos (the gold and ivory statue) and Promachos. | the three statues, the olive, the owl; at the end of the procession, a faint apparition of the goddess in helmet and aegis above the Parthenon's west pediment | Acropolis | M |
| 15 | **Poseidon** (Ποσειδῶν) | god | shrine | God of the sea who struck the rock with his trident and made a salt spring, losing the contest for Attica to Athena; honoured with Erechtheus on the rock. | trident marks in the rock near the Old Temple; the west pediment | Acropolis; Piraeus shrine | N |
| 16 | **Theseus** (Θησεύς) | hero | shrine + reenactor | The hero-king who killed the Minotaur and united the villages of Attica into one city; Kimon brought his bones home around 475. | a youth with a club in the Hephaisteion metopes; a festival reenactor with a club and a lion-skin-free short cloak | Hephaisteion (card); Agora in the procession | M |
| 17 | **Achilles and Odysseus (in the rhapsode's song)** | heroes | reenactor | At the Panathenaia, rhapsodes recited Homer by law, in order. | a rhapsode in an ornate robe with a staff; as he sings, faint silhouettes of the heroes appear | Agora stage on festival afternoons | N |
| 18 | **Herakles** (Ἡρακλῆς) | hero | statue | Son of Zeus, the strongest hero, with labours carved on the Hephaisteion and the Athenian treasury at Delphi. | lion skin, club | Hephaisteion metopes (card) | N |

### 4.2 Ordinary people (named)

Names typical of 5th-century Athens; persons invented unless stated.

| Figure | Who | Where / routine | Card (40–60 words) |
|---|---|---|---|
| **Philinna**, wool-worker and mother | citizen woman of Kydathenaion | home loom at dawn → fountain → home | "Philinna spins wool before sunrise and weaves until noon. Her husband sits on the Council this year. She goes out for water, for festivals and to visit her sister. Her daughter will carry a basket in next year's procession." |
| **Mania**, nurse | enslaved, from Phrygia (Mania was a common name for Phrygian women in Athens) | carries Philinna's baby; fetches water | "Mania was born in Phrygia and sold at Ephesus as a girl. She has raised two of Philinna's children. Athenian grave stones sometimes honour nurses like her by name, kindly. She hums Phrygian songs to the baby." |
| **Manes**, kiln-man | enslaved, Phrygian, works in a potter's workshop | Kerameikos kiln | "Manes knows the kiln's moods: three firings, air in, air out, then in again, and red clay turns black where the painter's slip lies. He has saved some coins; some enslaved craftsmen in Athens worked on their own and paid their master a share." |
| **Kephalos**, shield-maker | historical metic from Syracuse, rich owner of a shield workshop in Piraeus (Lysias, Plato) | Piraeus workshop and house | "Kephalos came from Syracuse at Pericles's invitation and makes shields in Piraeus with more than a hundred workers. Metics like him pay a special tax, serve in the army and cannot own land, but Athens could not run without them." |
| **Sosias**, charcoal seller | citizen farmer from Acharnai | road from the north gate to the Agora | "Sosias walks from Acharnai with two donkeys of oak charcoal. He votes in the assembly when the harvest allows, and grumbles that the city folk talk too much. His charcoal feeds the potters' kilns and the smithies." |
| **Nikarete**, bread-seller | citizen widow | Agora stall | "Nikarete sells barley cakes and wheat loaves from a basket in the Agora. Bread-women had a reputation for sharp tongues. She has seen every general of the last thirty years buy her bread, and tells you so." |
| **Toxamis**, archer | Scythian, a public slave owned by the city | Agora, Pnyx | "Toxamis is one of the city's Scythian archers: public slaves who keep order in the assembly and the courts. On assembly mornings they sweep the Agora with a rope dyed red, and anyone marked with red paint loses their pay." |
| **Euphiletos**, farmer | citizen of a rural deme (name from a court speech of Lysias) | olive groves by the Ilissos | "Euphiletos tends olives and vines outside the walls and brings his oil to the city. In a war he would serve as a hoplite. Tonight he will sleep in the city to see the procession at dawn." |
| **Hegeso**, girl | a citizen's daughter (the name is from a famous grave stele) | home → festival | "Hegeso is eleven. Girls her age weave the new robe for Athena with the priestesses, and a few of good family carry baskets in the procession. She practises walking with a basket on her head, very straight." |
| **Simon**, shoemaker | citizen; a 5th-century house with a cup inscribed SIMONOS was found at the Agora's edge | his shop | "Simon makes sandals at the corner of the Agora. Ancient writers said Socrates often sat at his bench to talk with young men too young to enter the Agora. The hobnails and his cup were found by archaeologists." |

### 4.3 Hero cards (40–60 words)

| Figure | Title · epithet | Text |
|---|---|---|
| Pericles | **Περικλῆς** · First citizen | "Elected general year after year, Pericles persuaded the Athenians to rebuild the Acropolis with the allies' tribute. Thucydides wrote that Athens was in name a democracy but in fact ruled by its first man. This summer, Sparta's patience is running out." |
| Aspasia | **Ἀσπασία** · of Miletus | "A foreign woman of learning and wit, Pericles's partner. Socrates is said to have learned rhetoric from her. Comic poets mocked her; later writers admired her. As a metic, her son by Pericles needed a special vote to become a citizen." |
| Socrates | **Σωκράτης** · The questioner | "A stonemason's son who walks barefoot in all weather and asks people what courage, justice or beauty really are. He wrote nothing. Soon he will march to Potidaea as a hoplite." |
| Sophocles | **Σοφοκλῆς** · Tragic poet | "Winner of more drama contests than anyone, and general with Pericles in the war against Samos. His *Antigone* asks what a citizen owes to the city and to the gods." |
| Euripides | **Εὐριπίδης** · Tragic poet | "Restless, questioning, fond of books. Next spring he will stage the *Medea*, a woman's fury against the man who betrayed her. It will come third." |
| Pheidias | **Φειδίας** · Sculptor | "He made the gold and ivory Athena inside the Parthenon and directed its sculpture. Enemies of Pericles accused him of theft; ancient accounts disagree about when and what happened next. His Zeus at Olympia became a wonder of the world." |
| Mnesikles | **Μνησικλῆς** · Architect | "His gateway to the Acropolis turns a steep rock into a stately climb. This year the work stops, with the stone bosses for lifting still on the blocks. They are still there today." |
| Protagoras | **Πρωταγόρας** · Sophist | "'Man is the measure of all things.' The famous teacher from Abdera charges fees to train young men in argument. Plato imagined Socrates debating him here, at the house of Kallias." |
| Meton | **Μέτων** · Astronomer | "On the Pnyx this summer he marks the solstice and proposes a cycle of 19 years that brings the moon's months back into step with the sun's year." |
| Alcibiades | **Ἀλκιβιάδης** · Pericles's ward | "Eighteen, rich, beautiful and reckless, and adored by the city. At Potidaea, Socrates will save his life. Later he will betray Athens and return to it, twice." |
| Solon | **Σόλων** · Lawgiver (a memory) | "Long ago he freed Athenians enslaved for debt and wrote the laws still kept on revolving wooden boards. He wrote poems, too: 'I grow old, always learning many things.'" |
| Tyrannicides | **Harmodios and Aristogeiton** | "Athens honoured these two men who killed the tyrant's brother as the founders of its freedom. When the Persians carried off their statue in 480, the city simply made a new one." |
| Themistocles | **Θεμιστοκλῆς** · Founder of the fleet (a memory) | "He persuaded Athens to spend its silver on ships, won at Salamis and walled Piraeus. Ostracised, he ended his life as a Persian governor. His harbour still hums below him." |
| Athena | **Ἀθηνᾶ** · Polias, Parthenos, Promachos | "She won Attica from Poseidon by giving the olive. Every summer the Athenians bring her old olive-wood statue a new woven robe. The gold and ivory Athena in the Parthenon was a treasure as much as an image." |
| Poseidon | **Ποσειδῶν** · Earth-shaker | "He struck the rock with his trident and a salt spring rose, but the gods gave the land to Athena. Athenians still showed the marks, and honoured him beside the hero Erechtheus." |
| Theseus | **Θησεύς** · Founder-hero | "Slayer of the Minotaur, he joined the villages of Attica into a single city. Kimon found his bones on Skyros and brought them home in triumph." |
| Rhapsode | **The rhapsode** · Singer of Homer | "At the Panathenaia, singers recite the *Iliad* and *Odyssey* in turn, by law. Listen, and Achilles' anger and Odysseus' long road home rise in the dusk." |
| Herakles | **Ἡρακλῆς** · Hero of the labours | "Strongest of heroes, son of Zeus and a mortal woman. His labours fill the metopes of the Hephaisteion; the Athenians claimed he was the first to honour them as a god." |

---

## 5. Civilization: society in motion

About a quarter of a million people may have lived in Attica in 432 (estimates vary widely):
perhaps 40,000–50,000 adult male citizens, their families, perhaps 10,000–25,000 metics with
families, and a very large number of enslaved people (estimates from about 60,000 to over 100,000).
Ps.-Xenophon complained that in Athens you could not tell a slave or metic from a citizen by dress.

| Layer | Who you see | Share of walkers | Routine |
|---|---|---|---|
| Citizen men | farmers, craftsmen, traders, the rich, the old | 25 % | market in the morning, assembly or court on some days, gymnasium, symposium for the wealthy |
| Citizen women | wives, mothers, priestesses, poorer women who work outside (sellers, nurses, wool-workers) | 15 % | spinning and weaving at home, water at the fountain, festivals, funerals, visits; wealthy women go out less |
| Children | boys to school with a slave escort (*paidagogos*), girls at home learning to weave; children play everywhere | 10 % | |
| Enslaved people | domestic servants, nurses, craftsmen in workshops, porters, mine workers at Laurion (not shown, card only), public slaves (Scythian archers, coin testers, clerks) | 25 % | work alongside the free in workshops and fields; some live and work independently and pay their owner |
| Metics (resident foreigners) | traders, bankers, craftsmen, shield-makers, potters, physicians, Aspasia | 10 % | like citizens at work; pay the metic tax; serve in the army and fleet; carry trays in the procession |
| Soldiers and sailors | hoplites (citizens who can afford armour), rowers (poorer citizens, metics, some slaves) | 8 % | drill at the Lyceum; the fleet at Piraeus |
| Priests and priestesses | priestess of Athena Polias, priests of Zeus, Dionysos and many shrines | 2 % | sacrifices, festivals |
| Officials | councillors, prytaneis, archons, generals, heralds, secretaries | 3 % | Bouleuterion, Tholos, Royal Stoa |
| Visitors | allies bringing tribute, traders from Ionia, Thrace, Egypt, Phoenicia | 2 % | Piraeus, Agora |

---

## 6. Civilization: dress, work and how Athens was run

### 6.1 Evidence for dress

Parthenon frieze (horsemen, elders, girls, water-carriers, musicians, marshals); Attic red-figure
vase painting (daily life, women at fountains, workshops, symposia, school scenes, athletes); early
Classical sculpture (the Tyrannicides, the Peplos-wearing figures); white-ground lekythoi and the
first Classical grave stelae (from about 430); texts: Thucydides 1.6 (the older rich men had only
recently given up linen chitons and golden cicada hair-pins), Ps.-Xenophon's *Constitution of the
Athenians* 1.10, Aristophanes (Scythian archers, saffron robes, workmen's exomis), the Brauron
clothing inventories (4th century) for colours and patterns.

**Garments.** *Chiton*: a tunic of linen (Ionic, fine, many folds, sleeves formed by pinning) or
wool (Doric); *peplos*: a heavy wool rectangle folded over at the top (*apoptygma*), pinned at the
shoulders, open on one side; *himation*: the large wool mantle, wrapped round the body and over the
left shoulder (worn alone by men, over a chiton by women, drawn over the head in public by many
women); *chlamys*: a short cloak pinned at the right shoulder for riders, travellers and young men;
*exomis*: a short tunic pinned on one shoulder only, for workers and craftsmen; *tribon*: a cheap
coarse cloak; *petasos*: broad-brimmed felt or straw hat; *pilos*: conical felt cap (workers,
sailors, Hephaistos); *sakkos* and *sphendone*: women's hair bag and headband; *krepides* (strapped
boots-sandals), plain sandals, soft boots (*endromides*), barefoot at home.

### 6.2 Dress reference

| Kind of person | Garments | Fabric, colours, rules | Hair, beard | Headgear | Footwear | Jewellery | Carries | Draw at 16–24 px | Evidence |
|---|---|---|---|---|---|---|---|---|---|
| Citizen man | himation alone, or short chiton + himation | wool; off-white, brown, blue, red; patterned borders for the rich; no sumptuary law, purple expensive | short to medium hair, full beard | bare, petasos for travel | sandals | signet ring | walking stick (fashionable) | long mantle over one shoulder + beard + stick | frieze (elders), vases |
| Elderly man | long chiton and himation | sober colours | white beard | — | sandals | — | staff | stooped, white beard | frieze, vases |
| Young man (rider, before full citizenship) | chlamys pinned at the right shoulder, short chiton or nothing beneath | wool, bright (red, purple, ochre) | longer hair, beardless | petasos hanging on the back | boots | — | spears, a horse | short cloak flying + hat on the back | Parthenon frieze horsemen |
| Citizen woman | Ionic linen chiton + himation, often over the head outdoors; or a wool peplos | linen and wool; saffron, red, blue, violet, white, patterned borders; women wove the family's clothes | long hair bound up in a sakkos or ribbons | himation over the head | sandals or soft shoes | earrings, necklace, bracelets | hydria, basket, spindle, mirror at home | long dress + mantle over the head | vases, white lekythoi, stelae |
| Girl / kanephoros | peplos with overfold, belted | fine wool, bright for festivals | long hair, fillet | basket on the head (festival) | sandals | — | basket, ribbons | small figure in peplos with basket | Parthenon frieze (girls) |
| Boy | short chiton or naked when small | undyed wool | short hair | — | barefoot | amulet | writing tablet, lyre, hoop | — | school vase scenes |
| Enslaved man | exomis or short chiton; loincloth for heavy work | coarse undyed wool | often cropped hair (vases), beard or not | pilos | barefoot | — | loads, tools | exomis + cropped hair | vases, Ps.-Xenophon (no distinctive dress) |
| Enslaved woman | plain long chiton, belted, no mantle | undyed wool | **cropped hair** (common in vase paintings of servants) | — | barefoot | — | hydria, baby, basket | short hair + plain dress | vases, stelae (nurses) |
| Metic | as citizens of the same trade | — | — | — | — | — | — | indistinguishable at a glance, as the sources say | Ps.-Xenophon 1.10 |
| Scythian archer (public slave) | **trousers** and a long-sleeved tunic with zigzag or diamond patterns | dyed, patterned | beard | **tall pointed cap with flaps** | soft boots | — | bow in a gorytos (combined bow-case and quiver), red-dyed rope | pointed cap + trousers + bow case | vase paintings (late 6th–5th c.), Aristophanes |
| Hoplite | chiton; linen-and-leather corslet (or bronze); greaves; helmet; round shield | red, blue, ochre tunics; shield blazons varied (each man's own: a bull, a gorgon, a snake, a tripod) | beard | **pilos-type or Attic helmet** (open face, typical by the 430s) or Corinthian (older) | barefoot or sandals | — | spear (dory, about 2.5 m), short sword, round shield (aspis, about 90 cm) | round shield + spear + helmet | vases, sculpture |
| Cavalryman | chlamys, short chiton, boots | bright | — | petasos or helmet | boots | — | two javelins | rider + hat | frieze |
| Rower | loincloth or exomis | undyed | — | pilos | barefoot | — | an oar and a cushion | — | texts, reliefs |
| Potter, smith, mason | exomis or loincloth; leather apron for smiths | undyed | beard | pilos for smiths | barefoot | — | tools | exomis + tool | workshop vases |
| Farmer / shepherd | exomis, short cloak of goatskin or felt in cold | undyed wool | beard | petasos or pilos | boots or barefoot | — | hoe, crook | — | vases |
| Priestess of Athena Polias | long chiton and himation, fillet | fine wool, white or saffron | hair bound | fillet | sandals | — | **a large temple key** (priestesses are shown carrying it) | dress + big key | vases, stelae |
| Priest | long chiton to the feet, himation, fillet or wreath | white | long beard | wreath | sandals | — | sacrificial knife, phiale | long dress + wreath | frieze, vases |
| Philosopher (Socrates) | coarse tribon, nothing beneath | worn brown | bald crown, beard | — | **barefoot** | — | — | bare feet + worn cloak | Plato, Xenophon |
| Athlete | nude, oiled | — | short hair | — | — | — | strigil, oil flask (aryballos), jumping weights, discus | nude, holding strigil | vases |
| Musician (aulos or kithara player) | long decorated chiton for performers; aulos players wear a cheek strap (*phorbeia*) | bright patterned | — | wreath | sandals | — | double aulos or kithara | long robe + instrument | vases |
| Actor and chorus | long sleeved patterned robe, linen mask | bright | — | mask | soft boots | — | — | mask held in hand | vases (the Pronomos vase, c. 400) |
| Rhapsode | ornate himation | rich colour | beard | wreath | — | — | staff (*rhabdos*) | staff + wreath | vases |
| Thracian (soldier or worker) | patterned cloak (*zeira*), tunic | brightly patterned wool | beard | **fox-skin cap** with ear flaps | high boots | — | crescent-shaped wicker shield (pelta), javelins | fox cap + patterned cloak | vases |
| Spartan visitor | short red cloak, chiton | red | **long hair**, beard, no moustache (tradition) | — | — | — | staff | long hair + red cloak | texts (Xenophon), sculpture |
| Ionian merchant | Ionic linen chiton + himation | fine, bright | beard, perfumed hair | — | soft shoes | rings | goods | — | vases |
| Persian envoy (rare) | Median dress (see `persepolis.md` §6.2) | — | — | — | — | — | — | — | vases (Persian figures) |

**Common mistakes to avoid (Athens).** Everyone in white; white marble temples and statues. Togas
(Roman) on Greeks. Roman armour, plumed Roman helmets, rectangular shields. Corinthian helmets on
every hoplite (by the 430s open-faced pilos and Attic types were common). Red cloaks on Athenians
as if they were Spartans. Spartans fighting nude. Women never outdoors (they went to fountains,
festivals, funerals and markets). Columns of the wrong order (Parthenon outer columns are Doric,
not Ionic or Corinthian). Stone theatres in 432. The Erechtheion and the Nike temple in 432.
Coins with emperors. Bearded young riders (they are beardless on the frieze).

### 6.3 Occupations and work

| # | Job | Where | Tools and materials | Steps (looping actions) | Hours / season | Who | Product → next |
|---|---|---|---|---|---|---|---|
| 1 | Quarryman | `pentelikon_quarry` | iron points, wedges, mallets, levers | mark → cut channel → drive wedges → lever free | dawn to dusk, dry season | free and enslaved workers | block → **sledge** |
| 2 | Sledge and ox-cart driver | quarry road | sledges, carts, oxen, brakes | rope down slope → load cart → drive → unload | daytime | free | block → **sculptors' yard** |
| 3 | Mason | Acropolis, Stoa of Zeus site | crane, ropes, chisels, iron clamps, lead | hoist → set → clamp (pour lead) → dress | daytime | citizens, metics and slaves worked side by side at the same daily wage (Erechtheion accounts, later) | wall/column |
| 4 | Sculptor | sculptors' yard | point, claw chisel, rasp, drill, emery | rough out → claw → rasp → polish | daytime | specialists | figure → **painter** |
| 5 | Painter of sculpture and architecture | yard, on scaffolds | pigments (Egyptian blue, ochres, cinnabar), wax, brushes | mix → paint → wax → gild | daytime | specialists | finished temple |
| 6 | Bronze caster | smithies near the Agora (bronze-working pits found by the Hephaisteion) | clay moulds, crucible, bellows | pack mould → melt → pour → chase | daytime | metics and citizens | statues, cauldrons, armour |
| 7 | Clay digger | clay pits outside the Dipylon | spade, baskets | dig → carry → soak | morning | enslaved | clay → **potter** |
| 8 | Potter | Kerameikos workshops | wheel, levigated clay | wedge → throw → trim → attach handles | daytime | citizens, metics, slaves | pot → **painter** |
| 9 | Vase painter | Kerameikos | fine slip, brush, relief line tool | sketch → outline → fill background black → details | daytime | specialists; some signed their work | painted pot → **kiln** |
| 10 | Kiln master | Kerameikos kilns | kiln, fuel (charcoal, brushwood) | stack → fire (oxidise) → seal (reduce) → reopen | firing days | — | finished pottery → **stall, ship** |
| 11 | Charcoal seller | road from Acharnai → Agora | donkeys, sacks | load → walk → sell | morning | farmers | fuel → **kilns, smithies, homes** |
| 12 | Farmer (olives, vines, barley) | outside the walls | hoe, sickle, pruning knife | hoe → prune → harvest → carry | barley harvest May–June; vintage Sept; olives Nov–Jan | citizens with slaves | grain → **threshing floor**; grapes → **press**; olives → **press** |
| 13 | Thresher | threshing floor | animals, forks, winnowing basket | spread → drive → winnow → bag | early summer | farm households | grain → **home mill** |
| 14 | Grinder and baker | homes, bakeries | saddle quern, oven | grind → knead → bake → stack | dawn | women (free and enslaved) | bread → **home, Nikarete's stall** |
| 15 | Olive presser | farm press | beam press, mill | crush → pack baskets → press → decant | winter | farm households | oil → **amphorae → market, prize amphorae** |
| 16 | Wool-worker | homes | spindle, distaff, warp-weighted loom | card → spin → warp → weave | all day, all year | women of every class | cloth → **family, market** |
| 17 | Fuller and dyer | workshops by water | vats, fuller's earth, dyes | soak → tread → rinse → hang | daytime | men | finished cloth |
| 18 | Shoemaker | Simon's shop | awl, leather, hobnails | cut → stitch → nail → fit | daytime | citizens, metics | sandals |
| 19 | Shield-maker | Kephalos's workshop, Piraeus | wood, bronze sheet, leather | shape core → face with bronze → paint blazon → fit grip | daytime | metic owner, enslaved workers | shields → **hoplites** |
| 20 | Shipwright | Piraeus | adze, saw, mortise-and-tenon joints, pine and fir from Macedon and Thrace | lay keel → build shell → fit frames → pitch | daytime | free and enslaved | trireme → **ship sheds** |
| 21 | Rower | triremes | oar, cushion | board → row in time to the aulos → rest → beach | campaigns, training | poorer citizens, metics | the fleet |
| 22 | Merchant / ship-owner | Piraeus emporion | ship, amphorae, contracts | load → sail → unload → sell | sailing season (spring–autumn) | citizens, metics, foreigners | grain from the Black Sea and Egypt → **grain market** |
| 23 | Fishmonger | Agora stalls | knives, baskets | gut → display → haggle → sell | morning | citizens, metics | fish → **homes** |
| 24 | Money-changer / banker | tables in the Agora and Piraeus | scales, coins | test coin → weigh → change → record | daytime | metics, freedmen | — |
| 25 | Water carrier | fountain houses | hydria | queue → fill → lift on the head → walk home | dawn and evening | women, enslaved | water → **homes** |
| 26 | Councillor / prytanis | Bouleuterion, Tholos | — | debate → vote → dine in the Tholos → sleep (a third stay overnight) | daily | citizens over 30 by lot, one year | decrees → **assembly** |
| 27 | Juror | law courts | bronze or wood ticket, voting pebbles | queue → allot → listen → vote | court days | citizens over 30; paid 2 obols a day (Pericles's measure) | verdict |
| 28 | Herald | Agora, Pnyx | voice, staff | call → proclaim → call silence | assembly days | officials | announcements |
| 29 | Secretary / scribe | Bouleuterion, Royal Stoa | papyrus, whitened boards, wax tablets, stone for inscriptions | write → copy → post → file | daily | officials, public slaves | decrees → **stone-cutter** |
| 30 | Letter-cutter | workshops | chisels, stele | layout → cut letters → paint red | daytime | specialists | inscribed decree → **Acropolis** |
| 31 | Scythian archer | Agora, Pnyx, courts | bow, red rope | stand → sweep with rope → escort → stand | daytime | public slaves | order |
| 32 | Priestess | Acropolis | key, phiale, incense | open temple → pour libation → pray → close | dawn, festivals | citizen women from old families | worship |
| 33 | Teacher | small schools | wax tablets, scrolls, lyre | dictate → correct → recite → play | morning | citizens, metics | literate boys |
| 34 | Gymnastics trainer | Lyceum, Academy | rod, oil, sand | demonstrate → wrestle → correct → oil | afternoon | citizens | athletes, fit hoplites |
| 35 | Aulos player | symposia, sacrifices, the theatre, triremes | double aulos with phorbeia | tune → play → rest → play | evening and festivals | men and women (aulos-girls hired for symposia were often enslaved) | music |
| 36 | Physician | house-surgery (*iatreion*) | instruments, herbs | examine → bandage → mix → advise | daytime | citizens and metics; public physicians hired by the city | care |

**Visible chains.**
Pentelikon quarry → sledge → ox cart → sculptors' yard → painter → Parthenon;
clay pit → potter → painter → kiln → stall in the Agora / amphorae onto a ship at Piraeus;
olive grove → press → amphora → market (and prize amphorae of oil for Panathenaic victors);
Black Sea grain ship → Piraeus emporion → cart up the Long Walls → grain stall → home mill → bread;
charcoal from Acharnai → kilns and smithies;
tribute ship → Piraeus → treasury on the Acropolis (Hellenotamiai) → stone list of the sixtieth
for Athena.

### 6.4 How Athens is run

| Area | How it worked in 432 | Where visible |
|---|---|---|
| Assembly (*ekklesia*) | every adult male citizen may attend, speak and vote; perhaps 40 regular meetings a year (the number is known for the 4th century); votes by show of hands | Pnyx (event: assembly morning with Scythian archers sweeping the Agora with a red rope) |
| Council of 500 (*boule*) | 50 men from each of the ten tribes, chosen by lot for a year; prepares business; each tribe's 50 (the *prytaneis*) serve a tenth of the year and eat in the Tholos, a third sleeping there | Bouleuterion, Tholos |
| Magistrates | nine archons and many boards by lot; ten generals (*strategoi*) elected every year (Pericles) | Royal Stoa (the king archon), the generals' office (location uncertain) |
| Law courts | large juries of citizens over 30 (hundreds per case), paid 2 obols a day; trials in a day; water-clock timing speeches | law court enclosure, Heliaia (event) |
| Areopagus | council of ex-archons, by now mainly judging homicide | Areopagus rock |
| Ostracism | once a year the assembly may vote to exile one man for ten years by writing his name on potsherds (*ostraka*) | ostraka on the ground in the Agora (props, cards; no ostracism in 432) |
| Money and tribute | the allies' tribute (*phoros*), managed by the Hellenotamiai; a sixtieth dedicated to Athena and recorded on stone; silver from the state mines at Laurion; the rich pay for warships and choruses (liturgies) | tribute ships at Piraeus, the inscribed lists on the Acropolis, the treasury in the Parthenon's west room |
| Grain supply | imports from the Black Sea, Egypt and Sicily through Piraeus; protected by the fleet | grain ships, emporion |
| Water | fountain houses fed by channels, wells and cisterns in houses | fountains, women queueing |
| Public works | overseen by elected boards (*epistatai*) who published accounts on stone (the Parthenon accounts survive) | building yards; account stelai |
| Army and navy | Thucydides gives 13,000 hoplites in the field, 16,000 on the walls, 1,200 cavalry and 300 triremes in 431 | Lyceum drill; ship sheds; hoplites embarking for Potidaea (event) |
| Religion | the city funds and organises festivals; priesthoods held by old families or by lot | altars, festivals |
| Records | decrees and accounts inscribed on marble and set up on the Acropolis and in the Agora; papyrus and whitened boards for working documents | inscribed stelai |

### 6.5 How the civilization lived (what to show)

| Topic | Accurate details | Shown as |
|---|---|---|
| Food | barley cakes (*maza*) and wheat bread; olives, figs, grapes, cheese, onions, garlic, lentils, chickpeas; fish fresh and salted (anchovies, sprats, tuna); meat mostly at sacrifices; wine always mixed with water; Hymettos honey | stalls, home ovens, the sacrificial feast after the procession |
| Farming | olives, vines, barley (Attica's thin soil grew little wheat), figs; goats and sheep; threshing floors on hills | olive groves by the Ilissos, threshing floors, goatherds |
| Crafts | painted pottery (red-figure at its height), bronze, marble, textiles, shields, ships | Kerameikos, smithies, Piraeus |
| Trade goods by origin | grain (Black Sea, Egypt, Sicily), timber (Macedon, Thrace), papyrus and linen (Egypt), wine (Chios, Thasos, Lesbos), dates and fine flour (Phoenicia), ivory (Libya), cypress (Crete), carpets and cushions (Carthage), slaves (Thrace, Phrygia), silphium (Cyrene). The comic poet Hermippus listed such imports around 425. | market stall labels, ship cargoes |
| Money | silver coins of Athens: the tetradrachm with Athena's head and the owl ("owls"), drachmas and small obols (people carried small change in their mouths); weights and measures checked by officials | money-changer's table |
| Writing | papyrus scrolls, wax tablets, potsherds for notes and ostraka, inscriptions on stone | school, Bouleuterion, ostraka |
| Schooling | boys of families who can pay: letters and Homer (*grammatistes*), lyre and song (*kitharistes*), gymnastics (*paidotribes*); a slave escort; girls learn at home | school scene in Melite |
| Medicine | Hippocratic physicians; public physicians paid by the city; healing heroes; the cult of Asklepios arrives only in 420 | physician's house (N) |
| Law | §6.4 | law court event |
| Religion and festivals | sacrifices at altars, processions, libations; household gods (Zeus of the courtyard, Hestia of the hearth), herms at doors; the calendar in §6.8 | altars, herms, processions |
| Theatre | tragedy and comedy at the City Dionysia (spring) and the Lenaia (winter), choruses of citizens; wooden seats in 432 | rehearsals in the theatre (the Medea chorus) |
| Athletics | gymnasia (Academy, Lyceum), palaistrai, races, the Panathenaic games with prize amphorae of oil | athletes at the Lyceum; torch race event |
| Baths | simple public bath-houses with hip-baths existed; most washed at home or at fountains | a small bath-house (N) |
| Music and dance | aulos and lyre everywhere: sacrifices, symposia, choruses, the fleet's rowing rhythm | aulos player, choral dance |
| The symposium | men reclining on couches in the andron after dinner, wine mixed in a krater, songs, games (*kottabos*), hired musicians | through a courtyard door at night (N) |
| Death and burial | burial or cremation outside the walls along the roads, especially the Kerameikos; painted stelae, white-ground lekythoi with oil; the state funeral for the war dead (Pericles's famous oration will come in winter 431/30) | Kerameikos cemetery, grave stelae |

### 6.6 The land beyond the walls

| Element | Where | Plan coordinates | What it shows |
|---|---|---|---|
| Piraeus with ship sheds and triremes | satellite S1 | c 0..38, r 132..159 | the fleet, merchant ships, the emporion, Kephalos's shield workshop, Themistocles's memory |
| Long Walls | region | c 0..20, r 106..131 | road and carts between them |
| Pentelikon quarries | satellite S2 | c 136..159, r 0..24 | the start of the marble chain |
| Olive groves, vineyards, farms | region | Ilissos valley (D13); north outside the wall (c 30..136, r 0..5) | farm work |
| Lyceum gymnasium (hoplite and cavalry training) | region | c 148..159, r 50..66 | drill, races |
| Academy | waypoint | world C 560..575, R 205..219 | sacred olives, gymnasium, torch-race start |
| Eleusis | waypoint | world C 556..575, R 222..250 | the Mysteries sanctuary at the end of the Sacred Way |
| Laurion silver mines | card only | — | the source of the owls; mined mostly by enslaved workers in harsh conditions |
| Marathon, Salamis, Aegina | overview-map labels and cards | — | memory of the Persian Wars; Aegina offshore in the Saronic Gulf |

### 6.7 The League and the wider Greek world

- **The Delian League** (founded 478 against Persia, now an Athenian empire): around 150–180
  tribute-paying cities in five districts (Ionia, Hellespont, Thrace, Caria, the Islands); Chios
  and Lesbos still contribute ships instead of money. Tribute arrives in spring and is displayed in
  the theatre at the City Dionysia (Isocrates 8.82). In game: **tribute ships** at Piraeus, envoys
  in the Agora (Ionian dress), a card for the stone **tribute lists** on the Acropolis.
- **The wider Greek world** on the map: Sparta (rival; unwalled villages), Corinth (rival and
  trader; the diolkos), Megara (excluded from Athenian markets by the decree of 432: a lone Megarian
  trader is turned back at the Agora boundary, card), Delphi and Olympia (shared sanctuaries),
  Corcyra (new ally), Ionia (Ephesus), Thrace (timber, silver, slaves), the Black Sea (grain), Egypt
  (Naukratis: papyrus, linen, grain), Sicily and Italy (grain; the Athenian-led colony of Thurii,
  444/3).
- **Overview map labels** for the Greek-time stretch: Ἀθῆναι, Πειραιεύς, Ἐλευσίς, Κόρινθος, Δελφοί,
  Ὀλυμπία, Σπάρτη, Κέρκυρα, Δῆλος, Ἔφεσος, with English beneath.
- **Cards** per waypoint and per allied district (unlocked by visiting or by seeing their envoys).

### 6.8 A year in Athens (Attic calendar, months begin at the new moon; the year starts after the summer solstice)

| Month (approx.) | Festivals | Work |
|---|---|---|
| Hekatombaion (Jul–Aug) | **Panathenaia** (the game's moment), Kronia, Synoikia | threshing done, figs ripening |
| Metageitnion (Aug–Sept) | — | grapes ripen |
| Boedromion (Sept–Oct) | **Eleusinian Mysteries** (procession along the Sacred Way), Genesia (for the dead) | vintage |
| Pyanepsion (Oct–Nov) | Pyanepsia, Oschophoria, **Thesmophoria** (women only), Apatouria, Chalkeia (smiths) | ploughing and sowing |
| Maimakterion (Nov–Dec) | — | olive harvest begins |
| Poseideon (Dec–Jan) | Rural Dionysia in the demes, Haloa | olives, pressing |
| Gamelion (Jan–Feb) | Lenaia (comedy) | month of weddings |
| Anthesterion (Feb–Mar) | **Anthesteria** (new wine, children's festival with small jugs), Lesser Mysteries | pruning |
| Elaphebolion (Mar–Apr) | **City Dionysia** (tragedy, tribute displayed in the theatre) | sailing season opens |
| Mounichion (Apr–May) | Mounichia, festivals of Artemis | barley ripens |
| Thargelion (May–Jun) | Thargelia, Plynteria (washing Athena's statue) | barley harvest |
| Skirophorion (Jun–Jul) | Skira, Dipolieia (the ox-sacrifice), Arrephoria | threshing |

The game is set at the Panathenaia; other festivals can be enabled as rotating events.

### 6.9 A day in Athens (schedule for ambient scenes)

| Time | Scene |
|---|---|
| Pre-dawn | lamps in houses; bakers' fires; the priestess walks to the Old Temple; an owl on the rock |
| Dawn | women and enslaved girls at the fountain house; farmers enter by the gates with donkeys; Meton at his sundial; the Parthenon doors open and the gold of the statue glints |
| Morning | the Agora fills ("the full market"); on assembly days the archers sweep citizens up to the Pnyx with a red rope; courts sit; the Council meets; workshops roar; ships load at Piraeus |
| Midday | heat; cicadas loudest; shops close; people rest in the shade of stoas and planes |
| Afternoon | gymnasia at the Academy and Lyceum; Socrates in the Stoa; rehearsal in the theatre; sea breeze |
| Dusk | the prytaneis dine in the Tholos; sacrifice smoke; lamps; Hymettos violet; memories appear (Solon, Themistocles) |
| Night | symposia behind courtyard walls with aulos music; the watch on the walls; the torch race on festival nights; stars |

### 6.10 Knowledge and ideas (met as places, people and cards)

| Idea | How the visitor meets it |
|---|---|
| **Democracy** | the Pnyx assembly event, the Council in the Tholos, jurors and ostraka; card: "In 432, a few tens of thousands of men governed themselves directly. Women, slaves and foreigners could not vote; Athens's freedom rested partly on the tribute of others." |
| **Philosophy** | Socrates in the Agora, Protagoras in a courtyard; card on the shift from asking about nature to asking how to live |
| **Drama** | the theatre with rehearsals; cards for Sophocles and Euripides; a mask found in the theatre (journal) |
| **History** | a card on Herodotus (who read from his *Histories* in Athens, tradition says) and the young Thucydides |
| **Geometry and astronomy** | Meton's sundial; a card on the 19-year cycle |
| **Sculpture and architecture** | the sculptors' yard, Pheidias, Mnesikles; card on the Parthenon's subtle curves (the base rises 6–7 cm in the middle; columns lean inward) |
| **City planning** | Piraeus's grid by Hippodamos (card) |
| **Medicine** | the physician (card on Hippocratic observation) |

---

## 7. Ambient life and events

### 7.1 Walkers and routines

| Group | Count (day / night) | Path or zone | Routine |
|---|---|---|---|
| Market crowd | 30 / 4 | Agora | browse stalls, haggle, chat in the stoas |
| Women at the fountains | 8 / 0 | fountain houses | queue, fill, carry home (dawn and evening peaks) |
| Potters and kiln workers | 12 / 2 | Kerameikos | chain §6.3 |
| Marble chain | 14 / 0 | quarry → road → yard → Parthenon | chain §6.3 |
| Officials and councillors | 8 / 2 | Bouleuterion, Tholos, Royal Stoa | walk, debate, dine |
| Philosophers and pupils | 4 / 0 | Stoa Poikile, Agora, Ilissos | walk in a group, stop, gesture |
| Hoplites | 10 / 4 | Lyceum, gates, walls | drill; watch at night |
| Sailors, rowers, shipwrights | 16 / 4 | Piraeus | haul, row, caulk |
| Farmers and herders | 10 / 0 | outside the walls | hoe, herd goats, bring donkeys to market |
| Children | 10 / 0 | lanes, Agora edges | play knucklebones, spin tops, chase a hoop |
| Athletes | 6 / 0 | Lyceum | run, wrestle, scrape |
| Scythian archers | 4 / 2 | Agora, Pnyx | stand, patrol |
| Carts on the Long Walls road | 1 every 2 min | Piraeus ↔ city | grain, amphorae |

### 7.2 Timed events

| Event | Trigger | Route and cast | Effects |
|---|---|---|---|
| **Panathenaic procession** (M) | each in-game morning during the festival (default: on) | from the Dipylon at dawn, along the Panathenaic Way through the Agora, up the ramp, through the Propylaia to the Great Altar: marshals; kanephoroi (girls with baskets); water-carriers (hydriaphoroi); metics carrying trays of cakes (skaphephoroi) and their daughters with parasols and stools; elders with olive branches; musicians (aulos, kithara); sacrificial cattle and sheep; hoplites; cavalry; chariots; the new robe (peplos) for Athena Polias carried folded | hymn on aulos and kithara, crowd murmur, smoke from the Great Altar; then a sacrificial feast in the Kerameikos and Agora |
| Torch race (N) | festival night | relay of runners with torches from the Academy altar of Prometheus to the Acropolis | streaks of light in the dark city, cheering |
| Assembly morning (M) | every 15 in-game minutes in the morning, some days | archers sweep the Agora with the red rope; citizens climb the Pnyx; herald's call; a speech by Pericles; hands raised | crowd, herald |
| Law court (N) | morning | jurors queue, allotment, a trial with a water clock, voting with pebbles | murmurs |
| Rehearsal in the theatre (M) | afternoon | a chorus of 15 dances and sings with an aulos player; Euripides watches | aulos, choral voices (wordless) |
| Hoplites embarking for Potidaea (N) | once per in-game day | a column marches down the Long Walls to triremes at Piraeus | farewell, families waving |
| Tribute ship (N) | random | a merchantman unloads sealed jars of silver at Piraeus, escorted up to the city | |
| Meltemi afternoon (M) | weather | wind rises, olive leaves flip silver, sea whitecaps, dust | wind bed |
| Summer storm (N) | rare weather | dark clouds over Hymettos, a short heavy shower and thunder, steam rising off hot stone | thunder, rain |

### 7.3 Birds, insects, small life

Cicadas (dominant summer sound), swallows and swifts, house sparrows, little owls on the rock and
walls (Athena's owl, *Athene noctua*), kestrels around the cliffs, hooded crows, gulls and
shearwaters at Piraeus, bees on thyme, lizards on sunny walls, cats are rare (ferrets and snakes
kept mice down; cats appear only occasionally in Athenian art), dogs common.

---

## 8. Light, weather and season

**Season:** high summer: hot days (30–35 °C), dry, brilliant light, cloudless skies, a sea breeze
in the afternoon, warm nights. The hills are gold and grey-green; olive leaves silver.

| Time | Sky (top → horizon) | Grading target | Light character |
|---|---|---|---|
| Dawn | `#3a4a7a` → `#f0a878` → `#fbe3b8` | pink-gold on marble, cool lilac shadows | the Parthenon west front lights last (it faces west); the east doors catch the first sun |
| Day | `#3f7fd0` → `#8fc3ef` → `#f2f4f2` | very bright, warm, high contrast; marble near white-gold; shadows short and blue | heat shimmer over paving at noon; strong colour on painted friezes |
| Dusk | `#40305e` → `#d8784a` → `#f6c27a` | marble honey then rose; Hymettos violet; sea deep blue | the west pediment glows in the low sun (the best view of the day) |
| Night | `#0c1430` → `#1c2a52` | cool blue, warm lamplight | many stars, the Milky Way; lamps in houses; torches on the walls; altar embers |

- **Haze:** warm, light, toward the sea (south-west foreground band) and the far mountains
  (Parnes north, Hymettos east, drawn as backdrop where at the world's north edge).
- **Wind:** calm mornings; meltemi in the afternoon from the north-east.
- **Dust:** summer dust devils on the Agora gravel (small, rare).
- **Rain:** very rare in summer (one storm event).
- **What glows at night:** oil lamps in house doorways and windows, torches at gates and the
  Dipylon, the Tholos (prytaneis on duty), lamps in the Parthenon (dusk), altar embers, the torch
  race. Glow layers: `parthenon`, `promachos` (glint, day), `great_altar`, `old_bouleuterion`,
  `tholos`, `stoa_poikile`, `dipylon`, `g_house*`, `g_lamp`, `g_brazier`, `g_wall` torches,
  `piraeus_harbour`.

---

## 9. Sound and music direction

### 9.1 Ambience beds

| Bed | Content | Where |
|---|---|---|
| `amb/athens_day.ogg` | cicadas in waves, distant voices, a hammer on marble, goat bells, swallows | everywhere by day |
| `amb/athens_agora.ogg` | crowd murmur, bargaining, a herald far off, a donkey | Agora zone |
| `amb/athens_sea.ogg` | small waves, rigging, gulls, shouted orders, a rowing aulos rhythm far off | Piraeus |
| `amb/athens_rock.ogg` | wind over the Acropolis plateau, a kestrel, cicadas below | Acropolis |
| `amb/athens_night.ogg` | crickets, a dog, a distant symposium song and aulos, an owl | night |
| One-shots | aulos phrase, lyre strum, potter's wheel, kiln roar, owl hoot, cart wheels, the creak of a trireme | positional |

### 9.2 Music brief

**What is attested.** The instruments: the **aulos** (a pair of reed pipes played together, loud,
reedy, expressive, with a cheek strap; used at sacrifices, in the theatre, for rowing); the
**lyra** (tortoise-shell lyre, 7 strings, for school and song); the **kithara** (large wooden
concert lyre of professionals); the **barbitos** (long-armed lyre for symposia); the
**syrinx** (pan-pipes, shepherds); **krotala** (clappers), **tympanon** (frame drum, women's
rites). The theory: the *harmoniai* (Dorian, Phrygian, Lydian, Mixolydian and others) built from
tetrachords in diatonic, chromatic and enharmonic genera; rhythm follows poetic metre (dactylic
hexameter, iambic, choral metres). Almost no notated music survives from the 5th century (a
papyrus scrap of Euripides's *Orestes* chorus copied around 200 BC is the main exception); the
Delphic hymns are of 128 BC.

**Evocative choices (modern, stated).** Day: a kithara (or lyra) leading, aulos answering,
light frame drum and krotala on festival passages. Mode: a Dorian-type diatonic scale (E–D–C–B |
A–G–F–E descending in Greek terms), with phrases shaped by metre (long–short–short patterns).
No modern harmony beyond drones and parallel fourths and fifths; heterophony (two instruments
playing the same melody with small differences) rather than chords. Night: solo lyre or
barbitos, slower, a hint of the Lydian mode; a distant aulos.

| Piece | Tempo | Form | Mood | Synthesis notes |
|---|---|---|---|---|
| `music/athens_day.ogg` (about 3 min loop) | 92 bpm, metre in long–short–short (dactylic) phrases | kithara melody in a Dorian-type scale with a low drone; aulos enters in heterophony; a bright middle festival section with krotala and frame drum | luminous, proud, warm, a little wistful | kithara: plucked string with a wooden body and bright attack; aulos: double-reed model with strong breath and slight pitch bends, two pipes (melody and drone); small room reverb (courtyard) |
| `music/athens_night.ogg` (about 3 min loop) | free, about 60 bpm | solo barbitos (lower, darker lyre), occasional far aulos, cicadas faded to crickets | starlit, gentle, the city asleep | longer decays, close and dry |

Overview-map motif: a rising kithara figure E–A–B–E.

---

## 10. What the player does here

| Activity | What exactly | M/N |
|---|---|---|
| Wander and look | pan across the city, Piraeus, the quarry and the Greek waypoints | M |
| Cards and journal | every landmark and figure; journal sections: Landmarks (39 + 19 waypoints), People (18 heroes + 10 ordinary), Allies and visitors, Things found (12: an owl tetradrachm, an ostrakon, a juror's ticket, a theatre mask, a herm, a white-ground lekythos, a lifting boss, a kiln-fired cup with a painter's signature, a prize amphora, a strigil, a loom weight, a voting pebble) | M |
| Gentle tasks | 1. Follow the Panathenaic procession from the Dipylon to the altar. 2. Follow a block from Pentelikon to the Parthenon. 3. Find Socrates and hear three questions. 4. Watch a pot from clay to kiln to stall. 5. See the solstice with Meton at dawn. 6. Visit all Greek waypoints. Each gives a keepsake | M (1–4), N (5–6) |
| Decorate zone | a courtyard house and garden in Melite (c 34..44, r 66..76, 11 × 11) to furnish with olives, fig, vine pergola, herms, altar, loom, couches, pots | M |
| Keepsake for the corner | completing task 1 unlocks an olive tree and an owl-perch for the corner | N |
| Photo mode | as in the corner | M |

---

## 11. Uncertainties for a human to check

1. **The Old Temple of Athena after 480** (foundations only vs. a repaired rear part): we show a
   repaired western chamber.
2. **Pheidias's trial and whereabouts in 432** (438 or 432; Athens or Olympia).
3. **Athena Promachos height** (estimates 7–9 m or more).
4. **Stoa of Zeus and South Stoa I dates** (c. 430–420): shown as one building site (Stoa of Zeus),
   South Stoa I omitted.
5. **The law court enclosure** identification (Heliaia?) is debated.
6. **Telesterion at Eleusis in 432** (Iktinos's project; progress uncertain).
7. **Population figures** (all estimates).
8. **The Pnyx in phase I**: orientation as reconstructed (audience on the natural slope facing
   north toward the bema); details of the early bema are uncertain.
9. **Protagoras's visit** around 433/432 rests on the dramatic date of Plato's dialogue.
10. **Meeting count of the assembly**: about 40 a year is known for the 4th century; the 5th-century
    number is assumed similar.
11. **Lyceum and Academy positions** are compressed; the Academy is moved outside the region.
