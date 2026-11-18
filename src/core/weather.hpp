#pragma once
// Wind and weather (docs/design/living-world.md §6): one shared wind whose direction drifts
// slowly and through which gust waves travel, and weather as drifting cells (clouds and
// showers) that cross the home region, wetting the ground under them. What comes when is a pure
// function of the seed and the weather period, so runs are reproducible. The player may ask for
// rain here or clear skies here instead of the natural weather. Pure logic: no SDL.

#include "core/iso.hpp"

#include <cstdint>
#include <span>
#include <vector>

namespace lc {

struct Catalog;

enum class WeatherMode : std::uint8_t { Natural, Rain, Clear };

struct WeatherCell {
    Vec2 centre; // tiles
    float radius = 8;
    float age = 0;
    float life = 1;
    float factor = 1; // drift relative to the wind
    bool rain = false;
    std::uint32_t id = 0;
    // 0..1: grows over the first fifth of its life, holds, fades over the last fifth.
    [[nodiscard]] float intensity() const;
};

struct Wind {
    Vec2 dir{1, 0};     // unit vector in tile space
    float strength = 0; // 0..1
    float speed = 0;    // tiles per second a cell drifts at
};

class Weather {
public:
    Weather(const Catalog& cat, std::uint64_t seed);

    // `region` is the land the weather crosses (the home region's open land).
    void update(float dt, int season, TileRect region);
    void setMode(WeatherMode m) { mode_ = m; }
    [[nodiscard]] WeatherMode mode() const { return mode_; }

    // How hard it rains at a point, 0..1 (snow in a snowy season is the same rain).
    [[nodiscard]] float rainAt(Vec2 tile) const;
    [[nodiscard]] bool raining(Vec2 tile) const;
    [[nodiscard]] Wind wind() const { return wind_; }
    // A gust wave now crossing the region: how strongly it is at a point, 0..1.
    [[nodiscard]] float gustAt(Vec2 tile) const;
    [[nodiscard]] bool gusting() const { return gustFront_ >= 0; }
    void gust();
    // A shower enters at the upwind edge of the region now (a script asking for one).
    void shower();
    // Wetness of the ground, 0..1, per block of kWetBlock tiles.
    [[nodiscard]] float wetness(TilePos t) const;
    [[nodiscard]] std::span<const WeatherCell> cells() const { return cells_; }
    [[nodiscard]] int wetBlocksX() const { return bw_; }
    [[nodiscard]] int wetBlocksY() const { return bh_; }
    [[nodiscard]] float wetBlock(int bx, int by) const {
        return wet_[static_cast<std::size_t>(by * bw_ + bx)];
    }

private:
    void spawnPeriod(int season, TileRect region);

    const Catalog* cat_; // a pointer, so a fresh one can be assigned when another world opens
    std::uint64_t seed_;
    WeatherMode mode_ = WeatherMode::Natural;
    double time_ = 0; // seconds of weather simulated
    std::int64_t period_ = -1;
    std::uint32_t nextId_ = 1;
    std::vector<WeatherCell> cells_;
    Wind wind_;
    float gustFront_ = -1; // distance the wave has travelled across the region, -1: none
    Vec2 gustOrigin_;
    TileRect region_;
    int bw_ = 0;
    int bh_ = 0;
    std::vector<float> wet_;
};

} // namespace lc
