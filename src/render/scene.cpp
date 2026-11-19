#include "render/scene.hpp"

#include "core/land.hpp"
#include "core/tuning.hpp"
#include "render/bands.hpp"
#include "render/decks.hpp"

#include <algorithm>
#include <cmath>
#include <deque>

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
    // Actors reach as far as their tallest frame, lifted onto the highest perch or flight.
    float lift = tuning::kHoverMax * iso_.tileH() + 2;
    for (const auto& def : cat.items)
        for (const int p : def.perch) lift = std::max(lift, static_cast<float>(p) + 2);
    for (const auto& anims : tables_.kinds)
        for (const KindAnim& ka : anims)
            for (const FrameSet* set : {&ka.front, &ka.back})
                for (const SpriteId id : set->frames) grow(itemReach_, atlas_.sprite(id), lift);
    lights_.reserve(256);
    chimneys_.reserve(64);
    fades_.reserve(kMaxFades);
    pops_.reserve(kMaxPops);
    pulses_.reserve(16);
    dynamic_.reserve(256);
    dynamicBoxes_.reserve(256);
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

bool Scene::flying(const Actor& a) const {
    return inAir(a, cat_.kinds[a.kind]);
}

bool Scene::glows(const Actor& a) const {
    const int v = cat_.kinds[a.kind].visitor;
    return v >= 0 && cat_.visitors[static_cast<std::size_t>(v)].glow;
}

std::size_t Scene::animOf(const Actor& a) const {
    const ActorKind& k = cat_.kinds[a.kind];
    if (a.overlay > 0) return a.overlayAnim;
    const bool moving =
        a.state == ActorState::Travel ||
        (a.state == ActorState::Follow && a.anim == 0 && (a.flags & actor_flag::kOnHat) == 0);
    if (!moving) return a.anim;
    // Walking with goods, under rain, or a swimmer on land: their own walks where drawn.
    if (k.carryAnim != 0xFF && a.goodsCount > 0) return k.carryAnim;
    if (k.rainAnim != 0xFF && weather_ != nullptr && weather_->raining(a.pos)) return k.rainAnim;
    if (k.waddleAnim != 0xFF && map_ != nullptr) {
        const TilePos t{static_cast<int>(std::floor(a.pos.x)),
                        static_cast<int>(std::floor(a.pos.y))};
        if (map_->hasGround(t) && !map_->isWater(t)) return k.waddleAnim;
    }
    return 0;
}

Vec2 Scene::actorAnchor(const Actor& a) const {
    if ((a.flags & actor_flag::kOnHat) != 0 && resident_ >= 0 &&
        std::cmp_less(resident_, actors_.size())) {
        // Resting on her hat: just above the top of her current frame.
        const Vec2 h = headOf(actors_[static_cast<std::size_t>(resident_)]);
        return {h.x, h.y + 2};
    }
    Vec2 w = iso_.toWorld(a.pos.x, a.pos.y);
    w.y -= a.lift + (onDecks(a) ? deckAt(a.pos) : 0.0f);
    if (cat_.kinds[a.kind].move == Locomotion::Fly && a.state != ActorState::Act)
        w.y -= std::sin(a.animTime * 3.1f) * 0.12f * iso_.tileH();
    return snapped(w);
}

Vec2 Scene::snapped(Vec2 w) const {
    // Moving things sit on the target's pixels, not the art's: at 2x and 3x the target has two
    // or three texels per art pixel, and a walker placed to whole art pixels would move in
    // jumps of that many window pixels and stand still one frame in four (L-105).
    const float res = std::max(1.0f, xf_.res);
    return {std::round(w.x * res) / res, std::round(w.y * res) / res};
}

FRect Scene::actorRect(const Actor& a) const {
    const KindAnim& ka = tables_.kinds[a.kind][animOf(a)];
    const Sprite& s = atlas_.sprite(ka.front.frames.front());
    const Vec2 w = actorAnchor(a);
    // Mirrored frames flip about the anchor, so take the wider side both ways.
    const float half = std::max(s.ox, s.w - s.ox);
    return {w.x - half, w.y - s.oy, w.x + half, w.y - s.oy + s.h};
}

Vec2 Scene::headOf(const Actor& a) const {
    const FRect r = actorRect(a);
    return {(r.x0 + r.x1) * 0.5f, r.y0};
}

std::optional<int> Scene::actorAt(std::span<const Actor> actors, Vec2 world) const {
    // The topmost as drawn: the last in the frame's order.
    std::optional<int> best;
    float bestDepth = -1e9f;
    const float inflate = tuning::kPetHitInflate * iso_.tileW() / 64.0f;
    for (std::size_t i = 0; i < actors.size(); ++i) {
        const Actor& a = actors[i];
        if ((a.flags & actor_flag::kAlive) == 0 || a.alpha < 0.5f) continue;
        const FRect r = actorRect(a);
        if (world.x < r.x0 - inflate || world.x > r.x1 + inflate || world.y < r.y0 - inflate ||
            world.y > r.y1 + inflate)
            continue;
        const float depth = i < actorRank_.size() && actorRank_[i] >= 0
                                ? actorRank_[i]
                                : a.pos.x + a.pos.y + (flying(a) ? 1000.0f : 0.0f);
        if (depth > bestDepth) {
            bestDepth = depth;
            best = static_cast<int>(i);
        }
    }
    return best;
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
    gathered_.clear();
    world.forEachItemIn(region, [&](const Item& it) {
        const int slot = slotFor(world, it);
        const auto& def = cat_.items[it.type];
        const FRect r = spriteRect(it, slot);
        // Trees drop leaves (or petals), as the catalog says.
        const bool tree = def.sheds != Shed::None;
        if (railed(def)) {
            gathered_.push_back({it, slot, r, tree, false, 0});
            gathered_.push_back({it, slot, r, tree, false, 1});
        } else {
            gathered_.push_back({it, slot, r, tree, false, -1});
        }
    });
    sorting_.clear();
    for (std::size_t i = 0; i < gathered_.size(); ++i)
        sorting_.push_back(itemBox(gathered_[i], static_cast<std::uint32_t>(i)));
    sorter_.sort(sorting_, 2 * iso_.tileW(), order_, graph_);
    placed_.clear();
    boxes_.clear();
    identity_.clear();
    std::vector<std::uint32_t>& rank = identity_; // borrowed: gathered item -> place
    rank.assign(order_.size(), 0);
    for (std::size_t k = 0; k < order_.size(); ++k) rank[order_[k]] = static_cast<std::uint32_t>(k);
    // The graph by place in the order, as the merge reads it with the placed items.
    {
        const OrderGraph byItem = graph_;
        graph_.start.assign(order_.size() + 1, 0);
        graph_.next.clear();
        for (std::size_t k = 0; k < order_.size(); ++k) {
            const std::uint32_t i = order_[k];
            for (std::uint32_t q = byItem.start[i]; q < byItem.start[i + 1]; ++q)
                graph_.next.push_back(rank[byItem.next[q]]);
            graph_.start[k + 1] = static_cast<std::uint32_t>(graph_.next.size());
        }
    }
    for (std::size_t k = 0; k < order_.size(); ++k) {
        placed_.push_back(gathered_[order_[k]]);
        boxes_.push_back(sorting_[order_[k]]);
        boxes_.back().box.id = depthId(DepthKind::Item, static_cast<std::uint32_t>(k));
    }
    identity_.resize(placed_.size());
    for (std::size_t k = 0; k < identity_.size(); ++k) identity_[k] = static_cast<std::uint32_t>(k);
    {
        std::vector<FRect> screens;
        screens.reserve(placed_.size());
        for (const Placed& pl : placed_) screens.push_back(pl.screen);
        grid_.build(screens, 2 * iso_.tileW());
    }
    merge_.index(boxes_, identity_, graph_, 2 * iso_.tileW());

    glowRects_.clear();
    lights_.clear();
    chimneys_.clear();
    moths_.clear();
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
                {{a.x + static_cast<float>(smoke[slot].x), a.y + static_cast<float>(smoke[slot].y)},
                 p.item.pos});
        if (spr.glow[slot].empty()) continue;
        // Lamp heads (lights that do not flicker like a fire) draw moths at night.
        const auto& idef = cat_.items[p.item.type];
        if (const auto& head = spr.light[slot];
            idef.fps <= 0 && head && cat_.hasTag(p.item.type, "light"))
            moths_.push_back({a.x + head->x, a.y + head->y});
        // Only what can hide an emissive pixel needs the glow pass: use the glow art's bounds.
        const Sprite& gs = atlas_.sprite(spr.glow[slot].frames.front());
        const FRect glowBox{a.x - gs.ox, a.y - gs.oy, a.x - gs.ox + gs.w, a.y - gs.oy + gs.h};
        glowRects_.push_back(glowBox);
        // Things behind the light cannot cover it.
        grid_.query(glowBox, [&](std::uint32_t j) {
            if (placed_[j].screen.overlaps(glowBox) &&
                (j == i || (constrains(boxes_[i].box, boxes_[j].box) &&
                            drawnBefore(boxes_[i].box, boxes_[j].box))))
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
    falls_.clear();
    world.forEachChunkIn(region, [&](int cx, int cy) {
        if (world.chunkTerrainCount(cx, cy, cat_.waterTerrain) == 0) return;
        const TileRect r =
            TileRect{cx * kChunk, cy * kChunk, (cx + 1) * kChunk, (cy + 1) * kChunk}.clipped(
                region);
        for (int y = r.y0; y < r.y1; ++y)
            for (int x = r.x0; x < r.x1; ++x) {
                if (!world.isWater({x, y}) || world.isWild({x, y})) continue;
                water_.push_back({x, y});
                // Water at a rim falls over it; mist rises at the foot of the fall.
                const Vec2 a = iso_.toWorld(TilePos{x, y});
                const float foot = tuning::kMistDrop * iso_.tileH();
                if (!floating_) continue;
                if (!world.hasGround({x + 1, y}))
                    falls_.push_back({{a.x + iso_.hw * 0.5f, a.y + iso_.hh * 1.5f + foot}});
                if (!world.hasGround({x, y + 1}))
                    falls_.push_back({{a.x - iso_.hw * 0.5f, a.y + iso_.hh * 1.5f + foot}});
            }
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

void Scene::popAt(TilePos origin) {
    if (pops_.size() == kMaxPops) pops_.erase(pops_.begin());
    std::erase_if(pops_, [&](const Pop& p) { return p.origin == origin; });
    pops_.push_back({origin, now_});
}

void Scene::produce(const Item& bed, int crop) {
    const auto f = [](int v) { return static_cast<float>(v); };
    const Vec2 c = iso_.toWorld(f(bed.pos.x) + f(bed.w) * 0.5f, f(bed.pos.y) + f(bed.h) * 0.5f);
    const float u = iso_.tileH();
    particles_.spawn(Fx::Produce, {c.x, c.y - 0.6f * u}, {0, -tuning::kProduceRise * u},
                     tuning::kProduceSeconds, static_cast<float>(crop));
}

void Scene::flourish(const NearInstance& nook, const World& world, Rng& rng) {
    if (!reduceMotion_) pulses_.push_back({nook, now_}); // the ring is motion; sparkles stay
    const TileRect& f = nook.footprint;
    for (int i = 0; i < 8; ++i) {
        const TilePos t{rng.range(f.x0 - nook.within, f.x1 + nook.within - 1),
                        rng.range(f.y0 - nook.within, f.y1 + nook.within - 1)};
        if (world.hasGround(t))
            burst({static_cast<float>(t.x) + 0.5f, static_cast<float>(t.y) + 0.5f}, rng);
    }
}

float Scene::landWave(const World& world, const Catalog& cat, int stage,
                      std::span<const Item> revealed) {
    // Steps from the land that was already open, through the stage's tiles.
    const StageDef& def = cat.stages[static_cast<std::size_t>(stage)];
    std::vector<int> dist(static_cast<std::size_t>(world.width() * world.height()), -1);
    const auto idx = [&](TilePos p) { return static_cast<std::size_t>(p.y * world.width() + p.x); };
    const auto inStage = [&](TilePos p) { return world.inBounds(p) && stageAt(cat, p) == stage; };
    std::deque<TilePos> open;
    for (const TileRect& r : def.rects)
        for (int y = r.y0; y < r.y1; ++y)
            for (int x = r.x0; x < r.x1; ++x)
                for (const TilePos d :
                     {TilePos{1, 0}, TilePos{-1, 0}, TilePos{0, 1}, TilePos{0, -1}}) {
                    const TilePos q{x + d.x, y + d.y};
                    if (world.hasGround(q) && !inStage(q) && !world.isWild(q) &&
                        dist[idx({x, y})] < 0) {
                        dist[idx({x, y})] = 0;
                        open.push_back({x, y});
                    }
                }
    while (!open.empty()) {
        const TilePos p = open.front();
        open.pop_front();
        for (const TilePos d : {TilePos{1, 0}, TilePos{-1, 0}, TilePos{0, 1}, TilePos{0, -1}}) {
            const TilePos q{p.x + d.x, p.y + d.y};
            if (inStage(q) && dist[idx(q)] < 0) {
                dist[idx(q)] = dist[idx(p)] + 1;
                open.push_back(q);
            }
        }
    }
    wave_.clear();
    float longest = 0;
    for (const TileRect& r : def.rects)
        for (int y = r.y0; y < r.y1; ++y)
            for (int x = r.x0; x < r.x1; ++x) {
                // With reduce motion the land opens in one short fade instead of a wave.
                const float delay = reduceMotion_
                                        ? 0.0f
                                        : static_cast<float>(std::max(0, dist[idx({x, y})])) *
                                              tuning::kLandWaveStep;
                longest = std::max(longest, delay);
                wave_.push_back({{x, y}, now_ + delay, thicketAt(tables_, {x, y})});
            }
    // Revealed items pop up as the wave reaches them (invisible until then).
    for (const Item& it : revealed) {
        if (pops_.size() == kMaxPops) break;
        pops_.push_back(
            {it.pos, now_ + (reduceMotion_ ? 0.0f
                                           : static_cast<float>(std::max(0, dist[idx(it.pos)])) *
                                                 tuning::kLandWaveStep)});
    }
    waveEnd_ = now_ + longest + tuning::kLandClearFade;
    return longest + tuning::kLandClearFade;
}

void Scene::drawArea(const World& world, const NearInstance& area, SDL_FColor color) {
    const TileRect& f = area.footprint;
    for (int y = f.y0 - area.within; y < f.y1 + area.within; ++y)
        for (int x = f.x0 - area.within; x < f.x1 + area.within; ++x)
            if (!f.contains(TilePos{x, y}) && world.hasGround({x, y}))
                sprite(tables_.tileArea, iso_.toWorld(TilePos{x, y}), color);
}

void Scene::resetWorld() {
    ground_->invalidate();
    regionRevision_ = ~0ULL;
    fades_.clear();
    pops_.clear();
    pulses_.clear();
    wave_.clear();
    waveEnd_ = 0;
    rustles_.clear();
    cooking_.reset();
    star_ = {};
    particles_.clear();
    season_ = -1;
}

void Scene::onRemoved(const Item& item) {
    if (fades_.size() == kMaxFades) fades_.erase(fades_.begin());
    // The connect mask is frozen at removal time; neighbours no longer include the item.
    fades_.push_back(
        {item, cat_.items[item.type].layout == Layout::Connect ? 0 : item.variant, now_});
    std::erase_if(pops_, [&](const Pop& p) { return p.origin == item.pos; });
}

const FrameSet& Scene::baseFrames(const Item& item, int slot) const {
    const ItemSprites& spr = tables_.items[item.type];
    const auto s = static_cast<std::size_t>(slot);
    return item.stage < spr.stages.size() ? spr.stages[item.stage][s] : spr.base[s];
}

void Scene::setSeason(int season) {
    if (season == season_) return;
    season_ = season;
    tables_ = buildSpriteTables(atlas_, cat_, season);
    ground_->invalidate();
    regionRevision_ = ~0ULL;
}

void Scene::update(float dt, const World& world, std::span<const Actor> actors,
                   const Weather& weather, Rng& rng) {
    const SeasonDef* season =
        season_ >= 0 ? &cat_.seasons[static_cast<std::size_t>(season_)] : nullptr;
    weather_ = &weather;
    map_ = &world;
    wind_ = weather.wind();
    const bool snow = season != nullptr && season->snow;
    now_ += dt;
    // Trees and grass sway faster in a stronger wind.
    sway_ += dt * (tuning::kSwayCalm + tuning::kSwayWind * wind_.strength);
    std::erase_if(fades_, [&](const Fade& f) { return now_ - f.start > tuning::kFadeOutSeconds; });
    std::erase_if(pops_, [&](const Pop& p) { return now_ - p.start > tuning::kPopSeconds; });
    std::erase_if(rustles_, [&](const Rustle& r) { return now_ > r.end; });
    for (WaveTile& w : wave_) {
        if (w.cleared || now_ < w.start) continue;
        w.cleared = true;
        if (w.thicket)
            particles_.spawn(Fx::Clear,
                             iso_.toWorld(static_cast<float>(w.tile.x) + 0.5f,
                                          static_cast<float>(w.tile.y) + 0.5f),
                             {0, 0}, tuning::kLandClearFade * 1.5f);
    }
    if (!wave_.empty() && now_ > waveEnd_) wave_.clear();
    std::erase_if(pulses_,
                  [&](const Pulse& p) { return now_ - p.start > tuning::kNookPulseSeconds; });
    const float u = iso_.tileH();
    // The wind's lean on screen: its x component in window space, -1..1.
    const float lean = (wind_.dir.x - wind_.dir.y) * 0.7071f * wind_.strength;

    for (const Chimney& c : chimneys_) {
        // A cooking chimney puffs twice as often, two puffs at a time.
        const bool cook = cooking_ && *cooking_ == c.origin;
        const float rate = (cook ? 2.0f : 1.0f) / tuning::kSmokeInterval;
        if (!rng.chance(dt * rate)) continue;
        for (int n = 0; n < (cook ? 2 : 1); ++n)
            particles_.spawn(
                Fx::Smoke, {c.at.x + rng.range(-1.0f, 1.0f), c.at.y},
                {(rng.range(0.05f, tuning::kSmokeDriftMax) + lean * tuning::kSmokeLean) * u,
                 -rng.range(tuning::kSmokeRiseMin, tuning::kSmokeRiseMax) * u},
                rng.range(2.2f, 3.2f));
    }
    const auto spawnMany = [&](float expected, auto&& one) {
        while (expected > 0) {
            if (rng.chance(std::min(1.0f, expected))) one();
            expected -= 1.0f;
        }
    };
    const auto rainHere = [&](Vec2 groundPx) { return weather.rainAt(iso_.toTile(groundPx)); };
    if (!water_.empty()) {
        spawnMany(
            static_cast<float>(water_.size()) * tuning::kRipplesPerSecondPerWaterTile * dt, [&] {
                const TilePos t = water_[static_cast<std::size_t>(
                    rng.range(0, static_cast<int>(water_.size()) - 1))];
                const Vec2 w = iso_.toWorld(static_cast<float>(t.x) + rng.range(0.25f, 0.75f),
                                            static_cast<float>(t.y) + rng.range(0.25f, 0.75f));
                particles_.spawn(Fx::Ripple, w, {0, 0}, tuning::kRippleSeconds + 0.1f);
            });
        // Rain stipples the water where it falls.
        if (!snow)
            spawnMany(
                static_cast<float>(water_.size()) * tuning::kRainRipplesPerSecondPerWaterTile * dt,
                [&] {
                    const TilePos t = water_[static_cast<std::size_t>(
                        rng.range(0, static_cast<int>(water_.size()) - 1))];
                    const Vec2 w = iso_.toWorld(static_cast<float>(t.x) + rng.range(0.25f, 0.75f),
                                                static_cast<float>(t.y) + rng.range(0.25f, 0.75f));
                    if (rng.chance(rainHere(w)))
                        particles_.spawn(Fx::Ripple, w, {0, 0}, tuning::kRippleSeconds + 0.1f);
                });
    }
    const bool anyRain = weather.mode() == WeatherMode::Rain ||
                         (weather.mode() == WeatherMode::Natural &&
                          std::ranges::any_of(weather.cells(), [](const WeatherCell& c) {
                              return c.rain && c.age >= 0;
                          }));
    if (anyRain && view_.x1 > view_.x0) {
        const float tiles =
            (view_.x1 - view_.x0) * (view_.y1 - view_.y0) / (iso_.tileW() * iso_.hh);
        const float fall = tuning::kRainFall * u;
        const float speed = tuning::kRainSpeed * u;
        // Keep room in the pool for smoke, ripples and leaves however large the view.
        const float maxRate = tuning::kRainPoolShare * static_cast<float>(Particles::kCapacity) /
                              (fall / speed + tuning::kSplashSeconds);
        const float rate = std::min(tuning::kRainDropsPerSecondPerTile * tiles, maxRate) * thin_;
        // Drops fall only where a shower is, slanting with the wind.
        const float slant = 0.15f + lean * tuning::kRainLean;
        if (snow) {
            const float slow = tuning::kSnowSpeed * u;
            spawnMany(rate * tuning::kSnowShare * dt, [&] {
                const Vec2 ground{rng.range(view_.x0, view_.x1), rng.range(view_.y0, view_.y1)};
                if (!rng.chance(rainHere(ground))) return;
                particles_.spawn(Fx::Snow, {ground.x - lean * fall * 0.4f, ground.y - fall},
                                 {lean * slow * 0.4f, slow}, fall / slow, rng.range(0.0f, 6.0f));
            });
        } else {
            spawnMany(rate * dt, [&] {
                const Vec2 ground{rng.range(view_.x0 - fall * slant, view_.x1 + fall * slant),
                                  rng.range(view_.y0, view_.y1)};
                if (!rng.chance(rainHere(ground))) return;
                particles_.spawn(Fx::Raindrop, {ground.x + fall * slant, ground.y - fall},
                                 {-speed * slant, speed}, fall / speed);
            });
        }
    }
    // Leaves fall by the season's measure (more in a gust); blossom sheds petals in spring.
    const float leaves = season != nullptr ? season->leaves : 1.0f;
    const float petals = season != nullptr ? season->petals : 0.0f;
    for (const std::uint32_t i : trees_) {
        if (i >= placed_.size()) continue;
        const bool blossom = cat_.items[placed_[i].item.type].sheds == Shed::Blossom;
        const bool petal = blossom && petals > 0.0f;
        const TilePos tp = placed_[i].item.pos;
        const float gust =
            weather.gustAt({static_cast<float>(tp.x) + 0.5f, static_cast<float>(tp.y) + 0.5f});
        const float rate = (petal ? tuning::kPetalsPerSecondPerTree * petals
                                  : tuning::kLeavesPerSecondPerTree * leaves) *
                           (1.0f + tuning::kGustLeaves * gust) * thin_;
        if (!rng.chance(rate * dt)) continue;
        const FRect& r = placed_[i].screen;
        particles_.spawn(
            petal ? Fx::Petal : Fx::Leaf,
            {(r.x0 + r.x1) * 0.5f + rng.range(-0.5f, 0.5f) * u, r.y0 + (r.y1 - r.y0) * 0.35f},
            {(rng.range(-0.25f, 0.25f) + lean * tuning::kLeafLean) * u, tuning::kLeafFall * u},
            2.6f, rng.range(0.0f, 6.0f));
    }
    // Mist rises at the foot of every waterfall.
    for (const Fall& f : falls_)
        if (rng.chance(dt * tuning::kMistPerSecond))
            particles_.spawn(Fx::Mist,
                             {f.foot.x + rng.range(-0.15f, 0.15f) * iso_.tileW(), f.foot.y},
                             {lean * 0.2f * u, -0.15f * u}, tuning::kMistSeconds);
    // Swimmers leave a wake; sleepers breathe out z's.
    sleepTick_ += dt;
    const bool zzz = sleepTick_ >= tuning::kZzzInterval;
    if (zzz) sleepTick_ = 0;
    for (const Actor& a : actors) {
        if ((a.flags & actor_flag::kAlive) == 0 || a.alpha <= 0.0f) continue;
        const ActorKind& k = cat_.kinds[a.kind];
        if (k.move == Locomotion::Swim && a.state == ActorState::Travel &&
            rng.chance(dt / tuning::kWakeInterval))
            particles_.spawn(Fx::Ripple, iso_.toWorld(a.pos.x, a.pos.y), {0, 0},
                             tuning::kRippleSeconds);
        if (zzz && !reduceMotion_ && k.sleepAnim != 0xFF && a.anim == k.sleepAnim &&
            a.state == ActorState::Act && a.overlay <= 0) {
            const Vec2 h = headOf(a);
            particles_.spawn(Fx::Zzz, {h.x + 2, h.y + 2}, {0.1f * u, -0.3f * u}, 1.5f);
        }
    }
    particles_.update(dt, world);
}

void Scene::heart(const Actor& a) {
    const Vec2 h = headOf(a);
    particles_.spawn(Fx::Heart, {h.x, h.y - 1}, {0, -0.35f * iso_.tileH()}, tuning::kHeartSeconds);
}

void Scene::rustle(Vec2 tile, Rng& rng) {
    // Trees within a tile shake for a moment and drop two leaves (petals in spring, nothing in
    // winter).
    const SeasonDef* season =
        season_ >= 0 ? &cat_.seasons[static_cast<std::size_t>(season_)] : nullptr;
    const float u = iso_.tileH();
    for (const std::uint32_t i : trees_) {
        if (i >= placed_.size()) continue;
        const Placed& pl = placed_[i];
        const TilePos t = pl.item.pos;
        if (std::abs(static_cast<float>(t.x) + 0.5f - tile.x) > 1.6f ||
            std::abs(static_cast<float>(t.y) + 0.5f - tile.y) > 1.6f)
            continue;
        rustles_.push_back({t, now_ + tuning::kRustleSeconds});
        const bool blossom = cat_.items[pl.item.type].sheds == Shed::Blossom;
        const bool petal = blossom && season != nullptr && season->petals > 0;
        if (season != nullptr && season->leaves <= 0 && !petal) continue;
        for (int n = 0; n < 2; ++n)
            particles_.spawn(petal ? Fx::Petal : Fx::Leaf,
                             {(pl.screen.x0 + pl.screen.x1) * 0.5f + rng.range(-0.5f, 0.5f) * u,
                              pl.screen.y0 + (pl.screen.y1 - pl.screen.y0) * 0.35f},
                             {rng.range(-0.25f, 0.25f) * u, tuning::kLeafFall * u}, 2.6f,
                             rng.range(0.0f, 6.0f));
    }
}

void Scene::fishJump(Vec2 tile) {
    const Vec2 w = iso_.toWorld(tile.x, tile.y);
    particles_.spawn(Fx::FishJump, w, {0, 0}, tuning::kFishJumpSeconds);
    particles_.spawn(Fx::Ripple, w, {0, 0}, tuning::kRippleSeconds);
}

void Scene::shootingStar(Rng& rng) {
    if (reduceMotion_) return; // no streaks with reduce motion (its sound still plays)
    star_.start = now_;
    star_.from = {rng.range(0.15f, 0.75f), rng.range(0.05f, 0.3f)};
    const float ang = rng.range(0.15f, 0.4f);
    star_.dir = {std::cos(ang), std::sin(ang)};
}

void Scene::ensureTargets(int w, int h, bool own) {
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
    if (own) make(world_);
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
                     float scaleY, int part) {
    const auto& def = cat_.items[item.type];
    const auto f = [](int v) { return static_cast<float>(v); };
    const Vec2 anchor = iso_.toWorld(item.pos);
    const Vec2 pivot =
        iso_.toWorld(f(item.pos.x) + f(item.w) * 0.5f, f(item.pos.y) + f(item.h) * 0.5f);
    Vec2 scale{1.0f, scaleY};
    const float t = popOf(item.pos);
    if (t < 0.0f) return; // revealed by a wave that has not reached it yet
    if (t >= 0.0f && t < 1.0f) {
        const float y = 0.35f + 0.65f * easeOutBack(t);
        scale = {1.0f + (1.0f - y) * 0.45f, y};
        alpha *= std::min(1.0f, t * 4.0f);
    }
    const std::uint32_t phase = tileHash(item.pos.x, item.pos.y) % 7;
    // Plants sway with the wind, faster as a gust passes and when something rustles them;
    // lights and machines keep their own pace.
    float clock = now_;
    float fps = def.fps;
    if (fps > 0 && !def.glow) {
        const Vec2 c{static_cast<float>(item.pos.x) + 0.5f, static_cast<float>(item.pos.y) + 0.5f};
        // Reduce motion keeps the gust's sound but not its wave through the plants.
        const float gust = weather_ != nullptr && !reduceMotion_ ? weather_->gustAt(c) : 0.0f;
        clock = sway_ * (1.0f + tuning::kGustSway * gust);
        if (std::ranges::any_of(rustles_, [&](const Rustle& r) { return r.tile == item.pos; })) {
            clock = now_;
            fps = tuning::kRustleFps;
        }
    }
    const SpriteId base = baseFrames(item, slot).at(clock, fps, phase);
    const SDL_FColor c = silhouette ? SDL_FColor{0, 0, 0, alpha}
                                    : exposed(base, {tint.r, tint.g, tint.b, tint.a * alpha});
    if (part < 0 || scale.x != 1.0f || scale.y != 1.0f) {
        // Whole (a half drawn whole while it pops in is drawn once: by the far half).
        if (part <= 0) sprite(base, anchor, c, false, pivot, scale);
        return;
    }
    // One half of a footbridge: cut along its span; the near half lies below the line.
    const CutLine cut = crossingCut(def, item, iso_);
    putSpriteCut(batch_, atlas_.sprite(base), anchor, xf_, c, blend_, cut.a, cut.b, part == 1);
}

OrderItem Scene::itemBox(const Placed& p, std::uint32_t id) const {
    const ItemDef& def = cat_.items[p.item.type];
    const Vec2 a = iso_.toWorld(p.item.pos);
    const float top = std::max(1.0f, a.y - p.screen.y0); // height over the top vertex
    const std::uint64_t key = depthId(DepthKind::Item, id, static_cast<std::uint32_t>(p.part + 1));
    if (!def.walkable) return {makeBox(tileRect(p.item), 0, top, key, iso_.hh), p.screen, 0};
    // What one walks on is a deck under whoever stands on it, a railed one in two halves.
    return {crossingBox(def, p.item, p.part, top, key, iso_.hh), p.screen, 0};
}

bool Scene::onDecks(const Actor& a) const {
    const ActorKind& k = cat_.kinds[a.kind];
    return k.move != Locomotion::Swim && !inAir(a, k);
}

float Scene::deckAt(Vec2 pos) const {
    return map_ != nullptr ? lc::deckAt(*map_, cat_, pos) : 0.0f;
}

void Scene::buildDynamic(const FrameParams& p) {
    dynamic_.clear();
    dynamicBoxes_.clear();
    actorRank_.assign(p.actors.size(), -1.0f);
    const auto add = [&](EntryKind kind, std::uint32_t index, const DepthBox& box, const FRect& sr,
                         bool glowing) {
        if (!sr.overlaps(view_)) return;
        dynamic_.push_back({kind, index, glowing || nearGlow(sr)});
        dynamicBoxes_.push_back({box, sr, 0});
    };
    int resident = -1; // her entry, for what rides on her hat
    for (std::uint32_t i = 0; i < p.actors.size(); ++i) {
        const Actor& a = p.actors[i];
        if ((a.flags & actor_flag::kAlive) == 0 || a.alpha <= 0.0f ||
            (a.flags & actor_flag::kOnHat) != 0)
            continue;
        const int v = cat_.kinds[a.kind].visitor;
        if (v >= 0 && cat_.visitors[static_cast<std::size_t>(v)].underwater) continue;
        // Its box: a point round the feet (or the ground under a flyer), from its height (a seat,
        // a perch, flight) to the top of its frame. Emissive visitors are always drawn in the
        // glow pass.
        const FRect r = actorRect(a);
        const float z = a.lift + (onDecks(a) ? deckAt(a.pos) : 0.0f);
        const DepthBox box =
            makeBox(pointRect(a.pos), z, z + (r.y1 - r.y0), depthId(DepthKind::Actor, i), iso_.hh);
        if (std::cmp_equal(i, resident_)) resident = static_cast<int>(dynamic_.size());
        add(EntryKind::Actor, i, box, r, glows(a));
    }
    // Riders on her hat go right after her: her box, a hair nearer.
    for (std::uint32_t i = 0; i < p.actors.size(); ++i) {
        const Actor& a = p.actors[i];
        if ((a.flags & actor_flag::kAlive) == 0 || a.alpha <= 0.0f ||
            (a.flags & actor_flag::kOnHat) == 0 || resident < 0)
            continue;
        DepthBox box = dynamicBoxes_[static_cast<std::size_t>(resident)].box;
        box.id = depthId(DepthKind::Actor, i, 1);
        box.near += 1e-3f;
        add(EntryKind::Actor, i, box, actorRect(a), glows(a));
    }
    for (std::uint32_t i = 0; i < p.ghosts.size(); ++i) {
        const Ghost& g = p.ghosts[i];
        if (g.mode != Ghost::Mode::Item) continue;
        const int slot = slotFor(*p.world, g.item);
        const Placed pl{g.item, slot, spriteRect(g.item, slot), false, false, -1};
        add(EntryKind::Ghost, i, itemBox(pl, i).box, pl.screen, false);
        dynamicBoxes_.back().box.id = depthId(DepthKind::Ghost, i);
    }
    for (std::uint32_t i = 0; i < fades_.size(); ++i) {
        const Placed pl{fades_[i].item, fades_[i].slot, spriteRect(fades_[i].item, fades_[i].slot),
                        false,          false,          -1};
        if (!pl.screen.overlaps(view_)) continue;
        add(EntryKind::Fade, i, itemBox(pl, i).box, pl.screen, false);
        dynamicBoxes_.back().box.id = depthId(DepthKind::Fade, i);
    }
    merge_.plan(boxes_, dynamicBoxes_, view_);
    float rank = 0;
    for (const ActorMerge::Step& st : merge_.sequence())
        if (st.actor && dynamic_[st.index].kind == EntryKind::Actor)
            actorRank_[dynamic_[st.index].index] = rank++;
}

void Scene::drawActor(const Actor& a, bool silhouette) {
    if ((a.flags & actor_flag::kAlive) == 0 || a.alpha <= 0.0f) return;
    const ActorKind& k = cat_.kinds[a.kind];
    const bool glow = glows(a);
    // Emissive visitors skip the graded pass and appear, ungraded, in the glow layer.
    if (glow && !silhouette) return;
    const KindAnim& ka = tables_.kinds[a.kind][animOf(a)];
    const bool backward = a.facing == Facing::Back || a.facing == Facing::BackMirrored;
    const bool back = backward && !ka.back.empty();
    // Mirrored frames cover +y and -x (plain animations, drawn facing front, too).
    const bool mirror = a.facing == Facing::FrontMirrored || a.facing == Facing::BackMirrored;
    // Moving animations step with the ground covered (their fps is at the kind's speed), so a
    // frame changes every so many pixels at any pace; the rest by the clock.
    const bool moving = animOf(a) != a.anim || a.state == ActorState::Travel;
    const float speed = std::max(0.05f, k.speed);
    const SpriteId id =
        (back ? ka.back : ka.front).at(moving ? a.stride / speed : a.animTime, ka.fps);
    const Vec2 w = actorAnchor(a);
    const float al = std::clamp(a.alpha, 0.0f, 1.0f);
    SDL_FColor color = silhouette && !glow ? SDL_FColor{0, 0, 0, al}
                       : glow              ? SDL_FColor{1, 1, 1, al}
                                           : exposed(id, {1, 1, 1, al});
    // Under the water: faded and cooled.
    if (k.visitor >= 0 && cat_.visitors[static_cast<std::size_t>(k.visitor)].underwater &&
        !silhouette)
        color = {color.r * tuning::kUnderwaterTint[0], color.g * tuning::kUnderwaterTint[1],
                 color.b * tuning::kUnderwaterTint[2], color.a * tuning::kUnderwaterAlpha};
    sprite(id, w, color, mirror);
}

void Scene::drawEntry(const FrameParams& p, const Entry& e, bool silhouette) {
    if (silhouette && !e.occludesGlow) return;
    switch (e.kind) {
    case EntryKind::Actor: drawActor(p.actors[e.index], silhouette); break;
    case EntryKind::Ghost: {
        const Ghost& g = p.ghosts[e.index];
        const int slot = slotFor(*p.world, g.item);
        drawItem(g.item, slot, tuning::kGhostAlpha, g.valid ? kWhite : kInvalidTint, silhouette);
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
    // Items a remove tool points at are tinted (one, or every one an area touches).
    const auto marked = [&](const Item& it) {
        return std::ranges::any_of(p.ghosts, [&](const Ghost& g) {
            if (g.mode != Ghost::Mode::Remove) return false;
            const Item* t = world.itemAt(g.tile);
            return t != nullptr && *t == it;
        });
    };
    if (!silhouette) drawnItems_ = 0;
    batch_.setBand(bandTag(silhouette ? Band::Glow : Band::Depth));
    // One order for everything standing in the home (draw-order.md §1.4): items, actors and
    // flyers, ghosts and fades.
    for (const ActorMerge::Step& st : merge_.sequence()) {
        if (st.actor) {
            drawEntry(p, dynamic_[st.index], silhouette);
            continue;
        }
        const Placed& pl = placed_[st.index];
        // The glow pass only needs what can hide an emissive pixel.
        if (silhouette && !pl.occludesGlow) continue;
        if (!silhouette) ++drawnItems_;
        const bool tinted = !silhouette && !p.ghosts.empty() && marked(pl.item);
        drawItem(pl.item, pl.slot, 1.0f, tinted ? kInvalidTint : kWhite, silhouette, 1.0f, pl.part);
        const auto& glowSet = tables_.items[pl.item.type].glow[static_cast<std::size_t>(pl.slot)];
        if (silhouette && !glowSet.empty()) {
            const auto& def = cat_.items[pl.item.type];
            sprite(glowSet.at(now_, def.fps, tileHash(pl.item.pos.x, pl.item.pos.y) % 7),
                   iso_.toWorld(pl.item.pos), {glow, glow, glow, 1.0f});
        }
    }
}

bool Scene::nearGlow(const FRect& r) const {
    return std::ranges::any_of(glowRects_, [&](const FRect& g) { return g.overlaps(r); });
}

void Scene::drawShadows(const FrameParams& p) {
    batch_.setBand(bandTag(Band::Shadows));
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
        if (t < 0.0f) continue;
        sprite(set.frames.front(), iso_.toWorld(pl.item.pos), {1, 1, 1, t < 1.0f ? t : 1.0f});
    }
    for (const Actor& a : p.actors) {
        if ((a.flags & actor_flag::kAlive) == 0 || a.alpha <= 0.0f ||
            (a.flags & actor_flag::kOnHat) != 0)
            continue;
        const ActorKind& kd = cat_.kinds[a.kind];
        const int v = kd.visitor;
        if (v >= 0 && cat_.visitors[static_cast<std::size_t>(v)].underwater) continue;
        // Something sitting on an item is in that item's shadow already.
        if (kd.move != Locomotion::Fly && a.lift > 0.5f) continue;
        Vec2 w = iso_.toWorld(a.pos.x, a.pos.y);
        w = snapped(w);
        const bool air = kd.move == Locomotion::Fly;
        const bool swim = kd.move == Locomotion::Swim;
        const float k = air ? 0.5f : (swim ? 0.85f : 0.7f);
        const float al = air ? 0.45f : swim ? tuning::kWaterShadowAlpha : 1.0f;
        sprite(atlas_.softShadow(), w, {1, 1, 1, std::clamp(a.alpha, 0.0f, 1.0f) * al}, false, w,
               {k, k});
    }
    // Clouds slide their soft shadows over the ground; showers are darker.
    if (p.weather != nullptr && p.cloudShadows) {
        // A round blob that fades all the way to nothing, darkened: no edge shows however large.
        const Sprite& blob = atlas_.sprite(atlas_.lightBlob());
        for (const WeatherCell& c : p.weather->cells()) {
            if (c.age < 0) continue;
            const Vec2 w = iso_.toWorld(c.centre.x, c.centre.y);
            const float sx = c.radius * iso_.tileW() * tuning::kCloudShadowSize / blob.w;
            const float al = c.intensity() * (c.rain ? tuning::kRainShadow : tuning::kCloudShadow);
            sprite(atlas_.lightBlob(), w, {0, 0, 0, al}, false, w, {sx, sx * 0.5f});
        }
    }
    batch_.flush();
    if (!SDL_SetRenderTarget(renderer_, into_)) SDL_Log("render: %s", SDL_GetError());
    fullQuad(shadow_.texture.get(), SDL_BLENDMODE_BLEND, {1, 1, 1, tables_.shadowOpacity});
}

void Scene::drawMarkers(const FrameParams& p) {
    batch_.setBand(bandTag(Band::GroundDecals));
    // Placement markers and nook areas sit on the ground under everything else.
    const World& world = *p.world;
    // Wet ground darkens, block by block, softly blending into its neighbours.
    if (p.weather != nullptr) {
        const auto b = static_cast<float>(tuning::kWetBlock);
        for (int by = 0; by < p.weather->wetBlocksY(); ++by)
            for (int bx = 0; bx < p.weather->wetBlocksX(); ++bx) {
                const float wet = p.weather->wetBlock(bx, by);
                if (wet < 0.02f) continue;
                const Vec2 at =
                    iso_.toWorld(static_cast<float>(bx) * b, static_cast<float>(by) * b);
                sprite(tables_.tileArea, at, {0, 0, 0.05f, wet * tuning::kWetDarken}, false, at,
                       {b, b});
            }
    }
    for (const Pulse& pl : pulses_) {
        const float k = (now_ - pl.start) / tuning::kNookPulseSeconds;
        drawArea(world, pl.area,
                 {1.0f, 0.86f, 0.55f, tuning::kNookPulseAlpha * std::sin(k * 3.14159f)});
    }
    // The grid lies over open land, under everything standing on it.
    if (p.grid > 0) {
        const TileRect v = visibleTiles(*p.camera, p.screen, world);
        for (int y = v.y0; y < v.y1; ++y)
            for (int x = v.x0; x < v.x1; ++x)
                if (world.hasGround({x, y}) && !world.isWild({x, y}))
                    sprite(tables_.tileGrid, iso_.toWorld(TilePos{x, y}), {1, 1, 1, p.grid});
    }
    if (p.footprints)
        for (const Placed& pl : placed_)
            for (int y = pl.item.pos.y; y < pl.item.pos.y + pl.item.h; ++y)
                for (int x = pl.item.pos.x; x < pl.item.pos.x + pl.item.w; ++x)
                    sprite(tables_.tileArea, iso_.toWorld(TilePos{x, y}),
                           {1, 1, 1, tuning::kFootprintAlpha});
    for (const NearInstance& o : p.outlines)
        drawArea(world, o, {1, 1, 1, tuning::kNookOutlineAlpha});
    // Land being opened still looks wild until the wave reaches each tile.
    for (const WaveTile& w : wave_) {
        const float a = std::clamp(1.0f - (now_ - w.start) / tuning::kLandClearFade, 0.0f, 1.0f);
        if (a <= 0.0f) continue;
        const Vec2 at = iso_.toWorld(w.tile);
        sprite(tables_.tileArea, at, {0, 0, 0, (1.0f - tuning::kWildDim) * a});
        if (w.thicket) sprite(*w.thicket, at, {1, 1, 1, a});
    }
    const auto marker = [&](TilePos t, bool ok) {
        if (world.hasGround(t))
            sprite(ok ? tables_.tileOk : tables_.tileBad, iso_.toWorld(t), {1, 1, 1, 0.9f});
    };
    for (const Ghost& g : p.ghosts) {
        switch (g.mode) {
        case Ghost::Mode::None: break;
        case Ghost::Mode::Item:
            for (int y = 0; y < g.item.h; ++y)
                for (int x = 0; x < g.item.w; ++x)
                    marker({g.item.pos.x + x, g.item.pos.y + y}, g.valid);
            break;
        case Ghost::Mode::Tile: marker(g.tile, g.valid); break;
        case Ghost::Mode::Remove:
            if (const Item* it = world.itemAt(g.tile)) {
                for (int y = 0; y < it->h; ++y)
                    for (int x = 0; x < it->w; ++x) marker({it->pos.x + x, it->pos.y + y}, false);
            }
            break;
        }
    }
}

void Scene::drawParticles(bool ground) {
    // Petals and ripples lie on the water; the rest are effects among what stands.
    batch_.setBand(bandTag(ground ? Band::WaterSurface : Band::Depth));
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
        case Fx::Petal:
        case Fx::Snow:
            // Floating on water, a petal rests on one frame.
            id = pt.landed ? set.frames.front() : set.at(pt.age, 5.0f);
            alpha = std::min(1.0f, (1.0f - k) * 3.0f);
            break;
        case Fx::Mist: alpha = 0.7f * std::sin(k * 3.14159f); break;
        case Fx::Produce:
            // A crop, not an animation: the frame was chosen when it was spawned (as sway).
            id = set.frames[static_cast<std::size_t>(pt.sway) % set.frames.size()];
            alpha = std::min(1.0f, (1.0f - k) * 2.5f);
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
        sprite(id, snapped(pt.pos), {1, 1, 1, alpha});
    }
}

void Scene::drawLighting(const FrameParams& p, Rgb amb) {
    batch_.setBand(bandTag(Band::Grading));
    const float glow = p.light.glow;
    const bool emissive = std::ranges::any_of(
        p.actors, [&](const Actor& a) { return (a.flags & actor_flag::kAlive) != 0 && glows(a); });
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
        for (const Actor& a : p.actors) {
            if ((a.flags & actor_flag::kAlive) == 0 || !glows(a)) continue;
            const Vec2 w = actorAnchor(a);
            const float t = fireflySync_ ? now_ * 1.6f : a.animTime;
            const float pulse = 0.6f + 0.4f * std::sin(t * 4.0f);
            sprite(atlas_.lightBlob(), w, scaled(kFireflyHalo, 0.5f * glow * pulse * a.alpha),
                   false, w, {0.35f, 0.3f});
        }
        batch_.flush();
    }
    if (!SDL_SetRenderTarget(renderer_, into_)) SDL_Log("render: %s", SDL_GetError());
    fullQuad(light_.texture.get(), SDL_BLENDMODE_MUL, kWhite);
    batch_.flush();
}

void Scene::drawGlow(const FrameParams& p) {
    batch_.setBand(bandTag(Band::Glow));
    const float glow = p.light.glow;
    const bool emissiveVisitors = std::ranges::any_of(
        p.actors, [&](const Actor& a) { return (a.flags & actor_flag::kAlive) != 0 && glows(a); });
    if (glow <= 0.01f && !emissiveVisitors) return;
    if (!SDL_SetRenderTarget(renderer_, glow_.texture.get()) ||
        !SDL_SetRenderDrawColorFloat(renderer_, 0, 0, 0, 0) || !SDL_RenderClear(renderer_)) {
        SDL_Log("render: glow: %s", SDL_GetError());
    }
    blend_ = SDL_BLENDMODE_BLEND;
    drawEntries(p, true);
    blend_ = SDL_BLENDMODE_ADD;
    for (const Actor& a : p.actors) {
        if ((a.flags & actor_flag::kAlive) == 0 || !glows(a)) continue;
        const Vec2 w = actorAnchor(a);
        // In unison (an event) or each to its own rhythm.
        const float t = fireflySync_ ? now_ * 1.6f : a.animTime;
        const float pulse =
            fireflySync_ ? std::max(0.0f, std::sin(t * 4.0f)) : 0.55f + 0.45f * std::sin(t * 4.0f);
        sprite(atlas_.lightBlob(), w, scaled(kFireflyCore, 0.8f * pulse * a.alpha), false, w,
               {0.12f, 0.12f});
    }
    batch_.flush();
    if (!SDL_SetRenderTarget(renderer_, into_)) SDL_Log("render: %s", SDL_GetError());
    fullQuad(glow_.texture.get(), SDL_BLENDMODE_ADD, kWhite);
    batch_.flush();
}

void Scene::setFloating(bool on) {
    floating_ = on;
    ground_->setRims(on);
    regionRevision_ = ~0ULL; // waterfalls are gathered with the region
}

void Scene::beginFrame(const FrameParams& p) {
    const World& world = *p.world;
    view_ = {xf_.origin.x, xf_.origin.y, xf_.origin.x + static_cast<float>(targetW_) / xf_.res,
             xf_.origin.y + static_cast<float>(targetH_) / xf_.res};
    const float s = p.camera->scale();
    const Vec2 cam = p.camera->position();
    topLeft_ = {cam.x - p.screen.x * 0.5f / s, cam.y - p.screen.y * 0.5f / s};
    night_ = std::clamp(p.light.night, 0.0f, 1.0f);
    actors_ = p.actors;
    resident_ = p.resident;
    map_ = p.world;
    fireflySync_ = p.fireflySync;
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
}

void Scene::draw(const FrameParams& p, SDL_Texture* out) {
    batch_.resetStats();
    const float s = p.camera->scale();
    // Target pixels per world pixel: native, except below 1x where the target matches the window.
    const float res = std::min(1.0f, s);
    const Vec2 cam = p.camera->position();
    const Vec2 topLeft{cam.x - p.screen.x * 0.5f / s, cam.y - p.screen.y * 0.5f / s};
    // The origin sits on the target's pixel grid so cached ground lands on whole pixels.
    const float px = 1.0f / res;
    const Vec2 origin{std::floor(topLeft.x / px) * px - px, std::floor(topLeft.y / px) * px - px};
    ensureTargets(static_cast<int>(std::ceil(p.screen.x / s * res)) + 3,
                  static_cast<int>(std::ceil(p.screen.y / s * res)) + 3, true);
    if (!world_.texture || !light_.texture || !glow_.texture || !shadow_.texture) return;
    xf_ = {origin, res, res < 1.0f ? SDL_SCALEMODE_LINEAR : SDL_SCALEMODE_NEAREST};
    into_ = world_.texture.get();
    beginFrame(p);

    if (!SDL_SetRenderTarget(renderer_, into_) ||
        !SDL_SetRenderDrawColorFloat(renderer_, 0, 0, 0, 0) || !SDL_RenderClear(renderer_)) {
        SDL_Log("render: world target: %s", SDL_GetError());
    }
    embedGround(p);
    embedObjects(p);
    drawLighting(p, p.light.ambient);
    drawMoths(p);
    drawGlow(p);

    if (!SDL_SetRenderTarget(renderer_, out)) SDL_Log("render: %s", SDL_GetError());
    composite(p, {1, 1}, false);
}

void Scene::embedBegin(const FrameParams& p, const Embed& e) {
    batch_.resetStats();
    ensureTargets(e.w, e.h, false);
    into_ = e.target;
    xf_ = {{e.xf.origin.x - e.offset.x, e.xf.origin.y - e.offset.y}, e.xf.res, e.xf.filter};
    beginFrame(p);
}

void Scene::embedGround(const FrameParams& p) {
    if (into_ == nullptr || !light_.texture || !glow_.texture || !shadow_.texture) return;
    batch_.setBand(bandTag(Band::Ground));
    ground_->draw(batch_, *p.world, view_, xf_, into_, now_);
    buildDynamic(p);
    drawShadows(p);
    blend_ = SDL_BLENDMODE_BLEND;
    drawMarkers(p);
    drawParticles(true);
    // Swimmers under the water go below everything that floats on it.
    batch_.setBand(bandTag(Band::WaterSurface));
    for (const Actor& a : p.actors) {
        const int v = cat_.kinds[a.kind].visitor;
        if (v >= 0 && cat_.visitors[static_cast<std::size_t>(v)].underwater) drawActor(a, false);
    }
    batch_.flush();
}

void Scene::embedObjects(const FrameParams& p) {
    if (into_ == nullptr || !shadow_.texture) return;
    blend_ = cover_;
    drawEntries(p, false);
    blend_ = SDL_BLENDMODE_BLEND;
    drawParticles(false);
    batch_.flush();
}

void Scene::embedLight(const FrameParams& p, Rgb ambient) {
    if (into_ == nullptr || !light_.texture) return;
    drawLighting(p, ambient);
    drawMoths(p);
}

void Scene::embedGlow(const FrameParams& p, SDL_Texture* into) {
    if (into != nullptr) into_ = into;
    if (into_ == nullptr || !glow_.texture) return;
    drawGlow(p);
}

void Scene::embedSky(const FrameParams& p) {
    drawSky(p, {1, 1});
    batch_.flush();
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
    batch_.setBand(bandTag(Band::Sky));
    batch_.use(nullptr, SDL_BLENDMODE_NONE);
    batch_.triangles(sky, 4, kQuad, 6);
    drawSky(p, scale);
    // The world's picture, everything from the ground to the glow, over the sky.
    batch_.setBand(bandTag(Band::Ground));
    // Whole-number magnification stays nearest-neighbour; anything else (mid-transition, or a
    // blurred copy) is filtered.
    const float ox = (xf_.origin.x - topLeft_.x) * s;
    const float oy = (xf_.origin.y - topLeft_.y) * s;
    const bool whole = std::abs(k - std::round(k)) < 1e-3f &&
                       std::abs(ox - std::round(ox)) < 1e-2f &&
                       std::abs(oy - std::round(oy)) < 1e-2f;
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

void Scene::drawMoths(const FrameParams& p) {
    batch_.setBand(bandTag(Band::Glow));
    if (reduceMotion_) return;
    // Two moths circle each lamp head at night, lit by it (drawn after the night grade).
    if (p.light.night < 0.3f || moths_.empty()) return;
    const FrameSet& set = tables_.fx[static_cast<std::size_t>(Fx::Moth)];
    const float r = tuning::kMothRadius * iso_.tileW();
    const float a = std::clamp((p.light.night - 0.3f) * 2.0f, 0.0f, 1.0f);
    blend_ = SDL_BLENDMODE_BLEND;
    for (const Vec2& head : moths_) {
        const float phase =
            static_cast<float>(tileHash(static_cast<int>(head.x), static_cast<int>(head.y)) % 628) *
            0.01f;
        for (int k = 0; k < 2; ++k) {
            const float ang = now_ * (2.2f + 0.4f * static_cast<float>(k)) + phase +
                              3.14159f * static_cast<float>(k);
            const Vec2 at{std::round(head.x + std::cos(ang) * r),
                          std::round(head.y + std::sin(ang) * r * 0.6f)};
            sprite(set.at(now_ + static_cast<float>(k) * 0.1f, 12.0f), at,
                   {tuning::kMothLit, tuning::kMothLit, tuning::kMothLit, a});
        }
    }
    batch_.flush();
}

void Scene::drawSky(const FrameParams& p, Vec2 scale) {
    batch_.setBand(bandTag(Band::SkyEffects));
    // Things in the sky behind the island, in window space: the rainbow and shooting stars.
    const float s = p.camera->scale();
    const Xform win{topLeft_, s * scale.x, SDL_SCALEMODE_NEAREST};
    if (p.rainbow > 0.0f && tables_.rainbow && p.world != nullptr) {
        const TileRect lb = p.world->landBounds();
        const Vec2 c = iso_.toWorld(static_cast<float>(lb.x0 + lb.x1) * 0.5f,
                                    static_cast<float>(lb.y0 + lb.y1) * 0.5f);
        const Vec2 top = iso_.toWorld(static_cast<float>(lb.x0), static_cast<float>(lb.y0));
        // Its feet rest behind the island's middle; integer-scaled with the island.
        const Vec2 at{c.x, top.y + (c.y - top.y) * tuning::kRainbowDrop};
        const float k = tuning::kRainbowScale;
        putSprite(batch_, atlas_.sprite(*tables_.rainbow), at, win, {1, 1, 1, p.rainbow},
                  SDL_BLENDMODE_BLEND, false, at, {k, k});
    }
    if (star_.start >= 0) {
        const float t = (now_ - star_.start) / tuning::kStarSeconds;
        if (t >= 1.0f || p.light.night < 0.5f) {
            star_.start = -1;
        } else {
            // A streak along a shallow diagonal, bright head first, fading as it goes.
            const float w = p.screen.x * scale.x;
            const float h = p.screen.y * scale.y;
            const float travel = w * tuning::kStarTravel * t;
            const Vec2 px{star_.from.x * w + star_.dir.x * travel,
                          star_.from.y * h + star_.dir.y * travel};
            const Xform screen{{0, 0}, 1.0f, SDL_SCALEMODE_NEAREST};
            const float k = std::max(1.0f, std::round(s * scale.x));
            const float a = std::sin(t * 3.14159f) * p.light.night;
            putSprite(
                batch_,
                atlas_.sprite(tables_.fx[static_cast<std::size_t>(Fx::StarStreak)].frames.front()),
                px, screen, {1, 1, 1, a}, SDL_BLENDMODE_ADD, false, px, {k, k});
        }
    }
}

SceneStats Scene::stats() const {
    SceneStats st;
    st.regionItems = placed_.size();
    st.drawnItems = drawnItems_;
    for (const Target* t : {&world_, &light_, &glow_, &shadow_})
        st.targetBytes += static_cast<std::size_t>(t->w) * static_cast<std::size_t>(t->h) * 4;
    st.groundBytes = ground_->bytes();
    st.groundSlotsRendered = ground_->slotsRendered();
    st.groundChunksCached = ground_->chunksCached();
    return st;
}

} // namespace lc
