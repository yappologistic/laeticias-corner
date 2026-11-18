#pragma once
// The world viewer's camera: a centre in world pixels and a zoom level, clamped so the centre
// always lies over the world's grid, with jumps, pans and eased flights that zoom out on the way
// (docs/design/world-tech.md §4.7). Pure logic (no SDL). World pixels stay below 2^16 on the
// 448 x 1280 grid, where float still resolves 1/256 px (core/iso.hpp).

#include "core/iso.hpp"

namespace lc::worldview {

class WorldCamera {
public:
    // `raise`: the most a tile is lifted by its level, px (it widens the world's box upward).
    WorldCamera(Iso iso, int gridW, int gridH, float raise);

    // Window size in pixels; the overview level's scale follows it.
    void setScreen(Vec2 px);
    [[nodiscard]] Vec2 screen() const { return screen_; }

    // Levels: 0 is the overview (the whole world fits), then tuning::kZoomLevels.
    [[nodiscard]] static int levels();
    [[nodiscard]] float levelScale(int level) const;
    // The level whose scale is nearest `zoom` (0 or less: the overview).
    [[nodiscard]] int levelFor(float zoom) const;
    void setLevel(int level);
    [[nodiscard]] int level() const { return level_; }
    // Window px per world px now; between levels while a flight runs.
    [[nodiscard]] float scale() const { return scale_; }

    void lookAt(Vec2 world);
    void lookAtTile(Vec2 tile) { lookAt(iso_.toWorld(tile.x, tile.y)); }
    void panBy(Vec2 screenDelta);
    // Eased flight to `world` arriving at `level`, zooming out mid-way so both ends are in view.
    void flyTo(Vec2 world, int level, float seconds);
    void update(float dt);
    [[nodiscard]] bool flying() const { return flight_.duration > 0; }
    // Where the flight ends: the view's centre and scale (meaningful while flying).
    [[nodiscard]] Vec2 arrival() const { return flight_.to; }
    [[nodiscard]] float arrivalScale() const { return flight_.s1; }

    [[nodiscard]] Vec2 centre() const { return pos_; }
    [[nodiscard]] FRect view() const; // world px on screen
    [[nodiscard]] Vec2 screenToWorld(Vec2 px) const;
    [[nodiscard]] Vec2 worldToScreen(Vec2 world) const;
    // World px box of the whole grid, raised tiles included.
    [[nodiscard]] FRect worldBox() const { return box_; }
    [[nodiscard]] Iso iso() const { return iso_; }

private:
    [[nodiscard]] Vec2 clamped(Vec2 world) const;

    struct Flight {
        Vec2 from;
        Vec2 to;
        float s0 = 1;
        float sMid = 1;
        float s1 = 1;
        float t = 0;
        float duration = 0; // 0: none
    };

    Iso iso_;
    int gridW_;
    int gridH_;
    FRect box_;
    Vec2 screen_{1280, 800};
    Vec2 pos_;
    int level_;
    float scale_;
    Flight flight_;
};

} // namespace lc::worldview
