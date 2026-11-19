// The benchmark: a map of any size, densely built around the camera and sparse elsewhere, run at
// night in the rain with the interface open so every pass is busy; reports update and draw times
// (average, 95th percentile, worst) at the working zoom and the overview, plus memory.

#include "app/app_impl.hpp"
#include "worldview/tuning.hpp"

#include <algorithm>
#include <array>
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

// What the player would notice in a case: frames by time with the slow ones by cause, what
// arrived late, the cache work behind it, and the main thread's allocations.
void reportSmooth(const char* name, const BenchFrames& fr) {
    std::array<char, 512> line{};
    const HitchLog log = fr.hitches();
    (void)log.line(line);
    std::printf("bench: %s: %s\n", name, line.data());
    int popFrames = 0;
    int popCells = 0;
    int popSprites = 0;
    float popShare = 0;
    int built = 0;
    double buildMs = 0;
    double uploadMs = 0;
    double gatherMs = 0;
    double uploadKiB = 0;
    long allocs = 0;
    int allocFrames = 0;
    for (const FrameSample& f : fr.all) {
        popFrames += f.popCells > 0 || f.popSprites > 0 ? 1 : 0;
        popCells = std::max(popCells, f.popCells);
        popSprites = std::max(popSprites, f.popSprites);
        popShare = std::max(popShare, f.popShare);
        built += f.cellsBuilt;
        buildMs = std::max(buildMs, static_cast<double>(f.buildMs));
        uploadMs = std::max(uploadMs, static_cast<double>(f.uploadMs));
        gatherMs = std::max(gatherMs, static_cast<double>(f.gatherMs));
        uploadKiB += static_cast<double>(f.uploadKiB);
        if (f.allocs >= 0) {
            allocs += f.allocs;
            ++allocFrames;
        }
    }
    std::printf("bench: %s: pop-in in %d of %zu frames (at most %d cells, %.1f%% of the view, %d "
                "sprites); built %d cells (worst frame %.2f ms), uploaded %.0f KiB (worst %.2f "
                "ms), gather on the main thread worst %.2f ms\n",
                name, popFrames, fr.all.size(), popCells, static_cast<double>(popShare) * 100.0,
                popSprites, built, buildMs, uploadKiB, uploadMs, gatherMs);
    if (allocFrames > 0)
        std::printf("bench: %s: %.1f allocations a frame on the main thread\n", name,
                    static_cast<double>(allocs) / allocFrames);
    std::printf("bench: %s: parts avg ms:", name);
    for (std::size_t i = 0; i < kFrameParts; ++i) {
        double sum = 0;
        for (const FrameSample& f : fr.all) sum += static_cast<double>(f.part[i]);
        std::printf(" %s %.3f", partName(static_cast<Part>(i)),
                    sum / static_cast<double>(std::max<std::size_t>(fr.all.size(), 1)));
    }
    std::printf("\n");
    if (allocFrames > 0) {
        std::printf("bench: %s: allocations by part:", name);
        for (std::size_t i = 0; i < kFrameParts; ++i) {
            double sum = 0;
            for (const FrameSample& f : fr.all) sum += f.partAllocs[i];
            if (sum > 0)
                std::printf(" %s %.1f", partName(static_cast<Part>(i)),
                            sum / static_cast<double>(fr.all.size()));
        }
        std::printf("\n");
    }
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
    const FrameMark mark = markFrame();
    partMs_ = {};
    partAllocs_ = {};
    step(static_cast<float>(tuning::kStepSeconds));
    stepMs_ = msBetween(t0, SDL_GetPerformanceCounter());
    stepAllocs_ = threadAllocs() - mark.allocs;
    frameDt_ = static_cast<float>(tuning::kStepSeconds);
    {
        const Timed timed(*this, Part::World);
        updateWorld(frameDt_);
    }
    alpha_ = 1;
    prepareView();
    const Uint64 tUi = SDL_GetPerformanceCounter();
    {
        const Timed timed(*this, Part::Model);
        ui_ = model();
    }
    {
        const Timed timed(*this, Part::UiUpdate);
        if (loaded_)
            map_.update(0, 0, false, false, false, mapModel(), font_, screen(), uiScale_, frameDt_);
        hud_.update({}, ui_, font_, screen(), uiScale_, static_cast<float>(tuning::kStepSeconds));
    }
    const Uint64 tUpdate = SDL_GetPerformanceCounter();
    render();
    const Uint64 tSubmit = SDL_GetPerformanceCounter();
    FrameSample f;
    closeMark(mark, f);
    f.gpuMs = static_cast<float>(syncGpu(t0));
    const Uint64 tPresent = SDL_GetPerformanceCounter();
    if (!SDL_RenderPresent(renderer_.get())) SDL_Log("present: %s", SDL_GetError());
    const Uint64 t1 = SDL_GetPerformanceCounter();
    f.frameMs = static_cast<float>(msBetween(t0, t1));
    f.cpuMs = static_cast<float>(msBetween(t0, tSubmit));
    f.simMs = static_cast<float>(actorMs_ + lifeMs_ + progressMs_);
    f.cityMs = static_cast<float>(cityMs_);
    f.condMs = static_cast<float>(progressMs_);
    f.updateMs = static_cast<float>(msBetween(t0, tUpdate));
    f.uiMs = static_cast<float>(msBetween(tUi, tUpdate) + hudDrawMs_);
    f.sceneMs = static_cast<float>(sceneMs_);
    f.presentMs = static_cast<float>(msBetween(tPresent, t1));
    f.drawCalls = sceneDrawCalls() + blur_->drawCalls() + uiBatch_->drawCalls();
    uiBatch_->resetStats();
    f.actorsLive = static_cast<int>(std::ranges::count_if(
        actors_.all(), [](const Actor& a) { return (a.flags & actor_flag::kAlive) != 0; }));
    f.steps = 1;
    closeParts(f);
    worldSample(f);
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
        report(name, "cpu (thread)", fr.of(&FrameSample::threadMs));
        // Not a time: millions of instructions, the same on a busy machine as on a quiet one.
        if (const PerfStats in = fr.of(&FrameSample::instrM); in.count > 0)
            std::printf("bench: %s: cpu work     avg %.2f p95 %.2f p99 %.2f worst %.2f M "
                        "instructions\n",
                        name, static_cast<double>(in.avg), static_cast<double>(in.p95),
                        static_cast<double>(in.p99), static_cast<double>(in.worst));
        report(name, "update", fr.of(&FrameSample::updateMs));
        report(name, "draw submit",
               fr.stats([](const FrameSample& f) { return f.cpuMs - f.updateMs; }));
        report(name, "simulation", fr.of(&FrameSample::simMs));
        report(name, "interface", fr.of(&FrameSample::uiMs));
        reportSmooth(name, fr);
        const auto [rss, peak] = processMemory();
        std::printf("bench: %s: memory rss %.0f MiB, peak %.0f MiB (ceiling %.0f at 1080p)\n", name,
                    rss, peak, memoryCeiling());
        if (!judge) return true;
        // The CPU budget is for the work the game does: where the system counts the main
        // thread's own CPU time that is what is judged, so a core taken away by another
        // program is not read as the game's work. The whole-frame budgets stay wall time: what
        // a player would see.
        const PerfStats work = fr.of(&FrameSample::threadMs);
        if ((work.count > 0 ? work.avg : cpu.avg) > opts_.budgetMs ||
            whole.p99 > tuning::kFrameP99Ms)
            fail(name);
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
    if (worldView_) {
        // Start-up: the frames from the first one until the world around the view is whole and
        // what loads ahead of need has loaded (pages, the wider levels). Their work is spread
        // out, so none may be slow; the CPU average is the steady state's budget, not theirs.
        BenchFrames fr;
        for (int f = 0; f < tuning::kBenchSettleFrames * 4; ++f) {
            fr.all.push_back(benchFrame());
            if (worldView_->idle()) break;
        }
        const PerfStats whole = fr.of(&FrameSample::frameMs);
        report("start-up", "whole frame", whole);
        report("start-up", "cpu (thread)", fr.of(&FrameSample::threadMs));
        reportSmooth("start-up", fr);
        std::printf("bench: start-up: everything around the first view ready after %zu frames\n",
                    fr.all.size());
        if (judge && (whole.p99 > tuning::kFrameP99Ms || whole.worst > tuning::kFrameWorstMs))
            fail("start-up frames");
        if (judge && startupMs_ > tuning::kStartupBudgetMs) fail("start-up time");
    }
    for (const int level : {kDefaultZoomLevel, kDefaultZoomLevel - 1})
        for (int attempt = 0; attempt < 2; ++attempt) {
            if (!benchWants(level == kDefaultZoomLevel ? "zoom 1" : "zoom 0.5")) break;
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
            if (!benchWants(crowd > 0 ? "crowd" : "busy corner")) break;
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
    const int city = benchWants("city life") ? benchCity(judge) : 0;
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
            // A steady view: what is built ahead of need (the wider levels) is done too. The
            // zoom, pan and travel cases are where that work is measured.
            if (worldView_->idle()) break;
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
            if (!benchWants(spot.name)) break;
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
            if (!benchWants(c.name)) continue;
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
    for (int attempt = 0; attempt < 2 && benchWants("pan rome"); ++attempt) {
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
        if (!benchWants("travel to")) break;
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
    if (!benchPlay(judgeCase)) over = true;
    if (benchWants("look") && !benchLook(judgeCase, warm, frames)) over = true;
    profilerOn_ = false;
    return !over;
}

bool App::benchPlay(const std::function<bool(const char*, const BenchFrames&, bool)>& judgeCase) {
    // What a player does with the view (CLAUDE.md "Performance": smooth always): zooming through
    // every level, fast pans at each scale, travel between every pair of places, the map opened
    // and closed. Each case holds the frame budgets and shows nothing arriving late: after a
    // view has settled, no cell from a coarser level and no sprite left out, on any frame.
    bool over = false;
    const bool judge = opts_.budgetMs > 0;
    journalOpen_ = false;
    const auto settle = [&] {
        for (int i = 0; i < tuning::kBenchSettleFrames; ++i) {
            (void)benchFrame();
            if (worldView_->idle()) break;
        }
    };
    const auto look = [&](Vec2 grid, int level) {
        camera_.place(gridToHome(grid), kZoomLevels[static_cast<std::size_t>(level)], screen());
        camera_.beginStep();
        worldView_->jumped(
            {camera_.position().x + homeOffset_.x, camera_.position().y + homeOffset_.y});
        settle();
    };
    // Pop-in over a case, against its allowance (frames that may show a stand-in at all).
    const auto smooth = [&](const char* name, const BenchFrames& fr, int allowed) {
        int popFrames = 0;
        int longest = 0;
        int run = 0;
        for (const FrameSample& f : fr.all) {
            const bool pop = f.popCells > 0 || f.popSprites > 0;
            popFrames += pop ? 1 : 0;
            run = pop ? run + 1 : 0;
            longest = std::max(longest, run);
        }
        std::printf("bench: %s: pop-in frames %d (allowed %d), longest run %d frames (%.0f ms at "
                    "60 FPS)\n",
                    name, popFrames, allowed, longest, longest * 1000.0 / 60.0);
        if (judge && popFrames > allowed) {
            std::printf("bench: over budget: %s pop-in\n", name);
            over = true;
        }
    };
    struct PlaySpot {
        const char* name;
        Vec2 grid;
    };
    static constexpr PlaySpot kForum{"forum", {80, 1077}};
    static constexpr PlaySpot kCountry{"country", {170, 880}};
    // The pointer a zoom keeps in place: off-centre, as a player's is.
    const Vec2 pointer{screen().x * 0.3f, screen().y * 0.62f};
    mouse_ = pointer;
    mouseInside_ = true;
    // Zoom sweeps: out to the widest level and in to the closest, a short rest at each.
    for (int attempt = 0; attempt < 2 && benchWants("zoom sweep"); ++attempt) {
        look(kForum.grid, kDefaultZoomLevel);
        BenchFrames fr;
        for (int sweep = 0; sweep < tuning::kBenchZoomSweeps; ++sweep)
            for (const int level : {1, 0, 1, 2, 3, 4, 3, 2}) {
                camera_.zoomTo(level, pointer, screen());
                int rest = 0;
                while (rest < tuning::kBenchZoomRest && fr.all.size() < 20000) {
                    fr.all.push_back(benchFrame());
                    rest = camera_.settled() ? rest + 1 : 0;
                }
            }
        smooth("zoom sweep", fr, tuning::kPopInFramesAllowed);
        if (judgeCase("zoom sweep", fr, attempt == 1)) break;
    }
    // Fast pans at each scale: across the city and across open country.
    for (const PlaySpot& spot : {kForum, kCountry})
        for (const int level : {2, 1, 0}) {
            char name[48];
            (void)std::snprintf(name, sizeof name, "pan %s %gx", spot.name,
                                static_cast<double>(kZoomLevels[static_cast<std::size_t>(level)]));
            for (int attempt = 0; attempt < 2 && benchWants(name); ++attempt) {
                look(spot.grid, level);
                BenchFrames fr;
                for (int f = 0; f < tuning::kBenchPanFrames; ++f) {
                    // Out along one diagonal and back along the other: new land all the way.
                    const float dir = f < tuning::kBenchPanFrames / 2 ? 1.0f : -1.0f;
                    camera_.dragBy(
                        {-tuning::kBenchWorldPanPx * dir, -tuning::kBenchWorldPanPx * 0.5f},
                        screen());
                    fr.all.push_back(benchFrame());
                }
                smooth(name, fr, tuning::kPopInFramesAllowed);
                if (judgeCase(name, fr, attempt == 1)) break;
            }
        }
    // Travel between every pair of the places a player goes to.
    if (benchWants("travel between")) {
        const world::WorldFile& wf = loaded_->file;
        std::vector<int> places;
        for (const char* id : {"corner", "rome", "athens", "parsa"})
            if (const int r = wf.findRegion(id); r >= 0) places.push_back(r);
        BenchFrames all;
        double worstMs = 0;
        int popFrames = 0;
        const auto go = [&](int to) {
            travelTo(to);
            BenchFrames fr;
            const Uint64 t0 = SDL_GetPerformanceCounter();
            while (travel_.region >= 0 && fr.all.size() < 600) {
                fr.all.push_back(benchFrame());
                // What shows once the veil lifts is seen: the destination must be there by then.
                if (travelFadeIn_ >= 0 &&
                    (fr.all.back().popCells > 0 || fr.all.back().popSprites > 0))
                    ++popFrames;
            }
            const double ms = msBetween(t0, SDL_GetPerformanceCounter());
            worstMs = std::max(worstMs, ms);
            all.all.insert(all.all.end(), fr.all.begin(), fr.all.end());
            return ms;
        };
        for (const int from : places)
            for (const int to : places) {
                if (from == to) continue;
                (void)go(from);
                const double ms = go(to);
                std::printf("bench: travel %s to %s: %.0f ms\n",
                            wf.regions[static_cast<std::size_t>(from)].id.c_str(),
                            wf.regions[static_cast<std::size_t>(to)].id.c_str(), ms);
            }
        std::printf("bench: travel: slowest journey %.0f ms (budget %.0f), %d frames with pop-in "
                    "after the veil began to lift\n",
                    worstMs, tuning::kTravelBudgetMs, popFrames);
        if (judge && (worstMs > tuning::kTravelBudgetMs || popFrames > 0)) {
            std::printf("bench: over budget: travel between places\n");
            over = true;
        }
        (void)judgeCase("travel", all, true);
    }
    // The map opened and closed over a city.
    for (int attempt = 0; attempt < 2 && benchWants("map"); ++attempt) {
        look(kForum.grid, kDefaultZoomLevel);
        BenchFrames fr;
        for (int k = 0; k < 4; ++k) {
            toggleMap();
            for (int f = 0; f < tuning::kBenchMapFrames; ++f) fr.all.push_back(benchFrame());
        }
        smooth("map", fr, tuning::kPopInFramesAllowed);
        if (judgeCase("map", fr, attempt == 1)) break;
    }
    mouseInside_ = false;
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
