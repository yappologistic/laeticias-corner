#pragma once
// World saves: versioned JSON with atomic, durable writes and graceful handling of bad input, the
// migration of older saves, and world folder names.
//
// World save format, version 4 (the only place it is documented; layout from
// docs/design/living-corner.md §2.4 and world-tech.md §2.7). One JSON object:
//   "version"    4
//   "name"       the world's name (its home corner's), "free_build" bool,
//   "created"    UTC "YYYY-MM-DDTHH:MM:SSZ", "played" active play time in seconds
//   "clock"      {"t": 0..1, "pin": "auto|day|dusk|night|dawn", "day": calendar day from 0}
//   "season_pin" "auto" or a season id
//   "settings"   {"weather": "natural|rain|clear"} (the player's weather choice; files that
//                 have only the older "rain": true read as "rain")
//   "progress"   {"unlocked": [item and terrain ids], "frames": [frame ids],
//                 "wishes": {"open": [ids, offer order], "done": [ids, grant order],
//                            "snoozed": {id: play time it may return}, "last_offer": seconds},
//                 "clues": [visitor ids], "seen": [visitor ids], "nooks": [nook ids],
//                 "harvests": n, "last_harvest_day": n, "new": [ids with an unseen dot]}
//   "home"       the home region: {"map": {"w", "h"}, "palette": [terrain ids],
//                 "terrain": [[palette index, run], ...] over the map, x fastest,
//                 "items": [{"id", "x", "y", "v", "g": [stage, progress] for growing items}],
//                 "stage": highest open land stage}; coordinates are home-relative
//   "world"      the player's delta over the prebuilt world (never the world itself):
//                {"camera": {"at": [tx, ty] view centre in world grid tiles, "zoom": scale},
//                 "home_view": {"at": [tx, ty] view centre in home tiles, "zoom"} (without a
//                 world: the floating island), "visited": [region ids],
//                 "journal": {region id: [entries found: "landmark:<id>", "figure:<id>"]},
//                 "seen": {region id: [entries seen, not found yet]}, "flags": [one-time facts,
//                 e.g. "seam_explained"]}
// Everything outside "home" is global to the world. Readers ignore what they do not know, skip
// ids the catalog no longer has (with a warning) and fall back to defaults for missing optional
// fields (or fields of the wrong type, each with a warning); counters and timers are clamped to
// what play could have made; files from a newer version are refused. Wild tiles (stages not yet
// open) hold nothing.
//
// Older files are still read:
// Version 3: as above but "world" holds only {"camera": {"at", "zoom"}} in home tiles (read as
//   "home_view"); nothing else changes, the world block starts empty.
// Versions 1 and 2, for migration (see migrateLegacy):
// Version 2 (engine chunked): "map", "chunk" (32), "base": "blank", "palette", "chunks":
//   [{"x", "y", "terrain": [[v, n], ...] rows of the chunk's in-map tiles (-1 = no ground),
//   "items": [{"id", "x", "y", "v"}] absolute}], "clock" {"t", "pin"}, "settings" {"rain",
//   "muted"}, "journal" [visitor ids]. A map of another size is centred.
// Version 1: "map", "palette", a flat row-major "terrain" array, a flat "items" array, and
//   "clock", "settings", "journal" as above. Its 20 x 20 map lands in the front corner.

#include "core/catalog.hpp"
#include "core/clock.hpp"
#include "core/progress.hpp"
#include "core/weather.hpp"
#include "core/world.hpp"

#include <expected>
#include <filesystem>
#include <optional>
#include <span>
#include <string>
#include <utility>
#include <vector>

namespace lc {

inline constexpr int kSaveVersion = 4;

// What the player has done in the wider world: their delta over the immutable prebuilt world.
struct WorldProgress {
    std::optional<Vec2> camera; // view centre in world grid tiles
    float zoom = 1;
    std::vector<std::string> visited; // region ids
    // Per region id: entries found (card opened) and seen (on arrival), in the order they came.
    std::vector<std::pair<std::string, std::vector<std::string>>> found;
    std::vector<std::pair<std::string, std::vector<std::string>>> seen;
    std::vector<std::string> flags;
};

struct SaveData {
    SaveData(World w, const Catalog& cat) : world(std::move(w)), progress(cat) {}

    World world;
    Progress progress;
    std::string name;
    bool freeBuild = false;
    std::string created;
    double played = 0;
    double clockTime = 0.2;
    ClockPin pin = ClockPin::Auto;
    int day = 0;
    int seasonPin = -1; // season index, -1: follow the calendar
    WeatherMode weather = WeatherMode::Natural;
    std::vector<std::string> seen; // visitor ids
    std::optional<Vec2> camera;    // view centre in home tiles (the floating island)
    float zoom = 1;
    WorldProgress worldState;
    int fromVersion = kSaveVersion;
    bool muted = false;                // older files only: it now lives in the profile
    std::vector<std::string> warnings; // entries skipped or repaired, one line per kind
};

[[nodiscard]] std::string serialize(const SaveData& data, const Catalog& cat);
// Rejects malformed or newer files; tolerates missing optional fields and unknown ids.
[[nodiscard]] std::expected<SaveData, std::string> deserialize(std::string_view text,
                                                               const Catalog& cat);

// The "version" a save file claims (0 when it is unreadable), so a file from a newer build can be
// told apart from a damaged one and left untouched.
[[nodiscard]] int saveFileVersion(std::string_view text);

// Brings a save read from version 1 or 2 up to the progress loop (§2.5): every piece the old game
// had stays unlocked, wishes those pieces already answer are done, veggie beds are ripe, and land
// stages holding anything the player made are open (without their reveal, so nothing is
// overwritten).
void migrateLegacy(SaveData& data, const Catalog& cat);

// Offset that centres a map of size `from` inside a map of size `to`.
[[nodiscard]] TilePos centringOffset(int fromW, int fromH, int toW, int toH);

// Folder name for a world: lowercase ASCII letters and digits, apostrophes dropped, other runs
// of characters as "-", at most 32 characters, "world" when empty, "-2", "-3"... when taken.
[[nodiscard]] std::string worldSlug(std::string_view name, std::span<const std::string> taken);
// Current UTC time as "YYYY-MM-DDTHH:MM:SSZ".
[[nodiscard]] std::string utcNow();

// Writes to a temporary sibling, flushes it to disk and renames it over the target, so neither a
// crash nor a power cut leaves a half-written save behind.
[[nodiscard]] std::expected<void, std::string> writeFileAtomic(const std::filesystem::path& file,
                                                               std::string_view contents);

// Settings shared by every world (docs/design/living-corner.md §2.3); a missing or malformed
// file falls back to defaults field by field. Fullscreen and the window's place are kept in
// window.json beside it (they belong to this machine's display, not to the player's taste).
inline constexpr int kUiScaleCount = 6; // Auto, then the factors below
inline constexpr float kUiScales[kUiScaleCount] = {0.0f, 0.75f, 1.0f, 1.25f, 1.5f, 2.0f};
struct Profile {
    int music = 70; // volumes, 0..100 in steps of 5
    int effects = 85;
    int ambience = 60;
    bool muted = false;
    int uiScale = 0; // index into kUiScales (0: auto)
    bool reduceMotion = false;
    bool chatty = true; // "chatter": the resident's idle remarks ("chatty") or not ("quiet")
    bool grid = false;  // the tile grid over open land (G)
    int brush = 1;      // paint brush side: 1, 3 or 5
    bool vsync = true;  // frames wait for the display
    std::string frame = "plain"; // the postcard frame last used
    std::string look = "high";   // the Look: classic | low | medium | high
    std::string clouds = "on";   // the clouds: on | shadows | off
    bool caption = true;         // postcards carry the world's name and the date
    bool onboarded = false;      // the first-minute tour was finished or skipped
    std::string lastWorld;       // folder name of the world played last
};
[[nodiscard]] Profile parseProfile(std::string_view text);
[[nodiscard]] std::string serialize(const Profile& p);

} // namespace lc
