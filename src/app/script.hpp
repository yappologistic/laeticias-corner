#pragma once
// Input scripts for headless runs. They drive the game through synthesized SDL events, the same
// path real input takes. One command per line; '#' starts a comment line.
//
// Points (one token):  X,Y      window pixels
//                      @TX,TY   centre of map tile (TX, TY) under the current camera
//                      ui:NAME  centre of a UI widget: build, remove, sound, photo, clock, rain,
//                               journal, journal_close, undo, redo, recentre, zoom_out, zoom_in,
//                               scroll_up, scroll_down, tab:<category id>, tile:<item or terrain
//                               id>, or of the toast and hint panels: toast, hint
//
// Commands:
//   move P                  pointer motion
//   click P [right]         press and release (left button unless "right")
//   drag P1 P2 [right]      press at P1, move to P2 over 8 frames, release
//   press P [right]         move to P and press the button (hold it)
//   release P [right]       move to P and release the button
//   key COMBO               e.g. r, escape, ctrl+z, ctrl+shift+z, home, f11, equals, minus, space
//   keydown COMBO           press (and hold) a key, e.g. keydown d, keydown ctrl
//   keyup COMBO             release a held key
//   wheel DY [P]            scroll (positive = away from the user), optionally at P
//   wait N                  let N frames pass
//   shot FILE.png           save the current frame (relative to the working directory)
//   set clock PHASE|auto    pin the clock to day/dusk/night/dawn instantly, or unpin
//   set rain on|off
//   expect WHAT ARGS...     fail the run unless the state matches:
//       tile P TERRAIN | item P ITEM|none | count ITEM|all N | tool none|place|paint|remove
//       drawer open|closed | journal open|closed | photo on|off | phase PHASE
//       seen VISITOR | undo yes|no | redo yes|no | photos N | muted yes|no | rain on|off
//       present VISITOR N (how many are on the map now) | habitat ok (every critter stands
//       where it may) | saved yes|no (a save file exists) | zoom 0.25|0.5|1|2|3
//       toast yes|no (a toast is showing) | panning yes|no (a pan key is held)
//       luma X,Y,W,H MIN MAX    mean luminance (0..255) of a window region of this frame
//       color X,Y,W,H R G B TOL mean colour of a region, each channel within TOL
// Widget points for drawer tiles scroll the drawer to the tile when it is off the page.
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
        Quit
    };
    Kind kind = Kind::Wait;
    int line = 0;
    ScriptPoint a;
    ScriptPoint b;
    bool hasPoint = false;
    bool right = false;
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
