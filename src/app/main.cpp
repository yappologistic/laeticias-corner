#include "app/app.hpp"

#include <cstdio>
#include <string_view>
#include <vector>

int main(int argc, char** argv) {
    const std::vector<std::string_view> args(argv + 1, argv + argc);
    const auto options = lc::parseOptions(args);
    if (!options) {
        (void)std::fprintf(stderr, "%s\n%.*s", options.error().c_str(),
                           static_cast<int>(lc::usage().size()), lc::usage().data());
        return 2;
    }
    if (options->help) {
        const auto u = lc::usage();
        return std::fwrite(u.data(), 1, u.size(), stdout) == u.size() ? 0 : 1;
    }
    return lc::runApp(*options);
}
