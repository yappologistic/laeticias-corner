#include "core/progress.hpp"

#include <algorithm>

namespace lc {

Progress::Progress(const Catalog& cat)
    : items(cat.items.size(), 0), terrain(cat.terrain.size(), 0), frames(cat.frames.size(), 0),
      newItems(cat.items.size(), 0), newTerrain(cat.terrain.size(), 0), wishes(cat.wishes.size()),
      clues(cat.visitors.size(), 0), nooks(cat.nooks.size(), 0) {
    unlock(cat.start);
}

void Progress::unlock(const Reward& r, bool fresh) {
    for (const int i : r.items) {
        const auto k = static_cast<std::size_t>(i);
        if (fresh && items[k] == 0) newItems[k] = 1;
        items[k] = 1;
    }
    for (const int t : r.terrain) {
        const auto k = static_cast<std::size_t>(t);
        if (fresh && terrain[k] == 0) newTerrain[k] = 1;
        terrain[k] = 1;
    }
    if (r.frame >= 0) frames[static_cast<std::size_t>(r.frame)] = 1;
    if (r.clue >= 0) clues[static_cast<std::size_t>(r.clue)] = 1;
}

void Progress::unlock(const PieceSet& s) {
    for (const int i : s.items) items[static_cast<std::size_t>(i)] = 1;
    for (const int t : s.terrain) terrain[static_cast<std::size_t>(t)] = 1;
    for (const int f : s.frames) frames[static_cast<std::size_t>(f)] = 1;
}

void Progress::unlockEverything(const Catalog& cat) {
    std::ranges::fill(items, 1);
    std::ranges::fill(terrain, 1);
    std::ranges::fill(frames, 1);
    for (std::size_t v = 0; v < cat.visitors.size(); ++v) clues[v] = cat.visitors[v].rare ? 1 : 0;
}

int Progress::nooksFound() const {
    return static_cast<int>(std::ranges::count(nooks, std::uint8_t{1}));
}

} // namespace lc
