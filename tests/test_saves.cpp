// World save version 3, migration of real saves from versions 1 and 2, folder names, profile.

#include "core/edit.hpp"
#include "core/land.hpp"
#include "core/rng.hpp"
#include "core/save.hpp"
#include "core/starter.hpp"
#include "core/tuning.hpp"
#include "core/worlds.hpp"
#include "core/writer.hpp"
#include "test_support.hpp"

#include <doctest.h>
#include <nlohmann/json.hpp>

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdlib>
#include <ctime>
#include <expected>
#include <optional>

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
    data.weather = WeatherMode::Clear;
    data.seen = {"duck", "cat"};
    data.camera = Vec2{29.5f, 30.25f};
    data.zoom = 2;

    const std::string text = serialize(data, c);
    CHECK(text.find("\"version\": 4") != std::string::npos);
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
    CHECK(loaded->weather == WeatherMode::Clear);
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

TEST_CASE("one mistyped field or an impossible number never costs the world (QA2-05..09)") {
    const Catalog& c = test::catalog();
    SaveData base(makeStarterWorld(c), c);
    base.played = 400;
    base.progress.lastOffer = 362;
    const std::string original = serialize(base, c);
    const auto edited =
        [&](std::initializer_list<std::pair<std::string_view, std::string_view>> e) {
            std::string text = original;
            for (const auto& [from, to] : e) {
                const auto pos = text.find(from);
                REQUIRE_MESSAGE(pos != std::string::npos, from);
                text.replace(pos, from.size(), to);
            }
            auto loaded = deserialize(text, c);
            REQUIRE(loaded.has_value());
            return std::move(*loaded);
        };
    // Wrongly typed optional fields fall back to their defaults, the rest is kept.
    const SaveData typed = edited({{"\"stage\": 0", "\"stage\": \"2\""},
                                   {"\"played\": 400.0", "\"played\": \"lots\""},
                                   {"\"harvests\": 0", "\"harvests\": [1]"}});
    CHECK(typed.progress.stage == 0);
    CHECK(typed.played == 0.0);
    CHECK(typed.world.items().size() == base.world.items().size());
    CHECK(typed.progress.lastOffer == 0.0); // brought back to the play clock
    CHECK(typed.warnings.size() >= 3);
    // Timers beyond the play clock are brought back, so offers resume.
    const SaveData timers = edited({{"\"last_offer\": 362.0", "\"last_offer\": 1e12"},
                                    {"\"snoozed\": {}", "\"snoozed\": {\"a_roof\": 1e300}"}});
    CHECK(timers.progress.lastOffer == doctest::Approx(400.0));
    CHECK(timers.progress.wishes[static_cast<std::size_t>(*c.findWish("a_roof"))].snoozedUntil <=
          400.0 + tuning::kWishSnooze);
    // Counters too large for play to have made are clamped, never wrapped.
    const SaveData huge = edited(
        {{"\"day\": 0", "\"day\": 2147483647"}, {"\"harvests\": 0", "\"harvests\": 99999999999"}});
    CHECK(huge.day == tuning::kMaxCalendarDay);
    CHECK(huge.progress.harvests == tuning::kMaxHarvests);
    // No more open wishes than the tray holds; the rest wait to be offered again.
    const SaveData open =
        edited({{"\"open\": []", "\"open\": [\"first_flowers\", \"a_roof\", \"path_to_door\", "
                                 "\"cat_bench\", \"three_beds\", \"reading_light\"]"}});
    CHECK(open.progress.open.size() == tuning::kMaxOpenWishes);
    for (const int w : open.progress.open)
        CHECK(open.progress.wishes[static_cast<std::size_t>(w)].state == WishState::Open);
    CHECK(std::ranges::count_if(open.progress.wishes, [](const WishProgress& w) {
              return w.state == WishState::Open;
          }) == tuning::kMaxOpenWishes);
}

TEST_CASE("a view or a growth out of every range is dropped or clamped, never cast (H3-021)") {
    const Catalog& c = test::catalog();
    SaveData data(makeStarterWorld(c), c);
    data.camera = Vec2{20, 20};
    data.worldState.camera = Vec2{40, 1200};
    data.world.addItem(makeItem(c, item("planter"), 0, {30, 31}));
    std::string text = serialize(data, c);
    const auto replace = [&](std::string_view from, std::string_view to) {
        const auto pos = text.find(from);
        REQUIRE(pos != std::string::npos);
        text.replace(pos, from.size(), to);
    };
    replace("\"at\": [\n    40.0,\n    1200.0\n   ]", "\"at\": [1e300, -3e38]");
    replace("\"at\": [\n    20.0,\n    20.0\n   ]", "\"at\": [3e38, 3e38]");
    replace("\"g\": [\n     0,\n     0.0\n    ]", "\"g\": [0, 1e300]");
    const auto loaded = deserialize(text, c);
    REQUIRE(loaded.has_value());
    CHECK_FALSE(loaded->camera.has_value());
    CHECK_FALSE(loaded->worldState.camera.has_value());
    const Item* bed = loaded->world.itemAt({30, 31});
    REQUIRE(bed != nullptr);
    CHECK(bed->growth == 1.0f);
}

TEST_CASE("a newer save is recognised as newer, a damaged one is not (QA2-03)") {
    CHECK(saveFileVersion("{\"version\": 4, \"home\": {}}") == 4);
    CHECK(saveFileVersion("{\"version\": 3}") == 3);
    CHECK(saveFileVersion("{\"version\": 9") == 0);
    CHECK(saveFileVersion("[]") == 0);
    CHECK(saveFileVersion("{\"version\": \"4\"}") == 0);
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
    // Written as the current version, it round-trips.
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

TEST_CASE("a chunked save keeps a water piece across a chunk line (L-011)") {
    // Water on both sides of x = 32, the rowboat (2 x 1, on water) at (31, 25): its origin's
    // chunk is listed first, so its second tile's water comes from the chunk after it.
    const std::string text = R"({"version": 2, "base": "blank", "chunk": 32,
        "palette": ["grass", "meadow", "path", "cobble", "water"],
        "map": {"w": 40, "h": 40}, "clock": {"pin": "none", "t": 0.3},
        "chunks": [
          {"x": 0, "y": 0, "terrain": [[0, 830], [4, 2], [0, 192]],
           "items": [{"id": "rowboat", "v": 0, "x": 31, "y": 25}]},
          {"x": 1, "y": 0, "terrain": [[0, 200], [4, 2], [0, 54]]}
        ]})";
    const Catalog& c = test::catalog();
    const auto data = deserialize(text, c);
    REQUIRE(data.has_value());
    CHECK(data->warnings.empty());
    const Item* boat = data->world.itemAt({32, 25});
    REQUIRE(boat != nullptr);
    CHECK(boat->type == item("rowboat"));
}

TEST_CASE("a postcard is named by the local date its caption shows (L-012)") {
    // 22:30 on 18 November 2026 at six hours west of Greenwich is 04:30 the next day in UTC.
    const char* old = std::getenv("TZ");
    const std::string keep = old != nullptr ? old : "";
    REQUIRE(setenv("TZ", "UTC+6", 1) == 0);
    tzset();
    CHECK(postcardStem("plum-hollow", 1795062600) == "plum-hollow-20261118-223000");
    if (old != nullptr)
        (void)setenv("TZ", keep.c_str(), 1);
    else
        (void)unsetenv("TZ");
    tzset();
}

TEST_CASE("a save cut short or corrupted anywhere is refused or read, never a crash") {
    const Catalog& c = test::catalog();
    for (const char* name : {"save_v1.json", "save_v2.json", "save_v3.json"}) {
        const std::string text = fixture(name);
        CAPTURE(name);
        for (std::size_t k = 0; k < text.size(); k += 1 + text.size() / 400) {
            CAPTURE(k);
            CHECK_NOTHROW((void)deserialize(text.substr(0, k), c));
            std::string flipped = text;
            flipped[k] = static_cast<char>(flipped[k] ^ 0x5A);
            CHECK_NOTHROW((void)deserialize(flipped, c));
        }
    }
}

TEST_CASE("world folder names and the profile") {
    const std::vector<std::string> none;
    CHECK(worldSlug("Laeticia's Corner", none) == "laeticias-corner");
    CHECK(worldSlug("Laeticia\xE2\x80\x99s Corner", none) == "laeticias-corner");
    CHECK(worldSlug("Plum Hollow", none) == "plum-hollow");
    CHECK(worldSlug("  --Fern bank!! ", none) == "fern-bank");
    CHECK(worldSlug("", none) == "world");
    // Other scripts: accented Latin and Greek spelled in Latin, the rest by code point; plain
    // ASCII, readable, and two names in a script without a spelling never meet.
    CHECK(worldSlug("P\xC4\x81rsa", none) == "parsa");                              // Pārsa
    CHECK(worldSlug("Caf\xC3\xA9 de la For\xC3\xAAt", none) == "cafe-de-la-foret"); // Café…
    CHECK(worldSlug("Cafe\xCC\x81", none) == "cafe");                               // e + U+0301
    CHECK(worldSlug("X\xC5\xA1"
                    "ay\xC4\x81r\xC5\xA1\xC4\x81",
                    none) == "xsayarsa");                                           // Xšayāršā
    CHECK(worldSlug("\xCE\x91\xCE\xB8\xCE\xAE\xCE\xBD\xCE\xB1", none) == "athena"); // Αθήνα
    CHECK(worldSlug("\xE1\xBC\x88\xCE\xB8\xE1\xBF\x86\xCE\xBD\xCE\xB1\xCE\xB9", none) ==
          "athenai");                                                   // Ἀθῆναι
    CHECK(worldSlug("\xE6\x97\xA5\xE6\x9C\xAC", none) == "u65e5u672c"); // 日本
    const std::string persian =
        worldSlug("\xD9\xBE\xD8\xA7\xD8\xB1\xD8\xB3\xD9\x87", none);                  // پارسه
    const std::string persian2 = worldSlug("\xD9\xBE\xD8\xA7\xD8\xB1\xD8\xB3", none); // پارس
    CHECK(persian == "u67eu627u631u633u647");
    CHECK(persian2 == "u67eu627u631u633");
    CHECK(persian != persian2);
    CHECK(worldSlug("Rome \xE2\x80\x94 spring", none) == "rome-spring"); // an em dash parts
    CHECK(worldSlug("bad \xFF byte", none) == "bad-byte");
    for (const char* n : {"P\xC4\x81rsa", "\xCE\x91\xCE\xB8\xCE\xAE\xCE\xBD\xCE\xB1",
                          "\xD9\xBE\xD8\xA7\xD8\xB1\xD8\xB3\xD9\x87"}) {
        const std::string slug = worldSlug(n, none);
        CAPTURE(slug);
        CHECK(slug == worldSlug(n, none)); // stable
        CHECK(std::ranges::all_of(slug, [](char ch) {
            return (ch >= 'a' && ch <= 'z') || (ch >= '0' && ch <= '9') || ch == '-';
        }));
    }
    // A name spelled like a world already there gets a folder of its own.
    const std::vector<std::string> parsa{"parsa"};
    CHECK(worldSlug("P\xC4\x81rsa", parsa) == "parsa-2");
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
    p.music = 35;
    p.uiScale = 3; // 125 %
    p.reduceMotion = true;
    p.vsync = false;
    p.frame = "starry";
    p.caption = false;
    p.onboarded = true;
    p.clouds = "shadows";
    const Profile back = parseProfile(serialize(p));
    CHECK(back.clouds == "shadows");
    CHECK(defaults.clouds == "on");
    CHECK(back.muted);
    CHECK(back.lastWorld == "fern-bank");
    CHECK(back.music == 35);
    CHECK(back.effects == 85);
    CHECK(back.uiScale == 3);
    CHECK(back.reduceMotion);
    CHECK_FALSE(back.vsync);
    CHECK(back.frame == "starry");
    CHECK_FALSE(back.caption);
    CHECK(back.onboarded);
    // Out of range or off the 5-step grid: clamped and snapped; an unknown scale is auto.
    const Profile clamped =
        parseProfile(R"({"volume": {"music": 140, "effects": 33}, "ui_scale": 1.1})");
    CHECK(clamped.music == 100);
    CHECK(clamped.effects == 30);
    CHECK(clamped.uiScale == 0);
    CHECK(utcNow().size() == 20);
}

TEST_CASE("the background writer writes, keeps the newest text and reports failures") {
    const auto dir = test::tempDir("writer");
    {
        FileWriter w;
        for (int i = 0; i < 50; ++i) w.write(dir / "a.json", "text " + std::to_string(i));
        w.flush();
        const auto done = w.poll();
        CHECK(done.finished);
        CHECK_FALSE(done.error.has_value());
        CHECK(readTextFile(dir / "a.json").value_or("") == "text 49");
        CHECK_FALSE(w.poll().finished); // nothing new since
        // A path that cannot be a file fails, and says so.
        w.write(dir / "a.json" / "inside", "x");
        w.flush();
        CHECK(w.poll().error.has_value());
        w.write(dir / "b.json", "last words");
    } // the destructor writes what is still waiting
    CHECK(readTextFile(dir / "b.json").value_or("") == "last words");
}

TEST_CASE("the worlds screen's list: names, days, pages, newest first; rename and delete") {
    const Catalog& c = test::catalog();
    const auto dir = test::tempDir("worlds");
    const auto write = [&](const std::string& slug, const std::string& name, int day, int seen) {
        SaveData d(makeStarterWorld(c), c);
        d.name = name;
        d.day = day;
        for (int i = 0; i < seen; ++i) d.seen.push_back(c.visitors[static_cast<std::size_t>(i)].id);
        REQUIRE(writeFileAtomic(dir / slug / "world.json", serialize(d, c)).has_value());
    };
    write("plum-hollow", "Plum Hollow", 7, 3);
    write("fernbank", "Fernbank", 2, 0);
    REQUIRE(writeFileAtomic(dir / "future" / "world.json", R"({"version": 9})").has_value());
    REQUIRE(writeFileAtomic(dir / "broken" / "world.json", "{ oops").has_value());
    std::filesystem::create_directories(dir / "empty");
    // The newest first: give them distinct times.
    using namespace std::chrono_literals;
    const auto t = std::filesystem::file_time_type::clock::now();
    std::filesystem::last_write_time(dir / "plum-hollow" / "world.json", t);
    std::filesystem::last_write_time(dir / "fernbank" / "world.json", t - 60s);
    std::filesystem::last_write_time(dir / "future" / "world.json", t - 120s);
    std::filesystem::last_write_time(dir / "broken" / "world.json", t - 180s);
    const auto list = listWorlds(dir);
    REQUIRE(list.size() == 4); // the empty folder is not a world
    CHECK(list[0].name == "Plum Hollow");
    CHECK(list[0].day == 7);
    CHECK(list[0].pages == 3);
    CHECK(list[1].slug == "fernbank");
    CHECK_FALSE(list[2].readable); // newer
    CHECK_FALSE(list[3].readable); // damaged
    CHECK(list[3].name == "broken");

    CHECK(trimName("  Moss Bank \t") == "Moss Bank");
    CHECK(checkName("", list) == NameProblem::Empty);
    CHECK(checkName("Fernbank", list) == NameProblem::Taken);
    CHECK(checkName("Fernbank", list, "fernbank") == NameProblem::None); // its own name
    CHECK(checkName(std::string(29, 'a'), list) == NameProblem::TooLong);
    CHECK(checkName("Ünïcødé Gärden Ünïcødé Gärde", list) == NameProblem::None); // 28 letters
    CHECK(freshName("Plum Hollow", list) == "Plum Hollow 2");
    CHECK(freshName("Moss Bank", list) == "Moss Bank");

    REQUIRE(renameWorld(dir / "fernbank" / "world.json", "Fern Bank").has_value());
    const auto again = listWorlds(dir);
    CHECK(std::ranges::any_of(again, [](const WorldSummary& w) { return w.name == "Fern Bank"; }));
    // A world from a newer version is not changed.
    const std::string before = readTextFile(dir / "future" / "world.json").value_or("");
    CHECK_FALSE(renameWorld(dir / "future" / "world.json", "Mine now").has_value());
    CHECK(readTextFile(dir / "future" / "world.json").value_or("") == before);
    REQUIRE(deleteWorld(dir / "broken").has_value());
    CHECK_FALSE(std::filesystem::exists(dir / "broken"));
}

TEST_CASE("a version 3 world opens unchanged and is written as version 4 with its view kept") {
    const Catalog& c = test::catalog();
    auto data = deserialize(fixture("save_v3.json"), c);
    REQUIRE(data.has_value());
    CHECK(data->fromVersion == 3);
    CHECK(data->warnings.empty());
    // The home view in home tiles is kept; the world block starts empty.
    REQUIRE(data->camera.has_value());
    CHECK(data->camera->x == doctest::Approx(30));
    CHECK(data->camera->y == doctest::Approx(25));
    CHECK(data->zoom == doctest::Approx(2));
    CHECK_FALSE(data->worldState.camera.has_value());
    CHECK(data->worldState.visited.empty());
    CHECK(data->world.items().size() == 43);
    const std::string v4 = serialize(*data, c);
    CHECK(v4.find("\"version\": 4") != std::string::npos);
    const auto again = deserialize(v4, c);
    REQUIRE(again.has_value());
    CHECK(again->fromVersion == 4);
    CHECK(again->warnings.empty());
    CHECK(sameWorld(again->world, data->world));
    REQUIRE(again->camera.has_value());
    CHECK(again->camera->x == doctest::Approx(30));
    CHECK(serialize(*again, c) == v4);
}

TEST_CASE("the world block keeps the player's delta over the world, and only that") {
    const Catalog& c = test::catalog();
    SaveData data(makeStarterWorld(c), c);
    data.name = "Delta";
    data.worldState.camera = Vec2{376.5f, 69.25f};
    data.worldState.zoom = 0.5f;
    data.worldState.visited = {"corner", "parsa"};
    data.worldState.found = {{"parsa", {"figure:parsa.xerxes", "landmark:parsa.apadana"}}};
    data.worldState.seen = {{"parsa", {"landmark:parsa.gate_of_all_lands"}}};
    data.worldState.flags = {"seam_explained"};
    const std::string text = serialize(data, c);
    // Small: nothing of the prebuilt world goes in.
    CHECK(text.size() < 12000);
    const auto back = deserialize(text, c);
    REQUIRE(back.has_value());
    CHECK(back->warnings.empty());
    const WorldProgress& w = back->worldState;
    REQUIRE(w.camera.has_value());
    CHECK(w.camera->x == doctest::Approx(376.5f));
    CHECK(w.camera->y == doctest::Approx(69.25f));
    CHECK(w.zoom == doctest::Approx(0.5f));
    CHECK(w.visited == data.worldState.visited);
    CHECK(w.found == data.worldState.found);
    CHECK(w.seen == data.worldState.seen);
    CHECK(w.flags == data.worldState.flags);
    CHECK(serialize(*back, c) == text);
    // Damaged parts of the block fall back one by one; duplicates collapse.
    std::string bad = text;
    const auto at = bad.find("\"visited\"");
    REQUIRE(at != std::string::npos);
    bad.replace(at, std::string("\"visited\"").size(), "\"visited\": 7, \"x\"");
    auto tolerant = deserialize(bad, c);
    REQUIRE(tolerant.has_value());
    CHECK(tolerant->worldState.found == data.worldState.found);
}

namespace {

// Hostile replacements for any one value of a save or profile: wrong types, numbers at and past
// every limit, empty and malformed containers, text that is not UTF-8, deep nesting.
constexpr std::string_view kInvalidUtf8 = "\"\xff\xfe\xc3\"";
const std::vector<std::string>& hostileValues() {
    static const std::vector<std::string> v = [] {
        std::vector<std::string> out = {"null",
                                        "true",
                                        "-1",
                                        "0",
                                        "2147483648",
                                        "-9223372036854775808",
                                        "18446744073709551615",
                                        "1e308",
                                        "-1e308",
                                        "3.4e39",
                                        "0.5",
                                        "\"\"",
                                        "\"x\"",
                                        std::string(kInvalidUtf8),
                                        "[]",
                                        "{}",
                                        "[[1, 2], [3]]",
                                        "{\"w\": -5, \"h\": 1e9}"};
        out.push_back(std::string(200, '[') + std::string(200, ']'));
        return out;
    }();
    return v;
}

// Every value's JSON pointer, arrays sampled at their first two and last entries so a long
// terrain list stays cheap.
void pointers(const nlohmann::json& j, const nlohmann::json::json_pointer& at,
              std::vector<nlohmann::json::json_pointer>& out) {
    out.push_back(at);
    if (j.is_object()) {
        for (const auto& [k, v] : j.items()) pointers(v, at / k, out);
    } else if (j.is_array()) {
        for (std::size_t i = 0; i < j.size(); ++i)
            if (i < 2 || i + 1 == j.size()) pointers(j[i], at / i, out);
    }
}

// `doc` with the value at `at` replaced by raw JSON text (which may be invalid UTF-8, so it is
// spliced into the dumped text rather than parsed).
std::string spliced(nlohmann::json doc, const nlohmann::json::json_pointer& at,
                    std::string_view raw) {
    constexpr std::string_view kMark = "@@HOSTILE@@";
    doc[at] = std::string(kMark);
    std::string text = doc.dump();
    const auto pos = text.find(std::string("\"") + std::string(kMark) + "\"");
    REQUIRE(pos != std::string::npos);
    text.replace(pos, kMark.size() + 2, raw);
    return text;
}

} // namespace

TEST_CASE("fuzz: any one value of a save replaced by anything is refused or repaired (H3-003)") {
    const Catalog& c = test::catalog();
    // A version 4 world with something in every section, and the real older saves.
    SaveData data(makeStarterWorld(c), c);
    std::vector<Item> revealed;
    openStage(data.world, c, 1, revealed);
    data.progress.stage = 1;
    data.world.addItem(makeItem(c, item("planter"), 1, {30, 31}));
    data.world.setGrowth(data.world.items().size() - 1, 1, 0.5f);
    data.progress.wishes[0].state = WishState::Done;
    data.progress.granted = {0};
    data.progress.wishes[1].state = WishState::Open;
    data.progress.open = {1};
    data.progress.wishes[2].snoozedUntil = 90;
    data.progress.nooks[0] = 1;
    data.played = 500;
    data.seen = {"duck"};
    data.camera = Vec2{20, 20};
    data.worldState.camera = Vec2{40, 1200};
    data.worldState.visited = {"home", "rome"};
    data.worldState.found = {{"rome", {"landmark:forum"}}};
    data.worldState.seen = {{"rome", {"figure:x"}}};
    data.worldState.flags = {"seam_explained"};
    const std::vector<std::string> sources = {serialize(data, c), fixture("save_v1.json"),
                                              fixture("save_v2.json"), fixture("save_v3.json")};
    Rng rng(0x5A7E);
    int loaded = 0;
    int refused = 0;
    for (const std::string& source : sources) {
        const auto doc = nlohmann::json::parse(source);
        std::vector<nlohmann::json::json_pointer> at;
        pointers(doc, nlohmann::json::json_pointer{}, at);
        // Each value once with a random hostile replacement, removed once, and a random sample
        // of the remaining pairs: bounded time, the same cases every run.
        std::vector<std::string> cases;
        for (const auto& p : at) {
            if (p.empty()) continue;
            const auto& values = hostileValues();
            cases.push_back(spliced(doc, p, values[rng.next() % values.size()]));
            nlohmann::json removed = doc;
            removed[p.parent_pointer()].is_object()
                ? (void)removed[p.parent_pointer()].erase(p.back())
                : removed[p.parent_pointer()].erase(std::stoul(p.back()));
            cases.push_back(removed.dump());
        }
        for (int k = 0; k < 150; ++k) {
            const auto& p = at[1 + rng.next() % (at.size() - 1)];
            const auto& values = hostileValues();
            cases.push_back(spliced(doc, p, values[rng.next() % values.size()]));
        }
        for (const std::string& text : cases) {
            CAPTURE(text.substr(0, 300));
            std::optional<std::expected<SaveData, std::string>> first;
            REQUIRE_NOTHROW(first.emplace(deserialize(text, c)));
            if (!first->has_value()) {
                ++refused;
                continue;
            }
            ++loaded;
            SaveData& d = **first;
            if (d.fromVersion < 3) migrateLegacy(d, c);
            // What was read is something play could have made, and it saves and reads back
            // as itself.
            CHECK(d.clockTime >= 0.0);
            CHECK(d.clockTime < 1.0);
            CHECK(d.day >= 0);
            CHECK(d.day <= tuning::kMaxCalendarDay);
            CHECK(std::isfinite(d.played));
            CHECK(std::isfinite(d.zoom));
            CHECK(std::isfinite(d.worldState.zoom));
            CHECK(d.progress.stage >= 0);
            CHECK(std::cmp_less(d.progress.stage, c.stages.size()));
            CHECK(d.progress.open.size() <= tuning::kMaxOpenWishes);
            CHECK(d.seasonPin < static_cast<int>(c.seasons.size()));
            const std::string again = serialize(d, c);
            const auto back = deserialize(again, c);
            REQUIRE(back.has_value());
            CHECK(back->warnings.empty());
            CHECK(serialize(*back, c) == again);
        }
    }
    CHECK(loaded > 0);
    CHECK(refused > 0);
}

TEST_CASE("fuzz: any one value of a profile replaced by anything falls back field by field") {
    Profile p;
    p.music = 35;
    p.uiScale = 3;
    p.brush = 5;
    p.lastWorld = "plum-hollow";
    const auto doc = nlohmann::json::parse(serialize(p));
    std::vector<nlohmann::json::json_pointer> at;
    pointers(doc, nlohmann::json::json_pointer{}, at);
    for (const auto& ptr : at) {
        if (ptr.empty()) continue;
        for (const std::string& v : hostileValues()) {
            const std::string text = spliced(doc, ptr, v);
            CAPTURE(text);
            Profile q;
            REQUIRE_NOTHROW(q = parseProfile(text));
            CHECK(q.music >= 0);
            CHECK(q.music <= 100);
            CHECK(q.effects >= 0);
            CHECK(q.effects <= 100);
            CHECK(q.ambience >= 0);
            CHECK(q.ambience <= 100);
            CHECK(q.uiScale >= 0);
            CHECK(q.uiScale < kUiScaleCount);
            CHECK((q.brush == 1 || q.brush == 3 || q.brush == 5));
            CHECK(parseProfile(serialize(q)).lastWorld == q.lastWorld);
        }
    }
}

TEST_CASE("a world named like a Windows device gets a folder Windows can make (H3-014)") {
    const std::vector<std::string> none;
    CHECK(worldSlug("Con", none) == "con-world");
    CHECK(worldSlug("NUL", none) == "nul-world");
    CHECK(worldSlug("com1", none) == "com1-world");
    CHECK(worldSlug("LPT9", none) == "lpt9-world");
    CHECK(worldSlug("Aux.", none) == "aux-world");
    CHECK(worldSlug("Console", none) == "console");
    CHECK(worldSlug("com", none) == "com");
    CHECK(worldSlug("com10", none) == "com10");
}

TEST_CASE("a profile's last world opens only a folder directly under worlds/ (H3-005)") {
    CHECK(plainFolderName("plum-hollow"));
    CHECK(plainFolderName(worldSlug("Laeticia's Corner", {})));
    for (const std::string_view bad :
         {std::string_view(""), std::string_view("."), std::string_view(".."),
          std::string_view("../plum"), std::string_view("a/b"), std::string_view("/etc"),
          std::string_view("c:\\x"), std::string_view("a\0b", 3)})
        CHECK_FALSE(plainFolderName(bad));
}
