#include "core/save.hpp"

#include "core/edit.hpp"
#include "core/land.hpp"
#include "core/tuning.hpp"

#include <nlohmann/json.hpp>

#include <algorithm>
#include <cctype>
#include <cerrno>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <format>
#include <map>
#include <memory>

#if defined(__unix__) || defined(__APPLE__)
#include <fcntl.h>
#include <unistd.h>
#define LC_HAVE_FSYNC 1
#endif

namespace lc {

using nlohmann::json;

namespace {

// Coordinates outside this range cannot be on any map; rejecting them early keeps every later
// addition far from integer overflow.
constexpr long long kCoordLimit = 1LL << 24;
constexpr std::string_view kSaveBaseBlank = "blank"; // version 2: untouched chunks are empty

std::string_view weatherId(WeatherMode m) {
    switch (m) {
    case WeatherMode::Natural: return "natural";
    case WeatherMode::Rain: return "rain";
    case WeatherMode::Clear: return "clear";
    }
    return "natural";
}

int terrainValue(const World& w, TilePos p) {
    const int t = w.terrainAt(p);
    return t == kNoGround ? -1 : t;
}

// Collects repairs by kind so a damaged file with a million bad entries logs a handful of lines.
class Warnings {
public:
    void add(const std::string& kind) { ++counts_[kind]; }
    void flush(std::vector<std::string>& out) const {
        for (const auto& [kind, n] : counts_)
            out.push_back(n == 1 ? kind : kind + " (" + std::to_string(n) + " times)");
    }

private:
    std::map<std::string, int> counts_;
};

// Optional fields are read one by one: a field of the wrong type or out of range falls back to
// its default with a warning, and never costs the rest of the world (QA2-09).
const json& listField(const json& j, const char* key, Warnings& warn) {
    static const json kEmpty = json::array();
    if (!j.is_object() || !j.contains(key)) return kEmpty;
    if (!j[key].is_array()) {
        warn.add(std::string("'") + key + "' was not a list and was ignored");
        return kEmpty;
    }
    return j[key];
}

long long intField(const json& j, const char* key, long long def, long long lo, long long hi,
                   Warnings& warn) {
    if (!j.is_object() || !j.contains(key)) return def;
    const json& v = j[key];
    if (!v.is_number_integer()) {
        warn.add(std::string("'") + key + "' was not a whole number and was reset");
        return def;
    }
    const long long n = v.is_number_unsigned() && v.get<unsigned long long>() > 1ULL << 62
                            ? hi
                            : v.get<long long>();
    if (n < lo || n > hi) warn.add(std::string("'") + key + "' was out of range and was clamped");
    return std::clamp(n, lo, hi);
}

double numField(const json& j, const char* key, double def, double lo, double hi, Warnings& warn) {
    if (!j.is_object() || !j.contains(key)) return def;
    const json& v = j[key];
    if (!v.is_number() || !std::isfinite(v.get<double>())) {
        warn.add(std::string("'") + key + "' was not a number and was reset");
        return def;
    }
    const double d = v.get<double>();
    if (d < lo || d > hi) warn.add(std::string("'") + key + "' was out of range and was clamped");
    return std::clamp(d, lo, hi);
}

bool boolField(const json& j, const char* key, bool def, Warnings& warn) {
    if (!j.is_object() || !j.contains(key)) return def;
    if (!j[key].is_boolean()) {
        warn.add(std::string("'") + key + "' was not true or false and was reset");
        return def;
    }
    return j[key].get<bool>();
}

std::string stringField(const json& j, const char* key, Warnings& warn) {
    if (!j.is_object() || !j.contains(key)) return {};
    if (!j[key].is_string()) {
        warn.add(std::string("'") + key + "' was not text and was dropped");
        return {};
    }
    return j[key].get<std::string>();
}

// The longest play time a save may claim (about 30 000 years); beyond it numbers lose seconds.
constexpr double kMaxPlayed = 1e12;

struct Loader {
    const Catalog& cat;
    SaveData& data;
    TilePos offset;
    std::vector<int> remap; // file palette index -> catalog terrain (kNoGround for -1)
    Warnings warn;

    void readPalette(const json& palette) {
        if (!palette.is_array()) throw std::runtime_error("palette is not a list");
        for (const auto& id : palette) {
            const std::string s = id.is_string() ? id.get<std::string>() : std::string("?");
            const auto idx = cat.findTerrain(s);
            if (!idx)
                warn.add("unknown terrain '" + s + "' became " +
                         cat.terrain[static_cast<std::size_t>(cat.baseTerrain)].id);
            remap.push_back(idx.value_or(cat.baseTerrain));
        }
    }

    void terrain(int x, int y, const json& v) {
        int t = cat.baseTerrain;
        if (v.is_number_integer() && v.get<long long>() == -1) {
            t = kNoGround;
        } else if (v.is_number_integer() && v.get<long long>() >= 0 &&
                   v.get<long long>() < static_cast<long long>(remap.size())) {
            t = remap[static_cast<std::size_t>(v.get<long long>())];
        } else {
            warn.add("terrain value out of range became the base terrain");
        }
        const TilePos p{x + offset.x, y + offset.y};
        if (!data.world.inBounds(p)) {
            warn.add("terrain outside the map was dropped");
            return;
        }
        data.world.setTerrain(p, t);
    }

    void item(const json& j) {
        if (!j.is_object() || !j.contains("id") || !j["id"].is_string()) {
            warn.add("malformed item skipped");
            return;
        }
        const auto id = j["id"].get<std::string>();
        const auto type = cat.findItem(id);
        if (!type) {
            warn.add("unknown item '" + id + "' skipped");
            return;
        }
        const auto coord = [&](const char* k) -> std::optional<int> {
            if (!j.contains(k) || !j[k].is_number_integer()) return std::nullopt;
            const auto v = j[k].get<long long>();
            if (v < -kCoordLimit || v > kCoordLimit) return std::nullopt;
            return static_cast<int>(v);
        };
        const auto x = coord("x");
        const auto y = coord("y");
        if (!x || !y) {
            warn.add("item '" + id + "' with bad coordinates skipped");
            return;
        }
        const auto& def = cat.items[static_cast<std::size_t>(*type)];
        const json& vj = j.contains("v") ? j["v"] : json(0);
        if (!vj.is_number_integer() || vj.get<long long>() < 0 ||
            vj.get<long long>() >= def.count) {
            warn.add("item '" + id + "' with an invalid variant skipped");
            return;
        }
        Item it = makeItem(cat, *type, static_cast<int>(vj.get<long long>()),
                           {*x + offset.x, *y + offset.y});
        if (canPlace(data.world, cat, it) != PlaceResult::Ok) {
            warn.add("item '" + id + "' no longer fits and was skipped");
            return;
        }
        if (def.growth.stages > 0 && j.contains("g")) {
            const json& g = j["g"];
            if (g.is_array() && g.size() == 2 && g[0].is_number_integer() && g[1].is_number() &&
                g[0].get<long long>() >= 0 && g[0].get<long long>() < def.growth.stages &&
                std::isfinite(g[1].get<double>())) {
                it.stage = static_cast<std::uint8_t>(g[0].get<int>());
                it.growth = std::clamp(g[1].get<float>(), 0.0f, 1.0f);
            } else {
                warn.add("item '" + id + "' with bad growth started over");
            }
        }
        data.world.addItem(it);
    }
};

// Ids from a list that the catalog knows, through `find`; the rest become one warning each kind.
template <typename F>
std::vector<int> knownIds(const json& list, F&& find, Warnings& warn, const char* what) {
    std::vector<int> out;
    if (!list.is_array()) return out;
    for (const auto& id : list) {
        if (!id.is_string()) continue;
        const auto i = find(id.get<std::string>());
        if (i)
            out.push_back(*i);
        else
            warn.add(std::string("unknown ") + what + " '" + id.get<std::string>() + "' dropped");
    }
    return out;
}

std::expected<std::pair<int, int>, std::string> mapSize(const json& root) {
    const json& map = root.at("map");
    const json& w = map.at("w");
    const json& h = map.at("h");
    if (!w.is_number_integer() || !h.is_number_integer() || w.get<long long>() < 1 ||
        h.get<long long>() < 1 || w.get<long long>() > kMaxMapSide ||
        h.get<long long>() > kMaxMapSide)
        return std::unexpected("save: map size out of range");
    return std::pair{w.get<int>(), h.get<int>()};
}

void readVersion1(const json& root, Loader& in, int fileW, int fileH) {
    const auto& terrain = root.at("terrain");
    if (!terrain.is_array() ||
        terrain.size() != static_cast<std::size_t>(fileW) * static_cast<std::size_t>(fileH))
        throw std::runtime_error("terrain has the wrong size");
    for (int y = 0; y < fileH; ++y)
        for (int x = 0; x < fileW; ++x)
            in.terrain(x, y,
                       terrain[static_cast<std::size_t>(y) * static_cast<std::size_t>(fileW) +
                               static_cast<std::size_t>(x)]);
    for (const auto& j : listField(root, "items", in.warn)) in.item(j);
}

void readVersion2(const json& root, Loader& in, int fileW, int fileH) {
    if (root.contains("chunk") &&
        (!root["chunk"].is_number_integer() || root["chunk"].get<long long>() < 1 ||
         root["chunk"].get<long long>() > 1024))
        throw std::runtime_error("chunk size out of range");
    const int chunk = root.contains("chunk") ? root["chunk"].get<int>() : kChunk;
    if (root.contains("base") &&
        (!root["base"].is_string() || root["base"].get<std::string>() != kSaveBaseBlank))
        throw std::runtime_error("unknown base");
    // Items are listed under the chunk of their origin, so every chunk's terrain is read before
    // any item: a water piece across a chunk line must find the water of the later chunk.
    std::vector<const json*> items;
    for (const auto& c : listField(root, "chunks", in.warn)) {
        if (!c.is_object() || !c.contains("x") || !c.contains("y") || !c["x"].is_number_integer() ||
            !c["y"].is_number_integer()) {
            in.warn.add("malformed chunk skipped");
            continue;
        }
        const long long cx = c["x"].get<long long>();
        const long long cy = c["y"].get<long long>();
        if (cx < 0 || cy < 0 || cx >= fileW || cy >= fileH || cx * chunk >= fileW ||
            cy * chunk >= fileH) {
            in.warn.add("chunk outside the map skipped");
            continue;
        }
        const long long x0 = cx * chunk;
        const long long y0 = cy * chunk;
        const int cw = static_cast<int>(std::min<long long>(chunk, fileW - x0));
        const int chH = static_cast<int>(std::min<long long>(chunk, fileH - y0));
        if (c.contains("terrain")) {
            const json& runs = c["terrain"];
            long long filled = 0;
            const long long total = static_cast<long long>(cw) * chH;
            for (const auto& run : runs.is_array() ? runs : json::array()) {
                if (!run.is_array() || run.size() != 2 || !run[1].is_number_integer()) {
                    in.warn.add("malformed terrain run skipped");
                    continue;
                }
                const long long n = run[1].get<long long>();
                for (long long k = 0; k < n && filled < total; ++k, ++filled)
                    in.terrain(static_cast<int>(x0 + filled % cw),
                               static_cast<int>(y0 + filled / cw), run[0]);
            }
            if (filled != total) in.warn.add("chunk terrain of the wrong length");
        }
        if (c.contains("items") && c["items"].is_array())
            for (const auto& j : c["items"]) items.push_back(&j);
    }
    for (const json* j : items) in.item(*j);
}

void readVersion3(const json& root, Loader& in) {
    const json& home = root.at("home");
    const auto size = mapSize(home);
    if (!size) throw std::runtime_error("home map size out of range");
    const auto [w, h] = *size;
    if (w != in.cat.mapW || h != in.cat.mapH) {
        in.offset = centringOffset(w, h, in.cat.mapW, in.cat.mapH);
        in.warn.add("a home map of another size was centred");
    }
    // Wild land first, so nothing can be loaded onto it.
    in.data.progress.stage = static_cast<int>(
        intField(home, "stage", 0, 0, static_cast<long long>(in.cat.stages.size()) - 1, in.warn));
    applyLand(in.data.world, in.cat, in.data.progress.stage);
    const json& runs = home.at("terrain");
    if (!runs.is_array()) throw std::runtime_error("home terrain is not a list");
    long long filled = 0;
    const long long total = static_cast<long long>(w) * h;
    for (const auto& run : runs) {
        if (!run.is_array() || run.size() != 2 || !run[1].is_number_integer()) {
            in.warn.add("malformed terrain run skipped");
            continue;
        }
        for (long long k = 0, n = run[1].get<long long>(); k < n && filled < total; ++k, ++filled)
            in.terrain(static_cast<int>(filled % w), static_cast<int>(filled / w), run[0]);
    }
    if (filled != total) in.warn.add("home terrain of the wrong length");
    for (const auto& j : listField(home, "items", in.warn)) in.item(j);
    // Wild tiles hold the base terrain only (a damaged file could say otherwise).
    World& world = in.data.world;
    for (int y = 0; y < world.height(); ++y)
        for (int x = 0; x < world.width(); ++x)
            if (world.isWild({x, y}) && world.terrainAt({x, y}) != in.cat.baseTerrain) {
                world.setTerrain({x, y}, in.cat.baseTerrain);
                in.warn.add("ground on wild land was cleared");
            }
}

void readProgress(const json& p, const Catalog& cat, SaveData& data, Warnings& warn) {
    Progress& pr = data.progress;
    const auto piece = [&](const std::string& id) -> std::optional<int> {
        if (const auto i = cat.findItem(id)) return i;
        if (const auto t = cat.findTerrain(id)) return static_cast<int>(cat.items.size()) + *t;
        return std::nullopt;
    };
    const auto mark = [&](const std::vector<int>& ids, std::vector<std::uint8_t>& items,
                          std::vector<std::uint8_t>& terrains) {
        for (const int i : ids) {
            if (std::cmp_less(i, cat.items.size()))
                items[static_cast<std::size_t>(i)] = 1;
            else
                terrains[static_cast<std::size_t>(i) - cat.items.size()] = 1;
        }
    };
    if (p.contains("unlocked")) {
        std::ranges::fill(pr.items, 0);
        std::ranges::fill(pr.terrain, 0);
        mark(knownIds(p["unlocked"], piece, warn, "piece"), pr.items, pr.terrain);
    }
    mark(knownIds(listField(p, "new", warn), piece, warn, "piece"), pr.newItems, pr.newTerrain);
    if (p.contains("frames")) {
        std::ranges::fill(pr.frames, 0);
        for (const int f : knownIds(
                 p["frames"], [&](const std::string& id) { return cat.findFrame(id); }, warn,
                 "frame"))
            pr.frames[static_cast<std::size_t>(f)] = 1;
    }
    const auto visitor = [&](const std::string& id) { return cat.findVisitor(id); };
    for (const int v : knownIds(listField(p, "clues", warn), visitor, warn, "visitor"))
        pr.clues[static_cast<std::size_t>(v)] = 1;
    for (const int v : knownIds(listField(p, "seen", warn), visitor, warn, "visitor"))
        if (std::ranges::find(data.seen, cat.visitors[static_cast<std::size_t>(v)].id) ==
            data.seen.end())
            data.seen.push_back(cat.visitors[static_cast<std::size_t>(v)].id);
    for (const int n : knownIds(
             listField(p, "nooks", warn), [&](const std::string& id) { return cat.findNook(id); },
             warn, "nook"))
        pr.nooks[static_cast<std::size_t>(n)] = 1;
    pr.harvests = static_cast<int>(intField(p, "harvests", 0, 0, tuning::kMaxHarvests, warn));
    pr.lastHarvestDay =
        static_cast<int>(intField(p, "last_harvest_day", -1, -1, tuning::kMaxCalendarDay, warn));
    if (p.contains("wishes") && p["wishes"].is_object()) {
        const json& w = p["wishes"];
        const auto wish = [&](const std::string& id) { return cat.findWish(id); };
        for (const int i : knownIds(listField(w, "done", warn), wish, warn, "wish")) {
            if (pr.wishes[static_cast<std::size_t>(i)].state == WishState::Done) continue;
            pr.wishes[static_cast<std::size_t>(i)].state = WishState::Done;
            pr.granted.push_back(i);
        }
        for (const int i : knownIds(listField(w, "open", warn), wish, warn, "wish")) {
            if (pr.wishes[static_cast<std::size_t>(i)].state != WishState::Waiting) continue;
            // Never more open than the tray holds; the rest wait to be offered again (QA2-05).
            if (std::cmp_greater_equal(pr.open.size(), tuning::kMaxOpenWishes)) {
                warn.add("more open wishes than the tray holds; the rest wait");
                continue;
            }
            pr.wishes[static_cast<std::size_t>(i)].state = WishState::Open;
            pr.open.push_back(i);
        }
        if (w.contains("snoozed") && w["snoozed"].is_object())
            for (const auto& [id, t] : w["snoozed"].items()) {
                const auto i = cat.findWish(id);
                if (i && t.is_number() && std::isfinite(t.get<double>()) &&
                    pr.wishes[static_cast<std::size_t>(*i)].state == WishState::Waiting)
                    pr.wishes[static_cast<std::size_t>(*i)].snoozedUntil =
                        std::max(0.0, t.get<double>());
            }
        pr.lastOffer = numField(w, "last_offer", 0.0, 0.0, kMaxPlayed, warn);
    }
}

// Old files said nothing about the calendar or progress; only these sections carry over.
void readLegacySections(const json& root, const Catalog& cat, SaveData& data) {
    if (root.contains("settings") && root["settings"].is_object()) {
        const auto& s = root["settings"];
        data.muted = s.contains("muted") && s["muted"].is_boolean() && s["muted"].get<bool>();
    }
    if (root.contains("journal") && root["journal"].is_array()) {
        for (const auto& id : root["journal"]) {
            if (!id.is_string()) continue;
            const auto s = id.get<std::string>();
            if (cat.findVisitor(s) && std::ranges::find(data.seen, s) == data.seen.end())
                data.seen.push_back(s);
        }
    }
}

} // namespace

TilePos centringOffset(int fromW, int fromH, int toW, int toH) {
    return {(toW - fromW) / 2, (toH - fromH) / 2};
}

std::string serialize(const SaveData& data, const Catalog& cat) {
    const World& w = data.world;
    const Progress& p = data.progress;
    json palette = json::array();
    for (const auto& t : cat.terrain) palette.push_back(t.id);
    json runs = json::array();
    int value = terrainValue(w, {0, 0});
    int count = 0;
    for (int y = 0; y < w.height(); ++y)
        for (int x = 0; x < w.width(); ++x) {
            const int v = terrainValue(w, {x, y});
            if (v != value) {
                runs.push_back({value, count});
                value = v;
                count = 0;
            }
            ++count;
        }
    runs.push_back({value, count});
    json items = json::array();
    // Row order, so the file does not depend on the order edits happened in.
    std::vector<const Item*> sorted;
    for (const Item& it : w.items()) sorted.push_back(&it);
    std::ranges::sort(sorted, [](const Item* a, const Item* b) {
        return a->pos.y != b->pos.y ? a->pos.y < b->pos.y : a->pos.x < b->pos.x;
    });
    for (const Item* it : sorted) {
        json j = {
            {"id", cat.items[it->type].id}, {"x", it->pos.x}, {"y", it->pos.y}, {"v", it->variant}};
        if (cat.items[it->type].growth.stages > 0) j["g"] = {it->stage, it->growth};
        items.push_back(std::move(j));
    }
    const auto ids = [&](const std::vector<std::uint8_t>& flags, const auto& defs) {
        json out = json::array();
        for (std::size_t i = 0; i < flags.size(); ++i)
            if (flags[i] != 0) out.push_back(defs[i].id);
        return out;
    };
    json unlocked = ids(p.items, cat.items);
    for (const auto& t : ids(p.terrain, cat.terrain)) unlocked.push_back(t);
    json fresh = ids(p.newItems, cat.items);
    for (const auto& t : ids(p.newTerrain, cat.terrain)) fresh.push_back(t);
    json open = json::array();
    for (const int i : p.open) open.push_back(cat.wishes[static_cast<std::size_t>(i)].id);
    json done = json::array();
    for (const int i : p.granted) done.push_back(cat.wishes[static_cast<std::size_t>(i)].id);
    json snoozed = json::object();
    for (std::size_t i = 0; i < p.wishes.size(); ++i)
        if (p.wishes[i].snoozedUntil >= 0) snoozed[cat.wishes[i].id] = p.wishes[i].snoozedUntil;
    json world = json::object();
    const WorldProgress& ws = data.worldState;
    if (ws.camera) world["camera"] = {{"at", {ws.camera->x, ws.camera->y}}, {"zoom", ws.zoom}};
    if (data.camera)
        world["home_view"] = {{"at", {data.camera->x, data.camera->y}}, {"zoom", data.zoom}};
    world["visited"] = ws.visited;
    const auto byRegion = [](const auto& lists) {
        json o = json::object();
        for (const auto& [region, entries] : lists)
            if (!entries.empty()) o[region] = entries;
        return o;
    };
    world["journal"] = byRegion(ws.found);
    world["seen"] = byRegion(ws.seen);
    world["flags"] = ws.flags;
    const json root = {
        {"version", kSaveVersion},
        {"name", data.name},
        {"free_build", data.freeBuild},
        {"created", data.created},
        {"played", data.played},
        {"clock", {{"t", data.clockTime}, {"pin", pinId(data.pin)}, {"day", data.day}}},
        {"season_pin", data.seasonPin < 0
                           ? std::string("auto")
                           : cat.seasons[static_cast<std::size_t>(data.seasonPin)].id},
        {"settings", {{"weather", weatherId(data.weather)}}},
        {"progress",
         {{"unlocked", std::move(unlocked)},
          {"frames", ids(p.frames, cat.frames)},
          {"wishes",
           {{"open", std::move(open)},
            {"done", std::move(done)},
            {"snoozed", std::move(snoozed)},
            {"last_offer", p.lastOffer}}},
          {"clues", ids(p.clues, cat.visitors)},
          {"seen", data.seen},
          {"nooks", ids(p.nooks, cat.nooks)},
          {"harvests", p.harvests},
          {"last_harvest_day", p.lastHarvestDay},
          {"new", std::move(fresh)}}},
        {"home",
         {{"map", {{"w", w.width()}, {"h", w.height()}}},
          {"palette", std::move(palette)},
          {"terrain", std::move(runs)},
          {"items", std::move(items)},
          {"stage", p.stage}}},
        {"world", std::move(world)},
    };
    return root.dump(1);
}

std::expected<SaveData, std::string> deserialize(std::string_view text, const Catalog& cat) {
    try {
        const json root = json::parse(text);
        if (!root.is_object()) return std::unexpected("save: not a JSON object");
        const json& vj = root.contains("version") ? root["version"] : json(0);
        const long long version = vj.is_number_integer() ? vj.get<long long>() : 0;
        if (version < 1) return std::unexpected("save: missing or invalid version");
        if (version > kSaveVersion)
            return std::unexpected("save: written by a newer version (" + std::to_string(version) +
                                   ")");
        SaveData data(World{cat}, cat);
        data.fromVersion = static_cast<int>(version);
        Loader in{cat, data, {}, {}, {}};
        if (version >= 3) {
            in.readPalette(root.at("home").at("palette"));
            readVersion3(root, in);
            if (root.contains("progress") && root["progress"].is_object())
                readProgress(root["progress"], cat, data, in.warn);
            data.name = stringField(root, "name", in.warn);
            data.freeBuild = boolField(root, "free_build", false, in.warn);
            data.created = stringField(root, "created", in.warn);
            data.played = numField(root, "played", 0.0, 0.0, kMaxPlayed, in.warn);
            // Timers measured against play time can never lie beyond it, so a damaged file
            // cannot keep wishes away for good (QA2-07).
            Progress& pr = data.progress;
            if (pr.lastOffer > data.played) {
                pr.lastOffer = data.played;
                in.warn.add("the last offer lay in the future and was brought back");
            }
            for (WishProgress& wp : pr.wishes)
                if (wp.snoozedUntil > data.played + tuning::kWishSnooze) {
                    wp.snoozedUntil = data.played + tuning::kWishSnooze;
                    in.warn.add("a snooze lay too far ahead and was shortened");
                }
            if (root.contains("season_pin") && root["season_pin"].is_string())
                data.seasonPin = cat.findSeason(root["season_pin"].get<std::string>()).value_or(-1);
            static const json kNone = json::object();
            const json& worldPart =
                root.contains("world") && root["world"].is_object() ? root["world"] : kNone;
            // A view: {"at": [x, y], "zoom"}; version 3 kept the home view under "camera".
            const auto readView = [&](const char* key, std::optional<Vec2>& at, float& zoom) {
                const json& cam =
                    worldPart.contains(key) && worldPart[key].is_object() ? worldPart[key] : kNone;
                if (cam.contains("at") && cam["at"].is_array() && cam["at"].size() == 2 &&
                    cam["at"][0].is_number() && cam["at"][1].is_number()) {
                    const Vec2 v{cam["at"][0].get<float>(), cam["at"][1].get<float>()};
                    if (std::isfinite(v.x) && std::isfinite(v.y)) at = v;
                    zoom = static_cast<float>(numField(cam, "zoom", 1.0, 0.1, 8.0, in.warn));
                }
            };
            WorldProgress& ws = data.worldState;
            if (version == 3) {
                readView("camera", data.camera, data.zoom);
            } else {
                readView("home_view", data.camera, data.zoom);
                readView("camera", ws.camera, ws.zoom);
                const auto strings = [&](const json& j, std::vector<std::string>& out) {
                    if (!j.is_array()) return;
                    for (const json& e : j)
                        if (e.is_string() &&
                            std::ranges::find(out, e.get<std::string>()) == out.end())
                            out.push_back(e.get<std::string>());
                };
                const auto lists = [&](const char* key, auto& out) {
                    if (!worldPart.contains(key) || !worldPart[key].is_object()) return;
                    for (const auto& [region, entries] : worldPart[key].items()) {
                        std::vector<std::string> v;
                        strings(entries, v);
                        if (!v.empty()) out.emplace_back(region, std::move(v));
                    }
                };
                if (worldPart.contains("visited")) strings(worldPart["visited"], ws.visited);
                if (worldPart.contains("flags")) strings(worldPart["flags"], ws.flags);
                lists("journal", ws.found);
                lists("seen", ws.seen);
            }
        } else {
            const auto size = mapSize(root);
            if (!size) return std::unexpected(size.error());
            const auto [fileW, fileH] = *size;
            // The first release's 20 x 20 map becomes the front corner of the home region (the
            // first land stage); the chunked format was already the 40 x 40 map.
            in.offset = version == 1 && fileW <= cat.mapW && fileH <= cat.mapH
                            ? TilePos{cat.mapW - fileW, cat.mapH - fileH}
                            : centringOffset(fileW, fileH, cat.mapW, cat.mapH);
            in.readPalette(root.at("palette"));
            if (version == 1)
                readVersion1(root, in, fileW, fileH);
            else
                readVersion2(root, in, fileW, fileH);
            if (fileW != cat.mapW || fileH != cat.mapH)
                data.warnings.push_back("a " + std::to_string(fileW) + "x" + std::to_string(fileH) +
                                        " map was placed on the " + std::to_string(cat.mapW) + "x" +
                                        std::to_string(cat.mapH) + " map");
            readLegacySections(root, cat, data);
        }
        if (root.contains("clock") && root["clock"].is_object()) {
            const auto& c = root["clock"];
            if (c.contains("t") && c["t"].is_number()) data.clockTime = c["t"].get<double>();
            if (!std::isfinite(data.clockTime) || data.clockTime < 0.0 || data.clockTime >= 1.0)
                data.clockTime = 0.2;
            if (c.contains("pin") && c["pin"].is_string())
                data.pin = parsePin(c["pin"].get<std::string>()).value_or(ClockPin::Auto);
            data.day = static_cast<int>(intField(c, "day", 0, 0, tuning::kMaxCalendarDay, in.warn));
        }
        if (root.contains("settings") && root["settings"].is_object()) {
            const auto& s = root["settings"];
            if (s.contains("weather") && s["weather"].is_string()) {
                const std::string w = s["weather"].get<std::string>();
                data.weather = w == "rain"    ? WeatherMode::Rain
                               : w == "clear" ? WeatherMode::Clear
                                              : WeatherMode::Natural;
            } else if (s.contains("rain") && s["rain"].is_boolean() && s["rain"].get<bool>()) {
                data.weather = WeatherMode::Rain;
            }
        }
        in.warn.flush(data.warnings);
        return data;
    } catch (const json::exception& e) {
        return std::unexpected(std::string("save: ") + e.what());
    } catch (const std::runtime_error& e) {
        return std::unexpected(std::string("save: ") + e.what());
    }
}

int saveFileVersion(std::string_view text) {
    try {
        const json root = json::parse(text);
        if (root.is_object() && root.contains("version") && root["version"].is_number_integer())
            return static_cast<int>(
                std::clamp<long long>(root["version"].get<long long>(), 0, 1 << 30));
    } catch (const json::exception&) {
        return 0;
    }
    return 0;
}

void migrateLegacy(SaveData& data, const Catalog& cat) {
    Progress& p = data.progress;
    p.unlock(cat.start);
    p.unlock(cat.legacy);
    // Wishes that only unlock pieces the player already has are quietly done.
    for (std::size_t i = 0; i < cat.wishes.size(); ++i) {
        const Reward& r = cat.wishes[i].reward;
        const bool onlyUnlocks = r.frame < 0 && r.clue < 0;
        const bool covered =
            std::ranges::all_of(r.items,
                                [&](int k) { return p.items[static_cast<std::size_t>(k)] != 0; }) &&
            std::ranges::all_of(r.terrain,
                                [&](int k) { return p.terrain[static_cast<std::size_t>(k)] != 0; });
        if (onlyUnlocks && covered && p.wishes[i].state != WishState::Done) {
            p.wishes[i].state = WishState::Done;
            p.granted.push_back(static_cast<int>(i));
        }
    }
    // Beds looked ripe in the old game, so they start ripe.
    World& w = data.world;
    for (std::size_t i = 0; i < w.items().size(); ++i) {
        const Growth& g = cat.items[w.items()[i].type].growth;
        if (g.stages > 0) w.setGrowth(i, g.stages - 1, 0.0f);
    }
    // Stages holding anything the player made open now, without their reveal.
    int stage = 0;
    for (int y = 0; y < w.height(); ++y)
        for (int x = 0; x < w.width(); ++x)
            if (w.hasGround({x, y}) &&
                (w.terrainAt({x, y}) != cat.baseTerrain || w.itemAt({x, y}) != nullptr))
                stage = std::max(stage, stageAt(cat, {x, y}));
    p.stage = stage;
    applyLand(w, cat, stage);
    data.day = 0;
    data.seasonPin = -1;
    data.fromVersion = kSaveVersion;
}

std::string worldSlug(std::string_view name, std::span<const std::string> taken) {
    constexpr std::string_view kCurly = "\xE2\x80\x99"; // U+2019, the typographic apostrophe
    std::string base;
    bool dash = false;
    for (std::size_t i = 0; i < name.size(); ++i) {
        const auto c = static_cast<unsigned char>(name[i]);
        if (c == '\'') continue;
        if (name.substr(i).starts_with(kCurly)) {
            i += kCurly.size() - 1;
            continue;
        }
        if (c < 0x80 && std::isalnum(c) != 0) {
            if (dash && !base.empty()) base += '-';
            dash = false;
            base += static_cast<char>(std::tolower(c));
        } else {
            dash = true;
        }
    }
    if (base.size() > 32) base.resize(32);
    while (!base.empty() && base.back() == '-') base.pop_back();
    if (base.empty()) base = "world";
    std::string slug = base;
    for (int n = 2; std::ranges::find(taken, slug) != taken.end(); ++n)
        slug = base + "-" + std::to_string(n);
    return slug;
}

std::string utcNow() {
    const auto now = std::chrono::floor<std::chrono::seconds>(std::chrono::system_clock::now());
    return std::format("{:%Y-%m-%dT%H:%M:%SZ}", now);
}

std::string postcardStem(std::string_view slug, std::time_t when) {
    std::tm t{};
#if defined(_WIN32)
    (void)localtime_s(&t, &when);
#else
    (void)localtime_r(&when, &t);
#endif
    return std::format("{}-{:04}{:02}{:02}-{:02}{:02}{:02}", slug, t.tm_year + 1900, t.tm_mon + 1,
                       t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec);
}

Profile parseProfile(std::string_view text) {
    Profile p;
    try {
        const json j = json::parse(text);
        if (!j.is_object()) return p;
        Warnings ignored; // a profile repairs itself quietly
        if (j.contains("volume") && j["volume"].is_object()) {
            const json& v = j["volume"];
            const auto vol = [&](const char* key, int def) {
                return static_cast<int>(intField(v, key, def, 0, 100, ignored)) / 5 * 5;
            };
            p.music = vol("music", p.music);
            p.effects = vol("effects", p.effects);
            p.ambience = vol("ambience", p.ambience);
        }
        p.muted = boolField(j, "muted", p.muted, ignored);
        if (j.contains("ui_scale") && j["ui_scale"].is_number()) {
            const double f = j["ui_scale"].get<double>();
            for (int i = 1; i < kUiScaleCount; ++i)
                if (std::abs(f - static_cast<double>(kUiScales[i])) < 1e-3) p.uiScale = i;
        }
        p.reduceMotion = boolField(j, "reduce_motion", p.reduceMotion, ignored);
        if (j.contains("chatter") && j["chatter"].is_string())
            p.chatty = j["chatter"].get<std::string>() != "quiet";
        p.grid = boolField(j, "grid", p.grid, ignored);
        if (j.contains("brush") && j["brush"].is_number_integer()) {
            const auto b = j["brush"].get<long long>();
            if (b == 1 || b == 3 || b == 5) p.brush = static_cast<int>(b);
        }
        p.vsync = boolField(j, "vsync", p.vsync, ignored);
        if (const std::string l = stringField(j, "look", ignored); !l.empty()) p.look = l;
        if (const std::string c = stringField(j, "clouds", ignored); !c.empty()) p.clouds = c;
        if (const std::string f = stringField(j, "frame", ignored); !f.empty()) p.frame = f;
        p.caption = boolField(j, "caption", p.caption, ignored);
        p.onboarded = boolField(j, "onboarded", p.onboarded, ignored);
        p.lastWorld = stringField(j, "last_world", ignored);
    } catch (const json::exception&) {
        return Profile{}; // a broken profile never stops the game: defaults
    }
    return p;
}

std::string serialize(const Profile& p) {
    json j = {{"version", 1},
              {"volume", {{"music", p.music}, {"effects", p.effects}, {"ambience", p.ambience}}},
              {"muted", p.muted},
              {"reduce_motion", p.reduceMotion},
              {"chatter", p.chatty ? "chatty" : "quiet"},
              {"grid", p.grid},
              {"brush", p.brush},
              {"vsync", p.vsync},
              {"look", p.look},
              {"clouds", p.clouds},
              {"frame", p.frame},
              {"caption", p.caption},
              {"onboarded", p.onboarded},
              {"last_world", p.lastWorld}};
    if (p.uiScale > 0 && p.uiScale < kUiScaleCount)
        j["ui_scale"] = kUiScales[p.uiScale];
    else
        j["ui_scale"] = "auto";
    return j.dump(1);
}

std::expected<void, std::string> writeFileAtomic(const std::filesystem::path& file,
                                                 std::string_view contents) {
    namespace fs = std::filesystem;
    std::error_code ec;
    if (file.has_parent_path()) fs::create_directories(file.parent_path(), ec);
    if (ec) return std::unexpected("cannot create " + file.parent_path().string());
    fs::path tmp = file;
    tmp += ".tmp";
    const auto fail = [&](const std::string& what) {
        const std::string why = std::strerror(errno);
        fs::remove(tmp, ec);
        return std::unexpected(what + " " + tmp.string() + ": " + why);
    };
    {
        const std::unique_ptr<std::FILE, int (*)(std::FILE*)> out(
            std::fopen(tmp.string().c_str(), "wb"), &std::fclose);
        if (!out) return fail("cannot open");
        if (std::fwrite(contents.data(), 1, contents.size(), out.get()) != contents.size() ||
            std::fflush(out.get()) != 0)
            return fail("cannot write");
#ifdef LC_HAVE_FSYNC
        if (::fsync(::fileno(out.get())) != 0) return fail("cannot flush");
#endif
    }
    fs::rename(tmp, file, ec);
    if (ec) {
        fs::remove(tmp, ec);
        return std::unexpected("cannot replace " + file.string() + ": " + ec.message());
    }
#ifdef LC_HAVE_FSYNC
    // The rename itself is only durable once the directory entry is flushed.
    const fs::path dir = file.has_parent_path() ? file.parent_path() : fs::path(".");
    if (const int fd = ::open(dir.string().c_str(), O_RDONLY | O_DIRECTORY); fd >= 0) {
        (void)::fsync(fd);
        (void)::close(fd);
    }
#endif
    return {};
}

} // namespace lc
