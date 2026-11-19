#pragma once
// The regions' life compiled for the simulation (docs/design/living-world.md §2–§5, the shapes
// as the builders wrote them: out/reports/world-life.md): actor kinds from the set catalogs;
// per region the roles with their schedules and routines as step programs, districts with
// hourly populations, groups, chains, festivals, events, figures and tokens. Names are resolved
// once to indices into the world (items, slots, districts, graph nodes); anything that does not
// resolve is reported with its region and entry and left out. Pure logic: no SDL.

#include "world/loader.hpp"

#include <array>
#include <cstdint>
#include <string>
#include <unordered_map>
#include <vector>

namespace lc::life {

using world::LoadedWorld;
using world::WorldMap;

inline constexpr int kNoIndex = -1;

// An animation every kind may name; kinds lacking one fall back to idle (or move in motion).
struct KindDef {
    std::string id;
    std::string name;
    std::string sprite; // atlas key prefix: "walker/<kind>", "figure/<id>", "ship/<kind>" ...
    int variants = 1;
    std::vector<std::uint16_t> anims; // LifeData::animNames indices this kind has
    std::vector<float> fps;           // per entry of `anims`
    std::vector<float> strides;       // per entry: tiles a cycle walks, 0 when not stated
    bool cart = false;                // carts and sledges: lifesim's slower default speed
    bool ship = false;                // afloat: at the water's level, under every deck
    int length = 1;                   // tiles its body runs along its heading (carts, ships)
    // A ship's height standing (its moving look) and with its mast down, px above the water,
    // from the geometry's actor `height`; 0: not given (never lowered).
    int standing = 0;
    int lowered = -1; // LifeData::animNames index of its `lowered` look, -1: none
    [[nodiscard]] bool has(int anim) const;
    [[nodiscard]] float fpsOf(int anim) const;
};

enum class Verb : std::uint8_t {
    Go,
    Use,
    Take,
    Put,
    Wander,
    Wait,
    Enter,
    Follow,
    Emit,
    Pick,
    Each,
    Routine
};

// Roam: a random node of the region's graph within `within` tiles (synthesised strolls).
// Flock: the node a herd shares (chosen per chunk and period, so flock-mates move together).
enum class TargetKind : std::uint8_t { None, Here, Node, Item, Home, SlotKind, Each, Roam, Flock };

struct Target {
    TargetKind kind = TargetKind::None;
    int node = kNoIndex;     // region graph node (Node)
    int item = kNoIndex;     // Content item (Item)
    int slot = kNoIndex;     // WorldMap::slotNames index (Item, Home); kNoIndex: beside
    int slotKind = kNoIndex; // WorldMap::slotKinds index (SlotKind)
    float within = 0;        // tiles; 0: anywhere sensible
    bool beside = false;     // Home: beside its home rather than at a slot
};

enum class Until : std::uint8_t { None, Hour, Clear, Rain };
enum class Effect : std::uint8_t { None, OpenShutters, Unload };
// Item states the data switches (living-world §2.3): drawn as layers, `lit` gates the glow.
enum class ItemState : std::uint8_t { None = 0, Lit = 1, Open = 2, Firing = 4 };

struct Step {
    Verb verb = Verb::Wait;
    Target target;
    float dur0 = 0; // seconds, uniform in [dur0, dur1]; 0, 0: none
    float dur1 = 0;
    Until until = Until::None;
    float untilHour = 0;
    std::uint16_t anim = 0;            // animNames index (Use and Wait)
    int goods = kNoIndex;              // Take, Put: LifeData::goods index
    float radius = 0;                  // Wander
    int zone = kNoIndex;               // Wander: map district
    int follow = kNoIndex;             // Follow: kind
    float spacing = 1;                 // Follow
    Effect effect = Effect::None;      // Use
    ItemState state = ItemState::None; // Use, Each
    int sound = kNoIndex;              // Emit: LifeData::sounds index (sfx or fx)
    bool fx = false;                   // Emit: a visual effect rather than a sound
    std::uint32_t first = 0;           // Pick: options; Each: body; Routine: the routine's block
    std::uint32_t count = 0;
    int eachItem = kNoIndex; // Each
    int eachMax = 3;
};

// A run of steps: a routine, a pick option, an each body.
struct Block {
    std::uint32_t first = 0;
    std::uint32_t count = 0;
    bool loop = false;
    float weight = 1; // as a pick option
};

// Filters shared by schedule blocks, populations, festivals and event triggers.
struct Filter {
    float from = 0; // game hours; from == to: all day
    float to = 0;
    bool hours = false;
    std::uint8_t every = 0; // days: day % every == offset
    std::uint8_t offset = 0;
    std::uint8_t seasons = 0;   // bit per season; 0: any
    std::uint8_t seasonDay = 0; // 1-based day of the season; 0: any
    std::uint16_t months = 0;   // bit per calendar month; 0: any
    int festival = kNoIndex;
    int notFestival = kNoIndex;
    std::int8_t weather = -1; // -1 any, 0 clear, 1 rain
};

struct ScheduleBlock {
    Filter when;
    int routine = kNoIndex; // block index
};

struct Role {
    std::string id;
    std::string name;
    int kind = kNoIndex;
    int homeItem = kNoIndex; // Content item
    int homeSlot = kNoIndex; // slot name
    float speed = 0;         // tiles/s; 0: the kind's default
    double speedExact = 0;   // as written (lifesim's travel times use it)
    std::vector<ScheduleBlock> schedule;
    std::vector<std::pair<std::string, int>> routines; // name -> block
    int rainRoutine = kNoIndex;                        // the rain interrupt's block
    std::string card;
    std::string carries; // `carries.light`: the light profile it holds after dark (renderer)
};

struct Population {
    int role = kNoIndex;
    int density = 0;        // LifeRegion::densities index
    float maxPerChunk = 0;  // people per 1 024 tiles of the district
    int perItem = kNoIndex; // Content item: count per placed instance in the district
    float count = 1;
    Filter when;
};

enum class Area : std::uint8_t { Centre, Town, Country, Road, Sea, Wild };

struct District {
    std::string id;
    int map = kNoIndex; // WorldMap district
    Area area = Area::Town;
    std::vector<Population> populations;
    int tiles = 0;                                     // all tiles of the district
    std::vector<std::pair<std::uint32_t, int>> chunks; // map chunk index, tiles there
    // Placed instances per populations entry with per_item (same order), map item indices.
    std::vector<std::vector<std::uint32_t>> instances;
};

enum class Formation : std::uint8_t { Line, Pairs, Cluster };

struct GroupMember {
    int kind = kNoIndex;
    int count = 1;
    int carry = kNoIndex; // goods
};

struct Group {
    std::string id;
    int leader = kNoIndex; // kind
    std::vector<GroupMember> members;
    Formation formation = Formation::Line;
    float spacing = 0.9f; // line and pairs; cluster: radius
};

struct Festival {
    std::string id;
    std::uint16_t months = 0; // bit per calendar month: on exactly those months (season and day
                              // aside); 0: by season and day
    std::uint8_t seasons = 0;
    int day = 0; // 1-based day of the season, 0: every day
    float from = 0;
    float to = 24;
};

// A chain stage (lifesim.py): a source, a transform (needs + makes), a carry, or a sink.
struct ChainStage {
    enum class Kind : std::uint8_t { Source, Transform, Carry, Sink };
    Kind kind = Kind::Source;
    std::string slot;     // slot reference as written (source, transform, sink)
    std::string from;     // carry
    std::string to;       // carry
    std::string out;      // transform: its output slot, default `slot`
    std::string near;     // node choosing the instance
    int goods = kNoIndex; // makes / carry / sink
    int needs = kNoIndex; // transform input
    int role = kNoIndex;  // `by`, when it names a role
    std::string by;       // as written
    int units = 1;
    int workers = 1;
    double dur = -1; // seconds; -1: lifesim's default for the stage
    std::string label;
};

struct Chain {
    std::string id;
    std::string name;
    double period = 120;
    float from = 6; // hours
    float to = 18;
    std::uint8_t seasons = 0;
    std::uint16_t months = 0; // bit per calendar month; 0: any
    std::vector<float> pace;  // by_month: the period is divided by it, per month; empty: 1
    int event = kNoIndex;     // runs only while this event runs
    std::vector<ChainStage> stages;
};

enum class Trigger : std::uint8_t {
    Window,
    Calendar,
    After,
    TokenArrived,
    Chain,
    Weather,
    Reactive
};
enum class EventSize : std::uint8_t { Small, Medium, Large };

struct CastEntry {
    int group = kNoIndex;
    int role = kNoIndex;
    int kind = kNoIndex;
    int count = 1;
    std::vector<int> rotate; // groups taken in turn, `count` a day, `spacing` seconds apart
    float spacing = 0;
};

struct Event {
    std::string id;
    Trigger trigger = Trigger::Window;
    Filter when;             // hours (the window), days, seasons, months, festival filters
    bool seasonTurn = false; // `season_turn`: on its season's first day (months: its month's)
    float chance = 1;
    double every = 0;        // game seconds between repeats inside the window; 0: once
    int festival = kNoIndex; // calendar
    int after = kNoIndex;    // after: event index
    int tokenKind = kNoIndex;
    int chain = kNoIndex;
    int chainStage = -1;
    std::string weather;      // weather kind as written
    int reactKind = kNoIndex; // reactive: an actor of this kind ...
    int reactItem = kNoIndex; // ... within reactWithin of this item ...
    float reactWithin = 2;
    int reactGoods = kNoIndex; // ... whose slot holds these goods
    float dur0 = 60;
    float dur1 = 60;
    EventSize size = EventSize::Small;
    std::string rarity;
    std::vector<CastEntry> cast;
    std::vector<int> route;  // region graph nodes
    std::uint32_t steps = 0; // block index of the event's steps
    std::vector<int> zones;  // map districts
    int sfx = kNoIndex;      // sounds index
    int ambience = kNoIndex;
    float ambienceGain = 1;
    bool glow = false;
    std::string card;
};

enum class FigurePresence : std::uint8_t {
    Present,
    Memory,
    Visitor,
    Reenactor,
    Tale,
    Apparition,
    Relief,
    Shrine,
    Statue
};

struct Figure {
    std::string actor; // as written (may name no kind: statues)
    int kind = kNoIndex;
    FigurePresence presence = FigurePresence::Present;
    bool translucent = false;
    bool imagined = false;
    int role = kNoIndex; // a role compiled from its schedule and routines, when it has them
    int district = kNoIndex;
    int atItem = kNoIndex; // `at`: the placed item it belongs to
    std::string card;
};

struct Token {
    int kind = kNoIndex;
    int region = kNoIndex; // LifeData::regions index of the file declaring it
    std::string lane;      // "<layer>:<id>" (RoadGraph lane), or empty for a road route
    std::string from, to;  // road route nodes ("<layer>:<id>")
    int count = 1;
    int group = kNoIndex; // region group following the token's leader
    int carry = kNoIndex; // goods
    int variant = -1;
    Filter when;        // the days it travels (months, season and its day); hours are below
    bool hours = false; // under way only from hourFrom to hourTo (game hours); waiting otherwise
    float hourFrom = 0;
    float hourTo = 0;
    std::vector<std::string> rest; // where a waiting instance stands: "<layer>:<node>" or ports
    std::vector<float> offsets;    // per instance, its share of the period (empty: k / count)
    std::vector<float> share;      // per month, the share of instances under way (empty: all)
    std::uint64_t seed = 0;        // from its id: the days each instance is under way
};

struct LifeRegion {
    std::string id;
    int worldRegion = kNoIndex; // WorldFile::regions index
    int layer = kNoIndex;       // LoadedWorld::graphs index of its layer's graph
    int season = -1;            // its own moment's season (the builders' day reports use it)
    std::vector<std::array<float, 24>> densities;
    std::vector<std::string> densityNames;
    std::vector<Role> roles;
    std::vector<District> districts;
    std::vector<Group> groups;
    std::vector<Chain> chains;
    std::vector<Festival> festivals;
    std::vector<Event> events;
    std::vector<Figure> figures;
    [[nodiscard]] int findRole(std::string_view id) const;
    [[nodiscard]] int findGroup(std::string_view id) const;
    [[nodiscard]] int findFestival(std::string_view id) const;
    [[nodiscard]] int findEvent(std::string_view id) const;
    [[nodiscard]] int findChain(std::string_view id) const;
};

struct LifeData {
    std::vector<KindDef> kinds;
    std::vector<std::string> animNames; // 0: idle, 1: move
    std::vector<std::string> goods;     // ids
    std::vector<std::string> sounds;    // sfx and fx names as written
    std::vector<Step> steps;
    std::vector<Block> blocks;
    std::vector<LifeRegion> regions;
    std::vector<Token> tokens;
    std::vector<std::string> seasons;  // the home catalog's, in order
    int seasonDays = 3;                // days in a season (the calendar's)
    std::vector<std::string> months;   // the world calendar's month ids (day n: month n mod size)
    std::vector<std::string> problems; // what did not resolve, one line each

    [[nodiscard]] int findKind(std::string_view id) const;
    [[nodiscard]] int findGoods(std::string_view id) const;
    [[nodiscard]] int findRegion(std::string_view id) const;
    [[nodiscard]] int regionOfWorld(int worldRegion) const; // -1 when it has no life
    [[nodiscard]] int monthOf(int day) const;               // the calendar month of a day
    [[nodiscard]] std::size_t memoryBytes() const;

    std::unordered_map<std::string, int> kindIndex;
    std::vector<int> worldToLife; // WorldFile::regions index -> regions index, -1
};

// A month mask holds month m (an empty mask holds every month).
[[nodiscard]] constexpr bool monthIn(std::uint16_t mask, int month) {
    return mask == 0 || ((mask >> month) & 1u) != 0;
}

inline constexpr std::uint16_t kAnimIdle = 0;
inline constexpr std::uint16_t kAnimMove = 1;

// Compiles every region file the world loaded. Never fails: problems are listed.
[[nodiscard]] LifeData compileLife(const LoadedWorld& w);

// worldgen.rng.hash64 of one text part (FNV-1a, then SplitMix64's finaliser): the day plan's draw
// is lifereport's, so the engine and the builders' day reports hold the same events.
[[nodiscard]] std::uint64_t worldgenHash(std::string_view text);

// Game hour "hh:mm" -> hours; a malformed value gives -1.
[[nodiscard]] float parseHour(std::string_view s);
// Inside [from, to) (wrapping past midnight), as citylife.in_hours: from == to holds no hour.
[[nodiscard]] bool inHours(float from, float to, float h);

} // namespace lc::life
