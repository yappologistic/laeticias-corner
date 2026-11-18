// lifeinfo: loads the world and its life and prints a summary, the problems the compile found,
// the chains as tools/worldgen's simulator would report them, life dumps, the city bench or the
// roaming soak. A debugging aid for the engine, world builders and QA; never opens a window.

#include "life/report.hpp"
#include "life/session.hpp"

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

void summary(const LifeSession& s) {
    const LifeWorld& w = *s.life;
    std::printf("load %.0f ms (life %.0f ms); %zu kinds, %zu goods, %zu steps, %zu tokens\n",
                s.loadMs, w.buildMs, w.data.kinds.size(), w.data.goods.size(), w.data.steps.size(),
                w.data.tokens.size());
    for (std::size_t r = 0; r < w.data.regions.size(); ++r) {
        const LifeRegion& reg = w.data.regions[r];
        const int p = w.pathsOf[r];
        std::printf("  %-20s roles %3zu districts %2zu chains %2zu events %2zu figures %2zu",
                    reg.id.c_str(), reg.roles.size(), reg.districts.size(), reg.chains.size(),
                    reg.events.size(), reg.figures.size());
        if (p >= 0) {
            const RegionPaths& rp = w.paths[static_cast<std::size_t>(p)];
            std::printf("  graph %d nodes, %zu edges; course tiles off the walk %d, steps %d",
                        rp.nodeCount(), rp.edges().size(), rp.badCourseTiles(),
                        rp.badCourseSteps());
        }
        std::printf("\n");
    }
    std::printf("life memory %.2f MB; %zu problems (lifeinfo problems)\n",
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
            seed = std::strtoull(arg(argc, argv, i), nullptr, 10);
        else
            break;
    }
    const std::string cmd = i < argc ? argv[i++] : "summary";
    std::string error;
    auto session = openLifeSession(assets, seed, error);
    if (!session) {
        std::fprintf(stderr, "lifeinfo: %s\n", error.c_str());
        return 1;
    }
    if (cmd == "summary") {
        summary(*session);
        return 0;
    }
    if (cmd == "problems") {
        for (const std::string& p : session->life->data.problems) std::printf("%s\n", p.c_str());
        for (const std::string& p : session->city->chains().problems())
            std::printf("%s\n", p.c_str());
        return 0;
    }
    if (cmd == "chains") {
        std::fputs(chainReport(*session->life).c_str(), stdout);
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
                    std::fprintf(stderr, "lifeinfo: unknown focus\n");
                    return 2;
                }
                o.focus = *f;
                haveFocus = true;
            } else if (a == "--hours") {
                o.hours = parseHours(arg(argc, argv, i));
            } else if (a == "--day") {
                o.day = std::atoi(arg(argc, argv, i));
            } else if (a == "--season") {
                o.season = std::atoi(arg(argc, argv, i));
            } else if (a == "--rain") {
                o.rain = true;
            } else if (a == "--label") {
                o.label = arg(argc, argv, i);
            } else if (a == "--view") {
                const std::string_view v = arg(argc, argv, i);
                const auto comma = v.find(',');
                std::from_chars(v.data(), v.data() + comma, o.halfW);
                std::from_chars(v.data() + comma + 1, v.data() + v.size(), o.halfH);
            } else if (a == "--out") {
                o.out = arg(argc, argv, i);
            }
        }
        if (!haveFocus || o.hours.empty() || o.out.empty()) {
            std::fputs(kUsage, stderr);
            return 2;
        }
        for (const auto& f : writeLifeDumps(*session, o)) std::printf("%s\n", f.c_str());
        return 0;
    }
    if (cmd == "bench") {
        BenchOptions o;
        for (; i < argc; ++i) {
            const std::string_view a = argv[i];
            if (a == "--frames") o.frames = std::atoi(arg(argc, argv, i));
            if (a == "--caps")
                for (const double c : parseHours(arg(argc, argv, i)))
                    o.caps.push_back(static_cast<int>(c));
        }
        std::vector<BenchCase> out;
        return runLifeBench(*session, o, out);
    }
    if (cmd == "soak") {
        const double seconds = i < argc ? std::atof(argv[i]) : 120.0;
        return runLifeSoak(*session, seconds, tuning::life::kSimBudgetMs);
    }
    std::fputs(kUsage, stderr);
    return 2;
}
