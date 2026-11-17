#include "render/camera.hpp"

#include "core/tuning.hpp"

#include <algorithm>
#include <cmath>

namespace lc {
namespace {
constexpr float kCliffDepth = 40.0f; // world px of cliff below the south rims
} // namespace

WorldBounds islandBounds(int mapW, int mapH) {
    return {-static_cast<float>(mapH * kHalfTileW), 0.0f, static_cast<float>(mapW * kHalfTileW),
            static_cast<float>((mapW + mapH) * kHalfTileH) + kCliffDepth};
}

int defaultZoom(Vec2 screen, int mapW, int mapH) {
    const WorldBounds b = islandBounds(mapW, mapH);
    // Let the island fill most of the view; a little cropping at the sides is fine.
    const float fit = std::min(screen.x * 1.2f / (b.x1 - b.x0), screen.y * 1.1f / (b.y1 - b.y0));
    return std::clamp(static_cast<int>(fit), tuning::kMinZoom, tuning::kMaxZoom);
}

Camera::Camera(int mapW, int mapH) : bounds_(islandBounds(mapW, mapH)), mapW_(mapW), mapH_(mapH) {
    pos_ = target_ = {(bounds_.x0 + bounds_.x1) * 0.5f, (bounds_.y0 + bounds_.y1) * 0.5f};
}

void Camera::clamp(Vec2& p) const {
    const float m = tuning::kCameraMargin;
    p.x = std::clamp(p.x, bounds_.x0 - m, bounds_.x1 + m);
    p.y = std::clamp(p.y, bounds_.y0 - m, bounds_.y1 + m);
}

void Camera::update(float dt) {
    const float k = 1.0f - std::exp(-tuning::kCameraEase * dt);
    pos_.x += (target_.x - pos_.x) * k;
    pos_.y += (target_.y - pos_.y) * k;
    if (std::abs(target_.x - pos_.x) < 0.01f && std::abs(target_.y - pos_.y) < 0.01f)
        pos_ = target_;
}

void Camera::recentre(Vec2 screen) {
    zoom_ = defaultZoom(screen, mapW_, mapH_);
    target_ = {(bounds_.x0 + bounds_.x1) * 0.5f, (bounds_.y0 + bounds_.y1) * 0.5f};
}

void Camera::dragBy(Vec2 d) {
    const auto z = static_cast<float>(zoom_);
    target_ = {target_.x - d.x / z, target_.y - d.y / z};
    clamp(target_);
    pos_ = target_;
}

void Camera::nudge(Vec2 d) {
    const auto z = static_cast<float>(zoom_);
    target_ = {target_.x + d.x / z, target_.y + d.y / z};
    clamp(target_);
}

void Camera::zoomAt(int zoom, Vec2 px, Vec2 screen) {
    zoom = std::clamp(zoom, tuning::kMinZoom, tuning::kMaxZoom);
    if (zoom == zoom_) return;
    const Vec2 anchor = screenToWorld(px, screen);
    zoom_ = zoom;
    const auto z = static_cast<float>(zoom_);
    pos_ = {anchor.x - (px.x - screen.x * 0.5f) / z, anchor.y - (px.y - screen.y * 0.5f) / z};
    clamp(pos_);
    target_ = pos_;
}

Vec2 Camera::screenToWorld(Vec2 px, Vec2 screen) const {
    const auto z = static_cast<float>(zoom_);
    return {pos_.x + (px.x - screen.x * 0.5f) / z, pos_.y + (px.y - screen.y * 0.5f) / z};
}

Vec2 Camera::worldToScreen(Vec2 w, Vec2 screen) const {
    const auto z = static_cast<float>(zoom_);
    return {(w.x - pos_.x) * z + screen.x * 0.5f, (w.y - pos_.y) * z + screen.y * 0.5f};
}

} // namespace lc
