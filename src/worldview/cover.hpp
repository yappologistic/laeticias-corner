#pragma once
// What hides a ground point at the coarser levels, where the static world is a cached impostor
// and moving things can only go over it: per tile, how many px of something in front (an item, a
// landmark's piece, raised ground) stand above that tile's ground point on screen. Built once from
// the same sprites the impostors are drawn from; an actor whose feet are covered is not drawn
// there, so nobody walks on the roofs of the buildings they are behind.

#include "world/world_map.hpp"
#include "worldview/gather.hpp"
#include "worldview/world_sprites.hpp"

#include <cmath>
#include <cstdint>
#include <vector>

namespace lc::worldview {

class CoverMap {
public:
    CoverMap(const world::WorldMap& map, const WorldSprites& sprites, const Hole& hole);
    // Px of something in front above the ground point of `t` (0 when none, 255 at most).
    [[nodiscard]] int at(TilePos t) const {
        return map_.inBounds(t) ? cover_[static_cast<std::size_t>(t.y * map_.width() + t.x)] : 0;
    }

    // The same at a point between tile centres (continuous tile coordinates, x.5: a centre),
    // blended from the four centres round it: someone in the back half of a tile behind a wall
    // is as covered as where they stand, not as the middle of their tile.
    [[nodiscard]] float at(Vec2 p) const {
        const float fx = p.x - 0.5f;
        const float fy = p.y - 0.5f;
        const int x = static_cast<int>(std::floor(fx));
        const int y = static_cast<int>(std::floor(fy));
        const float u = fx - static_cast<float>(x);
        const float v = fy - static_cast<float>(y);
        const auto c = [&](int dx, int dy) {
            return static_cast<float>(at(TilePos{x + dx, y + dy}));
        };
        return (c(0, 0) * (1 - u) + c(1, 0) * u) * (1 - v) + (c(0, 1) * (1 - u) + c(1, 1) * u) * v;
    }

private:
    // Marks the tiles behind `foot` whose ground point lies in `sprite` (world px) and above the
    // footprint's bottom edge at `level`.
    void occlude(FRect foot, int level, const FRect& sprite);
    void raised(TilePos q);

    const world::WorldMap& map_;
    Iso iso_;
    int lvl_;
    Hole hole_;
    std::vector<std::uint8_t> cover_;
};

// How many px of what stands on `foot` (its sprite `sprite`, raised by `raise` px) are drawn over
// the ground point of tile `t` at `point`: the point must be in its silhouette (the footprint's
// screen diamond extruded to the sprite's top, within the sprite) and the thing drawn after
// someone on `t` by the order's one depth relation (0: not covered). The rule the cover map
// rasterises, for tests to check against.
[[nodiscard]] float coverOf(Iso iso, Vec2 point, TilePos t, FRect foot, float raise,
                            const FRect& sprite);

} // namespace lc::worldview
