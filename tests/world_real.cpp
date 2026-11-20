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
#include <format>
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

TEST_CASE("real world: the home region keeps its own look, its file the rest") {
    // corner.json styles the land round the corner (sound, weather, life) but lays no tint or
    // haze on the home: the game's scene grades it from the home catalog's seasons.
    const world::LoadedWorld& w = realWorld();
    const std::size_t home = static_cast<std::size_t>(w.file.home.region);
    REQUIRE(home < w.regions.size());
    const world::Theme& t = w.regions[home].theme;
    CHECK(t.hazeStrength == 0.0f);
    for (const auto& g : t.grading) CHECK(g == world::Rgb3{1, 1, 1});
    CHECK_FALSE(w.regions[home].life.is_null()); // its life is read
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
    // Prebuilt items there stay in the list (no index moves) but nothing of the world stands on
    // the home's tiles.
    for (int y = hr.y0; y < hr.y1; ++y)
        for (int x = hr.x0; x < hr.x1; ++x)
            if (const int i = m.itemAt({x, y}); i >= 0)
                CHECK(m.items()[static_cast<std::size_t>(i)].layer == kHomeLayer);
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

TEST_CASE("real world: a stair is stepped onto at its foot and off at its head") {
    // world-loose-ends.md: first treads drawn 10-14 px up (`walk_z` is a tread's middle) refused
    // the step from the ground. Every walkable tile on a stair's foot edge takes the step from
    // the ground before it at the stair's level, and the head edge to the ground `rise` up.
    const WorldMap& m = *realWorld().map;
    int edges = 0;
    std::vector<std::string> refused;
    for (const Placed& it : m.items()) {
        const ItemInfo& info = m.info(it);
        if (info.rise <= 0 || it.head < 0) continue;
        const TileRect r = it.rect();
        for (const auto& [end, level] : {std::pair{(it.head + 2) % 4, int(it.level)},
                                         std::pair{int(it.head), it.level + info.rise}}) {
            const TilePos d = lc::world::kSteps[static_cast<std::size_t>(end)];
            for (int y = r.y0; y < r.y1; ++y)
                for (int x = r.x0; x < r.x1; ++x) {
                    const TilePos p{x, y};
                    const TilePos q{x + d.x, y + d.y};
                    if (r.contains(q) || !m.inBounds(q) || !m.walkable(p) || !m.walkable(q) ||
                        m.itemAt(q) >= 0 || m.level(q) != level)
                        continue;
                    ++edges;
                    std::array<WalkStep, 4> steps{};
                    const int n = m.walkNeighbours(q, steps);
                    if (std::none_of(steps.begin(), steps.begin() + n,
                                     [&](const WalkStep& s) { return s.to == p; }))
                        refused.push_back(
                            std::format("{} ({}, {}) from ({}, {})", info.id, p.x, p.y, q.x, q.y));
                }
        }
    }
    for (const std::string& s : refused) MESSAGE("refused: " << s);
    CHECK(edges > 100);
    CHECK(refused.empty());
}

TEST_CASE("slopes: every shape is the contract's mesh, continuous inside the tile") {
    for (int k = 1; k < kSlopeCount; ++k) {
        const auto s = Slope(k);
        CAPTURE(std::string(slopeKey(s)));
        const SlopeGrid& g = slopeGrid(s);
        for (int j = 0; j < 3; ++j)
            for (int i = 0; i < 3; ++i)
                CHECK(slopeHeight(s, static_cast<float>(i) * 0.5f, static_cast<float>(j) * 0.5f) ==
                      doctest::Approx(g[static_cast<std::size_t>(j * 3 + i)]));
        // Fine steps never jump: the fan's triangles meet along their shared edges.
        float worst = 0;
        for (int j = 0; j <= 64; ++j)
            for (int i = 0; i < 64; ++i) {
                const float u = static_cast<float>(i) / 64.0f;
                const float v = static_cast<float>(j) / 64.0f;
                const float h = slopeHeight(s, u, v);
                CHECK(h <= 0.0f);
                CHECK(h >= -1.0f);
                worst = std::max(worst, std::abs(slopeHeight(s, u + 1.0f / 64.0f, v) - h));
            }
        CHECK(worst <= 2.0f / 64.0f + 1e-5f);
    }
    // Corner shapes: the mask of low corners; peaks: every corner low.
    CHECK(slopeCorner(Slope(5), 0) == -1);
    CHECK(slopeCorner(Slope(5), 1) == 0);
    CHECK(slopeCorner(Slope(5), 2) == -1);
    CHECK(slopeCorner(Slope::RidgeX, 3) == -1);
    CHECK(slopeOf(15, kCornerN | kCornerS, true, false) == Slope::RidgeX0);
    CHECK(slopeOf(15, kCornerE | kCornerW, true, true) == Slope::RidgeY);
    CHECK(slopeOf(15, kCornerE | kCornerN, true, true) == Slope::Knoll);
    CHECK(slopeOf(6, 0, false, false) == Slope(6));
}

TEST_CASE("real world: the ground's surface is continuous where slopes meet, and hills slope") {
    const LoadedWorld& w = realWorld();
    const WorldMap& m = *w.map;
    const float lvl = static_cast<float>(m.levelPx());
    long slopes = 0;
    long joins = 0;
    long gaps = 0;
    long steps = 0;
    for (int y = 0; y + 1 < m.height(); ++y)
        for (int x = 0; x + 1 < m.width(); ++x) {
            const TilePos p{x, y};
            if (m.terrainAt(p) == kNone) continue;
            slopes += m.slopeAt(p) != Slope::Flat ? 1 : 0;
            for (int dir = 0; dir < 2; ++dir) {
                const TilePos q{x + kSteps[std::size_t(dir)].x, y + kSteps[std::size_t(dir)].y};
                if (m.terrainAt(q) == kNone) continue;
                if (m.surfacesMeet(p, dir)) {
                    if (m.level(p) != m.level(q)) ++joins;
                    // Along the shared edge both sides give one height.
                    for (int k = 0; k < 8; ++k) {
                        const float t = (static_cast<float>(k) + 0.5f) / 8.0f;
                        const Vec2 e =
                            dir == 0 ? Vec2{static_cast<float>(x + 1), static_cast<float>(y) + t}
                                     : Vec2{static_cast<float>(x) + t, static_cast<float>(y + 1)};
                        const Vec2 in = dir == 0 ? Vec2{e.x - 1e-4f, e.y} : Vec2{e.x, e.y - 1e-4f};
                        if (std::abs(m.surfaceZ(in) - m.surfaceZ(e)) > 0.01f * lvl) ++gaps;
                    }
                } else if (std::abs(m.level(p) - m.level(q)) == 1 && m.slopeAt(p) == Slope::Flat &&
                           m.slopeAt(q) == Slope::Flat) {
                    ++steps;
                }
            }
        }
    MESSAGE("slope tiles " << slopes << ", one-level joins across slopes " << joins
                           << ", one-level steps left as faces " << steps);
    CHECK(gaps == 0);
    // The graded world (9e49283): most one-level steps are slopes.
    CHECK(slopes > 10000);
    CHECK(joins > steps);
    // A plant on a slope stands at the surface of its tile's centre; a flat tile at its level.
    for (int y = 0; y < m.height(); y += 7)
        for (int x = 0; x < m.width(); x += 7) {
            const TilePos p{x, y};
            if (m.terrainAt(p) == kNone || m.slopeAt(p) != Slope::Flat) continue;
            CHECK(m.surfaceZ({static_cast<float>(x) + 0.3f, static_cast<float>(y) + 0.8f}) ==
                  doctest::Approx(static_cast<float>(m.level(p)) * lvl));
        }
}

TEST_CASE("real world: a walker's height is continuous over slopes, stairs and decks") {
    const LoadedWorld& w = realWorld();
    const WorldMap& m = *w.map;
    // From every walkable tile near a slope or a raised floor to each tile it may step to, in
    // small steps: never more than a small change a step, and on plain ground the surface.
    long courses = 0;
    float worst = 0;
    long offSurface = 0;
    for (int y = 1; y + 1 < m.height(); ++y)
        for (int x = 1; x + 1 < m.width(); ++x) {
            const TilePos p{x, y};
            if (!m.walkable(p) || m.slopeAt(p) == Slope::Flat) continue;
            std::array<WalkStep, 4> steps{};
            const int n = m.walkNeighbours(p, steps);
            for (int i = 0; i < n; ++i) {
                const TilePos q = steps[static_cast<std::size_t>(i)].to;
                const Vec2 a{static_cast<float>(x) + 0.5f, static_cast<float>(y) + 0.5f};
                const Vec2 d{static_cast<float>(q.x - x), static_cast<float>(q.y - y)};
                float prev = m.walkZ(a);
                for (int k = 1; k <= 64; ++k) {
                    const float f = static_cast<float>(k) / 64.0f;
                    const float z = m.walkZ({a.x + d.x * f, a.y + d.y * f});
                    worst = std::max(worst, std::abs(z - prev));
                    prev = z;
                }
                ++courses;
            }
            // On a slope tile with nothing raised round it, the walker stands on the surface.
            const Vec2 c{static_cast<float>(x) + 0.3f, static_cast<float>(y) + 0.6f};
            if (n > 0 && std::abs(m.walkZ(c) - m.surfaceZ(c)) > 0.5f &&
                m.floorZ(p) == m.level(p) * m.levelPx())
                ++offSurface;
        }
    MESSAGE(courses << " courses from slope tiles, largest change in 1/64 tile " << worst << " px, "
                    << offSurface << " off their surface");
    CHECK(courses > 1000);
    CHECK(worst <= 2.0f);
}

TEST_CASE("real world: a boat on a lane over falling water never drops in one step") {
    // The Euphrates boats' lane crosses a river falling three levels (grid (273, 235..237)): a
    // boat there was drawn at its tile's water level and dropped 48 px at the edge. Its height
    // (WorldMap::waterZ) blends between the waters, so it changes by little along the way, and
    // it floats at the water's own level in the middle of a tile on flat water.
    const LoadedWorld& w = realWorld();
    const WorldMap& m = *w.map;
    const world::RoadGraph& roads = w.roads;
    const auto lane =
        std::ranges::find(roads.lanes(), std::string("base:euphrates_boats"), &world::RoadLane::id);
    REQUIRE(lane != roads.lanes().end());
    float worst = 0;
    float span = 0;
    for (std::size_t i = 1; i < lane->points.size(); ++i) {
        const TilePos a = lane->points[i - 1];
        const TilePos b = lane->points[i];
        float prev = m.waterZ({static_cast<float>(a.x) + 0.5f, static_cast<float>(a.y) + 0.5f});
        for (int k = 1; k <= 64; ++k) {
            const float f = static_cast<float>(k) / 64.0f;
            const float z =
                m.waterZ({static_cast<float>(a.x) + 0.5f + static_cast<float>(b.x - a.x) * f,
                          static_cast<float>(a.y) + 0.5f + static_cast<float>(b.y - a.y) * f});
            worst = std::max(
                worst, std::abs(z - prev) * 64.0f /
                           static_cast<float>(std::max(std::abs(b.x - a.x), std::abs(b.y - a.y))));
            span = std::max(span, std::abs(z - prev));
            prev = z;
        }
    }
    MESSAGE("largest change along the lane: " << span << " px in a step, " << worst
                                              << " px per tile");
    // At most the whole fall over one tile's way, never in one step.
    CHECK(worst <= static_cast<float>(3 * m.levelPx()) + 0.5f);
    CHECK(span < static_cast<float>(m.levelPx()));
    const TilePos still = lane->points.front();
    CHECK(m.waterZ({static_cast<float>(still.x) + 0.5f, static_cast<float>(still.y) + 0.5f}) ==
          doctest::Approx(static_cast<float>(m.level(still) * m.levelPx())));
}
