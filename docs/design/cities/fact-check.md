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
| 2.5 | Achaemenid qanats debated; Polybius 10.28 | confirmed + filled in | Polybius 10.28 (Loeb, LacusCurtius, read): local story of five generations' use for whoever brought water; Wuttmann et al.: qanat at ʿAyn Manawir (Kharga, Egypt) in use by the late 5th c. BC, dated by Demotic ostraca of Artaxerxes I | card note: technique known in the empire; none dated at Pārsa |
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
