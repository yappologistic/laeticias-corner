#pragma once
// City life at scale (docs/design/living-world.md §7, tasks W4–W6): the people of the prebuilt
// regions living their day around wherever the camera looks.
//
// Tiers. The *active area* is every chunk touching the view grown by a margin; its people are
// live actors in one pooled array with stable handles, updated in round-robin buckets and drawn
// interpolated. Everything else is abstract and costs nothing per frame: district populations
// are a formula of (seed, hour, day type, weather), chains run on lifesim's clock (chains.hpp),
// events follow a day plan per region, ships and caravans are tokens whose position is a
// function of time. When a chunk becomes active its people are *materialised mid-routine*:
// each identity (district, population entry, chunk or placed instance, index) gets its schedule
// block for the hour, its routine and how far into it it is from the seed and the clock, so it
// stands where it would be. Nothing about them is saved; leaving and coming back gives the same
// people doing what they would be doing now.
//
// Renderer: `gather(rect, alpha, out)` writes the live actors overlapping a rect (allocation
// free, into the caller's span) with sub-tile position, floor height, level, facing, sprite
// prefix and animation, goods carried and draw-order hints. Mixer: `sounds()` (one-shots of the
// last step) and `forEachLoop` (event ambience and working places). Camera: `setView`.

#include "core/tuning.hpp"
#include "life/chains.hpp"
#include "life/data.hpp"
#include "life/paths.hpp"

#include <array>
#include <cstdint>
#include <memory>
#include <span>
#include <string>
#include <string_view>
#include <tuple>
#include <vector>

namespace lc::life {

// The compiled life of one loaded world and its walking tables, shared by every CityLife.
struct LifeWorld {
    const LoadedWorld* world = nullptr;
    LifeData data;
    std::vector<RegionPaths> paths;
    std::vector<int> pathsOf; // life region -> paths index, -1 when its layer has no graph
    // Slots grouped by (placed item, slot name): reservations count per group against its cap.
    std::vector<std::uint32_t> slotGroup; // per WorldSlot
    std::vector<std::uint8_t> groupCap;
    std::vector<std::uint32_t> groupFirst; // first WorldSlot of the group
    std::vector<std::uint8_t> groupSpots;  // its spots
    // Per map chunk: the life districts on it, (region, district, tiles).
    struct ChunkDistrict {
        std::uint16_t region;
        std::uint16_t district;
        std::uint16_t tiles;
    };
    std::vector<std::vector<ChunkDistrict>> chunkDistricts;
    // Per life region: its placed items by catalog item (sorted by info, then item index).
    std::vector<std::vector<std::pair<std::uint32_t, std::uint32_t>>> regionItems;
    double buildMs = 0;
    [[nodiscard]] const WorldMap& map() const { return *world->map; }
    [[nodiscard]] std::size_t memoryBytes() const;
};
[[nodiscard]] std::unique_ptr<LifeWorld> buildLifeWorld(const LoadedWorld& w);

// The world clock as city life reads it (the corner's clock and calendar).
struct LifeClock {
    int day = 0;    // calendar day; a new day begins at midnight
    double t = 0.2; // the clock, 0..1: hour = 6 + 24 t
    int season = 0; // index into the catalog's seasons
    bool rain = false;
    [[nodiscard]] double hour() const;    // 0..24
    [[nodiscard]] double seconds() const; // real seconds since day 0 06:00
    [[nodiscard]] static LifeClock at(int day, double hour, int season, bool rain = false);
};

// A stable reference to a live actor: stale once it is gone.
struct Handle {
    std::uint16_t index = 0xFFFF;
    std::uint16_t gen = 0;
    friend constexpr bool operator==(Handle, Handle) = default;
};

enum class Source : std::uint8_t { Population, Figure, Chain, Token, Cast };
enum class ActState : std::uint8_t { Idle, Travel, Act, Wander, Inside, Follow, Puppet, Leave };

// One live actor as the renderer draws it.
struct DrawActor {
    Handle handle;
    Vec2 pos;          // continuous tile coordinates, interpolated (x.5: a tile centre)
    float stride = 0;  // tiles walked, interpolated: pick walk frames by distance (no sliding)
    float speed = 0;   // tiles/s now
    float heading = 0; // radians in grid space (0: +x, pi/2: +y), continuous
    float z = 0;       // floor height, px above level 0 (stairs and walk floors included)
    std::uint8_t level = 0;
    std::uint8_t facing =
        0; // 0 front (+x), 1 front mirrored (+y), 2 back (-y), 3 back mirrored (-x)
    std::uint16_t kind = 0; // LifeData::kinds: sprite prefix, variants, animations
    std::uint8_t variant = 0;
    std::uint16_t anim = 0; // LifeData::animNames ("move", "idle", "serve" ...)
    float animTime = 0;     // seconds into the animation (frame = animTime * fps)
    float alpha = 1;        // fading in from a doorway or out into one
    int goods = -1;         // LifeData::goods carried, -1: none
    std::uint8_t goodsCount = 0;
    bool translucent = false; // memories
    int item = -1;            // map item whose walk tile it stands on (draw order), -1: ground
    bool floor = false;       // that tile is a walk-run floor: drawn after the floor piece
};

// A one-shot sound or effect of the last step, at a place.
struct LifeSound {
    int sound = -1; // LifeData::sounds
    bool fx = false;
    Vec2 at;
    int region = -1;
};

// A sound that lasts: a running event's ambience, a working place's loop.
struct LifeLoop {
    int sound = -1;
    float gain = 1;
    Vec2 at;
    int event = -1; // running event slot, -1 for a work loop
};

// A running (or abstractly running) event.
struct RunningEvent {
    int region = -1;
    int event = -1;
    double start = 0; // seconds since day 0 06:00
    double end = 0;
    int occurrence = 0;      // index of the occurrence in the day
    std::uint32_t trail = 0; // route tiles in the event's trail buffer
    float length = 0;        // route length, tiles
    Vec2 place;              // where it happens (route end, or its zone)
    bool active = false;     // its place or route touches the active area
};

struct DistrictCount {
    int region = -1;
    int district = -1;  // in the region
    float expected = 0; // the data's population over the active chunks (out of doors now)
    float formula = 0;  // the same without schedules (citylife.population)
    int live = 0;       // population actors of it alive and visible
    int inside = 0;     // alive but indoors
};

struct LifeStats {
    int live = 0;
    int visible = 0;
    std::array<int, 5> bySource{};
    int queued = 0;
    int tokens = 0;
    int tokensLive = 0;
    int running = 0;
    int chains = 0;
    float scale = 1; // population scale the cap required
    int spawnedThisStep = 0;
    int tablesBuilt = 0;
    int failedSteps = 0;
};

// The pooled record of a live actor (internal to CityLife; exposed for the inline templates).
struct LiveActor {
    struct Frame {
        std::uint16_t block = 0;
        std::uint8_t pc = 0;
        std::uint8_t n = 0;
    };
    std::uint64_t rng = 0; // its random stream (SplitMix64 state)
    std::uint64_t key = 0; // its identity: the same person every time it is materialised
    Vec2 pos;              // continuous tile coordinates
    Vec2 prev;             // at its previous update, for interpolation
    float z = 0;
    float prevZ = 0;
    float timer = 0; // seconds left in the step
    float animTime = 0;
    float alpha = 0;
    float speed = 0.9f; // tiles/s it walks at
    float s = 0;        // distance along its track (route tiles from the track's start)
    float speedNow = 0; // tiles/s now (eased; measured from the motion)
    float heading = 0;  // radians in grid space (atan2 of dy, dx)
    float stride = 0;   // tiles walked so far: the walk cycle's phase
    float prevStride = 0;
    float lateral = 0; // its own offset from the way's middle, tiles
    float rate = 1;    // its animations' pace (crowds out of step)
    Vec2 endPoint;     // where the track ends (a slot spot, a tile centre)
    Vec2 startOffset;  // where it stood off the start tile's centre (eased away)
    Route route;
    Tile16 tile;   // the tile it stands on
    Tile16 anchor; // a wander's centre
    std::array<Frame, 3> stack{};
    std::uint32_t step = 0xFFFFFFFF; // LifeData::steps index running
    std::int32_t group = -1;         // reserved slot group
    std::int32_t slot = -1;          // the WorldSlot spot it stands at
    std::int32_t home = -1;          // map item it belongs to (per-item populations)
    std::int32_t follow = -1;        // pool index it follows
    std::int32_t a = -1;             // puppets: chain run, token, running event
    std::int32_t b = -1;             // puppets: worker, instance, member
    std::uint16_t gen = 0;
    std::uint16_t kind = 0;
    std::int16_t role = -1;
    std::int16_t district = -1; // life district in its region
    std::int16_t goods = -1;
    std::int16_t zone = -1; // a wander's district
    std::uint16_t anim = 0;
    std::uint8_t goodsCount = 0;
    std::uint8_t region = 0;
    std::uint8_t depth = 0;
    std::uint8_t sched = 0xFF; // schedule block running
    std::uint8_t face = 0xFF;  // facing to keep at its slot
    std::uint8_t facing = 0;
    std::uint8_t variant = 0;
    std::uint8_t flags = 0;
    ActState state = ActState::Idle;
    Source source = Source::Population;
};
namespace live_flag {
inline constexpr std::uint8_t kAlive = 1;
inline constexpr std::uint8_t kUnwanted = 2; // its identity is no longer desired
inline constexpr std::uint8_t kRain = 4;     // running its rain routine
inline constexpr std::uint8_t kTranslucent = 8;
inline constexpr std::uint8_t kFadeIn = 16;
inline constexpr std::uint8_t kFadeOut = 32;
inline constexpr std::uint8_t kInterrupt = 64; // running a reactive event's steps
} // namespace live_flag

class CityLife {
public:
    CityLife(LifeWorld& w, std::uint64_t seed);
    ~CityLife();
    CityLife(const CityLife&) = delete;
    CityLife& operator=(const CityLife&) = delete;

    // The camera: the view in world tiles. Active chunks are those touching it grown by
    // tuning::life::kLiveMargin. An empty rect deactivates everything.
    void setView(TileRect view);
    // A view of `halfW` x `halfH` tiles each side around `centre`.
    void setFocus(TilePos centre, int halfW = 16, int halfH = 16);
    [[nodiscard]] TileRect view() const { return view_; }
    [[nodiscard]] TileRect activeRect() const { return active_; }

    // One fixed step of `dt` seconds (1/60).
    void update(const LifeClock& clock, float dt);
    // Brings the active area to its full population at once (arrival, tests, dumps).
    void settle(const LifeClock& clock);

    // Drawing.
    std::size_t gather(TileRect rect, float alpha, std::span<DrawActor> out) const;
    template <typename F>
    void forEachLive(F&& f) const;
    // Sound.
    [[nodiscard]] std::span<const LifeSound> sounds() const { return sounds_; }
    template <typename F>
    void forEachLoop(F&& f) const;
    // Goods stacked at slots (chain stocks): f(const world::WorldSlot&, goods, count).
    template <typename F>
    void forEachStock(TileRect rect, F&& f) const;
    // Item states the life switches (lit, open, firing) for a map item, as ItemState bits.
    [[nodiscard]] std::uint8_t itemState(std::uint32_t item) const;

    // Queries.
    [[nodiscard]] const LifeWorld& lifeWorld() const { return *w_; }
    [[nodiscard]] const LifeStats& stats() const { return stats_; }
    [[nodiscard]] const LifeClock& clock() const { return clock_; }
    [[nodiscard]] const Chains& chains() const { return chains_; }
    [[nodiscard]] std::span<const RunningEvent> running() const { return running_; }
    [[nodiscard]] std::span<const Tile16> trail(const RunningEvent& e) const;
    [[nodiscard]] const std::vector<DistrictCount>& districtCounts() const { return counts_; }
    [[nodiscard]] bool alive(Handle h) const;
    // Per live actor, for dumps and tests.
    struct Info {
        Handle handle;
        Source source;
        ActState state;
        int region;
        int role;     // in its region, -1 for tokens and casts
        int district; // in its region, -1
        int kind;
        TilePos tile;
        Vec2 pos;
        int level;
        int step; // LifeData::steps index running, -1
        int goods;
        int goodsCount;
        int slot; // reserved WorldSlot group, -1
        bool visible;
        std::uint64_t key;
    };
    template <typename F>
    void forEachInfo(F&& f) const;
    // Every reserved slot group and its count (tests: never over capacity).
    template <typename F>
    void forEachReservation(F&& f) const;
    [[nodiscard]] std::size_t memoryBytes() const;
    [[nodiscard]] int liveCount() const { return stats_.live; }
    // Tests and the bench: replace the population scale (0: automatic by the cap).
    void forceScale(float s) {
        forcedScale_ = s;
        dirty_ = true;
    }
    // The bench's crowd-size study: another cap than tuning::life::kLiveCap.
    void setLiveCap(int cap) {
        liveCap_ = cap;
        dirty_ = true;
    }
    // Day-plan occurrences of a region's events for a day: (event, start, end) in seconds.
    void dayPlan(int region, int day, int season,
                 std::vector<std::tuple<int, double, double>>& out) const;
    [[nodiscard]] bool festivalOn(int region, int festival, int day, int season) const;
    // `season`, or the world calendar's for `day` when it is -1.
    [[nodiscard]] int seasonFor(int day, int season) const;
    // The calendar month of `day` in that season (-1: the calendar's own).
    [[nodiscard]] int monthFor(int day, int season) const;
    // The data's population (out of doors, by the schedules) over the chunks a view would make
    // live at a clock, without changing anything: what the cap must hold there.
    [[nodiscard]] float expectedFor(TileRect view, const LifeClock& clock);

    struct Desire {
        std::uint64_t key = 0;
        Source source = Source::Population;
        std::int16_t region = -1;
        std::int16_t role = -1;
        std::int16_t district = -1;
        std::int16_t kind = -1;
        std::int32_t a = -1; // per-item instance (map item), chain run, token, running event
        std::int32_t b = -1; // chain worker, token instance, cast member
        std::uint32_t chunk = 0;
        float order = 0; // squared distance to the view centre: nearer spawn first
    };
    struct KeyIndex;
    using Actor = LiveActor;

private:
    // The clock, the plans, chains, events and tokens (no live actor moves).
    void advanceAbstract(const LifeClock& clock);
    // Population and materialisation.
    void reconcile();
    void desireChunk(std::uint32_t chunk);
    void spawnQueued(bool unbounded);
    int allocate();
    void release(int i);
    void materialise(int i, const Desire& d);
    void beginLeave(int i);
    // Behaviour.
    void think(int i, float dt);
    void chooseRoutine(int i);
    bool runSteps(int i, bool fastForward, double& budget);
    enum class Begin : std::uint8_t { Instant, Timed, Travel, Hold, Failed, Wait };
    Begin beginStep(int i, std::uint32_t s, float& estimate);
    void endStep(int i);
    bool untilMet(const Actor& a) const;
    void move(int i, float dt); // Motion: a track is the route's next tiles, walked as a smoothed
                                // continuous path.
    void startTrack(int i, Vec2 end);
    void fillTrack(int i);
    [[nodiscard]] bool moving(int i) const;
    [[nodiscard]] Vec2 trackRaw(int i, float s) const;
    [[nodiscard]] Vec2 trackPoint(int i, float s, bool lateral) const;
    void placeOnTrack(int i, float maxStep); // maxStep 0: wherever the track has it
    void motion(int i, float dt);            // every step: eased speed along the track
    void advanceBy(int i, float tiles);      // fast-forward: straight to a distance along it
    void afterStep(int i, float dt);         // speed, heading, facing and stride from the motion
    bool planTo(int i, TilePos goal, Vec2 end, int& builds);
    [[nodiscard]] Vec2 smoothAlong(std::span<const Tile16> line, float s) const;
    [[nodiscard]] Vec2 settleOnGround(Vec2 raw, Vec2 want) const;
    [[nodiscard]] static float atLength(std::span<const float> cum, float d);
    const std::vector<Tile16>& carrierPath(std::size_t key, TilePos from, TilePos to);
    struct TokenAt {
        Vec2 pos;
        std::uint8_t facing = 0;
        bool moving = false;
    };
    // Where token instance `k` of token `t` (or its group member) is now.
    bool tokenAt(std::size_t t, int k, int member, TokenAt& out) const;
    [[nodiscard]] int memberKind(const Token& tk, int member) const;
    bool resolve(int i, const Target& t, TilePos& goal, int& group, Vec2& at, float& z,
                 std::uint8_t& face);
    int nearestDoor(Vec2 p, float reach, TilePos& goal) const;
    void reserve(int i, int group);
    void unreserve(int i);
    void puppet(int i);
    // Abstract layers.
    void planDay(int region, int day, bool continuing);
    void updateEvents();
    void startEvent(int region, int event, double start, double end, int occurrence);
    void buildTrail(RunningEvent& e);
    void updateTokens();
    [[nodiscard]] bool eventRunning(int region, int event) const;
    void setItemState(std::uint32_t item, ItemState s, double until);
    // Index.
    void link(int i);
    void unlink(int i);
    [[nodiscard]] bool inView(Vec2 p) const;
    [[nodiscard]] bool festivalToday(int region, int festival) const;
    [[nodiscard]] bool filterPasses(const LifeRegion& r, const Filter& f) const;
    // A filter's calendar terms that hold for a whole day: its months and its day of the season.
    [[nodiscard]] bool dayPasses(const Filter& f, int day, int season) const;
    [[nodiscard]] bool tokenOn(const Token& tk) const; // travels today (its `when`)
    [[nodiscard]] int blockAt(int region, const Role& role) const;
    void countDistricts();

    LifeWorld* w_;
    const WorldMap* map_;
    std::uint64_t seed_;
    LifeClock clock_;
    double now_ = 0; // seconds since day 0 06:00
    float hour_ = 0;
    int hourIndex_ = -1;
    int day_ = -1;
    std::uint32_t frame_ = 0;
    TileRect view_;
    TileRect active_;
    std::vector<std::uint8_t> chunkActive_;
    std::vector<double> chunkSeen_;
    std::vector<std::uint32_t> activeChunks_;
    bool dirty_ = true;
    float forcedScale_ = 0;
    int liveCap_ = tuning::life::kLiveCap;
    float scale_ = 1;
    double lastReconcile_ = -1e9;
    int builds_ = 0; // next-hop tables this step may still build
    bool waited_ = false;
    bool materialising_ = false;

    std::vector<LiveActor> pool_;
    std::vector<std::array<Tile16, tuning::life::kMoveReach + 2>> desc_;
    struct Track {
        std::array<Tile16, 8> t{};
        int base = 0;       // route index of t[0]
        std::uint8_t n = 0; // tiles held
        bool ended = true;  // the route has no more tiles
    };
    std::vector<Track> tracks_;
    std::vector<float> trailCum_; // per trail tile: smoothed length from the trail's start
    struct Stops {
        std::array<std::uint16_t, 32> at{}; // trail indices of relay stations on the route
        std::uint8_t n = 0;
    };
    std::vector<Stops> trailStops_;
    std::vector<std::vector<Tile16>> carrierPaths_; // per chain run and stage, made once
    std::vector<std::vector<float>> carrierCum_;
    std::vector<int> free_;
    std::vector<int> chunkHead_; // per map chunk: first live actor, -1
    std::vector<int> chunkNext_; // per pool record
    std::vector<int> chunkOf_;   // per pool record
    std::unique_ptr<KeyIndex> keys_;
    std::vector<Desire> desires_;
    std::vector<Desire> queue_;
    std::size_t queueHead_ = 0;
    std::vector<std::uint8_t> groupCount_;
    std::vector<std::uint8_t> slotCount_;
    std::vector<std::uint8_t> itemState_;
    std::vector<float> itemStateUntil_;
    Chains chains_;
    std::vector<RunningEvent> running_;
    std::vector<Tile16> trails_; // kMaxRunningEvents * kEventTrail
    std::vector<std::vector<std::tuple<int, double, double>>> plans_; // per region: today's plan
    std::vector<std::size_t> planNext_;
    std::vector<double> reactiveCool_;
    double lastStart_ = -1e9;
    double lastNow_ = -1e18;
    std::vector<std::tuple<int, double, double>> planScratch_;
    struct TokenState {
        std::vector<Vec2> line; // polyline (tile coordinates)
        std::vector<float> cum; // cumulative length
        float length = 0;
        float period = 0;
        float farStay = 0; // seconds at the far end (in port, or working a fishing ground)
        bool fishing = false;
        bool ok = false;
    };
    std::vector<TokenState> tokenPaths_;
    std::vector<std::array<double, 2>> tokenLast_; // per token instance: last phase
    std::vector<LifeSound> sounds_;
    std::vector<DistrictCount> counts_;
    std::vector<Desire> scratchDesires_;
    std::vector<DistrictCount> scratchCounts_;
    LifeStats stats_;
};

template <typename F>
void CityLife::forEachLive(F&& f) const {
    for (const LiveActor& a : pool_)
        if ((a.flags & live_flag::kAlive) != 0) f(a);
}

template <typename F>
void CityLife::forEachLoop(F&& f) const {
    const auto& data = w_->data;
    for (std::size_t e = 0; e < running_.size(); ++e) {
        const RunningEvent& r = running_[e];
        if (!r.active || r.event < 0) continue;
        const Event& ev = data.regions[static_cast<std::size_t>(r.region)]
                              .events[static_cast<std::size_t>(r.event)];
        if (ev.ambience >= 0)
            f(LifeLoop{ev.ambience, ev.ambienceGain, r.place, static_cast<int>(e)});
    }
}

template <typename F>
void CityLife::forEachStock(TileRect rect, F&& f) const {
    const auto& slots = map_->slots();
    for (std::size_t i = 0; i < chains_.size(); ++i) {
        const ChainRun& run = chains_.run(i);
        if (!run.ok()) continue;
        for (const ChainRun::Counter& c : run.counters()) {
            const ChainPlace& p = run.place(c.ref);
            if (p.slot < 0 || c.count <= 0) continue;
            const world::WorldSlot& s = slots[static_cast<std::size_t>(p.slot)];
            if (rect.contains(s.tile)) f(s, c.goods, c.count);
        }
    }
}

template <typename F>
void CityLife::forEachInfo(F&& f) const {
    for (std::size_t i = 0; i < pool_.size(); ++i) {
        const LiveActor& a = pool_[i];
        if ((a.flags & live_flag::kAlive) == 0) continue;
        Info in{};
        in.handle = {static_cast<std::uint16_t>(i), a.gen};
        in.source = a.source;
        in.state = a.state;
        in.region = a.region;
        in.role = a.role;
        in.district = a.district;
        in.kind = a.kind;
        in.tile = a.tile.pos();
        in.pos = a.pos;
        in.level = map_->inBounds(a.tile.pos()) ? map_->level(a.tile.pos()) : 0;
        in.step = a.step == 0xFFFFFFFF ? -1 : static_cast<int>(a.step);
        in.goods = a.goods;
        in.goodsCount = a.goodsCount;
        in.slot = a.group;
        in.visible = a.state != ActState::Inside && a.alpha > 0.0f;
        in.key = a.key;
        f(in);
    }
}

template <typename F>
void CityLife::forEachReservation(F&& f) const {
    for (std::size_t g = 0; g < groupCount_.size(); ++g)
        if (groupCount_[g] > 0) f(static_cast<int>(g), int(groupCount_[g]), int(w_->groupCap[g]));
}

} // namespace lc::life
