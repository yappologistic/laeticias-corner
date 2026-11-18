# src/worldview: the world renderer and the viewer

Draws the prebuilt world that `src/world` loads (docs/design/world-tech.md §4.3–§4.8), and
`laeticias-world`, a headless viewer to look at it, measure it and take screenshots. Library
`lc_worldview` (links `lc_engine` for the atlas, batching, `putSprite`, `ScreenGrid`/`behind`,
the font and the clock's lighting, and `lc_world`). Nothing in the game uses it yet.

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
  stored in a 512 x 512 slot of a 4096 x 2048 cache page (96 MB, LRU, world-tech §4.14). Screen
  squares waste nothing (a chunk's diamond in a box wastes half), so 4K at 1x needs ~54 cells.
  Level 0 holds the ground: tiles in diagonal order at `level × tile.level` px, faces stacked
  under the +x/+y edges down to the neighbour by material (`aux` → terrain `faces`), the base and
  the overlay by mask, foam on water by land mask, the cap band (`…/top`) after the ground.
  Levels 1 and 2 are impostors of everything static: 1024-px blocks drawn at full resolution
  (ground, shadow layer, sorted items) and halved with filtering (2 x 2 box per halving). A cell is
  rebuilt only when its pages arrive late or its water animates; a cell not built yet shows its
  coarser level or the overview, so nothing flashes.
- **Objects** at the native level come from a region around the view, gathered and depth-sorted
  on a worker thread from tight tile spans (every sprite measured against its footprint, shadows
  included), re-gathered before the view reaches the region's edge and at a flight's destination
  on the way. The main thread culls the region to the view and emits sprites: no sorting, no
  allocation. Raised tiles that hide an item (world-tech §4.3's rule) join the sort and are drawn
  again over it; the ground goes under anything whose footprint covers it.
- **Shadows** are one layer (alpha normalised to a peak of 1, page by page, composited once at
  the measured opacity); **grading** multiplies the clock's ambient by the themes' keyframes;
  **glow** is added after it; **haze** leans the frame toward the themes' colour.
- **Pages**: the sets of the regions sampled every 8 tiles over the view grown by 64 are wanted;
  PNGs decode on a worker, upload in 1 MB slices into pre-made, pre-touched 4096² slots (drivers
  stall 20–40 ms on a fresh 64 MB texture), static on GPU renderers, streaming on the software
  one. Idle pages (10 s) are evicted LRU over 320 MB; when none is idle the least recent unwanted
  page goes; only a view needing more pages than the budget holds adds a slot (logged).
- **Draw calls** stay in the tens: cells and shadows are drawn page by page, items in the
  page-aware order (22 at the Agora, 10–17 on the Parsa terrace and the Acropolis).

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

## Merging into the game (next round)

1. Create `WorldView` beside the scene when `assets/world/world.json` exists; keep the island
   otherwise. Apply the save's home with `applyHome` (the viewer applies the starter scene) and
   call `CellCache::clear()`-style invalidation for the home rect's cells after every home edit
   (today only a full clear exists: add a rect invalidation when wiring edits).
2. Actors: merge them into `region_.order` per frame as world-tech §4.4 says (a `ScreenGrid`
   query against the static boxes); `Elem::floor` marks stair and walk floors, under actors on
   their tiles. The wild land's brambles and seasonal looks are not drawn yet.
3. UI over it (the glass panels and blur stay the game's), the era caption as a ribbon, picking
   (world-tech §4.3, §4.9), fast travel through the overview, audio themes from `ThemeMixer`
   weights and `RegionFile::theme` beds.
4. Move `tuning.hpp` into the game's tuning files if one place is wanted.
