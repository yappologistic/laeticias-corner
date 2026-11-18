#include "worldview/order.hpp"

#include <algorithm>
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

int pageSwitches(std::span<const OrderItem> items, std::span<const std::uint32_t> order) {
    int switches = 0;
    for (std::size_t k = 1; k < order.size(); ++k)
        if (items[order[k]].page != items[order[k - 1]].page) ++switches;
    return switches;
}

} // namespace lc::worldview
