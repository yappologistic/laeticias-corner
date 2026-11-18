# Fact-check of the city bibles

An independent check of `persepolis.md`, `athens.md`, `rome.md`, `world.md`, `sources.md` and
`docs/design/sets/world.md`, done in November 2026. Every change made in the bibles carries an
inline `[checked: …]` note naming its source, so builders can find what moved with
`grep -n "checked:" docs/design/cities/*.md docs/design/sets/world.md`.

**How to read the verdicts.**
- **confirmed**: the source named was read (the page or passage itself, not a search summary) and
  agrees.
- **corrected**: the source read disagrees; the bible now says what the source says.
- **uncertain**: the best sources disagree, or the evidence is thin; the bible now says so and
  names the option the game uses.
- **unverifiable**: no source could be read in this pass (blocked, too large, not online). Nothing
  in this column is marked confirmed.

"Read" below means the text was opened and the passage found. Where only a search summary was
available, the row says "(summary)". Some pages refused automated reading: Perseus (all ancient
texts there returned errors), Project Gutenberg (down for maintenance), some Encyclopaedia Iranica
sub-pages (403/404; the main articles "Persepolis", "Apadāna", "Nowruz i", "Candys", "Artystone"
and "Persepolis Elamite tablets" were read). Schmidt's *Persepolis I* (OIP 68) is a 259 MB PDF and
was not downloaded on this machine; Shahbazi's Iranica article, which summarises it, was used
instead, and positions on the excavation plan remain for a builder to check.

---

## 1. Pārsa (`persepolis.md` and the Persian waypoints)

### 1.1 Claims checked

| § | Claim (before) | Verdict | Best source and what it says | Change made |
|---|---|---|---|---|
| 1 | Spring audience linked to New Year only as a hypothesis; "Livius says so plainly" | corrected (framing) | Iranica "Persepolis" (A. Sh. Shahbazi): Herzfeld, Krefter, Erdmann, Ghirshman, Porada hold Persepolis was built for Nowruz; Nylander, Calmeyer, Mousavi deny any evidence; Shahbazi: "cannot be taken lightly". Iranica "Nowruz i" (Boyce): name first in Pahlavi as *nōg rōz*. Livius "Apadana": "perhaps", "no hard evidence". [Iranica Persepolis](https://www.iranicaonline.org/articles/persepolis/), [Iranica Nowruz i](https://www.iranicaonline.org/articles/nowruz-i/), [Livius](https://www.livius.org/articles/place/persepolis/persepolis-photos/persepolis-apadana/) | §1 rewritten: fact (year began in Ādukanaiša) vs hypothesis, both sides named; new card "A New Year at Pārsa?" (§6.10) |
| 1 | Columns 19 m tall | corrected | Shahbazi: Apadāna columns "19.50 m"; Iranica "Apadāna": "more than 19 m" | 19.5 m |
| 0 | Kuh-e Raḥmat as the mountain's name | uncertain (naming) | Shahbazi: older name Kuh-e Mehr, "translated" Raḥmat from the 13th century | note added: map name only |
| 0 | Old Persian *paridaida* | corrected | Iranica "Garden i" (Eilers) (summary): reconstructed *\*paridayda-*; Elamite *partetaš*; a late spelling *paradayadām* is debated | asterisk added |
| 1 | Royal tombs in the mountain are Artaxerxes II and III | confirmed | Shahbazi | — |
| 1 | Fortification tablets 509–493, Treasury 492–458 | confirmed | Iranica "Persepolis Elamite tablets": PF regnal years 13–28 of Darius (509–494; the last tablet month XII of year 28 = spring 493); PT "492–458" | — |
| 2.5 | Achaemenid qanats debated; Polybius 10.28 | confirmed + filled in | Polybius 10.28 (Loeb, LacusCurtius, read): local story of five generations' use for whoever brought water; Wuttmann et al. (summary): qanat at ʿAyn Manawir (Kharga, Egypt) in use by the late 5th c. BC, dated by Demotic ostraca of Artaxerxes I | card note: technique known in the empire; none dated at Pārsa |
| 3.1 | Apadāna: bulls in hall and north portico; lions east, griffins west "as a choice" | corrected | Iranica "Apadāna" (read): composite bull capitals "reserved for the hall and the principal, northern portico"; "addorsed animal capitals set directly on a fluted shaft were restricted to the west and east porticoes". Shahbazi (read): "in the western portico the double-headed bull capitals rested directly on the fluted shafts"; "the eastern portico had lion-headed capitals" | west portico: **bulls on the bare shaft**; east: lions on the bare shaft; no griffins |
| 3.2 | Great stair: 10 cm rise, 31 cm tread, 6.9 m wide, 111 per side | corrected | Shahbazi: each flight "ascends for sixty-three steps", then "another forty-eight"; "Each step is 6.70 m long, 10 cm high, and 38 cm wide" | 63 + 48, 38 cm, 6.70 m |
| 3.2 | Gate of All Lands: 4 columns, 16.5 m, double-bull capitals, three doors, bulls west, lamassu east | confirmed | Shahbazi: "four-columned square hall", columns "over 16.5 m", "two addorsed kneeling bulls"; Livius: "16½ meters", "A third entrance was to the south" | source note |
| 3.2 | Apadāna 36 + 3 × 12 = 72 columns; four corner towers | confirmed | Iranica "Apadāna" | — |
| 3.2 | North stair "(visible)" | corrected | §2.3 of the same file and the camera rule: north faces are hidden | "hidden" |
| 3.2 | Stair reliefs in two registers | corrected | Shahbazi: "three superimposed registers"; 23 delegations on the corresponding wing | three registers |
| 3.2 | Central panel: guards and sphinxes, but at 470 "the audience panel is still here" | confirmed + clarified | Shahbazi: Tilia showed the guards panel replaced the audience orthostats, which Artaxerxes I deposited in the Treasury; Livius "east stairs": the soldiers "replaced an older relief" of king and crown prince | 470 shows the audience scene; description fixed |
| 3.2 | Tačara: 12-column hall, portico on the south; DPa; decorated west stair later | confirmed | Shahbazi: "twelve columns", "portico on the south", Artaxerxes III added a staircase on the north-west | — |
| 3.2 | Hadiš: 36 columns, 12-column portico | confirmed | Shahbazi: "thirty-six columned", "twelve-columned portico on the north" | — |
| 3.2 | Tripylon shown finished | uncertain | Shahbazi: "must be attributed to Xerxes and Artaxerxes I" | note: may be unfinished in 470 |
| 3.2, 11 | Hall of 100 Columns: about 11 m; begun by Xerxes, finished by Artaxerxes I | corrected / confirmed | Shahbazi: "each nearly 14 m high", built "between 486 and 450"; north portico "double-headed man-bull capitals"; Livius: begun by Xerxes, finished by Artaxerxes I | 14 m, human-headed bull capitals |
| 3.2 | Darius's tomb façade, 30 throne-bearers, Gobryas spear-bearer, Aspathines bow-bearer | confirmed with nuance | Livius DNd: "Aspathines, the bowbearer, holds king Darius' battle-axe" (OP *vaçabara*, meaning debated) | note |
| 3.2 | Cyrus's tomb: six steps, gabled chamber, low door; Arrian's grove | confirmed | Arrian 6.29 (Chinnock, Wikisource, read): grove, stream, deep grass; narrow door; magi's house | door size and direction noted (direction from secondary sources: uncertain) |
| 3.7 | Pasargadae Gate R once inscribed "I, Cyrus the king, an Achaemenid" | confirmed + nuance | CMa; widely held to be a Darius-era addition (standard view; not re-read here) | note |
| 3.7 | Etemenanki seven stages | uncertain | Herodotus 1.181 (read): eight towers; Esagila tablet: seven levels | note |
| 3.7 | Babylon bridge, timber deck | confirmed | Herodotus 1.186 (read): blocks "bound together with iron and lead", planks laid by day and removed at night | note |
| 4.1 | Baradkama, treasurer, "present", "490s–460s" | **corrected** | CDLI catalogue of Cameron, OIP 65 (read, 19 entries): letters to Baratkama from Darius year 32 to Xerxes year 6 (490–480 BC); Xerxes years 12–19 letters go to **Mauš / Mawuš**; years 19–20 to Ratininda. [CDLI](https://cdli.earth/P537429) | figure becomes Mauš; Baradkama only as a memory |
| 4.1 | Artemisia commanded ships at Salamis | confirmed (standard; Hdt. 8.68–103 not re-read: Perseus blocked) | — | note: life after 480 unknown |
| 4.1 | Winged figure at Pasargadae "is not him" | corrected (overstated) | identity debated | "debated" |
| 4.1 | Darius "reorganised the empire into satrapies", canal | corrected (nuance) | satrapies existed under Cyrus; the canal was begun by Necho II | "reorganised", "completed" |
| 4.1 | Parnakka, Darius's uncle | uncertain | Iranica "Persepolis administrative archives" (summary): Henkelman: high nobility, "not necessarily a kinsman of the king" | softened |
| 4.1 | Irtašduna: one order, 200 jars of wine and 100 sheep | confirmed | Iranica "Persepolis Elamite tablets" (read): Darius "ordered the issue of 200 *marriš*" of wine and "100 sheep", Hallock 1969 no. 1795 | unit explained |
| 4.1 | Atossa = Udusana (Henkelman) | uncertain | not re-read | kept as proposal; naming clash with the child Udusana flagged |
| 4.1 | Tištrya, Yima, Ərəxša, Θraētaona, Saēna from the Avesta | confirmed in outline (Darmesteter, Yašt 8, as the researcher cited; not re-read) | the Avesta was written down in Sasanian times | caveat added to the figure rows |
| 4.2 | DSf: who did which crafts | confirmed | Livius DSf (read): stonecutters Ionians and Lydians; goldsmiths Medes and Egyptians; woodworkers Lydians and Egyptians; baked brick Babylonians; wall decorators Medes and Egyptians; cedar from Lebanon carried by Carians and Ionians from Babylon to Susa | cards say "at Susa" |
| 4.3 | Xerxes card: "Each spring", "beneath a parasol" | corrected | no text dates the audience; audience relief shows a canopy | card rewritten |
| 4.3 | Cyrus card: Alexander "found it guarded and honoured" | **corrected** | Arrian 6.29: the tomb "had been dug through and plundered"; Alexander had Aristobulus restore it | card rewritten |
| 6.1 | kandys, sarapis, anaxyrides as Median riding costume; empty sleeves | confirmed | Iranica "Candys" (Schmitt, read): "currently prevailing opinion"; empty sleeves on the reliefs; Xenophon *Cyr.* 8.3.13 purple tunic shot with white | — |
| 6.2 | Royal women's dress | uncertain (weak evidence, as stated) | no women on the Persepolis reliefs | — |
| 6.2 | "Faravahar" is a modern name | confirmed (with respect note) | — | wording |
| 6.5 | Herodotus 1.132 sacrifice without pipes | confirmed | Herodotus 1.131–132 (Rawlinson): no altar, no fire, no libation, no flute; a magus chants. The no-altar, no-fire claim contradicts the reliefs | note: Persian evidence first |
| 6.5 | Herodotus 1.136 boys taught to ride, shoot, speak the truth | confirmed | Herodotus 1.136: from five to twenty, three things | — |
| 6.5 | Herodotus 1.140 burial | confirmed | magi expose; Persians wax the body and bury it ("with reserve") | — |
| 6.7 | 23 delegations, gifts | confirmed; order and some names uncertain | Livius "east stairs" (read): same 23 peoples and gifts, listed in photo order | caveat |
| 6.10 | Cyrus Cylinder card | corrected (precision) | Cylinder lines 12, 17, 20–21, 30–32 (Livius, after Cogan/Schaudig, read): Marduk calls "Cyrus, king of Anšan"; entry "without fighting"; gods returned to Aššur, Susa, Agade, Ešnunna, Zamban, Me-Turnu, Der, Gutium; inhabitants gathered and returned; no mention of Jews or Jerusalem | card rewritten |
| 6.10 | Herodotus 8.98 on the relay riders | unverifiable here (Perseus blocked); standard passage | — | — |

### 1.2 Changes that affect art already built (Pārsa)

1. **`parsa.apadana`, west portico capitals: griffins → bulls.** `tools/artgen/sets/parsa/landmarks.py`
   line ~252 builds the west portico with `"griffin"`. Iranica ("Apadāna") and Shahbazi agree the
   west portico carried **double bulls set directly on the fluted shaft** (no bell and volute
   stage); the east portico **lions, also directly on the shaft**. The west portico is the one the
   default camera shows, so this is the most visible correction in the city. Both side porticoes
   should use a short protome capital (the toolkit's `"protome"` fraction, 0.15, fits better than
   the full `"bull"`/`"lion"` composite at 0.31); the north portico and the hall keep the full
   composite bull.
2. **`parsa.great_stair`: tread 38 cm, not 31 cm; width 6.70 m; 63 + 48 steps per side.** The
   built `GS_STEP = 1.4` design units: check that the lower flight is longer than the upper one
   (63 : 48) and that the run matches a 38 cm tread. Minor at this scale.
3. **`parsa.hall_100`, north-portico capitals: human-headed bulls.** Built as `"bull"`. Most of the
   portico is shown rising (`capital="none"`), so only the finished columns, if any, need a
   human-headed protome. Column height 13.5 m is consistent with "nearly 14 m".
4. **Apadāna north-stair central panel** (`parsa.apadana_stair_n`, hidden face; and any card art):
   in 470 it shows the **audience scene** (king enthroned under a canopy, crown prince, saluting
   official, incense stands), not the eight guards and sphinxes. Only matters for the view
   rotation and card illustrations.
5. **`parsa.baradkama` actor**: sprite can stay; rename the figure and card to **Mauš** (the treasurer
   of 470), or keep the id and change the displayed name and card. Baradkama may survive only as a
   memory.
6. **`parsa.udusana` actor** (child): its name is also the proposed Elamite name of Queen Atossa;
   renaming avoids confusion (owner's choice, not an error).
7. No change: Apadāna 19.5 m (`APA_COL`), Gate 16.5 m and bull capitals, Tačara and Hadiš plans,
   Darius's tomb, Cyrus's tomb (unless Stronach shows the door elsewhere than the model).

### 1.3 Changes that affect layouts (Pārsa)

1. **Tripylon** (c 87..93, r 71..78): may have been unfinished in 470 (Xerxes and Artaxerxes I).
   Layout unchanged; an optional scaffold prop would make it honest.
2. **Qanat line** (c 20..119, r 138..140): keep as nice-to-have; no qanat at Pārsa is dated to 470.
3. **Pasargadae** (world C 1176..1203, R 260..287): Cyrus's tomb door is reported on the north-west
   side; confirm before rotating `parsa.cyrus_tomb`.
4. No landmark is misplaced relative to the evidence read; positions against Schmidt's plan remain
   unchecked (see the note at the top).

### 1.4 Changes to card and figure text (Pārsa)

1. Xerxes card: "each spring" and "parasol" removed.
2. Cyrus card: Alexander found the tomb **robbed** and had it restored.
3. Cyrus Cylinder card: what it says, the cities it names, that it does not mention the Jews.
4. New card "A New Year at Pārsa?" with the fact, both sides and the late name.
5. Treasurer card: Mauš, not Baradkama.
6. Parnakka: no claim of kinship with Darius.
7. Darius: "reorganised" satrapies, "completed" the canal.
8. Aspathines: title meaning debated; holds the battle-axe.
9. Irtašduna: "jars" explained as *marriš* (about ten litres).
10. Hermon and all DSf citations: "at Susa".
11. Avestan figures: cards add that the hymns were written down much later.
12. Religion: Herodotus's "no altars, no fire" is shown as a Greek claim the reliefs contradict.

### 1.5 Naming the spring occasion at Pārsa (recommendation)

- Call the in-game event **"the spring audience"** (or "audience of the peoples"). Do not call it
  Nowruz, and do not call it "the New Year audience".
- Say as fact that the Persian administrative year began in the month *Ādukanaiša*, near the spring
  equinox.
- Give the New Year interpretation one card. Name both sides, including the Iranian historian
  Shapur Shahbazi, who supports it, and Nylander and Calmeyer, who reject it. State that
  the name Nowruz first appears in Middle Persian texts. End honestly: no one can yet prove it.
- Treat Nowruz with warmth as a living festival of hundreds of millions of people, never as a
  "myth" to be debunked. The question is only whether its story is documented at Pārsa in 470 BC.

---

## 2. Athens (`athens.md` and the Greek waypoints)

### 2.1 Claims checked

| § | Claim (before) | Verdict | Best source and what it says | Change made |
|---|---|---|---|---|
| 1 | 432 is the annual Panathenaia with procession, sacrifice and a new robe | uncertain | secondary summaries: Great Panathenaia every fourth year (434, 430); whether a peplos was given annually is debated | "perhaps" for the robe |
| 4.1, 7.2 | Rhapsodes recite Homer at "the Panathenaia" (in 432) | corrected | the rhapsodic contest belonged to the Great Panathenaia ([Plato] *Hipparchus* 228b; Lycurgus *Leocr.* 102; not readable here, secondary summaries agree) | informal recital in 432 |
| 3.2 | Stoa Poikile: four paintings; "captured shields hanging" | **corrected** | Pausanias 1.15 (Jones, theoi.com, read): paintings of Oinoe, the Amazons, Troy, Marathon; shields from Scione (421) and Sphacteria (425) | no shields in 432 |
| 3.7 | Telesterion: "Iktinos's Periclean rebuilding" | corrected | Plutarch *Pericles* 13 (LacusCurtius, read): Koroibos began it, Metagenes finished the frieze and upper columns, Xenokles the lantern; Iktinos not named | architects named; Iktinos as an abandoned design |
| 3.7 | Athenian Treasury at Delphi of Pentelic marble | **corrected** | secondary sources agree: entirely **Parian** marble; date debated 510–480 | Parian |
| 4.1 | Pheidias "present (disputed)" in the yard | corrected (presence) | Plutarch *Pericles* 31 (read): charge of embezzling gold, "died there of sickness" in prison; Philochorus (scholion, via Wikipedia/Spivey): killed by the Eleans after making the Zeus; workshop at Olympia active around 430 (Perseus Olympics site, summary) | memory figure; card gives both versions |
| 4.1 | Pericles's helmet hid a long head | confirmed | Plutarch *Pericles* 3 (read) | — |
| 3.2 | Odeion imitates the Persian king's tent | confirmed | Plutarch *Pericles* 13 (read): "an exact reproduction of the Great King's pavilion" (as reported) | — |
| 4.3 | Aspasia's son needed a special vote | confirmed | Plutarch *Pericles* 37 (read): the Athenians let Pericles enrol his illegitimate son | — |
| 4.2 | Kephalos "with more than a hundred workers" | uncertain | the 120-worker figure is usually cited for his sons' workshop in 404 (Lysias 12; not re-read) | number removed from card |
| 4.2 | Scythian archers' red rope; red-marked lose pay | uncertain | Aristophanes *Acharnians* 22 (rope), later scholia (fine); not re-read | softened |
| 6.10 | Parthenon base rises 6–7 cm in the middle | corrected (incomplete) | Stevens's survey (Cambridge UP appendix, summary): 0.103 m on the north flank; about 6 cm on the short ends | both figures; purpose "still argued" |
| 1 | Stoa of Zeus "only rising" in 432 | uncertain | dated c. 430–420 (Ancient Athens 3D, as the researcher cited) | "at most a fresh building site, possibly not begun" |
| 1 | Parthenon complete; Parthenos dedicated 438; pediments finished 432; Propylaia 437–432 | confirmed in outline (building accounts as summarised in standard works; not re-read) | — | — |
| 1 | Erechtheion 421–406, Nike temple 420s, no stone theatre, Pnyx phase II c. 404 | confirmed in outline (standard dates; not re-read) | — | — |
| 3.1 | Parthenon 8 × 17, 46 outer columns, 10.4 m; metope subjects; pediments | confirmed in outline (WHE as cited; not re-read) | — | — |
| 4.3 | Solon "I grow old, always learning many things" | confirmed in outline (Solon fr. 18 West; not re-read) | — | — |
| 4.3 | Thucydides 2.65 "in name a democracy" | unverifiable here (Perseus blocked) | — | — |
| 6.1 | Thucydides 1.6, Ps.-Xenophon 1.10, Thucydides 2.13 figures | unverifiable here (Perseus blocked) | standard passages | — |
| 4.1 | Socrates at Potidaea; saves Alcibiades | unverifiable here (Plato *Symposium* 219e–220e; not re-read) | — | — |
| 4.3 | Medea in 431 came third | unverifiable here (hypothesis to the play; not re-read) | — | — |
| 4.1 | Meton's solstice of 432 | unverifiable here (Ptolemy, *Almagest* 3.1; not re-read) | — | — |
| sets 4.2 | Delos: graves removed to Rheneia in 426/5, after our date | confirmed in outline (Thucydides 3.104; not re-read) | — | — |
| sets 4.2 | Corcyra allied to Athens since 433 | confirmed in outline (Thucydides 1.44; not re-read) | — | — |

### 2.2 Changes that affect art already built (Athens)

1. **`athens.stoa_poikile`: remove the captured shields.** `tools/artgen/sets/athens/agora.py`
   line ~144 builds it with `shields=7`; set `shields=0` (and drop "captured shields hung above"
   from the docstring at line ~141). The shields date from 425 and 421.
2. **`athens.pheidias` actor**: keep the sprite; change presence to a dusk memory in the sculptors'
   yard (and translucency if memories use it), with the new card.
3. **`athens.athenian_treasury`** (proposal, not yet built): Parian marble, a cooler, more
   translucent white than Pentelic's warm tone.
4. **`athens.telesterion`**: no change to the look (walls up, roof unfinished stays the honest
   choice).
5. **`athens.rhapsode` actor**: no art change; card and routine change only.
6. **`athens.stoa_zeus`**: optional: show fewer columns (pegged-out foundations), since it may not
   have been begun in 432.

### 2.3 Changes that affect layouts (Athens)

1. **Stoa of Zeus site** (c 20..23, r 38..48): keep the footprint, but as foundations at most.
2. No landmark found misplaced or anachronistic beyond the above; Pnyx phase I orientation, the
   theatre facing south and the Stoa Poikile facing south agree with the standard reconstructions
   (not re-checked against the Agora publications).

### 2.4 Changes to card and figure text (Athens)

1. Pheidias: memory, both ancient versions.
2. Rhapsode: the Homer contest is a Great Panathenaia event; in 432 an informal recital.
3. Kephalos: no workforce number.
4. Toxamis: the fine as "ancient commentators said".
5. Curvature card: about 6 cm on the ends, about 10–11 cm on the long sides; purpose debated.
6. §1 festival note: peplos "perhaps".

---

## 3. Rome (`rome.md` and the Roman waypoints)

### 3.1 Claims checked

| § | Claim (before) | Verdict | Best source and what it says | Change made |
|---|---|---|---|---|
| 1 | The Parilia, "which Hadrian renamed the Romaea" | corrected | Athenaeus 8.361f (Gulick, LacusCurtius, read): "the festival of the Parilia, as it used to be called, though it is now called the Roman Festival", linked to the temple of the Fortune of Rome built by Hadrian | "now called" (by c. AD 200) |
| 1 | Venus and Roma begun c. 121, dedicated 135, finished by 141; the Colossus moved by Decrianus with elephants | confirmed in outline (HA *Hadrian* 19 and the researcher's sources; not re-read) | the 121 start is inferred | note |
| 1 | Pantheon c. 114–128, shown complete | confirmed in outline (brick-stamp arguments as summarised; not re-read) | — | — |
| 1 | Hadrian in Italy 125–128; presence on 21 April 126 not recorded | confirmed (as stated) | — | card must say "imagined" |
| 3.1 | Pantheon dome "covered with gilded bronze tiles" | uncertain | the bronze tiles are recorded (removed in 663); gilding is not secure (not re-read) | "bronze tiles", gilding a choice |
| 3.7 | Ostia: the square of the guilds "with mosaics of each guild's emblem" | **corrected** | ostia-antica.org (regio II.vii.4, read): "Most mosaics were installed in the late second century" | plainer floors in 126 |
| 4.1 | Marcus Annius Verus "aged 5" | **corrected** | *Historia Augusta*, *Marcus* 1.5 (LacusCurtius, read): born the sixth day before the Kalends of May (26 April) in AD 121, on the Caelian; 1.10: Hadrian called him Verissimus after his father's death | aged four, five on 26 April |
| 4.1 | Diocles: Lusitanian, born 104, began 122 with the Whites, 1,462 wins | confirmed (secondary: Wikipedia citing CIL VI 10048) | first win 124; six years with the Whites, so still a White in 126 | — |
| 4.1 | Cloelia's equestrian statue on the Via Sacra | uncertain | Dionysius 5.35 (LacusCurtius, read): "This statue I found no longer standing"; Plutarch *Publicola* 19 (summary): stood on the Via Sacra, some said it was Valeria | note: presence in 126 uncertain |
| 4.2 | Vigiles: "Freedmen who served six years … earned citizenship" | corrected | lex Visellia via Gaius 1.32b (secondary): for Junian Latins (informally freed); later three years | card wording |
| 4.2 | Barge "about two days" upstream | unverifiable | no source given or found | softened to "a few days" |
| 4.3 | Hadrian "the first emperor to wear a beard" | corrected (overstated) | earlier emperors appear with light or mourning beards (general knowledge; not re-read) | "whose portraits always show a full beard" |
| 6.2 | Juvenal: "the poor wore [the toga] only for their funerals" | **corrected** | Juvenal 3 (Ramsay, read): "many parts of Italy … in which no man puts on a toga until he is dead" | about Italy's country towns |
| 7.2 | Parilia: "at dawn … flocks sprinkled with water" | **corrected** | Ovid *Fasti* 4 (Kline, read): "purify your sated sheep at twilight"; "sprinkle the ground with water"; sulphur smoke; olive, pine, juniper; prayer "four times, facing east"; hands washed in dew; leaping "over the crackling heaps of burning straw"; fumigants from Vesta (horse blood, calf ash, bean stalks) | rite rewritten |
| 4.3 | Plotina: Hadrian wore mourning nine days | unverifiable here (Dio 69.10; not re-read) | — | — |
| 4.2 | Seneca: the Senate rejected a uniform for slaves | unverifiable here (*De clementia* 1.24; not re-read) | — | — |
| 4.2 | Apion's letter (BGU II 423) | confirmed in outline (standard; not re-read) | — | — |
| 4.3 | Scipio alone with Jupiter before dawn (Livy 26.19) | unverifiable here (not re-read) | — | — |
| 4.1 | Apollodorus: Dio's story doubted | confirmed (as stated: Dio 69.4; doubts in modern work) | — | — |
| 4.1 | Cornelia's base (CIL VI 10043), Pliny 34.31 seated statue | confirmed in outline (researcher's Kajava source; not re-read) | — | — |
| 6.5 | Brick stamps naming the consuls of 123 | confirmed in outline (standard; not re-read) | — | — |
| world 6 | Brundisium "two columns" vs one column in `rome.md` | corrected (consistency) | two stand today, dates debated | `world.md` aligned |

### 3.2 Changes that affect art already built (Rome)

The `rome` set is in progress in the working tree (uncommitted art by the art agent), so these are
for that agent:

1. **`rome.ostia_guilds`**: `tools/artgen/sets/rome/ostia.py` (line ~106) gives each office a
   black-and-white emblem mosaic. Most of those mosaics are late 2nd century; for 126 use plain or
   simple floors, or keep a few emblems and label the card "most of the mosaics seen today are
   later".
2. **`rome.pantheon`**: `campus.py` line ~54 draws "gilded bronze tiles". Bronze tiles are
   certain; gilding is not. A warm bronze with a little sheen is the safer look.
3. **`rome.marcus`** actor: no art change (a child of four or five looks the same); card only.
4. No change needed for the Colosseum, the Forum temples' orientations, Trajan's Column, Circus
   Maximus or the Venus and Roma site from what was checked.

### 3.3 Changes that affect layouts (Rome)

1. **Cloelia statue** (on the Via Sacra; no plan coordinates given): optional; if placed, its card
   carries the doubt.
2. **Ostia guild square** (world C 100..170, R 184..239): no layout change.
3. No landmark found in the wrong place or anachronistic among those checked; the Temple of Divus
   Traianus position stays flagged as debated (nice-to-have).

### 3.4 Changes to card and figure text (Rome)

1. Marcus: "nearly five".
2. Hadrian: beard wording; presence "imagined".
3. Valens (vigiles): Junian Latins.
4. Mulvius: "a few days".
5. Cloelia: statue's presence uncertain, Valeria variant.
6. Parilia event and the "Romaea" wording.
7. Toga row: Juvenal is about country Italy.

---

## 4. Waypoints (`docs/design/sets/world.md` §4 and the city tables)

| Waypoint | Claim | Verdict | Source | Change |
|---|---|---|---|---|
| Babylon | "the timber deck lifted at night is in later commentary, not certain" | **corrected** | Herodotus 1.186 (read): planks laid by day, removed at night against thieves | sets/world.md and persepolis.md |
| Babylon | Etemenanki seven stages | uncertain | Herodotus 1.181: eight towers | note |
| Euphrates crossing | round hide boats (Herodotus 1.194) | confirmed with nuance | they came downriver from Armenia and were broken up at Babylon | note |
| Pasargadae | magi guardhouse, a sheep a day | confirmed and filled in | Arrian 6.29 (read): also flour, wine and a monthly horse; office hereditary since Cambyses | note |
| Pasargadae | Cyrus's tomb door direction | uncertain | north-west in secondary sources only | flagged |
| Delphi | no theatre in 432 | confirmed in outline (the stone theatre is 4th century; standard; not re-read) | — | — |
| Delphi | Athenian Treasury in Pentelic marble (athens.md) | **corrected** | Parian marble | athens.md |
| Eleusis | Telesterion by Iktinos | corrected | Plutarch *Pericles* 13 | athens.md |
| Delos | before the purification of 426/5 | confirmed in outline (Thucydides 3.104; not re-read) | — | — |
| Ephesus | archaic Artemision with Croesus's drums; Pliny's 120 years | unverifiable here (Herodotus 1.92, Pliny 36.95 not re-read) | — | — |
| Corinth | Apollo temple c. 540, 6 × 15 monolithic | unverifiable here (not re-read) | — | — |
| Sardis | reed and reed-roofed houses (Herodotus 5.101) | unverifiable here (not re-read) | — | — |
| Halys | gates and a fort (Herodotus 5.52); Croesus's bridges (1.75) | unverifiable here (Perseus blocked) | — | — |
| Gordion | Tumulus MM c. 740 BC, about 53 m | unverifiable here (not re-read) | — | — |
| Persian Gates | site debated | confirmed (as stated) | — | — |
| Ostia | guild mosaics | **corrected** | late 2nd century | rome.md |
| Capua | Hadrian restored, Antoninus dedicated the amphitheatre | unverifiable here (CIL X 3832 not re-read) | — | — |
| Brundisium | one or two columns | corrected (consistency) | — | world.md |

---

## 5. Counts

| City | Confirmed | Corrected | Uncertain | Unverifiable |
|---|---:|---:|---:|---:|
| Pārsa (incl. Persian waypoints) | 25 | 14 | 6 | 4 |
| Athens (incl. Greek waypoints) | 10 | 6 | 4 | 7 |
| Rome (incl. Roman waypoints) | 8 | 8 | 2 | 5 |

"Confirmed" includes the rows marked "confirmed in outline" (standard facts whose primary passage
could not be opened this time); a stricter count would move those to "unverifiable". The waypoint
rows of §4 are counted under their era, without counting twice a claim already in a city table.

---

## 6. What remains genuinely uncertain, and how to present it

Ordered by how visible they are in play.

1. **The New Year at Pārsa.** Present as §1.5: an event called "the spring audience", one card with
   both sides.
2. **Pheidias in 432.** A memory with both ancient versions; never a busy sculptor at the yard.
3. **Hadrian, Sabina and Antinous in Rome on 21 April 126.** Plausible, unrecorded. Their cards say
   "the game imagines them here for the festival".
4. **The annual peplos and the 432 festival programme.** The procession and sacrifice are safe; the
   robe is "perhaps"; Homer contests and prize games are Great Panathenaia events.
5. **Apadāna delegation names and order.** Use "probably" for doubtful peoples; no numbering on
   cards.
6. **Royal women's dress at Pārsa.** Reconstructed from seals and Anatolian art; the card says so.
7. **The Tripylon and the Stoa of Zeus.** Both may not have been finished (or begun) at the chosen
   moments; the bibles name the choice.
8. **The Old Temple of Athena after 480.** Shown with a repaired west chamber; card: "scholars
   disagree".
9. **Atossa = Udusana; Parnakka's kinship.** Proposals; cards avoid them or say "some scholars".
10. **Gilding of the Pantheon's bronze tiles; Cloelia's statue in 126.** Choices, labelled.
11. **Qanats at Pārsa.** Known in the empire (Egypt), not dated at Pārsa.
12. **Avestan figures.** The hymns are old but were written down in Sasanian times; cards say the
    storyteller tells "old Iranian tales" without claiming these exact words were told in 470.

A rule for all cards that grows out of this check: when a card cites an inscription made for one
place (DSf at Susa) or a writer centuries later (Arrian, Athenaeus, the *Historia Augusta*), say
where or when in a few words.

`sources.md` now marks every source with whether its text was read in this check and lists the
sources the check added.
