#include "core/path.hpp"

#include "core/catalog.hpp"
#include "core/tuning.hpp"
#include "core/world.hpp"

#include <algorithm>
#include <cmath>

namespace lc {
namespace {

constexpr TilePos kDirs[8] = {{1, 0}, {-1, 0}, {0, 1}, {0, -1}, {1, 1}, {1, -1}, {-1, 1}, {-1, -1}};
constexpr float kDiagonal = 1.41421356f;

bool heapLess(float a, float b) {
    return a > b; // min-heap through std::push_heap's max-heap
}

} // namespace

bool passable(const World& world, const Catalog& cat, Locomotion move, TilePos t, bool bank) {
    if (!world.hasGround(t) || world.isWild(t)) return false;
    const Item* it = world.itemAt(t);
    const ItemDef* def = it != nullptr ? &cat.items[it->type] : nullptr;
    const bool water = world.isWater(t);
    switch (move) {
    case Locomotion::Fly: return true;
    case Locomotion::Walk:
        if (def != nullptr && !def->walkable) return false;
        return !water || (def != nullptr && def->crossing);
    case Locomotion::Swim:
        if (def != nullptr && !def->walkable) return false;
        if (water) return true;
        if (!bank) return false;
        break;
    case Locomotion::Shore:
        if (def != nullptr && !def->walkable) return false;
        break;
    }
    // Shore, or a swimmer stepping out onto the bank: next to the other kind of ground.
    for (const TilePos d : {TilePos{1, 0}, TilePos{-1, 0}, TilePos{0, 1}, TilePos{0, -1}}) {
        const TilePos q{t.x + d.x, t.y + d.y};
        if (world.hasGround(q) && !world.isWild(q) && world.isWater(q) != water) return true;
    }
    return false;
}

float stepCost(const World& world, const Catalog& cat, Locomotion move, TilePos t) {
    if (move != Locomotion::Walk) return 1.0f;
    if (cat.terrain[static_cast<std::size_t>(world.terrainAt(t))].paved)
        return tuning::kPathCostPaved;
    const Item* it = world.itemAt(t);
    if (it != nullptr && cat.items[it->type].crossing) return tuning::kPathCostPaved;
    return tuning::kPathCostOther;
}

PathFinder::PathFinder(const Catalog& cat) : cat_(&cat) {
    heap_.reserve(1024);
    route_.reserve(256);
}

int PathFinder::find(const World& world, const PathQuery& q, std::span<TilePos> out) {
    expanded_ = 0;
    const TileRect r = q.bounds.clipped(world.bounds());
    if (out.empty() || !r.contains(q.from) || !r.contains(q.to) || q.from == q.to) return 0;
    const int w = r.x1 - r.x0;
    const auto cells = static_cast<std::size_t>(w) * static_cast<std::size_t>(r.y1 - r.y0);
    if (g_.size() < cells) {
        g_.resize(cells);
        parent_.resize(cells);
        stamp_.assign(cells, 0);
        closed_.resize(cells);
    }
    if (++search_ == 0) {
        std::ranges::fill(stamp_, 0u);
        search_ = 1;
    }
    const auto index = [&](TilePos p) {
        return static_cast<std::uint32_t>((p.y - r.y0) * w + (p.x - r.x0));
    };
    const auto at = [&](std::uint32_t i) {
        return TilePos{r.x0 + static_cast<int>(i) % w, r.y0 + static_cast<int>(i) / w};
    };
    const auto open = [&](TilePos p) {
        // The start may be a seat it is getting up from; the goal may be one it sits on.
        return p == q.to || p == q.from || passable(world, *cat_, q.move, p, q.bank);
    };
    const auto h = [&](TilePos p) {
        const auto dx = static_cast<float>(std::abs(p.x - q.to.x));
        const auto dy = static_cast<float>(std::abs(p.y - q.to.y));
        return (std::max(dx, dy) + (kDiagonal - 1.0f) * std::min(dx, dy)) * tuning::kPathCostPaved;
    };
    heap_.clear();
    const std::uint32_t s = index(q.from);
    stamp_[s] = search_;
    g_[s] = 0;
    parent_[s] = s;
    closed_[s] = 0;
    heap_.push_back({h(q.from), s});
    const std::uint32_t goal = index(q.to);
    bool found = false;
    while (!heap_.empty() && expanded_ < tuning::kPathMaxNodes) {
        std::ranges::pop_heap(heap_, heapLess, &Open::f);
        const std::uint32_t cur = heap_.back().node;
        heap_.pop_back();
        if (closed_[cur] != 0) continue;
        closed_[cur] = 1;
        ++expanded_;
        if (cur == goal) {
            found = true;
            break;
        }
        const TilePos p = at(cur);
        for (int d = 0; d < 8; ++d) {
            const TilePos n{p.x + kDirs[d].x, p.y + kDirs[d].y};
            if (!r.contains(n) || !open(n)) continue;
            const bool diagonal = d >= 4;
            // No corner cutting: both tiles beside a diagonal step must be open too.
            if (diagonal && (!open({p.x + kDirs[d].x, p.y}) || !open({p.x, p.y + kDirs[d].y})))
                continue;
            const std::uint32_t ni = index(n);
            const float cost = stepCost(world, *cat_, q.move, n) * (diagonal ? kDiagonal : 1.0f);
            const float ng = g_[cur] + cost;
            if (stamp_[ni] == search_ && (closed_[ni] != 0 || g_[ni] <= ng)) continue;
            stamp_[ni] = search_;
            closed_[ni] = 0;
            g_[ni] = ng;
            parent_[ni] = cur;
            heap_.push_back({ng + h(n), ni});
            std::ranges::push_heap(heap_, heapLess, &Open::f);
        }
    }
    if (!found) return 0;
    route_.clear();
    for (std::uint32_t i = goal; i != s; i = parent_[i]) route_.push_back(at(i));
    std::ranges::reverse(route_);

    // Pull the route straight where a straight line is open and no dearer than the steps it
    // replaces (so a walker does not leave a path to cut across grass).
    const auto lineOk = [&](TilePos a, TilePos b, float worst) {
        const float dx = static_cast<float>(b.x - a.x);
        const float dy = static_cast<float>(b.y - a.y);
        const int n = static_cast<int>(std::max(std::abs(dx), std::abs(dy)) * 4.0f);
        TilePos prev = a;
        for (int i = 1; i <= n; ++i) {
            const float k = static_cast<float>(i) / static_cast<float>(n);
            const TilePos t{static_cast<int>(std::floor(static_cast<float>(a.x) + 0.5f + dx * k)),
                            static_cast<int>(std::floor(static_cast<float>(a.y) + 0.5f + dy * k))};
            if (t == prev) continue;
            if (!open(t) || stepCost(world, *cat_, q.move, t) > worst) return false;
            if (t.x != prev.x && t.y != prev.y && (!open({t.x, prev.y}) || !open({prev.x, t.y})))
                return false;
            prev = t;
        }
        return true;
    };
    int written = 0;
    TilePos anchor = q.from;
    std::size_t i = 0;
    while (i < route_.size() && written < static_cast<int>(out.size())) {
        std::size_t best = i;
        float worst = stepCost(world, *cat_, q.move, route_[i]);
        for (std::size_t j = i + 1; j < route_.size() && j < i + 12; ++j) {
            worst = std::max(worst, stepCost(world, *cat_, q.move, route_[j]));
            if (route_[j] == q.to && !passable(world, *cat_, q.move, q.to, q.bank)) break;
            if (lineOk(anchor, route_[j], worst)) best = j;
        }
        out[static_cast<std::size_t>(written++)] = route_[best];
        anchor = route_[best];
        i = best + 1;
    }
    return written;
}

} // namespace lc
