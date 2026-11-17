#pragma once
// The game's interface: title and clock, build drawer, docks, hint line, journal, toasts and
// tooltips. Laid out and hit-tested each frame from a read-only model; user intent comes back as
// actions for the app to apply.

#include "core/catalog.hpp"
#include "core/clock.hpp"
#include "core/iso.hpp"
#include "core/visitors.hpp"
#include "render/sprites.hpp"
#include "ui/painter.hpp"

#include <array>
#include <optional>
#include <span>
#include <string>
#include <string_view>
#include <vector>

namespace lc {

enum class Tool : std::uint8_t { None, Place, Paint, Remove };

struct HudModel {
    const Catalog* cat = nullptr;
    const SpriteTables* sprites = nullptr;
    const Visitors* visitors = nullptr;
    Tool tool = Tool::None;
    int selection = -1; // item index (Place) or terrain index (Paint)
    int category = 0;   // open drawer tab
    bool drawerOpen = false;
    bool journalOpen = false;
    bool photo = false;
    bool muted = false;
    bool rain = false;
    ClockPin pin = ClockPin::Auto;
    Phase phase = Phase::Day;
    bool canUndo = false;
    bool canRedo = false;
    bool canZoomIn = true;
    bool canZoomOut = true;
    std::string_view hint;
    std::string_view warning;
};

struct UiInput {
    float x = 0;
    float y = 0;
    bool inside = false;  // pointer is over the window
    bool pressed = false; // left button went down this frame
    bool released = false;
    float wheel = 0;
    bool blocked = false; // the world owns the pointer (a drag started on the map)
};

struct HudAction {
    enum class Kind : std::uint8_t {
        ToggleBuild,
        Category,
        PickItem,
        PickTerrain,
        RemoveTool,
        Sound,
        Photo,
        Clock,
        Rain,
        Journal,
        Undo,
        Redo,
        Recentre,
        ZoomOut,
        ZoomIn,
        Hover
    };
    Kind kind;
    int arg = 0;
};

// The drawer's category with this id lists terrain instead of items.
inline constexpr std::string_view kGroundCategory = "terrain";

class Hud {
public:
    Hud();

    void update(const UiInput& in, const HudModel& model, const Font& font, Vec2 screen,
                float scale, float dt);
    void draw(Painter& painter, const HudModel& model) const;

    [[nodiscard]] std::span<const HudAction> actions() const {
        return {actions_.data(), actionCount_};
    }
    // True while the pointer is over the interface or a press that began on it is held.
    [[nodiscard]] bool wantsMouse() const { return overUi_ || captured_; }
    void toast(std::string text);
    void flash() { flash_ = 1.0f; }
    // Centre of a named widget for scripted input ("build", "tile:oak", "tab:homes"...).
    [[nodiscard]] std::optional<Vec2> widgetCentre(std::string_view name, const HudModel& m) const;

    // Entries of a drawer category: item indices, or terrain indices for the ground tab. Fills
    // `out` in place so the per-frame layout reuses its storage.
    static void categoryEntries(const Catalog& cat, int category, std::vector<int>& out);

    static constexpr int kMaxWidgets = 192;

private:
    struct Widget {
        int id = 0;
        Box box;
        bool enabled = true;
        bool selected = false;
        char32_t icon = 0;
        std::string_view label;    // drawn next to the icon (pill buttons) or under a tile
        std::string_view tooltip;  // empty: none
        std::string_view shortcut; // shown in the tooltip
        int ref = -1;              // tile: entry index in the catalog
    };
    struct Panel {
        Box box;
        float radius;
        float alpha;
    };

    void layout(const HudModel& m, const Font& font, Vec2 screen, float s);
    void emit(HudAction::Kind kind, int arg = 0);
    Widget& add(int id, Box box);
    void drawButton(Painter& p, const Widget& w, float alpha) const;
    void drawTile(Painter& p, const Widget& w, const HudModel& m, float alpha) const;
    void drawTitle(Painter& p, const HudModel& m) const;
    void drawJournal(Painter& p, const HudModel& m) const;
    void drawHint(Painter& p, const HudModel& m) const;
    void drawToast(Painter& p) const;
    void drawTooltip(Painter& p) const;
    void drawPanel(Painter& p, Box b, float radius, float alpha) const;

    std::vector<Widget> widgets_;
    std::vector<Panel> panels_;
    std::array<float, kMaxWidgets> hover_{};
    std::array<float, kMaxWidgets> press_{};
    std::array<HudAction, 16> actions_{};
    std::size_t actionCount_ = 0;
    std::vector<int> scroll_; // first visible drawer row per category
    std::vector<int> entries_;

    float scale_ = 1;
    Vec2 screen_;
    int hovered_ = 0;
    int pointed_ = 0;
    int active_ = 0;
    bool overUi_ = false;
    bool captured_ = false;
    float drawerT_ = 0;
    float journalT_ = 0;
    float hintT_ = 0;
    float hoverTime_ = 0;
    float tooltipT_ = 0;
    int tooltipId_ = 0;
    std::string toast_;
    float toastTime_ = 0;
    float toastT_ = 0;
    float flash_ = 0;
    std::string clockLabel_;
    std::string hintText_;
    Box titleBox_;
    Box journalBox_;
    Box drawerBox_;
    Box hintBox_;
    float bottomTop_ = 0;
};

} // namespace lc
