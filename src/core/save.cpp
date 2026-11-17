#include "core/save.hpp"

#include "core/edit.hpp"

#include <nlohmann/json.hpp>

#include <cerrno>
#include <cmath>
#include <cstdio>
#include <cstring>
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

int terrainValue(const World& w, TilePos p) {
    const int t = w.terrainAt(p);
    return t == kNoGround ? -1 : t;
}

bool chunkIsBlank(const World& w, const Catalog& cat, int cx, int cy) {
    if (!w.chunkItems(cx, cy).empty()) return false;
    const TileRect r =
        TileRect{cx * kChunk, cy * kChunk, (cx + 1) * kChunk, (cy + 1) * kChunk}.clipped(
            w.bounds());
    for (int y = r.y0; y < r.y1; ++y)
        for (int x = r.x0; x < r.x1; ++x)
            if (w.terrainAt({x, y}) != cat.baseTerrain) return false;
    return true;
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
        const Item it = makeItem(cat, *type, static_cast<int>(vj.get<long long>()),
                                 {*x + offset.x, *y + offset.y});
        if (canPlace(data.world, cat, it) != PlaceResult::Ok) {
            warn.add("item '" + id + "' no longer fits and was skipped");
            return;
        }
        data.world.addItem(it);
    }
};

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
    const json items = root.value("items", json::array());
    if (!items.is_array()) throw std::runtime_error("items is not a list");
    for (const auto& j : items) in.item(j);
}

void readVersion2(const json& root, Loader& in, int fileW, int fileH) {
    const int chunk = root.value("chunk", kChunk);
    if (chunk < 1 || chunk > 1024) throw std::runtime_error("chunk size out of range");
    const std::string base = root.value("base", std::string(kSaveBaseBlank));
    if (base != kSaveBaseBlank) throw std::runtime_error("unknown base '" + base + "'");
    const json chunks = root.value("chunks", json::array());
    if (!chunks.is_array()) throw std::runtime_error("chunks is not a list");
    for (const auto& c : chunks) {
        if (!c.is_object() || !c.contains("x") || !c.contains("y") || !c["x"].is_number_integer() ||
            !c["y"].is_number_integer()) {
            in.warn.add("malformed chunk skipped");
            continue;
        }
        const long long cx = c["x"].get<long long>();
        const long long cy = c["y"].get<long long>();
        const long long x0 = cx * chunk;
        const long long y0 = cy * chunk;
        if (cx < 0 || cy < 0 || x0 >= fileW || y0 >= fileH) {
            in.warn.add("chunk outside the map skipped");
            continue;
        }
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
            for (const auto& j : c["items"]) in.item(j);
    }
}

} // namespace

TilePos centringOffset(int fromW, int fromH, int toW, int toH) {
    return {(toW - fromW) / 2, (toH - fromH) / 2};
}

std::string serialize(const SaveData& data, const Catalog& cat) {
    const World& w = data.world;
    json palette = json::array();
    for (const auto& t : cat.terrain) palette.push_back(t.id);
    json chunks = json::array();
    for (int cy = 0; cy < w.chunksY(); ++cy) {
        for (int cx = 0; cx < w.chunksX(); ++cx) {
            if (!w.chunkTouched(cx, cy) || chunkIsBlank(w, cat, cx, cy)) continue;
            const TileRect r =
                TileRect{cx * kChunk, cy * kChunk, (cx + 1) * kChunk, (cy + 1) * kChunk}.clipped(
                    w.bounds());
            json runs = json::array();
            int value = terrainValue(w, {r.x0, r.y0});
            int count = 0;
            for (int y = r.y0; y < r.y1; ++y) {
                for (int x = r.x0; x < r.x1; ++x) {
                    const int v = terrainValue(w, {x, y});
                    if (v != value) {
                        runs.push_back({value, count});
                        value = v;
                        count = 0;
                    }
                    ++count;
                }
            }
            runs.push_back({value, count});
            json items = json::array();
            for (const std::uint32_t i : w.chunkItems(cx, cy)) {
                const Item& it = w.items()[i];
                items.push_back({{"id", cat.items[it.type].id},
                                 {"x", it.pos.x},
                                 {"y", it.pos.y},
                                 {"v", it.variant}});
            }
            chunks.push_back(
                {{"x", cx}, {"y", cy}, {"terrain", std::move(runs)}, {"items", std::move(items)}});
        }
    }
    const json root = {
        {"version", kSaveVersion},
        {"map", {{"w", w.width()}, {"h", w.height()}}},
        {"chunk", kChunk},
        {"base", kSaveBaseBlank},
        {"palette", std::move(palette)},
        {"chunks", std::move(chunks)},
        {"clock", {{"t", data.clockTime}, {"pin", pinId(data.pin)}}},
        {"settings", {{"rain", data.rain}, {"muted", data.muted}}},
        {"journal", data.journal},
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
        const auto size = mapSize(root);
        if (!size) return std::unexpected(size.error());
        const auto [fileW, fileH] = *size;

        SaveData data(World{cat});
        Loader in{cat, data, centringOffset(fileW, fileH, cat.mapW, cat.mapH), {}, {}};
        in.readPalette(root.at("palette"));
        if (version == 1)
            readVersion1(root, in, fileW, fileH);
        else
            readVersion2(root, in, fileW, fileH);
        if (fileW != cat.mapW || fileH != cat.mapH)
            data.warnings.push_back("a " + std::to_string(fileW) + "x" + std::to_string(fileH) +
                                    " map was centred on the " + std::to_string(cat.mapW) + "x" +
                                    std::to_string(cat.mapH) + " map");
        in.warn.flush(data.warnings);

        if (root.contains("clock") && root["clock"].is_object()) {
            const auto& c = root["clock"];
            if (c.contains("t") && c["t"].is_number()) data.clockTime = c["t"].get<double>();
            if (!std::isfinite(data.clockTime) || data.clockTime < 0.0 || data.clockTime >= 1.0)
                data.clockTime = 0.2;
            if (c.contains("pin") && c["pin"].is_string())
                data.pin = parsePin(c["pin"].get<std::string>()).value_or(ClockPin::Auto);
        }
        if (root.contains("settings") && root["settings"].is_object()) {
            const auto& s = root["settings"];
            data.rain = s.contains("rain") && s["rain"].is_boolean() && s["rain"].get<bool>();
            data.muted = s.contains("muted") && s["muted"].is_boolean() && s["muted"].get<bool>();
        }
        if (root.contains("journal") && root["journal"].is_array()) {
            for (const auto& id : root["journal"]) {
                if (!id.is_string()) continue;
                const auto s = id.get<std::string>();
                if (cat.findVisitor(s) && std::ranges::find(data.journal, s) == data.journal.end())
                    data.journal.push_back(s);
            }
        }
        return data;
    } catch (const json::exception& e) {
        return std::unexpected(std::string("save: ") + e.what());
    } catch (const std::runtime_error& e) {
        return std::unexpected(std::string("save: ") + e.what());
    }
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
