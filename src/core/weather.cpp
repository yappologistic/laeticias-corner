#include "core/weather.hpp"

#include "core/catalog.hpp"
#include "core/rng.hpp"
#include "core/tuning.hpp"

#include <algorithm>
#include <cmath>

namespace lc {
namespace {

// A value in [0, 1) that depends only on the seed and the key.
float hashed(std::uint64_t seed, std::uint64_t key) {
    Rng r(seed ^ (key * 0x9E3779B97F4A7C15ULL));
    return r.uniform();
}

float smooth(float x) {
    x = std::clamp(x, 0.0f, 1.0f);
    return x * x * (3 - 2 * x);
}

} // namespace

float WeatherCell::intensity() const {
    const float k = life > 0 ? age / life : 1.0f;
    return smooth(std::min(k / 0.2f, (1.0f - k) / 0.2f));
}

Weather::Weather(const Catalog& cat, std::uint64_t seed)
    : cat_(&cat), seed_(seed ^ 0x57EA7E5ULL),
      bw_((cat.mapW + tuning::kWetBlock - 1) / tuning::kWetBlock),
      bh_((cat.mapH + tuning::kWetBlock - 1) / tuning::kWetBlock),
      wet_(static_cast<std::size_t>(bw_ * bh_), 0.0f) {
    cells_.reserve(tuning::kMaxWeatherCells);
}

void Weather::spawnPeriod(int season, TileRect region) {
    const SeasonDef& s = cat_->seasons[static_cast<std::size_t>(season)];
    const auto key = static_cast<std::uint64_t>(period_) * 64;
    const auto count = [&](float expected, std::uint64_t k) {
        return static_cast<int>(std::floor(expected + hashed(seed_, key + k)));
    };
    const int showers = count(s.showers, 1);
    const int clouds = count(s.clouds, 2);
    const float w = static_cast<float>(region.x1 - region.x0);
    const float h = static_cast<float>(region.y1 - region.y0);
    const Vec2 mid{static_cast<float>(region.x0) + w * 0.5f,
                   static_cast<float>(region.y0) + h * 0.5f};
    const float reach = std::hypot(w, h) * 0.5f;
    for (int i = 0; i < showers + clouds; ++i) {
        if (cells_.size() >= tuning::kMaxWeatherCells) break;
        const std::uint64_t k = key + 8 + static_cast<std::uint64_t>(i) * 5;
        WeatherCell c;
        c.rain = i < showers;
        const float r0 = c.rain ? tuning::kRainCellMin : tuning::kCloudCellMin;
        const float r1 = c.rain ? tuning::kRainCellMax : tuning::kCloudCellMax;
        c.radius = r0 + (r1 - r0) * hashed(seed_, k);
        c.factor = 0.8f + 0.4f * hashed(seed_, k + 1);
        // It enters from the upwind edge, offset across the wind, and lives long enough to cross.
        const Vec2 d = wind_.dir;
        const Vec2 across{-d.y, d.x};
        const float off = (hashed(seed_, k + 2) * 2 - 1) * reach;
        const float start = reach + c.radius;
        c.centre = {mid.x - d.x * start + across.x * off, mid.y - d.y * start + across.y * off};
        const float speed = std::max(tuning::kCellMinSpeed, wind_.speed * c.factor);
        c.life = 2 * start / speed;
        c.age = -tuning::kWeatherPeriod * hashed(seed_, k + 3); // staggered within the period
        c.id = nextId_++;
        cells_.push_back(c);
    }
}

void Weather::update(float dt, int season, TileRect region) {
    time_ += dt;
    region_ = region;
    const SeasonDef& s = cat_->seasons[static_cast<std::size_t>(season)];
    // The wind drifts slowly in direction and strength; the same for everyone.
    const auto t = static_cast<float>(time_);
    const float phase = hashed(seed_, 7) * 6.2831853f;
    // Over minutes, not seconds: a shower keeps its course across the corner.
    const float angle = tuning::kWindAngle + 0.35f * std::sin(t / 700.0f + phase) +
                        0.15f * std::sin(t / 230.0f + 1.3f * phase);
    wind_.dir = {std::cos(angle), std::sin(angle)};
    wind_.strength =
        std::clamp(s.wind * (0.75f + 0.25f * std::sin(t / 170.0f + phase)), 0.0f, 1.0f);
    wind_.speed = tuning::kCellMinSpeed + tuning::kCellWindSpeed * wind_.strength;

    const auto p = static_cast<std::int64_t>(time_ / tuning::kWeatherPeriod);
    if (p != period_) {
        period_ = p;
        spawnPeriod(season, region);
    }
    for (WeatherCell& c : cells_) {
        c.age += dt;
        if (c.age < 0) continue;
        const float v = std::max(tuning::kCellMinSpeed, wind_.speed * c.factor) * dt;
        c.centre = {c.centre.x + wind_.dir.x * v, c.centre.y + wind_.dir.y * v};
    }
    std::erase_if(cells_, [](const WeatherCell& c) { return c.age >= c.life; });

    if (gustFront_ >= 0) {
        gustFront_ += tuning::kGustSpeed * dt;
        const float span = std::hypot(static_cast<float>(region.x1 - region.x0),
                                      static_cast<float>(region.y1 - region.y0));
        if (gustFront_ > span + tuning::kGustWidth * 2) gustFront_ = -1;
    }

    // The ground wets under rain and dries slowly after.
    for (int by = 0; by < bh_; ++by)
        for (int bx = 0; bx < bw_; ++bx) {
            const float half = static_cast<float>(tuning::kWetBlock) * 0.5f;
            const Vec2 c{static_cast<float>(bx * tuning::kWetBlock) + half,
                         static_cast<float>(by * tuning::kWetBlock) + half};
            float& w = wet_[static_cast<std::size_t>(by * bw_ + bx)];
            const float r = rainAt(c);
            w = std::clamp(w + (r * tuning::kWetRise - tuning::kWetDry) * dt, 0.0f, 1.0f);
        }
}

float Weather::rainAt(Vec2 p) const {
    switch (mode_) {
    case WeatherMode::Rain: return 1.0f;
    case WeatherMode::Clear: return 0.0f;
    case WeatherMode::Natural: break;
    }
    float best = 0;
    for (const WeatherCell& c : cells_) {
        if (!c.rain || c.age < 0) continue;
        const float d = std::hypot(p.x - c.centre.x, p.y - c.centre.y) / c.radius;
        best = std::max(best, c.intensity() * smooth((1.0f - d) / 0.25f));
    }
    return best;
}

bool Weather::rainingOnLand() const {
    switch (mode_) {
    case WeatherMode::Rain: return true;
    case WeatherMode::Clear: return false;
    case WeatherMode::Natural: break;
    }
    // Rain at the point of the land nearest each shower's middle.
    for (const WeatherCell& c : cells_) {
        if (!c.rain || c.age < 0) continue;
        const Vec2 near{
            std::clamp(c.centre.x, static_cast<float>(region_.x0), static_cast<float>(region_.x1)),
            std::clamp(c.centre.y, static_cast<float>(region_.y0), static_cast<float>(region_.y1))};
        if (raining(near)) return true;
    }
    return false;
}

bool Weather::raining(Vec2 p) const {
    return rainAt(p) >= tuning::kRainThreshold;
}

void Weather::shower() {
    if (cells_.size() >= tuning::kMaxWeatherCells) cells_.erase(cells_.begin());
    const float w = static_cast<float>(region_.x1 - region_.x0);
    const float h = static_cast<float>(region_.y1 - region_.y0);
    const Vec2 mid{static_cast<float>(region_.x0) + w * 0.5f,
                   static_cast<float>(region_.y0) + h * 0.5f};
    WeatherCell c;
    c.rain = true;
    c.radius = tuning::kRainCellMax;
    // Already grown, its leading edge over the upwind rim of the land.
    const float start = std::hypot(w, h) * 0.5f + c.radius;
    c.centre = {mid.x - wind_.dir.x * start, mid.y - wind_.dir.y * start};
    c.life = 2 * start / std::max(tuning::kCellMinSpeed, wind_.speed);
    c.age = c.life * 0.2f;
    c.id = nextId_++;
    cells_.push_back(c);
}

void Weather::gust() {
    // The wave starts at the upwind edge of the region and travels with the wind.
    const float w = static_cast<float>(region_.x1 - region_.x0);
    const float h = static_cast<float>(region_.y1 - region_.y0);
    const float reach = std::hypot(w, h) * 0.5f;
    gustOrigin_ = {static_cast<float>(region_.x0) + w * 0.5f - wind_.dir.x * reach,
                   static_cast<float>(region_.y0) + h * 0.5f - wind_.dir.y * reach};
    gustFront_ = 0;
}

float Weather::gustAt(Vec2 p) const {
    if (gustFront_ < 0) return 0.0f;
    const float along = (p.x - gustOrigin_.x) * wind_.dir.x + (p.y - gustOrigin_.y) * wind_.dir.y;
    const float d = (along - gustFront_) / tuning::kGustWidth;
    return std::exp(-d * d);
}

float Weather::wetness(TilePos t) const {
    const int bx = std::clamp(t.x / tuning::kWetBlock, 0, bw_ - 1);
    const int by = std::clamp(t.y / tuning::kWetBlock, 0, bh_ - 1);
    return wet_.empty() ? 0.0f : wetBlock(bx, by);
}

} // namespace lc
