#pragma once
// Input scripts for headless runs. They drive the game through synthesized SDL events, the same
// path real input takes. One command per line; '#' starts a comment line.
//
// Points (one token):  X,Y      window pixels
//                      @TX,TY   centre of map tile (TX, TY) under the current camera
//                      ui:NAME  centre of a UI widget: build, remove, sound, photo, clock, rain,
//                               journal, journal_close, undo, redo, recentre, zoom_out, zoom_in,
//                               tab:<category id>, tile:<item or terrain id>
//
// Commands:
//   move P                  pointer motion
//   click P [right]         press and release (left button unless "right")
//   drag P1 P2 [right]      press at P1, move to P2 over 8 frames, release
//   key COMBO               e.g. r, escape, ctrl+z, ctrl+shift+z, home, f11, equals, minus
//   wheel DY [P]            scroll (positive = away from the user), optionally at P
//   wait N                  let N frames pass
//   shot FILE.png           save the current frame (relative to the working directory)
//   set clock PHASE|auto    pin the clock to day/dusk/night/dawn instantly, or unpin
//   set rain on|off
//   expect WHAT ARGS...     fail the run unless the state matches:
//       tile P TERRAIN | item P ITEM|none | count ITEM|all N | tool none|place|paint|remove
//       drawer open|closed | journal open|closed | photo on|off | zoom N | phase PHASE
//       seen VISITOR | undo yes|no | redo yes|no | photos N | muted yes|no | rain on|off
//   quit

#include <cstdint>
#include <expected>
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
    enum class Kind : std::uint8_t { Move, Click, Drag, Key, Wheel, Wait, Shot, Set, Expect, Quit };
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

} // namespace lc
