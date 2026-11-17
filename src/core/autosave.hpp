#pragma once
// When to autosave: after a quiet moment, at the latest after a stretch of continuous editing,
// never mid-drag unless overdue, and not again too soon after a failed attempt.

#include "core/tuning.hpp"

#include <algorithm>

namespace lc {

class AutosaveClock {
public:
    void changed() {
        dirty_ = true;
        quiet_ = 0;
    }
    // Advances time; true when a save should be attempted now.
    [[nodiscard]] bool due(double dt, bool dragging) {
        retry_ = std::max(0.0, retry_ - dt);
        if (!dirty_) return false;
        quiet_ += dt;
        unsaved_ += dt;
        const bool quiet = quiet_ >= tuning::kAutosaveDelay && !dragging;
        const bool overdue = unsaved_ >= tuning::kAutosaveMaxDelay;
        return (quiet || overdue) && retry_ <= 0;
    }
    void saved() {
        dirty_ = false;
        unsaved_ = 0;
    }
    void failed() { retry_ = tuning::kSaveRetrySeconds; }
    [[nodiscard]] bool dirty() const { return dirty_; }

private:
    bool dirty_ = false;
    double quiet_ = 0;   // since the last change
    double unsaved_ = 0; // since the first change not yet saved
    double retry_ = 0;   // until another attempt after a failure
};

} // namespace lc
