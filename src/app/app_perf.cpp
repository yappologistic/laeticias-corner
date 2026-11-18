// Measurement: interpolated drawing between simulation steps, each frame's timings and counters
// into the profiler's ring and the --perf-log CSV, and the optional wait for the GPU that makes
// whole-frame times honest (CLAUDE.md, Performance).

#include "app/app_impl.hpp"

#include <algorithm>
#include <string>

namespace lc {
namespace {

constexpr int kMemoryEvery = 30; // frames between reads of the process's memory
constexpr float kSnapTiles =
    1.5f; // an actor that moved further in one step was placed, not walking

} // namespace

void App::prepareView() {
    view_ = camera_.interpolated(alpha_);
    const auto all = actors_.all();
    drawActors_.assign(all.begin(), all.end());
    if (alpha_ >= 1.0f) return;
    for (std::size_t i = 0; i < drawActors_.size() && i < actorPrev_.size(); ++i) {
        Actor& a = drawActors_[i];
        const Vec2 from = actorPrev_[i];
        const float dx = a.pos.x - from.x;
        const float dy = a.pos.y - from.y;
        if (dx * dx + dy * dy > kSnapTiles * kSnapTiles) continue;
        a.pos = {from.x + dx * alpha_, from.y + dy * alpha_};
    }
}

double App::syncGpu(Uint64 frameStart) {
    // Reading one pixel back makes the renderer submit everything queued and wait until the GPU
    // has drawn it: the frame's time to completion, at the cost of the CPU/GPU overlap.
    const SDL_Rect one{0, 0, 1, 1};
    if (const SurfacePtr px{SDL_RenderReadPixels(renderer_.get(), &one)}; !px)
        SDL_Log("gpu sync: %s", SDL_GetError());
    return msBetween(frameStart, SDL_GetPerformanceCounter());
}

void App::recordFrame(FrameSample& s) {
    s.sceneMs = static_cast<float>(sceneMs_);
    s.audioLoad = mixer_.load();
    s.drawCalls = sceneDrawCalls() + blur_->drawCalls() + uiBatch_->drawCalls();
    uiBatch_->resetStats();
    const SceneStats st = scene_->stats();
    s.spritesDrawn = static_cast<int>(st.drawnItems);
    s.spritesCulled = static_cast<int>(st.regionItems - std::min(st.regionItems, st.drawnItems));
    s.actorsLive = static_cast<int>(std::ranges::count_if(
        actors_.all(), [](const Actor& a) { return (a.flags & actor_flag::kAlive) != 0; }));
    s.actorsAbstract =
        0; // the home region keeps every actor live; abstract tiers come with the world
    s.chunksCached = st.groundChunksCached;
    if (worldView_) {
        // The world's share: its sprites, cells and pages.
        const worldview::FrameStats& ws = worldView_->stats();
        s.spritesDrawn += ws.spritesDrawn;
        s.spritesCulled += ws.spritesCulled;
        s.chunksCached += ws.cellsCached;
        s.placeholders = ws.placeholders;
        s.missingArt = worldView_->missingArt();
    }
    const std::size_t worldBytes = worldView_ ? worldView_->stats().textureBytes() : 0;
    s.textureMiB =
        static_cast<float>(static_cast<double>(atlas_->textureBytes() + st.targetBytes +
                                               st.groundBytes + blur_->bytes() + worldBytes) /
                           1048576.0);
    const FrameSample prev = perf_.size() > 0 ? perf_.recent(0) : FrameSample{};
    s.totalMiB =
        perfFrames_ % kMemoryEvery == 0 ? static_cast<float>(processMemory().first) : prev.totalMiB;
    perf_.push(s);
    if (perfLog_) {
        std::array<char, kPerfLineMax> line{};
        const std::size_t n = perfLine(perfFrames_, s, line);
        (void)std::fwrite(line.data(), 1, n, perfLog_.get());
        (void)std::fputc('\n', perfLog_.get());
    }
    ++perfFrames_;
}

} // namespace lc
