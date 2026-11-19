// The renderer and the Look (graphics plan §3.2, task E1): SDL's gpu driver when the Look asks
// for more than Classic, with the fallback chain gpu -> SDL's choice (interactive) or software
// (headless), one line logged when it falls back.

#include "app/app_impl.hpp"
#include "render/gpu/post.hpp"

#include <array>

namespace lc {

gpu::Quality App::wantedQuality() const {
    if (!opts_.quality.empty())
        return gpu::parseQuality(opts_.quality).value_or(gpu::Quality::Classic);
    // Headless runs keep today's frame unless asked (reproducible screenshots everywhere).
    if (opts_.headless) return gpu::Quality::Classic;
    Profile p;
    if (auto text = readTextFile(saveDir_ / kProfileFile)) p = parseProfile(*text);
    return gpu::parseQuality(p.look).value_or(gpu::Quality::High);
}

bool App::createRenderer() {
    // Headless runs default to the software renderer so screenshots are reproducible anywhere.
    std::string driver =
        !opts_.renderer.empty() ? opts_.renderer : (opts_.headless ? "software" : "");
    if (driver == "gpu" || (driver.empty() && wantedQuality() != gpu::Quality::Classic)) {
        // The offscreen renderer has no window (the offscreen video driver's Vulkan has no
        // surface): it draws into a target the window's size, which stands in for it.
        renderer_ = gpu::createRenderer(opts_.headless ? nullptr : window_.get());
        if (renderer_ && opts_.headless) {
            int w = 0;
            int h = 0;
            if (!SDL_GetWindowSizeInPixels(window_.get(), &w, &h)) SDL_Log("%s", SDL_GetError());
            screen_.reset(SDL_CreateTexture(renderer_.get(), SDL_PIXELFORMAT_ABGR8888,
                                            SDL_TEXTUREACCESS_TARGET, std::max(w, 1),
                                            std::max(h, 1)));
            if (!screen_ || !SDL_SetRenderTarget(renderer_.get(), screen_.get())) {
                SDL_Log("cannot create the offscreen frame: %s", SDL_GetError());
                screen_.reset();
                renderer_.reset();
            }
        }
        if (renderer_) return true;
        SDL_Log("look: no gpu renderer (%s): the classic look", SDL_GetError());
        lookFellBack_ = true; // the settings say so instead of promising the next start
        driver = opts_.headless ? "software" : "";
    }
    renderer_.reset(SDL_CreateRenderer(window_.get(), driver.empty() ? nullptr : driver.c_str()));
    if (!renderer_) {
        SDL_Log("cannot create renderer: %s", SDL_GetError());
        return false;
    }
    return true;
}

} // namespace lc

namespace lc {

bool App::benchLook(const std::function<bool(const char*, const BenchFrames&, bool)>& judgeCase,
                    const std::function<void()>& warm, int frames) {
    if (!worldView_ || !city_ || !gpu::isGpu(renderer_.get())) return true;
    // A dense city view (Rome at its busiest, crowds and the sketchbook open) and a lit night
    // (the Agora at 22:00, the plan's G7), each tier switched live on the same renderer.
    const gpu::Quality was = worldView_->quality();
    const int season = cat_.findSeason("spring").value_or(0);
    const life::Busiest busy = life::busiestView(*city_, "rome", 9, season);
    struct LookSpot {
        const char* name;
        Vec2 grid;
        double hour;
    };
    const LookSpot spots[] = {
        {"rome busiest",
         {static_cast<float>(busy.focus.x) + 0.5f, static_cast<float>(busy.focus.y) + 0.5f},
         busy.hour},
        {"agora 22:00", {262, 672}, 22.0}};
    seasonPin_ = season;
    clock_.setDay(9);
    clock_.setPin(ClockPin::Auto, true);
    // The tiers alternate in short rounds on the same view, so a busy machine's drift falls on
    // all of them alike; each tier's frames from every round are judged together.
    constexpr int kRounds = 6;
    constexpr int kSwitchFrames = 30;
    const int per = std::max(1, frames / kRounds);
    for (const LookSpot& s : spots) {
        clock_.setTime((s.hour - 6.0) / 24.0 + (s.hour < 6.0 ? 1.0 : 0.0));
        camera_.place(gridToHome(s.grid), kZoomLevels[kDefaultZoomLevel], screen());
        camera_.beginStep();
        worldView_->jumped(
            {camera_.position().x + homeOffset_.x, camera_.position().y + homeOffset_.y});
        for (int i = 0; i < tuning::kBenchSettleFrames && !worldView_->settled(); ++i)
            (void)benchFrame();
        warm();
        std::array<BenchFrames, gpu::kQualityCount> fr;
        std::array<worldview::FrameStats, gpu::kQualityCount> st{};
        for (int round = 0; round < kRounds; ++round)
            for (int t = 0; t < gpu::kQualityCount; ++t) {
                const auto q = static_cast<gpu::Quality>(t);
                if (worldView_->setQuality(q) != q) continue;
                // The switch's frames (from Classic the whole path is made and the water cells,
                // still on this path and stepped on Classic, are built again) are not the tier's.
                for (int f = 0; f < kSwitchFrames; ++f) (void)benchFrame();
                for (int f = 0; f < per; ++f)
                    fr[static_cast<std::size_t>(t)].all.push_back(benchFrame());
                st[static_cast<std::size_t>(t)] = worldView_->stats();
            }
        for (int t = 0; t < gpu::kQualityCount; ++t) {
            const auto ti = static_cast<std::size_t>(t);
            if (fr[ti].all.empty()) continue;
            char name[64];
            (void)std::snprintf(name, sizeof name, "look %s: %s",
                                std::string(gpu::qualityId(static_cast<gpu::Quality>(t))).c_str(),
                                s.name);
            std::printf(
                "bench: %s: world draw calls %d, targets %.1f MiB, world textures %.0f MiB\n", name,
                st[ti].drawCalls, static_cast<double>(st[ti].targetBytes) / 1048576.0,
                static_cast<double>(st[ti].textureBytes()) / 1048576.0);
            (void)judgeCase(name, fr[ti], true);
        }
    }
    // In motion: a fast pan over new land (out along one diagonal, back along the other), the
    // tiers taking turns along it in short stretches, so each meets fresh cells and the same
    // drift of the machine's load.
    struct PanSpot {
        const char* name;
        Vec2 grid;
        int level;
    };
    const PanSpot pans[] = {{"pan forum 1x", {80, 1077}, 2}, {"pan country 0.25x", {170, 880}, 0}};
    clock_.setTime((11.0 - 6.0) / 24.0);
    for (const PanSpot& p : pans) {
        camera_.place(gridToHome(p.grid), kZoomLevels[static_cast<std::size_t>(p.level)], screen());
        camera_.beginStep();
        worldView_->jumped(
            {camera_.position().x + homeOffset_.x, camera_.position().y + homeOffset_.y});
        for (int i = 0; i < tuning::kBenchSettleFrames && !worldView_->settled(); ++i)
            (void)benchFrame();
        warm();
        std::array<BenchFrames, gpu::kQualityCount> fr;
        constexpr int kStretches = 4 * kRounds;
        const int stretch = std::max(1, tuning::kBenchPanFrames / kRounds);
        for (int k = 0; k < kStretches; ++k) {
            const int t = (k + k / gpu::kQualityCount) % gpu::kQualityCount; // order rotates
            const auto q = static_cast<gpu::Quality>(t);
            if (worldView_->setQuality(q) != q) continue;
            const float dir = k < kStretches / 2 ? 1.0f : -1.0f;
            for (int f = 0; f < kSwitchFrames + stretch; ++f) {
                camera_.dragBy({-tuning::kBenchWorldPanPx * dir, -tuning::kBenchWorldPanPx * 0.5f},
                               screen());
                const FrameSample b = benchFrame();
                if (f >= kSwitchFrames) fr[static_cast<std::size_t>(t)].all.push_back(b);
            }
        }
        for (int t = 0; t < gpu::kQualityCount; ++t) {
            const auto ti = static_cast<std::size_t>(t);
            if (fr[ti].all.empty()) continue;
            char name[64];
            (void)std::snprintf(name, sizeof name, "look %s: %s",
                                std::string(gpu::qualityId(static_cast<gpu::Quality>(t))).c_str(),
                                p.name);
            (void)judgeCase(name, fr[ti], true);
        }
    }
    seasonPin_ = -1;
    clock_.setPin(ClockPin::Day, true);
    return worldView_->setQuality(was) == was;
}

} // namespace lc
