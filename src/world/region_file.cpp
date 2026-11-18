#include "world/region_file.hpp"

#include "world/json_util.hpp"

#include <algorithm>
#include <unordered_set>

namespace lc::world {

using namespace detail;

const Card* RegionFile::card(std::string_view cardId) const {
    const auto it = std::ranges::find(cards, cardId, &std::pair<std::string, Card>::first);
    return it == cards.end() ? nullptr : &it->second;
}

namespace {

constexpr std::array<const char*, 4> kPhases{"dawn", "day", "dusk", "night"};
// Sections read into structs; everything else is kept raw in RegionFile::life.
constexpr std::array<const char*, 11> kKnown{"version", "id",      "name",      "native",
                                             "caption", "theme",   "districts", "densities",
                                             "cards",   "strings", "journal"};

Rgb3 rgb(const json& v, const std::string& ctx) {
    if (!v.is_array() || v.size() != 3) fail(ctx + ": expected [r, g, b]");
    return {asFloat(v[0], ctx), asFloat(v[1], ctx), asFloat(v[2], ctx)};
}

// "hh:mm" as game hours.
float hours(const json& v, const std::string& ctx) {
    const std::string s = asString(v, ctx);
    const auto digit = [&](std::size_t i) {
        if (i >= s.size() || s[i] < '0' || s[i] > '9') fail(ctx + ": '" + s + "' is not hh:mm");
        return s[i] - '0';
    };
    if (s.size() != 5 || s[2] != ':') fail(ctx + ": '" + s + "' is not hh:mm");
    const int h = digit(0) * 10 + digit(1);
    const int m = digit(3) * 10 + digit(4);
    if (h > 24 || m > 59 || (h == 24 && m != 0)) fail(ctx + ": '" + s + "' is not a time of day");
    return static_cast<float>(h) + static_cast<float>(m) / 60.0f;
}

Theme theme(const json& t, const std::string& ctx, int gridW, int gridH) {
    Theme out;
    if (!t.is_object()) fail(ctx + ": expected an object");
    if (has(t, "grading")) {
        const json& g = asObject(t.at("grading"), ctx + ": grading");
        for (const auto& [key, val] : g.items()) {
            const auto it = std::ranges::find(kPhases, key);
            if (it == kPhases.end()) fail(ctx + ": grading: '" + key + "' is not a phase");
            out.grading[static_cast<std::size_t>(it - kPhases.begin())] =
                rgb(val, ctx + ": grading: " + key);
        }
    }
    if (has(t, "haze")) {
        const json& h = t.at("haze");
        out.haze = rgb(field(h, "colour", ctx + ": haze"), ctx + ": haze: colour");
        out.hazeStrength = asFloat(field(h, "strength", ctx + ": haze"), ctx + ": haze: strength");
        if (out.hazeStrength < 0 || out.hazeStrength > 1)
            fail(ctx + ": haze: strength must be 0..1");
    }
    out.climate = stringOr(t, "climate", "", ctx);
    if (has(t, "ambience")) {
        const std::string ac = ctx + ": ambience";
        const json& a = asObject(t.at("ambience"), ac);
        if (has(a, "beds")) {
            const json& beds = asArray(a.at("beds"), ac + ": beds");
            for (std::size_t i = 0; i < beds.size(); ++i) {
                const std::string bc = ac + ": beds[" + std::to_string(i) + "]";
                AmbienceBed b;
                b.file = asString(field(beds[i], "file", bc), bc + ": file");
                if (has(beds[i], "hours")) {
                    const json& hv = beds[i].at("hours");
                    if (!hv.is_array() || hv.size() != 2) fail(bc + ": hours is [from, to]");
                    b.from = hours(hv[0], bc + ": hours");
                    b.to = hours(hv[1], bc + ": hours");
                }
                out.beds.push_back(std::move(b));
            }
        }
        if (has(a, "zones")) {
            const json& zones = asArray(a.at("zones"), ac + ": zones");
            for (std::size_t i = 0; i < zones.size(); ++i) {
                const std::string zc = ac + ": zones[" + std::to_string(i) + "]";
                const json& r = field(zones[i], "rect", zc);
                if (!r.is_array() || r.size() != 4) fail(zc + ": rect is [x0, y0, x1, y1]");
                AmbienceZone z;
                z.rect = {asInt(r[0], zc + ": rect", 0, gridW - 1),
                          asInt(r[1], zc + ": rect", 0, gridH - 1),
                          asInt(r[2], zc + ": rect", 0, gridW - 1) + 1,
                          asInt(r[3], zc + ": rect", 0, gridH - 1) + 1};
                if (z.rect.empty()) fail(zc + ": empty rect");
                z.file = asString(field(zones[i], "file", zc), zc + ": file");
                z.gain = floatOr(zones[i], "gain", 1.0f, zc);
                out.zones.push_back(std::move(z));
            }
        }
    }
    if (has(t, "music")) {
        const json& m = asObject(t.at("music"), ctx + ": music");
        out.musicDay = stringOr(m, "day", "", ctx + ": music");
        out.musicNight = stringOr(m, "night", "", ctx + ": music");
    }
    out.seam = boolOr(t, "seam", false, ctx);
    return out;
}

} // namespace

std::expected<RegionFile, std::string> parseRegionFile(std::string_view text, std::string_view file,
                                                       std::string_view regionId, int gridW,
                                                       int gridH) {
    const std::string f(file);
    try {
        const json doc = parseDocument(text, f);
        requireVersion1(doc, f);
        RegionFile rf;
        rf.id = asString(field(doc, "id", f), f + ": id");
        if (rf.id != regionId)
            fail(f + ": id '" + rf.id + "' differs from the region '" + std::string(regionId) +
                 "' that names this file");
        rf.name = stringOr(doc, "name", "", f);
        rf.native = stringOr(doc, "native", "", f);
        rf.caption = stringOr(doc, "caption", "", f);
        if (has(doc, "theme")) rf.theme = theme(doc.at("theme"), f + ": theme", gridW, gridH);
        if (has(doc, "districts")) {
            std::unordered_set<std::string> seen;
            const json& ds = asArray(doc.at("districts"), f + ": districts");
            for (std::size_t i = 0; i < ds.size(); ++i) {
                const std::string dc = f + ": districts[" + std::to_string(i) + "]";
                RegionDistrict d;
                d.id = asString(field(ds[i], "id", dc), dc + ": id");
                if (d.id.empty() || !seen.insert(d.id).second)
                    fail(dc + ": empty or duplicated district id '" + d.id + "'");
                if (has(ds[i], "area")) d.area = asString(ds[i].at("area"), dc + ": area");
                d.populations = has(ds[i], "populations")
                                    ? asArray(ds[i].at("populations"), dc + ": populations")
                                    : json::array();
                rf.districts.push_back(std::move(d));
            }
        }
        if (has(doc, "densities")) {
            for (const auto& [key, val] :
                 asObject(doc.at("densities"), f + ": densities").items()) {
                const std::string dc = f + ": densities: " + key;
                if (!val.is_array() || val.size() != 24) fail(dc + ": expected 24 hourly values");
                std::array<float, 24> curve{};
                for (std::size_t h = 0; h < 24; ++h) {
                    curve[h] = asFloat(val[h], dc);
                    if (curve[h] < 0 || curve[h] > 1) fail(dc + ": values must be 0..1");
                }
                rf.densities.emplace_back(key, curve);
            }
        }
        if (has(doc, "cards")) {
            for (const auto& [key, val] : asObject(doc.at("cards"), f + ": cards").items()) {
                const std::string cc = f + ": cards: " + key;
                Card c;
                c.title = asString(field(val, "title", cc), cc + ": title");
                c.epithet = stringOr(val, "epithet", "", cc);
                c.text = asString(field(val, "text", cc), cc + ": text");
                rf.cards.emplace_back(key, std::move(c));
            }
        }
        if (has(doc, "strings"))
            for (const auto& [key, val] : asObject(doc.at("strings"), f + ": strings").items())
                rf.strings.emplace_back(key, asString(val, f + ": strings: " + key));
        if (has(doc, "journal")) rf.journal = asStrings(doc.at("journal"), f + ": journal");
        rf.life = json::object();
        for (const auto& [key, val] : doc.items())
            if (std::ranges::find(kKnown, key) == kKnown.end()) rf.life[key] = val;
        return rf;
    } catch (const Invalid& e) {
        return std::unexpected(e.what());
    }
}

} // namespace lc::world
