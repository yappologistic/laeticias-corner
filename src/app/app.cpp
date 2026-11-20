#include "app/app.hpp"

#include "app/app_impl.hpp"
#include "app/identity.hpp"
#include "audio/decode.hpp"
#include "audio/wav.hpp"
#include "core/growth.hpp"
#include "core/land.hpp"
#include "core/save.hpp"
#include "core/starter.hpp"
#include "render/bands.hpp"
#include "render/sprites.hpp"
#include "ui/painter.hpp"
#include "ui/strings.hpp"
#include "ui/theme.hpp"

#include <algorithm>
#include <cctype>
#include <chrono>
#include <cmath>
#include <cstdlib>
#include <format>
#include <fstream>
#include <iterator>
#include <utility>

namespace lc {
namespace {

constexpr std::string_view kRainBed = "amb/rain.ogg";           // under rain, not snow
constexpr std::string_view kWaterBed = "amb/water.ogg";         // with the water on screen
constexpr std::string_view kWaterfallBed = "amb/waterfall.ogg"; // where water meets the rim
constexpr int kThumbW = 384; // world thumbnail for the worlds screen
constexpr int kThumbH = 240;
constexpr int kHeadlessW = 1280; // headless window when --size is not given
constexpr int kHeadlessH = 800;
constexpr int kMinWindowW = 960; // the smallest window the interface is designed for
constexpr int kMinWindowH = 600;
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
        setAppMetadata();
        ok = SDL_Init(SDL_INIT_VIDEO);
        if (!ok) SDL_Log("SDL_Init failed: %s", SDL_GetError());
        // A computer with no sound (no audio driver at all, or one that cannot start) still
        // plays, silently: the mixer finds no device and says so once.
        if (ok && !SDL_InitSubSystem(SDL_INIT_AUDIO))
            SDL_Log("audio: no audio driver (%s); continuing silently", SDL_GetError());
    }
    ~SdlSession() { SDL_Quit(); }
    SdlSession(const SdlSession&) = delete;
    SdlSession& operator=(const SdlSession&) = delete;
};

fs::path findAssets(const Options& o) {
    if (o.assetsDir) return *o.assetsDir;
    // Set but empty is unset: an empty path would mean the current directory.
    if (const char* env = std::getenv("LAETICIA_ASSETS_DIR"); env != nullptr && *env != '\0')
        return env;
    if (const char* base = SDL_GetBasePath()) {
        const fs::path p = fs::path(base) / "assets";
        if (fs::exists(p / "catalog.json")) return p;
    }
    return LC_SOURCE_ASSETS_DIR;
}

fs::path findSaveDir(const Options& o) {
    if (o.saveDir) return *o.saveDir;
    if (const char* env = std::getenv("LAETICIA_SAVE_DIR"); env != nullptr && *env != '\0')
        return env;
    if (char* pref = SDL_GetPrefPath("Laeticia", "laeticias-corner")) {
        const fs::path p = pref;
        SDL_free(pref);
        return p;
    }
    return fs::current_path() / "save";
}

} // namespace

App::App(const Options& o, Catalog cat, fs::path assets)
    : opts_(o), assets_(std::move(assets)), saveDir_(findSaveDir(o)), cat_(std::move(cat)),
      world_(cat_),
      seed_(o.seed.value_or(
          o.headless ? 1
                     : static_cast<std::uint64_t>(
                           std::chrono::steady_clock::now().time_since_epoch().count()))),
      rng_(seed_), actors_(cat_, seed_), gates_(cat_.visitors.size()), weather_(cat_, seed_),
      events_(cat_, seed_), speech_(cat_, seed_), progress_(cat_), progression_(cat_),
      camera_(cat_.iso(), world_.landBounds(), 0), view_(camera_) {
    for (std::size_t v = 0; v < cat_.visitors.size(); ++v)
        gates_[v].allowed = !cat_.visitors[v].rare;
}

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
        // The interface is laid out for this size and up (QA2-11).
        if (!SDL_SetWindowMinimumSize(window_.get(), kMinWindowW, kMinWindowH))
            SDL_Log("window minimum size: %s", SDL_GetError());
        // Only a real window takes an icon; without the pictures the system's default stays.
        if (const SurfacePtr icon = loadWindowIcon(assets_ / "icon");
            icon && !SDL_SetWindowIcon(window_.get(), icon.get()))
            SDL_Log("window icon: %s", SDL_GetError());
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
    // The world's data is read and composed on a worker while the window, the renderer and the
    // art come up here: start-up waits for the longer of the two, not their sum.
    std::future<WorldLoad> worldJob;
    if (!(opts_.bench && opts_.map) && fs::exists(assets_ / "world" / "world.json"))
        worldJob = std::async(std::launch::async, [this] {
            const Uint64 t0 = SDL_GetPerformanceCounter();
            WorldLoad w{world::loadWorld(assets_, cat_), 0};
            w.ms = msBetween(t0, SDL_GetPerformanceCounter());
            return w;
        });
    if (!createWindow()) return false;
    if (!createRenderer()) return false;
    // The benchmark measures with vsync off: frame times then show what the machine can do.
    if (!opts_.headless && !SDL_SetRenderVSync(renderer_.get(), opts_.benchmark ? 0 : 1))
        SDL_Log("vsync unavailable: %s", SDL_GetError());
    if (screen_) {
        float w = 0;
        float h = 0;
        if (!SDL_GetTextureSize(screen_.get(), &w, &h)) return false;
        pixelW_ = static_cast<int>(w);
        pixelH_ = static_cast<int>(h);
    } else if (!SDL_GetRenderOutputSize(renderer_.get(), &pixelW_, &pixelH_)) {
        return false;
    }
    density_ = SDL_GetWindowPixelDensity(window_.get());
    if (density_ <= 0) density_ = 1;

    atlas_ = std::make_unique<Atlas>(renderer_.get(), assets_, cat_.iso());
    scene_ = std::make_unique<Scene>(renderer_.get(), *atlas_, cat_);
    uiBatch_ = std::make_unique<Batch>(renderer_.get());
    uiBatch_->setBand(bandTag(Band::Interface));
    blur_ = std::make_unique<Blur>(renderer_.get());
    buildThumbs();
    if (!font_.load(assets_ / "fonts")) return false;

    if (worldJob.valid() && !loadWorldData(worldJob.get())) return false;
    // The cities' life runs with the world (src/life/): the camera is its active area. It
    // keeps the map's item and slot numbers, so the home's land is cleared in the map first
    // (applying the home later renumbered them under it: an item index past the end as soon as
    // the world's layers placed anything on the home's land). It is worked out on a worker
    // while the sounds load here; nothing changes the map meanwhile.
    std::future<life::LifeSession> lifeJob;
    if (loaded_) {
        applyHomeToMap();
        lifeJob = std::async(std::launch::async,
                             [this] { return life::openLifeSession(*loaded_, seed_); });
    }
    mixer_.load(assets_ / "audio", cat_.audio);
    loadWorldAudio();
    if (lifeJob.valid()) {
        city_ = std::make_unique<life::LifeSession>(lifeJob.get());
        SDL_Log("city life: %.0f ms", city_->loadMs);
    }
    loadCityAudio();
    setupMusic();
    if (opts_.audioOut)
        mixer_.startCapture();
    else
        (void)mixer_.open();

    if (opts_.perfLog) {
        perfLog_.reset(std::fopen(opts_.perfLog->string().c_str(), "w"));
        if (!perfLog_)
            SDL_Log("perf log: cannot write %s", opts_.perfLog->string().c_str());
        else
            (void)std::fprintf(perfLog_.get(), "%s\n", kPerfHeader);
    }
    // The measuring modes build a world of their own and never touch the player's saves.
    if (!measuring()) loadOrStart();
    createWorldView();
    logo_ = atlas_->sprite(atlas_->resolve("title/logo", atlas_->placeholderBox()));
    if (!opts_.headless && !opts_.benchmark && !profile_.vsync &&
        !SDL_SetRenderVSync(renderer_.get(), 0))
        SDL_Log("vsync: %s", SDL_GetError());
    fitCameraLand();
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
    // With nobody living here, her wishes come from the tray and carry no face (Q3-08).
    if (cat_.residentKind >= 0)
        thumbs_.portrait =
            atlas_->sprite(atlas_->resolve("ui/portrait/" + cat_.resident.id, t.placeholder));
    thumbs_.tileW = cat_.iso().tileW();
}

void App::adopt(SaveData& data) {
    for (const auto& w : data.warnings) SDL_Log("save: %s", w.c_str());
    world_ = std::move(data.world);
    progress_ = std::move(data.progress);
    worldName_ = data.name.empty() ? defaultWorldName() : data.name;
    created_ = data.created.empty() ? utcNow() : data.created;
    freeBuild_ = data.freeBuild;
    played_ = data.played;
    clock_.setDay(data.day);
    seasonPin_ = data.seasonPin;
    clock_.setTime(data.clockTime);
    clock_.setPin(data.pin, false);
    weather_.setMode(data.weather);
    for (const auto& id : data.seen)
        if (const auto v = cat_.findVisitor(id)) actors_.markSeen(*v);
    if (data.camera) {
        savedCamera_ = cat_.iso().toWorld(data.camera->x, data.camera->y);
        savedZoom_ = data.zoom;
    }
    adoptWorldState(data.worldState);
    // Critters are placed once the camera exists (see run()).
}

bool App::loadWorld(const fs::path& file) {
    auto text = readTextFile(file);
    auto data = text ? deserialize(*text, cat_) : std::unexpected(text.error());
    if (data) {
        adopt(*data);
        SDL_Log("save: restored %s", file.string().c_str());
        return true;
    }
    // A world that cannot be opened (damaged, or from a newer build: living-corner §2.4, R10.3)
    // is refused and left exactly as it is: never renamed, never written over.
    const bool newer = text && saveFileVersion(*text) > kSaveVersion;
    SDL_Log("save: %s could not be opened (%s); left untouched", file.string().c_str(),
            newer ? "written by a newer version" : data.error().c_str());
    return false;
}

void App::startNewWorld(std::vector<std::string> taken, std::string name) {
    world_ = makeStarterWorld(cat_);
    progress_ = Progress(cat_);
    worldName_ = name.empty() ? defaultWorldName() : std::move(name);
    created_ = utcNow();
    slug_ = worldSlug(worldName_, taken);
}

std::string App::signedLine(std::string_view line, int giver) const {
    if (giver >= 0) {
        const std::string& who = cat_.visitors[static_cast<std::size_t>(giver)].name;
        return std::vformat(strings::kThanks, std::make_format_args(line, who));
    }
    if (cat_.residentKind >= 0)
        return std::vformat(strings::kThanks, std::make_format_args(line, cat_.resident.name));
    return std::vformat(strings::kThanksAlone, std::make_format_args(line));
}

std::string_view App::worldTip() const {
    if (!hoverTip_.empty()) return hoverTip_;
    // An empty hand over an actor names it (she answers to her name; visitors to theirs).
    // Only over the map: a panel under the pointer clears hover_ (worldInput).
    if (tool_ != Tool::None || photo_ || !hover_) return {};
    const auto who = actorUnder(mouse_);
    if (!who) return {};
    const ActorKind& k = cat_.kinds[actors_.all()[static_cast<std::size_t>(*who)].kind];
    return k.visitor >= 0
               ? std::string_view(cat_.visitors[static_cast<std::size_t>(k.visitor)].name)
               : std::string_view(cat_.resident.name);
}

std::string App::defaultWorldName() const {
    // Named after whoever lives there, as data says; nobody: a plain name.
    return cat_.residentKind >= 0
               ? std::vformat(strings::kDefaultWorldOf, std::make_format_args(cat_.resident.name))
               : std::string(strings::kDefaultWorldAlone);
}

void App::loadOrStart() {
    std::error_code ec;
    if (auto text = readTextFile(saveDir_ / kProfileFile)) profile_ = parseProfile(*text);
    muted_ = profile_.muted;
    brush_ = profile_.brush;
    grid_ = profile_.grid;
    const fs::path worlds = saveDir_ / kWorldsDir;
    const fs::path legacy = saveDir_ / kLegacyFile;

    // A save from before worlds existed becomes the first world (docs/design/living-corner.md
    // §2.5). It is renamed only once the new world and its thumbnail are written; if it cannot
    // be read it is left alone and the game starts as on a first launch.
    // Also when a `worlds` folder exists but holds no world yet (a crash in the middle of an
    // earlier migration), so the old corner is never ignored (QA2-13).
    const auto anyWorld = [&] {
        for (auto it = fs::directory_iterator(worlds, ec); !ec && it != fs::directory_iterator();
             it.increment(ec))
            if (fs::exists(it->path() / kWorldFile, ec)) return true;
        ec.clear();
        return false;
    };
    if (fs::exists(legacy, ec) && !anyWorld()) {
        auto text = readTextFile(legacy);
        auto data = text ? deserialize(*text, cat_) : std::unexpected(text.error());
        if (data && data->fromVersion < 3) {
            migrateLegacy(*data, cat_);
            if (data->muted) muted_ = true;
            adopt(*data);
            slug_ = worldSlug(worldName_, {});
            legacyToRetire_ = legacy;
            welcomePending_ = true;
            SDL_Log("save: migrated %s", legacy.string().c_str());
            return;
        }
        SDL_Log("save: %s could not be migrated (%s); left as it is", legacy.string().c_str(),
                data ? "not an older save" : data.error().c_str());
    }

    std::vector<std::string> taken;
    fs::path newest;
    fs::file_time_type newestTime{};
    for (auto it = fs::directory_iterator(worlds, ec); !ec && it != fs::directory_iterator();
         it.increment(ec)) {
        if (!it->is_directory(ec)) continue;
        taken.push_back(it->path().filename().string());
        const fs::path file = it->path() / kWorldFile;
        const auto t = fs::last_write_time(file, ec);
        if (ec) {
            ec.clear();
            continue;
        }
        if (newest.empty() || t > newestTime) {
            newest = it->path();
            newestTime = t;
        }
    }
    // The world played last, else the most recently saved one, else a new one.
    fs::path dir = newest;
    if (plainFolderName(profile_.lastWorld) &&
        fs::exists(worlds / profile_.lastWorld / kWorldFile, ec))
        dir = worlds / profile_.lastWorld;
    if (!dir.empty()) {
        slug_ = dir.filename().string();
        if (loadWorld(dir / kWorldFile)) return;
        // A fresh corner in a folder of its own, beside the world that could not be opened.
        startNewWorld(taken);
        freshWorld_ = true;
        if (!frontDoor()) hud_.toast(std::string(strings::kToastNotOpened));
        return;
    }
    startNewWorld(taken);
    freshWorld_ = true;
}

bool App::save(bool wait) {
    // A measuring world is never saved: nothing is gathered for it either, and the autosave
    // rests (it would otherwise come due again every step and be measured as the game's work).
    if (measuring()) {
        autosave_.saved();
        return true;
    }
    SaveData data(world_, cat_);
    data.progress = progress_;
    data.name = worldName_;
    data.freeBuild = freeBuild_;
    data.created = created_;
    data.played = played_;
    data.clockTime = clock_.time();
    data.pin = clock_.pin();
    data.day = clock_.day();
    data.seasonPin = seasonPin_;
    data.weather = weather_.mode();
    for (std::size_t v = 0; v < cat_.visitors.size(); ++v)
        if (actors_.seen(static_cast<int>(v))) data.seen.push_back(cat_.visitors[v].id);
    if (scene_) {
        data.camera = cat_.iso().toTile(camera_.position());
        data.zoom = camera_.zoom();
    }
    data.worldState = worldState();
    // The front door's preview of a new corner is not a world until it is begun.
    if (freshWorld_ && frontDoor()) return true;
    // The text is made here; the writing (and its flush to disk) happens on the writer's thread,
    // so an autosave never stalls a frame. `wait` is for the moments that need it on disk now.
    writer_.write(worldDir() / kWorldFile, serialize(data, cat_));
    profile_.muted = muted_;
    profile_.lastWorld = slug_;
    if (std::string text = serialize(profile_); text != profileWritten_) {
        profileWritten_ = text;
        writer_.write(saveDir_ / kProfileFile, std::move(text));
    }
    autosave_.saved();
    if (!wait) return true;
    writer_.flush();
    return pollSaves();
}

void App::saveFailed(const std::string& why) {
    SDL_Log("save: %s", why.c_str());
    if (!saveFailing_) hud_.toast(std::string(strings::kToastSaveFailed));
    saveFailing_ = true;
    profileWritten_.clear(); // write the profile again with the next save
    autosave_.changed();     // still unsaved: try again after the retry delay
    autosave_.failed();
}

bool App::pollSaves() {
    const FileWriter::Outcome o = writer_.poll();
    if (o.error) {
        saveFailed(*o.error);
        return false;
    }
    if (o.finished) saveFailing_ = false;
    return !saveFailing_;
}

bool App::writeThumbnail() {
    const TexturePtr target{SDL_CreateTexture(renderer_.get(), kTextureFormat,
                                              SDL_TEXTUREACCESS_TARGET, kThumbW, kThumbH)};
    if (!target) {
        SDL_Log("thumbnail: %s", SDL_GetError());
        return false;
    }
    const Vec2 size{static_cast<float>(kThumbW), static_cast<float>(kThumbH)};
    Camera cam(cat_.iso(), world_.landBounds(), scene_->cliffDepth());
    cam.frame({0, 0, size.x, size.y}, size, openBounds(cat_, progress_.stage, world_));
    FrameParams p;
    p.world = &world_;
    p.actors = actors_.all();
    p.resident = actors_.resident();
    p.weather = &weather_;
    p.camera = &cam;
    p.screen = size;
    p.light = lighting();
    drawScene(p, target.get());
    if (!SDL_SetRenderTarget(renderer_.get(), target.get()))
        SDL_Log("thumbnail: %s", SDL_GetError());
    const SurfacePtr pixels{SDL_RenderReadPixels(renderer_.get(), nullptr)};
    if (!SDL_SetRenderTarget(renderer_.get(), screenTarget()))
        SDL_Log("thumbnail: %s", SDL_GetError());
    std::error_code ec;
    fs::create_directories(worldDir(), ec);
    const fs::path file = worldDir() / kThumbFile;
    fs::path tmp = file;
    tmp += ".tmp";
    if (!pixels || !SDL_SavePNG(pixels.get(), tmp.string().c_str())) {
        SDL_Log("thumbnail: %s", SDL_GetError());
        fs::remove(tmp, ec);
        return false;
    }
    fs::rename(tmp, file, ec);
    if (ec) SDL_Log("thumbnail: %s", ec.message().c_str());
    return !ec;
}

CondFacts App::facts() const {
    CondFacts f;
    f.phase = clock_.phase();
    f.season = season();
    // Rain on the land, not where the camera happens to look (Q3-03).
    f.raining = weather_.rainingOnLand();
    f.present = actors_.presence();
    f.seen = actors_.seenFlags();
    f.harvestedToday = progress_.harvests > 0 && progress_.lastHarvestDay == clock_.day();
    // Her wishes come from her when she is about; with no resident, by day.
    f.residentAbout =
        cat_.residentKind >= 0 ? actors_.residentAvailable() : clock_.phase() != Phase::Night;
    f.nookHere = progression_.nookHere();
    using C = Counter;
    const auto at = [&](C c) -> int& { return f.counters[static_cast<std::size_t>(c)]; };
    at(C::Wishes) = static_cast<int>(progress_.granted.size());
    at(C::Seen) = actors_.seenCount();
    at(C::Nooks) = progress_.nooksFound();
    at(C::Pages) = at(C::Seen) + at(C::Nooks);
    at(C::Harvests) = progress_.harvests;
    at(C::Stage) = progress_.stage;
    return f;
}

void App::updateProgress() {
    const CondFacts f = facts();
    // Facts that change rarely trigger an evaluation at once; world edits are debounced and
    // wait for a drag to end, so a stroke counts once.
    std::uint64_t key = static_cast<std::uint64_t>(f.phase) |
                        (static_cast<std::uint64_t>(f.season) << 4) |
                        (static_cast<std::uint64_t>(f.raining) << 8) |
                        (static_cast<std::uint64_t>(f.residentAbout) << 9);
    for (const int n : f.present) key = key * 31 + static_cast<std::uint64_t>(n);
    for (const int c : f.counters) key = key * 131 + static_cast<std::uint64_t>(c);
    bool evaluate = key != factsKey_;
    factsKey_ = key;
    if (world_.revision() != evalRevision_ && !editor_.inGroup()) {
        if (evalDue_ < 0) evalDue_ = played_ + tuning::kConditionDebounce;
        if (played_ >= evalDue_) {
            evaluate = true;
            evalRevision_ = world_.revision();
            evalDue_ = -1;
        }
    }
    if (evaluate) {
        progression_.evaluate(world_, progress_, f, played_);
        unlockStems(f, loading_);
    }
    // Nothing is judged in the middle of a stroke: a passing state during a drag never counts
    // (docs/design/living-corner.md §3.3).
    if (!editor_.inGroup()) progression_.tick(world_, progress_, f, played_, !photo_, rng_);
    // Who may come: the season allows them (rare visitors also by their recipe, in Progression).
    const auto bit = static_cast<std::uint8_t>(1u << season());
    for (std::size_t v = 0; v < gates_.size(); ++v) {
        gates_[v].allowed = cat_.visitors[v].rare ? progression_.rareHere(static_cast<int>(v))
                                                  : (cat_.visitors[v].seasons & bit) != 0;
        gates_[v].extra = progression_.extraVisitors(static_cast<int>(v));
    }
    // What was already there when the world opened is found quietly (a migrated world's nooks).
    const bool quiet = std::exchange(loading_, false);
    for (const ProgressEvent& e : progression_.events()) {
        if (quiet && e.kind == ProgressEvent::Kind::NookFound) {
            markDirty();
            continue;
        }
        switch (e.kind) {
        case ProgressEvent::Kind::WishOffered: {
            play(sfx::kWish);
            const int giver = cat_.wishes[static_cast<std::size_t>(e.index)].giver;
            if (giver < 0) {
                // From her in the world: the bubble and the card arrive together.
                (void)speak(cat_.resident.context(e.already ? "already_done" : "wish_offer"),
                            SpeechWeight::Important);
                break;
            }
            for (const Actor& a : actors_.all())
                if ((a.flags & actor_flag::kAlive) != 0 && (a.flags & actor_flag::kLeaving) == 0 &&
                    cat_.kinds[a.kind].visitor == giver) {
                    scene_->burst(a.pos, rng_);
                    break;
                }
            break;
        }
        case ProgressEvent::Kind::WishGranted: onWishGranted(e.index); break;
        case ProgressEvent::Kind::NookFound: onNookFound(e.index); break;
        // A world opening with enough pages (a migrated one) gets its land without the wave.
        case ProgressEvent::Kind::StageOpens: openLand(e.index, !quiet); break;
        }
        markDirty();
    }
    progression_.clearEvents();
    // A world that opens with enough pages for more land (a migrated one) gets it at once, with
    // its reveals but without the wave.
    if (quiet)
        while (nextStagePages(cat_, progress_.stage) >= 0 &&
               pages() >= nextStagePages(cat_, progress_.stage))
            openLand(++progress_.stage, false);
}

void App::growBeds(float seconds) {
    const bool snow = cat_.seasons[static_cast<std::size_t>(season())].snow;
    const float seasonGrowth = cat_.seasons[static_cast<std::size_t>(season())].growth;
    anyRipe_ = false;
    for (std::size_t i = 0; i < world_.items().size(); ++i) {
        const Item& it = world_.items()[i];
        if (cat_.items[it.type].growth.stages == 0) continue;
        // Rain where the bed is (not snow) makes it grow faster.
        const bool rain = !snow && weather_.raining({static_cast<float>(it.pos.x) + 0.5f,
                                                     static_cast<float>(it.pos.y) + 0.5f});
        const float rate = growthRate(world_, cat_, it.rect(), rain, seasonGrowth,
                                      progression_.nookGrowth(world_, it.rect()));
        if (grow(world_, cat_, i, seconds, rate)) {
            scene_->popAt(it.pos);
            markDirty();
        }
        anyRipe_ = anyRipe_ || ripe(cat_, world_.items()[i]);
    }
}

bool App::pick(TilePos t) {
    const auto idx = world_.itemIndexAt(t);
    if (!idx || !ripe(cat_, world_.items()[*idx])) return false;
    const Item bed = world_.items()[*idx];
    harvest(world_, *idx);
    editor_.dropRedo();
    ++progress_.harvests;
    progress_.lastHarvestDay = clock_.day();
    playAt(sfx::kHarvest, tuning::kSfxLevel,
           {static_cast<float>(t.x) + 0.5f, static_cast<float>(t.y) + 0.5f}, true);
    scene_->produce(bed, bed.variant);
    // Hens come for what fell; she takes it home if she is near.
    (void)actors_.harvested(actorEnv(), bed.pos);
    lively_.happening(simTime_);
    markDirty();
    return true;
}

void App::playNote() {
    // Notes closer together than a quick drag's step are skipped (the phrase does not move).
    if (lastNote_ >= 0 && simTime_ - lastNote_ < tuning::kNoteMinGap) return;
    lastNote_ = simTime_;
    const int n = notes_.next(simTime_, rng_);
    if (std::cmp_less(n, cat_.audio.notes.size()))
        play(cat_.audio.notes[static_cast<std::size_t>(n)], tuning::kSfxLevel * tuning::kNoteLevel);
}

int App::pages() const {
    return actors_.seenCount() + progress_.nooksFound();
}

void App::fitCameraLand() {
    // The view stays near the land that is open, with a margin of wild land to look at; the bench
    // and soak worlds are open everywhere.
    TileRect r = openBounds(cat_, progress_.stage, world_);
    const int m = tuning::kCameraOpenMargin;
    r = TileRect{r.x0 - m, r.y0 - m, r.x1 + m, r.y1 + m}.clipped(world_.landBounds());
    if (loaded_ && !measuring()) {
        // In the world the camera roams over all of it.
        camera_.setLand(cameraLand(), 0, 0);
        return;
    }
    camera_.setLand(measuring() ? world_.landBounds() : r, scene_->cliffDepth());
}

void App::openLand(int stage, bool wave) {
    std::vector<Item> revealed;
    openStage(world_, cat_, stage, revealed);
    fitCameraLand();
    markDirty();
    if (!wave) return;
    (void)scene_->landWave(world_, cat_, stage, revealed);
    play(sfx::kLandOpen);
    const StageDef& def = cat_.stages[static_cast<std::size_t>(stage)];
    if (!def.line.empty()) (void)speakText(def.line, SpeechWeight::Important);
    cornerToast(std::vformat(strings::kToastNewLand, std::make_format_args(def.name)));
    // The camera never moves on its own: when the new land is out of sight, a chip offers it.
    TileRect box = def.rects.front();
    for (const TileRect& r : def.rects)
        box = {std::min(box.x0, r.x0), std::min(box.y0, r.y0), std::max(box.x1, r.x1),
               std::max(box.y1, r.y1)};
    const auto f = [](int v) { return static_cast<float>(v); };
    edgeChipTarget_ = cat_.iso().toWorld(f(box.x0 + box.x1) * 0.5f, f(box.y0 + box.y1) * 0.5f);
    const Vec2 at = camera_.worldToScreen(edgeChipTarget_, screen());
    const Box safe = hud_.safeArea();
    if (!safe.contains(at.x, at.y)) edgeChipUntil_ = simTime_ + tuning::kEdgeChipSeconds;
}

void App::onWishGranted(int wish) {
    const WishDef& def = cat_.wishes[static_cast<std::size_t>(wish)];
    play(sfx::kWishGranted);
    Ribbon r;
    r.title = strings::kWishGranted;
    const Reward& rw = def.reward;
    if (!rw.items.empty() || !rw.terrain.empty()) {
        r.text = strings::kNewInBuild;
        const auto add = [&](const std::string& name, const Sprite& icon) {
            r.text += (r.iconCount == 0 ? " " : ", ") + name;
            if (r.iconCount < static_cast<int>(r.icons.size()))
                r.icons[static_cast<std::size_t>(r.iconCount++)] = icon;
        };
        for (const int t : rw.terrain)
            add(cat_.terrain[static_cast<std::size_t>(t)].name,
                thumbs_.terrain[static_cast<std::size_t>(t)]);
        for (const int i : rw.items)
            add(cat_.items[static_cast<std::size_t>(i)].name,
                thumbs_.items[static_cast<std::size_t>(i)]);
    } else if (rw.frame >= 0) {
        r.text = std::vformat(
            strings::kNewFrame,
            std::make_format_args(cat_.frames[static_cast<std::size_t>(rw.frame)].name));
    } else if (rw.clue >= 0) {
        r.text = cat_.residentKind >= 0
                     ? std::vformat(strings::kNoteAdded, std::make_format_args(cat_.resident.name))
                     : std::string(strings::kNoteAddedAlone);
    }
    // Signed by whoever made the wish: a visitor, the resident, or nobody when nobody lives here.
    r.quote = signedLine(def.thanks, def.giver);
    hud_.ribbon(std::move(r));
}

void App::onNookFound(int nook) {
    const NookDef& def = cat_.nooks[static_cast<std::size_t>(nook)];
    play(sfx::kNook);
    const int pages = actors_.seenCount() + progress_.nooksFound();
    const int total = static_cast<int>(cat_.visitors.size() + cat_.nooks.size());
    cornerToast(
        std::vformat(strings::kToastNewNook, std::make_format_args(def.name, pages, total)));
    lively_.happening(simTime_);
    std::vector<NearInstance> found;
    cat_.conditions.instances(def.near, world_, found);
    if (found.empty()) return;
    const NearInstance& in = found.front();
    scene_->flourish(in, world_, rng_);
    // She walks over, if she is near and free, and says something about it.
    actors_.visit(actorEnv(),
                  {static_cast<float>(in.footprint.x0 + in.footprint.x1) * 0.5f,
                   static_cast<float>(in.footprint.y0 + in.footprint.y1) * 0.5f},
                  cat_.resident.context("nook_found"), tuning::kNookVisitReach);
    const auto f = [](int v) { return static_cast<float>(v); };
    const TileRect& r = in.footprint;
    Vec2 top = cat_.iso().toWorld(f(r.x0 + r.x1) * 0.5f, f(r.y0 + r.y1) * 0.5f);
    top.y -= cat_.iso().tileH() * tuning::kNookLabelLift;
    nookLabels_.push_back({nook, top, simTime_});
}

void App::updateHoverNook() {
    // Recomputed only when the pointer changes tile or the world changes. Wild land explains
    // itself to every tool; nooks and the gate answer an empty hand.
    const std::optional<TilePos> tile =
        tool_ == Tool::None || (hover_ && world_.isWild(*hover_)) ? hover_ : std::nullopt;
    if (tile == hoverNookTile_ && world_.revision() == hoverNookRevision_) return;
    hoverNookTile_ = tile;
    hoverNookRevision_ = world_.revision();
    hoverNook_.clear();
    hoverTip_ = {};
    if (!tile) return;
    if (world_.isWild(*tile)) {
        const int at = nextStagePages(cat_, stageAt(cat_, *tile) - 1);
        const int more = std::max(0, at - pages());
        hoverTipText_ = std::vformat(strings::kTipWild, std::make_format_args(at, more));
        hoverTip_ = hoverTipText_;
        return;
    }
    if (const Item* it = world_.itemAt(*tile); it && ripe(cat_, *it)) {
        hoverTip_ = strings::kTipRipe;
        return;
    }
    if (const Item* it = world_.itemAt(*tile); it && cat_.gate && it->rect().contains(*cat_.gate)) {
        hoverTip_ = strings::kTipGate;
        return;
    }
    std::vector<NearInstance> found;
    for (std::size_t n = 0; n < cat_.nooks.size() && hoverNook_.empty(); ++n) {
        if (progression_.nookHere()[n] == 0) continue;
        cat_.conditions.instances(cat_.nooks[n].near, world_, found);
        for (const NearInstance& in : found)
            if (in.footprint.contains(*tile)) {
                hoverNook_.push_back(in);
                hoverTip_ = cat_.nooks[n].name;
                break;
            }
    }
}

std::string_view App::waitingText(int node, std::string& out) const {
    const CondNode& n = cat_.conditions.node(node);
    const auto bit = [&](int i) { return ((n.mask >> i) & 1) != 0; };
    switch (n.kind) {
    case CondKind::Time: {
        // The first listed phase still to come today.
        static constexpr std::string_view kText[] = {strings::kWaitDay, strings::kWaitDusk,
                                                     strings::kWaitNight, strings::kWaitDawn};
        const int now = static_cast<int>(clock_.phase());
        for (int k = 1; k <= 4; ++k)
            if (bit((now + k) % 4)) return kText[(now + k) % 4];
        return {};
    }
    case CondKind::Season: {
        // The first listed season still to come from now (QA2-15).
        const int count = static_cast<int>(cat_.seasons.size());
        const int now = season();
        for (int k = 1; k <= count; ++k)
            if (bit((now + k) % count)) {
                std::string name = cat_.seasons[static_cast<std::size_t>((now + k) % count)].name;
                if (!name.empty())
                    name[0] = static_cast<char>(std::tolower(static_cast<unsigned char>(name[0])));
                out = std::vformat(strings::kWaitSeason, std::make_format_args(name));
                return out;
            }
        return {};
    }
    case CondKind::Weather: return n.mask != 0 ? strings::kWaitRain : strings::kWaitClear;
    default: return {};
    }
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
    cancelMove();
    shape_ = Shape::None;
    pipette_ = false;
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
        cancelMove();
        if (editor_.inGroup()) editor_.commit();
        drag_ = Drag::None;
        frameIndex_ = postcardFrame();
        menus_.hideBar(false);
        menus_.wakeBar();
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
        if (op.kind == Op::Kind::Add) {
            scene_->onPlaced(op.item, rng_);
            disturbed(op.item.rect(), op.item.type, false);
        } else if (op.kind == Op::Kind::Remove) {
            scene_->onRemoved(op.item);
            disturbed(op.item.rect(), -2, false);
        }
    }
    if (!ops.empty()) markDirty();
}

void App::undoRedo(bool redo) {
    // Undo in the middle of a drag ends the drag: the stroke so far is one step and is undone
    // whole, and nothing more is drawn until the button is pressed again.
    if (drag_ == Drag::Tool) drag_ = Drag::None;
    shape_ = Shape::None;
    cancelMove(); // a piece in hand goes back first
    const auto ops = redo ? editor_.redo(world_) : editor_.undo(world_);
    if (!ops.empty()) play(redo ? sfx::kRedo : sfx::kUndo);
    feedback(ops);
}

void App::zoomBy(int steps, Vec2 px) {
    tourMoved_ = true;
    // Zooming out past the widest view opens the world's map (world-tech §4.7).
    if (steps < 0 && camera_.level() == 0 && loaded_ && !map_.isOpen()) {
        toggleMap();
        return;
    }
    camera_.zoomTo(camera_.level() + steps, px, screen());
}

void App::frameCamera() {
    follow_.reset(); // the camera goes elsewhere: it no longer follows anyone
    const Box s = hud_.safeArea();
    camera_.frame({s.x, s.y, s.x + s.w, s.y + s.h}, screen(),
                  openBounds(cat_, progress_.stage, world_));
    keepOnHome(camera_);
}

void App::keepOnHome(Camera& c) const {
    // The land is framed in the room the interface leaves; with a large interface on a small
    // window that can put the window's centre off the home's grid, and the home's own panels
    // (the building dock among them) would fold away as if the player had left (H3-016). The
    // view slides the least it must to stand on the home again.
    if (!loaded_) return;
    const Vec2 t = cat_.iso().toTile(c.position());
    constexpr float kIn = 0.5f; // tiles inside the grid's edge
    const Vec2 k{std::clamp(t.x, kIn, static_cast<float>(world_.width()) - kIn),
                 std::clamp(t.y, kIn, static_cast<float>(world_.height()) - kIn)};
    if (k.x != t.x || k.y != t.y) c.place(cat_.iso().toWorld(k.x, k.y), c.zoom(), screen());
}

void App::handleKey(const SDL_KeyboardEvent& k) {
    const SDL_Keycode key = k.key;
    // Modifiers as the keys say, so clicks can read them (synthesized input included).
    mods_ = k.mod;
    const auto modBit = [](SDL_Keycode c) -> SDL_Keymod {
        switch (c) {
        case SDLK_LSHIFT: return SDL_KMOD_LSHIFT;
        case SDLK_RSHIFT: return SDL_KMOD_RSHIFT;
        case SDLK_LALT: return SDL_KMOD_LALT;
        case SDLK_RALT: return SDL_KMOD_RALT;
        case SDLK_LCTRL: return SDL_KMOD_LCTRL;
        case SDLK_RCTRL: return SDL_KMOD_RCTRL;
        default: return SDL_KMOD_NONE;
        }
    };
    if (const SDL_Keymod bit = modBit(key); bit != SDL_KMOD_NONE)
        mods_ = static_cast<SDL_Keymod>(k.down ? (mods_ | bit) : (mods_ & ~bit));
    const bool ctrl = (k.mod & SDL_KMOD_CTRL) != 0;
    const bool shift = (k.mod & SDL_KMOD_SHIFT) != 0;
    // While a page of the menus is open (or a name is being typed) the keys are theirs.
    if (k.down && (menus_.blocking() || menus_.editing())) {
        const auto menuKey = [&]() -> std::optional<MenuKey> {
            switch (key) {
            case SDLK_UP: return MenuKey::Up;
            case SDLK_DOWN: return MenuKey::Down;
            case SDLK_LEFT: return MenuKey::Left;
            case SDLK_RIGHT: return MenuKey::Right;
            case SDLK_RETURN:
            case SDLK_KP_ENTER: return MenuKey::Enter;
            case SDLK_ESCAPE: return MenuKey::Escape;
            case SDLK_BACKSPACE: return MenuKey::Backspace;
            default: return std::nullopt;
            }
        }();
        if (menuKey) {
            (void)menus_.key(*menuKey, menuModel());
            return;
        }
        if (menus_.editing()) return; // letters arrive as text input
        if (key == SDLK_F11)
            setFullscreen((SDL_GetWindowFlags(window_.get()) & SDL_WINDOW_FULLSCREEN) == 0);
        if (key == SDLK_M && ctrl) toggleMute();
        return;
    }
    if (!k.down && (menus_.blocking() || menus_.editing())) {
        // A key let go under the menus still lets go: a pan held into the pause menu used to
        // carry the camera away by itself after Resume.
        std::ranges::fill(keyPan_, false);
        footprintsHeld_ = false;
        return;
    }
    // Held Tab shows every footprint and nook; it lets go when released.
    if (key == SDLK_TAB) {
        footprintsHeld_ = k.down && !photo_;
        return;
    }
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
    // While the sketchbook is open the arrows turn its pages (WASD still pans).
    if (journalOpen_ && !photo_ && (key == SDLK_LEFT || key == SDLK_RIGHT)) {
        if (k.down && !k.repeat) {
            hud_.turnPage(key == SDLK_LEFT ? -1 : 1, ui_);
            play(sfx::kPage, tuning::kUiSfxLevel);
        }
        return;
    }
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
        if (follow_)
            follow_.reset();
        else if (map_.isOpen())
            toggleMap();
        else if (cardOpen_)
            closeCard();
        else if (photo_)
            togglePhoto();
        else if (carry_)
            cancelMove();
        else if (pipette_)
            pipette_ = false;
        else if (shape_ != Shape::None) {
            shape_ = Shape::None;
            drag_ = Drag::None;
        } else if (hud_.calendarOpen())
            hud_.closeCalendar();
        else if (tool_ != Tool::None)
            setTool(Tool::None, -1);
        else if (drawerOpen_) {
            drawerOpen_ = false;
            play(sfx::kClose, tuning::kUiSfxLevel);
        } else if (journalOpen_) {
            journalOpen_ = false;
            play(sfx::kClose, tuning::kUiSfxLevel);
        } else if (frontDoor()) {
            menus_.open(Page::Pause); // nothing left to cancel: the pause menu
        }
        return;
    case SDLK_F11:
        setFullscreen((SDL_GetWindowFlags(window_.get()) & SDL_WINDOW_FULLSCREEN) == 0);
        return;
    case SDLK_F3: profilerOn_ = !profilerOn_; return;
    case SDLK_P: togglePhoto(); return;
    case SDLK_F:
    case SDLK_T:
    case SDLK_H:
        // F follows the living figure whose card is open (Esc or a pan lets go).
        if (!photo_ && key == SDLK_F && cardOpen_ && city_ && city_->city->alive(cardActor_)) {
            follow_ = cardActor_;
            return;
        }
        if (!photo_) break;
        // The photo bar's keys: next frame, caption, hide the bar.
        if (key == SDLK_F) cycleFrame(1);
        if (key == SDLK_T) {
            profile_.caption = !profile_.caption;
            profileChanged();
        }
        if (key == SDLK_H) menus_.hideBar(!menus_.barHidden());
        menus_.wakeBar();
        return;
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
        if (ctrl) {
            toggleMute();
        } else if (!photo_) {
            toggleMap();
        }
        return;
    default: break;
    }
    if (photo_) return; // editing keys do nothing while framing a photo
    // Away from home the home's tools rest: no unseen undo, no armed eyedropper (L-108).
    static constexpr SDL_Keycode kEditing[] = {SDLK_Z, SDLK_Y,           SDLK_R,
                                               SDLK_B, SDLK_X,           SDLK_V,
                                               SDLK_I, SDLK_LEFTBRACKET, SDLK_RIGHTBRACKET};
    if (away() && std::ranges::find(kEditing, key) != std::end(kEditing)) return;

    switch (key) {
    case SDLK_Z:
        if (ctrl) undoRedo(shift);
        break;
    case SDLK_Y:
        if (ctrl) undoRedo(true);
        break;
    case SDLK_R:
        if (tool_ == Tool::Place || carry_) {
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
    case SDLK_V: setTool(tool_ == Tool::Move ? Tool::None : Tool::Move, -1); break;
    case SDLK_I: pipette_ = !pipette_; break;
    case SDLK_LEFTBRACKET:
    case SDLK_RIGHTBRACKET: {
        // Brush sizes 1, 3, 5.
        const auto& sizes = tuning::kBrushSizes;
        const auto at = std::ranges::find(sizes, brush_) - std::begin(sizes);
        const auto n = static_cast<std::ptrdiff_t>(std::size(sizes));
        brush_ = sizes[static_cast<std::size_t>(
            std::clamp<std::ptrdiff_t>(at + (key == SDLK_RIGHTBRACKET ? 1 : -1), 0, n - 1))];
        profile_.brush = brush_;
        markDirty();
        break;
    }
    case SDLK_G:
        grid_ = !grid_;
        profile_.grid = grid_;
        markDirty();
        break;
    case SDLK_J:
        journalOpen_ = !journalOpen_;
        play(journalOpen_ ? sfx::kOpen : sfx::kClose, tuning::kUiSfxLevel);
        break;
    case SDLK_C: cycleClock(); break;
    case SDLK_N: cycleWeather(); break;
    default: break;
    }
}

void App::handleEvent(const SDL_Event& e) {
    switch (e.type) {
    case SDL_EVENT_QUIT: running_ = false; break;
    case SDL_EVENT_WINDOW_PIXEL_SIZE_CHANGED:
    case SDL_EVENT_WINDOW_RESIZED:
    case SDL_EVENT_WINDOW_MOVED:
        // (The offscreen frame keeps its size: it has no window to follow.)
        if (!screen_ && !SDL_GetRenderOutputSize(renderer_.get(), &pixelW_, &pixelH_))
            SDL_Log("%s", SDL_GetError());
        density_ = std::max(1.0f, SDL_GetWindowPixelDensity(window_.get()));
        if ((SDL_GetWindowFlags(window_.get()) & SDL_WINDOW_FULLSCREEN) == 0) {
            WindowRect& r = windowState_.windowed;
            if (!SDL_GetWindowPosition(window_.get(), &r.x, &r.y) ||
                !SDL_GetWindowSize(window_.get(), &r.w, &r.h))
                SDL_Log("window: %s", SDL_GetError());
        }
        break;
    case SDL_EVENT_WINDOW_MINIMIZED:
    case SDL_EVENT_WINDOW_HIDDEN: hidden_ = true; break;
    case SDL_EVENT_WINDOW_RESTORED:
    case SDL_EVENT_WINDOW_SHOWN:
    case SDL_EVENT_WINDOW_EXPOSED: hidden_ = false; break;
    case SDL_EVENT_WINDOW_FOCUS_LOST:
        // Keys released while another window has focus never arrive here.
        std::ranges::fill(keyPan_, false);
        mods_ = SDL_KMOD_NONE;
        footprintsHeld_ = false;
        break;
    case SDL_EVENT_WINDOW_MOUSE_ENTER: mouseInside_ = true; break;
    case SDL_EVENT_WINDOW_MOUSE_LEAVE: mouseInside_ = false; break;
    case SDL_EVENT_MOUSE_MOTION: {
        const Vec2 p{e.motion.x * density_, e.motion.y * density_};
        mouseInside_ = true;
        if (drag_ == Drag::Pan && (p.x != lastPan_.x || p.y != lastPan_.y)) {
            camera_.dragBy({p.x - lastPan_.x, p.y - lastPan_.y}, screen());
            tourMoved_ = true;
            follow_.reset(); // a pan takes the camera back
        }
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
            if (e.button.button == SDL_BUTTON_RIGHT)
                (e.button.down ? rightPressed_ : rightReleased_) = true;
            if (e.button.down && drag_ == Drag::None) {
                // The pan starts in worldInput, once the interface has had its say: a right
                // click on a wish card opens its menu instead.
                panPending_ = true;
                rightDown_ = true;
                rightStart_ = mouse_;
            } else if (!e.button.down && rightDown_) {
                panPending_ = false;
                rightDown_ = false;
                if (drag_ == Drag::Pan) drag_ = Drag::None;
                // A right click without dragging cancels the current tool.
                const float moved = std::hypot(mouse_.x - rightStart_.x, mouse_.y - rightStart_.y);
                const bool click = moved < tuning::kClickSlop * density_;
                if (click && e.button.button == SDL_BUTTON_RIGHT) {
                    // Right click puts a piece in hand back, else lets go of the tool.
                    if (carry_)
                        cancelMove();
                    else if (pipette_)
                        pipette_ = false;
                    else if (tool_ != Tool::None)
                        setTool(Tool::None, -1);
                } else if (click && e.button.button == SDL_BUTTON_MIDDLE) {
                    middleClick_ = true;
                }
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
    case SDL_EVENT_TEXT_INPUT:
        if (e.text.text != nullptr) (void)menus_.text(e.text.text, font_);
        break;
    default: break;
    }
}

HudModel App::model() const {
    HudModel m;
    m.cat = &cat_;
    m.thumbs = &thumbs_;
    m.visitors = &actors_;
    m.progress = &progress_;
    cards_.clear();
    // One detail line per card, each in its own string, so no card's text points into another's.
    if (cardDetail_.size() < progress_.open.size()) cardDetail_.resize(progress_.open.size());
    for (std::size_t i = 0; i < progress_.open.size(); ++i) {
        const int w = progress_.open[i];
        const WishDef& def = cat_.wishes[static_cast<std::size_t>(w)];
        const WishStatus& st = progression_.status(w);
        WishCard c;
        c.wish = w;
        c.text = def.text;
        c.portrait = def.giver < 0 ? thumbs_.portrait
                                   : thumbs_.visitors[static_cast<std::size_t>(def.giver)];
        c.ready = st.ready;
        std::string& detail = cardDetail_[i];
        detail.clear();
        if (st.count >= 0 && !def.progress.empty()) {
            c.progress = static_cast<float>(st.count) / static_cast<float>(std::max(1, st.min));
            std::format_to(std::back_inserter(detail), strings::kWishCount,
                           std::min(st.count, st.min), st.min, def.progress);
            c.detail = detail;
        } else if (st.waiting >= 0) {
            c.detail = waitingText(st.waiting, detail);
        }
        cards_.push_back(c);
    }
    m.wishes = cards_;
    m.worldTip = worldTip();
    floatLabels_.clear();
    for (const NookLabel& l : nookLabels_) {
        const auto k = static_cast<float>((simTime_ - l.start) / tuning::kNookLabelSeconds);
        const float fade = std::min({1.0f, k * 6.0f, (1.0f - k) * 4.0f});
        floatLabels_.push_back({view_.worldToScreen(l.world, screen()),
                                cat_.nooks[static_cast<std::size_t>(l.nook)].name, fade});
    }
    // Held Tab names every nook in a small pill over its anchor.
    if (footprintsHeld_)
        for (const NookPlace& n : nookPlaces_) {
            const TileRect& r = n.area.footprint;
            const Vec2 top = cat_.iso().toWorld(static_cast<float>(r.x0 + r.x1) * 0.5f,
                                                static_cast<float>(r.y0 + r.y1) * 0.5f);
            floatLabels_.push_back({view_.worldToScreen(top, screen()),
                                    cat_.nooks[static_cast<std::size_t>(n.nook)].name, 1.0f});
        }
    m.labels = floatLabels_;
    m.edgeChip = simTime_ < edgeChipUntil_;
    m.worldName = worldName_;
    m.season = season();
    m.seasonDay = seasonOf(clock_.day(), cat_.seasonDays).day;
    m.seasonPin = seasonPin_;
    // What falls where the camera is (V6-014: Babylon's winter rain was shown as snow).
    m.snow = snowLiesHere();
    m.pages = actors_.seenCount() + progress_.nooksFound();
    m.pagesTotal = static_cast<int>(cat_.visitors.size() + cat_.nooks.size());
    m.nextStagePages = nextStagePages(cat_, progress_.stage);
    if (m.nextStagePages >= 0)
        m.nextStageName = cat_.stages[static_cast<std::size_t>(progress_.stage) + 1].name;
    m.tool = tool_;
    m.selection = selection_;
    m.category = category_;
    m.drawerOpen = drawerOpen_;
    m.journalOpen = journalOpen_;
    m.photo = photo_;
    m.muted = muted_;
    m.weather = weather_.mode();
    m.raining = raining();
    // Her speech bubble, above her head wherever she is on screen.
    if (const Bubble* b = speech_.showing(simTime_);
        b != nullptr && residentOnScreen() &&
        std::cmp_less(actors_.resident(), drawActors_.size())) {
        const Actor& r = drawActors_[static_cast<std::size_t>(actors_.resident())];
        m.bubble = b->text;
        m.bubbleAt = view_.worldToScreen(scene_->headOf(r), screen());
        m.bubbleAlpha = speech_.alpha(simTime_) * std::clamp(r.alpha, 0.0f, 1.0f);
    }
    m.pin = clock_.pin();
    m.phase = clock_.phase();
    m.canUndo = editor_.canUndo();
    m.canRedo = editor_.canRedo();
    m.canZoomIn = camera_.level() + 1 < static_cast<int>(kZoomLevels.size());
    m.canZoomOut = camera_.level() > 0 || loaded_ != nullptr;
    const Lighting l = lighting();
    m.brightness =
        std::clamp(((l.ambient.r + l.ambient.g + l.ambient.b) / 3.0f - 0.3f) / 0.6f, 0.0f, 1.0f);
    if (photo_) {
        fillWorldModel(m);
        return m; // the photo bar names its keys
    }
    m.hint = toolHint();
    m.warning = warning_;
    if ((tool_ == Tool::Place || carry_) && hover_ && warnTime_ <= 0 && shape_ == Shape::None)
        m.warning = placeWarning(canPlace(world_, cat_, ghostItem(*hover_)));
    fillWorldModel(m);
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
        case K::MoveTool: setTool(tool_ == Tool::Move ? Tool::None : Tool::Move, -1); break;
        case K::Menu: menus_.open(Page::Pause); break;
        case K::Photo: togglePhoto(); break;
        case K::Clock: cycleClock(); break;
        case K::Rain: cycleWeather(); break;
        case K::Journal:
            journalOpen_ = !journalOpen_;
            play(journalOpen_ ? sfx::kOpen : sfx::kClose, tuning::kUiSfxLevel);
            break;
        case K::Undo: undoRedo(false); break;
        case K::Redo: undoRedo(true); break;
        case K::Recentre: frameCamera(); break;
        case K::Map: toggleMap(); break;
        case K::Mute: toggleMute(); break;
        case K::CloseCard: closeCard(); break;
        case K::ZoomOut: zoomBy(-1, centre); break;
        case K::ZoomIn: zoomBy(1, centre); break;
        case K::SeenNew: {
            const auto n = static_cast<std::size_t>(a.arg);
            if (n < cat_.items.size())
                progress_.newItems[n] = 0;
            else
                progress_.newTerrain[n - cat_.items.size()] = 0;
            markDirty();
            break;
        }
        case K::OpenWishes:
            journalOpen_ = true;
            hud_.openSketchbook(0);
            play(sfx::kOpen, tuning::kUiSfxLevel);
            break;
        case K::PageTurn: play(sfx::kPage, tuning::kUiSfxLevel); break;
        case K::SeasonPin:
            seasonPin_ = a.arg;
            seasonByPin_ = true;
            markDirty();
            break;
        case K::EdgeChip:
            camera_.panTo(edgeChipTarget_, screen());
            edgeChipUntil_ = 0;
            break;
        case K::Snooze:
            if (a.arg >= 0) {
                progression_.snooze(a.arg, progress_, played_);
                markDirty();
            }
            break;
        case K::Hover: break;
        }
    }
}

void App::step(float dt) {
    syncHome();
    camera_.beginStep();
    actorPrev_.resize(actors_.all().size());
    for (std::size_t i = 0; i < actorPrev_.size(); ++i) actorPrev_[i] = actors_.all()[i].pos;
    simTime_ += dt;
    played_ += dt;
    thumbTimer_ += dt;
    clock_.update(dt);
    const Vec2 pan{(keyPan_[3] ? 1.0f : 0.0f) - (keyPan_[2] ? 1.0f : 0.0f),
                   (keyPan_[1] ? 1.0f : 0.0f) - (keyPan_[0] ? 1.0f : 0.0f)};
    if (pan.x != 0 || pan.y != 0) {
        tourMoved_ = true;
        follow_.reset(); // a pan takes the camera back
    }
    if (pan.x != 0 || pan.y != 0)
        camera_.nudge({pan.x * tuning::kKeyPanSpeed * dt, pan.y * tuning::kKeyPanSpeed * dt},
                      screen());
    camera_.update(dt, screen());
    wheelIdle_ += dt;
    if (wheelIdle_ > tuning::kWheelIdleReset) wheelAcc_ = 0;

    {
        // The home's life, less its actors and the weather (timed inside it).
        const auto at = [](Part p) { return static_cast<std::size_t>(p); };
        const double weather = partMs_[at(Part::Weather)];
        const std::uint64_t weatherAllocs = partAllocs_[at(Part::Weather)];
        const std::uint64_t a0 = threadAllocs();
        updateLife(dt);
        partMs_[at(Part::Actors)] += actorMs_;
        partMs_[at(Part::HomeLife)] += lifeMs_ - (partMs_[at(Part::Weather)] - weather);
        partAllocs_[at(Part::HomeLife)] +=
            threadAllocs() - a0 - (partAllocs_[at(Part::Weather)] - weatherAllocs);
    }
    {
        const Timed timed(*this, Part::City);
        stepCity(dt);
    }
    {
        const Timed timed(*this, Part::Progress);
        const Uint64 p0 = SDL_GetPerformanceCounter();
        updateProgress();
        progressMs_ = msBetween(p0, SDL_GetPerformanceCounter());
    }
    std::erase_if(nookLabels_, [&](const NookLabel& l) {
        return simTime_ - l.start > tuning::kNookLabelSeconds;
    });
    updateHoverNook();
    updateSeason(dt);
    growthAcc_ += dt;
    if (growthAcc_ >= tuning::kGrowthTick) {
        growBeds(static_cast<float>(growthAcc_));
        growthAcc_ = 0;
    }
    {
        const Timed timed(*this, Part::Effects);
        scene_->update(dt, world_, actors_.all(), weather_, rng_);
    }

    warnTime_ = std::max(0.0f, warnTime_ - dt);
    if (warnTime_ <= 0) warning_ = {};
    if (pendingNotes_ > 0 && (lastNote_ < 0 || simTime_ - lastNote_ >= tuning::kNoteMinGap)) {
        --pendingNotes_;
        playNote();
    }
    // Never saved with a piece in hand (it is out of the world until it is put down).
    if (autosave_.due(dt, drag_ == Drag::Tool, carry_.has_value())) (void)save();
    (void)pollSaves();
}

int App::season() const {
    return seasonPin_ >= 0 ? seasonPin_ : seasonOf(clock_.day(), cat_.seasonDays).season;
}

bool App::snowing() const {
    // Away, as the world's weather has it by the climate there (no snow on the desert).
    if (viewWeather_ && away()) return raining() && viewWeather_->snow();
    return raining() && cat_.seasons[static_cast<std::size_t>(season())].snow;
}

Lighting App::lighting() const {
    Lighting l = lightingAt(clock_.time(), rainHere());
    // The season's grade multiplies over the world with the day's light.
    const float k = gradeT_ * gradeT_ * (3 - 2 * gradeT_);
    const Rgb g{gradeFrom_.r + (gradeTo_.r - gradeFrom_.r) * k,
                gradeFrom_.g + (gradeTo_.g - gradeFrom_.g) * k,
                gradeFrom_.b + (gradeTo_.b - gradeFrom_.b) * k};
    l.ambient = {l.ambient.r * g.r, l.ambient.g * g.g, l.ambient.b * g.b};
    return l;
}

void App::updateSeason(float dt) {
    gradeT_ = std::min(1.0f, gradeT_ + dt / gradeSeconds_);
    const int s = season();
    if (s != seasonShown_) {
        // Looks switch at once; the grade glides from where it is to the new season's.
        const Rgb target = cat_.seasons[static_cast<std::size_t>(s)].grade;
        if (seasonShown_ < -1) {
            gradeFrom_ = gradeTo_ = target;
            gradeT_ = 1;
        } else {
            const float k = gradeT_ * gradeT_ * (3 - 2 * gradeT_);
            gradeFrom_ = {gradeFrom_.r + (gradeTo_.r - gradeFrom_.r) * k,
                          gradeFrom_.g + (gradeTo_.g - gradeFrom_.g) * k,
                          gradeFrom_.b + (gradeTo_.b - gradeFrom_.b) * k};
            gradeTo_ = target;
            gradeT_ = 0;
            gradeSeconds_ =
                seasonByPin_
                    ? tuning::kSeasonPinGlide
                    : static_cast<float>(tuning::kSeasonGradeGlide * tuning::kDayLengthSeconds);
        }
        seasonByPin_ = false;
        seasonShown_ = s;
        scene_->setSeason(s);
        if (worldView_) worldView_->setSeason(s);
    }
    if (clock_.day() != lastDay_) {
        lastDay_ = clock_.day();
        markDirty();
    }
}

void App::setupMusic() {
    for (const auto& s : cat_.audio.dayStems) dayStems_.push_back(mixer_.loopIndex(s.file));
    for (const auto& s : cat_.audio.nightStems) nightStems_.push_back(mixer_.loopIndex(s.file));
    stemOn_.assign(dayStems_.size() + nightStems_.size(), 0);
    // While a piece's first conditional stem (its melody) is locked, the rest is lifted a little.
    const auto lead = [](const std::vector<StemDef>& defs, const std::vector<int>& loops) {
        for (std::size_t i = 0; i < defs.size(); ++i)
            if (defs[i].when >= 0) return loops[i];
        return -1;
    };
    mixer_.setMakeup(dayStems_, lead(cat_.audio.dayStems, dayStems_), tuning::kDayMakeup);
    mixer_.setMakeup(nightStems_, lead(cat_.audio.nightStems, nightStems_), tuning::kNightMakeup);
    // The full mixes are the front door's (the catalog's music that is no stem): loaded, and on
    // the music bus.
    std::vector<std::string> full;
    for (const std::string& f : cat_.audio.music)
        if (mixer_.loopIndex(f) < 0) full.push_back(f);
    mixer_.loadMore(assets_ / "audio", {}, full);
    for (const std::string& f : full) {
        const int loop = mixer_.loopIndex(f);
        mixer_.setLoopMusic(loop);
        (f.contains("night") ? titleNight_ : titleDay_) = loop;
    }
}

void App::unlockStems(const CondFacts& f, bool instant) {
    std::size_t k = 0;
    for (const auto* piece : {&cat_.audio.dayStems, &cat_.audio.nightStems}) {
        const auto& loops = piece == &cat_.audio.dayStems ? dayStems_ : nightStems_;
        for (std::size_t i = 0; i < piece->size(); ++i, ++k) {
            const StemDef& s = (*piece)[i];
            if (stemOn_[k] != 0 || (s.when >= 0 && !cat_.conditions.eval(s.when, world_, f)))
                continue;
            stemOn_[k] = 1;
            // Layers there when the world opens play at once; new ones fade in on a bar line.
            mixer_.unlockStem(loops[i], instant || s.when < 0);
        }
    }
}

void App::updateAudio() {
    mixer_.setMuted(muted_);
    // Snow falling or lying where the view is muffles the beds (audio-seasons.md §5.10).
    mixer_.setMuffle(snowing() || snowLiesHere() ? 1.0f : 0.0f);
    applyVolumes(); // the music ducks while paused
    const Lighting l = lighting();
    const float n = std::clamp(l.night, 0.0f, 1.0f);
    // At the front door its own full mix plays (day or night by the clock); in the world the
    // home's stems play while the home holds the music (its share of the view).
    const bool door = menus_.frontDoorOpen();
    mixer_.setLoopGain(titleDay_, door ? tuning::kMusicLevel * (1 - n) : 0.0f);
    mixer_.setLoopGain(titleNight_, door ? tuning::kMusicLevel * n : 0.0f);
    const float home = door ? 0.0f : homeMusic();
    for (const int s : dayStems_) mixer_.setLoopGain(s, tuning::kMusicLevel * (1 - n) * home);
    for (const int s : nightStems_) mixer_.setLoopGain(s, tuning::kMusicLevel * n * home);
    updateWorldAudio(n);
    // The season's beds follow the weather where the camera looks: rain ducks the birds and
    // brings its own bed (snow brings none and lifts the winter bed). Birds swell at dawn and
    // after rain (the chorus events).
    const SeasonDef& def = cat_.seasons[static_cast<std::size_t>(season())];
    const bool snowSeason = def.snow;
    const float rain = snowSeason ? 0.0f : rainHere();
    const float snow = snowSeason ? rainHere() : 0.0f;
    const float boost = 1.0f + (tuning::kSnowAmbienceBoost - 1.0f) * snow;
    const float chorus = events_.gain(EventShow::Chorus);
    // Water and the waterfall are where they are on screen: louder and panned toward them.
    const TileRect vis = scene_->visibleTiles(camera_, screen(), world_);
    float water = 0;
    float waterX = 0;
    world_.forEachChunkIn(vis, [&](int cx, int cy) {
        const auto w = static_cast<float>(world_.chunkTerrainCount(cx, cy, cat_.waterTerrain));
        water += w;
        // The middle of the chunk stands for where its water is.
        const float half = static_cast<float>(kChunk) * 0.5f;
        waterX += w * panOf({static_cast<float>(cx * kChunk) + half,
                             static_cast<float>(cy * kChunk) + half});
    });
    for (const auto& file : cat_.audio.ambience) {
        float g = 0;
        float pan = 0;
        if (file == def.ambienceDay)
            g += tuning::kBirdsLevel * (1 - n) * boost * chorus *
                 (1.0f + (tuning::kRainBirdsDuck - 1.0f) * rain);
        if (file == def.ambienceNight)
            g += tuning::kCricketsLevel * n * boost *
                 (1.0f + (tuning::kRainCricketsDuck - 1.0f) * rain);
        if (file == kRainBed) g += tuning::kRainLevel * rain;
        if (file == kWaterBed && water > 0) {
            g += tuning::kWaterLevel * std::min(1.0f, water / tuning::kWaterTilesForFullLevel);
            pan = waterX / water * tuning::kBedPan;
        }
        if (file == kWaterfallBed && fallCount_ > 0) {
            g += tuning::kWaterfallLevel *
                 std::min(1.0f, static_cast<float>(fallCount_) / tuning::kFallTilesForFullLevel) *
                 distanceGain(fallCentre_);
            pan = panOf(fallCentre_);
        }
        const int loop = mixer_.loopIndex(file);
        mixer_.setLoopGain(loop, g * homeAmbience());
        mixer_.setLoopPan(loop, pan);
    }
}

void App::render() {
    FrameParams p;
    p.world = &world_;
    p.actors = drawActors_;
    p.resident = actors_.resident();
    p.weather = &weather_;
    p.cloudShadows =
        gpu::parseClouds(profile_.clouds).value_or(gpu::Clouds::On) != gpu::Clouds::Off &&
        (!worldView_ || worldView_->quality() == gpu::Quality::Classic);
    p.ghosts = buildGhosts();
    p.grid = grid_ ? tuning::kGridAlphaDay + (tuning::kGridAlphaNight - tuning::kGridAlphaDay) *
                                                 std::clamp(p.light.night, 0.0f, 1.0f)
                   : 0.0f;
    p.footprints = footprintsHeld_;
    if (footprintsHeld_) {
        allNooks_.clear();
        for (const NookPlace& n : nookPlaces_) allNooks_.push_back(n.area);
        p.outlines = allNooks_;
    }
    p.outlines = hoverNook_;
    p.camera = &view_;
    p.screen = screen();
    p.light = lighting();
    p.fireflySync = events_.active(EventShow::FireflySync);
    // The rainbow fades in, holds and fades out over its event.
    if (const float k = events_.progress(EventShow::Rainbow, simTime_); k >= 0) {
        const float t = k * tuning::kRainbowSeconds;
        p.rainbow = std::clamp(
            std::min(t / tuning::kRainbowIn, (tuning::kRainbowSeconds - t) / tuning::kRainbowOut),
            0.0f, 1.0f);
    }
    const Uint64 t0 = SDL_GetPerformanceCounter();
    {
        const Timed timed(*this, Part::Scene);
        drawScene(p);
    }
    if (photo_ && font_.build(renderer_.get(), uiScale_)) {
        // The postcard's frame and caption over the view; a postcard is taken with them and
        // before the bar is drawn.
        Painter painter(*uiBatch_, font_, {nullptr, p.screen, 0.5f}, uiScale_);
        drawPostcard(painter);
        uiBatch_->flush();
    }
    if (capturePending_) {
        capturePending_ = false;
        capturePhoto();
    }
    // The glass panels show a blurred copy of the scene.
    blur_->invalidate();
    {
        const Timed timed(*this, Part::Blur);
        if (blur_->begin(p.screen, theme::kBlurRadius * uiScale_)) {
            compositeScene(p, blur_->sourceScale(), true);
            blur_->end();
        }
    }
    const Uint64 t1 = SDL_GetPerformanceCounter();
    sceneMs_ = msBetween(t0, t1);
    const std::uint64_t uiAllocs = threadAllocs();
    if (!hudHidden_ && font_.build(renderer_.get(), uiScale_)) {
        // The model the interface was laid out from this frame: drawing never sees another.
        Painter painter(*uiBatch_, font_, {blur_->result(), p.screen, ui_.brightness}, uiScale_);
        // The interface shows in play; the front door's pages and the pause menu draw over a
        // world without it.
        if (menus_.page() == Page::None) hud_.draw(painter, ui_);
        if (map_.showing()) map_.draw(painter, mapModel_);
        const MenuModel& menus = menuModel();
        menus_.relayout(menus, font_);
        menus_.draw(painter, menus);
        if (profilerOn_) {
            drawPlaceholderLabels(painter);
            profiler_.draw(painter, perf_, screen(), uiScale_, opts_.gpuSync);
        }
        uiBatch_->flush();
    }
    if (const float veil = travelVeil(); veil > 0 && font_.build(renderer_.get(), uiScale_)) {
        Painter painter(*uiBatch_, font_, {nullptr, p.screen, 0.5f}, uiScale_);
        painter.roundRect({0, 0, p.screen.x, p.screen.y}, 0,
                          {theme::kTravelVeil.r, theme::kTravelVeil.g, theme::kTravelVeil.b, veil},
                          0);
        uiBatch_->flush();
    }
    hudDrawMs_ = msBetween(t1, SDL_GetPerformanceCounter());
    partMs_[static_cast<std::size_t>(Part::UiDraw)] += hudDrawMs_;
    partAllocs_[static_cast<std::size_t>(Part::UiDraw)] += threadAllocs() - uiAllocs;
}

void App::captureAudio(int steps) {
    const auto frames = static_cast<std::size_t>(steps * kAudioFramesPerStep);
    if (captureSkip_) {
        // A settling stretch between measured segments: mixed (time moves on) but not kept.
        skipBuffer_.resize(frames * 2);
        mixer_.render(skipBuffer_.data(), static_cast<int>(frames));
        return;
    }
    const std::size_t n = capture_.size();
    capture_.resize(n + frames * 2);
    mixer_.render(capture_.data() + n, static_cast<int>(frames));
}

void App::refreshScale() {
    const float display = SDL_GetWindowDisplayScale(window_.get());
    const float fit = std::min(static_cast<float>(pixelW_) / theme::kReferenceW,
                               static_cast<float>(pixelH_) / theme::kReferenceH);
    // Quarter steps keep glyph re-rasterisation rare while a window is being resized.
    // The player's interface size multiplies the automatic scale (R10.7).
    const float factor =
        profile_.uiScale > 0 ? kUiScales[std::clamp(profile_.uiScale, 0, kUiScaleCount - 1)] : 1.0f;
    uiScale_ =
        std::clamp(std::round(std::max(display > 0 ? display : 1.0f, fit) * factor * 4.0f) / 4.0f,
                   factor < 1.0f ? 0.75f : 1.0f, theme::kMaxScale);
}

int App::run() {
    if (!init()) return opts_.bench || opts_.benchmark ? kExitNoRenderer : 1;
    // A scripted or bench run asking for a shader tier where none can be made is skipped.
    if (!opts_.quality.empty() && wantedQuality() != gpu::Quality::Classic && worldView_ &&
        worldView_->quality() == gpu::Quality::Classic && (opts_.script || opts_.bench))
        return kExitNoRenderer;
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
    prepareView();
    ui_ = model();
    hud_.update({}, ui_, font_, screen(), uiScale_, 0);
    if (savedCamera_)
        camera_.place(*savedCamera_, savedZoom_, screen());
    else
        frameCamera();
    // What a renderer makes the first time it is asked (pipelines for every blending and target,
    // the look's targets, the cache's pages: tens of milliseconds a frame on SDL's gpu driver) is
    // made here, in frames nobody sees, so the first frame shown is an ordinary one.
    if (worldView_ && streams()) {
        worldView_->reserveFor(screen());
        scene_->reserveTargets(static_cast<int>(std::ceil(screen().x)) + 8,
                               static_cast<int>(std::ceil(screen().y)) + 8);
        // (The glass's blur, whatever is open at first.)
        if (blur_->begin(screen(), theme::kBlurRadius * uiScale_)) blur_->end();
        for (int k = 0; k < tuning::kWarmFrames; ++k) {
            render();
            if (!SDL_FlushRenderer(renderer_.get())) SDL_Log("render: %s", SDL_GetError());
        }
    }
    // The first view streams in over its first second or two (its pages decode on a worker,
    // its cells are built a few a frame): it is shown when it is whole, behind the veil a
    // journey arrives through, never filling in before the eyes. Runs that build everything at
    // once (headless scripts) and those that measure have nothing to hide.
    if (worldView_ && !measuring() && streams()) {
        travel_ = {loaded_->file.home.region, tuning::kTravelFadeOut, true};
        startVeil_ = true;
    }
    if (opts_.bench) {
        // SDL started with the process: its clock is the start-up time.
        startupMs_ = static_cast<double>(SDL_GetTicks());
        std::printf("bench: start-up to the first frame's setup %.0f ms (budget %.0f)\n",
                    startupMs_, tuning::kStartupBudgetMs);
        return runBench();
    }
    if (opts_.benchmark) return runBenchmark();
    if (opts_.soak > 0) return runSoak();
    if (opts_.focus && openCity()) {
        cityFocus_ = life::parseFocus(*city_->life, *opts_.focus);
        if (!cityFocus_) SDL_Log("city life: unknown focus %s", opts_.focus->c_str());
    }
    actors_.populate(actorEnv());
    refreshNooks();
    applyVolumes();
    applyReduceMotion();
    if (frontDoor()) {
        // The title over the last world; her greeting waits until the player walks in.
        refreshWorlds();
        menus_.open(Page::Title);
        greetPending_ = true;
    } else {
        // She greets the player when the corner opens and she can be seen.
        if (residentOnScreen() && speak(cat_.resident.context("greet"), SpeechWeight::Important))
            actors_.wave();
        tellMuted();
    }

    // Headless runs advance exactly one fixed step per frame so scripts are reproducible.
    const bool fixed = opts_.headless;
    Uint64 last = SDL_GetTicksNS();
    double acc = 0;
    while (running_) {
        const Uint64 t0 = SDL_GetPerformanceCounter();
        const FrameMark mark = markFrame();
        partMs_ = {};
        partAllocs_ = {};
        leftPressed_ = leftReleased_ = rightPressed_ = rightReleased_ = false;
        for (SDL_Event e; SDL_PollEvent(&e);) handleEvent(e);
        if (hidden_ && !opts_.headless) {
            // Minimised or hidden: nothing to draw and nothing moves on (the corner waits for its
            // player); sleep until something happens instead of spinning.
            if (SDL_Event e; SDL_WaitEventTimeout(&e, tuning::kHiddenWaitMs)) handleEvent(e);
            last = SDL_GetTicksNS();
            acc = 0;
            continue;
        }

        const Uint64 now = SDL_GetTicksNS();
        const double real = static_cast<double>(now - last) * 1e-9;
        last = now;
        const float frameDt = fixed ? static_cast<float>(tuning::kStepSeconds)
                                    : static_cast<float>(std::min(real, 0.1));
        frameDt_ = frameDt;
        refreshScale();
        if (!font_.build(renderer_.get(), uiScale_)) return 1;

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
        double simMs = 0;
        double condMs = 0;
        double cityMs = 0;
        // Menus stop the corner (pause and the front door); the title's camera drifts on.
        const bool blocked = menus_.blocking();
        if (blocked) {
            if (menus_.page() != Page::Pause) titleDrift(frameDt);
            acc = std::min(acc, tuning::kStepSeconds);
            steps = 0;
        }
        for (int i = 0; i < steps; ++i) {
            const Uint64 s0 = SDL_GetPerformanceCounter();
            const std::uint64_t a0 = threadAllocs();
            step(static_cast<float>(tuning::kStepSeconds));
            stepMs_ += msBetween(s0, SDL_GetPerformanceCounter());
            stepAllocs_ += threadAllocs() - a0;
            simMs += actorMs_ + lifeMs_ + progressMs_;
            condMs += progressMs_;
            cityMs += cityMs_;
        }
        if (!blocked)
            updateTour(static_cast<float>(steps) * static_cast<float>(tuning::kStepSeconds));
        {
            const Timed timed(*this, Part::World);
            updateWorld(frameDt);
        }
        // Drawing runs between steps: the camera and every actor are shown where they are this
        // far toward the next step, so motion is smooth at any refresh rate.
        alpha_ = fixed ? 1.0f : static_cast<float>(acc / tuning::kStepSeconds);
        prepareView();

        const Uint64 tUi = SDL_GetPerformanceCounter();
        const double updateMs = msBetween(t0, tUi);
        // One interface model per frame, built after the simulation: the interface is laid out,
        // hit-tested and drawn from it alone, so what is drawn always matches the layout even
        // when a click or a grant changes the game in between (QA2-01).
        {
            const Timed timed(*this, Part::Model);
            ui_ = model();
        }
        UiInput in;
        in.x = mouse_.x;
        in.y = mouse_.y;
        in.inside = mouseInside_;
        in.pressed = leftPressed_;
        in.released = leftReleased_;
        in.rightPressed = rightPressed_;
        in.rightReleased = rightReleased_;
        in.wheel = wheel_;
        in.blocked = drag_ != Drag::None;
        // The menus (a page, the coach card, the photo bar) see the pointer first.
        menus_.update(in, menuModel(), font_, screen(), uiScale_, frameDt);
        bool menusOwn = menus_.wantsMouse() || menus_.blocking();
        if (loaded_) {
            // The map takes the pointer while it is open, and nothing moves while travelling.
            const bool free = !menusOwn && menus_.page() == Page::None;
            map_.update(in.x, in.y, in.inside && free, in.pressed && free, in.released && free,
                        mapModel(), font_, screen(), uiScale_, frameDt);
            if (const auto c = map_.clicked()) travelTo(mapShown_[static_cast<std::size_t>(*c)]);
            menusOwn = menusOwn || map_.isOpen() || travel_.region >= 0;
        }
        UiInput hudIn = in;
        if (menusOwn || menus_.page() != Page::None) hudIn = UiInput{};
        hud_.update(hudIn, ui_, font_, screen(), uiScale_, frameDt);
        applyMenuActions();
        applyHudActions();
        if (menusOwn && drag_ != Drag::Tool) {
            hover_.reset();
            if (drag_ == Drag::Pan && leftReleased_) drag_ = Drag::None;
            wheel_ = 0;
            wheelAcc_ = 0;
        } else {
            worldInput();
        }
        // Text input is on while a name is being typed (the system's composition window).
        if (menus_.editing() != textInput_) {
            textInput_ = menus_.editing();
            if (!(textInput_ ? SDL_StartTextInput(window_.get())
                             : SDL_StopTextInput(window_.get())))
                SDL_Log("text input: %s", SDL_GetError());
        }
        writeProfileIfDue();
        const double uiMs = msBetween(tUi, SDL_GetPerformanceCounter());
        updateAudio();
        // A capture keeps time with the frames (one fixed step each when headless), so the
        // front door, the pause menu and the map, where nothing steps, are heard too.
        if (opts_.audioOut) captureAudio(1);
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
        const Uint64 tSubmit = SDL_GetPerformanceCounter();
        FrameSample fs;
        closeMark(mark, fs);
        const double gpuMs = opts_.gpuSync ? syncGpu(t0) : -1.0;
        const Uint64 tPresent = SDL_GetPerformanceCounter();
        if (!SDL_RenderPresent(renderer_.get())) SDL_Log("present: %s", SDL_GetError());
        const Uint64 t1 = SDL_GetPerformanceCounter();
        fs.frameMs = static_cast<float>(msBetween(t0, t1));
        fs.cpuMs = static_cast<float>(msBetween(t0, tSubmit));
        fs.gpuMs = static_cast<float>(gpuMs);
        fs.presentMs = static_cast<float>(msBetween(tPresent, t1));
        fs.simMs = static_cast<float>(simMs);
        fs.condMs = static_cast<float>(condMs);
        fs.cityMs = static_cast<float>(cityMs);
        fs.uiMs = static_cast<float>(uiMs + hudDrawMs_);
        fs.updateMs = static_cast<float>(updateMs + uiMs);
        partMs_[static_cast<std::size_t>(Part::UiUpdate)] +=
            uiMs - partMs_[static_cast<std::size_t>(Part::Model)];
        fs.steps = steps;
        recordFrame(fs);
        if (!legacyToRetire_.empty() && simTime_ >= retireAt_) {
            // The migrated world and its thumbnail exist now; the old file is kept, renamed. A
            // folder that cannot be written is tried again only after the save retry delay.
            std::error_code ec;
            if (save(true) && writeThumbnail()) {
                fs::rename(legacyToRetire_, saveDir_ / kLegacyKept, ec);
                if (ec) SDL_Log("save: cannot rename the old save: %s", ec.message().c_str());
                legacyToRetire_.clear();
            } else {
                retireAt_ = simTime_ + tuning::kSaveRetrySeconds;
            }
        }
        if (welcomePending_) {
            welcomePending_ = false;
            const int pages = actors_.seenCount() + progress_.nooksFound();
            hud_.toast(
                cat_.residentKind >= 0
                    ? std::vformat(strings::kToastWelcome,
                                   std::make_format_args(cat_.resident.name, pages))
                    : std::vformat(strings::kToastWelcomeAlone, std::make_format_args(pages)));
        }
        settlePhoto(false);
        settleWorlds(false);
        if (thumbTimer_ >= tuning::kThumbnailInterval) {
            thumbTimer_ = 0;
            (void)writeThumbnail();
        }
        // SDL started with the process: its clock is the start-up time (CLAUDE.md: within 3 s).
        if (frame_ == 0)
            SDL_Log("start: the first frame after %llu ms",
                    static_cast<unsigned long long>(SDL_GetTicks()));
        ++frame_;
        if (opts_.frames > 0 && frame_ >= opts_.frames) running_ = false;
    }
    cancelMove();
    if (editor_.inGroup()) editor_.commit();
    settlePhoto(true);
    profileDue_ = 0;
    writeProfileIfDue();
    if (!(freshWorld_ && frontDoor())) (void)writeThumbnail();
    if (!save(true) && exitCode_ == 0 && opts_.script) SDL_Log("save: the final save failed");
    rememberWindow();
    mixer_.close();
    if (opts_.audioOut) {
        if (auto r = writeWavFloat(*opts_.audioOut, capture_); !r) {
            SDL_Log("audio: %s", r.error().c_str());
            return 1;
        }
        SDL_Log("audio: wrote %s", opts_.audioOut->string().c_str());
        endSegment();
        if (!marks_.empty()) {
            std::ofstream out(opts_.audioOut->string() + ".marks", std::ios::binary);
            out << marks_;
        }
    }
    return exitCode_;
}

int runApp(const Options& options) {
    const SdlSession sdl(options.headless,
                         !options.renderer.empty() && options.renderer != "software");
    if (!sdl.ok) return 1;
    fs::path assets = findAssets(options);
    if (options.lifeDump) return runLifeDumps(options, assets);
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
