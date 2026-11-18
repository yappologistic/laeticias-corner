#pragma once
// Eased camera over the world: a few fixed zoom levels with eased transitions, framing that keeps
// the land clear of the interface, and pan limits that always keep some land on screen.

#include "core/iso.hpp"

#include <array>

namespace lc {

struct WorldBounds {
    float x0 = 0;
    float y0 = 0;
    float x1 = 0;
    float y1 = 0;
};

// Screen area left free by the interface, in window pixels.
struct SafeArea {
    float x0 = 0;
    float y0 = 0;
    float x1 = 0;
    float y1 = 0;
};

// Window pixels per art pixel at each level. 1 is the art's native density (the natural view on
// 1080p and 1440p), 2 and 3 magnify. Below 1 are the overviews, the only levels drawn with linear
// filtering: half scale, and quarter scale so the whole island still fits small windows.
inline constexpr std::array<float, 5> kZoomLevels{0.25f, 0.5f, 1.0f, 2.0f, 3.0f};
inline constexpr int kDefaultZoomLevel = 2;

// World-pixel box of a tile rectangle's ground, plus `below` px of cliff under its south rims.
[[nodiscard]] WorldBounds landBox(Iso iso, TileRect land, float below);
// Largest level at which `box` fits inside `safe` (with a little air); the overview otherwise.
[[nodiscard]] int fitLevel(WorldBounds box, SafeArea safe);

class Camera {
public:
    Camera(Iso iso, TileRect land, float cliffDepth);

    // The land changed shape (another map was loaded), or the cliff art is known.
    void setLand(TileRect land, float cliffDepth);
    void update(float dt, Vec2 screen);
    // Picks the largest level that shows `focus` (the open land) inside `safe` and centres it
    // there; the cliff under the south rims counts when the focus reaches them.
    void frame(SafeArea safe, Vec2 screen, TileRect focus);
    // Puts the view centre at `world` at the level nearest `zoom` (a restored view).
    void place(Vec2 world, float zoom, Vec2 screen);
    // Eased pan that centres the view on a world point.
    void panTo(Vec2 world, Vec2 screen);
    // Immediate pan by a screen-space delta (mouse drag).
    void dragBy(Vec2 screenDelta, Vec2 screen);
    // Eased pan by a screen-space delta (keys).
    void nudge(Vec2 screenDelta, Vec2 screen);
    // Eases to another level keeping the world point under `screenPx` fixed.
    void zoomTo(int level, Vec2 screenPx, Vec2 screen);

    [[nodiscard]] int level() const { return level_; }
    // The level's scale (the destination while a transition runs).
    [[nodiscard]] float zoom() const { return kZoomLevels[static_cast<std::size_t>(level_)]; }
    // The scale currently on screen.
    [[nodiscard]] float scale() const { return scale_; }
    [[nodiscard]] bool settled() const { return scale_ == zoom(); }
    [[nodiscard]] Vec2 position() const { return pos_; }
    // Rendering runs between simulation steps: call beginStep() before each step's update, then
    // draw with interpolated(alpha), alpha being how far the frame is from the last step toward
    // the next (1: exactly the latest step). Immediate moves (drags, framing) are never smoothed.
    void beginStep() {
        prevPos_ = pos_;
        prevScale_ = scale_;
    }
    [[nodiscard]] Camera interpolated(float alpha) const;
    // Reduce motion: pans and zooms arrive at once instead of easing.
    void setEasing(bool on) { easing_ = on; }
    [[nodiscard]] Vec2 screenToWorld(Vec2 px, Vec2 screen) const;
    [[nodiscard]] Vec2 worldToScreen(Vec2 world, Vec2 screen) const;

private:
    void clamp(Vec2& p, Vec2 screen, float scale) const;

    Iso iso_;
    TileRect land_;
    float cliffDepth_;
    Vec2 pos_;
    Vec2 target_;
    int level_ = kDefaultZoomLevel;
    float scale_ = kZoomLevels[kDefaultZoomLevel];
    // Zoom transitions keep this world point under this screen point.
    Vec2 anchorWorld_;
    Vec2 anchorPx_;
    Vec2 prevPos_; // at the last step, for interpolated drawing
    float prevScale_ = kZoomLevels[kDefaultZoomLevel];
    bool easing_ = true;
};

} // namespace lc
