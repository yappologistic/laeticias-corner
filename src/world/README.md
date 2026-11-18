# src/world: the world data runtime

Loads, validates and serves the prebuilt world that `tools/worldgen` and `tools/artgen` write:
`assets/world/world.json`, the layers `assets/world/layers/<id>.lcw` and their graphs, the region
files `assets/regions/<id>.json`, the set catalogs `assets/sets/<set>/catalog.json`, the atlas
page manifests `assets/atlas/<set>.<n>.json` and the geometry `assets/atlas/<set>.geom.json`.
Pure logic like `src/core` (no SDL), library `lc_world`, linking `lc_core` and nlohmann_json.
Nothing here renders or simulates; it is what the next engine round builds on.

## Shape

| Header | What |
|---|---|
| `loader.hpp` | `loadWorld(assets, homeCatalog)` → `LoadedWorld`: everything below, diagnostics, timings, `memoryBytes()` |
| `world_map.hpp` | `WorldMap`: the composed, resident world in 32 × 32 chunks; tile, item, piece, walk, slot and theme queries; the home seam (`HomeDelta`, `homeDeltaFrom`, `applyHome`) |
| `road_graph.hpp` | `RoadGraph`: the layers' graphs merged at portals; nearest node, O(1) next hops towards destinations, A* with reusable scratch, polylines; lanes |
| `content.hpp` | `Content`: home catalog (core's parser) + set catalogs + geometry joined by id; cross-file checks; `HomeContract` (the `tile.level`, `sets`, `world`, terrain `faces`/`under` fields core's parser ignores) |
| `world_file.hpp`, `layer_file.hpp`, `graph_file.hpp`, `region_file.hpp`, `set_catalog.hpp`, `atlas_pages.hpp`, `geometry.hpp` | one strict reader per format; errors name the file, the object and, for layers, the grid tile |
| `digest.hpp` | per-chunk FNV-1a digests of terrain, levels, districts and items, item counts, graph sizes; computed identically by `tests/world_tools/world_digest.py` from worldgen's reader |
| `diagnostics.hpp`, `tuning.hpp` | what a load skipped (errors: wrong data; warnings: expected gaps); the module's tunable numbers |
| `worldinfo_main.cpp` | the `worldinfo` tool (below) |

Load policy: contract and format errors in `catalog.json`, set catalogs, geometry, atlas
manifests and `world.json` stop the load with a precise message. A missing or broken layer, graph
or region file is left out with one diagnostic and the layers below show (world-tech §2.4).
Unknown terrain ids stay (drawn as the placeholder; water decided by name); unknown item ids are
skipped, one diagnostic per id with its count and first tile.

### Storage and queries

- Per tile 8 bytes: terrain (world table index), level byte, district, walk bits, occupancy
  (`u32`). Items are 16-byte `Placed` records indexed by the chunk of their origin; footprints
  over 8 × 8 are listed in every chunk they cover (`forEachItemIn` reports them once).
- `piecesIn(rect, out)`: items and the pieces of split landmarks overlapping a rect, sorted by
  footprint-centre depth key for `DepthSorter`, into a reused vector; walk-run floor pieces flagged.
- Walking: a tile is walkable if it has ground that is not water nor impassable, or a walkable
  item (deck when on water), or a walk tile of the item on it; a solid item blocks it, furniture
  on a landmark's walk tile takes the tile. `floorZ` gives the floor height in px (stairs
  interpolate foot → head, landmark walk floors use `walk_z`). `walkNeighbours` allows a step when
  the facing edge heights match within half a level (one level when a deck is involved); stairs
  are entered only at the foot and the head, never over their sides.
- Slots: geometry spots joined with catalog behaviour (kind, cap) at continuous tile positions;
  home items keep their home-catalog slots. Queries by radius (chunk index) and by district and
  kind (CSR index); `beside` slots are left to the user (free tiles around the item).
- Themes: `themeWeights(centre, out)` samples the district plane 9 × 9 at 8-tile spacing with the
  §4.6 radii (city 32, town 12, stretch and home 24, seam 16), normalised, heaviest first. The
  1 s low-pass and music hysteresis are the engine's (they need state).
- Graph: next-hop tables per destination node over its region's nodes (≤ 64 per region),
  built at load; `nextHop` is a table lookup. Long routes: `shortestPath` once, keep the polyline.

### Measured (release build, this machine)

Full world load 32 ms (catalogs, geometry and manifests 22, layers 2, composition 6, graphs 2);
`worldinfo` cold start 40–50 ms. Memory held by the loaded world 6.3 MB (map 4.8 MB), within
world-tech §2.8's ≈ 15 MB; a `worldinfo` process peaks at 16 MB resident. Queries: tile lookup
6 ns, walk neighbours 100 ns, a 64 × 64 view of the Pārsa terrace (356 items and pieces) 13 µs,
theme weights 0.8 µs, next hop 5 ns, A* across Pārsa 4 µs, nearest node 2.5 µs (random tiles,
mostly far from any road). `world_perf` asserts load < 300 ms, memory ≤ 15 MB and the per-frame
query budgets in optimised builds.

## Formats as implemented, and how they differ from `docs/design/world-tech.md`

Where the document and the files disagree, the files win; these are the differences found.

1. **Layer order.** `world.json` lists 29 layers; 4 exist (`base`, `parsa`, `ostia`, `corner`),
   the rest are skipped with a warning. `corner` is composed last, not second as in §2.3.
2. **Region files** do not exist yet (`assets/regions/` is absent): every region loads with the
   default theme. The reader follows §2.6; life sections (`figures`, `groups`, `chains`,
   `events`, `lanes_tokens`) and unknown sections are kept raw in `RegionFile::life`.
3. **Set catalogs for `world` and `rome` do not exist.** Worldgen resolves their ids from
   `tools/worldgen/plan/provisional.py` (V1 warnings only); the engine reads only contracts, so
   13 terrain ids draw as placeholders and 24 item ids (9 144 placed items, 8 000 of them base
   trees, plus Ostia's town and Portus) are skipped. The digest cross-check applies the same rule.
4. **Connect layouts** in set catalogs say `"count": 1`; CLAUDE.md says 16 masks. Read as 16.
5. **Water** is not stated in set catalogs (`parsa.water_channel` has no `"water": true`);
   worldgen decides by name (`WATER_NAMES`). The engine mirrors that list in one place
   (`waterByName`) and honours `"water"` when a catalog states it.
6. **Stair direction** is not stored anywhere. Kit stairs climb away from the side they face
   (worldgen's `stair(face=…)`; r0 faces +y), regardless of the catalog `axis`:
   `parsa.stair_relief` says `axis: "x"` but climbs across its one-tile depth (y at r0).
   Landmark stairs (r0 only) climb along `axis`; the engine picks the end whose neighbours stand
   `rise` levels up. A stair with no such end is a diagnostic.
7. **Geometry extras** beyond §1.10: `walk_z` (`{"dx,dy": px}`, floor height of a walk tile above
   the item's level) and `floor_pieces` (indices of walk pieces that are stair floors). Variant
   keys are `r<k>` (also `r4`, `r5` for variant layouts with more looks) and `m<mask>` for
   connect layouts.
8. **Landmark stairs with walk tiles** (`parsa.great_stair`): worldgen's walk map makes the whole
   footprint walkable for `rise > 0`; the engine uses the walk tiles when the geometry lists them.
9. **Composition drop rule**: worldgen drops a lower item through its occupancy grid (first item
   wins a tile), the engine by footprint as §2.4 states; they agree unless a lower layer has
   overlapping items. Furniture on a landmark's walk tile (allowed by V2) takes that tile.
10. **The home** (§4.1): the corner layer leaves the home rect transparent, so the base's
    `corner/reserved` land shows until a delta is applied; `applyHome` drops prebuilt items
    touching the rect (none today), writes terrain at the home level and keeps the district.
11. **`assets/catalog.json`** carries `sets`, `world` and home terrain `faces` (`grass` names
    `world.earth` and `world.coast`, materials of the missing `world` set) which core's parser
    ignores; `HomeContract` reads them.
12. **Strictness** beyond worldgen's reader: reserved header fields, item flags and level-byte
    bit 7 must be 0; plane values must lie in their tables; atlas images must be named
    `<set>.<n>.png`; sprites must fit a 4096 page.
13. **Sizes** (§2.8): today's world holds 31 terrain ids, 92 districts, 7 914 resolved items and
    428 graph nodes.

## Data findings (for the world builders)

- `assets/world/layers/base.lcw`: `athens.t_olive` placed with variant 3, its catalog has 3
  looks (914 placed, first at grid (381, 272)); `athens.t_cypress` with variants 2 and 3, its
  catalog has 2 (436 placed, first at grid (426, 457) and (426, 460)). These draw as
  placeholders. `worldinfo validate` lists every diagnostic; `world_unit` fails on any new error.
- The 24 `world.*` / `rome.*` item ids and 13 terrain ids above need set catalogs.

## worldinfo

```sh
build/release/worldinfo                    # summary: sizes, layers, items, graphs, timings, memory
build/release/worldinfo validate           # every diagnostic, exit 1 on errors
build/release/worldinfo region parsa       # a region's districts, items and graph nodes
build/release/worldinfo tile 378 49        # terrain, level, district, walking, items, slots
build/release/worldinfo digest             # same JSON as tests/world_tools/world_digest.py
build/release/worldinfo --assets DIR ...   # another assets directory
```

The digest cross-check (`ctest -R world_digest`) runs worldgen's reader on today's data at test
time and compares; it is skipped when `tools/worldgen/.venv` is absent. The invariant checks in
`world_unit` always run.

## Wiring it into the engine (next round)

- **Start-up:** after `loadCatalog`, call `loadWorld(assets, catalog)` when `world.json` exists
  (else today's island). Log `diagnostics` once. Keep the `LoadedWorld` beside the catalog (the
  map points at its `Content`).
- **Home:** convert the save's home map with `homeDeltaFrom(saveData.world, catalog)` and
  `applyHome` it after load and after every home edit; only the home rect's chunks are rebuilt.
  Build tools keep editing core's 40 × 40 `World`; conditions stay over the home rect.
- **Rendering by chunk:** cull to the chunks under the view grown by the tallest sprite
  (`GeomVariant::h`, `level × tile.level`); the ground cache reads `terrainAt`, `levelByte`
  (level, aux → the terrain's `faces` for edge materials, sea depth band, river flow) per chunk;
  items come from `piecesIn(viewRect, buffer)` as footprints for `DepthSorter`, drawn at their
  `level`; floor pieces go before actors on their tiles (§4.4).
- **Atlas pages:** `AtlasPages::find(key)` gives every set sprite's page before pixels load;
  the needed sets are the `RegionRef::set` of the regions sampled under the view (`regionAt`).
- **Themes:** feed `themeWeights` into the 1 s low-pass; grading, haze and ambience from the
  regions' `RegionFile::theme`.
- **Actors at scale:** `walkNeighbours`/`floorZ` for steps and heights; `RoadGraph::nextHop` for
  walkers heading to destinations; `shortestPath` + `polyline` once per token route; slots by
  `forEachSlotNear` / `forEachSlotInDistrict`; districts and densities from region files.
- **Tuning:** `src/world/tuning.hpp` holds this module's numbers; move them into
  `src/core/tuning.hpp` when merging if one place for all simulation numbers is preferred (this
  branch was not allowed to edit it).
