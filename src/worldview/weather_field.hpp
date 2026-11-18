#pragma once
// Weather over the whole world (CLAUDE.md "Where this is going": no part of the map is a still
// picture). Clouds and showers are a pure function of the seed, the weather period and a block of
// the grid: each block decides, per period, the cells that start over it, with the tendencies of
// the region it lies in (its theme's climate times the season's), and a cell's place at any time
// is where the shared wind has carried it since. Nothing is stepped or stored: the cells around the
// view are worked out when asked, so a front seen leaving one screen arrives on the next and a
// jump across the world finds the weather already there. Wet ground follows the cells' recent
// paths. The player's choice (rain here, clear here) acts around the view. Pure logic (no SDL).

#include "core/catalog.hpp"
#include "core/iso.hpp"
#include "core/weather.hpp"
#include "world/loader.hpp"

#include <cstdint>
#include <span>
#include <string_view>
#include <vector>

namespace lc::worldview {

// A climate's leaning against the season's own (multipliers): how often showers and clouds come
// and how hard the wind blows. Region files name the climate; until they carry numbers the
// engine's table (tuning.hpp) gives them.
struct Climate {
    float showers = 1;
    float clouds = 1;
    float wind = 1;
};
[[nodiscard]] Climate climateOf(std::string_view name);

struct SeasonClimate {
    float showers = 0.5f; // expected per block and period
    float clouds = 1;
    bool snow = false; // the home's: its rain falls as snow
    int month = -1;    // the calendar month (-1: none, the season's snow everywhere)
    int day = 0;       // the calendar day (lowland snow comes on some days)
};

// A place a shower passed lately, and how wet it left the ground (for drawing).
struct WeatherTrail {
    Vec2 at;
    float radius = 0;
    float wet = 0;
};

class WeatherField {
public:
    WeatherField(const world::LoadedWorld& world, std::uint64_t seed);

    // The cells over `view` (grid tiles) at `time` seconds, carried by `wind`; the season's
    // climate, and the player's choice around the view's centre.
    void update(double time, const Wind& wind, SeasonClimate season, TileRect view,
                WeatherMode mode);
    [[nodiscard]] std::span<const WeatherCell> cells() const { return cells_; }
    // How hard it rains (or snows) at a grid point, 0..1.
    [[nodiscard]] float rainAt(Vec2 tile) const;
    // How wet the ground is at a grid point, 0..1: the showers that crossed it lately.
    [[nodiscard]] float wetAt(Vec2 tile) const;
    // Whether showers over the view fall as snow: by the climate of the region under the view's
    // centre, its snow line that month against the ground's level (no snow in the desert).
    [[nodiscard]] bool snow() const { return snow_; }
    [[nodiscard]] std::span<const WeatherTrail> trails() const { return trails_; }

private:
    void blockCells(int bx, int by, std::int64_t period, const Wind& wind, SeasonClimate season,
                    TileRect view);

    const world::LoadedWorld& world_;
    std::uint64_t seed_;
    [[nodiscard]] bool snowsAt(TilePos t, SeasonClimate season) const;

    std::vector<Climate> climates_;         // per region
    std::vector<const ClimateDef*> snowOf_; // per region: its catalog climate, null: none
    std::vector<WeatherCell> cells_;
    std::vector<Vec2> drift_; // per cell: tiles per second it travels
    std::vector<WeatherTrail> trails_;
    double time_ = 0;
    bool snow_ = false;
};

} // namespace lc::worldview
