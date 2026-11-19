// The world renderer's ground (out/reports/art-smooth-land.md §3–§4): faces chosen by the
// corners of the two tiles at each front edge, slopes drawn from their art (or the flat look
// carried onto the mesh), water stepping down as falls, rapids and plunge pools, and the slow
// lightness field over land.

#include "core/rng.hpp"
#include "render/gpu/post.hpp"
#include "worldview/renderer.hpp"
#include "worldview/terrain.hpp"
#include "worldview/tuning.hpp"

#include <algorithm>
#include <cmath>
#include <initializer_list>

namespace lc::worldview {
namespace {

constexpr SDL_FColor kWhite{1, 1, 1, 1};

SDL_FColor grey(float k) {
    return {k, k, k, 1};
}

SDL_FColor times(SDL_FColor c, float k) {
    return {c.r * k, c.g * k, c.b * k, c.a};
}

// The two corners of tile p on its +x (side 0) or +y (side 1) edge, as (S, far end), and the
// neighbour's corners at the same two points.
constexpr std::array<std::array<int, 4>, 2> kEdgeCorners{{{2, 1, 3, 0}, {2, 3, 1, 0}}};


} // namespace

void WorldView::setSlopeSun(const float dir[3], float strength) {
    slopeSun_ = {dir[0], dir[1], dir[2], strength};
    slopeLights_.clear(); // worked out again by the next mesh drawn
}

float WorldView::macroAt(Vec2 tile) const {
    // Fades out toward the home, whose own scene draws its ground without the field: no step at
    // the border.
    const TileRect& h = hole_.tiles;
    const float dx =
        std::max({static_cast<float>(h.x0) - tile.x, 0.0f, tile.x - static_cast<float>(h.x1)});
    const float dy =
        std::max({static_cast<float>(h.y0) - tile.y, 0.0f, tile.y - static_cast<float>(h.y1)});
    const float fade = h.empty() ? 1.0f : std::clamp(std::max(dx, dy) / 6.0f, 0.0f, 1.0f);
    return 1.0f - tuning::kGroundMacroDepth * fade * groundMacro(tile);
}

bool WorldView::putTris(const SpriteRef& s, std::span<SDL_Vertex> v, std::span<const int> idx,
                        const Xform& x, SDL_BlendMode mode) {
    if (dry_) return true; // (a pass that only asks the tiles something)
    SDL_Texture* t = pages_->texture(s.page);
    if (t == nullptr) return false;
    const bool packed =
        decoder_ && s.packed && (s.page != PageAtlas::kHomePage || pages_->homePackedReady());
    if (packed) {
        if (mode == SDL_BLENDMODE_BLEND) mode = decoder_->replace();
        for (SDL_Vertex& p : v)
            p.color = packedColour(p.color, s.page == PageAtlas::kHomePage, false);
    }
    for (SDL_Vertex& p : v) {
        const Vec2 w = x.apply({p.position.x, p.position.y});
        p.position = {w.x, w.y};
    }
    if (!runsOpen_) {
        if (decoder_) decoder_->use(batch_, packed);
        batch_.use(t, mode, x.filter);
        batch_.triangles(v.data(), static_cast<int>(v.size()), idx.data(),
                         static_cast<int>(idx.size()));
        return true;
    }
    // In the live layer, kept with its page's run as put() keeps a sprite: a quad (four corners,
    // two triangles) as one polygon, any other triangle as one of its own.
    const std::uint32_t key =
        (s.page * 2U + (packed ? 1U : 0U)) ^ (static_cast<std::uint32_t>(mode) * 2654435761U);
    const auto keep = [&](std::initializer_list<SDL_Vertex> corners) {
        RunPoly poly;
        FRect box{1e9f, 1e9f, -1e9f, -1e9f};
        for (const SDL_Vertex& p : corners) {
            poly.v[static_cast<std::size_t>(poly.n++)] = p;
            box = {std::min(box.x0, p.position.x), std::min(box.y0, p.position.y),
                   std::max(box.x1, p.position.x), std::max(box.y1, p.position.y)};
        }
        if (!runs_.add(key, box)) return;
        runQuads_.push_back({t,
                             mode,
                             {box.x0, box.y0},
                             {box.x1, box.y1},
                             s.uv,
                             poly.v[0].color,
                             s.page,
                             runWhat_,
                             packed,
                             static_cast<std::int32_t>(runPolys_.size())});
        runPolys_.push_back(poly);
    };
    static constexpr std::array<int, 6> kQuad{0, 1, 2, 0, 2, 3};
    if (v.size() == 4 && std::ranges::equal(idx, kQuad)) {
        keep({v[0], v[1], v[2], v[3]});
        return true;
    }
    for (std::size_t i = 0; i + 2 < idx.size(); i += 3)
        keep({v[static_cast<std::size_t>(idx[i])], v[static_cast<std::size_t>(idx[i + 1])],
              v[static_cast<std::size_t>(idx[i + 2])]});
    return true;
}

float WorldView::depthAt(Vec2 tile) const {
    const float fx = tile.x - 0.5f;
    const float fy = tile.y - 0.5f;
    const int x0 = static_cast<int>(std::floor(fx));
    const int y0 = static_cast<int>(std::floor(fy));
    const float tx = fx - static_cast<float>(x0);
    const float ty = fy - static_cast<float>(y0);
    const auto at = [&](int x, int y) {
        const TilePos q{x, y};
        if (!map_.inBounds(q)) return 3.0f;
        const int t = map_.terrainAt(q);
        if (t == world::kNone || !map_.terrainInfo(t).water ||
            waterKinds_.channel[static_cast<std::size_t>(t)])
            return 0.0f;
        return static_cast<float>(world::auxOf(map_.levelByte(q)));
    };
    const float top = at(x0, y0) + (at(x0 + 1, y0) - at(x0, y0)) * tx;
    const float bottom = at(x0, y0 + 1) + (at(x0 + 1, y0 + 1) - at(x0, y0 + 1)) * tx;
    return top + (bottom - top) * ty;
}

bool WorldView::drawGround(const TileCtx& c, const SpriteRef& s, Vec2 anchor, const Xform& x,
                           float k) {
    if (!c.macro && !c.depth) return put(s, anchor, x, grey(k), SDL_BLENDMODE_BLEND);
    // The sprite's quad with the slow field at its corners (sampled on the tile's ground plane).
    const float x0 = anchor.x - s.ox;
    const float y0 = anchor.y - s.oy;
    const float raise = static_cast<float>(c.level * lvl_);
    const std::array<Vec2, 4> corner{
        {{x0, y0}, {x0 + s.w, y0}, {x0 + s.w, y0 + s.h}, {x0, y0 + s.h}}};
    const std::array<SDL_FPoint, 4> uv{
        {{s.uv.u0, s.uv.v0}, {s.uv.u1, s.uv.v0}, {s.uv.u1, s.uv.v1}, {s.uv.u0, s.uv.v1}}};
    std::array<SDL_Vertex, 4> v{};
    for (std::size_t i = 0; i < 4; ++i) {
        const Vec2 at = iso_.toTile({corner[i].x, corner[i].y + raise});
        const float m =
            c.depth ? 1.0f - tuning::kWaterDepthTint * depthAt(at) : k * macroAt(at);
        v[i] = {{corner[i].x, corner[i].y}, {m, m, m, 1}, uv[i]};
    }
    static constexpr std::array<int, 6> kQuad{0, 1, 2, 0, 2, 3};
    return putTris(s, v, kQuad, x, SDL_BLENDMODE_BLEND);
}

bool WorldView::putWarped(const TileCtx& c, const SpriteRef& s, const Xform& x, float k,
                          SDL_BlendMode mode) {
    if (slopeLights_.empty()) {
        slopeLights_.resize(world::kSlopeCount);
        for (int sh = 0; sh < world::kSlopeCount; ++sh)
            slopeLights_[static_cast<std::size_t>(sh)] =
                slopeLight(world::Slope(sh), static_cast<float>(lvl_) / iso_.hw, slopeSun_.data(),
                           slopeSun_[3]);
    }
    const world::SlopeGrid& h = world::slopeGrid(c.slope);
    const std::array<float, 8>& light = slopeLights_[static_cast<std::size_t>(c.slope)];
    // A mesh point: its place in the flat sprite (px from the sprite's corner) and in the world.
    struct P {
        float sx, sy;
        float wx, wy;
    };
    std::array<P, 9> grid{};
    for (std::size_t g = 0; g < 9; ++g) {
        const float u = static_cast<float>(g % 3) * 0.5f;
        const float vv = static_cast<float>(g / 3) * 0.5f;
        const float dx = (u - vv) * iso_.hw;
        const float dy = (u + vv) * iso_.hh;
        grid[g] = {s.ox + dx, s.oy + dy, c.a.x + dx, c.a.y + dy - h[g] * static_cast<float>(lvl_)};
    }
    triVerts_.clear();
    triIdx_.clear();
    const float du = (s.uv.u1 - s.uv.u0) / s.w;
    const float dv = (s.uv.v1 - s.uv.v0) / s.h;
    const float raise = static_cast<float>(c.level * lvl_);
    for (std::size_t t = 0; t < 8; ++t) {
        // Each triangle clipped to the sprite's rect in its own pixels (a trimmed sprite must not
        // reach into its neighbours on the page); the map to the world is affine per triangle.
        std::array<P, 8> a{};
        std::array<P, 8> b{};
        int n = 3;
        for (std::size_t k3 = 0; k3 < 3; ++k3)
            a[k3] = grid[static_cast<std::size_t>(world::kSlopeFan[t][k3])];
        const auto clip = [&](auto inside, auto cross) {
            int m = 0;
            for (int i = 0; i < n; ++i) {
                const P& p = a[static_cast<std::size_t>(i)];
                const P& q = a[static_cast<std::size_t>((i + 1) % n)];
                const bool pi = inside(p);
                if (pi) b[static_cast<std::size_t>(m++)] = p;
                if (pi != inside(q)) {
                    const float f = cross(p, q);
                    b[static_cast<std::size_t>(m++)] = {
                        p.sx + (q.sx - p.sx) * f, p.sy + (q.sy - p.sy) * f,
                        p.wx + (q.wx - p.wx) * f, p.wy + (q.wy - p.wy) * f};
                }
            }
            n = m;
            a = b;
        };
        const float w = s.w;
        const float hh = s.h;
        clip([](const P& p) { return p.sx >= 0; },
             [](const P& p, const P& q) { return p.sx / (p.sx - q.sx); });
        clip([w](const P& p) { return p.sx <= w; },
             [w](const P& p, const P& q) { return (w - p.sx) / (q.sx - p.sx); });
        clip([](const P& p) { return p.sy >= 0; },
             [](const P& p, const P& q) { return p.sy / (p.sy - q.sy); });
        clip([hh](const P& p) { return p.sy <= hh; },
             [hh](const P& p, const P& q) { return (hh - p.sy) / (q.sy - p.sy); });
        if (n < 3) continue;
        const auto base = static_cast<int>(triVerts_.size());
        const float lit = std::min(1.0f, k * light[t]);
        for (int i = 0; i < n; ++i) {
            const P& p = a[static_cast<std::size_t>(i)];
            const float m = c.macro ? lit * macroAt(iso_.toTile({p.wx, p.wy + raise})) : lit;
            triVerts_.push_back(
                {{p.wx, p.wy}, {m, m, m, 1}, {s.uv.u0 + p.sx * du, s.uv.v0 + p.sy * dv}});
        }
        for (int i = 1; i + 1 < n; ++i) {
            triIdx_.push_back(base);
            triIdx_.push_back(base + i);
            triIdx_.push_back(base + i + 1);
        }
    }
    if (triIdx_.empty()) return true;
    return putTris(s, triVerts_, triIdx_, x, mode);
}

bool WorldView::drawSlope(const TileCtx& c, const Xform& x, float now, bool* animated) {
    const TerrainLook& look = *c.look;
    const auto k = static_cast<std::size_t>(c.slope);
    const std::uint32_t pick = tileHash(c.p.x, c.p.y, 1);
    // Slope sprites are anchored at the top vertex of the tile one level down (their foot).
    const Vec2 foot{c.a.x, c.a.y + static_cast<float>(lvl_)};
    const bool overlay = !map_.terrainInfo(c.t).base;
    const int mask = overlay ? overlayMask(map_, c.p, c.t) : 15;
    const std::vector<SpriteRef>& own = look.slope[k];
    if (mask == 15 && !own.empty()) return drawGround(c, own[pick % own.size()], foot, x, 1);
    bool ok = true;
    // The base's slope (or its flat look on the mesh), then an overlay's flat look on the mesh.
    const std::vector<SpriteRef>& under = look.slopeBase[k];
    if (!under.empty()) {
        ok &= drawGround(c, under[pick % under.size()], foot, x, 1);
    } else {
        const std::vector<SpriteRef>& base = look.baseIn(lookSeason_);
        ok &= base.empty() ? putWarped(c, sprites_->diamond(), x, 1, SDL_BLENDMODE_BLEND)
                           : putWarped(c, base[pick % base.size()], x, 1, SDL_BLENDMODE_BLEND);
    }
    if (overlay && look.hasOverlay()) {
        const Frames& f = mask == 15 && !look.interior.empty()
                              ? look.interior[tileHash(c.p.x, c.p.y, 11) % look.interior.size()]
                              : look.overlayIn(mask, lookSeason_);
        ok &= putWarped(c, f.at(now, look.fps), x, 1, SDL_BLENDMODE_BLEND);
        if (look.animated() && animated != nullptr) *animated = true;
    }
    return ok;
}

bool WorldView::drawFaces(const TileCtx& c, const MaterialLook* mat, const Xform& x, float now,
                          bool* animated, std::array<int, 2>& cap, int skip) {
    bool ok = true;
    const TileCtx& t = c;
    for (int side = 0; side < 2; ++side) {
        if ((skip & (1 << side)) != 0) continue;
        const auto s = static_cast<std::size_t>(side);
        const TilePos n = side == 0 ? TilePos{t.p.x + 1, t.p.y} : TilePos{t.p.x, t.p.y + 1};
        const auto& ec = kEdgeCorners[s];
        const EdgeFace f =
            edgeFace(t.level, map_.cornerLevel(t.p, ec[0]), map_.cornerLevel(t.p, ec[1]),
                     map_.cornerLevel(n, ec[2]), map_.cornerLevel(n, ec[3]));
        if (f.empty()) continue;
        const bool art = mat != nullptr && !mat->band[s].empty();
        if (f.wedge >= 0) {
            // A wedge under the slope's falling edge; without wedge art a whole band, whose part
            // above the edge the slope covers.
            const auto& w =
                art ? mat->wedge[s][static_cast<std::size_t>(f.wedge)] : std::vector<SpriteRef>{};
            const std::uint32_t h = tileHash(t.p.x, t.p.y, 3u);
            if (!w.empty())
                ok &= put(w[h % w.size()], t.a, x, kWhite, SDL_BLENDMODE_BLEND);
            else if (art)
                ok &=
                    put(mat->band[s][h % mat->band[s].size()], t.a, x, kWhite, SDL_BLENDMODE_BLEND);
            else
                ok &= put(sprites_->face(side), t.a, x,
                          times(mat != nullptr ? mat->flat : t.look->flat,
                                side == 0 ? tuning::kFaceShadeSE : tuning::kFaceShadeSW),
                          SDL_BLENDMODE_BLEND);
        }
        if (f.capped() && art && mat->top[s]) cap[s] = f.first;
        const bool water = map_.inBounds(n) && map_.terrainAt(n) != world::kNone &&
                           sprites_->terrain(map_.terrainAt(n)).water;
        for (int b = f.first; b < f.last; ++b) {
            const Vec2 at{t.a.x, t.a.y + static_cast<float>(b * lvl_)};
            if (art) {
                if (b == cap[s]) continue;
                const auto& v = mat->band[s];
                const std::size_t k =
                    tileHash(t.p.x, t.p.y, 3u + static_cast<std::uint32_t>(b)) % v.size();
                // Faces are one tile edge wide and abut exactly (art-corrections.md). The lowest
                // level of a cliff standing in water carries the surf.
                if (b == f.last - 1 && water && !mat->foot[s].empty()) {
                    ok &=
                        put(mat->foot[s][k].at(now, mat->fps), at, x, kWhite, SDL_BLENDMODE_BLEND);
                    if (animated != nullptr) *animated = true;
                } else {
                    ok &= put(v[k], at, x, kWhite, SDL_BLENDMODE_BLEND);
                }
            } else {
                const SDL_FColor col =
                    times(mat != nullptr ? mat->flat : t.look->flat,
                          side == 0 ? tuning::kFaceShadeSE : tuning::kFaceShadeSW);
                ok &= put(sprites_->face(side), at, x, col, SDL_BLENDMODE_BLEND);
            }
        }
    }
    return ok;
}

int WorldView::fallDrop(TilePos p, int dir) const {
    return worldview::fallDrop(map_, waterKinds_, p, dir);
}

bool WorldView::drawFallFaces(const TileCtx& c, const Xform& x, float now, bool* animated,
                              bool after) {
    if (c.level == 0) return true;
    const FallLook& fl = sprites_->falls();
    bool ok = true;
    for (int side = 0; side < 2; ++side) {
        const int drop = fallDrop(c.p, side);
        if (drop == 0) continue;
        // Where the falling water goes on along the edge (`e<bits>`): past the bottom vertex,
        // past the far end; elsewhere the sheet pulls in from the bank.
        const TilePos s0 = side == 0 ? TilePos{c.p.x, c.p.y + 1} : TilePos{c.p.x + 1, c.p.y};
        const TilePos s1 = side == 0 ? TilePos{c.p.x, c.p.y - 1} : TilePos{c.p.x - 1, c.p.y};
        const auto goesOn = [&](TilePos q) {
            return map_.inBounds(q) && map_.terrainAt(q) != world::kNone &&
                   sprites_->terrain(map_.terrainAt(q)).water && map_.level(q) == c.level &&
                   fallDrop(q, side) > 0;
        };
        const std::size_t ends = (goesOn(s0) ? 1u : 0u) | (goesOn(s1) ? 2u : 0u);
        for (int b = 0; b < drop; ++b) {
            const FallPart part = fallPart(drop, b);
            // The lip and a one-level cascade lie over the upper tile's edge: after its ground.
            if ((part == FallPart::Top || part == FallPart::Rapid) != after) continue;
            const Frames& f =
                fl.part[static_cast<std::size_t>(side)][static_cast<std::size_t>(part)][ends];
            ok &= put(f.at(now, fl.fps), {c.a.x, c.a.y + static_cast<float>(b * lvl_)}, x, kWhite,
                      SDL_BLENDMODE_BLEND);
            if (animated != nullptr) *animated = true;
        }
    }
    if (!after) return ok;
    // White water speeding toward every edge it falls over (`n` toward -y, `e` toward +x).
    for (int dir = 0; dir < 4; ++dir) {
        if (fallDrop(c.p, dir) == 0) continue;
        const Frames& f = fl.rapids[dir == 0 || dir == 1 ? 1 : 0];
        if (f.empty()) continue;
        ok &= put(f.at(now, fl.fps), c.a, x, kWhite, SDL_BLENDMODE_BLEND, dir == 1 || dir == 2);
        if (animated != nullptr) *animated = true;
    }
    return ok;
}

bool WorldView::drawPlunge(const TileCtx& c, const Xform& x, float now, bool* animated) {
    // The edges with higher water beyond them that falls onto this tile: N 1, E 2, S 4, W 8.
    static constexpr std::array<std::pair<TilePos, int>, 4> kFrom{
        {{{0, -1}, 1}, {{1, 0}, 2}, {{0, 1}, 3}, {{-1, 0}, 0}}};
    int mask = 0;
    for (std::size_t i = 0; i < 4; ++i) {
        const TilePos q{c.p.x + kFrom[i].first.x, c.p.y + kFrom[i].first.y};
        if (!map_.inBounds(q) || map_.level(q) <= c.level) continue;
        const int qt = map_.terrainAt(q);
        if (qt != world::kNone && sprites_->terrain(qt).water && fallDrop(q, kFrom[i].second) > 0)
            mask |= 1 << i;
    }
    if (mask == 0) return true;
    const Frames& f = sprites_->falls().plunge[static_cast<std::size_t>(mask)];
    if (f.empty()) return true;
    if (animated != nullptr) *animated = true;
    return put(f.at(now, sprites_->falls().fps), c.a, x, kWhite, SDL_BLENDMODE_BLEND);
}

} // namespace lc::worldview
