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

} // namespace lc::gpu
