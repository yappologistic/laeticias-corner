#include "worldview/theme.hpp"

#include "worldview/tuning.hpp"

#include <algorithm>
#include <array>
#include <cmath>

namespace lc::worldview {
namespace {

// Keyframes in clock order with their index in world::Theme::grading (dawn, day, dusk, night).
struct Key {
    Phase phase;
    std::size_t index;
};
constexpr std::array<Key, 4> kKeys{
    {{Phase::Day, 1}, {Phase::Dusk, 2}, {Phase::Night, 3}, {Phase::Dawn, 0}}};

double wrap01(double t) {
    return t - std::floor(t);
}

} // namespace

Rgb gradingAt(const world::Theme& theme, double t) {
    t = wrap01(t);
    for (std::size_t k = 0; k < kKeys.size(); ++k) {
        const Key& a = kKeys[k];
        const Key& b = kKeys[(k + 1) % kKeys.size()];
        const double ta = phaseCentre(a.phase);
        const double span = wrap01(phaseCentre(b.phase) - ta);
        const double into = wrap01(t - ta);
        if (into > span) continue;
        auto u = static_cast<float>(into / span);
        u = u * u * (3.0f - 2.0f * u);
        const world::Rgb3& ca = theme.grading[a.index];
        const world::Rgb3& cb = theme.grading[b.index];
        return {ca[0] + (cb[0] - ca[0]) * u, ca[1] + (cb[1] - ca[1]) * u,
                ca[2] + (cb[2] - ca[2]) * u};
    }
    return {1, 1, 1};
}

ThemeMixer::ThemeMixer(std::vector<world::Theme> themes, std::vector<std::string> times)
    : themes_(std::move(themes)), times_(std::move(times)), target_(themes_.size(), 0.0f),
      smoothed_(themes_.size(), 0.0f) {}

void ThemeMixer::reset(std::span<const world::RegionWeight> w) {
    std::ranges::fill(target_, 0.0f);
    for (const world::RegionWeight& r : w) target_[static_cast<std::size_t>(r.region)] = r.weight;
    smoothed_ = target_;
    dominant_ = -1;
    settle(0);
}

void ThemeMixer::update(std::span<const world::RegionWeight> w, float dt) {
    std::ranges::fill(target_, 0.0f);
    for (const world::RegionWeight& r : w) target_[static_cast<std::size_t>(r.region)] = r.weight;
    const float k = 1.0f - std::exp(-dt / tuning::kThemeSeconds);
    for (std::size_t i = 0; i < smoothed_.size(); ++i)
        smoothed_[i] += (target_[i] - smoothed_[i]) * k;
    settle(dt);
}

void ThemeMixer::settle(float dt) {
    const auto best = std::ranges::max_element(smoothed_);
    if (best != smoothed_.end() && *best > 0) {
        const int b = static_cast<int>(best - smoothed_.begin());
        if (dominant_ < 0 ||
            *best > smoothed_[static_cast<std::size_t>(dominant_)] + tuning::kCaptionHysteresis)
            dominant_ = b;
    }
    captionAge_ += dt;
    if (dominant_ < 0) return;
    const std::string& time = times_[static_cast<std::size_t>(dominant_)];
    if (time != "none" && !time.empty() && time != captionedTime_) {
        captionedTime_ = time;
        caption_ = dominant_;
        captionAge_ = 0;
    }
}

float ThemeMixer::captionAlpha() const {
    if (caption_ < 0 || captionAge_ >= tuning::kCaptionSeconds) return 0;
    constexpr float kFade = 0.5f;
    return std::clamp(std::min(captionAge_, tuning::kCaptionSeconds - captionAge_) / kFade, 0.0f,
                      1.0f);
}

Grade ThemeMixer::grade(double clockT) const {
    Grade g{{0, 0, 0}, {0, 0, 0}, 0};
    float total = 0;
    float hazeWeight = 0;
    for (std::size_t i = 0; i < smoothed_.size(); ++i) {
        const float w = smoothed_[i];
        if (w <= 0) continue;
        const Rgb m = gradingAt(themes_[i], clockT);
        g.mul = {g.mul.r + m.r * w, g.mul.g + m.g * w, g.mul.b + m.b * w};
        const world::Theme& th = themes_[i];
        const float hw = w * th.hazeStrength;
        g.haze = {g.haze.r + th.haze[0] * hw, g.haze.g + th.haze[1] * hw,
                  g.haze.b + th.haze[2] * hw};
        hazeWeight += hw;
        g.hazeStrength += hw;
        total += w;
    }
    if (total <= 0) return {{1, 1, 1}, {1, 1, 1}, 0};
    g.mul = {g.mul.r / total, g.mul.g / total, g.mul.b / total};
    if (hazeWeight > 0)
        g.haze = {g.haze.r / hazeWeight, g.haze.g / hazeWeight, g.haze.b / hazeWeight};
    g.hazeStrength = g.hazeStrength / total * tuning::kHazeShare;
    return g;
}

} // namespace lc::worldview
