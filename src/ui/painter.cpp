#include "ui/painter.hpp"

#include <algorithm>
#include <array>
#include <cmath>
#include <numbers>

namespace lc {
namespace {
constexpr int kArcSegments = 10;
constexpr int kRim = 4 * (kArcSegments + 1);
} // namespace

void Painter::roundRect(Box b, float radius, SDL_FColor color, float feather) {
    if (b.w <= 0 || b.h <= 0 || color.a <= 0) return;
    radius = std::clamp(radius, 0.0f, std::min(b.w, b.h) * 0.5f);
    // Inset by half the feather so the visible edge stays where the box says.
    const float inset = std::min(feather * 0.5f, radius);
    const float r = std::max(0.0f, radius - inset);
    const Box in{b.x + inset, b.y + inset, b.w - 2 * inset, b.h - 2 * inset};
    const UvRect uv = font_.whiteUv();
    const SDL_FPoint t{(uv.u0 + uv.u1) * 0.5f, (uv.v0 + uv.v1) * 0.5f};
    SDL_FColor clear = color;
    clear.a = 0;

    std::array<SDL_Vertex, 1 + 2 * kRim> v;
    v[0] = {{in.cx(), in.cy()}, color, t};
    const SDL_FPoint centres[4] = {{in.x + in.w - r, in.y + r},
                                   {in.x + in.w - r, in.y + in.h - r},
                                   {in.x + r, in.y + in.h - r},
                                   {in.x + r, in.y + r}};
    int k = 0;
    for (int c = 0; c < 4; ++c) {
        for (int s = 0; s <= kArcSegments; ++s) {
            const float a = (static_cast<float>(c) - 1.0f + static_cast<float>(s) / kArcSegments) *
                            std::numbers::pi_v<float> * 0.5f;
            const float nx = std::cos(a);
            const float ny = std::sin(a);
            const SDL_FPoint p{centres[c].x + nx * r, centres[c].y + ny * r};
            v[static_cast<std::size_t>(1 + k)] = {p, color, t};
            v[static_cast<std::size_t>(1 + kRim + k)] = {
                {p.x + nx * feather, p.y + ny * feather}, clear, t};
            ++k;
        }
    }
    std::array<int, kRim * 9> idx;
    std::size_t n = 0;
    for (int i = 0; i < kRim; ++i) {
        const int a = 1 + i;
        const int b2 = 1 + (i + 1) % kRim;
        idx[n++] = 0;
        idx[n++] = a;
        idx[n++] = b2;
        // Feather quad between the solid rim and the transparent outer rim.
        idx[n++] = a;
        idx[n++] = a + kRim;
        idx[n++] = b2 + kRim;
        idx[n++] = a;
        idx[n++] = b2 + kRim;
        idx[n++] = b2;
    }
    batch_.use(font_.texture(), SDL_BLENDMODE_BLEND);
    batch_.triangles(v.data(), static_cast<int>(v.size()), idx.data(), static_cast<int>(n));
}

void Painter::text(Face face, std::string_view s, float x, float baseline, SDL_FColor color) {
    font_.draw(batch_, face, s, x, baseline, color);
}

float Painter::wrapped(Face face, std::string_view s, float x, float top, float width, int maxLines,
                       SDL_FColor color) {
    const float lh = font_.lineHeight(face);
    float y = top + font_.ascent(face);
    int lines = 0;
    std::size_t start = 0;
    while (start < s.size() && lines < maxLines) {
        // Grow the line word by word until it no longer fits.
        std::size_t end = start;
        std::size_t fit = start;
        while (end < s.size()) {
            std::size_t next = s.find(' ', end + 1);
            if (next == std::string_view::npos) next = s.size();
            if (font_.measure(face, s.substr(start, next - start)) > width && fit > start) break;
            fit = next;
            end = next;
        }
        std::string_view line = s.substr(start, fit - start);
        const bool last = lines + 1 == maxLines && fit < s.size();
        if (last) {
            // Truncate the final visible line with an ellipsis.
            while (!line.empty() && font_.measure(face, line) + font_.measure(face, "…") > width)
                line.remove_suffix(1);
            const float w = font_.draw(batch_, face, line, x, y, color);
            font_.draw(batch_, face, "…", x + w, y, color);
        } else {
            font_.draw(batch_, face, line, x, y, color);
        }
        ++lines;
        y += lh;
        start = fit < s.size() ? fit + 1 : fit;
    }
    return static_cast<float>(lines) * lh;
}

void Painter::icon(char32_t cp, float cx, float cy, SDL_FColor color) {
    font_.drawIcon(batch_, cp, cx, cy, color);
}

void Painter::thumbnail(SpriteId id, Box b, float alpha) {
    const Sprite& s = atlas_.sprite(id);
    const float k = std::max(1.0f, std::floor(std::min(b.w / s.w, b.h / s.h)));
    const float w = s.w * k;
    const float h = s.h * k;
    batch_.use(atlas_.texture(), SDL_BLENDMODE_BLEND);
    batch_.quad(SDL_FRect{std::round(b.cx() - w * 0.5f), std::round(b.cy() - h * 0.5f), w, h}, s.uv,
                {1, 1, 1, alpha});
}

} // namespace lc
