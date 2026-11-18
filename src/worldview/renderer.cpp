#include "worldview/renderer.hpp"

#include "core/rng.hpp"
#include "render/draw.hpp"
#include "worldview/tuning.hpp"

#include <algorithm>
#include <cmath>
#include <format>

namespace lc::worldview {
namespace {

constexpr SDL_FColor kWhite{1, 1, 1, 1};
constexpr int kMaxLevel = 15;
constexpr std::uint64_t kRegionTag = 1ULL << 63; // block tags are cell keys shifted by two

SDL_FColor times(SDL_FColor c, float k) {
    return {c.r * k, c.g * k, c.b * k, c.a};
}

int sameMask(const world::WorldMap& m, TilePos p, int t) {
    int mask = 0;
    const auto same = [&](int dx, int dy) {
        const TilePos n{p.x + dx, p.y + dy};
        return m.inBounds(n) && m.terrainAt(n) == t;
    };
    if (same(0, -1)) mask |= kMaskN;
    if (same(1, 0)) mask |= kMaskE;
    if (same(0, 1)) mask |= kMaskS;
    if (same(-1, 0)) mask |= kMaskW;
    return mask;
}

template <typename F>
void diagonals(TileRect r, F&& f) {
    for (int s = r.x0 + r.y0; s <= r.x1 + r.y1 - 2; ++s)
        for (int tx = std::max(r.x0, s - (r.y1 - 1)); tx <= std::min(r.x1 - 1, s - r.y0); ++tx)
            f(TilePos{tx, s - tx});
}

} // namespace

Lod WorldView::lodFor(float scale) {
    if (scale >= 1.0f) return Lod::Native;
    if (scale >= 0.5f) return Lod::Half;
    if (scale >= 0.25f) return Lod::Quarter;
    return Lod::Overview;
}

WorldView::WorldView(SDL_Renderer* renderer, const world::LoadedWorld& world,
                     const std::filesystem::path& assets, Atlas& home, Font& font, bool async)
    : renderer_(renderer), world_(world), map_(*world.map), iso_(map_.content().home().iso()),
      lvl_(map_.content().tileLevel()), async_(async), cells_(renderer, tuning::kCellBudget),
      batch_(renderer), theme_(
                            [&] {
                                std::vector<world::Theme> themes;
                                for (const world::RegionFile& r : world.regions)
                                    themes.push_back(r.theme);
                                return themes;
                            }(),
                            [&] {
                                std::vector<std::string> times;
                                for (const world::RegionRef& r : world.file.regions)
                                    times.push_back(r.time);
                                return times;
                            }()) {
    pages_ = std::make_unique<PageAtlas>(renderer, home, world.atlas, assets / "atlas", async,
                                         tuning::kPageBudget);
    sprites_ = std::make_unique<WorldSprites>(renderer, home, *pages_, map_, font);
    overview_ = std::make_unique<Overview>(map_, *sprites_, *pages_, async);
    prep_ = std::make_unique<Prep>(map_, *sprites_, async);
    if (async) warmUp();
    for (std::size_t t = 0; t < map_.terrainCount(); ++t) {
        const TerrainLook& l = sprites_->terrain(static_cast<int>(t));
        if (l.animated() || (!l.foam[0].empty() && l.fps > 0)) animFps_ = std::max(animFps_, l.fps);
    }
    // Backdrops by region: the first strip of the region's set (world-tech §1.11).
    backdrops_.resize(world.file.regions.size());
    for (std::size_t r = 0; r < world.file.regions.size(); ++r) {
        const auto set = std::ranges::find(map_.content().sets(), world.file.regions[r].set,
                                           &world::SetCatalog::set);
        if (set == map_.content().sets().end() || set->art.backdrops.empty()) continue;
        for (int n = 0; n < 2; ++n)
            for (int v = 0;; ++v) {
                const auto s = pages_->find(std::format(
                    "backdrop/{}/{}/v{}", set->art.backdrops.front(), n == 0 ? "day" : "night", v));
                if (!s) break;
                backdrops_[r][static_cast<std::size_t>(n)].push_back(*s);
            }
    }
}

WorldView::~WorldView() = default;

void WorldView::warmUp() {
    // Drivers prepare blend and filter state on first use, a stall of several milliseconds in
    // the middle of a run: use every combination once, into a scratch target, and wait.
    SDL_Texture* out = SDL_GetRenderTarget(renderer_);
    ensure(half_, tuning::kImpostorBlock / 2, tuning::kImpostorBlock / 2);
    SDL_Texture* white = pages_->texture(sprites_->white().page);
    if (!SDL_SetRenderTarget(renderer_, half_.texture.get()))
        SDL_Log("worldview: %s", SDL_GetError());
    for (const SDL_BlendMode mode :
         {SDL_BLENDMODE_NONE, SDL_BLENDMODE_BLEND, SDL_BLENDMODE_BLEND_PREMULTIPLIED,
          SDL_BLENDMODE_ADD, SDL_BLENDMODE_MOD})
        for (const SDL_ScaleMode scale : {SDL_SCALEMODE_NEAREST, SDL_SCALEMODE_LINEAR}) {
            batch_.use(white, mode, scale);
            batch_.quad(SDL_FRect{0, 0, 2, 2}, sprites_->white().uv, kWhite);
            batch_.flush();
        }
    batch_.use(nullptr, SDL_BLENDMODE_NONE);
    static constexpr int kTri[3] = {0, 1, 2};
    const SDL_Vertex v[3] = {
        {{0, 0}, kWhite, {0, 0}}, {{2, 0}, kWhite, {0, 0}}, {{0, 2}, kWhite, {0, 0}}};
    batch_.triangles(v, 3, kTri, 3);
    batch_.flush();
    const SDL_Rect one{0, 0, 1, 1};
    if (const SurfacePtr px{SDL_RenderReadPixels(renderer_, &one)}; !px)
        SDL_Log("worldview: %s", SDL_GetError());
    if (!SDL_SetRenderTarget(renderer_, out)) SDL_Log("worldview: %s", SDL_GetError());
    batch_.resetStats();
}

bool WorldView::put(const SpriteRef& s, Vec2 anchor, const Xform& x, SDL_FColor c,
                    SDL_BlendMode mode, bool mirror) {
    SDL_Texture* t = pages_->texture(s.page);
    if (t == nullptr) return false;
    putSprite(batch_, Sprite{t, s.uv, s.w, s.h, s.ox, s.oy}, anchor, x, c, mode, mirror);
    return true;
}

bool WorldView::putFace(const SpriteRef& s, int side, Vec2 anchor, const Xform& x, SDL_FColor c) {
    // A face spans the columns from its tile's bottom vertex to the side vertex, both included
    // (hw + 1 of them), or straight cliffs show a seam at every tile and concave corners a gap.
    // Narrower art gets a copy shifted two columns outward at each end, along the edge's 2:1
    // slope, underneath it.
    bool ok = true;
    if (s.w <= iso_.hw) {
        const float out = side == 0 ? -2.0f : 2.0f; // towards the bottom vertex
        ok &= put(s, {anchor.x + out, anchor.y + 1.0f}, x, c, SDL_BLENDMODE_BLEND);
        ok &= put(s, {anchor.x - out, anchor.y - 1.0f}, x, c, SDL_BLENDMODE_BLEND);
    }
    return put(s, anchor, x, c, SDL_BLENDMODE_BLEND) && ok;
}

bool WorldView::drawTile(TilePos p, const Xform& x, float now, bool* animated) {
    const int t = map_.terrainAt(p);
    if (t == world::kNone) return true;
    const TerrainLook& look = sprites_->terrain(t);
    const std::uint8_t lb = map_.levelByte(p);
    const int level = world::levelOf(lb);
    const int aux = world::auxOf(lb);
    const Vec2 a = [&] {
        const Vec2 w = iso_.toWorld(p);
        return Vec2{w.x, w.y - static_cast<float>(level * lvl_)};
    }();
    const MaterialLook* mat =
        look.water ? &sprites_->waterFace()
                   : (look.faces[static_cast<std::size_t>(aux)] >= 0
                          ? &sprites_->material(look.faces[static_cast<std::size_t>(aux)])
                          : nullptr);
    bool ok = true;
    std::array<int, 2> drop{};
    // Faces hang under the +x and +y edges, one band per level down to the neighbour (or to
    // level 0 at the world's rim); the uppermost band's cap goes on after the ground.
    for (int side = 0; side < 2; ++side) {
        const TilePos n = side == 0 ? TilePos{p.x + 1, p.y} : TilePos{p.x, p.y + 1};
        const int ln = map_.inBounds(n) && map_.terrainAt(n) != world::kNone ? map_.level(n) : 0;
        drop[static_cast<std::size_t>(side)] = level - ln;
        const auto s = static_cast<std::size_t>(side);
        for (int b = 0; b < level - ln; ++b) {
            const Vec2 at{a.x, a.y + static_cast<float>(b * lvl_)};
            if (mat != nullptr && !mat->band[s].empty()) {
                if (b == 0 && mat->top[s]) continue;
                const auto& v = mat->band[s];
                ok &= putFace(v[tileHash(p.x, p.y, 3u + static_cast<std::uint32_t>(b)) % v.size()],
                              side, at, x, kWhite);
            } else {
                const SDL_FColor c = times(mat != nullptr ? mat->flat : look.flat,
                                           side == 0 ? tuning::kFaceShadeSE : tuning::kFaceShadeSW);
                ok &= put(sprites_->face(side), at, x, c, SDL_BLENDMODE_BLEND);
            }
        }
    }
    const float tint = look.water ? 1.0f - tuning::kWaterDepthTint * static_cast<float>(aux) : 1.0f;
    const float jitter =
        1.0f +
        tuning::kFlatJitter * (static_cast<float>(tileHash(p.x, p.y, 7) % 100) / 50.0f - 1.0f);
    const SDL_FColor shade{tint, tint, tint, 1};
    const bool overlay = !map_.terrainInfo(t).base;
    if (!overlay || look.hasOverlay()) {
        if (look.base.empty())
            ok &=
                put(sprites_->diamond(), a, x,
                    times(overlay ? look.flatBase : look.flat, jitter * tint), SDL_BLENDMODE_BLEND);
        else
            ok &= put(look.base[tileHash(p.x, p.y, 1) % look.base.size()], a, x, shade,
                      SDL_BLENDMODE_BLEND);
    }
    if (overlay) {
        if (look.hasOverlay()) {
            const Frames& f = look.overlay[static_cast<std::size_t>(sameMask(map_, p, t))];
            ok &= put(f.at(now, look.fps), a, x, shade, SDL_BLENDMODE_BLEND);
            if (look.animated() && animated != nullptr) *animated = true;
        } else {
            ok &= put(sprites_->diamond(), a, x, times(look.flat, jitter * tint),
                      SDL_BLENDMODE_BLEND);
        }
    }
    if (look.water && !look.foam[0].empty()) {
        // Foam where the water meets land: the mask is of land neighbours.
        int land = 0;
        const auto dry = [&](int dx, int dy) {
            const TilePos n{p.x + dx, p.y + dy};
            if (!map_.inBounds(n)) return false;
            const int nt = map_.terrainAt(n);
            return nt != world::kNone && !sprites_->terrain(nt).water;
        };
        if (dry(0, -1)) land |= kMaskN;
        if (dry(1, 0)) land |= kMaskE;
        if (dry(0, 1)) land |= kMaskS;
        if (dry(-1, 0)) land |= kMaskW;
        if (land != 0) {
            ok &= put(look.foam[static_cast<std::size_t>(land)].at(now, look.fps), a, x, kWhite,
                      SDL_BLENDMODE_BLEND);
            if (animated != nullptr && look.fps > 0) *animated = true;
        }
    }
    for (int side = 0; side < 2; ++side) {
        const auto s = static_cast<std::size_t>(side);
        if (mat != nullptr && mat->top[s] && drop[s] > 0)
            ok &= putFace(*mat->top[s], side, a, x, kWhite);
    }
    return ok;
}

bool WorldView::drawTiles(const FRect& px, const Xform& x, float now, bool* animated) {
    const Reach& r = sprites_->groundReach();
    const TileRect tiles = tilesUnder(grown(px, r), iso_).clipped(map_.bounds());
    if (tiles.empty()) return true;
    const float lift = r.up - static_cast<float>(kMaxLevel * lvl_);
    bool ok = true;
    diagonals(tiles, [&](TilePos p) {
        const Vec2 w = iso_.toWorld(p);
        const float top = w.y - static_cast<float>(map_.level(p) * lvl_) - lift;
        if (w.x + r.right < px.x0 || w.x - r.left > px.x1 || w.y + r.down < px.y0 || top > px.y1)
            return;
        ok &= drawTile(p, x, now, animated);
    });
    return ok;
}

bool WorldView::drawElem(const Elem& e, const Xform& x, float now) {
    if (e.ground) return drawTile(e.tile, x, now, nullptr);
    const VariantLook& look = *e.look;
    const SpriteRef& s = e.piece >= 0 ? look.pieces[static_cast<std::size_t>(e.piece)]
                                      : look.base.at(now, sprites_->itemFps(map_.items()[e.item]));
    return put(s, e.anchor, x, kWhite, SDL_BLENDMODE_BLEND);
}

bool WorldView::drawShadows(const Gathered& g, const FRect& clip, const Xform& x, Target& layer,
                            Target& onto) {
    // Shadow sprites saturate in their own layer (their alpha was scaled to a peak of 1), which
    // is then laid over the ground once at the art's opacity: overlaps never double-darken.
    bool ok = true;
    batch_.flush();
    if (!SDL_SetRenderTarget(renderer_, layer.texture.get()) ||
        !SDL_SetRenderDrawColorFloat(renderer_, 0, 0, 0, 0) || !SDL_RenderClear(renderer_))
        SDL_Log("worldview: shadow layer: %s", SDL_GetError());
    // The layer's coverage does not depend on order: drawn page by page, one draw each.
    shadows_.clear();
    for (const std::uint32_t i : g.order) {
        const Elem& e = g.elems[i];
        if (!e.first || e.look == nullptr || !e.look->shadow) continue;
        const SpriteRef& s = *e.look->shadow;
        const FRect box{e.anchor.x - s.ox, e.anchor.y - s.oy, e.anchor.x - s.ox + s.w,
                        e.anchor.y - s.oy + s.h};
        if (box.overlaps(clip)) shadows_.emplace_back(s.page, i);
    }
    std::ranges::stable_sort(shadows_, {}, &std::pair<std::uint16_t, std::uint32_t>::first);
    for (const auto& [page, i] : shadows_)
        ok &= put(*g.elems[i].look->shadow, g.elems[i].anchor, x, kWhite, SDL_BLENDMODE_BLEND);
    const bool any = !shadows_.empty();
    batch_.flush();
    if (!SDL_SetRenderTarget(renderer_, onto.texture.get()))
        SDL_Log("worldview: %s", SDL_GetError());
    if (any) {
        const float w = static_cast<float>(layer.w);
        const float h = static_cast<float>(layer.h);
        batch_.use(layer.texture.get(), SDL_BLENDMODE_BLEND_PREMULTIPLIED, SDL_SCALEMODE_NEAREST);
        const float k = shadowOpacity();
        batch_.quad(SDL_FRect{0, 0, w, h}, {0, 0, 1, 1}, {k, k, k, k});
        batch_.flush();
    }
    return ok;
}

float WorldView::shadowOpacity() const {
    const float home = sprites_->homeShadowPeak();
    const float sets = pages_->shadowOpacity();
    return home >= 0 ? (home + sets) * 0.5f : sets;
}

void WorldView::buildGround(CellKey key, int si, double now) {
    // The ground straight into the slot, at native resolution.
    const int before = batch_.drawCalls();
    CellSlot& slot = cells_.slot(si);
    const FRect cell = cellRect(key);
    bool animated = false;
    batch_.flush();
    const auto fx = static_cast<float>(slot.x);
    const auto fy = static_cast<float>(slot.y);
    const SDL_Rect clip{slot.x, slot.y, tuning::kCellTexels, tuning::kCellTexels};
    const SDL_FRect fill{fx, fy, static_cast<float>(tuning::kCellTexels),
                         static_cast<float>(tuning::kCellTexels)};
    if (!SDL_SetRenderTarget(renderer_, cells_.page(slot.page)) ||
        !SDL_SetRenderClipRect(renderer_, &clip) ||
        !SDL_SetRenderDrawBlendMode(renderer_, SDL_BLENDMODE_NONE) ||
        !SDL_SetRenderDrawColorFloat(renderer_, 0, 0, 0, 0) ||
        !SDL_RenderFillRect(renderer_, &fill))
        SDL_Log("worldview: cell: %s", SDL_GetError());
    slot.complete = drawTiles(cell, {{cell.x0 - fx, cell.y0 - fy}, 1.0f, SDL_SCALEMODE_NEAREST},
                              static_cast<float>(now), &animated);
    batch_.flush();
    if (!SDL_SetRenderClipRect(renderer_, nullptr)) SDL_Log("worldview: %s", SDL_GetError());
    slot.animated = animated;
    slot.generation = pages_->generation();
    slot.anim = animFps_ > 0 ? static_cast<std::uint64_t>(now * animFps_) : 0;
    slot.ready = true;
    ++stats_.cellsBuilt;
    stats_.buildDrawCalls += batch_.drawCalls() - before;
}

namespace {

int blocksPerSide(int level) {
    return cellPx(level) / tuning::kImpostorBlock;
}

FRect blockRect(CellKey key, int block) {
    const FRect c = cellRect(key);
    const int n = blocksPerSide(key.level);
    const auto b = static_cast<float>(tuning::kImpostorBlock);
    const auto bx = static_cast<float>(block % n);
    const auto by = static_cast<float>(block / n);
    return {c.x0 + bx * b, c.y0 + by * b, c.x0 + (bx + 1) * b, c.y0 + (by + 1) * b};
}

std::uint64_t blockTag(CellKey key, int block) {
    return (packCell(key) << 2) | static_cast<std::uint64_t>(block);
}

} // namespace

void WorldView::requestImpostor(CellKey key, int si) {
    const int n = blocksPerSide(key.level);
    for (int b = 0; b < n * n; ++b) {
        const FRect r = blockRect(key, b);
        prep_->request({blockTag(key, b), gatherTiles(r, sprites_->itemSpan(), iso_), r});
    }
    cells_.slot(si).complete = true;
    building_.push_back({key, si, 0});
}

void WorldView::drawBlock(CellKey key, int si, int block, const Gathered& g) {
    // The block at full resolution with everything static, then halved with filtering into its
    // share of the slot (each halving averages 2 x 2 texels): 1024 -> 512 for level 1, and
    // -> 512 -> 256 for level 2.
    const int before = batch_.drawCalls();
    batch_.flush();
    const int size0 = tuning::kImpostorBlock;
    ensure(scratch_, size0, size0);
    ensure(scratchShadow_, size0, size0);
    ensure(half_, size0 / 2, size0 / 2);
    CellSlot& slot = cells_.slot(si);
    const FRect r = blockRect(key, block);
    const Xform x{{r.x0, r.y0}, 1.0f, SDL_SCALEMODE_NEAREST};
    if (!SDL_SetRenderTarget(renderer_, scratch_.texture.get()) ||
        !SDL_SetRenderDrawColorFloat(renderer_, 0, 0, 0, 0) || !SDL_RenderClear(renderer_))
        SDL_Log("worldview: impostor: %s", SDL_GetError());
    bool complete = drawTiles(r, x, 0, nullptr);
    complete &= drawShadows(g, r, x, scratchShadow_, scratch_);
    for (const std::uint32_t i : g.order) complete &= drawElem(g.elems[i], x, 0);
    batch_.flush();
    const int n = blocksPerSide(key.level);
    const int dst = tuning::kCellTexels / n;
    const Target* src = &scratch_;
    int size = size0;
    while (size / 2 > dst) {
        if (!SDL_SetRenderTarget(renderer_, half_.texture.get()))
            SDL_Log("worldview: %s", SDL_GetError());
        batch_.use(src->texture.get(), SDL_BLENDMODE_NONE, SDL_SCALEMODE_LINEAR);
        const auto hs = static_cast<float>(size / 2);
        batch_.quad(SDL_FRect{0, 0, hs, hs},
                    {0, 0, static_cast<float>(size) / static_cast<float>(src->w),
                     static_cast<float>(size) / static_cast<float>(src->h)},
                    kWhite);
        batch_.flush();
        src = &half_;
        size /= 2;
    }
    if (!SDL_SetRenderTarget(renderer_, cells_.page(slot.page)))
        SDL_Log("worldview: %s", SDL_GetError());
    batch_.use(src->texture.get(), SDL_BLENDMODE_NONE, SDL_SCALEMODE_LINEAR);
    batch_.quad(SDL_FRect{static_cast<float>(slot.x + (block % n) * dst),
                          static_cast<float>(slot.y + (block / n) * dst), static_cast<float>(dst),
                          static_cast<float>(dst)},
                {0, 0, static_cast<float>(size) / static_cast<float>(src->w),
                 static_cast<float>(size) / static_cast<float>(src->h)},
                kWhite);
    batch_.flush();
    slot.complete = slot.complete && complete;
    stats_.buildDrawCalls += batch_.drawCalls() - before;
}

void WorldView::progressImpostors() {
    int budget = async_ ? tuning::kImpostorBlocksPerFrame : 1 << 30;
    for (auto it = building_.begin(); it != building_.end();) {
        Building& b = *it;
        const int n = blocksPerSide(b.key.level);
        const std::uint32_t all = (1u << (n * n)) - 1;
        // Looking the cell up keeps its slot from being reused while it fills in.
        const bool alive = cells_.find(packCell(b.key)) == b.slot;
        for (int k = 0; k < n * n; ++k) {
            const std::uint32_t bit = 1u << k;
            if ((b.done & bit) != 0) continue;
            if (alive && budget <= 0) break;
            if (!prep_->take(blockTag(b.key, k), block_)) continue;
            b.done |= bit;
            if (!alive) continue;
            drawBlock(b.key, b.slot, k, block_);
            --budget;
        }
        if (b.done != all) {
            ++it;
            continue;
        }
        if (alive) {
            CellSlot& s = cells_.slot(b.slot);
            s.ready = true;
            s.generation = pages_->generation();
            ++stats_.impostorsBuilt;
        }
        it = building_.erase(it);
    }
}

void WorldView::drawCells(int level, const FRect& view, const Xform& x, double now) {
    const std::uint64_t anim = animFps_ > 0 ? static_cast<std::uint64_t>(now * animFps_) : 0;
    const auto stale = [&](int si) {
        const CellSlot& s = cells_.slot(si);
        return (!s.complete && s.generation != pages_->generation()) ||
               (level == 0 && s.animated && s.anim != anim);
    };
    const auto building = [&](CellKey k) {
        return std::ranges::any_of(building_, [&](const Building& b) { return b.key == k; });
    };
    int budget = async_ ? tuning::kCellBuildsPerFrame : 1 << 30;
    // Brings a cell up to date if the budget allows; false when it is not drawn yet.
    const auto build = [&](CellKey k) {
        const std::uint64_t key = packCell(k);
        int si = cells_.find(key);
        if (si >= 0 && !stale(si)) return cells_.slot(si).ready;
        if (level == 0) {
            if (budget <= 0) return false;
            if (si < 0) si = cells_.acquire(key);
            if (si < 0) return false;
            --budget;
            buildGround(k, si, now);
            return true;
        }
        if (building(k)) return si >= 0 && cells_.slot(si).ready;
        if (async_ && static_cast<int>(building_.size()) >= tuning::kImpostorCellsInFlight)
            return si >= 0 && cells_.slot(si).ready;
        if (si < 0) {
            si = cells_.acquire(key);
            if (si < 0) return false;
            cells_.slot(si).ready = false;
        }
        requestImpostor(k, si);
        return cells_.slot(si).ready;
    };
    if (level > 0) progressImpostors();
    keys_.clear();
    forEachCell(view, level, [&](CellKey k) { keys_.push_back(k); });
    for (const CellKey& k : keys_) (void)build(k);
    // Spare budget prepares the ring around the view.
    if (async_) {
        const auto s = static_cast<float>(cellPx(level) * tuning::kCellPrefetch);
        forEachCell({view.x0 - s, view.y0 - s, view.x1 + s, view.y1 + s}, level, [&](CellKey k) {
            if (cells_.find(packCell(k)) < 0) (void)build(k);
        });
    }
    if (level > 0 && !async_) progressImpostors();
    for (const CellKey& k : keys_) {
        const int si = cells_.find(packCell(k));
        if (si < 0 || !cells_.slot(si).ready) ++stats_.cellsPending;
    }
    if (!SDL_SetRenderTarget(renderer_, view_.texture.get()))
        SDL_Log("worldview: %s", SDL_GetError());
    // Cells not built yet show the overview underneath, or their coarser level.
    if (stats_.cellsPending > 0) drawOverview(x);
    // Cells never overlap, so they go page by page: one draw per cache page.
    const Vec2 side = CellCache::pageSize();
    composite_.clear();
    for (const CellKey& k : keys_) {
        int si = -1;
        CellKey from = k;
        for (int l = level; l <= 2 && si < 0; ++l) {
            from = {l, k.cx >> (l - level), k.cy >> (l - level)};
            si = cells_.find(packCell(from));
            if (si >= 0 && !cells_.slot(si).ready) si = -1;
        }
        if (si >= 0) composite_.push_back({k, from, si});
    }
    std::ranges::stable_sort(composite_, [&](const Composite& a, const Composite& b) {
        return cells_.slot(a.slot).page < cells_.slot(b.slot).page;
    });
    for (const Composite& c : composite_) {
        const CellSlot& s = cells_.slot(c.slot);
        // The part of the slot that covers the cell (all of it unless a coarser one stands in).
        const int shift = c.from.level - level;
        const int part = tuning::kCellTexels >> shift;
        const int ox = (c.key.cx - (c.from.cx << shift)) * part;
        const int oy = (c.key.cy - (c.from.cy << shift)) * part;
        const FRect r = cellRect(c.key);
        const Vec2 p0 = x.apply({r.x0, r.y0});
        const Vec2 p1 = x.apply({r.x1, r.y1});
        batch_.use(cells_.page(s.page), SDL_BLENDMODE_BLEND_PREMULTIPLIED,
                   shift == 0 ? SDL_SCALEMODE_NEAREST : SDL_SCALEMODE_LINEAR);
        batch_.quad(SDL_FRect{p0.x, p0.y, p1.x - p0.x, p1.y - p0.y},
                    {static_cast<float>(s.x + ox) / side.x, static_cast<float>(s.y + oy) / side.y,
                     static_cast<float>(s.x + ox + part) / side.x,
                     static_cast<float>(s.y + oy + part) / side.y},
                    kWhite);
    }
}

void WorldView::drawOverview(const Xform& x) {
    SDL_Texture* t = overview_->texture();
    if (t == nullptr) return;
    const OverviewImage& img = overview_->image();
    const float k = 1.0f / img.scale;
    const Vec2 p0 = x.apply(img.origin);
    const Vec2 p1 = x.apply({img.origin.x + static_cast<float>(img.w) * k,
                             img.origin.y + static_cast<float>(img.h) * k});
    batch_.use(t, SDL_BLENDMODE_BLEND, SDL_SCALEMODE_LINEAR);
    batch_.quad(SDL_FRect{p0.x, p0.y, p1.x - p0.x, p1.y - p0.y}, {0, 0, 1, 1}, kWhite);
}

void WorldView::drawBackdrops(const FRect& view, const Xform& x, bool night) {
    // Strips of 16 edge tiles behind the north (tx = 0) and east (ty = 0) edges; the north ones
    // are the same art mirrored, running the other way.
    constexpr int kSegment = 16;
    const auto n = static_cast<std::size_t>(night ? 1 : 0);
    for (int edge = 0; edge < 2; ++edge) {
        const int len = edge == 0 ? map_.width() : map_.height();
        for (int k = 0; k * kSegment < len; ++k) {
            const TilePos first = edge == 0 ? TilePos{k * kSegment, 0} : TilePos{0, k * kSegment};
            const int region = map_.regionAt(first);
            if (region < 0) continue;
            const auto& strips = backdrops_[static_cast<std::size_t>(region)][n];
            if (strips.empty()) continue;
            const SpriteRef& s = strips[tileHash(first.x, first.y, 11) % strips.size()];
            const Vec2 w = iso_.toWorld(first);
            const Vec2 a{w.x, w.y - static_cast<float>(map_.level(first) * lvl_)};
            const FRect box =
                edge == 0 ? FRect{a.x - s.ox, a.y - s.oy, a.x - s.ox + s.w, a.y - s.oy + s.h}
                          : FRect{a.x - (s.w - s.ox), a.y - s.oy, a.x + s.ox, a.y - s.oy + s.h};
            if (box.overlaps(view)) (void)put(s, a, x, kWhite, SDL_BLENDMODE_BLEND, edge == 1);
        }
    }
}

void WorldView::wantSets(const FRect& view) {
    // The sets of the regions sampled over the view grown by 64 tiles (world-tech §4.5).
    const TileRect t = tilesUnder(view, iso_);
    const int g = tuning::kNeededSetGrow;
    const TileRect r = TileRect{t.x0 - g, t.y0 - g, t.x1 + g, t.y1 + g}.clipped(map_.bounds());
    const int step = tuning::kNeededSetSpacing;
    std::vector<bool>& seen = setSeen_;
    seen.assign(world_.file.regions.size(), false);
    for (int y = r.y0; y < r.y1; y += step)
        for (int x = r.x0; x < r.x1; x += step) {
            const int region = map_.regionAt({x, y});
            if (region < 0 || seen[static_cast<std::size_t>(region)]) continue;
            seen[static_cast<std::size_t>(region)] = true;
            pages_->want(world_.file.regions[static_cast<std::size_t>(region)].set);
        }
    pages_->want("world");
}

void WorldView::ensure(Target& t, int w, int h) {
    if (!t.texture || t.w < w || t.h < h) {
        t.w = std::max(w, t.w);
        t.h = std::max(h, t.h);
        t.texture.reset(
            SDL_CreateTexture(renderer_, kTextureFormat, SDL_TEXTUREACCESS_TARGET, t.w, t.h));
        if (!t.texture ||
            !SDL_SetTextureBlendMode(t.texture.get(), SDL_BLENDMODE_BLEND_PREMULTIPLIED))
            SDL_Log("worldview: cannot create a target: %s", SDL_GetError());
    }
}

std::size_t WorldView::targetBytes() const {
    std::size_t n = 0;
    for (const Target* t : {&view_, &shadow_, &scratch_, &scratchShadow_, &half_})
        if (t->texture) n += static_cast<std::size_t>(t->w) * static_cast<std::size_t>(t->h) * 4;
    return n;
}

void WorldView::fullQuad(int w, int h, SDL_FColor c, SDL_BlendMode mode) {
    const SpriteRef& white = sprites_->white();
    SDL_Texture* t = pages_->texture(white.page);
    if (t == nullptr) return;
    batch_.use(t, mode, SDL_SCALEMODE_NEAREST);
    batch_.quad(SDL_FRect{0, 0, static_cast<float>(w), static_cast<float>(h)}, white.uv, c);
}

void WorldView::jumped(const WorldCamera& camera) {
    std::array<world::RegionWeight, 16> w{};
    const int n = map_.themeWeights(iso_.toTile(camera.centre()), w);
    theme_.reset(std::span(w).first(static_cast<std::size_t>(n)));
    themed_ = true;
}

void WorldView::draw(const WorldCamera& camera, double clock, float dt, double now) {
    SDL_Texture* out = SDL_GetRenderTarget(renderer_);
    stats_ = {};
    batch_.resetStats();
    cells_.beginFrame();
    const float s = camera.scale();
    const Lod lod = lodFor(s);
    stats_.lod = lod;
    const OverviewImage& ov = overview_->image();
    const float res = lod == Lod::Native    ? 1.0f
                      : lod == Lod::Half    ? 0.5f
                      : lod == Lod::Quarter ? 0.25f
                                            : std::min(ov.scale, s);
    const Vec2 screen = camera.screen();
    const Vec2 c = camera.centre();
    const Vec2 topLeft{c.x - screen.x * 0.5f / s, c.y - screen.y * 0.5f / s};
    // The target's origin sits on its own pixel grid, so cached cells land on whole texels.
    const float px = 1.0f / res;
    const Vec2 origin{std::floor(topLeft.x / px) * px - px, std::floor(topLeft.y / px) * px - px};
    viewW_ = static_cast<int>(std::ceil(screen.x / s * res)) + 3;
    viewH_ = static_cast<int>(std::ceil(screen.y / s * res)) + 3;
    ensure(view_, viewW_, viewH_);
    if (lod == Lod::Native) ensure(shadow_, viewW_, viewH_);
    const Xform xf{origin, res, res < 1.0f ? SDL_SCALEMODE_LINEAR : SDL_SCALEMODE_NEAREST};
    const FRect view{origin.x, origin.y, origin.x + static_cast<float>(viewW_) * px,
                     origin.y + static_cast<float>(viewH_) * px};

    // Themes and light.
    std::array<world::RegionWeight, 16> weights{};
    const int nw = map_.themeWeights(iso_.toTile(c), weights);
    const auto ws = std::span(weights).first(static_cast<std::size_t>(nw));
    if (!themed_) {
        theme_.reset(ws);
        themed_ = true;
    } else {
        theme_.update(ws, dt);
    }
    const Lighting light = lightingAt(clock, 0);
    const Grade grade = theme_.grade(clock);
    const SDL_FColor ambient{light.ambient.r * grade.mul.r, light.ambient.g * grade.mul.g,
                             light.ambient.b * grade.mul.b, 1};

    // Streaming.
    if (lod != Lod::Overview) wantSets(view);
    pages_->update(now);
    while (!overview_->upload(renderer_) && !async_) {}

    if (!SDL_SetRenderTarget(renderer_, view_.texture.get()) ||
        !SDL_SetRenderDrawColorFloat(renderer_, 0, 0, 0, 0) || !SDL_RenderClear(renderer_))
        SDL_Log("worldview: %s", SDL_GetError());
    if (lod != Lod::Overview) drawBackdrops(view, xf, light.night > 0.5f);
    if (lod == Lod::Overview) {
        drawOverview(xf);
    } else {
        const int level = lod == Lod::Native ? 0 : (lod == Lod::Half ? 1 : 2);
        drawCells(level, view, xf, now);
    }
    // A flight down to the native level gathers its destination on the way.
    if (camera.flying() && lodFor(camera.arrivalScale()) == Lod::Native) {
        const Vec2 to = camera.arrival();
        const float k = 0.5f / camera.arrivalScale();
        updateRegion(
            {to.x - screen.x * k, to.y - screen.y * k, to.x + screen.x * k, to.y + screen.y * k},
            false);
    }
    if (lod == Lod::Native) {
        if (!camera.flying()) updateRegion(view, true);
        stats_.regionElements = static_cast<int>(region_.elems.size());
        (void)drawShadows(region_, view, xf, shadow_, view_);
        for (const std::uint32_t i : region_.order) {
            if (!region_.items[i].screen.overlaps(view)) {
                ++stats_.spritesCulled;
                continue;
            }
            (void)drawElem(region_.elems[i], xf, static_cast<float>(now));
            ++stats_.spritesDrawn;
        }
    }
    batch_.flush();
    // Grading, then what glows (drawn after it, additively).
    fullQuad(viewW_, viewH_, ambient, SDL_BLENDMODE_MOD);
    if (lod == Lod::Native && light.glow > 0.01f) {
        const SDL_FColor g{light.glow, light.glow, light.glow, 1};
        for (const std::uint32_t i : region_.order) {
            const Elem& e = region_.elems[i];
            if (e.first && e.look != nullptr && e.look->glow &&
                region_.items[i].screen.overlaps(view))
                (void)put(*e.look->glow, e.anchor, xf, g, SDL_BLENDMODE_ADD);
        }
    }
    batch_.flush();

    // Onto the window: sky, the world, the haze.
    if (!SDL_SetRenderTarget(renderer_, out)) SDL_Log("worldview: %s", SDL_GetError());
    const SDL_FColor top{light.skyTop.r, light.skyTop.g, light.skyTop.b, 1};
    const SDL_FColor bottom{light.skyBottom.r, light.skyBottom.g, light.skyBottom.b, 1};
    const SDL_Vertex sky[4] = {{{0, 0}, top, {0, 0}},
                               {{screen.x, 0}, top, {0, 0}},
                               {{screen.x, screen.y}, bottom, {0, 0}},
                               {{0, screen.y}, bottom, {0, 0}}};
    static constexpr int kQuad[6] = {0, 1, 2, 0, 2, 3};
    batch_.use(nullptr, SDL_BLENDMODE_NONE);
    batch_.triangles(sky, 4, kQuad, 6);
    const float k = s / res; // window px per target px
    const bool whole = std::abs(k - std::round(k)) < 1e-3f;
    batch_.use(view_.texture.get(), SDL_BLENDMODE_BLEND_PREMULTIPLIED,
               whole ? SDL_SCALEMODE_NEAREST : SDL_SCALEMODE_LINEAR);
    batch_.quad(SDL_FRect{(origin.x - topLeft.x) * s, (origin.y - topLeft.y) * s,
                          static_cast<float>(viewW_) * k, static_cast<float>(viewH_) * k},
                {0, 0, static_cast<float>(viewW_) / static_cast<float>(view_.w),
                 static_cast<float>(viewH_) / static_cast<float>(view_.h)},
                kWhite);
    if (grade.hazeStrength > 0.001f)
        fullQuad(static_cast<int>(screen.x), static_cast<int>(screen.y),
                 {grade.haze.r, grade.haze.g, grade.haze.b, grade.hazeStrength},
                 SDL_BLENDMODE_BLEND);
    batch_.flush();

    stats_.drawCalls = batch_.drawCalls() - stats_.buildDrawCalls;
    stats_.cellsCached = cells_.cached();
    stats_.cellBytes = cells_.bytes();
    stats_.overviewBytes = overview_->texture() != nullptr ? overview_->bytes() : 0;
    stats_.pages = pages_->stats();
    stats_.targetBytes = targetBytes();
}

void WorldView::updateRegion(const FRect& view, bool needed) {
    const TileRect need = gatherTiles(view, sprites_->itemSpan(), iso_);
    const auto grow = [&](float k) {
        const int gx = std::max(tuning::kRegionMinGrow,
                                static_cast<int>(static_cast<float>(need.x1 - need.x0) * k));
        const int gy = std::max(tuning::kRegionMinGrow,
                                static_cast<int>(static_cast<float>(need.y1 - need.y0) * k));
        return TileRect{need.x0 - gx, need.y0 - gy, need.x1 + gx, need.y1 + gy};
    };
    const FRect all{-1e9f, -1e9f, 1e9f, 1e9f};
    // A finished gather takes over when it covers the view (one overtaken by a jump is dropped).
    if (regionPending_ && prep_->take(kRegionTag, next_)) {
        regionPending_ = false;
        if (pendingRect_.contains(need)) {
            std::swap(region_, next_);
            regionRect_ = pendingRect_;
            stats_.regionRebuilt = true;
        }
    }
    if (needed && !regionRect_.intersects(need)) {
        // Nothing gathered here (a jump): gather now rather than show empty land.
        regionRect_ = grow(tuning::kRegionGrow);
        prep_->now(regionRect_, all, region_);
        stats_.regionRebuilt = true;
    } else if (!regionPending_ && !regionRect_.contains(grow(tuning::kRegionEarly))) {
        pendingRect_ = grow(tuning::kRegionGrow);
        prep_->request({kRegionTag, pendingRect_, all});
        regionPending_ = true;
        // Synchronous gathering finishes at once.
        if (!async_) updateRegion(view, needed);
    }
}

bool WorldView::settled() const {
    return stats_.cellsPending == 0 && stats_.pages.streaming == 0 && !regionPending_ &&
           building_.empty() && overview_->texture() != nullptr;
}

std::string WorldView::caption() const {
    const int r = theme_.captionRegion();
    if (r < 0 || theme_.captionAlpha() <= 0) return {};
    const world::RegionFile& f = world_.regions[static_cast<std::size_t>(r)];
    return f.caption;
}

} // namespace lc::worldview
