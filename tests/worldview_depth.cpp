// Painter's order for the world's elements: valid on random scenes, pieces of a split landmark
// among other items, ground tiles under what stands on them, and fewer page switches with the
// page-aware tie-break.

#include "worldview/order.hpp"

#include <doctest.h>

#include <random>
#include <vector>

using namespace lc;
using namespace lc::worldview;

namespace {

constexpr Iso kIso{32, 16};

// The screen box of a footprint extruded `height` px up, as an item sprite covers it.
FRect boxOf(FRect f, float height) {
    const Vec2 top = kIso.toWorld(f.x0, f.y0);
    const Vec2 right = kIso.toWorld(f.x1, f.y0);
    const Vec2 bottom = kIso.toWorld(f.x1, f.y1);
    const Vec2 left = kIso.toWorld(f.x0, f.y1);
    return {left.x, top.y - height, right.x, bottom.y};
}

// Every pair of overlapping boxes appears in painter's order.
bool valid(const std::vector<OrderItem>& items, const std::vector<std::uint32_t>& order) {
    std::vector<std::size_t> at(items.size());
    for (std::size_t k = 0; k < order.size(); ++k) at[order[k]] = k;
    for (std::size_t i = 0; i < items.size(); ++i)
        for (std::size_t j = i + 1; j < items.size(); ++j) {
            if (!items[i].screen.overlaps(items[j].screen)) continue;
            const bool ij = drawnBefore(items[i], items[j]);
            if (ij != (at[i] < at[j])) return false;
        }
    return true;
}

// Non-overlapping footprints on a grid with random sizes, heights and pages.
std::vector<OrderItem> scene(std::uint32_t seed, int pages) {
    std::mt19937 rng(seed);
    std::vector<OrderItem> items;
    std::vector<int> taken(40 * 40, 0);
    for (int n = 0; n < 400; ++n) {
        const int x = static_cast<int>(rng() % 38);
        const int y = static_cast<int>(rng() % 38);
        const int w = 1 + static_cast<int>(rng() % 3);
        const int h = 1 + static_cast<int>(rng() % 3);
        bool free = true;
        for (int j = y; j < y + h; ++j)
            for (int i = x; i < x + w; ++i)
                free = free && taken[static_cast<std::size_t>(j * 40 + i)] == 0;
        if (!free) continue;
        for (int j = y; j < y + h; ++j)
            for (int i = x; i < x + w; ++i) taken[static_cast<std::size_t>(j * 40 + i)] = 1;
        const FRect f{static_cast<float>(x), static_cast<float>(y), static_cast<float>(x + w),
                      static_cast<float>(y + h)};
        items.push_back({f, boxOf(f, static_cast<float>(rng() % 120)),
                         static_cast<std::uint16_t>(rng() % static_cast<unsigned>(pages)), false});
    }
    return items;
}

} // namespace

TEST_CASE("depth: page-aware order is a valid painter's order with fewer page switches") {
    PageOrder sorter;
    std::vector<std::uint32_t> order;
    int awareSwitches = 0;
    int plainSwitches = 0;
    for (std::uint32_t seed = 1; seed <= 6; ++seed) {
        std::vector<OrderItem> items = scene(seed, 3);
        sorter.sort(items, 128, order);
        REQUIRE(order.size() == items.size());
        CHECK(valid(items, order));
        awareSwitches += pageSwitches(items, order);
        // The same scene with every element on one page sorts by depth alone.
        std::vector<OrderItem> one = items;
        for (OrderItem& it : one) it.page = 0;
        std::vector<std::uint32_t> plain;
        sorter.sort(one, 128, plain);
        CHECK(valid(one, plain));
        plainSwitches += pageSwitches(items, plain);
    }
    CHECK(awareSwitches * 2 < plainSwitches);
}

TEST_CASE("depth: a split landmark's pieces sort among the items around and inside it") {
    // A 12 x 6 landmark cut into pieces of at most 8 x 8, with a walk run through it, and
    // single items before, behind and beside it.
    std::vector<OrderItem> items;
    const std::vector<FRect> pieces{
        {10, 10, 18, 13}, {10, 13, 18, 16}, {18, 10, 22, 16}, {10, 16, 22, 17}};
    for (const FRect& p : pieces) items.push_back({p, boxOf(p, 160), 1, false});
    for (const FRect& f : std::vector<FRect>{
             {9, 12, 10, 13}, {23, 12, 24, 13}, {14, 18, 15, 19}, {14, 9, 15, 10}, {22, 9, 23, 10}})
        items.push_back({f, boxOf(f, 60), 0, false});
    PageOrder sorter;
    std::vector<std::uint32_t> order;
    sorter.sort(items, 128, order);
    CHECK(valid(items, order));
    std::vector<std::size_t> at(items.size());
    for (std::size_t k = 0; k < order.size(); ++k) at[order[k]] = k;
    CHECK(at[7] < at[0]); // the item behind the landmark's back piece comes first
    CHECK(at[3] < at[6]); // the front run before the item in front of it
    CHECK(at[1] < at[3]);
}

TEST_CASE("depth: a raised tile goes under what stands on it and over what it hides") {
    const FRect tile{5, 5, 6, 6};
    const OrderItem ground{tile, boxOf(tile, 40), 2, true};
    const OrderItem on{{4, 4, 6, 6}, boxOf({4, 4, 6, 6}, 80), 0, false}; // covers the tile
    const OrderItem behindIt{{3, 5, 4, 6}, boxOf({3, 5, 4, 6}, 30), 0, false};
    CHECK(drawnBefore(ground, on));
    CHECK_FALSE(drawnBefore(on, ground));
    CHECK(drawnBefore(behindIt, ground));
}

namespace {

// Actors on free tiles of a scene: a small square round the feet, a person-sized box.
std::vector<MergeActor> crowd(const std::vector<OrderItem>& items, std::uint32_t seed, int n,
                              std::uint16_t page) {
    std::mt19937 rng(seed);
    std::vector<MergeActor> out;
    while (static_cast<int>(out.size()) < n) {
        const float x = static_cast<float>(rng() % 3800) / 100.0f;
        const float y = static_cast<float>(rng() % 3800) / 100.0f;
        bool free = true;
        for (const OrderItem& it : items)
            free = free && !(x >= it.foot.x0 - 0.2f && x < it.foot.x1 + 0.2f &&
                             y >= it.foot.y0 - 0.2f && y < it.foot.y1 + 0.2f);
        if (!free) continue;
        const FRect f{x - 0.2f, y - 0.2f, x + 0.2f, y + 0.2f};
        const Vec2 a = kIso.toWorld(x, y);
        out.push_back({f, {a.x - 8, a.y - 40, a.x + 8, a.y}, page});
    }
    return out;
}

struct Merged {
    std::vector<int> seq; // >= 0: static element, < 0: -(actor + 1)
};

Merged merged(const std::vector<OrderItem>& items, const std::vector<std::uint32_t>& order,
              const ActorMerge& m) {
    Merged out;
    for (std::size_t k = 0; k <= order.size(); ++k) {
        for (const std::uint32_t a : m.before(k)) out.seq.push_back(-static_cast<int>(a) - 1);
        if (k < order.size()) out.seq.push_back(static_cast<int>(order[k]));
    }
    (void)items;
    return out;
}

} // namespace

TEST_CASE("depth: actors merge into the static order behind and in front of what they meet") {
    for (std::uint32_t seed = 1; seed <= 6; ++seed) {
        const std::vector<OrderItem> items = scene(seed, 3);
        std::vector<std::uint32_t> order;
        PageOrder sorter;
        sorter.sort(items, 64.0f, order);
        const std::vector<MergeActor> actors = crowd(items, seed * 7, 120, 3);
        ActorMerge m;
        m.index(items, order, 64.0f);
        m.plan(
            items, actors, [](std::uint32_t, std::uint32_t) { return 0; },
            [](std::uint32_t) { return true; });
        const Merged s = merged(items, order, m);
        REQUIRE(s.seq.size() == items.size() + actors.size());
        std::vector<std::size_t> atS(items.size()), atA(actors.size());
        for (std::size_t k = 0; k < s.seq.size(); ++k)
            (s.seq[k] >= 0 ? atS[static_cast<std::size_t>(s.seq[k])]
                           : atA[static_cast<std::size_t>(-s.seq[k] - 1)]) = k;
        int pairs = 0;
        int wrong = 0;
        for (std::size_t a = 0; a < actors.size(); ++a) {
            const OrderItem ai{actors[a].foot, actors[a].screen, actors[a].page, false};
            for (std::size_t e = 0; e < items.size(); ++e) {
                if (!items[e].screen.overlaps(ai.screen)) continue;
                ++pairs;
                if (drawnBefore(items[e], ai) != (atS[e] < atA[a])) ++wrong;
            }
            for (std::size_t b = a + 1; b < actors.size(); ++b) {
                const OrderItem bi{actors[b].foot, actors[b].screen, actors[b].page, false};
                if (!ai.screen.overlaps(bi.screen)) continue;
                ++pairs;
                if (drawnBefore(ai, bi) != (atA[a] < atA[b])) ++wrong;
            }
        }
        CAPTURE(seed);
        CHECK(pairs > 200);
        // Only where two statics that do not meet disagree about the actor between them.
        CHECK(wrong * 25 <= pairs);
        // The crowd (its own page) costs a handful of page switches, not one per person.
        std::vector<OrderItem> all = items;
        std::vector<std::uint32_t> seq;
        for (const int v : s.seq) {
            if (v >= 0) {
                seq.push_back(static_cast<std::uint32_t>(v));
            } else {
                const MergeActor& a = actors[static_cast<std::size_t>(-v - 1)];
                all.push_back({a.foot, a.screen, a.page, false});
                seq.push_back(static_cast<std::uint32_t>(all.size() - 1));
            }
        }
        const int added = pageSwitches(all, seq) - pageSwitches(items, order);
        MESSAGE("seed " << seed << ": " << wrong << " of " << pairs << " pairs, " << added
                        << " switches for " << actors.size() << " actors");
        CHECK(added <= 60);
    }
}

TEST_CASE("depth: an actor on a floor goes after it, under a roof before it") {
    // One landmark split into two pieces over the actor's tile: a floor and a roof.
    std::vector<OrderItem> items{{{0, 0, 4, 4}, {-64, -40, 64, 64}, 0, false},
                                 {{0, 0, 4, 4}, {-64, -120, 64, 64}, 0, false}};
    std::vector<std::uint32_t> order{0, 1};
    ActorMerge m;
    m.index(items, order, 64.0f);
    const Vec2 a = kIso.toWorld(2.0f, 2.0f);
    std::vector<MergeActor> actors{
        {{1.8f, 1.8f, 2.2f, 2.2f}, {a.x - 8, a.y - 40, a.x + 8, a.y}, 1}};
    m.plan(
        items, actors, [](std::uint32_t e, std::uint32_t) { return e == 0 ? -1 : 1; },
        [](std::uint32_t) { return true; });
    CHECK(m.before(0).empty());
    REQUIRE(m.before(1).size() == 1);
    CHECK(m.before(2).empty());
}
