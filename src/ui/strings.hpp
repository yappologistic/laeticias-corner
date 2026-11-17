#pragma once
// Every user-visible string of the interface (catalog names and blurbs live in the catalog).

#include <string_view>

namespace lc::strings {

inline constexpr std::string_view kTitle = "Laeticia's Corner";
inline constexpr std::string_view kWindowTitle = "Laeticia's Corner";

inline constexpr std::string_view kBuild = "Build";
inline constexpr std::string_view kRemove = "Remove";
inline constexpr std::string_view kSoundOn = "Sound on";
inline constexpr std::string_view kSoundOff = "Sound off";
inline constexpr std::string_view kPhoto = "Photo mode";
inline constexpr std::string_view kClockAuto = "Clock: follows the day";
inline constexpr std::string_view kClockDay = "Clock: pinned to day";
inline constexpr std::string_view kClockDusk = "Clock: pinned to dusk";
inline constexpr std::string_view kClockNight = "Clock: pinned to night";
inline constexpr std::string_view kClockDawn = "Clock: pinned to dawn";
inline constexpr std::string_view kRainOn = "Rain";
inline constexpr std::string_view kRainOff = "Rain";
inline constexpr std::string_view kJournal = "Visitors";
inline constexpr std::string_view kUndo = "Undo";
inline constexpr std::string_view kRedo = "Redo";
inline constexpr std::string_view kRecentre = "Recentre";
inline constexpr std::string_view kZoomOut = "Zoom out";
inline constexpr std::string_view kZoomIn = "Zoom in";
inline constexpr std::string_view kClose = "Close";

inline constexpr std::string_view kPhaseDay = "Day";
inline constexpr std::string_view kPhaseDusk = "Dusk";
inline constexpr std::string_view kPhaseNight = "Night";
inline constexpr std::string_view kPhaseDawn = "Dawn";
inline constexpr std::string_view kPinned = "pinned";
inline constexpr std::string_view kRaining = "raining";
inline constexpr std::string_view kSeparator = " · ";

inline constexpr std::string_view kHintPlace = "Click to place · R to rotate · Esc to cancel";
inline constexpr std::string_view kHintPlaceVariant =
    "Click to place · R for another look · Esc to cancel";
inline constexpr std::string_view kHintPlaceFixed = "Click to place · Esc to cancel";
inline constexpr std::string_view kHintDrag = " · Drag to place a row";
inline constexpr std::string_view kHintPaint = "Click and drag to paint · Esc to cancel";
inline constexpr std::string_view kHintRemove = "Click to remove · Drag to clear · Esc to cancel";
inline constexpr std::string_view kHintPhoto = "Photo saved · P or Esc to return";

inline constexpr std::string_view kWarnOccupied = "Something is already here";
inline constexpr std::string_view kWarnLand = "This needs dry land";
inline constexpr std::string_view kWarnWater = "This needs water";
inline constexpr std::string_view kWarnEdge = "That's past the edge";
inline constexpr std::string_view kWarnPaint = "Can't change the ground under that";
inline constexpr std::string_view kWarnNothing = "Nothing to remove here";

inline constexpr std::string_view kJournalEmpty = "Not seen yet";
inline constexpr std::string_view kJournalUnknown = "? ? ?";
inline constexpr std::string_view kToastNewVisitor = "New visitor: ";
inline constexpr std::string_view kToastPhoto = "Photo saved";
inline constexpr std::string_view kToastPhotoFailed = "Couldn't save the photo";

} // namespace lc::strings
