#include "app/window_state.hpp"

#include <nlohmann/json.hpp>

#include <algorithm>

namespace lc {

WindowRect defaultWindow(WindowRect usable) {
    const int w = std::max(std::min(kWindowMinW, usable.w),
                           static_cast<int>(static_cast<float>(usable.w) * kWindowFill));
    const int h = std::max(std::min(kWindowMinH, usable.h),
                           static_cast<int>(static_cast<float>(usable.h) * kWindowFill));
    return {usable.x + (usable.w - w) / 2, usable.y + (usable.h - h) / 2, w, h};
}

std::optional<WindowRect> restoreWindow(WindowRect saved, std::span<const WindowRect> usable) {
    if (saved.w < kWindowMinW / 2 || saved.h < kWindowMinH / 2) return std::nullopt;
    for (const WindowRect& d : usable) {
        // In 64 bits: a remembered rectangle is never trusted to stay far from INT_MAX.
        using L = long long;
        const L ox = std::min(L{saved.x} + saved.w, L{d.x} + d.w) - std::max(L{saved.x}, L{d.x});
        const L oy = std::min(L{saved.y} + saved.h, L{d.y} + d.h) - std::max(L{saved.y}, L{d.y});
        // Most of the window (including its title area) must be on this display.
        if (ox * 2 < saved.w || oy * 2 < saved.h || saved.y < d.y) continue;
        WindowRect r = saved;
        r.w = std::min(r.w, d.w);
        r.h = std::min(r.h, d.h);
        r.x = std::clamp(r.x, d.x, d.x + d.w - r.w);
        r.y = std::clamp(r.y, d.y, d.y + d.h - r.h);
        return r;
    }
    return std::nullopt;
}

std::optional<WindowState> parseWindowState(std::string_view text) {
    try {
        const auto j = nlohmann::json::parse(text);
        // Whole numbers no display could be far from: a hand-edited or damaged file never feeds
        // a float cast or an overflowing sum (restoreWindow adds positions and sizes).
        const auto field = [&](const char* key, long long lo, long long hi) -> std::optional<int> {
            const auto& v = j.at(key);
            if (!v.is_number_integer()) return std::nullopt;
            // A parsed positive number is unsigned: one past 2^63 must not wrap to negative.
            const long long n = v.is_number_unsigned() && v.get<unsigned long long>() > 1ULL << 62
                                    ? hi + 1
                                    : v.get<long long>();
            if (n < lo || n > hi) return std::nullopt;
            return static_cast<int>(n);
        };
        const auto x = field("x", -kWindowCoordMax, kWindowCoordMax);
        const auto y = field("y", -kWindowCoordMax, kWindowCoordMax);
        const auto w = field("w", 1, kWindowCoordMax);
        const auto h = field("h", 1, kWindowCoordMax);
        if (!x || !y || !w || !h) return std::nullopt;
        WindowState s;
        s.windowed = {*x, *y, *w, *h};
        s.fullscreen = j.value("fullscreen", false);
        return s;
    } catch (const nlohmann::json::exception&) {
        return std::nullopt;
    }
}

std::string serializeWindowState(const WindowState& s) {
    const nlohmann::json j = {{"x", s.windowed.x},
                              {"y", s.windowed.y},
                              {"w", s.windowed.w},
                              {"h", s.windowed.h},
                              {"fullscreen", s.fullscreen}};
    return j.dump(1);
}

} // namespace lc
