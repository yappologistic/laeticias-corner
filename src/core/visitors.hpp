#pragma once
// Who comes to the corner: visitors[].needs decide how many of each kind an area attracts, the
// progress loop gates them, and habitats say where they may stand. The actors themselves live
// in core/actors.hpp.

#include "core/catalog.hpp"
#include "core/iso.hpp"
#include "core/world.hpp"

#include <vector>

namespace lc {

// Terrain and item counts over an area, from the world's per-chunk tallies.
struct Tally {
    std::vector<int> terrain;
    std::vector<int> items;
};
// Sums the counts of every chunk overlapping `area` (so the tally is chunk-granular).
void tallyArea(const World& world, const Catalog& cat, TileRect area, Tally& out);

// What the progress loop decides about a visitor beyond its needs: whether it may come at all
// (its season, a rare visitor's recipe and timing) and how many more than `max` nooks allow.
struct VisitorGate {
    bool allowed = true;
    int extra = 0;
};

// How many of this visitor the tallied area attracts (0 when its needs are unmet or it is the
// wrong time of day). `night` is true only in the Night phase: dusk and dawn belong to the day.
[[nodiscard]] int desiredCount(const VisitorDef& def, const Tally& tally, bool night,
                               VisitorGate gate = {});
// Whether a critter of this habitat may stand on the tile containing p.
[[nodiscard]] bool habitatAllows(Habitat h, const World& world, const Catalog& cat, Vec2 p);

} // namespace lc
