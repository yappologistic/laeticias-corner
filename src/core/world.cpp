#include "core/world.hpp"

#include <algorithm>
#include <cassert>

namespace lc {

Footprint footprintOf(const ItemDef& def, int variant) {
    if (def.layout == Layout::Rotate && variant % 2 == 1) return {def.footprintH, def.footprintW};
    return {def.footprintW, def.footprintH};
}

Item makeItem(const Catalog& cat, int type, int variant, TilePos origin) {
    const auto fp = footprintOf(cat.items[static_cast<std::size_t>(type)], variant);
    return Item{.type = static_cast<std::uint16_t>(type),
                .variant = static_cast<std::uint8_t>(variant),
                .w = static_cast<std::uint8_t>(fp.w),
                .h = static_cast<std::uint8_t>(fp.h),
                .pos = origin};
}

World::World(const Catalog& cat) : World(cat, cat.mapW, cat.mapH) {}

World::World(const Catalog& cat, int width, int height)
    : w_(width), h_(height), cw_((width + kChunk - 1) >> kChunkShift),
      ch_((height + kChunk - 1) >> kChunkShift), water_(cat.waterTerrain),
      chunks_(static_cast<std::size_t>(cw_) * static_cast<std::size_t>(ch_)),
      terrainCounts_(cat.terrain.size(), 0), itemCounts_(cat.items.size(), 0) {
    const auto base = static_cast<std::uint8_t>(cat.baseTerrain);
    for (int cy = 0; cy < ch_; ++cy) {
        for (int cx = 0; cx < cw_; ++cx) {
            Chunk& c = chunks_[chunkIndex(cx, cy)];
            c.terrainCounts.assign(cat.terrain.size(), 0);
            c.itemCounts.assign(cat.items.size(), 0);
            for (int y = 0; y < kChunk; ++y) {
                for (int x = 0; x < kChunk; ++x) {
                    const TilePos p{cx * kChunk + x, cy * kChunk + y};
                    const bool in = inBounds(p);
                    c.terrain[local(p)] = in ? base : kNoGround;
                    c.terrainCounts[base] += in ? 1 : 0;
                }
            }
        }
    }
    terrainCounts_[base] = w_ * h_;
    land_ = bounds();
}

void World::bumpTerrain(TilePos p) {
    // Edges and cliff faces depend on the four neighbours, so their chunks are stale too.
    const TilePos around[5] = {p, {p.x - 1, p.y}, {p.x + 1, p.y}, {p.x, p.y - 1}, {p.x, p.y + 1}};
    std::size_t done[5];
    std::size_t n = 0;
    for (const TilePos q : around) {
        if (!inBounds(q)) continue;
        const std::size_t ci = chunkIndex(q.x >> kChunkShift, q.y >> kChunkShift);
        if (std::find(done, done + n, ci) != done + n) continue;
        done[n++] = ci;
        ++chunks_[ci].terrainRev;
    }
}

void World::setTerrain(TilePos p, int terrain) {
    Chunk& c = chunkOf(p);
    auto& cell = c.terrain[local(p)];
    if (cell == terrain) return;
    if (cell == kNoGround || terrain == kNoGround) land_.reset();
    if (cell != kNoGround) {
        --terrainCounts_[cell];
        --c.terrainCounts[cell];
    }
    cell = static_cast<std::uint8_t>(terrain);
    if (cell != kNoGround) {
        ++terrainCounts_[cell];
        ++c.terrainCounts[cell];
    }
    bumpTerrain(p);
    ++revision_;
}

void World::setWild(TilePos p, bool wild) {
    Chunk& c = chunkOf(p);
    if (c.wild[local(p)] == wild) return;
    c.wild[local(p)] = wild;
    wildCount_ += wild ? 1 : -1;
    bumpTerrain(p);
    ++revision_;
}

void World::setGrowth(std::size_t index, int stage, float progress) {
    Item& it = items_[index];
    if (it.stage != stage) ++revision_;
    it.stage = static_cast<std::uint8_t>(stage);
    it.growth = progress;
}

TileRect World::landBounds() const {
    if (land_) return *land_;
    TileRect r{w_, h_, 0, 0};
    for (int y = 0; y < h_; ++y) {
        for (int x = 0; x < w_; ++x) {
            if (terrainAt({x, y}) == kNoGround) continue;
            r = {std::min(r.x0, x), std::min(r.y0, y), std::max(r.x1, x + 1),
                 std::max(r.y1, y + 1)};
        }
    }
    land_ = r.empty() ? TileRect{} : r;
    return *land_;
}

std::optional<std::size_t> World::itemIndexAt(TilePos p) const {
    if (!inBounds(p)) return std::nullopt;
    const auto v = chunkOf(p).occupancy[local(p)];
    if (v == 0) return std::nullopt;
    return static_cast<std::size_t>(v - 1);
}

const Item* World::itemAt(TilePos p) const {
    const auto i = itemIndexAt(p);
    return i ? &items_[*i] : nullptr;
}

void World::setOccupancy(const Item& item, std::uint32_t value) {
    for (int y = item.pos.y; y < item.pos.y + item.h; ++y)
        for (int x = item.pos.x; x < item.pos.x + item.w; ++x)
            chunkOf({x, y}).occupancy[local({x, y})] = value;
}

void World::addItem(const Item& item) {
    assert(items_.size() < 0xFFFFFFFEu);
    const auto index = static_cast<std::uint32_t>(items_.size());
    items_.push_back(item);
    setOccupancy(item, index + 1);
    Chunk& c = chunkOf(item.pos);
    c.items.push_back(index);
    ++c.itemCounts[item.type];
    ++c.itemRev;
    ++itemCounts_[item.type];
    ++revision_;
}

Item World::removeItem(std::size_t i) {
    const Item removed = items_[i];
    setOccupancy(removed, 0);
    const auto drop = [](std::vector<std::uint32_t>& list, std::uint32_t v) {
        const auto it = std::ranges::find(list, v);
        assert(it != list.end());
        *it = list.back();
        list.pop_back();
    };
    Chunk& c = chunkOf(removed.pos);
    drop(c.items, static_cast<std::uint32_t>(i));
    --c.itemCounts[removed.type];
    ++c.itemRev;
    const std::size_t last = items_.size() - 1;
    if (i != last) {
        // The last item takes the freed slot: repoint its occupancy and chunk entry.
        items_[i] = items_[last];
        setOccupancy(items_[i], static_cast<std::uint32_t>(i + 1));
        auto& list = chunkOf(items_[i].pos).items;
        *std::ranges::find(list, static_cast<std::uint32_t>(last)) = static_cast<std::uint32_t>(i);
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
        return !hasGround(q) || terrainAt(q) == t;
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
