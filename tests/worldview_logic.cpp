// The world renderer's pure parts: cell maths and caching policy, page eviction, the camera's
// precision and limits over the 448 x 1280 grid, theme sampling and captions, the viewer's
// options and script language.

#include "worldview/camera.hpp"
#include "worldview/cells.hpp"
#include "worldview/page_runs.hpp"
#include "worldview/places.hpp"
#include "worldview/script.hpp"
#include "worldview/terrain.hpp"
#include "worldview/theme.hpp"

#include <doctest.h>

#include <array>
#include <cmath>
#include <set>
#include <string_view>
#include <vector>

using namespace lc;
using namespace lc::worldview;

namespace {

constexpr Iso kIso{32, 16};
constexpr int kGridW = 448;
constexpr int kGridH = 1280;

} // namespace

TEST_CASE("cells: keys are unique and floor towards negative world x") {
    std::set<std::uint64_t> keys;
    for (int level = 0; level < 3; ++level)
        for (int cy = -3; cy < 3; ++cy)
            for (int cx = -110; cx < 40; cx += 7)
                CHECK(keys.insert(packCell({level, cx, cy})).second);
    // The world spans x from -40960 to 14336 px: cells west of x = 0 have negative columns.
    std::vector<CellKey> seen;
    forEachCell({-513, 0, 1, 10}, 0, [&](CellKey k) { seen.push_back(k); });
    REQUIRE(seen.size() == 3);
    CHECK(seen.front() == CellKey{0, -2, 0});
    CHECK(seen.back() == CellKey{0, 0, 0});
    const FRect r = cellRect({2, -1, 0});
    CHECK(r.x0 == -2048.0f);
    CHECK(r.x1 == 0.0f);
}

TEST_CASE("cells: every tile whose top vertex lies in a rect is under it") {
    const FRect px{-1000.5f, 300.25f, 777.0f, 1999.0f};
    const TileRect t = tilesUnder(px, kIso);
    for (int y = t.y0 - 5; y < t.y1 + 5; ++y)
        for (int x = t.x0 - 5; x < t.x1 + 5; ++x) {
            const Vec2 w = kIso.toWorld(TilePos{x, y});
            const bool inside = w.x >= px.x0 && w.x < px.x1 && w.y >= px.y0 && w.y < px.y1;
            if (inside) CHECK(t.contains(TilePos{x, y}));
        }
}

TEST_CASE("cells: the least recently used slot not used this frame is reused") {
    const std::array<std::uint64_t, 5> used{7, 3, 9, 3, 12};
    CHECK(lruSlot(used, 12) == 1); // the first of the oldest
    const std::array<std::uint64_t, 2> busy{4, 4};
    CHECK(lruSlot(busy, 4) == -1);
}

TEST_CASE("cells: work done ahead spares what the last frames used") {
    // Frame 12: slot 2 was used last frame, slot 4 this frame.
    const std::array<std::uint64_t, 5> used{7, 3, 11, 10, 12};
    CHECK(lruSlot(used, 12, 0) == 1);
    const std::array<std::uint64_t, 3> recent{11, 10, 12};
    CHECK(lruSlot(recent, 12, 0) == 1); // anything not used this frame may go
    CHECK(lruSlot(recent, 12, 1) == 1); // not what the last frame used
    CHECK(lruSlot(recent, 12, 2) == -1);
}

TEST_CASE("cells: each step of a cell's water has its own key") {
    std::set<std::uint64_t> keys;
    for (int level = 0; level < 3; ++level)
        for (int frame = 0; frame < 4; ++frame)
            for (int cx = -110; cx < 40; cx += 7)
                CHECK(keys.insert(packCell({level, cx, 2, frame})).second);
}

TEST_CASE("cells: a zoom about a point keeps that point where it is on screen") {
    const FRect view{1000, 500, 3000, 1500}; // 2000 x 1000 world px at scale 1
    const Vec2 pointer{1500, 1250};          // a quarter in, three quarters down
    const FRect out = zoomedAbout(view, pointer, 1.0f, 0.5f);
    CHECK(out.x1 - out.x0 == doctest::Approx(4000));
    CHECK(out.y1 - out.y0 == doctest::Approx(2000));
    CHECK((pointer.x - out.x0) / (out.x1 - out.x0) == doctest::Approx(0.25));
    CHECK((pointer.y - out.y0) / (out.y1 - out.y0) == doctest::Approx(0.75));
    // Zooming out about a point always shows everything the view showed.
    CHECK(out.x0 <= view.x0);
    CHECK(out.y1 >= view.y1);
    const FRect in = zoomedAbout(out, pointer, 0.5f, 1.0f);
    CHECK(in.x0 == doctest::Approx(view.x0));
    CHECK(in.y1 == doctest::Approx(view.y1));
}

TEST_CASE("pages: idle, unwanted pages are evicted oldest first, only while over budget") {
    const std::array<PageUse, 5> pages{{
        {64, 1.0, true, false},  // idle long: first out
        {64, 5.0, true, false},  // idle, newer
        {64, 0.5, true, true},   // wanted now: kept however old
        {64, 19.0, true, false}, // used recently: kept
        {64, 0.0, false, false}, // not resident
    }};
    CHECK(pagesToEvict(pages, 20.0, 10.0, 1000) == std::vector<int>{});
    CHECK(pagesToEvict(pages, 20.0, 10.0, 192) == std::vector<int>{0});
    CHECK(pagesToEvict(pages, 20.0, 10.0, 100) == std::vector<int>{0, 1});
    CHECK(pagesToEvict(pages, 20.0, 10.0, 0) == std::vector<int>{0, 1});
}

TEST_CASE("camera: precision and limits over the whole grid") {
    WorldCamera cam(kIso, kGridW, kGridH, 240);
    cam.setScreen({1920, 1080});
    // World pixels reach tens of thousands; positions round-trip through tiles to well under a
    // pixel at every corner of the grid.
    for (const Vec2 t :
         {Vec2{0, 0}, Vec2{448, 0}, Vec2{0, 1280}, Vec2{448, 1280}, Vec2{376.5f, 69.5f}}) {
        cam.lookAtTile(t);
        const Vec2 back = kIso.toTile(cam.centre());
        CHECK(std::abs(back.x - t.x) < 1e-2f);
        CHECK(std::abs(back.y - t.y) < 1e-2f);
        const Vec2 s = cam.worldToScreen(cam.screenToWorld({17.25f, 1003.5f}));
        CHECK(std::abs(s.x - 17.25f) < 0.01f);
        CHECK(std::abs(s.y - 1003.5f) < 0.01f);
    }
    // The centre never leaves the grid, however far it is pushed.
    cam.lookAtTile({-500, 2000});
    const Vec2 c = kIso.toTile(cam.centre());
    CHECK(c.x >= -1e-3f);
    CHECK(c.y <= 1280.001f);
    cam.panBy({1e6f, -1e6f});
    const Vec2 d = kIso.toTile(cam.centre());
    CHECK(d.x <= 448.001f);
    CHECK(d.y >= -1e-3f);
    const FRect box = cam.worldBox();
    CHECK(box.x1 - box.x0 == doctest::Approx(1728 * 32));
}

TEST_CASE("camera: zoom levels, the overview fits the world, flights arrive exactly") {
    WorldCamera cam(kIso, kGridW, kGridH, 240);
    cam.setScreen({1280, 800});
    CHECK(cam.levelFor(1) == 3);
    CHECK(cam.levelFor(0.25f) == 1);
    CHECK(cam.levelFor(0) == 0);
    cam.setLevel(0);
    const FRect v = cam.view();
    const FRect box = cam.worldBox();
    CHECK(v.x0 <= box.x0);
    CHECK(v.x1 >= box.x1);
    CHECK(v.y0 <= box.y0);
    CHECK(v.y1 >= box.y1);
    cam.setLevel(3);
    cam.lookAtTile({376, 69});
    const Vec2 to = kIso.toWorld(300, 619);
    cam.flyTo(to, 3, 2.0f);
    float smallest = cam.scale();
    while (cam.flying()) {
        cam.update(1.0f / 120.0f);
        smallest = std::min(smallest, cam.scale());
    }
    CHECK(smallest < 0.25f); // it passed through every level on the way
    CHECK(cam.scale() == 1.0f);
    CHECK(cam.centre().x == doctest::Approx(to.x));
    CHECK(cam.centre().y == doctest::Approx(to.y));
}

TEST_CASE("themes: keyframes at the phase centres, blended between them") {
    world::Theme t;
    t.grading = {{{0.9f, 0.8f, 0.7f}, {1, 1, 1}, {1, 0.7f, 0.6f}, {0.4f, 0.5f, 0.7f}}};
    const Rgb day = gradingAt(t, phaseCentre(Phase::Day));
    CHECK(day.r == doctest::Approx(1));
    const Rgb night = gradingAt(t, phaseCentre(Phase::Night));
    CHECK(night.r == doctest::Approx(0.4f));
    CHECK(night.b == doctest::Approx(0.7f));
    const Rgb dawn = gradingAt(t, phaseCentre(Phase::Dawn));
    CHECK(dawn.g == doctest::Approx(0.8f));
    const double between = (phaseCentre(Phase::Dusk) + phaseCentre(Phase::Night)) * 0.5;
    const Rgb mid = gradingAt(t, between);
    CHECK(mid.r == doctest::Approx(0.7f));
}

TEST_CASE("themes: weights fade over a second, the dominant region changes past the hysteresis") {
    world::Theme warm;
    warm.grading[1] = {1.0f, 0.5f, 0.5f};
    warm.hazeStrength = 0.2f;
    warm.haze = {1, 0.9f, 0.8f};
    ThemeMixer m({world::Theme{}, warm, world::Theme{}});
    const std::array<world::RegionWeight, 1> home{{{0, 1.0f}}};
    const std::array<world::RegionWeight, 1> city{{{1, 1.0f}}};
    m.reset(home);
    CHECK(m.dominant() == 0);
    m.update(city, 0.1f);
    CHECK(m.weight(1) == doctest::Approx(1 - std::exp(-0.1f)));
    CHECK(m.dominant() == 0); // not yet past the other by the margin
    for (int i = 0; i < 30; ++i) m.update(city, 0.1f);
    CHECK(m.dominant() == 1);
    const Grade g = m.grade(phaseCentre(Phase::Day));
    CHECK(g.mul.g < 0.6f);
    CHECK(g.hazeStrength > 0.05f);
}

TEST_CASE("places: the caption names the place the view is in, once per visit") {
    using K = world::RegionKind;
    // 0 home, 1 a stretch of Athens' time, 2 Athens, 3 a seam, 4 a stretch of Parsa's time,
    // 5 a town of Parsa's time.
    PlaceTracker p({K::Home, K::Stretch, K::City, K::Seam, K::Stretch, K::Town},
                   {"timeless", "athens", "athens", "none", "parsa", "parsa"});
    const auto run = [&](int region, float seconds) {
        bool era = false;
        bool arrived = false;
        for (float t = 0; t < seconds; t += 0.1f) {
            p.update(region, 0.1f);
            era |= p.eraChanged();
            arrived |= p.arrived();
        }
        return std::pair{era, arrived};
    };
    p.reset(0);
    CHECK(p.place() == 0);
    CHECK(p.caption() == 0);
    CHECK(p.captionAlpha() == doctest::Approx(0).epsilon(0.01));
    // A brush with a boundary counts for nothing.
    (void)run(1, 0.2f);
    CHECK(p.region() == 0);
    // Out into the countryside: a new moment, but no named place and no caption.
    auto [era, arrived] = run(1, 1.0f);
    CHECK(era);
    CHECK_FALSE(arrived);
    CHECK(p.place() == -1);
    // Into the city: its caption, not the stretch's.
    std::tie(era, arrived) = run(2, 1.0f);
    CHECK(arrived);
    CHECK_FALSE(era); // the same moment as the stretch around it
    CHECK(p.caption() == 2);
    CHECK(p.captionAlpha() == doctest::Approx(1));
    (void)run(2, 4.0f);
    CHECK(p.captionAlpha() == doctest::Approx(0));
    // Out for a moment and back: the same visit, no caption again.
    (void)run(1, 2.0f);
    std::tie(era, arrived) = run(2, 1.0f);
    CHECK_FALSE(arrived);
    // A seam names no moment; the far side does.
    (void)run(3, 1.0f);
    std::tie(era, arrived) = run(4, 1.0f);
    CHECK(era);
    std::tie(era, arrived) = run(5, 1.0f);
    CHECK(arrived);
    CHECK(p.caption() == 5);
    // Away long enough, coming back is a new visit.
    (void)run(4, 25.0f);
    std::tie(era, arrived) = run(5, 1.0f);
    CHECK(arrived);
    // A jump shows the destination's caption at once.
    p.reset(2);
    CHECK(p.caption() == 2);
    CHECK(p.place() == 2);
}

TEST_CASE("viewer: options and scripts are checked before anything runs") {
    const std::array<std::string_view, 8> args{"--size", "1920x1080", "--goto",  "parsa",
                                               "--zoom", "overview",  "--clock", "night"};
    const auto o = parseViewerOptions(args);
    REQUIRE(o.has_value());
    CHECK(o->w == 1920);
    CHECK(o->zoom == 0.0f);
    CHECK(o->go == "parsa");
    const std::array<std::string_view, 2> bad{"--size", "12"};
    CHECK_FALSE(parseViewerOptions(bad).has_value());
    const std::array<std::string_view, 3> bench{"--bench", "flight", "--no-budget"};
    const auto b = parseViewerOptions(bench);
    REQUIRE(b.has_value());
    CHECK(b->benchCase == "flight");
    CHECK_FALSE(b->budget);
    const auto s = parseScript("# a comment\ngoto 374 58\nzoom 0.5\nexpect luma > 0.2\n"
                               "expect region parsa\nfly athens 1 3\nsettle\nshot a.png\n");
    REQUIRE(s.has_value());
    CHECK(s->size() == 7);
    CHECK(s->front().op == Op::Goto);
    CHECK(s->front().line == 2);
    CHECK_FALSE(parseScript("zoom 9\n").has_value());
    CHECK_FALSE(parseScript("frames 0\n").has_value());
    CHECK_FALSE(parseScript("teleport here\n").has_value());
    CHECK(parseClock("dusk") == phaseCentre(Phase::Dusk));
    CHECK_FALSE(parseClock("1.5").has_value());
    CHECK(compare(2, "<=", 2) == true);
    CHECK_FALSE(compare(2, "~", 2).has_value());
}

TEST_CASE(
    "page runs: sprites that do not meet draw page by page, those that meet keep their order") {
    PageRuns runs;
    runs.begin({0, 0, 640, 480});
    // Two pages alternating across the window, nothing touching: two runs, not six.
    for (int i = 0; i < 6; ++i) {
        const auto x = static_cast<float>(i * 100);
        CHECK(runs.add(static_cast<std::uint32_t>(i % 2), {x, 0, x + 40, 40}));
    }
    CHECK(runs.runs() == 2);
    const std::vector<std::uint32_t> apart(runs.order().begin(), runs.order().end());
    CHECK(apart == std::vector<std::uint32_t>{0, 2, 4, 1, 3, 5});

    // The same pages stacked on one spot: every change of page is a run, in the order given.
    runs.begin({0, 0, 640, 480});
    for (int i = 0; i < 6; ++i)
        CHECK(runs.add(static_cast<std::uint32_t>(i % 2), {300, 200, 340, 240}));
    CHECK(runs.runs() == 6);
    const std::vector<std::uint32_t> stacked(runs.order().begin(), runs.order().end());
    CHECK(stacked == std::vector<std::uint32_t>{0, 1, 2, 3, 4, 5});

    // Off the window: no entry.
    CHECK_FALSE(runs.add(0, {700, 0, 740, 40}));
    CHECK(runs.count() == 6);
}

TEST_CASE("page runs: whatever is drawn over something else is still drawn after it") {
    // Random boxes on four pages: in the order given back, every pair that meets keeps the
    // order it was given in, and each run holds one page.
    PageRuns runs;
    const FRect window{100, 50, 1380, 770};
    runs.begin(window);
    std::vector<FRect> boxes;
    std::vector<std::uint32_t> keys;
    std::uint32_t seed = 12345;
    const auto next = [&](std::uint32_t n) {
        seed = seed * 1664525u + 1013904223u;
        return (seed >> 8) % n;
    };
    for (int i = 0; i < 600; ++i) {
        const auto x = static_cast<float>(next(1500));
        const auto y = static_cast<float>(next(900));
        const FRect box{x, y, x + static_cast<float>(8 + next(200)),
                        y + static_cast<float>(8 + next(160))};
        const std::uint32_t key = next(4);
        if (runs.add(key, box)) {
            boxes.push_back(box);
            keys.push_back(key);
        }
    }
    const auto order = runs.order();
    REQUIRE(order.size() == boxes.size());
    std::vector<std::size_t> place(order.size());
    for (std::size_t k = 0; k < order.size(); ++k) place[order[k]] = k;
    int broken = 0;
    for (std::size_t a = 0; a < boxes.size(); ++a)
        for (std::size_t b = a + 1; b < boxes.size(); ++b)
            if (boxes[a].overlaps(boxes[b]) && place[a] > place[b]) ++broken;
    CHECK(broken == 0);
    int changes = 1;
    for (std::size_t k = 1; k < order.size(); ++k)
        changes += keys[order[k]] != keys[order[k - 1]] ? 1 : 0;
    CHECK(changes == runs.runs());
    // And it is worth having: far fewer runs than the changes of page in the order given.
    int given = 1;
    for (std::size_t k = 1; k < keys.size(); ++k) given += keys[k] != keys[k - 1] ? 1 : 0;
    CHECK(runs.runs() < given);
}

TEST_CASE("terrain: faces hang by the corners of both tiles, wedges under a falling edge") {
    // A flat tile over a flat neighbour two levels down: two bands, capped.
    EdgeFace f = edgeFace(5, 5, 5, 3, 3);
    CHECK(f.first == 0);
    CHECK(f.last == 2);
    CHECK(f.wedge == -1);
    CHECK(f.capped());
    // A one-level slope meeting its lower neighbour: nothing.
    CHECK(edgeFace(5, 4, 4, 4, 4).empty());
    // A slope whose edge falls toward its far end over a cliff to level 2: a wedge high at S,
    // then the bands below its lower corner; no cap under a wedge.
    f = edgeFace(5, 5, 4, 2, 2);
    CHECK(f.wedge == 0);
    CHECK(f.first == 1);
    CHECK(f.last == 3);
    CHECK_FALSE(f.capped());
    CHECK(edgeFace(5, 4, 5, 3, 3).wedge == 1);
    // The neighbour higher or level at both ends: no face; lower at one end: one band.
    CHECK(edgeFace(5, 5, 5, 5, 6).empty());
    f = edgeFace(5, 5, 5, 4, 5);
    CHECK(f.first == 0);
    CHECK(f.last == 1);
}

TEST_CASE("terrain: falling water's parts by the drop, the slope light, the slow field") {
    CHECK(fallPart(1, 0) == FallPart::Rapid);
    CHECK(fallPart(2, 0) == FallPart::Top);
    CHECK(fallPart(2, 1) == FallPart::Foot);
    CHECK(fallPart(4, 1) == FallPart::Mid);
    CHECK(fallPart(4, 2) == FallPart::Mid);
    CHECK(fallPart(4, 3) == FallPart::Foot);
    // Flat is 1; a slope falling toward +x (away from the upper-left sun) is darker, one
    // falling toward -x lighter (the art's formula).
    for (const float l : slopeLight(world::Slope::Flat, 0.5f)) CHECK(l == doctest::Approx(1.0f));
    const auto away = slopeLight(world::Slope(world::kCornerE | world::kCornerS), 0.5f);
    const auto toward = slopeLight(world::Slope(world::kCornerN | world::kCornerW), 0.5f);
    CHECK(away[2] < 1.0f);
    CHECK(toward[6] > 1.0f);
    // The slow field stays in [0, 1], changes little from tile to tile and is not flat.
    float lo = 1;
    float hi = 0;
    float worst = 0;
    for (int y = 0; y < 200; ++y)
        for (int x = 0; x < 200; ++x) {
            const float v = groundMacro({static_cast<float>(x) * 0.5f, static_cast<float>(y)});
            lo = std::min(lo, v);
            hi = std::max(hi, v);
            worst = std::max(worst, std::abs(groundMacro({static_cast<float>(x) * 0.5f + 0.5f,
                                                          static_cast<float>(y)}) -
                                             v));
        }
    CHECK(lo >= 0.0f);
    CHECK(hi <= 1.0f);
    CHECK(hi - lo > 0.5f);
    CHECK(worst < 0.12f);
}
