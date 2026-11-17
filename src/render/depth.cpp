#include "render/depth.hpp"

#include <algorithm>
#include <cmath>
#include <functional>

namespace lc {

bool behind(const FRect& a, const FRect& b) {
    const int sx = a.x1 <= b.x0 ? -1 : (b.x1 <= a.x0 ? 1 : 0);
    const int sy = a.y1 <= b.y0 ? -1 : (b.y1 <= a.y0 ? 1 : 0);
    if ((sx == 0 && sy == 0) || (sx != 0 && sy != 0 && sx != sy))
        return a.x0 + a.x1 + a.y0 + a.y1 <= b.x0 + b.x1 + b.y0 + b.y1;
    return (sx != 0 ? sx : sy) < 0;
}

int ScreenGrid::col(float x) const {
    return std::clamp(static_cast<int>(std::floor((x - x0_) / cell_)), 0, cols_ - 1);
}

int ScreenGrid::row(float y) const {
    return std::clamp(static_cast<int>(std::floor((y - y0_) / cell_)), 0, rows_ - 1);
}

void ScreenGrid::build(std::span<const FRect> boxes, float cell) {
    cols_ = rows_ = 0;
    if (boxes.empty()) return;
    FRect all = boxes.front();
    for (const FRect& b : boxes)
        all = {std::min(all.x0, b.x0), std::min(all.y0, b.y0), std::max(all.x1, b.x1),
               std::max(all.y1, b.y1)};
    x0_ = all.x0;
    y0_ = all.y0;
    cell_ = cell;
    // Keep the grid modest even for a huge region: cells grow instead.
    constexpr int kMaxSide = 512;
    const float span = std::max(all.x1 - all.x0, all.y1 - all.y0);
    if (span / cell_ > kMaxSide) cell_ = span / kMaxSide;
    cols_ = std::max(1, static_cast<int>(std::ceil((all.x1 - all.x0) / cell_)));
    rows_ = std::max(1, static_cast<int>(std::ceil((all.y1 - all.y0) / cell_)));
    const auto cells = static_cast<std::size_t>(cols_ * rows_);
    start_.assign(cells + 1, 0);
    for (const FRect& b : boxes)
        for (int cy = row(b.y0); cy <= row(b.y1); ++cy)
            for (int cx = col(b.x0); cx <= col(b.x1); ++cx)
                ++start_[static_cast<std::size_t>(cy * cols_ + cx) + 1];
    for (std::size_t c = 0; c < cells; ++c) start_[c + 1] += start_[c];
    items_.resize(start_[cells]);
    fill_.assign(start_.begin(), start_.end() - 1);
    for (std::uint32_t i = 0; i < boxes.size(); ++i) {
        const FRect& b = boxes[i];
        for (int cy = row(b.y0); cy <= row(b.y1); ++cy)
            for (int cx = col(b.x0); cx <= col(b.x1); ++cx)
                items_[fill_[static_cast<std::size_t>(cy * cols_ + cx)]++] = i;
    }
}

void DepthSorter::sort(std::span<const FRect> footprints, std::span<const FRect> screens,
                       float cell, std::vector<std::uint32_t>& order) {
    const std::size_t n = footprints.size();
    order.clear();
    grid_.build(screens, cell);
    edgeFrom_.clear();
    edgeTo_.clear();
    grid_.pairs(screens, [&](std::uint32_t i, std::uint32_t j) {
        const bool ij = behind(footprints[i], footprints[j]);
        edgeFrom_.push_back(ij ? i : j);
        edgeTo_.push_back(ij ? j : i);
    });
    // Adjacency in CSR form.
    start_.assign(n + 1, 0);
    indegree_.assign(n, 0);
    for (std::size_t e = 0; e < edgeFrom_.size(); ++e) {
        ++start_[edgeFrom_[e] + 1];
        ++indegree_[edgeTo_[e]];
    }
    for (std::size_t i = 0; i < n; ++i) start_[i + 1] += start_[i];
    next_.resize(edgeFrom_.size());
    cursor_.assign(start_.begin(), start_.end() - 1);
    for (std::size_t e = 0; e < edgeFrom_.size(); ++e) next_[cursor_[edgeFrom_[e]]++] = edgeTo_[e];
    const auto depth = [&](std::uint32_t i) {
        const FRect& f = footprints[i];
        return f.x0 + f.x1 + f.y0 + f.y1;
    };
    heap_.clear();
    const auto push = [&](std::uint32_t i) {
        heap_.emplace_back(depth(i), i);
        std::ranges::push_heap(heap_, std::greater<>{});
    };
    for (std::uint32_t i = 0; i < n; ++i)
        if (indegree_[i] == 0) push(i);
    done_.assign(n, 0);
    while (order.size() < n) {
        if (heap_.empty()) {
            // A cycle (only possible with contrived layouts): break it at the shallowest item.
            std::uint32_t pick = 0;
            bool found = false;
            for (std::uint32_t i = 0; i < n; ++i)
                if (done_[i] == 0 && (!found || depth(i) < depth(pick))) {
                    pick = i;
                    found = true;
                }
            indegree_[pick] = 0;
            push(pick);
        }
        std::ranges::pop_heap(heap_, std::greater<>{});
        const std::uint32_t i = heap_.back().second;
        heap_.pop_back();
        if (done_[i] != 0) continue;
        done_[i] = 1;
        order.push_back(i);
        for (std::uint32_t k = start_[i]; k < start_[i + 1]; ++k) {
            const std::uint32_t j = next_[k];
            if (--indegree_[j] == 0 && done_[j] == 0) push(j);
        }
    }
}

} // namespace lc
