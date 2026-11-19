#pragma once
// Painter's order for the depth-sorted band (docs/design/draw-order.md §1.4), shared by the world
// and the home scene: items, the pieces of split landmarks, raised ground tiles that hide
// something, named figures and the home, each a box (render/depth.hpp), sorted by the one
// comparator. PageOrder is the exact topological
// order with a page-aware tie-break: among the elements whose predecessors are all drawn, one on
// the texture page already bound is preferred, so page switches (draw calls) stay few. ActorMerge
// puts the moving things into that order each frame by the same comparator. Pure logic (no SDL).

#include "core/iso.hpp"
#include "render/depth.hpp"

#include <cstdint>
#include <span>
#include <utility>
#include <vector>

namespace lc {

struct OrderItem {
    DepthBox box;
    FRect screen; // world px box of everything it draws
    std::uint16_t page = 0;
};

// The edges a sort found between elements whose screens overlap, by element (CSR): what must be
// drawn after each one.
struct OrderGraph {
    std::vector<std::uint32_t> start; // per element, then one past the end
    std::vector<std::uint32_t> next;
    void clear() {
        start.clear();
        next.clear();
    }
};

class PageOrder {
public:
    // Orders `items` so that every pair of overlapping screen boxes is drawn back to front, and
    // keeps the edges in `graph`. Deterministic: ties go to the bound page, then the shallower
    // footprint, then the id. With `groups` (one per item, 0: none), two items of the same
    // non-zero group need no order between them (lights add up in any order; black silhouettes
    // cover alike), which leaves more room to keep a page bound.
    void sort(std::span<const OrderItem> items, float cell, std::vector<std::uint32_t>& order,
              OrderGraph& graph, std::span<const std::uint8_t> groups = {});
    // Cycles the last sort had to break (each a data fault: never hidden, reported).
    [[nodiscard]] int cyclesBroken() const { return cycles_; }
    // The element the first cycle was broken at (its box), when there was one.
    [[nodiscard]] const DepthBox& firstCycle() const { return firstCycle_; }

private:
    ScreenGrid grid_;
    std::vector<FRect> screens_;
    std::vector<std::uint32_t> edgeFrom_;
    std::vector<std::uint32_t> edgeTo_;
    std::vector<std::uint32_t> cursor_;
    std::vector<int> indegree_;
    std::vector<std::uint8_t> done_;
    std::vector<std::vector<std::pair<float, std::uint32_t>>> ready_; // per page, min-heaps
    int cycles_ = 0;
    DepthBox firstCycle_;
};

// Moving things merged into a static order each frame (draw-order.md §1.4): one exact order of
// the actors with the elements they meet, by the comparator. The static order is walked as it is;
// an element that must follow an actor not yet drawn is held back (with whatever must follow it)
// until that actor is drawn, so no pair that overlaps on screen is ever drawn the wrong way round.
// Actors ready to be drawn wait for their own page to be bound while nothing in front of them
// comes next, so a crowd costs a few draw calls. Allocation-free once warm.
class ActorMerge {
public:
    // One step of the frame's sequence: an element of the static order, or an actor.
    struct Step {
        std::uint32_t index; // element (into the items) or actor
        bool actor;
    };

    // Once per static order: its elements, order and graph (`cell`: the screen grid's size).
    void index(std::span<const OrderItem> items, std::span<const std::uint32_t> order,
               const OrderGraph& graph, float cell);
    // Plans this frame: `actors` (boxes, screens, pages) against what is drawn in `view` (world
    // px; an element whose box misses it is culled and orders nothing).
    void plan(std::span<const OrderItem> items, std::span<const OrderItem> actors,
              const FRect& view);
    // Everything to draw this frame, in order.
    [[nodiscard]] std::span<const Step> sequence() const { return seq_; }
    // Positions of the static order drawn this frame, in order (for passes that do not depend on
    // the order: shadows, glow).
    [[nodiscard]] std::span<const std::uint32_t> visible() const { return visible_; }
    // Elements held back behind an actor this frame, and cycles broken (data faults).
    [[nodiscard]] int heldBack() const { return held_; }
    [[nodiscard]] int cyclesBroken() const { return cycles_; }

private:
    void emitElement(std::uint32_t k);
    void emitActor(std::uint32_t a);
    void drain();
    void flushPending(bool all);

    std::span<const OrderItem> items_;
    std::span<const OrderItem> actors_;
    std::vector<std::uint32_t> order_;
    std::vector<std::uint32_t> rank_;             // per element: its position in the order
    std::vector<FRect> placed_;                   // screen boxes by position in the order
    std::vector<std::uint32_t> succStart_, succ_; // static edges by position (CSR)
    ScreenGrid grid_;                             // over the placed boxes, made once per order
    std::vector<std::uint32_t> seen_; // per position: the mark of the actor that last met it
    std::uint32_t tick_ = 1;
    float cell_ = 128;
    // Per frame.
    std::vector<std::uint8_t> drawnAt_;  // per position: drawn this frame
    std::vector<std::uint32_t> visible_; // drawn positions, in order
    std::vector<int> blocked_;           // per position: predecessors not drawn yet (held, actors)
    std::vector<std::uint8_t> state_;    // per position: 0 waiting, 1 held, 2 drawn
    std::vector<std::uint32_t> pairEl_, pairAc_;      // (position, actor) pairs that overlap
    std::vector<std::uint8_t> pairAfter_;             // the actor goes after the element
    std::vector<std::uint32_t> eSuccStart_, eSucc_;   // per position: actors after it
    std::vector<std::uint32_t> aSuccStart_, aSucc_;   // per actor: positions after it
    std::vector<std::uint32_t> aaSuccStart_, aaSucc_; // per actor: actors after it
    std::vector<int> aIndeg_;                         // per actor: what must go first, left
    std::vector<int> aStaticIndeg_;                   // of that, elements
    std::vector<std::uint8_t> aState_;                // 0 waiting, 1 ready, 2 drawn
    std::vector<std::uint32_t> pending_;              // ready actors
    std::vector<std::uint32_t> released_;             // held elements free to go
    ScreenGrid actorGrid_;
    std::vector<FRect> actorScreens_;
    std::vector<std::uint32_t> fill_;
    std::vector<Step> seq_;
    int bound_ = -1;     // the page bound by the last step
    bool added_ = false; // actors became ready since the last check
    int held_ = 0;
    int cycles_ = 0;
};

// The order oracle on boxes (draw-order.md §6.1): how many pairs of `items` and `actors` drawn in
// `seq` overlap on screen yet are drawn the other way round from the comparator (without
// `actorPairs`, pairs of two actors are not counted: where a stacked cycle had to be broken,
// that is the edge the merge gives up). Zero is right. For tests and the debug view (allocates).
[[nodiscard]] int orderViolations(std::span<const OrderItem> items,
                                  std::span<const OrderItem> actors,
                                  std::span<const ActorMerge::Step> seq, bool actorPairs = true,
                                  std::pair<DepthBox, DepthBox>* first = nullptr);

// The cycles among `items` whose screens overlap (draw-order.md §6.3): each as the elements it
// runs through, in order, one list per cycle found (at most `limit`). Empty when the order has
// none. For the whole-world scan and tests (allocates).
[[nodiscard]] std::vector<std::vector<std::uint32_t>> orderCycles(std::span<const OrderItem> items,
                                                                  float cell, std::size_t limit);

// Page switches along an order (what each one costs is a draw call).
[[nodiscard]] int pageSwitches(std::span<const OrderItem> items,
                               std::span<const std::uint32_t> order);

} // namespace lc
