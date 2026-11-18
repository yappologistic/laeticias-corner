# Seasons across the world

Spring, summer, autumn and winter for every region of the one connected world: the home corner,
Rome, Athens, Pārsa, the waypoint towns and every stretch of land and sea between them. This
document decides how the seasons work, what each season looks, sounds and feels like in each
place (with the history behind it), what each system changes, how it is built inside the page,
memory and frame budgets, and who builds what. It is written for the art, engine, audio, world
data and QA lanes, who can work from it in parallel.

Read first: `CLAUDE.md` ("Where this is going", the content contract, "Game rules", "Performance"),
`living-corner.md` R4 (the home region's seasons), `living-world.md` §4–§6 (one clock, climates,
events, weather), `look.md` (the rendering plan), `world-tech.md` §1.2, §1.7, §2.6, §4.5–§4.6, §4.14
(pages, terrain, region files, themes, budgets) and the three city bibles (§6.2 dress, §6.3 work,
§6.8 the year, §8 light and season).

Contents: 0 decisions · 1 the calendar · 2 climates · 3 what changes, system by system · 4 how it
is built inside the budgets · 5 transitions · 6 data · 7 work plan · 8 notes for the bibles and the
other design documents · 9 sources.

---

## 0. Decisions at a glance

| Question | Decision |
|---|---|
| One calendar or many | **One world calendar** turns everywhere. Each city's famous day is a festival on its true date inside the matching season (the Parilia on spring day 2, the Panathenaia on summer day 2, the spring audience through spring). The per-region season pins in today's region files go. |
| Length | Unchanged: 3 days a season, 12 days a year. **Each calendar day stands for one month**, March to February, so festivals, farm work, floods and sailing fall on their real months. |
| Climate | Fifteen climates replace today's four. Every region file names one. A climate maps each month to a look for each kind of plant and ground, a snow line, water levels, weather, sailing and travel. |
| Looks | Sprite looks become **states** (`@fresh`, `@dry`, `@turn`, `@bare`, `@bloom`, `@ripe` …). The climate decides which state a plant or ground shows in which month. Home's `@spring`…`@winter` keys keep working as the home climate's states. |
| What is engine | grade, haze and day length by region and month; snow cover (ground, evergreens, backdrops, and roofs on the shader path); wet, muddy and dusty ground; flood, low water, dry riverbeds and ice; falling leaves, petals, chaff and snow; who is out, what they wear, what they do, what sails and what travels. |
| What is generator | every plant and ground state from the same models (recoloured foliage, bare branches, blossom, crop stages, snow on conifers), snow, ice, flood and leaf-litter overlays, snow caps for mountain backdrops, cold and hot dress variants of the main walkers, and one "snow catcher" bit in every sprite. |
| What is bespoke modelling | a handful of seasonal props: hulls hauled ashore, threshing and winnowing gear, olive-harvest nets and ladders, the vintage, winter braziers and festival stalls, crane flocks, stork nests. |
| Cost | About 0.8 Mpx of new sprites for each city set and 2.3 Mpx for the world set. **No set gains a page.** The world page grows by 512 rows (+8 MB). Resident texture memory stays inside 320 MB, and drops if half-resolution shadows land first. |
| Player control | One **Set the scene** panel in the glass UI (key `K`, or click the title card): time, weather (here), wind and season, a "Follow the world" reset, and **Go to the moment** for the region in view. |
| First visible result | Athens and Attica in four seasons (gold summer, first rains, green winter with snow on Parnes, a spring of flowers), then Pārsa with real snow, then Rome. |

---

## 1. The calendar

### 1.1 Options weighed

| Option | Seasons show everywhere | Each city keeps its identity and festival | Honest to history | Simple for the player | Verdict |
|---|---|---|---|---|---|
| **A. One world calendar.** It turns everywhere; each city's famous day is its festival inside the matching season | yes: every region shows all four, by its own climate | yes: the famous day comes round every year on its true month; captions name it; "Go to the moment" reaches it | yes: Rome, Athens and Pārsa are all northern Mediterranean or Near Eastern places, so the same month really was the same season in all three | yes: one season, one sky, the rule home already uses | **chosen** |
| B. Seasons offset per region (by climate, or by a "hemisphere of feeling", so that each city sits in its famous season more often) | yes, but out of step | partly | **no**: the three cities share a hemisphere and nearly the same months; an offset would put snow on the Zagros while the Mesopotamian plain beside it is in harvest gold for the wrong reason | no: the overview would show summer and winter side by side across a mist band; weather fronts crossing a seam would change season mid-cloud | rejected |
| C. Season chosen by the player for each region | only where the player sets it | yes | neutral | no: more controls, a patchwork world, travel that jumps seasons | rejected (the world-wide season pin already lets anyone hold the whole world in one season) |
| D. Today's data: each city frozen in its moment (region `season` fields) | **no** | yes | no | yes | rejected: it breaks the owner's requirement outright |

Why A is honest: the cities are memories of different centuries, but each memory is a whole year
of a real place. Athens is not only its high summer: its winters were green and wet and its
hills turned gold in June. Rome's April showers, Pārsa's cold bright winters and short green spring,
and the Mesopotamian flood in April and May all happen on their own months under one calendar.
A city spends a quarter of its time in its famous season and its famous day comes once a year,
which makes the moment an occasion instead of wallpaper.

### 1.2 Days, months and years

- **Unchanged from home:** `clock.day` counts days; a day begins at midnight; season index
  `(day / 3) mod 4` (spring, summer, autumn, winter); season day `day mod 3 + 1`; new worlds start
  on spring day 1 at `t = 0.2`; the calendar moves only while the clock runs (and while it is
  pinned, one day passes per day length of play, so pinning never holds the seasons back).
- **New: one day is one month.** `month = day mod 12`, 0 = March:

| Season | Day 1 | Day 2 | Day 3 |
|---|---|---|---|
| Spring | March | April | May |
| Summer | June | July | August |
| Autumn | September | October | November |
| Winter | December | January | February |

  These are the meteorological seasons. The month is the unit the climates, festivals, farm work,
  water, sailing and travel are authored in (§6). Players see the season and its day as today;
  the calendar line may add the region's own month name where the bible attests it (Aprilis;
  Mounichion; Ādukanaiša), as a nice-to-have.
- **Each city's year runs round its moment** and repeats, as memories do. Captions and cards use:

| Region group | Spring and summer | Autumn and winter |
|---|---|---|
| Rome and the Roman-time stretch | AD 126 | AD 126/127 (January and February: AD 127) |
| Athens and the Greek-time stretch | 432 BC (the last spring and summer of peace) | 432/431 BC: still at peace; the war begins in the spring of 431, which the calendar never reaches because spring returns to 432 |
| Pārsa and the Persian-time stretch | c. 470 BC | c. 470/469 BC |
| Home | timeless | timeless |

- **Week days** stay `day mod 4` (`living-world.md` §4.1). Both cycles keep running; a festival
  names its season and season day, so it falls on one month a year.

### 1.3 The famous day and the festival calendar

- The festival calendar is the real calendar compressed one day per month. A festival entry keeps
  its shape `{id, season, day, hours}`; `day` is the season day, which is the month. §3.10 lists
  every city's festivals by month, with the corrections the data needs (§8).
- Each region file gains a `moment` (§6.2): the season and day of its famous day, the festival
  that makes it, and the caption shown while it runs ("Roma · the Parilia, 21 April AD 126"). On
  other days the caption names the era and the season ("Roma · AD 126 · winter").
- The life layer stops pinning regions to a season (`regionSeason` in `src/life/session.cpp`
  reads the region `season` field today). Every region uses the world season, or the player's pin.

### 1.4 Pinning

| Pin | Scope | Behaviour |
|---|---|---|
| Clock (exists) | world | holds the hour; days still pass per day length of play |
| Season (exists: "Follow the days" / "Always …") | world | replaces the season index everywhere; the season day still advances, so festivals of the pinned season still come round and the month looks within the season still progress |
| Wind (new) | world | Natural / Calm / Breeze / Windy / Gale: holds the wind strength; direction stays natural |
| Weather (exists, `living-world.md` §4.4) | the region under the camera | Natural / Rain here / Clear here, plus the kinds the climate allows in that month: Snow here, Fog here, Dust here, Storm here |

A season set by pin swaps looks in a 3-second wave and glides the grade over 2 seconds (§5.2).

### 1.5 The "Set the scene" panel

One quiet glass panel replaces the calendar popover. It opens from a click on the title card or
with `K`, and closes with Esc, `K` or a click outside. `C` (cycle the clock) and `N` (cycle the
weather) keep working as shortcuts to the same settings.

```
┌ Set the scene ─────────────────────────────────────────────── ✕ ┐
│ Ἀθῆναι · 432 BC · winter, day 2 of 3                             │
│                                                                  │
│    TIME           WEATHER         WIND            SEASON         │
│   ╭─────╮        ╭─────╮        ╭─────╮         ╭─────╮          │
│   │  ◐  │        │  ☁  │        │  ≋  │         │  ❄  │          │
│   ╰─────╯        ╰─────╯        ╰─────╯         ╰─────╯          │
│  ‹  Dusk  ›    ‹ Natural ›    ‹ Breeze ›     ‹  Winter  ›        │
│   • held        in Athens      everywhere     • held             │
│                                                                  │
│  ( Follow the world )                                            │
│ ──────────────────────────────────────────────────────────────── │
│  The moment: the Panathenaia, high summer        ( Go there )    │
│  Speed   [ Hold ] [ 1× ] [ 2× ] [ 4× ]                            │
└──────────────────────────────────────────────────────────────────┘
```

Behaviour:

- Four cards, each with a large icon, the current value between ‹ › arrows, and a scope line.
  Arrows (or the mouse wheel over a card, or Left/Right with keyboard focus) step through the
  values; the first value of each card is the natural one ("Follow the clock", "Natural",
  "Natural", "Follow the calendar"). A held value shows a dot and "held".
- **Weather** lists only what the region in view can have in this month: no "Snow here" in
  Babylon, no "Dust here" in a green Roman April. Its scope line names the region.
- **Season** values: Follow the calendar, Spring, Summer, Autumn, Winter. The header shows the
  effective season and day.
- **Follow the world** returns all four cards to natural in one step; it is disabled when nothing
  is held.
- **Go to the moment** appears when the region in view has a `moment`. It moves the calendar
  **forward** to the next day with the moment's season and season day (at most 11 days), clears
  the season pin, and sets the clock to the festival's first hour; the clock keeps running. A
  toast confirms ("Summer, day 2: the Panathenaia"). The calendar never moves backwards and
  nothing is taken away: home growth runs on play time, not on the calendar.
- **Speed** is the existing 1× / 2× / 4× / Hold row (`living-world.md` §8.4).
- Every control has hover, pressed, disabled and keyboard focus states; strings live in
  `src/ui/strings.hpp` (§6.4); the panel scales with the interface size like the rest of the UI.
- Save: `season_pin` and the clock pin exist; add `wind_pin` (`"auto"` or a level). Weather pins
  stay as they are today.

---

## 2. Climates

### 2.1 The fifteen climates and who uses them

Today's region files name four climates (`rome`, `athens`, `parsa`, `world`), which puts Babylon,
the Zagros snows and the Syrian steppe under Pārsa's weather. They become fifteen. Every region
file names exactly one (validator, §6.5). A climate that is mostly sea inherits a land climate for
its islands and coasts and adds a sea block.

| Climate | Character | Region files |
|---|---|---|
| `home` | cool, green, northern; the corner's existing seasons | `seam_dell` (and the home region) |
| `med_green` | Mediterranean with a green spring and early summer, gold late summer, mild wet winter, snow only on the hills | `rome`, `latium_italy`, `ostia`, `alban_mount`, `brundisium`, `ionia_lydia`, `ephesus`, `sardis`, `seam_ionia` |
| `med_dry` | Attic: the driest; hills gold and grey from June to October, green from November to April; snow on the mountains, rarely in the basin | `athens`, `attica_north`, `academy`, `eleusis`, `corinth`, `greece`, `delos` |
| `highland` | Mediterranean mountains: beech and oak woods, snowy winters, summer pastures | `apennines`, `arcadia`, `delphi` |
| `thracian` | continental north Aegean: cold winters with snow on the plain, green summers | `thrace` |
| `levant` | Levantine coast under snowy mountains (the cedars) | `east_med` |
| `anatolian` | high continental plateau: long snowy winters, a short green spring, gold steppe summers | `anatolia`, `halys` |
| `high_mountain` | the Zagros and Taurus: snow from November to April, peaks white most of the year, passes hard in deep winter | `zagros`, `taurus`, `persian_gates` |
| `mesopotamian` | alluvial plain: mild green winter, harvest in April and May with the flood, scorching dusty summer, date harvest in autumn | `mesopotamia`, `babylon`, `euphrates_crossing`, `susiana`, `susa` |
| `steppe` | Syrian steppe: a brief green flush after winter rain, bleached the rest of the year | `syrian_steppe` |
| `fars` | Pārsa at 1,600 m: cold bright winters with frost and some snow, a short green spring, hot dry summers with dust | `parsa` |
| `plateau` | the higher plateau north of Pārsa: colder and snowier than Fārs | `iran_plateau`, `pasargadae` |
| `sea_west` | inherits `med_green`; Tyrrhenian, Adriatic and Ionian waters; winter storms, the bora in the Adriatic | `tyrrhenian`, `adriatic`, `ionian_sea`, `seam_ionian` |
| `sea_aegean` | inherits `med_dry`; the Etesian north wind (meltemi) in July and August | `aegean`, `saronic` |
| `gulf` | inherits `mesopotamian`; the head of the Persian Gulf, the summer north-west wind (shamal) | `persian_gulf` |

Seams take their neighbours' climates through the existing influence weights (`world-tech.md`
§4.6); a region file's climate covers its whole rect.

### 2.2 What each season is like, climate by climate

Day lengths are given once in §3.11. "Level" is the world's elevation unit (16 px).

| Climate | Spring (Mar–May) | Summer (Jun–Aug) | Autumn (Sep–Nov) | Winter (Dec–Feb) |
|---|---|---|---|---|
| `home` | as `living-corner.md` R4.2: grass with tiny flowers, blossom, apple blossom, petals, showers | full leaf, warm, clear, crickets at night | oak, apple and blossom turn, leaves fall at 3×, wind and rain | snow instead of rain, bare broadleaves, snow-capped pines, the pond's rim icing over in deep winter (new, §3.4) |
| `med_green` (Rome, Latium, Campania, Ostia, Ionia, Lydia) | fresh green Campagna, poppies and wildflowers in April and May, planes and poplars in new leaf, figs and vines leafing, green wheat; showers, morning mist on rivers, the west wind (Favonius); swallows back; frogs at night; Tiber high and yellow-turbid in March, falling | grain ripens in June and is cut in June and July, golden stubble and threshing floors by July; hills turn gold from July; hot, clear, heat haze, thunder over the inland hills; cicadas by day, crickets at night; Tiber low and greener, wide mud banks | vintage in September and October (vines laden, then red-gold leaves), planes and poplars yellow in November with falling leaves, first rains in October green the ground again, ploughing and sowing in October and November, olive harvest begins in November; starling flocks wheel at dusk; cranes overhead | planes, poplars, figs and vines bare against evergreen stone pines, cypresses, olives, laurels and holm oaks; grass green; rain and cold clear days; snow on the Apennines and the Alban summit in view; in the city at most a rare dusting gone by noon; Tiber high and muddy over its banks; smoke from hearths and braziers; ships laid up |
| `med_dry` (Athens, Attica, Corinth, the Cyclades) | flowers everywhere in March and April (anemones, poppies, asphodel spikes), barley tall and green, ripening in May; almond already past its blossom (January and February); clear and breezy; swallows; the Ilissos still runs | the barley harvest is over by June; gold stubble, dry gold and grey hills, dust on paths, asphodel stalks dry; silver olives; cloudless and hot; the meltemi from the north-east in the afternoons (July and August); cicadas loud at midday; the Ilissos a line of dry stones | September stays dry and gold (vintage, Mysteries); the first rains come in October and November and darken the ground, then a green flush; planes and poplars yellow in November; cranes call overhead and ploughing begins; olive harvest from November | the hills turn green; winter rain in showers; snow on Parnes, Hymettos and Pentelikon in view, in the city a rare flurry that does not settle; planes, figs and vines bare; the Ilissos flows; olive harvest and pressing to January; almond blossom in January and February; triremes in their ship sheds |
| `highland` (Apennines, Arcadia, Delphi) | snow lingering on the tops into April and May, beech woods bare until May then bright new green, meltwater streams loud; flocks arrive on the drove roads in May | green upland pastures with flocks and shepherds, hay in July, cool clear air, thunderstorms on the ridges | beech woods copper in October, bare in November; flocks leave in October; mist in valleys | snow down to the valley floors from December to February; woods bare and snowy; empty pastures; low cloud on the ridges; at Delphi the god's winter months (§3.10) |
| `thracian` (Thrace, the Hellespont) | late green (April), storks, grain ships coming down from the Black Sea once sailing opens | green summers, wheat ripening in July | early autumn colour, ploughing in September | cold; snow settles on the plain in January; bare woods; grain traffic stops with the sailing season |
| `levant` (Cyprus, the Levant coast) | green coast, flowering maquis | dry gold coast, hot, steady sea wind | first rains in October | green coast under snow-covered mountains (the cedar ridges white from December to April) |
| `anatolian` (Phrygia, the Halys, Cappadocia) | snow gone from the plain in March; a short green flush in April and May with flowers; storks return; the Halys high and red with meltwater | green turning gold steppe, wheat cut in July, threshing in August; wind and racing cloud shadows; heat shimmer at noon | brown steppe, sowing in September and October, poplars gold in October; cranes passing south | snow cover on the whole plateau from December to February, frozen margins on streams and lakes, bare poplars, smoke from villages; caravans fewer; Mount Argaios white |
| `high_mountain` (Zagros, Taurus, the Persian Gates) | snow line climbing from level 10 to 13; meltwater torrents milky turquoise; Zagros oaks leaf in May; flowers (tulips, irises) on the slopes | snow only on the highest peaks; upland pastures with herders; clear, cold nights | oaks turn brown-gold in October; first snow on the tops in October and November | snow to level 9; gorges with ice; the road through the Gates in snow (Alexander's army fought there in snow and ice in January 330 BC); few caravans, couriers still riding |
| `mesopotamian` (Babylon, the Euphrates, Susa, Susiana) | barley green in March, ripe and cut in April, the flood rising in April and May over the low ground, rivers red-brown; date palms hand-pollinated; storks | from June scorching heat, the plain bleached, dust and the north-west wind; work at dawn and dusk; rivers falling to sandbars by August; at Susa, heat that Strabo says could roast a lizard crossing the street | date harvest in September and October (climbers in the palms, clusters of fruit); ploughing and sowing with seeder ploughs from October as the canals are cleared | mild, green barley in the fields from December, winter rain, morning fog on the marshes, wintering geese and cranes on the reed beds; at Babylon, by Greek report, the king's winter residence |
| `steppe` (Syrian steppe) | a brief green flush in February to April with herds moving out into it | bleached, heat shimmer, dust breezes; herders back at the wells and the river | dry, still | cold nights, occasional rain and a first green in February |
| `fars` (Pārsa) | the moment: the plain new green with young barley, almond and pomegranate blossom, tulips and lilies, channels full with snowmelt, snow on the ridges, storks on the plain; rare towering showers | barley ripe and cut in June, threshing floors and chaff in the wind; gold plain, dust breezes after dry days, heat; channels low; from July the court away and the terrace quiet | ploughing and sowing in October and November; planes and poplars gold in November; offerings of Bāgayādi; clear dry air | frost most nights, cold bright days, snow on the mountain behind the terrace all winter and on the plain on a few days in January (it melts within a day or two); thin ice on channels at dawn; bare poplars and vines; fire-altar evenings; few travellers on muddy roads |
| `plateau` (Pasargadae and the high plains) | as Fārs, two weeks later | as Fārs, a little cooler | as Fārs, earlier | snow on the ground more often than at Pārsa; frozen channels at dawn |
| `sea_west`, `sea_aegean`, `gulf` | sailing opens in March (the Navigium Isidis at Ostia on 5 March) and fills by May; calm seas | the full sailing season; calm, steady winds; the meltemi whitens the Aegean in July and August; the shamal blows dust over the Gulf in June and July | sailing grows risky from mid-September and closes on 11 November; autumn storms | the sea "closed": few ships, rough grey water, whitecaps; hulls hauled ashore and shipwrights at work; the Gulf's small boats still sail |

### 2.3 Month by month: which state each kind of plant and ground shows

Letters: **F** fresh (spring green, flowers in grass), **G** green (full leaf: the usual state),
**D** dry (summer gold, straw), **O** dormant (winter brown-olive), **B** bloom, **T** turning
(autumn colour), **X** bare, **W** fruit (grapes, dates), **P** ploughed, **S** sprouting,
**R** ripe, **U** stubble, **N** gone (no sprite: drawn as nothing). Snow is not a state: snow
cover is an engine layer by altitude and weather (§3.4). Classes are listed in §4.3.

| Climate | Class | Mar | Apr | May | Jun | Jul | Aug | Sep | Oct | Nov | Dec | Jan | Feb |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `med_green` | grass | F | F | F | G | D | D | D | G | G | G | G | G |
| | crop | G | G | G | R | R | U | U | P | P | S | S | G |
| | deciduous | X | F | G | G | G | G | G | G | T | X | X | X |
| | early_bloom | B | F | G | G | G | G | G | G | T | X | X | B |
| | vine | X | F | G | G | G | W | W | T | T | X | X | X |
| | reed | D | G | G | G | G | G | G | G | D | D | D | D |
| | wildflower | G | B | B | D | N | N | N | N | G | G | G | G |
| `med_dry` | grass | F | F | G | D | D | D | D | D | G | G | G | F |
| | crop | G | G | R | U | U | U | U | P | P | S | G | G |
| | deciduous | F | G | G | G | G | G | G | G | T | X | X | X |
| | early_bloom | F | G | G | G | G | G | G | G | T | X | B | B |
| | vine | X | F | G | G | G | W | W | T | T | X | X | X |
| | reed | D | G | G | G | G | G | G | G | D | D | D | D |
| | wildflower | B | B | D | D | D | D | D | D | G | G | G | B |
| `highland` | grass | O | F | F | F | G | D | D | G | O | O | O | O |
| | crop | S | G | G | G | R | U | P | S | S | S | S | S |
| | deciduous | X | X | F | G | G | G | G | T | X | X | X | X |
| `thracian` | grass | O | F | F | G | G | D | D | G | O | O | O | O |
| | crop | S | G | G | G | R | U | P | S | S | S | S | S |
| | deciduous | X | F | G | G | G | G | G | T | X | X | X | X |
| `levant` | as `med_dry` | | | | | | | | | | | | |
| `anatolian` | grass | O | F | F | G | D | D | D | D | O | O | O | O |
| | crop | S | G | G | G | R | U | P | S | S | S | S | S |
| | deciduous | X | F | G | G | G | G | G | T | X | X | X | X |
| | wildflower | N | B | B | D | N | N | N | N | N | N | N | N |
| `high_mountain` | grass | O | O | F | F | G | G | D | D | O | O | O | O |
| | deciduous | X | X | F | G | G | G | G | T | X | X | X | X |
| | wildflower | N | N | B | B | D | N | N | N | N | N | N | N |
| `mesopotamian` | grass | F | G | D | D | D | D | D | D | G | G | F | F |
| | crop | G | R | U | U | U | U | U | P | S | S | G | G |
| | deciduous | F | G | G | G | G | G | G | G | G | T | X | F |
| | reed | G | G | G | G | G | G | G | G | G | D | D | G |
| `steppe` | grass | F | G | D | D | D | D | D | D | D | D | G | F |
| `fars` | grass | F | F | G | D | D | D | D | D | O | O | O | O |
| | crop | G | G | G | R | U | U | U | P | S | S | S | S |
| | deciduous | F | F | G | G | G | G | G | G | T | X | X | X |
| | early_bloom | B | F | G | G | G | G | G | G | T | X | X | B |
| | vine | X | F | G | G | G | W | W | T | X | X | X | X |
| | wildflower | B | B | G | D | N | N | N | N | N | N | N | G |
| `plateau` | grass | O | F | F | G | D | D | D | O | O | O | O | O |
| | crop | S | G | G | G | R | U | P | S | S | S | S | S |
| | deciduous | X | F | G | G | G | G | T | T | X | X | X | X |
| `home` | every class | the home's own season names: spring ×3, summer ×3, autumn ×3, winter ×3 (unchanged) | | | | | | | | | | | |

Rows not listed for a climate inherit `med_green` (`evergreen` is always G). Item overrides
(§6.3): `bloom` months (oleander June–September, chaste tree July, pomegranate May–June, thyme
May–June, tamarisk April–May) and `fruit` months (date palm August–October) win over the class
state in every climate.

### 2.4 Snow lines

Snow falls where a winter cell passes (weather v2) and the tile's level is at or above the
month's line; above `perma` it always lies. "0" means everywhere in the region, "—" never.

| Climate | Oct | Nov | Dec | Jan | Feb | Mar | Apr | May | Jun–Sep | Lowland dusting |
|---|---|---|---|---|---|---|---|---|---|---|
| `home` | — | — | home rule: winter snow | home rule | home rule | — | — | — | — | — |
| `med_green` | — | — | 6 | 5 | 6 | 8 | — | — | — | rare: on a winter day, chance 0.2, dusting gone by noon |
| `med_dry` | — | — | 6 | 5 | 5 | 7 | — | — | — | flurries without settling, chance 0.15; settles only on the Acropolis rock tops for 2 game hours |
| `highland` | — | 11 | 8 | 7 | 7 | 8 | 10 | 12 | — | — |
| `thracian` | — | 6 | 3 | 1 | 2 | 5 | — | — | — | — |
| `levant` | — | — | 7 | 6 | 6 | 7 | 9 | — | — | — |
| `anatolian` | — | 7 | 5 | 0 | 0 | 5 | 8 | — | — | — |
| `high_mountain` | 13 | 12 | 10 | 9 | 9 | 10 | 11 | 13 | 14 (perma) | — |
| `fars` | — | 9 | 6 | 4 | 5 | 8 | — | — | — | Pārsa's plain (level 4) can take snow in January; it melts in one day |
| `plateau` | — | 7 | 5 | 4 | 4 | 6 | 9 | 11 | — | — |
| `mesopotamian`, `steppe`, `gulf` | — | — | — | — | — | — | — | — | — | never (frost on steppe nights only) |

Settling and melting rates per climate are in §6.1 (`snow.settle`, `snow.melt`): fast melt in
`med_*` and `fars`, slow in `anatolian`, `plateau` and `high_mountain` winters.

### 2.5 Water by month

| Water | High or flood | Normal | Low or dry | Ice | Colour |
|---|---|---|---|---|---|
| Tiber | Nov–Mar high; rank-1 flood tiles (mud banks) under water Dec–Feb | Apr–May, Oct | Jun–Sep, mud banks wide | never | yellow-turbid when high, olive-green when low (the bible's "flavus Tiberis") |
| Attic streams (Ilissos, Kephisos; `athens.riverbed`) | Dec–Mar flowing (rank-1 tiles) | Apr, Nov trickle | May–Oct dry stones | never | clear |
| Euphrates and Tigris | Apr–May flood: rank 1 on 1 April, rank 2 later that day, rank 3 on day 2 of the month; recedes through June | Jun–Jul falling, Nov–Mar with a small winter rise | Aug–Oct low, sandbars | never | red-brown in flood, green-brown when low |
| Pārsa channels and the Pulvar | Mar–May full with snowmelt | Jun, Nov–Feb | Jul–Oct thin | thin at dawn Dec–Feb, gone by 11:00 | clear |
| Anatolian rivers and lakes (the Halys, "red river") | Apr–May high | Jun–Jul, Oct–Nov | Aug–Sep | margins Dec–Feb, all day in January | red-brown always, stronger in spate |
| Zagros and Taurus streams | Apr–Jun torrents | Jul, Oct–Nov | Aug–Sep | margins and gorge ice Dec–Feb | milky turquoise in spate |
| Home pond and stream | spring | summer, autumn | — | rim ice on winter day 2 (no full freeze, so the ducks keep their water) | as today |
| Seas | — | — | — | never: the Mediterranean and the Gulf do not freeze | winter darker and rougher; summer calmer |

### 2.6 Weather by climate and season

Today's region `theme.weather` blocks keep their shape (`showers`, `clouds`, `wind`, `wind_from`,
`fog`, `dust`, `snow`). Each climate gives the defaults below; a region may override.

| Climate | Spring | Summer | Autumn | Winter |
|---|---|---|---|---|
| `med_green` | showers 2, clouds 2, wind 0.35 from the west, river fog 0.3 | showers 0, clouds 1, wind 0.3; storms 1 inland | showers 3, clouds 3, wind 0.4 | showers 3, clouds 4, wind 0.45; snow above the line |
| `med_dry` | showers 1, clouds 2, wind 0.35 | showers 0, clouds 1, wind 0.5 from the north-east (Jul–Aug), dust 1, storm 1 (rare) | showers 2 (from Oct), clouds 3, wind 0.4 | showers 3, clouds 4, wind 0.4 |
| `highland` | showers 2, clouds 3, fog 0.5 | storms 2 on ridges | fog 0.6 in valleys | snow 3, clouds 4, wind 0.5 |
| `thracian` | showers 2 | showers 1 | showers 2 | snow 2, wind 0.6 from the north |
| `levant` | showers 1 | clear, sea wind 0.4 | showers 1 (Oct) | showers 3 |
| `anatolian` | showers 2, clouds 3 | clouds 2 racing, wind 0.55, shimmer | clouds 2 | snow 3, wind 0.6, fog 0.3 |
| `high_mountain` | showers 2, mist 0.5 in gorges | clouds 2 | snow 1 (Oct–Nov) | snow 4, wind 0.7 |
| `mesopotamian` | showers 1, fog 0.2 | dust 3, wind 0.5 from the north-west, heat shimmer | clear | showers 2, marsh fog 0.5 |
| `steppe` | showers 1 | dust 3, shimmer | dust 1 | showers 1 |
| `fars` | showers 1 (towering), clouds 3, wind 0.35 from the north-west | dust 2, wind 0.45 | clear | showers 2, clouds 4, snow, frost |
| `plateau` | as `fars` | as `fars` | as `fars` | snow 3 |
| `sea_west` | sea state 1 | sea state 1 | sea state 2, storms 2 | sea state 2–3, storms 3, the bora (Adriatic) |
| `sea_aegean` | sea state 1 | meltemi: sea state 2 by afternoon (Jul–Aug) | sea state 2 | sea state 2–3 |
| `gulf` | calm | shamal: dust over the water (Jun–Jul) | calm | calm, showers 1 |

---

## 3. What changes, system by system

### 3.1 Terrain

| Ground | States made (plain state in brackets) | Notes |
|---|---|---|
| `rome.grass_spring` | (fresh) green, dry | the id keeps its name; ids are stable keys |
| `rome.field_spring` | (green) ploughed, sprout, ripe, stubble | |
| `athens.dry_grass` | (dry) fresh, green | Athens's plain art is summer |
| `athens.field_stubble` | (stubble) ploughed, sprout, green, ripe | |
| `athens.olive_soil` | (dry) green | winter herbs under the olives |
| `parsa.plain_grass` | (fresh) dry, dormant | |
| `parsa.field_barley` | (green) ploughed, sprout, ripe, stubble | |
| `world.steppe` | (dry) fresh, green, dormant | |
| `world.pasture` | (green) fresh, dry, dormant | |
| `world.alluvium` | (dry) green | the winter green plain |
| `world.scrub` | (dry) fresh, green | |
| `world.forest_floor` | (green) turn (leaf litter), dormant | |
| `world.field` | (green) ploughed, sprout, ripe, stubble | |
| `world.fallow` | (dry) fresh | |
| `world.marsh` | (green) dry | tan reeds in winter |
| Home grass and meadow | existing `@spring`, `@autumn`, `@winter` | unchanged |
| Paving, rock, sand, dune, desert, salt, snow, scree, roads | none | the engine darkens them when wet, muddies earth roads in wet months (§3.6), dusts them in dry months |

Terrain carries a `season_class` like plants (§6.3): grasses `grass`, fields `crop`, marsh `reed`.

### 3.2 Plants

| Set | Item | Class | States to make |
|---|---|---|---|
| world | `t_oak`, `t_oak_zagros`, `t_beech` | deciduous | fresh, turn, bare (+ bare shadow) |
| world | `t_pistachio` | deciduous | fresh, turn (red), bare (+ bare shadow) |
| world | `t_tamarisk` | deciduous, bloom Apr–May | bloom (pink), bare |
| world | `t_fir`, `t_cedar`, `t_juniper` | evergreen, `snow_look` | snow |
| world | `t_palm` | evergreen, fruit Aug–Oct | fruit |
| world | `t_reeds` | reed | dry |
| world | `p_wildflowers` | wildflower | bloom, dry (gone needs no art) |
| world | `p_thistle` | grass | green, dormant |
| world | `p_maquis`, `t_cork_oak`, `t_oleaster` | evergreen | none |
| rome | `t_plane`, `t_poplar`, `t_fig` | deciduous | fresh, turn, bare (+ bare shadows) |
| rome | `t_vine`, `r_vine` | vine | fresh, fruit, turn, bare |
| rome | `t_rose` | deciduous, bloom May | green, bare |
| rome | `p_poppy` | wildflower | green, dry |
| rome | `p_reeds` | reed | dry |
| rome | `p_acanthus` | wildflower (summer-dormant) | dry |
| rome | `t_stone_pine`, `t_cypress`, `t_laurel`, `t_myrtle`, `t_olive`, `t_box`, `t_oak` (holm oak), `p_cabbage` | evergreen | none |
| athens | `t_plane`, `t_poplar`, `t_fig` | deciduous | fresh, turn, bare (+ bare shadows) |
| athens | `t_vine` | vine | fresh, fruit, turn, bare |
| athens | `t_agnus` | deciduous, bloom Jul | green, bare |
| athens | `t_oleander` | evergreen, bloom Jun–Sep | green |
| athens | `p_thyme` | evergreen, bloom May–Jun | bloom |
| athens | `p_barley` | crop | ploughed, sprout, green, ripe |
| athens | `p_asphodel` | wildflower | bloom, green |
| athens | `p_reeds` | reed | dry |
| athens | `p_acanthus` | wildflower | dry |
| athens | `t_olive`, `t_cypress`, `t_pine`, `t_myrtle`, `t_laurel` | evergreen | none |
| parsa | `t_plane`, `t_poplar`, `t_willow`, `t_fig` | deciduous | fresh, turn, bare (+ bare shadows) |
| parsa | `t_almond` | early_bloom | fresh, green, turn, bare |
| parsa | `t_pomegranate` | deciduous, bloom May–Jun | green, turn (yellow), bare |
| parsa | `t_vine` | vine | fresh, fruit, turn, bare |
| parsa | `t_date` | evergreen, fruit Aug–Oct | fruit |
| parsa | `p_barley`, `p_wheat` | crop | ploughed, sprout, ripe, stubble |
| parsa | `p_lilies` | wildflower | green, dry |
| parsa | `p_rose` | deciduous, bloom May | green, bare |
| parsa | `p_steppe` | grass | dry, dormant |
| parsa | `t_cypress` | evergreen, `snow_look` | snow |

**Baked vegetation.** Some landmarks and kit carry trees inside their own sprites (gardens,
groves, peristyles). Evergreen foliage stays. Deciduous foliage baked into a landmark must not
stay green in winter: the art generator measures, per sprite, the share of its pixels made from a
deciduous foliage material, and every sprite above 3 % is either (a) split so the trees become
placed plant items (worldgen dresses them through the geometry's spots), or (b) given its
seasonal states if the sprite is small. Expected candidates: `parsa.pasargadae_garden`,
`athens.academy_grove` (planes among the olives), `athens.pandroseion` (olive: evergreen, no
change), Roman domus peristyles (roses). The art task reports the measured list.

### 3.3 Crops and fields

- Fields are terrain or crop items with `season_class: crop`; their state follows the climate's
  crop row (§2.3), so Mesopotamian barley is gold in April while Anatolian wheat is still green.
- **Harvest is watched, not swapped.** In a ripe month, the existing reaper and thresher events
  (`living-world.md` §6.4: L2, L3; Pārsa's `reapers`, `threshing`) move tiles from ripe to stubble
  along their path; the rest of the field turns at the month's end wave (§5.1). The same holds for
  ploughing (stubble or sprout to ploughed, behind the ox team).
- Threshing floors (`parsa.p_threshing`, a world and Greek and Roman equivalent in the kit) get a
  `chaff` emitter that blows downwind while worked (the shared wind).
- Vines show grapes in their fruit months; the vintage event (§3.10) strips them to green leaf
  vine by vine, then the turn wave colours them.

### 3.4 Water, snow and ice

- **Flood.** Worldgen ranks low tiles beside rivers (alluvium, marsh, mud bank, riverbed) 1–3 by
  height above the river (§6.5). In a flood month the engine draws `world.flood` (shallow muddy
  water, water-coded for the shader path, animated) on tiles up to the month's rank, rising and
  falling in waves (§5.1). Walkers treat flooded tiles as water; crossing items still work.
- **Low water and dry beds.** Low months narrow rivers by showing mud bank on rank-0 edge tiles
  (worldgen marks them) and stop the flow overlay on dry riverbeds.
- **River colour** is a multiply per water body and month, baked into ground cells when they are
  built (turbid `(1.08, 1.00, 0.80)`, red spate `(1.12, 0.92, 0.80)`, milky `(1.00, 1.05, 1.06)`).
- **Ice** (`world.ice`, an overlay masked by land neighbours like the foam) forms on still and
  slow water in the months and hours of §2.5. Under ice there are no ripples, no reflections and no
  floating petals; ducks at home keep to the open water in the middle.
- **Snow cover** (§4.2 for how it is drawn): a value per 8 × 8 block that rises under snow above
  the line and melts by day. It shows on ground (two densities with a dithered spreading edge), on
  evergreens in snowy climates (`@snow`), on the mountain backdrops (a snow-cap overlay whose
  snow line moves), and on roofs, wall tops, ledges and canopies on the shader path. Footprints:
  walkers on snow leave no trail (cost), but their steps use `sfx/world/step_snow.wav`.

### 3.5 Roofs and streets

| State | Where and when | How |
|---|---|---|
| Wet | under rain everywhere (exists) | wetness per block darkens ground up to 15 % and adds puddles on paving (exists) |
| Muddy | earth roads and lanes in wet months (`med_*` Nov–Mar, `fars` Dec–Mar, `anatolian` Mar–Apr and Oct–Nov) | the climate sets a **wetness floor** (0.3) for `road_earth`, `packed_earth`, `mud_bank`: darker roads, puddles after any shower |
| Dusty | paving, gravel and earth in dry months (`med_dry` Jun–Oct, `fars` and `steppe` and `mesopotamian` Jun–Sep) | ground cells baked 4 % lighter and warmer; dust motes and dust devils (exist) |
| Snow-dusted | only where §2.4 lets snow settle: Pārsa (some January days), Pasargadae, the plateau, the mountains, Thrace, Anatolia; a rare morning in Rome; the Acropolis rock tops for an hour or two | ground overlay; roofs and wall tops by the snow catcher on the shader path (§4.2); never on Babylon, Susa or the Gulf |
| Frost | dawn in `fars`, `plateau`, `anatolian`, `high_mountain`, `thracian` winters, gone by 09:00 | the dusting overlay at 25 % opacity on grass and earth, from 03:00 to 09:00 |

### 3.6 People: dress

Each main walker kind gets two seasonal variants made on the shared rig: **cold** and **hot**.
Populations pick variants by month (§6.2): cold at 0.7 of walkers in Dec–Feb and 0.35 in Nov and
Mar (in `anatolian`, `plateau`, `high_mountain` also 0.35 in Apr and Oct); hot at 0.4 of outdoor
workers and travellers in Jun–Aug, 0 for formal dress.

| Culture | Cold variant | Hot variant | Evidence |
|---|---|---|---|
| Roman (citizen at work, working woman, porter, carter, child) | hooded paenula or lacerna over the tunic, felt cap, extra layers; women's palla over the head and shoulders | broad-brimmed hat (petasus) on travellers, farmers, porters and sailors | Rome bible §6.2 (hooded paenula in bad weather); Suetonius, *Augustus* 82 (four tunics under a heavy toga in winter; never outdoors without a broad hat against the sun) |
| Greek (citizen, farmer, shepherd, worker, woman) | thick himation wrapped close, felt pilos; farmers in a goatskin cape and lined boots | petasos sun hat on farmers, travellers and riders; exomis for work | Athens bible §6.2; Hesiod, *Works and Days* 536–546 (a soft cloak, a long tunic, ox-hide boots lined with felt, a goatskin cape and a felt cap for winter) |
| Persian and Median (worker, guard in Median dress, herder, scribe) | the kandys worn with the sleeves on, the felt hood's flaps tied under the chin; herders in felt cloaks | kandys off the shoulders, hood flaps open; parasols stay status, not weather | Pārsa bible §6.2 (kandys, hoods with flaps, felt cloaks in cold) |
| Babylonian and Elamite | wool fringed mantle | light tunic, head cloth | Pārsa bible §6.2 (delegations) |
| Formal and ritual dress (togas, priests, Vestals, the king, delegations, kanephoroi) | unchanged | unchanged | ritual dress did not follow the weather |

### 3.7 People: seasonal work

Work routines take a `months` filter (§6.2) on top of their hours. What the land shows, by
climate:

| Work | `med_green` | `med_dry` | `fars` | `mesopotamian` | `anatolian`, `highland`, `thracian` |
|---|---|---|---|---|---|
| Pruning vines and trees | Feb–Mar | Feb | Feb–Mar | — | Mar |
| Ploughing and sowing | Oct–Nov | Oct–Nov (after the first rains; the cranes' call) | Oct–Nov | Oct–Dec (seeder ploughs) | Sep–Oct |
| Grain harvest (reapers) | Jun–Jul | May (barley), Jun (wheat) | Jun | Apr–May | Jul |
| Threshing and winnowing | Jul | Jun–Jul | Jun–Jul | May–Jun | Aug |
| Haymaking | Jun | — | — | — | Jul (`highland`) |
| Shearing | May | Apr–May | Apr | Mar–Apr | May |
| Vintage and treading | Sep–Oct | Sep | Sep | — | Sep |
| Olive harvest and pressing | Nov–Dec | Nov–Jan | — | — | — |
| Date pollination; date harvest | — | — | — | Mar–Apr; Sep–Oct | — |
| Canal and channel clearing | — | — | Aug–Sep (N) | Jul–Sep (low water) | — |
| Wood, charcoal | Dec–Feb | Dec–Feb (Acharnian charcoal burners on the road) | Nov–Feb | — | Oct–Nov |
| Wool work indoors (looms worked) | Dec–Feb | Dec–Feb | Nov–Feb (the bible's winter work) | Dec–Feb | Dec–Feb |
| Shipbuilding and repair (hulls ashore) | Dec–Feb at Ostia, Portus, Brundisium | Dec–Feb at Piraeus (triremes in their sheds) | — | — | — |

Building sites (the Temple of Venus and Roma, the Hall of a Hundred Columns) work all year but
at 0.6 strength in Dec–Feb.

### 3.8 Animals and birds

| Who | Where | Months | Shown as |
|---|---|---|---|
| Swallows and swifts | every climate but `high_mountain` | swallows Mar/Apr–Sep, swifts Apr–Aug | fx flocks at dawn and dusk (exist); their return is a spring turn event |
| White storks | `fars`, `anatolian`, `mesopotamian`, `thracian`, `med_green` marshes (N) | Mar–Aug | on the plain, on nests (a `nest` slot on towers and roofs: `occupied` state in those months, `empty` otherwise) |
| Common cranes | passing over `anatolian`, `thracian`, `med_dry`, `med_green` | Oct–Nov south, Mar north; wintering on `mesopotamian` marshes Dec–Feb | a V-shaped flock crossing the sky with `sfx/world/cranes.wav`; in autumn it starts the ploughing (Hesiod) |
| Starlings | Rome and Latium | Oct–Feb (few in March, none Apr–Sep) | dusk murmurations over the Tiber (the existing `starlings` event moves to these months, §8) |
| Geese and ducks | `mesopotamian` marshes, Tyrrhenian lagoons | Nov–Feb | flocks on the water, calls |
| Cicadas | `med_dry`, `med_green`, `levant`, `ionia` | Jun–Sep | sound emitter by day, clear weather (exists for Athens; extend) |
| Frogs | rivers and marshes everywhere warm | chorus Mar–May at night; silent Dec–Feb | sound, the frog-chorus event |
| Nightingales | Academy and Kolonos, Latium gardens, Pārsa's paradise (N) | Apr–Jun nights | one-shot song at night |
| Fireflies | home (exists), Latium (N) | Jun | as home |
| Bees, butterflies | all warm climates | Mar–Oct (bees all year in `mesopotamian` mildness, N) | as home |
| Flocks: transhumance | Apennines ↔ Apulia; Arcadia ↔ lowlands; Zagros ↔ Susiana; Taurus pastures; steppe ↔ river | up in May, on the high pastures Jun–Sep, down in Oct, in the lowlands Nov–Apr (Varro on Apulia and the mountains) | herd groups that use one district in summer and another in winter, walking the drove road in the move months (§6.2) |
| Lambs | all herding climates | Jan–Mar | small sheep beside the ewes (N: a lamb variant) |

### 3.9 Ships, caravans and couriers

| Lane | Factor on token counts by month (Mar … Feb) | Evidence |
|---|---|---|
| Roman and Greek sea lanes (`sea_west`, `sea_aegean`, the Saronic and Levant lanes) | 0.4, 0.6, 0.9, 1, 1, 1, 0.9, 0.5, 0.25, 0.1, 0.1, 0.1 | Vegetius 4.39: the sea closed from 11 November to 10 March, risky before late May and after mid-September; ships still went out for profit (Pliny) |
| Grain fleet from Alexandria to Portus; grain ships from the Black Sea through the Hellespont | 0, 0.3, 1, 1, 1, 1, 0.6, 0.2, 0, 0, 0, 0 | the sailing season |
| Gulf boats | 1 except Jun–Jul 0.6 (shamal) | coastal traffic all year |
| River barges (Tiber, Euphrates) | 1; Tiber 0.5 in its high months; Euphrates 0.4 at the flood's peak | |
| Caravans on mountain roads (Zagros, Taurus, the Persian Gates) | 0.6, 0.9, 1, 1, 1, 1, 1, 0.9, 0.6, 0.3, 0.2, 0.3 | winter roads; the Pārsa bible's "fewer travellers in winter" from the tablets |
| Caravans on the plateau and plains | winter months 0.5 (`anatolian`), 0.7 elsewhere | |
| Caravans in Mesopotamian summer | 1, but travelling at dawn, dusk and night (Jun–Aug) | heat |
| Royal couriers | 1 in every month | Herodotus 8.98: neither snow nor rain nor heat nor night stops them |
| Roads in Italy and Greece | winter 0.7 | |

- In closed-sea months harbours show **hulls hauled ashore** on their slipways and beaches
  (`world.hull_ashore`) with shipwrights at work, and Piraeus's triremes rest in their sheds
  (Hesiod, *Works and Days* 624–630: draw the ship up on land in winter).
- Ships that exist in the sea lanes in winter are the brave few; their sea state is rougher.

### 3.10 Festivals and events by season

Each city's calendar by month (season day). **M** = must-have, **N** = nice. Days marked ⚑
correct today's region data (§8).

**Rome (AD 126/127)**

| Season | Day 1 | Day 2 | Day 3 |
|---|---|---|---|
| Spring | Navigium Isidis at Ostia and Portus (5 March: a ship launched for Isis opens the sailing season; Apuleius) N; the Salii dance with their shields N | **Parilia** (21 April; the moment) M; Vinalia Priora (23 April) N ⚑ | Floralia's last days N |
| Summer | **Vestalia** (7–15 June: donkeys garlanded, bakers' holiday) M | Ludi Apollinares (6–13 July) M ⚑ (data has day 3) | Vinalia Rustica (19 August) N |
| Autumn | **Ludi Romani** (September: races and theatre) M | October Horse (15 October) N; new wine N | Ludi Plebeii (November) N |
| Winter | **Saturnalia** (17–23 December: gifts, lamps and candles, pottery figurines on stalls) M ⚑ (data has day 2) | Kalends of January: new consuls, vows, gifts N | **Lupercalia** (15 February: runners round the Palatine) M |

Seasonal events: grain fleet arrives (May–Aug) M; ships laid up and hulls ashore at Ostia
(Dec–Feb) M; starling murmurations (Oct–Feb) M; Tiber high over the banks (Dec–Feb) M; vintage in
the Latium vineyards (Sep–Oct) M; olive harvest (Nov–Dec) N; braziers lit at crossroads shrines
and in shops on winter evenings M; snow on the Apennines and the Alban summit in view (Dec–Mar) M;
the rare dusting on the city (a winter morning, chance 0.2) N.

**Athens (432/431 BC)**

| Season | Day 1 | Day 2 | Day 3 |
|---|---|---|---|
| Spring | — | **City Dionysia** (tragedy; the tribute displayed in the theatre) M | Thargelia N |
| Summer | Skira, Dipolieia N | **Panathenaia** (the moment) M | — (grapes ripen) |
| Autumn | **Eleusinian Mysteries** (procession along the Sacred Way) M | Pyanepsia, Oschophoria (vintage festival) N | **Thesmophoria** (women only) M; olive harvest begins M |
| Winter | Rural Dionysia in the demes N; olive harvest M | **Lenaia** M; olive pressing M | **Anthesteria** (new wine, children with little jugs) M |

The olive harvest runs on autumn day 3 and winter days 1–2, not through all of autumn ⚑.
Seasonal events: first rains (Oct–Nov) M; meltemi afternoons (Jul–Aug) M; cicadas (Jun–Sep) M;
cranes overhead and the first ploughing (Oct–Nov) M; triremes in their sheds at Piraeus (Dec–Feb)
M; snow on Parnes, Hymettos and Pentelikon in view (Dec–Mar) M; a winter flurry over the Agora
that does not settle N; almond blossom in the Ilissos valley (Jan–Feb) N; nightingales at the
Academy (Apr–Jun) N. At **Delphi**, the god's winter: for the three winter months the paean falls
silent and Dionysus is honoured instead (Plutarch, *On the E at Delphi* 389c), so the Sacred Way is
quiet and no consultants queue (Dec–Feb) N. **Delos** is busy with pilgrims and ships in the
sailing season only.

**Pārsa (c. 470/469 BC)**

| Season | Day 1 | Day 2 | Day 3 |
|---|---|---|---|
| Spring | **Spring audience** (the moment; delegations every day of spring) M | (audience) | (audience); planting fruit trees N |
| Summer | **Harvest offering** at the threshing floor M | court leaving; terrace quieter M | court away (Ecbatana, by Greek report): no delegations, half the guards, building work goes on M |
| Autumn | **Bāgayādi** offerings M; ploughing M | sowing M | Mithrakāna (attested only in Greek writers) N |
| Winter | **Fire evening** (Āçiyādiya) M | snow on the plain (when the January front comes) M | wool work, repairs; few travellers M |

Elsewhere on the Persian side: the spring flood and barley harvest on the Euphrates (Apr–May) M;
the date harvest at Babylon and in Susiana (Sep–Oct) M; canal clearing at low water (Jul–Sep) N;
Babylon as the king's winter residence (Dec–Feb: royal guards and banners at the palace; Xenophon,
*Cyropaedia* 8.6.22) N, with a card that says "Greek writers say"; snow at the Persian Gates and
on the Zagros road (Dec–Feb) M; storks arriving at Pārsa and on the plateau (March) M; heat at Susa
(streets empty at midday, Jun–Aug) N.

### 3.11 Light and grading

- **Day length** (world-wide, one sky): the sunrise and sunset move with the month, compressed by
  half so night stays short in play. Daylight hours at 38° N and the shift of the day phase's
  start and end:

| | Mar | Apr | May | Jun | Jul | Aug | Sep | Oct | Nov | Dec | Jan | Feb |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Real daylight (h) | 12.0 | 13.2 | 14.2 | 14.7 | 14.4 | 13.4 | 12.3 | 11.1 | 10.1 | 9.5 | 9.8 | 10.8 |
| Shift of sunrise and sunset (game h, each side) | 0 | +0.3 | +0.55 | +0.67 | +0.6 | +0.35 | +0.08 | −0.22 | −0.47 | −0.62 | −0.55 | −0.3 |

  The light phases (and so lamps, glows and phase conditions, which mean light and dark) follow
  the shift; routines keep their game hours.
- **Sun height**: the noon shadow length factor of `look.md` §2.3 (0.7×) becomes 0.55× in June
  and 1.15× in December, with the dawn and dusk factors unchanged. Winter light is lower, whiter
  and longer-shadowed; summer light short-shadowed and hot.
- **Grade per region and season** multiplies over the region's own grade (classic path: a
  per-channel multiply; shader path: deltas on the region look, `look.md` §3.5). Climate defaults;
  a region may override in its theme (§6.2):

| Climate | Spring | Summer | Autumn | Winter | Shader-path deltas |
|---|---|---|---|---|---|
| `med_green` | 0.99, 1.02, 0.97 | 1.04, 1.00, 0.92 | 1.05, 0.97, 0.88 | 0.94, 0.97, 1.04 | winter: saturation −6 %, haze +20 % (hearth smoke) in Rome; summer: haze +25 %, warmer high tint |
| `med_dry` | 1.00, 1.02, 0.96 | 1.06, 1.01, 0.90 | 1.03, 0.98, 0.92 | 0.93, 0.98, 1.03 | summer: exposure +4 %, contrast +5 %, bleached; winter: foliage hue band +6 % saturation (Attic winter green) |
| `highland`, `thracian` | 0.98, 1.02, 0.98 | 1.02, 1.00, 0.95 | 1.04, 0.96, 0.88 | 0.90, 0.95, 1.08 | winter: cool wb, valley fog |
| `levant` | as `med_dry` | | | | |
| `anatolian` | 0.98, 1.03, 0.98 | 1.05, 1.00, 0.90 | 1.04, 0.96, 0.88 | 0.88, 0.94, 1.10 | winter: high key, blue shadows |
| `high_mountain` | 0.96, 1.00, 1.04 | 1.00, 1.00, 1.00 | 1.02, 0.97, 0.92 | 0.86, 0.93, 1.12 | winter: blue-white |
| `mesopotamian`, `gulf` | 1.00, 1.02, 0.95 | 1.08, 0.98, 0.84 | 1.04, 0.99, 0.90 | 0.96, 0.99, 1.02 | summer: heavy warm haze +40 %, dust tint |
| `steppe` | 1.00, 1.02, 0.96 | 1.08, 1.00, 0.86 | 1.05, 1.00, 0.90 | 0.96, 0.98, 1.02 | summer: shimmer, contrast +8 % |
| `fars`, `plateau` | 0.99, 1.01, 0.98 | 1.06, 1.00, 0.88 | 1.04, 0.98, 0.90 | 0.90, 0.95, 1.08 | winter: crisp, haze −40 %, star density +; summer: dust |
| `home` | existing R4.2 grades | | | | |

  The look's acceptance targets (`look.md` §2.1) apply in every season; the season grade is air,
  not paint: the real change is in the looks.

### 3.12 Ambience and music

- **Music** does not change with the season (the cut in `living-corner.md` §10 stands): the
  pieces are about places, and the seasons are heard in the beds.
- **Beds** that carry a season in their content get seasonal variants, chosen by month like the
  rest; beds without a season stay. Variants replace a bed; they never add to the 8-loop budget.

| Bed today | Contains | Variant(s) | Months |
|---|---|---|---|
| `amb/athens/day.ogg` | cicadas in waves | `amb/athens/day_cool.ogg`: wind in olives, goat bells, sparrows and a robin, a far plough ox; rain-washed quiet | Oct–May |
| `amb/athens/night.ogg` | crickets | `amb/athens/night_winter.ogg`: no crickets, wind, a dog, an owl, a far symposium | Nov–Mar |
| `amb/parsa/plain_day.ogg` | swallows, thin wind | `…/plain_day_summer.ogg` (hot wind, grasshoppers, threshing far); `…/plain_day_winter.ogg` (cold wind, crows, no swallows) | Jun–Sep; Nov–Feb |
| `amb/parsa/plain_night.ogg` | crickets | `…/plain_night_winter.ogg` (frost-still, owl, a guard's steps) | Nov–Mar |
| `amb/rome/day.ogg` | swallows in the murmur | `amb/rome/day_winter.ogg` (no swallows; hearth crackle, wind in the streets, dripping gutters, jackdaws) | Dec–Feb |
| home beds | as R4.2 | unchanged | |
| world nature beds (`dawn_*`, `night_*`, `fields`) | mixed | new layers: `amb/world/frogs_spring.ogg` (Mar–May nights by water), `amb/world/wind_bare.ogg` (wind in bare branches, Dec–Feb woods), `amb/world/marsh_winter.ogg` (geese and ducks, Mesopotamian marsh Nov–Feb), `amb/world/flood.ogg` (lapping floodwater, Apr–May) | as listed |

- **Emitters** with seasons (exists for Athens's cicadas) extend to all cicada climates, frogs,
  the crane flock, nightingales and the stork clatter (exists).
- **Snow** dulls the world's beds (high frequencies down by cover, `look.md` §5) and uses
  `amb/world/snow.ogg`; footsteps on snow use `sfx/world/step_snow.wav` (both exist).
- **The turn of a season** at its first dawn plays a soft regional cue (§5.3).

---

## 4. How it is built inside the budgets

### 4.1 Where each change is made

| Change | Engine effect | Generator variant (same models, a few lines each) | Bespoke modelling |
|---|---|---|---|
| Foliage colour, bloom, bare branches, fruit | chooses the state per climate and month; cross-fades at the switch | **yes**: recolour leaf materials by state ramp; `bare` drops leaf voxels and keeps the branch skeleton (thin a little); `bloom` swaps a fraction of leaf voxels to blossom; `fruit` adds clusters | — |
| Ground (grass, fields, marsh) | chooses the state; bakes into ground cells | **yes**: ramp swaps, crop stage textures (furrows, rows of shoots, ripe gold with sheaves, stubble) | — |
| Snow on ground | **yes**: cover field, dithered overlay in ground cells | overlay sprites (2 densities, masked edge) | — |
| Snow on evergreens | swap to `@snow` above 0.5 cover (both paths) | **yes**: snow on the up-facing voxels of the canopy | — |
| Snow on roofs, wall tops, ledges, bare canopies | **shader path**: the snow-catcher bit (§4.2); classic path: none | the generator sets the bit | — |
| Snow on mountain backdrops | overlay with a moving snow line (§4.2) | **yes**: snow-cap overlay per backdrop variant | — |
| Wet, muddy, dusty, frost | **yes** (wetness exists; floors and tints per month) | — | — |
| Flood, low water, dry beds, ice, river colour | **yes** | overlays `world.flood`, `world.ice` | — |
| Leaf fall, petals, chaff, snowfall | **yes**: particles (exist for home; world-wide by class and wind) | leaf colours `fx/world.leaf/v0-3` | — |
| Leaf litter under deciduous trees | **yes**: hashed decals baked into ground cells in turn and bare months, faded in March | decals `fx/world.litter/v0-5` | — |
| Grade, haze, sun height, day length | **yes** | — | — |
| Cold and hot dress | variant weights by month | **yes**: rig garments (hood, cloak, sleeves, hat) | — |
| Who is out, what work, which festival | **yes** (data filters) | — | — |
| Flocks, birds | **yes** | crane flock, lamb (N) | — |
| Ships laid up | **yes** (token factors, harbour state) | — | `world.hull_ashore` (2 rotations), slipway cradle |
| Threshing, winnowing, vintage, olive harvest | events (exist in part) | — | threshing sledge and winnowing fork props per culture, olive nets and ladders and baskets, a treading vat, a date-climber pose |
| Festival props | events | — | Saturnalia stall with figurines and candles (Rome), Anthesteria jugs (Athens), fire-altar evening offerings (exist) |
| Stork nests | `nest` slot state by month | `occupied` / `empty` state of the nest prop | — |

### 4.2 Snow on what faces up: both render paths

The shader path (`look.md` §3) and the classic path must both show winter correctly, the shader
path more richly.

- **The snow-catcher bit.** The art generator knows, voxel by voxel, which faces point up. It sets
  the lowest bit of the **blue** channel of every base pixel that is an up-facing face of a
  material snow lies on (roof tiles, thatch, plaster, stone, earth, wall tops, ledges, canopy tops,
  rock), and clears it everywhere else (walls, water, glass, glow, figures). A ±1/255 change is
  invisible; pages are lossless PNG, so it survives packing exactly. **No page cost.**
- **Shader path.** The world sprite pass draws through a small sprite shader. Because the grade
  moves into the final pass on that path (`look.md` P8), the per-vertex colour of world sprites is
  free and carries data: **r = snow cover** of the sprite's block (0–1, after the snow line),
  **g = wetness**, **b = frost**, **a = alpha** (occluder fade). Where the bit is set the shader
  mixes toward snow white (with a cool shade on the darker side of the ramp) by
  `smoothstep(0.1, 0.8, r)`, and toward a frost tint by `b` at dawn. One render state, no extra
  draws; CPU cost is one table lookup per drawn sprite (≤ 0.02 ms).
- **If the graphics R&D adopts generator-made normal, height and material maps**, the snow pass
  reads them instead of the bit: snow by `normal · up` (soft gradients on domes and canopies),
  material decides where snow lies and where wet stone shines, and height adds drifts at wall feet
  and fills furrows first. The bit stays as the fallback for sets without maps. Nothing else in
  this plan changes; the maps do not replace the generator states for bare, bloom and crops,
  because those change geometry, not light.
- **Classic path** (no shaders): ground snow, frost, ice, flood, evergreen `@snow` looks,
  backdrop snow (uniform alpha by month), every plant and ground state, grade and particles all
  work; roofs and wall tops keep their art. Winter still reads as winter (white ground, bare and
  snowy trees, white mountains); it is the documented degradation of the fallback path.
- **Backdrop snow line.** Each snow-cap overlay stores, in its alpha, the height rank of each snow
  pixel (alpha = 255 − 16 × rank, rank 0 at the summit). The shader shows pixels whose rank is
  under the month's line; the classic path draws the overlay at one alpha per month (winter 1,
  late autumn and early spring 0.5, summer 0 except `high_mountain` peaks).

### 4.3 Sprite keys and classes

| Key | Rule |
|---|---|
| `<any key>@<state>` | A look of the sprite in one state. States: `fresh`, `green`, `dry`, `dormant`, `bloom`, `turn`, `bare`, `fruit`, `ploughed`, `sprout`, `ripe`, `stubble`, `snow`, and the home climate's `spring`, `summer`, `autumn`, `winter`. `gone` needs no key (nothing is drawn). |
| Plain key | The look the item's art shows; the item says which state that is (`plain_state`), and that state never gets an `@` key. |
| Resolution | Per climate, once per month change (on a worker thread): growth stage + state, stage, state, plain, exactly as `living-corner.md` R4.3. Shadows and glows follow the same rule (a `@bare` shadow is the thin branch shadow). Nothing is looked up per frame. |
| Snow looks | `@snow` for items with `snow_look`; chosen instead of the month's state when the block's snow cover ≥ 0.5. |
| `terrain/world.snowcover/d<1\|2>/v<0-3>`, `…/d2/m<mask>` | Snow over ground: dusting and full cover, four variants each, and masked edges for full cover. |
| `terrain/world.ice/m<mask>` | Ice on water, mask = land neighbours (as the foam). |
| `terrain/world.flood/m<mask>/f<0-3>` | Shallow flood water, mask = same-terrain neighbours, animated, water-coded. |
| `backdrop/<id>/snow/v<n>` | Snow-cap overlay of a backdrop variant, rank in alpha. |
| `fx/world.leaf/v<0-3>/f<k>` | Falling leaves in four colours (plane yellow-brown, poplar yellow, vine red, beech copper). |
| `fx/world.litter/v<0-5>` | Fallen-leaf decals. |
| `fx/world.crane_flock/f<k>` | A V of cranes, 4 frames. |
| `walker/<kind>/v<k>/…` | Seasonal dress variants are ordinary variants; the set catalog tags them `cold` or `hot` (§6.3). |

Classes (`season_class`): `grass`, `crop`, `deciduous`, `early_bloom`, `vine`, `reed`,
`wildflower`, `evergreen`. Items without a class never change looks (paving, buildings, props).

### 4.4 Cost per set

Measured from today's manifests (sprite rectangle area). Plants and ground are small: Rome's
whole plant list is 0.11 Mpx, a terrain's full mask set about 28 kpx.

| Set | Plant states (+ bare shadows) | Ground states | Walker variants | Overlays, backdrop snow, fx, props | **Total new** | Today's pages and fill |
|---|---|---|---|---|---|---|
| world | 0.45 Mpx | 0.56 | 0.15 | 0.25 overlays + 0.80 backdrop snow + 0.10 fx and props | **≈ 2.3 Mpx** | 1 page, 4096 × 2304, 89 % |
| rome | 0.15 | 0.15 | 0.40 | 0.05 (Saturnalia stall) | **≈ 0.75** | 3 pages, 82–90 % |
| athens | 0.15 | 0.16 | 0.45 | 0.05 | **≈ 0.8** | 2 pages (the second 4096 × 2560), 79–90 % |
| parsa | 0.35 | 0.13 | 0.60 | 0.45 (Kuh-e Raḥmat snow caps) | **≈ 1.55** | 2 pages, 86–89 % |
| home | 0 (exists) | 0 | 0 | 0 | 0 | 4096 × 1024 |

**Plan that fits:**

1. **Season looks pack beside their plain keys** on the page that holds the set's plants, kit and
   actors (page 0 of each city set, the world page), so a plant and its states share a texture and
   the depth pass breaks no batch when a tree changes state. A separate seasonal page was
   considered and rejected for exactly that reason: plants interleave with buildings in depth
   order, and a second texture would add a page switch at every tree.
2. Rome's, Athens's and Pārsa's kit pages have 1.6–2.3 Mpx of free rectangle area today, enough on
   paper; where the packer cannot fit them, **landmark pieces move off the kit page** into the
   space that **half-resolution shadows** (`look.md` §4.3, already proposed as the first art step)
   free on the shadow pages: about 9.3 Mpx in Rome, 4.8 in Athens, 5.3 in Pārsa.
3. The world page grows from 2304 to 2816 rows (+512 rows, +8 MB). It stays one page.
4. **No set gains a page.** Page counts stay world 1, Rome 3, Athens 2, Pārsa 2.

**Memory** (GPU pages resident: home + world + one city set, `world-tech.md` §4.5):

| | Today | With seasons | With seasons and half-res shadows |
|---|---|---|---|
| Home | 16 MB | 16 | 16 |
| World | 36 | 44 | 44 |
| Rome (largest city set) | 192 | 192 | ≈ 160 (the last page trims) |
| **Worst resident set** | **244 MB** | **252 MB** | **≈ 220 MB** |
| Budget | 320 MB | | |

CPU memory: per-climate sprite tables only for seasonal items (≈ 600 items × 15 climates × a few
entries) under 1 MB; the snow field is 160 × 56 blocks of 4 bytes (36 kB). Nothing grows over a
session: tables are rebuilt in place.

### 4.5 Frame and simulation budgets

| Work | Where | Budget |
|---|---|---|
| Sprite-table rebuild at a month change | worker thread; the main thread swaps a pointer | ≤ 2 ms on the worker, ≤ 0.05 ms main |
| Item state switches during a wave | per frame, items switching in view draw both looks cross-faded for 0.8 s | ≤ 200 extra sprites, ≤ 0.03 ms |
| Ground cells re-baked for state waves, snow quanta, flood ranks, litter | amortised, visible cells first, old cell shown until the new one is ready | ≤ 0.3 ms per frame; a full screen of cells refreshed within 1 s |
| Snow field and water state update | 1 Hz, sliced across frames | ≤ 0.02 ms per frame |
| Impostors (zoomed out) | re-rendered after a wave, 2 cells a frame, visible first | within the existing impostor budget |
| Overview tint | worldgen ships a 1 byte-per-tile ground class map; the engine colours it per climate and month on a worker once per game day and uploads it in one frame | ≤ 3 ms on the worker, one upload |
| Leaf, petal, chaff and snow particles | inside the existing pool | ≤ 2 500 live, ≤ 0.15 ms (`look.md` §3.7) |
| Seasonal populations, variants, tokens | inside city life | unchanged ≤ 0.6 ms simulation; ≤ 800 live actors |
| Draw calls | the snow shader is a render state, not a pass | no new scene draws |

---

## 5. Transitions

### 5.1 A month turns in waves, not with a pop

- The calendar day changes at midnight (as today). For every class whose state differs between
  the old and new month in a climate, **each item switches at its own moment** during the new
  day: `06:00 + h × 10 h`, with `h = hash(world seed, tile)`. Trees turn one by one through a
  morning and afternoon, under the player's eyes, each with a 0.8 s cross-fade.
- **Ground** switches in four hashed groups (07:00, 09:30, 12:00, 14:30), so cells re-bake four
  times on a turning day and the change spreads as a soft stipple across fields and hills.
- The **grade** glides from midnight to the end of dawn (`living-corner.md` R4.2, unchanged).
- While the clock is pinned, the wave runs on the fraction of the day length played.
- When the season is set by hand (pin or the panel), the wave is compressed to 3 seconds (items
  over 0–2 s, ground in two groups) and the grade glides over 2 seconds. With reduce motion, the
  switch is a plain 0.8 s cross-fade for everything at once.

### 5.2 The great turns

| Turn | What the player sees and hears |
|---|---|
| **Leaf turn** (`T`) and **leaf fall** (`X`) | trees colour through the day; the falling-leaf rate rises 3× in turn months and bursts on the first gust of the bare day; litter gathers under deciduous trees through the turn and bare months and fades in March; the wind in bare branches joins the woods' bed |
| **First snow** | the first winter front over a snowy climate: grey sky, the snowfall thickening, cover rising over about a game hour from the highest ground down, the ground stippling white tile by tile, evergreens catching it, roofs whitening on the shader path, the world's sound dulling; the first-snow sting (exists for home and Pārsa) |
| **Thaw** | cover melts by day from the edges inward (south-facing first is not shown: the grid has no aspect); the ground goes dark and wet (wetness 1, drying), earth roads muddy, streams rise; the snow line climbs month by month |
| **First green** | `O` or `D` to `F`: the ground freshens in its four groups; flowers appear in the grass; swallows return (event); frogs start at night |
| **First rains** (`med_dry`, `med_green` in October) | a real shower front, then the air after rain (the shader's +8 % saturation, half haze, 2 minutes), the dust laid; a week later in game (the next month) the green flush |
| **Flood rise and fall** | rank 1 tiles fill on the first morning of April, rank 2 that afternoon, rank 3 the next day; floodwater lapping in the bed; walkers re-route; in June the water draws back in reverse, leaving dark wet silt that dries over a day |
| **Harvest** | reapers walk the fields from ripe to stubble; threshing floors fill with chaff in the wind; the field's remainder turns at the month's end |
| **Closing of the sea** | through November the lanes thin; on winter day 1 the harbours show hulls hauled ashore and shipwrights; in March the Navigium Isidis launches the first ship and the lanes fill again by May |

### 5.3 The first dawn of a season

- **Home** keeps its own moment: `sfx/season.wav` and Laeticia's season line.
- **Everywhere else**, at the first dawn of a season, the region in view plays its turn cue: a
  short sting at low gain (`sfx/season.wav` until regional cues exist; Rome, Athens and Pārsa each
  get one, N) and the climate's turn event, chosen from: swallows return, storks arrive, first
  snow, first frost, cicadas begin, first rains, cranes overhead, flood rising, braziers lit,
  ships hauled ashore. The caption fades in for 3 seconds with the season: "Ἀθῆναι · autumn, 432
  BC".
- Turn events are ordinary events (`living-world.md` §5) with a `season_turn` trigger (§6.2), so
  they are in the day plan and deterministic.

---

## 6. Data

### 6.1 `assets/catalog.json`: `climates[]` (contract: orchestrator)

```json
"climates": [
  { "id": "fars",
    "name": "Fārs",
    "classes": {
      "grass":       ["fresh","fresh","green","dry","dry","dry","dry","dry","dormant","dormant","dormant","dormant"],
      "crop":        ["green","green","green","ripe","stubble","stubble","stubble","ploughed","sprout","sprout","sprout","sprout"],
      "deciduous":   ["fresh","fresh","green","green","green","green","green","green","turn","bare","bare","bare"],
      "early_bloom": ["bloom","fresh","green","green","green","green","green","green","turn","bare","bare","bloom"],
      "vine":        ["bare","fresh","green","green","green","fruit","fruit","turn","bare","bare","bare","bare"],
      "wildflower":  ["bloom","bloom","green","dry","gone","gone","gone","gone","gone","gone","gone","green"]
    },
    "inherits": "med_green",
    "snow": { "line": [8, null, null, null, null, null, null, null, 9, 6, 4, 5],
              "perma": null, "settle": 0.02, "melt": 0.004, "lowland": { "months": ["jan"], "chance": 0.4 } },
    "frost": ["dec", "jan", "feb"],
    "wet_floor": { "months": ["dec","jan","feb","mar"], "value": 0.3 },
    "dust":      { "months": ["jun","jul","aug","sep"] },
    "water": { "channels": ["full","full","full","normal","low","low","low","low","normal","normal","normal","normal"],
               "ice": { "months": ["dec","jan","feb"], "hours": ["03:00", "11:00"] } },
    "travel": { "caravan": [1,1,1,1,1,1,1,0.9,0.8,0.7,0.6,0.7], "courier": 1 },
    "weather": { "spring": { "showers": 1, "clouds": 3, "wind": 0.35, "wind_from": "north-west" },
                 "summer": { "showers": 0, "clouds": 1, "wind": 0.45, "dust": 2 },
                 "autumn": { "showers": 0, "clouds": 1, "wind": 0.3 },
                 "winter": { "showers": 2, "clouds": 4, "wind": 0.4, "snow": true } },
    "grade": { "spring": [0.99,1.01,0.98], "summer": [1.06,1.00,0.88],
               "autumn": [1.04,0.98,0.90], "winter": [0.90,0.95,1.08] },
    "look":  { "winter": { "haze": -0.4, "stars": 0.2 }, "summer": { "dust": 0.3 } },
    "dress": { "cold": [0.35,0,0,0,0,0,0,0,0.35,0.7,0.7,0.7], "hot": [0,0,0,0.4,0.4,0.4,0,0,0,0,0,0] },
    "turn_events": { "spring": "storks_arrive", "summer": "first_dust", "autumn": "ploughing_begins", "winter": "first_frost" }
  },
  { "id": "sea_west", "inherits": "med_green",
    "sea": { "state": [1,1,1,1,1,1,1,2,2,3,3,2],
             "sailing": [0.4,0.6,0.9,1,1,1,0.9,0.5,0.25,0.1,0.1,0.1] } }
]
```

- Arrays have 12 entries, index 0 = March. Month names (`"mar"`…`"feb"`) are accepted wherever a
  list of months is wanted. `inherits` fills any key a climate leaves out.
- `seasons[]` (home) is unchanged; the `home` climate's classes are the season names, so home
  resolves exactly as today.
- `tuning.hpp` gains: day-length shift table, wave hours, cross-fade length, snow cover quanta,
  frost hours, litter density, the shadow-length factors of §3.11.

### 6.2 Region files `assets/regions/<region>.json` (owned by each layer's builder)

```json
{
  "id": "athens",
  "climate": "med_dry",
  "era": { "caption": "Ἀθῆναι · {year}", "year": { "spring": "432 BC", "summer": "432 BC",
           "autumn": "432/431 BC", "winter": "432/431 BC" } },
  "moment": { "season": "summer", "day": 2, "festival": "panathenaia",
              "caption": "Ἀθῆναι · the Panathenaia, summer 432 BC" },
  "theme": {
    "seasons": {
      "winter": { "grade": [0.93, 0.98, 1.03],
                  "look": { "foliage_saturation": 0.06 },
                  "ambience": { "beds": [ { "file": "amb/athens/day_cool.ogg", "hours": ["05:00","19:30"] },
                                          { "file": "amb/athens/night_winter.ogg", "hours": ["19:30","05:00"] } ] } },
      "autumn": { "ambience": { "beds": [ { "file": "amb/athens/day_cool.ogg", "hours": ["05:00","19:30"],
                                            "months": ["oct","nov"] } ] } }
    },
    "weather": { "winter": { "showers": 3, "clouds": 4, "wind": 0.4 } }
  },
  "water": [ { "body": "ilissos", "rect": [330, 690, 359, 719], "kind": "stream",
               "level": ["high","low","dry","dry","dry","dry","dry","dry","low","high","high","high"] } ],
  "districts": [
    { "id": "agora", "populations": [
      { "role": "citizen", "density": "market", "max_per_chunk": 10,
        "variants": { "cold": "climate", "hot": "climate" } } ] },
    { "id": "groves", "populations": [
      { "role": "olive_picker", "density": "work", "max_per_chunk": 6, "when": { "months": ["nov","dec","jan"] } } ] }
  ],
  "groups": [
    { "id": "arcadian_flock", "kind": "herd", "actor": "world.sheep", "count": 18,
      "seasonal": { "summer": "arcadia/high_pasture", "winter": "greece/coastal_plain",
                    "move": ["may", "oct"], "route": "base:arcadia_drove" } } ],
  "festivals": [ { "id": "olive_harvest", "months": ["nov","dec","jan"], "hours": ["07:00","16:00"] } ],
  "events": [
    { "id": "first_rains", "rarity": "festival", "size": "medium",
      "trigger": { "on": "season_turn", "season": "autumn", "months": ["oct"] },
      "steps": [ { "emit": { "weather": "front" } } ], "string": "first_rains" } ],
  "lanes_tokens": [ { "actor": "athens.trireme", "lane": "base:saronic", "count": 4, "by_month": "sailing" } ],
  "harbours": [ { "zone": "piraeus_sheds", "laid_up": "sailing", "props": ["world.hull_ashore"] } ],
  "strings": { "season_turn.autumn": "The first rain. The whole city smells of dust and earth.",
               "first_rains": "First rains" }
}
```

New or changed fields:

| Field | Meaning |
|---|---|
| `climate` | one of `catalog.climates[].id` (required) |
| `season` (top level) | **removed** (it pinned the region to one season) |
| `caption` | replaced by `era.caption` with `{year}` filled per season, and `moment.caption` while the moment's festival runs; the engine appends the season name ("· winter") on other days |
| `moment` | `season`, `day`, `festival`, `caption`: the famous day, used by captions and **Go to the moment** |
| `theme.seasons.<season>` | `grade` (multiply), `look` (shader deltas), `haze`, `ambience` (beds that replace the year-round beds, optionally by `months`) |
| `water[]` | named bodies with a `rect`, `kind` (`river`, `stream`, `channel`, `lake`, `pond`), `level` by month (`flood`, `high`, `normal`, `low`, `dry`), optional `colour` by month; the climate's defaults apply when absent |
| `populations[].when.months`, `.variants` | month filters (beside `season`); dress variant weights (`"climate"` = the climate's `dress` row, or 12 numbers) |
| `groups[].seasonal` | a herd's summer and winter districts, move months and drove route |
| `festivals[].months` | a festival that spans months (the olive harvest) instead of `season` + `day` |
| `events[].trigger.on: "season_turn"` | the first dawn of `season` (optionally `months`) |
| `lanes_tokens[].by_month` | `"sailing"`, `"caravan"`, `"courier"` (the climate row) or 12 factors |
| `harbours[]` | zones whose ships are laid up when the lane factor is below 0.3, with the props shown |
| `strings.season_turn.<season>` | one optional line per season for the turn caption |

### 6.3 Set catalogs `assets/sets/<set>/catalog.json` (contract)

| Field | On | Meaning |
|---|---|---|
| `season_class` | items, terrain | one class of §4.3; absent means the look never changes |
| `plain_state` | items, terrain with a class | the state the plain art shows (`rome.grass_spring`: `fresh`; `athens.dry_grass`: `dry`; `parsa.t_almond`: `bloom`) |
| `states` | items, terrain with a class | the states the art supplies (the generator reads it; coverage checks it) |
| `bloom`, `fruit` | items | months that override the class state |
| `snow_look` | items | the art supplies `@snow` |
| `snow_catch` | items | `false` for items whose up faces never hold snow (braziers, fire altars, kilns, fountains); default `true` |
| `variant_tags` | actors | `{"v4": "cold", "v5": "hot"}`: which rig variants are seasonal dress |
| `art.overlays` | world set | `["world.snowcover", "world.ice", "world.flood"]` |
| `art.backdrop_snow` | sets with backdrops | backdrop ids that get snow-cap overlays |

The home catalog's items keep `season_looks` (it lists `@spring`…`@winter` looks); the engine reads
it as `states` under the home climate.

### 6.4 Interface strings (final text, `src/ui/strings.hpp`)

Set the scene · Time · Weather · Wind · Season · Follow the clock · Natural · Follow the
calendar · Follow the world · held · in {region} · everywhere · Calm · Breeze · Windy · Gale ·
Rain here · Snow here · Fog here · Dust here · Storm here · Clear here · The moment: {moment} ·
Go there · {Season}, day {d}: {festival} · {region} · {year} · {season}

### 6.5 Validators (`tools/worldgen`, worldgen core; engine coverage tests)

| Check | Rule |
|---|---|
| Climate named | every region file has `climate`, and it exists in the catalog |
| No season pin | no region file has a top-level `season` |
| Climate complete | every climate (after `inherits`) has 12 entries for every class used by an item or terrain placed in its regions; `sea` blocks only on climates used by sea regions |
| States covered | every state a placed item can resolve to (its climate rows, `bloom`, `fruit`, `snow_look`) is in its `states` or is its `plain_state` or `gone`; the engine's coverage test fails on a missing sprite for a listed state |
| Moment | `moment.festival` exists in `festivals`, and its season and day match |
| Festival months | a festival's `season` + `day` agrees with any `months` it gives; events filtered by month find a festival on that month |
| Flood ranks | ranked tiles are alluvium, marsh, mud bank or riverbed, within 12 tiles of a river, at most 1 level above it; every `flood` water body has rank-1 tiles |
| Snow | no snow line in `mesopotamian`, `steppe`, `gulf`; `lowland` only in climates of §2.4; backdrops in `art.backdrop_snow` have overlays |
| Herds | both seasonal districts exist; the drove route connects them on the graph |
| Tokens | `by_month` names a row the region's climate has |
| Dress | populations with `variants` use roles whose actors have the tagged variants |
| Audio | every seasonal bed and turn sound exists in the audio manifest |
| Captions | `era.caption` resolves for every season; no caption string hard-codes a season except `moment.caption` |

Worldgen also writes, into the base layer, the **flood ranks** (a sparse list of tile and rank) and
the **ground class map** for the overview (1 byte per tile).

---

## 7. Work plan

One agent per task. **M** = must-have, **N** = nice. Order is by when the first visible result
comes: **Athens in four seasons first** (it needs only states, grade and climates: no snow
engine), then **Pārsa with snow**, then **Rome**, then the rest of the world.

| # | Lane | Task | Needs | Acceptance | M/N |
|---|---|---|---|---|---|
| 1 | engine | **Calendar and climates**: month from the day; load `climates[]`; per-climate state resolution on a worker (`@<state>`, plain state, home compatibility); region season pin removed in life and render; captions with era, season and moment; day-length shift and sun height; season grade per region (classic multiply) | the catalog field from task 3 (or a fixture) | unit tests for month mapping, inheritance, resolution order, day length; scripted shots of a fixture world in four seasons; home's existing season scripts unchanged; bench and soak green | M |
| 2 | art (core) | **Generator machinery**: state rendering helpers shared by all sets (leaf recolour by state ramp, bare skeleton, bloom, fruit, crop stages, conifer snow), the snow-catcher bit in every base sprite of every set and the home page, half-resolution shadows if not landed, the baked-foliage report | — | pages rebuild byte-identical twice; a test reads the bit back on known roof and wall pixels; visual sheet of one tree and one field in every state | M |
| 3 | world data (core) + orchestrator | **Climates and validators**: the orchestrator adds `climates[]` (from §6.1 and §2) to the catalog; worldgen core adds the validators of §6.5, flood ranks and the ground class map in the base layer, and assigns `climate` in the stretch region files | — | `tools/worldgen/build.sh --check` passes with every check; a seeded failure for each check is reported by name | M |
| 4 | art | **Athens and the world set's Greek-side plants and ground**: §3.1 and §3.2 states for `athens` and for the world plants used in `med_dry`; baked foliage handled | 2 | an art sheet of every Athens plant and ground in each state; page count unchanged; fill reported | M |
| 5 | world data | **Athens region**: climate, era, moment, festival corrections, olive harvest months, seasonal populations, first rains event, the Ilissos water body, Piraeus laid-up harbour | 3 | `lifeinfo problems` empty; `life_chains` green; four-season life dumps of the Agora | M |
| 6 | QA | **First four-season look**: the Acropolis south view and the Agora at 11:00 clear, and Attica north, in four seasons, plus dusk in winter | 1, 4, 5 | review report with shots; image statistics as below | M |
| 7 | engine | **Snow, ice, flood and water states**: snow field, ground overlays, evergreen `@snow`, backdrop snow, frost, wet floor, dust, flood ranks, ice, river colour, litter decals, cell and impostor refresh amortised, overview tint | 1, 3; art overlays from 8 | unit tests (cover rises and melts by climate; flood waves; ice hours); scripted: Pārsa in a January front, Babylon on 1 April, Rome's Tiber in January; bench cases of §7.2 | M |
| 8 | art | **World set**: all world plant and ground states, overlays (`world.snowcover`, `world.ice`, `world.flood`), backdrop snow caps, leaf colours, litter, crane flock, `world.hull_ashore` and cradle, walker variants for world walkers | 2 | art sheets; the world page ≤ 4096 × 2816; validation green | M |
| 9 | art | **Pārsa set**: plant and ground states, Kuh-e Raḥmat snow caps, walker cold and hot variants, stork nest states, Pasargadae garden unbaked | 2 | sheets; two pages; fill reported | M |
| 10 | world data | **Pārsa and the Persian side**: climates for every Persian-side region file, moment, court away in summer, winter few travellers, flood water bodies (Euphrates, Tigris, Susiana canals), date harvest, Zagros and Taurus caravans, Zagros herds | 3 | as task 5 for Pārsa, Babylon, Susa | M |
| 11 | engine | **Seasonal life**: month filters, festival months, dress variant weights, token factors by month and harbour laid-up state, herd groups with seasonal districts, birds and emitters by month, turn events (`season_turn`), seasonal bed selection, leaf and petal and chaff particles world-wide | 1 | unit tests; `lifeinfo bench` with each city's busiest seasonal festival (Saturnalia, Lenaia, the fire evening) inside budget; scripted: Ostia in January shows hulls ashore and few ships | M |
| 12 | art | **Rome set**: plant and ground states, walker variants, Saturnalia stall | 2 | sheets; three pages | M |
| 13 | world data | **Rome and the Roman side**: climates, moment, festival corrections, grain fleet and laid-up months, starlings months, Tiber water body, Apennine ↔ Apulia transhumance | 3 | as task 5 | M |
| 14 | engine | **Set the scene panel**: panel, `K`, Go to the moment, wind pin, weather kinds by climate, strings, save field | 1 | scripted UI flow with shots of every state (hover, pressed, held, disabled); Go to the moment lands on the festival's first hour | M |
| 15 | engine (shader path) | **Snow on roofs and wet stone**: the sprite shader reading the bit (or the R&D maps), vertex data, frost; season deltas in the lookup | 7 and the `look.md` shader path | look suite shots: Pārsa terrace roofs white in a January front (shader), unchanged on classic; luma statistics | M where the shader path exists |
| 16 | audio | **Seasonal beds and cues**: the variants of §3.12, frogs, wind in bare branches, winter marsh, floodwater; turn cues for Rome, Athens, Pārsa (N) | — | loudness rules of `CLAUDE.md`; seamless loops; captured mixes of each city in four seasons | M (beds), N (cues) |
| 17 | world data | **The stretches**: climates, water bodies, herds and seasonal events for Latium, the Apennines, Greece, Arcadia, Thrace, Ionia, Anatolia, the Levant, the steppe, the seas | 3 | as task 5 for each layer | M |
| 18 | art | **Bespoke seasonal props**: threshing and winnowing gear per culture, olive nets and ladders, treading vat, date climber, Anthesteria jugs, lamb variant | 2 | sheets | N |
| 19 | QA | **Four seasons everywhere**: the full matrix (§7.1) and the performance gates (§7.2) | all M tasks | report; every check green | M |

### 7.1 Four-season acceptance (QA, scripted, headless)

- For **every region file**, a script `tests/scripts/seasons/<region>.lcs` frames the region's
  signature view (`set look landmark:ID ZOOM`, or the stretch's waypoint) at 11:00 with weather
  pinned clear, and shoots it on day 1, 4, 7 and 10 (one day in each season); snowy climates add
  a January shot during a front. Shots go to `build/<preset>/shots/seasons/`.
- **No two seasons look alike:** between any two of a region's four shots, at least 10 % of world
  pixels differ by more than 12 luma levels or 8° of hue (sea stretches: the ship count differs
  instead, and the sea state).
- **Vegetation is right:** in a rect of the region's dominant ground, mean hue and saturation fall
  in the season's band: `med_dry` winter green (hue 75–130°, S ≥ 30 %), summer gold (hue 35–60°);
  `fars` spring green, summer gold, winter dormant (S ≤ 25 %); `mesopotamian` winter green and
  summer bleached; `anatolian` winter white (luma ≥ 190 over the ground rect).
- **Snow only where true:** in a clear-weather January shot without the rare dusting, the ground
  rect of Rome, Athens, Babylon and Susa has no snow pixels (snow overlay count 0); Pārsa,
  Pasargadae, the Persian Gates, the Halys and the Apennines have snow above their lines; Babylon
  never has a snow overlay in any month.
- **Trees are right:** in winter, plane and poplar sprites resolve to `@bare`, olives, pines and
  cypresses to plain (scripted `expect sprite`); in October `med_*` vines show `@turn` or `@fruit`.
- **Life is right:** Ostia in January has ≤ 20 % of its July ship tokens and shows hulls ashore;
  the Apennine pastures have the flock in July and none in January; Pārsa's terrace has no
  delegations in August; cranes cross Attica in October.
- **Determinism:** `determinism_check` passes across a month wave and a first snow.

### 7.2 Performance cases (engine, in `--bench` and `--soak`)

| Case | Gate |
|---|---|
| `season_turn`: Rome's busiest view during a turn wave (ground re-bakes, cross-fades, 3× leaf fall) | whole frame p99 ≤ 8.3 ms, worst ≤ 16.6 ms; CPU ≤ 2 ms average |
| `snow_city`: the Pārsa terrace at night in a January front, cover rising, lamps lit | as above |
| `flood`: Babylon on the flood's first morning | as above |
| Overview during a season pin (impostor and tint refresh) | as above; no frame over 16.6 ms |
| Season pin flip at 1440p in a city (the 3-second wave) | as above |
| Soak: 600 s across four turns (exists) and a January front | memory flat after the first quarter; simulation ≤ 0.6 ms average |
| `lifeinfo bench`: each city at its busiest festival in each season | simulation and enumeration within the existing gates; ≤ 800 live |

---

## 8. Notes for the bibles and the other design documents

These are places where the existing documents or data need a note or a change. Owners decide;
none blocks the plan.

| Where | Note |
|---|---|
| `living-corner.md` §2.1, §13; `living-world.md` §4.1, §4.3 | Already "one calendar, global seasons": this document keeps that and adds months and climates. `living-world.md` §4.3's five-row climate table is superseded by §2; its "Olive harvest: autumn, all days" becomes November to January. |
| Region files today | `season` pins in `rome`, `athens`, `parsa`, `ostia`, `brundisium`, `alban_mount` freeze the season and must go; captions that name a season ("Rome · the Parilia, 21 April AD 126") become `moment.caption`, with `era.caption` for the other days. Babylon, Susa, the Zagros and the steppe use the `parsa` climate today; they get their own. |
| Rome festival data | Saturnalia (17–23 December) is winter day 1, not day 2. Ludi Apollinares (6–13 July) is summer day 2, not day 3. Vinalia Priora is 23 April (spring day 2); if it must not overlap the Parilia, keep it small, or show the Vinalia Rustica (19 August, summer day 3) instead. |
| `rome.md` §7.3 and the `starlings` event | Starling murmurations over Rome are an autumn and winter sight (October to February); in late April they are thin. Keep the event for autumn and winter. |
| `persepolis.md` §1, §6.8 | Xenophon (*Cyropaedia* 8.6.22) gives the king seven winter months in Babylon, three spring months in Susa and two summer months at Ecbatana. The spring audience at Pārsa is a modern reading; the card should say "perhaps". The bible's "court at Ecbatana in late summer" agrees with Xenophon. |
| `athens.md` §1 | The game's Athenian year now runs to February 431, still at peace; the outbreak of the war (spring 431) is never shown, because spring returns to 432. Worth one line in the bible. |
| `look.md` §3.6 | "City roofs keep their art (a whole winter set per city is out of budget)" is superseded: roofs take snow by the snow-catcher bit on the shader path, where snow is historically right, with no duplicated art. |
| `look.md` §4.4 | "Normal maps: not worth it" still holds for relighting; the snow pass needs one bit, and uses normals only if the R&D adopts them. |
| `world.md` §1, §8 | Each region is "remembered as it was in one moment": now one moment **and its year**. The seam captions add the season. |
| `world-tech.md` §1.7 | "Seasonal looks … (`…/autumn`, `…/winter` segments)" is replaced by the `@<state>` suffix of §4.3. Page budgets stand. |

---

## 9. Sources

Historical and climatic claims in this document rest on the following. Internal sources are the
city bibles (`rome.md`, `athens.md`, `persepolis.md`, with `fact-check.md`) and `sources.md`.

| Claim | Source |
|---|---|
| The sea closed from 11 November to 10 March; risky in spring and autumn; ships still sailed for profit | Vegetius, *Epitoma rei militaris* 4.39; discussion in J. Beresford, *The Ancient Sailing Season* (Brill 2013), review: https://www.talanta.nl/wp-content/uploads/2017/08/review-Stronk.pdf; https://www.romanports.org/en/articles/human-interest/156-winter-shipping.html |
| The Navigium Isidis (5 March) opened the sailing season | Apuleius, *Metamorphoses* 11; https://www.britannica.com/topic/mystery-religion/Seasonal-festivals; https://en.wikipedia.org/wiki/Navigium_Isidis |
| Harvest at the Pleiades' rising, ploughing at their setting; the crane's cry calls the ploughing; pruning before the swallow; vintage when Arcturus rises at dawn; winter clothing; the ship drawn ashore in winter | Hesiod, *Works and Days* 383–384, 448–451, 536–546, 564–570, 609–614, 618–630 (Evelyn-White translation): https://cts.perseids.org/read/greekLit/tlg0020/tlg002/perseus-eng2/365-455 and https://cts.perseids.org/read/greekLit/tlg0020/tlg002/perseus-eng2/545-640 |
| The Persian king's seasonal residences (Babylon in winter, Susa in spring, Ecbatana in summer) | Xenophon, *Cyropaedia* 8.6.22: https://cts.perseids.org/read/greekLit/tlg0032/tlg007/perseus-eng2/8.6.21-8.6.23 |
| Deep snow on the Armenian and east Anatolian highlands in winter | Xenophon, *Anabasis* 4.4–4.5: https://cts.perseids.org/read/greekLit/tlg0032/tlg006/perseus-eng2/4.5.17-4.5.36 |
| Snow and ice at the Persian Gates in January 330 BC | Arrian, *Anabasis* 3.18; Curtius 5.3–4; https://www.livius.org/articles/battle/persian-gate-330-bce/ |
| Persian royal couriers ran in all weathers | Herodotus 8.98 |
| Susa's summer heat | Strabo, *Geography* 15.3.10 |
| The Tigris and Euphrates flood in April and May from snowmelt, with a small winter rise; harvests in spring | https://www.britannica.com/place/Tigris-Euphrates-river-system/Economy; https://science.nasa.gov/earth/earth-observatory/annual-floods-return-to-iraq-4212/; https://en.wikipedia.org/wiki/Agriculture_in_Mesopotamia; study of Babylonian harvest dates: https://link.springer.com/article/10.1007/BF00166177 |
| Transhumance between the Apennines and the Apulian plains | Varro, *De re rustica* 2.1.16, 2.2.9 (Thayer): https://penelope.uchicago.edu/Thayer/E/Roman/Texts/Varro/de_Re_Rustica/2*.html; https://en.wikipedia.org/wiki/Transumanza |
| Roman monthly farm work (shearing in May, hay in June, vintage, olive gathering in December) | the *menologia rustica* (CIL VI 2305): https://en.wikipedia.org/wiki/Menologia_rustica |
| Snow on the hills in sight of Rome in winter; the rare severe winter in the city | Horace, *Odes* 1.9 (Soracte under snow); Livy 5.13 (the winter of 398 BC: roads blocked, the Tiber unnavigable) |
| Tiber floods in winter | Tacitus, *Histories* 1.86 (January AD 69) |
| Augustus's four tunics in winter and broad hat against the sun | Suetonius, *Augustus* 82 |
| Delphi's winter months given to Dionysus, the paean silent | Plutarch, *On the E at Delphi* 388e–389c |
| The Etesian (meltemi) winds of high summer | Aristotle, *Meteorology* 2.5 |
| Nightingales at Kolonos by the Academy | Sophocles, *Oedipus at Colonus* 668–678 |
| Athens: rain mostly November to March, dry June to September, snow rare in the city and common on the surrounding mountains | https://weather.metoffice.gov.uk/travel/holiday-weather/europe/greece/athens; https://www.climates.com/EUROPE/PDF/GRC01EUR.pdf |
| Persepolis at 1,600 m: frosty winter nights, light and infrequent snow | https://www.climatestotravel.com/climate/iran (approximate; modern climate as a guide to the ancient) |

Modern climate data is used as a guide to ancient conditions, which were broadly similar in these
regions over the last 2,500 years; where the game shows a rare event (Rome's dusting, Athens's
flurry, Pārsa's January snow), it is shown as rare.
