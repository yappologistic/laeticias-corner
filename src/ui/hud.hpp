#pragma once
// The game's interface: title and clock, build drawer, docks, hint line, journal, toasts and
// tooltips. Laid out and hit-tested each frame from a read-only model; user intent comes back as
// actions for the app to apply.

#include "core/catalog.hpp"
#include "core/clock.hpp"
#include "core/iso.hpp"
#include "core/progress.hpp"
#include "core/visitors.hpp"
#include "platform/sprite.hpp"
#include "ui/painter.hpp"

#include <array>
#include <optional>
#include <span>
#include <string>
#include <string_view>
#include <vector>

namespace lc {

enum class Tool : std::uint8_t { None, Place, Paint, Remove };

// First-frame art of every catalog entry, for drawer tiles and the journal.
struct ThumbSet {
    std::vector<Sprite> terrain;
    std::vector<Sprite> items;
    std::vector<Sprite> visitors;
    Sprite placeholder;
    Sprite portrait;  // the resident, for her wish cards
    float tileW = 64; // art tile width: one-tile things share one scale, so sizes compare
};

// One open wish as the tray shows it.
struct WishCard {
    int wish = -1;
    std::string_view text;
    Sprite portrait;         // the giver
    float progress = -1;     // a count goal's share done, 0..1; -1: no bar
    std::string_view detail; // "3 / 4 flower patches" or "Waiting for nightfall"
    bool ready = false;      // its goal holds: granted in a moment
};

// The wide toast that announces a granted wish and what it brought.
struct Ribbon {
    std::string title;
    std::string text;
    std::string quote; // the giver's thanks
    std::array<Sprite, 4> icons{};
    int iconCount = 0;
};

// A name floating over the world (a nook just found), at a window position.
struct FloatLabel {
    Vec2 at;
    std::string_view text;
    float alpha = 1;
};

struct HudModel {
    const Catalog* cat = nullptr;
    const ThumbSet* thumbs = nullptr;
    const Visitors* visitors = nullptr;
    const Progress* progress = nullptr; // unlocks and new-piece dots; null: everything unlocked
    std::span<const WishCard> wishes;   // the open wishes, in the order they were offered
    int pages = 0;                      // sketchbook pages: visitors seen and nooks found
    int pagesTotal = 0;
    int nextStagePages = -1; // pages the next land stage opens at; -1: all open
    std::string_view nextStageName;
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
    std::string_view worldTip; // what the pointer rests on in the world (a nook's name...)
    std::span<const FloatLabel> labels;
    bool edgeChip = false; // land opened out of sight: a chip points the way
    float brightness = 0;  // of the scene behind the glass, 0 dark .. 1 bright
};

struct UiInput {
    float x = 0;
    float y = 0;
    bool inside = false;  // pointer is over the window
    bool pressed = false; // left button went down this frame
    bool released = false;
    bool rightPressed = false; // right button went down this frame
    bool rightReleased = false;
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
        SeenNew,    // the pointer reached a tile with a "new" dot: `arg` is its entry code
        OpenWishes, // the "+N" tile or a wish card: the sketchbook's wishes; `arg` a wish or -1
        Snooze,     // "Not now" on wish `arg`
        PageTurn,   // the sketchbook changed tab
        EdgeChip,   // "New land": look at the stage that just opened
        Hover
    };
    Kind kind;
    int arg = 0;
};

// The drawer's category with this id lists terrain instead of items.
inline constexpr std::string_view kGroundCategory = "terrain";
[[nodiscard]] bool isGroundCategory(const Catalog& cat, int category);

// What a drawer tile stands for. Each tile carries its own, so drawing and picking never depend on
// the open tab still being the one the drawer was laid out for.
struct DrawerEntry {
    bool terrain = false; // `index` is a terrain index, else an item index
    bool locked = false;  // the "+N" tile of category `index`: pieces still to discover
    int index = -1;
    friend bool operator==(const DrawerEntry&, const DrawerEntry&) = default;
    // One integer per entry, for actions: items, then terrain (locked tiles are never sent).
    [[nodiscard]] int code(const Catalog& cat) const {
        return terrain ? static_cast<int>(cat.items.size()) + index : index;
    }
};

// Whether a drawer entry's piece is unlocked / still shows its "new" dot.
[[nodiscard]] bool entryUnlocked(const Progress* p, DrawerEntry e);
[[nodiscard]] bool entryNew(const Progress* p, DrawerEntry e);

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
    // Window area the interface leaves free (below the title, above the docks and hint line), as
    // of the last update.
    [[nodiscard]] Box safeArea() const { return safe_; }
    // Scrolls the open drawer so a named tile ("tile:<id>") is laid out from the next update;
    // false when the tile is not in the open tab.
    bool reveal(std::string_view name, const HudModel& m);
    // Opens the sketchbook on a tab (0 wishes, 1 visitors, 2 nooks) / turns its pages.
    void openSketchbook(int tab);
    void turnPage(int delta, const HudModel& m);
    [[nodiscard]] int sketchTab() const { return sketchTab_; }
    void toast(std::string text);
    void ribbon(Ribbon r);
    [[nodiscard]] bool ribbonShowing() const { return ribbonTime_ > 0.0f; }
    void flash() { flash_ = 1.0f; }
    [[nodiscard]] bool toastShowing() const { return toastTime_ > 0.0f; }
    // Centre of a named widget for scripted input ("build", "tile:oak", "tab:homes"...), or of
    // the "toast" and "hint" panels while they show.
    [[nodiscard]] std::optional<Vec2> widgetCentre(std::string_view name, const HudModel& m) const;
    // Current hover highlight (0..1) of a named widget; 0 when it is not shown.
    [[nodiscard]] float highlight(std::string_view name, const HudModel& m) const;

    // Entries of a drawer category: its unlocked items, or the unlocked terrain for the ground
    // tab, then a "+N" tile while some are still locked. Fills `out` in place so the per-frame
    // layout reuses its storage.
    static void categoryEntries(const Catalog& cat, int category, std::vector<DrawerEntry>& out,
                                const Progress* progress = nullptr);
    // Pieces of a category not unlocked yet.
    [[nodiscard]] static int lockedIn(const Catalog& cat, int category, const Progress* progress);

private:
    // Room for every widget of a frame (docks, tabs and a full drawer page), reserved up front.
    static constexpr std::size_t kWidgetReserve = 64;
    struct Thumbnailed {
        const Sprite* sprite;
        float maxScale;
    };
    struct Widget {
        int id = 0;
        Box box;
        bool enabled = true;
        bool selected = false;
        char32_t icon = 0;
        std::string_view label;    // drawn next to the icon (pill buttons) or under a tile
        std::string_view tooltip;  // empty: none
        std::string_view shortcut; // shown in the tooltip
        DrawerEntry entry;         // tile: what it stands for
        bool dot = false;          // a newly unlocked piece inside
    };
    struct Panel {
        Box box;
        float radius;
    };

    void layout(const HudModel& m, const Font& font, Vec2 screen, float s);
    // Lays out the docks, wrapping them into rows on narrow windows; returns the top row's y.
    float layoutDocks(const HudModel& m, Vec2 screen, float s);
    [[nodiscard]] Thumbnailed thumbFor(const HudModel& m, DrawerEntry e, float box) const;
    [[nodiscard]] const Widget* find(std::string_view name, const HudModel& m) const;
    void emit(HudAction::Kind kind, int arg = 0);
    Widget& add(int id, Box box);
    // Tiles are keyed by what they stand for, not by their slot, so hover and press feedback
    // never carry over to a different entry after a tab switch or scroll.
    [[nodiscard]] static int tileId(const Catalog& cat, DrawerEntry e);
    [[nodiscard]] float hoverOf(int id) const;
    [[nodiscard]] float pressOf(int id) const;
    void drawButton(Painter& p, const Widget& w, float alpha) const;
    void drawTab(Painter& p, const Widget& w, float alpha) const;
    void drawTile(Painter& p, const Widget& w, const HudModel& m, float alpha) const;
    void drawTitle(Painter& p, const HudModel& m) const;
    void layoutSketchbook(const HudModel& m, const Font& font, Vec2 screen, float s);
    void drawSketchbook(Painter& p, const HudModel& m) const;
    [[nodiscard]] static int sketchTabs(const HudModel& m);
    [[nodiscard]] std::string_view rewardText(const Catalog& cat, const Reward& r) const;
    void drawPill(Painter& p, const Widget& w, float alpha) const;
    void drawHint(Painter& p, const HudModel& m) const;
    void drawToast(Painter& p) const;
    void layoutTray(const Font& font, Vec2 screen, float s);
    void drawTray(Painter& p) const;
    void drawRibbon(Painter& p) const;
    void drawTooltip(Painter& p) const;
    void drawWorldTip(Painter& p, const HudModel& m) const;
    void drawLabels(Painter& p, const HudModel& m) const;

    std::vector<Widget> widgets_;
    std::vector<Panel> panels_; // the docks; always shown, never overlapping
    std::array<Box, 2> dividers_{};
    std::vector<float> hover_; // per widget id
    std::vector<float> press_;
    std::array<HudAction, 16> actions_{};
    std::size_t actionCount_ = 0;
    std::vector<int> scroll_; // first visible drawer row per category
    std::vector<DrawerEntry> entries_;

    float scale_ = 1;
    Vec2 screen_;
    Vec2 pointer_;
    float worldTipT_ = 0;
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
    std::string lockLabel_; // "+N" and its tooltip for the open tab's lock tile
    std::string lockTip_;

    // The sketchbook: tabs of rows, scrolled a row at a time.
    struct Row {
        enum class Kind : std::uint8_t { Section, OpenWish, GrantedWish, Visitor, Nook };
        Kind kind;
        int index; // section, wish card, wish, visitor or nook
        float h;
    };
    std::vector<Row> rows_;
    int sketchTab_ = 0;
    int sketchScroll_ = 0;
    int sketchShown_ = 0;
    bool sketchMore_ = false;
    float sketchBody_ = 0;
    std::string pagesText_;
    std::string untilText_;
    std::string noteLabel_;
    mutable std::string rewardText_;

    // The wish tray: cards slide in when offered and fade up when they leave.
    struct TrayCard {
        WishCard card;
        float in = 0;  // 0..1 entering
        float out = 0; // 0..1 leaving (0 while open)
        bool open = true;
        Box box;
        float lines = 1; // text lines
    };
    std::vector<TrayCard> tray_;
    Box trayBox_;
    Box trayLast_; // where the tray was last shown, kept while it is hidden
    float trayT_ = 0;
    bool trayCollapsed_ = false;
    int menuWish_ = -1; // the card whose "Not now" menu is open
    Box menuBox_;
    char trayCount_[8] = {};
    Ribbon ribbon_;
    float ribbonTime_ = 0;
    float ribbonT_ = 0;
    Box ribbonBox_;
    Box titleBox_;
    Box journalBox_;
    Box drawerBox_;
    Box hintBox_;
    Box toastBox_;
    Box safe_;
    float bottomTop_ = 0;
    bool scrollable_ = false;
    bool canScrollUp_ = false;
    bool canScrollDown_ = false;
};

} // namespace lc
