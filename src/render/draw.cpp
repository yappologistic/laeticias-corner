#include "render/draw.hpp"

#include <array>
#include <utility>

namespace lc {

void putSprite(Batch& batch, const Sprite& s, Vec2 anchor, const Xform& x, SDL_FColor color,
               SDL_BlendMode blend, bool mirror, Vec2 pivot, Vec2 scale) {
    const float x0 = mirror ? -(s.w - s.ox) : -s.ox;
    const float y0 = -s.oy;
    const auto place = [&](float lx, float ly) {
        const Vec2 w{pivot.x + (anchor.x + lx - pivot.x) * scale.x,
                     pivot.y + (anchor.y + ly - pivot.y) * scale.y};
        const Vec2 t = x.apply(w);
        return SDL_FPoint{t.x, t.y};
    };
    const SDL_FPoint p[4] = {place(x0, y0), place(x0 + s.w, y0), place(x0 + s.w, y0 + s.h),
                             place(x0, y0 + s.h)};
    UvRect uv = s.uv;
    if (mirror) std::swap(uv.u0, uv.u1);
    batch.use(s.texture, blend, x.filter);
    batch.quad(p, uv, color);
}

void putSpriteCut(Batch& batch, const Sprite& s, Vec2 anchor, const Xform& x, SDL_FColor color,
                  SDL_BlendMode blend, float a, float b, bool below) {
    // The sprite's rectangle clipped by the half-plane (a convex polygon of at most five
    // corners), texture coordinates carried along.
    const float x0 = anchor.x - s.ox;
    const float y0 = anchor.y - s.oy;
    const std::array<Vec2, 4> rect{
        {{x0, y0}, {x0 + s.w, y0}, {x0 + s.w, y0 + s.h}, {x0, y0 + s.h}}};
    const auto side = [&](Vec2 p) { return below ? p.y - (a + b * p.x) : (a + b * p.x) - p.y; };
    std::array<Vec2, 5> poly{};
    int n = 0;
    for (std::size_t i = 0; i < rect.size(); ++i) {
        const Vec2 p = rect[i];
        const Vec2 q = rect[(i + 1) % rect.size()];
        const float sp = side(p);
        const float sq = side(q);
        if (sp >= 0) poly[static_cast<std::size_t>(n++)] = p;
        if ((sp >= 0) != (sq >= 0) && n < 5) {
            const float t = sp / (sp - sq);
            poly[static_cast<std::size_t>(n++)] = {p.x + (q.x - p.x) * t, p.y + (q.y - p.y) * t};
        }
    }
    if (n < 3) return;
    std::array<SDL_Vertex, 5> v{};
    for (int i = 0; i < n; ++i) {
        const Vec2 w = poly[static_cast<std::size_t>(i)];
        const Vec2 t = x.apply(w);
        v[static_cast<std::size_t>(i)] = {{t.x, t.y},
                                          color,
                                          {s.uv.u0 + (s.uv.u1 - s.uv.u0) * (w.x - x0) / s.w,
                                           s.uv.v0 + (s.uv.v1 - s.uv.v0) * (w.y - y0) / s.h}};
    }
    std::array<int, 9> idx{};
    int m = 0;
    for (int i = 1; i + 1 < n; ++i) {
        idx[static_cast<std::size_t>(m++)] = 0;
        idx[static_cast<std::size_t>(m++)] = i;
        idx[static_cast<std::size_t>(m++)] = i + 1;
    }
    batch.use(s.texture, blend, x.filter);
    batch.triangles(v.data(), n, idx.data(), m);
}

} // namespace lc
