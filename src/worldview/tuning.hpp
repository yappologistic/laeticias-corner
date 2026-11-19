#pragma once
// The world renderer's and viewer's tunable numbers, in one place (budgets from CLAUDE.md
// "Performance" and docs/design/world-tech.md §4.14).

#include "core/iso.hpp"

#include <array>
#include <cstddef>
#include <string_view>

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
// What the cache holds (world-tech §4.14, restated by the smoothness round): the view at its own
// level with a ring around it, and the two wider levels a zoom out would show, kCellSpare times
// that, so a pan or a turn of the wheel finds its cells still there; or, where that is more,
// what a view of nothing but sea needs for its water to move at every level (the ground once
// per step of the loop, WorldView::cellBudget). In MiB (one per slot, in whole pages of 32):
// 192 at 1080p, 224 at 1440p, 384 at 4K.
inline constexpr double kCellSpare = 1.5;
inline constexpr std::size_t kCellBudgetMin = 96 * kMiB;
inline constexpr std::size_t kCellBudgetMax = 384 * kMiB;
inline constexpr int kImpostorBlock = 1024;      // impostor cells render in blocks of this many px
inline constexpr int kImpostorCellsInFlight = 8; // impostor cells gathering or drawing at once
inline constexpr int kCellRing = 1;              // cells around the view kept built, at its level
// Cells are built on the main thread within a time budget per frame (at least one build a frame
// whatever it costs): more while something in view or at a zoom's destination is missing, less
// for what is only built ahead (the ring, the wider levels). In milliseconds.
inline constexpr double kBuildMsNeeded = 2.0;
inline constexpr double kBuildMsAhead = 1.0;
// Work ahead of need takes only the time a frame leaves: what the last frame cost the main
// thread without the cache's own work (WorldView::setFrameCost), up to this much in all, of the
// 2 ms a frame may cost on average; the rest is kept for the shader tiers and a busy machine.
// Never less than the floor, so the cache always fills.
inline constexpr double kFrameCpuRoomMs = 1.5;
inline constexpr double kBuildMsAheadMin = 0.2;
// The ring leans toward where the view is going: this many frames of its motion ahead, at most
// kCellAheadMax cells.
inline constexpr float kCellAheadFrames = 24.0f;
inline constexpr int kCellAheadMax = 2;
// The native level is shown once this share of its ground cells and of its objects' tiles over
// the view is there (the rest fills in cell by cell); below it the half-scale level stays up.
inline constexpr float kNativeReadyShare = 0.75f;
// Water loops longer than this many steps are cut to it (each step is a cached copy of a cell).
inline constexpr int kCellPeriodMax = 4;

// Atlas pages: streamed per set, decoded off the main thread, uploaded in slices.
// Page slots follow what the sets on disk need (PageAtlas); this only caps them.
inline constexpr std::size_t kPageCeiling = 640 * kMiB;
inline constexpr int kUploadRows = 64; // a slice: 1 MB of a 4096-wide page (about 0.9 ms)
// Slices go up until this much of a frame is spent (at least one): more for a page the view is
// waiting for than for one loaded ahead of need.
inline constexpr double kUploadMsWanted = 1.5;
inline constexpr double kUploadMsAhead = 0.5;
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
inline constexpr float kPlaceDwell = 0.4f; // the region under the view counts after this long
inline constexpr float kVisitGap = 20.0f;  // away from a place this long: coming back is a visit
// World weather (weather_field.hpp): blocks of the grid that each decide their cells per period.
inline constexpr int kWeatherBlock = 48;             // tiles
inline constexpr float kWeatherCellsPerBlock = 1.0f; // expected per period at clouds 1
inline constexpr float kWeatherLifeMin = 200.0f;     // seconds
inline constexpr float kWeatherLifeMax = 420.0f;
inline constexpr std::size_t kWeatherCellsMax = 512; // considered per update
inline constexpr float kWetMemory = 90.0f;           // seconds a shower's path stays wet
inline constexpr int kWetSamples = 3;
inline constexpr float kCloudShadow = 0.16f; // darkness under a cloud, a shower more
inline constexpr float kShowerShadow = 0.26f;
inline constexpr float kWetDarken = 0.22f;    // wet ground darkens by up to this
inline constexpr int kRainStreaksPerTile = 2; // falling over a rained-on tile at full strength
inline constexpr float kRainFall = 520.0f;    // px a streak falls per second
inline constexpr float kSnowFall = 60.0f;
inline constexpr float kRainFallTiles = 6.0f; // tile heights a streak falls to its ground
inline constexpr float kRainAlpha = 0.55f;
inline constexpr float kSnowAlpha = 0.9f;
// The rain is a picture scrolled over a mesh (WorldView::drawRain).
inline constexpr int kRainPane = 512;  // px: the picture's tile each way (a power of two)
inline constexpr int kRainLayers = 4;  // its densities, side by side in one texture
inline constexpr int kRainMeshW = 256; // px between the corners that ask the showers
inline constexpr int kRainMeshH = 128; // (both divide the pane)
// Climates the region files name, against the season's own (until the files carry numbers):
// Rome's April showers, the Attic dry summer and its meltemi, dry bright Parsa, the open sea's
// squalls.
struct ClimateRow {
    std::string_view name;
    float showers;
    float clouds;
    float wind;
};
inline constexpr ClimateRow kClimates[] = {
    // The catalog's climates (world-seasons.md): showers, clouds, wind, until their months are
    // read.
    {"home", 1.0f, 1.0f, 1.0f},          {"med_green", 1.2f, 1.1f, 1.0f},
    {"med_dry", 0.35f, 0.6f, 1.6f},      {"highland", 1.3f, 1.2f, 1.2f},
    {"thracian", 1.2f, 1.1f, 1.2f},      {"levant", 0.4f, 0.6f, 1.1f},
    {"anatolian", 0.8f, 0.9f, 1.2f},     {"high_mountain", 1.4f, 1.3f, 1.5f},
    {"mesopotamian", 0.15f, 0.3f, 1.0f}, {"steppe", 0.4f, 0.6f, 1.4f},
    {"fars", 0.15f, 0.35f, 0.9f},        {"plateau", 0.25f, 0.45f, 1.1f},
    {"sea_west", 1.0f, 1.0f, 1.3f},      {"sea_aegean", 0.6f, 0.8f, 1.5f},
    {"gulf", 0.2f, 0.4f, 1.1f},
};
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
inline constexpr float kBedFadeSeconds = 20.0f; // beds crossfade at an hour's or a month's turn
inline constexpr float kSnowBedDuck = 0.29f;    // -3 dB on the beds while snow lies
inline constexpr float kStretchLift = 1.41f;    // +3 dB on the beds of places without music

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

// City life on screen (src/life/).
inline constexpr float kActorMoving = 0.05f;  // tiles/s: faster than this walks by distance
inline constexpr float kActorWalkPace = 0.9f; // tiles/s at which walk frames play at the art's fps
inline constexpr Vec2 kCarryAt{3, -31};       // px from the feet: goods in hand, no carry point
inline constexpr float kActorFoot = 0.2f;     // half the square round the feet, tiles
inline constexpr float kCoverHalfBody = 6.0f; // px either side of the feet a body takes
inline constexpr float kCoverHidden = 4.0f;   // px of something in front over the feet: hidden
inline constexpr int kActorMargin = 3;        // tiles beyond the view gathered (sprites overhang)
inline constexpr std::size_t kActorBuffer = 2048; // actors gathered per frame at most
inline constexpr float kActorShadowW = 0.42f;     // the soft shadow under the feet, tiles wide
inline constexpr float kActorShadow = 0.75f;      // its strength in the shadow layer
inline constexpr float kMemoryAlpha = 0.5f;       // memories are translucent
inline constexpr float kActorMergeCell = 128.0f;  // the merge's screen grid, world px

// City life's sound (city_sound.hpp; out/reports/audio-atmosphere.md "How the engine should mix").
inline constexpr float kCityRainOn = 0.05f;  // rain intensity at which rain is heard
inline constexpr float kCrowdHandful = 5.0f; // people in view: level 1 up to here
inline constexpr float kCrowdMarket = 20.0f; // level 2 up to here, festival beyond
inline constexpr float kCrowdRain = 0.4f;    // crowds hush in the rain (look.md §3.6)
inline constexpr float kCityWind = 0.6f;
inline constexpr float kRainSurface = 0.8f;
inline constexpr float kDawnFrom = 5.0f; // game hours of the climate's beds
inline constexpr float kDawnTo = 7.0f;
inline constexpr float kDuskFrom = 18.5f;
inline constexpr float kDuskTo = 20.5f;
inline constexpr float kNatureBed = 0.7f;
inline constexpr float kCicadas = 0.7f;
inline constexpr float kEventReach = 24.0f;    // tiles beyond half the view an event is heard
inline constexpr float kWorkReach = 14.0f;     // tiles a work loop carries (plus a quarter view)
inline constexpr float kCitySlowTick = 0.1f;   // s: work, voices
inline constexpr float kWorkShotEvery = 14.0f; // s between a worker's sounds, on average
inline constexpr float kVoiceEvery = 30.0f;    // s between an animal's calls, on average
inline constexpr float kWorkLoop = 0.8f;
inline constexpr float kWorkShot = 0.6f;
inline constexpr float kVoice = 0.6f;
inline constexpr float kCart = 0.7f;
inline constexpr float kStepZoom = 2.0f;   // footsteps from this zoom in
inline constexpr float kStepReach = 6.0f;  // tiles
inline constexpr float kStepTiles = 0.45f; // tiles walked per step
inline constexpr float kStep = 0.45f;
inline constexpr float kLifeShot = 0.9f;
inline constexpr float kCallMin = 25.0f; // s between birds' and animals' calls
inline constexpr float kCallMax = 70.0f;
inline constexpr float kCall = 0.6f;
inline constexpr std::size_t kShotsPerUpdate = 8;
// The year in sound (out/reports/audio-seasons.md §5).
inline constexpr float kSting = 0.7f;      // sunrise, nightfall, a storm's end, a season
inline constexpr float kStingDuck = 0.79f; // -2 dB on the music under a sting
inline constexpr float kStingDuckSeconds = 3.0f;
inline constexpr float kStormRain = 90.0f; // s of rain before its end has a sting
inline constexpr float kTreesWind = 0.5f;  // wind in the crowns where trees cover the view
inline constexpr float kTreesFull = 3.0f;  // a district a third trees is heard in full
inline constexpr float kWater = 1.0f;      // sea, shore and river by their share of view
inline constexpr int kWaterSamples = 8;    // per side of the view, at the slow tick
inline constexpr int kShoreTiles = 4;      // water this far from land is open water
inline constexpr float kDripAfter = 60.0f; // s drops keep falling after the rain
inline constexpr float kDripMin = 0.4f;    // s between drops
inline constexpr float kDripMax = 2.5f;
inline constexpr float kDrip = 0.35f;
inline constexpr float kLayerFull = 4.0f;        // a quarter of the view fresh water: full layer

// Fallback shadow opacity when no resident page measured one.
inline constexpr float kShadowOpacity = 0.4f;

// Camera flights (world-tech §4.7): eased, zooming out mid-way.
inline constexpr float kFlightSeconds = 1.5f;
inline constexpr float kPanTilesPerSecond = 24.0f; // keyboard pan in the interactive viewer

// Budgets the bench asserts (CLAUDE.md Performance).
inline constexpr double kFrameP99Ms = 8.3;
inline constexpr double kFrameWorstMs = 16.6;
inline constexpr double kCpuAvgMs = 2.0;
inline constexpr int kDrawCallsMax = 40;      // world-tech §4.4, a full city view at zoom 1
inline constexpr int kRunBreakersListed = 16; // lines the bench names a view's page costs in

} // namespace lc::worldview::tuning
