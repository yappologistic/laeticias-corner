#pragma once
// The world map (docs/design/world-tech.md §4.7): the worldgen overview art (north-up, two px per
// tile) fitted to the window behind glass, the places as markers, their names on hover, the
// view's own place outlined, and a click on a place asks to travel there.

#include "core/iso.hpp"
#include "platform/sprite.hpp"
#include "ui/font.hpp"
#include "ui/painter.hpp"

#include <optional>
#include <span>
#include <string>
#include <string_view>
#include <vector>

namespace lc {

enum class MapMarker : std::uint8_t { Home, City, Town };

struct MapPlace {
    std::string_view name;
    std::string_view native; // the original-language form, or empty
    std::string_view era;    // the moment it is remembered at, or empty
    Vec2 at;                 // overview image px
    MapMarker marker = MapMarker::Town;
};

// A town's lights after dark: overview image px, and how bright (0..1, more for many lights).
struct MapLight {
    Vec2 at;
    float strength = 0;
};

struct MapModel {
    const Sprite* image = nullptr; // the overview art, null while it is missing
    std::span<const MapPlace> places;
    Vec2 view; // where the view is now, overview image px
    std::span<const MapLight> lights;
};

// Grid tile <-> overview image px: plan column C = cols - 1 - y, row R = x, `scale` px per tile.
[[nodiscard]] Vec2 mapPixel(Vec2 gridTile, int gridH, float scale);
[[nodiscard]] Vec2 mapTile(Vec2 pixel, int gridH, float scale);

class MapScreen {
public:
    void open(bool on) { open_ = on; }
    [[nodiscard]] bool isOpen() const { return open_; }
    // Visible at all (it fades in and out).
    [[nodiscard]] bool showing() const { return t_ > 0.0f; }
    // Lays the map out and handles the pointer: a click on a place sets clicked().
    void update(float x, float y, bool inside, bool pressed, bool released, const MapModel& m,
                const Font& font, Vec2 screen, float scale, float dt);
    void draw(Painter& p, const MapModel& m) const;
    [[nodiscard]] std::optional<int> clicked() const { return clicked_; }
    [[nodiscard]] int hovered() const { return hovered_; }
    [[nodiscard]] bool wantsMouse() const { return open_; }
    // Window px of a place's marker (scripts point at it), as of the last update.
    [[nodiscard]] Vec2 markerAt(const MapModel& m, int place) const;
    // The towns' names as laid out at the last update: plates beside their markers that never
    // overlap each other, another marker or the edge (V6-018: names baked small into the art
    // could not be read). A town with no room keeps its name for the hover tip.
    struct Label {
        Box box;
        int place = -1;
    };
    [[nodiscard]] std::span<const Label> labels() const { return labels_; }

private:
    [[nodiscard]] Vec2 toScreen(Vec2 pixel) const;

    bool open_ = false;
    float t_ = 0;
    Box frame_;   // the panel
    Box image_;   // the art inside it
    float k_ = 1; // window px per image px
    float scale_ = 1;
    Vec2 screen_;
    int hovered_ = -1;
    int pressed_ = -1;
    std::optional<int> clicked_;
    std::vector<Label> labels_;
    void placeLabels(const MapModel& m, const Font& font);
};

} // namespace lc
