// The world's painter's order with heights (docs/design/draw-order.md): valid on random scenes
// with fewer page switches, split landmarks, raised ground, and the owner's places as fixtures
// built from the art's own geometry fields: a bridge with a boat under it and a walker on it, a
// gate's passage, a colonnade, a stair; actors merged exactly; the coarser levels' cut.

#include "worldview/actor_looks.hpp"
#include "worldview/cover.hpp"
#include "worldview/gather.hpp"
#include "worldview/tuning.hpp"

#include <doctest.h>

#include <algorithm>
#include <random>
#include <vector>

using namespace lc;
using namespace lc::worldview;

namespace {

constexpr Iso kIso{32, 16};
constexpr FRect kEverywhere{-1e9f, -1e9f, 1e9f, 1e9f}; // a view that culls nothing

// The screen box of a footprint raised z0 and extruded to z1, as a sprite covers it.
FRect boxOf(FRect f, float z1, float z0 = 0) {
    const Vec2 top = kIso.toWorld(f.x0, f.y0);
    const Vec2 right = kIso.toWorld(f.x1, f.y0);
    const Vec2 bottom = kIso.toWorld(f.x1, f.y1);
    const Vec2 left = kIso.toWorld(f.x0, f.y1);
    return {left.x, top.y - z1, right.x, bottom.y - z0};
}

std::uint32_t nextId = 1;
OrderItem item(FRect f, float z0, float z1, std::uint16_t page = 0) {
    return {makeBox(f, z0, z1, depthId(DepthKind::Item, nextId++), kIso.hh), boxOf(f, z1, z0),
            page};
}

// An actor standing at (x, y) on a floor `z`, `tall` px high.
OrderItem actor(float x, float y, float z, float tall, std::uint16_t page = 3) {
    const float k = lc::worldview::tuning::kActorFoot;
    const Vec2 a = kIso.toWorld(x, y);
    return {makeBox({x - k, y - k, x + k, y + k}, z, z + tall, depthId(DepthKind::Actor, nextId++),
                    kIso.hh),
            {a.x - 8, a.y - z - tall, a.x + 8, a.y - z},
            page};
}

// Every pair of overlapping boxes appears in painter's order.
bool valid(const std::vector<OrderItem>& items, const std::vector<std::uint32_t>& order) {
    std::vector<std::size_t> at(items.size());
    for (std::size_t k = 0; k < order.size(); ++k) at[order[k]] = k;
    for (std::size_t i = 0; i < items.size(); ++i)
        for (std::size_t j = i + 1; j < items.size(); ++j) {
            if (!items[i].screen.overlaps(items[j].screen)) continue;
            if (drawnBefore(items[i].box, items[j].box) != (at[i] < at[j])) return false;
        }
    return true;
}

// Non-overlapping footprints on a grid with random sizes, heights and pages.
std::vector<OrderItem> scene(std::uint32_t seed, int pages) {
    std::mt19937 rng(seed);
    std::vector<OrderItem> items;
    std::vector<int> taken(40 * 40, 0);
    for (int n = 0; n < 400; ++n) {
        const int x = static_cast<int>(rng() % 38);
        const int y = static_cast<int>(rng() % 38);
        const int w = 1 + static_cast<int>(rng() % 3);
        const int h = 1 + static_cast<int>(rng() % 3);
        bool free = true;
        for (int j = y; j < y + h; ++j)
            for (int i = x; i < x + w; ++i)
                free = free && taken[static_cast<std::size_t>(j * 40 + i)] == 0;
        if (!free) continue;
        for (int j = y; j < y + h; ++j)
            for (int i = x; i < x + w; ++i) taken[static_cast<std::size_t>(j * 40 + i)] = 1;
        const FRect f{static_cast<float>(x), static_cast<float>(y), static_cast<float>(x + w),
                      static_cast<float>(y + h)};
        items.push_back(item(f, 0, static_cast<float>(1 + rng() % 120),
                             static_cast<std::uint16_t>(rng() % static_cast<unsigned>(pages))));
    }
    return items;
}

// The positions of a merged sequence: statics by element, actors by actor.
struct Placed {
    std::vector<std::size_t> statics;
    std::vector<std::size_t> actors;
};
Placed placedOf(const ActorMerge& m, std::size_t ns, std::size_t na) {
    Placed p{std::vector<std::size_t>(ns, ~0u), std::vector<std::size_t>(na, ~0u)};
    const auto seq = m.sequence();
    for (std::size_t k = 0; k < seq.size(); ++k)
        (seq[k].actor ? p.actors : p.statics)[seq[k].index] = k;
    return p;
}

// Merges `actors` into the sorted `items` and returns where everything went.
Placed mergeAll(const std::vector<OrderItem>& items, const std::vector<OrderItem>& actors,
                ActorMerge& m) {
    PageOrder sorter;
    OrderGraph graph;
    std::vector<std::uint32_t> order;
    sorter.sort(items, 64.0f, order, graph);
    m.index(items, order, graph, 64.0f);
    m.plan(items, actors, kEverywhere);
    return placedOf(m, items.size(), actors.size());
}

} // namespace

TEST_CASE("depth: page-aware order is a valid painter's order with fewer page switches") {
    PageOrder sorter;
    OrderGraph graph;
    std::vector<std::uint32_t> order;
    int awareSwitches = 0;
    int plainSwitches = 0;
    for (std::uint32_t seed = 1; seed <= 6; ++seed) {
        std::vector<OrderItem> items = scene(seed, 3);
        sorter.sort(items, 128, order, graph);
        REQUIRE(order.size() == items.size());
        CHECK(valid(items, order));
        CHECK(sorter.cyclesBroken() == 0);
        awareSwitches += pageSwitches(items, order);
        // The same scene with every element on one page sorts by depth alone.
        std::vector<OrderItem> one = items;
        for (OrderItem& it : one) it.page = 0;
        std::vector<std::uint32_t> plain;
        sorter.sort(one, 128, plain, graph);
        CHECK(valid(one, plain));
        plainSwitches += pageSwitches(items, plain);
    }
    CHECK(awareSwitches * 2 < plainSwitches);
}

TEST_CASE("depth: a split landmark's pieces sort among the items around and inside it") {
    // A 12 x 6 landmark cut into pieces of at most 8 x 8, with a walk run through it, and
    // single items before, behind and beside it.
    std::vector<OrderItem> items;
    const std::vector<FRect> pieces{
        {10, 10, 18, 13}, {10, 13, 18, 16}, {18, 10, 22, 16}, {10, 16, 22, 17}};
    for (const FRect& p : pieces) items.push_back(item(p, 0, 160, 1));
    for (const FRect& f : std::vector<FRect>{
             {9, 12, 10, 13}, {23, 12, 24, 13}, {14, 18, 15, 19}, {14, 9, 15, 10}, {22, 9, 23, 10}})
        items.push_back(item(f, 0, 60));
    PageOrder sorter;
    OrderGraph graph;
    std::vector<std::uint32_t> order;
    sorter.sort(items, 128, order, graph);
    CHECK(valid(items, order));
    std::vector<std::size_t> at(items.size());
    for (std::size_t k = 0; k < order.size(); ++k) at[order[k]] = k;
    CHECK(at[7] < at[0]); // the item behind the landmark's back piece comes first
    CHECK(at[3] < at[6]); // the front run before the item in front of it
    CHECK(at[1] < at[3]);
}

TEST_CASE("depth: a raised tile goes under what stands on it and over what it hides") {
    const FRect tile{5, 5, 6, 6};
    const OrderItem ground = item(tile, 0, 48);              // level 3
    const OrderItem on = item({5, 5, 6, 6}, 48, 100);        // a tree on it
    const OrderItem behindIt = item({4, 5, 5, 6}, 16, 50);   // lower, behind it
    const OrderItem walkerOn = actor(5.5f, 5.5f, 48, 40);    // standing on it
    const OrderItem walkerBehind = actor(4.5f, 4.5f, 0, 40); // on the ground behind it
    CHECK(drawnBefore(ground.box, on.box));
    CHECK_FALSE(drawnBefore(on.box, ground.box));
    CHECK(drawnBefore(behindIt.box, ground.box));
    CHECK(drawnBefore(ground.box, walkerOn.box));
    CHECK(drawnBefore(walkerBehind.box, ground.box));
}

TEST_CASE("depth: a bridge carries walkers between its parapets and boats pass under its deck") {
    // rome.pons_fabricius r0 as its geometry gives it: a deck run x 1..2 over the river, walk_z
    // 20-24, under 18; parapet pieces either side; level 0 water.
    const world::GeomVariant g = [] {
        world::GeomVariant v;
        v.h = 56;
        v.pieces = {{{1, 0, 2, 4}, true, 18}, {{0, 0, 1, 4}, false, 0}, {{2, 0, 3, 4}, false, 0}};
        v.walk = {{1, 0}, {1, 1}, {1, 2}, {1, 3}};
        v.walkZ = {{{1, 0}, 20}, {{1, 1}, 24}, {{1, 2}, 24}, {{1, 3}, 20}};
        v.tops = {29, 20, 29, 31, 24, 31, 31, 24, 31, 29, 20, 29};
        v.topsW = 3;
        return v;
    }();
    world::ItemInfo info;
    info.walkable = true;
    info.crossing = true;
    const ZRange deck = heightsOf(&g, info, 0, 100);
    const ZRange farSide = heightsOf(&g, info, 1, 100);
    const ZRange nearSide = heightsOf(&g, info, 2, 100);
    CHECK(deck.z0 == 18);
    CHECK(deck.z1 == 24 + lc::tuning::kFloorTread);
    CHECK(farSide.z0 == 0);
    CHECK(farSide.z1 == 31);
    const OrderItem d = item({1, 0, 2, 4}, deck.z0, deck.z1);
    const OrderItem pFar = item({0, 0, 1, 4}, farSide.z0, farSide.z1);
    const OrderItem pNear = item({2, 0, 3, 4}, nearSide.z0, nearSide.z1);
    const OrderItem walker = actor(1.5f, 1.7f, 24, 44);
    const OrderItem barge = actor(1.5f, 2.0f, 0, 74); // taller than the clearance: its mast shows
    // The walker on the deck: after the deck and the far parapet, before the near one.
    CHECK(drawnBefore(d.box, walker.box));
    CHECK(drawnBefore(pFar.box, walker.box));
    CHECK(drawnBefore(walker.box, pNear.box));
    // The barge under it: before the deck (the deck hides it), after the far parapet.
    CHECK(drawnBefore(barge.box, d.box));
    CHECK(drawnBefore(pFar.box, barge.box));
    CHECK(drawnBefore(barge.box, pNear.box));
    // Walker over barge, wherever the barge is under the deck.
    CHECK(drawnBefore(barge.box, walker.box));
    // All of it in one merged order.
    const std::vector<OrderItem> statics{d, pFar, pNear};
    ActorMerge m;
    const Placed p = mergeAll(statics, {walker, barge}, m);
    CHECK(p.actors[1] < p.statics[0]);
    CHECK(p.statics[0] < p.actors[0]);
    CHECK(p.statics[1] < p.actors[0]);
    CHECK(p.actors[0] < p.statics[2]);
    CHECK(m.cyclesBroken() == 0);
}

TEST_CASE("depth: a gate's roof goes over who walks through it, a colonnade's columns round them") {
    // parsa.gate_all_lands: a passage run under a roof (under 151, roof 164), no floor pixels.
    world::GeomVariant g;
    g.h = 216;
    g.pieces = {{{1, 2, 6, 3}, false, 151}, {{0, 0, 1, 6}, false, 0}};
    g.walk = {{1, 2}, {2, 2}, {3, 2}, {4, 2}, {5, 2}};
    g.roof = {{{1, 2}, 167}, {{2, 2}, 164}, {{3, 2}, 164}, {{4, 2}, 164}, {{5, 2}, 176}};
    const world::ItemInfo info;
    const ZRange run = heightsOf(&g, info, 0, 300);
    CHECK(run.z0 == 151);
    CHECK(run.z1 == 216);
    const OrderItem roof = item({1, 2, 6, 3}, run.z0, run.z1);
    const OrderItem walker = actor(3.5f, 2.5f, 0, 46);
    const OrderItem cart = actor(4.5f, 2.5f, 0, 70);
    CHECK(drawnBefore(walker.box, roof.box));
    CHECK(drawnBefore(cart.box, roof.box));
    // Athens' stoa: the walk run is a floor (stylobate 5 px) with the roof in the same piece:
    // the floor goes under the walker; columns either side order by where they stand.
    world::GeomVariant stoa;
    stoa.h = 104;
    stoa.pieces = {{{1, 0, 2, 8}, true, 0}, {{0, 0, 1, 8}, false, 0}, {{2, 0, 3, 8}, false, 0}};
    for (int y = 0; y < 8; ++y) {
        stoa.walk.push_back({1, y});
        stoa.walkZ.push_back({{1, y}, 5});
        stoa.roof.push_back({{1, y}, 96});
    }
    const ZRange floor = heightsOf(&stoa, info, 0, 200);
    CHECK(floor.z0 == 0);
    CHECK(floor.z1 == 5 + lc::tuning::kFloorTread);
    const OrderItem walk = item({1, 0, 2, 8}, floor.z0, floor.z1);
    const OrderItem backColumns = item({0, 0, 1, 8}, 0, 104);
    const OrderItem frontColumns = item({2, 0, 3, 8}, 0, 104);
    const OrderItem inside = actor(1.5f, 4.5f, 5, 44);
    CHECK(drawnBefore(walk.box, inside.box));
    CHECK(drawnBefore(backColumns.box, inside.box));
    CHECK(drawnBefore(inside.box, frontColumns.box));
}

TEST_CASE("depth: a walker on a stair is over the treads behind and under the ones in front") {
    // A flight of four tread rows climbing -y (rows at smaller y are higher), parapets beside.
    std::vector<OrderItem> statics;
    for (int r = 0; r < 4; ++r) {
        const float z = static_cast<float>((4 - r) * 8);
        statics.push_back(item({1, static_cast<float>(r), 5, static_cast<float>(r + 1)}, 0,
                               z + lc::tuning::kFloorTread));
    }
    statics.push_back(item({0, 0, 1, 4}, 0, 48)); // the far parapet
    statics.push_back(item({5, 0, 6, 4}, 0, 48)); // the near parapet
    // Climbing: on row 2 (floor 16), near its upper edge, so its feet reach into row 1.
    const OrderItem w = actor(3.0f, 2.1f, 17, 44);
    for (int r = 0; r < 2; ++r) CHECK(drawnBefore(statics[static_cast<std::size_t>(r)].box, w.box));
    CHECK(drawnBefore(statics[2].box, w.box)); // the tread it stands on
    CHECK(drawnBefore(w.box, statics[3].box)); // the lower tread in front
    CHECK(drawnBefore(statics[4].box, w.box));
    CHECK(drawnBefore(w.box, statics[5].box));
    ActorMerge m;
    const Placed p = mergeAll(statics, {w}, m);
    CHECK(p.statics[2] < p.actors[0]);
    CHECK(p.actors[0] < p.statics[3]);
    CHECK(p.actors[0] < p.statics[5]);
}

TEST_CASE("depth: actors merge exactly, crossings included, at a few page switches") {
    for (std::uint32_t seed = 1; seed <= 6; ++seed) {
        const std::vector<OrderItem> items = scene(seed, 3);
        std::mt19937 rng(seed * 7);
        std::vector<OrderItem> actors;
        while (actors.size() < 160) {
            const float x = static_cast<float>(rng() % 3800) / 100.0f;
            const float y = static_cast<float>(rng() % 3800) / 100.0f;
            bool free = true;
            for (const OrderItem& it : items)
                free = free && !(x >= it.box.foot.x0 - 0.2f && x < it.box.foot.x1 + 0.2f &&
                                 y >= it.box.foot.y0 - 0.2f && y < it.box.foot.y1 + 0.2f);
            if (free) actors.push_back(actor(x, y, 0, 40));
        }
        ActorMerge m;
        const Placed p = mergeAll(items, actors, m);
        REQUIRE(m.sequence().size() == items.size() + actors.size());
        int pairs = 0;
        int wrong = 0;
        for (std::size_t a = 0; a < actors.size(); ++a) {
            for (std::size_t e = 0; e < items.size(); ++e) {
                if (!items[e].screen.overlaps(actors[a].screen)) continue;
                ++pairs;
                if (drawnBefore(items[e].box, actors[a].box) != (p.statics[e] < p.actors[a]))
                    ++wrong;
            }
            for (std::size_t b = a + 1; b < actors.size(); ++b) {
                if (!actors[a].screen.overlaps(actors[b].screen)) continue;
                ++pairs;
                if (drawnBefore(actors[a].box, actors[b].box) != (p.actors[a] < p.actors[b]))
                    ++wrong;
            }
        }
        // The statics among themselves keep a valid order too (held ones included).
        for (std::size_t i = 0; i < items.size(); ++i)
            for (std::size_t j = i + 1; j < items.size(); ++j)
                if (items[i].screen.overlaps(items[j].screen) &&
                    drawnBefore(items[i].box, items[j].box) != (p.statics[i] < p.statics[j]))
                    ++wrong;
        CAPTURE(seed);
        CHECK(pairs > 200);
        CHECK(wrong == 0);
        CHECK(m.cyclesBroken() == 0);
        // The crowd (its own page) costs a handful of page switches, not one per person.
        int switches = 0;
        int last = -1;
        for (const ActorMerge::Step& st : m.sequence()) {
            const int page = st.actor ? actors[st.index].page : items[st.index].page;
            switches += last >= 0 && page != last ? 1 : 0;
            last = page;
        }
        PageOrder sorter;
        OrderGraph graph;
        std::vector<std::uint32_t> order;
        sorter.sort(items, 64.0f, order, graph);
        const int added = switches - pageSwitches(items, order);
        MESSAGE("seed " << seed << ": " << pairs << " pairs, " << m.heldBack() << " held back, "
                        << added << " switches for " << actors.size() << " actors");
        CHECK(added <= 80);
    }
}

TEST_CASE("depth: two statics that do not meet, an actor between them: the order bends") {
    // The audit's M3: a bush in front of a walker and a wall behind it, the two far apart on
    // screen, so the static order may put the bush first. The walker must still go after the
    // wall and before the bush.
    const OrderItem bush = item({5, 6, 6, 7}, 0, 20, 0);
    const OrderItem wall = item({5, 2, 6, 5}, 0, 120, 1);
    const OrderItem w = actor(5.5f, 5.5f, 0, 44);
    REQUIRE(drawnBefore(w.box, bush.box));
    REQUIRE(drawnBefore(wall.box, w.box));
    REQUIRE_FALSE(bush.screen.overlaps(wall.screen));
    REQUIRE(w.screen.overlaps(bush.screen));
    REQUIRE(w.screen.overlaps(wall.screen));
    const std::vector<OrderItem> statics{bush, wall};
    // Force the static order to put the bush first (any order of the two is valid alone).
    ActorMerge m;
    m.index(statics, std::vector<std::uint32_t>{0, 1}, OrderGraph{{0, 0, 0}, {}}, 64.0f);
    m.plan(statics, std::vector<OrderItem>{w}, kEverywhere);
    const Placed p = placedOf(m, 2, 1);
    CHECK(p.statics[1] < p.actors[0]);
    CHECK(p.actors[0] < p.statics[0]);
    CHECK(m.heldBack() == 1);
}

TEST_CASE("actors: walk frames follow the distance walked, evenly, at any pace") {
    // Two walkers, one twice as fast: after the same distance both show the same frame, and a
    // frame lasts the same distance for both (feet never slide).
    const float fps = 8;
    const int n = 8;
    for (const float speed : {0.5f, 0.9f, 1.8f}) {
        float stride = 0;
        int changes = 0;
        int last = cycleFrame(true, 0, 0, fps, 0, n);
        float since = 0;
        float minRun = 1e9f;
        float maxRun = 0;
        for (int step = 0; step < 6000; ++step) {
            stride += speed / 600.0f;
            since += speed / 600.0f;
            const int f = cycleFrame(true, stride, 99.0f, fps, 0, n);
            if (f != last) {
                if (changes > 0) {
                    minRun = std::min(minRun, since);
                    maxRun = std::max(maxRun, since);
                }
                ++changes;
                since = 0;
                CHECK(f == (last + 1) % n);
                last = f;
            }
        }
        CAPTURE(speed);
        const float run = lc::worldview::tuning::kActorWalkPace / fps;
        CHECK(minRun > run - 0.01f);
        CHECK(maxRun < run + 0.01f);
        CHECK(cycleFrame(true, 3.0f, 0, fps, 0, n) == cycleFrame(true, 3.0f, 50, fps, 0, n));
        // The art's stride: twelve frames over 0.75 tiles, one per 0.0625 tiles walked.
        CHECK(cycleFrame(true, 0.75f * 2 + 0.0625f * 5 + 0.01f, 0, fps, 0.75f, 12) == 5);
    }
    CHECK(cycleFrame(false, 5.0f, 0.5f, 4, 0, 4) == 2);
}

TEST_CASE("cover: a box's silhouette at a screen column") {
    // A 4x2 building, 80 px tall: at its top vertex's column it spans its roof to its front.
    const FRect foot{10, 10, 14, 12};
    const Vec2 top = kIso.toWorld(10.0f, 10.0f);
    const RowBand s = silhouette(kIso, foot, 0, 80, top.x);
    CHECK(s.from == doctest::Approx(top.y - 80));
    CHECK(s.to == doctest::Approx(kIso.toWorld(12.0f, 12.0f).y)); // its front edge below it
    // Off to the side of its footprint: nothing.
    CHECK(silhouette(kIso, foot, 0, 80, kIso.toWorld(16.0f, 7.0f).x).empty());
    // A deck from 18 to 26 px: only that slab.
    const RowBand d = silhouette(kIso, {1, 0, 2, 4}, 18, 26, kIso.toWorld(1.5f, 2.0f).x);
    CHECK(d.to - d.from < kIso.tileH() + 8 + 1);
}
