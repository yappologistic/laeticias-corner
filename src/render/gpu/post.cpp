#include "render/gpu/post.hpp"

#include "render/gpu/shaders.hpp"
#include "render/gpu/tuning.hpp"

#include <algorithm>
#include <cmath>
#include <string_view>
#include <vector>

namespace lc::gpu {
namespace {

// std140 mirror of shaders/final.frag's block: every member a vec4.
struct FinalUniforms {
    float gain[4];
    float shadow[4];
    float high[4];
    float haze[4];
    float mixes[4];
    float texel[4];
    float world[4];
    float night[4];
    float key[4];
    float pool[4];
    float guard[4];
    float water[4];
    float tiles[4];
    float shallow[4];
    float deep[4];
    float skyw[4];
    float cloud[4];
    float deck[4];
    float deckBase[4];
    float river[4];
};

// std140 mirror of shaders/clouds.frag's block.
struct CloudUniforms {
    float frame[4];
    float sun[4];
    float clouds[2 * tuning::kClouds][4];
    float billows[tuning::kClouds * tuning::kCloudBillows][4];
};

// std140 mirror of shaders/shade.frag's block.
struct ShadeUniforms {
    float tint[4];
};

// std140 mirror of the bloom shaders' block.
struct BloomUniforms {
    float texel[4];
};

void set4(float (&d)[4], float a, float b, float c, float e) {
    d[0] = a;
    d[1] = b;
    d[2] = c;
    d[3] = e;
}

int halve(int v, int times) {
    return std::max(1, v >> times);
}

} // namespace

SDL_GPUShader* makeFragmentShader(SDL_GPUDevice* device, std::string_view name, Uint32 samplers) {
    const std::span<const std::uint8_t> code = shader(name);
    if (code.empty()) return nullptr;
    SDL_GPUShaderCreateInfo info{};
    info.code_size = code.size();
    info.code = code.data();
    info.entrypoint = "main";
    info.format = SDL_GPU_SHADERFORMAT_SPIRV;
    info.stage = SDL_GPU_SHADERSTAGE_FRAGMENT;
    info.num_samplers = samplers;
    info.num_uniform_buffers = 1;
    SDL_GPUShader* s = SDL_CreateGPUShader(device, &info);
    if (s == nullptr)
        SDL_Log("gpu: shader %.*s: %s", static_cast<int>(name.size()), name.data(), SDL_GetError());
    return s;
}

RendererPtr createRenderer(SDL_Window* window) {
    // Vulkan takes the committed SPIR-V on Linux and Windows; the environment may still choose.
    if (!SDL_SetHint(SDL_HINT_GPU_DRIVER, "vulkan")) SDL_Log("gpu: %s", SDL_GetError());
    RendererPtr r{SDL_CreateGPURenderer(nullptr, window)};
    if (!r) return r;
    SDL_GPUDevice* device = SDL_GetGPURendererDevice(r.get());
    if (device == nullptr || (SDL_GetGPUShaderFormats(device) & SDL_GPU_SHADERFORMAT_SPIRV) == 0) {
        SDL_SetError("the gpu device takes no SPIR-V");
        r.reset();
    }
    return r;
}

bool isGpu(SDL_Renderer* renderer) {
    const char* name = SDL_GetRendererName(renderer);
    return name != nullptr && std::string_view(name) == "gpu";
}

std::unique_ptr<Post> Post::make(SDL_Renderer* renderer, Quality q) {
    if (q == Quality::Classic || !isGpu(renderer)) return nullptr;
    std::unique_ptr<Post> p(new Post(renderer));
    if (!p->init()) return nullptr;
    p->quality_ = q;
    if (!p->channelsRead()) {
        SDL_Log("gpu: a test draw read its colour channels out of order");
        return nullptr;
    }
    return p;
}

Post::Post(SDL_Renderer* renderer) : renderer_(renderer) {}

bool Post::init() {
    device_ = SDL_GetGPURendererDevice(renderer_);
    if (device_ == nullptr) return false;
    finalShader_ = makeFragmentShader(device_, "final", 6);
    cloudShader_ = makeFragmentShader(device_, "clouds", 1);
    shadeShader_ = makeFragmentShader(device_, "shade", 1);
    downShader_ = makeFragmentShader(device_, "bloom_down", 1);
    upShader_ = makeFragmentShader(device_, "bloom_up", 1);
    SDL_GPUSamplerCreateInfo si{};
    si.min_filter = SDL_GPU_FILTER_LINEAR;
    si.mag_filter = SDL_GPU_FILTER_LINEAR;
    si.mipmap_mode = SDL_GPU_SAMPLERMIPMAPMODE_NEAREST;
    si.address_mode_u = SDL_GPU_SAMPLERADDRESSMODE_CLAMP_TO_EDGE;
    si.address_mode_v = SDL_GPU_SAMPLERADDRESSMODE_CLAMP_TO_EDGE;
    si.address_mode_w = SDL_GPU_SAMPLERADDRESSMODE_CLAMP_TO_EDGE;
    linear_ = SDL_CreateGPUSampler(device_, &si);
    if (linear_ == nullptr) SDL_Log("gpu: sampler: %s", SDL_GetError());
    if (finalShader_ == nullptr || downShader_ == nullptr || upShader_ == nullptr ||
        shadeShader_ == nullptr || cloudShader_ == nullptr || linear_ == nullptr)
        return false;
    SDL_GPURenderStateCreateInfo si2{};
    si2.fragment_shader = shadeShader_;
    shadeState_ = SDL_CreateGPURenderState(renderer_, &si2);
    si2.fragment_shader = cloudShader_;
    cloudState_ = SDL_CreateGPURenderState(renderer_, &si2);
    // The tile water field: made once, at its largest, updated in place.
    water_.reset(SDL_CreateTexture(renderer_, kFormat, SDL_TEXTUREACCESS_STATIC,
                                   tuning::kWaterField, tuning::kWaterField));
    if (shadeState_ == nullptr || cloudState_ == nullptr || !water_ ||
        !SDL_SetTextureScaleMode(water_.get(), SDL_SCALEMODE_LINEAR)) {
        SDL_Log("gpu: render state: %s", SDL_GetError());
        return false;
    }
    // The scene's mean: kMeanSide x (side / 2), halved to one texel (cleared: a black night).
    for (int w = tuning::kMeanSide, h = tuning::kMeanSide / 2; w >= 1;
         w /= 2, h = std::max(1, h / 2)) {
        mean_.push_back(target(w, h));
        if (!mean_.back()) return false;
        begin(mean_.back().get());
    }
    adapted_ = target(1, 1);
    if (!adapted_) return false;
    begin(adapted_.get());
    // The falloff: (1 - r^2)^2 inside the unit disc, premultiplied white.
    constexpr int kSide = tuning::kPoolTexture;
    std::vector<std::uint32_t> px(static_cast<std::size_t>(kSide * kSide));
    for (int y = 0; y < kSide; ++y)
        for (int x = 0; x < kSide; ++x) {
            const float dx = (static_cast<float>(x) + 0.5f) / kSide * 2 - 1;
            const float dy = (static_cast<float>(y) + 0.5f) / kSide * 2 - 1;
            const float k = std::max(0.0f, 1.0f - (dx * dx + dy * dy));
            const auto v = static_cast<std::uint32_t>(k * k * 255.0f + 0.5f);
            px[static_cast<std::size_t>(y * kSide + x)] = v | v << 8 | v << 16 | v << 24;
        }
    falloff_.reset(SDL_CreateTexture(renderer_, kFormat, SDL_TEXTUREACCESS_STATIC, kSide, kSide));
    // Pools add their light to the glow target's alpha alone (colour stays the glow's).
    poolBlend_ = SDL_ComposeCustomBlendMode(SDL_BLENDFACTOR_ONE, SDL_BLENDFACTOR_ONE,
                                            SDL_BLENDOPERATION_ADD, SDL_BLENDFACTOR_ONE,
                                            SDL_BLENDFACTOR_ONE, SDL_BLENDOPERATION_ADD);
    // Water marks lower the cell's alpha under the sprite and leave its colour.
    markBlend_ = SDL_ComposeCustomBlendMode(SDL_BLENDFACTOR_ZERO, SDL_BLENDFACTOR_ONE,
                                            SDL_BLENDOPERATION_ADD, SDL_BLENDFACTOR_ONE,
                                            SDL_BLENDFACTOR_ONE, SDL_BLENDOPERATION_REV_SUBTRACT);
    if (!falloff_ || !SDL_UpdateTexture(falloff_.get(), nullptr, px.data(), kSide * 4) ||
        !SDL_SetTextureBlendMode(falloff_.get(), poolBlend_) ||
        !SDL_SetTextureBlendMode(falloff_.get(), SDL_BLENDMODE_ADD_PREMULTIPLIED)) {
        SDL_Log("gpu: falloff: %s", SDL_GetError());
        return false;
    }
    return true;
}

bool Post::channelsRead() {
    // A known colour through the final pass with a neutral grade must come back as it went in.
    TexturePtr src{SDL_CreateTexture(renderer_, kFormat, SDL_TEXTUREACCESS_STATIC, 2, 2)};
    TexturePtr dst = target(2, 2);
    const std::uint32_t red[4] = {0xFF2040E0u, 0xFF2040E0u, 0xFF2040E0u, 0xFF2040E0u}; // ABGR
    if (!src || !dst || !SDL_UpdateTexture(src.get(), nullptr, red, 8)) return false;
    prepare(2, 2);
    Batch b(renderer_);
    SDL_Texture* out = SDL_GetRenderTarget(renderer_);
    begin(glow_.get());
    for (int i = 0; i < kLevels; ++i) begin(bloom_[static_cast<std::size_t>(i)].get());
    if (!SDL_SetRenderTarget(renderer_, dst.get())) return false;
    const FinalParams f;
    final(b, src.get(), f, SDL_FRect{0, 0, 2, 2}, {0, 0, 1, 1}, false);
    b.flush();
    use(b, nullptr);
    const SDL_Rect one{0, 0, 1, 1};
    const SurfacePtr read{SDL_RenderReadPixels(renderer_, &one)};
    const SurfacePtr rgba{read ? SDL_ConvertSurface(read.get(), SDL_PIXELFORMAT_RGBA32) : nullptr};
    if (!SDL_SetRenderTarget(renderer_, out)) SDL_Log("gpu: %s", SDL_GetError());
    if (!rgba) return false;
    const auto* c = static_cast<const std::uint8_t*>(rgba->pixels);
    // In: r 0xE0, g 0x40, b 0x20. The grade moves the values; swapped channels (the ARGB
    // trap) would put blue on top.
    return c[0] > 0x60 && c[0] > 2 * c[2] && c[0] > c[1] && c[1] > c[2];
}

Post::~Post() {
    // Queued draws still point at the states: submit them before the states go (the R&D
    // round found heap corruption when GPU objects outlive their order).
    if (!SDL_SetGPURenderState(renderer_, nullptr) || !SDL_FlushRenderer(renderer_))
        SDL_Log("gpu: %s", SDL_GetError());
    for (SDL_GPURenderState* s : final_)
        if (s != nullptr) SDL_DestroyGPURenderState(s);
    if (shadeState_ != nullptr) SDL_DestroyGPURenderState(shadeState_);
    if (cloudState_ != nullptr) SDL_DestroyGPURenderState(cloudState_);
    for (std::size_t i = 0; i < kLevels; ++i) {
        if (down_[i] != nullptr) SDL_DestroyGPURenderState(down_[i]);
        if (up_[i] != nullptr) SDL_DestroyGPURenderState(up_[i]);
    }
    if (device_ == nullptr) return;
    for (SDL_GPUShader* s : {finalShader_, downShader_, upShader_, shadeShader_, cloudShader_})
        if (s != nullptr) SDL_ReleaseGPUShader(device_, s);
    if (linear_ != nullptr) SDL_ReleaseGPUSampler(device_, linear_);
}

TexturePtr Post::target(int w, int h) const {
    TexturePtr t{SDL_CreateTexture(renderer_, kFormat, SDL_TEXTUREACCESS_TARGET, w, h)};
    if (!t || !SDL_SetTextureBlendMode(t.get(), SDL_BLENDMODE_BLEND_PREMULTIPLIED) ||
        !SDL_SetTextureScaleMode(t.get(), SDL_SCALEMODE_LINEAR)) {
        SDL_Log("gpu: cannot create a target: %s", SDL_GetError());
        return {};
    }
    return t;
}

SDL_GPUTexture* Post::gpuOf(SDL_Texture* t) const {
    return static_cast<SDL_GPUTexture*>(SDL_GetPointerProperty(
        SDL_GetTextureProperties(t), SDL_PROP_TEXTURE_GPU_TEXTURE_POINTER, nullptr));
}

int Post::levels() const {
    if (quality_ == Quality::Low) return 0; // Low: the glow layer itself, no halo
    return quality_ == Quality::Medium ? tuning::kBloomLevelsMedium : tuning::kBloomLevelsHigh;
}

void Post::prepare(int w, int h) {
    if (glow_ && w <= w_ && h <= h_) return;
    w_ = std::max(w, w_);
    h_ = std::max(h, h_);
    glow_ = target(w_, h_);
    for (int i = 0; i < kLevels; ++i)
        bloom_[static_cast<std::size_t>(i)] = target(halve(w_, i + 1), halve(h_, i + 1));
    clouds_ = target(halve(w_, 2), halve(h_, 2));
    begin(clouds_.get());
    cloudsClear_ = true;
    usedW_ = usedH_ = 0;
    rebuildStates();
}

void Post::rebuildStates() {
    // Sampler bindings are fixed when a state is made: remade with the targets.
    const auto drop = [](SDL_GPURenderState*& s) {
        if (s != nullptr) SDL_DestroyGPURenderState(s);
        s = nullptr;
    };
    for (SDL_GPURenderState*& s : final_) drop(s);
    for (std::size_t i = 0; i < kLevels; ++i) {
        drop(down_[i]);
        drop(up_[i]);
    }
    if (!glow_ || !bloom_[0] || !clouds_) return;
    // SDL 3.4.20 takes at most five samplers beside the drawn texture (R&D round): all five.
    const SDL_GPUTextureSamplerBinding bind[5] = {{gpuOf(glow_.get()), linear_},
                                                  {gpuOf(bloom_[0].get()), linear_},
                                                  {gpuOf(adapted_.get()), linear_},
                                                  {gpuOf(water_.get()), linear_},
                                                  {gpuOf(clouds_.get()), linear_}};
    SDL_GPURenderStateCreateInfo info{};
    info.fragment_shader = finalShader_;
    info.num_sampler_bindings = 5;
    info.sampler_bindings = bind;
    for (SDL_GPURenderState*& s : final_) s = SDL_CreateGPURenderState(renderer_, &info);
    SDL_GPURenderStateCreateInfo bi{};
    for (std::size_t i = 0; i < kLevels; ++i) {
        bi.fragment_shader = downShader_;
        down_[i] = SDL_CreateGPURenderState(renderer_, &bi);
        bi.fragment_shader = upShader_;
        up_[i] = SDL_CreateGPURenderState(renderer_, &bi);
    }
    for (SDL_GPURenderState* s : final_)
        if (s == nullptr) SDL_Log("gpu: render state: %s", SDL_GetError());
}

void Post::shade(Batch& b, SDL_Texture* layer, SDL_FRect dst, UvRect uv, Rgb tint) {
    ShadeUniforms u{};
    set4(u.tint, tint.r, tint.g, tint.b, 0);
    if (!SDL_SetGPURenderStateFragmentUniforms(shadeState_, 0, &u, sizeof u))
        SDL_Log("gpu: %s", SDL_GetError());
    use(b, shadeState_);
    b.use(layer, SDL_BLENDMODE_MUL, SDL_SCALEMODE_NEAREST);
    b.quad(dst, uv, {1, 1, 1, 1});
    b.flush();
    use(b, nullptr);
}

void Post::use(Batch& b, SDL_GPURenderState* s) {
    if (s == current_) return;
    b.flush();
    if (!SDL_SetGPURenderState(renderer_, s)) SDL_Log("gpu: %s", SDL_GetError());
    current_ = s;
}

void Post::begin(SDL_Texture* t) {
    if (!SDL_SetRenderTarget(renderer_, t) || !SDL_SetRenderDrawColorFloat(renderer_, 0, 0, 0, 0) ||
        !SDL_RenderClear(renderer_))
        SDL_Log("gpu: %s", SDL_GetError());
}

void Post::bloom(Batch& b, int w, int h) {
    b.flush();
    const int n = levels();
    const auto size = [&](int level, bool used) {
        // Level 0 is the glow target itself; level k the (k-1)th halving.
        const int sw = used ? w : w_;
        const int sh = used ? h : h_;
        return std::pair{level == 0 ? sw : halve(sw, level), level == 0 ? sh : halve(sh, level)};
    };
    const auto tex = [&](int level) {
        return level == 0 ? glow_.get() : bloom_[static_cast<std::size_t>(level - 1)].get();
    };
    const auto uniforms = [&](SDL_GPURenderState* s, int src) {
        const auto [aw, ah] = size(src, false);
        const auto [uw, uh] = size(src, true);
        BloomUniforms u{};
        set4(u.texel, 0.5f / static_cast<float>(aw), 0.5f / static_cast<float>(ah),
             (static_cast<float>(uw) - 0.5f) / static_cast<float>(aw),
             (static_cast<float>(uh) - 0.5f) / static_cast<float>(ah));
        if (!SDL_SetGPURenderStateFragmentUniforms(s, 0, &u, sizeof u))
            SDL_Log("gpu: %s", SDL_GetError());
    };
    const bool fresh = w != usedW_ || h != usedH_;
    usedW_ = w;
    usedH_ = h;
    const auto pass = [&](SDL_GPURenderState* s, int src, int dst, SDL_BlendMode mode, float k) {
        const auto [aw, ah] = size(src, false);
        const auto [uw, uh] = size(src, true);
        const auto [dw, dh] = size(dst, true);
        if (!SDL_SetRenderTarget(renderer_, tex(dst))) SDL_Log("gpu: %s", SDL_GetError());
        use(b, s);
        b.use(tex(src), mode, SDL_SCALEMODE_LINEAR);
        b.quad(SDL_FRect{0, 0, static_cast<float>(dw), static_cast<float>(dh)},
               {0, 0, static_cast<float>(uw) / static_cast<float>(aw),
                static_cast<float>(uh) / static_cast<float>(ah)},
               {k, k, k, k});
        b.flush();
    };
    for (int i = 1; i <= n; ++i) {
        SDL_GPURenderState* s = down_[static_cast<std::size_t>(i - 1)];
        if (fresh) uniforms(s, i - 1);
        pass(s, i - 1, i, SDL_BLENDMODE_NONE, 1.0f);
    }
    for (int i = n; i > 1; --i) {
        SDL_GPURenderState* s = up_[static_cast<std::size_t>(i - 1)];
        if (fresh) uniforms(s, i);
        pass(s, i, i - 1, SDL_BLENDMODE_ADD_PREMULTIPLIED, tuning::kBloomUpWeight);
    }
    use(b, nullptr);
}

void Post::clouds(Batch& b, const CloudParams& p, int w, int h) {
    CloudUniforms u{};
    const int n = std::min<int>(static_cast<int>(p.clouds.size()), tuning::kClouds);
    set4(u.frame, p.origin.x, p.origin.y, p.worldPerTexel, static_cast<float>(n));
    set4(u.sun, p.sunShift.x, p.sunShift.y, p.altitude, 0);
    for (int i = 0; i < n; ++i) {
        const Cloud& c = p.clouds[static_cast<std::size_t>(i)];
        set4(u.clouds[2 * i], c.ground.x, c.ground.y, c.width, c.seed);
        set4(u.clouds[2 * i + 1], c.growth, c.dark, c.parallax.x, c.parallax.y);
        // Its billows, in widths: across the cloud, larger in the middle, lifted off the base.
        const auto hash = [](float v) {
            const float s = std::sin(v * 12.9898f) * 43758.5453f;
            return s - std::floor(s);
        };
        for (int k = 0; k < tuning::kCloudBillows; ++k) {
            const auto fk = static_cast<float>(k);
            const float across = fk / static_cast<float>(tuning::kCloudBillows - 1) - 0.5f;
            const float r =
                0.16f + 0.12f * (1.0f - std::abs(across) * 2.0f) + 0.05f * hash(c.seed + fk * 7.1f);
            set4(u.billows[i * tuning::kCloudBillows + k],
                 across * 0.62f + (hash(c.seed + fk * 3.3f) - 0.5f) * 0.08f,
                 -r * 0.55f - hash(c.seed + fk * 5.9f) * 0.06f, r, 0);
        }
    }
    if (!SDL_SetGPURenderStateFragmentUniforms(cloudState_, 0, &u, sizeof u))
        SDL_Log("gpu: %s", SDL_GetError());
    b.flush();
    if (!SDL_SetRenderTarget(renderer_, clouds_.get())) SDL_Log("gpu: %s", SDL_GetError());
    use(b, cloudState_);
    b.use(falloff_.get(), SDL_BLENDMODE_NONE, SDL_SCALEMODE_NEAREST);
    b.quad(SDL_FRect{0, 0, static_cast<float>(halve(w, 2)), static_cast<float>(halve(h, 2))},
           {0, 0, 1, 1}, {1, 1, 1, 1});
    b.flush();
    use(b, nullptr);
    cloudsClear_ = false;
}

void Post::noClouds() {
    if (cloudsClear_) return;
    begin(clouds_.get());
    cloudsClear_ = true;
}

void Post::setWaterField(std::span<const std::uint32_t> texels, int w, int h) {
    if (w > tuning::kWaterField || h > tuning::kWaterField ||
        static_cast<int>(texels.size()) < w * h)
        return;
    const SDL_Rect r{0, 0, w, h};
    if (!SDL_UpdateTexture(water_.get(), &r, texels.data(), w * 4))
        SDL_Log("gpu: water: %s", SDL_GetError());
}

void Post::measure(Batch& b, SDL_Texture* scene, int w, int h, bool snap) {
    // The first frame (and a jump's) fills the whole chain; then one level a frame, top to
    // bottom, so the mean is at most a chain's length of frames old for one draw a frame.
    const std::size_t levels = mean_.size();
    snap = snap || measured_ == 0;
    const std::size_t first = snap ? 0 : measured_ % levels;
    const std::size_t last = snap ? levels : first + 1;
    ++measured_;
    b.flush();
    use(b, nullptr);
    for (std::size_t i = first; i < last; ++i) {
        SDL_Texture* src = i == 0 ? scene : mean_[i - 1].get();
        float u = 1;
        float v = 1;
        if (i == 0) {
            u = static_cast<float>(w) / static_cast<float>(w_);
            v = static_cast<float>(h) / static_cast<float>(h_);
        }
        float tw = 0;
        float th = 0;
        if (!SDL_GetTextureSize(mean_[i].get(), &tw, &th) ||
            !SDL_SetRenderTarget(renderer_, mean_[i].get()))
            SDL_Log("gpu: %s", SDL_GetError());
        b.use(src, SDL_BLENDMODE_NONE, SDL_SCALEMODE_LINEAR);
        b.quad(SDL_FRect{0, 0, tw, th}, {0, 0, u, v}, {1, 1, 1, 1});
        b.flush();
    }
    // The exposure's mean moves a share of the way to the newest each frame (premultiplied:
    // k * mean + (1 - k) * adapted where the scene covers), all the way on a jump.
    const float k = snap ? 1.0f : tuning::kExposureFollow;
    if (!SDL_SetRenderTarget(renderer_, adapted_.get())) SDL_Log("gpu: %s", SDL_GetError());
    b.use(mean_.back().get(), snap ? SDL_BLENDMODE_NONE : SDL_BLENDMODE_BLEND_PREMULTIPLIED,
          SDL_SCALEMODE_NEAREST);
    b.quad(SDL_FRect{0, 0, 1, 1}, {0, 0, 1, 1}, {k, k, k, k});
    b.flush();
}

void Post::final(Batch& b, SDL_Texture* scene, const FinalParams& f, SDL_FRect dst, UvRect uv,
                 bool aux) {
    SDL_GPURenderState* s = final_[aux ? 1 : 0];
    if (s == nullptr) return;
    const GradePhase& g = f.grade;
    FinalUniforms u{};
    const float night =
        std::clamp((f.night - tuning::kNightFrom) / (1.0f - tuning::kNightFrom), 0.0f, 1.0f);
    // By day nothing says which pixels are in shade but the shadow layer (laid on by shade()), so
    // the split toning's cool darks stay off lit surfaces: they come in with the twilight. Lit
    // surfaces keep at least the art's saturation and lean a little warmer.
    // Full day only while the clock gives no glow; dawn and dusk are mostly twilight's.
    const float day =
        (1.0f - std::clamp(f.glow, 0.0f, 1.0f)) * (1.0f - std::clamp(f.glow, 0.0f, 1.0f));
    // By day never darker than the art (a darker day read as greyer, not deeper).
    const float exposure = g.exposure + (std::max(g.exposure, 1.0f) - g.exposure) * day;
    const float darks = 1.0f - day;
    // A low sun warms what it lights at dawn and dusk (honey, not lilac, on stone).
    const float low = (1.0f - day) * (1.0f - night) * tuning::kTwilightWarm;
    set4(u.gain, g.wb.r * exposure * (1.0f + low), g.wb.g * exposure,
         g.wb.b * exposure * (1.0f - low), g.tint);
    set4(u.shadow, (g.shadowTint.r - 0.5f) * darks, (g.shadowTint.g - 0.5f) * darks,
         (g.shadowTint.b - 0.5f) * darks, g.contrast);
    // Sunlit (day, dawn and dusk, not night): the warm lift and saturation floor hold.
    const float lit = 1.0f - night;
    const float sat =
        g.saturation + (std::max(g.saturation, 1.0f) + tuning::kDaySaturation - g.saturation) * lit;
    set4(u.high, g.highTint.r - 0.5f + tuning::kDayWarm[0] * lit,
         g.highTint.g - 0.5f + tuning::kDayWarm[1] * lit,
         g.highTint.b - 0.5f + tuning::kDayWarm[2] * lit, sat);
    set4(u.haze, f.haze.r, f.haze.g, f.haze.b,
         f.hazeStrength * (f.near ? 1.0f - (1.0f - tuning::kNearDayHaze) * day : 1.0f));
    set4(u.mixes, g.shoulder, tuning::kPoolGain, tuning::kPoolWarm,
         levels() == 0
             ? 0.0f
             : tuning::kBloomGain * (tuning::kBloomFloor + (1.0f - tuning::kBloomFloor) * f.glow));
    set4(u.texel, static_cast<float>(w_), static_cast<float>(h_), f.windowPerTarget,
         tuning::kGlowCore);
    set4(u.world, f.artOrigin.x, f.artOrigin.y, f.targetPerArt,
         static_cast<float>(tuning::kPoolLevels));
    const Rgb moon = nightTint();
    set4(u.night, moon.r, moon.g, moon.b, night * tuning::kNightCool);
    const auto lerp = [](float from, float to, float k) { return from + (to - from) * k; };
    const float twilight = std::clamp(f.glow, 0.0f, 1.0f);
    const float aim =
        lerp(lerp(tuning::kDayKey, tuning::kTwilightKey, twilight), tuning::kNightKey, night);
    set4(u.key, aim,
         lerp(lerp(tuning::kTwilightAdaptMin, tuning::kDayAdapt[0], day), tuning::kNightAdapt[0],
              night),
         lerp(tuning::kDayAdapt[1], tuning::kNightAdapt[1], night), day);
    set4(u.pool, 1.0f / tuning::kLightHeadroom, tuning::kLampColour[0], tuning::kLampColour[1],
         tuning::kLampColour[2]);
    set4(u.guard, tuning::kDaySaturationGrowth, f.grid.x, f.grid.y, 1.0f / f.horizonTiles);
    set4(u.water, f.waterAt.x, f.waterAt.y, 1.0f / static_cast<float>(tuning::kWaterField),
         1.0f / static_cast<float>(tuning::kWaterField));
    set4(u.tiles, f.halfTile.x, f.halfTile.y, f.levelPx,
         static_cast<float>(std::fmod(f.time, 3600.0)));
    set4(u.shallow, f.shallow.r, f.shallow.g, f.shallow.b, f.bands);
    set4(u.deep, f.deep.r, f.deep.g, f.deep.b, f.reflections ? 1.0f : 0.0f);
    set4(u.skyw, f.skyInWater.r, f.skyInWater.g, f.skyInWater.b, f.skyShare);
    set4(u.cloud, f.deckAlpha, f.cloudShadow, f.rain, f.glints);
    set4(u.deck, f.deckColour.r, f.deckColour.g, f.deckColour.b, 0);
    set4(u.deckBase, f.deckBase.r, f.deckBase.g, f.deckBase.b, 0);
    set4(u.river, f.river.r, f.river.g, f.river.b, 0);
    if (!SDL_SetGPURenderStateFragmentUniforms(s, 0, &u, sizeof u))
        SDL_Log("gpu: %s", SDL_GetError());
    use(b, s);
    b.use(scene, SDL_BLENDMODE_BLEND_PREMULTIPLIED, SDL_SCALEMODE_LINEAR);
    b.quad(dst, uv, {1, 1, 1, 1});
    b.flush();
    use(b, nullptr);
}

std::size_t Post::bytes() const {
    std::size_t n = static_cast<std::size_t>(w_) * static_cast<std::size_t>(h_) * 4;
    for (int i = 0; i < kLevels; ++i)
        n += static_cast<std::size_t>(halve(w_, i + 1)) *
             static_cast<std::size_t>(halve(h_, i + 1)) * 4;
    n += static_cast<std::size_t>(halve(w_, 2)) * static_cast<std::size_t>(halve(h_, 2)) * 4;
    n += static_cast<std::size_t>(tuning::kWaterField * tuning::kWaterField * 4);
    return n + static_cast<std::size_t>(tuning::kPoolTexture * tuning::kPoolTexture * 4);
}

} // namespace lc::gpu
