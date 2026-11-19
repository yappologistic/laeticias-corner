// WorldView's shader path (graphics plan task E1, src/render/gpu/README.md): the grade of the
// regions in view, the world's lamp pools and glow, bloom, wind sway and the final composite.
// Classic frames never reach this file.

#include "render/gpu/post.hpp"
#include "render/gpu/tuning.hpp"
#include "worldview/cells.hpp"
#include "worldview/renderer.hpp"
#include "worldview/tuning.hpp"
#include "worldview/world_lights.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <future>
#include <numbers>

namespace lc::worldview {
namespace {

bool contains(std::string_view s, std::string_view w) {
    return s.find(w) != std::string_view::npos;
}

bool byRow(TilePos a, TilePos b) {
    return a.y != b.y ? a.y < b.y : a.x < b.x;
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
        // A new path has an empty water field: built again on the next frame.
        if (waterJob_.valid()) waterJob_.get();
        waterTexels_.clear();
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

void WorldView::refreshWater(const FRect& view) {
    namespace t = gpu::tuning;
    const TileRect seen = tilesUnder(view, iso_);
    constexpr int kNear = 4;   // tiles the view may near the field's edge before it is remade
    constexpr int kAhead = 16; // tiles held beyond the view each side
    const TileRect need{seen.x0 - kNear, seen.y0 - kNear, seen.x1 + kNear, seen.y1 + kNear};
    if (waterJob_.valid()) {
        // A field on its way: taken when ready; waited for only when the view left both fields
        // (a jump).
        const bool ready = waterJob_.wait_for(std::chrono::seconds(0)) == std::future_status::ready;
        if (!ready && waterPending_.contains(need)) return;
        waterJob_.get();
        waterRect_ = waterPending_;
        post_->setWaterField(waterTexels_, waterRect_.x1 - waterRect_.x0,
                             waterRect_.y1 - waterRect_.y0);
    }
    if (!waterTexels_.empty() && waterRect_.contains(need) && !waterStale_) return;
    // The items' water tiles (basins, harbours), once.
    if (!itemWaterRead_) {
        itemWaterRead_ = true;
        for (const world::Placed& it : map_.items())
            if (const world::GeomVariant* g = map_.geometry(it); g != nullptr)
                for (const TilePos t : g->water) itemWater_.push_back({it.x + t.x, it.y + t.y});
        std::ranges::sort(itemWater_, byRow);
    }
    // Per terrain: 0 land, 1 water, 2 a channel (rivers, canals: clear, flowing, no foam).
    if (waterKind_.size() != map_.terrainCount()) {
        waterKind_.resize(map_.terrainCount());
        for (std::size_t k = 0; k < waterKind_.size(); ++k) {
            const int tt = static_cast<int>(k);
            const std::string_view id = map_.terrainInfo(tt).id;
            waterKind_[k] = !sprites_->terrain(tt).water ? std::uint8_t{0}
                            : flowingWater(id)           ? std::uint8_t{2}
                                                         : std::uint8_t{1};
        }
    }
    const auto side = [&](int a0, int a1) {
        const int c = (a0 + a1) / 2;
        const int n = std::min(t::kWaterField, a1 - a0 + 2 * kAhead);
        return std::pair{c - n / 2, c - n / 2 + n};
    };
    const auto [x0, x1] = side(seen.x0, seen.x1);
    const auto [y0, y1] = side(seen.y0, seen.y1);
    const TileRect rect{x0, y0, x1, y1};
    // Panning, the next field is built on a worker while this one serves (its margin is ahead of
    // the view); the first field, a jump and scripted runs build it at once.
    waterStale_ = false;
    if (async_ && !waterTexels_.empty() && waterRect_.intersects(need)) {
        waterPending_ = rect;
        waterJob_ = std::async(std::launch::async, [this, rect] { buildWater(rect); });
        return;
    }
    buildWater(rect);
    waterRect_ = rect;
    post_->setWaterField(waterTexels_, x1 - x0, y1 - y0);
}

void WorldView::buildWater(TileRect rect) {
    // Reads only the immutable map and the per-terrain table; writes only the field's buffers.
    namespace t = gpu::tuning;
    constexpr int kPad = 10; // tiles of land read beyond the field (shore distances reach 9)
    const auto [x0, y0, x1, y1] = rect;
    // The padded block (a one-tile land-free border keeps the passes free of bounds checks).
    const int w = x1 - x0 + 2 * kPad + 2;
    const int h = y1 - y0 + 2 * kPad + 2;
    const int bx = x0 - kPad - 1;
    const int by = y0 - kPad - 1;
    constexpr float kFar = 99;
    const auto kindAt = [&](int x, int y) -> std::uint8_t {
        const TilePos p{bx + x, by + y};
        if (!map_.inBounds(p)) return sea_ >= 0 ? 1 : 0;
        const int tt = map_.terrainAt(p);
        const std::uint8_t k =
            tt == world::kNone ? std::uint8_t{0} : waterKind_[static_cast<std::size_t>(tt)];
        return k != 0 || itemWater_.empty() || !std::ranges::binary_search(itemWater_, p, byRow)
                   ? k
                   : std::uint8_t{1};
    };
    waterDist_.resize(static_cast<std::size_t>(w * h));
    float* d = waterDist_.data();
    for (int y = 0; y < h; ++y)
        for (int x = 0; x < w; ++x)
            d[y * w + x] = x == 0 || y == 0 || x == w - 1 || y == h - 1 ? kFar
                           : kindAt(x, y) != 0                          ? kFar
                                                                        : 0.0f;
    // Chamfered distance to the nearest land in tiles (land 0, water from 1), two passes.
    const float diag = std::numbers::sqrt2_v<float>;
    for (int y = 1; y < h - 1; ++y)
        for (int x = 1; x < w - 1; ++x) {
            float& v = d[y * w + x];
            if (v == 0.0f) continue;
            const float* up = d + (y - 1) * w + x;
            v = std::min({v, d[y * w + x - 1] + 1, up[0] + 1, up[-1] + diag, up[1] + diag});
        }
    for (int y = h - 2; y > 0; --y)
        for (int x = w - 2; x > 0; --x) {
            float& v = d[y * w + x];
            if (v == 0.0f) continue;
            const float* dn = d + (y + 1) * w + x;
            v = std::min({v, d[y * w + x + 1] + 1, dn[0] + 1, dn[1] + diag, dn[-1] + diag});
        }
    // Texels: r the shore distance ((d + 0.5) / 10, land -0.5), g b the flow (rivers by their aux
    // direction, tiles per second), a the flags (bit 7 water, bit 6 a channel, bits 0-3 the
    // level).
    const int fw = x1 - x0;
    const int fh = y1 - y0;
    waterTexels_.resize(static_cast<std::size_t>(fw * fh));
    const auto byte = [](float v) {
        return static_cast<std::uint32_t>(std::clamp(v, 0.0f, 1.0f) * 255.0f + 0.5f);
    };
    static constexpr float kDir[4][2] = {{0, -1}, {1, 0}, {0, 1}, {-1, 0}};
    constexpr std::uint32_t kStill = 128u << 8 | 128u << 16;
    for (int y = 0; y < fh; ++y)
        for (int x = 0; x < fw; ++x) {
            const TilePos p{x0 + x, y0 + y};
            const float dist = d[(y + kPad + 1) * w + x + kPad + 1];
            std::uint32_t texel = byte((std::max(dist - 0.5f, -0.5f) + 1.0f) / 10.0f) | kStill;
            if (dist > 0) texel |= 128u << 24;
            if (map_.inBounds(p)) {
                const std::uint8_t lb = map_.levelByte(p);
                texel |= static_cast<std::uint32_t>(world::levelOf(lb) & 15) << 24;
                const int tt = map_.terrainAt(p);
                if (dist > 0 && tt != world::kNone &&
                    waterKind_[static_cast<std::size_t>(tt)] == 2) {
                    const int a = world::auxOf(lb) & 3;
                    texel = (texel & 0xff0000ffu) |
                            byte(kDir[a][0] * t::kRiverSpeed * 0.5f + 0.5f) << 8 |
                            byte(kDir[a][1] * t::kRiverSpeed * 0.5f + 0.5f) << 16 | 64u << 24;
                }
            }
            waterTexels_[static_cast<std::size_t>(y * fw + x)] = texel;
        }
}

void WorldView::homeTerrainChanged() {
    // The workers read the map's home tiles: they finish before they change.
    if (seasonJob_.valid()) seasonJob_.wait();
    if (waterJob_.valid()) {
        waterJob_.get();
        waterRect_ = waterPending_;
        if (post_)
            post_->setWaterField(waterTexels_, waterRect_.x1 - waterRect_.x0,
                                 waterRect_.y1 - waterRect_.y0);
    }
    waterStale_ = true;
    homeWaterDirty_ = true;
}

void WorldView::markItemWater(const Elem& e, const Xform& x) {
    // With the packed pages every water texel marks itself as it draws.
    if (decoder_ || e.ground || e.figure || e.home) return;
    const world::GeomVariant* g = map_.geometry(map_.items()[e.item]);
    if (g == nullptr || g->water.empty()) return;
    const bool piece = e.piece >= 0 && static_cast<std::size_t>(e.piece) < g->pieces.size();
    const auto in = [&](TilePos t) {
        return !piece || g->pieces[static_cast<std::size_t>(e.piece)].rect.contains(t);
    };
    const auto mark = [&](TilePos t, bool maybe) {
        markWater(sprites_->diamond(),
                  {e.anchor.x + static_cast<float>(t.x - t.y) * iso_.hw,
                   e.anchor.y + static_cast<float>(t.x + t.y) * iso_.hh},
                  maybe);
    };
    // The water tiles, and the rim round them (the art's water reaches into the tiles of the
    // quay: there, only water-coloured pixels count).
    rimScratch_.clear();
    for (const TilePos t : g->water) {
        if (in(t)) mark(t, false);
        for (int dy = -1; dy <= 1; ++dy)
            for (int dx = -1; dx <= 1; ++dx) rimScratch_.push_back({t.x + dx, t.y + dy});
    }
    std::ranges::sort(rimScratch_, byRow);
    const auto [first, last] = std::ranges::unique(rimScratch_);
    rimScratch_.erase(first, last);
    for (const TilePos t : rimScratch_)
        if (in(t) && std::ranges::find(g->water, t) == g->water.end()) mark(t, true);
    flushMarks(x);
}

void WorldView::markHomeWater(const FRect& view, const Xform& x) {
    if (decoder_ && pages_->homePackedReady()) return; // its water texels mark themselves
    if (homeWaterDirty_ && !waterKind_.empty()) {
        homeWaterDirty_ = false;
        homeWater_.clear();
        const TileRect& h = hole_.tiles;
        for (int y = h.y0; y < h.y1; ++y)
            for (int tx = h.x0; tx < h.x1; ++tx) {
                const TilePos p{tx, y};
                const int tt = map_.inBounds(p) ? map_.terrainAt(p) : world::kNone;
                if (tt != world::kNone && waterKind_[static_cast<std::size_t>(tt)] != 0)
                    homeWater_.push_back(p);
            }
    }
    for (const TilePos p : homeWater_) {
        const Vec2 w = iso_.toWorld(p);
        const Vec2 a{w.x, w.y - static_cast<float>(map_.level(p) * lvl_)};
        if (a.x + iso_.hw < view.x0 || a.x - iso_.hw > view.x1 || a.y + iso_.tileH() < view.y0 ||
            a.y > view.y1)
            continue;
        markWater(sprites_->diamond(), a);
    }
    flushMarks(x);
}

void WorldView::sunGpu(double clock) {
    namespace t = gpu::tuning;
    const gpu::Quality q = post_->quality();
    const bool lit = q == gpu::Quality::Medium || q == gpu::Quality::High;
    if (!lit) {
        sunShadows_.reset();
        if (decoder_ && sunStep_ != -1) {
            const float up[3] = {0, 0, 1};
            decoder_->setSun(up, 0, 0);
            sunStep_ = -1;
            setSlopeSun(up, 0);
            staleCells();
        }
        return;
    }
    const int season = gpuFrame_.season;
    // The shadows the sun throws now, drawn each frame at the native level.
    // (As the sun goes down they ease back to the baked ones: no sun, no turning.)
    const gpu::Sun live = gpu::sunAt(clock, season);
    gpu::ShadowWarp warp = gpu::shadowWarp(live);
    const float id[4] = {1, 0, 0, 1};
    for (int i = 0; i < 4; ++i) warp.m[i] = id[i] + (warp.m[i] - id[i]) * live.strength;
    sunShadows_ = warp;
    // The relight and cached pictures (impostors' shadows too) by the sun of the step.
    const int step = static_cast<int>(std::floor(std::fmod(clock + 1.0, 1.0) * t::kSunSteps));
    if (step == sunStep_) return;
    sunStep_ = step;
    const gpu::Sun sun = gpu::sunAt((static_cast<double>(step) + 0.5) / t::kSunSteps, season);
    stepShadows_ = gpu::shadowWarp(sun);
    for (int i = 0; i < 4; ++i)
        stepShadows_.m[i] = id[i] + (stepShadows_.m[i] - id[i]) * sun.strength;
    if (decoder_) decoder_->setSun(sun.dir, sun.strength, t::kContact);
    setSlopeSun(sun.dir, sun.strength);
    staleCells();
}

bool WorldView::putShadow(const SpriteRef& s, const Elem& e, const Xform& x) {
    if (dry_) return true;
    SDL_Texture* tex = pages_->texture(s.page);
    if (tex == nullptr) return false;
    // Cached pictures take the stepped sun's shadows; the live frame the sun as it is.
    const gpu::ShadowWarp& w = drawingBlock_ ? stepShadows_ : *sunShadows_;
    const world::Placed& it = map_.items()[e.item];
    const TileRect r = it.rect();
    const auto fw = static_cast<float>(r.x1 - r.x0);
    const auto fh = static_cast<float>(r.y1 - r.y0);
    const Vec2 pivot{e.anchor.x + (fw - fh) * iso_.hw * 0.5f,
                     e.anchor.y + (fw + fh) * iso_.hh * 0.5f};
    constexpr int kGrid = 2;
    std::vector<SDL_Vertex>& verts = batch_.scratch().verts;
    std::vector<int>& idx = batch_.scratch().indices;
    verts.clear();
    idx.clear();
    const float x0 = e.anchor.x - s.ox;
    const float y0 = e.anchor.y - s.oy;
    // Offsets on the ground plane (x, 2y) from the pivot; only what lies the baked shadow's way
    // turns and stretches (what lies behind the caster stays at its foot).
    float farthest = 1e-3f;
    std::array<std::pair<Vec2, float>, (kGrid + 1) * (kGrid + 1)> moved{};
    for (int j = 0; j <= kGrid; ++j)
        for (int i = 0; i <= kGrid; ++i) {
            const Vec2 p{x0 + s.w * static_cast<float>(i) / kGrid,
                         y0 + s.h * static_cast<float>(j) / kGrid};
            const float ox = p.x - pivot.x;
            const float oy = 2.0f * (p.y - pivot.y);
            const float along = ox * w.along[0] + oy * w.along[1];
            Vec2 o{ox, oy};
            if (along > 0) o = {w.m[0] * ox + w.m[1] * oy, w.m[2] * ox + w.m[3] * oy};
            farthest = std::max(farthest, along);
            moved[static_cast<std::size_t>(j * (kGrid + 1) + i)] = {
                {pivot.x + o.x, pivot.y + o.y * 0.5f}, along};
        }
    for (int j = 0; j <= kGrid; ++j)
        for (int i = 0; i <= kGrid; ++i) {
            const auto& [p, along] = moved[static_cast<std::size_t>(j * (kGrid + 1) + i)];
            const float k = std::clamp((along / farthest - 0.4f) / 0.6f, 0.0f, 1.0f);
            const float a = 1.0f - (1.0f - gpu::tuning::kShadowFarAlpha) * k * k * (3 - 2 * k);
            const Vec2 sp = x.apply(p);
            verts.push_back({{sp.x, sp.y},
                             {1, 1, 1, a},
                             {s.uv.u0 + (s.uv.u1 - s.uv.u0) * static_cast<float>(i) / kGrid,
                              s.uv.v0 + (s.uv.v1 - s.uv.v0) * static_cast<float>(j) / kGrid}});
            if (i > 0 && j > 0) {
                const int b = j * (kGrid + 1) + i;
                for (const int q : {b - kGrid - 2, b - kGrid - 1, b, b - kGrid - 2, b, b - 1})
                    idx.push_back(q);
            }
        }
    plain();
    batch_.use(tex, SDL_BLENDMODE_BLEND, x.filter);
    batch_.triangles(verts.data(), static_cast<int>(verts.size()), idx.data(),
                     static_cast<int>(idx.size()));
    return true;
}

void WorldView::cloudsGpu() {
    namespace t = gpu::tuning;
    // A few cumulus per weather cell, placed and shaped by its id: they ride the cell with the
    // wind and grow and fade with it, so none pops in or out.
    const auto unit = [](std::uint32_t h) {
        h ^= h >> 16;
        h *= 0x7feb352du;
        h ^= h >> 15;
        h *= 0x846ca68bu;
        h ^= h >> 16;
        return static_cast<float>(h & 0xffffffu) / static_cast<float>(0x1000000);
    };
    cloudList_.clear();
    const Vec2 centre{(lastView_.x0 + lastView_.x1) * 0.5f, (lastView_.y0 + lastView_.y1) * 0.5f};
    const float sunX = -0.4f * t::kCloudAltitude;
    const float sunY = -0.3f * t::kCloudAltitude; // world px (the ground plane's y halved)
    if (weather_ != nullptr && clouds_ != gpu::Clouds::Off)
        for (const WeatherCell& c : weather_->cells()) {
            const float growth = c.intensity();
            if (c.age < 0 || growth < 0.02f) continue;
            const int n = 1 + (c.radius > 12.0f ? 1 : 0) + (c.radius > 16.0f ? 1 : 0);
            for (int k = 0; k < n && cloudList_.size() < static_cast<std::size_t>(t::kClouds);
                 ++k) {
                const std::uint32_t h = c.id * 2654435761u + static_cast<std::uint32_t>(k) * 97u;
                const float r = c.radius * 0.5f * unit(h + 1);
                const float a = 6.2831853f * unit(h + 2);
                const Vec2 g =
                    iso_.toWorld(c.centre.x + r * std::cos(a), c.centre.y + r * std::sin(a));
                // Growing, a cloud swells a little and fades in (dithered), so none is ever a
                // speck.
                const float width =
                    (t::kCloudWidth[0] + (t::kCloudWidth[1] - t::kCloudWidth[0]) * unit(h + 3)) *
                    (c.rain ? 1.25f : 1.0f) * (0.75f + 0.25f * growth);
                const Vec2 parallax{(g.x - centre.x) * t::kCloudParallax,
                                    (g.y - centre.y) * t::kCloudParallax};
                // Seen or casting a shadow in view (with a margin of its size).
                const float m = width;
                const float sx = g.x + parallax.x;
                const float sy = g.y + parallax.y - t::kCloudAltitude;
                const bool seen = sx + m > lastView_.x0 && sx - m < lastView_.x1 &&
                                  sy + m > lastView_.y0 && sy - m < lastView_.y1;
                const bool shadow = g.x + sunX + m > lastView_.x0 &&
                                    g.x + sunX - m < lastView_.x1 &&
                                    g.y + sunY + m > lastView_.y0 && g.y + sunY - m < lastView_.y1;
                if (seen || shadow)
                    cloudList_.push_back(
                        {g, width, unit(h + 4) * 97.0f, growth, c.rain ? 1.0f : 0.0f, parallax});
            }
        }
    if (cloudList_.empty()) {
        post_->noClouds();
        return;
    }
    gpu::CloudParams p;
    p.origin = gpuFrame_.artOrigin;
    p.worldPerTexel = 4.0f / res_;
    p.altitude = t::kCloudAltitude;
    p.sunShift = {sunX, 2.0f * sunY};
    p.clouds = cloudList_;
    post_->clouds(batch_, p, viewW_, viewH_);
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
                 now,
                 season};
    lights_->update(clock, now, life_);
}

void WorldView::lightGpu(const FRect& view, const Xform& x, Lod lod, float glow, const Hooks& hooks,
                         const FrameInfo& frame, bool home) {
    plain(); // (what follows is not decoded)
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
    plain(); // (what follows is not decoded)
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
    cloudsGpu();
    post_->measure(batch_, view_.texture.get(), viewW_, viewH_, snapExposure_);
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
    namespace t = gpu::tuning;
    const gpu::Quality q = post_->quality();
    const Lod lod = stats_.lod;
    // Water: layered below the overview (the overview's own art has its water drawn in).
    if (lod != Lod::Overview) {
        f.waterAt = {static_cast<float>(waterRect_.x0), static_cast<float>(waterRect_.y0)};
        f.halfTile = {iso_.hw, iso_.hh};
        f.grid = {static_cast<float>(map_.width()), static_cast<float>(map_.height())};
        f.horizonTiles = tuning::kHorizonTiles;
        f.levelPx = static_cast<float>(lvl_);
        f.time = gpuFrame_.now;
        const gpu::WaterColours wc = gpu::waterColours(gpuFrame_.grade.water, gpuFrame_.season);
        f.shallow = wc.shallow;
        f.deep = wc.deep;
        f.river = wc.river;
        f.bands = q == gpu::Quality::Low ? t::kWaterBandsLow : t::kWaterBandsHigh;
        f.reflections = q == gpu::Quality::High && lod == Lod::Native;
        // The sky it mirrors, seen from above: mostly the upper sky, with some of the horizon's
        // warmth (at a low sun the water is mostly the sky's).
        const Rgb s0 = gpuFrame_.grade.sky[0];
        const Rgb s2 = gpuFrame_.grade.sky[2];
        f.skyInWater = {s0.r * 0.6f + s2.r * 0.4f, s0.g * 0.6f + s2.g * 0.4f,
                        s0.b * 0.6f + s2.b * 0.4f};
        // Little sky by day (the water keeps its colour), more as the light goes.
        const float day = std::clamp(1.0f - std::max(gpuFrame_.glow, gpuFrame_.night), 0.0f, 1.0f);
        f.skyShare = t::kSkyInWater[1] + (t::kSkyInWater[0] - t::kSkyInWater[1]) * day;
        // Sun glints by day, fewer moon glints at night.
        f.glints = (t::kGlints * (1.0f - gpuFrame_.night) + t::kMoonGlints * gpuFrame_.night) *
                   (lod == Lod::Native ? 1.0f : 0.0f);
        if (weather_ != nullptr)
            f.rain = weather_->rainAt(iso_.toTile(
                {(lastView_.x0 + lastView_.x1) * 0.5f, (lastView_.y0 + lastView_.y1) * 0.5f}));
    }
    // Clouds: the deck only when they are on, thin near and fuller far; shadows by daylight.
    if (clouds_ != gpu::Clouds::Off) {
        f.cloudShadow = t::kCloudShadow * (1.0f - gpuFrame_.night);
        if (clouds_ == gpu::Clouds::On) f.deckAlpha = t::kDeckAlpha[static_cast<std::size_t>(lod)];
        // Sunlit tops nearly white, warmed by a low sun; bases the sky's blue-grey; dim at night.
        const Rgb hz = gpuFrame_.grade.sky[2];
        const Rgb skyMid = gpuFrame_.grade.sky[1];
        const float dim = 1.0f - 0.72f * gpuFrame_.night;
        f.deckColour = {(0.82f + 0.18f * hz.r) * dim, (0.82f + 0.18f * hz.g) * dim,
                        (0.82f + 0.18f * hz.b) * dim};
        f.deckBase = {(0.50f + 0.22f * skyMid.r) * dim, (0.53f + 0.22f * skyMid.g) * dim,
                      (0.60f + 0.22f * skyMid.b) * dim};
    }
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
    const bool packed = s.packed && (s.page != PageAtlas::kHomePage || pages_->homePackedReady());
    if (decoder_) decoder_->use(batch_, packed);
    const SDL_FColor c = decoder_ && packed
                             ? packedColour({1, 1, 1, 1}, s.page == PageAtlas::kHomePage, false)
                             : SDL_FColor{1, 1, 1, 1};
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
            verts.push_back({{p.x, p.y}, c, {k == 0 ? s.uv.u0 : s.uv.u1, vv}});
        }
        if (i > 0) {
            const int b = 2 * (i - 1);
            for (const int q : {b, b + 1, b + 3, b, b + 3, b + 2}) idx.push_back(q);
        }
    }
    batch_.use(t, decoder_ && packed ? decoder_->replace() : SDL_BLENDMODE_BLEND, x.filter);
    batch_.triangles(verts.data(), static_cast<int>(verts.size()), idx.data(),
                     static_cast<int>(idx.size()));
}

} // namespace lc::worldview
