#include "render/camera.hpp"

#include "core/tuning.hpp"

#include <algorithm>
#include <cmath>

namespace lc {

WorldBounds landBox(Iso iso, TileRect land, float below) {
    const auto f = [](int v) { return static_cast<float>(v); };
    return {iso.toWorld(f(land.x0), f(land.y1)).x, iso.toWorld(f(land.x0), f(land.y0)).y,
            iso.toWorld(f(land.x1), f(land.y0)).x, iso.toWorld(f(land.x1), f(land.y1)).y + below};
}

int fitLevel(WorldBounds box, SafeArea safe) {
    const float w = (safe.x1 - safe.x0) * tuning::kFrameFill;
    const float h = (safe.y1 - safe.y0) * tuning::kFrameFill;
    for (int l = static_cast<int>(kZoomLevels.size()) - 1; l > 0; --l) {
        const float s = kZoomLevels[static_cast<std::size_t>(l)];
        if ((box.x1 - box.x0) * s <= w && (box.y1 - box.y0) * s <= h) return l;
    }
    return 0;
}

Camera::Camera(Iso iso, TileRect land, float cliffDepth)
    : iso_(iso), land_(land), cliffDepth_(cliffDepth) {
    const WorldBounds b = landBox(iso_, land_, cliffDepth_);
    pos_ = target_ = prevPos_ = {(b.x0 + b.x1) * 0.5f, (b.y0 + b.y1) * 0.5f};
}

void Camera::setLand(TileRect land, float cliffDepth, float reach) {
    land_ = land;
    cliffDepth_ = cliffDepth;
    reach_ = reach;
}

void Camera::clamp(Vec2& p, Vec2 screen, float scale) const {
    if (land_.empty()) return;
    // Clamp the view centre, in tile space, to the land's rectangle grown by m tiles. A point m
    // tiles (or less) beyond the rectangle along both axes is at most 2m half-tiles away on screen,
    // so with m chosen from the half view the nearest land stays inside the inner part of the
    // window at every zoom.
    const float halfW = screen.x * 0.5f / scale;
    const float halfH = screen.y * 0.5f / scale;
    const float m = std::max(0.0f, reach_ * std::min(halfW / iso_.tileW(), halfH / iso_.tileH()));
    Vec2 t = iso_.toTile(p);
    t.x = std::clamp(t.x, static_cast<float>(land_.x0) - m, static_cast<float>(land_.x1) + m);
    t.y = std::clamp(t.y, static_cast<float>(land_.y0) - m, static_cast<float>(land_.y1) + m);
    p = iso_.toWorld(t.x, t.y);
}

Camera Camera::snapped(Vec2 screen) const {
    Camera c = *this;
    const auto snap = [&](float p, float half) {
        return (std::round((p - half / scale_) * scale_) / scale_) + half / scale_;
    };
    c.pos_ = {snap(pos_.x, screen.x * 0.5f), snap(pos_.y, screen.y * 0.5f)};
    return c;
}

Camera Camera::interpolated(float alpha) const {
    if (alpha >= 1.0f) return *this;
    Camera c = *this;
    c.pos_ = {prevPos_.x + (pos_.x - prevPos_.x) * alpha,
              prevPos_.y + (pos_.y - prevPos_.y) * alpha};
    c.scale_ = std::exp(std::log(prevScale_) + (std::log(scale_) - std::log(prevScale_)) * alpha);
    return c;
}

void Camera::update(float dt, Vec2 screen) {
    if (scale_ != zoom()) {
        // Ease in log space so every level change feels the same, keeping the anchor in place.
        const float k = easing_ ? 1.0f - std::exp(-tuning::kZoomEase * dt) : 1.0f;
        const float a = std::log(scale_);
        const float b = std::log(zoom());
        scale_ = std::abs(b - a) < 0.002f ? zoom() : std::exp(a + (b - a) * k);
        pos_ = {anchorWorld_.x - (anchorPx_.x - screen.x * 0.5f) / scale_,
                anchorWorld_.y - (anchorPx_.y - screen.y * 0.5f) / scale_};
        clamp(pos_, screen, scale_);
        target_ = pos_;
        return;
    }
    const float k = easing_ ? 1.0f - std::exp(-tuning::kCameraEase * dt) : 1.0f;
    clamp(target_, screen, scale_);
    pos_.x += (target_.x - pos_.x) * k;
    pos_.y += (target_.y - pos_.y) * k;
    if (std::abs(target_.x - pos_.x) < 0.01f && std::abs(target_.y - pos_.y) < 0.01f)
        pos_ = target_;
}

void Camera::frame(SafeArea safe, Vec2 screen, TileRect focus) {
    const bool rim = focus.x1 >= land_.x1 || focus.y1 >= land_.y1;
    const WorldBounds b = landBox(iso_, focus, rim ? cliffDepth_ : 0.0f);
    level_ = fitLevel(b, safe);
    scale_ = zoom();
    // Put the land's centre at the safe area's centre, not the window's.
    const Vec2 centre{(b.x0 + b.x1) * 0.5f, (b.y0 + b.y1) * 0.5f};
    const Vec2 safeCentre{(safe.x0 + safe.x1) * 0.5f, (safe.y0 + safe.y1) * 0.5f};
    pos_ = target_ = {centre.x - (safeCentre.x - screen.x * 0.5f) / scale_,
                      centre.y - (safeCentre.y - screen.y * 0.5f) / scale_};
    clamp(pos_, screen, scale_);
    target_ = prevPos_ = pos_;
    prevScale_ = scale_;
}

void Camera::place(Vec2 world, float zoom, Vec2 screen) {
    level_ = 0;
    for (std::size_t l = 0; l < kZoomLevels.size(); ++l)
        if (std::abs(kZoomLevels[l] - zoom) <
            std::abs(kZoomLevels[static_cast<std::size_t>(level_)] - zoom))
            level_ = static_cast<int>(l);
    scale_ = this->zoom();
    pos_ = world;
    clamp(pos_, screen, scale_);
    target_ = prevPos_ = pos_;
    prevScale_ = scale_;
}

void Camera::panTo(Vec2 world, Vec2 screen) {
    target_ = world;
    clamp(target_, screen, scale_);
}

void Camera::dragBy(Vec2 d, Vec2 screen) {
    target_ = {target_.x - d.x / scale_, target_.y - d.y / scale_};
    clamp(target_, screen, scale_);
    // The hand moves the view at once: the last step's view moves with it, so no smoothing lags
    // behind the pointer.
    prevPos_ = {prevPos_.x + target_.x - pos_.x, prevPos_.y + target_.y - pos_.y};
    pos_ = target_;
    anchorWorld_ = {anchorWorld_.x - d.x / scale_, anchorWorld_.y - d.y / scale_};
}

void Camera::nudge(Vec2 d, Vec2 screen) {
    target_ = {target_.x + d.x / scale_, target_.y + d.y / scale_};
    clamp(target_, screen, scale_);
}

void Camera::zoomTo(int level, Vec2 px, Vec2 screen) {
    level = std::clamp(level, 0, static_cast<int>(kZoomLevels.size()) - 1);
    if (level == level_) return;
    anchorWorld_ = screenToWorld(px, screen);
    anchorPx_ = px;
    level_ = level;
}

Vec2 Camera::screenToWorld(Vec2 px, Vec2 screen) const {
    return {pos_.x + (px.x - screen.x * 0.5f) / scale_, pos_.y + (px.y - screen.y * 0.5f) / scale_};
}

Vec2 Camera::worldToScreen(Vec2 w, Vec2 screen) const {
    return {(w.x - pos_.x) * scale_ + screen.x * 0.5f, (w.y - pos_.y) * scale_ + screen.y * 0.5f};
}

} // namespace lc
