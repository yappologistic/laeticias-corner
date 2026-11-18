#include "world/loader.hpp"

#include <algorithm>
#include <chrono>
#include <fstream>

namespace lc::world {

namespace {

using Clock = std::chrono::steady_clock;

double msSince(Clock::time_point t) {
    return std::chrono::duration<double, std::milli>(Clock::now() - t).count();
}

std::expected<std::vector<std::uint8_t>, std::string> readBytes(const std::filesystem::path& p) {
    std::ifstream in(p, std::ios::binary);
    if (!in) return std::unexpected(p.string() + ": cannot be opened");
    in.seekg(0, std::ios::end);
    const auto size = in.tellg();
    if (size < 0) return std::unexpected(p.string() + ": cannot be read");
    std::vector<std::uint8_t> data(static_cast<std::size_t>(size));
    in.seekg(0);
    in.read(reinterpret_cast<char*>(data.data()), static_cast<std::streamsize>(data.size()));
    if (!in) return std::unexpected(p.string() + ": cannot be read");
    return data;
}

} // namespace

std::size_t LoadedWorld::memoryBytes() const {
    std::size_t n = atlas.memoryBytes() + roads.memoryBytes();
    if (content) n += content->memoryBytes();
    if (map) n += map->memoryBytes();
    for (const GraphFile& g : graphs)
        n += g.nodes.capacity() * sizeof(GraphNode) + g.edges.capacity() * sizeof(GraphEdge) +
             g.lanes.capacity() * sizeof(Lane);
    for (const RegionFile& r : regions)
        n += sizeof(RegionFile) + r.cards.capacity() * sizeof(Card) + r.life.dump().size();
    return n;
}

std::expected<LoadedWorld, std::string> loadWorld(const std::filesystem::path& assets,
                                                  const Catalog& home) {
    const auto start = Clock::now();
    LoadedWorld w;
    Diagnostics& diag = w.diagnostics;

    auto t = Clock::now();
    const auto catalogText = readTextFile(assets / "catalog.json");
    if (!catalogText) return std::unexpected(catalogText.error());
    auto contract = parseHomeContract(*catalogText, "assets/catalog.json", home.tileH);
    if (!contract) return std::unexpected(contract.error());
    w.contract = std::move(*contract);
    if (w.contract.world.empty())
        return std::unexpected("assets/catalog.json: no 'world' entry names world.json");
    std::vector<SetCatalog> sets;
    std::vector<GeometryFile> geometry;
    for (const std::string& set : w.contract.sets) {
        const auto catFile = assets / "sets" / set / "catalog.json";
        if (std::filesystem::exists(catFile)) {
            const auto text = readTextFile(catFile);
            if (!text) return std::unexpected(text.error());
            auto sc = parseSetCatalog(*text, "assets/sets/" + set + "/catalog.json", set);
            if (!sc) return std::unexpected(sc.error());
            sets.push_back(std::move(*sc));
        } else {
            diag.warn("set '" + set + "' has no catalog yet (assets/sets/" + set +
                      "/catalog.json): its ids stay unresolved");
        }
        const auto geomFile = assets / "atlas" / (set + ".geom.json");
        if (std::filesystem::exists(geomFile)) {
            const auto text = readTextFile(geomFile);
            if (!text) return std::unexpected(text.error());
            auto g = parseGeometry(*text, "assets/atlas/" + set + ".geom.json", set);
            if (!g) return std::unexpected(g.error());
            if (g->tileW != home.tileW || g->tileH != home.tileH)
                diag.error(g->file + ": tile " + std::to_string(g->tileW) + " x " +
                           std::to_string(g->tileH) + " differs from the catalog's");
            geometry.push_back(std::move(*g));
        }
        if (auto ok = loadSetPages(w.atlas, assets / "atlas", set); !ok)
            return std::unexpected(ok.error());
    }
    auto content = Content::build(home, w.contract, std::move(sets), std::move(geometry));
    if (!content) return std::unexpected(content.error());
    w.content = std::make_unique<Content>(std::move(*content));
    w.content->validate(diag);
    w.timings.contracts = msSince(t);

    t = Clock::now();
    const std::filesystem::path worldPath = assets / w.contract.world;
    const std::filesystem::path worldDir = worldPath.parent_path();
    const auto worldText = readTextFile(worldPath);
    if (!worldText) return std::unexpected(worldText.error());
    auto wf = parseWorldFile(*worldText, "assets/" + w.contract.world);
    if (!wf) return std::unexpected(wf.error());
    w.file = std::move(*wf);
    std::vector<LayerFile> layerFiles;
    std::vector<std::string> layerIds;
    std::vector<const LayerRef*> refs;
    layerFiles.reserve(w.file.layers.size());
    for (const LayerRef& ref : w.file.layers) {
        const auto path = worldDir / ref.file;
        if (!std::filesystem::exists(path)) {
            diag.warn(ref.file + ": not built yet; the layers below show");
            continue;
        }
        const auto bytes = readBytes(path);
        if (!bytes) {
            diag.error(bytes.error() + "; layer skipped");
            continue;
        }
        auto lf = parseLayer(*bytes, w.file.gridW, w.file.gridH, ref.file);
        if (!lf) {
            diag.error(lf.error() + "; layer skipped");
            continue;
        }
        layerFiles.push_back(std::move(*lf));
        layerIds.push_back(ref.id);
        refs.push_back(&ref);
    }
    w.timings.layers = msSince(t);

    t = Clock::now();
    std::vector<LayerInput> inputs;
    inputs.reserve(layerFiles.size());
    for (std::size_t i = 0; i < layerFiles.size(); ++i)
        inputs.push_back({layerIds[i], &layerFiles[i]});
    w.map = std::make_unique<WorldMap>(w.file, *w.content, inputs, diag);
    w.layers = w.map->layers();
    w.timings.compose = msSince(t);

    t = Clock::now();
    for (std::size_t i = 0; i < refs.size(); ++i) {
        const LayerRef& ref = *refs[i];
        if (std::ranges::find(w.layers, ref.id) == w.layers.end()) continue;
        if (ref.graph.empty()) continue;
        const auto path = worldDir / ref.graph;
        if (!std::filesystem::exists(path)) {
            diag.warn(ref.graph + ": missing; layer " + ref.id + " has no paths");
            continue;
        }
        const auto text = readTextFile(path);
        if (!text) {
            diag.error(text.error());
            continue;
        }
        auto g = parseGraphFile(*text, ref.graph, ref.id, w.file.gridW, w.file.gridH);
        if (!g) {
            diag.error(g.error() + "; graph skipped");
            continue;
        }
        w.graphs.push_back(std::move(*g));
    }
    w.roads = RoadGraph(w.graphs, *w.map, diag);
    w.timings.graphs = msSince(t);

    t = Clock::now();
    w.regions.resize(w.file.regions.size());
    for (std::size_t i = 0; i < w.file.regions.size(); ++i) {
        const RegionRef& r = w.file.regions[i];
        if (r.life.empty()) continue;
        const auto path = assets / r.life;
        if (!std::filesystem::exists(path)) {
            diag.warn("assets/" + r.life + ": region '" + r.id + "' has no region file yet");
            continue;
        }
        const auto text = readTextFile(path);
        if (!text) {
            diag.error(text.error());
            continue;
        }
        auto rf = parseRegionFile(*text, "assets/" + r.life, r.id, w.file.gridW, w.file.gridH);
        if (!rf) {
            diag.error(rf.error() + "; region file skipped");
            continue;
        }
        w.regions[i] = std::move(*rf);
    }
    w.timings.regions = msSince(t);
    w.timings.total = msSince(start);
    return w;
}

} // namespace lc::world
