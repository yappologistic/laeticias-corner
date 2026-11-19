# src/worldview: the world renderer and the viewer

Draws the prebuilt world that `src/world` loads (docs/design/world-tech.md §4.3–§4.8), and
`laeticias-world`, a headless viewer to look at it, measure it and take screenshots. Library
`lc_worldview` (links `lc_engine` for the atlas, batching, `putSprite`, `ScreenGrid`/`behind`,
the font and the clock's lighting, and `lc_world`). The game draws through it (`src/app/app_world.cpp`).

## Shape

| File | What |
|---|---|
| `renderer.hpp` | `WorldView`: the frame at four levels of detail, region themes, streaming, stats |
| `page_atlas.hpp` | `PageAtlas`: home atlas + generated page + every set page as one key space; streaming, slots, LRU |
| `world_sprites.hpp` | `WorldSprites`: looks resolved once per terrain, face material and item variant; the generated page (flat ground and faces, labelled placeholders); the missing-art report |
| `gather.hpp` | `Gatherer`, `Prep`: elements meeting a rect (items, landmark pieces, raised tiles that hide them) and their order, on a worker thread |
| `order.hpp` | `PageOrder`: the exact topological painter's order with a page-aware tie-break; the ground rule |
| `cells.hpp`, `cell_cache.hpp` | cell maths, LRU slot and page-eviction policies (pure), slots in cache pages |
| `overview.hpp` | the generated isometric map of the whole world |
| `theme.hpp` | theme weights low-pass, grading by phase, haze, era caption with hysteresis (pure) |
| `camera.hpp` | `WorldCamera`: levels, limits over the grid, jumps, eased flights (pure) |
| `script.hpp`, `viewer.hpp` | the viewer's options, script language, bench cases |
| `tuning.hpp` | every number above |

## How a frame is drawn

- **Levels of detail** by scale: native (1, 2, 3), half and quarter (cell impostors), overview.
- **Cells** are squares of world pixels, not grid chunks: a level-L cell spans 512 << L px and is
  stored in a 512 x 512 slot of a 4096 x 2048 cache page (made and touched at load: a driver
  stalls a frame on the first draw into a fresh one). Screen squares waste nothing (a chunk's
  diamond in a box wastes half). Level 0 holds the ground: tiles in diagonal order at
  `level × tile.level` px, faces stacked under the +x/+y edges down to the neighbour by material
  (`aux` → terrain `faces`), the base and the overlay by mask, foam on water by land mask, the cap
  band (`…/top`) after the ground. A cell with water in it is cached once per step of the water's
  loop (four), so water moves at no cost per frame; the steps of cells in view are kept while
  there is room. Levels 1 and 2 are impostors of everything static: 1024-px blocks drawn at full
  resolution (ground, the shadow layer where something casts one, sorted items) and halved with
  filtering (2 x 2 box per halving). An impostor cell with water in it is kept in layers
  (`cells.hpp`): its ground once per step of the water's loop and what stands on it once, laid
  over whichever step is shown, so the sea moves at half and quarter scale too and a step costs
  a ground to draw, not the city on it.
- **Nothing arrives late.** Each frame lists the cells it wants in order of need: the view's
  own; those of a destination the view is heading for (the level a zoom under way ends at, a
  journey's place while the veil comes down); a ring around the view leaning the way it moves;
  and the two wider levels where a turn of the wheel about the pointer would show them. The list
  is deduplicated and cut to what the cache holds, so nothing wanted is ever pushed out by
  something else wanted. Cells are built on the main thread within a time budget per frame
  (2 ms for what is needed, 1 ms for what is built ahead; `tuning.hpp`), impostor blocks after
  their gather comes back from the worker. Drawing only composites: a cell not built yet shows
  its coarser level, or the overview under it. The cache holds, at a window's size, its own
  level with the ring and the two wider levels, half as much again, or what a view of nothing
  but sea needs for its water to move at every level, whichever is more (192 MiB at 1080p, 224
  at 1440p, 384 at 4K).
- **The native level waits whole.** Its objects are gathered on the worker, never on the main
  thread when frames are streamed: for the view as it moves, and ahead for a destination. While
  its ground cells or objects are still on their way the half-scale impostors stay up,
  magnified, if they are whole.
- **Objects** at the native level come from a region around the view, gathered and depth-sorted
  on a worker thread from tight tile spans (every sprite measured against its footprint, shadows
  included), re-gathered before the view reaches the region's edge and at a flight's destination
  on the way. The main thread culls the region to the view and emits sprites: no sorting, no
  allocation. Raised tiles that hide an item (world-tech §4.3's rule) join the sort and are drawn
  again over it; the ground goes under anything whose footprint covers it.
- **Shadows** are one layer (alpha normalised to a peak of 1, page by page, composited once at
  the measured opacity). A set with a shadow page (`<set>.s.json`: every shadow at half size)
  has its shadows drawn from it, twice their texels and filtered: one draw per set in view.
  **Grading** multiplies the clock's ambient by the themes' keyframes; **glow** is added after
  it, page by page; **haze** leans the frame toward the themes' colour.
- **Rain and snow** are one picture each (streaks at fixed places over a 512-px pane that tiles
  the world, four densities side by side), scrolled as it falls and drawn as a mesh of
  256 x 128 px cells whose corners ask the showers how hard it rains there: a few hundred quads
  for a whole view in the rain.
- **Pages**: the sets of the regions sampled every 8 tiles over the view grown by 64 (and over
  a destination) are wanted; PNGs decode on a worker and upload in 1 MB slices within a time
  budget per frame (1.5 ms for a page the view waits for, 0.5 ms for one loaded ahead) into
  pre-made, pre-touched textures, static on GPU renderers, streaming on the software one. While
  the ceiling (640 MiB) holds every page on disk, each has a texture of its own size and nothing
  is ever given up: the pages the view does not need yet load ahead in the background, so a
  journey to any city finds its art resident. Sets that outgrow the ceiling stream through equal
  4096² slots instead (idle pages out least recently used first; only a view needing more pages
  than the budget adds a slot); the shadow pages are always kept.
- **Draw calls**: cells, shadows and glow are drawn page by page. The objects are given in the
  painter's order and drawn in runs of one page (`page_runs.hpp`): a sprite joins the last run
  of its page unless something it is drawn over came after that run, so what does not meet on
  screen need not wait its turn. What is left is where sprites of two pages really are stacked
  on one spot; `laeticias-world --bench` names them under any city view over its draw calls.

## Missing art

Items without art draw their catalog `stand_in` (home art) when one is named, else a box of the
catalog height over the footprint, coloured by kind and labelled with the id. Terrain without art
is a flat diamond of the catalog `colour` (water darker by depth band); faces without art are flat
by material. `laeticias-world --report` lists all of it with counts; ids in no catalog are listed
as not drawn.

## Measured (release, development machine's GPU, opengl offscreen, vsync off, GPU synced)

Whole frame in ms (average / 95th / 99th / worst), most draw calls in a frame, texture MiB:

| Case | 1920 x 1080 | 2560 x 1440 | 3840 x 2160 |
|---|---|---|---|
| Parsa terrace, 1x | 0.34 / 0.43 / 0.75 / 1.90, 15, 381 | 0.55 / 0.76 / 1.00 / 2.26, 20, 394 | 1.08 / 1.45 / 1.54 / 1.63, 29, 525 |
| Agora, 1x, dusk | 0.44 / 0.47 / 0.73 / 3.25, 38, 477 | 0.67 / 0.71 / 0.90 / 2.08, **52**, 490 | 1.33 / 1.42 / 1.59 / 1.79, **79**, 621 |
| Acropolis, 1x, night | 0.53 / 0.57 / 0.82 / 0.87, 17, 477 | 0.78 / 0.86 / 0.93 / 1.23, 23, 490 | 1.53 / 1.64 / 1.81 / 2.41, **61**, 653 |
| Pan at 1800 px/s | 0.39 / 0.55 / 0.79 / 1.87, 25 | 0.59 / 0.81 / 1.09 / 2.16, 26 | 1.20 / 1.54 / 1.70 / 1.99, 27 |
| Flight Parsa to Athens | 0.33 / 1.00 / 1.29 / 2.19, 12 | 0.44 / 1.14 / 1.29 / 2.97, 21 | 0.72 / 1.72 / 2.09 / 2.58, 26 |
| Overview | 0.18 / 0.19 / 0.42 / 1.84, 5 | 0.26 / 0.26 / 0.27 / 0.54, 5 | 0.53 / 0.54 / 0.80 / 1.79, 5 |

CPU (update and submission) averages 0.1–0.5 ms. Draw calls go over world-tech's 40 at 1440p and
4K where home stand-ins (the world set's trees) interleave with a city's pages in depth; the world
set's own page will not remove that interleaving, so the next step is merging small pages or
drawing stand-ins from a copy on the city page. Load to first frame: world 60–70 ms,
renderer set-up (sprite tables, generated page, slots, warm-up) under 0.3 s; the overview builds
on a worker in about 1 s and shows when ready.

## In the game

- `WorldView::draw(ViewSpec, clock, Lighting, dt, now, Hooks)`: the game's scene draws the home
  (the `Hole`) at the hooks' turns while it is in view; `composite()` redraws the last frame for
  the glass blur. `places()` (the place, its caption, era changes), `pick()` and
  `visibleCards()` (cards and the journal), `setSeason()`, `setWeather()` (a `WeatherField`:
  cloud shadows, wet ground, rain and snow outside the hole), `holeChanged()` (the home's rim
  terrain changed).
- `Soundscape` (beds, zones, item loops, city music on phrases) and `WeatherField` (world-wide
  deterministic weather) are pure; the app turns them into mixer calls and the home's weather.
- Page slots follow the sets on disk (the two largest sets and the world set); glow is drawn
  live over the impostors at the coarser levels.

## City life on screen

- `setLife(city)` resolves every kind's frames (`ActorLooks`: per variant, animation and facing;
  carry points from the geometry; goods and stacks); `setLifeAlpha` places actors between steps.
  Each native frame `prepareActors` gathers the view (plus a margin), resolves frames (walks by
  distance at the catalog's `stride`), and `ActorMerge` (order.hpp) bounds each actor between
  the static elements behind and in front of it (a walk-floor piece or an unsplit deck under
  the feet, a landmark piece over the tile over the head), propagates the bounds between
  overlapping actors and schedules them where their page is bound. Half and quarter scale draw
  people over the impostors (not those under a roof); the overview none.
- `CitySound` (pure) turns the region files' sound data and what is drawn into loop gains and
  one-shots; the app plays them.
- Still home-only: trees, grass and smoke swaying in the wind and gusts, chimney and brazier
  smoke, petals and leaves, moths at lamps, ripples and fish, waterfalls at drops, birds, and the
  event delights (rainbow, shooting stars, birdsong) away from home; they belong in the world by
  rule (items' `emitters` and `smoke_at`, terrain), within the particle budget. Actors carry no
  light of their own (no `glow` frames in the walker art yet).

### Crowds measured (the game's `--bench`, release, opengl offscreen, GPU synced, quiet machine)

Whole frame average / 99th percentile, CPU average (ms), world draw calls at most, live / drawn
actors, city simulation average (ms):

| Case | 1920 x 1080 | 2560 x 1440 | 3840 x 2160 |
|---|---|---|---|
| Rome, busiest 07:00 | 6.8 / 10.3, 4.3, 52, 390 / 34, 0.26 | 9.6 / 11.6, 5.7, 103, 544 / 82, 0.47 | 13.8 / 15.7, 9.3, 208, 789 / 256, 0.67 |
| Rome, Parilia | 8.9 / 11.0, 4.7, 53, 381 / 33, 0.34 | 9.5 / 11.3, 5.5, 97, 556 / 82, 0.50 | 13.6 / 15.6, 9.1, 233, 800 / 253, 0.68 |
| Athens, busiest | 8.6 / 10.6, 4.7, 63, 495 / 43, 0.37 | 9.2 / 11.1, 5.5, 111, 508 / 106, 0.40 | 11.7 / 13.8, 7.9, 215, 788 / 251, 0.69 |
| Athens, Panathenaia | 8.4 / 10.5, 4.5, 62, 487 / 37, 0.31 | 9.3 / 11.1, 5.5, 99, 493 / 88, 0.32 | 11.7 / 13.7, 7.8, 201, 796 / 218, 0.67 |
| Pārsa, busiest | 8.7 / 11.1, 4.6, 63, 506 / 38, 0.31 | 9.4 / 11.4, 5.6, 96, 516 / 117, 0.34 | 12.0 / 13.7, 8.1, 186, 800 / 215, 0.65 |
| Pārsa, spring audience | 5.7 / 8.8, 3.9, 61, 520 / 43, 0.28 | 9.3 / 11.1, 5.6, 110, 524 / 124, 0.42 | 11.4 / 13.3, 7.5, 191, 780 / 226, 0.65 |
| Pan across Rome | 6.2 / 8.6, 3.8 | 8.0 / 11.4, 4.8 | 10.5 / 15.2, 6.5 |
| Fast travel to Rome / home | 230 / 275 ms, worst frame 8.3 / 10.7 | 282 / 341 ms, worst 9.8 / 15.1 | |

Over budget everywhere on CPU (2 ms) and on the 99th percentile; the crowd adds 0.2–0.8 ms of
preparation and, at 1440p and 4K, many draw calls: actors wait for their page only until a
static element in front of them comes, and in dense streets that is often. Next: actors' sprites
on the city's own pages beside its buildings (or a per-page actor pass with tighter occlusion),
and the game frame's own CPU (QA5: the home scene and the glass panels).
