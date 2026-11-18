#pragma once
// Frame timings and counters for the profiler overlay, --perf-log and the benchmarks: the last
// few seconds of frames in a fixed ring, with statistics computed without allocating, and the
// budgets a frame is held to (CLAUDE.md, Performance). Pure logic: the app measures, this keeps.

#include <array>
#include <cstddef>
#include <cstdint>
#include <span>

namespace lc {

// The parts of a frame's work on the main thread that are timed one by one, so that where the
// time goes is read, not guessed (the bench prints them per case).
enum class Part : std::uint8_t {
    Weather,  // the weather, at home and over the world
    Actors,   // the home's actors
    HomeLife, // events, speech and the rest of the home's life
    City,     // city life's step
    Progress, // conditions, wishes, nooks
    Effects,  // the home scene's particles and sway
    StepRest, // the rest of a step (camera, clock, growth, autosave)
    World,    // places, journeys, journal (once a frame)
    Model,    // building the interface's model
    UiUpdate, // interface layout and input
    Scene,    // the world's and the home's draw submission
    Blur,     // the blurred copy behind the glass
    UiDraw,   // interface drawing
    Count
};
inline constexpr std::size_t kFrameParts = static_cast<std::size_t>(Part::Count);
[[nodiscard]] const char* partName(Part p);

// One frame. Times in milliseconds; a time that was not measured is negative.
struct FrameSample {
    std::array<float, kFrameParts> part{};               // by Part
    std::array<std::uint16_t, kFrameParts> partAllocs{}; // heap allocations inside the timed parts
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
    float pageMiB = 0; // the world's atlas pages resident, and what they may hold
    float pageBudgetMiB = 0;
    int placeholders = 0; // sprites drawn as placeholders this frame (art still to come)
    int missingArt = 0;   // ids in the world with no art at all
    float cityMs = 0;     // city life's simulation in this frame's steps (src/life/)
    float crowdMs = 0;    // gathering, resolving and ordering its actors for drawing
    int cityLive = 0;     // its live actors
    int cityDrawn = 0;    // of them, drawn this frame
    // What the player would see arrive late (pop-in), this frame.
    int popCells = 0;   // cells in view shown from a coarser level, or not at all
    float popShare = 0; // the share of the view they cover, 0..1
    int popSprites = 0; // sprites left out: their page was still streaming, or not gathered
    // Cache work on the main thread, this frame.
    float buildMs = 0;   // drawing ground cells and impostor blocks
    float uploadMs = 0;  // uploading atlas page slices
    float gatherMs = 0;  // gathering a region at once (nothing was gathered there yet)
    int cellsBuilt = 0;  // ground cells and impostor blocks drawn
    float uploadKiB = 0; // page pixels uploaded
    // Where the main thread's wall time went besides running: waiting (blocked on a file, a
    // lock or the driver, or taken off its core by the scheduler) before the frame was submitted.
    float updateMs = 0;  // the frame's start to the start of drawing (steps, interface update)
    float threadMs = -1; // CPU time the main thread used for update and draw submission
    int allocs = -1;     // heap allocations the main thread made this frame (-1: not counted)
    // Millions of instructions the main thread ran in user mode for update and draw submission
    // (-1: not counted). The load on the machine does not move it.
    float instrM = -1;
};

// Why a frame was slow: the system that took the largest share of it.
enum class HitchCause : std::uint8_t {
    Simulation, // the fixed steps (actors, city life, conditions)
    Interface,  // interface update and drawing
    CellBuild,  // ground cells and impostor blocks drawn into the cache
    PageUpload, // atlas page slices uploaded
    Gather,     // a region gathered on the main thread
    Scene,      // the rest of the world's draw submission
    Gpu,        // waiting for the GPU to finish the frame
    Present,    // inside the present call
    Waiting,    // the main thread was not running (blocked, or the scheduler's)
    Count
};
[[nodiscard]] const char* hitchName(HitchCause c);
// The largest share of `s` (every share is measured; what none explains is Waiting).
[[nodiscard]] HitchCause hitchCause(const FrameSample& s);

// Frame times of a run as a histogram, with every frame over a budget counted by its cause.
struct HitchLog {
    // Upper bounds of the buckets in ms; the last bucket is everything above.
    static constexpr std::array<float, 5> kEdges{2.0f, 4.0f, 8.3f, 16.6f, 33.3f};
    std::array<int, kEdges.size() + 1> buckets{};
    std::array<int, static_cast<std::size_t>(HitchCause::Count)> over8{};  // 8.3 < t <= 16.6
    std::array<int, static_cast<std::size_t>(HitchCause::Count)> over16{}; // t > 16.6
    int frames = 0;
    void add(const FrameSample& s);
    [[nodiscard]] int slow() const;   // frames over 8.3 ms
    [[nodiscard]] int frozen() const; // frames over 16.6 ms
    // One line into `out` (cut short if it does not fit): the histogram and the causes.
    std::size_t line(std::span<char> out) const;
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
    "texture_mib,total_mib,city_ms,crowd_ms,city_live,city_drawn,pop_cells,pop_share,"
    "pop_sprites,build_ms,upload_ms,gather_ms,cells_built,upload_kib,thread_ms,allocs,instr_m,"
    "cause";
inline constexpr std::size_t kPerfLineMax = 384;
std::size_t perfLine(std::int64_t frame, const FrameSample& s, std::span<char> out);

} // namespace lc
