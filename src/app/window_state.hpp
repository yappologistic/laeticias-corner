#pragma once
// Where the game window opens: remembered between runs (size, position, fullscreen), or sized to
// a comfortable part of the display it opens on. Pure logic plus a tiny JSON file.

#include <filesystem>
#include <optional>
#include <span>
#include <string>
#include <string_view>

namespace lc {

struct WindowRect {
    int x = 0;
    int y = 0;
    int w = 0;
    int h = 0;
    friend bool operator==(const WindowRect&, const WindowRect&) = default;
};

struct WindowState {
    WindowRect windowed; // size and place while not fullscreen
    bool fullscreen = false;
};

// A window covering kWindowFill of the usable area, centred in it.
[[nodiscard]] WindowRect defaultWindow(WindowRect usable);
// The remembered window when it still fits mostly on one of `usable` displays (shrunk to fit if
// that display got smaller); nullopt when no display shows enough of it.
[[nodiscard]] std::optional<WindowRect> restoreWindow(WindowRect saved,
                                                      std::span<const WindowRect> usable);

[[nodiscard]] std::optional<WindowState> parseWindowState(std::string_view json);
[[nodiscard]] std::string serializeWindowState(const WindowState& s);

inline constexpr std::string_view kWindowFile = "window.json";
inline constexpr float kWindowFill = 0.8f;
inline constexpr int kWindowMinW = 640;
inline constexpr int kWindowMinH = 400;

} // namespace lc
