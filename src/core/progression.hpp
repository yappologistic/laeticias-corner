#pragma once
// The rules of the progress loop over a world's Progress (docs/design/living-corner.md R1, R3, R5,
// R7): conditions are re-evaluated when something changes, wishes are offered at a gentle pace
// and granted once their goal holds, and what happens comes back as events. Pure logic: the
// caller supplies the world, the facts and the play clock.

#include "core/catalog.hpp"
#include "core/condition.hpp"
#include "core/progress.hpp"
#include "core/world.hpp"

#include <cstdint>
#include <span>
#include <vector>

namespace lc {

struct ProgressEvent {
    enum class Kind : std::uint8_t { WishOffered, WishGranted };
    Kind kind = Kind::WishOffered;
    int index = 0;        // wish
    bool already = false; // WishOffered: its goal already held, so it is granted shortly
};

// What a wish card shows besides its text.
struct WishStatus {
    bool ready = false; // the goal holds; granted once the hold is over
    int count = -1;     // a top-level count goal: how many there are (-1: no readout)
    int min = 0;        // and how many it needs
    int waiting = -1;   // condition node of the time, season or weather term it waits for
};

class Progression {
public:
    explicit Progression(const Catalog& cat);

    // Re-evaluates everything that depends on the world or the facts (call after a change).
    void evaluate(const World& world, Progress& p, const CondFacts& facts, double played);
    // Call every simulation step. Wishes are offered at most once a second while `offering`
    // (not paused, not framing a photo); grants happen whenever their hold is over.
    void tick(const World& world, Progress& p, const CondFacts& facts, double played,
              bool offering);
    // "Not now": the wish leaves the tray and may come back after a while.
    void snooze(int wish, Progress& p, double played);

    [[nodiscard]] std::span<const ProgressEvent> events() const { return events_; }
    void clearEvents() { events_.clear(); }
    [[nodiscard]] const WishStatus& status(int wish) const {
        return status_[static_cast<std::size_t>(wish)];
    }
    // Whether a wish could be offered now (exposed for tests and the sketchbook).
    [[nodiscard]] bool offerable(int wish, const World& world, const Progress& p,
                                 const CondFacts& facts, double played) const;

private:
    void offer(const World& world, Progress& p, const CondFacts& facts, double played);
    void grant(int wish, Progress& p, double played);
    void refresh(int wish, const World& world, const CondFacts& facts, double played);

    const Catalog& cat_;
    std::vector<double> trueSince_; // per wish: play time its goal began to hold, -1: false
    std::vector<double> grantAt_;   // per wish: an offered wish already met, granted then
    std::vector<WishStatus> status_;
    std::vector<ProgressEvent> events_;
    double nextOffer_ = 0; // play time of the next pacing check
};

} // namespace lc
