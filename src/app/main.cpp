#include "app/app.hpp"

#include <cstdio>
#include <string_view>
#include <vector>

int main(int argc, char** argv) {
    const std::vector<std::string_view> args(argv + 1, argv + argc);
    const auto options = lc::parseOptions(args);
    if (!options) {
        std::fprintf(stderr, "%s\n%s", options.error().c_str(), lc::usage().data());
        return 2;
    }
    if (options->help) {
        std::fputs(lc::usage().data(), stdout);
        return 0;
    }
    return lc::runApp(*options);
}
