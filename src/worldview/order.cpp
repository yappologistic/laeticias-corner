#include "worldview/order.hpp"

#include <algorithm>
#include <climits>
#include <functional>

namespace lc::worldview {
namespace {

float depthKey(const FRect& f) {
    return f.x0 + f.x1 + f.y0 + f.y1;
}

bool covers(const FRect& outer, const FRect& inner) {
    return outer.x0 <= inner.x0 && outer.y0 <= inner.y0 && outer.x1 >= inner.x1 &&
           outer.y1 >= inner.y1;
}

} // namespace

bool drawnBefore(const OrderItem& a, const OrderItem& b) {
    if (a.ground != b.ground) {
        const OrderItem& g = a.ground ? a : b;
        const OrderItem& o = a.ground ? b : a;
        if (covers(o.foot, g.foot)) return a.ground;
    }
    return behind(a.foot, b.foot);
}

void PageOrder::sort(std::span<const OrderItem> items, float cell,
                     std::vector<std::uint32_t>& order) {
    const std::size_t n = items.size();
    order.clear();
    screens_.resize(n);
    std::uint16_t pages = 0;
    for (std::size_t i = 0; i < n; ++i) {
        screens_[i] = items[i].screen;
        pages = std::max<std::uint16_t>(pages, static_cast<std::uint16_t>(items[i].page + 1));
    }
    grid_.build(screens_, cell);
    edgeFrom_.clear();
    edgeTo_.clear();
    grid_.pairs(screens_, [&](std::uint32_t i, std::uint32_t j) {
        const bool ij = drawnBefore(items[i], items[j]);
        edgeFrom_.push_back(ij ? i : j);
        edgeTo_.push_back(ij ? j : i);
    });
    start_.assign(n + 1, 0);
    indegree_.assign(n, 0);
    for (std::size_t e = 0; e < edgeFrom_.size(); ++e) {
        ++start_[edgeFrom_[e] + 1];
        ++indegree_[edgeTo_[e]];
    }
    for (std::size_t i = 0; i < n; ++i) start_[i + 1] += start_[i];
    next_.resize(edgeFrom_.size());
    cursor_.assign(start_.begin(), start_.end() - 1);
    for (std::size_t e = 0; e < edgeFrom_.size(); ++e) next_[cursor_[edgeFrom_[e]]++] = edgeTo_[e];

    ready_.resize(pages);
    for (auto& h : ready_) h.clear();
    const auto push = [&](std::uint32_t i) {
        auto& h = ready_[items[i].page];
        h.emplace_back(depthKey(items[i].foot), i);
        std::ranges::push_heap(h, std::greater<>{});
    };
    for (std::uint32_t i = 0; i < n; ++i)
        if (indegree_[i] == 0) push(i);
    done_.assign(n, 0);
    std::uint16_t bound = 0;
    while (order.size() < n) {
        // The bound page if anything on it is ready, else the page with the shallowest element.
        int pick = ready_.empty() || ready_[bound].empty() ? -1 : bound;
        for (std::size_t p = 0; pick < 0 && p < ready_.size(); ++p) {
            if (ready_[p].empty()) continue;
            int best = static_cast<int>(p);
            for (std::size_t q = p + 1; q < ready_.size(); ++q)
                if (!ready_[q].empty() &&
                    ready_[q].front() < ready_[static_cast<std::size_t>(best)].front())
                    best = static_cast<int>(q);
            pick = best;
        }
        if (pick < 0) {
            // A cycle (only with contrived layouts): break it at the shallowest element left.
            std::uint32_t c = 0;
            bool found = false;
            for (std::uint32_t i = 0; i < n; ++i)
                if (done_[i] == 0 &&
                    (!found || depthKey(items[i].foot) < depthKey(items[c].foot))) {
                    c = i;
                    found = true;
                }
            indegree_[c] = 0;
            push(c);
            continue;
        }
        bound = static_cast<std::uint16_t>(pick);
        auto& h = ready_[bound];
        std::ranges::pop_heap(h, std::greater<>{});
        const std::uint32_t i = h.back().second;
        h.pop_back();
        if (done_[i] != 0) continue;
        done_[i] = 1;
        order.push_back(i);
        for (std::uint32_t k = start_[i]; k < start_[i + 1]; ++k) {
            const std::uint32_t j = next_[k];
            if (--indegree_[j] == 0 && done_[j] == 0) push(j);
        }
    }
}

void ActorMerge::index(std::span<const OrderItem> items, std::span<const std::uint32_t> order,
                       float cell) {
    order_.assign(order.begin(), order.end());
    rank_.assign(items.size(), 0);
    for (std::size_t k = 0; k < order.size(); ++k) rank_[order[k]] = static_cast<std::uint32_t>(k);
    screens_.resize(items.size());
    for (std::size_t i = 0; i < items.size(); ++i) screens_[i] = items[i].screen;
    cell_ = cell;
}

void ActorMerge::bounds(std::span<const OrderItem> items, std::span<const MergeActor> actors) {
    const std::size_t na = actors.size();
    const auto asItem = [&](std::uint32_t a) {
        return OrderItem{actors[a].foot, actors[a].screen, actors[a].page, false};
    };
    for (std::size_t p = 0; p < pairEl_.size(); ++p) {
        const std::uint32_t e = pairEl_[p];
        const std::uint32_t a = pairAc_[p];
        int r = rel_[p]; // -1, 0 or 1
        if (r == 0) r = drawnBefore(items[e], asItem(a)) ? -1 : 1;
        const int k = static_cast<int>(rank_[e]);
        if (r < 0)
            lo_[a] = std::max(lo_[a], k + 1);
        else
            hi_[a] = std::min(hi_[a], k);
    }
    // Actors over actors: who must go first.
    actorScreens_.resize(na);
    for (std::size_t a = 0; a < na; ++a) actorScreens_[a] = actors[a].screen;
    actorGrid_.build(actorScreens_, 64.0f);
    predStart_.assign(na + 1, 0);
    pairEl_.clear(); // reused: (before, after) actor pairs
    pairAc_.clear();
    actorGrid_.pairs(actorScreens_, [&](std::uint32_t i, std::uint32_t j) {
        const bool ij = drawnBefore(asItem(i), asItem(j));
        pairEl_.push_back(ij ? i : j);
        pairAc_.push_back(ij ? j : i);
        ++predStart_[(ij ? j : i) + 1];
    });
    for (std::size_t a = 0; a < na; ++a) predStart_[a + 1] += predStart_[a];
    pred_.resize(pairEl_.size());
    predFill_.assign(predStart_.begin(), predStart_.end() - 1);
    for (std::size_t p = 0; p < pairEl_.size(); ++p) pred_[predFill_[pairAc_[p]]++] = pairEl_[p];
    // Bounds pass along: someone in front goes no earlier than who is behind, and the one behind
    // no later than who is in front.
    byDepth_.resize(na);
    for (std::uint32_t a = 0; a < na; ++a) byDepth_[a] = a;
    const auto depth = [&](std::uint32_t a) {
        const FRect& f = actors[a].foot;
        return f.x0 + f.x1 + f.y0 + f.y1;
    };
    std::ranges::sort(byDepth_, [&](std::uint32_t a, std::uint32_t b) {
        return std::pair(depth(a), a) < std::pair(depth(b), b);
    });
    for (const std::uint32_t a : byDepth_)
        for (std::uint32_t k = predStart_[a]; k < predStart_[a + 1]; ++k)
            lo_[a] = std::max(lo_[a], lo_[pred_[k]]);
    for (auto it = byDepth_.rbegin(); it != byDepth_.rend(); ++it)
        for (std::uint32_t k = predStart_[*it]; k < predStart_[*it + 1]; ++k)
            hi_[pred_[k]] = std::min(hi_[pred_[k]], hi_[*it]);
    // Where the bounds cross (a static between two overlapping actors), the actor stays seen.
    for (std::size_t a = 0; a < na; ++a) hi_[a] = std::max(hi_[a], lo_[a]);
}

void ActorMerge::flush(std::uint32_t a, std::size_t k) {
    if (state_[a] == 2) return;
    state_[a] = 2;
    for (std::uint32_t p = predStart_[a]; p < predStart_[a + 1]; ++p)
        if (state_[pred_[p]] == 1) flush(pred_[p], k);
    out_.emplace_back(k, a);
}

void ActorMerge::schedule(std::span<const OrderItem> items, std::span<const MergeActor> actors,
                          const std::vector<std::uint8_t>& drawnAt) {
    const std::size_t na = actors.size();
    const std::size_t n = order_.size();
    out_.clear();
    pending_.clear();
    state_.assign(na, 0);
    byLo_.assign(byDepth_.begin(), byDepth_.end());
    std::ranges::stable_sort(byLo_, {}, [&](std::uint32_t a) { return lo_[a]; });
    int bound = -1;
    int minHi = INT_MAX;
    std::size_t next = 0;
    const auto flushPage = [&](std::size_t k) {
        // Whatever waits for the page now bound goes now (it may bind another: repeat).
        bool again = true;
        while (again && bound >= 0) {
            again = false;
            minHi = INT_MAX;
            for (const std::uint32_t a : pending_) {
                if (state_[a] != 1) continue;
                if (actors[a].page == bound) {
                    flush(a, k);
                } else {
                    minHi = std::min(minHi, hi_[a]);
                }
            }
            std::erase_if(pending_, [&](std::uint32_t a) { return state_[a] != 1; });
            if (!out_.empty() && out_.back().first == k &&
                actors[out_.back().second].page != bound) {
                bound = actors[out_.back().second].page;
                again = true;
            }
        }
    };
    int flushedFor = -2; // the bound page the waiting list was last checked against
    // Only drawn positions are visited (then the end): actors go just before one of them.
    for (std::size_t vi = 0; vi <= visible_.size(); ++vi) {
        const std::size_t k = vi < visible_.size() ? visible_[vi] : n;
        if (bound != flushedFor && !pending_.empty()) {
            flushPage(k);
            flushedFor = bound;
        }
        bool added = false;
        for (; next < byLo_.size() && lo_[byLo_[next]] <= static_cast<int>(k); ++next) {
            const std::uint32_t a = byLo_[next];
            state_[a] = 1;
            pending_.push_back(a);
            minHi = std::min(minHi, hi_[a]);
            added = true;
        }
        if (added) {
            flushPage(k);
            flushedFor = bound;
        }
        if (k == n || minHi <= static_cast<int>(k)) {
            // Someone in front comes next (or the end): everyone waiting goes now, back to front.
            std::ranges::sort(pending_, [&](std::uint32_t a, std::uint32_t b) {
                const FRect& fa = actors[a].foot;
                const FRect& fb = actors[b].foot;
                return std::pair(fa.x0 + fa.x1 + fa.y0 + fa.y1, a) <
                       std::pair(fb.x0 + fb.x1 + fb.y0 + fb.y1, b);
            });
            for (const std::uint32_t a : pending_)
                if (state_[a] == 1) flush(a, k);
            pending_.clear();
            minHi = INT_MAX;
            if (!out_.empty() && out_.back().first == k) bound = actors[out_.back().second].page;
        }
        if (k < n && drawnAt[k] != 0) bound = items[order_[k]].page;
    }
    emitStart_.assign(n + 2, 0);
    emit_.resize(out_.size());
    for (const auto& [k, a] : out_) ++emitStart_[k + 1];
    for (std::size_t k = 0; k <= n; ++k) emitStart_[k + 1] += emitStart_[k];
    for (std::size_t i = 0; i < out_.size(); ++i) emit_[i] = out_[i].second; // already by k
}

int pageSwitches(std::span<const OrderItem> items, std::span<const std::uint32_t> order) {
    int switches = 0;
    for (std::size_t k = 1; k < order.size(); ++k)
        if (items[order[k]].page != items[order[k - 1]].page) ++switches;
    return switches;
}

} // namespace lc::worldview
