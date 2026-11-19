#include "world/slopes.hpp"

#include <algorithm>
#include <cmath>

namespace lc::world {
namespace {

constexpr std::array<int, 4> kCornerCell{0, 2, 8, 6}; // N, E, S, W on the grid

constexpr SlopeGrid corner(int mask) {
    SlopeGrid h{};
    const auto low = [&](int bit) { return (mask & bit) != 0 ? -1.0f : 0.0f; };
    h[0] = low(kCornerN);
    h[2] = low(kCornerE);
    h[8] = low(kCornerS);
    h[6] = low(kCornerW);
    h[1] = (h[0] + h[2]) / 2;
    h[5] = (h[2] + h[8]) / 2;
    h[7] = (h[8] + h[6]) / 2;
    h[3] = (h[6] + h[0]) / 2;
    h[4] = (h[0] + h[2] + h[8] + h[6]) / 4;
    return h;
}

constexpr SlopeGrid peak(Slope s) {
    SlopeGrid h{};
    h.fill(-1.0f);
    h[4] = 0.0f;
    switch (s) {
    case Slope::RidgeX: h[3] = h[5] = 0.0f; break;
    case Slope::RidgeX0: h[3] = 0.0f; break;
    case Slope::RidgeX1: h[5] = 0.0f; break;
    case Slope::RidgeY: h[1] = h[7] = 0.0f; break;
    case Slope::RidgeY0: h[1] = 0.0f; break;
    case Slope::RidgeY1: h[7] = 0.0f; break;
    default: break;
    }
    return h;
}

constexpr std::array<SlopeGrid, kSlopeCount> kGrids = [] {
    std::array<SlopeGrid, kSlopeCount> g{};
    for (int m = 0; m < 15; ++m) g[static_cast<std::size_t>(m)] = corner(m);
    for (int s = 15; s < kSlopeCount; ++s) g[static_cast<std::size_t>(s)] = peak(Slope(s));
    return g;
}();

constexpr std::array<std::string_view, kSlopeCount> kKeys{
    "",        "c1",       "c2",       "c3",      "c4",       "c5",      "c6",  "c7",
    "c8",      "c9",       "c10",      "c11",     "c12",      "c13",     "c14", "knoll",
    "ridge_x", "ridge_x0", "ridge_x1", "ridge_y", "ridge_y0", "ridge_y1"};

} // namespace

const SlopeGrid& slopeGrid(Slope s) {
    return kGrids[std::min<std::size_t>(static_cast<std::size_t>(s), kSlopeCount - 1)];
}

float slopeHeight(Slope s, float u, float v) {
    if (s == Slope::Flat) return 0.0f;
    const SlopeGrid& h = slopeGrid(s);
    // From the centre: the major axis leads to an edge midpoint, the minor one on to the corner
    // beside it; that is the fan triangle holding the point, and its plane is linear in both.
    const float dx = std::clamp(u, 0.0f, 1.0f) * 2.0f - 1.0f;
    const float dy = std::clamp(v, 0.0f, 1.0f) * 2.0f - 1.0f;
    const float ax = std::abs(dx);
    const float ay = std::abs(dy);
    const int i = dx < 0 ? 0 : 2;
    const int j = dy < 0 ? 0 : 2;
    const float corner = h[static_cast<std::size_t>(j * 3 + i)];
    const float mid =
        ay >= ax ? h[static_cast<std::size_t>(j * 3 + 1)] : h[static_cast<std::size_t>(3 + i)];
    const float major = std::max(ax, ay);
    const float minor = std::min(ax, ay);
    return h[4] + major * (mid - h[4]) + minor * (corner - mid);
}

int slopeCorner(Slope s, int c) {
    return static_cast<int>(
        slopeGrid(s)[static_cast<std::size_t>(kCornerCell[static_cast<std::size_t>(c & 3)])]);
}

std::string_view slopeKey(Slope s) {
    return kKeys[std::min<std::size_t>(static_cast<std::size_t>(s), kSlopeCount - 1)];
}

int slopeRidgeAxis(int low, int lowerEdges) {
    if (low != 15) return 0;
    const int ys = lowerEdges & (kCornerN | kCornerS);
    const int xs = lowerEdges & (kCornerE | kCornerW);
    if (ys == (kCornerN | kCornerS) && xs == 0) return 1;
    if (xs == (kCornerE | kCornerW) && ys == 0) return 2;
    return 0;
}

Slope slopeOf(int low, int lowerEdges, bool ridgeBefore, bool ridgeAfter) {
    if (low <= 0) return Slope::Flat;
    if (low < 15) return Slope(low);
    const int axis = slopeRidgeAxis(low, lowerEdges);
    if (axis == 0 || !(ridgeBefore || ridgeAfter)) return Slope::Knoll;
    const int both = axis == 1 ? static_cast<int>(Slope::RidgeX) : static_cast<int>(Slope::RidgeY);
    return Slope(both + (ridgeBefore && ridgeAfter ? 0 : (ridgeBefore ? 1 : 2)));
}

} // namespace lc::world
