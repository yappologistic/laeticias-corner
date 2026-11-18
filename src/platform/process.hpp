#pragma once
// Process-wide measurements shared by the game and the world viewer.

#include <SDL3/SDL.h>

#include <cstdint>
#include <utility>

namespace lc {

// Milliseconds between two performance-counter readings.
[[nodiscard]] double msBetween(Uint64 a, Uint64 b);
// This process's resident memory in MiB (Linux; 0 elsewhere), and its peak.
[[nodiscard]] std::pair<double, double> processMemory();
// CPU time the calling thread has used, in milliseconds (-1 where the system does not say).
// Against the wall clock it tells running from waiting: a thread that was blocked on a file or a
// lock, or taken off its core, used no CPU meanwhile.
[[nodiscard]] double threadCpuMs();
// Heap allocations the calling thread has made since it started. The game's executable counts
// them (platform/alloc_count.cpp replaces operator new there); a program that does not count
// (the tests, sanitizer builds) reports none: allocCounting() says which.
[[nodiscard]] std::uint64_t threadAllocs();
[[nodiscard]] bool allocCounting();
// For the counting operator new only.
void noteAlloc() noexcept;
void enableAllocCounting() noexcept;

} // namespace lc
