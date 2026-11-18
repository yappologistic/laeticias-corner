#pragma once
// Every user-visible string of the interface (catalog names and blurbs live in the catalog).

#include <string_view>

namespace lc::strings {

inline constexpr std::string_view kTitle = "Laeticia's Corner";
inline constexpr std::string_view kWindowTitle = "Laeticia's Corner";

inline constexpr std::string_view kBuild = "Build";
inline constexpr std::string_view kRemove = "Remove";
inline constexpr std::string_view kMove = "Move";
inline constexpr std::string_view kBuildTip = "Build · Alt-click to copy";
inline constexpr std::string_view kMoveTip = "Move · Alt-click to copy";
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
inline constexpr std::string_view kNoteLabel = "{}'s note:";   // the resident's name
inline constexpr std::string_view kNoteLabelAlone = "A note:"; // nobody lives there
inline constexpr std::string_view kHereNow = "Here now";
inline constexpr std::string_view kUnknownNook = "? ? ?";
inline constexpr std::string_view kUndo = "Undo";
inline constexpr std::string_view kRedo = "Redo";
inline constexpr std::string_view kRecentre = "Recentre";
inline constexpr std::string_view kZoomOut = "Zoom out";
inline constexpr std::string_view kZoomIn = "Zoom in";
inline constexpr std::string_view kClose = "Close";
// The world (docs/design/world-tech.md §4).
inline constexpr std::string_view kMap = "Map";
inline constexpr std::string_view kWorldsLand = "This land belongs to the world";
inline constexpr std::string_view kAwayHint = "The tools rest here: Home returns to the corner";
inline constexpr std::string_view kSeamLine =
    "Each land here is remembered as it was in one moment. The sea keeps the years apart.";
inline constexpr std::string_view kMapTitle = "The world";
inline constexpr std::string_view kMapHint = "Click a place to travel there";
inline constexpr std::string_view kMapHome = "Home";
inline constexpr std::string_view kJournalFound = "{} of {} found";
inline constexpr std::string_view kProfMissing = "Missing art  {} placeholders in view, {} ids";
inline constexpr std::string_view kScrollUp = "Previous row";
inline constexpr std::string_view kScrollDown = "Next row";
inline constexpr std::string_view kWishes = "Wishes";
inline constexpr std::string_view kNotNow = "Not now";
inline constexpr std::string_view kWishGranted = "Wish granted";
inline constexpr std::string_view kNewInBuild = "New in Build:";
inline constexpr std::string_view kNewFrame = "New postcard frame: {}";
inline constexpr std::string_view kNoteAdded = "{}'s note added to the sketchbook"; // resident
inline constexpr std::string_view kNoteAddedAlone = "A note added to the sketchbook";
inline constexpr std::string_view kThanks = "“{}” — {}";     // the thanks line, who says it
inline constexpr std::string_view kThanksAlone = "“{}”";     // nobody to sign it
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
inline constexpr std::string_view kKeyMove = "V";
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
inline constexpr std::string_view kKeyMap = "M";
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
inline constexpr std::string_view kHintPlaceRow =
    "Click or drag to place · Esc to cancel · Shift-drag for a straight line";
inline constexpr std::string_view kHintPlaceRowVariant =
    "Click or drag to place · R for another look · Esc to cancel · Shift-drag for a straight line";
inline constexpr std::string_view kHintPlaceRowRotate =
    "Click or drag to place · R to rotate · Esc to cancel · Shift-drag for a straight line";
inline constexpr std::string_view kHintPaintBrush = "Brush {}×{} · Click and drag to paint · [ ] "
                                                    "brush size · Shift-drag for a rectangle · "
                                                    "Esc to cancel";
inline constexpr std::string_view kHintRemove =
    "Click to remove · Shift-drag to clear an area · Esc to cancel";
inline constexpr std::string_view kHintMovePick = "Click something to pick it up · Esc to cancel";
inline constexpr std::string_view kHintMoveCarry =
    "Click to put it down · R to rotate · Esc to put it back";
inline constexpr std::string_view kHintPipette = "Click something to copy it · Esc to cancel";

inline constexpr std::string_view kWarnOccupied = "Something is already here";
inline constexpr std::string_view kWarnLand = "This needs dry land";
inline constexpr std::string_view kWarnWater = "This needs water";
inline constexpr std::string_view kWarnEdge = "That's past the edge";
inline constexpr std::string_view kWarnPaint = "Can't change the ground under that";
inline constexpr std::string_view kWarnNothing = "Nothing to remove here";
inline constexpr std::string_view kWarnWild = "This land is still wild";
inline constexpr std::string_view kWarnLocked = "Not unlocked yet";
inline constexpr std::string_view kWarnNothingToPick = "Nothing to pick up here";

inline constexpr std::string_view kJournalUnknown = "Someone new";
inline constexpr std::string_view kToastNewVisitor = "New visitor: ";
inline constexpr std::string_view kToastNewNook = "New nook: {} · {} of {} pages";
inline constexpr std::string_view kToastNewLand = "New land: {}";
inline constexpr std::string_view kNewLandChip = "New land";
inline constexpr std::string_view kTipWild = "Wild land · opens at {} pages ({} more)";
inline constexpr std::string_view kTipGate = "The road out";
inline constexpr std::string_view kTipRipe = "Ripe · click to pick";
inline constexpr std::string_view kHintRipe = "Ripe beds can be picked. Click one.";
inline constexpr std::string_view kToastSaveFailed = "Couldn't save your corner; will keep trying";
inline constexpr std::string_view kToastNotOpened =
    "Your world couldn't be opened, so it is left as it is. This is a fresh corner.";
inline constexpr std::string_view kToastWelcome =
    "Welcome back. {} has started a sketchbook: {} pages so far."; // the resident, pages
inline constexpr std::string_view kToastWelcomeAlone =
    "Welcome back. There is a sketchbook now: {} pages so far.";

inline constexpr std::string_view kBenchmarkTitle = "Laeticia's Corner benchmark";
inline constexpr std::string_view kBenchmarkClose = "Press any key or click to close.";

// The front door (docs/design/living-corner.md §6.5–6.10).
inline constexpr std::string_view kDefaultWorldOf = "{}'s Corner";  // the resident's name
inline constexpr std::string_view kDefaultWorldAlone = "My Corner"; // when nobody lives there
inline constexpr std::string_view kContinue = "Continue · {}";
inline constexpr std::string_view kBegin = "Begin";
inline constexpr std::string_view kWorldsButton = "Worlds";
inline constexpr std::string_view kSettings = "Settings";
inline constexpr std::string_view kQuit = "Quit";
inline constexpr std::string_view kYourWorlds = "Your worlds";
inline constexpr std::string_view kNewWorld = "New world";
inline constexpr std::string_view kPlay = "Play";
inline constexpr std::string_view kRename = "Rename";
inline constexpr std::string_view kDelete = "Delete";
inline constexpr std::string_view kBack = "Back";
inline constexpr std::string_view kKeyEsc = "Esc";
inline constexpr std::string_view kWorldDetail = "{}, day {} · {} pages"; // season, day, pages
inline constexpr std::string_view kWorldDetailOne = "{}, day {} · {} page";
inline constexpr std::string_view kCannotOpen = "Can't be opened here";
inline constexpr std::string_view kCouldNotOpen = "This world couldn't be opened";
inline constexpr std::string_view kCouldNotOpenText =
    "Its file is left exactly as it was. It may come from a newer version of the game.";
inline constexpr std::string_view kNameYourWorld = "Name your world";
inline constexpr std::string_view kFreeBuild = "Free build";
inline constexpr std::string_view kFreeBuildText = "Everything unlocked and all land open from "
                                                   "the start. Wishes still come, just for the "
                                                   "company.";
inline constexpr std::string_view kCreate = "Create";
inline constexpr std::string_view kCancel = "Cancel";
inline constexpr std::string_view kNameEmpty = "Give it a name first";
inline constexpr std::string_view kNameTaken = "You already have a world with that name";
inline constexpr std::string_view kNameTooLong = "At most 28 letters";
inline constexpr std::string_view kLetterMissing = "That letter isn't in the game's font yet";
inline constexpr std::string_view kDeleteTitle = "Delete “{}”?";
inline constexpr std::string_view kDeleteText = "The whole world goes, corner and all. Its "
                                                "postcards stay where they are. This can't be "
                                                "undone.";
inline constexpr std::string_view kKeepIt = "Keep it";
inline constexpr std::string_view kPaused = "Paused";
inline constexpr std::string_view kResume = "Resume";
inline constexpr std::string_view kOpenPostcards = "Open postcards folder";
inline constexpr std::string_view kBackToWorlds = "Back to worlds";
inline constexpr std::string_view kMenu = "Menu";
inline constexpr std::string_view kSound = "Sound";
inline constexpr std::string_view kMusic = "Music";
inline constexpr std::string_view kEffects = "Effects";
inline constexpr std::string_view kAmbience = "Ambience";
inline constexpr std::string_view kMuteAll = "Mute all";
inline constexpr std::string_view kDisplay = "Display";
inline constexpr std::string_view kFullscreen = "Fullscreen";
inline constexpr std::string_view kInterfaceSize = "Interface size";
inline constexpr std::string_view kAuto = "Auto";
inline constexpr std::string_view kPercent = "{}%";
inline constexpr std::string_view kReduceMotion = "Reduce motion";
inline constexpr std::string_view kShowGrid = "Show grid";
inline constexpr std::string_view kVsync = "Wait for the display";
inline constexpr std::string_view kChatter = "Chatter";
inline constexpr std::string_view kChatty = "Chatty";
inline constexpr std::string_view kQuiet = "Quiet";
inline constexpr std::string_view kHelp = "Help";
inline constexpr std::string_view kTourSetting = "First-minute tour";
inline constexpr std::string_view kReplay = "Replay";
inline constexpr std::string_view kDone = "Done";
inline constexpr std::string_view kOn = "on";
inline constexpr std::string_view kOff = "off";
inline constexpr std::string_view kKeyMute = "Ctrl+M";
inline constexpr std::string_view kKeyFullscreen = "F11";
inline constexpr std::string_view kKeyGrid = "G";
// The first-minute tour (R10.5).
inline constexpr std::string_view kTourLook = "Drag to look around.";
inline constexpr std::string_view kTourBuild = "Open Build to plant something.";
inline constexpr std::string_view kTourPlant = "Pick the {}, then click the ground."; // piece
inline constexpr std::string_view kTourWish = "{} has a wish. Granting it unlocks new pieces.";
inline constexpr std::string_view kTourWishAlone = "A wish has come. Granting it unlocks new "
                                                   "pieces.";
inline constexpr std::string_view kTourKeys = "Ctrl+Z undoes anything. J opens the sketchbook.";
inline constexpr std::string_view kTourEnd = "That's all. Make yourself at home.";
inline constexpr std::string_view kSkipTour = "Skip tour";
// The photo bar (§6.8) and postcards (R12).
inline constexpr std::string_view kFrameLabel = "Frame: {}";
inline constexpr std::string_view kCaption = "Caption";
inline constexpr std::string_view kHideBar = "Hide bar";
inline constexpr std::string_view kTakePostcard = "Take postcard";
inline constexpr std::string_view kOpenFolder = "Open folder";
inline constexpr std::string_view kClosePhoto = "Close";
inline constexpr std::string_view kKeyFrame = "F";
inline constexpr std::string_view kKeyCaption = "T";
inline constexpr std::string_view kKeyHideBar = "H";
inline constexpr std::string_view kKeyTake = "Space";
inline constexpr std::string_view kPostcardSaved = "Postcard saved";
inline constexpr std::string_view kPostcardFailed = "Couldn't save the postcard";
inline constexpr std::string_view kPostcardDate =
    "{}, day {} · {} {} {}"; // season, day, d, month, y
inline constexpr std::string_view kMonths[] = {"January",   "February", "March",    "April",
                                               "May",       "June",     "July",     "August",
                                               "September", "October",  "November", "December"};

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
inline constexpr std::string_view kProfMemory =
    "Memory: textures {:.0f} MiB (pages {:.0f} of {:.0f}) · process {:.0f} MiB";
inline constexpr std::string_view kProfWithin = "Within budget: p99 {:.1f} ms, worst {:.1f} ms";
inline constexpr std::string_view kProfOver = "Over budget: p99 {:.1f} ms, worst {:.1f} ms";

} // namespace lc::strings
