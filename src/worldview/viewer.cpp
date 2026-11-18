#include "worldview/viewer.hpp"

#include "core/perf.hpp"
#include "core/starter.hpp"
#include "platform/process.hpp"
#include "world/loader.hpp"
#include "worldview/renderer.hpp"
#include "worldview/tuning.hpp"

#include <algorithm>
#include <charconv>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <functional>
#include <memory>
#include <numbers>
#include <string>
#include <vector>

namespace lc::worldview {
namespace fs = std::filesystem;
namespace {

constexpr float kStep = 1.0f / 60.0f;       // script frames
constexpr float kBenchStep = 1.0f / 120.0f; // bench frames: motion at the 120 FPS target
constexpr int kSettleFrames = 4000;
constexpr int kWarmFrames = 60;

// Owns SDL initialisation; headless runs can never reach the desktop or the speakers.
struct Session {
    bool ok = false;
    Session(bool headless, bool gpu) {
        if (headless &&
            (!SDL_SetHintWithPriority(SDL_HINT_VIDEO_DRIVER, gpu ? "offscreen" : "dummy",
                                      SDL_HINT_OVERRIDE) ||
             !SDL_SetHintWithPriority(SDL_HINT_AUDIO_DRIVER, "dummy", SDL_HINT_OVERRIDE))) {
            SDL_Log("cannot force headless drivers: %s", SDL_GetError());
            return;
        }
        ok = SDL_Init(SDL_INIT_VIDEO);
        if (!ok) SDL_Log("SDL_Init failed: %s", SDL_GetError());
    }
    ~Session() { SDL_Quit(); }
    Session(const Session&) = delete;
    Session& operator=(const Session&) = delete;
};

fs::path findAssets(const ViewerOptions& o) {
    if (o.assets) return *o.assets;
    if (const char* env = std::getenv("LAETICIA_ASSETS_DIR")) return env;
    return LC_SOURCE_ASSETS_DIR;
}

struct ImageStats {
    double luma = 0;
    double contrast = 0;
};

ImageStats imageStats(SDL_Surface* s) {
    const SurfacePtr px{SDL_ConvertSurface(s, SDL_PIXELFORMAT_RGBA32)};
    if (!px) return {};
    double sum = 0;
    double sq = 0;
    const auto n = static_cast<double>(px->w) * static_cast<double>(px->h);
    for (int y = 0; y < px->h; ++y) {
        const auto* row = static_cast<const std::uint8_t*>(px->pixels) +
                          static_cast<std::ptrdiff_t>(y) * px->pitch;
        for (int x = 0; x < px->w; ++x) {
            const std::uint8_t* p = row + static_cast<std::ptrdiff_t>(x) * 4;
            const double l = (0.2126 * p[0] + 0.7152 * p[1] + 0.0722 * p[2]) / 255.0;
            sum += l;
            sq += l * l;
        }
    }
    const double mean = sum / n;
    return {mean, std::sqrt(std::max(0.0, sq / n - mean * mean))};
}

struct Sample {
    float frameMs = 0;
    float cpuMs = 0;
    int drawCalls = 0;
    int drawn = 0;
    int culled = 0;
};

class Viewer {
public:
    Viewer(const ViewerOptions& o, fs::path assets) : o_(o), assets_(std::move(assets)) {}

    int run();

private:
    bool load();
    bool init();
    void frame(float dt);
    void present();
    // Reading a pixel back waits until the GPU has drawn everything queued.
    void gpuSync();
    [[nodiscard]] std::optional<Vec2> tileOf(std::string_view target) const;
    void lookAtTile(Vec2 tile);
    bool go(std::string_view target);
    void settle();
    bool shot(const fs::path& file);
    ImageStats measure();
    int runScript();
    int runBench();
    int runInteractive();
    void report() const;

    ViewerOptions o_;
    fs::path assets_;
    Catalog cat_;
    std::optional<world::LoadedWorld> world_;
    WindowPtr window_;
    RendererPtr renderer_;
    std::unique_ptr<Atlas> atlas_;
    Font font_;
    std::unique_ptr<Batch> ui_;
    std::unique_ptr<WorldView> view_;
    std::unique_ptr<WorldCamera> camera_;
    double clock_ = 0.25;
    double now_ = 0;
    int pw_ = 0;
    int ph_ = 0;
    bool async_ = false;
};

bool Viewer::load() {
    auto cat = loadCatalog(assets_ / "catalog.json");
    if (!cat) {
        SDL_Log("catalog: %s", cat.error().c_str());
        return false;
    }
    cat_ = std::move(*cat);
    auto w = world::loadWorld(assets_, cat_);
    if (!w) {
        SDL_Log("world: %s", w.error().c_str());
        return false;
    }
    world_.emplace(std::move(*w));
    // The player's region shows the starter scene, as a new world opens (world-tech §4.1).
    world::Diagnostics diag;
    if (auto r = world_->map->applyHome(world::homeDeltaFrom(makeStarterWorld(cat_), cat_), diag);
        !r)
        SDL_Log("home: %s", r.error().c_str());
    SDL_Log(
        "world: loaded in %.1f ms, %zu errors and %zu warnings in the data (worldinfo validate)",
        world_->timings.total, world_->diagnostics.errors.size(),
        world_->diagnostics.warnings.size());
    return true;
}

bool Viewer::init() {
    const SDL_WindowFlags flags =
        o_.interactive ? SDL_WINDOW_RESIZABLE | SDL_WINDOW_HIGH_PIXEL_DENSITY : 0;
    window_.reset(SDL_CreateWindow("Laeticia's Corner: the world", o_.w, o_.h, flags));
    if (!window_) {
        SDL_Log("cannot create window: %s", SDL_GetError());
        return false;
    }
    const std::string driver =
        !o_.renderer.empty() ? o_.renderer : (o_.interactive ? "" : "software");
    renderer_.reset(SDL_CreateRenderer(window_.get(), driver.empty() ? nullptr : driver.c_str()));
    if (!renderer_) {
        SDL_Log("cannot create renderer: %s", SDL_GetError());
        return false;
    }
    if (o_.interactive && !SDL_SetRenderVSync(renderer_.get(), 1))
        SDL_Log("vsync: %s", SDL_GetError());
    if (!SDL_GetRenderOutputSize(renderer_.get(), &pw_, &ph_)) return false;
    atlas_ = std::make_unique<Atlas>(renderer_.get(), assets_, cat_.iso());
    if (!font_.load(assets_ / "fonts") || !font_.build(renderer_.get(), 1.0f)) return false;
    ui_ = std::make_unique<Batch>(renderer_.get());
    async_ = o_.interactive || o_.bench;
    view_ = std::make_unique<WorldView>(renderer_.get(), *world_, assets_, *atlas_, async_);
    const world::WorldMap& m = *world_->map;
    camera_ = std::make_unique<WorldCamera>(cat_.iso(), m.width(), m.height(),
                                            static_cast<float>(15 * m.content().tileLevel()));
    camera_->setScreen({static_cast<float>(pw_), static_cast<float>(ph_)});
    camera_->setLevel(camera_->levelFor(o_.zoom));
    clock_ = parseClock(o_.clock).value_or(0.25);
    return go(o_.go.empty() ? "corner" : o_.go);
}

std::optional<Vec2> Viewer::tileOf(std::string_view target) const {
    const world::WorldFile& wf = world_->file;
    if (const auto comma = target.find(','); comma != std::string_view::npos) {
        int x = 0;
        int y = 0;
        const auto a = std::from_chars(target.data(), target.data() + comma, x);
        const auto b = std::from_chars(target.data() + comma + 1, target.data() + target.size(), y);
        if (a.ec != std::errc{} || b.ec != std::errc{}) return std::nullopt;
        return Vec2{static_cast<float>(x) + 0.5f, static_cast<float>(y) + 0.5f};
    }
    const int r = wf.findRegion(target);
    if (r < 0) return std::nullopt;
    for (const world::Marker& mk : wf.markers)
        if (mk.region == r)
            return Vec2{static_cast<float>(mk.at.x) + 0.5f, static_cast<float>(mk.at.y) + 0.5f};
    // No marker: the middle of the region's tiles.
    const world::WorldMap& m = *world_->map;
    double sx = 0;
    double sy = 0;
    long n = 0;
    for (int y = 0; y < m.height(); y += 4)
        for (int x = 0; x < m.width(); x += 4)
            if (m.regionAt({x, y}) == r) {
                sx += x;
                sy += y;
                ++n;
            }
    if (n == 0) return std::nullopt;
    return Vec2{static_cast<float>(sx / static_cast<double>(n)),
                static_cast<float>(sy / static_cast<double>(n))};
}

void Viewer::lookAtTile(Vec2 t) {
    // Centre on the tile as drawn, lifted by its level.
    const world::WorldMap& m = *world_->map;
    const TilePos p{static_cast<int>(t.x), static_cast<int>(t.y)};
    const int level = m.inBounds(p) ? m.level(p) : 0;
    const Vec2 w = cat_.iso().toWorld(t.x, t.y);
    camera_->lookAt({w.x, w.y - static_cast<float>(level * m.content().tileLevel())});
}

bool Viewer::go(std::string_view target) {
    const auto t = tileOf(target);
    if (!t) {
        SDL_Log("goto: no region or tile '%.*s'", static_cast<int>(target.size()), target.data());
        return false;
    }
    lookAtTile(*t);
    view_->jumped(*camera_);
    return true;
}

void Viewer::frame(float dt) {
    camera_->update(dt);
    now_ += static_cast<double>(dt);
    if (!SDL_SetRenderTarget(renderer_.get(), nullptr)) SDL_Log("%s", SDL_GetError());
    view_->draw(*camera_, clock_, dt, now_);
    // The era caption as a plain label for now (world-tech §4.8).
    const std::string caption = view_->caption();
    if (!caption.empty()) {
        const float a = view_->captionAlpha();
        const float w = font_.measure(Face::Title, caption);
        const float x = std::round((static_cast<float>(pw_) - w) * 0.5f);
        const float y = std::round(font_.lineHeight(Face::Title) * 1.5f);
        (void)font_.draw(*ui_, Face::Title, caption, x + 1, y + 1, {0, 0, 0, 0.5f * a});
        (void)font_.draw(*ui_, Face::Title, caption, x, y, {1, 0.98f, 0.93f, a});
        ui_->flush();
    }
}

void Viewer::present() {
    if (!SDL_RenderPresent(renderer_.get())) SDL_Log("present: %s", SDL_GetError());
}

void Viewer::gpuSync() {
    const SDL_Rect one{0, 0, 1, 1};
    if (const SurfacePtr px{SDL_RenderReadPixels(renderer_.get(), &one)}; !px)
        SDL_Log("gpu sync: %s", SDL_GetError());
}

void Viewer::settle() {
    for (int i = 0; i < kSettleFrames; ++i) {
        frame(kStep);
        present();
        if (view_->settled() && !camera_->flying()) return;
    }
    SDL_Log("settle: still streaming after %d frames", kSettleFrames);
}

bool Viewer::shot(const fs::path& file) {
    frame(0);
    const SurfacePtr px{SDL_RenderReadPixels(renderer_.get(), nullptr)};
    present();
    if (!px) {
        SDL_Log("shot: %s", SDL_GetError());
        return false;
    }
    if (file.has_parent_path()) {
        std::error_code ec;
        fs::create_directories(file.parent_path(), ec);
    }
    if (!SDL_SavePNG(px.get(), file.string().c_str())) {
        SDL_Log("shot: cannot write %s: %s", file.string().c_str(), SDL_GetError());
        return false;
    }
    SDL_Log("shot: %s", file.string().c_str());
    return true;
}

ImageStats Viewer::measure() {
    frame(0);
    const SurfacePtr px{SDL_RenderReadPixels(renderer_.get(), nullptr)};
    present();
    return px ? imageStats(px.get()) : ImageStats{};
}

int Viewer::runScript() {
    auto text = readTextFile(*o_.script);
    if (!text) {
        SDL_Log("script: %s", text.error().c_str());
        return 1;
    }
    auto cmds = parseScript(*text);
    if (!cmds) {
        SDL_Log("script %s: %s", o_.script->string().c_str(), cmds.error().c_str());
        return 2;
    }
    const auto fail = [&](const Command& c, const std::string& what) {
        SDL_Log("script %s line %d: %s", o_.script->filename().string().c_str(), c.line,
                what.c_str());
        return 1;
    };
    const auto num = [](const std::string& s) { return std::strtod(s.c_str(), nullptr); };
    for (const Command& c : *cmds) {
        const auto& a = c.args;
        switch (c.op) {
        case Op::Goto:
            if (!go(a.size() == 2 ? a[0] + "," + a[1] : a[0])) return fail(c, "no such place");
            break;
        case Op::Zoom: camera_->setLevel(camera_->levelFor(*parseZoom(a[0]))); break;
        case Op::Clock: clock_ = *parseClock(a[0]); break;
        case Op::Pan:
            camera_->panBy({static_cast<float>(num(a[0])), static_cast<float>(num(a[1]))});
            break;
        case Op::Fly: {
            const bool xy = a.size() >= 2 && std::isdigit(static_cast<unsigned char>(a[0][0])) &&
                            std::isdigit(static_cast<unsigned char>(a[1][0]));
            const auto t = tileOf(xy ? a[0] + "," + a[1] : a[0]);
            if (!t) return fail(c, "no such place");
            const std::size_t rest = xy ? 2 : 1;
            const int level = a.size() > rest ? camera_->levelFor(parseZoom(a[rest]).value_or(1))
                                              : camera_->level();
            const float secs =
                a.size() > rest + 1 ? static_cast<float>(num(a[rest + 1])) : tuning::kFlightSeconds;
            camera_->flyTo(cat_.iso().toWorld(t->x, t->y), level, secs);
            break;
        }
        case Op::Frames:
            for (int i = 0; i < static_cast<int>(num(a[0])); ++i) {
                frame(kStep);
                present();
            }
            break;
        case Op::Settle: settle(); break;
        case Op::Shot:
            if (!shot(o_.shots ? *o_.shots / a[0] : fs::path(a[0]))) return fail(c, "shot failed");
            break;
        case Op::Expect: {
            const FrameStats& st = view_->stats();
            const std::string& what = a[0];
            if (what == "region" || what == "lod" || what == "page_resident" || what == "caption") {
                bool ok = false;
                std::string got;
                if (what == "region") {
                    const int d = view_->theme().dominant();
                    got = d >= 0 ? world_->file.regions[static_cast<std::size_t>(d)].id : "none";
                    ok = got == a[1];
                } else if (what == "lod") {
                    static constexpr const char* kNames[] = {"native", "half", "quarter",
                                                             "overview"};
                    got = kNames[static_cast<int>(st.lod)];
                    ok = got == a[1];
                } else if (what == "page_resident") {
                    ok = view_->pages().setResident(a[1]);
                    got = ok ? "resident" : "not resident";
                } else {
                    got = view_->caption();
                    ok = !got.empty();
                }
                if (!ok)
                    return fail(c, "expected " + what + (a.size() > 1 ? " " + a[1] : "") +
                                       ", got " + got);
                break;
            }
            if (a.size() != 3) return fail(c, "expect " + what + " needs an operator and a value");
            double v = 0;
            if (what == "luma" || what == "contrast") {
                const ImageStats im = measure();
                v = what == "luma" ? im.luma : im.contrast;
            } else if (what == "draw_calls") {
                v = st.drawCalls;
            } else if (what == "sprites") {
                v = st.spritesDrawn;
            } else if (what == "placeholders") {
                v = view_->sprites().placeholdersPlaced();
            } else if (what == "flat_terrain") {
                v = static_cast<double>(view_->sprites().missingTerrain().size());
            } else if (what == "cells_pending") {
                v = st.cellsPending;
            } else {
                return fail(c, "cannot expect '" + what + "'");
            }
            const auto r = compare(v, a[1], num(a[2]));
            if (!r) return fail(c, "unknown operator " + a[1]);
            if (!*r)
                return fail(c, std::format("expected {} {} {}, got {:.4f}", what, a[1], a[2], v));
            SDL_Log("expect %s %s %s: %.4f", what.c_str(), a[1].c_str(), a[2].c_str(), v);
            break;
        }
        }
    }
    return 0;
}

void Viewer::report() const {
    const WorldSprites& s = view_->sprites();
    std::printf("missing art: %d placed items drawn as placeholders\n", s.placeholdersPlaced());
    for (const MissingArt& m : s.missingItems())
        std::printf("  item %-28s %6d placed  %s\n", m.id.c_str(), m.count,
                    m.look == Look::StandIn ? "stand-in" : "placeholder");
    for (const MissingArt& m : s.missingTerrain())
        std::printf("  terrain %-25s %6d tiles  flat colour\n", m.id.c_str(), m.count);
    for (const std::string& m : s.flatMaterials())
        std::printf("  faces %-27s flat colour\n", m.c_str());
    for (const auto& [id, n] : world_->map->unresolved())
        std::printf("  item %-28s %6d placed  in no catalog (not drawn)\n", id.c_str(), n);
}

int Viewer::runBench() {
    struct Case {
        const char* name;
        const char* what;
        std::function<void()> setup;
        std::function<void(int, int)> step; // frame index, frame count
        int frames;
        bool city; // the draw-call budget applies
    };
    WorldCamera& cam = *camera_;
    // Grid tiles of the views the world builders preview (tools/worldgen/regions/*/layout.py).
    const Vec2 terrace{374, 58};
    const Vec2 agora{262, 672};
    const Vec2 acropolis{313, 615};
    const auto circle = [&](float radius) {
        return [&cam, radius](int i, int n) {
            const float a =
                2.0f * std::numbers::pi_v<float> * static_cast<float>(i) / static_cast<float>(n);
            const float da = 2.0f * std::numbers::pi_v<float> / static_cast<float>(n);
            cam.panBy({-std::sin(a) * radius * da * cam.scale(),
                       std::cos(a) * radius * da * cam.scale()});
        };
    };
    const std::vector<Case> cases{
        {"parsa_terrace", "Parsa terrace at 1x, day, a slow circle",
         [&] {
             clock_ = *parseClock("day");
             cam.setLevel(cam.levelFor(1));
             lookAtTile(terrace);
         },
         circle(300), 600, true},
        {"agora", "Athenian Agora at 1x, dusk, a slow circle",
         [&] {
             clock_ = *parseClock("dusk");
             cam.setLevel(cam.levelFor(1));
             lookAtTile(agora);
         },
         circle(300), 600, true},
        {"acropolis_night", "Acropolis at 1x, night (glow), a slow circle",
         [&] {
             clock_ = *parseClock("night");
             cam.setLevel(cam.levelFor(1));
             lookAtTile(acropolis);
         },
         circle(300), 600, true},
        {"pan_fast", "Athens at 1x, panning 1800 px/s across the region and back",
         [&] {
             clock_ = *parseClock("day");
             cam.setLevel(cam.levelFor(1));
             lookAtTile({270, 600});
         },
         [&](int i, int n) {
             const float v = 1800.0f * kBenchStep * (i < n / 2 ? 1.0f : -1.0f);
             cam.panBy({v * cam.scale(), v * 0.5f * cam.scale()});
         },
         720, false},
        {"flight", "Parsa to Athens through every zoom level (6 s)",
         [&] {
             clock_ = *parseClock("day");
             cam.setLevel(cam.levelFor(1));
             lookAtTile(terrace);
         },
         [&](int i, int) {
             if (i == 0) cam.flyTo(cat_.iso().toWorld(agora.x, agora.y), cam.levelFor(1), 6.0f);
         },
         840, false},
        {"overview", "the overview, panning",
         [&] {
             clock_ = *parseClock("day");
             cam.setLevel(0);
             lookAtTile({224, 640});
         },
         circle(400), 480, false},
    };
    bool over = false;
    std::printf("bench %dx%d, renderer %s\n", pw_, ph_, SDL_GetRendererName(renderer_.get()));
    std::printf("%-16s %6s %6s %6s %6s | %5s %5s | %5s %7s %7s | %5s %7s %7s\n", "case", "avg",
                "p95", "p99", "worst", "cpu", "cpu99", "draws", "drawn", "culled", "cells",
                "texMiB", "rssMiB");
    for (const Case& c : cases) {
        if (!o_.benchCase.empty() && o_.benchCase != c.name) continue;
        c.setup();
        view_->jumped(cam);
        // Warm up until the start is loaded and built: the cases measure what follows.
        for (int i = 0; i < kWarmFrames || (!view_->settled() && i < kSettleFrames); ++i) {
            frame(kBenchStep);
            present();
            gpuSync();
        }
        std::vector<Sample> samples;
        samples.reserve(static_cast<std::size_t>(c.frames));
        for (int i = 0; i < c.frames; ++i) {
            const Uint64 t0 = SDL_GetPerformanceCounter();
            c.step(i, c.frames);
            frame(kBenchStep);
            const Uint64 t1 = SDL_GetPerformanceCounter();
            present();
            gpuSync();
            const Uint64 t2 = SDL_GetPerformanceCounter();
            const double f = static_cast<double>(SDL_GetPerformanceFrequency()) / 1000.0;
            const FrameStats& st = view_->stats();
            samples.push_back({static_cast<float>(static_cast<double>(t2 - t0) / f),
                               static_cast<float>(static_cast<double>(t1 - t0) / f), st.drawCalls,
                               st.spritesDrawn, st.spritesCulled});
        }
        std::vector<float> frameMs;
        std::vector<float> cpuMs;
        int draws = 0;
        double drawn = 0;
        double culled = 0;
        for (const Sample& s : samples) {
            frameMs.push_back(s.frameMs);
            cpuMs.push_back(s.cpuMs);
            draws = std::max(draws, s.drawCalls);
            drawn += s.drawn;
            culled += s.culled;
        }
        const PerfStats fs = perfStats(frameMs);
        const PerfStats cs = perfStats(cpuMs);
        const FrameStats& st = view_->stats();
        const double n = static_cast<double>(samples.size());
        std::printf(
            "%-16s %6.2f %6.2f %6.2f %6.2f | %5.2f %5.2f | %5d %7.0f %7.0f | %5d %7.1f %7.1f\n",
            c.name, static_cast<double>(fs.avg), static_cast<double>(fs.p95),
            static_cast<double>(fs.p99), static_cast<double>(fs.worst), static_cast<double>(cs.avg),
            static_cast<double>(cs.p99), draws, drawn / n, culled / n, st.cellsCached,
            static_cast<double>(st.textureBytes()) / 1048576.0, processMemory().first);
        const bool bad = fs.p99 > tuning::kFrameP99Ms || fs.worst > tuning::kFrameWorstMs ||
                         cs.avg > tuning::kCpuAvgMs || (c.city && draws > tuning::kDrawCallsGate);
        if (bad) std::printf("  over budget: %s\n", c.what);
        if (c.city && draws > tuning::kDrawCallsMax)
            std::printf("  over the %d-draw target (gate %d): %s\n", tuning::kDrawCallsMax,
                        tuning::kDrawCallsGate, c.what);
        over = over || bad;
    }
    std::printf(
        "budgets: frame p99 <= %.1f ms, worst <= %.1f ms, cpu avg <= %.1f ms, city draws <= %d "
        "(target %d)\n",
        tuning::kFrameP99Ms, tuning::kFrameWorstMs, tuning::kCpuAvgMs, tuning::kDrawCallsGate,
        tuning::kDrawCallsMax);
    return over && o_.budget ? 3 : 0;
}

int Viewer::runInteractive() {
    // For a person flying around: arrows or WASD pan, wheel or +/- zoom, M the overview, N the
    // time of day, 1-4 fly home, to Rome, Athens and Parsa.
    static constexpr const char* kPlaces[] = {"corner", "rome", "athens", "parsa"};
    Uint64 last = SDL_GetTicksNS();
    for (;;) {
        for (SDL_Event e; SDL_PollEvent(&e);) {
            if (e.type == SDL_EVENT_QUIT) return 0;
            if (e.type == SDL_EVENT_WINDOW_PIXEL_SIZE_CHANGED) {
                pw_ = e.window.data1;
                ph_ = e.window.data2;
                camera_->setScreen({static_cast<float>(pw_), static_cast<float>(ph_)});
            }
            if (e.type == SDL_EVENT_MOUSE_WHEEL)
                camera_->setLevel(camera_->level() + (e.wheel.y > 0 ? 1 : -1));
            if (e.type != SDL_EVENT_KEY_DOWN) continue;
            const SDL_Keycode k = e.key.key;
            if (k == SDLK_ESCAPE) return 0;
            if (k == SDLK_EQUALS || k == SDLK_KP_PLUS) camera_->setLevel(camera_->level() + 1);
            if (k == SDLK_MINUS || k == SDLK_KP_MINUS) camera_->setLevel(camera_->level() - 1);
            if (k == SDLK_M) camera_->setLevel(camera_->level() == 0 ? tuning::kDefaultZoom : 0);
            if (k == SDLK_N) clock_ = std::fmod(clock_ + 0.125, 1.0);
            if (k >= SDLK_1 && k <= SDLK_4)
                if (const auto t = tileOf(kPlaces[k - SDLK_1]))
                    camera_->flyTo(cat_.iso().toWorld(t->x, t->y), camera_->levelFor(1),
                                   tuning::kFlightSeconds * 2);
        }
        const Uint64 now = SDL_GetTicksNS();
        const float dt = std::min(0.1f, static_cast<float>(now - last) * 1e-9f);
        last = now;
        const bool* keys = SDL_GetKeyboardState(nullptr);
        const float v = tuning::kPanTilesPerSecond * 64.0f * dt * camera_->scale();
        const float dx = static_cast<float>((keys[SDL_SCANCODE_D] || keys[SDL_SCANCODE_RIGHT]) -
                                            (keys[SDL_SCANCODE_A] || keys[SDL_SCANCODE_LEFT]));
        const float dy = static_cast<float>((keys[SDL_SCANCODE_S] || keys[SDL_SCANCODE_DOWN]) -
                                            (keys[SDL_SCANCODE_W] || keys[SDL_SCANCODE_UP]));
        if (dx != 0 || dy != 0) camera_->panBy({dx * v, dy * v});
        frame(dt);
        present();
    }
}

int Viewer::run() {
    const bool gpu = !o_.renderer.empty() && o_.renderer != "software";
    const Session session(!o_.interactive, gpu);
    if (!session.ok) return 1;
    if (!load()) return 1;
    if (!init()) return o_.bench ? 77 : 1;
    if (o_.report) report();
    if (o_.bench) {
        if (!gpu) {
            SDL_Log("bench: needs a GPU renderer (--renderer opengl)");
            return 77;
        }
        return runBench();
    }
    if (o_.interactive) return runInteractive();
    if (o_.script) return runScript();
    settle();
    if (o_.shot) return shot(*o_.shot) ? 0 : 1;
    return 0;
}

} // namespace

int runViewer(const ViewerOptions& options) {
    Viewer v(options, findAssets(options));
    return v.run();
}

} // namespace lc::worldview
