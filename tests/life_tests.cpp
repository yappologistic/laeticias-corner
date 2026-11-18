// City life (src/life/): the compiled data, walking, the chains against tools/worldgen's
// simulator, the day plan, and the simulation of the three city centres: populations against
// the data, nobody where nobody can stand, slots within capacity, events to completion, the same
// live state for the same clock however often the area comes and goes, byte-identical runs.

#include "life/report.hpp"
#include "life/session.hpp"
#include "world_support.hpp"

#include <doctest.h>
#include <nlohmann/json.hpp>

#include <algorithm>
#include <bit>
#include <climits>
#include <cstdlib>
#include <map>
#include <random>
#include <set>

using namespace lc;
using namespace lc::life;
using namespace lc::wtest;

namespace {

LifeWorld& lifeWorld() {
    static std::unique_ptr<LifeWorld> w = buildLifeWorld(realWorld());
    return *w;
}

TilePos centreOf(std::string_view district) {
    const auto f = parseFocus(lifeWorld(), district);
    REQUIRE(f.has_value());
    return *f;
}

// The season of a city's famous month (world-seasons.md: the regions' pins are gone; at the
// famous month every city shows the crowds it showed before): Rome and Pārsa in spring, Athens in
// summer.
int seasonOf(std::string_view region) {
    const auto& s = lifeWorld().data.seasons;
    const auto at = std::ranges::find(s, region == "athens" ? "summer" : "spring");
    return static_cast<int>(at - s.begin());
}

// The problems the data has today, reported to their owners (out/reports/engine-city-life.md);
// anything else fails.
bool knownProblem(const std::string& p) {
    return p.find("are in no set catalog") != std::string::npos;
}

void step(CityLife& c, LifeClock& clock, int steps) {
    for (int k = 0; k < steps; ++k) {
        clock.t += tuning::kStepSeconds / tuning::kDayLengthSeconds;
        if (clock.t >= 1.0) clock.t -= 1.0;
        if (clock.t >= tuning::kMidnight &&
            clock.t - tuning::kStepSeconds / tuning::kDayLengthSeconds < tuning::kMidnight)
            ++clock.day;
        c.update(clock, static_cast<float>(tuning::kStepSeconds));
    }
}

// Every live person, figure, chain worker and event cast stands on a walkable tile, at the
// tile's level, not on water (ships and caravans follow their lanes).
void checkGround(const CityLife& c) {
    const WorldMap& m = lifeWorld().map();
    int checked = 0;
    c.forEachInfo([&](const CityLife::Info& in) {
        if (in.source == Source::Token) return;
        CAPTURE(in.tile.x);
        CAPTURE(in.tile.y);
        CAPTURE(static_cast<int>(in.source));
        REQUIRE(m.inBounds(in.tile));
        CHECK(m.walkable(in.tile));
        // Where it is drawn, too (smoothed paths cut corners only over walkable ground).
        const TilePos drawn{static_cast<int>(std::floor(in.pos.x)),
                            static_cast<int>(std::floor(in.pos.y))};
        CHECK(m.walkable(drawn));
        const int t = m.terrainAt(in.tile);
        const bool water = t != world::kNone && m.terrainInfo(t).water;
        CHECK((!water || m.itemAt(in.tile) >= 0)); // on water only on a deck or a bridge
        CHECK(in.level == m.level(in.tile));
        ++checked;
    });
    CHECK(checked > 0);
}

void checkSlots(const CityLife& c) {
    c.forEachReservation([&](int group, int count, int cap) {
        CAPTURE(group);
        CHECK(count <= cap);
    });
    // Everyone stands at a spot of the group reserved, and nobody shares a spot while the group
    // has a free one (L-116).
    const LifeWorld& w = c.lifeWorld();
    std::map<int, std::vector<int>> spots;
    c.forEachInfo([&](const CityLife::Info& in) {
        if (in.slot < 0) return;
        CAPTURE(in.slot);
        REQUIRE(in.spot >= 0);
        CHECK(w.slotGroup[static_cast<std::size_t>(in.spot)] ==
              static_cast<std::uint32_t>(in.slot));
        spots[in.slot].push_back(in.spot);
    });
    for (auto& [group, taken] : spots) {
        const auto g = static_cast<std::size_t>(group);
        const std::size_t own = w.groupSpotsAt[g + 1] - w.groupSpotsAt[g];
        std::ranges::sort(taken);
        const auto distinct = static_cast<std::size_t>(
            std::ranges::distance(taken.begin(), std::ranges::unique(taken).begin()));
        CAPTURE(group);
        CHECK(distinct == std::min(taken.size(), own));
    }
}

struct Snapshot {
    std::vector<std::tuple<std::uint64_t, int, int, int, int>> rows; // key, x, y, step, goods
    friend bool operator==(const Snapshot&, const Snapshot&) = default;
};

int sourceOf(const CityLife& c, std::uint64_t key) {
    int out = -1;
    c.forEachInfo([&](const CityLife::Info& in) {
        if (in.key == key) out = static_cast<int>(in.source) * 100 + static_cast<int>(in.state);
    });
    return out;
}

Snapshot snapshot(const CityLife& c) {
    Snapshot s;
    c.forEachInfo([&](const CityLife::Info& in) {
        s.rows.emplace_back(in.key, static_cast<int>(in.pos.x * 16),
                            static_cast<int>(in.pos.y * 16), in.step, in.goods);
    });
    std::ranges::sort(s.rows);
    return s;
}

} // namespace

TEST_CASE("life: every region's life compiles, and what does not resolve is known") {
    const LifeWorld& w = lifeWorld();
    for (const std::string city :
         {"rome", "athens", "parsa", "ostia", "alban_mount", "brundisium"}) {
        CAPTURE(city);
        const int r = w.data.findRegion(city);
        REQUIRE(r >= 0);
        const LifeRegion& reg = w.data.regions[static_cast<std::size_t>(r)];
        CHECK(reg.roles.size() > 10);
        CHECK(!reg.districts.empty());
        CHECK(!reg.events.empty());
        CHECK(w.pathsOf[static_cast<std::size_t>(r)] >= 0);
        int scheduled = 0;
        for (const Role& role : reg.roles) {
            CAPTURE(role.id);
            CHECK(role.kind >= 0);
            // Roles with no day of their own are cast by events (Pārsa's delegations).
            scheduled += role.schedule.empty() ? 0 : 1;
        }
        CHECK(scheduled * 2 > static_cast<int>(reg.roles.size()));
    }
    CHECK(w.data.regions[static_cast<std::size_t>(w.data.findRegion("rome"))].chains.size() == 9);
    CHECK(w.data.regions[static_cast<std::size_t>(w.data.findRegion("athens"))].chains.size() ==
          10);
    CHECK(w.data.regions[static_cast<std::size_t>(w.data.findRegion("parsa"))].chains.size() == 8);
    for (const std::string& p : w.data.problems) {
        const bool known = knownProblem(p);
        CHECK_MESSAGE(known, p);
    }
}

TEST_CASE("life: the walk data's faults are named with their tiles, and nobody is sent there") {
    // Road edges walkers cannot use and slot spots off the walkable ground or out of reach: each
    // named with its grid tile (for worldgen), each routed around (edges left out of walking,
    // such spots never chosen: resolve() stands only where the region's walkers reach).
    const std::vector<std::string> faults = walkProblems(lifeWorld());
    for (const std::string& f : faults) {
        CAPTURE(f);
        CHECK(f.find("at grid (") != std::string::npos);
    }
    MESSAGE(faults.size() << " walk-data faults");
    CityLife city(lifeWorld(), 3);
    for (const char* place : {"forum", "agora", "terrace"}) {
        city.setFocus(centreOf(place));
        LifeClock clock = LifeClock::at(1, 10.0, -1);
        city.settle(clock);
        step(city, clock, 600);
        city.forEachInfo([&](const CityLife::Info& in) {
            if (in.spot < 0) return;
            const world::WorldSlot& s =
                lifeWorld().map().slots()[static_cast<std::size_t>(in.spot)];
            CAPTURE(s.tile.x);
            CAPTURE(s.tile.y);
            CHECK(lifeWorld().map().walkable(in.tile));
        });
    }
}

TEST_CASE("life: courses are worldgen's staircases, tile for tile") {
    const int cols = lifeWorld().map().height();
    const auto grid = [&](int c, int r) { return TilePos{r, cols - 1 - c}; };
    const auto plan = [&](Tile16 g) { return std::pair<int, int>{cols - 1 - g.y, g.x}; };
    std::vector<Tile16> out;
    // worldgen.raster.path_tiles([(0, 0), (3, 1)]) and ([(5, 5), (2, 9), (2, 12)]).
    std::vector<TilePos> a{grid(0, 0), grid(3, 1)};
    pathTiles(a, cols, out);
    std::vector<std::pair<int, int>> got;
    for (const Tile16 t : out) got.push_back(plan(t));
    CHECK(got == std::vector<std::pair<int, int>>{{0, 0}, {1, 0}, {2, 0}, {2, 1}, {3, 1}});
    std::vector<TilePos> b{grid(5, 5), grid(2, 9), grid(2, 12)};
    pathTiles(b, cols, out);
    got.clear();
    for (const Tile16 t : out) got.push_back(plan(t));
    CHECK(got == std::vector<std::pair<int, int>>{{5, 5},
                                                  {5, 6},
                                                  {4, 6},
                                                  {4, 7},
                                                  {3, 7},
                                                  {3, 8},
                                                  {2, 8},
                                                  {2, 9},
                                                  {2, 10},
                                                  {2, 11},
                                                  {2, 12}});
}

TEST_CASE("life: the day plan draws as worldgen's day reports do") {
    // worldgen.rng.hash64("rome:senate:1") and ("athens:wedding:7"), modulo 1000.
    CHECK(worldgenHash("rome:senate:1") == 7489259229695019214ULL);
    CHECK(worldgenHash("athens:wedding:7") % 1000 == 276);
    CHECK(inHours(18.5f, 5.0f, 23.0f));
    CHECK(inHours(18.5f, 5.0f, 4.0f));
    CHECK_FALSE(inHours(18.5f, 5.0f, 12.0f));
    CHECK_FALSE(inHours(6.0f, 6.0f, 6.0f)); // citylife: [a, a) holds no hour
    LifeClock c = LifeClock::at(9, 1.5, 0);
    CHECK(c.hour() == doctest::Approx(1.5));
    CHECK(c.seconds() == doctest::Approx(9 * 720 - 4.5 * 30));
    c = LifeClock::at(2, 6.0, 0);
    CHECK(c.seconds() == doctest::Approx(2 * 720));
    // The same plan twice; large events of a region never overlap.
    CityLife city(lifeWorld(), 1);
    std::vector<std::tuple<int, double, double>> p1;
    std::vector<std::tuple<int, double, double>> p2;
    for (const char* region : {"rome", "athens", "parsa"}) {
        const int r = lifeWorld().data.findRegion(region);
        const LifeRegion& reg = lifeWorld().data.regions[static_cast<std::size_t>(r)];
        for (int day = 0; day < 12; ++day) {
            city.dayPlan(r, day, reg.season, p1);
            city.dayPlan(r, day, reg.season, p2);
            CHECK(p1 == p2);
            double end = -1e18;
            for (const auto& [e, start, stop] : p1) {
                CHECK(stop > start);
                if (reg.events[static_cast<std::size_t>(e)].size != EventSize::Large) continue;
                CHECK(start >= end - 1e-9);
                end = stop;
            }
        }
    }
    // Rome's Parilia: festival on day 1 of the cycle (spring, season day 2), its procession
    // planned.
    const int rome = lifeWorld().data.findRegion("rome");
    city.dayPlan(rome, 1, seasonOf("rome"), p1);
    const LifeRegion& reg = lifeWorld().data.regions[static_cast<std::size_t>(rome)];
    CHECK(std::ranges::any_of(p1, [&](const auto& e) {
        return reg.events[static_cast<std::size_t>(std::get<0>(e))].id == "parilia_procession";
    }));
    city.dayPlan(rome, 2, seasonOf("rome"), p1);
    CHECK_FALSE(std::ranges::any_of(p1, [&](const auto& e) {
        return reg.events[static_cast<std::size_t>(std::get<0>(e))].id == "parilia_procession";
    }));
}

TEST_CASE("life: the calendar's months: festivals, populations, events and season turns") {
    const LifeData& d = lifeWorld().data;
    REQUIRE(d.months.size() == 12);
    CHECK(d.months.front() == "mar");
    CHECK(d.monthOf(13) == 1);
    CityLife city(lifeWorld(), 1);
    // Month-only festivals are on in their months and no other day (they once ran every day).
    const auto festivalDays = [&](const char* region, const char* festival) {
        const int r = d.findRegion(region);
        const int f = d.regions[static_cast<std::size_t>(r)].findFestival(festival);
        REQUIRE(f >= 0);
        std::vector<int> days;
        for (int day = 0; day < 24; ++day)
            if (city.festivalOn(r, f, day, -1)) days.push_back(day);
        return days;
    };
    CHECK(festivalDays("babylon", "king_in_babylon") == std::vector<int>{9, 10, 11, 21, 22, 23});
    CHECK(festivalDays("athens", "olive_harvest") == std::vector<int>{8, 9, 10, 20, 21, 22});
    CHECK(festivalDays("ostia", "grain_fleet") == std::vector<int>{2, 14});
    // Every event is planned only in its months, and a season's turn once a year, at its first
    // dawn (L-101: it once came every morning of the season).
    std::vector<std::tuple<int, double, double>> plan;
    for (std::size_t r = 0; r < d.regions.size(); ++r) {
        const LifeRegion& reg = d.regions[r];
        std::vector<int> planned(reg.events.size(), 0);
        for (int day = 0; day < 12; ++day) {
            city.dayPlan(static_cast<int>(r), day, -1, plan);
            for (const auto& entry : plan) {
                const int e = std::get<0>(entry);
                const Event& ev = reg.events[static_cast<std::size_t>(e)];
                CAPTURE(reg.id);
                CAPTURE(ev.id);
                CHECK(monthIn(ev.when.months, d.monthOf(day)));
                if (ev.seasonTurn && ev.when.months == 0) CHECK(day % d.seasonDays == 0);
                planned[static_cast<std::size_t>(e)] |= 1 << day; // days, not occurrences
            }
        }
        for (std::size_t e = 0; e < reg.events.size(); ++e)
            if (reg.events[e].seasonTurn) {
                CAPTURE(reg.id);
                CAPTURE(reg.events[e].id);
                CHECK(std::popcount(static_cast<unsigned>(planned[e])) <= 1);
            }
    }
    // The planned events of the whole world at once leave room for those no plan holds (rain,
    // arrivals, chains, `after`): once the world's 24 slots were full by mid-morning.
    std::vector<std::pair<double, int>> edges;
    for (std::size_t r = 0; r < d.regions.size(); ++r)
        for (int day = 0; day < 12; ++day) {
            city.dayPlan(static_cast<int>(r), day, -1, plan);
            for (const auto& [e, start, stop] : plan) {
                edges.emplace_back(start, 1);
                edges.emplace_back(stop, -1);
            }
        }
    std::ranges::sort(edges);
    int at = 0;
    int most = 0;
    for (const auto& [t, k] : edges) most = std::max(most, at += k);
    MESSAGE("planned events running at once, at most " << most);
    CHECK(most + 16 <= tuning::life::kMaxRunningEvents);
    // Populations follow their months: the whole world's crowd at 10:00 is the month's, as
    // the data means it: about 5 000 to 5 400 with the towns and the land between alive
    // (world-alive.md); before months were read, every month's variant at once was far more.
    const TileRect all = lifeWorld().map().bounds();
    for (int day = 0; day < 12; ++day) {
        const float n = city.expectedFor(all, LifeClock::at(day, 10.0, -1));
        CAPTURE(day);
        CHECK(n > 4600.0f);
        CHECK(n < 6000.0f);
    }
}

TEST_CASE("life: carts are what is drawn as one, not a name holding \"cart\" (L-109)") {
    const LifeData& d = lifeWorld().data;
    const auto cart = [&](std::string_view id) {
        const int k = d.findKind(id);
        REQUIRE(k >= 0);
        return d.kinds[static_cast<std::size_t>(k)].cart;
    };
    CHECK_FALSE(cart("rome.carter"));
    CHECK(cart("rome.cart"));
    CHECK(cart("athens.sledge"));
}

TEST_CASE("life: next hops follow shortest ways, and every planned walk is legal") {
    LifeWorld& w = lifeWorld();
    const WorldMap& m = w.map();
    for (const char* region : {"rome", "athens", "parsa"}) {
        CAPTURE(region);
        RegionPaths& p = w.paths[static_cast<std::size_t>(
            w.pathsOf[static_cast<std::size_t>(w.data.findRegion(region))])];
        std::mt19937 rng(11); // NOLINT(bugprone-random-generator-seed): the same pairs every run
        std::uniform_int_distribution<int> rx(p.regionRect().x0, p.regionRect().x1 - 1);
        std::uniform_int_distribution<int> ry(p.regionRect().y0, p.regionRect().y1 - 1);
        std::array<Tile16, tuning::life::kMoveReach + 2> desc{};
        std::array<world::WalkStep, 4> steps{};
        int walked = 0;
        for (int k = 0; k < 4000 && walked < 150; ++k) {
            const TilePos a{rx(rng), ry(rng)};
            const TilePos b{rx(rng), ry(rng)};
            if (!m.walkable(a) || !m.walkable(b) || !p.reachable(a) || !p.reachable(b)) continue;
            Route r;
            int builds = 1000;
            if (p.plan(a, b, r, desc, builds) != PlanResult::Ok) continue;
            TilePos cur = a;
            TilePos nx;
            int n = 0;
            while (p.next(r, cur, desc, nx) && n < 20000) {
                // Each step a walker could make.
                const int ns = m.walkNeighbours(cur, steps);
                const bool legal =
                    std::any_of(steps.begin(), steps.begin() + ns,
                                [&](const world::WalkStep& s) { return s.to == nx; });
                CAPTURE(cur.x);
                CAPTURE(cur.y);
                CAPTURE(nx.x);
                CAPTURE(nx.y);
                REQUIRE(legal);
                cur = nx;
                ++n;
            }
            CHECK(cur == b);
            ++walked;
        }
        CHECK(walked >= 100);
    }
    // Next hops against Dijkstra: the hop chain from any node ends at the destination after
    // exactly the shortest distance.
    RegionPaths& rome = w.paths[static_cast<std::size_t>(
        w.pathsOf[static_cast<std::size_t>(w.data.findRegion("rome"))])];
    std::vector<int> dist;
    for (int dest = 0; dest < rome.nodeCount(); dest += 37) {
        rome.distances(dest, dist);
        for (int from = 0; from < rome.nodeCount(); from += 5) {
            if (dist[static_cast<std::size_t>(from)] == INT_MAX) continue;
            const TilePos a = rome.nodeAt(from);
            const TilePos b = rome.nodeAt(dest);
            if (!m.walkable(a) || !m.walkable(b)) continue;
            Route r;
            std::array<Tile16, tuning::life::kMoveReach + 2> desc{};
            int builds = 1000;
            if (rome.plan(a, b, r, desc, builds) != PlanResult::Ok || r.leg == Leg::Line) continue;
            const int len = rome.length(r, a, desc);
            CHECK(len >= 0);
            // Walking between two node tiles never takes longer than the graph's way (blocked
            // edges aside, which only lengthen it).
            CHECK(len >= dist[static_cast<std::size_t>(from)] - 1);
        }
    }
}

TEST_CASE("life: chains keep their rules over a simulated fortnight, and the cycle is exact") {
    LifeWorld& w = lifeWorld();
    Chains chains(w.data, w.map(), w.paths, w.pathsOf);
    REQUIRE(chains.size() >= 30);
    for (std::size_t i = 0; i < chains.size(); ++i) {
        CAPTURE(chains.run(i).chain().id);
        CHECK(chains.run(i).ok());
    }
    // Tick by tick for 14 days, every counter 0..3 always.
    Chains a(w.data, w.map(), w.paths, w.pathsOf);
    for (long t = 0; t < 14 * 720; t += 60) {
        a.advanceTo(static_cast<double>(t), 0, 0, [](int, int) { return true; });
        for (std::size_t i = 0; i < a.size(); ++i)
            for (const ChainRun::Counter& c : a.run(i).counters()) {
                CHECK(c.count >= 0);
                CHECK(c.count <= tuning::life::kChainCap);
            }
    }
    // A jump to day 40 equals walking there tick by tick from day 30's 06:00, each day in its
    // own season and month (the month-limited and month-paced chains among them).
    const auto seasonOf = [&](long t) {
        return static_cast<int>((t / 720 / w.data.seasonDays) %
                                static_cast<long>(w.data.seasons.size()));
    };
    const auto monthOf = [&](long t) { return w.data.monthOf(static_cast<int>(t / 720)); };
    const auto none = [](int, int) { return false; };
    Chains jump(w.data, w.map(), w.paths, w.pathsOf);
    jump.advanceTo(40 * 720 + 300, seasonOf(40 * 720), monthOf(40 * 720), none);
    Chains walk(w.data, w.map(), w.paths, w.pathsOf);
    walk.advanceTo(30 * 720, seasonOf(30 * 720), monthOf(30 * 720), none);
    for (long t = 30 * 720; t <= 40 * 720 + 300; t += 1)
        walk.advanceTo(static_cast<double>(t), seasonOf(t - 1), monthOf(t - 1), none); // tick t-1
    for (std::size_t i = 0; i < jump.size(); ++i) {
        CAPTURE(jump.run(i).chain().id);
        if (jump.run(i).chain().event >= 0) continue;
        CHECK(jump.run(i).snapshot() == walk.run(i).snapshot());
    }
}

TEST_CASE("life: chains agree with tools/worldgen's lifesim, stage by stage") {
    // The reference is written at test time by tests/world_tools/life_chains.py (the life_chains
    // test); run alone, without it, the case has nothing to compare with.
    const char* path = std::getenv("LC_LIFE_CHAINS"); // NOLINT(concurrency-mt-unsafe)
    if (path == nullptr) {
        MESSAGE("skipped: LC_LIFE_CHAINS names no reference (ctest -R life_chains makes one)");
        return;
    }
    const auto text = readTextFile(path);
    REQUIRE(text.has_value());
    const auto py = nlohmann::json::parse(*text);
    const auto cpp = nlohmann::json::parse(chainReport(lifeWorld()));
    CHECK(py.size() == cpp.size());
    for (auto it = py.begin(); it != py.end(); ++it) {
        CAPTURE(it.key());
        REQUIRE(cpp.contains(it.key()));
        const auto& a = it.value();
        const auto& b = cpp[it.key()];
        if (a["stages"].empty()) {
            CHECK(!b["errors"].empty()); // worldgen could not place it either
            continue;
        }
        CHECK(a["stages"] == b["stages"]);
        CHECK(a["per_day"] == b["per_day"]);
        for (std::size_t s = 0; s < a["travel"].size(); ++s)
            CHECK(a["travel"][s].get<double>() ==
                  doctest::Approx(b["travel"][s].get<double>()).epsilon(1e-6));
        for (auto c = b["count"].begin(); c != b["count"].end(); ++c) {
            CAPTURE(c.key());
            const int expect = a["count"].contains(c.key()) ? a["count"][c.key()].get<int>() : 0;
            CHECK(c.value().get<int>() == expect);
        }
    }
}

TEST_CASE("city: the three centres live their day as the data says") {
    CityLife city(lifeWorld(), 7);
    struct Case {
        const char* focus;
        const char* region;
        int day;
    };
    for (const Case cs :
         {Case{"forum", "rome", 9}, Case{"forum", "rome", 1}, Case{"agora", "athens", 5},
          Case{"agora", "athens", 4}, Case{"terrace", "parsa", 2}, Case{"terrace", "parsa", 3}}) {
        for (const double hour : {5.5, 10.0, 15.5, 19.5, 1.5}) {
            const std::string where = std::string(cs.focus) + " day " + std::to_string(cs.day);
            CAPTURE(where);
            CAPTURE(cs.day);
            CAPTURE(hour);
            city.setFocus(centreOf(cs.focus));
            LifeClock clock = LifeClock::at(cs.day, hour, seasonOf(cs.region));
            city.settle(clock);
            // Districts: the live count against the data's population for the hour.
            float expected = 0;
            int live = 0;
            for (const DistrictCount& d : city.districtCounts()) {
                expected += d.expected;
                live += d.live + d.inside;
                CAPTURE(lifeWorld()
                            .data.regions[static_cast<std::size_t>(d.region)]
                            .districts[static_cast<std::size_t>(d.district)]
                            .id);
                CAPTURE(d.expected);
                // Fractional people are rounded by hash, one draw per population entry and
                // chunk: the spread is about a square root.
                const float want = d.expected * city.stats().scale; // the cap's share
                CHECK(std::abs(static_cast<float>(d.live + d.inside) - want) <=
                      3.0f + 1.5f * std::sqrt(want));
            }
            // Over the cap (the Panathenaia's Agora) populations are scaled down in proportion.
            expected *= city.stats().scale;
            CHECK(std::abs(static_cast<float>(live) - expected) <=
                  4.0f + 2.0f * std::sqrt(expected));
            checkGround(city);
            checkSlots(city);
            // A minute of life later: still where people can stand, still within capacity.
            step(city, clock, 3600);
            checkGround(city);
            checkSlots(city);
        }
    }
}

TEST_CASE("city: busy mornings, quiet nights") {
    CityLife city(lifeWorld(), 3);
    for (const auto& [focus, region, day] :
         {std::tuple{"forum", "rome", 9}, std::tuple{"agora", "athens", 5},
          std::tuple{"terrace", "parsa", 2}}) {
        CAPTURE(focus);
        city.setFocus(centreOf(focus));
        city.settle(LifeClock::at(day, 10.0, seasonOf(region)));
        const int morning = city.stats().bySource[0];
        city.settle(LifeClock::at(day, 1.5, seasonOf(region)));
        const int night = city.stats().bySource[0];
        CHECK(morning > 150);
        CHECK(night * 4 < morning);
    }
}

TEST_CASE("city: the same clock gives the same people however often the area comes and goes") {
    CityLife city(lifeWorld(), 5);
    const LifeClock clock = LifeClock::at(9, 10.5, seasonOf("rome"));
    city.setFocus(centreOf("forum"));
    city.settle(clock);
    const Snapshot first = snapshot(city);
    CHECK(first.rows.size() > 300);
    for (int k = 0; k < 3; ++k) {
        city.setFocus(centreOf("agora")); // far away: Rome folds back to its abstract state
        LifeClock away = clock;
        away.t += 3.0 / tuning::kDayLengthSeconds; // a moment later (the 2 s linger has passed)
        city.settle(away);
        city.settle(away);
        city.setFocus(centreOf("forum"));
        city.settle(clock);
        const Snapshot again = snapshot(city);
        if (!(again == first)) {
            std::map<std::uint64_t, std::tuple<std::uint64_t, int, int, int, int>> a;
            for (const auto& r : first.rows) a[std::get<0>(r)] = r;
            int shown = 0;
            int missing = 0;
            for (const auto& r : again.rows) {
                const auto it = a.find(std::get<0>(r));
                if (it == a.end()) {
                    ++missing;
                    continue;
                }
                if (it->second != r && shown++ < 8)
                    MESSAGE("differs: key "
                            << std::get<0>(r) << " source " << sourceOf(city, std::get<0>(r))
                            << " pos " << std::get<1>(it->second) << "," << std::get<2>(it->second)
                            << " -> " << std::get<1>(r) << "," << std::get<2>(r) << " step "
                            << std::get<3>(it->second) << " -> " << std::get<3>(r));
            }
            MESSAGE("rows " << first.rows.size() << " vs " << again.rows.size() << ", new keys "
                            << missing);
        }
        CHECK(again == first);
    }
}

TEST_CASE("city: travellers keep their hours, wait at rest stops, leave at their offsets") {
    // The corner's walkers to Rome's western gate (latium_italy.2): two instances, 05:00 to
    // 19:30, offsets 0.988 and 0.441, the climate's road row (all of spring).
    const LifeData& d = lifeWorld().data;
    const auto t = static_cast<std::size_t>(
        std::ranges::find(d.tokens, worldgenHash("latium_italy.2"), &Token::seed) -
        d.tokens.begin());
    REQUIRE(t < d.tokens.size());
    const Token& tk = d.tokens[t];
    CHECK(tk.hours);
    CHECK(tk.rest.size() == 2);
    REQUIRE(tk.offsets.size() == 2);
    REQUIRE(tk.share.size() == 12);
    CityLife city(lifeWorld(), 1);
    city.setFocus(centreOf("forum"));
    city.settle(LifeClock::at(1, 2.0, -1));
    CHECK_FALSE(city.tokenPhase(t, 0).underway); // 02:00: waiting
    CHECK_FALSE(city.tokenPhase(t, 1).underway);
    const double night = city.tokenPhase(t, 0).phase;
    city.settle(LifeClock::at(1, 4.5, -1));
    CHECK(city.tokenPhase(t, 0).phase == doctest::Approx(night)); // its clock stood still
    city.settle(LifeClock::at(1, 10.0, -1));
    CHECK(city.tokenPhase(t, 0).underway);
    CHECK(city.tokenPhase(t, 1).underway);
    // Spaced by their offsets, not evenly.
    const double a = city.tokenPhase(t, 0).phase;
    const double b = city.tokenPhase(t, 1).phase;
    const double gap = a - b;
    CHECK(gap != doctest::Approx(0));
    // Bad token data is named: an unknown rest stop or climate row would be a problem line.
    for (const std::string& p : d.problems) CHECK(p.find("token") == std::string::npos);
}

TEST_CASE("city: nobody walks in place, in the cities, towns, roads and seas, at four hours") {
    // Each place at four hours: after a settling minute, 20 s watched; every second each live
    // actor's window says whether it was drawn walking without getting anywhere (marching) or
    // walked to and fro. The causes are tallied by source, state and step for the report.
    // Before the body drove the drawing: 5 054 actor-seconds marching over these 32 views.
    const char* places[] = {"forum",
                            "agora",
                            "terrace",
                            "district:ostia/forum",
                            "district:delphi/sanctuary",
                            "district:latium_italy/road",
                            "district:greece/road",
                            "district:tyrrhenian/sea",
                            "district:saronic/sea",
                            "district:corinth/town"};
    long marching = 0;
    long oscillating = 0;
    long stuckLong = 0;
    std::map<std::string, long> causes;
    for (const char* place : places)
        for (const double hour : {7.0, 10.5, 15.0, 21.0}) {
            CityLife city(lifeWorld(), 11);
            city.setFocus(centreOf(place), 24, 16);
            LifeClock clock = LifeClock::at(1, hour, -1);
            city.settle(clock);
            step(city, clock, 60 * 60);
            long here = 0;
            for (int k = 0; k < 20; ++k) {
                step(city, clock, 60);
                city.forEachInfo([&](const CityLife::Info& in) {
                    if ((in.body & body_flag::kMarching) == 0 &&
                        (in.body & body_flag::kOscillating) == 0)
                        return;
                    ++here;
                    marching += (in.body & body_flag::kMarching) != 0 ? 1 : 0;
                    oscillating += (in.body & body_flag::kOscillating) != 0 ? 1 : 0;
                    const LifeData& d = lifeWorld().data;
                    const std::string verb =
                        in.step >= 0 ? std::to_string(static_cast<int>(
                                           d.steps[static_cast<std::size_t>(in.step)].verb))
                                     : "-";
                    ++causes["source " + std::to_string(static_cast<int>(in.source)) + " state " +
                             std::to_string(static_cast<int>(in.state)) + " verb " + verb +
                             ((in.body & body_flag::kStuck) != 0 ? " stuck" : "") +
                             ((in.body & body_flag::kOscillating) != 0 ? " to-and-fro" : "")];
                });
                city.forEachInfo([&](const CityLife::Info& in) {
                    if (in.stall > tuning::life::kStallGiveUp + tuning::life::kProgressWindow)
                        ++stuckLong;
                });
            }
            MESSAGE(std::string(place)
                    << " " << hour << "h: " << here << " actor-seconds walking in place, live "
                    << city.liveCount() << ", stuck now " << city.stats().stuck);
        }
    for (const auto& [c, n] : causes) MESSAGE(c << ": " << n);
    MESSAGE("marching " << marching << ", to and fro (two windows) " << oscillating
                        << ", going nowhere past the watchdog " << stuckLong);
    // Nobody is drawn walking on the spot; nobody goes nowhere (stuck, to and fro) past the
    // watchdog's bound, after which the step is given up or the actor leaves.
    CHECK(marching == 0);
    CHECK(stuckLong == 0);
}

TEST_CASE("city: the same seed and script give byte-identical dumps") {
    std::string dumps[2];
    for (std::string& out : dumps) {
        CityLife city(lifeWorld(), 42);
        LifeClock clock = LifeClock::at(1, 8.75, seasonOf("rome"));
        city.setFocus(centreOf("forum"));
        city.settle(clock);
        step(city, clock, 1200);
        city.setFocus({centreOf("forum").x + 20, centreOf("forum").y + 10});
        step(city, clock, 1200);
        out = lifeDump(city, "determinism");
    }
    CHECK(dumps[0].size() > 10000);
    CHECK(dumps[0] == dumps[1]);
}

TEST_CASE("city: the clock gliding to a pin is no jump; chains never run backwards (L-002)") {
    CityLife city(lifeWorld(), 5);
    const int rome = lifeWorld().data.findRegion("rome");
    const LifeRegion& reg = lifeWorld().data.regions[static_cast<std::size_t>(rome)];
    const auto showerRuns = [&] {
        return std::ranges::any_of(city.running(), [&](const RunningEvent& e) {
            return e.region == rome && e.event >= 0 &&
                   reg.events[static_cast<std::size_t>(e.event)].id == "spring_shower";
        });
    };
    city.setFocus(centreOf("forum"));
    LifeClock clock = LifeClock::at(0, 10.0, -1); // March: Rome's spring shower may come
    clock.epoch = 0;
    city.settle(clock);
    step(city, clock, 10);
    clock.rain = true; // the shower's weather event starts (it is in no day plan)
    step(city, clock, 2);
    REQUIRE(showerRuns());
    // The pin's glide: 3.75 life seconds a step, forward then back, with no jump counted.
    const double glide = 0.5 * tuning::kStepSeconds / tuning::kPinEaseSeconds;
    for (int k = 0; k < 16; ++k) {
        clock.t += glide;
        city.update(clock, static_cast<float>(tuning::kStepSeconds));
        CHECK(showerRuns());
    }
    const long tick = city.chains().tick();
    for (int k = 0; k < 16; ++k) {
        clock.t -= glide;
        city.update(clock, static_cast<float>(tuning::kStepSeconds));
        CHECK(city.chains().tick() >= tick);
    }
    CHECK(showerRuns());
    // A jump the caller counts still rebuilds from the plan, dropping what no plan holds.
    clock.epoch = 1;
    city.update(clock, static_cast<float>(tuning::kStepSeconds));
    CHECK_FALSE(showerRuns());
}

TEST_CASE("city: an event runs to completion and the day goes on around it") {
    CityLife city(lifeWorld(), 9);
    // Rome, a Senate day (week day 1): the senators walk from the Velia to the Curia.
    const int rome = lifeWorld().data.findRegion("rome");
    const LifeRegion& reg = lifeWorld().data.regions[static_cast<std::size_t>(rome)];
    std::vector<std::tuple<int, double, double>> plan;
    city.dayPlan(rome, 9, seasonOf("rome"), plan);
    const auto senate = std::ranges::find_if(plan, [&](const auto& e) {
        return reg.events[static_cast<std::size_t>(std::get<0>(e))].id == "senate";
    });
    REQUIRE(senate != plan.end());
    const double start = std::get<1>(*senate);
    const double end = std::get<2>(*senate);
    city.setFocus(centreOf("forum"));
    LifeClock clock = LifeClock::at(9, 6.0, seasonOf("rome"));
    clock.t += (start - clock.seconds() - 5.0) / tuning::kDayLengthSeconds;
    city.settle(clock);
    bool seen = false;
    int castSeen = 0;
    while (clock.seconds() < end + 10.0) {
        step(city, clock, 60);
        const bool running = std::ranges::any_of(city.running(), [&](const RunningEvent& e) {
            return e.region == rome && e.event >= 0 &&
                   reg.events[static_cast<std::size_t>(e.event)].id == "senate";
        });
        if (running) {
            seen = true;
            castSeen =
                std::max(castSeen, city.stats().bySource[static_cast<std::size_t>(Source::Cast)]);
        }
    }
    CHECK(seen);
    CHECK(castSeen >= 10); // the senators, lictors and clients formed up
    CHECK_FALSE(std::ranges::any_of(city.running(), [&](const RunningEvent& e) {
        return e.region == rome && e.event >= 0 &&
               reg.events[static_cast<std::size_t>(e.event)].id == "senate";
    }));
    // The district populations hold through it and after.
    for (const DistrictCount& d : city.districtCounts())
        CHECK(std::abs(static_cast<float>(d.live + d.inside) - d.expected) <=
              3.0f + 1.5f * std::sqrt(d.expected));
    checkGround(city);
}

TEST_CASE("city: arriving spreads the materialisation across steps") {
    CityLife city(lifeWorld(), 2);
    LifeClock clock = LifeClock::at(9, 10.0, seasonOf("rome"));
    city.setFocus(centreOf("agora"));
    city.settle(clock);
    city.setFocus(centreOf("forum"));
    int steps = 0;
    int most = 0;
    do {
        step(city, clock, 1);
        most = std::max(most, city.stats().spawnedThisStep);
        ++steps;
    } while (city.stats().queued > 0 && steps < 600);
    CHECK(most <= tuning::life::kSpawnsPerStep);
    CHECK(steps > 5);
    CHECK(steps < 600);
    CHECK(city.stats().live > 300);
}

TEST_CASE("city: the cap scales populations down in proportion") {
    CityLife city(lifeWorld(), 4);
    city.setFocus(centreOf("forum"));
    const LifeClock clock = LifeClock::at(9, 10.0, seasonOf("rome"));
    city.settle(clock);
    const int full = city.stats().bySource[0];
    std::map<int, int> byRole;
    city.forEachInfo([&](const CityLife::Info& in) {
        if (in.source == Source::Population) ++byRole[in.role];
    });
    city.setLiveCap(full / 2);
    city.settle(clock);
    city.settle(clock);
    CHECK(city.stats().live <= full / 2);
    CHECK(city.stats().scale < 0.8f);
    std::map<int, int> scaled;
    city.forEachInfo([&](const CityLife::Info& in) {
        if (in.source == Source::Population) ++scaled[in.role];
    });
    // The biggest roles keep about their share.
    for (const auto& [role, n] : byRole)
        if (n >= 30)
            CHECK(std::abs(static_cast<float>(scaled[role]) / static_cast<float>(n) -
                           city.stats().scale) < 0.25f);
}

TEST_CASE("city: never more live than the cap, panning fast and jumping between cities") {
    // QA5 Q5-E-20: a step's spawns were not counted against the cap while they happened.
    CityLife city(lifeWorld(), 6);
    LifeClock clock = LifeClock::at(1, 8.0, seasonOf("rome"));
    const TilePos forum = centreOf("forum");
    int worst = 0;
    for (int k = 0; k < 1500; ++k) {
        const char* far[] = {"agora", "terrace", "forum"};
        TilePos at = k % 500 == 499 ? centreOf(far[(k / 500) % 3])
                                    : TilePos{forum.x + (k % 500) / 4 - 60, forum.y};
        city.setFocus(at);
        step(city, clock, 1);
        int live = 0;
        city.forEachInfo([&](const CityLife::Info&) { ++live; });
        worst = std::max(worst, live);
    }
    MESSAGE("most live " << worst);
    CHECK(worst <= tuning::life::kLiveCap);
}

TEST_CASE("city: ships and barges on their lanes, carts on the road, live where the camera is") {
    CityLife city(lifeWorld(), 6);
    LifeClock clock = LifeClock::at(9, 9.0, seasonOf("rome"));
    // Rome's Tiber lane: three barges and a fishing boat; somewhere along it there is one.
    int seen = 0;
    for (const char* d :
         {"district:rome/river", "district:rome/emporium", "district:ostia/portus"}) {
        city.setFocus(centreOf(d), 40, 40);
        for (int k = 0; k < 10 && seen == 0; ++k) {
            step(city, clock, 600);
            seen = city.stats().bySource[static_cast<std::size_t>(Source::Token)];
        }
        if (seen > 0) break;
    }
    CHECK(city.stats().tokens > 40);
    CHECK(seen > 0);
}

TEST_CASE("city: gather writes what is drawn, interpolated, without allocating") {
    CityLife city(lifeWorld(), 8);
    LifeClock clock = LifeClock::at(9, 10.0, seasonOf("rome"));
    city.setFocus(centreOf("forum"));
    city.settle(clock);
    step(city, clock, 30);
    std::vector<DrawActor> buf(64);
    const std::size_t n = city.gather(city.view(), 0.5f, buf);
    CHECK(n == buf.size()); // the view holds more than 64: the span bounds it
    std::vector<DrawActor> all(4096);
    const std::size_t m = city.gather(city.activeRect(), 0.25f, all);
    CHECK(m > 200);
    const auto& kinds = lifeWorld().data.kinds;
    for (std::size_t i = 0; i < m; ++i) {
        const DrawActor& d = all[i];
        CHECK(city.alive(d.handle));
        CHECK(d.kind < kinds.size());
        CHECK(d.alpha > 0.0f);
        CHECK(city.activeRect().contains(
            TilePos{static_cast<int>(d.pos.x), static_cast<int>(d.pos.y)}));
    }
}

TEST_CASE("city: people walk smoothly: even pace, eased turns, diagonals, strides by distance") {
    CityLife city(lifeWorld(), 12);
    LifeClock clock = LifeClock::at(9, 10.0, seasonOf("rome"));
    city.setFocus(centreOf("forum"));
    city.settle(clock);
    step(city, clock, 120);
    std::vector<DrawActor> before(4096);
    std::vector<DrawActor> after(4096);
    int moving = 0;
    int jumps = 0;
    int flips = 0;
    int diagonal = 0;
    int slides = 0;
    std::set<float> rates;
    for (int k = 0; k < 600; ++k) {
        const std::size_t n0 = city.gather(city.activeRect(), 1.0f, before);
        step(city, clock, 1);
        const std::size_t n1 = city.gather(city.activeRect(), 1.0f, after);
        std::map<std::uint32_t, const DrawActor*> was;
        for (std::size_t i = 0; i < n0; ++i)
            was[(std::uint32_t(before[i].handle.index) << 16) | before[i].handle.gen] = &before[i];
        for (std::size_t i = 0; i < n1; ++i) {
            const DrawActor& d = after[i];
            const auto it = was.find((std::uint32_t(d.handle.index) << 16) | d.handle.gen);
            if (it == was.end()) continue;
            const DrawActor& p = *it->second;
            const float dx = d.pos.x - p.pos.x;
            const float dy = d.pos.y - p.pos.y;
            const float dist = std::sqrt(dx * dx + dy * dy);
            if (dist > 0.5f) continue; // a puppet placed by its formula after an event turned
            // The stride is the distance walked: frames chosen by it never slide.
            if (std::abs((d.stride - p.stride) - dist) > 1e-3f) ++slides;
            if (d.speed < 0.3f || p.speed < 0.3f) continue;
            ++moving;
            // An even pace: never more than a step's worth at a brisk walk.
            if (dist > 1.6f * static_cast<float>(tuning::kStepSeconds)) {
                if (jumps < 12)
                    MESSAGE("jump " << lifeWorld().data.kinds[d.kind].id << " "
                                    << dist / tuning::kStepSeconds << " tiles/s at " << d.pos.x
                                    << "," << d.pos.y << " speed " << d.speed);
                ++jumps;
            }
            float turn = d.heading - p.heading;
            while (turn > 3.1415927f) turn -= 6.2831853f;
            while (turn < -3.1415927f) turn += 6.2831853f;
            if (std::abs(turn) > 0.8f) ++flips; // no about-turn or right angle in one step
            const float s2 = std::abs(std::sin(2.0f * d.heading));
            if (s2 > 0.5f) ++diagonal;
        }
    }
    MESSAGE("moving samples " << moving << ", jumps " << jumps << ", flips " << flips
                              << ", diagonal " << diagonal << ", slides " << slides);
    REQUIRE(moving > 20000);
    CHECK(jumps == 0);
    CHECK(flips * 1000 < moving);  // under one in a thousand steps
    CHECK(diagonal * 10 > moving); // people take diagonals, not only grid lines
    CHECK(slides == 0);
    // Crowds out of step: every actor its own animation phase and pace.
    std::set<int> phases;
    const std::size_t n = city.gather(city.activeRect(), 0.0f, after);
    for (std::size_t i = 0; i < n; ++i)
        phases.insert(static_cast<int>(after[i].animTime * 10.0f) % 40);
    CHECK(phases.size() > 30);
}

TEST_CASE("city: the land between the cities is alive: travellers, couriers, boats") {
    CityLife city(lifeWorld(), 21);
    // The Royal Road in Anatolia: couriers ride station to station every two game hours, the
    // road's travellers and grooms are about.
    // A relay station of the base graph in Anatolia (found by name: the builders renumber them).
    std::optional<TilePos> station;
    const world::RoadGraph& roads = realWorld().roads;
    const int anatolia = realWorld().file.findRegion("anatolia");
    for (const world::RoadNode& n : roads.nodes())
        if (n.id.find("royal_road_station") != std::string::npos && n.region == anatolia) {
            station = n.at;
            break;
        }
    REQUIRE(station.has_value());
    city.setFocus(*station, 24, 24);
    LifeClock clock = LifeClock::at(2, 8.0, 0);
    city.settle(clock);
    int people = 0;
    int casts = 0;
    for (int k = 0; k < 16; ++k) {
        step(city, clock, 600);
        people =
            std::max(people, city.stats().bySource[static_cast<std::size_t>(Source::Population)]);
        casts = std::max(casts, city.stats().bySource[static_cast<std::size_t>(Source::Cast)]);
    }
    CHECK(people > 0);
    CHECK(casts > 0); // the courier and the groom came by
    checkGround(city);
    // Fishing boats and ships on the lanes: some are where the camera looks when it follows the
    // coast of Latium and the Saronic gulf.
    int boats = 0;
    for (const char* d :
         {"district:ostia/portus", "district:athens/piraeus", "district:corinth/kenchreai"}) {
        const auto f = parseFocus(lifeWorld(), d);
        if (!f) continue;
        city.setFocus(*f, 40, 40);
        city.settle(clock);
        for (int k = 0; k < 10 && boats == 0; ++k) {
            step(city, clock, 600);
            boats = city.stats().bySource[static_cast<std::size_t>(Source::Token)];
        }
    }
    CHECK(boats > 0);
}
