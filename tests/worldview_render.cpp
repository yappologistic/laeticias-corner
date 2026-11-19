// The world renderer on the committed world, headless with the software renderer: gathering finds
// every piece and orders them, cached cells leave no seams, impostors match the full-detail view
// at their scale, and missing art is drawn and counted.

#include "core/catalog.hpp"
#include "render/atlas.hpp"
#include "render/bands.hpp"
#include "ui/font.hpp"
#include "world/loader.hpp"
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
                drawnBefore(tight.items[i].box, tight.items[j].box) != (at[i] < at[j]))
                ++bad;
    CHECK(bad == 0);
    CHECK(tight.cycles == 0);
}

TEST_CASE("render: every draw names its band, at every level") {
    // draw-order.md §2: no draw call without a band, and the depth band is where the world's
    // objects go at the native level.
    Rig& r = rig();
    REQUIRE(r.ok);
    for (const int level : {3, 2, 1, 0}) {
        const SurfacePtr px = r.frame(r.camera({313, 615}, level));
        REQUIRE(px);
        const auto& calls = r.view->bandDrawCalls();
        CAPTURE(level);
        CHECK(calls.back() == 0);
    }
    (void)r.frame(r.camera({313, 615}, 3));
    CHECK(r.view->bandDrawCalls()[bandTag(Band::Depth)] > 0);
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
