#pragma once
// Command-line options.

#include <cstdint>
#include <expected>
#include <filesystem>
#include <optional>
#include <span>
#include <string>
#include <string_view>

namespace lc {

struct Options {
    bool headless = false;
    int width = 1280;
    int height = 800;
    std::optional<std::filesystem::path> script;
    std::optional<std::filesystem::path> saveDir;
    std::optional<std::filesystem::path> assetsDir;
    std::optional<std::uint64_t> seed;
    std::string renderer; // SDL render driver; empty = software when headless, else SDL's choice
    int frames = 0;       // 0 = run until quit
    bool bench = false;
    bool help = false;
};

[[nodiscard]] std::expected<Options, std::string>
parseOptions(std::span<const std::string_view> args);
[[nodiscard]] std::string_view usage();

} // namespace lc
