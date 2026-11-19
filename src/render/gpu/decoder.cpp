#include "render/gpu/decoder.hpp"

#include "render/gpu/post.hpp"
#include "render/gpu/tuning.hpp"

#include <algorithm>
#include <array>
#include <vector>

namespace lc::gpu {

std::unique_ptr<Decoder> Decoder::make(SDL_Renderer* renderer, const SDL_Surface* ramps,
                                       const RampSeasons& seasons) {
    if (!isGpu(renderer) || ramps == nullptr) return nullptr;
    std::unique_ptr<Decoder> d(new Decoder(renderer));
    SDL_GPUDevice* device = SDL_GetGPURendererDevice(renderer);
    if (device == nullptr) return nullptr;
    d->shader_ = makeFragmentShader(device, "packed", 3);
    SDL_GPUSamplerCreateInfo si{};
    si.min_filter = SDL_GPU_FILTER_NEAREST;
    si.mag_filter = SDL_GPU_FILTER_NEAREST;
    si.mipmap_mode = SDL_GPU_SAMPLERMIPMAPMODE_NEAREST;
    si.address_mode_u = SDL_GPU_SAMPLERADDRESSMODE_CLAMP_TO_EDGE;
    si.address_mode_v = SDL_GPU_SAMPLERADDRESSMODE_CLAMP_TO_EDGE;
    si.address_mode_w = SDL_GPU_SAMPLERADDRESSMODE_CLAMP_TO_EDGE;
    d->nearest_ = SDL_CreateGPUSampler(device, &si);
    // The ramp table at full width (8 steps) and every id a word can name.
    const SurfacePtr table{SDL_ConvertSurface(const_cast<SDL_Surface*>(ramps), Post::kFormat)};
    d->ramps_.reset(
        SDL_CreateTexture(renderer, Post::kFormat, SDL_TEXTUREACCESS_STATIC, 8, kRampIds));
    d->remap_.reset(
        SDL_CreateTexture(renderer, Post::kFormat, SDL_TEXTUREACCESS_STATIC, kRampIds, kClimates));
    if (d->shader_ == nullptr || d->nearest_ == nullptr || !table || !d->ramps_ || !d->remap_) {
        SDL_Log("decoder: %s", SDL_GetError());
        return nullptr;
    }
    std::vector<std::uint32_t> px(static_cast<std::size_t>(8 * kRampIds), 0);
    for (int y = 0; y < table->h && y < kRampIds; ++y)
        for (int x = 0; x < table->w && x < 8; ++x) {
            // Alpha carries the step's Oklab lightness (0: no such step).
            const std::uint32_t c = *reinterpret_cast<const std::uint32_t*>(
                static_cast<const std::uint8_t*>(table->pixels) +
                static_cast<std::ptrdiff_t>(y) * table->pitch + x * 4);
            const float l =
                seasons.lightness[static_cast<std::size_t>(y)][static_cast<std::size_t>(x)];
            const auto a = static_cast<std::uint32_t>(std::clamp(l, 0.0f, 1.0f) * 255.0f + 0.5f);
            px[static_cast<std::size_t>(y * 8 + x)] = (c & 0x00FFFFFFu) | (a << 24);
        }
    if (!SDL_UpdateTexture(d->ramps_.get(), nullptr, px.data(), 8 * 4)) {
        SDL_Log("decoder: %s", SDL_GetError());
        return nullptr;
    }
    // Until a month is set every ramp stays itself.
    std::vector<std::uint8_t> identity(static_cast<std::size_t>(kRampIds * kClimates));
    for (std::size_t i = 0; i < identity.size(); ++i)
        identity[i] = static_cast<std::uint8_t>(i % kRampIds);
    d->setRemap(identity, std::array<bool, kRampIds>{});
    d->replace_ = SDL_ComposeCustomBlendMode(SDL_BLENDFACTOR_ONE, SDL_BLENDFACTOR_ZERO,
                                             SDL_BLENDOPERATION_ADD, SDL_BLENDFACTOR_ONE,
                                             SDL_BLENDFACTOR_ZERO, SDL_BLENDOPERATION_ADD);
    SDL_GPURenderStateCreateInfo ci{};
    ci.fragment_shader = d->shader_;
    std::array<SDL_GPUTextureSamplerBinding, 2> bind{
        {{static_cast<SDL_GPUTexture*>(
              SDL_GetPointerProperty(SDL_GetTextureProperties(d->ramps_.get()),
                                     SDL_PROP_TEXTURE_GPU_TEXTURE_POINTER, nullptr)),
          d->nearest_},
         {static_cast<SDL_GPUTexture*>(
              SDL_GetPointerProperty(SDL_GetTextureProperties(d->remap_.get()),
                                     SDL_PROP_TEXTURE_GPU_TEXTURE_POINTER, nullptr)),
          d->nearest_}}};
    ci.num_sampler_bindings = static_cast<Sint32>(bind.size());
    ci.sampler_bindings = bind.data();
    d->state_ = SDL_CreateGPURenderState(renderer, &ci);
    if (d->state_ == nullptr || bind[0].texture == nullptr || bind[1].texture == nullptr) {
        SDL_Log("decoder: render state: %s", SDL_GetError());
        return nullptr;
    }
    d->uniforms_[0] = static_cast<float>(seasons.snow);
    d->uniforms_[1] = kItemWaterMark;
    const float up[3] = {0, 0, 1};
    d->setSun(up, 0, 0);
    return d;
}

Decoder::~Decoder() {
    // Draws queued with the state must be submitted before it goes.
    if (!SDL_SetGPURenderState(renderer_, nullptr) || !SDL_FlushRenderer(renderer_))
        SDL_Log("decoder: %s", SDL_GetError());
    if (state_ != nullptr) SDL_DestroyGPURenderState(state_);
    SDL_GPUDevice* device = SDL_GetGPURendererDevice(renderer_);
    if (device != nullptr) {
        if (nearest_ != nullptr) SDL_ReleaseGPUSampler(device, nearest_);
        if (shader_ != nullptr) SDL_ReleaseGPUShader(device, shader_);
    }
}

void Decoder::setRemap(std::span<const std::uint8_t> rows, std::span<const bool, kRampIds> water) {
    if (rows.size() < static_cast<std::size_t>(kRampIds * kClimates)) return;
    std::vector<std::uint32_t> px(rows.size());
    // Red: the ramp it becomes; green: 255 when the original ramp is water.
    for (std::size_t i = 0; i < rows.size(); ++i)
        px[i] = rows[i] | (water[i % kRampIds] ? 0xFF00u : 0u) | 0xFF000000u;
    if (!SDL_UpdateTexture(remap_.get(), nullptr, px.data(), kRampIds * 4))
        SDL_Log("decoder: %s", SDL_GetError());
}

void Decoder::setSun(const float dir[3], float strength, float contact) {
    for (int i = 0; i < 3; ++i) uniforms_[4 + i] = dir[i];
    uniforms_[7] = strength;
    uniforms_[8] = tuning::kRelightExponent;
    uniforms_[9] = contact;
    uniforms_[10] = tuning::kRelightMax;
    uniforms_[11] = tuning::kRelightLift;
    if (!SDL_SetGPURenderStateFragmentUniforms(state_, 0, uniforms_, sizeof uniforms_))
        SDL_Log("decoder: %s", SDL_GetError());
}

void Decoder::use(Batch& b, bool on) {
    if (on == on_) return;
    b.flush();
    if (!SDL_SetGPURenderState(renderer_, on ? state_ : nullptr))
        SDL_Log("decoder: %s", SDL_GetError());
    on_ = on;
}

} // namespace lc::gpu
