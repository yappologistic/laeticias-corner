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
inline constexpr int kCellTexels = 512;               // slot side; a level-L cell spans 512 << L px
inline constexpr int kCellPageSlots = 4;              // slots per cache page side (2048 x 2048)
inline constexpr std::size_t kCellBudget = 96 * kMiB; // world-tech §4.14: ground cache 96 MB
inline constexpr int kImpostorBlock = 1024;   // impostor cells render in blocks of this many px
inline constexpr int kCellBuildsPerFrame = 4; // native cells (re)built per frame at most
inline constexpr int kImpostorBuildsPerFrame = 1;
inline constexpr int kCellPrefetch = 1; // ring of cells around the view built when budget allows

// Atlas pages: streamed per set, decoded off the main thread, uploaded in slices.
inline constexpr std::size_t kPageBudget = 320 * kMiB; // world-tech §4.14
inline constexpr int kUploadRowsPerFrame = 512;        // 8 MB of a 4096-wide page per frame
inline constexpr double kPageIdleSeconds = 10.0;       // unused this long: may be evicted
inline constexpr int kNeededSetGrow = 64;              // tiles around the view whose sets load
inline constexpr int kNeededSetSpacing = 8;            // district sampling step, tiles

// Objects near the camera are gathered into a region this much larger than the view.
inline constexpr float kRegionGrow = 0.5f;
inline constexpr int kRegionMinGrow = 12; // tiles

// The overview: an isometric map of the whole world generated at load, at this scale.
inline constexpr int kOverviewDivisor = 16; // world px per overview px

// Themes (world-tech §4.6): weights low-passed with this time constant; captions change only
// when the dominant region leads by this margin.
inline constexpr float kThemeSeconds = 1.0f;
inline constexpr float kCaptionHysteresis = 0.1f;
inline constexpr float kCaptionSeconds = 3.0f;
inline constexpr float kHazeShare = 0.5f; // how much of a region's haze strength tints the view

// Look of things that have no art yet.
inline constexpr float kFaceShadeSE = 0.78f; // flat faces: the south-east side is darker
inline constexpr float kFaceShadeSW = 0.92f;
inline constexpr float kWaterDepthTint = 0.08f; // per sea depth band
inline constexpr float kFlatJitter = 0.04f;     // per-tile brightness variation of flat terrain
inline constexpr float kPlaceholderHeight = 32; // px, when the catalog gives none
inline constexpr float kPlaceholderAlphaBig = 0.45f; // large landmark placeholders let land show
inline constexpr int kPlaceholderBigTiles = 36;

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
