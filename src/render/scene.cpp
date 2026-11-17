#include "render/scene.hpp"

#include "core/tuning.hpp"

#include <algorithm>
#include <cmath>
#include <numbers>
#include <queue>

namespace lc {
namespace {

constexpr float kCritterMoveFps = 6.0f;
constexpr float kCritterIdleFps = 2.0f;
constexpr SDL_FColor kWhite{1, 1, 1, 1};
constexpr SDL_FColor kInvalidTint{1.0f, 0.45f, 0.42f, 1.0f};
constexpr SDL_FColor kWarmLight{1.0f, 0.80f, 0.52f, 1.0f};

struct TileRect {
    float x0, y0, x1, y1;
};

TileRect tileRect(const Item& it) {
    return {static_cast<float>(it.pos.x), static_cast<float>(it.pos.y),
            static_cast<float>(it.pos.x + it.w), static_cast<float>(it.pos.y + it.h)};
}

TileRect pointRect(Vec2 p) {
    return {p.x - 0.01f, p.y - 0.01f, p.x + 0.01f, p.y + 0.01f};
}

// True when a must be drawn before b. Non-overlapping footprints are separated along at least
// one axis; the object further along +x or +y is nearer the viewer. When the separation is
// ambiguous (opposite directions, or overlap) the footprint centres decide.
bool behind(const TileRect& a, const TileRect& b) {
    const int sx = a.x1 <= b.x0 ? -1 : (b.x1 <= a.x0 ? 1 : 0);
    const int sy = a.y1 <= b.y0 ? -1 : (b.y1 <= a.y0 ? 1 : 0);
    if ((sx == 0 && sy == 0) || (sx != 0 && sy != 0 && sx != sy))
        return a.x0 + a.x1 + a.y0 + a.y1 <= b.x0 + b.x1 + b.y0 + b.y1;
    return (sx != 0 ? sx : sy) < 0;
}

template <typename R>
bool overlaps(const R& a, const R& b) {
    return a.x0 < b.x1 && b.x0 < a.x1 && a.y0 < b.y1 && b.y0 < a.y1;
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

} // namespace

Scene::Scene(SDL_Renderer* renderer, Atlas& atlas, const Catalog& cat)
    : renderer_(renderer), atlas_(atlas), cat_(cat), tables_(buildSpriteTables(atlas, cat)),
      batch_(renderer), popStart_(static_cast<std::size_t>(cat.mapW * cat.mapH), -1e9f) {
    placed_.reserve(static_cast<std::size_t>(cat.mapW * cat.mapH));
    entries_.reserve(static_cast<std::size_t>(cat.mapW * cat.mapH) + 256);
    lights_.reserve(256);
    chimneys_.reserve(64);
    water_.reserve(static_cast<std::size_t>(cat.mapW * cat.mapH));
    fades_.reserve(64);
    const WorldBounds b = islandBounds(cat.mapW, cat.mapH);
    constexpr float kPad = 8.0f;
    groundRect_ = {b.x0 - kPad, b.y0 - kPad, b.x1 + kPad, b.y1 + kPad};
}

int Scene::slotFor(const World& world, const Item& item) const {
    return cat_.items[item.type].layout == Layout::Connect ? world.itemMask(item.pos, item.type)
                                                           : item.variant;
}

Scene::Rect Scene::spriteRect(const Item& item, int slot) const {
    const Sprite& s =
        atlas_.sprite(tables_.items[item.type].base[static_cast<std::size_t>(slot)].frames.front());
    const Vec2 a = tileToWorld(static_cast<float>(item.pos.x), static_cast<float>(item.pos.y));
    return {a.x - s.ox, a.y - s.oy, a.x - s.ox + s.w, a.y - s.oy + s.h};
}

void Scene::rebuild(const World& world) {
    revision_ = world.revision();
    const auto items = world.items();
    const std::size_t n = items.size();

    // Topological order over pairs whose sprites can overlap on screen.
    std::vector<Placed> all;
    all.reserve(n);
    for (const Item& it : items) {
        const int slot = slotFor(world, it);
        const auto& def = cat_.items[it.type];
        const Rect r = spriteRect(it, slot);
        all.push_back({it, slot, r,
                       def.category == *cat_.findCategory("nature") && !def.walkable &&
                           r.y1 - r.y0 >= 30.0f});
    }
    std::vector<std::vector<std::uint16_t>> next(n);
    std::vector<int> indegree(n, 0);
    for (std::size_t i = 0; i < n; ++i) {
        for (std::size_t j = i + 1; j < n; ++j) {
            if (!overlaps(all[i].screen, all[j].screen)) continue;
            const bool ij = behind(tileRect(all[i].item), tileRect(all[j].item));
            const auto from = ij ? i : j;
            const auto to = ij ? j : i;
            next[from].push_back(static_cast<std::uint16_t>(to));
            ++indegree[to];
        }
    }
    const auto depth = [&](std::size_t i) {
        const auto& it = all[i].item;
        return static_cast<float>(it.pos.x * 2 + it.w + it.pos.y * 2 + it.h);
    };
    using Key = std::pair<float, std::size_t>;
    std::priority_queue<Key, std::vector<Key>, std::greater<>> ready;
    for (std::size_t i = 0; i < n; ++i)
        if (indegree[i] == 0) ready.push({depth(i), i});
    placed_.clear();
    std::vector<bool> done(n, false);
    while (placed_.size() < n) {
        if (ready.empty()) {
            // A cycle (only possible with contrived layouts): break it at the shallowest item.
            std::size_t pick = n;
            for (std::size_t i = 0; i < n; ++i)
                if (!done[i] && (pick == n || depth(i) < depth(pick))) pick = i;
            indegree[pick] = 0;
            ready.push({depth(pick), pick});
        }
        const auto [d, i] = ready.top();
        ready.pop();
        if (done[i]) continue;
        done[i] = true;
        placed_.push_back(all[i]);
        for (const auto j : next[i])
            if (--indegree[j] == 0 && !done[j]) ready.push({depth(j), j});
    }

    glowRects_.clear();
    for (const Placed& p : placed_)
        if (!tables_.items[p.item.type].glow[static_cast<std::size_t>(p.slot)].empty())
            glowRects_.push_back(p.screen);
    for (Placed& p : placed_)
        p.occludesGlow =
            std::ranges::any_of(glowRects_, [&](const Rect& g) { return overlaps(g, p.screen); });

    lights_.clear();
    chimneys_.clear();
    for (const Placed& p : placed_) {
        const auto& spr = tables_.items[p.item.type];
        const auto slot = static_cast<std::size_t>(p.slot);
        const Vec2 a =
            tileToWorld(static_cast<float>(p.item.pos.x), static_cast<float>(p.item.pos.y));
        if (slot < spr.light.size() && spr.light[slot]) {
            const float size = static_cast<float>(std::max(p.item.w, p.item.h));
            lights_.push_back(
                {{a.x + spr.light[slot]->x, a.y + spr.light[slot]->y}, 26.0f + 14.0f * size});
        }
        if (slot < spr.smoke.size() && spr.smoke[slot])
            chimneys_.push_back({a.x + spr.smoke[slot]->x, a.y + spr.smoke[slot]->y});
    }
    water_.clear();
    for (int y = 0; y < world.height(); ++y)
        for (int x = 0; x < world.width(); ++x)
            if (world.isWater({x, y})) water_.push_back({x, y});
}

void Scene::onPlaced(const Item& item, float now, Rng& rng) {
    popStart_[static_cast<std::size_t>(item.pos.y * cat_.mapW + item.pos.x)] = now;
    const Vec2 c = tileToWorld(static_cast<float>(item.pos.x) + item.w * 0.5f,
                               static_cast<float>(item.pos.y) + item.h * 0.5f);
    for (int i = 0; i < 3; ++i) {
        particles_.spawn(Fx::Sparkle,
                         {c.x + rng.range(-10.0f, 10.0f), c.y - rng.range(2.0f, 18.0f)}, {0, -6},
                         rng.range(0.4f, 0.7f));
    }
}

void Scene::onRemoved(const Item& item, float now) {
    if (fades_.size() == fades_.capacity()) fades_.erase(fades_.begin());
    // The connect mask is frozen at removal time; neighbours no longer include the item.
    fades_.push_back(
        {item, cat_.items[item.type].layout == Layout::Connect ? 0 : item.variant, now});
    popStart_[static_cast<std::size_t>(item.pos.y * cat_.mapW + item.pos.x)] = -1e9f;
}

void Scene::update(float dt, const World& world, bool rain, Rng& rng) {
    if (world.revision() != revision_) rebuild(world);
    now_ += dt;
    std::erase_if(fades_, [&](const Fade& f) { return now_ - f.start > tuning::kFadeOutSeconds; });

    for (const Vec2& c : chimneys_) {
        if (rng.chance(dt / tuning::kSmokeInterval))
            particles_.spawn(Fx::Smoke, {c.x + rng.range(-1.0f, 1.0f), c.y},
                             {rng.range(1.0f, 5.0f), rng.range(-12.0f, -8.0f)},
                             rng.range(2.2f, 3.2f));
    }
    if (!water_.empty()) {
        const float rate =
            static_cast<float>(water_.size()) * (rain ? tuning::kRainRipplesPerSecondPerWaterTile
                                                      : tuning::kRipplesPerSecondPerWaterTile);
        float expected = rate * dt;
        while (expected > 0) {
            if (rng.chance(std::min(1.0f, expected))) {
                const TilePos t = water_[static_cast<std::size_t>(
                    rng.range(0, static_cast<int>(water_.size()) - 1))];
                const Vec2 w = tileToWorld(static_cast<float>(t.x) + rng.range(0.25f, 0.75f),
                                           static_cast<float>(t.y) + rng.range(0.25f, 0.75f));
                particles_.spawn(Fx::Ripple, w, {0, 0}, 0.9f);
            }
            expected -= 1.0f;
        }
    }
    if (rain && view_.x1 > view_.x0) {
        const float area = (view_.x1 - view_.x0) * (view_.y1 - view_.y0) / (640.0f * 360.0f);
        float expected = tuning::kRainDropsPerSecond * area * dt;
        while (expected > 0) {
            if (rng.chance(std::min(1.0f, expected))) {
                constexpr float kFall = 90.0f;
                constexpr float kSpeed = 260.0f;
                const Vec2 ground{rng.range(view_.x0, view_.x1 + 40.0f),
                                  rng.range(view_.y0, view_.y1)};
                particles_.spawn(Fx::Raindrop, {ground.x + kFall * 0.15f, ground.y - kFall},
                                 {-kSpeed * 0.15f, kSpeed}, kFall / kSpeed);
            }
            expected -= 1.0f;
        }
    }
    for (const Placed& p : placed_) {
        if (!p.tree || !rng.chance(tuning::kLeavesPerSecondPerTree * dt)) continue;
        const float cx = (p.screen.x0 + p.screen.x1) * 0.5f;
        particles_.spawn(
            Fx::Leaf,
            {cx + rng.range(-8.0f, 8.0f), p.screen.y0 + (p.screen.y1 - p.screen.y0) * 0.35f},
            {rng.range(-4.0f, 4.0f), 9.0f}, 2.6f, rng.range(0.0f, 6.0f));
    }
    particles_.update(dt, world);
}

void Scene::ensureTargets(int w, int h) {
    if (w == targetW_ && h == targetH_ && worldTarget_) return;
    targetW_ = w;
    targetH_ = h;
    const auto make = [&](SDL_ScaleMode mode) {
        TexturePtr t{
            SDL_CreateTexture(renderer_, SDL_PIXELFORMAT_RGBA8888, SDL_TEXTUREACCESS_TARGET, w, h)};
        if (!t) {
            SDL_Log("render: cannot create %dx%d target: %s", w, h, SDL_GetError());
            return t;
        }
        if (!SDL_SetTextureScaleMode(t.get(), mode)) SDL_Log("render: %s", SDL_GetError());
        return t;
    };
    worldTarget_ = make(SDL_SCALEMODE_NEAREST);
    lightTarget_ = make(SDL_SCALEMODE_NEAREST);
    glowTarget_ = make(SDL_SCALEMODE_NEAREST);
}

void Scene::sprite(SpriteId id, Vec2 anchor, SDL_FColor color, bool mirror, Vec2 pivot,
                   Vec2 scale) {
    const Sprite& s = atlas_.sprite(id);
    const float x0 = mirror ? -(s.w - s.ox) : -s.ox;
    const float y0 = -s.oy;
    const auto place = [&](float lx, float ly) {
        const float wx = anchor.x + lx;
        const float wy = anchor.y + ly;
        return SDL_FPoint{pivot.x + (wx - pivot.x) * scale.x - origin_.x,
                          pivot.y + (wy - pivot.y) * scale.y - origin_.y};
    };
    const SDL_FPoint p[4] = {place(x0, y0), place(x0 + s.w, y0), place(x0 + s.w, y0 + s.h),
                             place(x0, y0 + s.h)};
    UvRect uv = s.uv;
    if (mirror) std::swap(uv.u0, uv.u1);
    batch_.quad(p, uv, color);
}

void Scene::drawItem(const Item& item, int slot, float alpha, SDL_FColor tint, bool silhouette,
                     float scaleY) {
    const auto& def = cat_.items[item.type];
    const auto& spr = tables_.items[item.type];
    const auto s = static_cast<std::size_t>(slot);
    const Vec2 anchor = tileToWorld(static_cast<float>(item.pos.x), static_cast<float>(item.pos.y));
    const Vec2 pivot = tileToWorld(static_cast<float>(item.pos.x) + item.w * 0.5f,
                                   static_cast<float>(item.pos.y) + item.h * 0.5f);
    Vec2 scale{1.0f, scaleY};
    const float t =
        (now_ - popStart_[static_cast<std::size_t>(item.pos.y * cat_.mapW + item.pos.x)]) /
        tuning::kPopSeconds;
    if (t >= 0.0f && t < 1.0f) {
        const float y = 0.35f + 0.65f * easeOutBack(t);
        scale = {1.0f + (1.0f - y) * 0.45f, y};
        alpha *= std::min(1.0f, t * 4.0f);
    }
    const std::uint32_t phase = tileHash(item.pos.x, item.pos.y) % 7;
    const SpriteId base = spr.base[s].at(now_, def.fps, phase);
    const SDL_FColor c = silhouette ? SDL_FColor{0, 0, 0, alpha}
                                    : SDL_FColor{tint.r, tint.g, tint.b, tint.a * alpha};
    sprite(base, anchor, c, false, pivot, scale);
}

void Scene::buildOrder(const FrameParams& p) {
    entries_.clear();
    for (std::size_t i = 0; i < placed_.size(); ++i)
        entries_.push_back({EntryKind::Static, static_cast<std::uint16_t>(i),
                            static_cast<int>(i) * 2 + 1, 0, false});

    const auto insert = [&](EntryKind kind, std::uint16_t index, const TileRect& tr,
                            const Rect& sr) {
        int after = 0;
        for (std::size_t i = 0; i < placed_.size(); ++i) {
            if (overlaps(placed_[i].screen, sr) && behind(tileRect(placed_[i].item), tr))
                after = static_cast<int>(i) + 1;
        }
        entries_.push_back({kind, index, after * 2, tr.x0 + tr.x1 + tr.y0 + tr.y1, nearGlow(sr)});
    };

    for (std::size_t i = 0; i < p.critters.size(); ++i) {
        const Critter& c = p.critters[i];
        if (cat_.visitors[c.visitor].habitat == Habitat::Air) continue;
        const Vec2 w = tileToWorld(c.pos.x, c.pos.y);
        insert(EntryKind::Critter, static_cast<std::uint16_t>(i), pointRect(c.pos),
               {w.x - 12, w.y - 24, w.x + 12, w.y + 2});
    }
    if (p.ghost.mode == Ghost::Mode::Item) {
        const int slot = slotFor(*p.world, p.ghost.item);
        insert(EntryKind::Ghost, 0, tileRect(p.ghost.item), spriteRect(p.ghost.item, slot));
    }
    for (std::size_t i = 0; i < fades_.size(); ++i)
        insert(EntryKind::Fade, static_cast<std::uint16_t>(i), tileRect(fades_[i].item),
               spriteRect(fades_[i].item, fades_[i].slot));

    std::ranges::sort(entries_, [](const Entry& a, const Entry& b) {
        return a.after != b.after ? a.after < b.after : a.depth < b.depth;
    });
}

void Scene::drawCritter(const Critter& c, const FrameParams& p, bool silhouette) {
    const auto& def = cat_.visitors[c.visitor];
    const bool back = c.facing == Facing::Back || c.facing == Facing::BackMirrored;
    const bool mirror = c.facing == Facing::FrontMirrored || c.facing == Facing::BackMirrored;
    const auto anim = static_cast<std::size_t>(
        c.moving ? (back ? CritterAnim::MoveBack : CritterAnim::MoveFront)
                 : (back ? CritterAnim::IdleBack : CritterAnim::IdleFront));
    const FrameSet& set = tables_.critters[c.visitor][anim];
    const SpriteId id = set.at(c.animTime, c.moving ? kCritterMoveFps : kCritterIdleFps);
    Vec2 w = tileToWorld(c.pos.x, c.pos.y);
    if (def.habitat == Habitat::Air) w.y -= c.hover + std::sin(c.animTime * 3.1f) * 2.0f;
    w = {std::round(w.x), std::round(w.y)};
    const float a = std::clamp(c.alpha, 0.0f, 1.0f);
    sprite(id, w, silhouette ? SDL_FColor{0, 0, 0, a} : SDL_FColor{1, 1, 1, a}, mirror);
    (void)p;
}

void Scene::drawEntries(const FrameParams& p, bool silhouette) {
    const float glow = p.light.glow;
    const World& world = *p.world;
    const Item* removeTarget =
        p.ghost.mode == Ghost::Mode::Remove ? world.itemAt(p.ghost.tile) : nullptr;
    for (const Entry& e : entries_) {
        // The glow pass only needs what can hide an emissive pixel.
        if (silhouette &&
            !(e.kind == EntryKind::Static ? placed_[e.index].occludesGlow : e.occludesGlow))
            continue;
        switch (e.kind) {
        case EntryKind::Static: {
            const Placed& pl = placed_[e.index];
            const bool marked = removeTarget != nullptr && *removeTarget == pl.item;
            drawItem(pl.item, pl.slot, 1.0f, marked ? kInvalidTint : kWhite, silhouette);
            const auto& glowSet =
                tables_.items[pl.item.type].glow[static_cast<std::size_t>(pl.slot)];
            if (silhouette && !glowSet.empty()) {
                const Vec2 a = tileToWorld(static_cast<float>(pl.item.pos.x),
                                           static_cast<float>(pl.item.pos.y));
                const auto& def = cat_.items[pl.item.type];
                sprite(glowSet.at(now_, def.fps, tileHash(pl.item.pos.x, pl.item.pos.y) % 7), a,
                       {glow, glow, glow, 1.0f});
            }
            break;
        }
        case EntryKind::Critter: drawCritter(p.critters[e.index], p, silhouette); break;
        case EntryKind::Ghost: {
            const int slot = slotFor(world, p.ghost.item);
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
    // Flyers are always above the ground clutter.
    for (const Critter& c : p.critters) {
        if (cat_.visitors[c.visitor].habitat != Habitat::Air) continue;
        const Vec2 w = tileToWorld(c.pos.x, c.pos.y);
        if (silhouette && !nearGlow({w.x - 8, w.y - c.hover - 12, w.x + 8, w.y - c.hover + 4}))
            continue;
        drawCritter(c, p, silhouette);
    }
}

bool Scene::nearGlow(const Rect& r) const {
    return std::ranges::any_of(glowRects_, [&](const Rect& g) { return overlaps(g, r); });
}

void Scene::renderGroundCache(const World& world) {
    const int w = world.width();
    const int h = world.height();
    const auto gw = static_cast<int>(groundRect_.x1 - groundRect_.x0);
    const auto gh = static_cast<int>(groundRect_.y1 - groundRect_.y0);
    if (!ground_) {
        ground_.reset(SDL_CreateTexture(renderer_, SDL_PIXELFORMAT_RGBA8888,
                                        SDL_TEXTUREACCESS_TARGET, gw, gh));
        if (!ground_ || !SDL_SetTextureScaleMode(ground_.get(), SDL_SCALEMODE_NEAREST)) {
            SDL_Log("render: ground cache: %s", SDL_GetError());
            return;
        }
    }
    if (!SDL_SetRenderTarget(renderer_, ground_.get()) ||
        !SDL_SetRenderDrawColorFloat(renderer_, 0, 0, 0, 0) || !SDL_RenderClear(renderer_)) {
        SDL_Log("render: ground cache: %s", SDL_GetError());
    }
    const Vec2 saved = origin_;
    origin_ = {groundRect_.x0, groundRect_.y0};
    batch_.use(atlas_.texture(), SDL_BLENDMODE_BLEND);
    for (int y = 0; y < h; ++y)
        sprite(tables_.cliffSE, tileToWorld(static_cast<float>(w - 1), static_cast<float>(y)),
               kWhite);
    for (int x = 0; x < w; ++x)
        sprite(tables_.cliffSW, tileToWorld(static_cast<float>(x), static_cast<float>(h - 1)),
               kWhite);
    const auto& baseVariants = tables_.terrainBase[static_cast<std::size_t>(cat_.baseTerrain)];
    for (int s = 0; s <= w + h - 2; ++s) {
        for (int x = std::max(0, s - h + 1); x <= std::min(s, w - 1); ++x) {
            const int y = s - x;
            const Vec2 a = tileToWorld(static_cast<float>(x), static_cast<float>(y));
            sprite(baseVariants[tileHash(x, y, 1) % baseVariants.size()], a, kWhite);
            const int t = world.terrainAt({x, y});
            if (t == cat_.baseTerrain) continue;
            const auto& def = cat_.terrain[static_cast<std::size_t>(t)];
            const FrameSet& set =
                tables_.terrainOverlay[static_cast<std::size_t>(t)]
                                      [static_cast<std::size_t>(world.terrainMask({x, y}))];
            sprite(set.at(now_, def.fps), a, kWhite);
        }
    }
    batch_.flush();
    origin_ = saved;
    if (!SDL_SetRenderTarget(renderer_, worldTarget_.get())) SDL_Log("render: %s", SDL_GetError());
}

void Scene::drawGround(const World& world) {
    // The cache key folds in the current frame of every animated terrain.
    std::uint64_t key = world.revision() * 1000003ULL;
    for (const auto& t : cat_.terrain)
        key = key * 31 + (t.fps > 0 ? static_cast<std::uint64_t>(now_ * t.fps) : 0);
    if (key != groundKey_ || !ground_) {
        batch_.flush();
        renderGroundCache(world);
        groundKey_ = key;
    }
    if (!ground_) return;
    batch_.use(ground_.get(), SDL_BLENDMODE_BLEND);
    batch_.quad(SDL_FRect{groundRect_.x0 - origin_.x, groundRect_.y0 - origin_.y,
                          groundRect_.x1 - groundRect_.x0, groundRect_.y1 - groundRect_.y0},
                {0, 0, 1, 1}, kWhite);
    batch_.use(atlas_.texture(), SDL_BLENDMODE_BLEND);
}

void Scene::drawShadows(const FrameParams& p) {
    for (const Placed& pl : placed_) {
        const auto& set = tables_.items[pl.item.type].shadow[static_cast<std::size_t>(pl.slot)];
        if (set.empty()) continue;
        const float t =
            (now_ -
             popStart_[static_cast<std::size_t>(pl.item.pos.y * cat_.mapW + pl.item.pos.x)]) /
            tuning::kPopSeconds;
        const float a = t >= 0.0f && t < 1.0f ? t : 1.0f;
        sprite(set.frames.front(),
               tileToWorld(static_cast<float>(pl.item.pos.x), static_cast<float>(pl.item.pos.y)),
               {1, 1, 1, a});
    }
    for (const Critter& c : p.critters) {
        const bool air = cat_.visitors[c.visitor].habitat == Habitat::Air;
        if (cat_.visitors[c.visitor].habitat == Habitat::Water) continue;
        const Vec2 w = tileToWorld(c.pos.x, c.pos.y);
        sprite(atlas_.softShadow(), {std::round(w.x), std::round(w.y)},
               {1, 1, 1, std::clamp(c.alpha, 0.0f, 1.0f) * (air ? 0.45f : 1.0f)}, false,
               {std::round(w.x), std::round(w.y)}, air ? Vec2{0.5f, 0.5f} : Vec2{0.7f, 0.7f});
    }
    // Placement markers sit on the ground under everything else.
    const World& world = *p.world;
    const auto marker = [&](TilePos t, bool ok) {
        if (world.inBounds(t))
            sprite(ok ? tables_.tileOk : tables_.tileBad,
                   tileToWorld(static_cast<float>(t.x), static_cast<float>(t.y)), {1, 1, 1, 0.9f});
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
    for (const Particle& pt : particles_.all()) {
        if ((pt.kind == Fx::Ripple) != ground) continue;
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
    if (!SDL_SetRenderTarget(renderer_, lightTarget_.get()) ||
        !SDL_SetRenderDrawColorFloat(renderer_, amb.r, amb.g, amb.b, 1.0f) ||
        !SDL_RenderClear(renderer_)) {
        SDL_Log("render: light map: %s", SDL_GetError());
    }
    const float glow = p.light.glow;
    if (glow > 0.01f) {
        batch_.use(atlas_.texture(), SDL_BLENDMODE_ADD);
        const SDL_FColor warm = scaled(kWarmLight, 0.6f * glow);
        for (const Light& l : lights_) {
            const float s = l.radius / 32.0f;
            sprite(atlas_.lightBlob(), l.pos, warm, false, l.pos, {s, s * 0.75f});
        }
        for (const Critter& c : p.critters) {
            if (cat_.visitors[c.visitor].time != VisitTime::Night) continue;
            Vec2 w = tileToWorld(c.pos.x, c.pos.y);
            w.y -= c.hover;
            const float pulse = 0.6f + 0.4f * std::sin(c.animTime * 4.0f);
            sprite(atlas_.lightBlob(), w,
                   scaled({0.75f, 1.0f, 0.55f, 1.0f}, 0.5f * glow * pulse * c.alpha), false, w,
                   {0.35f, 0.3f});
        }
        batch_.flush();
    }
    if (!SDL_SetRenderTarget(renderer_, worldTarget_.get())) SDL_Log("render: %s", SDL_GetError());
    batch_.use(lightTarget_.get(), SDL_BLENDMODE_MUL);
    batch_.quad(SDL_FRect{0, 0, static_cast<float>(targetW_), static_cast<float>(targetH_)},
                {0, 0, 1, 1}, kWhite);
    batch_.flush();
}

void Scene::drawGlow(const FrameParams& p) {
    const float glow = p.light.glow;
    if (glow <= 0.01f) return;
    if (!SDL_SetRenderTarget(renderer_, glowTarget_.get()) ||
        !SDL_SetRenderDrawColorFloat(renderer_, 0, 0, 0, 0) || !SDL_RenderClear(renderer_)) {
        SDL_Log("render: glow: %s", SDL_GetError());
    }
    batch_.use(atlas_.texture(), SDL_BLENDMODE_BLEND);
    drawEntries(p, true);
    batch_.use(atlas_.texture(), SDL_BLENDMODE_ADD);
    for (const Critter& c : p.critters) {
        if (cat_.visitors[c.visitor].time != VisitTime::Night) continue;
        Vec2 w = tileToWorld(c.pos.x, c.pos.y);
        w.y -= c.hover + std::sin(c.animTime * 3.1f) * 2.0f;
        const float pulse = 0.55f + 0.45f * std::sin(c.animTime * 4.0f);
        sprite(atlas_.lightBlob(), w, scaled({0.8f, 1.0f, 0.5f, 1.0f}, glow * pulse * c.alpha),
               false, w, {0.12f, 0.12f});
    }
    batch_.flush();
    if (!SDL_SetRenderTarget(renderer_, worldTarget_.get())) SDL_Log("render: %s", SDL_GetError());
    batch_.use(glowTarget_.get(), SDL_BLENDMODE_ADD);
    batch_.quad(SDL_FRect{0, 0, static_cast<float>(targetW_), static_cast<float>(targetH_)},
                {0, 0, 1, 1}, kWhite);
    batch_.flush();
}

void Scene::draw(const FrameParams& p) {
    batch_.resetStats();
    const World& world = *p.world;
    if (world.revision() != revision_) rebuild(world);

    const auto z = static_cast<float>(p.camera->zoom());
    const Vec2 cam = p.camera->position();
    const Vec2 topLeft{cam.x - p.screen.x * 0.5f / z, cam.y - p.screen.y * 0.5f / z};
    origin_ = {std::floor(topLeft.x) - 1.0f, std::floor(topLeft.y) - 1.0f};
    ensureTargets(static_cast<int>(std::ceil(p.screen.x / z)) + 3,
                  static_cast<int>(std::ceil(p.screen.y / z)) + 3);
    if (!worldTarget_ || !lightTarget_ || !glowTarget_) return;
    view_ = {origin_.x, origin_.y, origin_.x + static_cast<float>(targetW_),
             origin_.y + static_cast<float>(targetH_)};

    if (!SDL_SetRenderTarget(renderer_, worldTarget_.get()) ||
        !SDL_SetRenderDrawColorFloat(renderer_, 0, 0, 0, 0) || !SDL_RenderClear(renderer_)) {
        SDL_Log("render: world target: %s", SDL_GetError());
    }
    buildOrder(p);
    batch_.use(atlas_.texture(), SDL_BLENDMODE_BLEND);
    drawGround(world);
    drawShadows(p);
    drawParticles(true);
    drawEntries(p, false);
    drawParticles(false);
    batch_.flush();
    drawLighting(p);
    drawGlow(p);

    if (!SDL_SetRenderTarget(renderer_, nullptr)) SDL_Log("render: %s", SDL_GetError());
    // Sky gradient behind the floating island.
    const Rgb t = p.light.skyTop;
    const Rgb b = p.light.skyBottom;
    const SDL_Vertex sky[4] = {
        {{0, 0}, {t.r, t.g, t.b, 1}, {0, 0}},
        {{p.screen.x, 0}, {t.r, t.g, t.b, 1}, {0, 0}},
        {{p.screen.x, p.screen.y}, {b.r, b.g, b.b, 1}, {0, 0}},
        {{0, p.screen.y}, {b.r, b.g, b.b, 1}, {0, 0}},
    };
    static constexpr int kQuad[6] = {0, 1, 2, 0, 2, 3};
    batch_.use(nullptr, SDL_BLENDMODE_NONE);
    batch_.triangles(sky, 4, kQuad, 6);
    batch_.use(worldTarget_.get(), SDL_BLENDMODE_BLEND);
    batch_.quad(SDL_FRect{(origin_.x - topLeft.x) * z, (origin_.y - topLeft.y) * z,
                          static_cast<float>(targetW_) * z, static_cast<float>(targetH_) * z},
                {0, 0, 1, 1}, kWhite);
    batch_.flush();
}

} // namespace lc
