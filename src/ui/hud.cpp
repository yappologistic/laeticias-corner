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
    widgets_.reserve(kMaxWidgets);
    panels_.reserve(16);
    entries_.reserve(256);
    toast_.reserve(96);
    clockLabel_.reserve(64);
    hintText_.reserve(192);
}

std::vector<int> Hud::categoryEntries(const Catalog& cat, int category) {
    std::vector<int> out;
    if (cat.categories[static_cast<std::size_t>(category)].id == kGroundCategory) {
        for (std::size_t t = 0; t < cat.terrain.size(); ++t) out.push_back(static_cast<int>(t));
    } else {
        for (std::size_t i = 0; i < cat.items.size(); ++i)
            if (cat.items[i].category == category) out.push_back(static_cast<int>(i));
    }
    return out;
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
        panels_.push_back({w.box, dockH * 0.5f, 1});
        Widget& r = add(kRemove, {margin + buildW + gap, y, dockH, dockH});
        r.icon = theme::icon::kEraser;
        r.tooltip = strings::kRemove;
        r.shortcut = "X";
        r.selected = m.tool == Tool::Remove;
        panels_.push_back({r.box, dockH * 0.5f, 1});
    }
    const float leftEnd = margin + buildW + gap + dockH;

    // Right dock: undo, redo | recentre | zoom out, zoom in.
    const float divider = gap * 2;
    const float rightW = 5 * btn + 2 * divider + 2 * pad;
    const float rightX = screen.x - margin - rightW;
    panels_.push_back({{rightX, y, rightW, dockH}, dockH * 0.5f, 1});
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
        x += divider;
        button(kRecentre, theme::icon::kHome, strings::kRecentre, "Home", true);
        x += divider;
        button(kZoomOut, theme::icon::kMinus, strings::kZoomOut, "−", m.canZoomOut);
        button(kZoomIn, theme::icon::kPlus, strings::kZoomIn, "+", m.canZoomIn);
    }

    // Centre dock, kept clear of both side groups on narrow windows.
    const float centreW = 5 * btn + 2 * pad;
    float centreX = std::round((screen.x - centreW) * 0.5f);
    centreX = std::clamp(centreX, leftEnd + gap, std::max(leftEnd + gap, rightX - gap - centreW));
    panels_.push_back({{centreX, y, centreW, dockH}, dockH * 0.5f, 1});
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
        entries_ = categoryEntries(*m.cat, m.category);
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
        panels_.push_back({drawerBox_, theme::kPanelRadius * s, smooth(drawerT_)});

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
        const bool ground =
            m.cat->categories[static_cast<std::size_t>(m.category)].id == kGroundCategory;
        for (int i = 0; i < rows * cols; ++i) {
            const int e = scroll * cols + i;
            if (e >= total) break;
            const int col = i % cols;
            const int row = i / cols;
            Widget& t = add(kTile0 + std::min(e, kMaxWidgets - kTile0 - 1),
                            {drawerBox_.x + ppad + static_cast<float>(col) * (tileW + gap),
                             gy + static_cast<float>(row) * (tileH + gap), tileW, tileH});
            t.ref = entries_[static_cast<std::size_t>(e)];
            t.label = ground
                          ? std::string_view(m.cat->terrain[static_cast<std::size_t>(t.ref)].name)
                          : std::string_view(m.cat->items[static_cast<std::size_t>(t.ref)].name);
            t.selected =
                (ground ? m.tool == Tool::Paint : m.tool == Tool::Place) && m.selection == t.ref;
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
        panels_.push_back({journalBox_, theme::kPanelRadius * s, smooth(journalT_)});
        Widget& c = add(kJournalClose, {journalBox_.x + jw - 8 * s - 32 * s, journalBox_.y + 8 * s,
                                        32 * s, 32 * s});
        c.icon = theme::icon::kClose;
        c.tooltip = strings::kClose;
        c.shortcut = "J";
    }
}

void Hud::update(const UiInput& in, const HudModel& m, const Font& font, Vec2 screen, float s,
                 float dt) {
    actionCount_ = 0;
    scale_ = s;
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
        hovered_ = active_ = 0;
        return;
    }
    const bool canPoint = in.inside && !in.blocked;
    overUi_ = false;
    int hovered = 0;
    if (canPoint) {
        for (const Panel& p : panels_)
            if (p.alpha > 0.5f && p.box.contains(in.x, in.y)) overUi_ = true;
        if (titleBox_.contains(in.x, in.y)) overUi_ = true;
        for (auto it = widgets_.rbegin(); it != widgets_.rend(); ++it) {
            if (it->box.contains(in.x, in.y)) {
                overUi_ = true;
                if (it->enabled) hovered = it->id;
                break;
            }
        }
    }
    // Panels that are animating closed are not interactive.
    if (hovered >= kTab0 && drawerT_ < 1.0f && !m.drawerOpen) hovered = 0;
    if (hovered == kJournalClose && !m.journalOpen) hovered = 0;
    if (hovered != hovered_ && hovered != 0) emit(HudAction::Kind::Hover);
    if (hovered != hovered_) hoverTime_ = 0;
    hovered_ = hovered;
    hoverTime_ += dt;

    if (in.pressed && canPoint && overUi_) {
        captured_ = true;
        active_ = hovered;
        hoverTime_ = -10.0f; // no tooltip right after a click
    }
    if (in.released && captured_) {
        if (active_ != 0 && active_ == hovered) {
            const auto ref = [&] {
                for (const Widget& w : widgets_)
                    if (w.id == active_) return w.ref;
                return -1;
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
                    const bool ground =
                        m.cat->categories[static_cast<std::size_t>(m.category)].id ==
                        kGroundCategory;
                    emit(ground ? HudAction::Kind::PickTerrain : HudAction::Kind::PickItem, ref);
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

    for (int id = 0; id < kMaxWidgets; ++id) {
        hover_[static_cast<std::size_t>(id)] =
            approach(hover_[static_cast<std::size_t>(id)], id == hovered_ && id != 0, dt);
        press_[static_cast<std::size_t>(id)] =
            approach(press_[static_cast<std::size_t>(id)],
                     id == active_ && id == hovered_ && id != 0, dt * 2);
    }
    const bool showTip = hovered_ != 0 && hoverTime_ > theme::kTooltipDelay && active_ == 0;
    if (showTip) tooltipId_ = hovered_;
    tooltipT_ = approach(tooltipT_, showTip, dt);
}

std::optional<Vec2> Hud::widgetCentre(std::string_view name, const HudModel& m) const {
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
            const bool ground =
                m.cat->categories[static_cast<std::size_t>(m.category)].id == kGroundCategory;
            const auto& entryId = ground ? m.cat->terrain[static_cast<std::size_t>(w.ref)].id
                                         : m.cat->items[static_cast<std::size_t>(w.ref)].id;
            if (entryId == *tile) return Vec2{w.box.cx(), w.box.cy()};
        } else if (id != 0 && w.id == id) {
            return Vec2{w.box.cx(), w.box.cy()};
        }
    }
    return std::nullopt;
}

void Hud::drawPanel(Painter& p, Box b, float radius, float alpha) const {
    const float s = scale_;
    const float soft = theme::kShadowSoftness * s;
    p.roundRect(
        {b.x - soft * 0.25f, b.y + 2 * s - soft * 0.25f, b.w + soft * 0.5f, b.h + soft * 0.5f},
        radius + soft * 0.5f, withAlpha(theme::kShadow, alpha * 0.6f), soft);
    p.roundRect(b, radius, withAlpha(theme::kPanel, alpha));
}

void Hud::drawButton(Painter& p, const Widget& w, float alpha) const {
    const auto i = static_cast<std::size_t>(w.id);
    const float h = smooth(hover_[i]);
    const float pr = smooth(press_[i]);
    const float r = std::min(w.box.w, w.box.h) * 0.5f;
    const float inset = (w.id == kBuild || w.id == kRemove) ? theme::kDockPad * scale_ : 0.0f;
    const Box inner{w.box.x + inset, w.box.y + inset, w.box.w - 2 * inset, w.box.h - 2 * inset};
    const float ir = r - inset;
    if (w.selected) {
        p.roundRect(inner, ir, withAlpha(theme::kAccent, alpha));
    }
    if (h > 0)
        p.roundRect(inner, ir,
                    withAlpha(w.selected ? SDL_FColor{1, 1, 1, 0.14f} : theme::kHover, alpha * h));
    if (pr > 0) p.roundRect(inner, ir, withAlpha(theme::kPressed, alpha * pr));
    SDL_FColor ink = w.selected ? theme::kOnAccent : theme::kInk;
    if (!w.enabled) ink = withAlpha(ink, 0.32f);
    ink = withAlpha(ink, alpha);
    const float press = pr * scale_; // content dips one unit while pressed
    if (!w.label.empty()) {
        const Font& f = p.font();
        const float textW = f.measure(Face::Body, w.label);
        const float iconW = theme::kIcon * scale_;
        const float total = iconW + 8 * scale_ + textW;
        const float x0 = inner.cx() - total * 0.5f;
        p.icon(w.icon, x0 + iconW * 0.5f, inner.cy() + press, ink);
        p.text(Face::Body, w.label, x0 + iconW + 8 * scale_,
               inner.cy() + press + f.ascent(Face::Body) * 0.36f, ink);
    } else {
        p.icon(w.icon, inner.cx(), inner.cy() + press, ink);
    }
}

void Hud::drawTile(Painter& p, const Widget& w, const HudModel& m, float alpha) const {
    const float s = scale_;
    const auto i = static_cast<std::size_t>(w.id);
    const float h = smooth(hover_[i]);
    const float pr = smooth(press_[i]);
    const float r = 12.0f * s;
    if (w.selected) {
        p.roundRect(w.box, r, withAlpha(theme::kAccent, alpha));
        p.roundRect({w.box.x + 2 * s, w.box.y + 2 * s, w.box.w - 4 * s, w.box.h - 4 * s}, r - 2 * s,
                    withAlpha(mixColor(theme::kPanelSolid, theme::kAccent, 0.12f), alpha));
    } else {
        p.roundRect(w.box, r, withAlpha(theme::kTileBack, alpha));
    }
    if (h > 0) p.roundRect(w.box, r, withAlpha(theme::kHover, alpha * h));
    if (pr > 0) p.roundRect(w.box, r, withAlpha(theme::kPressed, alpha * pr));

    const bool ground =
        m.cat->categories[static_cast<std::size_t>(m.category)].id == kGroundCategory;
    SpriteId thumb = 0;
    const auto& spr = *m.sprites;
    if (ground) {
        const auto t = static_cast<std::size_t>(w.ref);
        thumb = m.cat->terrain[t].base ? spr.terrainBase[t].front()
                                       : spr.terrainOverlay[t][15].frames.front();
    } else {
        thumb = spr.items[static_cast<std::size_t>(w.ref)].base.front().frames.front();
    }
    const float lift = h * 2.0f * s - pr * s;
    const float th = theme::kThumb * s;
    p.thumbnail(thumb, {w.box.x + (w.box.w - th) * 0.5f, w.box.y + 6 * s - lift, th, th}, alpha);

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
    const SDL_FColor ink = withAlpha(w.selected ? theme::kAccent : theme::kInk, alpha);
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
    drawPanel(p, b, theme::kPanelRadius * s, 1.0f);
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
    drawPanel(p, b, theme::kPanelRadius * s, a);
    const Font& f = p.font();
    const float pad = theme::kPanelPad * s;
    p.text(Face::Title, strings::kJournal, b.x + pad, b.y + 24 * s + f.ascent(Face::Title) * 0.36f,
           withAlpha(theme::kInk, a));
    float y = b.y + 48.0f * s;
    const float row = theme::kJournalRow * s;
    for (std::size_t v = 0; v < m.cat->visitors.size(); ++v) {
        if (y + row > b.y + b.h + 1) break;
        const auto& def = m.cat->visitors[v];
        const bool seen = m.visitors->seen(static_cast<int>(v));
        const Box icon{b.x + pad, y + 6 * s, 40 * s, 40 * s};
        p.roundRect(icon, 20 * s, withAlpha(theme::kTileBack, a));
        if (seen) {
            const auto anim = static_cast<std::size_t>(CritterAnim::IdleFront);
            p.thumbnail(m.sprites->critters[v][anim].frames.front(),
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
    const float s = scale_;
    const Font& f = p.font();
    const float pad = 16.0f * s;
    const float w1 = f.measure(Face::Body, hintText_);
    const float w2 = m.warning.empty() ? 0.0f : f.measure(Face::Body, m.warning);
    const float sep = (w1 > 0 && w2 > 0) ? f.measure(Face::Body, strings::kSeparator) : 0.0f;
    const float w = w1 + sep + w2 + 2 * pad;
    const float h = 36.0f * s;
    const float bottom = drawerT_ > 0.0f ? drawerBox_.y : bottomTop_;
    const Box b{std::round((screen_.x - w) * 0.5f), bottom - theme::kGap * s - h + (1 - a) * 8 * s,
                w, h};
    drawPanel(p, b, h * 0.5f, a);
    const float base = b.cy() + f.ascent(Face::Body) * 0.36f;
    float x = b.x + pad;
    p.text(Face::Body, hintText_, x, base, withAlpha(theme::kInk, a));
    x += w1;
    if (w2 > 0) {
        if (sep > 0) {
            p.text(Face::Body, strings::kSeparator, x, base, withAlpha(theme::kInkMuted, a));
            x += sep;
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
    const float w = iconW + 10 * s + f.measure(Face::Body, toast_) + 2 * pad;
    const float h = 40.0f * s;
    const Box b{std::round((screen_.x - w) * 0.5f), theme::kMargin * s - (1 - a) * 12 * s, w, h};
    drawPanel(p, b, h * 0.5f, a);
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
    const float y = above ? w->box.y - bh - 10 * s + (1 - a) * 4 * s
                          : w->box.y + w->box.h + 10 * s - (1 - a) * 4 * s;
    const Box b{x, y, bw, bh};
    p.roundRect({b.x, b.y + 2 * s, b.w, b.h}, 10 * s, withAlpha(theme::kShadow, a * 0.5f), 8 * s);
    p.roundRect(b, 10 * s, withAlpha(theme::kInk, 0.94f * a));
    const float base = b.cy() + f.ascent(Face::Body) * 0.36f;
    p.text(Face::Body, w->tooltip, b.x + pad, base, withAlpha(theme::kOnAccent, a));
    if (kw > 0) {
        const Box chip{b.x + pad + tw + 8 * s, b.y + 6 * s, kw, bh - 12 * s};
        p.roundRect(chip, 6 * s, withAlpha(SDL_FColor{1, 1, 1, 0.16f}, a));
        p.text(Face::Body, w->shortcut, chip.x + 6 * s, base,
               withAlpha(theme::kOnAccent, a * 0.85f));
    }
}

void Hud::draw(Painter& p, const HudModel& m) const {
    if (!m.photo) {
        drawTitle(p, m);
        if (journalT_ > 0) drawJournal(p, m);
        if (drawerT_ > 0) {
            const float a = smooth(drawerT_);
            drawPanel(p, drawerBox_, theme::kPanelRadius * scale_, a);
            for (const Widget& w : widgets_) {
                if (w.id >= kTile0) {
                    drawTile(p, w, m, a);
                } else if (w.id >= kTab0) {
                    const auto i = static_cast<std::size_t>(w.id);
                    const float r = w.box.h * 0.5f;
                    if (w.selected)
                        p.roundRect(w.box, r, withAlpha(theme::kInk, a));
                    else if (hover_[i] > 0)
                        p.roundRect(w.box, r, withAlpha(theme::kHover, a * smooth(hover_[i])));
                    const Font& f = p.font();
                    const float tw = f.measure(Face::Body, w.label);
                    p.text(Face::Body, w.label, w.box.cx() - tw * 0.5f,
                           w.box.cy() + f.ascent(Face::Body) * 0.36f,
                           withAlpha(w.selected ? theme::kOnAccent : theme::kInk, a));
                }
            }
        }
        for (const Panel& pn : panels_) {
            if (pn.box.x == drawerBox_.x && pn.box.y == drawerBox_.y) continue;
            if (pn.box.x == journalBox_.x && pn.box.y == journalBox_.y) continue;
            drawPanel(p, pn.box, pn.radius, pn.alpha);
        }
        for (const Widget& w : widgets_) {
            if (w.id >= kTab0) continue;
            if (w.id == kJournalClose) {
                if (journalT_ > 0) drawButton(p, w, smooth(journalT_));
                continue;
            }
            drawButton(p, w, 1.0f);
        }
        drawHint(p, m);
        drawToast(p);
        drawTooltip(p);
    }
    if (flash_ > 0)
        p.roundRect({0, 0, screen_.x, screen_.y}, 0,
                    withAlpha(theme::kFlash, flash_ * flash_ * 0.8f), 0);
}

} // namespace lc
