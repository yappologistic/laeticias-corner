#include "ui/profiler.hpp"

#include "core/tuning.hpp"
#include "ui/strings.hpp"
#include "ui/theme.hpp"

#include <algorithm>
#include <format>

namespace lc {
namespace {

// An output iterator into a fixed buffer that drops what does not fit.
struct Bounded {
    using difference_type = std::ptrdiff_t;
    char* p;
    char* end;
    Bounded& operator=(char c) {
        if (p != end) *p++ = c;
        return *this;
    }
    Bounded& operator*() { return *this; }
    Bounded& operator++() { return *this; }
    Bounded operator++(int) { return *this; }
};

SDL_FColor withAlpha(SDL_FColor c, float a) {
    return {c.r, c.g, c.b, c.a * a};
}

} // namespace

void Profiler::draw(Painter& p, const PerfRing& ring, Vec2 screen, float s, bool gpuSync) {
    const Font& f = p.font();
    const PerfStats frame = ring.stats(&FrameSample::frameMs);
    const PerfStats cpu = ring.stats(&FrameSample::cpuMs);
    const PerfStats gpu = ring.stats(&FrameSample::gpuMs);
    const PerfStats sim = ring.stats(&FrameSample::simMs);
    const PerfStats cond = ring.stats(&FrameSample::condMs);
    const PerfStats scene = ring.stats(&FrameSample::sceneMs);
    const PerfStats present = ring.stats(&FrameSample::presentMs);
    const PerfStats ui = ring.stats(&FrameSample::uiMs);
    const FrameSample last = ring.size() > 0 ? ring.recent(0) : FrameSample{};
    std::size_t n = 0;
    const auto line = [&](std::string_view fmt, const auto&... args) {
        auto& buf = text_[n];
        Bounded out{buf.data(), buf.data() + buf.size()};
        out = std::vformat_to(out, fmt, std::make_format_args(args...));
        lines_[n] = {buf.data(), static_cast<std::size_t>(out.p - buf.data())};
        ++n;
    };
    const float fps = frame.avg > 0 ? 1000.0f / frame.avg : 0.0f;
    line(strings::kProfFrame, fps, frame.avg, frame.p95, frame.p99, frame.worst);
    line(strings::kProfCpu, cpu.avg, cpu.p99, cpu.worst);
    if (gpuSync && gpu.count > 0)
        line(strings::kProfGpu, gpu.avg, gpu.p99, gpu.worst);
    else
        line(strings::kProfGpuOff);
    line(strings::kProfSim, sim.avg, sim.p99, cond.avg);
    line(strings::kProfScene, scene.avg, ui.avg, present.avg);
    line(strings::kProfAudio, last.audioLoad * 100.0f);
    line(strings::kProfDraw, last.drawCalls, last.spritesDrawn, last.spritesCulled);
    line(strings::kProfActors, last.actorsLive, last.actorsAbstract, last.chunksCached);
    line(strings::kProfMemory, last.textureMiB, last.pageMiB, last.pageBudgetMiB, last.totalMiB);
    line(strings::kProfMissing, last.placeholders, last.missingArt);
    const bool over = frame.p99 > static_cast<float>(tuning::kFrameP99Ms) ||
                      frame.worst > static_cast<float>(tuning::kFrameWorstMs);
    line(over ? strings::kProfOver : strings::kProfWithin, static_cast<float>(tuning::kFrameP99Ms),
         static_cast<float>(tuning::kFrameWorstMs));

    // The panel: a graph of the last frames over the text.
    const float pad = theme::kPanelPad * s;
    const float lh = f.lineHeight(Face::Body);
    float textW = 0;
    for (std::size_t i = 0; i < n; ++i) textW = std::max(textW, f.measure(Face::Body, lines_[i]));
    const float graphH = theme::kProfGraphH * s;
    const float w = std::min(screen.x - 2 * theme::kMargin * s,
                             std::max(textW, theme::kProfGraphW * s) + 2 * pad);
    const float h = 2 * pad + graphH + theme::kGap * s + static_cast<float>(n) * lh;
    const Box b{std::round((screen.x - w) * 0.5f), theme::kProfTop * s, w, h};
    p.glass(b, theme::kPanelRadius * s, 1, theme::kGlassTip);
    p.endGlass();
    const Box g{b.x + pad, b.y + pad, b.w - 2 * pad, graphH};
    p.roundRect(g, 0, theme::kInset, 0);
    // Bars scale so that 25 ms fills the graph; the 120 and 60 FPS lines are drawn over them.
    constexpr float kGraphMs = 25.0f;
    const auto bars = std::min<std::size_t>(ring.size(), static_cast<std::size_t>(g.w / s));
    const float bw = g.w / static_cast<float>(std::max<std::size_t>(bars, 1));
    for (std::size_t i = 0; i < bars; ++i) {
        const float ms = ring.recent(i).frameMs;
        const float bh = std::min(1.0f, ms / kGraphMs) * g.h;
        const SDL_FColor c = ms > static_cast<float>(tuning::kFrameWorstMs) ? theme::kWarn
                             : ms > static_cast<float>(tuning::kFrameP99Ms) ? theme::kGold
                                                                            : theme::kAccent;
        p.roundRect({g.x + g.w - static_cast<float>(i + 1) * bw, g.y + g.h - bh, bw, bh}, 0,
                    withAlpha(c, 0.8f), 0);
    }
    for (const float ms :
         {static_cast<float>(tuning::kFrameP99Ms), static_cast<float>(tuning::kFrameWorstMs)}) {
        const float y = g.y + g.h - ms / kGraphMs * g.h;
        p.roundRect({g.x, std::round(y), g.w, theme::kRim * s}, 0, theme::kInkMuted, 0);
    }
    float y = g.y + g.h + theme::kGap * s;
    for (std::size_t i = 0; i < n; ++i) {
        const SDL_FColor ink = i + 1 == n ? (over ? theme::kWarn : theme::kAccent)
                               : i == 0   ? theme::kInk
                                          : theme::kInkMuted;
        p.text(Face::Body, lines_[i], g.x, y + f.ascent(Face::Body), ink);
        y += lh;
    }
    p.endLayer();
}

void Profiler::drawCard(Painter& p, std::span<const std::string> lines, Vec2 screen, float s,
                        bool pass) {
    const Font& f = p.font();
    const float pad = theme::kPanelPad * s * 1.5f;
    const float lh = f.lineHeight(Face::Body);
    // A tab splits a line into a label and a value, the values lined up in one column.
    float labels = 0;
    for (const std::string& l : lines)
        if (const auto tab = l.find('\t'); tab != std::string::npos)
            labels = std::max(labels, f.measure(Face::Body, std::string_view(l).substr(0, tab)));
    const float col = labels + theme::kGap * s * 2;
    float w = 0;
    for (std::size_t i = 0; i < lines.size(); ++i) {
        const std::string_view l = lines[i];
        const auto tab = l.find('\t');
        w = std::max(w, tab == std::string_view::npos
                            ? f.measure(i == 0 ? Face::Title : Face::Body, l)
                            : col + f.measure(Face::Body, l.substr(tab + 1)));
    }
    w = std::min(w + 2 * pad, screen.x - 2 * theme::kMargin * s);
    const float h =
        2 * pad + f.lineHeight(Face::Title) + lh * 0.5f + static_cast<float>(lines.size() - 1) * lh;
    const Box b{std::round((screen.x - w) * 0.5f), std::round((screen.y - h) * 0.5f), w, h};
    p.glass(b, theme::kPanelRadius * s, 1, theme::kGlass);
    p.endGlass();
    float y = b.y + pad;
    for (std::size_t i = 0; i < lines.size(); ++i) {
        const std::string_view l = lines[i];
        if (i == 0) {
            p.text(Face::Title, l, b.x + pad, y + f.ascent(Face::Title), theme::kInk);
            y += f.lineHeight(Face::Title) + lh * 0.5f;
            continue;
        }
        const SDL_FColor ink = i == 1 ? (pass ? theme::kAccent : theme::kWarn)
                                      : (i + 1 == lines.size() ? theme::kInk : theme::kInkMuted);
        const auto tab = l.find('\t');
        const float base = y + f.ascent(Face::Body);
        if (tab == std::string_view::npos) {
            p.text(Face::Body, l, b.x + pad, base, ink);
        } else {
            p.text(Face::Body, l.substr(0, tab), b.x + pad, base, ink);
            p.text(Face::Body, l.substr(tab + 1), b.x + pad + col, base, theme::kInk);
        }
        y += lh;
    }
    p.endLayer();
}

} // namespace lc
