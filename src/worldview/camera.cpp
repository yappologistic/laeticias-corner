#include "worldview/camera.hpp"

#include "worldview/tuning.hpp"

#include <algorithm>
#include <cmath>

namespace lc::worldview {
namespace {

float smooth(float t) {
    t = std::clamp(t, 0.0f, 1.0f);
    return t * t * (3.0f - 2.0f * t);
}

} // namespace

WorldCamera::WorldCamera(Iso iso, int gridW, int gridH, float raise)
    : iso_(iso), gridW_(gridW), gridH_(gridH), level_(tuning::kDefaultZoom),
      scale_(levelScale(tuning::kDefaultZoom)) {
    const auto w = static_cast<float>(gridW);
    const auto h = static_cast<float>(gridH);
    box_ = {iso.toWorld(0, h).x, iso.toWorld(0, 0).y - raise, iso.toWorld(w, 0).x,
            iso.toWorld(w, h).y};
    lookAtTile({w * 0.5f, h * 0.5f});
}

int WorldCamera::levels() {
    return 1 + static_cast<int>(tuning::kZoomLevels.size());
}

float WorldCamera::levelScale(int level) const {
    if (level <= 0) {
        const float fit =
            std::min(screen_.x / (box_.x1 - box_.x0), screen_.y / (box_.y1 - box_.y0));
        return fit * tuning::kOverviewMargin;
    }
    return tuning::kZoomLevels[static_cast<std::size_t>(std::min(level, levels() - 1) - 1)];
}

int WorldCamera::levelFor(float zoom) const {
    if (zoom <= 0) return 0;
    int best = 0;
    for (int l = 1; l < levels(); ++l)
        if (std::abs(std::log(levelScale(l) / zoom)) < std::abs(std::log(levelScale(best) / zoom)))
            best = l;
    return best;
}

void WorldCamera::setScreen(Vec2 px) {
    screen_ = px;
    if (!flying()) scale_ = levelScale(level_);
}

void WorldCamera::setLevel(int level) {
    level_ = std::clamp(level, 0, levels() - 1);
    flight_.duration = 0;
    scale_ = levelScale(level_);
    // The overview shows the whole world.
    if (level_ == 0) pos_ = clamped({(box_.x0 + box_.x1) * 0.5f, (box_.y0 + box_.y1) * 0.5f});
}

Vec2 WorldCamera::clamped(Vec2 world) const {
    // Keep the centre over the grid: clamp in tile space, where the grid is a rectangle.
    Vec2 t = iso_.toTile(world);
    t.x = std::clamp(t.x, 0.0f, static_cast<float>(gridW_));
    t.y = std::clamp(t.y, 0.0f, static_cast<float>(gridH_));
    return iso_.toWorld(t.x, t.y);
}

void WorldCamera::lookAt(Vec2 world) {
    flight_.duration = 0;
    scale_ = levelScale(level_);
    pos_ = clamped(world);
}

void WorldCamera::panBy(Vec2 d) {
    pos_ = clamped({pos_.x + d.x / scale_, pos_.y + d.y / scale_});
}

void WorldCamera::flyTo(Vec2 world, int level, float seconds) {
    level = std::clamp(level, 0, levels() - 1);
    const Vec2 to =
        clamped(level == 0 ? Vec2{(box_.x0 + box_.x1) * 0.5f, (box_.y0 + box_.y1) * 0.5f} : world);
    const float s1 = levelScale(level);
    const float dist = std::hypot(to.x - pos_.x, to.y - pos_.y);
    // Mid-way the view is wide enough to hold both ends, but never wider than the overview.
    const float fit = dist > 0 ? 0.8f * std::min(screen_.x, screen_.y) / dist : s1;
    const float sMid = std::max(std::min({scale_, s1, fit}), levelScale(0));
    flight_ = {pos_, to, scale_, sMid, s1, 0, std::max(seconds, 1e-3f)};
    level_ = level;
}

void WorldCamera::update(float dt) {
    if (!flying()) return;
    Flight& f = flight_;
    f.t = std::min(f.t + dt, f.duration);
    const float u = f.t / f.duration;
    const float k = smooth(u);
    pos_ = clamped({f.from.x + (f.to.x - f.from.x) * k, f.from.y + (f.to.y - f.from.y) * k});
    // Scale eases out to the middle and back in, in log space so each zoom step takes as long.
    const float a = u < 0.5f ? f.s0 : f.sMid;
    const float b = u < 0.5f ? f.sMid : f.s1;
    const float v = smooth(u < 0.5f ? 2.0f * u : 2.0f * u - 1.0f);
    scale_ = std::exp(std::log(a) + (std::log(b) - std::log(a)) * v);
    if (f.t >= f.duration) {
        f.duration = 0;
        scale_ = f.s1;
        pos_ = f.to;
    }
}

FRect WorldCamera::view() const {
    const float hw = screen_.x * 0.5f / scale_;
    const float hh = screen_.y * 0.5f / scale_;
    return {pos_.x - hw, pos_.y - hh, pos_.x + hw, pos_.y + hh};
}

Vec2 WorldCamera::screenToWorld(Vec2 px) const {
    return {pos_.x + (px.x - screen_.x * 0.5f) / scale_,
            pos_.y + (px.y - screen_.y * 0.5f) / scale_};
}

Vec2 WorldCamera::worldToScreen(Vec2 w) const {
    return {(w.x - pos_.x) * scale_ + screen_.x * 0.5f, (w.y - pos_.y) * scale_ + screen_.y * 0.5f};
}

} // namespace lc::worldview
