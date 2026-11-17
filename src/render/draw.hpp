#pragma once
// Placing atlas sprites in a render target: world pixels map to target pixels through an origin
// and a resolution (target pixels per world pixel; below 1 only for the overview).

#include "core/iso.hpp"
#include "platform/batch.hpp"
#include "platform/sprite.hpp"

namespace lc {

struct Xform {
    Vec2 origin;   // world px at the target's top-left pixel
    float res = 1; // target px per world px
    SDL_ScaleMode filter = SDL_SCALEMODE_NEAREST;
    [[nodiscard]] Vec2 apply(Vec2 w) const {
        return {(w.x - origin.x) * res, (w.y - origin.y) * res};
    }
};

// Draws `s` with its anchor at world point `anchor`, optionally mirrored and scaled about `pivot`.
void putSprite(Batch& batch, const Sprite& s, Vec2 anchor, const Xform& x, SDL_FColor color,
               SDL_BlendMode blend, bool mirror = false, Vec2 pivot = {}, Vec2 scale = {1, 1});

} // namespace lc
