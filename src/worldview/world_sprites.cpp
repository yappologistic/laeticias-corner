#include "worldview/world_sprites.hpp"

#include "core/rng.hpp"
#include "worldview/tuning.hpp"

#include <algorithm>
#include <cmath>
#include <format>
#include <map>
#include <ranges>
#include <set>

namespace lc::worldview {
namespace {

constexpr int kPagePad = 2;

SDL_FColor rgb(int r, int g, int b) {
    return {static_cast<float>(r) / 255.0f, static_cast<float>(g) / 255.0f,
            static_cast<float>(b) / 255.0f, 1};
}

// Faces of the shared materials until the world set's edge art exists (the world builders'
// preview uses the same colours).
SDL_FColor materialColour(const std::string& id) {
    static const std::map<std::string, SDL_FColor, std::less<>> kKnown{
        {"world.coast", rgb(168, 146, 112)},
        {"world.rock", rgb(132, 124, 116)},
        {"world.earth", rgb(140, 108, 76)},
        {"world.snow", rgb(226, 230, 238)}};
    const auto it = kKnown.find(id);
    return it != kKnown.end() ? it->second : rgb(140, 118, 90);
}

SDL_FColor terrainColour(const world::TerrainInfo& t) {
    if (t.colour) return rgb((*t.colour)[0], (*t.colour)[1], (*t.colour)[2]);
    if (t.known) return rgb(150, 140, 110);
    // Unknown ids: a stable colour per id, so each reads as its own patch.
    const auto h = static_cast<std::uint32_t>(std::hash<std::string>{}(t.id));
    return rgb(80 + static_cast<int>(h % 120), 80 + static_cast<int>((h >> 8) % 120),
               80 + static_cast<int>((h >> 16) % 120));
}

// Surf on the lowest face of a sea cliff moves at the sea's pace (the art report's timing).
constexpr float kFaceSurfFps = 4.0f;

// Placeholder colours by what the item is (the preview's categories).
SDL_FColor categoryColour(const world::ItemInfo& d, Footprint fp) {
    if (d.landmark) return rgb(196, 112, 86);
    if (d.rise > 0) return rgb(190, 170, 140);
    if (d.on == Surface::Water || d.crossing) return rgb(120, 150, 170);
    if (d.layout == Layout::Connect) return rgb(168, 160, 150);
    if (fp.w * fp.h == 1 && d.layout == Layout::Variant) return rgb(110, 156, 92);
    if (fp.w * fp.h >= 4 && d.height >= 40) return rgb(214, 176, 112);
    return rgb(176, 172, 166);
}

Frames frames(const PageAtlas& pages, const std::string& prefix) {
    Frames out;
    for (int f = 0;; ++f) {
        const auto s = pages.find(std::format("{}/f{}", prefix, f));
        if (!s) break;
        out.f.push_back(*s);
    }
    return out;
}

std::vector<SpriteRef> variants(const PageAtlas& pages, const std::string& prefix) {
    std::vector<SpriteRef> out;
    for (int v = 0;; ++v) {
        const auto s = pages.find(std::format("{}/v{}", prefix, v));
        if (!s) break;
        out.push_back(*s);
    }
    return out;
}

// The season's look of `n` numbered sprites `<prefix><sep><k>` (`<key>@<season>`, falling back
// to the plain sprite one by one); empty when none of them has a seasonal look.
std::vector<SpriteRef> seasonal(const PageAtlas& pages, const std::string& prefix,
                                std::string_view sep, const std::string& at, std::size_t n) {
    std::vector<SpriteRef> out;
    bool any = false;
    for (std::size_t k = 0; k < n; ++k) {
        const std::string key = std::format("{}{}{}", prefix, sep, k);
        if (auto s = pages.find(key + at)) {
            out.push_back(*s);
            any = true;
        } else if (auto plain = pages.find(key)) {
            out.push_back(*plain);
        }
    }
    if (!any) out.clear();
    return out;
}

// How far a sprite reaches beyond the screen diamond of its footprint `f` (tiles relative to the
// anchor's tile): gathering finds an item from the tiles its sprite can cover.
void span(Reach& r, const SpriteRef& s, TileRect f, Iso iso) {
    r.left = std::max(r.left, static_cast<float>(f.x0 - f.y1) * iso.hw + s.ox);
    r.right = std::max(r.right, (s.w - s.ox) - static_cast<float>(f.x1 - f.y0) * iso.hw);
    r.up = std::max(r.up, static_cast<float>(f.x0 + f.y0) * iso.hh + s.oy);
    r.down = std::max(r.down, (s.h - s.oy) - static_cast<float>(f.x1 + f.y1) * iso.hh);
}

void reach(Reach& r, const SpriteRef& s) {
    r.left = std::max(r.left, s.ox);
    r.right = std::max(r.right, s.w - s.ox);
    r.up = std::max(r.up, s.oy);
    r.down = std::max(r.down, s.h - s.oy);
}

// The ground raster (CLAUDE.md "Projection"), anchor-relative: rows 2, 6, ... wide, mirrored.
bool inDiamond(int x, int y, int hw, int hh) {
    if (y < 0 || y >= 2 * hh || x < -hw + 1 || x >= hw - 1) return false;
    const int r = y < hh ? y : 2 * hh - 1 - y;
    return x >= -(2 * r + 1) && x < 2 * r + 1;
}

int diamondBottom(int x, int hw, int hh) {
    for (int y = 2 * hh - 1; y >= 0; --y)
        if (inDiamond(x, y, hw, hh)) return y;
    return -1;
}

void putWhite(SDL_Surface* s, int x, int y) {
    auto* row = reinterpret_cast<std::uint32_t*>(static_cast<std::uint8_t*>(s->pixels) +
                                                 static_cast<std::ptrdiff_t>(y) * s->pitch);
    row[x] = 0xFFFFFFFFu;
}

// A one-pixel line as a thin quad.
void line(Batch& b, Vec2 a, Vec2 c, SDL_FColor col) {
    const float dx = c.x - a.x;
    const float dy = c.y - a.y;
    const float len = std::max(1e-3f, std::hypot(dx, dy));
    const float nx = -dy / len * 0.5f;
    const float ny = dx / len * 0.5f;
    const SDL_FPoint p[4] = {
        {a.x + nx, a.y + ny}, {c.x + nx, c.y + ny}, {c.x - nx, c.y - ny}, {a.x - nx, a.y - ny}};
    b.quad(p, {}, col);
}

void poly(Batch& b, const Vec2 (&p)[4], SDL_FColor col) {
    const SDL_FPoint q[4] = {
        {p[0].x, p[0].y}, {p[1].x, p[1].y}, {p[2].x, p[2].y}, {p[3].x, p[3].y}};
    b.quad(q, {}, col);
}

SDL_FColor shade(SDL_FColor c, float k, float a) {
    return {std::min(1.0f, c.r * k), std::min(1.0f, c.g * k), std::min(1.0f, c.b * k), a};
}

} // namespace

WorldSprites::WorldSprites(SDL_Renderer* renderer, Atlas& home, PageAtlas& pages,
                           const world::WorldMap& map)
    : iso_(map.content().home().iso()), level_(map.content().tileLevel()) {
    resolveTerrain(map, pages);
    resolveFalls(map, pages);
    resolveItems(map, home, pages);
    buildPage(renderer, map, pages);
    count(map);
}

int WorldSprites::internMaterial(const std::string& id, PageAtlas& pages) {
    const auto it = std::ranges::find(materials_, id, &MaterialLook::id);
    if (it != materials_.end()) return static_cast<int>(it - materials_.begin());
    MaterialLook m;
    m.id = id;
    m.band[0] = variants(pages, "edge/" + id + "_se");
    m.band[1] = variants(pages, "edge/" + id + "_sw");
    m.top[0] = pages.find("edge/" + id + "_se/top");
    m.top[1] = pages.find("edge/" + id + "_sw/top");
    for (int side = 0; side < 2; ++side) {
        const auto sd = static_cast<std::size_t>(side);
        for (std::size_t v = 0; v < m.band[sd].size(); ++v) {
            Frames f = frames(pages, std::format("edge/{}_{}/v{}", id, side == 0 ? "se" : "sw", v));
            if (f.empty()) break;
            m.foot[sd].push_back(std::move(f));
        }
    }
    for (int side = 0; side < 2; ++side)
        for (int w = 0; w < 2; ++w)
            m.wedge[static_cast<std::size_t>(side)][static_cast<std::size_t>(w)] =
                variants(pages, std::format("edge/{}_{}/w{}", id, side == 0 ? "se" : "sw", w));
    if (m.foot[0].size() != m.band[0].size() || m.foot[1].size() != m.band[1].size()) {
        m.foot[0].clear();
        m.foot[1].clear();
    }
    m.fps = kFaceSurfFps;
    m.flat = materialColour(id);
    if (m.band[0].empty() || m.band[1].empty()) {
        m.band[0].clear();
        m.band[1].clear();
        flatMaterials_.push_back(id);
    }
    for (int side = 0; side < 2; ++side) {
        for (const SpriteRef& s : m.band[static_cast<std::size_t>(side)]) reach(groundReach_, s);
        for (const auto& w : m.wedge[static_cast<std::size_t>(side)])
            for (const SpriteRef& s : w) reach(groundReach_, s);
        if (m.top[static_cast<std::size_t>(side)])
            reach(groundReach_, *m.top[static_cast<std::size_t>(side)]);
    }
    materials_.push_back(std::move(m));
    return static_cast<int>(materials_.size() - 1);
}

void WorldSprites::resolveTerrain(const world::WorldMap& map, PageAtlas& pages) {
    const world::Content& content = map.content();
    waterFace_.id = "water";
    waterFace_.flat = rgb(150, 196, 214);
    terrains_.resize(map.terrainCount());
    for (std::size_t t = 0; t < map.terrainCount(); ++t) {
        const world::TerrainInfo& info = map.terrainInfo(static_cast<int>(t));
        TerrainLook& look = terrains_[t];
        look.water = info.water;
        look.fps = info.fps;
        look.flat = terrainColour(info);
        std::vector<std::string> faces = info.faces;
        if (info.base || !info.known) {
            look.base = variants(pages, "terrain/" + info.id);
        } else {
            const world::TerrainInfo under = content.terrain(info.under);
            look.base = variants(pages, "terrain/" + under.id);
            look.flatBase = terrainColour(under);
            if (faces.empty()) faces = under.faces;
            for (int m = 0; m < 16; ++m)
                look.overlay[static_cast<std::size_t>(m)] =
                    frames(pages, std::format("terrain/{}/m{}", info.id, m));
            if (std::ranges::any_of(look.overlay, &Frames::empty))
                for (Frames& f : look.overlay) f.f.clear();
            // The interior's further looks (`m15/v<n>`, V6-004); v0 is `m15` itself.
            if (look.hasOverlay())
                for (int v = 1;; ++v) {
                    Frames f = frames(pages, std::format("terrain/{}/m15/v{}", info.id, v));
                    if (f.empty()) break;
                    if (look.interior.empty()) look.interior.push_back(look.overlay[15]);
                    look.interior.push_back(std::move(f));
                }
        }
        if (info.slopes) {
            const std::string baseId = info.base || !info.known ? info.id : info.under;
            for (int sh = 1; sh < world::kSlopeCount; ++sh) {
                const auto key = world::slopeKey(world::Slope(sh));
                const auto k = static_cast<std::size_t>(sh);
                look.slope[k] = variants(pages, std::format("terrain/{}/slope/{}", info.id, key));
                look.slopeBase[k] =
                    baseId == info.id
                        ? look.slope[k]
                        : variants(pages, std::format("terrain/{}/slope/{}", baseId, key));
                for (const SpriteRef& s : look.slope[k]) reach(groundReach_, s);
                for (const SpriteRef& s : look.slopeBase[k]) reach(groundReach_, s);
            }
            if (std::ranges::any_of(look.slope | std::views::drop(1),
                                    [](const auto& v) { return v.empty(); }))
                flatSlopes_.push_back(info.id);
        }
        if (info.water) {
            for (int m = 0; m < 16; ++m)
                look.foam[static_cast<std::size_t>(m)] =
                    frames(pages, std::format("terrain/{}/foam/m{}", info.id, m));
            if (std::ranges::any_of(look.foam, &Frames::empty))
                for (Frames& f : look.foam) f.f.clear();
        }
        const auto& seasons = content.home().seasons;
        for (std::size_t sn = 0; sn < seasons.size() && sn < kSeasonLooks; ++sn) {
            const std::string at = "@" + seasons[sn].id;
            const std::string baseId = info.base || !info.known ? info.id : info.under;
            look.seasonBase[sn] = seasonal(pages, "terrain/" + baseId, "/v", at, look.base.size());
            if (look.hasOverlay()) {
                bool all = true;
                for (int m = 0; m < 16 && all; ++m) {
                    auto& f = look.seasonOverlay[sn][static_cast<std::size_t>(m)];
                    f.f = seasonal(pages, std::format("terrain/{}/m{}", info.id, m), "/f", at,
                                   look.overlay[static_cast<std::size_t>(m)].f.size());
                    all = !f.empty();
                }
                if (!all)
                    for (Frames& f : look.seasonOverlay[sn]) f.f.clear();
            }
        }
        for (std::size_t k = 0; k < faces.size() && k < look.faces.size(); ++k)
            look.faces[k] = internMaterial(faces[k], pages);
        for (const SpriteRef& s : look.base) reach(groundReach_, s);
        for (const Frames& o : look.overlay)
            for (const SpriteRef& s : o.f) reach(groundReach_, s);
    }
}

void WorldSprites::resolveFalls(const world::WorldMap& map, PageAtlas& pages) {
    for (const world::SetCatalog& set : map.content().sets())
        if (set.art.fallFps > 0) {
            falls_.fps = set.art.fallFps;
            falls_.speed = set.art.fallSpeed;
        }
    static constexpr std::array<std::string_view, 4> kParts{"rapid", "top", "mid", "foot"};
    for (int side = 0; side < 2; ++side)
        for (std::size_t p = 0; p < kParts.size(); ++p)
            for (int e = 0; e < 4; ++e) {
                Frames f = frames(pages, std::format("edge/world.fall_{}/{}/e{}",
                                                     side == 0 ? "se" : "sw", kParts[p], e));
                for (const SpriteRef& s : f.f) reach(groundReach_, s);
                falls_.part[static_cast<std::size_t>(side)][p][static_cast<std::size_t>(e)] =
                    std::move(f);
            }
    for (int m = 1; m < 16; ++m)
        falls_.plunge[static_cast<std::size_t>(m)] =
            frames(pages, std::format("terrain/world.river/plunge/m{}", m));
    falls_.rapids[0] = frames(pages, "terrain/world.river/rapids_n");
    falls_.rapids[1] = frames(pages, "terrain/world.river/rapids_e");
    // Every part on both sides, or none: half a fall would show a box of water again.
    for (const auto& side : falls_.part)
        for (const auto& part : side)
            if (std::ranges::any_of(part, &Frames::empty)) falls_.part[0][0][0].f.clear();
    for (const Frames& f : falls_.plunge)
        for (const SpriteRef& s : f.f) reach(groundReach_, s);
    for (const Frames& f : falls_.rapids)
        for (const SpriteRef& s : f.f) reach(groundReach_, s);
}

void WorldSprites::resolveItems(const world::WorldMap& map, Atlas& home, PageAtlas& pages) {
    const world::Content& content = map.content();
    const Catalog& cat = content.home();
    // Placeholders are made only for what is placed.
    std::set<std::pair<std::uint32_t, int>> placed;
    for (const world::Placed& it : map.items())
        placed.emplace(it.info, map.info(it).layout == Layout::Connect ? it.mask : it.variant);
    float peakSum = 0;
    int peaks = 0;
    const auto shadow = [&](const std::string& key) -> std::optional<SpriteRef> {
        if (const auto id = home.find(key)) {
            peakSum += home.normalizeAlpha(*id);
            ++peaks;
        }
        auto s = pages.find(key);
        if (s) pages.markShadow(*s);
        return s;
    };
    items_.resize(content.items().size());
    fps_.resize(content.items().size());
    for (std::size_t i = 0; i < content.items().size(); ++i) {
        const world::ItemInfo& info = content.item(static_cast<int>(i));
        fps_[i] = info.fps;
        const bool connect = info.layout == Layout::Connect;
        const int slots = connect ? 16 : (info.layout == Layout::Rotate ? 4 : info.count);
        auto& out = items_[i];
        out.resize(static_cast<std::size_t>(slots));
        for (int v = 0; v < slots; ++v) {
            VariantLook& look = out[static_cast<std::size_t>(v)];
            const std::string vk = info.variantKey(connect ? 0 : v, connect ? v : 0);
            const std::string prefix = "item/" + info.id;
            look.base = frames(pages, prefix + "/base/" + vk);
            if (const world::GeomVariant* g =
                    content.geometry(static_cast<int>(i), connect ? 0 : v, connect ? v : 0);
                g != nullptr && !g->pieces.empty()) {
                for (std::size_t p = 0; p < g->pieces.size(); ++p) {
                    const auto s = pages.find(std::format("{}/base/{}/p{}/f0", prefix, vk, p));
                    if (!s) {
                        look.pieces.clear();
                        break;
                    }
                    look.pieces.push_back(*s);
                }
            }
            if (!look.base.empty() && look.pieces.empty())
                for (std::size_t sn = 0; sn < cat.seasons.size() && sn < kSeasonLooks; ++sn)
                    look.seasonBase[sn].f = seasonal(pages, prefix + "/base/" + vk, "/f",
                                                     "@" + cat.seasons[sn].id, look.base.f.size());
            if (!look.base.empty() || !look.pieces.empty()) {
                look.shadow = shadow(prefix + "/shadow/" + vk + "/f0");
                look.glow = pages.find(prefix + "/glow/" + vk + "/f0");
            } else if (const auto si =
                           info.standIn.empty() ? std::nullopt : cat.findItem(info.standIn)) {
                const ItemDef& d = cat.items[static_cast<std::size_t>(*si)];
                const std::string hk = d.layout == Layout::Connect
                                           ? std::format("m{}", v % 16)
                                           : std::format("r{}", v % std::max(d.count, 1));
                look.base = frames(pages, "item/" + d.id + "/base/" + hk);
                look.shadow = shadow("item/" + d.id + "/shadow/" + hk + "/f0");
                look.look = Look::StandIn;
                for (std::size_t sn = 0; sn < cat.seasons.size() && sn < kSeasonLooks; ++sn)
                    look.seasonBase[sn].f = seasonal(pages, "item/" + d.id + "/base/" + hk, "/f",
                                                     "@" + cat.seasons[sn].id, look.base.f.size());
            }
            if (look.base.empty() && look.pieces.empty()) {
                look.look = Look::Placeholder;
                if (placed.contains({static_cast<std::uint32_t>(i), v})) {
                    const Footprint fp = info.footprint(connect ? 0 : v);
                    boxes_.push_back({static_cast<std::uint32_t>(i), v, fp.w, fp.h});
                }
            }
            const Footprint fp = info.footprint(connect ? 0 : v);
            for (const SpriteRef& s : look.base.f) span(itemSpan_, s, {0, 0, fp.w, fp.h}, iso_);
            // Shadows fall beyond the sprite: an item off the view may still shade it.
            if (look.shadow) span(itemSpan_, *look.shadow, {0, 0, fp.w, fp.h}, iso_);
            if (const world::GeomVariant* g =
                    content.geometry(static_cast<int>(i), connect ? 0 : v, connect ? v : 0);
                g != nullptr && g->pieces.size() == look.pieces.size())
                for (std::size_t p = 0; p < look.pieces.size(); ++p)
                    span(itemSpan_, look.pieces[p], g->pieces[p].rect, iso_);
        }
    }
    homeShadowPeak_ = peaks > 0 ? peakSum / static_cast<float>(peaks) : -1.0f;
}

void WorldSprites::buildPage(SDL_Renderer* renderer, const world::WorldMap& map, PageAtlas& pages) {
    const world::Content& content = map.content();
    const int hw = static_cast<int>(iso_.hw);
    const int hh = static_cast<int>(iso_.hh);
    const int lvl = level_;
    // Faces: one band under each lower edge, exactly below the diamond's raster, from the bottom
    // vertex to the side vertex with both included (south-east columns -1 .. hw-1, south-west
    // -hw .. 0), so faces meet along straight cliffs and in corners. The side vertex column has
    // no diamond pixel: the edge there lies one row above its neighbour's.
    const auto edgeBottom = [&](int x) {
        if (x >= hw - 1) return diamondBottom(hw - 2, hw, hh) - 1;
        if (x <= -hw) return diamondBottom(-hw + 1, hw, hh) - 1;
        return diamondBottom(x, hw, hh);
    };
    int faceTop = 2 * hh;
    int faceBottom = 0;
    for (int x = -hw; x < hw; ++x) {
        const int yb = edgeBottom(x);
        faceTop = std::min(faceTop, yb + 1);
        faceBottom = std::max(faceBottom, yb + lvl);
    }
    const int faceH = faceBottom - faceTop + 1;
    const int headerH = std::max(2 * hh, faceH) + kPagePad;

    // Markers, measured and shelf-packed below the engine sprites: a low slab over the footprint,
    // as quiet as honesty allows (the profiler's overlay names them).
    for (Box& b : boxes_) {
        b.height = tuning::kPlaceholderHeight;
        const int boxW = (b.fw + b.fh) * hw + 2;
        b.w = boxW;
        const int top = static_cast<int>(std::ceil(b.height));
        b.h = (b.fw + b.fh) * hh + top + 2;
        b.ox = static_cast<float>(b.fh * hw + 1);
        b.oy = static_cast<float>(top + 1);
    }
    int pageW = 1024;
    for (const Box& b : boxes_) pageW = std::max(pageW, b.w + 2 * kPagePad);
    std::vector<std::size_t> byHeight(boxes_.size());
    for (std::size_t i = 0; i < byHeight.size(); ++i) byHeight[i] = i;
    std::ranges::stable_sort(
        byHeight, [&](std::size_t a, std::size_t b) { return boxes_[a].h > boxes_[b].h; });
    int x = 0;
    int y = headerH;
    int rowH = 0;
    for (const std::size_t i : byHeight) {
        Box& b = boxes_[i];
        if (x + b.w + kPagePad > pageW) {
            x = 0;
            y += rowH + kPagePad;
            rowH = 0;
        }
        b.x = x;
        b.y = y;
        x += b.w + kPagePad;
        rowH = std::max(rowH, b.h);
    }
    const int pageH = std::min(world::kMaxPageSide, y + rowH + kPagePad);

    // Engine sprites in pixels: a white block, the diamond, the two faces.
    const SurfacePtr px{SDL_CreateSurface(pageW, pageH, kTextureFormat)};
    if (!px || !SDL_ClearSurface(px.get(), 0, 0, 0, 0)) {
        SDL_Log("worldview: cannot make the generated page: %s", SDL_GetError());
        return;
    }
    for (int j = 0; j < 4; ++j)
        for (int i = 0; i < 4; ++i) putWhite(px.get(), i, j);
    const int dx = 4 + kPagePad;
    for (int j = 0; j < 2 * hh; ++j)
        for (int i = 0; i < 2 * hw; ++i)
            if (inDiamond(i - hw, j, hw, hh)) putWhite(px.get(), dx + i, j);
    const int fx = dx + 2 * hw + kPagePad;
    for (int i = 0; i <= hw; ++i) {
        const int se = edgeBottom(i - 1);
        for (int j = se + 1; j <= se + lvl; ++j) putWhite(px.get(), fx + i, j - faceTop);
        const int sw = edgeBottom(i - hw);
        for (int j = sw + 1; j <= sw + lvl; ++j)
            putWhite(px.get(), fx + hw + 1 + kPagePad + i, j - faceTop);
    }
    TexturePtr page{
        SDL_CreateTexture(renderer, kTextureFormat, SDL_TEXTUREACCESS_TARGET, pageW, pageH)};
    const TexturePtr pixels = uploadTexture(renderer, px.get());
    SDL_Texture* out = SDL_GetRenderTarget(renderer); // the window, or what stands in for it
    if (!page || !pixels || !SDL_SetTextureBlendMode(page.get(), SDL_BLENDMODE_BLEND) ||
        !SDL_SetTextureBlendMode(pixels.get(), SDL_BLENDMODE_NONE) ||
        !SDL_SetRenderTarget(renderer, page.get()) ||
        !SDL_RenderTexture(renderer, pixels.get(), nullptr, nullptr)) {
        SDL_Log("worldview: generated page: %s", SDL_GetError());
        return;
    }

    // Placeholder markers: the footprint as a low tinted slab, translucent, with a soft rim.
    Batch batch(renderer);
    for (const Box& b : boxes_) {
        const world::ItemInfo& info = content.item(static_cast<int>(b.info));
        const Vec2 a{static_cast<float>(b.x) + b.ox, static_cast<float>(b.y) + b.oy};
        const auto P = [&](float tx, float ty, float up) {
            return Vec2{a.x + (tx - ty) * iso_.hw, a.y + (tx + ty) * iso_.hh - up};
        };
        const auto fw = static_cast<float>(b.fw);
        const auto fh = static_cast<float>(b.fh);
        const float hpx = b.height;
        const Vec2 right = P(fw, 0, 0), bottom = P(fw, fh, 0), left = P(0, fh, 0);
        const Vec2 topU = P(0, 0, hpx), rightU = P(fw, 0, hpx), bottomU = P(fw, fh, hpx),
                   leftU = P(0, fh, hpx);
        const SDL_FColor base = categoryColour(info, {b.fw, b.fh});
        const float alpha = tuning::kPlaceholderAlpha;
        batch.use(nullptr, SDL_BLENDMODE_NONE);
        poly(batch, {left, bottom, bottomU, leftU}, shade(base, 0.86f, alpha));
        poly(batch, {bottom, right, rightU, bottomU}, shade(base, 0.72f, alpha));
        poly(batch, {topU, rightU, bottomU, leftU}, shade(base, 1.0f, alpha * 0.8f));
        batch.use(nullptr, SDL_BLENDMODE_BLEND);
        for (const auto& [p, q] :
             {std::pair{topU, rightU}, {rightU, bottomU}, {bottomU, leftU}, {leftU, topU}})
            line(batch, p, q, shade(base, 1.25f, alpha));
    }
    batch.flush();
    if (!SDL_SetRenderTarget(renderer, out)) SDL_Log("worldview: %s", SDL_GetError());
    pages.setGenerated(std::move(page), pageW, pageH);

    white_ = pages.generated(1, 1, 2, 2, 1, 1);
    diamond_ = pages.generated(dx, 0, 2 * hw, 2 * hh, static_cast<float>(hw), 0);
    face_[0] = pages.generated(fx, 0, hw + 1, faceH, 1, static_cast<float>(-faceTop));
    face_[1] = pages.generated(fx + hw + 1 + kPagePad, 0, hw + 1, faceH, static_cast<float>(hw),
                               static_cast<float>(-faceTop));
    reach(groundReach_, diamond_);
    reach(groundReach_, face_[0]);
    reach(groundReach_, face_[1]);
    for (const Box& b : boxes_) {
        VariantLook& look = items_[b.info][static_cast<std::size_t>(b.variant)];
        if (b.y + b.h > pageH) continue; // did not fit: the generic box below
        look.base.f = {pages.generated(b.x, b.y, b.w, b.h, b.ox, b.oy)};
        span(itemSpan_, look.base.f.front(), {0, 0, b.fw, b.fh}, iso_);
    }
    unknown_.base.f = {diamond_};
    unknown_.look = Look::Placeholder;
    for (auto& variants : items_)
        for (VariantLook& v : variants)
            if (v.base.empty() && v.pieces.empty()) v.base = unknown_.base;
    groundReach_.up += static_cast<float>(15 * lvl);
    itemSpan_.up += static_cast<float>(15 * lvl);
}

const VariantLook& WorldSprites::item(const world::Placed& it) const {
    const auto& v = items_[it.info];
    const std::size_t k = v.size() == 16 ? it.mask : it.variant;
    return k < v.size() ? v[k] : unknown_;
}

void WorldSprites::count(const world::WorldMap& map) {
    std::map<std::uint32_t, std::pair<int, Look>> items;
    for (const world::Placed& it : map.items()) {
        const VariantLook& look = item(it);
        if (look.look == Look::Art) continue;
        auto& e = items[it.info];
        ++e.first;
        e.second = look.look;
        if (look.look == Look::Placeholder) ++placeholdersPlaced_;
    }
    for (const auto& [info, e] : items)
        missingItems_.push_back({map.content().item(static_cast<int>(info)).id, e.first, e.second});
    std::vector<int> tiles(terrains_.size(), 0);
    for (int y = 0; y < map.height(); ++y)
        for (int x = 0; x < map.width(); ++x) {
            const int t = map.terrainAt({x, y});
            if (t != world::kNone) ++tiles[static_cast<std::size_t>(t)];
        }
    for (std::size_t t = 0; t < terrains_.size(); ++t) {
        const TerrainLook& l = terrains_[t];
        const bool overlay = !map.terrainInfo(static_cast<int>(t)).base;
        if (tiles[t] > 0 && (overlay ? !l.hasOverlay() : l.base.empty()))
            missingTerrain_.push_back({map.terrainInfo(static_cast<int>(t)).id, tiles[t]});
    }
    std::ranges::sort(missingItems_, std::greater<>{}, &MissingArt::count);
    std::ranges::sort(missingTerrain_, std::greater<>{}, &MissingArt::count);
}

} // namespace lc::worldview
