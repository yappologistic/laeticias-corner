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

} // namespace

TEST_CASE("the shipped catalog parses and validates") {
    const Catalog& c = test::catalog();
    CHECK(c.mapW == 20);
    CHECK(c.mapH == 20);
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
    CHECK(cottage.smokeAt[0].x == 10);
    CHECK(cottage.smokeAt[0].y == -19);
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
    CHECK_FALSE(broken("\"version\": 1", "\"version\": 7").has_value());
    CHECK_FALSE(broken("\"category\": \"nature\"", "\"category\": \"space\"").has_value());
    CHECK_FALSE(broken("\"footprint\": [3, 2]", "\"footprint\": [0, 2]").has_value());
    CHECK_FALSE(broken("\"on\": \"water\"", "\"on\": \"lava\"").has_value());
    CHECK_FALSE(broken("\"coop\": 1", "\"castle\": 1").has_value());
    CHECK_FALSE(broken("\"id\": \"pine\"", "\"id\": \"oak\"").has_value());
    CHECK_FALSE(broken("\"sfx/cat.wav\"", "\"sfx/dog.wav\"").has_value());
    CHECK_FALSE(broken("[[10, -19], [-2, -15], [-10, -21], [2, -25]]", "[[10, -19]]").has_value());
    CHECK_FALSE(broken("[[10, -19], [-2, -15]", "[[10], [-2, -15]").has_value());
    const auto err = broken("\"layout\": \"connect\"", "\"layout\": \"spiral\"");
    REQUIRE_FALSE(err.has_value());
    CHECK(err.error().find("hedge") != std::string::npos);
}

TEST_CASE("projection matches the contract") {
    CHECK(tileToWorld(0, 0).x == 0);
    CHECK(tileToWorld(1, 0).x == 16);
    CHECK(tileToWorld(1, 0).y == 8);
    CHECK(tileToWorld(0, 1).x == -16);
    CHECK(tileAt({0, 8}) == TilePos{0, 0});     // centre of tile 0,0
    CHECK(tileAt({0, 0.5f}) == TilePos{0, 0});  // just under the top vertex
    CHECK(tileAt({0, 15.5f}) == TilePos{0, 0}); // just above the bottom vertex
    CHECK(tileAt({15.5f, 8}) == TilePos{0, 0}); // right corner
    CHECK(tileAt({16.5f, 9}) == TilePos{1, 0}); // past it, inside the next tile
    CHECK(tileAt({0, 16.5f}) == TilePos{1, 1});
    const Vec2 w = tileToWorld(7, 3);
    CHECK(tileAt({w.x, w.y + 8}) == TilePos{7, 3});
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
    const Item barn = makeItem(c, item(c, "barn"), 0, {17, 18});
    CHECK(canPlace(w, c, barn) == PlaceResult::Ok);
    CHECK(canPlace(w, c, makeItem(c, item(c, "barn"), 0, {18, 18})) == PlaceResult::OutOfBounds);
    CHECK(canPlace(w, c, makeItem(c, item(c, "barn"), 1, {17, 18})) == PlaceResult::OutOfBounds);
    CHECK(canPlace(w, c, makeItem(c, item(c, "oak"), 0, {-1, 0})) == PlaceResult::OutOfBounds);
    w.addItem(barn);
    CHECK(canPlace(w, c, makeItem(c, item(c, "oak"), 0, {19, 19})) == PlaceResult::Occupied);
    CHECK(canPlace(w, c, makeItem(c, item(c, "oak"), 0, {16, 19})) == PlaceResult::Ok);
    // A 2x2 overlapping a single tile of the barn.
    CHECK(canPlace(w, c, makeItem(c, item(c, "cottage"), 0, {16, 17})) == PlaceResult::Occupied);

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
    CHECK(canPaint(w, c, {20, 6}, path) == PaintResult::OutOfBounds);
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
    CHECK(ed.paint(w, c, {30, 30}, path) == PaintResult::OutOfBounds);
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
    CHECK(parsePhase("dusk") == Phase::Dusk);
    CHECK_FALSE(parsePhase("noon"));
    CHECK(parsePin("auto") == ClockPin::Auto);

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
    CHECK(desiredCount(duck, w, false) == 0);
    w.setTerrain({5, 0}, water);
    CHECK(desiredCount(duck, w, false) == tuning::kVisitorsPerNeed);
    for (int x = 0; x < 20; ++x) w.setTerrain({x, 1}, water);
    CHECK(desiredCount(duck, w, false) == duck.max);

    w.addItem(makeItem(c, item(c, "flowers_red"), 0, {5, 5}));
    w.addItem(makeItem(c, item(c, "flowers_white"), 0, {6, 5}));
    w.addItem(makeItem(c, item(c, "flowers_violet"), 0, {7, 5}));
    CHECK(desiredCount(butterfly, w, false) == 0);
    w.addItem(makeItem(c, item(c, "flowers_red"), 0, {8, 5}));
    CHECK(desiredCount(butterfly, w, false) > 0);
    CHECK(desiredCount(butterfly, w, true) == 0); // day visitor

    for (int x = 0; x < 3; ++x) w.addItem(makeItem(c, item(c, "tall_grass"), 0, {x, 8}));
    CHECK(desiredCount(firefly, w, false) == 0);
    CHECK(desiredCount(firefly, w, true) > 0);

    w.addItem(makeItem(c, item(c, "cottage"), 0, {10, 10}));
    w.addItem(makeItem(c, item(c, "cottage"), 0, {14, 10}));
    CHECK(desiredCount(cat, w, true) == 1); // max 1
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
        vis.update(w, c, false, static_cast<float>(tuning::kStepSeconds), rng);
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
    CHECK(vis.present(duckId) ==
          desiredCount(c.visitors[static_cast<std::size_t>(duckId)], w, false));
    CHECK(arrivals == vis.present(duckId));

    // Drain the pond: the ducks fade away.
    for (int y = 4; y < 8; ++y)
        for (int x = 4; x < 8; ++x) w.setTerrain({x, y}, c.baseTerrain);
    for (int i = 0; i < 60 * 5; ++i)
        vis.update(w, c, false, static_cast<float>(tuning::kStepSeconds), rng);
    CHECK(vis.critters().empty());
}

TEST_CASE("populate spawns the full population without events") {
    const Catalog& c = test::catalog();
    const World w = makeStarterWorld(c);
    Rng rng(3);
    Visitors vis(c);
    vis.populate(w, c, true, rng);
    CHECK(vis.events().empty());
    const int ducks = vis.present(*c.findVisitor("duck"));
    CHECK(ducks > 0);
    CHECK(vis.present(*c.findVisitor("firefly")) > 0);
    CHECK(vis.present(*c.findVisitor("butterfly")) == 0);
}

TEST_CASE("the starter scene is pleasant and valid") {
    const Catalog& c = test::catalog();
    const World w = makeStarterWorld(c);
    CHECK(w.items().size() > 20);
    CHECK(w.terrainCount(terrain(c, "water")) >= 6);
    CHECK(w.terrainCount(terrain(c, "path")) > 10);
    for (const Item& it : w.items()) {
        World probe(c);
        for (int y = 0; y < 20; ++y)
            for (int x = 0; x < 20; ++x) probe.setTerrain({x, y}, w.terrainAt({x, y}));
        CHECK(canPlace(probe, c, it) == PlaceResult::Ok);
    }
}

TEST_CASE("save round trip") {
    const Catalog& c = test::catalog();
    SaveData data(makeStarterWorld(c));
    data.world.addItem(makeItem(c, item(c, "barn"), 3, {2, 17}));
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
    for (int y = 0; y < 20; ++y)
        for (int x = 0; x < 20; ++x)
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
    CHECK_FALSE(deserialize("{\"version\": 1, \"map\": {\"w\": 5, \"h\": 5}}", c).has_value());

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
