#include "worldview/terrain.hpp"

#include "core/rng.hpp"
#include "render/gpu/look.hpp"
#include "render/gpu/tuning.hpp"
#include "worldview/tuning.hpp"

#include <algorithm>
#include <cmath>

namespace lc::worldview {

EdgeFace edgeFace(int level, int aS, int aFar, int bS, int bFar) {
    // The neighbour is drawn after the face and covers what lies below its own edge, so bands
    // run from the tile's lower corner down to the neighbour's lowest one.
    if (bS >= aS && bFar >= aFar) return {};
    EdgeFace f;
    f.first = level - std::min(aS, aFar);
    f.last = std::max(f.first, level - std::min(bS, bFar));
    if (aS != aFar) f.wedge = aS > aFar ? 0 : 1;
    return f;
}

std::array<float, 8> slopeLight(world::Slope s, float levelUnits, const float* sun,
                                float strength) {
    const world::SlopeGrid& h = world::slopeGrid(s);
    const float* baked = gpu::kBakedSun;
    const auto light = [](const float* d, float nx, float ny, float nz) {
        const float dl = std::sqrt(d[0] * d[0] + d[1] * d[1] + d[2] * d[2]);
        return 0.42f + 0.58f * std::max(0.0f, (nx * d[0] + ny * d[1] + nz * d[2]) / dl);
    };
    const float flat = light(baked, 0, 0, 1);
    const float flatNow = sun != nullptr ? light(sun, 0, 0, 1) : flat;
    std::array<float, 8> out{};
    for (std::size_t t = 0; t < 8; ++t) {
        float p[3][3];
        for (int k = 0; k < 3; ++k) {
            const int g = world::kSlopeFan[t][static_cast<std::size_t>(k)];
            p[k][0] = static_cast<float>(g % 3) * 0.5f;
            p[k][1] = static_cast<float>(g / 3) * 0.5f;
            p[k][2] = h[static_cast<std::size_t>(g)] * levelUnits;
        }
        const float a[3] = {p[1][0] - p[0][0], p[1][1] - p[0][1], p[1][2] - p[0][2]};
        const float b[3] = {p[2][0] - p[0][0], p[2][1] - p[0][1], p[2][2] - p[0][2]};
        float n[3] = {a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2],
                      a[0] * b[1] - a[1] * b[0]};
        const float len = std::sqrt(n[0] * n[0] + n[1] * n[1] + n[2] * n[2]);
        if (len <= 0) {
            out[t] = 1;
            continue;
        }
        const float up = n[2] < 0 ? -1.0f : 1.0f;
        const float nx = n[0] * up / len;
        const float ny = n[1] * up / len;
        const float nz = n[2] * up / len;
        const float bakedRatio = light(baked, nx, ny, nz) / flat;
        out[t] = bakedRatio;
        if (sun != nullptr && strength > 0) {
            const float now = light(sun, nx, ny, nz) / flatNow;
            const float k = std::clamp(1.0f + (now / bakedRatio - 1.0f) * strength,
                                       1.0f / gpu::tuning::kRelightMax, gpu::tuning::kRelightLift);
            out[t] = bakedRatio * k;
        }
    }
    return out;
}

FallPart fallPart(int drop, int b) {
    if (drop <= 1) return FallPart::Rapid;
    if (b == 0) return FallPart::Top;
    return b >= drop - 1 ? FallPart::Foot : FallPart::Mid;
}

int overlayMask(const world::WorldMap& m, TilePos p, int t) {
    int mask = 0;
    // Waters are one water for each other's edges (sea, shallows and rivers meet without a rim of
    // sand between them: art-world.md); beyond the grid the sea runs on.
    const bool water = m.terrainInfo(t).water;
    const auto same = [&](int dx, int dy) {
        const TilePos n{p.x + dx, p.y + dy};
        if (!m.inBounds(n)) return water;
        const int nt = m.terrainAt(n);
        return nt == t || (water && nt != world::kNone && m.terrainInfo(nt).water);
    };
    if (same(0, -1)) mask |= kMaskN;
    if (same(1, 0)) mask |= kMaskE;
    if (same(0, 1)) mask |= kMaskS;
    if (same(-1, 0)) mask |= kMaskW;
    return mask;
}

int overlayMaskExcept(const world::WorldMap& m, TilePos p, int t, int except) {
    int mask = 0;
    const bool water = m.terrainInfo(t).water;
    const auto same = [&](int dx, int dy) {
        const TilePos n{p.x + dx, p.y + dy};
        if (!m.inBounds(n)) return false; // the deep sea beyond the grid
        const int nt = m.terrainAt(n);
        return nt == t ||
               (water && nt != world::kNone && nt != except && m.terrainInfo(nt).water);
    };
    if (same(0, -1)) mask |= kMaskN;
    if (same(1, 0)) mask |= kMaskE;
    if (same(0, 1)) mask |= kMaskS;
    if (same(-1, 0)) mask |= kMaskW;
    return mask;
}

bool flowingWater(std::string_view id) {
    return id.find("river") != std::string_view::npos ||
           id.find("channel") != std::string_view::npos ||
           id.find("stream") != std::string_view::npos ||
           id.find("canal") != std::string_view::npos;
}

int fallDrop(const world::WorldMap& m, const WaterKinds& w, TilePos p, int dir) {
    const int level = m.level(p);
    if (level == 0) return 0;
    const TilePos q{p.x + world::kSteps[static_cast<std::size_t>(dir)].x,
                    p.y + world::kSteps[static_cast<std::size_t>(dir)].y};
    if (!m.inBounds(q)) return level; // the sea beyond the grid
    const int qt = m.terrainAt(q);
    if (qt == world::kNone) return 0;
    if (m.terrainInfo(qt).water) return std::max(0, level - m.level(q));
    // Onto land: the neighbour's corners on the shared edge (+x, +y, -x, -y).
    static constexpr std::array<std::array<int, 2>, 4> kFar{{{0, 3}, {0, 1}, {1, 2}, {3, 2}}};
    const auto& fc = kFar[static_cast<std::size_t>(dir)];
    const int drop = level - std::min(m.cornerLevel(q, fc[0]), m.cornerLevel(q, fc[1]));
    if (drop <= 0) return 0;
    const auto t = static_cast<std::size_t>(m.terrainAt(p));
    const bool flows = w.channel[t] && world::auxOf(m.levelByte(p)) == ((dir + 1) & 3);
    return flows || !w.bank[t] ? drop : 0;
}

float groundMacro(Vec2 tile) {
    const auto octave = [&](float cell, std::uint32_t salt) {
        const float fx = tile.x / cell;
        const float fy = tile.y / cell;
        const int x0 = static_cast<int>(std::floor(fx));
        const int y0 = static_cast<int>(std::floor(fy));
        const float tx = fx - static_cast<float>(x0);
        const float ty = fy - static_cast<float>(y0);
        // Smoothstep weights: continuous with a continuous slope across lattice lines.
        const float sx = tx * tx * (3 - 2 * tx);
        const float sy = ty * ty * (3 - 2 * ty);
        const auto at = [&](int x, int y) {
            return static_cast<float>(tileHash(x, y, salt) % 1024u) / 1023.0f;
        };
        const float top = at(x0, y0) + (at(x0 + 1, y0) - at(x0, y0)) * sx;
        const float bottom = at(x0, y0 + 1) + (at(x0 + 1, y0 + 1) - at(x0, y0 + 1)) * sx;
        return top + (bottom - top) * sy;
    };
    return octave(tuning::kGroundMacroCells[0], 101) * 0.6f +
           octave(tuning::kGroundMacroCells[1], 211) * 0.4f;
}

} // namespace lc::worldview
