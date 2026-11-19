#include "platform/batch.hpp"

#include <algorithm>

namespace lc {
namespace {
// Large enough that a full map plus effects fits in one submission per pass.
constexpr std::size_t kMaxVerts = 65536;
constexpr std::size_t kMaxIndices = kMaxVerts * 3 / 2;
} // namespace

Batch::Batch(SDL_Renderer* renderer)
    : renderer_(renderer), verts_(std::make_unique_for_overwrite<SDL_Vertex[]>(kMaxVerts)),
      indices_(std::make_unique_for_overwrite<int[]>(kMaxIndices)) {}

void Batch::use(SDL_Texture* texture, SDL_BlendMode mode, SDL_ScaleMode scale) {
    if (texture == texture_ && mode == mode_ && (texture == nullptr || scale == scale_)) return;
    flush();
    texture_ = texture;
    mode_ = mode;
    scale_ = scale;
}

void Batch::submit(const SDL_Vertex* verts, int vertCount, const int* indices, int indexCount) {
    // Logged rather than fatal: a failed submission only loses one frame's geometry.
    // Blend and scale modes are captured per draw command, so setting them here is safe even
    // though the same texture is drawn differently later in the frame.
    const bool modeOk = texture_ != nullptr ? SDL_SetTextureBlendMode(texture_, mode_) &&
                                                  SDL_SetTextureScaleMode(texture_, scale_)
                                            : SDL_SetRenderDrawBlendMode(renderer_, mode_);
    if (!modeOk ||
        !SDL_RenderGeometry(renderer_, texture_, verts, vertCount, indices, indexCount)) {
        SDL_Log("render: geometry submission failed: %s", SDL_GetError());
    }
    ++drawCalls_;
    ++bandDraws_[band_ < kTags - 1 ? band_ : kTags - 1];
}

void Batch::flush() {
    if (indexCount_ == 0) return;
    submit(verts_.get(), static_cast<int>(vertCount_), indices_.get(),
           static_cast<int>(indexCount_));
    vertCount_ = 0;
    indexCount_ = 0;
}

void Batch::triangles(const SDL_Vertex* verts, int vertCount, const int* indices, int indexCount) {
    const auto nv = static_cast<std::size_t>(vertCount);
    const auto ni = static_cast<std::size_t>(indexCount);
    if (vertCount_ + nv > kMaxVerts || indexCount_ + ni > kMaxIndices) flush();
    if (nv > kMaxVerts || ni > kMaxIndices) {
        // More than the arrays hold (a veil over a very large window): as it was given.
        submit(verts, vertCount, indices, indexCount);
        return;
    }
    const int base = static_cast<int>(vertCount_);
    std::copy_n(verts, nv, verts_.get() + vertCount_);
    int* out = indices_.get() + indexCount_;
    for (std::size_t i = 0; i < ni; ++i) out[i] = base + indices[i];
    vertCount_ += nv;
    indexCount_ += ni;
}

void Batch::quad(const SDL_FPoint (&p)[4], UvRect uv, SDL_FColor color) {
    // The hot path of every frame: written straight into the arrays.
    if (vertCount_ + 4 > kMaxVerts || indexCount_ + 6 > kMaxIndices) flush();
    const int base = static_cast<int>(vertCount_);
    SDL_Vertex* v = verts_.get() + vertCount_;
    v[0] = {p[0], color, {uv.u0, uv.v0}};
    v[1] = {p[1], color, {uv.u1, uv.v0}};
    v[2] = {p[2], color, {uv.u1, uv.v1}};
    v[3] = {p[3], color, {uv.u0, uv.v1}};
    int* i = indices_.get() + indexCount_;
    i[0] = base;
    i[1] = base + 1;
    i[2] = base + 2;
    i[3] = base;
    i[4] = base + 2;
    i[5] = base + 3;
    vertCount_ += 4;
    indexCount_ += 6;
}

void Batch::quad(SDL_FRect d, UvRect uv, SDL_FColor color) {
    const SDL_FPoint p[4] = {
        {d.x, d.y}, {d.x + d.w, d.y}, {d.x + d.w, d.y + d.h}, {d.x, d.y + d.h}};
    quad(p, uv, color);
}

} // namespace lc
