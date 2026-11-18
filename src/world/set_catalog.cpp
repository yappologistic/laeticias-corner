#include "world/set_catalog.hpp"

#include "world/json_util.hpp"

#include <algorithm>
#include <array>
#include <unordered_set>

namespace lc::world {

using namespace detail;

namespace {

// Mirrors WATER_NAMES in tools/worldgen/worldgen/catalog.py so both sides agree on walkability.
constexpr std::array<std::string_view, 6> kWaterNames{"water", "sea",         "shallows",
                                                      "river", "river_tiber", "water_channel"};
// Largest footprint side a set may declare (landmarks are split into pieces of at most 8 x 8).
constexpr int kMaxSetFootprint = 64;
constexpr int kMaxRise = 15;

Layout layoutOf(const std::string& s, const std::string& ctx) {
    if (s == "rotate") return Layout::Rotate;
    if (s == "variant") return Layout::Variant;
    if (s == "connect") return Layout::Connect;
    fail(ctx + ": layout '" + s + "' is not rotate, variant or connect");
}

Surface surfaceOf(const std::string& s, const std::string& ctx) {
    if (s == "land") return Surface::Land;
    if (s == "water") return Surface::Water;
    // "any" as the home catalog writes it; "either" as world-tech §1.12 did.
    if (s == "any" || s == "either") return Surface::Any;
    fail(ctx + ": on '" + s + "' is not land, water or any");
}

void unique(std::unordered_set<std::string>& seen, const std::string& id, const std::string& ctx) {
    if (!seen.insert(id).second) fail(ctx + ": id '" + id + "' is duplicated in this catalog");
}

SetTerrain terrain(const json& t, const std::string& ctx, const std::string& set) {
    SetTerrain d;
    d.id = asString(field(t, "id", ctx), ctx + ": id");
    const std::string c = ctx + " '" + d.id + "'";
    requireSetId(d.id, set, c);
    d.name = asString(field(t, "name", c), c + ": name");
    d.base = boolOr(t, "base", false, c);
    d.under = stringOr(t, "under", "", c);
    if (d.base && !d.under.empty()) fail(c + ": a base terrain has no 'under'");
    if (!d.base && d.under.empty()) fail(c + ": an overlay must name the base it is drawn over");
    d.variants = intOr(t, "variants", 1, c, 1, 64);
    d.edges = intOr(t, "edges", 0, c, 0, 16);
    d.fps = floatOr(t, "fps", 0.0f, c);
    if (d.fps < 0) fail(c + ": fps must not be negative");
    if (has(t, "faces")) d.faces = asStrings(t.at("faces"), c + ": faces");
    if (d.faces.size() > 4) fail(c + ": at most 4 faces (the level byte's aux has two bits)");
    d.water = boolOr(t, "water", waterByName(d.id), c);
    d.paved = boolOr(t, "paved", false, c);
    return d;
}

SetItem item(const json& i, const std::string& ctx, const std::string& set) {
    SetItem d;
    d.id = asString(field(i, "id", ctx), ctx + ": id");
    const std::string c = ctx + " '" + d.id + "'";
    requireSetId(d.id, set, c);
    d.name = asString(field(i, "name", c), c + ": name");
    const auto fp = asIntPair(field(i, "footprint", c), c + ": footprint", 1, kMaxSetFootprint);
    d.footW = fp[0];
    d.footH = fp[1];
    d.layout = layoutOf(stringOr(i, "layout", "variant", c), c);
    d.count = intOr(i, "count", 1, c, 1, 255);
    // A connect layout always has the 16 neighbour masks; set catalogs write "count": 1 for it.
    if (d.layout == Layout::Connect) d.count = 16;
    if (d.layout == Layout::Rotate && d.count > 4) fail(c + ": a rotate layout has at most 4");
    d.on = surfaceOf(stringOr(i, "on", "land", c), c);
    d.walkable = boolOr(i, "walkable", false, c);
    d.landmark = boolOr(i, "landmark", false, c);
    if (has(i, "rotations")) {
        const json& r = asArray(i.at("rotations"), c + ": rotations");
        for (std::size_t k = 0; k < r.size(); ++k)
            d.rotations.push_back(asInt(r[k], c + ": rotations", 0, d.count - 1));
        if (d.rotations.empty()) fail(c + ": rotations is empty");
    } else if (d.landmark || d.layout != Layout::Rotate) {
        d.rotations = {0};
    } else {
        for (int k = 0; k < d.count; ++k) d.rotations.push_back(k);
    }
    d.scale = floatOr(i, "scale", 1.0f, c);
    if (d.scale <= 0) fail(c + ": scale must be positive");
    d.height = intOr(i, "height", 0, c, 0, 4096);
    d.layers = has(i, "layers") ? asStrings(i.at("layers"), c + ": layers")
                                : std::vector<std::string>{"base", "shadow"};
    if (has(i, "states")) d.states = asStrings(i.at("states"), c + ": states");
    for (const auto& l : d.layers)
        if (l != "base" && l != "shadow" && l != "glow") fail(c + ": unknown layer '" + l + "'");
    d.occluder = boolOr(i, "occluder", false, c);
    d.card = stringOr(i, "card", "", c);
    d.rise = intOr(i, "rise", 0, c, 0, kMaxRise);
    if (has(i, "axis")) {
        const std::string a = asString(i.at("axis"), c + ": axis");
        if (a != "x" && a != "y") fail(c + ": axis must be 'x' or 'y'");
        d.axis = a[0];
    }
    if (d.rise > 0 && d.axis == 0) fail(c + ": a stair or ramp (rise > 0) needs an axis");
    d.fps = floatOr(i, "fps", 0.0f, c);
    if (d.fps < 0) fail(c + ": fps must not be negative");
    if (has(i, "slots")) {
        std::unordered_set<std::string> ids;
        const json& slots = asArray(i.at("slots"), c + ": slots");
        for (std::size_t s = 0; s < slots.size(); ++s) {
            const std::string sc = c + ": slots[" + std::to_string(s) + "]";
            SlotBehaviour b;
            b.id = asString(field(slots[s], "id", sc), sc + ": id");
            if (b.id.empty() || !ids.insert(b.id).second)
                fail(sc + ": empty or duplicated slot id '" + b.id + "'");
            b.kind = asString(field(slots[s], "kind", sc), sc + ": kind");
            b.cap = intOr(slots[s], "cap", 1, sc, 1, 255);
            d.slots.push_back(std::move(b));
        }
    }
    if (has(i, "emitters"))
        for (const auto& [name, fx] : asObject(i.at("emitters"), c + ": emitters").items())
            d.emitters.emplace_back(name, asString(fx, c + ": emitters: " + name));
    return d;
}

SetActor actor(const json& a, const std::string& ctx, const std::string& set) {
    SetActor d;
    d.id = asString(field(a, "id", ctx), ctx + ": id");
    const std::string c = ctx + " '" + d.id + "'";
    requireSetId(d.id, set, c);
    d.name = asString(field(a, "name", c), c + ": name");
    d.sprite = asString(field(a, "sprite", c), c + ": sprite");
    d.variants = intOr(a, "variants", 1, c, 1, 64);
    for (const auto& [pose, spec] : asObject(field(a, "anims", c), c + ": anims").items()) {
        const float fps = asFloat(field(spec, "fps", c + ": anims: " + pose), c + ": fps");
        if (fps <= 0) fail(c + ": anims: " + pose + ": fps must be positive");
        d.anims.emplace_back(pose, fps);
    }
    if (d.anims.empty()) fail(c + ": an actor needs at least one animation");
    if (has(a, "size")) {
        const auto s = asIntPair(a.at("size"), c + ": size", 1, 16);
        d.sizeW = s[0];
        d.sizeH = s[1];
    }
    return d;
}

SetGoods goods(const json& g, const std::string& ctx, const std::string& set) {
    SetGoods d;
    d.id = asString(field(g, "id", ctx), ctx + ": id");
    const std::string c = ctx + " '" + d.id + "'";
    requireSetId(d.id, set, c);
    d.name = asString(field(g, "name", c), c + ": name");
    d.sprite = stringOr(g, "sprite", "goods/" + d.id, c);
    d.stack = intOr(g, "stack", 1, c, 1, 3);
    return d;
}

} // namespace

bool waterByName(std::string_view terrainId) {
    const auto dot = terrainId.find('.');
    const std::string_view name =
        dot == std::string_view::npos ? terrainId : terrainId.substr(dot + 1);
    return std::ranges::find(kWaterNames, name) != kWaterNames.end();
}

std::expected<SetCatalog, std::string> parseSetCatalog(std::string_view text, std::string_view file,
                                                       std::string_view set) {
    const std::string f(file);
    const std::string s(set);
    try {
        const json doc = parseDocument(text, f);
        requireVersion1(doc, f);
        SetCatalog cat;
        cat.file = f;
        cat.set = asString(field(doc, "set", f), f + ": set");
        if (cat.set != set) fail(f + ": set '" + cat.set + "' differs from '" + s + "'");
        std::unordered_set<std::string> ids;
        // Actor kinds draw from their own key families (critter/, walker/, figure/, ...), so an
        // actor may share its id with an item (rome.castor: the statue and the apparition).
        std::unordered_set<std::string> actorIds;
        const auto each = [&](const char* key, auto&& parse) {
            if (!has(doc, key)) return;
            const json& list = asArray(doc.at(key), f + ": " + key);
            for (std::size_t i = 0; i < list.size(); ++i)
                parse(list[i], f + ": " + key + "[" + std::to_string(i) + "]");
        };
        each("terrain", [&](const json& j, const std::string& c) {
            cat.terrain.push_back(terrain(j, c, s));
            unique(ids, cat.terrain.back().id, c);
        });
        each("items", [&](const json& j, const std::string& c) {
            cat.items.push_back(item(j, c, s));
            unique(ids, cat.items.back().id, c);
        });
        each("actors", [&](const json& j, const std::string& c) {
            cat.actors.push_back(actor(j, c, s));
            unique(actorIds, cat.actors.back().id, c);
        });
        each("goods", [&](const json& j, const std::string& c) {
            cat.goods.push_back(goods(j, c, s));
            unique(ids, cat.goods.back().id, c);
        });
        for (const auto& t : cat.terrain) {
            if (t.base) continue;
            const auto u = std::ranges::find(cat.terrain, t.under, &SetTerrain::id);
            if (u != cat.terrain.end() && !u->base)
                fail(f + ": terrain '" + t.id + "': its under '" + t.under + "' is not a base");
        }
        if (has(doc, "art")) {
            const json& art = asObject(doc.at("art"), f + ": art");
            if (has(art, "edges")) cat.art.edges = asStrings(art.at("edges"), f + ": art: edges");
            if (has(art, "backdrops"))
                cat.art.backdrops = asStrings(art.at("backdrops"), f + ": art: backdrops");
            if (has(art, "fx")) cat.art.fx = asStrings(art.at("fx"), f + ": art: fx");
        }
        return cat;
    } catch (const Invalid& e) {
        return std::unexpected(e.what());
    }
}

} // namespace lc::world
