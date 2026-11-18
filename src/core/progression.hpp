#pragma once
// The rules of the progress loop over a world's Progress (docs/design/living-corner.md R1, R3, R5,
// R7): conditions are re-evaluated when something changes, wishes are offered at a gentle pace
// and granted once their goal holds, and what happens comes back as events. Pure logic: the
// caller supplies the world, the facts and the play clock.

#include "core/catalog.hpp"
#include "core/condition.hpp"
#include "core/progress.hpp"
#include "core/rng.hpp"
#include "core/world.hpp"

#include <cstdint>
#include <span>
#include <vector>

namespace lc {

struct ProgressEvent {
    enum class Kind : std::uint8_t { WishOffered, WishGranted, NookFound, StageOpens };
    Kind kind = Kind::WishOffered;
    int index = 0;        // wish, nook or land stage
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
    // (not paused, not framing a photo); grants happen whenever their hold is over; rare
    // visitors' timings advance.
    void tick(const World& world, Progress& p, const CondFacts& facts, double played, bool offering,
              Rng& rng);
    // "Not now": the wish leaves the tray and may come back after a while.
    void snooze(int wish, Progress& p, double played);

    [[nodiscard]] std::span<const ProgressEvent> events() const { return events_; }
    void clearEvents() { events_.clear(); }
    [[nodiscard]] const WishStatus& status(int wish) const {
        return status_[static_cast<std::size_t>(wish)];
    }
    // Per nook: an instance exists now (recomputed by evaluate).
    [[nodiscard]] std::span<const std::uint8_t> nookHere() const { return nookHere_; }
    // Extra visitors nooks allow (their `cap` effects), per visitor.
    [[nodiscard]] int extraVisitors(int visitor) const;
    // A rare visitor may be here now: its recipe has held long enough and its visit is on.
    [[nodiscard]] bool rareHere(int visitor) const {
        return rare_[static_cast<std::size_t>(visitor)].here;
    }
    // Growth multiplier nooks give a bed whose footprint is `rect`.
    [[nodiscard]] float nookGrowth(const World& world, TileRect rect) const;
    // Whether a wish could be offered now (exposed for tests and the sketchbook).
    [[nodiscard]] bool offerable(int wish, const World& world, const Progress& p,
                                 const CondFacts& facts, double played) const;

private:
    // A rare visitor's comings and goings (docs/design/living-corner.md R3.2).
    struct Rare {
        bool holds = false; // recipe and season allow it now
        double since = -1;  // play time the recipe began to hold
        double delay = 0;   // how long it must hold before the visitor comes
        bool here = false;
        double stay = 0;       // length of this visit
        double leaves = 0;     // play time the visit ends (counted from the first sighting)
        double awayUntil = -1; // after a visit it stays away a while
    };
    void tickRare(const CondFacts& facts, double played, Rng& rng);
    [[nodiscard]] int rareRate(int visitor) const;
    void offer(const World& world, Progress& p, const CondFacts& facts, double played);
    void settleClues(Progress& p, const CondFacts& facts);
    void grant(int wish, Progress& p, double played);
    void refresh(int wish, const World& world, const CondFacts& facts, double played);

    const Catalog& cat_;
    std::vector<double> trueSince_; // per wish: play time its goal began to hold, -1: false
    std::vector<double> grantAt_;   // per wish: an offered wish already met, granted then
    std::vector<WishStatus> status_;
    std::vector<ProgressEvent> events_;
    std::vector<std::uint8_t> nookHere_;
    std::vector<Rare> rare_;
    mutable std::vector<NearInstance> instances_; // scratch for area lookups
    double nextOffer_ = 0;                        // play time of the next pacing check
    double stageReady_ = 0;                       // stages reached together open this far apart
};

} // namespace lc
