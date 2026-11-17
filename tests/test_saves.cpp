// World save version 3, migration of real saves from versions 1 and 2, folder names, profile.

#include "core/edit.hpp"
#include "core/land.hpp"
#include "core/save.hpp"
#include "core/starter.hpp"
#include "test_support.hpp"

#include <doctest.h>

#include <algorithm>

using namespace lc;

namespace {

int item(std::string_view id) {
    return *test::catalog().findItem(id);
}

std::string fixture(std::string_view name) {
    auto text = readTextFile(std::filesystem::path(LC_TEST_FIXTURES_DIR) / name);
    REQUIRE(text.has_value());
    return *text;
}

bool sameWorld(const World& a, const World& b) {
    if (a.width() != b.width() || a.height() != b.height() || a.items().size() != b.items().size())
        return false;
    for (int y = 0; y < a.height(); ++y)
        for (int x = 0; x < a.width(); ++x)
            if (a.terrainAt({x, y}) != b.terrainAt({x, y}) || a.isWild({x, y}) != b.isWild({x, y}))
                return false;
    return std::ranges::all_of(a.items(), [&](const Item& it) {
        const Item* o = b.itemAt(it.pos);
        return o != nullptr && *o == it && o->stage == it.stage && o->growth == it.growth;
    });
}

} // namespace

TEST_CASE("world saves round-trip everything: home, progress, clock, calendar, camera") {
    const Catalog& c = test::catalog();
    SaveData data(makeStarterWorld(c), c);
    std::vector<Item> revealed;
    openStage(data.world, c, 1, revealed);
    data.progress.stage = 1;
    CHECK_FALSE(revealed.empty());
    const Item bed = makeItem(c, item("planter"), 2, {30, 31});
    data.world.addItem(bed);
    data.world.setGrowth(data.world.items().size() - 1, 2, 0.375f);
    Progress& p = data.progress;
    p.unlock(c.wishes[0].reward, true);
    p.wishes[0].state = WishState::Done;
    p.granted = {0};
    p.wishes[1].state = WishState::Open;
    p.open = {1};
    p.wishes[6].snoozedUntil = 812.5;
    p.lastOffer = 640.25;
    p.clues[static_cast<std::size_t>(*c.findVisitor("owl"))] = 1;
    p.nooks[0] = 1;
    p.harvests = 3;
    p.lastHarvestDay = 5;
    data.name = "Plum Hollow";
    data.created = "2026-11-17T10:42:00Z";
    data.played = 5234.5;
    data.clockTime = 0.31;
    data.pin = ClockPin::Dusk;
    data.day = 7;
    data.seasonPin = 3;
    data.rain = true;
    data.seen = {"duck", "cat"};
    data.camera = Vec2{29.5f, 30.25f};
    data.zoom = 2;

    const std::string text = serialize(data, c);
    CHECK(text.find("\"version\": 3") != std::string::npos);
    const auto loaded = deserialize(text, c);
    REQUIRE(loaded.has_value());
    CHECK(loaded->warnings.empty());
    CHECK(sameWorld(loaded->world, data.world));
    const Item* g = loaded->world.itemAt({30, 31});
    REQUIRE(g != nullptr);
    CHECK(g->stage == 2);
    CHECK(g->growth == doctest::Approx(0.375f));
    const Progress& q = loaded->progress;
    CHECK(q.items == p.items);
    CHECK(q.terrain == p.terrain);
    CHECK(q.newItems == p.newItems);
    CHECK(q.frames == p.frames);
    CHECK(q.granted == p.granted);
    CHECK(q.open == p.open);
    CHECK(q.wishes[6].snoozedUntil == doctest::Approx(812.5));
    CHECK(q.lastOffer == doctest::Approx(640.25));
    CHECK(q.clues == p.clues);
    CHECK(q.nooks == p.nooks);
    CHECK(q.harvests == 3);
    CHECK(q.lastHarvestDay == 5);
    CHECK(q.stage == 1);
    CHECK(loaded->name == "Plum Hollow");
    CHECK(loaded->created == data.created);
    CHECK(loaded->played == doctest::Approx(5234.5));
    CHECK(loaded->pin == ClockPin::Dusk);
    CHECK(loaded->day == 7);
    CHECK(loaded->seasonPin == 3);
    CHECK(loaded->rain);
    CHECK(loaded->seen == data.seen);
    REQUIRE(loaded->camera.has_value());
    CHECK(loaded->camera->x == doctest::Approx(29.5f));
    CHECK(loaded->zoom == doctest::Approx(2.0f));
    CHECK(serialize(*loaded, c) == text);
}

TEST_CASE("corrupt, newer, damaged and odd world saves are handled") {
    const Catalog& c = test::catalog();
    CHECK_FALSE(deserialize("", c).has_value());
    CHECK_FALSE(deserialize("{\"version\": 3, \"home\": [", c).has_value());
    CHECK_FALSE(deserialize("[1,2,3]", c).has_value());
    CHECK_FALSE(deserialize("{\"home\": {}}", c).has_value());
    CHECK_FALSE(deserialize("{\"version\": 4}", c).has_value());
    CHECK_FALSE(deserialize("{\"version\": 3}", c).has_value()); // no home region
    CHECK_FALSE(deserialize("{\"version\": 1.5}", c).has_value());

    SaveData data(makeStarterWorld(c), c);
    std::string text = serialize(data, c);
    const auto replace = [&](std::string_view from, std::string_view to) {
        const auto pos = text.find(from);
        REQUIRE(pos != std::string::npos);
        text.replace(pos, from.size(), to);
    };
    replace("\"id\": \"bench\"", "\"id\": \"baobab\"");
    replace("\"unlocked\": [", "\"unlocked\": [\"jetpack\", ");
    // Things on wild land (only a hand-edited file could put them there) are dropped.
    replace("\"items\": [",
            "\"items\": [{\"id\": \"oak\", \"x\": 3, \"y\": 3, \"v\": 0}, "
            "{\"id\": \"planter\", \"x\": 21, \"y\": 39, \"v\": 0, \"g\": [9, 0.5]}, "
            "{\"id\": \"oak\", \"x\": 1.5, \"y\": 30}, ");
    const auto loaded = deserialize(text, c);
    REQUIRE(loaded.has_value()); // repaired entry by entry, not rejected
    CHECK(loaded->world.itemCount(item("bench")) == 0);
    CHECK(loaded->world.itemAt({3, 3}) == nullptr);
    REQUIRE(loaded->world.itemAt({21, 39}) != nullptr);
    CHECK(loaded->world.itemAt({21, 39})->stage == 0); // bad growth starts over
    CHECK(loaded->progress.items[static_cast<std::size_t>(item("oak"))] == 1);
    const auto said = [&](std::string_view what) {
        return std::ranges::any_of(loaded->warnings, [&](const std::string& w) {
            return w.find(what) != std::string::npos;
        });
    };
    CHECK(said("baobab"));
    CHECK(said("jetpack"));
    CHECK(said("growth"));
    CHECK(loaded->warnings.size() <= 6);
}

TEST_CASE("a real first-release save becomes the front corner of a version 3 world") {
    const Catalog& c = test::catalog();
    auto data = deserialize(fixture("save_v1.json"), c);
    REQUIRE(data.has_value());
    CHECK(data->fromVersion == 1);
    CHECK(data->muted); // moves to the profile
    // The 20 x 20 map sits at (+20, +20): exactly the first land stage.
    const Item* cottage = data->world.itemAt({35, 35});
    REQUIRE(cottage != nullptr);
    CHECK(cottage->type == item("cottage"));
    CHECK(data->world.itemAt({29, 31})->type == item("planter"));
    CHECK(data->world.items().size() == 31);
    migrateLegacy(*data, c);
    CHECK(data->progress.stage == 0);
    for (int y = 0; y < c.mapH; ++y)
        for (int x = 0; x < c.mapW; ++x) CHECK(data->world.isWild({x, y}) == (x < 20 || y < 20));
    // Every original piece stays unlocked; the eleven new ones still come from wishes.
    for (const int i : c.legacy.items)
        CHECK(data->progress.items[static_cast<std::size_t>(i)] == 1);
    for (const int t : c.legacy.terrain)
        CHECK(data->progress.terrain[static_cast<std::size_t>(t)] == 1);
    CHECK(std::ranges::count(data->progress.items, std::uint8_t{1}) == 31);
    CHECK(data->progress.items[static_cast<std::size_t>(item("apple_tree"))] == 0);
    // Wishes whose rewards it already has are quietly done; the rest wait.
    const auto done = [&](std::string_view id) {
        return data->progress.wishes[static_cast<std::size_t>(*c.findWish(id))].state ==
               WishState::Done;
    };
    CHECK(done("first_flowers"));
    CHECK(done("a_roof"));
    CHECK(done("path_to_door"));
    CHECK_FALSE(done("little_wood"));   // apple tree is new
    CHECK_FALSE(done("garden_gate"));   // a frame
    CHECK_FALSE(done("winter_greens")); // a clue
    CHECK(data->progress.newItems == std::vector<std::uint8_t>(c.items.size(), 0));
    // Beds looked ripe, so they are; the journal became the seen list.
    CHECK(data->world.itemAt({29, 31})->stage ==
          c.items[static_cast<std::size_t>(item("planter"))].growth.stages - 1);
    CHECK(data->seen == std::vector<std::string>{"duck", "cat", "firefly"});
    CHECK(data->day == 0);
    CHECK(data->pin == ClockPin::Dusk);
    // Written as version 3, it round-trips.
    const std::string v3 = serialize(*data, c);
    const auto again = deserialize(v3, c);
    REQUIRE(again.has_value());
    CHECK(again->warnings.empty());
    CHECK(sameWorld(again->world, data->world));
    CHECK(serialize(*again, c) == v3);
}

TEST_CASE("a real chunked save keeps everything, opening the stages it built on") {
    const Catalog& c = test::catalog();
    auto data = deserialize(fixture("save_v2.json"), c);
    REQUIRE(data.has_value());
    CHECK(data->fromVersion == 2);
    const std::size_t items = data->world.items().size();
    CHECK(items == 42);
    const World before = data->world;
    migrateLegacy(*data, c);
    // Its starter scene reached into the high wood, so every stage is open, and no reveal was
    // written over what the player made.
    CHECK(data->progress.stage == static_cast<int>(c.stages.size()) - 1);
    CHECK(data->world.items().size() == items);
    CHECK(data->world.wildCount() == 0);
    for (int y = 0; y < c.mapH; ++y)
        for (int x = 0; x < c.mapW; ++x)
            CHECK(data->world.terrainAt({x, y}) == before.terrainAt({x, y}));
    CHECK(data->world.itemAt({12, 16})->type == item("cottage"));
    CHECK(data->seen == std::vector<std::string>{"duck", "cat"});
}

TEST_CASE("world folder names and the profile") {
    const std::vector<std::string> none;
    CHECK(worldSlug("Laeticia's Corner", none) == "laeticias-corner");
    CHECK(worldSlug("Laeticia\xE2\x80\x99s Corner", none) == "laeticias-corner");
    CHECK(worldSlug("Plum Hollow", none) == "plum-hollow");
    CHECK(worldSlug("  --Fern bank!! ", none) == "fern-bank");
    CHECK(worldSlug("", none) == "world");
    CHECK(worldSlug("\xE6\x97\xA5\xE6\x9C\xAC", none) == "world");
    const std::string longName =
        worldSlug("A very long name for a world that goes on and on", none);
    CHECK(longName.size() <= 32);
    CHECK(longName.back() != '-');
    const std::vector<std::string> taken{"plum-hollow", "plum-hollow-2"};
    CHECK(worldSlug("Plum Hollow", taken) == "plum-hollow-3");

    const Profile defaults = parseProfile("{ not json");
    CHECK_FALSE(defaults.muted);
    CHECK(defaults.lastWorld.empty());
    const Profile odd = parseProfile(R"({"muted": "yes", "last_world": "plum-hollow"})");
    CHECK_FALSE(odd.muted); // a bad field falls back alone
    CHECK(odd.lastWorld == "plum-hollow");
    Profile p;
    p.muted = true;
    p.lastWorld = "fern-bank";
    const Profile back = parseProfile(serialize(p));
    CHECK(back.muted);
    CHECK(back.lastWorld == "fern-bank");
    CHECK(utcNow().size() == 20);
}
