#include "worldview/weather_field.hpp"

#include "core/rng.hpp"
#include "core/tuning.hpp"
#include "worldview/tuning.hpp"

#include <algorithm>
#include <cmath>

namespace lc::worldview {

Climate climateOf(std::string_view name) {
    for (const auto& c : tuning::kClimates)
        if (c.name == name) return {c.showers, c.clouds, c.wind};
    return {};
}

WeatherField::WeatherField(const world::LoadedWorld& world, std::uint64_t seed)
    : world_(world), seed_(seed) {
    for (const world::RegionFile& r : world.regions) {
        climates_.push_back(climateOf(r.theme.climate));
        snowOf_.push_back(world.map->content().home().findClimate(r.theme.climate));
    }
    cells_.reserve(tuning::kWeatherCellsMax + 1); // and the player's shower
    trails_.reserve(tuning::kWeatherCellsMax * (tuning::kWetSamples + 1));
    drift_.reserve(tuning::kWeatherCellsMax);
}

bool WeatherField::snowsAt(TilePos t, SeasonClimate season) const {
    const world::WorldMap& m = *world_.map;
    if (!m.inBounds(t)) return season.snow;
    const int region = m.regionAt(t);
    const ClimateDef* c = region >= 0 && static_cast<std::size_t>(region) < snowOf_.size()
                              ? snowOf_[static_cast<std::size_t>(region)]
                              : nullptr;
    if (c == nullptr || season.month < 0 ||
        static_cast<std::size_t>(season.month) >= c->snowLine.size())
        return season.snow;
    const int line = c->snowLine[static_cast<std::size_t>(season.month)];
    if (line >= 0 && m.level(t) >= line) return true;
    // Below the line only in its lowland months, on some days (the same all day, everywhere).
    if (((c->lowlandMonths >> season.month) & 1u) == 0) return false;
    Rng rng(seed_ ^ (static_cast<std::uint64_t>(season.day) * 0xC2B2AE3D27D4EB4FULL) ^
            static_cast<std::uint64_t>(region));
    return rng.range(0.0f, 1.0f) < c->lowlandChance;
}

void WeatherField::blockSeeds(int bx, int by, std::int64_t period, SeasonClimate season) {
    const int b = tuning::kWeatherBlock;
    const world::WorldMap& m = *world_.map;
    const TilePos mid{std::clamp(bx * b + b / 2, 0, m.width() - 1),
                      std::clamp(by * b + b / 2, 0, m.height() - 1)};
    const int region = m.regionAt(mid);
    const Climate c = region >= 0 && static_cast<std::size_t>(region) < climates_.size()
                          ? climates_[static_cast<std::size_t>(region)]
                          : Climate{};
    Rng rng(seed_ ^ (static_cast<std::uint64_t>(period) * 0x9E3779B97F4A7C15ULL) ^
            (static_cast<std::uint64_t>(bx + 4096) << 20) ^ static_cast<std::uint64_t>(by + 4096));
    const float expected = season.clouds * c.clouds * tuning::kWeatherCellsPerBlock;
    const auto count = static_cast<int>(expected + rng.range(0.0f, 1.0f));
    const double start = static_cast<double>(period) * ::lc::tuning::kWeatherPeriod;
    for (int k = 0; k < count; ++k) {
        Seed s;
        s.rain = rng.chance(std::clamp(season.showers * c.showers, 0.0f, 1.0f));
        s.radius = s.rain ? rng.range(::lc::tuning::kRainCellMin, ::lc::tuning::kRainCellMax)
                          : rng.range(::lc::tuning::kCloudCellMin, ::lc::tuning::kCloudCellMax);
        s.life = rng.range(tuning::kWeatherLifeMin, tuning::kWeatherLifeMax);
        s.factor = rng.range(0.8f, 1.2f);
        s.born = start + rng.range(0.0f, ::lc::tuning::kWeatherPeriod);
        s.id = static_cast<std::uint32_t>(rng.next());
        s.at = {static_cast<float>(bx * b) + rng.range(0.0f, static_cast<float>(b)),
                static_cast<float>(by * b) + rng.range(0.0f, static_cast<float>(b))};
        s.wind = c.wind;
        seeds_.push_back(s);
    }
}

void WeatherField::update(double time, const Wind& wind, SeasonClimate season, TileRect view,
                          WeatherMode mode) {
    time_ = time;
    snow_ = snowsAt({(view.x0 + view.x1) / 2, (view.y0 + view.y1) / 2}, season);
    cells_.clear();
    drift_.clear();
    // Blocks whose cells can reach the view: as far as a cell of each period can have drifted
    // since its period began (L-112: the young periods need few blocks). Newest first, so if the
    // cap ever cuts, it cuts the oldest cells (the young ones fade in, the old are going).
    const float speed = ::lc::tuning::kCellMinSpeed + ::lc::tuning::kCellWindSpeed * 2.0f;
    const float radius = std::max(::lc::tuning::kCloudCellMax, ::lc::tuning::kRainCellMax);
    const int b = tuning::kWeatherBlock;
    const auto now = static_cast<std::int64_t>(time / ::lc::tuning::kWeatherPeriod);
    const int periods = kPeriods - 1;
    if (mode != WeatherMode::Clear) {
        // What a block decides depends only on the seed, the block, the period and the season:
        // it is worked out again only when the blocks asked or the season change (the view
        // or a period's reach crossing into another block, a new period), not on every step.
        // Where each cell has drifted to and how old it is, is.
        SeedKey key{
            .period = now, .showers = season.showers, .clouds = season.clouds, .blocks = {}};
        for (int k = 0; k <= periods; ++k) {
            const double since = time - static_cast<double>(now - k) * ::lc::tuning::kWeatherPeriod;
            const float age =
                std::min(tuning::kWeatherLifeMax, static_cast<float>(std::max(0.0, since)));
            const auto r = static_cast<int>(age * speed + radius) + 1;
            key.blocks[static_cast<std::size_t>(k)] = {(view.x0 - r) / b - 1, (view.y0 - r) / b - 1,
                                                       (view.x1 + r) / b + 1,
                                                       (view.y1 + r) / b + 1};
        }
        if (!(key == seedKey_)) {
            seedKey_ = key;
            seeds_.clear();
            for (int k = 0; k <= periods; ++k) {
                const Blocks& r = key.blocks[static_cast<std::size_t>(k)];
                for (int by = r.y0; by <= r.y1; ++by)
                    for (int bx = r.x0; bx <= r.x1; ++bx) blockSeeds(bx, by, now - k, season);
            }
        }
        for (const Seed& s : seeds_) {
            const auto age = static_cast<float>(time_ - s.born);
            if (age < 0 || age > s.life) continue;
            const float v = (::lc::tuning::kCellMinSpeed +
                             ::lc::tuning::kCellWindSpeed * wind.strength * s.wind) *
                            s.factor;
            const Vec2 drift{wind.dir.x * v, wind.dir.y * v};
            const Vec2 centre{s.at.x + drift.x * age, s.at.y + drift.y * age};
            // Only what touches the view (grown by its radius) is kept, and counted against
            // the cap.
            const bool touches = centre.x + s.radius > static_cast<float>(view.x0) &&
                                 centre.x - s.radius < static_cast<float>(view.x1) &&
                                 centre.y + s.radius > static_cast<float>(view.y0) &&
                                 centre.y - s.radius < static_cast<float>(view.y1);
            if (!touches || cells_.size() >= tuning::kWeatherCellsMax) continue;
            WeatherCell cell;
            cell.centre = centre;
            cell.radius = s.radius;
            cell.life = s.life;
            cell.factor = s.factor;
            cell.age = age;
            cell.id = s.id;
            cell.rain = s.rain;
            cells_.push_back(cell);
            drift_.push_back(drift);
        }
    }
    trails_.clear();
    for (std::size_t i = 0; i < cells_.size(); ++i) {
        const WeatherCell& c = cells_[i];
        if (!c.rain) continue;
        for (int k = 1; k <= tuning::kWetSamples; ++k) {
            const float back = tuning::kWetMemory * static_cast<float>(k) /
                               static_cast<float>(tuning::kWetSamples);
            if (back > c.age) break;
            trails_.push_back({{c.centre.x - drift_[i].x * back, c.centre.y - drift_[i].y * back},
                               c.radius,
                               c.intensity() * (1.0f - back / tuning::kWetMemory)});
        }
        trails_.push_back({c.centre, c.radius, c.intensity()});
    }
    if (mode == WeatherMode::Clear) return;
    if (mode == WeatherMode::Rain) {
        // Rain here: a shower sits over the view.
        WeatherCell c;
        c.centre = {static_cast<float>(view.x0 + view.x1) * 0.5f,
                    static_cast<float>(view.y0 + view.y1) * 0.5f};
        c.radius = static_cast<float>(std::max(view.x1 - view.x0, view.y1 - view.y0));
        c.rain = true;
        c.life = 1e6f;
        c.age = c.life * 0.5f; // fully grown
        cells_.push_back(c);
        drift_.push_back({});
    }
}

float WeatherField::rainAt(Vec2 t) const {
    float r = 0;
    for (const WeatherCell& c : cells_) {
        if (!c.rain) continue;
        const float d = std::hypot(t.x - c.centre.x, t.y - c.centre.y) / c.radius;
        if (d < 1) r = std::max(r, c.intensity() * (1.0f - d * d));
    }
    return std::min(1.0f, r);
}

float WeatherField::wetAt(Vec2 t) const {
    // Wet where a shower is or passed within the last kWetMemory seconds (sampled along its path).
    float w = 0;
    for (std::size_t i = 0; i < cells_.size(); ++i) {
        const WeatherCell& c = cells_[i];
        if (!c.rain) continue;
        for (int k = 0; k <= tuning::kWetSamples; ++k) {
            const float back = tuning::kWetMemory * static_cast<float>(k) /
                               static_cast<float>(tuning::kWetSamples);
            if (back > c.age) break;
            const Vec2 p{c.centre.x - drift_[i].x * back, c.centre.y - drift_[i].y * back};
            const float d = std::hypot(t.x - p.x, t.y - p.y) / c.radius;
            if (d < 1) w = std::max(w, (1.0f - back / tuning::kWetMemory) * (1.0f - d));
        }
    }
    return std::min(1.0f, w);
}

} // namespace lc::worldview
