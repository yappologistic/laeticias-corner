#pragma once
// Every user-visible string of the interface (catalog names and blurbs live in the catalog).

#include <string_view>

namespace lc::strings {

inline constexpr std::string_view kTitle = "Laeticia's Corner";
inline constexpr std::string_view kWindowTitle = "Laeticia's Corner";
inline constexpr std::string_view kDefaultWorldName = "Laeticia's Corner";

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
inline constexpr std::string_view kWeatherNatural = "Weather as it comes";
inline constexpr std::string_view kWeatherRain = "Rain here";
inline constexpr std::string_view kWeatherSnow = "Snow here";
inline constexpr std::string_view kWeatherClear = "Clear skies here";
inline constexpr std::string_view kCalendar = "Calendar";
inline constexpr std::string_view kCalendarDay = "{} · day {} of {}";
inline constexpr std::string_view kSeasons = "Seasons";
inline constexpr std::string_view kFollowDays = "Follow the days";
inline constexpr std::string_view kAlwaysSeason = "Always {}"; // season name, lower case
inline constexpr std::string_view kSketchbook = "Sketchbook";
inline constexpr std::string_view kTabWishes = "Wishes";
inline constexpr std::string_view kTabVisitors = "Visitors";
inline constexpr std::string_view kTabNooks = "Nooks";
inline constexpr std::string_view kPagesOf = "{} of {} pages";
inline constexpr std::string_view kMoreUntil = "{} more until {}"; // pages, stage name
inline constexpr std::string_view kAllOpen = "Every part of the map is open";
inline constexpr std::string_view kOpenSection = "Open";
inline constexpr std::string_view kGrantedSection = "Granted";
inline constexpr std::string_view kRarer = "Rarer visitors";
inline constexpr std::string_view kNoteLabel = "{}'s note:"; // the resident's name
inline constexpr std::string_view kHereNow = "Here now";
inline constexpr std::string_view kUnknownNook = "? ? ?";
inline constexpr std::string_view kUndo = "Undo";
inline constexpr std::string_view kRedo = "Redo";
inline constexpr std::string_view kRecentre = "Recentre";
inline constexpr std::string_view kZoomOut = "Zoom out";
inline constexpr std::string_view kZoomIn = "Zoom in";
inline constexpr std::string_view kClose = "Close";
inline constexpr std::string_view kScrollUp = "Previous row";
inline constexpr std::string_view kScrollDown = "Next row";
inline constexpr std::string_view kWishes = "Wishes";
inline constexpr std::string_view kNotNow = "Not now";
inline constexpr std::string_view kWishGranted = "Wish granted";
inline constexpr std::string_view kNewInBuild = "New in Build:";
inline constexpr std::string_view kNewFrame = "New postcard frame: {}";
inline constexpr std::string_view kNoteAdded = "{}'s note added to the sketchbook"; // resident
inline constexpr std::string_view kThanks = "“{}” — {}";     // the thanks line, who says it
inline constexpr std::string_view kWishCount = "{} / {} {}"; // have, need, progress label
inline constexpr std::string_view kWaitNight = "Waiting for nightfall";
inline constexpr std::string_view kWaitDusk = "Waiting for dusk";
inline constexpr std::string_view kWaitDawn = "Waiting for dawn";
inline constexpr std::string_view kWaitDay = "Waiting for daytime";
inline constexpr std::string_view kWaitSeason = "Waiting for {}"; // season name, lower case
inline constexpr std::string_view kWaitRain = "Waiting for rain";
inline constexpr std::string_view kWaitClear = "Waiting for clear skies";
inline constexpr std::string_view kTipLocked = "{} more to discover. Grant wishes to unlock them.";

// Shortcut labels shown in tooltips.
inline constexpr std::string_view kKeyBuild = "B";
inline constexpr std::string_view kKeyRemove = "X";
inline constexpr std::string_view kKeyUndo = "Ctrl+Z";
inline constexpr std::string_view kKeyRedo = "Ctrl+Shift+Z";
inline constexpr std::string_view kKeyRecentre = "Home";
inline constexpr std::string_view kKeyZoomOut = "−";
inline constexpr std::string_view kKeyZoomIn = "+";
inline constexpr std::string_view kKeySound = "M";
inline constexpr std::string_view kKeyPhoto = "P";
inline constexpr std::string_view kKeyClock = "C";
inline constexpr std::string_view kKeyRain = "N";
inline constexpr std::string_view kKeyJournal = "J";
inline constexpr std::string_view kKeyWheel = "Wheel";

inline constexpr std::string_view kPhaseDay = "Day";
inline constexpr std::string_view kPhaseDusk = "Dusk";
inline constexpr std::string_view kPhaseNight = "Night";
inline constexpr std::string_view kPhaseDawn = "Dawn";
inline constexpr std::string_view kPinned = "pinned";
inline constexpr std::string_view kRaining = "raining";
inline constexpr std::string_view kSnowing = "snowing";
inline constexpr std::string_view kSeparator = " · ";

inline constexpr std::string_view kHintPlace = "Click to place · R to rotate · Esc to cancel";
inline constexpr std::string_view kHintPlaceVariant =
    "Click to place · R for another look · Esc to cancel";
inline constexpr std::string_view kHintPlaceFixed = "Click to place · Esc to cancel";
inline constexpr std::string_view kHintPlaceRow = "Click or drag to place · Esc to cancel";
inline constexpr std::string_view kHintPlaceRowVariant =
    "Click or drag to place · R for another look · Esc to cancel";
inline constexpr std::string_view kHintPlaceRowRotate =
    "Click or drag to place · R to rotate · Esc to cancel";
inline constexpr std::string_view kHintPaint = "Click and drag to paint · Esc to cancel";
inline constexpr std::string_view kHintRemove = "Click to remove · Drag to clear · Esc to cancel";
inline constexpr std::string_view kHintPhoto =
    "Frame your photo · Space or click to take it · Esc to return";

inline constexpr std::string_view kWarnOccupied = "Something is already here";
inline constexpr std::string_view kWarnLand = "This needs dry land";
inline constexpr std::string_view kWarnWater = "This needs water";
inline constexpr std::string_view kWarnEdge = "That's past the edge";
inline constexpr std::string_view kWarnPaint = "Can't change the ground under that";
inline constexpr std::string_view kWarnNothing = "Nothing to remove here";
inline constexpr std::string_view kWarnWild = "This land is still wild";

inline constexpr std::string_view kJournalUnknown = "Someone new";
inline constexpr std::string_view kToastNewVisitor = "New visitor: ";
inline constexpr std::string_view kToastNewNook = "New nook: {} · {} of {} pages";
inline constexpr std::string_view kToastNewLand = "New land: {}";
inline constexpr std::string_view kNewLandChip = "New land";
inline constexpr std::string_view kTipWild = "Wild land · opens at {} pages ({} more)";
inline constexpr std::string_view kTipGate = "The road out";
inline constexpr std::string_view kTipRipe = "Ripe · click to pick";
inline constexpr std::string_view kHintRipe = "Ripe beds can be picked. Click one.";
inline constexpr std::string_view kToastPhoto = "Photo saved";
inline constexpr std::string_view kToastPhotoFailed = "Couldn't save the photo";
inline constexpr std::string_view kToastSaveFailed = "Couldn't save your corner; will keep trying";
inline constexpr std::string_view kToastNewerSave =
    "Your world was saved by a newer version of the game. It is left as it is.";
inline constexpr std::string_view kToastWelcome =
    "Welcome back. Laeticia has started a sketchbook: {} pages so far.";
inline constexpr std::string_view kPhotoFile = "laeticias-corner-{:04}.png"; // numbered

// The profiler overlay (F3): numbers over the last seconds of frames.
inline constexpr std::string_view kProfFrame =
    "Frame {:.0f} FPS · avg {:.2f} · p95 {:.2f} · p99 {:.2f} · worst {:.2f} ms";
inline constexpr std::string_view kProfCpu = "CPU avg {:.2f} · p99 {:.2f} · worst {:.2f} ms";
inline constexpr std::string_view kProfGpu = "GPU done avg {:.2f} · p99 {:.2f} · worst {:.2f} ms";
inline constexpr std::string_view kProfGpuOff = "GPU done: not synchronised (--gpu-sync)";
inline constexpr std::string_view kProfSim =
    "Simulation {:.3f} · p99 {:.3f} · conditions {:.3f} ms";
inline constexpr std::string_view kProfScene =
    "Scene {:.3f} · interface {:.3f} · present {:.3f} ms";
inline constexpr std::string_view kProfAudio = "Audio callback load {:.1f}%";
inline constexpr std::string_view kProfDraw = "Draw calls {} · sprites {} drawn, {} culled";
inline constexpr std::string_view kProfActors = "Actors {} live, {} abstract · chunks {} cached";
inline constexpr std::string_view kProfMemory = "Memory: textures {:.0f} MiB · process {:.0f} MiB";
inline constexpr std::string_view kProfWithin = "Within budget: p99 {:.1f} ms, worst {:.1f} ms";
inline constexpr std::string_view kProfOver = "Over budget: p99 {:.1f} ms, worst {:.1f} ms";

} // namespace lc::strings
