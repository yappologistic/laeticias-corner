#include "worldview/cover.hpp"

#include "worldview/order.hpp"
#include "worldview/tuning.hpp"

#include <algorithm>
#include <cmath>

namespace lc::worldview {
namespace {

constexpr int kMaxRows = 40; // tiles behind a sprite that it can still cover (the tallest ~640 px)

// The square round a tile's centre that stands for someone on it in the painter's order.
FRect footOf(TilePos t) {
    const auto x = static_cast<float>(t.x);
    const auto y = static_cast<float>(t.y);
    return {x + 0.5f - tuning::kActorFoot, y + 0.5f - tuning::kActorFoot,
            x + 0.5f + tuning::kActorFoot, y + 0.5f + tuning::kActorFoot};
}

} // namespace

float coverOf(Iso iso, Vec2 point, TilePos t, FRect foot, float raise, const FRect& sprite) {
    // The one depth relation of every level (drawnBefore, as the native merge uses): only
    // something drawn after a person on `t` can hide them.
    const OrderItem element{foot, sprite, 0, false};
    const OrderItem person{footOf(t), {point.x, point.y, point.x, point.y}, 0, false};
    if (drawnBefore(element, person)) return 0;
    if (point.x < sprite.x0 || point.x >= sprite.x1 || point.y < sprite.y0) return 0;
    // Above the bottom edge of the footprint's screen diamond: the sprite stands over the point
    // (below it, the point is in front of the thing, on the ground before it).
    const Vec2 l = iso.toWorld(foot.x0, foot.y1);
    const Vec2 b = iso.toWorld(foot.x1, foot.y1);
    const Vec2 r = iso.toWorld(foot.x1, foot.y0);
    if (point.x < l.x || point.x > r.x) return 0;
    const float bottom =
        (point.x <= b.x ? l.y + (b.y - l.y) * (point.x - l.x) / std::max(1.0f, b.x - l.x)
                        : b.y + (r.y - b.y) * (point.x - b.x) / std::max(1.0f, r.x - b.x)) -
        raise;
    if (point.y > bottom) return 0;
    // And under the footprint's top edges raised to the sprite's top: the silhouette of the
    // thing standing on the footprint, not the box round its sprite (no transparent corners).
    const Vec2 tv = iso.toWorld(foot.x0, foot.y0);
    const float height = tv.y - raise - sprite.y0;
    const float topEdge =
        (point.x <= tv.x ? l.y + (tv.y - l.y) * (point.x - l.x) / std::max(1.0f, tv.x - l.x)
                         : tv.y + (r.y - tv.y) * (point.x - tv.x) / std::max(1.0f, r.x - tv.x)) -
        raise - height;
    if (point.y < topEdge) return 0;
    return point.y - topEdge;
}

CoverMap::CoverMap(const world::WorldMap& map, const WorldSprites& sprites, const Hole& hole)
    : map_(map), iso_(map.content().home().iso()), lvl_(map.content().tileLevel()), hole_(hole),
      cover_(static_cast<std::size_t>(map.width()) * static_cast<std::size_t>(map.height()), 0) {
    // Items and landmark pieces with the sprite the impostors draw for them.
    for (const world::Placed& it : map.items()) {
        if (hole_.tiles.contains(TilePos{it.x, it.y})) continue;
        const VariantLook& look = sprites.item(it);
        const Vec2 w = iso_.toWorld(TilePos{it.x, it.y});
        const Vec2 a{w.x, w.y - static_cast<float>(it.level * lvl_)};
        const auto rect = [&](const SpriteRef& s) {
            return FRect{a.x - s.ox, a.y - s.oy, a.x - s.ox + s.w, a.y - s.oy + s.h};
        };
        // Split exactly as the native order splits it (Gatherer: a piece wherever the geometry
        // has pieces and the look has art for them), so both levels hide the same people.
        const world::GeomVariant* g = map.geometry(it);
        if (g != nullptr && !g->pieces.empty() && !look.pieces.empty()) {
            for (std::size_t k = 0; k < g->pieces.size() && k < look.pieces.size(); ++k) {
                const TileRect& p = g->pieces[k].rect;
                occlude({static_cast<float>(it.x + p.x0), static_cast<float>(it.y + p.y0),
                         static_cast<float>(it.x + p.x1), static_cast<float>(it.y + p.y1)},
                        it.level, rect(look.pieces[k]));
            }
        } else if (!look.base.empty()) {
            const TileRect r = it.rect();
            occlude({static_cast<float>(r.x0), static_cast<float>(r.y0), static_cast<float>(r.x1),
                     static_cast<float>(r.y1)},
                    it.level, rect(look.base.f.front()));
        }
    }
    // Raised ground hides what is lower behind it.
    for (int y = 0; y < map.height(); ++y)
        for (int x = 0; x < map.width(); ++x)
            if (map.level({x, y}) > 0) raised({x, y});
}

void CoverMap::occlude(FRect foot, int level, const FRect& sprite) {
    const float raise = static_cast<float>(level * lvl_);
    const float bottom = iso_.toWorld(foot.x1, foot.y1).y - raise;
    const int rows =
        std::min(kMaxRows, static_cast<int>(std::ceil((bottom - sprite.y0) / iso_.hh)) + 1);
    const TileRect r =
        TileRect{static_cast<int>(foot.x0) - rows, static_cast<int>(foot.y0) - rows,
                 static_cast<int>(std::ceil(foot.x1)), static_cast<int>(std::ceil(foot.y1))}
            .clipped(map_.bounds());
    for (int y = r.y0; y < r.y1; ++y)
        for (int x = r.x0; x < r.x1; ++x) {
            const TilePos t{x, y};
            if (static_cast<float>(x) >= foot.x0 && static_cast<float>(x) < foot.x1 &&
                static_cast<float>(y) >= foot.y0 && static_cast<float>(y) < foot.y1)
                continue; // under it, not behind it (a walk tile: someone stands on it)
            if (hole_.tiles.contains(t)) continue;
            const Vec2 c = iso_.toWorld(static_cast<float>(x) + 0.5f, static_cast<float>(y) + 0.5f);
            const Vec2 p{c.x, c.y - static_cast<float>(map_.level(t) * lvl_)};
            const float k = coverOf(iso_, p, t, foot, raise, sprite);
            auto& v = cover_[static_cast<std::size_t>(y * map_.width() + x)];
            v = static_cast<std::uint8_t>(std::max<float>(v, std::min(255.0f, k)));
        }
}

void CoverMap::raised(TilePos q) {
    // A raised tile is a block from its neighbours' ground up to its own top: lower tiles behind
    // it within its height are hidden by its top and faces.
    if (hole_.tiles.contains(q)) return;
    const int lq = map_.level(q);
    const FRect foot{static_cast<float>(q.x), static_cast<float>(q.y), static_cast<float>(q.x + 1),
                     static_cast<float>(q.y + 1)};
    const Vec2 top = iso_.toWorld(q);
    for (int a = 0; a <= lq + 1; ++a)
        for (int b = 0; a + b <= lq + 1; ++b) {
            const TilePos t{q.x - a, q.y - b};
            if ((a == 0 && b == 0) || !map_.inBounds(t) || hole_.tiles.contains(t)) continue;
            const int lt = map_.level(t);
            if (lt >= lq) continue;
            const Vec2 c =
                iso_.toWorld(static_cast<float>(t.x) + 0.5f, static_cast<float>(t.y) + 0.5f);
            const Vec2 p{c.x, c.y - static_cast<float>(lt * lvl_)};
            // The block's silhouette: its top surface's diamond down to the lower ground.
            const float edge = top.y - static_cast<float>(lq * lvl_) + std::abs(p.x - top.x) * 0.5f;
            const FRect sprite{top.x - iso_.hw, edge, top.x + iso_.hw, edge + iso_.tileH()};
            const float k = coverOf(iso_, p, t, foot, static_cast<float>(lt * lvl_), sprite);
            auto& v = cover_[static_cast<std::size_t>(t.y * map_.width() + t.x)];
            v = static_cast<std::uint8_t>(std::max<float>(v, std::min(255.0f, k)));
        }
}

} // namespace lc::worldview
