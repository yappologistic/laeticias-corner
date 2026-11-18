#pragma once
// The shader path on SDL's `gpu` render driver (docs/design/graphics-plan.md §3, task E1;
// src/render/gpu/README.md): the world is drawn in neutral daylight into its target, lamp pools
// go into a light target and what glows into a glow target; bloom halves the glow target down
// and back up (dual filter); one final pass grades, lights, hazes and adds the glow onto the
// window. Every other renderer has no custom shaders: make() returns null there and the caller
// keeps its classic frame.

#include "platform/batch.hpp"
#include "platform/sdl_ptr.hpp"
#include "render/gpu/look.hpp"

#include <SDL3/SDL_gpu.h>

#include <array>
#include <cstddef>
#include <memory>
#include <vector>

namespace lc::gpu {

// SDL's `gpu` renderer on `window` (null: offscreen, for headless runs, drawing into targets
// only), on Vulkan unless the environment names another driver, able to take SPIR-V. Null (with
// the reason logged by the caller from SDL_GetError) where it cannot be made.
[[nodiscard]] RendererPtr createRenderer(SDL_Window* window);
// The renderer is SDL's `gpu` driver.
[[nodiscard]] bool isGpu(SDL_Renderer* renderer);

// Everything the final pass needs for one frame.
struct FinalParams {
    GradePhase grade;
    Rgb haze;
    float hazeStrength = 0;
    float glow = 0;            // the clock's emissive strength, 0..1
    float night = 0;           // 0 day .. 1 deep night (the low light's cool shift)
    bool near = true;          // a native zoom (clear air by day)
    float windowPerTarget = 1; // window px per target px (sharp sampling)
    Vec2 artOrigin;            // art px at the target's (0, 0), for the world-anchored dither
    float targetPerArt = 1;    // target px per art px
};

class Post {
public:
    // Null unless `renderer` is SDL's `gpu` driver, every shader, sampler and state is made and
    // a test draw reads back its channels in order.
    [[nodiscard]] static std::unique_ptr<Post> make(SDL_Renderer* renderer, Quality q);
    ~Post();
    Post(const Post&) = delete;
    Post& operator=(const Post&) = delete;

    // Every texture a shader samples (CLAUDE.md probe: ARGB reads swizzled in custom shaders).
    static constexpr SDL_PixelFormat kFormat = SDL_PIXELFORMAT_ABGR8888;

    void setQuality(Quality q) { quality_ = q; }
    [[nodiscard]] Quality quality() const { return quality_; }
    // Targets for a world target allocated at `w` x `h` (grown, never shrunk).
    void prepare(int w, int h);
    // Lays the shadow layer (premultiplied black, alpha its coverage) over the current target by
    // multiplying with `tint` where it covers: the classic darkening, in the sky's colour.
    void shade(Batch& b, SDL_Texture* layer, SDL_FRect dst, UvRect uv, Rgb tint);
    // Binds `t` (light() or glow()) as the render target, cleared to transparent black.
    void begin(SDL_Texture* t);
    [[nodiscard]] SDL_Texture* light() const { return light_.get(); }
    [[nodiscard]] SDL_Texture* glow() const { return glow_.get(); }
    // A soft round falloff (white, premultiplied: (1 - r^2)^2), for pools and far lights.
    [[nodiscard]] SDL_Texture* falloff() const { return falloff_.get(); }
    // Halves the glow target's used `w` x `h` down the tier's levels and back up.
    void bloom(Batch& b, int w, int h);
    // Averages the scene's used `w` x `h` down to one texel for the night's exposure.
    void measure(Batch& b, SDL_Texture* scene, int w, int h);
    // Grades `scene` (premultiplied, the size prepare() was given) with the light and glow
    // targets onto the current target at `dst`, `uv` being the scene's used part. `aux` draws a
    // second copy in the same frame (the glass panels' blurred source) with its own uniforms.
    void final(Batch& b, SDL_Texture* scene, const FinalParams& f, SDL_FRect dst, UvRect uv,
               bool aux);
    // Texture memory of the targets.
    [[nodiscard]] std::size_t bytes() const;

private:
    static constexpr int kLevels = 5;

    explicit Post(SDL_Renderer* renderer);
    bool init();
    bool channelsRead();
    void rebuildStates();
    void use(Batch& b, SDL_GPURenderState* s);
    [[nodiscard]] TexturePtr target(int w, int h) const;
    [[nodiscard]] SDL_GPUTexture* gpuOf(SDL_Texture* t) const;
    [[nodiscard]] int levels() const;

    SDL_Renderer* renderer_;
    SDL_GPUDevice* device_ = nullptr;
    Quality quality_ = Quality::High;
    SDL_GPUShader* finalShader_ = nullptr;
    SDL_GPUShader* downShader_ = nullptr;
    SDL_GPUShader* upShader_ = nullptr;
    SDL_GPUShader* shadeShader_ = nullptr;
    SDL_GPURenderState* shadeState_ = nullptr;
    SDL_GPUSampler* linear_ = nullptr;
    // Sampler bindings and uniforms are fixed per state, so each pass and level has its own.
    std::array<SDL_GPURenderState*, 2> final_{}; // the window, the glass copy
    std::array<SDL_GPURenderState*, kLevels> down_{};
    std::array<SDL_GPURenderState*, kLevels> up_{};
    SDL_GPURenderState* current_ = nullptr;
    int w_ = 0; // allocated
    int h_ = 0;
    int usedW_ = 0; // the bloom chain's uniforms are for this used size
    int usedH_ = 0;
    TexturePtr light_;
    TexturePtr glow_;
    std::array<TexturePtr, kLevels> bloom_;
    TexturePtr falloff_;
    std::vector<TexturePtr> mean_; // kMeanSide wide, halved down to 1 x 1
    std::uint32_t measured_ = 0;   // frames since the path was made (the mean's cadence)
};

} // namespace lc::gpu
