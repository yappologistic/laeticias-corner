// The benchmark: a map of any size, densely built around the camera and sparse elsewhere, run at
// night in the rain with the interface open so every pass is busy; reports update and draw times
// (average, 95th percentile, worst) at the working zoom and the overview, plus memory.

#include "app/app_impl.hpp"

#include <algorithm>
#include <cstdio>
#include <fstream>
#include <string>

namespace lc {
namespace {

constexpr int kNearSide = 96;      // tiles of dense building around the map centre
constexpr float kFarShare = 0.05f; // density elsewhere, relative to near
constexpr int kLakeSide = 12;
constexpr int kWarmup = 30;
constexpr float kPanPxPerFrame = 6.0f; // the second half of each phase pans

struct Series {
    std::vector<double> samples;
    void add(double ms) { samples.push_back(ms); }
    [[nodiscard]] double avg() const {
        double s = 0;
        for (const double v : samples) s += v;
        return samples.empty() ? 0 : s / static_cast<double>(samples.size());
    }
    [[nodiscard]] double pct(double p) const {
        if (samples.empty()) return 0;
        std::vector<double> v = samples;
        const auto k = static_cast<std::size_t>(p * static_cast<double>(v.size() - 1));
        std::ranges::nth_element(v, v.begin() + static_cast<std::ptrdiff_t>(k));
        return v[k];
    }
    [[nodiscard]] double max() const {
        return samples.empty() ? 0 : *std::ranges::max_element(samples);
    }
};

// Resident and peak memory of this process in MiB (Linux; 0 elsewhere).
std::pair<double, double> processMemory() {
    std::ifstream in("/proc/self/status");
    double rss = 0;
    double peak = 0;
    for (std::string line; std::getline(in, line);) {
        const auto field = [&](const char* key, double& out) {
            if (line.starts_with(key))
                out = std::stod(line.substr(std::string_view(key).size())) / 1024.0;
        };
        field("VmRSS:", rss);
        field("VmHWM:", peak);
    }
    return {rss, peak};
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

int App::runBench() {
    fillBenchWorld();
    clock_.setPin(ClockPin::Night, true);
    rain_ = true;
    drawerOpen_ = true;
    journalOpen_ = true;
    camera_.setLand(world_.landBounds(), scene_->cliffDepth());
    const auto ms = [](Uint64 a, Uint64 b) {
        return static_cast<double>(b - a) * 1000.0 /
               static_cast<double>(SDL_GetPerformanceFrequency());
    };
    const int frames = opts_.frames > 0 ? opts_.frames : 600;
    std::printf("bench: map %dx%d, %zu items, %dx%d px, %s renderer, density %.2f near\n",
                world_.width(), world_.height(), world_.items().size(), pixelW_, pixelH_,
                SDL_GetRendererName(renderer_.get()), static_cast<double>(opts_.density));
    bool over = false;
    for (const int level : {kDefaultZoomLevel, kDefaultZoomLevel - 1}) {
        // Centre the camera on the built-up middle at this level.
        const Vec2 mid = cat_.iso().toWorld(static_cast<float>(world_.width()) * 0.5f,
                                            static_cast<float>(world_.height()) * 0.5f);
        const Vec2 here = camera_.worldToScreen(mid, screen());
        camera_.dragBy({screen().x * 0.5f - here.x, screen().y * 0.5f - here.y}, screen());
        camera_.zoomTo(level, {screen().x * 0.5f, screen().y * 0.5f}, screen());
        for (int i = 0; i < 120 && !camera_.settled(); ++i)
            camera_.update(static_cast<float>(tuning::kStepSeconds), screen());
        visitors_.populate(world_, cat_, night(), rng_, activeArea());
        Series upd;
        Series drw;
        Series pan;
        int calls = 0;
        int slots = 0;
        for (int f = 0; f < kWarmup + frames; ++f) {
            const bool panning = f >= kWarmup + frames / 2;
            if (panning) camera_.dragBy({kPanPxPerFrame, kPanPxPerFrame * 0.5f}, screen());
            const Uint64 t0 = SDL_GetPerformanceCounter();
            step(static_cast<float>(tuning::kStepSeconds));
            hud_.update({}, model(), font_, screen(), uiScale_,
                        static_cast<float>(tuning::kStepSeconds));
            const Uint64 t1 = SDL_GetPerformanceCounter();
            render();
            const Uint64 t2 = SDL_GetPerformanceCounter();
            calls = scene_->drawCalls() + blur_->drawCalls() + uiBatch_->drawCalls();
            uiBatch_->resetStats();
            if (!SDL_RenderPresent(renderer_.get())) SDL_Log("present: %s", SDL_GetError());
            if (f < kWarmup) continue;
            slots += scene_->stats().groundSlotsRendered;
            upd.add(ms(t0, t1));
            drw.add(ms(t1, t2));
            if (panning) pan.add(ms(t0, t2));
        }
        const SceneStats st = scene_->stats();
        const auto [rss, peak] = processMemory();
        const double total = upd.avg() + drw.avg();
        std::printf("bench: zoom %g: %zu critters, %zu items in region, %zu drawn, %d draw calls, "
                    "%d ground chunks redrawn\n",
                    static_cast<double>(camera_.zoom()), visitors_.critters().size(),
                    st.regionItems, st.drawnItems, calls, slots);
        std::printf("bench: zoom %g: update avg %.3f p95 %.3f max %.3f ms\n",
                    static_cast<double>(camera_.zoom()), upd.avg(), upd.pct(0.95), upd.max());
        std::printf("bench: zoom %g: draw   avg %.3f p95 %.3f max %.3f ms\n",
                    static_cast<double>(camera_.zoom()), drw.avg(), drw.pct(0.95), drw.max());
        std::printf("bench: zoom %g: total  avg %.3f ms (panning avg %.3f p95 %.3f ms)\n",
                    static_cast<double>(camera_.zoom()), total, pan.avg(), pan.pct(0.95));
        std::printf("bench: zoom %g: memory rss %.0f MiB, peak %.0f MiB; textures: atlas %.0f, "
                    "targets %.0f, ground cache %.0f MiB\n",
                    static_cast<double>(camera_.zoom()), rss, peak,
                    static_cast<double>(atlas_->textureBytes()) / 1048576.0,
                    static_cast<double>(st.targetBytes) / 1048576.0,
                    static_cast<double>(st.groundBytes) / 1048576.0);
        if (opts_.budgetMs > 0 && total > opts_.budgetMs) {
            std::printf("bench: zoom %g is over the %.2f ms budget\n",
                        static_cast<double>(camera_.zoom()), opts_.budgetMs);
            over = true;
        }
    }
    return over ? kExitOverBudget : 0;
}

} // namespace lc
