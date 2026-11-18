#pragma once
// Region themes around the camera (docs/design/world-tech.md §4.6, §4.8): the district plane's
// weights low-passed over a second, the regions' grading keyframes mixed by weight and by the
// clock, the haze, and which region's era caption shows (with hysteresis). Pure logic (no SDL).

#include "core/clock.hpp"
#include "world/region_file.hpp"
#include "world/world_map.hpp"

#include <span>
#include <string>
#include <vector>

namespace lc::worldview {

struct Grade {
    Rgb mul;                // multiplies the clock's ambient light
    Rgb haze;               // colour the view leans towards
    float hazeStrength = 0; // how far, 0..1
};

// A theme's grading multiplier at clock time t (0..1): its four keyframes sit at the phase
// centres and blend smoothly between neighbours.
[[nodiscard]] Rgb gradingAt(const world::Theme& theme, double t);

class ThemeMixer {
public:
    // One theme per WorldFile region (regions without a file use the default theme) and each
    // region's `time` (the moment its caption names).
    ThemeMixer(std::vector<world::Theme> themes, std::vector<std::string> times);

    // Snaps the weights (a jump or fast travel resets the low-pass).
    void reset(std::span<const world::RegionWeight> w);
    void update(std::span<const world::RegionWeight> w, float dt);
    [[nodiscard]] Grade grade(double clockT) const;
    [[nodiscard]] float weight(int region) const {
        return smoothed_[static_cast<std::size_t>(region)];
    }
    // The region the view belongs to (-1 before any weight); changes only past the hysteresis.
    [[nodiscard]] int dominant() const { return dominant_; }
    // The region whose caption is showing and its opacity (0 when none).
    [[nodiscard]] int captionRegion() const { return caption_; }
    [[nodiscard]] float captionAlpha() const;

private:
    void settle(float dt);

    std::vector<world::Theme> themes_;
    std::vector<std::string> times_;
    std::vector<float> target_;
    std::vector<float> smoothed_;
    int dominant_ = -1;
    std::string captionedTime_;
    int caption_ = -1;
    float captionAge_ = 0;
};

} // namespace lc::worldview
