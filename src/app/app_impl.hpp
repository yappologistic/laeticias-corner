#pragma once
// The App class shared by the app's translation units (main loop and input in app.cpp, scripted
// runs in app_script.cpp, the benchmark in app_bench.cpp). Not part of any public interface.

#include "app/options.hpp"
#include "app/script.hpp"
#include "app/window_state.hpp"
#include "audio/mixer.hpp"
#include "core/autosave.hpp"
#include "core/catalog.hpp"
#include "core/clock.hpp"
#include "core/edit.hpp"
#include "core/rng.hpp"
#include "core/tuning.hpp"
#include "core/visitors.hpp"
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

class App {
public:
    App(const Options& o, Catalog cat, fs::path assets);

    int run();

private:
    bool init();
    bool createWindow();
    void loadOrStart();
    bool save();
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
    [[nodiscard]] Vec2 screen() const {
        return {static_cast<float>(pixelW_), static_cast<float>(pixelH_)};
    }
    [[nodiscard]] HudModel model() const;
    [[nodiscard]] Item ghostItem(TilePos hover) const;
    [[nodiscard]] Ghost ghost() const;
    [[nodiscard]] bool night() const;
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
    float wheel_ = 0;     // this frame, for the interface
    float wheelAcc_ = 0;  // toward the next zoom step
    float wheelIdle_ = 0; // seconds since the last wheel event
    bool keyPan_[4] = {};
    enum class Drag : std::uint8_t { None, Tool, Pan };
    Drag drag_ = Drag::None;
    bool rightDown_ = false;
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
