#include "core/catalog.hpp"

#include <nlohmann/json.hpp>

#include <algorithm>
#include <fstream>
#include <sstream>
#include <stdexcept>
#include <unordered_set>
#include <utility>

namespace lc {
namespace {

using nlohmann::json;

struct Invalid : std::runtime_error {
    using std::runtime_error::runtime_error;
};

[[noreturn]] void fail(const std::string& msg) {
    throw Invalid{msg};
}

template <typename T>
T get(const json& j, const char* key, const std::string& ctx) {
    if (!j.contains(key)) fail(ctx + ": missing '" + key + "'");
    try {
        return j.at(key).get<T>();
    } catch (const json::exception&) {
        fail(ctx + ": '" + key + "' has the wrong type");
    }
}

template <typename T>
T getOr(const json& j, const char* key, T fallback, const std::string& ctx) {
    return j.contains(key) ? get<T>(j, key, ctx) : fallback;
}

template <typename Def>
std::optional<int> findById(const std::vector<Def>& defs, std::string_view id) {
    const auto it = std::ranges::find(defs, id, &Def::id);
    if (it == defs.end()) return std::nullopt;
    return static_cast<int>(it - defs.begin());
}

template <typename Def>
void checkUnique(const std::vector<Def>& defs, const char* what) {
    std::unordered_set<std::string> seen;
    for (const auto& d : defs) {
        if (d.id.empty()) fail(std::string(what) + ": empty id");
        if (!seen.insert(d.id).second) fail(std::string(what) + " '" + d.id + "' is duplicated");
    }
}

// Maps a catalog sound name to the sfx file the engine plays for it.
std::string soundFile(const std::string& name) {
    if (name == "splash" || name == "paint") return "sfx/" + name + ".wav";
    return "sfx/place_" + name + ".wav";
}

std::vector<Amount> amounts(const json& obj, const std::string& ctx, bool terrain,
                            const Catalog& cat) {
    std::vector<Amount> out;
    if (!obj.is_object()) fail(ctx + ": expected an object");
    for (const auto& [key, value] : obj.items()) {
        const auto idx = terrain ? cat.findTerrain(key) : cat.findItem(key);
        if (!idx) fail(ctx + ": unknown " + (terrain ? "terrain" : "item") + " '" + key + "'");
        if (!value.is_number_integer() || value.get<int>() < 1)
            fail(ctx + ": amount for '" + key + "' must be a positive integer");
        out.push_back({*idx, value.get<int>()});
    }
    return out;
}

Catalog parse(const json& root) {
    Catalog cat;
    if (get<int>(root, "version", "catalog") != 1) fail("catalog: unsupported version");
    const auto& tile = root.at("tile");
    cat.tileW = get<int>(tile, "w", "tile");
    cat.tileH = get<int>(tile, "h", "tile");
    if (cat.tileW != 32 || cat.tileH != 16) fail("tile: the engine projection expects 32x16");
    const auto& map = root.at("map");
    cat.mapW = get<int>(map, "w", "map");
    cat.mapH = get<int>(map, "h", "map");
    if (cat.mapW < 1 || cat.mapH < 1 || cat.mapW > 256 || cat.mapH > 256)
        fail("map: size out of range");

    const auto& audio = root.at("audio");
    cat.audio.music = get<std::vector<std::string>>(audio, "music", "audio");
    cat.audio.ambience = get<std::vector<std::string>>(audio, "ambience", "audio");
    cat.audio.sfx = get<std::vector<std::string>>(audio, "sfx", "audio");
    const auto requireSfx = [&](const std::string& file, const std::string& ctx) {
        if (std::ranges::find(cat.audio.sfx, file) == cat.audio.sfx.end())
            fail(ctx + ": sound file '" + file + "' is not listed under audio.sfx");
    };

    int baseCount = 0;
    for (const auto& t : root.at("terrain")) {
        TerrainDef d;
        d.id = get<std::string>(t, "id", "terrain");
        const std::string ctx = "terrain '" + d.id + "'";
        d.name = get<std::string>(t, "name", ctx);
        d.base = getOr(t, "base", false, ctx);
        d.water = d.id == "water";
        d.variants = getOr(t, "variants", 1, ctx);
        d.fps = getOr(t, "fps", 0.0f, ctx);
        if (d.variants < 1) fail(ctx + ": variants must be >= 1");
        if (!d.base && getOr(t, "edges", 0, ctx) != 16)
            fail(ctx + ": overlay terrain must declare 16 edge masks");
        if (t.contains("sound")) {
            d.sound = soundFile(get<std::string>(t, "sound", ctx));
            requireSfx(d.sound, ctx);
        }
        baseCount += d.base ? 1 : 0;
        cat.terrain.push_back(std::move(d));
    }
    checkUnique(cat.terrain, "terrain");
    if (baseCount != 1) fail("terrain: exactly one base terrain is required");
    if (cat.terrain.size() > 255) fail("terrain: too many entries");
    cat.baseTerrain = static_cast<int>(
        std::ranges::find_if(cat.terrain, [](const TerrainDef& t) { return t.base; }) -
        cat.terrain.begin());
    const auto water = cat.findTerrain("water");
    if (!water) fail("terrain: a 'water' terrain is required");
    cat.waterTerrain = *water;
    if (cat.terrain[static_cast<std::size_t>(cat.waterTerrain)].base)
        fail("terrain: water cannot be the base terrain");

    for (const auto& c : root.at("categories")) {
        CategoryDef d;
        d.id = get<std::string>(c, "id", "category");
        d.name = get<std::string>(c, "name", "category '" + d.id + "'");
        cat.categories.push_back(std::move(d));
    }
    checkUnique(cat.categories, "category");

    for (const auto& it : root.at("items")) {
        ItemDef d;
        d.id = get<std::string>(it, "id", "item");
        const std::string ctx = "item '" + d.id + "'";
        d.name = get<std::string>(it, "name", ctx);
        const auto category = cat.findCategory(get<std::string>(it, "category", ctx));
        if (!category) fail(ctx + ": unknown category");
        d.category = *category;
        const auto fp = get<std::vector<int>>(it, "footprint", ctx);
        if (fp.size() != 2 || fp[0] < 1 || fp[1] < 1 || fp[0] > 8 || fp[1] > 8)
            fail(ctx + ": footprint must be [w, h] within 1..8");
        d.footprintW = fp[0];
        d.footprintH = fp[1];
        const auto layout = get<std::string>(it, "layout", ctx);
        if (layout == "variant")
            d.layout = Layout::Variant;
        else if (layout == "rotate")
            d.layout = Layout::Rotate;
        else if (layout == "connect")
            d.layout = Layout::Connect;
        else
            fail(ctx + ": unknown layout '" + layout + "'");
        if (d.layout == Layout::Connect) {
            if (d.footprintW != 1 || d.footprintH != 1) fail(ctx + ": connect items must be 1x1");
            d.count = 1;
        } else {
            d.count = get<int>(it, "count", ctx);
            if (d.count < 1 || d.count > 16) fail(ctx + ": count must be within 1..16");
            if (d.layout == Layout::Rotate && d.count != 1 && d.count != 2 && d.count != 4)
                fail(ctx + ": rotate count must be 1, 2 or 4");
        }
        const auto on = get<std::string>(it, "on", ctx);
        if (on == "land")
            d.on = Surface::Land;
        else if (on == "water")
            d.on = Surface::Water;
        else if (on == "any")
            d.on = Surface::Any;
        else
            fail(ctx + ": 'on' must be land, water or any");
        d.sound = soundFile(get<std::string>(it, "sound", ctx));
        requireSfx(d.sound, ctx);
        d.walkable = getOr(it, "walkable", false, ctx);
        d.glow = getOr(it, "glow", false, ctx);
        if (it.contains("smoke_at")) {
            const auto pts = get<std::vector<std::vector<int>>>(it, "smoke_at", ctx);
            if (std::cmp_not_equal(pts.size(), d.count))
                fail(ctx + ": smoke_at needs one [x, y] per variant");
            for (const auto& pt : pts) {
                if (pt.size() != 2) fail(ctx + ": smoke_at entries must be [x, y]");
                d.smokeAt.push_back({pt[0], pt[1]});
            }
        }
        d.fps = getOr(it, "fps", 0.0f, ctx);
        if (d.fps < 0) fail(ctx + ": fps must be >= 0");
        cat.items.push_back(std::move(d));
    }
    checkUnique(cat.items, "item");
    if (cat.items.size() > 60000) fail("items: too many entries");

    for (const auto& v : root.at("visitors")) {
        VisitorDef d;
        d.id = get<std::string>(v, "id", "visitor");
        const std::string ctx = "visitor '" + d.id + "'";
        d.name = get<std::string>(v, "name", ctx);
        const auto habitat = get<std::string>(v, "habitat", ctx);
        if (habitat == "land")
            d.habitat = Habitat::Land;
        else if (habitat == "water")
            d.habitat = Habitat::Water;
        else if (habitat == "air")
            d.habitat = Habitat::Air;
        else
            fail(ctx + ": unknown habitat");
        const auto time = get<std::string>(v, "time", ctx);
        if (time == "any")
            d.time = VisitTime::Any;
        else if (time == "day")
            d.time = VisitTime::Day;
        else if (time == "night")
            d.time = VisitTime::Night;
        else
            fail(ctx + ": unknown time");
        const auto& needs = v.at("needs");
        if (needs.contains("terrain")) d.terrainNeeds = amounts(needs["terrain"], ctx, true, cat);
        if (needs.contains("items")) d.itemNeeds = amounts(needs["items"], ctx, false, cat);
        if (needs.contains("any_items")) {
            d.anyItems = amounts(needs["any_items"], ctx, false, cat);
            d.anyTotal = get<int>(needs, "total", ctx);
            if (d.anyTotal < 1) fail(ctx + ": any_items total must be >= 1");
        }
        if (d.terrainNeeds.empty() && d.itemNeeds.empty() && d.anyItems.empty())
            fail(ctx + ": needs nothing, so it would always be present");
        d.max = get<int>(v, "max", ctx);
        d.glow = getOr(v, "glow", false, ctx);
        if (d.max < 1 || d.max > 32) fail(ctx + ": max must be within 1..32");
        if (v.contains("voice")) {
            d.voice = "sfx/" + get<std::string>(v, "voice", ctx) + ".wav";
            requireSfx(d.voice, ctx);
        }
        d.blurb = get<std::string>(v, "blurb", ctx);
        cat.visitors.push_back(std::move(d));
    }
    checkUnique(cat.visitors, "visitor");
    return cat;
}

} // namespace

std::optional<int> Catalog::findTerrain(std::string_view id) const {
    return findById(terrain, id);
}
std::optional<int> Catalog::findItem(std::string_view id) const {
    return findById(items, id);
}
std::optional<int> Catalog::findCategory(std::string_view id) const {
    return findById(categories, id);
}
std::optional<int> Catalog::findVisitor(std::string_view id) const {
    return findById(visitors, id);
}

std::expected<Catalog, std::string> parseCatalog(std::string_view text) {
    try {
        return parse(json::parse(text));
    } catch (const Invalid& e) {
        return std::unexpected(std::string(e.what()));
    } catch (const json::exception& e) {
        return std::unexpected(std::string("catalog: ") + e.what());
    }
}

std::expected<std::string, std::string> readTextFile(const std::filesystem::path& p) {
    std::ifstream in(p, std::ios::binary);
    if (!in) return std::unexpected("cannot open " + p.string());
    std::ostringstream ss;
    ss << in.rdbuf();
    if (in.bad()) return std::unexpected("cannot read " + p.string());
    return ss.str();
}

std::expected<Catalog, std::string> loadCatalog(const std::filesystem::path& file) {
    return readTextFile(file).and_then([](const std::string& s) { return parseCatalog(s); });
}

} // namespace lc
