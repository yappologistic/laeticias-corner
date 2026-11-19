#pragma once
// The UI's look: palette, spacing grid, sizes (in UI units, multiplied by the UI scale), timing
// and icon codepoints of the bundled Lucide font.

#include <SDL3/SDL.h>

#include <cstdint>

namespace lc::theme {

// Palette: dark smoky glass over the scene, off-white ink and one soft sage accent.
inline constexpr SDL_FColor kInk{0.965f, 0.957f, 0.925f, 1.0f};
inline constexpr SDL_FColor kInkMuted{0.965f, 0.957f, 0.925f, 0.66f};
inline constexpr float kInkDisabled = 0.34f; // alpha factor on disabled icons
inline constexpr SDL_FColor kHover{1.0f, 1.0f, 1.0f, 0.11f};
inline constexpr SDL_FColor kPressed{0.0f, 0.0f, 0.0f, 0.20f};
inline constexpr SDL_FColor kAccent{0.66f, 0.82f, 0.62f, 1.0f};
inline constexpr SDL_FColor kAccentWash{0.60f, 0.78f, 0.56f, 0.26f};
inline constexpr SDL_FColor kAccentRim{0.72f, 0.88f, 0.68f, 0.70f};
inline constexpr SDL_FColor kWarn{1.0f, 0.66f, 0.56f, 1.0f};
inline constexpr SDL_FColor kInset{1.0f, 1.0f, 1.0f, 0.06f};
inline constexpr SDL_FColor kInsetRimTop{1.0f, 1.0f, 1.0f, 0.12f};
inline constexpr SDL_FColor kInsetRimBottom{1.0f, 1.0f, 1.0f, 0.04f};
inline constexpr SDL_FColor kChip{1.0f, 1.0f, 1.0f, 0.12f};
inline constexpr SDL_FColor kDivider{1.0f, 1.0f, 1.0f, 0.12f};
inline constexpr SDL_FColor kFlash{1.0f, 1.0f, 1.0f, 1.0f};
inline constexpr SDL_FColor kCaptionInk{1.0f, 0.98f, 0.93f, 1.0f}; // the era caption over the world
inline constexpr SDL_FColor kCaptionShadow{0.05f, 0.05f, 0.08f, 1.0f};
inline constexpr SDL_FColor kMapDot{0.62f, 0.16f, 0.12f, 1.0f}; // the overview art's ink red
inline constexpr SDL_FColor kMapDotRim{0.98f, 0.95f, 0.86f, 0.9f};
inline constexpr SDL_FColor kMapLight{1.0f, 0.72f, 0.36f, 1.0f}; // a town's lamps after dark
inline constexpr SDL_FColor kMapView{1.0f, 1.0f, 1.0f, 0.55f};
inline constexpr SDL_FColor kTravelVeil{0.93f, 0.89f, 0.80f,
                                        1.0f}; // fast travel fades through paper
inline constexpr SDL_FColor kDotRim{0.06f, 0.08f, 0.07f, 0.7f};
inline constexpr SDL_FColor kSilhouette{0.06f, 0.07f, 0.06f, 0.92f};     // visitors not seen yet
inline constexpr SDL_FColor kSilhouetteBack{0.85f, 0.88f, 0.82f, 0.30f}; // behind a silhouette
inline constexpr SDL_FColor kGold{0.98f, 0.82f, 0.48f, 1.0f}; // wishes: header, ready glow

// The glass material, layered over the blurred scene: a dimmed copy of the blur, a dark green-grey
// tint, a faint top-down sheen, a light rim that is brighter along the top, and a soft shadow.
struct Glass {
    SDL_FColor backdrop; // multiplies the blurred scene
    SDL_FColor tint;
    SDL_FColor sheenTop;
    SDL_FColor sheenBottom;
    SDL_FColor rimTop;
    SDL_FColor rimBottom;
    SDL_FColor shadow;
    float shadowSoftness; // UI units
    float shadowDrop;     // UI units
};
inline constexpr Glass kGlass{
    .backdrop = {0.86f, 0.86f, 0.84f, 1.0f},
    .tint = {0.075f, 0.090f, 0.080f, 0.58f},
    .sheenTop = {1.0f, 1.0f, 1.0f, 0.07f},
    .sheenBottom = {1.0f, 1.0f, 1.0f, 0.0f},
    .rimTop = {1.0f, 1.0f, 1.0f, 0.30f},
    .rimBottom = {1.0f, 1.0f, 1.0f, 0.09f},
    .shadow = {0.02f, 0.03f, 0.02f, 0.22f},
    .shadowSoftness = 14.0f,
    .shadowDrop = 4.0f,
};
// Tooltips float over everything, so they are denser to stay readable over other glass.
inline constexpr Glass kGlassTip{
    .backdrop = {0.85f, 0.85f, 0.83f, 1.0f},
    .tint = {0.070f, 0.082f, 0.075f, 0.72f},
    .sheenTop = {1.0f, 1.0f, 1.0f, 0.06f},
    .sheenBottom = {1.0f, 1.0f, 1.0f, 0.0f},
    .rimTop = {1.0f, 1.0f, 1.0f, 0.24f},
    .rimBottom = {1.0f, 1.0f, 1.0f, 0.08f},
    .shadow = {0.02f, 0.03f, 0.02f, 0.32f},
    .shadowSoftness = 10.0f,
    .shadowDrop = 2.0f,
};
// The veil over the whole world behind the pause menu and dialogs: mostly the blur itself.
inline constexpr Glass kGlassVeil{
    .backdrop = {0.92f, 0.92f, 0.90f, 1.0f},
    .tint = {0.06f, 0.07f, 0.065f, 0.28f},
    .sheenTop = {1.0f, 1.0f, 1.0f, 0.0f},
    .sheenBottom = {1.0f, 1.0f, 1.0f, 0.0f},
    .rimTop = {1.0f, 1.0f, 1.0f, 0.0f},
    .rimBottom = {1.0f, 1.0f, 1.0f, 0.0f},
    .shadow = {0.0f, 0.0f, 0.0f, 0.0f},
    .shadowSoftness = 0.0f,
    .shadowDrop = 0.0f,
};
// Over a bright scene the glass deepens toward these, keeping text contrast high (about 8:1 or
// more over a white backdrop); over a dark scene it stays lighter and more see-through.
inline constexpr float kGlassBrightBackdrop = 0.62f;
inline constexpr float kGlassBrightTint = 0.72f;
// Without a blurred backdrop (render targets unavailable) the glass falls back to this fill.
inline constexpr SDL_FColor kGlassFallback{0.16f, 0.18f, 0.165f, 0.90f};
// Backdrop blur radius (UI units) and the width of light rims.
inline constexpr float kBlurRadius = 18.0f;
inline constexpr float kRim = 1.0f;

// Layout grid (UI units).
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
inline constexpr float kSketchW = 384.0f;
inline constexpr float kPlaceCardW = 360.0f; // a landmark's or figure's card
inline constexpr int kCardLines = 9;
inline constexpr float kCaptionTop = 84.0f; // the era caption, below the title card's band
// The world map.
inline constexpr float kMapHeader = 36.0f;
inline constexpr float kMapReach = 14.0f; // a marker answers the pointer this far away
inline constexpr float kMapHomeDot = 6.0f;
inline constexpr float kMapCityDot = 6.0f;
inline constexpr float kMapTownDot = 3.5f;
inline constexpr float kMapViewRing = 10.0f;
inline constexpr int kRareSectionAfter = 4; // common visitors seen before the rarer ones show
inline constexpr float kTileRadius = 12.0f;
inline constexpr float kBuildExtra = 64.0f; // Build pill width beyond its icon
inline constexpr float kLabelGap = 8.0f;    // icon to label in pill buttons
inline constexpr float kTitlePad = 14.0f;
inline constexpr float kTitleIconGap = 6.0f;
inline constexpr float kTitleMaxW = 300.0f; // a longer world name is cut short with an ellipsis
inline constexpr float kTabExtra = 28.0f;   // tab width beyond its label
inline constexpr float kSlide = 16.0f;      // drawer and journal slide while fading
inline constexpr float kHintPad = 16.0f;
inline constexpr float kHintH = 36.0f;
inline constexpr float kHintSlide = 8.0f;
inline constexpr float kToastPad = 18.0f;
inline constexpr float kToastH = 40.0f;
inline constexpr float kToastIconGap = 10.0f;
inline constexpr float kToastSlide = 12.0f;
inline constexpr float kJournalHeader = 48.0f;
inline constexpr float kJournalIcon = 40.0f;
inline constexpr float kJournalIconPad = 4.0f;
inline constexpr float kJournalTextGap = 12.0f;
inline constexpr float kJournalRowPad = 6.0f;
inline constexpr float kCloseSize = 32.0f;
inline constexpr float kCloseInset = 8.0f;
inline constexpr float kTileInset = 4.0f;
inline constexpr float kThumbTop = 6.0f;
inline constexpr float kTileLabelBottom = 12.0f;
inline constexpr float kTileLift = 2.0f; // hovered thumbnails rise this much
inline constexpr float kTipPad = 10.0f;
inline constexpr float kTipH = 32.0f;
inline constexpr float kTipGap = 10.0f;
inline constexpr float kTipRadius = 10.0f;
// The resident's speech bubble.
inline constexpr float kBubblePad = 12.0f;
inline constexpr float kBubbleMaxW = 230.0f;
inline constexpr float kBubbleRadius = 14.0f;
inline constexpr float kBubbleLift = 6.0f; // above her head
inline constexpr float kBubbleDot = 7.0f;
inline constexpr SDL_FColor kBubbleTrail{0.12f, 0.13f, 0.16f, 0.7f};
inline constexpr float kTipSlide = 4.0f;
inline constexpr float kChipPad = 6.0f;
inline constexpr float kChipGap = 8.0f;
inline constexpr float kChipRadius = 6.0f;
inline constexpr float kDotRadius = 4.0f; // "new" marks
inline constexpr float kTrayW = 300.0f;   // wish tray
inline constexpr float kTrayHeader = 44.0f;
inline constexpr float kCardPad = 12.0f;
inline constexpr float kCardGap = 10.0f;
inline constexpr float kCardSlide = 40.0f; // a card slides in from this far right
inline constexpr float kPortrait = 28.0f;
inline constexpr float kBarW = 64.0f; // count progress
inline constexpr float kBarH = 6.0f;
inline constexpr float kBarGap = 4.0f;
inline constexpr float kRibbonIcon = 28.0f;
inline constexpr float kRibbonMaxW = 560.0f;
inline constexpr float kRibbonMinW = 360.0f;    // narrower bands put it across the top
inline constexpr float kWorldTipOffset = 18.0f; // from the pointer to a world tooltip
// Text is centred on a line by putting its baseline this fraction of the ascent below it.
inline constexpr float kBaselineCentre = 0.36f;

// Type: two text sizes plus the icon size.
inline constexpr float kTextBody = 15.0f;
inline constexpr float kTextTitle = 19.0f;
inline constexpr float kIcon = 20.0f;

// Timing (seconds).
inline constexpr float kTransition = 0.15f;
inline constexpr float kTooltipDelay = 0.45f;
inline constexpr float kToastSeconds = 3.2f;
inline constexpr float kToastQueuedSeconds = 1.6f; // a toast others wait behind shows this long
inline constexpr int kToastQueue = 4; // toasts waiting their turn; more drop the oldest
inline constexpr int kToastLines = 2; // a long toast wraps to this many lines
inline constexpr float kFlashSeconds = 0.35f;
inline constexpr float kRibbonSeconds = 4.0f;
inline constexpr float kCardIn = 0.25f;
inline constexpr float kCardOut = 0.3f;

// UI scale: display density, raised on very large windows so 4K stays readable.
inline constexpr float kReferenceW = 1600.0f;
inline constexpr float kReferenceH = 900.0f;
inline constexpr float kMaxScale = 3.0f;

// The front door's panels (UI units).
inline constexpr float kMenuW = 340.0f;      // title and pause panels
inline constexpr float kMenuButtonH = 44.0f; // their buttons
inline constexpr float kCardW = 208.0f;      // a world card
inline constexpr float kCardThumbH = 120.0f; // its thumbnail (384 x 240 halved, near enough)
inline constexpr float kDialogW = 440.0f;
inline constexpr float kSettingsColW = 380.0f;
inline constexpr float kRowH = 36.0f; // a settings row
inline constexpr float kSliderW = 150.0f;
inline constexpr float kFieldH = 40.0f;
inline constexpr float kPhotoBarH = 44.0f; // the photo bar
inline constexpr float kSliderTrack = 5.0f;
inline constexpr float kBarFadeAfter = 2.0f; // seconds without pointer movement
inline constexpr float kLogoScale = 2.0f;    // the pixel-art logo at this many pixels per pixel

inline constexpr float kPulseSpeed = 4.0f; // the tour's highlight breathes this fast
inline constexpr float kPulseGrow = 4.0f;  // and grows this far (UI units)

// The profiler overlay.
inline constexpr float kProfGraphW = 360.0f;
inline constexpr float kProfGraphH = 72.0f;
inline constexpr float kProfTop = 96.0f; // below the title card

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
inline constexpr char32_t kChevronUp = 0xE070;
inline constexpr char32_t kChevronDown = 0xE06D;
inline constexpr char32_t kChevronLeft = 0xE06E;
inline constexpr char32_t kChevronRight = 0xE06F;
inline constexpr char32_t kLock = 0xE10B;
inline constexpr char32_t kSparkles = 0xE412;
inline constexpr char32_t kSnowflake = 0xE165;
inline constexpr char32_t kLeaf = 0xE2DE;
inline constexpr char32_t kFlower = 0xE2D3;
inline constexpr char32_t kCheck = 0xE06C;
inline constexpr char32_t kMove = 0xE121;
inline constexpr char32_t kPipette = 0xE13B;
inline constexpr char32_t kMenu = 0xE115;
inline constexpr char32_t kMap = 0xE110;
inline constexpr char32_t kLandmark = 0xE23A;
inline constexpr char32_t kSettings = 0xE154;
inline constexpr char32_t kFrame = 0xE291;
inline constexpr char32_t kImage = 0xE0F6;
inline constexpr char32_t kFolderOpen = 0xE247;
inline constexpr char32_t kHeart = 0xE0F2;
inline constexpr char32_t kPencil = 0xE1F9;
inline constexpr char32_t kTrash = 0xE18D;
inline constexpr char32_t kPlay = 0xE13C;
inline constexpr char32_t kType = 0xE198;
inline constexpr char32_t kEyeOff = 0xE0BB;
inline constexpr char32_t kArrowLeft = 0xE048;
inline constexpr char32_t kLogOut = 0xE10E;
inline constexpr char32_t kAll[] = {
    kPlus,         kMinus,   kEraser,   kSoundOn,   kSoundOff,  kCamera,      kClockAuto,
    kSun,          kSunset,  kSunrise,  kMoon,      kRain,      kJournal,     kUndo,
    kRedo,         kHome,    kClose,    kSparkle,   kChevronUp, kChevronDown, kChevronLeft,
    kChevronRight, kLock,    kSparkles, kSnowflake, kLeaf,      kFlower,      kCheck,
    kMove,         kPipette, kMenu,     kSettings,  kFrame,     kImage,       kFolderOpen,
    kHeart,        kPencil,  kTrash,    kPlay,      kType,      kEyeOff,      kArrowLeft,
    kLogOut,       kMap,     kLandmark};
} // namespace icon

} // namespace lc::theme
