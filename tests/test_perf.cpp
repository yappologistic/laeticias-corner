// Measurement: frame statistics, the profiler's ring, the CSV line, interpolated drawing.

#include "core/perf.hpp"
#include "render/camera.hpp"
#include "test_support.hpp"

#include <doctest.h>

#include <array>
#include <cmath>
#include <string_view>
#include <vector>

using namespace lc;

TEST_CASE("frame statistics: average, nearest-rank percentiles and worst") {
    std::vector<float> v;
    for (int i = 1; i <= 100; ++i) v.push_back(static_cast<float>(i));
    const PerfStats s = perfStats(v);
    CHECK(s.count == 100);
    CHECK(s.avg == doctest::Approx(50.5));
    CHECK(s.p95 == 95.0f);
    CHECK(s.p99 == 99.0f);
    CHECK(s.worst == 100.0f);
    CHECK(perfStats({}).count == 0);
}

TEST_CASE("the profiler's ring keeps the last frames and skips unmeasured ones") {
    PerfRing ring;
    for (std::size_t i = 0; i < PerfRing::kCapacity + 10; ++i) {
        FrameSample f;
        f.frameMs = static_cast<float>(i);
        f.gpuMs = i % 2 == 0 ? 1.0f : -1.0f; // every other frame measured
        ring.push(f);
    }
    CHECK(ring.size() == PerfRing::kCapacity);
    CHECK(ring.recent(0).frameMs == static_cast<float>(PerfRing::kCapacity + 9));
    CHECK(ring.stats(&FrameSample::frameMs, 4).worst ==
          static_cast<float>(PerfRing::kCapacity + 9));
    CHECK(ring.stats(&FrameSample::frameMs, 4).count == 4);
    CHECK(ring.stats(&FrameSample::gpuMs).count == static_cast<int>(PerfRing::kCapacity / 2));
}

TEST_CASE("a perf-log line has one value per header column") {
    FrameSample f;
    f.frameMs = 4.25f;
    f.drawCalls = 21;
    std::array<char, kPerfLineMax> buf{};
    const std::string_view line(buf.data(), perfLine(7, f, buf));
    CHECK(line.starts_with("7,4.250,"));
    const auto commas = [](std::string_view s) { return std::ranges::count(s, ','); };
    CHECK(commas(line) == commas(kPerfHeader));
}

TEST_CASE("a slow frame is blamed on the system that took the largest share of it") {
    FrameSample f;
    f.frameMs = 20;
    f.cpuMs = 18;
    f.threadMs = 17.5f;
    f.sceneMs = 15;
    f.buildMs = 12; // inside the scene's time
    f.simMs = 1;
    f.uiMs = 1;
    CHECK(hitchCause(f) == HitchCause::CellBuild);
    f.buildMs = 1;
    f.uploadMs = 2;
    CHECK(hitchCause(f) == HitchCause::Scene);
    // The same frame with the thread off its core for most of it: nothing of the game's.
    f.threadMs = 3;
    CHECK(hitchCause(f) == HitchCause::Waiting);
    f.threadMs = 17.5f;
    f.gpuMs = 60; // the GPU finished long after submission
    CHECK(hitchCause(f) == HitchCause::Gpu);
}

TEST_CASE("the hitch log counts frames by time and the slow ones by cause") {
    HitchLog log;
    for (const float ms : {1.0f, 3.0f, 3.5f, 8.0f, 9.0f, 20.0f, 40.0f}) {
        FrameSample f;
        f.frameMs = ms;
        f.cpuMs = ms;
        f.threadMs = ms;
        f.simMs = ms; // all of it simulation
        log.add(f);
    }
    CHECK(log.frames == 7);
    CHECK(log.buckets == std::array<int, 6>{1, 2, 1, 1, 1, 1});
    CHECK(log.slow() == 3);
    CHECK(log.frozen() == 2);
    CHECK(log.over8[static_cast<std::size_t>(HitchCause::Simulation)] == 1);
    CHECK(log.over16[static_cast<std::size_t>(HitchCause::Simulation)] == 2);
    std::array<char, 256> line{};
    const std::string_view text(line.data(), log.line(line));
    CHECK(text.find("over 8.3 ms: 1 simulation") != std::string_view::npos);
    CHECK(text.find("over 16.6 ms: 2 simulation") != std::string_view::npos);
    // A buffer too small cuts the line short instead of overrunning it.
    std::array<char, 16> tiny{};
    CHECK(log.line(tiny) < tiny.size());
}

TEST_CASE("drawing between steps: the camera interpolates, a drag never lags") {
    const Catalog& c = test::catalog();
    Camera cam(c.iso(), {0, 0, 40, 40}, 0);
    const Vec2 screen{1280, 800};
    cam.place(c.iso().toWorld(20, 20), 1, screen);
    cam.beginStep();
    const Vec2 start = cam.position();
    cam.nudge({100, 0}, screen);
    cam.update(1.0f / 60.0f, screen);
    const Vec2 end = cam.position();
    REQUIRE(end.x > start.x);
    // Exactly at the step it is the camera itself; halfway, halfway.
    CHECK(cam.interpolated(1).position().x == end.x);
    CHECK(cam.interpolated(0.5f).position().x == doctest::Approx((start.x + end.x) * 0.5f));
    CHECK(cam.interpolated(0).position().x == doctest::Approx(start.x));
    // A drag moves the drawn view at once, whatever the interpolation.
    cam.update(10.0f, screen); // settle
    cam.beginStep();
    cam.dragBy({-40, 0}, screen);
    CHECK(cam.interpolated(0).position().x == doctest::Approx(cam.position().x));
    CHECK(cam.interpolated(0.3f).position().x == doctest::Approx(cam.position().x));
}

TEST_CASE("a pan eases out evenly and comes to rest on a whole window pixel") {
    const Catalog& c = test::catalog();
    for (const float zoom : {1.0f, 2.0f, 3.0f}) {
        Camera cam(c.iso(), {0, 0, 40, 40}, 0);
        const Vec2 screen{1281, 801}; // odd: the centre lies between pixels
        cam.place(c.iso().toWorld(20, 20), zoom, screen);
        // A held key, then let go: every step after that is shorter than the one before
        // (never a step back, never a longer one), down to rest.
        for (int i = 0; i < 30; ++i) {
            cam.beginStep();
            cam.nudge({7.3f, 3.1f}, screen);
            cam.update(1.0f / 60.0f, screen);
        }
        float last = 1e9f;
        int steps = 0;
        while (cam.moving() || steps == 0) {
            const Vec2 before = cam.position();
            cam.beginStep();
            cam.update(1.0f / 60.0f, screen);
            const float moved =
                std::hypot(cam.position().x - before.x, cam.position().y - before.y);
            // The very last step closes what is left (under a hundredth of a pixel short).
            CHECK(moved <= last + 0.02f / zoom);
            last = moved;
            REQUIRE(++steps < 600);
        }
        // At rest the window's corner is on a whole pixel: drawing it snapped changes nothing.
        const Vec2 rest = cam.position();
        const Vec2 snapped = cam.snapped(screen).position();
        CHECK(snapped.x == doctest::Approx(rest.x).epsilon(1e-6));
        CHECK(snapped.y == doctest::Approx(rest.y).epsilon(1e-6));
        const float corner = (rest.x - screen.x * 0.5f / zoom) * zoom;
        CHECK(std::abs(corner - std::round(corner)) < 1e-2f);
    }
}
