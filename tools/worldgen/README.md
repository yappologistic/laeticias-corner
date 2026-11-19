# worldgen: building the world as code

`tools/worldgen` compiles region sources into the world files the engine loads
(`assets/world/world.json`, `assets/world/layers/<layer>.lcw` and `.graph.json`,
`assets/world/overview.png`), validates the composed world, and renders previews from the atlas
pages without the engine. The formats and rules are `docs/design/world-tech.md` §2–§3; this file is
the practical guide.

## Commands

```sh
tools/worldgen/build.sh parsa                 # compile + validate one layer, write it if clean
tools/worldgen/build.sh parsa --preview       # … and write previews to out/worldgen/parsa/
tools/worldgen/build.sh base                  # regenerate the procedural base (worldgen core only)
tools/worldgen/build.sh --all                 # base, then every layer with a layout
tools/worldgen/build.sh --check               # validate the committed files (report: out/worldgen/check.txt)
tools/worldgen/build.sh world --preview       # world.png, overview_full.png, assets/world/overview.png
tools/worldgen/build.sh parsa --no-write      # validate only
tools/worldgen/build.sh --test                # the test suite (about 25 s)
tools/worldgen/build.sh --life                # region files of the stretches, seas, seams, waypoints
tools/worldgen/build.sh --seasons             # catalogs' seasonal fields, flood ranks, ground classes, needs
tools/worldgen/build.sh --city athens --year --preview   # … and a year in the life, the season maps
tools/worldgen/build.sh --year-all            # a year in the life of every region file
tools/worldgen/build.sh --nights athens --preview   # lit nights: warm-lit share per view, night previews
tools/worldgen/build.sh --alive [--before DIR]      # expected life everywhere, checks A1-A6
```

After changing the base or a town that touches it, rebuild the towns and then the base once more:
the base blends into the committed layers' edges and carves rivers to their water, and the towns
copy the base below them, so two rounds reach a fixed point (a fresh build then reproduces the
committed files byte for byte).

The first run creates `.venv` from `requirements.txt` (numpy, Pillow). Everything runs under
`nice -n 19`, single-threaded, headless. A layer is compiled against the **committed** files of
every other layer, so builders of different layers never wait on each other. A layer with errors
is not written; the report says why.

Outputs per built layer in `out/worldgen/<layer>/` (`--check` writes one `out/worldgen/check.txt`
for all layers instead): `report.txt` (every error and warning, numbered,
with file:line of the layout call and local/plan/grid coordinates), `map.png` (1 px per tile for
the base, 4 px for a layer: terrain colours, level shading, items as dots, graph in yellow),
`issues.png` (the map with every issue circled and numbered as in the report),
`close_<view>.png` (isometric close-ups of each `L.view()` and of every landmark's
surroundings), `missing_art.txt` (ids drawn as placeholders). Delete them when done.

## Authoring a region

One builder owns one layer: `tools/worldgen/regions/<layer>/layout.py` (+ `README.md`),
`assets/world/layers/<layer>.*` and `assets/regions/<region>.json`. The layer list, rects,
regions and base levels are in `plan/world_plan.py` (`LAYERS`, `REGIONS`); ask the worldgen core
owner to change them. `regions/ostia/layout.py` is the template town; `regions/corner/layout.py`
is a countryside layer.

```python
from worldgen.dsl import Layout
from worldgen.shapes import Ellipse, Line, Poly, Rect

def build(L: Layout) -> None:
    sea = L.sea_below()                                  # follow the base layer's coast
    L.fill("parsa.plain_grass", level=0, district="fields")
    L.paint(sea, "world.sea"); L.level(sea, -4)          # sea is world level 0
    L.district("town", Rect(0, 62, 48, 112))
    road = L.street([(0, 50), (26, 50)], width=3, paving="parsa.packed_earth", kind="road",
                    portal="royal_road_w")
    L.place("parsa.apadana", rect=(60, 54, 83, 77), name="apadana")
    L.houses(Rect(0, 62, 48, 112), {"parsa.p_house": 3, "parsa.p_house_small": 5},
             front=[road], gap=0.15, seed="town")
    L.view("forecourt", Rect(20, 30, 70, 64))
```

### Coordinates, levels, facings

- **Local plan coordinates** `(c, r)`: `c` east, `r` south, from the region's north-west corner,
  exactly the city files' tables. Rects are inclusive `(c0, r0, c1, r1)` (a 4-tuple works wherever
  a shape does). Worldgen converts to grid (`tx = R`, `ty = 1279 − C`) only when writing files.
- **Levels are local**: the region's base level (`REGIONS` in the plan) is added. World levels are
  0..15; the sea is 0, so a coastal town at base 1 paints its sea at local `-1`.
- **Facings** are compass words. Kit faces `+y` (west) in `r0`, so `"west"` = `r0`, `"north"` =
  `r1`, `"east"` = `r2`, `"south"` = `r3`; worldgen turns the footprint for you (odd `k` swaps it).
  Landmarks are modelled in grid axes and always use `r0`, whatever `face` says.
- `place(at=(c, r))` gives the footprint's **north-west** tile; `place(rect=...)` gives the whole
  footprint and is checked against the catalog footprint after rotation (V4).
- **Stairs and ramps**: `L.stair(item, rect=..., face=...)` — the foot (lower end) is on the
  `face` side, the head on the opposite side. The footprint is at the lower level; the tile beyond
  the head must be `rise` levels higher (V3). Walkers change level only on stairs and ramps (V5).

### The API (world-tech §3.3, plus a few helpers)

| Call | Does |
|---|---|
| `fill(terrain, level=0, district=None)` | whole layer |
| `paint(shape, terrain)`, `level(shape, n, face=None)`, `impassable(shape)`, `transparent(shape)`, `no_ground(shape)` | ground; `face` names the edge material of raised tiles (must be in the terrain's `faces`, or its base's) |
| `district(name, shape)` | `"town"` is stored as `<region>/town`; a layer holding several regions writes `"seam_dell/dell"` |
| `place(item, rect=|at=, face=, variant=, name=)` | one item; reports overlaps (V2) instead of placing |
| `scatter(shape, {item: weight}, density, min_gap=1, seed=, clump=0)` | per-tile draws; `clump` (0..1) makes thickets and clearings |
| `row(line, item, every, face=, offset=)` | items along a line's centre walk |
| `houses(shape, kit, front=[streets], gap=, seed=)` | district filler: frontage first, doors to the street, alleys, then smaller pieces inside facing reachable tiles; houses whose door gets cut off are removed |
| `fields(shape, crop, plot=(w, h), path=None, seed=)` | plots that wobble by a tile, one in five fallow; `crop` is a terrain or an item planted in rows |
| `wall(line, kit, tower=, every=, gates=[(c, r, item)])` | connect-layout walls with towers and gates |
| `street(points, width=, paving=, kerb=, kind=, portal=)` | paints and makes graph edges; crossings and T-junctions become nodes (a street end joins only a street at its own level, or one it meets on a stair, ramp or deck); `portal` names the end on the layer edge; `paving=None` keeps the ground (a way over a bridge's deck, whose water stays) |
| `stair(item, rect=, face=, name=)` | see above; makes a `stair` edge. Where the end lands inside a landmark, it snaps to the landmark's nearest walk tile; a landing shared by two stairs joins only their flights |
| `river(points, width=, terrain=, banks={item: density}, seed=)`, `channel(...)` | water with flow (aux) following the points |
| `lane(id, points, kind=, ports={id: point index})` | ship and barge lanes |
| `node(id, at, kind="dest")` | a named node; snapped to the nearest street within 16 tiles |
| `edge(a, b, kind=, via=)` | an explicit edge between named nodes (over ground the layer leaves to another) |
| `link(placed, slot, node)` | slot spot ↔ node |
| `fits(item, at, face=)` | would `place` succeed here (free, flat, suitable, off the streets)? For detail that gives way |
| `walk_tiles(placed)` | a landmark's walk tiles (plan) from the geometry file; `place` may put furniture on them |
| `remove(placed)` | take back an item a filler placed (thinning, door clearing) |
| `expect(landmark, rect=, level=)` | V4 check of your own placement |
| `moved(landmark, rect=, why=, level=)` | declare a landmark a deliberate step off its city-file rect (or level): V4 reports the move, with the reason, as a warning |
| `view(name, rect)` | a close-up preview |
| `sightline(name, shape)` | mark a monumental approach: only the region's own set and home pieces with art may stand in it (V15) |
| `below_terrain(c, r)`, `below_level(c, r)`, `land_below()`, `sea_below()`, `coast_below()`, `below_where(pred)` | read the committed layers underneath (the base's coast, rivers, levels) |
| `terrain_at(C, R)` | what this layer has painted so far (world coordinates) |

Shapes: `Rect`, `Poly` (vertices are tiles, boundary included), `Line(points, width)` (odd widths
centre on the named tiles, even widths on their south-east corners, so a width-2 street along
row `r` covers `r` and `r + 1`), `Ellipse(c, r, rx, ry)`, and `a | b`, `a - b`, `a & b`.

**Order is the only state.** Later calls win on the same tiles. Lay streets before houses and
water before scattering trees (painting water under a tree is caught by V3). Every random choice is
a pure function of `(region, seed, tile)`: changing one `scatter` never reshuffles another.

### Multi-piece landmarks

Place a landmark **once**, with its whole footprint rect, at `r0`. The art tool cuts it into pieces
and emits walk tiles and slot spots in `assets/atlas/<set>.geom.json`; worldgen reads them (V7 checks
every spot is walkable and near the graph). Do not place pieces separately. Its stairs are separate
items (`L.stair`), furniture inside it is kit placed on its walk tiles (`L.place("parsa.p_throne",
at=…)`). Paint the paving under walk tiles yourself: walk-tile floors are ground terrain, not part
of the landmark. Name landmarks with their city-file id (`name="apadana"`); V4 compares every
`<set>.<id>` you place with the city file's §2.3 table (rect and local level). A listed landmark
you have not placed is a warning, and an error once your region README says `Status: complete`.

### Believable districts, not grids

- Streets follow the city file's plan, then wander: give long streets a vertex every 8–15 tiles
  and let them bend; vary widths (main 2–3, lanes 1).
- Use `houses` with `gap` 0.1–0.2 and a kit of 3–6 pieces of different sizes with uneven weights;
  it leaves alleys and courtyards. Several `houses` calls with different seeds and kits per
  quarter read as neighbourhoods.
- Break uniform areas with `scatter(..., clump=0.5–0.9)`: yards, wells, ovens, trees in gardens.
- `fields` already wobbles plot sizes and leaves fallow plots; vary `plot` between districts.
- Look at `close_<view>.png` at 1× before committing: a street that reads as a ruler line, or a
  block of identical houses, needs another pass.
- Diagonal street segments are rasterised as staircases, and graph edges between crossings on
  them may leave the painted tiles: prefer axis-parallel runs with jogs (`regions/parsa`'s
  `orth()` helper).
- With a mixed kit, `houses` favours the small pieces; run it twice (large pieces first, then a
  fill with the small ones) for courtyard-house quarters.

### Content that does not exist yet

Ids resolve from `assets/catalog.json` and `assets/sets/<set>/catalog.json`, then drafts
(`docs/design/sets/<set>.json`), then `plan/provisional.py` (worldgen's stand-ins: footprints and
heights from the city files). Draft and provisional ids validate with a V1 warning per id. Missing
art draws as a grey box of the catalog height with the id on it; provisional plants draw a home
sprite as a stand-in so country previews can be judged.

## Waypoint towns (`worldgen/waypoint.py`)

Small layers on the plans of `docs/design/sets/world.md` §4 (`regions/delphi/layout.py` is a short
example). `WP.ground(L)` copies the base below (terrain, levels, sea depth, river flow) so the edges
meet the world; `WP.portal_street(L, pid, points, width=, paving=)` lays a road from the plan's portal
tile at the plan's level (across the edge where two authored layers touch); `WP.raise_levels` builds
a mound or acropolis in benches; `WP.climb` lays a path up a slope with a flight per level;
`WP.river_level` gives a town's river a level no higher than where the base's river flows in;
`WP.harbour_lane` ends the town's lane on the base lane's port tile; `WP.finish` clears door steps,
lights the town for the night (`WP.night`: a fire where each road comes in, lamps at its named
places, crossings and along its streets, from the set's kit), caps glow and fits faces; `WP.pier`
lays a jetty or mole from the strand out over the water. Landmarks a city set has not drawn yet are provisional ids at their final
footprints (`plan/provisional.py`).

## Routes and lanes (`worldgen/routes.py`)

`ROUTES` and `ROAD_STYLES` in the plan say where roads go and what stands along them. Each route is
an axis-parallel A* path (turn penalty, pull to the straight line), a profile that changes level only
on `world.ramp` flights (a level per 4 tiles plus a landing), meeting every portal and junction at its
fixed level; paving; a ford, bridge or pontoon on water; then markers, stations, stops, tombs,
graves, terrace walls, watchtowers, beacons and farms with tracks; harbours at route and lane ends.
Between two portals of a town without a layout the base carries the road through the town's rect.

Connections, not removals: a harbour lays its planks only from a strand walkers reach from a road
(`shore_reach`; a road is extended down to the strand where a harbour belongs, as the Troad road
to Abydos and the Cilician spur), with no scarp beside the planks (`cliff_beside`), its beacon on
the strand beside the root; a fold whose gate no walk of one level from a road reaches gets a
drove track (`drove_tracks`: earth paving of the region's set, levels changing only on ramps) to
the nearest node of the base graph or another fold's track, with a `fold_<c>_<r>` node at its
gate, so herds (`life.droves`, `seasonlife.transhumance`) leave from their folds. A fold is not
built where its gate opens onto water, a cliff or another item (`country.fold_site`); a later
route never lays a ramp on a tile an earlier road paves.

## Lit nights (`worldgen/lights.py`, `worldgen/nights.py`)

Every region file gets `lights` (the profiles: kind, colour temperature, radius, strength,
flicker, hours, rain, festivals) and `light_points` (`[tx, ty, item, profile(, emitter)]` at placed
light-giving items, chosen by rule per item kind and district, at most 48 per chunk); night roles
and evening events get `carries` (the lamp or torch they hold). Glowing items no point names stay
dark at night. Layouts add the street-level lights a civilization had with `night_posts`
(lamps in niches at crossings, braziers at gates, torches on processional ways) and `crossings`
(finish.py). `--nights` measures each populated quarter and the golden views at 1x: the share
warm-lit at dusk, 22:00 and 02:00 against the quality bar (2–8 % in a city, 1–4 % in a village),
the unlit median, and writes `out/worldgen/night/nights.md` and previews. The checks are L12
(`lights.check`): every point at a placed light-giving item or one of its emitters, profiles in
range (warm 1700–2600 K, flicker depth ≤ 0.08, valid hours and conditions), no two lights of a kind
on one tile, carriers' profiles present, and no populated quarter without light at dusk.

## Validation (world-tech §3.5)

| # | Check | Level |
|---|---|---|
| V1 | ids exist (terrain, items, districts `<region>/<name>` of the layer's regions, face materials); draft/provisional ids warn | error / warning |
| V2 | no overlaps in a layer; items of lower layers dropped by this one | error / warning |
| V3 | footprints on ground of their `on` kind, flat; a landmark's declared walk tiles may lie one level off its (flat) solid tiles, a step its art's floor carries; stairs: foot at the stair's level, head `rise` higher | error |
| V4 | `expect()` rects and levels; city-file §2.3 landmark rects and levels (a set footprint that holds the bible's rect, e.g. a hall modelled with its portico, warns; rows without a footprint are not landmarks) | error (missing: warning) |
| V5 | every graph edge walkable along its course; levels change only on stairs, ramps, or decks on water (jetties, bridges, fords, and a landmark's walk tiles over water or on an `on: water` landmark: a bridge's deck, the island's quay); entering a landmark whose set has no geometry yet warns | error / warning |
| V6 | graph connected; portals declared in the plan, every layer carrying one on the plan's tile (one node, world-tech §2.5: a street ending a step short of it is joined across the edge by the compiler), with a walkable tile of the other layer beside it across the boundary at its level; present in the other layer when it is built (a base route still planned warns); dest nodes ≤ 64; the journey's `NETWORK` chain (plan) in one network once its layers exist | error / warning |
| V7 | slot spots (geometry files) and doors of buildings walkable and within 24 walking tiles of the graph; a kit slot on its own footprint (a seat, a shed's yard) counts from the walkable tile beside it; a `mooring` slot on water is a boat's spot: it must touch a walkable tile (beside the spot or beside its post) within reach of the graph; spots inside a landmark that only its geometry can open warn ("art geometry") | error / warning |
| V8 | two base terrains never touch; seas at level 0; rivers never flow uphill | error |
| V9 | layer rect inside its regions; every tile with ground has a district; a stretch's sea district has no piece farther than 24 tiles from its body that no sea path joins to it (plan `INLETS` excepted) | error |
| V10 | ≤ 1 200 items and ≤ 40 glowing items per chunk, ≤ 254 districts | error |
| V11 | ≤ 25 % of walkable tiles hidden behind raised ground | warning |
| V12 | item cards exist in the region file | error |
| V13 | determinism: two compiles give the same bytes (test suite) | test |
| V14 | the base's relief: no isolated single-tile level change on open country, at most 2 % of it on one-tile benches with a cliff step or on ground without slope art (a graded hillside is one slope), no river reach under 6 tiles between two falls of under 3 levels | error (base) |
| V15 | a marked `sightline` holds no world kit (fords, plank ramps, timber bridges, …) and no placeholder | error |
| V17 | the engine's walk rules on every graph edge (`worldgen/walk.py`) | error (a step only a landmark's `walk_z` makes: warning) |
| V16 | crossings (`worldgen/crossings.py`): every step the graph makes onto or off a deck (a landmark's walk tiles at its level plus `walk_z`, walkable kit on water at the water's level) stays within half a level of what it meets; bridges, fords, pontoons, landmarks on water and gates a road passes through are joined at two ends (a pier may end at a `dest` node on its planks); a landmark bridge's walkway never ends over water; a one-wide span is entered over its ends, never from its side (only a stair may join it there); jetties and moles touch walkable land within a level of the water; connect decks run along one axis (two wide draws a frame); a stair's foot and head landings are walkable, at its level and `rise` higher, and met by a path (wide flights share landings) | error (a landmark floor on dry land, landmark stairs: warning) |

| V18 | faces (`worldgen/landform.py`): a raised land tile's face index names one of its terrain's materials (its own, else its base's, the engine's rule), and that material has face art on both sides | error |
| V19 | straight seams: two natural grounds never meet along one row or column for more than 12 tiles (paving, roads and their verges, formal garden beds, water may run straight) | error |
| V20 | map markers: every marker but the home's lies in its region and opens on its place: built pieces cover 6 % of the view round it, one within 2 tiles (plan `MARKER_AT` where a town stands off its rect's middle) | error |
| V21 | floors: an interior floor (`parsa.paving_red`) lies only on walk tiles of the landmark whose footprint holds it; no base ground shows through paving | error |
| V22 | water steps: running water steps down over the edge it flows to (a rapid at one level, a fall at more), never a single level into the sea, never above the land beside it; no stream tile juts out with lower ground on two sides | error |
| V23 | slopes: slope ground (the catalogs' `art.slopes`) a level above a neighbour has art for all 21 slope shapes | error |
| W-* | where walkers may be (`worldgen/walkable.py`, draw-order.md §5.2), by the engine walk model over the composed world: W-V3 one level under every footprint, walk tiles included; W-S3 a stair's head and foot meet the levels it joins; W-D1 decks reached and met by the land beside them; W-D2 only crossings and piers walkable on water; W-W5 every item's walk tiles reached by a graph; W-L1/L2/L3 slot spots on tiles their users can stand on, reached, moorings on water by a reached quay; W-G1 edge ends in one walk component; W-G2 nodes and edges never under an item without walk tiles; W-O2 lanes on water and under an item only through its geometry's `under` | error (art pending: warning) |

Faults whose fix is a set's geometry (the art lane's) are listed in `plan/art_pending.py`: each
turns its W error into a warning that names what the art must change, and `--check` fails on an
entry no fault matches any more, so the list only shrinks. `--check` also writes
`out/worldgen/walkable.md`: per region the walk tiles, those on items and how many of them no
graph reaches (zero), walkable ground in components no graph reaches (country benches, islets),
slot spots, nodes, lanes and edges by kind. The base drops its own kit that fails W-W5/L1/L2
(`base.drop_unreached_kit`, after placement checked reach by its simpler rules), the layout API
refuses walkable kit that is no crossing on water (`dsl.deck_kit`) and removes it where water is
painted over it, and base lanes keep every leg on open water (`routes.on_water`), off piers.

Additions: V1 also checks that every placed variant is a valid look or rotation of its catalog
entry, retired stand-ins, and the region-set rule (a region of set S carries home, world and S ids
only; seams also both neighbours'). V6 checks portal levels against the plan and that lane ports
named in the plan's lanes meet across layers within a tile; a graph part that reaches a portal may
stand apart. V7 warns (art geometry) for kit slots deep inside their own footprint. V8 counts river
flows between two layers as the base's errors (warnings elsewhere). V10 holds a layer to the chunk
budgets it adds to.

`--check` also checks that `assets/world/world.json` lists exactly the layer files present, in
composition order, and that `assets/world/placeholders.json` lists every placed id no set catalog
defines (provisional or draft stand-ins: id, set, layer, grid origin, variant, footprint, height),
which the engine draws as labelled placeholders and the art lane reads as its backlog; a build rewrites `world.json` only when that list changes and says so, so
commit it with the layer that changed it. A region README is complete when it has the line
`Status: complete` on its own.

`build.sh --city <region>…` runs the life checks of a city's region file (`worldgen/citylife.py`,
`lifesim.py`, `lifereport.py`); `--check` runs them on the committed city files too.

Chains (`worldgen/lifesim.py`, read the same way by the engine): a slot reference
(`<item>.<slot>`) names one instance per chain. When two stages of a chain name the same slot
reference with a different `near`, **the later stage's choice wins for both** (the simulator
resolves references into one table, the last stage writing it): to send two stages to two
instances of one kind, give them different slot references or one `near` each that resolves to
the same instance. `athens_oil` (`g_stall.sell`) and `ostia_grain` (`rome.quay.mooring`) rely on
this today.

V17 mirrors the engine's walk rules (`worldgen/walk.py`, from `src/world/world_map.cpp`) for every
graph edge: tiles walkable as the engine builds them (a landmark stair only on its walk tiles), a
step within half a level of the facing edges (a level onto a deck), a stair entered only at its
foot or head. A step onto a landmark's own floor or tread that only its `walk_z` makes (half to
one level) is a warning for the art or the engine. Landmark stairs' edges run over their walk
tiles (`compiler._stair_course`); a stair end on a landmark's floor is not snapped to a street.

Every region file (cities through `--city`, the rest through `--life`) also gets its sound
(`worldgen/sound.py`: `theme.sound`, `districts[].sound`, event `sfx`/`ambience`/`sounds`,
working roles' `sound`, positional loops on placed workplaces, all measured on the built world
and named from `assets/audio/*/manifest.json`), its look (`worldgen/look.py`: `theme.look` of
docs/design/look.md §3.5 and `districts[].look`) and its names (`worldgen/places.py`: a specific
name, caption and era for every region, a name for every district). `--check` runs L9 (sound:
every file and family in a manifest; no silent event, working role or populated district), L10
(look: schema and ranges) and L11 (names and eras) on every committed region file.

Crossings over a river sunk below its banks: `finish.landings(L)` steps the street down to the
decks (a ramp on four straight tiles, else a two-tile stair); kit decks (`world.bridge_*`,
`world.pontoon`, `world.ford`) meet banks flush with the water, so towns on plains keep their
rivers flush; the base's routes meet every crossing at the water's level and lay decks on the
road's own lane only.

`--check` validates committed files without their layouts, so checks that need the layout source
(V4 expectations, V7 slots, source lines) only run when the layer is built.

## Seasons (docs/design/seasons.md)

One world calendar: calendar day n is month `n mod 12` (0 = March), season `(n / 3) mod 4`,
season day `n mod 3 + 1`, week day `n mod 4`. Twelve days hold every month with its week day, so
the life checks (L3-L5, L8) run over days 0..11 and have seen the whole year; a festival is on a
day by its `season` + `day` or its `months`; a population, schedule block, event trigger or chain
may say `months`; a chain may say `by_month` (twelve pace factors, its period divided by them; a
slowed chain is judged after two days of filling); a district may say `seasonal_area` (`area`,
`months`: a terrace whose court is away is held to a town's numbers in those months).

- `worldgen/climates.py`: the fifteen climates (classes of plant and ground state by month, snow
  lines, frost, wet and dusty months, water levels and ice, travel and sailing rows, weather,
  grades, looks, dress, turn events, birds, work, transhumance), the calendar and its turns, which
  climate each region has, which climates may meet, and the set pieces that change with the
  seasons. `--seasons` writes them into the catalogs (only those fields, each file's own layout).
- `worldgen/seasons.py`: the calendar, climate resolution (`inherits`), the catalog writer, the
  water bodies, flood ranks and ground classes (`assets/world/seasons.json`, `groundclass.png`).
- `worldgen/seasonlife.py`: what every region file gets (climate, era, moment, weather and themes
  by season, water by month, tokens by month, harbours, dress, birds, herds between summer and
  winter pastures, seasonal work on the farms, the turns of the seasons) and the helpers the
  cities' own `regions/<city>/seasons.py` use (`monthly`, `vary`, `factors`).
- `worldgen/seasoncheck.py`: S1-S19 (`--check`, report `out/worldgen/seasons_check.txt`; S18 snow
  painted as ground only where the climate keeps snow all year, S19 no lying snow on a lowland
  above freezing, no summer snow below level 13, no palm under snow) and the
  needs file `assets/world/season-needs.json` (seasonal art and audio not made yet).
- `worldgen/seasonreport.py`: a year in the life and the season maps (`out/worldgen/seasons/`).

A city keeps its famous month exactly as its day in the life was built (the Parilia in April,
the Panathenaia in July, the spring audience in April); its `seasons.py` lays the other months
over it. The checks hold every month to the same rules as that day.

## The base layer and the plan (worldgen core)

`plan/world_plan.py` holds the coarse authored world: regions and stretches, district ownership
rules, layers, portals, land/sea/island polygons, relief per stretch, mountain bands, rivers,
routes and lanes, stretch looks, overview labels. `worldgen/base.py` turns it into the base layer
(coasts roughened by bounded noise, islets beside the open-sea lanes, relief with domain-warped
stretch settings, rivers, routes by A*, fields and forests by stretch look, districts).

Relief reads as landforms at the game's camera (plan `LANDFORM`, `RIVER_FORM`): the continuous
height is grouped into benches two levels tall whose risers take a third of the run (looser in
mountain bands, plain rounding next to authored edges), every level's outline is opened and
closed by two tiles, a bench too narrow to stand on joins the scarp above it, pimples go, and no
scarp is taller than three levels. Rivers run level for at least a reach (24 tiles), the drops of
the next reach gathered into one fall; their valleys have a flat floor a third of `valley` wide
and rise in a scarp; deltas lie flat at the shore's level. V14 holds the result. City rects are reserved flat at the
city's base level; town rects keep natural ground but no country items. Each table entry affects
only its own area, and all noise is a function of world position and a string key.

## The land's form (`worldgen/landform.py`)

The art draws a one-level step of natural ground as a slope (out/reports/art-smooth-land.md §3),
so the land is shaped for it:

- **Grading.** The base raises slope ground (the catalogs' `art.slopes`, rock excepted) to one
  level below its highest slope neighbour (eight around), never more than a level above water
  beside it, after the roads are laid and before the country (`base.shape_for_slopes`); roads,
  their verges, anything placed, cities, towns and a band round authored layers keep their
  levels. Waypoint towns grade their own natural ground the same way (`waypoint.grade_country`,
  off streets, items and a two-tile band at the layer's edge). Lone spikes and pits on open
  ground are smoothed (`lone_steps`), never a bank beside water.
- **Slopes and cliffs.** What slopes follows from the data: a step of one level between slope
  ground is a slope; two levels or more, rock ground (`CLIFF_GROUND`) and ground with no slope art
  keep their faces; a raised tile whose face material is masonry (`BUILT_FACES`: ashlar, brick,
  travertine, basalt) is a built edge and should stay flat (the contract for the engine).
- **Water steps.** `base.square_falls`: a river's mouth reach ends in three tiles at the sea's
  level; water never stands above its banks; every step between water tiles runs square across
  the flow, so the upper tile's flow (aux) names the edge the water falls over and the drop is
  the two tiles' level difference (one: rapid, two or more: fall). V22 holds every layer to it.
- **Borders.** The base's looks follow a noise-displaced stretch map (`base.look_map`, only where
  the neighbouring biome's sets may stand), margins between two base grounds swing in width, and
  every layer's straight natural seams are waved after its layout runs (`wave_seams`: free tiles
  only, the level and face moving with the terrain where the step follows the border); free base
  ground enclosed by paving is paved (`close_paving_holes`). V18-V23 above.
- **Lights.** `--nights` also measures every town at its map marker (its arrival view, held to
  the village bar) and the cities' day-busiest views (`nights.BUSIEST`, dark by history after
  dark, held to the village bar too).
- `--seasons` writes `out/worldgen/seasons/snow.md`: per region and month, snow lying on its
  lowland, on its highest ground only, a dusting some days, or none.

## Files

`worldgen/`: `dsl.py` layout API · `shapes.py`, `raster.py` shapes and exact rasterisation ·
`catalog.py` catalogs, atlas pages, geometry · `layer.py`, `graph.py` file formats ·
`compiler.py` layout → layer and graph · `compose.py` the engine's composition rule ·
`validate.py` V1–V12 · `landform.py` V18–V23, grading, waved borders · `walk.py` the engine walk model (V17) · `walkable.py` W-* and the
walkability report · `bible.py` city-file landmark tables · `base.py` the base layer ·
`preview.py` maps, overview, isometric close-ups · `rng.py` SplitMix64 streams and noise ·
`climates.py`, `seasons.py`, `seasonlife.py`, `seasoncheck.py`, `seasonreport.py` the seasons ·
`build.py` the command line. Tests in `tests/`.

## Life everywhere (`worldgen/traffic.py`, `countrylife.py`, `townlife.py`, `alive.py`)

- **Traffic** (`traffic.TRAFFIC`): who travels each road, river and sea lane, filed as lane
  tokens in the region it belongs to, with its groups. `traffic.finish` gives every token of
  every region file (cities included) an `id`, `hours` (when under way), `rest` (the relay
  stations, inns, towns and harbours on its way, or its lane's ports: where it waits outside
  its hours), irregular `offsets` and, through `seasonlife.tokens`, its climate's `by_month`
  row. Paths are found on the joined graph of all layers (`traffic.Joined`), as the engine walks.
- **Countryside** (`countrylife.py`): roles and populations bound to what the base places
  (stations, towers, beacons, folds, farmsteads, woods, groves, pines, thyme, reeds, palms),
  the `pasture` districts' herds, goatherds, Thracian riders, gazelles, owls; area kinds for the
  base districts; the year's events of every stretch, sea and seam (`EVENTS`); the corner's
  borderland (`corner_file`); `ambient` lists for the engine's sky and sea layer.
- **Towns** (`townlife.TOWNS`): each waypoint town's trades, chain, market day, night watch and
  events, plus the household roles by set, calibrated so every district meets its area's
  minimum in its leanest month and stays under its cap. Town files are held to every life check
  (L1-L8); stretches, seams and the corner to all but L5.
- **Numbers and checks** (`alive.py`, `--alive`, also run by `--check`): expected actors per
  region and hour block and month, the share of empty screens, the worst active area at 1x and
  1/4 zoom; A1 no daytime block without life, A2 no 1x active area over the live cap from the
  lanes' own data, A3 every token has both ends, a path, rest stops on its way, hours and
  offsets, A4 months filters without doubles or holes, A5 an event in every season, A6 no two
  large events at once.
