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

// Bloom: halvings of the glow layer by tier (Low, Medium, High), and its strength.
inline constexpr int kBloomLevelsLow = 3;
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
inline constexpr float kDaySaturation = 0.12f;
inline constexpr float kDayWarm[3] = {0.14f, 0.06f, -0.10f};
inline constexpr float kTwilightWarm = 0.08f; // dawn and dusk: red up, blue down by this
inline constexpr float kNightAdapt[2] = {0.45f, 2.0f};
inline constexpr int kMeanSide = 64; // the scene is first sampled to this many texels across
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
inline constexpr float kPoolRise = 0.7f;
inline constexpr float kLightHeadroom = 0.4f; // pools are stored at this share (8-bit target:
                                              // overlapping flames must not clip to white)
inline constexpr float kPoolWall = 0.5f;
inline constexpr float kMapLightFull = 4.0f; // a map chunk this bright in lights: the fullest point
inline constexpr float kCarriedHeight = 20;  // world px from the feet to a carried flame
inline constexpr float kCarriedFlame =
    2.5f; // world px radius of the flame's point // the pool's upper half (walls behind) at this
          // strength // walls above a light lit to this share of its height
inline constexpr int kPoolLevels = 6;      // a pool's light in this many dithered bands
inline constexpr int kPoolTexture = 64;    // the falloff texture's side
inline constexpr float kFarLightPx = 2.5f; // window px radius of a light seen from afar, at least
inline constexpr float kFarLightWorld = 9; // ... or this many world px
inline constexpr float kWindowFadeHours = 0.2f; // lights come on and go out over this long
inline constexpr float kStaggerHours = 1.5f;    // windows and doors light one by one over this
inline constexpr float kDuskHour = 19.0f;       // `dusk` and `dawn` in the lights' hours (the
inline constexpr float kDawnHour = 5.5f;        // measuring's; the clock has no day length yet)
inline constexpr float kRainDim = 0.6f;         // `rain: dim`
inline constexpr float kRainOut = 0.15f;        // rain at or above this puts `rain: out` lights out

} // namespace lc::gpu::tuning
