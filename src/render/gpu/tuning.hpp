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
inline constexpr float kNightTint[3] = {0.80f, 0.97f, 1.50f};
inline constexpr float kNightCool = 0.55f;
// Exposure at deep night against the regions' own night grade, which leaves the bright city art
// above the bar's night key (median 22-45; the owner's recommendation 28-38).
inline constexpr float kNightExposure = 0.62f;
// The night shift starts past dusk: from the clock's night at this value to full at 1.
inline constexpr float kNightFrom = 0.5f;
// The key by day against the regions' exposure (none at dusk and night, by the clock's glow):
// the art is drawn for the bright classic frame (day median 140+ in the cities against the
// bar's 95-125).
inline constexpr float kKey = 0.9f;
// Shade takes the sky's colour (the regions' `theme.look.shade`) by the shadow layer's coverage
// times this: shade is the sky's colour, not grey (quality bar §4.1, graphics plan §1.2).
inline constexpr float kShadeTint = 1.0f;

// Light pools (world_lights.hpp): falloff strength * (1 - (d/R)^2)^2, as the worldgen
// measuring assumes (out/reports/world-nights.md §1).
inline constexpr float kPoolGain = 1.35f;  // albedo * light added
inline constexpr float kPoolWarm = 0.22f;  // plus this much of the light by the pixel's luma
inline constexpr float kPoolDay = 0.12f;   // share of a pool still seen at full day
inline constexpr float kPoolRise = 0.9f;   // walls above a light lit to this share of its height
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
