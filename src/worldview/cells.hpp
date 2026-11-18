#pragma once
// Cells: squares of world pixels the renderer caches as textures, and the pure maths and eviction
// policies behind the cell cache and the page streamer. A level-L cell spans 512 << L world px and
// is stored at 512 x 512 texels, so every level costs the same per cell: level 0 holds the ground
// at native resolution, levels 1 and 2 are impostors of everything static at half and quarter
// scale. Pure logic (no SDL).

#include "core/iso.hpp"
#include "worldview/tuning.hpp"

#include <cmath>
#include <cstddef>
#include <cstdint>
#include <span>
#include <vector>

namespace lc::worldview {

struct CellKey {
    int level = 0;
    int cx = 0; // cell column and row: floor(world px / cell px), negative west of x = 0
    int cy = 0;
    friend constexpr bool operator==(CellKey, CellKey) = default;
};

[[nodiscard]] constexpr int cellPx(int level) {
    return tuning::kCellTexels << level;
}
[[nodiscard]] constexpr std::uint64_t packCell(CellKey k) {
    // 2^20 cells either way of the origin per axis is far beyond the world (about 108 x 54).
    constexpr std::int64_t kBias = 1 << 20;
    return (static_cast<std::uint64_t>(k.level) << 42) |
           (static_cast<std::uint64_t>(k.cx + kBias) << 21) |
           static_cast<std::uint64_t>(k.cy + kBias);
}
[[nodiscard]] inline FRect cellRect(CellKey k) {
    const auto s = static_cast<float>(cellPx(k.level));
    return {static_cast<float>(k.cx) * s, static_cast<float>(k.cy) * s,
            static_cast<float>(k.cx + 1) * s, static_cast<float>(k.cy + 1) * s};
}

// Calls f(CellKey) for every level-`level` cell meeting `view`, row by row.
template <typename F>
void forEachCell(const FRect& view, int level, F&& f) {
    const auto s = static_cast<float>(cellPx(level));
    const int x0 = static_cast<int>(std::floor(view.x0 / s));
    const int y0 = static_cast<int>(std::floor(view.y0 / s));
    const int x1 = static_cast<int>(std::ceil(view.x1 / s));
    const int y1 = static_cast<int>(std::ceil(view.y1 / s));
    for (int cy = y0; cy < y1; ++cy)
        for (int cx = x0; cx < x1; ++cx) f(CellKey{level, cx, cy});
}

// The tile rectangle whose top vertices can fall inside `px` (world pixels), unclipped.
[[nodiscard]] TileRect tilesUnder(const FRect& px, Iso iso);

// How far drawn things reach from their tile's top vertex, world px (raise included).
struct Reach {
    float left = 0;
    float right = 0;
    float up = 0;   // above the top vertex
    float down = 0; // below it
};
// The world px rect whose tiles (or items anchored there) can draw into `px`.
[[nodiscard]] inline FRect grown(const FRect& px, const Reach& r) {
    // A sprite reaching up from its anchor is found by looking below the rect, and so on.
    return {px.x0 - r.right, px.y0 - r.down, px.x1 + r.left, px.y1 + r.up};
}

// Least-recently-used slot that was not used in `frame`, or -1 when every one was.
[[nodiscard]] int lruSlot(std::span<const std::uint64_t> lastUsed, std::uint64_t frame);

// Atlas page residency for eviction decisions.
struct PageUse {
    std::size_t bytes = 0;
    double lastUsed = 0; // seconds
    bool resident = false;
    bool wanted = false; // needed by the view this frame
};
// Pages to evict, oldest first, until the resident bytes fit `budget`: only resident pages not
// wanted now and idle at least `idle` seconds (world-tech §4.5).
[[nodiscard]] std::vector<int> pagesToEvict(std::span<const PageUse> pages, double now, double idle,
                                            std::size_t budget);

} // namespace lc::worldview
