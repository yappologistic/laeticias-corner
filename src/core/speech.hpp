#pragma once
// The resident's speech bubbles (docs/design/living-corner.md R6.6): one at a time, shown for a
// time that grows with the line, each context's lines in a shuffled order so none repeats until
// the others have been said, and paced so she is never chatty. Pure logic: no SDL.

#include "core/catalog.hpp"
#include "core/rng.hpp"

#include <cstdint>
#include <string_view>
#include <vector>

namespace lc {

// How much a line matters: an important one may cut in on a bubble already showing.
enum class SpeechWeight : std::uint8_t { Idle, Routine, Important };

struct Bubble {
    std::string_view text;
    double start = 0;
    double end = 0;
    int context = -1; // -1: a line from elsewhere (a stage's, a season's)
};

class Speech {
public:
    Speech(const Catalog& cat, std::uint64_t seed);

    // Offers a line of `context` at time `now`. Returns true when it is shown (the caller plays
    // a murmur). Routine and idle lines wait for a quiet moment instead of interrupting.
    bool offer(int context, SpeechWeight weight, double now);
    // The same for a line that is not one of her contexts (a land stage's, a season's).
    bool offerText(std::string_view text, SpeechWeight weight, double now);
    // The bubble showing at `now`, if any.
    [[nodiscard]] const Bubble* showing(double now) const;
    // 0..1 visibility of the current bubble (it fades in and out).
    [[nodiscard]] float alpha(double now) const;
    // The next line of a context (no repeats until every line of it was used).
    std::string_view next(int context);

private:
    [[nodiscard]] bool free(SpeechWeight weight, double now) const;

    const Catalog* cat_; // a pointer, so a fresh one can be assigned when another world opens
    Rng rng_;
    std::vector<std::vector<std::uint8_t>> order_;
    std::vector<std::uint8_t> pos_;
    Bubble bubble_;
    double lastEnd_ = -1e9;
};

} // namespace lc
