#pragma once
// Runs of one texture page out of a painter's-order stream of sprites. Two sprites whose
// drawings do not meet may be drawn in either order, so a sprite joins the last run of its page
// unless something it would be drawn over came after that run: a city whose pages alternate
// in depth at every other sprite then draws in a few runs instead of a draw call per change.
// Pure logic (no SDL).

#include "core/iso.hpp"

#include <cstdint>
#include <span>
#include <vector>

namespace lc::worldview {

class PageRuns {
public:
    // A new stream over a window of target px (the boxes given later are in the same px).
    void begin(FRect window);
    // The next sprite in painter's order: what it is drawn with (page, blending: any number)
    // and the box its pixels stay within. False when the box misses the window (nothing of it
    // would be drawn: it gets no entry); otherwise it is entry count() - 1.
    bool add(std::uint32_t key, const FRect& box);
    // The entries in the order to draw them: run by run, each run in the order it was given.
    [[nodiscard]] std::span<const std::uint32_t> order();
    // The same as order() last gave it (for a report afterwards).
    [[nodiscard]] std::span<const std::uint32_t> drawn() const { return order_; }
    [[nodiscard]] std::uint32_t count() const { return static_cast<std::uint32_t>(next_.size()); }
    [[nodiscard]] int runs() const { return static_cast<int>(runs_.size()); }

private:
    static constexpr int kCell = 32; // px: how finely "do they meet" is asked
    static constexpr std::uint32_t kEnd = 0xFFFFFFFFu;
    struct Run {
        std::uint32_t key = 0;
        std::uint32_t head = kEnd;
        std::uint32_t tail = kEnd;
    };
    struct Latest {
        std::uint32_t key = 0;
        int run = -1;
    };

    FRect window_;
    int cols_ = 0;
    int rows_ = 0;
    std::vector<int> last_; // per grid cell: the last run that drew into it, -1 none
    std::vector<Run> runs_;
    std::vector<Latest> latest_;      // per key seen: its last run (a handful of keys)
    std::vector<std::uint32_t> next_; // per entry: the next of its run
    std::vector<std::uint32_t> order_;
};

} // namespace lc::worldview
