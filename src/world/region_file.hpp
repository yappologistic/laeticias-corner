#pragma once
// A region file `assets/regions/<region>.json` (docs/design/world-tech.md §2.6): theme, districts
// and their populations, density curves, cards and text. Life sections whose engine does not exist
// yet (figures, groups, chains, events, token lanes) and any section this reader does not know are
// kept as raw JSON, never rejected.

#include "core/iso.hpp"

#include <nlohmann/json.hpp>

#include <array>
#include <expected>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

namespace lc::world {

using Rgb3 = std::array<float, 3>;

struct AmbienceBed {
    std::string file;
    float from = 0; // game hours, 0..24; from > to wraps over midnight
    float to = 24;
    std::string weather;             // "rain": only under rain; empty: any weather
    std::vector<std::string> months; // calendar month ids it plays in; empty: every month
};

struct AmbienceZone {
    TileRect rect; // grid, half-open (inclusive in the file)
    std::string file;
    float gain = 1;
    float from = 0; // game hours it plays; from > to wraps over midnight
    float to = 24;
};

struct ItemLoop {
    std::string item; // set item id: every placed one is a source
    std::string file;
    std::string when; // "always", "lit" (dusk and night), "afternoon", ...
};

struct Theme {
    // Multipliers on the clock's grading per phase (dawn, day, dusk, night): {1, 1, 1} = as today.
    std::array<Rgb3, 4> grading{{{1, 1, 1}, {1, 1, 1}, {1, 1, 1}, {1, 1, 1}}};
    Rgb3 haze{1, 1, 1};
    float hazeStrength = 0;
    std::string climate;
    std::vector<AmbienceBed> beds;
    // A season's own beds (`seasons.<id>.ambience.beds`): in that season they replace `beds` for
    // the hours (and months) they cover.
    std::vector<std::pair<std::string, std::vector<AmbienceBed>>> seasonBeds;
    std::vector<AmbienceZone> zones;
    std::vector<ItemLoop> loops;
    std::string musicDay; // empty: none (stretches)
    std::string musicNight;
    bool seam = false;
    nlohmann::json sound; // world-loose-ends.md §2: families, nature, stings, voices (as written)
};

struct RegionDistrict {
    std::string id;   // the name part of "<region>/<name>"
    std::string area; // living-world §1.1 area kind: centre, town, country, road, sea, wild
    nlohmann::json populations; // living-world.md shapes, kept as written
    nlohmann::json sound;       // surfaces, wind, steps, cart, crowd (as written)
};

struct Card {
    std::string title;
    std::string epithet;
    std::string text;
};

struct RegionFile {
    std::string id;
    std::string name;
    std::string native;
    std::string caption;
    Theme theme;
    std::vector<RegionDistrict> districts;
    std::vector<std::pair<std::string, std::array<float, 24>>> densities;
    std::vector<std::pair<std::string, Card>> cards;
    std::vector<std::pair<std::string, std::string>> strings;
    std::vector<std::string> journal;
    nlohmann::json life; // object: figures, groups, chains, events, lanes_tokens, unknown sections

    [[nodiscard]] const Card* card(std::string_view id) const;
};

// `id` must match the file's "id"; zone rects must lie in the grid.
[[nodiscard]] std::expected<RegionFile, std::string> parseRegionFile(std::string_view text,
                                                                     std::string_view file,
                                                                     std::string_view id, int gridW,
                                                                     int gridH);

} // namespace lc::world
