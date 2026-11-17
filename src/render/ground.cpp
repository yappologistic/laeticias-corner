#include "render/ground.hpp"

#include "core/rng.hpp"
#include "core/tuning.hpp"

#include <algorithm>
#include <cmath>

namespace lc {
namespace {

constexpr int kPad = 2;            // spare pixels around a slot's content
constexpr int kPageSlotsMax = 4;   // slots per page side, at most
constexpr int kPageSideMax = 4096; // keep pages within every renderer's texture limit
constexpr SDL_FColor kWhite{1, 1, 1, 1};

std::uint64_t keyOf(int level, int cx, int cy) {
    return (static_cast<std::uint64_t>(level) << 62) | (static_cast<std::uint64_t>(cx) << 31) |
           static_cast<std::uint64_t>(cy);
}

} // namespace

std::optional<SpriteId> thicketAt(const SpriteTables& tables, TilePos p) {
    if (tables.thickets.empty()) return std::nullopt;
    const std::uint32_t h = tileHash(p.x, p.y, 7);
    if (static_cast<float>(h % 1000) >= tuning::kWildThicketChance * 1000.0f) return std::nullopt;
    return tables.thickets[(h / 1000) % tables.thickets.size()];
}

GroundCache::GroundCache(SDL_Renderer* renderer, const Atlas& atlas, const Catalog& cat,
                         const SpriteTables& tables, std::size_t budgetBytes)
    : renderer_(renderer), atlas_(atlas), cat_(cat), tables_(tables), iso_(cat.iso()),
      waterFps_(cat.terrain[static_cast<std::size_t>(cat.waterTerrain)].fps) {
    const Reach& r = tables_.groundReach;
    slotW_ = static_cast<int>(static_cast<float>(kBaseChunk) * iso_.tileW() +
                              std::ceil(r.left + r.right)) +
             2 * kPad;
    slotH_ = static_cast<int>(static_cast<float>(kBaseChunk) * iso_.tileH() +
                              std::ceil(r.top + r.bottom)) +
             2 * kPad;
    slotsX_ = std::clamp(kPageSideMax / slotW_, 1, kPageSlotsMax);
    slotsY_ = std::clamp(kPageSideMax / slotH_, 1, kPageSlotsMax);
    pageBytes_ =
        static_cast<std::size_t>(slotW_ * slotsX_) * static_cast<std::size_t>(slotH_ * slotsY_) * 4;
    maxPages_ = std::max<std::size_t>(1, budgetBytes / pageBytes_);
}

std::size_t GroundCache::bytes() const {
    const std::size_t scratch = scratch_ ? static_cast<std::size_t>(4 * slotW_ * slotH_) * 4 : 0;
    return pages_.size() * pageBytes_ + scratch;
}

FRect GroundCache::chunkBox(int level, int cx, int cy) const {
    const int c = chunkTiles(level);
    const auto f = [](int v) { return static_cast<float>(v); };
    const float x0 = f(cx * c);
    const float y0 = f(cy * c);
    const float x1 = f(cx * c + c);
    const float y1 = f(cy * c + c);
    const Reach& r = tables_.groundReach;
    const float pad = static_cast<float>(kPad << level);
    return {iso_.toWorld(x0, y1).x - r.left - pad, iso_.toWorld(x0, y0).y - r.top - pad,
            iso_.toWorld(x1, y0).x + r.right + pad, iso_.toWorld(x1, y1).y + r.bottom + pad};
}

std::uint32_t GroundCache::revisionOf(const World& world, int level, int cx, int cy) const {
    const int c = chunkTiles(level);
    std::uint32_t sum = 0;
    world.forEachChunkIn({cx * c, cy * c, cx * c + c, cy * c + c},
                         [&](int wx, int wy) { sum += world.chunkTerrainRevision(wx, wy); });
    return sum;
}

bool GroundCache::hasAnimated(const World& world, int level, int cx, int cy) const {
    const int c = chunkTiles(level);
    bool any = false;
    world.forEachChunkIn({cx * c, cy * c, cx * c + c, cy * c + c}, [&](int wx, int wy) {
        for (std::size_t t = 0; t < cat_.terrain.size(); ++t)
            if (cat_.terrain[t].fps > 0 && world.chunkTerrainCount(wx, wy, static_cast<int>(t)) > 0)
                any = true;
    });
    return any;
}

void GroundCache::drawTile(Batch& batch, const World& world, TilePos p, const Xform& x,
                           float now) const {
    if (!world.hasGround(p)) return;
    const Vec2 a = iso_.toWorld(p);
    // Cliff faces hang under rims that face open sky; tiles drawn later (further south) cover
    // them where the land continues.
    const bool water = world.isWater(p);
    if (!world.hasGround({p.x + 1, p.y})) {
        putSprite(batch, atlas_.sprite(tables_.cliffSE), a, x, kWhite, SDL_BLENDMODE_BLEND);
        // Water reaching the rim falls over it.
        if (water)
            putSprite(batch, atlas_.sprite(tables_.fallSE.at(now, waterFps_)), a, x, kWhite,
                      SDL_BLENDMODE_BLEND);
    }
    if (!world.hasGround({p.x, p.y + 1})) {
        putSprite(batch, atlas_.sprite(tables_.cliffSW), a, x, kWhite, SDL_BLENDMODE_BLEND);
        if (water)
            putSprite(batch, atlas_.sprite(tables_.fallSW.at(now, waterFps_)), a, x, kWhite,
                      SDL_BLENDMODE_BLEND);
    }
    const auto& base = tables_.terrainBase[static_cast<std::size_t>(cat_.baseTerrain)];
    if (world.isWild(p)) {
        // Wild land: the grass dimmed and cooled, brambles on four tiles in five.
        static constexpr SDL_FColor kWild{tuning::kWildDim * tuning::kWildCool[0],
                                          tuning::kWildDim * tuning::kWildCool[1],
                                          tuning::kWildDim * tuning::kWildCool[2], 1.0f};
        putSprite(batch, atlas_.sprite(base[tileHash(p.x, p.y, 1) % base.size()]), a, x, kWild,
                  SDL_BLENDMODE_BLEND);
        if (const auto t = thicketAt(tables_, p))
            putSprite(batch, atlas_.sprite(*t), a, x, kWhite, SDL_BLENDMODE_BLEND);
        return;
    }
    putSprite(batch, atlas_.sprite(base[tileHash(p.x, p.y, 1) % base.size()]), a, x, kWhite,
              SDL_BLENDMODE_BLEND);
    const int t = world.terrainAt(p);
    if (t == cat_.baseTerrain) return;
    const auto& def = cat_.terrain[static_cast<std::size_t>(t)];
    const FrameSet& set = tables_.terrainOverlay[static_cast<std::size_t>(t)]
                                                [static_cast<std::size_t>(world.terrainMask(p))];
    putSprite(batch, atlas_.sprite(set.at(now, def.fps)), a, x, kWhite, SDL_BLENDMODE_BLEND);
}

void GroundCache::drawChunk(Batch& batch, const World& world, int level, int cx, int cy,
                            const Xform& x, float now) const {
    const int c = chunkTiles(level);
    // At the overview a one-tile border of the neighbours is drawn too, so filtering never
    // leaves part-covered pixels along a chunk's edge.
    const int b = level > 0 ? 1 : 0;
    const TileRect r =
        TileRect{cx * c - b, cy * c - b, cx * c + c + b, cy * c + c + b}.clipped(world.bounds());
    for (int s = r.x0 + r.y0; s <= r.x1 + r.y1 - 2; ++s)
        for (int tx = std::max(r.x0, s - (r.y1 - 1)); tx <= std::min(r.x1 - 1, s - r.y0); ++tx)
            drawTile(batch, world, {tx, s - tx}, x, now);
}

int GroundCache::acquire() {
    const std::size_t perPage = static_cast<std::size_t>(slotsX_ * slotsY_);
    if (slots_.size() < maxPages_ * perPage) {
        const std::size_t i = slots_.size();
        const std::size_t page = i / perPage;
        if (page == pages_.size()) {
            TexturePtr t{SDL_CreateTexture(renderer_, kTextureFormat, SDL_TEXTUREACCESS_TARGET,
                                           slotW_ * slotsX_, slotH_ * slotsY_)};
            if (!t) {
                SDL_Log("ground: cannot create a cache page: %s", SDL_GetError());
                maxPages_ = pages_.size();
                return -1;
            }
            pages_.push_back(std::move(t));
        }
        const auto k = static_cast<int>(i % perPage);
        Slot s;
        s.page = static_cast<int>(page);
        s.x = (k % slotsX_) * slotW_;
        s.y = (k / slotsX_) * slotH_;
        slots_.push_back(s);
        return static_cast<int>(i);
    }
    int lru = -1;
    for (std::size_t i = 0; i < slots_.size(); ++i)
        if (slots_[i].used != frame_ &&
            (lru < 0 || slots_[i].used < slots_[static_cast<std::size_t>(lru)].used))
            lru = static_cast<int>(i);
    if (lru >= 0) {
        byKey_.erase(slots_[static_cast<std::size_t>(lru)].key);
        slots_[static_cast<std::size_t>(lru)].key = ~0ULL;
    }
    return lru;
}

void GroundCache::draw(Batch& batch, const World& world, const FRect& view, const Xform& target,
                       SDL_Texture* targetTexture, float now) {
    ++frame_;
    rendered_ = 0;
    const int level = target.res < 1.0f ? 1 : 0;
    const int c = chunkTiles(level);
    const float res = 1.0f / static_cast<float>(1 << level);
    std::uint64_t anim = 0;
    for (const auto& t : cat_.terrain)
        anim = anim * 31 + (t.fps > 0 ? static_cast<std::uint64_t>(now * t.fps) : 0);

    // Chunks whose box meets the view, found through the view's bounding box in tile space.
    const Reach& reach = tables_.groundReach;
    const FRect grown{view.x0 - reach.right, view.y0 - reach.bottom, view.x1 + reach.left,
                      view.y1 + reach.top};
    const Vec2 corners[4] = {iso_.toTile({grown.x0, grown.y0}), iso_.toTile({grown.x1, grown.y0}),
                             iso_.toTile({grown.x0, grown.y1}), iso_.toTile({grown.x1, grown.y1})};
    float tx0 = corners[0].x, tx1 = corners[0].x, ty0 = corners[0].y, ty1 = corners[0].y;
    for (const Vec2& v : corners) {
        tx0 = std::min(tx0, v.x);
        tx1 = std::max(tx1, v.x);
        ty0 = std::min(ty0, v.y);
        ty1 = std::max(ty1, v.y);
    }
    const TileRect tiles =
        TileRect{static_cast<int>(std::floor(tx0)), static_cast<int>(std::floor(ty0)),
                 static_cast<int>(std::floor(tx1)) + 1, static_cast<int>(std::floor(ty1)) + 1}
            .clipped(world.bounds());
    if (tiles.empty()) return;
    const int cx0 = tiles.x0 / c;
    const int cy0 = tiles.y0 / c;
    const int cx1 = (tiles.x1 - 1) / c;
    const int cy1 = (tiles.y1 - 1) / c;

    // Back to front along the diagonals, so cliff overhangs fall under the land in front.
    const auto each = [&](auto&& f) {
        for (int s = cx0 + cy0; s <= cx1 + cy1; ++s)
            for (int cx = std::max(cx0, s - cy1); cx <= std::min(cx1, s - cy0); ++cx) {
                const int cy = s - cx;
                if (chunkBox(level, cx, cy).overlaps(view)) f(cx, cy);
            }
    };

    // Pass 1: bring stale slots up to date (each costs a render-target switch).
    batch.flush();
    each([&](int cx, int cy) {
        const std::uint64_t key = keyOf(level, cx, cy);
        const auto it = byKey_.find(key);
        int si = it != byKey_.end() ? it->second : -1;
        const std::uint32_t rev = revisionOf(world, level, cx, cy);
        if (si >= 0) {
            Slot& s = slots_[static_cast<std::size_t>(si)];
            s.used = frame_;
            if (s.revision == rev && (!s.animated || s.anim == anim)) return;
        } else {
            si = acquire();
            if (si < 0) return; // drawn directly in pass 2
            byKey_[key] = si;
        }
        Slot& s = slots_[static_cast<std::size_t>(si)];
        s.key = key;
        s.revision = rev;
        s.anim = anim;
        s.animated = hasAnimated(world, level, cx, cy);
        s.used = frame_;
        ++rendered_;
        const FRect box = chunkBox(level, cx, cy);
        SDL_Texture* page = pages_[static_cast<std::size_t>(s.page)].get();
        const SDL_Rect rect{s.x, s.y, slotW_, slotH_};
        const SDL_FRect frect{static_cast<float>(s.x), static_cast<float>(s.y),
                              static_cast<float>(slotW_), static_cast<float>(slotH_)};
        if (level > 0) {
            if (!scratch_) {
                scratch_.reset(SDL_CreateTexture(renderer_, kTextureFormat,
                                                 SDL_TEXTUREACCESS_TARGET, 2 * slotW_, 2 * slotH_));
                if (!scratch_) SDL_Log("ground: cannot create scratch: %s", SDL_GetError());
            }
            if (scratch_) {
                if (!SDL_SetRenderTarget(renderer_, scratch_.get()) ||
                    !SDL_SetRenderDrawColorFloat(renderer_, 0, 0, 0, 0) ||
                    !SDL_RenderClear(renderer_))
                    SDL_Log("ground: %s", SDL_GetError());
                drawChunk(batch, world, level, cx, cy, {{box.x0, box.y0}, 1.0f}, now);
                batch.flush();
                if (!SDL_SetRenderTarget(renderer_, page)) SDL_Log("ground: %s", SDL_GetError());
                batch.use(scratch_.get(), SDL_BLENDMODE_NONE, SDL_SCALEMODE_LINEAR);
                batch.quad(frect, {0, 0, 1, 1}, kWhite);
                batch.flush();
                return;
            }
        }
        if (!SDL_SetRenderTarget(renderer_, page) || !SDL_SetRenderClipRect(renderer_, &rect) ||
            !SDL_SetRenderDrawBlendMode(renderer_, SDL_BLENDMODE_NONE) ||
            !SDL_SetRenderDrawColorFloat(renderer_, 0, 0, 0, 0) ||
            !SDL_RenderFillRect(renderer_, &frect)) {
            SDL_Log("ground: %s", SDL_GetError());
        }
        const Xform x{
            {box.x0 - static_cast<float>(s.x) / res, box.y0 - static_cast<float>(s.y) / res},
            res,
            level > 0 ? SDL_SCALEMODE_LINEAR : SDL_SCALEMODE_NEAREST};
        drawChunk(batch, world, level, cx, cy, x, now);
        batch.flush();
        if (!SDL_SetRenderClipRect(renderer_, nullptr)) SDL_Log("ground: %s", SDL_GetError());
    });
    if (!SDL_SetRenderTarget(renderer_, targetTexture)) SDL_Log("ground: %s", SDL_GetError());

    // Pass 2: composite the slots (and draw any overflow directly), in order.
    const float k = target.res / res;
    const SDL_ScaleMode filter = k == 1.0f ? SDL_SCALEMODE_NEAREST : SDL_SCALEMODE_LINEAR;
    each([&](int cx, int cy) {
        const auto it = byKey_.find(keyOf(level, cx, cy));
        if (it == byKey_.end() || slots_[static_cast<std::size_t>(it->second)].used != frame_) {
            drawChunk(batch, world, level, cx, cy, target, now);
            return;
        }
        const Slot& s = slots_[static_cast<std::size_t>(it->second)];
        const FRect box = chunkBox(level, cx, cy);
        const Vec2 p = target.apply({box.x0, box.y0});
        const auto pw = static_cast<float>(slotW_ * slotsX_);
        const auto ph = static_cast<float>(slotH_ * slotsY_);
        // Slots were drawn over transparent black, so they hold premultiplied colour (which is
        // also what keeps filtered edges from darkening).
        batch.use(pages_[static_cast<std::size_t>(s.page)].get(), SDL_BLENDMODE_BLEND_PREMULTIPLIED,
                  filter);
        batch.quad(
            SDL_FRect{p.x, p.y, static_cast<float>(slotW_) * k, static_cast<float>(slotH_) * k},
            {static_cast<float>(s.x) / pw, static_cast<float>(s.y) / ph,
             static_cast<float>(s.x + slotW_) / pw, static_cast<float>(s.y + slotH_) / ph},
            kWhite);
    });
}

} // namespace lc
