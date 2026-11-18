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
    for (const world::RegionFile& r : world.regions)
        climates_.push_back(climateOf(r.theme.climate));
    cells_.reserve(tuning::kWeatherCellsMax);
    trails_.reserve(tuning::kWeatherCellsMax * (tuning::kWetSamples + 1));
    drift_.reserve(tuning::kWeatherCellsMax);
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
    snow_ = season.snow;
    cells_.clear();
    drift_.clear();
    // Blocks whose cells can reach the view: upwind by as far as a cell drifts in its life.
    const float reach = tuning::kWeatherLifeMax *
                            (::lc::tuning::kCellMinSpeed + ::lc::tuning::kCellWindSpeed * 2.0f) +
                        ::lc::tuning::kCloudCellMax;
    const int b = tuning::kWeatherBlock;
    const auto r = static_cast<int>(reach);
    const int bx0 = (view.x0 - r) / b - 1;
    const int by0 = (view.y0 - r) / b - 1;
    const int bx1 = (view.x1 + r) / b + 1;
    const int by1 = (view.y1 + r) / b + 1;
    const auto now = static_cast<std::int64_t>(time / ::lc::tuning::kWeatherPeriod);
    const int periods =
        static_cast<int>(tuning::kWeatherLifeMax / ::lc::tuning::kWeatherPeriod) + 1;
    if (mode != WeatherMode::Clear) {
        // What the blocks decide depends only on the seed, the block, the period and the
        // season: it is worked out again only when one of them changes (the view crossing into
        // another block, a new period), not on every step. Where each cell has drifted to and
        // how old it is, is.
        const SeedKey key{bx0, by0, bx1, by1, now, season.showers, season.clouds};
        if (!(key == seedKey_)) {
            seedKey_ = key;
            seeds_.clear();
            for (std::int64_t p = now - periods; p <= now; ++p)
                for (int by = by0; by <= by1; ++by)
                    for (int bx = bx0; bx <= bx1; ++bx) blockSeeds(bx, by, p, season);
        }
        for (const Seed& s : seeds_) {
            if (cells_.size() >= tuning::kWeatherCellsMax) break;
            WeatherCell cell;
            cell.rain = s.rain;
            cell.radius = s.radius;
            cell.life = s.life;
            cell.factor = s.factor;
            cell.age = static_cast<float>(time_ - s.born);
            cell.id = s.id;
            if (cell.age < 0 || cell.age > cell.life) continue;
            const float speed = (::lc::tuning::kCellMinSpeed +
                                 ::lc::tuning::kCellWindSpeed * wind.strength * s.wind) *
                                cell.factor;
            const Vec2 v{wind.dir.x * speed, wind.dir.y * speed};
            cell.centre = {s.at.x + v.x * cell.age, s.at.y + v.y * cell.age};
            cells_.push_back(cell);
            drift_.push_back(v);
        }
    }
    // Only what touches the view (grown by a radius) is kept.
    const auto touches = [&](const WeatherCell& c) {
        return c.centre.x + c.radius > static_cast<float>(view.x0) &&
               c.centre.x - c.radius < static_cast<float>(view.x1) &&
               c.centre.y + c.radius > static_cast<float>(view.y0) &&
               c.centre.y - c.radius < static_cast<float>(view.y1);
    };
    std::size_t keep = 0;
    for (std::size_t i = 0; i < cells_.size(); ++i)
        if (touches(cells_[i])) {
            cells_[keep] = cells_[i];
            drift_[keep] = drift_[i];
            ++keep;
        }
    cells_.resize(keep);
    drift_.resize(keep);
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
