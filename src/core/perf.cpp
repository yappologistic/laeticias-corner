#include "core/perf.hpp"

#include <algorithm>
#include <cmath>
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
        "{:.1f},{:.1f},{:.3f},{:.3f},{},{}",
        frame, s.frameMs, s.cpuMs, s.gpuMs, s.presentMs, s.simMs, s.condMs, s.sceneMs, s.uiMs,
        s.audioLoad, s.steps, s.drawCalls, s.spritesDrawn, s.spritesCulled, s.actorsLive,
        s.actorsAbstract, s.chunksCached, s.textureMiB, s.totalMiB, s.cityMs, s.crowdMs, s.cityLive,
        s.cityDrawn);
    return std::min(static_cast<std::size_t>(r.size), out.size());
}

} // namespace lc
