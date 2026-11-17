// The living corner's logic: actor kinds read from the catalog, routines and their steps,
// slots and reservations, path-finding, schedules, reactions to the world changing, petting
// and startling, the resident's day, events, weather, speech and the liveliness measure.

#include "core/actors.hpp"
#include "core/edit.hpp"
#include "core/events.hpp"
#include "core/lively.hpp"
#include "core/path.hpp"
#include "core/speech.hpp"
#include "core/starter.hpp"
#include "core/tuning.hpp"
#include "core/weather.hpp"
#include "test_support.hpp"

#include <doctest.h>
#include <nlohmann/json.hpp>

#include <algorithm>
#include <cmath>
#include <map>
#include <set>

using namespace lc;

namespace {

int item(std::string_view id) {
    return *test::catalog().findItem(id);
}

TilePos tileOf(Vec2 p) {
    return {static_cast<int>(std::floor(p.x)), static_cast<int>(std::floor(p.y))};
}

// A corner with actors in it, stepped like the game steps it.
struct Life {
    const Catalog& cat;
    World world;
    Actors actors;
    std::vector<VisitorGate> gates;
    std::vector<int> present;
    std::vector<std::uint8_t> seen;
    std::vector<std::uint8_t> nooks;
    double clock = 0.2;
    bool pinned = false;
    Phase phase = Phase::Day;
    int season = 1; // summer: everyone may come
    bool raining = false;
    double now = 0;
    std::vector<ActorEvent> log;

    explicit Life(const Catalog& c = test::catalog(), std::uint64_t seed = 1)
        : cat(c), world(c), actors(c, seed), gates(c.visitors.size()),
          present(c.visitors.size(), 0), seen(c.visitors.size(), 0), nooks(c.nooks.size(), 0) {
        for (std::size_t i = 0; i < gates.size(); ++i) gates[i].allowed = !c.visitors[i].rare;
    }
    ActorEnv env() const {
        ActorEnv e;
        e.world = &world;
        e.area = world.bounds();
        e.gates = gates;
        e.clock = clock;
        e.pinned = pinned;
        e.phase = phase;
        e.season = season;
        e.facts.phase = phase;
        e.facts.season = season;
        e.facts.raining = raining;
        e.facts.present = present;
        e.facts.seen = seen;
        e.facts.nookHere = nooks;
        e.now = now;
        return e;
    }
    void step(float dt = static_cast<float>(tuning::kStepSeconds)) {
        now += dt;
        actors.update(env(), dt);
        for (const auto& e : actors.events()) log.push_back(e);
        actors.clearEvents();
        std::ranges::copy(actors.presence(), present.begin());
    }
    void run(double seconds) {
        for (int i = 0; i < static_cast<int>(seconds / tuning::kStepSeconds + 0.5); ++i) step();
    }
    void place(std::string_view id, int x, int y, int v = 0) {
        const Item it = makeItem(cat, item(id), v, {x, y});
        REQUIRE(canPlace(world, cat, it) == PlaceResult::Ok);
        world.addItem(it);
    }
    void water(TileRect r) {
        for (int y = r.y0; y < r.y1; ++y)
            for (int x = r.x0; x < r.x1; ++x) world.setTerrain({x, y}, cat.waterTerrain);
    }
    [[nodiscard]] int kind(std::string_view id) const {
        return static_cast<int>(std::ranges::find(cat.kinds, id, &ActorKind::id) -
                                cat.kinds.begin());
    }
    [[nodiscard]] std::vector<const Actor*> of(std::string_view id) const {
        std::vector<const Actor*> out;
        for (const Actor& a : actors.all())
            if ((a.flags & actor_flag::kAlive) != 0 && a.kind == kind(id)) out.push_back(&a);
        return out;
    }
    [[nodiscard]] const Actor& her() const {
        return actors.all()[static_cast<std::size_t>(actors.resident())];
    }
    [[nodiscard]] std::string anim(const Actor& a) const { return cat.kinds[a.kind].anims[a.anim]; }
};

// The catalog with one change made to its JSON.
Catalog edited(const std::function<void(nlohmann::json&)>& edit) {
    nlohmann::json j = nlohmann::json::parse(test::catalogText());
    edit(j);
    auto c = parseCatalog(j.dump());
    REQUIRE_MESSAGE(c.has_value(), (c ? std::string{} : c.error()));
    return std::move(*c);
}

// No two actors hold the same spot, and no slot holds more than its cap.
void checkReservations(const Life& l) {
    std::map<std::tuple<int, int, int, int>, int> slots;
    std::set<std::tuple<int, int, int, int, int>> spots;
    for (const Actor& a : l.actors.all()) {
        if ((a.flags & actor_flag::kAlive) == 0 || !a.reserved) continue;
        ++slots[{a.resX, a.resY, a.resType, a.resSlot}];
        if (a.resType == 0xFFFF) {
            CHECK(spots.insert({a.resX, a.resY, a.resType, 0, 0}).second);
            continue;
        }
        const ItemDef& def = l.cat.items[a.resType];
        if (a.resSlot < def.slots.size()) {
            const SlotDef& sd = def.slots[a.resSlot];
            CHECK(slots[{a.resX, a.resY, a.resType, a.resSlot}] <= sd.cap);
            if (sd.where == SlotWhere::Beside || sd.spots.front().size() > 1)
                CHECK(spots.insert({a.resX, a.resY, a.resType, a.resSlot, a.resSpot}).second);
        } else {
            CHECK(spots.insert({a.resX, a.resY, a.resType, a.resSlot, a.resSpot}).second);
        }
    }
}

} // namespace

TEST_CASE("actor records are 96 bytes of plain data, and every visitor is read as a kind") {
    static_assert(std::is_trivially_copyable_v<Actor>);
    CHECK(sizeof(Actor) <= 96);
    const Catalog& c = test::catalog();
    REQUIRE(c.kinds.size() == c.visitors.size() + 1);
    for (std::size_t v = 0; v < c.visitors.size(); ++v) {
        CHECK(c.kinds[v].visitor == static_cast<int>(v));
        CHECK(c.kinds[v].anims[0] == "move");
        CHECK(c.kinds[v].anims[1] == "idle");
    }
    const ActorKind& duck = c.kinds[static_cast<std::size_t>(*c.findVisitor("duck"))];
    CHECK(duck.move == Locomotion::Swim);
    CHECK(duck.line);
    CHECK(duck.waddleAnim != 0xFF); // it goes ashore to sleep, so it waddles there
    const ActorKind& cat = c.kinds[static_cast<std::size_t>(*c.findVisitor("cat"))];
    CHECK(cat.watches);
    CHECK(cat.startleFrom == 1u << cat.sleepAnim); // only a sleeping cat startles
    const ActorKind& bee = c.kinds[static_cast<std::size_t>(*c.findVisitor("bee"))];
    CHECK(bee.home == *c.findItem("beehive")); // bees go home to the hive in rain and at dusk
    CHECK_FALSE(bee.interrupts.empty());
    REQUIRE(c.residentKind >= 0);
    const ActorKind& her = c.kinds[static_cast<std::size_t>(c.residentKind)];
    CHECK(her.visitor < 0);
    CHECK(her.home == *c.findItem("cottage"));
    CHECK(her.schedule.size() == 6);
    CHECK(her.carryAnim != 0xFF);
    CHECK(her.rainAnim != 0xFF);
}

TEST_CASE("bad actor data is refused, naming the entry") {
    nlohmann::json j = nlohmann::json::parse(test::catalogText());
    j["resident"]["routines"]["wake"]["steps"][1]["dur"] = "two";
    auto r = parseCatalog(j.dump());
    REQUIRE_FALSE(r.has_value());
    CHECK(r.error().find("resident 'laeticia'") != std::string::npos);
    j = nlohmann::json::parse(test::catalogText());
    j["resident"]["schedule"][0]["routine"] = "nap_all_day";
    r = parseCatalog(j.dump());
    REQUIRE_FALSE(r.has_value());
    CHECK(r.error().find("unknown routine") != std::string::npos);
    j = nlohmann::json::parse(test::catalogText());
    j["resident"]["routines"]["react"]["steps"][0]["effect"] = "dance";
    r = parseCatalog(j.dump());
    REQUIRE_FALSE(r.has_value());
    CHECK(r.error().find("unknown effect") != std::string::npos);
}

TEST_CASE("the resident can be left out entirely") {
    const Catalog c = edited([](nlohmann::json& j) { j["resident"]["enabled"] = false; });
    CHECK(c.residentKind < 0);
    CHECK(c.kinds.size() == c.visitors.size());
    Life l(c);
    l.run(2);
    CHECK(l.actors.resident() < 0);
    CHECK_FALSE(l.actors.residentAvailable());
}

TEST_CASE("visitors arrive, stay in their habitat and leave when unwelcome") {
    Life l;
    const int duck = *l.cat.findVisitor("duck");
    l.water({4, 4, 8, 8});
    int arrivals = 0;
    bool first = false;
    for (int i = 0; i < 60 * 30; ++i) {
        l.step();
        for (const Actor* a : l.of("duck"))
            REQUIRE(passable(l.world, l.cat, Locomotion::Swim, tileOf(a->pos), true));
    }
    for (const ActorEvent& e : l.log) {
        if (e.kind != ActorEvent::Kind::Arrived) continue;
        ++arrivals;
        if (e.first) {
            CHECK_FALSE(first);
            first = true;
        }
    }
    CHECK(first);
    CHECK(l.actors.seen(duck));
    CHECK(l.actors.present(duck) == tuning::kVisitorsPerNeed * 2);
    CHECK(arrivals == l.actors.present(duck));
    // Drain the pond: the ducks go.
    for (int y = 4; y < 8; ++y)
        for (int x = 4; x < 8; ++x) l.world.setTerrain({x, y}, l.cat.baseTerrain);
    l.run(8);
    CHECK(l.of("duck").empty());
}

TEST_CASE("populate places who was there before, without events, and the resident at home") {
    Life l;
    l.world = makeStarterWorld(l.cat);
    for (int x = 22; x < 25; ++x) l.place("tall_grass", x, 38);
    l.phase = Phase::Night;
    l.actors.populate(l.env());
    CHECK(l.actors.events().empty());
    CHECK(l.of("duck").empty()); // nobody seen yet: first sightings must still be events
    for (const char* id : {"duck", "firefly", "butterfly"})
        l.actors.markSeen(*l.cat.findVisitor(id));
    l.actors.populate(l.env());
    CHECK(l.actors.events().empty());
    CHECK(!l.of("duck").empty());
    CHECK(!l.of("firefly").empty());
    CHECK(l.of("butterfly").empty()); // a day visitor
    REQUIRE(l.actors.resident() >= 0);
    // No cottage yet: she is at her bedroll (the starter spot).
    CHECK(tileOf(l.her().pos) == l.cat.starter.resident);
}

TEST_CASE("actors never step onto tiles edited away under them, and step off ones that change") {
    Life l;
    l.water({4, 10, 20, 13});
    l.actors.markSeen(*l.cat.findVisitor("duck"));
    l.actors.populate(l.env());
    REQUIRE(!l.of("duck").empty());
    for (int i = 0; i < 900; ++i) {
        if (i % 50 == 25) {
            const int x = 5 + (i / 50) % 14;
            for (int y = 10; y < 13; ++y) l.world.setTerrain({x, y}, l.cat.baseTerrain);
        }
        std::vector<Actor> before(l.actors.all().begin(), l.actors.all().end());
        l.step();
        for (std::size_t j = 0; j < before.size() && j < l.actors.all().size(); ++j) {
            const Actor& now = l.actors.all()[j];
            if ((now.flags & actor_flag::kAlive) == 0 || (now.flags & actor_flag::kLeaving) != 0 ||
                now.kind != l.kind("duck") || (before[j].flags & actor_flag::kAlive) == 0)
                continue;
            if (!(tileOf(before[j].pos) == tileOf(now.pos)))
                CHECK(passable(l.world, l.cat, Locomotion::Swim, tileOf(now.pos), true));
        }
    }
}

TEST_CASE("a cat whose tile is built on walks off instead of vanishing") {
    Life l;
    l.place("cottage", 20, 20);
    l.actors.markSeen(*l.cat.findVisitor("cat"));
    l.actors.populate(l.env());
    REQUIRE(l.of("cat").size() == 1);
    l.run(1);
    const TilePos t = tileOf(l.of("cat")[0]->pos);
    if (l.world.itemAt(t) == nullptr) l.place("rock", t.x, t.y);
    l.run(3);
    REQUIRE(l.of("cat").size() == 1);
    const Actor& cat = *l.of("cat")[0];
    CHECK((passable(l.world, l.cat, Locomotion::Walk, tileOf(cat.pos)) || cat.reserved));
}

TEST_CASE("visitors live in the active area only") {
    Life l;
    l.world = World(l.cat, 200, 200);
    l.water({150, 150, 160, 160});
    const int duck = *l.cat.findVisitor("duck");
    l.actors.markSeen(duck);
    ActorEnv e = l.env();
    e.area = {0, 0, 64, 64};
    l.actors.populate(e);
    CHECK(l.actors.present(duck) == 0);
    e.area = {128, 128, 192, 192};
    l.actors.populate(e);
    CHECK(l.actors.present(duck) > 0);
    e.area = {0, 0, 64, 64};
    l.actors.update(e, 0.01f);
    CHECK(l.actors.present(duck) == 0);
    std::size_t arrived = 0;
    for (const auto& ev : l.actors.events())
        arrived += ev.kind == ActorEvent::Kind::Arrived ? 1 : 0;
    CHECK(arrived == 0);
    l.actors.clearEvents();
    e.area = {128, 128, 192, 192};
    l.actors.update(e, 0.01f);
    CHECK(l.actors.present(duck) > 0);
    for (const auto& ev : l.actors.events()) CHECK(ev.kind != ActorEvent::Kind::Arrived);
}

TEST_CASE("path-finding: around things, no corner cutting, crossings, wild land, the way") {
    const Catalog& c = test::catalog();
    World w(c, 24, 24);
    PathFinder pf(c);
    std::array<TilePos, 64> out{};
    PathQuery q;
    q.bounds = w.bounds();
    q.from = {2, 2};
    q.to = {10, 2};
    int n = pf.find(w, q, out);
    REQUIRE(n > 0);
    CHECK(out[static_cast<std::size_t>(n - 1)] == TilePos{10, 2});
    // A wall of rocks in the way: it goes round.
    for (int y = 0; y < 6; ++y) w.addItem(makeItem(c, *c.findItem("rock"), 0, {6, y}));
    n = pf.find(w, q, out);
    REQUIRE(n > 0);
    for (int i = 0; i < n; ++i)
        CHECK(passable(w, c, Locomotion::Walk, out[static_cast<std::size_t>(i)]));
    // Fully walled in: no way, and the search stays bounded.
    for (int y = 0; y < 24; ++y)
        if (w.itemAt({6, y}) == nullptr) w.addItem(makeItem(c, *c.findItem("rock"), 0, {6, y}));
    CHECK(pf.find(w, q, out) == 0);
    CHECK(pf.lastExpanded() <= tuning::kPathMaxNodes);
    // Diagonal gaps between two blocks are not squeezed through.
    World d(c, 8, 8);
    d.addItem(makeItem(c, *c.findItem("rock"), 0, {3, 3}));
    d.addItem(makeItem(c, *c.findItem("rock"), 0, {4, 4}));
    q.bounds = d.bounds();
    q.from = {3, 4};
    q.to = {4, 3};
    n = pf.find(d, q, out);
    REQUIRE(n > 0);
    CHECK(n > 1); // not the single diagonal step between the rocks
    // Water needs a crossing; a bridge makes one.
    World r(c, 12, 5);
    for (int y = 0; y < 5; ++y) r.setTerrain({6, y}, c.waterTerrain);
    q.bounds = r.bounds();
    q.from = {2, 2};
    q.to = {10, 2};
    CHECK(pf.find(r, q, out) == 0);
    r.addItem(makeItem(c, *c.findItem("bridge"), 0, {6, 2}));
    CHECK(pf.find(r, q, out) > 0);
    // Wild land is closed.
    r.setWild({6, 2}, true);
    CHECK(pf.find(r, q, out) == 0);
    // A seat (not walkable) can be the goal: it is stepped onto.
    World s(c, 8, 8);
    s.addItem(makeItem(c, *c.findItem("bench"), 0, {5, 5}));
    q.bounds = s.bounds();
    q.from = {1, 1};
    q.to = {5, 5};
    n = pf.find(s, q, out);
    REQUIRE(n > 0);
    CHECK(out[static_cast<std::size_t>(n - 1)] == TilePos{5, 5});
    // Walkers keep to a path when it costs less than cutting across grass.
    World p(c, 20, 20);
    const int path = *c.findTerrain("path");
    for (int x = 2; x <= 17; ++x) p.setTerrain({x, 2}, path);
    for (int y = 2; y <= 17; ++y) p.setTerrain({17, y}, path);
    q.bounds = p.bounds();
    q.from = {2, 2};
    q.to = {17, 17};
    n = pf.find(p, q, out);
    REQUIRE(n > 0);
    for (int i = 0; i < n; ++i) CHECK(p.terrainAt(out[static_cast<std::size_t>(i)]) == path);
}

TEST_CASE("her schedule: the block at each hour, across midnight, and looping a pinned phase") {
    Life l;
    l.run(0.5);
    REQUIRE(l.actors.resident() >= 0);
    const auto& sched = l.cat.kinds[static_cast<std::size_t>(l.cat.residentKind)].schedule;
    const auto blockAt = [&](double t, Phase p) {
        l.clock = t;
        l.phase = p;
        l.step();
        return static_cast<std::uint8_t>(l.actors.scheduleBlock(l.env()));
    };
    const auto routine = [&](std::uint8_t b) {
        return l.cat.program.routines[static_cast<std::size_t>(sched[b].routine)].name;
    };
    // hour = 6 + 24 t: t 0.05 is 07:12 (chores), 0.25 13:00 (leisure), 0.40 15:36 (stroll),
    // 0.55 19:12 (evening), 0.70 22:48 (home), 0.80 01:12 (home, past midnight), 0.89 03:21 (wake).
    CHECK(routine(blockAt(0.05, Phase::Day)) == "chores");
    CHECK(routine(blockAt(0.25, Phase::Day)) == "leisure");
    CHECK(routine(blockAt(0.40, Phase::Day)) == "stroll");
    CHECK(routine(blockAt(0.55, Phase::Dusk)) == "evening");
    CHECK(routine(blockAt(0.70, Phase::Night)) == "home");
    CHECK(routine(blockAt(0.80, Phase::Night)) == "home");
    CHECK(routine(blockAt(0.89, Phase::Dawn)) == "wake");
    // A pinned dusk keeps her in the evening; a pinned day loops chores, leisure and stroll.
    l.pinned = true;
    CHECK(routine(blockAt(0.25, Phase::Dusk)) == "evening");
    std::set<std::string> seen;
    l.clock = 0.25;
    l.phase = Phase::Day;
    for (int i = 0; i < 12 * 60; ++i) {
        l.run(1);
        seen.insert(routine(static_cast<std::uint8_t>(l.actors.scheduleBlock(l.env()))));
    }
    // ...and she follows it between activities.
    CHECK(l.her().sched != 0xFF);
    CHECK(seen == std::set<std::string>{"chores", "leisure", "stroll"});
}

TEST_CASE("she sits on a seat, never shares it, and steps off when it is taken away") {
    Life l;
    l.world = makeStarterWorld(l.cat);
    l.clock = 0.25; // leisure
    l.run(90);
    // Somewhere in that time she sat (the starter bench is the only seat).
    bool sat = false;
    for (int i = 0; i < 120 * 60 && !sat; ++i) {
        l.step();
        sat = l.her().state == ActorState::Act && l.her().lift > 0;
        checkReservations(l);
    }
    REQUIRE(sat);
    const Item* bench = l.world.itemAt(tileOf(l.her().pos));
    REQUIRE(bench != nullptr);
    CHECK(l.cat.items[bench->type].id == "bench");
    CHECK(l.her().resType == bench->type);
    // The bench is removed under her: she lets go and stands on open ground.
    const TilePos benchAt = bench->pos;
    l.world.removeItem(*l.world.itemIndexAt(benchAt));
    l.run(2);
    const bool holdsBench = l.her().reserved && l.her().resType == item("bench");
    CHECK_FALSE(holdsBench);
    CHECK(l.her().lift == 0.0f);
    CHECK(passable(l.world, l.cat, Locomotion::Walk, tileOf(l.her().pos)));
}

TEST_CASE("water painted under her: she steps aside to dry land") {
    Life l;
    l.world = makeStarterWorld(l.cat);
    l.run(1);
    // When she is standing somewhere open (not on a seat), the ground under her turns to water.
    for (int i = 0; i < 60 * 60 && l.world.itemAt(tileOf(l.her().pos)) != nullptr; ++i) l.step();
    const TilePos t = tileOf(l.her().pos);
    REQUIRE(l.world.itemAt(t) == nullptr);
    l.world.setTerrain(t, l.cat.waterTerrain);
    l.run(3);
    CHECK(tileOf(l.her().pos) != t);
    const Item* under = l.world.itemAt(tileOf(l.her().pos));
    const bool onSeat = under != nullptr && l.her().reserved && under->type == l.her().resType;
    CHECK((passable(l.world, l.cat, Locomotion::Walk, tileOf(l.her().pos)) || onSeat));
}

TEST_CASE("a busy corner: no two actors ever hold one spot") {
    Life l;
    l.world = makeStarterWorld(l.cat);
    for (const auto& [id, x, y] : {std::tuple{"cottage", 32, 30},
                                   {"coop", 26, 32},
                                   {"beehive", 36, 31},
                                   {"flowers_red", 34, 28},
                                   {"flowers_white", 35, 28},
                                   {"flowers_violet", 36, 28},
                                   {"flowers_red", 36, 29},
                                   {"campfire", 30, 36},
                                   {"planter", 24, 33},
                                   {"stump", 27, 27}})
        l.place(id, x, y);
    for (int i = 0; i < 90 * 60; ++i) {
        l.step();
        if (i % 30 == 0) checkReservations(l);
    }
    CHECK(!l.of("hen").empty());
    CHECK(!l.of("bee").empty());
    CHECK(!l.of("butterfly").empty());
}

TEST_CASE("the same seed gives the same life; another seed another") {
    const auto runWith = [](std::uint64_t seed) {
        Life l(test::catalog(), seed);
        l.world = makeStarterWorld(l.cat);
        l.place("coop", 26, 32);
        l.place("cottage", 32, 30);
        l.run(40);
        std::vector<float> trace;
        for (const Actor& a : l.actors.all()) {
            trace.push_back(a.pos.x);
            trace.push_back(a.pos.y);
        }
        return trace;
    };
    CHECK(runWith(3) == runWith(3));
    CHECK(runWith(3) != runWith(4));
}

TEST_CASE("ducks swim in a line, and the line keeps its spacing") {
    Life l;
    l.water({2, 2, 18, 18});
    l.actors.markSeen(*l.cat.findVisitor("duck"));
    l.actors.populate(l.env());
    l.run(30);
    const auto ducks = l.of("duck");
    REQUIRE(ducks.size() >= 2);
    int followers = 0;
    for (const Actor* d : ducks) followers += (d->flags & actor_flag::kFollower) != 0 ? 1 : 0;
    CHECK(followers == static_cast<int>(ducks.size()) - 1);
    // Each follower stays close behind the one ahead of it.
    for (std::size_t i = 1; i < ducks.size(); ++i) {
        const float d = std::hypot(ducks[i]->pos.x - ducks[i - 1]->pos.x,
                                   ducks[i]->pos.y - ducks[i - 1]->pos.y);
        CHECK(d < tuning::kLineSpacing * 3.0f);
    }
}

TEST_CASE("petting: a heart, then a cooldown; she answers a click, then waits") {
    Life l;
    l.place("coop", 10, 10);
    l.run(12);
    const auto hens = l.of("hen");
    REQUIRE(!hens.empty());
    const int hen = static_cast<int>(hens[0] - l.actors.all().data());
    CHECK(l.actors.pet(hen));
    CHECK_FALSE(l.actors.pet(hen)); // cooling down
    REQUIRE(!l.actors.events().empty());
    CHECK(l.actors.events().back().kind == ActorEvent::Kind::Pet);
    CHECK(l.actors.all()[static_cast<std::size_t>(hen)].overlay > 0);
    l.run(tuning::kPetCooldown + 0.5);
    CHECK(l.actors.pet(hen));
    // Clicking her: a click line, and not again for a while.
    REQUIRE(l.actors.resident() >= 0);
    l.actors.clearEvents();
    CHECK(l.actors.pet(l.actors.resident()));
    REQUIRE(!l.actors.events().empty());
    CHECK(l.actors.events().back().kind == ActorEvent::Kind::Say);
    CHECK(l.actors.events().back().arg == l.cat.resident.context("click"));
    CHECK_FALSE(l.actors.pet(l.actors.resident()));
}

TEST_CASE("startle: placements near a duck send it off; a cat only from sleep") {
    Life l;
    l.water({2, 2, 14, 14});
    l.actors.markSeen(*l.cat.findVisitor("duck"));
    l.actors.populate(l.env());
    l.run(2);
    const auto ducks = l.of("duck");
    REQUIRE(!ducks.empty());
    const Vec2 p = ducks[0]->pos;
    const TilePos t = tileOf(p);
    l.actors.disturb(l.env(), {t.x + 1, t.y, t.x + 2, t.y + 1}, item("lily_pads"), false);
    bool startled = false;
    for (const ActorEvent& e : l.actors.events())
        startled = startled || e.kind == ActorEvent::Kind::Startle;
    CHECK(startled);
    // Far away: nothing.
    l.actors.clearEvents();
    l.run(6);
    l.actors.clearEvents();
    l.actors.disturb(l.env(), {30, 30, 31, 31}, item("rock"), false);
    for (const ActorEvent& e : l.actors.events()) CHECK(e.kind != ActorEvent::Kind::Startle);
    // An awake cat does not mind; only its sleep is disturbed.
    Life c;
    c.place("cottage", 10, 10);
    c.actors.markSeen(*c.cat.findVisitor("cat"));
    c.actors.populate(c.env());
    c.run(0.5);
    const auto cats = c.of("cat");
    REQUIRE(cats.size() == 1);
    const Actor& cat = *cats[0];
    const TilePos ct = tileOf(cat.pos);
    if (!c.actors.asleep(cat)) {
        c.actors.clearEvents();
        c.actors.disturb(c.env(), {ct.x, ct.y + 1, ct.x + 1, ct.y + 2}, item("rock"), false);
        for (const ActorEvent& e : c.actors.events()) CHECK(e.kind != ActorEvent::Kind::Startle);
    }
}

TEST_CASE("hens go into the coop at night and come out of it in the morning") {
    Life l;
    l.place("coop", 10, 10);
    l.run(15);
    REQUIRE(!l.of("hen").empty());
    l.phase = Phase::Night;
    l.clock = 0.7;
    // They walk to the coop's door and go in; none simply fades where it stands.
    for (int i = 0; i < 60 * 60 && !l.of("hen").empty(); ++i) {
        l.step();
        for (const Actor* h : l.of("hen"))
            if (h->alpha < 0.5f && (h->flags & actor_flag::kLeaving) != 0)
                CHECK(std::hypot(h->pos.x - 11.5f, h->pos.y - 10.5f) < 1.5f);
    }
    CHECK(l.of("hen").empty());
    l.phase = Phase::Dawn;
    l.clock = 0.9;
    l.log.clear();
    l.run(4);
    REQUIRE(!l.of("hen").empty());
    // Out of the coop's door (tile 11, 10 for rotation 0).
    int out = 0;
    for (const ActorEvent& e : l.log)
        if (e.kind == ActorEvent::Kind::Arrived) {
            ++out;
            CHECK(std::hypot(e.pos.x - 11.5f, e.pos.y - 10.5f) < 0.6f);
        }
    CHECK(out > 0);
}

TEST_CASE("bees go between the flowers and the hive, and shelter there in rain") {
    Life l;
    l.place("beehive", 10, 10);
    for (int x = 7; x < 13; ++x) l.place("flowers_red", x, 13);
    l.run(5);
    REQUIRE(!l.of("bee").empty());
    bool inside = false;
    bool sipping = false;
    for (int i = 0; i < 60 * 60; ++i) {
        l.step();
        for (const Actor* b : l.of("bee")) {
            inside = inside || b->state == ActorState::Inside;
            sipping = sipping || (b->state == ActorState::Act && b->lift > 0);
        }
    }
    CHECK(inside);
    CHECK(sipping);
    l.raining = true;
    l.run(25);
    for (const Actor* b : l.of("bee")) CHECK(b->state == ActorState::Inside);
}

TEST_CASE("chores: she waters each bed once a day, then feeds the hens at the coop") {
    Life l;
    l.world = makeStarterWorld(l.cat);
    l.place("planter", 24, 33);
    l.place("planter", 26, 33);
    l.place("coop", 26, 30);
    l.clock = 0.0; // 06:00: chores
    l.run(120);
    std::set<std::pair<int, int>> watered;
    int fed = 0;
    for (const ActorEvent& e : l.log) {
        if (e.kind != ActorEvent::Kind::Effect) continue;
        if (static_cast<Effect>(e.arg) == Effect::WaterBed) {
            CHECK(watered.insert({e.item.x, e.item.y}).second); // once per bed
        }
        if (static_cast<Effect>(e.arg) == Effect::CallHens) ++fed;
    }
    CHECK(watered.size() == 2);
    CHECK(fed == 1);
}

TEST_CASE("she shelters from rain after a moment, then says the rain has stopped") {
    Life l;
    l.world = makeStarterWorld(l.cat);
    l.place("cottage", 32, 30);
    l.clock = 0.25;
    l.run(5);
    l.raining = true;
    l.run(2);
    CHECK(l.her().prio == 0); // not yet: she gives it a few seconds
    l.run(4);
    CHECK(l.her().prio != 0);
    l.run(40);
    CHECK(l.her().state == ActorState::Inside);
    l.log.clear();
    l.raining = false;
    l.run(3);
    bool stopped = false;
    for (const ActorEvent& e : l.log)
        stopped = stopped ||
                  (e.kind == ActorEvent::Kind::Say && e.arg == l.cat.resident.context("rain_stop"));
    CHECK(stopped);
}

TEST_CASE("a placement nearby: she turns and says a line for its kind, then rests her remarks") {
    Life l;
    l.world = makeStarterWorld(l.cat);
    l.run(1);
    const TilePos at = tileOf(l.her().pos);
    l.place("oak", at.x + 2, at.y);
    l.actors.disturb(l.env(), {at.x + 2, at.y, at.x + 3, at.y + 1}, item("oak"), true);
    l.run(1);
    bool said = false;
    for (const ActorEvent& e : l.log)
        said = said ||
               (e.kind == ActorEvent::Kind::Say && e.arg == l.cat.resident.context("place_tree"));
    CHECK(said);
    // Within the cooldown, a fresh placement still gets a word only by chance, never twice.
    l.log.clear();
    l.place("oak", at.x - 2, at.y);
    l.actors.disturb(l.env(), {at.x - 2, at.y, at.x - 1, at.y + 1}, item("oak"), false);
    l.run(3);
    for (const ActorEvent& e : l.log)
        CHECK(!(e.kind == ActorEvent::Kind::Say && e.arg == l.cat.resident.context("place_tree")));
}

TEST_CASE("a harvest nearby: she takes it home, and the chimney gets cooking") {
    Life l;
    l.world = makeStarterWorld(l.cat);
    l.place("cottage", 32, 30);
    l.place("planter", 30, 31);
    l.clock = 0.25;
    l.run(2);
    REQUIRE(l.actors.harvested(l.env(), {30, 31}));
    CHECK(l.her().goodsCount == 1);
    l.run(60);
    bool cooked = false;
    for (const ActorEvent& e : l.log)
        cooked = cooked ||
                 (e.kind == ActorEvent::Kind::Effect && static_cast<Effect>(e.arg) == Effect::Cook);
    CHECK(cooked);
    CHECK(l.her().goodsCount == 0);
}

TEST_CASE("events: a pure plan per seed, cooldowns, spacing and once a day") {
    const Catalog& c = test::catalog();
    World w(c);
    for (int x = 0; x < 10; ++x) w.setTerrain({x, 0}, c.waterTerrain);
    const auto plan = [&](std::uint64_t seed) {
        EventScheduler s(c, seed);
        std::vector<std::pair<int, int>> starts;
        EventEnv e;
        e.world = &w;
        for (int i = 0; i < 60 * 600; ++i) {
            e.now = i * tuning::kStepSeconds;
            e.phase = (i / (60 * 120)) % 2 == 0 ? Phase::Day : Phase::Night;
            s.update(e, static_cast<float>(tuning::kStepSeconds));
            for (const FiredEvent& f : s.fired()) starts.emplace_back(f.event, i);
            s.clearFired();
        }
        return starts;
    };
    const auto a = plan(9);
    CHECK(a == plan(9));
    CHECK(a != plan(10));
    CHECK(!a.empty());
    // Scheduled (window) starts keep at least kEventSpacing apart.
    int last = -1000000;
    for (const auto& [ev, at] : a) {
        if (c.events[static_cast<std::size_t>(ev)].on != EventOn::Window) continue;
        CHECK(at - last >= static_cast<int>(tuning::kEventSpacing * 60) - 1);
        last = at;
    }
    // A rustle needs a tree beside the change, and rests between rustles.
    EventScheduler s(c, 1);
    World t(c);
    t.addItem(makeItem(c, *c.findItem("oak"), 0, {5, 5}));
    s.placed(t, {6, 5, 7, 6}, 10.0);
    s.placed(t, {6, 5, 7, 6}, 10.1);
    s.placed(t, {20, 20, 21, 21}, 20.0);
    CHECK(s.fired().size() == 1);
    // The rainbow follows a long enough shower by day, once a day.
    EventScheduler r(c, 1);
    EventEnv e;
    e.world = &w;
    const auto rain = [&](double from, double to, int day) {
        int rainbows = 0;
        for (double t2 = from; t2 < to; t2 += 0.5) {
            e.now = t2;
            e.day = day;
            e.facts.raining = t2 < to - 1.0;
            r.update(e, 0.5f);
            for (const FiredEvent& f : r.fired())
                rainbows +=
                    c.events[static_cast<std::size_t>(f.event)].show == EventShow::Rainbow ? 1 : 0;
            r.clearFired();
        }
        return rainbows;
    };
    CHECK(rain(0, 30, 0) == 0);    // too short
    CHECK(rain(100, 200, 0) == 1); // long enough
    CHECK(rain(300, 400, 0) == 0); // not twice a day
    CHECK(rain(500, 600, 1) == 1); // the next day again
}

TEST_CASE("weather: a pure plan per seed; asking for rain or clear skies here") {
    const Catalog& c = test::catalog();
    const auto cells = [&](std::uint64_t seed) {
        Weather w(c, seed);
        std::vector<float> out;
        for (int i = 0; i < 60 * 400; ++i) {
            w.update(static_cast<float>(tuning::kStepSeconds), 0, {20, 20, 40, 40});
            if (i % 600 == 0)
                for (const WeatherCell& cell : w.cells()) {
                    out.push_back(cell.centre.x);
                    out.push_back(cell.centre.y);
                }
        }
        return out;
    };
    CHECK(cells(5) == cells(5));
    CHECK(cells(5) != cells(6));
    Weather w(c, 1);
    w.setMode(WeatherMode::Rain);
    w.update(1.0f, 0, {20, 20, 40, 40});
    CHECK(w.raining({25, 25}));
    CHECK(w.raining({0, 0})); // everywhere
    // The ground wets under rain and dries after.
    for (int i = 0; i < 60; ++i) w.update(1.0f, 0, {20, 20, 40, 40});
    const float wet = w.wetness({25, 25});
    CHECK(wet > 0.5f);
    w.setMode(WeatherMode::Clear);
    CHECK_FALSE(w.raining({25, 25}));
    for (int i = 0; i < 60; ++i) w.update(1.0f, 0, {20, 20, 40, 40});
    CHECK(w.wetness({25, 25}) < wet);
    // A gust crosses the region and passes.
    w.gust();
    CHECK(w.gusting());
    for (int i = 0; i < 600 && w.gusting(); ++i)
        w.update(static_cast<float>(tuning::kStepSeconds), 0, {20, 20, 40, 40});
    CHECK_FALSE(w.gusting());
}

TEST_CASE("speech: no line repeats before the others; routine lines wait their turn") {
    const Catalog& c = test::catalog();
    Speech sp(c, 3);
    const int idle = c.resident.context("idle");
    const auto& lines = c.resident.lines[static_cast<std::size_t>(idle)];
    std::set<std::string_view> once;
    for (std::size_t i = 0; i < lines.size(); ++i) CHECK(once.insert(sp.next(idle)).second);
    // One bubble at a time: routine lines do not cut in; important ones do.
    CHECK(sp.offer(c.resident.context("morning"), SpeechWeight::Routine, 10.0));
    CHECK_FALSE(sp.offer(c.resident.context("dusk"), SpeechWeight::Routine, 10.5));
    CHECK(sp.offer(c.resident.context("click"), SpeechWeight::Important, 10.6));
    const Bubble* b = sp.showing(10.7);
    REQUIRE(b != nullptr);
    CHECK(b->context == c.resident.context("click"));
    CHECK(b->end - b->start ==
          doctest::Approx(tuning::kBubbleBase +
                          tuning::kBubblePerChar * static_cast<double>(b->text.size())));
    // After it, a little quiet before the next ordinary line.
    CHECK_FALSE(sp.offer(c.resident.context("dusk"), SpeechWeight::Routine, b->end + 0.5));
    CHECK(sp.offer(c.resident.context("dusk"), SpeechWeight::Routine,
                   b->end + tuning::kBubbleGap + 0.1));
}

TEST_CASE("liveliness: too quiet and too busy both fail") {
    LivelyProbe p;
    for (int s = 0; s < 120; ++s) {
        if (s % 30 == 0) p.happening(s);
        p.sample(4, s);
    }
    CHECK(p.check(3, 20, 1, 3).share() > 0.95f);
    CHECK(p.check(6, 20, 1, 3).share() < 0.05f); // too few movers
    LivelyProbe busy;
    for (int s = 0; s < 120; ++s) {
        busy.happening(s);
        busy.sample(25, s);
    }
    const LivelyReport r = busy.check(3, 20, 1, 3);
    CHECK(r.busy == r.samples);
}
