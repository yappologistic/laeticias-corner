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
    view_ = camera_.moving() ? camera_.interpolated(alpha_) : camera_.snapped(screen());
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
        a.stride -= std::hypot(dx, dy) * (1.0f - alpha_); // the walk cycle between steps too
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

App::FrameMark App::markFrame() {
    return {threadCpuMs(), threadAllocs(), threadInstructions()};
}

void App::closeMark(const FrameMark& m, FrameSample& s) {
    const double now = threadCpuMs();
    s.threadMs = now >= 0 ? static_cast<float>(now - m.threadMs) : -1.0f;
    s.allocs = allocCounting() ? static_cast<int>(threadAllocs() - m.allocs) : -1;
    const std::uint64_t instructions = threadInstructions();
    s.instrM = instructions > 0 ? static_cast<float>(instructions - m.instructions) * 1e-6f : -1.0f;
}

void App::worldSample(FrameSample& s) const {
    if (!worldView_) return;
    const worldview::FrameStats& ws = worldView_->stats();
    s.spritesDrawn += ws.spritesDrawn;
    s.spritesCulled += ws.spritesCulled;
    s.chunksCached += ws.cellsCached;
    s.placeholders = ws.placeholders;
    s.pageMiB = static_cast<float>(static_cast<double>(ws.pages.bytes) / 1048576.0);
    s.pageBudgetMiB = static_cast<float>(static_cast<double>(ws.pages.budget) / 1048576.0);
    s.missingArt = worldView_->missingArt();
    s.crowdMs = static_cast<float>(ws.actorMs);
    s.cityDrawn = ws.actorsDrawn;
    s.cityLive = city_ ? city_->city->liveCount() : 0;
    // A coarser level standing in for the whole view counts as every cell of it arriving late.
    s.popCells = ws.cellsPending + (ws.lodHeld ? 1 : 0);
    s.popShare = ws.lodHeld ? 1.0f : ws.pendingShare;
    s.popSprites = ws.spritesMissing + (ws.regionShort ? 1 : 0);
    s.buildMs = static_cast<float>(ws.buildMs);
    s.uploadMs = static_cast<float>(ws.uploadMs);
    s.gatherMs = static_cast<float>(ws.gatherMs);
    s.cellsBuilt = ws.cellsBuilt + ws.blocksBuilt;
    s.uploadKiB = static_cast<float>(static_cast<double>(ws.uploadBytes) / 1024.0);
}

void App::closeParts(FrameSample& s) {
    // What a step did besides its timed parts.
    const auto at = [&](Part p) -> double& { return partMs_[static_cast<std::size_t>(p)]; };
    at(Part::StepRest) =
        std::max(0.0, stepMs_ - at(Part::Weather) - at(Part::Actors) - at(Part::HomeLife) -
                          at(Part::City) - at(Part::Progress) - at(Part::Effects));
    std::uint64_t counted = 0;
    for (const Part p :
         {Part::Weather, Part::Actors, Part::HomeLife, Part::City, Part::Progress, Part::Effects})
        counted += partAllocs_[static_cast<std::size_t>(p)];
    partAllocs_[static_cast<std::size_t>(Part::StepRest)] =
        stepAllocs_ > counted ? stepAllocs_ - counted : 0;
    stepAllocs_ = 0;
    for (std::size_t i = 0; i < kFrameParts; ++i) {
        s.part[i] = static_cast<float>(partMs_[i]);
        s.partAllocs[i] =
            static_cast<std::uint16_t>(std::min<std::uint64_t>(partAllocs_[i], 65535));
    }
    stepMs_ = 0;
}

void App::recordFrame(FrameSample& s) {
    closeParts(s);
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
    worldSample(s);
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
