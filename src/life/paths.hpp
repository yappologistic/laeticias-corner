#pragma once
// Walking in a region without searching per actor (docs/design/living-world.md §7.6): the
// region's layer graph with every edge rasterised to its course of tiles (worldgen's
// path_tiles), a field that leads every walkable tile within reach of the graph onto it (built
// once), and next-hop tables towards destination nodes, built lazily under a per-step budget
// and kept in a small LRU. A route is a few numbers in the actor: climb the field to the graph,
// run along courses node to node by table, and descend to the goal. Also worldgen's slot labels
// (citylife._graph_labels) and integer graph distances, which the chains share with lifesim.

#include "world/graph_file.hpp"
#include "world/world_map.hpp"

#include <array>
#include <cstdint>
#include <span>
#include <string>
#include <unordered_map>
#include <vector>

namespace lc::life {

struct Tile16 {
    std::int16_t x = 0;
    std::int16_t y = 0;
    [[nodiscard]] TilePos pos() const { return {x, y}; }
    friend constexpr bool operator==(Tile16, Tile16) = default;
};
[[nodiscard]] inline Tile16 tile16(TilePos p) {
    return {static_cast<std::int16_t>(p.x), static_cast<std::int16_t>(p.y)};
}

enum class Leg : std::uint8_t { None, Line, Climb, Course, Hops, Descend, Done };

// Everything a walker needs to follow its route, kept in the actor.
struct Route {
    Leg leg = Leg::None;
    Leg then = Leg::None;     // after the current course: Hops or Descend
    std::int8_t step = 1;     // direction along the current course
    std::uint8_t descLen = 0; // tiles in the descent buffer
    std::uint8_t descPos = 0;
    std::int16_t edge = -1;      // the course being walked
    std::uint16_t idx = 0;       // position on it
    std::uint16_t end = 0;       // where this course leg stops
    std::uint16_t node = 0;      // the node the walk is heading for (Hops)
    std::uint16_t dest = 0;      // the last node before the goal's course; kSame: one course
    std::int16_t startEdge = -1; // start seed: an edge, or -1 when it is node `startIdx`
    std::uint16_t startIdx = 0;
    std::int16_t endEdge = -1; // goal seed, likewise
    std::uint16_t endIdx = 0;
    Tile16 start; // a straight line's first tile
    Tile16 goal;
};
inline constexpr std::uint16_t kSame = 0xFFFF;

enum class PlanResult : std::uint8_t { Ok, Wait, Fail };

class RegionPaths {
public:
    // Builds the courses, the field over the region's tiles grown by the reach, and the labels.
    RegionPaths(const world::WorldMap& map, const world::GraphFile& graph, int worldRegion);

    struct Edge {
        std::uint16_t a = 0;
        std::uint16_t b = 0;
        std::uint32_t begin = 0; // into courses: tiles from a's tile to b's
        std::uint32_t len = 0;
        int weight = 1;       // worldgen's: max(1, tiles - 1)
        bool blocked = false; // a course tile walkers cannot stand on, or a step they cannot make
    };

    [[nodiscard]] int nodeCount() const { return static_cast<int>(nodes_.size()); }
    [[nodiscard]] TilePos nodeAt(int n) const { return nodes_[static_cast<std::size_t>(n)].pos(); }
    [[nodiscard]] const std::string& nodeId(int n) const {
        return ids_[static_cast<std::size_t>(n)];
    }
    [[nodiscard]] int findNode(std::string_view id) const;
    // A relay station (couriers change horses there): its kind, or its name says so.
    [[nodiscard]] bool isStation(int n) const {
        return stations_[static_cast<std::size_t>(n)] != 0;
    }
    [[nodiscard]] std::span<const Edge> edges() const { return edges_; }
    [[nodiscard]] std::span<const Tile16> course(int e) const {
        const Edge& ed = edges_[static_cast<std::size_t>(e)];
        return {courses_.data() + ed.begin, ed.len};
    }
    [[nodiscard]] TileRect rect() const { return rect_; }
    [[nodiscard]] TileRect regionRect() const { return regionRect_; } // the region's own tiles
    [[nodiscard]] int worldRegion() const { return region_; }

    // The field: true when walkers can reach the graph from here.
    [[nodiscard]] bool reachable(TilePos p) const { return dirAt(p) != 0; }
    // worldgen's label of a tile (citylife._graph_labels): the node a walker reaches first, or -1.
    [[nodiscard]] int label(TilePos p) const;

    // Plans a walk from `from` to `to` into `r` and the descent buffer `desc`. Tables it needs
    // are built on the spot (counted in `builds`): the result never depends on what is cached.
    PlanResult plan(TilePos from, TilePos to, Route& r, std::span<Tile16> desc, int& builds);
    // The next tile of the route from `cur` (the tile the walker stands on); false when the goal
    // is reached or the way is lost.
    bool next(Route& r, TilePos cur, std::span<const Tile16> desc, TilePos& out);
    // Tiles left on a fresh route (walks it on a copy). -1 when it cannot be walked.
    int length(const Route& r, TilePos from, std::span<const Tile16> desc);

    // Integer path-graph distances from a node to every node (Dijkstra, worldgen weights);
    // unreachable nodes get INT_MAX.
    void distances(int from, std::vector<int>& out) const;

    [[nodiscard]] std::size_t memoryBytes() const;
    [[nodiscard]] int tablesBuilt() const { return tablesBuilt_; }
    // Course tiles a walker cannot stand on, and course steps no walker could make (data checks).
    [[nodiscard]] int badCourseTiles() const { return badCourseTiles_; }
    [[nodiscard]] int badCourseSteps() const { return badCourseSteps_; }
    [[nodiscard]] int blockedEdges() const { return blockedEdges_; }
    [[nodiscard]] bool onCourse(TilePos p) const;

    // A straight 4-connected line a walker can take (every step legal), at most `maxLen` tiles.
    [[nodiscard]] bool lineClear(TilePos a, TilePos b, int maxLen) const;

private:
    struct Seed {
        std::uint32_t key = 0;
        std::int16_t edge = -1; // -1: a node tile
        std::uint16_t idx = 0;  // course index, or the node
    };
    // Distances to one destination; the next hop is derived (the first neighbour on a shortest
    // way), so a table is two bytes a node.
    struct Table {
        int dest = -1;
        std::uint32_t used = 0;
        std::vector<std::uint16_t> dist; // per node: tiles to dest, 0xFFFF none
    };

    [[nodiscard]] std::size_t cell(TilePos p) const {
        return static_cast<std::size_t>(p.y - rect_.y0) * static_cast<std::size_t>(rect_.width()) +
               static_cast<std::size_t>(p.x - rect_.x0);
    }
    [[nodiscard]] bool inRect(TilePos p) const { return rect_.contains(p); }
    [[nodiscard]] std::uint8_t dirAt(TilePos p) const { return inRect(p) ? dir_[cell(p)] : 0; }
    [[nodiscard]] const Seed* seedAt(TilePos p) const;
    void buildField();
    void buildLabels(const world::GraphFile& graph);
    Table* table(int dest, int& builds);
    [[nodiscard]] int hop(const Table& t, int node) const; // adjacency index, -1 at dest or none
    void courseLeg(Route& r, int edge, int from, int to, Leg then) const;
    // `all`: blocked edges too (worldgen's distances); else the edges walkers can use.
    void buildTable(Table& t, int dest, bool all = false) const;
    [[nodiscard]] int edgeBetween(int a, int b) const;
    static TilePos lineStep(TilePos cur, TilePos a, TilePos b);

    const world::WorldMap* map_;
    int region_;
    TileRect regionRect_;
    TileRect rect_;
    std::vector<Tile16> nodes_;
    std::vector<std::string> ids_;
    std::vector<std::uint8_t> stations_;
    std::unordered_map<std::string, int> index_;
    std::vector<Edge> edges_;
    std::vector<Tile16> courses_;
    std::vector<std::uint32_t> adjStart_;
    std::vector<std::uint16_t> adjEdge_;    // per adjacency entry: the edge
    std::vector<std::uint8_t> dir_;         // 0 none, 1..4 kSteps index + 1, 5 seed
    std::vector<Seed> seeds_;               // sorted by key
    std::vector<std::int16_t> labels_;      // per cell: node, -1
    std::vector<std::uint32_t> courseKeys_; // sorted keys of every course tile
    std::vector<int> tableOf_;              // per node: index into tables_, -1
    std::vector<Table> tables_;
    std::uint32_t clock_ = 0;
    std::size_t tableCap_ = 0;
    int tablesBuilt_ = 0;
    int badCourseTiles_ = 0;
    int badCourseSteps_ = 0;
    int blockedEdges_ = 0;
};

// worldgen's raster.path_tiles over grid points (computed in plan coordinates, as worldgen does,
// so the staircases agree tile for tile). `cols` is the grid height (plan columns).
void pathTiles(std::span<const TilePos> points, int cols, std::vector<Tile16>& out);

} // namespace lc::life
