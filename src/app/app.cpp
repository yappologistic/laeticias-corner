#include "app/app.hpp"

#include "app/script.hpp"
#include "audio/mixer.hpp"
#include "core/catalog.hpp"
#include "core/clock.hpp"
#include "core/edit.hpp"
#include "core/rng.hpp"
#include "core/save.hpp"
#include "core/starter.hpp"
#include "core/tuning.hpp"
#include "core/visitors.hpp"
#include "core/world.hpp"
#include "render/atlas.hpp"
#include "render/blur.hpp"
#include "render/camera.hpp"
#include "render/scene.hpp"
#include "render/sdl_ptr.hpp"
#include "ui/font.hpp"
#include "ui/hud.hpp"
#include "ui/painter.hpp"
#include "ui/strings.hpp"
#include "ui/theme.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <format>
#include <memory>
#include <optional>

namespace lc {
namespace {

namespace fs = std::filesystem;

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
constexpr float kWarnSeconds = 1.6f;
constexpr int kDragSteps = 8;

// Owns SDL initialisation so it outlives every other SDL object in App.
struct SdlSession {
    bool ok = false;
    SdlSession(bool headless, bool gpu) {
        if (headless) {
            // Override any environment so automated runs can never reach the desktop or speakers.
            // The dummy video driver suffices for software rendering; offscreen (EGL, still no
            // window) is only needed when a GPU renderer is requested.
            SDL_SetHintWithPriority(SDL_HINT_VIDEO_DRIVER, gpu ? "offscreen" : "dummy",
                                    SDL_HINT_OVERRIDE);
            SDL_SetHintWithPriority(SDL_HINT_AUDIO_DRIVER, "dummy", SDL_HINT_OVERRIDE);
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

class App {
public:
    App(const Options& o, Catalog cat, fs::path assets)
        : opts_(o), assets_(std::move(assets)), saveDir_(findSaveDir(o)), cat_(std::move(cat)),
          world_(cat_), visitors_(cat_),
          rng_(o.seed.value_or(
              o.headless ? 1
                         : static_cast<std::uint64_t>(
                               std::chrono::steady_clock::now().time_since_epoch().count()))),
          camera_(cat_.mapW, cat_.mapH) {}

    int run();

private:
    bool init();
    void loadOrStart();
    void save();
    void handleEvent(const SDL_Event& e);
    void handleKey(const SDL_KeyboardEvent& k);
    void applyHudActions();
    void worldInput();
    void applyTool(TilePos t, bool first);
    void step(float dt);
    void render();
    void refreshScale();
    void updateAudio();
    void play(std::string_view file, float gain = tuning::kSfxLevel, bool jitter = false);
    void feedback(std::span<const Op> ops);
    void setTool(Tool t, int selection);
    void togglePhoto();
    void capturePhoto();
    void cycleClock();
    void markDirty() {
        dirty_ = true;
        sinceChange_ = 0;
    }
    [[nodiscard]] Vec2 screen() const {
        return {static_cast<float>(pixelW_), static_cast<float>(pixelH_)};
    }
    [[nodiscard]] HudModel model() const;
    [[nodiscard]] Item ghostItem(TilePos hover) const;
    [[nodiscard]] Ghost ghost() const;
    [[nodiscard]] bool night() const;

    // Scripting
    bool scriptStep();
    std::optional<Vec2> resolve(const ScriptPoint& p);
    void pushMouseMotion(Vec2 px);
    void pushButton(Vec2 px, bool down, bool right);
    void pushKey(std::string_view combo, bool down);
    std::optional<std::string> check(const ScriptCommand& c);
    bool shot(const fs::path& file);

    void runBench();

    Options opts_;
    fs::path assets_;
    fs::path saveDir_;
    Catalog cat_;
    World world_;
    Editor editor_{tuning::kUndoSteps};
    Clock clock_;
    Visitors visitors_;
    Rng rng_;
    bool rain_ = false;
    bool muted_ = false;
    Camera camera_;

    WindowPtr window_;
    RendererPtr renderer_;
    std::unique_ptr<Atlas> atlas_;
    std::unique_ptr<Scene> scene_;
    std::unique_ptr<Batch> uiBatch_;
    std::unique_ptr<Blur> blur_;
    Font font_;
    Hud hud_;
    Mixer mixer_;
    int pixelW_ = 0;
    int pixelH_ = 0;
    float density_ = 1;
    float uiScale_ = 1;

    // Input
    Vec2 mouse_;
    bool mouseInside_ = false;
    bool leftPressed_ = false;
    bool leftReleased_ = false;
    float wheel_ = 0;
    bool keyPan_[4] = {};
    enum class Drag : std::uint8_t { None, Tool, Pan };
    Drag drag_ = Drag::None;
    bool rightDown_ = false;
    Vec2 rightStart_;
    Vec2 lastPan_;
    TilePos lastTile_;
    std::optional<TilePos> hover_;

    // Tools and UI state
    Tool tool_ = Tool::None;
    int selection_ = -1;
    int variant_ = 0;
    int category_ = 0;
    bool drawerOpen_ = false;
    bool journalOpen_ = false;
    bool photo_ = false;
    bool capturePending_ = false;
    bool photoSaved_ = false;
    std::string_view warning_;
    float warnTime_ = 0;
    float lastPaintSound_ = -1;

    // Time and saving
    float simTime_ = 0;
    bool dirty_ = false;
    float sinceChange_ = 0;
    bool running_ = true;
    int exitCode_ = 0;
    int frame_ = 0;

    // Script state
    std::vector<ScriptCommand> script_;
    std::size_t scriptPos_ = 0;
    int scriptPhase_ = 0; // sub-step within the current command
    int scriptWait_ = 0;
};

bool App::init() {

    SDL_WindowFlags flags = SDL_WINDOW_RESIZABLE | SDL_WINDOW_HIGH_PIXEL_DENSITY;
    window_.reset(SDL_CreateWindow(std::string(strings::kWindowTitle).c_str(), opts_.width,
                                   opts_.height, flags));
    if (!window_) {
        SDL_Log("cannot create window: %s", SDL_GetError());
        return false;
    }
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

    atlas_ = std::make_unique<Atlas>(renderer_.get(), assets_);
    scene_ = std::make_unique<Scene>(renderer_.get(), *atlas_, cat_);
    uiBatch_ = std::make_unique<Batch>(renderer_.get());
    blur_ = std::make_unique<Blur>(renderer_.get());
    if (!font_.load(assets_ / "fonts")) return false;

    mixer_.load(assets_ / "audio", cat_.audio);
    (void)mixer_.open();

    loadOrStart();
    camera_.recentre(screen());
    return true;
}

void App::loadOrStart() {
    const fs::path file = saveDir_ / kSaveFile;
    std::error_code ec;
    if (fs::exists(file, ec)) {
        auto text = readTextFile(file);
        auto data = text ? deserialize(*text, cat_) : std::unexpected(text.error());
        if (data) {
            for (const auto& w : data->warnings) SDL_Log("save: skipped %s", w.c_str());
            world_ = std::move(data->world);
            clock_.setTime(data->clockTime);
            clock_.setPin(data->pin, false);
            rain_ = data->rain;
            muted_ = data->muted;
            for (const auto& id : data->journal)
                if (const auto v = cat_.findVisitor(id)) visitors_.markSeen(*v);
            visitors_.populate(world_, cat_, night(), rng_);
            SDL_Log("save: restored %s", file.string().c_str());
            return;
        }
        // Keep the unreadable file for inspection instead of silently overwriting it.
        fs::path backup = file;
        backup += ".bak";
        fs::rename(file, backup, ec);
        SDL_Log("save: %s; moved aside to %s and starting fresh", data.error().c_str(),
                backup.string().c_str());
    }
    world_ = makeStarterWorld(cat_);
}

void App::save() {
    SaveData data(world_);
    data.clockTime = clock_.time();
    data.pin = clock_.pin();
    data.rain = rain_;
    data.muted = muted_;
    for (std::size_t v = 0; v < cat_.visitors.size(); ++v)
        if (visitors_.seen(static_cast<int>(v))) data.journal.push_back(cat_.visitors[v].id);
    if (auto r = writeFileAtomic(saveDir_ / kSaveFile, serialize(data, cat_)); !r)
        SDL_Log("save: %s", r.error().c_str());
    dirty_ = false;
}

bool App::night() const {
    const Phase p = clock_.phase();
    return p == Phase::Dusk || p == Phase::Night;
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
                                          ClockPin::Auto};
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
        capturePending_ = true;
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
        file = dir / std::format("laeticias-corner-{:04}.png", n);
        if (!fs::exists(file, ec)) break;
    }
    photoSaved_ = shot(file);
    if (photoSaved_) {
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
            scene_->onPlaced(op.item, simTime_, rng_);
        else if (op.kind == Op::Kind::Remove)
            scene_->onRemoved(op.item, simTime_);
    }
    if (!ops.empty()) markDirty();
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
    if (panIndex >= 0 && !ctrl) {
        keyPan_[panIndex] = k.down;
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
        return;
    }
    case SDLK_P: togglePhoto(); return;
    case SDLK_HOME: camera_.recentre(screen()); return;
    case SDLK_EQUALS:
    case SDLK_PLUS:
    case SDLK_KP_PLUS: camera_.zoomAt(camera_.zoom() + 1, centre, screen()); return;
    case SDLK_MINUS:
    case SDLK_KP_MINUS: camera_.zoomAt(camera_.zoom() - 1, centre, screen()); return;
    case SDLK_M:
        muted_ = !muted_;
        markDirty();
        return;
    default: break;
    }
    if (photo_) return; // editing keys do nothing while framing a photo

    switch (key) {
    case SDLK_Z:
        if (ctrl) {
            const auto ops = shift ? editor_.redo(world_) : editor_.undo(world_);
            if (!ops.empty()) play(shift ? sfx::kRedo : sfx::kUndo);
            feedback(ops);
        }
        break;
    case SDLK_Y:
        if (ctrl) {
            const auto ops = editor_.redo(world_);
            if (!ops.empty()) play(sfx::kRedo);
            feedback(ops);
        }
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
        if (!SDL_GetRenderOutputSize(renderer_.get(), &pixelW_, &pixelH_))
            SDL_Log("%s", SDL_GetError());
        density_ = std::max(1.0f, SDL_GetWindowPixelDensity(window_.get()));
        break;
    case SDL_EVENT_WINDOW_MOUSE_ENTER: mouseInside_ = true; break;
    case SDL_EVENT_WINDOW_MOUSE_LEAVE: mouseInside_ = false; break;
    case SDL_EVENT_MOUSE_MOTION: {
        const Vec2 p{e.motion.x * density_, e.motion.y * density_};
        mouseInside_ = true;
        if (drag_ == Drag::Pan) camera_.dragBy({p.x - lastPan_.x, p.y - lastPan_.y});
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
                if (moved < 4.0f * density_ && e.button.button == SDL_BUTTON_RIGHT &&
                    tool_ != Tool::None)
                    setTool(Tool::None, -1);
            }
        }
        break;
    }
    case SDL_EVENT_MOUSE_WHEEL:
        mouse_ = {e.wheel.mouse_x * density_, e.wheel.mouse_y * density_};
        wheel_ += e.wheel.y;
        break;
    case SDL_EVENT_KEY_DOWN:
    case SDL_EVENT_KEY_UP: handleKey(e.key); break;
    default: break;
    }
}

HudModel App::model() const {
    HudModel m;
    m.cat = &cat_;
    m.sprites = &scene_->sprites();
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
    m.canZoomIn = camera_.zoom() < tuning::kMaxZoom;
    m.canZoomOut = camera_.zoom() > tuning::kMinZoom;
    switch (tool_) {
    case Tool::None: break;
    case Tool::Place: {
        const auto& def = cat_.items[static_cast<std::size_t>(selection_)];
        m.hint = def.count <= 1 ? strings::kHintPlaceFixed
                                : (def.layout == Layout::Rotate ? strings::kHintPlace
                                                                : strings::kHintPlaceVariant);
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
        case K::Undo:
            feedback(editor_.undo(world_));
            play(sfx::kUndo);
            break;
        case K::Redo:
            feedback(editor_.redo(world_));
            play(sfx::kRedo);
            break;
        case K::Recentre: camera_.recentre(screen()); break;
        case K::ZoomOut: camera_.zoomAt(camera_.zoom() - 1, centre, screen()); break;
        case K::ZoomIn: camera_.zoomAt(camera_.zoom() + 1, centre, screen()); break;
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
            scene_->onPlaced(item, simTime_, rng_);
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
        const Item* it = w.itemAt(t);
        if (it != nullptr) {
            const Item removed = *it;
            (void)editor_.remove(w, t);
            scene_->onRemoved(removed, simTime_);
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
        const TilePos t = tileAt(camera_.screenToWorld(mouse_, screen()));
        if (world_.inBounds(t)) hover_ = t;
    }
    if (!uiOwns && wheel_ != 0) {
        const int steps = wheel_ > 0 ? 1 : -1;
        camera_.zoomAt(camera_.zoom() + steps, mouse_, screen());
    }
    wheel_ = 0;

    if (leftPressed_ && !uiOwns && drag_ == Drag::None) {
        if (tool_ == Tool::None || photo_) {
            drag_ = Drag::Pan;
            lastPan_ = mouse_;
        } else if (const auto t = hover_) {
            drag_ = Drag::Tool;
            editor_.begin();
            applyTool(*t, true);
            lastTile_ = *t;
        }
    }
    if (drag_ == Drag::Tool && hover_ && *hover_ != lastTile_) {
        const bool repeat = tool_ != Tool::Place ||
                            (cat_.items[static_cast<std::size_t>(selection_)].footprintW == 1 &&
                             cat_.items[static_cast<std::size_t>(selection_)].footprintH == 1);
        if (repeat) walkLine(lastTile_, *hover_, [&](TilePos t) { applyTool(t, false); });
        lastTile_ = *hover_;
    }
    if (leftReleased_) {
        if (drag_ == Drag::Tool) editor_.commit();
        if (drag_ != Drag::None && !rightDown_) drag_ = Drag::None;
    }
}

void App::step(float dt) {
    simTime_ += dt;
    clock_.update(dt);
    const Vec2 pan{(keyPan_[3] ? 1.0f : 0.0f) - (keyPan_[2] ? 1.0f : 0.0f),
                   (keyPan_[1] ? 1.0f : 0.0f) - (keyPan_[0] ? 1.0f : 0.0f)};
    if (pan.x != 0 || pan.y != 0)
        camera_.nudge({pan.x * tuning::kKeyPanSpeed * dt, pan.y * tuning::kKeyPanSpeed * dt});
    camera_.update(dt);

    visitors_.update(world_, cat_, night(), dt, rng_);
    for (const VisitorEvent& e : visitors_.events()) {
        const auto& def = cat_.visitors[static_cast<std::size_t>(e.visitor)];
        if (e.kind == VisitorEvent::Kind::Arrived && e.firstSighting) {
            hud_.toast(std::string(strings::kToastNewVisitor) + def.name);
            play(sfx::kDiscover);
            markDirty();
        }
        if (!def.voice.empty() && (e.kind == VisitorEvent::Kind::Call || e.firstSighting))
            play(def.voice, tuning::kSfxLevel * 0.6f, true);
    }
    scene_->update(dt, world_, rain_, rng_);

    warnTime_ = std::max(0.0f, warnTime_ - dt);
    if (warnTime_ <= 0) warning_ = {};
    if (dirty_) {
        sinceChange_ += dt;
        if (sinceChange_ >= tuning::kAutosaveDelay && drag_ != Drag::Tool) save();
    }
}

void App::updateAudio() {
    mixer_.setMuted(muted_);
    const Lighting l = lightingAt(clock_.time(), rain_);
    const float n = std::clamp(l.night, 0.0f, 1.0f);
    mixer_.setLoopGain(Loop::DayMusic, tuning::kMusicLevel * (1 - n));
    mixer_.setLoopGain(Loop::NightMusic, tuning::kMusicLevel * n);
    mixer_.setLoopGain(Loop::Birds, tuning::kBirdsLevel * (1 - n) * (rain_ ? 0.3f : 1.0f));
    mixer_.setLoopGain(Loop::Crickets, tuning::kCricketsLevel * n * (rain_ ? 0.5f : 1.0f));
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
    p.time = simTime_;
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
        Painter painter(*uiBatch_, font_, *atlas_, {blur_->result(), p.screen}, uiScale_);
        hud_.draw(painter, model());
        uiBatch_->flush();
    }
}

// --- scripting --------------------------------------------------------------------------------

std::optional<Vec2> App::resolve(const ScriptPoint& p) {
    switch (p.kind) {
    case ScriptPoint::Kind::Pixel: return Vec2{p.x, p.y};
    case ScriptPoint::Kind::Tile:
        return camera_.worldToScreen(tileToWorld(p.x + 0.5f, p.y + 0.5f), screen());
    case ScriptPoint::Kind::Widget: return hud_.widgetCentre(p.widget, model());
    }
    return std::nullopt;
}

void App::pushMouseMotion(Vec2 px) {
    SDL_Event e{};
    e.type = SDL_EVENT_MOUSE_MOTION;
    e.motion.windowID = SDL_GetWindowID(window_.get());
    e.motion.x = px.x / density_;
    e.motion.y = px.y / density_;
    e.motion.xrel = (px.x - mouse_.x) / density_;
    e.motion.yrel = (px.y - mouse_.y) / density_;
    if (!SDL_PushEvent(&e)) SDL_Log("script: %s", SDL_GetError());
}

void App::pushButton(Vec2 px, bool down, bool right) {
    SDL_Event e{};
    e.type = down ? SDL_EVENT_MOUSE_BUTTON_DOWN : SDL_EVENT_MOUSE_BUTTON_UP;
    e.button.windowID = SDL_GetWindowID(window_.get());
    e.button.button = static_cast<Uint8>(right ? SDL_BUTTON_RIGHT : SDL_BUTTON_LEFT);
    e.button.down = down;
    e.button.clicks = 1;
    e.button.x = px.x / density_;
    e.button.y = px.y / density_;
    if (!SDL_PushEvent(&e)) SDL_Log("script: %s", SDL_GetError());
}

void App::pushKey(std::string_view combo, bool down) {
    SDL_Keymod mod = SDL_KMOD_NONE;
    std::string name(combo);
    for (const auto& [prefix, m] :
         {std::pair{"ctrl+", SDL_KMOD_LCTRL}, std::pair{"shift+", SDL_KMOD_LSHIFT}}) {
        for (auto pos = name.find(prefix); pos != std::string::npos; pos = name.find(prefix)) {
            name.erase(pos, std::string_view(prefix).size());
            mod = static_cast<SDL_Keymod>(mod | m);
        }
    }
    if (name == "equals" || name == "plus")
        name = "=";
    else if (name == "minus")
        name = "-";
    SDL_Event e{};
    e.type = down ? SDL_EVENT_KEY_DOWN : SDL_EVENT_KEY_UP;
    e.key.windowID = SDL_GetWindowID(window_.get());
    e.key.key = SDL_GetKeyFromName(name.c_str());
    e.key.scancode = SDL_GetScancodeFromKey(e.key.key, nullptr);
    e.key.mod = mod;
    e.key.down = down;
    if (e.key.key == SDLK_UNKNOWN)
        SDL_Log("script: unknown key '%s'", name.c_str());
    else if (!SDL_PushEvent(&e))
        SDL_Log("script: %s", SDL_GetError());
}

std::optional<std::string> App::check(const ScriptCommand& c) {
    const auto& a = c.args;
    const std::string& what = a[0];
    const auto mismatch = [&](const std::string& actual) {
        return std::format("expected {} {} but found {}", what, a.back(), actual);
    };
    const auto yesNo = [&](bool v) -> std::optional<std::string> {
        const bool want = a[1] == "yes" || a[1] == "on" || a[1] == "open" || a[1] == "true";
        return want == v ? std::nullopt : std::optional(mismatch(v ? "yes" : "no"));
    };
    const auto tileOf = [&]() -> std::optional<TilePos> {
        if (c.a.kind == ScriptPoint::Kind::Tile)
            return TilePos{static_cast<int>(c.a.x), static_cast<int>(c.a.y)};
        const auto px = resolve(c.a);
        if (!px) return std::nullopt;
        return tileAt(camera_.screenToWorld(*px, screen()));
    };
    if (what == "tile" || what == "item") {
        const auto t = tileOf();
        if (!t || !world_.inBounds(*t)) return std::string("point is off the map");
        if (what == "tile") {
            const auto& id = cat_.terrain[static_cast<std::size_t>(world_.terrainAt(*t))].id;
            return id == a[2] ? std::nullopt : std::optional(mismatch(id));
        }
        const Item* it = world_.itemAt(*t);
        const std::string id = it ? cat_.items[it->type].id : "none";
        return id == a[2] ? std::nullopt : std::optional(mismatch(id));
    }
    if (what == "count") {
        if (a.size() != 3) return std::string("expect count ITEM N");
        int have = 0;
        if (a[1] == "all")
            have = static_cast<int>(world_.items().size());
        else if (const auto idx = cat_.findItem(a[1]))
            have = world_.itemCount(*idx);
        else
            return "unknown item " + a[1];
        return std::to_string(have) == a[2] ? std::nullopt
                                            : std::optional(mismatch(std::to_string(have)));
    }
    if (what == "tool") {
        static constexpr std::string_view kNames[] = {"none", "place", "paint", "remove"};
        const std::string_view have = kNames[static_cast<std::size_t>(tool_)];
        return have == a[1] ? std::nullopt : std::optional(mismatch(std::string(have)));
    }
    if (what == "drawer") return yesNo(drawerOpen_);
    if (what == "journal") return yesNo(journalOpen_);
    if (what == "photo") return yesNo(photo_);
    if (what == "undo") return yesNo(editor_.canUndo());
    if (what == "redo") return yesNo(editor_.canRedo());
    if (what == "muted") return yesNo(muted_);
    if (what == "rain") return yesNo(rain_);
    if (what == "zoom") {
        return std::to_string(camera_.zoom()) == a[1]
                   ? std::nullopt
                   : std::optional(mismatch(std::to_string(camera_.zoom())));
    }
    if (what == "phase") {
        const std::string have(phaseId(clock_.phase()));
        return have == a[1] ? std::nullopt : std::optional(mismatch(have));
    }
    if (what == "seen") {
        const auto v = cat_.findVisitor(a[1]);
        if (!v) return "unknown visitor " + a[1];
        return visitors_.seen(*v) ? std::nullopt
                                  : std::optional(std::format("visitor {} not seen", a[1]));
    }
    if (what == "photos") {
        int n = 0;
        std::error_code ec;
        for (auto it = fs::directory_iterator(saveDir_ / kPhotoDir, ec);
             !ec && it != fs::directory_iterator(); ++it)
            n += it->path().extension() == ".png" ? 1 : 0;
        return std::to_string(n) == a[1] ? std::nullopt
                                         : std::optional(mismatch(std::to_string(n)));
    }
    return "unknown expectation '" + what + "'";
}

// Runs the script for one frame. Returns false when the script asks to stop.
bool App::scriptStep() {
    if (scriptWait_ > 0) {
        --scriptWait_;
        return true;
    }
    while (scriptPos_ < script_.size()) {
        const ScriptCommand& c = script_[scriptPos_];
        const auto fail = [&](const std::string& why) {
            SDL_Log("script line %d: %s", c.line, why.c_str());
            exitCode_ = 1;
            return false;
        };
        const auto next = [&] {
            ++scriptPos_;
            scriptPhase_ = 0;
        };
        using K = ScriptCommand::Kind;
        switch (c.kind) {
        case K::Move: {
            const auto p = resolve(c.a);
            if (!p) return fail("cannot resolve point");
            pushMouseMotion(*p);
            next();
            return true;
        }
        case K::Click: {
            const auto p = resolve(c.a);
            if (!p) return fail("cannot resolve point");
            if (scriptPhase_ == 0) {
                pushMouseMotion(*p);
                pushButton(*p, true, c.right);
                scriptPhase_ = 1;
            } else {
                pushButton(*p, false, c.right);
                next();
            }
            return true;
        }
        case K::Drag: {
            if (scriptPhase_ == 0) {
                const auto p = resolve(c.a);
                if (!p) return fail("cannot resolve point");
                pushMouseMotion(*p);
                pushButton(*p, true, c.right);
                // Resolve the end point now: dragging may move the camera.
                const auto q = resolve(c.b);
                if (!q) return fail("cannot resolve point");
                script_[scriptPos_].a = {ScriptPoint::Kind::Pixel, p->x, p->y, {}};
                script_[scriptPos_].b = {ScriptPoint::Kind::Pixel, q->x, q->y, {}};
                scriptPhase_ = 1;
                return true;
            }
            const float k = static_cast<float>(scriptPhase_) / kDragSteps;
            const Vec2 p{c.a.x + (c.b.x - c.a.x) * k, c.a.y + (c.b.y - c.a.y) * k};
            if (scriptPhase_ <= kDragSteps) {
                pushMouseMotion(p);
                ++scriptPhase_;
            } else {
                pushButton({c.b.x, c.b.y}, false, c.right);
                next();
            }
            return true;
        }
        case K::Key:
            if (scriptPhase_ == 0) {
                pushKey(c.args[0], true);
                scriptPhase_ = 1;
            } else {
                pushKey(c.args[0], false);
                next();
            }
            return true;
        case K::Wheel: {
            const auto p = c.hasPoint ? resolve(c.a) : std::optional(mouse_);
            if (!p) return fail("cannot resolve point");
            if (c.hasPoint) pushMouseMotion(*p);
            SDL_Event e{};
            e.type = SDL_EVENT_MOUSE_WHEEL;
            e.wheel.windowID = SDL_GetWindowID(window_.get());
            e.wheel.y = c.amount;
            e.wheel.mouse_x = p->x / density_;
            e.wheel.mouse_y = p->y / density_;
            if (!SDL_PushEvent(&e)) SDL_Log("script: %s", SDL_GetError());
            next();
            return true;
        }
        case K::Wait:
            scriptWait_ = static_cast<int>(c.amount) - 1;
            next();
            if (scriptWait_ >= 0) return true;
            scriptWait_ = 0;
            continue;
        case K::Shot:
            // Taken after this frame renders; see run().
            return true;
        case K::Set:
            if (c.args[0] == "clock") {
                const auto pin = parsePin(c.args[1]);
                if (!pin) return fail("unknown clock value " + c.args[1]);
                clock_.setPin(*pin, true);
            } else {
                rain_ = c.args[1] == "on";
            }
            next();
            continue;
        case K::Expect:
            if (const auto err = check(c)) return fail(*err);
            next();
            continue;
        case K::Quit: return false;
        }
    }
    return false; // the script ran out: done
}

// --- main loop --------------------------------------------------------------------------------

void App::runBench() {
    // Fill every free tile with something, paint a lake, and render at night in the rain so every
    // pass (glow, light pools, particles) is busy.
    Rng fill(opts_.seed.value_or(1));
    World& w = world_;
    for (int y = 6; y < 12; ++y)
        for (int x = 4; x < 10; ++x)
            if (w.itemAt({x, y}) == nullptr) w.setTerrain({x, y}, cat_.waterTerrain);
    for (int y = 0; y < w.height(); ++y) {
        for (int x = 0; x < w.width(); ++x) {
            for (int attempt = 0; attempt < 8 && w.itemAt({x, y}) == nullptr; ++attempt) {
                const int type = fill.range(0, static_cast<int>(cat_.items.size()) - 1);
                const int variant =
                    fill.range(0, cat_.items[static_cast<std::size_t>(type)].count - 1);
                const Item it = makeItem(cat_, type, variant, {x, y});
                if (canPlace(w, cat_, it) == PlaceResult::Ok) w.addItem(it);
            }
        }
    }
    clock_.setPin(ClockPin::Night, true);
    rain_ = true;
    drawerOpen_ = true;
    journalOpen_ = true;
    visitors_.populate(w, cat_, night(), rng_);

    const int frames = opts_.frames > 0 ? opts_.frames : 600;
    double updSum = 0;
    double updMax = 0;
    double drawSum = 0;
    double drawMax = 0;
    int calls = 0;
    const auto ms = [](Uint64 a, Uint64 b) {
        return static_cast<double>(b - a) * 1000.0 /
               static_cast<double>(SDL_GetPerformanceFrequency());
    };
    for (int f = 0; f < frames; ++f) {
        const Uint64 t0 = SDL_GetPerformanceCounter();
        step(static_cast<float>(tuning::kStepSeconds));
        const Uint64 t1 = SDL_GetPerformanceCounter();
        hud_.update({}, model(), font_, screen(), uiScale_,
                    static_cast<float>(tuning::kStepSeconds));
        render();
        const Uint64 t2 = SDL_GetPerformanceCounter();
        calls = scene_->drawCalls() + blur_->drawCalls() + uiBatch_->drawCalls();
        uiBatch_->resetStats();
        if (!SDL_RenderPresent(renderer_.get())) SDL_Log("present: %s", SDL_GetError());
        if (f < 10) continue; // warm-up
        updSum += ms(t0, t1);
        updMax = std::max(updMax, ms(t0, t1));
        drawSum += ms(t1, t2);
        drawMax = std::max(drawMax, ms(t1, t2));
    }
    const double n = frames - 10;
    std::printf("bench: %zu items, %zu critters, %dx%d, %d frames\n", w.items().size(),
                visitors_.critters().size(), pixelW_, pixelH_, frames - 10);
    std::printf("bench: update avg %.3f ms, max %.3f ms\n", updSum / n, updMax);
    std::printf("bench: draw   avg %.3f ms, max %.3f ms (%s renderer)\n", drawSum / n, drawMax,
                SDL_GetRendererName(renderer_.get()));
    std::printf("bench: draw calls per frame %d\n", calls);
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
    if (!init()) return 1;
    if (opts_.script) {
        auto text = readTextFile(*opts_.script);
        auto parsed = text ? parseScript(*text) : std::unexpected(text.error());
        if (!parsed) {
            SDL_Log("%s", parsed.error().c_str());
            return 2;
        }
        script_ = std::move(*parsed);
    }
    refreshScale();
    if (!font_.build(renderer_.get(), uiScale_)) return 1;
    if (opts_.bench) {
        runBench();
        return 0;
    }

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
    save();
    mixer_.close();
    return exitCode_;
}

} // namespace

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
    App app(options, std::move(*cat), std::move(assets));
    return app.run();
}

} // namespace lc
