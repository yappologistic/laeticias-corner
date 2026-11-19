#pragma once
// The shader path's tunable numbers (src/render/gpu/README.md), in one place.

namespace lc::gpu::tuning {

// Wind sway (look.hpp windLean): every swaying thing leans in one wind.
inline constexpr float kSwayRate = 1.7f;       // radians per second of the steady rocking
inline constexpr float kGustSpacing = 0.0016f; // gust crests per world px downwind
inline constexpr float kGustRate = 0.22f;      // crests passing a point per second
inline constexpr float kGustGain = 1.6f;       // a crest's lean over the steady sway
inline constexpr int kSwayStrips = 4;          // a swaying sprite is bent in this many strips
// Lean at the top of the sprite in a full wind, art px, by kind.
inline constexpr float kSwayTree = 4.0f;
inline constexpr float kSwayReeds = 4.5f;
inline constexpr float kSwayCloth = 5.0f; // banners, awnings, flags, sails at rest
inline constexpr float kSwayCrop = 3.0f;
inline constexpr float kSwayBush = 2.0f;
inline constexpr float kWindFloor = 0.35f; // the stillest air still stirs a little

// The sun (look.hpp sunAt): half the daylight in hours and the noon height (radians) by season
// (spring, summer, autumn, winter); the lowest sun light and shadows take; the height by which
// its light has come in.
inline constexpr float kSunHalfDay[4] = {6.0f, 7.0f, 6.0f, 5.0f};
inline constexpr float kSunNoon[4] = {0.96f, 1.18f, 0.90f, 0.62f};
inline constexpr float kSunLowest = 0.14f; // about 8 degrees
inline constexpr float kSunFade = 0.10f;
// Relight (packed.frag): the sun's steps through the day (cached cells are drawn again at
// each), and how far a ramp may be stepped from its baked light either way.
inline constexpr int kSunSteps = 48;
inline constexpr float kRelightMax = 1.8f;      // shade: light down to 1 / this
inline constexpr float kRelightLift = 1.3f;     // sun: light up to this
inline constexpr float kRelightExponent = 0.8f; // light ratio to Oklab lightness (perceived)
inline constexpr float kContact = 0.18f;        // the feet of walls this much darker
// Turning shadows: a shadow's far share fades to this alpha (soft far edge); a shadow at most
// this many times the baked one's length.
inline constexpr float kShadowFarAlpha = 0.45f;
inline constexpr float kShadowLongest = 3.0f;

// Bloom: halvings of the glow layer by tier (Low has none: the glow layer alone), and its
// strength.
inline constexpr int kBloomLevelsMedium = 3;
inline constexpr int kBloomLevelsHigh = 5;
inline constexpr float kBloomGain = 0.85f;    // halo added, times the clock's glow
inline constexpr float kBloomFloor = 0.25f;   // share of the halo kept by day
inline constexpr float kGlowCore = 1.0f;      // the glow layer itself, added sharp
inline constexpr float kBloomUpWeight = 0.9f; // each finer level adds this much of the coarser

// Night: low light shifts toward cool blue at its own luma (the eye's rods), keeping the
// value structure; this share at deep night (the regions' night grade alone leaves warm earth
// brown).
inline constexpr float kNightTint[3] = {0.84f, 0.97f, 1.36f};
inline constexpr float kNightCool = 0.55f;
// The exposure follows the scene (its mean luma after the regions' white balance and exposure,
// averaged on the GPU, no readback) toward a key by the hour: the art is drawn for the bright
// classic frame (city days median 140+ against the bar's 95-125), and the regions' night grade
// leaves bright stone above the bar's night key and gardens near black. Keys by day, at dawn and
// dusk (the clock's glow) and at night (bar: median 22-45, the owner's recommendation 28-38),
// with the range the exposure may move in by day and by night.
inline constexpr float kDayKey = 0.44f;
inline constexpr float kTwilightKey = 0.34f;
inline constexpr float kNightKey = 0.20f;
inline constexpr float kDayAdapt[2] = {1.0f, 1.12f};
inline constexpr float kTwilightAdaptMin = 0.8f; // dawn and dusk may be held down toward their key
// Haze at the native zooms by day, as a share of the region's: near, the air is clear (the
// cities' pale stone went grey under a full share); it rises with distance, zoom and twilight.
inline constexpr float kNearDayHaze = 0.3f;
// By day lit surfaces keep at least the art's saturation plus this, and their highlights lean
// warm by this much (added to the region's high tint before its amount).
inline constexpr float kDaySaturation = 0.06f;
// ... and no pixel's saturation grows by day past this many times its own (plus 0.02): richer,
// never garish (the Agora's dry earth went orange under the region's strong contrast).
inline constexpr float kDaySaturationGrowth = 1.08f;
inline constexpr float kDayWarm[3] = {0.10f, 0.04f, -0.06f};
inline constexpr float kTwilightWarm = 0.08f; // dawn and dusk: red up, blue down by this
inline constexpr float kNightAdapt[2] = {
    0.8f, 1.3f};                     // narrow: the place and hour set night, not the frame
inline constexpr int kMeanSide = 64; // the scene is first sampled to this many texels across
// The exposure follows the scene's mean this share of the way a frame (about half a second to
// settle at 60 frames a second; a jump takes it at once).
inline constexpr float kExposureFollow = 0.06f;

// Water: the tile water field's side (tiles round the view, one texel each); the colours come
// from the region's body colour: deeper and richer offshore, turquoise in the shallows, rivers
// greener and a little turbid, winter seas greyer; bands by tier, the sky's share by day and at
// dawn, dusk and night, glints by day; channels (rivers, canals) clear and without foam.
inline constexpr int kWaterField = 512;
inline constexpr float kShallowTint[3] = {0.22f, 0.78f, 0.74f}; // the shallows lean to this
inline constexpr float kShallowShare = 0.45f;
inline constexpr float kRiverTint[3] = {0.26f, 0.56f, 0.38f}; // rivers lean to this
inline constexpr float kRiverShare = 0.50f;
inline constexpr float kDeepValue = 0.86f; // offshore: the body's value times this ...
inline constexpr float kDeepChroma = 1.4f; // ... and its chroma times this
inline constexpr float kSeasonGrey[4] = {0.0f, 0.0f, 0.15f, 0.40f}; // spring .. winter
inline constexpr float kWaterBandsLow = 3;
inline constexpr float kWaterBandsHigh = 4;
inline constexpr float kSkyInWater[2] = {0.12f, 0.6f}; // by day, at dawn, dusk and night
inline constexpr float kGlints = 0.9f;
inline constexpr float kMoonGlints = 0.6f;
inline constexpr float kRiverSpeed = 0.55f; // tiles per second along a river's flow

// Clouds: cumulus over the world's weather cells (a few per cell, a few sizes), drawn at a
// quarter of the resolution and read on a grid of two art pixels; seen faint near (the world
// stays visible) and fuller far; their shadows on the ground are the stronger cue.
inline constexpr int kClouds = 32;
inline constexpr int kCloudBillows = 5;             // round billows on a cloud's base
inline constexpr float kCloudWidth[2] = {320, 820}; // px, the smallest and largest at full growth
inline constexpr float kCloudAltitude = 520;        // px a cloud's base stands above its point
inline constexpr float kCloudParallax = 0.12f;      // share of its offset from the view's centre
inline constexpr float kCloudShadow = 0.26f;        // a cloud's shadow takes this of the sunlight
inline constexpr float kDeckAlpha[4] = {0.35f, 0.72f, 0.85f,
                                        0.9f}; // native, half, quarter, overview
// The night shift starts past dusk: from the clock's night at this value to full at 1.
inline constexpr float kNightFrom = 0.5f;
// Shade takes the sky's colour (the regions' `theme.look.shade`) by the shadow layer's coverage
// times this: shade is the sky's colour, not grey (quality bar §4.1, graphics plan §1.2).
inline constexpr float kShadeTint = 0.8f;

// Light pools (world_lights.hpp): falloff strength * (1 - (d/R)^2)^2, as the worldgen
// measuring assumes (out/reports/world-nights.md §1).
inline constexpr float kPoolGain = 0.35f; // albedo * light added
inline constexpr float kPoolWarm = 0.85f; // plus this much of the light by the pixel's luma
inline constexpr float kPoolDay = 0.12f;  // share of a pool still seen at full day
inline constexpr float kPoolRise = 0.7f;  // walls above a light lit to this share of its height
// The lamps' light colour (their flames are 1700-2600 K, close enough to one warm hue that the
// pools share it: they live in one alpha channel of the glow target).
inline constexpr float kLampColour[3] = {1.0f, 0.58f, 0.28f};
// The pool list of the visible chunks is rebuilt when the view crosses a chunk, the hour moves
// on by this much, or after this many frames (rain at the lights); flicker is applied per frame.
inline constexpr float kPoolHourStep = 0.02f;
inline constexpr int kPoolRefreshFrames = 30;
inline constexpr float kLightHeadroom = 0.4f; // pools are stored at this share (8-bit target:
                                              // overlapping flames must not clip to white)
inline constexpr float kPoolWall = 0.5f; // the pool's upper half (walls behind) at this strength
inline constexpr float kMapLightFull = 4.0f; // a map chunk this bright in lights: the fullest point
inline constexpr float kCarriedHeight = 20;  // world px from the feet to a carried flame
inline constexpr float kCarriedFlame = 2.5f; // world px radius of the flame's point
inline constexpr int kPoolLevels = 6;        // a pool's light in this many dithered bands
inline constexpr int kPoolTexture = 64;      // the falloff texture's side
inline constexpr float kFarLightPx = 2.5f;   // window px radius of a light seen from afar, at least
inline constexpr float kFarLightWorld = 9;   // ... or this many world px
inline constexpr float kWindowFadeHours = 0.2f; // lights come on and go out over this long
inline constexpr float kStaggerHours = 1.5f;    // windows and doors light one by one over this
inline constexpr float kDuskHour = 19.0f;       // `dusk` and `dawn` in the lights' hours (the
inline constexpr float kDawnHour = 5.5f;        // measuring's; the clock has no day length yet)
inline constexpr float kRainDim = 0.6f;         // `rain: dim`
inline constexpr float kRainOut = 0.15f;        // rain at or above this puts `rain: out` lights out

} // namespace lc::gpu::tuning
