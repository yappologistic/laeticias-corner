#pragma once
// What a world load skipped or found wrong, one line each, for the engine to log once. Errors are
// data that is wrong and was left out; warnings are expected gaps (a layer or a set not built yet).

#include <string>
#include <vector>

namespace lc::world {

struct Diagnostics {
    std::vector<std::string> errors;
    std::vector<std::string> warnings;

    void error(std::string line) { errors.push_back(std::move(line)); }
    void warn(std::string line) { warnings.push_back(std::move(line)); }
};

} // namespace lc::world
