#pragma once
// Counts by 64-bit key in a fixed open-addressing table: no allocation after construction, O(1)
// add, remove and lookup (linear probing, backward-shift deletion). The actors' reservations use
// it so that "is this seat taken?" never scans every reservation.

#include <cstdint>
#include <vector>

namespace lc {

class FlatCount {
public:
    // `capacity` is rounded up to a power of two and must exceed the keys held at once.
    explicit FlatCount(std::size_t capacity) {
        std::size_t n = 16;
        while (n < capacity) n <<= 1;
        keys_.assign(n, 0);
        counts_.assign(n, 0);
    }
    [[nodiscard]] int get(std::uint64_t key) const {
        for (std::size_t i = home(key);; i = (i + 1) & mask()) {
            if (keys_[i] == 0) return 0;
            if (keys_[i] == key) return counts_[i];
        }
    }
    void add(std::uint64_t key) {
        std::size_t i = home(key);
        while (keys_[i] != 0 && keys_[i] != key) i = (i + 1) & mask();
        keys_[i] = key;
        ++counts_[i];
    }
    void remove(std::uint64_t key) {
        std::size_t i = home(key);
        while (keys_[i] != key) {
            if (keys_[i] == 0) return;
            i = (i + 1) & mask();
        }
        if (--counts_[i] > 0) return;
        for (std::size_t j = i;;) {
            keys_[i] = 0;
            counts_[i] = 0;
            for (;;) {
                j = (j + 1) & mask();
                if (keys_[j] == 0) return;
                const std::size_t h = home(keys_[j]);
                if (i <= j ? (i < h && h <= j) : (i < h || h <= j)) continue;
                break;
            }
            keys_[i] = keys_[j];
            counts_[i] = counts_[j];
            i = j;
        }
    }
    void clear() {
        std::fill(keys_.begin(), keys_.end(), 0);
        std::fill(counts_.begin(), counts_.end(), 0);
    }

private:
    [[nodiscard]] std::size_t mask() const { return keys_.size() - 1; }
    [[nodiscard]] std::size_t home(std::uint64_t k) const {
        k ^= k >> 33;
        k *= 0xFF51AFD7ED558CCDULL;
        k ^= k >> 33;
        return static_cast<std::size_t>(k) & mask();
    }
    std::vector<std::uint64_t> keys_; // 0: empty (keys are made never to be 0)
    std::vector<int> counts_;
};

} // namespace lc
