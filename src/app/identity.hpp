#pragma once
// The game as the desktop knows it: name, version and application id for SDL, and the window icon.

#include "platform/sdl_ptr.hpp"

#include <array>
#include <filesystem>

namespace lc {

// The pictures under assets/icon/ (icon-<size>.png), drawn by tools/artgen/icon.py.
inline constexpr std::array<int, 8> kIconSizes{16, 24, 32, 48, 64, 128, 256, 512};
// The window icon's size at 100 % display scale; the others up to kIconLargest are its alternates.
inline constexpr int kIconBase = 32;
inline constexpr int kIconLargest = 256;

// Tells SDL the game's name, version and reverse-domain id (the name of the Linux package's
// desktop file, so Wayland and X11 desktops match the window to its launcher and icon). Call
// before SDL_Init; a failure is logged and harmless.
void setAppMetadata();

// The window icon from `dir` (assets/icon): the kIconBase picture carrying the other sizes as
// alternate images, from which SDL picks per display scale and use. Null when the base picture
// cannot be read (logged once); a missing alternate is logged and skipped.
[[nodiscard]] SurfacePtr loadWindowIcon(const std::filesystem::path& dir);

} // namespace lc
