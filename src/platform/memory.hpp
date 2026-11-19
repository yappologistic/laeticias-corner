#pragma once
// This process's memory as the system counts it; no SDL, so the pure libraries may ask too.

#include <utility>

namespace lc {

// Resident memory in MiB and its peak so far (Linux and Windows; 0 elsewhere).
[[nodiscard]] std::pair<double, double> processMemory();

} // namespace lc
