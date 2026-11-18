#pragma once
// Where the region files' named figures stand while their routines wait for the actor-scale
// round (docs/design/world-tech.md §4.9): at the place their first routine walks to (an item's
// slot or a graph node in their region), else near the region's marker; on the nearest open
// walkable tile with no item on it and no landmark in front of it on screen (so nothing hides
// them), each on a tile of its own. Pure logic.

#include "world/loader.hpp"

#include <string>
#include <vector>

namespace lc::world {

struct FigurePlace {
    int region = -1;
    std::string actor;  // set actor id, e.g. "rome.hadrian"
    std::string card;   // card id in the region file, or empty
    std::string sprite; // the actor's sprite prefix, e.g. "figure/rome.hadrian"
    Vec2 at;            // continuous tile coordinates (x.5: a tile's centre)
    int level = 0;
};

[[nodiscard]] std::vector<FigurePlace> placeFigures(const LoadedWorld& world);

} // namespace lc::world
