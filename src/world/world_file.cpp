#include "world/world_file.hpp"

#include "core/catalog.hpp"
#include "core/world.hpp"
#include "world/json_util.hpp"
#include "world/layer_file.hpp"

#include <algorithm>
#include <unordered_set>

namespace lc::world {

using namespace detail;

int WorldFile::findRegion(std::string_view id) const {
    const auto it = std::ranges::find(regions, id, &RegionRef::id);
    return it == regions.end() ? -1 : static_cast<int>(it - regions.begin());
}

namespace {

RegionKind regionKind(const std::string& s, const std::string& ctx) {
    if (s == "home") return RegionKind::Home;
    if (s == "city") return RegionKind::City;
    if (s == "town") return RegionKind::Town;
    if (s == "stretch") return RegionKind::Stretch;
    if (s == "seam") return RegionKind::Seam;
    fail(ctx + ": kind '" + s + "' is not home, city, town, stretch or seam");
}

int regionIndex(const WorldFile& wf, const std::string& id, const std::string& ctx) {
    const int i = wf.findRegion(id);
    if (i < 0) fail(ctx + ": region '" + id + "' is not listed under regions");
    return i;
}

} // namespace

std::expected<WorldFile, std::string> parseWorldFile(std::string_view text, std::string_view file) {
    const std::string f(file);
    try {
        const json doc = parseDocument(text, f);
        requireVersion1(doc, f);
        WorldFile wf;
        const auto grid = asIntPair(field(doc, "grid", f), f + ": grid", 1, kMaxMapSide);
        wf.gridW = grid[0];
        wf.gridH = grid[1];
        if (static_cast<long long>(wf.gridW) * wf.gridH > kMaxMapTiles)
            fail(f + ": grid of " + std::to_string(wf.gridW) + " x " + std::to_string(wf.gridH) +
                 " is larger than the engine allows");
        wf.chunk = asInt(field(doc, "chunk", f), f + ": chunk", 1, 1 << 16);
        if (wf.chunk != kChunk)
            fail(f + ": chunk " + std::to_string(wf.chunk) + " differs from the engine's " +
                 std::to_string(kChunk));

        std::unordered_set<std::string> seen;
        const json& regions = asArray(field(doc, "regions", f), f + ": regions");
        for (std::size_t i = 0; i < regions.size(); ++i) {
            const std::string ctx = f + ": regions[" + std::to_string(i) + "]";
            const json& r = regions[i];
            RegionRef ref;
            ref.id = asString(field(r, "id", ctx), ctx + ": id");
            const std::string rc = ctx + " '" + ref.id + "'";
            if (ref.id.empty() || !seen.insert(ref.id).second)
                fail(rc + ": empty or duplicated region id");
            ref.set = asString(field(r, "set", rc), rc + ": set");
            ref.kind = regionKind(asString(field(r, "kind", rc), rc + ": kind"), rc);
            ref.time = asString(field(r, "time", rc), rc + ": time");
            ref.life = stringOr(r, "life", "", rc);
            wf.regions.push_back(std::move(ref));
        }

        const json& home = asObject(field(doc, "home", f), f + ": home");
        const std::string hc = f + ": home";
        const TilePos origin =
            asTile(field(home, "origin", hc), hc + ": origin", wf.gridW, wf.gridH);
        const auto size = asIntPair(field(home, "size", hc), hc + ": size", 1, kMaxMapSide);
        wf.home.rect = {origin.x, origin.y, origin.x + size[0], origin.y + size[1]};
        if (!TileRect{0, 0, wf.gridW, wf.gridH}.contains(wf.home.rect))
            fail(hc + ": the home rect leaves the grid");
        wf.home.level = asInt(field(home, "level", hc), hc + ": level", 0, kLevelMask);
        wf.home.region = regionIndex(wf, asString(field(home, "region", hc), hc + ": region"), hc);

        seen.clear();
        const json& layers = asArray(field(doc, "layers", f), f + ": layers");
        for (std::size_t i = 0; i < layers.size(); ++i) {
            const std::string ctx = f + ": layers[" + std::to_string(i) + "]";
            LayerRef ref;
            ref.id = asString(field(layers[i], "id", ctx), ctx + ": id");
            if (ref.id.empty() || !seen.insert(ref.id).second)
                fail(ctx + ": empty or duplicated layer id '" + ref.id + "'");
            ref.file = asString(field(layers[i], "file", ctx), ctx + ": file");
            ref.graph = stringOr(layers[i], "graph", "", ctx);
            if (ref.file.empty()) fail(ctx + ": empty file");
            wf.layers.push_back(std::move(ref));
        }
        if (wf.layers.size() > 0xFF) fail(f + ": more than 255 layers");

        if (has(doc, "markers")) {
            const json& markers = asArray(doc.at("markers"), f + ": markers");
            for (std::size_t i = 0; i < markers.size(); ++i) {
                const std::string ctx = f + ": markers[" + std::to_string(i) + "]";
                Marker m;
                m.region = regionIndex(
                    wf, asString(field(markers[i], "region", ctx), ctx + ": region"), ctx);
                m.at = asTile(field(markers[i], "at", ctx), ctx + ": at", wf.gridW, wf.gridH);
                m.icon = asString(field(markers[i], "icon", ctx), ctx + ": icon");
                wf.markers.push_back(std::move(m));
            }
        }
        return wf;
    } catch (const Invalid& e) {
        return std::unexpected(e.what());
    }
}

} // namespace lc::world
