#include "platform/process.hpp"

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

} // namespace lc
