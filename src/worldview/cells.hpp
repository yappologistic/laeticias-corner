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
    int frame = 0; // which step of its animation it shows (0 for a still cell)
    friend constexpr bool operator==(CellKey, CellKey) = default;
};

// A coarse cell with water in it is kept in layers: its ground once per step of the water's
// loop (frames 0, 1, ...) and everything that stands on it once, under this frame number, laid
// over whichever step of the ground is shown. So the sea moves at half and quarter scale, and a
// step costs a ground to draw, not the city on it.
inline constexpr int kObjectsFrame = 15;
[[nodiscard]] constexpr CellKey objectsKey(CellKey k) {
    return {k.level, k.cx, k.cy, kObjectsFrame};
}

[[nodiscard]] constexpr int cellPx(int level) {
    return tuning::kCellTexels << level;
}
[[nodiscard]] constexpr std::uint64_t packCell(CellKey k) {
    // 2^20 cells either way of the origin per axis is far beyond the world (about 108 x 54).
    constexpr std::int64_t kBias = 1 << 20;
    return (static_cast<std::uint64_t>(k.frame) << 46) |
           (static_cast<std::uint64_t>(k.level) << 42) |
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

// Least-recently-used slot that was not used in `frame`, or -1 when every one was. `spare`:
// slots used within that many frames before `frame` are kept too (work done ahead of need must
// not push out what the last frames showed).
[[nodiscard]] int lruSlot(std::span<const std::uint64_t> lastUsed, std::uint64_t frame,
                          std::uint64_t spare = 0);

// The world px a view shows after the scale changes from `scale` to `to` about `anchor` (a
// point that keeps its place on screen, as the pointer does when the wheel zooms).
[[nodiscard]] constexpr FRect zoomedAbout(const FRect& view, Vec2 anchor, float scale, float to) {
    const float k = scale / to;
    return {anchor.x - (anchor.x - view.x0) * k, anchor.y - (anchor.y - view.y0) * k,
            anchor.x + (view.x1 - anchor.x) * k, anchor.y + (view.y1 - anchor.y) * k};
}

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
