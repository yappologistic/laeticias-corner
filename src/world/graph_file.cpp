#include "world/graph_file.hpp"

#include "world/json_util.hpp"

#include <array>
#include <unordered_map>
#include <unordered_set>

namespace lc::world {

using namespace detail;

namespace {

constexpr std::array<const char*, 6> kNodeKinds{"", "dest", "door", "gate", "station", "portal"};
constexpr std::array<const char*, 9> kEdgeKinds{"street",  "road", "track",  "stair", "ramp",
                                                "towpath", "quay", "bridge", "ford"};
constexpr std::array<const char*, 3> kLaneKinds{"sea", "river", "towpath"};

template <std::size_t N>
int kindIndex(const std::array<const char*, N>& names, const std::string& s, std::size_t from,
              const std::string& ctx) {
    for (std::size_t i = from; i < N; ++i)
        if (s == names[i]) return static_cast<int>(i);
    std::string all;
    for (std::size_t i = from; i < N; ++i) all += std::string(i > from ? ", " : "") + names[i];
    fail(ctx + ": kind '" + s + "' is not one of " + all);
}

std::vector<TilePos> points(const json& v, const std::string& ctx, int w, int h) {
    std::vector<TilePos> out;
    const json& a = asArray(v, ctx);
    out.reserve(a.size());
    for (std::size_t i = 0; i < a.size(); ++i)
        out.push_back(asTile(a[i], ctx + "[" + std::to_string(i) + "]", w, h));
    return out;
}

} // namespace

const char* nodeKindName(NodeKind k) {
    return k == NodeKind::Plain ? "plain" : kNodeKinds[static_cast<std::size_t>(k)];
}

const char* edgeKindName(EdgeKind k) {
    return kEdgeKinds[static_cast<std::size_t>(k)];
}

std::expected<GraphFile, std::string> parseGraphFile(std::string_view text, std::string_view file,
                                                     std::string_view layer, int gridW, int gridH) {
    const std::string f(file);
    try {
        const json doc = parseDocument(text, f);
        requireVersion1(doc, f);
        GraphFile g;
        g.layer = asString(field(doc, "layer", f), f + ": layer");
        if (g.layer != layer)
            fail(f + ": layer '" + g.layer + "' differs from '" + std::string(layer) + "'");
        std::unordered_map<std::string, int> index;
        const json& nodes = asArray(field(doc, "nodes", f), f + ": nodes");
        g.nodes.reserve(nodes.size());
        for (std::size_t i = 0; i < nodes.size(); ++i) {
            std::string ctx = f + ": nodes[" + std::to_string(i) + "]";
            GraphNode n;
            n.id = asString(field(nodes[i], "id", ctx), ctx + ": id");
            ctx += " '" + n.id + "'";
            if (n.id.empty() || !index.emplace(n.id, static_cast<int>(i)).second)
                fail(ctx + ": empty or duplicated node id");
            n.at = asTile(field(nodes[i], "at", ctx), ctx + ": at", gridW, gridH);
            if (has(nodes[i], "kind"))
                n.kind = static_cast<NodeKind>(
                    kindIndex(kNodeKinds, asString(nodes[i].at("kind"), ctx + ": kind"), 1, ctx));
            g.nodes.push_back(std::move(n));
        }
        const json& edges = asArray(field(doc, "edges", f), f + ": edges");
        g.edges.reserve(edges.size());
        for (std::size_t i = 0; i < edges.size(); ++i) {
            const std::string ctx = f + ": edges[" + std::to_string(i) + "]";
            GraphEdge e;
            const auto end = [&](const char* key) {
                const std::string id = asString(field(edges[i], key, ctx), ctx + ": " + key);
                const auto it = index.find(id);
                if (it == index.end()) fail(ctx + ": node '" + id + "' does not exist");
                return it->second;
            };
            e.a = end("a");
            e.b = end("b");
            if (e.a == e.b)
                fail(ctx + ": both ends are node '" + g.nodes[std::size_t(e.a)].id + "'");
            e.kind = static_cast<EdgeKind>(kindIndex(
                kEdgeKinds, asString(field(edges[i], "kind", ctx), ctx + ": kind"), 0, ctx));
            if (has(edges[i], "via"))
                e.via = points(edges[i].at("via"), ctx + ": via", gridW, gridH);
            g.edges.push_back(std::move(e));
        }
        if (has(doc, "lanes")) {
            std::unordered_set<std::string> laneIds;
            const json& lanes = asArray(doc.at("lanes"), f + ": lanes");
            for (std::size_t i = 0; i < lanes.size(); ++i) {
                std::string ctx = f + ": lanes[" + std::to_string(i) + "]";
                Lane ln;
                ln.id = asString(field(lanes[i], "id", ctx), ctx + ": id");
                ctx += " '" + ln.id + "'";
                if (ln.id.empty() || !laneIds.insert(ln.id).second)
                    fail(ctx + ": empty or duplicated lane id");
                ln.kind = static_cast<LaneKind>(kindIndex(
                    kLaneKinds, asString(field(lanes[i], "kind", ctx), ctx + ": kind"), 0, ctx));
                ln.points = points(field(lanes[i], "points", ctx), ctx + ": points", gridW, gridH);
                if (ln.points.size() < 2) fail(ctx + ": a lane needs at least two points");
                if (has(lanes[i], "ports")) {
                    std::unordered_set<std::string> portIds;
                    const json& ports = asArray(lanes[i].at("ports"), ctx + ": ports");
                    for (std::size_t p = 0; p < ports.size(); ++p) {
                        const std::string pc = ctx + ": ports[" + std::to_string(p) + "]";
                        LanePort port;
                        port.id = asString(field(ports[p], "id", pc), pc + ": id");
                        if (port.id.empty() || !portIds.insert(port.id).second)
                            fail(pc + ": empty or duplicated port id '" + port.id + "'");
                        port.at = asInt(field(ports[p], "at", pc), pc + ": at", 0,
                                        static_cast<long long>(ln.points.size()) - 1);
                        port.slot = stringOr(ports[p], "slot", "", pc);
                        ln.ports.push_back(std::move(port));
                    }
                }
                g.lanes.push_back(std::move(ln));
            }
        }
        return g;
    } catch (const Invalid& e) {
        return std::unexpected(e.what());
    }
}

} // namespace lc::world
