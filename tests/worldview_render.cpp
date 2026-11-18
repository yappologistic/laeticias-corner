// The world renderer on the committed world, headless with the software renderer: gathering finds
// every piece and orders them, cached cells leave no seams, impostors match the full-detail view
// at their scale, and missing art is drawn and counted.

#include "core/catalog.hpp"
#include "life/data.hpp"
#include "render/atlas.hpp"
#include "ui/font.hpp"
#include "world/loader.hpp"
#include "worldview/city_sound.hpp"
#include "worldview/gather.hpp"
#include "worldview/renderer.hpp"
#include "worldview/soundscape.hpp"
#include "worldview/weather_field.hpp"

#include <doctest.h>

#include <cmath>
#include <memory>
#include <optional>
#include <set>

using namespace lc;
using namespace lc::worldview;

namespace {

constexpr int kW = 640;
constexpr int kH = 400;

// One SDL session, window and software renderer, the world and its renderer, for the whole run.
struct Rig {
    bool ok = false;
    WindowPtr window;
    RendererPtr renderer;
    Catalog cat;
    std::optional<world::LoadedWorld> world;
    std::unique_ptr<Atlas> atlas;
    Font font;
    std::unique_ptr<WorldView> view;
    TexturePtr target;

    Rig() {
        if (!SDL_SetHintWithPriority(SDL_HINT_VIDEO_DRIVER, "dummy", SDL_HINT_OVERRIDE) ||
            !SDL_Init(SDL_INIT_VIDEO))
            return;
        window.reset(SDL_CreateWindow("worldview test", kW, kH, 0));
        if (window) renderer.reset(SDL_CreateRenderer(window.get(), "software"));
        auto c = loadCatalog(std::filesystem::path(LC_WORLDVIEW_ASSETS_DIR) / "catalog.json");
        if (!renderer || !c) return;
        cat = std::move(*c);
        auto w = world::loadWorld(LC_WORLDVIEW_ASSETS_DIR, cat);
        if (!w) return;
        world.emplace(std::move(*w));
        atlas = std::make_unique<Atlas>(renderer.get(), LC_WORLDVIEW_ASSETS_DIR, cat.iso());
        if (!font.load(std::filesystem::path(LC_WORLDVIEW_ASSETS_DIR) / "fonts") ||
            !font.build(renderer.get(), 1.0f))
            return;
        view = std::make_unique<WorldView>(renderer.get(), *world, LC_WORLDVIEW_ASSETS_DIR, *atlas,
                                           false);
        target.reset(
            SDL_CreateTexture(renderer.get(), kTextureFormat, SDL_TEXTUREACCESS_TARGET, kW, kH));
        ok = target != nullptr;
    }
    ~Rig() {
        view.reset();
        target.reset();
        atlas.reset();
        renderer.reset();
        window.reset();
        SDL_Quit();
    }
    Rig(const Rig&) = delete;
    Rig& operator=(const Rig&) = delete;

    [[nodiscard]] WorldCamera camera(Vec2 tile, int level) const {
        WorldCamera cam(cat.iso(), world->map->width(), world->map->height(), 240);
        cam.setScreen({kW, kH});
        cam.setLevel(level);
        cam.lookAtTile(tile);
        return cam;
    }

    // The frame for `cam`, RGBA.
    SurfacePtr frame(const WorldCamera& cam) {
        if (!SDL_SetRenderTarget(renderer.get(), target.get())) return {};
        view->draw(cam, phaseCentre(Phase::Day), 0, 0);
        SurfacePtr px{SDL_RenderReadPixels(renderer.get(), nullptr)};
        (void)SDL_SetRenderTarget(renderer.get(), nullptr);
        return px ? SurfacePtr{SDL_ConvertSurface(px.get(), SDL_PIXELFORMAT_RGBA32)} : SurfacePtr{};
    }
};

Rig& rig() {
    static Rig r;
    return r;
}

const std::uint8_t* pixel(const SDL_Surface* s, int x, int y) {
    return static_cast<const std::uint8_t*>(s->pixels) + static_cast<std::ptrdiff_t>(y) * s->pitch +
           static_cast<std::ptrdiff_t>(x) * 4;
}

} // namespace

TEST_CASE("render: the gathered elements of the Parsa terrace are complete and in order") {
    Rig& r = rig();
    REQUIRE(r.ok);
    const world::WorldMap& m = *r.world->map;
    const Iso iso = r.cat.iso();
    Gatherer g(m, r.view->sprites());
    const Vec2 c = iso.toWorld(374, 58);
    const FRect clip{c.x - 900, c.y - 600, c.x + 900, c.y + 600};
    Gathered tight;
    g.run(gatherTiles(clip, r.view->sprites().itemSpan(), iso), clip, tight);
    Gathered wide;
    const TileRect around = tilesUnder(clip, iso);
    g.run({around.x0 - 60, around.y0 - 60, around.x1 + 60, around.y1 + 60}, clip, wide);
    // The tight span finds everything a much wider search does.
    REQUIRE(tight.elems.size() > 200);
    CHECK(tight.elems.size() == wide.elems.size());
    // Every split landmark found has all its pieces that meet the clip, once each.
    std::set<std::pair<std::uint32_t, int>> seen;
    int pieces = 0;
    for (const Elem& e : tight.elems)
        if (!e.ground) {
            CHECK(seen.emplace(e.item, e.piece).second);
            pieces += e.piece >= 0 ? 1 : 0;
        }
    CHECK(pieces > 50);
    // Painter's order holds for every overlapping pair.
    std::vector<std::size_t> at(tight.elems.size());
    for (std::size_t k = 0; k < tight.order.size(); ++k) at[tight.order[k]] = k;
    int bad = 0;
    for (std::size_t i = 0; i < tight.items.size(); ++i)
        for (std::size_t j = i + 1; j < tight.items.size(); ++j)
            if (tight.items[i].screen.overlaps(tight.items[j].screen) &&
                drawnBefore(tight.items[i], tight.items[j]) != (at[i] < at[j]))
                ++bad;
    CHECK(bad == 0);
}

TEST_CASE("render: cached cells and the live layer leave no seams as the view moves") {
    Rig& r = rig();
    REQUIRE(r.ok);
    // The same place drawn twice, the second time moved by a whole number of pixels: cell
    // boundaries cross the frame elsewhere, the overlap must match exactly.
    for (const Vec2 tile : {Vec2{374, 58}, Vec2{313, 615}}) {
        WorldCamera a = r.camera(tile, 3);
        WorldCamera b = a;
        b.panBy({173, 91});
        const SurfacePtr pa = r.frame(a);
        const SurfacePtr pb = r.frame(b);
        REQUIRE(pa);
        REQUIRE(pb);
        long differ = 0;
        for (int y = 0; y < kH - 91; ++y)
            for (int x = 0; x < kW - 173; ++x)
                if (std::memcmp(pixel(pa.get(), x + 173, y + 91), pixel(pb.get(), x, y), 4) != 0)
                    ++differ;
        CHECK(differ == 0);
    }
}

TEST_CASE("render: impostors match the full-detail view at their scale") {
    Rig& r = rig();
    REQUIRE(r.ok);
    const Vec2 tile{262, 672}; // the Athenian Agora
    const SurfacePtr full = r.frame(r.camera(tile, 3));
    const SurfacePtr half = r.frame(r.camera(tile, 2));
    REQUIRE(full);
    REQUIRE(half);
    // The middle of the half-scale frame against the full frame averaged 2 x 2.
    double diff = 0;
    long n = 0;
    for (int y = kH / 4 + 8; y < kH * 3 / 4 - 8; ++y)
        for (int x = kW / 4 + 8; x < kW * 3 / 4 - 8; ++x) {
            const int fx = (x - kW / 4) * 2;
            const int fy = (y - kH / 4) * 2;
            for (int ch = 0; ch < 3; ++ch) {
                double avg = 0;
                for (int dy = 0; dy < 2; ++dy)
                    for (int dx = 0; dx < 2; ++dx) avg += pixel(full.get(), fx + dx, fy + dy)[ch];
                diff += std::abs(avg / 4 - pixel(half.get(), x, y)[ch]);
                ++n;
            }
        }
    MESSAGE("mean difference " << diff / static_cast<double>(n));
    CHECK(diff / static_cast<double>(n) < 2.0);
}

TEST_CASE("render: missing art is drawn as placeholders or stand-ins and counted") {
    Rig& r = rig();
    REQUIRE(r.ok);
    const WorldSprites& s = r.view->sprites();
    // What has no art yet is listed with how often it is placed, and the placeholders add up.
    int placeholders = 0;
    for (const MissingArt& m : s.missingItems()) {
        CHECK(m.count > 0);
        CHECK(m.look != Look::Art);
        if (m.look == Look::Placeholder) placeholders += m.count;
    }
    CHECK(placeholders == s.placeholdersPlaced());
    // Every placed item resolves to something drawable.
    for (const world::Placed& it : r.world->map->items()) {
        const VariantLook& look = s.item(it);
        CHECK((!look.base.empty() || !look.pieces.empty()));
    }
}

TEST_CASE("sound: beds, zones and music follow the view; a city's piece starts on a phrase") {
    Rig& r = rig();
    REQUIRE(r.ok);
    const world::LoadedWorld& w = *r.world;
    Soundscape s(w, std::filesystem::path(LC_WORLDVIEW_ASSETS_DIR) / "audio");
    const auto file = [&](std::string_view f) {
        const auto it = std::ranges::find(s.files(), f);
        REQUIRE(it != s.files().end());
        return static_cast<std::size_t>(it - s.files().begin());
    };
    std::vector<float> weights(w.file.regions.size(), 0.0f);
    const auto at = [&](std::string_view region, Vec2 centre, double clock, float seconds) {
        std::ranges::fill(weights, 0.0f);
        weights[static_cast<std::size_t>(w.file.findRegion(region))] = 1.0f;
        bool seek = false;
        for (float t = 0; t < seconds; t += 0.1f) {
            s.update({weights, centre, 16, clock, 0, 0.1f});
            seek = seek || !s.seeks().empty();
        }
        return seek;
    };
    const int rome = w.file.findRegion("rome");
    // At home: the home's own music, no city's.
    (void)at("corner", {60, 1220}, 0.2, 1);
    CHECK(s.musicRegion() == w.file.home.region);
    CHECK(s.homeMusic() == doctest::Approx(1));
    // Into the Forum by day: Rome's piece starts on a phrase and fades in over four seconds; the
    // day bed and the forum zone play; the home's music fades out.
    CHECK(at("rome", {80, 1077}, 0.2, 0.2f));
    CHECK(s.musicRegion() == rome);
    CHECK(s.out()[file("music/rome/day.ogg")].gain < 0.2f);
    (void)at("rome", {80, 1077}, 0.2, 5);
    CHECK(s.out()[file("music/rome/day.ogg")].gain > 0.4f);
    CHECK(s.out()[file("music/rome/night.ogg")].gain == doctest::Approx(0));
    CHECK(s.out()[file("amb/rome/day.ogg")].gain > 0.2f);
    CHECK(s.out()[file("amb/rome/forum.ogg")].gain > 0.2f);
    CHECK(s.homeMusic() == doctest::Approx(0));
    // Far from the forum its zone is silent.
    (void)at("rome", {140, 1130}, 0.2, 1);
    CHECK(s.out()[file("amb/rome/forum.ogg")].gain == doctest::Approx(0));
    // Out into a stretch: no music after the fade, the stretch's bed.
    CHECK_FALSE(at("latium_italy", {150, 1150}, 0.2, 5));
    CHECK(s.musicRegion() == -1);
    CHECK(s.out()[file("music/rome/day.ogg")].gain == doctest::Approx(0));
    CHECK(s.out()[file("amb/world/fields.ogg")].gain > 0.2f);
    // Back again: a phrase start again.
    CHECK(at("rome", {80, 1077}, 0.2, 0.5f));
}

TEST_CASE("sound: a bed the view stands in surrounds it; loops sound from all their sources") {
    // L-113: zones were panned toward their centre and loops toward their nearest source, so a
    // resting view heard beds from one side.
    const TileRect zone{0, 0, 100, 100};
    CHECK(std::abs(zonePan(zone, {50, 50}, 15)) < 0.05f);
    CHECK(std::abs(zonePan(zone, {2, 97}, 15)) < 0.05f);
    // Outside, it comes from the side it lies on, and mirrored places hear it mirrored.
    const float right = zonePan(zone, {110, 50}, 15);
    CHECK(std::abs(right) > 0.1f);
    CHECK(zonePan(zone, {50, 110}, 15) == doctest::Approx(-right));
    // Two sources of one loop either side of the view and none other in reach: from the middle.
    Rig& r = rig();
    REQUIRE(r.ok);
    const world::LoadedWorld& w = *r.world;
    Soundscape s(w, std::filesystem::path(LC_WORLDVIEW_ASSETS_DIR) / "audio");
    std::vector<float> weights(w.file.regions.size(), 0.0f);
    bool tested = false;
    for (const world::RegionFile& rf : w.regions) {
        for (const world::ItemLoop& l : rf.theme.loops) {
            const int item = w.content->findItem(l.item);
            if (item < 0 || l.when != "always" || tested) continue;
            std::vector<Vec2> at;
            for (const world::Placed& it : w.map->items())
                if (static_cast<int>(it.info) == item)
                    at.push_back({static_cast<float>(it.x) + static_cast<float>(it.w) * 0.5f,
                                  static_cast<float>(it.y) + static_cast<float>(it.h) * 0.5f});
            for (std::size_t a = 0; a < at.size() && !tested; ++a)
                for (std::size_t b = a + 1; b < at.size() && !tested; ++b) {
                    const Vec2 mid{(at[a].x + at[b].x) * 0.5f, (at[a].y + at[b].y) * 0.5f};
                    const float lean = (at[a].x - mid.x) - (at[a].y - mid.y);
                    if (std::hypot(at[a].x - mid.x, at[a].y - mid.y) > 8 || std::abs(lean) < 2)
                        continue;
                    // Nothing else playing this file near the middle.
                    bool alone = true;
                    for (const world::RegionFile& rg : w.regions)
                        for (const world::ItemLoop& o : rg.theme.loops)
                            if (o.file == l.file)
                                for (const world::Placed& it : w.map->items())
                                    if (static_cast<int>(it.info) == w.content->findItem(o.item)) {
                                        const Vec2 p{static_cast<float>(it.x) +
                                                         static_cast<float>(it.w) * 0.5f,
                                                     static_cast<float>(it.y) +
                                                         static_cast<float>(it.h) * 0.5f};
                                        const bool pair = (p.x == at[a].x && p.y == at[a].y) ||
                                                          (p.x == at[b].x && p.y == at[b].y);
                                        if (!pair && std::hypot(p.x - mid.x, p.y - mid.y) < 15)
                                            alone = false;
                                    }
                    if (!alone) continue;
                    s.update({weights, mid, 15, 0.2, 0, 0.5f});
                    const auto f = static_cast<std::size_t>(std::ranges::find(s.files(), l.file) -
                                                            s.files().begin());
                    MESSAGE(l.file << " between " << at[a].x << "," << at[a].y << " and " << at[b].x
                                   << "," << at[b].y);
                    CHECK(s.out()[f].gain > 0);
                    CHECK(std::abs(s.out()[f].pan) < 0.05f);
                    tested = true;
                }
        }
    }
    CHECK(tested);
}

TEST_CASE("sound: every region has a bed in every month, by day and night; a season's own beds "
          "replace the plain ones") {
    Rig& r = rig();
    REQUIRE(r.ok);
    const world::LoadedWorld& w = *r.world;
    const std::filesystem::path audio = std::filesystem::path(LC_WORLDVIEW_ASSETS_DIR) / "audio";
    Soundscape s(w, audio);
    const Catalog& cat = w.content->home();
    const auto season = [&](std::string_view id) {
        return static_cast<int>(std::ranges::find(cat.seasons, id, &SeasonDef::id) -
                                cat.seasons.begin());
    };
    const auto month = [&](std::string_view id) {
        return static_cast<int>(std::ranges::find(cat.months, id) - cat.months.begin());
    };
    REQUIRE(cat.months.size() == 12);
    int m = 0;
    for (std::size_t k = 0; k < cat.seasons.size(); ++k)
        for (int d = 0; d < cat.seasonDays[k]; ++d, ++m)
            for (const float hour : {12.0f, 0.0f})
                for (std::size_t g = 0; g < w.file.regions.size(); ++g) {
                    const auto beds =
                        s.bedsOf(static_cast<int>(g), static_cast<int>(k), m, hour, false);
                    CHECK_MESSAGE(!beds.empty(),
                                  w.file.regions[g].id << " " << cat.seasons[k].id << " " << hour);
                    for (const std::string& f : beds)
                        CHECK_MESSAGE(std::filesystem::exists(audio / f), f);
                }
    const int rome = w.file.findRegion("rome");
    const int parsa = w.file.findRegion("parsa");
    using Files = std::vector<std::string>;
    CHECK(s.bedsOf(rome, season("spring"), month("mar"), 12, false) == Files{"amb/rome/day.ogg"});
    CHECK(s.bedsOf(rome, season("winter"), month("dec"), 12, false) ==
          Files{"amb/rome/day_winter.ogg"});
    CHECK(s.bedsOf(rome, season("winter"), month("jan"), 0, false) == Files{"amb/rome/night.ogg"});
    // A season's beds for some of its months only: the plain ones in the others.
    CHECK(s.bedsOf(parsa, season("autumn"), month("sep"), 12, false) ==
          Files{"amb/parsa/plain_day_summer.ogg"});
    CHECK(s.bedsOf(parsa, season("autumn"), month("oct"), 12, false) ==
          Files{"amb/parsa/plain_day.ogg"});
    CHECK(s.bedsOf(parsa, season("autumn"), month("nov"), 12, false) ==
          Files{"amb/parsa/plain_day_winter.ogg"});
    // Pārsa's rain bed only under rain (it played all day in dry weather).
    CHECK(s.bedsOf(parsa, season("spring"), month("apr"), 12, false) ==
          Files{"amb/parsa/plain_day.ogg"});
    CHECK(s.bedsOf(parsa, season("spring"), month("apr"), 12, true) ==
          Files{"amb/parsa/plain_day.ogg", "amb/parsa/rain.ogg"});
}

TEST_CASE("sound: a season's turn crossfades its beds with equal power, never a jump") {
    Rig& r = rig();
    REQUIRE(r.ok);
    const world::LoadedWorld& w = *r.world;
    Soundscape s(w, std::filesystem::path(LC_WORLDVIEW_ASSETS_DIR) / "audio");
    const Catalog& cat = w.content->home();
    const auto index = [&](std::string_view f) {
        return static_cast<std::size_t>(std::ranges::find(s.files(), f) - s.files().begin());
    };
    const std::size_t plain = index("amb/rome/day.ogg");
    const std::size_t winter = index("amb/rome/day_winter.ogg");
    REQUIRE(winter < s.files().size());
    std::vector<float> weights(w.file.regions.size(), 0.0f);
    weights[static_cast<std::size_t>(w.file.findRegion("rome"))] = 1.0f;
    const auto seasonOf = [&](std::string_view id) {
        return static_cast<int>(std::ranges::find(cat.seasons, id, &SeasonDef::id) -
                                cat.seasons.begin());
    };
    Soundscape::Input in{weights, {130, 1140}, 16, 0.2, 0, 0.1f};
    in.season = seasonOf("autumn");
    in.month = 8; // November
    for (int i = 0; i < 10; ++i) s.update(in);
    const float a0 = s.out()[plain].gain;
    REQUIRE(a0 > 0);
    CHECK(s.out()[winter].gain == doctest::Approx(0));
    in.season = seasonOf("winter");
    in.month = 9; // December
    std::vector<std::pair<float, float>> trace;
    for (int i = 0; i < 300; ++i) {
        s.update(in);
        trace.emplace_back(s.out()[plain].gain, s.out()[winter].gain);
    }
    const float b1 = trace.back().second;
    REQUIRE(b1 > 0);
    CHECK(trace.back().first == doctest::Approx(0));
    float prevA = a0;
    float prevB = 0;
    for (const auto& [a, b] : trace) {
        const float power = (a / a0) * (a / a0) + (b / b1) * (b / b1);
        CHECK(power == doctest::Approx(1.0f).epsilon(0.05));
        CHECK(std::abs(a - prevA) < 0.03f);
        CHECK(std::abs(b - prevB) < 0.03f);
        prevA = a;
        prevB = b;
    }
}

TEST_CASE("sound: nature beds of the season and of snow lying, on every land region") {
    Rig& r = rig();
    REQUIRE(r.ok);
    const world::LoadedWorld& w = *r.world;
    const Catalog& cat = w.content->home();
    life::LifeData data;
    for (const SeasonDef& sd : cat.seasons) data.seasons.push_back(sd.id);
    data.months = cat.months;
    const CitySound cs(w, data, std::filesystem::path(LC_WORLDVIEW_ASSETS_DIR) / "audio", 1);
    const auto season = [&](std::string_view id) {
        return static_cast<int>(std::ranges::find(cat.seasons, id, &SeasonDef::id) -
                                cat.seasons.begin());
    };
    const int rome = w.file.findRegion("rome");
    CHECK(cs.natureOf(rome, season("spring"), 0, false) == "amb/world/dawn_scrub.ogg");
    CHECK(cs.natureOf(rome, season("autumn"), 0, false) == "amb/world/dawn_autumn.ogg");
    CHECK(cs.natureOf(rome, season("winter"), 2, false) == "amb/world/night_cold.ogg");
    CHECK(cs.natureOf(rome, season("spring"), 3, false).empty()); // no day bed but snow's
    const int zagros = w.file.findRegion("zagros");
    CHECK(cs.natureOf(zagros, season("winter"), 2, true) == "amb/world/night_snow.ogg");
    CHECK(cs.natureOf(zagros, season("winter"), 3, true) == "amb/world/day_snow.ogg");
    // Every region on land hears a night of its own in every season.
    for (std::size_t g = 0; g < w.regions.size(); ++g) {
        const nlohmann::json& snd = w.regions[g].theme.sound;
        if (!snd.is_object() || snd.value("climate", "") == "sea" || !snd.contains("nature"))
            continue;
        for (std::size_t k = 0; k < cat.seasons.size(); ++k)
            CHECK_MESSAGE(!cs.natureOf(static_cast<int>(g), static_cast<int>(k), 2, false).empty(),
                          w.file.regions[g].id << " " << cat.seasons[k].id);
    }
}

TEST_CASE("sound: game hours wrap over midnight") {
    CHECK(gameHour(0.0) == doctest::Approx(6));
    CHECK(gameHour(0.75) == doctest::Approx(0));
    CHECK(inHours(23, 19, 6));
    CHECK(inHours(3, 19, 6));
    CHECK_FALSE(inHours(12, 19, 6));
    CHECK(inHours(12, 6, 19));
}

TEST_CASE("weather: world-wide, deterministic, continuous across views, by climate") {
    Rig& r = rig();
    REQUIRE(r.ok);
    const world::LoadedWorld& w = *r.world;
    const Wind wind{{1, 0}, 0.5f, 0.3f};
    const SeasonClimate spring{0.6f, 1.2f, false};
    WeatherField a(w, 7);
    WeatherField b(w, 7);
    const TileRect rome{60, 1050, 140, 1130};
    a.update(5000.0, wind, spring, rome, WeatherMode::Natural);
    b.update(5000.0, wind, spring, rome, WeatherMode::Natural);
    REQUIRE(a.cells().size() == b.cells().size());
    for (std::size_t i = 0; i < a.cells().size(); ++i)
        CHECK(a.cells()[i].centre.x == b.cells()[i].centre.x);
    // A cell seen from one view is the same cell, at the same place, from an overlapping one.
    WeatherField c(w, 7);
    c.update(5000.0, wind, spring, {100, 1050, 180, 1130}, WeatherMode::Natural);
    int shared = 0;
    for (const WeatherCell& x : a.cells())
        for (const WeatherCell& y : c.cells())
            if (x.id == y.id) {
                CHECK(x.centre.x == doctest::Approx(y.centre.x));
                CHECK(x.centre.y == doctest::Approx(y.centre.y));
                ++shared;
            }
    // ... and a minute later it has moved on with the wind.
    WeatherField later(w, 7);
    later.update(5060.0, wind, spring, rome, WeatherMode::Natural);
    for (const WeatherCell& x : a.cells())
        for (const WeatherCell& y : later.cells())
            if (x.id == y.id) CHECK(y.centre.x > x.centre.x);
    // Rome's April rains far more than dry Parsa over a long run.
    const auto rainy = [&](TileRect view) {
        int n = 0;
        for (int p = 0; p < 200; ++p) {
            WeatherField f(w, 11);
            f.update(120.0 * p + 60.0, wind, spring, view, WeatherMode::Natural);
            for (const WeatherCell& x : f.cells()) n += x.rain ? 1 : 0;
        }
        return n;
    };
    CHECK(rainy(rome) > 2 * rainy({340, 40, 420, 120}));
    // Rain here and clear here act around the view.
    WeatherField forced(w, 7);
    forced.update(5000.0, wind, spring, rome, WeatherMode::Rain);
    CHECK(forced.rainAt({100, 1090}) > 0.5f);
    forced.update(5000.0, wind, spring, rome, WeatherMode::Clear);
    CHECK(forced.cells().empty());
    CHECK(forced.rainAt({100, 1090}) == doctest::Approx(0));
    (void)shared;
}

TEST_CASE("weather: young showers exist and fade in; snow falls only where the climate has it") {
    Rig& r = rig();
    REQUIRE(r.ok);
    const world::LoadedWorld& w = *r.world;
    const Wind wind{{1, 0}, 0.5f, 0.3f};
    // Rome's spring is the busiest sky: once the cap cut the youngest periods, so showers came
    // in at full strength (L-112). A cell new in the middle of the view has just been born.
    const SeasonClimate spring{0.6f, 1.2f, false};
    const TileRect rome{60, 1050, 140, 1130};
    WeatherField f(w, 7);
    std::vector<std::uint32_t> before;
    int born = 0;
    for (int k = 0; k < 600; ++k) {
        f.update(5000.0 + k, wind, spring, rome, WeatherMode::Natural);
        for (const WeatherCell& c : f.cells()) {
            const float m = c.radius + 2.0f;
            const bool inner = c.centre.x - m > static_cast<float>(rome.x0) &&
                               c.centre.x + m < static_cast<float>(rome.x1) &&
                               c.centre.y - m > static_cast<float>(rome.y0) &&
                               c.centre.y + m < static_cast<float>(rome.y1);
            if (k == 0 || !inner || std::ranges::find(before, c.id) != before.end()) continue;
            CAPTURE(k);
            CHECK(c.intensity() < 0.25f);
            ++born;
        }
        before.clear();
        for (const WeatherCell& c : f.cells()) before.push_back(c.id);
    }
    CHECK(born > 0);
    // Every cell over a place is there whichever view holds it.
    WeatherField a(w, 7);
    WeatherField b(w, 7);
    a.update(5000.0, wind, spring, rome, WeatherMode::Natural);
    b.update(5000.0, wind, spring, {rome.x0 + 40, rome.y0, rome.x1 + 40, rome.y1},
             WeatherMode::Natural);
    for (const WeatherCell& x : a.cells()) {
        if (x.centre.x - x.radius < static_cast<float>(rome.x0 + 40)) continue;
        CHECK(std::ranges::any_of(b.cells(), [&](const WeatherCell& y) { return y.id == x.id; }));
    }
    // Winter (December): it snows at home, never on Babylon's plain.
    const int babylon = w.map->regionAt({300, 225});
    REQUIRE(babylon >= 0);
    REQUIRE(w.file.regions[static_cast<std::size_t>(babylon)].id == "babylon");
    const SeasonClimate winter{0.5f, 1.0f, true, 9, 9};
    WeatherField s(w, 7);
    s.update(5000.0, wind, winter, {290, 215, 310, 235}, WeatherMode::Rain);
    CHECK_FALSE(s.snow());
    const TileRect h = w.file.home.rect;
    s.update(5000.0, wind, winter, h, WeatherMode::Rain);
    CHECK(s.snow());
}
