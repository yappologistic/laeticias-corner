#include "core/autosave.hpp"
#include "core/catalog.hpp"
#include "core/clock.hpp"
#include "core/edit.hpp"
#include "core/rng.hpp"
#include "core/save.hpp"
#include "core/starter.hpp"
#include "core/tuning.hpp"
#include "core/visitors.hpp"
#include "core/world.hpp"
#include "test_support.hpp"

#include <doctest.h>

#include <filesystem>
#include <fstream>

using namespace lc;

namespace {

int item(const Catalog& c, std::string_view id) {
    return *c.findItem(id);
}
int terrain(const Catalog& c, std::string_view id) {
    return *c.findTerrain(id);
}

// Everyone may come except rare visitors, whose recipes are the progress loop's business.
const std::vector<VisitorGate>& gates() {
    static const std::vector<VisitorGate> g = [] {
        std::vector<VisitorGate> v(test::catalog().visitors.size());
        for (std::size_t i = 0; i < v.size(); ++i) v[i].allowed = !test::catalog().visitors[i].rare;
        return v;
    }();
    return g;
}

// How many of a visitor the whole world attracts.
int wants(const VisitorDef& def, const World& w, bool night) {
    Tally t;
    tallyArea(w, test::catalog(), w.bounds(), t);
    return desiredCount(def, t, night);
}

} // namespace

TEST_CASE("the shipped catalog parses and validates") {
    const Catalog& c = test::catalog();
    CHECK(c.mapW == 40);
    CHECK(c.mapH == 40);
    CHECK(c.tileW == 64);
    CHECK(c.tileH == 32);
    CHECK(c.iso().hw == 32.0f);
    CHECK(c.iso().hh == 16.0f);
    CHECK(c.terrain[static_cast<std::size_t>(c.baseTerrain)].id == "grass");
    CHECK(c.terrain[static_cast<std::size_t>(c.waterTerrain)].water);
    const auto& barn = c.items[static_cast<std::size_t>(item(c, "barn"))];
    CHECK(barn.footprintW == 3);
    CHECK(barn.footprintH == 2);
    CHECK(barn.layout == Layout::Rotate);
    CHECK(barn.sound == "sfx/place_wood.wav");
    const auto& lily = c.items[static_cast<std::size_t>(item(c, "lily_pads"))];
    CHECK(lily.sound == "sfx/splash.wav");
    const auto& butterfly = c.visitors[static_cast<std::size_t>(*c.findVisitor("butterfly"))];
    CHECK(butterfly.anyItems.size() == 3);
    CHECK(butterfly.anyTotal == 4);
    CHECK(c.visitors[static_cast<std::size_t>(*c.findVisitor("duck"))].voice == "sfx/duck.wav");
    CHECK(c.visitors[static_cast<std::size_t>(*c.findVisitor("firefly"))].glow);
    CHECK_FALSE(c.visitors[static_cast<std::size_t>(*c.findVisitor("duck"))].glow);
    const auto& cottage = c.items[static_cast<std::size_t>(item(c, "cottage"))];
    REQUIRE(cottage.smokeAt.size() == 4);
    CHECK(cottage.smokeAt[0].x == 20);
    CHECK(cottage.smokeAt[0].y == -38);
    CHECK(c.items[static_cast<std::size_t>(item(c, "barn"))].smokeAt.empty());
}

TEST_CASE("catalog validation reports bad content") {
    const auto broken = [](std::string_view from, std::string_view to) {
        std::string text = test::catalogText();
        const auto pos = text.find(from);
        REQUIRE(pos != std::string::npos);
        text.replace(pos, from.size(), to);
        return parseCatalog(text);
    };
    CHECK_FALSE(parseCatalog("{ not json").has_value());
    CHECK_FALSE(broken("\"version\": 2", "\"version\": 7").has_value());
    // Conditions, land and wishes are checked too, naming the entry.
    const auto cond =
        broken("\"min\": 4}}, \"progress\"", "\"min\": 4, \"max\": 2}}, \"progress\"");
    REQUIRE_FALSE(cond.has_value());
    CHECK(cond.error().find("first_flowers") != std::string::npos);
    CHECK_FALSE(broken("\"rects\": [[8, 20, 19, 39]]", "\"rects\": [[8, 20, 20, 39]]").has_value());
    CHECK_FALSE(broken("\"rects\": [[8, 20, 19, 39]]", "\"rects\": [[9, 20, 19, 39]]").has_value());
    CHECK_FALSE(broken("{\"time\": [\"night\"]}", "{\"time\": [\"noon\"]}").has_value());
    CHECK_FALSE(broken("\"after\": [\"first_flowers\"]", "\"after\": [\"a_roof\"]").has_value());
    CHECK_FALSE(broken("{\"seen\": \"cat\"}", "{\"seen\": \"dog\"}").has_value());
    CHECK_FALSE(
        broken("\"reward\": {\"clue\": \"owl\"}", "\"reward\": {\"clue\": \"cat\"}").has_value());
    CHECK_FALSE(broken("\"category\": \"nature\"", "\"category\": \"space\"").has_value());
    CHECK_FALSE(broken("\"footprint\": [3, 2]", "\"footprint\": [0, 2]").has_value());
    CHECK_FALSE(broken("\"on\": \"water\"", "\"on\": \"lava\"").has_value());
    CHECK_FALSE(broken("\"coop\": 1", "\"castle\": 1").has_value());
    CHECK_FALSE(broken("\"id\": \"pine\"", "\"id\": \"oak\"").has_value());
    CHECK_FALSE(broken("\"sfx/cat.wav\"", "\"sfx/dog.wav\"").has_value());
    CHECK_FALSE(broken("[[20, -38], [-4, -30], [-20, -42], [4, -50]]", "[[20, -38]]").has_value());
    CHECK_FALSE(broken("[[20, -38], [-4, -30]", "[[20], [-4, -30]").has_value());
    // The cell must be 2:1 with whole half sizes; the map must stay within the limits.
    CHECK_FALSE(broken("\"w\": 64, \"h\": 32", "\"w\": 64, \"h\": 30").has_value());
    CHECK_FALSE(broken("\"w\": 64, \"h\": 32", "\"w\": 33, \"h\": 16").has_value());
    CHECK(broken("\"w\": 64, \"h\": 32", "\"w\": 32, \"h\": 16").has_value());
    // The land stages must cover the home map exactly, so it cannot grow on its own.
    CHECK_FALSE(broken("\"w\": 40, \"h\": 40", "\"w\": 1024, \"h\": 512").has_value());
    CHECK_FALSE(broken("\"w\": 40, \"h\": 40", "\"w\": 4096, \"h\": 4096").has_value());
    const auto err = broken("\"layout\": \"connect\"", "\"layout\": \"spiral\"");
    REQUIRE_FALSE(err.has_value());
    CHECK(err.error().find("hedge") != std::string::npos);
}

TEST_CASE("projection matches the contract at any tile size") {
    for (const Iso iso : {Iso{16, 8}, Iso{32, 16}, Iso{64, 32}}) {
        CAPTURE(iso.hw);
        const float hw = iso.hw;
        const float hh = iso.hh;
        CHECK(iso.toWorld(0, 0).x == 0);
        CHECK(iso.toWorld(1, 0).x == hw);
        CHECK(iso.toWorld(1, 0).y == hh);
        CHECK(iso.toWorld(0, 1).x == -hw);
        CHECK(iso.tileAt({0, hh}) == TilePos{0, 0});             // centre of tile 0,0
        CHECK(iso.tileAt({0, 0.5f}) == TilePos{0, 0});           // just under the top vertex
        CHECK(iso.tileAt({0, 2 * hh - 0.5f}) == TilePos{0, 0});  // just above the bottom
        CHECK(iso.tileAt({hw - 0.5f, hh}) == TilePos{0, 0});     // right corner
        CHECK(iso.tileAt({hw + 0.5f, hh + 1}) == TilePos{1, 0}); // past it, the next tile
        CHECK(iso.tileAt({0, 2 * hh + 0.5f}) == TilePos{1, 1});
        const Vec2 w = iso.toWorld(7, 3);
        CHECK(iso.tileAt({w.x, w.y + hh}) == TilePos{7, 3});
    }
    // Picking stays exact at the far corner of a 1024 x 512 world of 64 x 32 tiles.
    const Iso iso = test::catalog().iso();
    for (const TilePos t :
         {TilePos{1023, 511}, TilePos{1023, 0}, TilePos{0, 511}, TilePos{777, 333}}) {
        const Vec2 c = iso.toWorld(static_cast<float>(t.x) + 0.5f, static_cast<float>(t.y) + 0.5f);
        CHECK(iso.tileAt(c) == t);
        const Vec2 near{c.x + iso.hw * 0.98f, c.y};
        CHECK(iso.tileAt(near) == t);
    }
}

TEST_CASE("rotated footprints swap width and height") {
    const Catalog& c = test::catalog();
    const auto& barn = c.items[static_cast<std::size_t>(item(c, "barn"))];
    CHECK(footprintOf(barn, 0).w == 3);
    CHECK(footprintOf(barn, 1).w == 2);
    CHECK(footprintOf(barn, 1).h == 3);
    CHECK(footprintOf(barn, 2).w == 3);
    const auto& oak = c.items[static_cast<std::size_t>(item(c, "oak"))];
    CHECK(footprintOf(oak, 1).w == 1); // variant layout never rotates
}

TEST_CASE("placement rules: bounds, overlap, land and water") {
    const Catalog& c = test::catalog();
    World w(c);
    const int water = terrain(c, "water");
    const int e = c.mapW - 3; // a 3x2 barn flush with the far corner
    const Item barn = makeItem(c, item(c, "barn"), 0, {e, c.mapH - 2});
    CHECK(canPlace(w, c, barn) == PlaceResult::Ok);
    CHECK(canPlace(w, c, makeItem(c, item(c, "barn"), 0, {e + 1, c.mapH - 2})) ==
          PlaceResult::OutOfBounds);
    CHECK(canPlace(w, c, makeItem(c, item(c, "barn"), 1, {e, c.mapH - 2})) ==
          PlaceResult::OutOfBounds);
    CHECK(canPlace(w, c, makeItem(c, item(c, "oak"), 0, {-1, 0})) == PlaceResult::OutOfBounds);
    // Coordinates near the int limits (a damaged save) are refused without overflowing.
    CHECK(canPlace(w, c, makeItem(c, item(c, "barn"), 0, {2147483646, 0})) ==
          PlaceResult::OutOfBounds);
    CHECK(canPlace(w, c, makeItem(c, item(c, "barn"), 0, {0, -2147483647})) ==
          PlaceResult::OutOfBounds);
    w.addItem(barn);
    CHECK(canPlace(w, c, makeItem(c, item(c, "oak"), 0, {c.mapW - 1, c.mapH - 1})) ==
          PlaceResult::Occupied);
    CHECK(canPlace(w, c, makeItem(c, item(c, "oak"), 0, {e - 1, c.mapH - 1})) == PlaceResult::Ok);
    // A 2x2 overlapping a single tile of the barn.
    CHECK(canPlace(w, c, makeItem(c, item(c, "cottage"), 0, {e - 1, c.mapH - 3})) ==
          PlaceResult::Occupied);

    w.setTerrain({3, 3}, water);
    CHECK(canPlace(w, c, makeItem(c, item(c, "oak"), 0, {3, 3})) == PlaceResult::NeedsLand);
    CHECK(canPlace(w, c, makeItem(c, item(c, "lily_pads"), 0, {3, 3})) == PlaceResult::Ok);
    CHECK(canPlace(w, c, makeItem(c, item(c, "lily_pads"), 0, {4, 3})) == PlaceResult::NeedsWater);
    CHECK(canPlace(w, c, makeItem(c, item(c, "rock"), 0, {3, 3})) == PlaceResult::Ok);
    CHECK(canPlace(w, c, makeItem(c, item(c, "rock"), 0, {4, 3})) == PlaceResult::Ok);
    // A cottage with one corner in water.
    CHECK(canPlace(w, c, makeItem(c, item(c, "cottage"), 0, {2, 2})) == PlaceResult::NeedsLand);
}

TEST_CASE("painting refuses to put the wrong ground under an item") {
    const Catalog& c = test::catalog();
    World w(c);
    const int water = terrain(c, "water");
    const int path = terrain(c, "path");
    w.addItem(makeItem(c, item(c, "oak"), 0, {5, 5}));
    CHECK(canPaint(w, c, {5, 5}, water) == PaintResult::BlockedByItem);
    CHECK(canPaint(w, c, {5, 5}, path) == PaintResult::Ok);
    CHECK(canPaint(w, c, {5, 6}, c.baseTerrain) == PaintResult::Unchanged);
    CHECK(canPaint(w, c, {c.mapW, 6}, path) == PaintResult::OutOfBounds);
    CHECK(canPaint(w, c, {5, 6}, 999) == PaintResult::OutOfBounds);
    w.setTerrain({8, 8}, water);
    w.addItem(makeItem(c, item(c, "bridge"), 0, {8, 8}));
    CHECK(canPaint(w, c, {8, 8}, path) == PaintResult::BlockedByItem);
    w.addItem(makeItem(c, item(c, "rock"), 0, {9, 9}));
    CHECK(canPaint(w, c, {9, 9}, water) == PaintResult::Ok);
}

TEST_CASE("world bookkeeping: occupancy, counts, masks") {
    const Catalog& c = test::catalog();
    World w(c);
    const int hedge = item(c, "hedge");
    w.addItem(makeItem(c, hedge, 0, {4, 4}));
    w.addItem(makeItem(c, hedge, 0, {5, 4}));
    w.addItem(makeItem(c, hedge, 0, {4, 5}));
    w.addItem(makeItem(c, item(c, "cottage"), 0, {10, 10}));
    CHECK(w.itemCount(hedge) == 3);
    CHECK(w.itemMask({4, 4}, hedge) == (kMaskE | kMaskS));
    CHECK(w.itemMask({5, 4}, hedge) == kMaskW);
    CHECK(w.itemAt({11, 11})->pos == TilePos{10, 10});
    // Removing an earlier item must keep the moved item's occupancy right.
    w.removeItem(0);
    CHECK(w.itemCount(hedge) == 2);
    CHECK(w.itemAt({4, 4}) == nullptr);
    CHECK(w.itemAt({11, 10})->type == item(c, "cottage"));
    CHECK(w.itemAt({4, 5})->type == hedge);

    const int water = terrain(c, "water");
    w.setTerrain({0, 0}, water);
    w.setTerrain({1, 0}, water);
    CHECK(w.terrainCount(water) == 2);
    CHECK(w.terrainMask({0, 0}) == (kMaskN | kMaskE | kMaskW)); // map edges count as same
    CHECK(w.terrainMask({1, 0}) == (kMaskN | kMaskW));
}

TEST_CASE("undo and redo, including drags as one step") {
    const Catalog& c = test::catalog();
    World w(c);
    Editor ed(tuning::kUndoSteps);
    const int path = terrain(c, "path");
    CHECK_FALSE(ed.canUndo());
    CHECK(ed.undo(w).empty());

    ed.begin();
    for (int x = 0; x < 5; ++x) CHECK(ed.paint(w, c, {x, 2}, path) == PaintResult::Ok);
    CHECK(ed.paint(w, c, {2, 2}, path) == PaintResult::Unchanged);
    ed.commit();
    CHECK(w.terrainCount(path) == 5);

    CHECK(ed.place(w, c, makeItem(c, item(c, "cottage"), 1, {8, 8})) == PlaceResult::Ok);
    const auto rev = w.revision();
    // Failed actions leave no undo step behind.
    CHECK(ed.place(w, c, makeItem(c, item(c, "oak"), 0, {8, 8})) == PlaceResult::Occupied);
    ed.begin();
    CHECK(ed.paint(w, c, {c.mapW + 10, 30}, path) == PaintResult::OutOfBounds);
    ed.commit();
    CHECK(w.revision() == rev);

    CHECK(ed.remove(w, {9, 9}));
    CHECK_FALSE(ed.remove(w, {9, 9}));
    CHECK(w.items().empty());

    auto ops = ed.undo(w); // brings the cottage back
    REQUIRE(ops.size() == 1);
    CHECK(ops[0].kind == Op::Kind::Add);
    CHECK(w.itemAt({9, 9})->variant == 1);
    ops = ed.undo(w); // removes it again
    CHECK(ops[0].kind == Op::Kind::Remove);
    CHECK(w.items().empty());
    ops = ed.undo(w); // the whole drag
    CHECK(ops.size() == 5);
    CHECK(w.terrainCount(path) == 0);
    CHECK_FALSE(ed.canUndo());

    CHECK(ed.redo(w).size() == 5);
    CHECK(w.terrainCount(path) == 5);
    CHECK(ed.redo(w).size() == 1);
    CHECK(w.items().size() == 1);
    // A new edit clears the redo stack.
    CHECK(ed.place(w, c, makeItem(c, item(c, "oak"), 0, {0, 0})) == PlaceResult::Ok);
    CHECK_FALSE(ed.canRedo());

    ed.begin();
    ed.commit();
    CHECK(ed.undo(w).size() == 1); // the empty group was not recorded
}

TEST_CASE("undo history is bounded") {
    const Catalog& c = test::catalog();
    World w(c);
    Editor ed(3);
    for (int x = 0; x < 6; ++x) (void)ed.paint(w, c, {x, 0}, terrain(c, "path"));
    int steps = 0;
    while (!ed.undo(w).empty()) ++steps;
    CHECK(steps == 3);
    CHECK(w.terrainCount(terrain(c, "path")) == 3);
}

TEST_CASE("clock phases, pinning and lighting") {
    CHECK(phaseAt(0.1) == Phase::Day);
    CHECK(phaseAt(0.55) == Phase::Dusk);
    CHECK(phaseAt(0.7) == Phase::Night);
    CHECK(phaseAt(0.9) == Phase::Dawn);
    CHECK(phaseAt(1.1) == Phase::Day);
    for (Phase p : {Phase::Day, Phase::Dusk, Phase::Night, Phase::Dawn})
        CHECK(phaseAt(phaseCentre(p)) == p);
    CHECK(parsePin("auto") == ClockPin::Auto);
    CHECK(parsePin("dawn") == ClockPin::Dawn);
    CHECK_FALSE(parsePin("noon"));
    CHECK(phaseId(Phase::Dusk) == "dusk");

    Clock clock;
    clock.setTime(0.49);
    clock.update(tuning::kDayLengthSeconds * 0.02);
    CHECK(clock.phase() == Phase::Dusk);
    clock.setPin(ClockPin::Night, false);
    for (int i = 0; i < 200; ++i) clock.update(tuning::kStepSeconds);
    CHECK(clock.time() == doctest::Approx(phaseCentre(Phase::Night)));
    clock.update(100.0); // pinned: stays put
    CHECK(clock.phase() == Phase::Night);
    clock.setPin(ClockPin::Day, true);
    CHECK(clock.phase() == Phase::Day);

    const Lighting day = lightingAt(phaseCentre(Phase::Day), false);
    const Lighting night = lightingAt(phaseCentre(Phase::Night), false);
    CHECK(day.glow == doctest::Approx(0.0));
    CHECK(night.glow == doctest::Approx(1.0));
    CHECK(night.ambient.b > night.ambient.r);
    // Night is genuinely dark: well under half the day's light on every channel.
    CHECK(night.ambient.r < 0.4f * day.ambient.r);
    CHECK(night.ambient.g < 0.4f * day.ambient.g);
    CHECK(lightingAt(phaseCentre(Phase::Day), true).ambient.r < day.ambient.r);
    // Continuous across the wrap point.
    const Lighting a = lightingAt(0.9999, false);
    const Lighting b = lightingAt(0.0001, false);
    CHECK(a.ambient.g == doctest::Approx(b.ambient.g).epsilon(0.01));
}

TEST_CASE("visitor needs decide who comes") {
    const Catalog& c = test::catalog();
    World w(c);
    const auto& duck = c.visitors[static_cast<std::size_t>(*c.findVisitor("duck"))];
    const auto& butterfly = c.visitors[static_cast<std::size_t>(*c.findVisitor("butterfly"))];
    const auto& firefly = c.visitors[static_cast<std::size_t>(*c.findVisitor("firefly"))];
    const auto& cat = c.visitors[static_cast<std::size_t>(*c.findVisitor("cat"))];
    const int water = terrain(c, "water");
    for (int x = 0; x < 5; ++x) w.setTerrain({x, 0}, water);
    CHECK(wants(duck, w, false) == 0);
    w.setTerrain({5, 0}, water);
    CHECK(wants(duck, w, false) == tuning::kVisitorsPerNeed);
    for (int x = 0; x < 20; ++x) w.setTerrain({x, 1}, water);
    CHECK(wants(duck, w, false) == duck.max);

    w.addItem(makeItem(c, item(c, "flowers_red"), 0, {5, 5}));
    w.addItem(makeItem(c, item(c, "flowers_white"), 0, {6, 5}));
    w.addItem(makeItem(c, item(c, "flowers_violet"), 0, {7, 5}));
    CHECK(wants(butterfly, w, false) == 0);
    w.addItem(makeItem(c, item(c, "flowers_red"), 0, {8, 5}));
    CHECK(wants(butterfly, w, false) > 0);
    CHECK(wants(butterfly, w, true) == 0); // day visitor

    for (int x = 0; x < 3; ++x) w.addItem(makeItem(c, item(c, "tall_grass"), 0, {x, 8}));
    CHECK(wants(firefly, w, false) == 0);
    CHECK(wants(firefly, w, true) > 0);

    w.addItem(makeItem(c, item(c, "cottage"), 0, {10, 10}));
    w.addItem(makeItem(c, item(c, "cottage"), 0, {14, 10}));
    CHECK(wants(cat, w, true) == 1); // max 1
}

TEST_CASE("visitors arrive, stay in their habitat and leave when unwelcome") {
    const Catalog& c = test::catalog();
    World w(c);
    Rng rng(7);
    Visitors vis(c);
    const int duckId = *c.findVisitor("duck");
    const int water = terrain(c, "water");
    for (int y = 4; y < 8; ++y)
        for (int x = 4; x < 8; ++x) w.setTerrain({x, y}, water);

    bool firstSeen = false;
    int arrivals = 0;
    for (int i = 0; i < 60 * 30; ++i) {
        vis.update(w, c, false, static_cast<float>(tuning::kStepSeconds), rng, w.bounds(), gates());
        for (const auto& e : vis.events()) {
            if (e.kind != VisitorEvent::Kind::Arrived) continue;
            ++arrivals;
            if (e.firstSighting) {
                CHECK_FALSE(firstSeen);
                firstSeen = true;
            }
        }
        for (const Critter& cr : vis.critters()) {
            REQUIRE(habitatAllows(Habitat::Water, w, c, cr.pos));
        }
    }
    CHECK(firstSeen);
    CHECK(vis.seen(duckId));
    CHECK(vis.present(duckId) == wants(c.visitors[static_cast<std::size_t>(duckId)], w, false));
    CHECK(arrivals == vis.present(duckId));

    // Drain the pond: the ducks fade away.
    for (int y = 4; y < 8; ++y)
        for (int x = 4; x < 8; ++x) w.setTerrain({x, y}, c.baseTerrain);
    for (int i = 0; i < 60 * 5; ++i)
        vis.update(w, c, false, static_cast<float>(tuning::kStepSeconds), rng, w.bounds(), gates());
    CHECK(vis.critters().empty());
}

TEST_CASE("populate spawns the full population without events") {
    const Catalog& c = test::catalog();
    World w = makeStarterWorld(c);
    for (int x = 22; x < 25; ++x) w.addItem(makeItem(c, item(c, "tall_grass"), 0, {x, 38}));
    Rng rng(3);
    Visitors vis(c);
    vis.populate(w, c, true, rng, w.bounds(), gates());
    CHECK(vis.critters().empty()); // nobody seen yet: first sightings must still be events
    for (const char* id : {"duck", "firefly", "butterfly"}) vis.markSeen(*c.findVisitor(id));
    vis.populate(w, c, true, rng, w.bounds(), gates());
    CHECK(vis.events().empty());
    const int ducks = vis.present(*c.findVisitor("duck"));
    CHECK(ducks > 0);
    CHECK(vis.present(*c.findVisitor("firefly")) > 0);
    CHECK(vis.present(*c.findVisitor("butterfly")) == 0);
}

TEST_CASE("the starter scene is pleasant and valid") {
    const Catalog& c = test::catalog();
    const World w = makeStarterWorld(c);
    CHECK(w.items().size() >= 15);
    CHECK(w.terrainCount(terrain(c, "water")) >= 6); // ducks from the first minute
    CHECK(w.terrainCount(terrain(c, "path")) >= 8);
    // Only the first stage is open; the starter scene lies inside it.
    CHECK(w.wildCount() == c.mapW * c.mapH - 400);
    for (const Item& it : w.items()) CHECK_FALSE(w.isWild(it.pos));
    for (const Item& it : w.items()) {
        World probe(c);
        for (int y = 0; y < c.mapH; ++y)
            for (int x = 0; x < c.mapW; ++x) probe.setTerrain({x, y}, w.terrainAt({x, y}));
        CHECK(canPlace(probe, c, it) == PlaceResult::Ok);
    }
}

TEST_CASE("save round trip") {
    const Catalog& c = test::catalog();
    SaveData data(makeStarterWorld(c));
    data.world.addItem(makeItem(c, item(c, "barn"), 3, {2, c.mapH - 3}));
    data.clockTime = 0.7;
    data.pin = ClockPin::Night;
    data.rain = true;
    data.muted = true;
    data.journal = {"duck", "cat"};

    const std::string text = serialize(data, c);
    const auto loaded = deserialize(text, c);
    REQUIRE(loaded.has_value());
    CHECK(loaded->warnings.empty());
    CHECK(loaded->clockTime == doctest::Approx(0.7));
    CHECK(loaded->pin == ClockPin::Night);
    CHECK(loaded->rain);
    CHECK(loaded->muted);
    CHECK(loaded->journal == data.journal);
    for (int y = 0; y < c.mapH; ++y)
        for (int x = 0; x < c.mapW; ++x)
            CHECK(loaded->world.terrainAt({x, y}) == data.world.terrainAt({x, y}));
    REQUIRE(loaded->world.items().size() == data.world.items().size());
    for (const Item& it : data.world.items()) {
        const Item* other = loaded->world.itemAt(it.pos);
        REQUIRE(other != nullptr);
        CHECK(*other == it);
    }
    CHECK(serialize(*loaded, c) == text);
}

TEST_CASE("corrupt, newer and odd saves are handled") {
    const Catalog& c = test::catalog();
    CHECK_FALSE(deserialize("", c).has_value());
    CHECK_FALSE(deserialize("{\"version\": 1, \"items\": [", c).has_value());
    CHECK_FALSE(deserialize("[1,2,3]", c).has_value());
    CHECK_FALSE(deserialize("{\"items\": []}", c).has_value());
    CHECK_FALSE(deserialize("{\"version\": 99}", c).has_value());
    CHECK_FALSE(deserialize("{\"version\": 1, \"map\": {\"w\": 0, \"h\": 5}}", c).has_value());
    CHECK_FALSE(deserialize("{\"version\": 1.5}", c).has_value());

    SaveData data(World{c});
    data.world.addItem(makeItem(c, item(c, "oak"), 0, {1, 1}));
    std::string text = serialize(data, c);
    const auto replace = [&](std::string_view from, std::string_view to) {
        const auto pos = text.find(from);
        REQUIRE(pos != std::string::npos);
        text.replace(pos, from.size(), to);
    };
    replace("\"oak\"", "\"baobab\"");
    const auto loaded = deserialize(text, c);
    REQUIRE(loaded.has_value()); // unknown ids are skipped, not fatal
    CHECK(loaded->world.items().empty());
    CHECK(loaded->warnings.size() == 1);
    CHECK(loaded->warnings[0].find("baobab") != std::string::npos);

    // Minimal file without the optional sections.
    const std::string minimal = R"({"version":1,"map":{"w":20,"h":20},"palette":["grass"],
        "terrain":[)" + [] {
        std::string s;
        for (int i = 0; i < 400; ++i) s += i ? ",0" : "0";
        return s;
    }() + "]}";
    const auto min = deserialize(minimal, c);
    REQUIRE(min.has_value());
    CHECK(min->pin == ClockPin::Auto);
    CHECK_FALSE(min->rain);
    CHECK(min->world.width() == c.mapW); // an older, smaller map loads into the current one
}

TEST_CASE("atomic write replaces the file and leaves no temp behind") {
    namespace fs = std::filesystem;
    const fs::path dir = test::tempDir("atomic");
    const fs::path file = dir / "nested" / "corner.json";
    REQUIRE(writeFileAtomic(file, "first").has_value());
    REQUIRE(writeFileAtomic(file, "second").has_value());
    CHECK(*readTextFile(file) == "second");
    CHECK_FALSE(fs::exists(fs::path(file).concat(".tmp")));
    CHECK_FALSE(writeFileAtomic(dir / "nested", "x").has_value()); // a directory is in the way
}

TEST_CASE("rng is deterministic per seed") {
    Rng a(42);
    Rng b(42);
    Rng d(43);
    bool differs = false;
    for (int i = 0; i < 100; ++i) {
        const auto x = a.next();
        CHECK(x == b.next());
        differs |= x != d.next();
        const int r = a.range(2, 5);
        b.range(2, 5);
        CHECK(r >= 2);
        CHECK(r <= 5);
    }
    CHECK(differs);
}

TEST_CASE("chunked world: area queries, tallies and revisions match brute force") {
    const Catalog& c = test::catalog();
    // Not a multiple of the chunk size, and far larger than the home map.
    World w(c, 1000, 600);
    CHECK(w.chunksX() == (1000 + kChunk - 1) / kChunk);
    CHECK(w.landBounds() == TileRect{0, 0, 1000, 600});
    Rng rng(11);
    const int types = static_cast<int>(c.items.size());
    for (int i = 0; i < 4000; ++i) {
        const int type = rng.range(0, types - 1);
        const auto& def = c.items[static_cast<std::size_t>(type)];
        if (def.on == Surface::Water) continue;
        const Item it =
            makeItem(c, type, rng.range(0, def.count - 1), {rng.range(0, 999), rng.range(0, 599)});
        if (canPlace(w, c, it) == PlaceResult::Ok) w.addItem(it);
    }
    // Remove a third, so swap-removals move items between chunk lists.
    for (int i = 0; i < 1200 && !w.items().empty(); ++i)
        w.removeItem(
            static_cast<std::size_t>(rng.range(0, static_cast<int>(w.items().size()) - 1)));
    for (std::size_t i = 0; i < w.items().size(); ++i) {
        const Item& it = w.items()[i];
        for (int y = it.pos.y; y < it.pos.y + it.h; ++y)
            for (int x = it.pos.x; x < it.pos.x + it.w; ++x) REQUIRE(w.itemIndexAt({x, y}) == i);
    }
    for (const TileRect r : {TileRect{0, 0, 40, 40}, TileRect{31, 31, 33, 33},
                             TileRect{500, 100, 640, 230}, TileRect{990, 590, 1200, 900}}) {
        std::size_t viaChunks = 0;
        w.forEachItemIn(r, [&](const Item& it) {
            CHECK(it.rect().intersects(r));
            ++viaChunks;
        });
        std::size_t brute = 0;
        for (const Item& it : w.items()) brute += it.rect().intersects(r) ? 1 : 0;
        CHECK(viaChunks == brute);
    }
    for (std::size_t t = 0; t < c.items.size(); ++t) {
        int sum = 0;
        for (int cy = 0; cy < w.chunksY(); ++cy)
            for (int cx = 0; cx < w.chunksX(); ++cx)
                sum += w.chunkItemCount(cx, cy, static_cast<int>(t));
        CHECK(sum == w.itemCount(static_cast<int>(t)));
    }
    // A terrain change on a chunk edge invalidates the neighbour whose edges depend on it.
    const auto before = w.chunkTerrainRevision(1, 0);
    const auto other = w.chunkTerrainRevision(5, 5);
    w.setTerrain({kChunk - 1, 3}, c.waterTerrain);
    CHECK(w.chunkTerrainRevision(1, 0) != before);
    CHECK(w.chunkTerrainRevision(5, 5) == other);
    CHECK(w.chunkTerrainCount(0, 0, c.waterTerrain) == 1);
    CHECK(w.terrainCount(c.waterTerrain) == 1);
}

TEST_CASE("tiles without ground shape the land: refused for edits, edges run into the rim") {
    const Catalog& c = test::catalog();
    World w(c);
    for (int y = 0; y < c.mapH; ++y)
        for (int x = 30; x < c.mapW; ++x) w.setTerrain({x, y}, kNoGround);
    CHECK(w.landBounds() == TileRect{0, 0, 30, c.mapH});
    CHECK_FALSE(w.hasGround({30, 4}));
    CHECK(w.hasGround({29, 4}));
    CHECK(canPlace(w, c, makeItem(c, item(c, "oak"), 0, {31, 4})) == PlaceResult::OutOfBounds);
    CHECK(canPlace(w, c, makeItem(c, item(c, "cottage"), 0, {29, 4})) == PlaceResult::OutOfBounds);
    CHECK(canPaint(w, c, {31, 4}, terrain(c, "path")) == PaintResult::OutOfBounds);
    w.setTerrain({29, 4}, c.waterTerrain);
    CHECK((w.terrainMask({29, 4}) & kMaskE) != 0); // open sky counts as "same"
    CHECK(w.terrainCount(c.baseTerrain) == 30 * c.mapH - 1);
    CHECK_FALSE(habitatAllows(Habitat::Air, w, c, {31.5f, 4.5f}));
}

TEST_CASE("critters never step onto tiles edited away under their walk") {
    const Catalog& c = test::catalog();
    World w(c);
    const int water = terrain(c, "water");
    for (int y = 10; y < 13; ++y)
        for (int x = 4; x < 20; ++x) w.setTerrain({x, y}, water);
    Rng rng(5);
    Visitors vis(c);
    vis.markSeen(*c.findVisitor("duck"));
    vis.populate(w, c, false, rng, w.bounds(), gates());
    REQUIRE(vis.present(*c.findVisitor("duck")) > 0);
    // Let them swim, then drain the channel in stripes while they move.
    for (int i = 0; i < 600; ++i) {
        if (i % 50 == 25) {
            const int x = 5 + (i / 50) % 14;
            for (int y = 10; y < 13; ++y) w.setTerrain({x, y}, c.baseTerrain);
        }
        const auto before = std::vector<Critter>(vis.critters().begin(), vis.critters().end());
        vis.update(w, c, false, static_cast<float>(tuning::kStepSeconds), rng, w.bounds(), gates());
        // Order is kept by update (new arrivals are appended, departures removed in order), so
        // compare each surviving critter with its previous position.
        std::size_t j = 0;
        for (const Critter& now : vis.critters()) {
            while (j < before.size() &&
                   (before[j].visitor != now.visitor ||
                    std::hypot(before[j].pos.x - now.pos.x, before[j].pos.y - now.pos.y) > 0.1f))
                ++j;
            if (j == before.size()) break; // a new arrival
            const TilePos a{static_cast<int>(std::floor(before[j].pos.x)),
                            static_cast<int>(std::floor(before[j].pos.y))};
            const TilePos b{static_cast<int>(std::floor(now.pos.x)),
                            static_cast<int>(std::floor(now.pos.y))};
            if (!(a == b)) CHECK(habitatAllows(c.visitors[now.visitor].habitat, w, c, now.pos));
            ++j;
        }
    }
}

TEST_CASE("a critter whose tile is edited away walks to an allowed neighbour") {
    const Catalog& c = test::catalog();
    World w(c);
    const int cottage = item(c, "cottage");
    w.addItem(makeItem(c, cottage, 0, {20, 20}));
    Rng rng(9);
    Visitors vis(c);
    const int catId = *c.findVisitor("cat");
    vis.markSeen(catId);
    vis.populate(w, c, false, rng, w.bounds(), gates());
    REQUIRE(vis.present(catId) == 1);
    const auto catPos = [&] {
        for (const Critter& cr : vis.critters())
            if (cr.visitor == catId) return cr.pos;
        return Vec2{-1, -1};
    };
    const Vec2 p = catPos();
    const TilePos t{static_cast<int>(p.x), static_cast<int>(p.y)};
    // Put a rock right under the cat (unless that is the cottage itself).
    REQUIRE(w.itemAt(t) == nullptr);
    w.addItem(makeItem(c, item(c, "rock"), 0, t));
    for (int i = 0; i < 120; ++i)
        vis.update(w, c, false, static_cast<float>(tuning::kStepSeconds), rng, w.bounds(), gates());
    REQUIRE(vis.present(catId) == 1); // it moved off instead of fading away
    CHECK(habitatAllows(Habitat::Land, w, c, catPos()));
}

TEST_CASE("visitors live in the active area only") {
    const Catalog& c = test::catalog();
    World w(c, 200, 200);
    const int water = terrain(c, "water");
    for (int y = 150; y < 160; ++y)
        for (int x = 150; x < 160; ++x) w.setTerrain({x, y}, water);
    Rng rng(4);
    Visitors vis(c);
    const int duck = *c.findVisitor("duck");
    vis.markSeen(duck);
    vis.populate(w, c, false, rng, {0, 0, 64, 64}, gates());
    CHECK(vis.present(duck) == 0); // the pond is outside the area: nobody is simulated there
    vis.populate(w, c, false, rng, {128, 128, 192, 192}, gates());
    CHECK(vis.present(duck) > 0);
    // The view leaves: they are dropped silently; it comes back: they are simply there again.
    vis.update(w, c, false, 0.01f, rng, {0, 0, 64, 64}, gates());
    CHECK(vis.critters().empty());
    CHECK(vis.events().empty());
    vis.update(w, c, false, 0.01f, rng, {128, 128, 192, 192}, gates());
    CHECK(vis.present(duck) > 0);
    CHECK(vis.events().empty());
    for (const Critter& cr : vis.critters()) CHECK(cr.pos.x >= 128);
}

TEST_CASE("a save from the old 20x20 map loads centred on the new map with nothing lost") {
    const Catalog& c = test::catalog();
    // Version 1 file as the previous release wrote it.
    std::string terrainList;
    for (int i = 0; i < 400; ++i) {
        const int x = i % 20;
        const int y = i / 20;
        terrainList += (i ? "," : "") + std::string((x == 0 && y == 0)     ? "1"
                                                    : (y == 19 && x == 19) ? "2"
                                                                           : "0");
    }
    const std::string v1 = R"({"version":1,"map":{"w":20,"h":20},"palette":["grass","water","path"],
        "terrain":[)" + terrainList +
                           R"(],
        "items":[{"id":"oak","x":0,"y":5,"v":2},{"id":"barn","x":17,"y":18,"v":0},
                 {"id":"lily_pads","x":0,"y":0,"v":1}],
        "clock":{"t":0.7,"pin":"night"},"settings":{"rain":true,"muted":false},
        "journal":["duck"]})";
    const auto loaded = deserialize(v1, c);
    REQUIRE(loaded.has_value());
    const TilePos o = centringOffset(20, 20, c.mapW, c.mapH);
    CHECK(o == TilePos{10, 10});
    const World& w = loaded->world;
    CHECK(w.terrainAt({o.x, o.y}) == c.waterTerrain);
    CHECK(w.terrainAt({o.x + 19, o.y + 19}) == terrain(c, "path"));
    CHECK(w.items().size() == 3);
    CHECK(w.itemAt({o.x, o.y + 5})->type == item(c, "oak"));
    CHECK(w.itemAt({o.x + 19, o.y + 19})->type == item(c, "barn"));
    CHECK(w.itemAt({o.x, o.y})->type == item(c, "lily_pads"));
    CHECK(loaded->pin == ClockPin::Night);
    CHECK(loaded->rain);
    REQUIRE(loaded->warnings.size() == 1);
    CHECK(loaded->warnings[0].find("centred") != std::string::npos);
    // Written back as version 2 it round-trips exactly.
    const std::string v2 = serialize(*loaded, c);
    CHECK(v2.find("\"version\": 2") != std::string::npos);
    const auto again = deserialize(v2, c);
    REQUIRE(again.has_value());
    CHECK(again->warnings.empty());
    CHECK(serialize(*again, c) == v2);
}

TEST_CASE("damaged saves are repaired entry by entry, not rejected or overflowed") {
    const Catalog& c = test::catalog();
    SaveData data(World{c});
    data.world.setTerrain({3, 3}, c.waterTerrain);
    std::string text = serialize(data, c);
    const auto pos = text.find("\"items\": []");
    REQUIRE(pos != std::string::npos);
    std::string items = "\"items\": [";
    items += R"({"id":"oak","x":1.5,"y":2},{"id":"oak","x":2147483647,"y":0},)";
    items += R"({"id":"oak","x":-2147483648,"y":-5},{"id":"oak","x":"7","y":0},{"id":"oak"},)";
    for (int i = 0; i < 2000; ++i) items += R"({"id":"rock","x":5,"y":5},)";
    items += R"({"id":"oak","x":8,"y":8}])";
    text.replace(pos, std::string("\"items\": []").size(), items);
    const auto loaded = deserialize(text, c);
    REQUIRE(loaded.has_value());
    CHECK(loaded->world.items().size() == 2); // one rock, one good oak
    CHECK(loaded->world.itemAt({8, 8}) != nullptr);
    // Warnings are grouped by kind: a handful of lines, not two thousand.
    CHECK(loaded->warnings.size() <= 4);

    // One bad terrain value no longer rejects the whole file.
    std::string cells = "99";
    for (int i = 1; i < c.mapW * c.mapH; ++i) cells += ",0";
    const auto repaired = deserialize(R"({"version":1,"map":{"w":)" + std::to_string(c.mapW) +
                                          R"(,"h":)" + std::to_string(c.mapH) +
                                          R"(},"palette":["grass"],"terrain":[)" + cells + "]}",
                                      c);
    REQUIRE(repaired.has_value());
    CHECK(repaired->world.terrainAt({0, 0}) == c.baseTerrain);
    CHECK(repaired->warnings.size() == 1);
}

TEST_CASE("saves hold only what changed, so a huge world saves small") {
    const Catalog& c = test::catalog();
    SaveData data(World{c, 1024, 512});
    data.world.setTerrain({700, 300}, terrain(c, "path"));
    data.world.addItem(makeItem(c, item(c, "oak"), 0, {701, 300}));
    const std::string text = serialize(data, c);
    CHECK(text.size() < 8000);
    CHECK(text.find("\"chunks\"") != std::string::npos);
    // A chunk edited back to its original state is still fine to load.
    data.world.setTerrain({700, 300}, c.baseTerrain);
    CHECK(serialize(data, c).size() < 8000);
}

TEST_CASE("autosave fires under continuous editing, after quiet moments, and retries later") {
    const double step = tuning::kStepSeconds;
    AutosaveClock a;
    CHECK_FALSE(a.due(step, false)); // nothing to save
    // An edit every 50 frames never leaves a quiet moment, yet a save comes within the maximum.
    double t = 0;
    bool fired = false;
    for (int f = 0; f < 60 * 60 && !fired; ++f) {
        if (f % 50 == 0) a.changed();
        fired = a.due(step, false);
        t += step;
    }
    CHECK(fired);
    CHECK(t <= tuning::kAutosaveMaxDelay + step * 2);
    a.saved();
    CHECK_FALSE(a.dirty());
    // After one change, a quiet moment triggers it, but not during a drag.
    a.changed();
    int frames = 0;
    while (!a.due(step, true) && frames < 60 * 30) ++frames;
    CHECK(frames * step >= tuning::kAutosaveMaxDelay - step * 2); // only the deadline, mid-drag
    a.saved();
    a.changed();
    frames = 0;
    while (!a.due(step, false)) ++frames;
    CHECK(frames * step == doctest::Approx(tuning::kAutosaveDelay).epsilon(0.05));
    // A failure waits before the next attempt.
    a.failed();
    frames = 0;
    while (!a.due(step, false)) ++frames;
    CHECK(frames * step == doctest::Approx(tuning::kSaveRetrySeconds).epsilon(0.02));
}
