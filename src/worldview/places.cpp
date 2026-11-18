#include "worldview/places.hpp"

#include "worldview/tuning.hpp"

#include <algorithm>

namespace lc::worldview {

PlaceTracker::PlaceTracker(std::vector<world::RegionKind> kinds, std::vector<std::string> times)
    : kinds_(std::move(kinds)), times_(std::move(times)) {}

bool PlaceTracker::named(int region) const {
    if (region < 0 || region >= static_cast<int>(kinds_.size())) return false;
    const world::RegionKind k = kinds_[static_cast<std::size_t>(region)];
    return k == world::RegionKind::Home || k == world::RegionKind::City ||
           k == world::RegionKind::Town;
}

int PlaceTracker::place() const {
    return named(region_) ? region_ : -1;
}

void PlaceTracker::enter(int region) {
    region_ = region;
    if (region < 0 || region >= static_cast<int>(times_.size())) return;
    const std::string& time = times_[static_cast<std::size_t>(region)];
    // Seams and open sea name no moment: the era is the last one crossed into.
    if (time != "none" && !time.empty() && time != era_) {
        eraChanged_ = !era_.empty();
        era_ = time;
    }
    if (named(region)) {
        away_ = 0;
        if (region != visiting_) {
            visiting_ = region;
            caption_ = region;
            captionAge_ = 0;
            arrived_ = true;
        }
    }
}

void PlaceTracker::reset(int region) {
    eraChanged_ = arrived_ = false;
    candidate_ = region;
    dwell_ = 0;
    visiting_ = -1;
    caption_ = -1;
    enter(region);
}

void PlaceTracker::update(int region, float dt) {
    eraChanged_ = arrived_ = false;
    captionAge_ += dt;
    if (region != candidate_) {
        candidate_ = region;
        dwell_ = 0;
    } else {
        dwell_ += dt;
    }
    if (candidate_ != region_ && dwell_ >= tuning::kPlaceDwell) enter(candidate_);
    // Out of the visited place long enough: coming back is a new visit.
    if (visiting_ >= 0 && region_ != visiting_) {
        away_ += dt;
        if (away_ >= tuning::kVisitGap) visiting_ = -1;
    }
}

float PlaceTracker::captionAlpha() const {
    if (caption_ < 0 || captionAge_ >= tuning::kCaptionSeconds) return 0;
    return std::clamp(std::min(captionAge_, tuning::kCaptionSeconds - captionAge_) /
                          tuning::kCaptionFade,
                      0.0f, 1.0f);
}

} // namespace lc::worldview
