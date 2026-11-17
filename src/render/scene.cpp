#include "render/scene.hpp"

#include "core/tuning.hpp"

#include <algorithm>
#include <cmath>

namespace lc {
namespace {

constexpr SDL_FColor kWhite{1, 1, 1, 1};
constexpr SDL_FColor colour(const float (&c)[3]) {
    return {c[0], c[1], c[2], 1.0f};
}
constexpr SDL_FColor kInvalidTint = colour(tuning::kInvalidTint);
constexpr SDL_FColor kWarmLight = colour(tuning::kWarmLight);
constexpr SDL_FColor kFireflyHalo = colour(tuning::kFireflyHalo);
constexpr SDL_FColor kFireflyCore = colour(tuning::kFireflyCore);
constexpr std::size_t kMaxPops = 256;
constexpr std::size_t kMaxFades = 64;

FRect tileRect(const Item& it) {
    const auto f = [](int v) { return static_cast<float>(v); };
    return {f(it.pos.x), f(it.pos.y), f(it.pos.x + it.w), f(it.pos.y + it.h)};
}

FRect pointRect(Vec2 p) {
    return {p.x - 0.01f, p.y - 0.01f, p.x + 0.01f, p.y + 0.01f};
}

float easeOutBack(float t) {
    constexpr float c1 = 1.70158f;
    constexpr float c3 = c1 + 1.0f;
    const float u = t - 1.0f;
    return 1.0f + c3 * u * u * u + c1 * u * u;
}

SDL_FColor scaled(SDL_FColor c, float k) {
    return {c.r * k, c.g * k, c.b * k, c.a};
}

void grow(Reach& r, const Sprite& s, float extraTop = 0) {
    r.left = std::max(r.left, s.ox);
    r.right = std::max(r.right, s.w - s.ox);
    r.top = std::max(r.top, s.oy + extraTop);
    r.bottom = std::max(r.bottom, s.h - s.oy);
}

} // namespace

Scene::Scene(SDL_Renderer* renderer, Atlas& atlas, const Catalog& cat)
    : renderer_(renderer), atlas_(atlas), cat_(cat), iso_(cat.iso()),
      tables_(buildSpriteTables(atlas, cat)), batch_(renderer), particles_(cat.iso()) {
    ground_ =
        std::make_unique<GroundCache>(renderer, atlas, cat, tables_, tuning::kGroundCacheBytes);
    if (const SurfacePtr px{SDL_CreateSurface(1, 1, SDL_PIXELFORMAT_RGBA32)};
        px && SDL_ClearSurface(px.get(), 1, 1, 1, 1))
        white_ = uploadTexture(renderer, px.get());
    for (const auto& it : tables_.items)
        for (const auto& set : it.base)
            for (const SpriteId id : set.frames) grow(itemReach_, atlas_.sprite(id));
    for (const auto& anims : tables_.critters)
        for (const auto& set : anims)
            for (const SpriteId id : set.frames)
                grow(itemReach_, atlas_.sprite(id), tuning::kHoverMax * iso_.tileH() + 2);
    lights_.reserve(256);
    chimneys_.reserve(64);
    fades_.reserve(kMaxFades);
    pops_.reserve(kMaxPops);
    pulses_.reserve(16);
    dynamic_.reserve(256);
}

int Scene::slotFor(const World& world, const Item& item) const {
    return cat_.items[item.type].layout == Layout::Connect ? world.itemMask(item.pos, item.type)
                                                           : item.variant;
}

FRect Scene::spriteRect(const Item& item, int slot) const {
    const Sprite& s =
        atlas_.sprite(tables_.items[item.type].base[static_cast<std::size_t>(slot)].frames.front());
    const Vec2 a = iso_.toWorld(item.pos);
    return {a.x - s.ox, a.y - s.oy, a.x - s.ox + s.w, a.y - s.oy + s.h};
}

FRect Scene::critterRect(const Critter& c) const {
    const FrameSet& set =
        tables_.critters[c.visitor][static_cast<std::size_t>(CritterAnim::IdleFront)];
    const Sprite& s = atlas_.sprite(set.frames.front());
    const Vec2 a = iso_.toWorld(c.pos.x, c.pos.y);
    // Mirrored frames flip about the anchor, so take the wider side both ways.
    const float half = std::max(s.ox, s.w - s.ox);
    return {a.x - half, a.y - s.oy, a.x + half, a.y - s.oy + s.h};
}

TileRect Scene::visibleTiles(const Camera& camera, Vec2 screen, const World& world) const {
    const float s = camera.scale();
    const Vec2 c = camera.position();
    const FRect view{c.x - screen.x * 0.5f / s, c.y - screen.y * 0.5f / s,
                     c.x + screen.x * 0.5f / s, c.y + screen.y * 0.5f / s};
    // An anchor this far outside the view can still put sprite pixels inside it.
    const FRect g{view.x0 - itemReach_.right, view.y0 - itemReach_.bottom,
                  view.x1 + itemReach_.left, view.y1 + itemReach_.top};
    const Vec2 k[4] = {iso_.toTile({g.x0, g.y0}), iso_.toTile({g.x1, g.y0}),
                       iso_.toTile({g.x0, g.y1}), iso_.toTile({g.x1, g.y1})};
    float x0 = k[0].x, x1 = k[0].x, y0 = k[0].y, y1 = k[0].y;
    for (const Vec2& v : k) {
        x0 = std::min(x0, v.x);
        x1 = std::max(x1, v.x);
        y0 = std::min(y0, v.y);
        y1 = std::max(y1, v.y);
    }
    return TileRect{static_cast<int>(std::floor(x0)), static_cast<int>(std::floor(y0)),
                    static_cast<int>(std::floor(x1)) + 1, static_cast<int>(std::floor(y1)) + 1}
        .clipped(world.bounds());
}

void Scene::rebuild(const World& world, TileRect region) {
    region_ = region;
    regionRevision_ = world.revision();
    const auto nature = cat_.findCategory("nature");
    gathered_.clear();
    world.forEachItemIn(region, [&](const Item& it) {
        const int slot = slotFor(world, it);
        const auto& def = cat_.items[it.type];
        const FRect r = spriteRect(it, slot);
        // Trees (tall nature pieces) drop the occasional leaf.
        const bool tree = nature && def.category == *nature && !def.walkable &&
                          r.y1 - r.y0 >= tuning::kTreeHeight * iso_.tileH();
        gathered_.push_back({it, slot, r, tree, false});
    });
    footprints_.clear();
    screens_.clear();
    for (const Placed& p : gathered_) {
        footprints_.push_back(tileRect(p.item));
        screens_.push_back(p.screen);
    }
    sorter_.sort(footprints_, screens_, 2 * iso_.tileW(), order_);
    placed_.clear();
    footprints_.clear();
    screens_.clear();
    for (const std::uint32_t i : order_) {
        placed_.push_back(gathered_[i]);
        footprints_.push_back(tileRect(gathered_[i].item));
        screens_.push_back(gathered_[i].screen);
    }
    grid_.build(screens_, 2 * iso_.tileW());

    glowRects_.clear();
    lights_.clear();
    chimneys_.clear();
    trees_.clear();
    for (std::uint32_t i = 0; i < placed_.size(); ++i) {
        Placed& p = placed_[i];
        const auto& spr = tables_.items[p.item.type];
        const auto slot = static_cast<std::size_t>(p.slot);
        if (p.tree) trees_.push_back(i);
        const Vec2 a = iso_.toWorld(p.item.pos);
        const auto& smoke = cat_.items[p.item.type].smokeAt;
        if (slot < smoke.size())
            chimneys_.push_back(
                {a.x + static_cast<float>(smoke[slot].x), a.y + static_cast<float>(smoke[slot].y)});
        if (spr.glow[slot].empty()) continue;
        // Only what can hide an emissive pixel needs the glow pass: use the glow art's bounds.
        const Sprite& gs = atlas_.sprite(spr.glow[slot].frames.front());
        const FRect glowBox{a.x - gs.ox, a.y - gs.oy, a.x - gs.ox + gs.w, a.y - gs.oy + gs.h};
        glowRects_.push_back(glowBox);
        // Things behind the light cannot cover it.
        grid_.query(glowBox, [&](std::uint32_t j) {
            if (placed_[j].screen.overlaps(glowBox) &&
                (j == i || behind(footprints_[i], footprints_[j])))
                placed_[j].occludesGlow = true;
        });
        // The pool lies on the ground: under a small light, or in front of a building, below
        // its windows.
        const TileRect fp = p.item.rect();
        const auto f = [](int v) { return static_cast<float>(v); };
        Vec2 pos = iso_.toWorld(f(fp.x0) + f(p.item.w) * 0.5f, f(fp.y0) + f(p.item.h) * 0.5f);
        if (const auto& light = spr.light[slot]; light && (p.item.w > 1 || p.item.h > 1)) {
            const Vec2 left = iso_.toWorld(f(fp.x0), f(fp.y1));
            const Vec2 bottom = iso_.toWorld(f(fp.x1), f(fp.y1));
            const Vec2 right = iso_.toWorld(f(fp.x1), f(fp.y0));
            const float x = std::clamp(a.x + light->x, left.x, right.x);
            const Vec2 from = x <= bottom.x ? left : bottom;
            const Vec2 to = x <= bottom.x ? bottom : right;
            const float k = to.x > from.x ? (x - from.x) / (to.x - from.x) : 0.0f;
            pos = {x, from.y + (to.y - from.y) * k + iso_.hh * 0.5f};
        }
        const float side = static_cast<float>(std::max(p.item.w, p.item.h));
        lights_.push_back(
            {pos, iso_.tileW() * (tuning::kLightRadius + tuning::kLightRadiusPerSide * side)});
    }

    water_.clear();
    world.forEachChunkIn(region, [&](int cx, int cy) {
        if (world.chunkTerrainCount(cx, cy, cat_.waterTerrain) == 0) return;
        const TileRect r =
            TileRect{cx * kChunk, cy * kChunk, (cx + 1) * kChunk, (cy + 1) * kChunk}.clipped(
                region);
        for (int y = r.y0; y < r.y1; ++y)
            for (int x = r.x0; x < r.x1; ++x)
                if (world.isWater({x, y})) water_.push_back({x, y});
    });
}

float Scene::popOf(TilePos origin) const {
    for (const Pop& p : pops_)
        if (p.origin == origin) return (now_ - p.start) / tuning::kPopSeconds;
    return 1.0f;
}

void Scene::onPlaced(const Item& item, Rng& rng) {
    if (pops_.size() == kMaxPops) pops_.erase(pops_.begin());
    std::erase_if(pops_, [&](const Pop& p) { return p.origin == item.pos; });
    pops_.push_back({item.pos, now_});
    const auto f = [](int v) { return static_cast<float>(v); };
    const Vec2 c = iso_.toWorld(f(item.pos.x) + f(item.w) * 0.5f, f(item.pos.y) + f(item.h) * 0.5f);
    const float u = iso_.tileH();
    for (int i = 0; i < 3; ++i) {
        particles_.spawn(Fx::Sparkle,
                         {c.x + rng.range(-1.0f, 1.0f) * tuning::kSparkleSpread * u,
                          c.y - rng.range(0.1f, 1.1f) * u},
                         {0, -tuning::kSparkleRise * u}, rng.range(0.4f, 0.7f));
    }
}

void Scene::burst(Vec2 tile, Rng& rng) {
    const Vec2 c = iso_.toWorld(tile.x, tile.y);
    const float u = iso_.tileH();
    for (int i = 0; i < 6; ++i)
        particles_.spawn(Fx::Sparkle,
                         {c.x + rng.range(-1.0f, 1.0f) * tuning::kSparkleSpread * u,
                          c.y - rng.range(0.6f, 1.8f) * u},
                         {0, -tuning::kSparkleRise * u}, rng.range(0.6f, 1.0f));
}

void Scene::flourish(const NearInstance& nook, const World& world, Rng& rng) {
    pulses_.push_back({nook, now_});
    const TileRect& f = nook.footprint;
    for (int i = 0; i < 8; ++i) {
        const TilePos t{rng.range(f.x0 - nook.within, f.x1 + nook.within - 1),
                        rng.range(f.y0 - nook.within, f.y1 + nook.within - 1)};
        if (world.hasGround(t))
            burst({static_cast<float>(t.x) + 0.5f, static_cast<float>(t.y) + 0.5f}, rng);
    }
}

void Scene::drawArea(const World& world, const NearInstance& area, SDL_FColor color) {
    const TileRect& f = area.footprint;
    for (int y = f.y0 - area.within; y < f.y1 + area.within; ++y)
        for (int x = f.x0 - area.within; x < f.x1 + area.within; ++x)
            if (!f.contains(TilePos{x, y}) && world.hasGround({x, y}))
                sprite(tables_.tileArea, iso_.toWorld(TilePos{x, y}), color);
}

void Scene::onRemoved(const Item& item) {
    if (fades_.size() == kMaxFades) fades_.erase(fades_.begin());
    // The connect mask is frozen at removal time; neighbours no longer include the item.
    fades_.push_back(
        {item, cat_.items[item.type].layout == Layout::Connect ? 0 : item.variant, now_});
    std::erase_if(pops_, [&](const Pop& p) { return p.origin == item.pos; });
}

void Scene::update(float dt, const World& world, std::span<const Critter> critters, bool rain,
                   Rng& rng) {
    now_ += dt;
    std::erase_if(fades_, [&](const Fade& f) { return now_ - f.start > tuning::kFadeOutSeconds; });
    std::erase_if(pops_, [&](const Pop& p) { return now_ - p.start > tuning::kPopSeconds; });
    std::erase_if(pulses_,
                  [&](const Pulse& p) { return now_ - p.start > tuning::kNookPulseSeconds; });
    const float u = iso_.tileH();

    for (const Vec2& c : chimneys_) {
        if (rng.chance(dt / tuning::kSmokeInterval))
            particles_.spawn(Fx::Smoke, {c.x + rng.range(-1.0f, 1.0f), c.y},
                             {rng.range(0.05f, tuning::kSmokeDriftMax) * u,
                              -rng.range(tuning::kSmokeRiseMin, tuning::kSmokeRiseMax) * u},
                             rng.range(2.2f, 3.2f));
    }
    const auto spawnMany = [&](float expected, auto&& one) {
        while (expected > 0) {
            if (rng.chance(std::min(1.0f, expected))) one();
            expected -= 1.0f;
        }
    };
    if (!water_.empty()) {
        const float rate =
            static_cast<float>(water_.size()) * (rain ? tuning::kRainRipplesPerSecondPerWaterTile
                                                      : tuning::kRipplesPerSecondPerWaterTile);
        spawnMany(rate * dt, [&] {
            const TilePos t =
                water_[static_cast<std::size_t>(rng.range(0, static_cast<int>(water_.size()) - 1))];
            const Vec2 w = iso_.toWorld(static_cast<float>(t.x) + rng.range(0.25f, 0.75f),
                                        static_cast<float>(t.y) + rng.range(0.25f, 0.75f));
            particles_.spawn(Fx::Ripple, w, {0, 0}, tuning::kRippleSeconds + 0.1f);
        });
    }
    if (rain && view_.x1 > view_.x0) {
        const float tiles =
            (view_.x1 - view_.x0) * (view_.y1 - view_.y0) / (iso_.tileW() * iso_.hh);
        const float fall = tuning::kRainFall * u;
        const float speed = tuning::kRainSpeed * u;
        // Keep room in the pool for smoke, ripples and leaves however large the view.
        const float maxRate = tuning::kRainPoolShare * static_cast<float>(Particles::kCapacity) /
                              (fall / speed + tuning::kSplashSeconds);
        const float rate = std::min(tuning::kRainDropsPerSecondPerTile * tiles, maxRate);
        spawnMany(rate * dt, [&] {
            const Vec2 ground{rng.range(view_.x0, view_.x1 + fall * 0.15f),
                              rng.range(view_.y0, view_.y1)};
            particles_.spawn(Fx::Raindrop, {ground.x + fall * 0.15f, ground.y - fall},
                             {-speed * 0.15f, speed}, fall / speed);
        });
    }
    for (const std::uint32_t i : trees_) {
        if (i >= placed_.size() || !rng.chance(tuning::kLeavesPerSecondPerTree * dt)) continue;
        const FRect& r = placed_[i].screen;
        particles_.spawn(
            Fx::Leaf,
            {(r.x0 + r.x1) * 0.5f + rng.range(-0.5f, 0.5f) * u, r.y0 + (r.y1 - r.y0) * 0.35f},
            {rng.range(-0.25f, 0.25f) * u, tuning::kLeafFall * u}, 2.6f, rng.range(0.0f, 6.0f));
    }
    // Swimmers leave a wake.
    for (const Critter& c : critters) {
        if (cat_.visitors[c.visitor].habitat != Habitat::Water || !c.moving) continue;
        if (rng.chance(dt / tuning::kWakeInterval))
            particles_.spawn(Fx::Ripple, iso_.toWorld(c.pos.x, c.pos.y), {0, 0},
                             tuning::kRippleSeconds);
    }
    particles_.update(dt, world);
}

void Scene::ensureTargets(int w, int h) {
    targetW_ = w;
    targetH_ = h;
    // Allocated with headroom and never shrunk, so zoom transitions and window resizes reuse
    // the same textures.
    const auto make = [&](Target& t) {
        if (t.texture && t.w >= w && t.h >= h) return;
        const int aw = std::max(t.w, (w + 255) / 256 * 256);
        const int ah = std::max(t.h, (h + 255) / 256 * 256);
        t.texture.reset(
            SDL_CreateTexture(renderer_, kTextureFormat, SDL_TEXTUREACCESS_TARGET, aw, ah));
        t.w = t.texture ? aw : 0;
        t.h = t.texture ? ah : 0;
        if (!t.texture) SDL_Log("render: cannot create %dx%d target: %s", aw, ah, SDL_GetError());
    };
    make(world_);
    make(light_);
    make(glow_);
    make(shadow_);
}

void Scene::fullQuad(SDL_Texture* texture, SDL_BlendMode mode, SDL_FColor color) {
    const auto& t = texture == world_.texture.get()   ? world_
                    : texture == light_.texture.get() ? light_
                    : texture == glow_.texture.get()  ? glow_
                                                      : shadow_;
    const auto w = static_cast<float>(targetW_);
    const auto h = static_cast<float>(targetH_);
    batch_.use(texture, mode, SDL_SCALEMODE_NEAREST);
    batch_.quad(SDL_FRect{0, 0, w, h},
                {0, 0, w / static_cast<float>(t.w), h / static_cast<float>(t.h)}, color);
}

void Scene::sprite(SpriteId id, Vec2 anchor, SDL_FColor color, bool mirror, Vec2 pivot,
                   Vec2 scale) {
    putSprite(batch_, atlas_.sprite(id), anchor, xf_, color, blend_, mirror, pivot, scale);
}

SDL_FColor Scene::exposed(SpriteId id, SDL_FColor c) const {
    const float luma = atlas_.luma(id);
    if (night_ <= 0.0f || luma <= tuning::kNightLumaCap) return c;
    return scaled(c, 1.0f + (tuning::kNightLumaCap / luma - 1.0f) * night_);
}

void Scene::drawItem(const Item& item, int slot, float alpha, SDL_FColor tint, bool silhouette,
                     float scaleY) {
    const auto& def = cat_.items[item.type];
    const auto& spr = tables_.items[item.type];
    const auto s = static_cast<std::size_t>(slot);
    const auto f = [](int v) { return static_cast<float>(v); };
    const Vec2 anchor = iso_.toWorld(item.pos);
    const Vec2 pivot =
        iso_.toWorld(f(item.pos.x) + f(item.w) * 0.5f, f(item.pos.y) + f(item.h) * 0.5f);
    Vec2 scale{1.0f, scaleY};
    const float t = popOf(item.pos);
    if (t >= 0.0f && t < 1.0f) {
        const float y = 0.35f + 0.65f * easeOutBack(t);
        scale = {1.0f + (1.0f - y) * 0.45f, y};
        alpha *= std::min(1.0f, t * 4.0f);
    }
    const std::uint32_t phase = tileHash(item.pos.x, item.pos.y) % 7;
    const SpriteId base = spr.base[s].at(now_, def.fps, phase);
    const SDL_FColor c = silhouette ? SDL_FColor{0, 0, 0, alpha}
                                    : exposed(base, {tint.r, tint.g, tint.b, tint.a * alpha});
    sprite(base, anchor, c, false, pivot, scale);
}

void Scene::buildDynamic(const FrameParams& p) {
    dynamic_.clear();
    const auto insert = [&](EntryKind kind, std::uint32_t index, const FRect& tr, const FRect& sr,
                            bool glowing) {
        if (!sr.overlaps(view_)) return;
        std::uint32_t after = 0;
        grid_.query(sr, [&](std::uint32_t i) {
            if (i + 1 > after && placed_[i].screen.overlaps(sr) && behind(footprints_[i], tr))
                after = i + 1;
        });
        dynamic_.push_back(
            {kind, index, after, tr.x0 + tr.x1 + tr.y0 + tr.y1, glowing || nearGlow(sr)});
    };
    for (std::uint32_t i = 0; i < p.critters.size(); ++i) {
        const Critter& c = p.critters[i];
        const auto& def = cat_.visitors[c.visitor];
        if (def.habitat == Habitat::Air) continue;
        // Emissive visitors are always drawn in the glow pass.
        insert(EntryKind::Critter, i, pointRect(c.pos), critterRect(c), def.glow);
    }
    if (p.ghost.mode == Ghost::Mode::Item) {
        const int slot = slotFor(*p.world, p.ghost.item);
        insert(EntryKind::Ghost, 0, tileRect(p.ghost.item), spriteRect(p.ghost.item, slot), false);
    }
    for (std::uint32_t i = 0; i < fades_.size(); ++i)
        insert(EntryKind::Fade, i, tileRect(fades_[i].item),
               spriteRect(fades_[i].item, fades_[i].slot), false);
    std::ranges::sort(dynamic_, [](const Entry& a, const Entry& b) {
        return a.after != b.after ? a.after < b.after : a.depth < b.depth;
    });
}

void Scene::drawCritter(const Critter& c, bool silhouette) {
    const auto& def = cat_.visitors[c.visitor];
    // Emissive visitors skip the graded pass and appear, ungraded, in the glow layer.
    if (def.glow && !silhouette) return;
    const bool back = c.facing == Facing::Back || c.facing == Facing::BackMirrored;
    const bool mirror = c.facing == Facing::FrontMirrored || c.facing == Facing::BackMirrored;
    const auto anim = static_cast<std::size_t>(
        c.moving ? (back ? CritterAnim::MoveBack : CritterAnim::MoveFront)
                 : (back ? CritterAnim::IdleBack : CritterAnim::IdleFront));
    const FrameSet& set = tables_.critters[c.visitor][anim];
    const SpriteId id =
        set.at(c.animTime, c.moving ? tuning::kCritterMoveFps : tuning::kCritterIdleFps);
    Vec2 w = iso_.toWorld(c.pos.x, c.pos.y);
    if (def.habitat == Habitat::Air)
        w.y -= (c.hover + std::sin(c.animTime * 3.1f) * 0.12f) * iso_.tileH();
    w = {std::round(w.x), std::round(w.y)};
    const float a = std::clamp(c.alpha, 0.0f, 1.0f);
    const SDL_FColor color = silhouette && !def.glow ? SDL_FColor{0, 0, 0, a}
                             : def.glow              ? SDL_FColor{1, 1, 1, a}
                                                     : exposed(id, {1, 1, 1, a});
    sprite(id, w, color, mirror);
}

void Scene::drawEntry(const FrameParams& p, const Entry& e, bool silhouette) {
    if (silhouette && !e.occludesGlow) return;
    switch (e.kind) {
    case EntryKind::Critter: drawCritter(p.critters[e.index], silhouette); break;
    case EntryKind::Ghost: {
        const int slot = slotFor(*p.world, p.ghost.item);
        drawItem(p.ghost.item, slot, tuning::kGhostAlpha, p.ghost.valid ? kWhite : kInvalidTint,
                 silhouette);
        break;
    }
    case EntryKind::Fade: {
        const Fade& f = fades_[e.index];
        const float t = std::clamp((now_ - f.start) / tuning::kFadeOutSeconds, 0.0f, 1.0f);
        drawItem(f.item, f.slot, 1.0f - t, kWhite, silhouette, 1.0f - 0.12f * t);
        break;
    }
    }
}

void Scene::drawEntries(const FrameParams& p, bool silhouette) {
    const float glow = p.light.glow;
    const World& world = *p.world;
    const Item* removeTarget =
        p.ghost.mode == Ghost::Mode::Remove ? world.itemAt(p.ghost.tile) : nullptr;
    std::size_t d = 0;
    if (!silhouette) drawnItems_ = 0;
    for (std::uint32_t i = 0; i < placed_.size(); ++i) {
        for (; d < dynamic_.size() && dynamic_[d].after <= i; ++d)
            drawEntry(p, dynamic_[d], silhouette);
        const Placed& pl = placed_[i];
        if (!pl.screen.overlaps(view_)) continue;
        // The glow pass only needs what can hide an emissive pixel.
        if (silhouette && !pl.occludesGlow) continue;
        if (!silhouette) ++drawnItems_;
        const bool marked = removeTarget != nullptr && *removeTarget == pl.item;
        drawItem(pl.item, pl.slot, 1.0f, marked ? kInvalidTint : kWhite, silhouette);
        const auto& glowSet = tables_.items[pl.item.type].glow[static_cast<std::size_t>(pl.slot)];
        if (silhouette && !glowSet.empty()) {
            const auto& def = cat_.items[pl.item.type];
            sprite(glowSet.at(now_, def.fps, tileHash(pl.item.pos.x, pl.item.pos.y) % 7),
                   iso_.toWorld(pl.item.pos), {glow, glow, glow, 1.0f});
        }
    }
    for (; d < dynamic_.size(); ++d) drawEntry(p, dynamic_[d], silhouette);
    // Flyers are always above the ground clutter.
    for (const Critter& c : p.critters) {
        const auto& def = cat_.visitors[c.visitor];
        if (def.habitat != Habitat::Air) continue;
        FRect r = critterRect(c);
        const float lift = c.hover * iso_.tileH();
        r.y0 -= lift;
        r.y1 -= lift;
        if (!r.overlaps(view_) || (silhouette && !def.glow && !nearGlow(r))) continue;
        drawCritter(c, silhouette);
    }
}

bool Scene::nearGlow(const FRect& r) const {
    return std::ranges::any_of(glowRects_, [&](const FRect& g) { return g.overlaps(r); });
}

void Scene::drawShadows(const FrameParams& p) {
    // Shadow sprites were normalised to a peak alpha of 1, so drawing them into their own layer
    // saturates where they overlap; the layer is then composited once at the art's opacity.
    batch_.flush();
    if (!SDL_SetRenderTarget(renderer_, shadow_.texture.get()) ||
        !SDL_SetRenderDrawColorFloat(renderer_, 0, 0, 0, 0) || !SDL_RenderClear(renderer_)) {
        SDL_Log("render: shadow layer: %s", SDL_GetError());
    }
    blend_ = SDL_BLENDMODE_BLEND;
    for (const Placed& pl : placed_) {
        if (!pl.screen.overlaps(view_)) continue;
        const auto& set = tables_.items[pl.item.type].shadow[static_cast<std::size_t>(pl.slot)];
        if (set.empty()) continue;
        const float t = popOf(pl.item.pos);
        sprite(set.frames.front(), iso_.toWorld(pl.item.pos),
               {1, 1, 1, t >= 0.0f && t < 1.0f ? t : 1.0f});
    }
    for (const Critter& c : p.critters) {
        const Habitat h = cat_.visitors[c.visitor].habitat;
        Vec2 w = iso_.toWorld(c.pos.x, c.pos.y);
        w = {std::round(w.x), std::round(w.y)};
        const float k = h == Habitat::Air ? 0.5f : (h == Habitat::Water ? 0.85f : 0.7f);
        const float a = h == Habitat::Air     ? 0.45f
                        : h == Habitat::Water ? tuning::kWaterShadowAlpha
                                              : 1.0f;
        sprite(atlas_.softShadow(), w, {1, 1, 1, std::clamp(c.alpha, 0.0f, 1.0f) * a}, false, w,
               {k, k});
    }
    batch_.flush();
    if (!SDL_SetRenderTarget(renderer_, world_.texture.get()))
        SDL_Log("render: %s", SDL_GetError());
    fullQuad(shadow_.texture.get(), SDL_BLENDMODE_BLEND, {1, 1, 1, tables_.shadowOpacity});
}

void Scene::drawMarkers(const FrameParams& p) {
    // Placement markers and nook areas sit on the ground under everything else.
    const World& world = *p.world;
    for (const Pulse& pl : pulses_) {
        const float k = (now_ - pl.start) / tuning::kNookPulseSeconds;
        drawArea(world, pl.area,
                 {1.0f, 0.86f, 0.55f, tuning::kNookPulseAlpha * std::sin(k * 3.14159f)});
    }
    for (const NearInstance& o : p.outlines)
        drawArea(world, o, {1, 1, 1, tuning::kNookOutlineAlpha});
    const auto marker = [&](TilePos t, bool ok) {
        if (world.hasGround(t))
            sprite(ok ? tables_.tileOk : tables_.tileBad, iso_.toWorld(t), {1, 1, 1, 0.9f});
    };
    switch (p.ghost.mode) {
    case Ghost::Mode::None: break;
    case Ghost::Mode::Item:
        for (int y = 0; y < p.ghost.item.h; ++y)
            for (int x = 0; x < p.ghost.item.w; ++x)
                marker({p.ghost.item.pos.x + x, p.ghost.item.pos.y + y}, p.ghost.valid);
        break;
    case Ghost::Mode::Tile: marker(p.ghost.tile, p.ghost.valid); break;
    case Ghost::Mode::Remove:
        if (const Item* it = world.itemAt(p.ghost.tile)) {
            for (int y = 0; y < it->h; ++y)
                for (int x = 0; x < it->w; ++x) marker({it->pos.x + x, it->pos.y + y}, false);
        }
        break;
    }
}

void Scene::drawParticles(bool ground) {
    const float m = iso_.tileW();
    const FRect near{view_.x0 - m, view_.y0 - m, view_.x1 + m, view_.y1 + m};
    for (const Particle& pt : particles_.all()) {
        if ((pt.kind == Fx::Ripple) != ground || !near.overlaps(pointRect(pt.pos))) continue;
        const FrameSet& set = tables_.fx[static_cast<std::size_t>(pt.kind)];
        const float k = std::clamp(pt.age / pt.life, 0.0f, 0.999f);
        SpriteId id =
            set.frames[static_cast<std::size_t>(k * static_cast<float>(set.frames.size()))];
        float alpha = 1.0f;
        switch (pt.kind) {
        case Fx::Smoke: alpha = 0.8f * (1.0f - k); break;
        case Fx::Leaf:
            id = set.at(pt.age, 5.0f);
            alpha = std::min(1.0f, (1.0f - k) * 3.0f);
            break;
        case Fx::Raindrop:
            // Frame 0 is the falling streak; the remaining frames are the splash.
            if (!pt.landed || set.frames.size() < 2) {
                id = set.frames.front();
            } else {
                const auto n = set.frames.size() - 1;
                id = set.frames[1 + std::min(n - 1,
                                             static_cast<std::size_t>(k * static_cast<float>(n)))];
            }
            alpha = 0.8f;
            break;
        default: break;
        }
        sprite(id, {std::round(pt.pos.x), std::round(pt.pos.y)}, {1, 1, 1, alpha});
    }
}

void Scene::drawLighting(const FrameParams& p) {
    const Rgb amb = p.light.ambient;
    const float glow = p.light.glow;
    const bool emissive = std::ranges::any_of(
        p.critters, [&](const Critter& c) { return cat_.visitors[c.visitor].glow; });
    if (glow <= 0.01f && !emissive && white_) {
        // No light pools: the light map would be one flat colour, so multiply by it directly.
        // (Through a white texel: the software renderer mishandles untextured multiply.)
        if (amb.r >= 0.999f && amb.g >= 0.999f && amb.b >= 0.999f) return;
        batch_.use(white_.get(), SDL_BLENDMODE_MUL, SDL_SCALEMODE_NEAREST);
        batch_.quad(SDL_FRect{0, 0, static_cast<float>(targetW_), static_cast<float>(targetH_)},
                    {0, 0, 1, 1}, {amb.r, amb.g, amb.b, 1});
        batch_.flush();
        return;
    }
    if (!SDL_SetRenderTarget(renderer_, light_.texture.get()) ||
        !SDL_SetRenderDrawColorFloat(renderer_, amb.r, amb.g, amb.b, 1.0f) ||
        !SDL_RenderClear(renderer_)) {
        SDL_Log("render: light map: %s", SDL_GetError());
    }
    if (glow > 0.01f || emissive) {
        blend_ = SDL_BLENDMODE_ADD;
        const SDL_FColor warm = scaled(kWarmLight, tuning::kLightStrength * glow);
        const float blobRadius = atlas_.sprite(atlas_.lightBlob()).w * 0.5f;
        for (const Light& l : lights_) {
            const FRect r{l.pos.x - l.radius, l.pos.y - l.radius, l.pos.x + l.radius,
                          l.pos.y + l.radius};
            if (!r.overlaps(view_)) continue;
            const float s = l.radius / blobRadius;
            sprite(atlas_.lightBlob(), l.pos, warm, false, l.pos, {s, s * 0.6f});
        }
        for (const Critter& c : p.critters) {
            if (!cat_.visitors[c.visitor].glow) continue;
            Vec2 w = iso_.toWorld(c.pos.x, c.pos.y);
            w.y -= c.hover * iso_.tileH();
            const float pulse = 0.6f + 0.4f * std::sin(c.animTime * 4.0f);
            sprite(atlas_.lightBlob(), w, scaled(kFireflyHalo, 0.5f * glow * pulse * c.alpha),
                   false, w, {0.35f, 0.3f});
        }
        batch_.flush();
    }
    if (!SDL_SetRenderTarget(renderer_, world_.texture.get()))
        SDL_Log("render: %s", SDL_GetError());
    fullQuad(light_.texture.get(), SDL_BLENDMODE_MUL, kWhite);
    batch_.flush();
}

void Scene::drawGlow(const FrameParams& p) {
    const float glow = p.light.glow;
    const bool emissiveVisitors = std::ranges::any_of(
        p.critters, [&](const Critter& c) { return cat_.visitors[c.visitor].glow; });
    if (glow <= 0.01f && !emissiveVisitors) return;
    if (!SDL_SetRenderTarget(renderer_, glow_.texture.get()) ||
        !SDL_SetRenderDrawColorFloat(renderer_, 0, 0, 0, 0) || !SDL_RenderClear(renderer_)) {
        SDL_Log("render: glow: %s", SDL_GetError());
    }
    blend_ = SDL_BLENDMODE_BLEND;
    drawEntries(p, true);
    blend_ = SDL_BLENDMODE_ADD;
    for (const Critter& c : p.critters) {
        if (!cat_.visitors[c.visitor].glow) continue;
        Vec2 w = iso_.toWorld(c.pos.x, c.pos.y);
        w.y -= (c.hover + std::sin(c.animTime * 3.1f) * 0.12f) * iso_.tileH();
        const float pulse = 0.55f + 0.45f * std::sin(c.animTime * 4.0f);
        sprite(atlas_.lightBlob(), w, scaled(kFireflyCore, 0.8f * pulse * c.alpha), false, w,
               {0.12f, 0.12f});
    }
    batch_.flush();
    if (!SDL_SetRenderTarget(renderer_, world_.texture.get()))
        SDL_Log("render: %s", SDL_GetError());
    fullQuad(glow_.texture.get(), SDL_BLENDMODE_ADD, kWhite);
    batch_.flush();
}

void Scene::draw(const FrameParams& p, SDL_Texture* out) {
    batch_.resetStats();
    const World& world = *p.world;
    const float s = p.camera->scale();
    // Target pixels per world pixel: native, except below 1x where the target matches the window.
    const float res = std::min(1.0f, s);
    const Vec2 cam = p.camera->position();
    topLeft_ = {cam.x - p.screen.x * 0.5f / s, cam.y - p.screen.y * 0.5f / s};
    // The origin sits on the target's pixel grid so cached ground lands on whole pixels.
    const float px = 1.0f / res;
    const Vec2 origin{std::floor(topLeft_.x / px) * px - px, std::floor(topLeft_.y / px) * px - px};
    ensureTargets(static_cast<int>(std::ceil(p.screen.x / s * res)) + 3,
                  static_cast<int>(std::ceil(p.screen.y / s * res)) + 3);
    if (!world_.texture || !light_.texture || !glow_.texture || !shadow_.texture) return;
    xf_ = {origin, res, res < 1.0f ? SDL_SCALEMODE_LINEAR : SDL_SCALEMODE_NEAREST};
    view_ = {origin.x, origin.y, origin.x + static_cast<float>(targetW_) * px,
             origin.y + static_cast<float>(targetH_) * px};
    night_ = std::clamp(p.light.night, 0.0f, 1.0f);

    const TileRect vis = visibleTiles(*p.camera, p.screen, world);
    if (world.revision() != regionRevision_ || !region_.contains(vis)) {
        const int gx =
            std::max(tuning::kRegionMinGrow,
                     static_cast<int>(static_cast<float>(vis.x1 - vis.x0) * tuning::kRegionGrow));
        const int gy =
            std::max(tuning::kRegionMinGrow,
                     static_cast<int>(static_cast<float>(vis.y1 - vis.y0) * tuning::kRegionGrow));
        rebuild(world, TileRect{vis.x0 - gx, vis.y0 - gy, vis.x1 + gx, vis.y1 + gy}.clipped(
                           world.bounds()));
    }

    if (!SDL_SetRenderTarget(renderer_, world_.texture.get()) ||
        !SDL_SetRenderDrawColorFloat(renderer_, 0, 0, 0, 0) || !SDL_RenderClear(renderer_)) {
        SDL_Log("render: world target: %s", SDL_GetError());
    }
    ground_->draw(batch_, world, view_, xf_, world_.texture.get(), now_);
    buildDynamic(p);
    drawShadows(p);
    blend_ = SDL_BLENDMODE_BLEND;
    drawMarkers(p);
    drawParticles(true);
    drawEntries(p, false);
    drawParticles(false);
    batch_.flush();
    drawLighting(p);
    drawGlow(p);

    if (!SDL_SetRenderTarget(renderer_, out)) SDL_Log("render: %s", SDL_GetError());
    composite(p, {1, 1}, false);
}

void Scene::composite(const FrameParams& p, Vec2 scale, bool smooth) {
    if (!world_.texture) return;
    const float s = p.camera->scale();
    const float k = s / xf_.res; // window px per target px
    const float w = p.screen.x * scale.x;
    const float h = p.screen.y * scale.y;
    // Sky gradient behind the floating island.
    const Rgb t = p.light.skyTop;
    const Rgb b = p.light.skyBottom;
    const SDL_Vertex sky[4] = {
        {{0, 0}, {t.r, t.g, t.b, 1}, {0, 0}},
        {{w, 0}, {t.r, t.g, t.b, 1}, {0, 0}},
        {{w, h}, {b.r, b.g, b.b, 1}, {0, 0}},
        {{0, h}, {b.r, b.g, b.b, 1}, {0, 0}},
    };
    static constexpr int kQuad[6] = {0, 1, 2, 0, 2, 3};
    batch_.use(nullptr, SDL_BLENDMODE_NONE);
    batch_.triangles(sky, 4, kQuad, 6);
    // Whole-number magnification stays nearest-neighbour; anything else (mid-transition, or a
    // blurred copy) is filtered.
    const bool whole = std::abs(k - std::round(k)) < 1e-3f;
    // The world layer was drawn over transparent black, so its colour is premultiplied.
    batch_.use(world_.texture.get(), SDL_BLENDMODE_BLEND_PREMULTIPLIED,
               smooth || !whole ? SDL_SCALEMODE_LINEAR : SDL_SCALEMODE_NEAREST);
    const auto tw = static_cast<float>(targetW_);
    const auto th = static_cast<float>(targetH_);
    batch_.quad(
        SDL_FRect{(xf_.origin.x - topLeft_.x) * s * scale.x,
                  (xf_.origin.y - topLeft_.y) * s * scale.y, tw * k * scale.x, th * k * scale.y},
        {0, 0, tw / static_cast<float>(world_.w), th / static_cast<float>(world_.h)}, kWhite);
    batch_.flush();
}

SceneStats Scene::stats() const {
    SceneStats st;
    st.regionItems = placed_.size();
    st.drawnItems = drawnItems_;
    for (const Target* t : {&world_, &light_, &glow_, &shadow_})
        st.targetBytes += static_cast<std::size_t>(t->w) * static_cast<std::size_t>(t->h) * 4;
    st.groundBytes = ground_->bytes();
    st.groundSlotsRendered = ground_->slotsRendered();
    return st;
}

} // namespace lc
