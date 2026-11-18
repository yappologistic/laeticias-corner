#include "world/digest.hpp"

#include "world/json_util.hpp"

#include <algorithm>
#include <charconv>
#include <format>
#include <tuple>

namespace lc::world {

using namespace detail;

namespace {

struct Fnv {
    std::uint64_t h = 0xcbf29ce484222325ull;
    void byte(std::uint8_t b) {
        h ^= b;
        h *= 0x100000001b3ull;
    }
    void text(std::string_view s) {
        for (const char c : s) byte(static_cast<std::uint8_t>(c));
        byte(0);
    }
    void u16(int v) {
        byte(static_cast<std::uint8_t>(v & 0xFF));
        byte(static_cast<std::uint8_t>((v >> 8) & 0xFF));
    }
};

std::string hex(std::uint64_t v) {
    return std::format("{:016x}", v);
}

} // namespace

WorldDigest digestOf(const LoadedWorld& world) {
    const WorldMap& m = *world.map;
    WorldDigest d;
    d.gridW = m.width();
    d.gridH = m.height();
    d.chunk = kChunk;
    d.layers = world.layers;
    d.chunks.resize(static_cast<std::size_t>(m.chunksX() * m.chunksY()));
    for (int cy = 0; cy < m.chunksY(); ++cy)
        for (int cx = 0; cx < m.chunksX(); ++cx) {
            Fnv t;
            Fnv l;
            Fnv ds;
            for (int y = cy * kChunk; y < std::min((cy + 1) * kChunk, m.height()); ++y)
                for (int x = cx * kChunk; x < std::min((cx + 1) * kChunk, m.width()); ++x) {
                    const int ter = m.terrainAt({x, y});
                    t.text(ter == kNone ? "" : m.terrainInfo(ter).id);
                    l.byte(m.levelByte({x, y}));
                    const int dis = m.districtAt({x, y});
                    ds.text(dis == kNone ? "" : m.districtName(dis));
                }
            auto& c = d.chunks[static_cast<std::size_t>(cy * m.chunksX() + cx)];
            c[0] = t.h;
            c[1] = l.h;
            c[2] = ds.h;
        }
    std::vector<std::vector<std::tuple<int, int, std::string_view, int>>> byChunk(d.chunks.size());
    for (const Placed& it : m.items()) {
        const std::string& id = m.info(it).id;
        ++d.itemCounts[id];
        ++d.itemsTotal;
        const auto c =
            static_cast<std::size_t>((it.y >> kChunkShift) * m.chunksX() + (it.x >> kChunkShift));
        byChunk[c].emplace_back(it.y, it.x, id, it.variant);
    }
    for (std::size_t c = 0; c < byChunk.size(); ++c) {
        std::ranges::sort(byChunk[c]);
        Fnv f;
        for (const auto& [y, x, id, v] : byChunk[c]) {
            f.text(id);
            f.u16(x);
            f.u16(y);
            f.byte(static_cast<std::uint8_t>(v));
        }
        d.chunks[c][3] = f.h;
    }
    for (const auto& [id, n] : m.unresolved()) d.unresolved[id] = n;
    for (const GraphFile& g : world.graphs)
        d.graphs[g.layer] = {static_cast<int>(g.nodes.size()), static_cast<int>(g.edges.size()),
                             static_cast<int>(g.lanes.size())};
    d.mergedNodes = static_cast<int>(world.roads.nodes().size());
    return d;
}

std::string toJson(const WorldDigest& d) {
    json j;
    j["version"] = 1;
    j["grid"] = {d.gridW, d.gridH};
    j["chunk"] = d.chunk;
    j["layers"] = d.layers;
    j["items_total"] = d.itemsTotal;
    j["item_counts"] = d.itemCounts;
    j["unresolved"] = d.unresolved;
    json g = json::object();
    for (const auto& [layer, s] : d.graphs)
        g[layer] = {{"nodes", s.nodes}, {"edges", s.edges}, {"lanes", s.lanes}};
    j["graphs"] = g;
    j["merged_nodes"] = d.mergedNodes;
    json chunks = json::array();
    for (const auto& c : d.chunks) chunks.push_back({hex(c[0]), hex(c[1]), hex(c[2]), hex(c[3])});
    j["chunks"] = chunks;
    return j.dump(1) + "\n";
}

std::expected<WorldDigest, std::string> parseDigest(std::string_view text, std::string_view file) {
    const std::string f(file);
    try {
        const json doc = parseDocument(text, f);
        requireVersion1(doc, f);
        WorldDigest d;
        const auto grid = asIntPair(field(doc, "grid", f), f + ": grid", 1, 1 << 16);
        d.gridW = grid[0];
        d.gridH = grid[1];
        d.chunk = asInt(field(doc, "chunk", f), f + ": chunk", 1, 1 << 16);
        d.layers = asStrings(field(doc, "layers", f), f + ": layers");
        d.itemsTotal = asInt(field(doc, "items_total", f), f + ": items_total", 0, 1 << 30);
        for (const auto& [id, n] : asObject(field(doc, "item_counts", f), f).items())
            d.itemCounts[id] = asInt(n, f + ": item_counts", 0, 1 << 30);
        for (const auto& [id, n] : asObject(field(doc, "unresolved", f), f).items())
            d.unresolved[id] = asInt(n, f + ": unresolved", 0, 1 << 30);
        for (const auto& [layer, s] : asObject(field(doc, "graphs", f), f).items()) {
            const std::string c = f + ": graphs: " + layer;
            d.graphs[layer] = {asInt(field(s, "nodes", c), c, 0, 1 << 30),
                               asInt(field(s, "edges", c), c, 0, 1 << 30),
                               asInt(field(s, "lanes", c), c, 0, 1 << 30)};
        }
        d.mergedNodes = asInt(field(doc, "merged_nodes", f), f + ": merged_nodes", 0, 1 << 30);
        const json& chunks = asArray(field(doc, "chunks", f), f + ": chunks");
        for (std::size_t i = 0; i < chunks.size(); ++i) {
            const std::string c = f + ": chunks[" + std::to_string(i) + "]";
            if (!chunks[i].is_array() || chunks[i].size() != 4) fail(c + ": expected 4 hashes");
            std::array<std::uint64_t, 4> h{};
            for (std::size_t k = 0; k < 4; ++k) {
                const std::string s = asString(chunks[i][k], c);
                const auto [p, ec] = std::from_chars(s.data(), s.data() + s.size(), h[k], 16);
                if (ec != std::errc{} || p != s.data() + s.size() || s.size() != 16)
                    fail(c + ": '" + s + "' is not a 16-digit hex hash");
            }
            d.chunks.push_back(h);
        }
        return d;
    } catch (const Invalid& e) {
        return std::unexpected(e.what());
    }
}

std::vector<std::string> compareDigests(const WorldDigest& a, const WorldDigest& b) {
    std::vector<std::string> out;
    if (a.gridW != b.gridW || a.gridH != b.gridH || a.chunk != b.chunk)
        out.emplace_back("grid or chunk size differs");
    if (a.layers != b.layers) out.emplace_back("composed layers differ");
    if (a.itemsTotal != b.itemsTotal)
        out.emplace_back("items: " + std::to_string(a.itemsTotal) + " expected, " +
                         std::to_string(b.itemsTotal) + " loaded");
    const auto maps = [&](const std::map<std::string, int>& x, const std::map<std::string, int>& y,
                          const char* what) {
        for (const auto& [id, n] : x) {
            const auto it = y.find(id);
            const int m = it == y.end() ? 0 : it->second;
            if (m != n)
                out.emplace_back(std::string(what) + " " + id + ": " + std::to_string(n) +
                                 " expected, " + std::to_string(m) + " loaded");
        }
        for (const auto& [id, n] : y)
            if (!x.contains(id))
                out.emplace_back(std::string(what) + " " + id + ": none expected, " +
                                 std::to_string(n) + " loaded");
    };
    maps(a.itemCounts, b.itemCounts, "item");
    maps(a.unresolved, b.unresolved, "unresolved");
    if (a.graphs != b.graphs) out.emplace_back("graph sizes differ");
    if (a.mergedNodes != b.mergedNodes)
        out.emplace_back("merged nodes: " + std::to_string(a.mergedNodes) + " expected, " +
                         std::to_string(b.mergedNodes) + " loaded");
    if (a.chunks.size() != b.chunks.size()) {
        out.emplace_back("chunk counts differ");
        return out;
    }
    constexpr std::array<const char*, 4> kWhat{"terrain", "level", "district", "items"};
    const int cx = a.chunk > 0 ? (a.gridW + a.chunk - 1) / a.chunk : 1;
    for (std::size_t i = 0; i < a.chunks.size(); ++i)
        for (std::size_t k = 0; k < 4; ++k)
            if (a.chunks[i][k] != b.chunks[i][k]) {
                const int x = static_cast<int>(i) % cx * a.chunk;
                const int y = static_cast<int>(i) / cx * a.chunk;
                out.emplace_back(std::string(kWhat[k]) + " differs in chunk " + std::to_string(i) +
                                 " (grid " + std::to_string(x) + ".." +
                                 std::to_string(x + a.chunk - 1) + ", " + std::to_string(y) + ".." +
                                 std::to_string(y + a.chunk - 1) + ")");
            }
    return out;
}

} // namespace lc::world
