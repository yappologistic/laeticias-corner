#pragma once
// The content contract (assets/catalog.json, version 2) parsed and validated into plain structs.
// Field meanings: CLAUDE.md "Content contract" and docs/design/living-corner.md §11.

#include "core/actor_data.hpp"
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
    std::string sound;  // sfx path, empty when silent
    bool paved = false; // walkers prefer it
};

struct CategoryDef {
    std::string id;
    std::string name;
};

struct Offset {
    int x = 0;
    int y = 0;
};

// An interaction point on an item (docs/design/living-world.md §2.3). Positions are resolved per
// variant: `spots[v]` lists points in tile coordinates from the origin tile's top corner, `lift[v]`
// is how many pixels above the ground they are (a seat, a perch), `face[v]` the direction an
// actor there faces (0 +x, 1 +y, 2 -x, 3 -y; 0xFF: free). Beside slots have no fixed points:
// any free tile next to the footprint will do.
enum class SlotWhere : std::uint8_t { On, Beside, Tile };
enum class SlotFacing : std::uint8_t { Free, Rotation, Item, Out };

struct SlotDef {
    int name = 0; // Catalog::slotNames
    int kind = 0; // Catalog::slotKinds
    SlotWhere where = SlotWhere::On;
    SlotFacing facing = SlotFacing::Free;
    int cap = 1;
    std::vector<std::vector<Vec2>> spots;
    std::vector<float> lift;
    std::vector<std::uint8_t> face;
    int holds = -1; // goods it keeps, -1: none
    int holdsMax = 0;
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
    int shelter = 0;        // beds within this many tiles grow even when the season rests them
    bool crossing = false;  // walkers may cross water on it (tag "crossing")
    std::vector<int> perch; // pixel height a percher sits at, per variant; empty: none
    int deck = 0;           // a walkable item's floor, px above the ground (0: the ground)
    std::vector<SlotDef> slots;
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
    float growth = 1;  // how fast beds grow (0: they rest, unless sheltered)
    std::string line;
    float showers = 0; // rain cells expected per weather period
    float clouds = 0;  // cloud cells expected per weather period
    float wind = 0.3f; // usual wind strength, 0..1
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
    // `prefer`: who (a visitor index, -1 the resident) and which activity (activityNames).
    std::vector<std::pair<int, int>> prefer;
};

// Who lives in the corner: everything about her is data, and she can be left out entirely.
struct ResidentDef {
    bool enabled = true;
    std::string id;
    std::string name;
    std::string blurb;
    std::vector<std::string> voice;              // sfx paths
    std::vector<std::string> contexts;           // line contexts
    std::vector<std::vector<std::string>> lines; // per context
    [[nodiscard]] int context(std::string_view c) const;
};

struct GoodsDef {
    std::string id;
    std::string name;
};

// The corner's moments of delight as scheduled or triggered events (living-world.md §5).
enum class EventShow : std::uint8_t {
    Rainbow,
    ShootingStar,
    OwlCall,
    Rustle,
    Gust,
    FishJump,
    FrogChorus,
    Chorus,
    FireflySync,
    Smoke,
    Season
};
enum class EventOn : std::uint8_t {
    Window,   // at random times inside its filters (an average gap, or a range)
    Hours,    // active while the clock is inside `from`..`to`
    Rain,     // while it rains here, and `duration` after
    RainStop, // rain here stopped after at least `minRain` seconds
    Placed,   // a placement, move or removal near an item with tag `nearTag`
    Reactive, // its `when` condition holds
    Cook,     // the resident cooked a harvest
    Season    // the first dawn of a season
};

struct EventDef {
    std::string id;
    EventShow show = EventShow::Gust;
    EventOn on = EventOn::Window;
    std::uint8_t phases = 0xF;
    std::uint8_t seasons = 0xFF;
    int weather = -1; // 0 clear, 1 rain, -1 either
    int when = -1;    // condition node
    float mean = 0;   // Window: average gap in seconds
    float every0 = 0; // Window: gap range; Reactive: gap; Rain: repeat inside the event
    float every1 = 0;
    float from = 0; // Hours
    float to = 0;
    float cooldown = 0;
    bool daily = false; // at most once per calendar day
    float dur0 = 0;
    float dur1 = 0;
    float minRain = 0;
    int nearTag = -1;
    float within = 1;
    std::string sfx; // empty: silent
    float gain = 1;
    int who = -1; // a visitor it asks to call (the frog's chorus), -1: none
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

// A climate of the world (the catalog's `climates`, parents resolved): what the engine reads of
// it so far, its snow.
struct ClimateDef {
    std::string id;
    std::vector<int> snowLine;       // per month: the lowest level snow falls and lies on; -1: none
    std::uint16_t lowlandMonths = 0; // months snow may fall below the line too (bit per month)
    float lowlandChance = 0;         // on how many of those days
    // Traffic rows by month (road, caravan, courier, barge, sailing, grain ...): the share of a
    // traveller's instances under way each month.
    struct Row {
        std::string name;
        std::vector<float> share; // per month
    };
    std::vector<Row> traffic;
    [[nodiscard]] const Row* row(std::string_view name) const;
};

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
    std::vector<int> seasonDays; // days of each season, for the calendar
    // The world calendar's months in order (day n is month n mod size, as many as the year's
    // days); empty when the catalog has no calendar.
    std::vector<std::string> months;
    std::vector<ClimateDef> climates;
    [[nodiscard]] const ClimateDef* findClimate(std::string_view id) const;
    std::vector<StageDef> stages;
    std::optional<TilePos> gate; // the home region's way out (the road gate), if any
    StarterDef starter;
    PieceSet start;  // unlocked in a new world
    PieceSet legacy; // unlocked for worlds migrated from the first save format
    std::vector<FrameDef> frames;
    std::vector<WishDef> wishes;
    std::vector<NookDef> nooks;
    ResidentDef resident;
    std::vector<GoodsDef> goods;
    std::vector<EventDef> events;
    std::vector<std::string> slotNames;
    std::vector<std::string> slotKinds;
    std::vector<std::string> activityNames; // nook `prefer` keys
    std::vector<std::string> emitSounds;    // sfx paths named by `emit` steps
    std::vector<ActorKind> kinds;           // visitors first (same index), then the resident
    ActorProgram program;
    int residentKind = -1; // -1: nobody lives here
    int tourWish = -1;     // the first-minute tour: the wish it shows, the piece it plants
    int tourPiece = -1;
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
