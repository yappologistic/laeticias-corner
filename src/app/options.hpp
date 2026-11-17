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

struct Size {
    int w = 0;
    int h = 0;
};

struct Options {
    bool headless = false;
    std::optional<Size> size; // window size; unset: sized to the display (1280x800 headless)
    std::optional<std::filesystem::path> script;
    std::optional<std::filesystem::path> saveDir;
    std::optional<std::filesystem::path> assetsDir;
    std::optional<std::uint64_t> seed;
    std::string renderer; // SDL render driver; empty = software when headless, else SDL's choice
    int frames = 0;       // 0 = run until quit
    std::optional<std::filesystem::path> audioOut; // capture the mix to a WAV file
    bool bench = false;
    std::optional<Size> map; // bench: map size instead of the catalog's
    float density = 0.5f;    // bench: share of tiles filled around the camera
    double budgetMs = 0;     // bench: fail when update + draw averages more than this
    double soak = 0;         // seconds of play to run checking that memory stays flat (0: no)
    bool help = false;
};

[[nodiscard]] std::expected<Options, std::string>
parseOptions(std::span<const std::string_view> args);
[[nodiscard]] std::string_view usage();

} // namespace lc
