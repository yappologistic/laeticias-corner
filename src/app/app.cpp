#include "app/app.hpp"

#include "app/app_impl.hpp"
#include "audio/decode.hpp"
#include "audio/wav.hpp"
#include "core/save.hpp"
#include "core/starter.hpp"
#include "render/sprites.hpp"
#include "ui/painter.hpp"
#include "ui/strings.hpp"
#include "ui/theme.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdlib>
#include <format>

namespace lc {
namespace {

// Sound files the engine plays besides the per-item/terrain/visitor sounds in the catalog.
namespace sfx {
constexpr std::string_view kRemove = "sfx/remove.wav";
constexpr std::string_view kRotate = "sfx/rotate.wav";
constexpr std::string_view kInvalid = "sfx/invalid.wav";
constexpr std::string_view kUndo = "sfx/undo.wav";
constexpr std::string_view kRedo = "sfx/redo.wav";
constexpr std::string_view kHover = "sfx/ui_hover.wav";
constexpr std::string_view kClick = "sfx/ui_click.wav";
constexpr std::string_view kOpen = "sfx/ui_open.wav";
constexpr std::string_view kClose = "sfx/ui_close.wav";
constexpr std::string_view kShutter = "sfx/shutter.wav";
constexpr std::string_view kDiscover = "sfx/discover.wav";
constexpr std::string_view kPaint = "sfx/paint.wav";
} // namespace sfx

constexpr std::string_view kSaveFile = "corner.json";
constexpr std::string_view kPhotoDir = "photos";
constexpr int kBadSaveCopies = 3;    // corner.json.bad1 (newest) .. bad3
constexpr float kWarnSeconds = 1.6f; // how long a refusal stays in the hint line
constexpr float kClickSlop = 4.0f;   // px a click may move and still count as a click
constexpr int kHeadlessW = 1280;     // headless window when --size is not given
constexpr int kHeadlessH = 800;
constexpr int kAudioFramesPerStep = kMixRate / 60; // capture: one simulation step of sound

// Owns SDL initialisation so it outlives every other SDL object in App.
struct SdlSession {
    bool ok = false;
    SdlSession(bool headless, bool gpu) {
        if (headless) {
            // Override any environment so automated runs can never reach the desktop or speakers.
            // The dummy video driver suffices for software rendering; offscreen (EGL, still no
            // window) is only needed when a GPU renderer is requested.
            if (!SDL_SetHintWithPriority(SDL_HINT_VIDEO_DRIVER, gpu ? "offscreen" : "dummy",
                                         SDL_HINT_OVERRIDE) ||
                !SDL_SetHintWithPriority(SDL_HINT_AUDIO_DRIVER, "dummy", SDL_HINT_OVERRIDE)) {
                SDL_Log("cannot force headless drivers: %s", SDL_GetError());
                return;
            }
        }
        ok = SDL_Init(SDL_INIT_VIDEO | SDL_INIT_AUDIO);
        if (!ok) SDL_Log("SDL_Init failed: %s", SDL_GetError());
    }
    ~SdlSession() { SDL_Quit(); }
    SdlSession(const SdlSession&) = delete;
    SdlSession& operator=(const SdlSession&) = delete;
};

fs::path findAssets(const Options& o) {
    if (o.assetsDir) return *o.assetsDir;
    if (const char* env = std::getenv("LAETICIA_ASSETS_DIR")) return env;
    if (const char* base = SDL_GetBasePath()) {
        const fs::path p = fs::path(base) / "assets";
        if (fs::exists(p / "catalog.json")) return p;
    }
    return LC_SOURCE_ASSETS_DIR;
}

fs::path findSaveDir(const Options& o) {
    if (o.saveDir) return *o.saveDir;
    if (const char* env = std::getenv("LAETICIA_SAVE_DIR")) return env;
    if (char* pref = SDL_GetPrefPath("Laeticia", "laeticias-corner")) {
        const fs::path p = pref;
        SDL_free(pref);
        return p;
    }
    return fs::current_path() / "save";
}

std::string_view placeWarning(PlaceResult r) {
    switch (r) {
    case PlaceResult::Ok: return {};
    case PlaceResult::OutOfBounds: return strings::kWarnEdge;
    case PlaceResult::Occupied: return strings::kWarnOccupied;
    case PlaceResult::NeedsLand: return strings::kWarnLand;
    case PlaceResult::NeedsWater: return strings::kWarnWater;
    }
    return {};
}

// 4-connected walk from a (exclusive) to b (inclusive), so drags never leave diagonal gaps.
template <typename F>
void walkLine(TilePos a, TilePos b, F&& visit) {
    const int tx = b.x - a.x;
    const int ty = b.y - a.y;
    TilePos c = a;
    while (c != b) {
        const int rx = b.x - c.x;
        const int ry = b.y - c.y;
        if (std::abs(rx) * std::abs(ty) >= std::abs(ry) * std::abs(tx) && rx != 0)
            c.x += rx > 0 ? 1 : -1;
        else
            c.y += ry > 0 ? 1 : -1;
        visit(c);
    }
}

bool oneTile(const ItemDef& def) {
    return def.footprintW == 1 && def.footprintH == 1;
}

} // namespace

App::App(const Options& o, Catalog cat, fs::path assets)
    : opts_(o), assets_(std::move(assets)), saveDir_(findSaveDir(o)), cat_(std::move(cat)),
      world_(cat_), visitors_(cat_),
      rng_(o.seed.value_or(o.headless
                               ? 1
                               : static_cast<std::uint64_t>(
                                     std::chrono::steady_clock::now().time_since_epoch().count()))),
      camera_(cat_.iso(), world_.landBounds(), 0) {}

bool App::createWindow() {
    SDL_WindowFlags flags = SDL_WINDOW_RESIZABLE | SDL_WINDOW_HIGH_PIXEL_DENSITY;
    std::optional<WindowRect> place;
    if (opts_.size) {
        place = WindowRect{0, 0, opts_.size->w, opts_.size->h};
    } else if (opts_.headless) {
        place = WindowRect{0, 0, kHeadlessW, kHeadlessH};
    } else {
        // Remembered placement if a display still shows it, else most of the display the
        // pointer is on.
        int count = 0;
        const SdlBuffer ids{SDL_GetDisplays(&count)};
        std::vector<WindowRect> usable;
        for (int i = 0; i < count; ++i) {
            SDL_Rect r;
            if (SDL_GetDisplayUsableBounds(static_cast<SDL_DisplayID*>(ids.get())[i], &r))
                usable.push_back({r.x, r.y, r.w, r.h});
        }
        if (auto text = readTextFile(saveDir_ / kWindowFile)) {
            if (const auto s = parseWindowState(*text)) {
                windowState_ = *s;
                place = restoreWindow(s->windowed, usable);
            }
        }
        if (!place) {
            float mx = 0;
            float my = 0;
            (void)SDL_GetGlobalMouseState(&mx, &my);
            const SDL_Point at{static_cast<int>(mx), static_cast<int>(my)};
            SDL_DisplayID d = SDL_GetDisplayForPoint(&at);
            if (d == 0) d = SDL_GetPrimaryDisplay();
            SDL_Rect r{0, 0, kHeadlessW, kHeadlessH};
            if (d == 0 || !SDL_GetDisplayUsableBounds(d, &r))
                SDL_Log("display bounds unavailable: %s", SDL_GetError());
            place = defaultWindow({r.x, r.y, r.w, r.h});
        }
        windowState_.windowed = *place;
    }
    window_.reset(SDL_CreateWindow(std::string(strings::kWindowTitle).c_str(), place->w, place->h,
                                   flags | (opts_.headless ? 0 : SDL_WINDOW_HIDDEN)));
    if (!window_) {
        SDL_Log("cannot create window: %s", SDL_GetError());
        return false;
    }
    if (!opts_.headless) {
        if (!opts_.size && !SDL_SetWindowPosition(window_.get(), place->x, place->y))
            SDL_Log("window position: %s", SDL_GetError());
        if (windowState_.fullscreen && !SDL_SetWindowFullscreen(window_.get(), true))
            SDL_Log("fullscreen: %s", SDL_GetError());
        if (!SDL_ShowWindow(window_.get())) SDL_Log("show window: %s", SDL_GetError());
    }
    return true;
}

void App::rememberWindow() {
    if (opts_.headless || opts_.size || !window_) return;
    if (auto r = writeFileAtomic(saveDir_ / kWindowFile, serializeWindowState(windowState_)); !r)
        SDL_Log("window: %s", r.error().c_str());
}

bool App::init() {
    if (!createWindow()) return false;
    // Headless runs default to the software renderer so screenshots are reproducible anywhere.
    const std::string driver =
        !opts_.renderer.empty() ? opts_.renderer : (opts_.headless ? "software" : "");
    renderer_.reset(SDL_CreateRenderer(window_.get(), driver.empty() ? nullptr : driver.c_str()));
    if (!renderer_) {
        SDL_Log("cannot create renderer: %s", SDL_GetError());
        return false;
    }
    if (!opts_.headless && !SDL_SetRenderVSync(renderer_.get(), 1))
        SDL_Log("vsync unavailable: %s", SDL_GetError());
    if (!SDL_GetRenderOutputSize(renderer_.get(), &pixelW_, &pixelH_)) return false;
    density_ = SDL_GetWindowPixelDensity(window_.get());
    if (density_ <= 0) density_ = 1;

    atlas_ = std::make_unique<Atlas>(renderer_.get(), assets_, cat_.iso());
    scene_ = std::make_unique<Scene>(renderer_.get(), *atlas_, cat_);
    uiBatch_ = std::make_unique<Batch>(renderer_.get());
    blur_ = std::make_unique<Blur>(renderer_.get());
    buildThumbs();
    if (!font_.load(assets_ / "fonts")) return false;

    mixer_.load(assets_ / "audio", cat_.audio);
    if (opts_.audioOut)
        mixer_.startCapture();
    else
        (void)mixer_.open();

    if (!opts_.bench) loadOrStart();
    camera_.setLand(world_.landBounds(), scene_->cliffDepth());
    return true;
}

void App::buildThumbs() {
    const SpriteTables& t = scene_->sprites();
    const auto spriteOf = [&](Thumb kind, int i) { return atlas_->sprite(thumbnail(t, kind, i)); };
    for (std::size_t i = 0; i < cat_.terrain.size(); ++i)
        thumbs_.terrain.push_back(spriteOf(Thumb::Terrain, static_cast<int>(i)));
    for (std::size_t i = 0; i < cat_.items.size(); ++i)
        thumbs_.items.push_back(spriteOf(Thumb::Item, static_cast<int>(i)));
    for (std::size_t i = 0; i < cat_.visitors.size(); ++i)
        thumbs_.visitors.push_back(spriteOf(Thumb::Visitor, static_cast<int>(i)));
    thumbs_.placeholder = atlas_->sprite(t.placeholder);
    thumbs_.tileW = cat_.iso().tileW();
}

void App::loadOrStart() {
    const fs::path file = saveDir_ / kSaveFile;
    std::error_code ec;
    if (fs::exists(file, ec)) {
        auto text = readTextFile(file);
        auto data = text ? deserialize(*text, cat_) : std::unexpected(text.error());
        if (data) {
            for (const auto& w : data->warnings) SDL_Log("save: %s", w.c_str());
            world_ = std::move(data->world);
            clock_.setTime(data->clockTime);
            clock_.setPin(data->pin, false);
            rain_ = data->rain;
            muted_ = data->muted;
            for (const auto& id : data->journal)
                if (const auto v = cat_.findVisitor(id)) visitors_.markSeen(*v);
            // Critters are placed once the camera exists (see run()).
            SDL_Log("save: restored %s", file.string().c_str());
            return;
        }
        // Keep the unreadable file for inspection instead of overwriting it: the newest few
        // bad copies are kept, oldest dropped.
        const auto bad = [&](int n) {
            fs::path p = file;
            p += ".bad" + std::to_string(n);
            return p;
        };
        fs::remove_all(bad(kBadSaveCopies), ec);
        for (int n = kBadSaveCopies - 1; n >= 1; --n)
            if (fs::exists(bad(n), ec)) fs::rename(bad(n), bad(n + 1), ec);
        fs::rename(file, bad(1), ec);
        saveBlocked_ = static_cast<bool>(ec);
        if (ec)
            SDL_Log("save: %s; could not move it aside (%s), starting fresh without saving over it",
                    data.error().c_str(), ec.message().c_str());
        else
            SDL_Log("save: %s; moved aside to %s and starting fresh", data.error().c_str(),
                    bad(1).string().c_str());
    }
    world_ = makeStarterWorld(cat_);
}

bool App::save() {
    SaveData data(world_);
    data.clockTime = clock_.time();
    data.pin = clock_.pin();
    data.rain = rain_;
    data.muted = muted_;
    for (std::size_t v = 0; v < cat_.visitors.size(); ++v)
        if (visitors_.seen(static_cast<int>(v))) data.journal.push_back(cat_.visitors[v].id);
    // Never write over a save that could not be read and could not be moved aside.
    const fs::path file = saveDir_ / kSaveFile;
    auto r = saveBlocked_ ? std::expected<void, std::string>(std::unexpect,
                                                             "an unreadable save is in the way")
                          : writeFileAtomic(file, serialize(data, cat_));
    if (!r) {
        SDL_Log("save: %s", r.error().c_str());
        if (!saveFailing_) hud_.toast(std::string(strings::kToastSaveFailed));
        saveFailing_ = true;
        autosave_.failed();
        return false;
    }
    saveFailing_ = false;
    autosave_.saved();
    return true;
}

bool App::night() const {
    // Dusk and dawn belong to the day: night visitors come out only in the Night phase.
    return clock_.phase() == Phase::Night;
}

TileRect App::activeArea() const {
    const TileRect v = scene_->visibleTiles(camera_, screen(), world_);
    const int m = tuning::kActiveMargin;
    const auto down = [](int a) { return (a >> kChunkShift) << kChunkShift; };
    const auto up = [](int a) { return ((a + kChunk - 1) >> kChunkShift) << kChunkShift; };
    return TileRect{down(v.x0 - m), down(v.y0 - m), up(v.x1 + m), up(v.y1 + m)}.clipped(
        world_.bounds());
}

void App::play(std::string_view file, float gain, bool jitter) {
    const float pitch =
        jitter ? 1.0f + rng_.range(-tuning::kPitchJitter, tuning::kPitchJitter) : 1.0f;
    mixer_.play(mixer_.sfxIndex(file), gain, pitch);
}

void App::setTool(Tool t, int selection) {
    if (editor_.inGroup()) editor_.commit();
    drag_ = drag_ == Drag::Tool ? Drag::None : drag_;
    tool_ = t;
    selection_ = selection;
    variant_ = 0;
}

void App::cycleClock() {
    static constexpr ClockPin kCycle[] = {ClockPin::Day, ClockPin::Dusk, ClockPin::Night,
                                          ClockPin::Dawn, ClockPin::Auto};
    const auto cur = clock_.pin();
    ClockPin next = ClockPin::Day;
    for (std::size_t i = 0; i < std::size(kCycle); ++i)
        if (kCycle[i] == cur) next = kCycle[(i + 1) % std::size(kCycle)];
    clock_.setPin(next, false);
    markDirty();
}

void App::togglePhoto() {
    photo_ = !photo_;
    if (photo_) {
        // Photo mode hides the interface; the player frames the shot, then takes it.
        if (editor_.inGroup()) editor_.commit();
        drag_ = Drag::None;
    } else if (photoSaved_) {
        hud_.toast(std::string(strings::kToastPhoto));
        photoSaved_ = false;
    }
}

void App::capturePhoto() {
    const fs::path dir = saveDir_ / kPhotoDir;
    std::error_code ec;
    fs::create_directories(dir, ec);
    fs::path file;
    for (int n = 1; n < 100000; ++n) {
        file = dir / std::vformat(strings::kPhotoFile, std::make_format_args(n));
        if (!fs::exists(file, ec)) break;
    }
    if (shot(file)) {
        photoSaved_ = true;
        play(sfx::kShutter);
        hud_.flash();
        SDL_Log("photo: saved %s", file.string().c_str());
    } else {
        hud_.toast(std::string(strings::kToastPhotoFailed));
    }
}

bool App::shot(const fs::path& file) {
    SurfacePtr s{SDL_RenderReadPixels(renderer_.get(), nullptr)};
    if (!s) {
        SDL_Log("screenshot: %s", SDL_GetError());
        return false;
    }
    std::error_code ec;
    if (file.has_parent_path()) fs::create_directories(file.parent_path(), ec);
    if (!SDL_SavePNG(s.get(), file.string().c_str())) {
        SDL_Log("screenshot: %s", SDL_GetError());
        return false;
    }
    return true;
}

void App::feedback(std::span<const Op> ops) {
    for (const Op& op : ops) {
        if (op.kind == Op::Kind::Add)
            scene_->onPlaced(op.item, rng_);
        else if (op.kind == Op::Kind::Remove)
            scene_->onRemoved(op.item);
    }
    if (!ops.empty()) markDirty();
}

void App::undoRedo(bool redo) {
    // Undo in the middle of a drag ends the drag: the stroke so far is one step and is undone
    // whole, and nothing more is drawn until the button is pressed again.
    if (drag_ == Drag::Tool) drag_ = Drag::None;
    const auto ops = redo ? editor_.redo(world_) : editor_.undo(world_);
    if (!ops.empty()) play(redo ? sfx::kRedo : sfx::kUndo);
    feedback(ops);
}

void App::zoomBy(int steps, Vec2 px) {
    camera_.zoomTo(camera_.level() + steps, px, screen());
}

void App::frameCamera() {
    const Box s = hud_.safeArea();
    camera_.frame({s.x, s.y, s.x + s.w, s.y + s.h}, screen());
}

void App::handleKey(const SDL_KeyboardEvent& k) {
    const SDL_Keycode key = k.key;
    const bool ctrl = (k.mod & SDL_KMOD_CTRL) != 0;
    const bool shift = (k.mod & SDL_KMOD_SHIFT) != 0;
    const auto panIndex = [&]() -> int {
        switch (key) {
        case SDLK_W:
        case SDLK_UP: return 0;
        case SDLK_S:
        case SDLK_DOWN: return 1;
        case SDLK_A:
        case SDLK_LEFT: return 2;
        case SDLK_D:
        case SDLK_RIGHT: return 3;
        default: return -1;
        }
    }();
    if (panIndex >= 0) {
        // A release always stops the pan, whatever modifiers are held by then.
        if (!k.down)
            keyPan_[panIndex] = false;
        else if (!ctrl)
            keyPan_[panIndex] = true;
        return;
    }
    if (!k.down || k.repeat) return;

    const Vec2 centre{screen().x * 0.5f, screen().y * 0.5f};
    switch (key) {
    case SDLK_ESCAPE:
        if (photo_)
            togglePhoto();
        else if (tool_ != Tool::None)
            setTool(Tool::None, -1);
        else if (drawerOpen_) {
            drawerOpen_ = false;
            play(sfx::kClose, tuning::kUiSfxLevel);
        } else if (journalOpen_) {
            journalOpen_ = false;
            play(sfx::kClose, tuning::kUiSfxLevel);
        }
        return;
    case SDLK_F11: {
        const bool fs = (SDL_GetWindowFlags(window_.get()) & SDL_WINDOW_FULLSCREEN) != 0;
        if (!SDL_SetWindowFullscreen(window_.get(), !fs)) SDL_Log("fullscreen: %s", SDL_GetError());
        windowState_.fullscreen = !fs;
        return;
    }
    case SDLK_P: togglePhoto(); return;
    case SDLK_SPACE:
    case SDLK_RETURN:
        if (photo_) capturePending_ = true;
        return;
    case SDLK_HOME: frameCamera(); return;
    case SDLK_EQUALS:
    case SDLK_PLUS:
    case SDLK_KP_PLUS: zoomBy(1, centre); return;
    case SDLK_MINUS:
    case SDLK_KP_MINUS: zoomBy(-1, centre); return;
    case SDLK_M:
        muted_ = !muted_;
        markDirty();
        return;
    default: break;
    }
    if (photo_) return; // editing keys do nothing while framing a photo

    switch (key) {
    case SDLK_Z:
        if (ctrl) undoRedo(shift);
        break;
    case SDLK_Y:
        if (ctrl) undoRedo(true);
        break;
    case SDLK_R:
        if (tool_ == Tool::Place) {
            const auto& def = cat_.items[static_cast<std::size_t>(selection_)];
            if (def.count > 1) {
                variant_ = (variant_ + 1) % def.count;
                play(sfx::kRotate);
            }
        }
        break;
    case SDLK_B:
        drawerOpen_ = !drawerOpen_;
        play(drawerOpen_ ? sfx::kOpen : sfx::kClose, tuning::kUiSfxLevel);
        break;
    case SDLK_X: setTool(tool_ == Tool::Remove ? Tool::None : Tool::Remove, -1); break;
    case SDLK_J:
        journalOpen_ = !journalOpen_;
        play(journalOpen_ ? sfx::kOpen : sfx::kClose, tuning::kUiSfxLevel);
        break;
    case SDLK_C: cycleClock(); break;
    case SDLK_N:
        rain_ = !rain_;
        markDirty();
        break;
    default: break;
    }
}

void App::handleEvent(const SDL_Event& e) {
    switch (e.type) {
    case SDL_EVENT_QUIT: running_ = false; break;
    case SDL_EVENT_WINDOW_PIXEL_SIZE_CHANGED:
    case SDL_EVENT_WINDOW_RESIZED:
    case SDL_EVENT_WINDOW_MOVED:
        if (!SDL_GetRenderOutputSize(renderer_.get(), &pixelW_, &pixelH_))
            SDL_Log("%s", SDL_GetError());
        density_ = std::max(1.0f, SDL_GetWindowPixelDensity(window_.get()));
        if ((SDL_GetWindowFlags(window_.get()) & SDL_WINDOW_FULLSCREEN) == 0) {
            WindowRect& r = windowState_.windowed;
            if (!SDL_GetWindowPosition(window_.get(), &r.x, &r.y) ||
                !SDL_GetWindowSize(window_.get(), &r.w, &r.h))
                SDL_Log("window: %s", SDL_GetError());
        }
        break;
    case SDL_EVENT_WINDOW_FOCUS_LOST:
        // Keys released while another window has focus never arrive here.
        std::ranges::fill(keyPan_, false);
        break;
    case SDL_EVENT_WINDOW_MOUSE_ENTER: mouseInside_ = true; break;
    case SDL_EVENT_WINDOW_MOUSE_LEAVE: mouseInside_ = false; break;
    case SDL_EVENT_MOUSE_MOTION: {
        const Vec2 p{e.motion.x * density_, e.motion.y * density_};
        mouseInside_ = true;
        if (drag_ == Drag::Pan) camera_.dragBy({p.x - lastPan_.x, p.y - lastPan_.y}, screen());
        lastPan_ = p;
        mouse_ = p;
        break;
    }
    case SDL_EVENT_MOUSE_BUTTON_DOWN:
    case SDL_EVENT_MOUSE_BUTTON_UP: {
        mouse_ = {e.button.x * density_, e.button.y * density_};
        lastPan_ = mouse_;
        mouseInside_ = true;
        if (e.button.button == SDL_BUTTON_LEFT) {
            (e.button.down ? leftPressed_ : leftReleased_) = true;
        } else if (e.button.button == SDL_BUTTON_RIGHT || e.button.button == SDL_BUTTON_MIDDLE) {
            if (e.button.down && drag_ == Drag::None) {
                drag_ = Drag::Pan;
                rightDown_ = true;
                rightStart_ = mouse_;
            } else if (!e.button.down && rightDown_) {
                rightDown_ = false;
                if (drag_ == Drag::Pan) drag_ = Drag::None;
                // A right click without dragging cancels the current tool.
                const float moved = std::hypot(mouse_.x - rightStart_.x, mouse_.y - rightStart_.y);
                if (moved < kClickSlop * density_ && e.button.button == SDL_BUTTON_RIGHT &&
                    tool_ != Tool::None)
                    setTool(Tool::None, -1);
            }
        }
        break;
    }
    case SDL_EVENT_MOUSE_WHEEL:
        mouse_ = {e.wheel.mouse_x * density_, e.wheel.mouse_y * density_};
        wheel_ += e.wheel.y;
        wheelAcc_ += e.wheel.y;
        wheelIdle_ = 0;
        break;
    case SDL_EVENT_KEY_DOWN:
    case SDL_EVENT_KEY_UP: handleKey(e.key); break;
    default: break;
    }
}

HudModel App::model() const {
    HudModel m;
    m.cat = &cat_;
    m.thumbs = &thumbs_;
    m.visitors = &visitors_;
    m.tool = tool_;
    m.selection = selection_;
    m.category = category_;
    m.drawerOpen = drawerOpen_;
    m.journalOpen = journalOpen_;
    m.photo = photo_;
    m.muted = muted_;
    m.rain = rain_;
    m.pin = clock_.pin();
    m.phase = clock_.phase();
    m.canUndo = editor_.canUndo();
    m.canRedo = editor_.canRedo();
    m.canZoomIn = camera_.level() + 1 < static_cast<int>(kZoomLevels.size());
    m.canZoomOut = camera_.level() > 0;
    const Lighting l = lightingAt(clock_.time(), rain_);
    m.brightness =
        std::clamp(((l.ambient.r + l.ambient.g + l.ambient.b) / 3.0f - 0.3f) / 0.6f, 0.0f, 1.0f);
    if (photo_) {
        m.hint = strings::kHintPhoto;
        return m;
    }
    switch (tool_) {
    case Tool::None: break;
    case Tool::Place: {
        const auto& def = cat_.items[static_cast<std::size_t>(selection_)];
        const bool row = oneTile(def);
        if (def.count <= 1)
            m.hint = row ? strings::kHintPlaceRow : strings::kHintPlaceFixed;
        else if (def.layout == Layout::Rotate)
            m.hint = row ? strings::kHintPlaceRowRotate : strings::kHintPlace;
        else
            m.hint = row ? strings::kHintPlaceRowVariant : strings::kHintPlaceVariant;
        break;
    }
    case Tool::Paint: m.hint = strings::kHintPaint; break;
    case Tool::Remove: m.hint = strings::kHintRemove; break;
    }
    m.warning = warning_;
    if (tool_ == Tool::Place && hover_ && warnTime_ <= 0)
        m.warning = placeWarning(canPlace(world_, cat_, ghostItem(*hover_)));
    return m;
}

void App::applyHudActions() {
    for (const HudAction& a : hud_.actions()) {
        using K = HudAction::Kind;
        if (a.kind == K::Hover) {
            play(sfx::kHover, tuning::kUiSfxLevel * 0.6f);
            continue;
        }
        play(sfx::kClick, tuning::kUiSfxLevel);
        const Vec2 centre{screen().x * 0.5f, screen().y * 0.5f};
        switch (a.kind) {
        case K::ToggleBuild:
            drawerOpen_ = !drawerOpen_;
            play(drawerOpen_ ? sfx::kOpen : sfx::kClose, tuning::kUiSfxLevel);
            break;
        case K::Category: category_ = a.arg; break;
        case K::PickItem:
        case K::PickTerrain: {
            const Tool t = a.kind == K::PickItem ? Tool::Place : Tool::Paint;
            if (tool_ == t && selection_ == a.arg) {
                setTool(Tool::None, -1);
            } else {
                setTool(t, a.arg);
                drawerOpen_ = false; // get out of the way of the map
            }
            break;
        }
        case K::RemoveTool: setTool(tool_ == Tool::Remove ? Tool::None : Tool::Remove, -1); break;
        case K::Sound:
            muted_ = !muted_;
            markDirty();
            break;
        case K::Photo: togglePhoto(); break;
        case K::Clock: cycleClock(); break;
        case K::Rain:
            rain_ = !rain_;
            markDirty();
            break;
        case K::Journal:
            journalOpen_ = !journalOpen_;
            play(journalOpen_ ? sfx::kOpen : sfx::kClose, tuning::kUiSfxLevel);
            break;
        case K::Undo: undoRedo(false); break;
        case K::Redo: undoRedo(true); break;
        case K::Recentre: frameCamera(); break;
        case K::ZoomOut: zoomBy(-1, centre); break;
        case K::ZoomIn: zoomBy(1, centre); break;
        case K::Hover: break;
        }
    }
}

Item App::ghostItem(TilePos hover) const {
    const auto& def = cat_.items[static_cast<std::size_t>(selection_)];
    const Footprint fp = footprintOf(def, variant_);
    // Centre multi-tile footprints on the cursor.
    return makeItem(cat_, selection_, variant_,
                    {hover.x - (fp.w - 1) / 2, hover.y - (fp.h - 1) / 2});
}

Ghost App::ghost() const {
    Ghost g;
    if (!hover_ || photo_ || drag_ == Drag::Pan) return g;
    switch (tool_) {
    case Tool::None: break;
    case Tool::Place:
        g.mode = Ghost::Mode::Item;
        g.item = ghostItem(*hover_);
        g.valid = canPlace(world_, cat_, g.item) == PlaceResult::Ok;
        break;
    case Tool::Paint: {
        g.mode = Ghost::Mode::Tile;
        g.tile = *hover_;
        const auto r = canPaint(world_, cat_, *hover_, selection_);
        g.valid = r == PaintResult::Ok || r == PaintResult::Unchanged;
        break;
    }
    case Tool::Remove:
        g.mode = Ghost::Mode::Remove;
        g.tile = *hover_;
        g.valid = world_.itemAt(*hover_) != nullptr;
        break;
    }
    return g;
}

void App::applyTool(TilePos t, bool first) {
    World& w = world_;
    const auto warn = [&](std::string_view text) {
        warning_ = text;
        warnTime_ = kWarnSeconds;
    };
    switch (tool_) {
    case Tool::None: break;
    case Tool::Place: {
        const Item item = ghostItem(t);
        const auto r = editor_.place(w, cat_, item);
        if (r == PlaceResult::Ok) {
            scene_->onPlaced(item, rng_);
            play(cat_.items[item.type].sound, tuning::kSfxLevel, true);
            markDirty();
        } else if (first) {
            play(sfx::kInvalid);
        }
        break;
    }
    case Tool::Paint: {
        const auto r = editor_.paint(w, cat_, t, selection_);
        if (r == PaintResult::Ok) {
            if (simTime_ - lastPaintSound_ > tuning::kPaintSoundGap) {
                const auto& snd = cat_.terrain[static_cast<std::size_t>(selection_)].sound;
                play(snd.empty() ? sfx::kPaint : std::string_view(snd), tuning::kSfxLevel, true);
                lastPaintSound_ = simTime_;
            }
            markDirty();
        } else if (r == PaintResult::BlockedByItem) {
            if (first) play(sfx::kInvalid);
            warn(strings::kWarnPaint);
        }
        break;
    }
    case Tool::Remove: {
        if (const Item* it = w.itemAt(t)) {
            const Item removed = *it;
            (void)editor_.remove(w, t);
            scene_->onRemoved(removed);
            play(sfx::kRemove, tuning::kSfxLevel, true);
            markDirty();
        } else if (first) {
            warn(strings::kWarnNothing);
        }
        break;
    }
    }
}

void App::worldInput() {
    const bool uiOwns = hud_.wantsMouse() && drag_ != Drag::Tool;
    hover_.reset();
    if (mouseInside_ && !uiOwns && !photo_) {
        const TilePos t = cat_.iso().tileAt(camera_.screenToWorld(mouse_, screen()));
        if (world_.hasGround(t)) hover_ = t;
    }
    // Whole notches step the zoom; small deltas (touchpads, smooth wheels) add up to a step.
    if (uiOwns) wheelAcc_ = 0;
    for (; wheelAcc_ >= 1.0f; wheelAcc_ -= 1.0f) zoomBy(1, mouse_);
    for (; wheelAcc_ <= -1.0f; wheelAcc_ += 1.0f) zoomBy(-1, mouse_);
    wheel_ = 0;

    if (leftPressed_ && !uiOwns && drag_ == Drag::None) {
        if (tool_ == Tool::None || photo_) {
            drag_ = Drag::Pan;
            lastPan_ = pressStart_ = mouse_;
        } else if (const auto t = hover_) {
            drag_ = Drag::Tool;
            editor_.begin();
            applyTool(*t, true);
            lastTile_ = *t;
        }
    }
    if (drag_ == Drag::Tool && hover_ && *hover_ != lastTile_) {
        const bool repeat =
            tool_ != Tool::Place || oneTile(cat_.items[static_cast<std::size_t>(selection_)]);
        if (repeat) walkLine(lastTile_, *hover_, [&](TilePos t) { applyTool(t, false); });
        lastTile_ = *hover_;
    }
    if (leftReleased_) {
        if (drag_ == Drag::Tool) editor_.commit();
        // In photo mode a click (not a drag) takes the photo.
        if (photo_ && drag_ == Drag::Pan && !rightDown_ &&
            std::hypot(mouse_.x - pressStart_.x, mouse_.y - pressStart_.y) < kClickSlop * density_)
            capturePending_ = true;
        if (drag_ != Drag::None && !rightDown_) drag_ = Drag::None;
    }
}

void App::step(float dt) {
    simTime_ += dt;
    clock_.update(dt);
    const Vec2 pan{(keyPan_[3] ? 1.0f : 0.0f) - (keyPan_[2] ? 1.0f : 0.0f),
                   (keyPan_[1] ? 1.0f : 0.0f) - (keyPan_[0] ? 1.0f : 0.0f)};
    if (pan.x != 0 || pan.y != 0)
        camera_.nudge({pan.x * tuning::kKeyPanSpeed * dt, pan.y * tuning::kKeyPanSpeed * dt},
                      screen());
    camera_.update(dt, screen());
    wheelIdle_ += dt;
    if (wheelIdle_ > tuning::kWheelIdleReset) wheelAcc_ = 0;

    visitors_.update(world_, cat_, night(), dt, rng_, activeArea());
    for (const VisitorEvent& e : visitors_.events()) {
        const auto& def = cat_.visitors[static_cast<std::size_t>(e.visitor)];
        if (e.kind == VisitorEvent::Kind::Arrived && e.firstSighting) {
            hud_.toast(std::string(strings::kToastNewVisitor) + def.name);
            play(sfx::kDiscover);
            markDirty();
        }
        if (!def.voice.empty() && (e.kind == VisitorEvent::Kind::Call || e.firstSighting))
            play(def.voice, tuning::kVoiceLevel, true);
    }
    scene_->update(dt, world_, visitors_.critters(), rain_, rng_);

    warnTime_ = std::max(0.0f, warnTime_ - dt);
    if (warnTime_ <= 0) warning_ = {};
    if (autosave_.due(dt, drag_ == Drag::Tool)) (void)save();
}

void App::updateAudio() {
    mixer_.setMuted(muted_);
    const Lighting l = lightingAt(clock_.time(), rain_);
    const float n = std::clamp(l.night, 0.0f, 1.0f);
    mixer_.setLoopGain(Loop::DayMusic, tuning::kMusicLevel * (1 - n));
    mixer_.setLoopGain(Loop::NightMusic, tuning::kMusicLevel * n);
    mixer_.setLoopGain(Loop::Birds,
                       tuning::kBirdsLevel * (1 - n) * (rain_ ? tuning::kRainBirdsDuck : 1.0f));
    mixer_.setLoopGain(Loop::Crickets,
                       tuning::kCricketsLevel * n * (rain_ ? tuning::kRainCricketsDuck : 1.0f));
    mixer_.setLoopGain(Loop::Rain, rain_ ? tuning::kRainLevel : 0.0f);
    const float water = static_cast<float>(world_.terrainCount(cat_.waterTerrain));
    mixer_.setLoopGain(Loop::Water, tuning::kWaterLevel *
                                        std::min(1.0f, water / tuning::kWaterTilesForFullLevel));
}

void App::render() {
    FrameParams p;
    p.world = &world_;
    p.critters = visitors_.critters();
    p.ghost = ghost();
    p.camera = &camera_;
    p.screen = screen();
    p.light = lightingAt(clock_.time(), rain_);
    scene_->draw(p);
    if (capturePending_) {
        capturePending_ = false;
        capturePhoto();
    }
    // The glass panels show a blurred copy of the scene; photo mode has no panels to feed.
    blur_->invalidate();
    if (!photo_ && blur_->begin(p.screen, theme::kBlurRadius * uiScale_)) {
        scene_->composite(p, blur_->sourceScale(), true);
        blur_->end();
    }
    if (font_.build(renderer_.get(), uiScale_)) {
        const HudModel m = model();
        Painter painter(*uiBatch_, font_, {blur_->result(), p.screen, m.brightness}, uiScale_);
        hud_.draw(painter, m);
        uiBatch_->flush();
    }
}

void App::refreshScale() {
    const float display = SDL_GetWindowDisplayScale(window_.get());
    const float fit = std::min(static_cast<float>(pixelW_) / theme::kReferenceW,
                               static_cast<float>(pixelH_) / theme::kReferenceH);
    // Quarter steps keep glyph re-rasterisation rare while a window is being resized.
    uiScale_ = std::clamp(std::round(std::max(display > 0 ? display : 1.0f, fit) * 4.0f) / 4.0f,
                          1.0f, theme::kMaxScale);
}

int App::run() {
    if (!init()) return opts_.bench ? kExitNoRenderer : 1;
    if (opts_.script) {
        auto text = readTextFile(*opts_.script);
        auto parsed = text ? parseScript(*text) : std::unexpected(text.error());
        if (!parsed) {
            SDL_Log("%s", parsed.error().c_str());
            return kExitBadScript;
        }
        script_ = std::move(*parsed);
    }
    refreshScale();
    if (!font_.build(renderer_.get(), uiScale_)) return 1;
    // One interface layout first, so the camera can frame the land clear of it.
    hud_.update({}, model(), font_, screen(), uiScale_, 0);
    frameCamera();
    if (opts_.bench) return runBench();
    visitors_.populate(world_, cat_, night(), rng_, activeArea());

    // Headless runs advance exactly one fixed step per frame so scripts are reproducible.
    const bool fixed = opts_.headless;
    Uint64 last = SDL_GetTicksNS();
    double acc = 0;
    while (running_) {
        leftPressed_ = leftReleased_ = false;
        for (SDL_Event e; SDL_PollEvent(&e);) handleEvent(e);

        const Uint64 now = SDL_GetTicksNS();
        const double real = static_cast<double>(now - last) * 1e-9;
        last = now;
        const float frameDt = fixed ? static_cast<float>(tuning::kStepSeconds)
                                    : static_cast<float>(std::min(real, 0.1));
        refreshScale();
        if (!font_.build(renderer_.get(), uiScale_)) return 1;

        UiInput in;
        in.x = mouse_.x;
        in.y = mouse_.y;
        in.inside = mouseInside_;
        in.pressed = leftPressed_;
        in.released = leftReleased_;
        in.wheel = wheel_;
        in.blocked = drag_ != Drag::None;
        hud_.update(in, model(), font_, screen(), uiScale_, frameDt);
        applyHudActions();
        worldInput();

        int steps = 1;
        if (!fixed) {
            acc += real;
            steps = static_cast<int>(acc / tuning::kStepSeconds);
            acc -= steps * tuning::kStepSeconds;
            if (steps > tuning::kMaxStepsPerFrame) {
                steps = tuning::kMaxStepsPerFrame;
                acc = 0;
            }
        }
        for (int i = 0; i < steps; ++i) step(static_cast<float>(tuning::kStepSeconds));
        updateAudio();
        if (opts_.audioOut) {
            const std::size_t n = capture_.size();
            capture_.resize(n + static_cast<std::size_t>(steps * kAudioFramesPerStep * 2));
            mixer_.render(capture_.data() + n, steps * kAudioFramesPerStep);
        }
        render();

        // The script runs after the frame is drawn: shots capture it, and the input it queues is
        // handled at the start of the next frame, exactly like real events.
        if (!script_.empty()) {
            if (scriptWait_ == 0 && scriptPos_ < script_.size() &&
                script_[scriptPos_].kind == ScriptCommand::Kind::Shot) {
                const auto& file = script_[scriptPos_].args[0];
                if (shot(file))
                    SDL_Log("script: saved %s", file.c_str());
                else
                    exitCode_ = 1;
                ++scriptPos_;
            }
            if (!scriptStep()) running_ = false;
        }
        if (!SDL_RenderPresent(renderer_.get())) SDL_Log("present: %s", SDL_GetError());
        ++frame_;
        if (opts_.frames > 0 && frame_ >= opts_.frames) running_ = false;
    }
    if (editor_.inGroup()) editor_.commit();
    if (!save() && exitCode_ == 0 && opts_.script) SDL_Log("save: the final save failed");
    rememberWindow();
    mixer_.close();
    if (opts_.audioOut) {
        if (auto r = writeWavFloat(*opts_.audioOut, capture_); !r) {
            SDL_Log("audio: %s", r.error().c_str());
            return 1;
        }
        SDL_Log("audio: wrote %s", opts_.audioOut->string().c_str());
    }
    return exitCode_;
}

int runApp(const Options& options) {
    const SdlSession sdl(options.headless,
                         !options.renderer.empty() && options.renderer != "software");
    if (!sdl.ok) return 1;
    fs::path assets = findAssets(options);
    auto cat = loadCatalog(assets / "catalog.json");
    if (!cat) {
        SDL_Log("cannot start: %s", cat.error().c_str());
        return 1;
    }
    if (options.bench && options.map) {
        cat->mapW = options.map->w;
        cat->mapH = options.map->h;
    }
    App app(options, std::move(*cat), std::move(assets));
    return app.run();
}

} // namespace lc
