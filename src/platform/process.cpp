#include "platform/process.hpp"

#include <atomic>
#include <charconv>
#include <ctime>
#if defined(__linux__)
#include <linux/perf_event.h>
#include <sys/syscall.h>
#include <unistd.h>
#endif
#include <fstream>
#include <iterator>
#include <string>
#include <string_view>

namespace lc {

double msBetween(Uint64 a, Uint64 b) {
    return static_cast<double>(b - a) * 1000.0 / static_cast<double>(SDL_GetPerformanceFrequency());
}

double threadCpuMs() {
#if defined(CLOCK_THREAD_CPUTIME_ID)
    timespec t{};
    if (clock_gettime(CLOCK_THREAD_CPUTIME_ID, &t) == 0)
        return static_cast<double>(t.tv_sec) * 1000.0 + static_cast<double>(t.tv_nsec) * 1e-6;
#endif
    return -1.0;
}

CpuStalls cpuStallsFrom(std::string_view cpuStat) {
    const auto field = [&](std::string_view key) {
        long long v = 0;
        for (std::size_t at = cpuStat.find(key); at != std::string_view::npos;
             at = cpuStat.find(key, at + 1)) {
            if (at != 0 && cpuStat[at - 1] != '\n') continue; // (inside another field's name)
            const char* first = cpuStat.data() + at + key.size();
            (void)std::from_chars(first, cpuStat.data() + cpuStat.size(), v);
            break;
        }
        return v;
    };
    return {field("nr_throttled "), static_cast<double>(field("throttled_usec ")) / 1000.0};
}

CpuStalls cpuLimitStalls() {
#if defined(__linux__)
    std::string dir;
    {
        std::ifstream self("/proc/self/cgroup");
        for (std::string line; std::getline(self, line);)
            if (line.starts_with("0::")) dir = "/sys/fs/cgroup" + line.substr(3);
    }
    const auto text = [](const std::string& file) {
        std::ifstream in(file);
        return std::string(std::istreambuf_iterator<char>(in), {});
    };
    for (; dir.size() > std::string_view("/sys/fs/cgroup").size();
         dir.resize(dir.find_last_of('/'))) {
        const std::string quota = text(dir + "/cpu.max");
        if (!quota.empty() && !quota.starts_with("max"))
            return cpuStallsFrom(text(dir + "/cpu.stat"));
    }
#endif
    return {};
}

#if defined(__linux__)
namespace {
// One counter per thread, opened on first use and closed with the thread.
struct InstructionCounter {
    int fd = -1;
    InstructionCounter() {
        perf_event_attr attr{};
        attr.type = PERF_TYPE_HARDWARE;
        attr.size = sizeof attr;
        attr.config = PERF_COUNT_HW_INSTRUCTIONS;
        attr.exclude_kernel = 1; // what an unprivileged process may count
        attr.exclude_hv = 1;
        fd = static_cast<int>(syscall(SYS_perf_event_open, &attr, 0, -1, -1, 0));
    }
    ~InstructionCounter() {
        if (fd >= 0) close(fd);
    }
    InstructionCounter(const InstructionCounter&) = delete;
    InstructionCounter& operator=(const InstructionCounter&) = delete;
};
} // namespace

std::uint64_t threadInstructions() {
    thread_local const InstructionCounter counter;
    std::uint64_t n = 0;
    if (counter.fd < 0 || read(counter.fd, &n, sizeof n) != static_cast<ssize_t>(sizeof n))
        return 0;
    return n;
}
#else
std::uint64_t threadInstructions() {
    return 0;
}
#endif

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
