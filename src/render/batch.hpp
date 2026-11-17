#pragma once
// Accumulates textured triangles and submits them in as few SDL_RenderGeometry calls as possible.

#include <SDL3/SDL.h>

#include <vector>

namespace lc {

struct UvRect {
    float u0 = 0;
    float v0 = 0;
    float u1 = 0;
    float v1 = 0;
};

class Batch {
public:
    explicit Batch(SDL_Renderer* renderer);

    // Switches texture/blend mode, flushing pending geometry when either changes.
    void use(SDL_Texture* texture, SDL_BlendMode mode);
    void quad(SDL_FRect dst, UvRect uv, SDL_FColor color);
    // Corners in order top-left, top-right, bottom-right, bottom-left.
    void quad(const SDL_FPoint (&p)[4], UvRect uv, SDL_FColor color);
    // Arbitrary indexed triangles; indices are local to `verts`.
    void triangles(const SDL_Vertex* verts, int vertCount, const int* indices, int indexCount);
    void flush();

    [[nodiscard]] int drawCalls() const { return drawCalls_; }
    void resetStats() { drawCalls_ = 0; }

private:
    SDL_Renderer* renderer_;
    SDL_Texture* texture_ = nullptr;
    SDL_BlendMode mode_ = SDL_BLENDMODE_BLEND;
    std::vector<SDL_Vertex> verts_;
    std::vector<int> indices_;
    int drawCalls_ = 0;
};

} // namespace lc
