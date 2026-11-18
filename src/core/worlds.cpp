#include "core/worlds.hpp"

#include "core/save.hpp"

#include <nlohmann/json.hpp>

#include <algorithm>

namespace lc {

using nlohmann::json;

namespace {

constexpr std::string_view kWorldFileName = "world.json";

int codepoints(std::string_view s) {
    return static_cast<int>(std::ranges::count_if(
        s, [](char c) { return (static_cast<unsigned char>(c) & 0xC0) != 0x80; }));
}

} // namespace

std::vector<WorldSummary> listWorlds(const std::filesystem::path& worldsDir) {
    namespace fs = std::filesystem;
    std::vector<WorldSummary> out;
    std::error_code ec;
    for (auto it = fs::directory_iterator(worldsDir, ec); !ec && it != fs::directory_iterator();
         it.increment(ec)) {
        const fs::path file = it->path() / kWorldFileName;
        if (!it->is_directory(ec) || !fs::is_regular_file(file, ec)) continue;
        WorldSummary w;
        w.slug = it->path().filename().string();
        w.name = w.slug;
        w.saved = fs::last_write_time(file, ec);
        w.readable = false;
        if (const auto text = readTextFile(file)) {
            try {
                const json root = json::parse(*text);
                const bool known = root.is_object() && root.contains("version") &&
                                   root["version"].is_number_integer() &&
                                   root["version"].get<long long>() <= kSaveVersion;
                if (known) {
                    w.readable = true;
                    if (root.contains("name") && root["name"].is_string() &&
                        !root["name"].get<std::string>().empty())
                        w.name = root["name"].get<std::string>();
                    if (root.contains("clock") && root["clock"].is_object() &&
                        root["clock"].contains("day") && root["clock"]["day"].is_number_integer())
                        w.day = static_cast<int>(std::clamp<long long>(
                            root["clock"]["day"].get<long long>(), 0, 1'000'000));
                    if (root.contains("progress") && root["progress"].is_object()) {
                        const json& p = root["progress"];
                        for (const char* key : {"seen", "nooks"})
                            if (p.contains(key) && p[key].is_array())
                                w.pages += static_cast<int>(p[key].size());
                    }
                }
            } catch (const json::exception&) {
                w.readable = false;
            }
        }
        out.push_back(std::move(w));
    }
    std::ranges::sort(out, [](const WorldSummary& a, const WorldSummary& b) {
        return a.saved != b.saved ? a.saved > b.saved : a.slug < b.slug;
    });
    return out;
}

std::string trimName(std::string_view name) {
    const auto first = name.find_first_not_of(" \t");
    if (first == std::string_view::npos) return {};
    const auto last = name.find_last_not_of(" \t");
    return std::string(name.substr(first, last - first + 1));
}

NameProblem checkName(std::string_view name, std::span<const WorldSummary> worlds,
                      std::string_view self) {
    if (name.empty()) return NameProblem::Empty;
    if (codepoints(name) > kWorldNameMax) return NameProblem::TooLong;
    for (const WorldSummary& w : worlds)
        if (w.slug != self && w.name == name) return NameProblem::Taken;
    return NameProblem::None;
}

std::string freshName(std::string_view base, std::span<const WorldSummary> worlds) {
    std::string name(base);
    for (int n = 2; checkName(name, worlds) == NameProblem::Taken; ++n)
        name = std::string(base) + " " + std::to_string(n);
    return name;
}

std::expected<void, std::string> renameWorld(const std::filesystem::path& file,
                                             std::string_view name) {
    const auto text = readTextFile(file);
    if (!text) return std::unexpected(text.error());
    try {
        json root = json::parse(*text);
        if (!root.is_object() || !root.contains("version") ||
            !root["version"].is_number_integer() || root["version"].get<long long>() > kSaveVersion)
            return std::unexpected("not a world this version can change");
        root["name"] = std::string(name);
        // A new name is not a new visit: the world keeps its place in the list.
        std::error_code ec;
        const auto when = std::filesystem::last_write_time(file, ec);
        auto r = writeFileAtomic(file, root.dump(1));
        if (r && !ec) std::filesystem::last_write_time(file, when, ec);
        return r;
    } catch (const json::exception& e) {
        return std::unexpected(std::string("unreadable: ") + e.what());
    }
}

std::expected<void, std::string> deleteWorld(const std::filesystem::path& dir) {
    std::error_code ec;
    std::filesystem::remove_all(dir, ec);
    if (ec) return std::unexpected("cannot delete " + dir.string() + ": " + ec.message());
    return {};
}

} // namespace lc
