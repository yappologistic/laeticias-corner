#pragma once
// The world-global progress of one world save: unlocked pieces, wishes, clues, discovered nooks,
// harvests and the opened land stage (docs/design/living-corner.md §2.1). Saved; the derived
// state (nook instances, music layers) is recomputed.

#include "core/catalog.hpp"

#include <cstdint>
#include <vector>

namespace lc {

enum class WishState : std::uint8_t { Waiting, Open, Done };

struct WishProgress {
    WishState state = WishState::Waiting;
    double snoozedUntil = -1; // play time at which a snoozed wish may return; -1: not snoozed
};

struct Progress {
    explicit Progress(const Catalog& cat);

    std::vector<std::uint8_t> items; // unlocked, per item
    std::vector<std::uint8_t> terrain;
    std::vector<std::uint8_t> frames;
    std::vector<std::uint8_t> newItems; // unlocked but its "new" dot not seen yet
    std::vector<std::uint8_t> newTerrain;
    std::vector<WishProgress> wishes;
    std::vector<int> open;           // open wishes, in the order they were offered
    std::vector<int> granted;        // granted wishes, in the order they were granted
    double lastOffer = 0;            // play time of the last offer or grant
    std::vector<std::uint8_t> clues; // per visitor
    std::vector<std::uint8_t> nooks; // discovered, per nook
    int harvests = 0;
    int lastHarvestDay = -1;
    int stage = 0; // highest open land stage (home region)

    // Unlocks pieces; with `fresh`, ones not unlocked before get a "new" dot.
    void unlock(const Reward& r, bool fresh);
    void unlock(const PieceSet& s);
    void unlockEverything(const Catalog& cat);
    [[nodiscard]] int nooksFound() const;
};

} // namespace lc
