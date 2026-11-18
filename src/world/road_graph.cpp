#include "world/road_graph.hpp"

#include "world/tuning.hpp"

#include <algorithm>
#include <cmath>
#include <limits>
#include <numeric>

namespace lc::world {

namespace {

constexpr std::uint16_t kNoHop = 0xFFFF;

float dist(TilePos a, TilePos b) {
    const auto dx = static_cast<float>(a.x - b.x);
    const auto dy = static_cast<float>(a.y - b.y);
    return std::sqrt(dx * dx + dy * dy);
}

std::string at(TilePos p) {
    return "grid (" + std::to_string(p.x) + ", " + std::to_string(p.y) + ")";
}

} // namespace

RoadGraph::RoadGraph(std::span<const GraphFile> graphs, const WorldMap& map, Diagnostics& diag) {
    std::unordered_map<std::string, std::uint32_t> portals;
    for (const GraphFile& g : graphs) {
        std::vector<std::uint32_t> local(g.nodes.size());
        for (std::size_t i = 0; i < g.nodes.size(); ++i) {
            const GraphNode& n = g.nodes[i];
            const std::string full = g.layer + ":" + n.id;
            if (n.kind == NodeKind::Portal) {
                const auto it = portals.find(n.id);
                if (it != portals.end()) {
                    const RoadNode& first = nodes_[it->second];
                    if (first.at != n.at)
                        diag.error("layers/" + g.layer + ".graph.json: portal '" + n.id + "' at " +
                                   at(n.at) + ", but " + first.id + " is at " + at(first.at));
                    local[i] = it->second;
                    index_.emplace(full, it->second);
                    continue;
                }
                portals.emplace(n.id, static_cast<std::uint32_t>(nodes_.size()));
            }
            local[i] = static_cast<std::uint32_t>(nodes_.size());
            index_.emplace(full, local[i]);
            nodes_.push_back({full, n.at, n.kind, map.regionAt(n.at), 0, -1});
        }
        for (const GraphEdge& e : g.edges) {
            RoadEdge re;
            re.a = local[static_cast<std::size_t>(e.a)];
            re.b = local[static_cast<std::size_t>(e.b)];
            re.kind = e.kind;
            re.viaBegin = static_cast<std::uint32_t>(via_.size());
            re.viaCount = static_cast<std::uint32_t>(e.via.size());
            TilePos prev = nodes_[re.a].at;
            for (const TilePos v : e.via) {
                re.length += dist(prev, v);
                prev = v;
                via_.push_back(v);
            }
            re.length += dist(prev, nodes_[re.b].at);
            edges_.push_back(re);
        }
        for (const Lane& ln : g.lanes)
            lanes_.push_back({g.layer + ":" + ln.id, ln.kind, ln.points, ln.ports});
    }
    adjStart_.assign(nodes_.size() + 1, 0);
    for (const RoadEdge& e : edges_) {
        ++adjStart_[e.a + 1];
        ++adjStart_[e.b + 1];
    }
    std::partial_sum(adjStart_.begin(), adjStart_.end(), adjStart_.begin());
    adj_.resize(adjStart_.back());
    std::vector<std::uint32_t> fill(adjStart_.begin(), adjStart_.end() - 1);
    for (std::uint32_t i = 0; i < edges_.size(); ++i) {
        adj_[fill[edges_[i].a]++] = i;
        adj_[fill[edges_[i].b]++] = i;
    }
    // Components by flood fill.
    std::vector<int> comp(nodes_.size(), -1);
    std::vector<std::uint32_t> stack;
    for (std::uint32_t s = 0; s < nodes_.size(); ++s) {
        if (comp[s] >= 0) continue;
        comp[s] = components_;
        stack.push_back(s);
        while (!stack.empty()) {
            const std::uint32_t n = stack.back();
            stack.pop_back();
            for (const std::uint32_t e : edgesAt(n)) {
                const std::uint32_t o = edges_[e].a == n ? edges_[e].b : edges_[e].a;
                if (comp[o] < 0) {
                    comp[o] = components_;
                    stack.push_back(o);
                }
            }
        }
        ++components_;
    }
    for (std::size_t i = 0; i < nodes_.size(); ++i) nodes_[i].component = comp[i];
    bucketsX_ = (map.width() + kChunk - 1) >> kChunkShift;
    bucketsY_ = (map.height() + kChunk - 1) >> kChunkShift;
    const auto bucket = [&](const RoadNode& n) {
        return static_cast<std::size_t>((n.at.y >> kChunkShift) * bucketsX_ +
                                        (n.at.x >> kChunkShift));
    };
    bucketStart_.assign(static_cast<std::size_t>(bucketsX_ * bucketsY_) + 1, 0);
    for (const RoadNode& n : nodes_) ++bucketStart_[bucket(n) + 1];
    std::partial_sum(bucketStart_.begin(), bucketStart_.end(), bucketStart_.begin());
    bucketNodes_.resize(nodes_.size());
    fill.assign(bucketStart_.begin(), bucketStart_.end() - 1);
    for (std::uint32_t i = 0; i < nodes_.size(); ++i) bucketNodes_[fill[bucket(nodes_[i])]++] = i;
    buildTables(diag);
}

void RoadGraph::buildTables(Diagnostics& diag) {
    int regions = 0;
    for (const RoadNode& n : nodes_) regions = std::max(regions, n.region + 1);
    tables_.assign(static_cast<std::size_t>(regions), {});
    localIndex_.assign(nodes_.size(), kNoHop);
    for (std::uint32_t i = 0; i < nodes_.size(); ++i) {
        RoadNode& n = nodes_[i];
        if (n.region < 0) continue;
        RegionTable& t = tables_[static_cast<std::size_t>(n.region)];
        if (t.nodes.size() >= kNoHop) continue;
        localIndex_[i] = static_cast<std::uint16_t>(t.nodes.size());
        t.nodes.push_back(i);
        if (n.kind != NodeKind::Dest) continue;
        if (static_cast<int>(t.dests.size()) >= tuning::kMaxDestsPerRegion) {
            diag.error("dest node " + n.id + ": its region already has " +
                       std::to_string(tuning::kMaxDestsPerRegion) + " destinations");
            continue;
        }
        n.destSlot = static_cast<int>(t.dests.size());
        t.dests.push_back(i);
    }
    std::vector<float> d;
    std::vector<std::pair<float, std::uint16_t>> heap;
    for (std::size_t r = 0; r < tables_.size(); ++r) {
        RegionTable& t = tables_[r];
        const std::size_t n = t.nodes.size();
        t.hop.assign(t.dests.size() * n, kNoHop);
        for (std::size_t k = 0; k < t.dests.size(); ++k) {
            std::uint16_t* hop = t.hop.data() + k * n;
            d.assign(n, std::numeric_limits<float>::infinity());
            const std::uint16_t src = localIndex_[t.dests[k]];
            d[src] = 0;
            hop[src] = src;
            heap.assign(1, {0.0f, src});
            while (!heap.empty()) {
                std::ranges::pop_heap(heap, std::greater<>{});
                const auto [du, u] = heap.back();
                heap.pop_back();
                if (du > d[u]) continue;
                const std::uint32_t gu = t.nodes[u];
                for (const std::uint32_t e : edgesAt(gu)) {
                    const std::uint32_t go = edges_[e].a == gu ? edges_[e].b : edges_[e].a;
                    if (nodes_[go].region != static_cast<int>(r)) continue;
                    const std::uint16_t o = localIndex_[go];
                    if (o == kNoHop) continue;
                    const float nd = du + edges_[e].length;
                    if (nd < d[o]) {
                        d[o] = nd;
                        hop[o] = u; // from o, the next step towards the dest is u
                        heap.emplace_back(nd, o);
                        std::ranges::push_heap(heap, std::greater<>{});
                    }
                }
            }
        }
    }
}

int RoadGraph::findNode(std::string_view id) const {
    const auto it = index_.find(id);
    return it == index_.end() ? -1 : static_cast<int>(it->second);
}

int RoadGraph::nearestNode(Vec2 p) const {
    if (nodes_.empty()) return -1;
    const int bx = std::clamp(static_cast<int>(std::floor(p.x)) >> kChunkShift, 0, bucketsX_ - 1);
    const int by = std::clamp(static_cast<int>(std::floor(p.y)) >> kChunkShift, 0, bucketsY_ - 1);
    int best = -1;
    float bestD2 = std::numeric_limits<float>::infinity();
    const int rings = std::max(bucketsX_, bucketsY_);
    for (int r = 0; r <= rings; ++r) {
        const float reach = static_cast<float>((r - 1) * kChunk);
        if (best >= 0 && reach > 0 && reach * reach > bestD2) break;
        for (int y = by - r; y <= by + r; ++y)
            for (int x = bx - r; x <= bx + r; ++x) {
                if (std::max(std::abs(x - bx), std::abs(y - by)) != r) continue;
                if (x < 0 || y < 0 || x >= bucketsX_ || y >= bucketsY_) continue;
                const auto b = static_cast<std::size_t>(y * bucketsX_ + x);
                for (std::uint32_t k = bucketStart_[b]; k < bucketStart_[b + 1]; ++k) {
                    const RoadNode& n = nodes_[bucketNodes_[k]];
                    const float dx = static_cast<float>(n.at.x) + 0.5f - p.x;
                    const float dy = static_cast<float>(n.at.y) + 0.5f - p.y;
                    const float d2 = dx * dx + dy * dy;
                    if (d2 < bestD2 || (d2 == bestD2 && static_cast<int>(bucketNodes_[k]) < best)) {
                        bestD2 = d2;
                        best = static_cast<int>(bucketNodes_[k]);
                    }
                }
            }
    }
    return best;
}

int RoadGraph::nextHop(int from, int dest) const {
    if (from < 0 || dest < 0 || from >= static_cast<int>(nodes_.size()) ||
        dest >= static_cast<int>(nodes_.size()))
        return -1;
    const RoadNode& d = nodes_[static_cast<std::size_t>(dest)];
    if (d.destSlot < 0 || nodes_[static_cast<std::size_t>(from)].region != d.region) return -1;
    const RegionTable& t = tables_[static_cast<std::size_t>(d.region)];
    const std::uint16_t li = localIndex_[static_cast<std::size_t>(from)];
    if (li == kNoHop) return -1;
    const std::uint16_t h = t.hop[static_cast<std::size_t>(d.destSlot) * t.nodes.size() + li];
    return h == kNoHop ? -1 : static_cast<int>(t.nodes[h]);
}

bool RoadGraph::shortestPath(int from, int to, PathScratch& s,
                             std::vector<std::uint32_t>& out) const {
    out.clear();
    const auto n = nodes_.size();
    if (from < 0 || to < 0 || std::size_t(from) >= n || std::size_t(to) >= n) return false;
    if (nodes_[std::size_t(from)].component != nodes_[std::size_t(to)].component) return false;
    if (s.g.size() != n) {
        s.g.assign(n, 0);
        s.parent.assign(n, 0);
        s.stamp.assign(n, 0);
        s.generation = 0;
    }
    if (++s.generation == 0) {
        std::ranges::fill(s.stamp, 0);
        s.generation = 1;
    }
    const TilePos goal = nodes_[std::size_t(to)].at;
    const auto start = static_cast<std::uint32_t>(from);
    s.stamp[start] = s.generation;
    s.g[start] = 0;
    s.parent[start] = start;
    s.heap.assign(1, {dist(nodes_[start].at, goal), start});
    while (!s.heap.empty()) {
        std::ranges::pop_heap(s.heap, std::greater<>{});
        const auto [f, u] = s.heap.back();
        s.heap.pop_back();
        if (u == static_cast<std::uint32_t>(to)) break;
        if (f - dist(nodes_[u].at, goal) > s.g[u] + 1e-4f) continue; // stale entry
        for (const std::uint32_t e : edgesAt(u)) {
            const std::uint32_t o = edges_[e].a == u ? edges_[e].b : edges_[e].a;
            const float ng = s.g[u] + edges_[e].length;
            if (s.stamp[o] == s.generation && ng >= s.g[o]) continue;
            s.stamp[o] = s.generation;
            s.g[o] = ng;
            s.parent[o] = u;
            s.heap.emplace_back(ng + dist(nodes_[o].at, goal), o);
            std::ranges::push_heap(s.heap, std::greater<>{});
        }
    }
    if (s.stamp[std::size_t(to)] != s.generation) return false;
    for (auto v = static_cast<std::uint32_t>(to);; v = s.parent[v]) {
        out.push_back(v);
        if (v == start) break;
    }
    std::ranges::reverse(out);
    return true;
}

int RoadGraph::edgeBetween(std::uint32_t a, std::uint32_t b) const {
    int best = -1;
    for (const std::uint32_t e : edgesAt(a)) {
        const RoadEdge& re = edges_[e];
        if ((re.a == a && re.b == b) || (re.a == b && re.b == a))
            if (best < 0 || re.length < edges_[std::size_t(best)].length)
                best = static_cast<int>(e);
    }
    return best;
}

void RoadGraph::polyline(std::span<const std::uint32_t> path, std::vector<TilePos>& out) const {
    out.clear();
    for (std::size_t i = 0; i < path.size(); ++i) {
        out.push_back(nodes_[path[i]].at);
        if (i + 1 == path.size()) break;
        const int e = edgeBetween(path[i], path[i + 1]);
        if (e < 0) continue;
        const RoadEdge& re = edges_[std::size_t(e)];
        const auto v = via(re);
        if (re.a == path[i])
            out.insert(out.end(), v.begin(), v.end());
        else
            out.insert(out.end(), v.rbegin(), v.rend());
    }
}

std::size_t RoadGraph::memoryBytes() const {
    std::size_t n = nodes_.capacity() * sizeof(RoadNode) + edges_.capacity() * sizeof(RoadEdge) +
                    via_.capacity() * sizeof(TilePos) + lanes_.capacity() * sizeof(RoadLane) +
                    (adjStart_.capacity() + adj_.capacity() + bucketStart_.capacity() +
                     bucketNodes_.capacity()) *
                        sizeof(std::uint32_t) +
                    localIndex_.capacity() * sizeof(std::uint16_t) +
                    index_.size() * (sizeof(std::string) + 3 * sizeof(void*));
    for (const RoadNode& r : nodes_) n += r.id.capacity();
    for (const RegionTable& t : tables_)
        n += (t.nodes.capacity() + t.dests.capacity()) * sizeof(std::uint32_t) +
             t.hop.capacity() * sizeof(std::uint16_t);
    return n;
}

} // namespace lc::world
