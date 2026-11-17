#pragma once
// Land you earn: the home region opens in stages (catalog `land`). Tiles of stages not yet open
// are wild: no building, no walking, base terrain only. A stage opening writes its reveal.

#include "core/catalog.hpp"
#include "core/world.hpp"

#include <vector>

namespace lc {

// The stage a tile belongs to; tiles outside every stage rectangle (larger test maps) count as
// the first stage.
[[nodiscard]] int stageAt(const Catalog& cat, TilePos p);
// Marks every tile of a stage after `opened` wild and the rest open.
void applyLand(World& world, const Catalog& cat, int opened);
// Opens one stage: clears its wild flags and writes its revealed terrain and items (items only
// onto tiles where they fit). Appends the items it placed to `placed`.
void openStage(World& world, const Catalog& cat, int stage, std::vector<Item>& placed);
// Pages needed for the stage after `opened`; -1 when every stage is open.
[[nodiscard]] int nextStagePages(const Catalog& cat, int opened);
// Bounding rectangle of the open tiles.
[[nodiscard]] TileRect openBounds(const Catalog& cat, int opened, const World& world);

} // namespace lc
