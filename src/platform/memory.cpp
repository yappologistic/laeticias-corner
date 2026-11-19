#include "platform/memory.hpp"

#if defined(_WIN32)
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
// After windows.h, which it needs. PSAPI_VERSION 2 (the default) maps the call to kernel32.
#include <psapi.h>
#else
#include <fstream>
#include <string>
#include <string_view>
#endif

namespace lc {

#if defined(_WIN32)
std::pair<double, double> processMemory() {
    PROCESS_MEMORY_COUNTERS c{};
    c.cb = sizeof c;
    if (GetProcessMemoryInfo(GetCurrentProcess(), &c, sizeof c) == 0) return {0, 0};
    constexpr double kMiB = 1024.0 * 1024.0;
    return {static_cast<double>(c.WorkingSetSize) / kMiB,
            static_cast<double>(c.PeakWorkingSetSize) / kMiB};
}
#else
std::pair<double, double> processMemory() {
    // Linux; elsewhere the file does not open and both stay 0.
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
#endif

} // namespace lc
