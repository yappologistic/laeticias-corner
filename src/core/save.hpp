#pragma once
// Versioned JSON save files with atomic writes and graceful handling of bad input.

#include "core/catalog.hpp"
#include "core/clock.hpp"
#include "core/world.hpp"

#include <expected>
#include <filesystem>
#include <string>
#include <utility>
#include <vector>

namespace lc {

inline constexpr int kSaveVersion = 1;

struct SaveData {
    explicit SaveData(World w) : world(std::move(w)) {}

    World world;
    double clockTime = 0.2;
    ClockPin pin = ClockPin::Auto;
    bool rain = false;
    bool muted = false;
    std::vector<std::string> journal;  // visitor ids seen so far
    std::vector<std::string> warnings; // entries skipped because the catalog no longer has them
};

[[nodiscard]] std::string serialize(const SaveData& data, const Catalog& cat);
// Rejects malformed or newer files; tolerates missing optional fields and unknown ids.
[[nodiscard]] std::expected<SaveData, std::string> deserialize(std::string_view text,
                                                               const Catalog& cat);

// Writes to a temporary sibling and renames it over the target, so a crash never leaves a
// half-written save behind.
[[nodiscard]] std::expected<void, std::string> writeFileAtomic(const std::filesystem::path& file,
                                                               std::string_view contents);

} // namespace lc
