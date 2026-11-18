#pragma once
// Grid path-finding for walkers and swimmers (docs/design/living-corner.md R6.5): A* over eight
// directions without cutting corners, bounded in area and in nodes expanded, with its buffers
// reused between searches so steady play allocates nothing. Paths are then pulled straight where
// a straight line costs no more than the steps it replaces, so walkers keep to the paths.

#include "core/actor_data.hpp"
#include "core/iso.hpp"

#include <cstdint>
#include <span>
#include <vector>

namespace lc {

struct Catalog;
class World;

struct PathQuery {
    Locomotion move = Locomotion::Walk;
    TilePos from;
    TilePos to;
    TileRect bounds;   // the search never leaves this rectangle
    bool bank = false; // a swimmer may step out onto land next to water (to sleep on the bank)
};

// Whether an actor moving this way may stand on tile t. `bank` lets swimmers onto the bank.
[[nodiscard]] bool passable(const World& world, const Catalog& cat, Locomotion move, TilePos t,
                            bool bank = false);
// Cost of stepping onto a passable tile: paths, cobbles and crossings are cheaper to walk.
[[nodiscard]] float stepCost(const World& world, const Catalog& cat, Locomotion move, TilePos t);

class PathFinder {
public:
    explicit PathFinder(const Catalog& cat);
    // Writes the tiles to visit after `from`, ending with `to`, into `out` (at most out.size();
    // a longer route is cut and re-planned on arrival). The goal tile itself may be occupied
    // (a seat is stepped onto). Returns the number written, 0 when there is no way.
    int find(const World& world, const PathQuery& q, std::span<TilePos> out);
    [[nodiscard]] int lastExpanded() const { return expanded_; }

private:
    struct Open {
        float f;
        std::uint32_t node;
    };
    const Catalog* cat_; // a pointer, so a fresh one can be assigned when another world opens
    std::vector<float> g_;
    std::vector<std::uint32_t> parent_;
    std::vector<std::uint32_t> stamp_; // the search a node's data belongs to
    std::vector<std::uint8_t> closed_;
    std::vector<Open> heap_;
    std::vector<TilePos> route_;
    std::uint32_t search_ = 0;
    int expanded_ = 0;
};

} // namespace lc
