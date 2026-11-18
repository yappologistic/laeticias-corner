#include "core/speech.hpp"

#include "core/tuning.hpp"

#include <algorithm>

namespace lc {

Speech::Speech(const Catalog& cat, std::uint64_t seed)
    : cat_(&cat), rng_(seed ^ 0x5BEEC4ULL), order_(cat.resident.lines.size()),
      pos_(cat.resident.lines.size(), 0) {}

std::string_view Speech::next(int context) {
    const auto c = static_cast<std::size_t>(context);
    const auto& lines = cat_->resident.lines[c];
    auto& order = order_[c];
    if (order.empty() || pos_[c] >= order.size()) {
        // A fresh shuffle; never start it with the line that ended the last one.
        const int last = order.empty() ? -1 : order.back();
        order.resize(lines.size());
        for (std::size_t i = 0; i < order.size(); ++i) order[i] = static_cast<std::uint8_t>(i);
        for (std::size_t i = order.size(); i > 1; --i)
            std::swap(order[i - 1],
                      order[static_cast<std::size_t>(rng_.range(0, static_cast<int>(i) - 1))]);
        if (order.size() > 1 && order.front() == last) std::swap(order.front(), order.back());
        pos_[c] = 0;
    }
    return lines[order[pos_[c]++]];
}

bool Speech::offer(int context, SpeechWeight weight, double now) {
    if (context < 0 || std::cmp_greater_equal(context, cat_->resident.lines.size())) return false;
    if (!free(weight, now)) return false;
    if (!offerText(next(context), SpeechWeight::Important, now)) return false;
    bubble_.context = context;
    return true;
}

bool Speech::free(SpeechWeight weight, double now) const {
    const bool busy = showing(now) != nullptr;
    if (busy && weight != SpeechWeight::Important) return false;
    // Routine and idle lines also leave a little quiet after the last bubble.
    return busy || weight == SpeechWeight::Important || now - lastEnd_ >= tuning::kBubbleGap;
}

bool Speech::offerText(std::string_view text, SpeechWeight weight, double now) {
    if (text.empty() || !free(weight, now)) return false;
    bubble_.text = text;
    bubble_.start = now;
    bubble_.end =
        now + tuning::kBubbleBase + tuning::kBubblePerChar * static_cast<double>(text.size());
    bubble_.context = -1;
    lastEnd_ = bubble_.end;
    return true;
}

const Bubble* Speech::showing(double now) const {
    return !bubble_.text.empty() && now >= bubble_.start && now < bubble_.end ? &bubble_ : nullptr;
}

float Speech::alpha(double now) const {
    if (showing(now) == nullptr) return 0.0f;
    const double k = std::min(now - bubble_.start, bubble_.end - now) / tuning::kBubbleFade;
    return static_cast<float>(std::clamp(k, 0.0, 1.0));
}

} // namespace lc
