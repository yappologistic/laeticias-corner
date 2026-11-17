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

// The scene is laid out on a small design grid and centred on whatever map the catalog asks for.
constexpr int kDesignSize = 28;

// A meadow at the top with three flower patches (butterflies want four), a pond with reeds and
// lily pads on the right, a path wandering up from the south rim to a cobbled spot by the pond
// with a bench and a lamp, and groves framing the edges. The open ground left of the path is
// waiting for a cottage.
constexpr Strip kTerrain[] = {
    {"meadow", 2, 9, 12},   {"meadow", 3, 8, 13},  {"meadow", 4, 7, 14},  {"meadow", 5, 7, 14},
    {"meadow", 6, 8, 13},   {"water", 6, 19, 21},  {"meadow", 7, 9, 12},  {"water", 7, 18, 22},
    {"water", 8, 18, 23},   {"water", 9, 17, 23},  {"water", 10, 17, 22}, {"water", 11, 18, 21},
    {"cobble", 12, 16, 18}, {"water", 12, 20, 21}, {"path", 13, 15, 15},  {"cobble", 13, 16, 18},
    {"path", 14, 15, 15},   {"path", 15, 14, 15},  {"path", 16, 14, 14},  {"path", 17, 13, 14},
    {"path", 18, 13, 13},   {"path", 19, 12, 13},  {"path", 20, 12, 12},  {"path", 21, 11, 12},
    {"path", 22, 11, 11},   {"path", 23, 10, 11},  {"path", 24, 10, 10},  {"path", 25, 9, 10},
    {"path", 26, 9, 9},     {"path", 27, 9, 9}};

constexpr Placement kItems[] = {{"oak", 3, 1, 0},
                                {"pine", 1, 3, 1},
                                {"oak", 5, 0, 2},
                                {"pine", 1, 14, 0},
                                {"oak", 2, 17, 1},
                                {"pine", 0, 19, 2},
                                {"oak", 3, 20, 3},
                                {"bush", 4, 16, 0},
                                {"mushrooms", 3, 18, 0},
                                {"stump", 5, 21, 0},
                                {"pine", 24, 1, 0},
                                {"oak", 26, 3, 1},
                                {"pine", 22, 2, 2},
                                {"blossom", 25, 6, 1},
                                {"oak", 22, 20, 0},
                                {"blossom", 20, 22, 2},
                                {"pine", 24, 23, 3},
                                {"berry_bush", 21, 18, 0},
                                {"bush", 18, 24, 2},
                                {"flowers_red", 10, 3, 0},
                                {"flowers_white", 11, 5, 1},
                                {"flowers_violet", 9, 4, 2},
                                {"blossom", 14, 4, 0},
                                {"bush", 7, 7, 1},
                                {"tall_grass", 6, 5, 0},
                                {"tall_grass", 13, 8, 1},
                                {"reeds", 17, 7, 0},
                                {"reeds", 23, 9, 1},
                                {"reeds", 21, 12, 2},
                                {"lily_pads", 19, 8, 0},
                                {"lily_pads", 21, 10, 2},
                                {"rock", 16, 9, 0},
                                {"rock", 24, 11, 1},
                                {"bench", 16, 11, 0},
                                {"lamp", 19, 12, 0},
                                {"tall_grass", 13, 22, 2},
                                {"rock", 12, 25, 2},
                                {"bush", 8, 24, 1},
                                {"mushrooms", 14, 19, 1}};

} // namespace

World makeStarterWorld(const Catalog& cat) {
    World world(cat);
    const TilePos o{(world.width() - kDesignSize) / 2, (world.height() - kDesignSize) / 2};
    for (const Strip& s : kTerrain) {
        const auto t = cat.findTerrain(s.terrain);
        if (!t) continue;
        for (int x = s.x0; x <= s.x1; ++x) {
            const TilePos p{o.x + x, o.y + s.y};
            if (world.hasGround(p)) world.setTerrain(p, *t);
        }
    }
    for (const Placement& p : kItems) {
        const auto type = cat.findItem(p.item);
        if (!type) continue;
        const int variant = p.variant % cat.items[static_cast<std::size_t>(*type)].count;
        const Item item = makeItem(cat, *type, variant, {o.x + p.x, o.y + p.y});
        if (canPlace(world, cat, item) == PlaceResult::Ok) world.addItem(item);
    }
    return world;
}

} // namespace lc
