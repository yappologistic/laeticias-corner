#include "core/catalog.hpp"

#include <nlohmann/json.hpp>

#include <algorithm>
#include <array>
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

// Longest wish text and speech line the interface lays out (docs/design/living-corner.md §9).
constexpr std::size_t kMaxWishText = 80;
constexpr std::size_t kMaxLine = 52;
constexpr std::array<std::string_view, 4> kPhaseIds{"day", "dusk", "night", "dawn"};

template <typename T>
T get(const json& j, const char* key, const std::string& ctx) {
    if (!j.is_object() || !j.contains(key)) fail(ctx + ": missing '" + key + "'");
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

// Takes a plain C string for the context: a temporary std::string argument would make GCC warn
// that the returned reference might dangle.
const json& section(const json& j, const char* key, const char* ctx) {
    if (!j.is_object() || !j.contains(key)) fail(std::string(ctx) + ": missing '" + key + "'");
    return j.at(key);
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

class Parser {
public:
    explicit Parser(Catalog& cat) : cat_(cat) {}

    void requireSfx(const std::string& file, const std::string& ctx) const {
        if (std::ranges::find(cat_.audio.sfx, file) == cat_.audio.sfx.end())
            fail(ctx + ": sound file '" + file + "' is not listed under audio.sfx");
    }

    int item(const std::string& id, const std::string& ctx) const {
        const auto i = cat_.findItem(id);
        if (!i) fail(ctx + ": unknown item '" + id + "'");
        return *i;
    }
    int terrain(const std::string& id, const std::string& ctx) const {
        const auto t = cat_.findTerrain(id);
        if (!t) fail(ctx + ": unknown terrain '" + id + "'");
        return *t;
    }
    int visitor(const std::string& id, const std::string& ctx) const {
        const auto v = cat_.findVisitor(id);
        if (!v) fail(ctx + ": unknown visitor '" + id + "'");
        return *v;
    }

    std::uint8_t seasonMask(const json& list, const std::string& ctx) const {
        if (!list.is_array() || list.empty()) fail(ctx + ": expected a list of seasons");
        std::uint8_t mask = 0;
        for (const auto& s : list) {
            const auto i = s.is_string() ? cat_.findSeason(s.get<std::string>()) : std::nullopt;
            if (!i) fail(ctx + ": unknown season " + s.dump());
            mask |= static_cast<std::uint8_t>(1u << *i);
        }
        return mask;
    }

    void phases(const json& list, const std::string& ctx) const {
        if (!list.is_array() || list.empty()) fail(ctx + ": expected a list of phases");
        for (const auto& p : list)
            if (!p.is_string() ||
                std::ranges::find(kPhaseIds, p.get<std::string>()) == kPhaseIds.end())
                fail(ctx + ": unknown phase " + p.dump());
    }

    // Inclusive [x0, y0, x1, y1] inside the map, as a half-open rectangle.
    TileRect rect(const json& j, const std::string& ctx) const {
        if (!j.is_array() || j.size() != 4) fail(ctx + ": a rect is [x0, y0, x1, y1]");
        std::array<int, 4> v{};
        for (std::size_t i = 0; i < 4; ++i) {
            if (!j[i].is_number_integer()) fail(ctx + ": rect values must be integers");
            v[i] = j[i].get<int>();
        }
        const TileRect r{v[0], v[1], v[2] + 1, v[3] + 1};
        if (r.empty() || !TileRect{0, 0, cat_.mapW, cat_.mapH}.contains(r))
            fail(ctx + ": rect outside the map or empty");
        return r;
    }

    std::vector<TerrainFill> fills(const json& list, const std::string& ctx) const {
        std::vector<TerrainFill> out;
        if (!list.is_array()) fail(ctx + ": terrain must be a list");
        for (const auto& f : list)
            out.push_back({terrain(get<std::string>(f, "id", ctx), ctx),
                           rect(section(f, "rect", ctx.c_str()), ctx)});
        return out;
    }

    std::vector<Placement> placements(const json& list, const std::string& ctx) const {
        std::vector<Placement> out;
        if (!list.is_array()) fail(ctx + ": items must be a list");
        for (const auto& p : list) {
            const int type = item(get<std::string>(p, "id", ctx), ctx);
            const int v = getOr(p, "v", 0, ctx);
            const auto& def = cat_.items[static_cast<std::size_t>(type)];
            if (v < 0 || v >= def.count) fail(ctx + ": variant out of range for " + def.id);
            out.push_back({type, {get<int>(p, "x", ctx), get<int>(p, "y", ctx)}, v});
        }
        return out;
    }

    PieceSet pieces(const json& j, const std::string& ctx, bool withFrames) const {
        PieceSet s;
        for (const auto& id : get<std::vector<std::string>>(j, "terrain", ctx))
            s.terrain.push_back(terrain(id, ctx));
        for (const auto& id : get<std::vector<std::string>>(j, "items", ctx))
            s.items.push_back(item(id, ctx));
        if (withFrames)
            for (const auto& id : get<std::vector<std::string>>(j, "frames", ctx)) {
                const auto f = cat_.findFrame(id);
                if (!f) fail(ctx + ": unknown frame '" + id + "'");
                s.frames.push_back(*f);
            }
        return s;
    }

    std::vector<Amount> amounts(const json& obj, const std::string& ctx, bool isTerrain) const {
        std::vector<Amount> out;
        if (!obj.is_object()) fail(ctx + ": expected an object");
        for (const auto& [key, value] : obj.items()) {
            const int idx = isTerrain ? terrain(key, ctx) : item(key, ctx);
            if (!value.is_number_integer() || value.get<int>() < 1)
                fail(ctx + ": amount for '" + key + "' must be a positive integer");
            out.push_back({idx, value.get<int>()});
        }
        return out;
    }

    void terrains(const json& root) {
        int baseCount = 0;
        for (const auto& t : section(root, "terrain", "catalog")) {
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
            cat_.terrain.push_back(std::move(d));
        }
        checkUnique(cat_.terrain, "terrain");
        if (baseCount != 1) fail("terrain: exactly one base terrain is required");
        if (cat_.terrain.size() > 255) fail("terrain: too many entries");
        cat_.baseTerrain = static_cast<int>(
            std::ranges::find_if(cat_.terrain, [](const TerrainDef& t) { return t.base; }) -
            cat_.terrain.begin());
        const auto water = cat_.findTerrain("water");
        if (!water) fail("terrain: a 'water' terrain is required");
        cat_.waterTerrain = *water;
        if (cat_.terrain[static_cast<std::size_t>(cat_.waterTerrain)].base)
            fail("terrain: water cannot be the base terrain");
        cat_.conditions.setBaseTerrain(cat_.baseTerrain);
    }

    void slots(const json& list, const ItemDef& d, const std::string& ctx) const {
        if (!list.is_array()) fail(ctx + ": slots must be a list");
        for (const auto& s : list) {
            const std::string sctx = ctx + " slot";
            (void)get<std::string>(s, "id", sctx);
            (void)get<std::string>(s, "kind", sctx);
            const auto where = get<std::string>(s, "where", sctx);
            if (where != "on" && where != "beside" && where != "tile")
                fail(sctx + ": 'where' must be on, beside or tile");
            if (getOr(s, "cap", 1, sctx) < 1) fail(sctx + ": cap must be at least 1");
            if (where == "tile") {
                const json& tiles = section(s, "tiles", sctx.c_str());
                if (!tiles.is_object() || tiles.empty()) fail(sctx + ": tiles per rotation");
                for (const auto& [k, v] : tiles.items()) {
                    if (k.size() < 2 || k[0] != 'r' || std::stoi(k.substr(1)) >= d.count)
                        fail(sctx + ": tiles key '" + k + "' is not a variant of the item");
                    (void)get<std::vector<std::vector<int>>>(tiles, k.c_str(), sctx);
                }
            }
            if (s.contains("states")) (void)get<std::vector<std::string>>(s, "states", sctx);
        }
    }

    void items(const json& root) {
        for (const auto& it : section(root, "items", "catalog")) {
            ItemDef d;
            d.id = get<std::string>(it, "id", "item");
            const std::string ctx = "item '" + d.id + "'";
            d.name = get<std::string>(it, "name", ctx);
            const auto category = cat_.findCategory(get<std::string>(it, "category", ctx));
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
                if (d.footprintW != 1 || d.footprintH != 1)
                    fail(ctx + ": connect items must be 1x1");
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
            for (const auto& tag : getOr(it, "tags", std::vector<std::string>{}, ctx)) {
                auto t = cat_.findTag(tag);
                if (!t) {
                    cat_.tags.push_back(tag);
                    t = static_cast<int>(cat_.tags.size()) - 1;
                }
                d.tags.push_back(*t);
            }
            if (it.contains("perch")) {
                const json& p = it["perch"];
                const bool ok =
                    p.is_number_integer() ||
                    (p.is_array() && std::cmp_equal(p.size(), d.count) &&
                     std::ranges::all_of(p, [](const json& v) { return v.is_number_integer(); }));
                if (!ok) fail(ctx + ": perch is a pixel height, or one per variant");
            }
            if (it.contains("season_looks"))
                d.seasonLooks = seasonMask(it["season_looks"], ctx + " season_looks");
            if (it.contains("growth")) {
                const json& g = it["growth"];
                d.growth.stages = get<int>(g, "stages", ctx);
                d.growth.seconds = get<float>(g, "seconds", ctx);
                d.growth.harvest = getOr(g, "harvest", false, ctx);
                if (d.growth.stages < 2 || d.growth.stages > 8 || d.growth.seconds <= 0)
                    fail(ctx + ": growth needs 2..8 stages and positive seconds");
            }
            if (it.contains("sheds")) {
                const auto s = get<std::string>(it, "sheds", ctx);
                if (s == "leaves")
                    d.sheds = Shed::Leaves;
                else if (s == "blossom")
                    d.sheds = Shed::Blossom;
                else
                    fail(ctx + ": sheds is 'leaves' or 'blossom'");
            }
            if (it.contains("click_sound")) {
                d.clickSound = "sfx/" + get<std::string>(it, "click_sound", ctx) + ".wav";
                requireSfx(d.clickSound, ctx);
            }
            if (it.contains("slots")) slots(it["slots"], d, ctx);
            cat_.items.push_back(std::move(d));
        }
        checkUnique(cat_.items, "item");
        if (cat_.items.size() > 60000) fail("items: too many entries");
    }

    // Activity data drives visitor behaviour in a later engine round; validated now so the
    // content stays correct.
    void activities(const json& list, const std::string& ctx) const {
        if (!list.is_array() || list.empty()) fail(ctx + ": activities must be a non-empty list");
        std::vector<std::string> ids;
        for (const auto& a : list) {
            const auto id = get<std::string>(a, "id", ctx + " activity");
            const std::string actx = ctx + " activity '" + id + "'";
            ids.push_back(id);
            if (a.contains("anim")) (void)get<std::string>(a, "anim", actx);
            if (a.contains("at")) {
                const json& at = a["at"];
                if (!at.is_object() || at.size() != 1) fail(actx + ": 'at' has one key");
                const auto& key = at.begin().key();
                if (key == "item")
                    (void)item(get<std::string>(at, "item", actx), actx);
                else if (key == "items")
                    for (const auto& i : get<std::vector<std::string>>(at, "items", actx))
                        (void)item(i, actx);
                else if (key == "tag") {
                    if (!cat_.findTag(get<std::string>(at, "tag", actx)))
                        fail(actx + ": unknown tag");
                } else if (key != "here" && key != "bank" && key != "shore" && key != "resident")
                    fail(actx + ": unknown target '" + key + "'");
            }
            if (a.contains("spot")) {
                const auto spot = get<std::string>(a, "spot", actx);
                if (spot != "on" && spot != "beside") fail(actx + ": spot is on or beside");
            }
            if (a.contains("time")) phases(a["time"], actx);
            if (a.contains("seasons")) (void)seasonMask(a["seasons"], actx);
            for (const char* range : {"dur", "every"}) {
                if (!a.contains(range)) continue;
                const auto r = get<std::vector<float>>(a, range, actx);
                if (r.size() != 2 || r[0] < 0 || r[1] < r[0])
                    fail(actx + ": '" + range + "' is [min, max]");
            }
            if (a.contains("every") != a.contains("call_anim"))
                fail(actx + ": 'every' and 'call_anim' go together");
            if (getOr(a, "weight", 1.0f, actx) < 0) fail(actx + ": weight must be >= 0");
            if (std::ranges::count(ids, id) > 1) fail(actx + ": duplicated");
        }
    }

    void visitors(const json& root) {
        for (const auto& v : section(root, "visitors", "catalog")) {
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
            else if (habitat == "shore")
                d.habitat = Habitat::Shore;
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
            const auto& needs = section(v, "needs", ctx.c_str());
            if (needs.contains("terrain")) d.terrainNeeds = amounts(needs["terrain"], ctx, true);
            if (needs.contains("items")) d.itemNeeds = amounts(needs["items"], ctx, false);
            if (needs.contains("any_items")) {
                d.anyItems = amounts(needs["any_items"], ctx, false);
                d.anyTotal = get<int>(needs, "total", ctx);
                if (d.anyTotal < 1) fail(ctx + ": any_items total must be >= 1");
            }
            d.rare = getOr(v, "rare", false, ctx);
            const bool needsNothing =
                d.terrainNeeds.empty() && d.itemNeeds.empty() && d.anyItems.empty();
            if (d.rare && (!needsNothing || !v.contains("recipe")))
                fail(ctx + ": a rare visitor needs nothing but its recipe");
            if (!d.rare && needsNothing)
                fail(ctx + ": needs nothing, so it would always be present");
            d.max = get<int>(v, "max", ctx);
            d.glow = getOr(v, "glow", false, ctx);
            if (d.max < 1 || d.max > 32) fail(ctx + ": max must be within 1..32");
            if (d.rare && d.max != 1) fail(ctx + ": a rare visitor comes alone (max 1)");
            if (v.contains("voice")) {
                d.voice = "sfx/" + get<std::string>(v, "voice", ctx) + ".wav";
                requireSfx(d.voice, ctx);
            }
            d.blurb = get<std::string>(v, "blurb", ctx);
            d.hint = get<std::string>(v, "hint", ctx);
            if (v.contains("seasons")) d.seasons = seasonMask(v["seasons"], ctx);
            d.clue = getOr(v, "clue", std::string{}, ctx);
            if (d.rare && d.clue.empty()) fail(ctx + ": a rare visitor needs a clue");
            d.underwater = getOr(v, "underwater", false, ctx);
            for (const auto& n : d.itemNeeds) d.attractItems.push_back(n.index);
            for (const auto& n : d.anyItems) d.attractItems.push_back(n.index);
            for (const auto& n : d.terrainNeeds) d.attractTerrain.push_back(n.index);
            cat_.visitors.push_back(std::move(d));
        }
        checkUnique(cat_.visitors, "visitor");
        if (cat_.visitors.size() > 255) fail("visitors: too many entries");
        // Behaviour fields refer to other visitors' data only through items and tags, so they
        // can be checked once every visitor is known.
        std::size_t i = 0;
        for (const auto& v : section(root, "visitors", "catalog")) {
            const VisitorDef& d = cat_.visitors[i++];
            const std::string ctx = "visitor '" + d.id + "'";
            if (v.contains("activities")) activities(v["activities"], ctx);
            if (v.contains("cycle")) {
                const auto cycle = get<std::vector<std::string>>(v, "cycle", ctx);
                for (const auto& id : cycle) {
                    const bool found = v.contains("activities") &&
                                       std::ranges::any_of(v["activities"], [&](const json& a) {
                                           return a.value("id", std::string{}) == id;
                                       });
                    if (!found) fail(ctx + ": cycle names unknown activity '" + id + "'");
                }
            }
            if (v.contains("home")) (void)item(get<std::string>(v, "home", ctx), ctx);
            if (v.contains("startle")) {
                const json& s = v["startle"];
                if (get<float>(s, "radius", ctx + " startle") <= 0)
                    fail(ctx + ": startle radius must be positive");
                if (s.contains("only_from"))
                    (void)get<std::vector<std::string>>(s, "only_from", ctx + " startle");
            }
            if (v.contains("pet") && v["pet"].contains("sound"))
                requireSfx("sfx/" + get<std::string>(v["pet"], "sound", ctx) + ".wav", ctx);
            for (const char* flag : {"line", "hide_in_rain"}) (void)getOr(v, flag, false, ctx);
        }
    }

    void seasons(const json& root) {
        for (const auto& s : section(root, "seasons", "catalog")) {
            SeasonDef d;
            d.id = get<std::string>(s, "id", "season");
            const std::string ctx = "season '" + d.id + "'";
            d.name = get<std::string>(s, "name", ctx);
            d.days = get<int>(s, "days", ctx);
            if (d.days < 1) fail(ctx + ": days must be at least 1");
            const auto mul = get<std::vector<float>>(section(s, "grade", ctx.c_str()), "mul", ctx);
            if (mul.size() != 3 || std::ranges::any_of(mul, [](float m) { return m <= 0; }))
                fail(ctx + ": grade.mul is three positive numbers");
            d.grade = {mul[0], mul[1], mul[2]};
            const json& amb = section(s, "ambience", ctx.c_str());
            d.ambienceDay = get<std::string>(amb, "day", ctx);
            d.ambienceNight = get<std::string>(amb, "night", ctx);
            for (const auto* f : {&d.ambienceDay, &d.ambienceNight})
                if (std::ranges::find(cat_.audio.ambience, *f) == cat_.audio.ambience.end())
                    fail(ctx + ": ambience '" + *f + "' is not listed under audio.ambience");
            const json& fx = section(s, "fx", ctx.c_str());
            d.petals = get<float>(fx, "petal", ctx);
            d.leaves = get<float>(fx, "leaf", ctx);
            if (s.contains("rain_as")) {
                if (get<std::string>(s, "rain_as", ctx) != "snow")
                    fail(ctx + ": rain_as can only be 'snow'");
                d.snow = true;
            }
            d.line = get<std::string>(s, "line", ctx);
            cat_.seasonDays.push_back(d.days);
            cat_.seasons.push_back(std::move(d));
        }
        checkUnique(cat_.seasons, "season");
        if (cat_.seasons.empty() || cat_.seasons.size() > 8) fail("seasons: 1 to 8 are needed");
    }

    void land(const json& root) {
        const json& land = section(root, "land", "catalog");
        if (get<std::string>(land, "measure", "land") != "pages")
            fail("land: the only measure is 'pages'");
        if (land.contains("gate")) {
            const auto g = get<std::vector<int>>(land, "gate", "land");
            if (g.size() != 2 || g[0] < 0 || g[1] < 0 || g[0] >= cat_.mapW || g[1] >= cat_.mapH)
                fail("land: gate is an [x, y] tile on the map");
            cat_.gate = TilePos{g[0], g[1]};
        }
        std::vector<int> owner(
            static_cast<std::size_t>(cat_.mapW) * static_cast<std::size_t>(cat_.mapH), -1);
        for (const auto& s : section(land, "stages", "land")) {
            StageDef d;
            d.id = get<std::string>(s, "id", "stage");
            const std::string ctx = "stage '" + d.id + "'";
            d.name = get<std::string>(s, "name", ctx);
            d.pages = get<int>(s, "pages", ctx);
            d.line = getOr(s, "line", std::string{}, ctx);
            const int index = static_cast<int>(cat_.stages.size());
            if (index == 0 && d.pages != 0) fail(ctx + ": the first stage opens at 0 pages");
            if (index > 0 && d.pages < cat_.stages.back().pages)
                fail(ctx + ": stages must open in order of pages");
            for (const auto& r : section(s, "rects", ctx.c_str())) {
                const TileRect t = rect(r, ctx);
                d.rects.push_back(t);
                for (int y = t.y0; y < t.y1; ++y)
                    for (int x = t.x0; x < t.x1; ++x) {
                        int& o = owner[static_cast<std::size_t>(y * cat_.mapW + x)];
                        if (o >= 0) fail(ctx + ": overlaps another stage");
                        o = index;
                    }
            }
            const auto inside = [&](TileRect r) {
                for (int y = r.y0; y < r.y1; ++y)
                    for (int x = r.x0; x < r.x1; ++x)
                        if (owner[static_cast<std::size_t>(y * cat_.mapW + x)] != index)
                            return false;
                return true;
            };
            if (s.contains("reveal")) {
                const json& rv = s["reveal"];
                if (rv.contains("terrain")) d.terrain = fills(rv["terrain"], ctx + " reveal");
                if (rv.contains("items")) d.items = placements(rv["items"], ctx + " reveal");
            }
            for (const auto& f : d.terrain)
                if (!inside(f.rect)) fail(ctx + ": revealed terrain outside the stage");
            for (const auto& p : d.items)
                if (!inside({p.pos.x, p.pos.y, p.pos.x + 1, p.pos.y + 1}))
                    fail(ctx + ": revealed item outside the stage");
            cat_.stages.push_back(std::move(d));
        }
        checkUnique(cat_.stages, "stage");
        if (cat_.stages.empty() || cat_.stages.size() > 16) fail("land: 1 to 16 stages");
        if (std::ranges::find(owner, -1) != owner.end())
            fail("land: the stages must cover the whole map");
    }

    void starter(const json& root) {
        const json& s = section(root, "starter", "catalog");
        cat_.starter.terrain = fills(section(s, "terrain", "starter"), "starter");
        cat_.starter.items = placements(section(s, "items", "starter"), "starter");
        const auto r = get<std::vector<int>>(s, "resident", "starter");
        if (r.size() != 2 || r[0] < 0 || r[1] < 0 || r[0] >= cat_.mapW || r[1] >= cat_.mapH)
            fail("starter: resident is an [x, y] tile on the map");
        cat_.starter.resident = {r[0], r[1]};
        // A new world opens on the first stage only, so the starter scene must lie inside it.
        const auto first = [&](TilePos p) {
            return std::ranges::any_of(cat_.stages.front().rects,
                                       [&](const TileRect& t) { return t.contains(p); });
        };
        for (const auto& f : cat_.starter.terrain)
            if (!first({f.rect.x0, f.rect.y0}) || !first({f.rect.x1 - 1, f.rect.y1 - 1}))
                fail("starter: terrain outside the first stage");
        for (const auto& p : cat_.starter.items)
            if (!first(p.pos)) fail("starter: item outside the first stage");
        if (!first(cat_.starter.resident)) fail("starter: resident outside the first stage");
    }

    void frames(const json& root) {
        for (const auto& f : section(root, "frames", "catalog")) {
            FrameDef d;
            d.id = get<std::string>(f, "id", "frame");
            d.name = get<std::string>(f, "name", "frame '" + d.id + "'");
            cat_.frames.push_back(std::move(d));
        }
        checkUnique(cat_.frames, "frame");
    }

    void resident(const json& root) {
        const json& r = section(root, "resident", "catalog");
        ResidentDef& d = cat_.resident;
        d.id = get<std::string>(r, "id", "resident");
        const std::string ctx = "resident '" + d.id + "'";
        d.name = get<std::string>(r, "name", ctx);
        d.blurb = get<std::string>(r, "blurb", ctx);
        for (const auto& v : get<std::vector<std::string>>(r, "voice", ctx)) {
            d.voice.push_back("sfx/" + v + ".wav");
            requireSfx(d.voice.back(), ctx);
        }
        const json& lines = section(r, "lines", ctx.c_str());
        if (!lines.is_object() || lines.empty()) fail(ctx + ": lines by context");
        for (const auto& [key, list] : lines.items()) {
            if (!list.is_array() || list.empty()) fail(ctx + ": lines '" + key + "' is empty");
            for (const auto& l : list)
                if (!l.is_string() || l.get<std::string>().size() > kMaxLine)
                    fail(ctx + ": line in '" + key + "' is not text of at most 52 characters");
        }
        // Her day as actor data is read by the actor system (a later engine round).
        for (const char* key : {"schedule", "interrupts"})
            if (!section(r, key, ctx.c_str()).is_array())
                fail(ctx + ": '" + key + "' must be a list");
        if (!section(r, "routines", ctx.c_str()).is_object())
            fail(ctx + ": 'routines' is an object");
        if (cat_.findVisitor(d.id)) fail(ctx + ": shares an id with a visitor");
    }

    void wishes(const json& root, std::span<const std::string> nookIds) {
        for (const auto& w : section(root, "wishes", "catalog")) {
            WishDef d;
            d.id = get<std::string>(w, "id", "wish");
            const std::string ctx = "wish '" + d.id + "'";
            const auto giver = get<std::string>(w, "giver", ctx);
            d.giver = giver == cat_.resident.id ? -1 : visitor(giver, ctx);
            for (const auto& a : getOr(w, "after", std::vector<std::string>{}, ctx)) {
                const auto i = cat_.findWish(a);
                if (!i) fail(ctx + ": 'after' must name an earlier wish ('" + a + "')");
                d.after.push_back(*i);
            }
            if (w.contains("requires"))
                d.gate = cat_.conditions.compile(w["requires"], cat_, nookIds, ctx);
            d.text = get<std::string>(w, "text", ctx);
            if (d.text.empty() || d.text.size() > kMaxWishText)
                fail(ctx + ": text must be 1 to 80 characters");
            d.goal = cat_.conditions.compile(section(w, "goal", ctx.c_str()), cat_, nookIds, ctx);
            d.progress = getOr(w, "progress", std::string{}, ctx);
            if (!d.progress.empty() && cat_.conditions.node(d.goal).kind != CondKind::Count)
                fail(ctx + ": a progress label needs a top-level count goal");
            d.thanks = get<std::string>(w, "thanks", ctx);
            const json& rw = section(w, "reward", ctx.c_str());
            for (const auto& id : getOr(rw, "unlock", std::vector<std::string>{}, ctx)) {
                if (const auto i = cat_.findItem(id))
                    d.reward.items.push_back(*i);
                else
                    d.reward.terrain.push_back(terrain(id, ctx));
            }
            if (rw.contains("frame")) {
                const auto f = cat_.findFrame(get<std::string>(rw, "frame", ctx));
                if (!f) fail(ctx + ": unknown frame");
                d.reward.frame = *f;
            }
            if (rw.contains("clue")) {
                d.reward.clue = visitor(get<std::string>(rw, "clue", ctx), ctx);
                if (!cat_.visitors[static_cast<std::size_t>(d.reward.clue)].rare)
                    fail(ctx + ": a clue is for a rare visitor");
            }
            if (d.reward.items.empty() && d.reward.terrain.empty() && d.reward.frame < 0 &&
                d.reward.clue < 0)
                fail(ctx + ": a wish needs a reward");
            cat_.conditions.needed(d.goal, d.needed);
            cat_.wishes.push_back(std::move(d));
        }
        checkUnique(cat_.wishes, "wish");
    }

    void nooks(const json& root, std::span<const std::string> nookIds) {
        std::size_t i = 0;
        for (const auto& n : section(root, "nooks", "catalog")) {
            NookDef d;
            d.id = nookIds[i++];
            const std::string ctx = "nook '" + d.id + "'";
            d.name = get<std::string>(n, "name", ctx);
            d.condition =
                cat_.conditions.compile(section(n, "condition", ctx.c_str()), cat_, nookIds, ctx);
            d.near = cat_.conditions.nookNear(d.condition);
            if (d.near < 0) fail(ctx + ": needs exactly one 'near', at the top or in a top 'all'");
            d.teaser = get<std::string>(n, "teaser", ctx);
            d.blurb = get<std::string>(n, "blurb", ctx);
            d.gift = get<std::string>(n, "gift", ctx);
            for (const auto& e : getOr(n, "effects", json::array(), ctx)) {
                if (!e.is_object() || e.size() != 1) fail(ctx + ": an effect has one key");
                const auto& key = e.begin().key();
                const json& v = e.begin().value();
                if (key == "growth") {
                    d.growth = get<float>(e, "growth", ctx);
                    if (d.growth <= 0) fail(ctx + ": growth must be positive");
                } else if (key == "cap") {
                    d.caps.push_back({visitor(get<std::string>(v, "visitor", ctx), ctx),
                                      get<int>(v, "add", ctx)});
                } else if (key == "rare_rate") {
                    d.rareRate.push_back({visitor(get<std::string>(v, "visitor", ctx), ctx),
                                          get<int>(v, "mul", ctx)});
                    if (d.rareRate.back().count < 1) fail(ctx + ": rare_rate mul must be >= 1");
                } else if (key == "prefer") {
                    const auto who = get<std::string>(v, "who", ctx);
                    if (who != cat_.resident.id) (void)visitor(who, ctx);
                    (void)get<std::string>(v, "activity", ctx);
                } else if (key == "fx") {
                    (void)get<std::string>(v, "name", ctx);
                    if (v.contains("seasons")) (void)seasonMask(v["seasons"], ctx);
                } else if (key == "routine") {
                    (void)get<std::string>(e, "routine", ctx);
                } else {
                    fail(ctx + ": unknown effect '" + key + "'");
                }
            }
            cat_.nooks.push_back(std::move(d));
        }
        checkUnique(cat_.nooks, "nook");
    }

    void audio(const json& root) {
        const auto& a = section(root, "audio", "catalog");
        cat_.audio.music = get<std::vector<std::string>>(a, "music", "audio");
        cat_.audio.ambience = get<std::vector<std::string>>(a, "ambience", "audio");
        cat_.audio.sfx = get<std::vector<std::string>>(a, "sfx", "audio");
        cat_.audio.notes = get<std::vector<std::string>>(a, "notes", "audio");
        for (const auto& n : cat_.audio.notes) requireSfx(n, "audio notes");
        if (cat_.audio.notes.size() < 4) fail("audio: notes needs at least four files");
    }

    void stems(const json& root, std::span<const std::string> nookIds) {
        const auto& st = section(section(root, "audio", "catalog"), "stems", "audio");
        for (const auto& [piece, out] :
             {std::pair{"day", &cat_.audio.dayStems}, std::pair{"night", &cat_.audio.nightStems}}) {
            for (const auto& s : section(st, piece, "audio stems")) {
                StemDef d;
                d.id = get<std::string>(s, "id", "stem");
                const std::string ctx = std::string("stem '") + piece + "/" + d.id + "'";
                d.file = get<std::string>(s, "file", ctx);
                if (std::ranges::find(cat_.audio.music, d.file) == cat_.audio.music.end())
                    fail(ctx + ": file is not listed under audio.music");
                if (s.contains("when"))
                    d.when = cat_.conditions.compile(s["when"], cat_, nookIds, ctx);
                out->push_back(std::move(d));
            }
            if (out->empty() || out->size() > 8) fail(std::string("stems: 1 to 8 for ") + piece);
        }
    }

    // Rare visitors gather around what their recipe asks for.
    void attractors() {
        for (auto& v : cat_.visitors) {
            if (v.recipe < 0) continue;
            std::vector<int> sels;
            cat_.conditions.needed(v.recipe, sels);
            for (const int s : sels) {
                const Selector& sel = cat_.conditions.selector(s);
                auto& out = sel.terrain ? v.attractTerrain : v.attractItems;
                for (const int id : sel.ids)
                    if (std::ranges::find(out, id) == out.end()) out.push_back(id);
            }
        }
    }

    void parse(const json& root) {
        if (get<int>(root, "version", "catalog") != 2) fail("catalog: unsupported version");
        const auto& tile = section(root, "tile", "catalog");
        cat_.tileW = get<int>(tile, "w", "tile");
        cat_.tileH = get<int>(tile, "h", "tile");
        // 2:1 isometric cells with whole half-sizes, so tile vertices land on whole pixels.
        if (cat_.tileH < 4 || cat_.tileH > 512 || cat_.tileH % 2 != 0 ||
            cat_.tileW != 2 * cat_.tileH)
            fail("tile: expected a 2:1 cell with an even height between 4 and 512");
        const auto& map = section(root, "map", "catalog");
        cat_.mapW = get<int>(map, "w", "map");
        cat_.mapH = get<int>(map, "h", "map");
        if (cat_.mapW < 1 || cat_.mapH < 1 || cat_.mapW > kMaxMapSide || cat_.mapH > kMaxMapSide ||
            static_cast<long long>(cat_.mapW) * cat_.mapH > kMaxMapTiles)
            fail("map: size out of range");

        audio(root);
        terrains(root);
        for (const auto& c : section(root, "categories", "catalog")) {
            CategoryDef d;
            d.id = get<std::string>(c, "id", "category");
            d.name = get<std::string>(c, "name", "category '" + d.id + "'");
            cat_.categories.push_back(std::move(d));
        }
        checkUnique(cat_.categories, "category");
        seasons(root);
        items(root);
        visitors(root);
        frames(root);
        land(root);
        starter(root);
        const json& prog = section(root, "progression", "catalog");
        cat_.start = pieces(section(prog, "start", "progression"), "progression start", true);
        cat_.legacy = pieces(section(prog, "legacy", "progression"), "progression legacy", false);
        resident(root);

        // Conditions may name any nook, so nook ids are known before anything is compiled.
        std::vector<std::string> nookIds;
        for (const auto& n : section(root, "nooks", "catalog"))
            nookIds.push_back(get<std::string>(n, "id", "nook"));
        std::size_t vi = 0;
        for (const auto& v : section(root, "visitors", "catalog")) {
            VisitorDef& d = cat_.visitors[vi++];
            if (v.contains("recipe"))
                d.recipe = cat_.conditions.compile(v["recipe"], cat_, nookIds,
                                                   "visitor '" + d.id + "' recipe");
        }
        wishes(root, nookIds);
        nooks(root, nookIds);
        stems(root, nookIds);
        attractors();
    }

private:
    Catalog& cat_;
};

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
std::optional<int> Catalog::findSeason(std::string_view id) const {
    return findById(seasons, id);
}
std::optional<int> Catalog::findFrame(std::string_view id) const {
    return findById(frames, id);
}
std::optional<int> Catalog::findWish(std::string_view id) const {
    return findById(wishes, id);
}
std::optional<int> Catalog::findNook(std::string_view id) const {
    return findById(nooks, id);
}
std::optional<int> Catalog::findTag(std::string_view id) const {
    const auto it = std::ranges::find(tags, id);
    if (it == tags.end()) return std::nullopt;
    return static_cast<int>(it - tags.begin());
}
bool Catalog::hasTag(int item, std::string_view tag) const {
    const auto t = findTag(tag);
    return t && std::ranges::find(items[static_cast<std::size_t>(item)].tags, *t) !=
                    items[static_cast<std::size_t>(item)].tags.end();
}

std::expected<Catalog, std::string> parseCatalog(std::string_view text) {
    try {
        Catalog cat;
        Parser(cat).parse(json::parse(text));
        return cat;
    } catch (const Invalid& e) {
        return std::unexpected(std::string(e.what()));
    } catch (const json::exception& e) {
        return std::unexpected(std::string("catalog: ") + e.what());
    } catch (const std::exception& e) {
        // Condition compile errors carry their entry's name.
        return std::unexpected(std::string(e.what()));
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
