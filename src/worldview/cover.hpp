#pragma once
// The coarser levels' half of the one order (docs/design/draw-order.md §3.2 D, §3.4). At ½ and ¼
// the static world is a cached picture and moving things can only be drawn over it, so each one
// is cut where something nearer covers it instead: per tile the box of what stands there (the
// base and top of its item, px above level 0, from the art's per-tile tops and the same heights
// the native order sorts by) and the ground's own block; an actor's rows inside the silhouette of
// any such box that the comparator puts in front of it are not drawn. Built once from the map.

#include "render/depth.hpp"
#include "world/world_map.hpp"
#include "worldview/gather.hpp"
#include "worldview/world_sprites.hpp"

#include <cstdint>
#include <vector>

namespace lc::worldview {

// Rows of world px, [from, to): empty when from >= to.
struct RowBand {
    float from = 0;
    float to = 0;
    [[nodiscard]] bool empty() const { return from >= to; }
};

// The rows a box covers at screen column `x` (world px): its footprint's diamond raised by z1
// above, by z0 below; empty where the column misses the footprint.
[[nodiscard]] RowBand silhouette(Iso iso, const FRect& foot, float z0, float z1, float x);

class TopField {
public:
    TopField(const world::WorldMap& map, const WorldSprites& sprites, const Hole& hole);

    // In steps of kStep px (one byte each, draw-order.md §3.4): the base rounded down, the top up.
    static constexpr int kStep = 4;
    struct TileBox {
        std::uint8_t low = 0; // base of the item standing on the tile, above level 0
        std::uint8_t top = 0; // its top over this tile (0: no item)
    };
    [[nodiscard]] TileBox at(TilePos t) const {
        return map_.inBounds(t) ? boxes_[static_cast<std::size_t>(t.y * map_.width() + t.x)]
                                : TileBox{};
    }
    // The rows of `actor` (its box; the feet at world px `feet`, raised by its height) that what
    // stands in front of it covers: one band, the hull of every covering silhouette that meets
    // the sprite's rows [spriteTop, feet.y]. With `groundOnly`, raised ground alone (the native
    // level, whose items are in the painter's order already).
    [[nodiscard]] RowBand cut(const DepthBox& actor, Vec2 feet, float spriteTop,
                              bool groundOnly = false) const;
    [[nodiscard]] int maxTop() const { return maxTop_; }

private:
    const world::WorldMap& map_;
    Iso iso_;
    int lvl_;
    Hole hole_;
    std::vector<TileBox> boxes_;
    int maxTop_ = 0;
};

} // namespace lc::worldview
