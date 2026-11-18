#pragma once
// Painter's order for the world's elements (docs/design/world-tech.md §4.4): items, the pieces of
// split landmarks, and raised ground tiles that hide something behind them. The exact topological
// order of render/depth.hpp, with a page-aware tie-break: among the elements whose predecessors
// are all drawn, one on the texture page already bound is preferred, so page switches (draw
// calls) stay few. Pure logic (no SDL).

#include "core/iso.hpp"
#include "render/depth.hpp"

#include <cstdint>
#include <span>
#include <vector>

namespace lc::worldview {

struct OrderItem {
    FRect foot;   // footprint, tile coordinates
    FRect screen; // world px box of everything it draws
    std::uint16_t page = 0;
    bool ground = false; // a raised ground tile (drawn under anything standing on it)
};

// True when a must be drawn before b: the footprint rule, except that ground goes under any
// item whose footprint covers it.
[[nodiscard]] bool drawnBefore(const OrderItem& a, const OrderItem& b);

class PageOrder {
public:
    // Orders `items` so that every pair of overlapping screen boxes is drawn back to front.
    // Deterministic: ties go to the bound page, then the shallower footprint, then the index.
    void sort(std::span<const OrderItem> items, float cell, std::vector<std::uint32_t>& order);

private:
    ScreenGrid grid_;
    std::vector<FRect> screens_;
    std::vector<std::uint32_t> edgeFrom_;
    std::vector<std::uint32_t> edgeTo_;
    std::vector<std::uint32_t> start_;
    std::vector<std::uint32_t> next_;
    std::vector<std::uint32_t> cursor_;
    std::vector<int> indegree_;
    std::vector<std::uint8_t> done_;
    std::vector<std::vector<std::pair<float, std::uint32_t>>> ready_; // per page, min-heaps
};

// Moving things merged into a static order each frame without re-sorting it (world-tech §4.4):
// each actor goes after every static element behind it and before every one in front of it
// whose screen boxes meet its own, and before or after an overlapping actor by the footprint
// rule. Within those bounds actors wait for their own page to be bound, so a crowd costs a few
// draw calls, not one per person. Allocation-free once warm.
struct MergeActor {
    FRect foot;   // a small square round its feet, tile coordinates
    FRect screen; // world px box of what it draws
    std::uint16_t page = 0;
};

class ActorMerge {
public:
    // Once per static order: its ranks and screen boxes (`cell`: the screen grid's size).
    void index(std::span<const OrderItem> items, std::span<const std::uint32_t> order, float cell);
    // Plans this frame's actors. `relation(element, actor)` says how a static element whose box
    // meets an actor's stands to it: -1 drawn before it, +1 after it, 0 by the footprint rule.
    // `view`: world px drawn this frame; an element whose box misses it is culled (and binds no
    // page).
    template <typename Rel>
    void plan(std::span<const OrderItem> items, std::span<const MergeActor> actors, Rel&& relation,
              const FRect& view);
    // The actors to draw just before position k of the static order (k == order size: after the
    // last), in draw order.
    [[nodiscard]] std::span<const std::uint32_t> before(std::size_t k) const {
        return std::span(emit_).subspan(emitStart_[k], emitStart_[k + 1] - emitStart_[k]);
    }
    // Positions of the static order drawn this frame, in order: all the frame needs to visit.
    [[nodiscard]] std::span<const std::uint32_t> visible() const { return visible_; }

private:
    void bounds(std::span<const OrderItem> items, std::span<const MergeActor> actors);
    void schedule(std::span<const OrderItem> items, std::span<const MergeActor> actors,
                  const std::vector<std::uint8_t>& drawnAt);
    void flush(std::uint32_t a, std::size_t k);

    std::vector<std::uint32_t> order_;
    std::vector<std::uint32_t> rank_; // per element: its position in the order
    std::vector<FRect> placed_;       // screen boxes by position in the order
    ScreenGrid grid_;                 // over them, made once per order
    std::vector<std::uint32_t> seen_; // per position: the mark of the actor that last met it
    std::uint32_t tick_ = 1;
    // Per frame.
    std::vector<int> lo_, hi_;          // per actor: positions it may be drawn before
    std::vector<int> rel_;              // per candidate pair, from the caller
    std::vector<std::uint32_t> pairEl_; // candidates (element, actor)
    std::vector<std::uint32_t> pairAc_;
    ScreenGrid actorGrid_;
    std::vector<FRect> actorScreens_;
    std::vector<std::uint32_t> predStart_, pred_, predFill_; // actors behind and overlapping
    std::vector<std::uint32_t> byDepth_, byLo_;
    std::vector<std::uint32_t> depthRank_; // per actor: its place in byDepth_
    std::vector<std::uint32_t> pending_;
    std::vector<std::uint8_t> state_; // 0 waiting, 1 pending, 2 drawn
    std::vector<std::uint8_t> drawnAt_;
    std::vector<std::uint32_t> visible_;
    float cell_ = 128;
    std::vector<std::pair<std::size_t, std::uint32_t>> out_; // (position, actor) in draw order
    std::vector<std::uint32_t> emit_;
    std::vector<std::uint32_t> emitStart_;
};

template <typename Rel>
void ActorMerge::plan(std::span<const OrderItem> items, std::span<const MergeActor> actors,
                      Rel&& relation, const FRect& view) {
    const std::size_t na = actors.size();
    lo_.assign(na, 0);
    hi_.assign(na, static_cast<int>(order_.size()));
    pairEl_.clear();
    pairAc_.clear();
    rel_.clear();
    // Only what is drawn this frame matters: culled elements order nothing. The boxes lie in
    // draw order, so this is one pass over contiguous memory.
    drawnAt_.assign(order_.size(), 0);
    visible_.clear();
    for (std::size_t k = 0; k < order_.size(); ++k)
        if (placed_[k].overlaps(view)) {
            drawnAt_[k] = 1;
            visible_.push_back(static_cast<std::uint32_t>(k));
        }
    // Actors meet what is drawn through the grid made with the order, each element once.
    if (tick_ > 0xFFFFFFFFu - na - 1) {
        seen_.assign(seen_.size(), 0);
        tick_ = 1;
    }
    for (std::uint32_t a = 0; a < na; ++a) {
        const std::uint32_t mark = tick_ + a;
        grid_.query(actors[a].screen, [&](std::uint32_t k) {
            if (drawnAt_[k] == 0 || seen_[k] == mark || !placed_[k].overlaps(actors[a].screen))
                return;
            seen_[k] = mark;
            const std::uint32_t e = order_[k];
            pairEl_.push_back(e);
            pairAc_.push_back(a);
            rel_.push_back(static_cast<int>(relation(e, a)));
        });
    }
    tick_ += static_cast<std::uint32_t>(na) + 1;
    bounds(items, actors);
    schedule(items, actors, drawnAt_);
}

// Page switches along an order (what each one costs is a draw call).
[[nodiscard]] int pageSwitches(std::span<const OrderItem> items,
                               std::span<const std::uint32_t> order);

} // namespace lc::worldview
