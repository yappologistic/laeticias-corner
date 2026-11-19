#include "worldview/page_runs.hpp"

#include <algorithm>
#include <cmath>

namespace lc::worldview {

void PageRuns::begin(FRect window) {
    window_ = window;
    cols_ = std::max(1, static_cast<int>(std::ceil((window.x1 - window.x0) / kCell)));
    rows_ = std::max(1, static_cast<int>(std::ceil((window.y1 - window.y0) / kCell)));
    last_.assign(static_cast<std::size_t>(cols_) * static_cast<std::size_t>(rows_), -1);
    runs_.clear();
    latest_.clear();
    next_.clear();
    order_.clear();
}

bool PageRuns::add(std::uint32_t key, const FRect& box) {
    if (!box.overlaps(window_)) return false;
    const auto cell = [](float v, float from, int n) {
        return std::clamp(static_cast<int>(std::floor((v - from) / kCell)), 0, n - 1);
    };
    const int cx0 = cell(box.x0, window_.x0, cols_);
    const int cx1 = cell(box.x1, window_.x0, cols_);
    const int cy0 = cell(box.y0, window_.y0, rows_);
    const int cy1 = cell(box.y1, window_.y0, rows_);
    // The last run that drew where this sprite draws: it may not go before that one.
    int after = -1;
    for (int y = cy0; y <= cy1; ++y) {
        const int* row =
            last_.data() + static_cast<std::size_t>(y) * static_cast<std::size_t>(cols_);
        for (int x = cx0; x <= cx1; ++x) after = std::max(after, row[x]);
    }
    auto mine = std::ranges::find(latest_, key, &Latest::key);
    if (mine == latest_.end()) mine = latest_.insert(latest_.end(), Latest{key, -1});
    if (mine->run < after || mine->run < 0) {
        mine->run = static_cast<int>(runs_.size());
        runs_.push_back({key, kEnd, kEnd});
    }
    const int run = mine->run;
    const auto entry = static_cast<std::uint32_t>(next_.size());
    next_.push_back(kEnd);
    Run& r = runs_[static_cast<std::size_t>(run)];
    if (r.tail == kEnd)
        r.head = entry;
    else
        next_[r.tail] = entry;
    r.tail = entry;
    for (int y = cy0; y <= cy1; ++y) {
        int* row = last_.data() + static_cast<std::size_t>(y) * static_cast<std::size_t>(cols_);
        for (int x = cx0; x <= cx1; ++x) row[x] = std::max(row[x], run);
    }
    return true;
}

std::span<const std::uint32_t> PageRuns::order() {
    order_.clear();
    for (const Run& r : runs_)
        for (std::uint32_t e = r.head; e != kEnd; e = next_[e]) order_.push_back(e);
    return order_;
}

} // namespace lc::worldview
