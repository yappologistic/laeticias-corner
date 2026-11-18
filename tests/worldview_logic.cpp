// The world renderer's pure parts: cell maths and caching policy, page eviction, the camera's
// precision and limits over the 448 x 1280 grid, theme sampling and captions, the viewer's
// options and script language.

#include "worldview/camera.hpp"
#include "worldview/cells.hpp"
#include "worldview/script.hpp"
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

TEST_CASE("themes: weights fade over a second, captions change past the hysteresis") {
    world::Theme warm;
    warm.grading[1] = {1.0f, 0.5f, 0.5f};
    warm.hazeStrength = 0.2f;
    warm.haze = {1, 0.9f, 0.8f};
    ThemeMixer m({world::Theme{}, warm, world::Theme{}}, {"timeless", "athens", "none"});
    const std::array<world::RegionWeight, 1> home{{{0, 1.0f}}};
    const std::array<world::RegionWeight, 1> city{{{1, 1.0f}}};
    m.reset(home);
    CHECK(m.dominant() == 0);
    CHECK(m.captionRegion() == 0);
    CHECK(m.captionAlpha() == doctest::Approx(0).epsilon(0.01));
    m.update(city, 0.1f);
    CHECK(m.weight(1) == doctest::Approx(1 - std::exp(-0.1f)));
    CHECK(m.dominant() == 0); // not yet past the other by the margin
    for (int i = 0; i < 30; ++i) m.update(city, 0.1f);
    CHECK(m.dominant() == 1);
    CHECK(m.captionRegion() == 1);
    const Grade g = m.grade(phaseCentre(Phase::Day));
    CHECK(g.mul.g < 0.6f);
    CHECK(g.hazeStrength > 0.05f);
    // A seam names no time: its caption never shows.
    const std::array<world::RegionWeight, 1> seam{{{2, 1.0f}}};
    m.reset(seam);
    CHECK(m.captionRegion() == 1);
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
