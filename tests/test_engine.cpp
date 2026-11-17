#include "app/options.hpp"
#include "app/script.hpp"
#include "core/tuning.hpp"
#include "render/atlas.hpp"
#include "render/camera.hpp"
#include "render/fx.hpp"
#include "render/sprites.hpp"
#include "test_support.hpp"
#include "ui/font.hpp"
#include "ui/hud.hpp"

#include <doctest.h>

#include <array>
#include <cmath>

using namespace lc;

TEST_CASE("options parse and reject bad input") {
    const std::array<std::string_view, 9> args{
        "--size", "960x600", "--script", "a.lcs", "--seed", "9", "--frames", "30", "--save-dir"};
    CHECK_FALSE(parseOptions(args).has_value()); // --save-dir without a value
    const std::array<std::string_view, 8> ok{"--size", "960x600", "--script", "a.lcs",
                                             "--seed", "9",       "--frames", "30"};
    const auto o = parseOptions(ok);
    REQUIRE(o.has_value());
    CHECK(o->width == 960);
    CHECK(o->height == 600);
    CHECK(o->headless); // scripts always run headless
    CHECK(o->seed == 9u);
    CHECK(o->frames == 30);
    const std::array<std::string_view, 1> bench{"--bench"};
    CHECK(parseOptions(bench)->headless);
    const std::array<std::string_view, 2> badSize{"--size", "10x10"};
    CHECK_FALSE(parseOptions(badSize).has_value());
    const std::array<std::string_view, 1> unknown{"--fly"};
    CHECK_FALSE(parseOptions(unknown).has_value());
}

TEST_CASE("script language parses every command") {
    const auto s = parseScript(R"(# comment
move 10,20
click @3,4
click ui:build right
drag @1,1 @5,1
key ctrl+shift+z
wheel -1 ui:zoom_in
wait 30
shot out/a.png
set clock night
set rain on
expect item @3,4 oak
expect count all 12
quit
)");
    REQUIRE(s.has_value());
    REQUIRE(s->size() == 13);
    CHECK((*s)[0].kind == ScriptCommand::Kind::Move);
    CHECK((*s)[0].a.x == 10);
    CHECK((*s)[1].a.kind == ScriptPoint::Kind::Tile);
    CHECK((*s)[2].a.widget == "build");
    CHECK((*s)[2].right);
    CHECK((*s)[3].b.x == 5);
    CHECK((*s)[4].args[0] == "ctrl+shift+z");
    CHECK((*s)[5].amount == -1);
    CHECK((*s)[5].hasPoint);
    CHECK((*s)[6].amount == 30);
    CHECK((*s)[10].a.kind == ScriptPoint::Kind::Tile);
    CHECK((*s)[12].kind == ScriptCommand::Kind::Quit);

    CHECK_FALSE(parseScript("hop 1,2").has_value());
    CHECK_FALSE(parseScript("move 1").has_value());
    CHECK_FALSE(parseScript("drag 1,1").has_value());
    CHECK_FALSE(parseScript("wait -2").has_value());
    CHECK_FALSE(parseScript("set fog on").has_value());
    const auto err = parseScript("move 1,1\nclick 1,1 left");
    REQUIRE_FALSE(err.has_value());
    CHECK(err.error().find("line 2") != std::string::npos);
}

TEST_CASE("camera maps screen and world consistently and zooms about the cursor") {
    Camera cam(20, 20);
    const Vec2 screen{1280, 800};
    cam.recentre(screen);
    CHECK(cam.zoom() == defaultZoom(screen, 20, 20));
    const Vec2 px{300, 200};
    const Vec2 w = cam.screenToWorld(px, screen);
    const Vec2 back = cam.worldToScreen(w, screen);
    CHECK(back.x == doctest::Approx(px.x));
    CHECK(back.y == doctest::Approx(px.y));

    const int z = cam.zoom();
    cam.zoomAt(z + 1, px, screen);
    CHECK(cam.zoom() == z + 1);
    const Vec2 w2 = cam.screenToWorld(px, screen);
    CHECK(w2.x == doctest::Approx(w.x).epsilon(0.001));
    CHECK(w2.y == doctest::Approx(w.y).epsilon(0.001));
    cam.zoomAt(99, px, screen);
    CHECK(cam.zoom() == tuning::kMaxZoom);
    cam.zoomAt(-5, px, screen);
    CHECK(cam.zoom() == tuning::kMinZoom);

    // Panning is limited so the island cannot be lost.
    for (int i = 0; i < 100; ++i) cam.dragBy({5000, 5000});
    const WorldBounds b = islandBounds(20, 20);
    CHECK(cam.position().x >= b.x0 - tuning::kCameraMargin - 0.01f);
    CHECK(cam.position().y >= b.y0 - tuning::kCameraMargin - 0.01f);

    CHECK(defaultZoom({960, 600}, 20, 20) >= 1);
    CHECK(defaultZoom({3840, 2160}, 20, 20) > defaultZoom({1280, 800}, 20, 20));
}

TEST_CASE("atlas manifest parsing") {
    const auto m = parseAtlasManifest(
        R"({"version":1,"image":"atlas.png","sprites":{"a":{"x":1,"y":2,"w":3,"h":4,"ox":-1,"oy":5}}})");
    REQUIRE(m.has_value());
    CHECK(m->sprites.at("a").ox == -1);
    CHECK_FALSE(parseAtlasManifest(R"({"version":2,"sprites":{}})").has_value());
    CHECK_FALSE(parseAtlasManifest(
                    R"({"version":1,"sprites":{"a":{"x":0,"y":0,"w":0,"h":4,"ox":0,"oy":0}}})")
                    .has_value());
    CHECK_FALSE(parseAtlasManifest("[").has_value());
}

TEST_CASE("required sprite keys follow the contract") {
    const auto keys = requiredSpriteKeys(test::catalog());
    const auto has = [&](std::string_view k) { return std::ranges::find(keys, k) != keys.end(); };
    CHECK(has("terrain/grass/v3"));
    CHECK(has("terrain/water/m15/f0"));
    CHECK(has("item/hedge/base/m9/f0"));
    CHECK(has("item/barn/base/r3/f0"));
    CHECK(has("item/lamp/glow/r0/f0"));
    CHECK_FALSE(has("item/oak/glow/r0/f0"));
    CHECK(has("critter/duck/move_back/f0"));
    CHECK(has("fx/raindrop/f0"));
    CHECK(has("edge/cliff_sw"));
}

TEST_CASE("utf-8 decoding") {
    const std::string_view s = "a·…\xff";
    std::size_t i = 0;
    CHECK(nextCodepoint(s, i) == U'a');
    CHECK(nextCodepoint(s, i) == 0xB7);
    CHECK(nextCodepoint(s, i) == 0x2026);
    CHECK(nextCodepoint(s, i) == 0xFFFD);
    CHECK(i == s.size());
}

TEST_CASE("drawer categories list terrain for the ground tab") {
    const Catalog& c = test::catalog();
    const auto ground = Hud::categoryEntries(c, *c.findCategory(kGroundCategory));
    CHECK(ground.size() == c.terrain.size());
    const auto homes = Hud::categoryEntries(c, *c.findCategory("homes"));
    CHECK(homes.size() == 6);
    for (int i : homes)
        CHECK(c.items[static_cast<std::size_t>(i)].category == *c.findCategory("homes"));
}

TEST_CASE("particles expire and rain leaves ripples on water") {
    const Catalog& c = test::catalog();
    World w(c);
    w.setTerrain({0, 0}, c.waterTerrain);
    Particles p;
    p.spawn(Fx::Raindrop, tileToWorld(0.5f, 0.5f), {0, 0}, 0.1f);
    p.spawn(Fx::Raindrop, tileToWorld(5.5f, 5.5f), {0, 0}, 0.1f);
    p.spawn(Fx::Smoke, {0, 0}, {0, -10}, 1.0f);
    p.update(0.2f, w);
    REQUIRE(p.all().size() == 2);
    int ripples = 0;
    for (const auto& pt : p.all()) ripples += pt.kind == Fx::Ripple ? 1 : 0;
    CHECK(ripples == 1);
    for (std::size_t i = 0; i < Particles::kCapacity + 10; ++i)
        p.spawn(Fx::Sparkle, {0, 0}, {0, 0}, 1.0f);
    CHECK(p.all().size() == Particles::kCapacity);
    p.update(5.0f, w);
    CHECK(p.all().empty());
}
