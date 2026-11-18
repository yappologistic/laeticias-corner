#pragma once
// Tunable numbers of the world runtime, in one place (docs/design/world-tech.md §4.6, §2.5).

namespace lc::world::tuning {

// Theme sampling: a 9 x 9 grid of district samples at this spacing around the camera centre.
inline constexpr int kThemeSamplesPerSide = 9;
inline constexpr float kThemeSampleSpacing = 8.0f; // tiles
// Blend radius by region kind, in tiles: a sample at distance d adds smoothstep(1 - d / radius).
inline constexpr float kThemeRadiusCity = 32.0f;
inline constexpr float kThemeRadiusTown = 12.0f;
inline constexpr float kThemeRadiusStretch = 24.0f; // also the home region
inline constexpr float kThemeRadiusSeam = 16.0f;

// At most this many destination nodes per region get next-hop tables.
inline constexpr int kMaxDestsPerRegion = 64;

} // namespace lc::world::tuning
