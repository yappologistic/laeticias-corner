#pragma once
// Which place the view is in, and when its era caption shows (docs/design/world-tech.md §4.8,
// docs/design/cities/world.md §8): the region under the view's centre (every tile belongs to one,
// so the most specific region there is a tile lookup), held for a moment before it counts so a
// boundary never flickers. A caption shows when the view arrives in a named place (the home, a
// city or a town) it was not visiting already; a visit ends when another place is entered or the
// view stays away for a while. Crossing into another moment (a region's `time`) is reported once
// for the seam's chime. Pure logic (no SDL).

#include "world/world_file.hpp"

#include <string>
#include <vector>

namespace lc::worldview {

class PlaceTracker {
public:
    PlaceTracker(std::vector<world::RegionKind> kinds, std::vector<std::string> times);

    // A jump or fast travel: the region counts at once and its caption shows (if it is a place).
    void reset(int region);
    void update(int region, float dt);

    // The region the view is in (after the dwell; -1 before any).
    [[nodiscard]] int region() const { return region_; }
    // The named place the view is in: the region when it is the home, a city or a town, else -1.
    [[nodiscard]] int place() const;
    // The place whose caption shows and its opacity (0 when none).
    [[nodiscard]] int caption() const { return caption_; }
    [[nodiscard]] float captionAlpha() const;
    // Set by the update that crossed into another moment, cleared by the next.
    [[nodiscard]] bool eraChanged() const { return eraChanged_; }
    // Set by the update that arrived in a new place.
    [[nodiscard]] bool arrived() const { return arrived_; }

private:
    [[nodiscard]] bool named(int region) const;
    void enter(int region);

    std::vector<world::RegionKind> kinds_;
    std::vector<std::string> times_;
    int region_ = -1;
    int candidate_ = -1;
    float dwell_ = 0;
    int visiting_ = -1; // the place of the current visit
    float away_ = 0;    // seconds out of it
    std::string era_;   // the moment last crossed into
    int caption_ = -1;
    float captionAge_ = 0;
    bool eraChanged_ = false;
    bool arrived_ = false;
};

} // namespace lc::worldview
