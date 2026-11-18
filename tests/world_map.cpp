// The resident world on a small synthetic world built from the "tst" fixture set: composition,
// item and piece queries, walking with levels, stairs and decks, slots, region themes, the home
// delta and the road graph.

#include "world/world_map.hpp"

#include "core/starter.hpp"
#include "world/road_graph.hpp"
#include "world_support.hpp"

#include <doctest.h>

#include <algorithm>
#include <set>

using namespace lc;
using namespace lc::world;
using namespace lc::wtest;

namespace {

bool contains(const std::vector<std::string>& lines, const std::string& s) {
    return std::ranges::any_of(
        lines, [&](const std::string& l) { return l.find(s) != std::string::npos; });
}

// Base layer tables.
enum : std::uint8_t { kGrass, kPool, kPaving };
enum : std::uint8_t { kWild, kMarket, kTemple, kHomeReserved };
enum : std::uint16_t {
    kOak,
    kHouse,
    kHall,
    kStool,
    kStair,
    kGrand,
    kJetty,
    kWall,
    kGhost,
    kWorldOak,
    kCottage
};

struct Fixture {
    std::unique_ptr<Content> content = tstContent();
    WorldFile wf = tstWorldFile();
    LayerFile base;
    LayerFile top;
    Diagnostics diag;
    std::unique_ptr<WorldMap> map;

    Fixture() {
        base =
            blankLayer(0, 0, 64, 96, {"tst.grass", "tst.pool", "tst.paving"},
                       {"wild/land", "town/market", "town/temple", "home/reserved"},
                       {"oak", "tst.house", "tst.hall", "tst.stool", "tst.stair", "tst.grand_stair",
                        "tst.jetty", "tst.wall", "tst.ghost", "world.t_oak", "cottage"});
        for (int y = 0; y < 96; ++y)
            for (int x = 0; x < 64; ++x) {
                std::uint8_t level = 0;
                std::uint8_t district = x < 32 && y < 32 ? kMarket : kWild;
                std::uint8_t terrain = kGrass;
                if (x >= 20 && x < 24 && y >= 40 && y < 44) terrain = kPool;
                if (x == 19 && y >= 40 && y < 44) level = 1;           // a bank one level up
                if (x >= 30 && x < 40 && y >= 40 && y < 50) level = 1; // a terrace
                if (x >= 53 && x < 57 && y >= 18 && y < 25) level = 2; // above the grand stair
                if (x == 5 && y == 50) level = kImpassable;
                if (x >= 40 && x < 48 && y >= 60 && y < 68) district = kHomeReserved;
                setCell(base, x, y, terrain, level, district);
            }
        setCell(base, 63, 95, kCellNoGround, 0, 0);
        addItem(base, 2, 50, kOak, 0);
        addItem(base, 10, 50, kHouse, 0); // dropped by the top layer
        addItem(base, 2, 2, kHall, 0);    // 10 x 4: a big item
        addItem(base, 6, 5, kStool, 1);   // furniture on one of the hall's walk tiles
        addItem(base, 31, 50, kStair, 0); // faces +y: foot (31, 52), head (31, 49) on the terrace
        addItem(base, 50, 20, kGrand, 0);
        addItem(base, 20, 41, kJetty, 0);
        addItem(base, 40, 10, kWall, 0);
        addItem(base, 41, 10, kWall, 0);
        addItem(base, 41, 11, kWall, 0);
        addItem(base, 45, 5, kStool, 5);   // variant out of range
        addItem(base, 5, 80, kStair, 0);   // on flat ground: nowhere to climb to
        addItem(base, 7, 7, kGhost, 0);    // set with a catalog: an error
        addItem(base, 8, 8, kWorldOak, 0); // set without a catalog: a warning
        addItem(base, 20, 70, kHouse, 0);
        addItem(base, 25, 70, kCottage, 0);
        addItem(base, 44, 64, kOak, 0);   // inside the home rect
        addItem(base, 39, 59, kHouse, 0); // touches the home rect
        top = blankLayer(8, 48, 8, 8, {"tst.paving"}, {"town/temple"}, {"tst.stool"});
        setCell(top, 11, 51, 0, 0, 0);
        setCell(top, 12, 52, kCellNoGround, 3, 0);
        addItem(top, 14, 54, 0, 0);
        const std::vector<LayerInput> layers{{"base", &base}, {"town", &top}};
        map = std::make_unique<WorldMap>(wf, *content, layers, diag);
    }

    [[nodiscard]] int find(const std::string& id, TilePos at) const {
        for (std::size_t i = 0; i < map->items().size(); ++i) {
            const Placed& p = map->items()[i];
            if (map->info(p).id == id && p.x == at.x && p.y == at.y) return static_cast<int>(i);
        }
        return -1;
    }
};

} // namespace

TEST_CASE("map: layers compose by the world-tech rule") {
    const Fixture f;
    const WorldMap& m = *f.map;
    CHECK(m.width() == 64);
    CHECK(m.height() == 96);
    CHECK(m.chunksX() == 2);
    CHECK(m.chunksY() == 3);
    CHECK(m.layers() == std::vector<std::string>{"base", "town"});
    CHECK(m.terrainInfo(m.terrainAt({11, 51})).id == "tst.paving");
    CHECK(m.districtName(m.districtAt({11, 51})) == "town/temple");
    CHECK(m.regionAt({11, 51}) == f.wf.findRegion("town"));
    CHECK(m.terrainAt({12, 52}) == kNone);
    CHECK(m.districtAt({12, 52}) == kNone);
    CHECK(m.level({12, 52}) == 3);
    CHECK(m.regionAt({12, 52}) == -1);
    CHECK(m.terrainInfo(m.terrainAt({13, 53})).id == "tst.grass"); // transparent in the top layer
    CHECK(m.regionAt({13, 53}) == f.wf.findRegion("wild"));
    CHECK(m.regionAt({5, 5}) == f.wf.findRegion("town"));
    CHECK(m.terrainAt({63, 95}) == kNone);
    CHECK(impassableBit(m.levelByte({5, 50})));
    CHECK(m.findDistrict("town/market") >= 0);
    CHECK(m.findDistrict("nowhere") == -1);
    // The house under a set cell of the top layer is dropped; untouched items stay.
    CHECK(f.find("tst.house", {10, 50}) == -1);
    CHECK(f.find("oak", {2, 50}) >= 0);
    const int stool = f.find("tst.stool", {14, 54});
    REQUIRE(stool >= 0);
    CHECK(m.items()[std::size_t(stool)].layer == 1);
    CHECK(contains(
        f.diag.warnings,
        "layers/town.lcw drops 1 item(s) of base under its cells (first at grid (10, 50))"));
}

TEST_CASE("map: unknown ids are skipped, wrong variants reported") {
    const Fixture f;
    const auto& u = f.map->unresolved();
    REQUIRE(u.size() == 2);
    CHECK(u[0] == std::pair<std::string, int>{"tst.ghost", 1});
    CHECK(u[1] == std::pair<std::string, int>{"world.t_oak", 1});
    CHECK(
        contains(f.diag.errors, "layers/base.lcw: item id 'tst.ghost' is in no catalog: 1 placed"));
    CHECK(contains(f.diag.warnings,
                   "item id 'world.t_oak' is in no catalog (set 'world' has no catalog yet)"));
    CHECK(contains(f.diag.errors, "tst.stool placed with variant 5, but its catalog has 2 (1 "
                                  "placed, first at grid (45, 5))"));
    CHECK(contains(f.diag.errors,
                   "tst.stair at grid (5, 80): the tiles beyond its head are not 1 level(s)"));
    CHECK(f.find("tst.ghost", {7, 7}) == -1);
}

TEST_CASE("map: item queries find each item once, big ones from any chunk") {
    const Fixture f;
    const WorldMap& m = *f.map;
    const int hall = f.find("tst.hall", {2, 2});
    REQUIRE(hall >= 0);
    int seen = 0;
    m.forEachItemIn({11, 5, 12, 6},
                    [&](std::uint32_t i, const Placed&) { seen += int(i) == hall; });
    CHECK(seen == 1);
    // Against brute force on rectangles across chunk borders.
    for (int k = 0; k < 200; ++k) {
        const int x0 = (k * 37) % 64 - 4;
        const int y0 = (k * 53) % 96 - 4;
        const TileRect r{x0, y0, x0 + 1 + k % 23, y0 + 1 + (k * 7) % 31};
        std::multiset<std::uint32_t> got;
        m.forEachItemIn(r, [&](std::uint32_t i, const Placed&) { got.insert(i); });
        std::multiset<std::uint32_t> want;
        for (std::uint32_t i = 0; i < m.items().size(); ++i)
            if (m.items()[i].rect().intersects(r.clipped(m.bounds()))) want.insert(i);
        CHECK(got == want);
    }
    CHECK(m.itemAt({3, 3}) == hall);
    CHECK(m.itemAt({0, 0}) == -1);
}

TEST_CASE("map: pieces of split items come out in depth-key order") {
    const Fixture f;
    const WorldMap& m = *f.map;
    std::vector<DrawPiece> out;
    m.piecesIn({0, 0, 64, 32}, out);
    int hallPieces = 0;
    bool floorSeen = false;
    for (std::size_t i = 0; i < out.size(); ++i) {
        const Placed& p = m.items()[out[i].item];
        if (m.info(p).id == "tst.hall") {
            ++hallPieces;
            CHECK(out[i].piece >= 0);
        }
        if (m.info(p).id == "tst.grand_stair" && out[i].piece == 1) {
            floorSeen = out[i].floor;
            CHECK(out[i].rect == TileRect{50, 21, 53, 22});
        }
        if (i > 0) {
            const auto key = [](const DrawPiece& d) {
                return d.rect.x0 + d.rect.x1 + d.rect.y0 + d.rect.y1;
            };
            CHECK(key(out[i - 1]) <= key(out[i]));
        }
    }
    CHECK(hallPieces == 4);
    CHECK(floorSeen);
    // A view over one corner of the hall gets only the pieces it overlaps.
    m.piecesIn({9, 5, 10, 6}, out);
    REQUIRE(out.size() == 1);
    CHECK(out[0].rect == TileRect{2, 5, 10, 6}); // the portico run
    const std::size_t cap = out.capacity();
    m.piecesIn({0, 0, 1, 1}, out);
    CHECK(out.capacity() == cap); // the buffer is reused
}

TEST_CASE("map: walkability from terrain, items, walk tiles and the impassable bit") {
    const Fixture f;
    const WorldMap& m = *f.map;
    CHECK(m.walkable({0, 60}));
    CHECK_FALSE(m.walkable({22, 42})); // water
    CHECK_FALSE(m.walkable({5, 50}));  // impassable
    CHECK_FALSE(m.walkable({2, 50}));  // the oak
    CHECK_FALSE(m.walkable({3, 3}));   // inside the hall
    CHECK(m.walkable({3, 5}));         // the hall's portico (a walk tile)
    CHECK_FALSE(m.walkable({6, 5}));   // the stool on a walk tile
    CHECK(m.itemAt({6, 5}) == f.find("tst.stool", {6, 5}));
    CHECK(m.walkable({20, 41}));       // the jetty over water
    CHECK_FALSE(m.walkable({12, 52})); // no ground
    CHECK_FALSE(m.walkable({-1, 0}));
    CHECK(m.walkable({11, 51})); // paving
}

TEST_CASE("map: walking changes level only on stairs, walk floors and decks") {
    const Fixture f;
    const WorldMap& m = *f.map;
    std::array<WalkStep, 4> s{};
    const auto steps = [&](TilePos p) {
        std::vector<std::pair<TilePos, int>> out;
        out.reserve(4);
        const int n = m.walkNeighbours(p, s);
        for (int i = 0; i < n; ++i) out.emplace_back(s[std::size_t(i)].to, s[std::size_t(i)].dz);
        return out;
    };
    const auto has = [&](TilePos from, TilePos to) {
        return std::ranges::any_of(steps(from), [&](const auto& e) { return e.first == to; });
    };
    // A plain level change is a cliff.
    CHECK_FALSE(has({29, 45}, {30, 45}));
    CHECK(has({30, 45}, {31, 45}));
    // The kit stair: foot at (31, 52), head at (31, 49) on the terrace.
    CHECK(m.floorZ({31, 51}) == 4);
    CHECK(m.floorZ({31, 50}) == 12);
    CHECK(has({31, 52}, {31, 51}));
    CHECK(has({31, 51}, {31, 50}));
    CHECK(has({31, 50}, {31, 49}));
    CHECK(has({31, 49}, {31, 50}));
    CHECK_FALSE(has({30, 50}, {31, 50})); // not from the side
    CHECK_FALSE(has({31, 50}, {32, 50}));
    const auto up = steps({31, 50});
    const auto head =
        std::ranges::find_if(up, [](const auto& e) { return e.first == TilePos{31, 49}; });
    REQUIRE(head != up.end());
    CHECK(head->second == 16 - 12);
    // The landmark stair climbs by its walk floors: 0, 16, 32 px, out onto level 2.
    CHECK(m.floorZ({50, 21}) == 0);
    CHECK(m.floorZ({51, 21}) == 16);
    CHECK(m.floorZ({52, 21}) == 32);
    CHECK(has({49, 21}, {50, 21}));
    CHECK(has({50, 21}, {51, 21}));
    CHECK(has({52, 21}, {53, 21}));
    CHECK_FALSE(m.walkable({51, 20}));
    // A deck on water steps one level to its bank.
    CHECK(has({19, 41}, {20, 41}));
    CHECK(has({20, 41}, {19, 41}));
    CHECK_FALSE(has({20, 41}, {21, 41}));
    // Nothing leaves an unwalkable tile.
    CHECK(m.walkNeighbours({22, 42}, s) == 0);
}

TEST_CASE("map: connect layouts get their neighbour masks") {
    const Fixture f;
    const WorldMap& m = *f.map;
    CHECK(m.items()[std::size_t(f.find("tst.wall", {40, 10}))].mask == kMaskE);
    CHECK(m.items()[std::size_t(f.find("tst.wall", {41, 10}))].mask == (kMaskW | kMaskS));
    CHECK(m.items()[std::size_t(f.find("tst.wall", {41, 11}))].mask == kMaskN);
}

TEST_CASE("map: slots get world positions and catalog behaviour") {
    const Fixture f;
    const WorldMap& m = *f.map;
    const int seat = m.findSlotKind("seat");
    const int stand = m.findSlotKind("stand");
    const int door = m.findSlotKind("door");
    REQUIRE(seat >= 0);
    REQUIRE(stand >= 0);
    REQUIRE(door >= 0);
    std::vector<WorldSlot> found;
    m.forEachSlotNear({6.25f, 5.25f}, 0.5f, seat, [&](const WorldSlot& s) { found.push_back(s); });
    REQUIRE(found.size() == 1);
    CHECK(found[0].at.x == doctest::Approx(6.25f)); // tile (6, 5) centre moved 8 px up the screen
    CHECK(found[0].at.y == doctest::Approx(5.25f));
    CHECK(found[0].z == 6);
    CHECK(found[0].face == 1);
    CHECK(m.slotNames()[found[0].name] == "throne");
    CHECK(found[0].item == std::uint32_t(f.find("tst.hall", {2, 2})));
    found.clear();
    m.forEachSlotNear({21.5f, 72.5f}, 0.1f, door, [&](const WorldSlot& s) { found.push_back(s); });
    REQUIRE(found.size() == 1); // tst.house r0 at (20, 70): door spot t = (1, 2)
    CHECK(found[0].tile == TilePos{21, 72});
    // The home cottage keeps its home-catalog slots, placed in the world.
    const Catalog& home = homeCatalog();
    const auto cottageType = home.findItem("cottage");
    REQUIRE(cottageType.has_value());
    const ItemDef& cottage = home.items[std::size_t(cottageType.value_or(0))];
    int expected = 0;
    for (const SlotDef& s : cottage.slots)
        if (s.where != SlotWhere::Beside && !s.spots.empty()) expected += int(s.spots[0].size());
    int cottageSlots = 0;
    for (const WorldSlot& s : m.slots()) cottageSlots += m.info(m.items()[s.item]).id == "cottage";
    CHECK(cottageSlots == expected);
    // Radius queries agree with brute force; district queries see only their district.
    for (int k = 0; k < 50; ++k) {
        const Vec2 c{float(k * 13 % 64), float(k * 29 % 96)};
        const float r = 3.0f + float(k % 20);
        const int kind = k % 3 == 0 ? -1 : stand;
        int got = 0;
        m.forEachSlotNear(c, r, kind, [&](const WorldSlot&) { ++got; });
        int want = 0;
        for (const WorldSlot& s : m.slots()) {
            const float dx = s.at.x - c.x;
            const float dy = s.at.y - c.y;
            want += (kind < 0 || s.kind == kind) && dx * dx + dy * dy <= r * r;
        }
        CHECK(got == want);
    }
    int guards = 0;
    m.forEachSlotInDistrict(m.findDistrict("town/market"), stand, [&](const WorldSlot& s) {
        CHECK(m.slotNames()[s.name] == "guard");
        CHECK(s.cap == 2);
        ++guards;
    });
    CHECK(guards == 2);
    int none = 0;
    m.forEachSlotInDistrict(m.findDistrict("wild/land"), seat, [&](const WorldSlot&) { ++none; });
    CHECK(none == 0);
}

TEST_CASE("map: region theme weights blend by kind and distance") {
    const Fixture f;
    const WorldMap& m = *f.map;
    std::array<RegionWeight, 8> w{};
    int n = m.themeWeights({10.5f, 10.5f}, w);
    REQUIRE(n == 1);
    CHECK(w[0].region == f.wf.findRegion("town"));
    CHECK(w[0].weight == doctest::Approx(1.0f));
    n = m.themeWeights({32.0f, 16.0f}, w);
    REQUIRE(n == 2);
    CHECK(w[0].weight >= w[1].weight);
    CHECK(w[0].weight + w[1].weight == doctest::Approx(1.0f));
    std::array<RegionWeight, 1> one{};
    CHECK(m.themeWeights({32.0f, 16.0f}, one) == 1);
    CHECK(m.themeWeights({-100.0f, -100.0f}, w) == 0);
}

TEST_CASE("map: a home delta overlays the home rect") {
    Fixture f;
    WorldMap& m = *f.map;
    const std::size_t prebuilt = m.items().size();
    const int hall = f.find("tst.hall", {2, 2});
    // Prebuilt items under the home stay in the list as composed (off the map's tiles once the
    // home is applied), so applying the home moves no index (city life keeps them; L-018).
    const int oak = f.find("oak", {44, 64});
    REQUIRE(oak >= 0);
    std::vector<std::pair<std::uint32_t, TilePos>> before;
    for (const Placed& it : m.items()) before.emplace_back(it.info, TilePos{it.x, it.y});
    HomeDelta d;
    d.w = 8;
    d.h = 8;
    d.palette = {"grass", "path"};
    d.terrain.assign(64, 0);
    for (int x = 0; x < 8; ++x) d.terrain[std::size_t(x)] = 1;
    d.terrain[63] = kNone;
    d.wild.assign(64, 0);
    for (int x = 0; x < 8; ++x) d.wild[std::size_t(7 * 8 + x)] = 1;
    d.items = {{"cottage", 2, 2, 0},
               {"oak", 1, 5, 0},
               {"nonsense", 0, 0, 0},
               {"oak", 3, 3, 0},
               {"cottage", 7, 7, 0}};
    Diagnostics diag;
    REQUIRE(m.applyHome(d, diag).has_value());
    CHECK(contains(diag.warnings, "home item nonsense at (0, 0): no catalog has it"));
    CHECK(contains(diag.warnings, "home item oak at (3, 3): overlaps another home item"));
    CHECK(contains(diag.warnings, "home item cottage at (7, 7): leaves the home region"));
    CHECK(m.terrainInfo(m.terrainAt({40, 60})).id == "path");
    CHECK(m.terrainInfo(m.terrainAt({41, 62})).id == "grass");
    CHECK(m.level({41, 62}) == 1);
    CHECK(m.terrainAt({47, 67}) == kNone);
    CHECK(m.regionAt({41, 62}) == f.wf.findRegion("home"));
    const int cottage = m.itemAt({42, 62});
    REQUIRE(cottage >= 0);
    CHECK(m.info(m.items()[std::size_t(cottage)]).id == "cottage");
    CHECK(m.items()[std::size_t(cottage)].layer == kHomeLayer);
    CHECK(m.itemAt({44, 64}) != oak); // prebuilt items under the home are not on the map
    const int under = m.itemAt({39, 59});
    CHECK((under < 0 || m.info(m.items()[std::size_t(under)]).id != "tst.house"));
    CHECK(m.items().size() == prebuilt + 2);
    for (std::size_t i = 0; i < prebuilt; ++i) {
        CAPTURE(i);
        CHECK(m.items()[i].info == before[i].first);
        CHECK(TilePos{m.items()[i].x, m.items()[i].y} == before[i].second);
    }
    CHECK(m.walkable({41, 61}));
    CHECK_FALSE(m.walkable({41, 67})); // wild land
    CHECK(f.find("tst.hall", {2, 2}) == hall);
    // A second delta replaces the home items and leaves the rest alone.
    d.items = {{"oak", 6, 6, 0}};
    REQUIRE(m.applyHome(d, diag).has_value());
    CHECK(m.itemAt({42, 62}) == -1);
    REQUIRE(m.itemAt({46, 66}) >= 0);
    CHECK(m.info(m.items()[std::size_t(m.itemAt({46, 66}))]).id == "oak");
    CHECK(m.items().size() == prebuilt + 1);
    CHECK(f.find("tst.hall", {2, 2}) == hall);
    int cottageSlots = 0;
    std::set<std::uint32_t> cottages;
    for (const WorldSlot& s : m.slots())
        if (m.info(m.items()[s.item]).id == "cottage") {
            ++cottageSlots;
            cottages.insert(s.item);
        }
    CHECK(cottageSlots > 0);
    CHECK(cottages.size() == 1); // only the one at (25, 70), outside the home
    // Wrong sizes are refused.
    d.w = 4;
    CHECK_FALSE(m.applyHome(d, diag).has_value());
}

TEST_CASE("map: a core World converts into a home delta") {
    const Catalog& cat = homeCatalog();
    const World starter = makeStarterWorld(cat);
    const HomeDelta d = homeDeltaFrom(starter, cat);
    CHECK(d.w == starter.width());
    CHECK(d.h == starter.height());
    CHECK(d.items.size() == starter.items().size());
    int wild = 0;
    for (const std::uint8_t v : d.wild) wild += v;
    CHECK(wild == starter.wildCount());
    for (int y = 0; y < d.h; y += 7)
        for (int x = 0; x < d.w; x += 5) {
            const std::uint8_t v = d.terrain[std::size_t(y * d.w + x)];
            const int t = starter.terrainAt({x, y});
            if (t == kNoGround)
                CHECK(v == kNone);
            else
                CHECK(d.palette[v] == cat.terrain[std::size_t(t)].id);
        }
}

TEST_CASE("graph: layers merge at portals; next hops and A* agree") {
    const Fixture f;
    auto town = parseGraphFile(fixture("graph_ok.json"), "graph_ok.json", "town", 64, 96);
    REQUIRE(town.has_value());
    GraphFile base;
    base.layer = "base";
    base.nodes = {{"gate", {2, 2}, NodeKind::Portal}, {"far", {40, 2}, NodeKind::Dest}};
    base.edges = {{0, 1, EdgeKind::Road, {}}};
    std::vector<GraphFile> graphs{base, *town};
    Diagnostics diag;
    const RoadGraph g(graphs, *f.map, diag);
    CHECK(diag.errors.empty());
    CHECK(g.nodes().size() == 6);
    CHECK(g.findNode("base:gate") == g.findNode("town:gate"));
    CHECK(g.findNode("town:nowhere") == -1);
    CHECK(g.componentCount() == 1);
    CHECK(g.lanes().size() == 1);
    CHECK(g.lanes()[0].id == "town:harbour");
    const int gate = g.findNode("town:gate");
    const int a = g.findNode("town:a");
    const int market = g.findNode("town:market");
    const int temple = g.findNode("town:temple");
    const int far = g.findNode("base:far");
    CHECK(g.edgesAt(std::uint32_t(gate)).size() == 2);
    // Nearest node against brute force.
    for (int k = 0; k < 40; ++k) {
        const Vec2 p{float(k * 7 % 64) + 0.3f, float(k * 11 % 96) + 0.6f};
        int best = -1;
        float bd = 1e30f;
        for (std::size_t i = 0; i < g.nodes().size(); ++i) {
            const float dx = float(g.nodes()[i].at.x) + 0.5f - p.x;
            const float dy = float(g.nodes()[i].at.y) + 0.5f - p.y;
            if (dx * dx + dy * dy < bd) {
                bd = dx * dx + dy * dy;
                best = int(i);
            }
        }
        CHECK(g.nearestNode(p) == best);
    }
    // a -> temple: through the market (41.3 tiles) beats the track (47.1).
    CHECK(g.nextHop(a, temple) == market);
    PathScratch scratch;
    std::vector<std::uint32_t> path;
    REQUIRE(g.shortestPath(gate, temple, scratch, path));
    std::vector<std::uint32_t> hops{std::uint32_t(gate)};
    for (int n = gate; n != temple; n = g.nextHop(n, temple)) {
        REQUIRE(n >= 0);
        hops.push_back(std::uint32_t(g.nextHop(n, temple)));
    }
    CHECK(hops == path);
    std::vector<TilePos> line;
    g.polyline(path, line);
    REQUIRE(line.size() == path.size() + 3);
    CHECK(line[line.size() - 4] == TilePos{20, 20});
    CHECK(line[line.size() - 2] == TilePos{20, 28});
    REQUIRE(g.shortestPath(temple, gate, scratch, path)); // scratch reused
    CHECK(path.front() == std::uint32_t(temple));
    g.polyline(path, line);
    CHECK(line[1] == TilePos{20, 28}); // via points reversed when walking the edge backwards
    // No tables across regions or towards plain nodes.
    CHECK(g.nextHop(far, temple) == -1);
    CHECK(g.nextHop(gate, a) == -1);
    CHECK(g.nextHop(temple, temple) == temple);
    REQUIRE(g.shortestPath(far, temple, scratch, path));
    CHECK(path.front() == std::uint32_t(far));
}
