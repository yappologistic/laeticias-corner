#include "worldview/gather.hpp"

#include "worldview/cells.hpp"

#include <algorithm>

namespace lc::worldview {
namespace {

constexpr float kSortCell = 128.0f; // the depth sort's screen grid, world px
constexpr int kMaxLevel = 15;

FRect rectOf(TileRect r) {
    return {static_cast<float>(r.x0), static_cast<float>(r.y0), static_cast<float>(r.x1),
            static_cast<float>(r.y1)};
}

} // namespace

TileRect gatherTiles(const FRect& clip, const Reach& span, Iso iso) {
    return tilesUnder(
        {clip.x0 - span.right, clip.y0 - span.down, clip.x1 + span.left, clip.y1 + span.up}, iso);
}

Gatherer::Gatherer(const world::WorldMap& map, const WorldSprites& sprites)
    : map_(map), sprites_(sprites), iso_(map.content().home().iso()),
      lvl_(map.content().tileLevel()), stamp_(map.items().size(), 0) {}

void Gatherer::run(TileRect tiles, const FRect& clip, Gathered& out) {
    out.clear();
    tiles = tiles.clipped(map_.bounds());
    if (tiles.empty()) return;
    ++pass_;
    map_.piecesIn(tiles, pieces_);
    const auto placed = map_.items();
    for (const world::DrawPiece& d : pieces_) {
        const world::Placed& it = placed[d.item];
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
        out.elems.push_back({&look,
                             d.item,
                             static_cast<std::int16_t>(split ? d.piece : -1),
                             false,
                             first,
                             {it.x, it.y},
                             a});
        out.items.push_back({rectOf(split ? d.rect : it.rect()), box, s.page, false});
    }
    // Raised tiles that hide an item behind them join the sort (world-tech §4.3): Q hides P when
    // P lies behind it, lower by dL > 0, within dL + 1 rows.
    const Reach& gr = sprites_.groundReach();
    const float lift = gr.up - static_cast<float>(kMaxLevel * lvl_);
    for (int qy = tiles.y0; qy < tiles.y1; ++qy)
        for (int qx = tiles.x0; qx < tiles.x1; ++qx) {
            const TilePos q{qx, qy};
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
                    if ((a == 0 && b == 0) || !map_.inBounds(p) || map_.itemAt(p) < 0) continue;
                    const int dl = lq - map_.level(p);
                    hides = dl > 0 && a + b <= dl + 1;
                }
            if (!hides) continue;
            const TerrainLook& look = sprites_.terrain(t);
            const std::uint16_t page =
                look.base.empty() ? PageAtlas::kGeneratedPage : look.base.front().page;
            out.elems.push_back({nullptr, 0, -1, true, false, q, {}});
            out.items.push_back({rectOf({qx, qy, qx + 1, qy + 1}), box, page, true});
        }
    sorter_.sort(out.items, kSortCell, out.order);
}

Prep::Prep(const world::WorldMap& map, const WorldSprites& sprites, bool async)
    : async_(async), mine_(map, sprites), theirs_(map, sprites) {
    if (async_) worker_ = std::jthread([this](const std::stop_token& st) { work(st); });
}

Prep::~Prep() {
    worker_.request_stop();
    wake_.notify_all();
}

void Prep::request(const Job& job) {
    if (!async_) {
        Done d{job.tag, {}};
        mine_.run(job.tiles, job.clip, d.result);
        done_.push_back(std::move(d));
        return;
    }
    const std::scoped_lock lock(mutex_);
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
