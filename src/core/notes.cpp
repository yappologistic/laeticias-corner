#include "core/notes.hpp"

#include "core/tuning.hpp"

#include <array>
#include <cstdlib>

namespace lc {
namespace {

constexpr std::array<int, 3> kStarts{0, 2, 3};      // D4, F#4, A4
constexpr std::array<int, 4> kCadences{0, 3, 5, 8}; // D4, A4, D5, A5

} // namespace

int PhraseWalker::next(double now, Rng& rng) {
    if (now - last_ > tuning::kNotePhraseReset) {
        // A fresh phrase after a pause.
        idx_ = kStarts[static_cast<std::size_t>(rng.range(0, 2))];
        dir_ = 1;
        len_ = 0;
        phraseLen_ = rng.range(4, 6);
    } else if (len_ >= phraseLen_) {
        // Cadence: land on the nearest D or A in the walking direction (or nearest at all).
        int best = -1;
        for (const int c : kCadences)
            if ((dir_ > 0 ? c >= idx_ : c <= idx_) &&
                (best < 0 || std::abs(c - idx_) < std::abs(best - idx_)))
                best = c;
        if (best < 0)
            for (const int c : kCadences)
                if (best < 0 || std::abs(c - idx_) < std::abs(best - idx_)) best = c;
        idx_ = best;
        len_ = 0;
        phraseLen_ = rng.range(4, 6);
    } else {
        if (rng.chance(tuning::kNoteTurnChance)) dir_ = -dir_;
        idx_ += dir_ * (rng.range(0, 3) == 3 ? 2 : 1);
        if (idx_ < 0 || idx_ >= kNotes) {
            dir_ = -dir_;
            idx_ = idx_ < 0 ? -idx_ : 2 * (kNotes - 1) - idx_;
        }
    }
    ++len_;
    last_ = now;
    return idx_;
}

} // namespace lc
