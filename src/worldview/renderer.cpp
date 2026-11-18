#include "worldview/renderer.hpp"

#include "core/rng.hpp"
#include "core/tuning.hpp"
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
    // Waters are one water for each other's edges (sea, shallows and rivers meet without a rim of
    // sand between them: art-world.md); beyond the grid the sea runs on.
    const bool water = m.terrainInfo(t).water;
    const auto same = [&](int dx, int dy) {
        const TilePos n{p.x + dx, p.y + dy};
        if (!m.inBounds(n)) return water;
        const int nt = m.terrainAt(n);
        return nt == t || (water && nt != world::kNone && m.terrainInfo(nt).water);
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

// The region of the tile under a world px point (on the ground plane), -1 off the grid.
int regionUnder(const world::WorldMap& m, Iso iso, Vec2 px) {
    const Vec2 t = iso.toTile(px);
    const TilePos p{static_cast<int>(std::floor(t.x)), static_cast<int>(std::floor(t.y))};
    return m.inBounds(p) ? m.regionAt(p) : -1;
}

} // namespace

Lod WorldView::lodFor(float scale) {
    if (scale >= 1.0f) return Lod::Native;
    if (scale >= 0.5f) return Lod::Half;
    if (scale >= 0.25f) return Lod::Quarter;
    return Lod::Overview;
}

WorldView::WorldView(SDL_Renderer* renderer, const world::LoadedWorld& world,
                     const std::filesystem::path& assets, Atlas& home, bool async, Hole hole,
                     const std::vector<world::FigurePlace>& figures)
    : renderer_(renderer), world_(world), map_(*world.map), iso_(map_.content().home().iso()),
      lvl_(map_.content().tileLevel()), async_(async), hole_(hole), homeAtlas_(home),
      cells_(renderer, tuning::kCellBudget), batch_(renderer), theme_([&] {
          std::vector<world::Theme> themes;
          for (const world::RegionFile& r : world.regions) themes.push_back(r.theme);
          return themes;
      }()),
      places_(
          [&] {
              std::vector<world::RegionKind> kinds;
              for (const world::RegionRef& r : world.file.regions) kinds.push_back(r.kind);
              return kinds;
          }(),
          [&] {
              std::vector<std::string> times;
              for (const world::RegionRef& r : world.file.regions) times.push_back(r.time);
              return times;
          }()) {
    pages_ = std::make_unique<PageAtlas>(renderer, home, world.atlas, assets / "atlas", async,
                                         tuning::kPageCeiling);
    sprites_ = std::make_unique<WorldSprites>(renderer, home, *pages_, map_);
    // Asynchronous runs build the overview on a worker from the start; synchronous ones only
    // when a frame needs it (it stands in for cells not built yet, which they never have).
    if (async) overview_ = std::make_unique<Overview>(map_, *sprites_, *pages_, async);
    for (std::size_t f = 0; f < figures.size(); ++f) {
        const world::FigurePlace& fp = figures[f];
        auto s = pages_->find(fp.sprite + "/idle_front/f0");
        if (!s) s = pages_->find(fp.sprite + "/idle/f0");
        if (!s) {
            ++figuresMissing_;
            continue;
        }
        const Vec2 w = iso_.toWorld(fp.at.x, fp.at.y);
        const TilePos t{static_cast<int>(std::floor(fp.at.x)),
                        static_cast<int>(std::floor(fp.at.y))};
        figures_.push_back(
            {*s,
             {std::round(w.x), std::round(w.y) - static_cast<float>(fp.level * lvl_)},
             t,
             fp.region});
        figureOf_.push_back(static_cast<std::uint32_t>(f));
    }
    prep_ = std::make_unique<Prep>(map_, *sprites_, async, hole_, figures_);
    buildGlow();
    blob_ = home.sprite(home.lightBlob());
    raindrop_ = home.find("fx/raindrop/f0");
    snowflake_ = home.find("fx/snowflake/f0");
    if (async) warmUp();
    for (std::size_t t = 0; t < map_.terrainCount(); ++t) {
        const world::TerrainInfo& info = map_.terrainInfo(static_cast<int>(t));
        if (info.water && (sea_ < 0 || info.id.find("sea") != std::string::npos))
            sea_ = static_cast<int>(t);
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
                const std::size_t k =
                    tileHash(p.x, p.y, 3u + static_cast<std::uint32_t>(b)) % v.size();
                // Faces are one tile edge wide and abut exactly (art-corrections.md). The lowest
                // level of a cliff standing in water carries the surf.
                const bool surf = b == level - ln - 1 && !mat->foot[s].empty() &&
                                  map_.inBounds(n) && map_.terrainAt(n) != world::kNone &&
                                  sprites_->terrain(map_.terrainAt(n)).water;
                if (surf) {
                    ok &=
                        put(mat->foot[s][k].at(now, mat->fps), at, x, kWhite, SDL_BLENDMODE_BLEND);
                    if (animated != nullptr) *animated = true;
                } else {
                    ok &= put(v[k], at, x, kWhite, SDL_BLENDMODE_BLEND);
                }
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
        const std::vector<SpriteRef>& base = look.baseIn(season_);
        if (base.empty())
            ok &=
                put(sprites_->diamond(), a, x,
                    times(overlay ? look.flatBase : look.flat, jitter * tint), SDL_BLENDMODE_BLEND);
        else
            ok &= put(base[tileHash(p.x, p.y, 1) % base.size()], a, x, shade, SDL_BLENDMODE_BLEND);
    }
    if (overlay) {
        if (look.hasOverlay()) {
            const Frames& f = look.overlayIn(sameMask(map_, p, t), season_);
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
            ok &= put(*mat->top[s], a, x, kWhite, SDL_BLENDMODE_BLEND);
    }
    return ok;
}

bool WorldView::drawTiles(const FRect& px, const Xform& x, float now, bool* animated) {
    const Reach& r = sprites_->groundReach();
    const TileRect tiles = tilesUnder(grown(px, r), iso_);
    if (tiles.empty()) return true;
    const float lift = r.up - static_cast<float>(kMaxLevel * lvl_);
    bool ok = true;
    diagonals(tiles, [&](TilePos p) {
        const Vec2 w = iso_.toWorld(p);
        if (!map_.inBounds(p)) {
            if (w.x + r.right >= px.x0 && w.x - r.left <= px.x1 && w.y + r.down >= px.y0 &&
                w.y - iso_.tileH() <= px.y1)
                ok &= drawBeyond(p, x, now);
            return;
        }
        // The game's scene draws the hole; its rim tiles are drawn here too, under the scene's,
        // so the soft edges of its tile art meet the world's ground, not the sky.
        const TileRect& h = hole_.tiles;
        if (h.contains(p) && p.x > h.x0 && p.y > h.y0 && p.x < h.x1 - 1 && p.y < h.y1 - 1) return;
        const float top = w.y - static_cast<float>(map_.level(p) * lvl_) - lift;
        if (w.x + r.right < px.x0 || w.x - r.left > px.x1 || w.y + r.down < px.y0 || top > px.y1)
            return;
        ok &= drawTile(p, x, now, animated);
    });
    return ok;
}

bool WorldView::drawBeyond(TilePos p, const Xform& x, float now) {
    const Vec2 a = iso_.toWorld(p);
    // Tiles beyond the edge, along the grid's axes (outside a corner, the larger of the two).
    const int dx = p.x < 0 ? -p.x : std::max(0, p.x - map_.width() + 1);
    const int dy = p.y < 0 ? -p.y : std::max(0, p.y - map_.height() + 1);
    const float k = std::min(1.0f, static_cast<float>(std::max(dx, dy)) / tuning::kHorizonTiles);
    bool ok = true;
    const float tint = 1.0f - tuning::kWaterDepthTint * 3.0f;
    if (sea_ >= 0) {
        const TerrainLook& look = sprites_->terrain(sea_);
        const std::vector<SpriteRef>& base = look.baseIn(season_);
        if (base.empty())
            ok &= put(sprites_->diamond(), a, x, times(look.flat, tint), SDL_BLENDMODE_BLEND);
        else
            ok &= put(base[tileHash(p.x, p.y, 1) % base.size()], a, x, {tint, tint, tint, 1},
                      SDL_BLENDMODE_BLEND);
    }
    const auto& h = tuning::kHorizonHaze;
    const float alpha = sea_ >= 0 ? k * tuning::kHorizonHazeMax : 1.0f;
    if (alpha > 0.0f)
        ok &= put(sprites_->diamond(), a, x, {h[0], h[1], h[2], alpha}, SDL_BLENDMODE_BLEND);
    (void)now;
    return ok;
}

bool WorldView::drawElem(const Elem& e, const Xform& x, float now) {
    if (e.home) return true; // the game's scene draws it
    if (e.figure) return put(figures_[e.item].sprite, e.anchor, x, kWhite, SDL_BLENDMODE_BLEND);
    if (e.ground) return drawTile(e.tile, x, now, nullptr);
    const VariantLook& look = *e.look;
    const SpriteRef& s =
        e.piece >= 0 ? look.pieces[static_cast<std::size_t>(e.piece)]
                     : look.baseIn(season_).at(now, sprites_->itemFps(map_.items()[e.item]));
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
    drawActorShadows(x);
    const bool any = !shadows_.empty() || !actorDraw_.empty();
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
        const int sa = a.from.level - a.key.level;
        const int sb = b.from.level - b.key.level;
        const int pa = cells_.slot(a.slot).page;
        const int pb = cells_.slot(b.slot).page;
        return pa != pb ? pa < pb : sa < sb;
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
    Overview& ov = overview();
    while (!ov.upload(renderer_) && !async_) {}
    SDL_Texture* t = ov.texture();
    if (t == nullptr) return;
    const OverviewImage& img = ov.image();
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

void WorldView::wantSets(const FRect& view, bool prefetch) {
    // The sets of the regions sampled over the view, grown by 64 tiles at the native level
    // (world-tech §4.5); impostors far out need only what they draw.
    const TileRect t = tilesUnder(view, iso_);
    const int g = prefetch ? tuning::kNeededSetGrow : 0;
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

std::optional<WorldView::Picked> WorldView::pick(Vec2 px) const {
    // Figures first: they are small and stand clear (world/figures.hpp), while a landmark's box
    // is much larger than what it draws.
    for (auto it = region_.order.rbegin(); it != region_.order.rend(); ++it) {
        const Elem& e = region_.elems[*it];
        const FRect& b = region_.items[*it].screen;
        if (e.figure && px.x >= b.x0 && px.x < b.x1 && px.y >= b.y0 && px.y < b.y1)
            return Picked{true, figureOf_[e.item]};
    }
    for (auto it = region_.order.rbegin(); it != region_.order.rend(); ++it) {
        const Elem& e = region_.elems[*it];
        const FRect& b = region_.items[*it].screen;
        if (e.ground || e.home || px.x < b.x0 || px.x >= b.x1 || px.y < b.y0 || px.y >= b.y1)
            continue;
        if (e.figure) return Picked{true, figureOf_[e.item]};
        if (!map_.info(map_.items()[e.item]).card.empty()) return Picked{false, e.item};
    }
    return std::nullopt;
}

void WorldView::drawWeatherGround(const FRect& view, const Xform& x) {
    // Cloud shadows: soft dark blobs drifting with the cells (showers darker); then the wet ground
    // where showers passed, darkened tile by tile. The home's own scene shades its land.
    const float blobR = blob_.w * 0.5f;
    for (const WeatherCell& c : weather_->cells()) {
        const Vec2 w = iso_.toWorld(c.centre.x, c.centre.y);
        const float rpx = c.radius * iso_.tileW() * 0.5f;
        if (w.x + rpx < view.x0 || w.x - rpx > view.x1 || w.y + rpx < view.y0 ||
            w.y - rpx > view.y1)
            continue;
        const float k = rpx / blobR;
        const float a = c.intensity() * (c.rain ? tuning::kShowerShadow : tuning::kCloudShadow);
        putSprite(batch_, blob_, w, x, {0, 0, 0, a}, SDL_BLENDMODE_BLEND, false, w, {k, k * 0.5f});
    }
    // Wet ground: darker along each shower's path over the last kWetMemory seconds.
    for (const WeatherTrail& t : weather_->trails()) {
        const Vec2 w = iso_.toWorld(t.at.x, t.at.y);
        const float rpx = t.radius * iso_.tileW() * 0.5f;
        if (w.x + rpx < view.x0 || w.x - rpx > view.x1 || w.y + rpx < view.y0 ||
            w.y - rpx > view.y1)
            continue;
        const float k = rpx / blobR;
        putSprite(batch_, blob_, w, x, {0, 0, 0.02f, t.wet * tuning::kWetDarken},
                  SDL_BLENDMODE_BLEND, false, w, {k, k * 0.5f});
    }
    batch_.flush();
}

void WorldView::drawRain(const FRect& view, const Xform& x, double now) {
    // Rain (or snow) falls where a shower is: streaks at stable places per tile, falling through
    // a tile's height over and over; nothing is stored, so any view of the world has its rain.
    const bool snow = weather_->snow();
    const std::optional<SpriteId>& id = snow ? snowflake_ : raindrop_;
    if (!id) return;
    const Sprite& s = homeAtlas_.sprite(*id);
    const TileRect tiles = tilesUnder(view, iso_).clipped(map_.bounds());
    const float fall = snow ? tuning::kSnowFall : tuning::kRainFall;
    const float drop = iso_.tileH() * 6.0f; // px a streak falls before it starts again
    for (int y = tiles.y0; y < tiles.y1; ++y)
        for (int tx = tiles.x0; tx < tiles.x1; ++tx) {
            const Vec2 c{static_cast<float>(tx) + 0.5f, static_cast<float>(y) + 0.5f};
            if (hole_.tiles.contains(TilePos{tx, y})) continue;
            const float r = weather_->rainAt(c);
            if (r < ::lc::tuning::kRainThreshold) continue;
            const Vec2 w = iso_.toWorld(c.x, c.y);
            for (int k = 0; k < tuning::kRainStreaksPerTile; ++k) {
                const std::uint32_t h = tileHash(tx, y, 31u + static_cast<std::uint32_t>(k));
                if (static_cast<float>(h % 1000) / 1000.0f > r) continue;
                const float ox = (static_cast<float>(h % 61) / 60.0f - 0.5f) * iso_.tileW();
                const float phase = static_cast<float>((h >> 8) % 1000) / 1000.0f;
                const float t = std::fmod(static_cast<float>(now) * fall / drop + phase, 1.0f);
                const Vec2 at{std::round(w.x + ox), std::round(w.y - drop * (1.0f - t))};
                if (at.y < view.y0 - 16 || at.y > view.y1 + 16) continue;
                putSprite(batch_, s, at, x, {1, 1, 1, snow ? 0.9f : 0.55f}, SDL_BLENDMODE_BLEND);
            }
        }
    batch_.flush();
}

void WorldView::buildGlow() {
    const auto chunks = static_cast<std::size_t>(map_.chunksX() * map_.chunksY());
    std::vector<std::uint32_t> count(chunks + 1, 0);
    const auto chunkOf = [&](const world::Placed& it) {
        return static_cast<std::size_t>((it.y >> kChunkShift) * map_.chunksX() +
                                        (it.x >> kChunkShift));
    };
    const auto glows = [&](const world::Placed& it) {
        return !hole_.tiles.contains(TilePos{it.x, it.y}) && sprites_->item(it).glow.has_value();
    };
    for (const world::Placed& it : map_.items())
        if (glows(it)) ++count[chunkOf(it) + 1];
    for (std::size_t c = 0; c < chunks; ++c) count[c + 1] += count[c];
    glowStart_ = count;
    glow_.resize(count[chunks]);
    for (const world::Placed& it : map_.items()) {
        if (!glows(it)) continue;
        const Vec2 w = iso_.toWorld(TilePos{it.x, it.y});
        glow_[count[chunkOf(it)]++] = {&*sprites_->item(it).glow,
                                       {w.x, w.y - static_cast<float>(it.level * lvl_)}};
    }
}

void WorldView::drawCoarseGlow(const FRect& view, const Xform& x, float strength) {
    const SDL_FColor g{strength, strength, strength, 1};
    const TileRect tiles = gatherTiles(view, sprites_->itemSpan(), iso_).clipped(map_.bounds());
    if (tiles.empty()) return;
    for (int cy = tiles.y0 >> kChunkShift; cy <= (tiles.y1 - 1) >> kChunkShift; ++cy)
        for (int cx = tiles.x0 >> kChunkShift; cx <= (tiles.x1 - 1) >> kChunkShift; ++cx) {
            const auto c = static_cast<std::size_t>(cy * map_.chunksX() + cx);
            for (std::uint32_t i = glowStart_[c]; i < glowStart_[c + 1]; ++i) {
                const GlowSource& s = glow_[i];
                const SpriteRef& r = *s.sprite;
                const FRect box{s.anchor.x - r.ox, s.anchor.y - r.oy, s.anchor.x - r.ox + r.w,
                                s.anchor.y - r.oy + r.h};
                if (box.overlaps(view)) (void)put(r, s.anchor, x, g, SDL_BLENDMODE_ADD);
            }
        }
    batch_.flush();
}

std::size_t WorldView::textureBudget() const {
    return pages_->stats().budget + cells_.budget() + targetBytes() +
           (overview_ ? overview_->bytes() : 0);
}

int WorldView::missingArt() const {
    int n = figuresMissing_;
    for (const MissingArt& m : sprites_->missingItems()) n += m.look == Look::Placeholder ? 1 : 0;
    n += static_cast<int>(sprites_->missingTerrain().size() + sprites_->flatMaterials().size());
    // Ids placed in the layers that no catalog defines are not drawn at all; they count too.
    n += static_cast<int>(map_.unresolved().size());
    return n;
}

void WorldView::placeholdersInView(std::vector<std::pair<Vec2, std::uint32_t>>& out) const {
    out.clear();
    for (std::size_t i = 0; i < region_.elems.size(); ++i) {
        const Elem& e = region_.elems[i];
        if (e.look != nullptr && e.first && e.look->look == Look::Placeholder &&
            region_.items[i].screen.overlaps(lastView_))
            out.emplace_back(e.anchor, map_.items()[e.item].info);
    }
}

void WorldView::visibleCards(std::vector<Picked>& out) const {
    out.clear();
    for (std::size_t i = 0; i < region_.elems.size(); ++i) {
        const Elem& e = region_.elems[i];
        if (e.ground || e.home || !region_.items[i].screen.overlaps(lastView_)) continue;
        if (e.figure) {
            out.push_back({true, figureOf_[e.item]});
        } else if (e.first && !map_.info(map_.items()[e.item]).card.empty()) {
            out.push_back({false, e.item});
        }
    }
}

void WorldView::setSeason(int season) {
    season = season >= 0 && season < kSeasonLooks ? season : -1;
    if (season == season_) return;
    season_ = season;
    // Ground and impostors hold the season's looks: draw them again.
    cells_.clear(); // impostors in flight finish into slots no longer theirs and are dropped
}

void WorldView::holeChanged() {
    const Vec2 a = iso_.toWorld(TilePos{hole_.tiles.x0, hole_.tiles.y1});
    const Vec2 b = iso_.toWorld(TilePos{hole_.tiles.x1, hole_.tiles.y0});
    const float top = iso_.toWorld(TilePos{hole_.tiles.x0, hole_.tiles.y0}).y;
    const float bottom = iso_.toWorld(TilePos{hole_.tiles.x1, hole_.tiles.y1}).y;
    const float raise = static_cast<float>(kMaxLevel * lvl_);
    const FRect r{a.x, top - raise, b.x, bottom + iso_.tileH()};
    for (int level = 0; level <= 2; ++level)
        forEachCell(r, level, [&](CellKey k) {
            const int si = cells_.find(packCell(k));
            if (si < 0) return;
            CellSlot& slot = cells_.slot(si);
            slot.complete = false;
            slot.generation = ~0u;
        });
}

void WorldView::jumped(const WorldCamera& camera) {
    jumped(camera.centre());
}

void WorldView::jumped(Vec2 centre) {
    std::array<world::RegionWeight, 16> w{};
    const int n = map_.themeWeights(iso_.toTile(centre), w);
    theme_.reset(std::span(w).first(static_cast<std::size_t>(n)));
    places_.reset(regionUnder(map_, iso_, centre));
    themed_ = true;
}

void WorldView::draw(const WorldCamera& camera, double clock, float dt, double now) {
    ViewSpec v{camera.centre(), camera.scale(),   camera.screen(),
               camera.flying(), camera.arrival(), camera.arrivalScale()};
    static const Hooks kNone;
    draw(v, clock, lightingAt(clock, 0), dt, now, kNone);
}

Overview& WorldView::overview() {
    if (!overview_) overview_ = std::make_unique<Overview>(map_, *sprites_, *pages_, async_);
    return *overview_;
}

void WorldView::draw(const ViewSpec& camera, double clock, const Lighting& light, float dt,
                     double now, const Hooks& hooks) {
    SDL_Texture* out = SDL_GetRenderTarget(renderer_);
    stats_ = {};
    batch_.resetStats();
    cells_.beginFrame();
    const float s = camera.scale;
    const Lod lod = lodFor(s);
    stats_.lod = lod;
    // At 2x and 3x the native level is drawn at the zoom's resolution: sprites stay whole art
    // pixels, while moving things are placed to the window's pixel.
    const float res = lod == Lod::Native    ? std::max(1.0f, std::floor(s + 1e-3f))
                      : lod == Lod::Half    ? 0.5f
                      : lod == Lod::Quarter ? 0.25f
                                            : std::min(overview().image().scale, s);
    const Vec2 screen = camera.screen;
    const Vec2 c = camera.centre;
    const Vec2 topLeft{c.x - screen.x * 0.5f / s, c.y - screen.y * 0.5f / s};
    // The target's origin sits on its own pixel grid, so cached cells land on whole texels.
    const float px = 1.0f / res;
    const Vec2 origin{std::floor(topLeft.x / px) * px - px, std::floor(topLeft.y / px) * px - px};
    res_ = res;
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
    const int here = regionUnder(map_, iso_, c);
    if (!themed_) {
        theme_.reset(ws);
        places_.reset(here);
        themed_ = true;
    } else {
        theme_.update(ws, dt);
        places_.update(here, dt);
    }
    const Grade grade = theme_.grade(clock);
    const SDL_FColor ambient{light.ambient.r * grade.mul.r, light.ambient.g * grade.mul.g,
                             light.ambient.b * grade.mul.b, 1};
    const FrameInfo frame{view_.texture.get(), xf, view, viewW_, viewH_, lod, ambient, s, topLeft};
    lastView_ = {topLeft.x, topLeft.y, topLeft.x + screen.x / s, topLeft.y + screen.y / s};

    // Streaming.
    if (lod != Lod::Overview) wantSets(view, lod == Lod::Native);
    // The cell cache holds what a frame needs at this window size, at least its stated budget.
    cells_.reserve(static_cast<std::size_t>(
        static_cast<double>(tuning::kCellBudget) *
        std::clamp(static_cast<double>(screen.x * screen.y) / tuning::kCellBudgetArea, 1.0,
                   tuning::kCellBudgetMaxScale)));
    pages_->update(now);
    if (overview_) {
        while (!overview_->upload(renderer_) && !async_) {}
    }

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
    batch_.flush();
    // The game's scene works only while its home is in view.
    const bool home = lod != Lod::Overview && !hole_.empty() && hole_.screen.overlaps(view);
    // The world's cloud shadows go under the home's ground: the home's scene shades its own land.
    if (weather_ != nullptr && lod != Lod::Overview) drawWeatherGround(view, xf);
    if (hooks.ground && home) hooks.ground(frame);
    // A flight down to the native level gathers its destination on the way.
    if (camera.flying && lodFor(camera.arrivalScale) == Lod::Native) {
        const Vec2 to = camera.arrival;
        const float k = 0.5f / camera.arrivalScale;
        updateRegion(
            {to.x - screen.x * k, to.y - screen.y * k, to.x + screen.x * k, to.y + screen.y * k},
            false);
    }
    bool homeDrawn = false;
    if (lod == Lod::Native) {
        if (!camera.flying) updateRegion(view, true);
        stats_.regionElements = static_cast<int>(region_.elems.size());
        prepareActors(view, lod);
        (void)drawShadows(region_, view, xf, shadow_, view_);
        for (std::size_t k = 0; k < region_.order.size(); ++k) {
            for (const std::uint32_t a : merge_.before(k)) drawActor(actorOf_[a], xf);
            const std::uint32_t i = region_.order[k];
            if (!region_.items[i].screen.overlaps(view)) {
                ++stats_.spritesCulled;
                continue;
            }
            const Elem& e = region_.elems[i];
            if (e.home) {
                batch_.flush();
                if (hooks.objects && home) hooks.objects(frame);
                homeDrawn = true;
                continue;
            }
            (void)drawElem(e, xf, static_cast<float>(now));
            ++stats_.spritesDrawn;
            if (e.look != nullptr && e.look->look == Look::Placeholder) ++stats_.placeholders;
        }
        for (const std::uint32_t a : merge_.before(region_.order.size()))
            drawActor(actorOf_[a], xf);
    } else if (lod != Lod::Overview) {
        // Coarser levels have no live objects of their own: people go over the impostors.
        prepareActors(view, lod);
        for (const std::uint32_t a : coarse_) drawActor(a, xf);
    } else {
        actorCount_ = 0;
        actorDraw_.clear();
    }
    batch_.flush();
    // The home's objects go over the impostors at the coarser levels.
    if (!homeDrawn && hooks.objects && home) hooks.objects(frame);
    if (weather_ != nullptr && (lod == Lod::Native || lod == Lod::Half)) drawRain(view, xf, now);
    // Grading, then what glows (drawn after it, additively).
    if (hooks.light && home)
        hooks.light(frame);
    else
        fullQuad(viewW_, viewH_, ambient, SDL_BLENDMODE_MOD);
    if (lod != Lod::Native && light.glow > 0.01f)
        drawCoarseGlow(view, xf,
                       light.glow * (lod == Lod::Overview ? tuning::kOverviewGlow : 1.0f));
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
    if (hooks.glow && home) hooks.glow(frame);

    // Onto the window: sky, the world, the haze.
    if (!SDL_SetRenderTarget(renderer_, out)) SDL_Log("worldview: %s", SDL_GetError());
    present_ = {origin, topLeft, s, res, light.skyTop, light.skyBottom, grade, screen, true};
    composite({1, 1}, false);
    if (hooks.overlay) hooks.overlay(frame);

    stats_.drawCalls = batch_.drawCalls() - stats_.buildDrawCalls;
    stats_.cellsCached = cells_.cached();
    stats_.cellBytes = cells_.bytes();
    stats_.overviewBytes = overview_ && overview_->texture() != nullptr ? overview_->bytes() : 0;
    stats_.pages = pages_->stats();
    stats_.targetBytes = targetBytes();
}

void WorldView::composite(Vec2 scale, bool smooth) {
    if (!present_.valid) return;
    const Present& p = present_;
    const float w = p.screen.x * scale.x;
    const float h = p.screen.y * scale.y;
    const SDL_FColor top{p.skyTop.r, p.skyTop.g, p.skyTop.b, 1};
    const SDL_FColor bottom{p.skyBottom.r, p.skyBottom.g, p.skyBottom.b, 1};
    const SDL_Vertex sky[4] = {{{0, 0}, top, {0, 0}},
                               {{w, 0}, top, {0, 0}},
                               {{w, h}, bottom, {0, 0}},
                               {{0, h}, bottom, {0, 0}}};
    static constexpr int kQuad[6] = {0, 1, 2, 0, 2, 3};
    batch_.use(nullptr, SDL_BLENDMODE_NONE);
    batch_.triangles(sky, 4, kQuad, 6);
    const float k = p.scale / p.res; // window px per target px
    // Nearest only when whole target pixels land on whole window pixels; a view between pixels
    // (a moving camera) is filtered, so it glides instead of stepping a pixel now and then.
    const float ox = (p.origin.x - p.topLeft.x) * p.scale;
    const float oy = (p.origin.y - p.topLeft.y) * p.scale;
    const bool whole = std::abs(k - std::round(k)) < 1e-3f &&
                       std::abs(ox - std::round(ox)) < 1e-2f &&
                       std::abs(oy - std::round(oy)) < 1e-2f;
    batch_.use(view_.texture.get(), SDL_BLENDMODE_BLEND_PREMULTIPLIED,
               whole && !smooth ? SDL_SCALEMODE_NEAREST : SDL_SCALEMODE_LINEAR);
    batch_.quad(SDL_FRect{(p.origin.x - p.topLeft.x) * p.scale * scale.x,
                          (p.origin.y - p.topLeft.y) * p.scale * scale.y,
                          static_cast<float>(viewW_) * k * scale.x,
                          static_cast<float>(viewH_) * k * scale.y},
                {0, 0, static_cast<float>(viewW_) / static_cast<float>(view_.w),
                 static_cast<float>(viewH_) / static_cast<float>(view_.h)},
                kWhite);
    if (p.grade.hazeStrength > 0.001f)
        fullQuad(static_cast<int>(w), static_cast<int>(h),
                 {p.grade.haze.r, p.grade.haze.g, p.grade.haze.b, p.grade.hazeStrength},
                 SDL_BLENDMODE_BLEND);
    batch_.flush();
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
            mergeIndexed_ = false;
        }
    }
    if (needed && !regionRect_.intersects(need)) {
        // Nothing gathered here (a jump): gather now rather than show empty land.
        regionRect_ = grow(tuning::kRegionGrow);
        prep_->now(regionRect_, all, region_);
        stats_.regionRebuilt = true;
        mergeIndexed_ = false;
    } else if (!regionPending_ && !regionRect_.contains(grow(tuning::kRegionEarly))) {
        pendingRect_ = grow(tuning::kRegionGrow);
        prep_->request({kRegionTag, pendingRect_, all});
        regionPending_ = true;
        // Synchronous gathering finishes at once.
        if (!async_) updateRegion(view, needed);
    }
}

void WorldView::setLife(const life::CityLife* city) {
    life_ = city;
    if (city != nullptr && !looks_)
        looks_ = std::make_unique<ActorLooks>(*pages_, city->lifeWorld().data, map_.content());
    actorBuf_.resize(tuning::kActorBuffer);
    actorCount_ = 0;
}

void WorldView::prepareActors(const FRect& view, Lod lod) {
    const Uint64 t0 = SDL_GetPerformanceCounter();
    prepareActorsTimed(view, lod);
    stats_.actorMs = static_cast<double>(SDL_GetPerformanceCounter() - t0) * 1000.0 /
                     static_cast<double>(SDL_GetPerformanceFrequency());
}

void WorldView::prepareActorsTimed(const FRect& view, Lod lod) {
    actorDraw_.clear();
    mergeActors_.clear();
    actorOf_.clear();
    coarse_.clear();
    actorCount_ = 0;
    if (lod == Lod::Native && !mergeIndexed_) {
        merge_.index(region_.items, region_.order, tuning::kActorMergeCell);
        mergeIndexed_ = true;
    }
    if (life_ == nullptr || !looks_) {
        if (lod == Lod::Native)
            merge_.plan(
                region_.items, {}, [](std::uint32_t, std::uint32_t) { return 0; },
                [](std::uint32_t) { return false; });
        return;
    }
    TileRect tiles = tilesUnder(view, iso_);
    const int m = tuning::kActorMargin;
    tiles =
        TileRect{tiles.x0 - m, tiles.y0 - m, tiles.x1 + m, tiles.y1 + m * 2}.clipped(map_.bounds());
    actorCount_ = life_->gather(tiles, lifeAlpha_, actorBuf_);
    const float px = 1.0f / res_;
    for (std::size_t i = 0; i < actorCount_; ++i) {
        const life::DrawActor& d = actorBuf_[i];
        ActorDraw ad;
        const TilePos t{static_cast<int>(std::floor(d.pos.x)),
                        static_cast<int>(std::floor(d.pos.y))};
        const auto look = hole_.tiles.contains(t) ? std::nullopt : looks_->resolve(d);
        if (look) {
            const Vec2 w = iso_.toWorld(d.pos.x, d.pos.y);
            // Whole pixels of the target, so sprites stay crisp.
            ad.anchor = {std::round(w.x / px) * px, std::round((w.y - d.z) / px) * px};
            ad.sprite = look->sprite;
            ad.mirror = look->mirror;
            const float a = d.alpha * (d.translucent ? tuning::kMemoryAlpha : 1.0f);
            ad.colour = {1, 1, 1, a};
            if (d.goods >= 0 && d.goodsCount > 0) {
                ad.goods = looks_->goods(d.goods, 0);
                ad.goodsAt = {ad.anchor.x + look->carry.x, ad.anchor.y + look->carry.y};
            }
            ad.depth = d.pos.x + d.pos.y;
        }
        actorDraw_.push_back(ad);
        if (ad.sprite == nullptr) continue;
        const SpriteRef& s = *ad.sprite;
        const float x0 = ad.anchor.x - (ad.mirror ? s.w - s.ox : s.ox);
        FRect box{x0, ad.anchor.y - s.oy, x0 + s.w, ad.anchor.y - s.oy + s.h};
        if (!box.overlaps(view)) continue;
        if (ad.goods != nullptr) box.y0 = std::min(box.y0, ad.goodsAt.y - ad.goods->oy);
        if (lod != Lod::Native) {
            // Under a roof or a colonnade there is nothing to see from this far.
            if (d.item < 0 || d.floor) coarse_.push_back(static_cast<std::uint32_t>(i));
            continue;
        }
        const float f = tuning::kActorFoot;
        mergeActors_.push_back(
            {FRect{d.pos.x - f, d.pos.y - f, d.pos.x + f, d.pos.y + f}, box, s.page});
        actorOf_.push_back(static_cast<std::uint32_t>(i));
    }
    if (lod != Lod::Native) {
        std::ranges::sort(coarse_, {}, [&](std::uint32_t i) { return actorDraw_[i].depth; });
        return;
    }
    merge_.plan(
        region_.items, mergeActors_,
        [&](std::uint32_t e, std::uint32_t a) {
            const Elem& el = region_.elems[e];
            const life::DrawActor& d = actorBuf_[actorOf_[a]];
            const FRect& foot = region_.items[e].foot;
            const bool on =
                d.pos.x >= foot.x0 && d.pos.x < foot.x1 && d.pos.y >= foot.y0 && d.pos.y < foot.y1;
            // The raised tile someone stands on is under them.
            if (el.ground) return on ? -1 : 0;
            if (el.home || el.figure || d.item < 0 || el.item != static_cast<std::uint32_t>(d.item))
                return 0;
            // On an item's walk tile: its floor (and an unsplit deck) is under the feet; a
            // landmark piece over the tile (a roof, a lintel, a gateway) is over the head.
            if (el.floor || el.piece < 0) return -1;
            return on ? 1 : 0;
        },
        [&](std::uint32_t e) { return region_.items[e].screen.overlaps(view); });
}

void WorldView::actorsAt(Vec2 px, std::vector<life::Handle>& out) const {
    out.clear();
    std::vector<std::pair<float, life::Handle>> hits; // a click, not a frame: allocation is fine
    for (std::size_t i = 0; i < actorDraw_.size(); ++i) {
        const ActorDraw& a = actorDraw_[i];
        if (a.sprite == nullptr) continue;
        const SpriteRef& s = *a.sprite;
        const float x0 = a.anchor.x - (a.mirror ? s.w - s.ox : s.ox);
        // A little narrower than the sprite: what is clicked is the person, not the air beside.
        const float inset = s.w * 0.2f;
        if (px.x < x0 + inset || px.x >= x0 + s.w - inset || px.y < a.anchor.y - s.oy ||
            px.y >= a.anchor.y - s.oy + s.h)
            continue;
        hits.emplace_back(-a.depth, actorBuf_[i].handle);
    }
    std::ranges::sort(hits, {}, &std::pair<float, life::Handle>::first);
    for (const auto& h : hits) out.push_back(h.second);
}

void WorldView::drawActor(std::uint32_t i, const Xform& x) {
    const ActorDraw& a = actorDraw_[i];
    if (put(*a.sprite, a.anchor, x, a.colour, SDL_BLENDMODE_BLEND, a.mirror)) ++stats_.actorsDrawn;
    if (a.goods != nullptr) (void)put(*a.goods, a.goodsAt, x, a.colour, SDL_BLENDMODE_BLEND);
}

void WorldView::drawActorShadows(const Xform& x) {
    // Soft ovals under the feet in the shared shadow layer: they merge with the buildings'.
    const float rx = tuning::kActorShadowW * iso_.tileW() * 0.5f / (blob_.w * 0.5f);
    for (const std::uint32_t i : actorOf_) {
        const ActorDraw& a = actorDraw_[i];
        const SDL_FColor c{0, 0, 0, tuning::kActorShadow * a.colour.a};
        putSprite(batch_, blob_, a.anchor, x, c, SDL_BLENDMODE_BLEND, false, a.anchor,
                  {rx, rx * 0.5f});
    }
}

bool WorldView::settled() const {
    return stats_.cellsPending == 0 && stats_.pages.streaming == 0 && !regionPending_ &&
           building_.empty() && (!overview_ || overview_->texture() != nullptr);
}

std::string WorldView::caption() const {
    const int r = places_.caption();
    if (r < 0 || places_.captionAlpha() <= 0) return {};
    const world::RegionFile& f = world_.regions[static_cast<std::size_t>(r)];
    return f.caption;
}

} // namespace lc::worldview
