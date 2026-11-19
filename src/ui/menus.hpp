#pragma once
// The front door and the glass around play (docs/design/living-corner.md R10, R12, §6.5–6.9):
// the title screen, "Your worlds" with its dialogs, settings, the pause menu, the tour's coach
// card and the photo bar. Like the HUD it is laid out and hit-tested each frame from a read-only
// model, and intent comes back as actions; it also owns the pages that are open, keyboard focus
// and the text field.

#include "core/save.hpp"
#include "platform/sprite.hpp"
#include "ui/hud.hpp"
#include "ui/painter.hpp"

#include <array>
#include <cstdint>
#include <optional>
#include <span>
#include <string>
#include <string_view>
#include <vector>

namespace lc {

enum class Page : std::uint8_t {
    None,
    Title,
    Worlds,
    NewWorld,
    Delete,
    LoadError,
    Settings,
    Pause
};

// One world card.
struct MenuWorld {
    std::string_view name;
    std::string_view detail; // "Autumn, day 3 · 14 pages"
    Sprite thumb;            // no texture: a plain card
    bool readable = true;    // false: it cannot be opened here (damaged, or from a newer version)
};

struct MenuModel {
    const Profile* profile = nullptr;
    bool firstLaunch = false; // a fresh corner nobody has begun: the title offers Begin (and
                              // Worlds when there are any)
    std::string_view continueName;
    std::span<const MenuWorld> worlds;
    Sprite logo;
    std::string_view residentName; // heads the chatter setting; empty: nobody lives here
    bool fullscreen = false;
    float coachBottom = 0;       // the coach card sits above this (the HUD's bottom panels)
    std::string_view coach;      // the tour's step text; empty: no coach card
    std::string_view deleteName; // the world the delete dialog asks about
    bool photo = false;          // the photo bar shows
    std::string_view frameName;
    float barBottom = 0; // the bar stands above this (the postcard's caption, else the edge)
    bool caption = true;
    int frames = 1;                // postcard frames unlocked (the arrows show when there are more)
    int look = 3;                  // the Look: 0 Classic .. 3 High (graphics plan §3.2)
    bool lookAfterRestart = false; // this renderer cannot show it: it applies on the next start
    bool lookUnavailable = false;  // no shader renderer on this computer: Classic is drawn
    int clouds = 0;                // the clouds: 0 on, 1 shadows only, 2 off
};

struct MenuAction {
    enum class Kind : std::uint8_t {
        Continue,
        Begin,
        Worlds,
        Settings,
        Quit,
        Back,
        Play,     // arg: world
        Rename,   // arg: world, text: the new name
        Delete,   // arg: world (confirmed)
        NewWorld, // the name dialog asks
        Create,   // text: the name, arg: 1 for free build
        Volume,   // arg: 0 music, 1 effects, 2 ambience; value in `value`
        Mute,
        Fullscreen,
        UiScale, // arg: index into kUiScales
        ReduceMotion,
        Grid,
        Vsync,
        Look,    // arg: 0 Classic .. 3 High
        Clouds,  // arg: 0 on, 1 shadows only, 2 off
        Chatter, // arg: 1 chatty
        ReplayTour,
        Resume,
        OpenPostcards,
        BackToWorlds,
        SkipTour,
        FramePrev,
        FrameNext,
        Caption,
        HideBar,
        TakePostcard,
        ClosePhoto,
        Hover,
        Click,
    };
    Kind kind;
    int arg = 0;
    int value = 0;
    std::string text;
};

// Keyboard input the menus understand (the app passes key presses while a page is open).
enum class MenuKey : std::uint8_t { Up, Down, Left, Right, Enter, Escape, Backspace };

class Menus {
public:
    void update(const UiInput& in, const MenuModel& m, const Font& font, Vec2 screen, float scale,
                float dt);
    // Lays out again from `m` without input: called before draw() whenever actions may have
    // changed what the model points at (a refreshed worlds list), so drawing never reads a stale
    // layout.
    void relayout(const MenuModel& m, const Font& font) { layout(m, font, scale_); }
    void draw(Painter& p, const MenuModel& m) const;

    [[nodiscard]] std::span<const MenuAction> actions() const { return actions_; }
    void clearActions() { actions_.clear(); }

    [[nodiscard]] Page page() const { return pages_[static_cast<std::size_t>(depth_)]; }
    // Opens a page over the current one / closes the top one / closes them all.
    void open(Page p);
    void back();
    void closeAll();
    // The front door is open (the title, the worlds and their dialogs, settings from the title):
    // no world is being played under it.
    [[nodiscard]] bool frontDoorOpen() const { return depth_ > 0 && pages_[1] != Page::Pause; }
    // A page that stops play: everything but the coach card and the photo bar.
    [[nodiscard]] bool blocking() const { return page() != Page::None; }
    // Keys while a page is open; true when the menus used it.
    bool key(MenuKey k, const MenuModel& m);
    // Text typed into the open field; characters the interface cannot draw are refused (and the
    // field says so). True when there was a field to type into.
    bool text(std::string_view utf8, const Font& font);
    [[nodiscard]] bool editing() const { return fieldOpen_; }
    // The app found the name wanting: the field stays open and says why.
    void fieldError(std::string_view why) {
        fieldNote_ = why;
        fieldSelected_ = true; // typing again replaces the refused name
    }
    // The rename or name field is done with.
    void closeField() { fieldOpen_ = false; }
    // Starts editing a name: a new world's (with its default) or world `index`'s.
    void editName(std::string_view initial, int world);
    // True while the pointer is over a panel or the photo bar (the world does not get it).
    [[nodiscard]] bool wantsMouse() const { return overUi_; }
    // Centre of a named widget for scripts ("menu:continue", "menu:play:0"...).
    [[nodiscard]] std::optional<Vec2> widgetCentre(std::string_view name) const;
    // Every widget laid out now (tests: nothing overlaps, nothing leaves the window).
    [[nodiscard]] std::vector<Box> widgetBoxes() const {
        std::vector<Box> out;
        for (const Widget& w : widgets_) out.push_back(w.box);
        return out;
    }
    // The photo bar fades after a while without pointer movement; this wakes it.
    void wakeBar() { barIdle_ = 0; }
    void hideBar(bool hidden) { barHidden_ = hidden; }
    [[nodiscard]] bool barHidden() const { return barHidden_; }

private:
    enum class Kind : std::uint8_t {
        Button,
        Danger,
        Toggle,
        Slider,
        Choice,
        Card,
        NewCard,
        Icon,
        Field,
        Link,
        Bar
    };
    struct Widget {
        int id = 0;
        Kind kind = Kind::Button;
        Box box;
        std::string_view label;
        std::string_view value; // a toggle's or choice's state, a shortcut chip
        char32_t icon = 0;
        float amount = 0; // sliders: 0..1
        float rowX = 0;   // sliders: where their row (and label) begins
        bool on = false;
        bool enabled = true;
        bool note = false; // a settings row's explanation: small, muted, under its row
    };
    Widget& add(int id, Kind kind, Box box, std::string_view label = {});
    void emit(MenuAction::Kind k, int arg = 0, int value = 0, std::string text = {});
    void layout(const MenuModel& m, const Font& font, float s);
    void layoutTitle(const MenuModel& m, float s);
    void layoutWorlds(const MenuModel& m, const Font& font, float s);
    void layoutDialog(const MenuModel& m, const Font& font, float s);
    void layoutSettings(const MenuModel& m, const Font& font, float s);
    void layoutPause(const Font& font, float s);
    void layoutCoach(const MenuModel& m, const Font& font, float s);
    void layoutBar(const MenuModel& m, const Font& font, float s);
    void activate(const Widget& w, const MenuModel& m, float pointerX);
    [[nodiscard]] const Widget* find(int id) const;
    [[nodiscard]] float hoverOf(int id) const;
    void drawWidget(Painter& p, const Widget& w, float alpha) const;
    void drawField(Painter& p, Box b, float alpha) const;

    std::array<Page, 5> pages_{Page::None};
    int depth_ = 0;
    std::vector<Widget> widgets_;
    std::vector<MenuAction> actions_;
    std::vector<Box> panels_; // glass behind the open page
    Box fullGlass_;           // the blurred world behind the pause menu
    std::string_view heading_;
    std::string headingText_;
    std::string_view body_; // a dialog's wrapped text
    Box headingBox_;
    Box bodyBox_;
    Box logoBox_;
    Box coachBox_;
    Box barBox_;
    float scale_ = 1;
    Vec2 screen_;
    Vec2 pointer_;
    int hovered_ = 0;
    int active_ = 0; // the widget a press began on
    int focus_ = 0;  // the widget the keyboard is on (0: none)
    bool overUi_ = false;
    float pageT_ = 0; // the open page fades in
    std::vector<float> hover_;
    int dragging_ = 0; // a slider being dragged
    int worldsScroll_ = 0;
    bool settingsScrollable_ = false; // the settings do not fit even tight: one scrolling column
    int settingsScroll_ = 0;          // items scrolled past
    int settingsScrollMax_ = 0;
    int worldsRows_ = 0; // rows of cards that fit
    int worldsTotalRows_ = 0;
    int selectedWorld_ = -1; // the card showing its buttons (hover or focus)
    // The text field: a new world's name, or a world being renamed.
    bool fieldOpen_ = false;
    int fieldWorld_ = -1; // -1: the new world dialog
    std::string field_;
    bool fieldSelected_ = false; // the name it opened with is selected: typing replaces it
    std::string_view fieldNote_;
    bool freeBuild_ = false;
    int deleteWorld_ = -1;
    float barIdle_ = 0;
    float barT_ = 0;
    bool barHidden_ = false;
    std::array<std::string, 3> volumeText_;
    std::string scaleText_;
    std::string lookText_;
    mutable std::vector<std::string> nameCut_; // card names cut to fit
};

} // namespace lc
