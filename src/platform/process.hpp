#pragma once
// Process-wide measurements shared by the game and the world viewer.

#include <SDL3/SDL.h>

#include <utility>

namespace lc {

// Milliseconds between two performance-counter readings.
[[nodiscard]] double msBetween(Uint64 a, Uint64 b);
// This process's resident memory in MiB (Linux; 0 elsewhere), and its peak.
[[nodiscard]] std::pair<double, double> processMemory();

} // namespace lc
