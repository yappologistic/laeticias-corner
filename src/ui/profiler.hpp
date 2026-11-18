#pragma once
// The profiler overlay (F3): a frame-time graph with the 120 and 60 FPS lines, the whole frame's
// average, 95th and 99th percentile and worst over the last seconds, per-system times, draw
// calls, sprites, actors, cached chunks and memory. Text is formatted into fixed buffers, so
// drawing it allocates nothing.

#include "core/perf.hpp"
#include "ui/painter.hpp"

#include <array>
#include <span>
#include <string>
#include <string_view>

namespace lc {

class Profiler {
public:
    // Laid out at the top centre of `screen`, under the interface's top band.
    void draw(Painter& p, const PerfRing& ring, Vec2 screen, float scale, bool gpuSync);
    // The benchmark's results: lines of text on a centred card, the verdict line coloured.
    static void drawCard(Painter& p, std::span<const std::string> lines, Vec2 screen, float scale,
                         bool pass);

private:
    static constexpr std::size_t kLines = 10;
    static constexpr std::size_t kLineMax = 96;
    std::array<std::array<char, kLineMax>, kLines> text_{};
    std::array<std::string_view, kLines> lines_{};
};

} // namespace lc
