// The benchmark: a map of any size, densely built around the camera and sparse elsewhere, run at
// night in the rain with the interface open so every pass is busy; reports update and draw times
// (average, 95th percentile, worst) at the working zoom and the overview, plus memory.

#include "app/app_impl.hpp"
#include "worldview/tuning.hpp"

#include <algorithm>
#include <cstdio>
#include <fstream>
#include <functional>
#include <string>

namespace lc {
namespace {

constexpr int kNearSide = 96;      // tiles of dense building around the map centre
constexpr float kFarShare = 0.05f; // density elsewhere, relative to near
constexpr int kLakeSide = 12;
constexpr int kWarmup = 30;
constexpr float kPanPxPerFrame = 6.0f; // the second half of each phase pans

void report(const char* name, const char* what, const PerfStats& s) {
    std::printf("bench: %s: %-12s avg %.3f p95 %.3f p99 %.3f worst %.3f ms\n", name, what,
                static_cast<double>(s.avg), static_cast<double>(s.p95), static_cast<double>(s.p99),
                static_cast<double>(s.worst));
}

} // namespace

void App::fillBenchWorld() {
    Rng fill(opts_.seed.value_or(1));
    World& w = world_;
    const TilePos c{w.width() / 2, w.height() / 2};
    const TileRect near =
        TileRect{c.x - kNearSide / 2, c.y - kNearSide / 2, c.x + kNearSide / 2, c.y + kNearSide / 2}
            .clipped(w.bounds());
    const TileRect lake =
        TileRect{c.x - kLakeSide / 2, c.y + 4, c.x + kLakeSide / 2, c.y + 4 + kLakeSide}.clipped(
            w.bounds());
    for (int y = lake.y0; y < lake.y1; ++y)
        for (int x = lake.x0; x < lake.x1; ++x) w.setTerrain({x, y}, cat_.waterTerrain);
    const auto path = cat_.findTerrain("path");
    for (int y = 0; y < w.height(); ++y) {
        for (int x = 0; x < w.width(); ++x) {
            const float density =
                near.contains(TilePos{x, y}) ? opts_.density : opts_.density * kFarShare;
            if (path && w.terrainAt({x, y}) == cat_.baseTerrain && fill.chance(density * 0.1f))
                w.setTerrain({x, y}, *path);
            if (!fill.chance(density)) continue;
            for (int attempt = 0; attempt < 4 && w.itemAt({x, y}) == nullptr; ++attempt) {
                const int type = fill.range(0, static_cast<int>(cat_.items.size()) - 1);
                const int variant =
                    fill.range(0, cat_.items[static_cast<std::size_t>(type)].count - 1);
                const Item it = makeItem(cat_, type, variant, {x, y});
                if (canPlace(w, cat_, it) == PlaceResult::Ok) w.addItem(it);
            }
        }
    }
}

FrameSample App::benchFrame() {
    // The same work as a frame of play (a step, the interface, the scene, presentation), timed
    // whole: the GPU is waited for before presenting, so the frame's time includes its drawing.
    const Uint64 t0 = SDL_GetPerformanceCounter();
    step(static_cast<float>(tuning::kStepSeconds));
    frameDt_ = static_cast<float>(tuning::kStepSeconds);
    updateWorld(frameDt_);
    alpha_ = 1;
    prepareView();
    ui_ = model();
    hud_.update({}, ui_, font_, screen(), uiScale_, static_cast<float>(tuning::kStepSeconds));
    const Uint64 tUpdate = SDL_GetPerformanceCounter();
    render();
    const Uint64 tSubmit = SDL_GetPerformanceCounter();
    FrameSample f;
    f.gpuMs = static_cast<float>(syncGpu(t0));
    const Uint64 tPresent = SDL_GetPerformanceCounter();
    if (!SDL_RenderPresent(renderer_.get())) SDL_Log("present: %s", SDL_GetError());
    const Uint64 t1 = SDL_GetPerformanceCounter();
    f.frameMs = static_cast<float>(msBetween(t0, t1));
    f.cpuMs = static_cast<float>(msBetween(t0, tSubmit));
    f.simMs = static_cast<float>(actorMs_ + lifeMs_ + progressMs_);
    f.cityMs = static_cast<float>(cityMs_);
    f.condMs = static_cast<float>(progressMs_);
    f.uiMs = static_cast<float>(msBetween(t0, tUpdate)); // the update half: step and interface
    f.sceneMs = static_cast<float>(msBetween(tUpdate, tSubmit)); // the draw submission half
    f.presentMs = static_cast<float>(msBetween(tPresent, t1));
    f.drawCalls = sceneDrawCalls() + blur_->drawCalls() + uiBatch_->drawCalls();
    uiBatch_->resetStats();
    f.actorsLive = static_cast<int>(std::ranges::count_if(
        actors_.all(), [](const Actor& a) { return (a.flags & actor_flag::kAlive) != 0; }));
    f.steps = 1;
    return f;
}

int App::runBench() {
    fillBenchWorld();
    clock_.setPin(ClockPin::Night, true);
    weather_.setMode(WeatherMode::Rain);
    drawerOpen_ = true;
    journalOpen_ = true;
    camera_.setLand(world_.landBounds(), scene_->cliffDepth());
    const int frames = opts_.frames > 0 ? opts_.frames : 600;
    std::printf("bench: map %dx%d, %zu items, %dx%d px, %s renderer, density %.2f near\n",
                world_.width(), world_.height(), world_.items().size(), pixelW_, pixelH_,
                SDL_GetRendererName(renderer_.get()), static_cast<double>(opts_.density));
    const bool judge = opts_.budgetMs > 0;
    bool over = false;
    const auto fail = [&](const char* what) {
        std::printf("bench: over budget: %s\n", what);
        over = true;
    };
    {
        // Every condition the progress loop knows, evaluated over the filled map at once (the
        // worst case: in play only open wishes and changed facts are looked at).
        const CondFacts f = facts();
        const ConditionSet& cs = cat_.conditions;
        std::vector<float> cond;
        int holding = 0;
        for (int i = 0; i < 40; ++i) {
            holding = 0;
            const Uint64 t0 = SDL_GetPerformanceCounter();
            for (const WishDef& w : cat_.wishes) {
                holding += cs.eval(w.goal, world_, f) ? 1 : 0;
                if (w.gate >= 0) holding += cs.eval(w.gate, world_, f) ? 1 : 0;
            }
            for (const NookDef& n : cat_.nooks) holding += cs.eval(n.condition, world_, f) ? 1 : 0;
            for (const VisitorDef& v : cat_.visitors)
                if (v.recipe >= 0) holding += cs.eval(v.recipe, world_, f) ? 1 : 0;
            for (const auto* piece : {&cat_.audio.dayStems, &cat_.audio.nightStems})
                for (const StemDef& st : *piece)
                    if (st.when >= 0) holding += cs.eval(st.when, world_, f) ? 1 : 0;
            cond.push_back(static_cast<float>(msBetween(t0, SDL_GetPerformanceCounter())));
        }
        const PerfStats c = perfStats(cond);
        std::printf("bench: conditions: every wish, gate, nook, recipe and stem: avg %.3f worst "
                    "%.3f ms (%d hold)\n",
                    static_cast<double>(c.avg), static_cast<double>(c.worst), holding);
        if (judge && c.avg > tuning::kConditionBudgetMs) fail("conditions");
    }
    // One case: its frames timed, reported and held to the budgets of CLAUDE.md (whole frame
    // 99th percentile and worst; the CPU's update and draw submission on average).
    // Returns false when only the worst frame was over: a lone frame on a busy machine can be
    // the scheduler's, so the caller measures that case once more before calling it a failure.
    const auto judgeCase = [&](const char* name, const BenchFrames& fr, bool last) {
        const PerfStats whole = fr.of(&FrameSample::frameMs);
        const PerfStats cpu = fr.of(&FrameSample::cpuMs);
        report(name, "whole frame", whole);
        report(name, "gpu done", fr.of(&FrameSample::gpuMs));
        report(name, "cpu", cpu);
        report(name, "update", fr.of(&FrameSample::uiMs));
        report(name, "draw submit", fr.of(&FrameSample::sceneMs));
        report(name, "simulation", fr.of(&FrameSample::simMs));
        const auto [rss, peak] = processMemory();
        std::printf("bench: %s: memory rss %.0f MiB, peak %.0f MiB (ceiling %.0f at 1080p)\n", name,
                    rss, peak, memoryCeiling());
        if (!judge) return true;
        if (cpu.avg > opts_.budgetMs || whole.p99 > tuning::kFrameP99Ms) fail(name);
        if (whole.worst <= tuning::kFrameWorstMs) return true;
        if (last) {
            fail(name);
            return true;
        }
        std::printf("bench: %s: one frame over %.1f ms; measuring again\n", name,
                    tuning::kFrameWorstMs);
        return false;
    };
    const auto warm = [&] {
        for (int f = 0; f < kWarmup; ++f) (void)benchFrame();
    };
    for (const int level : {kDefaultZoomLevel, kDefaultZoomLevel - 1})
        for (int attempt = 0; attempt < 2; ++attempt) {
            // Centre the camera on the built-up middle at this level.
            const Vec2 mid = cat_.iso().toWorld(static_cast<float>(world_.width()) * 0.5f,
                                                static_cast<float>(world_.height()) * 0.5f);
            const Vec2 here = camera_.worldToScreen(mid, screen());
            camera_.dragBy({screen().x * 0.5f - here.x, screen().y * 0.5f - here.y}, screen());
            camera_.zoomTo(level, {screen().x * 0.5f, screen().y * 0.5f}, screen());
            for (int i = 0; i < 120 && !camera_.settled(); ++i)
                camera_.update(static_cast<float>(tuning::kStepSeconds), screen());
            actors_.populate(actorEnv());
            warm();
            BenchFrames still;
            BenchFrames pan;
            int slots = 0;
            for (int f = 0; f < frames; ++f) {
                const bool panning = f >= frames / 2;
                if (panning) camera_.dragBy({kPanPxPerFrame, kPanPxPerFrame * 0.5f}, screen());
                const FrameSample s = benchFrame();
                (panning ? pan : still).all.push_back(s);
                slots += scene_->stats().groundSlotsRendered;
            }
            const SceneStats st = scene_->stats();
            char name[32];
            (void)std::snprintf(name, sizeof name, "zoom %g", static_cast<double>(camera_.zoom()));
            std::printf(
                "bench: %s: %d actors, %zu items in region, %zu drawn, %d draw calls, %d "
                "ground chunks redrawn; textures: atlas %.0f, targets %.0f, ground cache %.0f, "
                "blur %.0f MiB\n",
                name, pan.all.back().actorsLive, st.regionItems, st.drawnItems,
                pan.all.back().drawCalls, slots,
                static_cast<double>(atlas_->textureBytes()) / 1048576.0,
                static_cast<double>(st.targetBytes) / 1048576.0,
                static_cast<double>(st.groundBytes) / 1048576.0,
                static_cast<double>(blur_->bytes()) / 1048576.0);
            BenchFrames all = still;
            all.all.insert(all.all.end(), pan.all.begin(), pan.all.end());
            report(name, "panning", pan.of(&FrameSample::frameMs));
            if (judgeCase(name, all, attempt == 1)) break;
        }
    // A busy corner: every visitor kind seen and allowed, at its full number; then a crowd of
    // kBenchCrowd actors. The actor update is timed on its own against its share of the frame.
    for (std::size_t v = 0; v < cat_.visitors.size(); ++v) {
        actors_.markSeen(static_cast<int>(v));
        gates_[v].allowed = true;
    }
    clock_.setPin(ClockPin::Day, true);
    weather_.setMode(WeatherMode::Natural);
    for (const int crowd : {0, tuning::kBenchCrowd})
        for (int attempt = 0; attempt < 2; ++attempt) {
            actors_.populate(actorEnv());
            if (crowd > 0)
                actors_.crowd(actorEnv(),
                              crowd - static_cast<int>(
                                          std::ranges::count_if(actors_.all(), [](const Actor& a) {
                                              return (a.flags & actor_flag::kAlive) != 0;
                                          })));
            warm();
            BenchFrames fr;
            std::vector<float> act;
            for (int f = 0; f < frames; ++f) {
                fr.all.push_back(benchFrame());
                act.push_back(static_cast<float>(actorMs_));
            }
            const char* name = crowd > 0 ? "crowd" : "busy corner";
            const PerfStats a = perfStats(act);
            std::printf("bench: %s: %d actors (path searches in the last step %d)\n", name,
                        fr.all.back().actorsLive, actors_.searches());
            report(name, "actors", a);
            const double actorBudget = crowd > 0 ? tuning::kCrowdBudgetMs : tuning::kSimBudgetMs;
            if (judge && (a.avg > actorBudget || fr.of(&FrameSample::simMs).avg >
                                                     static_cast<float>(tuning::kSimBudgetMs)))
                fail(name);
            if (judgeCase(name, fr, attempt == 1)) break;
        }
    if (worldView_ && !benchWorld(judgeCase, warm, frames)) over = true;
    // Memory is held to its ceiling at the size the gate runs (1080p and below).
    if (judge && pixelW_ * pixelH_ <= 1920 * 1080 && processMemory().second > memoryCeiling())
        fail("memory");
    const int city = benchCity(judge);
    return over || city == kExitOverBudget ? kExitOverBudget : 0;
}

bool App::benchWorld(const std::function<bool(const char*, const BenchFrames&, bool)>& judgeCase,
                     const std::function<void()>& warm, int frames) {
    // The world (CLAUDE.md "Performance"): each city's busiest view at 1x by day with the
    // sketchbook and the profiler open, a fast pan across Rome, and fast travel.
    bool over = false;
    clock_.setPin(ClockPin::Day, true);
    drawerOpen_ = false;
    journalOpen_ = true;
    profilerOn_ = true;
    // The world's camera limits (the corner's cases keep the camera on the filled home).
    camera_.setLand(cameraLand(), 0, 0);
    const auto settle = [&] {
        for (int i = 0; i < tuning::kBenchSettleFrames; ++i) {
            (void)benchFrame();
            if (worldView_->settled()) break;
        }
    };
    const auto look = [&](Vec2 grid) {
        camera_.place(gridToHome(grid), kZoomLevels[kDefaultZoomLevel], screen());
        camera_.beginStep();
        worldView_->jumped(
            {camera_.position().x + homeOffset_.x, camera_.position().y + homeOffset_.y});
        settle();
    };
    struct BenchSpot {
        const char* name;
        Vec2 grid;
    };
    for (const BenchSpot& spot :
         {BenchSpot{"forum", {80, 1077}}, BenchSpot{"agora", {262, 672}},
          BenchSpot{"acropolis", {305, 618}}, BenchSpot{"parsa terrace", {376, 69}}})
        for (int attempt = 0; attempt < 2; ++attempt) {
            look(spot.grid);
            warm();
            BenchFrames fr;
            int draws = 0;
            for (int f = 0; f < frames; ++f) {
                fr.all.push_back(benchFrame());
                draws = std::max(draws, fr.all.back().drawCalls);
            }
            const double tex = static_cast<double>(worldView_->stats().textureBytes()) / 1048576.0;
            const double budget = static_cast<double>(worldView_->textureBudget()) / 1048576.0;
            std::printf("bench: %s: %d draw calls at most (world %d), %.0f MiB of world textures "
                        "(budget %.0f)\n",
                        spot.name, draws, worldView_->stats().drawCalls, tex, budget);
            if (opts_.budgetMs > 0 && tex > budget) {
                std::printf("bench: over budget: %s textures\n", spot.name);
                over = true;
            }
            if (judgeCase(spot.name, fr, attempt == 1)) break;
        }
    // Crowds (src/life/): each city at its busiest view and hour, on an ordinary day and on its
    // festival, the life simulated and drawn with the world.
    if (city_) {
        struct Crowd {
            const char* name;
            const char* region;
            const char* season;
            int day;
        };
        clock_.setPin(ClockPin::Auto, true);
        for (const Crowd& c :
             {Crowd{"rome crowd", "rome", "spring", 9}, Crowd{"rome parilia", "rome", "spring", 1},
              Crowd{"athens crowd", "athens", "summer", 5},
              Crowd{"athens panathenaia", "athens", "summer", 4},
              Crowd{"parsa crowd", "parsa", "spring", 0},
              Crowd{"parsa audience", "parsa", "spring", 1}}) {
            const int season = cat_.findSeason(c.season).value_or(0);
            const life::Busiest b = life::busiestView(*city_, c.region, c.day, season);
            seasonPin_ = season;
            clock_.setDay(c.day);
            clock_.setTime((b.hour - 6.0) / 24.0 + (b.hour < 6.0 ? 1.0 : 0.0));
            for (int attempt = 0; attempt < 2; ++attempt) {
                look({static_cast<float>(b.focus.x) + 0.5f, static_cast<float>(b.focus.y) + 0.5f});
                warm();
                BenchFrames fr;
                int draws = 0;
                int world = 0;
                std::vector<float> sim;
                std::vector<float> crowd;
                int drawn = 0;
                for (int f = 0; f < frames; ++f) {
                    fr.all.push_back(benchFrame());
                    draws = std::max(draws, fr.all.back().drawCalls);
                    world = std::max(world, worldView_->stats().drawCalls);
                    sim.push_back(static_cast<float>(cityMs_));
                    crowd.push_back(static_cast<float>(worldView_->stats().actorMs));
                    drawn = std::max(drawn, worldView_->stats().actorsDrawn);
                }
                const PerfStats s = perfStats(sim);
                const PerfStats p = perfStats(crowd);
                std::printf("bench: %s: %d live, %d drawn at most, city simulation avg %.3f worst "
                            "%.3f ms, crowd preparation avg %.3f ms, %d draw calls at most "
                            "(world %d%s)\n",
                            c.name, city_->city->liveCount(), drawn, static_cast<double>(s.avg),
                            static_cast<double>(s.worst), static_cast<double>(p.avg), draws, world,
                            world > tuning::kSceneDrawCalls ? ", over the scene's 40 (reported)"
                                                            : "");
                if (opts_.budgetMs > 0 && (s.avg > tuning::kSimBudgetMs ||
                                           city_->city->liveCount() > tuning::life::kLiveCap)) {
                    std::printf("bench: over budget: %s simulation\n", c.name);
                    over = true;
                }
                if (judgeCase(c.name, fr, attempt == 1)) break;
            }
        }
        seasonPin_ = -1;
        clock_.setPin(ClockPin::Day, true);
    }
    // A pan across Rome at 1800 px a second (30 px a step).
    for (int attempt = 0; attempt < 2; ++attempt) {
        look({60, 1050});
        BenchFrames fr;
        for (int f = 0; f < frames; ++f) {
            camera_.dragBy({tuning::kBenchWorldPanPx, tuning::kBenchWorldPanPx * 0.25f}, screen());
            fr.all.push_back(benchFrame());
        }
        if (judgeCase("pan rome", fr, attempt == 1)) break;
    }
    // Fast travel from Parsa to Rome and home: no frame frozen, each journey within a second.
    look({376, 69});
    for (const char* to : {"rome", "corner"}) {
        travelTo(loaded_->file.findRegion(to));
        BenchFrames fr;
        const Uint64 t0 = SDL_GetPerformanceCounter();
        while (travel_.region >= 0 && fr.all.size() < 600) fr.all.push_back(benchFrame());
        const double ms = msBetween(t0, SDL_GetPerformanceCounter());
        const PerfStats whole = fr.of(&FrameSample::frameMs);
        std::printf("bench: travel to %s: %.0f ms in %zu frames, worst frame %.2f ms\n", to, ms,
                    fr.all.size(), static_cast<double>(whole.worst));
        if (opts_.budgetMs > 0 &&
            (whole.worst > tuning::kFrameWorstMs || ms > tuning::kTravelBudgetMs)) {
            std::printf("bench: over budget: travel to %s\n", to);
            over = true;
        }
    }
    profilerOn_ = false;
    return !over;
}

double App::memoryCeiling() const {
    return worldView_ ? tuning::kBenchWorldMemoryMiB : tuning::kBenchMemoryMiB;
}

double App::soakCeiling() const {
    // On the software renderer (the soak's) the world's textures are process memory too.
    const bool software = std::string_view(SDL_GetRendererName(renderer_.get())) == "software";
    return memoryCeiling() + (worldView_ && software
                                  ? static_cast<double>(worldView_->textureBudget()) / 1048576.0
                                  : 0.0);
}

int App::runSoak() {
    // A busy corner left running: every visitor kind welcome, the clock and calendar going,
    // natural weather, events by their schedules. BenchFrames are drawn now and then so the scene's
    // caches take part too. Memory must stay flat once the first quarter has warmed it up, and
    // under the ceiling.
    fillBenchWorld();
    for (std::size_t v = 0; v < cat_.visitors.size(); ++v) actors_.markSeen(static_cast<int>(v));
    clock_.setPin(ClockPin::Auto, true);
    weather_.setMode(WeatherMode::Natural);
    camera_.setLand(world_.landBounds(), scene_->cliffDepth());
    actors_.populate(actorEnv());
    const auto steps = static_cast<long long>(opts_.soak / tuning::kStepSeconds);
    double warm = 0;
    std::vector<float> sim;
    std::vector<float> frames;
    sim.reserve(static_cast<std::size_t>(steps));
    // The calendar turns a day every kSoakDaySeconds of soak, so even the gate's short soak
    // crosses several season turns (and every cache keyed by season: Q3-04).
    const auto dayEvery = static_cast<long long>(tuning::kSoakDaySeconds / tuning::kStepSeconds);
    const int startSeason = season();
    int seasonTurns = 0;
    for (long long st = 0; st < steps; ++st) {
        if (st > 0 && st % dayEvery == 0) {
            const int before = season();
            clock_.setDay(clock_.day() + 1);
            seasonTurns += season() != before ? 1 : 0;
        }
        if (st % tuning::kSoakDrawEvery == 0) {
            frames.push_back(benchFrame().frameMs);
        } else {
            step(static_cast<float>(tuning::kStepSeconds));
        }
        sim.push_back(static_cast<float>(actorMs_ + lifeMs_ + progressMs_));
        if (st == steps / 4) warm = processMemory().first;
    }
    const auto [end, peak] = processMemory();
    const auto alive = std::ranges::count_if(
        actors_.all(), [](const Actor& a) { return (a.flags & actor_flag::kAlive) != 0; });
    const PerfStats s = perfStats(sim);
    const PerfStats f = perfStats(frames);
    std::printf("soak: %.0f s of play, day %d, %d season turns from %s, %td actors at the end\n",
                opts_.soak, clock_.day(), seasonTurns,
                cat_.seasons[static_cast<std::size_t>(startSeason)].id.c_str(), alive);
    const SceneStats st = scene_->stats();
    std::printf("soak: caches: ground %.1f MiB (%d chunks), textures %.1f MiB\n",
                static_cast<double>(st.groundBytes) / 1048576.0, st.groundChunksCached,
                static_cast<double>(atlas_->textureBytes() + st.targetBytes + st.groundBytes) /
                    1048576.0);
    std::printf(
        "soak: simulation step avg %.3f p95 %.3f p99 %.3f worst %.3f ms (budget avg %.2f)\n",
        static_cast<double>(s.avg), static_cast<double>(s.p95), static_cast<double>(s.p99),
        static_cast<double>(s.worst), tuning::kSimBudgetMs);
    std::printf("soak: drawn frames (%s renderer) avg %.3f p95 %.3f p99 %.3f worst %.3f ms\n",
                SDL_GetRendererName(renderer_.get()), static_cast<double>(f.avg),
                static_cast<double>(f.p95), static_cast<double>(f.p99),
                static_cast<double>(f.worst));
    std::printf("soak: rss %.1f MiB after a quarter, %.1f MiB at the end, peak %.1f (allowed "
                "growth %.1f MiB, ceiling %.0f MiB)\n",
                warm, end, peak, tuning::kSoakGrowthMiB, soakCeiling());
    bool over = false;
    if (end - warm > tuning::kSoakGrowthMiB) {
        std::printf("soak: memory grew\n");
        over = true;
    }
    // The ceiling and the simulation budget are held where budgets apply (--budget-ms): a
    // sanitizer build's shadow memory and pace are not the game's.
    if (opts_.budgetMs > 0 && peak > soakCeiling()) {
        std::printf("soak: memory over its ceiling\n");
        over = true;
    }
    if (opts_.budgetMs > 0 && s.avg > static_cast<float>(tuning::kSimBudgetMs)) {
        std::printf("soak: simulation over its budget\n");
        over = true;
    }
    // The cities: the active area roaming the world for as long (life.cpp's soak).
    if (soakCity() == kExitOverBudget) over = true;
    return over ? kExitOverBudget : 0;
}

} // namespace lc
