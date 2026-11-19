// The shader path's pure parts (src/render/gpu/look.hpp, src/worldview/world_lights.hpp): tiers,
// the region grade from `theme.look`, the wind, flicker and the lights' hours; and the world
// data's lights matched to the committed world's items.

#include "core/catalog.hpp"
#include "render/atlas.hpp"
#include "render/gpu/look.hpp"
#include "render/gpu/seasons.hpp"
#include "render/gpu/tuning.hpp"
#include "world/loader.hpp"
#include "worldview/renderer.hpp"
#include "worldview/world_lights.hpp"

#include <doctest.h>
#include <nlohmann/json.hpp>

#include <cmath>
#include <numbers>
#include <optional>

using namespace lc;
using namespace lc::worldview;

namespace {

bool near(float a, float b, float tol = 1e-3f) {
    return std::abs(a - b) <= tol;
}

double hourAt(double h) {
    return (h - 6.0) / 24.0 - std::floor((h - 6.0) / 24.0);
}

} // namespace

TEST_CASE("gpu: quality ids round-trip; unknown ones are refused") {
    for (int i = 0; i < gpu::kQualityCount; ++i) {
        const auto q = static_cast<gpu::Quality>(i);
        CHECK(gpu::parseQuality(gpu::qualityId(q)) == q);
    }
    CHECK_FALSE(gpu::parseQuality("ultra").has_value());
    CHECK_FALSE(gpu::parseQuality("").has_value());
    for (int i = 0; i < gpu::kCloudModes; ++i) {
        const auto c = static_cast<gpu::Clouds>(i);
        CHECK(gpu::parseClouds(gpu::cloudsId(c)) == c);
    }
    CHECK_FALSE(gpu::parseClouds("thick").has_value());
}

TEST_CASE("gpu: a neutral grade leaves colours as they are; night cools at the same luma") {
    const gpu::GradePhase neutral;
    for (const Rgb c : {Rgb{0.8f, 0.6f, 0.4f}, Rgb{0.1f, 0.2f, 0.3f}, Rgb{0.5f, 0.5f, 0.5f}}) {
        const Rgb g = gpu::applyGrade(neutral, c);
        CHECK(near(g.r, c.r));
        CHECK(near(g.g, c.g));
        CHECK(near(g.b, c.b));
    }
    const Rgb warm{0.30f, 0.24f, 0.18f};
    const Rgb cooled = gpu::applyGrade(neutral, warm, gpu::nightTint(), 1.0f);
    const auto luma = [](Rgb c) { return 0.299f * c.r + 0.587f * c.g + 0.114f * c.b; };
    CHECK(cooled.b > cooled.r);
    CHECK(near(luma(cooled), luma(warm), 0.01f));
}

TEST_CASE("gpu: the curve works on lightness, so warm earth is not saturated into orange") {
    gpu::GradePhase g;
    g.contrast = 0.48f;
    const Rgb earth{0.78f, 0.62f, 0.44f};
    const Rgb out = gpu::applyGrade(g, earth);
    // The channels keep their proportions (hue and saturation stay); only lightness moves.
    CHECK(near(out.g / out.r, earth.g / earth.r, 0.01f));
    CHECK(near(out.b / out.r, earth.b / earth.r, 0.01f));
}

TEST_CASE("gpu: a region's look sits at the phase centres and fills gaps from the fallback") {
    const nlohmann::json look = nlohmann::json::parse(R"({
        "phases": {"day": {"wb": [1.1, 1.0, 0.9], "exposure": 0.9, "contrast": 0.4},
                   "night": {"exposure": 0.4}},
        "sky": {"day": ["#000000", "#808080", "#ffffff"]},
        "shade": {"day": "#6f98d8"},
        "haze": {"colour": "#ff0000", "strength": 0.1, "by_zoom": {"quarter": 0.3}},
        "water": {"body": "#204060"}})");
    const nlohmann::json seasons = nlohmann::json::parse(
        R"({"winter": {"grade": [0.9, 1.0, 1.1], "look": {"saturation": -0.1}}})");
    const gpu::RegionLook& home = gpu::homeLook();
    const gpu::RegionLook l = gpu::parseLook(look, seasons, home);
    CHECK(near(l.phases[1].wb.r, 1.1f));
    CHECK(near(l.phases[1].exposure, 0.9f));
    CHECK(near(l.phases[1].shoulder, home.phases[1].shoulder)); // not written: the fallback's
    CHECK(near(l.phases[3].exposure, 0.4f));
    CHECK(near(l.phases[0].exposure, home.phases[0].exposure));
    CHECK(near(l.sky[1][2].r, 1.0f));
    CHECK(near(l.haze.r, 1.0f));
    CHECK(near(l.hazeByLod[0], 0.1f));
    CHECK(near(l.hazeByLod[2], 0.3f));
    CHECK(near(l.hazeByLod[1], home.hazeByLod[1]));
    CHECK(near(l.water.b, static_cast<float>(0x60) / 255.0f));
    CHECK(near(gpu::gradeAt(l, 0.3, -1, 0).water.g, static_cast<float>(0x40) / 255.0f));
    // At the day phase's centre the day's grade, exactly; winter shifts it.
    const gpu::GradeAt day = gpu::gradeAt(l, phaseCentre(Phase::Day), -1, 0);
    CHECK(near(day.grade.exposure, 0.9f));
    CHECK(near(day.grade.contrast, 0.4f));
    CHECK(near(day.shade.b, static_cast<float>(0xd8) / 255.0f));
    const gpu::GradeAt winter = gpu::gradeAt(l, phaseCentre(Phase::Day), 3, 2);
    CHECK(near(winter.grade.wb.r, 1.1f * 0.9f));
    CHECK(near(winter.grade.saturation, l.phases[1].saturation - 0.1f));
    CHECK(near(winter.hazeStrength, 0.3f));
    // Between two centres a blend of the two, continuous.
    const double mid = (phaseCentre(Phase::Day) + phaseCentre(Phase::Dusk)) * 0.5;
    const float e = gpu::gradeAt(l, mid, -1, 0).grade.exposure;
    CHECK(e < 0.9f);
    CHECK(e > l.phases[2].exposure);
    CHECK(near(gpu::gradeAt(l, mid + 1e-4, -1, 0).grade.exposure, e, 1e-3f));
}

TEST_CASE("gpu: regions mix by weight") {
    gpu::GradeAt a = gpu::gradeAt(gpu::homeLook(), 0.2, -1, 0);
    gpu::GradeAt acc = gpu::scaled(a, 0.25f);
    gpu::accumulate(acc, a, 0.75f);
    CHECK(near(acc.grade.exposure, a.grade.exposure));
    CHECK(near(acc.sky[0].b, a.sky[0].b));
}

TEST_CASE("gpu: one wind leans everything downwind, gusts travel, never against the wind") {
    const Vec2 dir{1, 0};
    float lo = 10;
    float hi = -10;
    for (int i = 0; i < 400; ++i) {
        const float v = gpu::windLean({static_cast<float>(i) * 37.0f, 11.0f}, i * 0.05, dir, 1);
        lo = std::min(lo, v);
        hi = std::max(hi, v);
    }
    CHECK(lo >= 0.0f);
    CHECK(hi <= 1.0f + gpu::tuning::kGustGain + 1e-3f);
    CHECK(hi > 1.0f); // gust crests pass
    // Calm air barely stirs; motion is continuous frame to frame.
    CHECK(gpu::windLean({100, 100}, 3.0, dir, 0.0f) == doctest::Approx(0.0f));
    const float a = gpu::windLean({500, 300}, 10.0, dir, 0.6f);
    const float b = gpu::windLean({500, 300}, 10.0 + 1.0 / 120.0, dir, 0.6f);
    CHECK(std::abs(a - b) < 0.05f);
}

TEST_CASE("gpu: flicker stays within its depth and differs light to light") {
    for (const gpu::Flicker f :
         {gpu::Flicker::Steady, gpu::Flicker::Gutter, gpu::Flicker::Breathe, gpu::Flicker::Leap}) {
        float lo = 2;
        float hi = -1;
        for (int i = 0; i < 600; ++i) {
            const float v = gpu::flicker(f, 4, 8, 0.08f, 1234, i / 60.0);
            lo = std::min(lo, v);
            hi = std::max(hi, v);
        }
        CHECK(lo >= 1.0f - 0.08f - 1e-4f);
        CHECK(hi <= 1.0f + 1e-4f);
        CHECK(hi - lo > 0.005f); // it moves
    }
    CHECK(gpu::flicker(gpu::Flicker::Leap, 4, 8, 0.08f, 1, 2.0) !=
          gpu::flicker(gpu::Flicker::Leap, 4, 8, 0.08f, 2, 2.0));
}

TEST_CASE("lights: profiles read the world data's shape; hours run past midnight and fade") {
    const LightProfile p = parseLightProfile("door_lamp", nlohmann::json::parse(R"({
        "kind": "door", "kelvin": 1900, "colour": "#ff8c3c", "radius": 2.2, "strength": 0.7,
        "flicker": {"style": "gutter", "hz": [4, 7], "depth": 0.5},
        "hours": [["dusk", "01:30"]], "rain": "dim"})"));
    CHECK(p.kind == "door");
    CHECK(near(p.colour.r, 1.0f));
    CHECK(near(p.colour.g, 140.0f / 255.0f));
    CHECK(near(p.radius, 2.2f));
    CHECK(p.flicker == gpu::Flicker::Gutter);
    CHECK(near(p.depth, 0.08f)); // never across a ramp step (quality bar §4.3)
    CHECK(p.rain == LightRain::Dim);
    CHECK(p.staggered);
    REQUIRE(p.hours.size() == 1);
    CHECK(near(p.hours[0].first, gpu::tuning::kDuskHour));
    // Out at noon, burning at midnight (past midnight), out again by dawn.
    CHECK(hoursOn(p, 12.0f, 7) == 0.0f);
    CHECK(hoursOn(p, 0.0f, 7) == 1.0f);
    CHECK(hoursOn(p, 4.0f, 7) == 0.0f);
    // Windows and doors light one by one after the hour, each fading in.
    int lit = 0;
    for (std::uint32_t seed = 0; seed < 100; ++seed)
        if (hoursOn(p, gpu::tuning::kDuskHour + 0.6f, seed) > 0) ++lit;
    CHECK(lit > 10);
    CHECK(lit < 90);
    const LightProfile only = parseLightProfile(
        "tapers", nlohmann::json::parse(R"({"kind": "window", "hours": [["dusk", "dawn"]],
                                            "only": "saturnalia"})"));
    CHECK(only.festivalOnly);
    CHECK(only.only == "saturnalia");
    const LightProfile altar = parseLightProfile(
        "altar", nlohmann::json::parse(R"({"kind": "altar", "hours": [["dusk", "dawn"]],
                                           "festivals": {"*": 2.0, "parilia": 1.5}})"));
    REQUIRE(altar.festivals.size() == 2);
    CHECK_FALSE(altar.festivalOnly);
}

TEST_CASE("lights: every light point of the committed world names its item") {
    // (The render tests' session may be up already: SDL counts its subsystems.)
    REQUIRE(SDL_SetHintWithPriority(SDL_HINT_VIDEO_DRIVER, "dummy", SDL_HINT_OVERRIDE));
    REQUIRE(SDL_InitSubSystem(SDL_INIT_VIDEO));
    {
        const WindowPtr window{SDL_CreateWindow("lights test", 64, 64, 0)};
        REQUIRE(window);
        const RendererPtr renderer{SDL_CreateRenderer(window.get(), "software")};
        REQUIRE(renderer);
        auto cat = loadCatalog(std::filesystem::path(LC_WORLDVIEW_ASSETS_DIR) / "catalog.json");
        REQUIRE(cat);
        auto world = world::loadWorld(LC_WORLDVIEW_ASSETS_DIR, *cat);
        REQUIRE(world);
        Atlas atlas(renderer.get(), LC_WORLDVIEW_ASSETS_DIR, cat->iso());
        WorldView view(renderer.get(), *world, LC_WORLDVIEW_ASSETS_DIR, atlas, false);
        // The software renderer has no shader path: the classic look, said once.
        CHECK(view.setQuality(gpu::Quality::High) == gpu::Quality::Classic);
        CHECK(view.quality() == gpu::Quality::Classic);
        std::size_t points = 0;
        for (const world::RegionFile& rf : world->regions)
            if (rf.life.is_object() && rf.life.contains("light_points"))
                points += rf.life.at("light_points").size();
        WorldLights l(*world, view.sprites(), {});
        CHECK(l.unmatched() == 0);
        CHECK(l.count() == points);
        CHECK(points > 1000);
        // At 22:00 some burn and every colour stays a warm flame's.
        l.update(hourAt(22.0), 100.0, nullptr);
        int burning = 0;
        l.forEach(
            world->map->bounds(), [](Vec2) { return 0.0f; },
            [&](const WorldLight&, Rgb c, float radius) {
                ++burning;
                CHECK(c.r >= c.g);
                CHECK(c.g >= c.b);
                CHECK(radius > 0.0f);
            });
        CHECK(burning > 200);
        // At noon almost nothing (glass furnaces and forges may burn).
        l.update(hourAt(12.0), 100.0, nullptr);
        int noon = 0;
        l.forEach(
            world->map->bounds(), [](Vec2) { return 0.0f; },
            [&](const WorldLight&, Rgb, float) { ++noon; });
        CHECK(noon < burning / 4);
        // Roles name what they carry by profile id, per region; unknown ids are none.
        bool carried = false;
        for (std::size_t r = 0; r < world->regions.size(); ++r)
            if (l.profileOf(static_cast<int>(r), "carried_torch") >= 0) carried = true;
        CHECK(carried);
        CHECK(l.profileOf(0, "no such light") == -1);
    }
    SDL_QuitSubSystem(SDL_INIT_VIDEO);
}

TEST_CASE(
    "gpu: water takes the region's colour: deeper offshore, turquoise shallows, greyer winter") {
    const Rgb body{0.12f, 0.37f, 0.55f}; // an Aegean blue
    const auto chroma = [](Rgb c) { return std::max({c.r, c.g, c.b}) - std::min({c.r, c.g, c.b}); };
    const auto luma = [](Rgb c) { return 0.299f * c.r + 0.587f * c.g + 0.114f * c.b; };
    const gpu::WaterColours summer = gpu::waterColours(body, 1);
    CHECK(luma(summer.deep) < luma(body));
    CHECK(chroma(summer.deep) > 0.3f); // offshore stays a clear blue, never slate
    CHECK(summer.deep.b > summer.deep.g);
    CHECK(summer.shallow.g / summer.shallow.b > body.g / body.b); // the shallows lean green
    CHECK(luma(summer.shallow) > luma(body));
    CHECK(summer.river.g / summer.river.b > summer.deep.g / summer.deep.b); // rivers greener
    const gpu::WaterColours winter = gpu::waterColours(body, 3);
    CHECK(chroma(winter.deep) < chroma(summer.deep));
    CHECK(chroma(winter.shallow) < chroma(summer.shallow));
    const gpu::WaterColours none = gpu::waterColours(body, -1);
    CHECK(near(none.deep.b, summer.deep.b)); // summer adds no grey
}

TEST_CASE("gpu: seasons: a climate's month swaps green ramps; snow builds and thaws by its line") {
    const nlohmann::json ramps = nlohmann::json::parse(R"({"ramps": [
        {"id": 1, "class": "foliage_deciduous", "steps": 7,
         "states": {"fresh": 159, "dry": 160, "turn": 162}},
        {"id": 28, "class": "grass", "steps": 6,
         "states": {"fresh": 163, "dry": 164, "dormant": 165, "turn": 186}},
        {"id": 7, "class": "stone", "steps": 6},
        {"id": 40, "class": "snow", "steps": 5}, {"id": 115, "class": "snow", "steps": 3}]})");
    const gpu::RampSeasons r = gpu::parseRamps(ramps);
    CHECK(r.snow == 40); // the widest snow ramp
    ClimateDef c;
    c.snowLine = {-1, -1, -1, -1, -1, -1, -1, -1, -1, 4, 4, 4}; // snow from December, level 4
    using G = GreenState;
    c.greens[0] = {G::Fresh, G::Fresh, G::Fresh, G::Green,   G::Dry,     G::Dry,
                   G::Dry,   G::Green, G::Green, G::Dormant, G::Dormant, G::Dormant};
    c.greens[1] = {G::Bare,  G::Fresh, G::Green, G::Green, G::Green, G::Green,
                   G::Green, G::Turn,  G::Turn,  G::Bare,  G::Bare,  G::Bare};
    std::array<std::uint8_t, gpu::kRampIds> row{};
    gpu::remapRow(r, c, 0, row); // March: fresh grass, leafless trees
    CHECK(row[28] == 163);
    CHECK(row[1] == 160);        // no dormant leaves: the dry state
    CHECK(row[7] == 7);          // stone is stone all year
    gpu::remapRow(r, c, 3, row); // June: plain green
    CHECK(row[28] == 28);
    CHECK(row[1] == 1);
    gpu::remapRow(r, c, 7, row); // October: the trees turn
    CHECK(row[1] == 162);
    gpu::remapRow(r, c, 9, row); // December: dormant grass
    CHECK(row[28] == 165);
    // Snow: none below the line, half on it, all above; it builds over December's first morning
    // and thaws over March's.
    CHECK(gpu::snowCover(c, 9, 0.5f, 3) == 0.0f);
    CHECK(gpu::snowCover(c, 9, 0.5f, 4) == 0.5f);
    CHECK(gpu::snowCover(c, 9, 0.5f, 6) == 1.0f);
    CHECK(gpu::snowCover(c, 9, 0.0f, 6) == 0.0f); // December's dawn: none yet
    const float building = gpu::snowCover(c, 9, 0.2f, 6);
    CHECK(building > 0.0f);
    CHECK(building < 1.0f);
    CHECK(gpu::snowCover(c, 10, 0.0f, 6) == 1.0f); // January: lying all day
    CHECK(gpu::snowCover(c, 0, 0.0f, 6) == 1.0f);  // March's dawn: still there
    CHECK(gpu::snowCover(c, 0, 0.5f, 6) == 0.0f);  // ... gone by midday
}

TEST_CASE("gpu: seasons: ramps follow their class's words; missing states keep today's look") {
    // The real table's shapes (QA7 V7-001): the leaf ramp with no dormant or bare state, the
    // blossom ramp with no states, `pal.leaf` classed as grass; then the same once the art gives
    // a bare state, blossom states that follow the early bloom, and `pal.leaf` the deciduous.
    const auto parse = [](const char* text) {
        return gpu::parseRamps(nlohmann::json::parse(text));
    };
    const gpu::RampSeasons today = parse(R"({"ramps": [
        {"id": 1, "class": "foliage_deciduous", "states": {"fresh": 159, "dry": 160, "turn": 162}},
        {"id": 3, "class": "foliage_deciduous"},
        {"id": 103, "class": "grass", "states": {"fresh": 175, "dry": 176, "dormant": 177}}]})");
    const gpu::RampSeasons art = parse(R"({"ramps": [
        {"id": 1, "class": "foliage_deciduous",
         "states": {"fresh": 159, "dry": 160, "turn": 162, "bare": 170}},
        {"id": 3, "class": "foliage_deciduous", "follows": "early_bloom",
         "states": {"fresh": 159, "green": 1, "turn": 162, "dormant": 160}},
        {"id": 103, "class": "grass", "follows": "deciduous",
         "states": {"fresh": 175, "dry": 176, "dormant": 177}}]})");
    ClimateDef c; // med_green's grass, deciduous and early bloom, March to February
    using G = GreenState;
    const auto at = [](GreenClass k) { return static_cast<std::size_t>(k); };
    c.greens[at(GreenClass::Grass)] = {G::Fresh, G::Fresh, G::Fresh, G::Green, G::Dry,   G::Dry,
                                       G::Dry,   G::Green, G::Green, G::Green, G::Green, G::Green};
    c.greens[at(GreenClass::Deciduous)] = {G::Bare,  G::Fresh, G::Green, G::Green,
                                           G::Green, G::Green, G::Green, G::Green,
                                           G::Turn,  G::Bare,  G::Bare,  G::Bare};
    c.greens[at(GreenClass::EarlyBloom)] = {G::Bloom, G::Fresh, G::Green, G::Green,
                                            G::Green, G::Green, G::Green, G::Green,
                                            G::Turn,  G::Bare,  G::Bare,  G::Bloom};
    std::array<std::uint8_t, gpu::kRampIds> row{};
    constexpr int kDecember = 9;
    constexpr int kJuly = 4;
    constexpr int kFebruary = 11;
    gpu::remapRow(today, c, kDecember, row);
    CHECK(row[1] == 160);   // leafless falls to dry, as before
    CHECK(row[3] == 3);     // blossom as drawn
    CHECK(row[103] == 103); // green grass in December
    gpu::remapRow(art, c, kDecember, row);
    CHECK(row[1] == 170);   // bare
    CHECK(row[3] == 160);   // the early bloom's bare: dormant, as it has no bare
    CHECK(row[103] == 177); // leaves now follow the trees: dormant
    gpu::remapRow(art, c, kJuly, row);
    CHECK(row[3] == 1); // leaves, not blossom, in summer
    gpu::remapRow(art, c, kFebruary, row);
    CHECK(row[3] == 3); // in bloom: as drawn
}

TEST_CASE("gpu: seasons over the land: built ground takes the land's level; climates blend") {
    // A 12 x 1 strip: climate 0 on the left half, 1 on the right; a paved platform (levels 6)
    // on natural ground at level 2.
    constexpr int w = 12;
    std::vector<std::uint8_t> climate(w, 0);
    std::vector<std::uint8_t> level(w, 2);
    std::vector<std::uint8_t> natural(w, 1);
    for (int x = 6; x < w; ++x) climate[static_cast<std::size_t>(x)] = 1;
    for (int x = 2; x < 5; ++x) {
        level[static_cast<std::size_t>(x)] = 6;
        natural[static_cast<std::size_t>(x)] = 0;
    }
    const std::vector<gpu::SeasonTile> f = gpu::seasonField(w, 1, climate, level, natural);
    CHECK(f[3].landLevel == 2); // the platform's snow is the land's, not its top's
    CHECK(f[0].landLevel == 2);
    CHECK(f[5].other == 1); // beside the border: the other climate, at distance 0
    CHECK(f[5].distance == 0);
    CHECK(f[0].other == 1);
    CHECK(f[0].distance == 5);
    CHECK(f[6].other == 0);
    // Half at the border, less further in, none past the band.
    CHECK(gpu::otherShare(0, 0) == doctest::Approx(0.5f));
    CHECK(gpu::otherShare(5, 0) < 0.5f);
    CHECK(gpu::otherShare(5, 0) > 0.0f);
    CHECK(gpu::otherShare(gpu::kSeasonBand, 0) == 0.0f);
}

TEST_CASE("gpu: the sun rises, stands highest at noon in the baked sun's direction, sets") {
    const auto deg = [](float r) { return r * 180.0f / std::numbers::pi_v<float>; };
    const gpu::Sun noon = gpu::sunAt(0.25, 1); // 12:00, summer
    CHECK(deg(noon.elevation) > 60.0f);
    CHECK(noon.strength == doctest::Approx(1.0f));
    // At noon it shines from the art's baked direction (its shadows are the baked ones).
    const float az = std::atan2(noon.dir[1], noon.dir[0]);
    CHECK(az == doctest::Approx(std::atan2(gpu::kBakedSun[1], gpu::kBakedSun[0])).epsilon(0.01));
    const gpu::Sun morning = gpu::sunAt(0.0625, 1); // 07:30
    const gpu::Sun evening = gpu::sunAt(0.4375, 1); // 16:30
    CHECK(morning.elevation < noon.elevation);
    CHECK(morning.elevation == doctest::Approx(evening.elevation).epsilon(0.01));
    // Morning and evening light come from opposite sides of the noon direction.
    CHECK(morning.dir[0] * evening.dir[1] - morning.dir[1] * evening.dir[0] != doctest::Approx(0));
    CHECK(gpu::sunAt(0.75, 1).strength == 0.0f);           // midnight
    CHECK(gpu::sunAt(0.25, 3).elevation < noon.elevation); // winter's noon is lower
    // Shadows: near the baked ones at noon, longer when the sun is low, never past the limit.
    const gpu::ShadowWarp wn = gpu::shadowWarp(noon);
    CHECK(wn.m[0] == doctest::Approx(1.0f).epsilon(0.15));
    const gpu::ShadowWarp we = gpu::shadowWarp(gpu::sunAt(0.47, 1));
    const float stretch = std::hypot(we.m[0] * wn.along[0] + we.m[1] * wn.along[1],
                                     we.m[2] * wn.along[0] + we.m[3] * wn.along[1]);
    CHECK(stretch > 1.5f);
    CHECK(stretch <= gpu::tuning::kShadowLongest + 1e-3f);
}
