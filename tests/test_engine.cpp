#include "app/options.hpp"
#include "app/script.hpp"
#include "app/window_state.hpp"
#include "audio/decode.hpp"
#include "audio/mixer.hpp"
#include "audio/stems.hpp"
#include "audio/wav.hpp"
#include "audio_meter.hpp"
#include "core/rng.hpp"
#include "core/tuning.hpp"
#include "platform/process.hpp"
#include "render/atlas.hpp"
#include "render/blur.hpp"
#include "render/camera.hpp"
#include "render/depth.hpp"
#include "render/fx.hpp"
#include "render/sprites.hpp"
#include "test_support.hpp"
#include "ui/font.hpp"
#include "ui/hud.hpp"
#include "ui/map_screen.hpp"
#include "ui/menus.hpp"
#include "ui/painter.hpp"

#include <SDL3/SDL.h>

#include <doctest.h>

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdlib>
#include <format>
#include <fstream>
#include <map>
#include <set>
#include <tuple>

using namespace lc;

TEST_CASE("options parse and reject bad input") {
    const std::array<std::string_view, 9> args{
        "--size", "960x600", "--script", "a.lcs", "--seed", "9", "--frames", "30", "--save-dir"};
    CHECK_FALSE(parseOptions(args).has_value()); // --save-dir without a value
    const std::array<std::string_view, 8> ok{"--size", "960x600", "--script", "a.lcs",
                                             "--seed", "9",       "--frames", "30"};
    const auto o = parseOptions(ok);
    REQUIRE(o.has_value());
    REQUIRE(o->size.has_value());
    CHECK(o->size->w == 960);
    CHECK(o->size->h == 600);
    CHECK(o->headless); // scripts always run headless
    CHECK(o->seed == 9u);
    CHECK(o->frames == 30);
    const std::array<std::string_view, 1> bench{"--bench"};
    CHECK(parseOptions(bench)->headless);
    const std::array<std::string_view, 2> badSize{"--size", "10x10"};
    CHECK_FALSE(parseOptions(badSize).has_value());
    const std::array<std::string_view, 1> unknown{"--fly"};
    CHECK_FALSE(parseOptions(unknown).has_value());
    const std::array<std::string_view, 1> none{"--headless"};
    CHECK_FALSE(parseOptions(none)->size.has_value()); // sized to the display unless given
    const std::array<std::string_view, 7> bench2{"--bench", "--map",       "1024x512", "--density",
                                                 "0.4",     "--budget-ms", "2"};
    const auto b = parseOptions(bench2);
    REQUIRE(b.has_value());
    CHECK(b->map->w == 1024);
    CHECK(b->density == doctest::Approx(0.4f));
    CHECK(b->budgetMs == doctest::Approx(2.0));
    const std::array<std::string_view, 4> one{"--bench", "--bench-case", "rome crowd",
                                              "--streamed"};
    const auto c = parseOptions(one);
    REQUIRE(c.has_value());
    CHECK(c->benchCase == "rome crowd");
    CHECK(c->streamed);
    CHECK_FALSE(b->streamed);
    const std::array<std::string_view, 1> noCase{"--bench-case"};
    CHECK_FALSE(parseOptions(noCase).has_value());
    const std::array<std::string_view, 2> tooBig{"--map", "4096x4096"};
    CHECK_FALSE(parseOptions(tooBig).has_value());
    const std::array<std::string_view, 2> audio{"--audio-out", "a.wav"};
    CHECK(parseOptions(audio)->headless);
    const std::array<std::string_view, 2> dir{"--script", "."};
    CHECK_FALSE(parseOptions(dir).has_value()); // a directory is not a script
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
press @2,2
release 10,10 right
keydown ctrl
keyup d
expect luma 0,0,10,10 20 80
expect color 5,5,4,4 10 20 30 8
expect present duck 2
)");
    REQUIRE(s.has_value());
    REQUIRE(s->size() == 20);
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
    CHECK((*s)[13].kind == ScriptCommand::Kind::Press);
    CHECK((*s)[14].kind == ScriptCommand::Kind::Release);
    CHECK((*s)[14].right);
    CHECK((*s)[15].kind == ScriptCommand::Kind::KeyDown);
    CHECK((*s)[16].kind == ScriptCommand::Kind::KeyUp);
    CHECK(parseScriptRect("1,2,3,4")->h == 4);
    CHECK_FALSE(parseScriptRect("1,2,3").has_value());
    CHECK_FALSE(parseScriptRect("1,2,0,4").has_value());
    CHECK_FALSE(parseScript("expect luma 1,2,3 0 9").has_value());
    CHECK_FALSE(parseScript("wait 99999999999").has_value()); // would overflow the frame count

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
    const Iso iso = test::catalog().iso();
    const TileRect land{0, 0, 40, 40};
    Camera cam(iso, land, 66);
    const Vec2 screen{1920, 1080};
    cam.frame({16, 120, 1904, 940}, screen, land);
    const Vec2 px{300, 200};
    const Vec2 w = cam.screenToWorld(px, screen);
    const Vec2 back = cam.worldToScreen(w, screen);
    CHECK(back.x == doctest::Approx(px.x));
    CHECK(back.y == doctest::Approx(px.y));

    const int level = cam.level();
    cam.zoomTo(level + 1, px, screen);
    CHECK(cam.level() == level + 1);
    CHECK_FALSE(cam.settled());
    // The transition eases: halfway through it is between the two scales.
    cam.update(1.0f / 60.0f, screen);
    CHECK(cam.scale() > kZoomLevels[static_cast<std::size_t>(level)]);
    CHECK(cam.scale() < kZoomLevels[static_cast<std::size_t>(level + 1)]);
    for (int i = 0; i < 120; ++i) cam.update(1.0f / 60.0f, screen);
    CHECK(cam.settled());
    const Vec2 w2 = cam.screenToWorld(px, screen);
    CHECK(w2.x == doctest::Approx(w.x).epsilon(0.001));
    CHECK(w2.y == doctest::Approx(w.y).epsilon(0.001));
    cam.zoomTo(99, px, screen);
    CHECK(cam.level() == static_cast<int>(kZoomLevels.size()) - 1);
    cam.zoomTo(-5, px, screen);
    CHECK(cam.level() == 0);
}

TEST_CASE("camera limits keep land on screen at every zoom and window size") {
    const Iso iso = test::catalog().iso();
    for (const TileRect land : {TileRect{0, 0, 40, 40}, TileRect{0, 0, 1024, 512}}) {
        for (const Vec2 screen : {Vec2{960, 600}, Vec2{1920, 1080}, Vec2{3840, 2160}}) {
            for (int level = 0; level < static_cast<int>(kZoomLevels.size()); ++level) {
                for (const Vec2 d : {Vec2{1, 0}, Vec2{-1, 0}, Vec2{0, 1}, Vec2{0, -1}, Vec2{1, 1},
                                     Vec2{-1, 1}, Vec2{1, -1}, Vec2{-1, -1}}) {
                    CAPTURE(land.x1);
                    CAPTURE(screen.x);
                    CAPTURE(level);
                    Camera cam(iso, land, 66);
                    cam.zoomTo(level, {screen.x / 2, screen.y / 2}, screen);
                    for (int i = 0; i < 200; ++i) cam.update(1.0f / 60.0f, screen);
                    for (int i = 0; i < 400; ++i) cam.dragBy({d.x * 5000, d.y * 5000}, screen);
                    cam.update(1.0f / 60.0f, screen);
                    // The land point nearest the view centre must be well inside the window.
                    Vec2 t = iso.toTile(cam.screenToWorld({screen.x / 2, screen.y / 2}, screen));
                    t.x = std::clamp(t.x, static_cast<float>(land.x0), static_cast<float>(land.x1));
                    t.y = std::clamp(t.y, static_cast<float>(land.y0), static_cast<float>(land.y1));
                    const Vec2 p = cam.worldToScreen(iso.toWorld(t.x, t.y), screen);
                    const bool visible = p.x > screen.x * 0.05f && p.x < screen.x * 0.95f &&
                                         p.y > screen.y * 0.05f && p.y < screen.y * 0.95f;
                    CHECK(visible);
                }
            }
        }
    }
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
    std::vector<DrawerEntry> ground;
    Hud::categoryEntries(c, *c.findCategory(kGroundCategory), ground);
    REQUIRE(ground.size() == c.terrain.size());
    for (std::size_t t = 0; t < ground.size(); ++t)
        CHECK(ground[t] == DrawerEntry{.terrain = true, .index = static_cast<int>(t)});
    std::vector<DrawerEntry> homes;
    Hud::categoryEntries(c, *c.findCategory("homes"), homes);
    CHECK(homes.size() == 6);
    for (const DrawerEntry& e : homes) {
        CHECK_FALSE(e.terrain);
        CHECK(c.items[static_cast<std::size_t>(e.index)].category == *c.findCategory("homes"));
    }
}

TEST_CASE("the drawer lists unlocked pieces, then a lock tile while some are still to discover") {
    const Catalog& c = test::catalog();
    Progress p(c);
    const int homes = *c.findCategory("homes");
    const int ground = *c.findCategory(kGroundCategory);
    std::vector<DrawerEntry> e;
    Hud::categoryEntries(c, homes, e, &p);
    // A new world has only the cottage among the homes.
    REQUIRE(e.size() == 2);
    CHECK(e[0] == DrawerEntry{.terrain = false, .index = *c.findItem("cottage")});
    CHECK(e[1].locked);
    CHECK(Hud::lockedIn(c, homes, &p) == 5);
    Hud::categoryEntries(c, ground, e, &p);
    CHECK(e.size() == 5); // grass, meadow, path, water, then the lock (cobble comes later)
    CHECK(e.back().locked);
    // Unlocking marks new pieces; a complete tab has no lock tile.
    Reward r;
    r.terrain = {*c.findTerrain("cobble")};
    p.unlock(r, true);
    CHECK(entryNew(&p, {.terrain = true, .index = *c.findTerrain("cobble")}));
    CHECK_FALSE(entryNew(&p, {.terrain = true, .index = *c.findTerrain("grass")}));
    Hud::categoryEntries(c, ground, e, &p);
    CHECK(e.size() == 5);
    CHECK_FALSE(e.back().locked);
    CHECK(Hud::lockedIn(c, ground, &p) == 0);
    p.unlockEverything(c);
    for (std::size_t k = 0; k < c.categories.size(); ++k)
        CHECK(Hud::lockedIn(c, static_cast<int>(k), &p) == 0);
}

TEST_CASE("thumbnails fall back to the placeholder instead of crashing") {
    SpriteTables t;
    t.placeholder = 7;
    t.terrainBase = {{3}, {}};
    t.terrainOverlay.resize(2);
    t.terrainOverlay[1][15].frames = {4};
    t.items.resize(3);
    t.items[0].base = {FrameSet{{5}}};
    t.items[1].base = {FrameSet{}}; // missing art
    t.kinds.resize(1);
    t.kinds[0].resize(2);
    t.kinds[0][1].front.frames = {6};

    CHECK(thumbnail(t, Thumb::Terrain, 0) == 3);
    CHECK(thumbnail(t, Thumb::Terrain, 1) == 4);
    CHECK(thumbnail(t, Thumb::Item, 0) == 5);
    CHECK(thumbnail(t, Thumb::Visitor, 0) == 6);
    CHECK(thumbnail(t, Thumb::Item, 1) == 7);     // empty frame set
    CHECK(thumbnail(t, Thumb::Item, 2) == 7);     // no variants at all
    CHECK(thumbnail(t, Thumb::Terrain, 25) == 7); // an item index used as terrain: out of range
    CHECK(thumbnail(t, Thumb::Item, -1) == 7);
    CHECK(thumbnail(t, Thumb::Visitor, 1) == 7);
    t.terrainOverlay[1][15].frames.clear();
    CHECK(thumbnail(t, Thumb::Terrain, 1) == 7);
}

TEST_CASE("particles expire and rain leaves ripples on water") {
    const Catalog& c = test::catalog();
    World w(c);
    w.setTerrain({0, 0}, c.waterTerrain);
    const Iso iso = c.iso();
    Particles p(iso);
    p.spawn(Fx::Raindrop, iso.toWorld(0.5f, 0.5f), {0, 0}, 0.1f);
    p.spawn(Fx::Raindrop, iso.toWorld(5.5f, 5.5f), {0, 0}, 0.1f);
    p.spawn(Fx::Smoke, {0, 0}, {0, -10}, 1.0f);
    p.update(0.2f, w);
    REQUIRE(p.all().size() == 3); // smoke, a ripple on the water and a splash on the grass
    int ripples = 0;
    int splashes = 0;
    for (const auto& pt : p.all()) {
        ripples += pt.kind == Fx::Ripple ? 1 : 0;
        splashes += pt.kind == Fx::Raindrop && pt.landed ? 1 : 0;
    }
    CHECK(ripples == 1);
    CHECK(splashes == 1);
    // Off the map a drop simply disappears.
    p.spawn(Fx::Raindrop, iso.toWorld(-3.0f, -3.0f), {0, 0}, 0.1f);
    p.update(0.2f, w);
    CHECK(p.all().size() == 3);
    for (std::size_t i = 0; i < Particles::kCapacity + 10; ++i)
        p.spawn(Fx::Sparkle, {0, 0}, {0, 0}, 1.0f);
    CHECK(p.all().size() == Particles::kCapacity);
    p.update(5.0f, w);
    CHECK(p.all().empty());
}

TEST_CASE("mixer: effects pass untouched, pile-ups are limited, mute and loops ramp smoothly") {
    // Forced to the dummy driver even when run by hand: tests never reach the speakers.
    REQUIRE(SDL_SetHintWithPriority(SDL_HINT_AUDIO_DRIVER, "dummy", SDL_HINT_OVERRIDE));
    REQUIRE(SDL_Init(SDL_INIT_AUDIO));
    {
        Mixer mixer;
        mixer.load(test::assetsDir() / "audio", test::catalog().audio);
        mixer.startCapture();
        CHECK(mixer.sfxIndex("sfx/not_a_sound.wav") == -1);
        const int click = mixer.sfxIndex("sfx/ui_click.wav");
        REQUIRE(click >= 0);
        const auto clickSamples = loadWavMono(test::assetsDir() / "audio/sfx/ui_click.wav");
        REQUIRE(clickSamples.has_value());
        constexpr int kFrames = 4096;
        std::vector<float> out(kFrames * 2);
        // The master gain fades in from silence over a few milliseconds.
        mixer.render(out.data(), kFrames);
        for (const float v : out) CHECK(v == 0.0f);
        // A single effect below the limiter's ceiling comes out exactly scaled.
        mixer.play(click, 0.5f, 1.0f);
        mixer.render(out.data(), kFrames);
        // (The voice ends one sample early: its last sample is the interpolation end point.)
        const std::size_t n = std::min<std::size_t>(clickSamples->size() - 1, kFrames);
        double err = 0;
        for (std::size_t i = 0; i < n; ++i) {
            err = std::max(err,
                           static_cast<double>(std::abs(out[i * 2] - (*clickSamples)[i] * 0.5f)));
            CHECK(out[i * 2] == out[i * 2 + 1]);
        }
        CHECK(err < 1e-5);
        // Twenty-four loud voices at once never exceed the ceiling.
        for (int i = 0; i < 100; ++i) mixer.play(click, 4.0f, 1.0f); // also overflows the ring
        float peak = 0;
        for (int k = 0; k < 4; ++k) {
            mixer.render(out.data(), kFrames);
            for (const float v : out) peak = std::max(peak, std::abs(v));
        }
        CHECK(peak <= tuning::kLimiterCeiling + 1e-4f);
        CHECK(peak > 0.5f);
        // Music fades in without a jump, and mute fades the master out to silence.
        const int pad = mixer.loopIndex("music/day_pad.ogg");
        REQUIRE(pad >= 0);
        mixer.unlockStem(pad, true);
        mixer.setLoopGain(pad, tuning::kMusicLevel);
        float prev = 0;
        float jump = 0;
        for (int k = 0; k < 40; ++k) {
            mixer.render(out.data(), kFrames);
            for (std::size_t i = 0; i < out.size(); i += 2) {
                jump = std::max(jump, std::abs(out[i] - prev));
                prev = out[i];
            }
        }
        CHECK(jump < 0.2f);
        mixer.setMuted(true);
        for (int k = 0; k < 3; ++k) mixer.render(out.data(), kFrames);
        for (const float v : out) CHECK(v == 0.0f);
    }
    SDL_QuitSubSystem(SDL_INIT_AUDIO);
}

TEST_CASE("mixer buses: the player's volumes glide, never click, and stems reset for a world") {
    REQUIRE(SDL_SetHintWithPriority(SDL_HINT_AUDIO_DRIVER, "dummy", SDL_HINT_OVERRIDE));
    REQUIRE(SDL_Init(SDL_INIT_AUDIO));
    {
        Mixer mixer;
        mixer.load(test::assetsDir() / "audio", test::catalog().audio);
        mixer.startCapture();
        constexpr int kFrames = 4096;
        std::vector<float> out(kFrames * 2);
        const int pad = mixer.loopIndex("music/day_pad.ogg");
        REQUIRE(pad >= 0);
        mixer.unlockStem(pad, true);
        mixer.setLoopGain(pad, tuning::kMusicLevel);
        const auto energy = [&] {
            double e = 0;
            for (int k = 0; k < 8; ++k) {
                mixer.render(out.data(), kFrames);
                for (const float v : out) e += static_cast<double>(v) * v;
            }
            return e;
        };
        for (int k = 0; k < 8; ++k) (void)energy(); // the loop's own gain glides in first
        const double full = energy();
        REQUIRE(full > 0);
        // The music bus down to zero: a glide (no sample-to-sample jump), then silence.
        mixer.setBus(Mixer::Bus::Music, 0.0f);
        float prev = out[out.size() - 2];
        float jump = 0;
        for (int k = 0; k < 60; ++k) {
            mixer.render(out.data(), kFrames);
            for (std::size_t i = 0; i < out.size(); i += 2) {
                jump = std::max(jump, std::abs(out[i] - prev));
                prev = out[i];
            }
        }
        CHECK(jump < 0.2f);
        CHECK(energy() == 0.0);
        // Halfway, about a quarter of the energy (the amplitude halves).
        mixer.setBus(Mixer::Bus::Music, 0.5f);
        for (int k = 0; k < 8; ++k) (void)energy();
        const double half = energy();
        CHECK(half > full * 0.1);
        CHECK(half < full * 0.5);
        // The ambience bus leaves the music alone; another world's stems start silent.
        mixer.setBus(Mixer::Bus::Ambience, 0.0f);
        CHECK(energy() > 0);
        mixer.resetStems();
        for (int k = 0; k < 2; ++k) mixer.render(out.data(), kFrames);
        CHECK(mixer.stemLevel(pad) == 0.0f);
        CHECK(energy() == 0.0);
    }
    SDL_QuitSubSystem(SDL_INIT_AUDIO);
}

TEST_CASE("mixer: snow's muffle low-passes the beds, glides in without a click, spares the dry") {
    REQUIRE(SDL_SetHintWithPriority(SDL_HINT_AUDIO_DRIVER, "dummy", SDL_HINT_OVERRIDE));
    REQUIRE(SDL_Init(SDL_INIT_AUDIO));
    {
        // Three mixers play the same rain bed in step: open, muffled, and muffled but dry.
        const AudioList& list = test::catalog().audio;
        const auto rain = std::ranges::find_if(
            list.ambience, [](const std::string& f) { return f.contains("rain"); });
        REQUIRE(rain != list.ambience.end());
        std::array<Mixer, 3> mixers;
        for (Mixer& m : mixers) {
            m.load(test::assetsDir() / "audio", list);
            m.startCapture();
            m.setLoopGain(m.loopIndex(*rain), 0.5f);
        }
        mixers[1].setMuffle(1.0f);
        mixers[2].setMuffle(1.0f);
        mixers[2].setLoopDry(mixers[2].loopIndex(*rain), true);
        constexpr int kFrames = 4096;
        std::vector<float> out(kFrames * 2);
        struct Sum {
            double e = 0; // energy
            double d = 0; // energy of the sample-to-sample differences: brightness
            float prev = 0;
            float jump = 0;
        };
        std::array<Sum, 3> sums;
        for (int k = 0; k < 120; ++k)
            for (std::size_t m = 0; m < 3; ++m) {
                mixers[m].render(out.data(), kFrames);
                Sum& s = sums[m];
                for (std::size_t i = 0; i < out.size(); i += 2) {
                    const float diff = out[i] - s.prev;
                    s.prev = out[i];
                    s.jump = std::max(s.jump, std::abs(diff));
                    if (k < 80) continue; // the gains and the muffle glide in first
                    s.e += static_cast<double>(out[i]) * out[i];
                    s.d += static_cast<double>(diff) * diff;
                }
            }
        const auto bright = [](const Sum& s) { return s.e > 0 ? s.d / s.e : 0.0; };
        REQUIRE(sums[0].e > 0);
        MESSAGE("open " << sums[0].e << " / " << bright(sums[0]) << ", muffled " << sums[1].e
                        << " / " << bright(sums[1]));
        CHECK(bright(sums[1]) < bright(sums[0]) * 0.7);    // the highs are gone
        CHECK(sums[1].e > sums[0].e * 0.2);                // the bed is still there
        CHECK(sums[1].jump < sums[0].jump * 1.5f + 0.01f); // gliding in made no click
        CHECK(sums[2].e == doctest::Approx(sums[0].e));    // the dry bed untouched
    }
    SDL_QuitSubSystem(SDL_INIT_AUDIO);
}

TEST_CASE("music stems: bar lines, fades and a stem joining in step with the others") {
    constexpr std::uint64_t kBar = tuning::kMusicBarSamples;
    CHECK(nextBar(0, kBar) == 0);
    CHECK(nextBar(1, kBar) == kBar);
    CHECK(nextBar(kBar, kBar) == kBar);
    CHECK(nextBar(kBar * 5 + 3, kBar) == kBar * 6);
    CHECK(fadeLevel(10, 20, 100) == 0.0f);
    CHECK(fadeLevel(70, 20, 100) == doctest::Approx(0.5f));
    CHECK(fadeLevel(500, 20, 100) == 1.0f);
    CHECK(loopOffset(4704000 + 17, 4704000) == 17);

    REQUIRE(SDL_SetHintWithPriority(SDL_HINT_AUDIO_DRIVER, "dummy", SDL_HINT_OVERRIDE));
    REQUIRE(SDL_Init(SDL_INIT_AUDIO));
    {
        // Three mixers on one clock: pad alone; pad then keys joining a bar into the music; keys
        // alone from the start. Once the keys have faded in, the second is exactly the sum of
        // the other two, so the late stem landed on the master position, sample for sample.
        const auto setup = [](Mixer& m, bool pad, bool keys) {
            m.load(test::assetsDir() / "audio", test::catalog().audio);
            m.startCapture();
            const int p = m.loopIndex("music/day_pad.ogg");
            const int k = m.loopIndex("music/day_keys.ogg");
            REQUIRE(p >= 0);
            REQUIRE(k >= 0);
            m.setLoopGain(p, 0.3f);
            m.setLoopGain(k, 0.3f);
            if (pad) m.unlockStem(p, true);
            if (keys) m.unlockStem(k, true);
            return k;
        };
        Mixer a, b, c;
        (void)setup(a, true, false);
        const int keysB = setup(b, true, false);
        (void)setup(c, false, true);
        constexpr int kChunk = 4410;
        std::vector<float> oa(kChunk * 2), ob(kChunk * 2), oc(kChunk * 2);
        const auto step = [&] {
            a.render(oa.data(), kChunk);
            b.render(ob.data(), kChunk);
            c.render(oc.data(), kChunk);
        };
        for (int i = 0; i < 40; ++i) step(); // 4 s: gains settled, more than a bar in
        CHECK(b.musicPosition() == 40 * static_cast<std::uint64_t>(kChunk));
        b.unlockStem(keysB, false);
        // Before the next bar line the keys are silent in b.
        step();
        double early = 0;
        for (std::size_t i = 0; i < ob.size(); ++i)
            early = std::max(early, static_cast<double>(std::abs(ob[i] - oa[i])));
        CHECK(early < 1e-6);
        // After the bar line and four bars of fade, b = a + c.
        const auto fadeEnd = (nextBar(41 * static_cast<std::uint64_t>(kChunk), kBar) +
                              kBar * tuning::kStemFadeBars) /
                                 kChunk +
                             2;
        while (b.musicPosition() / kChunk < fadeEnd) step();
        double err = 0;
        double signal = 0;
        for (int k = 0; k < 10; ++k) {
            step();
            for (std::size_t i = 0; i < ob.size(); ++i) {
                err = std::max(err, static_cast<double>(std::abs(ob[i] - oa[i] - oc[i])));
                signal = std::max(signal, static_cast<double>(std::abs(oc[i])));
            }
        }
        CHECK(signal > 0.01);
        CHECK(err < 1e-4);
    }
    SDL_QuitSubSystem(SDL_INIT_AUDIO);
}

TEST_CASE("float WAV round trip") {
    const auto file = test::tempDir("wav") / "a.wav";
    const std::vector<float> s{0.0f, 0.25f, -0.5f, 1.0f, 0.125f, -1.0f};
    REQUIRE(writeWavFloat(file, s).has_value());
    const auto back = readWavFloat(file);
    REQUIRE(back.has_value());
    CHECK(*back == s);
    CHECK_FALSE(readWavFloat(test::tempDir("wav2") / "missing.wav").has_value());
}

TEST_CASE("window placement: a share of the display, or the remembered spot if still visible") {
    const WindowRect d{0, 0, 1920, 1040};
    const WindowRect w = defaultWindow(d);
    CHECK(w.w == static_cast<int>(1920 * kWindowFill));
    CHECK(w.x == (1920 - w.w) / 2);
    const WindowRect displays[] = {d, {1920, 0, 2560, 1400}};
    CHECK(restoreWindow({2000, 100, 1600, 900}, displays) == WindowRect{2000, 100, 1600, 900});
    // The second display is gone: the window no longer shows, so the default is used.
    CHECK_FALSE(restoreWindow({2000, 100, 1600, 900}, std::span(displays, 1)).has_value());
    // Larger than the display it is on: shrunk to fit.
    const auto shrunk = restoreWindow({10, 10, 1900, 1200}, std::span(displays, 1));
    REQUIRE(shrunk.has_value());
    CHECK(shrunk->h == 1040);
    const auto s = parseWindowState(serializeWindowState({{5, 6, 700, 500}, true}));
    REQUIRE(s.has_value());
    CHECK(s->windowed == WindowRect{5, 6, 700, 500});
    CHECK(s->fullscreen);
    CHECK_FALSE(parseWindowState("{").has_value());
}

TEST_CASE("depth order respects every overlapping pair and handles large footprints") {
    const Iso iso = test::catalog().iso();
    Rng rng(21);
    // Random non-overlapping footprints up to 8x8, with screen boxes like real sprites.
    std::vector<FRect> foot;
    std::vector<FRect> screen;
    std::vector<std::uint8_t> used(120 * 120, 0);
    for (int attempt = 0; attempt < 3000; ++attempt) {
        const int w = rng.chance(0.2f) ? rng.range(2, 8) : 1;
        const int h = rng.chance(0.2f) ? rng.range(2, 8) : 1;
        const int x = rng.range(0, 120 - w);
        const int y = rng.range(0, 120 - h);
        bool free = true;
        for (int yy = y; yy < y + h; ++yy)
            for (int xx = x; xx < x + w; ++xx)
                free &= used[static_cast<std::size_t>(yy * 120 + xx)] == 0;
        if (!free) continue;
        for (int yy = y; yy < y + h; ++yy)
            for (int xx = x; xx < x + w; ++xx) used[static_cast<std::size_t>(yy * 120 + xx)] = 1;
        const auto f = [](int v) { return static_cast<float>(v); };
        foot.push_back({f(x), f(y), f(x + w), f(y + h)});
        const float left = iso.toWorld(f(x), f(y + h)).x;
        const float right = iso.toWorld(f(x + w), f(y)).x;
        const float bottom = iso.toWorld(f(x + w), f(y + h)).y;
        const float tall = iso.tileH() * rng.range(1.0f, 4.0f) * f(std::max(w, h));
        screen.push_back({left - 8, iso.toWorld(f(x), f(y)).y - tall, right + 8, bottom});
    }
    DepthSorter sorter;
    std::vector<std::uint32_t> order;
    sorter.sort(foot, screen, 2 * iso.tileW(), order);
    REQUIRE(order.size() == foot.size());
    std::vector<std::size_t> rank(foot.size());
    for (std::size_t k = 0; k < order.size(); ++k) rank[order[k]] = k;
    int pairs = 0;
    for (std::size_t i = 0; i < foot.size(); ++i)
        for (std::size_t j = i + 1; j < foot.size(); ++j) {
            if (!screen[i].overlaps(screen[j])) continue;
            ++pairs;
            const bool ij = behind(foot[i], foot[j]);
            CHECK((ij ? rank[i] < rank[j] : rank[j] < rank[i]));
        }
    CHECK(pairs > 1000);
}

TEST_CASE("screen grid finds every overlapping pair exactly once") {
    Rng rng(3);
    std::vector<FRect> boxes;
    for (int i = 0; i < 600; ++i) {
        const float x = rng.range(-500.0f, 5000.0f);
        const float y = rng.range(-500.0f, 3000.0f);
        boxes.push_back({x, y, x + rng.range(1.0f, 300.0f), y + rng.range(1.0f, 300.0f)});
    }
    ScreenGrid grid;
    grid.build(boxes, 128);
    std::set<std::pair<std::uint32_t, std::uint32_t>> found;
    int calls = 0;
    grid.pairs(boxes, [&](std::uint32_t i, std::uint32_t j) {
        ++calls;
        found.emplace(i, j);
    });
    int brute = 0;
    for (std::uint32_t i = 0; i < boxes.size(); ++i)
        for (std::uint32_t j = i + 1; j < boxes.size(); ++j)
            if (boxes[i].overlaps(boxes[j])) {
                ++brute;
                CHECK(found.contains({i, j}));
            }
    CHECK(calls == brute);
}

TEST_CASE("backdrop blur spreads an edge evenly without leaking across the frame") {
    REQUIRE(SDL_SetHintWithPriority(SDL_HINT_VIDEO_DRIVER, "dummy", SDL_HINT_OVERRIDE));
    REQUIRE(SDL_InitSubSystem(SDL_INIT_VIDEO));
    {
        const WindowPtr window{SDL_CreateWindow("blur", 64, 64, SDL_WINDOW_HIDDEN)};
        REQUIRE(window);
        const RendererPtr renderer{SDL_CreateRenderer(window.get(), "software")};
        REQUIRE(renderer);
        Blur blur(renderer.get());
        CHECK(blur.result() == nullptr);
        // Two window sizes and blur strengths, as at small and large UI scales.
        for (const auto& [w, h, radius] : {std::tuple{960, 600, 18.0f}, {1920, 1080, 45.0f}}) {
            CAPTURE(w);
            const Vec2 screen{static_cast<float>(w), static_cast<float>(h)};
            REQUIRE(blur.begin(screen, radius));
            // A dark left half and a light right half.
            const Vec2 k = blur.sourceScale();
            REQUIRE(SDL_SetRenderDrawColorFloat(renderer.get(), 0, 0, 0, 1));
            REQUIRE(SDL_RenderClear(renderer.get()));
            REQUIRE(SDL_SetRenderDrawColorFloat(renderer.get(), 1, 1, 1, 1));
            const SDL_FRect light{screen.x * 0.5f * k.x, 0, screen.x * 0.5f * k.x, screen.y * k.y};
            REQUIRE(SDL_RenderFillRect(renderer.get(), &light));
            blur.end();
            SDL_Texture* out = blur.result();
            REQUIRE(out != nullptr);
            CHECK(blur.drawCalls() == 2 * (blur.levels() - 1));

            REQUIRE(SDL_SetRenderTarget(renderer.get(), out));
            const SurfacePtr px{SDL_RenderReadPixels(renderer.get(), nullptr)};
            REQUIRE(SDL_SetRenderTarget(renderer.get(), nullptr));
            REQUIRE(px);
            const auto at = [&](int x, int y) {
                Uint8 r = 0, g = 0, b = 0, a = 0;
                REQUIRE(SDL_ReadSurfacePixel(px.get(), x, y, &r, &g, &b, &a));
                CHECK(a == 255); // opaque, so glass never shows holes
                return static_cast<int>(r);
            };
            for (const int y : {0, px->h / 2, px->h - 1}) {
                // The frame's far edges keep their own colour: nothing wraps around.
                CHECK(at(0, y) <= 4);
                CHECK(at(px->w - 1, y) >= 251);
                // Rises steadily across the edge, with a spread near the requested radius.
                int prev = 0;
                int lo = -1;
                int hi = -1;
                for (int x = 0; x < px->w; ++x) {
                    const int v = at(x, y);
                    CHECK(v + 2 >= prev);
                    prev = v;
                    if (lo < 0 && v > 25) lo = x;
                    if (hi < 0 && v > 230) hi = x;
                }
                const float spread =
                    static_cast<float>(hi - lo) * screen.x / static_cast<float>(px->w);
                // The chain deepens in powers of two, so the 10-90% rise lands within a factor of
                // about 1.4 either side of 1.28 radii (a Gaussian whose radius is two sigma).
                CHECK(spread > radius * 0.8f);
                CHECK(spread < radius * 2.0f);
            }
        }
        blur.invalidate();
        CHECK(blur.result() == nullptr);
    }
    SDL_QuitSubSystem(SDL_INIT_VIDEO);
}

TEST_CASE("drawer hover belongs to a tile's entry, not to its slot") {
    REQUIRE(SDL_SetHintWithPriority(SDL_HINT_VIDEO_DRIVER, "dummy", SDL_HINT_OVERRIDE));
    REQUIRE(SDL_InitSubSystem(SDL_INIT_VIDEO));
    {
        const WindowPtr window{SDL_CreateWindow("hud", 64, 64, SDL_WINDOW_HIDDEN)};
        REQUIRE(window);
        const RendererPtr renderer{SDL_CreateRenderer(window.get(), "software")};
        REQUIRE(renderer);
        Font font;
        REQUIRE(font.load(test::assetsDir() / "fonts"));
        REQUIRE(font.build(renderer.get(), 1.0f));
        const Catalog& c = test::catalog();
        HudModel m;
        m.cat = &c;
        m.drawerOpen = true;
        m.category = *c.findCategory("nature");
        Hud hud;
        const Vec2 screen{1280, 800};
        UiInput in;
        in.inside = true;
        const auto frames = [&](int n) {
            for (int i = 0; i < n; ++i) hud.update(in, m, font, screen, 1.0f, 1.0f / 60.0f);
        };
        frames(30); // drawer fully open
        const auto first = [&](int category) {
            std::vector<DrawerEntry> e;
            Hud::categoryEntries(c, category, e);
            REQUIRE_FALSE(e.empty());
            const auto i = static_cast<std::size_t>(e[0].index);
            return "tile:" + (e[0].terrain ? c.terrain[i].id : c.items[i].id);
        };
        const std::string natureTile = first(m.category);
        const auto at = hud.widgetCentre(natureTile, m);
        REQUIRE(at);
        in.x = at->x;
        in.y = at->y;
        frames(30);
        CHECK(hud.highlight(natureTile, m) == doctest::Approx(1.0f));

        // Switch tab with the pointer on the tab, as a click does: the tile now in the same slot
        // must not inherit the fading highlight.
        const int garden = *c.findCategory("garden");
        const auto tab = hud.widgetCentre("tab:garden", m);
        REQUIRE(tab);
        in.x = tab->x;
        in.y = tab->y;
        m.category = garden;
        frames(2);
        const std::string gardenTile = first(garden);
        const auto same = hud.widgetCentre(gardenTile, m);
        REQUIRE(same);
        REQUIRE(same->x == at->x);
        REQUIRE(same->y == at->y);
        CHECK(hud.highlight(gardenTile, m) == 0.0f);
    }
    SDL_QuitSubSystem(SDL_INIT_VIDEO);
}

namespace {

// A hidden software-rendered window with the UI fonts, for interface tests.
struct UiFixture {
    UiFixture() {
        REQUIRE(SDL_SetHintWithPriority(SDL_HINT_VIDEO_DRIVER, "dummy", SDL_HINT_OVERRIDE));
        REQUIRE(SDL_InitSubSystem(SDL_INIT_VIDEO));
        window.reset(SDL_CreateWindow("ui", 64, 64, SDL_WINDOW_HIDDEN));
        REQUIRE(window);
        renderer.reset(SDL_CreateRenderer(window.get(), "software"));
        REQUIRE(renderer);
        REQUIRE(font.load(test::assetsDir() / "fonts"));
    }
    ~UiFixture() {
        renderer.reset();
        window.reset();
        SDL_QuitSubSystem(SDL_INIT_VIDEO);
    }
    UiFixture(const UiFixture&) = delete;
    UiFixture& operator=(const UiFixture&) = delete;

    WindowPtr window;
    RendererPtr renderer;
    Font font;
};

float uiScaleFor(Vec2 screen) {
    return std::clamp(
        std::round(std::max(1.0f, std::min(screen.x / 1600.0f, screen.y / 900.0f)) * 4.0f) / 4.0f,
        1.0f, 3.0f);
}

bool overlap(const Box& a, const Box& b) {
    return a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h;
}

} // namespace

TEST_CASE("first-launch framing shows the open corner clear of the interface at any size") {
    UiFixture ui;
    const Catalog& c = test::catalog();
    const Iso iso = c.iso();
    const World world(c);
    Actors vis(c, 1);
    for (const Vec2 screen : {Vec2{960, 600}, Vec2{1280, 800}, Vec2{1920, 1080}, Vec2{2560, 1440},
                              Vec2{3840, 2160}, Vec2{1600, 1200}}) {
        CAPTURE(screen.x);
        const float s = uiScaleFor(screen);
        REQUIRE(ui.font.build(ui.renderer.get(), s));
        HudModel m;
        m.cat = &c;
        m.visitors = &vis;
        Hud hud;
        hud.update({}, m, ui.font, screen, s, 0);
        const Box safe = hud.safeArea();
        Camera cam(iso, world.landBounds(), 66);
        const TileRect corner = c.stages.front().rects.front();
        cam.frame({safe.x, safe.y, safe.x + safe.w, safe.y + safe.h}, screen, corner);
        const WorldBounds b = landBox(iso, corner, 66);
        const Vec2 tl = cam.worldToScreen({b.x0, b.y0}, screen);
        const Vec2 br = cam.worldToScreen({b.x1, b.y1}, screen);
        CHECK(tl.x >= safe.x - 0.5f);
        CHECK(tl.y >= safe.y - 0.5f);
        CHECK(br.x <= safe.x + safe.w + 0.5f);
        CHECK(br.y <= safe.y + safe.h + 0.5f);
        // The 20x20 corner is 1280 art pixels wide: native 1x from 1080p up, 2x at 4K.
        if (screen.x >= 1920) CHECK(cam.zoom() >= 1.0f);
        if (screen.x >= 3840) CHECK(cam.zoom() == 2.0f);
    }
}

TEST_CASE("the toast and the hint line stop the pointer; small windows keep docks apart") {
    UiFixture ui;
    const Catalog& c = test::catalog();
    Actors vis(c, 1);
    for (const Vec2 screen : {Vec2{320, 240}, Vec2{640, 400}, Vec2{960, 600}, Vec2{1280, 800}}) {
        CAPTURE(screen.x);
        REQUIRE(ui.font.build(ui.renderer.get(), 1.0f));
        HudModel m;
        m.cat = &c;
        m.visitors = &vis;
        m.hint = "Click to place · Esc to cancel";
        m.journalOpen = true;
        m.drawerOpen = true;
        m.category = *c.findCategory("nature");
        Hud hud;
        hud.toast("New visitor: Ducks");
        UiInput in;
        in.inside = true;
        in.x = in.y = -100; // off the interface while things open
        for (int i = 0; i < 30; ++i) hud.update(in, m, ui.font, screen, 1.0f, 1.0f / 60.0f);
        // Every dock button is reachable and no two docks overlap.
        std::vector<Box> buttons;
        for (const char* name : {"build", "remove", "move", "menu", "photo", "clock", "rain",
                                 "journal", "undo", "redo", "recentre", "zoom_out", "zoom_in"}) {
            const auto p = hud.widgetCentre(name, m);
            REQUIRE(p);
            CHECK(p->x > 0);
            CHECK(p->x < screen.x);
            CHECK(p->y > 0);
            CHECK(p->y < screen.y);
            buttons.push_back({p->x - 1, p->y - 1, 2, 2});
        }
        for (std::size_t i = 0; i < buttons.size(); ++i)
            for (std::size_t j = i + 1; j < buttons.size(); ++j)
                CHECK_FALSE(overlap(buttons[i], buttons[j]));
        // The pointer on the toast or on the hint belongs to the interface.
        const Box safe = hud.safeArea();
        CHECK(safe.h >= 0);
        if (screen.x >= 960) {
            const auto toastAt = [&]() {
                const auto at = hud.widgetCentre("toast", m);
                REQUIRE(at);
                in.x = at->x;
                in.y = at->y;
                hud.update(in, m, ui.font, screen, 1.0f, 1.0f / 60.0f);
                return hud.wantsMouse();
            };
            CHECK(toastAt());
        }
    }
}

TEST_CASE("the name beside the pointer stays clear of the title card and the docks (Q5-E-14)") {
    UiFixture ui;
    const Catalog& c = test::catalog();
    Actors vis(c, 1);
    REQUIRE(ui.font.build(ui.renderer.get(), 1.0f));
    const Progress progress(c);
    HudModel m;
    m.cat = &c;
    m.visitors = &vis;
    m.progress = &progress;
    m.worldTip = "Basilica Aemilia";
    Hud hud;
    const Vec2 screen{1280, 800};
    UiInput in;
    in.inside = true;
    const auto clear = [&](float x, float y) {
        in.x = x;
        in.y = y;
        hud.update(in, m, ui.font, screen, 1.0f, 1.0f / 60.0f);
        const Box tip = hud.worldTipBox(ui.font, m.worldTip);
        CHECK_FALSE(overlap(tip, hud.titleBox()));
        for (const char* name : {"build", "journal", "zoom_in", "clock"}) {
            const auto at = hud.widgetCentre(name, m);
            REQUIRE(at);
            CHECK_FALSE(overlap(tip, {at->x - 1, at->y - 1, 2, 2}));
        }
        CHECK(tip.y >= 0);
        CHECK(tip.y + tip.h <= screen.y);
    };
    clear(0, 0); // where a scripted pointer rests: the tip used to cover the title
    const Box title = hud.titleBox();
    clear(title.x + title.w + 2, title.y + 4);
    clear(640, 790);
    clear(1270, 790);
}

TEST_CASE("a long card shows its whole text above the docks; a long title is cut short (Q5-E-12)") {
    UiFixture ui;
    const Catalog& c = test::catalog();
    Actors vis(c, 1);
    REQUIRE(ui.font.build(ui.renderer.get(), 1.0f));
    const Progress progress(c);
    std::string text;
    for (int i = 0; i < 14; ++i)
        text += "Nowruz: the king receives the gifts of every land on the terrace at Pārsa. ";
    HudModel m;
    m.cat = &c;
    m.visitors = &vis;
    m.progress = &progress;
    m.cardTitle = "A title far too long for any card the world would ever open at all";
    m.cardText = text;
    m.cardEpithet = "The new year";
    Hud hud;
    const Vec2 screen{1280, 800};
    UiInput in;
    in.inside = true;
    in.x = in.y = -100;
    for (int i = 0; i < 60; ++i) hud.update(in, m, ui.font, screen, 1.0f, 1.0f / 60.0f);
    const Box card = hud.cardBox();
    REQUIRE(card.w > 0);
    const float textW = card.w - 2 * theme::kPanelPad;
    const int lines = wrapLines(ui.font, Face::Body, text, textW, 100);
    REQUIRE(lines > theme::kCardLines);
    CHECK(card.h >= static_cast<float>(lines) * ui.font.lineHeight(Face::Body));
    CHECK(card.y >= 0);
    // ... and clear of the docks.
    const auto build = hud.widgetCentre("build", m);
    REQUIRE(build);
    CHECK(card.y + card.h < build->y);
}

TEST_CASE("the corner's news folds away when the view leaves home and waits for it (Q5-E-02)") {
    UiFixture ui;
    const Catalog& c = test::catalog();
    Actors vis(c, 1);
    REQUIRE(ui.font.build(ui.renderer.get(), 1.0f));
    const Progress progress(c);
    HudModel m;
    m.cat = &c;
    m.visitors = &vis;
    m.progress = &progress;
    Hud hud;
    UiInput in;
    const auto run = [&](int frames) {
        for (int i = 0; i < frames; ++i)
            hud.update(in, m, ui.font, {1280, 800}, 1.0f, 1.0f / 60.0f);
    };
    hud.toast("New visitor: Ducks", true);
    run(10);
    CHECK(hud.toastText() == "New visitor: Ducks");
    m.away = true; // a journey to Athens with the toast still up
    run(2);
    CHECK(hud.toastText().empty());
    hud.toast("New land: the meadow", true);
    hud.toast("Postcard saved"); // not the corner's: shown wherever the view is
    run(60);
    CHECK(hud.toastText() == "Postcard saved"); // the corner's waits; others go on by
    run(600);
    CHECK(hud.toastText().empty());
    m.away = false;
    run(60);
    CHECK(hud.toastText() == "New land: the meadow");
}

TEST_CASE("towns on the map carry readable names that never overlap (V6-018)") {
    UiFixture ui;
    // The overview's size, the three cities and a cluster of towns as close as Ostia and Portus.
    Sprite art;
    art.w = 2560;
    art.h = 896;
    const std::vector<MapPlace> places{{"Roma", "", "", {300, 420}, MapMarker::City},
                                       {"Ostia", "", "", {262, 452}, MapMarker::Town},
                                       {"Portus", "", "", {258, 446}, MapMarker::Town},
                                       {"Tibur", "", "", {330, 405}, MapMarker::Town},
                                       {"Mons Albanus", "", "", {322, 440}, MapMarker::Town},
                                       {"Capua", "", "", {420, 520}, MapMarker::Town},
                                       {"Beneventum", "", "", {470, 515}, MapMarker::Town},
                                       {"Brundisium", "", "", {700, 560}, MapMarker::Town},
                                       {"Delphi", "", "", {1200, 520}, MapMarker::Town},
                                       {"Corinth", "", "", {1240, 560}, MapMarker::Town},
                                       {"Athenai", "", "", {1300, 580}, MapMarker::City},
                                       {"Parsa", "", "", {2400, 700}, MapMarker::City}};
    MapModel m;
    m.image = &art;
    m.places = places;
    for (const Vec2 screen : {Vec2{1580, 845}, Vec2{960, 600}, Vec2{2560, 1440}})
        for (const float s : {1.0f, 1.5f, 2.0f}) {
            REQUIRE(ui.font.build(ui.renderer.get(), s));
            MapScreen map;
            map.open(true);
            for (int i = 0; i < 30; ++i)
                map.update(-1, -1, false, false, false, m, ui.font, screen, s, 1.0f / 60.0f);
            const auto labels = map.labels();
            INFO(screen.x << "x" << screen.y << " at " << s);
            // Most towns named (at a small window all but the crowded pair); with large
            // text in a small window the crowded ones keep their names for the hover tip.
            MESSAGE(labels.size() << " of 9 towns named");
            CHECK(labels.size() >= (screen.x >= 1580 && s <= 1.0f ? 7u : 3u));
            for (std::size_t i = 0; i < labels.size(); ++i) {
                const Box& a = labels[i].box;
                CHECK(a.h >= ui.font.lineHeight(Face::Body)); // the interface's own text size
                CHECK(a.x >= 0);
                CHECK(a.x + a.w <= screen.x);
                for (std::size_t j = i + 1; j < labels.size(); ++j)
                    CHECK_FALSE(overlap(a, labels[j].box));
                for (std::size_t k = 0; k < places.size(); ++k) {
                    const Vec2 c = map.markerAt(m, static_cast<int>(k));
                    CHECK_FALSE(a.contains(c.x, c.y));
                }
            }
        }
}

TEST_CASE("sketchbook widgets have ids of their own: many places, no nook, a wish's Not now") {
    UiFixture ui;
    const Catalog& c = test::catalog();
    Actors vis(c, 1);
    REQUIRE(ui.font.build(ui.renderer.get(), 1.0f));
    // Twelve places and no nook found (L-008: the tenth place's tab took the first "Not now"'s
    // id, so its click snoozed another wish).
    static constexpr std::string_view kNames[] = {"A", "B", "C", "D", "E", "F",
                                                  "G", "H", "I", "J", "K", "L"};
    std::vector<JournalPlace> places;
    for (const std::string_view n : kNames) places.push_back({n, "", {}});
    WishCard wish;
    wish.wish = 5;
    wish.text = "A wish";
    const Progress progress(c); // no nook found yet
    HudModel m;
    m.cat = &c;
    m.visitors = &vis;
    m.progress = &progress;
    m.journalOpen = true;
    m.places = places;
    m.wishes = std::span(&wish, 1);
    Hud hud;
    const Vec2 screen{1280, 800};
    UiInput in;
    in.inside = true;
    in.x = in.y = -100;
    for (int i = 0; i < 30; ++i) hud.update(in, m, ui.font, screen, 1.0f, 1.0f / 60.0f);
    const auto at = hud.widgetCentre("sketch_not_now", m);
    REQUIRE(at);
    in.x = at->x;
    in.y = at->y;
    hud.update(in, m, ui.font, screen, 1.0f, 1.0f / 60.0f);
    in.pressed = true;
    hud.update(in, m, ui.font, screen, 1.0f, 1.0f / 60.0f);
    in.pressed = false;
    in.released = true;
    hud.update(in, m, ui.font, screen, 1.0f, 1.0f / 60.0f);
    const auto acts = hud.actions();
    const auto snooze = std::ranges::find_if(
        acts, [](const HudAction& a) { return a.kind == HudAction::Kind::Snooze; });
    REQUIRE(snooze != acts.end());
    CHECK(snooze->arg == 5);
}

TEST_CASE("a figure's own name is shown only when the card does not already say it (Q5-E-13)") {
    CHECK(namedAlready("Kūruš (a memory)", "Kūruš", "Cyrus, founder (a memory)"));
    CHECK(namedAlready("Hermon, stonecutter", "Hermon", "Stonecutter from Ionia"));
    CHECK(namedAlready("Aspasia", "Ἀσπασία", "Aspasia of Miletus"));
    CHECK_FALSE(namedAlready("Hadrianus", "Hadrian", "Emperor"));
    CHECK_FALSE(namedAlready("Xšayāršā", "Xerxes", "King of kings"));
}

TEST_CASE("cutting text drops whole characters, never half of one (L-017)") {
    // "Pārsa": the ā is two bytes; every cut leaves valid UTF-8.
    std::string_view s = "P\xC4\x81rsa";
    std::vector<std::string_view> cuts;
    while (!s.empty()) {
        dropLastCharacter(s);
        cuts.push_back(s);
    }
    CHECK(cuts == std::vector<std::string_view>{"P\xC4\x81rs", "P\xC4\x81r", "P\xC4\x81", "P", ""});
}

TEST_CASE("settings fit every window and interface size, every row reachable, room for more") {
    UiFixture ui;
    const Profile profile;
    MenuModel m;
    m.profile = &profile;
    m.residentName = "Laeticia";
    UiInput in;
    in.inside = true;
    in.x = in.y = -100;
    const Vec2 screens[] = {{960, 600},   {1280, 800},  {1580, 845},
                            {1920, 1080}, {2560, 1440}, {3840, 2160}};
    for (const Vec2 base : screens)
        for (const float factor : kUiScales)
            // The window as it is, and with two rows' height less: the look and clouds rows the
            // other branches add must fit too.
            for (const int fewer : {0, 2}) {
                const float fit =
                    std::min(base.x / theme::kReferenceW, base.y / theme::kReferenceH);
                const float f = factor > 0 ? factor : 1.0f;
                const float s = std::clamp(std::round(std::max(1.0f, fit) * f * 4.0f) / 4.0f,
                                           f < 1.0f ? 0.75f : 1.0f, theme::kMaxScale);
                REQUIRE(ui.font.build(ui.renderer.get(), s));
                const Vec2 screen{base.x, base.y - static_cast<float>(fewer) * theme::kRowH * s};
                Menus menus;
                menus.open(Page::Settings);
                const auto layout = [&](float wheel) {
                    in.wheel = wheel;
                    menus.update(in, m, ui.font, screen, s, 1.0f / 60.0f);
                    in.wheel = 0;
                };
                layout(0);
                const auto check = [&] {
                    const std::vector<Box> boxes = menus.widgetBoxes();
                    INFO(screen.x << "x" << screen.y << " at " << s);
                    for (const Box& b : boxes) {
                        CHECK(b.x >= -0.5f);
                        CHECK(b.y >= -0.5f);
                        CHECK(b.x + b.w <= screen.x + 0.5f);
                        CHECK(b.y + b.h <= screen.y + 0.5f);
                    }
                    for (std::size_t i = 0; i < boxes.size(); ++i)
                        for (std::size_t j = i + 1; j < boxes.size(); ++j) {
                            const Box& a = boxes[i];
                            const Box& b = boxes[j];
                            const bool over = a.x + 0.5f < b.x + b.w && b.x + 0.5f < a.x + a.w &&
                                              a.y + 0.5f < b.y + b.h && b.y + 0.5f < a.y + a.h;
                            CHECK_FALSE(over);
                        }
                    CHECK(menus.widgetCentre("done"));
                };
                check();
                // Every row of both sides (the look tier and clouds too) can be reached: seen
                // at some scroll position on the way to the end.
                static constexpr const char* kRows[] = {
                    "music",    "effects",       "ambience", "mute",  "fullscreen",
                    "ui_scale", "reduce_motion", "grid",     "vsync", "look",
                    "clouds",   "chatty",        "quiet",    "replay"};
                std::set<std::string> seen;
                for (int k = 0; k < 30; ++k) {
                    for (const char* row : kRows)
                        if (menus.widgetCentre(row)) seen.insert(row);
                    if (menus.widgetCentre("replay")) break;
                    layout(-1);
                    check();
                }
                for (const char* row : kRows) CHECK_MESSAGE(seen.contains(row), row);
            }
}

TEST_CASE("world cards keep their own ids past a hundred worlds (L-111)") {
    UiFixture ui;
    REQUIRE(ui.font.build(ui.renderer.get(), 1.0f));
    const Profile profile;
    std::vector<MenuWorld> worlds(120);
    for (MenuWorld& w : worlds) w.name = "A world";
    MenuModel m;
    m.profile = &profile;
    m.worlds = worlds;
    Menus menus;
    menus.open(Page::Worlds);
    const Vec2 screen{1280, 800};
    UiInput in;
    in.inside = true;
    for (int i = 0; i < 60; ++i) {
        in.wheel = i < 50 ? -1.0f : 0.0f; // scrolled to the last cards
        menus.update(in, m, ui.font, screen, 1.0f, 1.0f / 60.0f);
    }
    in.wheel = 0;
    const auto click = [&](const std::string& name) {
        const auto at = menus.widgetCentre(name);
        REQUIRE(at);
        menus.clearActions();
        in.x = at->x;
        in.y = at->y;
        menus.update(in, m, ui.font, screen, 1.0f, 1.0f / 60.0f);
        in.pressed = true;
        menus.update(in, m, ui.font, screen, 1.0f, 1.0f / 60.0f);
        in.pressed = false;
        in.released = true;
        menus.update(in, m, ui.font, screen, 1.0f, 1.0f / 60.0f);
        in.released = false;
    };
    const auto played = [&] {
        for (const MenuAction& a : menus.actions())
            if (a.kind == MenuAction::Kind::Play) return a.arg;
        return -1;
    };
    // A card past the hundredth (world 110's card once had the id of world 10's Play button).
    int n = 119;
    while (n >= 100 && !menus.widgetCentre("card:" + std::to_string(n))) --n;
    REQUIRE(n >= 100);
    click("card:" + std::to_string(n));
    CHECK(played() == -1);
    click("play:" + std::to_string(n));
    CHECK(played() == n);
}

TEST_CASE("the drawer scrolls to tiles off its page and shows row arrows") {
    UiFixture ui;
    const Catalog& c = test::catalog();
    Actors vis(c, 1);
    REQUIRE(ui.font.build(ui.renderer.get(), 1.0f));
    HudModel m;
    m.cat = &c;
    m.visitors = &vis;
    m.drawerOpen = true;
    m.category = *c.findCategory("nature");
    Hud hud;
    const Vec2 screen{640, 480};
    UiInput in;
    for (int i = 0; i < 30; ++i) hud.update(in, m, ui.font, screen, 1.0f, 1.0f / 60.0f);
    CHECK(hud.widgetCentre("scroll_down", m).has_value());
    CHECK_FALSE(hud.widgetCentre("tile:lily_pads", m).has_value());
    REQUIRE(hud.reveal("tile:lily_pads", m));
    hud.update(in, m, ui.font, screen, 1.0f, 1.0f / 60.0f);
    CHECK(hud.widgetCentre("tile:lily_pads", m).has_value());
    CHECK_FALSE(hud.reveal("tile:cottage", m)); // not in the open tab
}

TEST_CASE("glass keeps text contrast high over a white daytime sky") {
    UiFixture ui;
    REQUIRE(ui.font.build(ui.renderer.get(), 1.0f));
    // A plain white backdrop (the brightest the blurred sky can be) behind one glass panel.
    TexturePtr white{SDL_CreateTexture(ui.renderer.get(), SDL_PIXELFORMAT_RGBA8888,
                                       SDL_TEXTUREACCESS_TARGET, 64, 64)};
    REQUIRE(white);
    REQUIRE(SDL_SetRenderTarget(ui.renderer.get(), white.get()));
    REQUIRE(SDL_SetRenderDrawColorFloat(ui.renderer.get(), 1, 1, 1, 1));
    REQUIRE(SDL_RenderClear(ui.renderer.get()));
    REQUIRE(SDL_SetRenderTarget(ui.renderer.get(), nullptr));
    REQUIRE(SDL_SetRenderDrawColorFloat(ui.renderer.get(), 1, 1, 1, 1));
    REQUIRE(SDL_RenderClear(ui.renderer.get()));
    Batch batch(ui.renderer.get());
    Painter p(batch, ui.font, {white.get(), {64, 64}, 1.0f}, 1.0f);
    p.glass({4, 4, 56, 56}, 8, 1.0f, theme::kGlass);
    p.endGlass();
    batch.flush();
    const SDL_Rect r{32, 32, 1, 1};
    const SurfacePtr px{SDL_RenderReadPixels(ui.renderer.get(), &r)};
    REQUIRE(px);
    Uint8 cr = 0, cg = 0, cb = 0, ca = 0;
    REQUIRE(SDL_ReadSurfacePixel(px.get(), 0, 0, &cr, &cg, &cb, &ca));
    const auto lin = [](double v) {
        v /= 255.0;
        return v <= 0.04045 ? v / 12.92 : std::pow((v + 0.055) / 1.055, 2.4);
    };
    const double bg = 0.2126 * lin(cr) + 0.7152 * lin(cg) + 0.0722 * lin(cb);
    const auto& ink = theme::kInk;
    const double fg =
        0.2126 * lin(ink.r * 255) + 0.7152 * lin(ink.g * 255) + 0.0722 * lin(ink.b * 255);
    const double contrast = (fg + 0.05) / (bg + 0.05);
    CAPTURE(contrast);
    CHECK(contrast >= 7.0);
}

TEST_CASE("a large panel's fill is watertight: no seam between its triangles") {
    // The outline of a rounded panel whose corners fall between pixels (a 960 x 600 window
    // put the worlds screen there, and dotted lines ran across its glass): every side of
    // every triangle inside the fill is shared, value for value, with exactly one other
    // triangle, and the sides nobody shares are the outline itself.
    for (const float nudge : {0.0f, 0.25f, 0.37f}) {
        std::vector<SDL_FPoint> outline;
        const float x0 = 31.5f + nudge;
        const float y0 = 31.25f + nudge;
        const float x1 = 927.25f + nudge;
        const float y1 = 568.5f + nudge;
        const float rad = nudge == 0.37f ? 0.0f : 18.0f; // the last: square corners
        const SDL_FPoint corners[4] = {
            {x1 - rad, y0 + rad}, {x1 - rad, y1 - rad}, {x0 + rad, y1 - rad}, {x0 + rad, y0 + rad}};
        for (int c = 0; c < 4; ++c)
            for (int k = 0; k <= 8; ++k) {
                const float a =
                    (static_cast<float>(c) - 1.0f + static_cast<float>(k) / 8.0f) * 1.5707964f;
                outline.push_back(
                    {corners[c].x + std::cos(a) * rad, corners[c].y + std::sin(a) * rad});
            }
        std::vector<SDL_FPoint> points;
        std::vector<int> indices;
        fanMesh({(x0 + x1) * 0.5f, (y0 + y1) * 0.5f}, outline, 384.0f, points, indices);
        REQUIRE(indices.size() % 3 == 0);
        REQUIRE(indices.size() > 4 * 3 * 2); // it was cut up: more than a fan of its four sides
        using Point = std::pair<float, float>;
        using Side = std::pair<Point, Point>;
        std::map<Side, int> sides;
        const auto pt = [&](int i) {
            const SDL_FPoint p = points[static_cast<std::size_t>(i)];
            return Point{p.x, p.y};
        };
        for (std::size_t t = 0; t < indices.size(); t += 3)
            for (int e = 0; e < 3; ++e) {
                Point a = pt(indices[t + static_cast<std::size_t>(e)]);
                Point b = pt(indices[t + static_cast<std::size_t>((e + 1) % 3)]);
                if (b < a) std::swap(a, b);
                ++sides[{a, b}];
            }
        std::set<Side> rim;
        for (std::size_t i = 0; i < outline.size(); ++i) {
            Point a{outline[i].x, outline[i].y};
            const SDL_FPoint q = outline[(i + 1) % outline.size()];
            Point b{q.x, q.y};
            if (b < a) std::swap(a, b);
            rim.insert({a, b});
        }
        // A side nobody shares is on the outline: one of its sides, or a piece of a straight
        // (level or upright) one, whose ends are on it exactly.
        float left = outline[0].x;
        float right = left;
        float top = outline[0].y;
        float bottom = top;
        for (const SDL_FPoint p : outline) {
            left = std::min(left, p.x);
            right = std::max(right, p.x);
            top = std::min(top, p.y);
            bottom = std::max(bottom, p.y);
        }
        int open = 0;
        int crowded = 0;
        for (const auto& [side, n] : sides) {
            if (n > 2) ++crowded;
            if (n != 1 || rim.contains(side)) continue;
            const bool level = side.first.second == side.second.second &&
                               (side.first.second == top || side.first.second == bottom);
            const bool upright = side.first.first == side.second.first &&
                                 (side.first.first == left || side.first.first == right);
            if (!level && !upright) ++open;
        }
        CHECK(open == 0);
        CHECK(crowded == 0);
        // No triangle is empty (a square corner's two points in one place make none).
        int empty = 0;
        for (std::size_t t = 0; t < indices.size(); t += 3) {
            const Point a = pt(indices[t]);
            const Point b = pt(indices[t + 1]);
            const Point c = pt(indices[t + 2]);
            const float twice = (b.first - a.first) * (c.second - a.second) -
                                (c.first - a.first) * (b.second - a.second);
            empty += twice == 0 ? 1 : 0;
        }
        CHECK(empty == 0);
        // And no triangle is larger than asked.
        float longest = 0;
        for (const auto& [side, n] : sides)
            longest = std::max(longest, std::hypot(side.second.first - side.first.first,
                                                   side.second.second - side.first.second));
        CHECK(longest <= 384.0f);
    }
}

TEST_CASE("text faces carry the minus sign and kerning") {
    UiFixture ui;
    REQUIRE(ui.font.build(ui.renderer.get(), 1.0f));
    // A missing glyph would fall back to '?', which is far narrower than U+2212.
    CHECK(ui.font.measure(Face::Body, "−") != ui.font.measure(Face::Body, "?"));
    CHECK(ui.font.measure(Face::Body, "look") > ui.font.measure(Face::Body, "loo"));
}

TEST_CASE("a scale the glyphs cannot be built at keeps the last atlas (L-014)") {
    UiFixture ui;
    REQUIRE(ui.font.build(ui.renderer.get(), 1.0f));
    const float word = ui.font.measure(Face::Body, "Laeticia");
    SDL_Texture* const before = ui.font.texture();
    // At this size the glyphs fit no texture: the game used to quit on the spot, unsaved.
    CHECK(ui.font.build(ui.renderer.get(), 60.0f));
    CHECK(ui.font.texture() == before);
    CHECK(ui.font.scale() == doctest::Approx(1.0f));
    CHECK(ui.font.measure(Face::Body, "Laeticia") == doctest::Approx(word));
    // Asked again it is not retried every frame, and a good scale builds at once.
    CHECK(ui.font.build(ui.renderer.get(), 60.0f));
    REQUIRE(ui.font.build(ui.renderer.get(), 2.0f));
    CHECK(ui.font.scale() == doctest::Approx(2.0f));
    CHECK(ui.font.measure(Face::Body, "Laeticia") > word * 1.5f);
}

namespace {

// A click is a jump between neighbouring samples far beyond the local motion of the signal,
// and a corner (the signal turns at once, as a step or an impulse does; a loud high tone, a
// bird's chirp, is a jump between samples too but bends smoothly).
int clicksIn(const std::vector<float>& s) {
    constexpr std::size_t kWindow = 512;
    const std::size_t frames = s.size() / 2;
    int clicks = 0;
    for (int ch = 0; ch < 2; ++ch) {
        std::vector<float> d(frames, 0);
        for (std::size_t i = 1; i < frames; ++i)
            d[i] = std::abs(s[i * 2 + static_cast<std::size_t>(ch)] -
                            s[(i - 1) * 2 + static_cast<std::size_t>(ch)]);
        double sum = 0;
        for (std::size_t i = 0; i < std::min(frames, 2 * kWindow); ++i) sum += d[i] * d[i];
        for (std::size_t i = kWindow; i + kWindow < frames; ++i) {
            const double local = std::sqrt((sum - d[i] * d[i]) / (2.0 * kWindow - 1));
            const auto at = [&](std::size_t k) { return s[k * 2 + static_cast<std::size_t>(ch)]; };
            const float bend = i + 1 < frames ? std::abs(at(i + 1) - 2 * at(i) + at(i - 1)) : 0;
            if (d[i] > 0.05f && d[i] > 8.0 * local + 0.01 && bend > 0.9f * d[i]) ++clicks;
            sum += static_cast<double>(d[i + kWindow]) * d[i + kWindow] -
                   static_cast<double>(d[i - kWindow]) * d[i - kWindow];
        }
    }
    return clicks;
}

} // namespace

// Analyses the mix captured by the audio_capture run (path in LC_AUDIO_CAPTURE): a drag-paint,
// a mute toggle and a day/night crossfade must neither clip nor click.
TEST_CASE("process: a group's CPU stalls are read from its cpu.stat") {
    // What Linux writes for a group with a quota; the fields the bench reports are the count of
    // periods in which the group was frozen and the time it stood still.
    const lc::CpuStalls s = lc::cpuStallsFrom("usage_usec 9120011\nuser_usec 8000000\n"
                                              "system_usec 1120011\nnr_periods 5120\n"
                                              "nr_throttled 410583\nthrottled_usec 125292781\n"
                                              "nr_bursts 0\nburst_usec 0\n");
    CHECK(s.count == 410583);
    CHECK(s.ms == doctest::Approx(125292.781));
    // A group without a quota writes neither: nothing stalled.
    const lc::CpuStalls none = lc::cpuStallsFrom("usage_usec 12\nuser_usec 8\nsystem_usec 4\n");
    CHECK(none.count == 0);
    CHECK(none.ms == 0.0);
    // A name that ends like a field's is not that field.
    CHECK(lc::cpuStallsFrom("core.nr_throttled 7\nnr_throttled 3\n").count == 3);
    // Whatever this process runs in: a count that never goes down.
    const lc::CpuStalls a = lc::cpuLimitStalls();
    const lc::CpuStalls z = lc::cpuLimitStalls();
    CHECK(z.count >= a.count);
    CHECK(z.ms >= a.ms);
}

TEST_CASE("capture: the mix has no clipping and no clicks") {
    const char* file = std::getenv("LC_AUDIO_CAPTURE");
    if (file == nullptr) {
        MESSAGE("LC_AUDIO_CAPTURE not set; run through ctest");
        return;
    }
    const auto s = readWavFloat(file);
    REQUIRE_MESSAGE(s.has_value(), s.error());
    REQUIRE(s->size() > static_cast<std::size_t>(kMixRate) * 2 * 3);
    float peak = 0;
    double energy = 0;
    for (const float v : *s) {
        peak = std::max(peak, std::abs(v));
        energy += static_cast<double>(v) * v;
    }
    CHECK(peak <= tuning::kLimiterCeiling + 1e-4f); // never reaches full scale
    CHECK(energy > 0);                              // something was audible
    // Positional layers lean left or right: the two channels are not the same signal.
    double left = 0;
    double right = 0;
    for (std::size_t i = 0; i + 1 < s->size(); i += 2) {
        left += static_cast<double>((*s)[i]) * (*s)[i];
        right += static_cast<double>((*s)[i + 1]) * (*s)[i + 1];
    }
    CHECK(std::abs(left - right) > 0.01 * (left + right));
    CHECK(clicksIn(*s) == 0);
}

// Analyses the mix of the world_year run (path in LC_AUDIO_YEAR): Rome's and Pārsa's seasons
// and nights, the open sea and the snow, crossfaded as the year turns.
TEST_CASE("capture: the year away from home is never silent, balanced, unclipped and smooth") {
    const char* file = std::getenv("LC_AUDIO_YEAR");
    if (file == nullptr) {
        MESSAGE("LC_AUDIO_YEAR not set; run through ctest");
        return;
    }
    const auto s = readWavFloat(file);
    REQUIRE_MESSAGE(s.has_value(), s.error());
    const auto second = static_cast<std::size_t>(kMixRate) * 2;
    REQUIRE(s->size() > second * 60);
    float peak = 0;
    for (const float v : *s) peak = std::max(peak, std::abs(v));
    CHECK(peak <= tuning::kLimiterCeiling + 1e-4f);
    // Every second is heard (above -60 dBFS) and none is loud (under -10 dBFS); the beds sit in
    // the middle of the field, not to one side (L-113: within 3 dB over the whole run).
    double left = 0;
    double right = 0;
    int quiet = 0;
    int loud = 0;
    for (std::size_t at = 0; at + second <= s->size(); at += second) {
        double e = 0;
        for (std::size_t i = at; i + 1 < at + second; i += 2) {
            left += static_cast<double>((*s)[i]) * (*s)[i];
            right += static_cast<double>((*s)[i + 1]) * (*s)[i + 1];
            e += static_cast<double>((*s)[i]) * (*s)[i] +
                 static_cast<double>((*s)[i + 1]) * (*s)[i + 1];
        }
        const double db = 10.0 * std::log10(e / static_cast<double>(second) + 1e-20);
        if (db < -60.0) ++quiet;
        if (db > -10.0) ++loud;
    }
    CHECK(quiet == 0);
    CHECK(loud == 0);
    CHECK(std::abs(10.0 * std::log10(left / right)) < 3.0);
    CHECK(clicksIn(*s) == 0);
}

// Analyses the world's mix (path in LC_AUDIO_MIX, segments in its .marks): loudness, peaks,
// balance and the buses' shares of each situation, against the targets in core/tuning.hpp.
TEST_CASE("capture: the mix across the world is balanced, unclipped and smooth") {
    const char* file = std::getenv("LC_AUDIO_MIX");
    if (file == nullptr) {
        MESSAGE("LC_AUDIO_MIX not set; run through ctest");
        return;
    }
    const auto s = readWavFloat(file);
    REQUIRE_MESSAGE(s.has_value(), s.error());
    std::ifstream marks(std::string(file) + ".marks");
    REQUIRE(marks);
    struct Segment {
        std::string name;
        meter::Reading r;
        double music = 0, fx = 0, amb = 0; // dB of the buses' sum
    };
    std::vector<Segment> segs;
    std::string name;
    std::size_t from = 0, to = 0;
    double em = 0, ef = 0, ea = 0;
    while (marks >> name >> from >> to >> em >> ef >> ea) {
        REQUIRE(to * 2 <= s->size());
        const std::span<const float> part(s->data() + from * 2, (to - from) * 2);
        const double sum = em + ef + ea + 1e-20;
        Segment g{name, meter::measure(part), 10 * std::log10(em / sum + 1e-12),
                  10 * std::log10(ef / sum + 1e-12), 10 * std::log10(ea / sum + 1e-12)};
        MESSAGE(
            std::format("{:<26} {:6.1f} LUFS  st {:6.1f}  tp {:6.1f}  bal {:5.1f}  low {:5.1f}  "
                        "high {:6.1f}  jump {:4.1f}  music {:6.1f}  fx {:6.1f}  amb {:6.1f}",
                        g.name, g.r.integrated, g.r.shortMax, g.r.truePeak, g.r.balance, g.r.low,
                        g.r.high, g.r.jump, g.music, g.fx, g.amb));
        const std::vector<float> copy(part.begin(), part.end());
        CHECK_MESSAGE(clicksIn(copy) == 0, g.name);
        CHECK_MESSAGE(g.r.truePeak <= tuning::kMixTruePeak, g.name);
        CHECK_MESSAGE(std::abs(g.r.balance) <= tuning::kMixBalance, g.name);
        if (g.name != "mute") { // the mute fades to silence and back on purpose
            CHECK_MESSAGE(g.r.integrated >= tuning::kMixQuietest, g.name);
            CHECK_MESSAGE(g.r.integrated <= tuning::kMixLoudest, g.name);
            CHECK_MESSAGE(g.r.jump <= tuning::kMixJump, g.name);
        }
        // A city's piece is heard over its streets.
        if (g.music > -100 && !g.name.starts_with("home") && !g.name.starts_with("title") &&
            !g.name.starts_with("travel") && g.name != "map.open" && g.name != "pause" &&
            g.name != "mute")
            CHECK_MESSAGE(g.music - g.amb >= tuning::kMixMusicUnder, g.name);
        segs.push_back(g);
    }
    REQUIRE(segs.size() > 30);
    // Neighbouring places are within a few LU of each other (QA5 Q5-S-01: the stretches were
    // dropouts beside the cities).
    const auto loud = [&](std::string_view n) {
        const auto it = std::ranges::find(segs, n, &Segment::name);
        REQUIRE_MESSAGE(it != segs.end(), n);
        return it->r.integrated;
    };
    static constexpr std::pair<std::string_view, std::string_view> kNeighbours[] = {
        {"home.summer.day", "latium.road"},     {"latium.road", "rome.market"},
        {"rome.market", "ostia.harbour"},       {"ostia.harbour", "tyrrhenian.sea"},
        {"athens.market", "corinth.town"},      {"corinth.town", "sparta.villages"},
        {"parsa.market", "persian_gates.road"}, {"persian_gates.road", "zagros.land"},
        {"rome.market", "athens.market"},       {"athens.market", "parsa.market"}};
    for (const auto& [a, b] : kNeighbours)
        CHECK_MESSAGE(std::abs(loud(a) - loud(b)) <= tuning::kMixNeighbours, a << " / " << b);
}
