// worldinfo: loads the world and prints a summary, validates it, or dumps a region, a tile or the
// digest. A debugging aid for world builders and QA; built with the project, not installed.

#include "core/catalog.hpp"
#include "world/digest.hpp"
#include "world/loader.hpp"

#include <charconv>
#include <cstdio>
#include <filesystem>
#include <map>
#include <string>
#include <string_view>
#include <sys/resource.h>
#include <vector>

using namespace lc;
using namespace lc::world;

namespace {

constexpr const char* kUsage =
    "usage: worldinfo [--assets DIR] [summary | validate | digest | region ID | tile X Y |\n"
    "                 slopes X Y R]\n"
    "  summary   sizes, layers, items, graphs, timings and memory (default)\n"
    "  validate  every diagnostic; exits 1 when the data has errors\n"
    "  digest    the digest tests/world_tools/world_digest.py also writes\n"
    "  region    a region's tiles, districts, items and graph nodes\n"
    "  tile      everything at one grid tile\n"
    "  slopes    levels and slope shapes round a grid tile, R tiles each way (rows along x)\n";

const char* kindName(RegionKind k) {
    switch (k) {
    case RegionKind::Home: return "home";
    case RegionKind::City: return "city";
    case RegionKind::Town: return "town";
    case RegionKind::Stretch: return "stretch";
    case RegionKind::Seam: return "seam";
    }
    return "?";
}

void summary(const LoadedWorld& w) {
    const WorldMap& m = *w.map;
    std::printf("grid %d x %d (%d x %d chunks), home at (%d, %d) %d x %d level %d\n", m.width(),
                m.height(), m.chunksX(), m.chunksY(), w.file.home.rect.x0, w.file.home.rect.y0,
                w.file.home.rect.x1 - w.file.home.rect.x0,
                w.file.home.rect.y1 - w.file.home.rect.y0, w.file.home.level);
    std::printf("layers composed (%zu of %zu):", w.layers.size(), w.file.layers.size());
    for (const auto& l : w.layers) std::printf(" %s", l.c_str());
    std::printf("\nterrain ids %zu, districts %zu, regions %zu (%zu with a region file)\n",
                m.terrainCount(), m.districtCount(), w.file.regions.size(),
                static_cast<std::size_t>(std::ranges::count_if(
                    w.regions, [](const RegionFile& r) { return !r.id.empty(); })));
    std::map<std::string, int> bySet;
    for (const Placed& it : m.items()) ++bySet[m.info(it).set];
    std::printf("items %zu:", m.items().size());
    for (const auto& [set, n] : bySet) std::printf(" %s %d", set.c_str(), n);
    int skipped = 0;
    for (const auto& [id, n] : m.unresolved()) skipped += n;
    std::printf("; %d skipped (%zu unknown ids)\n", skipped, m.unresolved().size());
    std::printf("slots %zu, graph nodes %zu, edges %zu, lanes %zu, components %d\n",
                m.slots().size(), w.roads.nodes().size(), w.roads.edges().size(),
                w.roads.lanes().size(), w.roads.componentCount());
    std::printf("atlas pages %zu with %zu keys\n", w.atlas.pages().size(), w.atlas.size());
    std::printf("load %.1f ms (contracts %.1f, layers %.1f, compose %.1f, graphs %.1f, regions "
                "%.1f)\n",
                w.timings.total, w.timings.contracts, w.timings.layers, w.timings.compose,
                w.timings.graphs, w.timings.regions);
    rusage usage{};
    getrusage(RUSAGE_SELF, &usage);
    std::printf("memory %.2f MB (map %.2f MB); this process peaked at %.1f MB resident\n",
                static_cast<double>(w.memoryBytes()) / 1e6,
                static_cast<double>(m.memoryBytes()) / 1e6,
                static_cast<double>(usage.ru_maxrss) / 1024.0);
    std::printf("diagnostics: %zu error(s), %zu warning(s) (worldinfo validate lists them)\n",
                w.diagnostics.errors.size(), w.diagnostics.warnings.size());
}

void region(const LoadedWorld& w, const std::string& id) {
    const WorldMap& m = *w.map;
    const int r = w.file.findRegion(id);
    if (r < 0) {
        std::printf("no region '%s'\n", id.c_str());
        return;
    }
    const RegionRef& ref = w.file.regions[static_cast<std::size_t>(r)];
    std::printf("%s: %s, set %s, time %s, file %s%s\n", ref.id.c_str(), kindName(ref.kind),
                ref.set.c_str(), ref.time.c_str(), ref.life.c_str(),
                w.regions[static_cast<std::size_t>(r)].id.empty() ? " (missing)" : "");
    std::map<int, int> districts;
    TileRect box{m.width(), m.height(), 0, 0};
    for (int y = 0; y < m.height(); ++y)
        for (int x = 0; x < m.width(); ++x)
            if (m.regionAt({x, y}) == r) {
                ++districts[m.districtAt({x, y})];
                box = {std::min(box.x0, x), std::min(box.y0, y), std::max(box.x1, x + 1),
                       std::max(box.y1, y + 1)};
            }
    if (districts.empty()) {
        std::printf("  no tiles\n");
        return;
    }
    std::printf("  tiles in grid (%d, %d)..(%d, %d)\n", box.x0, box.y0, box.x1 - 1, box.y1 - 1);
    for (const auto& [d, n] : districts)
        std::printf("  district %-28s %7d tiles\n", m.districtName(d).c_str(), n);
    std::map<std::string, int> items;
    m.forEachItemIn(box, [&](std::uint32_t, const Placed& it) {
        if (m.regionAt({it.x, it.y}) == r) ++items[m.info(it).id];
    });
    for (const auto& [i, n] : items) std::printf("  item %-30s %5d\n", i.c_str(), n);
    int nodes = 0;
    int dests = 0;
    for (const RoadNode& n : w.roads.nodes())
        if (n.region == r) {
            ++nodes;
            dests += n.kind == NodeKind::Dest;
        }
    std::printf("  graph nodes %d (%d destinations)\n", nodes, dests);
}

void tile(const LoadedWorld& w, TilePos p) {
    const WorldMap& m = *w.map;
    if (!m.inBounds(p)) {
        std::printf("(%d, %d) is outside the grid\n", p.x, p.y);
        return;
    }
    const int t = m.terrainAt(p);
    const std::uint8_t lb = m.levelByte(p);
    std::printf("grid (%d, %d): terrain %s%s, level %d, aux %d%s\n", p.x, p.y,
                t == kNone ? "(no ground)" : m.terrainInfo(t).id.c_str(),
                t != kNone && !m.terrainInfo(t).known ? " (unknown)" : "", levelOf(lb), auxOf(lb),
                impassableBit(lb) ? ", impassable" : "");
    const int d = m.districtAt(p);
    const int r = m.regionAt(p);
    std::printf("  district %s, region %s\n", d == kNone ? "-" : m.districtName(d).c_str(),
                r < 0 ? "-" : w.file.regions[static_cast<std::size_t>(r)].id.c_str());
    std::printf("  walkable %s, floor %d px\n", m.walkable(p) ? "yes" : "no", m.floorZ(p));
    if (const Slope s = m.slopeAt(p); s != Slope::Flat)
        std::printf("  slope %s (corners N %d, E %d, S %d, W %d)\n",
                    std::string(slopeKey(s)).c_str(), m.cornerLevel(p, 0), m.cornerLevel(p, 1),
                    m.cornerLevel(p, 2), m.cornerLevel(p, 3));
    std::array<WalkStep, 4> steps{};
    const int n = m.walkNeighbours(p, steps);
    for (int i = 0; i < n; ++i)
        std::printf("  step to (%d, %d) dz %d\n", steps[std::size_t(i)].to.x,
                    steps[std::size_t(i)].to.y, steps[std::size_t(i)].dz);
    m.forEachItemIn({p.x, p.y, p.x + 1, p.y + 1}, [&](std::uint32_t i, const Placed& it) {
        std::printf("  item #%u %s r%d at (%d, %d) %dx%d layer %s%s\n", i, m.info(it).id.c_str(),
                    it.variant, it.x, it.y, it.w, it.h,
                    it.layer == kHomeLayer ? "home" : m.layers()[it.layer].c_str(),
                    m.itemAt(p) == static_cast<int>(i) ? " (occupies)" : "");
    });
    m.forEachSlotNear({float(p.x) + 0.5f, float(p.y) + 0.5f}, 0.75f, -1, [&](const WorldSlot& s) {
        std::printf("  slot %s (%s) of item #%u at (%.2f, %.2f)\n", m.slotNames()[s.name].c_str(),
                    m.slotKinds()[s.kind].c_str(), s.item, s.at.x, s.at.y);
    });
    const int node = w.roads.nearestNode({float(p.x) + 0.5f, float(p.y) + 0.5f});
    if (node >= 0) {
        const RoadNode& rn = w.roads.nodes()[static_cast<std::size_t>(node)];
        std::printf("  nearest graph node %s (%s) at (%d, %d)\n", rn.id.c_str(),
                    nodeKindName(rn.kind), rn.at.x, rn.at.y);
    }
}

// Levels round p (hex digit) with the slope's key beside each sloped tile, and `~` for water.
void slopes(const LoadedWorld& w, TilePos p, int r) {
    const WorldMap& m = *w.map;
    std::printf("      ");
    for (int x = p.x - r; x <= p.x + r; ++x) std::printf("%-9d", x);
    std::printf("\n");
    for (int y = p.y - r; y <= p.y + r; ++y) {
        std::printf("%5d ", y);
        for (int x = p.x - r; x <= p.x + r; ++x) {
            const TilePos q{x, y};
            if (!m.inBounds(q) || m.terrainAt(q) == kNone) {
                std::printf("%-9s", ".");
                continue;
            }
            const bool water = m.terrainInfo(m.terrainAt(q)).water;
            const std::string key(slopeKey(m.slopeAt(q)));
            std::printf("%X%c%-7s", m.level(q), water ? '~' : (m.itemAt(q) >= 0 ? '*' : ' '),
                        key.c_str());
        }
        std::printf("\n");
    }
}

bool toInt(const char* s, int& out) {
    const std::string_view v(s);
    const auto [p, ec] = std::from_chars(v.data(), v.data() + v.size(), out);
    return ec == std::errc{} && p == v.data() + v.size();
}

} // namespace

int main(int argc, char** argv) {
    std::vector<std::string> args(argv + 1, argv + argc);
    std::filesystem::path assets = LC_WORLDINFO_ASSETS_DIR;
    if (args.size() >= 2 && args[0] == "--assets") {
        assets = args[1];
        args.erase(args.begin(), args.begin() + 2);
    }
    const std::string cmd = args.empty() ? "summary" : args[0];
    const auto cat = loadCatalog(assets / "catalog.json");
    if (!cat) {
        (void)std::fprintf(stderr, "worldinfo: %s\n", cat.error().c_str());
        return 2;
    }
    const auto world = loadWorld(assets, *cat);
    if (!world) {
        (void)std::fprintf(stderr, "worldinfo: %s\n", world.error().c_str());
        return 2;
    }
    if (cmd == "summary" && args.size() <= 1) {
        summary(*world);
    } else if (cmd == "validate" && args.size() == 1) {
        for (const auto& e : world->diagnostics.errors) std::printf("error: %s\n", e.c_str());
        for (const auto& e : world->diagnostics.warnings) std::printf("warning: %s\n", e.c_str());
        std::printf("%zu error(s), %zu warning(s)\n", world->diagnostics.errors.size(),
                    world->diagnostics.warnings.size());
        return world->diagnostics.errors.empty() ? 0 : 1;
    } else if (cmd == "digest" && args.size() == 1) {
        (void)std::fputs(toJson(digestOf(*world)).c_str(), stdout);
    } else if (cmd == "region" && args.size() == 2) {
        region(*world, args[1]);
    } else if (TilePos p; cmd == "tile" && args.size() == 3 && toInt(args[1].c_str(), p.x) &&
                          toInt(args[2].c_str(), p.y)) {
        tile(*world, p);
    } else if (int r = 0; cmd == "slopes" && args.size() == 4 && toInt(args[1].c_str(), p.x) &&
                          toInt(args[2].c_str(), p.y) && toInt(args[3].c_str(), r)) {
        slopes(*world, p, r);
    } else {
        (void)std::fputs(kUsage, stderr);
        return 2;
    }
    return 0;
}
