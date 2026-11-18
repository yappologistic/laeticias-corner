#include "core/perf.hpp"

#include "core/tuning.hpp"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <format>

namespace lc {

PerfStats perfStats(std::span<float> values) {
    PerfStats s;
    s.count = static_cast<int>(values.size());
    if (values.empty()) return s;
    double sum = 0;
    for (const float v : values) sum += v;
    s.avg = static_cast<float>(sum / static_cast<double>(values.size()));
    const auto rank = [&](float p) {
        // Nearest rank: the smallest value with at least p of the samples at or below it.
        const auto k = static_cast<std::size_t>(
            std::max(0.0f, std::ceil(p * static_cast<float>(values.size())) - 1.0f));
        std::ranges::nth_element(values, values.begin() + static_cast<std::ptrdiff_t>(k));
        return values[k];
    };
    s.p95 = rank(0.95f);
    s.p99 = rank(0.99f);
    s.worst = *std::ranges::max_element(values);
    return s;
}

void PerfRing::push(const FrameSample& s) {
    ring_[head_] = s;
    head_ = (head_ + 1) % kCapacity;
    count_ = std::min(count_ + 1, kCapacity);
}

const FrameSample& PerfRing::recent(std::size_t i) const {
    return ring_[(head_ + kCapacity - 1 - i % kCapacity) % kCapacity];
}

PerfStats PerfRing::stats(float FrameSample::* field, std::size_t window) const {
    const std::size_t n = window == 0 ? count_ : std::min(window, count_);
    std::size_t k = 0;
    for (std::size_t i = 0; i < n; ++i) {
        const float v = recent(i).*field;
        if (v >= 0) scratch_[k++] = v; // unmeasured frames do not count
    }
    return perfStats(std::span<float>(scratch_.data(), k));
}

std::size_t perfLine(std::int64_t frame, const FrameSample& s, std::span<char> out) {
    const auto r = std::format_to_n(
        out.data(), static_cast<std::ptrdiff_t>(out.size()),
        "{},{:.3f},{:.3f},{:.3f},{:.3f},{:.3f},{:.3f},{:.3f},{:.3f},{:.3f},{},{},{},{},{},{},{},"
        "{:.1f},{:.1f},{:.3f},{:.3f},{},{},{},{:.4f},{},{:.3f},{:.3f},{:.3f},{},{:.0f},{:.3f},{},"
        "{:.3f},{}",
        frame, s.frameMs, s.cpuMs, s.gpuMs, s.presentMs, s.simMs, s.condMs, s.sceneMs, s.uiMs,
        s.audioLoad, s.steps, s.drawCalls, s.spritesDrawn, s.spritesCulled, s.actorsLive,
        s.actorsAbstract, s.chunksCached, s.textureMiB, s.totalMiB, s.cityMs, s.crowdMs, s.cityLive,
        s.cityDrawn, s.popCells, s.popShare, s.popSprites, s.buildMs, s.uploadMs, s.gatherMs,
        s.cellsBuilt, s.uploadKiB, s.threadMs, s.allocs, s.instrM,
        s.frameMs > static_cast<float>(tuning::kFrameP99Ms) ? hitchName(hitchCause(s)) : "");
    return std::min(static_cast<std::size_t>(r.size), out.size());
}

const char* partName(Part p) {
    static constexpr std::array<const char*, kFrameParts> kNames{
        "weather", "actors", "home life", "city",  "progress", "effects", "step rest",
        "world",   "model",  "ui update", "scene", "blur",     "ui draw"};
    return kNames[static_cast<std::size_t>(p)];
}

const char* hitchName(HitchCause c) {
    static constexpr std::array<const char*, static_cast<std::size_t>(HitchCause::Count)> kNames{
        "simulation", "interface", "cell build", "page upload", "gather",
        "scene",      "gpu",       "present",    "waiting"};
    return kNames[static_cast<std::size_t>(c)];
}

HitchCause hitchCause(const FrameSample& s) {
    std::array<float, static_cast<std::size_t>(HitchCause::Count)> share{};
    const auto at = [&](HitchCause c) -> float& { return share[static_cast<std::size_t>(c)]; };
    at(HitchCause::Simulation) = s.simMs;
    at(HitchCause::Interface) = s.uiMs;
    at(HitchCause::CellBuild) = s.buildMs;
    at(HitchCause::PageUpload) = s.uploadMs;
    at(HitchCause::Gather) = s.gatherMs;
    at(HitchCause::Scene) = std::max(0.0f, s.sceneMs - s.buildMs - s.uploadMs - s.gatherMs);
    at(HitchCause::Gpu) = s.gpuMs >= 0 ? std::max(0.0f, s.gpuMs - s.cpuMs) : 0.0f;
    at(HitchCause::Present) = s.presentMs;
    // Wall time before submission that the thread did not spend running.
    at(HitchCause::Waiting) = s.threadMs >= 0 ? std::max(0.0f, s.cpuMs - s.threadMs) : 0.0f;
    // A thread kept waiting inside a system shows in that system's wall time too: what it
    // waited is taken out of the largest share, so a descheduled frame is not blamed on it.
    const auto top = std::ranges::max_element(share.begin(), share.end() - 1);
    *top = std::max(0.0f, *top - at(HitchCause::Waiting));
    return static_cast<HitchCause>(std::ranges::max_element(share) - share.begin());
}

void HitchLog::add(const FrameSample& s) {
    ++frames;
    std::size_t b = 0;
    while (b < kEdges.size() && s.frameMs > kEdges[b]) ++b;
    ++buckets[b];
    if (s.frameMs <= static_cast<float>(tuning::kFrameP99Ms)) return;
    auto& by = s.frameMs > static_cast<float>(tuning::kFrameWorstMs) ? over16 : over8;
    ++by[static_cast<std::size_t>(hitchCause(s))];
}

int HitchLog::slow() const {
    return buckets[3] + buckets[4] + buckets[5];
}

int HitchLog::frozen() const {
    return buckets[4] + buckets[5];
}

std::size_t HitchLog::line(std::span<char> out) const {
    std::size_t n = 0;
    const auto put = [&](const char* fmt, const auto&... args) {
        if (n >= out.size()) return;
        const int r = std::snprintf(out.data() + n, out.size() - n, fmt, args...);
        n = r < 0 ? out.size() : std::min(out.size(), n + static_cast<std::size_t>(r));
    };
    put("%d frames: <=2 ms %d, <=4 %d, <=8.3 %d, <=16.6 %d, <=33.3 %d, over %d", frames, buckets[0],
        buckets[1], buckets[2], buckets[3], buckets[4], buckets[5]);
    for (const auto* by : {&over8, &over16}) {
        bool any = false;
        for (std::size_t c = 0; c < by->size(); ++c) {
            if ((*by)[c] == 0) continue;
            put("%s%d %s", any ? ", " : (by == &over8 ? "; over 8.3 ms: " : "; over 16.6 ms: "),
                (*by)[c], hitchName(static_cast<HitchCause>(c)));
            any = true;
        }
    }
    return std::min(n, out.size() - 1);
}

} // namespace lc
