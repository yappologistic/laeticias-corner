#include "worldview/cells.hpp"

#include <algorithm>

namespace lc::worldview {

TileRect tilesUnder(const FRect& px, Iso iso) {
    const Vec2 c[4] = {iso.toTile({px.x0, px.y0}), iso.toTile({px.x1, px.y0}),
                       iso.toTile({px.x0, px.y1}), iso.toTile({px.x1, px.y1})};
    float x0 = c[0].x, x1 = c[0].x, y0 = c[0].y, y1 = c[0].y;
    for (const Vec2& v : c) {
        x0 = std::min(x0, v.x);
        x1 = std::max(x1, v.x);
        y0 = std::min(y0, v.y);
        y1 = std::max(y1, v.y);
    }
    return {static_cast<int>(std::floor(x0)), static_cast<int>(std::floor(y0)),
            static_cast<int>(std::floor(x1)) + 1, static_cast<int>(std::floor(y1)) + 1};
}

int lruSlot(std::span<const std::uint64_t> lastUsed, std::uint64_t frame, std::uint64_t spare) {
    int best = -1;
    for (std::size_t i = 0; i < lastUsed.size(); ++i)
        if (lastUsed[i] + spare < frame &&
            (best < 0 || lastUsed[i] < lastUsed[static_cast<std::size_t>(best)]))
            best = static_cast<int>(i);
    return best;
}

std::vector<int> pagesToEvict(std::span<const PageUse> pages, double now, double idle,
                              std::size_t budget) {
    std::size_t resident = 0;
    std::vector<int> candidates;
    for (std::size_t i = 0; i < pages.size(); ++i) {
        const PageUse& p = pages[i];
        if (!p.resident) continue;
        resident += p.bytes;
        if (!p.wanted && now - p.lastUsed >= idle) candidates.push_back(static_cast<int>(i));
    }
    std::ranges::stable_sort(candidates, [&](int a, int b) {
        return pages[static_cast<std::size_t>(a)].lastUsed <
               pages[static_cast<std::size_t>(b)].lastUsed;
    });
    std::vector<int> out;
    for (const int i : candidates) {
        if (resident <= budget) break;
        resident -= pages[static_cast<std::size_t>(i)].bytes;
        out.push_back(i);
    }
    return out;
}

} // namespace lc::worldview
