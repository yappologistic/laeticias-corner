#include "ui/hud.hpp"

#include "ui/strings.hpp"
#include "ui/theme.hpp"

#include <algorithm>
#include <cmath>
#include <format>
#include <utility>

namespace lc {
namespace {

enum Wid : int {
    kNone = 0,
    kBuild,
    kRemove,
    kSound,
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
    kTab0 = 16,
    kTile0 = 32,
};

struct Named {
    std::string_view name;
    int id;
};
constexpr Named kNames[] = {
    {"build", kBuild},
    {"remove", kRemove},
    {"sound", kSound},
    {"photo", kPhoto},
    {"clock", kClock},
    {"rain", kRain},
    {"journal", kJournal},
    {"undo", kUndo},
    {"redo", kRedo},
    {"recentre", kRecentre},
    {"zoom_out", kZoomOut},
    {"zoom_in", kZoomIn},
    {"journal_close", kJournalClose},
    {"scroll_up", kScrollUp},
    {"scroll_down", kScrollDown},
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
}

void Hud::categoryEntries(const Catalog& cat, int category, std::vector<DrawerEntry>& out) {
    out.clear();
    if (isGroundCategory(cat, category)) {
        for (std::size_t t = 0; t < cat.terrain.size(); ++t)
            out.push_back({.terrain = true, .index = static_cast<int>(t)});
    } else {
        for (std::size_t i = 0; i < cat.items.size(); ++i)
            if (cat.items[i].category == category)
                out.push_back({.terrain = false, .index = static_cast<int>(i)});
    }
}

int Hud::tileId(const Catalog& cat, DrawerEntry e) {
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
    toast_ = std::move(text);
    toastTime_ = theme::kToastSeconds;
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
    const float leftW = buildW + gap + dockH;
    const float divider = gap * 2;
    const float rightW = 5 * btn + 2 * divider + 2 * pad;
    const float centreW = 5 * btn + 2 * pad;
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

    {
        Widget& w = add(kBuild, {margin, leftY, buildW, dockH});
        w.icon = theme::icon::kPlus;
        w.label = strings::kBuild;
        w.tooltip = strings::kBuild;
        w.shortcut = strings::kKeyBuild;
        w.selected = m.drawerOpen || m.tool == Tool::Place || m.tool == Tool::Paint;
        panels_.push_back({w.box, dockH * 0.5f});
        Widget& r = add(kRemove, {margin + buildW + gap, leftY, dockH, dockH});
        r.icon = theme::icon::kEraser;
        r.tooltip = strings::kRemove;
        r.shortcut = strings::kKeyRemove;
        r.selected = m.tool == Tool::Remove;
        panels_.push_back({r.box, dockH * 0.5f});
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
        button(kSound, m.muted ? theme::icon::kSoundOff : theme::icon::kSoundOn,
               m.muted ? strings::kSoundOff : strings::kSoundOn, strings::kKeySound, false);
        button(kPhoto, theme::icon::kCamera, strings::kPhoto, strings::kKeyPhoto, false);
        button(kClock, pinIcon(m.pin), pinTooltip(m.pin), strings::kKeyClock,
               m.pin != ClockPin::Auto);
        button(kRain, theme::icon::kRain, m.rain ? strings::kRainOn : strings::kRainOff,
               strings::kKeyRain, m.rain);
        button(kJournal, theme::icon::kJournal, strings::kJournal, strings::kKeyJournal,
               m.journalOpen);
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
        const float w1 = font.measure(Face::Title, strings::kTitle);
        const float w2 =
            theme::kIcon * s + theme::kTitleIconGap * s + font.measure(Face::Body, clockLabel_);
        titleBox_ = {margin, margin, std::max(w1, w2) + 2 * tpad,
                     2 * tpad + font.lineHeight(Face::Title) + font.lineHeight(Face::Body)};
    }

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
        categoryEntries(*m.cat, m.category, entries_);
        const int total = static_cast<int>(entries_.size());
        const int rowsTotal = (total + cols - 1) / cols;
        const int rows = std::clamp(rowsTotal, 1, theme::kDrawerRows);
        if (scroll_.size() != m.cat->categories.size()) scroll_.assign(m.cat->categories.size(), 0);
        int& scroll = scroll_[static_cast<std::size_t>(m.category)];
        scroll = std::clamp(scroll, 0, std::max(0, rowsTotal - rows));
        scrollable_ = rowsTotal > rows;
        canScrollUp_ = scroll > 0;
        canScrollDown_ = scroll < rowsTotal - rows;

        const float w =
            2 * ppad + static_cast<float>(cols) * tileW + static_cast<float>(cols - 1) * gap;
        const float h = 2 * ppad + theme::kTabH * s + gap + static_cast<float>(rows) * tileH +
                        static_cast<float>(rows - 1) * gap;
        const float slide = (1.0f - smooth(drawerT_)) * theme::kSlide * s;
        drawerBox_ = {margin, bottomTop_ - gap - h + slide, w, h};

        float tx = drawerBox_.x + ppad;
        const float ty = drawerBox_.y + ppad;
        for (std::size_t c = 0; c < m.cat->categories.size(); ++c) {
            const float tabW =
                font.measure(Face::Body, m.cat->categories[c].name) + theme::kTabExtra * s;
            Widget& t = add(kTab0 + static_cast<int>(c), {tx, ty, tabW, theme::kTabH * s});
            t.label = m.cat->categories[c].name;
            t.selected = static_cast<int>(c) == m.category;
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
            const auto idx = static_cast<std::size_t>(t.entry.index);
            t.label = t.entry.terrain ? std::string_view(m.cat->terrain[idx].name)
                                      : std::string_view(m.cat->items[idx].name);
            t.selected = (t.entry.terrain ? m.tool == Tool::Paint : m.tool == Tool::Place) &&
                         m.selection == t.entry.index;
        }
    }

    // Journal panel, top-right, never reaching under the drawer or the docks.
    journalBox_ = {};
    if (journalT_ > 0.0f) {
        const float jw = std::min(theme::kJournalW * s, screen.x - 2 * margin);
        const float header = theme::kJournalHeader * s;
        const float h = header +
                        static_cast<float>(m.cat->visitors.size()) * theme::kJournalRow * s +
                        theme::kPanelPad * s * 0.5f;
        const float slide = (1.0f - smooth(journalT_)) * theme::kSlide * s;
        const float x = screen.x - margin - jw + slide;
        float bottom = bottomTop_ - gap;
        if (drawerT_ > 0.0f && x < drawerBox_.x + drawerBox_.w) bottom = drawerBox_.y - gap;
        journalBox_ = {x, margin, jw, std::max(header, std::min(h, bottom - margin))};
        const float cs = theme::kCloseSize * s;
        const float ci = theme::kCloseInset * s;
        Widget& c = add(kJournalClose, {journalBox_.x + jw - ci - cs, journalBox_.y + ci, cs, cs});
        c.icon = theme::icon::kClose;
        c.tooltip = strings::kClose;
        c.shortcut = strings::kKeyJournal;
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
        const float bottom = drawerT_ > 0.0f ? drawerBox_.y : bottomTop_;
        hintBox_ = {std::round((screen.x - w) * 0.5f),
                    bottom - gap - hintH + (1 - a) * theme::kHintSlide * s, w, hintH};
    }
    // The toast sits in the free band between the title and the journal, or below the title
    // when that band is too narrow.
    {
        const float tpad = theme::kToastPad * s;
        const float w = std::min(theme::kIcon * s + theme::kToastIconGap * s +
                                     font.measure(Face::Body, toast_) + 2 * tpad,
                                 screen.x - 2 * margin);
        const float h = theme::kToastH * s;
        const float left = titleBox_.x + titleBox_.w + gap;
        const float right = journalT_ > 0.0f ? journalBox_.x - gap : screen.x - margin;
        float x = std::round((screen.x - w) * 0.5f);
        float y = margin;
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
        tileId(*m.cat, {.terrain = true, .index = static_cast<int>(m.cat->terrain.size())}));
    if (hover_.size() != ids) {
        hover_.assign(ids, 0.0f);
        press_.assign(ids, 0.0f);
    }
    screen_ = screen;
    drawerT_ = approach(drawerT_, m.drawerOpen && !m.photo, dt);
    journalT_ = approach(journalT_, m.journalOpen && !m.photo, dt);
    // In photo mode only the hint line stays (it says how to take the photo and get back).
    hintT_ = approach(hintT_, !m.hint.empty() || !m.warning.empty(), dt);
    toastTime_ = std::max(0.0f, toastTime_ - dt);
    toastT_ = approach(toastT_, toastTime_ > 0.0f && !m.photo, dt);
    flash_ = std::max(0.0f, flash_ - dt / theme::kFlashSeconds);

    clockLabel_.assign(phaseName(m.phase));
    if (m.pin != ClockPin::Auto) clockLabel_.append(strings::kSeparator).append(strings::kPinned);
    if (m.rain) clockLabel_.append(strings::kSeparator).append(strings::kRaining);
    hintText_.assign(m.hint);

    layout(m, font, screen, s);

    if (m.photo) {
        overUi_ = captured_ = false;
        hovered_ = pointed_ = active_ = 0;
        return;
    }
    const bool canPoint = in.inside && !in.blocked;
    overUi_ = false;
    int hovered = 0; // enabled widget under the pointer
    int pointed = 0; // any widget under the pointer: disabled ones still explain themselves
    if (canPoint) {
        for (const Panel& p : panels_)
            if (p.box.contains(in.x, in.y)) overUi_ = true;
        // Every visible panel stops the pointer, so neither clicks nor the placement ghost reach
        // the map through it.
        if (titleBox_.contains(in.x, in.y) ||
            (drawerT_ > 0.5f && drawerBox_.contains(in.x, in.y)) ||
            (journalT_ > 0.5f && journalBox_.contains(in.x, in.y)) ||
            (hintT_ > 0.5f && hintBox_.contains(in.x, in.y)) ||
            (toastT_ > 0.5f && !toast_.empty() && toastBox_.contains(in.x, in.y)))
            overUi_ = true;
        for (auto it = widgets_.rbegin(); it != widgets_.rend(); ++it) {
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
    if (hovered == kJournalClose && !m.journalOpen) hovered = 0;
    if (hovered != hovered_ && hovered != 0) emit(HudAction::Kind::Hover);
    if (pointed != pointed_) hoverTime_ = 0;
    hovered_ = hovered;
    pointed_ = pointed;
    hoverTime_ += dt;

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
            case kSound: emit(HudAction::Kind::Sound); break;
            case kPhoto: emit(HudAction::Kind::Photo); break;
            case kClock: emit(HudAction::Kind::Clock); break;
            case kRain: emit(HudAction::Kind::Rain); break;
            case kJournal:
            case kJournalClose: emit(HudAction::Kind::Journal); break;
            case kUndo: emit(HudAction::Kind::Undo); break;
            case kRedo: emit(HudAction::Kind::Redo); break;
            case kRecentre: emit(HudAction::Kind::Recentre); break;
            case kZoomOut: emit(HudAction::Kind::ZoomOut); break;
            case kZoomIn: emit(HudAction::Kind::ZoomIn); break;
            case kScrollUp:
                if (!scroll_.empty()) --scroll_[static_cast<std::size_t>(m.category)];
                break;
            case kScrollDown:
                if (!scroll_.empty()) ++scroll_[static_cast<std::size_t>(m.category)];
                break;
            default:
                if (active_ >= kTile0) {
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
    if (in.wheel != 0 && canPoint && drawerBox_.contains(in.x, in.y) && !scroll_.empty())
        scroll_[static_cast<std::size_t>(m.category)] += in.wheel > 0 ? -1 : 1;

    for (std::size_t i = 1; i < hover_.size(); ++i) {
        const int id = static_cast<int>(i);
        hover_[i] = approach(hover_[i], id == hovered_, dt);
        press_[i] = approach(press_[i], id == active_ && id == hovered_, dt * 2);
    }
    const bool showTip = pointed_ != 0 && hoverTime_ > theme::kTooltipDelay && active_ == 0;
    if (showTip) tooltipId_ = pointed_;
    tooltipT_ = approach(tooltipT_, showTip, dt);
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
    const float inset = (w.id == kBuild || w.id == kRemove) ? theme::kDockPad * s : 0.0f;
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
    const Thumbnailed t = thumbFor(m, w.entry, box.w);
    p.thumbnail(*t.sprite, box, t.maxScale, alpha);

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
    p.text(Face::Title, strings::kTitle, b.x + pad, b.y + pad + f.ascent(Face::Title), theme::kInk);
    const float y2 = b.y + pad + lh1;
    p.icon(phaseIcon(m.phase), b.x + pad + iconW * 0.5f, y2 + lh2 * 0.5f, theme::kInkMuted);
    p.text(Face::Body, clockLabel_, b.x + pad + iconW + theme::kTitleIconGap * s,
           y2 + f.ascent(Face::Body), theme::kInkMuted);
}

void Hud::drawJournal(Painter& p, const HudModel& m) const {
    const float a = smooth(journalT_);
    const float s = scale_;
    const Box b = journalBox_;
    const Font& f = p.font();
    const float pad = theme::kPanelPad * s;
    const float header = theme::kJournalHeader * s;
    p.text(Face::Title, strings::kJournal, b.x + pad,
           b.y + header * 0.5f + f.ascent(Face::Title) * theme::kBaselineCentre,
           withAlpha(theme::kInk, a));
    p.roundRect({b.x + pad, b.y + header - theme::kRim * s, b.w - 2 * pad, theme::kRim * s}, 0,
                withAlpha(theme::kDivider, a), 0);
    float y = b.y + header;
    const float row = theme::kJournalRow * s;
    const float rowPad = theme::kJournalRowPad * s;
    const float iconSize = theme::kJournalIcon * s;
    const float iconPad = theme::kJournalIconPad * s;
    for (std::size_t v = 0; v < m.cat->visitors.size(); ++v) {
        if (y + row > b.y + b.h + 1) break;
        const auto& def = m.cat->visitors[v];
        const bool seen = m.visitors->seen(static_cast<int>(v));
        const Box icon{b.x + pad, y + rowPad, iconSize, iconSize};
        p.roundRect(icon, iconSize * 0.5f, withAlpha(theme::kInset, a));
        p.rim(icon, iconSize * 0.5f, theme::kRim * s, withAlpha(theme::kInsetRimTop, a),
              withAlpha(theme::kInsetRimBottom, a));
        if (seen) {
            const Sprite& spr =
                v < m.thumbs->visitors.size() ? m.thumbs->visitors[v] : m.thumbs->placeholder;
            p.thumbnail(
                spr,
                {icon.x + iconPad, icon.y + iconPad, icon.w - 2 * iconPad, icon.h - 2 * iconPad},
                (icon.w - 2 * iconPad) / spr.w, a);
        } else {
            p.text(Face::Body, strings::kJournalMystery,
                   icon.cx() - f.measure(Face::Body, strings::kJournalMystery) * 0.5f,
                   icon.cy() + f.ascent(Face::Body) * theme::kBaselineCentre,
                   withAlpha(theme::kInkMuted, a));
        }
        const float tx = icon.x + icon.w + theme::kJournalTextGap * s;
        const float tw = b.x + b.w - pad - tx;
        p.text(Face::Body, seen ? std::string_view(def.name) : strings::kJournalUnknown, tx,
               y + rowPad + f.ascent(Face::Body), withAlpha(theme::kInk, a));
        const int present = m.visitors->present(static_cast<int>(v));
        if (present > 0) {
            char buf[24];
            const auto end =
                std::format_to_n(buf, sizeof buf, "{}{}", strings::kJournalCount, present);
            const std::string_view count(buf, static_cast<std::size_t>(end.out - buf));
            p.text(Face::Body, count, b.x + b.w - pad - f.measure(Face::Body, count),
                   y + rowPad + f.ascent(Face::Body), withAlpha(theme::kAccent, a));
        }
        p.wrapped(Face::Body, seen ? std::string_view(def.blurb) : strings::kJournalEmpty, tx,
                  y + rowPad + f.lineHeight(Face::Body), tw, 1, withAlpha(theme::kInkMuted, a));
        y += row;
    }
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
    p.text(Face::Body, toast_, b.x + pad + iconW + theme::kToastIconGap * s,
           b.cy() + f.ascent(Face::Body) * theme::kBaselineCentre, withAlpha(theme::kInk, a));
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
    categoryEntries(*m.cat, m.category, entries_);
    const auto it = std::ranges::find_if(entries_, [&](const DrawerEntry& e) {
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
            if (w.id == kJournalClose) {
                if (journalT_ > 0) drawButton(p, w, ja);
                continue;
            }
            drawButton(p, w, 1.0f);
        }
        if (journalT_ > 0) drawJournal(p, m);
        p.endLayer();

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
    const float ta = toast_.empty() || m.photo ? 0.0f : smooth(toastT_);
    if (ha > 0 || ta > 0) {
        p.glass(hintBox_, hintBox_.h * 0.5f, ha, theme::kGlass);
        p.glass(toastBox_, toastBox_.h * 0.5f, ta, theme::kGlass);
        p.endGlass();
        drawHint(p, m);
        drawToast(p);
    }
    if (!m.photo) drawTooltip(p);
    if (flash_ > 0)
        p.roundRect({0, 0, screen_.x, screen_.y}, 0,
                    withAlpha(theme::kFlash, flash_ * flash_ * 0.8f), 0);
}

} // namespace lc
