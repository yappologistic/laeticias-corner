#pragma once
// Process-wide measurements shared by the game and the world viewer.

#include <SDL3/SDL.h>

#include <cstdint>
#include <string_view>
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
// How often a control group was frozen for having used its CPU quota, and for how long. A
// program in such a group stands still for the rest of the period whoever used the quota up:
// frames of tens of ms that are nobody's work, on a machine whose load average looks idle.
struct CpuStalls {
    long long count = 0;
    double ms = 0;
};
// Read from the text of a group's `cpu.stat`.
[[nodiscard]] CpuStalls cpuStallsFrom(std::string_view cpuStat);
// Those of the nearest group above this process that has a quota (Linux, cgroup v2; none where
// there is no quota or no such system). The bench says them beside each case's times.
[[nodiscard]] CpuStalls cpuLimitStalls();
// Instructions the calling thread has run in user mode since its first call here (Linux, where
// the kernel lets a process count its own; 0 elsewhere). Unlike time it does not depend on how
// busy the machine is: the measure to compare two builds by on a loaded machine.
[[nodiscard]] std::uint64_t threadInstructions();
// Heap allocations the calling thread has made since it started. The game's executable counts
// them (platform/alloc_count.cpp replaces operator new there); a program that does not count
// (the tests, sanitizer builds) reports none: allocCounting() says which.
[[nodiscard]] std::uint64_t threadAllocs();
[[nodiscard]] bool allocCounting();
// For the counting operator new only.
void noteAlloc() noexcept;
void enableAllocCounting() noexcept;

} // namespace lc
