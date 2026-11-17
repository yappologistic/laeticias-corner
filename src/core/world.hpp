#pragma once
// The map: a terrain grid plus placed items with a per-tile occupancy index.

#include "core/catalog.hpp"
#include "core/iso.hpp"

#include <cstdint>
#include <optional>
#include <span>
#include <vector>

namespace lc {

struct Item {
    std::uint16_t type = 0;
    std::uint8_t variant = 0; // rotation k for rotate layouts, look for variant layouts
    std::uint8_t w = 1;       // footprint after rotation
    std::uint8_t h = 1;
    TilePos pos; // origin tile: smallest tx, ty of the footprint
    friend bool operator==(const Item&, const Item&) = default;
};

struct Footprint {
    int w = 1;
    int h = 1;
};

[[nodiscard]] Footprint footprintOf(const ItemDef& def, int variant);
[[nodiscard]] Item makeItem(const Catalog& cat, int type, int variant, TilePos origin);

class World {
public:
    explicit World(const Catalog& cat);

    [[nodiscard]] int width() const { return w_; }
    [[nodiscard]] int height() const { return h_; }
    [[nodiscard]] bool inBounds(TilePos p) const {
        return p.x >= 0 && p.y >= 0 && p.x < w_ && p.y < h_;
    }
    [[nodiscard]] int terrainAt(TilePos p) const { return terrain_[index(p)]; }
    [[nodiscard]] bool isWater(TilePos p) const { return terrainAt(p) == water_; }
    void setTerrain(TilePos p, int terrain);

    [[nodiscard]] std::span<const Item> items() const { return items_; }
    [[nodiscard]] std::optional<std::size_t> itemIndexAt(TilePos p) const;
    [[nodiscard]] const Item* itemAt(TilePos p) const;
    // Precondition: every footprint tile is in bounds and free.
    void addItem(const Item& item);
    Item removeItem(std::size_t index);

    [[nodiscard]] int terrainCount(int terrain) const {
        return terrainCounts_[static_cast<std::size_t>(terrain)];
    }
    [[nodiscard]] int itemCount(int type) const {
        return itemCounts_[static_cast<std::size_t>(type)];
    }
    // Bumped on every change so views can cache derived data.
    [[nodiscard]] std::uint64_t revision() const { return revision_; }

    // Same-kind neighbour mask (N=1, E=2, S=4, W=8). Out-of-map neighbours count as "same" for
    // terrain so overlays run cleanly into the cliff rim instead of rounding off.
    [[nodiscard]] int terrainMask(TilePos p) const;
    [[nodiscard]] int itemMask(TilePos p, int type) const;

private:
    [[nodiscard]] std::size_t index(TilePos p) const {
        return static_cast<std::size_t>(p.y * w_ + p.x);
    }
    void setOccupancy(const Item& item, std::uint16_t value);

    int w_;
    int h_;
    int water_;
    std::vector<std::uint8_t> terrain_;
    std::vector<std::uint16_t> occupancy_; // item index + 1, 0 = free
    std::vector<Item> items_;
    std::vector<int> terrainCounts_;
    std::vector<int> itemCounts_;
    std::uint64_t revision_ = 0;
};

} // namespace lc
