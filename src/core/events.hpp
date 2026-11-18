#pragma once
// The event scheduler (docs/design/living-world.md §5): the corner's moments of delight from the
// catalog's `events`, started by their triggers (random windows, hours of the day, rain starting
// and stopping, placements, conditions, cooking, a new season), with cooldowns, once-a-day
// limits and the rule that scheduled events start at most once per kEventSpacing seconds (a
// deferred one waits, it is never dropped). Random windows come from a stream per event derived
// from the seed, so the same run always brings the same moments. Pure logic: no SDL.

#include "core/catalog.hpp"
#include "core/condition.hpp"
#include "core/iso.hpp"

#include <cstdint>
#include <span>
#include <vector>

namespace lc {

class World;

struct EventEnv {
    const World* world = nullptr;
    CondFacts facts; // `raining` is the weather at the view
    Phase phase = Phase::Day;
    int season = 0;
    int day = 0;
    float hour = 12;
    bool seasonDawn = false; // the first dawn of a season began this step
    double now = 0;          // simulation seconds
};

struct FiredEvent {
    int event = 0;      // catalog event
    Vec2 at{-1, -1};    // where it happens (tiles), when it has a place
    bool pulse = false; // a repeat inside a running event (another croak)
};

class EventScheduler {
public:
    EventScheduler(const Catalog& cat, std::uint64_t seed);

    void update(const EventEnv& env, float dt);
    // A placement, move or removal over `rect` (player triggers).
    void placed(const World& world, TileRect rect, double now);
    // The resident cooked a harvest.
    void cooked(double now);

    // What started or pulsed during the last update (and the triggers since).
    [[nodiscard]] std::span<const FiredEvent> fired() const { return fired_; }
    void clearFired() { fired_.clear(); }
    [[nodiscard]] bool active(EventShow show) const;
    // The largest gain among running events of this show (1 when none).
    [[nodiscard]] float gain(EventShow show) const;
    // How far through a running event of this show is, 0..1, or -1 when none runs.
    [[nodiscard]] float progress(EventShow show, double now) const;

private:
    struct Running {
        int event;
        double start;
        double end;
        double nextPulse;
    };
    void start(int e, double now, Vec2 at);
    [[nodiscard]] double gap(int e);
    [[nodiscard]] bool filters(const EventDef& d, const EventEnv& env) const;
    [[nodiscard]] double duration(int e);

    const Catalog* cat_; // a pointer, so a fresh one can be assigned when another world opens
    std::uint64_t seed_;
    std::vector<double> due_;          // window events: when the next one is due
    std::vector<double> last_;         // when each last started
    std::vector<int> lastDay_;         // the calendar day each last started (daily ones)
    std::vector<std::uint32_t> drawn_; // draws made from each event's stream
    std::vector<Running> running_;
    std::vector<FiredEvent> fired_;
    double lastScheduled_ = -1e9; // the last start of a scheduled (window) event
    bool wasRaining_ = false;
    double rainSince_ = 0;
    double rainEnded_ = -1e9;
};

} // namespace lc
