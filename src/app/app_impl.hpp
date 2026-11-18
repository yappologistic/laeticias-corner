#pragma once
// The App class shared by the app's translation units (main loop and input in app.cpp, scripted
// runs in app_script.cpp, the benchmark in app_bench.cpp). Not part of any public interface.

#include "app/options.hpp"
#include "app/script.hpp"
#include "app/window_state.hpp"
#include "audio/mixer.hpp"
#include "core/actors.hpp"
#include "core/autosave.hpp"
#include "core/catalog.hpp"
#include "core/clock.hpp"
#include "core/edit.hpp"
#include "core/events.hpp"
#include "core/lively.hpp"
#include "core/notes.hpp"
#include "core/progress.hpp"
#include "core/progression.hpp"
#include "core/rng.hpp"
#include "core/save.hpp"
#include "core/speech.hpp"
#include "core/tuning.hpp"
#include "core/visitors.hpp"
#include "core/weather.hpp"
#include "core/world.hpp"
#include "platform/batch.hpp"
#include "platform/sdl_ptr.hpp"
#include "render/atlas.hpp"
#include "render/blur.hpp"
#include "render/camera.hpp"
#include "render/scene.hpp"
#include "ui/font.hpp"
#include "ui/hud.hpp"

#include <filesystem>
#include <memory>
#include <optional>
#include <span>
#include <string>
#include <string_view>
#include <vector>

namespace lc {

namespace fs = std::filesystem;

// Process exit codes beyond 0 (success) and 1 (failure).
inline constexpr int kExitBadScript = 2;
inline constexpr int kExitOverBudget = 3;
inline constexpr int kExitNoRenderer = 77; // ctest treats it as "skipped"

// Files under the save directory (docs/design/living-corner.md §2.2).
inline constexpr std::string_view kWorldsDir = "worlds";
inline constexpr std::string_view kWorldFile = "world.json";
inline constexpr std::string_view kThumbFile = "thumb.png";
inline constexpr std::string_view kProfileFile = "profile.json";
inline constexpr std::string_view kLegacyFile = "corner.json";
inline constexpr std::string_view kLegacyKept = "corner.v1.json";

class App {
public:
    App(const Options& o, Catalog cat, fs::path assets);

    int run();

private:
    bool init();
    bool createWindow();
    void loadOrStart();
    void startNewWorld(std::vector<std::string> taken);
    void adopt(SaveData& data);
    bool loadWorld(const fs::path& file);
    bool save();
    [[nodiscard]] fs::path worldDir() const { return saveDir_ / kWorldsDir / slug_; }
    // Renders the open home region into a small image beside the world save.
    bool writeThumbnail();
    void handleEvent(const SDL_Event& e);
    void handleKey(const SDL_KeyboardEvent& k);
    void applyHudActions();
    void worldInput();
    void applyTool(TilePos t, bool first);
    void step(float dt);
    void render();
    void refreshScale();
    void frameCamera();
    void zoomBy(int steps, Vec2 px);
    void undoRedo(bool redo);
    void updateAudio();
    void play(std::string_view file, float gain = tuning::kSfxLevel, bool jitter = false);
    void feedback(std::span<const Op> ops);
    void setTool(Tool t, int selection);
    void togglePhoto();
    void capturePhoto();
    void cycleClock();
    void markDirty() { autosave_.changed(); }
    // The progress loop: facts for conditions, re-evaluation when something changed, pacing.
    [[nodiscard]] CondFacts facts() const;
    void updateProgress();
    void onWishGranted(int wish);
    void onNookFound(int nook);
    void updateHoverNook();
    // Opens the next land stage; with `wave`, the brambles clear visibly and a chip points the
    // way when it is out of sight.
    void openLand(int stage, bool wave);
    [[nodiscard]] int pages() const;
    // Seasons: the effective one (pinned or from the calendar), its grade gliding in, and the
    // lighting with that grade applied.
    [[nodiscard]] int season() const;
    void updateSeason(float dt);
    [[nodiscard]] Lighting lighting() const;
    [[nodiscard]] bool snowing() const;
    void setupMusic();
    // Beds grow by `seconds` of play; a click with an empty hand picks a ripe one.
    void growBeds(float seconds);
    // One tuned note of the building phrase (never pitch-jittered, so it stays in tune).
    void playNote();
    bool pick(TilePos t);
    void unlockStems(const CondFacts& f, bool instant);
    [[nodiscard]] std::string_view waitingText(int node, std::string& out) const;
    [[nodiscard]] Vec2 screen() const {
        return {static_cast<float>(pixelW_), static_cast<float>(pixelH_)};
    }
    [[nodiscard]] HudModel model() const;
    [[nodiscard]] Item ghostItem(TilePos hover) const;
    [[nodiscard]] Ghost ghost() const;
    [[nodiscard]] bool night() const;
    // Life (actors, weather, events, speech): app.cpp's second half lives in app_life.cpp.
    [[nodiscard]] ActorEnv actorEnv() const;
    void updateLife(float dt);
    void handleActorEvents();
    void handleWorldEvents();
    void refreshNooks();
    // The weather where the camera looks (sky, sound, the conditions' `weather`).
    [[nodiscard]] bool raining() const;
    [[nodiscard]] float rainHere() const;
    [[nodiscard]] Vec2 viewTile() const;
    void cycleWeather();
    // A sound placed in the stereo field by where its source is on screen, quieter far away;
    // the same sound twice within kMergeSeconds plays once, and busy moments drop extras.
    void playAt(std::string_view file, float gain, Vec2 tile, bool jitter = false);
    [[nodiscard]] float distanceGain(Vec2 tile) const;
    [[nodiscard]] float panOf(Vec2 tile) const;
    // The resident speaks (a bubble, if she is on screen, and one of her murmurs).
    bool speak(int context, SpeechWeight weight);
    bool speakText(std::string_view text, SpeechWeight weight);
    [[nodiscard]] bool residentOnScreen() const;
    // Something was placed, moved or removed over `rect` (type -1: water painted, -2: removed).
    void disturbed(TileRect rect, int type, bool fresh);
    [[nodiscard]] std::optional<int> actorUnder(Vec2 px) const;
    [[nodiscard]] int moversInView() const;
    // Chunk-aligned area around the view where critters live.
    [[nodiscard]] TileRect activeArea() const;
    void buildThumbs();
    void rememberWindow();

    // Scripting (app_script.cpp)
    bool scriptStep();
    std::optional<Vec2> resolve(const ScriptPoint& p);
    void pushMouseMotion(Vec2 px);
    void pushButton(Vec2 px, bool down, bool right);
    void pushKey(std::string_view combo, bool down);
    std::optional<std::string> check(const ScriptCommand& c);
    bool shot(const fs::path& file);

    // Benchmark (app_bench.cpp)
    int runBench();
    void fillBenchWorld();
    // The soak run: busy play for opts_.soak seconds, memory checked to stay flat.
    int runSoak();

    Options opts_;
    fs::path assets_;
    fs::path saveDir_;
    Catalog cat_;
    World world_;
    Editor editor_{tuning::kUndoSteps};
    Clock clock_;
    std::uint64_t seed_; // the game's one seed; every random stream derives from it
    Rng rng_;
    Actors actors_;
    std::vector<VisitorGate> gates_; // per visitor, from the progress loop
    Weather weather_;
    EventScheduler events_;
    Speech speech_;
    LivelyProbe lively_;
    std::vector<PreferArea> prefer_; // nook areas that weigh what actors choose
    std::vector<NookPlace> nookPlaces_;
    std::uint64_t nookRevision_ = ~0ULL;
    std::vector<std::uint8_t> nookSeen_; // nookHere when the places were gathered
    struct Played {
        int sfx;
        double at;
    };
    std::vector<Played> recentSounds_; // positional one-shots, for merging and the budget
    double idleLineAt_ = 0;            // when she may next say an idle line
    double livelyAt_ = 0;              // next liveliness sample
    // Per-system times of the last step (ms), kept measurable for the bench and a profiler.
    double actorMs_ = 0;    // actors
    double lifeMs_ = 0;     // weather, events, speech and sound around them
    double progressMs_ = 0; // conditions, wishes, nooks, rare visitors
    int ripeDay_ = -1;      // the day a bed first ripened (her "something's ripe" line)
    double ripeSince_ = -1; // when, in play seconds
    bool rainWas_ = false;  // rain at the view, last step
    int fallCount_ = 0;     // water tiles at the rims (the waterfall's bed)
    Vec2 fallCentre_;       // their middle, in tiles
    std::uint64_t fallRevision_ = ~0ULL;
    bool muted_ = false;
    Progress progress_;
    Progression progression_;
    std::uint64_t evalRevision_ = ~0ULL; // world revision last evaluated
    double evalDue_ = -1;                // play time of a debounced evaluation
    std::uint64_t factsKey_ = ~0ULL;     // what the facts were at the last evaluation
    mutable std::vector<WishCard> cards_;
    // Nooks: the one under the pointer (outlined, named) and names floating over new ones.
    struct NookLabel {
        int nook;
        Vec2 world; // above its anchor
        float start;
    };
    std::vector<NookLabel> nookLabels_;
    mutable std::vector<FloatLabel> floatLabels_;
    std::vector<NearInstance> hoverNook_;
    std::string_view hoverTip_;
    std::optional<TilePos> hoverNookTile_;
    std::uint64_t hoverNookRevision_ = ~0ULL;
    bool loading_ = true;      // the first evaluation finds what was already there, quietly
    std::string hoverTipText_; // storage for formatted world tooltips
    float edgeChipUntil_ = 0;
    double growthAcc_ = 0;
    PhraseWalker notes_;
    double lastNote_ = -1;
    int strokeTiles_ = 0; // tiles painted in this stroke, for its notes
    bool anyRipe_ = false;
    Vec2 edgeChipTarget_;
    mutable std::vector<std::string> cardDetail_;
    HudModel ui_; // this frame's interface model (see run())
    // The open world save and the profile shared by all of them.
    std::string worldName_;
    std::string created_;
    std::string slug_;
    bool freeBuild_ = false;
    double played_ = 0; // active play time, seconds
    int seasonPin_ = -1;
    int seasonShown_ = -2;     // the season the scene shows (-2: none yet)
    bool seasonByPin_ = false; // the next season change came from the pin: glide quickly
    Rgb gradeFrom_;
    Rgb gradeTo_;
    float gradeT_ = 1;
    float gradeSeconds_ = 1;
    Phase lastPhase_ = Phase::Day;
    int lastDay_ = 0;
    std::vector<int> dayStems_; // loops of each piece's stems
    std::vector<int> nightStems_;
    std::vector<std::uint8_t> stemOn_; // per catalog stem (day, then night): unlocked
    Profile profile_;
    std::string profileWritten_; // the profile as last written, to write it only on change
    std::optional<Vec2> savedCamera_;
    float savedZoom_ = 1;
    double thumbTimer_ = 0;
    fs::path legacyToRetire_; // an old save to rename once its world and thumbnail are written
    float retireAt_ = 0;      // when to try that again after a failed write
    bool welcomePending_ = false;
    Camera camera_;

    WindowPtr window_;
    RendererPtr renderer_;
    std::unique_ptr<Atlas> atlas_;
    std::unique_ptr<Scene> scene_;
    std::unique_ptr<Batch> uiBatch_;
    std::unique_ptr<Blur> blur_;
    ThumbSet thumbs_;
    Font font_;
    Hud hud_;
    Mixer mixer_;
    std::vector<float> capture_; // the mix, when capturing audio
    int pixelW_ = 0;
    int pixelH_ = 0;
    float density_ = 1;
    float uiScale_ = 1;
    WindowState windowState_;

    // Input
    Vec2 mouse_;
    bool mouseInside_ = false;
    bool leftPressed_ = false;
    bool leftReleased_ = false;
    bool rightPressed_ = false;
    bool rightReleased_ = false;
    float wheel_ = 0;     // this frame, for the interface
    float wheelAcc_ = 0;  // toward the next zoom step
    float wheelIdle_ = 0; // seconds since the last wheel event
    bool keyPan_[4] = {};
    enum class Drag : std::uint8_t { None, Tool, Pan };
    Drag drag_ = Drag::None;
    bool rightDown_ = false;
    bool panPending_ = false; // right or middle button went down: pan unless the UI takes it
    Vec2 rightStart_;
    Vec2 pressStart_;
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
    AutosaveClock autosave_;
    bool saveFailing_ = false;
    bool saveBlocked_ = false; // an unreadable save could not be moved aside: never overwrite it
    bool newerSave_ = false;   // the world to open came from a newer build and was left alone
    bool running_ = true;
    int exitCode_ = 0;
    int frame_ = 0;

    // Script state
    std::vector<ScriptCommand> script_;
    std::size_t scriptPos_ = 0;
    int scriptPhase_ = 0; // sub-step within the current command
    int scriptWait_ = 0;
    int scriptRetries_ = 0; // frames spent waiting for a widget to scroll into view
};

} // namespace lc
