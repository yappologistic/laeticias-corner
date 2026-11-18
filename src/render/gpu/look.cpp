#include "render/gpu/look.hpp"

#include "render/gpu/tuning.hpp"

#include <nlohmann/json.hpp>

#include <algorithm>
#include <cmath>
#include <numbers>
#include <string>

namespace lc::gpu {
namespace {

using json = nlohmann::json;

constexpr std::array<std::string_view, kQualityCount> kQualityIds{"classic", "low", "medium",
                                                                  "high"};
constexpr std::array<std::string_view, kPhases> kPhaseIds{"dawn", "day", "dusk", "night"};
constexpr float kTau = 2.0f * std::numbers::pi_v<float>;

double wrap01(double t) {
    return t - std::floor(t);
}

float smoothstep(float e0, float e1, float x) {
    const float t = std::clamp((x - e0) / (e1 - e0), 0.0f, 1.0f);
    return t * t * (3.0f - 2.0f * t);
}

float luma(Rgb c) {
    return c.r * 0.299f + c.g * 0.587f + c.b * 0.114f;
}

Rgb lerp(Rgb a, Rgb b, float k) {
    return {a.r + (b.r - a.r) * k, a.g + (b.g - a.g) * k, a.b + (b.b - a.b) * k};
}

Rgb operator*(Rgb a, Rgb b) {
    return {a.r * b.r, a.g * b.g, a.b * b.b};
}

Rgb hex(std::string_view s) {
    if (s.size() != 7 || s[0] != '#') return {1, 1, 1};
    const auto nib = [](char c) {
        if (c >= '0' && c <= '9') return c - '0';
        if (c >= 'a' && c <= 'f') return c - 'a' + 10;
        if (c >= 'A' && c <= 'F') return c - 'A' + 10;
        return 0;
    };
    const auto byte = [&](std::size_t i) {
        return static_cast<float>(nib(s[i]) * 16 + nib(s[i + 1])) / 255.0f;
    };
    return {byte(1), byte(3), byte(5)};
}

GradePhase ph(Rgb wb, float exposure, Rgb shadow, Rgb high, float tint, float contrast, float sat,
              float shoulder) {
    return {wb, exposure, shadow, high, tint, contrast, sat, shoulder};
}

RegionLook makeHome() {
    RegionLook l;
    l.phases = {ph({0.96f, 0.88f, 0.88f}, 0.88f, {0.34f, 0.34f, 0.64f}, {0.72f, 0.58f, 0.42f},
                   0.28f, 0.30f, 1.10f, 0.2f),
                ph({1.0f, 1.0f, 0.98f}, 1.0f, {0.32f, 0.40f, 0.66f}, {0.56f, 0.54f, 0.46f}, 0.26f,
                   0.30f, 1.10f, 0.3f),
                ph({1.0f, 0.80f, 0.62f}, 0.80f, {0.30f, 0.32f, 0.62f}, {0.92f, 0.62f, 0.30f}, 0.36f,
                   0.34f, 1.18f, 0.2f),
                ph({0.78f, 0.82f, 1.0f}, 0.48f, {0.26f, 0.30f, 0.56f}, {0.54f, 0.52f, 0.60f}, 0.28f,
                   0.22f, 0.85f, 0.0f)};
    l.sky = {{{hex("#384a7a"), hex("#eaa47e"), hex("#f8dcb4")},
              {hex("#4a8ad0"), hex("#a6cdee"), hex("#eef2ee")},
              {hex("#3e2e58"), hex("#d8703e"), hex("#f6c07a")},
              {hex("#0e1532"), hex("#202c52"), hex("#2c3860")}}};
    l.shade = {hex("#7c74ac"), hex("#7aa4d6"), hex("#665494"), hex("#283462")};
    l.haze = hex("#e8e2d4");
    l.hazeByLod = {0.04f, 0.12f, 0.18f, 0.26f};
    l.water = hex("#4a8fb0");
    return l;
}

float num(const json& j, const char* key, float fallback) {
    const auto it = j.find(key);
    return it != j.end() && it->is_number() ? it->get<float>() : fallback;
}

Rgb rgb(const json& j, const char* key, Rgb fallback) {
    const auto it = j.find(key);
    if (it == j.end()) return fallback;
    if (it->is_string()) return hex(it->get<std::string>());
    if (!it->is_array() || it->size() != 3) return fallback;
    for (const json& v : *it)
        if (!v.is_number()) return fallback;
    return {(*it)[0].get<float>(), (*it)[1].get<float>(), (*it)[2].get<float>()};
}

GradePhase parsePhase(const json& j, const GradePhase& f) {
    if (!j.is_object()) return f;
    GradePhase p;
    p.wb = rgb(j, "wb", f.wb);
    p.exposure = num(j, "exposure", f.exposure);
    p.shadowTint = rgb(j, "shadow_tint", f.shadowTint);
    p.highTint = rgb(j, "high_tint", f.highTint);
    p.tint = num(j, "tint", f.tint);
    p.contrast = num(j, "contrast", f.contrast);
    p.saturation = num(j, "saturation", f.saturation);
    p.shoulder = num(j, "shoulder", f.shoulder);
    return p;
}

void add(GradePhase& acc, const GradePhase& p, float w) {
    const auto addRgb = [w](Rgb& a, Rgb b) {
        a.r += b.r * w;
        a.g += b.g * w;
        a.b += b.b * w;
    };
    addRgb(acc.wb, p.wb);
    acc.exposure += p.exposure * w;
    addRgb(acc.shadowTint, p.shadowTint);
    addRgb(acc.highTint, p.highTint);
    acc.tint += p.tint * w;
    acc.contrast += p.contrast * w;
    acc.saturation += p.saturation * w;
    acc.shoulder += p.shoulder * w;
}

GradePhase mixPhase(const GradePhase& a, const GradePhase& b, float k) {
    GradePhase out{{0, 0, 0}, 0, {0, 0, 0}, {0, 0, 0}, 0, 0, 0, 0};
    add(out, a, 1.0f - k);
    add(out, b, k);
    return out;
}

// Value noise in time: smooth between hashed values one unit apart.
float hash01(std::uint32_t x) {
    x ^= x >> 16;
    x *= 0x7feb352dU;
    x ^= x >> 15;
    x *= 0x846ca68bU;
    x ^= x >> 16;
    return static_cast<float>(x) / 4294967295.0f;
}

float noise1(double t, std::uint32_t seed) {
    const double f = std::floor(t);
    const auto i = static_cast<std::uint32_t>(static_cast<std::int64_t>(f));
    const auto u = static_cast<float>(t - f);
    const float s = u * u * (3.0f - 2.0f * u);
    const float a = hash01(i * 0x9e3779b1U ^ seed);
    const float b = hash01((i + 1) * 0x9e3779b1U ^ seed);
    return a + (b - a) * s;
}

} // namespace

std::optional<Quality> parseQuality(std::string_view id) {
    for (int i = 0; i < kQualityCount; ++i)
        if (kQualityIds[static_cast<std::size_t>(i)] == id) return static_cast<Quality>(i);
    return std::nullopt;
}

std::string_view qualityId(Quality q) {
    return kQualityIds[static_cast<std::size_t>(q)];
}

constexpr std::array<std::string_view, kCloudModes> kCloudIds{"on", "shadows", "off"};

std::optional<Clouds> parseClouds(std::string_view id) {
    for (int i = 0; i < kCloudModes; ++i)
        if (kCloudIds[static_cast<std::size_t>(i)] == id) return static_cast<Clouds>(i);
    return std::nullopt;
}

std::string_view cloudsId(Clouds c) {
    return kCloudIds[static_cast<std::size_t>(c)];
}

const RegionLook& homeLook() {
    static const RegionLook kHome = makeHome();
    return kHome;
}

RegionLook parseLook(const json& look, const json& seasons, const RegionLook& fallback) {
    RegionLook l = fallback;
    if (look.is_object()) {
        if (const auto ph = look.find("phases"); ph != look.end() && ph->is_object())
            for (std::size_t i = 0; i < kPhaseIds.size(); ++i)
                if (const auto p = ph->find(std::string(kPhaseIds[i])); p != ph->end())
                    l.phases[i] = parsePhase(*p, fallback.phases[i]);
        if (const auto sky = look.find("sky"); sky != look.end() && sky->is_object())
            for (std::size_t i = 0; i < kPhaseIds.size(); ++i) {
                const auto s = sky->find(std::string(kPhaseIds[i]));
                if (s == sky->end() || !s->is_array() || s->size() != 3) continue;
                for (std::size_t k = 0; k < 3; ++k)
                    if ((*s)[k].is_string()) l.sky[i][k] = hex((*s)[k].get<std::string>());
            }
        if (const auto sh = look.find("shade"); sh != look.end() && sh->is_object())
            for (std::size_t i = 0; i < kPhaseIds.size(); ++i) {
                const auto c = sh->find(std::string(kPhaseIds[i]));
                if (c != sh->end() && c->is_string()) l.shade[i] = hex(c->get<std::string>());
            }
        if (const auto h = look.find("haze"); h != look.end() && h->is_object()) {
            l.haze = rgb(*h, "colour", fallback.haze);
            l.hazeByLod[0] = num(*h, "strength", fallback.hazeByLod[0]);
            if (const auto z = h->find("by_zoom"); z != h->end() && z->is_object()) {
                l.hazeByLod[1] = num(*z, "half", fallback.hazeByLod[1]);
                l.hazeByLod[2] = num(*z, "quarter", fallback.hazeByLod[2]);
                l.hazeByLod[3] = num(*z, "overview", fallback.hazeByLod[3]);
            }
        }
        if (const auto wt = look.find("water"); wt != look.end() && wt->is_object())
            l.water = rgb(*wt, "body", fallback.water);
    }
    if (seasons.is_object())
        for (std::size_t i = 0; i < kSeasonIds.size(); ++i) {
            const auto s = seasons.find(std::string(kSeasonIds[i]));
            if (s == seasons.end() || !s->is_object()) continue;
            SeasonGrade& g = l.seasons[i];
            g.wb = rgb(*s, "grade", g.wb);
            if (const auto lk = s->find("look"); lk != s->end() && lk->is_object()) {
                g.saturation = num(*lk, "saturation", 0);
                g.warmth = num(*lk, "warmth", 0);
            }
        }
    return l;
}

GradeAt gradeAt(const RegionLook& look, double clock, int season, int lod) {
    // Keyframes in clock order with their index in the files' phase order.
    struct Key {
        Phase phase;
        std::size_t index;
    };
    static constexpr std::array<Key, 4> kKeys{
        {{Phase::Day, 1}, {Phase::Dusk, 2}, {Phase::Night, 3}, {Phase::Dawn, 0}}};
    const double t = wrap01(clock);
    std::size_t a = 0;
    std::size_t b = 0;
    float u = 0;
    for (std::size_t k = 0; k < kKeys.size(); ++k) {
        const double ta = phaseCentre(kKeys[k].phase);
        const double span = wrap01(phaseCentre(kKeys[(k + 1) % kKeys.size()].phase) - ta);
        const double into = wrap01(t - ta);
        if (into > span) continue;
        a = kKeys[k].index;
        b = kKeys[(k + 1) % kKeys.size()].index;
        u = static_cast<float>(into / span);
        u = u * u * (3.0f - 2.0f * u);
        break;
    }
    GradeAt g;
    g.grade = mixPhase(look.phases[a], look.phases[b], u);
    for (std::size_t k = 0; k < 3; ++k) g.sky[k] = lerp(look.sky[a][k], look.sky[b][k], u);
    g.shade = lerp(look.shade[a], look.shade[b], u);
    if (season >= 0 && season < kSeasons) {
        const SeasonGrade& s = look.seasons[static_cast<std::size_t>(season)];
        g.grade.wb = g.grade.wb * s.wb;
        g.grade.wb.r *= 1.0f + s.warmth;
        g.grade.wb.b *= 1.0f - s.warmth;
        g.grade.saturation += s.saturation;
    }
    // The air takes the sky's colour as the light goes: the day's haze, the horizon at dawn and
    // dusk, the night sky's middle at night (a warm day haze over a night city warms it).
    const auto airOf = [&](std::size_t phase) {
        static constexpr std::array<float, kPhases> kToSky{0.5f, 0.0f, 0.6f, 1.0f};
        const Rgb sky = phase == 3 ? look.sky[phase][1] : look.sky[phase][2];
        return lerp(look.haze, sky, kToSky[phase]);
    };
    g.haze = lerp(airOf(a), airOf(b), u);
    g.hazeStrength = look.hazeByLod[static_cast<std::size_t>(std::clamp(lod, 0, 3))];
    g.water = look.water;
    return g;
}

void accumulate(GradeAt& acc, const GradeAt& g, float w) {
    add(acc.grade, g.grade, w);
    for (std::size_t k = 0; k < 3; ++k) {
        acc.sky[k].r += g.sky[k].r * w;
        acc.sky[k].g += g.sky[k].g * w;
        acc.sky[k].b += g.sky[k].b * w;
    }
    acc.shade.r += g.shade.r * w;
    acc.shade.g += g.shade.g * w;
    acc.shade.b += g.shade.b * w;
    acc.haze.r += g.haze.r * w;
    acc.haze.g += g.haze.g * w;
    acc.haze.b += g.haze.b * w;
    acc.hazeStrength += g.hazeStrength * w;
    acc.water.r += g.water.r * w;
    acc.water.g += g.water.g * w;
    acc.water.b += g.water.b * w;
}

GradeAt scaled(const GradeAt& g, float k) {
    GradeAt out{{{0, 0, 0}, 0, {0, 0, 0}, {0, 0, 0}, 0, 0, 0, 0},
                {Rgb{0, 0, 0}, Rgb{0, 0, 0}, Rgb{0, 0, 0}},
                {0, 0, 0},
                {0, 0, 0},
                0,
                {0, 0, 0}};
    accumulate(out, g, k);
    return out;
}

Rgb applyGrade(const GradePhase& g, Rgb a, Rgb nightTint, float night) {
    // tools/worldgen look.py's parameters as the art director's mock-ups apply them
    // (out/look/mockups/make.py `grade`), with the curve and shoulder on lightness alone (per
    // channel they saturate warm earth into orange) and the cool shift of low light at night.
    Rgb c{a.r * g.wb.r * g.exposure, a.g * g.wb.g * g.exposure, a.b * g.wb.b * g.exposure};
    float l = luma(c);
    const float ws = 1.0f - smoothstep(0.0f, 0.55f, l);
    const float wh = smoothstep(0.45f, 1.0f, l);
    const auto tone = [&](float v, float sh, float hi) {
        return std::clamp(v + ws * (sh - 0.5f) * g.tint + wh * (hi - 0.5f) * g.tint, 0.0f, 1.0f);
    };
    c = {tone(c.r, g.shadowTint.r, g.highTint.r), tone(c.g, g.shadowTint.g, g.highTint.g),
         tone(c.b, g.shadowTint.b, g.highTint.b)};
    l = luma(c);
    float k = l + g.contrast * (l - 0.5f) * l * (1.0f - l) * 4.0f;
    if (k > 0.8f) k = 0.8f + (k - 0.8f) * (1.0f - g.shoulder);
    const float scale = k / std::max(l, 1e-4f);
    const float s = 1.0f + (g.saturation - 1.0f) * (1.0f - std::abs(2.0f * k - 1.0f));
    const auto sat = [&](float v) { return k + (v * scale - k) * s; };
    c = {sat(c.r), sat(c.g), sat(c.b)};
    const float m = luma(c);
    const auto cool = [&](float v, float t) {
        return std::clamp(v + (m * t - v) * night, 0.0f, 1.0f);
    };
    return {cool(c.r, nightTint.r), cool(c.g, nightTint.g), cool(c.b, nightTint.b)};
}

Rgb nightTint() {
    const Rgb t{tuning::kNightTint[0], tuning::kNightTint[1], tuning::kNightTint[2]};
    const float l = luma(t);
    return {t.r / l, t.g / l, t.b / l};
}

float windLean(Vec2 w, double now, Vec2 dir, float strength) {
    const auto t = static_cast<float>(std::fmod(now, 3600.0));
    const float along = w.x * dir.x + w.y * dir.y;
    // The steady sway: a slow rocking whose phase drifts across the world, faster in a strong
    // wind, never against the wind.
    const float rate = tuning::kSwayRate * (0.6f + 0.6f * strength);
    const float base = 0.55f + 0.45f * std::sin(t * rate + w.x * 0.011f + w.y * 0.007f);
    // Gust crests rolling downwind as visible waves.
    const float wave = std::sin((along * tuning::kGustSpacing - t * tuning::kGustRate) * kTau);
    const float crest = std::max(0.0f, wave);
    const float c2 = crest * crest;
    const float gust = c2 * c2 * c2; // ^6: narrow crests
    return strength * (base + tuning::kGustGain * gust);
}

std::optional<Flicker> parseFlicker(std::string_view id) {
    if (id == "steady") return Flicker::Steady;
    if (id == "gutter") return Flicker::Gutter;
    if (id == "breathe") return Flicker::Breathe;
    if (id == "leap") return Flicker::Leap;
    return std::nullopt;
}

float flicker(Flicker style, float hzLo, float hzHi, float depth, std::uint32_t seed, double now) {
    const float hz = hzLo + (hzHi - hzLo) * hash01(seed ^ 0x51ed270bU);
    const double t = now * static_cast<double>(hz);
    float v = 0;
    switch (style) {
    case Flicker::Steady: v = 0.5f + 0.5f * (noise1(t * 0.35, seed) - 0.5f); break;
    case Flicker::Gutter: {
        // A torch: a restless flame with now and then a deeper dip.
        const float dip = noise1(t * 0.25, seed ^ 0xa5a5a5a5U);
        v = 0.6f * noise1(t, seed) + 0.4f * dip * dip * dip;
        break;
    }
    case Flicker::Breathe:
        v = 0.5f +
            0.5f * std::sin(static_cast<float>(std::fmod(t, 1.0)) * kTau + hash01(seed) * kTau);
        break;
    case Flicker::Leap: v = 0.6f * noise1(t, seed) + 0.4f * noise1(t * 1.7, seed ^ 0x3c3cU); break;
    }
    return 1.0f - std::clamp(depth, 0.0f, 1.0f) * std::clamp(v, 0.0f, 1.0f);
}

} // namespace lc::gpu
