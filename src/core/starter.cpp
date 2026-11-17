#include "core/starter.hpp"

#include "core/edit.hpp"
#include "core/land.hpp"

namespace lc {

World makeStarterWorld(const Catalog& cat) {
    World world(cat);
    for (const TerrainFill& f : cat.starter.terrain)
        for (int y = f.rect.y0; y < f.rect.y1; ++y)
            for (int x = f.rect.x0; x < f.rect.x1; ++x) world.setTerrain({x, y}, f.terrain);
    for (const Placement& p : cat.starter.items) {
        const Item item = makeItem(cat, p.item, p.variant, p.pos);
        if (canPlace(world, cat, item) == PlaceResult::Ok) world.addItem(item);
    }
    applyLand(world, cat, 0);
    return world;
}

} // namespace lc
