#pragma once
// The content contract (assets/catalog.json, version 2) parsed and validated into plain structs.
// Field meanings: CLAUDE.md "Content contract" and docs/design/living-corner.md §11.

#include "core/clock.hpp"
#include "core/condition.hpp"
#include "core/iso.hpp"

#include <cstdint>
#include <expected>
#include <filesystem>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

namespace lc {

enum class Surface : std::uint8_t { Land, Water, Any };
enum class Layout : std::uint8_t { Variant, Rotate, Connect };
// Shore: water next to land, or land next to water.
enum class Habitat : std::uint8_t { Land, Water, Air, Shore };
enum class VisitTime : std::uint8_t { Any, Day, Night };
// What a tree drops: nothing, leaves, or petals in spring and leaves otherwise.
enum class Shed : std::uint8_t { None, Leaves, Blossom };

struct TerrainDef {
    std::string id;
    std::string name;
    bool base = false;
    bool water = false;
    int variants = 1;
    float fps = 0;
    std::string sound; // sfx path, empty when silent
};

struct CategoryDef {
    std::string id;
    std::string name;
};

struct Offset {
    int x = 0;
    int y = 0;
};

struct Growth {
    int stages = 0; // 0: the item does not grow
    float seconds = 0;
    bool harvest = false;
};

struct ItemDef {
    std::string id;
    std::string name;
    int category = 0;
    int footprintW = 1;
    int footprintH = 1;
    Layout layout = Layout::Variant;
    int count = 1; // variants for variant/rotate layouts; 16 masks for connect
    Surface on = Surface::Land;
    std::string sound; // sfx path
    bool walkable = false;
    bool glow = false;
    std::vector<Offset> smokeAt; // chimney top per variant, from the anchor; empty = no smoke
    float fps = 0;
    std::vector<int> tags;        // indices into Catalog::tags; the first picks reaction lines
    std::uint8_t seasonLooks = 0; // bit per season with `@season` art
    Growth growth;
    Shed sheds = Shed::None;
    std::string clickSound; // sfx path played when clicked with no tool, empty when none
};

struct Amount {
    int index = 0;
    int count = 0;
};

struct VisitorDef {
    std::string id;
    std::string name;
    Habitat habitat = Habitat::Land;
    VisitTime time = VisitTime::Any;
    std::vector<Amount> terrainNeeds; // every entry must be met
    std::vector<Amount> itemNeeds;    // every entry must be met
    std::vector<Amount> anyItems;     // weighted sum over these items must reach anyTotal
    int anyTotal = 0;
    int max = 1;
    bool glow = false; // emissive: drawn after night grading
    std::string voice; // sfx path, empty when silent
    std::string blurb;
    std::string hint;              // sketchbook text before discovery
    std::uint8_t seasons = 0xFF;   // bit per season in which it may come
    bool rare = false;             // comes by its recipe alone
    int recipe = -1;               // condition node, -1 when none
    std::string clue;              // the recipe in words, revealed by a clue reward
    bool underwater = false;       // drawn under water items, faded and cool
    std::vector<int> attractItems; // item types it gathers around (needs, or its recipe)
    std::vector<int> attractTerrain;
};

struct SeasonDef {
    std::string id;
    std::string name;
    int days = 3;
    Rgb grade;
    std::string ambienceDay; // ambience file
    std::string ambienceNight;
    float petals = 0; // falling-thing multipliers
    float leaves = 1;
    bool snow = false; // rain falls as snow
    std::string line;
};

struct TerrainFill {
    int terrain = 0;
    TileRect rect; // half-open
};

struct Placement {
    int item = 0;
    TilePos pos;
    int variant = 0;
};

struct StageDef {
    std::string id;
    std::string name;
    std::vector<TileRect> rects; // half-open
    int pages = 0;
    std::string line;
    std::vector<TerrainFill> terrain; // revealed when the stage opens
    std::vector<Placement> items;
};

struct StarterDef {
    std::vector<TerrainFill> terrain;
    std::vector<Placement> items;
    TilePos resident;
};

struct PieceSet {
    std::vector<int> terrain;
    std::vector<int> items;
    std::vector<int> frames;
};

struct FrameDef {
    std::string id;
    std::string name;
};

struct Reward {
    std::vector<int> items;
    std::vector<int> terrain;
    int frame = -1;
    int clue = -1; // rare visitor index
};

struct WishDef {
    std::string id;
    int giver = -1; // visitor index; -1 is the resident
    std::vector<int> after;
    int gate = -1; // `requires`: condition node that must hold to offer it, -1 when none
    std::string text;
    int goal = 0;
    std::string progress; // label for a top-level count goal
    std::string thanks;
    Reward reward;
    std::vector<int> needed; // selectors the goal needs; pieces must be unlocked to offer it
};

struct NookDef {
    std::string id;
    std::string name;
    int condition = 0;
    int near = 0; // its `near` term: each passing anchor is an instance
    std::string teaser;
    std::string blurb;
    std::string gift;
    float growth = 1;             // growth multiplier for beds in its area
    std::vector<Amount> caps;     // visitor index, extra `max`
    std::vector<Amount> rareRate; // visitor index, divisor of the arrival delay
};

struct ResidentDef {
    std::string id;
    std::string name;
    std::string blurb;
    std::vector<std::string> voice; // sfx paths
};

struct StemDef {
    std::string id;
    std::string file;
    int when = -1; // condition node, -1: always
};

struct AudioList {
    std::vector<std::string> music;
    std::vector<std::string> ambience;
    std::vector<std::string> sfx;
    std::vector<StemDef> dayStems;
    std::vector<StemDef> nightStems;
    std::vector<std::string> notes; // in scale order
};

// Map limits: a continuous world of about 1024 x 512 tiles is planned; these leave headroom
// while keeping tile indices and pixel extents far from overflow.
inline constexpr int kMaxMapSide = 4096;
inline constexpr long long kMaxMapTiles = 1LL << 22;

struct Catalog {
    int tileW = 64;
    int tileH = 32;
    int mapW = 40;
    int mapH = 40;
    std::vector<TerrainDef> terrain;
    std::vector<CategoryDef> categories;
    std::vector<ItemDef> items;
    std::vector<VisitorDef> visitors;
    std::vector<std::string> tags;
    std::vector<SeasonDef> seasons;
    std::vector<StageDef> stages;
    StarterDef starter;
    PieceSet start;  // unlocked in a new world
    PieceSet legacy; // unlocked for worlds migrated from the first save format
    std::vector<FrameDef> frames;
    std::vector<WishDef> wishes;
    std::vector<NookDef> nooks;
    ResidentDef resident;
    ConditionSet conditions;
    AudioList audio;
    int baseTerrain = 0;
    int waterTerrain = 0;

    [[nodiscard]] Iso iso() const {
        return {static_cast<float>(tileW) * 0.5f, static_cast<float>(tileH) * 0.5f};
    }
    [[nodiscard]] std::optional<int> findTerrain(std::string_view id) const;
    [[nodiscard]] std::optional<int> findItem(std::string_view id) const;
    [[nodiscard]] std::optional<int> findCategory(std::string_view id) const;
    [[nodiscard]] std::optional<int> findVisitor(std::string_view id) const;
    [[nodiscard]] std::optional<int> findTag(std::string_view id) const;
    [[nodiscard]] std::optional<int> findSeason(std::string_view id) const;
    [[nodiscard]] std::optional<int> findFrame(std::string_view id) const;
    [[nodiscard]] std::optional<int> findWish(std::string_view id) const;
    [[nodiscard]] std::optional<int> findNook(std::string_view id) const;
    [[nodiscard]] bool hasTag(int item, std::string_view tag) const;
};

// Parses and validates; the error names the offending entry.
[[nodiscard]] std::expected<Catalog, std::string> parseCatalog(std::string_view json);
[[nodiscard]] std::expected<Catalog, std::string> loadCatalog(const std::filesystem::path& file);

[[nodiscard]] std::expected<std::string, std::string> readTextFile(const std::filesystem::path& p);

} // namespace lc
