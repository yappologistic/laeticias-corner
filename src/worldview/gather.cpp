#include "worldview/gather.hpp"

#include "worldview/cells.hpp"
#include "worldview/tuning.hpp"

#include <algorithm>
#include <climits>

namespace lc::worldview {
namespace {

constexpr float kSortCell = 128.0f; // the depth sort's screen grid, world px
constexpr int kMaxLevel = 15;

FRect rectOf(TileRect r) {
    return {static_cast<float>(r.x0), static_cast<float>(r.y0), static_cast<float>(r.x1),
            static_cast<float>(r.y1)};
}

} // namespace

ZRange heightsOf(const world::GeomVariant* g, const world::ItemInfo& info, int piece,
                 float spriteH) {
    const auto f = [](int v) { return static_cast<float>(v); };
    if (g == nullptr) return {0, info.height > 0 ? f(info.height) : spriteH};
    const world::GeomPiece* gp = piece >= 0 && std::cmp_less(piece, g->pieces.size())
                                     ? &g->pieces[static_cast<std::size_t>(piece)]
                                     : nullptr;
    const auto inside = [&](TilePos t) { return gp == nullptr || gp->rect.contains(t); };
    bool walk = false;
    int floorMax = 0;
    int floorMin = INT_MAX;
    for (const TilePos t : g->walk) {
        if (!inside(t)) continue;
        int z = 0;
        for (const auto& [wt, wz] : g->walkZ)
            if (wt == t) z = wz;
        walk = true;
        floorMax = std::max(floorMax, z);
        floorMin = std::min(floorMin, z);
    }
    int roofMin = INT_MAX;
    for (const auto& [t, z] : g->roof)
        if (inside(t)) roofMin = std::min(roofMin, z);
    int top = -1;
    if (g->topsW > 0)
        for (std::size_t i = 0; i < g->tops.size(); ++i) {
            const TilePos t{static_cast<int>(i) % g->topsW, static_cast<int>(i) / g->topsW};
            if (inside(t)) top = std::max(top, g->tops[i]);
        }
    int under = gp != nullptr ? gp->under : g->under;
    // A walkable kit piece (a timber bridge, a mole) lists no walk tiles: all of it is floor, at
    // its top.
    if (!walk && info.walkable && gp == nullptr) {
        walk = true;
        floorMax = floorMin = std::max(top, 0);
    }
    // A crossing's deck stands over the water even where the art gives no clearance (some
    // connect variants of the kit bridges): whatever floats under it is below it.
    if (walk && info.crossing && under == 0 && floorMin > 0) under = 1;
    if (walk) {
        // A deck: room under it below its floor (boats under, walkers over).
        if (under > 0 && under <= floorMin) return {f(under), f(floorMax), ZRange::Kind::Deck};
        // A run under a roof (a gate's passage, an arch): from the overhead's underside up.
        const int over = std::min(roofMin, under > 0 ? under : INT_MAX);
        if (over != INT_MAX && (gp == nullptr || !gp->floor))
            return {f(over), f(std::max(g->h, over)), ZRange::Kind::Overhead};
        // A floor: stair treads, a walk run's paving, under whoever stands on it; with a roof
        // over it in the same piece, both (drawn in two parts).
        ZRange z{0, f(floorMax), ZRange::Kind::Floor};
        if (over != INT_MAX) {
            z.over = f(over);
            z.top = f(std::max(g->h, over));
        }
        return z;
    }
    return {0, top >= 0 ? f(top) : f(g->h)};
}

TileRect gatherTiles(const FRect& clip, const Reach& span, Iso iso) {
    return tilesUnder(
        {clip.x0 - span.right, clip.y0 - span.down, clip.x1 + span.left, clip.y1 + span.up}, iso);
}

Gatherer::Gatherer(const world::WorldMap& map, const WorldSprites& sprites, Hole hole,
                   std::span<const FigureLook> figures)
    : map_(map), sprites_(sprites), hole_(hole), figures_(figures),
      iso_(map.content().home().iso()), lvl_(map.content().tileLevel()), hh_(iso_.hh),
      stamp_(map.items().size(), 0) {}

void Gatherer::run(TileRect tiles, const FRect& clip, Gathered& out) {
    out.clear();
    tiles = tiles.clipped(map_.bounds());
    if (tiles.empty()) return;
    ++pass_;
    map_.piecesIn(tiles, pieces_);
    const auto placed = map_.items();
    for (const world::DrawPiece& d : pieces_) {
        const world::Placed& it = placed[d.item];
        if (hole_.tiles.contains(TilePos{it.x, it.y})) continue;
        const VariantLook& look = sprites_.item(it);
        // Geometry pieces without piece art draw the whole sprite once.
        const bool split = d.piece >= 0 && !look.pieces.empty();
        const bool first = stamp_[d.item] != pass_;
        if (!split && !first) continue;
        const SpriteRef& s =
            split ? look.pieces[static_cast<std::size_t>(d.piece)] : look.base.f.front();
        const Vec2 w = iso_.toWorld(TilePos{it.x, it.y});
        const Vec2 a{w.x, w.y - static_cast<float>(it.level * lvl_)};
        const FRect box{a.x - s.ox, a.y - s.oy, a.x - s.ox + s.w, a.y - s.oy + s.h};
        // An item off the clip whose shadow falls on it still belongs (for its shadow).
        const bool shades =
            first && look.shadow &&
            FRect{a.x - look.shadow->ox, a.y - look.shadow->oy,
                  a.x - look.shadow->ox + look.shadow->w, a.y - look.shadow->oy + look.shadow->h}
                .overlaps(clip);
        if (!box.overlaps(clip) && !shades) continue;
        stamp_[d.item] = pass_;
        const Elem e{&look, d.item,       static_cast<std::int16_t>(split ? d.piece : -1),
                     false, first,        false,
                     false, {it.x, it.y}, a};
        const float base = static_cast<float>(it.level * lvl_);
        const ZRange z = heightsOf(map_.geometry(it), map_.info(it), split ? d.piece : -1, s.oy);
        const FRect foot = rectOf(split ? d.rect : it.rect());
        const auto part = static_cast<std::uint32_t>(split ? d.piece + 1 : 0);
        out.elems.push_back(e);
        out.items.push_back(
            {makeBox(foot, base + z.z0, base + z.z1, depthId(DepthKind::Item, d.item, part), hh_),
             box, s.page});
        if (z.over >= 0) {
            // The floor before whoever walks on it, the roof over them after.
            out.elems.back().part = 0;
            out.elems.back().cutZ = base + z.over;
            out.elems.push_back(e);
            out.elems.back().first = false;
            out.elems.back().part = 1;
            out.elems.back().cutZ = base + z.over;
            out.items.push_back({makeBox(foot, base + z.over, base + z.top,
                                         depthId(DepthKind::Item, d.item, part | 0x8000u), hh_),
                                 box, s.page});
        }
    }
    // Raised tiles that hide an item or walkable ground behind them join the sort (world-tech
    // §4.3, draw-order.md §1.5 e): Q hides P when P lies behind it, lower by dL > 0, within
    // dL + 1 rows.
    const Reach& gr = sprites_.groundReach();
    const float lift = gr.up - static_cast<float>(kMaxLevel * lvl_);
    for (int qy = tiles.y0; qy < tiles.y1; ++qy)
        for (int qx = tiles.x0; qx < tiles.x1; ++qx) {
            const TilePos q{qx, qy};
            // Never read inside the hole: the game writes it while this runs on a worker.
            if (hole_.tiles.contains(q)) continue;
            const int t = map_.terrainAt(q);
            if (t == world::kNone) continue;
            const int lq = map_.level(q);
            if (lq == 0) continue;
            const Vec2 w = iso_.toWorld(q);
            const FRect box{w.x - gr.left, w.y - static_cast<float>(lq * lvl_) - lift,
                            w.x + gr.right, w.y + gr.down};
            if (!box.overlaps(clip)) continue;
            bool hides = false;
            for (int a = 0; a <= lq + 1 && !hides; ++a)
                for (int b = 0; a + b <= lq + 1 && !hides; ++b) {
                    const TilePos p{qx - a, qy - b};
                    if ((a == 0 && b == 0) || !map_.inBounds(p) || hole_.tiles.contains(p) ||
                        (map_.itemAt(p) < 0 && !map_.walkable(p)))
                        continue;
                    const int dl = lq - map_.level(p);
                    hides = dl > 0 && a + b <= dl + 1;
                }
            if (!hides) continue;
            const TerrainLook& look = sprites_.terrain(t);
            const std::uint16_t page =
                look.base.empty() ? PageAtlas::kGeneratedPage : look.base.front().page;
            out.elems.push_back({nullptr, 0, -1, true, false, false, false, q, {}});
            out.items.push_back(
                {makeBox(
                     rectOf({qx, qy, qx + 1, qy + 1}), 0, static_cast<float>(lq * lvl_),
                     depthId(DepthKind::Ground, static_cast<std::uint32_t>(qy * map_.width() + qx)),
                     hh_),
                 box, page});
        }
    for (std::size_t f = 0; f < figures_.size(); ++f) {
        const FigureLook& fg = figures_[f];
        if (!tiles.contains(fg.tile)) continue;
        const SpriteRef& s = fg.sprite;
        const FRect box{fg.anchor.x - s.ox, fg.anchor.y - s.oy, fg.anchor.x - s.ox + s.w,
                        fg.anchor.y - s.oy + s.h};
        if (!box.overlaps(clip)) continue;
        out.elems.push_back({nullptr, static_cast<std::uint32_t>(f), -1, false, false, false, true,
                             fg.tile, fg.anchor});
        // Where it stands, like an actor: a small square round its feet.
        const Vec2 at = iso_.toTile(
            {fg.anchor.x, fg.anchor.y + static_cast<float>(map_.level(fg.tile) * lvl_)});
        const float k = tuning::kActorFoot;
        const float z0 = static_cast<float>(map_.level(fg.tile) * lvl_);
        out.items.push_back(
            {makeBox({at.x - k, at.y - k, at.x + k, at.y + k}, z0, z0 + s.oy,
                     depthId(DepthKind::Figure, static_cast<std::uint32_t>(f)), hh_),
             box, s.page});
    }
    if (!hole_.empty() && hole_.tiles.intersects(tiles) && hole_.screen.overlaps(clip)) {
        out.elems.push_back(
            {nullptr, 0, -1, false, false, true, false, {hole_.tiles.x0, hole_.tiles.y0}, {}});
        out.items.push_back(
            {makeBox(rectOf(hole_.tiles), hole_.z0, hole_.z1, depthId(DepthKind::Home, 0), hh_),
             hole_.screen, PageAtlas::kGeneratedPage});
    }
    sorter_.sort(out.items, kSortCell, out.order, out.graph);
    out.cycles = sorter_.cyclesBroken();
    out.cycleAt = sorter_.firstCycle();
}

Prep::Prep(const world::WorldMap& map, const WorldSprites& sprites, bool async, Hole hole,
           std::span<const FigureLook> figures)
    : async_(async), mine_(map, sprites, hole, figures), theirs_(map, sprites, hole, figures) {
    if (async_) worker_ = std::jthread([this](const std::stop_token& st) { work(st); });
}

Prep::~Prep() {
    worker_.request_stop();
    wake_.notify_all();
}

void Prep::request(const Job& job, bool urgent) {
    if (!async_) {
        Done d{job.tag, {}};
        mine_.run(job.tiles, job.clip, d.result);
        done_.push_back(std::move(d));
        return;
    }
    const std::scoped_lock lock(mutex_);
    if (urgent)
        queue_.push_front(job);
    else
        queue_.push_back(job);
    wake_.notify_one();
}

bool Prep::take(std::uint64_t tag, Gathered& out) {
    const std::scoped_lock lock(mutex_);
    const auto it = std::ranges::find(done_, tag, &Done::tag);
    if (it == done_.end()) return false;
    std::swap(out, it->result);
    done_.erase(it);
    return true;
}

void Prep::work(const std::stop_token& stop) {
    Gathered result;
    for (;;) {
        Job job;
        {
            std::unique_lock lock(mutex_);
            if (!wake_.wait(lock, stop, [&] { return !queue_.empty(); })) return;
            job = queue_.front();
            queue_.pop_front();
        }
        theirs_.run(job.tiles, job.clip, result);
        const std::scoped_lock lock(mutex_);
        done_.push_back({job.tag, std::move(result)});
        result = {};
    }
}

} // namespace lc::worldview
