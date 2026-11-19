// Properties of the one depth comparator and its sort (docs/design/draw-order.md §6.2): on
// random and adversarial boxes (long thin pieces, pieces of L-shaped footprints, stacked levels,
// decks over boats, actors among them) it is irreflexive, antisymmetric, free of 3-cycles among
// boxes whose screens overlap pairwise, unchanged by moving everything by whole tiles, and the
// sort's result does not depend on the order its input came in.

#include "core/rng.hpp"
#include "render/depth.hpp"
#include "render/order.hpp"

#include <doctest.h>

#include <algorithm>
#include <vector>

using namespace lc;

namespace {

constexpr Iso kIso{32, 16};

// The screen box of a box standing on the ground: its footprint's diamond from z0 up to z1.
FRect screenOf(const DepthBox& b) {
    const Vec2 top = kIso.toWorld(b.foot.x0, b.foot.y0);
    const Vec2 right = kIso.toWorld(b.foot.x1, b.foot.y0);
    const Vec2 bottom = kIso.toWorld(b.foot.x1, b.foot.y1);
    const Vec2 left = kIso.toWorld(b.foot.x0, b.foot.y1);
    return {left.x, top.y - b.z1, right.x, bottom.y - b.z0};
}

std::uint32_t gId = 1;
DepthBox box(float x0, float y0, float x1, float y1, float z0, float z1) {
    return makeBox({x0, y0, x1, y1}, z0, z1, depthId(DepthKind::Item, gId++), kIso.hh);
}

// Ground-standing boxes with disjoint footprints: long thin runs, squares, the pieces of an
// L-shaped landmark, on random levels; and actors on free ground between them.
std::vector<DepthBox> groundScene(Rng& rng, int n) {
    std::vector<DepthBox> out;
    std::vector<std::uint8_t> used(64 * 64, 0);
    const auto take = [&](int x, int y, int w, int h) {
        for (int j = y; j < y + h; ++j)
            for (int i = x; i < x + w; ++i)
                if (used[static_cast<std::size_t>(j * 64 + i)] != 0) return false;
        for (int j = y; j < y + h; ++j)
            for (int i = x; i < x + w; ++i) used[static_cast<std::size_t>(j * 64 + i)] = 1;
        return true;
    };
    for (int k = 0; k < n * 4 && static_cast<int>(out.size()) < n; ++k) {
        const int shape = rng.range(0, 3);
        const int x = rng.range(0, 54);
        const int y = rng.range(0, 54);
        const float level = static_cast<float>(rng.range(0, 3) * 16);
        const auto f = [](int v) { return static_cast<float>(v); };
        if (shape == 0) { // a long thin run along x or y
            const bool alongX = rng.chance(0.5f);
            const int len = rng.range(3, 8);
            if (take(x, y, alongX ? len : 1, alongX ? 1 : len))
                out.push_back(box(f(x), f(y), f(x + (alongX ? len : 1)), f(y + (alongX ? 1 : len)),
                                  level, level + rng.range(10.0f, 200.0f)));
        } else if (shape == 1) { // an L of two pieces, one landmark's height
            if (take(x, y, 6, 2) && take(x, y + 2, 2, 4)) {
                const float h = rng.range(40.0f, 220.0f);
                out.push_back(box(f(x), f(y), f(x + 6), f(y + 2), level, level + h));
                out.push_back(box(f(x), f(y + 2), f(x + 2), f(y + 6), level, level + h));
            }
        } else if (shape == 2) { // a square item
            const int w = rng.range(1, 4);
            if (take(x, y, w, w))
                out.push_back(
                    box(f(x), f(y), f(x + w), f(y + w), level, level + rng.range(5.0f, 90.0f)));
        } else if (take(x, y, 1, 1)) { // an actor on a free tile
            const float cx = f(x) + rng.range(0.25f, 0.75f);
            const float cy = f(y) + rng.range(0.25f, 0.75f);
            out.push_back(box(cx - 0.2f, cy - 0.2f, cx + 0.2f, cy + 0.2f, level,
                              level + rng.range(20.0f, 74.0f)));
        }
    }
    return out;
}

} // namespace

TEST_CASE("order props: the comparator is irreflexive and antisymmetric on any boxes") {
    Rng rng(7);
    for (int i = 0; i < 100000; ++i) {
        const float x = rng.range(0.0f, 10.0f);
        const float y = rng.range(0.0f, 10.0f);
        const float z = rng.range(0.0f, 100.0f);
        const DepthBox a = box(x, y, x + rng.range(0.1f, 8.0f), y + rng.range(0.1f, 8.0f), z,
                               z + rng.range(1.0f, 200.0f));
        // Often overlapping it, sometimes equal in every coordinate but the id.
        const DepthBox b = rng.chance(0.05f)
                               ? DepthBox{a.foot, a.z0, a.z1, a.id + 1, a.near}
                               : box(x + rng.range(-3.0f, 3.0f), y + rng.range(-3.0f, 3.0f),
                                     x + rng.range(0.5f, 6.0f), y + rng.range(0.5f, 6.0f),
                                     rng.range(0.0f, 100.0f), rng.range(100.0f, 300.0f));
        CHECK_FALSE(drawnBefore(a, a));
        CHECK(drawnBefore(a, b) != drawnBefore(b, a));
    }
}

TEST_CASE("order props: no 3-cycle among ground-standing boxes that overlap on screen") {
    Rng rng(11);
    int triples = 0;
    for (int scene = 0; scene < 40; ++scene) {
        const std::vector<DepthBox> boxes = groundScene(rng, 160);
        std::vector<FRect> screens;
        for (const DepthBox& b : boxes) screens.push_back(screenOf(b));
        for (std::size_t i = 0; i < boxes.size(); ++i)
            for (std::size_t j = i + 1; j < boxes.size(); ++j) {
                if (!screens[i].overlaps(screens[j])) continue;
                for (std::size_t k = j + 1; k < boxes.size(); ++k) {
                    if (!screens[i].overlaps(screens[k]) || !screens[j].overlaps(screens[k]))
                        continue;
                    // A cycle needs every pair to be an edge of the sort.
                    if (!constrains(boxes[i], boxes[j]) || !constrains(boxes[j], boxes[k]) ||
                        !constrains(boxes[i], boxes[k]))
                        continue;
                    ++triples;
                    const bool ij = drawnBefore(boxes[i], boxes[j]);
                    const bool jk = drawnBefore(boxes[j], boxes[k]);
                    const bool ki = drawnBefore(boxes[k], boxes[i]);
                    // A cycle is all three one way round (or all three the other).
                    const bool cycle = (ij && jk && ki) || (!ij && !jk && !ki);
                    CAPTURE(scene);
                    CHECK_FALSE(cycle);
                }
            }
    }
    CHECK(triples > 2000);
}

TEST_CASE("order props: stacked boxes: decks, boats, walkers and the parapets beside them") {
    // A deck run over water with its parapets, a boat under it and a walker on it at random
    // places along the run. Deck, parapets and each mover are always ordered as the model says.
    // The two movers can close a cycle through the deck (the walker further back on the deck,
    // the boat nearer the camera under it): the merge then gives up the walker-boat edge, never
    // the deck's, and counts it.
    Rng rng(5);
    int cycles = 0;
    for (int t = 0; t < 2000; ++t) {
        const float len = static_cast<float>(rng.range(2, 8));
        const DepthBox deck = box(1, 0, 2, len, 18, 26);
        const DepthBox farSide = box(0, 0, 1, len, 0, 31);
        const DepthBox nearSide = box(2, 0, 3, len, 0, 31);
        const float wy = rng.range(0.3f, len - 0.3f);
        const float by = rng.range(0.3f, len - 0.3f);
        const DepthBox walker =
            box(1.3f, wy - 0.2f, 1.7f, wy + 0.2f, 24, 24 + rng.range(30.0f, 50.0f));
        const DepthBox boat = box(1.3f, by - 0.2f, 1.7f, by + 0.2f, 0, rng.range(20.0f, 80.0f));
        CHECK(drawnBefore(deck, walker));
        CHECK(drawnBefore(boat, deck));
        CHECK(drawnBefore(farSide, walker));
        CHECK(drawnBefore(walker, nearSide));
        CHECK(drawnBefore(farSide, boat));
        CHECK(drawnBefore(boat, nearSide));
        // In one merged order.
        std::vector<OrderItem> statics;
        for (const DepthBox& b : {deck, farSide, nearSide}) statics.push_back({b, screenOf(b), 0});
        std::vector<OrderItem> movers;
        for (const DepthBox& b : {walker, boat}) movers.push_back({b, screenOf(b), 1});
        PageOrder sorter;
        OrderGraph graph;
        std::vector<std::uint32_t> order;
        sorter.sort(statics, 128, order, graph);
        ActorMerge m;
        m.index(statics, order, graph, 128);
        m.plan(statics, movers, {-1e9f, -1e9f, 1e9f, 1e9f});
        CHECK(orderViolations(statics, movers, m.sequence(), false) == 0);
        cycles += m.cyclesBroken();
    }
    MESSAGE(cycles << " walker-boat cycles broken in 2000 scenes");
    CHECK(cycles > 0);
}

TEST_CASE("order props: moving everything by whole tiles changes no pair") {
    Rng rng(3);
    const std::vector<DepthBox> boxes = groundScene(rng, 200);
    for (int t = 0; t < 5; ++t) {
        const auto dx = static_cast<float>(rng.range(-100, 100));
        const auto dy = static_cast<float>(rng.range(-100, 100));
        for (std::size_t i = 0; i < boxes.size(); ++i)
            for (std::size_t j = i + 1; j < boxes.size(); ++j) {
                const auto moved = [&](const DepthBox& b) {
                    return makeBox({b.foot.x0 + dx, b.foot.y0 + dy, b.foot.x1 + dx, b.foot.y1 + dy},
                                   b.z0, b.z1, b.id, kIso.hh);
                };
                CHECK(drawnBefore(boxes[i], boxes[j]) ==
                      drawnBefore(moved(boxes[i]), moved(boxes[j])));
            }
    }
}

TEST_CASE("order props: the sort's result does not depend on the order of its input") {
    Rng rng(9);
    const std::vector<DepthBox> boxes = groundScene(rng, 250);
    std::vector<OrderItem> items;
    for (const DepthBox& b : boxes) items.push_back({b, screenOf(b), 0});
    PageOrder sorter;
    OrderGraph graph;
    std::vector<std::uint32_t> order;
    sorter.sort(items, 128, order, graph);
    CHECK(sorter.cyclesBroken() == 0);
    std::vector<std::uint64_t> ids;
    for (const std::uint32_t i : order) ids.push_back(items[i].box.id);
    // The overlapping pairs come out the same way round whatever the input order.
    for (int t = 0; t < 4; ++t) {
        std::vector<OrderItem> shuffled = items;
        for (std::size_t i = shuffled.size(); i > 1; --i)
            std::swap(shuffled[i - 1],
                      shuffled[static_cast<std::size_t>(rng.range(0, static_cast<int>(i) - 1))]);
        std::vector<std::uint32_t> o2;
        sorter.sort(shuffled, 128, o2, graph);
        std::vector<std::size_t> at(shuffled.size());
        for (std::size_t k = 0; k < o2.size(); ++k) at[o2[k]] = k;
        int wrong = 0;
        for (std::size_t i = 0; i < shuffled.size(); ++i)
            for (std::size_t j = i + 1; j < shuffled.size(); ++j)
                if (shuffled[i].screen.overlaps(shuffled[j].screen) &&
                    constrains(shuffled[i].box, shuffled[j].box) &&
                    drawnBefore(shuffled[i].box, shuffled[j].box) != (at[i] < at[j]))
                    ++wrong;
        CHECK(wrong == 0);
    }
}

TEST_CASE("order props: a broken comparator is caught by the oracle") {
    // The oracle on boxes (orderViolations) counts pairs drawn against the comparator: the
    // sort's own order has none, the reverse of it many.
    Rng rng(13);
    const std::vector<DepthBox> boxes = groundScene(rng, 200);
    std::vector<OrderItem> items;
    for (const DepthBox& b : boxes) items.push_back({b, screenOf(b), 0});
    PageOrder sorter;
    OrderGraph graph;
    std::vector<std::uint32_t> order;
    sorter.sort(items, 128, order, graph);
    std::vector<ActorMerge::Step> seq;
    for (const std::uint32_t i : order) seq.push_back({i, false});
    CHECK(orderViolations(items, {}, seq) == 0);
    std::ranges::reverse(seq);
    CHECK(orderViolations(items, {}, seq) > 50);
}
