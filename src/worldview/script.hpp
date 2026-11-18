#pragma once
// The world viewer's options and its script language. Pure parsing (no SDL).
//
// A script is one command per line; `#` starts a comment. Grid tiles are (x, y) as world.json
// and worldinfo use them.
//
//   goto <region> | goto <x> <y>     jump to a region's marker or a grid tile, centred as drawn
//   zoom <overview|0.25|0.5|1|2|3>
//   clock <day|dusk|night|dawn|t>    time of day; t in 0..1
//   pan <dx> <dy>                    move the view by window pixels
//   fly <region> [zoom] [seconds] | fly <x> <y> [zoom] [seconds]
//                                    start an eased flight; frames run it
//   frames <n>                       draw n frames, 1/60 s apart
//   settle                           draw until nothing streams or builds (and the flight ends)
//   shot <file>                      save the window as PNG (relative to --shots, else cwd)
//   expect <what> [op value]         fail the run unless it holds; <what> is one of
//       luma, contrast               mean and spread of the last frame's luminance (0..1)
//       draw_calls, sprites, placeholders, flat_terrain, cells_pending
//       lod <native|half|quarter|overview>
//       region <id>                  the region the view belongs to
//       page_resident <set>          every page of the set is resident
//       caption                      an era caption is showing

#include <cstdint>
#include <expected>
#include <filesystem>
#include <optional>
#include <span>
#include <string>
#include <string_view>
#include <vector>

namespace lc::worldview {

struct ViewerOptions {
    std::optional<std::filesystem::path> assets;
    int w = 1280;
    int h = 800;
    std::string go; // region id or "x,y"
    float zoom = 1; // 0: overview
    std::string clock = "day";
    std::optional<std::filesystem::path> shot;
    std::optional<std::filesystem::path> script;
    std::optional<std::filesystem::path> shots; // where script shots go
    std::string renderer;                       // SDL render driver; empty: software (headless)
    bool bench = false;
    std::string benchCase; // empty: every case
    bool budget = true;    // the bench fails over budget (sanitizer builds only report)
    bool interactive = false;
    bool report = false;
    bool help = false;
};

[[nodiscard]] std::expected<ViewerOptions, std::string>
parseViewerOptions(std::span<const std::string_view> args);
[[nodiscard]] std::string_view viewerUsage();

// "day", "dusk", "night", "dawn" (the phase centres) or a number in 0..1.
[[nodiscard]] std::optional<double> parseClock(std::string_view s);
// "overview" (0) or a positive number.
[[nodiscard]] std::optional<float> parseZoom(std::string_view s);

enum class Op : std::uint8_t { Goto, Zoom, Clock, Pan, Fly, Frames, Settle, Shot, Expect };

struct Command {
    Op op;
    std::vector<std::string> args;
    int line = 0;
};

[[nodiscard]] std::expected<std::vector<Command>, std::string> parseScript(std::string_view text);

// Compares `a` with `b` by `op` (<, <=, >, >=, ==); nullopt for an unknown operator.
[[nodiscard]] std::optional<bool> compare(double a, std::string_view op, double b);

} // namespace lc::worldview
