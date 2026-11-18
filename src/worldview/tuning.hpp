#pragma once
// The world renderer's and viewer's tunable numbers, in one place (budgets from CLAUDE.md
// "Performance" and docs/design/world-tech.md §4.14).

#include <array>
#include <cstddef>

namespace lc::worldview::tuning {

inline constexpr std::size_t kMiB = 1024 * 1024;

// Zoom levels after the overview (window px per art px). Below 1 the world is drawn from
// pre-rendered cell impostors; the overview level fits the whole world on screen.
inline constexpr std::array<float, 5> kZoomLevels{0.25f, 0.5f, 1.0f, 2.0f, 3.0f};
inline constexpr int kDefaultZoom = 3; // index into the viewer's levels (0: overview), here 1x
inline constexpr float kOverviewMargin = 0.94f; // share of the window the whole world fills

// Cell cache: square cells of world pixels, rendered once into slots of shared page textures.
inline constexpr int kCellTexels = 512;   // slot side; a level-L cell spans 512 << L px
inline constexpr int kCellPageSlotsX = 8; // cache pages of 4096 x 2048: few pages, few draws
inline constexpr int kCellPageSlotsY = 4;
inline constexpr std::size_t kCellBudget = 96 * kMiB;      // world-tech §4.14: ground cache 96 MB
inline constexpr double kCellBudgetArea = 2560.0 * 1440.0; // ... per this much window,
inline constexpr double kCellBudgetMaxScale = 1.5; // and at most this many times it (144 at 4K)
inline constexpr int kImpostorBlock = 1024;       // impostor cells render in blocks of this many px
inline constexpr int kCellBuildsPerFrame = 4;     // native cells (re)built per frame at most
inline constexpr int kImpostorBlocksPerFrame = 1; // impostor blocks drawn per frame at most
inline constexpr int kImpostorCellsInFlight = 4;  // impostor cells gathering at once
inline constexpr int kCellPrefetch = 1; // ring of cells around the view built when budget allows

// Atlas pages: streamed per set, decoded off the main thread, uploaded in slices.
// Page slots follow what the sets on disk need (PageAtlas); this only caps them.
inline constexpr std::size_t kPageCeiling = 640 * kMiB;
inline constexpr int kUploadRowsPerFrame = 64;   // 1 MB of a 4096-wide page per frame
inline constexpr int kPagesInFlight = 2;         // decoded or decoding, not yet in their slot
inline constexpr double kPageIdleSeconds = 10.0; // unused this long: may be evicted
inline constexpr int kNeededSetGrow = 64;        // tiles around the view whose sets load
inline constexpr int kNeededSetSpacing = 8;      // district sampling step, tiles

// Objects near the camera are gathered into a region this much larger than the view.
inline constexpr float kRegionGrow = 0.5f;
inline constexpr float kRegionEarly = 0.2f; // re-gather once the view comes this close to its edge
inline constexpr int kRegionMinGrow = 12;   // tiles

// The overview: an isometric map of the whole world generated at load, at this scale.
inline constexpr int kOverviewDivisor = 16; // world px per overview px

// Themes (world-tech §4.6): weights low-passed with this time constant; captions change only
// when the dominant region leads by this margin.
inline constexpr float kThemeSeconds = 1.0f;
inline constexpr float kCaptionHysteresis = 0.1f;
inline constexpr float kCaptionSeconds = 3.0f;
inline constexpr float kCaptionFade = 0.5f;
inline constexpr float kPlaceDwell = 0.4f;   // the region under the view counts after this long
inline constexpr float kVisitGap = 20.0f;    // away from a place this long: coming back is a visit
inline constexpr float kOverviewGlow = 0.6f; // lights at the overview: fewer pixels, softer
inline constexpr float kHazeShare = 0.5f;    // how much of a region's haze strength tints the view

// The soundscape (world-tech §4.6, §4.12). Levels are mixer gains before the player's buses.
inline constexpr float kBedLevel = 0.5f;      // a region's bed at its full weight
inline constexpr float kZoneLevel = 0.6f;     // a zone with the view inside it
inline constexpr float kZoneReach = 12.0f;    // tiles outside a zone where it fades to nothing
inline constexpr float kItemLoopLevel = 0.5f; // the nearest fountain, brazier ... on its tile
inline constexpr float kLoopReach = 14.0f;    // tiles
inline constexpr float kLoopRefresh = 0.1f;   // seconds between nearest-source searches
inline constexpr float kSeamDuck = 0.5f;      // -6 dB under a seam's drone
inline constexpr float kMusicThreshold = 0.5f;
inline constexpr float kMusicHysteresis = 0.1f;
inline constexpr float kMusicFadeSeconds = 4.0f;
inline constexpr float kMusic = 0.55f; // a city's piece, as the home's stems (core kMusicLevel)

// Look of things that have no art yet.
inline constexpr float kFaceShadeSE = 0.78f; // flat faces: the south-east side is darker
inline constexpr float kFaceShadeSW = 0.92f;
inline constexpr float kWaterDepthTint = 0.08f; // per sea depth band
// Beyond the grid the sea runs on to the horizon, fading into haze over this many tiles.
inline constexpr float kHorizonTiles = 40.0f;
inline constexpr float kHorizonHazeMax = 0.85f;
inline constexpr std::array<float, 3> kHorizonHaze{0.70f, 0.79f, 0.84f};
inline constexpr float kFlatJitter = 0.04f;       // per-tile brightness variation of flat terrain
inline constexpr float kPlaceholderHeight = 4;    // px: a low slab over the footprint
inline constexpr float kPlaceholderAlpha = 0.55f; // the land shows through it

// Fallback shadow opacity when no resident page measured one.
inline constexpr float kShadowOpacity = 0.4f;

// Camera flights (world-tech §4.7): eased, zooming out mid-way.
inline constexpr float kFlightSeconds = 1.5f;
inline constexpr float kPanTilesPerSecond = 24.0f; // keyboard pan in the interactive viewer

// Budgets the bench asserts (CLAUDE.md Performance).
inline constexpr double kFrameP99Ms = 8.3;
inline constexpr double kFrameWorstMs = 16.6;
inline constexpr double kCpuAvgMs = 2.0;
inline constexpr int kDrawCallsMax = 40; // world-tech §4.4, a full city view at zoom 1

} // namespace lc::worldview::tuning
