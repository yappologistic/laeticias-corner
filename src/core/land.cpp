#include "core/land.hpp"

#include "core/edit.hpp"

#include <algorithm>
#include <utility>

namespace lc {

int stageAt(const Catalog& cat, TilePos p) {
    for (std::size_t s = 0; s < cat.stages.size(); ++s)
        for (const TileRect& r : cat.stages[s].rects)
            if (r.contains(p)) return static_cast<int>(s);
    return 0;
}

void applyLand(World& world, const Catalog& cat, int opened) {
    for (int y = 0; y < world.height(); ++y)
        for (int x = 0; x < world.width(); ++x)
            if (world.hasGround({x, y})) world.setWild({x, y}, stageAt(cat, {x, y}) > opened);
}

void openStage(World& world, const Catalog& cat, int stage, std::vector<Item>& placed) {
    const StageDef& def = cat.stages[static_cast<std::size_t>(stage)];
    for (const TileRect& r : def.rects)
        for (int y = r.y0; y < r.y1; ++y)
            for (int x = r.x0; x < r.x1; ++x)
                if (world.hasGround({x, y})) world.setWild({x, y}, false);
    for (const TerrainFill& f : def.terrain)
        for (int y = f.rect.y0; y < f.rect.y1; ++y)
            for (int x = f.rect.x0; x < f.rect.x1; ++x)
                if (world.hasGround({x, y}) && !world.itemAt({x, y}))
                    world.setTerrain({x, y}, f.terrain);
    for (const Placement& p : def.items) {
        const Item it = makeItem(cat, p.item, p.variant, p.pos);
        if (canPlace(world, cat, it) != PlaceResult::Ok) continue;
        world.addItem(it);
        placed.push_back(it);
    }
}

int nextStagePages(const Catalog& cat, int opened) {
    const auto next = static_cast<std::size_t>(opened + 1);
    return next < cat.stages.size() ? cat.stages[next].pages : -1;
}

TileRect openBounds(const Catalog& cat, int opened, const World& world) {
    TileRect r{world.width(), world.height(), 0, 0};
    bool any = false;
    for (int s = 0; s <= opened && std::cmp_less(s, cat.stages.size()); ++s)
        for (const TileRect& t : cat.stages[static_cast<std::size_t>(s)].rects) {
            const TileRect c = t.clipped(world.bounds());
            if (c.empty()) continue;
            r = any ? TileRect{std::min(r.x0, c.x0), std::min(r.y0, c.y0), std::max(r.x1, c.x1),
                               std::max(r.y1, c.y1)}
                    : c;
            any = true;
        }
    // Maps larger than the stages (benchmarks) are open everywhere.
    return any && world.width() == cat.mapW && world.height() == cat.mapH ? r : world.landBounds();
}

} // namespace lc
