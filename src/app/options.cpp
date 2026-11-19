#include "app/options.hpp"

#include "render/gpu/look.hpp"

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
           "  --size WxH          window size in pixels (default: fitted to the display, "
           "1280x800 headless)\n"
           "  --script FILE       drive the game with an input script (implies --headless)\n"
           "  --save-dir DIR      where the corner and photos are saved (env LAETICIA_SAVE_DIR)\n"
           "  --assets DIR        asset directory (env LAETICIA_ASSETS_DIR)\n"
           "  --seed N            random seed (default: time, or 1 when headless)\n"
           "  --frames N          quit after N frames\n"
           "  --renderer NAME     SDL render driver (headless default: software)\n"
           "  --quality LOOK      classic | low | medium | high (default: the settings'; any\n"
           "                      but classic asks for SDL's gpu driver, else falls back)\n"
           "  --audio-out FILE    write the mix to a 32-bit float WAV instead of a device "
           "(implies --headless)\n"
           "  --bench             fill the map and report frame timings (implies --headless)\n"
           "  --map WxH           bench: map size (default: the catalog's)\n"
           "  --density D         bench: share of tiles filled near the camera, 0..1 (0.5)\n"
           "  --budget-ms MS      bench: exit 3 when update + draw averages more than MS\n"
           "  --bench-case TEXT   bench: only the cases whose name contains TEXT\n"
           "  --streamed          headless: build the world's cells and pages over frames as the\n"
           "                      windowed game does (a headless run builds them at once, so its\n"
           "                      screenshots are the same every time)\n"
           "  --soak SECONDS      run that much busy play fast and exit 3 if memory grows "
           "(implies --headless)\n"
           "  --perf-log FILE     write per-frame timings and counters to FILE as CSV\n"
           "  --gpu-sync          wait for the GPU every frame so its time can be measured\n"
           "  --benchmark         open a window and play a fixed 75 s tour, then show and save\n"
           "                      frame-time results beside the save (for a person to run)\n"
           "  --front-door        start at the title screen even when headless (tests)\n"
           "  --focus F           city life: the active area around F (x,y | layer:node |\n"
           "                      forum | agora | terrace | district:<region>/<name>)\n"
           "  --life-dump FILE    write city-life dumps of the area round --focus and exit\n"
           "                      (one hour: FILE; several: FILE_hhmm.json)\n"
           "  --life-hours H,..   game hours of the dumps (default 10)\n"
           "  --life-day N        calendar day of the dumps (default 1)\n"
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
        } else if (a == "--gpu-sync") {
            o.gpuSync = true;
        } else if (a == "--benchmark") {
            o.benchmark = o.gpuSync = true;
        } else if (a == "--front-door") {
            o.frontDoor = true;
        } else if (a == "--perf-log") {
            const auto v = value();
            if (!v) return std::unexpected(v.error());
            o.perfLog = std::filesystem::path(*v);
        } else if (a == "--help" || a == "-h") {
            o.help = true;
        } else if (a == "--size" || a == "--map") {
            const auto v = value();
            if (!v) return std::unexpected(v.error());
            const auto x = v->find('x');
            Size size;
            const bool ok = x != std::string_view::npos && parseNumber(v->substr(0, x), size.w) &&
                            parseNumber(v->substr(x + 1), size.h);
            if (a == "--size") {
                if (!ok || size.w < 320 || size.h < 240 || size.w > 8192 || size.h > 8192)
                    return std::unexpected("--size expects WxH between 320x240 and 8192x8192");
                o.size = size;
            } else {
                if (!ok || size.w < 1 || size.h < 1 || size.w > 4096 || size.h > 4096 ||
                    static_cast<long long>(size.w) * size.h > (1LL << 22))
                    return std::unexpected("--map expects WxH within 4096x4096 and 4M tiles");
                o.map = size;
            }
        } else if (a == "--density") {
            const auto v = value();
            if (!v || !parseNumber(*v, o.density) || o.density < 0 || o.density > 1)
                return std::unexpected("--density expects a number from 0 to 1");
        } else if (a == "--streamed") {
            o.streamed = true;
        } else if (a == "--bench-case") {
            const auto v = value();
            if (!v) return std::unexpected("--bench-case expects a case name");
            o.benchCase = *v;
        } else if (a == "--budget-ms") {
            const auto v = value();
            if (!v || !parseNumber(*v, o.budgetMs) || o.budgetMs <= 0)
                return std::unexpected("--budget-ms expects a positive number");
        } else if (a == "--soak") {
            const auto v = value();
            if (!v || !parseNumber(*v, o.soak) || o.soak <= 0)
                return std::unexpected("--soak expects a positive number of seconds");
            o.headless = true;
        } else if (a == "--audio-out") {
            const auto v = value();
            if (!v) return std::unexpected(v.error());
            o.audioOut = std::filesystem::path(*v);
            o.headless = true;
        } else if (a == "--script") {
            const auto v = value();
            if (!v) return std::unexpected(v.error());
            o.script = std::filesystem::path(*v);
            o.headless = true;
            std::error_code ec;
            if (std::filesystem::is_directory(*o.script, ec))
                return std::unexpected("--script expects a file, not a directory");
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
        } else if (a == "--quality") {
            const auto v = value();
            if (!v || !gpu::parseQuality(*v))
                return std::unexpected("--quality expects classic, low, medium or high");
            o.quality = std::string(*v);
        } else if (a == "--focus") {
            const auto v = value();
            if (!v || v->empty()) return std::unexpected("--focus expects a place");
            o.focus = std::string(*v);
        } else if (a == "--life-dump") {
            const auto v = value();
            if (!v) return std::unexpected(v.error());
            o.lifeDump = std::filesystem::path(*v);
            o.headless = true;
        } else if (a == "--life-hours") {
            const auto v = value();
            if (!v || v->empty()) return std::unexpected("--life-hours expects hours");
            o.lifeHours = std::string(*v);
        } else if (a == "--life-day") {
            const auto v = value();
            if (!v || !parseNumber(*v, o.lifeDay) || o.lifeDay < 0)
                return std::unexpected("--life-day expects a day");
        } else if (a == "--frames") {
            const auto v = value();
            if (!v || !parseNumber(*v, o.frames) || o.frames < 0)
                return std::unexpected("--frames expects a non-negative number");
        } else {
            return std::unexpected("unknown option " + std::string(a));
        }
    }
    // A look above Classic is drawn by SDL's gpu driver.
    if (!o.quality.empty() && o.quality != "classic" && o.renderer.empty()) o.renderer = "gpu";
    // The windowless GPU driver never really presents, so without a wait for the GPU its queue
    // of frames (and the process's memory) grows without bound.
    if (o.headless && !o.renderer.empty() && o.renderer != "software") o.gpuSync = true;
    return o;
}

} // namespace lc
