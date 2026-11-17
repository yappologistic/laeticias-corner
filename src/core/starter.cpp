#include "core/starter.hpp"

#include "core/edit.hpp"

#include <string_view>

namespace lc {
namespace {

struct Strip {
    std::string_view terrain;
    int y;
    int x0;
    int x1; // inclusive
};

struct Placement {
    std::string_view item;
    int x;
    int y;
    int variant;
};

// A pond with reeds and lily pads, a path wandering up to it, a meadow patch with flowers and a
// lamp by a bench. Three flower patches (butterflies want four) and a missing cottage leave
// obvious first things to discover.
constexpr Strip kTerrain[] = {
    {"meadow", 2, 3, 6},  {"meadow", 3, 2, 7},   {"meadow", 4, 2, 7},  {"meadow", 5, 3, 6},
    {"meadow", 6, 4, 5},  {"water", 4, 14, 15},  {"water", 5, 13, 16}, {"water", 6, 13, 16},
    {"water", 7, 14, 16}, {"water", 8, 15, 15},  {"path", 19, 9, 9},   {"path", 18, 9, 9},
    {"path", 17, 9, 9},   {"path", 16, 9, 10},   {"path", 15, 10, 10}, {"path", 14, 10, 10},
    {"path", 13, 10, 10}, {"path", 12, 10, 11},  {"path", 11, 11, 11}, {"path", 10, 11, 12},
    {"path", 9, 12, 13},  {"cobble", 8, 12, 13},
};

constexpr Placement kItems[] = {
    {"oak", 2, 9, 0},           {"oak", 4, 14, 1},
    {"oak", 7, 1, 2},           {"oak", 17, 17, 3},
    {"pine", 1, 4, 0},          {"pine", 2, 16, 1},
    {"pine", 17, 13, 2},        {"pine", 0, 11, 3},
    {"blossom", 7, 8, 0},       {"blossom", 15, 11, 1},
    {"bush", 5, 10, 0},         {"bush", 9, 4, 1},
    {"berry_bush", 13, 15, 0},  {"flowers_red", 4, 3, 0},
    {"flowers_white", 5, 4, 1}, {"flowers_violet", 3, 5, 2},
    {"tall_grass", 2, 7, 0},    {"tall_grass", 17, 9, 1},
    {"reeds", 12, 5, 0},        {"reeds", 16, 5, 1},
    {"lily_pads", 14, 5, 0},    {"lily_pads", 15, 7, 2},
    {"rock", 12, 3, 0},         {"rock", 18, 7, 1},
    {"stump", 6, 16, 0},        {"mushrooms", 3, 13, 0},
    {"bench", 13, 9, 0},        {"lamp", 12, 11, 0},
};

} // namespace

World makeStarterWorld(const Catalog& cat) {
    World world(cat);
    for (const Strip& s : kTerrain) {
        const auto t = cat.findTerrain(s.terrain);
        if (!t) continue;
        for (int x = s.x0; x <= s.x1; ++x)
            if (world.inBounds({x, s.y})) world.setTerrain({x, s.y}, *t);
    }
    for (const Placement& p : kItems) {
        const auto type = cat.findItem(p.item);
        if (!type) continue;
        const int variant = p.variant % cat.items[static_cast<std::size_t>(*type)].count;
        const Item item = makeItem(cat, *type, variant, {p.x, p.y});
        if (canPlace(world, cat, item) == PlaceResult::Ok) world.addItem(item);
    }
    return world;
}

} // namespace lc
