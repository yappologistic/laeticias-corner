#include "platform/batch.hpp"

namespace lc {
namespace {
// Large enough that a full map plus effects fits in one submission per pass.
constexpr std::size_t kMaxVerts = 65536;
constexpr std::size_t kMaxIndices = kMaxVerts * 3 / 2;
} // namespace

Batch::Batch(SDL_Renderer* renderer) : renderer_(renderer) {
    verts_.reserve(kMaxVerts);
    indices_.reserve(kMaxIndices);
}

void Batch::use(SDL_Texture* texture, SDL_BlendMode mode, SDL_ScaleMode scale) {
    if (texture == texture_ && mode == mode_ && (texture == nullptr || scale == scale_)) return;
    flush();
    texture_ = texture;
    mode_ = mode;
    scale_ = scale;
}

void Batch::flush() {
    if (indices_.empty()) return;
    // Logged rather than fatal: a failed submission only loses one frame's geometry.
    // Blend and scale modes are captured per draw command, so setting them here is safe even
    // though the same texture is drawn differently later in the frame.
    const bool modeOk = texture_ != nullptr ? SDL_SetTextureBlendMode(texture_, mode_) &&
                                                  SDL_SetTextureScaleMode(texture_, scale_)
                                            : SDL_SetRenderDrawBlendMode(renderer_, mode_);
    if (!modeOk ||
        !SDL_RenderGeometry(renderer_, texture_, verts_.data(), static_cast<int>(verts_.size()),
                            indices_.data(), static_cast<int>(indices_.size()))) {
        SDL_Log("render: geometry submission failed: %s", SDL_GetError());
    }
    ++drawCalls_;
    verts_.clear();
    indices_.clear();
}

void Batch::triangles(const SDL_Vertex* verts, int vertCount, const int* indices, int indexCount) {
    if (verts_.size() + static_cast<std::size_t>(vertCount) > kMaxVerts ||
        indices_.size() + static_cast<std::size_t>(indexCount) > kMaxIndices) {
        flush();
    }
    const int base = static_cast<int>(verts_.size());
    verts_.insert(verts_.end(), verts, verts + vertCount);
    for (int i = 0; i < indexCount; ++i) indices_.push_back(base + indices[i]);
}

void Batch::quad(const SDL_FPoint (&p)[4], UvRect uv, SDL_FColor color) {
    const SDL_Vertex v[4] = {
        {p[0], color, {uv.u0, uv.v0}},
        {p[1], color, {uv.u1, uv.v0}},
        {p[2], color, {uv.u1, uv.v1}},
        {p[3], color, {uv.u0, uv.v1}},
    };
    static constexpr int kIdx[6] = {0, 1, 2, 0, 2, 3};
    triangles(v, 4, kIdx, 6);
}

void Batch::quad(SDL_FRect d, UvRect uv, SDL_FColor color) {
    const SDL_FPoint p[4] = {
        {d.x, d.y}, {d.x + d.w, d.y}, {d.x + d.w, d.y + d.h}, {d.x, d.y + d.h}};
    quad(p, uv, color);
}

} // namespace lc
