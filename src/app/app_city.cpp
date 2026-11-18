// City life driven by the game without the world renderer (src/life/): opened on demand by
// --focus or a script, stepped with the game's clock, checked by script expectations; the life
// dumps (--life-dump), and the city cases of --bench and --soak. The world renderer's
// integration replaces the focus with its camera.

#include "app/app_impl.hpp"
#include "life/report.hpp"

#include <SDL3/SDL.h>

#include <cstdio>
#include <fstream>

namespace lc {

namespace {

std::uint64_t citySeed(const Options& o) {
    return o.seed.value_or(1);
}

} // namespace

bool App::openCity() {
    if (city_) return true;
    if (loaded_) {
        city_ = std::make_unique<life::LifeSession>(life::openLifeSession(*loaded_, seed_));
        SDL_Log("city life: %.0f ms", city_->loadMs);
        if (worldView_) worldView_->setLife(city_->city.get());
        return true;
    }
    std::string error;
    auto s = life::openLifeSession(assets_, citySeed(opts_), error);
    if (!s) {
        SDL_Log("city life: cannot open the world: %s", error.c_str());
        return false;
    }
    city_ = std::make_unique<life::LifeSession>(std::move(*s));
    return true;
}

life::LifeClock App::cityClock() const {
    life::LifeClock c;
    c.day = clock_.day();
    c.t = clock_.time();
    c.season = season();
    c.rain = rainHere() >= tuning::kRainThreshold;
    c.epoch = (static_cast<std::int64_t>(clocks_) << 32) | clock_.jumps();
    return c;
}

TileRect App::cityView() const {
    if (cityOff_) return {};
    if (cityFocus_)
        return {cityFocus_->x - 16, cityFocus_->y - 16, cityFocus_->x + 17, cityFocus_->y + 17};
    // The map and the overview show no one; elsewhere the view (the life grows it by a ring, so
    // people walk in from beyond the edges instead of appearing).
    if (!worldView_ || map_.isOpen() ||
        worldview::WorldView::lodFor(view_.scale()) == worldview::Lod::Overview)
        return {};
    return cameraTiles();
}

void App::stepCity(float dt) {
    cityMs_ = 0;
    if (!city_) return;
    const Uint64 t0 = SDL_GetPerformanceCounter();
    city_->city->setView(cityView());
    city_->city->update(cityClock(), dt);
    cityMs_ = msBetween(t0, SDL_GetPerformanceCounter());
    if (citySound_) citySound_->addLifeSounds(city_->city->sounds());
}

std::optional<std::string> App::checkCity(std::span<const std::string> a) {
    if (!city_) return "no city life open (set city F first)";
    const life::CityLife& c = *city_->city;
    const world::WorldMap& m = *city_->world->map;
    const auto range = [&](int have, std::size_t at) -> std::optional<std::string> {
        if (a.size() < at + 2) return "expect city " + a[1] + " ... MIN MAX";
        const int lo = std::stoi(a[at]);
        const int hi = std::stoi(a[at + 1]);
        if (have >= lo && have <= hi) return std::nullopt;
        return std::format("expected city {} in {}..{} but found {}", a[1], lo, hi, have);
    };
    const std::string& what = a[1];
    if (what == "live") return range(c.stats().live, 2);
    if (what == "ground") {
        int bad = 0;
        c.forEachInfo([&](const life::CityLife::Info& in) {
            if (in.source == life::Source::Token) return;
            if (!m.inBounds(in.tile) || !m.walkable(in.tile) || in.level != m.level(in.tile)) ++bad;
        });
        return bad == 0 ? std::nullopt
                        : std::optional(std::format("{} people off the walkable ground", bad));
    }
    if (what == "moving") {
        // Nobody drawn walking on the spot, nobody going nowhere past the watchdog.
        const life::LifeStats& st = c.stats();
        if (st.marching == 0 && st.lost == 0) return std::nullopt;
        return std::format("{} walking in place, {} going nowhere past the watchdog", st.marching,
                           st.lost);
    }
    if (what == "slots") {
        int over = 0;
        c.forEachReservation([&](int, int count, int cap) { over += count > cap ? 1 : 0; });
        return over == 0 ? std::nullopt
                         : std::optional(std::format("{} slots over capacity", over));
    }
    if (what == "event" && a.size() >= 4) {
        bool on = false;
        for (const life::RunningEvent& e : c.running())
            if (e.event >= 0 && e.active &&
                city_->life->data.regions[static_cast<std::size_t>(e.region)]
                        .events[static_cast<std::size_t>(e.event)]
                        .id == a[2])
                on = true;
        const bool want = a[3] == "yes";
        return on == want ? std::nullopt
                          : std::optional(std::format("expected city event {} {}", a[2], a[3]));
    }
    if (what == "district" && a.size() >= 5) {
        int live = 0;
        for (const life::DistrictCount& d : c.districtCounts())
            if (city_->life->data.regions[static_cast<std::size_t>(d.region)]
                    .districts[static_cast<std::size_t>(d.district)]
                    .id == a[2])
                live += d.live + d.inside;
        if (live >= std::stoi(a[3]) && live <= std::stoi(a[4])) return std::nullopt;
        return std::format("expected city district {} in {}..{} but found {}", a[2], a[3], a[4],
                           live);
    }
    if (what == "drawn") // the sprites put last frame, not the actors gathered round the view
        return range(worldView_ ? worldView_->stats().actorsDrawn : 0, 2);
    if (what == "people") return range(citySound_ ? citySound_->people() : 0, 2);
    if (what == "sound" && a.size() >= 5) {
        // expect city sound FILE MIN MAX: the gain (x100) its loop is set to now.
        if (!citySound_) return "no city sound";
        const auto& files = citySound_->loops();
        const auto it = std::ranges::find(files, a[2]);
        if (it == files.end()) return "the city plays no " + a[2];
        const float g = citySound_->out()[static_cast<std::size_t>(it - files.begin())].gain;
        return range(static_cast<int>(std::lround(g * 100.0f)), 3);
    }
    return "unknown city expectation " + what;
}

int App::benchCity(bool judge) {
    if (!openCity()) return 0; // no world: nothing to measure
    life::BenchOptions o;
    o.frames = opts_.frames > 0 ? opts_.frames : 1200;
    o.assert = judge;
    std::vector<life::BenchCase> out;
    std::printf("bench: city life (simulation and enumeration; drawing them is the world "
                "renderer's)\n");
    return life::runLifeBench(*city_, o, out);
}

int App::soakCity() {
    if (!openCity()) return 0;
    // The budget where budgets apply (--budget-ms), as the corner's soak; memory always.
    return life::runLifeSoak(*city_, opts_.soak, opts_.budgetMs > 0 ? tuning::kSimBudgetMs : 0);
}

int runLifeDumps(const Options& o, const std::filesystem::path& assets) {
    std::string error;
    auto s = life::openLifeSession(assets, citySeed(o), error);
    if (!s) {
        SDL_Log("life dump: cannot open the world: %s", error.c_str());
        return 1;
    }
    const auto focus = life::parseFocus(*s->life, o.focus.value_or("forum"));
    if (!focus) {
        SDL_Log("life dump: unknown focus %s", o.focus.value_or("forum").c_str());
        return 2;
    }
    life::DumpOptions d;
    d.focus = *focus;
    d.day = o.lifeDay;
    d.hours = life::parseHours(o.lifeHours);
    d.out = o.lifeDump.value_or("life.json");
    d.label = o.focus.value_or("forum");
    if (d.hours.empty()) {
        SDL_Log("life dump: no hours in %s", o.lifeHours.c_str());
        return 2;
    }
    for (const auto& f : life::writeLifeDumps(*s, d))
        SDL_Log("life dump: wrote %s", f.string().c_str());
    return 0;
}

} // namespace lc
