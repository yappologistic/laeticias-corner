#pragma once
// Sloped ground (out/reports/art-smooth-land.md §3, the slope contract): a tile whose surface
// falls one level toward some of its corners instead of standing on a vertical face. A shape is
// nine heights on a 3 x 3 grid over the tile (corners, edge midpoints, centre) in levels relative
// to the tile's level (0 or -1), cut into eight triangles fanned round the centre; the renderer
// draws that mesh and walkers stand on it, so what is drawn is what is walked.

#include <array>
#include <cstdint>
#include <string_view>

namespace lc::world {

// Corners as the contract numbers them: the diamond's top (u, v = 0, 0), right (1, 0), bottom
// (1, 1) and left (0, 1) vertex; u runs along +x, v along +y.
inline constexpr int kCornerN = 1;
inline constexpr int kCornerE = 2;
inline constexpr int kCornerS = 4;
inline constexpr int kCornerW = 8;

// Flat, the corner shapes c1..c14 (the value is the mask of low corners), and the shapes with
// every corner low: a knoll (only the centre stays up) and ridges along x or y whose line stays
// up through the edge midpoints it continues through (`0`: only toward u (or v) = 0, `1`: only
// toward 1).
enum class Slope : std::uint8_t {
    Flat = 0,
    Knoll = 15,
    RidgeX,
    RidgeX0,
    RidgeX1,
    RidgeY,
    RidgeY0,
    RidgeY1,
};
inline constexpr int kSlopeCount = 22; // Flat and the 21 shapes of the contract

// Heights of the 3 x 3 grid, index j * 3 + i at (u, v) = (i / 2, j / 2), in levels (<= 0).
using SlopeGrid = std::array<float, 9>;
[[nodiscard]] const SlopeGrid& slopeGrid(Slope s);
// The fan: eight triangles of grid indices, every one touching the centre (4).
inline constexpr std::array<std::array<int, 3>, 8> kSlopeFan{
    {{0, 1, 4}, {1, 2, 4}, {2, 5, 4}, {5, 8, 4}, {8, 7, 4}, {7, 6, 4}, {6, 3, 4}, {3, 0, 4}}};
// Surface height in levels relative to the tile's at tile point (u, v), each in [0, 1]: the
// height inside the fan triangle that holds the point (continuous across the tile, and across
// tile edges where neighbouring shapes meet, which the corner rule guarantees).
[[nodiscard]] float slopeHeight(Slope s, float u, float v);
// Height of corner `c` (0 N, 1 E, 2 S, 3 W) in levels relative to the tile's: 0 or -1.
[[nodiscard]] int slopeCorner(Slope s, int c);
// The atlas key segment: "c5", "knoll", "ridge_x0"; empty for Flat.
[[nodiscard]] std::string_view slopeKey(Slope s);

// The axis a tile with every corner low ridges along: 1 x when only its -y and +y neighbours
// are lower, 2 y when only -x and +x are, else 0. `lowerEdges` holds the edge neighbours that
// stand lower as N 1 (-y), E 2 (+x), S 4 (+y), W 8 (-x).
[[nodiscard]] int slopeRidgeAxis(int low, int lowerEdges);
// The shape for low corners `low`, lower edge neighbours and, for a ridge, whether the
// neighbours before and after it along its axis (-x and +x, or -y and +y) ridge the same way at
// the same level.
[[nodiscard]] Slope slopeOf(int low, int lowerEdges, bool ridgeBefore, bool ridgeAfter);

} // namespace lc::world
