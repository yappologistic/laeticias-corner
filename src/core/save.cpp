#include "core/save.hpp"

#include "core/edit.hpp"

#include <nlohmann/json.hpp>

#include <fstream>

namespace lc {

using nlohmann::json;

std::string serialize(const SaveData& data, const Catalog& cat) {
    const World& w = data.world;
    json terrain = json::array();
    for (int y = 0; y < w.height(); ++y)
        for (int x = 0; x < w.width(); ++x) terrain.push_back(w.terrainAt({x, y}));
    json palette = json::array();
    for (const auto& t : cat.terrain) palette.push_back(t.id);
    json items = json::array();
    for (const Item& it : w.items()) {
        items.push_back(
            {{"id", cat.items[it.type].id}, {"x", it.pos.x}, {"y", it.pos.y}, {"v", it.variant}});
    }
    const json root = {
        {"version", kSaveVersion},
        {"map", {{"w", w.width()}, {"h", w.height()}}},
        {"palette", std::move(palette)},
        {"terrain", std::move(terrain)},
        {"items", std::move(items)},
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
        const int version = root.value("version", 0);
        if (version < 1) return std::unexpected("save: missing or invalid version");
        if (version > kSaveVersion)
            return std::unexpected("save: written by a newer version (" + std::to_string(version) +
                                   ")");

        SaveData data(World{cat});
        World& w = data.world;
        const auto& map = root.at("map");
        if (map.at("w").get<int>() != w.width() || map.at("h").get<int>() != w.height())
            return std::unexpected("save: map size does not match the catalog");

        const auto& palette = root.at("palette");
        std::vector<int> remap;
        for (const auto& id : palette) {
            const auto idx = cat.findTerrain(id.get<std::string>());
            if (!idx) data.warnings.push_back("unknown terrain '" + id.get<std::string>() + "'");
            remap.push_back(idx.value_or(cat.baseTerrain));
        }
        const auto& terrain = root.at("terrain");
        if (!terrain.is_array() ||
            terrain.size() != static_cast<std::size_t>(w.width() * w.height()))
            return std::unexpected("save: terrain has the wrong size");
        for (int y = 0; y < w.height(); ++y) {
            for (int x = 0; x < w.width(); ++x) {
                const int v = terrain[static_cast<std::size_t>(y * w.width() + x)].get<int>();
                if (v < 0 || static_cast<std::size_t>(v) >= remap.size())
                    return std::unexpected("save: terrain index out of range");
                w.setTerrain({x, y}, remap[static_cast<std::size_t>(v)]);
            }
        }

        for (const auto& j : root.value("items", json::array())) {
            const auto id = j.at("id").get<std::string>();
            const auto type = cat.findItem(id);
            if (!type) {
                data.warnings.push_back("unknown item '" + id + "'");
                continue;
            }
            const auto& def = cat.items[static_cast<std::size_t>(*type)];
            const int variant = j.value("v", 0);
            if (variant < 0 || variant >= def.count) {
                data.warnings.push_back("item '" + id + "' has an invalid variant");
                continue;
            }
            const Item item =
                makeItem(cat, *type, variant, {j.at("x").get<int>(), j.at("y").get<int>()});
            if (canPlace(w, cat, item) != PlaceResult::Ok) {
                data.warnings.push_back("item '" + id + "' no longer fits");
                continue;
            }
            w.addItem(item);
        }

        if (root.contains("clock")) {
            const auto& c = root["clock"];
            data.clockTime = c.value("t", data.clockTime);
            if (!(data.clockTime >= 0.0 && data.clockTime < 1.0)) data.clockTime = 0.2;
            data.pin = parsePin(c.value("pin", std::string("auto"))).value_or(ClockPin::Auto);
        }
        if (root.contains("settings")) {
            data.rain = root["settings"].value("rain", false);
            data.muted = root["settings"].value("muted", false);
        }
        for (const auto& id : root.value("journal", json::array())) {
            const auto s = id.get<std::string>();
            if (cat.findVisitor(s)) data.journal.push_back(s);
        }
        return data;
    } catch (const json::exception& e) {
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
    {
        std::ofstream out(tmp, std::ios::binary | std::ios::trunc);
        if (!out) return std::unexpected("cannot open " + tmp.string());
        out.write(contents.data(), static_cast<std::streamsize>(contents.size()));
        out.flush();
        if (!out) return std::unexpected("cannot write " + tmp.string());
    }
    fs::rename(tmp, file, ec);
    if (ec) {
        fs::remove(tmp, ec);
        return std::unexpected("cannot replace " + file.string());
    }
    return {};
}

} // namespace lc
