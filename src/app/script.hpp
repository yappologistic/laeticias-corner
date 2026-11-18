#pragma once
// Input scripts for headless runs. They drive the game through synthesized SDL events, the same
// path real input takes. One command per line; '#' starts a comment line.
//
// Points (one token):  X,Y      window pixels
//                      @TX,TY   centre of map tile (TX, TY) under the current camera
//                      ui:NAME  centre of a UI widget: build, remove, sound, photo, clock, rain,
//                               journal (the sketchbook), journal_close, undo, redo, recentre,
//                               zoom_out, zoom_in, tray, card:N, not_now, sketch:wishes|visitors|
//                               nooks, sketch_not_now, calendar, season_auto|spring|summer|
//                               autumn|winter, edge_chip,
//                               scroll_up, scroll_down, tab:<category id>, tile:<item or terrain
//                               id>, or of the toast and hint panels: toast, hint
//                  actor:KIND   the middle of the first actor of that kind in the window (a
//                               visitor id or the resident's); none in view fails the run
//                  grid:TX,TY   the middle of world grid tile (TX, TY), raised by its level
//                  map:REGION   that place's marker on the open map
//                  landmark:ID  the middle of the first placed item with that id (world set)
//                  figure:ID    the middle of that named figure where it stands
//                  ui:menu:NAME the front door's widgets: continue (also Begin), worlds, settings,
//                               quit, back, new, card:N, play:N, rename:N, delete:N, field,
//                               freebuild, cancel, create, keep, confirm_delete, error_back,
//                               music, effects, ambience, mute, fullscreen, ui_scale,
//                               reduce_motion, grid, vsync, chatty, quiet, replay, done, resume,
//                               pause_settings, postcards, back_to_worlds, pause_quit, skip_tour,
//                               frame_prev, frame_next, caption, hide_bar, take, folder,
//                               close_photo
//
// Commands:
//   move P                  pointer motion
//   click P [right|middle]  press and release (left button unless "right" or "middle")
//   drag P1 P2 [right|middle]  press at P1, move to P2 over 8 frames, release
//   press P [right|middle]  move to P and press the button (hold it)
//   release P [right|middle]  move to P and release the button
//   key COMBO               e.g. r, escape, ctrl+z, ctrl+shift+z, alt+x, home, f3, f11, equals,
//                           minus, space
//   keydown COMBO           press (and hold) a key, e.g. keydown d, keydown ctrl
//   keyup COMBO             release a held key
//   wheel DY [P]            scroll (positive = away from the user), optionally at P
//   wait N                  let N frames pass
//   shot FILE.png           save the current frame (relative to the working directory)
//   set clock PHASE|auto    pin the clock to day/dusk/night/dawn instantly, or unpin
//   set rain on|off         rain here, or the weather as it comes
//   set weather natural|rain|clear
//   set time T              the time of day, 0..1 (0.2 mid-morning, 0.55 dusk, 0.75 midnight)
//   set chatter chatty|quiet   the resident's idle remarks
//   set camera TX TY ZOOM   look at tile (TX, TY) at a zoom level (0.25, 0.5, 1, 2, 3)
//   set world TX TY ZOOM    the same at a world grid tile (a jump: themes and places snap);
//   set world PLACE ZOOM    or at a place: forum, agora, terrace, layer:node,
//                           district:<region>/<id> (city life's foci)
//   set look KIND ZOOM      look at the first actor of that kind, a named figure, or a
//                           landmark:ID (the first placed)
//   set lively reset        start a fresh liveliness record (see expect lively)
//   set shower now          a shower enters at the upwind edge of the open land
//   set unlock all          unlock every piece, frame and clue (as a free-build world has)
//   set played [+]SECONDS   move the play clock on (wish pacing and the like) without frames:
//                           to SECONDS (never backwards), or by them with a +
//   set land N              open land stages up to N at once, with their reveals
//   set season ID|auto      keep a season (as the calendar's pin does), or follow the days
//   set day N               the calendar day (the season follows unless pinned)
//   set grow SECONDS        let the beds grow that much play time at once
//   set wish ID open        offer that wish now (it joins the tray even past three)
//   set city F|off          city life (src/life/): load the world and keep the active area
//                           round F (x,y | layer:node | forum | agora | terrace |
//                           district:<region>/<name>), stepped with the game's clock
//   set city_dump FILE      write a life dump of the area (relative to the working directory)
//   waitfor N WHAT ARGS...  wait up to N frames until `expect WHAT ARGS...` holds, else fail
//   fast S [WHAT ARGS...]   simulate S seconds without drawing (or until `expect WHAT ARGS...`
//                           holds, failing if it never does); state checks only; an audio
//                           capture keeps recording through it
//   expect WHAT ARGS...     fail the run unless the state matches:
//       tile P TERRAIN | item P ITEM|none | count ITEM|all N | tool none|place|paint|remove|move
//       drawer open|closed | journal open|closed | photo on|off | phase PHASE | profiler yes|no
//       grid yes|no | footprints yes|no (Tab held) | carrying yes|no (a piece being moved)
//       brush N | pipette yes|no
//       page none|title|worlds|newworld|delete|loaderror|settings|pause (the menus' top page)
//       tour N (its step, 0: none) | onboarded yes|no | worlds N (on the worlds screen)
//       world NAME... (the open world's name) | fresh yes|no (an unbegun preview)
//       card N NAME... (the N-th world on the worlds screen, newest first)
//       volume music|effects|ambience N | reduce_motion yes|no | ui_scale N | vsync yes|no
//       frame ID (the postcard frame) | caption yes|no | postcards N (files in its folder)
//       seen VISITOR [yes|no] | undo yes|no | redo yes|no | photos N | muted yes|no | rain on|off
//       present VISITOR N (how many are on the map now) | habitat ok (every critter stands
//       where it may) | saved yes|no (a save file exists) | zoom 0.25|0.5|1|2|3
//       toast yes|no (a toast is showing) | toast WORDS... (the toast showing contains them)
//       | toast not WORDS... (it does not); tip and thanks likewise for the name beside the
//       pointer and the granted wish's thanks | portrait N yes|no (the N-th open wish card
//       shows a portrait)
//       panning yes|no (a pan key is held)
//       file PATH yes|no (PATH, relative to the save directory, exists)
//       widget NAME yes|no (the widget is laid out now; also card:N, the N-th wish card)
//       wish ID open|done|waiting | wishes N (open now) | ribbon yes|no (a wish was granted)
//       sketch wishes|visitors|nooks (the sketchbook's open tab) | nook ID yes|no (found)
//       stage N (highest open land stage) | season ID (the effective season) | day N
//       growth P STAGE (growth stage of the item at P) | harvests N
//       region ID (the world region under the view) | place ID|none (the named place)
//       era yes|no | era WORDS... (the era caption showing contains them)
//       away yes|no (the view is off the home region) | map open|closed | travelling yes|no
//       info yes|no | info WORDS... (the open landmark or figure card's title contains them)
//       visited REGION yes|no | journal REGION N (entries) | found REGION N (cards opened)
//       figures N (named figures standing in the world, at least) | tip WORDS... (the world tip)
//       luma X,Y,W,H MIN MAX    mean luminance (0..255) of a window region of this frame
//       color X,Y,W,H R G B TOL mean colour of a region, each channel within TOL
//       lit X,Y,W,H MIN         at least MIN (0..1) of the region's pixels are lamplight (bright,
//                               warm: the night's lit windows, lamps and fires)
//       actor KIND ANIM|moving|inside|hat|any [ITEM]  one actor of that kind (a visitor id or
//                               the resident's) is doing that now, at that item's slot if given
//       bubble yes|no (the resident is speaking) | bubble CONTEXT (a line of that context) |
//       raining yes|no (where the camera looks) visible KIND N (that many seen, not inside) | bank
//       KIND (every one seen on land beside water) | together KIND D (every one seen within D tiles
//       of another) | population yes (no visitor over its max, no leaver lingering) falls N (open
//       water tiles on the rims, falling over) | weather natural|rain|clear | event SHOW yes|no
//       (rainbow, gust, chorus, smoke...) stem FILE MIN (in an --audio-out capture: that music stem
//       has faded in to at least MIN) lively MIN CAP HMIN HCAP SHARE   since `set lively reset`, at
//       least SHARE (0..1) of the
//                               one-second samples had MIN..CAP purposeful movers in view and
//                               HMIN..HCAP new happenings in the last minute
//       city live MIN MAX | city ground ok (every live person on a walkable tile at its level)
//       | city slots ok (no slot over capacity) | city event ID yes|no (running in the area)
//       | city district NAME MIN MAX (live people of the district) | city drawn MIN MAX (actors
//       drawn this frame) | city people MIN MAX (people the crowd hears) | city sound FILE MIN
//       MAX (that city loop's gain x 100 now)
// Widget points for drawer tiles scroll the drawer to the tile when it is off the page.
//   place ITEM @TX,TY [V]   place an item (variant or rotation V) as the build tool would, undoable
//   paint TERRAIN @TX,TY [@TX2,TY2]   paint a tile (or a rectangle) as the paint tool would
//   type TEXT...            type into the open name field (words joined by single spaces)
//   quit

#include <cstdint>
#include <expected>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

namespace lc {

struct ScriptPoint {
    enum class Kind : std::uint8_t { Pixel, Tile, Widget };
    Kind kind = Kind::Pixel;
    float x = 0;
    float y = 0;
    std::string widget;
};

struct ScriptCommand {
    enum class Kind : std::uint8_t {
        Move,
        Click,
        Drag,
        Press,
        Release,
        Key,
        KeyDown,
        KeyUp,
        Wheel,
        Wait,
        Shot,
        Set,
        Expect,
        WaitFor,
        Fast,
        Place,
        Paint,
        Type,
        Quit
    };
    Kind kind = Kind::Wait;
    int line = 0;
    ScriptPoint a;
    ScriptPoint b;
    bool hasPoint = false;
    bool right = false;
    bool middle = false;           // the middle button instead of the left
    float amount = 0;              // wheel delta, wait frames
    std::vector<std::string> args; // key combo, file name, set/expect arguments
};

[[nodiscard]] std::expected<std::vector<ScriptCommand>, std::string>
parseScript(std::string_view text);

struct ScriptRect {
    int x = 0;
    int y = 0;
    int w = 0;
    int h = 0;
};
// "X,Y,W,H" with a positive size.
[[nodiscard]] std::optional<ScriptRect> parseScriptRect(std::string_view token);

// Longest wait a script may ask for (about a day at 60 frames per second).
inline constexpr float kScriptMaxWait = 5e6f;

} // namespace lc
