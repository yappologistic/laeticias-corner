#pragma once
// What to draw over a stretch of the world, in painter's order (docs/design/world-tech.md §4.3,
// §4.4): the items and landmark pieces whose sprites meet a rectangle, with the raised tiles that
// hide one of them, sorted by PageOrder. Gathering only reads the map and the sprite tables, so
// it runs on a worker thread (Prep) while the main thread draws; the main thread never sorts.

#include "world/world_map.hpp"
#include "worldview/order.hpp"
#include "worldview/world_sprites.hpp"

#include <condition_variable>
#include <cstdint>
#include <deque>
#include <mutex>
#include <thread>
#include <vector>

namespace lc::worldview {

struct Elem {
    const VariantLook* look = nullptr; // null for a ground tile
    std::uint32_t item = 0;
    std::int16_t piece = -1; // -1: the whole sprite
    bool ground = false;     // a raised tile drawn over what it hides
    bool first = false;      // the item's first element: it draws the shadow and the glow
    TilePos tile;            // the item's origin, or the ground tile
    Vec2 anchor;             // world px, raised by the level
};

struct Gathered {
    std::vector<Elem> elems;
    std::vector<OrderItem> items; // per element: footprint, screen box, page
    std::vector<std::uint32_t> order;
    void clear() {
        elems.clear();
        items.clear();
        order.clear();
    }
};

// The tiles whose items can draw into `clip` (world px): sprites rise from their footprints by
// at most span.up and overhang them by span.left/right/down.
[[nodiscard]] TileRect gatherTiles(const FRect& clip, const Reach& span, Iso iso);

class Gatherer {
public:
    Gatherer(const world::WorldMap& map, const WorldSprites& sprites);
    // Elements over `tiles` whose boxes meet `clip`, sorted, into `out` (cleared first).
    void run(TileRect tiles, const FRect& clip, Gathered& out);

private:
    const world::WorldMap& map_;
    const WorldSprites& sprites_;
    Iso iso_;
    int lvl_;
    std::vector<world::DrawPiece> pieces_;
    std::vector<std::uint32_t> stamp_; // per map item: the pass it was last taken in
    std::uint32_t pass_ = 0;
    PageOrder sorter_;
};

// Gathering jobs, run on a worker thread when asynchronous (else at once, on the caller's).
class Prep {
public:
    struct Job {
        std::uint64_t tag = 0;
        TileRect tiles;
        FRect clip;
    };

    Prep(const world::WorldMap& map, const WorldSprites& sprites, bool async);
    ~Prep();
    Prep(const Prep&) = delete;
    Prep& operator=(const Prep&) = delete;

    void request(const Job& job);
    // Moves the finished result for `tag` into `out`; false while it is not ready.
    [[nodiscard]] bool take(std::uint64_t tag, Gathered& out);
    // Gathers on the calling thread (when nothing usable exists yet).
    void now(TileRect tiles, const FRect& clip, Gathered& out) { mine_.run(tiles, clip, out); }

private:
    struct Done {
        std::uint64_t tag = 0;
        Gathered result;
    };
    void work(const std::stop_token& stop);

    bool async_;
    Gatherer mine_;   // the caller's thread
    Gatherer theirs_; // the worker's
    std::mutex mutex_;
    std::condition_variable_any wake_;
    std::deque<Job> queue_;
    std::vector<Done> done_;
    std::jthread worker_; // last: joined first
};

} // namespace lc::worldview
