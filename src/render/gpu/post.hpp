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
#include <span>
#include <string_view>
#include <vector>

namespace lc::gpu {

// SDL's `gpu` renderer on `window` (null: offscreen, for headless runs, drawing into targets
// only), on Vulkan unless the environment names another driver, able to take SPIR-V. Null (with
// the reason logged by the caller from SDL_GetError) where it cannot be made.
[[nodiscard]] RendererPtr createRenderer(SDL_Window* window);
// The renderer is SDL's `gpu` driver.
[[nodiscard]] bool isGpu(SDL_Renderer* renderer);
// One of the committed fragment shaders (assets/shaders, embedded) with one uniform buffer and
// `samplers` samplers; null with the reason logged.
[[nodiscard]] SDL_GPUShader* makeFragmentShader(SDL_GPUDevice* device, std::string_view name,
                                                Uint32 samplers);

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
    // Water: the field's first tile; half a tile (world px), a level's height; the
    // water's colours and bands (0: no layered water); mirrored edges (High); the sky in it.
    Vec2 waterAt;
    Vec2 halfTile{32, 16};
    Vec2 grid{1, 1};         // the world grid's size in tiles (beyond it the sea hazes away)
    float horizonTiles = 40; // ... over this many tiles
    float levelPx = 16;
    double time = 0;
    Rgb shallow{0.46f, 0.73f, 0.68f};
    Rgb deep{0.06f, 0.19f, 0.27f};
    float bands = 0;
    bool reflections = false;
    Rgb skyInWater;
    float skyShare = 0;
    // Clouds: their opacity at this zoom, their shadows' strength, their sunlit and shaded
    // colours; rain; glints. Rivers' colour.
    float deckAlpha = 0;
    float cloudShadow = 0;
    Rgb deckColour{1, 1, 1};
    Rgb deckBase{0.7f, 0.74f, 0.82f};
    Rgb river{0.25f, 0.42f, 0.38f};
    float rain = 0;
    float glints = 0;
};

// The cloud pass's inputs.
struct CloudParams {
    Vec2 origin;             // world px at the scene target's (0, 0)
    float worldPerTexel = 4; // world px per cloud texel
    Vec2 sunShift;           // ground-plane px from a cloud's point to its shadow
    float altitude = 520;    // px a cloud's base stands above its point
    std::span<const Cloud> clouds;
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
    // Binds `t` (glow()) as the render target, cleared to transparent black.
    void begin(SDL_Texture* t);
    // What glows (rgb, added and bloomed) and the lamps' pools (alpha: their light, stored with
    // headroom), one target so the frame switches to it once.
    [[nodiscard]] SDL_Texture* glow() const { return glow_.get(); }
    // Pools add into the glow target's alpha only (draw with falloff() and colour (0, 0, 0, k)).
    [[nodiscard]] SDL_BlendMode poolBlend() const { return poolBlend_; }
    // Marks water in the ground cells: the target's alpha lowered by the sprite's coverage times
    // the vertex alpha (kWaterMark), its colour kept. The final pass reads alpha in (0.5, 0.995)
    // as water (under 0.97: only where the colour is water's); whatever is drawn over it later
    // restores alpha 1.
    [[nodiscard]] SDL_BlendMode markBlend() const { return markBlend_; }
    static constexpr float kWaterMark = 0.02f;
    static constexpr float kMaybeWaterMark = 0.045f; // water if the colour is water's
    // What stands over water (draw-order.md band B6) restores alpha 1 however faintly it is
    // drawn: colour blended as SDL_BLENDMODE_BLEND, alpha added (a ghost or a fading piece
    // drawn at half strength over water stays on top of it instead of under the water pass).
    [[nodiscard]] SDL_BlendMode coverBlend() const { return coverBlend_; }
    // A layer of ground laid over other ground (the home's over the world's rim tiles, and its
    // chunks' borders over each other) goes on over as usual and then is stamped, so the target
    // holds the layer's own alpha (its water mark among it) wherever the layer covers: while on,
    // draws with stampBlend() set the target's alpha to a picture's own under the texels it
    // covers (alpha 0.9 and over, stamp.frag), colour kept.
    void stamp(Batch& b, bool on);
    [[nodiscard]] SDL_BlendMode stampBlend() const { return stampBlend_; }
    // A soft round falloff (white, premultiplied: (1 - r^2)^2), for pools and far lights.
    [[nodiscard]] SDL_Texture* falloff() const { return falloff_.get(); }
    // Halves the glow target's used `w` x `h` down the tier's levels and back up.
    void bloom(Batch& b, int w, int h);
    // The clouds and their shadows for this frame at a quarter of the scene's used size.
    void clouds(Batch& b, const CloudParams& p, int w, int h);
    // No clouds this frame (the setting Off, or none in the sky): the cloud target cleared.
    void noClouds();
    // The tile water field round the view (one texel per tile: shore distance, flow, flags; at
    // most kWaterField a side), its first tile at (x0, y0).
    void setWaterField(std::span<const std::uint32_t> texels, int w, int h);
    // Averages the scene's used `w` x `h` down to one texel for the exposure, one level a frame
    // (the exposure follows slowly; the chain refreshes every few frames for one draw each).
    // The exposure the final pass reads follows the mean smoothly (a share of the way each
    // frame); `snap`: the view jumped (a journey's arrival, a jump): the whole chain is measured
    // at once and taken as it is, so the destination is exposed right from its first frame.
    void measure(Batch& b, SDL_Texture* scene, int w, int h, bool snap);
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
    SDL_GPUShader* stampShader_ = nullptr;
    SDL_GPURenderState* stampState_ = nullptr;
    SDL_GPUShader* cloudShader_ = nullptr;
    SDL_GPURenderState* cloudState_ = nullptr;
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
    TexturePtr glow_;
    std::array<TexturePtr, kLevels> bloom_;
    TexturePtr falloff_;
    TexturePtr water_;  // the tile water field (static, updated when the view's region moves)
    TexturePtr clouds_; // the deck (r) and its shadows (g), a quarter of the scene
    bool cloudsClear_ = false;
    std::vector<TexturePtr> mean_; // kMeanSide wide, halved down to 1 x 1
    TexturePtr adapted_;           // 1 x 1: the mean the exposure follows, smoothed
    std::uint32_t measured_ = 0;   // frames since the path was made (the mean's cadence)
    SDL_BlendMode poolBlend_ = SDL_BLENDMODE_INVALID;
    SDL_BlendMode markBlend_ = SDL_BLENDMODE_INVALID;
    SDL_BlendMode coverBlend_ = SDL_BLENDMODE_INVALID;
    SDL_BlendMode stampBlend_ = SDL_BLENDMODE_INVALID;
};

} // namespace lc::gpu
