#include "life/session.hpp"

#include "life/report.hpp"

#include <algorithm>
#include <charconv>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <fstream>
#include <numeric>

namespace lc::life {

namespace {

using Clock = std::chrono::steady_clock;

double msSince(Clock::time_point t) {
    return std::chrono::duration<double, std::milli>(Clock::now() - t).count();
}

double rssMb() {
    std::ifstream in("/proc/self/status");
    for (std::string line; std::getline(in, line);)
        if (line.starts_with("VmRSS:")) return std::stod(line.substr(6)) / 1024.0;
    return 0;
}

struct Series {
    std::vector<double> v;
    void add(double x) { v.push_back(x); }
    [[nodiscard]] double avg() const {
        return v.empty() ? 0
                         : std::accumulate(v.begin(), v.end(), 0.0) / static_cast<double>(v.size());
    }
    [[nodiscard]] double pct(double p) {
        if (v.empty()) return 0;
        std::vector<double> s = v;
        std::ranges::sort(s);
        return s[std::min(s.size() - 1,
                          static_cast<std::size_t>(p * static_cast<double>(s.size())))];
    }
    [[nodiscard]] double worst() const { return v.empty() ? 0 : *std::ranges::max_element(v); }
};

// The calendar season of a day (seasons of seasonDays days, in order).
int seasonOfDay(const LifeData& d, int day) {
    const int n = std::max<int>(1, static_cast<int>(d.seasons.size()));
    return (day / std::max(1, d.seasonDays)) % n;
}

} // namespace

int regionSeason(const LifeSession& s, TilePos at, int day) {
    const LifeData& d = s.life->data;
    const int lr = d.regionOfWorld(s.world->map->regionAt(at));
    if (lr >= 0 && d.regions[static_cast<std::size_t>(lr)].season >= 0)
        return d.regions[static_cast<std::size_t>(lr)].season;
    return seasonOfDay(d, day);
}

std::optional<LifeSession> openLifeSession(const std::filesystem::path& assets, std::uint64_t seed,
                                           std::string& error) {
    const auto t0 = Clock::now();
    LifeSession s;
    auto cat = loadCatalog(assets / "catalog.json");
    if (!cat) {
        error = cat.error();
        return std::nullopt;
    }
    s.catalog = std::make_unique<Catalog>(std::move(*cat));
    auto w = world::loadWorld(assets, *s.catalog);
    if (!w) {
        error = w.error();
        return std::nullopt;
    }
    s.ownWorld = std::make_unique<LoadedWorld>(std::move(*w));
    s.world = s.ownWorld.get();
    s.life = buildLifeWorld(*s.world);
    s.city = std::make_unique<CityLife>(*s.life, seed);
    s.loadMs = msSince(t0);
    return s;
}

LifeSession openLifeSession(const LoadedWorld& world, std::uint64_t seed) {
    const auto t0 = Clock::now();
    LifeSession s;
    s.world = &world;
    s.life = buildLifeWorld(world);
    s.city = std::make_unique<CityLife>(*s.life, seed);
    s.loadMs = msSince(t0);
    return s;
}

std::optional<TilePos> parseFocus(const LifeWorld& w, std::string_view text) {
    const WorldMap& map = w.map();
    // City centres by district.
    std::string district;
    if (text == "forum") district = "rome/forum";
    if (text == "agora") district = "athens/agora";
    if (text == "terrace") district = "parsa/terrace";
    if (text.starts_with("district:")) district = std::string(text.substr(9));
    if (!district.empty()) {
        const int d = map.findDistrict(district);
        if (d < 0) return std::nullopt;
        double sx = 0;
        double sy = 0;
        int n = 0;
        for (int y = 0; y < map.height(); ++y)
            for (int x = 0; x < map.width(); ++x)
                if (map.districtAt({x, y}) == d) {
                    sx += x;
                    sy += y;
                    ++n;
                }
        if (n == 0) return std::nullopt;
        const TilePos c{static_cast<int>(sx / n), static_cast<int>(sy / n)};
        TilePos best = c;
        int bd = INT32_MAX;
        for (int y = c.y - 24; y <= c.y + 24; ++y)
            for (int x = c.x - 24; x <= c.x + 24; ++x)
                if (map.inBounds({x, y}) && map.districtAt({x, y}) == d && map.walkable({x, y})) {
                    const int dd = (x - c.x) * (x - c.x) + (y - c.y) * (y - c.y);
                    if (dd < bd) {
                        bd = dd;
                        best = {x, y};
                    }
                }
        return best;
    }
    if (const auto colon = text.find(':'); colon != std::string_view::npos) {
        const int n = w.world->roads.findNode(text);
        if (n < 0) return std::nullopt;
        return w.world->roads.nodes()[static_cast<std::size_t>(n)].at;
    }
    const auto comma = text.find(',');
    if (comma == std::string_view::npos) return std::nullopt;
    TilePos p;
    const std::string str(text);
    const char* c = str.c_str();
    if (std::from_chars(c, c + comma, p.x).ec != std::errc{} ||
        std::from_chars(c + comma + 1, c + str.size(), p.y).ec != std::errc{})
        return std::nullopt;
    if (!map.inBounds(p)) return std::nullopt;
    return p;
}

std::vector<double> parseHours(std::string_view text) {
    std::vector<double> out;
    while (!text.empty()) {
        const auto comma = text.find(',');
        const std::string_view part = text.substr(0, comma);
        if (part.find(':') != std::string_view::npos) {
            const float h = parseHour(part);
            if (h >= 0) out.push_back(h);
        } else {
            double v = 0;
            if (std::from_chars(part.data(), part.data() + part.size(), v).ec == std::errc{})
                out.push_back(v);
        }
        if (comma == std::string_view::npos) break;
        text.remove_prefix(comma + 1);
    }
    return out;
}

Busiest busiestView(LifeSession& s, std::string_view region, int day, int season) {
    Busiest best;
    const LifeData& d = s.life->data;
    const int r = d.findRegion(region);
    if (r < 0) return best;
    const LifeRegion& reg = d.regions[static_cast<std::size_t>(r)];
    std::vector<std::uint32_t> chunks;
    for (const District& dist : reg.districts)
        for (const auto& [c, n] : dist.chunks)
            if (n > 64) chunks.push_back(c);
    std::ranges::sort(chunks);
    const auto [first, last] = std::ranges::unique(chunks);
    chunks.erase(first, last);
    const auto cx = static_cast<std::uint32_t>(s.world->map->chunksX());
    for (const std::uint32_t c : chunks)
        for (int half = 1; half < 48; ++half) {
            const double h = half * 0.5;
            const TilePos f{static_cast<int>(c % cx) * kChunk + kChunk / 2,
                            static_cast<int>(c / cx) * kChunk + kChunk / 2};
            const float e = s.city->expectedFor({f.x - 16, f.y - 16, f.x + 16, f.y + 16},
                                                LifeClock::at(day, h, season));
            if (e > best.expected) best = {f, h, e};
        }
    return best;
}

std::vector<std::filesystem::path> writeLifeDumps(LifeSession& s, const DumpOptions& o) {
    std::vector<std::filesystem::path> files;
    CityLife& city = *s.city;
    int season = o.season;
    if (season < 0) {
        // The focus region's own season (its moment), as the builders' day reports read days.
        const int lr = s.life->data.regionOfWorld(s.world->map->regionAt(o.focus));
        season = lr >= 0 && s.life->data.regions[static_cast<std::size_t>(lr)].season >= 0
                     ? s.life->data.regions[static_cast<std::size_t>(lr)].season
                     : seasonOfDay(s.life->data, o.day);
    }
    for (const double h : o.hours) {
        LifeClock c = LifeClock::at(o.day, h, season, o.rain);
        city.setFocus(o.focus, o.halfW, o.halfH);
        city.settle(c);
        const int steps = static_cast<int>(o.settleSeconds * 60.0);
        for (int k = 0; k < steps; ++k) {
            c.t += tuning::kStepSeconds / tuning::kDayLengthSeconds;
            if (c.t >= 1.0) c.t -= 1.0;
            city.update(c, static_cast<float>(tuning::kStepSeconds));
        }
        city.settle(c);
        std::filesystem::path f = o.out;
        if (o.hours.size() > 1) {
            char buf[16];
            (void)std::snprintf(buf, sizeof buf, "_%02d%02d.json", static_cast<int>(h),
                                static_cast<int>(std::lround((h - std::floor(h)) * 60.0)) % 60);
            f = o.out.string() + buf;
        }
        std::ofstream out(f, std::ios::binary);
        out << lifeDump(city, o.label);
        files.push_back(f);
    }
    return files;
}

namespace {

struct CaseSpec {
    enum Kind { Still, Sweep, Jump };
    CaseSpec(std::string n, TilePos f, int d, double h, Kind k = Still)
        : name(std::move(n)), focus(f), day(d), hour(h), kind(k) {}
    std::string name;
    TilePos focus;
    int day = 1;
    double hour = 10;
    Kind kind = Still;
    std::vector<TilePos> stops; // Sweep: from, to; Jump: the cities in turn
    int cap = 0;
    float scale = 0;
};

BenchCase runCase(LifeSession& s, const CaseSpec& spec, int frames) {
    CityLife& city = *s.city;
    BenchCase out;
    out.name = spec.name;
    city.setLiveCap(spec.cap > 0 ? spec.cap : tuning::life::kLiveCap);
    city.forceScale(spec.scale);
    LifeClock c = LifeClock::at(spec.day, spec.hour, regionSeason(s, spec.focus, spec.day));
    city.setFocus(spec.focus);
    city.settle(c);
    // Warm a few seconds so the area moves.
    for (int k = 0; k < 120; ++k) {
        c.t += tuning::kStepSeconds / tuning::kDayLengthSeconds;
        city.update(c, static_cast<float>(tuning::kStepSeconds));
    }
    Series sim;
    Series enu;
    Series enuAll;
    std::vector<DrawActor> buf(2048);
    long liveSum = 0;
    out.liveMin = 1 << 30;
    for (int k = 0; k < frames; ++k) {
        c.t += tuning::kStepSeconds / tuning::kDayLengthSeconds;
        if (c.t >= 1.0) c.t -= 1.0;
        if (spec.kind == CaseSpec::Sweep && spec.stops.size() >= 2) {
            const float f = static_cast<float>(k) / static_cast<float>(frames);
            const TilePos a = spec.stops[0];
            const TilePos b = spec.stops[1];
            city.setFocus({a.x + static_cast<int>(static_cast<float>(b.x - a.x) * f),
                           a.y + static_cast<int>(static_cast<float>(b.y - a.y) * f)});
        }
        if (spec.kind == CaseSpec::Jump && !spec.stops.empty() && k % 300 == 0)
            city.setFocus(spec.stops[static_cast<std::size_t>(k / 300) % spec.stops.size()]);
        const auto t0 = Clock::now();
        city.update(c, static_cast<float>(tuning::kStepSeconds));
        sim.add(msSince(t0));
        const auto t1 = Clock::now();
        const std::size_t n = city.gather(city.view(), 0.5f, buf);
        enu.add(msSince(t1));
        (void)n;
        const auto t2 = Clock::now();
        const std::size_t all = city.gather(city.activeRect(), 0.5f, buf);
        enuAll.add(msSince(t2));
        (void)all;
        const int live = city.stats().live;
        liveSum += live;
        out.liveMin = std::min(out.liveMin, live);
        out.liveMax = std::max(out.liveMax, live);
        out.spawnMax = std::max(out.spawnMax, city.stats().spawnedThisStep);
    }
    out.simAvg = sim.avg();
    out.simP95 = sim.pct(0.95);
    out.simP99 = sim.pct(0.99);
    out.simWorst = sim.worst();
    out.enumAvg = enu.avg();
    out.enumP95 = enu.pct(0.95);
    out.enumP99 = enu.pct(0.99);
    out.enumWorst = enu.worst();
    out.enumAllAvg = enuAll.avg();
    out.enumAllWorst = enuAll.worst();
    out.liveAvg = static_cast<int>(liveSum / std::max(1, frames));
    out.abstractTokens = city.stats().tokens;
    out.chains = city.stats().chains;
    out.events = city.stats().running;
    out.memoryMb = rssMb();
    city.setLiveCap(tuning::life::kLiveCap);
    city.forceScale(0);
    return out;
}

} // namespace

int runLifeBench(LifeSession& s, const BenchOptions& o, std::vector<BenchCase>& out) {
    const LifeWorld& w = *s.life;
    const auto forum = parseFocus(w, "forum");
    const auto agora = parseFocus(w, "agora");
    const auto terrace = parseFocus(w, "terrace");
    if (!forum || !agora || !terrace) {
        (void)std::fprintf(stderr, "life bench: the city centres are not on the map\n");
        return 1;
    }
    std::vector<CaseSpec> cases;
    if (!o.caps.empty()) {
        // The crowd-size study: Rome's core on the Parilia afternoon, the live count held at each
        // cap (scaled from the data's population there).
        for (const int cap : o.caps) {
            CaseSpec c("rome forum, " + std::to_string(cap) + " live", *forum, 1, 16.5);
            c.cap = cap;
            c.scale = -static_cast<float>(cap); // negative: scale to reach this many
            cases.push_back(c);
        }
    } else {
        // Each city at its busiest view on an ordinary day and on its festival, on the calendar
        // (L-110: once a festival's label ran another day, searched in one season and measured
        // in another): the Parilia day 1, the Panathenaia day 4, Parsa's audience day 1; an
        // ordinary day is the first of the year with no festival of the city's on.
        struct City {
            const char* region;
            const char* festival; // null: an ordinary day
            const char* what;
        };
        const auto dayOf = [&](int r, const char* festival) {
            const LifeRegion& reg = w.data.regions[static_cast<std::size_t>(r)];
            const int year = w.data.seasonDays * static_cast<int>(w.data.seasons.size());
            for (int day = 0; day < year; ++day) {
                bool any = false;
                for (std::size_t f = 0; f < reg.festivals.size(); ++f)
                    if (s.city->festivalOn(r, static_cast<int>(f), day, -1)) {
                        if (festival != nullptr && reg.festivals[f].id == festival) return day;
                        any = true;
                    }
                if (festival == nullptr && !any) return day;
            }
            return -1;
        };
        for (const City& c :
             {City{"rome", nullptr, "ordinary day"}, City{"rome", "parilia", "Parilia"},
              City{"athens", nullptr, "ordinary day"}, City{"athens", "panathenaia", "Panathenaia"},
              City{"parsa", "spring_audience", "spring audience"},
              City{"parsa", nullptr, "ordinary day"}}) {
            const int r = w.data.findRegion(c.region);
            const int day = r >= 0 ? dayOf(r, c.festival) : -1;
            if (day < 0) {
                (void)std::fprintf(stderr, "life bench: no day for %s %s\n", c.region, c.what);
                return 1;
            }
            const int season = s.city->seasonFor(day, -1);
            const Busiest b = busiestView(s, c.region, day, season);
            char name[96];
            (void)std::snprintf(name, sizeof name, "%s %s, busiest %02d:%02d (%.0f)", c.region,
                                c.what, static_cast<int>(b.hour),
                                static_cast<int>(b.hour * 60) % 60,
                                static_cast<double>(b.expected));
            cases.emplace_back(name, b.focus, day, b.hour);
        }
        CaseSpec sweep("rome, a fast pan across", {40, 1080}, 9, 10.5, CaseSpec::Sweep);
        sweep.stops = {{40, 1080}, {170, 1100}};
        cases.push_back(sweep);
        CaseSpec jump("jumps between the cities every 5 s", *forum, 9, 10.5, CaseSpec::Jump);
        jump.stops = {*forum, *agora, *terrace};
        cases.push_back(jump);
    }
    int rc = 0;
    (void)std::printf("%-46s %24s %20s %13s %15s %5s %6s\n", "city case (ms per step)",
                      "simulation avg/p95/p99/max", "view enum avg/p99/max", "area avg/max",
                      "live min/avg/max", "spawn", "RSS MB");
    for (CaseSpec& spec : cases) {
        if (spec.scale < 0) {
            // Find the scale that gives this many live actors: the data's count at scale 1 first.
            CityLife& city = *s.city;
            city.setLiveCap(100000);
            city.forceScale(1);
            LifeClock c = LifeClock::at(spec.day, spec.hour, regionSeason(s, spec.focus, spec.day));
            city.setFocus(spec.focus);
            city.settle(c);
            const int atOne = std::max(1, city.stats().live);
            spec.scale = static_cast<float>(-spec.scale) / static_cast<float>(atOne);
            spec.cap =
                std::max(spec.cap, static_cast<int>(static_cast<float>(atOne) * spec.scale) + 50);
            city.setLiveCap(tuning::life::kLiveCap);
            city.forceScale(0);
        }
        BenchCase b = runCase(s, spec, o.frames);
        if (o.assert&& o.caps.empty()) {
            if (b.simAvg > o.budgetMs) {
                b.ok = false;
                b.why = "simulation average over budget";
            }
            if (b.simWorst > 16.6) {
                b.ok = false;
                b.why = "a step blocked for more than a frame";
            }
            if (b.enumAvg > 0.25) {
                b.ok = false;
                b.why = "enumeration over 0.25 ms";
            }
            // Every case is a city's crowd: one that measured an empty view measured nothing.
            if (b.liveMax < tuning::life::kBenchCrowdMin) {
                b.ok = false;
                b.why = "the view held no crowd";
            }
        }
        (void)std::printf(
            "%-46s %5.3f/%5.3f/%5.3f/%5.2f   %5.3f/%5.3f/%5.3f %6.3f/%5.3f  %4d/%4d/%4d "
            "%5d %6.1f %s\n",
            b.name.c_str(), b.simAvg, b.simP95, b.simP99, b.simWorst, b.enumAvg, b.enumP99,
            b.enumWorst, b.enumAllAvg, b.enumAllWorst, b.liveMin, b.liveAvg, b.liveMax, b.spawnMax,
            b.memoryMb, b.ok ? "" : ("FAIL: " + b.why).c_str());
        if (!b.ok) rc = 3;
        out.push_back(b);
    }
    (void)std::fflush(stdout);
    return rc;
}

int runLifeSoak(LifeSession& s, double seconds, double budgetMs) {
    CityLife& city = *s.city;
    const LifeWorld& w = *s.life;
    std::vector<TilePos> places;
    for (const char* name :
         {"forum", "agora", "terrace", "district:ostia/forum", "district:rome/emporium",
          "district:athens/piraeus", "district:parsa/town", "district:rome/transtiberim"})
        if (const auto p = parseFocus(w, name)) places.push_back(*p);
    if (places.empty()) return 1;
    LifeClock c = LifeClock::at(0, 8.0, 0);
    city.setFocus(places[0]);
    city.settle(c);
    const long steps = static_cast<long>(seconds * 60.0);
    double quarterRss = 0;
    std::size_t quarterBytes = 0;
    Series sim;
    std::uint64_t roam = 0x50A1;
    TilePos at = places[0];
    std::vector<DrawActor> buf(2048);
    double worst = 0;
    long inPlace = 0; // actor-seconds drawn walking on the spot, or stuck past the watchdog
    int mostLive = 0;
    const long unstuck0 = city.stats().unstuck;
    for (long k = 0; k < steps; ++k) {
        // The clock at play speed; a calendar day every 50 s so the soak crosses the seasons.
        c.t += tuning::kStepSeconds / tuning::kDayLengthSeconds;
        if (c.t >= 1.0) c.t -= 1.0;
        if (k % 3000 == 0 && k > 0) {
            ++c.day;
            c.season = seasonOfDay(w.data, c.day);
        }
        if (k % 1200 == 0) {
            // Jump to another place, or walk the camera slowly.
            roam = roam * 6364136223846793005ULL + 1442695040888963407ULL;
            at = places[(roam >> 33) % places.size()];
        } else if (k % 20 == 0) {
            at = {at.x + static_cast<int>((roam >> 40) % 3) - 1,
                  at.y + static_cast<int>((roam >> 44) % 3) - 1};
            at.x = std::clamp(at.x, 0, w.map().width() - 1);
            at.y = std::clamp(at.y, 0, w.map().height() - 1);
        }
        city.setFocus(at);
        const auto t0 = Clock::now();
        city.update(c, static_cast<float>(tuning::kStepSeconds));
        const double ms = msSince(t0);
        sim.add(ms);
        worst = std::max(worst, ms);
        if (k % 4 == 0) (void)city.gather(city.view(), 0.5f, buf);
        if (k % 60 == 30) inPlace += city.stats().marching + city.stats().lost;
        mostLive = std::max(mostLive, city.stats().live);
        if (k == steps / 4) {
            quarterRss = rssMb();
            quarterBytes = city.memoryBytes();
        }
    }
    const double endRss = rssMb();
    const std::size_t endBytes = city.memoryBytes();
    (void)std::printf(
        "life soak: %.0f s, day %d; simulation avg %.3f ms, p99 %.3f, worst %.2f; live at end %d; "
        "rss %.1f MB after a quarter, %.1f MB at the end; life memory %.2f -> %.2f MB\n",
        seconds, c.day, sim.avg(), sim.pct(0.99), worst, city.stats().live, quarterRss, endRss,
        static_cast<double>(quarterBytes) / 1e6, static_cast<double>(endBytes) / 1e6);
    (void)std::printf("life soak: %ld actor-seconds walking in place or stuck, %ld given up by "
                      "the watchdog\n",
                      inPlace, city.stats().unstuck - unstuck0);
    int rc = 0;
    if (inPlace > 0) {
        (void)std::printf("life soak: FAIL people walking in place\n");
        rc = 3;
    }
    // The roam crosses three city centres: a run that met nobody measured nothing.
    if (mostLive < tuning::life::kBenchCrowdMin) {
        (void)std::printf("life soak: FAIL the roam met no crowd (at most %d live)\n", mostLive);
        rc = 3;
    }
    if (endRss > quarterRss + tuning::kSoakGrowthMiB || endBytes > quarterBytes) {
        (void)std::printf("life soak: FAIL memory grew\n");
        rc = 3;
    }
    if (budgetMs > 0 && sim.avg() > budgetMs) {
        (void)std::printf("life soak: FAIL simulation average over %.2f ms\n", budgetMs);
        rc = 3;
    }
    return rc;
}

} // namespace lc::life
