#include "core/clock.hpp"

#include "core/tuning.hpp"

#include <array>
#include <cmath>

namespace lc {
namespace {

constexpr std::array<std::string_view, 4> kPhaseIds{"day", "dusk", "night", "dawn"};
constexpr std::array<std::string_view, 5> kPinIds{"auto", "day", "dusk", "night", "dawn"};

double wrap(double t) {
    return t - std::floor(t);
}

float mix(float a, float b, float k) {
    return a + (b - a) * k;
}

Rgb mix(const float* a, const float* b, float k) {
    return {mix(a[0], b[0], k), mix(a[1], b[1], k), mix(a[2], b[2], k)};
}

} // namespace

std::string_view phaseId(Phase p) {
    return kPhaseIds[static_cast<std::size_t>(p)];
}
std::string_view pinId(ClockPin p) {
    return kPinIds[static_cast<std::size_t>(p)];
}

std::optional<ClockPin> parsePin(std::string_view id) {
    for (std::size_t i = 0; i < kPinIds.size(); ++i)
        if (kPinIds[i] == id) return static_cast<ClockPin>(i);
    return std::nullopt;
}

Phase phaseAt(double t) {
    t = wrap(t);
    if (t < tuning::kDuskStart) return Phase::Day;
    if (t < tuning::kNightStart) return Phase::Dusk;
    if (t < tuning::kDawnStart) return Phase::Night;
    return Phase::Dawn;
}

double phaseCentre(Phase p) {
    switch (p) {
    case Phase::Day: return tuning::kDuskStart * 0.5;
    case Phase::Dusk: return (tuning::kDuskStart + tuning::kNightStart) * 0.5;
    case Phase::Night: return (tuning::kNightStart + tuning::kDawnStart) * 0.5;
    case Phase::Dawn: return (tuning::kDawnStart + 1.0) * 0.5;
    }
    return 0;
}

Phase Clock::phase() const {
    return phaseAt(t_);
}

void Clock::setTime(double t) {
    t_ = wrap(t);
}

void Clock::setPin(ClockPin pin, bool instant) {
    pin_ = pin;
    if (instant && pin != ClockPin::Auto)
        t_ = phaseCentre(static_cast<Phase>(static_cast<int>(pin) - 1));
}

void Clock::update(double dt) {
    if (pin_ == ClockPin::Auto) {
        t_ = wrap(t_ + dt / tuning::kDayLengthSeconds);
        return;
    }
    // Glide along the shortest way round the cycle so pinning never jumps.
    const double target = phaseCentre(static_cast<Phase>(static_cast<int>(pin_) - 1));
    const double d = wrap(target - t_ + 0.5) - 0.5;
    const double maxStep = 0.5 * dt / tuning::kPinEaseSeconds; // half a cycle at most
    t_ = std::abs(d) <= maxStep ? target : wrap(t_ + std::copysign(maxStep, d));
}

Lighting lightingAt(double t, bool raining) {
    t = wrap(t);
    const auto& keys = tuning::kLightKeys;
    constexpr std::size_t n = std::size(tuning::kLightKeys);
    std::size_t hi = 0;
    while (hi < n && keys[hi].t <= t) ++hi;
    const auto& a = keys[(hi + n - 1) % n];
    const auto& b = keys[hi % n];
    const double span = wrap(b.t - a.t);
    double k = span > 0 ? wrap(t - a.t) / span : 0.0;
    k = k * k * (3 - 2 * k);
    const auto kf = static_cast<float>(k);

    Lighting l;
    l.ambient = mix(a.ambient, b.ambient, kf);
    l.skyTop = mix(a.skyTop, b.skyTop, kf);
    l.skyBottom = mix(a.skyBottom, b.skyBottom, kf);
    l.glow = mix(a.glow, b.glow, kf);
    l.night = mix(a.night, b.night, kf);
    if (raining) {
        const auto grey = [](Rgb c) {
            const float y = (c.r + c.g + c.b) / 3.0f;
            const float g = tuning::kRainSkyGrey;
            return Rgb{mix(c.r, y, g), mix(c.g, y, g), mix(c.b, y, g)};
        };
        l.skyTop = grey(l.skyTop);
        l.skyBottom = grey(l.skyBottom);
        l.ambient = {l.ambient.r * tuning::kRainAmbientDim, l.ambient.g * tuning::kRainAmbientDim,
                     l.ambient.b * tuning::kRainAmbientDim};
    }
    return l;
}

} // namespace lc
