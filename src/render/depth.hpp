#pragma once
// Painter's order for footprints on the isometric grid, computed only for what is near the camera.
// Pure logic (no SDL) so it is unit-tested directly.

#include "core/iso.hpp"

#include <algorithm>
#include <cstdint>
#include <span>
#include <vector>

namespace lc {

// True when footprint a must be drawn before footprint b (both in tile coordinates).
// Non-overlapping footprints are separated along at least one axis; the one further along +x or
// +y is nearer the viewer. When the separation is ambiguous the footprint centres decide.
[[nodiscard]] bool behind(const FRect& a, const FRect& b);

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

// Orders `footprints` so that whenever two `screens` overlap, the footprint behind comes first.
// Ties go to the shallower footprint centre, then to the lower index, so results are stable.
class DepthSorter {
public:
    void sort(std::span<const FRect> footprints, std::span<const FRect> screens, float cell,
              std::vector<std::uint32_t>& order);
    [[nodiscard]] const ScreenGrid& grid() const { return grid_; }

private:
    ScreenGrid grid_;
    std::vector<std::uint32_t> edgeFrom_;
    std::vector<std::uint32_t> edgeTo_;
    std::vector<std::uint32_t> start_;
    std::vector<std::uint32_t> next_;
    std::vector<std::uint32_t> cursor_;
    std::vector<int> indegree_;
    std::vector<std::uint8_t> done_;
    std::vector<std::pair<float, std::uint32_t>> heap_;
};

} // namespace lc
