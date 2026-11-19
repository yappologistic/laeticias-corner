#pragma once
// What several sound systems want of the mixer's loops in one update, combined before it reaches
// the mixer: one file named by two systems (a region's bed and an event's ambience) is one loop,
// and the louder want wins with its pan. Neither may silence the other, and the loop is never
// louder than either system meant (they ask for the same sound, not for two of it).

#include <cstddef>
#include <vector>

namespace lc {

class LoopWants {
public:
    struct Want {
        float gain = 0;
        float pan = 0;
    };
    // Starts an update over `loops` mixer loops (no allocation once sized).
    void begin(std::size_t loops) {
        if (wants_.size() != loops) {
            wants_.assign(loops, {});
            wanted_.assign(loops, 0);
            touched_.reserve(loops);
        }
        for (const int l : touched_) {
            wants_[static_cast<std::size_t>(l)] = {};
            wanted_[static_cast<std::size_t>(l)] = 0;
        }
        touched_.clear();
    }
    void want(int loop, float gain, float pan) {
        if (loop < 0 || static_cast<std::size_t>(loop) >= wants_.size()) return;
        const auto i = static_cast<std::size_t>(loop);
        if (wanted_[i] == 0) {
            wanted_[i] = 1;
            touched_.push_back(loop);
            wants_[i] = {gain, pan};
        } else if (gain > wants_[i].gain) {
            wants_[i] = {gain, pan};
        }
    }
    // f(loop, want) for every loop wanted this update, once each.
    template <typename F>
    void forEach(F&& f) const {
        for (const int l : touched_) f(l, wants_[static_cast<std::size_t>(l)]);
    }

private:
    std::vector<Want> wants_;
    std::vector<char> wanted_; // per loop: wanted this update
    std::vector<int> touched_;
};

} // namespace lc
