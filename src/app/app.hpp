#pragma once
// The game executable's top level: window, main loop, input, tools, scripting and saving.

#include "app/options.hpp"

namespace lc {

// Returns the process exit code (non-zero when a script expectation failed or startup failed).
int runApp(const Options& options);

} // namespace lc
