#include "render/decks.hpp"

#include <algorithm>
#include <cmath>

namespace lc {
namespace {

// r0 (and r2) spans +x, r1 (and r3) +y.
bool alongX(const Item& item) {
    return item.variant % 2 == 0;
}

} // namespace

bool railed(const ItemDef& def) {
    return def.walkable && def.deck > 0 && def.layout == Layout::Rotate;
}

float deckAt(const World& world, const Catalog& cat, Vec2 pos) {
    const auto deck = [&](TilePos t) {
        const Item* it = world.itemAt(t);
        if (it == nullptr) return 0.0f;
        const ItemDef& d = cat.items[it->type];
        return d.walkable ? static_cast<float>(d.deck) : 0.0f;
    };
    // Open water beside a footbridge is not stepped onto: the deck does not dip toward it.
    const auto steppable = [&](TilePos t) {
        if (!world.hasGround(t)) return false;
        const Item* it = world.itemAt(t);
        return !world.isWater(t) || (it != nullptr && cat.items[it->type].walkable);
    };
    const TilePos t{static_cast<int>(std::floor(pos.x)), static_cast<int>(std::floor(pos.y))};
    if (!world.inBounds(t)) return 0.0f;
    const float z = deck(t);
    const float fx = pos.x - static_cast<float>(t.x) - 0.5f;
    const float fy = pos.y - static_cast<float>(t.y) - 0.5f;
    float out = z;
    const auto toward = [&](TilePos n, float f) {
        if (f > 0 && steppable(n)) out += f * (deck(n) - z);
    };
    toward({t.x + 1, t.y}, fx);
    toward({t.x - 1, t.y}, -fx);
    toward({t.x, t.y + 1}, fy);
    toward({t.x, t.y - 1}, -fy);
    return out;
}

DepthBox crossingBox(const ItemDef& def, const Item& item, int part, float top, std::uint64_t id,
                     float hh) {
    const auto f = [](int v) { return static_cast<float>(v); };
    FRect foot{f(item.pos.x), f(item.pos.y), f(item.pos.x + item.w), f(item.pos.y + item.h)};
    const auto deck = static_cast<float>(def.deck);
    const float under = deck > 0 ? 1.0f : 0.0f; // whatever swims under it stays under it
    if (part < 0) return makeBox(foot, under, deck, id, hh);
    const bool x = alongX(item);
    const float mid = x ? f(item.pos.y) + 0.5f : f(item.pos.x) + 0.5f;
    (x ? (part == 0 ? foot.y1 : foot.y0) : (part == 0 ? foot.x1 : foot.x0)) = mid;
    return makeBox(foot, part == 0 ? under : deck + 1, std::max(top, deck + 2), id, hh);
}

CutLine crossingCut(const ItemDef& def, const Item& item, Iso iso) {
    // A ground point (gx, gy) at height z is drawn at x = (gx - gy)·hw, y = (gx + gy)·hh - z:
    // the line gy = c (a span along x) or gx = c (along y) at the deck's height.
    const bool x = alongX(item);
    const float c =
        x ? static_cast<float>(item.pos.y) + 0.5f : static_cast<float>(item.pos.x) + 0.5f;
    return {2.0f * c * iso.hh - static_cast<float>(def.deck), (x ? 1.0f : -1.0f) * iso.hh / iso.hw};
}

} // namespace lc
