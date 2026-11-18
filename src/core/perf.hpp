#pragma once
// Frame timings and counters for the profiler overlay, --perf-log and the benchmarks: the last
// few seconds of frames in a fixed ring, with statistics computed without allocating, and the
// budgets a frame is held to (CLAUDE.md, Performance). Pure logic: the app measures, this keeps.

#include <array>
#include <cstddef>
#include <cstdint>
#include <span>

namespace lc {

// One frame. Times in milliseconds; a time that was not measured is negative.
struct FrameSample {
    float frameMs = 0;   // start of this frame to the start of the next: the whole frame
    float cpuMs = 0;     // simulation, interface and draw submission on the main thread
    float gpuMs = -1;    // until the GPU had finished the frame (only when synchronised)
    float presentMs = 0; // inside the present call (submission to the driver, vsync waits)
    float simMs = 0;     // actors, weather, events, conditions and the rest of a step
    float condMs = 0;    // the progress loop's conditions alone
    float sceneMs = 0;   // building and queuing the world's draws
    float uiMs = 0;      // interface layout, input and drawing
    float audioLoad = 0; // share of the audio callback's time budget spent mixing, 0..1
    int steps = 0;       // simulation steps this frame
    int drawCalls = 0;
    int spritesDrawn = 0;
    int spritesCulled = 0;
    int actorsLive = 0;
    int actorsAbstract = 0;
    int chunksCached = 0;
    float textureMiB = 0;
    float totalMiB = 0;
    int placeholders = 0; // sprites drawn as placeholders this frame (art still to come)
    int missingArt = 0;   // ids in the world with no art at all
};

struct PerfStats {
    float avg = 0;
    float p95 = 0;
    float p99 = 0;
    float worst = 0;
    int count = 0;
};

// Statistics of `values` (reordered in place). Percentiles are nearest-rank.
[[nodiscard]] PerfStats perfStats(std::span<float> values);

class PerfRing {
public:
    static constexpr std::size_t kCapacity = 512; // about four seconds at 120 FPS

    void push(const FrameSample& s);
    void clear() { count_ = 0; }
    [[nodiscard]] std::size_t size() const { return count_; }
    // The i-th most recent frame (0: the last one).
    [[nodiscard]] const FrameSample& recent(std::size_t i) const;
    // Statistics of one field over the last `window` frames (all kept when 0).
    [[nodiscard]] PerfStats stats(float FrameSample::* field, std::size_t window = 0) const;

private:
    std::array<FrameSample, kCapacity> ring_{};
    std::size_t head_ = 0; // next slot to write
    std::size_t count_ = 0;
    mutable std::array<float, kCapacity> scratch_{};
};

// The CSV columns of --perf-log, in FrameSample order, and one frame as a line (no newline
// allocation: written into `out`, which must hold kPerfLineMax characters). Returns its length.
inline constexpr const char* kPerfHeader =
    "frame,frame_ms,cpu_ms,gpu_ms,present_ms,sim_ms,cond_ms,scene_ms,ui_ms,audio_load,steps,"
    "draw_calls,sprites_drawn,sprites_culled,actors_live,actors_abstract,chunks_cached,"
    "texture_mib,total_mib";
inline constexpr std::size_t kPerfLineMax = 256;
std::size_t perfLine(std::int64_t frame, const FrameSample& s, std::span<char> out);

} // namespace lc
