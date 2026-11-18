#include "life/paths.hpp"

#include "core/tuning.hpp"

#include <algorithm>
#include <climits>
#include <cstdlib>
#include <deque>
#include <queue>

namespace lc::life {

namespace tl = tuning::life;
using world::kSteps;
using world::WalkStep;

void pathTiles(std::span<const TilePos> points, int cols, std::vector<Tile16>& out) {
    out.clear();
    const auto plan = [&](TilePos g) { return TilePos{cols - 1 - g.y, g.x}; };
    const auto push = [&](int c, int r) {
        out.push_back(tile16({r, cols - 1 - c})); // back to grid
    };
    for (std::size_t i = 0; i + 1 < points.size(); ++i) {
        const TilePos p0 = plan(points[i]);
        const TilePos p1 = plan(points[i + 1]);
        const int dc = p1.x - p0.x;
        const int dr = p1.y - p0.y;
        const int sc = dc > 0 ? 1 : -1;
        const int sr = dr > 0 ? 1 : -1;
        const int adc = std::abs(dc);
        const int adr = std::abs(dr);
        const Tile16 start = tile16({p0.y, cols - 1 - p0.x});
        if (out.empty() || !(out.back() == start)) push(p0.x, p0.y);
        int ic = 0;
        int ir = 0;
        for (int k = 0; k < adc + adr; ++k) {
            if (ic == adc)
                ++ir;
            else if (ir == adr)
                ++ic;
            else if (std::abs((ic + 1) * adr - ir * adc) <= std::abs(ic * adr - (ir + 1) * adc))
                ++ic;
            else
                ++ir;
            push(p0.x + sc * ic, p0.y + sr * ir);
        }
    }
    if (points.size() == 1) out.push_back(tile16(points[0]));
}

namespace {

std::uint32_t keyOf(TilePos p) {
    return (static_cast<std::uint32_t>(p.y) << 16) | static_cast<std::uint32_t>(p.x);
}

bool stepLegal(const world::WorldMap& m, TilePos a, TilePos b) {
    std::array<WalkStep, 4> steps{};
    const int n = m.walkNeighbours(a, steps);
    for (int i = 0; i < n; ++i)
        if (steps[static_cast<std::size_t>(i)].to == b) return true;
    return false;
}

} // namespace

RegionPaths::RegionPaths(const world::WorldMap& map, const world::GraphFile& graph, int worldRegion)
    : map_(&map), region_(worldRegion) {
    // The region's own tiles, grown by the reach of the field.
    TileRect bb{INT_MAX, INT_MAX, INT_MIN, INT_MIN};
    for (int y = 0; y < map.height(); ++y)
        for (int x = 0; x < map.width(); ++x)
            if (map.regionAt({x, y}) == worldRegion) {
                bb.x0 = std::min(bb.x0, x);
                bb.y0 = std::min(bb.y0, y);
                bb.x1 = std::max(bb.x1, x + 1);
                bb.y1 = std::max(bb.y1, y + 1);
            }
    if (bb.x0 > bb.x1) bb = {0, 0, 0, 0};
    regionRect_ = bb;
    rect_ = TileRect{bb.x0 - tl::kMoveReach, bb.y0 - tl::kMoveReach, bb.x1 + tl::kMoveReach,
                     bb.y1 + tl::kMoveReach}
                .clipped(map.bounds());
    for (std::size_t n = 0; n < graph.nodes.size(); ++n) {
        nodes_.push_back(tile16(graph.nodes[n].at));
        ids_.push_back(graph.nodes[n].id);
        stations_.push_back(graph.nodes[n].kind == world::NodeKind::Station ||
                                    graph.nodes[n].id.find("station") != std::string::npos
                                ? 1
                                : 0);
        index_.emplace(graph.nodes[n].id, static_cast<int>(n));
    }
    std::vector<TilePos> pts;
    std::vector<Tile16> tiles;
    std::vector<std::vector<std::uint16_t>> adj(nodes_.size());
    for (const world::GraphEdge& e : graph.edges) {
        pts.clear();
        pts.push_back(graph.nodes[static_cast<std::size_t>(e.a)].at);
        pts.insert(pts.end(), e.via.begin(), e.via.end());
        pts.push_back(graph.nodes[static_cast<std::size_t>(e.b)].at);
        pathTiles(pts, map.height(), tiles);
        Edge ed;
        ed.a = static_cast<std::uint16_t>(e.a);
        ed.b = static_cast<std::uint16_t>(e.b);
        ed.begin = static_cast<std::uint32_t>(courses_.size());
        ed.len = static_cast<std::uint32_t>(tiles.size());
        ed.weight = std::max(1, static_cast<int>(tiles.size()) - 1);
        courses_.insert(courses_.end(), tiles.begin(), tiles.end());
        const auto ei = static_cast<std::uint16_t>(edges_.size());
        adj[ed.a].push_back(ei);
        adj[ed.b].push_back(ei);
        edges_.push_back(ed);
        for (std::size_t i = 0; i < tiles.size(); ++i) {
            const TilePos t = tiles[i].pos();
            if (!map.walkable(t)) {
                ++badCourseTiles_;
                edges_.back().blocked = true;
            }
            if (i > 0 && !stepLegal(map, tiles[i - 1].pos(), t)) {
                ++badCourseSteps_;
                edges_.back().blocked = true;
            }
        }
        if (edges_.back().blocked) ++blockedEdges_;
    }
    adjStart_.push_back(0);
    for (const auto& a : adj) {
        adjEdge_.insert(adjEdge_.end(), a.begin(), a.end());
        adjStart_.push_back(static_cast<std::uint32_t>(adjEdge_.size()));
    }
    for (const Tile16 t : courses_) courseKeys_.push_back(keyOf(t.pos()));
    std::ranges::sort(courseKeys_);
    tableOf_.assign(nodes_.size(), -1);
    // Never reallocated: a plan holds pointers to two tables at once. At most about a megabyte
    // of tables per region (living-world §7.5).
    tableCap_ = std::clamp<std::size_t>(tl::kTableBytesPerRegion /
                                            std::max<std::size_t>(1, 2 * nodes_.size()),
                                        8, tl::kTablesPerRegion);
    tables_.reserve(tableCap_);
    buildField();
    buildLabels(graph);
}

int RegionPaths::findNode(std::string_view id) const {
    const auto it = index_.find(std::string(id));
    return it == index_.end() ? -1 : it->second;
}

bool RegionPaths::onCourse(TilePos p) const {
    return std::ranges::binary_search(courseKeys_, keyOf(p));
}

const RegionPaths::Seed* RegionPaths::seedAt(TilePos p) const {
    const std::uint32_t k = keyOf(p);
    const auto it = std::ranges::lower_bound(seeds_, k, {}, &Seed::key);
    return it != seeds_.end() && it->key == k ? &*it : nullptr;
}

void RegionPaths::buildField() {
    if (rect_.empty()) return;
    dir_.assign(static_cast<std::size_t>(rect_.width()) * static_cast<std::size_t>(rect_.height()),
                0);
    std::vector<std::uint8_t> depth(dir_.size(), 0);
    std::deque<TilePos> q;
    const auto seed = [&](TilePos t, std::int16_t edge, std::uint16_t idx) {
        if (!inRect(t) || !map_->walkable(t)) return;
        const std::size_t c = cell(t);
        if (dir_[c] == 5) return;
        dir_[c] = 5;
        seeds_.push_back({keyOf(t), edge, idx});
        q.push_back(t);
    };
    // Nodes first: a node tile is a node seed even where a course passes over it.
    for (std::size_t n = 0; n < nodes_.size(); ++n)
        seed(nodes_[n].pos(), -1, static_cast<std::uint16_t>(n));
    for (std::size_t e = 0; e < edges_.size(); ++e) {
        if (edges_[e].blocked) continue; // its tiles are reached from elsewhere, if at all
        const auto c = course(static_cast<int>(e));
        for (std::size_t i = 0; i < c.size(); ++i)
            seed(c[i].pos(), static_cast<std::int16_t>(e), static_cast<std::uint16_t>(i));
    }
    std::ranges::sort(seeds_, {}, &Seed::key);
    std::array<WalkStep, 4> steps{};
    while (!q.empty()) {
        const TilePos p = q.front();
        q.pop_front();
        const std::uint8_t d = depth[cell(p)];
        if (d >= tl::kMoveReach) continue;
        const int n = map_->walkNeighbours(p, steps);
        for (int i = 0; i < n; ++i) {
            const TilePos to = steps[static_cast<std::size_t>(i)].to;
            if (!inRect(to) || dir_[cell(to)] != 0 || !stepLegal(*map_, to, p)) continue;
            // The direction from `to` back to `p`.
            const TilePos back{p.x - to.x, p.y - to.y};
            for (std::uint8_t k = 0; k < 4; ++k)
                if (kSteps[k] == back) dir_[cell(to)] = static_cast<std::uint8_t>(k + 1);
            depth[cell(to)] = static_cast<std::uint8_t>(d + 1);
            q.push_back(to);
        }
    }
}

void RegionPaths::buildLabels(const world::GraphFile& graph) {
    // citylife._graph_labels in plan coordinates: seeds from every course (the nearer end's
    // node), node tiles over them, then a breadth-first spread in sorted order, at most REACH
    // steps, inside the region's rect grown by 2, over walkable tiles of one level or stairs.
    labels_.assign(dir_.size(), -1);
    if (rect_.empty()) return;
    const int cols = map_->height();
    const auto plan = [&](TilePos g) { return TilePos{cols - 1 - g.y, g.x}; };
    const auto grid = [&](TilePos p) { return TilePos{p.y, cols - 1 - p.x}; };
    std::vector<std::uint8_t> depth(dir_.size(), 0);
    std::vector<TilePos> seeds; // plan tiles
    const auto put = [&](TilePos g, int label, bool overwrite) {
        if (!inRect(g)) return;
        std::int16_t& l = labels_[cell(g)];
        if (l >= 0 && !overwrite) return;
        if (l < 0) seeds.push_back(plan(g));
        l = static_cast<std::int16_t>(label);
    };
    for (std::size_t e = 0; e < edges_.size(); ++e) {
        const auto c = course(static_cast<int>(e));
        const double half = static_cast<double>(c.size()) / 2.0;
        for (std::size_t i = 0; i < c.size(); ++i)
            put(c[i].pos(), static_cast<double>(i) < half ? edges_[e].a : edges_[e].b, false);
    }
    for (std::size_t n = 0; n < graph.nodes.size(); ++n)
        put(nodes_[n].pos(), static_cast<int>(n), true);
    std::ranges::sort(seeds,
                      [](TilePos a, TilePos b) { return a.x != b.x ? a.x < b.x : a.y < b.y; });
    const TilePos pa = plan({regionRect_.x0, regionRect_.y1 - 1});
    const TilePos pb = plan({regionRect_.x1 - 1, regionRect_.y0});
    const int c0 = std::min(pa.x, pb.x) - 2;
    const int c1 = std::max(pa.x, pb.x) + 2;
    const int r0 = std::min(pa.y, pb.y) - 2;
    const int r1 = std::max(pa.y, pb.y) + 2;
    const auto stair = [&](TilePos g) {
        const int it = map_->itemAt(g);
        return it >= 0 && map_->info(map_->items()[static_cast<std::size_t>(it)]).rise > 0;
    };
    std::deque<TilePos> q(seeds.begin(), seeds.end());
    static constexpr std::array<TilePos, 4> kPlanSteps{{{1, 0}, {-1, 0}, {0, 1}, {0, -1}}};
    while (!q.empty()) {
        const TilePos p = q.front();
        q.pop_front();
        const TilePos g = grid(p);
        const std::uint8_t d = depth[cell(g)];
        if (d >= tl::kLabelReach) continue;
        for (const TilePos s : kPlanSteps) {
            const TilePos n{p.x + s.x, p.y + s.y};
            if (n.x < c0 || n.x > c1 || n.y < r0 || n.y > r1) continue;
            const TilePos ng = grid(n);
            if (!inRect(ng) || labels_[cell(ng)] >= 0) continue;
            if (!map_->walkable(ng)) continue;
            if (map_->level(ng) != map_->level(g) && !stair(ng) && !stair(g)) continue;
            labels_[cell(ng)] = labels_[cell(g)];
            depth[cell(ng)] = static_cast<std::uint8_t>(d + 1);
            q.push_back(n);
        }
    }
}

int RegionPaths::label(TilePos p) const {
    return inRect(p) ? labels_[cell(p)] : -1;
}

int RegionPaths::edgeBetween(int a, int b) const {
    for (std::uint32_t k = adjStart_[static_cast<std::size_t>(a)];
         k < adjStart_[static_cast<std::size_t>(a) + 1]; ++k) {
        const Edge& e = edges_[adjEdge_[k]];
        if ((e.a == a && e.b == b) || (e.b == a && e.a == b)) return adjEdge_[k];
    }
    return -1;
}

void RegionPaths::buildTable(Table& t, int dest, bool all) const {
    const std::size_t n = nodes_.size();
    t.dest = dest;
    t.dist.assign(n, 0xFFFF);
    std::vector<int> dist(n, INT_MAX);
    using Item = std::pair<int, int>;
    std::priority_queue<Item, std::vector<Item>, std::greater<>> heap;
    dist[static_cast<std::size_t>(dest)] = 0;
    heap.emplace(0, dest);
    while (!heap.empty()) {
        const auto [d, u] = heap.top();
        heap.pop();
        if (d > dist[static_cast<std::size_t>(u)]) continue;
        for (std::uint32_t k = adjStart_[static_cast<std::size_t>(u)];
             k < adjStart_[static_cast<std::size_t>(u) + 1]; ++k) {
            const Edge& e = edges_[adjEdge_[k]];
            if (e.blocked && !all) continue;
            const int v = e.a == u ? e.b : e.a;
            const int nd = d + e.weight;
            if (nd < dist[static_cast<std::size_t>(v)]) {
                dist[static_cast<std::size_t>(v)] = nd;
                heap.emplace(nd, v);
            }
        }
    }
    for (std::size_t u = 0; u < n; ++u)
        if (dist[u] != INT_MAX) t.dist[u] = static_cast<std::uint16_t>(std::min(dist[u], 0xFFFE));
}

int RegionPaths::hop(const Table& t, int node) const {
    const auto u = static_cast<std::size_t>(node);
    if (node == t.dest || t.dist[u] == 0xFFFF) return -1;
    // The first neighbour on a shortest way (lowest adjacency index: deterministic).
    for (std::uint32_t k = adjStart_[u]; k < adjStart_[u + 1]; ++k) {
        const Edge& e = edges_[adjEdge_[k]];
        if (e.blocked) continue;
        const int v = e.a == node ? e.b : e.a;
        const std::uint16_t dv = t.dist[static_cast<std::size_t>(v)];
        if (dv != 0xFFFF && dv + e.weight == t.dist[u]) return static_cast<int>(k - adjStart_[u]);
    }
    return -1;
}

RegionPaths::Table* RegionPaths::table(int dest, int& builds) {
    const int at = tableOf_[static_cast<std::size_t>(dest)];
    if (at >= 0) {
        tables_[static_cast<std::size_t>(at)].used = ++clock_;
        return &tables_[static_cast<std::size_t>(at)];
    }
    --builds; // counted, never refused: what is cached must not change where anyone walks
    std::size_t slot = tables_.size();
    if (tables_.size() < tableCap_) {
        tables_.emplace_back();
    } else {
        slot = static_cast<std::size_t>(std::ranges::min_element(tables_, {}, &Table::used) -
                                        tables_.begin());
        tableOf_[static_cast<std::size_t>(tables_[slot].dest)] = -1;
    }
    buildTable(tables_[slot], dest);
    tables_[slot].used = ++clock_;
    tableOf_[static_cast<std::size_t>(dest)] = static_cast<int>(slot);
    ++tablesBuilt_;
    return &tables_[slot];
}

void RegionPaths::distances(int from, std::vector<int>& out) const {
    Table t;
    buildTable(t, from, true);
    out.assign(nodes_.size(), INT_MAX);
    for (std::size_t u = 0; u < nodes_.size(); ++u)
        if (t.dist[u] != 0xFFFF) out[u] = t.dist[u];
}

TilePos RegionPaths::lineStep(TilePos cur, TilePos a, TilePos b) {
    // One step of the staircase from a to b, as path_tiles chooses: the axis keeping closest to
    // the exact line.
    const int dx = b.x - a.x;
    const int dy = b.y - a.y;
    const int ix = std::abs(cur.x - a.x);
    const int iy = std::abs(cur.y - a.y);
    const int adx = std::abs(dx);
    const int ady = std::abs(dy);
    const int sx = dx > 0 ? 1 : -1;
    const int sy = dy > 0 ? 1 : -1;
    if (ix == adx) return {cur.x, cur.y + sy};
    if (iy == ady) return {cur.x + sx, cur.y};
    if (std::abs((ix + 1) * ady - iy * adx) <= std::abs(ix * ady - (iy + 1) * adx))
        return {cur.x + sx, cur.y};
    return {cur.x, cur.y + sy};
}

bool RegionPaths::lineClear(TilePos a, TilePos b, int maxLen) const {
    if (std::abs(b.x - a.x) + std::abs(b.y - a.y) > maxLen) return false;
    TilePos cur = a;
    while (!(cur == b)) {
        const TilePos nx = lineStep(cur, a, b);
        if (!stepLegal(*map_, cur, nx)) return false;
        cur = nx;
    }
    return true;
}

PlanResult RegionPaths::plan(TilePos from, TilePos to, Route& r, std::span<Tile16> desc,
                             int& builds) {
    r = Route{};
    r.goal = tile16(to);
    if (from == to) {
        r.leg = Leg::Done;
        return PlanResult::Ok;
    }
    if (lineClear(from, to, 16)) {
        r.leg = Leg::Line;
        r.start = tile16(from);
        return PlanResult::Ok;
    }
    if (!reachable(from) || !reachable(to)) return PlanResult::Fail;
    // The goal's chain up to its seed, kept reversed for the descent.
    std::size_t n = 0;
    TilePos t = to;
    while (dirAt(t) != 5) {
        if (n >= desc.size()) return PlanResult::Fail;
        desc[n++] = tile16(t);
        const TilePos s = kSteps[static_cast<std::size_t>(dirAt(t) - 1)];
        t = {t.x + s.x, t.y + s.y};
    }
    std::reverse(desc.begin(), desc.begin() + static_cast<std::ptrdiff_t>(n));
    r.descLen = static_cast<std::uint8_t>(n);
    const Seed* gs = seedAt(t);
    TilePos f = from;
    while (dirAt(f) != 5) {
        const TilePos s = kSteps[static_cast<std::size_t>(dirAt(f) - 1)];
        f = {f.x + s.x, f.y + s.y};
    }
    const Seed* ss = seedAt(f);
    if (gs == nullptr || ss == nullptr) return PlanResult::Fail;
    r.startEdge = ss->edge;
    r.startIdx = ss->idx;
    r.endEdge = gs->edge;
    r.endIdx = gs->idx;
    r.leg = Leg::Climb;
    if ((ss->edge >= 0 && ss->edge == gs->edge) ||
        (ss->edge < 0 && gs->edge < 0 && ss->idx == gs->idx)) {
        r.dest = kSame; // one course (or one node) holds both seeds
        return PlanResult::Ok;
    }
    // Candidate nodes at either end: (node, tiles from the seed).
    struct Cand {
        int node;
        int cost;
    };
    const auto ends = [&](const Seed& s, std::array<Cand, 2>& out) {
        if (s.edge < 0) {
            out[0] = {s.idx, 0};
            return 1;
        }
        const Edge& e = edges_[static_cast<std::size_t>(s.edge)];
        out[0] = {e.a, s.idx};
        out[1] = {e.b, static_cast<int>(e.len) - 1 - s.idx};
        return 2;
    };
    std::array<Cand, 2> us{};
    std::array<Cand, 2> vs{};
    const int nu = ends(*ss, us);
    const int nv = ends(*gs, vs);
    std::array<const Table*, 2> tabs{};
    for (std::size_t j = 0; j < static_cast<std::size_t>(nv); ++j) {
        tabs[j] = table(vs[j].node, builds);
        if (tabs[j] == nullptr) return PlanResult::Wait;
    }
    int best = INT_MAX;
    for (std::size_t i = 0; i < static_cast<std::size_t>(nu); ++i)
        for (std::size_t j = 0; j < static_cast<std::size_t>(nv); ++j) {
            const std::uint16_t d = tabs[j]->dist[static_cast<std::size_t>(us[i].node)];
            if (d == 0xFFFF) continue;
            const int cost = us[i].cost + d + vs[j].cost;
            if (cost < best) {
                best = cost;
                r.node = static_cast<std::uint16_t>(us[i].node);
                r.dest = static_cast<std::uint16_t>(vs[j].node);
            }
        }
    return best == INT_MAX ? PlanResult::Fail : PlanResult::Ok;
}

void RegionPaths::courseLeg(Route& r, int edge, int from, int to, Leg then) const {
    r.leg = Leg::Course;
    r.edge = static_cast<std::int16_t>(edge);
    r.idx = static_cast<std::uint16_t>(from);
    r.end = static_cast<std::uint16_t>(to);
    r.step = static_cast<std::int8_t>(to >= from ? 1 : -1);
    r.then = then;
}

bool RegionPaths::next(Route& r, TilePos cur, std::span<const Tile16> desc, TilePos& out) {
    // A node's position on an edge's course.
    const auto at = [&](int edge, int node) {
        const Edge& e = edges_[static_cast<std::size_t>(edge)];
        return e.a == node ? 0 : static_cast<int>(e.len) - 1;
    };
    for (int guard = 0; guard < 16; ++guard) {
        switch (r.leg) {
        case Leg::None:
        case Leg::Done: return false;
        case Leg::Line:
            if (cur == r.goal.pos()) {
                r.leg = Leg::Done;
                return false;
            }
            out = lineStep(cur, r.start.pos(), r.goal.pos());
            return true;
        case Leg::Climb: {
            const std::uint8_t d = dirAt(cur);
            if (d == 0) {
                r.leg = Leg::Done;
                return false;
            }
            if (d != 5) {
                const TilePos s = kSteps[static_cast<std::size_t>(d - 1)];
                out = {cur.x + s.x, cur.y + s.y};
                return true;
            }
            if (r.dest == kSame) {
                if (r.startEdge >= 0)
                    courseLeg(r, r.startEdge, r.startIdx, r.endIdx, Leg::Descend);
                else
                    r.leg = Leg::Descend;
            } else if (r.startEdge >= 0) {
                courseLeg(r, r.startEdge, r.startIdx, at(r.startEdge, r.node), Leg::Hops);
            } else {
                r.leg = Leg::Hops;
            }
            continue;
        }
        case Leg::Course: {
            if (r.idx == r.end) {
                r.leg = r.then;
                continue;
            }
            r.idx = static_cast<std::uint16_t>(r.idx + r.step);
            out = courses_[edges_[static_cast<std::size_t>(r.edge)].begin + r.idx].pos();
            return true;
        }
        case Leg::Hops: {
            if (r.node == r.dest) {
                if (r.endEdge >= 0)
                    courseLeg(r, r.endEdge, at(r.endEdge, r.dest), r.endIdx, Leg::Descend);
                else
                    r.leg = Leg::Descend;
                continue;
            }
            int force = 1; // a table evicted mid-walk is rebuilt at once
            const Table* t = table(r.dest, force);
            const int k = hop(*t, r.node);
            if (k < 0) {
                r.leg = Leg::Done;
                return false;
            }
            const int e = adjEdge_[adjStart_[r.node] + static_cast<std::uint32_t>(k)];
            const Edge& ed = edges_[static_cast<std::size_t>(e)];
            const int from = at(e, r.node);
            r.node = ed.a == r.node ? ed.b : ed.a;
            courseLeg(r, e, from, from == 0 ? static_cast<int>(ed.len) - 1 : 0, Leg::Hops);
            continue;
        }
        case Leg::Descend:
            if (r.descPos < r.descLen) {
                out = desc[r.descPos++].pos();
                return true;
            }
            r.leg = Leg::Done;
            return false;
        }
    }
    r.leg = Leg::Done;
    return false;
}

int RegionPaths::length(const Route& r, TilePos from, std::span<const Tile16> desc) {
    Route copy = r;
    TilePos cur = from;
    TilePos nx;
    int n = 0;
    while (next(copy, cur, desc, nx)) {
        cur = nx;
        if (++n > 100000) return -1;
    }
    return cur == r.goal.pos() ? n : -1;
}

std::size_t RegionPaths::memoryBytes() const {
    std::size_t n = nodes_.capacity() * sizeof(Tile16) + edges_.capacity() * sizeof(Edge) +
                    courses_.capacity() * sizeof(Tile16) + dir_.capacity() +
                    seeds_.capacity() * sizeof(Seed) + labels_.capacity() * sizeof(std::int16_t) +
                    courseKeys_.capacity() * 4 + adjEdge_.capacity() * 2 + adjStart_.capacity() * 4;
    for (const Table& t : tables_) n += t.dist.capacity() * 2;
    return n;
}

} // namespace lc::life
