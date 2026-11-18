#pragma once
// The shared actor system (docs/design/living-world.md §2, tasks W1 and W2): one pool of small
// fixed records for everything that moves in the home region — visitors read as actor kinds and
// the resident. Each actor runs its kind's routines (steps interpreted from the catalog's
// program), picks targets among items' slots with reservations so no two share a seat, finds its
// way on the grid, reacts to the world changing under it, to rain, to placements nearby and to
// being petted. Every random choice comes from a per-actor stream derived from the game's seed,
// so a scripted run is reproducible. Pure logic: no SDL.

#include "core/actor_data.hpp"
#include "core/catalog.hpp"
#include "core/condition.hpp"
#include "core/flat_count.hpp"
#include "core/iso.hpp"
#include "core/path.hpp"
#include "core/tuning.hpp"
#include "core/visitors.hpp"
#include "core/world.hpp"

#include <array>
#include <cstdint>
#include <span>
#include <string>
#include <vector>

namespace lc {

class Weather;

// front faces +x (down-right), back faces -y (up-right); the mirrored pair covers +y and -x.
enum class Facing : std::uint8_t { Front, FrontMirrored, Back, BackMirrored };

enum class ActorState : std::uint8_t {
    Choose, // between steps
    Travel, // on its way somewhere
    Act,    // using a slot, waiting, idling
    Inside, // gone into an item (hidden, still simulated)
    Follow  // keeping behind (or on) someone
};

namespace actor_flag {
inline constexpr std::uint16_t kAlive = 1u << 0;
inline constexpr std::uint16_t kLeaving = 1u << 1;
inline constexpr std::uint16_t kOnHat = 1u << 2;      // resting on the resident's hat
inline constexpr std::uint16_t kErrand = 1u << 3;     // going somewhere it was called to
inline constexpr std::uint16_t kFleeing = 1u << 4;    // startled, hurrying away
inline constexpr std::uint16_t kFollower = 1u << 5;   // in a line behind another
inline constexpr std::uint16_t kFadeOut = 1u << 6;    // going inside, or leaving by fading
inline constexpr std::uint16_t kGone = 1u << 7;       // left for good once faded
inline constexpr std::uint16_t kPause = 1u << 8;      // a short rest that is no step of a routine
inline constexpr std::uint16_t kSheltered = 1u << 9;  // went for shelter in this spell of rain
inline constexpr std::uint16_t kStepAside = 1u << 10; // displaced: stepping to open ground
inline constexpr std::uint16_t kHomeRetry = 1u << 11; // a leaver already set out home twice
inline constexpr std::uint16_t kCrowd = 1u << 12;     // the bench's crowd: outside the counts
} // namespace actor_flag
inline constexpr std::uint8_t kPathPending = 0xFF; // waiting for a path search this step

// One frame of a routine being run: a block and the step reached in it.
struct ActorFrame {
    std::uint16_t block = 0;
    std::uint8_t pc = 0;
    std::uint8_t n = 0; // iterations done (each), or kLoopFrame for a looping routine
};
inline constexpr std::uint8_t kLoopFrame = 0x80;
inline constexpr int kActorStack = 4;

// The fixed runtime record (living-world.md §2.4): 96 bytes, plain data.
struct Actor {
    std::uint64_t rng = 0; // this actor's random stream (SplitMix64 state)
    Vec2 pos;              // continuous tile coordinates
    Vec2 goal;             // where the current travel ends
    float timer = 0;       // time left in the current step
    float call = 0;        // time to the next call animation; a wander's remaining time
    float animTime = 0;
    float stride = 0; // tiles walked, swum or flown: moving animations advance by it
    float alpha = 0;
    float lift = 0;        // pixels above the ground (a seat, a perch, flight)
    float overlay = 0;     // pet or startle reaction time left
    std::int16_t resX = 0; // reserved slot: the item's origin (or the tile)
    std::int16_t resY = 0;
    std::uint16_t resType = 0;
    std::uint8_t resSlot = 0;
    std::uint8_t resSpot = 0;
    std::array<ActorFrame, kActorStack> stack{};
    std::uint16_t kind = 0;
    std::uint16_t flags = 0;
    std::uint8_t depth = 0;
    std::uint8_t anim = 1;
    Facing facing = Facing::Front;
    ActorState state = ActorState::Choose;
    std::uint8_t sched = 0xFF; // schedule block it runs (resident)
    std::uint8_t goods = 0xFF;
    std::uint8_t goodsCount = 0;
    std::uint8_t pathLen = 0;
    std::uint8_t pathPos = 0;
    std::uint8_t prio = 0;        // priority of the interrupt it is running, 0: none
    std::uint8_t overlayAnim = 0; // animation of the reaction
    std::uint8_t rainHold = 0;    // tenths of a second rain has held here
    std::uint8_t petCool = 0;     // tenths of a second until it can be petted again
    std::uint8_t startleCool = 0; // tenths of a second until it startles again
    bool reserved = false;
};
static_assert(sizeof(Actor) <= 96, "the actor record is 96 bytes");

// In the air (or on her hat): drawn over everything. A flyer resting on its slot (a flower, a
// perch, the hive) is depth-sorted like a walker, behind what stands in front of it (Q3-13).
[[nodiscard]] inline bool inAir(const Actor& a, const ActorKind& k) {
    if ((a.flags & actor_flag::kOnHat) != 0) return true;
    return k.move == Locomotion::Fly && (a.state != ActorState::Act || !a.reserved);
}

struct ActorEvent {
    enum class Kind : std::uint8_t {
        Arrived, // a visitor came (first: its first sighting)
        Voice,   // its call
        Say,     // the resident speaks: `arg` is a line context
        Emit,    // a sound: `arg` indexes Catalog::emitSounds
        Effect,  // an effect hook: `arg` is the Effect, `item` the item it acts on
        Pet,     // petted: a heart and a sound
        Startle, // startled by a placement
        Goods    // goods changed hands
    };
    Kind kind = Kind::Arrived;
    int actor = -1;
    int kind_ = 0; // actor kind
    Vec2 pos;
    int arg = -1;
    TilePos item;
    bool first = false;
};

// A nook instance whose `prefer` effect weighs targets inside it.
struct PreferArea {
    int kind = -1;     // actor kind
    int activity = -1; // Catalog::activityNames
    NearInstance area;
};

// A nook instance that exists now (for nook targets and strolls).
struct NookPlace {
    int nook = 0;
    NearInstance area;
};

// What the actors see this step.
struct ActorEnv {
    const World* world = nullptr;
    TileRect area; // the active area: actors live inside it
    std::span<const VisitorGate> gates;
    double clock = 0.2; // time of day, 0..1
    bool pinned = false;
    Phase phase = Phase::Day;
    int season = 0;
    int day = 0;
    CondFacts facts; // world facts for conditions; `raining` is replaced by the weather per actor
    const Weather* weather = nullptr; // rain at a point; null: `facts.raining` everywhere
    bool snow = false;                // rain falls as snow
    std::span<const PreferArea> prefer;
    std::span<const NookPlace> nooks;
    double now = 0; // play seconds, for "placed in the last ten minutes"
};

class Actors {
public:
    Actors(const Catalog& cat, std::uint64_t seed);

    void update(const ActorEnv& env, float dt);
    // Spawns the population the area attracts at once, for the kinds already seen (after
    // loading), and places the resident where her schedule has her now.
    void populate(const ActorEnv& env);

    [[nodiscard]] std::span<const Actor> all() const { return pool_; }
    [[nodiscard]] std::span<const ActorEvent> events() const { return events_; }
    void clearEvents() { events_.clear(); }
    [[nodiscard]] bool alive(int i) const {
        return (pool_[static_cast<std::size_t>(i)].flags & actor_flag::kAlive) != 0;
    }
    [[nodiscard]] int resident() const { return resident_; }
    // A visible, purposeful mover (living-world.md §1.1): travelling or acting at a slot.
    [[nodiscard]] bool purposeful(const Actor& a) const;
    [[nodiscard]] bool asleep(const Actor& a) const;
    [[nodiscard]] bool hidden(const Actor& a) const {
        return a.state == ActorState::Inside && a.alpha <= 0.0f;
    }

    // The visitor journal.
    [[nodiscard]] bool seen(int visitor) const {
        return seen_[static_cast<std::size_t>(visitor)] != 0;
    }
    void markSeen(int visitor) { seen_[static_cast<std::size_t>(visitor)] = 1; }
    [[nodiscard]] std::span<const std::uint8_t> seenFlags() const { return seen_; }
    [[nodiscard]] int seenCount() const;
    // Visitors present per kind, not counting leavers (refreshed by update and populate).
    [[nodiscard]] std::span<const int> presence() const { return presence_; }
    [[nodiscard]] int present(int visitor) const {
        return presence_[static_cast<std::size_t>(visitor)];
    }

    // The player's touch. Petting gives a heart; clicking the resident makes her speak.
    bool pet(int actor);
    // Something was placed, moved or removed over `rect`: critters nearby startle, the resident
    // steps aside or turns to look. `type` is the item placed (-1: painted water, -2: removed),
    // `fresh` true when it is the first of its kind in the corner.
    void disturb(const ActorEnv& env, TileRect rect, int type, bool fresh);
    // A bed was picked: hens nearby come to peck; the resident, if near, carries it home.
    // Returns true when she takes it.
    bool harvested(const ActorEnv& env, TilePos bed);
    // The resident walks over to `tile`, if it is within `reach`, and says a line there (a nook
    // just found); with `sketch` she sits down to draw what is there (a new visitor).
    void visit(const ActorEnv& env, Vec2 tile, int context, float reach, bool sketch = false);
    // The resident turns to the player and waves (greeting them when the corner opens).
    void wave();
    // Idle critters that watch the pointer turn to face it.
    void lookAt(std::optional<TilePos> tile);
    // Plays a visitor's call animation (an event asking the frog to croak). Returns its actor.
    int call(int visitor);

    // The resident is about: not asleep, not inside (wishes come from her then).
    [[nodiscard]] bool residentAvailable() const;
    // Her home cottage (an item origin), if she has one.
    [[nodiscard]] std::optional<TilePos> residentHome() const { return home_; }

    // Fills the area with `count` more visitors of every kind in turn, wherever each may stand,
    // whatever their needs (the bench's crowd). Returns how many were placed.
    int crowd(const ActorEnv& env, int count);
    // The resident's schedule block for the time `env` gives (her own clock while it is pinned).
    [[nodiscard]] int scheduleBlock(const ActorEnv& env) const;
    // The population rule (Q3-02): never more of a visitor present than its max (plus what nooks
    // allow), and no leaver lingering past kLeaveLimitSeconds on its way out. Empty when it holds,
    // else what breaks it.
    [[nodiscard]] std::string populationError(std::span<const VisitorGate> gates) const;
    // Path-finding budget used this step (searches), for the bench.
    [[nodiscard]] int searches() const { return searches_; }

private:
    struct Reservation {
        std::int16_t x, y; // the item's origin (or the tile)
        std::uint16_t type;
        std::uint8_t slot, spot;
        std::uint16_t actor;
        std::int16_t tx = -1, ty = -1; // the tile it stands on, for spots on the ground
    };
    // A chosen place to go: a point, how high it is, which way to face, what it reserves.
    struct Pick {
        Vec2 point;
        float lift = 0;
        std::uint8_t face = 0xFF; // 0..3, 0xFF: free
        bool reserve = false;
        Reservation res{};
        Vec2 look{-1, -1}; // face this point on arrival (an item, a visitor)
    };
    struct Errand {
        Vec2 point;        // where to go (a startle: what it flees from)
        Vec2 look{-1, -1}; // what to face there
        float dur = 0;
        std::uint8_t anim = 1;
        int say = -1;
    };

    // Presence (who comes and goes), from the visitor rules.
    void presence(const ActorEnv& env, float dt);
    int spawn(const ActorEnv& env, int kind, float alpha, bool fromHome);
    // Puts `a` in pool slot `slot` (a free one, or the end), resetting its per-actor arrays.
    void claim(std::size_t slot, const Actor& a);
    void countPresence();
    void leave(const ActorEnv& env, int i);
    // Where an actor comes out of an item: its door, else its first slot, else beside it.
    [[nodiscard]] std::optional<Vec2> doorOf(const ActorEnv& env, const Item& it) const;
    bool anchor(const ActorEnv& env, int visitor, TilePos& out, std::uint64_t& rng) const;

    // Behaviour.
    void tick(const ActorEnv& env, int i, float dt);
    void run(const ActorEnv& env, int i);
    void restart(int i);
    void push(Actor& a, int block, std::uint8_t n);
    void advance(Actor& a);
    enum class Start : std::uint8_t { Done, Running, Failed };
    Start start(const ActorEnv& env, int i, const Step& s);
    void arrive(const ActorEnv& env, int i, const Step& s);
    void finishFailed(int i);
    void beginErrand(const ActorEnv& env, int i);
    void flee(const ActorEnv& env, int i);
    [[nodiscard]] int lineAhead(int i) const;
    void updateLines(const ActorEnv& env);
    [[nodiscard]] int waterBody(const World& world, Vec2 p) const;
    void chooseRoutine(const ActorEnv& env, int i);
    [[nodiscard]] float hour(const ActorEnv& env) const;
    bool interrupts(const ActorEnv& env, int i, float dt);
    void beginInterrupt(int i, const Interrupt& in);
    void finishStep(const ActorEnv& env, int i);
    void travel(const ActorEnv& env, int i, float dt);
    void follow(const ActorEnv& env, int i, float dt);
    bool goTo(const ActorEnv& env, int i, const Pick& p, bool bank = false);
    bool plan(const ActorEnv& env, int i, bool bank);
    [[nodiscard]] bool untilMet(const ActorEnv& env, const Actor& a, const Step& s) const;
    void fireEffect(const ActorEnv& env, int i, Effect e);
    void say(int i, int context);
    void validate(const ActorEnv& env, int i);

    // Targets and slots.
    bool resolve(const ActorEnv& env, int i, const Target& t, int activity, Pick& out);
    bool slotPick(const ActorEnv& env, int i, const Item& it, const Target& t, Pick& out,
                  float& weight);
    [[nodiscard]] float prefer(const ActorEnv& env, int kind, int activity, TilePos t) const;
    bool bankPick(const ActorEnv& env, int i, bool shore, Pick& out);
    bool wanderPick(const ActorEnv& env, int i, float radius, Pick& out, int activity = -1);
    bool poiPick(const ActorEnv& env, int i, Poi poi, int activity, Pick& out, int nook = -1);
    bool homePick(const ActorEnv& env, int i, int slot, Pick& out);
    [[nodiscard]] const Item* homeItem(const ActorEnv& env, const Actor& a) const;
    // Reservations on that slot (or spot) by anyone but `self`.
    [[nodiscard]] int taken(const Reservation& r, int self) const;
    void reserve(int i, const Reservation& r, Vec2 at);
    // Someone other than `self` means to stand on this tile.
    [[nodiscard]] bool tileTaken(TilePos t, int self) const;
    void release(int i);
    bool freeTile(const ActorEnv& env, const Actor& a, TilePos t) const;
    [[nodiscard]] bool rainAt(const ActorEnv& env, Vec2 p) const;
    [[nodiscard]] CondFacts factsFor(const ActorEnv& env, const Actor& a) const;
    void updateHome(const ActorEnv& env);

    // Per-actor randomness.
    static float uniform(Actor& a);
    static float range(Actor& a, float lo, float hi) { return lo + (hi - lo) * uniform(a); }
    static int range(Actor& a, int lo, int hi);

    const Catalog* cat_; // a pointer, so a fresh one can be assigned when another world opens
    std::uint64_t seed_;
    std::uint64_t spawned_ = 0; // spawn counter: each actor's stream key
    std::vector<Actor> pool_;
    static constexpr std::size_t kPathTiles = 24; // a longer trip is re-planned on the way
    std::vector<std::array<TilePos, kPathTiles>> paths_;
    struct CachedPath {
        std::uint64_t rev = ~0ULL; // world revision it was found in
        TilePos from;
        TilePos to;
        Locomotion move = Locomotion::Walk;
        bool bank = false;
        std::uint8_t len = 0;
        std::array<TilePos, kPathTiles> tiles{};
    };
    std::array<CachedPath, 32> pathCache_{};
    std::size_t pathNext_ = 0;
    std::vector<Errand> errands_;
    std::vector<Pick> dests_; // where each is going (or the element of its each)
    // The elements an `each` has visited this time (items by origin), per actor.
    struct Visited {
        std::array<TilePos, 16> at{};
        std::uint8_t count = 0;
    };
    std::vector<Visited> visited_;
    bool eachNext_ = false; // the next start() of an each continues it (else it starts afresh)
    // Lines: who follows whom (per kind and body of water), and followers that gave up.
    std::vector<int> lineAhead_;
    std::vector<float> stuck_;   // seconds a follower has been unable to move
    std::vector<float> lineBan_; // seconds before it may join a line again
    struct Inside {
        TilePos at{-1, -1};
        int type = -1; // -1: nothing recorded
    };
    std::vector<Inside> inside_;  // the item each actor went into
    std::vector<float> leaveAge_; // seconds since each leaver set out
    struct LineTail {
        std::uint16_t kind;
        int body;
        int actor;
    };
    std::vector<LineTail> lineTail_;
    std::vector<int> bodies_; // body of water per tile of bodyArea_, -1: land
    TileRect bodyArea_;
    std::uint64_t bodyRevision_ = ~0ULL;
    std::vector<TilePos> bodyOpen_;
    // Each actor holds at most one reservation (held_, valid while Actor::reserved); counts by
    // slot, spot and ground tile answer "taken?" without scanning (Q3 scaling list).
    std::vector<Reservation> held_;
    FlatCount reserved_{tuning::kActorPool * 4};
    // Records freed (lowest first): spawning takes one without scanning the pool.
    std::vector<int> freed_; // a min-heap
    void pushFreed(int i);
    void popFreed();
    std::vector<ActorEvent> events_;
    PathFinder finder_;
    const World* map_ = nullptr; // the world of this update
    int searches_ = 0;
    int resident_ = -1;

    // Presence state, per visitor.
    TileRect area_;
    std::uint64_t tallyRevision_ = ~0ULL;
    Tally tally_;
    std::vector<std::uint8_t> seen_;
    std::vector<int> presence_;
    std::vector<float> cooldown_;

    // The resident's world.
    std::optional<TilePos> home_;
    TilePos bedroll_;
    float sat_ = 0;         // seconds she has been sitting
    float reactCool_ = 0;   // seconds until she reacts to a placement again
    float clickCool_ = 0;   // seconds until a click makes her speak again
    float hourPrivate_ = 6; // her clock while the real one is pinned (R6.7)
    bool wasPinned_ = false;
    Phase pinPhase_ = Phase::Day;
    std::uint64_t saidMask_ = 0; // contexts her block's routine has said (once per block)
    bool blockDone_ = false;     // her block's routine ran to the end
    float tenths_ = 0;           // cooldown accumulator
    int ticks_ = 0;              // tenths of a second this step
    std::uint32_t frame_ = 0;    // steps taken, for the thinking buckets
    float bucketTenths_ = 0;
    int bucketTicks_ = 0; // tenths since a bucket last thought
    TilePos placedAt_;    // the last placement near her, for her reaction
    int placedType_ = -1;
    struct Recent {
        TilePos at;
        double when;
    };
    std::vector<Recent> recent_;                   // placements in the last ten minutes (strolls)
    std::vector<std::pair<TilePos, int>> watered_; // beds watered, and the day
    std::optional<TilePos> look_;                  // the pointer's tile, for watchers
};

} // namespace lc
