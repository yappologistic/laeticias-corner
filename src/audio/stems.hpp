#pragma once
// Arithmetic of music that grows: stems share one master sample position, a newly unlocked stem
// waits for the next bar line and fades in over a few bars (docs/design/living-corner.md R8.2).

#include <algorithm>
#include <cstdint>

namespace lc {

// The first bar line at or after `pos` (positions and bars in samples).
[[nodiscard]] constexpr std::uint64_t nextBar(std::uint64_t pos, std::uint64_t bar) {
    return bar == 0 ? pos : (pos + bar - 1) / bar * bar;
}

// Level of a stem fading in from `start` over `length` samples, at `pos`.
[[nodiscard]] constexpr float fadeLevel(std::uint64_t pos, std::uint64_t start,
                                        std::uint64_t length) {
    if (pos <= start) return 0.0f;
    if (length == 0 || pos >= start + length) return 1.0f;
    return static_cast<float>(pos - start) / static_cast<float>(length);
}

// Where a stem of `length` samples must be to play in step with the master position.
[[nodiscard]] constexpr std::uint64_t loopOffset(std::uint64_t master, std::uint64_t length) {
    return length == 0 ? 0 : master % length;
}

} // namespace lc
