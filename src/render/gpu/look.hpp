#pragma once
// The shader path's pure side (docs/design/graphics-plan.md §3, task E1): the quality tiers, the
// region grade read from `theme.look` (per phase, blended by the clock, the regions in view and
// the season), the world's wind for sway and the flames' flicker. No SDL.

#include "core/clock.hpp"
#include "core/iso.hpp"

#include <nlohmann/json_fwd.hpp>

#include <array>
#include <cstdint>
#include <optional>
#include <string_view>

namespace lc::gpu {

// The Look setting (graphics plan §3.2). Classic is today's frame on any renderer; the others
// need SDL's `gpu` driver and fall back to Classic where it cannot be made.
enum class Quality : std::uint8_t { Classic, Low, Medium, High };
inline constexpr int kQualityCount = 4;
[[nodiscard]] std::optional<Quality> parseQuality(std::string_view id);
[[nodiscard]] std::string_view qualityId(Quality q);
// A region's water in one season, from its body colour (`theme.look.water.body`): offshore
// deeper and richer, the shallows leaning turquoise, rivers greener and a little turbid; autumn
// and winter greyer (`season` indexes kSeasonIds, -1 none).
struct WaterColours {
    Rgb shallow;
    Rgb deep;
    Rgb river;
};
[[nodiscard]] WaterColours waterColours(Rgb body, int season);

// The sun over the day (grid axes: +x down-right, +y down-left, z up; the art's normals use them):
// it rises at the noon direction less a quarter turn and sets at it plus a quarter turn, the
// noon direction being the art's baked sun's, highest at noon by the season.
struct Sun {
    float dir[3] = {0, 0, 1}; // unit, toward the sun
    float elevation = 0;      // radians above the horizon
    float strength = 0;       // 0 below the horizon .. 1 once a few degrees up
};
[[nodiscard]] Sun sunAt(double clock, int season);
// The art's baked sun (tools/artgen render.py SUN) and the one its cast shadows used.
inline constexpr float kBakedSun[3] = {-0.45f, 0.28f, 0.85f};
inline constexpr float kBakedShadowSun[3] = {-0.38f, 0.16f, 0.91f};
// The ground-plane map (screen x, 2 * screen y, so distances are round) that turns a baked
// shadow's offset from its caster toward `sun`'s shadow: offsets along the baked shadow's way
// are stretched and turned onto the sun's, those behind the caster stay. `out` is a 2 x 2
// matrix (row major) and the baked shadow's unit direction.
struct ShadowWarp {
    float m[4] = {1, 0, 0, 1};
    float along[2] = {0, 1}; // the baked shadow's direction (unit, ground plane)
};
[[nodiscard]] ShadowWarp shadowWarp(const Sun& sun);

// A cumulus for the cloud pass (post.hpp CloudParams).
struct Cloud {
    Vec2 ground;      // world px of the point it stands over
    float width = 0;  // px at full growth
    float seed = 0;   // its billows' shape
    float growth = 0; // 0..1 as its weather cell grows and fades
    float dark = 0;   // 0 fair, 1 a rain cloud
    Vec2 parallax;    // world px it is seen moved from over its point (it is high up)
};
// The clouds setting: the deck and its shadows, the shadows alone, or neither.
enum class Clouds : std::uint8_t { On, Shadows, Off };
inline constexpr int kCloudModes = 3;
[[nodiscard]] std::optional<Clouds> parseClouds(std::string_view id);
[[nodiscard]] std::string_view cloudsId(Clouds c);

// One phase of a region's grade, as `theme.look.phases.<phase>` writes it (tools/worldgen
// look.py): white balance and exposure, split toning around mid grey, an S-curve, a highlight
// shoulder and saturation weighted to the midtones.
struct GradePhase {
    Rgb wb{1, 1, 1};
    float exposure = 1;
    Rgb shadowTint{0.5f, 0.5f, 0.5f};
    Rgb highTint{0.5f, 0.5f, 0.5f};
    float tint = 0;
    float contrast = 0;
    float saturation = 1;
    float shoulder = 0;
};

// What the seasons change in a region's grade (`theme.seasons.<season>`): a multiplier on the
// white balance, and `look` shifts of saturation and warmth.
struct SeasonGrade {
    Rgb wb{1, 1, 1};
    float saturation = 0;
    float warmth = 0;
};

inline constexpr int kPhases = 4;  // dawn, day, dusk, night: the files' order
inline constexpr int kSeasons = 4; // spring, summer, autumn, winter
inline constexpr std::array<std::string_view, kSeasons> kSeasonIds{"spring", "summer", "autumn",
                                                                   "winter"};

struct RegionLook {
    std::array<GradePhase, kPhases> phases;
    std::array<std::array<Rgb, 3>, kPhases> sky; // top, middle, horizon
    std::array<Rgb, kPhases> shade;              // the sky's light in shade (`theme.look.shade`)
    Rgb haze{0.91f, 0.89f, 0.83f};
    std::array<float, 4> hazeByLod{0.04f, 0.12f, 0.18f, 0.26f}; // native, half, quarter, overview
    std::array<SeasonGrade, kSeasons> seasons;
    Rgb water{0.29f, 0.56f, 0.69f}; // the water's body colour (`theme.look.water.body`)
};

// The home's look (the `home` family of tools/worldgen/worldgen/look.py): the corner has no
// region file, and regions whose file carries no `theme.look` use it too.
[[nodiscard]] const RegionLook& homeLook();
// `look` is `theme.look`, `seasons` is `theme.seasons` (either may be null or missing fields:
// those come from `fallback`).
[[nodiscard]] RegionLook parseLook(const nlohmann::json& look, const nlohmann::json& seasons,
                                   const RegionLook& fallback);

// A region's grade at a clock time (0..1, hour = 6 + 24 t): its four phases sit at the phase
// centres and blend smoothly; `season` indexes kSeasonIds (-1: none); `lod` 0..3 picks the haze.
struct GradeAt {
    GradePhase grade;
    std::array<Rgb, 3> sky;
    Rgb shade;
    Rgb haze;
    float hazeStrength = 0;
    Rgb water;
};
[[nodiscard]] GradeAt gradeAt(const RegionLook& look, double clock, int season, int lod);
// acc += g * w (every field, linearly): regions in view mix by their weights.
void accumulate(GradeAt& acc, const GradeAt& g, float w);
[[nodiscard]] GradeAt scaled(const GradeAt& g, float k);

// The grade applied to one colour on the CPU, exactly as shaders/final.frag does (tests, and the
// golden scenes' expectations): `night` 0..1 shifts toward `nightTint` (luma 1) at that luma.
[[nodiscard]] Rgb applyGrade(const GradePhase& g, Rgb c, Rgb nightTint = {1, 1, 1},
                             float night = 0);
// The tint low light shifts toward (luma 1), and how far a full night shifts.
[[nodiscard]] Rgb nightTint();

// One wind for the whole world: a slow sway everywhere plus gust crests rolling downwind.
// `dir` is the wind's unit direction in world px, `strength` 0..1; the result is the signed
// lean, in units of an item's full sway, at a world px point.
[[nodiscard]] float windLean(Vec2 worldPx, double now, Vec2 dir, float strength);

// How a flame's brightness moves (`lights.profiles.<id>.flicker.style`).
enum class Flicker : std::uint8_t { Steady, Gutter, Breathe, Leap };
[[nodiscard]] std::optional<Flicker> parseFlicker(std::string_view id);
// The brightness factor (1 - depth .. 1) of a light with this style, rate range (Hz) and depth,
// its own `seed`, at `now` seconds: smooth in time, different for every light.
[[nodiscard]] float flicker(Flicker style, float hzLo, float hzHi, float depth, std::uint32_t seed,
                            double now);

} // namespace lc::gpu
