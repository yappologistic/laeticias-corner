#pragma once
// The liveliness rule of thumb as a measurement (docs/design/living-world.md §1.1): samples of
// how many things move with purpose in view, and how many new happenings the last minute
// brought, checked against an area's minimum and cap. Too quiet fails, and so does too busy.

#include <algorithm>
#include <array>
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
    LivelyProbe() { happenings_.reserve(kMaxHappenings); }
    void happening(double now) {
        if (happenings_.size() < kMaxHappenings) happenings_.push_back(now);
    }
    // One sample: purposeful movers in view now; happenings counted over the last minute. The
    // last kMaxSamples are kept (a fixed ring: a whole session never grows it, Q3-11).
    void sample(int movers, double now) {
        std::erase_if(happenings_, [&](double t) { return now - t > kWindow; });
        samples_[next_] = {movers, static_cast<int>(happenings_.size()), now};
        next_ = (next_ + 1) % kMaxSamples;
        count_ = std::min(count_ + 1, kMaxSamples);
    }
    void reset() {
        count_ = next_ = 0;
        happenings_.clear();
    }
    // Movers within [minMovers, capMovers]; happenings at most capHappenings per minute and,
    // once a minute has been sampled, at least minHappenings.
    [[nodiscard]] LivelyReport check(int minMovers, int capMovers, int minHappenings,
                                     int capHappenings) const {
        LivelyReport r;
        if (count_ == 0) return r;
        const std::size_t oldest = (next_ + kMaxSamples - count_) % kMaxSamples;
        const double first = samples_[oldest].at;
        r.moversMin = samples_[oldest].movers;
        for (std::size_t k = 0; k < count_; ++k) {
            const Sample& s = samples_[(oldest + k) % kMaxSamples];
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
    static constexpr std::size_t kMaxSamples = 900;   // fifteen minutes at one a second
    static constexpr std::size_t kMaxHappenings = 64; // in a minute: far past any cap
    struct Sample {
        int movers = 0;
        int happenings = 0;
        double at = 0;
    };
    std::array<Sample, kMaxSamples> samples_{};
    std::size_t next_ = 0;
    std::size_t count_ = 0;
    std::vector<double> happenings_;
};

} // namespace lc
