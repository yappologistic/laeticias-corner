#include "ui/hud.hpp"

#include "ui/strings.hpp"
#include "ui/theme.hpp"

#include <algorithm>
#include <cmath>

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
    if (cat.categories[static_cast<std::size_t>(category)].id == kGroundCategory) {
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

void Hud::layout(const HudModel& m, const Font& font, Vec2 screen, float s) {
    widgets_.clear();
    panels_.clear();
    const float margin = theme::kMargin * s;
    const float btn = theme::kButton * s;
    const float pad = theme::kDockPad * s;
    const float dockH = btn + 2 * pad;
    const float gap = theme::kGap * s;
    const float y = screen.y - margin - dockH;
    bottomTop_ = y;

    // Bottom-left: Build pill and the remove tool.
    const float buildW = btn + 64.0f * s;
    {
        Widget& w = add(kBuild, {margin, y, buildW, dockH});
        w.icon = theme::icon::kPlus;
        w.label = strings::kBuild;
        w.tooltip = strings::kBuild;
        w.shortcut = "B";
        w.selected = m.drawerOpen || m.tool == Tool::Place || m.tool == Tool::Paint;
        panels_.push_back({w.box, dockH * 0.5f});
        Widget& r = add(kRemove, {margin + buildW + gap, y, dockH, dockH});
        r.icon = theme::icon::kEraser;
        r.tooltip = strings::kRemove;
        r.shortcut = "X";
        r.selected = m.tool == Tool::Remove;
        panels_.push_back({r.box, dockH * 0.5f});
    }
    const float leftEnd = margin + buildW + gap + dockH;

    // Right dock: undo, redo | recentre | zoom out, zoom in.
    const float divider = gap * 2;
    const float rightW = 5 * btn + 2 * divider + 2 * pad;
    const float rightX = screen.x - margin - rightW;
    panels_.push_back({{rightX, y, rightW, dockH}, dockH * 0.5f});
    {
        float x = rightX + pad;
        const auto button = [&](int id, char32_t icon, std::string_view tip, std::string_view key,
                                bool enabled) {
            Widget& w = add(id, {x, y + pad, btn, btn});
            w.icon = icon;
            w.tooltip = tip;
            w.shortcut = key;
            w.enabled = enabled;
            x += btn;
        };
        button(kUndo, theme::icon::kUndo, strings::kUndo, "Ctrl+Z", m.canUndo);
        button(kRedo, theme::icon::kRedo, strings::kRedo, "Ctrl+Shift+Z", m.canRedo);
        const auto rule = [&](Box& b) {
            b = {std::round(x + divider * 0.5f - theme::kRim * s * 0.5f), y + pad + btn * 0.25f,
                 theme::kRim * s, btn * 0.5f};
            x += divider;
        };
        rule(dividers_[0]);
        button(kRecentre, theme::icon::kHome, strings::kRecentre, "Home", true);
        rule(dividers_[1]);
        button(kZoomOut, theme::icon::kMinus, strings::kZoomOut, "−", m.canZoomOut);
        button(kZoomIn, theme::icon::kPlus, strings::kZoomIn, "+", m.canZoomIn);
    }

    // Centre dock, kept clear of both side groups on narrow windows.
    const float centreW = 5 * btn + 2 * pad;
    float centreX = std::round((screen.x - centreW) * 0.5f);
    centreX = std::clamp(centreX, leftEnd + gap, std::max(leftEnd + gap, rightX - gap - centreW));
    panels_.push_back({{centreX, y, centreW, dockH}, dockH * 0.5f});
    {
        float x = centreX + pad;
        const auto button = [&](int id, char32_t icon, std::string_view tip, std::string_view key,
                                bool selected) {
            Widget& w = add(id, {x, y + pad, btn, btn});
            w.icon = icon;
            w.tooltip = tip;
            w.shortcut = key;
            w.selected = selected;
            x += btn;
        };
        button(kSound, m.muted ? theme::icon::kSoundOff : theme::icon::kSoundOn,
               m.muted ? strings::kSoundOff : strings::kSoundOn, "M", false);
        button(kPhoto, theme::icon::kCamera, strings::kPhoto, "P", false);
        button(kClock, pinIcon(m.pin), pinTooltip(m.pin), "C", m.pin != ClockPin::Auto);
        button(kRain, theme::icon::kRain, m.rain ? strings::kRainOn : strings::kRainOff, "N",
               m.rain);
        button(kJournal, theme::icon::kJournal, strings::kJournal, "J", m.journalOpen);
    }

    // Title and clock, top-left.
    {
        const float tpad = 14.0f * s;
        const float w1 = font.measure(Face::Title, strings::kTitle);
        const float w2 = theme::kIcon * s + 6 * s + font.measure(Face::Body, clockLabel_);
        titleBox_ = {margin, margin, std::max(w1, w2) + 2 * tpad,
                     2 * tpad + font.lineHeight(Face::Title) + font.lineHeight(Face::Body)};
    }

    // Build drawer above the bottom-left group.
    drawerBox_ = {};
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

        const float w =
            2 * ppad + static_cast<float>(cols) * tileW + static_cast<float>(cols - 1) * gap;
        const float h = 2 * ppad + theme::kTabH * s + gap + static_cast<float>(rows) * tileH +
                        static_cast<float>(rows - 1) * gap;
        const float slide = (1.0f - smooth(drawerT_)) * 16.0f * s;
        drawerBox_ = {margin, y - gap - h + slide, w, h};

        float tx = drawerBox_.x + ppad;
        const float ty = drawerBox_.y + ppad;
        for (std::size_t c = 0; c < m.cat->categories.size(); ++c) {
            const float tabW = font.measure(Face::Body, m.cat->categories[c].name) + 28.0f * s;
            Widget& t = add(kTab0 + static_cast<int>(c), {tx, ty, tabW, theme::kTabH * s});
            t.label = m.cat->categories[c].name;
            t.selected = static_cast<int>(c) == m.category;
            tx += tabW + gap;
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

    // Journal panel, top-right.
    journalBox_ = {};
    if (journalT_ > 0.0f) {
        const float jw = std::min(theme::kJournalW * s, screen.x - 2 * margin);
        const float header = 48.0f * s;
        const float h = header +
                        static_cast<float>(m.cat->visitors.size()) * theme::kJournalRow * s +
                        theme::kPanelPad * s * 0.5f;
        const float slide = (1.0f - smooth(journalT_)) * 16.0f * s;
        journalBox_ = {screen.x - margin - jw + slide, margin, jw, std::min(h, y - gap - margin)};
        Widget& c = add(kJournalClose, {journalBox_.x + jw - 8 * s - 32 * s, journalBox_.y + 8 * s,
                                        32 * s, 32 * s});
        c.icon = theme::icon::kClose;
        c.tooltip = strings::kClose;
        c.shortcut = "J";
    }

    // Hint line above the drawer or docks, toast at the top; both slide a little as they fade.
    {
        const float hpad = 16.0f * s;
        const float w1 = font.measure(Face::Body, hintText_);
        const float w2 = m.warning.empty() ? 0.0f : font.measure(Face::Body, m.warning);
        const float sep = (w1 > 0 && w2 > 0) ? font.measure(Face::Body, strings::kSeparator) : 0.0f;
        const float w = w1 + sep + w2 + 2 * hpad;
        const float h = 36.0f * s;
        const float a = smooth(hintT_);
        const float bottom = drawerT_ > 0.0f ? drawerBox_.y : bottomTop_;
        hintBox_ = {std::round((screen.x - w) * 0.5f), bottom - gap - h + (1 - a) * 8 * s, w, h};
    }
    {
        const float tpad = 18.0f * s;
        const float w = theme::kIcon * s + 10 * s + font.measure(Face::Body, toast_) + 2 * tpad;
        const float h = 40.0f * s;
        toastBox_ = {std::round((screen.x - w) * 0.5f), margin - (1 - smooth(toastT_)) * 12 * s, w,
                     h};
    }
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
    hintT_ = approach(hintT_, (!m.hint.empty() || !m.warning.empty()) && !m.photo, dt);
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
        if (titleBox_.contains(in.x, in.y) ||
            (drawerT_ > 0.5f && drawerBox_.contains(in.x, in.y)) ||
            (journalT_ > 0.5f && journalBox_.contains(in.x, in.y)))
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
    if (hovered >= kTab0 && drawerT_ < 1.0f && !m.drawerOpen) hovered = 0;
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
    if (in.wheel != 0 && canPoint && drawerBox_.contains(in.x, in.y) && !scroll_.empty()) {
        scroll_[static_cast<std::size_t>(m.category)] += in.wheel > 0 ? -1 : 1;
    }

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
        const float total = iconW + 8 * s + textW;
        const float x0 = inner.cx() - total * 0.5f;
        p.icon(w.icon, x0 + iconW * 0.5f, inner.cy() + press, ink);
        p.text(Face::Body, w.label, x0 + iconW + 8 * s,
               inner.cy() + press + f.ascent(Face::Body) * 0.36f, ink);
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
    p.text(Face::Body, w.label, w.box.cx() - tw * 0.5f, w.box.cy() + f.ascent(Face::Body) * 0.36f,
           withAlpha(ink, alpha));
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

    const SpriteId thumb =
        thumbnail(*m.sprites, w.entry.terrain ? Thumb::Terrain : Thumb::Item, w.entry.index);
    const float lift = h * 2.0f * s - pr * s;
    const float th = theme::kThumb * s;
    p.thumbnail(thumb, {w.box.x + 4 * s, w.box.y + 6 * s - lift, w.box.w - 8 * s, th}, alpha);

    const Font& f = p.font();
    std::string_view label = w.label;
    const float maxW = w.box.w - 8 * s;
    float tw = f.measure(Face::Body, label);
    bool cut = false;
    while (tw > maxW && label.size() > 1) {
        label.remove_suffix(1);
        tw = f.measure(Face::Body, label) + f.measure(Face::Body, "…");
        cut = true;
    }
    const float x = w.box.cx() - tw * 0.5f;
    const float base = w.box.y + w.box.h - 12 * s;
    const SDL_FColor ink = withAlpha(theme::kInk, alpha);
    const float adv = f.measure(Face::Body, label);
    p.text(Face::Body, label, x, base, ink);
    if (cut) p.text(Face::Body, "…", x + adv, base, ink);
}

void Hud::drawTitle(Painter& p, const HudModel& m) const {
    const float s = scale_;
    const Font& f = p.font();
    const float pad = 14.0f * s;
    const float iconW = theme::kIcon * s;
    const float lh1 = f.lineHeight(Face::Title);
    const float lh2 = f.lineHeight(Face::Body);
    const Box b = titleBox_;
    p.text(Face::Title, strings::kTitle, b.x + pad, b.y + pad + f.ascent(Face::Title), theme::kInk);
    const float y2 = b.y + pad + lh1;
    p.icon(phaseIcon(m.phase), b.x + pad + iconW * 0.5f, y2 + lh2 * 0.5f, theme::kInkMuted);
    p.text(Face::Body, clockLabel_, b.x + pad + iconW + 6 * s, y2 + f.ascent(Face::Body),
           theme::kInkMuted);
}

void Hud::drawJournal(Painter& p, const HudModel& m) const {
    const float a = smooth(journalT_);
    const float s = scale_;
    const Box b = journalBox_;
    const Font& f = p.font();
    const float pad = theme::kPanelPad * s;
    const float header = 48.0f * s;
    p.text(Face::Title, strings::kJournal, b.x + pad, b.y + 24 * s + f.ascent(Face::Title) * 0.36f,
           withAlpha(theme::kInk, a));
    p.roundRect({b.x + pad, b.y + header - theme::kRim * s, b.w - 2 * pad, theme::kRim * s}, 0,
                withAlpha(theme::kDivider, a), 0);
    float y = b.y + header;
    const float row = theme::kJournalRow * s;
    for (std::size_t v = 0; v < m.cat->visitors.size(); ++v) {
        if (y + row > b.y + b.h + 1) break;
        const auto& def = m.cat->visitors[v];
        const bool seen = m.visitors->seen(static_cast<int>(v));
        const Box icon{b.x + pad, y + 6 * s, 40 * s, 40 * s};
        p.roundRect(icon, 20 * s, withAlpha(theme::kInset, a));
        p.rim(icon, 20 * s, theme::kRim * s, withAlpha(theme::kInsetRimTop, a),
              withAlpha(theme::kInsetRimBottom, a));
        if (seen) {
            p.thumbnail(thumbnail(*m.sprites, Thumb::Visitor, static_cast<int>(v)),
                        {icon.x + 4 * s, icon.y + 4 * s, 32 * s, 32 * s}, a);
        } else {
            p.text(Face::Body, "?", icon.cx() - f.measure(Face::Body, "?") * 0.5f,
                   icon.cy() + f.ascent(Face::Body) * 0.36f, withAlpha(theme::kInkMuted, a));
        }
        const float tx = icon.x + icon.w + 12 * s;
        const float tw = b.x + b.w - pad - tx;
        p.text(Face::Body, seen ? std::string_view(def.name) : strings::kJournalUnknown, tx,
               y + 6 * s + f.ascent(Face::Body), withAlpha(theme::kInk, a));
        const int present = m.visitors->present(static_cast<int>(v));
        if (present > 0) {
            char buf[16];
            const int n = std::snprintf(buf, sizeof buf, "×%d", present);
            const std::string_view count(buf, static_cast<std::size_t>(std::max(0, n)));
            p.text(Face::Body, count, b.x + b.w - pad - f.measure(Face::Body, count),
                   y + 6 * s + f.ascent(Face::Body), withAlpha(theme::kAccent, a));
        }
        p.wrapped(Face::Body, seen ? std::string_view(def.blurb) : strings::kJournalEmpty, tx,
                  y + 6 * s + f.lineHeight(Face::Body), tw, 1, withAlpha(theme::kInkMuted, a));
        y += row;
    }
}

void Hud::drawHint(Painter& p, const HudModel& m) const {
    const float a = smooth(hintT_);
    if (a <= 0) return;
    const Font& f = p.font();
    const Box b = hintBox_;
    const float base = b.cy() + f.ascent(Face::Body) * 0.36f;
    float x = b.x + 16.0f * scale_;
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
    const float pad = 18.0f * s;
    const float iconW = theme::kIcon * s;
    const Box b = toastBox_;
    p.icon(theme::icon::kSparkle, b.x + pad + iconW * 0.5f, b.cy(), withAlpha(theme::kAccent, a));
    p.text(Face::Body, toast_, b.x + pad + iconW + 10 * s, b.cy() + f.ascent(Face::Body) * 0.36f,
           withAlpha(theme::kInk, a));
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
    const float pad = 10.0f * s;
    const float tw = f.measure(Face::Body, w->tooltip);
    const float kw = w->shortcut.empty() ? 0.0f : f.measure(Face::Body, w->shortcut) + 12 * s;
    const float bw = tw + (kw > 0 ? kw + 8 * s : 0) + 2 * pad;
    const float bh = 32.0f * s;
    const bool above = w->box.y > screen_.y * 0.5f;
    float x = std::round(w->box.cx() - bw * 0.5f);
    x = std::clamp(x, theme::kMargin * s * 0.5f, screen_.x - bw - theme::kMargin * s * 0.5f);
    float y = above ? w->box.y - bh - 10 * s + (1 - a) * 4 * s
                    : w->box.y + w->box.h + 10 * s - (1 - a) * 4 * s;
    // Above the docks, keep clear of a visible hint line rather than covering it.
    const Box& h = hintBox_;
    if (above && hintT_ > 0 && x < h.x + h.w && x + bw > h.x && y < h.y + h.h && y + bh > h.y)
        y = h.y - bh - theme::kGap * s;
    const Box b{x, y, bw, bh};
    p.glass(b, 10 * s, a, theme::kGlassTip);
    p.endGlass();
    const float base = b.cy() + f.ascent(Face::Body) * 0.36f;
    p.text(Face::Body, w->tooltip, b.x + pad, base, withAlpha(theme::kInk, a));
    if (kw > 0) {
        const Box chip{b.x + pad + tw + 8 * s, b.y + 6 * s, kw, bh - 12 * s};
        p.roundRect(chip, 6 * s, withAlpha(theme::kChip, a));
        p.rim(chip, 6 * s, theme::kRim * s, withAlpha(theme::kInsetRimTop, a),
              withAlpha(theme::kInsetRimBottom, a));
        p.text(Face::Body, w->shortcut, chip.x + 6 * s, base, withAlpha(theme::kInkMuted, a));
    }
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
            if (w.id >= kTab0) continue;
            if (w.id == kJournalClose) {
                if (journalT_ > 0) drawButton(p, w, ja);
                continue;
            }
            drawButton(p, w, 1.0f);
        }
        if (journalT_ > 0) drawJournal(p, m);
        p.endLayer();

        // The drawer may cover the journal on small windows.
        if (drawerT_ > 0) {
            const float a = smooth(drawerT_);
            p.glass(drawerBox_, radius, a, theme::kGlass);
            p.endGlass();
            for (const Widget& w : widgets_) {
                if (w.id >= kTile0)
                    drawTile(p, w, m, a);
                else if (w.id >= kTab0)
                    drawTab(p, w, a);
            }
            p.endLayer();
        }

        const float ha = smooth(hintT_);
        const float ta = toast_.empty() ? 0.0f : smooth(toastT_);
        if (ha > 0 || ta > 0) {
            p.glass(hintBox_, hintBox_.h * 0.5f, ha, theme::kGlass);
            p.glass(toastBox_, toastBox_.h * 0.5f, ta, theme::kGlass);
            p.endGlass();
            drawHint(p, m);
            drawToast(p);
        }
        drawTooltip(p);
    }
    if (flash_ > 0)
        p.roundRect({0, 0, screen_.x, screen_.y}, 0,
                    withAlpha(theme::kFlash, flash_ * flash_ * 0.8f), 0);
}

} // namespace lc
