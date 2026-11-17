#include "render/blur.hpp"

#include <algorithm>
#include <cmath>

namespace lc {
namespace {
// A chain n levels deep blurs with a radius (two sigma) of about this many times 2^n pixels,
// which picks the depth for a requested radius.
constexpr float kRadiusPerTexel = 2.4f;
} // namespace

bool Blur::begin(Vec2 screen, float radius) {
    ready_ = false;
    drawCalls_ = 0;
    const int count = std::clamp(
        static_cast<int>(std::lround(std::log2(std::max(radius, 1.0f) / kRadiusPerTexel))), 2,
        kMaxLevels);
    // Exact factor-of-two sizes keep every down pass a clean 2x2 average; the frame is stretched
    // by a few pixels at most to fill the first level.
    const int div = 1 << count;
    const int bw = std::max(1, static_cast<int>(std::ceil(screen.x / static_cast<float>(div))));
    const int bh = std::max(1, static_cast<int>(std::ceil(screen.y / static_cast<float>(div))));
    if (count != count_ || bw != baseW_ || bh != baseH_ || !levels_[0]) {
        count_ = count;
        baseW_ = bw;
        baseH_ = bh;
        for (auto& t : levels_) t.reset();
        for (int i = 0; i < count; ++i) {
            const int k = 1 << (count - 1 - i);
            TexturePtr t{SDL_CreateTexture(renderer_, SDL_PIXELFORMAT_RGBA8888,
                                           SDL_TEXTUREACCESS_TARGET, bw * k, bh * k)};
            if (!t || !SDL_SetTextureScaleMode(t.get(), SDL_SCALEMODE_LINEAR) ||
                !SDL_SetTextureBlendMode(t.get(), SDL_BLENDMODE_BLEND)) {
                SDL_Log("blur: cannot create %dx%d level: %s", bw * k, bh * k, SDL_GetError());
                for (auto& l : levels_) l.reset();
                count_ = 0;
                return false;
            }
            levels_[static_cast<std::size_t>(i)] = std::move(t);
        }
    }
    const float w0 = static_cast<float>(baseW_ << (count_ - 1));
    const float h0 = static_cast<float>(baseH_ << (count_ - 1));
    scale_ = {w0 / screen.x, h0 / screen.y};
    if (!SDL_SetRenderTarget(renderer_, levels_[0].get())) {
        SDL_Log("blur: %s", SDL_GetError());
        return false;
    }
    return true;
}

void Blur::pass(int from, int to) {
    SDL_Texture* src = levels_[static_cast<std::size_t>(from)].get();
    SDL_Texture* dst = levels_[static_cast<std::size_t>(to)].get();
    float dw = 0;
    float dh = 0;
    if (!SDL_GetTextureSize(dst, &dw, &dh) || !SDL_SetRenderTarget(renderer_, dst)) {
        SDL_Log("blur: %s", SDL_GetError());
        return;
    }
    // Five full-target quads: the source in place, then shifted one target pixel along each
    // diagonal (two source texels going down, half a texel going up). Drawn in order with alphas
    // 1, 1/2 ... 1/5 over an opaque source they leave the plain average. Whole-pixel shifts with
    // UVs inside [0, 1] keep linear filtering on every renderer (the software one snaps vertices
    // and falls back to nearest sampling for UVs outside that range); the unshifted quad covers
    // the strips the shifted ones leave at the edges, so nothing stale or wrapped shows there.
    constexpr float kOffsets[5][2] = {{0, 0}, {-1, -1}, {1, 1}, {1, -1}, {-1, 1}};
    std::array<SDL_Vertex, 20> v;
    std::array<int, 30> idx;
    for (std::size_t q = 0; q < 5; ++q) {
        const float x = kOffsets[q][0];
        const float y = kOffsets[q][1];
        const SDL_FColor c{1, 1, 1, 1.0f / static_cast<float>(q + 1)};
        const std::size_t b = q * 4;
        v[b + 0] = {{x, y}, c, {0, 0}};
        v[b + 1] = {{dw + x, y}, c, {1, 0}};
        v[b + 2] = {{dw + x, dh + y}, c, {1, 1}};
        v[b + 3] = {{x, dh + y}, c, {0, 1}};
        const int base = static_cast<int>(b);
        const int quad[6] = {base, base + 1, base + 2, base, base + 2, base + 3};
        std::copy(std::begin(quad), std::end(quad), idx.begin() + static_cast<long>(q * 6));
    }
    if (!SDL_RenderGeometry(renderer_, src, v.data(), static_cast<int>(v.size()), idx.data(),
                            static_cast<int>(idx.size())))
        SDL_Log("blur: %s", SDL_GetError());
    ++drawCalls_;
}

void Blur::end() {
    for (int i = 0; i + 1 < count_; ++i) pass(i, i + 1);
    for (int i = count_ - 1; i > 0; --i) pass(i, i - 1);
    if (!SDL_SetRenderTarget(renderer_, nullptr)) SDL_Log("blur: %s", SDL_GetError());
    ready_ = count_ > 0;
}

} // namespace lc
