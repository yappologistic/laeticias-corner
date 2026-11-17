#pragma once
// Tuned placement notes: each placement plays one note of a ten-note pentatonic set, chosen by a
// walker that makes quick building sound like a short phrase landing on a cadence
// (docs/design/living-corner.md R8.3).

#include "core/rng.hpp"

namespace lc {

class PhraseWalker {
public:
    // The note (0..kNotes-1) for a placement at play time `now`.
    int next(double now, Rng& rng);

    static constexpr int kNotes = 10;

private:
    int idx_ = 0;
    int dir_ = 1;
    int len_ = 0;
    int phraseLen_ = 0;
    double last_ = -1e9;
};

} // namespace lc
