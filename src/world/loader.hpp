#pragma once
// Loads the whole world from an assets directory (docs/design/world-tech.md §4.2): the home
// contract fields, set catalogs, geometry, atlas manifests, world.json, every layer and graph,
// the region files; composes the layers and builds the road graph. Contract and format errors in
// catalogs, geometry, manifests and world.json stop the load; a broken or missing layer, graph or
// region file is left out with a diagnostic (the base shows instead).

#include "core/catalog.hpp"
#include "world/atlas_pages.hpp"
#include "world/content.hpp"
#include "world/diagnostics.hpp"
#include "world/graph_file.hpp"
#include "world/region_file.hpp"
#include "world/road_graph.hpp"
#include "world/world_file.hpp"
#include "world/world_map.hpp"

#include <expected>
#include <filesystem>
#include <memory>
#include <string>
#include <vector>

namespace lc::world {

struct LoadTimings {      // milliseconds
    double contracts = 0; // home contract fields, set catalogs, geometry, atlas manifests
    double layers = 0;    // world.json, reading and parsing layer files
    double compose = 0;
    double graphs = 0;
    double regions = 0;
    double total = 0;
};

struct LoadedWorld {
    HomeContract contract;
    WorldFile file;
    std::unique_ptr<Content> content; // stable address: the map points at it
    AtlasPages atlas;
    std::vector<std::string> layers; // ids of the layers composed, in order
    std::vector<GraphFile> graphs;   // per composed layer that has a valid graph
    std::vector<RegionFile> regions; // per WorldFile region; id empty when it has no file
    std::unique_ptr<WorldMap> map;
    RoadGraph roads;
    Diagnostics diagnostics;
    LoadTimings timings;

    // Bytes held by everything above (the CPU side of the world, world-tech §2.8).
    [[nodiscard]] std::size_t memoryBytes() const;
};

// `home` (the parsed assets/catalog.json) must outlive the result.
[[nodiscard]] std::expected<LoadedWorld, std::string> loadWorld(const std::filesystem::path& assets,
                                                                const Catalog& home);

} // namespace lc::world
