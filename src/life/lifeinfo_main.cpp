// lifeinfo: loads the world and its life and prints a summary, the problems the compile found,
// the chains as tools/worldgen's simulator would report them, life dumps, the city bench or the
// roaming soak. A debugging aid for the engine, world builders and QA; never opens a window.

#include "life/report.hpp"
#include "life/session.hpp"

#include <algorithm>
#include <array>
#include <charconv>
#include <cstdio>
#include <cstring>
#include <string>
#include <string_view>
#include <vector>

using namespace lc;
using namespace lc::life;

namespace {

constexpr const char* kUsage =
    "usage: lifeinfo [--assets DIR] [--seed N] COMMAND\n"
    "  summary                  regions, roles, populations, paths, build time (default)\n"
    "  problems                 every reference the compile could not resolve\n"
    "  chains                   the chains as worldgen's lifesim reports them (JSON)\n"
    "  dump --focus F --hours H [--day D] [--season S] [--rain] [--view W,H] --out PREFIX\n"
    "                           life dumps (F: x,y | layer:node | forum | agora | terrace)\n"
    "  bench [--frames N] [--caps 400,600,800]   the city cases (exit 3 over budget)\n"
    "  soak SECONDS             roam the world; exit 3 when memory grows\n";

const char* arg(int argc, char** argv, int& i) {
    return i + 1 < argc ? argv[++i] : "";
}

// A number from an argument; `fallback` when it is not one.
template <typename T>
T number(std::string_view s, T fallback) {
    const std::string text(s);
    T v{};
    const auto [p, ec] = std::from_chars(text.c_str(), text.c_str() + text.size(), v);
    return ec == std::errc{} && p == text.c_str() + text.size() ? v : fallback;
}

void summary(const LifeSession& s) {
    const LifeWorld& w = *s.life;
    (void)std::printf("load %.0f ms (life %.0f ms); %zu kinds, %zu goods, %zu steps, %zu tokens\n",
                      s.loadMs, w.buildMs, w.data.kinds.size(), w.data.goods.size(),
                      w.data.steps.size(), w.data.tokens.size());
    for (std::size_t r = 0; r < w.data.regions.size(); ++r) {
        const LifeRegion& reg = w.data.regions[r];
        const int p = w.pathsOf[r];
        (void)std::printf("  %-20s roles %3zu districts %2zu chains %2zu events %2zu figures %2zu",
                          reg.id.c_str(), reg.roles.size(), reg.districts.size(), reg.chains.size(),
                          reg.events.size(), reg.figures.size());
        if (p >= 0) {
            const RegionPaths& rp = w.paths[static_cast<std::size_t>(p)];
            (void)std::printf("  graph %d nodes, %zu edges; course tiles off the walk %d, steps %d",
                              rp.nodeCount(), rp.edges().size(), rp.badCourseTiles(),
                              rp.badCourseSteps());
        }
        (void)std::printf("\n");
    }
    (void)std::printf("life memory %.2f MB; %zu problems (lifeinfo problems)\n",
                      static_cast<double>(w.memoryBytes()) / 1e6, w.data.problems.size());
}

} // namespace

int main(int argc, char** argv) {
    std::filesystem::path assets = LC_LIFEINFO_ASSETS_DIR;
    std::uint64_t seed = 1;
    int i = 1;
    for (; i < argc; ++i) {
        const std::string_view a = argv[i];
        if (a == "--assets")
            assets = arg(argc, argv, i);
        else if (a == "--seed")
            seed = number<std::uint64_t>(arg(argc, argv, i), seed);
        else
            break;
    }
    const std::string cmd = i < argc ? argv[i++] : "summary";
    std::string error;
    auto session = openLifeSession(assets, seed, error);
    if (!session) {
        (void)std::fprintf(stderr, "lifeinfo: %s\n", error.c_str());
        return 1;
    }
    if (cmd == "summary") {
        summary(*session);
        return 0;
    }
    if (cmd == "problems") {
        for (const std::string& p : session->life->data.problems) std::printf("%s\n", p.c_str());
        for (const std::string& p : session->city->chains().problems())
            (void)std::printf("%s\n", p.c_str());
        for (const std::string& p : walkProblems(*session->life))
            (void)std::printf("%s\n", p.c_str());
        return 0;
    }
    if (cmd == "chains") {
        (void)std::fputs(chainReport(*session->life).c_str(), stdout);
        return 0;
    }
    if (cmd == "dump") {
        DumpOptions o;
        bool haveFocus = false;
        for (; i < argc; ++i) {
            const std::string_view a = argv[i];
            if (a == "--focus") {
                const auto f = parseFocus(*session->life, arg(argc, argv, i));
                if (!f) {
                    (void)std::fprintf(stderr, "lifeinfo: unknown focus\n");
                    return 2;
                }
                o.focus = *f;
                haveFocus = true;
            } else if (a == "--hours") {
                o.hours = parseHours(arg(argc, argv, i));
            } else if (a == "--day") {
                o.day = number(arg(argc, argv, i), o.day);
            } else if (a == "--season") {
                o.season = number(arg(argc, argv, i), o.season);
            } else if (a == "--rain") {
                o.rain = true;
            } else if (a == "--label") {
                o.label = arg(argc, argv, i);
            } else if (a == "--view") {
                const std::string_view v = arg(argc, argv, i);
                const auto comma = v.find(',');
                if (comma != std::string_view::npos) {
                    o.halfW = number(v.substr(0, comma), o.halfW);
                    o.halfH = number(v.substr(comma + 1), o.halfH);
                }
            } else if (a == "--out") {
                o.out = arg(argc, argv, i);
            }
        }
        if (!haveFocus || o.hours.empty() || o.out.empty()) {
            (void)std::fputs(kUsage, stderr);
            return 2;
        }
        for (const auto& f : writeLifeDumps(*session, o)) std::printf("%s\n", f.c_str());
        return 0;
    }
    if (cmd == "bench") {
        BenchOptions o;
        for (; i < argc; ++i) {
            const std::string_view a = argv[i];
            if (a == "--frames") o.frames = number(arg(argc, argv, i), o.frames);
            if (a == "--caps")
                for (const double c : parseHours(arg(argc, argv, i)))
                    o.caps.push_back(static_cast<int>(c));
        }
        std::vector<BenchCase> out;
        return runLifeBench(*session, o, out);
    }
    if (cmd == "soak") {
        const double seconds = i < argc ? number(argv[i], 120.0) : 120.0;
#ifdef NDEBUG
        return runLifeSoak(*session, seconds, tuning::kSimBudgetMs);
#else
        return runLifeSoak(*session, seconds,
                           0); // memory only: a sanitizer's pace is not the game's
#endif
    }
    (void)std::fputs(kUsage, stderr);
    return 2;
}
