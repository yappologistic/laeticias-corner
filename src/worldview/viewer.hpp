#pragma once
// The world viewer, laeticias-world: loads the prebuilt world and draws it with WorldView,
// headless unless --interactive (dummy video and the software renderer for reproducible shots;
// --renderer opengl uses the windowless offscreen driver for GPU timings). It takes shots, runs
// scripts (worldview/script.hpp) and the bench cases, and reports what draws without art.

#include "worldview/script.hpp"

namespace lc::worldview {

// Exit codes: 0 fine, 1 failure (load, script expectation), 2 usage, 3 over budget (bench),
// 77 no GPU renderer for the bench.
[[nodiscard]] int runViewer(const ViewerOptions& options);

} // namespace lc::worldview
