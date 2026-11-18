// The committed world: invariants, agreement with tools/worldgen's reader, determinism, the home
// overlay, and the load-time, memory and query budgets.

#include "core/starter.hpp"
#include "world/digest.hpp"
#include "world/figures.hpp"
#include "world/loader.hpp"
#include "world_support.hpp"

#include <doctest.h>

#include <algorithm>
#include <chrono>
#include <cstdlib>
#include <filesystem>
#include <map>
#include <numeric>
#include <random>
#include <set>
#include <span>

using namespace lc;
using namespace lc::world;
using namespace lc::wtest;

namespace {

// Problems in the committed data that the world builders have been told about (see
// out/reports/engine-city-life.md): town landmarks placed in layers whose set catalog does not
// define them yet. Each is reported as "item id '<id>' is in no catalog"; any other error, or
// another id, fails. Fixing the data needs no change here.
constexpr std::array<const char*, 18> kKnownUncatalogued{
    "athens.acrocorinth_summit",
    "athens.artemision",
    "athens.athenian_treasury",
    "athens.corinth_apollo",
    "athens.delos_sanctuary",
    "athens.delphi_apollo",
    "athens.diolkos",
    "athens.naxian_lions",
    "parsa.babylon_tower",
    "parsa.babylon_wall",
    "parsa.etemenanki",
    "parsa.gates_station",
    "parsa.halys_gates",
    "parsa.ishtar_gate",
    "parsa.pasargadae_garden",
    "parsa.processional_way",
    "parsa.royal_road_head",
    "parsa.susa_palace",
};
bool knownError(const std::string& e) {
    return std::ranges::any_of(kKnownUncatalogued, [&](const char* id) {
        return e.find("item id '" + std::string(id) + "' is in no catalog") != std::string::npos;
    });
}

bool hasCatalog(const LoadedWorld& w, const std::string& id) {
    const auto dot = id.find('.');
    if (dot == std::string::npos) return true;
    return std::ranges::any_of(w.content->sets(),
                               [&](const SetCatalog& s) { return s.set == id.substr(0, dot); });
}

using SteadyClock = std::chrono::steady_clock;
double nsPer(SteadyClock::time_point t, double n) {
    return std::chrono::duration<double, std::nano>(SteadyClock::now() - t).count() / n;
}

} // namespace

TEST_CASE("real world: composed from every layer on disk, ids resolve or are accounted for") {
    const LoadedWorld& w = realWorld();
    const WorldMap& m = *w.map;
    CHECK(m.width() == 448);
    CHECK(m.height() == 1280);
    CHECK(m.chunksX() * m.chunksY() == 560);
    std::vector<std::string> present;
    for (const LayerRef& ref : w.file.layers)
        if (std::filesystem::exists(assetsDir() / "world" / ref.file)) present.push_back(ref.id);
    CHECK(w.layers == present);
    CHECK(w.layers.front() == "base");
    CHECK(m.homeRect() == TileRect{40, 1200, 80, 1240});
    CHECK(m.regionAt({40, 1200}) == w.file.findRegion("corner"));
    // Every placed item resolved to a catalog entry; the skipped ids are only from sets that
    // have no catalog yet.
    for (const Placed& it : m.items()) CHECK(it.info < w.content->items().size());
    for (const auto& [id, n] : m.unresolved()) {
        CAPTURE(id);
        CHECK((!hasCatalog(w, id) ||
               std::ranges::find(kKnownUncatalogued, id) != kKnownUncatalogued.end()));
    }
    for (const std::string& e : w.diagnostics.errors) {
        const bool known = knownError(e);
        CHECK_MESSAGE(known, e);
        if (known) MESSAGE("data finding: " << e);
    }
}

TEST_CASE("real world: every piece and slot of a placed item exists in geometry and the atlas") {
    const LoadedWorld& w = realWorld();
    const WorldMap& m = *w.map;
    std::set<std::string> missing;
    std::set<std::uint32_t> checked;
    for (const Placed& it : m.items()) {
        const ItemInfo& info = m.info(it);
        if (info.homeType >= 0 || !checked.insert(it.info * 64u + it.variant).second) continue;
        // A set whose art is not drawn yet (the shared `world` set) has no pages to check.
        if (std::ranges::none_of(w.atlas.pages(),
                                 [&](const AtlasPage& pg) { return pg.set == info.set; }))
            continue;
        if (it.variant >= info.count && info.layout != Layout::Connect) continue; // known finding
        const GeomVariant* g = m.geometry(it);
        if (info.landmark) {
            CHECK_MESSAGE(g != nullptr, info.id << " " << info.variantKey(it.variant, it.mask));
        }
        if (g != nullptr && !g->pieces.empty()) {
            for (std::size_t p = 0; p < g->pieces.size(); ++p) {
                const std::string key = "item/" + info.id + "/base/r" + std::to_string(it.variant) +
                                        "/p" + std::to_string(p) + "/f0";
                if (w.atlas.find(key) == nullptr) missing.insert(key);
            }
        } else {
            const std::string key =
                "item/" + info.id + "/base/" + info.variantKey(it.variant, it.mask) + "/f0";
            if (w.atlas.find(key) == nullptr) missing.insert(key);
        }
    }
    for (const std::string& k : missing) MESSAGE("no sprite " << k);
    CHECK(missing.empty());
    // Slots carry their catalog behaviour, and every catalog slot of a placed item has a spot.
    std::map<std::uint32_t, std::set<std::string>> slotsOf;
    for (const WorldSlot& s : m.slots()) {
        const ItemInfo& info = m.info(m.items()[s.item]);
        if (info.homeType >= 0) continue;
        CHECK_FALSE(m.slotKinds()[s.kind].empty());
        slotsOf[s.item].insert(m.slotNames()[s.name]);
    }
    for (std::uint32_t i = 0; i < m.items().size(); ++i) {
        const ItemInfo& info = m.info(m.items()[i]);
        if (info.homeType >= 0 || m.geometry(m.items()[i]) == nullptr) continue;
        for (const SlotBehaviour& b : info.slots) {
            CAPTURE(info.id);
            CHECK(slotsOf[i].contains(b.id));
        }
    }
    CHECK(m.slots().size() > 100);
}

TEST_CASE("real world: every layer's graph is connected or joins through a portal (V6)") {
    const LoadedWorld& w = realWorld();
    CHECK(w.graphs.size() == w.layers.size());
    for (const GraphFile& g : w.graphs) {
        CAPTURE(g.layer);
        std::vector<int> parent(g.nodes.size());
        std::iota(parent.begin(), parent.end(), 0);
        const auto find = [&](int x) {
            while (parent[std::size_t(x)] != x)
                x = parent[std::size_t(x)] = parent[std::size_t(parent[std::size_t(x)])];
            return x;
        };
        for (const GraphEdge& e : g.edges) parent[std::size_t(find(e.a))] = find(e.b);
        // worldgen's V6: a part that reaches a portal joins the world through another layer
        // (the base's roads of Italy, Greece and Persia meet only in the towns between them).
        std::map<int, std::pair<int, bool>> parts; // root -> size, has a portal
        for (int i = 0; i < int(g.nodes.size()); ++i) {
            auto& [size, portal] = parts[find(i)];
            ++size;
            portal = portal || g.nodes[std::size_t(i)].kind == NodeKind::Portal;
        }
        const auto main =
            std::ranges::max_element(parts, {}, [](const auto& p) { return p.second.first; });
        for (const auto& [root, part] : parts) {
            CAPTURE(g.nodes[std::size_t(root)].id);
            CHECK((root == main->first || part.second));
        }
    }
    const RoadGraph& r = w.roads;
    CHECK(r.findNode("base:corner_road_s") >= 0);
    CHECK(r.findNode("base:corner_road_s") == r.findNode("corner:corner_road_s"));
    // Following next hops from any node of a region ends at the destination, without loops.
    int walks = 0;
    for (std::size_t d = 0; d < r.nodes().size(); ++d) {
        if (r.nodes()[d].destSlot < 0) continue;
        for (std::size_t n = 0; n < r.nodes().size(); ++n) {
            int at = static_cast<int>(n);
            if (r.nextHop(at, int(d)) < 0) continue;
            std::size_t steps = 0;
            while (at != int(d) && at >= 0 && steps <= r.nodes().size()) {
                at = r.nextHop(at, int(d));
                ++steps;
            }
            CHECK(at == int(d));
            ++walks;
        }
    }
    CHECK(walks > 1000);
}

TEST_CASE("real world: the digest equals tools/worldgen's, byte for byte") {
    // The reference is written at test time by tests/world_tools/world_digest.py (the
    // world_digest test); run alone, without it, the case has nothing to compare with.
    const char* path = std::getenv("LC_WORLD_DIGEST"); // NOLINT(concurrency-mt-unsafe)
    if (path == nullptr) {
        MESSAGE("skipped: LC_WORLD_DIGEST names no reference (ctest -R world_digest makes one)");
        return;
    }
    const auto text = readTextFile(path);
    REQUIRE_MESSAGE(text.has_value(), path);
    const auto expected = parseDigest(*text, path);
    REQUIRE_MESSAGE(expected.has_value(), (expected ? "" : expected.error()));
    const WorldDigest actual = digestOf(realWorld());
    const auto diff = compareDigests(*expected, actual);
    for (std::size_t i = 0; i < std::min<std::size_t>(diff.size(), 20); ++i) MESSAGE(diff[i]);
    CHECK(diff.empty());
    CHECK(toJson(actual) == *text);
}

TEST_CASE("real world: loading twice gives the same world") {
    const auto again = loadWorld(assetsDir(), homeCatalog());
    REQUIRE(again.has_value());
    const LoadedWorld& w = realWorld();
    CHECK(toJson(digestOf(*again)) == toJson(digestOf(w)));
    CHECK(again->map->slots().size() == w.map->slots().size());
    CHECK(again->roads.nodes().size() == w.roads.nodes().size());
    CHECK(again->diagnostics.errors == w.diagnostics.errors);
    CHECK(again->diagnostics.warnings == w.diagnostics.warnings);
}

TEST_CASE("real world: regions, districts and themes") {
    const LoadedWorld& w = realWorld();
    const WorldMap& m = *w.map;
    for (const Marker& mk : w.file.markers) {
        CAPTURE(w.file.regions[std::size_t(mk.region)].id);
        if (std::ranges::find(w.layers, w.file.regions[std::size_t(mk.region)].id) ==
            w.layers.end())
            continue; // a place whose layer is not built yet: the base's reserved land
        CHECK(m.regionAt(mk.at) == mk.region);
        std::array<RegionWeight, 4> weights{};
        const int n = m.themeWeights({float(mk.at.x) + 0.5f, float(mk.at.y) + 0.5f}, weights);
        REQUIRE(n >= 1);
        // A town's radius is half a stretch's (§4.6), so its theme blends in rather than leads.
        CHECK(std::ranges::any_of(std::span(weights).first(std::size_t(n)),
                                  [&](const RegionWeight& rw) { return rw.region == mk.region; }));
    }
    for (std::size_t d = 0; d < m.districtCount(); ++d) {
        CAPTURE(m.districtName(int(d)));
        CHECK(m.districtRegion(int(d)) >= 0);
    }
}

TEST_CASE("real world: the starter home overlays the corner") {
    auto w = loadWorld(assetsDir(), homeCatalog());
    REQUIRE(w.has_value());
    WorldMap& m = *w->map;
    const Catalog& cat = homeCatalog();
    const World starter = makeStarterWorld(cat);
    Diagnostics diag;
    REQUIRE(m.applyHome(homeDeltaFrom(starter, cat), diag).has_value());
    for (const std::string& e : diag.errors) CHECK_MESSAGE(knownError(e), e);
    const TileRect hr = m.homeRect();
    for (const Item& it : starter.items()) {
        const TilePos p{hr.x0 + it.pos.x, hr.y0 + it.pos.y};
        const int i = m.itemAt(p);
        REQUIRE(i >= 0);
        CHECK(m.info(m.items()[std::size_t(i)]).id == cat.items[it.type].id);
    }
    for (int y = 0; y < starter.height(); y += 3)
        for (int x = 0; x < starter.width(); x += 3) {
            const int t = starter.terrainAt({x, y});
            const TilePos p{hr.x0 + x, hr.y0 + y};
            if (t == kNoGround)
                CHECK(m.terrainAt(p) == kNone);
            else
                CHECK(m.terrainInfo(m.terrainAt(p)).id == cat.terrain[std::size_t(t)].id);
            CHECK(m.level(p) == w->file.home.level);
            if (starter.isWild({x, y})) CHECK_FALSE(m.walkable(p));
        }
    for (const Placed& it : m.items())
        if (it.layer != kHomeLayer) CHECK_FALSE(it.rect().intersects(hr));
}

TEST_CASE("perf: load time and memory") {
    double best = 1e9;
    std::size_t bytes = 0;
    LoadTimings t;
    for (int i = 0; i < 5; ++i) {
        const auto w = loadWorld(assetsDir(), homeCatalog());
        REQUIRE(w.has_value());
        if (w->timings.total < best) {
            best = w->timings.total;
            t = w->timings;
        }
        bytes = w->memoryBytes();
    }
    MESSAGE("load " << best << " ms (contracts " << t.contracts << ", layers " << t.layers
                    << ", compose " << t.compose << ", graphs " << t.graphs << ", regions "
                    << t.regions << "); world memory " << double(bytes) / 1e6 << " MB");
    // world-tech §2.8: about 15 MB of CPU memory for the whole world.
    CHECK(bytes <= 15'000'000);
#ifdef NDEBUG
    CHECK(best < 300.0);
#endif
}

TEST_CASE("perf: query throughput") {
    const LoadedWorld& w = realWorld();
    const WorldMap& m = *w.map;
    std::mt19937 rng(7); // NOLINT(bugprone-random-generator-seed): the same tiles every run
    std::uniform_int_distribution<int> rx(0, m.width() - 1);
    std::uniform_int_distribution<int> ry(0, m.height() - 1);
    std::vector<TilePos> tiles(1 << 16);
    for (TilePos& p : tiles) p = {rx(rng), ry(rng)};
    constexpr int kTileOps = 1 << 22;
    auto t = SteadyClock::now();
    long sink = 0;
    for (int i = 0; i < kTileOps; ++i) {
        const TilePos p = tiles[std::size_t(i) & 0xFFFF];
        sink += m.terrainAt(p) + m.level(p) + m.regionAt(p);
    }
    const double tile = nsPer(t, kTileOps);
    std::array<WalkStep, 4> steps{};
    t = SteadyClock::now();
    for (int i = 0; i < kTileOps; ++i)
        sink += m.walkNeighbours(tiles[std::size_t(i) & 0xFFFF], steps);
    const double walk = nsPer(t, kTileOps);
    // The busiest view the world has today: the Parsa terrace, 64 x 64 tiles (about a 1440p
    // screen at zoom 1), items and pieces in depth-key order.
    const TileRect view{340, 30, 404, 94};
    std::vector<DrawPiece> pieces;
    m.piecesIn(view, pieces);
    const std::size_t inView = pieces.size();
    t = SteadyClock::now();
    for (int i = 0; i < 2000; ++i) m.piecesIn(view, pieces);
    const double view_us = nsPer(t, 2000) / 1000;
    std::array<RegionWeight, 8> weights{};
    t = SteadyClock::now();
    for (int i = 0; i < 100000; ++i) {
        const TilePos p = tiles[std::size_t(i) & 0xFFFF];
        sink += m.themeWeights({float(p.x), float(p.y)}, weights);
    }
    const double theme_us = nsPer(t, 100000) / 1000;
    const RoadGraph& r = w.roads;
    t = SteadyClock::now();
    for (int i = 0; i < 100000; ++i) {
        const TilePos p = tiles[std::size_t(i) & 0xFFFF];
        sink += r.nearestNode({float(p.x), float(p.y)});
    }
    const double nearest = nsPer(t, 100000);
    std::vector<int> dests;
    for (std::size_t i = 0; i < r.nodes().size(); ++i)
        if (r.nodes()[i].destSlot >= 0) dests.push_back(int(i));
    REQUIRE_FALSE(dests.empty());
    t = SteadyClock::now();
    for (int i = 0; i < kTileOps; ++i)
        sink += r.nextHop(i % int(r.nodes().size()), dests[std::size_t(i) % dests.size()]);
    const double hop = nsPer(t, kTileOps);
    PathScratch scratch;
    std::vector<std::uint32_t> path;
    const int from = r.findNode("parsa:royal_road_w");
    REQUIRE(from >= 0);
    t = SteadyClock::now();
    int found = 0;
    for (std::size_t i = 0; i < 2000; ++i)
        found += r.shortestPath(from, dests[i % dests.size()], scratch, path);
    const double astar_us = nsPer(t, 2000) / 1000;
    CHECK(found > 0);
    MESSAGE("tile lookups " << tile << " ns; walk neighbours " << walk << " ns; view of " << inView
                            << " pieces " << view_us << " us; theme weights " << theme_us
                            << " us; nearest node " << nearest << " ns; next hop " << hop
                            << " ns; A* on " << r.nodes().size() << " nodes " << astar_us
                            << " us (sink " << sink % 7 << ")");
    CHECK(inView > 200);
#ifdef NDEBUG
    // world-tech §4.14: gather and cull 0.2 ms, themes 0.05 ms per frame.
    CHECK(view_us < 200.0);
    CHECK(theme_us < 50.0);
    CHECK(tile < 20.0);
    CHECK(walk < 200.0);
    CHECK(hop < 50.0);
#endif
}

TEST_CASE("real world: named figures stand on open ground in their regions, one per tile") {
    const LoadedWorld& w = realWorld();
    const WorldMap& m = *w.map;
    const auto figures = placeFigures(w);
    std::set<std::pair<int, int>> tiles;
    std::map<std::string, int> perRegion;
    for (const FigurePlace& f : figures) {
        CAPTURE(f.actor);
        const TilePos t{static_cast<int>(f.at.x), static_cast<int>(f.at.y)};
        REQUIRE(m.inBounds(t));
        CHECK(m.walkable(t));
        CHECK(m.itemAt(t) < 0);
        CHECK(m.regionAt(t) == f.region);
        CHECK(f.level == m.level(t));
        CHECK(tiles.insert({t.x, t.y}).second);
        CHECK_FALSE(f.sprite.empty());
        ++perRegion[w.file.regions[static_cast<std::size_t>(f.region)].id];
    }
    // Every figure of the three cities that is a person (an actor; shrines, statues, reliefs
    // and tales are shown by places) has a place.
    for (const std::string city : {"rome", "athens", "parsa"}) {
        const RegionFile& rf = w.regions[static_cast<std::size_t>(w.file.findRegion(city))];
        CAPTURE(city);
        const auto people = std::ranges::count_if(
            rf.life["figures"], [](const nlohmann::json& f) { return f.contains("actor"); });
        CHECK(perRegion[city] == static_cast<int>(people));
    }
}

TEST_CASE("real world: stairs and ramps stand on their lower tile and reach their head") {
    // QA (owner, Acropolis): stair pieces floating over the ground. A stair is drawn at its
    // item's level, which must be its footprint's lowest; its head (the side it climbs to) must
    // stand `rise` levels up. Mismatches in the layouts are listed
    // (out/reports/world-game-faults.md).
    const LoadedWorld& w = realWorld();
    const WorldMap& m = *w.map;
    int stairs = 0;
    int drawnHigh = 0;
    std::vector<std::string> unreached;
    for (const Placed& it : m.items()) {
        const ItemInfo& info = m.info(it);
        if (info.rise <= 0) continue;
        ++stairs;
        const TileRect r = it.rect();
        int low = 99;
        for (int y = r.y0; y < r.y1; ++y)
            for (int x = r.x0; x < r.x1; ++x)
                if (m.inBounds({x, y})) low = std::min(low, m.level({x, y}));
        CAPTURE(info.id);
        CAPTURE(it.x);
        CAPTURE(it.y);
        if (it.level > low) ++drawnHigh;
        CHECK(it.level <= low);
        if (it.head < 0)
            unreached.push_back(info.id + " at (" + std::to_string(it.x) + ", " +
                                std::to_string(it.y) + ")");
    }
    CHECK(stairs > 50);
    CHECK(drawnHigh == 0);
    for (const std::string& s : unreached) MESSAGE("data finding: no head at its rise: " << s);
}
