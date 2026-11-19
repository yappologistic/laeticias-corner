#pragma once
// The worlds in a save directory as the worlds screen shows them, without loading any of them:
// name, calendar day and sketchbook pages read from each save; names checked, made unique,
// changed and worlds deleted (docs/design/living-corner.md R10.3, R10.4). Pure logic.

#include <cstdint>
#include <expected>
#include <filesystem>
#include <span>
#include <string>
#include <string_view>
#include <vector>

namespace lc {

struct WorldSummary {
    std::string slug; // its folder
    std::string name;
    std::filesystem::file_time_type saved{}; // when its save was last written
    int day = 0;                             // calendar day
    int pages = 0;                           // visitors seen and nooks found
    bool readable = true; // false: damaged, or written by a newer version (shown, not opened)
};

// Every folder under `worldsDir` holding a world.json, the one saved last first.
[[nodiscard]] std::vector<WorldSummary> listWorlds(const std::filesystem::path& worldsDir);

// True when `slug` can only name a folder directly under the worlds folder: not empty, not "."
// or "..", no separators (a hand-edited profile's "last_world" never reaches outside it).
[[nodiscard]] bool plainFolderName(std::string_view slug);

inline constexpr int kWorldNameMax = 28; // characters, after trimming

// The name without leading and trailing spaces.
[[nodiscard]] std::string trimName(std::string_view name);
enum class NameProblem : std::uint8_t { None, Empty, TooLong, Taken };
// Checks a trimmed name against the other worlds (`self` is the world being renamed, if any).
[[nodiscard]] NameProblem checkName(std::string_view name, std::span<const WorldSummary> worlds,
                                    std::string_view self = {});
// `base`, else "base 2", "base 3"... whichever no world has yet.
[[nodiscard]] std::string freshName(std::string_view base, std::span<const WorldSummary> worlds);

// Gives the world saved in `file` a new name, written atomically; a file it cannot read (or from
// a newer version) is left as it is.
[[nodiscard]] std::expected<void, std::string> renameWorld(const std::filesystem::path& file,
                                                           std::string_view name);
// Removes a world's folder with everything in it.
[[nodiscard]] std::expected<void, std::string> deleteWorld(const std::filesystem::path& dir);

} // namespace lc
