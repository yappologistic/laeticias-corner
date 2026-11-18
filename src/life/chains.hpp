#pragma once
// Chains of goods (docs/design/living-world.md §3, W5) exactly as tools/worldgen's simulator
// (worldgen/lifesim.py) runs them: one tick per real second, slots and hands of at most three,
// a source making one unit per period while its slot has room, transforms of one input into one
// output, carriers walking the path-graph distance at their speed and back, sinks using one unit
// at a time. The engine runs every region's chains this way all the time, seen or not, so the
// stacks and the carriers are where the formula says when the camera arrives; live actors only
// show that state (they never change it), so activating an area cannot make it drift.
//
// Clock: tick n is n real seconds after day 0 06:00 (lifesim starts its day at 06:00). Long jumps
// use the chains' daily cycle: the state at each 06:00 is kept until it repeats, after which any
// day's state is looked up. A chain bound to an event starts each day empty (its event days are
// not periodic).

#include "life/data.hpp"
#include "life/paths.hpp"

#include <cstdint>
#include <string>
#include <vector>

namespace lc::life {

// Where a chain's slot reference is: the graph node lifesim uses for distances, and the tile
// and placed item an actor works at.
struct ChainPlace {
    int node = -1;        // region graph node (citylife label), -1: unreachable
    int item = -1;        // map item index, -1 for node references
    TilePos tile{-1, -1}; // where a worker stands
    int slot = -1;        // the WorldSlot drawn with the stack, -1 when none (beside, node)
};

struct ChainStats {
    long work = 0;
    long starve = 0;
    long block = 0;
    long done = 0;
};

enum class WorkerPhase : std::uint8_t { Idle, Out, Back, Work };

struct ChainWorker {
    double t = 0;
    WorkerPhase phase = WorkerPhase::Idle;
    int hand = 0;
    friend bool operator==(const ChainWorker&, const ChainWorker&) = default;
};

class ChainRun {
public:
    // Resolves the stages' places (errors listed when a place cannot be found or reached).
    ChainRun(const LifeData& data, const LifeRegion& region, const Chain& chain,
             const world::WorldMap& map, const RegionPaths& paths);

    [[nodiscard]] bool ok() const { return errors_.empty(); }
    [[nodiscard]] const std::vector<std::string>& errors() const { return errors_; }
    [[nodiscard]] const Chain& chain() const { return *chain_; }

    // One second at tick `t`. `on`: inside the chain's hours (and season and event, in the
    // engine). Returns false when a counter left 0..3 (an error is recorded).
    bool tick(long t, bool on);
    [[nodiscard]] bool hoursOn(long t) const;

    // State.
    struct Counter {
        std::string ref;
        int goods = -1;
        int count = 0;
    };
    [[nodiscard]] const std::vector<Counter>& counters() const { return counters_; }
    [[nodiscard]] const std::vector<ChainWorker>& workers() const { return workers_; }
    // Stage of each worker, and the first worker of each stage.
    [[nodiscard]] int stageOf(std::size_t worker) const { return workerStage_[worker]; }
    [[nodiscard]] const std::vector<ChainStats>& stats() const { return stats_; }
    [[nodiscard]] const std::vector<long>& perDay() const { return perDay_; }
    [[nodiscard]] long made() const { return made_; }
    [[nodiscard]] double travel(std::size_t stage) const { return travel_[stage]; }
    [[nodiscard]] const ChainPlace& place(const std::string& ref) const;
    // Completions this tick, per stage (goods changing hands: happenings, chain events).
    [[nodiscard]] const std::vector<std::uint8_t>& doneNow() const { return doneNow_; }
    void resetStats() { stats_.assign(stats_.size(), {}); }
    void setDays(int days) { perDay_.assign(static_cast<std::size_t>(days), 0); }

    struct Snapshot {
        std::vector<int> counts;
        std::vector<ChainWorker> workers;
        long made = 0;
        friend bool operator==(const Snapshot&, const Snapshot&) = default;
    };
    [[nodiscard]] Snapshot snapshot() const;
    void restore(const Snapshot& s);
    void clear();

private:
    int counter(const std::string& ref, int goods);

    const Chain* chain_;
    std::vector<std::string> errors_;
    std::vector<std::pair<std::string, ChainPlace>> places_;
    std::vector<Counter> counters_;
    // Per stage: counter indices (carry: from, to; transform: in, out; source and sink: slot).
    std::vector<std::pair<int, int>> keys_;
    std::vector<double> travel_;
    std::vector<ChainWorker> workers_;
    std::vector<int> workerStage_;
    std::vector<ChainStats> stats_;
    std::vector<long> perDay_;
    std::vector<std::uint8_t> doneNow_;
    long made_ = 0;
};

// Every region's chains on the world clock, with the daily-cycle fast-forward.
class Chains {
public:
    Chains(const LifeData& data, const world::WorldMap& map, std::vector<RegionPaths>& paths,
           const std::vector<int>& pathsOfRegion);

    // Brings every chain to tick floor(seconds since day 0 06:00). `running(region, event)`
    // says whether an event runs (event-bound chains).
    template <typename Running>
    void advanceTo(double seconds, int season, Running&& running);

    [[nodiscard]] std::size_t size() const { return runs_.size(); }
    [[nodiscard]] const ChainRun& run(std::size_t i) const { return runs_[i]; }
    [[nodiscard]] int regionOf(std::size_t i) const { return region_[i]; }
    [[nodiscard]] long tick() const { return tick_; }
    // Chains whose completions of the last advance should raise chain events: (chain, stage).
    [[nodiscard]] const std::vector<std::pair<int, int>>& completions() const { return done_; }
    [[nodiscard]] std::size_t memoryBytes() const;
    [[nodiscard]] std::vector<std::string> problems() const;

private:
    void dayStart(std::size_t i, long day);
    [[nodiscard]] bool gated(std::size_t i) const;

    const LifeData* data_;
    std::vector<ChainRun> runs_;
    std::vector<int> region_;
    std::vector<int> regionChain_; // chain index inside its region
    // Per chain: the state at 06:00 of each day until the cycle is found, and the cycle.
    std::vector<std::vector<ChainRun::Snapshot>> days_;
    std::vector<int> cycleStart_; // -1 until found
    std::vector<int> cycleLen_;
    long tick_ = -1;
    std::vector<std::pair<int, int>> done_;
};

template <typename Running>
void Chains::advanceTo(double seconds, int season, Running&& running) {
    constexpr long kDay = 720;
    const long target = static_cast<long>(seconds);
    done_.clear();
    if (target < 0) return;
    if (tick_ < 0 || target < tick_ || target - tick_ > kDay) {
        // A jump (or the first call): every chain from its state at this day's 06:00.
        const long day = target / kDay;
        for (std::size_t i = 0; i < runs_.size(); ++i) dayStart(i, day);
        tick_ = day * kDay;
    }
    for (; tick_ < target; ++tick_) {
        if (tick_ % kDay == 0)
            for (std::size_t i = 0; i < runs_.size(); ++i) dayStart(i, tick_ / kDay);
        for (std::size_t i = 0; i < runs_.size(); ++i) {
            ChainRun& r = runs_[i];
            if (!r.ok()) continue;
            const Chain& c = r.chain();
            bool on = r.hoursOn(tick_);
            if (c.seasons != 0 && (c.seasons & (1u << season)) == 0) on = false;
            if (c.event >= 0 && !running(region_[i], c.event)) on = false;
            r.tick(tick_, on);
            for (std::size_t s = 0; s < r.doneNow().size(); ++s)
                if (r.doneNow()[s] != 0 && done_.size() < 64)
                    done_.emplace_back(static_cast<int>(i), static_cast<int>(s));
        }
    }
}

} // namespace lc::life
