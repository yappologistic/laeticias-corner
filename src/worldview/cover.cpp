#include "worldview/cover.hpp"

#include <algorithm>
#include <array>
#include <cmath>

namespace lc::worldview {

RowBand silhouette(Iso iso, const FRect& foot, float z0, float z1, float x) {
    const Vec2 l = iso.toWorld(foot.x0, foot.y1);
    const Vec2 t = iso.toWorld(foot.x0, foot.y0);
    const Vec2 r = iso.toWorld(foot.x1, foot.y0);
    const Vec2 b = iso.toWorld(foot.x1, foot.y1);
    if (x < l.x || x > r.x) return {};
    const auto along = [&](Vec2 p, Vec2 q) {
        return q.x > p.x ? p.y + (q.y - p.y) * (x - p.x) / (q.x - p.x) : p.y;
    };
    const float upper = x <= t.x ? along(l, t) : along(t, r);
    const float lower = x <= b.x ? along(l, b) : along(b, r);
    return {upper - z1, lower - z0};
}

TopField::TopField(const world::WorldMap& map, const WorldSprites& sprites, const Hole& hole)
    : map_(map), iso_(map.content().home().iso()), lvl_(map.content().tileLevel()), hole_(hole),
      boxes_(static_cast<std::size_t>(map.width()) * static_cast<std::size_t>(map.height())) {
    std::vector<ZRange> pieces; // per piece of the item at hand
    for (const world::Placed& it : map.items()) {
        if (hole_.tiles.contains(TilePos{it.x, it.y})) continue;
        const world::GeomVariant* g = map.geometry(it);
        const world::ItemInfo& info = map.info(it);
        const VariantLook& look = sprites.item(it);
        const float spriteH = look.base.empty() ? 0.0f : look.base.f.front().oy;
        const std::size_t np = g != nullptr ? g->pieces.size() : 0;
        pieces.clear();
        for (std::size_t p = 0; p < std::max<std::size_t>(np, 1); ++p)
            pieces.push_back(heightsOf(g, info, np == 0 ? -1 : static_cast<int>(p), spriteH));
        const int base = it.level * lvl_;
        for (int dy = 0; dy < it.h; ++dy)
            for (int dx = 0; dx < it.w; ++dx) {
                const TilePos t{it.x + dx, it.y + dy};
                if (!map.inBounds(t)) continue;
                const TilePos rel{dx, dy};
                std::size_t p = 0;
                for (std::size_t q = 0; q < np; ++q)
                    if (g->pieces[q].rect.contains(rel)) p = q;
                const ZRange& z = pieces[p];
                const bool walk = g == nullptr
                                      ? info.walkable
                                      : (std::ranges::find(g->walk, rel) != g->walk.end() ||
                                         (g->walk.empty() && info.walkable));
                // A solid tile's own top where the art gives it; a walk tile's box (its floor,
                // deck or overhead) as the order sorts it.
                float top = z.z1;
                ZRange box = z;
                // A walk tile under a roof in a floor piece: the roof is what can cover anyone.
                if (walk && z.over >= 0) box = {z.over, z.top, ZRange::Kind::Overhead};
                top = box.z1;
                if (!walk && g != nullptr && g->topsW > 0 && dx < g->topsW &&
                    static_cast<std::size_t>(dy * g->topsW + dx) < g->tops.size())
                    top = static_cast<float>(g->tops[static_cast<std::size_t>(dy * g->topsW + dx)]);
                const auto step = [](float v, bool up) {
                    const float s = v / static_cast<float>(kStep);
                    return static_cast<std::uint8_t>(
                        std::clamp(up ? std::ceil(s) : std::floor(s), 0.0f, 255.0f));
                };
                TileBox& b = boxes_[static_cast<std::size_t>(t.y * map.width() + t.x)];
                b.low = step(static_cast<float>(base) + box.z0, false);
                b.top = std::max(b.top,
                                 step(static_cast<float>(base) + std::max(top, box.z0 + 1), true));
                maxTop_ = std::max(maxTop_, b.top * kStep);
            }
    }
    for (int y = 0; y < map.height(); ++y)
        for (int x = 0; x < map.width(); ++x) maxTop_ = std::max(maxTop_, map.level({x, y}) * lvl_);
}

RowBand TopField::cut(const DepthBox& actor, Vec2 feet, float spriteTop, bool groundOnly) const {
    const float fx = (actor.foot.x0 + actor.foot.x1) * 0.5f;
    const float fy = (actor.foot.y0 + actor.foot.y1) * 0.5f;
    const int a = static_cast<int>(std::floor(fx));
    const int b = static_cast<int>(std::floor(fy));
    // Tiles further down the screen than this cannot reach up over the actor.
    const int last = static_cast<int>((static_cast<float>(maxTop_) - actor.z0) / iso_.tileH()) + 2;
    RowBand hidden{};
    const auto consider = [&](const DepthBox& box) {
        if (drawnBefore(box, actor)) return;
        const RowBand s = silhouette(iso_, box.foot, box.z0, box.z1, feet.x);
        if (s.empty() || s.to <= spriteTop || s.from >= feet.y) return;
        hidden =
            hidden.empty() ? s : RowBand{std::min(hidden.from, s.from), std::max(hidden.to, s.to)};
    };
    const auto tile = [&](TilePos t) {
        if (!map_.inBounds(t) || hole_.tiles.contains(t)) return;
        const FRect r{static_cast<float>(t.x), static_cast<float>(t.y), static_cast<float>(t.x + 1),
                      static_cast<float>(t.y + 1)};
        const auto id = static_cast<std::uint32_t>(t.y * map_.width() + t.x);
        if (const int l = map_.level(t); l > 0)
            consider(makeBox(r, 0, static_cast<float>(l * lvl_), depthId(DepthKind::Ground, id),
                             iso_.hh));
        const TileBox& tb = boxes_[id];
        if (!groundOnly && tb.top > 0)
            consider(makeBox(r, static_cast<float>(tb.low * kStep),
                             static_cast<float>(tb.top * kStep), depthId(DepthKind::Item, id),
                             iso_.hh));
    };
    // The tiles round the feet (a roof or a deck over them), then the two diagonals down the
    // screen through the actor's column.
    static constexpr std::array<TilePos, 6> kNear{
        {{-1, -1}, {-1, 0}, {0, -1}, {0, 0}, {1, 0}, {0, 1}}};
    for (const TilePos d : kNear) tile({a + d.x, b + d.y});
    for (int k = 1; k <= last; ++k) {
        tile({a + k, b + k});
        tile({a + k + 1, b + k});
        tile({a + k, b + k + 1});
    }
    return hidden;
}

} // namespace lc::worldview
