#pragma once
// The union of the layers' path graphs (docs/design/world-tech.md §2.5, §4.10): node ids become
// "<layer>:<id>", portals with the same id in two layers are one node. Built once at load with
// next-hop tables towards every destination node inside its region, so walkers never search per
// frame; long routes (tokens, caravans) use shortestPath once and keep the result.

#include "world/graph_file.hpp"
#include "world/world_map.hpp"

#include <cstdint>
#include <span>
#include <string>
#include <string_view>
#include <unordered_map>
#include <vector>

namespace lc::world {

struct RoadNode {
    std::string id; // "<layer>:<id>" of the first layer that has it
    TilePos at;
    NodeKind kind = NodeKind::Plain;
    int region = -1;   // WorldFile::regions index of its tile, -1 when none
    int component = 0; // connected component
    int destSlot = -1; // index among its region's dest nodes, -1 when not a dest with a table
};

struct RoadEdge {
    std::uint32_t a = 0;
    std::uint32_t b = 0;
    EdgeKind kind = EdgeKind::Road;
    float length = 0;           // tiles, along the polyline
    std::uint32_t viaBegin = 0; // into RoadGraph::viaPoints()
    std::uint32_t viaCount = 0;
};

struct RoadLane {
    std::string id; // "<layer>:<id>"
    LaneKind kind = LaneKind::Sea;
    std::vector<TilePos> points;
    std::vector<LanePort> ports;
};

// Reusable search state so repeated searches do not allocate.
struct PathScratch {
    std::vector<float> g;
    std::vector<std::uint32_t> parent;
    std::vector<std::uint32_t> stamp;
    std::vector<std::pair<float, std::uint32_t>> heap;
    std::uint32_t generation = 0;
};

class RoadGraph {
public:
    RoadGraph() = default;
    // `graphs` in composition order. Portals merged by id; a portal whose copies disagree on the
    // tile is reported and keeps the first.
    RoadGraph(std::span<const GraphFile> graphs, const WorldMap& map, Diagnostics& diag);

    [[nodiscard]] const std::vector<RoadNode>& nodes() const { return nodes_; }
    [[nodiscard]] const std::vector<RoadEdge>& edges() const { return edges_; }
    [[nodiscard]] const std::vector<RoadLane>& lanes() const { return lanes_; }
    [[nodiscard]] std::span<const TilePos> via(const RoadEdge& e) const {
        return {via_.data() + e.viaBegin, e.viaCount};
    }
    [[nodiscard]] int componentCount() const { return components_; }
    // Edges at a node (indices into edges()).
    [[nodiscard]] std::span<const std::uint32_t> edgesAt(std::uint32_t node) const {
        return {adj_.data() + adjStart_[node], adjStart_[node + 1] - adjStart_[node]};
    }
    // "<layer>:<id>" (a merged portal answers to every layer's name); -1 when absent.
    [[nodiscard]] int findNode(std::string_view id) const;
    // Nearest node to a point (tiles), -1 when the graph is empty.
    [[nodiscard]] int nearestNode(Vec2 p) const;
    // Next node from `from` towards the dest node `dest` (same region), -1 when `dest` has no
    // table, `from` is outside its region, or there is no way. O(1).
    [[nodiscard]] int nextHop(int from, int dest) const;
    // Shortest path (A*, by length) from `from` to `to`, nodes from `from` to `to` inclusive.
    // False when unreachable.
    [[nodiscard]] bool shortestPath(int from, int to, PathScratch& scratch,
                                    std::vector<std::uint32_t>& out) const;
    // The tiles a path passes through: node positions and the edges' via points, in order.
    void polyline(std::span<const std::uint32_t> path, std::vector<TilePos>& out) const;
    [[nodiscard]] std::size_t memoryBytes() const;

private:
    struct Hash {
        using is_transparent = void;
        std::size_t operator()(std::string_view s) const {
            return std::hash<std::string_view>{}(s);
        }
    };
    struct RegionTable {
        std::vector<std::uint32_t> nodes; // global node indices in this region
        std::vector<std::uint32_t> dests; // global indices of its dest nodes with tables
        std::vector<std::uint16_t> hop;   // [dest][local node]: local index of the next node
    };
    [[nodiscard]] int edgeBetween(std::uint32_t a, std::uint32_t b) const;
    void buildTables(Diagnostics& diag);

    std::vector<RoadNode> nodes_;
    std::vector<RoadEdge> edges_;
    std::vector<TilePos> via_;
    std::vector<RoadLane> lanes_;
    std::vector<std::uint32_t> adjStart_;
    std::vector<std::uint32_t> adj_;
    std::unordered_map<std::string, std::uint32_t, Hash, std::equal_to<>> index_;
    std::vector<std::uint16_t> localIndex_; // node -> index inside its region's table
    std::vector<RegionTable> tables_;       // per region
    // Nodes bucketed by 32 x 32 chunk for nearestNode.
    int bucketsX_ = 0;
    int bucketsY_ = 0;
    std::vector<std::uint32_t> bucketStart_;
    std::vector<std::uint32_t> bucketNodes_;
    int components_ = 0;
};

} // namespace lc::world
