#pragma once
// One layer's path graph `<layer>.graph.json` (docs/design/world-tech.md §2.5): nodes, edges with
// their polylines, and lanes for ships and barges. Coordinates are grid tiles.

#include "core/iso.hpp"

#include <cstdint>
#include <expected>
#include <string>
#include <string_view>
#include <vector>

namespace lc::world {

enum class NodeKind : std::uint8_t { Plain, Dest, Door, Gate, Station, Portal };
enum class EdgeKind : std::uint8_t {
    Street,
    Road,
    Track,
    Stair,
    Ramp,
    Towpath,
    Quay,
    Bridge,
    Ford
};
enum class LaneKind : std::uint8_t { Sea, River, Towpath };

struct GraphNode {
    std::string id; // local to the layer; portals share ids across layers
    TilePos at;
    NodeKind kind = NodeKind::Plain;
};

struct GraphEdge {
    int a = 0; // indices into GraphFile::nodes
    int b = 0;
    EdgeKind kind = EdgeKind::Road;
    std::vector<TilePos> via; // polyline between the end nodes, exclusive
};

struct LanePort {
    std::string id;
    int at = 0;       // index into Lane::points
    std::string slot; // "<item>:<slot>", empty when none
};

struct Lane {
    std::string id;
    LaneKind kind = LaneKind::Sea;
    std::vector<TilePos> points;
    std::vector<LanePort> ports;
};

struct GraphFile {
    std::string layer;
    std::vector<GraphNode> nodes;
    std::vector<GraphEdge> edges;
    std::vector<Lane> lanes;
};

[[nodiscard]] const char* nodeKindName(NodeKind k);
[[nodiscard]] const char* edgeKindName(EdgeKind k);

// `layer` must match the file's "layer"; every point must lie in the grid.
[[nodiscard]] std::expected<GraphFile, std::string> parseGraphFile(std::string_view text,
                                                                   std::string_view file,
                                                                   std::string_view layer,
                                                                   int gridW, int gridH);

} // namespace lc::world
