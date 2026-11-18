# The `world` set: the land and sea between the cities

Design of the shared art set and its catalog. The draft catalog is
`docs/design/sets/world.catalog.json` (same schema as the city set catalogs; copy it to
`assets/sets/world/catalog.json` to make it the contract). Every `world.*` id in this file is in
that JSON and the reverse; ids proposed for a city set are marked **＋ proposal** and are not in it.

Read with: `docs/design/world-tech.md` §1 (art contract), §3.8 (base layer); `cities/world.md`
(the plan); the waypoint tables `rome.md` §3.7, `athens.md` §3.7, `persepolis.md` §3.7;
`living-world.md` §2–§6 (actors, goods, events, weather).

Contents: 0 scope and rules · 1 terrain, faces, roads · 2 plants and natural props · 3 connective
kit · 4 waypoint towns · 5 people, animals, boats, goods · 6 sky, weather, markers · 7 seams ·
8 page budget · 9 for the world-builder · 10 for the engine and audio · 11 cut · 12 decisions ·
sources.

Legend: **M** must-have, **N** nice-to-have (the JSON marks N entries `"nice": true`; artgen and
worldgen ignore unknown fields, and the art agent builds N entries only when told). Footprints are
catalog `[x, y]` at `r0` (`x` = north–south rows, `y` = east–west columns, the convention of the
city catalogs); plan sizes in waypoint plans are written `c × r` (east–west × north–south).
Heights are px above the anchor at 64 × 32.

---

## 0. Scope and rules

### 0.1 What belongs in `world`

One rule, checkable against the layer files:

1. **Natural things**: terrain, rock, water, sea, snow, the plants and props a stretch needs that
   its era's set does not already have, wild and farm animals of the countryside, birds, sea life,
   weather, backdrops.
2. **The base layer's built things**: everything worldgen places in the connective stretches
   (roads, crossings, roadside and coastal kit, farms' small structures, river and sea craft,
   travellers), **for every era**, unless the era's set already has an equivalent (then the base
   uses the set's id: `rome.r_milestone`, `rome.mutatio`, `athens.g_herm`, `parsa.p_well` …).
3. **Not in `world`**: the unique landmarks of waypoint towns. They live in their era's set (as the
   Roman ones already do: `rome.brundisium_harbour`, `rome.latiaris` …) because town layers are
   authored with their set's kit and load its pages anyway. §4 lists them per town.

Consequence for builders (**region-set rule**): a tile in a region whose set is S may carry ids of
`home`, `world` and S only; seam regions (`seam_ionia`, `seam_ionian`, `seam_dell`) may also use the
sets on both sides. The engine always has `home` and `world` resident and loads S near S's
regions (world-tech §4.5), so this rule is what guarantees no missing sprite.

### 0.2 Ids already used as stand-ins

Worldgen's `plan/provisional.py` and the committed layers use these `world.*` ids; all are kept
with the same meaning: `world.sand`, `world.steppe`, `world.alluvium`, `world.sea`,
`world.shallows`, `world.river`, `world.rock`, `world.snow`, `world.marsh`, `world.road_earth`,
`world.field`, `world.scree`, faces `world.earth`, `world.coast`, `world.rock`, `world.snow`;
`world.t_oak`, `world.t_beech`, `world.t_fir`, `world.t_cedar`, `world.t_tamarisk`,
`world.t_reeds`, `world.wayside_shrine`, `world.milestone`, `world.stair_earth`, `world.ramp`,
`world.ford`.

**Retired** (a set already has one; worldgen maps them, V1 will flag leftovers):

| Stand-in | Use instead | Why |
|---|---|---|
| `world.t_plane` | `athens.t_plane`, `parsa.t_plane`, `rome.t_plane` by region set | all three sets made a plane |
| `world.t_poplar` | `athens.t_poplar`, `parsa.t_poplar`, `rome.t_poplar` | likewise |
| `world.t_pine_aleppo` | `athens.t_pine` | Attica's pine exists |

**Redefined:** `world.t_palm` is kept, now as *palm clumps and young palms* (two looks) beside
`parsa.t_date`'s two single palms, so groves of four looks do not repeat.

The Royal Road in `ROUTES` should paint `world.road_royal` (new) instead of `world.road_earth`.

### 0.3 Era of each asset

World assets are either era-neutral (rock, a jetty, a sheep) or carry the look of the era of the
stretches they serve, stated per row. Nothing in `world` may contradict the moment of the region it
is placed in: no lateen sails, no water wheels (the noria is not attested before the Hellenistic
period), no stirrups, no horseshoes, no windmills, no stone theatre at Delphi (§4.8).

---

## 1. Terrain, faces and roads

### 1.1 Terrains

Three bases, everything else overlays (16 masks, rounded where a neighbour differs, `under` drawn
beneath). The `under` of each overlay is chosen so the **rim it exposes is a plausible margin**:
water shows a sand or gravel bank, rock and snow show dry earth, marsh shows mud. That makes
transitions between any overlay and any set's base read as a natural edge without extra tiles.

| Id | Kind | M/N | Look (what must be right) | Where |
|---|---|---|---|---|
| `world.sand` | base, 4 variants | M | warm pale sand, faint ripples on 2 variants, scattered shell and pebble flecks | beaches, desert, river banks under water overlays |
| `world.steppe` | base, 4 variants | M | pale gold dry grass in tussocks over buff earth, stony flecks; 1 variant greener | Anatolia, Syrian steppe, Zagros, bands' foot |
| `world.alluvium` | base, 4 variants | M | grey-brown silt with green patches and dried mud cracks on 1 variant | Mesopotamia, Susiana, river deltas |
| `world.sea` | overlay on sand, 4 frames | M | deep blue with slow swell highlights; depth tint by the engine (world-tech §1.8); frames loop seamlessly | all seas |
| foam | `terrain/world.sea/foam/m<mask>/f<k>`, 16 × 4 | M | white surf lines along the edges facing land (mask = land neighbours), foam fading outward | every sea tile touching land |
| `world.shallows` | overlay on sand, 4 frames | M | turquoise over visible sand ripples, sparkles; meets `world.sea` edge-to-edge (same frame timing) | first 1–2 sea tiles off beaches, lagoons, the sacred lake of Delos |
| `world.river` | overlay on sand, 4 frames | M | green-brown river water, darker centre, bank shimmer; reads at 1 tile wide (canals) | rivers, canals |
| flow | `terrain/world.river/flow_n|e/f<k>`, 8 frames | M | faint streaks and bubbles scrolling downstream; additive-free alpha | river tiles (aux = direction) |
| `world.rock` | overlay on steppe | M | grey limestone outcrop, bedding lines, lit upper-left lips, a tuft in cracks | hills, mountain bands, cliffs' tops |
| `world.snow` | overlay on steppe | M | spring snow patches with rock showing through on the rims (April/spring in every era east and west) | tops above level 11 |
| `world.scree` | overlay on steppe | M | pale angular rubble fans | under cliffs, gorges, pass flanks |
| `world.marsh` | overlay on alluvium | M | wet green-black mud, pools with glints, sedge tufts | river mouths (Ephesus, Kaystros), Mesopotamian marsh, Pontine coast |
| `world.road_earth` | overlay on steppe | M | packed brown earth, two worn wheel ruts and a hoof lane, stones pushed to the verge | Greek roads and tracks, the corner road, farm tracks everywhere |
| `world.road_royal` | overlay on steppe | M | a broad graded road: pale compacted gravel over earth, raised camber, shallow ditch lines at the masked edges, no ruts (graded and kept) | the Royal Road, the Pārsa–Pasargadae road |
| `world.field` | overlay on steppe | M | ploughed furrows (diagonal to the tile so masks continue), clods; reads as ploughland or fallow-ploughed | fields of the Persian stretches and Thrace; Italy and Greece use `rome.field_spring`, `athens.field_stubble` |
| `world.scrub` | overlay on steppe | M | grey-green garrigue: low cushions, bare stony ground between | Mediterranean hills of every era, islands |
| `world.forest_floor` | overlay on steppe | M | dark leaf litter, moss, fallen twigs, a fern | under woods (beech, oak, fir, cedar) so canopies sit on shade |
| `world.dune` | overlay on sand | M | wind ripples and crests, lit and shadowed sides | Syrian desert edge, coastal dunes |
| `world.gravel_desert` | overlay on sand | M | dark varnished pebbles on buff ground (hamada) | Syrian desert south of the steppe |
| `world.salt_flat` | overlay on sand | N | white crust with polygon cracks | salt pans, Gulf shore, the plateau's kavir edges |
| `world.fallow` | overlay on steppe | N | weedy stubble with grazing paths | fields at rest |
| `world.pasture` | overlay on steppe | N | lush short green grass with flowers | Thrace, Ionian valleys, high Apennine meadows in April |

Vineyard and orchard floors come from the sets (`rome.vineyard_soil`, `athens.olive_soil`,
`parsa.garden_bed`); the world adds none.

### 1.2 Where bases meet

Two bases never touch (world-tech §1.7). Each base boundary is placed under something that hides
it:

| Boundary | Hidden under |
|---|---|
| `rome.grass_spring` ↔ `world.sand` | the coast (sea overlays) |
| `athens.dry_grass` ↔ `world.steppe` | the Ionian haze seam band (C 852..859) and the Hermos |
| `world.steppe` ↔ `world.alluvium` | the Euphrates and Tigris (rivers expose sand), else a 2-tile `world.field` band |
| `world.steppe` ↔ `parsa.plain_grass` | the Zagros rock band, else a `world.scree` / `world.rock` ridge |
| `world.steppe` ↔ `world.sand` (desert) | a `world.gravel_desert` band 3–6 tiles wide (its rim exposes sand) |

Inside one base, biomes change by overlay patches with noise edges (2–4 tiles of dithered
patches), never straight lines.

### 1.3 Faces (edge materials)

`edge/<material>_<se|sw>/v0..3` plus `…/top`, one level (16 px) each, stacked.

| Id | M/N | Look | Used by |
|---|---|---|---|
| `world.rock` | M | grey limestone strata, lit lips, undercuts, a shrub on a ledge; rim band with grass | hills, mountains, Delphi's cliffs, Persian Gates, Acrocorinth |
| `world.earth` | M | layered brown earth, pebbles, roots; grassy lip | river terraces, tells (Susa mound), field steps |
| `world.snow` | M | rock face with snow on ledges and a snow cornice in `top` | peaks |
| `world.coast` | M | sea cliff: wave-cut notch at the foot, animated foam 4 frames (`…/v<n>/f<k>`), salt-stained band | headlands, islands, the corner's cliff |
| `world.basalt` | N | dark columnar basalt with rusty weathering | Vesuvius, Etna, Argaios, Hauran |

The sets keep their own (`athens.limestone`, `parsa.rock`, `rome.tufa` …). The Parsa art pass
proved the method (`terrain.py` `cliff`, `materials.ashlar` strata, `arch.field_fill`).

### 1.4 Roads by civilization and how they join

| Road | Terrain | Kit along it | Join |
|---|---|---|---|
| Roman via (Appia, Ostiensis, Aurelia) | `rome.basalt_paving` (polygonal basalt with kerbs, exists) | `rome.r_milestone`, tombs, pines, `rome.mutatio`, `world.bridge_arch` | at Rome's portals; ends at Brundisium's quay |
| Greek road and cart track | `world.road_earth` | `athens.g_herm` at junctions, grave stelai near towns, `athens.g_shrine`, `world.terrace_wall` on slopes, `world.cairn` (N) on passes | Athens' four portals; Delphi way, Corinth |
| Persian Royal Road | `world.road_royal`, width 2 | `world.royal_station`, wells and troughs (`parsa.p_well`, `parsa.p_trough`), `world.watchtower`, `world.beacon` | Sardis (`parsa.royal_road_head`) → Pārsa portal `royal_road_w` |
| The corner's old road | `world.road_earth`, width 1 | `world.milestone`, `world.wayside_shrine`, `world.stile` at the dell | corner → Rome `aurelia_w` |

Roads of different eras never meet (seams sit between them); a road of one era meets a town of the
same era at its portal, where the town's own paving takes over on the portal tile.

---

## 2. Plants and natural props

### 2.1 New plants and props

Each is a small family of looks (`variant` layout) so repeated scattering does not tile. Only the
reed bed sways (2 frames); trees are static as in the city sets.

| Id | Looks | H | M/N | Look and facts | Serves |
|---|---|---:|---|---|---|
| `world.t_oak` | 4 | 85 | M | deciduous oak (downy/Turkey/valonia type): broad lobed-leaf crown, grey furrowed trunk; r0 full round, r1 old pollard, r2 young, r3 lopsided field oak | Italy's hills, Epirus, Thrace, Anatolia |
| `world.t_oak_zagros` | 3 | 60 | M | Persian (Brant's) oak: low, broad, open crown, several stems from the base, dry grass under; grows in open park woodland, not closed forest | Zagros, the plateau's edges |
| `world.t_beech` | 3 | 95 | M | smooth silver trunk, dense rounded crown, fresh April green | Apennines, Thrace |
| `world.t_fir` | 3 | 105 | M | silver/Greek fir: dark narrow cone, level branches, snow-tipped look on r2 | Apennines, Pindus, Arcadia, Taurus |
| `world.t_cedar` | 2 | 115 | M | cedar of Lebanon: flat tiered layers, massive trunk; the Taurus and Lebanon cedars were the timber of empires (Assyrian and Persian texts; the Darius Susa foundation charter names cedar from Lebanon) | Taurus, Lebanon band |
| `world.t_pistachio` | 2 | 55 | M | wild pistachio (*Pistacia atlantica*): rounded grey-green crown, short trunk, reddish fruit clusters | Zagros, plateau, Syrian steppe wadis |
| `world.t_tamarisk` | 3 | 45 | M | feathery grey-green shrub-tree, pink plumes on r1 | desert rivers, Gulf shore, Mesopotamian banks |
| `world.t_palm` | 2 | 100 | M | r0 a clump of three date palms of different heights with offshoots, r1 a young palm, fronds to the ground | with `parsa.t_date` in Mesopotamia, Susiana, the Gulf, the Levant |
| `world.t_reeds` | 4 | 44 | M | tall reed bed (*Phragmites*/giant reed), plumes, sways in 2 frames; walkable, `on: any` | every river margin and marsh (the city reeds are 30 px garden reeds) |
| `world.p_maquis` | 4 | 26 | M | evergreen scrub cushions: kermes oak, lentisk, strawberry tree (red fruit), broom in flower | Med hills of Italy, Greece, Ionia, Cyprus |
| `world.p_thistle` | 3 | 14 | M | spiny thistles, camelthorn tufts | steppe, fallow, roadsides |
| `world.p_wildflowers` | 6 | 8 | M | r0 red poppies and white chamomile (Italy, April); r1 blue chicory and yellow composites (Greek summer); r2 red tulips and irises (Zagros, plateau, spring); r3 small yellow and white desert daisies (steppe spring); r4 sea squill spikes and sea lavender (coasts, late summer); r5 red anemones and grape hyacinths (Anatolia, spring). Worldgen picks the look by stretch | everywhere, sparsely |
| `world.t_juniper` | 3 | 50 | N | twisted juniper, flaking red bark | Anatolia, Arcadia, Zagros |
| `world.t_cork_oak` | 2 | 75 | N | thick corky bark, stripped orange-red lower trunk on r1 | Latium, Sardinia, Corsica |
| `world.t_oleaster` | 2 | 50 | N | wild olive: scrubby, many-stemmed | Levant, Cyprus, Lydia (parsa regions have no olive) |
| `world.boulder` | 4 | 18 | M | r0–r1 grey limestone, r2 red sandstone, r3 dark basalt | everywhere |
| `world.crag` | 3 | 48 | M | 2 × 2 rock tor with a shrub; breaks up mountain flats and frames passes | bands, passes, islands |
| `world.peak` | 3 | 130 | M | 3 × 3 summit: r0 limestone horn with snow streaks, r1 snow dome, r2 volcanic cone with a crater lip (Vesuvius after AD 79, Etna, Argaios) | summits ≥ level 11 (world.md §4 "peak sprites") |
| `world.driftwood` | 2 | 6 | N | bleached logs on sand | beaches |

### 2.2 Plants already in the city sets (do not duplicate)

Umbrella pine, cypress, plane, holm oak, laurel, myrtle, fig, olive, vine, box, poplar, reeds,
poppy (`rome`); olive, plane, cypress, pine, fig, vine, poplar, agnus, oleander, myrtle, laurel,
thyme, asphodel, reeds (`athens`); cypress, plane, poplar, willow, pomegranate, almond, vine, date,
fig, barley, wheat, steppe grass (`parsa`). Biome palettes per stretch are in §9.3.

---

## 3. Connective kit

Artists: the Roman, Greek and Persian toolkits apply as noted (`arch.py`: walls, stairs,
`mudbrick_wall`, `flat_roof`, `tent`, `merlons`; `materials.py`: `ashlar`, `mud_plaster`,
`roof`, `timber`, `beam_ends`, `stain`; `greek.py`: `house_wall`, `tiled_roof`, `herm`, `stele`;
`roman.py`: `arch_mask`, `wall`, `opening`; `terrain.py`: `cliff`, `water`). The world palette is
home + a `world` colour list; reuse the parsa and athens ramps for mudbrick, plaster, limestone,
timber and tile so world kit sits beside city kit without a seam.

| Id | Fp | Layout | H | M/N | Look and facts | Toolkit |
|---|---|---|---:|---|---|---|
| `world.ford` | 1×1 | variant 2, on water, walkable, `crossing` | 6 | M | r0 stepping stones, r1 gravel shallows with marker poles | `terrain.water` |
| `world.bridge_arch` | 1×1 | connect, on water, walkable | 34 | M | Roman stone arch bridge: semicircular arches of grey limestone or tufa voussoirs, triangular cutwaters upstream, paved deck with a low parapet; masks give end ramps and middles. Rome era only (e.g. Pons Campanus over the Savo, the bridges at Beneventum) | `roman.arch_mask`, `materials.ashlar` |
| `world.bridge_timber` | 1×1 | connect, on water, walkable | 24 | M | oak trestles, plank deck, one hand-rail; era-neutral (Greek and Persian rivers; Herodotus 1.75 says Croesus crossed the Halys by bridges) | `materials.timber` |
| `world.pontoon` | 1×1 | connect, on water, walkable, 2 frames | 12 | M | boats moored side by side, planks laid across, rope rails; bob 1 px. Attested: Xenophon, *Anabasis* 1.2.5 (seven boats on the Maeander), 2.4.24 (37 boats on the Tigris at Sittake); used for the Tigris crossing between Babylon and Susa | `materials.timber` |
| `world.jetty` | 1×1 | connect, on water, walkable | 10 | M | oak piles, plank deck, bollards; `mooring`, `load` slots | — |
| `world.mole` | 1×1 | connect, on water, walkable | 14 | M | rubble breakwater with a dressed top and bollards; `mooring`, gull `perch` | `materials.ashlar` |
| `world.stair_stone` | 1×2 | rotate 4, rise 1 | 22 | M | rock-cut steps with worn treads (Delphi's sacred way, passes) | `arch.stair` |
| `world.stair_earth` | 1×2 | rotate 4, rise 1 | 20 | M | earth steps held by logs | `arch.stair` |
| `world.ramp` | 1×4 | rotate 4, rise 1 | 18 | M | graded earth ramp with a stone kerb (roads climbing) | — |
| `world.stile` | 1×1 | rotate 2, walkable | 18 | M | dry-stone wall stepped as a stile (the corner–Rome seam) | — |
| `world.milestone` | 1×1 | rotate 2 | 26 | M | plain uninscribed stone (the corner road; Roman roads use `rome.r_milestone`) | — |
| `world.wayside_shrine` | 1×1 | rotate 2 | 44 | M | rustic stone niche with offerings, no named god (the corner, world.md §7) | — |
| `world.royal_station` | 4×4 | rotate 4, glow | 52 | M | small Royal Road station: mudbrick walls on a stone footing, plastered; a flat-roofed range with beam ends, a reed-and-pole stable lean-to, trough, timber-lintel gate, a lamp; slots `door`, `change` (couriers), `horse` (the fresh horse waits), `trough`, `rest`. Persepolis Fortification texts record travel rations issued at stations about a day apart; Herodotus 5.52 counts 111 stations from Sardis to Susa and 8.98 the relay of riders | `arch.mudbrick_wall`, `flat_roof`, `materials.mud_plaster`, `beam_ends`, `roof` |
| `world.watchtower` | 2×2 | rotate 4, glow | 92 | M | square rubble tower, two storeys, timber parapet, ladder; fire emitter | `materials.ashlar`, `timber` |
| `world.beacon` | 1×1 | rotate 1, glow, slot state `lit` | 40 | M | brushwood pyre on a stone platform; lit at night or in events. Fire signals: Herodotus 9.3; Aeschylus, *Agamemnon* 281–316 | — |
| `world.sheepfold` | 3×3 | rotate 2 | 34 | M | dry-stone fold topped with thorn brush, a lean-to hut; `pen`, `gate` | — |
| `world.field_hut` | 1×1 | variant 2 | 34 | M | r0 corbelled stone hut (Med), r1 reed-and-brush shelter (East); `shelter` | — |
| `world.terrace_wall` | 1×1 | connect | 14 | M | dry-stone retaining wall a course above grade (olive terraces of the Gulf of Corinth, vineyards) | — |
| `world.charcoal_kiln` | 2×2 | variant 2, glow | 30 | M | r0 earth-covered stack smoking from vents, r1 wood stacked for covering; smoke emitter (Acharnai's charcoal burners, Aristophanes' *Acharnians*) | `fx` home `smoke` |
| `world.fish_hut` | 1×2 | rotate 4, glow | 40 | M | stone-and-reed hut, thatch, nets and oars leaning | — |
| `world.drying_rack` | 1×1 | rotate 2 | 26 | M | pole frame with nets and split fish; `mend` holds fish | — |
| `world.shaduf` | 1×1 | rotate 4, 2 frames | 52 | M | upright with a counterweighted sweep and bucket; dip and lift. Attested in Mesopotamia from an Akkadian seal (c. 2200 BC) to Assyrian reliefs | — |
| `world.reed_hut` | 2×2 | rotate 4, glow | 46 | M | arched reed-bundle house with mat walls (as on Uruk-period seals and Assyrian marsh reliefs) | — |
| `world.tumulus` | 3×3 | variant 2 | 40 | M | grassy earth mound; r0 with a stone ring wall (krepis) as at Lydian Bin Tepe, r1 plain | — |
| `world.inn` | 4×4 | rotate 4, glow | 60 | N | courtyard inn (Greek *pandokeion*, Roman *caupona*): rubble walls, tiled roof, gate, trough | `greek.tiled_roof`, `house_wall` |
| `world.cairn` | 1×1 | variant 2 | 14 | N | roadside stone heap (Greek *hermaion*), pass cairns | — |
| `world.matar_shrine` | 2×2 | rotate 2 | 70 | N | Phrygian rock-cut cult façade with geometric patterns and a niche (Phrygian highlands, 6th century) | `arch.field_fill` |
| `world.cistern` | 2×2 | rotate 2 | 14 | N | rock-cut cistern mouth with a stone lid and trough | — |
| `world.haystack` | 1×1 | variant 2 | 26 | N | straw stack, r1 half-used | — |
| `world.treading_vat` | 2×2 | rotate 2 | 18 | N | plastered treading floor draining to a vat (wine) | — |
| `world.boundary_stone` | 1×1 | variant 2 | 16 | N | rough field marker | — |
| `world.quarry` | 3×3 | rotate 4 | 50 | N | small stepped cut face, blocks, wedge slots (Tibur's travertine, roadside stone) | as `parsa.quarry` |
| `world.log_stack` | 1×2 | rotate 2 | 18 | N | cedar logs stacked for hauling | — |
| `world.salt_pans` | 2×2 | variant 2 | 8 | N | shallow pans with white crust, a heap | — |
| `world.tent_black` | 2×2 | rotate 2, glow | 32 | N | black goat-hair tent on poles (steppe herders and caravaneers; "the tents of Kedar") | `arch.tent` |

Inns of the Via Appia are `rome.mutatio` (exists); `world.inn` is the optional larger stop.

---

## 4. Waypoint towns

Each waypoint is a small authored layer (16–36 tiles) at landmark scale `s ≈ 0.5`. For each:
the moment, 3–8 assets (✔ exists, ＋ proposal for the era set, W `world`), key facts and
uncertainties, and a plan in **local plan coordinates** `(c, r)` from the north-west corner of the
town's rect in `world_plan.py` (`c` east, `r` south; the levels are the region's base level plus
the number given). A landmark's rect in a plan is its footprint laid in its true orientation, so
`c` extent × `r` extent is the catalog footprint `[x, y]` read as `[r, c]`. Landmark ids proposed for a city set follow the bibles' names with the set
prefix.

### 4.1 Rome's waypoints (April AD 126, under Hadrian)

**Ostia and Portus** (C 100..170, R 184..239; M) — built (worldgen WG2) with ✔ `rome.portus_hexagon`,
`rome.portus_lighthouse`, `rome.ostia_guilds`, `rome.ostia_capitolium`, insulae, horrea,
`rome.quay`, `rome.merchantman`, `rome.barge`. World adds W `world.jetty` and `world.fish_hut` at
the beach south of the Tiber mouth, W `world.fishing_boat`, W `world.gull` on the moles, and is the
port of the corner's sea lane.

**Tibur and Hadrian's Villa** (C 272..303, R 40..79; N). Assets: ✔ `rome.hadrian_villa` (22 × 24,
under construction since c. AD 118), ＋ `rome.tibur_temple` (N: the round temple above the Anio
falls, `roman.round_temple`), ✔ `rome.t_olive` groves (Tibur's olives), W `world.quarry` (travertine,
*lapis Tiburtinus*) with ✔ `rome.barge` on the Anio, ✔ `rome.r_villa_farm`. Uncertainty: which
villa parts stood finished in 126 (the Maritime Theatre was among the first). Plan: villa c 2..25,
r 14..35 on the plain at +0; Tibur on its hill c 22..31, r 0..12 at +3..5 (`world.rock` faces);
quarry c 26..28, r 20..22; Anio from the hill west along r 10..12.

**Alban Mount** (C 278..311, R 130..175; M). Assets: ✔ `rome.latiaris` (6 × 6) on the summit, the
crater lake (W `world.sea` centre with `world.shallows` rim, aux depth), ✔ `rome.r_villa_farm`
villas on the rim, W `world.t_oak` and `world.t_beech` woods on the upper slopes, ✔
`rome.t_stone_pine` near villas, the summit road in ✔ `rome.basalt_paving` (the paved *Via
Sacra* up Monte Cavo survives), ✔ `rome.r_tomb` and `rome.r_milestone` on the Via Appia at the
foot. Facts: the Latin Festival (*Feriae Latinae*) was held here each year by the consuls; the
temple's form is unknown (rome.md shows a small temple in a precinct). Plan: summit c 18..23,
r 4..9 at +8 with the sanctuary; lake ellipse c 4..15, r 14..27 at +3; woods r 0..30 above +4;
villas c 2..6, r 30..34 and c 24..28, r 28..32; Via Appia along r 40..45 at +0.

**Capua** (C 318..333, R 198..213; N). Assets: ✔ `rome.capua_amphitheatre` (8 × 10), ✔
`rome.r_scaffold` on its flank (an inscription records Hadrian's restoration and Antoninus Pius'
dedication, so works may be under way in 126: flagged), ✔ `rome.r_insula_low`, ✔ `rome.r_tomb`
along the Appia, ✔ `rome.mutatio`. Plan: amphitheatre c 3..12, r 3..10; town c 0..15, r 11..15;
Appia along r 12..13 east–west.

**Beneventum** (C 344..355, R 208..219; N). Assets: ✔ `rome.arch_beneventum` (1 × 3, dedicated 114)
where the Via Traiana leaves the Appia, W `world.bridge_arch` over the Sabatus (the Roman bridge at
Beneventum), ✔ `rome.r_milestone`, ✔ `rome.r_insula_low`. Plan: arch c 5..7, r 5 on the Traiana
fork; river r 9..10; bridge c 3..4.

**Brundisium** (C 380..407, R 248..279; M). Assets: ✔ `rome.brundisium_harbour` (12 × 16), the
marker column at the end of the Appia (✔ `rome.r_column_honor`; the surviving column's date is
debated, shown plain, rome.md §3.7), ✔ `rome.r_horrea`, ✔ `rome.merchantman`, W `world.mole` with W
`world.beacon` at its head, W `world.fishing_boat`, W `world.gull`, W `world.fish_hut`. Plan:
harbour c 8..23, r 6..17; column c 12, r 18 at the road's end; moles c 0..7, r 10..11 and
c 24..27, r 14..15; town c 4..20, r 19..30; the Ionian crossing lane leaves from c 26, r 22.

### 4.2 Greek waypoints (summer 432 BC, the last summer of peace)

**Corcyra / Kerkyra** (C 440..455, R 200..225; N). Assets: ✔ `athens.g_house`, ✔ `athens.trireme`
(Corcyra's fleet; allied to Athens since 433, Thucydides 1.44), W `world.mole`, W `world.jetty`,
＋ `athens.corcyra_artemis` (N: the archaic temple of Artemis, c. 580 BC, with the Gorgon pediment,
`greek.temple`). Plan: harbour c 2..7, r 10..16 on the east shore; town c 4..12, r 4..14; temple
c 8..13, r 16..20.

**Delphi** (C 500..519, R 250..265, base level 3; M). Assets: ＋ `athens.delphi_apollo`
(6 × 12; the Alkmaeonid temple, late 6th century, marble east front), ＋ `athens.athenian_treasury`
(2 × 3), ＋ `athens.stoa_athenians` (N: the Ionic stoa against the polygonal wall, after 479),
＋ `athens.serpent_column` (N, 479), ＋ `athens.castalian_spring` (N), the Phaedriades as relief
with W `world.rock` faces and W `world.crag`, the Sacred Way as `world.road_earth` with W
`world.stair_stone`, ✔ `athens.g_statue_base` and `athens.g_stele_inscr` along it, ✔ `athens.t_olive`
in the Pleistos valley below. **Correction**: no theatre in 432 — the stone theatre is 4th
century BC and any earlier arrangement is unknown; leave its site as open slope. The polygonal
terrace wall (c. 548) is the terrace's edge face (`athens.ashlar`). Plan: cliffs r 0..3 at +6..8,
impassable; temple terrace c 4..17, r 4..9 at +2 (temple c 6..17, r 4..9, long axis east–west,
front east); stoa below the terrace c 6..13, r 10 at +1; treasury c 3..5, r 11..12 at +1; Sacred
Way enters at c 18, r 15 and zigzags west then east up to the temple's east front; spring c 18..19,
r 6..7 in the gorge; olive slope r 12..15 at +0.

**Olympia** (C 470..491, R 320..340; N). Assets: ＋ `athens.olympia_zeus` (7 × 15, finished c. 456),
＋ `athens.pheidias_workshop` (4 × 8; its 430s date debated), ＋ `athens.olympia_stadium` (4 × 20),
✔ `athens.g_wall` for the Altis wall, ✔ `athens.t_olive` and `athens.t_plane`, the Alpheios
(base river, crossing the south-west corner r 16..20). Plan: Altis c 0..16, r 1..11 walled;
temple c 1..15, r 3..9 (long axis east–west); workshop c 1..8, r 12..15 outside the Altis' south
side; stadium c 18..21, r 0..19 east.

**Sparta** (C 515..535, R 360..385; N). Assets: ✔ `athens.g_house` and `athens.g_farmstead` in four
or five loose villages, ✔ `athens.g_shrine`, ＋ `athens.sparta_chalkioikos` (N: the small sanctuary of
Athena of the Bronze House on the low acropolis), the Eurotas (base), **no city wall** (Sparta was
unwalled in the 5th century). WG: add a small Taygetos band west of the rect for the backdrop of the
valley. Plan: villages at c 2..7, r 2..7; c 12..18, r 4..9; c 3..9, r 14..19; c 13..19, r 15..21;
acropolis c 8..12, r 9..13 at +2; Eurotas along c 18..20.

**Corinth** (C 553..575, R 280..305; M). Assets: ＋ `athens.corinth_apollo` (6 × 12, c. 540 BC,
stocky monolithic Doric columns, 6 × 15), Acrocorinth as **relief** (levels +2..+9, W
`world.rock` faces, impassable flanks, a zigzag path with W `world.stair_stone`) with ＋
`athens.acrocorinth_summit` (3 × 3: the small temple of Aphrodite and a wall circuit) replacing the
bible's 10 × 10 landmark (saves about 1 Mpx and looks better as real ground), ＋ `athens.diolkos`
(2 × 20, the paved ship trackway with a ship on a wheeled cradle), Lechaion and Kenchreai from W
`world.mole`, W `world.jetty`, W `world.beacon`, ✔ `athens.merchant` and `athens.trireme`, ✔
`athens.g_house` town. Plan: Lechaion c 1..6, r 2..6 on the gulf; town c 2..14, r 8..17; temple
c 4..15, r 10..15 (long axis east–west); diolkos c 15..16, r 2..21 across the isthmus; Kenchreai
c 17..22, r 14..19 on the Saronic side; Acrocorinth c 0..10, r 16..25, summit c 4..6, r 19..21.

**Eleusis** (C 556..575, R 222..250; M). Assets: ✔ `athens.telesterion` (10 × 10, Periclean rebuilding
under way, roof unfinished), ✔ `athens.g_wall` sanctuary wall, ✔ `athens.g_wall_gate` as the
propylon, ✔ `athens.g_house` town, ✔ `athens.field_stubble` on the Thriasian plain, W `world.jetty`
on the bay. Plan: acropolis hill c 0..6, r 0..8 at +2..3 (`world.rock`); Telesterion c 4..13,
r 6..15 at +1 against it; wall around c 3..15, r 5..17; gate c 14..15, r 10..11 facing the Sacred
Way, which arrives from the east edge (Athens' `sacred_way_w`); town r 17..22; shore r 24..28.

**Academy / Akademeia** (C 560..575, R 205..219; N). Assets: ✔ `athens.academy_grove` (10 × 12),
✔ `athens.t_olive` (the sacred olives) and `athens.t_plane`, ✔ `athens.g_grave_stele` along the road
from the Dipylon (the public cemetery lined it). Plan: grove c 3..14, r 2..11; road from the south
edge c 14, r 14 to the grove.

**Delos** (C 775..790, R 330..345; M). Assets: ＋ `athens.naxian_lions` (8 × 2, c. 600 BC, facing the
lake), ＋ `athens.delos_sanctuary` (10 × 8: the old poros temple of Apollo, the unfinished marble
temple begun after 478, the Artemision), the sacred lake (W `world.shallows`), W `world.mole` for the
sacred harbour, ✔ `athens.g_house`, ✔ `athens.g_grave_stele` (432 is before the Athenian
purification of 426/5 removed the graves to Rheneia; the League treasury had gone to Athens in 454).
**WG**: the plan's Delos polygon is about 7 × 8 tiles; enlarge it to about 12 × 13 inside
C 777..789, R 332..344 so the sanctuary and the terrace of lions fit. Plan (enlarged island):
harbour c 2..4, r 6..10 on the west shore; sanctuary c 4..13, r 4..11; lions c 5..12, r 12..13
facing a lake at c 6..10, r 14..15; Mt Kynthos c 11..14, r 9..14 at +3 (`world.rock`).

**Ephesus / Ephesos** (C 832..851, R 235..255; M). Assets: ＋ `athens.artemision` (8 × 16; the
archaic dipteral temple begun c. 560 with Croesus' carved column drums; Pliny gives 120 years of
building, so finishing work in 432 is possible: flagged), ✔ `athens.g_house` on the slopes, W
`world.marsh` and W `world.t_reeds` (the temple stood in the wet plain of the Kaystros), W
`world.mole`, W `world.jetty`, ✔ `athens.merchant`. Ephesus was a member of the Delian League.
Plan: harbour c 0..5, r 4..10 at the Kaystros mouth (base river ends c 7, r 11); temple c 2..17,
r 13..20 (long axis east–west, entrance west); town c 10..19, r 2..10 at +1..2; marsh around the
temple r 12..20.

### 4.3 Persian waypoints (spring c. 470 BC, under Xerxes)

**Sardis** (C 860..879, R 200..219, base 2; M). Assets: the acropolis as **relief** (+2..+7,
W `world.earth` faces read as its eroded slopes, impassable above +5) with ✔ `parsa.fort_wall`
and `parsa.fort_tower` on the crest (replacing the 10 × 10 landmark: saves about 1 Mpx), ＋
`parsa.royal_road_head` (4 × 4: the first station, a stone and an Aramaic sign panel), ✔
`parsa.p_house_small` (Herodotus 5.101: Sardis' houses were reed or reed-roofed mudbrick; the town
burned in 499 and was rebuilt), the Paktolos (W `world.river` 1 tile) with ✔ `parsa.labourer`
washing gold, ＋ `parsa.gold_refinery` (N: the 6th-century refinery by the Paktolos), ＋
`parsa.cybele_altar` (N: the stepped altar with lions beside it), W `world.tumulus` ×3 across the
Hermos (Bin Tepe, the Lydian royal mounds; Herodotus 1.93 on Alyattes' tomb). Plan: Hermos crosses
r 6..10 (base river); tumuli c 4..18, r 0..5 north of it; lower town c 2..18, r 10..14; Paktolos
c 4, r 11..19; acropolis c 6..15, r 12..19; road head c 9..12, r 11..14 with the road leaving east
along r 12.

**Halys crossing** (C 950..965, R 120..135, base 5; M). Assets: ＋ `parsa.halys_gates` (8 × 4: gate
towers and a guard post before the river, Herodotus 5.52), W `world.bridge_timber` across the
Halys, W `world.watchtower`, W `world.royal_station`, ✔ `parsa.guard_spear`, caravans. Plan:
river c 5..7, r 0..15 (base); gates c 0..3, r 6..13 straddling the road on the west bank (8 rows
north–south); bridge c 5..7, r 9..10; station c 10..13, r 4..7; tower c 12..13, r 11..12.

**Gordion** (C 905..925, R 130..150, base 5; N). Assets: ＋ `parsa.gordion_mound` (10 × 10: the great
mound, Tumulus MM, c. 740 BC, about 53 m high), W `world.tumulus` ×4, the citadel mound at +2 with
✔ `parsa.fort_wall`, ✔ `parsa.p_house_small`. Gordion was under Persia from c. 540 and prospered on
the roads (Penn excavations); WG: the Sangarios is missing from `RIVERS`. Plan: Tumulus MM
c 2..11, r 2..11; small mounds around c 12..19, r 0..6; citadel c 10..18, r 10..18.

**Sidon / Byblos harbour** (C 990..1007, R 300..340; N). Assets: ＋ `parsa.phoenician_harbour` (12 × 8)
or, cheaper, kit: W `world.mole`, W `world.jetty`, W `world.beacon`, W `world.phoenician`, W
`world.log_stack`, W `world.logger`, W `world.t_cedar` on the Lebanon slope, ✔ `parsa.p_house`.
＋ `parsa.eshmun` (N: the temple of Eshmun, begun by the 5th-century kings of Sidon). Plan:
harbour c 2..9, r 14..21; town c 8..16, r 10..26; logs on the shore c 3..6, r 24..26; cedars up
the slope east, c 12..17, r 0..12.

**Euphrates crossing** (C 1008..1023, R 170..185; M). Assets: ＋ `parsa.ferry_station` (6 × 6) or its
parts: W `world.jetty` landing stages on both banks, W `world.quffa` boats (Herodotus 1.194: round
boats of hide over willow frames, carrying a donkey), W `world.kelek` (N: log rafts on inflated
skins, Assyrian reliefs), W `world.royal_station`, ✔ `parsa.p_tent` camp, W `world.t_tamarisk` and
`world.t_reeds`, ✔ `parsa.t_poplar`. Uncertainty: the site (Thapsacus, Zeugma or Carchemish
are candidates; Herodotus says only that the river must be crossed by boat). Plan: river c 6..9,
r 0..15; landings c 4..5 and c 10..11 at r 7..9; station c 11..14, r 3..6; camp c 0..3, r 9..12;
`quffa` lane across r 8.

**Babylon** (C 1036..1071, R 285..316; M). Assets: ＋ `parsa.ishtar_gate` (6 × 4; blue glazed brick
with relief aurochs and *mušḫuššu*, Nebuchadnezzar II, c. 575 BC), ＋ `parsa.processional_way`
(2 × 14, glazed striding lions), ＋ `parsa.etemenanki` (12 × 12; recommend `s = 0.4`, height
≈ 210 px, to save area), ＋ `parsa.babylon_wall` (kit wall and tower), ＋ `parsa.euphrates_bridge`
(N; Herodotus 1.186: stone piers bound with iron and lead; the timber deck lifted at night is in
later commentary, not certain), ＋ `parsa.esagila` (N), ✔ `parsa.p_house` and `parsa.t_date`, W
`world.t_palm`, W `world.reed_boat`, W `world.quffa`, W `world.shaduf`. Etemenanki's state under
Xerxes is debated (persepolis.md §3.7): shown standing. Plan (the base Euphrates runs from c 12,
r 1 to c 20, r 27, 4 wide): Ishtar Gate c 30..35, r 1..4; inner wall west of it c 18..29, r 2..3,
towers every 3; processional way c 32..33, r 5..18; Etemenanki c 20..31, r 17..28; bridge (N)
c 10..19, r 22..23; Esagila (N) south of the tower if room, r 29..31; west bank houses c 2..11,
r 10..20 with palms c 0..10, r 5..30; groves north of the wall r 0..1; shadufs on canal banks every
6–8 tiles.

**Susa** (C 1080..1103, R 315..340; M). Assets: ＋ `parsa.susa_palace` (14 × 12: Darius' apadāna of
36 bull-capital columns beside courtyard buildings faced with glazed-brick archers, lions and
winged bulls), the citadel mound as relief (+4, W `world.earth` faces, `parsa.packed_earth` on top;
the bible's "terrain set" needs no new terrain), ✔ `parsa.p_house` town, the Shaur (base river
`karun`, W `world.river`), ✔ `parsa.t_date`, W `world.t_palm`, ＋ `parsa.susa_gate` (N: Darius'
gate). Plan: mound c 0..13, r 0..14 at +4; palace c 0..13, r 2..13; river c 14..18 diagonal;
town c 0..12, r 16..25 and c 18..23, r 4..20; palms along the river.

**Persian Gates** (C 1112..1127, R 330..345, base 6; M). Assets: ＋ `parsa.gates_station` (8 × 6: a
walled station with guards), the defile as relief (levels +6..+9 on both sides, W `world.rock`
faces, impassable), W `world.watchtower`, W `world.beacon`, W `world.t_oak_zagros`, W `world.crag`,
W `world.snow` on the tops. Facts: in 470 a guarded pass on the road to Pārsa (the battle of
330 BC is later; the site is debated between Tang-e Meyran and Tang-e Mohammad Reza). Plan: road
along r 7..8 west → east; cliffs r 0..5 and r 10..15; station at the west mouth where it widens,
c 0..7, r 5..10 (the road through its yard); watchtower on a ledge c 11..12, r 4..5 at +3;
beacon c 14, r 2 at +5.

**Pasargadae** (C 1176..1203, R 260..287, base 5; M). Assets: ✔ `parsa.cyrus_tomb` (5 × 5), ＋
`parsa.pasargadae_garden` (12 × 10: Palace P facing a garden with narrow stone channels and square
basins), ✔ `parsa.p_channel` and `parsa.water_channel`, ✔ `parsa.t_cypress` and `parsa.t_plane`,
＋ `parsa.pasargadae_gate` (N: Gate R with the four-winged figure; who it shows is debated), ✔
`parsa.p_house_small` as the magi's guardhouse by the tomb (Arrian, *Anabasis* 6.29: magi kept the
tomb and received a sheep a day), ＋ `parsa.tall_e_takht` (N: the stone platform on the hill).
Founded by Cyrus c. 546–530. Plan: tomb c 4..8, r 18..22 with the guardhouse c 9..10, r 20..21;
garden c 12..23, r 4..13; gate (N) c 16..21, r 16..21; road from the south edge c 14, r 27 (the
Pārsa road) north to the gate; platform (N) c 2..10, r 0..3 at +2.

### 4.4 Count and what the city sets must add

| Set | Waypoint landmarks to add | M | N | Est. area | Page room |
|---|---|---:|---:|---|---|
| `rome` | all exist; `rome.tibur_temple` (N) | 0 | 1 | 0.1 Mpx | in its 3-page budget |
| `athens` | corinth_apollo, acrocorinth_summit, diolkos, delphi_apollo, athenian_treasury, naxian_lions, delos_sanctuary, artemision (M); stoa_athenians, serpent_column, castalian_spring, olympia_zeus, pheidias_workshop, olympia_stadium, sparta_chalkioikos, corcyra_artemis (N) | 8 | 8 | M 2.6, N 1.3 Mpx | page 1 has ≈ 8 Mpx free: fits |
| `parsa` | ishtar_gate, processional_way, etemenanki, babylon_wall, susa_palace, gates_station, ferry_station, halys_gates, pasargadae_garden, royal_road_head (M); pasargadae_gate, euphrates_bridge, esagila, gordion_mound, phoenician_harbour, gold_refinery, cybele_altar, susa_gate, eshmun, tall_e_takht (N) | 10 | 10 | M 4.3 (with the two economies), N 2.0 Mpx | page 1 has ≈ 4.6 Mpx usable: M fits narrowly; N does not (§8.3) |

Estimates use the measured cost of built landmarks: ≈ 4–7 kpx per footprint tile for
temples and courtyards, ≈ 11 kpx per tile for tall gates and towers (base + shadow).

---

## 5. People, animals, boats and goods

### 5.1 Walkers on the shared rig

City sets already supply soldiers on the march (`rome.legionary`, `athens.hoplite`,
`parsa.guard_spear`, `parsa.archer`), farmers, shepherds, drovers, caravan drivers and the Persian
courier rider (`parsa.courier`) with the station groom (`parsa.groom`). `world` adds the kinds that
belong to every road and shore:

| Id | Variants | Poses | M/N | Dress (evidence and mistakes to avoid) |
|---|---|---|---|---|
| `world.traveller` | 3 | move, idle, sit, carry, carry_idle | M | v0 knee tunic, short pinned cloak, broad travelling hat on the back, staff and bundle (petasos on Greek vases; Romans travelled in the hooded paenula); v1 ankle tunic, wrapped shawl and head cloth (Near East); v2 woman in long tunic with the mantle over the head. Travellers of any origin are plausible on the roads (Ionian Greeks on the Royal Road, Syrians in Italy). Avoid pilgrim scallops, medieval hats |
| `world.merchant` | 2 | move, idle, talk, serve, carry, carry_idle | M | v0 Phoenician/Levantine: long fringed tunic with sash, conical cap or headband, beard; v1 Ionian Greek: chiton and himation |
| `world.muleteer` | 2 | move, idle, gesture, carry | M | belted knee tunic, felt cap (pilos), goad stick, bare feet or sandals |
| `world.fisher` | 2 | move, idle, work_low, haul, carry, carry_idle, sit | M | v0 loincloth or exomis and pilos, net over the shoulder; v1 short tunic, basket |
| `world.sailor` | 2 | move, idle, haul, carry, carry_idle | M | exomis, pilos or head cloth, rope coil; serves every harbour's dockside |
| `world.logger` | 2 | move, idle, haul, work_high | N | short tunic, axe; hauls logs (Lebanon) |

### 5.2 Animals and birds

The city sets have their own donkeys, mules, oxen, sheep, goats and dogs; the world's are the
ones used in every stretch (one flock looks the same on all roads; Pārsa's set has none of these).

| Id | Variants | Anims | M/N | Look |
|---|---|---|---|---|
| `world.donkey` | v0 bare, v1 with panniers | move, idle, graze | M | grey with the dark shoulder cross, long ears |
| `world.mule` | v0 bare, v1 pack saddle with bales | move, idle, graze | M | bay, taller than the donkey |
| `world.sheep` | v0 Mediterranean, v1 fat-tailed | move, idle, graze | M | v1: broad fat tail, the sheep of Mesopotamian art and Herodotus 3.113 |
| `world.goat` | v0 black long-haired, v1 brown and white | move, idle, graze | M | |
| `world.ox` | 1 | move, idle, graze | M | humpless dun working ox, long horns |
| `world.dog` | 1 | move, idle, run, sleep | M | light herding dog |
| `world.gazelle` | 1 | move, idle, graze | N | Syrian steppe |
| `world.gull` | 1 | move (fly), idle (perched) | M | yellow-legged gull |
| `world.stork` | 1 | move, idle, peck | M | white stork; spring nests on roofs (event P12) |
| `world.crane` | 1 | move | M | grey crane in V flocks (event W3) |
| `world.eagle` | 1 | move | M | soaring over bands and passes |
| `world.swift` | 1 | move | M | dusk swirls over towns (W4) |
| `world.raven` | 1 | move, idle | N | mountain bands |

Camels are `parsa.dromedary` and `parsa.bactrian_camel`; horses are the sets'. Herons, ducks and
frogs on Mesopotamian water reuse the home visitors (`heron`, `duck`, `frog`; the home page is
always resident). Dolphins and fish shoals are effects (§6.3).

### 5.3 Boats and ships

Triremes and Greek merchantmen are `athens.*`; Roman merchantmen and barges `rome.*`. Anims as
world-tech §1.9 (`move` sail full, `slack`, `row`, `idle` moored; 4 frames each, both facings);
crews baked in; sails blow to screen right.

| Id | Size | Anims | M/N | Look and facts |
|---|---|---|---|---|
| `world.fishing_boat` | 2 × 1 | move, slack, row, idle | M | open boat about 6 m, short mast with a small square sail, two pairs of oars, eyes painted at the bow (Greek, Roman and Phoenician boats all carried them), crew of two; serves the Tyrrhenian, Adriatic, the Gulf, the corner's coaster lane |
| `world.quffa` | 1 × 1 | move (paddled), idle | M | round hide-covered willow basket boat, one or two paddlers, sacks or a donkey aboard (Herodotus 1.194) |
| `world.reed_boat` | 2 × 1 | move (poled), idle | M | bundled reeds, upturned ends, bitumen-dark waterline, a poler and a load of dates or reeds |
| `world.kelek` | 2 × 1 | move, idle | N | log raft on inflated skins with a steersman |
| `world.phoenician` | 4 × 2 | move, slack, row, idle | N | round-hulled merchant ship, high stem and stern, horse-head prow ornament, square sail, two steering oars; sails in both the Greek and the Persian worlds |

### 5.4 Goods

`goods/<id>` carried (10–16 px) and `goods/<id>/s1..s3` stacks (≤ 24 × 20). The city sets have their
own bread, amphorae, sacks, fish and water jars for city chains; these are the road's and the sea's.

| Id | M/N | Look |
|---|---|---|
| `world.goods_sacks` | M | tied sacks of grain |
| `world.goods_amphorae` | M | pointed transport amphorae (generic) |
| `world.goods_bale` | M | cloth-wrapped, roped bale (caravans) |
| `world.goods_fish` | M | flat basket of fish |
| `world.goods_dates` | M | palm-leaf basket of dates |
| `world.goods_fleece` | M | rolled fleeces |
| `world.goods_letter` | M | sealed document in a pouch (couriers) |
| `world.goods_waterskin` | M | goatskin of water |
| `world.goods_firewood` | M | brushwood bundle |
| `world.goods_charcoal` | M | sacks of charcoal (Acharnai, Apennine burners) |
| `world.goods_reeds` | M | reed bundle |
| `world.goods_salt` | N | baskets of salt |
| `world.goods_logs` | N | cedar logs |

---

## 6. Sky, weather and markers

### 6.1 Backdrops

Strips stand only behind the **north and east** world edges (world.md §3.2). The Taurus and the
Zagros are interior bands: they are made of terrain levels, `world.rock`/`world.snow` faces and
`world.peak` sprites, not strips. Segments are `backdrop/<id>/day/v<n>`, 512 px per 16 edge tiles,
**at most 256 px tall** (half the Pārsa strip's height: the cost of a backdrop is almost all in its
height), ends matched so variants join.

| Id | Where | Variants | M/N | Look |
|---|---|---|---|---|
| `world.bd_far_hills` | every north and east edge without its own strip | 2 | M | blue-grey ranges in haze, two depths; grades well at any hour |
| `world.bd_alps` | north edge C 0..447 (corner, Rome, Apennines, Adriatic) | 2 | N | far snowy range over green foothills |
| `world.bd_pindos` | north edge C 448..879 (Pindos, Haemus, Thrace) | 2 | N | grey limestone ranges with snow patches |
| `world.bd_pontic` | north edge C 880..1135 (Pontic and Armenian ranges) | 2 | N | forested ranges under a cloud bank, white peaks far behind |
| `world.bd_plateau` | north edge C 1136..1279 and east edge R 0..303 | 2 | N | dry ochre ranges, a white volcanic cone far off |

The east edge R 304..447 is `parsa.kuh_rahmat` (exists). Night is the engine's grading of the day
strip (CLAUDE.md: grading is done by the engine, not baked); `night`/`winter` segments are optional
(§12, decision 4).

### 6.2 Weather sprites

Keys `weather/<kind>_v<n>` (world-tech §1.11; bare kind names, this is the only set with weather).
Soft, low-alpha, drawn by the engine over the ground as living-world §6.1 says.

| Kind | Variants | Size | M/N | Use |
|---|---|---|---|---|
| `cloud_shadow` | 4 | ≈ 192 × 96 | M | W6 cloud shadows; racing over the Anatolian steppe |
| `fog` | 4 | ≈ 384 × 48 strips | M | W2 valley fog; mist in Zagros gorges and on the Apennines |
| `dust` | 4 | ≈ 256 × 96 | M | W8 dust breeze (Persian stretches, Syrian steppe) |
| `seam_mist` | 4 | ≈ 512 × 96 | M | the pale golden Ionian mist bank (§7) |
| `seam_haze` | 2 | ≈ 384 × 64 | M | the Ionian-coast haze over the Kaystros hills (§7) |
| `squall` | 2 | ≈ 128 × 192 | N | a dark rain curtain under a storm cell at sea (W1) |
| `heat_shimmer` | 2 | ≈ 256 × 32 | N | heat over the Syrian steppe and Greek plains |

### 6.3 Effects

`fx/<id>/f<n>`: `world.whitecap` (open water at sea state ≥ 2), `world.wake` (behind ships),
`world.dolphin` (arcing beside a bow, S3), `world.dust_puff` (hooves and carts on dry roads),
`world.chaff` (threshing, L3), `world.lightning` (W1), `world.puddle` (wet ground, W7),
`world.fire` (beacon, watchtower), `world.shimmer` (golden motes in the seam mist), `world.spray`
(surf against cliffs and moles) — all M; `world.fish_shoal` (dark glinting patch) N. Reused from home:
`fish_jump`, `smoke`, `raindrop`, `snowflake`, `ripple`, `mist`.

### 6.4 Overview markers

`ui/marker_<icon>` (≈ 24 × 24, sepia ink on the paper map): M `home` (cottage), `rome` (dome and
column), `athens` (the Acropolis), `parsa` (stairway and two columns), `town` (a small drawn
tower), `town_unseen` (an open dot); N `port`, `pass`, `shrine`.

---

## 7. Seams between eras in art terms

| Seam | Marks | Assets |
|---|---|---|
| Corner ↔ Rome, the dell (C 88..103) | soft mist in the hollow, a dry-stone wall with a stile across the old road; the road turns from `world.road_earth` to Rome's paving only at Rome's portal | `world.stile`, `world.terrace_wall`, home `mist` |
| Italy ↔ Greece, the Ionian mist band (C 430..445) | a pale golden mist bank standing on the sea: `weather/seam_mist` strips drawn by the engine as a constant fog layer over every tile of the `seam_ionian` district, densest at C 436..440; `fx/world.shimmer` motes; no islands, props or wakes inside it; ships fade over 3 s at the seam ports (world-tech §4.11). The sea itself is unchanged, so the band reads as weather, not as a wall | `seam_mist`, `world.shimmer` |
| Greek ↔ Persian, the Ionian-coast haze (C 852..859) | a faint warm haze over the Kaystros hills: `weather/seam_haze` strips over the `seam_ionia` district, lighter than the sea mist; base terrain continues (`athens.dry_grass` to the Hermos, §1.2); the Ephesus–Sardis road crosses it and walkers turn back inside it; one `world.cairn` (N) at the crest | `seam_haze`, `world.shimmer` |

---

## 8. Page budget

### 8.1 Estimate

Areas are atlas rectangles (base + shadow + glow, all frames, all variants), estimated from the
measured `parsa` and `athens` pages: overlay terrain ≈ 28 kpx (16 masks), animated ≈ 110 kpx,
1 × 1 tree look ≈ 18 kpx with shadow, walker kind-variant ≈ 25–30 kpx, animals 50–115 kpx per
variant, fishing boat ≈ 100 kpx, merchant ship ≈ 450 kpx, 3 × 3 kit in 4 rotations ≈ 200 kpx,
backdrop segment ≈ 150 kpx at 256 px tall.

| Category | Must (n) | Must (Mpx) | Nice (n) | Nice (Mpx) |
|---|---:|---:|---:|---:|
| Terrain (3 bases, overlays) | 17 | 0.76 | 3 | 0.08 |
| Edge faces | 4 | 0.07 | 1 | 0.01 |
| Plants and natural props | 15 | 0.77 | 4 | 0.11 |
| Connective kit | 24 | 1.67 | 11 | 0.56 |
| Walkers | 5 | 0.32 | 1 | 0.05 |
| Animals and birds | 11 | 0.77 | 2 | 0.06 |
| Boats and ships | 3 | 0.21 | 2 | 0.50 |
| Goods | 11 | 0.02 | 2 | 0.00 |
| Effects | 10 | 0.06 | 1 | 0.01 |
| Weather sprites | 5 | 0.49 | 2 | 0.07 |
| Backdrops | 1 | 0.30 | 4 | 1.20 |
| Overview markers | 6 | 0.02 | 3 | 0.00 |
| **Total** | **112** | **5.47** | **36** | **2.65** |

One 4096² page is 16.78 Mpx; the Pārsa skyline packer filled page 0 to 93 %.

### 8.2 Verdict: one page, with room

- **Everything above, must and nice, fits in `world.0`** (8.1 Mpx of 16.8, about half the page).
  The must-have list alone is 5.5 Mpx.
- **Against a second world page.** The world page is resident everywhere. A second one costs 64 MB
  of GPU memory in every view, and in Rome (home 16 + world 128 + rome 3 × 64) it would reach
  336 MB, over the 320 MB page budget (world-tech §4.5, §4.14). There is no content that needs it.
- **What the free half is for** (in this order, each only on request): seasonal looks
  (`@autumn`, `@winter` for `world.steppe`, the deciduous trees and backdrops, ≈ 1.2 Mpx),
  night backdrop segments if the engine fallback is refused (≈ 1.5 Mpx), more looks for the
  commonest trees (≈ 0.3 Mpx), and the reserve for later stretches.

### 8.3 The Persian waypoints (not in `world`, but they decide a page)

The parsa set has two pages and ≈ 4.6 Mpx usable left on page 1. Its must-have waypoint
landmarks are ≈ 5.9 Mpx as the bible sizes them; with the two economies of §4.3 (Sardis'
acropolis as relief with existing wall kit, Etemenanki at `s = 0.4`) they are ≈ 4.3 Mpx and fit,
narrowly. The nice ones (≈ 2.0 Mpx) do not. Recommendation: build the must-haves on `parsa.1`; if
the nice ones are wanted, add `parsa.2` (it loads only near Persian regions: home 16 + world 64 +
parsa 192 = 272 MB, inside the budget). Do not put them on the world page: that would give
`world.*` ids to era landmarks and blur the rule of §0.1. (The alternative exists and is cheaper in
memory; it is the orchestrator's call, decision 6.)

---

## 9. For the world-builder

### 9.1 Ids and footprints

Art-only ids (no footprint): faces `world.rock`, `world.earth`, `world.snow`, `world.coast`,
`world.basalt` (N); backdrops §6.1; effects §6.3; weather §6.2; markers §6.4.

| Id | Kind | Footprint [x, y] | Layout × count | Height px | On | M/N | est. kpx |
|---|---|---|---|---:|---|---|---:|
| `world.t_oak` | item | [1, 1] | variant × 4 | 85 | land | M | 72 |
| `world.t_oak_zagros` | item | [1, 1] | variant × 3 | 60 | land | M | 50 |
| `world.t_beech` | item | [1, 1] | variant × 3 | 95 | land | M | 54 |
| `world.t_fir` | item | [1, 1] | variant × 3 | 105 | land | M | 54 |
| `world.t_cedar` | item | [1, 1] | variant × 2 | 115 | land | M | 74 |
| `world.t_pistachio` | item | [1, 1] | variant × 2 | 55 | land | M | 36 |
| `world.t_tamarisk` | item | [1, 1] | variant × 3 | 45 | land | M | 40 |
| `world.t_palm` | item | [1, 1] | variant × 2 | 100 | land | M | 58 |
| `world.t_reeds` | item | [1, 1] | variant × 4 | 44 | any | M | 28 |
| `world.p_maquis` | item | [1, 1] | variant × 4 | 26 | land | M | 16 |
| `world.p_thistle` | item | [1, 1] | variant × 3 | 14 | land | M | 6 |
| `world.p_wildflowers` | item | [1, 1] | variant × 6 | 8 | land | M | 9 |
| `world.t_juniper` | item | [1, 1] | variant × 3 | 50 | land | N | 36 |
| `world.t_cork_oak` | item | [1, 1] | variant × 2 | 75 | land | N | 36 |
| `world.t_oleaster` | item | [1, 1] | variant × 2 | 50 | land | N | 36 |
| `world.boulder` | item | [1, 1] | variant × 4 | 18 | land | M | 20 |
| `world.crag` | item | [2, 2] | variant × 3 | 48 | land | M | 60 |
| `world.peak` | item | [3, 3] | variant × 3 | 130 | land | M | 195 |
| `world.driftwood` | item | [1, 1] | variant × 2 | 6 | land | N | 4 |
| `world.ford` | item | [1, 1] | variant × 2 | 6 | water | M | 6 |
| `world.bridge_arch` | item | [1, 1] | connect × 16 | 34 | water | M | 112 |
| `world.bridge_timber` | item | [1, 1] | connect × 16 | 24 | water | M | 80 |
| `world.pontoon` | item | [1, 1] | connect × 16 | 12 | water | M | 96 |
| `world.jetty` | item | [1, 1] | connect × 16 | 10 | water | M | 64 |
| `world.mole` | item | [1, 1] | connect × 16 | 14 | water | M | 64 |
| `world.stair_stone` | item | [1, 2] | rotate × 4 | 22 | land | M | 44 |
| `world.stair_earth` | item | [1, 2] | rotate × 4 | 20 | land | M | 44 |
| `world.ramp` | item | [1, 4] | rotate × 4 | 18 | land | M | 80 |
| `world.stile` | item | [1, 1] | rotate × 2 | 18 | land | M | 8 |
| `world.milestone` | item | [1, 1] | rotate × 2 | 26 | land | M | 4 |
| `world.wayside_shrine` | item | [1, 1] | rotate × 2 | 44 | land | M | 10 |
| `world.royal_station` | item | [4, 4] | rotate × 4 | 52 | land | M | 420 |
| `world.watchtower` | item | [2, 2] | rotate × 4 | 92 | land | M | 140 |
| `world.beacon` | item | [1, 1] | rotate × 1 | 40 | land | M | 6 |
| `world.sheepfold` | item | [3, 3] | rotate × 2 | 34 | land | M | 80 |
| `world.field_hut` | item | [1, 1] | variant × 2 | 34 | land | M | 14 |
| `world.terrace_wall` | item | [1, 1] | connect × 16 | 14 | land | M | 80 |
| `world.charcoal_kiln` | item | [2, 2] | variant × 2 | 30 | land | M | 36 |
| `world.fish_hut` | item | [1, 2] | rotate × 4 | 40 | land | M | 56 |
| `world.drying_rack` | item | [1, 1] | rotate × 2 | 26 | land | M | 8 |
| `world.shaduf` | item | [1, 1] | rotate × 4 | 52 | land | M | 36 |
| `world.reed_hut` | item | [2, 2] | rotate × 4 | 46 | land | M | 100 |
| `world.tumulus` | item | [3, 3] | variant × 2 | 40 | land | M | 80 |
| `world.inn` | item | [4, 4] | rotate × 4 | 60 | land | N | 220 |
| `world.cairn` | item | [1, 1] | variant × 2 | 14 | land | N | 6 |
| `world.matar_shrine` | item | [2, 2] | rotate × 2 | 70 | land | N | 40 |
| `world.cistern` | item | [2, 2] | rotate × 2 | 14 | land | N | 20 |
| `world.haystack` | item | [1, 1] | variant × 2 | 26 | land | N | 10 |
| `world.treading_vat` | item | [2, 2] | rotate × 2 | 18 | land | N | 20 |
| `world.boundary_stone` | item | [1, 1] | variant × 2 | 16 | land | N | 4 |
| `world.quarry` | item | [3, 3] | rotate × 4 | 50 | land | N | 150 |
| `world.log_stack` | item | [1, 2] | rotate × 2 | 18 | land | N | 16 |
| `world.salt_pans` | item | [2, 2] | variant × 2 | 8 | land | N | 30 |
| `world.tent_black` | item | [2, 2] | rotate × 2 | 32 | land | N | 40 |
| `world.sand` | terrain, base | 1 tile | 4 variants | — | — | M | 8 |
| `world.steppe` | terrain, base | 1 tile | 4 variants | — | — | M | 8 |
| `world.alluvium` | terrain, base | 1 tile | 4 variants | — | — | M | 8 |
| `world.sea` | terrain, overlay on `world.sand` | 1 tile | 16 masks × 4 frames | — | — | M | 112 |
| `world.shallows` | terrain, overlay on `world.sand` | 1 tile | 16 masks × 4 frames | — | — | M | 112 |
| `world.river` | terrain, overlay on `world.sand` | 1 tile | 16 masks × 4 frames | — | — | M | 112 |
| `world.rock` | terrain, overlay on `world.steppe` | 1 tile | 16 masks | — | — | M | 28 |
| `world.snow` | terrain, overlay on `world.steppe` | 1 tile | 16 masks | — | — | M | 28 |
| `world.scree` | terrain, overlay on `world.steppe` | 1 tile | 16 masks | — | — | M | 28 |
| `world.marsh` | terrain, overlay on `world.alluvium` | 1 tile | 16 masks | — | — | M | 28 |
| `world.road_earth` | terrain, overlay on `world.steppe` | 1 tile | 16 masks | — | — | M | 28 |
| `world.road_royal` | terrain, overlay on `world.steppe` | 1 tile | 16 masks | — | — | M | 28 |
| `world.field` | terrain, overlay on `world.steppe` | 1 tile | 16 masks | — | — | M | 28 |
| `world.scrub` | terrain, overlay on `world.steppe` | 1 tile | 16 masks | — | — | M | 28 |
| `world.forest_floor` | terrain, overlay on `world.steppe` | 1 tile | 16 masks | — | — | M | 28 |
| `world.dune` | terrain, overlay on `world.sand` | 1 tile | 16 masks | — | — | M | 28 |
| `world.gravel_desert` | terrain, overlay on `world.sand` | 1 tile | 16 masks | — | — | M | 28 |
| `world.salt_flat` | terrain, overlay on `world.sand` | 1 tile | 16 masks | — | — | N | 28 |
| `world.fallow` | terrain, overlay on `world.steppe` | 1 tile | 16 masks | — | — | N | 28 |
| `world.pasture` | terrain, overlay on `world.steppe` | 1 tile | 16 masks | — | — | N | 28 |
| `world.traveller` | walker | — | v × 3 | — | — | M | 90 |
| `world.merchant` | walker | — | v × 2 | — | — | M | 60 |
| `world.muleteer` | walker | — | v × 2 | — | — | M | 56 |
| `world.fisher` | walker | — | v × 2 | — | — | M | 60 |
| `world.sailor` | walker | — | v × 2 | — | — | M | 52 |
| `world.logger` | walker | — | v × 2 | — | — | N | 50 |
| `world.donkey` | critter | — | v × 2 | — | — | M | 156 |
| `world.mule` | critter | — | v × 2 | — | — | M | 200 |
| `world.sheep` | critter | — | v × 2 | — | — | M | 102 |
| `world.goat` | critter | — | v × 2 | — | — | M | 100 |
| `world.ox` | critter | — | v × 1 | — | — | M | 115 |
| `world.dog` | critter | — | v × 1 | — | — | M | 50 |
| `world.gazelle` | critter | — | v × 1 | — | — | N | 50 |
| `world.gull` | critter | — | v × 1 | — | — | M | 8 |
| `world.stork` | critter | — | v × 1 | — | — | M | 15 |
| `world.crane` | critter | — | v × 1 | — | — | M | 10 |
| `world.eagle` | critter | — | v × 1 | — | — | M | 12 |
| `world.swift` | critter | — | v × 1 | — | — | M | 4 |
| `world.raven` | critter | — | v × 1 | — | — | N | 8 |
| `world.fishing_boat` | ship | [2, 1] | v × 1 | — | — | M | 100 |
| `world.quffa` | ship | [1, 1] | v × 1 | — | — | M | 40 |
| `world.reed_boat` | ship | [2, 1] | v × 1 | — | — | M | 70 |
| `world.kelek` | ship | [2, 1] | v × 1 | — | — | N | 50 |
| `world.phoenician` | ship | [4, 2] | v × 1 | — | — | N | 450 |
| `world.goods_sacks` | goods | — | stack 3 | — | — | M | 2 |
| `world.goods_amphorae` | goods | — | stack 3 | — | — | M | 2 |
| `world.goods_bale` | goods | — | stack 3 | — | — | M | 2 |
| `world.goods_fish` | goods | — | stack 3 | — | — | M | 2 |
| `world.goods_dates` | goods | — | stack 3 | — | — | M | 2 |
| `world.goods_fleece` | goods | — | stack 3 | — | — | M | 2 |
| `world.goods_letter` | goods | — | stack 3 | — | — | M | 2 |
| `world.goods_waterskin` | goods | — | stack 3 | — | — | M | 2 |
| `world.goods_firewood` | goods | — | stack 3 | — | — | M | 2 |
| `world.goods_charcoal` | goods | — | stack 3 | — | — | M | 2 |
| `world.goods_reeds` | goods | — | stack 3 | — | — | M | 2 |
| `world.goods_salt` | goods | — | stack 3 | — | — | N | 2 |
| `world.goods_logs` | goods | — | stack 3 | — | — | N | 2 |

### 9.2 Waypoint layouts

The plans are in §4 per town, in local plan coordinates of the town's rect. Each town layer: the
town's own landmarks from its set (placed once with their full rect), its set's houses by
`houses()`, world kit at the coordinates given, the route meeting the town at its portal on the
edge where the plan says the road arrives. Towns keep natural relief (worldgen choice 10), so
place relief first (cliffs, mounds, acropoleis), then water, then roads, then landmarks, then
houses and plants.

### 9.3 Biome rules: what grows and stands where

Weights are relative within a stretch; density is items per land tile outside fields and roads.
"Water" means within 2 tiles of river or marsh; "high" means level ≥ 8.

| Stretch (set) | Base | Overlays | Plants (weights) | Props | Animals |
|---|---|---|---|---|---|
| latium_italy (rome) | `rome.grass_spring` | fields `rome.field_spring`, `rome.vineyard_soil` near roads; `world.rock` on steep tiles; `world.marsh` on the Pontine coast | `rome.t_oak` 2, `world.t_oak` 2, `rome.t_olive` 2 (slopes, in rows), `rome.t_stone_pine` 1 (only by roads and villas: rome.md warns the city-wide pine look is partly modern), `rome.t_cypress` 1 (tombs), `rome.t_poplar` + `world.t_reeds` (water), `world.p_wildflowers` r0; density 0.05, forest 0.22 | `world.boulder`, `world.field_hut`, `world.haystack` (N), `rome.r_villa_farm` hamlets every 40 | `world.sheep` v0, `world.goat`, `world.ox`, `world.dog` |
| apennines (rome) | `rome.grass_spring` | `world.forest_floor` under woods; `world.rock`, `world.scree` from level 9, `world.snow` from 11 | `world.t_beech` 3, `world.t_oak` 2, `world.t_fir` 2 (high); forest 0.45 | `world.peak` on summits every ≈ 10 tiles, `world.crag`, `world.sheepfold` on high meadows (transhumance) | flocks on the drove road, `world.eagle`, `world.raven` (N) |
| tyrrhenian islands (rome) | `rome.grass_spring` | `world.scrub` 40 % | `world.p_maquis` 3, `rome.t_oak` 2, `world.t_cork_oak` (N) 1 | `world.boulder`, `world.fish_hut` coves | `world.goat` |
| greece (athens) | `athens.dry_grass` | `world.scrub` on hills 30 %, `world.rock`; `athens.olive_soil` on terraces with `world.terrace_wall` | `athens.t_olive` 3, `world.p_maquis` 2, `athens.t_cypress` 1, `athens.t_pine` 1, `world.t_oak` 1 (Epirus, the north), `athens.p_thyme`, `world.p_thistle`, `world.p_wildflowers` r1, r4 on coasts | `athens.g_farmstead` + `athens.g_threshing` hamlets, `world.field_hut`, `world.boulder` | `world.goat` 2 : `world.sheep` 1, `world.dog`, `world.donkey` |
| arcadia (athens) | `athens.dry_grass` | `world.forest_floor`, `world.rock` | `world.t_fir` 3, `world.t_oak` 2, `world.t_juniper` (N) | `world.peak`, `world.crag` | flocks |
| attica_north (athens) | `athens.dry_grass` | `athens.olive_soil` | `athens.t_olive` 4, `athens.t_pine` 1, `world.p_maquis` 1 | `world.charcoal_kiln` on Parnes' slopes, `world.terrace_wall` | `world.donkey` v1 with charcoal |
| thrace (athens, N) | `athens.dry_grass` | `world.pasture` (N) | `world.t_oak` 3, `world.t_beech` 1 | `world.tumulus` | flocks |
| ionia_lydia (athens) | `athens.dry_grass` | `athens.field_stubble`; `world.marsh` at river mouths | `athens.t_olive` 2, `athens.t_plane` 1, `athens.t_poplar` 1, `world.t_reeds` (water) | `world.fish_hut` | |
| anatolia (parsa) | `world.steppe` | `world.field` near rivers 5 %; `world.rock`, `world.scree` on hills; `world.basalt` faces (N) on Argaios | `parsa.p_steppe` 3, `world.p_thistle` 2, `world.t_oak` 1, `parsa.t_poplar` + `parsa.t_willow` (water), `world.t_juniper` (N), `world.p_wildflowers` r5 | `world.tumulus` (Phrygia), `world.sheepfold`, `world.boulder`, `world.matar_shrine` (N) | `world.sheep`, `world.goat`, `parsa.nisaean_horse` herds |
| taurus (parsa) | `world.steppe` | `world.forest_floor`, `world.rock`, `world.snow` | `world.t_cedar` 2, `world.t_fir` 2 | `world.peak`, `world.crag`; pass with `world.ramp` | `world.eagle` |
| east_med (parsa, N) | `world.steppe` | `world.scrub` | `world.p_maquis` 2, `world.t_oleaster` (N) 1, `world.t_cedar` on the Lebanon band, `parsa.t_date` on the coast | `world.fish_hut`, `world.log_stack` (N) | |
| mesopotamia, susiana (parsa) | `world.alluvium` | `world.field` 30–35 % between canals (`world.river`, 1 wide, every 6–10 tiles); `world.marsh` on low tiles near rivers and in the south | `parsa.t_date` 3, `world.t_palm` 2 (groves along water), `parsa.t_poplar` 1, `world.t_tamarisk` 1, `world.t_reeds` dense in marsh | `world.shaduf` on canal banks every 6–8, `world.reed_hut` clusters in marsh, `parsa.p_house_small` villages | `world.sheep` v1, `world.goat`, `world.ox`, `world.donkey`, home `heron`, `duck`, `frog`, `world.stork` |
| syrian_steppe (parsa) | `world.steppe` → `world.gravel_desert` south of R ≈ 380 | `world.dune` patches, `world.salt_flat` (N) | `parsa.p_steppe` 2, `world.p_thistle` 2, `world.t_tamarisk` in wadis, `world.t_pistachio` rare, `world.p_wildflowers` r3; density 0.02 → 0.005 | `world.tent_black` (N), `world.cistern` (N), `world.cairn` (N) | `parsa.dromedary` caravans, `world.gazelle` (N) |
| persian_gulf shore (parsa, N) | `world.sand` | `world.shallows`, `world.salt_flat` (N) | `world.t_palm`, `parsa.t_date`, `world.t_tamarisk` | `world.fish_hut`, `world.drying_rack` | `world.gull` |
| zagros (parsa) | `world.steppe` | `world.rock`, `world.scree`, `world.snow` | `world.t_oak_zagros` 3 (open woodland 0.25), `world.t_pistachio` 1, `world.t_juniper` (N), `world.p_wildflowers` r2 | `world.peak`, `world.crag`, the pass | `world.goat`, `world.eagle` |
| iran_plateau (parsa) | `parsa.plain_grass` | `parsa.field_barley` near qanats and streams | `parsa.t_cypress`, `parsa.t_poplar`, `parsa.t_almond`, `world.t_pistachio`, `world.p_wildflowers` r2 | `parsa.p_qanat_shaft` lines, `world.sheepfold` | `world.sheep` v1, `parsa.nisaean_horse` |

Everywhere: rivers get 1–2 tiles of `world.t_reeds` and a line of the set's riverside tree at
density 0.4; coasts get `world.p_wildflowers` r4 and, near harbours, `world.fish_hut`.

### 9.4 What goes on the routes

| Route | Paving | Every | Stations | At crossings | Near towns |
|---|---|---|---|---|---|
| Via Appia | `rome.basalt_paving`, width 2 | `rome.r_milestone` 8, alternating sides | `rome.mutatio` 24; `world.inn` (N) at every second | `world.bridge_arch` | tombs (`rome.r_tomb`, `tomb_drum`, `tomb_house`, `tomb_altar`) every 5 within 20 tiles of a town, every 16 elsewhere; pine and cypress pairs beside tombs |
| corner road | `world.road_earth`, width 1 | `world.milestone` 12 | — | `world.ford` | `world.wayside_shrine` once |
| Greek roads | `world.road_earth`, width 1–2 | `athens.g_herm` 16 and at every junction | `athens.g_shrine` 24 | `world.bridge_timber` or `world.ford` | grave stelai and mounds in the last 10 tiles before a town; `world.terrace_wall` on slopes; `world.cairn` (N) on passes |
| Royal Road | `world.road_royal`, width 2 | a watering stop (`parsa.p_well` + `parsa.p_trough`) 8 | `world.royal_station` 16 (the plan's 12 gives 33 identical stations; 16 gives 25 and leaves room for the stops) | Halys `world.bridge_timber` in the gates; Euphrates ferry; Tigris `world.pontoon` | `world.watchtower` at passes and river gates; `world.beacon` on heights about every 32 |
| Pasargadae road | `world.road_royal` | `parsa.t_cypress` pairs 6 | — | — | — |
| Canals and river lanes | — | `world.shaduf` 6–8 on banks | — | `world.jetty` landings | `world.reed_hut` by moorings |

### 9.5 Density: worth scrolling, never cluttered

- **A beat every 30–40 tiles of road**: a hamlet, a station, a crossing, a shrine with a figure at
  it, a flock on the move. **A waypoint or a great crossing every 80–120 tiles.** Between beats,
  10–20 tiles of quiet country with plants only.
- **Keep the road readable**: 2 tiles each side free of trees and props except the route's own kit;
  plants thicken with distance from the road (0.5× within 6 tiles).
- **Clump, do not sprinkle**: `scatter(clump=)` with clearings; groves, woods and thickets with
  edges; open steppe nearly empty (0.01–0.02) so caravans and cloud shadows carry it.
- **Life near the road**: populations on `<stretch>/road` districts, flocks on side tracks, boats
  near the coast and in river lanes; no actors in impassable bands except birds.
- **Budget**: ≤ 400 items per chunk in the countryside (V10's limit is 1 200; cities need the
  headroom), ≤ 12 glow items per chunk outside towns.

---

## 10. For the engine and audio

### 10.1 Actor kinds and schedules

The full kind entries (anims, locomotion, schedules, routines) are in the JSON. Conventions used
there that the engine should confirm (§12): a route token's lane or route gives it the ports
`start` and `end`; a fishing boat's lane has ports `home` and `grounds`.

| Kind | Presence (region files) | Day | Night | Interrupts |
|---|---|---|---|---|
| `world.traveller` | population on `<stretch>/road` districts, density curve `road_day` (0 at night, peaks 08–11 and 15–18) | walks between roadside rest slots (milestones, stations, inns), prays at shrines, wanders | enters a roadside door (station, inn) | storm → shelter |
| `world.merchant` | route token with a donkey group | trades at ports `start` and `end` | lodges | — |
| `world.muleteer` | route token leading `world.mule` v1 × 3–5 (`line`, spacing 0.8): event L5 | hauls `start` → trough at a station → `end` | camps in a roadside door | — |
| `world.fisher` | population per `world.fish_hut` (1–2) | launches at dawn, mends nets, lands the catch at 11–13 and carries fish to the rack | home | rain → home |
| `world.sailor` | population per mooring (1–2) | hauls at moorings | ashore | — |
| `world.fishing_boat` | lane token per harbour (2–4), event S2 | out at 05:30 to `grounds`, back by 11:30 with fish | moored | storm → moored |
| `world.quffa` | lane token across a river | ferries `start` ↔ `end` | moored | — |
| `world.reed_boat` | lane token on river and marsh lanes | poles between ports | moored | — |
| `world.sheep`, `world.goat` | group `flock` with the region set's shepherd as leader and `world.dog` (`cluster`, radius 3): event L1 | graze | in `world.sheepfold` `pen` | — |
| `world.gull` | population on sea and harbour districts | wheels and perches on moles and jetties | roosts | — |
| `world.stork` | population in Persian, Anatolian and Greek farmland, spring and summer | forages in fields, nests on roofs (P12) | — | — |
| `world.eagle` | population in band districts, 1 per 2 chunks | soars 09–17 | — | — |
| `world.crane`, `world.swift` | event cast (W3, W4) | — | — | — |

**The Persian courier relay (event L6)** uses existing kinds: `parsa.courier` as a route token
between stations; at each `world.royal_station` it stops at `change`, `enter`s the `door`, and a
fresh `parsa.courier` `exit`s while `parsa.groom` holds a horse at `horse` (a hand-over the eye
reads as a relay; Herodotus 8.98). Caravans (L7) are groups of `parsa.caravan_driver` with
`parsa.dromedary` or `parsa.bactrian_camel` and `world.donkey` v1, arriving at stations at dusk.

### 10.2 Events on the road and at sea

All from `living-world.md` §5.3, now with their assets: L1 flock (`world.sheep`, `world.goat`,
`world.dog`, `sfx/world/sheep_bells.wav`), L5 mule train, L6 courier, L7 caravan, L3 threshing
(`world.chaff`), S2 fishing fleet (`world.fishing_boat`, `world.gull`), S3 dolphins
(`world.dolphin`), S5 becalmed (`row`), S7 swell (`world.spray`, foam), W1 storm (`squall`,
`world.lightning`, `amb/world/storm.ogg`, `sfx/world/thunder_far.wav`), W2 fog, W3 cranes
(`world.crane`, `sfx/world/cranes.wav`), W4 swifts, W6 cloud shadows, W7 shower (`world.puddle`),
W8 dust. New: **beacons lit** at dusk on the Royal Road's heights in sequence (`world.beacon`
state `lit`), Common, 1 min.

### 10.3 Audio by stretch (existing files in `assets/audio/world/`)

| Stretch | Day bed | Night bed | One-shots and loops |
|---|---|---|---|
| Seas (Tyrrhenian, Adriatic, Ionian, Aegean, Gulf) | `amb/world/sea.ogg` | `sea.ogg` | `amb/world/ship.ogg` near ships, `sfx/world/gull.wav`, `rope.wav` |
| Seam mist bands | `amb/world/seam.ogg` (others duck 6 dB) | same | `sfx/world/seam.wav` with the caption |
| Latium–Italy, Greek countryside, Iranian plateau | `amb/world/fields.ogg` | `amb/world/desert_night.ogg` | `sheep_bells.wav`, `dog_far.wav`, `cart.ogg` on carts |
| Apennines, Zagros, Taurus, Arcadia | `amb/world/mountain.ogg` | `mountain.ogg` | `cranes.wav` (W3) |
| Anatolia, Syrian steppe, the Royal Road | `amb/world/road.ogg` | `desert_night.ogg` | `gallop.wav` (couriers), `hoof.wav`, `step.wav` |
| Ionia–Lydia, Mesopotamia, Susiana, river tiles | `amb/world/river.ogg` | `river.ogg` | `pour.wav` at shadufs |
| Weather | `amb/world/storm.ogg` mixed in under a storm cell | — | `thunder_far.wav` |
| Positional loops | — | — | `brazier.ogg` at beacons and watchtower fires while lit, `smith.ogg`, `loom.ogg` in hamlets |

Requests for a later audio round (not blocking): stork bill-clatter (P12), donkey bray, ferry
paddle splashes, the beacon catching (can reuse `lamp.wav` pitched down), wind in reeds for marsh
zones (the river bed has it faintly).

---

## 11. Cut from this set

- Era-specific clothing of fishermen and sailors (one Mediterranean look serves all eras).
- Separate Greek rut-road terrain (folded into `world.road_earth`), river-bank faces, sandstone
  faces, seasonal looks, night backdrop segments, swaying trees (only reeds sway).
- Carts and wagons (the sets have them), camels and horses (the sets have them), the Persian
  covered carriage, war elephants.
- Water wheels, lateen sails, horseshoes, windmills (anachronistic).
- One mole and one jetty for every culture (no Phoenician cothon, no Greek shipsheds outside
  Piraeus).
- A Delphi theatre (not there in 432).

---

## 12. Decisions for the orchestrator

1. **Scope rule** (§0.1): `world` = nature + everything the base layer places, any era, unless a set
   has it; town landmarks stay in their era sets. Builders follow the region-set rule.
2. **Retire** `world.t_plane`, `world.t_poplar`, `world.t_pine_aleppo` (worldgen maps them to the
   sets' trees); **redefine** `world.t_palm` as clumps; the Royal Road paints `world.road_royal`.
3. **File name**: worldgen's draft tier reads `docs/design/sets/world.json`; this draft is
   `world.catalog.json` as briefed, so it changes nothing until copied to
   `assets/sets/world/catalog.json` (or renamed).
4. **Backdrops day-only**, ≤ 256 px tall; the engine grades them for night and falls back to `day`
   when a `night`/`winter` segment is missing (a one-line fallback rule in the engine).
5. **Weather keys** are bare kind names (`weather/fog_v0`), no set prefix.
6. **Persian waypoints**: build the must-haves on `parsa.1` with the economies (Sardis' acropolis
   and Acrocorinth as relief; Etemenanki at `s = 0.4`); add `parsa.2` only for the nice ones. Not
   on the world page.
7. **World plan fixes** for worldgen core: enlarge the Delos island polygon; add the Sangarios
   river (Gordion) and a small Taygetos band west of Sparta; Royal Road stations every 16.
8. **Token port convention**: route tokens get ports `start`/`end`; fishing lanes `home`/`grounds`.
9. **`"nice": true`** marks N entries in set catalogs (ignored by tools).
10. **World animals in the stretches** although `rome` and `athens` have their own (≈ 0.7 Mpx, so
    one flock looks the same on every road and Pārsa's stretches get any at all).

---

## Sources

- Herodotus, *Histories* 1.75 (Halys bridges), 1.93 (Alyattes' mound), 1.186 (Babylon's bridge),
  1.194 (round hide boats), 3.113 (fat-tailed sheep), 5.52–54 (the Royal Road, stations, the Halys
  gate and guard post), 5.101 (Sardis' reed houses), 8.98 (the relay of riders), 9.3 (fire
  signals): Perseus/Perseids texts, e.g. https://cts.perseids.org/read/greekLit/tlg0016/tlg001/perseus-eng2/5.52.1-5.52.3 ;
  Livius, "Royal Road": https://livius.org/articles/concept/royal-road
- Xenophon, *Anabasis* 1.2.5, 1.4.11, 2.4.24 (bridges of boats, the Euphrates at Thapsacus).
- Thucydides 1.44 (Corcyra's alliance); Arrian, *Anabasis* 6.29 (Cyrus' tomb and its magi);
  Aeschylus, *Agamemnon* 281–316 (beacon chain); Pliny, *Natural History* 36.95 (the Artemision).
- Encyclopaedia Iranica, "Persepolis Elamite Tablets" (travel rations, stations a day apart):
  https://iranicaonline.org/articles/persepolis-elamite-tablets
- Sardis Expedition, "Pactolus North" (the Lydian gold refinery and altar of Cybele):
  https://sardisexpedition.org/en/essays/about-pn ; Harvard Art Museums, Archaeological
  Exploration of Sardis: https://harvardartmuseums.org/teaching-and-research/research-centers/archaeological-exploration-of-sardis
- Penn Museum, Gordion and Tumulus MM: https://penn.museum/sites/expedition/gordion-and-the-penn-museum ,
  https://penn.museum/documents/publications/expedition/57-3/tumulus-mm.pdf
- Delphi theatre's date (stone theatre 4th century BC, earlier form unknown): World History
  Encyclopedia, "Greek Theatre Architecture": https://www.worldhistory.org/article/895/greek-theatre-architecture/
- The city bibles' source lists (`docs/design/cities/sources.md`) for every landmark named in §4.
