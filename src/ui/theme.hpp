#pragma once
// The UI's look: palette, spacing grid, sizes (in UI units, multiplied by the UI scale), timing
// and icon codepoints of the bundled Lucide font.

#include <SDL3/SDL.h>

#include <cstdint>

namespace lc::theme {

// Palette: warm paper panels with dark cocoa ink and a muted teal accent.
inline constexpr SDL_FColor kPanel{0.984f, 0.961f, 0.918f, 0.90f};
inline constexpr SDL_FColor kPanelSolid{0.984f, 0.961f, 0.918f, 0.97f};
inline constexpr SDL_FColor kShadow{0.10f, 0.07f, 0.05f, 0.22f};
inline constexpr SDL_FColor kInk{0.24f, 0.19f, 0.17f, 1.0f};
inline constexpr SDL_FColor kInkMuted{0.24f, 0.19f, 0.17f, 0.58f};
inline constexpr SDL_FColor kHover{0.24f, 0.19f, 0.17f, 0.08f};
inline constexpr SDL_FColor kPressed{0.24f, 0.19f, 0.17f, 0.16f};
inline constexpr SDL_FColor kAccent{0.29f, 0.53f, 0.50f, 1.0f};
inline constexpr SDL_FColor kOnAccent{0.99f, 0.98f, 0.95f, 1.0f};
inline constexpr SDL_FColor kWarn{0.76f, 0.33f, 0.24f, 1.0f};
inline constexpr SDL_FColor kDivider{0.24f, 0.19f, 0.17f, 0.12f};
inline constexpr SDL_FColor kTileBack{0.24f, 0.19f, 0.17f, 0.05f};
inline constexpr SDL_FColor kFlash{1.0f, 1.0f, 1.0f, 1.0f};

// Layout grid (UI units).
inline constexpr float kUnit = 8.0f;
inline constexpr float kMargin = 16.0f;
inline constexpr float kGap = 8.0f;
inline constexpr float kButton = 40.0f;
inline constexpr float kDockPad = 4.0f;
inline constexpr float kPanelRadius = 16.0f;
inline constexpr float kPanelPad = 16.0f;
inline constexpr float kTileW = 88.0f;
inline constexpr float kTileH = 96.0f;
inline constexpr float kThumb = 56.0f;
inline constexpr int kDrawerMaxCols = 8;
inline constexpr int kDrawerRows = 2;
inline constexpr float kTabH = 32.0f;
inline constexpr float kJournalW = 320.0f;
inline constexpr float kJournalRow = 56.0f;
inline constexpr float kShadowSoftness = 12.0f;

// Type: two text sizes plus the icon size.
inline constexpr float kTextBody = 15.0f;
inline constexpr float kTextTitle = 19.0f;
inline constexpr float kIcon = 20.0f;

// Timing (seconds).
inline constexpr float kTransition = 0.15f;
inline constexpr float kTooltipDelay = 0.45f;
inline constexpr float kToastSeconds = 3.2f;
inline constexpr float kFlashSeconds = 0.35f;

// UI scale: display density, raised on very large windows so 4K stays readable.
inline constexpr float kReferenceW = 1600.0f;
inline constexpr float kReferenceH = 900.0f;
inline constexpr float kMaxScale = 3.0f;

namespace icon {
inline constexpr char32_t kPlus = 0xE13D;
inline constexpr char32_t kMinus = 0xE11C;
inline constexpr char32_t kEraser = 0xE28F;
inline constexpr char32_t kSoundOn = 0xE1AB;
inline constexpr char32_t kSoundOff = 0xE1AC;
inline constexpr char32_t kCamera = 0xE064;
inline constexpr char32_t kClockAuto = 0xE2B2; // sun-moon
inline constexpr char32_t kSun = 0xE178;
inline constexpr char32_t kSunset = 0xE17A;
inline constexpr char32_t kSunrise = 0xE179;
inline constexpr char32_t kMoon = 0xE11E;
inline constexpr char32_t kRain = 0xE08E;
inline constexpr char32_t kJournal = 0xE05F;
inline constexpr char32_t kUndo = 0xE2A1;
inline constexpr char32_t kRedo = 0xE2A0;
inline constexpr char32_t kHome = 0xE0F5;
inline constexpr char32_t kClose = 0xE1B2;
inline constexpr char32_t kSparkle = 0xE47E;
inline constexpr char32_t kAll[] = {kPlus,      kMinus, kEraser, kSoundOn, kSoundOff, kCamera,
                                    kClockAuto, kSun,   kSunset, kSunrise, kMoon,     kRain,
                                    kJournal,   kUndo,  kRedo,   kHome,    kClose,    kSparkle};
} // namespace icon

} // namespace lc::theme
