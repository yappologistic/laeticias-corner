#include "worldview/script.hpp"

#include "core/clock.hpp"

#include <charconv>
#include <cmath>
#include <utility>

namespace lc::worldview {
namespace {

std::optional<double> number(std::string_view s) {
    double v = 0;
    const auto [p, ec] = std::from_chars(s.data(), s.data() + s.size(), v);
    if (ec != std::errc{} || p != s.data() + s.size() || !std::isfinite(v)) return std::nullopt;
    return v;
}

// Carriage returns count as blanks: a script checked out on Windows ends its lines with them.
bool blank(char c) {
    return c == ' ' || c == '\t' || c == '\r';
}

std::vector<std::string> words(std::string_view line) {
    std::vector<std::string> out;
    std::size_t i = 0;
    while (i < line.size()) {
        while (i < line.size() && blank(line[i])) ++i;
        std::size_t j = i;
        while (j < line.size() && !blank(line[j])) ++j;
        if (j > i) out.emplace_back(line.substr(i, j - i));
        i = j;
    }
    return out;
}

} // namespace

std::optional<double> parseClock(std::string_view s) {
    if (s == "day") return phaseCentre(Phase::Day);
    if (s == "dusk") return phaseCentre(Phase::Dusk);
    if (s == "night") return phaseCentre(Phase::Night);
    if (s == "dawn") return phaseCentre(Phase::Dawn);
    const auto v = number(s);
    if (!v || *v < 0 || *v > 1) return std::nullopt;
    return v;
}

std::optional<float> parseZoom(std::string_view s) {
    if (s == "overview") return 0.0f;
    const auto v = number(s);
    if (!v || *v <= 0 || *v > 8) return std::nullopt;
    return static_cast<float>(*v);
}

std::string_view viewerUsage() {
    return "laeticias-world: draws the prebuilt world headless (never a window unless asked)\n"
           "  --assets DIR        assets directory\n"
           "  --size WxH          window size (default 1280x800)\n"
           "  --goto REGION|X,Y   start at a region's marker or a grid tile\n"
           "  --zoom Z            overview, 0.25, 0.5, 1, 2 or 3\n"
           "  --clock T           day, dusk, night, dawn or 0..1\n"
           "  --shot FILE         save one settled frame as PNG\n"
           "  --script FILE       run a viewer script (see src/worldview/script.hpp)\n"
           "  --shots DIR         where script shots go\n"
           "  --renderer NAME     SDL render driver; opengl uses the windowless offscreen driver\n"
           "  --bench [CASE]      run the bench cases (opengl), exit 3 over budget, 77 without "
           "GPU\n"
           "  --no-budget         the bench reports without failing (sanitizer builds)\n"
           "  --report            print what draws without art\n"
           "  --interactive       open a window to fly around (for a person, never automation)\n";
}

std::expected<ViewerOptions, std::string>
parseViewerOptions(std::span<const std::string_view> args) {
    ViewerOptions o;
    for (std::size_t i = 0; i < args.size(); ++i) {
        const std::string_view a = args[i];
        const auto value = [&]() -> std::expected<std::string_view, std::string> {
            if (i + 1 >= args.size()) return std::unexpected(std::string(a) + " needs a value");
            return args[++i];
        };
        if (a == "--help" || a == "-h") {
            o.help = true;
        } else if (a == "--assets") {
            const auto v = value();
            if (!v) return std::unexpected(v.error());
            o.assets = std::filesystem::path(*v);
        } else if (a == "--size") {
            const auto v = value();
            if (!v) return std::unexpected(v.error());
            const auto x = v->find('x');
            const auto w = x == std::string_view::npos ? std::nullopt : number(v->substr(0, x));
            const auto h = x == std::string_view::npos ? std::nullopt : number(v->substr(x + 1));
            if (!w || !h || *w < 64 || *h < 64 || *w > 8192 || *h > 8192)
                return std::unexpected("--size wants WxH, each 64..8192");
            o.w = static_cast<int>(*w);
            o.h = static_cast<int>(*h);
        } else if (a == "--goto") {
            const auto v = value();
            if (!v) return std::unexpected(v.error());
            o.go = std::string(*v);
        } else if (a == "--zoom") {
            const auto v = value();
            if (!v) return std::unexpected(v.error());
            const auto z = parseZoom(*v);
            if (!z) return std::unexpected("--zoom wants overview or a scale");
            o.zoom = *z;
        } else if (a == "--clock") {
            const auto v = value();
            if (!v) return std::unexpected(v.error());
            if (!parseClock(*v))
                return std::unexpected("--clock wants day, dusk, night, dawn or 0..1");
            o.clock = std::string(*v);
        } else if (a == "--shot" || a == "--script" || a == "--shots") {
            const auto v = value();
            if (!v) return std::unexpected(v.error());
            (a == "--shot"     ? o.shot
             : a == "--script" ? o.script
                               : o.shots) = std::filesystem::path(*v);
        } else if (a == "--renderer") {
            const auto v = value();
            if (!v) return std::unexpected(v.error());
            o.renderer = std::string(*v);
        } else if (a == "--bench") {
            o.bench = true;
            if (i + 1 < args.size() && !args[i + 1].starts_with("--"))
                o.benchCase = std::string(args[++i]);
        } else if (a == "--no-budget") {
            o.budget = false;
        } else if (a == "--report") {
            o.report = true;
        } else if (a == "--interactive") {
            o.interactive = true;
        } else {
            return std::unexpected("unknown option " + std::string(a));
        }
    }
    if (o.interactive && (o.bench || o.script || o.shot))
        return std::unexpected("--interactive runs alone");
    return o;
}

std::expected<std::vector<Command>, std::string> parseScript(std::string_view text) {
    struct Spec {
        std::string_view name;
        Op op;
        std::size_t min;
        std::size_t max;
    };
    static constexpr Spec kSpecs[] = {
        {"goto", Op::Goto, 1, 2},     {"zoom", Op::Zoom, 1, 1}, {"clock", Op::Clock, 1, 1},
        {"pan", Op::Pan, 2, 2},       {"fly", Op::Fly, 1, 4},   {"frames", Op::Frames, 1, 1},
        {"settle", Op::Settle, 0, 0}, {"shot", Op::Shot, 1, 1}, {"expect", Op::Expect, 1, 3},
    };
    std::vector<Command> out;
    int lineNo = 0;
    std::size_t at = 0;
    while (at <= text.size()) {
        const std::size_t end = std::min(text.find('\n', at), text.size());
        std::string_view line = text.substr(at, end - at);
        at = end + 1;
        ++lineNo;
        if (const auto hash = line.find('#'); hash != std::string_view::npos)
            line = line.substr(0, hash);
        auto w = words(line);
        if (w.empty()) continue;
        const std::string head = std::move(w.front());
        w.erase(w.begin());
        const Spec* spec = nullptr;
        for (const Spec& s : kSpecs)
            if (s.name == head) spec = &s;
        const std::string where = "line " + std::to_string(lineNo) + ": ";
        if (spec == nullptr) return std::unexpected(where + "unknown command '" + head + "'");
        if (w.size() < spec->min || w.size() > spec->max)
            return std::unexpected(where + "'" + head + "' takes " + std::to_string(spec->min) +
                                   ".." + std::to_string(spec->max) + " arguments");
        const auto num = [&](std::size_t k) { return number(w[k]).has_value(); };
        bool ok = true;
        switch (spec->op) {
        case Op::Zoom: ok = parseZoom(w[0]).has_value(); break;
        case Op::Clock: ok = parseClock(w[0]).has_value(); break;
        case Op::Pan: ok = num(0) && num(1); break;
        case Op::Frames: ok = num(0) && *number(w[0]) >= 1; break;
        case Op::Goto: ok = w.size() == 1 || (num(0) && num(1)); break;
        case Op::Expect:
            ok = w.size() != 2 || w[0] == "region" || w[0] == "lod" || w[0] == "page_resident";
            break;
        default: break;
        }
        if (!ok) return std::unexpected(where + "bad arguments to '" + head + "'");
        out.push_back({spec->op, std::move(w), lineNo});
    }
    return out;
}

std::optional<bool> compare(double a, std::string_view op, double b) {
    if (op == "<") return a < b;
    if (op == "<=") return a <= b;
    if (op == ">") return a > b;
    if (op == ">=") return a >= b;
    if (op == "==") return a == b;
    return std::nullopt;
}

} // namespace lc::worldview
