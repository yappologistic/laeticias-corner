#pragma once
// The seasons on the data pages (out/reports/art-data-contract.md §1, §4): each green ramp of the
// ramp table has season states (fresh, dry, dormant, turn); a climate says per month which one
// its grass and deciduous leaves show, and where snow lies. Pure: the remap rows and the snow
// cover the packed decode (decoder.hpp) reads.

#include "core/catalog.hpp"

#include <nlohmann/json_fwd.hpp>

#include <array>
#include <cstdint>
#include <span>
#include <vector>

namespace lc::gpu {

inline constexpr int kRampIds = 256;

struct RampSeasons {
    // Per ramp id: its green class (-1: none), and its state ramps for fresh, dry, dormant and
    // turn (0: the ramp has no such state).
    std::array<std::int8_t, kRampIds> green{};
    std::array<std::array<std::uint8_t, 4>, kRampIds> states{};
    std::uint8_t snow = 0;              // the snow ramp (class `snow`, the widest)
    std::array<bool, kRampIds> water{}; // class `water`: such texels are water for the look
};
// From `assets/atlas/ramps.json`. Ramps of class `grass` are grass, `foliage_deciduous` leaves.
[[nodiscard]] RampSeasons parseRamps(const nlohmann::json& ramps);

// The ramp each ramp id becomes in `climate`'s `month` (kRampIds entries).
void remapRow(const RampSeasons& r, const ClimateDef& climate, int month,
              std::span<std::uint8_t, kRampIds> out);

// How much of what catches snow is under it (0..1) at `level` in `climate`: snow lies above the
// month's snow line (half of it on the line's own level); it moves from the last month's cover
// to this month's over the morning (`dayFraction` 0..1 from midnight): building, thawing.
inline constexpr float kSnowMorning = 0.4f; // snow builds or thaws by this time of day
inline constexpr float kSnowStep = 0.05f;   // ... in steps of this much of the day
[[nodiscard]] float snowCover(const ClimateDef& climate, int month, float dayFraction, int level);

// The seasons over the land, per tile of a grid (built once, on a worker): the land's own level
// (a paved platform, a stair or a terrace takes the level of the nearest natural ground round it:
// snow comes with the land's altitude, not with what was built on it), and where two climates
// meet, the other climate within kSeasonBand tiles and how far it is (so a border blends over a
// band instead of cutting along the region grid).
inline constexpr int kSeasonBand = 20;
inline constexpr std::uint8_t kNoClimate = 255;
struct SeasonTile {
    std::uint8_t landLevel = 0;
    std::uint8_t other = kNoClimate; // the nearest other climate, kNoClimate: none in the band
    std::uint8_t distance = 0;       // tiles to it
};
// `climate` (kNoClimate: none), `level` and `natural` (not paved) per tile, row by row.
[[nodiscard]] std::vector<SeasonTile> seasonField(int w, int h,
                                                  std::span<const std::uint8_t> climate,
                                                  std::span<const std::uint8_t> level,
                                                  std::span<const std::uint8_t> natural);
// The share (0..0.5) of the other climate at a tile `distance` from the border, its edge broken
// by `noise` (-0.5..0.5, smooth over a few tiles): half at the border, none at the band's end.
[[nodiscard]] float otherShare(int distance, float noise);

} // namespace lc::gpu
