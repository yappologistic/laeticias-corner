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
        const int ox = std::min(saved.x + saved.w, d.x + d.w) - std::max(saved.x, d.x);
        const int oy = std::min(saved.y + saved.h, d.y + d.h) - std::max(saved.y, d.y);
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
        WindowState s;
        s.windowed = {j.at("x").get<int>(), j.at("y").get<int>(), j.at("w").get<int>(),
                      j.at("h").get<int>()};
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
