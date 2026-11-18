// The front door (docs/design/living-corner.md R10): the title screen over the last world,
// "Your worlds" (play, create, rename, delete), settings applied at once and kept in the
// profile, the pause menu, and the first-minute tour. Switching worlds rebuilds every piece of
// per-world state in place; the window, renderer, atlas, sound and interface stay.

#include "app/app_impl.hpp"
#include "core/land.hpp"
#include "core/starter.hpp"
#include "render/gpu/post.hpp"
#include "ui/strings.hpp"

#include <algorithm>
#include <cmath>
#include <format>

namespace lc {
namespace {

constexpr float kTitleDrift = 4.0f;      // window px per second the title's camera drifts
constexpr float kProfileDebounce = 0.5f; // seconds after a change before the profile is written
constexpr float kEffectsTick = 0.15f;    // the effects slider's click, at most this often
constexpr float kPauseDuck = 0.5f;       // music while paused: -6 dB

// The tour's steps (R10.5); 0 is "not touring".
enum TourStep : int { kTourOff = 0, kLook, kOpenBuild, kPlant, kWish, kKeys, kEnd };

} // namespace

bool App::frontDoor() const {
    return !measuring() && (!opts_.headless || opts_.frontDoor);
}

void App::resetWorld() {
    cancelMove();
    world_ = World(cat_);
    editor_ = Editor(tuning::kUndoSteps);
    clock_ = Clock{};
    actors_ = Actors(cat_, seed_);
    for (std::size_t v = 0; v < gates_.size(); ++v) gates_[v] = {!cat_.visitors[v].rare, 0};
    weather_ = Weather(cat_, seed_);
    events_ = EventScheduler(cat_, seed_);
    speech_ = Speech(cat_, seed_);
    lively_ = LivelyProbe{};
    prefer_.clear();
    nookPlaces_.clear();
    nookRevision_ = ~0ULL;
    nookSeen_.clear();
    recentSounds_.clear();
    idleLineAt_ = livelyAt_ = 0;
    ripeDay_ = -1;
    ripeSince_ = -1;
    rainWas_ = false;
    fallCount_ = 0;
    fallRevision_ = ~0ULL;
    rimTiles_.clear();
    progress_ = Progress(cat_);
    progression_ = Progression(cat_);
    evalRevision_ = ~0ULL;
    evalDue_ = -1;
    factsKey_ = ~0ULL;
    nookLabels_.clear();
    hoverNook_.clear();
    hoverTip_ = {};
    hoverNookTile_.reset();
    hoverNookRevision_ = ~0ULL;
    loading_ = true;
    edgeChipUntil_ = 0;
    growthAcc_ = 0;
    notes_ = PhraseWalker{};
    lastNote_ = -1;
    anyRipe_ = false;
    adoptWorldState({});
    worldName_.clear();
    created_.clear();
    slug_.clear();
    freeBuild_ = false;
    freshWorld_ = false;
    played_ = 0;
    seasonPin_ = -1;
    seasonShown_ = -2;
    seasonByPin_ = false;
    gradeT_ = 1;
    lastPhase_ = Phase::Day;
    lastDay_ = 0;
    std::ranges::fill(stemOn_, 0);
    mixer_.resetStems();
    savedCamera_.reset();
    thumbTimer_ = 0;
    legacyToRetire_.clear();
    welcomePending_ = false;
    tool_ = Tool::None;
    selection_ = -1;
    shape_ = Shape::None;
    pipette_ = false;
    drawerOpen_ = journalOpen_ = photo_ = false;
    warning_ = {};
    saveFailing_ = false;
    autosave_ = AutosaveClock{};
    pendingNotes_ = 0;
    placements_ = 0;
    tourStep_ = kTourOff;
    hud_ = Hud{};
    scene_->resetWorld();
}

void App::enterWorld() {
    // The world just loaded (or created) comes alive: critters, the camera on its land, her
    // greeting, and the tour for a player who has not had it.
    fitCameraLand();
    refreshScale();
    if (font_.build(renderer_.get(), uiScale_)) {
        prepareView();
        ui_ = model();
        hud_.update({}, ui_, font_, screen(), uiScale_, 0);
    }
    if (savedCamera_)
        camera_.place(*savedCamera_, savedZoom_, screen());
    else
        frameCamera();
    actors_.populate(actorEnv());
    refreshNooks();
    greetPending_ = true; // as the player walks in
}

void App::startPlay() {
    // From the title (or a dialog) into the world.
    menus_.closeAll();
    if (std::exchange(greetPending_, false) && residentOnScreen() &&
        speak(cat_.resident.context("greet"), SpeechWeight::Important))
        actors_.wave();
    if (!profile_.onboarded && frontDoor() && tourStep_ == kTourOff) startTour();
}

void App::leaveWorld() {
    // Saved with its thumbnail before anything else opens.
    cancelMove();
    if (editor_.inGroup()) editor_.commit();
    if (!freshWorld_) {
        (void)save(true);
        (void)writeThumbnail();
    }
}

bool App::openWorld(const std::string& slug) {
    leaveWorld();
    resetWorld();
    slug_ = slug;
    if (!loadWorld(saveDir_ / kWorldsDir / slug / kWorldFile)) {
        // Shown as "couldn't be opened"; the corner behind the menus is a fresh one.
        startNewWorld(takenSlugs());
        freshWorld_ = true;
        enterWorld();
        return false;
    }
    enterWorld();
    return true;
}

void App::createWorld(std::string name, bool freeBuild) {
    leaveWorld();
    resetWorld();
    startNewWorld(takenSlugs(), std::move(name));
    freeBuild_ = freeBuild;
    if (freeBuild) {
        // Everything unlocked and all land open from the start (R10.4).
        progress_.unlockEverything(cat_);
        while (nextStagePages(cat_, progress_.stage) >= 0) openLand(++progress_.stage, false);
    }
    enterWorld();
    (void)save(true);
    (void)writeThumbnail();
}

std::vector<std::string> App::takenSlugs() const {
    // Every folder under worlds/, readable or not, so a new world never shares one.
    std::vector<std::string> taken;
    std::error_code ec;
    for (auto it = fs::directory_iterator(saveDir_ / kWorldsDir, ec);
         !ec && it != fs::directory_iterator(); it.increment(ec))
        taken.emplace_back(it->path().filename().string());
    return taken;
}

void App::refreshWorlds() {
    worldList_ = listWorlds(saveDir_ / kWorldsDir);
    worldThumbs_.clear();
    worldDetails_.clear();
    menuWorlds_.clear();
    worldDetails_.reserve(worldList_.size());
    for (const WorldSummary& w : worldList_) {
        TexturePtr tex;
        if (const SurfacePtr img{
                SDL_LoadPNG((saveDir_ / kWorldsDir / w.slug / kThumbFile).string().c_str())})
            tex = uploadTexture(renderer_.get(), img.get());
        const SeasonDay sd = seasonOf(w.day, cat_.seasonDays);
        const int day = sd.day + 1;
        const int pages = w.pages;
        worldDetails_.push_back(
            w.readable ? std::vformat(pages == 1 ? strings::kWorldDetailOne : strings::kWorldDetail,
                                      std::make_format_args(
                                          cat_.seasons[static_cast<std::size_t>(sd.season)].name,
                                          day, pages))
                       : std::string(strings::kCannotOpen));
        worldThumbs_.push_back(std::move(tex));
    }
    for (std::size_t i = 0; i < worldList_.size(); ++i) {
        MenuWorld mw;
        mw.name = worldList_[i].name;
        mw.detail = worldDetails_[i];
        mw.readable = worldList_[i].readable;
        if (SDL_Texture* t = worldThumbs_[i].get()) {
            float w = 0;
            float h = 0;
            if (SDL_GetTextureSize(t, &w, &h)) mw.thumb = Sprite{t, {0, 0, 1, 1}, w, h, 0, 0};
        }
        menuWorlds_.push_back(mw);
    }
}

const MenuModel& App::menuModel() {
    MenuModel& m = menuModel_;
    m.profile = &profile_;
    m.firstLaunch = freshWorld_;
    m.continueName = worldName_;
    m.worlds = menuWorlds_;
    m.logo = logo_;
    m.residentName =
        cat_.residentKind >= 0 ? std::string_view(cat_.resident.name) : std::string_view{};
    m.fullscreen = window_ && (SDL_GetWindowFlags(window_.get()) & SDL_WINDOW_FULLSCREEN) != 0;
    m.coachBottom = hud_.bottomPanelsTop();
    m.coach = tourStep_ != kTourOff && menus_.page() == Page::None && !photo_ ? coachText_
                                                                              : std::string_view{};
    m.deleteName = deleteIndex_ >= 0 && std::cmp_less(deleteIndex_, worldList_.size())
                       ? std::string_view(worldList_[static_cast<std::size_t>(deleteIndex_)].name)
                       : std::string_view{};
    m.photo = photo_;
    m.frameName = frameIndex_ >= 0
                      ? std::string_view(cat_.frames[static_cast<std::size_t>(frameIndex_)].name)
                      : std::string_view{};
    m.caption = profile_.caption;
    m.barBottom = profile_.caption && captionTop_ > 0 ? captionTop_ - theme::kGap * uiScale_ : 0.0f;
    m.frames = static_cast<int>(std::ranges::count(progress_.frames, std::uint8_t{1}));
    const gpu::Quality look = gpu::parseQuality(profile_.look).value_or(gpu::Quality::High);
    m.look = static_cast<int>(look);
    m.lookAfterRestart = look != gpu::Quality::Classic && worldView_ &&
                         worldView_->quality() == gpu::Quality::Classic;
    m.clouds = static_cast<int>(gpu::parseClouds(profile_.clouds).value_or(gpu::Clouds::On));
    return m;
}

void App::toggleMute() {
    // Muting is saved at once (a muted profile left over is the first thing to puzzle over).
    muted_ = !muted_;
    profile_.muted = muted_;
    profileDue_ = 0;
    writeProfileIfDue();
}

void App::profileChanged() {
    profileDue_ = static_cast<float>(SDL_GetTicks()) / 1000.0f + kProfileDebounce;
}

void App::writeProfileIfDue() {
    if (profileDue_ < 0 || static_cast<float>(SDL_GetTicks()) / 1000.0f < profileDue_) return;
    profileDue_ = -1;
    profile_.muted = muted_;
    if (std::string text = serialize(profile_); text != profileWritten_) {
        profileWritten_ = text;
        writer_.write(saveDir_ / kProfileFile, std::move(text));
    }
}

void App::applyVolumes() {
    const auto level = [](int v) { return static_cast<float>(v) / 100.0f; };
    const bool paused = menus_.page() == Page::Pause;
    mixer_.setBus(Mixer::Bus::Music, level(profile_.music) * (paused ? kPauseDuck : 1.0f));
    mixer_.setBus(Mixer::Bus::Effects, level(profile_.effects));
    mixer_.setBus(Mixer::Bus::Ambience, level(profile_.ambience));
}

void App::applyReduceMotion() {
    camera_.setEasing(!profile_.reduceMotion);
    scene_->setReduceMotion(profile_.reduceMotion);
    hud_.setReduceMotion(profile_.reduceMotion);
}

void App::setFullscreen(bool on) {
    if (opts_.headless || !window_) return;
    if (!SDL_SetWindowFullscreen(window_.get(), on)) SDL_Log("fullscreen: %s", SDL_GetError());
    windowState_.fullscreen = on;
}

void App::applyMenuActions() {
    using K = MenuAction::Kind;
    for (const MenuAction& a : menus_.actions()) {
        switch (a.kind) {
        case K::Hover: play(sfx::kHover, tuning::kUiSfxLevel * 0.6f); break;
        case K::Click: play(sfx::kClick, tuning::kUiSfxLevel); break;
        case K::Continue:
            if (freshWorld_) break;
            startPlay();
            break;
        case K::Begin:
        case K::NewWorld:
            refreshWorlds();
            menus_.open(Page::NewWorld);
            menus_.editName(freshName(defaultWorldName(), worldList_), -1);
            break;
        case K::Worlds:
            refreshWorlds();
            menus_.open(Page::Worlds);
            break;
        case K::Settings: menus_.open(Page::Settings); break;
        case K::Quit: running_ = false; break;
        case K::Back: menus_.back(); break;
        case K::Play: {
            if (std::cmp_greater_equal(a.arg, worldList_.size())) break;
            const WorldSummary& w = worldList_[static_cast<std::size_t>(a.arg)];
            // The world behind the menus plays at once; another one is opened first.
            if ((w.slug == slug_ && !freshWorld_) || openWorld(w.slug)) {
                startPlay();
            } else {
                refreshWorlds();
                menus_.open(Page::LoadError);
            }
            break;
        }
        case K::Rename: {
            if (std::cmp_greater_equal(a.arg, worldList_.size())) break;
            const WorldSummary& w = worldList_[static_cast<std::size_t>(a.arg)];
            const std::string name = trimName(a.text);
            if (const auto why = nameProblem(checkName(name, worldList_, w.slug)); !why.empty()) {
                menus_.fieldError(why);
                break;
            }
            if (w.slug == slug_ && !freshWorld_) {
                worldName_ = name;
                (void)save(true);
            } else if (auto r = renameWorld(saveDir_ / kWorldsDir / w.slug / kWorldFile, name);
                       !r) {
                SDL_Log("rename: %s", r.error().c_str());
            }
            menus_.closeField();
            refreshWorlds();
            break;
        }
        case K::Delete:
            if (a.arg < 0) {
                // Asked for: the dialog names the world first.
                deleteIndex_ = -1 - a.arg;
                menus_.open(Page::Delete);
            } else if (std::cmp_less(a.arg, worldList_.size())) {
                const std::string slug = worldList_[static_cast<std::size_t>(a.arg)].slug;
                if (slug == slug_ && !freshWorld_) {
                    // The world behind the menus goes too: a fresh preview takes its place.
                    resetWorld();
                    refreshWorlds();
                    startNewWorld(takenSlugs());
                    freshWorld_ = true;
                    enterWorld();
                }
                if (auto r = deleteWorld(saveDir_ / kWorldsDir / slug); !r)
                    SDL_Log("delete: %s", r.error().c_str());
                deleteIndex_ = -1;
                menus_.back();
                refreshWorlds();
            }
            break;
        case K::Create: {
            const std::string name = trimName(a.text);
            if (const auto why = nameProblem(checkName(name, worldList_)); !why.empty()) {
                menus_.fieldError(why);
                break;
            }
            createWorld(name, a.arg != 0);
            refreshWorlds();
            startPlay();
            break;
        }
        case K::Volume: {
            int& v = a.arg == 0   ? profile_.music
                     : a.arg == 1 ? profile_.effects
                                  : profile_.ambience;
            if (v == a.value) break;
            v = std::clamp(a.value, 0, 100);
            applyVolumes();
            profileChanged();
            // The effects slider sounds at its new level, now and then while it moves.
            const auto now = static_cast<float>(SDL_GetTicks()) / 1000.0f;
            if (a.arg == 1 && now - effectsTick_ >= kEffectsTick) {
                effectsTick_ = now;
                play(sfx::kClick, tuning::kUiSfxLevel);
            }
            break;
        }
        case K::Mute: toggleMute(); break;
        case K::Fullscreen:
            setFullscreen((SDL_GetWindowFlags(window_.get()) & SDL_WINDOW_FULLSCREEN) == 0);
            break;
        case K::UiScale:
            profile_.uiScale = std::clamp(a.arg, 0, kUiScaleCount - 1);
            profileChanged();
            break;
        case K::ReduceMotion:
            profile_.reduceMotion = !profile_.reduceMotion;
            applyReduceMotion();
            profileChanged();
            break;
        case K::Grid:
            grid_ = profile_.grid = !grid_;
            profileChanged();
            break;
        case K::Vsync:
            profile_.vsync = !profile_.vsync;
            if (!opts_.headless && !SDL_SetRenderVSync(renderer_.get(), profile_.vsync ? 1 : 0))
                SDL_Log("vsync: %s", SDL_GetError());
            profileChanged();
            break;
        case K::Look: {
            const auto q = static_cast<gpu::Quality>(std::clamp(a.arg, 0, gpu::kQualityCount - 1));
            profile_.look = std::string(gpu::qualityId(q));
            // Tiers switch live on SDL's gpu driver; another renderer shows them after a restart.
            if (worldView_ && gpu::isGpu(renderer_.get())) (void)worldView_->setQuality(q);
            profileChanged();
            break;
        }
        case K::Clouds: {
            const auto c = static_cast<gpu::Clouds>(std::clamp(a.arg, 0, gpu::kCloudModes - 1));
            profile_.clouds = std::string(gpu::cloudsId(c));
            if (worldView_) worldView_->setClouds(c);
            profileChanged();
            break;
        }
        case K::Chatter:
            profile_.chatty = a.arg != 0;
            profileChanged();
            break;
        case K::ReplayTour:
            profile_.onboarded = false;
            profileChanged();
            // In a world it starts once the menus close; otherwise with the next world.
            break;
        case K::Resume: startPlay(); break;
        case K::OpenPostcards: openPostcardsFolder(); break;
        case K::BackToWorlds:
            leaveWorld();
            refreshWorlds();
            menus_.closeAll();
            menus_.open(Page::Title);
            menus_.open(Page::Worlds);
            break;
        case K::SkipTour: endTour(); break;
        case K::FramePrev:
        case K::FrameNext: cycleFrame(a.kind == K::FrameNext ? 1 : -1); break;
        case K::Caption:
            profile_.caption = !profile_.caption;
            profileChanged();
            break;
        case K::HideBar: menus_.hideBar(!menus_.barHidden()); break;
        case K::TakePostcard: capturePending_ = true; break;
        case K::ClosePhoto: togglePhoto(); break;
        }
    }
    menus_.clearActions();
}

std::string_view App::nameProblem(NameProblem p) {
    switch (p) {
    case NameProblem::None: return {};
    case NameProblem::Empty: return strings::kNameEmpty;
    case NameProblem::TooLong: return strings::kNameTooLong;
    case NameProblem::Taken: return strings::kNameTaken;
    }
    return {};
}

void App::titleDrift(float dt) {
    // The title's camera drifts slowly across the corner along a wide loop; nothing simulates,
    // but the scene's water and particles keep moving.
    titleAngle_ += dt * 0.05f;
    camera_.dragBy({std::cos(titleAngle_) * kTitleDrift * dt * density_,
                    std::sin(titleAngle_) * kTitleDrift * 0.5f * dt * density_},
                   screen());
    camera_.beginStep();
    scene_->update(dt, world_, actors_.all(), weather_, rng_);
}

void App::startTour() {
    tourStep_ = kLook;
    tourT_ = 0;
    tourMoved_ = false;
    tourPlacements_ = placements_;
    hud_.holdToasts(true);
    (void)speak(cat_.resident.context("tour"), SpeechWeight::Important);
    setTourText();
}

void App::endTour() {
    tourStep_ = kTourOff;
    hud_.holdToasts(false);
    hud_.setPulse({}, {});
    profile_.onboarded = true;
    profileChanged();
}

void App::setTourText() {
    static constexpr std::string_view kTileOf = "tile:";
    switch (tourStep_) {
    case kLook:
        coachText_ = strings::kTourLook;
        hud_.setPulse({}, {});
        break;
    case kOpenBuild:
        coachText_ = strings::kTourBuild;
        hud_.setPulse("build", {});
        break;
    case kPlant: {
        const std::string_view piece =
            cat_.tourPiece >= 0
                ? std::string_view(cat_.items[static_cast<std::size_t>(cat_.tourPiece)].name)
                : std::string_view{};
        std::string lower(piece);
        if (!lower.empty())
            lower[0] = static_cast<char>(std::tolower(static_cast<unsigned char>(lower[0])));
        coachText_ = std::vformat(strings::kTourPlant, std::make_format_args(lower));
        tourPulse_ = std::string(kTileOf) +
                     (cat_.tourPiece >= 0 ? cat_.items[static_cast<std::size_t>(cat_.tourPiece)].id
                                          : std::string{});
        hud_.setPulse(tourPulse_, {});
        // The drawer turns to the piece's tab, so the pulsing tile is in sight.
        if (cat_.tourPiece >= 0)
            category_ = cat_.items[static_cast<std::size_t>(cat_.tourPiece)].category;
        break;
    }
    case kWish:
        coachText_ =
            cat_.residentKind >= 0
                ? std::vformat(strings::kTourWish, std::make_format_args(cat_.resident.name))
                : std::string(strings::kTourWishAlone);
        hud_.setPulse("tray", {});
        break;
    case kKeys:
        coachText_ = strings::kTourKeys;
        hud_.setPulse("undo", "journal");
        break;
    case kEnd:
        coachText_ = strings::kTourEnd;
        hud_.setPulse({}, {});
        break;
    default: break;
    }
}

void App::updateTour(float dt) {
    if (tourStep_ == kTourOff || menus_.blocking()) return;
    tourT_ += dt;
    const int wish = cat_.tourWish;
    const auto next = [&] {
        ++tourStep_;
        tourT_ = 0;
        if (tourStep_ == kWish) {
            // Its wish is offered now, unless it was granted already (then the step is skipped).
            hud_.holdToasts(false);
            if (wish < 0 ||
                progress_.wishes[static_cast<std::size_t>(wish)].state == WishState::Done) {
                ++tourStep_;
            } else if (progress_.wishes[static_cast<std::size_t>(wish)].state ==
                       WishState::Waiting) {
                progress_.wishes[static_cast<std::size_t>(wish)].state = WishState::Open;
                progress_.open.push_back(wish);
                progression_.evaluate(world_, progress_, facts(), played_);
                play(sfx::kWish);
            }
        }
        if (tourStep_ > kEnd) {
            endTour();
            return;
        }
        setTourText();
    };
    switch (tourStep_) {
    case kLook:
        if (tourMoved_ || tourT_ >= tuning::kTourLookSeconds) next();
        break;
    case kOpenBuild:
        if (drawerOpen_) next();
        break;
    case kPlant:
        if (placements_ > tourPlacements_) next();
        break;
    case kWish:
        if (wish < 0 || progress_.wishes[static_cast<std::size_t>(wish)].state == WishState::Done)
            next();
        break;
    case kKeys:
        if (tourT_ >= tuning::kTourKeysSeconds) next();
        break;
    case kEnd:
        if (tourT_ >= tuning::kTourEndSeconds) next();
        break;
    default: break;
    }
}

} // namespace lc
