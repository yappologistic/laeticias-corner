#pragma once
// The world's lights for the shader path (graphics plan §3.1 step 2, task E1), from the world
// data (out/reports/world-nights.md): every region file's `lights.profiles` and `light_points`
// matched to the placed items they name. A light sits at its item's emitter or glow layer, and
// its pool's centre on the ground in front of it. Lights are bucketed by map chunk once, at
// load; a frame visits only the chunks it shows. Glowing items in a region with light points
// that no point names stay dark at night (the data's rhythm of pools and shadow); elsewhere every
// glow layer glows as on the classic path.

#include "core/clock.hpp"
#include "core/iso.hpp"
#include "render/gpu/look.hpp"
#include "world/loader.hpp"
#include "worldview/gather.hpp"
#include "worldview/world_sprites.hpp"

#include <cstdint>
#include <span>
#include <string>
#include <vector>

namespace lc::worldview {

enum class LightRain : std::uint8_t { Sheltered, Dim, Out };

struct LightProfile {
    std::string id;
    std::string kind; // window, door, lamp, torch, brazier, fire, ...
    Rgb colour{1.0f, 0.66f, 0.36f};
    float radius = 2; // tiles
    float strength = 0.7f;
    gpu::Flicker flicker = gpu::Flicker::Steady;
    float hzLo = 4;
    float hzHi = 7;
    float depth = 0.05f;
    std::vector<std::pair<float, float>> hours; // game hours [on, off); off < on: past midnight
    LightRain rain = LightRain::Sheltered;
    bool festivalOnly = false; // `only`: lit on a festival's or an event's night alone
    bool staggered = false;    // windows and doors light one by one
};

[[nodiscard]] LightProfile parseLightProfile(std::string_view id, const nlohmann::json& j);
// How far a profile's hours have it on at game hour `hour` (0..24), with its light's own
// stagger: 0 out, 1 burning, fading over tuning::kWindowFadeHours.
[[nodiscard]] float hoursOn(const LightProfile& p, float hour, std::uint32_t seed);

struct WorldLight {
    Vec2 at;     // world px, the flame (raised by the item's level)
    Vec2 ground; // world px, the pool's centre on the ground
    std::uint32_t seed = 0;
    std::uint16_t profile = 0;
};

class WorldLights {
public:
    // Reads every region's lights and matches each point to its item (points naming no item at
    // their tile are counted in unmatched()). The hole's items are the game's own.
    WorldLights(const world::LoadedWorld& world, const WorldSprites& sprites, Hole hole);

    // This frame's state of every profile: the clock (0..1) and seconds since start.
    void update(double clock, double now);
    // Lights of the chunks meeting `tiles` with their colour now (already times strength,
    // flicker, hours and rain): `rain(Vec2 tile)` says how hard it rains at a grid point (asked
    // only for lights rain puts out or dims); `f(const WorldLight&, Rgb colour, float radius)`
    // with the radius in tiles.
    template <typename R, typename F>
    void forEach(TileRect tiles, R&& rain, F&& f) const;
    // Whether a placed item's glow layer burns now (true for items the data does not govern).
    [[nodiscard]] bool glowOn(std::uint32_t item) const;
    [[nodiscard]] std::size_t count() const { return lights_.size(); }
    [[nodiscard]] int unmatched() const { return unmatched_; }
    [[nodiscard]] std::span<const LightProfile> profiles() const { return profiles_; }

private:
    [[nodiscard]] Rgb colourOf(const WorldLight& l, float rain) const;
    [[nodiscard]] Vec2 tileOf(const WorldLight& l) const;

    const world::WorldMap& map_;
    std::vector<LightProfile> profiles_;
    std::vector<WorldLight> lights_;   // by chunk (CSR)
    std::vector<std::uint32_t> start_; // per chunk, then one past the end
    // Items with a light point, sorted, each with its points' profiles and seeds (a window's
    // glow and its pool light together); and per item whether the data governs its glow.
    struct Named {
        std::uint32_t item = 0;
        std::uint16_t profile = 0;
        std::uint32_t seed = 0;
        auto operator<=>(const Named&) const = default;
    };
    std::vector<Named> named_;
    std::vector<bool> governed_;
    Iso iso_;
    // Per frame.
    float hour_ = 0;
    double now_ = 0;
    int unmatched_ = 0;
};

template <typename R, typename F>
void WorldLights::forEach(TileRect tiles, R&& rain, F&& f) const {
    const TileRect t = tiles.clipped(map_.bounds());
    if (t.empty() || start_.empty()) return;
    for (int cy = t.y0 >> kChunkShift; cy <= (t.y1 - 1) >> kChunkShift; ++cy)
        for (int cx = t.x0 >> kChunkShift; cx <= (t.x1 - 1) >> kChunkShift; ++cx) {
            const auto c = static_cast<std::size_t>(cy * map_.chunksX() + cx);
            for (std::uint32_t i = start_[c]; i < start_[c + 1]; ++i) {
                const WorldLight& l = lights_[i];
                const LightProfile& p = profiles_[l.profile];
                const Rgb col =
                    colourOf(l, p.rain == LightRain::Sheltered ? 0.0f : rain(tileOf(l)));
                if (col.r + col.g + col.b <= 0.002f) continue;
                f(l, col, p.radius);
            }
        }
}

} // namespace lc::worldview
