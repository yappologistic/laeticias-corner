#pragma once
// Sprites drawn from the packed pages on SDL's `gpu` driver (out/reports/art-data-contract.md,
// assets/shaders/packed.frag): the ramp table, the month's remap per climate, and the render
// state that decodes them. Every look tier on this driver draws through it (the classic tier
// too), so the pages are the packed ones for the whole run; other renderers keep the colour
// pages.

#include "platform/batch.hpp"
#include "platform/sdl_ptr.hpp"
#include "render/gpu/seasons.hpp"

#include <SDL3/SDL_gpu.h>

#include <memory>
#include <span>

namespace lc::gpu {

class Decoder {
public:
    // The climates a remap holds (rows of the remap texture).
    static constexpr int kClimates = 32;
    // Null unless `renderer` is SDL's `gpu` driver and the shader, samplers and state are made;
    // `ramps` is `assets/atlas/ramps.png` (a row per ramp id, a column per step).
    [[nodiscard]] static std::unique_ptr<Decoder> make(SDL_Renderer* renderer,
                                                       const SDL_Surface* ramps, int snowRamp);
    ~Decoder();
    Decoder(const Decoder&) = delete;
    Decoder& operator=(const Decoder&) = delete;

    // The remap: kClimates rows of kRampIds ramp ids (row per climate, for the month); `water`
    // per ramp id: its texels are water (marked for the look's water, kItemWaterMark).
    void setRemap(std::span<const std::uint8_t> rows, std::span<const bool, kRampIds> water);
    // Packed sprites draw opaque (the contract: what is translucent is colour-only) and write
    // their alpha as it is (1, or the water mark), empty texels discarded: a water texel stays
    // marked whatever lies under it, and what is drawn over water restores alpha 1.
    [[nodiscard]] SDL_BlendMode replace() const { return replace_; }
    static constexpr float kItemWaterMark = 0.97f;
    // Draws from now on decode (on) or are plain (off). Off before anything else sets a render
    // state or another batch draws (the home's scene, the look's passes).
    void use(Batch& b, bool on);

private:
    explicit Decoder(SDL_Renderer* renderer) : renderer_(renderer) {}
    SDL_Renderer* renderer_;
    SDL_GPUShader* shader_ = nullptr;
    SDL_GPUSampler* nearest_ = nullptr;
    SDL_GPURenderState* state_ = nullptr;
    TexturePtr ramps_;
    TexturePtr remap_;
    bool on_ = false;
    SDL_BlendMode replace_ = SDL_BLENDMODE_INVALID;
};

} // namespace lc::gpu
