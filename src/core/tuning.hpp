#pragma once
// Every tunable number of the simulation and presentation lives here.

#include <cstddef>

namespace lc::tuning {

// Simulation
inline constexpr double kStepSeconds = 1.0 / 60.0;
inline constexpr int kMaxStepsPerFrame = 5;
inline constexpr std::size_t kUndoSteps = 200;
inline constexpr double kAutosaveDelay = 1.5;       // seconds after the last change
inline constexpr double kAutosaveMaxDelay = 20.0;   // longest unsaved stretch while editing
inline constexpr double kSaveRetrySeconds = 10.0;   // after a failed save
inline constexpr double kThumbnailInterval = 300.0; // play seconds between world thumbnails

// Clock: fractions of one full cycle.
inline constexpr double kDayLengthSeconds = 12.0 * 60.0;
inline constexpr double kDuskStart = 0.50;
inline constexpr double kNightStart = 0.625;
inline constexpr double kDawnStart = 0.875;
inline constexpr double kPinEaseSeconds = 1.6; // time to glide to a pinned phase
inline constexpr double kMidnight = 0.75;      // a new calendar day begins here
// The season's colour grade glides to the new season over this share of a cycle (midnight to
// the end of dawn), or this many seconds when the season is pinned by hand.
inline constexpr double kSeasonGradeGlide = 0.25;
inline constexpr float kSeasonPinGlide = 2.0f;

// Lighting keyframes over the cycle, interpolated smoothly and wrapping at 1.0.
struct LightKey {
    double t;
    float ambient[3];
    float skyTop[3];
    float skyBottom[3];
    float glow;
    float night;
};
inline constexpr LightKey kLightKeys[] = {
    {0.04, {1.00f, 1.00f, 1.00f}, {0.55f, 0.74f, 0.86f}, {0.86f, 0.90f, 0.86f}, 0.0f, 0.0f},
    {0.46, {1.00f, 0.98f, 0.95f}, {0.56f, 0.72f, 0.85f}, {0.90f, 0.88f, 0.80f}, 0.0f, 0.0f},
    {0.56, {0.92f, 0.66f, 0.56f}, {0.34f, 0.32f, 0.52f}, {0.92f, 0.60f, 0.46f}, 0.65f, 0.45f},
    {0.66, {0.30f, 0.34f, 0.52f}, {0.04f, 0.05f, 0.12f}, {0.11f, 0.13f, 0.24f}, 1.0f, 1.0f},
    {0.84, {0.30f, 0.34f, 0.52f}, {0.04f, 0.05f, 0.12f}, {0.11f, 0.13f, 0.24f}, 1.0f, 1.0f},
    {0.94, {0.80f, 0.70f, 0.78f}, {0.44f, 0.48f, 0.68f}, {0.94f, 0.76f, 0.68f}, 0.35f, 0.3f},
};
inline constexpr float kRainSkyGrey = 0.45f; // blend of sky toward grey while raining

// Progress loop (docs/design/living-corner.md §12)
inline constexpr int kMaxOpenWishes = 3;
inline constexpr double kWishOfferGap = 75.0;      // play seconds between offers or grants
inline constexpr double kWishOfferGapEmpty = 30.0; // ... while no wish is open
inline constexpr double kWishSnooze = 600.0;       // "Not now" keeps a wish away this long
inline constexpr double kWishGrantHold = 1.5;      // a goal must hold this long to count
inline constexpr double kWishAlreadyDoneDelay = 3.0;
inline constexpr double kWishPacingTick = 1.0; // offers are considered once a second
inline constexpr double kConditionDebounce = 0.25;
inline constexpr float kNookPulseSeconds = 1.6f; // a found nook's area pulses this long
inline constexpr float kNookPulseAlpha = 0.5f;
inline constexpr float kNookLabelSeconds = 3.5f;  // its name floats above it this long
inline constexpr float kNookOutlineAlpha = 0.22f; // the hovered nook's area
inline constexpr float kNookLabelLift = 3.0f;     // tile heights above the anchor's centre
inline constexpr double kLandStageGap = 4.0;      // seconds between stages opening together
inline constexpr float kLandWaveStep = 0.08f;     // seconds per tile as the brambles clear
inline constexpr float kLandClearFade = 0.4f;     // each tile's brambles fade this long
inline constexpr float kWildDim = 0.70f;          // wild grass brightness
inline constexpr float kWildCool[3] = {0.94f, 0.99f, 1.08f};
inline constexpr float kWildThicketChance = 0.8f; // tiles of wild land with brambles
inline constexpr float kEdgeChipSeconds = 8.0f;   // "New land" chip for an off-screen stage

// Visitors
inline constexpr int kVisitorsPerNeed = 2; // satisfied once -> 2 visitors, twice -> 4...
inline constexpr float kFirstArrivalDelay = 1.0f;
inline constexpr float kArrivalInterval = 2.5f;
inline constexpr float kDepartureInterval = 1.2f;
inline constexpr float kFadeSeconds = 0.8f;
inline constexpr int kWanderRadius = 3;
inline constexpr float kLandSpeed = 0.9f; // tiles per second
inline constexpr float kWaterSpeed = 0.6f;
inline constexpr float kAirSpeed = 1.6f;
inline constexpr float kIdleMin = 1.0f;
inline constexpr float kIdleMax = 4.0f;
inline constexpr float kAirIdleMax = 1.2f;
inline constexpr float kVoiceChancePerSecond = 0.02f;
inline constexpr float kReturnToAnchorChance = 0.35f; // per new walk: head back to the attraction
inline constexpr int kTargetAttempts = 8;
inline constexpr int kSpawnAttempts = 16;
inline constexpr float kHoverMin = 0.5f; // flight height range, in tile heights
inline constexpr float kHoverMax = 1.1f;

// Camera
inline constexpr float kCameraEase = 12.0f;   // 1/s exponential approach
inline constexpr float kZoomEase = 14.0f;     // 1/s, in log scale
inline constexpr float kKeyPanSpeed = 720.0f; // screen px per second
// Fraction of the half view the view centre may stray beyond the land (keeps land on screen).
inline constexpr float kCameraReach = 0.8f;
inline constexpr float kFrameFill = 0.94f;     // framing leaves this much of the safe area used
inline constexpr float kWheelIdleReset = 0.4f; // seconds before a partial wheel step is dropped
// Critters are simulated within the visible tiles grown by this many tiles on each side.
inline constexpr int kActiveMargin = 16;

// Presentation. Lengths are in tile heights (or widths where noted), so they follow the art.
inline constexpr float kPopSeconds = 0.32f;
inline constexpr float kFadeOutSeconds = 0.22f;
inline constexpr float kGhostAlpha = 0.72f;
inline constexpr float kPaintSoundGap = 0.07f;
inline constexpr float kSmokeInterval = 0.45f;
inline constexpr float kSmokeRiseMin = 0.5f; // tile heights per second
inline constexpr float kSmokeRiseMax = 0.75f;
inline constexpr float kSmokeDriftMax = 0.3f;
inline constexpr float kRipplesPerSecondPerWaterTile = 0.035f;
inline constexpr float kRainRipplesPerSecondPerWaterTile = 0.6f;
inline constexpr float kRainDropsPerSecondPerTile = 0.58f;
inline constexpr float kRainFall = 5.6f;      // tile heights a drop falls
inline constexpr float kRainSpeed = 16.0f;    // tile heights per second
inline constexpr float kRainPoolShare = 0.6f; // most of the particle pool rain may take
inline constexpr float kRippleSeconds = 0.8f;
inline constexpr float kSplashSeconds = 0.22f;
inline constexpr float kLeavesPerSecondPerTree = 0.012f;
inline constexpr float kPetalsPerSecondPerTree = 0.03f;
inline constexpr float kSnowSpeed = 1.2f;  // tile heights per second
inline constexpr float kSnowShare = 0.35f; // snowflakes per raindrop the view would have
inline constexpr float kLeafFall = 0.56f;
inline constexpr float kLeafSway = 0.375f;
inline constexpr float kSparkleSpread = 0.6f;
inline constexpr float kSparkleRise = 0.4f;
inline constexpr float kWakeInterval = 0.9f; // seconds between ripples behind a swimming critter
inline constexpr float kPitchJitter = 0.06f;
inline constexpr float kRainAmbientDim = 0.85f;
// Night lighting. Pools sit on the ground in front of a light; radius in tile widths.
inline constexpr float kLightRadius = 0.8f;
inline constexpr float kLightRadiusPerSide = 0.45f;
inline constexpr float kLightStrength = 0.5f;
// At night a sprite brighter than this (mean luminance) is exposed down to it, so pale things
// never out-shine the lights.
inline constexpr float kNightLumaCap = 0.42f;
inline constexpr float kWaterShadowAlpha = 0.4f;
inline constexpr float kWarmLight[3] = {1.0f, 0.78f, 0.48f};   // lamp, fire and window pools
inline constexpr float kFireflyHalo[3] = {0.75f, 1.0f, 0.55f}; // light around a firefly
inline constexpr float kFireflyCore[3] = {0.8f, 1.0f, 0.5f};   // its glowing body
inline constexpr float kInvalidTint[3] = {1.0f, 0.45f, 0.42f}; // refused ghosts, removal mark
inline constexpr float kCritterMoveFps = 6.0f;
inline constexpr float kCritterIdleFps = 2.0f;
inline constexpr float kWarnSeconds = 1.6f; // how long a refusal stays in the hint line
inline constexpr float kClickSlop = 4.0f;   // window px a click may move and still be a click

// Rendering budgets
inline constexpr std::size_t kGroundCacheBytes = 128u << 20; // GPU memory for cached ground
// Objects are gathered for the view grown by this share of its size (at least the minimum, in
// tiles), so panning rarely rebuilds the depth order.
inline constexpr float kRegionGrow = 0.3f;
inline constexpr int kRegionMinGrow = 8;

// Audio levels (linear gain)
inline constexpr float kMusicLevel = 0.55f;
inline constexpr float kBirdsLevel = 0.45f;
inline constexpr float kCricketsLevel = 0.45f;
inline constexpr float kRainLevel = 0.6f;
inline constexpr float kWaterLevel = 0.4f;
inline constexpr float kWaterTilesForFullLevel = 24.0f;
inline constexpr float kSfxLevel = 0.8f;
inline constexpr float kUiSfxLevel = 0.35f;
inline constexpr float kLoopFadeSeconds = 2.5f;
inline constexpr float kMasterFadeSeconds = 0.05f;
inline constexpr float kLimiterCeiling = 0.89f; // about -1 dBFS
inline constexpr float kLimiterReleaseSeconds = 0.25f;
inline constexpr float kRainBirdsDuck = 0.3f;    // birds under rain
inline constexpr float kRainCricketsDuck = 0.5f; // crickets under rain
inline constexpr float kVoiceLevel = 0.48f;
// Music stems (docs/design/living-corner.md R8): 72 bpm in 4/4 at 44.1 kHz is 147 000 samples a
// bar; a newly unlocked stem fades in over this many bars from the next bar line.
inline constexpr int kMusicBarSamples = 147000;
inline constexpr int kStemFadeBars = 4;
// While a piece's melody is locked, its pad and keys are lifted (the opening is quieter).
inline constexpr float kDayMakeup = 1.259f;        // +2 dB
inline constexpr float kNightMakeup = 1.122f;      // +1 dB
inline constexpr float kSnowAmbienceBoost = 1.41f; // winter bed under snow, +3 dB

} // namespace lc::tuning
