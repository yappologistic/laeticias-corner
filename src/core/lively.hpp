#pragma once
// The liveliness rule of thumb as a measurement (docs/design/living-world.md §1.1): samples of
// how many things move with purpose in view, and how many new happenings the last minute
// brought, checked against an area's minimum and cap. Too quiet fails, and so does too busy.

#include <algorithm>
#include <cstddef>
#include <vector>

namespace lc {

struct LivelyReport {
    int samples = 0;
    int quiet = 0; // samples under a minimum
    int busy = 0;  // samples over a cap
    int moversMin = 0;
    int moversMax = 0;
    int happeningsMax = 0;
    [[nodiscard]] float share() const {
        return samples == 0
                   ? 0.0f
                   : static_cast<float>(samples - quiet - busy) / static_cast<float>(samples);
    }
};

class LivelyProbe {
public:
    void happening(double now) { happenings_.push_back(now); }
    // One sample: purposeful movers in view now; happenings counted over the last minute.
    void sample(int movers, double now) {
        std::erase_if(happenings_, [&](double t) { return now - t > kWindow; });
        samples_.push_back({movers, static_cast<int>(happenings_.size()), now});
    }
    void reset() {
        samples_.clear();
        happenings_.clear();
    }
    // Movers within [minMovers, capMovers]; happenings at most capHappenings per minute and,
    // once a minute has been sampled, at least minHappenings.
    [[nodiscard]] LivelyReport check(int minMovers, int capMovers, int minHappenings,
                                     int capHappenings) const {
        LivelyReport r;
        if (samples_.empty()) return r;
        const double first = samples_.front().at;
        r.moversMin = samples_.front().movers;
        for (const Sample& s : samples_) {
            ++r.samples;
            r.moversMin = std::min(r.moversMin, s.movers);
            r.moversMax = std::max(r.moversMax, s.movers);
            r.happeningsMax = std::max(r.happeningsMax, s.happenings);
            const bool minuteIn = s.at - first >= kWindow;
            if (s.movers > capMovers || s.happenings > capHappenings)
                ++r.busy;
            else if (s.movers < minMovers || (minuteIn && s.happenings < minHappenings))
                ++r.quiet;
        }
        return r;
    }

private:
    static constexpr double kWindow = 60.0;
    struct Sample {
        int movers;
        int happenings;
        double at;
    };
    std::vector<Sample> samples_;
    std::vector<double> happenings_;
};

} // namespace lc
