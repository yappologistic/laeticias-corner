#pragma once
// Things that grow (veggie beds): stages advance with play time, faster in rain and in a kitchen
// garden, resting when the season rests them unless something shelters them
// (docs/design/living-corner.md R4.4). Ripe things stay ripe.

#include "core/catalog.hpp"
#include "core/world.hpp"

namespace lc {

// How fast an item at `rect` grows now: rain (not snow) doubles it, `nook` multiplies it, and a
// resting season stops it unless a sheltering item is near enough.
[[nodiscard]] float growthRate(const World& world, const Catalog& cat, TileRect rect, bool raining,
                               float seasonGrowth, float nook);
// Advances item `index` by `seconds` at `rate`; true when it reached a new stage.
bool grow(World& world, const Catalog& cat, std::size_t index, float seconds, float rate);
// Whether an item is ripe and can be picked.
[[nodiscard]] bool ripe(const Catalog& cat, const Item& item);
// Picks a ripe item: it starts again from its first stage.
void harvest(World& world, std::size_t index);

} // namespace lc
