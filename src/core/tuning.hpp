#pragma once
// Every tunable number of the simulation and presentation lives here.

#include <cstddef>

namespace lc::tuning {

// Simulation
inline constexpr double kStepSeconds = 1.0 / 60.0;
inline constexpr int kMaxStepsPerFrame = 5;
inline constexpr std::size_t kUndoSteps = 200;
inline constexpr double kAutosaveDelay = 1.5; // seconds after the last change

// Clock: fractions of one full cycle.
inline constexpr double kDayLengthSeconds = 12.0 * 60.0;
inline constexpr double kDuskStart = 0.50;
inline constexpr double kNightStart = 0.625;
inline constexpr double kDawnStart = 0.875;
inline constexpr double kPinEaseSeconds = 1.6; // time to glide to a pinned phase

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
    {0.56, {0.98f, 0.74f, 0.62f}, {0.36f, 0.35f, 0.56f}, {0.96f, 0.66f, 0.50f}, 0.65f, 0.45f},
    {0.66, {0.40f, 0.46f, 0.72f}, {0.07f, 0.09f, 0.20f}, {0.17f, 0.20f, 0.36f}, 1.0f, 1.0f},
    {0.84, {0.40f, 0.46f, 0.72f}, {0.07f, 0.09f, 0.20f}, {0.17f, 0.20f, 0.36f}, 1.0f, 1.0f},
    {0.94, {0.88f, 0.78f, 0.84f}, {0.47f, 0.52f, 0.72f}, {0.96f, 0.80f, 0.72f}, 0.35f, 0.3f},
};
inline constexpr float kRainSkyGrey = 0.45f; // blend of sky toward grey while raining

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

// Camera
inline constexpr int kMinZoom = 1;
inline constexpr int kMaxZoom = 6;
inline constexpr float kCameraEase = 12.0f;   // 1/s exponential approach
inline constexpr float kKeyPanSpeed = 360.0f; // screen px per second
inline constexpr float kCameraMargin = 48.0f; // world px allowed beyond the island

// Presentation
inline constexpr float kPopSeconds = 0.32f;
inline constexpr float kFadeOutSeconds = 0.22f;
inline constexpr float kGhostAlpha = 0.72f;
inline constexpr float kPaintSoundGap = 0.07f;
inline constexpr float kSmokeInterval = 0.45f;
inline constexpr float kRipplesPerSecondPerWaterTile = 0.035f;
inline constexpr float kRainRipplesPerSecondPerWaterTile = 0.6f;
inline constexpr float kRainDropsPerSecond = 520.0f; // per 640x360 world px of view
inline constexpr float kLeavesPerSecondPerTree = 0.012f;
inline constexpr float kPitchJitter = 0.06f;
inline constexpr float kRainAmbientDim = 0.85f;

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

} // namespace lc::tuning
