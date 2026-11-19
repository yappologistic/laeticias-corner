#include "world/geometry.hpp"

#include "world/json_util.hpp"

#include <algorithm>
#include <array>
#include <charconv>

namespace lc::world {

using namespace detail;

const GeomVariant* GeomItem::variant(std::string_view key) const {
    const auto it = std::ranges::find(variants, key, &GeomVariant::key);
    return it == variants.end() ? nullptr : &*it;
}

namespace {

constexpr std::array<std::string_view, 4> kFaces{"+x", "+y", "-x", "-y"};
// Offsets inside a geometry file stay near their item; this bounds them well past any footprint.
constexpr int kMaxOffset = 1 << 14;

bool parseInt(std::string_view s, int& out) {
    const auto [p, ec] = std::from_chars(s.data(), s.data() + s.size(), out);
    return ec == std::errc{} && p == s.data() + s.size();
}

// "r<k>" (rotate and variant layouts) or "m<mask>" (connect layouts).
void checkVariantKey(const std::string& key, const std::string& ctx) {
    int n = 0;
    const bool ok = key.size() >= 2 && (key[0] == 'r' || key[0] == 'm') &&
                    parseInt(std::string_view(key).substr(1), n) && n >= 0 &&
                    n < (key[0] == 'm' ? 16 : 256);
    if (!ok) fail(ctx + ": '" + key + "' is not a variant key r<k> or m<mask>");
}

Offset offset(const json& v, const std::string& ctx) {
    const auto p = asIntPair(v, ctx, -kMaxOffset, kMaxOffset);
    return {p[0], p[1]};
}

TilePos tileOffset(const json& v, const std::string& ctx) {
    const auto p = asIntPair(v, ctx, -kMaxOffset, kMaxOffset);
    return {p[0], p[1]};
}

GeomVariant variant(const std::string& key, const json& g, const std::string& c) {
    GeomVariant v;
    v.key = key;
    v.h = asInt(field(g, "h", c), c + ": h", 0, kMaxOffset);
    if (has(g, "pieces")) {
        const json& ps = asArray(g.at("pieces"), c + ": pieces");
        for (std::size_t i = 0; i < ps.size(); ++i) {
            const std::string pc = c + ": pieces[" + std::to_string(i) + "]";
            if (!ps[i].is_array() || ps[i].size() != 4) fail(pc + ": expected [dx, dy, w, h]");
            const int x = asInt(ps[i][0], pc, 0, kMaxOffset);
            const int y = asInt(ps[i][1], pc, 0, kMaxOffset);
            const int w = asInt(ps[i][2], pc + ": w", 1, kMaxPieceSide);
            const int h = asInt(ps[i][3], pc + ": h", 1, kMaxPieceSide);
            v.pieces.push_back({{x, y, x + w, y + h}, false});
        }
    }
    if (has(g, "walk")) {
        const json& ws = asArray(g.at("walk"), c + ": walk");
        for (std::size_t i = 0; i < ws.size(); ++i)
            v.walk.push_back(tileOffset(ws[i], c + ": walk[" + std::to_string(i) + "]"));
    }
    if (has(g, "water")) {
        const json& ws = asArray(g.at("water"), c + ": water");
        for (std::size_t i = 0; i < ws.size(); ++i)
            v.water.push_back(tileOffset(ws[i], c + ": water[" + std::to_string(i) + "]"));
    }
    if (has(g, "walk_z")) {
        for (const auto& [k, z] : asObject(g.at("walk_z"), c + ": walk_z").items()) {
            const std::string zc = c + ": walk_z: " + k;
            const auto comma = k.find(',');
            TilePos t;
            if (comma == std::string::npos ||
                !parseInt(std::string_view(k).substr(0, comma), t.x) ||
                !parseInt(std::string_view(k).substr(comma + 1), t.y))
                fail(zc + ": the key is not \"dx,dy\"");
            // A kit deck's floor (a crossing, with no walk list: it walks by its tag) may name
            // its tiles; with a walk list a floor belongs to one of its tiles.
            if (!v.walk.empty() && std::ranges::find(v.walk, t) == v.walk.end())
                fail(zc + ": not a walk tile");
            v.walkZ.emplace_back(t, asInt(z, zc, 0, kMaxOffset));
        }
    }
    if (has(g, "floor_pieces")) {
        const json& fs = asArray(g.at("floor_pieces"), c + ": floor_pieces");
        for (std::size_t i = 0; i < fs.size(); ++i) {
            const int p =
                asInt(fs[i], c + ": floor_pieces", 0, static_cast<long long>(v.pieces.size()) - 1);
            v.pieces[static_cast<std::size_t>(p)].floor = true;
        }
    }
    if (has(g, "slots")) {
        for (const auto& [id, spots] : asObject(g.at("slots"), c + ": slots").items()) {
            const std::string sc = c + ": slots: " + id;
            GeomSlot slot;
            slot.id = id;
            const json& list = asArray(spots, sc);
            if (list.empty()) fail(sc + ": a slot needs at least one spot");
            for (std::size_t i = 0; i < list.size(); ++i) {
                const std::string pc = sc + "[" + std::to_string(i) + "]";
                GeomSpot s;
                s.t = tileOffset(field(list[i], "t", pc), pc + ": t");
                if (has(list[i], "off")) s.off = offset(list[i].at("off"), pc + ": off");
                s.z = intOr(list[i], "z", 0, pc, -kMaxOffset, kMaxOffset);
                if (has(list[i], "face")) {
                    const std::string f = asString(list[i].at("face"), pc + ": face");
                    const auto it = std::ranges::find(kFaces, f);
                    if (it == kFaces.end()) fail(pc + ": face '" + f + "' is not +x, +y, -x or -y");
                    s.face = static_cast<std::uint8_t>(it - kFaces.begin());
                }
                slot.spots.push_back(s);
            }
            v.slots.push_back(std::move(slot));
        }
    }
    if (has(g, "emitters"))
        for (const auto& [name, at] : asObject(g.at("emitters"), c + ": emitters").items())
            v.emitters.emplace_back(name, offset(at, c + ": emitters: " + name));
    return v;
}

} // namespace

std::expected<GeometryFile, std::string> parseGeometry(std::string_view text, std::string_view file,
                                                       std::string_view set) {
    const std::string f(file);
    try {
        const json doc = parseDocument(text, f);
        requireVersion1(doc, f);
        GeometryFile g;
        g.file = f;
        g.set = asString(field(doc, "set", f), f + ": set");
        if (g.set != set) fail(f + ": set '" + g.set + "' differs from '" + std::string(set) + "'");
        const auto tile = asIntPair(field(doc, "tile", f), f + ": tile", 1, 4096);
        g.tileW = tile[0];
        g.tileH = tile[1];
        for (const auto& [id, vars] : asObject(field(doc, "items", f), f + ": items").items()) {
            const std::string ic = f + ": items: " + id;
            requireSetId(id, g.set, ic);
            GeomItem item;
            item.id = id;
            for (const auto& [key, gv] : asObject(vars, ic).items()) {
                checkVariantKey(key, ic);
                item.variants.push_back(
                    variant(key, asObject(gv, ic + ": " + key), ic + ": " + key));
            }
            g.items.push_back(std::move(item));
        }
        if (has(doc, "actors")) {
            for (const auto& [id, a] : asObject(doc.at("actors"), f + ": actors").items()) {
                const std::string ac = f + ": actors: " + id;
                requireSetId(id, g.set, ac);
                GeomActor actor;
                actor.id = id;
                if (has(a, "carry_at"))
                    for (const auto& [anim, frames] :
                         asObject(a.at("carry_at"), ac + ": carry_at").items()) {
                        std::vector<Offset> pts;
                        const json& list = asArray(frames, ac + ": carry_at: " + anim);
                        pts.reserve(list.size());
                        for (std::size_t i = 0; i < list.size(); ++i)
                            pts.push_back(offset(list[i], ac + ": carry_at: " + anim));
                        actor.carryAt.emplace_back(anim, std::move(pts));
                    }
                g.actors.push_back(std::move(actor));
            }
        }
        return g;
    } catch (const Invalid& e) {
        return std::unexpected(e.what());
    }
}

} // namespace lc::world
