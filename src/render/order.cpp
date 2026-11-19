#include "render/order.hpp"

#include <algorithm>
#include <functional>

namespace lc {
namespace {

float depthKey(const FRect& f) {
    return f.x0 + f.x1 + f.y0 + f.y1;
}

} // namespace

void PageOrder::sort(std::span<const OrderItem> items, float cell,
                     std::vector<std::uint32_t>& order, OrderGraph& graph,
                     std::span<const std::uint8_t> groups) {
    const std::size_t n = items.size();
    order.clear();
    cycles_ = 0;
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
        if (!constrains(items[i].box, items[j].box)) return;
        if (!groups.empty() && groups[i] != 0 && groups[i] == groups[j]) return;
        const bool ij = drawnBefore(items[i].box, items[j].box);
        edgeFrom_.push_back(ij ? i : j);
        edgeTo_.push_back(ij ? j : i);
    });
    std::vector<std::uint32_t>& start = graph.start;
    std::vector<std::uint32_t>& next = graph.next;
    start.assign(n + 1, 0);
    indegree_.assign(n, 0);
    for (std::size_t e = 0; e < edgeFrom_.size(); ++e) {
        ++start[edgeFrom_[e] + 1];
        ++indegree_[edgeTo_[e]];
    }
    for (std::size_t i = 0; i < n; ++i) start[i + 1] += start[i];
    next.resize(edgeFrom_.size());
    cursor_.assign(start.begin(), start.end() - 1);
    for (std::size_t e = 0; e < edgeFrom_.size(); ++e) next[cursor_[edgeFrom_[e]]++] = edgeTo_[e];

    ready_.resize(pages);
    for (auto& h : ready_) h.clear();
    const auto push = [&](std::uint32_t i) {
        auto& h = ready_[items[i].page];
        h.emplace_back(depthKey(items[i].box.foot), i);
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
            // A cycle (a fault in the data): break it at the shallowest element left.
            std::uint32_t c = 0;
            bool found = false;
            for (std::uint32_t i = 0; i < n; ++i)
                if (done_[i] == 0 &&
                    (!found || depthKey(items[i].box.foot) < depthKey(items[c].box.foot))) {
                    c = i;
                    found = true;
                }
            indegree_[c] = 0;
            push(c);
            if (cycles_++ == 0) firstCycle_ = items[c].box;
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
        for (std::uint32_t k = start[i]; k < start[i + 1]; ++k) {
            const std::uint32_t j = next[k];
            if (--indegree_[j] == 0 && done_[j] == 0) push(j);
        }
    }
}

void ActorMerge::index(std::span<const OrderItem> items, std::span<const std::uint32_t> order,
                       const OrderGraph& graph, float cell) {
    const std::size_t n = order.size();
    order_.assign(order.begin(), order.end());
    rank_.assign(items.size(), 0);
    for (std::size_t k = 0; k < n; ++k) rank_[order[k]] = static_cast<std::uint32_t>(k);
    placed_.resize(n);
    for (std::size_t k = 0; k < n; ++k) placed_[k] = items[order[k]].screen;
    // The static edges by position, for holding back what follows a held element.
    succStart_.assign(n + 1, 0);
    succ_.clear();
    if (graph.start.size() == items.size() + 1) {
        for (std::size_t k = 0; k < n; ++k) {
            const std::uint32_t e = order[k];
            for (std::uint32_t q = graph.start[e]; q < graph.start[e + 1]; ++q)
                succ_.push_back(rank_[graph.next[q]]);
            succStart_[k + 1] = static_cast<std::uint32_t>(succ_.size());
        }
    }
    cell_ = cell;
    grid_.build(placed_, cell_);
    seen_.assign(n, 0);
    tick_ = 1;
}

void ActorMerge::plan(std::span<const OrderItem> items, std::span<const OrderItem> actors,
                      const FRect& view) {
    items_ = items;
    actors_ = actors;
    const std::size_t n = order_.size();
    const std::size_t na = actors.size();
    held_ = 0;
    cycles_ = 0;
    seq_.clear();
    // Only what is drawn this frame matters: culled elements order nothing. The boxes lie in
    // draw order, so this is one pass over contiguous memory.
    drawnAt_.assign(n, 0);
    visible_.clear();
    for (std::size_t k = 0; k < n; ++k)
        if (placed_[k].overlaps(view)) {
            drawnAt_[k] = 1;
            visible_.push_back(static_cast<std::uint32_t>(k));
        }
    // Actors meet what is drawn through the grid made with the order, each element once.
    pairEl_.clear();
    pairAc_.clear();
    pairAfter_.clear();
    if (tick_ > 0xFFFFFFFFu - na - 1) {
        seen_.assign(seen_.size(), 0);
        tick_ = 1;
    }
    for (std::uint32_t a = 0; a < na; ++a) {
        const std::uint32_t mark = tick_ + a;
        grid_.query(actors[a].screen, [&](std::uint32_t k) {
            if (drawnAt_[k] == 0 || seen_[k] == mark || !placed_[k].overlaps(actors[a].screen))
                return;
            seen_[k] = mark;
            if (!constrains(items[order_[k]].box, actors[a].box)) return;
            pairEl_.push_back(k);
            pairAc_.push_back(a);
            pairAfter_.push_back(drawnBefore(items[order_[k]].box, actors[a].box) ? 1 : 0);
        });
    }
    tick_ += static_cast<std::uint32_t>(na) + 1;

    // Edges: element -> actor (the actor waits), actor -> element (the element waits), each
    // kept by its source (CSR).
    blocked_.assign(n, 0);
    aIndeg_.assign(na, 0);
    aStaticIndeg_.assign(na, 0);
    aSuccStart_.assign(na + 1, 0);
    eSuccStart_.assign(n + 1, 0);
    for (std::size_t p = 0; p < pairEl_.size(); ++p) {
        if (pairAfter_[p] != 0) {
            ++aIndeg_[pairAc_[p]];
            ++aStaticIndeg_[pairAc_[p]];
            ++eSuccStart_[pairEl_[p] + 1];
        } else {
            ++blocked_[pairEl_[p]];
            ++aSuccStart_[pairAc_[p] + 1];
        }
    }
    for (std::size_t a = 0; a < na; ++a) aSuccStart_[a + 1] += aSuccStart_[a];
    for (std::size_t k = 0; k < n; ++k) eSuccStart_[k + 1] += eSuccStart_[k];
    aSucc_.resize(aSuccStart_[na]);
    eSucc_.resize(eSuccStart_[n]);
    fill_.assign(aSuccStart_.begin(), aSuccStart_.end() - 1);
    for (std::size_t p = 0; p < pairEl_.size(); ++p)
        if (pairAfter_[p] == 0) aSucc_[fill_[pairAc_[p]]++] = pairEl_[p];
    fill_.assign(eSuccStart_.begin(), eSuccStart_.end() - 1);
    for (std::size_t p = 0; p < pairEl_.size(); ++p)
        if (pairAfter_[p] != 0) eSucc_[fill_[pairEl_[p]]++] = pairAc_[p];
    // Actors over actors.
    actorScreens_.resize(na);
    for (std::size_t a = 0; a < na; ++a) actorScreens_[a] = actors[a].screen;
    actorGrid_.build(actorScreens_, 64.0f);
    aaSuccStart_.assign(na + 1, 0);
    pairEl_.clear(); // reused: (before, after) actor pairs
    pairAc_.clear();
    actorGrid_.pairs(actorScreens_, [&](std::uint32_t i, std::uint32_t j) {
        if (!constrains(actors[i].box, actors[j].box)) return;
        const bool ij = drawnBefore(actors[i].box, actors[j].box);
        pairEl_.push_back(ij ? i : j);
        pairAc_.push_back(ij ? j : i);
        ++aaSuccStart_[(ij ? i : j) + 1];
        ++aIndeg_[ij ? j : i];
    });
    for (std::size_t a = 0; a < na; ++a) aaSuccStart_[a + 1] += aaSuccStart_[a];
    aaSucc_.resize(aaSuccStart_[na]);
    fill_.assign(aaSuccStart_.begin(), aaSuccStart_.end() - 1);
    for (std::size_t p = 0; p < pairEl_.size(); ++p) aaSucc_[fill_[pairEl_[p]]++] = pairAc_[p];

    // Walk the static order.
    state_.assign(n, 0);
    aState_.assign(na, 0);
    pending_.clear();
    released_.clear();
    bound_ = -1;
    int checked = -2; // the bound page the ready actors were last checked against
    for (std::uint32_t a = 0; a < na; ++a)
        if (aIndeg_[a] == 0) {
            aState_[a] = 1;
            pending_.push_back(a);
        }
    for (const std::uint32_t k : visible_) {
        if (state_[k] != 0) continue;
        // What waits for the page now bound goes now, cheaply (checked when either changed).
        if (!pending_.empty() && (bound_ != checked || added_)) {
            flushPending(false);
            checked = bound_;
            added_ = false;
        }
        if (blocked_[k] > 0) flushPending(true);
        if (blocked_[k] > 0) {
            // Something in front of it is not drawn yet (an actor waiting for what it stands
            // behind, held further back): hold it, and what must follow it.
            state_[k] = 1;
            ++held_;
            for (std::uint32_t q = succStart_[k]; q < succStart_[k + 1]; ++q)
                if (drawnAt_[succ_[q]] != 0 && state_[succ_[q]] != 2) ++blocked_[succ_[q]];
            continue;
        }
        emitElement(k);
        drain();
    }
    flushPending(true);
    // Anything left closes a cycle. Among boxes that stand on the ground the comparator has none
    // (draw-order.md §1.3); stacked ones can: a walker on a long deck and a boat under it nearer
    // the camera (deck, walker, boat, deck). It is broken where it shows least: first an actor
    // that waits only for other actors goes (the boat's mast behind the walker, the deck still
    // over the boat and under the walker), then a held element, then any actor; each is counted.
    for (;;) {
        std::uint32_t a = 0;
        for (; a < na && !(aState_[a] == 0 && aStaticIndeg_[a] == 0); ++a) {}
        if (a < na) {
            ++cycles_;
            aIndeg_[a] = 0;
            aState_[a] = 1;
            pending_.push_back(a);
            flushPending(true);
            continue;
        }
        std::uint32_t k = 0;
        bool found = false;
        for (const std::uint32_t v : visible_)
            if (state_[v] == 1) {
                k = v;
                found = true;
                break;
            }
        if (found) {
            ++cycles_;
            blocked_[k] = 0;
            released_.push_back(k);
            drain();
            flushPending(true);
            continue;
        }
        for (a = 0; a < na && aState_[a] != 0; ++a) {}
        if (a == na) break;
        ++cycles_;
        aIndeg_[a] = 0;
        aState_[a] = 1;
        pending_.push_back(a);
        flushPending(true);
    }
}

void ActorMerge::emitElement(std::uint32_t k) {
    const bool wasHeld = state_[k] == 1;
    state_[k] = 2;
    const std::uint32_t e = order_[k];
    seq_.push_back({e, false});
    bound_ = items_[e].page;
    // Actors behind it may now go.
    for (std::uint32_t q = eSuccStart_[k]; q < eSuccStart_[k + 1]; ++q) {
        const std::uint32_t a = eSucc_[q];
        --aStaticIndeg_[a];
        if (--aIndeg_[a] == 0 && aState_[a] == 0) {
            aState_[a] = 1;
            pending_.push_back(a);
            added_ = true;
        }
    }
    // Its static successors no longer wait for it (only counted while it was held).
    if (wasHeld)
        for (std::uint32_t q = succStart_[k]; q < succStart_[k + 1]; ++q) {
            const std::uint32_t j = succ_[q];
            if (drawnAt_[j] == 0 || state_[j] == 2) continue;
            if (--blocked_[j] == 0 && state_[j] == 1) released_.push_back(j);
        }
}

void ActorMerge::emitActor(std::uint32_t a) {
    aState_[a] = 2;
    seq_.push_back({a, true});
    bound_ = actors_[a].page;
    for (std::uint32_t q = aSuccStart_[a]; q < aSuccStart_[a + 1]; ++q) {
        const std::uint32_t k = aSucc_[q];
        if (--blocked_[k] == 0 && state_[k] == 1) released_.push_back(k);
    }
    for (std::uint32_t q = aaSuccStart_[a]; q < aaSuccStart_[a + 1]; ++q) {
        const std::uint32_t b = aaSucc_[q];
        if (--aIndeg_[b] == 0 && aState_[b] == 0) {
            aState_[b] = 1;
            pending_.push_back(b);
            added_ = true;
        }
    }
}

void ActorMerge::drain() {
    // Held elements whose last blocker went: overdue, so drawn at once, back to front.
    while (!released_.empty()) {
        const auto it = std::ranges::min_element(released_);
        const std::uint32_t k = *it;
        released_.erase(it);
        if (state_[k] == 1 && blocked_[k] == 0) emitElement(k);
    }
}

void ActorMerge::flushPending(bool all) {
    // Ready actors: those on the bound page go at once (no page switch); with `all`, every one,
    // grouped by page, back to front within a page. Each may make others ready: repeat.
    const auto key = [&](std::uint32_t a) {
        const FRect& f = actors_[a].box.foot;
        return f.x0 + f.x1 + f.y0 + f.y1;
    };
    while (!pending_.empty()) {
        const int bound = bound_;
        // Taken out first: emitting appends the newly ready to pending_.
        const auto cut =
            all ? pending_.end() : std::ranges::partition(pending_, [&](std::uint32_t a) {
                                       return actors_[a].page == bound;
                                   }).begin();
        if (cut == pending_.begin()) break;
        fill_.assign(pending_.begin(), cut);
        pending_.erase(pending_.begin(), cut);
        std::ranges::sort(fill_, [&](std::uint32_t a, std::uint32_t b) {
            const bool ab = actors_[a].page == bound;
            const bool bb = actors_[b].page == bound;
            if (ab != bb) return ab;
            if (actors_[a].page != actors_[b].page) return actors_[a].page < actors_[b].page;
            const float ka = key(a);
            const float kb = key(b);
            return ka != kb ? ka < kb : a < b;
        });
        for (const std::uint32_t a : fill_) {
            emitActor(a);
            drain();
        }
    }
}

int orderViolations(std::span<const OrderItem> items, std::span<const OrderItem> actors,
                    std::span<const ActorMerge::Step> seq, bool actorPairs,
                    std::pair<DepthBox, DepthBox>* first) {
    std::vector<const OrderItem*> drawn;
    std::vector<bool> actor;
    std::vector<FRect> screens;
    drawn.reserve(seq.size());
    screens.reserve(seq.size());
    for (const ActorMerge::Step& st : seq) {
        drawn.push_back(st.actor ? &actors[st.index] : &items[st.index]);
        actor.push_back(st.actor);
        screens.push_back(drawn.back()->screen);
    }
    ScreenGrid grid;
    grid.build(screens, 128.0f);
    int bad = 0;
    grid.pairs(screens, [&](std::uint32_t i, std::uint32_t j) {
        // i < j: i was drawn first, so it must be the one behind.
        if ((actorPairs || !actor[i] || !actor[j]) && constrains(drawn[i]->box, drawn[j]->box) &&
            !drawnBefore(drawn[i]->box, drawn[j]->box)) {
            if (bad == 0 && first != nullptr) *first = {drawn[i]->box, drawn[j]->box};
            ++bad;
        }
    });
    return bad;
}

std::vector<std::vector<std::uint32_t>> orderCycles(std::span<const OrderItem> items, float cell,
                                                    std::size_t limit) {
    const std::size_t n = items.size();
    std::vector<FRect> screens(n);
    for (std::size_t i = 0; i < n; ++i) screens[i] = items[i].screen;
    ScreenGrid grid;
    grid.build(screens, cell);
    std::vector<std::vector<std::uint32_t>> next(n);
    std::vector<std::vector<std::uint32_t>> prev(n);
    std::vector<int> indegree(n, 0);
    grid.pairs(screens, [&](std::uint32_t i, std::uint32_t j) {
        if (!constrains(items[i].box, items[j].box)) return;
        const bool ij = drawnBefore(items[i].box, items[j].box);
        next[ij ? i : j].push_back(ij ? j : i);
        prev[ij ? j : i].push_back(ij ? i : j);
        ++indegree[ij ? j : i];
    });
    // Peel off everything Kahn's sort can draw; every element left waits for another one left,
    // so walking back through those always comes round to a cycle.
    std::vector<std::uint32_t> ready;
    for (std::uint32_t i = 0; i < n; ++i)
        if (indegree[i] == 0) ready.push_back(i);
    while (!ready.empty()) {
        const std::uint32_t i = ready.back();
        ready.pop_back();
        for (const std::uint32_t j : next[i])
            if (--indegree[j] == 0) ready.push_back(j);
    }
    std::vector<std::vector<std::uint32_t>> out;
    std::vector<int> seenAt(n, -1);
    for (std::uint32_t s0 = 0; s0 < n && out.size() < limit; ++s0) {
        if (indegree[s0] <= 0) continue;
        std::vector<std::uint32_t> path;
        std::uint32_t v = s0;
        bool stuck = false;
        while (seenAt[v] < 0) {
            seenAt[v] = static_cast<int>(path.size());
            path.push_back(v);
            const auto it =
                std::ranges::find_if(prev[v], [&](std::uint32_t u) { return indegree[u] > 0; });
            if (it == prev[v].end()) {
                stuck = true; // its waiting was on a cycle already taken out
                break;
            }
            v = *it;
        }
        if (!stuck) {
            std::vector<std::uint32_t> cycle(path.begin() + seenAt[v], path.end());
            std::ranges::reverse(cycle); // walked backwards: put it in drawing order
            out.push_back(std::move(cycle));
        }
        for (const std::uint32_t p : path) {
            indegree[p] = 0;
            seenAt[p] = -1;
        }
    }
    return out;
}

int pageSwitches(std::span<const OrderItem> items, std::span<const std::uint32_t> order) {
    int switches = 0;
    for (std::size_t k = 1; k < order.size(); ++k)
        if (items[order[k]].page != items[order[k - 1]].page) ++switches;
    return switches;
}

} // namespace lc
