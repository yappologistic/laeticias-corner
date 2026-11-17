#include "render/draw.hpp"

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

} // namespace lc
