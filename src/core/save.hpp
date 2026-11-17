#pragma once
// Versioned JSON save files with atomic, durable writes and graceful handling of bad input.
//
// Save format, version 2 (the only place it is documented). One JSON object:
//   "version"  2
//   "map"      {"w": W, "h": H}            map size the file was written for
//   "chunk"    32                          side of a chunk in tiles
//   "base"     "blank"                     what untouched chunks contain (see below)
//   "palette"  ["grass", "meadow", ...]    terrain ids; terrain values index this list
//   "chunks"   [{"x": CX, "y": CY,         one entry per chunk that differs from the base
//                "terrain": [[v, n], ...], run-length rows of the chunk's in-map tiles,
//                                          row by row; v = palette index, -1 = no ground
//                "items": [{"id": ID, "x": X, "y": Y, "v": VARIANT}, ...]}]
//                                          items whose origin tile lies in the chunk, in
//                                          absolute tile coordinates
//   "clock"    {"t": 0..1, "pin": "auto|day|dusk|night|dawn"}
//   "settings" {"rain": bool, "muted": bool}
//   "journal"  [visitor ids seen so far]
// Readers ignore sections and fields they do not know, skip ids the catalog no longer has (with a
// warning) and fall back to defaults for missing optional sections; files from a newer version
// are refused. A map of another size than the catalog's is loaded centred on the new map.
//
// Version 1 (still read): "map", "palette", a flat row-major "terrain" array of W*H palette
// indices, a flat "items" array, and "clock"/"settings"/"journal" as above.
//
// Why chunks and a base: the world is planned to grow into one continuous map of roughly
// 1024 x 512 tiles that is mostly prebuilt. "base" will then name that prebuilt content (shipped
// with the game, never written by saves), and the file holds only the chunks the player changed,
// so an autosave costs what the player built, not what the world contains. Later versions can
// split chunk entries into separate files or append-only journals behind the same seam.

#include "core/catalog.hpp"
#include "core/clock.hpp"
#include "core/world.hpp"

#include <expected>
#include <filesystem>
#include <string>
#include <utility>
#include <vector>

namespace lc {

inline constexpr int kSaveVersion = 2;
inline constexpr std::string_view kSaveBaseBlank = "blank";

struct SaveData {
    explicit SaveData(World w) : world(std::move(w)) {}

    World world;
    double clockTime = 0.2;
    ClockPin pin = ClockPin::Auto;
    bool rain = false;
    bool muted = false;
    std::vector<std::string> journal;  // visitor ids seen so far
    std::vector<std::string> warnings; // entries skipped or repaired, one line per kind
};

[[nodiscard]] std::string serialize(const SaveData& data, const Catalog& cat);
// Rejects malformed or newer files; tolerates missing optional fields, unknown ids and a map of a
// different size (content is centred, anything that no longer fits is reported).
[[nodiscard]] std::expected<SaveData, std::string> deserialize(std::string_view text,
                                                               const Catalog& cat);

// Offset that centres a map of size `from` inside a map of size `to`.
[[nodiscard]] TilePos centringOffset(int fromW, int fromH, int toW, int toH);

// Writes to a temporary sibling, flushes it to disk and renames it over the target, so neither a
// crash nor a power cut leaves a half-written save behind.
[[nodiscard]] std::expected<void, std::string> writeFileAtomic(const std::filesystem::path& file,
                                                               std::string_view contents);

} // namespace lc
