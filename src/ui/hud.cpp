#include "ui/hud.hpp"

#include "ui/strings.hpp"
#include "ui/theme.hpp"

#include <algorithm>
#include <charconv>
#include <cmath>
#include <format>
#include <utility>

namespace lc {
namespace {

enum Wid : int {
    kNone = 0,
    kBuild,
    kRemove,
    kMove,
    kMenu,
    kPhoto,
    kClock,
    kRain,
    kJournal,
    kUndo,
    kRedo,
    kRecentre,
    kZoomOut,
    kZoomIn,
    kJournalClose,
    kScrollUp,
    kScrollDown,
    kTrayHeader,
    kCard0,                            // wish cards: kCard0 + slot
    kNotNow = kCard0 + 8,              // the card menu's only entry
    kSketchTab0,                       // sketchbook tabs: kSketchTab0 + tab
    kSketchNotNow0 = kSketchTab0 + 12, // "Not now" on the sketchbook's open wishes
    kEdgeChip = kSketchNotNow0 + 3,    // "New land"
    kTitleCard,                        // opens the calendar
    kCalPin0,                          // calendar: follow the days, then each season
    kMap = kCalPin0 + 9,               // the world map
    kCardClose,                        // the landmark or figure card's close button
    kSoundButton,                      // mute and unmute, anywhere
    kTab0 = 72,                        // drawer tabs: kTab0 + category
    kTile0 = 96,                       // drawer tiles: see tileId
};
constexpr int kTraySlots = kNotNow - kCard0;

struct Named {
    std::string_view name;
    int id;
};
constexpr Named kNames[] = {
    {"build", kBuild},
    {"remove", kRemove},
    {"move", kMove},
    {"menu", kMenu},
    {"photo", kPhoto},
    {"clock", kClock},
    {"rain", kRain},
    {"journal", kJournal},
    {"undo", kUndo},
    {"redo", kRedo},
    {"recentre", kRecentre},
    {"map", kMap},
    {"card_close", kCardClose},
    {"sound", kSoundButton},
    {"zoom_out", kZoomOut},
    {"zoom_in", kZoomIn},
    {"journal_close", kJournalClose},
    {"scroll_up", kScrollUp},
    {"scroll_down", kScrollDown},
    {"tray", kTrayHeader},
    {"not_now", kNotNow},
    {"sketch:wishes", kSketchTab0},
    {"sketch:visitors", kSketchTab0 + 1},
    {"sketch:nooks", kSketchTab0 + 2},
    {"sketch:place0", kSketchTab0 + 3},
    {"sketch:place1", kSketchTab0 + 4},
    {"sketch_not_now", kSketchNotNow0},
    {"edge_chip", kEdgeChip},
    {"calendar", kTitleCard},
    {"season_auto", kCalPin0},
    {"season_spring", kCalPin0 + 1},
    {"season_summer", kCalPin0 + 2},
    {"season_autumn", kCalPin0 + 3},
    {"season_winter", kCalPin0 + 4},
};

float approach(float v, bool on, float dt) {
    const float step = dt / theme::kTransition;
    return on ? std::min(1.0f, v + step) : std::max(0.0f, v - step);
}

float smooth(float t) {
    return t * t * (3 - 2 * t);
}

SDL_FColor withAlpha(SDL_FColor c, float a) {
    return {c.r, c.g, c.b, c.a * a};
}

// The small accent dot that marks something new.
void drawDot(Painter& p, float cx, float cy, float s, float alpha) {
    const float r = theme::kDotRadius * s;
    p.roundRect({cx - r - s, cy - r - s, 2 * (r + s), 2 * (r + s)}, r + s,
                withAlpha(theme::kDotRim, alpha));
    p.roundRect({cx - r, cy - r, 2 * r, 2 * r}, r, withAlpha(theme::kAccent, alpha));
}

SDL_FColor mixColor(SDL_FColor a, SDL_FColor b, float k) {
    return {a.r + (b.r - a.r) * k, a.g + (b.g - a.g) * k, a.b + (b.b - a.b) * k,
            a.a + (b.a - a.a) * k};
}

std::string_view phaseName(Phase p) {
    switch (p) {
    case Phase::Day: return strings::kPhaseDay;
    case Phase::Dusk: return strings::kPhaseDusk;
    case Phase::Night: return strings::kPhaseNight;
    case Phase::Dawn: return strings::kPhaseDawn;
    }
    return {};
}

char32_t phaseIcon(Phase p) {
    switch (p) {
    case Phase::Day: return theme::icon::kSun;
    case Phase::Dusk: return theme::icon::kSunset;
    case Phase::Night: return theme::icon::kMoon;
    case Phase::Dawn: return theme::icon::kSunrise;
    }
    return 0;
}

char32_t pinIcon(ClockPin p) {
    switch (p) {
    case ClockPin::Auto: return theme::icon::kClockAuto;
    case ClockPin::Day: return theme::icon::kSun;
    case ClockPin::Dusk: return theme::icon::kSunset;
    case ClockPin::Night: return theme::icon::kMoon;
    case ClockPin::Dawn: return theme::icon::kSunrise;
    }
    return 0;
}

std::string_view pinTooltip(ClockPin p) {
    switch (p) {
    case ClockPin::Auto: return strings::kClockAuto;
    case ClockPin::Day: return strings::kClockDay;
    case ClockPin::Dusk: return strings::kClockDusk;
    case ClockPin::Night: return strings::kClockNight;
    case ClockPin::Dawn: return strings::kClockDawn;
    }
    return {};
}

} // namespace

bool entryUnlocked(const Progress* p, DrawerEntry e) {
    if (p == nullptr || e.locked) return true;
    const auto i = static_cast<std::size_t>(e.index);
    return (e.terrain ? p->terrain[i] : p->items[i]) != 0;
}

bool entryNew(const Progress* p, DrawerEntry e) {
    if (p == nullptr || e.locked) return false;
    const auto i = static_cast<std::size_t>(e.index);
    return (e.terrain ? p->newTerrain[i] : p->newItems[i]) != 0;
}

bool isGroundCategory(const Catalog& cat, int category) {
    return category >= 0 && std::cmp_less(category, cat.categories.size()) &&
           cat.categories[static_cast<std::size_t>(category)].id == kGroundCategory;
}

Hud::Hud() {
    widgets_.reserve(kWidgetReserve);
    panels_.reserve(16);
    entries_.reserve(256);
    toast_.reserve(96);
    clockLabel_.reserve(64);
    hintText_.reserve(192);
    lockLabel_.reserve(16);
    lockTip_.reserve(96);
    tray_.reserve(kTraySlots);
}

void Hud::ribbon(Ribbon r) {
    ribbon_ = std::move(r);
    ribbonTime_ = theme::kRibbonSeconds;
}

void Hud::categoryEntries(const Catalog& cat, int category, std::vector<DrawerEntry>& out,
                          const Progress* progress) {
    out.clear();
    const auto offer = [&](DrawerEntry e) {
        if (entryUnlocked(progress, e)) out.push_back(e);
    };
    if (isGroundCategory(cat, category)) {
        for (std::size_t t = 0; t < cat.terrain.size(); ++t)
            offer({.terrain = true, .index = static_cast<int>(t)});
    } else {
        for (std::size_t i = 0; i < cat.items.size(); ++i)
            if (cat.items[i].category == category)
                offer({.terrain = false, .index = static_cast<int>(i)});
    }
    if (lockedIn(cat, category, progress) > 0)
        out.push_back({.terrain = false, .locked = true, .index = category});
}

int Hud::lockedIn(const Catalog& cat, int category, const Progress* progress) {
    if (progress == nullptr) return 0;
    int n = 0;
    if (isGroundCategory(cat, category)) {
        for (const std::uint8_t u : progress->terrain) n += u == 0 ? 1 : 0;
    } else {
        for (std::size_t i = 0; i < cat.items.size(); ++i)
            n += cat.items[i].category == category && progress->items[i] == 0 ? 1 : 0;
    }
    return n;
}

int Hud::tileId(const Catalog& cat, DrawerEntry e) {
    if (e.locked) return kTile0 + static_cast<int>(cat.items.size() + cat.terrain.size()) + e.index;
    return kTile0 + (e.terrain ? static_cast<int>(cat.items.size()) : 0) + e.index;
}

float Hud::hoverOf(int id) const {
    const auto i = static_cast<std::size_t>(id);
    return i < hover_.size() ? smooth(hover_[i]) : 0.0f;
}

float Hud::pressOf(int id) const {
    const auto i = static_cast<std::size_t>(id);
    return i < press_.size() ? smooth(press_[i]) : 0.0f;
}

void Hud::toast(std::string text) {
    if (toastTime_ <= 0.0f && toastT_ <= 0.0f && toastWaiting_ == 0 && !toastsHeld_) {
        toast_ = std::move(text);
        toastTime_ = theme::kToastSeconds;
        toastShown_ = 0;
        return;
    }
    if (toastWaiting_ == theme::kToastQueue) {
        // Full: the oldest waiting one gives way.
        std::ranges::rotate(toastQueue_, toastQueue_.begin() + 1);
        --toastWaiting_;
    }
    toastQueue_[static_cast<std::size_t>(toastWaiting_++)] = std::move(text);
}

void Hud::emit(HudAction::Kind kind, int arg) {
    if (actionCount_ < actions_.size()) actions_[actionCount_++] = {kind, arg};
}

Hud::Widget& Hud::add(int id, Box box) {
    widgets_.push_back(Widget{});
    Widget& w = widgets_.back();
    w.id = id;
    w.box = box;
    return w;
}

float Hud::layoutDocks(const HudModel& m, Vec2 screen, float s) {
    const float margin = theme::kMargin * s;
    const float btn = theme::kButton * s;
    const float pad = theme::kDockPad * s;
    const float dockH = btn + 2 * pad;
    const float gap = theme::kGap * s;
    const float buildW = btn + theme::kBuildExtra * s;
    const float leftW = buildW + 2 * (gap + dockH);
    const float divider = gap * 2;
    const float rightW = 5 * btn + 2 * divider + 2 * pad;
    const float centreW = (m.world ? 7.0f : 6.0f) * btn + 2 * pad;
    const float avail = screen.x - 2 * margin;
    // One row when everything fits; otherwise the centre dock, then the right dock, move up a
    // row each, so no dock ever overlaps another.
    const bool oneRow = leftW + gap + centreW + gap + rightW <= avail;
    const bool twoRows = !oneRow && leftW + gap + rightW <= avail;
    const float row0 = screen.y - margin - dockH;
    const float rowStep = dockH + gap;
    const float leftY = row0;
    const float rightY = oneRow || twoRows ? row0 : row0 - rowStep;
    const float centreY = oneRow ? row0 : rightY - rowStep;

    // The building dock belongs to the home: away from it, it folds away.
    if (!m.away) {
        Widget& w = add(kBuild, {margin, leftY, buildW, dockH});
        w.icon = theme::icon::kPlus;
        w.label = strings::kBuild;
        w.tooltip = strings::kBuildTip;
        w.shortcut = strings::kKeyBuild;
        w.selected = m.drawerOpen || m.tool == Tool::Place || m.tool == Tool::Paint;
        w.enabled = !m.away;
        w.dot =
            m.progress != nullptr && (std::ranges::find(m.progress->newItems, std::uint8_t{1}) !=
                                          m.progress->newItems.end() ||
                                      std::ranges::find(m.progress->newTerrain, std::uint8_t{1}) !=
                                          m.progress->newTerrain.end());
        panels_.push_back({w.box, dockH * 0.5f});
        Widget& r = add(kRemove, {margin + buildW + gap, leftY, dockH, dockH});
        r.icon = theme::icon::kEraser;
        r.tooltip = strings::kRemove;
        r.shortcut = strings::kKeyRemove;
        r.selected = m.tool == Tool::Remove;
        r.enabled = !m.away;
        panels_.push_back({r.box, dockH * 0.5f});
        Widget& v = add(kMove, {margin + buildW + 2 * gap + dockH, leftY, dockH, dockH});
        v.icon = theme::icon::kMove;
        v.tooltip = strings::kMoveTip;
        v.shortcut = strings::kKeyMove;
        v.selected = m.tool == Tool::Move;
        v.enabled = !m.away;
        panels_.push_back({v.box, dockH * 0.5f});
    }

    // Right dock: undo, redo | recentre | zoom out, zoom in.
    const float rightX = screen.x - margin - rightW;
    panels_.push_back({{rightX, rightY, rightW, dockH}, dockH * 0.5f});
    {
        float x = rightX + pad;
        const auto button = [&](int id, char32_t icon, std::string_view tip, std::string_view key,
                                bool enabled) {
            Widget& w = add(id, {x, rightY + pad, btn, btn});
            w.icon = icon;
            w.tooltip = tip;
            w.shortcut = key;
            w.enabled = enabled;
            x += btn;
        };
        button(kUndo, theme::icon::kUndo, strings::kUndo, strings::kKeyUndo, m.canUndo);
        button(kRedo, theme::icon::kRedo, strings::kRedo, strings::kKeyRedo, m.canRedo);
        const auto rule = [&](Box& b) {
            b = {std::round(x + divider * 0.5f - theme::kRim * s * 0.5f),
                 rightY + pad + btn * 0.25f, theme::kRim * s, btn * 0.5f};
            x += divider;
        };
        rule(dividers_[0]);
        button(kRecentre, theme::icon::kHome, strings::kRecentre, strings::kKeyRecentre, true);
        rule(dividers_[1]);
        button(kZoomOut, theme::icon::kMinus, strings::kZoomOut, strings::kKeyZoomOut,
               m.canZoomOut);
        button(kZoomIn, theme::icon::kPlus, strings::kZoomIn, strings::kKeyZoomIn, m.canZoomIn);
    }

    float centreX = std::round((screen.x - centreW) * 0.5f);
    if (oneRow)
        centreX = std::clamp(centreX, margin + leftW + gap,
                             std::max(margin + leftW + gap, rightX - gap - centreW));
    panels_.push_back({{centreX, centreY, centreW, dockH}, dockH * 0.5f});
    {
        float x = centreX + pad;
        const auto button = [&](int id, char32_t icon, std::string_view tip, std::string_view key,
                                bool selected) {
            Widget& w = add(id, {x, centreY + pad, btn, btn});
            w.icon = icon;
            w.tooltip = tip;
            w.shortcut = key;
            w.selected = selected;
            x += btn;
        };
        button(kMenu, theme::icon::kMenu, strings::kMenu, strings::kKeyEsc, false);
        button(kPhoto, theme::icon::kCamera, strings::kPhoto, strings::kKeyPhoto, false);
        button(kClock, pinIcon(m.pin), pinTooltip(m.pin), strings::kKeyClock,
               m.pin != ClockPin::Auto);
        // Weather as it comes, rain (or snow) here, or clear skies here.
        const char32_t wet = m.snow ? theme::icon::kSnowflake : theme::icon::kRain;
        switch (m.weather) {
        case WeatherMode::Natural:
            button(kRain, wet, strings::kWeatherNatural, strings::kKeyRain, false);
            break;
        case WeatherMode::Rain:
            button(kRain, wet, m.snow ? strings::kWeatherSnow : strings::kWeatherRain,
                   strings::kKeyRain, true);
            break;
        case WeatherMode::Clear:
            button(kRain, theme::icon::kSun, strings::kWeatherClear, strings::kKeyRain, true);
            break;
        }
        button(kJournal, theme::icon::kJournal, strings::kSketchbook, strings::kKeyJournal,
               m.journalOpen);
        if (m.world) button(kMap, theme::icon::kMap, strings::kMap, strings::kKeyMap, false);
        // Muted shows unmistakably: the crossed speaker, lit as a held button.
        button(kSoundButton, m.muted ? theme::icon::kSoundOff : theme::icon::kSoundOn,
               m.muted ? strings::kSoundOff : strings::kSoundOn, strings::kKeyMute, m.muted);
    }
    return std::min(centreY, rightY);
}

void Hud::layout(const HudModel& m, const Font& font, Vec2 screen, float s) {
    widgets_.clear();
    panels_.clear();
    const float margin = theme::kMargin * s;
    const float gap = theme::kGap * s;
    bottomTop_ = layoutDocks(m, screen, s);

    // Title and clock, top-left.
    {
        const float tpad = theme::kTitlePad * s;
        const float maxName = std::min(theme::kTitleMaxW * s, screen.x * 0.5f);
        const std::string_view name = m.away && !m.place.empty()
                                          ? m.place
                                          : (m.worldName.empty() ? strings::kTitle : m.worldName);
        titleName_ = elide(font, Face::Title, name, maxName, titleCut_);
        const float w1 = font.measure(Face::Title, titleName_);
        const float w2 =
            theme::kIcon * s + theme::kTitleIconGap * s + font.measure(Face::Body, clockLabel_);
        titleBox_ = {margin, margin, std::max(w1, w2) + 2 * tpad,
                     2 * tpad + font.lineHeight(Face::Title) + font.lineHeight(Face::Body)};
    }

    {
        Widget& t = add(kTitleCard, titleBox_);
        t.tooltip = strings::kCalendar;
    }
    layoutCalendar(m, font, s);

    // The tray first, so the drawer (drawn over it) is hit first where they meet.
    layoutTray(font, screen, s);

    // Build drawer above the docks.
    drawerBox_ = {};
    scrollable_ = canScrollUp_ = canScrollDown_ = false;
    if (drawerT_ > 0.0f) {
        const float ppad = theme::kPanelPad * s;
        const float tileW = theme::kTileW * s;
        const float tileH = theme::kTileH * s;
        const float avail = screen.x - 2 * margin - 2 * ppad;
        const int cols =
            std::clamp(static_cast<int>((avail + gap) / (tileW + gap)), 1, theme::kDrawerMaxCols);
        categoryEntries(*m.cat, m.category, entries_, m.progress);
        const int total = static_cast<int>(entries_.size());
        const int rowsTotal = (total + cols - 1) / cols;
        const int rows = std::clamp(rowsTotal, 1, theme::kDrawerRows);
        if (scroll_.size() != m.cat->categories.size()) scroll_.assign(m.cat->categories.size(), 0);
        int& scroll = scroll_[static_cast<std::size_t>(m.category)];
        scroll = std::clamp(scroll, 0, std::max(0, rowsTotal - rows));
        scrollable_ = rowsTotal > rows;
        canScrollUp_ = scroll > 0;
        canScrollDown_ = scroll < rowsTotal - rows;

        // As wide as its tiles need (a young world has few), but never narrower than the tabs.
        float tabsW = -gap;
        for (const auto& cdef : m.cat->categories)
            tabsW += font.measure(Face::Body, cdef.name) + theme::kTabExtra * s + gap;
        if (scrollable_) tabsW += 2 * theme::kTabH * s + gap * 1.5f;
        const int used = std::clamp(total, 1, cols);
        const float w = 2 * ppad + std::max(tabsW, static_cast<float>(used) * tileW +
                                                       static_cast<float>(used - 1) * gap);
        const float h = 2 * ppad + theme::kTabH * s + gap + static_cast<float>(rows) * tileH +
                        static_cast<float>(rows - 1) * gap;
        const float slide = (1.0f - smooth(drawerT_)) * slideBy(s);
        drawerBox_ = {margin, bottomTop_ - gap - h + slide, w, h};

        float tx = drawerBox_.x + ppad;
        const float ty = drawerBox_.y + ppad;
        for (std::size_t c = 0; c < m.cat->categories.size(); ++c) {
            const float tabW =
                font.measure(Face::Body, m.cat->categories[c].name) + theme::kTabExtra * s;
            Widget& t = add(kTab0 + static_cast<int>(c), {tx, ty, tabW, theme::kTabH * s});
            t.label = m.cat->categories[c].name;
            t.selected = static_cast<int>(c) == m.category;
            if (m.progress != nullptr) {
                const bool ground = isGroundCategory(*m.cat, static_cast<int>(c));
                for (std::size_t i = 0; i < (ground ? m.cat->terrain.size() : m.cat->items.size());
                     ++i)
                    t.dot = t.dot || (ground ? m.progress->newTerrain[i] != 0
                                             : m.cat->items[i].category == static_cast<int>(c) &&
                                                   m.progress->newItems[i] != 0);
            }
            tx += tabW + gap;
        }
        if (scrollable_) {
            // Row arrows at the end of the tab row; the wheel scrolls too.
            const float b = theme::kTabH * s;
            const float right = drawerBox_.x + drawerBox_.w - ppad;
            Widget& down = add(kScrollDown, {right - b, ty, b, b});
            down.icon = theme::icon::kChevronDown;
            down.tooltip = strings::kScrollDown;
            down.shortcut = strings::kKeyWheel;
            down.enabled = canScrollDown_;
            Widget& up = add(kScrollUp, {right - 2 * b - gap * 0.5f, ty, b, b});
            up.icon = theme::icon::kChevronUp;
            up.tooltip = strings::kScrollUp;
            up.shortcut = strings::kKeyWheel;
            up.enabled = canScrollUp_;
        }
        const float gy = ty + theme::kTabH * s + gap;
        for (int i = 0; i < rows * cols; ++i) {
            const int e = scroll * cols + i;
            if (e >= total) break;
            const int col = i % cols;
            const int row = i / cols;
            const DrawerEntry entry = entries_[static_cast<std::size_t>(e)];
            Widget& t = add(tileId(*m.cat, entry),
                            {drawerBox_.x + ppad + static_cast<float>(col) * (tileW + gap),
                             gy + static_cast<float>(row) * (tileH + gap), tileW, tileH});
            t.entry = entry;
            if (entry.locked) {
                const int n = lockedIn(*m.cat, m.category, m.progress);
                lockLabel_ = std::format("+{}", n);
                lockTip_ = std::vformat(strings::kTipLocked, std::make_format_args(n));
                t.label = lockLabel_;
                t.tooltip = lockTip_;
                t.icon = theme::icon::kLock;
                continue;
            }
            const auto idx = static_cast<std::size_t>(t.entry.index);
            t.label = t.entry.terrain ? std::string_view(m.cat->terrain[idx].name)
                                      : std::string_view(m.cat->items[idx].name);
            t.selected = (t.entry.terrain ? m.tool == Tool::Paint : m.tool == Tool::Place) &&
                         m.selection == t.entry.index;
            t.dot = entryNew(m.progress, entry);
        }
    }

    // The sketchbook, top right, never reaching under the drawer or the docks.
    journalBox_ = {};
    if (journalT_ > 0.0f) layoutSketchbook(m, font, screen, s);

    // A landmark's or figure's card: right of centre, clear of the docks.
    cardBox_ = {};
    if (cardT_ > 0.0f && !m.cardTitle.empty()) {
        const float pad = theme::kPanelPad * s;
        const float w = std::min(theme::kPlaceCardW * s, screen.x - 2 * margin);
        const float textW = w - 2 * pad;
        const float lines =
            static_cast<float>(wrapLines(font, Face::Body, m.cardText, textW, theme::kCardLines));
        float h =
            2 * pad + font.lineHeight(Face::Title) + lines * font.lineHeight(Face::Body) + gap;
        if (!m.cardNative.empty()) h += font.lineHeight(Face::Body);
        if (!m.cardEpithet.empty()) h += font.lineHeight(Face::Body);
        const float x = screen.x - margin - w;
        const float y = std::max(margin, (bottomTop_ - gap - h) * 0.5f);
        cardBox_ = {x + (1.0f - smooth(cardT_)) * slideBy(s), y, w, h};
        const float cs = theme::kCloseSize * s;
        const float ci = theme::kCloseInset * s;
        Widget& c = add(kCardClose, {cardBox_.x + w - ci - cs, y + ci, cs, cs});
        c.icon = theme::icon::kClose;
        c.tooltip = strings::kClose;
        c.shortcut = strings::kKeyEsc;
    }

    // "New land" above the right dock while a stage opened out of sight.
    if (m.edgeChip && !m.photo && !m.away) {
        const float cw = font.measure(Face::Body, strings::kNewLandChip) + theme::kIcon * s +
                         theme::kLabelGap * s + 2 * theme::kHintPad * s;
        const float ch = theme::kHintH * s;
        float y = bottomTop_ - gap - ch;
        if (drawerT_ > 0.0f) y = std::min(y, drawerBox_.y - gap - ch);
        Widget& w = add(kEdgeChip, {screen.x - margin - cw, y, cw, ch});
        w.label = strings::kNewLandChip;
        w.icon = theme::icon::kChevronRight;
        panels_.push_back({w.box, ch * 0.5f});
    }

    // Hint line above the drawer or docks; both slide a little as they fade.
    const float hintH = theme::kHintH * s;
    {
        const float hpad = theme::kHintPad * s;
        const float w1 = font.measure(Face::Body, hintText_);
        const float w2 = m.warning.empty() ? 0.0f : font.measure(Face::Body, m.warning);
        const float sep = (w1 > 0 && w2 > 0) ? font.measure(Face::Body, strings::kSeparator) : 0.0f;
        const float w = std::min(w1 + sep + w2 + 2 * hpad, screen.x - 2 * margin);
        const float a = smooth(hintT_);
        // Above an open drawer; a closing one lets it drop back at once, off the map.
        const float bottom = m.drawerOpen && drawerT_ > 0.0f ? drawerBox_.y : bottomTop_;
        hintBox_ = {std::round((screen.x - w) * 0.5f),
                    bottom - gap - hintH + (1 - a) * theme::kHintSlide * s, w, hintH};
    }
    // The ribbon announcing a granted wish: top centre, as wide as its content.
    ribbonBox_ = {};
    if (ribbonT_ > 0.0f) {
        const float pad = theme::kToastPad * s;
        const float icon = theme::kRibbonIcon * s;
        const float line2 = font.measure(Face::Body, ribbon_.text) +
                            static_cast<float>(ribbon_.iconCount) * (icon + gap * 0.5f) + gap;
        const float line1 =
            theme::kIcon * s + theme::kToastIconGap * s + font.measure(Face::Title, ribbon_.title);
        // Between the title and the tray when that band is wide enough, else across the top.
        const float bandL = titleBox_.x + titleBox_.w + gap;
        float bandR = trayLast_.w > 0 && !tray_.empty() ? trayLast_.x - gap : screen.x - margin;
        if (journalT_ > 0.0f) bandR = std::min(bandR, journalBox_.x - gap);
        const bool inBand = bandR - bandL >= theme::kRibbonMinW * s;
        // Too narrow beside the title: under it, still clear of the tray and the sketchbook.
        const bool under = !inBand && bandR - margin >= theme::kRibbonMinW * s;
        const float maxW = std::min(theme::kRibbonMaxW * s, inBand  ? bandR - bandL
                                                            : under ? bandR - margin
                                                                    : screen.x - 2 * margin);
        const float quoteW = std::min(font.measure(Face::Body, ribbon_.quote), maxW - 2 * pad);
        const float w = std::min(maxW, std::max({line1, line2, quoteW}) + 2 * pad);
        const float lh = font.lineHeight(Face::Body);
        const int quoteLines =
            ribbon_.quote.empty() ? 0 : wrapLines(font, Face::Body, ribbon_.quote, w - 2 * pad, 2);
        const float h = 2 * pad + font.lineHeight(Face::Title) + gap * 0.5f + std::max(icon, lh) +
                        (quoteLines > 0 ? gap * 0.5f + static_cast<float>(quoteLines) * lh : 0.0f);
        const float x = inBand  ? std::clamp(std::round((screen.x - w) * 0.5f), bandL, bandR - w)
                        : under ? margin
                                : std::round((screen.x - w) * 0.5f);
        const float y = under ? titleBox_.y + titleBox_.h + gap : margin;
        ribbonBox_ = {x, y - (1 - smooth(ribbonT_)) * theme::kToastSlide * s, w, h};
    }
    // The toast sits in the free band between the title and the journal, or below the title
    // when that band is too narrow; below the ribbon while one shows.
    {
        const float tpad = theme::kToastPad * s;
        const float chrome = theme::kIcon * s + theme::kToastIconGap * s + 2 * tpad;
        const float w = std::min({chrome + font.measure(Face::Body, toast_), theme::kRibbonMaxW * s,
                                  screen.x - 2 * margin});
        // A long toast wraps to a second line rather than running off the glass.
        toastLines_ = wrapLines(font, Face::Body, toast_, w - chrome, theme::kToastLines);
        const float h =
            theme::kToastH * s + static_cast<float>(toastLines_ - 1) * font.lineHeight(Face::Body);
        const float left = titleBox_.x + titleBox_.w + gap;
        float right = journalT_ > 0.0f ? journalBox_.x - gap : screen.x - margin;
        if (trayT_ > 0.0f && trayBox_.w > 0) right = std::min(right, trayBox_.x - gap);
        float x = std::round((screen.x - w) * 0.5f);
        float y = ribbonBox_.w > 0 ? ribbonBox_.y + ribbonBox_.h + gap : margin;
        if (x < left || x + w > right) {
            x = std::round(std::clamp((left + right - w) * 0.5f, left, std::max(left, right - w)));
            if (x + w > right) {
                x = margin;
                y = titleBox_.y + titleBox_.h + gap;
            }
        }
        toastBox_ = {x, y - (1 - smooth(toastT_)) * theme::kToastSlide * s, w, h};
    }
    const float top = titleBox_.y + titleBox_.h + gap;
    safe_ = {margin, top, screen.x - 2 * margin,
             std::max(0.0f, bottomTop_ - gap - hintH - gap - top)};
}

void Hud::update(const UiInput& in, const HudModel& m, const Font& font, Vec2 screen, float s,
                 float dt) {
    actionCount_ = 0;
    scale_ = s;
    const auto ids = static_cast<std::size_t>(
        tileId(*m.cat, {.locked = true, .index = static_cast<int>(m.cat->categories.size())}));
    if (hover_.size() != ids) {
        hover_.assign(ids, 0.0f);
        press_.assign(ids, 0.0f);
    }
    screen_ = screen;
    drawerT_ = approach(drawerT_, m.drawerOpen && !m.photo && !m.away, dt);
    cardT_ = approach(cardT_, !m.cardTitle.empty() && !m.photo, dt);
    journalT_ = approach(journalT_, m.journalOpen && !m.photo, dt);
    // In photo mode only the hint line stays (it says how to take the photo and get back).
    hintT_ = approach(hintT_, !m.hint.empty() || !m.warning.empty(), dt);
    // While others wait, a toast steps aside once it has been up long enough to read.
    toastShown_ += dt;
    if (toastWaiting_ > 0)
        toastTime_ = std::min(toastTime_, std::max(0.0f, theme::kToastQueuedSeconds - toastShown_));
    toastTime_ = std::max(0.0f, toastTime_ - dt);
    toastT_ = approach(toastT_, toastTime_ > 0.0f, dt);
    if (toastTime_ <= 0.0f && toastT_ <= 0.0f && toastWaiting_ > 0 && !toastsHeld_) {
        toast_ = std::move(toastQueue_[0]);
        std::ranges::rotate(toastQueue_, toastQueue_.begin() + 1);
        --toastWaiting_;
        toastTime_ = theme::kToastSeconds;
        toastShown_ = 0;
    }
    flash_ = std::max(0.0f, flash_ - dt / theme::kFlashSeconds);
    pulseT_ += dt;
    if (m.photo) calendarOpen_ = false;
    calendarT_ = approach(calendarT_, calendarOpen_, dt);
    ribbonTime_ = std::max(0.0f, ribbonTime_ - dt);
    ribbonT_ = approach(ribbonT_, ribbonTime_ > 0.0f && !m.photo, dt);

    // Tray cards follow the open wishes: new ones slide in, granted or snoozed ones fade up.
    for (TrayCard& t : tray_) t.open = false;
    for (const WishCard& c : m.wishes) {
        const auto it = std::ranges::find_if(
            tray_, [&](const TrayCard& t) { return t.card.wish == c.wish && t.out == 0.0f; });
        if (it != tray_.end()) {
            it->card = c;
            it->open = true;
        } else if (std::cmp_less(tray_.size(), kTraySlots)) {
            tray_.push_back({c, 0.0f, 0.0f, true, {}, 1});
        }
    }
    for (TrayCard& t : tray_) {
        t.in = std::min(1.0f, t.in + dt / theme::kCardIn);
        if (!t.open) {
            t.card.detail = {}; // its text belonged to the open card
            t.out = std::min(1.0f, t.out + dt / theme::kCardOut);
        }
    }
    std::erase_if(tray_, [](const TrayCard& t) { return t.out >= 1.0f; });
    if (menuWish_ >= 0 &&
        std::ranges::none_of(m.wishes, [&](const WishCard& c) { return c.wish == menuWish_; }))
        menuWish_ = -1;
    // The tray steps aside for the journal, for photos and for a drawer that reaches it.
    const bool drawerOverTray = drawerT_ > 0.0f && trayLast_.w > 0 && drawerBox_.w > 0 &&
                                drawerBox_.y < trayLast_.y + trayLast_.h &&
                                drawerBox_.x + drawerBox_.w > trayLast_.x;
    const bool ribbonOverTray = ribbonT_ > 0.0f && trayLast_.w > 0 && ribbonBox_.w > 0 &&
                                ribbonBox_.x + ribbonBox_.w > trayLast_.x;
    // On a narrow window the calendar can reach across to the tray: the tray waits (QA2-11).
    const bool calendarOverTray = calendarT_ > 0.0f && trayLast_.w > 0 && calendarBox_.w > 0 &&
                                  calendarBox_.x + calendarBox_.w > trayLast_.x &&
                                  calendarBox_.y < trayLast_.y + trayLast_.h;
    trayT_ = approach(trayT_,
                      !tray_.empty() && !m.journalOpen && !m.photo && !m.away && !drawerOverTray &&
                          !ribbonOverTray && !calendarOverTray,
                      dt);
    const auto end = std::format_to_n(trayCount_, sizeof trayCount_ - 1, "{}", m.wishes.size());
    *end.out = '\0';

    // The wheel scrolls what the pointer was over in the frame on screen, before this frame's
    // layout clamps the scroll, so drawing never runs past the end of a list (QA2-02).
    if (in.wheel != 0 && in.inside && !in.blocked && !m.photo) {
        if (drawerT_ > 0.5f && drawerBox_.contains(in.x, in.y) && !scroll_.empty())
            scroll_[static_cast<std::size_t>(m.category)] += in.wheel > 0 ? -1 : 1;
        if (journalT_ > 0.5f && journalBox_.contains(in.x, in.y))
            sketchScroll_ += in.wheel > 0 ? -1 : 1;
    }

    if (noteLabel_.empty())
        noteLabel_ =
            m.cat->residentKind >= 0
                ? std::vformat(strings::kNoteLabel, std::make_format_args(m.cat->resident.name))
                : std::string(strings::kNoteLabelAlone);

    clockLabel_.assign(phaseName(m.phase));
    if (!m.cat->seasons.empty()) {
        clockLabel_.append(strings::kSeparator)
            .append(m.cat->seasons[static_cast<std::size_t>(m.season)].name)
            .append(" ")
            .append(std::to_string(m.seasonDay + 1));
    }
    if (m.pin != ClockPin::Auto) clockLabel_.append(strings::kSeparator).append(strings::kPinned);
    if (m.raining)
        clockLabel_.append(strings::kSeparator)
            .append(m.snow ? strings::kSnowing : strings::kRaining);
    // A hint fading out keeps its words until it is gone (an empty pill would shrink to a dot).
    if (!m.hint.empty() || !m.warning.empty() || hintT_ <= 0) hintText_.assign(m.hint);

    layout(m, font, screen, s);

    if (m.photo) {
        overUi_ = captured_ = false;
        hovered_ = pointed_ = active_ = 0;
        return;
    }
    const bool canPoint = in.inside && !in.blocked;
    pointer_ = {in.x, in.y};
    overUi_ = false;
    int hovered = 0; // enabled widget under the pointer
    int pointed = 0; // any widget under the pointer: disabled ones still explain themselves
    if (canPoint) {
        for (const Panel& p : panels_)
            if (p.box.contains(in.x, in.y)) overUi_ = true;
        // Every visible panel stops the pointer, so neither clicks nor the placement ghost reach
        // the map through it.
        if (titleBox_.contains(in.x, in.y) ||
            (m.drawerOpen && drawerT_ > 0.5f && drawerBox_.contains(in.x, in.y)) ||
            (journalT_ > 0.5f && journalBox_.contains(in.x, in.y)) ||
            (hintT_ > 0.5f && hintBox_.contains(in.x, in.y)) ||
            (toastT_ > 0.5f && !toast_.empty() && toastBox_.contains(in.x, in.y)) ||
            (trayT_ > 0.5f && trayBox_.contains(in.x, in.y)) ||
            (ribbonT_ > 0.5f && ribbonBox_.contains(in.x, in.y)) ||
            (calendarT_ > 0.5f && calendarBox_.contains(in.x, in.y)))
            overUi_ = true;
        // A drawer on its way out no longer holds the pointer: the map is usable at once after
        // picking a piece.
        const bool drawerLeaving = !m.drawerOpen && drawerT_ < 1.0f;
        for (auto it = widgets_.rbegin(); it != widgets_.rend(); ++it) {
            if (drawerLeaving && (it->id >= kTab0 || it->id == kScrollUp || it->id == kScrollDown))
                continue;
            if (it->box.contains(in.x, in.y)) {
                overUi_ = true;
                pointed = it->id;
                if (it->enabled) hovered = it->id;
                break;
            }
        }
    }
    // Panels that are animating closed are not interactive.
    if ((hovered >= kTab0 || hovered == kScrollUp || hovered == kScrollDown) && drawerT_ < 1.0f &&
        !m.drawerOpen)
        hovered = 0;
    if ((hovered == kJournalClose || (hovered >= kSketchTab0 && hovered < kSketchNotNow0 + 3)) &&
        !m.journalOpen)
        hovered = 0;
    if (hovered != hovered_ && hovered != 0) {
        emit(HudAction::Kind::Hover);
        for (const Widget& w : widgets_)
            if (w.id == hovered && w.dot && hovered >= kTile0)
                emit(HudAction::Kind::SeenNew, w.entry.code(*m.cat));
    }
    if (pointed != pointed_) hoverTime_ = 0;
    hovered_ = hovered;
    pointed_ = pointed;
    hoverTime_ += dt;

    // A right click on a wish card opens its small menu; any other click closes it.
    if (in.rightPressed && canPoint) {
        menuWish_ = -1;
        if (hovered >= kCard0 && hovered < kNotNow) {
            const auto slot = static_cast<std::size_t>(hovered - kCard0);
            if (slot < tray_.size() && tray_[slot].open) {
                menuWish_ = tray_[slot].card.wish;
                emit(HudAction::Kind::Hover);
            }
        }
    }
    if (in.pressed && canPoint && hovered != kNotNow) menuWish_ = -1;
    // A click elsewhere closes the calendar.
    if (in.pressed && canPoint && calendarOpen_ && hovered != kTitleCard &&
        (hovered < kCalPin0 || hovered > kCalPin0 + 8) && !calendarBox_.contains(in.x, in.y))
        calendarOpen_ = false;
    if (in.pressed && canPoint && overUi_) {
        captured_ = true;
        active_ = hovered;
        hoverTime_ = -10.0f; // no tooltip right after a click
    }
    if (in.released && captured_) {
        if (active_ != 0 && active_ == hovered) {
            const auto entry = [&] {
                for (const Widget& w : widgets_)
                    if (w.id == active_) return w.entry;
                return DrawerEntry{};
            }();
            switch (active_) {
            case kBuild: emit(HudAction::Kind::ToggleBuild); break;
            case kRemove: emit(HudAction::Kind::RemoveTool); break;
            case kMove: emit(HudAction::Kind::MoveTool); break;
            case kMenu: emit(HudAction::Kind::Menu); break;
            case kPhoto: emit(HudAction::Kind::Photo); break;
            case kClock: emit(HudAction::Kind::Clock); break;
            case kRain: emit(HudAction::Kind::Rain); break;
            case kJournal:
            case kJournalClose: emit(HudAction::Kind::Journal); break;
            case kUndo: emit(HudAction::Kind::Undo); break;
            case kRedo: emit(HudAction::Kind::Redo); break;
            case kRecentre: emit(HudAction::Kind::Recentre); break;
            case kMap: emit(HudAction::Kind::Map); break;
            case kSoundButton: emit(HudAction::Kind::Mute); break;
            case kCardClose: emit(HudAction::Kind::CloseCard); break;
            case kZoomOut: emit(HudAction::Kind::ZoomOut); break;
            case kZoomIn: emit(HudAction::Kind::ZoomIn); break;
            case kScrollUp:
                if (!scroll_.empty()) --scroll_[static_cast<std::size_t>(m.category)];
                break;
            case kScrollDown:
                if (!scroll_.empty()) ++scroll_[static_cast<std::size_t>(m.category)];
                break;
            case kTrayHeader: trayCollapsed_ = !trayCollapsed_; break;
            case kTitleCard: calendarOpen_ = !calendarOpen_; break;
            case kCalPin0:
            case kCalPin0 + 1:
            case kCalPin0 + 2:
            case kCalPin0 + 3:
            case kCalPin0 + 4:
            case kCalPin0 + 5:
            case kCalPin0 + 6:
            case kCalPin0 + 7:
            case kCalPin0 + 8: emit(HudAction::Kind::SeasonPin, active_ - kCalPin0 - 1); break;
            case kEdgeChip: emit(HudAction::Kind::EdgeChip); break;
            case kSketchTab0:
            case kSketchTab0 + 1:
            case kSketchTab0 + 2:
            case kSketchTab0 + 3:
            case kSketchTab0 + 4:
            case kSketchTab0 + 5:
            case kSketchTab0 + 6:
            case kSketchTab0 + 7:
            case kSketchTab0 + 8:
            case kSketchTab0 + 9:
            case kSketchTab0 + 10:
            case kSketchTab0 + 11:
                if (entry.index != sketchTab_) {
                    sketchTab_ = entry.index;
                    sketchScroll_ = 0;
                    emit(HudAction::Kind::PageTurn);
                }
                break;
            case kSketchNotNow0:
            case kSketchNotNow0 + 1:
            case kSketchNotNow0 + 2: emit(HudAction::Kind::Snooze, entry.index); break;
            case kNotNow:
                emit(HudAction::Kind::Snooze, menuWish_);
                menuWish_ = -1;
                break;
            default:
                if (active_ >= kCard0 && active_ < kNotNow) {
                    const auto slot = static_cast<std::size_t>(active_ - kCard0);
                    if (slot < tray_.size())
                        emit(HudAction::Kind::OpenWishes, tray_[slot].card.wish);
                } else if (active_ >= kTile0 && entry.locked) {
                    emit(HudAction::Kind::OpenWishes, -1);
                } else if (active_ >= kTile0) {
                    emit(entry.terrain ? HudAction::Kind::PickTerrain : HudAction::Kind::PickItem,
                         entry.index);
                } else if (active_ >= kTab0) {
                    emit(HudAction::Kind::Category, active_ - kTab0);
                }
            }
        }
        active_ = 0;
        captured_ = false;
    }

    for (std::size_t i = 1; i < hover_.size(); ++i) {
        const int id = static_cast<int>(i);
        hover_[i] = approach(hover_[i], id == hovered_, dt);
        press_[i] = approach(press_[i], id == active_ && id == hovered_, dt * 2);
    }
    worldTipT_ = approach(worldTipT_, !m.worldTip.empty() && !overUi_ && canPoint, dt);
    const bool showTip = pointed_ != 0 && hoverTime_ > theme::kTooltipDelay && active_ == 0;
    if (showTip) tooltipId_ = pointed_;
    tooltipT_ = approach(tooltipT_, showTip, dt);
}

void Hud::layoutTray(const Font& font, Vec2 screen, float s) {
    trayBox_ = {};
    menuBox_ = {};
    if (trayT_ <= 0.0f || tray_.empty()) return;
    const float margin = theme::kMargin * s;
    const float pad = theme::kCardPad * s;
    const float portrait = theme::kPortrait * s;
    const float w = std::min(theme::kTrayW * s, screen.x - 2 * margin);
    const float x = screen.x - margin - w + (1.0f - smooth(trayT_)) * slideBy(s);
    const float header = theme::kTrayHeader * s;
    Widget& h = add(kTrayHeader, {x, margin, w, header});
    h.tooltip = strings::kWishes;
    float y = margin + header;
    const float textX = pad + portrait + theme::kCardGap * s;
    const float textW = w - textX - pad;
    const float lh = font.lineHeight(Face::Body);
    for (std::size_t i = 0; i < tray_.size(); ++i) {
        TrayCard& t = tray_[i];
        t.lines = static_cast<float>(wrapLines(font, Face::Body, t.card.text, textW, 2));
        const float detail = t.card.detail.empty() ? 0.0f : lh + theme::kBarGap * s;
        const float body = std::max(portrait, t.lines * lh + detail);
        // A leaving card folds away as it fades.
        const float hgt = (body + 2 * pad) * (1.0f - smooth(t.out));
        t.box = {x, y, w, hgt};
        if (trayCollapsed_) t.box.h = 0;
        if (!trayCollapsed_ && t.open && trayT_ >= 1.0f) {
            Widget& c = add(kCard0 + static_cast<int>(i), t.box);
            // The full text, only when the card cuts it short.
            if (wrapLines(font, Face::Body, t.card.text, textW, 3) > 2) c.tooltip = t.card.text;
        }
        y += t.box.h;
        if (t.card.wish == menuWish_ && t.open && !trayCollapsed_) {
            const float mw = font.measure(Face::Body, strings::kNotNow) + 2 * theme::kTipPad * s;
            const float mh = theme::kTipH * s;
            menuBox_ = {x - mw - theme::kGap * s, t.box.y + (t.box.h - mh) * 0.5f, mw, mh};
            Widget& n = add(kNotNow, menuBox_);
            n.label = strings::kNotNow;
        }
    }
    trayBox_ = {x, margin, w, y - margin + (trayCollapsed_ ? 0.0f : pad * 0.25f)};
    trayLast_ = trayBox_;
}

const Hud::Widget* Hud::find(std::string_view name, const HudModel& m) const {
    int id = 0;
    for (const Named& n : kNames)
        if (n.name == name) id = n.id;
    const auto byPrefix = [&](std::string_view prefix) -> std::optional<std::string_view> {
        if (!name.starts_with(prefix)) return std::nullopt;
        return name.substr(prefix.size());
    };
    if (const auto tab = byPrefix("tab:")) {
        if (const auto c = m.cat->findCategory(*tab)) id = kTab0 + *c;
    }
    const auto tile = byPrefix("tile:");
    for (const Widget& w : widgets_) {
        if (tile && w.id >= kTile0) {
            if (w.entry.locked) {
                if (*tile == "locked") return &w;
                continue;
            }
            const auto i = static_cast<std::size_t>(w.entry.index);
            const auto& entryId = w.entry.terrain ? m.cat->terrain[i].id : m.cat->items[i].id;
            if (entryId == *tile) return &w;
        } else if (id != 0 && w.id == id) {
            return &w;
        }
    }
    return nullptr;
}

std::optional<Vec2> Hud::widgetCentre(std::string_view name, const HudModel& m) const {
    if (name == "toast" && toastT_ > 0.5f) return Vec2{toastBox_.cx(), toastBox_.cy()};
    if (name.starts_with("card:")) {
        // "card:N": the N-th open wish card.
        int n = 0;
        const std::string_view digits = name.substr(5);
        if (std::from_chars(digits.data(), digits.data() + digits.size(), n).ec != std::errc{})
            return std::nullopt;
        int k = 0;
        for (const TrayCard& t : tray_)
            if (t.open && t.box.h > 0 && k++ == n) return Vec2{t.box.cx(), t.box.cy()};
        return std::nullopt;
    }
    if (name == "hint" && hintT_ > 0.5f) return Vec2{hintBox_.cx(), hintBox_.cy()};
    const Widget* w = find(name, m);
    if (w == nullptr) return std::nullopt;
    return Vec2{w->box.cx(), w->box.cy()};
}

float Hud::highlight(std::string_view name, const HudModel& m) const {
    const Widget* w = find(name, m);
    return w != nullptr ? hoverOf(w->id) : 0.0f;
}

Hud::Thumbnailed Hud::thumbFor(const HudModel& m, DrawerEntry e, float box) const {
    const ThumbSet& t = *m.thumbs;
    const auto& list = e.terrain ? t.terrain : t.items;
    const Sprite* s = e.index >= 0 && std::cmp_less(e.index, list.size())
                          ? &list[static_cast<std::size_t>(e.index)]
                          : &t.placeholder;
    // One-tile things share one scale (a bush stays smaller than an oak); bigger pieces shrink
    // to fit.
    return {s, box / t.tileW};
}

void Hud::drawButton(Painter& p, const Widget& w, float alpha) const {
    const float s = scale_;
    const float h = w.enabled ? hoverOf(w.id) : 0.0f;
    const float pr = pressOf(w.id);
    const float r = std::min(w.box.w, w.box.h) * 0.5f;
    const float inset =
        (w.id == kBuild || w.id == kRemove || w.id == kMove) ? theme::kDockPad * s : 0.0f;
    const Box inner{w.box.x + inset, w.box.y + inset, w.box.w - 2 * inset, w.box.h - 2 * inset};
    const float ir = r - inset;
    if (w.selected) {
        p.roundRect(inner, ir, withAlpha(theme::kAccentWash, alpha));
        p.rim(inner, ir, theme::kRim * s, withAlpha(theme::kAccentRim, alpha),
              withAlpha(theme::kAccentRim, alpha * 0.5f));
    }
    if (h > 0) p.roundRect(inner, ir, withAlpha(theme::kHover, alpha * h));
    if (pr > 0) p.roundRect(inner, ir, withAlpha(theme::kPressed, alpha * pr));
    SDL_FColor ink = theme::kInk;
    if (!w.enabled) ink = withAlpha(ink, theme::kInkDisabled);
    ink = withAlpha(ink, alpha);
    const float press = pr * s; // content dips one unit while pressed
    if (!w.label.empty()) {
        const Font& f = p.font();
        const float textW = f.measure(Face::Body, w.label);
        const float iconW = theme::kIcon * s;
        const float total = iconW + theme::kLabelGap * s + textW;
        const float x0 = inner.cx() - total * 0.5f;
        p.icon(w.icon, x0 + iconW * 0.5f, inner.cy() + press, ink);
        p.text(Face::Body, w.label, x0 + iconW + theme::kLabelGap * s,
               inner.cy() + press + f.ascent(Face::Body) * theme::kBaselineCentre, ink);
    } else {
        p.icon(w.icon, inner.cx(), inner.cy() + press, ink);
    }
    if (w.dot) drawDot(p, inner.x + inner.w - ir * 0.55f, inner.y + ir * 0.45f, s, alpha);
}

void Hud::drawPill(Painter& p, const Widget& w, float alpha) const {
    const float r = w.box.h * 0.5f;
    p.roundRect(w.box, r, withAlpha(theme::kInset, alpha));
    p.rim(w.box, r, theme::kRim * scale_, withAlpha(theme::kInsetRimTop, alpha),
          withAlpha(theme::kInsetRimBottom, alpha));
    const float h = hoverOf(w.id);
    if (h > 0) p.roundRect(w.box, r, withAlpha(theme::kHover, alpha * h));
    const float pr = pressOf(w.id);
    if (pr > 0) p.roundRect(w.box, r, withAlpha(theme::kPressed, alpha * pr));
    const Font& f = p.font();
    p.text(Face::Body, w.label, w.box.cx() - f.measure(Face::Body, w.label) * 0.5f,
           w.box.cy() + f.ascent(Face::Body) * theme::kBaselineCentre,
           withAlpha(mixColor(theme::kInkMuted, theme::kInk, h), alpha));
}

void Hud::drawTab(Painter& p, const Widget& w, float alpha) const {
    const float r = w.box.h * 0.5f;
    const float h = hoverOf(w.id);
    if (w.selected) {
        p.roundRect(w.box, r, withAlpha(theme::kAccentWash, alpha));
        p.rim(w.box, r, theme::kRim * scale_, withAlpha(theme::kAccentRim, alpha),
              withAlpha(theme::kAccentRim, alpha * 0.5f));
    }
    if (h > 0) p.roundRect(w.box, r, withAlpha(theme::kHover, alpha * h));
    const Font& f = p.font();
    const float tw = f.measure(Face::Body, w.label);
    const SDL_FColor ink = w.selected ? theme::kInk : mixColor(theme::kInkMuted, theme::kInk, h);
    p.text(Face::Body, w.label, w.box.cx() - tw * 0.5f,
           w.box.cy() + f.ascent(Face::Body) * theme::kBaselineCentre, withAlpha(ink, alpha));
    if (w.dot) drawDot(p, w.box.x + w.box.w - r * 0.6f, w.box.y + r * 0.5f, scale_, alpha);
}

void Hud::drawTile(Painter& p, const Widget& w, const HudModel& m, float alpha) const {
    const float s = scale_;
    const float h = hoverOf(w.id);
    const float pr = pressOf(w.id);
    const float r = theme::kTileRadius * s;
    p.roundRect(w.box, r, withAlpha(theme::kInset, alpha));
    if (w.selected) {
        p.roundRect(w.box, r, withAlpha(theme::kAccentWash, alpha));
        p.rim(w.box, r, 2 * theme::kRim * s, withAlpha(theme::kAccentRim, alpha),
              withAlpha(theme::kAccentRim, alpha * 0.7f));
    } else {
        p.rim(w.box, r, theme::kRim * s, withAlpha(theme::kInsetRimTop, alpha),
              withAlpha(theme::kInsetRimBottom, alpha));
    }
    if (h > 0) p.roundRect(w.box, r, withAlpha(theme::kHover, alpha * h));
    if (pr > 0) p.roundRect(w.box, r, withAlpha(theme::kPressed, alpha * pr));

    const float inset = theme::kTileInset * s;
    const Box box{w.box.x + inset, w.box.y + theme::kThumbTop * s - (h * theme::kTileLift - pr) * s,
                  w.box.w - 2 * inset, theme::kThumb * s};
    if (w.entry.locked) {
        // Pieces still to discover: a quiet lock and a count, no art.
        const SDL_FColor muted = withAlpha(theme::kInkMuted, alpha);
        p.icon(theme::icon::kLock, box.cx(), box.cy(), muted);
        const Font& f = p.font();
        p.text(Face::Body, w.label, w.box.cx() - f.measure(Face::Body, w.label) * 0.5f,
               w.box.y + w.box.h - theme::kTileLabelBottom * s, muted);
        return;
    }
    const Thumbnailed t = thumbFor(m, w.entry, box.w);
    p.thumbnail(*t.sprite, box, t.maxScale, alpha);
    if (w.dot) drawDot(p, w.box.x + w.box.w - r * 0.75f, w.box.y + r * 0.75f, s, alpha);

    const Font& f = p.font();
    std::string_view label = w.label;
    const float maxW = w.box.w - 2 * inset;
    float tw = f.measure(Face::Body, label);
    bool cut = false;
    while (tw > maxW && label.size() > 1) {
        label.remove_suffix(1);
        tw = f.measure(Face::Body, label) + f.measure(Face::Body, "…");
        cut = true;
    }
    const float x = w.box.cx() - tw * 0.5f;
    const float base = w.box.y + w.box.h - theme::kTileLabelBottom * s;
    const SDL_FColor ink = withAlpha(theme::kInk, alpha);
    const float adv = f.measure(Face::Body, label);
    p.text(Face::Body, label, x, base, ink);
    if (cut) p.text(Face::Body, "…", x + adv, base, ink);
}

void Hud::drawTitle(Painter& p, const HudModel& m) const {
    const float s = scale_;
    const Font& f = p.font();
    const float pad = theme::kTitlePad * s;
    const float iconW = theme::kIcon * s;
    const float lh1 = f.lineHeight(Face::Title);
    const float lh2 = f.lineHeight(Face::Body);
    const Box b = titleBox_;
    p.text(Face::Title, titleName_, b.x + pad, b.y + pad + f.ascent(Face::Title), theme::kInk);
    const float h = hoverOf(kTitleCard);
    if (h > 0) p.roundRect(b, theme::kPanelRadius * s, withAlpha(theme::kHover, h * 0.6f));
    const float y2 = b.y + pad + lh1;
    p.icon(phaseIcon(m.phase), b.x + pad + iconW * 0.5f, y2 + lh2 * 0.5f, theme::kInkMuted);
    p.text(Face::Body, clockLabel_, b.x + pad + iconW + theme::kTitleIconGap * s,
           y2 + f.ascent(Face::Body), theme::kInkMuted);
}

void Hud::openSketchbook(int tab) {
    sketchTab_ = std::clamp(tab, 0, kSketchNotNow0 - kSketchTab0 - 1);
    sketchScroll_ = 0;
}

void Hud::turnPage(int delta, const HudModel& m) {
    const int tabs = sketchTabs(m);
    sketchTab_ = (sketchTab_ + delta + tabs) % tabs;
    sketchScroll_ = 0;
}

const JournalPlace& Hud::placeOpen(const HudModel& m) const {
    const int homeTabs = m.progress != nullptr && m.progress->nooksFound() > 0 ? 3 : 2;
    return m.places[static_cast<std::size_t>(
        std::clamp(sketchTab_ - homeTabs, 0, static_cast<int>(m.places.size()) - 1))];
}

int Hud::sketchTabs(const HudModel& m) {
    // The nooks tab appears with the first nook found; then a tab per place visited.
    const int home = m.progress != nullptr && m.progress->nooksFound() > 0 ? 3 : 2;
    return std::min(home + static_cast<int>(m.places.size()), kSketchNotNow0 - kSketchTab0);
}

void Hud::layoutSketchbook(const HudModel& m, const Font& font, Vec2 screen, float s) {
    const float margin = theme::kMargin * s;
    const float gap = theme::kGap * s;
    const float pad = theme::kPanelPad * s;
    const float lh = font.lineHeight(Face::Body);
    const float jw = std::min(theme::kSketchW * s, screen.x - 2 * margin);
    const float slide = (1.0f - smooth(journalT_)) * slideBy(s);
    const float x = screen.x - margin - jw + slide;
    float bottom = bottomTop_ - gap;
    if (drawerT_ > 0.0f && x < drawerBox_.x + drawerBox_.w) bottom = drawerBox_.y - gap;
    const float header = theme::kJournalHeader * s;
    const float cs = theme::kCloseSize * s;
    const float ci = theme::kCloseInset * s;
    Widget& c = add(kJournalClose, {x + jw - ci - cs, margin + ci, cs, cs});
    c.icon = theme::icon::kClose;
    c.tooltip = strings::kClose;
    c.shortcut = strings::kKeyJournal;

    // Pages line, then the tabs.
    pagesText_ = std::vformat(strings::kPagesOf, std::make_format_args(m.pages, m.pagesTotal));
    untilText_.clear();
    if (m.nextStagePages < 0) {
        untilText_ = strings::kAllOpen;
    } else {
        std::string stage(m.nextStageName);
        if (!stage.empty())
            stage[0] = static_cast<char>(std::tolower(static_cast<unsigned char>(stage[0])));
        const int more = std::max(0, m.nextStagePages - m.pages);
        untilText_ = std::vformat(strings::kMoreUntil, std::make_format_args(more, stage));
    }
    float y = margin + header + gap * 0.5f + 2 * lh + gap;
    const int tabs = sketchTabs(m);
    sketchTab_ = std::min(sketchTab_, tabs - 1);
    static constexpr std::string_view kTabNames[] = {strings::kTabWishes, strings::kTabVisitors,
                                                     strings::kTabNooks};
    const int homeTabs = m.progress != nullptr && m.progress->nooksFound() > 0 ? 3 : 2;
    float tx = x + pad;
    for (int t = 0; t < tabs; ++t) {
        const std::string_view name =
            t < homeTabs ? kTabNames[t] : m.places[static_cast<std::size_t>(t - homeTabs)].name;
        const float tw = font.measure(Face::Body, name) + theme::kTabExtra * s;
        // Tabs wrap onto another row rather than run past the page.
        if (tx > x + pad && tx + tw > x + jw - pad) {
            tx = x + pad;
            y += theme::kTabH * s + gap * 0.5f;
        }
        // The home's tabs keep their ids (scripts name them); places follow the nooks' slot.
        Widget& w = add(t < homeTabs ? kSketchTab0 + t : kSketchTab0 + 3 + (t - homeTabs),
                        {tx, y, tw, theme::kTabH * s});
        w.label = name;
        w.entry.index = t;
        w.selected = t == sketchTab_;
        tx += tw + gap;
    }
    y += theme::kTabH * s + gap;
    sketchBody_ = y;

    // Rows of the open tab, measured so the panel can stop at the last one that fits.
    rows_.clear();
    const float icon = theme::kJournalIcon * s;
    const float textW = jw - 2 * pad - icon - theme::kJournalTextGap * s;
    const float rowPad = theme::kJournalRowPad * s;
    const auto rowH = [&](float body) { return std::max(icon, body) + 2 * rowPad; };
    const auto lines = [&](std::string_view text, float w, int max) {
        return static_cast<float>(wrapLines(font, Face::Body, text, w, max)) * lh;
    };
    const Catalog& cat = *m.cat;
    const Progress* pr = m.progress;
    if (sketchTab_ == 0 && pr != nullptr) {
        const float nowW = font.measure(Face::Body, strings::kNotNow) + 2 * theme::kTipPad * s;
        if (!m.wishes.empty()) rows_.push_back({Row::Kind::Section, 0, lh + gap});
        for (std::size_t i = 0; i < m.wishes.size(); ++i) {
            const WishCard& card = m.wishes[i];
            const float body =
                lines(card.text, textW - nowW - gap, 3) + (card.detail.empty() ? 0.0f : lh);
            rows_.push_back({Row::Kind::OpenWish, static_cast<int>(i), rowH(body)});
        }
        if (!pr->granted.empty()) rows_.push_back({Row::Kind::Section, 1, lh + gap});
        for (std::size_t k = pr->granted.size(); k-- > 0;) {
            const WishDef& w = cat.wishes[static_cast<std::size_t>(pr->granted[k])];
            rows_.push_back(
                {Row::Kind::GrantedWish, pr->granted[k], rowH(lines(w.thanks, textW, 2) + lh)});
        }
    } else if (sketchTab_ == 1) {
        int commonSeen = 0;
        for (std::size_t v = 0; v < cat.visitors.size(); ++v) {
            const VisitorDef& def = cat.visitors[v];
            if (def.rare) continue;
            const bool seen = m.visitors->seen(static_cast<int>(v));
            commonSeen += seen ? 1 : 0;
            rows_.push_back({Row::Kind::Visitor, static_cast<int>(v),
                             rowH(lh + lines(seen ? def.blurb : def.hint, textW, 2))});
        }
        // The rarer visitors appear once four common ones have been seen.
        if (commonSeen >= theme::kRareSectionAfter) {
            rows_.push_back({Row::Kind::Section, 2, lh + gap});
            for (std::size_t v = 0; v < cat.visitors.size(); ++v) {
                const VisitorDef& def = cat.visitors[v];
                if (!def.rare) continue;
                const bool seen = m.visitors->seen(static_cast<int>(v));
                const bool clued = pr != nullptr && pr->clues[v] != 0;
                float body = lh + lines(seen ? def.blurb : def.hint, textW, 2);
                if (!seen && clued) body += lines(def.clue, textW, 3) + lh;
                rows_.push_back({Row::Kind::Visitor, static_cast<int>(v), rowH(body)});
            }
        }
    } else if (sketchTab_ >= homeTabs) {
        const JournalPlace& place = m.places[static_cast<std::size_t>(sketchTab_ - homeTabs)];
        rows_.push_back({Row::Kind::Section, 3, lh + gap});
        for (std::size_t e = 0; e < place.entries.size(); ++e)
            rows_.push_back({Row::Kind::Entry, static_cast<int>(e),
                             rowH(lh + lines(place.entries[e].epithet, textW, 2))});
    } else if (sketchTab_ == 2) {
        for (std::size_t n = 0; n < cat.nooks.size(); ++n) {
            const NookDef& def = cat.nooks[n];
            const bool found = pr != nullptr && pr->nooks[n] != 0;
            const float body = lh + (found ? lines(def.blurb, textW, 2) + lines(def.gift, textW, 2)
                                           : lines(def.teaser, textW, 2));
            rows_.push_back({Row::Kind::Nook, static_cast<int>(n), rowH(body)});
        }
    }
    // Scroll by whole rows; the panel ends at the last row that fits.
    const float avail = bottom - sketchBody_ - pad * 0.5f;
    int last = static_cast<int>(rows_.size());
    float used = 0;
    int fit = 0;
    for (int i = static_cast<int>(rows_.size()) - 1; i >= 0; --i) {
        if (used + rows_[static_cast<std::size_t>(i)].h > avail) break;
        used += rows_[static_cast<std::size_t>(i)].h;
        ++fit;
    }
    sketchScroll_ = std::clamp(sketchScroll_, 0, std::max(0, last - fit));
    float h = 0;
    sketchShown_ = 0;
    for (int i = sketchScroll_; i < last; ++i) {
        const float rh = rows_[static_cast<std::size_t>(i)].h;
        if (h + rh > avail) break;
        h += rh;
        ++sketchShown_;
    }
    sketchMore_ = sketchScroll_ + sketchShown_ < last;
    // "Not now" buttons of the open wishes shown.
    float ry = sketchBody_;
    for (int i = sketchScroll_; i < sketchScroll_ + sketchShown_; ++i) {
        const Row& r = rows_[static_cast<std::size_t>(i)];
        if (r.kind == Row::Kind::OpenWish && r.index < 3) {
            const float nowW = font.measure(Face::Body, strings::kNotNow) + 2 * theme::kTipPad * s;
            Widget& n = add(kSketchNotNow0 + r.index,
                            {x + jw - pad - nowW, ry + rowPad, nowW, theme::kTipH * s});
            n.label = strings::kNotNow;
            n.entry.index = m.wishes[static_cast<std::size_t>(r.index)].wish;
        }
        ry += r.h;
    }
    const float minH = sketchBody_ - margin + lh * 2;
    journalBox_ = {x, margin, jw, std::max(minH, sketchBody_ - margin + h + pad * 0.5f)};
}

void Hud::drawSketchbook(Painter& p, const HudModel& m) const {
    const float a = smooth(journalT_);
    const float s = scale_;
    const Box b = journalBox_;
    const Font& f = p.font();
    const float pad = theme::kPanelPad * s;
    const float lh = f.lineHeight(Face::Body);
    const float header = theme::kJournalHeader * s;
    const SDL_FColor ink = withAlpha(theme::kInk, a);
    const SDL_FColor muted = withAlpha(theme::kInkMuted, a);
    p.text(Face::Title, strings::kSketchbook, b.x + pad,
           b.y + header * 0.5f + f.ascent(Face::Title) * theme::kBaselineCentre, ink);
    // Pages and the way to the next stage of land.
    float y = b.y + header + theme::kGap * s * 0.5f;
    p.text(Face::Body, pagesText_, b.x + pad, y + f.ascent(Face::Body), ink);
    const float barX = b.x + pad + f.measure(Face::Body, pagesText_) + theme::kCardGap * s;
    const float barW = b.x + b.w - pad - barX;
    const float bh = theme::kBarH * s;
    const Box track{barX, y + (lh - bh) * 0.5f, barW, bh};
    p.roundRect(track, bh * 0.5f, withAlpha(theme::kInset, a * 2));
    if (m.pagesTotal > 0) {
        const float done = static_cast<float>(m.pages) / static_cast<float>(m.pagesTotal);
        p.roundRect({track.x, track.y, std::max(bh, barW * std::min(1.0f, done)), bh}, bh * 0.5f,
                    withAlpha(theme::kAccent, a));
    }
    p.text(Face::Body, untilText_, b.x + pad, y + lh + f.ascent(Face::Body), muted);
    for (const Widget& w : widgets_)
        if (w.id >= kSketchTab0 && w.id < kSketchNotNow0) drawTab(p, w, a);

    const float icon = theme::kJournalIcon * s;
    const float iconPad = theme::kJournalIconPad * s;
    const float rowPad = theme::kJournalRowPad * s;
    const float gapX = theme::kJournalTextGap * s;
    const Catalog& cat = *m.cat;
    static constexpr std::string_view kSections[] = {strings::kOpenSection,
                                                     strings::kGrantedSection, strings::kRarer};
    y = sketchBody_;
    const auto disc = [&](Box box, bool lit) {
        p.roundRect(box, box.w * 0.5f, withAlpha(lit ? theme::kSilhouetteBack : theme::kInset, a));
        p.rim(box, box.w * 0.5f, theme::kRim * s, withAlpha(theme::kInsetRimTop, a),
              withAlpha(theme::kInsetRimBottom, a));
    };
    const auto art = [&](Box box, const Sprite& spr, SDL_FColor tint) {
        const Box in{box.x + iconPad, box.y + iconPad, box.w - 2 * iconPad, box.h - 2 * iconPad};
        p.thumbnail(spr, in, in.w / std::max(1.0f, std::max(spr.w, spr.h)), a, tint);
    };
    const int end = std::min(sketchScroll_ + sketchShown_, static_cast<int>(rows_.size()));
    for (int i = sketchScroll_; i < end; ++i) {
        const Row& r = rows_[static_cast<std::size_t>(i)];
        const Box ib{b.x + pad, y + rowPad, icon, icon};
        const float tx = ib.x + icon + gapX;
        const float tw = b.x + b.w - pad - tx;
        switch (r.kind) {
        case Row::Kind::Section:
            p.text(Face::Body, r.index < 3 ? kSections[r.index] : placeOpen(m).summary, b.x + pad,
                   y + f.ascent(Face::Body), withAlpha(theme::kGold, a));
            break;
        case Row::Kind::Entry: {
            const JournalEntry& e = placeOpen(m).entries[static_cast<std::size_t>(r.index)];
            disc(ib, false);
            p.icon(theme::icon::kLandmark, ib.cx(), ib.cy(),
                   withAlpha(e.found ? theme::kGold : theme::kInkMuted, a * (e.found ? 1 : 0.5f)));
            p.text(Face::Body, e.name, tx, y + rowPad + f.ascent(Face::Body),
                   e.found ? ink : muted);
            p.wrapped(Face::Body, e.epithet, tx, y + rowPad + lh, tw, 2, muted);
            break;
        }
        case Row::Kind::OpenWish: {
            if (std::cmp_greater_equal(r.index, m.wishes.size())) break;
            const WishCard& c = m.wishes[static_cast<std::size_t>(r.index)];
            disc(ib, false);
            art(ib, c.portrait, {1, 1, 1, 1});
            const float nowW = f.measure(Face::Body, strings::kNotNow) + 2 * theme::kTipPad * s;
            const float used =
                p.wrapped(Face::Body, c.text, tx, y + rowPad, tw - nowW - theme::kGap * s, 3, ink);
            if (!c.detail.empty())
                p.text(Face::Body, c.detail, tx, y + rowPad + used + f.ascent(Face::Body), muted);
            break;
        }
        case Row::Kind::GrantedWish: {
            const WishDef& w = cat.wishes[static_cast<std::size_t>(r.index)];
            disc(ib, false);
            art(ib,
                w.giver < 0 ? m.thumbs->portrait
                            : m.thumbs->visitors[static_cast<std::size_t>(w.giver)],
                {1, 1, 1, 1});
            const float used = p.wrapped(Face::Body, w.thanks, tx, y + rowPad, tw, 2, ink);
            const float ry = y + rowPad + used;
            p.icon(theme::icon::kCheck, tx + theme::kIcon * s * 0.4f, ry + lh * 0.5f,
                   withAlpha(theme::kAccent, a));
            p.wrapped(Face::Body, rewardText(cat, w.reward), tx + theme::kIcon * s, ry,
                      tw - theme::kIcon * s, 1, muted);
            break;
        }
        case Row::Kind::Visitor: {
            const VisitorDef& def = cat.visitors[static_cast<std::size_t>(r.index)];
            const bool seen = m.visitors->seen(r.index);
            const Sprite& spr = static_cast<std::size_t>(r.index) < m.thumbs->visitors.size()
                                    ? m.thumbs->visitors[static_cast<std::size_t>(r.index)]
                                    : m.thumbs->placeholder;
            disc(ib, !seen);
            // Not seen yet: the shape, as a silhouette.
            art(ib, spr, seen ? SDL_FColor{1, 1, 1, 1} : theme::kSilhouette);
            p.text(Face::Body, seen ? std::string_view(def.name) : strings::kJournalUnknown, tx,
                   y + rowPad + f.ascent(Face::Body), ink);
            const int present = m.visitors->present(r.index);
            if (present > 0) {
                const float hw = f.measure(Face::Body, strings::kHereNow);
                const float hx = b.x + b.w - pad - hw;
                p.text(Face::Body, strings::kHereNow, hx, y + rowPad + f.ascent(Face::Body),
                       withAlpha(theme::kAccent, a));
                const float dr = theme::kDotRadius * s;
                p.roundRect({hx - 3 * dr, y + rowPad + lh * 0.5f - dr, 2 * dr, 2 * dr}, dr,
                            withAlpha(theme::kAccent, a));
            }
            float ty = y + rowPad + lh;
            ty += p.wrapped(Face::Body, seen ? def.blurb : def.hint, tx, ty, tw, 2, muted);
            if (!seen && m.progress != nullptr &&
                m.progress->clues[static_cast<std::size_t>(r.index)]) {
                p.text(Face::Body, noteLabel_, tx, ty + f.ascent(Face::Body),
                       withAlpha(theme::kGold, a));
                p.wrapped(Face::Body, def.clue, tx, ty + lh, tw, 3, ink);
            }
            break;
        }
        case Row::Kind::Nook: {
            const NookDef& def = cat.nooks[static_cast<std::size_t>(r.index)];
            const bool found =
                m.progress != nullptr && m.progress->nooks[static_cast<std::size_t>(r.index)];
            disc(ib, false);
            p.icon(theme::icon::kSparkles, ib.cx(), ib.cy(),
                   withAlpha(found ? theme::kGold : theme::kInkMuted, a * (found ? 1.0f : 0.5f)));
            p.text(Face::Body, found ? std::string_view(def.name) : strings::kUnknownNook, tx,
                   y + rowPad + f.ascent(Face::Body), found ? ink : muted);
            float ty = y + rowPad + lh;
            if (found) {
                ty += p.wrapped(Face::Body, def.blurb, tx, ty, tw, 2, ink);
                p.wrapped(Face::Body, def.gift, tx, ty, tw, 2, muted);
            } else {
                p.wrapped(Face::Body, def.teaser, tx, ty, tw, 2,
                          withAlpha(theme::kInkMuted, a * 0.8f));
            }
            break;
        }
        }
        y += r.h;
    }
    if (sketchMore_ || sketchScroll_ > 0) {
        const float cx = b.x + b.w * 0.5f;
        if (sketchMore_) p.icon(theme::icon::kChevronDown, cx, b.y + b.h - pad * 0.45f, muted);
    }
}

std::string_view Hud::rewardText(const Catalog& cat, const Reward& r) const {
    rewardText_.clear();
    const auto add = [&](std::string_view name) {
        if (!rewardText_.empty()) rewardText_ += ", ";
        rewardText_ += name;
    };
    for (const int t : r.terrain) add(cat.terrain[static_cast<std::size_t>(t)].name);
    for (const int i : r.items) add(cat.items[static_cast<std::size_t>(i)].name);
    if (r.frame >= 0) add(cat.frames[static_cast<std::size_t>(r.frame)].name);
    if (r.clue >= 0) add(noteLabel_);
    return rewardText_;
}

void Hud::drawHint(Painter& p, const HudModel& m) const {
    const float a = smooth(hintT_);
    if (a <= 0) return;
    const Font& f = p.font();
    const Box b = hintBox_;
    const float base = b.cy() + f.ascent(Face::Body) * theme::kBaselineCentre;
    float x = b.x + theme::kHintPad * scale_;
    p.text(Face::Body, hintText_, x, base, withAlpha(theme::kInk, a));
    x += f.measure(Face::Body, hintText_);
    if (!m.warning.empty()) {
        if (!hintText_.empty()) {
            p.text(Face::Body, strings::kSeparator, x, base, withAlpha(theme::kInkMuted, a));
            x += f.measure(Face::Body, strings::kSeparator);
        }
        p.text(Face::Body, m.warning, x, base, withAlpha(theme::kWarn, a));
    }
}

void Hud::drawToast(Painter& p) const {
    const float a = smooth(toastT_);
    if (a <= 0 || toast_.empty()) return;
    const float s = scale_;
    const Font& f = p.font();
    const float pad = theme::kToastPad * s;
    const float iconW = theme::kIcon * s;
    const Box b = toastBox_;
    p.icon(theme::icon::kSparkle, b.x + pad + iconW * 0.5f, b.cy(), withAlpha(theme::kAccent, a));
    const float x = b.x + pad + iconW + theme::kToastIconGap * s;
    if (toastLines_ <= 1) {
        p.text(Face::Body, toast_, x, b.cy() + f.ascent(Face::Body) * theme::kBaselineCentre,
               withAlpha(theme::kInk, a));
        return;
    }
    const float lh = f.lineHeight(Face::Body);
    p.wrapped(Face::Body, toast_, x, b.cy() - lh * static_cast<float>(toastLines_) * 0.5f,
              b.x + b.w - pad - x, toastLines_, withAlpha(theme::kInk, a));
}

void Hud::drawTray(Painter& p) const {
    const float a = smooth(trayT_);
    if (a <= 0 || trayBox_.w <= 0) return;
    const float s = scale_;
    const Font& f = p.font();
    const float pad = theme::kCardPad * s;
    const float portrait = theme::kPortrait * s;
    const Box hb{trayBox_.x, trayBox_.y, trayBox_.w, theme::kTrayHeader * s};
    const float base = hb.cy() + f.ascent(Face::Body) * theme::kBaselineCentre;
    p.icon(theme::icon::kSparkles, hb.x + pad + theme::kIcon * s * 0.5f, hb.cy(),
           withAlpha(theme::kGold, a));
    p.text(Face::Title, strings::kWishes, hb.x + pad + theme::kIcon * s + theme::kCardGap * s,
           hb.cy() + f.ascent(Face::Title) * theme::kBaselineCentre, withAlpha(theme::kInk, a));
    p.text(Face::Body, trayCount_, hb.x + hb.w - pad - f.measure(Face::Body, trayCount_), base,
           withAlpha(theme::kInkMuted, a));
    const float hh = hoverOf(kTrayHeader);
    if (hh > 0) p.roundRect(hb, theme::kPanelRadius * s, withAlpha(theme::kHover, a * hh * 0.5f));
    if (trayCollapsed_) return;
    const float lh = f.lineHeight(Face::Body);
    for (std::size_t i = 0; i < tray_.size(); ++i) {
        const TrayCard& t = tray_[i];
        if (t.box.h <= 1) continue;
        const float in = smooth(t.in);
        const float ca = a * in * (1.0f - smooth(t.out));
        const float dx = (1.0f - in) * theme::kCardSlide * s;
        const float dy = -smooth(t.out) * theme::kCardSlide * s * 0.5f;
        const Box b{t.box.x + dx, t.box.y + dy, t.box.w, t.box.h};
        p.roundRect({b.x + pad, b.y, b.w - 2 * pad, theme::kRim * s}, 0,
                    withAlpha(theme::kDivider, ca), 0);
        const int id = kCard0 + static_cast<int>(i);
        const float hov = hoverOf(id);
        const float r = theme::kTileRadius * s;
        const Box inner{b.x + pad * 0.4f, b.y + pad * 0.3f, b.w - pad * 0.8f, b.h - pad * 0.6f};
        if (hov > 0) p.roundRect(inner, r, withAlpha(theme::kHover, ca * hov));
        if (t.card.ready || t.out > 0)
            p.rim(inner, r, 2 * theme::kRim * s, withAlpha(theme::kGold, ca),
                  withAlpha(theme::kGold, ca * 0.5f));
        const Box pic{b.x + pad, b.y + pad, portrait, portrait};
        p.roundRect(pic, portrait * 0.5f, withAlpha(theme::kInset, ca));
        if (t.card.portrait.texture != nullptr)
            p.thumbnail(t.card.portrait, pic, pic.w / std::max(1.0f, t.card.portrait.w), ca);
        else
            p.icon(theme::icon::kSparkles, pic.cx(), pic.cy(), withAlpha(theme::kGold, ca));
        const float tx = pic.x + portrait + theme::kCardGap * s;
        const float tw = b.x + b.w - pad - tx;
        p.wrapped(Face::Body, t.card.text, tx, b.y + pad, tw, 2, withAlpha(theme::kInk, ca));
        if (t.card.detail.empty()) continue;
        float dyy = b.y + pad + t.lines * lh + theme::kBarGap * s;
        float dx2 = tx;
        if (t.card.progress >= 0) {
            const float bw = theme::kBarW * s;
            const float bh = theme::kBarH * s;
            const Box track{tx, dyy + (lh - bh) * 0.5f, bw, bh};
            p.roundRect(track, bh * 0.5f, withAlpha(theme::kInset, ca * 2));
            p.roundRect({track.x, track.y, std::max(bh, bw * std::min(1.0f, t.card.progress)), bh},
                        bh * 0.5f, withAlpha(theme::kAccent, ca));
            dx2 += bw + theme::kCardGap * s;
        }
        p.text(Face::Body, t.card.detail, dx2, dyy + f.ascent(Face::Body),
               withAlpha(theme::kInkMuted, ca));
    }
    if (menuBox_.w > 0) {
        p.glass(menuBox_, theme::kTipRadius * scale_, a, theme::kGlassTip);
        p.endGlass();
        const float mh = hoverOf(kNotNow);
        if (mh > 0) p.roundRect(menuBox_, theme::kTipRadius * scale_, withAlpha(theme::kHover, mh));
        p.text(Face::Body, strings::kNotNow, menuBox_.x + theme::kTipPad * s,
               menuBox_.cy() + f.ascent(Face::Body) * theme::kBaselineCentre,
               withAlpha(theme::kInk, a));
    }
}

void Hud::drawCard(Painter& p, const HudModel& m) const {
    const float a = smooth(cardT_);
    if (a <= 0 || cardBox_.w <= 0) return;
    const float s = scale_;
    const Font& f = p.font();
    const Box b = cardBox_;
    const float pad = theme::kPanelPad * s;
    p.glass(b, theme::kPanelRadius * s, a, theme::kGlass);
    p.endGlass();
    float y = b.y + pad;
    p.text(Face::Title, m.cardTitle, b.x + pad, y + f.ascent(Face::Title),
           withAlpha(theme::kInk, a));
    y += f.lineHeight(Face::Title);
    for (const std::string_view line : {m.cardNative, m.cardEpithet}) {
        if (line.empty()) continue;
        p.text(Face::Body, line, b.x + pad, y + f.ascent(Face::Body),
               withAlpha(theme::kInkMuted, a));
        y += f.lineHeight(Face::Body);
    }
    y += theme::kGap * s;
    p.wrapped(Face::Body, m.cardText, b.x + pad, y, b.w - 2 * pad, theme::kCardLines,
              withAlpha(theme::kInk, a));
    for (const Widget& w : widgets_)
        if (w.id == kCardClose) drawButton(p, w, a);
    p.endLayer();
}

void Hud::drawCaption(Painter& p, const HudModel& m) const {
    // Quiet: no panel, a soft shadow under light type, centred at the top.
    if (m.captionAlpha <= 0 || m.caption.empty()) return;
    const float a = m.captionAlpha;
    const float s = scale_;
    const Font& f = p.font();
    const float top = theme::kCaptionTop * s;
    const float w1 = f.measure(Face::Title, m.caption);
    const float x1 = std::round((screen_.x - w1) * 0.5f);
    const float base1 = top + f.ascent(Face::Title);
    const float sh = std::max(1.0f, std::round(s));
    p.text(Face::Title, m.caption, x1 + sh, base1 + sh, withAlpha(theme::kCaptionShadow, a * 0.6f));
    p.text(Face::Title, m.caption, x1, base1, withAlpha(theme::kCaptionInk, a));
    if (m.captionSub.empty()) return;
    const float w2 = f.measure(Face::Body, m.captionSub);
    const float x2 = std::round((screen_.x - w2) * 0.5f);
    const float base2 = top + f.lineHeight(Face::Title) + f.ascent(Face::Body);
    p.text(Face::Body, m.captionSub, x2 + sh, base2 + sh,
           withAlpha(theme::kCaptionShadow, a * 0.6f));
    p.text(Face::Body, m.captionSub, x2, base2, withAlpha(theme::kCaptionInk, a * 0.85f));
}

void Hud::drawRibbon(Painter& p) const {
    const float a = smooth(ribbonT_);
    if (a <= 0) return;
    const float s = scale_;
    const Font& f = p.font();
    const Box b = ribbonBox_;
    const float pad = theme::kToastPad * s;
    p.glass(b, theme::kPanelRadius * s, a, theme::kGlass);
    p.endGlass();
    float y = b.y + pad;
    p.icon(theme::icon::kSparkles, b.x + pad + theme::kIcon * s * 0.5f,
           y + f.lineHeight(Face::Title) * 0.5f, withAlpha(theme::kGold, a));
    p.text(Face::Title, ribbon_.title, b.x + pad + theme::kIcon * s + theme::kToastIconGap * s,
           y + f.ascent(Face::Title), withAlpha(theme::kInk, a));
    y += f.lineHeight(Face::Title) + theme::kGap * s * 0.5f;
    const float icon = theme::kRibbonIcon * s;
    float x = b.x + pad;
    const float lineH = std::max(icon, f.lineHeight(Face::Body));
    p.text(Face::Body, ribbon_.text, x,
           y + (lineH - f.lineHeight(Face::Body)) * 0.5f + f.ascent(Face::Body),
           withAlpha(theme::kInk, a));
    x += f.measure(Face::Body, ribbon_.text) + theme::kGap * s;
    for (int i = 0; i < ribbon_.iconCount; ++i) {
        const Sprite& sp = ribbon_.icons[static_cast<std::size_t>(i)];
        p.thumbnail(sp, {x, y, icon, icon}, icon / std::max(sp.w, sp.h * 0.75f), a);
        x += icon + theme::kGap * s * 0.5f;
    }
    if (!ribbon_.quote.empty()) {
        y += lineH + theme::kGap * s * 0.5f;
        p.wrapped(Face::Body, ribbon_.quote, b.x + pad, y, b.w - 2 * pad, 2,
                  withAlpha(theme::kInkMuted, a));
    }
    p.endLayer();
}

void Hud::layoutCalendar(const HudModel& m, const Font& font, float s) {
    calendarBox_ = {};
    if (calendarT_ <= 0.0f || m.cat->seasons.empty()) return;
    const float pad = theme::kPanelPad * s;
    const float lh = font.lineHeight(Face::Body);
    const float row = theme::kTipH * s;
    const auto& seasons = m.cat->seasons;
    const SeasonDef& now = seasons[static_cast<std::size_t>(m.season)];
    const int day = m.seasonDay + 1;
    calendarLine_ =
        std::vformat(strings::kCalendarDay, std::make_format_args(now.name, day, now.days));
    const auto lower = [](std::string s0) {
        if (!s0.empty()) s0[0] = static_cast<char>(std::tolower(static_cast<unsigned char>(s0[0])));
        return s0;
    };
    pinLabels_[0] = strings::kFollowDays;
    float w = font.measure(Face::Title, calendarLine_);
    for (std::size_t i = 0; i < seasons.size() && i + 1 < pinLabels_.size(); ++i) {
        const std::string name = lower(seasons[i].name);
        pinLabels_[i + 1] = std::vformat(strings::kAlwaysSeason, std::make_format_args(name));
    }
    const std::size_t pins = std::min(seasons.size() + 1, pinLabels_.size());
    for (std::size_t i = 0; i < pins; ++i)
        w = std::max(w, font.measure(Face::Body, pinLabels_[i]) + theme::kIcon * s * 2);
    float chips = 0;
    for (const auto& sd : seasons)
        chips += font.measure(Face::Body, sd.name) + theme::kIcon * s + 3 * theme::kGap * s;
    w = std::max(w, chips) + 2 * pad;
    const float slide = (1.0f - smooth(calendarT_)) * slideBy(s) * 0.5f;
    const float x = titleBox_.x;
    float y = titleBox_.y + titleBox_.h + theme::kGap * s - slide;
    const float top = y;
    y += pad + font.lineHeight(Face::Title) + theme::kGap * s; // the date
    y += row + theme::kGap * s;                                // the season chips
    y += lh + theme::kGap * s * 0.5f;                          // "Seasons"
    for (std::size_t i = 0; i < pins; ++i) {
        Widget& r = add(kCalPin0 + static_cast<int>(i), {x + pad * 0.5f, y, w - pad, row});
        r.label = pinLabels_[i];
        r.selected = static_cast<int>(i) - 1 == m.seasonPin;
        y += row;
    }
    calendarBox_ = {x, top, w, y + pad * 0.5f - top};
}

void Hud::drawCalendar(Painter& p, const HudModel& m) const {
    const float a = smooth(calendarT_);
    if (a <= 0 || calendarBox_.w <= 0) return;
    const float s = scale_;
    const Font& f = p.font();
    const float pad = theme::kPanelPad * s;
    const Box b = calendarBox_;
    p.glass(b, theme::kPanelRadius * s, a, theme::kGlass);
    p.endGlass();
    float y = b.y + pad;
    p.text(Face::Title, calendarLine_, b.x + pad, y + f.ascent(Face::Title),
           withAlpha(theme::kInk, a));
    y += f.lineHeight(Face::Title) + theme::kGap * s;
    // The year's seasons, the current one lit.
    static constexpr char32_t kIcons[] = {theme::icon::kFlower, theme::icon::kSun,
                                          theme::icon::kLeaf, theme::icon::kSnowflake};
    const float row = theme::kTipH * s;
    float x = b.x + pad;
    for (std::size_t i = 0; i < m.cat->seasons.size(); ++i) {
        const auto& name = m.cat->seasons[i].name;
        const float cw = f.measure(Face::Body, name) + theme::kIcon * s + 2 * theme::kGap * s;
        const Box chip{x, y, cw, row};
        const bool lit = static_cast<int>(i) == m.season;
        if (lit) {
            p.roundRect(chip, row * 0.5f, withAlpha(theme::kAccentWash, a));
            p.rim(chip, row * 0.5f, theme::kRim * s, withAlpha(theme::kAccentRim, a),
                  withAlpha(theme::kAccentRim, a * 0.5f));
        }
        const SDL_FColor ink = withAlpha(lit ? theme::kInk : theme::kInkMuted, a);
        p.icon(kIcons[i % std::size(kIcons)], chip.x + theme::kGap * s + theme::kIcon * s * 0.4f,
               chip.cy(), ink);
        p.text(Face::Body, name, chip.x + theme::kGap * s + theme::kIcon * s,
               chip.cy() + f.ascent(Face::Body) * theme::kBaselineCentre, ink);
        x += cw + theme::kGap * s;
    }
    y += row + theme::kGap * s;
    p.text(Face::Body, strings::kSeasons, b.x + pad, y + f.ascent(Face::Body),
           withAlpha(theme::kGold, a));
    for (const Widget& w : widgets_) {
        if (w.id < kCalPin0 || w.id > kCalPin0 + 8) continue;
        const float h = hoverOf(w.id);
        if (h > 0) p.roundRect(w.box, w.box.h * 0.5f, withAlpha(theme::kHover, a * h));
        // A radio: a ring, filled when chosen.
        const float r = theme::kDotRadius * s * 1.6f;
        const float cx = w.box.x + pad * 0.5f + r;
        const Box ring{cx - r, w.box.cy() - r, 2 * r, 2 * r};
        p.rim(ring, r, theme::kRim * s * 1.5f, withAlpha(theme::kInk, a * 0.8f),
              withAlpha(theme::kInk, a * 0.6f));
        if (w.selected) {
            const float d = r * 0.5f;
            p.roundRect({cx - d, w.box.cy() - d, 2 * d, 2 * d}, d, withAlpha(theme::kAccent, a));
        }
        p.text(Face::Body, w.label, cx + r + theme::kGap * s,
               w.box.cy() + f.ascent(Face::Body) * theme::kBaselineCentre,
               withAlpha(w.selected ? theme::kInk : theme::kInkMuted, a));
    }
    p.endLayer();
}

void Hud::drawWorldTip(Painter& p, const HudModel& m) const {
    const float a = smooth(worldTipT_);
    if (a <= 0 || m.worldTip.empty()) return;
    const float s = scale_;
    const Font& f = p.font();
    const float pad = theme::kTipPad * s;
    const float bw = f.measure(Face::Body, m.worldTip) + 2 * pad;
    const float bh = theme::kTipH * s;
    const float x = std::clamp(pointer_.x + theme::kWorldTipOffset * s, theme::kMargin * s * 0.5f,
                               screen_.x - bw - theme::kMargin * s * 0.5f);
    float y = pointer_.y + theme::kWorldTipOffset * s;
    if (y + bh > screen_.y - theme::kMargin * s) y = pointer_.y - bh - theme::kWorldTipOffset * s;
    const Box b{x, y, bw, bh};
    p.glass(b, theme::kTipRadius * s, a, theme::kGlassTip);
    p.endGlass();
    p.text(Face::Body, m.worldTip, b.x + pad,
           b.cy() + f.ascent(Face::Body) * theme::kBaselineCentre, withAlpha(theme::kInk, a));
}

void Hud::drawLabels(Painter& p, const HudModel& m) const {
    if (m.labels.empty()) return;
    const float s = scale_;
    const Font& f = p.font();
    const float pad = theme::kToastPad * s;
    for (const FloatLabel& l : m.labels) {
        const float w =
            theme::kIcon * s + theme::kToastIconGap * s + f.measure(Face::Title, l.text) + 2 * pad;
        const float h = theme::kToastH * s;
        const Box b{std::round(l.at.x - w * 0.5f), std::round(l.at.y - h), w, h};
        p.glass(b, h * 0.5f, l.alpha, theme::kGlass);
        p.endGlass();
        p.icon(theme::icon::kSparkles, b.x + pad + theme::kIcon * s * 0.5f, b.cy(),
               withAlpha(theme::kGold, l.alpha));
        p.text(Face::Title, l.text, b.x + pad + theme::kIcon * s + theme::kToastIconGap * s,
               b.cy() + f.ascent(Face::Title) * theme::kBaselineCentre,
               withAlpha(theme::kInk, l.alpha));
    }
}

void Hud::drawBubble(Painter& p, const HudModel& m) const {
    if (m.bubble.empty() || m.bubbleAlpha <= 0) return;
    const float s = scale_;
    const Font& f = p.font();
    const float pad = theme::kBubblePad * s;
    const float maxW = theme::kBubbleMaxW * s;
    const float textW = std::min(f.measure(Face::Body, m.bubble), maxW);
    const int lines = wrapLines(f, Face::Body, m.bubble, textW + 1, 2);
    const float lh = f.lineHeight(Face::Body);
    const float w = textW + 2 * pad;
    const float h = static_cast<float>(lines) * lh + 2 * pad * 0.75f;
    const float dot = theme::kBubbleDot * s;
    // Above her head, kept on screen; a small trail of dots points down to her.
    const float x = std::clamp(std::round(m.bubbleAt.x - w * 0.5f), theme::kMargin * s * 0.5f,
                               screen_.x - w - theme::kMargin * s * 0.5f);
    const float y = std::max(theme::kMargin * s * 0.5f,
                             std::round(m.bubbleAt.y - theme::kBubbleLift * s - h - 1.6f * dot));
    const Box b{x, y, w, h};
    const float a = m.bubbleAlpha;
    p.glass(b, theme::kBubbleRadius * s, a, theme::kGlassTip);
    p.endGlass();
    const float cx = std::clamp(m.bubbleAt.x, b.x + dot, b.x + b.w - dot);
    p.roundRect({cx - dot * 0.5f, b.y + b.h + dot * 0.25f, dot, dot}, dot * 0.5f,
                withAlpha(theme::kBubbleTrail, a));
    p.roundRect({cx - dot * 0.3f, b.y + b.h + dot * 1.15f, dot * 0.6f, dot * 0.6f}, dot * 0.3f,
                withAlpha(theme::kBubbleTrail, a));
    p.wrapped(Face::Body, m.bubble, b.x + pad, b.y + pad * 0.75f, textW + 1, 2,
              withAlpha(theme::kInk, a));
}

float Hud::bottomPanelsTop() const {
    float top = bottomTop_;
    if (drawerT_ > 0.0f && drawerBox_.w > 0) top = std::min(top, drawerBox_.y);
    if (hintT_ > 0.0f && hintBox_.w > 0) top = std::min(top, hintBox_.y);
    return top - theme::kGap * scale_;
}

void Hud::drawPulse(Painter& p, const HudModel& m) const {
    // A soft ring breathing around the widgets the tour points at.
    const float k = 0.5f + 0.5f * std::sin(pulseT_ * theme::kPulseSpeed);
    for (const std::string& name : pulse_) {
        if (name.empty()) continue;
        Box b;
        if (name == "tray") {
            if (trayT_ <= 0.5f || trayBox_.w <= 0) continue;
            b = trayBox_;
        } else if (const Widget* w = find(name, m); w != nullptr) {
            b = w->box;
        } else {
            continue;
        }
        const float g = theme::kPulseGrow * scale_ * k;
        const Box ring{b.x - g, b.y - g, b.w + 2 * g, b.h + 2 * g};
        const float r = std::min(ring.w, ring.h) * 0.5f;
        p.rim(ring, std::min(r, theme::kPanelRadius * scale_ + g), 2 * theme::kRim * scale_,
              withAlpha(theme::kAccent, 0.5f + 0.5f * k),
              withAlpha(theme::kAccent, 0.3f + 0.4f * k));
    }
}

void Hud::drawTooltip(Painter& p) const {
    const float a = smooth(tooltipT_);
    if (a <= 0) return;
    const Widget* w = nullptr;
    for (const Widget& c : widgets_)
        if (c.id == tooltipId_) w = &c;
    if (w == nullptr || w->tooltip.empty()) return;
    const float s = scale_;
    const Font& f = p.font();
    const float pad = theme::kTipPad * s;
    const float chipPad = theme::kChipPad * s;
    const float tw = f.measure(Face::Body, w->tooltip);
    const float kw = w->shortcut.empty() ? 0.0f : f.measure(Face::Body, w->shortcut) + 2 * chipPad;
    const float bw = tw + (kw > 0 ? kw + theme::kChipGap * s : 0) + 2 * pad;
    const float bh = theme::kTipH * s;
    const bool above = w->box.y > screen_.y * 0.5f;
    float x = std::round(w->box.cx() - bw * 0.5f);
    x = std::clamp(x, theme::kMargin * s * 0.5f, screen_.x - bw - theme::kMargin * s * 0.5f);
    const float gap = theme::kTipGap * s;
    const float slide = (1 - a) * theme::kTipSlide * s;
    float y = above ? w->box.y - bh - gap + slide : w->box.y + w->box.h + gap - slide;
    // Above the docks, keep clear of a visible hint line rather than covering it.
    const Box& h = hintBox_;
    if (above && hintT_ > 0 && x < h.x + h.w && x + bw > h.x && y < h.y + h.h && y + bh > h.y)
        y = h.y - bh - theme::kGap * s;
    const Box b{x, y, bw, bh};
    p.glass(b, theme::kTipRadius * s, a, theme::kGlassTip);
    p.endGlass();
    const float base = b.cy() + f.ascent(Face::Body) * theme::kBaselineCentre;
    p.text(Face::Body, w->tooltip, b.x + pad, base, withAlpha(theme::kInk, a));
    if (kw > 0) {
        const Box chip{b.x + pad + tw + theme::kChipGap * s, b.y + chipPad, kw, bh - 2 * chipPad};
        const float cr = theme::kChipRadius * s;
        p.roundRect(chip, cr, withAlpha(theme::kChip, a));
        p.rim(chip, cr, theme::kRim * s, withAlpha(theme::kInsetRimTop, a),
              withAlpha(theme::kInsetRimBottom, a));
        p.text(Face::Body, w->shortcut, chip.x + chipPad, base, withAlpha(theme::kInkMuted, a));
    }
}

bool Hud::reveal(std::string_view name, const HudModel& m) {
    if (!name.starts_with("tile:") || !m.drawerOpen) return false;
    const std::string_view id = name.substr(5);
    categoryEntries(*m.cat, m.category, entries_, m.progress);
    const auto it = std::ranges::find_if(entries_, [&](const DrawerEntry& e) {
        if (e.locked) return id == "locked";
        const auto i = static_cast<std::size_t>(e.index);
        return (e.terrain ? m.cat->terrain[i].id : m.cat->items[i].id) == id;
    });
    if (it == entries_.end() || scroll_.size() != m.cat->categories.size()) return false;
    const float avail = screen_.x - 2 * theme::kMargin * scale_ - 2 * theme::kPanelPad * scale_;
    const float tileW = theme::kTileW * scale_;
    const float gap = theme::kGap * scale_;
    const int cols =
        std::clamp(static_cast<int>((avail + gap) / (tileW + gap)), 1, theme::kDrawerMaxCols);
    scroll_[static_cast<std::size_t>(m.category)] = static_cast<int>(it - entries_.begin()) / cols;
    return true;
}

void Hud::draw(Painter& p, const HudModel& m) const {
    // The era caption lies under every panel.
    if (!m.photo) drawCaption(p, m);
    if (!m.photo) {
        const float radius = theme::kPanelRadius * scale_;
        // Title, docks and journal never overlap, so they share one layer.
        const float ja = smooth(journalT_);
        p.glass(titleBox_, radius, 1, theme::kGlass);
        for (const Panel& pn : panels_) p.glass(pn.box, pn.radius, 1, theme::kGlass);
        if (journalT_ > 0) p.glass(journalBox_, radius, ja, theme::kGlass);
        p.endGlass();
        drawTitle(p, m);
        for (const Box& d : dividers_) p.roundRect(d, 0, theme::kDivider, 0);
        for (const Widget& w : widgets_) {
            if (w.id >= kTab0 || w.id == kScrollUp || w.id == kScrollDown) continue;
            if (w.id >= kTrayHeader && w.id <= kNotNow) continue;     // the tray draws its own
            if (w.id >= kTitleCard && w.id <= kCalPin0 + 8) continue; // title and calendar
            if (w.id == kJournalClose) {
                if (journalT_ > 0) drawButton(p, w, ja);
                continue;
            }
            if (w.id >= kSketchTab0 && w.id < kSketchNotNow0) continue; // drawn with the book
            if (w.id >= kSketchNotNow0 && w.id < kSketchNotNow0 + 3) {
                drawPill(p, w, ja);
                continue;
            }
            drawButton(p, w, 1.0f);
        }
        if (journalT_ > 0) drawSketchbook(p, m);
        p.endLayer();

        // The wish tray is its own layer: it fades out as the journal fades in at its place.
        if (trayT_ > 0 && trayBox_.w > 0) {
            p.glass(trayBox_, radius, smooth(trayT_), theme::kGlass);
            p.endGlass();
            drawTray(p);
            p.endLayer();
        }

        // The drawer is its own layer: the journal and docks keep clear of it.
        if (drawerT_ > 0) {
            const float a = smooth(drawerT_);
            p.glass(drawerBox_, radius, a, theme::kGlass);
            p.endGlass();
            for (const Widget& w : widgets_) {
                if (w.id >= kTile0)
                    drawTile(p, w, m, a);
                else if (w.id >= kTab0)
                    drawTab(p, w, a);
                else if (w.id == kScrollUp || w.id == kScrollDown)
                    drawButton(p, w, a);
            }
            p.endLayer();
        }
    }
    const float ha = smooth(hintT_);
    const float ta = toast_.empty() ? 0.0f : smooth(toastT_);
    if (ha > 0 || ta > 0) {
        p.glass(hintBox_, hintBox_.h * 0.5f, ha, theme::kGlass);
        p.glass(toastBox_, std::min(toastBox_.h, theme::kToastH * scale_) * 0.5f, ta,
                theme::kGlass);
        p.endGlass();
        drawHint(p, m);
        drawToast(p);
    }
    if (!m.photo) drawPulse(p, m);
    if (!m.photo) {
        drawCalendar(p, m);
        drawLabels(p, m);
        drawBubble(p, m);
        drawCard(p, m);
        drawRibbon(p);
        drawWorldTip(p, m);
        drawTooltip(p);
    }
    if (flash_ > 0)
        p.roundRect({0, 0, screen_.x, screen_.y}, 0,
                    withAlpha(theme::kFlash, flash_ * flash_ * 0.8f), 0);
}

} // namespace lc
