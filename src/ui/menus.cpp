#include "ui/menus.hpp"

#include "core/worlds.hpp"
#include "ui/strings.hpp"
#include "ui/theme.hpp"

#include <algorithm>
#include <charconv>
#include <cmath>
#include <format>
#include <utility>

namespace lc {
namespace {

enum Id : int {
    kContinue = 1,
    kWorlds,
    kSettings,
    kQuit,
    kBack = 10,
    kNewCard,
    kField = 20,
    kFreeBuild,
    kCancel,
    kCreate,
    kKeep,
    kConfirmDelete,
    kErrorBack,
    kMusic = 30, // 30..32: the volume sliders
    kMute = 33,
    kFullscreen,
    kUiScale,
    kReduceMotion,
    kGrid,
    kVsync,
    kChatty,
    kQuiet,
    kReplay,
    kDone,
    kResume = 50,
    kPauseSettings,
    kPostcards,
    kBackToWorlds,
    kPauseQuit,
    kSkipTour = 60,
    kFramePrev = 70,
    kFrameNext,
    kCaption,
    kHideBar,
    kTake,
    kFolder,
    kClosePhoto,
    kWorld0 = 100, // per world i, four ids from kWorld0 + 4 i: its card, play, rename, delete
};
enum WorldPart : int { kCardPart, kPlayPart, kRenamePart, kDeletePart, kParts };
// Ids that cannot meet another world's however many worlds there are (L-111).
constexpr int worldId(int world, WorldPart part) {
    return kWorld0 + world * kParts + part;
}
constexpr int worldOf(int id) {
    return id >= kWorld0 ? (id - kWorld0) / kParts : -1;
}
constexpr int partOf(int id) {
    return (id - kWorld0) % kParts;
}

struct Named {
    std::string_view name;
    int id;
};
constexpr Named kNames[] = {
    {"continue", kContinue},
    {"worlds", kWorlds},
    {"settings", kSettings},
    {"quit", kQuit},
    {"back", kBack},
    {"new", kNewCard},
    {"field", kField},
    {"freebuild", kFreeBuild},
    {"cancel", kCancel},
    {"create", kCreate},
    {"keep", kKeep},
    {"confirm_delete", kConfirmDelete},
    {"error_back", kErrorBack},
    {"music", kMusic},
    {"effects", kMusic + 1},
    {"ambience", kMusic + 2},
    {"mute", kMute},
    {"fullscreen", kFullscreen},
    {"ui_scale", kUiScale},
    {"reduce_motion", kReduceMotion},
    {"grid", kGrid},
    {"vsync", kVsync},
    {"chatty", kChatty},
    {"quiet", kQuiet},
    {"replay", kReplay},
    {"done", kDone},
    {"resume", kResume},
    {"pause_settings", kPauseSettings},
    {"postcards", kPostcards},
    {"back_to_worlds", kBackToWorlds},
    {"pause_quit", kPauseQuit},
    {"skip_tour", kSkipTour},
    {"frame_prev", kFramePrev},
    {"frame_next", kFrameNext},
    {"caption", kCaption},
    {"hide_bar", kHideBar},
    {"take", kTake},
    {"folder", kFolder},
    {"close_photo", kClosePhoto},
};

SDL_FColor withAlpha(SDL_FColor c, float a) {
    return {c.r, c.g, c.b, c.a * a};
}

float approach(float v, bool on, float dt) {
    const float step = dt / theme::kTransition;
    return on ? std::min(1.0f, v + step) : std::max(0.0f, v - step);
}

// Widgets the keyboard can rest on, in the order ↑ and ↓ walk them.
bool focusable(int id) {
    return id != kField;
}

} // namespace

Menus::Widget& Menus::add(int id, Kind kind, Box box, std::string_view label) {
    widgets_.push_back(Widget{});
    Widget& w = widgets_.back();
    w.id = id;
    w.kind = kind;
    w.box = box;
    w.label = label;
    return w;
}

void Menus::emit(MenuAction::Kind k, int arg, int value, std::string text) {
    actions_.push_back({k, arg, value, std::move(text)});
}

void Menus::open(Page p) {
    if (depth_ + 1 < static_cast<int>(pages_.size())) ++depth_;
    pages_[static_cast<std::size_t>(depth_)] = p;
    focus_ = 0;
    pageT_ = 0;
    dragging_ = 0;
    if (p != Page::Worlds) selectedWorld_ = -1;
}

void Menus::back() {
    if (depth_ > 0) --depth_;
    fieldOpen_ = false;
    focus_ = 0;
    dragging_ = 0;
}

void Menus::closeAll() {
    depth_ = 0;
    pages_[0] = Page::None;
    fieldOpen_ = false;
    focus_ = 0;
}

void Menus::editName(std::string_view initial, int world) {
    fieldOpen_ = true;
    fieldWorld_ = world;
    field_.assign(initial);
    fieldSelected_ = true;
    fieldNote_ = {};
}

const Menus::Widget* Menus::find(int id) const {
    for (const Widget& w : widgets_)
        if (w.id == id) return &w;
    return nullptr;
}

float Menus::hoverOf(int id) const {
    const auto i = static_cast<std::size_t>(id);
    return i < hover_.size() ? hover_[i] : 0.0f;
}

std::optional<Vec2> Menus::widgetCentre(std::string_view name) const {
    int id = 0;
    for (const Named& n : kNames)
        if (n.name == name) id = n.id;
    // "card:N", "play:N", "rename:N", "delete:N"
    for (const auto& [prefix, part] : {std::pair{std::string_view("card:"), kCardPart},
                                       std::pair{std::string_view("play:"), kPlayPart},
                                       std::pair{std::string_view("rename:"), kRenamePart},
                                       std::pair{std::string_view("delete:"), kDeletePart}})
        if (name.starts_with(prefix)) {
            int n = 0;
            const std::string_view d = name.substr(prefix.size());
            if (std::from_chars(d.data(), d.data() + d.size(), n).ec == std::errc{})
                id = worldId(n, part);
        }
    if (const Widget* w = find(id); w != nullptr) return Vec2{w->box.cx(), w->box.cy()};
    return std::nullopt;
}

bool Menus::text(std::string_view utf8, const Font& font) {
    if (!fieldOpen_) return false;
    // Only what the interface can draw, and never past the longest name.
    for (std::size_t i = 0; i < utf8.size();) {
        const std::size_t start = i;
        const char32_t cp = nextCodepoint(utf8, i);
        if (cp < 32 || !font.has(cp)) {
            fieldNote_ = strings::kLetterMissing;
            continue;
        }
        if (std::exchange(fieldSelected_, false)) field_.clear();
        const auto letters = std::ranges::count_if(
            field_, [](char c) { return (static_cast<unsigned char>(c) & 0xC0) != 0x80; });
        if (letters >= kWorldNameMax) {
            fieldNote_ = strings::kNameTooLong;
            break;
        }
        field_.append(utf8.substr(start, i - start));
        fieldNote_ = {};
    }
    return true;
}

bool Menus::key(MenuKey k, const MenuModel& m) {
    if (fieldOpen_) {
        switch (k) {
        case MenuKey::Backspace:
            if (std::exchange(fieldSelected_, false)) {
                field_.clear();
                return true;
            }
            // One whole character.
            while (!field_.empty() && (static_cast<unsigned char>(field_.back()) & 0xC0) == 0x80)
                field_.pop_back();
            if (!field_.empty()) field_.pop_back();
            fieldNote_ = {};
            return true;
        case MenuKey::Enter:
            if (fieldWorld_ >= 0)
                emit(MenuAction::Kind::Rename, fieldWorld_, 0, field_);
            else
                emit(MenuAction::Kind::Create, freeBuild_ ? 1 : 0, 0, field_);
            return true;
        case MenuKey::Escape:
            fieldOpen_ = false;
            if (fieldWorld_ < 0) back(); // the name dialog goes with its field
            return true;
        default:
            fieldSelected_ = false; // the arrows let go of the selection, keeping the text
            return true;
        }
    }
    if (page() == Page::None) return false;
    switch (k) {
    case MenuKey::Escape:
        switch (page()) {
        case Page::Title: return true; // nothing to go back to
        case Page::Pause: emit(MenuAction::Kind::Resume); return true;
        default: back(); return true;
        }
    case MenuKey::Up:
    case MenuKey::Down: {
        std::vector<int> order;
        for (const Widget& w : widgets_)
            if (w.enabled && focusable(w.id) && w.kind != Kind::Bar) order.push_back(w.id);
        if (order.empty()) return true;
        auto it = std::ranges::find(order, focus_);
        // A settings page that scrolls moves on past its last (first) row shown.
        if (page() == Page::Settings && settingsScrollable_ && it != order.end()) {
            const bool down = k == MenuKey::Down;
            const bool edge = down ? it + 2 >= order.end() // the row above Done
                                   : it == order.begin();
            if (edge && (down ? settingsScroll_ < settingsScrollMax_ : settingsScroll_ > 0)) {
                settingsScroll_ += down ? 1 : -1;
                return true;
            }
        }
        const auto n = static_cast<std::ptrdiff_t>(order.size());
        std::ptrdiff_t i = it == order.end() ? (k == MenuKey::Down ? -1 : 0) : it - order.begin();
        i = (i + (k == MenuKey::Down ? 1 : n - 1)) % n;
        focus_ = order[static_cast<std::size_t>(i)];
        if (worldOf(focus_) >= 0) selectedWorld_ = worldOf(focus_);
        emit(MenuAction::Kind::Hover);
        return true;
    }
    case MenuKey::Left:
    case MenuKey::Right: {
        const Widget* w = find(focus_);
        if (w == nullptr) return true;
        const int d = k == MenuKey::Right ? 1 : -1;
        if (w->kind == Kind::Slider) {
            const int bus = w->id - kMusic;
            const int v = std::clamp(static_cast<int>(std::lround(w->amount * 20.0f)) + d, 0, 20);
            emit(MenuAction::Kind::Volume, bus, v * 5);
        } else if (w->id == kUiScale && m.profile != nullptr) {
            emit(MenuAction::Kind::UiScale,
                 std::clamp(m.profile->uiScale + d, 0, kUiScaleCount - 1));
        }
        return true;
    }
    case MenuKey::Enter:
        if (const Widget* w = find(focus_); w != nullptr) activate(*w, m, w->box.cx());
        return true;
    case MenuKey::Backspace: return true;
    }
    return true;
}

void Menus::activate(const Widget& w, const MenuModel& m, float px) {
    using K = MenuAction::Kind;
    emit(K::Click);
    const int id = w.id;
    if (const int world = worldOf(id); world >= 0) {
        switch (partOf(id)) {
        case kCardPart: selectedWorld_ = world; break;
        case kPlayPart: emit(K::Play, world); break;
        case kRenamePart:
            if (world < static_cast<int>(m.worlds.size()))
                editName(m.worlds[static_cast<std::size_t>(world)].name, world);
            break;
        default:
            deleteWorld_ = world;
            emit(K::Delete, -1 - deleteWorld_); // asks; the app opens the dialog with the name
        }
        return;
    }
    if (id >= kMusic && id < kMusic + 3) {
        const float k = std::clamp((px - w.box.x) / std::max(1.0f, w.box.w), 0.0f, 1.0f);
        emit(K::Volume, id - kMusic, static_cast<int>(std::lround(k * 20.0f)) * 5);
        return;
    }
    switch (id) {
    case kContinue: emit(m.firstLaunch ? K::Begin : K::Continue); break;
    case kWorlds: emit(K::Worlds); break;
    case kSettings:
    case kPauseSettings: emit(K::Settings); break;
    case kQuit:
    case kPauseQuit: emit(K::Quit); break;
    case kBack:
    case kErrorBack:
    case kDone:
    case kKeep: back(); break;
    case kCancel:
        fieldOpen_ = false;
        back();
        break;
    case kNewCard: emit(K::NewWorld); break;
    case kFreeBuild: freeBuild_ = !freeBuild_; break;
    case kCreate: emit(K::Create, freeBuild_ ? 1 : 0, 0, field_); break;
    case kConfirmDelete: emit(K::Delete, deleteWorld_); break;
    case kMute: emit(K::Mute); break;
    case kFullscreen: emit(K::Fullscreen); break;
    case kUiScale:
        if (m.profile != nullptr) emit(K::UiScale, (m.profile->uiScale + 1) % kUiScaleCount);
        break;
    case kReduceMotion: emit(K::ReduceMotion); break;
    case kGrid: emit(K::Grid); break;
    case kVsync: emit(K::Vsync); break;
    case kChatty: emit(K::Chatter, 1); break;
    case kQuiet: emit(K::Chatter, 0); break;
    case kReplay: emit(K::ReplayTour); break;
    case kResume: emit(K::Resume); break;
    case kPostcards:
    case kFolder: emit(K::OpenPostcards); break;
    case kBackToWorlds: emit(K::BackToWorlds); break;
    case kSkipTour: emit(K::SkipTour); break;
    case kFramePrev: emit(K::FramePrev); break;
    case kFrameNext: emit(K::FrameNext); break;
    case kCaption: emit(K::Caption); break;
    case kHideBar: emit(K::HideBar); break;
    case kTake: emit(K::TakePostcard); break;
    case kClosePhoto: emit(K::ClosePhoto); break;
    default: break;
    }
}

void Menus::update(const UiInput& in, const MenuModel& m, const Font& font, Vec2 screen, float s,
                   float dt) {
    scale_ = s;
    screen_ = screen;
    const bool moved = in.x != pointer_.x || in.y != pointer_.y;
    pointer_ = {in.x, in.y};
    pageT_ = approach(pageT_, page() != Page::None, dt);
    // The photo bar wakes with the pointer and fades after a while without it.
    barIdle_ = moved ? 0.0f : barIdle_ + dt;
    barT_ = approach(barT_, m.photo && !barHidden_ && barIdle_ < theme::kBarFadeAfter, dt);
    layout(m, font, s);
    if (const auto ids = static_cast<std::size_t>(worldId(static_cast<int>(m.worlds.size()), {}));
        hover_.size() != ids)
        hover_.assign(ids, 0.0f);

    overUi_ = false;
    int hovered = 0;
    if (in.inside && !in.blocked) {
        for (const Box& b : panels_)
            if (b.contains(in.x, in.y)) overUi_ = true;
        if (page() == Page::Pause || page() == Page::Title || page() == Page::Worlds ||
            page() == Page::Settings || page() == Page::NewWorld || page() == Page::Delete ||
            page() == Page::LoadError)
            overUi_ = true; // a page covers the world
        for (auto it = widgets_.rbegin(); it != widgets_.rend(); ++it)
            if (it->enabled && it->box.contains(in.x, in.y)) {
                hovered = it->id;
                overUi_ = true;
                break;
            }
    }
    if (hovered != hovered_ && hovered != 0) {
        emit(MenuAction::Kind::Hover);
        if (worldOf(hovered) >= 0) selectedWorld_ = worldOf(hovered);
    }
    hovered_ = hovered;
    if (in.pressed && hovered != 0) {
        active_ = hovered;
        focus_ = 0; // the pointer takes over from the keyboard
        if (const Widget* w = find(hovered); w != nullptr && w->kind == Kind::Slider) {
            dragging_ = hovered;
            activate(*w, m, in.x);
        }
    }
    if (dragging_ != 0 && !in.released && moved)
        if (const Widget* w = find(dragging_); w != nullptr) {
            const float k = std::clamp((in.x - w->box.x) / std::max(1.0f, w->box.w), 0.0f, 1.0f);
            emit(MenuAction::Kind::Volume, dragging_ - kMusic,
                 static_cast<int>(std::lround(k * 20.0f)) * 5);
        }
    if (in.released) {
        if (active_ != 0 && active_ == hovered && dragging_ == 0)
            if (const Widget* w = find(active_); w != nullptr) activate(*w, m, in.x);
        active_ = 0;
        dragging_ = 0;
    }
    if (in.wheel != 0 && page() == Page::Settings && settingsScrollable_ && in.inside)
        settingsScroll_ =
            std::clamp(settingsScroll_ + (in.wheel > 0 ? -1 : 1), 0, settingsScrollMax_);
    if (in.wheel != 0 && page() == Page::Worlds && in.inside) {
        worldsScroll_ += in.wheel > 0 ? -1 : 1;
        worldsScroll_ = std::clamp(worldsScroll_, 0, std::max(0, worldsTotalRows_ - worldsRows_));
    }
    for (std::size_t i = 1; i < hover_.size(); ++i) {
        const int id = static_cast<int>(i);
        hover_[i] = approach(hover_[i], id == hovered_ || id == focus_, dt);
    }
}

void Menus::layout(const MenuModel& m, const Font& font, float s) {
    widgets_.clear();
    panels_.clear();
    fullGlass_ = {};
    heading_ = {};
    body_ = {};
    headingBox_ = bodyBox_ = logoBox_ = coachBox_ = barBox_ = {};
    switch (page()) {
    case Page::None: break;
    case Page::Title: layoutTitle(m, s); break;
    case Page::Worlds: layoutWorlds(m, font, s); break;
    case Page::NewWorld:
    case Page::Delete:
    case Page::LoadError: layoutDialog(m, font, s); break;
    case Page::Settings: layoutSettings(m, font, s); break;
    case Page::Pause: layoutPause(font, s); break;
    }
    if (page() == Page::None && !m.coach.empty()) layoutCoach(m, font, s);
    if (page() == Page::None && m.photo && barT_ > 0) layoutBar(m, font, s);
}

void Menus::layoutTitle(const MenuModel& m, float s) {
    const float pad = theme::kPanelPad * s * 1.5f;
    const float bh = theme::kMenuButtonH * s;
    const float gap = theme::kGap * s * 1.25f;
    const float w = std::min(theme::kMenuW * s, screen_.x - 2 * theme::kMargin * s);
    // The logo at a whole number of pixels per art pixel, as large as the panel allows.
    const float logoScale = std::max(
        1.0f,
        std::floor(std::min(theme::kLogoScale * s, (w - 2 * pad) / std::max(1.0f, m.logo.w))));
    const float logoH = m.logo.h * logoScale;
    const int buttons = m.firstLaunch ? 3 : 4;
    const float h = 2 * pad + logoH + gap * 2 + static_cast<float>(buttons) * (bh + gap) - gap;
    // Left of centre, so the corner shows beside it (§6.5).
    const float x = std::round(std::max(theme::kMargin * s, screen_.x * 0.22f - w * 0.5f));
    const float y = std::round((screen_.y - h) * 0.5f);
    panels_.push_back({x, y, w, h});
    logoBox_ = {x + pad, y + pad, w - 2 * pad, logoH};
    float by = y + pad + logoH + gap * 2;
    const auto button = [&](int id, std::string_view label) {
        add(id, Kind::Button, {x + pad, by, w - 2 * pad, bh}, label);
        by += bh + gap;
    };
    headingText_ = std::vformat(strings::kContinue, std::make_format_args(m.continueName));
    button(kContinue, m.firstLaunch ? strings::kBegin : std::string_view(headingText_));
    if (!m.firstLaunch) button(kWorlds, strings::kWorldsButton);
    button(kSettings, strings::kSettings);
    button(kQuit, strings::kQuit);
}

void Menus::layoutWorlds(const MenuModel& m, const Font& font, float s) {
    const float margin = theme::kMargin * s * 2;
    const float pad = theme::kPanelPad * s * 1.5f;
    const float gap = theme::kGap * s * 2;
    const Box panel{margin, margin, screen_.x - 2 * margin, screen_.y - 2 * margin};
    panels_.push_back(panel);
    heading_ = strings::kYourWorlds;
    headingBox_ = {panel.x + pad, panel.y + pad, panel.w - 2 * pad, font.lineHeight(Face::Title)};
    const float backW = font.measure(Face::Body, strings::kBack) +
                        font.measure(Face::Body, strings::kKeyEsc) + 7 * theme::kGap * s;
    Widget& b =
        add(kBack, Kind::Button,
            {panel.x + panel.w - pad - backW, panel.y + pad * 0.6f, backW, theme::kTipH * s},
            strings::kBack);
    b.value = strings::kKeyEsc;
    // A grid of cards, the newest first, then the dashed "New world" card.
    const float cw = theme::kCardW * s;
    const float thumbH = theme::kCardThumbH * s;
    const float lh = font.lineHeight(Face::Body);
    const float ch = thumbH + theme::kGap * s + font.lineHeight(Face::Title) + lh +
                     theme::kTipH * s + theme::kGap * s * 2;
    const float top = headingBox_.y + headingBox_.h + gap;
    const int cols = std::max(1, static_cast<int>((panel.w - 2 * pad + gap) / (cw + gap)));
    const int count = static_cast<int>(m.worlds.size()) + 1;
    worldsTotalRows_ = (count + cols - 1) / cols;
    worldsRows_ = std::max(1, static_cast<int>((panel.y + panel.h - pad - top + gap) / (ch + gap)));
    worldsScroll_ = std::clamp(worldsScroll_, 0, std::max(0, worldsTotalRows_ - worldsRows_));
    const float used = static_cast<float>(std::min(cols, count)) * (cw + gap) - gap;
    const float x0 = std::round(panel.x + (panel.w - used) * 0.5f);
    nameCut_.resize(m.worlds.size());
    for (int i = worldsScroll_ * cols; i < count && i < (worldsScroll_ + worldsRows_) * cols; ++i) {
        const int row = i / cols - worldsScroll_;
        const Box card{x0 + static_cast<float>(i % cols) * (cw + gap),
                       top + static_cast<float>(row) * (ch + gap), cw, ch};
        if (i == count - 1) {
            add(kNewCard, Kind::NewCard, card, strings::kNewWorld).icon = theme::icon::kPlus;
            continue;
        }
        const MenuWorld& world = m.worlds[static_cast<std::size_t>(i)];
        Widget& c = add(worldId(i, kCardPart), Kind::Card, card, world.name);
        c.value = world.detail;
        c.on = selectedWorld_ == i;
        c.enabled = true;
        if (selectedWorld_ != i || (fieldOpen_ && fieldWorld_ == i)) continue;
        // Play, rename and delete on the selected card.
        const float bh = theme::kTipH * s;
        const float by = card.y + card.h - bh - theme::kGap * s;
        const float ix = card.x + card.w - theme::kGap * s - 2 * bh - theme::kGap * s * 0.5f;
        Widget& play = add(worldId(i, kPlayPart), Kind::Button,
                           {card.x + theme::kGap * s, by, ix - card.x - 2 * theme::kGap * s, bh},
                           strings::kPlay);
        play.icon = theme::icon::kPlay; // a world that cannot be opened says so when played
        Widget& ren = add(worldId(i, kRenamePart), Kind::Icon, {ix, by, bh, bh}, strings::kRename);
        ren.icon = theme::icon::kPencil;
        ren.enabled = world.readable;
        add(worldId(i, kDeletePart), Kind::Icon, {ix + bh + theme::kGap * s * 0.5f, by, bh, bh},
            strings::kDelete)
            .icon = theme::icon::kTrash;
    }
    if (fieldOpen_ && fieldWorld_ >= 0)
        if (const Widget* c = find(worldId(fieldWorld_, kCardPart)); c != nullptr)
            add(kField, Kind::Field,
                {c->box.x + theme::kGap * s, c->box.y + thumbH + theme::kGap * s,
                 c->box.w - 2 * theme::kGap * s, theme::kFieldH * s});
}

void Menus::layoutDialog(const MenuModel& m, const Font& font, float s) {
    const float pad = theme::kPanelPad * s * 1.5f;
    const float w = std::min(theme::kDialogW * s, screen_.x - 2 * theme::kMargin * s);
    const float bh = theme::kMenuButtonH * s * 0.85f;
    const float lh = font.lineHeight(Face::Body);
    const float gap = theme::kGap * s * 1.5f;
    float h = 2 * pad + font.lineHeight(Face::Title) + gap + bh;
    switch (page()) {
    case Page::NewWorld:
        heading_ = strings::kNameYourWorld;
        body_ = strings::kFreeBuildText;
        h += theme::kFieldH * s + lh + gap + theme::kRowH * s +
             static_cast<float>(wrapLines(font, Face::Body, body_, w - 2 * pad, 3)) * lh + gap;
        break;
    case Page::Delete:
        headingText_ = std::vformat(strings::kDeleteTitle, std::make_format_args(m.deleteName));
        heading_ = headingText_;
        body_ = strings::kDeleteText;
        h += static_cast<float>(wrapLines(font, Face::Body, body_, w - 2 * pad, 4)) * lh + gap;
        break;
    default:
        heading_ = strings::kCouldNotOpen;
        body_ = strings::kCouldNotOpenText;
        h += static_cast<float>(wrapLines(font, Face::Body, body_, w - 2 * pad, 3)) * lh + gap;
        break;
    }
    const Box panel{std::round((screen_.x - w) * 0.5f), std::round((screen_.y - h) * 0.5f), w, h};
    panels_.push_back(panel);
    fullGlass_ = {0, 0, screen_.x, screen_.y};
    headingBox_ = {panel.x + pad, panel.y + pad, w - 2 * pad, font.lineHeight(Face::Title)};
    float y = headingBox_.y + headingBox_.h + gap;
    if (page() == Page::NewWorld) {
        add(kField, Kind::Field, {panel.x + pad, y, w - 2 * pad, theme::kFieldH * s});
        y += theme::kFieldH * s + lh + gap;
        Widget& t = add(kFreeBuild, Kind::Toggle, {panel.x + pad, y, w - 2 * pad, theme::kRowH * s},
                        strings::kFreeBuild);
        t.on = freeBuild_;
        t.value = freeBuild_ ? strings::kOn : strings::kOff;
        y += theme::kRowH * s;
    }
    const int lines = page() == Page::Delete ? 4 : 3;
    bodyBox_ = {panel.x + pad, y, w - 2 * pad,
                static_cast<float>(wrapLines(font, Face::Body, body_, w - 2 * pad, lines)) * lh};
    const float by = panel.y + panel.h - pad - bh;
    const float bw = (w - 2 * pad - gap) * 0.5f;
    switch (page()) {
    case Page::NewWorld:
        add(kCancel, Kind::Button, {panel.x + pad, by, bw, bh}, strings::kCancel);
        add(kCreate, Kind::Button, {panel.x + pad + bw + gap, by, bw, bh}, strings::kCreate).on =
            true;
        break;
    case Page::Delete:
        // Keep it is the default (Enter); Delete is the quiet, red one.
        add(kKeep, Kind::Button, {panel.x + pad, by, bw, bh}, strings::kKeepIt).on = true;
        add(kConfirmDelete, Kind::Danger, {panel.x + pad + bw + gap, by, bw, bh}, strings::kDelete);
        if (focus_ == 0) focus_ = kKeep;
        break;
    default:
        add(kErrorBack, Kind::Button, {panel.x + pad + bw + gap, by, bw, bh}, strings::kBack);
        break;
    }
}

void Menus::layoutSettings(const MenuModel& m, const Font& font, float s) {
    // The rows as a list in sections, flowed into as many columns as the window has room for
    // (two when they fit, more when the rows do not fit in two), rows a little tighter when
    // that is not enough, and as a last resort one scrolling column: more rows (look and
    // clouds settings) never overlap or fall off the screen at any size.
    const Profile& pr = m.profile != nullptr ? *m.profile : Profile{};
    enum class Row : std::uint8_t {
        Section,
        Volume,
        Mute,
        Fullscreen,
        UiScale,
        ReduceMotion,
        Grid,
        Vsync,
        Chatter,
        Tour
    };
    struct Entry {
        Row row;
        int arg = 0;            // the volume's bus
        std::string_view title; // a section's name
    };
    std::array<Entry, 24> items{};
    std::size_t count = 0;
    const auto put = [&](Row r, int arg = 0, std::string_view title = {}) {
        if (count < items.size()) items[count++] = {r, arg, title};
    };
    put(Row::Section, 0, strings::kSound);
    for (int i = 0; i < 3; ++i) put(Row::Volume, i);
    put(Row::Mute);
    put(Row::Section, 0, strings::kDisplay);
    put(Row::Fullscreen);
    put(Row::UiScale);
    put(Row::ReduceMotion);
    put(Row::Grid);
    put(Row::Vsync);
    if (!m.residentName.empty()) {
        put(Row::Section, 0, m.residentName);
        put(Row::Chatter);
    }
    put(Row::Section, 0, strings::kHelp);
    put(Row::Tour);

    const float margin = theme::kMargin * s;
    const float pad = theme::kPanelPad * s * 1.5f;
    const float lh = font.lineHeight(Face::Body);
    const float gap = theme::kGap * s * 2;
    const float colW = theme::kSettingsColW * s;
    const float sectionH = lh + theme::kGap * s;
    const float bh = theme::kMenuButtonH * s * 0.85f;
    const float chrome = 2 * pad + font.lineHeight(Face::Title) + gap + gap + bh;
    const float availH = std::max(lh, screen_.y - 2 * margin - chrome);
    const int maxCols =
        std::clamp(static_cast<int>((screen_.x - 2 * margin - 2 * pad + gap) / (colW + gap)), 1, 3);

    // Sections are the places a column may break.
    std::array<std::size_t, 12> starts{};
    std::size_t sections = 0;
    for (std::size_t i = 0; i < count; ++i)
        if (items[i].row == Row::Section && sections < starts.size()) starts[sections++] = i;
    const auto heightOf = [&](std::size_t from, std::size_t to, float r) {
        float h = 0;
        for (std::size_t i = from; i < to; ++i) h += items[i].row == Row::Section ? sectionH : r;
        return h;
    };
    const auto sectionEnd = [&](std::size_t k) { return k + 1 < sections ? starts[k + 1] : count; };
    // The most even split of the sections into `cols` columns: its tallest column and breaks.
    struct Split {
        float tallest = 0;
        std::array<std::size_t, 3> first{}; // the first section of each column
    };
    const auto split = [&](int cols, float r) {
        Split best{1e30f, {}};
        const std::size_t n = sections;
        const auto column = [&](std::size_t a, std::size_t b) {
            return a < b ? heightOf(starts[a], sectionEnd(b - 1), r) : 0.0f;
        };
        if (cols <= 1 || n < 2) return Split{column(0, n), {0, n, n}};
        for (std::size_t b1 = 1; b1 < n; ++b1) {
            if (cols == 2) {
                const float t = std::max(column(0, b1), column(b1, n));
                if (t < best.tallest) best = {t, {0, b1, n}};
                continue;
            }
            for (std::size_t b2 = b1 + 1; b2 < n; ++b2) {
                const float t = std::max({column(0, b1), column(b1, b2), column(b2, n)});
                if (t < best.tallest) best = {t, {0, b1, b2}};
            }
        }
        return best;
    };
    float r = theme::kRowH * s;
    int cols = std::min(2, maxCols);
    Split layoutSplit = split(cols, r);
    for (int c = cols + 1; layoutSplit.tallest > availH && c <= maxCols; ++c) {
        cols = c;
        layoutSplit = split(cols, r);
    }
    const float rMin = std::max(lh * 1.15f, r * 0.75f);
    // Tighter rows, as far as they read well (the headings keep their height, hence a few
    // passes).
    for (int pass = 0; pass < 4 && layoutSplit.tallest > availH && r > rMin; ++pass) {
        r = std::max(rMin, r * availH / layoutSplit.tallest);
        layoutSplit = split(cols, r);
    }
    settingsScrollable_ = layoutSplit.tallest > availH;
    if (settingsScrollable_) {
        cols = 1;
        r = rMin;
        layoutSplit = {availH, {0, sections, sections}};
    }
    const float cw = cols > 1 ? colW : std::min(colW, screen_.x - 2 * margin - 2 * pad);
    const float w = cw * static_cast<float>(cols) + gap * static_cast<float>(cols - 1) + 2 * pad;
    const float bodyH = std::min(layoutSplit.tallest, availH);
    const float h = chrome + bodyH;
    const Box panel{std::round((screen_.x - w) * 0.5f),
                    std::round(std::max(margin, (screen_.y - h) * 0.5f)), w, h};
    panels_.push_back(panel);
    fullGlass_ = {0, 0, screen_.x, screen_.y};
    heading_ = strings::kSettings;
    headingBox_ = {panel.x + pad, panel.y + pad, w - 2 * pad, font.lineHeight(Face::Title)};
    const float colTop = headingBox_.y + headingBox_.h + gap;
    const float colBottom = colTop + bodyH;

    // Scrolling: whole items from the top are skipped; a line says when more lie below.
    std::size_t skip = 0;
    if (settingsScrollable_) {
        std::size_t fit = 0;
        for (float used = sectionH; fit < count; ++fit) { // a line kept for "more below"
            used += items[count - 1 - fit].row == Row::Section ? sectionH : r;
            if (used > bodyH) break;
        }
        settingsScrollMax_ = static_cast<int>(count - fit);
        settingsScroll_ = std::clamp(settingsScroll_, 0, settingsScrollMax_);
        skip = static_cast<std::size_t>(settingsScroll_);
    } else {
        settingsScroll_ = settingsScrollMax_ = 0;
    }

    float x = panel.x + pad;
    float y = colTop;
    int col = 0;
    std::size_t section = 0;
    for (std::size_t i = skip; i < count; ++i) {
        const Entry& it = items[i];
        if (it.row == Row::Section) {
            // A column's first section opens the next column.
            while (section < sections && starts[section] != i) ++section;
            if (col + 1 < cols && section == layoutSplit.first[static_cast<std::size_t>(col + 1)] &&
                section > 0) {
                ++col;
                x += cw + gap;
                y = colTop;
            }
        }
        const float ih = it.row == Row::Section ? sectionH : r;
        if (settingsScrollable_ && y + ih > colBottom - sectionH && i + 1 < count) {
            Widget& more = add(0, Kind::Link, {x, y, cw, sectionH}, strings::kMoreSettings);
            more.enabled = false;
            more.on = true;
            break;
        }
        const auto toggle = [&](int id, std::string_view label, bool on, std::string_view key) {
            Widget& t = add(id, Kind::Toggle, {x, y, cw, r}, label);
            t.on = on;
            t.value = key;
        };
        const auto label = [&](std::string_view text, float share) {
            Widget& lab = add(0, Kind::Link, {x, y, cw * share, r}, text);
            lab.enabled = false;
            lab.on = true; // drawn as a row label
        };
        switch (it.row) {
        case Row::Section: {
            Widget& t = add(0, Kind::Link, {x, y, cw, sectionH}, it.title);
            t.enabled = false;
            break;
        }
        case Row::Volume: {
            static constexpr std::string_view kVolNames[] = {strings::kMusic, strings::kEffects,
                                                             strings::kAmbience};
            const int vols[] = {pr.music, pr.effects, pr.ambience};
            const auto k = static_cast<std::size_t>(it.arg);
            volumeText_[k] = std::to_string(vols[k]);
            Widget& sl = add(kMusic + it.arg, Kind::Slider,
                             {x + cw - theme::kSliderW * s - font.measure(Face::Body, "100") -
                                  theme::kGap * s * 2,
                              y, theme::kSliderW * s, r},
                             kVolNames[k]);
            sl.amount = static_cast<float>(vols[k]) / 100.0f;
            sl.rowX = x;
            sl.value = volumeText_[k];
            break;
        }
        case Row::Mute: toggle(kMute, strings::kMuteAll, pr.muted, strings::kKeyMute); break;
        case Row::Fullscreen:
            toggle(kFullscreen, strings::kFullscreen, m.fullscreen, strings::kKeyFullscreen);
            break;
        case Row::UiScale: {
            const int percent = static_cast<int>(
                std::lround(kUiScales[std::clamp(pr.uiScale, 0, kUiScaleCount - 1)] * 100.0f));
            scaleText_ = pr.uiScale <= 0
                             ? std::string(strings::kAuto)
                             : std::vformat(strings::kPercent, std::make_format_args(percent));
            Widget& sc = add(kUiScale, Kind::Choice, {x, y, cw, r}, strings::kInterfaceSize);
            sc.value = scaleText_;
            break;
        }
        case Row::ReduceMotion:
            toggle(kReduceMotion, strings::kReduceMotion, pr.reduceMotion, {});
            break;
        case Row::Grid: toggle(kGrid, strings::kShowGrid, pr.grid, strings::kKeyGrid); break;
        case Row::Vsync: toggle(kVsync, strings::kVsync, pr.vsync, {}); break;
        case Row::Chatter: {
            label(strings::kChatter, 0.4f);
            const float chip = (cw * 0.6f - theme::kGap * s) * 0.5f;
            add(kChatty, Kind::Button, {x + cw - 2 * chip - theme::kGap * s, y, chip, r},
                strings::kChatty)
                .on = pr.chatty;
            add(kQuiet, Kind::Button, {x + cw - chip, y, chip, r}, strings::kQuiet).on = !pr.chatty;
            break;
        }
        case Row::Tour: {
            label(strings::kTourSetting, 0.6f);
            const float rw = font.measure(Face::Body, strings::kReplay) + 4 * theme::kGap * s;
            add(kReplay, Kind::Button, {x + cw - rw, y, rw, r}, strings::kReplay);
            break;
        }
        }
        y += ih;
    }
    const float dw = font.measure(Face::Body, strings::kDone) + 8 * theme::kGap * s;
    add(kDone, Kind::Button, {panel.x + panel.w - pad - dw, panel.y + panel.h - pad - bh, dw, bh},
        strings::kDone)
        .on = true;
}

void Menus::layoutPause(const Font& font, float s) {
    const float pad = theme::kPanelPad * s * 1.5f;
    const float bh = theme::kMenuButtonH * s;
    const float gap = theme::kGap * s * 1.25f;
    const float w = std::min(theme::kMenuW * s, screen_.x - 2 * theme::kMargin * s);
    const float h = 2 * pad + font.lineHeight(Face::Title) + gap * 2 + 5 * (bh + gap) - gap;
    const Box panel{std::round((screen_.x - w) * 0.5f), std::round((screen_.y - h) * 0.5f), w, h};
    panels_.push_back(panel);
    fullGlass_ = {0, 0, screen_.x, screen_.y};
    heading_ = strings::kPaused;
    headingBox_ = {panel.x + pad, panel.y + pad, w - 2 * pad, font.lineHeight(Face::Title)};
    float y = headingBox_.y + headingBox_.h + gap * 2;
    const auto button = [&](int id, std::string_view label) -> Widget& {
        Widget& b = add(id, Kind::Button, {panel.x + pad, y, w - 2 * pad, bh}, label);
        y += bh + gap;
        return b;
    };
    button(kResume, strings::kResume).value = strings::kKeyEsc;
    button(kPauseSettings, strings::kSettings);
    button(kPostcards, strings::kOpenPostcards);
    button(kBackToWorlds, strings::kBackToWorlds);
    button(kPauseQuit, strings::kQuit);
}

void Menus::layoutCoach(const MenuModel& m, const Font& font, float s) {
    const float pad = theme::kToastPad * s;
    const float h = theme::kToastH * s;
    const float skipW = font.measure(Face::Body, strings::kSkipTour) + 3 * theme::kGap * s;
    const float w = std::min(font.measure(Face::Body, m.coach) + skipW + 3 * pad,
                             screen_.x - 2 * theme::kMargin * s);
    coachBox_ = {std::round((screen_.x - w) * 0.5f), m.coachBottom - h, w, h};
    panels_.push_back(coachBox_);
    add(kSkipTour, Kind::Link,
        {coachBox_.x + w - pad * 0.5f - skipW, coachBox_.y + (h - theme::kTipH * s) * 0.5f, skipW,
         theme::kTipH * s},
        strings::kSkipTour);
}

void Menus::layoutBar(const MenuModel& m, const Font& font, float s) {
    const float h = theme::kPhotoBarH * s;
    const float gap = theme::kGap * s;
    const float pad = theme::kGap * s;
    // Segments: ‹ Frame: name › | Caption | Hide bar | Take postcard | folder | close.
    headingText_ = std::vformat(strings::kFrameLabel, std::make_format_args(m.frameName));
    const float bh = h - 2 * pad;
    const auto width = [&](std::string_view label, std::string_view key) {
        return font.measure(Face::Body, label) + font.measure(Face::Body, key) + 5 * gap +
               theme::kIcon * s;
    };
    const float frameW = width(headingText_, strings::kKeyFrame) + (m.frames > 1 ? 2 * bh : 0.0f);
    const float capW = width(strings::kCaption, strings::kKeyCaption);
    const float hideW = width(strings::kHideBar, strings::kKeyHideBar);
    const float takeW = width(strings::kTakePostcard, strings::kKeyTake);
    const float total = frameW + capW + hideW + takeW + 2 * bh + 6 * gap + 2 * pad;
    const float w = std::min(total, screen_.x - 2 * theme::kMargin * s);
    const float bottom = m.barBottom > 0 ? m.barBottom : screen_.y - theme::kMargin * s;
    barBox_ = {std::round((screen_.x - w) * 0.5f), bottom - h, w, h};
    panels_.push_back(barBox_);
    float x = barBox_.x + pad;
    const float y = barBox_.y + pad;
    if (m.frames > 1) {
        add(kFramePrev, Kind::Icon, {x, y, bh, bh}).icon = theme::icon::kChevronLeft;
        x += bh;
    }
    Widget& fr = add(kFrameNext, Kind::Bar, {x, y, frameW - (m.frames > 1 ? 2 * bh : 0.0f), bh},
                     headingText_);
    fr.icon = theme::icon::kFrame;
    fr.value = strings::kKeyFrame;
    fr.enabled = m.frames > 1;
    x += fr.box.w;
    if (m.frames > 1) {
        add(kFrameNext, Kind::Icon, {x, y, bh, bh}).icon = theme::icon::kChevronRight;
        x += bh;
    }
    x += gap;
    const auto seg = [&](int id, std::string_view label, std::string_view key, char32_t icon,
                         float sw) -> Widget& {
        Widget& b = add(id, Kind::Bar, {x, y, sw, bh}, label);
        b.value = key;
        b.icon = icon;
        x += sw + gap;
        return b;
    };
    seg(kCaption, strings::kCaption, strings::kKeyCaption, theme::icon::kType, capW).on = m.caption;
    seg(kHideBar, strings::kHideBar, strings::kKeyHideBar, theme::icon::kEyeOff, hideW);
    seg(kTake, strings::kTakePostcard, strings::kKeyTake, theme::icon::kCamera, takeW).on = true;
    add(kFolder, Kind::Icon, {x, y, bh, bh}, strings::kOpenFolder).icon = theme::icon::kFolderOpen;
    x += bh + gap;
    add(kClosePhoto, Kind::Icon, {x, y, bh, bh}, strings::kClosePhoto).icon = theme::icon::kClose;
}

void Menus::drawField(Painter& p, Box b, float a) const {
    const float s = scale_;
    const Font& f = p.font();
    const float r = theme::kTileRadius * s;
    p.roundRect(b, r, withAlpha(theme::kInset, a * 1.5f));
    p.rim(b, r, theme::kRim * s, withAlpha(theme::kAccentRim, a),
          withAlpha(theme::kAccentRim, a * 0.5f));
    const float pad = theme::kGap * s * 1.5f;
    const float base = b.cy() + f.ascent(Face::Body) * theme::kBaselineCentre;
    // The end of a long name stays in view.
    std::string_view shown = field_;
    while (!shown.empty() && f.measure(Face::Body, shown) > b.w - 3 * pad) {
        std::size_t i = 0;
        (void)nextCodepoint(shown, i);
        shown.remove_prefix(i);
    }
    if (fieldSelected_ && !shown.empty())
        p.roundRect(
            {b.x + pad - s, b.y + b.h * 0.2f, f.measure(Face::Body, shown) + 2 * s, b.h * 0.6f},
            theme::kTipRadius * s * 0.5f, withAlpha(theme::kAccentWash, a * 1.6f));
    p.text(Face::Body, shown, b.x + pad, base, withAlpha(theme::kInk, a));
    const float cx = b.x + pad + f.measure(Face::Body, shown) + s;
    p.roundRect({cx, b.y + b.h * 0.25f, std::max(1.0f, s * 1.5f), b.h * 0.5f}, 0,
                withAlpha(theme::kAccent, a), 0);
    if (!fieldNote_.empty())
        p.text(Face::Body, fieldNote_, b.x,
               b.y + b.h + f.lineHeight(Face::Body) * 0.2f + f.ascent(Face::Body),
               withAlpha(theme::kWarn, a));
}

void Menus::drawWidget(Painter& p, const Widget& w, float a) const {
    const float s = scale_;
    const Font& f = p.font();
    const float h = hoverOf(w.id);
    const float base = w.box.cy() + f.ascent(Face::Body) * theme::kBaselineCentre;
    const SDL_FColor ink = withAlpha(w.enabled ? theme::kInk : theme::kInkMuted, a);
    const SDL_FColor muted = withAlpha(theme::kInkMuted, a);
    const auto chip = [&](std::string_view key, float right) {
        // A shortcut chip at the right end.
        if (key.empty()) return right;
        const float cp = theme::kChipPad * s;
        const float kw = f.measure(Face::Body, key) + 2 * cp;
        const Box c{right - kw, w.box.cy() - (theme::kTipH * s - 2 * cp) * 0.5f, kw,
                    theme::kTipH * s - 2 * cp};
        p.roundRect(c, theme::kChipRadius * s, withAlpha(theme::kChip, a));
        p.text(Face::Body, key, c.x + cp, base, muted);
        return c.x - theme::kGap * s;
    };
    switch (w.kind) {
    case Kind::Button:
    case Kind::Danger:
    case Kind::Bar:
    case Kind::Icon: {
        const float r = std::min(w.box.h * 0.5f, theme::kTileRadius * s * 1.5f);
        if (w.kind != Kind::Bar && w.kind != Kind::Icon) {
            p.roundRect(w.box, r, withAlpha(w.on ? theme::kAccentWash : theme::kInset, a));
            p.rim(w.box, r, theme::kRim * s,
                  withAlpha(w.on ? theme::kAccentRim : theme::kInsetRimTop, a),
                  withAlpha(theme::kInsetRimBottom, a));
        } else if (w.on) {
            p.roundRect(w.box, r, withAlpha(theme::kAccentWash, a));
        }
        if (h > 0) p.roundRect(w.box, r, withAlpha(theme::kHover, a * h));
        if (w.id == focus_)
            p.rim(w.box, r, 2 * theme::kRim * s, withAlpha(theme::kAccentRim, a),
                  withAlpha(theme::kAccentRim, a));
        const SDL_FColor c = w.kind == Kind::Danger ? withAlpha(theme::kWarn, a) : ink;
        if (w.kind == Kind::Icon) {
            p.icon(w.icon, w.box.cx(), w.box.cy(), c);
            break;
        }
        // The label centred (a bar segment's from its left), a shortcut chip at the right end.
        const float chipLeft = chip(w.value, w.box.x + w.box.w - theme::kGap * s * 1.5f);
        const float tw = f.measure(Face::Body, w.label) +
                         (w.icon != 0 ? theme::kIcon * s + theme::kLabelGap * s : 0.0f);
        // Centred in the button, or in what the chip leaves of a narrow one.
        float x = w.kind == Kind::Bar ? w.box.x + theme::kGap * s : w.box.cx() - tw * 0.5f;
        if (w.kind != Kind::Bar && !w.value.empty() && x + tw > chipLeft)
            x = std::max(w.box.x + theme::kGap * s, (w.box.x + chipLeft - tw) * 0.5f);
        if (w.icon != 0) {
            p.icon(w.icon, x + theme::kIcon * s * 0.5f, w.box.cy(), c);
            x += theme::kIcon * s + theme::kLabelGap * s;
        }
        p.text(Face::Body, w.label, x, base, c);
        break;
    }
    case Kind::Link: {
        if (!w.enabled) {
            // A section heading (gold) or a row's label.
            p.text(Face::Body, w.label, w.box.x, w.on ? base : w.box.y + f.ascent(Face::Body),
                   w.on ? ink : withAlpha(theme::kGold, a));
            break;
        }
        const float tw = f.measure(Face::Body, w.label);
        p.text(Face::Body, w.label, w.box.cx() - tw * 0.5f, base,
               withAlpha(h > 0 ? theme::kInk : theme::kAccent, a));
        p.roundRect({w.box.cx() - tw * 0.5f, base + 2 * s, tw, s}, 0,
                    withAlpha(theme::kAccent, a * (0.4f + 0.6f * h)), 0);
        break;
    }
    case Kind::Toggle:
    case Kind::Choice: {
        if (h > 0)
            p.roundRect(w.box, theme::kTileRadius * s, withAlpha(theme::kHover, a * h * 0.6f));
        if (w.id == focus_)
            p.rim(w.box, theme::kTileRadius * s, theme::kRim * s, withAlpha(theme::kAccentRim, a),
                  withAlpha(theme::kAccentRim, a));
        p.text(Face::Body, w.label, w.box.x + theme::kGap * s, base, ink);
        // The state as a pill at the right: on/off for toggles, the value for a choice.
        const std::string_view state =
            w.kind == Kind::Choice ? w.value : (w.on ? strings::kOn : strings::kOff);
        const float pw = std::max(f.measure(Face::Body, state) + 4 * theme::kGap * s, 56 * s);
        const float ph = w.box.h - theme::kGap * s;
        const Box pill{w.box.x + w.box.w - pw - theme::kGap * s * 0.5f, w.box.cy() - ph * 0.5f, pw,
                       ph};
        p.roundRect(
            pill, ph * 0.5f,
            withAlpha(w.on || w.kind == Kind::Choice ? theme::kAccentWash : theme::kInset, a));
        p.rim(pill, ph * 0.5f, theme::kRim * s,
              withAlpha(w.on ? theme::kAccentRim : theme::kInsetRimTop, a),
              withAlpha(theme::kInsetRimBottom, a));
        const float sw = f.measure(Face::Body, state);
        p.text(Face::Body, state, pill.cx() - sw * 0.5f, base,
               w.on || w.kind == Kind::Choice ? ink : muted);
        if (w.kind == Kind::Toggle && !w.value.empty() && w.value != strings::kOn &&
            w.value != strings::kOff)
            chip(w.value, pill.x - theme::kGap * s);
        break;
    }
    case Kind::Slider: {
        // The row: its label at the left, the track, the value at the right.
        p.text(Face::Body, w.label, w.rowX + theme::kGap * s, base, ink);
        if (h > 0) p.roundRect(w.box, w.box.h * 0.5f, withAlpha(theme::kHover, a * h * 0.5f));
        const float th = theme::kSliderTrack * s;
        const Box track{w.box.x, w.box.cy() - th * 0.5f, w.box.w, th};
        p.roundRect(track, th * 0.5f, withAlpha(theme::kInset, a * 2));
        p.roundRect({track.x, track.y, std::max(th, track.w * w.amount), th}, th * 0.5f,
                    withAlpha(theme::kAccent, a));
        const float kr = th * 2.2f;
        const float kx = track.x + track.w * w.amount;
        p.roundRect({kx - kr, w.box.cy() - kr, 2 * kr, 2 * kr}, kr, withAlpha(theme::kInk, a));
        if (w.id == focus_)
            p.rim({kx - kr * 1.6f, w.box.cy() - kr * 1.6f, 3.2f * kr, 3.2f * kr}, kr * 1.6f,
                  theme::kRim * s * 1.5f, withAlpha(theme::kAccentRim, a),
                  withAlpha(theme::kAccentRim, a));
        p.text(Face::Body, w.value, w.box.x + w.box.w + theme::kGap * s * 2, base, ink);
        break;
    }
    case Kind::Card:
    case Kind::NewCard: {
        const float r = theme::kTileRadius * s;
        if (w.kind == Kind::NewCard) {
            // A dashed outline: short rounded dashes along the edges.
            const float dash = 8 * s;
            const SDL_FColor c = withAlpha(theme::kInkMuted, a * (0.5f + 0.5f * h));
            const int across = static_cast<int>((w.box.w - 2 * r) / (2 * dash)) + 1;
            const int down = static_cast<int>((w.box.h - 2 * r) / (2 * dash)) + 1;
            for (int i = 0; i < across; ++i) {
                const float x = w.box.x + r + static_cast<float>(i) * 2 * dash;
                p.roundRect({x, w.box.y, dash, s * 1.5f}, 0, c, 0);
                p.roundRect({x, w.box.y + w.box.h - s * 1.5f, dash, s * 1.5f}, 0, c, 0);
            }
            for (int i = 0; i < down; ++i) {
                const float y = w.box.y + r + static_cast<float>(i) * 2 * dash;
                p.roundRect({w.box.x, y, s * 1.5f, dash}, 0, c, 0);
                p.roundRect({w.box.x + w.box.w - s * 1.5f, y, s * 1.5f, dash}, 0, c, 0);
            }
            if (h > 0) p.roundRect(w.box, r, withAlpha(theme::kHover, a * h * 0.5f));
            p.icon(theme::icon::kPlus, w.box.cx(), w.box.cy() - f.lineHeight(Face::Body) * 0.6f,
                   ink);
            const float tw = f.measure(Face::Body, w.label);
            p.text(Face::Body, w.label, w.box.cx() - tw * 0.5f,
                   w.box.cy() + f.lineHeight(Face::Body) * 0.6f + f.ascent(Face::Body) * 0.5f, ink);
            break;
        }
        p.roundRect(w.box, r, withAlpha(theme::kInset, a * (w.on ? 2.0f : 1.0f)));
        p.rim(w.box, r, theme::kRim * s,
              withAlpha(w.on ? theme::kAccentRim : theme::kInsetRimTop, a),
              withAlpha(theme::kInsetRimBottom, a));
        if (h > 0) p.roundRect(w.box, r, withAlpha(theme::kHover, a * h * 0.4f));
        const float in = theme::kGap * s;
        const Box thumb{w.box.x + in, w.box.y + in, w.box.w - 2 * in, theme::kCardThumbH * s};
        p.roundRect(thumb, r * 0.6f, withAlpha(theme::kGlassFallback, a));
        break;
    }
    case Kind::Field: drawField(p, w.box, a); break;
    }
}

void Menus::draw(Painter& p, const MenuModel& m) const {
    const float s = scale_;
    const Font& f = p.font();
    const float a = page() == Page::None ? 1.0f : std::max(0.2f, pageT_);
    if (fullGlass_.w > 0) {
        // The world blurs behind the glass of a pause or dialog.
        p.glass(fullGlass_, 0, a, theme::kGlassVeil);
        p.endGlass();
        p.endLayer();
    }
    for (const Box& b : panels_) {
        const bool bar = b.y == barBox_.y && b.w == barBox_.w && barBox_.w > 0;
        p.glass(b, bar || b.y == coachBox_.y ? b.h * 0.5f : theme::kPanelRadius * s * 1.25f,
                bar ? barT_ : a, theme::kGlass);
    }
    p.endGlass();
    if (logoBox_.w > 0 && m.logo.texture != nullptr) {
        const float k =
            std::max(1.0f, std::floor(std::min(theme::kLogoScale * s, logoBox_.w / m.logo.w)));
        p.thumbnail(m.logo, logoBox_, k, a);
    }
    if (!heading_.empty())
        p.text(Face::Title, heading_, headingBox_.x, headingBox_.y + f.ascent(Face::Title),
               withAlpha(theme::kInk, a));
    if (!body_.empty())
        p.wrapped(Face::Body, body_, bodyBox_.x, bodyBox_.y, bodyBox_.w, 4,
                  withAlpha(theme::kInkMuted, a));
    if (coachBox_.w > 0) {
        const float pad = theme::kToastPad * s;
        p.icon(theme::icon::kSparkle, coachBox_.x + pad, coachBox_.cy(),
               withAlpha(theme::kAccent, a));
        p.text(Face::Body, m.coach, coachBox_.x + pad + theme::kIcon * s,
               coachBox_.cy() + f.ascent(Face::Body) * theme::kBaselineCentre,
               withAlpha(theme::kInk, a));
    }
    for (const Widget& w : widgets_) {
        const float wa =
            barBox_.w > 0 && w.box.y >= barBox_.y && w.box.y < barBox_.y + barBox_.h ? barT_ : a;
        drawWidget(p, w, wa);
        if (w.kind == Kind::Card) {
            // The card's thumbnail, name and detail.
            const auto i = static_cast<std::size_t>(worldOf(w.id));
            const float in = theme::kGap * s;
            const Box thumb{w.box.x + in, w.box.y + in, w.box.w - 2 * in, theme::kCardThumbH * s};
            if (i < m.worlds.size() && m.worlds[i].thumb.texture != nullptr)
                p.thumbnail(m.worlds[i].thumb, thumb, 1.0f, wa);
            if (fieldOpen_ && fieldWorld_ == static_cast<int>(i)) continue;
            const std::string_view name =
                i < nameCut_.size() ? elide(f, Face::Title, w.label, w.box.w - 2 * in, nameCut_[i])
                                    : w.label;
            float y = thumb.y + thumb.h + in;
            p.text(Face::Title, name, w.box.x + in, y + f.ascent(Face::Title),
                   withAlpha(theme::kInk, wa));
            y += f.lineHeight(Face::Title);
            p.text(Face::Body, w.value, w.box.x + in, y + f.ascent(Face::Body),
                   withAlpha(theme::kInkMuted, wa));
        }
    }
    p.endLayer();
}

} // namespace lc
