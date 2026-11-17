#pragma once
// A drawable image: the texture it lives in, where, its size and its anchor. Carrying the texture
// keeps every consumer independent of how many atlas pages exist.

#include "platform/batch.hpp"

#include <SDL3/SDL.h>

namespace lc {

struct Sprite {
    SDL_Texture* texture = nullptr;
    UvRect uv;
    float w = 0;
    float h = 0;
    float ox = 0; // anchor inside the sprite
    float oy = 0;
};

} // namespace lc
