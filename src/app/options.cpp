#include "app/options.hpp"

#include <charconv>

namespace lc {
namespace {

template <typename T>
bool parseNumber(std::string_view s, T& out) {
    const auto [p, ec] = std::from_chars(s.data(), s.data() + s.size(), out);
    return ec == std::errc{} && p == s.data() + s.size();
}

} // namespace

std::string_view usage() {
    return "usage: laeticias-corner [options]\n"
           "  --headless          no visible window, no sound device (offscreen video, dummy "
           "audio)\n"
           "  --size WxH          window size in pixels (default 1280x800)\n"
           "  --script FILE       drive the game with an input script (implies --headless)\n"
           "  --save-dir DIR      where the corner and photos are saved (env LAETICIA_SAVE_DIR)\n"
           "  --assets DIR        asset directory (env LAETICIA_ASSETS_DIR)\n"
           "  --seed N            random seed (default: time, or 1 when headless)\n"
           "  --frames N          quit after N frames\n"
           "  --renderer NAME     SDL render driver (headless default: software)\n"
           "  --bench             fill the map and report frame timings (implies --headless)\n"
           "  --help              show this text\n";
}

std::expected<Options, std::string> parseOptions(std::span<const std::string_view> args) {
    Options o;
    for (std::size_t i = 0; i < args.size(); ++i) {
        const std::string_view a = args[i];
        const auto value = [&]() -> std::expected<std::string_view, std::string> {
            if (i + 1 >= args.size()) return std::unexpected(std::string(a) + " needs a value");
            return args[++i];
        };
        if (a == "--headless") {
            o.headless = true;
        } else if (a == "--bench") {
            o.bench = o.headless = true;
        } else if (a == "--help" || a == "-h") {
            o.help = true;
        } else if (a == "--size") {
            const auto v = value();
            if (!v) return std::unexpected(v.error());
            const auto x = v->find('x');
            if (x == std::string_view::npos || !parseNumber(v->substr(0, x), o.width) ||
                !parseNumber(v->substr(x + 1), o.height) || o.width < 320 || o.height < 240 ||
                o.width > 8192 || o.height > 8192)
                return std::unexpected("--size expects WxH between 320x240 and 8192x8192");
        } else if (a == "--script") {
            const auto v = value();
            if (!v) return std::unexpected(v.error());
            o.script = std::filesystem::path(*v);
            o.headless = true;
        } else if (a == "--save-dir") {
            const auto v = value();
            if (!v) return std::unexpected(v.error());
            o.saveDir = std::filesystem::path(*v);
        } else if (a == "--assets") {
            const auto v = value();
            if (!v) return std::unexpected(v.error());
            o.assetsDir = std::filesystem::path(*v);
        } else if (a == "--seed") {
            const auto v = value();
            std::uint64_t seed = 0;
            if (!v || !parseNumber(*v, seed)) return std::unexpected("--seed expects a number");
            o.seed = seed;
        } else if (a == "--renderer") {
            const auto v = value();
            if (!v || v->empty()) return std::unexpected("--renderer expects a driver name");
            o.renderer = std::string(*v);
        } else if (a == "--frames") {
            const auto v = value();
            if (!v || !parseNumber(*v, o.frames) || o.frames < 0)
                return std::unexpected("--frames expects a non-negative number");
        } else {
            return std::unexpected("unknown option " + std::string(a));
        }
    }
    return o;
}

} // namespace lc
