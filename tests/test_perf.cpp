// Measurement: frame statistics, the profiler's ring, the CSV line, interpolated drawing.

#include "core/perf.hpp"
#include "render/camera.hpp"
#include "test_support.hpp"

#include <doctest.h>

#include <array>
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
