#pragma once
// The one depth model (docs/design/draw-order.md §1): boxes, their comparator and the painter's
// order over what is near the camera. Pure logic (no SDL) so it is unit-tested directly.

#include "core/iso.hpp"

#include <algorithm>
#include <cstdint>
#include <span>
#include <vector>

namespace lc {

// Every depth-sorted drawable is a box (docs/design/draw-order.md §1.2): a footprint in tile
// coordinates and a height range in px above level 0, with a stable id that breaks the last tie.
struct DepthBox {
    FRect foot;
    float z0 = 0;
    float z1 = 0;
    std::uint64_t id = 0; // deterministic: what it is and which, never a page or a pointer
    float near = 0;       // tie-break nearness, world px: makeBox sets it
};

// A box with its nearness (§1.3: the footprint's mean ground row plus its mean height), for the
// tile half-height `hh`.
[[nodiscard]] constexpr DepthBox makeBox(FRect foot, float z0, float z1, std::uint64_t id,
                                         float hh) {
    return {foot, z0, z1, id,
            (foot.x0 + foot.x1 + foot.y0 + foot.y1) * hh * 0.5f + (z0 + z1) * 0.5f};
}

// What a box stands for, the top byte of its id (ties between equal boxes go in this order).
enum class DepthKind : std::uint8_t { Ground = 1, Item, Figure, Home, Actor, Ghost, Fade };

[[nodiscard]] constexpr std::uint64_t depthId(DepthKind kind, std::uint32_t index,
                                              std::uint32_t part = 0) {
    return (static_cast<std::uint64_t>(kind) << 56) |
           (static_cast<std::uint64_t>(index & 0xFFFFFFu) << 32) | part;
}

// True when a is drawn before b, for two boxes whose screen rectangles overlap (§1.3): the first
// separating axis of x, y, then height decides; boxes that meet in all three go by the higher
// base, then the smaller nearness, then the id. Antisymmetric and total on a pair;
// not transitive across pairs that do not overlap on screen, so it orders a topological sort,
// never std::sort.
[[nodiscard]] bool drawnBefore(const DepthBox& a, const DepthBox& b);

// Buckets rectangles by a uniform grid over their screen boxes so overlap queries only look at
// neighbours. Storage is reused between builds.
class ScreenGrid {
public:
    void build(std::span<const FRect> boxes, float cell);
    // Calls f(index) once per box whose cell range touches r (callers test the exact overlap).
    template <typename F>
    void query(const FRect& r, F&& f) const {
        if (cols_ == 0) return;
        const int cx0 = col(r.x0);
        const int cx1 = col(r.x1);
        const int cy0 = row(r.y0);
        const int cy1 = row(r.y1);
        for (int cy = cy0; cy <= cy1; ++cy)
            for (int cx = cx0; cx <= cx1; ++cx) {
                const auto c = static_cast<std::size_t>(cy * cols_ + cx);
                for (std::uint32_t k = start_[c]; k < start_[c + 1]; ++k) f(items_[k]);
            }
    }
    // Calls f(i, j) once for every pair of boxes that overlap (i < j).
    template <typename F>
    void pairs(std::span<const FRect> boxes, F&& f) const {
        for (int cy = 0; cy < rows_; ++cy)
            for (int cx = 0; cx < cols_; ++cx) {
                const auto c = static_cast<std::size_t>(cy * cols_ + cx);
                for (std::uint32_t a = start_[c]; a < start_[c + 1]; ++a)
                    for (std::uint32_t b = a + 1; b < start_[c + 1]; ++b) {
                        const std::uint32_t i = items_[a];
                        const std::uint32_t j = items_[b];
                        const FRect& p = boxes[i];
                        const FRect& q = boxes[j];
                        if (!p.overlaps(q)) continue;
                        // Report each pair only from the cell holding its overlap's corner.
                        if (col(std::max(p.x0, q.x0)) != cx || row(std::max(p.y0, q.y0)) != cy)
                            continue;
                        f(std::min(i, j), std::max(i, j));
                    }
            }
    }

private:
    [[nodiscard]] int col(float x) const;
    [[nodiscard]] int row(float y) const;

    float x0_ = 0;
    float y0_ = 0;
    float cell_ = 1;
    int cols_ = 0;
    int rows_ = 0;
    std::vector<std::uint32_t> start_; // CSR offsets per cell
    std::vector<std::uint32_t> items_;
    std::vector<std::uint32_t> fill_;
};

} // namespace lc
