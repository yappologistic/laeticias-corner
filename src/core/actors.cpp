#include "core/actors.hpp"

#include "core/growth.hpp"
#include "core/rng.hpp"
#include "core/tuning.hpp"
#include "core/weather.hpp"

#include <algorithm>
#include <cassert>
#include <cmath>

namespace lc {
namespace {

using namespace actor_flag;

constexpr std::uint16_t kTileRes = 0xFFFF; // a reservation of a bare tile, not an item slot
constexpr std::uint8_t kImplicitOn = 0xFE;
constexpr std::uint8_t kImplicitBeside = 0xFD;
constexpr std::uint8_t kAnyTile = 0xFF; // a beside spot: the tile itself is the key

TilePos tileOf(Vec2 p) {
    return {static_cast<int>(std::floor(p.x)), static_cast<int>(std::floor(p.y))};
}

Vec2 centre(TilePos t) {
    return {static_cast<float>(t.x) + 0.5f, static_cast<float>(t.y) + 0.5f};
}

float dist(Vec2 a, Vec2 b) {
    return std::hypot(a.x - b.x, a.y - b.y);
}

Facing facingFor(Vec2 d) {
    if (std::abs(d.x) >= std::abs(d.y)) return d.x >= 0 ? Facing::Front : Facing::BackMirrored;
    return d.y >= 0 ? Facing::FrontMirrored : Facing::Back;
}

// 0 +x, 1 +y, 2 -x, 3 -y.
Facing facingOf(std::uint8_t dir) {
    static constexpr Facing kFacings[] = {Facing::Front, Facing::FrontMirrored,
                                          Facing::BackMirrored, Facing::Back};
    return kFacings[dir & 3];
}

// Distance from a point to a tile rectangle (0 inside it).
float distToRect(Vec2 p, TileRect r) {
    const float dx =
        std::max({static_cast<float>(r.x0) - p.x, 0.0f, p.x - static_cast<float>(r.x1)});
    const float dy =
        std::max({static_cast<float>(r.y0) - p.y, 0.0f, p.y - static_cast<float>(r.y1)});
    return std::hypot(dx, dy);
}

bool inArea(const NearInstance& n, TilePos t) {
    const TileRect& f = n.footprint;
    return t.x >= f.x0 - n.within && t.y >= f.y0 - n.within && t.x < f.x1 + n.within &&
           t.y < f.y1 + n.within;
}

float hourOfClock(double t) {
    return static_cast<float>(std::fmod(6.0 + 24.0 * t, 24.0));
}

bool hourIn(float h, float from, float to) {
    return from <= to ? h >= from && h < to : h >= from || h < to;
}

// The game hours a phase spans (dawn 03-06, day 06-18, dusk 18-21, night 21-03).
std::pair<float, float> phaseHours(Phase p) {
    switch (p) {
    case Phase::Dawn: return {3, 6};
    case Phase::Day: return {6, 18};
    case Phase::Dusk: return {18, 21};
    case Phase::Night: return {21, 27};
    }
    return {6, 18};
}

// A swimmer's point kept away from the edges of its water tile that meet land, so it is drawn
// on the water rather than over the bank.
Vec2 offShore(const World& w, Vec2 p) {
    const TilePos t = tileOf(p);
    if (!w.hasGround(t) || !w.isWater(t)) return p;
    const float m = tuning::kShoreMargin;
    const auto land = [&](int dx, int dy) {
        const TilePos q{t.x + dx, t.y + dy};
        return w.hasGround(q) && !w.isWater(q);
    };
    const auto fx = static_cast<float>(t.x);
    const auto fy = static_cast<float>(t.y);
    if (land(-1, 0)) p.x = std::max(p.x, fx + m);
    if (land(1, 0)) p.x = std::min(p.x, fx + 1 - m);
    if (land(0, -1)) p.y = std::max(p.y, fy + m);
    if (land(0, 1)) p.y = std::min(p.y, fy + 1 - m);
    return p;
}

std::uint64_t splitmix(std::uint64_t& s) {
    std::uint64_t z = (s += 0x9E3779B97F4A7C15ULL);
    z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL;
    z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL;
    return z ^ (z >> 31);
}

} // namespace

float Actors::uniform(Actor& a) {
    return static_cast<float>(splitmix(a.rng) >> 40) * (1.0f / 16777216.0f);
}

int Actors::range(Actor& a, int lo, int hi) {
    const auto span = static_cast<std::uint64_t>(hi - lo) + 1;
    return lo + static_cast<int>(splitmix(a.rng) % span);
}

Actors::Actors(const Catalog& cat, std::uint64_t seed)
    : cat_(&cat), seed_(seed), finder_(cat), seen_(cat.visitors.size(), 0),
      presence_(cat.visitors.size(), 0), cooldown_(cat.visitors.size(), 0.0f) {
    pool_.reserve(tuning::kActorPool);
    paths_.reserve(tuning::kActorPool);
    errands_.reserve(tuning::kActorPool);
    dests_.reserve(tuning::kActorPool);
    visited_.reserve(tuning::kActorPool);
    stuck_.reserve(tuning::kActorPool);
    inside_.reserve(tuning::kActorPool);
    leaveAge_.reserve(tuning::kActorPool);
    lineBan_.reserve(tuning::kActorPool);
    lineAhead_.reserve(tuning::kActorPool);
    lineTail_.reserve(16);
    bodyOpen_.reserve(256);
    reservations_.reserve(tuning::kActorPool);
    events_.reserve(tuning::kActorPool);
    recent_.reserve(64);
    watered_.reserve(32);
    tally_.terrain.reserve(cat.terrain.size());
    tally_.items.reserve(cat.items.size());
}

int Actors::seenCount() const {
    return static_cast<int>(std::ranges::count(seen_, std::uint8_t{1}));
}

bool Actors::purposeful(const Actor& a) const {
    if ((a.flags & kAlive) == 0 || a.alpha < 0.5f) return false;
    if (a.state == ActorState::Travel || a.state == ActorState::Follow) return true;
    return a.state == ActorState::Act && a.anim > 1;
}

bool Actors::asleep(const Actor& a) const {
    const ActorKind& k = cat_->kinds[a.kind];
    return k.sleepAnim != 0xFF && a.anim == k.sleepAnim && a.state == ActorState::Act;
}

bool Actors::residentAvailable() const {
    if (resident_ < 0) return false;
    const Actor& a = pool_[static_cast<std::size_t>(resident_)];
    return a.state != ActorState::Inside && !asleep(a);
}

void Actors::countPresence() {
    std::ranges::fill(presence_, 0);
    for (const Actor& a : pool_) {
        if ((a.flags & kAlive) == 0 || (a.flags & (kLeaving | kCrowd)) != 0) continue;
        const int v = cat_->kinds[a.kind].visitor;
        if (v >= 0) ++presence_[static_cast<std::size_t>(v)];
    }
}

float Actors::hour(const ActorEnv& env) const {
    return env.pinned ? std::fmod(hourPrivate_, 24.0f) : hourOfClock(env.clock);
}

int Actors::scheduleBlock(const ActorEnv& env) const {
    if (cat_->residentKind < 0) return -1;
    const auto& sched = cat_->kinds[static_cast<std::size_t>(cat_->residentKind)].schedule;
    const float h = hour(env);
    for (std::size_t b = 0; b < sched.size(); ++b)
        if (hourIn(h, sched[b].from, sched[b].to)) return static_cast<int>(b);
    return 0;
}

bool Actors::rainAt(const ActorEnv& env, Vec2 p) const {
    return env.weather != nullptr ? env.weather->raining(p) : env.facts.raining;
}

CondFacts Actors::factsFor(const ActorEnv& env, const Actor& a) const {
    CondFacts f = env.facts;
    f.raining = rainAt(env, a.pos);
    f.home = cat_->kinds[a.kind].visitor < 0 && home_.has_value();
    return f;
}

// --- Reservations ----------------------------------------------------------------------------

int Actors::taken(const Reservation& r, int self) const {
    int n = 0;
    for (const Reservation& o : reservations_)
        if (o.actor != self && o.x == r.x && o.y == r.y && o.type == r.type && o.slot == r.slot &&
            (r.spot == kAnyTile || o.spot == r.spot))
            ++n;
    return n;
}

bool Actors::tileTaken(TilePos t, int self) const {
    return std::ranges::any_of(reservations_, [&](const Reservation& r) {
        return r.actor != self && r.tx == t.x && r.ty == t.y;
    });
}

void Actors::reserve(int i, const Reservation& r, Vec2 at) {
    release(i);
    Actor& a = pool_[static_cast<std::size_t>(i)];
    Reservation k = r;
    k.actor = static_cast<std::uint16_t>(i);
    // Spots on the ground (beside an item, a tile slot, a bank) keep their tile to themselves;
    // spots on an item (seats) are kept apart by the slot.
    const TilePos t = tileOf(at);
    const Item* it = r.type == kTileRes ? nullptr : (map_ != nullptr ? map_->itemAt(t) : nullptr);
    if (it == nullptr) {
        k.tx = static_cast<std::int16_t>(t.x);
        k.ty = static_cast<std::int16_t>(t.y);
    }
    reservations_.push_back(k);
    a.resX = r.x;
    a.resY = r.y;
    a.resType = r.type;
    a.resSlot = r.slot;
    a.resSpot = r.spot;
    a.reserved = true;
}

void Actors::release(int i) {
    Actor& a = pool_[static_cast<std::size_t>(i)];
    if (!a.reserved) return;
    std::erase_if(reservations_, [&](const Reservation& r) { return r.actor == i; });
    a.reserved = false;
}

// --- Presence --------------------------------------------------------------------------------

bool Actors::anchor(const ActorEnv& env, int visitor, TilePos& out, std::uint64_t& rng) const {
    const World& world = *env.world;
    const auto& def = cat_->visitors[static_cast<std::size_t>(visitor)];
    // Reservoir sampling over everything in the area that attracts this visitor.
    int count = 0;
    const auto offer = [&](TilePos p) {
        if (splitmix(rng) % static_cast<std::uint64_t>(++count) == 0) out = p;
    };
    world.forEachItemIn(area_, [&](const Item& it) {
        if (area_.contains(it.pos) &&
            std::ranges::find(def.attractItems, it.type) != def.attractItems.end())
            offer(it.pos);
    });
    for (const int terrain : def.attractTerrain) {
        world.forEachChunkIn(area_, [&](int cx, int cy) {
            if (world.chunkTerrainCount(cx, cy, terrain) == 0) return;
            const TileRect r =
                TileRect{cx * kChunk, cy * kChunk, (cx + 1) * kChunk, (cy + 1) * kChunk}.clipped(
                    area_.clipped(world.bounds()));
            for (int y = r.y0; y < r.y1; ++y)
                for (int x = r.x0; x < r.x1; ++x)
                    if (world.terrainAt({x, y}) == terrain && !world.isWild({x, y})) offer({x, y});
        });
    }
    return count > 0;
}

std::optional<Vec2> Actors::doorOf(const ActorEnv& env, const Item& it) const {
    const ItemDef& def = cat_->items[it.type];
    const auto door = std::ranges::find(cat_->slotKinds, "door");
    const SlotDef* pick = nullptr;
    for (const SlotDef& s : def.slots)
        if (door != cat_->slotKinds.end() && s.kind == door - cat_->slotKinds.begin()) {
            pick = &s;
            break;
        }
    if (pick == nullptr && !def.slots.empty()) pick = &def.slots.front();
    if (pick != nullptr && !pick->spots.empty()) {
        const Vec2 p = pick->spots[it.variant].front();
        return Vec2{static_cast<float>(it.pos.x) + p.x, static_cast<float>(it.pos.y) + p.y};
    }
    const TileRect fp = it.rect();
    for (int y = fp.y0 - 1; y <= fp.y1; ++y)
        for (int x = fp.x0 - 1; x <= fp.x1; ++x)
            if (!fp.contains(TilePos{x, y}) &&
                passable(*env.world, *cat_, Locomotion::Walk, {x, y}))
                return centre({x, y});
    return std::nullopt;
}

int Actors::spawn(const ActorEnv& env, int kind, float alpha, bool fromHome) {
    const ActorKind& k = cat_->kinds[static_cast<std::size_t>(kind)];
    // A free record, or a new one while the pool has room.
    std::size_t slot = pool_.size();
    for (std::size_t s = 0; s < pool_.size(); ++s)
        if ((pool_[s].flags & kAlive) == 0) {
            slot = s;
            break;
        }
    if (slot == pool_.size() && pool_.size() >= tuning::kActorPool) return -1;
    Actor a;
    // Each actor's stream comes from the one seed and its spawn number.
    a.rng = seed_ ^ (0xA5F0000000000000ULL + (static_cast<std::uint64_t>(kind) << 32) + spawned_);
    (void)splitmix(a.rng);
    a.kind = static_cast<std::uint16_t>(kind);
    a.flags = kAlive;
    a.alpha = alpha;
    a.animTime = range(a, 0.0f, 10.0f);
    a.facing = static_cast<Facing>(range(a, 0, 3));
    bool placed = false;
    if (k.visitor < 0) {
        // The resident: at her door, or at her bedroll.
        a.pos = centre(bedroll_);
        if (home_)
            if (const Item* it = env.world->itemAt(*home_))
                if (const auto d = doorOf(env, *it)) a.pos = *d;
        placed = true;
    } else {
        const int v = k.visitor;
        std::uint64_t rng = a.rng;
        TilePos at;
        if (fromHome && k.home >= 0 && anchor(env, v, at, rng)) {
            // Out of its home's door (hens at dawn, bees from the hive).
            const Item* home = nullptr;
            float bd = 1e9f;
            env.world->forEachItemIn(area_, [&](const Item& it) {
                const float d = dist(centre(it.pos), centre(at));
                if (it.type == k.home && !env.world->isWild(it.pos) && d < bd) {
                    bd = d;
                    home = &it;
                }
            });
            if (home != nullptr)
                if (const auto d = doorOf(env, *home)) {
                    a.pos = *d;
                    placed = true;
                }
        }
        if (!placed && anchor(env, v, at, rng)) {
            const Habitat h = cat_->visitors[static_cast<std::size_t>(v)].habitat;
            for (int attempt = 0; attempt < tuning::kSpawnAttempts && !placed; ++attempt) {
                const int r = attempt < tuning::kSpawnAttempts / 2 ? 1 : tuning::kWanderRadius;
                const Vec2 p{static_cast<float>(at.x + range(a, -r, r)) + range(a, 0.25f, 0.75f),
                             static_cast<float>(at.y + range(a, -r, r)) + range(a, 0.25f, 0.75f)};
                if (!area_.contains(tileOf(p)) || !habitatAllows(h, *env.world, *cat_, p)) continue;
                a.pos = k.move == Locomotion::Swim ? offShore(*env.world, p) : p;
                placed = true;
            }
        }
        a.rng ^= rng;
        if (k.move == Locomotion::Fly)
            a.lift = range(a, tuning::kHoverMin, tuning::kHoverMax) * cat_->iso().tileH();
    }
    if (!placed) return -1;
    a.goal = a.pos;
    ++spawned_;
    claim(slot, a);
    return static_cast<int>(slot);
}

void Actors::claim(std::size_t slot, const Actor& a) {
    // Every array kept per actor grows or is reset with its record.
    if (slot == pool_.size()) {
        pool_.push_back(a);
        paths_.emplace_back();
        errands_.emplace_back();
        dests_.emplace_back();
        visited_.emplace_back();
        stuck_.push_back(0);
        lineBan_.push_back(0);
        inside_.emplace_back();
        leaveAge_.push_back(0);
        return;
    }
    pool_[slot] = a;
    errands_[slot] = {};
    dests_[slot] = {};
    visited_[slot] = {};
    stuck_[slot] = 0;
    lineBan_[slot] = 0;
    inside_[slot] = {};
    leaveAge_[slot] = 0;
}

void Actors::leave(const ActorEnv& env, int i) {
    Actor& a = pool_[static_cast<std::size_t>(i)];
    if ((a.flags & kLeaving) == 0) leaveAge_[static_cast<std::size_t>(i)] = 0;
    a.flags |= kLeaving;
    const ActorKind& k = cat_->kinds[a.kind];
    const int r = k.findRoutine("leave", cat_->program);
    Pick p;
    if (r >= 0 && homePick(env, i, -1, p)) {
        restart(i);
        push(a, cat_->program.routines[static_cast<std::size_t>(r)].block, 0);
        a.prio = 0xFF; // nothing interrupts going home
        return;
    }
    a.flags |= kFadeOut | kGone;
}

void Actors::presence(const ActorEnv& env, float dt) {
    const World& world = *env.world;
    const bool moved = env.area != area_;
    if (moved) {
        area_ = env.area;
        for (std::size_t i = 0; i < pool_.size(); ++i) {
            Actor& a = pool_[i];
            if ((a.flags & kAlive) != 0 && cat_->kinds[a.kind].visitor >= 0 &&
                !area_.contains(tileOf(a.pos))) {
                release(static_cast<int>(i));
                a.flags = 0;
            }
        }
    }
    if (moved || tallyRevision_ != world.revision()) {
        tallyArea(world, *cat_, area_, tally_);
        tallyRevision_ = world.revision();
    }
    countPresence();
    const bool night = env.phase == Phase::Night;
    for (std::size_t v = 0; v < cat_->visitors.size(); ++v) {
        const int vi = static_cast<int>(v);
        const int want = desiredCount(cat_->visitors[v], tally_, night, env.gates[v]);
        int have = presence_[v];
        if (moved && seen(vi))
            for (; have < want && spawn(env, vi, 0.0f, false) >= 0; ++have) {}
        cooldown_[v] = std::max(0.0f, cooldown_[v] - dt);
        if (have == 0 && want > 0)
            cooldown_[v] = std::min(cooldown_[v], tuning::kFirstArrivalDelay);
        if (have < want && cooldown_[v] <= 0.0f) {
            const int i = spawn(env, vi, 0.0f, true);
            if (i >= 0) {
                const bool first = !seen(vi);
                markSeen(vi);
                events_.push_back({ActorEvent::Kind::Arrived,
                                   i,
                                   vi,
                                   pool_[static_cast<std::size_t>(i)].pos,
                                   -1,
                                   {},
                                   first});
                ++have;
            }
            cooldown_[v] = tuning::kArrivalInterval;
        } else if (have > want && cooldown_[v] <= 0.0f) {
            for (std::size_t i = pool_.size(); i-- > 0;) {
                const Actor& a = pool_[i];
                if ((a.flags & kAlive) != 0 && (a.flags & (kLeaving | kCrowd)) == 0 &&
                    cat_->kinds[a.kind].visitor == vi) {
                    leave(env, static_cast<int>(i));
                    break;
                }
            }
            cooldown_[v] = tuning::kDepartureInterval;
        }
    }
    countPresence();
}

// --- The resident's world ---------------------------------------------------------------------

void Actors::updateHome(const ActorEnv& env) {
    if (cat_->residentKind < 0) return;
    const World& world = *env.world;
    const int homeType = cat_->kinds[static_cast<std::size_t>(cat_->residentKind)].home;
    // Her home is the first of its kind in the item list; she keeps it while it stands.
    const bool kept = home_ && world.itemAt(*home_) != nullptr &&
                      world.itemAt(*home_)->pos == *home_ && world.itemAt(*home_)->type == homeType;
    if (!kept) {
        const bool had = home_.has_value();
        home_.reset();
        if (homeType >= 0)
            for (const Item& it : world.items())
                if (it.type == homeType && !world.isWild(it.pos)) {
                    home_ = it.pos;
                    break;
                }
        if (had && !home_ && resident_ >= 0) {
            const int ctx = cat_->resident.context("home_lost");
            if (ctx >= 0) say(resident_, ctx);
        }
    }
    // Without a home she sleeps on her bedroll: by a campfire, else her spot, else near the
    // middle of the first land.
    const auto fire = cat_->findItem("campfire");
    std::optional<TilePos> spot;
    if (fire)
        for (const Item& it : world.items())
            if (it.type == *fire && !world.isWild(it.pos)) {
                for (const TilePos d :
                     {TilePos{1, 0}, TilePos{0, 1}, TilePos{-1, 0}, TilePos{0, -1}}) {
                    const TilePos t{it.pos.x + d.x, it.pos.y + d.y};
                    if (passable(world, *cat_, Locomotion::Walk, t)) {
                        spot = t;
                        break;
                    }
                }
                if (spot) break;
            }
    if (!spot && passable(world, *cat_, Locomotion::Walk, cat_->starter.resident))
        spot = cat_->starter.resident;
    if (!spot && !cat_->stages.empty()) {
        const TileRect r = cat_->stages.front().rects.front();
        const TilePos mid{(r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2};
        int best = 1 << 30;
        for (int y = r.y0; y < r.y1; ++y)
            for (int x = r.x0; x < r.x1; ++x)
                if (passable(world, *cat_, Locomotion::Walk, {x, y})) {
                    const int d = std::abs(x - mid.x) + std::abs(y - mid.y);
                    if (d < best) {
                        best = d;
                        spot = TilePos{x, y};
                    }
                }
    }
    bedroll_ = spot.value_or(cat_->starter.resident);
}

// --- Targets ----------------------------------------------------------------------------------

float Actors::prefer(const ActorEnv& env, int kind, int activity, TilePos t) const {
    if (activity < 0) return 1.0f;
    for (const PreferArea& p : env.prefer)
        if (p.kind == kind && p.activity == activity && inArea(p.area, t))
            return tuning::kNookPreferWeight;
    return 1.0f;
}

bool Actors::freeTile(const ActorEnv& env, const Actor& a, TilePos t) const {
    const ActorKind& k = cat_->kinds[a.kind];
    if (!env.world->hasGround(t) || env.world->isWild(t)) return false;
    if (k.move == Locomotion::Fly) return true;
    return passable(*env.world, *cat_, k.move, t);
}

bool Actors::slotPick(const ActorEnv& env, int i, const Item& it, const Target& t, Pick& out,
                      float& weight) {
    const Actor& a = pool_[static_cast<std::size_t>(i)];
    const ItemDef& def = cat_->items[it.type];
    // Which of the item's slots the target means.
    int chosen = -1;
    std::uint8_t implicit = 0;
    for (std::size_t s = 0; s < def.slots.size() && chosen < 0; ++s) {
        const SlotDef& sd = def.slots[s];
        const bool match = t.slot >= 0          ? sd.name == t.slot
                           : t.slotKind >= 0    ? sd.kind == t.slotKind
                           : t.spot == Spot::On ? sd.where != SlotWhere::Beside
                                                // beside: the tiles around it, not a named use
                                                : t.spot != Spot::Beside;
        if (match) chosen = static_cast<int>(s);
    }
    if (chosen < 0) {
        if (t.slot >= 0 || t.slotKind >= 0) return false;
        // Implicit slots: on (where it has a perch) and beside.
        implicit = (t.spot != Spot::Beside && !def.perch.empty()) ? kImplicitOn : kImplicitBeside;
        if (t.spot == Spot::On && implicit != kImplicitOn) return false;
    }
    const SlotDef* sd = chosen >= 0 ? &def.slots[static_cast<std::size_t>(chosen)] : nullptr;
    const bool beside =
        sd != nullptr ? sd->where == SlotWhere::Beside : implicit == kImplicitBeside;
    Reservation r{static_cast<std::int16_t>(it.pos.x),
                  static_cast<std::int16_t>(it.pos.y),
                  it.type,
                  sd != nullptr ? static_cast<std::uint8_t>(chosen) : implicit,
                  0,
                  0};
    const int cap = sd != nullptr ? sd->cap : (beside ? 64 : 1);
    {
        Reservation all = r;
        all.spot = kAnyTile;
        if (taken(all, i) >= cap) return false;
    }
    const Vec2 ctr{static_cast<float>(it.pos.x) + static_cast<float>(it.w) * 0.5f,
                   static_cast<float>(it.pos.y) + static_cast<float>(it.h) * 0.5f};
    float best = 1e9f;
    if (beside) {
        // The nearest free tile around the footprint that this actor may stand on.
        const TileRect fp = it.rect();
        for (int y = fp.y0 - 1; y <= fp.y1; ++y)
            for (int x = fp.x0 - 1; x <= fp.x1; ++x) {
                if (fp.contains(TilePos{x, y})) continue;
                const bool corner = (x < fp.x0 || x >= fp.x1) && (y < fp.y0 || y >= fp.y1);
                if (corner || !freeTile(env, a, {x, y})) continue;
                Reservation q = r;
                q.spot = static_cast<std::uint8_t>((y - fp.y0 + 1) * 16 + (x - fp.x0 + 1));
                if (taken(q, i) > 0 || tileTaken({x, y}, i)) continue;
                const float d = dist(a.pos, centre({x, y}));
                if (d < best) {
                    best = d;
                    out.point = centre({x, y});
                    out.res = q;
                }
            }
        if (best >= 1e9f) return false;
        out.lift = 0;
        out.look = ctr;
        if (sd != nullptr && sd->facing == SlotFacing::Out)
            out.look = {2 * out.point.x - ctr.x, 2 * out.point.y - ctr.y};
        else if (sd != nullptr && sd->facing == SlotFacing::Free)
            out.look = {-1, -1};
    } else {
        const std::vector<Vec2>* spots = sd != nullptr ? &sd->spots[it.variant] : nullptr;
        const Vec2 mid{static_cast<float>(it.w) * 0.5f, static_cast<float>(it.h) * 0.5f};
        const int n = spots != nullptr ? static_cast<int>(spots->size()) : 1;
        const bool perSpot = n > 1;
        for (int s = 0; s < n; ++s) {
            const Vec2 local = spots != nullptr ? (*spots)[static_cast<std::size_t>(s)] : mid;
            const Vec2 p{static_cast<float>(it.pos.x) + local.x,
                         static_cast<float>(it.pos.y) + local.y};
            Reservation q = r;
            q.spot = static_cast<std::uint8_t>(s);
            if (perSpot && taken(q, i) > 0) continue;
            // A tile spot must be somewhere this actor may stand.
            if ((sd == nullptr || sd->where == SlotWhere::Tile) && !it.rect().contains(tileOf(p)) &&
                !freeTile(env, a, tileOf(p)))
                continue;
            const float d = dist(a.pos, p);
            if (d < best) {
                best = d;
                out.point = p;
                out.res = q;
            }
        }
        if (best >= 1e9f) return false;
        if (!perSpot) out.res.spot = 0;
        out.lift = sd != nullptr ? (sd->lift.empty() ? 0.0f : sd->lift[it.variant])
                                 : static_cast<float>(def.perch[it.variant]);
        out.look = {-1, -1};
        if (sd != nullptr && !sd->face.empty()) {
            out.face = sd->face[it.variant];
        } else if (sd != nullptr && sd->facing == SlotFacing::Item) {
            out.look = ctr;
        }
    }
    out.reserve = true;
    weight = 1.0f;
    return true;
}

const Item* Actors::homeItem(const ActorEnv& env, const Actor& a) const {
    const ActorKind& k = cat_->kinds[a.kind];
    if (k.visitor < 0) return home_ ? env.world->itemAt(*home_) : nullptr;
    if (k.home < 0) return nullptr;
    const Item* best = nullptr;
    float bd = 1e9f;
    env.world->forEachItemIn(area_, [&](const Item& it) {
        if (it.type != k.home || env.world->isWild(it.pos)) return;
        const float d = dist(a.pos, centre(it.pos));
        if (d < bd) {
            bd = d;
            best = &it;
        }
    });
    return best;
}

bool Actors::homePick(const ActorEnv& env, int i, int slot, Pick& out) {
    const Actor& a = pool_[static_cast<std::size_t>(i)];
    const Item* it = homeItem(env, a);
    if (it == nullptr) return false;
    const ItemDef& def = cat_->items[it->type];
    Target t;
    t.kind = Target::Kind::Items;
    t.slot = slot;
    if (slot < 0) {
        // Its door if it has one, else its first slot, else beside it.
        const auto door = std::ranges::find(cat_->slotKinds, "door");
        const int doorKind =
            door == cat_->slotKinds.end() ? -1 : static_cast<int>(door - cat_->slotKinds.begin());
        for (const SlotDef& s : def.slots)
            if (s.kind == doorKind) {
                t.slot = s.name;
                break;
            }
        if (t.slot < 0 && !def.slots.empty()) t.slot = def.slots.front().name;
        if (t.slot < 0) t.spot = Spot::Beside;
    }
    float w = 0;
    return slotPick(env, i, *it, t, out, w);
}

bool Actors::bankPick(const ActorEnv& env, int i, bool shore, Pick& out) {
    Actor& a = pool_[static_cast<std::size_t>(i)];
    const World& world = *env.world;
    const TilePos c = tileOf(a.pos);
    const int r = tuning::kBankSearch;
    float total = 0;
    bool found = false;
    for (int y = c.y - r; y <= c.y + r; ++y)
        for (int x = c.x - r; x <= c.x + r; ++x) {
            const TilePos t{x, y};
            if (!area_.contains(t) || !world.hasGround(t) || world.isWild(t)) continue;
            const bool ok = shore ? habitatAllows(Habitat::Shore, world, *cat_, centre(t))
                                  : !world.isWater(t) &&
                                        passable(world, *cat_, Locomotion::Swim, t, true) &&
                                        passable(world, *cat_, Locomotion::Walk, t);
            if (!ok) continue;
            const Reservation q{
                static_cast<std::int16_t>(x), static_cast<std::int16_t>(y), kTileRes, 0, 0, 0};
            if (tileTaken(t, i)) continue;
            const float w =
                prefer(env, a.kind, -1, t) * (1.0f / (1.0f + dist(a.pos, centre(t)) * 0.2f));
            total += w;
            if (uniform(a) * total < w) {
                out.point = centre(t);
                out.res = q;
                found = true;
            }
        }
    out.reserve = found;
    out.lift = 0;
    return found;
}

bool Actors::wanderPick(const ActorEnv& env, int i, float radius, Pick& out, int activity) {
    Actor& a = pool_[static_cast<std::size_t>(i)];
    const World& world = *env.world;
    const ActorKind& k = cat_->kinds[a.kind];
    TilePos from = tileOf(a.pos);
    if (k.visitor >= 0) {
        // Mostly drift around the current spot, sometimes head back to what attracted it, and
        // half the time inside a nook that prefers its wandering.
        const PreferArea* pa = nullptr;
        for (const PreferArea& p : env.prefer)
            if (activity >= 0 && p.kind == a.kind && p.activity == activity) pa = &p;
        if (pa != nullptr && uniform(a) < 0.5f) {
            const TileRect& f = pa->area.footprint;
            from = {range(a, f.x0 - pa->area.within, f.x1 + pa->area.within - 1),
                    range(a, f.y0 - pa->area.within, f.y1 + pa->area.within - 1)};
        } else if (uniform(a) < tuning::kReturnToAnchorChance) {
            std::uint64_t rng = a.rng;
            (void)anchor(env, k.visitor, from, rng);
            a.rng = rng;
        }
    }
    const int r = static_cast<int>(radius);
    const Habitat h = k.visitor >= 0 ? cat_->visitors[static_cast<std::size_t>(k.visitor)].habitat
                                     : Habitat::Land;
    for (int attempt = 0; attempt < tuning::kTargetAttempts; ++attempt) {
        const Vec2 p{static_cast<float>(from.x + range(a, -r, r)) + range(a, 0.2f, 0.8f),
                     static_cast<float>(from.y + range(a, -r, r)) + range(a, 0.2f, 0.8f)};
        const TilePos t = tileOf(p);
        if (!area_.contains(t)) continue;
        const bool ok = k.visitor >= 0 ? habitatAllows(h, world, *cat_, p)
                                       : passable(world, *cat_, Locomotion::Walk, t);
        if (!ok) continue;
        out.point = k.move == Locomotion::Swim ? offShore(world, p) : p;
        out.lift = k.move == Locomotion::Fly
                       ? range(a, tuning::kHoverMin, tuning::kHoverMax) * cat_->iso().tileH()
                       : 0.0f;
        out.reserve = false;
        return true;
    }
    return false;
}

bool Actors::poiPick(const ActorEnv& env, int i, Poi poi, int activity, Pick& out, int nook) {
    Actor& a = pool_[static_cast<std::size_t>(i)];
    // Points of interest: nooks, things placed in the last ten minutes, visitors.
    float total = 0;
    Vec2 chosen{-1, -1};
    const auto offer = [&](Vec2 p, float w) {
        if (!area_.contains(tileOf(p))) return;
        w *= prefer(env, a.kind, activity, tileOf(p));
        total += w;
        if (uniform(a) * total < w) chosen = p;
    };
    if (poi == Poi::Stroll || poi == Poi::Nooks)
        for (const NookPlace& n : env.nooks) {
            if (nook >= 0 && n.nook != nook) continue;
            const TileRect& f = n.area.footprint;
            offer({static_cast<float>(f.x0 + f.x1) * 0.5f, static_cast<float>(f.y0 + f.y1) * 0.5f},
                  1.0f);
        }
    if (poi == Poi::Stroll || poi == Poi::NewItems)
        for (const Recent& r : recent_) offer(centre(r.at), tuning::kNewItemWeight);
    if (poi == Poi::Stroll || poi == Poi::Visitors)
        for (std::size_t j = 0; j < pool_.size(); ++j) {
            const Actor& o = pool_[j];
            if (static_cast<int>(j) == i || (o.flags & kAlive) == 0 || hidden(o) ||
                cat_->kinds[o.kind].visitor < 0)
                continue;
            offer(o.pos, 1.0f);
        }
    if (poi == Poi::Stroll && total <= 0) {
        // Nothing of note yet: a stroll to a random open spot.
        return wanderPick(env, i, tuning::kStrollRadius, out);
    }
    if (total <= 0) return false;
    // Stand on a free tile one or two steps from it, looking at it.
    const TilePos c = tileOf(chosen);
    float best = 1e9f;
    for (int y = c.y - 2; y <= c.y + 2; ++y)
        for (int x = c.x - 2; x <= c.x + 2; ++x) {
            const TilePos t{x, y};
            if (t == c || !freeTile(env, a, t)) continue;
            const Reservation q{
                static_cast<std::int16_t>(x), static_cast<std::int16_t>(y), kTileRes, 0, 0, 0};
            if (tileTaken(t, i)) continue;
            const float d = std::abs(dist(centre(t), chosen) - 1.5f) + range(a, 0.0f, 0.5f);
            if (d < best) {
                best = d;
                out.point = centre(t);
                out.res = q;
            }
        }
    if (best >= 1e9f) return false;
    out.reserve = true;
    out.lift = 0;
    out.look = chosen;
    return true;
}

bool Actors::resolve(const ActorEnv& env, int i, const Target& t, int activity, Pick& out) {
    Actor& a = pool_[static_cast<std::size_t>(i)];
    out = Pick{};
    switch (t.kind) {
    case Target::Kind::Here:
        out.point = a.pos;
        out.lift = a.lift;
        return true;
    case Target::Kind::Each: {
        if (!a.reserved) return false;
        // The reservation made when the iteration began.
        if (a.resType == kTileRes) {
            out.point = centre({a.resX, a.resY});
            out.look = dests_[static_cast<std::size_t>(i)].look;
            return true;
        }
        const Item* it = env.world->itemAt({a.resX, a.resY});
        if (it == nullptr) return false;
        out = dests_[static_cast<std::size_t>(i)];
        out.reserve = false;
        return true;
    }
    case Target::Kind::Home: return homePick(env, i, t.slot, out);
    case Target::Kind::Bank: return bankPick(env, i, false, out);
    case Target::Kind::Shore: return bankPick(env, i, true, out);
    case Target::Kind::Resident: {
        if (resident_ < 0 || !residentAvailable()) return false;
        out.point = pool_[static_cast<std::size_t>(resident_)].pos;
        return true;
    }
    case Target::Kind::Bedroll: out.point = centre(bedroll_); return true;
    case Target::Kind::Poi: return poiPick(env, i, t.poi, activity, out);
    case Target::Kind::Nook: return poiPick(env, i, Poi::Nooks, activity, out, t.id);
    case Target::Kind::Items:
    case Target::Kind::Tag:
    case Target::Kind::SlotKind: break;
    }
    // Items: everything matching within reach, weighed (nooks that prefer this activity weigh
    // more), one chosen at random.
    Vec2 from = a.pos;
    if (t.nearHome) {
        const Item* h = homeItem(env, a);
        if (h == nullptr) return false;
        from = centre(h->pos);
    }
    TileRect search = area_;
    if (t.within > 0) {
        const int r = static_cast<int>(std::ceil(t.within));
        search = TileRect{static_cast<int>(from.x) - r, static_cast<int>(from.y) - r,
                          static_cast<int>(from.x) + r + 1, static_cast<int>(from.y) + r + 1}
                     .clipped(area_);
    }
    float total = 0;
    bool found = false;
    env.world->forEachItemIn(search, [&](const Item& it) {
        if (env.world->isWild(it.pos) || !area_.contains(it.pos)) return;
        const ItemDef& def = cat_->items[it.type];
        bool match = false;
        switch (t.kind) {
        case Target::Kind::Items: match = std::ranges::find(t.ids, it.type) != t.ids.end(); break;
        case Target::Kind::Tag: match = std::ranges::find(def.tags, t.id) != def.tags.end(); break;
        case Target::Kind::SlotKind:
            match = std::ranges::any_of(def.slots,
                                        [&](const SlotDef& s) { return s.kind == t.slotKind; }) &&
                    (t.id < 0 || std::ranges::find(def.tags, t.id) != def.tags.end());
            break;
        default: break;
        }
        if (!match) return;
        if (t.within > 0 && distToRect(from, it.rect()) > t.within) return;
        Pick p;
        float w = 0;
        if (!slotPick(env, i, it, t, p, w)) return;
        w *= prefer(env, a.kind, activity, it.pos);
        total += w;
        if (uniform(a) * total < w) {
            out = p;
            found = true;
        }
    });
    return found;
}

// --- Routines ---------------------------------------------------------------------------------

void Actors::push(Actor& a, int block, std::uint8_t n) {
    // The catalog loader refuses routines nested deeper than the stack (compileActors), so this
    // always has room.
    assert(a.depth < kActorStack);
    if (a.depth >= kActorStack) return;
    a.stack[a.depth++] = {static_cast<std::uint16_t>(block), 0, n};
}

void Actors::advance(Actor& a) {
    if (a.depth > 0) ++a.stack[a.depth - 1].pc;
    a.state = ActorState::Choose;
}

void Actors::restart(int i) {
    Actor& a = pool_[static_cast<std::size_t>(i)];
    release(i);
    a.depth = 0;
    a.state = ActorState::Choose;
    a.anim = 1;
    a.prio = (a.flags & kLeaving) != 0 ? a.prio : 0;
    a.pathLen = 0;
    a.flags &= static_cast<std::uint16_t>(~(kErrand | kOnHat | kFadeOut));
    if (cat_->kinds[a.kind].move != Locomotion::Fly) a.lift = 0;
}

void Actors::chooseRoutine(const ActorEnv& env, int i) {
    Actor& a = pool_[static_cast<std::size_t>(i)];
    const ActorKind& k = cat_->kinds[a.kind];
    const ActorProgram& p = cat_->program;
    if (k.visitor >= 0) {
        push(a, p.routines[static_cast<std::size_t>(k.main)].block, kLoopFrame);
        return;
    }
    const int blk = scheduleBlock(env);
    if (blk != a.sched) {
        a.sched = static_cast<std::uint8_t>(blk);
        saidMask_ = 0;
        blockDone_ = false;
    }
    if (blockDone_) {
        // Her block's routine is done: she potters about until the next one.
        Pick pk;
        if (uniform(a) < 0.5f && wanderPick(env, i, tuning::kPotterRadius, pk) &&
            goTo(env, i, pk)) {
            dests_[static_cast<std::size_t>(i)].lift = 0;
            return;
        }
        a.state = ActorState::Act;
        a.anim = 1;
        a.timer = range(a, tuning::kIdleMin * 2, tuning::kIdleMax * 2);
        return;
    }
    const Routine& r =
        p.routines[static_cast<std::size_t>(k.schedule[static_cast<std::size_t>(blk)].routine)];
    push(a, r.block, r.loop ? kLoopFrame : 0);
}

void Actors::run(const ActorEnv& env, int i) {
    Actor& a = pool_[static_cast<std::size_t>(i)];
    const ActorProgram& p = cat_->program;
    const ActorKind& k = cat_->kinds[a.kind];
    for (int guard = 0; guard < 24 && a.state == ActorState::Choose; ++guard) {
        // The resident follows her schedule between activities.
        if (k.visitor < 0 && a.prio == 0 && a.depth > 0 && scheduleBlock(env) != a.sched)
            restart(i);
        if (a.depth == 0 && (a.flags & kLeaving) != 0) {
            // A leaver whose walk home ended without going in (its door gone, startled, fenced
            // off: Q3-02) tries the way home once more, then fades where it is. It never takes
            // up its day again, so it is never left out of the count while it lingers.
            if ((a.flags & kHomeRetry) == 0) {
                a.flags |= kHomeRetry;
                leave(env, i);
                if (a.depth > 0) continue;
            }
            a.flags |= kFadeOut | kGone;
            a.state = ActorState::Act;
            return;
        }
        if (a.depth == 0) {
            chooseRoutine(env, i);
            if (a.depth == 0) return;
        }
        ActorFrame& f = a.stack[a.depth - 1];
        const Block& b = p.blocks[f.block];
        if (f.pc >= b.count) {
            if ((f.n & kLoopFrame) != 0) {
                f.pc = 0;
                if (k.visitor < 0) saidMask_ = 0;
                continue;
            }
            // An each frame moves on to its next element.
            if (a.depth >= 2) {
                const ActorFrame& parent = a.stack[a.depth - 2];
                const Step& ps =
                    p.steps[static_cast<std::size_t>(p.blockSteps[static_cast<std::size_t>(
                        p.blocks[parent.block].first + parent.pc)])];
                if (ps.verb == Verb::Each && f.n + 1 < ps.b) {
                    // The finished element's frame goes first, so the next one takes its place
                    // (no extra depth), and its count is read before that frame is reused (Q3-05).
                    const auto done = static_cast<std::uint8_t>(f.n + 1);
                    --a.depth;
                    eachNext_ = true;
                    if (start(env, i, ps) == Start::Running && a.depth > 0) {
                        a.stack[a.depth - 1].n = done;
                        a.state = ActorState::Choose;
                        continue;
                    }
                    ++a.stack[a.depth - 1].pc; // no more elements: the each is done
                    continue;
                }
            }
            --a.depth;
            if (a.depth == 0) {
                // A routine ended: an interrupt gives way to the schedule; the resident's block
                // routine runs once, then she potters until the block changes.
                if (a.prio != 0 && (a.flags & kLeaving) == 0) {
                    a.prio = 0;
                } else if (k.visitor < 0) {
                    blockDone_ = true;
                }
                continue;
            }
            ++a.stack[a.depth - 1].pc;
            continue;
        }
        const Step& s = p.steps[static_cast<std::size_t>(
            p.blockSteps[static_cast<std::size_t>(b.first + f.pc)])];
        const int depthBefore = a.depth;
        switch (start(env, i, s)) {
        case Start::Done: ++a.stack[a.depth - 1].pc; break;
        case Start::Running:
            if (a.depth > depthBefore) {
                a.state = ActorState::Choose; // a block was pushed: run it
                break;
            }
            return;
        case Start::Failed:
            // A failed step abandons the block it is in (an option whose target is gone),
            // after a short pause so nobody spins on it.
            if (a.depth > 1) {
                --a.depth;
                ++a.stack[a.depth - 1].pc;
            } else {
                ++a.stack[0].pc;
            }
            release(i);
            a.state = ActorState::Act;
            a.anim = 1;
            a.timer = range(a, 0.3f, 1.0f);
            a.flags |= kPause;
            return;
        }
    }
}

bool Actors::goTo(const ActorEnv& env, int i, const Pick& p, bool bank) {
    Actor& a = pool_[static_cast<std::size_t>(i)];
    if (p.reserve) reserve(i, p.res, p.point);
    dests_[static_cast<std::size_t>(i)] = p;
    a.goal = p.point;
    a.state = ActorState::Travel;
    if (cat_->kinds[a.kind].move == Locomotion::Fly || dist(a.pos, a.goal) < 0.05f) {
        a.pathLen = 0;
        return true;
    }
    if (!plan(env, i, bank)) {
        release(i);
        a.state = ActorState::Choose;
        return false;
    }
    return true;
}

bool Actors::plan(const ActorEnv& env, int i, bool bank) {
    Actor& a = pool_[static_cast<std::size_t>(i)];
    const ActorKind& k = cat_->kinds[a.kind];
    const TilePos from = tileOf(a.pos);
    const TilePos to = tileOf(a.goal);
    a.pathPos = 0;
    if (from == to) {
        a.pathLen = 0;
        return true;
    }
    // Swimmers and shore walkers try the straight line first; it is almost always clear.
    if (k.move != Locomotion::Walk) {
        const float len = dist(a.pos, a.goal);
        const int steps = std::max(1, static_cast<int>(len / 0.2f));
        bool clear = true;
        for (int s = 1; s <= steps && clear; ++s) {
            const float f = static_cast<float>(s) / static_cast<float>(steps);
            const TilePos t =
                tileOf({a.pos.x + (a.goal.x - a.pos.x) * f, a.pos.y + (a.goal.y - a.pos.y) * f});
            clear = t == to || t == from || passable(*env.world, *cat_, k.move, t, bank);
        }
        if (clear) {
            a.pathLen = 0;
            return true;
        }
    }
    if (searches_ >= tuning::kPathSearchesPerStep) {
        a.pathLen = kPathPending;
        return true;
    }
    // The same trip in the same world is found once (hens to their coop, her to her bench).
    auto& out = paths_[static_cast<std::size_t>(i)];
    const std::uint64_t rev = env.world->revision();
    for (const CachedPath& c : pathCache_)
        if (c.rev == rev && c.from == from && c.to == to && c.move == k.move && c.bank == bank) {
            std::ranges::copy(c.tiles, out.begin());
            a.pathLen = c.len;
            return c.len > 0;
        }
    ++searches_;
    PathQuery q;
    q.move = k.move;
    q.from = from;
    q.to = to;
    q.bounds = area_;
    q.bank = bank;
    const int n = finder_.find(*env.world, q, out);
    CachedPath& slot = pathCache_[pathNext_++ % pathCache_.size()];
    slot = {rev, from, to, k.move, bank, static_cast<std::uint8_t>(std::max(0, n)), out};
    if (n <= 0) return false;
    a.pathLen = static_cast<std::uint8_t>(n);
    return true;
}

bool Actors::untilMet(const ActorEnv& env, const Actor& a, const Step& s) const {
    switch (s.until) {
    case Until::None: return false;
    case Until::Hour: {
        // Until H: done once the hour has left the span from her block's start to H (so a
        // clock that jumps ahead lets her out, and a pinned night keeps her in).
        const ActorKind& k = cat_->kinds[a.kind];
        if (a.sched < k.schedule.size())
            return !hourIn(hour(env), k.schedule[a.sched].from, s.hour);
        return hourIn(hour(env), s.hour, std::fmod(s.hour + 1.0f, 24.0f));
    }
    case Until::Phase: return ((s.phases >> static_cast<int>(env.phase)) & 1) != 0;
    case Until::Clear: return !rainAt(env, a.pos);
    case Until::Rain: return rainAt(env, a.pos);
    }
    return false;
}

Actors::Start Actors::start(const ActorEnv& env, int i, const Step& s) {
    Actor& a = pool_[static_cast<std::size_t>(i)];
    const ActorProgram& p = cat_->program;
    const auto targetOf = [&](int t) -> const Target& {
        return p.targets[static_cast<std::size_t>(t)];
    };
    switch (s.verb) {
    case Verb::Go: {
        Pick pk;
        const bool got = resolve(env, i, targetOf(s.target), s.activity, pk) ||
                         (s.orElse >= 0 && resolve(env, i, targetOf(s.orElse), s.activity, pk));
        if (!got) return Start::Failed;
        if (targetOf(s.target).kind == Target::Kind::Here) return Start::Done;
        const bool bank = targetOf(s.target).kind == Target::Kind::Bank;
        return goTo(env, i, pk, bank) ? Start::Running : Start::Failed;
    }
    case Verb::Use:
    case Verb::Enter: {
        const Target& t = targetOf(s.target);
        Pick pk;
        if (t.kind != Target::Kind::Here && t.kind != Target::Kind::Each) {
            // Already at that slot (a `go` to the same target came first)?
            bool there = false;
            if (a.reserved && a.resType != kTileRes) {
                const Item* it = env.world->itemAt({a.resX, a.resY});
                const SlotDef* sd = it != nullptr && a.resSlot < cat_->items[it->type].slots.size()
                                        ? &cat_->items[it->type].slots[a.resSlot]
                                        : nullptr;
                there = it != nullptr && dist(a.pos, a.goal) < 0.1f &&
                        (t.kind != Target::Kind::Items ||
                         std::ranges::find(t.ids, it->type) != t.ids.end()) &&
                        (t.slot < 0 || (sd != nullptr && sd->name == t.slot));
            }
            if (!there) {
                if (!resolve(env, i, t, s.activity, pk) ||
                    !goTo(env, i, pk, t.kind == Target::Kind::Bank))
                    return Start::Failed;
                return Start::Running; // the act begins on arrival
            }
        } else if (t.kind == Target::Kind::Each) {
            if (!resolve(env, i, t, s.activity, pk)) return Start::Failed;
            if (dist(a.pos, pk.point) > 0.1f)
                return goTo(env, i, pk) ? Start::Running : Start::Failed;
        }
        arrive(env, i, s);
        return a.state == ActorState::Choose ? Start::Done : Start::Running;
    }
    case Verb::Exit:
        if (a.state == ActorState::Inside || a.alpha < 1.0f) {
            a.flags &= static_cast<std::uint16_t>(~kFadeOut);
            Pick pk;
            if (homePick(env, i, -1, pk)) {
                a.pos = a.goal = pk.point;
                reserve(i, pk.res, pk.point);
                release(i);
            }
        }
        a.state = ActorState::Choose;
        return Start::Done;
    case Verb::Take:
        a.goods = static_cast<std::uint8_t>(s.a);
        a.goodsCount =
            static_cast<std::uint8_t>(std::min<int>(a.goodsCount + 1, tuning::kHandsMax));
        events_.push_back({ActorEvent::Kind::Goods, i, a.kind, a.pos, s.a, {}, false});
        return Start::Done;
    case Verb::Put:
        if (a.goods == s.a && a.goodsCount > 0) {
            if (--a.goodsCount == 0) a.goods = 0xFF;
            events_.push_back({ActorEvent::Kind::Goods, i, a.kind, a.pos, s.a, {}, false});
        }
        return Start::Done;
    case Verb::Wander: {
        Pick pk;
        if (!wanderPick(env, i, s.radius, pk, s.activity)) return Start::Failed;
        a.call = s.dur1 > 0 ? range(a, s.dur0, s.dur1) : 0.0f;
        return goTo(env, i, pk) ? Start::Running : Start::Failed;
    }
    case Verb::Wait:
        a.state = ActorState::Act;
        a.anim = 1;
        a.timer = s.dur1 > 0 ? range(a, s.dur0, s.dur1) : 0.0f;
        return Start::Running;
    case Verb::Follow:
        if (resident_ < 0 || !residentAvailable() || resident_ == i) return Start::Failed;
        if (s.onHat && pool_[static_cast<std::size_t>(resident_)].prio != 0) return Start::Failed;
        a.state = ActorState::Follow;
        a.timer = s.dur1 > 0 ? range(a, s.dur0, s.dur1) : tuning::kIdleMax;
        release(i);
        return Start::Running;
    case Verb::Say:
        if (a.prio == 0 && ((saidMask_ >> (s.a & 63)) & 1) != 0) return Start::Done;
        if (a.prio == 0) saidMask_ |= 1ULL << (s.a & 63);
        say(i, s.a);
        return Start::Done;
    case Verb::Emit:
        events_.push_back({ActorEvent::Kind::Emit, i, a.kind, a.pos, s.a, {}, false});
        return Start::Done;
    case Verb::Pick: {
        // Weighted choice among the options whose filters pass and whose target exists.
        const CondFacts facts = factsFor(env, a);
        float total = 0;
        int chosen = -1;
        for (int o = 0; o < s.b; ++o) {
            const PickOption& opt = p.options[static_cast<std::size_t>(s.a + o)];
            if (opt.weight <= 0 || ((opt.phases >> static_cast<int>(env.phase)) & 1) == 0 ||
                ((opt.seasons >> env.season) & 1) == 0)
                continue;
            if (opt.cond >= 0 && !cat_->conditions.eval(opt.cond, *env.world, facts)) continue;
            if (opt.needsSitting > 0 &&
                (resident_ < 0 || sat_ < opt.needsSitting ||
                 dist(pool_[static_cast<std::size_t>(resident_)].pos, a.pos) > tuning::kHatReach))
                continue;
            // The option's first step must have something to go to.
            const Block& b = p.blocks[static_cast<std::size_t>(opt.block)];
            const Step& first =
                p.steps[static_cast<std::size_t>(p.blockSteps[static_cast<std::size_t>(b.first)])];
            if (first.target >= 0 && (first.verb == Verb::Go || first.verb == Verb::Use)) {
                const Target& t = targetOf(first.target);
                if (t.kind != Target::Kind::Here && t.kind != Target::Kind::Each) {
                    Pick probe;
                    if (!resolve(env, i, t, first.activity, probe)) continue;
                }
            }
            if (first.verb == Verb::Follow && (resident_ < 0 || !residentAvailable())) continue;
            // Acting right here: a nook that prefers this activity makes it likelier there.
            float w = opt.weight;
            if (first.target >= 0 && targetOf(first.target).kind == Target::Kind::Here)
                w *= prefer(env, a.kind, opt.activity, tileOf(a.pos));
            total += w;
            if (uniform(a) * total < w) chosen = o;
        }
        if (chosen < 0) return Start::Failed;
        push(a, p.options[static_cast<std::size_t>(s.a + chosen)].block, 0);
        return Start::Running;
    }
    case Verb::Routine: {
        const Routine& r = p.routines[static_cast<std::size_t>(s.a)];
        push(a, r.block, r.loop ? kLoopFrame : 0);
        return Start::Running;
    }
    case Verb::If: {
        const bool ok = cat_->conditions.eval(s.cond, *env.world, factsFor(env, a));
        if (ok) {
            push(a, s.a, 0);
            return Start::Running;
        }
        if (s.b >= 0) {
            push(a, s.b, 0);
            return Start::Running;
        }
        return Start::Done;
    }
    case Verb::Each: {
        // The next element: the nearest (or a random one) not yet visited this time.
        const Target& t = targetOf(s.target);
        // A water_bed each only visits beds that want water today.
        bool watering = false;
        const Block& body = p.blocks[static_cast<std::size_t>(s.a)];
        for (int b = 0; b < body.count; ++b)
            watering =
                watering || p.steps[static_cast<std::size_t>(
                                        p.blockSteps[static_cast<std::size_t>(body.first + b)])]
                                    .effect == Effect::WaterBed;
        Pick pk;
        bool got = false;
        // Every element visited by this each is left out, not only the last (Q3-05).
        Visited& seenHere = visited_[static_cast<std::size_t>(i)];
        if (!std::exchange(eachNext_, false)) seenHere.count = 0;
        const auto visitedBefore = [&](TilePos q) {
            return std::find(seenHere.at.begin(), seenHere.at.begin() + seenHere.count, q) !=
                   seenHere.at.begin() + seenHere.count;
        };
        TilePos chosen{-1, -1};
        if (t.kind == Target::Kind::Poi) {
            got = poiPick(env, i, t.poi, s.activity, pk);
        } else {
            release(i);
            float best = 1e9f;
            const float seasonGrowth = cat_->seasons[static_cast<std::size_t>(env.season)].growth;
            env.world->forEachItemIn(area_, [&](const Item& it) {
                if (env.world->isWild(it.pos)) return;
                const ItemDef& def = cat_->items[it.type];
                const bool match = t.kind == Target::Kind::Items
                                       ? std::ranges::find(t.ids, it.type) != t.ids.end()
                                   : t.kind == Target::Kind::Tag
                                       ? std::ranges::find(def.tags, t.id) != def.tags.end()
                                       : false;
                if (!match || visitedBefore(it.pos)) return;
                if (watering) {
                    if (def.growth.stages == 0 || it.stage + 1 >= def.growth.stages ||
                        rainAt(env, centre(it.pos)) ||
                        growthRate(*env.world, *cat_, it.rect(), false, seasonGrowth, 1.0f) <= 0)
                        return;
                    if (std::ranges::any_of(watered_, [&](const auto& w) {
                            return w.first == it.pos && w.second == env.day;
                        }))
                        return;
                }
                Pick c;
                float w = 0;
                if (!slotPick(env, i, it, t, c, w)) return;
                const float d = s.nearest ? dist(a.pos, c.point) : range(a, 0.0f, 100.0f);
                if (d < best) {
                    best = d;
                    pk = c;
                    chosen = it.pos;
                    got = true;
                }
            });
        }
        if (!got) return Start::Done;
        if (chosen.x >= 0 && seenHere.count < seenHere.at.size())
            seenHere.at[seenHere.count++] = chosen;
        if (pk.reserve) reserve(i, pk.res, pk.point);
        dests_[static_cast<std::size_t>(i)] = pk;
        push(a, s.a, 0);
        return Start::Running;
    }
    }
    return Start::Done;
}

// The act part of a use or enter step, once there.
void Actors::arrive(const ActorEnv& env, int i, const Step& s) {
    Actor& a = pool_[static_cast<std::size_t>(i)];
    const Pick& d = dests_[static_cast<std::size_t>(i)];
    if (s.verb == Verb::Enter) {
        // What it went into, so its removal brings the actor out (validate).
        Inside& in = inside_[static_cast<std::size_t>(i)];
        in = {};
        if (a.reserved && a.resType != kTileRes) {
            in = {{a.resX, a.resY}, a.resType};
        } else if (const Item* home = homeItem(env, a)) {
            in = {home->pos, home->type};
        }
        a.flags |= kFadeOut;
        a.state = ActorState::Inside;
        a.anim = 1;
        a.timer = s.dur1 > 0 ? range(a, s.dur0, s.dur1) : 0.0f;
        if (s.dur1 <= 0 && s.until == Until::None) a.flags |= kGone; // in for good
        return;
    }
    a.state = ActorState::Act;
    a.anim = s.anim != 0xFF ? s.anim : 1;
    a.timer = s.dur1 > 0 ? range(a, s.dur0, s.dur1) : 0.0f;
    a.call = s.every1 > 0 ? range(a, s.every0, s.every1) : 0.0f;
    if (d.face != 0xFF && dist(a.pos, d.point) < 0.1f) a.facing = facingOf(d.face);
    if (d.look.x >= 0) a.facing = facingFor({d.look.x - a.pos.x, d.look.y - a.pos.y});
    if (s.effect == Effect::CallHens || s.effect == Effect::TossPebble ||
        s.effect == Effect::ReactLine)
        fireEffect(env, i, s.effect);
    if (s.dur1 <= 0 && s.until == Until::None) a.state = ActorState::Choose;
}

void Actors::finishStep(const ActorEnv& env, int i) {
    Actor& a = pool_[static_cast<std::size_t>(i)];
    if ((a.flags & kPause) != 0 || a.depth == 0) {
        a.flags &= static_cast<std::uint16_t>(~kPause);
        a.state = ActorState::Choose;
        return;
    }
    if ((a.flags & kErrand) != 0) {
        a.flags &= static_cast<std::uint16_t>(~kErrand);
        restart(i);
        return;
    }
    const ActorProgram& p = cat_->program;
    const ActorFrame& f = a.stack[a.depth - 1];
    const Step& s = p.steps[static_cast<std::size_t>(
        p.blockSteps[static_cast<std::size_t>(p.blocks[f.block].first + f.pc)])];
    if (s.effect == Effect::WaterBed || s.effect == Effect::Cook) fireEffect(env, i, s.effect);
    a.anim = 1;
    advance(a);
}

void Actors::fireEffect(const ActorEnv& env, int i, Effect e) {
    Actor& a = pool_[static_cast<std::size_t>(i)];
    const TilePos at{a.resX, a.resY};
    switch (e) {
    case Effect::None: return;
    case Effect::WaterBed:
        if (!a.reserved) return;
        watered_.emplace_back(at, env.day);
        std::erase_if(watered_, [&](const auto& w) { return w.second != env.day; });
        break;
    case Effect::CallHens: {
        // Everyone who lives in the item she feeds at comes to peck around her.
        if (!a.reserved) return;
        for (std::size_t j = 0; j < pool_.size(); ++j) {
            Actor& h = pool_[j];
            const ActorKind& hk = cat_->kinds[h.kind];
            if ((h.flags & kAlive) == 0 || (h.flags & kLeaving) != 0 || hk.home != a.resType ||
                dist(h.pos, a.pos) > tuning::kCallRadius)
                continue;
            const auto peck = std::ranges::find(hk.anims, "peck");
            Errand& er = errands_[j];
            er.point = {a.pos.x + range(h, -1.5f, 1.5f), a.pos.y + range(h, -1.5f, 1.5f)};
            er.dur = tuning::kHenPeckSeconds;
            er.anim =
                peck == hk.anims.end() ? 1 : static_cast<std::uint8_t>(peck - hk.anims.begin());
            er.say = -1;
            beginErrand(env, static_cast<int>(j));
        }
        break;
    }
    case Effect::Cook:
        a.goods = 0xFF;
        a.goodsCount = 0;
        break;
    case Effect::TossPebble: break;
    case Effect::ReactLine: {
        a.facing = facingFor({static_cast<float>(placedAt_.x) + 0.5f - a.pos.x,
                              static_cast<float>(placedAt_.y) + 0.5f - a.pos.y});
        int ctx = -1;
        if (placedType_ == -1) ctx = cat_->resident.context("place_water");
        if (placedType_ >= 0) {
            const auto& tags = cat_->items[static_cast<std::size_t>(placedType_)].tags;
            if (!tags.empty())
                ctx = cat_->resident.context("place_" +
                                             cat_->tags[static_cast<std::size_t>(tags.front())]);
        }
        if (ctx < 0) ctx = cat_->resident.context("place_other");
        if (ctx >= 0) say(i, ctx);
        return;
    }
    }
    events_.push_back({ActorEvent::Kind::Effect, i, a.kind, a.pos, static_cast<int>(e), at, false});
}

void Actors::say(int i, int context) {
    if (context < 0) return;
    const Actor& a = pool_[static_cast<std::size_t>(i)];
    events_.push_back({ActorEvent::Kind::Say, i, a.kind, a.pos, context, {}, false});
}

// --- Moving -----------------------------------------------------------------------------------

void Actors::travel(const ActorEnv& env, int i, float dt) {
    Actor& a = pool_[static_cast<std::size_t>(i)];
    const ActorKind& k = cat_->kinds[a.kind];
    const World& world = *env.world;
    const Pick& d = dests_[static_cast<std::size_t>(i)];
    if (a.pathLen == kPathPending && !plan(env, i, false)) {
        a.state = ActorState::Choose;
        finishFailed(i);
        return;
    }
    if (a.pathLen == kPathPending) return;
    const bool last = a.pathPos >= a.pathLen;
    const Vec2 next = last ? a.goal : centre(paths_[static_cast<std::size_t>(i)][a.pathPos]);
    float speed = k.speed;
    if (k.visitor < 0)
        speed = stepCost(world, *cat_, Locomotion::Walk, tileOf(a.pos)) <= tuning::kPathCostPaved
                    ? tuning::kResidentSpeedPath
                    : tuning::kResidentSpeedOther;
    if ((a.flags & (kFleeing | kStepAside)) != 0) speed *= tuning::kStartleSpeed;
    const Vec2 delta{next.x - a.pos.x, next.y - a.pos.y};
    const float len = std::hypot(delta.x, delta.y);
    const float step = speed * dt;
    if (len > 1e-4f) a.facing = facingFor(delta);
    if (k.move == Locomotion::Fly) {
        // Flyers rise to their flight height and settle at the end.
        const float near = std::min(1.0f, len / 1.0f);
        const float hover = tuning::kHoverMin * cat_->iso().tileH();
        const float want = d.lift + (std::max(hover, d.lift) - d.lift) * near;
        a.lift += (want - a.lift) * std::min(1.0f, dt * 4.0f);
    } else {
        a.lift += (0.0f - a.lift) * std::min(1.0f, dt * 8.0f);
    }
    Vec2 np =
        len <= step ? next : Vec2{a.pos.x + delta.x / len * step, a.pos.y + delta.y / len * step};
    const TilePos nt = tileOf(np);
    // Never step onto a tile that is off-limits: from off the middle of a tile (getting up from
    // a seat) a straight line may clip a corner the plan went round, so it goes to the middle
    // first; a tile that closed since the way was planned means planning again.
    if (k.move != Locomotion::Fly && !(nt == tileOf(a.pos)) && !(nt == tileOf(a.goal)) &&
        !passable(world, *cat_, k.move, nt, true)) {
        const Vec2 mid = centre(tileOf(a.pos));
        const float off = dist(a.pos, mid);
        if (off > 0.02f) {
            const float s2 = std::min(off, step);
            a.pos = {a.pos.x + (mid.x - a.pos.x) / off * s2,
                     a.pos.y + (mid.y - a.pos.y) / off * s2};
            return;
        }
        if (!plan(env, i, true)) finishFailed(i);
        return;
    }
    a.pos = np;
    if (len > step) return;
    if (!last) {
        ++a.pathPos;
        return;
    }
    // Arrived.
    a.lift = d.lift;
    if (d.face != 0xFF) a.facing = facingOf(d.face);
    if (d.look.x >= 0) a.facing = facingFor({d.look.x - a.pos.x, d.look.y - a.pos.y});
    if ((a.flags & kFleeing) != 0) {
        a.flags &= static_cast<std::uint16_t>(~kFleeing);
        restart(i);
        return;
    }
    if ((a.flags & kStepAside) != 0) {
        // Stepped aside: an interrupt carries on with its step, anything else chooses afresh.
        a.flags &= static_cast<std::uint16_t>(~kStepAside);
        if (a.prio == 0) restart(i);
        a.state = ActorState::Choose;
        return;
    }
    if ((a.flags & kErrand) != 0) {
        const Errand& er = errands_[static_cast<std::size_t>(i)];
        if (er.say >= 0) say(i, er.say);
        a.state = ActorState::Act;
        a.anim = er.anim;
        a.timer = er.dur;
        if (er.look.x >= 0) a.facing = facingFor({er.look.x - a.pos.x, er.look.y - a.pos.y});
        return;
    }
    if (a.depth == 0) {
        // A potter between routines: rest a moment.
        a.state = ActorState::Act;
        a.anim = 1;
        a.timer = range(a, tuning::kIdleMin, tuning::kIdleMax);
        a.flags |= kPause;
        return;
    }
    const ActorProgram& p = cat_->program;
    const ActorFrame& f = a.stack[a.depth - 1];
    const Step& s = p.steps[static_cast<std::size_t>(
        p.blockSteps[static_cast<std::size_t>(p.blocks[f.block].first + f.pc)])];
    switch (s.verb) {
    case Verb::Use:
    case Verb::Enter: arrive(env, i, s); break;
    case Verb::Wander:
        // Wandering: a short idle after each walk; with a duration, more walks until it is up.
        a.state = ActorState::Act;
        a.anim = 1;
        a.timer = range(a, tuning::kIdleMin * 0.5f,
                        k.move == Locomotion::Fly ? tuning::kAirIdleMax : tuning::kIdleMax);
        break;
    default: advance(a); break;
    }
}

void Actors::finishFailed(int i) {
    Actor& a = pool_[static_cast<std::size_t>(i)];
    a.flags &= static_cast<std::uint16_t>(~(kErrand | kFleeing));
    restart(i);
    a.state = ActorState::Act;
    a.anim = 1;
    a.timer = range(a, 0.3f, 1.0f);
    a.flags |= kPause;
}

void Actors::follow(const ActorEnv& env, int i, float dt) {
    Actor& a = pool_[static_cast<std::size_t>(i)];
    const ActorKind& k = cat_->kinds[a.kind];
    a.timer -= dt;
    const bool line = (a.flags & kFollower) != 0;
    int leader = line ? lineAhead(i) : resident_;
    if (leader < 0 || (!line && (a.timer <= 0 || !residentAvailable()))) {
        a.flags &= static_cast<std::uint16_t>(~kOnHat);
        if (line) {
            a.flags &= static_cast<std::uint16_t>(~kFollower);
            restart(i);
        } else {
            advance(a);
        }
        return;
    }
    const Actor& l = pool_[static_cast<std::size_t>(leader)];
    const ActorProgram& p = cat_->program;
    // A swimmer in line goes ashore only behind a leader that went ashore.
    const bool ashore = !env.world->isWater(tileOf(l.pos));
    // On her hat: once she has sat long enough, land there and rest.
    bool hat = false;
    if (!line && a.depth > 0) {
        const ActorFrame& f = a.stack[a.depth - 1];
        const Step& s = p.steps[static_cast<std::size_t>(
            p.blockSteps[static_cast<std::size_t>(p.blocks[f.block].first + f.pc)])];
        hat = s.onHat && sat_ > 0;
    }
    Vec2 want;
    const float spacing = line ? tuning::kLineSpacing : tuning::kFollowSpacing;
    if (hat) {
        want = l.pos;
    } else {
        // A point behind the one ahead, opposite the way it faces.
        static constexpr Vec2 kBack[] = {{-1, 0}, {0, -1}, {1, 0}, {0, 1}};
        const int dir = l.facing == Facing::Front           ? 0
                        : l.facing == Facing::FrontMirrored ? 1
                        : l.facing == Facing::BackMirrored  ? 2
                                                            : 3;
        want = {l.pos.x + kBack[dir].x * spacing, l.pos.y + kBack[dir].y * spacing};
        // Behind a leader that went ashore, a swimmer finds its own spot on the bank beside it
        // (ducks sleep side by side on land, not on the water behind the one ahead).
        if (k.move == Locomotion::Swim && ashore && env.world->inBounds(tileOf(want)) &&
            env.world->isWater(tileOf(want))) {
            for (const Vec2 o : kBack) {
                const Vec2 c{l.pos.x + o.x * spacing, l.pos.y + o.y * spacing};
                if (env.world->inBounds(tileOf(c)) && !env.world->isWater(tileOf(c)) &&
                    passable(*env.world, *cat_, k.move, tileOf(c), true)) {
                    want = c;
                    break;
                }
            }
        }
        if (k.move != Locomotion::Fly && !passable(*env.world, *cat_, k.move, tileOf(want), ashore))
            want = l.pos;
        if (k.move == Locomotion::Swim && !ashore) want = offShore(*env.world, want);
    }
    // A line member does what its leader does: acting together, sleeping side by side.
    const bool leaderActs = line && l.state == ActorState::Act;
    // A swimmer still on the water behind a leader that went ashore keeps coming until it is
    // ashore too, however close it already is, to a spot well inside its tile (not on the edge
    // where the water begins).
    const bool wading = k.move == Locomotion::Swim && ashore &&
                        env.world->inBounds(tileOf(a.pos)) && env.world->isWater(tileOf(a.pos));
    if (wading) {
        const TilePos wt = tileOf(want);
        want = {
            std::clamp(want.x, static_cast<float>(wt.x) + 0.25f, static_cast<float>(wt.x) + 0.75f),
            std::clamp(want.y, static_cast<float>(wt.y) + 0.25f, static_cast<float>(wt.y) + 0.75f)};
    }
    const Vec2 dlt{want.x - a.pos.x, want.y - a.pos.y};
    const float len = std::hypot(dlt.x, dlt.y);
    const float gap = hat ? 0.02f : spacing * 0.3f;
    const float close = wading ? 0.02f : gap;
    if (len > close && (!leaderActs || wading || len >= spacing * 1.5f)) {
        const float step = std::min(len - close * 0.5f, k.speed * 1.2f * dt);
        const Vec2 np{a.pos.x + dlt.x / len * step, a.pos.y + dlt.y / len * step};
        const bool moves = k.move == Locomotion::Fly || tileOf(np) == tileOf(a.pos) ||
                           passable(*env.world, *cat_, k.move, tileOf(np), ashore);
        if (moves) a.pos = np;
        a.facing = facingFor(dlt);
        a.anim = 0;
        // A follower that cannot close the gap gives up the line for a while and chooses on
        // its own, instead of paddling on the spot (Q3-01).
        float& stuck = stuck_[static_cast<std::size_t>(i)];
        stuck = moves ? 0.0f : stuck + dt;
        if (line && stuck > tuning::kFollowStuckSeconds) {
            stuck = 0;
            lineBan_[static_cast<std::size_t>(i)] = tuning::kLineBanSeconds;
            a.flags &= static_cast<std::uint16_t>(~kFollower);
            restart(i);
            return;
        }
    } else {
        stuck_[static_cast<std::size_t>(i)] = 0;
        a.anim = leaderActs ? l.anim : 1;
        if (leaderActs) a.facing = l.facing;
    }
    if (hat && len < 0.1f) {
        a.flags |= kOnHat;
        const auto rest = std::ranges::find(k.anims, "rest");
        if (rest != k.anims.end()) a.anim = static_cast<std::uint8_t>(rest - k.anims.begin());
    } else {
        a.flags &= static_cast<std::uint16_t>(~kOnHat);
    }
    if (k.move == Locomotion::Fly && (a.flags & kOnHat) == 0) {
        const float hover = tuning::kHoverMin * cat_->iso().tileH();
        a.lift += (hover - a.lift) * std::min(1.0f, dt * 4.0f);
    }
}

int Actors::lineAhead(int i) const {
    return std::cmp_less(i, lineAhead_.size()) ? lineAhead_[static_cast<std::size_t>(i)] : -1;
}

int Actors::waterBody(const World& world, Vec2 p) const {
    // The connected body of water a swimmer is on, or beside (ducks asleep on the bank).
    const TilePos t = tileOf(p);
    const auto at = [&](TilePos q) -> int {
        if (!bodyArea_.contains(q) || !world.isWater(q)) return -1;
        return bodies_[static_cast<std::size_t>((q.y - bodyArea_.y0) * bodyArea_.width() +
                                                (q.x - bodyArea_.x0))];
    };
    if (const int b = at(t); b >= 0) return b;
    for (int dy = -1; dy <= 1; ++dy)
        for (int dx = -1; dx <= 1; ++dx)
            if (const int b = at({t.x + dx, t.y + dy}); b >= 0) return b;
    return -1;
}

void Actors::updateLines(const ActorEnv& env) {
    // Lines form per kind and per connected body of water (Q3-01): a duck on another pond is
    // never asked to follow one it cannot reach. Bodies are labelled within the active area,
    // again only when the world or the area changes.
    const World& world = *env.world;
    if (bodyRevision_ != world.revision() || bodyArea_ != area_) {
        bodyRevision_ = world.revision();
        bodyArea_ = area_;
        bodies_.assign(static_cast<std::size_t>(std::max(0, area_.width() * area_.height())), -1);
        int next = 0;
        std::vector<TilePos>& open = bodyOpen_;
        for (int y = area_.y0; y < area_.y1; ++y)
            for (int x = area_.x0; x < area_.x1; ++x) {
                const auto idx = [&](TilePos q) {
                    return static_cast<std::size_t>((q.y - area_.y0) * area_.width() +
                                                    (q.x - area_.x0));
                };
                if (!world.isWater({x, y}) || bodies_[idx({x, y})] >= 0) continue;
                open.clear();
                open.push_back({x, y});
                bodies_[idx({x, y})] = next;
                while (!open.empty()) {
                    const TilePos q = open.back();
                    open.pop_back();
                    for (const TilePos d :
                         {TilePos{1, 0}, TilePos{-1, 0}, TilePos{0, 1}, TilePos{0, -1}}) {
                        const TilePos n{q.x + d.x, q.y + d.y};
                        if (area_.contains(n) && world.isWater(n) && bodies_[idx(n)] < 0) {
                            bodies_[idx(n)] = next;
                            open.push_back(n);
                        }
                    }
                }
                ++next;
            }
    }
    // The one ahead: the previous member of the same kind on the same water, in pool order.
    lineAhead_.assign(pool_.size(), -1);
    lineTail_.clear();
    for (std::size_t j = 0; j < pool_.size(); ++j) {
        const Actor& a = pool_[j];
        const ActorKind& k = cat_->kinds[a.kind];
        if ((a.flags & kAlive) == 0 || !k.line || (a.flags & kLeaving) != 0 || lineBan_[j] > 0.0f)
            continue;
        const int body = k.move == Locomotion::Swim ? waterBody(world, a.pos) : 0;
        if (body < 0) continue;
        const auto tail = std::ranges::find_if(
            lineTail_, [&](const LineTail& t) { return t.kind == a.kind && t.body == body; });
        if (tail == lineTail_.end()) {
            lineTail_.push_back({a.kind, body, static_cast<int>(j)});
        } else {
            lineAhead_[j] = tail->actor;
            tail->actor = static_cast<int>(j);
        }
    }
}

// --- Interrupts, errands and reactions -----------------------------------------------------------

void Actors::beginInterrupt(int i, const Interrupt& in) {
    Actor& a = pool_[static_cast<std::size_t>(i)];
    a.flags &= static_cast<std::uint16_t>(~(kErrand | kFleeing | kFollower));
    restart(i);
    const Routine& r = cat_->program.routines[static_cast<std::size_t>(in.routine)];
    push(a, r.block, r.loop ? kLoopFrame : 0);
    a.prio = static_cast<std::uint8_t>(std::max(1, in.priority));
}

void Actors::beginErrand(const ActorEnv& env, int i) {
    Actor& a = pool_[static_cast<std::size_t>(i)];
    Errand& er = errands_[static_cast<std::size_t>(i)];
    // The point itself, or the nearest tile around it this actor may stand on.
    TilePos t = tileOf(er.point);
    if (!freeTile(env, a, t)) {
        bool found = false;
        for (int r = 1; r <= 2 && !found; ++r)
            for (int y = t.y - r; y <= t.y + r && !found; ++y)
                for (int x = t.x - r; x <= t.x + r && !found; ++x)
                    if (freeTile(env, a, {x, y})) {
                        er.point = centre({x, y});
                        found = true;
                    }
        if (!found) return;
    }
    restart(i);
    a.flags &= static_cast<std::uint16_t>(~kFollower);
    Pick pk;
    pk.point = er.point;
    if (!goTo(env, i, pk)) return;
    a.flags |= kErrand;
}

bool Actors::interrupts(const ActorEnv& env, int i, float dt) {
    Actor& a = pool_[static_cast<std::size_t>(i)];
    const ActorKind& k = cat_->kinds[a.kind];
    (void)dt;
    const bool rain = rainAt(env, a.pos);
    if (rain) {
        a.rainHold = static_cast<std::uint8_t>(std::min(255, a.rainHold + bucketTicks_));
    } else {
        a.rainHold = 0;
        a.flags &= static_cast<std::uint16_t>(~kSheltered);
    }
    for (const Interrupt& in : k.interrupts) {
        if (in.on != Interrupt::On::Rain || !rain || a.prio >= in.priority ||
            a.state == ActorState::Inside || (a.flags & (kLeaving | kSheltered)) != 0)
            continue;
        // Once per spell of rain, when it has held here for the delay.
        if (a.rainHold < std::max(1.0f, in.delay * 10.0f)) continue;
        beginInterrupt(i, in);
        a.flags |= kSheltered;
        return true;
    }
    return false;
}

void Actors::disturb(const ActorEnv& env, TileRect rect, int type, bool fresh) {
    const Vec2 cause{static_cast<float>(rect.x0 + rect.x1) * 0.5f,
                     static_cast<float>(rect.y0 + rect.y1) * 0.5f};
    if (type != -2) recent_.push_back({{rect.x0, rect.y0}, env.now});
    for (std::size_t j = 0; j < pool_.size(); ++j) {
        Actor& a = pool_[j];
        if ((a.flags & kAlive) == 0 || hidden(a)) continue;
        const ActorKind& k = cat_->kinds[a.kind];
        const int i = static_cast<int>(j);
        if (k.visitor < 0) {
            // She turns to look: always at the first of its kind, otherwise sometimes.
            if (type == -2 || distToRect(a.pos, rect) > tuning::kReactRadius || asleep(a) ||
                a.prio != 0 || reactCool_ > 0 || a.state == ActorState::Inside)
                continue;
            if (a.state == ActorState::Act && a.anim != 1 &&
                cat_->kinds[a.kind].anims[a.anim] == "read")
                continue;
            for (const Interrupt& in : k.interrupts) {
                if (in.on != Interrupt::On::PlacedNearby) continue;
                if (!fresh && uniform(a) >= in.chance) break;
                placedAt_ = {rect.x0, rect.y0};
                placedType_ = type;
                reactCool_ = in.cooldown;
                beginInterrupt(i, in);
                break;
            }
            continue;
        }
        if (k.startleRadius <= 0 || a.startleCool > 0 || distToRect(a.pos, rect) > k.startleRadius)
            continue;
        if (((k.startleFrom >> a.anim) & 1) == 0) continue;
        // A short start (its animation), then away from the cause at speed.
        a.overlay = tuning::kStartleSeconds;
        a.overlayAnim = k.startleAnim != 0xFF ? k.startleAnim : 1;
        a.startleCool = static_cast<std::uint8_t>(tuning::kStartleCooldown * 10.0f);
        a.flags &= static_cast<std::uint16_t>(~kFollower);
        restart(i);
        a.flags |= kFleeing;
        Errand& er = errands_[j];
        er.point = cause;
        events_.push_back({ActorEvent::Kind::Startle, i, a.kind, a.pos, -1, {}, false});
    }
}

void Actors::flee(const ActorEnv& env, int i) {
    Actor& a = pool_[static_cast<std::size_t>(i)];
    const Vec2 cause = errands_[static_cast<std::size_t>(i)].point;
    Vec2 away{a.pos.x - cause.x, a.pos.y - cause.y};
    const float l = std::hypot(away.x, away.y);
    away = l > 1e-3f ? Vec2{away.x / l, away.y / l} : Vec2{1, 0};
    const ActorKind& k = cat_->kinds[a.kind];
    for (int attempt = 0; attempt < 8; ++attempt) {
        const float ang = range(a, -0.8f, 0.8f);
        const float r = range(a, tuning::kStartleMin, tuning::kStartleMax);
        const Vec2 d{away.x * std::cos(ang) - away.y * std::sin(ang),
                     away.x * std::sin(ang) + away.y * std::cos(ang)};
        const Vec2 p{a.pos.x + d.x * r, a.pos.y + d.y * r};
        const TilePos t = tileOf(p);
        if (!area_.contains(t)) continue;
        const bool ok =
            k.visitor >= 0
                ? habitatAllows(cat_->visitors[static_cast<std::size_t>(k.visitor)].habitat,
                                *env.world, *cat_, p)
                : passable(*env.world, *cat_, k.move, t);
        if (!ok) continue;
        Pick pk;
        pk.point = p;
        pk.lift = k.move == Locomotion::Fly ? a.lift : 0.0f;
        if (goTo(env, i, pk)) {
            a.flags |= kFleeing;
            return;
        }
    }
    a.flags &= static_cast<std::uint16_t>(~kFleeing);
    restart(i);
}

bool Actors::pet(int i) {
    if (i < 0 || std::cmp_greater_equal(i, pool_.size())) return false;
    Actor& a = pool_[static_cast<std::size_t>(i)];
    if ((a.flags & kAlive) == 0 || hidden(a)) return false;
    const ActorKind& k = cat_->kinds[a.kind];
    if (k.visitor < 0) {
        if (clickCool_ > 0) return false;
        clickCool_ = tuning::kClickCooldown;
        if (a.state != ActorState::Travel) a.facing = Facing::Front;
        say(i, cat_->resident.context("click"));
        return true;
    }
    if (a.petCool > 0) return false;
    // A sleeper wakes first (its startle animation, the cat's stretch), then is petted.
    const bool wake = asleep(a) && k.startleAnim != 0xFF;
    a.overlay = tuning::kPetSeconds + (wake ? tuning::kStartleSeconds : 0.0f);
    a.overlayAnim = k.petAnim != 0xFF ? k.petAnim : 1;
    a.petCool = static_cast<std::uint8_t>(tuning::kPetCooldown * 10.0f);
    a.facing = Facing::Front;
    events_.push_back({ActorEvent::Kind::Pet, i, a.kind, a.pos, wake ? 1 : 0, {}, false});
    return true;
}

bool Actors::harvested(const ActorEnv& env, TilePos bed) {
    const Vec2 c = centre(bed);
    bool taken = false;
    for (std::size_t j = 0; j < pool_.size(); ++j) {
        Actor& a = pool_[j];
        if ((a.flags & kAlive) == 0 || hidden(a) || (a.flags & kLeaving) != 0) continue;
        const ActorKind& k = cat_->kinds[a.kind];
        const int i = static_cast<int>(j);
        if (k.visitor < 0) {
            if (dist(a.pos, c) > tuning::kHarvestReach || !residentAvailable()) continue;
            const auto produce = std::ranges::find(cat_->goods, "produce", &GoodsDef::id);
            for (const Interrupt& in : k.interrupts) {
                if (in.on != Interrupt::On::Harvest || produce == cat_->goods.end()) continue;
                beginInterrupt(i, in);
                a.goods = static_cast<std::uint8_t>(produce - cat_->goods.begin());
                a.goodsCount = 1;
                taken = true;
                break;
            }
            continue;
        }
        // Peckers nearby come for what fell.
        const auto peck = std::ranges::find(k.anims, "peck");
        if (peck == k.anims.end() || dist(a.pos, c) > tuning::kHarvestPeckReach) continue;
        Errand& er = errands_[j];
        er.point = {c.x + range(a, -1.2f, 1.2f), c.y + range(a, -1.2f, 1.2f)};
        er.dur = tuning::kHenPeckSeconds;
        er.anim = static_cast<std::uint8_t>(peck - k.anims.begin());
        er.say = -1;
        er.look = c;
        beginErrand(env, i);
    }
    return taken;
}

void Actors::visit(const ActorEnv& env, Vec2 tile, int context, float reach, bool sketch) {
    if (resident_ < 0 || !residentAvailable()) return;
    Actor& a = pool_[static_cast<std::size_t>(resident_)];
    if (a.prio != 0 || (a.flags & kErrand) != 0 || dist(a.pos, tile) > reach) return;
    Errand& er = errands_[static_cast<std::size_t>(resident_)];
    er.point = {tile.x + 1.0f, tile.y + 1.0f};
    er.look = tile;
    er.say = context;
    // A new visitor gets drawn: she sits down to sketch it a while.
    const auto& names = cat_->kinds[a.kind].anims;
    const auto pencil = std::ranges::find(names, "sketch");
    er.anim =
        sketch && pencil != names.end() ? static_cast<std::uint8_t>(pencil - names.begin()) : 1;
    er.dur = er.anim != 1 ? tuning::kSketchVisitor : tuning::kVisitLinger;
    beginErrand(env, resident_);
}

void Actors::wave() {
    if (resident_ < 0 || !residentAvailable()) return;
    Actor& a = pool_[static_cast<std::size_t>(resident_)];
    const ActorKind& k = cat_->kinds[a.kind];
    if (k.waveAnim == 0xFF || a.state == ActorState::Travel) return;
    a.overlay = tuning::kWaveSeconds;
    a.overlayAnim = k.waveAnim;
    a.facing = Facing::Front;
}

void Actors::lookAt(std::optional<TilePos> tile) {
    look_ = tile;
}

int Actors::call(int visitor) {
    for (std::size_t j = 0; j < pool_.size(); ++j) {
        Actor& a = pool_[j];
        const ActorKind& k = cat_->kinds[a.kind];
        if ((a.flags & kAlive) == 0 || k.visitor != visitor || hidden(a) || a.overlay > 0) continue;
        a.overlay = tuning::kCallSeconds;
        a.overlayAnim = k.callAnim != 0xFF ? k.callAnim : 1;
        events_.push_back(
            {ActorEvent::Kind::Voice, static_cast<int>(j), a.kind, a.pos, -1, {}, false});
        return static_cast<int>(j);
    }
    return -1;
}

// --- The world changing under them ---------------------------------------------------------------

void Actors::validate(const ActorEnv& env, int i) {
    Actor& a = pool_[static_cast<std::size_t>(i)];
    const World& world = *env.world;
    const ActorKind& k = cat_->kinds[a.kind];
    // Its slot's item was removed or replaced: let go and choose again.
    if (a.reserved && a.resType != kTileRes) {
        const Item* it = world.itemAt({a.resX, a.resY});
        if (it == nullptr || it->type != a.resType || it->pos.x != a.resX || it->pos.y != a.resY) {
            release(i);
            if (a.state == ActorState::Act || a.state == ActorState::Travel) {
                a.flags &= static_cast<std::uint16_t>(~kErrand);
                restart(i);
            }
        }
    }
    // On the item it sits on: that is where it belongs. Only a seat it still holds counts (a
    // released one left stale fields behind: Q3-07).
    const Item* under = world.itemAt(tileOf(a.pos));
    const bool seated = a.reserved && under != nullptr && under->pos.x == a.resX &&
                        under->pos.y == a.resY && under->type == a.resType;
    if (a.state == ActorState::Inside) {
        // The home it is inside was removed (Q3-06): she comes out at once and goes on with her
        // day (to the bedroll when no cottage is left); a visitor simply leaves.
        const Inside& in = inside_[static_cast<std::size_t>(i)];
        const Item* home = in.type >= 0 ? world.itemAt(in.at) : nullptr;
        if (in.type >= 0 && (home == nullptr || home->type != in.type || home->pos != in.at)) {
            inside_[static_cast<std::size_t>(i)] = {};
            if (k.visitor >= 0) {
                a.flags |= kLeaving | kFadeOut | kGone;
            } else {
                restart(i);
                a.alpha = std::max(a.alpha, 0.01f);
            }
            return;
        }
    }
    if (a.state == ActorState::Inside || k.move == Locomotion::Fly) {
        if (!world.hasGround(tileOf(a.pos))) a.flags |= kFadeOut | kGone;
        return;
    }
    const TilePos t = tileOf(a.pos);
    // Walking off (from a seat, say) is fine; standing where it may not stand is not.
    if (seated || a.state == ActorState::Travel || passable(world, *cat_, k.move, t, true)) return;
    // Displaced: step to the nearest tile it may stand on, within a few; else go.
    float best = 1e9f;
    Vec2 to{};
    const int r = k.visitor < 0 ? tuning::kDisplaceReach : 1;
    for (int y = t.y - r; y <= t.y + r; ++y)
        for (int x = t.x - r; x <= t.x + r; ++x) {
            if (!passable(world, *cat_, k.move, {x, y})) continue;
            const float d = dist(a.pos, centre({x, y}));
            if (d < best) {
                best = d;
                to = centre({x, y});
            }
        }
    if (best < 1e9f) {
        // Whatever it was doing waits: it steps aside quickly, then carries on.
        dests_[static_cast<std::size_t>(i)] = Pick{};
        dests_[static_cast<std::size_t>(i)].point = to;
        a.goal = to;
        a.pathLen = 0;
        a.state = ActorState::Travel;
        a.flags |= kStepAside;
        return;
    }
    restart(i);
    if (k.visitor < 0) {
        // The only time she teleports: she fades and reappears at home.
        Pick pk;
        a.pos = homePick(env, i, -1, pk) ? pk.point : centre(bedroll_);
        release(i);
        a.alpha = 0;
        return;
    }
    a.flags |= kLeaving | kFadeOut | kGone;
}

// --- The step ---------------------------------------------------------------------------------

void Actors::tick(const ActorEnv& env, int i, float dt) {
    Actor& a = pool_[static_cast<std::size_t>(i)];
    const ActorKind& k = cat_->kinds[a.kind];
    a.animTime += dt;
    const float fade = dt / tuning::kFadeSeconds;
    if ((a.flags & kFadeOut) != 0 || a.state == ActorState::Inside)
        a.alpha = std::max(0.0f, a.alpha - fade);
    else
        a.alpha = std::min(1.0f, a.alpha + fade);
    if ((a.flags & kGone) != 0) {
        if (a.alpha <= 0.0f) {
            release(i);
            a.flags = 0;
        }
        return;
    }
    // Thinking is time-sliced: each actor checks the world under it and its interrupts in its
    // own bucket of steps; moving and acting run every step.
    const bool thinks = (frame_ + static_cast<std::uint32_t>(i)) % tuning::kThinkBuckets == 0;
    if (thinks) validate(env, i);
    if ((a.flags & kAlive) == 0 || (a.flags & kGone) != 0) return;
    if (a.overlay > 0) {
        a.overlay -= dt;
        // A pet or a call is a moment over the activity, not a pause of it (R2.4): its timer
        // keeps running, so petting again and again never holds a critter on one activity.
        if (a.state == ActorState::Act) a.timer -= dt;
        // A woken sleeper stretches first, then is petted.
        if ((a.flags & kFleeing) == 0 && a.overlay <= tuning::kPetSeconds && k.petAnim != 0xFF)
            a.overlayAnim = a.overlayAnim == k.startleAnim && asleep(a) ? k.petAnim : a.overlayAnim;
        if (a.overlay <= 0 && (a.flags & kFleeing) != 0 && a.state != ActorState::Travel)
            flee(env, i);
        return;
    }
    if ((a.flags & kFollower) != 0) {
        follow(env, i, dt);
        return;
    }
    if (thinks && interrupts(env, i, dt)) return;
    // Watchers turn to the pointer while sitting or idle.
    if (k.watches && look_ && a.state == ActorState::Act && !asleep(a) &&
        dist(a.pos, centre(*look_)) <= tuning::kWatchReach)
        a.facing = facingFor({static_cast<float>(look_->x) + 0.5f - a.pos.x,
                              static_cast<float>(look_->y) + 0.5f - a.pos.y});
    switch (a.state) {
    case ActorState::Travel:
        if ((a.flags & kErrand) == 0 && a.depth > 0) {
            // A wander has a time limit when it was given one.
            if (a.call > 0) a.call -= dt;
        }
        {
            const Vec2 before = a.pos;
            travel(env, i, dt);
            // A walk that has stopped getting anywhere (its way blocked again and again) is given
            // up, so nobody walks on the spot, a leaver included.
            float& stalled = stuck_[static_cast<std::size_t>(i)];
            stalled =
                a.state == ActorState::Travel && dist(before, a.pos) < 1e-4f ? stalled + dt : 0;
            if (stalled > tuning::kTravelStuckSeconds) {
                stalled = 0;
                a.state = ActorState::Choose;
                finishFailed(i);
            }
            break;
        }
    case ActorState::Act: {
        a.timer -= dt;
        bool done = a.timer <= 0;
        // Her day moved on to its next part: she finishes what she is doing now.
        if (k.visitor < 0 && a.prio == 0 && thinks && a.depth > 0 && scheduleBlock(env) != a.sched)
            done = true;
        if (a.depth > 0 && (a.flags & (kPause | kErrand)) == 0) {
            const ActorProgram& p = cat_->program;
            const ActorFrame& f = a.stack[a.depth - 1];
            const Step& s = p.steps[static_cast<std::size_t>(
                p.blockSteps[static_cast<std::size_t>(p.blocks[f.block].first + f.pc)])];
            if (s.until != Until::None) done = untilMet(env, a, s);
            if (s.verb == Verb::Wander && done) {
                // More walks while its time lasts.
                Pick pk;
                if (a.call > 0 && wanderPick(env, i, s.radius, pk, s.activity) && goTo(env, i, pk))
                    break;
            }
            // Calls during the act (the owl's hoot, the heron's strike).
            if (s.every1 > 0 && s.callAnim != 0xFF) {
                a.call -= dt;
                if (a.call <= 0) {
                    a.call = range(a, s.every0, s.every1);
                    a.overlay = tuning::kCallSeconds;
                    a.overlayAnim = s.callAnim;
                    events_.push_back({ActorEvent::Kind::Voice, i, a.kind, a.pos, -1, {}, false});
                }
            }
        }
        if (done) finishStep(env, i);
        break;
    }
    case ActorState::Inside: {
        if (a.depth == 0) break;
        const ActorProgram& p = cat_->program;
        const ActorFrame& f = a.stack[a.depth - 1];
        const Step& s = p.steps[static_cast<std::size_t>(
            p.blockSteps[static_cast<std::size_t>(p.blocks[f.block].first + f.pc)])];
        a.timer -= dt;
        const bool done = s.until != Until::None ? untilMet(env, a, s) : a.timer <= 0 && s.dur1 > 0;
        if (done) {
            a.flags &= static_cast<std::uint16_t>(~kFadeOut);
            a.state = ActorState::Choose;
            ++a.stack[a.depth - 1].pc;
        }
        break;
    }
    case ActorState::Follow: follow(env, i, dt); break;
    case ActorState::Choose: break;
    }
    if (a.state == ActorState::Choose) run(env, i);
}

void Actors::update(const ActorEnv& env, float dt) {
    searches_ = 0;
    map_ = env.world;
    updateHome(env);
    // Her private clock while the real one is pinned loops the pinned phase's blocks (R6.7).
    if (env.pinned) {
        const auto [from, to] = phaseHours(env.phase);
        if (!wasPinned_ || pinPhase_ != env.phase) hourPrivate_ = from;
        hourPrivate_ += dt * 24.0f / static_cast<float>(tuning::kDayLengthSeconds);
        if (hourPrivate_ >= to) hourPrivate_ = from;
        pinPhase_ = env.phase;
    }
    wasPinned_ = env.pinned;
    presence(env, dt);
    if (resident_ < 0 && cat_->residentKind >= 0) {
        resident_ = spawn(env, cat_->residentKind, 0.0f, false);
    }
    // Lines: everyone but the first of a kind on a body of water follows the one ahead.
    for (float& b : lineBan_) b = std::max(0.0f, b - dt);
    updateLines(env);
    for (std::size_t j = 0; j < pool_.size(); ++j) {
        Actor& a = pool_[j];
        if ((a.flags & kAlive) == 0 || !cat_->kinds[a.kind].line || (a.flags & kLeaving) != 0)
            continue;
        const bool follower = lineAhead(static_cast<int>(j)) >= 0;
        if (follower && (a.flags & kFollower) == 0 && a.overlay <= 0 &&
            (a.flags & (kFleeing | kErrand)) == 0) {
            restart(static_cast<int>(j));
            a.flags |= kFollower;
            a.state = ActorState::Follow;
        } else if (!follower && (a.flags & kFollower) != 0) {
            a.flags &= static_cast<std::uint16_t>(~kFollower);
            restart(static_cast<int>(j));
        }
    }
    // Cooldowns in tenths of a second.
    tenths_ += dt * 10.0f;
    ticks_ = static_cast<int>(tenths_);
    tenths_ -= static_cast<float>(ticks_);
    // Each bucket of thinkers sees the tenths since its last turn.
    ++frame_;
    bucketTenths_ += dt * 10.0f * static_cast<float>(tuning::kThinkBuckets);
    bucketTicks_ = static_cast<int>(bucketTenths_);
    bucketTenths_ -= static_cast<float>(bucketTicks_);
    for (std::size_t j = 0; j < pool_.size(); ++j)
        if ((pool_[j].flags & kLeaving) != 0) leaveAge_[j] += dt;
    for (Actor& a : pool_) {
        a.petCool = static_cast<std::uint8_t>(std::max(0, a.petCool - ticks_));
        a.startleCool = static_cast<std::uint8_t>(std::max(0, a.startleCool - ticks_));
    }
    reactCool_ = std::max(0.0f, reactCool_ - dt);
    clickCool_ = std::max(0.0f, clickCool_ - dt);
    for (std::size_t j = 0; j < pool_.size(); ++j)
        if ((pool_[j].flags & kAlive) != 0) tick(env, static_cast<int>(j), dt);
    // How long she has been sitting (butterflies land on her hat after a while).
    if (resident_ >= 0) {
        const Actor& r = pool_[static_cast<std::size_t>(resident_)];
        const bool sitting = r.state == ActorState::Act && r.lift > 0 && !hidden(r);
        sat_ = sitting ? sat_ + dt : 0.0f;
    }
    std::erase_if(recent_,
                  [&](const Recent& r) { return env.now - r.when > tuning::kNewItemSeconds; });
    countPresence();
}

std::string Actors::populationError(std::span<const VisitorGate> gates) const {
    std::vector<int> present(cat_->visitors.size(), 0);
    for (std::size_t j = 0; j < pool_.size(); ++j) {
        const Actor& a = pool_[j];
        if ((a.flags & kAlive) == 0 || (a.flags & kCrowd) != 0) continue;
        const int v = cat_->kinds[a.kind].visitor;
        if (v < 0) continue;
        if ((a.flags & kLeaving) != 0) {
            if (leaveAge_[j] > tuning::kLeaveLimitSeconds)
                return cat_->visitors[static_cast<std::size_t>(v)].id + " #" + std::to_string(j) +
                       " has been leaving for " + std::to_string(leaveAge_[j]) + " s";
            continue;
        }
        ++present[static_cast<std::size_t>(v)];
    }
    for (std::size_t v = 0; v < present.size(); ++v) {
        const int extra = v < gates.size() ? gates[v].extra : 0;
        if (present[v] > cat_->visitors[v].max + extra)
            return std::to_string(present[v]) + " " + cat_->visitors[v].id + " present, max " +
                   std::to_string(cat_->visitors[v].max + extra);
    }
    return {};
}

int Actors::crowd(const ActorEnv& env, int count) {
    map_ = env.world;
    area_ = env.area;
    std::uint64_t rng = seed_ ^ 0xC40DULL;
    int placed = 0;
    for (int n = 0; n < count * 4 && placed < count; ++n) {
        const int kind = n % static_cast<int>(cat_->visitors.size());
        const Habitat h = cat_->visitors[static_cast<std::size_t>(kind)].habitat;
        const TilePos t{
            area_.x0 +
                static_cast<int>(splitmix(rng) % static_cast<std::uint64_t>(area_.x1 - area_.x0)),
            area_.y0 +
                static_cast<int>(splitmix(rng) % static_cast<std::uint64_t>(area_.y1 - area_.y0))};
        if (!habitatAllows(h, *env.world, *cat_, centre(t))) continue;
        Actor a;
        a.rng = seed_ ^ (0xC0FFEEULL + spawned_++);
        a.kind = static_cast<std::uint16_t>(kind);
        // A crowd member stays whatever the visitor rules want (Q3-10: the bench measures the
        // number it asked for).
        a.flags = kAlive | kCrowd;
        a.alpha = 1;
        a.pos = a.goal = centre(t);
        if (cat_->kinds[static_cast<std::size_t>(kind)].move == Locomotion::Fly)
            a.lift = tuning::kHoverMin * cat_->iso().tileH();
        if (pool_.size() >= tuning::kActorPool) break;
        claim(pool_.size(), a);
        ++placed;
    }
    return placed;
}

void Actors::populate(const ActorEnv& env) {
    map_ = env.world;
    for (std::size_t i = 0; i < pool_.size(); ++i)
        if ((pool_[i].flags & kAlive) != 0) release(static_cast<int>(i));
    pool_.clear();
    paths_.clear();
    errands_.clear();
    dests_.clear();
    reservations_.clear();
    resident_ = -1;
    area_ = env.area;
    tallyArea(*env.world, *cat_, area_, tally_);
    tallyRevision_ = env.world->revision();
    updateHome(env);
    const bool night = env.phase == Phase::Night;
    for (std::size_t v = 0; v < cat_->visitors.size(); ++v) {
        // Kinds never seen arrive the normal way, so their first sighting is still an event.
        if (!seen(static_cast<int>(v))) continue;
        const int want = desiredCount(cat_->visitors[v], tally_, night, env.gates[v]);
        for (int n = 0; n < want; ++n) (void)spawn(env, static_cast<int>(v), 1.0f, false);
        cooldown_[v] = tuning::kArrivalInterval;
    }
    if (cat_->residentKind >= 0) {
        resident_ = spawn(env, cat_->residentKind, 1.0f, false);
        // At night, with a home, she is already inside.
        if (resident_ >= 0 && env.phase == Phase::Night && home_) {
            Actor& a = pool_[static_cast<std::size_t>(resident_)];
            a.alpha = 0;
        }
    }
    countPresence();
}

} // namespace lc
