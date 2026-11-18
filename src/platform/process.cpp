#include "platform/process.hpp"

#include <atomic>
#include <ctime>
#include <fstream>
#include <string>
#include <string_view>

namespace lc {

double msBetween(Uint64 a, Uint64 b) {
    return static_cast<double>(b - a) * 1000.0 / static_cast<double>(SDL_GetPerformanceFrequency());
}

std::pair<double, double> processMemory() {
    std::ifstream in("/proc/self/status");
    double rss = 0;
    double peak = 0;
    for (std::string line; std::getline(in, line);) {
        const auto field = [&](const char* key, double& out) {
            if (line.starts_with(key))
                out = std::stod(line.substr(std::string_view(key).size())) / 1024.0;
        };
        field("VmRSS:", rss);
        field("VmHWM:", peak);
    }
    return {rss, peak};
}

double threadCpuMs() {
#if defined(CLOCK_THREAD_CPUTIME_ID)
    timespec t{};
    if (clock_gettime(CLOCK_THREAD_CPUTIME_ID, &t) == 0)
        return static_cast<double>(t.tv_sec) * 1000.0 + static_cast<double>(t.tv_nsec) * 1e-6;
#endif
    return -1.0;
}

namespace {
// Plain thread-local integers: operator new runs before and after every other object's life.
thread_local std::uint64_t tAllocs = 0;
std::atomic<bool> gCounting{false};
} // namespace

std::uint64_t threadAllocs() {
    return tAllocs;
}

bool allocCounting() {
    return gCounting.load(std::memory_order_relaxed);
}

void noteAlloc() noexcept {
    ++tAllocs;
}

void enableAllocCounting() noexcept {
    gCounting.store(true, std::memory_order_relaxed);
}

} // namespace lc
