#pragma once
// Every tunable number of the simulation and presentation lives here.

#include <cstddef>
#include <cstdint>

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
inline constexpr double kPinEaseSeconds = 1.6;     // time to glide to a pinned phase
inline constexpr double kMidnight = 0.75;          // a new calendar day begins here
inline constexpr int kMaxCalendarDay = 1'000'000;  // saves cannot push the calendar past this
inline constexpr int kMaxHarvests = 1'000'000'000; // nor the harvest count
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
inline constexpr double kConditionBudgetMs = 1.0; // every condition at once, on a full map
// The actor update's share of the frame (living-world.md §7.5): a busy corner at its caps, and
// a crowd of kBenchCrowd actors at about a microsecond each.
inline constexpr double kSimBudgetMs = 0.6;   // actors, events, weather and conditions, on average
inline constexpr double kCrowdBudgetMs = 0.4; // the crowd's actors alone
inline constexpr double kFrameP99Ms = 8.3;    // CLAUDE.md "Performance": 99th percentile frame
inline constexpr double kFrameWorstMs = 16.6;
inline constexpr double kCpuBudgetMs = 2.0;   // update + draw submission on the CPU, on average
inline constexpr double kSoakGrowthMiB = 4.0; // memory a long session may add after warming up
// The process's resident memory may not pass this in the bench at 1080p, nor the soak at its size.
// It covers the atlas, the four world targets and the blur chain at that size, the ground cache's
// budget and the code and drivers around them; see out/reports/engine-frontdoor.md for the sums.
inline constexpr double kBenchMemoryMiB = 512.0;
inline constexpr long long kSoakDrawEvery = 120; // steps between frames drawn during a soak
inline constexpr int kBenchCrowd = 400;
// Rare visitors: the recipe holds this long before one comes; a visit lasts, then it stays away.
inline constexpr float kRareDelayMin = 20.0f;
inline constexpr float kRareDelayMax = 60.0f;
inline constexpr float kRareStayMin = 180.0f;
inline constexpr float kRareStayMax = 360.0f;
inline constexpr float kRareAwayMin = 120.0f;
inline constexpr float kRareAwayMax = 240.0f;
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
inline constexpr float kRainGrowth = 2.0f;        // beds grow this much faster in rain
inline constexpr float kWaterBoost = 0.25f;       // of a stage, her morning watering gives
inline constexpr double kRipeLineDelay = 30.0;    // a bed ripe this long unpicked: she says so
inline constexpr double kGrowthTick = 0.5;        // seconds between growth updates
inline constexpr float kProduceRise = 1.4f;       // tile heights per second
inline constexpr float kProduceSeconds = 1.2f;

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

// Actors (docs/design/living-world.md §2, living-corner.md R2 and R6)
inline constexpr std::size_t kActorPool = 512;    // records; the home region needs a few dozen
inline constexpr std::uint32_t kThinkBuckets = 4; // actors check the world in turn, one in four
inline constexpr float kPathCostPaved = 1.0f;     // paths, cobbles and crossings
inline constexpr float kPathCostOther = 1.6f;
inline constexpr int kPathMaxNodes = 4096;        // nodes one search may expand
inline constexpr int kPathSearchesPerStep = 8;    // more wait for the next step
inline constexpr float kResidentSpeedPath = 1.1f; // tiles per second on paths
inline constexpr float kResidentSpeedOther = 0.9f;
inline constexpr float kNookPreferWeight = 4.0f;
inline constexpr float kShoreMargin = 0.3f;   // swimmers keep this far (tiles) from the bank
inline constexpr int kBankSearch = 6;         // tiles around a swimmer it looks for a bank
inline constexpr float kStrollRadius = 6.0f;  // a stroll with nothing of note goes this far
inline constexpr float kNewItemWeight = 3.0f; // strolls favour what was placed lately
inline constexpr double kNewItemSeconds = 600.0;
inline constexpr float kPotterRadius = 2.0f; // pottering about between routines
inline constexpr int kHandsMax = 3;          // goods units carried at once
inline constexpr float kHatReach = 4.0f;     // a butterfly finds her hat within this
inline constexpr float kCallRadius = 6.0f;   // hens come to feed from this far
inline constexpr float kHenPeckSeconds = 6.0f;
inline constexpr float kLineSpacing = 0.7f;   // ducks in a line, tiles apart
inline constexpr float kFollowSpacing = 1.0f; // following her, a tile behind
inline constexpr float kReactRadius = 8.0f;   // she turns to placements this close
inline constexpr float kStartleSeconds = 0.6f;
inline constexpr float kStartleCooldown = 5.0f;
inline constexpr float kStartleSpeed = 2.5f;
inline constexpr float kStartleMin = 2.0f; // tiles it flees
inline constexpr float kStartleMax = 3.0f;
inline constexpr float kPetSeconds = 1.5f;
inline constexpr float kPetCooldown = 4.0f;
inline constexpr float kPetHitInflate = 4.0f; // px at 1x around a critter's frame
inline constexpr float kClickCooldown = 8.0f; // between her answers to a click
inline constexpr float kHarvestReach = 12.0f; // she takes the harvest home from this far
inline constexpr float kHarvestPeckReach = 5.0f;
inline constexpr float kNookVisitReach = 15.0f; // she walks over to a new nook from this far
inline constexpr float kVisitLinger = 2.5f;
inline constexpr float kSketchVisitor = 15.0f; // she sketches a new visitor this long
inline constexpr float kCallSeconds = 1.0f;    // a call animation
inline constexpr float kWaveSeconds = 1.6f;    // her wave hello
inline constexpr float kWatchReach = 3.0f;     // the cat watches the pointer this close
inline constexpr int kDisplaceReach = 3;       // she steps aside this far
// Her speech (living-corner.md R6.6): shown 2.5 s plus a little per character, fading in and
// out; ordinary lines leave a gap after the last; idle chatter comes every minute or two.
inline constexpr double kBubbleBase = 2.5;
inline constexpr double kBubblePerChar = 0.05;
inline constexpr double kBubbleFade = 0.2;
inline constexpr double kBubbleGap = 4.0;
inline constexpr float kIdleLineMin = 60.0f;
inline constexpr float kIdleLineMax = 120.0f;
inline constexpr float kFirstSightReach = 12.0f; // she remarks on a first visitor this close

// Events (living-world.md §5): scheduled starts keep this far apart; a deferred one retries.
inline constexpr double kEventSpacing = 20.0;
inline constexpr double kEventRetry = 5.0;

// Weather and wind (living-world.md §6)
inline constexpr int kWetBlock = 8; // tiles per side of a wetness block
inline constexpr std::size_t kMaxWeatherCells = 6;
inline constexpr float kRainCellMin = 6.0f; // radius in tiles
inline constexpr float kRainCellMax = 14.0f;
inline constexpr float kCloudCellMin = 8.0f;
inline constexpr float kCloudCellMax = 20.0f;
inline constexpr float kCellMinSpeed = 0.12f;   // tiles per second
inline constexpr float kCellWindSpeed = 0.35f;  // added at full wind
inline constexpr float kWeatherPeriod = 120.0f; // seconds between weather decisions
inline constexpr float kWindAngle = 0.4f;       // radians from +x in tile space
inline constexpr float kGustSpeed = 18.0f;      // tiles per second a gust wave travels
inline constexpr float kGustWidth = 4.0f;       // tiles
inline constexpr float kRainThreshold = 0.3f;   // rain this strong counts as raining
inline constexpr float kWetRise = 0.02f;        // per second under full rain
inline constexpr float kWetDry = 0.005f;

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
inline constexpr float kPetalFloatSeconds = 6.0f; // a petal on water floats this long
inline constexpr float kPetalDrift = 0.08f;       // tile heights per second
inline constexpr float kSnowSpeed = 1.2f;         // tile heights per second
inline constexpr float kSnowShare = 0.35f;        // snowflakes per raindrop the view would have
inline constexpr float kLeafFall = 0.56f;
inline constexpr float kLeafSway = 0.375f;
inline constexpr float kSparkleSpread = 0.6f;
inline constexpr float kSparkleRise = 0.4f;
inline constexpr float kWakeInterval = 0.9f; // seconds between ripples behind a swimming critter
inline constexpr float kSwayCalm = 0.6f;     // sway clock speed with no wind
inline constexpr float kSwayWind = 1.2f;     // added at full wind
inline constexpr float kGustSway = 2.0f;     // sway runs this much faster as a gust passes
inline constexpr float kGustLeaves = 8.0f;   // and trees drop this many times more leaves
inline constexpr float kRustleSeconds = 0.6f;
inline constexpr float kRustleFps = 8.0f;
inline constexpr float kSmokeLean = 0.5f; // how far the wind pushes smoke, leaves and rain
inline constexpr float kLeafLean = 0.4f;
inline constexpr float kRainLean = 0.25f;
inline constexpr float kMistDrop = 1.6f; // tile heights below a rim tile's top: a fall's foot
inline constexpr float kMistPerSecond = 0.7f;
inline constexpr float kMistSeconds = 1.8f;
inline constexpr float kZzzInterval = 3.0f;
inline constexpr float kHeartSeconds = 1.2f;
inline constexpr float kFishJumpSeconds = 1.0f;
inline constexpr float kMothRadius = 10.0f / 64.0f; // tile widths
inline constexpr float kMothLit = 0.7f;
inline constexpr float kStarSeconds = 1.0f;
inline constexpr float kStarTravel = 0.35f; // share of the window width a shooting star crosses
inline constexpr float kRainbowScale = 2.0f;
inline constexpr float kRainbowDrop = 0.15f;    // its feet, from the island's top toward its middle
inline constexpr float kCloudShadowSize = 1.4f; // blob width per tile of cell radius
inline constexpr float kCloudShadow = 0.3f;
inline constexpr float kRainShadow = 1.0f;
inline constexpr float kWetDarken = 0.16f;
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
inline constexpr float kUnderwaterAlpha = 0.6f; // swimmers below the surface (the koi)
inline constexpr float kUnderwaterTint[3] = {0.72f, 0.86f, 1.0f};
inline constexpr float kWarmLight[3] = {1.0f, 0.78f, 0.48f};   // lamp, fire and window pools
inline constexpr float kFireflyHalo[3] = {0.75f, 1.0f, 0.55f}; // light around a firefly
inline constexpr float kFireflyCore[3] = {0.8f, 1.0f, 0.5f};   // its glowing body
inline constexpr float kInvalidTint[3] = {1.0f, 0.45f, 0.42f}; // refused ghosts, removal mark
inline constexpr float kCritterMoveFps = 6.0f;
inline constexpr float kCritterIdleFps = 2.0f;
inline constexpr float kCritterActFps = 5.0f;  // actions of three frames or more
inline constexpr float kCritterSlowFps = 1.5f; // two-frame loops: breathing, a page turn
inline constexpr float kWarnSeconds = 1.6f;    // how long a refusal stays in the hint line
inline constexpr float kClickSlop = 4.0f;      // window px a click may move and still be a click

inline constexpr int kCameraOpenMargin = 6; // tiles of wild land the camera may look over

inline constexpr int kHiddenWaitMs = 250; // a hidden window sleeps on events this long at most

// The first-minute tour (R10.5)
inline constexpr float kTourLookSeconds = 6.0f;
inline constexpr float kTourKeysSeconds = 5.0f;
inline constexpr float kTourEndSeconds = 4.0f;

inline constexpr float kReduceMotionParticles = 0.3f; // particles kept with reduce motion

// Builder comforts (docs/design/living-corner.md R11)
inline constexpr float kGridAlphaDay = 0.14f;
inline constexpr float kGridAlphaNight = 0.10f;
inline constexpr float kFootprintAlpha = 0.3f; // hold Tab: every item's footprint
inline constexpr int kBrushSizes[] = {1, 3, 5};
inline constexpr int kLineNotes = 5; // notes a placed line plays, one after another

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
inline constexpr float kWaterfallLevel = 0.5f;
inline constexpr float kFallTilesForFullLevel = 6.0f;
inline constexpr float kBedPan = 0.6f;         // a positional bed leans at most this far
inline constexpr float kPanLimit = 0.8f;       // nothing sits in one ear
inline constexpr float kPositionalNear = 6.0f; // tiles from the view centre at full gain
inline constexpr float kPositionalLevel = 0.9f;
inline constexpr std::size_t kMaxPositional = 12; // one-shots at once
inline constexpr double kMergeSeconds = 0.08;     // the same sound this close plays once
inline constexpr double kVoiceBusy = 0.6;         // a one-shot counts against the budget this long
inline constexpr float kRainbowSeconds = 48.0f;
inline constexpr float kRainbowIn = 3.0f;
inline constexpr float kRainbowOut = 5.0f;
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
// Tuned placement notes: about 8 dB under the placement sounds, a phrase restarts after a pause,
// quick drags skip notes closer together than this.
inline constexpr float kNoteLevel = 0.4f;
inline constexpr double kNotePhraseReset = 2.0;
inline constexpr double kNoteMinGap = 0.09;
inline constexpr float kNoteTurnChance = 0.2f;
inline constexpr int kPaintNoteEvery = 6; // tiles painted between notes in a stroke
// While a piece's melody is locked, its pad and keys are lifted (the opening is quieter).
inline constexpr float kDayMakeup = 1.259f;        // +2 dB
inline constexpr float kNightMakeup = 1.122f;      // +1 dB
inline constexpr float kSnowAmbienceBoost = 1.41f; // winter bed under snow, +3 dB

} // namespace lc::tuning
