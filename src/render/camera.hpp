#pragma once
// Eased camera over the world: integer zoom, pan limits that keep the island in view.

#include "core/iso.hpp"

namespace lc {

struct WorldBounds {
    float x0 = 0;
    float y0 = 0;
    float x1 = 0;
    float y1 = 0;
};

[[nodiscard]] WorldBounds islandBounds(int mapW, int mapH);
[[nodiscard]] int defaultZoom(Vec2 screen, int mapW, int mapH);

class Camera {
public:
    Camera(int mapW, int mapH);

    void update(float dt);
    void recentre(Vec2 screen);
    // Immediate pan by a screen-space delta (mouse drag).
    void dragBy(Vec2 screenDelta);
    // Eased pan by a screen-space delta (keys).
    void nudge(Vec2 screenDelta);
    // Changes zoom keeping the world point under `screenPx` fixed.
    void zoomAt(int zoom, Vec2 screenPx, Vec2 screen);

    [[nodiscard]] int zoom() const { return zoom_; }
    [[nodiscard]] Vec2 position() const { return pos_; }
    [[nodiscard]] Vec2 screenToWorld(Vec2 px, Vec2 screen) const;
    [[nodiscard]] Vec2 worldToScreen(Vec2 world, Vec2 screen) const;

private:
    void clamp(Vec2& p) const;

    WorldBounds bounds_;
    int mapW_;
    int mapH_;
    Vec2 pos_;
    Vec2 target_;
    int zoom_ = 2;
};

} // namespace lc
