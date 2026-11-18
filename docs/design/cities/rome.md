# Roma · April, AD 126

Design bible for the Rome region and the Roman-time stretches around it. Read `world.md` first
(scale, coordinates, camera, elevation, data model). Evidence: `sources.md` (section "Rome").

Names. Latin forms are used on cards with English beneath: Forum Romanum, Capitolium (the temple
of Iuppiter Optimus Maximus), Amphitheatrum Flavium (the Colosseum; the name "Colosseum" is
medieval, from the nearby Colossus), Pantheum, Forum Traiani, Columna Traiani, Circus Maximus,
Palatium, Insula Tiberina, Tiberis, Via Appia, Ostia, Portus.

---

## 1. Identity

**The moment: around 21 April AD 126, Rome's birthday (the Parilia, which Athenaeus, writing
about AD 200, says was "now called" the Romaia, in honour of the Fortune of Rome whose temple
Hadrian built; Hadrian's coins of 121 already celebrate the city's 874th birthday with circus
games), in the ninth year of Hadrian (r. 117–138).** [checked: Athenaeus 8.361f (Gulick,
LacusCurtius): "the Parilia, as it used to be called, though it is now called the Roman
Festival"; "renamed by Hadrian" was an overstatement]

Why this moment:

- **Imperial Rome at its fullest before the late empire**: Trajan's Forum, Column (113) and
  Markets are new; the Colosseum (80), the Flavian palace on the Palatine, the Capitoline temple
  rebuilt by Domitian with gilded roof tiles, the Baths of Trajan (109) all stand.
- **The Pantheon has just been rebuilt.** Brick stamps and construction evidence date Hadrian's
  rotunda to about 114–128, with dedication usually placed around 125–128 (some scholars argue the
  project began under Trajan). The game shows it complete.
- **The Temple of Venus and Roma is a building site.** Begun around 121 on the Velia, on the day of
  Rome's birthday (the 121 date is inferred from Athenaeus and the coins), it was dedicated in 135 and
  finished by 141. To make room, the colossal bronze statue (the Colossus, now a sun god) was moved
  upright by the architect Decrianus with the help of elephants (Historia Augusta).
- **Hadrian is in Italy** between his first great journey (121–125) and the second (from 128); his
  villa at Tibur is rising. Exactly where he was on 21 April 126 is not recorded; the game shows
  him in Rome for the festival.
- **What does not yet exist** and is not shown: the Temple of Antoninus and Faustina (141), the
  Mausoleum of Hadrian (begun c. 130s), the Arch of Septimius Severus (203), the Septizodium, the
  Baths of Caracalla and of Diocletian, the Basilica of Maxentius, the Arch of Constantine, the
  Aurelian Walls (271: Rome in 126 is **an open city without a circuit wall**; the old Servian wall
  survives only in stretches and gates), anything Christian in monument form.
- **April**: spring sun, poppies in the fields, swallows back, the sailing season open and the
  grain fleet arriving, the festivals of Ceres, Pales and Venus in quick succession.

**The feeling, in five sentences.**
You smell baking bread at dawn, wood smoke from bath furnaces, the sour tang of the fullers' vats,
pine resin and wet stone from fountains, fish sauce and fried food from street counters, and
incense from temple steps. You hear fountains everywhere, the roar of a crowd from the Circus, the
creak of a treadwheel crane, hawkers calling, the cart wheels that are banned by day and rumble all
night, and a water organ from the arena. You see warm brick and travertine, coloured marbles and
gilded bronze, five-storey apartment blocks with balconies over shopfronts, umbrella pines and
cypresses on the hills, and the long arcades of the aqueducts walking in over the Campagna.
Rome is most itself in the **golden late afternoon**, when the baths are full, the light turns the
travertine honey and the Forum fills with people walking home.

**"Aroma" made visible.** Bread: thin chimney smoke from bakeries at dawn. Baths: steam from
furnace flues in the afternoon. Fountains: spray glints at every street corner (*lacus*). Incense:
blue smoke on temple steps. Night: a parade of carts with lanterns.

---

## 2. Map plan

### 2.1 Size, scope, orientation

- **Region: 176 × 160 tiles, world origin (96, 24), base level 1.** Local plan coordinates `c`
  (east), `r` (south): world `C = 96 + c`, `R = 24 + r`; world level = 1 + local level.
- **Neighbours:** the corner lies west (its old road comes over the Janiculum ridge as the Via
  Aurelia); Ostia and Portus lie south-west on the coast (§3.7); Tibur and the Alban hills east;
  the Via Appia leaves at the south-east for Brundisium.
- **Camera:** from the south-west (`world.md` §3.2). In view: the Capitoline temple (faces south),
  the Curia, the Basilica Aemilia, the Temple of Mars Ultor, Trajan's Markets, the Theatre of
  Marcellus's arcades, the Palatine palace above the Circus Maximus, the Colosseum, the aqueduct
  arcades, Emporium and the river. Hidden: the Pantheon's portico (it faces north; the rotunda and
  dome are seen from behind), the fronts of the temples of Saturn, Concord and Castor.
- **Scale:** monuments at `s = 0.65` (tile ≈ 6.2 m real) unless stated; imperial fora `s = 0.5`;
  the Colosseum `s = 0.6`; the Theatre of Marcellus `s = 0.5`; very large complexes at `s = 0.33–0.4`
  (Circus Maximus, Baths of Trajan, Saepta, Stadium, Theatre of Pompey). Distances compressed
  about 2 × (one tile ≈ 13 m of real distance between monuments).
- **In scope (region):** the Capitol, the Forum Romanum, the imperial fora with Trajan's Forum and
  Markets, the Velia with the Temple of Venus and Roma, the Colosseum valley, the Palatine, the
  Circus Maximus, the Forum Boarium and Tiber Island, the Theatre of Marcellus, the southern Campus
  Martius with the Pantheon, the Subura, the Caelian with the aqueduct, the Aventine, the Emporium
  with Monte Testaccio, Transtiberim (Trastevere), the start of the Via Appia, the Castra Praetoria
  (compressed).
- **Roman-time waypoints outside the region** (§3.7): Ostia and Portus, Tibur and Hadrian's Villa,
  the Alban Mount, Capua, Beneventum, Brundisium.

### 2.2 Districts

| # | District | Plan area (c, r) | Level | Contents |
|---|---|---|---|---|
| D1 | Capitoline hill | c 66..85, r 44..66 | 6–7 | temple of Jupiter, the Arx with Juno Moneta, the Tabularium, the Tarpeian rock |
| D2 | Forum Romanum | c 86..122, r 52..77 | 0 | the old civic heart |
| D3 | Imperial fora | c 72..128, r 13..54 | 0–1 | Trajan, Caesar, Augustus, Nerva, Peace |
| D4 | Quirinal slope and Trajan's Markets | c 97..111, r 10..34 | 1–5 | the Markets climbing the hill |
| D5 | Subura and Esquiline edge | c 112..143, r 10..38 | 0–2 | apartment blocks, shops, workshops |
| D6 | Velia and Colosseum valley | c 123..175, r 56..90 | 0–1 | Arch of Titus, Venus and Roma (building site), Colossus, Meta Sudans, Colosseum |
| D7 | Oppian (Baths of Trajan) | c 144..175, r 18..52 | 2 | the great baths (N), houses |
| D8 | Palatine | c 98..140, r 78..106 | 6 | imperial palace, Apollo, the hut of Romulus |
| D9 | Circus Maximus valley | c 82..136, r 107..119 | 0 | the circus |
| D10 | Aventine | c 66..132, r 120..139 | 5 | temples, houses, gardens |
| D11 | Caelian | c 137..175, r 90..130 | 3 | rich houses, the aqueduct, Via Appia start |
| D12 | Forum Boarium, Holitorium, Velabrum | c 62..84, r 86..106 | 0 | river-port markets, round temple, Ara Maxima |
| D13 | Tiber Island and bridges | c 44..66, r 84..108 | 0 | island shaped like a ship, temple of Aesculapius |
| D14 | Southern Campus Martius | c 10..70, r 0..72 | 0 | Pantheon, Baths of Agrippa, Saepta, Stadium, Theatre of Pompey, Porticus Octaviae, Theatre of Marcellus |
| D15 | Transtiberim (Trastevere) and the Janiculum | c 0..44, r 64..159 | 0–3 | workshops, warehouses, dock workers, a Jewish community, the Via Aurelia over the ridge |
| D16 | Emporium and Monte Testaccio | c 58..96, r 140..159 | 0–4 | river wharves, warehouses, the mound of oil amphorae |
| D17 | Castra Praetoria (compressed) | c 158..175, r 0..14 | 2 | the Praetorian Guard's camp |
| D18 | Suburban villa, vineyards and market gardens | c 137..175, r 131..159 | 1–2 | along the Via Appia: tombs, pines, a villa, vines |

### 2.3 Landmark placement (local plan coordinates, inclusive)

| Id | Landmark | Footprint (c, r) | w × h | Level | Notes |
|---|---|---|---|---|---|
| `capitolium` | Temple of Iuppiter Optimus Maximus | c 70..78, r 51..60 | 9 × 10 | 6 | faces south (in view); gilded bronze roof tiles |
| `arx` | Arx with the Temple of Juno Moneta | c 70..78, r 44..49 | 9 × 6 | 7 | |
| `tabularium` | Tabularium (record office) | c 81..85, r 53..64 | 5 × 12 | 1 → 6 | arcaded façade looking down the Forum |
| `tarpeian` | Tarpeian rock | c 66..69, r 60..66 | 4 × 7 | 6 | cliff on the hill's south-west |
| `concord` | Temple of Concord | c 86..89, r 54..60 | 4 × 7 | 0 | faces east |
| `vespasian` | Temple of Vespasian and Titus | c 86..89, r 61..64 | 4 × 4 | 0 | faces east |
| `saturn` | Temple of Saturn (state treasury) | c 87..93, r 65..68 | 7 × 4 | 0 | faces east |
| `rostra` | Rostra (speakers' platform with ships' rams) | c 91..94, r 59..61 | 4 × 3 | 0 | with the Golden Milestone beside it |
| `curia` | Curia Iulia (Senate house) | c 93..96, r 53..56 | 4 × 4 | 0 | faces south-west (in view) |
| `lapis_niger` | Lapis Niger (black stone shrine) | c 95..95, r 57..57 | 1 × 1 | 0 | |
| `aemilia` | Basilica Aemilia | c 97..112, r 53..58 | 16 × 6 | 0 | shops (tabernae) along its front |
| `forum_square` | Forum square with Lacus Curtius, the fig, olive and vine | c 95..107, r 59..68 | 13 × 10 | 0 | paved; Pliny mentions the fig, olive and vine growing here |
| `julia` | Basilica Iulia (law courts) | c 94..109, r 69..76 | 16 × 8 | 0 | |
| `castor` | Temple of Castor and Pollux | c 110..114, r 69..76 | 5 × 8 | 0 | faces north; the Lacus Iuturnae spring beside it (c 115, r 72..73) |
| `divus_julius` | Temple of Divus Iulius | c 108..111, r 61..65 | 4 × 5 | 0 | faces west (in view); built where Caesar was cremated |
| `regia` | Regia | c 112..114, r 62..63 | 3 × 2 | 0 | |
| `vesta` | Temple of Vesta | c 112..114, r 66..68 | 3 × 3 | 0 | round; the eternal fire |
| `vestals` | House of the Vestals (Atrium Vestae) | c 115..121, r 65..71 | 7 × 7 | 0 | courtyard with pools |
| `piperataria` | Horrea Piperataria (spice warehouses) | c 116..124, r 56..61 | 9 × 6 | 0 | built by Domitian for pepper and spices from India |
| `arch_titus` | Arch of Titus | c 123..123, r 69..70 | 1 × 2 | 1 | on the Via Sacra at the top of the Velia |
| `venus_roma` | Temple of Venus and Roma (building site) | c 125..142, r 62..73 | 18 × 12 | 1 | platform with a half-built double temple |
| `colossus` | Colossus (statue of the Sun) | c 144..146, r 64..66 | 3 × 3 | 0 | moved here by Hadrian |
| `meta_sudans` | Meta Sudans fountain | c 144..145, r 76..77 | 2 × 2 | 0 | |
| `colosseum` | Amphitheatrum Flavium | c 148..175, r 64..87 | 28 × 24 | 0 | `s = 0.6` |
| `trajan_forum` | Forum of Trajan: square with equestrian statue (c 84..85, r 35..36), hemicycles | c 72..96, r 29..41 | 25 × 13 | 0 | `s = 0.5` |
| `basilica_ulpia` | Basilica Ulpia | c 74..94, r 24..28 | 21 × 5 | 0 | faces south-east (in view) |
| `trajan_column` | Trajan's Column between two libraries | column c 84..84, r 21..21; libraries c 80..83 and c 85..88, r 20..23 | 9 × 4 | 0 | |
| `trajan_temple` | Temple of Divus Traianus (location debated) | c 80..88, r 13..18 | 9 × 6 | 0 | N; placed north of the Column, the traditional reconstruction |
| `trajan_markets` | Trajan's Markets | c 97..109, r 16..33 | 13 × 18 | 1–5 | hemicycle facing south-west (in view), the Via Biberatica |
| `augustus_forum` | Forum of Augustus with Temple of Mars Ultor (c 104..109, r 35..40) and firewall | c 98..110, r 34..46 | 13 × 13 | 0 | temple faces south-west (in view) |
| `caesar_forum` | Forum of Caesar with Temple of Venus Genetrix (c 85..88, r 43..46) | c 85..96, r 43..52 | 12 × 10 | 0 | |
| `nerva_forum` | Forum of Nerva (Transitorium) with Temple of Minerva | c 111..114, r 41..52 | 4 × 12 | 0 | |
| `pacis` | Templum Pacis (Temple of Peace) and garden | c 115..128, r 40..54 | 14 × 15 | 0 | |
| `palatine_tiberiana` | Domus Tiberiana | c 100..112, r 78..84 | 13 × 7 | 6 | |
| `domus_flavia` | Domus Flavia (state palace) | c 110..123, r 85..95 | 14 × 11 | 6 | |
| `domus_augustana` | Domus Augustana (residence) with exedra over the Circus | c 113..126, r 96..104 | 14 × 9 | 6 | the curved façade faces south over the Circus (in view) |
| `palatine_stadium` | Palatine "stadium" garden | c 127..132, r 86..104 | 6 × 19 | 6 | |
| `apollo_palatinus` | Temple of Apollo Palatinus | c 101..106, r 91..96 | 6 × 6 | 6 | |
| `house_augustus` | House of Augustus | c 101..105, r 97..101 | 5 × 5 | 6 | |
| `casa_romuli` | Hut of Romulus | c 99..99, r 102..102 | 1 × 1 | 6 | |
| `lupercal` | Lupercal grotto | c 97..98, r 104..105 | 2 × 2 | 1 | |
| `circus_maximus` | Circus Maximus | c 82..132, r 108..117 | 51 × 10 | 0 | `s = 0.33`; starting gates (carceres) at the west end, curved end east with an arch of Titus |
| `porta_capena` | Porta Capena (Servian gate) | c 133..136, r 118..121 | 4 × 4 | 0 | the Via Appia begins |
| `portunus` | Temple of Portunus | c 70..71, r 96..98 | 2 × 3 | 0 | |
| `hercules_victor` | Round temple of Hercules Victor | c 73..75, r 99..101 | 3 × 3 | 0 | |
| `ara_maxima` | Ara Maxima of Hercules | c 77..78, r 97..98 | 2 × 2 | 0 | |
| `tiber_island` | Tiber Island with the Temple of Aesculapius | c 50..60, r 86..92 | 11 × 7 | 0 | travertine prow, an obelisk as the "mast" |
| `pons_fabricius` | Pons Fabricius | c 61..64, r 87..88 | 4 × 2 | 0 | |
| `pons_cestius` | Pons Cestius | c 46..49, r 89..90 | 4 × 2 | 0 | |
| `pons_aemilius` | Pons Aemilius | c 52..61, r 96..97 | 10 × 2 | 0 | |
| `pons_sublicius` | Pons Sublicius (the wooden bridge) | c 52..61, r 106..107 | 10 × 2 | 0 | sacred: no iron allowed in it |
| `marcellus` | Theatre of Marcellus | c 56..71, r 72..83 | 16 × 12 | 0 | `s = 0.5`; arcaded curve faces south-west (in view) |
| `octavia` | Porticus Octaviae | c 50..60, r 62..70 | 11 × 9 | 0 | |
| `pantheon` | Pantheon | rotunda c 36..44, r 13..21; portico c 37..43, r 8..12 | 9 × 14 | 0 | faces north (hidden); dome in view |
| `pantheon_court` | Pantheon forecourt (colonnaded) | c 34..46, r 0..7 | 13 × 8 | 0 | |
| `matidia` | Temple of Matidia (Hadrian, after 119) | c 48..53, r 0..5 | 6 × 6 | 0 | N |
| `saepta` | Saepta Iulia | c 48..56, r 8..30 | 9 × 23 | 0 | `s = 0.35`; N |
| `iseum` | Iseum Campense (Isis and Serapis) | c 58..64, r 14..22 | 7 × 9 | 0 | N |
| `agrippa_baths` | Baths of Agrippa and the Stagnum | baths c 34..46, r 23..31; pool c 22..32, r 30..35 | — | 0 | |
| `stadium_domitian` | Stadium of Domitian | c 12..21, r 2..26 | 10 × 25 | 0 | `s = 0.35`; N |
| `pompey_theatre` | Theatre of Pompey | c 26..37, r 36..47 | 12 × 12 | 0 | `s = 0.4`; N |
| `trajan_baths` | Baths of Trajan | c 144..173, r 20..49 | 30 × 30 | 2 | `s = 0.35`; N |
| `aqua_claudia` | Aqua Claudia / Arcus Neroniani arcades | from c 175, r 128 → c 155, r 110 → c 137, r 100 | — | 3 → 6 | arcade kit |
| `castra_praetoria` | Castra Praetoria | c 158..175, r 0..14 | 18 × 15 | 2 | `s = 0.4` |
| `emporium` | Emporium wharf and Porticus Aemilia warehouse | wharf c 61..66, r 140..159; warehouse c 67..85, r 142..150 | — | 0 | `s = 0.25` for the warehouse |
| `horrea_galbana` | Horrea Galbana (grain warehouses) | c 67..84, r 151..156 | 18 × 6 | 0 | |
| `testaccio` | Monte Testaccio | c 86..96, r 148..159 | 11 × 12 | 1–4 | mound of broken oil amphorae (smaller than today) |
| `appia_tombs` | Via Appia tombs, pines and milestones | along the road from (136, 121) to (175, 150) | — | 1 | |
| `suburban_villa` | Suburban villa with vineyard | c 150..166, r 140..154 | 17 × 15 | 1 | |
| `synagogue` | Synagogue of a Transtiberim community (form not known archaeologically) | c 24..28, r 104..107 | 5 × 4 | 0 | N; a modest house-like building |

### 2.4 Plan

Local coordinates, north up, 1 character = 4 × 4 tiles; generated from the tables above (later
footprints win where they share a cell). `.` is open ground, gardens and lanes.

```
   c→ 0       32      64      96      128     160 
r  0  ~~~SSShhnnnnsshhhh.....................PPPPP
r  4  ~~~SSShhnnnnsshhhh.....................PPPPP
r  8  ~~~SSShhhNNhssshhh..........hhhhhhhh...PPPPP
r 12  ~~~SSShhhNNNsssssh..ttt.....hhhhhhhh...PPPPP
r 16  ~~~SSShhhNNNsssssh..ttt.MMMMhhhhhhhh........
r 20  ~~~SSShhBBBBsssssh..|l|.MMMMhhhhhhhhHHHHHHHH
r 24  ~~~SSShhBBBBssshhhUUUUUUMMMMhhhhhhhhHHHHHHHH
r 28  ~~~hh~~~~BBBssshhhUUUUUUMMMMhhhhhhhhHHHHHHHH
r 32  ~~~hh~~~~hhhhhhhhhFFFFFFGGGGhhhhhhhhHHHHHHHH
r 36  ~~~~~~ZZZZhhhhhhhhFFFFFFGGGGhhhhhhhhHHHHHHHH
r 40  ..~~~~ZZZZhhhhhhhhFFFqqqqGGnEEEEE...HHHHHHHH
r 44  ..~~~~ZZZZhhhhhhCaaaCqqqqGGnEEEEE...HHHHHHHH
r 48  ..~~~~hhhhhhhhhhCaaaCqqqq..nEEEEEhhhHHHHHHHH
r 52  ..~~~~hhhhhhhhhhCJJJTqqqqAAnEEEEEhhhhhhhhhhh
r 56  ..~~~~~~~~~hhhhhCJJJToRcAAAAAxxxhhhhhhhhhhhh
r 60  ..hhh~~~~~~hQQQQCJJJToRR###d:xxYYYYYhhhhhhhh
r 64  jhhhh~~~~~~hQQQQCCCCTooo###dVVVYYYYY*OOOOOOO
r 68  jhhhh~~~~~~~QQQQhh...ooIIIIkVV!YYYYY.OOOOOOO
r 72  jhhhhhhhhh~~~hKKKK...::IIIIkk::YYYYY.OOOOOOO
r 76  jhhhhhhhhh~~~.KKKK...::IIDDDDpppppppmOOOOOOO
r 80  jhhhhhhhhh~~~.KKKK......pDDDDppppppp.OOOOOOO
r 84  jhhhhhhhhhh~iii==.......pDDDDDDDDDpp.OOOOOOO
r 88  jhhhhhhhhhh==ii==.......p@@DDDDDDDpphhhhhhhh
r 92  jhhhhhhhhhh~iiii~bbb....p@@DDDDDDDpphhhhhhhh
r 96  jhhhhhhhhhhh.===.bbb....p@@pDDDDDDpphhhhhhhh
r100  jhhhhhhhhhhh.~~~.bbb....%pppDDDDDDpphhhhhhhh
r104  jhhhhhyyhhhh.===.bbb....wpppDDDDDDpphhhhhhhh
r108  jhhhhhhhhhhh.~~~....XXXXXXXXXXXXXXhhhhhzzzhh
r112  jhhhhhhhhhhh.~~~....XXXXXXXXXXXXXXhhhhhzzzhh
r116  jhhhhhhhhhhh.~~~....XXXXXXXXXXXXXgghhhhzzzhh
r120  jhhhhhhhhhhh.~~~uuuuuuuuuuuuuuuuugghhhhhhhhh
r124  jhhhhhhhhhhh.~~~uuuuuuuuuuuuuuuuuuhhhhhhhhhh
r128  jhhhhhhhhhhh.~~~uuuuuuuuuuuuuuuuuu,,,,,,,,,,
r132  jhhhhhhhhhhh.~~~uuuuuuuuuuuuuuuuuu,,,,,,,,,,
r136  jhhhhhhhhhhh.~~~uuuuuuuuuuuuuuuuuu,,,,,,,,,,
r140  jhhhhhhhhhhh.~eWWWWWWWeee.........,,,LLLLL,,
r144  jhhhhhhhhhhh.~eWWWWWWWeee.........,,,LLLLL,,
r148  jhhhhhhhhhhh.~eWWWWWW^^^^.........,,,LLLLL,,
r152  jhhhhhhhhhhh.~eWWWWWW^^^^.........,,,LLLLL,,
r156  jhhhhhhhhhhh.~eWWWWWW^^^^.........,,,,,,,,,,
```

Legend: `~` Tiber and pools, `j` Janiculum ridge, `h` houses and insulae (Campus Martius,
Subura, Caelian, Transtiberim, Esquiline edge), `,` villas, vineyards, Campagna, `S` Stadium of
Domitian, `n` Pantheon forecourt and Forum of Nerva, `N` Pantheon, `s` Saepta, Temple of Matidia,
Iseum, `B` Baths of Agrippa, `Z` Theatre of Pompey, `Q` Porticus Octaviae, `K` Theatre of
Marcellus, `i` Tiber Island, `=` bridges, `b` Forum Boarium temples, `C` Capitoline hill, `a`
Arx, `J` Capitolium, `T` Tabularium, `o` temples of Concord, Vespasian, Saturn, `R` Rostra, `c`
Curia, `#` Forum square, `:` Forum Romanum (other), `A` Basilica Aemilia, `I` Basilica Iulia, `k`
Temple of Castor, `d` Divus Iulius, `v` Vesta, `V` House of the Vestals, `x` Horrea Piperataria,
`!` Arch of Titus, `Y` Venus and Roma (site), `*` Colossus, `m` Meta Sudans, `O` Colosseum, `F`
Forum of Trajan, `U` Basilica Ulpia, `|` libraries, `l` Trajan's Column, `t` Temple of Trajan,
`M` Trajan's Markets, `G` Forum of Augustus, `q` Forum of Caesar, `E` Templum Pacis, `H` Baths of
Trajan, `P` Castra Praetoria, `p` Palatine, `D` palaces, `@` Apollo Palatinus, `%` hut of Romulus,
`w` Lupercal, `X` Circus Maximus, `g` Porta Capena, `u` Aventine, `y` synagogue, `z` player's
peristyle garden, `e` Emporium, `W` wharf and warehouses, `^` Monte Testaccio, `L` suburban
villa.

### 2.5 Streets, water, walls and gates

- **Via Sacra**: from the Forum's west end (c 87, r 64) east past the Regia and the Vestals, up the
  Velia under the Arch of Titus (c 123, r 69..70) and down to the Colosseum valley (c 147, r 75).
  Basalt paving, 2 tiles wide.
- **Clivus Capitolinus**: from the Forum (c 90, r 64) winding up past the Temple of Saturn to the
  Capitolium (c 74, r 61). Stairs from the Forum to the Arx (c 80..84, r 50..53).
- **Argiletum** (c 96..97, r 30..52) north from the Forum into the Subura; **Vicus Tuscus**
  (c 100..101, r 77..104) south from the Forum to the Circus and the river; **Vicus Iugarius**
  (c 80..92, r 69..92) to the Forum Holitorium.
- **Via Lata / Flaminia** north from the Capitol's foot (c 70, r 44) up the Campus Martius to the
  north edge (c 64, r 0).
- **Via Appia** from the Porta Capena (c 136, r 121) south-east to the edge (c 175, r 150) and on
  (world C 271, R 174).
- **Via Aurelia** from the Pons Aemilius west through Transtiberim and over the Janiculum to the
  west edge (c 0, r 96), where the corner's old road joins it.
- **Streets**: everywhere else narrow lanes (1 tile) between apartment blocks, with stepping
  stones at crossings and fountain basins (*lacus*) every 8–12 tiles; a street shrine of the Lares
  (*compitum*) at many crossroads.
- **Tiber**: 6 tiles wide, from the north edge (c 6, r 0) south along the west (c 2..9, r 0..36),
  then south-east (c 20, r 58; c 40, r 70; c 46, r 82), dividing around Tiber Island (west channel
  c 46..49, east channel c 61..64, r 84..94), then south in a channel c 53..60 to the south edge
  (r 159) and on to Ostia. Stone
  embankments with mooring rings near the Emporium and Forum Boarium; mud banks and reeds
  elsewhere.
- **Aqueducts**: the Aqua Claudia arcade crosses the Caelian on high arches and enters the Palatine
  (`aqua_claudia`); smaller channels distribute to fountains, baths and houses (lead pipes stamped
  with names). Of the ten aqueducts serving Rome in 126 (Appia, Anio Vetus, Marcia, Tepula, Iulia,
  Virgo, Alsietina, Claudia, Anio Novus and Trajan's new Traiana of 109), only the Claudia's
  arcade is modelled in full; others appear as distribution towers (*castella*) and fountains.
- **Walls and gates**: Rome has no circuit wall in 126. Surviving stretches of the old Servian wall
  stand on the Aventine (c 66..90, r 132..134) and at the Porta Capena. The sacred boundary
  (*pomerium*) is marked by stone markers (*cippi*), a nice-to-have detail.
- **Cloaca Maxima**: the great sewer outlet into the Tiber at c 64, r 98 (arched mouth in the
  embankment).

### 2.6 Elevation

Local levels; world level = 1 + local.

| Area | Level | Notes |
|---|---|---|
| Forum, Campus Martius, valleys, river banks | 0 | |
| Velia | 1 | gentle rise under the Arch of Titus |
| Oppian, Castra Praetoria | 2 | |
| Caelian | 3 | |
| Quirinal slope (Markets) | 1–5 | terraces with stairs |
| Aventine | 5 | `earth` and `brick` retaining walls |
| Palatine | 6 | `brick` substructures facing the Circus (in view) and the Forum |
| Capitol (temple summit) | 6; Arx 7 | `rock` (tufa) cliffs; the Tarpeian rock on the south-west |
| Monte Testaccio | 1–4 | |
| Janiculum ridge | 3 | west edge; seam mist toward the corner |

Stairs and ramps: Clivus Capitolinus (rise 6), Forum–Arx stairs (rise 7), Clivus Palatinus from
the Arch of Titus (rise 5), Markets stairs (rise 4), Aventine steps (rise 5), Caelian ramp (rise 3).

---

## 3. Asset list

Legend: **M** must-have, **N** nice-to-have. Heights in px at 64 × 32 (10 px/m × `s`). Layers: B
base, S shadow, G glow.

### 3.1 Architectural facts every artist must get right (Rome 126)

- **Materials:** brick-faced concrete (*opus testaceum*: thin red-orange fired bricks in neat
  courses with mortar, concrete core) for nearly everything built since Nero; **travertine** (warm
  cream stone with holes) for the Colosseum and Theatre of Marcellus; **tufa** (grey-brown volcanic
  stone) for older walls and podia; **marble** veneers and columns in many colours: white (Luna,
  Proconnesian, Pentelic), yellow *giallo antico* (Numidia), purple-veined *pavonazzetto*
  (Phrygia), green *cipollino* (Euboea), red porphyry (Egypt), grey and pink Egyptian granite.
  Roofs of red terracotta tiles; on the greatest temples, **gilded bronze** tiles (the Capitolium,
  the Pantheon dome).
- **Orders:** Corinthian dominates imperial temples (acanthus capitals); the Colosseum and Theatre
  of Marcellus stack Tuscan/Doric, Ionic and Corinthian half-columns framing arches; the Pantheon
  portico is Corinthian with monolithic granite shafts.
- **Colour:** temples were painted and gilded in details (capitals, mouldings, pediment
  sculpture); interiors rich in coloured marble; apartment blocks were brick-coloured or plastered
  and painted (red and yellow ochre); shops had painted signs.
- **Pantheon:** portico of 16 monolithic Corinthian columns (8 across the front of grey Egyptian
  granite, the rest pink granite), bronze trusses in the portico roof, the inscription
  M·AGRIPPA·L·F·COS·TERTIVM·FECIT (Hadrian kept Agrippa's dedication); a high intermediate block;
  the brick rotunda with a stepped dome 43.3 m across, covered with **bronze tiles** (removed in
  663; whether they were gilded is not certain: show warm bronze, with a gilded sheen as a choice;
  not re-checked in this pass); the
  **oculus** (about 9 m) open to the sky; the colonnaded forecourt to the north.
- **Colosseum:** an ellipse about 188 × 156 m and 48.5 m high: **three storeys of 80 arches**
  framed by half-columns (Tuscan, Ionic, Corinthian) and an **attic** with Corinthian pilasters,
  small windows and the corbels and sockets for the **240 masts of the awning** (*velarium*);
  statues in the arches of the second and third storeys (shown on coins of Titus); four axial
  entrances, the north one for the emperor; numbered entrances for the public.
- **Insulae** (apartment blocks): 4–5 storeys (Trajan limited height to 60 Roman feet, about 18 m;
  Aurelius Victor), brick-faced, ground floor of **tabernae** (shops with wide openings closed by
  wooden shutters), an upper mezzanine, apartments above with windows (some with mica, most with
  shutters), wooden or brick balconies, tiled roofs, interior courtyards; stairs straight from the
  street. Model after the 2nd-century blocks at Ostia.
- **Domus** (wealthy houses): blank walls on the street with shops let out at the front; inside an
  atrium with a pool (*impluvium*), a garden courtyard with colonnade (*peristylium*), painted walls.

### 3.2 Landmarks

| Id | Name | Footprint | Height px | Layers | Anim | M/N | Look |
|---|---|---|---|---|---|---|---|
| `capitolium` | Temple of Jupiter | 9 × 10 | 200 | B,S,G | — | M | hexastyle Corinthian temple of Pentelic marble on a huge podium, three cellae (Jupiter, Juno, Minerva), gilded bronze roof tiles, a bronze chariot group on the pediment apex, crowded with statues and dedications |
| `arx` | Arx and Juno Moneta | 9 × 6 | 110 | B,S | — | N | smaller temple; the mint had been nearby |
| `tabularium` | Tabularium | 5 × 12 | 150 | B,S | — | M | massive tufa base, arcade gallery with Doric half-columns above, looking down the Forum |
| `tarpeian` | Tarpeian rock | 4 × 7 | cliff | B | — | N | |
| `concord` | Temple of Concord | 4 × 7 | 120 | B,S | — | N | wide transverse cella, hexastyle porch, a gallery of art inside |
| `vespasian` | Temple of Vespasian | 4 × 4 | 120 | B,S | — | N | hexastyle Corinthian on a high podium |
| `saturn` | Temple of Saturn | 7 × 4 | 140 | B,S | — | M | Ionic hexastyle on a high podium; the state treasury in the podium |
| `rostra` | Rostra | 4 × 3 | 40 | B,S | — | M | curved platform faced with bronze ships' rams, honorific statues and columns on top |
| `curia` | Curia Iulia | 4 × 4 | 140 | B,S,G | — | M | tall brick hall with a plain gabled front, bronze doors, stucco imitating marble |
| `lapis_niger` | Lapis Niger | 1 × 1 | 6 | B | — | N | black marble paving square with a low fence |
| `aemilia` | Basilica Aemilia | 16 × 6 | 130 | B,S | — | M | two-storey arcaded front of white marble with tabernae behind |
| `forum_square` | Forum square | 13 × 10 | 30 (statues) | B | fig leaves | M | travertine paving, honorary columns and statues, the Lacus Curtius well-head, the fig, olive and vine |
| `julia` | Basilica Iulia | 16 × 8 | 130 | B,S | — | M | two-storey arcaded hall; the centumviral court; gaming boards scratched into its steps |
| `castor` | Temple of Castor | 5 × 8 | 160 | B,S | — | M | octastyle Corinthian on a very high podium (three columns survive today) |
| `lacus_iuturnae` | Spring of Juturna | 1 × 2 | 20 | B | water | N | basin with statues of the Dioscuri and their horses |
| `divus_julius` | Temple of Divus Iulius | 4 × 5 | 115 | B,S | — | M | hexastyle on a podium with a speakers' platform decorated with ships' rams and a round altar in a niche |
| `regia` | Regia | 3 × 2 | 50 | B,S | — | N | |
| `vesta` | Temple of Vesta | 3 × 3 | 100 | B,S,G | fire glow, smoke | M | round, 20 Corinthian columns, conical roof with a smoke opening; the eternal fire inside |
| `vestals` | House of the Vestals | 7 × 7 | 70 | B,S,G | water | M | two-storey courtyard house with long pools |
| `piperataria` | Horrea Piperataria | 9 × 6 | 70 | B,S | — | N | brick warehouse with small barred windows |
| `arch_titus` | Arch of Titus | 1 × 2 | 100 | B,S | — | M | single-bay marble arch with composite half-columns, the relief of the spoils of Jerusalem inside (card notes its meaning for Rome's Jewish community), inscription in the attic, a bronze chariot group on top |
| `venus_roma` | Temple of Venus and Roma (building site) | 18 × 12 | 40–150 | B,S | crane, dust | M | vast platform on the Velia, two back-to-back cellae (Venus facing east, Roma facing west) rising, part of the peristyle of white marble Corinthian columns up, treadwheel cranes, column drums and capitals lying in rows |
| `colossus` | Colossus | 3 × 3 | 250 | B,S,G | ray glint | M | colossal bronze standing male figure as the Sun god with a radiate crown, on a tall base (statue about 30–35 m; estimates vary) |
| `meta_sudans` | Meta Sudans | 2 × 2 | 110 | B,S | water | M | tall conical brick fountain faced with marble, water running down its sides into a round basin |
| `colosseum` | Colosseum | 28 × 24 | 290 | B,S,G | flags, awning, crowd noise | M | §3.1; awning sails partly drawn on game days; statues in arches |
| `trajan_forum` | Forum of Trajan | 25 × 13 | 120 | B,S | — | M | vast paved square framed by colonnades with statues of captive Dacians in the attic, gilded bronze horse-and-rider statue of Trajan in the centre, hemicycles at the sides |
| `basilica_ulpia` | Basilica Ulpia | 21 × 5 | 125 | B,S | — | M | huge basilica front with columns of coloured marble, gilded bronze roof tiles |
| `trajan_column` | Trajan's Column | 1 × 1 (+ libraries) | 200 | B,S | — | M | column of Luna marble, 100 Roman feet (29.8 m) on a pedestal carved with captured weapons, a spiral relief band (23 turns) of the Dacian wars, a bronze statue of Trajan on top; the two libraries with large windows facing it |
| `trajan_temple` | Temple of Divus Traianus | 9 × 6 | 140 | B,S | — | N | octastyle temple (location and form debated) |
| `trajan_markets` | Trajan's Markets | 13 × 18 | 40–160 | B,S,G | — | M | semicircular brick façade in tiers of shop-fronts and arched windows, a great vaulted hall above, the Via Biberatica street with shops |
| `augustus_forum` | Forum of Augustus and Mars Ultor | 13 × 13 | 165 (firewall) | B,S | — | M | octastyle Corinthian temple of white marble on a high podium against a huge **grey tufa firewall**; porticoes with two exedrae holding statues of Aeneas, Romulus and the great men of Rome (*summi viri*) with inscribed tablets |
| `caesar_forum` | Forum of Caesar and Venus Genetrix | 12 × 10 | 120 | B,S | — | M | narrow colonnaded square, temple (restored by Trajan in 113), the Basilica Argentaria (bankers) |
| `nerva_forum` | Forum of Nerva | 4 × 12 | 110 | B,S | — | N | narrow forum with columns standing close to the wall, frieze of women's crafts (the myth of Arachne) |
| `pacis` | Templum Pacis | 14 × 15 | 90 | B,S | water | N | garden square with long water channels and flower beds, porticoes with art treasures (including the menorah from Jerusalem), a library |
| `palatine_tiberiana` | Domus Tiberiana | 13 × 7 | 90 | B,S,G | — | N | |
| `domus_flavia` | Domus Flavia | 14 × 11 | 130 | B,S,G | — | M | vast throne hall and dining hall around a peristyle with a fountain maze |
| `domus_augustana` | Domus Augustana | 14 × 9 | 160 | B,S,G | — | M | the residence; its curved exedra and high brick substructures face the Circus |
| `palatine_stadium` | Palatine stadium garden | 6 × 19 | 50 | B,S | — | N | |
| `apollo_palatinus` | Temple of Apollo | 6 × 6 | 110 | B,S | — | N | Luna marble temple of Augustus |
| `house_augustus` | House of Augustus | 5 × 5 | 50 | B,S | — | N | modest house with painted rooms |
| `casa_romuli` | Hut of Romulus | 1 × 1 | 36 | B,S | — | M | small thatched hut of wattle and daub, piously rebuilt whenever damaged |
| `lupercal` | Lupercal | 2 × 2 | 20 | B | — | M | cave shrine at the foot of the hill, a fig tree (the Ficus Ruminalis tradition) |
| `circus_maximus` | Circus Maximus | 51 × 10 | 90 | B,S,G | races | M | long arena with tiered seating on three sides, shops in the outer arcades; the central barrier (*spina*) with the **obelisk** brought by Augustus, shrines, **seven bronze dolphins and seven eggs** as lap counters; twelve starting gates at the west end; a triumphal arch of Titus at the curved east end |
| `porta_capena` | Porta Capena | 4 × 4 | 70 | B,S | water drips | N | old tufa gate under an aqueduct branch (the "wet gate") |
| `portunus` | Temple of Portunus | 2 × 3 | 70 | B,S | — | M | small Ionic temple on a podium (survives) |
| `hercules_victor` | Hercules Victor | 3 × 3 | 70 | B,S | — | M | round temple with 20 Corinthian columns of white marble (survives) |
| `ara_maxima` | Ara Maxima | 2 × 2 | 20 | B,S | — | N | |
| `tiber_island` | Tiber Island | 11 × 7 | 90 | B,S | — | M | island faced with travertine as a ship's prow and stern, the temple of Aesculapius (the healing god; sick people sleep in its porticoes), an obelisk as a mast |
| `pons_fabricius` / `pons_cestius` / `pons_aemilius` | Stone bridges | per table | 40 | B,S | — | M | travertine and tufa arches |
| `pons_sublicius` | Wooden bridge | 10 × 2 | 30 | B,S | — | N | |
| `marcellus` | Theatre of Marcellus | 16 × 12 | 165 | B,S | — | M | semicircular travertine façade with arcades (Doric, Ionic, then an attic) |
| `octavia` | Porticus Octaviae | 11 × 9 | 100 | B,S | — | N | colonnaded precinct with temples of Jupiter and Juno and art; a seated statue of Cornelia (§4) |
| `pantheon` | Pantheon | 9 × 14 | 280 | B,S,G | oculus light beam inside (card) | M | §3.1 |
| `pantheon_court` | Pantheon forecourt | 13 × 8 | 60 | B,S | — | N | colonnades around a paved court |
| `matidia` | Temple of Matidia | 6 × 6 | 110 | B,S | — | N | Hadrian's temple to his deified mother-in-law |
| `saepta` | Saepta Iulia | 9 × 23 | 70 | B,S | — | N | long colonnaded hall, luxury shops |
| `iseum` | Iseum Campense | 7 × 9 | 90 | B,S | — | N | Egyptian-style sanctuary with obelisks and sphinxes |
| `agrippa_baths` | Baths of Agrippa and pool | per table | 90 | B,S,G | steam | M | |
| `stadium_domitian` | Stadium of Domitian | 10 × 25 | 60 | B,S | — | N | |
| `pompey_theatre` | Theatre of Pompey | 12 × 12 | 110 | B,S | — | N | with the temple of Venus Victrix on top of the cavea |
| `trajan_baths` | Baths of Trajan | 30 × 30 | 110 | B,S,G | steam | N | huge symmetrical bath complex with great halls, exedrae and gardens |
| `aqua_claudia` | Aqueduct arcade (kit) | 1 × 1 straight, 1 × 1 pier | 140–180 | B,S | — | M | tall arches of tufa ashlar (rusticated) and brick, the channel on top |
| `castra_praetoria` | Castra Praetoria | 18 × 15 | 70 | B,S,G | — | N | rectangular brick-walled camp with gates and towers, barracks inside |
| `emporium` | Emporium and Porticus Aemilia | per table | 60 | B,S | — | M | travertine quay with ramps and mooring stones, a giant warehouse of vaulted bays |
| `horrea_galbana` | Horrea Galbana | 18 × 6 | 60 | B,S | — | M | grain warehouse around courtyards |
| `testaccio` | Monte Testaccio | 11 × 12 | mound | B | — | M | a hill made of broken Spanish oil amphorae (Dressel 20), layered and limed |
| `appia_tombs` | Tombs of the Via Appia (kit) | 1 × 1 / 2 × 2 / 3 × 3 | 40–110 | B,S | — | M | round drum tombs, house tombs, altars with inscriptions |
| `suburban_villa` | Villa with vineyard | 17 × 15 | 70 | B,S,G | — | N | |
| `synagogue` | Synagogue | 5 × 4 | 60 | B,S,G | — | N | |

### 3.3 Kit: buildings, structures and props

| Id | Name | Footprint | Height px | Rot | Layers | Anim | M/N | Look |
|---|---|---|---|---|---|---|---|---|
| `r_insula` | Insula (apartment block) | 4 × 3 | 140 | 4 | B,S,G | laundry flutters | M | §3.1; G: lit windows |
| `r_insula_corner` | Insula corner block with balcony | 3 × 3 | 140 | 4 | B,S,G | — | M | |
| `r_insula_low` | Two-storey shop-house | 3 × 2 | 85 | 4 | B,S,G | — | M | |
| `r_domus` | Domus | 5 × 4 | 80 | 4 | B,S,G | — | M | blank walls, a door with two pilasters, roof with a square opening over the atrium |
| `r_taberna` | Shop front (variants: baker, wine, oil, cloth, pottery, lamp, shoes, books) | 1 × 1 | 50 | 4 | B,S,G | shutter opens | M | wide opening, masonry counter, goods, painted sign |
| `r_thermopolium` | Street counter (hot food) | 1 × 1 | 50 | 4 | B,S,G | steam | M | L-shaped masonry counter with sunk jars, painted front |
| `r_bakery` | Bakery with donkey mill and oven | 3 × 2 | 60 | 4 | B,S,G | mill turns, smoke | M | hourglass-shaped lava mills turned by donkeys, a domed brick oven |
| `r_fullonica` | Fullery | 3 × 2 | 50 | 4 | B,S | treading | M | basins and vats where workers tread cloth, drying racks |
| `r_dyeworks` | Dyer's shop | 2 × 2 | 50 | 4 | B,S | steam | N | |
| `r_glass` | Glass workshop | 2 × 2 | 50 | 4 | B,S,G | furnace glow | N | glassblower at a small furnace (blown glass was common) |
| `r_smithy` | Smithy | 2 × 2 | 50 | 4 | B,S,G | fire | M | |
| `r_lacus` | Street fountain | 1 × 1 | 24 | 2 | B | water | M | rectangular stone basin with a carved spout (often a head) |
| `r_compitum` | Crossroads shrine of the Lares | 1 × 1 | 36 | 2 | B,S,G | lamp | M | small altar and painted niche with two dancing Lares |
| `r_latrine` | Public latrine | 2 × 2 | 40 | 4 | B,S | — | N | |
| `r_bath_small` | Neighbourhood bath (balneum) | 4 × 3 | 70 | 4 | B,S,G | steam | M | brick, a smoking furnace flue, windows with glass |
| `r_horrea` | Warehouse | 4 × 4 | 60 | 4 | B,S | — | M | |
| `r_crane` | Treadwheel crane | 2 × 2 | 140 | 2 | B,S | wheel turns | M | big wooden wheel walked by men, a tall jib |
| `r_scaffold` | Scaffolding | 1 × 1 | 60–140 | 1 | B,S | — | M | |
| `r_cart` | Heavy cart (plaustrum) | 2 × 1 | 36 | 4 | B,S | wheels | M | |
| `r_carriage` | Travel carriage (raeda) | 2 × 1 | 40 | 4 | B,S | wheels | N | |
| `r_litter` | Litter with bearers | 2 × 1 | 40 | 4 | B,S | carried | M | curtained litter on poles |
| `r_milestone` | Milestone | 1 × 1 | 30 | 2 | B | — | M | cylindrical stone with an inscription naming the emperor and the miles from Rome |
| `r_stall` | Market stall | 2 × 1 | 40 | 4 | B,S | awning | M | |
| `r_amphorae` | Amphora stacks (Spanish oil, Gallic wine, African, Eastern) | 1 × 1 | 26 | 2 | B,S | — | M | different shapes by origin (Dressel 20 globular for Baetican oil, slender wine amphorae) |
| `r_barge` | Tiber barge (towed) | 4 × 1 | 40 | 4 | B,S | — | M | flat river boat with a mast for the tow rope |
| `r_merchantman` | Roman merchant ship | 5 × 2 | 100 | 4 | B,S | sail | M | round-hulled, square mainsail with a small foresail (*artemon*), swan-neck stern post |
| `r_statue` | Honorific statue on base | 1 × 1 | 60 | 4 | B,S | — | M | togate or armoured figure, bronze or marble |
| `r_column_honor` | Honorary column | 1 × 1 | 100 | 1 | B,S | — | N | |
| `r_lamp` | Lantern / lamp | 1 × 1 | 10 | 4 | G | flicker | M | |
| `r_brazier` | Brazier | 1 × 1 | 24 | 1 | B,G | fire | M | |
| `r_altar` | Altar | 1 × 1 | 24 | 2 | B,S,G | smoke | M | |
| `r_tomb` | Small tomb / columbarium | 2 × 2 | 50 | 4 | B,S | — | M | |
| `r_vine` | Pergola with vines | 1 × 1 | 40 | 2 | B | — | M | |
| `r_well` | Garden well and basin | 1 × 1 | 20 | 1 | B | — | N | |
| `r_vigiles` | Watch-station (excubitorium) | 3 × 2 | 60 | 4 | B,S,G | — | N | |

### 3.4 Plants

| Id | Name | Height px | Anim | M/N | Note |
|---|---|---|---|---|---|
| `t_stone_pine` | Stone (umbrella) pine | 120 | sway | M | cultivated since the Republic for pine nuts, on villas and roads; use moderately (the city-wide pine look is partly modern) |
| `t_cypress` | Cypress | 110 | sway | M | tombs, gardens |
| `t_plane` | Plane | 110 | sway | M | shading porticoes and gardens |
| `t_laurel` | Laurel (bay) | 50 | — | M | sacred to Apollo; doorways of the palace |
| `t_myrtle` | Myrtle | 30 | — | M | sacred to Venus |
| `t_fig` | Fig | 55 | — | M | the Forum fig, gardens |
| `t_olive` | Olive | 55 | shimmer | M | the Forum olive, the Campagna |
| `t_vine` | Vine | 30 | — | M | |
| `t_box` | Box hedge (topiary) | 16 | — | M | peristyle gardens |
| `t_rose` | Roses | 14 | — | M | gardens, festival garlands |
| `t_poplar` | Poplar | 100 | shimmer | N | river banks |
| `t_oak` | Holm oak | 80 | — | N | |
| `p_acanthus` | Acanthus | 14 | — | M | |
| `p_poppy` | Poppies in grass (April) | 8 | — | M | |
| `p_reeds` | Reeds | 30 | sway | M | Tiber banks |
| `p_cabbage` | Market-garden beds | 8 | — | M | |

### 3.5 Terrain

`grass_spring` (base, fresh green), `basalt_paving` (roads: polygonal grey-black blocks with
kerbs), `travertine_paving` (forums and squares), `brick_ground` (yards), `packed_earth`
(lanes), `tufa_rock` (hills, cliffs), `field_spring` (green wheat), `vineyard_soil`, `river_tiber`
(muddy yellow-green, the "flavus Tiberis"), `mud_bank`.

### 3.6 Walkers and animals

| Kind | Variants | Anim | M/N |
|---|---|---|---|
| Citizen in tunic (everyday) | 4 | walk, talk | M |
| Citizen in toga (formal) | 3 | walk, salute | M |
| Senator (broad stripe, toga) with attendants | 2 | walk | M |
| Matron in stola and palla | 3 | walk, shop | M |
| Working woman (seller, innkeeper, midwife) | 4 | sell, carry | M |
| Child (boy with bulla, girl) | 4 | run, play with nuts | M |
| Enslaved household worker | 4 | carry, sweep | M |
| Freedman / freedwoman shopkeeper | 3 | sell | M |
| Praetorian guard (in the city) | 2 | stand, march | M |
| Vigil (fireman) | 2 | patrol with bucket and axe | M |
| Lictor with fasces | 2 | walk ahead of a magistrate | M |
| Vestal | 1 | walk with attendants | M |
| Priest (flamen with apex cap) | 1 | walk, sacrifice | N |
| Builders (bricklayer, treadwheel walker, marble cutter) | 3 | loop actions | M |
| Porters and dockers | 3 | carry sacks and amphorae | M |
| Barge haulers | 2 | haul rope | M |
| Carter (night only) | 2 | drive cart | M |
| Litter bearers | 1 set | carry | M |
| Baker, fuller, smith, glassblower | 1 each | loop actions | M |
| Gladiators (murmillo, retiarius, thraex) in training | 3 | spar | N |
| Charioteer | 1 | walk with helmet under arm | N |
| Foreigners: Egyptian sailor, Syrian merchant, Greek teacher, Gaul in trousers, German guard, Moorish horseman, Jewish trader | 7 | walk | M (4) / N (3) |
| Animals: donkey (mills and loads), mule, ox, horse (racehorses), dogs, cats (common in Roman houses by now), pigeons, chickens, goats in Trastevere, a caged lion for the arena (N), elephants (N; the imperial herd) | — | — | M (donkey, mule, ox, horse, dog, cat, pigeons) |
| Birds: swallows, swifts, starlings at dusk (murmurations over the Tiber), crows, gulls at the Emporium, storks (N) | — | — | M |

**Asset counts (Rome region):** landmarks 69 entries (M 40 / N 29; the three stone bridges share one entry), kit 35 (M 28 / N 7), plants 16
(M 14 / N 2), terrain 10 (M), walker kinds 22 (M 20 / N 2), animals 11 (M 7 / N 4).

### 3.7 Roman-time waypoints outside the region

World coordinates (`world.md` §5–6). Same moment (AD 126), Rome kit; unique landmarks at
`s ≈ 0.4–0.5`.

| Waypoint (world rect) | Landmark id | Footprint | Height px | M/N | Look (what must be right) |
|---|---|---|---|---|---|
| **Ostia and Portus** (C 100..170, R 184..239; the Tiber reaches the sea at about C 126, R 226) | `portus_hexagon` | 20 × 18 | 40 | M | Trajan's hexagonal harbour basin (about 358 m a side; opened c. 112), lined with warehouses and quays, connected by a canal to the Tiber; ships moored side by side |
| | `portus_lighthouse` | 3 × 3 | 160 | M | the lighthouse of Claudius's outer harbour, a tower of diminishing storeys with a fire on top (built on the sunken ship that had carried Caligula's obelisk) |
| | `ostia_town` | kit, 24 × 16 | — | M | brick insulae and warehouses (*horrea*), the square of the shipping offices (Piazzale delle Corporazioni; most of the emblem mosaics seen today were laid in the **late 2nd century**, after our date, so in 126 show plainer floors or few emblems [checked: ostia-antica.org, regio II.vii.4]), the Capitolium of Ostia (Hadrianic, 120s), the river harbour with barges |
| **Tibur and Hadrian's Villa** (C 272..303, R 40..79) | `hadrian_villa` | 22 × 24 | 110 | N | a sprawling villa under construction since about 118: the round "Maritime Theatre" (a moated island house), long pools, colonnades, scaffolding and workers; Tibur town on its hill with the round temple above the Anio waterfalls |
| **Alban Mount** (C 278..311, R 130..175) | `latiaris` | 6 × 6 | 70 | M | the sanctuary of Jupiter Latiaris on the summit, where the consuls held the Latin Festival (*Feriae Latinae*) each year; below it the round crater lake (Lacus Albanus) and villas; the Via Appia passes at its foot |
| **Capua** (C 318..333, R 198..213) | `capua_amphitheatre` | 10 × 8 | 110 | N | the great amphitheatre of Capua, the second largest in Italy |
| **Beneventum** (C 344..355, R 208..219) | `arch_trajan_beneventum` | 2 × 1 | 100 | N | Trajan's marble arch (dedicated 114) where the Via Traiana leaves the Appia, covered in reliefs of his deeds |
| **Brundisium** (C 380..407, R 248..279) | `brundisium_harbour` | 16 × 12 | 70 | M | the branching natural harbour, quays, warehouses, ships for Greece; a column at the end of the Via Appia (the surviving column's date is debated: shown as a simple marker column) |
| On the Via Appia (whole stretch) | `mutatio` | 6 × 4 | 50 | M | road relay station for changing mules (Rome's state post, the *cursus publicus*), with an inn (*caupona*) nearby |

**Asset counts (Rome with waypoints):** region landmarks 69 (M 40 / N 29) + waypoint landmarks 9
(M 5 / N 4) = 78; kit 35 (M 28 / N 7); plants 16 (M 14 / N 2); terrain 10 (M); walker kinds 22
(M 20 / N 2); animals 11 (M 7 / N 4). **About 172 entries: must-have about 124, nice-to-have
about 48.** The must-have landmark set (Capitol, Forum core, Colosseum, Venus and Roma site,
Trajan's Forum and Markets, Forum of Augustus, Palatine, Circus, Tiber Island and bridges, Forum
Boarium temples, Theatre of Marcellus, Pantheon, aqueduct, Emporium and Testaccio, Ostia/Portus,
Alban Mount, Brundisium) builds a convincing Rome on its own.

---

## 4. Figures

### 4.1 Heroes and notables

| # | Figure | Dates | Presence | Who they were | How to recognise | Where / what they do | M/N |
|---|---|---|---|---|---|---|---|
| 1 | **Hadrian** (Publius Aelius Hadrianus) | 76–138; r. 117–138 | present | Emperor, Trajan's successor, tireless traveller, lover of Greek culture, architect-amateur; he made the beard fashionable for Roman men. | **short curly beard**, curled hair; toga with purple border on formal occasions, otherwise tunic and cloak; lictors ahead | the Palatine; the Venus and Roma site inspecting plans; the Pantheon; the Circus box during races | M |
| 2 | **Vibia Sabina** | c. 83–136/7 | present | Empress, grand-niece of Trajan, Hadrian's wife; she travelled with him and received the title Augusta. | elegant stola and palla, her portrait hairstyle (hair swept up into a high coil with a diadem-like band) | Palatine gardens; visits the Vestals; the Circus | M |
| 3 | **Antinous** | c. 111–130 | present (probable) | A youth from Bithynia, Hadrian's beloved, with him from about 124 until his death in the Nile in 130, after which Hadrian made him a god. His presence in Rome in 126 is likely but not documented. | youth with thick curly hair, chlamys, often with hunting gear | Palatine; rides out with Hadrian's hunting party | N |
| 4 | **Marcus Annius Verus (the future Marcus Aurelius)**, aged 4 (five on 26 April) | b. 26 April 121 [checked: *Historia Augusta*, *Marcus* 1.5, 1.10 (LacusCurtius): born "the sixth day before the Kalends of May", consulship = AD 121, on the Caelian; Hadrian called him Verissimus after his father's death] | present | A child of a senatorial family whom Hadrian noticed and nicknamed "Verissimus" (most truthful); he would become emperor in 161 and write the *Meditations*. | small boy in a toga with purple border (*praetexta*) and a gold *bulla* amulet; a tutor beside him | Caelian (his family's house was there); watches the procession | M |
| 5 | **Apollodorus of Damascus** | fl. 100s–120s | present (uncertain) | Trajan's architect: the Forum and Column of Trajan, the Baths of Trajan, the Danube bridge. Cassius Dio says he mocked Hadrian's design for Venus and Roma and was exiled and killed; many historians doubt the story. | Greek-style mantle (pallium) over tunic, a scroll of plans, a measuring rod | Trajan's Forum, looking at the Column; his card tells the story with its doubts | M |
| 6 | **Juvenal** (Decimus Iunius Iuvenalis) | c. 55–after 127 | present | Satirical poet whose verses complain of noisy streets, falling roof tiles, rich patrons and the city's crowds; the source of "bread and circuses". | thin older man in a worn toga, grumbling | Subura streets and the morning *salutatio* queues | M |
| 7 | **Suetonius** (Gaius Suetonius Tranquillus) | c. 69–after 122 | present | Biographer of the Caesars and Hadrian's former secretary for correspondence, dismissed in about 122. | tunic with the narrow stripe of an equestrian, writing tablets | libraries of Trajan's Forum | N |
| 8 | **Mesomedes of Crete** | fl. 2nd century | present | Freedman, lyre-singer and composer at Hadrian's court; some of his hymns survive with their ancient musical notation, among the very few ancient melodies we can still read. | long performer's robe, a large concert lyre (*cithara*) | Palatine gardens, evenings; the music card | M |
| 9 | **Soranus of Ephesus** | fl. 98–138 | present | Greek physician practising in Rome under Trajan and Hadrian, author of a treatise on women's health and childbirth, on care of newborns and midwifery. | Greek mantle, a case of instruments | Tiber Island sanctuary of Aesculapius; a house call | N |
| 10 | **Gaius Appuleius Diocles** | 104–after 146 | present (aged 22) | Charioteer from Lusitania whose racing career began in 122; his monument lists 1,462 victories. In 126 he races for the Whites. | leather helmet cap, laced leather bands round his torso, tunic in his faction's colour, a whip | the Circus stables and races | M |
| 11 | **The senior Vestal (Virgo Vestalis Maxima)** | — | present | Chief of the six Vestal Virgins who kept Vesta's eternal fire and the sacred objects of Rome for 30 years of service; much honoured. Her name in 126 is not known. | white stola, the veil (*suffibulum*) pinned at the breast, woollen bands (*infula, vittae*) and the special braided hairstyle | Temple of Vesta, House of the Vestals; walks to the Circus with a lictor | M |
| 12 | **Plotina** | d. c. 122 | memory | Trajan's widow, praised for her modesty and learning; she supported Hadrian's succession and the Epicurean school in Athens. | translucent; dignified matron with a high hairstyle | the Forum of Trajan at dusk | N |
| 13 | **Trajan** (Marcus Ulpius Traianus) | 53–117 | statue + memory | Emperor 98–117, conqueror of Dacia, builder of the forum, markets and harbour; called "the best" (*optimus princeps*). His ashes lie in the Column's base. | the bronze statue on the Column; the equestrian statue; at dusk a memory in armour by the Column | Trajan's Forum | M |
| 14 | **Aeneas** | myth | statue | Trojan hero, son of Venus, who carried his father Anchises out of burning Troy and led his son Ascanius to Italy, ancestor of the Romans (Virgil's *Aeneid*). | statue group in the Forum of Augustus: Aeneas with the old Anchises on his shoulder and the boy Ascanius by the hand | Forum of Augustus | M |
| 15 | **Romulus and Remus, the she-wolf** | myth | statue + shrine | Twin sons of Mars, set adrift on the Tiber, nursed by a she-wolf at the Lupercal; Romulus founded Rome on 21 April (traditionally 753 BC) and was later worshipped as Quirinus. | the statue of Romulus carrying the spoils of a defeated king in the Forum of Augustus; the Lupercal with a wolf image; a festival reenactor at the Parilia | Lupercal, hut of Romulus, Forum of Augustus | M |
| 16 | **Numa Pompilius** | legend | memory | Second king, the peaceful founder of Rome's religious institutions, advised by the nymph Egeria; the Regia and the cult of Vesta were credited to him. | translucent bearded king in a toga, a scroll | the Regia at dusk | N |
| 17 | **Cloelia** | legend | statue | A young hostage who escaped from the Etruscan king's camp by swimming the Tiber and led other girls to safety; Rome honoured her with an equestrian statue on the Via Sacra (Livy 2.13). Whether a statue stood there in 126 is uncertain: Dionysius (5.35) found the old one gone, "said to have been destroyed when a fire broke out in the adjacent houses", while Pliny and Seneca later speak of one on the Sacred Way, and some said it showed Valeria, not Cloelia. [checked: Dionysius 5.35 (LacusCurtius); Plutarch, *Publicola* 19 (summary)] | bronze girl on horseback | Via Sacra | M |
| 18 | **Cornelia, mother of the Gracchi** | c. 190–c. 115 BC | statue | Daughter of Scipio Africanus, educated, famous for raising her sons (the reformers Tiberius and Gaius Gracchus) and for calling them her jewels. A base inscribed "Cornelia, daughter of Africanus, mother of the Gracchi" survives (Capitoline Museums); Pliny mentions her seated statue in a portico (the Porticus Octaviae area; details debated). | seated marble matron | Porticus Octaviae | M |
| 19 | **Scipio Africanus** | 236–183 BC | memory | Victor over Hannibal at Zama; Livy says he went up to the Capitoline temple before dawn and sat alone with Jupiter before any public business. | translucent general in a toga | Capitolium, only at dawn | N |
| 20 | **Julius Caesar** | 100–44 BC | memory | Dictator, assassinated in 44 BC; cremated in the Forum where his temple now stands; deified. | translucent, laurel wreath, toga | Temple of Divus Iulius at dusk | M |
| 21 | **Cicero** | 106–43 BC | memory | Orator and statesman who spoke from the Rostra; after his murder his head and hands were displayed there. | translucent elderly orator in a toga, scroll | Rostra at dusk, speaking silently | N |
| 22 | **Castor and Pollux** | myth | shrine + apparition | The divine twins who, tradition says, brought news of the victory at Lake Regillus and watered their horses at the spring of Juturna in the Forum. | two young riders with horses and starred caps, watering at the spring | appear at the Lacus Iuturnae at dawn, rarely | N |

### 4.2 Ordinary people (named)

Roman naming: citizens have two or three names; freed slaves take their former master's family
name; Trajan's and Hadrian's freedmen were *Ulpii* and *Aelii*. Persons invented unless stated.

| Figure | Who | Where / routine | Card (40–60 words) |
|---|---|---|---|
| **Claudia Helpis**, innkeeper | freedwoman running a thermopolium in the Subura | counter from dawn to night | "Born a slave, freed by her mistress, Claudia Helpis now runs her own counter of hot chickpeas, lentils, wine and bread. Freed men and women ran a large share of Rome's shops; many proudly carved their trade on their tombs." |
| **Lucius Vibius Primus**, baker | citizen, master of a bakery with four donkey mills | bakery | "Primus's donkeys turn the stone mills before dawn; by sunrise the loaves are stamped with his mark. Every month the state hands out free grain to two hundred thousand citizens; most take it to bakers like him." |
| **Publius Aelius Eutyches**, clerk | imperial freedman in the grain office | Forum → warehouses | "An imperial freedman, he counts the grain ships' cargoes for the prefect of the grain supply. Under Hadrian more such posts went to equestrians, but freedmen still ran the daily paperwork of the empire." |
| **Apion**, sailor | Egyptian, serving in the fleet (a real letter of a 2nd-century Egyptian recruit named Apion survives) | Portus ↔ Emporium | "Apion came from a village in Egypt and joined the fleet. In a real letter, a sailor of that name told his father he had arrived safely at Misenum and had been given a Roman name. Today he rides a grain barge upriver." |
| **Quintus Mulvius**, barge master | citizen, Tiber boatman | the towpath | "Mulvius steers a barge up the Tiber from Portus, towed by men and oxen on the bank path: a few days against the current for some thirty-five kilometres, much quicker back down with the stream." [checked: softened; the bible's "two days" had no source] |
| **Titus Flavius Valens**, fireman | a freedman's son serving in the *vigiles*, the night watch and fire brigade | patrols at night | "Valens walks the streets at night with buckets, axes and blankets. Fire is the great terror of a city of wooden floors and oil lamps. Informally freed slaves who served six years in the watch earned full citizenship." [checked: lex Visellia (AD 24) as reported by Gaius 1.32b (secondary summaries): the reward was for Junian Latins, later shortened to three years by a decree of the Senate (date unknown)] |
| **Felicula**, girl | daughter of a fuller, aged 9 | streets, fountain, games | "Felicula fetches water from the fountain twice a day and plays with walnuts on the pavement with her brother. Her mother dyes cloth; her father treads it clean. She wants to see the races." |
| **Rufina**, weaver | woman of the Jewish community of Transtiberim | home loom, market | "Rufina's family has lived across the Tiber for generations among dockers, potters and traders from the East. Rome's Jews had their own synagogues and burial places; the Arch of Titus, with its spoils of Jerusalem, is not a monument they love." |
| **Sextus**, enslaved litter-bearer | from Thrace, owned by a senatorial household | carries a litter at the morning salutatio | "Sextus carries his master's litter across the city every morning with seven others. Rome had no uniform for slaves: the Senate once rejected one, Seneca says, in case the slaves saw how many they were." |
| **Iulia Ianuaria**, midwife | citizen woman, *obstetrix* | house calls | "Ianuaria has delivered half the children of her street. Soranus wrote that a good midwife must be literate, calm and have soft hands and short nails. Inscriptions remember several midwives by name." |

### 4.3 Hero cards (40–60 words)

| Figure | Title · epithet | Text |
|---|---|---|
| Hadrian | **Hadrianus** · Emperor and traveller | "He has walked the empire from Britain, where his wall is being built, to Syria. Back in Rome he is rebuilding the Pantheon and designing a temple to Venus and Roma himself. He is the first emperor whose portraits always show a full beard." [checked: softened: earlier emperors had been shown with light beards in mourning or youth] |
| Sabina | **Vibia Sabina** · Augusta | "Trajan's grand-niece and Hadrian's wife, she travelled with him across the provinces. Coins carry her portrait and her elaborate hairstyle, copied by fashionable women across the empire." |
| Antinous | **Antinous** · of Bithynia | "A youth from Bithynia, beloved of Hadrian. After his death in the Nile in 130, Hadrian made him a god and founded a city in his name. Today he rides out to hunt." |
| Marcus | **Marcus Annius Verus** · nearly five | "Hadrian calls this serious little boy 'Verissimus', the most truthful. In 35 years he will be emperor and write, in Greek, a private book of reflections that people still read." |
| Apollodorus | **Apollodorus of Damascus** · Architect | "He built Trajan's Forum, Column and Baths and a bridge over the Danube. A later historian says he mocked Hadrian's temple design and paid with his life; many historians think the story is gossip." |
| Juvenal | **Iuvenalis** · Satirist | "He hates the noise: carts at night, crowds by day, tiles falling from tall blocks. He said the people want only two things, bread and circuses. Come and listen, he has more to say." |
| Suetonius | **Suetonius** · Biographer | "Once Hadrian's secretary for letters, now writing lives of the Caesars full of habits, sayings and scandal. He was dismissed, the story goes, for a lapse of manners toward the empress." |
| Mesomedes | **Mesomedes** · Court musician | "A freed lyre-singer from Crete who composes hymns for Hadrian. Some of his songs survive with their melodies written above the words, and can still be sung today." |
| Soranus | **Soranus** · Physician | "Trained in Alexandria, he writes about childbirth, the care of mothers and newborns, and what makes a good midwife. His book was used for more than a thousand years." |
| Diocles | **Diocles** · Charioteer | "A young driver from Lusitania. By the end of his career he will have won 1,462 races and a fortune greater than many senators'. Today he drives four horses for the Whites." |
| Vestal | **Virgo Vestalis Maxima** · Keeper of the fire | "Six women guard the eternal fire of Vesta for thirty years each. They have seats of honour at the games, can free a condemned man they meet by chance, and keep the wills of emperors." |
| Plotina | **Plotina** · Trajan's widow (a memory) | "Praised for her modesty and her learning, she supported Hadrian when Trajan died. Hadrian built her a temple and wore mourning for nine days." |
| Trajan | **Traianus** · The best emperor | "The Senate called him *optimus princeps*. His Column tells the Dacian wars in a spiral of 2,500 figures; his ashes rest in its base." |
| Aeneas | **Aeneas** · Ancestor of Rome | "Carrying his father, leading his son, he fled burning Troy for Italy. Augustus placed him here, facing Romulus, at the beginning of Rome's story." |
| Romulus and Remus | **Romulus and Remus** · Sons of Mars | "Set adrift on the flooded Tiber, nursed by a she-wolf in the Lupercal cave below the Palatine. Romulus founded the city on 21 April; today is its birthday." |
| Numa | **Numa** · The peaceful king (a memory) | "Rome's second king gave the city its priests, its calendar and the cult of Vesta, advised, they said, by the nymph Egeria in a sacred grove." |
| Cloelia | **Cloelia** · The girl who swam the Tiber | "A hostage of the Etruscan king, she escaped across the river with other girls. The king admired her courage so much he let her free more hostages. Rome gave her a statue on horseback." |
| Cornelia | **Cornelia** · Mother of the Gracchi | "Daughter of Scipio, she refused a king's proposal, educated her children herself, and called her sons her jewels. Her statue's base still survives." |
| Scipio | **Scipio Africanus** · Victor over Hannibal (a memory) | "Before any public business he climbed to Jupiter's temple and sat there alone, Livy says. Some Romans whispered he was the god's son." |
| Caesar | **Divus Iulius** · (a memory) | "Dictator, killed by senators in 44 BC. The people burned his body here in the Forum; on that spot rose his temple, the first to a Roman made a god." |
| Cicero | **Cicero** · Orator (a memory) | "He spoke from these Rostra against Catiline and Mark Antony. After his murder, Antony had his head and hands nailed here. At dusk, he still seems to speak." |
| Castor and Pollux | **The Dioscuri** · Divine twins | "After the battle of Lake Regillus two young riders were seen watering their horses at Juturna's spring, announcing the victory, then vanishing. Rome built them a temple beside the spring." |

---

## 5. Civilization: society in motion

Rome in 126 had perhaps a million inhabitants (estimates range from about 450,000 to over a
million): citizens rich and poor, freed people, enslaved people (perhaps a fifth to a third of the
population), and immigrants from every province.

| Layer | Who you see | Share of walkers | Routine |
|---|---|---|---|
| Emperor and household | Hadrian, Sabina, imperial freedmen and slaves, the Praetorians | rare | Palatine, public appearances |
| Senators and equestrians | in togas with stripes, with clients and attendants | 3 % | morning salutatio, Senate in the Curia, courts, baths |
| Ordinary citizens (*plebs*) | shopkeepers, craftsmen, labourers, clients | 30 % | work from dawn, the grain distribution, the baths, games |
| Freed people | shopkeepers, artisans, clerks, the rich freedman | 15 % | own trades; freedmen's associations |
| Enslaved people | domestic servants, porters, litter-bearers, craftsmen, secretaries, dockers; public slaves | 20 % | at work everywhere; no distinctive dress |
| Women | matrons, workers (sellers, innkeepers, midwives, wet-nurses, weavers, fullers' wives), Vestals, empresses | (part of the above) 40 % of walkers | home, market, fountains, baths (separate hours or bathhouses), temples, the games |
| Children | boys and girls with amulets, school pupils under an awning in the Forum | 8 % | school mornings, play in the streets |
| Soldiers and watch | Praetorians, urban cohorts, vigiles, imperial horse guards | 6 % | guard posts, patrols at night |
| Priests | Vestals, pontiffs, flamens, priests of Isis and Cybele | 1 % | sacrifices, festivals |
| Foreigners | Greeks, Syrians, Egyptians, Jews, Gauls, Spaniards, Africans, Germans, Arabs, Indians (rare) | 10 % | trade, teaching, medicine, service |
| Performers | gladiators, charioteers, actors, mime dancers, musicians | 2 % | games |

---

## 6. Civilization: dress, work and how Rome was run

### 6.1 Evidence for dress

Statues and portrait busts (Hadrian, Sabina, Plotina; togate statues), reliefs (the Arch of Titus;
Trajan's Column: legionaries in plate armour, auxiliaries in mail, Dacians; the Anaglypha Traiani in
the Forum), funerary reliefs of freedmen and tradespeople (bakers, butchers, midwives), Pompeian
and Ostian wall paintings and mosaics (to 79 AD and 2nd century), the Zliten mosaic (arena
musicians and gladiators), surviving textiles (Egyptian finds), texts: Juvenal and Martial (the
burden of the toga), the Historia Augusta (Hadrian required senators and equestrians to wear the
toga in public), Seneca (no uniform for slaves), Quintilian (how to wear a toga).

**Garments.** *Tunica*: the basic belted tunic of wool or linen, knee length for men, ankle length
for women; *clavi*: purple stripes from shoulder to hem: broad (*latus clavus*) for senators,
narrow (*angustus clavus*) for equestrians; *toga*: the citizen's large semicircular white wool
mantle (about 5 m long), worn for formal public life; *toga praetexta* (purple border: magistrates,
freeborn boys); *toga pulla* (dark, mourning); *stola*: the long sleeveless overdress of married
women, worn over the tunic (by the 2nd century mostly on statues and formal occasions); *palla*:
women's mantle, often over the head; *paenula*: hooded bell-shaped travel cloak; *lacerna*: open
cloak pinned at the shoulder; *sagum*: soldier's cloak; *subligaculum*: loincloth; *pilleus*: felt
cap of the newly freed; *calcei*: closed shoes of the citizen (senators' black, patricians' with a
crescent buckle); *soleae*: sandals for home; *caligae*: soldiers' hobnailed boots.

### 6.2 Dress reference

| Kind of person | Garments | Fabric, colours, rules | Hair, beard | Headgear | Footwear | Jewellery | Carries | Draw at 16–24 px | Evidence |
|---|---|---|---|---|---|---|---|---|---|
| Emperor (Hadrian) | toga with purple border on state occasions; purple and gold for triumphs; general's cloak (*paludamentum*) and cuirass for the army; at home a tunic | purple restricted to imperial and magistrate uses | short curly beard, curled hair | laurel wreath for ceremony | calcei | signet ring | — | beard + white toga with purple edge + lictors | busts, statues |
| Senator | white toga over tunic with broad purple stripes | wool | **short beard in Hadrian's fashion** (many men followed him), or clean-shaven older men | bare | black senatorial calcei | gold ring | scroll | toga + stripe + attendants | statues, reliefs |
| Equestrian | tunic with narrow stripes, toga in public | wool | as above | — | calcei | **gold ring** of rank | tablets | — | texts |
| Citizen at work | belted tunic, knee length; cloak (lacerna or paenula) in bad weather | undyed wool, browns, reds, greens, blue; rich colours costlier | short hair, beard or not | hooded paenula in rain, felt cap | sandals, shoes | — | tools | short tunic | reliefs of trades |
| Citizen formal | white toga | toga required at the games and in public business; Juvenal says that in many parts of **Italy** nobody puts on a toga until he is dead [checked: Juvenal 3 (Ramsay, tertullian.org); the line is about country towns, not the poor of Rome] | — | — | calcei | — | — | white mantle wrapped over the left arm | Quintilian, Juvenal |
| Matron | ankle-length tunic, **stola** (long overdress with shoulder straps), **palla** over the head outside | fine wool or linen, coloured (saffron, green, blue, violet), patterned | **Sabina-style** high coiffure, or hair parted and gathered in a bun; wigs and hairpieces (blond hair from Germany prized) | palla, ribbons (*vittae*) | soft shoes | earrings, necklaces, rings, hairpins | — | long dress + mantle over the head + hair high | statues of Sabina and Plotina |
| Working woman | long tunic, belt, apron, shawl | undyed or simple colours | hair tied up, kerchief | kerchief | sandals | — | baskets, jugs | — | funerary reliefs (sellers, midwives) |
| Boy (freeborn) | tunic; toga praetexta formally | — | short hair | — | sandals | **bulla** (gold or leather amulet at the neck) | walnuts, writing tablet | bulla dot | statues |
| Girl | tunic, small palla | — | hair in a knot | — | sandals | **lunula** (crescent amulet) | doll | — | — |
| Enslaved person | as free workers: tunic, cloak | **no distinctive dress** (Seneca); quality depends on household | — | — | sandals or barefoot | — | loads | indistinguishable by dress, shown by tasks | Seneca, reliefs |
| Freed person | as citizens; the **pilleus** cap at the moment of freeing | — | — | pilleus (ceremony) | — | — | — | — | coins (Libertas), tomb reliefs |
| Vestal | white stola, **suffibulum** (white veil pinned at the breast), **infula** and **vittae** (wool bands) | white wool | the *seni crines* (six braids) | infula | — | — | a lamp or simpulum (ladle) | white veil with bands | statues |
| Flamen (priest) | heavy cloak (*laena*) over a toga | — | — | **apex** (cap topped with a spike of olive wood) | — | — | — | the spiked cap | reliefs (Ara Pacis) |
| Priest of Isis | white linen, shaven head | linen | **shaven head** | — | — | — | sistrum | shaven head + white | wall paintings |
| Lictor | toga or tunic with a red cloak (*sagum*) | — | — | — | — | — | **fasces** (bundle of rods; the axe removed inside the city) | rods on shoulder | reliefs |
| Praetorian (in Rome) | in the city, tunic and cloak or even toga; on parade, cuirass and helmet with plume | — | short hair, beard optional | crested helmet on parade | caligae | — | spear, oval or rectangular shield (on reliefs) | — | reliefs, Tacitus |
| Legionary (on campaign, shown on the Column; in Rome only as veterans and recruits) | **lorica segmentata** (iron plate armour) over a tunic; scarf (*focale*); belt with apron of studded straps | tunic colour debated (undyed and red both likely) | short hair | Imperial Gallic helmet | caligae | — | curved rectangular shield (*scutum*), javelin (*pilum*), short sword (*gladius*) on the right | rectangle shield + plates | Trajan's Column |
| Auxiliary | **lorica hamata** (mail) | — | — | helmet | caligae | — | flat oval shield, spear, longer sword | oval shield + mail | Trajan's Column |
| Vigil (fireman) | tunic, sturdy cloak | — | — | — | boots | — | **leather bucket**, axe, a pole with a hook | bucket + axe | texts |
| Gladiators | murmillo (fish-crested helmet, large shield, sword), retiarius (no helmet, net, trident, shoulder guard), thraex (griffin-crested helmet, small shield, curved sword), secutor | loincloth (*subligaculum*), belt, arm guard (*manica*) | — | helmets | barefoot | — | — | crest/net silhouette | Zliten mosaic, reliefs |
| Charioteer | short tunic in faction colour (White, Red, Green, Blue), laced leather bands round the torso | — | — | close leather cap | boots | — | whip, knife (to cut the reins) | coloured tunic + strapped chest | mosaics |
| Musician (tibicen, cornicen) | tunic, toga at sacrifices | — | — | — | — | — | double tibia; the G-shaped cornu | — | reliefs, Zliten mosaic |
| Greek teacher / philosopher | **pallium** (Greek mantle) without toga; Hadrian himself liked Greek dress | — | long beard | — | sandals | — | scroll | beard + mantle without tunic stripes | portraits |
| Egyptian sailor | short tunic, sometimes linen | — | short hair | — | barefoot | — | rope | — | papyri, mosaics |
| Syrian merchant | long tunic, mantle | colourful | beard | — | — | rings | goods | — | reliefs from Palmyra |
| Gaul / German | trousers (*bracae*), long-sleeved tunic, hooded cloak | checked or striped wool | long hair, moustache | hood | boots | torc (Gauls) | — | trousers + hood | reliefs |
| Parthian envoy (N) | trousers, long-sleeved tunic, coat | rich | beard | cap | boots | — | — | — | reliefs |
| Dacian (veteran, prisoner, on the Column) | trousers, tunic, cloak | — | long hair, beard | **pileus** (Dacian felt cap) | — | — | — | cap + trousers | Trajan's Column, Forum attic statues |

**Common mistakes to avoid (Rome).** Everyone in white togas all day (the toga was formal and
increasingly avoided; most people wore coloured or undyed tunics). Clean-shaven men only (in 126
beards are in fashion). Lorica segmentata on everyone (auxiliaries wore mail; praetorians in the
city often did not wear armour). Medieval cloaks and helmets, horned or winged helmets. Purple
worn by anyone. Slaves in chains or rags as a uniform. White marble everywhere (brick, travertine,
coloured marbles, gilding, paint). The Aurelian Walls, the Arch of Constantine, the Septimius
Severus arch or the Temple of Antoninus and Faustina in 126. Gladiators in the Circus Maximus
(chariot races were in the Circus; gladiators in the amphitheatre). Thumbs-up/thumbs-down as a
known gesture (the ancient gesture is uncertain).

### 6.3 Occupations and work

| # | Job | Where | Tools and materials | Steps (looping actions) | Hours / season | Who | Product → next |
|---|---|---|---|---|---|---|---|
| 1 | Sailor of the grain fleet | sea → Portus | sails, ropes | reef sail → steer → moor → unload | sailing season (Apr–Oct) | free sailors, Egyptians | grain → **Portus warehouses** |
| 2 | Docker (*saccarius*) | Portus, Emporium | sacks, gangplanks | shoulder sack → cross plank → drop → tally | daytime | free and enslaved; dockers had guilds | grain, oil → **warehouses / barges** |
| 3 | Barge hauler (*helciarius*) | Tiber towpath | tow rope, harness, oxen | lean into rope → walk → rest → walk | daytime | free labourers | barge → **Emporium** |
| 4 | Warehouse clerk | Horrea Galbana, Emporium | tablets, measures, seals | measure → record → seal → store | daytime | freedmen, slaves | grain → **distribution, bakers** |
| 5 | Grain distributor | Porticus Minucia (card) / distribution point | tokens, measures | check token → measure 5 modii → pour → next | monthly | officials | grain → **citizens → bakers** |
| 6 | Miller | bakery | lava mills, donkeys | load grain → drive donkey → sieve → bag | before dawn | slaves, freedmen | flour → **baker** |
| 7 | Baker (*pistor*) | bakery | troughs, oven, stamps | knead → shape → stamp → bake | before dawn | freedmen, citizens | bread → **taberna, street** |
| 8 | Thermopolium keeper | counter | jars, braziers, ladles | ladle → serve → wipe → call out | dawn to night | freedwomen and men | hot food → **passers-by** |
| 9 | Garum and oil seller | taberna | amphorae, measures | pour → stopper → weigh → sell | daytime | merchants | — |
| 10 | Butcher | taberna | cleaver, hooks, scales | hang → cut → weigh → wrap | morning | — | meat |
| 11 | Fishmonger | Forum Piscarium area, tabernae | baskets, tanks | display → gut → weigh → sell | morning | — | fish |
| 12 | Fuller | fullonica | vats of water and urine, fuller's earth, frames | tread → rinse → brush → hang on frames | daytime | freedmen, slaves | clean cloth → **owner, dyer** |
| 13 | Dyer | dyeworks | vats (madder, woad, saffron; purple only from Tyre and the imperial dye-works) | soak → dip → wring → hang | daytime | — | dyed cloth → **tailors** |
| 14 | Glassblower | glass workshop | furnace, blowpipe, tongs | gather → blow → shape → anneal | daytime | Syrian and local craftsmen | glass vessels → **shops** |
| 15 | Brickmaker | brickyards (*figlinae*) up the Tiber (card); bricks arrive by barge | moulds, stamps, kilns | mould → stamp (many stamps name the consuls of 123) → dry → fire | spring–autumn | free and enslaved | bricks → **building sites** |
| 16 | Bricklayer and concrete gang | building sites (Venus and Roma) | trowels, baskets of mortar, rubble | lay brick facing → pour rubble and mortar → tamp → raise scaffold | daytime | free and enslaved; contractors | walls |
| 17 | Treadwheel walker | cranes | wheel, ropes | walk wheel → lift → hold → lower | daytime | labourers | lifted block |
| 18 | Marble cutter (*marmorarius*) | marble yard by the Tiber, building sites | saws with sand, chisels, drills | saw slab → shape → drill → polish | daytime | specialists, many Greek | columns, veneer → **temples** |
| 19 | Sculptor | workshops | chisels, drills, rasps | rough out → drill curls → smooth → paint | daytime | often Greek | statues → **fora, houses** |
| 20 | Fresco painter | domus interiors | lime plaster, pigments, brushes | plaster → sketch → paint while wet → polish | daytime | teams | painted rooms |
| 21 | Mosaicist | domus, baths | tesserae, mortar, hammer | cut tesserae → set → grout → polish | daytime | teams | floors |
| 22 | Aqueduct worker (*aquarius*) | castella, channels | tools, lead pipe | clear channel → patch → check flow → open valve | daytime | public slaves (Frontinus) | water → **fountains, baths** |
| 23 | Bath stoker (*fornacator*) | bath furnaces | wood, rakes | stoke → rake → feed → check heat | before opening, afternoon | slaves | heat → **baths** |
| 24 | Bath attendant | baths | oil, strigils, towels | oil → scrape → guard clothes → fetch towels | afternoon | slaves | — |
| 25 | Barber (*tonsor*) | street, shops | razor, scissors, mirror | lather → shave → trim beard (fashion!) → mirror | morning | freedmen | trimmed beards |
| 26 | Street vendor | streets, Forum | trays, baskets | call → offer → bargain → sell | daytime | poor citizens, freedpeople, children | sausages, pastries, matches of sulphur |
| 27 | Litter bearer | streets | litter, poles | lift → carry → set down → wait | morning | enslaved | — |
| 28 | Carter (night) | streets | heavy carts, oxen, mules | load at the edge → enter at dusk → deliver → leave by dawn | night (wheeled traffic banned by day) | free and enslaved | building stone, goods |
| 29 | Vigil (fireman) | streets, watch-stations | buckets, axes, blankets soaked in vinegar, pumps | patrol → check lamps → sound alarm → bucket chain | night | freedmen recruits | safety |
| 30 | Lawyer / advocate | Basilica Iulia | rhetoric, tablets | rise → speak → gesture → sit | morning | senators, equestrians | verdicts |
| 31 | Schoolteacher (*ludi magister*) | under an awning in the Forum, shops | tablets, stylus, abacus, cane | dictate → copy → recite → correct | morning | freedmen, Greeks | literate children |
| 32 | Physician / midwife | houses, Tiber Island | instruments, herbs | examine → treat → bandage → advise | daytime | Greeks, freedmen and women | care |
| 33 | Priest at sacrifice, with musician | temples | knife, axe, incense, tibia | wash hands → offer incense → kill victim → inspect entrails (*haruspex*) | festivals | priests, attendants, tibicen | sacrifice and feast |
| 34 | Gladiator | Ludus Magnus (card), arena | weapons | warm up → spar → rest → fight | games days | enslaved, condemned, some volunteers | spectacle |
| 35 | Charioteer and stable hand | Circus stables (card) | horses, chariots | harness → drive → rub down → feed | race days | enslaved and freed; stars became rich | races |
| 36 | Vine-dresser and gardener | villa, market gardens | pruning knife, hoe, baskets | prune → tie → hoe → pick | seasonal | slaves, tenants | wine, vegetables → **market** |
| 37 | Shepherd / goatherd | Campagna, Trastevere edge | crook, dogs | lead → graze → milk → fold | daytime | free and enslaved | cheese, wool |

**Visible chains.**
grain ship → Portus → barge towed up the Tiber → Emporium wharf → Horrea Galbana → grain
distribution and bakers → bread at a taberna;
Spanish oil amphorae → Emporium → oil sellers → broken amphorae thrown onto Monte Testaccio;
marble blocks by barge → marble yard → treadwheel crane → Venus and Roma temple;
aqueduct arcade → castellum → street fountain → baths → (outflow to the Cloaca Maxima → Tiber);
wool → fuller → dyer → tunic → citizen.

### 6.4 How Rome is run

| Area | How it worked in 126 | Where visible |
|---|---|---|
| Emperor and court | the emperor holds supreme power, advised by friends and jurists; his offices (letters, petitions, accounts) staffed by equestrians and imperial freedmen | Palatine; the emperor's appearances in the Forum and the Circus |
| Senate | about 600 senators meet in the Curia; they pass decrees, judge senators, govern some provinces; prestige more than power | Curia (event: senators arriving with clients) |
| Magistrates | consuls (two each year, plus replacements), praetors (justice and games), aediles (streets, markets, buildings), quaestors; lictors with fasces precede them | Forum |
| Prefect of the City | commands the urban cohorts, keeps order, judges | — (card) |
| Praetorian Guard | the emperor's guard, about 10,000 men, camped at the Castra Praetoria | the camp, guards on the Palatine |
| Vigiles | seven cohorts of firemen and night watch for the fourteen regions of the city, under a prefect | watch-stations, night patrols |
| Grain supply (*annona*) | the prefect of the grain supply organises imports (Egypt, Africa, Sicily) and the monthly free grain for about 200,000 citizens holding a token | ships, warehouses, distribution point |
| Water | the curator of the waters and his public slaves run the aqueducts, fountains and pipes; private connections need a grant | aqueduct, castella, fountains |
| Streets and markets | aediles inspect weights, clean streets; the 265 neighbourhoods (*vici*) each have magistrates (*vicomagistri*) who tend the crossroads shrine of the Lares and the emperor's Genius | crossroads shrines |
| Law | praetors issue edicts; courts sit in the basilicas (the centumviral court in the Basilica Iulia); jurists give opinions; Hadrian will have the praetor's edict fixed in permanent form by the jurist Salvius Iulianus (around 130) | Basilica Iulia (event: a trial with crowds on the steps) |
| Taxes | Italy pays no land tax; the provinces pay tribute in money and kind; customs dues at ports; a 5 % inheritance tax for citizens | customs post at Portus (card) |
| Religion | state priesthoods (pontiffs, Vestals, flamens, augurs), the imperial cult, plus Isis, Cybele, Mithras (in small underground temples), Jewish synagogues; a few Christian groups | temples, Iseum, synagogue |
| Records | the Tabularium (state archive), the daily gazette (*acta diurna*) posted in public, bronze tablets of laws on the Capitol, private letters on wax tablets and papyrus | Tabularium; a notice board in the Forum |
| Public works | curators of public works and of roads; emperors pay for great buildings | Venus and Roma site |

### 6.5 How the civilization lived (what to show)

| Topic | Accurate details | Shown as |
|---|---|---|
| Food | bread, porridge (*puls*), olive oil, wine (watered), vegetables, legumes, cheese, eggs, fish, sausages; **garum** (fish sauce) everywhere; the rich dine lying on couches on many courses; the poor eat at street counters because most flats lack kitchens | thermopolia, bakeries, tabernae, a dinner glimpsed in a domus |
| Farming | wheat imported; around Rome: market gardens, vineyards, olives, flocks on the Campagna | D18, Latium stretch |
| Crafts | brick, glass, lamps, marble, mosaics, frescoes, cloth, leather, metal | workshops in the Subura and Transtiberim |
| Trade goods by province | §6.7 | amphora stacks, warehouses, stall labels |
| Money | gold *aureus*, silver *denarius*, brass *sestertius* (4 to a denarius), copper *as*; Hadrian's portrait on coins; bankers in the Basilica Argentaria | money-changer's table, coins in the journal |
| Writing | wax tablets, ink on wooden leaf tablets, papyrus scrolls; graffiti on walls (election notices, jokes, love notes) | painted notices and graffiti decals on walls |
| Schooling | primary school in the open under an awning; grammarians teaching literature; rhetoric for the elite; girls of rich families taught at home | school scene in a Forum portico |
| Medicine | Greek physicians, midwives, the healing sanctuary on Tiber Island | Tiber Island, Soranus |
| Law and courts | §6.4 | Basilica Iulia |
| Religion and festivals | sacrifices with music, household shrines (*lararium*), crossroads shrines, foreign cults | altars, Iseum, synagogue |
| Games | chariot races at the Circus Maximus (factions Red, White, Green, Blue), gladiators and animal hunts in the Colosseum, theatre and mime | Circus event, Colosseum game day |
| Baths | the great public baths (Agrippa, Trajan) and many small ones: changing room, warm, hot and cold rooms, exercise yard; cheap entry; afternoon custom | baths with steam, crowds after the 8th hour |
| Music and dance | tibia at sacrifices, cornu and hydraulis at the games, cithara at court, sistrum in the Isis cult | §9 |
| Housing | the poor in upper floors of insulae, the rich in domus; fire and collapse were common fears (Juvenal) | insulae and domus kit |
| Death and burial | cremation (inhumation slowly growing in the 2nd century); tombs line the roads outside the city; columbaria with urn niches; funeral processions with masks of ancestors and pipers | Via Appia tombs; a funeral procession (N) |

### 6.6 The land beyond the walls

| Element | Where | Coordinates | What it shows |
|---|---|---|---|
| Ostia and Portus | waypoint | world C 100..170, R 184..239 | the grain fleet, the lighthouse, the shipping guilds |
| Tiber wharves and Monte Testaccio | region | D16 | barges, warehouses, the amphora mound |
| Aqueduct arcade across the Campagna | region + Latium stretch | `aqua_claudia`; the arcade continues east into the Latium stretch (world C 272..300, R 150..160) | the water's journey |
| Via Appia with milestones, tombs, relay stations | region + Italy stretch | Porta Capena → Brundisium | travellers, carriages |
| Farms, villas and vineyards | region D18 + Latium | — | country life |
| Quarries | cards and goods: Luna (Carrara) marble arrives by sea, travertine from Tibur by barge down the Anio | marble yard props | |
| Tibur and Hadrian's Villa | waypoint | world C 272..303, R 40..79 | the emperor's project |
| Alban Mount | waypoint | world C 278..311, R 130..175 | the Latin Festival sanctuary |
| Army | the Castra Praetoria (region D17); legions are on the frontiers (card for each province's legions) | — | Praetorians drilling |

### 6.7 The empire at large

The empire of 126 runs from Britain to Mesopotamia's edge (Hadrian gave up Trajan's eastern
conquests in 117). The game shows it through goods, people and labels:

| Province or region | What arrived in Rome | In-city presence |
|---|---|---|
| Egypt | grain (a third of Rome's supply by some estimates), papyrus, linen, granite and porphyry (the Pantheon's grey columns), obelisks | the grain fleet, Egyptian sailors, the Iseum |
| Africa Proconsularis, Numidia | grain, olive oil, yellow marble, wild animals for the games | Africa oil amphorae, caged animals |
| Baetica (southern Spain) | olive oil (in Dressel 20 amphorae that built Monte Testaccio), fish sauce, silver | Testaccio, garum shops |
| Gaul | wine, red-gloss tableware (samian ware), woollen cloaks | Gallic traders in trousers, red pottery on stalls |
| Britannia | lead, tin, hunting dogs, oysters; Hadrian's Wall begun 122 | a card; British hounds |
| Germania | amber (via the Baltic trade), blond hair for wigs; soldiers of the emperor's horse guard | German guards |
| Achaea (Greece) | marble, art, teachers, doctors, philosophers | Greek teachers and doctors; Hadrian's Greek tastes |
| Asia (western Turkey) | Proconnesian marble, wine, textiles | marble yard |
| Syria and Judaea | glass, purple dye from Tyre, dates, balsam, linen | Syrian merchants, glassblowers; the Jewish community of Transtiberim |
| Arabia and India (through the Red Sea) | pepper and spices (the Horrea Piperataria), incense, pearls, gems, cotton | spice warehouse, an Indian trader (N) |
| China (through Parthia and India) | silk (rare, costly) | a silk-seller in the Saepta (N) |
| Dacia | gold, conquered by Trajan | Dacian captives in the art of Trajan's Forum |
| Cappadocia | horses for the Circus | racehorses |
| Italy | wine (Falernian), Luna marble, travertine, bricks | everywhere |

Overview-map labels for the Roman-time stretch: ROMA, OSTIA, PORTVS, TIBVR, MONS ALBANVS, CAPVA,
BENEVENTVM, BRVNDISIVM, VIA APPIA, MARE TYRRHENVM, MARE HADRIATICVM. Cards per province, unlocked
by finding their goods.

### 6.8 A year in Rome (festival calendar)

| Month | Festivals | Work |
|---|---|---|
| January | Kalends (new consuls, vows, gifts), Compitalia (crossroads shrines) | — |
| February | Lupercalia (15th: runners round the Palatine), Parentalia (for the dead) | pruning |
| March | Mars's month: the Salii dance through the city with their shields; Quinquatrus | sailing season opens |
| April | Megalesia (Cybele, games), Cerialia (Ceres), **Parilia / Romaea (21st, the game's moment)**, Vinalia, Floralia begins | spring sowing, first grain ships |
| May | Lemuria (spirits of the dead), Floralia ends | haymaking |
| June | Vestalia (Vesta's temple opened to women; bakers' holiday, donkeys garlanded) | grain harvest |
| July | Ludi Apollinares | threshing |
| August | Vulcanalia, Consualia | — |
| September | **Ludi Romani** (Roman Games: races and theatre) | vintage |
| October | the October Horse (a race and sacrifice on the Campus Martius) | wine making |
| November | Ludi Plebeii | olive harvest, sailing season closes |
| December | **Saturnalia** (17–23: gifts, feasting, slaves served by masters, candles and pottery figurines) | — |

### 6.9 A day in Rome (Roman hours divide daylight into twelve; schedule for ambient scenes)

| Time | Scene |
|---|---|
| Before dawn | bakers at work; the last carts leave the city; vigiles end their rounds |
| Dawn (1st hour) | the **salutatio**: clients in togas queue at patrons' doors on the Caelian and Palatine; Scipio's memory at the Capitol; sacrifices begin at temples |
| Morning (2nd–5th hours) | courts in the Basilica Iulia; the Senate in session (some days); schools in the porticoes; markets busy; building sites roaring; ships unloading at the Emporium |
| Midday (6th–7th hours) | light lunch at street counters; shops close; siesta |
| Afternoon (8th–9th hours) | **the baths fill**; exercise and ball games; on festival days the races in the Circus |
| Late afternoon (10th hour) | dinner (*cena*) in houses; the Forum empties in golden light |
| Dusk | lamps lit at crossroads shrines; memories appear (Caesar, Cicero, Numa) |
| Night | carts enter (wheeled traffic was banned by day); vigiles patrol with buckets; noise from popinae; the Vestals' fire glows |

### 6.10 Knowledge and ideas (met as places, people and cards)

| Idea | How the visitor meets it |
|---|---|
| **Law** | the Basilica Iulia trial; the Tabularium; a card on Roman law as a body of rules and expert opinions that shaped later European law (and on Hadrian's codified edict) |
| **Engineering and concrete** | the Pantheon dome (largest unreinforced concrete dome; lighter stone toward the top); the Venus and Roma site with cranes; card on Roman concrete |
| **Aqueducts and water** | follow the water task; card on the ten aqueducts |
| **Roads and the state post** | milestones and the relay station on the Via Appia; card on the *cursus publicus* |
| **Maps** | a card at the Porticus area on Agrippa's map of the world displayed in Rome; it opens the overview map |
| **Greek learning in Rome** | Mesomedes, Soranus, Greek teachers; Hadrian's philhellenism |
| **Literature** | Juvenal and Suetonius; libraries of Trajan's Forum |
| **Calendar** | the Julian calendar (card at the Regia) |

---

## 7. Ambient life and events

### 7.1 Walkers and routines

| Group | Count (day / night) | Path or zone | Routine |
|---|---|---|---|
| Forum crowd | 40 / 6 | Forum, Via Sacra, basilicas | walk, talk, listen to speakers, sit on the basilica steps playing board games |
| Clients and patrons | 12 / 0 | Caelian and Palatine houses → Forum (morning) | queue at doors, follow the patron in procession |
| Shopkeepers and street sellers | 24 / 4 | Subura, Markets, Saepta, Forum Boarium | open shutters, call, sell |
| Grain chain | 20 / 4 | Emporium → warehouses → bakeries | chain §6.3 |
| Builders | 24 / 0 | Venus and Roma | crane walkers, masons, carts (unloading at night) |
| Bathers | 20 (afternoon peak) / 0 | baths | arrive with towel and oil flask, leave with wet hair |
| Women at fountains | 10 / 2 | street fountains | fill jugs, talk |
| Children | 14 / 0 | streets, school portico | play with walnuts, knucklebones, hoops; recite |
| Vigiles | 2 / 10 | everywhere | patrol at night with lanterns and buckets |
| Night carts | 0 / 12 | from the edges to sites and markets | rumbling carts with lanterns, oxen |
| Praetorians | 6 / 6 | Palatine gates, Castra | guard |
| Foreigners | 10 / 2 | Emporium, Transtiberim, Forum | trade, talk |
| Shepherds and vine-dressers | 6 / 0 | D18, Campagna | herd, prune |

### 7.2 Timed events

| Event | Trigger | Route and cast | Effects |
|---|---|---|---|
| **Parilia / Romaea** (M, the game's moment) | dusk (and the prayer at dawn) of each festival day | Ovid's shepherds' rite, at twilight: the fold swept and sprinkled with water and hung with green boughs, the sheep purified with smoke of burning sulphur, olive wood, pine and juniper; the people fetch fumigants from Vesta's altar (horse blood, calf ash, bean stalks); the prayer to Pales said four times facing the east, hands washed in dew; then young people leap three times over heaps of burning straw. [checked: Ovid, *Fasti* 4 (Kline translation): "purify your sated sheep at twilight", "sprinkle the ground with water"; the flocks are smoked, not sprinkled; the bible's "at dawn" corrected] In the day a procession from the Forum to the Venus and Roma site where Hadrian, Sabina and priests offer sacrifice; at dusk feasting in the streets | bonfires (glow), tibia music, crowd cheers |
| **Races at the Circus Maximus** (M) | every 20 in-game minutes in the afternoon | procession (*pompa circensis*) from the Capitol through the Forum to the Circus with images of the gods; then chariot races of four-horse teams in faction colours, seven laps, dolphins tipping at each lap | the roar of the crowd carries across the city |
| Game day at the Colosseum (N) | some afternoons | crowds enter through numbered arches, the awning drawn, the water organ and horns play; inside not shown (card) | distant roar, hydraulis and cornu |
| Salutatio (M) | each morning | clients gather at domus doors | murmurs |
| Senate session (N) | some mornings | senators in togas with lictors and clients arrive at the Curia | |
| Grain fleet arrives (M) | random, mornings | ships at Portus, barges towed up the Tiber, dockers at the Emporium | shouts, gulls |
| Vestals' walk (N) | daily | the senior Vestal with a lictor from the Atrium Vestae to the Circus | crowd parts respectfully |
| Fire alarm (N) | rare | smoke from an insula in the Subura; vigiles run with buckets; a bucket chain; fire out | bell, shouts; no lasting damage |
| Night carts (M) | every night | carts enter at dusk and leave before dawn | rumble, lanterns |
| Spring shower (M) | weather | short rain, gutters spout, steam off warm paving, a rainbow over the Palatine | rain bed |
| Starling murmuration (N) | dusk | flocks wheel over the Tiber | soft whoosh |

### 7.3 Birds, insects, small life

Swallows and swifts (back in April), starlings at dusk, sparrows, pigeons on temple roofs, crows,
gulls at the Emporium, a kestrel on the Colosseum, storks on the Campagna, bees in gardens, cats in
shops and houses, dogs ("cave canem" signs), donkeys in mills, frogs in the Tiber shallows.

---

## 8. Light, weather and season

**Season:** April: mild days (18–22 °C), cool nights, spring showers, fresh green on the hills,
poppies and wildflowers in the Campagna, morning mist on the Tiber.

| Time | Sky (top → horizon) | Grading target | Light character |
|---|---|---|---|
| Dawn | `#32406e` → `#e59b78` → `#f8d9b0` | soft pink-gold on travertine, mist in the valleys | the Capitol and Palatine tops lit first; bread smoke rising |
| Day | `#4b86c9` → `#a3c9ea` → `#eef0ec` | warm neutral, rich brick reds and greens | gilded roofs flash (Capitolium, Pantheon dome, Basilica Ulpia) |
| Dusk | `#3c2d55` → `#d6703f` → `#f4c37a` | **honey-gold**, deep warm shadows: Rome's signature light | travertine and brick glow; the dome glows gold; starlings |
| Night | `#0d1330` → `#20294d` | blue with many warm points | lamps at crossroads shrines, lit windows in insulae, lanterns on carts, the Vestals' fire, torches at the Palatine gates; stars dimmed slightly by smoke |

- **Haze:** warm smoke haze over the city (bakeries, baths), stronger in the afternoon; mist on
  the Tiber at dawn.
- **Wind:** gentle west wind (the *Favonius*, the spring wind) in the afternoons.
- **Rain:** spring showers (memorable: steaming streets, spouting gutters, a rainbow).
- **What glows at night:** insula windows (many small warm squares), crossroads shrines, the
  Temple of Vesta, the Palatine, bath furnaces' mouths, cart lanterns, thermopolia, bonfires on the
  Parilia. Glow layers: `capitolium`, `curia`, `vesta`, `vestals`, `colosseum` (torches on game
  nights), `colossus` (rays glint at sunset, not glow), `trajan_markets`, `domus_*`, `pantheon`
  (oculus light inside), `circus_maximus`, `r_insula*`, `r_taberna`, `r_thermopolium`, `r_compitum`,
  `r_bath_small`, `r_lamp`, `r_brazier`, `castra_praetoria`.

---

## 9. Sound and music direction

### 9.1 Ambience beds

| Bed | Content | Where |
|---|---|---|
| `amb/rome_day.ogg` | a dense city murmur, fountain splash, hawkers' calls, hammering, a donkey, distant crowd swells | everywhere by day |
| `amb/rome_forum.ogg` | closer voices, an orator far off, footsteps on stone, pigeons | Forum zone |
| `amb/rome_river.ogg` | water against barges, ropes creaking, dockers' shouts, gulls | Tiber and Emporium |
| `amb/rome_circus.ogg` | the roar of 150,000 people rising and falling, hoofbeats on sand | near the Circus during races |
| `amb/rome_night.ogg` | cart wheels on basalt, oxen, a shout, a dog, a distant tavern song, fountains | night |
| One-shots | tibia phrase at a sacrifice, cornu call, sistrum shake at the Iseum, water organ chords from the Colosseum on game days, the treadwheel creak, bath-house echoes | positional |

### 9.2 Music brief

**What is attested.** The **tibia** (Latin name of the aulos, double reed pipes, at every
sacrifice and in the theatre); **cornu** (a big G-shaped bronze horn), **tuba** (straight bronze
trumpet), **lituus** and **buccina** (military signals); the **hydraulis** (water organ, played at
the games: the Zliten mosaic shows it with horns beside gladiators); the **cithara** and lyre
(court and concert music; virtuoso citharodes were stars); the **scabellum** (a foot clapper of
pantomime dancers), cymbals and the frame drum (*tympanum*, Cybele's cult), the **sistrum**
(rattle of Isis). Theory followed Greek models (Ptolemy wrote his *Harmonics* in the 2nd century).
**Mesomedes's hymns** (Hymn to Nemesis, Hymn to the Muse, and the Hymn to the Sun, whose
authorship is debated) survive with notation from exactly this court.

**Evocative choices (modern, stated).** Day: a cithara melody in a Hypolydian/Lydian-type
diatonic mode (the hymns' tonal world), doubled heterophonically by a soft tibia, over a low drone;
on festival passages a hydraulis chord and cornu fanfare far away, like the city's pulse. Night: a
solo lyre with long notes and a faint distant hydraulis. No modern chord progressions, no Hollywood
brass: the grandeur should come from the space and the warmth.

| Piece | Tempo | Form | Mood | Synthesis notes |
|---|---|---|---|---|
| `music/rome_day.ogg` (about 3 min loop) | 84 bpm, stately 3/4 and 4/4 alternating with hymn-like long–short rhythms | cithara theme, tibia joins, a middle festival section with hydraulis drone chords and a distant cornu call, return to the cithara | warm, confident, golden, a little nostalgic | cithara: plucked string with a large wooden body; tibia: reedy, softer than the Greek aulos sound; hydraulis: breathy pipe organ with water-pump flutter (a slight tremolo), only sustained intervals; cornu: brassy natural-horn tones far back in reverb (large stone space, 2.5 s) |
| `music/rome_night.ogg` (about 3 min loop) | free, about 58 bpm | solo lyre, a few tibia sighs, a faint hydraulis pedal | intimate, lamplit | close and dry, with a soft fountain bed underneath |

Overview-map motif: three cithara notes and a soft cornu answer (F–A–C, then F).

---

## 10. What the player does here

| Activity | What exactly | M/N |
|---|---|---|
| Wander and look | the city from the Janiculum to the Caelian, the river to Ostia, the Via Appia to Brundisium | M |
| Cards and journal | journal sections: Landmarks (69 + 9 waypoints), People (22 heroes + 10 ordinary), Provinces (14), Things found (12: a sestertius of Hadrian, a brick stamped with the consuls of 123, a grain token, a lamp, a bulla, a strigil, a gladiator figurine, a faction token, a milestone, a wax tablet, a Dressel 20 amphora handle, a lead pipe stamp) | M |
| Gentle tasks | 1. Follow the grain from Portus to a loaf. 2. Follow the water from the aqueduct to a fountain and a bath. 3. Find all the statues of the Forum of Augustus. 4. Watch a race and cheer for a faction. 5. Stand in the Pantheon at noon (the sunlight disc moves across the dome; a card notes the debated idea that it strikes the doorway on 21 April). 6. Find the seven memory figures at dusk | M (1–4), N (5–6) |
| Decorate zone | a peristyle garden of a domus on the Caelian (c 156..166, r 108..118, 11 × 11): box hedges, roses, fountains, statues, painted walls, a lararium | M |
| Keepsake for the corner | completing task 2 unlocks a small Roman fountain basin for the corner | N |
| Photo mode | as in the corner | M |

---

## 11. Uncertainties for a human to check

1. **Pantheon dating** (begun under Trajan or Hadrian; dedication c. 125–128).
2. **Temple of Venus and Roma** progress in 126 (begun c. 121; dedicated 135): shown half-built.
3. **Colossus**: its height (about 30–35 m) and the date of its move.
4. **Temple of Divus Traianus** location (north of the Column in the traditional reconstruction;
   recent work questions it). Marked nice-to-have.
5. **Hadrian's and Antinous's presence in Rome on 21 April 126** is not documented (still true after
   the fact-check; the cards should say "the game imagines him here").
6. **Apollodorus's fate** (Dio's story is doubted).
7. **Cornelia's statue** location and the date of its base (Augustan by letter forms).
8. **Population figures** (all estimates).
9. **Monte Testaccio's size in 126** (it grew until the mid-3rd century): shown at about half
   today's height.
10. **Synagogue** form and location in Transtiberim are not known archaeologically.
11. **The column at Brundisium** (its date is debated).
12. **Legionary tunic colour** (red vs. undyed) is debated.
13. **The Pantheon sunbeam on 21 April** is a modern hypothesis.
14. **Fact-check (November 2026)**: Marcus is four on 21 April 126 (born 26 April 121); the Parilia
    was "now called" the Romaia by Athenaeus's time (not renamed by decree); Ovid's rite is at
    twilight with the sheep smoked, not sprinkled; Ostia's guild mosaics are mostly late 2nd century;
    Cloelia's statue in 126 is uncertain; the vigiles reward was for Junian Latins (`fact-check.md`).
