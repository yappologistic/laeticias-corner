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
