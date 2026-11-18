// WorldView's shader path (graphics plan task E1, src/render/gpu/README.md): the grade of the
// regions in view, the world's lamp pools and glow, bloom, wind sway and the final composite.
// Classic frames never reach this file.

#include "render/gpu/post.hpp"
#include "render/gpu/tuning.hpp"
#include "worldview/renderer.hpp"
#include "worldview/world_lights.hpp"

#include <algorithm>
#include <cmath>
#include <numbers>

namespace lc::worldview {
namespace {

bool contains(std::string_view s, std::string_view w) {
    return s.find(w) != std::string_view::npos;
}

// How far an item leans at its top in a full wind (art px), and whether it keeps its frames:
// trees, vines, reeds, crops and small plants bend; banners, awnings and parasols lean and keep
// their own flapping. Set items by their catalog's naming (`t_` trees and vines, `p_` plants),
// home items by their tags.
std::pair<float, bool> swayFor(const world::ItemInfo& info, const Catalog& home) {
    namespace t = gpu::tuning;
    const std::string_view id = info.id;
    if (contains(id, "hut") || contains(id, "_garden") || contains(id, "grove")) return {0, false};
    if (contains(id, "banner") || contains(id, "awning") || contains(id, "flag") ||
        contains(id, "parasol"))
        return {t::kSwayCloth, true};
    if (contains(id, "reed") || contains(id, "papyrus")) return {t::kSwayReeds, false};
    if (contains(id, "barley") || contains(id, "wheat") || contains(id, "steppe"))
        return {t::kSwayCrop, false};
    if (contains(id, "vine")) return {t::kSwayBush, false};
    if (contains(id, ".t_")) return {t::kSwayTree, false};
    for (const std::string_view plant : {"wildflowers", "poppy", "asphodel", "thyme", "lilies",
                                         "rose", "maquis", "thistle", "acanthus", "cabbage"})
        if (contains(id, ".p_" + std::string(plant))) return {t::kSwayBush, false};
    if (info.homeType >= 0) {
        const ItemDef& d = home.items[static_cast<std::size_t>(info.homeType)];
        for (const int tag : d.tags) {
            const std::string& name = home.tags[static_cast<std::size_t>(tag)];
            if (name == "tree") return {t::kSwayTree, false};
            if (name == "flower" || name == "crop") return {t::kSwayBush, false};
        }
    }
    return {0, false};
}

} // namespace

template <typename R, typename F>
void WorldView::forEachCarried(R&& rain, F&& f) {
    // Roles with `carries` hold their light while its hours hold (city life's actors drawn
    // this frame); the profile per (life region, role) is resolved once.
    if (life_ == nullptr || !lights_ || actorCount_ == 0) return;
    const life::LifeData& d = life_->lifeWorld().data;
    if (carried_.size() != d.regions.size()) {
        carried_.assign(d.regions.size(), {});
        for (std::size_t r = 0; r < d.regions.size(); ++r)
            for (const life::Role& role : d.regions[r].roles)
                carried_[r].push_back(static_cast<std::int16_t>(
                    role.carries.empty()
                        ? -1
                        : lights_->profileOf(d.regions[r].worldRegion, role.carries)));
    }
    for (std::size_t i = 0; i < actorCount_; ++i) {
        const life::DrawActor& a = actorBuf_[i];
        if (a.role < 0 || a.region >= carried_.size()) continue;
        const std::vector<std::int16_t>& roles = carried_[a.region];
        if (static_cast<std::size_t>(a.role) >= roles.size() ||
            roles[static_cast<std::size_t>(a.role)] < 0)
            continue;
        const auto profile = static_cast<std::uint16_t>(roles[static_cast<std::size_t>(a.role)]);
        const LightProfile& p = lights_->profiles()[profile];
        const Rgb c = lights_->colourOf(profile, a.handle.index * 2654435761U + a.handle.gen,
                                        p.rain == LightRain::Sheltered ? 0.0f : rain(a.pos));
        if (c.r + c.g + c.b <= 0.002f) continue;
        const Vec2 w = iso_.toWorld(a.pos.x, a.pos.y);
        const Vec2 feet{w.x, w.y - a.z};
        f(feet, Vec2{feet.x, feet.y - gpu::tuning::kCarriedHeight},
          Rgb{c.r * a.alpha, c.g * a.alpha, c.b * a.alpha}, p.radius);
    }
}

gpu::Quality WorldView::setQuality(gpu::Quality q) {
    if (q == gpu::Quality::Classic) {
        if (post_) {
            post_.reset();
            view_ = {}; // remade in the classic format
            shadow_ = {};
        }
        return q;
    }
    if (!post_) {
        post_ = gpu::Post::make(renderer_, q);
        if (!post_) {
            SDL_Log("look: no shader path on the '%s' renderer: the classic look",
                    SDL_GetRendererName(renderer_));
            return gpu::Quality::Classic;
        }
        view_ = {}; // remade in the format the shaders read
        shadow_ = {};
        reserveGpuTargets();
        if (!lights_) {
            lights_ = std::make_unique<WorldLights>(world_, *sprites_, hole_);
            if (lights_->unmatched() > 0)
                SDL_Log("look: %d light points name no item at their tile", lights_->unmatched());
        }
        if (regionLooks_.empty())
            for (const world::RegionFile& rf : world_.regions)
                regionLooks_.push_back(
                    gpu::parseLook(rf.theme.look, rf.theme.seasons, gpu::homeLook()));
        if (swayOf_.empty())
            for (const world::ItemInfo& info : map_.content().items()) {
                const auto [lean, frames] = swayFor(info, map_.content().home());
                swayOf_.push_back({lean, frames});
            }
    }
    post_->setQuality(q);
    return q;
}

void WorldView::reserveGpuTargets() {
    // Every target the path draws into, sized for the whole display at once: a window resized or
    // made fullscreen later never allocates in the middle of play (a 15 MiB target costs a driver
    // stall). Windowless renderers have their one size already.
    SDL_Window* win = SDL_GetRenderWindow(renderer_);
    const SDL_DisplayMode* m =
        win != nullptr ? SDL_GetDesktopDisplayMode(SDL_GetDisplayForWindow(win)) : nullptr;
    if (m == nullptr) return;
    const float density = m->pixel_density > 0 ? m->pixel_density : 1.0f;
    const int w = static_cast<int>(std::ceil(static_cast<float>(m->w) * density)) + 3;
    const int h = static_cast<int>(std::ceil(static_cast<float>(m->h) * density)) + 3;
    ensure(view_, w, h);
    ensure(shadow_, w, h);
    post_->prepare(view_.w, view_.h);
}

gpu::Quality WorldView::quality() const {
    return post_ ? post_->quality() : gpu::Quality::Classic;
}

void WorldView::setWind(Vec2 dir, float strength, bool reduceMotion) {
    // Grid direction to world px.
    const Vec2 w{(dir.x - dir.y) * iso_.hw, (dir.x + dir.y) * iso_.hh};
    const float n = std::hypot(w.x, w.y);
    windDir_ = n > 1e-4f ? Vec2{w.x / n, w.y / n} : Vec2{1, 0};
    windStrength_ = std::max(gpu::tuning::kWindFloor, std::clamp(strength, 0.0f, 1.0f)) *
                    (reduceMotion ? 0.5f : 1.0f);
}

void WorldView::mapLights(std::vector<std::pair<Vec2, float>>& out) const {
    out.clear();
    if (!post_ || !lights_) return;
    // One point per map chunk with burning lights, at their middle, brighter for more.
    const int cw = map_.chunksX();
    mapSums_.assign(static_cast<std::size_t>(cw * map_.chunksY()), {});
    lights_->forEachBurning([&](Vec2 tile, Rgb c) {
        const int cx = std::clamp(static_cast<int>(tile.x) >> kChunkShift, 0, cw - 1);
        const int cy = std::clamp(static_cast<int>(tile.y) >> kChunkShift, 0, map_.chunksY() - 1);
        auto& s = mapSums_[static_cast<std::size_t>(cy * cw + cx)];
        const float k = (c.r + c.g + c.b) / 3.0f;
        s.first.x += tile.x * k;
        s.first.y += tile.y * k;
        s.second += k;
    });
    for (const auto& [at, k] : mapSums_)
        if (k > 0.01f)
            out.emplace_back(Vec2{at.x / k, at.y / k},
                             std::min(1.0f, k / gpu::tuning::kMapLightFull));
}

bool WorldView::glowing(std::uint32_t item) const {
    return !post_ || !lights_ || lights_->glowOn(item);
}

void WorldView::gradeGpu(double clock, double now, const Lighting& light, Lod lod, Vec2 origin) {
    int season = -1;
    const Catalog& home = map_.content().home();
    if (season_ >= 0 && static_cast<std::size_t>(season_) < home.seasons.size())
        for (int i = 0; i < gpu::kSeasons; ++i)
            if (gpu::kSeasonIds[static_cast<std::size_t>(i)] ==
                home.seasons[static_cast<std::size_t>(season_)].id)
                season = i;
    const int lodIndex = static_cast<int>(lod);
    gpu::GradeAt acc = gpu::scaled(gpu::gradeAt(gpu::homeLook(), clock, season, lodIndex), 0);
    float total = 0;
    for (std::size_t i = 0; i < regionLooks_.size(); ++i) {
        const float w = theme_.weight(static_cast<int>(i));
        if (w <= 1e-4f) continue;
        gpu::accumulate(acc, gpu::gradeAt(regionLooks_[i], clock, season, lodIndex), w);
        total += w;
    }
    // Where no region claims the view (the corner and its surroundings), the home's look.
    if (total < 1.0f) {
        gpu::accumulate(acc, gpu::gradeAt(gpu::homeLook(), clock, season, lodIndex), 1.0f - total);
        total = 1.0f;
    }
    gpuFrame_ = {gpu::scaled(acc, 1.0f / total),
                 light.glow,
                 light.night,
                 lod == Lod::Native,
                 origin,
                 res_,
                 now};
    lights_->update(clock, now, life_);
}

void WorldView::lightGpu(const FRect& view, const Xform& x, Lod lod, float glow, const Hooks& hooks,
                         const FrameInfo& frame, bool home) {
    namespace t = gpu::tuning;
    batch_.flush();
    // The home's scene keeps its moths and its light map neutral: the world's light is ours.
    if (hooks.light && home) {
        FrameInfo neutral = frame;
        neutral.ambient = {1, 1, 1, 1};
        hooks.light(neutral);
        batch_.flush();
    }
    post_->begin(post_->glow());
    if (lod != Lod::Overview) {
        // A pool is an ellipse on the ground ((1 - (d/R)^2)^2 inside R tiles) below its centre,
        // and above it fades up the walls behind to near the flame's height. Pools add into the
        // glow target's alpha (one warm colour, tuning::kLampColour), all in one draw.
        const float day =
            (t::kPoolDay + (1.0f - t::kPoolDay) * std::clamp(glow, 0.0f, 1.0f)) * t::kLightHeadroom;
        const float ax = std::numbers::sqrt2_v<float> * iso_.hw;
        const float ay = std::numbers::sqrt2_v<float> * iso_.hh;
        const auto pool = [&](Vec2 ground, float height, float radius, float k) {
            const float a = radius * ax * x.res;
            const float b = radius * ay * x.res;
            const float up = b + std::max(0.0f, height) * t::kPoolRise * x.res;
            const Vec2 g = x.apply(ground);
            const SDL_FColor col{0, 0, 0, k * day};
            const SDL_FColor top{0, 0, 0, k * day * t::kPoolWall};
            // Above the centre stand walls as often as ground: the light fades toward the top,
            // so a white wall behind a flame is warmed, not turned into a lit block.
            const SDL_Vertex v[8] = {
                {{g.x - a, g.y - up}, top, {0, 0}}, {{g.x + a, g.y - up}, top, {1, 0}},
                {{g.x + a, g.y}, col, {1, 0.5f}},   {{g.x - a, g.y}, col, {0, 0.5f}},
                {{g.x - a, g.y}, col, {0, 0.5f}},   {{g.x + a, g.y}, col, {1, 0.5f}},
                {{g.x + a, g.y + b}, col, {1, 1}},  {{g.x - a, g.y + b}, col, {0, 1}}};
            static constexpr int kQuads[12] = {0, 1, 2, 0, 2, 3, 4, 5, 6, 4, 6, 7};
            batch_.triangles(v, 8, kQuads, 12);
        };
        const auto rain = [&](Vec2 tile) {
            return weather_ != nullptr ? weather_->rainAt(tile) : 0.0f;
        };
        refreshPools(view, rain);
        batch_.use(post_->falloff(), post_->poolBlend(), SDL_SCALEMODE_LINEAR);
        for (const PoolLight& l : pools_)
            pool(l.ground, l.height, l.radius, l.base * lights_->flickerOf(l.profile, l.seed));
        const auto strength = [](Rgb c) {
            const float lamp = 0.299f * t::kLampColour[0] + 0.587f * t::kLampColour[1] +
                               0.114f * t::kLampColour[2];
            return (0.299f * c.r + 0.587f * c.g + 0.114f * c.b) / lamp;
        };
        if (home && hooks.lamps && glow > 0.01f)
            // The home's lamps burn with the clock's glow; their reach is in world px.
            for (const HomeLamp& lamp : hooks.lamps())
                pool(lamp.at, 0, lamp.radius / (ax * 1.4f), glow);
        forEachCarried(rain, [&](Vec2 feet, Vec2, Rgb c, float radius) {
            pool(feet, t::kCarriedHeight, radius, strength(c));
        });
        batch_.flush();
        // The carried flame itself (the walker art has no glow frames yet): a small warm point
        // at the hand, bloomed with the rest.
        const float r = std::max(1.5f, t::kCarriedFlame * x.res);
        batch_.use(post_->falloff(), SDL_BLENDMODE_ADD_PREMULTIPLIED, SDL_SCALEMODE_LINEAR);
        forEachCarried([](Vec2) { return 0.0f; },
                       [&](Vec2, Vec2 hand, Rgb c, float) {
                           const Vec2 p = x.apply(hand);
                           batch_.quad(SDL_FRect{p.x - r, p.y - r, 2 * r, 2 * r}, {0, 0, 1, 1},
                                       {c.r * 1.5f, c.g * 1.5f, c.b * 1.5f, 1});
                       });
        batch_.flush();
    }
}

template <typename R>
void WorldView::refreshPools(const FRect& view, R&& rain) {
    // The visible chunks' lights with their slow part (hours, strength, festival, rain) kept
    // between frames: rebuilt when the view crosses a chunk, the hour moves on a step, or every
    // few frames for the rain; only the flicker is per frame.
    namespace t = gpu::tuning;
    TileRect tiles = gatherTiles(view, sprites_->itemSpan(), iso_);
    const int margin = 13; // the widest pool's reach, tiles
    constexpr int kMask = ~((1 << kChunkShift) - 1);
    tiles = {(tiles.x0 - margin) & kMask, (tiles.y0 - margin) & kMask,
             ((tiles.x1 + margin) & kMask) + (1 << kChunkShift),
             ((tiles.y1 + margin) & kMask) + (1 << kChunkShift)};
    const int step = static_cast<int>(lights_->hour() / t::kPoolHourStep);
    if (tiles.x0 == poolTiles_.x0 && tiles.y0 == poolTiles_.y0 && tiles.x1 == poolTiles_.x1 &&
        tiles.y1 == poolTiles_.y1 && step == poolStep_ && ++poolAge_ < t::kPoolRefreshFrames)
        return;
    poolTiles_ = tiles;
    poolStep_ = step;
    poolAge_ = 0;
    pools_.clear();
    const float lamp =
        0.299f * t::kLampColour[0] + 0.587f * t::kLampColour[1] + 0.114f * t::kLampColour[2];
    lights_->forEachBase(tiles, rain, [&](const WorldLight& l, float base) {
        const Rgb c = lights_->profiles()[l.profile].colour;
        pools_.push_back({l.ground, l.ground.y - l.at.y, lights_->profiles()[l.profile].radius,
                          base * (0.299f * c.r + 0.587f * c.g + 0.114f * c.b) / lamp, l.seed,
                          l.profile});
    });
}

void WorldView::bloomGpu(const FRect& view, const Xform& x, Lod lod, float glow) {
    namespace t = gpu::tuning;
    if (lod == Lod::Overview && glow > 0.01f) {
        // From afar every light is a warm point a few window px across, so towns sparkle.
        const float windowPerTarget = present_.valid ? present_.scale / x.res : 1.0f;
        const float r =
            std::max(t::kFarLightPx / std::max(windowPerTarget, 1e-3f), t::kFarLightWorld * x.res);
        batch_.use(post_->falloff(), SDL_BLENDMODE_ADD_PREMULTIPLIED, SDL_SCALEMODE_LINEAR);
        const TileRect tiles = gatherTiles(view, sprites_->itemSpan(), iso_);
        lights_->forEach(
            tiles, [](Vec2) { return 0.0f; },
            [&](const WorldLight& l, Rgb c, float) {
                const Vec2 p = x.apply(l.at);
                const float k = glow * 1.6f;
                batch_.quad(SDL_FRect{p.x - r, p.y - r, 2 * r, 2 * r}, {0, 0, 1, 1},
                            {c.r * k, c.g * k, c.b * k, 1});
            });
        batch_.flush();
    }
    post_->bloom(batch_, viewW_, viewH_);
    post_->measure(batch_, view_.texture.get(), viewW_, viewH_);
    if (!SDL_SetRenderTarget(renderer_, view_.texture.get())) SDL_Log("look: %s", SDL_GetError());
}

void WorldView::compositeGpu(Vec2 scale, bool smooth) {
    const Present& p = present_;
    const float w = p.screen.x * scale.x;
    const float h = p.screen.y * scale.y;
    // The sky in three stops, top to horizon (the regions' `theme.look.sky`).
    const auto col = [](Rgb c) { return SDL_FColor{c.r, c.g, c.b, 1}; };
    const std::array<Rgb, 3>& sky = gpuFrame_.grade.sky;
    const float mid = h * 0.6f;
    const SDL_Vertex v[6] = {{{0, 0}, col(sky[0]), {0, 0}},   {{w, 0}, col(sky[0]), {0, 0}},
                             {{w, mid}, col(sky[1]), {0, 0}}, {{0, mid}, col(sky[1]), {0, 0}},
                             {{w, h}, col(sky[2]), {0, 0}},   {{0, h}, col(sky[2]), {0, 0}}};
    static constexpr int kSky[12] = {0, 1, 2, 0, 2, 3, 3, 2, 4, 3, 4, 5};
    batch_.use(nullptr, SDL_BLENDMODE_NONE);
    batch_.triangles(v, 6, kSky, 12);
    const float k = p.scale / p.res; // window px per target px
    gpu::FinalParams f;
    f.grade = gpuFrame_.grade.grade;
    f.haze = gpuFrame_.grade.haze;
    f.hazeStrength = gpuFrame_.grade.hazeStrength;
    f.glow = gpuFrame_.glow;
    f.night = gpuFrame_.night;
    f.near = gpuFrame_.near;
    f.windowPerTarget = k * scale.x;
    f.artOrigin = gpuFrame_.artOrigin;
    f.targetPerArt = gpuFrame_.res;
    post_->final(batch_, view_.texture.get(), f,
                 SDL_FRect{(p.origin.x - p.topLeft.x) * p.scale * scale.x,
                           (p.origin.y - p.topLeft.y) * p.scale * scale.y,
                           static_cast<float>(viewW_) * k * scale.x,
                           static_cast<float>(viewH_) * k * scale.y},
                 {0, 0, static_cast<float>(viewW_) / static_cast<float>(view_.w),
                  static_cast<float>(viewH_) / static_cast<float>(view_.h)},
                 smooth || scale.x != 1.0f || scale.y != 1.0f);
}

void WorldView::shadeGpu(SDL_Texture* layer, float w, float h) {
    // Full shade: the classic darkening, its colour leaning to the region's shade colour (luma
    // kept) by tuning::kShadeTint.
    const float k = shadowOpacity();
    const Rgb s = gpuFrame_.grade.shade;
    const float l = std::max(1e-3f, 0.299f * s.r + 0.587f * s.g + 0.114f * s.b);
    const auto tint = [&](float c) {
        return (1.0f - k) * (1.0f + (c / l - 1.0f) * gpu::tuning::kShadeTint);
    };
    post_->shade(batch_, layer, SDL_FRect{0, 0, w, h}, {0, 0, 1, 1},
                 {tint(s.r), tint(s.g), tint(s.b)});
}

void WorldView::putSwaying(const SpriteRef& s, Vec2 anchor, const Xform& x, float lean) {
    // Rows shift sideways by the wind, more toward the top (by the square of the height), the
    // base still: whole sprites sway with no extra frames. Downwind on screen, never against.
    SDL_Texture* t = pages_->texture(s.page);
    if (t == nullptr) return;
    const float side = windDir_.x >= 0 ? 1.0f : -1.0f;
    const float dx = lean * side * (0.4f + 0.6f * std::abs(windDir_.x)) *
                     gpu::windLean(anchor, gpuFrame_.now, windDir_, windStrength_);
    constexpr int kStrips = gpu::tuning::kSwayStrips;
    const float x0 = anchor.x - s.ox;
    const float y0 = anchor.y - s.oy;
    std::vector<SDL_Vertex>& verts = batch_.scratch().verts;
    std::vector<int>& idx = batch_.scratch().indices;
    verts.clear();
    idx.clear();
    for (int i = 0; i <= kStrips; ++i) {
        const float f = static_cast<float>(i) / static_cast<float>(kStrips);
        const float wy = y0 + s.h * f;
        const float up = std::clamp((anchor.y - wy) / std::max(s.h, 1.0f), 0.0f, 1.0f);
        const float vv = s.uv.v0 + (s.uv.v1 - s.uv.v0) * f;
        for (int k = 0; k < 2; ++k) {
            const Vec2 p = x.apply({x0 + (k == 0 ? 0 : s.w) + dx * up * up, wy});
            verts.push_back({{p.x, p.y}, {1, 1, 1, 1}, {k == 0 ? s.uv.u0 : s.uv.u1, vv}});
        }
        if (i > 0) {
            const int b = 2 * (i - 1);
            for (const int q : {b, b + 1, b + 3, b, b + 3, b + 2}) idx.push_back(q);
        }
    }
    batch_.use(t, SDL_BLENDMODE_BLEND, x.filter);
    batch_.triangles(verts.data(), static_cast<int>(verts.size()), idx.data(),
                     static_cast<int>(idx.size()));
}

} // namespace lc::worldview
