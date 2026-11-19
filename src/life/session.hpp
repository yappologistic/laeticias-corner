#pragma once
// Running city life without a renderer: a session that loads the world and its life (for tools,
// tests and the game's headless flags), the life dumps at chosen hours, the city cases of the
// bench and the roaming soak. Everything is measured with a steady clock; nothing here draws.

#include "life/city.hpp"

#include <filesystem>
#include <memory>
#include <optional>
#include <string>
#include <vector>

namespace lc::life {

// The world, its life and one CityLife, loaded from an assets directory.
struct LifeSession {
    std::unique_ptr<Catalog> catalog;
    std::unique_ptr<LoadedWorld> ownWorld; // null when the session runs over someone's world
    const LoadedWorld* world = nullptr;
    std::unique_ptr<LifeWorld> life;
    std::unique_ptr<CityLife> city;
    double loadMs = 0;
};
[[nodiscard]] std::optional<LifeSession> openLifeSession(const std::filesystem::path& assets,
                                                         std::uint64_t seed, std::string& error);
// The life of a world already loaded (the game's): it must outlive the session.
[[nodiscard]] LifeSession openLifeSession(const LoadedWorld& world, std::uint64_t seed);

// The season a place is shown in by default: its region's own moment (Rome and Pārsa spring,
// Athens summer), else the calendar's for `day`.
[[nodiscard]] int regionSeason(const LifeSession& s, TilePos at, int day);

// A focus by name: "x,y" in grid tiles, or "<layer>:<node>" (a graph node), or one of the city
// centres "forum", "agora", "terrace".
[[nodiscard]] std::optional<TilePos> parseFocus(const LifeWorld& w, std::string_view text);

// Game hours: "5.5,10,15.5" or "05:30,10:00".
[[nodiscard]] std::vector<double> parseHours(std::string_view text);

// The busiest view of a region on a day: the focus (a chunk centre) and hour whose live area the
// data fills most, and how many people that is.
struct Busiest {
    TilePos focus;
    double hour = 0;
    float expected = 0;
};
[[nodiscard]] Busiest busiestView(LifeSession& s, std::string_view region, int day, int season);

struct DumpOptions {
    TilePos focus;
    int halfW = 16; // the view around the focus, tiles
    int halfH = 16;
    int day = 1;
    int season = -1; // -1: the region's own season
    bool rain = false;
    std::vector<double> hours;
    double settleSeconds = 20; // simulated after arriving, before the dump
    std::filesystem::path out; // a file (one hour) or a prefix: <out>_<hhmm>.json
    std::string label;
};
// Writes one dump per hour. Returns the files written.
std::vector<std::filesystem::path> writeLifeDumps(LifeSession& s, const DumpOptions& o);

struct BenchCase {
    std::string name;
    double simAvg = 0, simP95 = 0, simP99 = 0, simWorst = 0; // ms per step
    // The longest step in the process's own CPU time: what the simulation did, without the
    // time another program held its core (which the wall clock above includes).
    double simWorkWorst = 0;
    double enumAvg = 0, enumP95 = 0, enumP99 = 0, enumWorst = 0; // ms per gather of the view
    double enumAllAvg = 0, enumAllWorst = 0;                     // of the whole active area
    int liveMin = 0, liveMax = 0, liveAvg = 0;
    int abstractTokens = 0, chains = 0, events = 0;
    double memoryMb = 0;
    int spawnMax = 0; // most actors materialised in one step
    bool ok = true;
    std::string why;
};
struct BenchOptions {
    int frames = 1800;     // steps per case
    double budgetMs = 0.6; // simulation average (CLAUDE.md)
#ifdef NDEBUG
    bool assert =
        true; // timing budgets hold in optimised builds (a sanitizer's pace is not the game's)
#else
    bool assert = false;
#endif
    std::vector<int> caps; // when set: the crowd-size study (live actors forced to each)
    // CPU time the calling thread has used, in ms: the game gives its platform's (it has other
    // threads running); null: the process's (`std::clock`), right for a tool with one thread.
    double (*ownMs)() = nullptr;
};
// The city cases: every city core at its busiest hour and on its festival, a fast move across
// a region and a jump between cities. Prints a table; returns 3 when a budget fails.
int runLifeBench(LifeSession& s, const BenchOptions& o, std::vector<BenchCase>& out);

// `seconds` of busy play at 60 Hz with the area roaming the world; exits 3 when memory grows
// after the first quarter or, when `budgetMs` > 0, the simulation averages over it.
int runLifeSoak(LifeSession& s, double seconds, double budgetMs);

} // namespace lc::life
