#pragma once
// The game's single seeded random source (SplitMix64), so scripted runs are reproducible.

#include <cstdint>

namespace lc {

class Rng {
public:
    explicit Rng(std::uint64_t seed) : state_(seed) {}

    std::uint64_t next() {
        std::uint64_t z = (state_ += 0x9E3779B97F4A7C15ULL);
        z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL;
        z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL;
        return z ^ (z >> 31);
    }

    // Uniform in [0, 1).
    float uniform() { return static_cast<float>(next() >> 40) * (1.0f / 16777216.0f); }
    float range(float lo, float hi) { return lo + (hi - lo) * uniform(); }
    // Uniform integer in [lo, hi].
    int range(int lo, int hi) {
        const auto span = static_cast<std::uint64_t>(hi - lo) + 1;
        return lo + static_cast<int>(next() % span);
    }
    bool chance(float p) { return uniform() < p; }

private:
    std::uint64_t state_;
};

// Stable per-tile hash for deterministic decoration choices (terrain variants, animation phase).
[[nodiscard]] constexpr std::uint32_t tileHash(int x, int y, std::uint32_t salt = 0) {
    std::uint32_t h = static_cast<std::uint32_t>(x) * 0x8DA6B343u ^
                      static_cast<std::uint32_t>(y) * 0xD8163841u ^ salt * 0xCB1AB31Fu;
    h ^= h >> 13;
    h *= 0x5BD1E995u;
    h ^= h >> 15;
    return h;
}

} // namespace lc
