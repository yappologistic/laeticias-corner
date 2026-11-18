#include "worldview/viewer.hpp"

#include <cstdio>
#include <string_view>
#include <vector>

int main(int argc, char** argv) {
    const std::vector<std::string_view> args(argv + 1, argv + argc);
    const auto options = lc::worldview::parseViewerOptions(args);
    const auto usage = lc::worldview::viewerUsage();
    if (!options) {
        (void)std::fprintf(stderr, "%s\n%.*s", options.error().c_str(),
                           static_cast<int>(usage.size()), usage.data());
        return 2;
    }
    if (options->help)
        return std::fwrite(usage.data(), 1, usage.size(), stdout) == usage.size() ? 0 : 1;
    return lc::worldview::runViewer(*options);
}
