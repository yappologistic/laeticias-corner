#include "worldview/renderer.hpp"

#include "core/rng.hpp"
#include "core/tuning.hpp"
#include "platform/process.hpp"
#include "render/bands.hpp"
#include "render/draw.hpp"
#include "render/gpu/post.hpp"
#include "worldview/tuning.hpp"
#include "worldview/world_lights.hpp"

#include <nlohmann/json.hpp>

#include <algorithm>
#include <chrono>
#include <cmath>
#include <format>
#include <fstream>

namespace lc::worldview {
namespace {

constexpr SDL_FColor kWhite{1, 1, 1, 1};

// Adds the time a scope takes to `ms` (cache work on the main thread, for the profiler).
class Timed {
public:
    explicit Timed(double& ms) : ms_(ms), t0_(SDL_GetPerformanceCounter()) {}
    ~Timed() { ms_ += msBetween(t0_, SDL_GetPerformanceCounter()); }
    Timed(const Timed&) = delete;
    Timed& operator=(const Timed&) = delete;

private:
    double& ms_;
    Uint64 t0_;
};
constexpr int kMaxLevel = 15;
constexpr std::uint64_t kRegionTag = 1ULL << 63; // block tags are cell keys shifted by two
constexpr std::uint64_t kAheadTag = kRegionTag | 1;

SDL_FColor times(SDL_FColor c, float k) {
    return {c.r * k, c.g * k, c.b * k, c.a};
}

// Calls f for the tiles of `r` in painter's order (diagonal by diagonal) whose top vertex lies
// between world x `x0` and `x1`: a screen rectangle is a diamond in the grid, and its bounding
// tile rectangle holds twice the tiles that can draw into it.
template <typename F>
void diagonals(TileRect r, float halfW, float x0, float x1, F&& f) {
    for (int s = r.x0 + r.y0; s <= r.x1 + r.y1 - 2; ++s) {
        // A tile's top vertex is at x = (tx - ty) * halfW = (2 tx - s) * halfW.
        const auto fs = static_cast<float>(s);
        const int lo = static_cast<int>(std::floor((fs + x0 / halfW) * 0.5f));
        const int hi = static_cast<int>(std::ceil((fs + x1 / halfW) * 0.5f));
        for (int tx = std::max({r.x0, s - (r.y1 - 1), lo});
             tx <= std::min({r.x1 - 1, s - r.y0, hi}); ++tx)
            f(TilePos{tx, s - tx});
    }
}

// The region of the tile a world px point lies on (the land's level counted), -1 off the grid.
int regionUnder(const world::WorldMap& m, Iso iso, int lift, Vec2 px) {
    const TilePos p = tileTopAt(iso, lift, kMaxLevel, px,
                                [&](TilePos t) { return m.inBounds(t) ? m.level(t) : -1; });
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
      cells_(renderer, tuning::kCellBudgetMin, async), batch_(renderer), theme_([&] {
          std::vector<world::Theme> themes;
          themes.reserve(world.regions.size());
          for (const world::RegionFile& r : world.regions) themes.push_back(r.theme);
          return themes;
      }()),
      places_(
          [&] {
              std::vector<world::RegionKind> kinds;
              kinds.reserve(world.file.regions.size());
              for (const world::RegionRef& r : world.file.regions) kinds.push_back(r.kind);
              return kinds;
          }(),
          [&] {
              std::vector<std::string> times;
              times.reserve(world.file.regions.size());
              for (const world::RegionRef& r : world.file.regions) times.push_back(r.time);
              return times;
          }()) {
    // On SDL's gpu driver the sets' pages are their packed twins, decoded as they draw (the
    // seasons by climate and month); elsewhere the colour pages.
    if (gpu::isGpu(renderer)) {
        std::ifstream in(assets / "atlas" / "ramps.json");
        const SurfacePtr table{SDL_LoadPNG((assets / "atlas" / "ramps.png").string().c_str())};
        try {
            if (in && table) {
                rampSeasons_ = gpu::parseRamps(nlohmann::json::parse(in));
                decoder_ = gpu::Decoder::make(renderer, table.get(), rampSeasons_);
            }
        } catch (const nlohmann::json::exception& e) {
            SDL_Log("worldview: ramps.json: %s", e.what());
        }
        if (!decoder_) SDL_Log("worldview: no packed decode: the colour pages, no seasons by data");
    }
    const Catalog& cat = map_.content().home();
    const auto climateRow = [&](std::string_view id) {
        for (std::size_t i = 0; i < cat.climates.size() && i + 1 < gpu::Decoder::kClimates; ++i)
            if (cat.climates[i].id == id) return static_cast<int>(i);
        return -1;
    };
    for (const world::RegionFile& r : world.regions) {
        const int c = climateRow(r.theme.climate);
        regionClimate_.push_back(c < 0 ? std::uint8_t{255} : static_cast<std::uint8_t>(c));
    }
    fallbackClimate_ = std::max(0, climateRow("med_green"));
    homeClimate_ = climateRow("home");
    if (decoder_) startSeasonField();
    pages_ = std::make_unique<PageAtlas>(renderer, home, world.atlas, assets / "atlas", async,
                                         tuning::kPageCeiling, decoder_ != nullptr);
    sprites_ = std::make_unique<WorldSprites>(renderer, home, *pages_, map_);
    buildMacro();
    waterKinds_.channel.resize(map_.terrainCount());
    waterKinds_.bank.resize(map_.terrainCount());
    for (std::size_t t = 0; t < map_.terrainCount(); ++t) {
        const world::TerrainInfo& info = map_.terrainInfo(static_cast<int>(t));
        waterKinds_.channel[t] = info.water && flowingWater(info.id);
        waterKinds_.bank[t] = sprites_->terrain(static_cast<int>(t)).faces[0] >= 0;
    }
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
    gpuDriver_ = gpu::isGpu(renderer_);
    if (!hole_.empty()) {
        // The home stands at its level; nothing outside it reaches over or under it.
        hole_.z0 = static_cast<float>(map_.level({hole_.tiles.x0, hole_.tiles.y0}) * lvl_);
        hole_.z1 = hole_.z0 + static_cast<float>(kMaxLevel * lvl_);
    }
    prep_ = std::make_unique<Prep>(map_, *sprites_, async, hole_, figures_);
    {
        // The coarse levels' top field: one pass over the items, a few milliseconds.
        const Uint64 t0 = SDL_GetPerformanceCounter();
        tops_ = std::make_unique<TopField>(map_, *sprites_, hole_);
        SDL_Log("worldview: top field in %.0f ms",
                static_cast<double>(SDL_GetPerformanceCounter() - t0) * 1000.0 /
                    static_cast<double>(SDL_GetPerformanceFrequency()));
    }
    buildGlow();
    blob_ = home.sprite(home.lightBlob());
    if (const auto drop = home.find("fx/raindrop/f0"))
        buildRainPicture(rainPicture_, home.sprite(*drop), 31u);
    if (const auto flake = home.find("fx/snowflake/f0"))
        buildRainPicture(snowPicture_, home.sprite(*flake), 37u);
    if (async) warmUp();
    for (std::size_t t = 0; t < map_.terrainCount(); ++t) {
        const world::TerrainInfo& info = map_.terrainInfo(static_cast<int>(t));
        if (info.water && (sea_ < 0 || info.id.find("sea") != std::string::npos))
            sea_ = static_cast<int>(t);
        const TerrainLook& l = sprites_->terrain(static_cast<int>(t));
        if (l.animated() || (!l.foam[0].empty() && l.fps > 0)) {
            animFps_ = std::max(animFps_, l.fps);
            // A cell with water is cached once per step of the longest loop in it.
            std::size_t frames = l.animated() ? l.overlay[0].f.size() : 1;
            for (const Frames& f : l.foam) frames = std::max(frames, f.f.size());
            animPeriod_ = std::clamp(static_cast<int>(frames), animPeriod_, tuning::kCellPeriodMax);
        }
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
    // Every target a frame may need is made now: each is a stall of several milliseconds on
    // first use (tens on SDL's gpu driver), and the impostors' scratch targets were first
    // needed in the middle of play.
    ensure(scratch_, tuning::kImpostorBlock, tuning::kImpostorBlock);
    ensure(scratchShadow_, tuning::kImpostorBlock, tuning::kImpostorBlock);
    ensure(half_, tuning::kImpostorBlock / 2, tuning::kImpostorBlock / 2);
    warmTarget(half_.texture.get());
}

void WorldView::warmTarget(SDL_Texture* target) {
    // Drivers prepare blend and filter state on first use for each kind of target, a stall of
    // several milliseconds in the middle of a run: use every combination once, and wait.
    if (target == nullptr) return;
    SDL_Texture* out = SDL_GetRenderTarget(renderer_);
    batch_.setBand(bandTag(Band::Debug)); // into a target at load, never seen
    SDL_Texture* white = pages_->texture(sprites_->white().page);
    if (!SDL_SetRenderTarget(renderer_, target)) SDL_Log("worldview: %s", SDL_GetError());
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
    // A sprite of a packed page is drawn through the decode, with its own blending and colour.
    // (The home page's twin may still be on its way: its sprites draw plain until then.)
    const bool packed =
        decoder_ && s.packed && (s.page != PageAtlas::kHomePage || pages_->homePackedReady());
    if (packed) {
        if (c.a >= 1.0f && mode == SDL_BLENDMODE_BLEND) mode = decoder_->replace();
        c = packedColour(c, s.page == PageAtlas::kHomePage, mirror);
    }
    if (!runsOpen_) {
        if (decoder_) decoder_->use(batch_, packed);
        putSprite(batch_, Sprite{t, s.uv, s.w, s.h, s.ox, s.oy}, anchor, x, c, mode, mirror);
        return true;
    }
    // Kept for closeRuns, which draws it with its page's run: the corners as putSprite makes
    // them, to the last bit. What it is drawn with (page, blending, decoded or not) is its
    // run's key: mixed into one number, and should two ever share it they are still drawn
    // each with its own state, only without a run to themselves.
    const float lx = mirror ? -(s.w - s.ox) : -s.ox;
    const float ly = -s.oy;
    const Vec2 p0 = x.apply({anchor.x + lx, anchor.y + ly});
    const Vec2 p1 = x.apply({anchor.x + (lx + s.w), anchor.y + (ly + s.h)});
    const std::uint32_t key =
        (s.page * 2U + (packed ? 1U : 0U)) ^ (static_cast<std::uint32_t>(mode) * 2654435761U);
    if (!runs_.add(key, {p0.x, p0.y, p1.x, p1.y}))
        return true; // off the target: nothing of it would be drawn
    UvRect uv = s.uv;
    if (mirror) std::swap(uv.u0, uv.u1);
    runQuads_.push_back({t, mode, p0, p1, uv, c, s.page, runWhat_, packed});
    return true;
}

bool WorldView::putPoly(const SpriteRef& s, Vec2 anchor, const Xform& x, SDL_FColor c,
                        SDL_BlendMode mode, bool mirror, std::span<const Vec2> pts) {
    SDL_Texture* t = pages_->texture(s.page);
    if (t == nullptr) return false;
    if (pts.size() < 3) return true;
    const bool packed =
        decoder_ && s.packed && (s.page != PageAtlas::kHomePage || pages_->homePackedReady());
    if (packed) {
        if (c.a >= 1.0f && mode == SDL_BLENDMODE_BLEND) mode = decoder_->replace();
        c = packedColour(c, s.page == PageAtlas::kHomePage, mirror);
    }
    // Texture coordinates by where each corner lies in the sprite's picture (mirrored: from the
    // other side).
    const float x0 = anchor.x - (mirror ? s.w - s.ox : s.ox);
    const float y0 = anchor.y - s.oy;
    RunPoly poly;
    FRect box{1e9f, 1e9f, -1e9f, -1e9f};
    for (const Vec2 w : pts) {
        const Vec2 p = x.apply(w);
        float u = (w.x - x0) / s.w;
        if (mirror) u = 1.0f - u;
        poly.v[static_cast<std::size_t>(poly.n++)] = {
            {p.x, p.y},
            c,
            {s.uv.u0 + (s.uv.u1 - s.uv.u0) * u, s.uv.v0 + (s.uv.v1 - s.uv.v0) * (w.y - y0) / s.h}};
        box = {std::min(box.x0, p.x), std::min(box.y0, p.y), std::max(box.x1, p.x),
               std::max(box.y1, p.y)};
        if (poly.n == static_cast<int>(poly.v.size())) break;
    }
    static constexpr std::array<int, 9> kFan{0, 1, 2, 0, 2, 3, 0, 3, 4};
    if (!runsOpen_) {
        if (decoder_) decoder_->use(batch_, packed);
        batch_.use(t, mode, x.filter);
        batch_.triangles(poly.v.data(), poly.n, kFan.data(), (poly.n - 2) * 3);
        return true;
    }
    const std::uint32_t key =
        (s.page * 2U + (packed ? 1U : 0U)) ^ (static_cast<std::uint32_t>(mode) * 2654435761U);
    if (!runs_.add(key, box)) return true; // off the target
    runQuads_.push_back({t,
                         mode,
                         {box.x0, box.y0},
                         {box.x1, box.y1},
                         s.uv,
                         c,
                         s.page,
                         runWhat_,
                         packed,
                         static_cast<std::int32_t>(runPolys_.size())});
    runPolys_.push_back(poly);
    return true;
}

void WorldView::openRuns() {
    runs_.begin({0, 0, static_cast<float>(viewW_), static_cast<float>(viewH_)});
    runQuads_.clear();
    runPolys_.clear();
    runsOpen_ = true;
}

void WorldView::closeRuns(SDL_ScaleMode filter) {
    for (const std::uint32_t e : runs_.order()) {
        const RunQuad& q = runQuads_[e];
        if (decoder_) decoder_->use(batch_, q.packed);
        batch_.use(q.texture, q.mode, filter);
        if (q.poly >= 0) {
            static constexpr std::array<int, 9> kFan{0, 1, 2, 0, 2, 3, 0, 3, 4};
            const RunPoly& rp = runPolys_[static_cast<std::size_t>(q.poly)];
            batch_.triangles(rp.v.data(), rp.n, kFan.data(), (rp.n - 2) * 3);
            continue;
        }
        const SDL_FPoint p[4] = {
            {q.p0.x, q.p0.y}, {q.p1.x, q.p0.y}, {q.p1.x, q.p1.y}, {q.p0.x, q.p1.y}};
        batch_.quad(p, q.uv, q.colour);
    }
    batch_.flush();
    runsOpen_ = false;
}

std::vector<WorldView::RunBreaker> WorldView::runBreakers() const {
    // A run of a dozen sprites or fewer is one that something of another page was drawn
    // through; longer ones are a page's own share of the view.
    constexpr std::size_t kShort = 12;
    std::vector<RunBreaker> out;
    const auto order = runs_.drawn();
    const auto name = [&](std::uint32_t what) -> std::string {
        if (what == kRunActor) return "people";
        if (what == kRunFigure) return "figures";
        if ((what & kRunTerrain) != 0)
            return "terrain " + map_.terrainInfo(static_cast<int>(what & ~kRunTerrain)).id;
        return world_.content->item(static_cast<int>(what)).id;
    };
    for (std::size_t a = 0; a < order.size();) {
        std::size_t b = a;
        while (b < order.size() && runQuads_[order[b]].page == runQuads_[order[a]].page) ++b;
        for (std::size_t k = a; k < b; ++k) {
            const RunQuad& q = runQuads_[order[k]];
            std::string what = name(q.what);
            std::string page = pages_->pageName(q.page);
            auto it = std::ranges::find_if(
                out, [&](const RunBreaker& r) { return r.what == what && r.page == page; });
            if (it == out.end())
                it = out.insert(out.end(), {std::move(what), std::move(page), 0, 0});
            ++it->inView;
            it->inShortRuns += b - a <= kShort ? 1 : 0;
        }
        a = b;
    }
    std::erase_if(out, [](const RunBreaker& r) { return r.inShortRuns == 0; });
    std::ranges::sort(out, [](const RunBreaker& x, const RunBreaker& y) {
        return x.inShortRuns != y.inShortRuns ? x.inShortRuns > y.inShortRuns : x.what < y.what;
    });
    return out;
}

bool WorldView::drawTile(TilePos p, const Xform& x, float now, bool* animated) {
    const int t = map_.terrainAt(p);
    if (t == world::kNone) return true;
    seasonAt(p);
    const TerrainLook& look = sprites_->terrain(t);
    // Falling water keeps its frames on both paths (the shader path has no sheet of its own yet).
    const float fallNow = now;
    bool* const fallAnimated = animated;
    // On the shader path water moves in the final pass: its tiles stay still in the cells (no
    // rebuilds at the art's frame rate) and are marked for it.
    if (post_ && look.water) {
        now = 0;
        animated = nullptr;
    }
    const std::uint8_t lb = map_.levelByte(p);
    TileCtx c;
    c.p = p;
    c.t = t;
    c.look = &look;
    c.level = world::levelOf(lb);
    c.aux = world::auxOf(lb);
    c.slope = map_.slopeAt(p);
    c.a = [&] {
        const Vec2 w = iso_.toWorld(p);
        return Vec2{w.x, w.y - static_cast<float>(c.level * lvl_)};
    }();
    // Depth tints still water by its aux (a river's aux is its flow: no tint); on Classic it
    // is blended between tiles (the shader path draws depth in its water pass).
    const bool still = look.water && !waterKinds_.channel[static_cast<std::size_t>(t)];
    c.tint = still ? 1.0f - tuning::kWaterDepthTint * static_cast<float>(c.aux) : 1.0f;
    c.macro = !look.water && !hole_.tiles.contains(p);
    c.depth = still && !post_;
    // Land hangs its own face material; water its bank's (the base under it) where it stands
    // over land it does not flow onto, and falls everywhere else it steps down.
    const int face = look.faces[static_cast<std::size_t>(look.water ? 0 : c.aux)];
    const MaterialLook* mat = face >= 0    ? &sprites_->material(face)
                              : look.water ? &sprites_->waterFace()
                                           : nullptr;
    bool ok = true;
    std::array<int, 2> cap{-1, -1};
    int skip = 0;
    if (look.water && !sprites_->falls().empty()) {
        for (int side = 0; side < 2; ++side)
            if (fallDrop(p, side) > 0) skip |= 1 << side;
        ok &= drawFallFaces(c, x, fallNow, fallAnimated, false);
    }
    ok &= drawFaces(c, mat, x, now, animated, cap, skip);
    if (look.water) cap = {-1, -1}; // (no turf over water)
    const float jitter =
        1.0f +
        tuning::kFlatJitter * (static_cast<float>(tileHash(p.x, p.y, 7) % 100) / 50.0f - 1.0f);
    const bool overlay = !map_.terrainInfo(t).base;
    if (c.slope != world::Slope::Flat) {
        ok &= drawSlope(c, x, now, animated);
    } else {
        if (!overlay || look.hasOverlay()) {
            const std::vector<SpriteRef>& base = look.baseIn(lookSeason_);
            if (base.empty())
                ok &= put(sprites_->diamond(), c.a, x,
                          times(overlay ? look.flatBase : look.flat, jitter * c.tint),
                          SDL_BLENDMODE_BLEND);
            else
                ok &= drawGround(c, base[tileHash(p.x, p.y, 1) % base.size()], c.a, x, c.tint);
            if (post_ && look.water && !overlay) markWater(sprites_->diamond(), c.a);
        }
        if (overlay) {
            if (look.hasOverlay()) {
                const int mask = overlayMask(map_, p, t);
                // The interior's looks are picked per tile (V6-004); seasonal looks keep theirs.
                // Classic: shallows meeting the deep sea round off over the sea's own water
                // instead of stepping in whole diamonds (QA V7-017).
                const int own =
                    c.depth && sea_ >= 0 && t != sea_ ? overlayMaskExcept(map_, p, t, sea_) : mask;
                if (own != mask) {
                    const TerrainLook& sea = sprites_->terrain(sea_);
                    if (sea.hasOverlay()) {
                        ok &= drawGround(c, sea.overlayIn(mask, lookSeason_).at(now, sea.fps), c.a,
                                         x, c.tint);
                        if (sea.animated() && animated != nullptr) *animated = true;
                    }
                }
                const Frames& f = own == 15 && !look.interior.empty() &&
                                          &look.overlayIn(15, lookSeason_) == &look.overlay[15]
                                      ? look.interior[tileHash(p.x, p.y, 11) % look.interior.size()]
                                      : look.overlayIn(own, lookSeason_);
                ok &= drawGround(c, f.at(now, look.fps), c.a, x, c.tint);
                if (post_ && look.water) markWater(f.at(now, look.fps), c.a);
                if (look.animated() && animated != nullptr) *animated = true;
            } else {
                ok &= put(sprites_->diamond(), c.a, x, times(look.flat, jitter * c.tint),
                          SDL_BLENDMODE_BLEND);
            }
        }
    }
    if (look.water && !look.foam[0].empty() && !post_) { // (the shader path draws its own)
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
            ok &= put(look.foam[static_cast<std::size_t>(land)].at(now, look.fps), c.a, x, kWhite,
                      SDL_BLENDMODE_BLEND);
            if (animated != nullptr && look.fps > 0) *animated = true;
        }
    }
    if (look.water && !sprites_->falls().empty()) {
        ok &= drawPlunge(c, x, fallNow, fallAnimated);
        ok &= drawFallFaces(c, x, fallNow, fallAnimated, true);
    }
    for (int side = 0; side < 2; ++side) {
        const auto s = static_cast<std::size_t>(side);
        if (mat != nullptr && mat->top[s] && cap[s] >= 0)
            ok &= put(*mat->top[s], {c.a.x, c.a.y + static_cast<float>(cap[s] * lvl_)}, x, kWhite,
                      SDL_BLENDMODE_BLEND);
    }
    return ok;
}

bool WorldView::drawTiles(const FRect& px, const Xform& x, float now, bool* animated) {
    const Reach& r = sprites_->groundReach();
    const TileRect tiles = tilesUnder(grown(px, r), iso_);
    if (tiles.empty()) return true;
    const float lift = r.up - static_cast<float>(kMaxLevel * lvl_);
    bool ok = true;
    // The sea beyond the grid first, in two passes (the water, then its haze): flat and under
    // everything, and each pass one texture instead of two draws per tile. (Its water marks,
    // flat too, go on after the haze in one draw.)
    const float x0 = px.x0 - r.right;
    const float x1 = px.x1 + r.left;
    if (!map_.bounds().contains(tiles)) {
        for (const bool haze : {false, true})
            diagonals(tiles, iso_.hw, x0, x1, [&](TilePos p) {
                if (map_.inBounds(p)) return;
                const Vec2 w = iso_.toWorld(p);
                if (w.x + r.right >= px.x0 && w.x - r.left <= px.x1 && w.y + r.down >= px.y0 &&
                    w.y - iso_.tileH() <= px.y1)
                    ok &= drawBeyond(p, x, haze, now, animated);
            });
        flushMarks(x);
    }
    // Water marks wait until something drawn later could cover them: only a tile standing
    // higher than marked water behind it reaches over it (tiles at its level or lower meet it
    // edge to edge, and faces hang forward). On flat land a cell's marks go on in one draw.
    const int tw = tiles.x1 - tiles.x0;
    pendingWater_.assign(static_cast<std::size_t>(tw * (tiles.y1 - tiles.y0)), kNoWater);
    int lowest = kNoWater;
    const auto covers = [&](TilePos p, int level) {
        const int reach = std::min(2 * (level - lowest) + 1, 8);
        for (int b = 0; b <= reach; ++b)
            for (int a = 0; a + b <= reach; ++a) {
                const TilePos q{p.x - a, p.y - b};
                if ((a == 0 && b == 0) || std::abs(a - b) > 2 || !tiles.contains(q)) continue;
                const int lq = pendingWater_[static_cast<std::size_t>((q.y - tiles.y0) * tw +
                                                                      (q.x - tiles.x0))];
                if (lq != kNoWater && a + b <= 2 * (level - lq) + 1) return true;
            }
        return false;
    };
    diagonals(tiles, iso_.hw, x0, x1, [&](TilePos p) {
        if (!map_.inBounds(p)) return;
        const Vec2 w = iso_.toWorld(p);
        // The game's scene draws the hole; its rim tiles are drawn here too, under the scene's,
        // so the soft edges of its tile art meet the world's ground, not the sky.
        const TileRect& h = hole_.tiles;
        if (h.contains(p) && p.x > h.x0 && p.y > h.y0 && p.x < h.x1 - 1 && p.y < h.y1 - 1) return;
        const float top = w.y - static_cast<float>(map_.level(p) * lvl_) - lift;
        if (w.x + r.right < px.x0 || w.x - r.left > px.x1 || w.y + r.down < px.y0 || top > px.y1)
            return;
        const int level = map_.level(p);
        if (!marks_.empty() && level > lowest && covers(p, level)) {
            flushMarks(x);
            std::ranges::fill(pendingWater_, kNoWater);
            lowest = kNoWater;
        }
        const std::size_t before = marks_.size();
        ok &= drawTile(p, x, now, animated);
        if (marks_.size() > before) {
            pendingWater_[static_cast<std::size_t>((p.y - tiles.y0) * tw + (p.x - tiles.x0))] =
                static_cast<std::uint8_t>(level);
            lowest = std::min(lowest, level);
        }
    });
    flushMarks(x);
    return ok;
}

void WorldView::markWater(const SpriteRef& s, Vec2 anchor, bool maybe) {
    // Its water texels mark themselves as they draw (packed, and its page ready).
    if (decoder_ && s.packed && !maybe &&
        (s.page != PageAtlas::kHomePage || pages_->homePackedReady()))
        return;
    marks_.push_back({s, anchor, maybe});
}

void WorldView::flushMarks(const Xform& x) {
    if (marks_.empty()) return;
    for (const Mark& m : marks_)
        (void)put(m.sprite, m.anchor, x,
                  {1, 1, 1, m.maybe ? gpu::Post::kMaybeWaterMark : gpu::Post::kWaterMark},
                  post_->markBlend());
    marks_.clear();
}

bool WorldView::drawBeyond(TilePos p, const Xform& x, bool haze, float now, bool* animated) {
    const Vec2 a = iso_.toWorld(p);
    seasonCtx_ = {fallbackClimate_, fallbackClimate_, -1, 0, 0};
    lookSeason_ = season_;
    if (!haze) {
        // Beyond the grid the sea runs on: a tile there is the deep sea among sea, drawn as
        // the grid's own deepest water is (its art with every neighbour the same, at the
        // step its loop is in), so the edge of the grid is nowhere to be seen. (The sea's
        // art lies over another terrain's: its `base` is that terrain, sand, and was all
        // that was drawn here.)
        if (sea_ < 0) return true;
        const float tint = 1.0f - tuning::kWaterDepthTint * 3.0f;
        const TerrainLook& look = sprites_->terrain(sea_);
        if (look.hasOverlay()) {
            if (look.animated() && animated != nullptr) *animated = true;
            return put(look.overlayIn(kMaskN | kMaskE | kMaskS | kMaskW, season_).at(now, look.fps),
                       a, x, {tint, tint, tint, 1}, SDL_BLENDMODE_BLEND);
        }
        const std::vector<SpriteRef>& base = look.baseIn(season_);
        return base.empty()
                   ? put(sprites_->diamond(), a, x, times(look.flat, tint), SDL_BLENDMODE_BLEND)
                   : put(base[tileHash(p.x, p.y, 1) % base.size()], a, x, {tint, tint, tint, 1},
                         SDL_BLENDMODE_BLEND);
    }
    // Tiles beyond the edge, along the grid's axes (outside a corner, the larger of the two).
    const int dx = p.x < 0 ? -p.x : std::max(0, p.x - map_.width() + 1);
    const int dy = p.y < 0 ? -p.y : std::max(0, p.y - map_.height() + 1);
    const float k = std::min(1.0f, static_cast<float>(std::max(dx, dy)) / tuning::kHorizonTiles);
    const auto& h = tuning::kHorizonHaze;
    const float alpha = sea_ >= 0 ? k * tuning::kHorizonHazeMax : 1.0f;
    // (Marked over the haze: the final pass hands the hazed art back with distance.)
    if (post_ && sea_ >= 0) markWater(sprites_->diamond(), a);
    return alpha <= 0.0f ||
           put(sprites_->diamond(), a, x, {h[0], h[1], h[2], alpha}, SDL_BLENDMODE_BLEND);
}

const SpriteRef& WorldView::elemSprite(const Elem& e, float now) const {
    const VariantLook& look = *e.look;
    return e.piece >= 0 ? look.pieces[static_cast<std::size_t>(e.piece)]
                        : look.baseIn(lookSeason_).at(now, sprites_->itemFps(map_.items()[e.item]));
}

FRect WorldView::elemFoot(const Elem& e) const {
    const world::Placed& it = map_.items()[e.item];
    TileRect r = it.rect();
    if (const world::GeomVariant* g = map_.geometry(it);
        g != nullptr && e.piece >= 0 && std::cmp_less(e.piece, g->pieces.size())) {
        const TileRect& p = g->pieces[static_cast<std::size_t>(e.piece)].rect;
        r = {it.x + p.x0, it.y + p.y0, it.x + p.x1, it.y + p.y1};
    }
    const auto f = [](int v) { return static_cast<float>(v); };
    return {f(r.x0), f(r.y0), f(r.x1), f(r.y1)};
}

bool WorldView::drawElem(const Elem& e, const Xform& x, float now) {
    if (e.home) return true; // the game's scene draws it
    if (e.figure) return put(figures_[e.item].sprite, e.anchor, x, kWhite, SDL_BLENDMODE_BLEND);
    if (e.ground) {
        // A raised tile drawn live shows its water and falls at the step the cells round it
        // hold (their loop's middle), never at the frame's own time: the two must meet.
        const float at =
            animFps_ > 0 && animPeriod_ > 1
                ? (static_cast<float>(animStep_ % static_cast<std::uint64_t>(animPeriod_)) + 0.5f) /
                      animFps_
                : 0.0f;
        (void)now;
        return drawTile(e.tile, x, at, nullptr);
    }
    seasonAt(e.tile);
    const SpriteRef& s = elemSprite(e, now);
    if (post_ && e.piece < 0)
        if (const Sway& w = swayOf_[map_.items()[e.item].info]; w.lean > 0) {
            putSwaying(w.frames ? s : e.look->baseIn(lookSeason_).f.front(), e.anchor, x, w.lean);
            return true;
        }
    if (e.part < 0) {
        const bool ok = put(s, e.anchor, x, kWhite, SDL_BLENDMODE_BLEND);
        if (post_) markItemWater(e, x); // over the item's own pixels
        return ok;
    }
    if (e.part >= 2) return putHalf(s, e, x, kWhite);
    // One part of a floor with a roof over it: the rows below or above the roof's underside.
    return putCut(s, e.anchor, x, elemFoot(e), e.cutZ, e.part == 1);
}

bool WorldView::putHalf(const SpriteRef& s, const Elem& e, const Xform& x, SDL_FColor c) {
    // A kit bridge's half: the sprite's rectangle cut by its span through the tile's centre at
    // the deck's height (a ground point (gx, gy) at height z is drawn at y = (gx + gy)·hh − z);
    // the near half lies below the line.
    const float mid =
        e.alongX ? static_cast<float>(e.tile.y) + 0.5f : static_cast<float>(e.tile.x) + 0.5f;
    const float a = 2.0f * mid * iso_.hh - e.cutZ;
    const float b = (e.alongX ? 1.0f : -1.0f) * iso_.hh / iso_.hw;
    const bool near = e.part == 3;
    const float x0 = e.anchor.x - s.ox;
    const float y0 = e.anchor.y - s.oy;
    const std::array<Vec2, 4> rect{
        {{x0, y0}, {x0 + s.w, y0}, {x0 + s.w, y0 + s.h}, {x0, y0 + s.h}}};
    const auto side = [&](Vec2 p) { return near ? p.y - (a + b * p.x) : (a + b * p.x) - p.y; };
    std::array<Vec2, 5> poly{};
    std::size_t n = 0;
    for (std::size_t i = 0; i < rect.size(); ++i) {
        const Vec2 p = rect[i];
        const Vec2 q = rect[(i + 1) % rect.size()];
        const float sp = side(p);
        const float sq = side(q);
        if (sp >= 0 && n < poly.size()) poly[n++] = p;
        if ((sp >= 0) != (sq >= 0) && n < poly.size()) {
            const float t = sp / (sp - sq);
            poly[n++] = {p.x + (q.x - p.x) * t, p.y + (q.y - p.y) * t};
        }
    }
    return putPoly(s, e.anchor, x, c, SDL_BLENDMODE_BLEND, false, std::span(poly).first(n));
}

bool WorldView::putCut(const SpriteRef& s, Vec2 anchor, const Xform& x, const FRect& foot, float z,
                       bool upper, SDL_FColor c) {
    // The cut follows the footprint's front edges raised to the underside: every voxel of the
    // overhead lies above it, every voxel of the floor below (draw-order.md §1.5 f). Strips
    // between the edges' corners, each a trapezoid.
    const Vec2 l = iso_.toWorld(foot.x0, foot.y1);
    const Vec2 b = iso_.toWorld(foot.x1, foot.y1);
    const Vec2 r = iso_.toWorld(foot.x1, foot.y0);
    const float sx0 = anchor.x - s.ox;
    const float sy0 = anchor.y - s.oy;
    const float sx1 = sx0 + s.w;
    const float sy1 = sy0 + s.h;
    const auto cut = [&](float wx) {
        const float cx = std::clamp(wx, l.x, r.x);
        const float y = cx <= b.x ? l.y + (b.y - l.y) * (cx - l.x) / std::max(1.0f, b.x - l.x)
                                  : b.y + (r.y - b.y) * (cx - b.x) / std::max(1.0f, r.x - b.x);
        return std::clamp(y - z + 1, sy0, sy1);
    };
    std::array<float, 5> xs{sx0, std::clamp(l.x, sx0, sx1), std::clamp(b.x, sx0, sx1),
                            std::clamp(r.x, sx0, sx1), sx1};
    std::ranges::sort(xs);
    bool ok = true;
    for (std::size_t i = 0; i + 1 < xs.size(); ++i) {
        const float xa = xs[i];
        const float xb = xs[i + 1];
        if (xb <= xa) continue;
        const float ca = cut(xa);
        const float cb = cut(xb);
        const std::array<Vec2, 4> q =
            upper ? std::array<Vec2, 4>{{{xa, sy0}, {xb, sy0}, {xb, cb}, {xa, ca}}}
                  : std::array<Vec2, 4>{{{xa, ca}, {xb, cb}, {xb, sy1}, {xa, sy1}}};
        ok &= putPoly(s, anchor, x, c, SDL_BLENDMODE_BLEND, false, q);
    }
    return ok;
}

bool WorldView::drawShadows(const Gathered& g, const FRect& clip, const Xform& x, Target& layer,
                            Target& onto, bool actors, std::span<const std::uint32_t> visible) {
    plain(); // (what follows is not decoded)
    // Shadow sprites saturate in their own layer (their alpha was scaled to a peak of 1), which
    // is then laid over the ground once at the art's opacity: overlaps never double-darken.
    // The layer's coverage does not depend on order: drawn page by page, one draw each.
    shadows_.clear();
    // An element's screen box holds its shadow: what is not drawn casts none in view.
    const std::size_t n = visible.empty() ? g.order.size() : visible.size();
    const auto at = [&](std::size_t j) { return g.order[visible.empty() ? j : visible[j]]; };
    for (std::size_t j = 0; j < n; ++j) {
        const Elem& e = g.elems[at(j)];
        if (!e.first || e.look == nullptr || !e.look->shadow) continue;
        const SpriteRef& s = *e.look->shadow;
        const FRect box{e.anchor.x - s.ox, e.anchor.y - s.oy, e.anchor.x - s.ox + s.w,
                        e.anchor.y - s.oy + s.h};
        if (box.overlaps(clip)) shadows_.emplace_back(s.page, static_cast<std::uint32_t>(j));
    }
    // Open sea and bare land cast nothing: no layer is cleared, bound and laid over for them
    // (half the cost of an impostor block that has no shadow in it).
    if (shadows_.empty() && (!actors || actorOf_.empty())) return true;
    bool ok = true;
    batch_.flush();
    if (!SDL_SetRenderTarget(renderer_, layer.texture.get()) ||
        !SDL_SetRenderDrawColorFloat(renderer_, 0, 0, 0, 0) || !SDL_RenderClear(renderer_))
        SDL_Log("worldview: shadow layer: %s", SDL_GetError());
    // By page, then in the order's sequence: a total order, so the plain sort (which, unlike
    // the stable one, allocates nothing) gives the same result every time.
    std::ranges::sort(shadows_);
    // A shadow page holds its art at half size: enlarged, so filtered.
    Xform soft = x;
    soft.filter = SDL_SCALEMODE_LINEAR;
    for (const auto& [page, j] : shadows_) {
        const Elem& e = g.elems[at(j)];
        if (const std::optional<SpriteRef>& sh = e.look->shadow)
            ok &= sunShadows_ ? putShadow(*sh, e, pages_->smooth(page) ? soft : x)
                              : put(*sh, e.anchor, pages_->smooth(page) ? soft : x, kWhite,
                                    SDL_BLENDMODE_BLEND);
    }
    // People's shadows belong to the frame they are drawn in, never to a cached picture.
    if (actors) drawActorShadows(x);
    batch_.flush();
    if (!SDL_SetRenderTarget(renderer_, onto.texture.get()))
        SDL_Log("worldview: %s", SDL_GetError());
    if (post_) {
        shadeGpu(layer.texture.get(), static_cast<float>(layer.w), static_cast<float>(layer.h));
        return ok;
    }
    const float w = static_cast<float>(layer.w);
    const float h = static_cast<float>(layer.h);
    batch_.use(layer.texture.get(), SDL_BLENDMODE_BLEND_PREMULTIPLIED, SDL_SCALEMODE_NEAREST);
    const float k = shadowOpacity();
    batch_.quad(SDL_FRect{0, 0, w, h}, {0, 0, 1, 1}, {k, k, k, k});
    batch_.flush();
    return ok;
}

float WorldView::shadowOpacity() const {
    const float home = sprites_->homeShadowPeak();
    const float sets = pages_->shadowOpacity();
    return home >= 0 ? (home + sets) * 0.5f : sets;
}

void WorldView::buildGround(CellKey key, int si) {
    // The ground straight into the slot, at native resolution, at this step of its water's loop.
    const Timed timed(stats_.buildMs);
    const int before = batch_.drawCalls();
    CellSlot& slot = cells_.slot(si);
    const FRect cell = cellRect(key);
    bool animated = false;
    plain(); // the clear below is a fill: no page bound for the decode
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
    // Half a step in, so rounding never lands on the step before.
    const float at = animFps_ > 0 ? (static_cast<float>(key.frame) + 0.5f) / animFps_ : 0.0f;
    slot.complete =
        drawTiles(cell, {{cell.x0 - fx, cell.y0 - fy}, 1.0f, SDL_SCALEMODE_NEAREST}, at, &animated);
    batch_.flush();
    if (!SDL_SetRenderClipRect(renderer_, nullptr)) SDL_Log("worldview: %s", SDL_GetError());
    flushBuild();
    slot.period = animated ? static_cast<std::uint8_t>(animPeriod_) : 1;
    slot.generation = pages_->generation();
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
    const int row = block / n; // whole blocks
    const auto by = static_cast<float>(row);
    return {c.x0 + bx * b, c.y0 + by * b, c.x0 + (bx + 1) * b, c.y0 + (by + 1) * b};
}

std::uint64_t blockTag(CellKey key, int block) {
    return (packCell(key) << 2) | static_cast<std::uint64_t>(block);
}

} // namespace

bool WorldView::tilesAnimated(const FRect& px) {
    // Asked of the map's chunks, each of which knows whether any of its terrain moves (worked
    // out once): a cell is said to move a little more often than it does (a chunk's worth),
    // which costs it a second slot and nothing else. Asking the tiles themselves cost as much
    // as drawing them, for every coarse cell that came into view.
    if (chunkMoves_.empty()) {
        chunkMoves_.assign(static_cast<std::size_t>(map_.chunksX()) *
                               static_cast<std::size_t>(map_.chunksY()),
                           false);
        for (int y = 0; y < map_.height(); ++y)
            for (int x = 0; x < map_.width(); ++x) {
                const int t = map_.terrainAt({x, y});
                if (t != world::kNone && sprites_->terrain(t).fps > 0)
                    chunkMoves_[static_cast<std::size_t>((y >> kChunkShift) * map_.chunksX() +
                                                         (x >> kChunkShift))] = true;
            }
    }
    const TileRect all = tilesUnder(grown(px, sprites_->groundReach()), iso_);
    // Beyond the grid the sea runs on, and moves if the sea does.
    if (!map_.bounds().contains(all) && sea_ >= 0 && sprites_->terrain(sea_).animated())
        return true;
    const TileRect tiles = all.clipped(map_.bounds());
    if (tiles.empty()) return false;
    for (int cy = tiles.y0 >> kChunkShift; cy <= (tiles.y1 - 1) >> kChunkShift; ++cy)
        for (int cx = tiles.x0 >> kChunkShift; cx <= (tiles.x1 - 1) >> kChunkShift; ++cx)
            if (chunkMoves_[static_cast<std::size_t>(cy * map_.chunksX() + cx)]) return true;
    return false;
}

bool WorldView::cellWhole(CellKey k, int* over) {
    if (over != nullptr) *over = -1;
    const int si = cells_.find(packCell(k));
    if (si < 0 || !cells_.slot(si).ready) return false;
    if (k.level == 0 || cells_.slot(si).period <= 1) return true;
    const int oi = cells_.find(packCell(objectsKey(k)));
    if (oi < 0 || !cells_.slot(oi).ready) return false;
    if (over != nullptr) *over = oi;
    return true;
}

void WorldView::requestImpostor(CellKey key, int si, int rank) {
    const int n = blocksPerSide(key.level);
    for (int b = 0; b < n * n; ++b) {
        const FRect r = blockRect(key, b);
        prep_->request({blockTag(key, b), gatherTiles(r, sprites_->itemSpan(), iso_), r}, false);
    }
    // Where the cell has water, its ground and what stands on it go into a slot each
    // (cells.hpp): the later steps of the water are then grounds only.
    int objects = -1;
    bool moves = false;
    {
        const Timed timed(stats_.buildMs);
        moves = animPeriod_ > 1 && tilesAnimated(cellRect(key));
    }
    if (moves) {
        const std::uint64_t ok = packCell(objectsKey(key));
        objects = cells_.peek(ok);
        if (objects < 0) objects = cells_.acquire(ok, rank == kRankView ? 0 : 1);
        if (objects >= 0) {
            cells_.slot(objects).ready = false;
            cells_.slot(objects).complete = true;
        }
    }
    CellSlot& slot = cells_.slot(si);
    slot.complete = true;
    slot.period = objects >= 0 ? static_cast<std::uint8_t>(animPeriod_) : 1;
    building_.push_back({key, si, 0, rank, objects, false});
}

void WorldView::flushBuild() {
    // A build is handed to the driver at once, so its share of the work is timed with the
    // build and held to the build's budget, not found in whatever is drawn next. Not on SDL's
    // gpu driver: there every flush sends the frame's whole vertex store again (and makes
    // another copy of it the first time a frame flushes that often: 50 ms and more in one
    // frame), and nothing is saved by it, the work being done when the frame is submitted.
    if (gpuDriver_) return;
    if (!SDL_FlushRenderer(renderer_)) SDL_Log("worldview: %s", SDL_GetError());
}

void WorldView::halveInto(int si, int level, int block) {
    // Each halving averages 2 x 2 texels: 1024 -> 512 for level 1, and -> 512 -> 256 for level 2.
    plain(); // (targets are copied as they are, not decoded)
    const CellSlot& slot = cells_.slot(si);
    const int n = blocksPerSide(level);
    const int dst = tuning::kCellTexels / n;
    const Target* src = &scratch_;
    int size = tuning::kImpostorBlock;
    while (size / 2 > dst) {
        if (!SDL_SetRenderTarget(renderer_, half_.texture.get()))
            SDL_Log("worldview: %s", SDL_GetError());
        batch_.use(src->texture.get(), SDL_BLENDMODE_NONE, SDL_SCALEMODE_LINEAR);
        const int half = size / 2; // whole texels
        const auto hs = static_cast<float>(half);
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
    const int col = block % n; // whole blocks
    const int row = block / n;
    batch_.quad(SDL_FRect{static_cast<float>(slot.x + col * dst),
                          static_cast<float>(slot.y + row * dst), static_cast<float>(dst),
                          static_cast<float>(dst)},
                {0, 0, static_cast<float>(size) / static_cast<float>(src->w),
                 static_cast<float>(size) / static_cast<float>(src->h)},
                kWhite);
    batch_.flush();
}

void WorldView::drawBlock(const Building& b, int block, const Gathered& g) {
    // The block at full resolution with everything static, then halved with filtering into its
    // share of the slot. A cell with water: the ground into its slot, then what stands on it
    // (shadows and objects over nothing) into the objects layer's.
    const Timed timed(stats_.buildMs);
    const int before = batch_.drawCalls();
    batch_.flush();
    const int size0 = tuning::kImpostorBlock;
    drawingBlock_ = true; // (shadows take the stepped sun: this picture is cached)
    ensure(scratch_, size0, size0);
    ensure(scratchShadow_, size0, size0);
    ensure(half_, size0 / 2, size0 / 2);
    const FRect r = blockRect(b.key, block);
    const Xform x{{r.x0, r.y0}, 1.0f, SDL_SCALEMODE_NEAREST};
    const auto clear = [&] {
        if (!SDL_SetRenderTarget(renderer_, scratch_.texture.get()) ||
            !SDL_SetRenderDrawColorFloat(renderer_, 0, 0, 0, 0) || !SDL_RenderClear(renderer_))
            SDL_Log("worldview: impostor: %s", SDL_GetError());
    };
    clear();
    bool complete = drawTiles(r, x, 0, nullptr);
    if (b.objects >= 0) {
        batch_.flush();
        halveInto(b.slot, b.key.level, block);
        clear();
    }
    complete &= drawShadows(g, r, x, scratchShadow_, scratch_, false);
    for (const std::uint32_t i : g.order) complete &= drawElem(g.elems[i], x, 0);
    drawingBlock_ = false;
    batch_.flush();
    halveInto(b.objects >= 0 ? b.objects : b.slot, b.key.level, block);
    flushBuild();
    CellSlot& slot = cells_.slot(b.slot);
    slot.complete = slot.complete && complete;
    ++stats_.blocksBuilt;
    stats_.buildDrawCalls += batch_.drawCalls() - before;
}

void WorldView::drawGroundBlock(CellKey key, int si, int block) {
    const Timed timed(stats_.buildMs);
    const int before = batch_.drawCalls();
    batch_.flush();
    const int size0 = tuning::kImpostorBlock;
    ensure(scratch_, size0, size0);
    ensure(half_, size0 / 2, size0 / 2);
    const FRect r = blockRect(key, block);
    if (!SDL_SetRenderTarget(renderer_, scratch_.texture.get()) ||
        !SDL_SetRenderDrawColorFloat(renderer_, 0, 0, 0, 0) || !SDL_RenderClear(renderer_))
        SDL_Log("worldview: impostor: %s", SDL_GetError());
    // Half a step in, so rounding never lands on the step before.
    const float at = animFps_ > 0 ? (static_cast<float>(key.frame) + 0.5f) / animFps_ : 0.0f;
    const bool complete = drawTiles(r, {{r.x0, r.y0}, 1.0f, SDL_SCALEMODE_NEAREST}, at, nullptr);
    batch_.flush();
    halveInto(si, key.level, block);
    flushBuild();
    CellSlot& slot = cells_.slot(si);
    slot.complete = slot.complete && complete;
    ++stats_.blocksBuilt;
    stats_.buildDrawCalls += batch_.drawCalls() - before;
}

double WorldView::buildLimit(int rank) const {
    if (!async_) return 1e9;
    // A moving view needs its ring soon: it builds at the pace of what is needed.
    const bool moving = velocity_.x != 0 || velocity_.y != 0;
    if (rank == kRankView || (rank == kRankRing && moving)) return tuning::kBuildMsNeeded;
    // A destination is not seen yet (a veil is over it, or the zoom is still on its way): it
    // is built in the time the frame leaves, never slower than its floor.
    const double room = tuning::kFrameCpuRoomMs - frameCost_;
    if (rank == kRankArrival)
        return std::clamp(room, tuning::kBuildMsArrivalMin, tuning::kBuildMsNeeded);
    return std::clamp(room, tuning::kBuildMsAheadMin, tuning::kBuildMsAhead);
}

bool WorldView::buildSpent(int rank) const {
    if (stats_.buildMs >= buildLimit(rank)) return true;
    // On SDL's gpu driver a build's cost is not in its time (nothing is handed over until the
    // frame is: flushBuild) but in the passes it adds to the frame, each a change of target:
    // a count holds it instead.
    return gpuDriver_ && async_ &&
           stats_.cellsBuilt + stats_.blocksBuilt >=
               (rank == kRankView ? tuning::kGpuBuildsNeeded : tuning::kGpuBuildsAhead);
}

void WorldView::progressImpostors() {
    // Blocks whose gathers are back are drawn, the cells the view waits for first, while the
    // frame's build time lasts.
    std::ranges::sort(building_, [](const Building& a, const Building& b) {
        return a.rank != b.rank ? a.rank < b.rank : packCell(a.key) < packCell(b.key);
    });
    for (auto it = building_.begin(); it != building_.end();) {
        Building& b = *it;
        const int n = blocksPerSide(b.key.level);
        const std::uint32_t all = (1u << (n * n)) - 1;
        // Looking the cell up keeps its slot from being reused while it fills in.
        const bool alive = cells_.find(packCell(b.key)) == b.slot;
        for (int k = 0; k < n * n; ++k) {
            const std::uint32_t bit = 1u << k;
            if ((b.done & bit) != 0) continue;
            if (alive && buildSpent(b.rank)) break;
            if (!b.ground && !prep_->take(blockTag(b.key, k), block_)) continue;
            b.done |= bit;
            if (alive && b.ground) drawGroundBlock(b.key, b.slot, k);
            if (alive && !b.ground) drawBlock(b, k, block_);
        }
        if (b.done != all) {
            ++it;
            continue;
        }
        if (alive) {
            CellSlot& s = cells_.slot(b.slot);
            s.ready = true;
            s.generation = pages_->generation();
            if (b.objects >= 0) {
                CellSlot& o = cells_.slot(b.objects);
                o.ready = true;
                o.generation = s.generation;
            }
            ++stats_.impostorsBuilt;
        }
        it = building_.erase(it);
    }
    // What is built ahead waits its turn anew each frame.
    for (Building& b : building_) b.rank = kRankAhead;
}

int WorldView::cellFrame(int level, int cx, int cy, int ahead) {
    // A cell's first build (step 0) tells whether anything in it moves.
    const int si = cells_.find(packCell({level, cx, cy, 0}));
    if (si < 0 || !cells_.slot(si).ready) return 0;
    const int period = cells_.slot(si).period;
    return period > 1 ? static_cast<int>((animStep_ + static_cast<std::uint64_t>(ahead)) %
                                         static_cast<std::uint64_t>(period))
                      : 0;
}

void WorldView::wantCells(const FRect& rect, int level, int rank) {
    forEachCell(rect, level, [&](CellKey k) {
        // Out of view any step of a cell's water will do (its first exists once it is built):
        // only what is seen is kept step by step, so the loop costs slots where it shows.
        // A coarse cell with water is its ground and its objects layer: both are kept.
        if (level > 0) {
            const int first = cells_.peek(packCell(k));
            if (first >= 0 && cells_.slot(first).period > 1)
                wants_.push_back({objectsKey(k), rank});
        }
        if (rank != kRankView) {
            wants_.push_back({k, rank});
            return;
        }
        // A coarse view on the move asks only for a cell's first step: a cell that has just
        // come in may soon be gone, and each further step of its water is its whole ground
        // drawn again (a quarter-scale pan over the sea cost half as much again for it). Its
        // water moves with the steps it has (shownSlot) and gets the rest when the view rests.
        const bool moving = velocity_.x != 0 || velocity_.y != 0;
        if (moving && level > 0) {
            wants_.push_back({k, rank});
            return;
        }
        k.frame = cellFrame(level, k.cx, k.cy, 0);
        wants_.push_back({k, rank});
        // The next step is built before its turn comes; the rest of the loop is kept while
        // there is room, so a loop that fits is built once.
        const int next = cellFrame(level, k.cx, k.cy, 1);
        if (next == k.frame) return;
        // While the view moves, a cell that has just come in is one that may soon be gone: the
        // other steps of its water are built in the time frames leave (it shows the step it
        // has meanwhile), not at the pace of what is needed.
        wants_.push_back({{k.level, k.cx, k.cy, next}, moving ? kRankAhead : kRankRing});
        for (int f = 0; f < animPeriod_; ++f)
            if (f != k.frame && f != next) wants_.push_back({{k.level, k.cx, k.cy, f}, kRankAhead});
    });
}

void WorldView::planCells(int level, const FRect& view, const ViewSpec& spec, const FRect& seen) {
    wants_.clear();
    wantCells(view, level, kRankView);
    // Everything else is work ahead of need: synchronous runs build exactly what they show.
    if (!async_) return;
    const Vec2 screen = spec.screen;
    if (spec.heading && lodFor(spec.arrivalScale) != Lod::Overview) {
        // A zoom or a journey under way: its destination is built while it is on its way.
        const float k = 0.5f / spec.arrivalScale;
        const Lod to = lodFor(spec.arrivalScale);
        wantCells({spec.arrival.x - screen.x * k, spec.arrival.y - screen.y * k,
                   spec.arrival.x + screen.x * k, spec.arrival.y + screen.y * k},
                  to == Lod::Native ? 0 : (to == Lod::Half ? 1 : 2), kRankArrival);
    }
    // The ring around the view, leaning the way the view moves.
    const auto cell = static_cast<float>(cellPx(level));
    const float ring = cell * static_cast<float>(tuning::kCellRing);
    const float reach = cell * static_cast<float>(tuning::kCellAheadMax);
    const Vec2 lead{std::clamp(velocity_.x * tuning::kCellAheadFrames, -reach, reach),
                    std::clamp(velocity_.y * tuning::kCellAheadFrames, -reach, reach)};
    wantCells({view.x0 - ring + std::min(0.0f, lead.x), view.y0 - ring + std::min(0.0f, lead.y),
               view.x1 + ring + std::max(0.0f, lead.x), view.y1 + ring + std::max(0.0f, lead.y)},
              level, kRankRing);
    // The wider levels, where a turn of the wheel about the pointer would show them: zooming
    // out finds its cells already there.
    for (int l = level + 1; l <= 2; ++l)
        wantCells(zoomedAbout(seen, spec.pointer, spec.scale, 1.0f / static_cast<float>(1 << l)), l,
                  kRankAhead);
}

void WorldView::buildCells() {
    const auto stale = [&](int si) {
        const CellSlot& s = cells_.slot(si);
        return !s.complete && s.generation != pages_->generation();
    };
    progressImpostors();
    // Each cell once, at its most urgent rank, in order of need: the view, a destination, the
    // ring, the wider levels.
    std::ranges::sort(wants_, [](const CellWant& a, const CellWant& b) {
        const std::uint64_t ka = packCell(a.key);
        const std::uint64_t kb = packCell(b.key);
        return ka != kb ? ka < kb : a.rank < b.rank;
    });
    const auto dup =
        std::ranges::unique(wants_, {}, [](const CellWant& w) { return packCell(w.key); });
    wants_.erase(dup.begin(), dup.end());
    std::ranges::sort(wants_, [](const CellWant& a, const CellWant& b) {
        return a.rank != b.rank ? a.rank < b.rank : packCell(a.key) < packCell(b.key);
    });
    // No more is wanted than the cache holds (impostors filling in keep their slots too): what
    // is left out is the least urgent, and nothing wanted is ever pushed out by something else
    // wanted, so the cache never churns.
    const std::size_t room =
        cells_.capacity() > building_.size() ? cells_.capacity() - building_.size() : 0;
    if (wants_.size() > room) {
        stats_.prefetchPending += static_cast<int>(wants_.size() - room);
        wants_.resize(room);
    }
    for (const CellWant& w : wants_) (void)cells_.find(packCell(w.key));
    // What is missing first, then what is shown but stale (a new season, month, snow or sun
    // step): a stale cell stays on screen while it waits, a missing one is a hole.
    for (const bool redraw : {false, true})
        for (const CellWant& w : wants_) {
            if (w.key.frame == kObjectsFrame) continue; // built with its cell; wanted so it is kept
            const std::uint64_t key = packCell(w.key);
            int si = cells_.peek(key);
            const auto inFlight = std::ranges::find(building_, w.key, &Building::key);
            if (inFlight != building_.end()) {
                if (redraw) continue;
                inFlight->rank = std::min(inFlight->rank, w.rank);
                if (w.rank != kRankView) ++stats_.prefetchPending;
                continue;
            }
            // A coarse cell's first key stands for all of it: it is rebuilt if its objects layer
            // was let go.
            const bool whole = w.key.level == 0 || w.key.frame != 0 || cellWhole(w.key);
            const bool shown = si >= 0 && cells_.slot(si).ready && whole;
            if (shown && (!redraw || !stale(si))) continue;
            if (!shown && redraw) continue;
            if (redraw && buildSpent(kRankAhead)) continue; // at the ahead pace
            if (w.rank != kRankView) ++stats_.prefetchPending;
            // What is built ahead leaves alone what the last frame showed (a stand-in, a step of
            // the water's loop).
            const std::uint64_t spare = w.rank == kRankView ? 0 : 1;
            if (w.key.level == 0) {
                if (buildSpent(w.rank)) continue;
                if (si < 0) si = cells_.acquire(key, spare);
                if (si < 0) continue;
                buildGround(w.key, si);
                if (w.rank != kRankView) --stats_.prefetchPending;
                continue;
            }
            if (async_ && static_cast<int>(building_.size()) >= tuning::kImpostorCellsInFlight)
                continue;
            if (si < 0) {
                si = cells_.acquire(key, spare);
                if (si < 0) continue;
                cells_.slot(si).ready = false;
            }
            if (w.key.frame != 0) {
                // A later step of a cell's water: its ground again, nothing gathered.
                cells_.slot(si).complete = true;
                building_.push_back({w.key, si, 0, w.rank, -1, true});
            } else {
                requestImpostor(w.key, si, w.rank);
            }
        }
    // Synchronous gathers are back at once: draw them now.
    if (!async_) progressImpostors();
}

int WorldView::shownSlot(CellKey k) {
    if (k.level > 0 && !cellWhole({k.level, k.cx, k.cy, 0})) return -1;
    int si = cells_.find(packCell(k));
    if (si >= 0 && cells_.slot(si).ready) return si;
    // Moving water whose step is not built yet keeps its last one: the nearest step before.
    const int first = cells_.find(packCell({k.level, k.cx, k.cy, 0}));
    if (first < 0 || !cells_.slot(first).ready) return -1;
    const int period = cells_.slot(first).period;
    for (int back = 1; back < period; ++back) {
        si = cells_.find(packCell({k.level, k.cx, k.cy, (k.frame + period - back) % period}));
        if (si >= 0 && cells_.slot(si).ready) return si;
    }
    return first;
}

bool WorldView::nativeMostlyReady(const FRect& view) {
    int cells = 0;
    int built = 0;
    forEachCell(view, 0, [&](CellKey k) {
        const int si = cells_.peek(packCell(k));
        ++cells;
        built += si >= 0 && cells_.slot(si).ready ? 1 : 0;
    });
    const TileRect need = gatherTiles(view, sprites_->itemSpan(), iso_).clipped(map_.bounds());
    const TileRect have = need.clipped(regionRect_);
    const auto area = [](const TileRect& r) {
        return r.empty() ? 0.0f : static_cast<float>(r.x1 - r.x0) * static_cast<float>(r.y1 - r.y0);
    };
    return static_cast<float>(built) >= tuning::kNativeReadyShare * static_cast<float>(cells) &&
           area(have) >= tuning::kNativeReadyShare * area(need);
}

bool WorldView::cellsReady(int level, const FRect& view) {
    bool ready = true;
    forEachCell(view, level, [&](CellKey k) { ready = ready && cellWhole(k); });
    return ready;
}

void WorldView::drawCells(int level, const FRect& view, const Xform& x) {
    plain(); // (what follows is not decoded)
    keys_.clear();
    forEachCell(view, level, [&](CellKey k) {
        k.frame = cellFrame(level, k.cx, k.cy, 0);
        keys_.push_back(k);
    });
    if (!SDL_SetRenderTarget(renderer_, view_.texture.get()))
        SDL_Log("worldview: %s", SDL_GetError());
    // Cells never overlap, so they go page by page: one draw per cache page. A cell not built
    // yet shows its coarser level, or the overview underneath.
    const Vec2 side = CellCache::pageSize();
    composite_.clear();
    float pendingArea = 0;
    for (const CellKey& k : keys_) {
        int si = shownSlot(k);
        CellKey from = k;
        const bool pending = si < 0;
        for (int l = level + 1; l <= 2 && si < 0; ++l) {
            from = {l, k.cx >> (l - level), k.cy >> (l - level), 0};
            si = cellWhole(from) ? cells_.find(packCell(from)) : -1;
        }
        int over = -1;
        if (si >= 0 && from.level > 0) (void)cellWhole({from.level, from.cx, from.cy, 0}, &over);
        if (si >= 0) composite_.push_back({k, from, si, over});
        if (!pending) continue;
        // Only what the window shows counts as seen (the target is a few px larger).
        const FRect r = cellRect(k);
        const float w = std::min(r.x1, lastView_.x1) - std::max(r.x0, lastView_.x0);
        const float h = std::min(r.y1, lastView_.y1) - std::max(r.y0, lastView_.y0);
        if (w <= 0 || h <= 0) continue;
        ++stats_.cellsPending;
        pendingArea += w * h;
        if (si < 0) ++stats_.cellsBare;
    }
    stats_.pendingShare =
        pendingArea / ((lastView_.x1 - lastView_.x0) * (lastView_.y1 - lastView_.y0));
    if (stats_.cellsBare > 0) drawOverview(view, x);
    std::ranges::sort(composite_, [&](const Composite& a, const Composite& b) {
        const int sa = a.from.level - a.key.level;
        const int sb = b.from.level - b.key.level;
        const int pa = cells_.slot(a.slot).page;
        const int pb = cells_.slot(b.slot).page;
        if (pa != pb) return pa < pb;
        return sa != sb ? sa < sb : packCell(a.key) < packCell(b.key);
    });
    const auto lay = [&](const Composite& c, int slot) {
        const CellSlot& s = cells_.slot(slot);
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
    };
    for (const Composite& c : composite_) lay(c, c.slot);
    // What stands on the cells with water, over whichever step of their ground was laid.
    for (const Composite& c : composite_)
        if (c.over >= 0) lay(c, c.over);
}

void WorldView::drawOverview(const FRect& view, const Xform& x) {
    plain(); // (what follows is not decoded)
    Overview& ov = overview();
    while (!ov.upload(renderer_) && !async_) {}
    SDL_Texture* t = ov.texture();
    if (t == nullptr) return;
    const OverviewImage& img = ov.image();
    const float k = 1.0f / img.scale;
    // Only the texels under the view, whole ones so that the picture lies where it did.
    const TexelSpan span = texelsUnder(img.origin, k, img.w, img.h, view);
    if (span.empty()) return;
    const auto at = [&](int tx, int ty) {
        return x.apply(
            {img.origin.x + static_cast<float>(tx) * k, img.origin.y + static_cast<float>(ty) * k});
    };
    const Vec2 p0 = at(span.x0, span.y0);
    const Vec2 p1 = at(span.x1, span.y1);
    const auto w = static_cast<float>(img.w);
    const auto h = static_cast<float>(img.h);
    batch_.use(t, SDL_BLENDMODE_BLEND, SDL_SCALEMODE_LINEAR);
    batch_.quad(SDL_FRect{p0.x, p0.y, p1.x - p0.x, p1.y - p0.y},
                {static_cast<float>(span.x0) / w, static_cast<float>(span.y0) / h,
                 static_cast<float>(span.x1) / w, static_cast<float>(span.y1) / h},
                kWhite);
}

void WorldView::drawBackdrops(const FRect& view, const Xform& x, bool night) {
    // Strips of 16 edge tiles behind the north (tx = 0) and east (ty = 0) edges; the north ones
    // are the same art mirrored, running the other way.
    constexpr int kSegment = 16;
    const auto n = static_cast<std::size_t>(night ? 1 : 0);
    for (int edge = 0; edge < 2; ++edge) {
        const int len = edge == 0 ? map_.width() : map_.height();
        const auto firstOf = [&](int k) {
            return edge == 0 ? TilePos{k * kSegment, 0} : TilePos{0, k * kSegment};
        };
        // A segment's strips, or none: where the edge is water the land behind is out of sight
        // (a strip there stood in the sea).
        const auto stripsOf = [&](int k) -> const std::vector<SpriteRef>* {
            if (k < 0 || k * kSegment >= len) return nullptr;
            const TilePos first = firstOf(k);
            const int region = map_.regionAt(first);
            if (region < 0) return nullptr;
            const auto& strips = backdrops_[static_cast<std::size_t>(region)][n];
            if (strips.empty()) return nullptr;
            for (int i = 0; i < kSegment && i + k * kSegment < len; ++i) {
                const TilePos p = edge == 0 ? TilePos{first.x + i, 0} : TilePos{0, first.y + i};
                if (sprites_->terrain(map_.terrainAt(p)).water) return nullptr;
            }
            return &strips;
        };
        for (int k = 0; k * kSegment < len; ++k) {
            const std::vector<SpriteRef>* strips = stripsOf(k);
            if (strips == nullptr) continue;
            const TilePos first = firstOf(k);
            const SpriteRef& s = (*strips)[tileHash(first.x, first.y, 11) % strips->size()];
            const Vec2 w = iso_.toWorld(first);
            const Vec2 a{w.x, w.y - static_cast<float>(map_.level(first) * lvl_)};
            const FRect box =
                edge == 0 ? FRect{a.x - s.ox, a.y - s.oy, a.x - s.ox + s.w, a.y - s.oy + s.h}
                          : FRect{a.x - (s.w - s.ox), a.y - s.oy, a.x + s.ox, a.y - s.oy + s.h};
            if (!box.overlaps(view)) continue;
            // The strips' ends are cut square: where a run of them ends, its end fades into the
            // haze (QA7 V7-007), in slices across the strip (its left end is segment k's).
            const bool fadeIn = stripsOf(k - 1) == nullptr;
            const bool fadeOut = stripsOf(k + 1) == nullptr;
            if (!fadeIn && !fadeOut) {
                (void)put(s, a, x, kWhite, SDL_BLENDMODE_BLEND, edge == 1);
                continue;
            }
            constexpr int kSlices = 16;
            for (int i = 0; i < kSlices; ++i) {
                const float f0 = static_cast<float>(i) / kSlices;
                const float f1 = static_cast<float>(i + 1) / kSlices;
                const float mid = (f0 + f1) * 0.5f;
                const auto ramp = [](float t) {
                    t = std::clamp(t / tuning::kBackdropFade, 0.0f, 1.0f);
                    return t * t * (3.0f - 2.0f * t);
                };
                const float alpha =
                    (fadeIn ? ramp(mid) : 1.0f) * (fadeOut ? ramp(1.0f - mid) : 1.0f);
                if (alpha <= 0.0f) continue;
                SpriteRef slice = s;
                slice.w = s.w * (f1 - f0);
                slice.ox = s.ox - s.w * f0;
                slice.uv.u0 = s.uv.u0 + (s.uv.u1 - s.uv.u0) * f0;
                slice.uv.u1 = s.uv.u0 + (s.uv.u1 - s.uv.u0) * f1;
                (void)put(slice, a, x, {1, 1, 1, alpha}, SDL_BLENDMODE_BLEND, edge == 1);
            }
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
        // The shader path samples the world target: in the format its shaders read.
        t.texture.reset(SDL_CreateTexture(
            renderer_,
            post_ && (&t == &view_ || &t == &shadow_) ? gpu::Post::kFormat : kTextureFormat,
            SDL_TEXTUREACCESS_TARGET, t.w, t.h));
        if (!t.texture ||
            !SDL_SetTextureBlendMode(t.texture.get(), SDL_BLENDMODE_BLEND_PREMULTIPLIED))
            SDL_Log("worldview: cannot create a target: %s", SDL_GetError());
    }
}

std::size_t WorldView::targetBytes() const {
    std::size_t n = 0;
    for (const Target* t :
         {&view_, &shadow_, &scratch_, &scratchShadow_, &half_, &rainPicture_, &snowPicture_})
        if (t->texture) n += static_cast<std::size_t>(t->w) * static_cast<std::size_t>(t->h) * 4;
    return n + (post_ ? post_->bytes() : 0);
}

void WorldView::fullQuad(int w, int h, SDL_FColor c, SDL_BlendMode mode) {
    plain(); // (what follows is not decoded)
    const SpriteRef& white = sprites_->white();
    SDL_Texture* t = pages_->texture(white.page);
    if (t == nullptr) return;
    batch_.use(t, mode, SDL_SCALEMODE_NEAREST);
    batch_.quad(SDL_FRect{0, 0, static_cast<float>(w), static_cast<float>(h)}, white.uv, c);
}

std::optional<WorldView::Picked> WorldView::pick(Vec2 px) const {
    // What is drawn there, nearest first, by the drawing's own order (draw-order.md 4.5): the
    // topmost element that draws a pixel under the pointer decides, and opens its card if it has
    // one (a landmark's box covers far more than its pixels). Where nothing is drawn, the
    // nearest footprint under the pointer at its level does: a building's bare ground (a walk
    // floor's courtyard, the open end of a building site) is the building's.
    const Elem* ground = nullptr;
    for (auto it = region_.order.rbegin(); it != region_.order.rend(); ++it) {
        const Elem& e = region_.elems[*it];
        if (e.ground || e.home) continue;
        const OrderItem& o = region_.items[*it];
        const FRect& b = o.screen;
        const bool inBox = px.x >= b.x0 && px.x < b.x1 && px.y >= b.y0 && px.y < b.y1;
        if (e.figure) {
            if (inBox) return Picked{true, figureOf_[e.item]};
            continue;
        }
        const SpriteRef& s = e.piece >= 0 ? e.look->pieces[static_cast<std::size_t>(e.piece)]
                                          : e.look->base.f.front();
        if (inBox && pages_->drawsAt(s, px.x - b.x0, px.y - b.y0)) {
            if (map_.info(map_.items()[e.item]).card.empty()) return std::nullopt;
            return Picked{false, e.item};
        }
        if (ground != nullptr) continue;
        const float lift = iso_.toWorld(e.tile).y - e.anchor.y;
        const Vec2 t = iso_.toWorld(o.box.foot.x0, o.box.foot.y0);
        const Vec2 r = iso_.toWorld(o.box.foot.x1, o.box.foot.y0);
        const Vec2 bt = iso_.toWorld(o.box.foot.x1, o.box.foot.y1);
        const Vec2 l = iso_.toWorld(o.box.foot.x0, o.box.foot.y1);
        const auto edge = [&](Vec2 a, Vec2 c) {
            return a.y + (c.y - a.y) * (px.x - a.x) / (c.x - a.x);
        };
        if (px.x >= l.x && px.x < r.x && px.y >= (px.x < t.x ? edge(l, t) : edge(t, r)) - lift &&
            px.y <= (px.x < bt.x ? edge(l, bt) : edge(bt, r)) - lift)
            ground = &e;
    }
    if (ground == nullptr || map_.info(map_.items()[ground->item]).card.empty())
        return std::nullopt;
    return Picked{false, ground->item};
}

void WorldView::drawWeatherGround(const FRect& view, const Xform& x) {
    plain(); // (what follows is not decoded)
    // Cloud shadows: soft dark blobs drifting with the cells (showers darker); then the wet ground
    // where showers passed, darkened tile by tile. The home's own scene shades its land.
    const float blobR = blob_.w * 0.5f;
    // (The shader path draws the clouds' shadows from the same cells itself.)
    const bool none = post_ || clouds_ == gpu::Clouds::Off;
    for (const WeatherCell& c : none ? std::span<const WeatherCell>{} : weather_->cells()) {
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

void WorldView::buildRainPicture(Target& t, const Sprite& s, std::uint32_t salt) {
    plain(); // (the home atlas's sprite as it is)
    const int pane = tuning::kRainPane;
    ensure(t, pane * tuning::kRainLayers, pane);
    if (!t.texture || !SDL_SetRenderTarget(renderer_, t.texture.get()) ||
        !SDL_SetRenderDrawColorFloat(renderer_, 0, 0, 0, 0) || !SDL_RenderClear(renderer_)) {
        SDL_Log("worldview: rain picture: %s", SDL_GetError());
        t.texture.reset();
        return;
    }
    // As many streaks over a tile's worth of the pane as fall on a tile, shared out among the
    // densities.
    const float perTile = static_cast<float>(tuning::kRainStreaksPerTile);
    const int count = static_cast<int>(perTile * static_cast<float>(pane * pane) /
                                       (iso_.tileW() * iso_.tileH() * 0.5f)) /
                      tuning::kRainLayers;
    const auto room = static_cast<std::uint32_t>(pane - static_cast<int>(s.w) + 1);
    // Copied, not blended: the picture keeps the art's own colour and alpha, and is drawn like
    // it (blending its mesh, whose corners differ, needs that on the software renderer).
    batch_.use(s.texture, SDL_BLENDMODE_NONE, SDL_SCALEMODE_NEAREST);
    for (int layer = 0; layer < tuning::kRainLayers; ++layer)
        for (int k = 0; k < count; ++k) {
            const std::uint32_t h = tileHash(layer, k, salt);
            const float px = static_cast<float>(layer * pane) + static_cast<float>(h % room);
            const float py = static_cast<float>((h >> 12) % static_cast<std::uint32_t>(pane));
            // A streak over the pane's lower edge goes on at its top: the pane tiles.
            for (const float y : {py, py - static_cast<float>(pane)})
                if (y + s.h > 0) batch_.quad(SDL_FRect{px, y, s.w, s.h}, s.uv, kWhite);
        }
    batch_.flush();
    if (!SDL_SetRenderTarget(renderer_, nullptr)) SDL_Log("worldview: %s", SDL_GetError());
}

void WorldView::drawRain(const FRect& view, const Xform& x, double now) {
    plain(); // (what follows is not decoded)
    // Rain (or snow) falls where a shower is. It is one picture of streaks at fixed places over
    // a pane that tiles the world, falling by being scrolled, drawn as a coarse mesh whose
    // corners ask the showers how hard it rains there: a few hundred quads for a whole view in
    // the rain, where a quad per streak was five thousand and a fifth of the frame's work.
    // Nothing is stored, so any view of the world has its rain.
    const bool snow = weather_->snow();
    const Target& picture = snow ? snowPicture_ : rainPicture_;
    if (!picture.texture) return;
    // Only the tiles under a shower are looked at: none in view (most frames) costs nothing.
    const TileRect inView = tilesUnder(view, iso_).clipped(map_.bounds());
    TileRect tiles{inView.x1, inView.y1, inView.x0, inView.y0};
    for (const WeatherCell& c : weather_->cells()) {
        if (!c.rain) continue;
        const TileRect r = TileRect{static_cast<int>(std::floor(c.centre.x - c.radius)),
                                    static_cast<int>(std::floor(c.centre.y - c.radius)),
                                    static_cast<int>(std::ceil(c.centre.x + c.radius)) + 1,
                                    static_cast<int>(std::ceil(c.centre.y + c.radius)) + 1}
                               .clipped(inView);
        if (r.empty()) continue;
        tiles = {std::min(tiles.x0, r.x0), std::min(tiles.y0, r.y0), std::max(tiles.x1, r.x1),
                 std::max(tiles.y1, r.y1)};
    }
    if (tiles.x0 >= tiles.x1 || tiles.y0 >= tiles.y1) return;
    // The showers that reach those tiles, once: each corner then asks only them, and without a
    // square root (intensity x (1 - d^2 / r^2), as WeatherField::rainAt gives).
    showers_.clear();
    for (const WeatherCell& c : weather_->cells()) {
        if (!c.rain || c.centre.x + c.radius < static_cast<float>(tiles.x0) ||
            c.centre.x - c.radius > static_cast<float>(tiles.x1) ||
            c.centre.y + c.radius < static_cast<float>(tiles.y0) ||
            c.centre.y - c.radius > static_cast<float>(tiles.y1))
            continue;
        showers_.push_back({c.centre, 1.0f / (c.radius * c.radius), c.intensity()});
    }
    // How hard it rains at a grid point: nothing below the strength that counts as rain, off
    // the grid, or over the home (its scene has its own rain).
    const auto rainAt = [&](Vec2 t) {
        const TilePos tile{static_cast<int>(std::floor(t.x)), static_cast<int>(std::floor(t.y))};
        if (!map_.inBounds(tile) || hole_.tiles.contains(tile)) return 0.0f;
        float r = 0;
        for (const Shower& sh : showers_) {
            const float dx = t.x - sh.centre.x;
            const float dy = t.y - sh.centre.y;
            const float d2 = (dx * dx + dy * dy) * sh.invR2;
            if (d2 < 1) r = std::max(r, sh.intensity * (1.0f - d2));
        }
        return r < ::lc::tuning::kRainThreshold ? 0.0f : std::min(1.0f, r);
    };
    const int pane = tuning::kRainPane;
    const int mw = tuning::kRainMeshW;
    const int mh = tuning::kRainMeshH;
    // How far the picture has fallen, in whole px, and how many panes have gone by: a pane
    // keeps its look all the way down.
    const double fallen = now * static_cast<double>(snow ? tuning::kSnowFall : tuning::kRainFall);
    const auto passed = static_cast<std::int64_t>(std::floor(fallen / pane));
    const auto scroll = static_cast<int>(fallen - static_cast<double>(passed) * pane);
    // The mesh: columns at whole multiples of its width, rows riding down with the picture.
    const int i0 = static_cast<int>(std::floor(view.x0 / static_cast<float>(mw)));
    const int i1 = static_cast<int>(std::ceil(view.x1 / static_cast<float>(mw)));
    const int j0 = static_cast<int>(
        std::floor((view.y0 - static_cast<float>(scroll)) / static_cast<float>(mh)));
    const int j1 = static_cast<int>(
        std::ceil((view.y1 - static_cast<float>(scroll)) / static_cast<float>(mh)));
    const int cols = i1 - i0;
    const int rows = j1 - j0;
    if (cols <= 0 || rows <= 0) return;
    // A streak is drawn somewhere along its fall above the ground it lands on: what is seen at
    // a point rains on the ground half a fall below it.
    const float below = iso_.tileH() * tuning::kRainFallTiles * 0.5f;
    const auto stride = static_cast<std::size_t>(cols + 1);
    rainMesh_.resize(stride * static_cast<std::size_t>(rows + 1));
    for (int j = 0; j <= rows; ++j)
        for (int i = 0; i <= cols; ++i) {
            const Vec2 w{static_cast<float>((i0 + i) * mw),
                         static_cast<float>((j0 + j) * mh + scroll)};
            rainMesh_[static_cast<std::size_t>(j) * stride + static_cast<std::size_t>(i)] =
                rainAt(iso_.toTile({w.x, w.y + below}));
        }
    // Farther out a quarter of the streaks: as many on screen at any zoom.
    const int layers = res_ < 1.0f ? 1 : tuning::kRainLayers;
    const float strength = snow ? tuning::kSnowAlpha : tuning::kRainAlpha;
    const auto wrap = [](int v, int n) { return ((v % n) + n) % n; };
    const float texW = static_cast<float>(pane * tuning::kRainLayers);
    static constexpr int kQuad[6] = {0, 1, 2, 0, 2, 3};
    batch_.use(picture.texture.get(), SDL_BLENDMODE_BLEND, x.filter);
    for (int j = 0; j < rows; ++j)
        for (int i = 0; i < cols; ++i) {
            const std::size_t at =
                static_cast<std::size_t>(j) * stride + static_cast<std::size_t>(i);
            const float r[4] = {rainMesh_[at], rainMesh_[at + 1], rainMesh_[at + stride + 1],
                                rainMesh_[at + stride]};
            if (std::max({r[0], r[1], r[2], r[3]}) <= 0) continue;
            const int wx = (i0 + i) * mw;
            const int py = (j0 + j) * mh; // in the picture as it falls
            const int inX = wrap(wx, pane);
            const int inY = wrap(py, pane);
            // Which of the pictures each pane shows first differs from pane to pane, so the
            // eye finds no repeat.
            const auto turn =
                tileHash((wx - inX) / pane, static_cast<int>((py - inY) / pane - passed), 41u);
            const Vec2 p0 = x.apply({static_cast<float>(wx), static_cast<float>(py + scroll)});
            const Vec2 p1 =
                x.apply({static_cast<float>(wx + mw), static_cast<float>(py + scroll + mh)});
            const float v0 = static_cast<float>(inY) / static_cast<float>(pane);
            const float v1 = static_cast<float>(inY + mh) / static_cast<float>(pane);
            for (int layer = 0; layer < layers; ++layer) {
                // Each density comes in over its own share of the strength: a shower's edge
                // thins out and fades instead of ending.
                float a[4];
                float most = 0;
                for (int c = 0; c < 4; ++c) {
                    a[c] = std::clamp(r[c] * static_cast<float>(layers) - static_cast<float>(layer),
                                      0.0f, 1.0f) *
                           strength;
                    most = std::max(most, a[c]);
                }
                if (most <= 0) break;
                const int which = static_cast<int>((turn + static_cast<std::uint32_t>(layer)) %
                                                   static_cast<std::uint32_t>(tuning::kRainLayers));
                const float u0 = static_cast<float>(which * pane + inX) / texW;
                const float u1 = static_cast<float>(which * pane + inX + mw) / texW;
                const SDL_Vertex v[4] = {{{p0.x, p0.y}, {1, 1, 1, a[0]}, {u0, v0}},
                                         {{p1.x, p0.y}, {1, 1, 1, a[1]}, {u1, v0}},
                                         {{p1.x, p1.y}, {1, 1, 1, a[2]}, {u1, v1}},
                                         {{p0.x, p1.y}, {1, 1, 1, a[3]}, {u0, v1}}};
                batch_.triangles(v, 4, kQuad, 6);
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
        const std::optional<SpriteRef>& gl = sprites_->item(it).glow;
        if (!gl) continue; // glows() said it has one
        const Vec2 w = iso_.toWorld(TilePos{it.x, it.y});
        glow_[count[chunkOf(it)]++] = {
            &*gl,
            {w.x, w.y - map_.surfaceZ(
                            {static_cast<float>(it.x) + 0.5f, static_cast<float>(it.y) + 0.5f})},
            static_cast<std::uint32_t>(&it - map_.items().data())};
    }
}

void WorldView::drawCoarseGlow(const FRect& view, const Xform& x, float strength) {
    plain(); // (what follows is not decoded)
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
                if (box.overlaps(view) && glowing(s.item))
                    lit_.push_back({r.page, i, &r, s.anchor});
            }
        }
    drawLit(x, g);
}

void WorldView::drawLit(const Xform& x, SDL_FColor strength) {
    // Light adds up the same in any order: page by page, so a view with lamps on four pages
    // makes four draws for them, where the painter's order made one wherever the page changed
    // (most of the draw calls of a city at night).
    std::ranges::sort(lit_, {}, [](const Lit& l) { return std::pair{l.page, l.seq}; });
    for (const Lit& l : lit_) (void)put(*l.sprite, l.anchor, x, strength, SDL_BLENDMODE_ADD);
    lit_.clear();
    batch_.flush();
}

void WorldView::reserveFor(Vec2 screen) {
    cells_.reserve(cellBudget(screen));
    // The frame's targets at the window's size and a little over (the look's path has made
    // its own, for the whole display). The target is the window's size at every zoom but the
    // whole ones above 1x, where it is smaller.
    if (post_) {
        warmTarget(view_.texture.get());
        return;
    }
    const int w = static_cast<int>(std::ceil(screen.x)) + tuning::kViewTargetSpare;
    const int h = static_cast<int>(std::ceil(screen.y)) + tuning::kViewTargetSpare;
    ensure(view_, w, h);
    ensure(shadow_, w, h);
}

std::size_t WorldView::cellBudget(Vec2 screen) {
    // Cells per level over a window (every level's cells cover the same share of it), the view's
    // own level with its ring, and the two wider levels: tuning.hpp says why.
    const auto side = static_cast<float>(tuning::kCellTexels);
    const double nx = std::ceil(screen.x / side) + 1;
    const double ny = std::ceil(screen.y / side) + 1;
    const double ring = 2.0 * tuning::kCellRing;
    const double view = nx * ny;
    const double around = (nx + ring) * (ny + ring) - view;
    // Land: a slot a cell (the view, its ring, two wider levels), kCellSpare times. Water at
    // its most (the half-scale level in view, all of it sea): the view's ground once per step
    // and its objects layer, two slots a cell for the ring and for the wider level.
    const double land = (view + around + 2 * view) * tuning::kCellSpare;
    const double sea = view * (tuning::kCellPeriodMax + 1) + 2 * around + 2 * view;
    const double slots = std::max(land, sea);
    return std::clamp(static_cast<std::size_t>(slots) * tuning::kMiB, tuning::kCellBudgetMin,
                      tuning::kCellBudgetMax);
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
    if (stats_.placeholders == 0) return; // nothing to look for among thousands of elements
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
    // Ground and impostors hold the season's looks: drawn again, the old shown until then.
    staleCells();
}

void WorldView::staleCells() {
    cells_.staleAll();
}

void WorldView::setCalendar(int month, float dayFraction) {
    dayFraction_ = std::clamp(dayFraction, 0.0f, 1.0f);
    if (!decoder_) return;
    adoptSeasonField();
    if (pages_->homePackedReady() != homeReadySeen_) {
        homeReadySeen_ = pages_->homePackedReady();
        staleCells(); // the corner's art from its packed twin from now on
    }
    const std::vector<ClimateDef>& climates = map_.content().home().climates;
    bool stale = false;
    if (month != month_) {
        month_ = month;
        remapRows_.assign(static_cast<std::size_t>(gpu::kRampIds * gpu::Decoder::kClimates), 0);
        for (int c = 0; c < gpu::Decoder::kClimates; ++c) {
            const auto row = std::span<std::uint8_t, gpu::kRampIds>(
                remapRows_.data() + static_cast<std::size_t>(c * gpu::kRampIds), gpu::kRampIds);
            // (The last row stays as it is: the home's art.)
            if (static_cast<std::size_t>(c) < climates.size() && c < gpu::Decoder::kClimates - 1)
                gpu::remapRow(rampSeasons_, climates[static_cast<std::size_t>(c)], month, row);
            else
                for (int i = 0; i < gpu::kRampIds; ++i)
                    row[static_cast<std::size_t>(i)] = static_cast<std::uint8_t>(i);
        }
        decoder_->setRemap(remapRows_, rampSeasons_.water);
        stale = true;
    }
    // Snow builds and thaws over a morning in steps: cells are drawn again at each step, only
    // in a month where some climate's snow line moves.
    const int step = static_cast<int>(std::min(dayFraction_, gpu::kSnowMorning) / gpu::kSnowStep);
    if (step != snowStep_) {
        snowStep_ = step;
        for (const ClimateDef& c : climates) {
            const auto n = static_cast<int>(c.snowLine.size());
            if (n > 0 && month_ >= 0 &&
                c.snowLine[static_cast<std::size_t>(month_ % n)] !=
                    c.snowLine[static_cast<std::size_t>((month_ + n - 1) % n)])
                stale = true;
        }
    }
    if (stale) staleCells();
}

int WorldView::climateOf(TilePos p) const {
    const int r = map_.inBounds(p) ? map_.regionAt(p) : -1;
    return r >= 0 && static_cast<std::size_t>(r) < regionClimate_.size() &&
                   regionClimate_[static_cast<std::size_t>(r)] != gpu::kNoClimate
               ? regionClimate_[static_cast<std::size_t>(r)]
               : fallbackClimate_;
}

void WorldView::startSeasonField() {
    // The land's levels and the climates' borders, once, on a worker: it reads the map's
    // immutable layers (the home's tiles wait for it: homeTerrainChanged).
    seasonJob_ = std::async(std::launch::async, [this] {
        const int w = map_.width();
        const int h = map_.height();
        const auto n = static_cast<std::size_t>(w) * static_cast<std::size_t>(h);
        std::vector<std::uint8_t> climate(n);
        std::vector<std::uint8_t> level(n);
        std::vector<std::uint8_t> natural(n);
        // Built ground is paved, or raised on masonry faces (ashlar, brick, dressed travertine):
        // a terrace, a podium, a platform; earth, rock and tufa faces are the land's own.
        const auto built = [](std::string_view face) {
            return face.ends_with(".ashlar") || face.ends_with(".brick") ||
                   face.ends_with(".travertine");
        };
        for (int y = 0; y < h; ++y)
            for (int x = 0; x < w; ++x) {
                const TilePos p{x, y};
                const auto i = static_cast<std::size_t>(y) * static_cast<std::size_t>(w) +
                               static_cast<std::size_t>(x);
                climate[i] = static_cast<std::uint8_t>(climateOf(p));
                level[i] = static_cast<std::uint8_t>(map_.level(p));
                const int t = map_.terrainAt(p);
                if (t == world::kNone) continue;
                const world::TerrainInfo& info = map_.terrainInfo(t);
                const auto aux = static_cast<std::size_t>(world::auxOf(map_.levelByte(p)));
                const bool masonry = aux < info.faces.size() && built(info.faces[aux]);
                natural[i] = !info.paved && !masonry ? 1 : 0;
            }
        return gpu::seasonField(w, h, climate, level, natural);
    });
}

void WorldView::adoptSeasonField() {
    if (!seasonJob_.valid() ||
        seasonJob_.wait_for(std::chrono::seconds(0)) != std::future_status::ready)
        return;
    seasonField_ = seasonJob_.get();
    staleCells(); // the borders blend and platforms lose their own snow line from now on
}

std::optional<GroundDecode> WorldView::homeGroundDecode() {
    SDL_Texture* page = pages_->texture(PageAtlas::kHomePage);
    if (!decoder_ || page == nullptr || !pages_->homePackedReady()) return std::nullopt;
    if (homePacked_.empty()) homePacked_ = pages_->homePackedSprites();
    // The home's ground is the home's art (its own looks: the identity row) under the home
    // climate's snow at the land's level, as the world draws the corner's land round it.
    const TilePos centre{(hole_.tiles.x0 + hole_.tiles.x1) / 2,
                         (hole_.tiles.y0 + hole_.tiles.y1) / 2};
    seasonAt(centre);
    seasonCtx_.share = 0;
    seasonCtx_.other = -1;
    const SDL_FColor c = packedColour({1, 1, 1, 1}, true, false);
    GroundDecode d;
    d.page = page;
    d.packed = &homePacked_;
    d.use = [this](Batch& b, bool on) { decoder_->use(b, on); };
    d.replace = decoder_->replace();
    d.row = c.g;
    d.snow = c.b;
    if (post_) {
        d.stamp = [this](Batch& b, bool on) { post_->stamp(b, on); };
        d.stampBlend = post_->stampBlend();
    }
    return d;
}

SDL_BlendMode WorldView::coverBlend() const {
    return post_ ? post_->coverBlend() : SDL_BLENDMODE_BLEND;
}

void WorldView::seasonAt(TilePos p) {
    lookSeason_ = season_;
    if (!decoder_) return;
    const int own = climateOf(p);
    SeasonCtx ctx{own, own, -1, 0, map_.inBounds(p) ? map_.level(p) : 0};
    if (map_.inBounds(p) && !seasonField_.empty()) {
        const gpu::SeasonTile& st =
            seasonField_[static_cast<std::size_t>(p.y) * static_cast<std::size_t>(map_.width()) +
                         static_cast<std::size_t>(p.x)];
        ctx.level = st.landLevel;
        // The home climate's land keeps its own drawn looks (as the home's scene draws it, so
        // the corner and the land round it agree): its neighbours carry the whole blend on
        // their side, the home's season full at the border and fading out.
        const bool home = own == homeClimate_;
        const bool beside = st.other == homeClimate_;
        if (st.other != gpu::kNoClimate && !home) {
            // A smooth noise a few tiles across breaks the band's edge; each tile then takes
            // the neighbour's grass and leaves by its share, in patches of a few tiles (a noise
            // finer still: a tile by tile choice was a checkerboard, QA7 V7-005). Two octaves
            // (11 and 4 tiles): the band meanders instead of following the line.
            const auto octave = [&](int cell, std::uint32_t salt) {
                const auto lattice = [&](int x, int y) {
                    return static_cast<float>(tileHash(x, y, salt) % 1024u) / 1023.0f;
                };
                const int cx = p.x >= 0 ? p.x / cell : (p.x - cell + 1) / cell;
                const int cy = p.y >= 0 ? p.y / cell : (p.y - cell + 1) / cell;
                const float fx = static_cast<float>(p.x - cx * cell) / static_cast<float>(cell);
                const float fy = static_cast<float>(p.y - cy * cell) / static_cast<float>(cell);
                const float sx = fx * fx * (3 - 2 * fx);
                const float sy = fy * fy * (3 - 2 * fy);
                return (lattice(cx, cy) * (1 - sx) + lattice(cx + 1, cy) * sx) * (1 - sy) +
                       (lattice(cx, cy + 1) * (1 - sx) + lattice(cx + 1, cy + 1) * sx) * sy;
            };
            const float noise = octave(11, 11) * 0.7f + octave(4, 17) * 0.3f - 0.5f;
            ctx.other = st.other;
            ctx.share = gpu::otherShare(st.distance, noise) * (beside ? 2.0f : 1.0f);
            const float patch = octave(3, 13) * 0.65f + octave(2, 19) * 0.35f;
            if ((patch - 0.5f) * 2.0f + 0.5f < ctx.share) ctx.climate = st.other;
        }
    }
    seasonCtx_ = ctx;
    // In a border's band in the snowy season every tile draws the plain looks, its snow the
    // blended cover grain by grain (drawn snow is one climate's: the home's snowy winter grass
    // would end in a line, or in a patchwork of whole tiles, at the border). The other seasons
    // keep their looks there (a plain look may be a winter one: QA7 V7-004's snowy peaks).
    const std::vector<SeasonDef>& seasons = map_.content().home().seasons;
    const bool snowy = season_ >= 0 && std::cmp_less(season_, seasons.size()) &&
                       seasons[static_cast<std::size_t>(season_)].snow;
    lookSeason_ = snowy && ctx.other >= 0 && ctx.share > 0.0f ? -1 : season_;
}

SDL_FColor WorldView::packedColour(SDL_FColor c, bool homeArt, bool mirrored) const {
    // The decode reads the tint's lightness, the climate's row and the snow lying there. The
    // home's art carries its seasons in its own looks (as the home's scene draws it): its row
    // leaves every ramp as it is, and only the snow is the climate's.
    const std::vector<ClimateDef>& climates = map_.content().home().climates;
    // Snow blends across a border by the share (snowy hills fade into a green plain).
    float snow = 0;
    const float day = static_cast<float>(snowStep_) * gpu::kSnowStep;
    const auto cover = [&](int k) {
        return month_ >= 0 && k >= 0 && static_cast<std::size_t>(k) < climates.size()
                   ? gpu::snowCover(climates[static_cast<std::size_t>(k)], month_, day,
                                    seasonCtx_.level)
                   : 0.0f;
    };
    const float own = cover(seasonCtx_.own);
    const float other = seasonCtx_.other >= 0 ? cover(seasonCtx_.other) : 0.0f;
    const float s = seasonCtx_.share;
    // Where only one side has snow, it thins out to nothing at the border on its own side: a
    // blend never carries snow onto land whose climate has none (QA7 V7-008). The home's drawn
    // snow is the exception: the land round it takes it, so the corner is one snow with it.
    if (seasonCtx_.other == homeClimate_ || (own > 0.0f && other > 0.0f))
        snow = own * (1 - s) + other * s;
    else
        snow = own * std::max(0.0f, 1.0f - 2.0f * s);
    // (Home art taking a neighbour's season is drawn plain: it takes that climate's row.)
    const int row =
        homeArt && lookSeason_ == season_ ? gpu::Decoder::kClimates - 1 : seasonCtx_.climate;
    // Red: the tint's lightness in its lower half, 0.5 more when drawn mirrored (the decode swaps
    // the normal's axes then).
    return {(0.299f * c.r + 0.587f * c.g + 0.114f * c.b) * 0.49f + (mirrored ? 0.5f : 0.0f),
            static_cast<float>(row) / 255.0f, snow, c.a};
}

void WorldView::plain() {
    if (decoder_) decoder_->use(batch_, false);
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
            // Every step of the cell's water that is cached (a coarse cell's objects layer is
            // redone with its first).
            for (k.frame = 0; k.frame < animPeriod_; ++k.frame) {
                const int si = cells_.find(packCell(k));
                if (si < 0) continue;
                CellSlot& slot = cells_.slot(si);
                slot.complete = false;
                slot.generation = ~0u;
            }
        });
}

void WorldView::jumped(const WorldCamera& camera) {
    jumped(camera.centre());
}

void WorldView::jumped(Vec2 centre) {
    std::array<world::RegionWeight, 16> w{};
    const int n = map_.themeWeights(iso_.toTile(centre), w);
    theme_.reset(std::span(w).first(static_cast<std::size_t>(n)));
    places_.reset(regionUnder(map_, iso_, lvl_, centre));
    themed_ = true;
    jumped_ = true;
}

void WorldView::draw(const WorldCamera& camera, double clock, float dt, double now) {
    ViewSpec v{camera.centre(),  camera.scale(),        camera.screen(), camera.flying(),
               camera.arrival(), camera.arrivalScale(), camera.centre()};
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
    const Vec2 screen = camera.screen;
    const Vec2 c = camera.centre;
    const Vec2 topLeft{c.x - screen.x * 0.5f / s, c.y - screen.y * 0.5f / s};
    const FRect seen{topLeft.x, topLeft.y, topLeft.x + screen.x / s, topLeft.y + screen.y / s};
    // How fast the view moves, for building ahead of it; a jump is no motion.
    snapExposure_ = jumped_ || !lastView_.overlaps(seen);
    velocity_ = jumped_ || !lastView_.overlaps(seen)
                    ? Vec2{}
                    : Vec2{(seen.x0 + seen.x1 - lastView_.x0 - lastView_.x1) * 0.5f,
                           (seen.y0 + seen.y1 - lastView_.y0 - lastView_.y1) * 0.5f};
    jumped_ = false;
    animStep_ = animFps_ > 0 ? static_cast<std::uint64_t>(now * animFps_) : 0;
    const Lod want = lodFor(s);
    // Objects gathered for this view meanwhile (a destination's, on arrival) are taken over
    // before the level is chosen, so an arrival that was made ready is shown at once.
    if (want == Lod::Native) adoptRegion(seen);
    // The native level needs its ground cells and its objects. While most of them are still on
    // their way (a zoom in that arrived at once, a jump) the half-scale impostors stay up,
    // magnified, if they are whole: the previous level until the new one is there, never a hole.
    // A view that only lacks a strip at its leading edge (a fast pan) stays native: a cell not
    // built yet shows its coarser level by itself, which is far less to see than the whole view
    // changing level for a frame.
    Lod lod = want;
    if (async_ && want == Lod::Native && !nativeMostlyReady(seen) && cellsReady(1, seen))
        lod = Lod::Half;
    stats_.lod = lod;
    stats_.lodHeld = lod != want;
    // At 2x and 3x the native level is drawn at the zoom's resolution: sprites stay whole art
    // pixels, while moving things are placed to the window's pixel.
    const float res = lod == Lod::Native    ? std::max(1.0f, std::floor(s + 1e-3f))
                      : lod == Lod::Half    ? 0.5f
                      : lod == Lod::Quarter ? 0.25f
                                            : std::min(overview().image().scale, s);
    // The target's origin sits on its own pixel grid, so cached cells land on whole texels.
    const float px = 1.0f / res;
    const Vec2 origin{std::floor(topLeft.x / px) * px - px, std::floor(topLeft.y / px) * px - px};
    res_ = res;
    viewW_ = static_cast<int>(std::ceil(screen.x / s * res)) + 3;
    viewH_ = static_cast<int>(std::ceil(screen.y / s * res)) + 3;
    ensure(view_, viewW_, viewH_);
    if (post_) post_->prepare(view_.w, view_.h);
    if (lod == Lod::Native) ensure(shadow_, viewW_, viewH_);
    const Xform xf{origin, res, res < 1.0f ? SDL_SCALEMODE_LINEAR : SDL_SCALEMODE_NEAREST};
    const FRect view{origin.x, origin.y, origin.x + static_cast<float>(viewW_) * px,
                     origin.y + static_cast<float>(viewH_) * px};

    // Themes and light.
    std::array<world::RegionWeight, 16> weights{};
    const int nw = map_.themeWeights(iso_.toTile(c), weights);
    const auto ws = std::span(weights).first(static_cast<std::size_t>(nw));
    const int here = regionUnder(map_, iso_, lvl_, c);
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
    if (!post_ && decoder_ && sunStep_ != -1) {
        // Classic on this driver decodes the art as baked.
        const float up[3] = {0, 0, 1};
        decoder_->setSun(up, 0, 0);
        sunStep_ = -1;
        staleCells();
    }
    if (post_) {
        gradeGpu(clock, now, light, lod, origin);
        sunGpu(clock);
        if (lod != Lod::Overview) refreshWater(view);
    }
    lastView_ = seen;

    // Streaming: the sets of the view, and of where it is heading.
    const float half = 0.5f / camera.arrivalScale;
    const FRect arrival{camera.arrival.x - screen.x * half, camera.arrival.y - screen.y * half,
                        camera.arrival.x + screen.x * half, camera.arrival.y + screen.y * half};
    const bool arriving = camera.heading && lodFor(camera.arrivalScale) != Lod::Overview;
    if (want != Lod::Overview) wantSets(view, want == Lod::Native);
    if (arriving) wantSets(arrival, lodFor(camera.arrivalScale) == Lod::Native);
    cells_.reserve(cellBudget(screen));
    {
        const Timed timed(stats_.uploadMs);
        plain(); // (a synchronous run may make and touch a page slot here)
        pages_->update(now);
        stats_.uploadBytes = pages_->uploadedBytes();
    }
    if (overview_) {
        while (!overview_->upload(renderer_) && !async_) {}
    }

    if (!SDL_SetRenderTarget(renderer_, view_.texture.get()) ||
        !SDL_SetRenderDrawColorFloat(renderer_, 0, 0, 0, 0) || !SDL_RenderClear(renderer_))
        SDL_Log("worldview: %s", SDL_GetError());
    batch_.setBand(bandTag(Band::FarBackdrop));
    if (lod != Lod::Overview) drawBackdrops(view, xf, light.night > 0.5f);
    // Cached cells hold the bands from the ground to the depth band, baked in their order.
    batch_.setBand(bandTag(Band::Ground));
    const auto levelOf = [](Lod l) { return l == Lod::Native ? 0 : (l == Lod::Half ? 1 : 2); };
    if (want != Lod::Overview) {
        // What to build is planned for the level the view wants, even while a coarser one
        // stands in for it.
        planCells(levelOf(want), lod == want ? view : seen, camera, seen);
        // A level standing in is wanted as long as it is shown.
        if (lod != want) wantCells(view, levelOf(lod), kRankView);
        buildCells();
    }
    if (lod == Lod::Overview) {
        drawOverview(view, xf);
    } else {
        drawCells(levelOf(lod), view, xf);
    }
    batch_.flush();
    if (!SDL_SetRenderTarget(renderer_, view_.texture.get()))
        SDL_Log("worldview: %s", SDL_GetError());
    // The game's scene works only while its home is in view.
    const bool home = lod != Lod::Overview && !hole_.empty() && hole_.screen.overlaps(view);
    // The world's cloud shadows go under the home's ground: the home's scene shades its own land.
    batch_.setBand(bandTag(Band::Shadows));
    if (weather_ != nullptr && lod != Lod::Overview) drawWeatherGround(view, xf);
    if (hooks.ground && home) {
        plain();
        hooks.ground(frame);
    }
    if (post_ && home) markHomeWater(view, xf);
    // A zoom or a journey down to the native level gathers its destination on the way.
    if (arriving && lodFor(camera.arrivalScale) == Lod::Native) gatherAhead(arrival);
    if (want == Lod::Native) updateRegion(lod == want ? view : seen);
    bool homeDrawn = false;
    lastLod_ = lod;
    if (lod == Lod::Native) {
        stats_.regionElements = static_cast<int>(region_.elems.size());
        stats_.regionShort = !regionRect_.contains(
            gatherTiles(view, sprites_->itemSpan(), iso_).clipped(map_.bounds()));
        prepareActors(view, lod);
        batch_.setBand(bandTag(Band::Shadows));
        (void)drawShadows(region_, view, xf, shadow_, view_, true, merge_.visible());
        batch_.setBand(bandTag(Band::Depth));
        stats_.spritesCulled = static_cast<int>(region_.order.size() - merge_.visible().size());
        // The painter's order, drawn page by page wherever the picture is the same for it
        // (page_runs.hpp): what does not meet on screen need not wait its turn.
        openRuns();
        for (const ActorMerge::Step& st : merge_.sequence()) {
            if (st.actor) {
                runWhat_ = kRunActor;
                drawActor(actorOf_[st.index], xf);
                continue;
            }
            const Elem& e = region_.elems[st.index];
            if (e.home) {
                // The home's scene takes its turn between what is behind it and in front.
                closeRuns(xf.filter);
                if (hooks.objects && home) {
                    plain();
                    hooks.objects(frame);
                }
                homeDrawn = true;
                openRuns();
                continue;
            }
            runWhat_ = e.figure   ? kRunFigure
                       : e.ground ? kRunTerrain | static_cast<std::uint32_t>(map_.terrainAt(e.tile))
                                  : map_.items()[e.item].info;
            if (!drawElem(e, xf, static_cast<float>(now))) ++stats_.spritesMissing;
            ++stats_.spritesDrawn;
            if (e.look != nullptr && e.look->look == Look::Placeholder) ++stats_.placeholders;
        }
        closeRuns(xf.filter);
    } else if (lod != Lod::Overview) {
        // Coarser levels have no live objects of their own: people go over the impostors, cut
        // where something in front of them covers them.
        prepareActors(view, lod);
        batch_.setBand(bandTag(Band::Depth));
        for (const std::uint32_t a : coarse_) drawActor(a, xf);
    } else {
        actorCount_ = 0;
        actorDraw_.clear();
    }
    batch_.flush();
    // The home's objects go over the impostors at the coarser levels.
    if (!homeDrawn && hooks.objects && home) {
        plain();
        hooks.objects(frame);
    }
    batch_.setBand(bandTag(Band::Weather));
    if (weather_ != nullptr && (lod == Lod::Native || lod == Lod::Half)) drawRain(view, xf, now);
    // Grading, then what glows (drawn after it, additively). The shader path grades in its
    // final pass and lights and glows in targets of its own.
    plain();
    batch_.setBand(bandTag(Band::Grading));
    if (post_)
        lightGpu(view, xf, lod, light.glow, hooks, frame, home);
    else if (hooks.light && home)
        hooks.light(frame);
    else
        fullQuad(viewW_, viewH_, ambient, SDL_BLENDMODE_MOD);
    batch_.setBand(bandTag(Band::Glow));
    if (lod != Lod::Native && light.glow > 0.01f)
        drawCoarseGlow(view, xf,
                       light.glow * (lod == Lod::Overview ? tuning::kOverviewGlow : 1.0f));
    if (lod == Lod::Native && light.glow > 0.01f) {
        const SDL_FColor g{light.glow, light.glow, light.glow, 1};
        for (const std::uint32_t k : merge_.visible()) {
            const std::uint32_t i = region_.order[k];
            const Elem& e = region_.elems[i];
            if (e.first && e.look != nullptr && e.look->glow && glowing(e.item))
                lit_.push_back({e.look->glow->page, k, &*e.look->glow, e.anchor});
        }
        drawLit(xf, g);
    }
    plain();
    batch_.flush();
    if (hooks.glow && home)
        hooks.glow(
            post_ ? FrameInfo{post_->glow(), xf, view, viewW_, viewH_, lod, ambient, s, topLeft}
                  : frame);
    if (post_) bloomGpu(view, xf, lod, light.glow);

    // Onto the window: sky, the world, the haze.
    if (!SDL_SetRenderTarget(renderer_, out)) SDL_Log("worldview: %s", SDL_GetError());
    present_ = {origin, topLeft, s, res, light.skyTop, light.skyBottom, grade, screen, true};
    composite({1, 1}, false);
    if (hooks.overlay) {
        plain();
        hooks.overlay(frame);
    }

    stats_.drawCalls = batch_.drawCalls() - stats_.buildDrawCalls;
    stats_.cellsCached = cells_.cached();
    stats_.cellBytes = cells_.bytes();
    stats_.overviewBytes = overview_ && overview_->texture() != nullptr ? overview_->bytes() : 0;
    stats_.pages = pages_->stats();
    stats_.targetBytes = targetBytes();
}

float WorldView::partialAlpha(SDL_Rect window) {
    return alphaShare(window, 13, 246);
}

float WorldView::waterMarked(SDL_Rect window) {
    return alphaShare(window, 246, 253);
}

float WorldView::alphaShare(SDL_Rect window, Uint8 lo, Uint8 hi) {
    if (!present_.valid || !view_.texture) return 0;
    const Present& p = present_;
    const auto at = [&](float w, float topLeft, float origin) {
        return static_cast<int>(std::floor((w / p.scale + topLeft - origin) * p.res));
    };
    const int x0 = std::clamp(at(static_cast<float>(window.x), p.topLeft.x, p.origin.x), 0, viewW_);
    const int y0 = std::clamp(at(static_cast<float>(window.y), p.topLeft.y, p.origin.y), 0, viewH_);
    const int x1 =
        std::clamp(at(static_cast<float>(window.x + window.w), p.topLeft.x, p.origin.x), 0, viewW_);
    const int y1 =
        std::clamp(at(static_cast<float>(window.y + window.h), p.topLeft.y, p.origin.y), 0, viewH_);
    if (x1 <= x0 || y1 <= y0) return 0;
    SDL_Texture* was = SDL_GetRenderTarget(renderer_);
    if (!SDL_SetRenderTarget(renderer_, view_.texture.get())) return 0;
    const SDL_Rect r{x0, y0, x1 - x0, y1 - y0};
    const SurfacePtr px{SDL_RenderReadPixels(renderer_, &r)};
    if (!SDL_SetRenderTarget(renderer_, was)) SDL_Log("worldview: %s", SDL_GetError());
    if (!px) return 0;
    int in = 0;
    for (int y = 0; y < px->h; ++y)
        for (int x = 0; x < px->w; ++x) {
            Uint8 cr = 0, cg = 0, cb = 0, ca = 0;
            if (!SDL_ReadSurfacePixel(px.get(), x, y, &cr, &cg, &cb, &ca)) return 0;
            if (ca >= lo && ca <= hi) ++in;
        }
    return static_cast<float>(in) / static_cast<float>(px->w * px->h);
}

void WorldView::composite(Vec2 scale, bool smooth) {
    plain(); // (what follows is not decoded)
    if (!present_.valid) return;
    if (post_) {
        compositeGpu(scale, smooth);
        return;
    }
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
    batch_.setBand(bandTag(Band::Sky));
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
    // The world's picture, everything from the backdrop to the glow, over the sky.
    batch_.setBand(bandTag(Band::Ground));
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

TileRect WorldView::regionAround(const TileRect& need, float k) {
    const int gx = std::max(tuning::kRegionMinGrow,
                            static_cast<int>(static_cast<float>(need.x1 - need.x0) * k));
    const int gy = std::max(tuning::kRegionMinGrow,
                            static_cast<int>(static_cast<float>(need.y1 - need.y0) * k));
    return TileRect{need.x0 - gx, need.y0 - gy, need.x1 + gx, need.y1 + gy};
}

void WorldView::adoptRegion(const FRect& view) {
    const TileRect inMap = gatherTiles(view, sprites_->itemSpan(), iso_).clipped(map_.bounds());
    // A finished gather takes over when it covers the view (one overtaken by a jump is dropped).
    if (regionPending_ && prep_->take(kRegionTag, next_)) {
        regionPending_ = false;
        if (pendingRect_.contains(inMap)) {
            std::swap(region_, next_);
            regionRect_ = pendingRect_;
            stats_.regionRebuilt = true;
            mergeIndexed_ = false;
        }
    }
    // So does what was gathered ahead for a destination, once the view is there.
    if (aheadPending_ && prep_->take(kAheadTag, ahead_)) {
        aheadPending_ = false;
        aheadReady_ = true;
    }
    if (aheadReady_ && !regionRect_.contains(inMap) && aheadRect_.contains(inMap)) {
        std::swap(region_, ahead_);
        regionRect_ = aheadRect_;
        aheadReady_ = false;
        stats_.regionRebuilt = true;
        mergeIndexed_ = false;
    }
}

void WorldView::updateRegion(const FRect& view) {
    const TileRect need = gatherTiles(view, sprites_->itemSpan(), iso_);
    const FRect all{-1e9f, -1e9f, 1e9f, 1e9f};
    adoptRegion(view);
    if (!async_ && !regionRect_.intersects(need)) {
        // Nothing gathered here (a jump): synchronous runs gather before they draw. With a
        // worker the request below is back within a frame or two, and nothing blocks.
        regionRect_ = regionAround(need, tuning::kRegionGrow);
        const Timed timed(stats_.gatherMs);
        prep_->now(regionRect_, all, region_);
        stats_.regionRebuilt = true;
        mergeIndexed_ = false;
    } else if (!regionPending_ &&
               !regionRect_.contains(
                   regionAround(need, tuning::kRegionEarly).clipped(map_.bounds()))) {
        pendingRect_ = regionAround(need, tuning::kRegionGrow);
        prep_->request({kRegionTag, pendingRect_, all}, true);
        regionPending_ = true;
        // Synchronous gathering finishes at once.
        if (!async_) updateRegion(view);
    }
}

void WorldView::gatherAhead(const FRect& view) {
    const TileRect need = gatherTiles(view, sprites_->itemSpan(), iso_).clipped(map_.bounds());
    if (regionRect_.contains(need) || aheadPending_ || (aheadReady_ && aheadRect_.contains(need)) ||
        (regionPending_ && pendingRect_.contains(need)))
        return;
    aheadRect_ = regionAround(need, tuning::kRegionGrow);
    aheadReady_ = false;
    aheadPending_ = true;
    prep_->request({kAheadTag, aheadRect_, {-1e9f, -1e9f, 1e9f, 1e9f}}, true);
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
        merge_.index(region_.items, region_.order, region_.graph, tuning::kActorMergeCell);
        mergeIndexed_ = true;
    }
    if (life_ == nullptr || !looks_) {
        if (lod == Lod::Native) merge_.plan(region_.items, {}, view);
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
        const Vec2 w = iso_.toWorld(d.pos.x, d.pos.y);
        // The tiles under a view are a box twice the view: half of those gathered stand off
        // screen, and are passed over before anything is resolved for them.
        const float feetY = w.y - d.z;
        const bool near = w.x + actorReach_.right >= view.x0 && w.x - actorReach_.left <= view.x1 &&
                          feetY + actorReach_.down >= view.y0 && feetY - actorReach_.up <= view.y1;
        const auto look = !near || hole_.tiles.contains(t) ? std::nullopt : looks_->resolve(d);
        if (look) {
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
        }
        actorDraw_.push_back(ad);
        if (ad.sprite == nullptr) continue;
        const SpriteRef& s = *ad.sprite;
        const float x0 = ad.anchor.x - (ad.mirror ? s.w - s.ox : s.ox);
        FRect box{x0, ad.anchor.y - s.oy, x0 + s.w, ad.anchor.y - s.oy + s.h};
        // Art larger than anything seen so far widens the reach for the frames to come.
        const float side = std::max(s.ox, s.w - s.ox) + 1;
        actorReach_ = {std::max(actorReach_.left, side), std::max(actorReach_.right, side),
                       std::max(actorReach_.up, s.oy + 1),
                       std::max(actorReach_.down, s.h - s.oy + 1)};
        if (!box.overlaps(view)) continue;
        if (ad.goods != nullptr) box.y0 = std::min(box.y0, ad.goodsAt.y - ad.goods->oy);
        // Its box (draw-order.md §1.2): a small square round the feet, from the floor it stands
        // on to the top of what is drawn (goods and riders included: they go with it).
        const float f = tuning::kActorFoot;
        actorDraw_.back().box = makeBox({d.pos.x - f, d.pos.y - f, d.pos.x + f, d.pos.y + f}, d.z,
                                        d.z + (ad.anchor.y - box.y0),
                                        depthId(DepthKind::Actor, d.handle.index), iso_.hh);
        {
            // Zoomed out the impostor holds everything static: the rows of whoever stands behind
            // something in front of them are left out, as the native order would paint over
            // them. At the native level items are in the painter's order and only raised ground
            // (a terrace's edge, a hill) cuts.
            ActorDraw& c = actorDraw_.back();
            c.hidden = tops_->cut(c.box, c.anchor, box.y0, lod == Lod::Native);
            if (c.hidden.from <= box.y0 && c.hidden.to >= c.anchor.y) continue; // all of it
        }
        mergeActors_.push_back({actorDraw_.back().box, box, s.page});
        actorOf_.push_back(static_cast<std::uint32_t>(i));
    }
    ActorMerge& merge = lod == Lod::Native ? merge_ : coarseMerge_;
    if (lod != Lod::Native) coarseMerge_.index({}, {}, {}, tuning::kActorMergeCell);
    merge.plan(lod == Lod::Native ? std::span<const OrderItem>(region_.items)
                                  : std::span<const OrderItem>{},
               mergeActors_, view);
    float rank = 0;
    for (const ActorMerge::Step& st : merge.sequence())
        if (st.actor) {
            actorDraw_[actorOf_[st.index]].drawn = rank++;
            if (lod != Lod::Native) coarse_.push_back(actorOf_[st.index]);
        }
}

void WorldView::actorsAt(Vec2 px, std::vector<life::Handle>& out) const {
    out.clear();
    auto& hits = actorHits_; // kept: the pointer asks every frame it rests on the world
    hits.clear();
    for (std::size_t i = 0; i < actorDraw_.size(); ++i) {
        const ActorDraw& a = actorDraw_[i];
        if (a.sprite == nullptr || a.drawn < 0) continue;
        const SpriteRef& s = *a.sprite;
        const float x0 = a.anchor.x - (a.mirror ? s.w - s.ox : s.ox);
        // A little narrower than the sprite: what is clicked is the person, not the air beside.
        const float inset = s.w * 0.2f;
        if (px.x < x0 + inset || px.x >= x0 + s.w - inset || px.y < a.anchor.y - s.oy ||
            px.y >= a.anchor.y - s.oy + s.h)
            continue;
        if (px.y >= a.hidden.from && px.y < a.hidden.to) continue; // covered there
        // Frontmost first: the last drawn.
        hits.emplace_back(-a.drawn, actorBuf_[i].handle);
    }
    std::ranges::sort(hits, [](const auto& a, const auto& b) {
        return a.first != b.first ? a.first < b.first : a.second.index < b.second.index;
    });
    for (const auto& h : hits) out.push_back(h.second);
}

int WorldView::coarseActorsCovered(float px, std::string* first) const {
    constexpr int kRows = 40; // tiles in front whose art can reach back over someone
    int covered = 0;
    std::vector<world::DrawPiece> pieces; // a test's question, not a frame's: allocation is fine
    for (const std::uint32_t i : coarse_) {
        const life::DrawActor& d = actorBuf_[i];
        const ActorDraw& ad = actorDraw_[i];
        const TilePos t{static_cast<int>(std::floor(d.pos.x)),
                        static_cast<int>(std::floor(d.pos.y))};
        const float top = ad.anchor.y - (ad.box.z1 - ad.box.z0);
        map_.piecesIn(TileRect{t.x - 2, t.y - 2, t.x + kRows, t.y + kRows}.clipped(map_.bounds()),
                      pieces);
        float most = 0;
        for (const world::DrawPiece& p : pieces) {
            const world::Placed& it = map_.items()[p.item];
            if (hole_.tiles.contains(TilePos{it.x, it.y})) continue;
            const VariantLook& look = sprites_->item(it);
            const bool split = p.piece >= 0 && !look.pieces.empty();
            if (!split && look.base.empty()) continue;
            const SpriteRef& s =
                split ? look.pieces[static_cast<std::size_t>(p.piece)] : look.base.f.front();
            const TileRect r = split ? p.rect : it.rect();
            const float base = static_cast<float>(it.level * lvl_);
            const ZRange z =
                heightsOf(map_.geometry(it), map_.info(it), split ? p.piece : -1, s.oy);
            const DepthBox b =
                makeBox({static_cast<float>(r.x0), static_cast<float>(r.y0),
                         static_cast<float>(r.x1), static_cast<float>(r.y1)},
                        base + z.z0, base + z.z1, depthId(DepthKind::Item, p.item), iso_.hh);
            if (drawnBefore(b, ad.box)) continue;
            // Rows of the person drawn inside its silhouette at the person's column: the piece
            // tile by tile, each as tall as the art says it is there (a solid piece's tops).
            const world::GeomVariant* g = map_.geometry(it);
            const bool perTile = z.kind == ZRange::Kind::Solid && g != nullptr && g->topsW > 0;
            for (int ty = r.y0; ty < r.y1; ++ty)
                for (int tx = r.x0; tx < r.x1; ++tx) {
                    float z1 = b.z1;
                    if (perTile && tx - it.x < g->topsW) {
                        const auto at =
                            static_cast<std::size_t>((ty - it.y) * g->topsW + (tx - it.x));
                        if (at < g->tops.size()) z1 = base + static_cast<float>(g->tops[at]);
                    }
                    const RowBand sil =
                        silhouette(iso_,
                                   {static_cast<float>(tx), static_cast<float>(ty),
                                    static_cast<float>(tx + 1), static_cast<float>(ty + 1)},
                                   b.z0, std::max(z1, b.z0), ad.anchor.x);
                    if (sil.empty()) continue;
                    const auto overlap = [&](float from, float to) {
                        return std::max(0.0f, std::min(to, sil.to) - std::max(from, sil.from));
                    };
                    const float shown = ad.hidden.empty()
                                            ? overlap(top, ad.anchor.y)
                                            : overlap(top, std::min(ad.anchor.y, ad.hidden.from)) +
                                                  overlap(std::max(top, ad.hidden.to), ad.anchor.y);
                    if (shown > most && shown > px && first != nullptr && covered == 0)
                        *first = std::format(
                            "{} at ({:.2f}, {:.2f}) z {:.0f}: {:.0f} rows inside {} piece {} at "
                            "({}, {})",
                            life_->lifeWorld().data.kinds[d.kind].id, d.pos.x, d.pos.y, d.z, shown,
                            map_.info(it).id, p.piece, tx, ty);
                    most = std::max(most, shown);
                }
        }
        covered += most > px ? 1 : 0;
    }
    return covered;
}

int WorldView::coarseActorsOnItems() const {
    int on = 0;
    for (const std::uint32_t i : coarse_) {
        const life::DrawActor& d = actorBuf_[i];
        const TilePos t{static_cast<int>(std::floor(d.pos.x)),
                        static_cast<int>(std::floor(d.pos.y))};
        on += map_.inBounds(t) && map_.itemAt(t) >= 0 ? 1 : 0;
    }
    return on;
}

int WorldView::orderViolations(std::string* first) const {
    std::pair<DepthBox, DepthBox> pair;
    const int n =
        lastLod_ == Lod::Native
            ? lc::orderViolations(region_.items, mergeActors_, merge_.sequence(), false, &pair)
            : lc::orderViolations({}, mergeActors_, coarseMerge_.sequence(), false, &pair);
    const auto name = [&](const DepthBox& b) {
        const auto kind = static_cast<DepthKind>(b.id >> 56);
        const auto index = static_cast<std::uint32_t>((b.id >> 32) & 0xFFFFFFu);
        std::string what = kind == DepthKind::Item && index < map_.items().size()
                               ? map_.info(map_.items()[index]).id
                               : (kind == DepthKind::Actor ? "actor" : "element");
        return std::format("{} part {} [{:.1f},{:.1f}..{:.1f},{:.1f}] z {:.0f}..{:.0f}", what,
                           b.id & 0xFFFFFFFFu, b.foot.x0, b.foot.y0, b.foot.x1, b.foot.y1, b.z0,
                           b.z1);
    };
    if (n > 0 && first != nullptr)
        *first = "drawn first " + name(pair.first) + ", then " + name(pair.second);
    else if (region_.cycles > 0 && lastLod_ == Lod::Native && first != nullptr)
        *first = std::format("{} cycle(s) in the static order, the first broken at {}",
                             region_.cycles, name(region_.cycleAt));
    return n;
}

int WorldView::orderCycles() const {
    // The static sort's cycles are data faults; the merge's are stacked movers (a walker on a
    // deck over a boat), broken between the two actors and not counted here.
    return region_.cycles;
}

int WorldView::sunkActors(std::string* first) const {
    if (lastLod_ != Lod::Native || life_ == nullptr) return 0;
    const auto& kinds = life_->lifeWorld().data.kinds;
    int sunk = 0;
    for (const std::uint32_t i : actorOf_) {
        const life::DrawActor& d = actorBuf_[i];
        if (kinds[d.kind].sprite.starts_with("ship/")) continue;
        const TilePos t{static_cast<int>(std::floor(d.pos.x)),
                        static_cast<int>(std::floor(d.pos.y))};
        if (!map_.inBounds(t) || map_.itemAt(t) < 0) continue;
        const world::Placed& it = map_.items()[static_cast<std::size_t>(map_.itemAt(t))];
        const world::GeomVariant* g = map_.geometry(it);
        const world::ItemInfo& info = map_.info(it);
        const TilePos rel{t.x - it.x, t.y - it.y};
        int piece = -1;
        if (g != nullptr)
            for (std::size_t q = 0; q < g->pieces.size(); ++q)
                if (g->pieces[q].rect.contains(rel)) piece = static_cast<int>(q);
        const bool walkTile = g != nullptr ? std::ranges::find(g->walk, rel) != g->walk.end() ||
                                                 (g->walk.empty() && info.walkable)
                                           : info.walkable;
        if (!walkTile) continue;
        const ZRange z = heightsOf(g, info, piece, 0);
        // A floor or a deck (who walks under an overhead run stands on the ground).
        const bool stoodOn = z.kind == ZRange::Kind::Floor || z.kind == ZRange::Kind::Deck;
        // The tile's own floor: its walk_z, else (a kit deck) its tops.
        int floor = 0;
        bool known = false;
        if (g != nullptr)
            for (const auto& [wt, wz] : g->walkZ)
                if (wt == rel) {
                    floor = wz;
                    known = true;
                }
        if (!known && info.crossing && g != nullptr && g->topsW > 0 && rel.x < g->topsW &&
            static_cast<std::size_t>(rel.y * g->topsW + rel.x) < g->tops.size())
            floor = g->tops[static_cast<std::size_t>(rel.y * g->topsW + rel.x)];
        const auto surface = static_cast<float>(it.level * lvl_ + floor);
        if (!stoodOn || d.z + tuning::kDeckReach >= surface) continue;
        if (sunk++ == 0 && first != nullptr)
            *first = std::format("{} at ({:.2f}, {:.2f}) z {:.0f} on {} whose floor is at {:.0f}",
                                 kinds[d.kind].id, d.pos.x, d.pos.y, d.z, info.id, surface);
    }
    return sunk;
}

void WorldView::drawActor(std::uint32_t i, const Xform& x) {
    seasonCtx_ = {fallbackClimate_, fallbackClimate_, -1, 0, 0};
    lookSeason_ = season_; // people carry no grass or snow
    const ActorDraw& a = actorDraw_[i];
    if (putRows(*a.sprite, a.anchor, x, a.colour, a.mirror, a.hidden))
        ++stats_.actorsDrawn;
    else
        ++stats_.spritesMissing;
    if (a.goods != nullptr) (void)putRows(*a.goods, a.goodsAt, x, a.colour, false, a.hidden);
}

bool WorldView::putRows(const SpriteRef& s, Vec2 anchor, const Xform& x, SDL_FColor c, bool mirror,
                        RowBand hide) {
    if (hide.empty()) return put(s, anchor, x, c, SDL_BLENDMODE_BLEND, mirror);
    // Whole art rows of the sprite above and below the covered band.
    const float top = anchor.y - s.oy;
    const auto row = [&](float y) { return std::clamp(std::round(y - top), 0.0f, s.h); };
    const float r0 = row(hide.from);
    const float r1 = row(hide.to);
    const float x0 = anchor.x - (mirror ? s.w - s.ox : s.ox);
    bool ok = true;
    for (const auto& [from, to] : {std::pair{0.0f, r0}, std::pair{r1, s.h}}) {
        if (to <= from) continue;
        const std::array<Vec2, 4> q{
            {{x0, top + from}, {x0 + s.w, top + from}, {x0 + s.w, top + to}, {x0, top + to}}};
        ok &= putPoly(s, anchor, x, c, SDL_BLENDMODE_BLEND, mirror, q);
    }
    return ok;
}

void WorldView::drawActorShadows(const Xform& x) {
    plain(); // (what follows is not decoded)
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
    // The view itself is whole: its cells at its own level, its pages, its objects. What is
    // built ahead of need (stats().prefetchPending, pages loaded ahead) is not waited for.
    return !stats_.popIn() && stats_.pages.wanted == 0 &&
           (!overview_ || overview_->texture() != nullptr);
}

std::string WorldView::caption() const {
    const int r = places_.caption();
    if (r < 0 || places_.captionAlpha() <= 0) return {};
    const world::RegionFile& f = world_.regions[static_cast<std::size_t>(r)];
    return f.caption;
}

} // namespace lc::worldview
