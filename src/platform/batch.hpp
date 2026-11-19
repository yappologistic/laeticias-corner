#pragma once
// Accumulates textured triangles and submits them in as few SDL_RenderGeometry calls as possible.

#include <SDL3/SDL.h>

#include <cstddef>
#include <memory>
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

    // Switches texture, blend mode and sampling, flushing pending geometry when any changes.
    void use(SDL_Texture* texture, SDL_BlendMode mode, SDL_ScaleMode scale = SDL_SCALEMODE_NEAREST);
    void quad(SDL_FRect dst, UvRect uv, SDL_FColor color);
    // Corners in order top-left, top-right, bottom-right, bottom-left.
    void quad(const SDL_FPoint (&p)[4], UvRect uv, SDL_FColor color);
    // Arbitrary indexed triangles; indices are local to `verts`.
    void triangles(const SDL_Vertex* verts, int vertCount, const int* indices, int indexCount);
    void flush();

    [[nodiscard]] int drawCalls() const { return drawCalls_; }
    // Storage a caller may build geometry in before handing it to triangles(); it keeps its
    // capacity from frame to frame.
    struct Scratch {
        std::vector<SDL_Vertex> verts;
        std::vector<int> indices;
        std::vector<SDL_FPoint> points;
    };
    [[nodiscard]] Scratch& scratch() { return scratch_; }
    void resetStats() { drawCalls_ = 0; }

private:
    SDL_Renderer* renderer_;
    SDL_Texture* texture_ = nullptr;
    SDL_BlendMode mode_ = SDL_BLENDMODE_BLEND;
    SDL_ScaleMode scale_ = SDL_SCALEMODE_NEAREST;
    void submit(const SDL_Vertex* verts, int vertCount, const int* indices, int indexCount);

    // Whole arrays made once and written by position: every sprite of every frame goes
    // through here, and a growing vector would test its capacity ten times a quad. Made
    // without being filled, so only what a frame writes is ever touched.
    std::unique_ptr<SDL_Vertex[]> verts_;
    std::unique_ptr<int[]> indices_;
    std::size_t vertCount_ = 0;
    std::size_t indexCount_ = 0;
    int drawCalls_ = 0;
    Scratch scratch_;
};

} // namespace lc
