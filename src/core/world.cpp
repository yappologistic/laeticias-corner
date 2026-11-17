#include "core/world.hpp"

#include <cassert>

namespace lc {

Footprint footprintOf(const ItemDef& def, int variant) {
    if (def.layout == Layout::Rotate && variant % 2 == 1) return {def.footprintH, def.footprintW};
    return {def.footprintW, def.footprintH};
}

Item makeItem(const Catalog& cat, int type, int variant, TilePos origin) {
    const auto fp = footprintOf(cat.items[static_cast<std::size_t>(type)], variant);
    return Item{static_cast<std::uint16_t>(type), static_cast<std::uint8_t>(variant),
                static_cast<std::uint8_t>(fp.w), static_cast<std::uint8_t>(fp.h), origin};
}

World::World(const Catalog& cat)
    : w_(cat.mapW), h_(cat.mapH), water_(cat.waterTerrain),
      terrain_(static_cast<std::size_t>(w_ * h_), static_cast<std::uint8_t>(cat.baseTerrain)),
      occupancy_(static_cast<std::size_t>(w_ * h_), 0), terrainCounts_(cat.terrain.size(), 0),
      itemCounts_(cat.items.size(), 0) {
    terrainCounts_[static_cast<std::size_t>(cat.baseTerrain)] = w_ * h_;
    items_.reserve(static_cast<std::size_t>(w_ * h_));
}

void World::setTerrain(TilePos p, int terrain) {
    auto& cell = terrain_[index(p)];
    if (cell == terrain) return;
    --terrainCounts_[cell];
    cell = static_cast<std::uint8_t>(terrain);
    ++terrainCounts_[cell];
    ++revision_;
}

std::optional<std::size_t> World::itemIndexAt(TilePos p) const {
    if (!inBounds(p)) return std::nullopt;
    const auto v = occupancy_[index(p)];
    if (v == 0) return std::nullopt;
    return static_cast<std::size_t>(v - 1);
}

const Item* World::itemAt(TilePos p) const {
    const auto i = itemIndexAt(p);
    return i ? &items_[*i] : nullptr;
}

void World::setOccupancy(const Item& item, std::uint16_t value) {
    for (int y = item.pos.y; y < item.pos.y + item.h; ++y)
        for (int x = item.pos.x; x < item.pos.x + item.w; ++x) occupancy_[index({x, y})] = value;
}

void World::addItem(const Item& item) {
    assert(items_.size() < 0xFFFF);
    items_.push_back(item);
    setOccupancy(item, static_cast<std::uint16_t>(items_.size()));
    ++itemCounts_[item.type];
    ++revision_;
}

Item World::removeItem(std::size_t i) {
    const Item removed = items_[i];
    setOccupancy(removed, 0);
    if (i + 1 != items_.size()) {
        items_[i] = items_.back();
        setOccupancy(items_[i], static_cast<std::uint16_t>(i + 1));
    }
    items_.pop_back();
    --itemCounts_[removed.type];
    ++revision_;
    return removed;
}

int World::terrainMask(TilePos p) const {
    const int t = terrainAt(p);
    const auto same = [&](int dx, int dy) {
        const TilePos q{p.x + dx, p.y + dy};
        return !inBounds(q) || terrainAt(q) == t;
    };
    return (same(0, -1) ? kMaskN : 0) | (same(1, 0) ? kMaskE : 0) | (same(0, 1) ? kMaskS : 0) |
           (same(-1, 0) ? kMaskW : 0);
}

int World::itemMask(TilePos p, int type) const {
    const auto same = [&](int dx, int dy) {
        const Item* it = itemAt({p.x + dx, p.y + dy});
        return it != nullptr && it->type == type;
    };
    return (same(0, -1) ? kMaskN : 0) | (same(1, 0) ? kMaskE : 0) | (same(0, 1) ? kMaskS : 0) |
           (same(-1, 0) ? kMaskW : 0);
}

} // namespace lc
