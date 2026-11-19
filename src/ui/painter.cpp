#include "ui/painter.hpp"

#include <algorithm>
#include <cmath>
#include <numbers>

namespace lc {
namespace {
constexpr int kArcSegments = 10; // a corner's arc at most
constexpr int kOutline = 4 * (kArcSegments + 1);
using Loop = std::array<SDL_FPoint, kOutline>;

// Segments for a corner of radius `r` px: as many as keep its arc as close to the circle as
// the largest corners drawn are with all ten (0.08 px at a radius of 25). A small button's
// corner needs five, not ten, and every vertex of an outline is shaded here and copied again
// by the renderer.
int arcSegments(float r) {
    return std::clamp(static_cast<int>(std::ceil(2.0f * std::sqrt(std::max(0.0f, r)))), 1,
                      kArcSegments);
}

// Vertices of an outline whose corners have `segments` each.
constexpr int outlineCount(int segments) {
    return 4 * (segments + 1);
}

// Unit directions of the outline's vertices for each number of segments, computed once:
// outlines are rebuilt many times a frame.
const Loop& arcDirections(int segments) {
    static const std::array<Loop, kArcSegments + 1> tables = [] {
        std::array<Loop, kArcSegments + 1> all{};
        for (int n = 1; n <= kArcSegments; ++n) {
            std::size_t k = 0;
            for (int c = 0; c < 4; ++c) {
                for (int s = 0; s <= n; ++s) {
                    const float a = (static_cast<float>(c) - 1.0f +
                                     static_cast<float>(s) / static_cast<float>(n)) *
                                    std::numbers::pi_v<float> * 0.5f;
                    all[static_cast<std::size_t>(n)][k++] = {std::cos(a), std::sin(a)};
                }
            }
        }
        return all;
    }();
    return tables[static_cast<std::size_t>(segments)];
}

// Outline of a rounded rectangle inset by `d` (negative grows it), clockwise from the top-right
// arc, `segments` to a corner. `r` is the radius before insetting.
void outline(Box b, float r, float d, int segments, Loop& out) {
    const float ri = std::max(0.0f, r - d);
    const Box in{b.x + d, b.y + d, b.w - 2 * d, b.h - 2 * d};
    const SDL_FPoint centres[4] = {{in.x + in.w - ri, in.y + ri},
                                   {in.x + in.w - ri, in.y + in.h - ri},
                                   {in.x + ri, in.y + in.h - ri},
                                   {in.x + ri, in.y + ri}};
    const Loop& dir = arcDirections(segments);
    const auto perCorner = static_cast<std::size_t>(segments + 1);
    for (std::size_t k = 0; k < 4 * perCorner; ++k) {
        const SDL_FPoint c = centres[k / perCorner];
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

// Index list joining loop `a` to loop `b` (vertex offsets, `count` vertices each) with one quad
// per outline segment.
template <std::size_t N>
std::size_t band(std::array<int, N>& idx, std::size_t n, int a, int b, int count) {
    for (int i = 0; i < count; ++i) {
        const int j = (i + 1) % count;
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
    if (radius == 0 && feather == 0 && b.w <= kMaxTriangle && b.h <= kMaxTriangle) {
        // A plain rectangle (a bar of a graph, a divider) is one quad: the same pixels as the
        // fan below at a thirtieth of the vertices.
        const SDL_FPoint q[4] = {
            {b.x, b.y}, {b.x + b.w, b.y}, {b.x + b.w, b.y + b.h}, {b.x, b.y + b.h}};
        const SDL_Vertex v[4] = {{q[0], shade.at(q[0].y), uv(q[0])},
                                 {q[1], shade.at(q[1].y), uv(q[1])},
                                 {q[2], shade.at(q[2].y), uv(q[2])},
                                 {q[3], shade.at(q[3].y), uv(q[3])}};
        static constexpr int kQuad[6] = {0, 1, 2, 0, 2, 3};
        batch_.use(texture, SDL_BLENDMODE_BLEND, SDL_SCALEMODE_LINEAR);
        batch_.triangles(v, 4, kQuad, 6);
        return;
    }
    // The solid edge sits half the feather inside the box so the visible edge stays where the box
    // says; the transparent edge half outside.
    const float inset = std::min(feather * 0.5f, radius);
    const int segments = arcSegments(radius + std::max(0.0f, feather - inset));
    const int count = outlineCount(segments);
    const auto uc = static_cast<std::size_t>(count);
    Loop solid;
    Loop clear;
    outline(b, radius, inset, segments, solid);
    outline(b, radius, inset - feather, segments, clear);

    std::array<SDL_Vertex, 1 + 2 * kOutline> v;
    const SDL_FPoint centre{b.cx(), b.cy()};
    v[0] = {centre, shade.at(centre.y), uv(centre)};
    for (std::size_t i = 0; i < uc; ++i) {
        v[1 + i] = {solid[i], shade.at(solid[i].y), uv(solid[i])};
        v[1 + uc + i] = {clear[i], shade.at(clear[i].y, 0.0f), uv(clear[i])};
    }
    std::array<int, kOutline * 9> idx;
    std::size_t n = 0;
    batch_.use(texture, SDL_BLENDMODE_BLEND, SDL_SCALEMODE_LINEAR);
    // Large panels (a full-window veil) are filled in small triangles: renderers rasterise
    // huge ones unreliably (the software one drops parts of them).
    const bool big = b.w > kMaxTriangle || b.h > kMaxTriangle;
    for (int i = 0; i < count && !big; ++i) {
        idx[n++] = 0;
        idx[n++] = 1 + i;
        idx[n++] = 1 + (i + 1) % count;
    }
    if (big) {
        // The batch's scratch storage: kept between frames, so nothing is allocated per frame.
        auto& points = batch_.scratch().points;
        auto& bigV_ = batch_.scratch().verts;
        auto& bigI_ = batch_.scratch().indices;
        fanMesh(centre, std::span(solid.data(), uc), kMaxTriangle, points, bigI_);
        bigV_.clear();
        for (const SDL_FPoint pt : points) bigV_.push_back({pt, shade.at(pt.y), uv(pt)});
        batch_.triangles(bigV_.data(), static_cast<int>(bigV_.size()), bigI_.data(),
                         static_cast<int>(bigI_.size()));
    }
    n = band(idx, n, 1, 1 + count, count);
    batch_.triangles(v.data(), 1 + 2 * count, idx.data(), static_cast<int>(n));
}

void fanMesh(SDL_FPoint centre, std::span<const SDL_FPoint> outline, float maxEdge,
             std::vector<SDL_FPoint>& points, std::vector<int>& indices) {
    points.clear();
    indices.clear();
    const std::size_t count = outline.size();
    if (count < 3) return;
    // Rings: the outline drawn in towards the centre, the same number of rings all round.
    float spoke = 0;
    for (const SDL_FPoint p : outline)
        spoke = std::max(spoke, std::hypot(p.x - centre.x, p.y - centre.y));
    // A ring's quads are halved along their diagonal, the longest side of the two triangles:
    // rings and pieces are cut so that even it stays within the limit.
    const float cut = maxEdge * 0.7071f;
    const int rings = std::max(1, static_cast<int>(std::ceil(spoke / cut)));
    // Outline vertex `i` on ring `r` (the outline itself on the last): one value whichever of
    // the two sides that meet there asks.
    const auto on = [&](std::size_t i, int r) {
        const SDL_FPoint p = outline[i % count];
        if (r == rings) return p;
        const float t = static_cast<float>(r) / static_cast<float>(rings);
        return SDL_FPoint{centre.x + (p.x - centre.x) * t, centre.y + (p.y - centre.y) * t};
    };
    points.push_back(centre);
    for (std::size_t i = 0; i < count; ++i) {
        // A long side (a panel's straight edge) is cut into pieces, the same on every ring.
        const SDL_FPoint p = outline[i];
        const SDL_FPoint q = outline[(i + 1) % count];
        // A square corner is two outline points in one place: no side, no triangles (a
        // renderer that pairs triangles into rectangles misreads empty ones).
        if (p.x == q.x && p.y == q.y) continue;
        const int pieces =
            std::max(1, static_cast<int>(std::ceil(std::hypot(q.x - p.x, q.y - p.y) / cut)));
        const int base = static_cast<int>(points.size());
        for (int r = 1; r <= rings; ++r) {
            const SDL_FPoint from = on(i, r);
            const SDL_FPoint to = on(i + 1, r);
            for (int j = 0; j <= pieces; ++j) {
                if (j == 0 || j == pieces) {
                    points.push_back(j == 0 ? from : to);
                    continue;
                }
                const float u = static_cast<float>(j) / static_cast<float>(pieces);
                points.push_back({from.x + (to.x - from.x) * u, from.y + (to.y - from.y) * u});
            }
        }
        const auto at = [&](int r, int j) { return base + (r - 1) * (pieces + 1) + j; };
        for (int j = 0; j < pieces; ++j) {
            indices.insert(indices.end(), {0, at(1, j), at(1, j + 1)});
            for (int r = 1; r < rings; ++r) {
                indices.insert(indices.end(), {at(r, j), at(r + 1, j), at(r + 1, j + 1)});
                indices.insert(indices.end(), {at(r, j), at(r + 1, j + 1), at(r, j + 1)});
            }
        }
    }
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
    const int segments = arcSegments(radius + 0.5f);
    const int count = outlineCount(segments);
    const auto uc = static_cast<std::size_t>(count);
    std::array<SDL_Vertex, 3 * kOutline> v;
    Loop loop;
    for (std::size_t l = 0; l < 3; ++l) {
        outline(b, radius, d[l], segments, loop);
        for (std::size_t i = 0; i < uc; ++i)
            v[l * uc + i] = {loop[i], shade.at(loop[i].y, a[l]), t};
    }
    std::array<int, kOutline * 12> idx;
    std::size_t n = 0;
    for (int l = 0; l < 2; ++l) n = band(idx, n, l * count, (l + 1) * count, count);
    batch_.use(font_.texture(), SDL_BLENDMODE_BLEND, SDL_SCALEMODE_LINEAR);
    batch_.triangles(v.data(), 3 * count, idx.data(), static_cast<int>(n));
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
        Font::Run run; // the line so far: each word is measured once
        while (end < s.size()) {
            std::size_t next = s.find(' ', end + 1);
            if (next == std::string_view::npos) next = s.size();
            font.extend(face, s.substr(end, next - end), run);
            if (run.width > width && fit > start) break;
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

void dropLastCharacter(std::string_view& s) {
    while (!s.empty() && (static_cast<unsigned char>(s.back()) & 0xC0u) == 0x80u)
        s.remove_suffix(1); // continuation bytes
    if (!s.empty()) s.remove_suffix(1);
}

bool namedAlready(std::string_view name, std::string_view title, std::string_view epithet) {
    std::string_view base = name.substr(0, std::min(name.find(','), name.find(" (")));
    while (base.ends_with(' ')) base.remove_suffix(1);
    if (base.empty()) return true;
    return title.contains(base) || epithet.contains(base);
}

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
                    dropLastCharacter(line);
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
