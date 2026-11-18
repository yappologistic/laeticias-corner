// The windowed benchmark (--benchmark): the one mode meant for a person to launch. It plays a
// fixed, seeded 75-second tour of the corner's busiest views in a real window with vsync off,
// waiting for the GPU every frame so the times are whole, then shows a results card and writes
// benchmark-<date>.txt beside the save. Headless (tests) it runs one step per frame and exits
// after writing the report.

#include "app/app_impl.hpp"
#include "ui/strings.hpp"

#include <algorithm>
#include <chrono>
#include <format>
#include <string>
#include <vector>

namespace lc {
namespace {

// The tour: what each stretch shows. Times in seconds from the start.
struct Leg {
    float until;
    const char* name;
    int zoomLevel; // index into kZoomLevels
    ClockPin pin;  // time of day
    bool rain;
    float panSpeed; // window px per second along a slow circle (fast legs pan quicker)
    bool panels;    // the drawer and sketchbook open
};
constexpr Leg kTour[] = {
    {10, "day, 1x", 2, ClockPin::Day, false, 60, false},
    {20, "close up, 2x and 3x", 3, ClockPin::Day, false, 90, false},
    {30, "overview, 0.5x and 0.25x", 1, ClockPin::Dusk, false, 120, false},
    {45, "night with lights and rain", 2, ClockPin::Night, true, 80, false},
    {60, "fast panning", 2, ClockPin::Day, false, 900, false},
    {75, "panels open, busy corner", 2, ClockPin::Dusk, false, 140, true},
};
constexpr float kTourSeconds = 75.0f;

PerfStats statsOf(const std::vector<FrameSample>& frames, float FrameSample::* field) {
    std::vector<float> v;
    v.reserve(frames.size());
    for (const FrameSample& f : frames)
        if (f.*field >= 0) v.push_back(f.*field);
    return perfStats(v);
}

} // namespace

int App::runBenchmark() {
    fillBenchWorld();
    for (std::size_t v = 0; v < cat_.visitors.size(); ++v) {
        actors_.markSeen(static_cast<int>(v));
        gates_[v].allowed = true;
    }
    camera_.setLand(world_.landBounds(), scene_->cliffDepth());
    actors_.populate(actorEnv());
    const Vec2 mid = cat_.iso().toWorld(static_cast<float>(world_.width()) * 0.5f,
                                        static_cast<float>(world_.height()) * 0.5f);
    camera_.place(mid, 1, screen());

    // A second of warming up first: caches fill, nothing is measured.
    for (int i = 0; i < static_cast<int>(1.0 / tuning::kStepSeconds); ++i) (void)benchFrame();

    std::vector<FrameSample> frames;
    std::vector<std::vector<float>> legFrames(std::size(kTour));
    frames.reserve(static_cast<std::size_t>(kTourSeconds * 400));
    const bool fixed = opts_.headless;
    double t = 0; // tour time
    Uint64 last = SDL_GetTicksNS();
    int leg = -1;
    while (running_ && t < kTourSeconds) {
        const Uint64 t0 = SDL_GetPerformanceCounter();
        for (SDL_Event e; SDL_PollEvent(&e);) {
            if (e.type == SDL_EVENT_QUIT ||
                (e.type == SDL_EVENT_KEY_DOWN && e.key.key == SDLK_ESCAPE))
                return 0; // stopped early: nothing to report
            if (e.type == SDL_EVENT_WINDOW_PIXEL_SIZE_CHANGED) handleEvent(e);
        }
        const Uint64 now = SDL_GetTicksNS();
        const double real = fixed ? tuning::kStepSeconds : static_cast<double>(now - last) * 1e-9;
        last = now;
        t += real;
        // The leg this moment belongs to, and its setting.
        int l = 0;
        while (l + 1 < static_cast<int>(std::size(kTour)) &&
               t >= static_cast<double>(kTour[static_cast<std::size_t>(l)].until))
            ++l;
        const Leg& g = kTour[static_cast<std::size_t>(l)];
        if (l != leg) {
            leg = l;
            clock_.setPin(g.pin, true);
            weather_.setMode(g.rain ? WeatherMode::Rain : WeatherMode::Clear);
            drawerOpen_ = journalOpen_ = g.panels;
            camera_.zoomTo(g.zoomLevel, {screen().x * 0.5f, screen().y * 0.5f}, screen());
        }
        // Legs that show two zoom levels switch halfway.
        const float legStart = l == 0 ? 0.0f : kTour[static_cast<std::size_t>(l) - 1].until;
        const bool second = t > static_cast<double>((legStart + g.until) * 0.5f);
        if (second && (l == 1 || l == 2) && camera_.level() == g.zoomLevel)
            camera_.zoomTo(g.zoomLevel + (l == 1 ? 1 : -1), {screen().x * 0.5f, screen().y * 0.5f},
                           screen());
        // A slow circle around the middle; the fast leg sweeps across.
        const auto angle = static_cast<float>(t * 0.6);
        const auto dt = static_cast<float>(real);
        camera_.dragBy(
            {std::cos(angle) * g.panSpeed * dt, std::sin(angle) * g.panSpeed * 0.5f * dt},
            screen());

        // A frame as in play, timed whole (benchFrame steps once; real time may need more).
        const int steps = fixed ? 1
                                : std::clamp(static_cast<int>(real / tuning::kStepSeconds), 1,
                                             tuning::kMaxStepsPerFrame);
        for (int i = 1; i < steps; ++i) step(static_cast<float>(tuning::kStepSeconds));
        FrameSample f = benchFrame();
        f.frameMs = static_cast<float>(msBetween(t0, SDL_GetPerformanceCounter()));
        f.steps = steps;
        frames.push_back(f);
        legFrames[static_cast<std::size_t>(l)].push_back(f.frameMs);
    }

    // The report.
    const PerfStats whole = statsOf(frames, &FrameSample::frameMs);
    const PerfStats cpu = statsOf(frames, &FrameSample::cpuMs);
    const PerfStats gpu = statsOf(frames, &FrameSample::gpuMs);
    const auto over = [&](double ms) {
        return 100.0 *
               static_cast<double>(std::ranges::count_if(
                   frames, [&](const FrameSample& f) { return f.frameMs > ms; })) /
               static_cast<double>(std::max<std::size_t>(frames.size(), 1));
    };
    const bool pass = whole.p99 <= tuning::kFrameP99Ms && whole.worst <= tuning::kFrameWorstMs &&
                      cpu.avg <= tuning::kCpuBudgetMs;
    const SDL_DisplayMode* mode = SDL_GetCurrentDisplayMode(SDL_GetDisplayForWindow(window_.get()));
    const char* video = SDL_GetCurrentVideoDriver();
    std::vector<std::string> lines;
    lines.push_back(std::format("{} {}", strings::kBenchmarkTitle, utcNow()));
    lines.push_back(std::format(
        "Verdict: {} (budgets: p99 {:.1f} ms, worst {:.1f} ms, CPU {:.1f} ms)",
        pass ? "PASS" : "FAIL", tuning::kFrameP99Ms, tuning::kFrameWorstMs, tuning::kCpuBudgetMs));
    lines.push_back(std::format("Renderer: {} · video: {} · vsync off",
                                SDL_GetRendererName(renderer_.get()), video ? video : "?"));
    lines.push_back(std::format("Window: {}x{} px · display {}x{} at {:.0f} Hz", pixelW_, pixelH_,
                                mode ? mode->w : 0, mode ? mode->h : 0,
                                mode ? static_cast<double>(mode->refresh_rate) : 0.0));
    lines.push_back(std::format("Frames: {} in {:.0f} s · average {:.0f} FPS", frames.size(),
                                kTourSeconds,
                                whole.avg > 0 ? 1000.0 / static_cast<double>(whole.avg) : 0.0));
    const auto row = [&](const char* what, const PerfStats& s) {
        lines.push_back(std::format("{}\tavg {:.2f} · p95 {:.2f} · p99 {:.2f} · worst {:.2f} ms",
                                    what, s.avg, s.p95, s.p99, s.worst));
    };
    row("Whole frame", whole);
    row("CPU", cpu);
    row("GPU done", gpu);
    lines.push_back(std::format("Frames over 8.3 ms: {:.2f}% · over 16.6 ms: {:.2f}%",
                                over(tuning::kFrameP99Ms), over(tuning::kFrameWorstMs)));
    for (std::size_t i = 0; i < std::size(kTour); ++i) {
        const PerfStats s = perfStats(legFrames[i]);
        lines.push_back(
            std::format("  {}\tp99 {:.2f} · worst {:.2f} ms", kTour[i].name, s.p99, s.worst));
    }
    lines.push_back(std::format("Memory: process peak {:.0f} MiB", processMemory().second));
    // In the file the columns are padded with spaces; the card lines them up itself.
    std::size_t col = 0;
    for (const std::string& l : lines)
        if (const auto tab = l.find('\t'); tab != std::string::npos) col = std::max(col, tab);
    std::string text;
    for (const std::string& l : lines) {
        const auto tab = l.find('\t');
        text += tab == std::string::npos
                    ? l
                    : l.substr(0, tab) + std::string(col + 2 - tab, ' ') + l.substr(tab + 1);
        text += '\n';
    }
    const auto stamp = std::chrono::floor<std::chrono::seconds>(std::chrono::system_clock::now());
    const fs::path file = saveDir_ / std::format("benchmark-{:%Y%m%d-%H%M%S}.txt", stamp);
    if (auto r = writeFileAtomic(file, text); !r) {
        SDL_Log("benchmark: %s", r.error().c_str());
        return 1;
    }
    SDL_Log("benchmark: wrote %s", file.string().c_str());

    // The results card stays until the window is closed or a key is pressed. Headless, it is
    // drawn once into an image beside the report (for the tests' eyes) and the run ends.
    lines.push_back(std::string(strings::kBenchmarkClose));
    drawerOpen_ = journalOpen_ = false;
    hudHidden_ = true;
    if (opts_.headless) running_ = false;
    do {
        for (SDL_Event e; SDL_PollEvent(&e);) {
            if (e.type == SDL_EVENT_QUIT || e.type == SDL_EVENT_KEY_DOWN ||
                e.type == SDL_EVENT_MOUSE_BUTTON_DOWN)
                running_ = false;
            if (e.type == SDL_EVENT_WINDOW_PIXEL_SIZE_CHANGED) handleEvent(e);
        }
        step(static_cast<float>(tuning::kStepSeconds));
        alpha_ = 1;
        prepareView();
        render();
        if (font_.build(renderer_.get(), uiScale_)) {
            Painter painter(*uiBatch_, font_, {blur_->result(), screen(), 0.5f}, uiScale_);
            Profiler::drawCard(painter, lines, screen(), uiScale_, pass);
            uiBatch_->flush();
        }
        if (opts_.headless) return shot(saveDir_ / "benchmark-card.png") ? 0 : 1;
        if (!SDL_RenderPresent(renderer_.get())) SDL_Log("present: %s", SDL_GetError());
        SDL_Delay(16); // the card needs no speed
    } while (running_);
    return 0;
}

} // namespace lc
