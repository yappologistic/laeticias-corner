#include "render/depth.hpp"

#include <algorithm>
#include <cmath>

namespace lc {

bool drawnBefore(const DepthBox& a, const DepthBox& b) {
    // 1-2. Footprints apart along x or y: the one further back is behind. Apart on both axes the
    // opposite ways round, the two stand side by side on screen and meet only where a sprite is
    // wider than its footprint (a person, a horse): the nearer goes in front (see constrains).
    const int sx = a.foot.x1 <= b.foot.x0 ? -1 : (b.foot.x1 <= a.foot.x0 ? 1 : 0);
    const int sy = a.foot.y1 <= b.foot.y0 ? -1 : (b.foot.y1 <= a.foot.y0 ? 1 : 0);
    if (sx != 0 && sy != 0 && sx != sy) return a.near != b.near ? a.near < b.near : a.id < b.id;
    if (sx != 0) return sx < 0;
    if (sy != 0) return sy < 0;
    // 3. One over the other, apart in height: the camera looks down, so the lower is behind.
    if (a.z1 <= b.z0) return true;
    if (b.z1 <= a.z0) return false;
    // 4. Meeting in all three (a thing partly under another): the higher base is nearer. At one
    // base the two only touch at an edge (a walker at a wall's foot): the axis they reach least
    // into each other along separates them.
    if (a.z0 != b.z0) return a.z0 < b.z0;
    const float ox = std::min(a.foot.x1, b.foot.x1) - std::max(a.foot.x0, b.foot.x0);
    const float oy = std::min(a.foot.y1, b.foot.y1) - std::max(a.foot.y0, b.foot.y0);
    const float ca = ox <= oy ? a.foot.x0 + a.foot.x1 : a.foot.y0 + a.foot.y1;
    const float cb = ox <= oy ? b.foot.x0 + b.foot.x1 : b.foot.y0 + b.foot.y1;
    if (ca != cb) return ca < cb;
    if (a.near != b.near) return a.near < b.near;
    return a.id < b.id;
}

bool constrains(const DepthBox& a, const DepthBox& b) {
    const bool opposite = (a.foot.x1 <= b.foot.x0 && b.foot.y1 <= a.foot.y0) ||
                          (b.foot.x1 <= a.foot.x0 && a.foot.y1 <= b.foot.y0);
    if (!opposite) return true;
    const auto mover = [](const DepthBox& d) {
        const auto k = static_cast<DepthKind>(d.id >> 56);
        return k == DepthKind::Actor || k == DepthKind::Figure;
    };
    return mover(a) || mover(b);
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

} // namespace lc
