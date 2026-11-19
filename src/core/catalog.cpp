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
    return j.contains(key) ? get<T>(j, key, ctx) : std::move(fallback);
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

int intern(std::vector<std::string>& names, const std::string& s) {
    const auto it = std::ranges::find(names, s);
    if (it != names.end()) return static_cast<int>(it - names.begin());
    names.push_back(s);
    return static_cast<int>(names.size()) - 1;
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
            d.paved = getOr(t, "paved", false, ctx);
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

    // Per-variant values: one for all, or {"r0": v, ...} listing every variant.
    template <typename T, typename F>
    std::vector<T> perVariant(const json& j, const ItemDef& d, const std::string& ctx, F&& read) {
        std::vector<T> out;
        if (!j.is_object()) {
            out.assign(static_cast<std::size_t>(d.count), read(j));
            return out;
        }
        for (int v = 0; v < d.count; ++v) {
            const std::string key = "r" + std::to_string(v);
            if (!j.contains(key)) fail(ctx + ": '" + key + "' is missing (list every variant)");
            out.push_back(read(j[key]));
        }
        if (j.size() != out.size()) fail(ctx + ": keys are the item's variants r0..");
        return out;
    }

    void slots(const json& list, ItemDef& d, const std::string& ctx) {
        if (!list.is_array()) fail(ctx + ": slots must be a list");
        for (const auto& s : list) {
            const std::string sctx = ctx + " slot";
            SlotDef slot;
            const auto name = get<std::string>(s, "id", sctx);
            const auto taken = std::ranges::any_of(d.slots, [&](const SlotDef& o) {
                return cat_.slotNames[static_cast<std::size_t>(o.name)] == name;
            });
            if (taken) fail(sctx + ": '" + name + "' is duplicated");
            slot.name = intern(cat_.slotNames, name);
            slot.kind = intern(cat_.slotKinds, get<std::string>(s, "kind", sctx));
            const auto where = get<std::string>(s, "where", sctx);
            if (where == "on")
                slot.where = SlotWhere::On;
            else if (where == "beside")
                slot.where = SlotWhere::Beside;
            else if (where == "tile")
                slot.where = SlotWhere::Tile;
            else
                fail(sctx + ": 'where' must be on, beside or tile");
            slot.cap = getOr(s, "cap", 1, sctx);
            if (slot.cap < 1 || slot.cap > 8) fail(sctx + ": cap must be within 1..8");
            const auto facing = getOr(s, "facing", std::string("free"), sctx);
            if (facing == "rotation")
                slot.facing = SlotFacing::Rotation;
            else if (facing == "item")
                slot.facing = SlotFacing::Item;
            else if (facing == "out")
                slot.facing = SlotFacing::Out;
            else if (facing != "free")
                fail(sctx + ": facing is rotation, item, out or free");
            const auto points = [&](const json& j, float add) {
                std::vector<Vec2> pts;
                if (!j.is_array() || j.empty()) fail(sctx + ": a list of [x, y] points");
                for (const auto& pt : j) {
                    if (!pt.is_array() || pt.size() != 2 || !pt[0].is_number() ||
                        !pt[1].is_number())
                        fail(sctx + ": points are [x, y]");
                    pts.push_back({pt[0].get<float>() + add, pt[1].get<float>() + add});
                }
                return pts;
            };
            if (slot.where == SlotWhere::Tile) {
                // Whole tiles: actors stand in their middle.
                slot.spots = perVariant<std::vector<Vec2>>(
                    section(s, "tiles", sctx.c_str()), d, sctx + " tiles",
                    [&](const json& j) { return points(j, 0.5f); });
            } else if (s.contains("spots")) {
                if (slot.where != SlotWhere::On) fail(sctx + ": spots belong to 'on' slots");
                slot.spots = perVariant<std::vector<Vec2>>(
                    s["spots"], d, sctx + " spots", [&](const json& j) { return points(j, 0.0f); });
            } else if (slot.where == SlotWhere::On) {
                for (int v = 0; v < d.count; ++v) {
                    const bool turned = d.layout == Layout::Rotate && v % 2 == 1;
                    const int w = turned ? d.footprintH : d.footprintW;
                    const int h = turned ? d.footprintW : d.footprintH;
                    slot.spots.push_back(
                        {{static_cast<float>(w) * 0.5f, static_cast<float>(h) * 0.5f}});
                }
            }
            if (slot.where != SlotWhere::Beside)
                for (const auto& pts : slot.spots)
                    if (std::cmp_less(pts.size(), slot.cap) && pts.size() > 1)
                        fail(sctx + ": fewer spots than its cap");
            if (s.contains("lift"))
                slot.lift = perVariant<float>(s["lift"], d, sctx + " lift",
                                              [&](const json& j) { return j.get<float>(); });
            else if (slot.where == SlotWhere::On && !d.perch.empty())
                for (const int p : d.perch) slot.lift.push_back(static_cast<float>(p));
            if (s.contains("face")) {
                slot.face =
                    perVariant<std::uint8_t>(s["face"], d, sctx + " face", [&](const json& j) {
                        static constexpr std::string_view kDirs[] = {"+x", "+y", "-x", "-y"};
                        const auto it = std::ranges::find(kDirs, j.get<std::string>());
                        if (it == std::end(kDirs)) fail(sctx + ": face is +x, +y, -x or -y");
                        return static_cast<std::uint8_t>(it - std::begin(kDirs));
                    });
            } else if (slot.facing == SlotFacing::Rotation) {
                // R2.1: r0 faces +x, r1 +y, r2 -x, r3 -y.
                for (int v = 0; v < d.count; ++v)
                    slot.face.push_back(static_cast<std::uint8_t>(v % 4));
            }
            if (s.contains("states")) (void)get<std::vector<std::string>>(s, "states", sctx);
            if (s.contains("holds")) {
                const json& h = s["holds"];
                if (!h.is_object() || h.size() != 1) fail(sctx + ": holds one kind of goods");
                const auto it = std::ranges::find(cat_.goods, h.begin().key(), &GoodsDef::id);
                if (it == cat_.goods.end())
                    fail(sctx + ": unknown goods '" + h.begin().key() + "'");
                slot.holds = static_cast<int>(it - cat_.goods.begin());
                slot.holdsMax = h.begin().value().get<int>();
                if (slot.holdsMax < 1 || slot.holdsMax > 3) fail(sctx + ": holds 1 to 3");
            }
            d.slots.push_back(std::move(slot));
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
                d.crossing = d.crossing || tag == "crossing";
            }
            if (it.contains("perch")) {
                const json& p = it["perch"];
                const bool ok =
                    p.is_number_integer() ||
                    (p.is_array() && std::cmp_equal(p.size(), d.count) &&
                     std::ranges::all_of(p, [](const json& v) { return v.is_number_integer(); }));
                if (!ok) fail(ctx + ": perch is a pixel height, or one per variant");
                if (p.is_array())
                    d.perch = p.get<std::vector<int>>();
                else
                    d.perch.assign(static_cast<std::size_t>(d.count), p.get<int>());
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
            d.shelter = getOr(it, "shelter", 0, ctx);
            if (d.shelter < 0 || d.shelter > 8) fail(ctx + ": shelter must be within 0..8");
            if (it.contains("slots")) slots(it["slots"], d, ctx);
            cat_.items.push_back(std::move(d));
        }
        checkUnique(cat_.items, "item");
        if (cat_.items.size() > 60000) fail("items: too many entries");
    }

    // Activities are read as actor routines (core/actor_data.cpp); this checks what that
    // reading takes for granted.
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
            d.growth = getOr(s, "growth", 1.0f, ctx);
            if (d.growth < 0) fail(ctx + ": growth must be >= 0");
            d.line = get<std::string>(s, "line", ctx);
            if (s.contains("climate")) {
                const json& c = s["climate"];
                d.showers = getOr(c, "showers", 0.0f, ctx);
                d.clouds = getOr(c, "clouds", 0.0f, ctx);
                d.wind = getOr(c, "wind", 0.3f, ctx);
                if (d.showers < 0 || d.clouds < 0 || d.wind < 0 || d.wind > 1)
                    fail(ctx + ": climate showers and clouds >= 0, wind within 0..1");
            }
            cat_.seasonDays.push_back(d.days);
            cat_.seasons.push_back(std::move(d));
        }
        checkUnique(cat_.seasons, "season");
        if (cat_.seasons.empty() || cat_.seasons.size() > 8) fail("seasons: 1 to 8 are needed");
    }

    void calendar(const json& root) {
        if (!root.contains("calendar")) return;
        const json& cal = section(root, "calendar", "catalog");
        const json& months = cal.contains("months") ? cal["months"] : json();
        if (!months.is_array()) fail("calendar: missing 'months'");
        // Month i is calendar day i of the year, so it must lie in that day's season.
        std::vector<std::string> seasonOfDay;
        for (const SeasonDef& d : cat_.seasons)
            for (int k = 0; k < d.days; ++k) seasonOfDay.push_back(d.id);
        if (months.size() != seasonOfDay.size())
            fail("calendar: one month per day of the year is needed");
        for (std::size_t i = 0; i < months.size(); ++i) {
            const std::string ctx = "calendar month " + std::to_string(i);
            const std::string id = get<std::string>(months[i], "id", ctx);
            if (get<std::string>(months[i], "season", ctx) != seasonOfDay[i])
                fail(ctx + " ('" + id + "'): its season is not that day's");
            if (std::ranges::find(cat_.months, id) != cat_.months.end())
                fail(ctx + ": '" + id + "' twice");
            cat_.months.push_back(id);
        }
    }

    // Snow of each climate; a climate without its own `snow` block takes its parent's.
    void climates(const json& root) {
        if (!root.contains("climates")) return;
        const json& list = root["climates"];
        if (!list.is_array()) fail("climates: expected a list");
        const auto byId = [&](const std::string& id) -> const json* {
            for (const json& c : list)
                if (c.is_object() && c.value("id", std::string()) == id) return &c;
            return nullptr;
        };
        for (const json& c : list) {
            const std::string id = get<std::string>(c, "id", "climates");
            const std::string ctx = "climate " + id;
            const json* from = &c;
            for (int depth = 0; !from->contains("snow") && from->contains("inherits"); ++depth) {
                from = byId(get<std::string>(*from, "inherits", ctx));
                if (from == nullptr || depth > 16) fail(ctx + ": inherits no climate");
            }
            ClimateDef d;
            d.id = id;
            d.snowLine.assign(cat_.months.size(), -1);
            if (from->contains("snow")) {
                const json& snow = (*from)["snow"];
                if (const auto line = snow.find("line"); line != snow.end()) {
                    if (!line->is_array() || line->size() != cat_.months.size())
                        fail(ctx + ": snow line needs one level (or null) per month");
                    for (std::size_t m = 0; m < line->size(); ++m)
                        if ((*line)[m].is_number_integer())
                            d.snowLine[m] = std::max(0, (*line)[m].get<int>());
                }
                if (const auto low = snow.find("lowland"); low != snow.end()) {
                    for (const json& m : low->value("months", json::array())) {
                        const auto it = std::ranges::find(cat_.months, m.get<std::string>());
                        if (it == cat_.months.end()) fail(ctx + ": lowland month unknown");
                        d.lowlandMonths |=
                            static_cast<std::uint16_t>(1u << (it - cat_.months.begin()));
                    }
                    d.lowlandChance = std::clamp(getOr(*low, "chance", 0.0f, ctx), 0.0f, 1.0f);
                }
            }
            // Traffic by month (`by_month` rows): the travel rows merge key by key down the
            // parents (the nearer wins), the sea rows come whole from the nearest sea block, and
            // a land climate's sailing is its coast's.
            const auto rows = [&](const json& block) {
                for (auto it = block.begin(); it != block.end(); ++it) {
                    if (std::ranges::find(d.traffic, it.key(), &ClimateDef::Row::name) !=
                        d.traffic.end())
                        continue;
                    std::vector<float> row(cat_.months.size(), 0.0f);
                    if (it->is_number()) {
                        std::ranges::fill(row, it->get<float>());
                    } else if (it->is_array() && it->size() == row.size() &&
                               std::ranges::all_of(*it,
                                                   [](const json& v) { return v.is_number(); })) {
                        for (std::size_t m = 0; m < row.size(); ++m) row[m] = (*it)[m].get<float>();
                    } else {
                        continue; // not a row of factors (notes, closed months, hours)
                    }
                    d.traffic.push_back({it.key(), std::move(row)});
                }
            };
            const json* sea = nullptr;
            std::string coast;
            for (const json* k = &c; k != nullptr;
                 k = k->contains("inherits") ? byId(get<std::string>(*k, "inherits", ctx))
                                             : nullptr) {
                if (const auto t = k->find("travel"); t != k->end() && t->is_object()) rows(*t);
                if (sea == nullptr && k->contains("sea") && (*k)["sea"].is_object())
                    sea = &(*k)["sea"];
                if (coast.empty() && k->contains("coast"))
                    coast = get<std::string>(*k, "coast", ctx);
            }
            if (sea == nullptr && !coast.empty())
                if (const json* cc = byId(coast); cc != nullptr && cc->contains("sea"))
                    sea = &(*cc)["sea"];
            if (sea != nullptr) rows(*sea);
            // Greens by month, from the nearest climate up the parents that names them (the sets'
            // own words, `set_classes`, before the shared `classes`).
            for (const json* k = &c; k != nullptr;
                 k = k->contains("inherits") ? byId(get<std::string>(*k, "inherits", ctx))
                                             : nullptr) {
                const char* key = k->contains("set_classes") ? "set_classes"
                                  : k->contains("classes")   ? "classes"
                                                             : nullptr;
                if (key == nullptr) continue;
                const json& cl = (*k)[key];
                static constexpr std::array<std::pair<const char*, GreenClass>, kGreenClasses>
                    kClasses{{{"grass", GreenClass::Grass}, {"deciduous", GreenClass::Deciduous}}};
                for (const auto& [name, cls] : kClasses) {
                    const auto it = cl.find(name);
                    if (it == cl.end() || !it->is_array() || it->size() != cat_.months.size())
                        continue;
                    auto& row = d.greens[static_cast<std::size_t>(cls)];
                    for (const json& w : *it) {
                        const std::string s = w.is_string() ? w.get<std::string>() : "";
                        row.push_back(s == "fresh"     ? GreenState::Fresh
                                      : s == "dry"     ? GreenState::Dry
                                      : s == "gone"    ? GreenState::Dry
                                      : s == "dormant" ? GreenState::Dormant
                                      : s == "turn"    ? GreenState::Turn
                                      : s == "bare"    ? GreenState::Bare
                                                       : GreenState::Green);
                    }
                }
                break;
            }
            cat_.climates.push_back(std::move(d));
        }
        checkUnique(cat_.climates, "climate");
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
        d.enabled = getOr(r, "enabled", true, ctx);
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
            std::vector<std::string> texts;
            for (const auto& l : list) {
                if (!l.is_string() || l.get<std::string>().size() > kMaxLine)
                    fail(ctx + ": line in '" + key + "' is not text of at most 52 characters");
                texts.push_back(l.get<std::string>());
            }
            d.contexts.push_back(key);
            d.lines.push_back(std::move(texts));
        }
        if (cat_.findVisitor(d.id)) fail(ctx + ": shares an id with a visitor");
    }

    void goods(const json& root) {
        for (const auto& g : getOr(root, "goods", json::array(), "catalog")) {
            GoodsDef d;
            d.id = get<std::string>(g, "id", "goods");
            d.name = get<std::string>(g, "name", "goods '" + d.id + "'");
            cat_.goods.push_back(std::move(d));
        }
        checkUnique(cat_.goods, "goods");
    }

    void events(const json& root, std::span<const std::string> nookIds) {
        static constexpr std::pair<std::string_view, EventShow> kShows[] = {
            {"rainbow", EventShow::Rainbow},
            {"shooting_star", EventShow::ShootingStar},
            {"owl_call", EventShow::OwlCall},
            {"rustle", EventShow::Rustle},
            {"gust", EventShow::Gust},
            {"fish_jump", EventShow::FishJump},
            {"frog_chorus", EventShow::FrogChorus},
            {"chorus", EventShow::Chorus},
            {"firefly_sync", EventShow::FireflySync},
            {"smoke", EventShow::Smoke},
            {"season", EventShow::Season}};
        static constexpr std::pair<std::string_view, EventOn> kTriggers[] = {
            {"window", EventOn::Window}, {"hours", EventOn::Hours},
            {"rain", EventOn::Rain},     {"rain_stop", EventOn::RainStop},
            {"placed", EventOn::Placed}, {"reactive", EventOn::Reactive},
            {"cook", EventOn::Cook},     {"season", EventOn::Season}};
        for (const auto& e : getOr(root, "events", json::array(), "catalog")) {
            EventDef d;
            d.id = get<std::string>(e, "id", "event");
            const std::string ctx = "event '" + d.id + "'";
            const auto show = get<std::string>(e, "show", ctx);
            const auto trig = get<std::string>(e, "trigger", ctx);
            bool found = false;
            for (const auto& [n, v] : kShows)
                if (n == show) {
                    d.show = v;
                    found = true;
                }
            if (!found) fail(ctx + ": unknown show '" + show + "'");
            found = false;
            for (const auto& [n, v] : kTriggers)
                if (n == trig) {
                    d.on = v;
                    found = true;
                }
            if (!found) fail(ctx + ": unknown trigger '" + trig + "'");
            if (e.contains("time")) {
                d.phases = 0;
                phases(e["time"], ctx);
                for (const auto& p : e["time"])
                    d.phases |= static_cast<std::uint8_t>(
                        1u << (std::ranges::find(kPhaseIds, p.get<std::string>()) -
                               kPhaseIds.begin()));
            }
            if (e.contains("seasons")) d.seasons = seasonMask(e["seasons"], ctx);
            if (e.contains("weather")) {
                const auto w = get<std::string>(e, "weather", ctx);
                if (w != "clear" && w != "rain") fail(ctx + ": weather is clear or rain");
                d.weather = w == "rain" ? 1 : 0;
            }
            if (e.contains("when")) d.when = cat_.conditions.compile(e["when"], cat_, nookIds, ctx);
            d.mean = getOr(e, "mean", 0.0f, ctx);
            const auto pair = [&](const char* key, float& a, float& b) {
                if (!e.contains(key)) return;
                const json& v = e[key];
                if (v.is_number()) {
                    a = b = v.get<float>();
                    return;
                }
                const auto r = get<std::vector<float>>(e, key, ctx);
                if (r.size() != 2 || r[0] < 0 || r[1] < r[0])
                    fail(ctx + ": '" + key + "' is [min, max]");
                a = r[0];
                b = r[1];
            };
            pair("every", d.every0, d.every1);
            pair("duration", d.dur0, d.dur1);
            if (d.on == EventOn::Window && d.mean <= 0 && d.every1 <= 0)
                fail(ctx + ": a window event needs 'mean' or 'every'");
            if (d.on == EventOn::Hours) {
                const auto h = get<std::vector<float>>(e, "hours", ctx);
                if (h.size() != 2) fail(ctx + ": hours [from, to] as game hours");
                d.from = h[0];
                d.to = h[1];
            }
            d.cooldown = getOr(e, "cooldown", 0.0f, ctx);
            d.daily = getOr(e, "daily", false, ctx);
            d.minRain = getOr(e, "min_rain", 0.0f, ctx);
            if (d.on == EventOn::Placed) {
                const json& n = section(e, "near", ctx.c_str());
                const auto tag = cat_.findTag(get<std::string>(n, "tag", ctx));
                if (!tag) fail(ctx + ": unknown tag");
                d.nearTag = *tag;
                d.within = getOr(n, "within", 1.0f, ctx);
            }
            if (e.contains("sfx")) {
                d.sfx = "sfx/" + get<std::string>(e, "sfx", ctx) + ".wav";
                requireSfx(d.sfx, ctx);
            }
            d.gain = getOr(e, "gain", 1.0f, ctx);
            if (e.contains("who")) d.who = visitor(get<std::string>(e, "who", ctx), ctx);
            cat_.events.push_back(std::move(d));
        }
        checkUnique(cat_.events, "event");
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
                    const int w = who == cat_.resident.id ? -1 : visitor(who, ctx);
                    d.prefer.emplace_back(
                        w, intern(cat_.activityNames, get<std::string>(v, "activity", ctx)));
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
        calendar(root);
        climates(root);
        goods(root);
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
        if (root.contains("tour")) {
            // The first-minute tour's wish and the piece it asks to plant (R10.5).
            const json& t = root["tour"];
            const auto wish = cat_.findWish(get<std::string>(t, "wish", "tour"));
            const auto piece = cat_.findItem(get<std::string>(t, "piece", "tour"));
            if (!wish || !piece) fail("tour: wish and piece must name a wish and an item");
            cat_.tourWish = *wish;
            cat_.tourPiece = *piece;
        }
        nooks(root, nookIds);
        stems(root, nookIds);
        events(root, nookIds);
        attractors();
        compileActors(root, cat_);
    }

private:
    Catalog& cat_;
};

} // namespace

const ClimateDef::Row* ClimateDef::row(std::string_view name) const {
    const auto it = std::ranges::find(traffic, name, &Row::name);
    return it == traffic.end() ? nullptr : &*it;
}

const ClimateDef* Catalog::findClimate(std::string_view id) const {
    const auto i = findById(climates, id);
    return i ? &climates[static_cast<std::size_t>(*i)] : nullptr;
}

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
int ResidentDef::context(std::string_view c) const {
    const auto it = std::ranges::find(contexts, c);
    return it == contexts.end() ? -1 : static_cast<int>(it - contexts.begin());
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
