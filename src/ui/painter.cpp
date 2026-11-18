#include "ui/painter.hpp"

#include <algorithm>
#include <cmath>
#include <numbers>

namespace lc {
namespace {
constexpr int kArcSegments = 10;
constexpr int kOutline = 4 * (kArcSegments + 1);
using Loop = std::array<SDL_FPoint, kOutline>;

// Unit directions of the outline's vertices, computed once: outlines are rebuilt many times a
// frame.
const Loop& arcDirections() {
    static const Loop table = [] {
        Loop t{};
        std::size_t k = 0;
        for (int c = 0; c < 4; ++c) {
            for (int s = 0; s <= kArcSegments; ++s) {
                const float a =
                    (static_cast<float>(c) - 1.0f + static_cast<float>(s) / kArcSegments) *
                    std::numbers::pi_v<float> * 0.5f;
                t[k++] = {std::cos(a), std::sin(a)};
            }
        }
        return t;
    }();
    return table;
}

// Outline of a rounded rectangle inset by `d` (negative grows it), clockwise from the top-right
// arc. `r` is the radius before insetting.
void outline(Box b, float r, float d, Loop& out) {
    const float ri = std::max(0.0f, r - d);
    const Box in{b.x + d, b.y + d, b.w - 2 * d, b.h - 2 * d};
    const SDL_FPoint centres[4] = {{in.x + in.w - ri, in.y + ri},
                                   {in.x + in.w - ri, in.y + in.h - ri},
                                   {in.x + ri, in.y + in.h - ri},
                                   {in.x + ri, in.y + ri}};
    const Loop& dir = arcDirections();
    for (std::size_t k = 0; k < out.size(); ++k) {
        const SDL_FPoint c = centres[k / (kArcSegments + 1)];
        out[k] = {c.x + dir[k].x * ri, c.y + dir[k].y * ri};
    }
}

SDL_FColor lerp(SDL_FColor a, SDL_FColor b, float k) {
    return {a.r + (b.r - a.r) * k, a.g + (b.g - a.g) * k, a.b + (b.b - a.b) * k,
            a.a + (b.a - a.a) * k};
}

SDL_FColor scaled(SDL_FColor c, float alpha) {
    return {c.r, c.g, c.b, c.a * alpha};
}

// `top` composited over `under` (straight alpha).
SDL_FColor over(SDL_FColor top, SDL_FColor under) {
    const float a = top.a + under.a * (1 - top.a);
    if (a <= 0) return {0, 0, 0, 0};
    const float k = under.a * (1 - top.a);
    return {(top.r * top.a + under.r * k) / a, (top.g * top.a + under.g * k) / a,
            (top.b * top.a + under.b * k) / a, a};
}

// Vertical shading: the colour at height y of a box shaded from `top` to `bottom`.
struct Shade {
    Box b;
    SDL_FColor top;
    SDL_FColor bottom;
    [[nodiscard]] SDL_FColor at(float y, float alpha = 1.0f) const {
        const float k = b.h > 0 ? std::clamp((y - b.y) / b.h, 0.0f, 1.0f) : 0.0f;
        return scaled(lerp(top, bottom, k), alpha);
    }
};

// Index list joining loop `a` to loop `b` (vertex offsets) with one quad per outline segment.
template <std::size_t N>
std::size_t band(std::array<int, N>& idx, std::size_t n, int a, int b) {
    for (int i = 0; i < kOutline; ++i) {
        const int j = (i + 1) % kOutline;
        idx[n++] = a + i;
        idx[n++] = b + i;
        idx[n++] = b + j;
        idx[n++] = a + i;
        idx[n++] = b + j;
        idx[n++] = a + j;
    }
    return n;
}
} // namespace

void Painter::shape(Box b, float radius, float feather, SDL_FColor top, SDL_FColor bottom,
                    Fill fill) {
    if (b.w <= 0 || b.h <= 0 || (top.a <= 0 && bottom.a <= 0)) return;
    radius = std::clamp(radius, 0.0f, std::min(b.w, b.h) * 0.5f);
    // The solid edge sits half the feather inside the box so the visible edge stays where the box
    // says; the transparent edge half outside.
    const float inset = std::min(feather * 0.5f, radius);
    Loop solid;
    Loop clear;
    outline(b, radius, inset, solid);
    outline(b, radius, inset - feather, clear);

    SDL_Texture* texture = font_.texture();
    const UvRect white = font_.whiteUv();
    const SDL_FPoint whiteUv{(white.u0 + white.u1) * 0.5f, (white.v0 + white.v1) * 0.5f};
    const bool sampled = fill == Fill::Backdrop && backdrop_.texture != nullptr;
    if (sampled) texture = backdrop_.texture;
    const auto uv = [&](SDL_FPoint p) {
        if (!sampled) return whiteUv;
        // Clamped: the feathered rim may poke past the window, where the blur has no data.
        return SDL_FPoint{std::clamp(p.x / backdrop_.screen.x, 0.0f, 1.0f),
                          std::clamp(p.y / backdrop_.screen.y, 0.0f, 1.0f)};
    };
    const Shade shade{b, top, bottom};

    std::array<SDL_Vertex, 1 + 2 * kOutline> v;
    const SDL_FPoint centre{b.cx(), b.cy()};
    v[0] = {centre, shade.at(centre.y), uv(centre)};
    for (std::size_t i = 0; i < kOutline; ++i) {
        v[1 + i] = {solid[i], shade.at(solid[i].y), uv(solid[i])};
        v[1 + kOutline + i] = {clear[i], shade.at(clear[i].y, 0.0f), uv(clear[i])};
    }
    std::array<int, kOutline * 9> idx;
    std::size_t n = 0;
    for (int i = 0; i < kOutline; ++i) {
        idx[n++] = 0;
        idx[n++] = 1 + i;
        idx[n++] = 1 + (i + 1) % kOutline;
    }
    n = band(idx, n, 1, 1 + kOutline);
    batch_.use(texture, SDL_BLENDMODE_BLEND, SDL_SCALEMODE_LINEAR);
    batch_.triangles(v.data(), static_cast<int>(v.size()), idx.data(), static_cast<int>(n));
}

void Painter::roundRect(Box b, float radius, SDL_FColor color, float feather) {
    shape(b, radius, feather, color, color, Fill::Flat);
}

void Painter::gradient(Box b, float radius, SDL_FColor top, SDL_FColor bottom) {
    shape(b, radius, 1.0f, top, bottom, Fill::Flat);
}

void Painter::rim(Box b, float radius, float width, SDL_FColor top, SDL_FColor bottom) {
    if (b.w <= 0 || b.h <= 0 || (top.a <= 0 && bottom.a <= 0)) return;
    radius = std::clamp(radius, 0.0f, std::min(b.w, b.h) * 0.5f);
    // Three outlines, transparent-solid-transparent: an anti-aliased line covering about
    // (width + 1) / 2 px, peaking half its width inside the edge.
    const float d[3] = {-0.5f, width * 0.5f, width + 0.5f};
    const float a[3] = {0, 1, 0};
    const UvRect white = font_.whiteUv();
    const SDL_FPoint t{(white.u0 + white.u1) * 0.5f, (white.v0 + white.v1) * 0.5f};
    const Shade shade{b, top, bottom};
    std::array<SDL_Vertex, 3 * kOutline> v;
    Loop loop;
    for (std::size_t l = 0; l < 3; ++l) {
        outline(b, radius, d[l], loop);
        for (std::size_t i = 0; i < kOutline; ++i)
            v[l * kOutline + i] = {loop[i], shade.at(loop[i].y, a[l]), t};
    }
    std::array<int, kOutline * 12> idx;
    std::size_t n = 0;
    for (int l = 0; l < 2; ++l) n = band(idx, n, l * kOutline, (l + 1) * kOutline);
    batch_.use(font_.texture(), SDL_BLENDMODE_BLEND, SDL_SCALEMODE_LINEAR);
    batch_.triangles(v.data(), static_cast<int>(v.size()), idx.data(), static_cast<int>(n));
}

void Painter::glass(Box b, float radius, float alpha, const theme::Glass& style) {
    if (alpha <= 0 || b.w <= 0 || b.h <= 0) return;
    if (paneCount_ == panes_.size()) endGlass();
    panes_[paneCount_++] = {b, radius, alpha, &style};
}

void Painter::endGlass() {
    const std::span panes(panes_.data(), paneCount_);
    paneCount_ = 0;
    // Pass by pass rather than pane by pane: each pass uses one texture, so a layer of panels
    // costs two texture switches however many panels it has.
    for (const Pane& p : panes) {
        const float soft = p.style->shadowSoftness * scale_;
        roundRect({p.box.x - soft * 0.25f, p.box.y + p.style->shadowDrop * scale_ - soft * 0.25f,
                   p.box.w + soft * 0.5f, p.box.h + soft * 0.5f},
                  p.radius + soft * 0.5f, scaled(p.style->shadow, p.alpha), soft);
    }
    const float bright = std::clamp(backdrop_.brightness, 0.0f, 1.0f);
    for (const Pane& p : panes) {
        if (backdrop_.texture != nullptr) {
            SDL_FColor c = p.style->backdrop;
            const float k = c.r + (theme::kGlassBrightBackdrop - c.r) * bright;
            c = scaled({k, k * c.g / c.r, k * c.b / c.r, c.a}, p.alpha);
            shape(p.box, p.radius, 1.0f, c, c, Fill::Backdrop);
        } else {
            roundRect(p.box, p.radius, scaled(theme::kGlassFallback, p.alpha));
        }
    }
    for (const Pane& p : panes) {
        const theme::Glass& g = *p.style;
        SDL_FColor tint = g.tint;
        tint.a = std::max(tint.a, tint.a + (theme::kGlassBrightTint - tint.a) * bright);
        gradient(p.box, p.radius, scaled(over(g.sheenTop, tint), p.alpha),
                 scaled(over(g.sheenBottom, tint), p.alpha));
        rim(p.box, p.radius, theme::kRim * scale_, scaled(g.rimTop, p.alpha),
            scaled(g.rimBottom, p.alpha));
    }
}

void Painter::text(Face face, std::string_view s, float x, float baseline, SDL_FColor color) {
    font_.draw(batch_, face, s, x, baseline, color);
}

namespace {

// Splits `s` into lines no wider than `width` (a single long word gets a line of its own) and
// calls line(text, isLastShown) for at most maxLines of them.
template <typename F>
int breakLines(const Font& font, Face face, std::string_view s, float width, int maxLines,
               F&& line) {
    int lines = 0;
    std::size_t start = 0;
    while (start < s.size() && lines < maxLines) {
        std::size_t end = start;
        std::size_t fit = start;
        while (end < s.size()) {
            std::size_t next = s.find(' ', end + 1);
            if (next == std::string_view::npos) next = s.size();
            if (font.measure(face, s.substr(start, next - start)) > width && fit > start) break;
            fit = next;
            end = next;
        }
        line(s.substr(start, fit - start), lines + 1 == maxLines && fit < s.size());
        ++lines;
        start = fit < s.size() ? fit + 1 : fit;
    }
    return lines;
}

} // namespace

std::string_view elide(const Font& font, Face face, std::string_view s, float width,
                       std::string& out) {
    if (font.measure(face, s) <= width) return s;
    constexpr std::string_view kEllipsis = "\u2026";
    const float room = width - font.measure(face, kEllipsis);
    // Whole characters only, so a cut never splits a UTF-8 sequence.
    std::size_t keep = 0;
    for (std::size_t i = 0; i < s.size();) {
        std::size_t j = i;
        (void)nextCodepoint(s, j);
        if (font.measure(face, s.substr(0, j)) > room) break;
        keep = i = j;
    }
    while (keep > 0 && s[keep - 1] == ' ') --keep;
    out.assign(s.substr(0, keep)).append(kEllipsis);
    return out;
}

int wrapLines(const Font& font, Face face, std::string_view s, float width, int maxLines) {
    return breakLines(font, face, s, width, maxLines, [](std::string_view, bool) {});
}

float Painter::wrapped(Face face, std::string_view s, float x, float top, float width, int maxLines,
                       SDL_FColor color) {
    const float lh = font_.lineHeight(face);
    float y = top + font_.ascent(face);
    const int lines =
        breakLines(font_, face, s, width, maxLines, [&](std::string_view line, bool cut) {
            if (cut) {
                // Truncate the final visible line with an ellipsis.
                while (!line.empty() &&
                       font_.measure(face, line) + font_.measure(face, "…") > width)
                    line.remove_suffix(1);
                const float w = font_.draw(batch_, face, line, x, y, color);
                font_.draw(batch_, face, "…", x + w, y, color);
            } else {
                font_.draw(batch_, face, line, x, y, color);
            }
            y += lh;
        });
    return static_cast<float>(lines) * lh;
}

void Painter::icon(char32_t cp, float cx, float cy, SDL_FColor color) {
    font_.drawIcon(batch_, cp, cx, cy, color);
}

void Painter::thumbnail(const Sprite& sprite, Box b, float maxScale, float alpha, SDL_FColor tint) {
    if (thumbCount_ == thumbs_.size()) endLayer();
    thumbs_[thumbCount_++] = {sprite, b, maxScale, {tint.r, tint.g, tint.b, tint.a * alpha}};
}

void Painter::endLayer() {
    for (std::size_t i = 0; i < thumbCount_; ++i) {
        const Thumb& t = thumbs_[i];
        const Sprite& s = t.sprite;
        if (s.w <= 0 || s.h <= 0 || s.texture == nullptr) continue;
        const float fit = std::min({t.box.w / s.w, t.box.h / s.h, t.maxScale});
        const bool whole = fit >= 1.0f;
        const float k = whole ? std::floor(fit) : fit;
        const float w = s.w * k;
        const float h = s.h * k;
        batch_.use(s.texture, SDL_BLENDMODE_BLEND,
                   whole ? SDL_SCALEMODE_NEAREST : SDL_SCALEMODE_LINEAR);
        batch_.quad(
            SDL_FRect{std::round(t.box.cx() - w * 0.5f), std::round(t.box.cy() - h * 0.5f), w, h},
            s.uv, t.color);
    }
    thumbCount_ = 0;
}

} // namespace lc
