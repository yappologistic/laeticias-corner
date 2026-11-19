#include "life/city.hpp"

#include "core/tuning.hpp"

#include <algorithm>
#include <bit>
#include <chrono>
#include <climits>
#include <cmath>
#include <numbers>
#include <unordered_map>

namespace lc::life {

namespace tl = tuning::life;
using world::kSteps;
using world::Placed;
using world::WorldSlot;

namespace {

constexpr std::uint32_t kNoStep = 0xFFFFFFFF;
constexpr int kHalfChunk = kChunk / 2;
constexpr double kDaySeconds = 720.0;
constexpr double kSecondsPerHour = 30.0;

std::uint64_t mix(std::uint64_t z) {
    z += 0x9E3779B97F4A7C15ULL;
    z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL;
    z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL;
    return z ^ (z >> 31);
}

std::uint64_t hashOf(std::initializer_list<std::uint64_t> parts) {
    std::uint64_t h = 0x243F6A8885A308D3ULL;
    for (const std::uint64_t p : parts) h = mix(h ^ p);
    return h == 0 ? 1 : h;
}

// [0, 1) from a hash.
double unit(std::uint64_t h) {
    return static_cast<double>(h >> 11) * (1.0 / 9007199254740992.0);
}

std::uint64_t next(std::uint64_t& state) {
    std::uint64_t z = (state += 0x9E3779B97F4A7C15ULL);
    z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL;
    z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL;
    return z ^ (z >> 31);
}

float uniform(LiveActor& a) {
    return static_cast<float>(next(a.rng) >> 40) * (1.0f / 16777216.0f);
}
float range(LiveActor& a, float lo, float hi) {
    return lo + (hi - lo) * uniform(a);
}

Vec2 centre(TilePos t) {
    return {static_cast<float>(t.x) + 0.5f, static_cast<float>(t.y) + 0.5f};
}

std::uint8_t facingOf(int dx, int dy) {
    if (dx > 0) return 0; // +x: front
    if (dy > 0) return 1; // +y: front mirrored
    if (dy < 0) return 2; // -y: back
    return 3;             // -x: back mirrored
}

float dist2(Vec2 a, Vec2 b) {
    const float dx = a.x - b.x;
    const float dy = a.y - b.y;
    return dx * dx + dy * dy;
}

} // namespace

// Open addressing from identity keys to pool records (no allocation after construction).
struct CityLife::KeyIndex {
    explicit KeyIndex(std::size_t capacity) : keys(capacity, 0), values(capacity, -1) {}
    std::vector<std::uint64_t> keys;
    std::vector<int> values;
    [[nodiscard]] std::size_t home(std::uint64_t k) const { return mix(k) & (keys.size() - 1); }
    [[nodiscard]] int find(std::uint64_t k) const {
        for (std::size_t i = home(k);; i = (i + 1) & (keys.size() - 1)) {
            if (keys[i] == 0) return -1;
            if (keys[i] == k) return values[i];
        }
    }
    void insert(std::uint64_t k, int v) {
        std::size_t i = home(k);
        while (keys[i] != 0 && keys[i] != k) i = (i + 1) & (keys.size() - 1);
        keys[i] = k;
        values[i] = v;
    }
    void erase(std::uint64_t k) {
        std::size_t i = home(k);
        while (keys[i] != k) {
            if (keys[i] == 0) return;
            i = (i + 1) & (keys.size() - 1);
        }
        // Backward-shift deletion keeps every probe chain unbroken.
        std::size_t j = i;
        for (;;) {
            keys[i] = 0;
            values[i] = -1;
            for (;;) {
                j = (j + 1) & (keys.size() - 1);
                if (keys[j] == 0) return;
                const std::size_t h = home(keys[j]);
                const bool between = i <= j ? (i < h && h <= j) : (i < h || h <= j);
                if (!between) break;
            }
            keys[i] = keys[j];
            values[i] = values[j];
            i = j;
        }
    }
};

// -- the clock -----------------------------------------------------------------------------------

double LifeClock::hour() const {
    return std::fmod(6.0 + 24.0 * t, 24.0);
}

double LifeClock::seconds() const {
    const double cycle = t < tuning::kMidnight ? t : t - 1.0;
    return static_cast<double>(day) * kDaySeconds + cycle * kDaySeconds;
}

LifeClock LifeClock::at(int day, double hour, int season, bool rain) {
    LifeClock c;
    c.day = day;
    c.t = std::fmod((hour - 6.0) / 24.0 + 1.0, 1.0);
    c.season = season;
    c.rain = rain;
    return c;
}

// -- the shared world ----------------------------------------------------------------------------

std::unique_ptr<LifeWorld> buildLifeWorld(const LoadedWorld& w) {
    const auto t0 = std::chrono::steady_clock::now();
    auto lw = std::make_unique<LifeWorld>();
    lw->world = &w;
    lw->data = compileLife(w);
    const WorldMap& map = *w.map;
    lw->pathsOf.assign(lw->data.regions.size(), -1);
    for (std::size_t r = 0; r < lw->data.regions.size(); ++r) {
        const LifeRegion& reg = lw->data.regions[r];
        if (reg.layer < 0) continue;
        lw->pathsOf[r] = static_cast<int>(lw->paths.size());
        lw->paths.emplace_back(map, w.graphs[static_cast<std::size_t>(reg.layer)], reg.worldRegion);
    }
    // Slot groups: the spots of one slot of one placed item. The map keeps slots by chunk, so a
    // group's spots need not be neighbours there: each group lists its own (L-116).
    const auto& slots = map.slots();
    lw->slotGroup.resize(slots.size());
    std::unordered_map<std::uint64_t, std::uint32_t> groups;
    std::vector<std::uint32_t> spots;
    for (std::size_t s = 0; s < slots.size(); ++s) {
        const std::uint64_t k = (static_cast<std::uint64_t>(slots[s].item) << 16) | slots[s].name;
        const auto [it, fresh] = groups.emplace(k, static_cast<std::uint32_t>(lw->groupCap.size()));
        if (fresh) {
            lw->groupCap.push_back(slots[s].cap);
            spots.push_back(0);
        }
        lw->slotGroup[s] = it->second;
        ++spots[it->second];
    }
    lw->groupSpotsAt.assign(spots.size() + 1, 0);
    for (std::size_t g = 0; g < spots.size(); ++g)
        lw->groupSpotsAt[g + 1] = lw->groupSpotsAt[g] + spots[g];
    lw->groupSlots.resize(slots.size());
    std::vector<std::uint32_t> next(lw->groupSpotsAt.begin(), lw->groupSpotsAt.end() - 1);
    for (std::size_t s = 0; s < slots.size(); ++s)
        lw->groupSlots[next[lw->slotGroup[s]]++] = static_cast<std::uint32_t>(s);
    lw->chunkDistricts.resize(static_cast<std::size_t>(map.chunksX() * map.chunksY()));
    lw->regionItems.resize(lw->data.regions.size());
    for (std::size_t r = 0; r < lw->data.regions.size(); ++r) {
        const LifeRegion& reg = lw->data.regions[r];
        for (std::size_t d = 0; d < reg.districts.size(); ++d)
            for (const auto& [chunk, tiles] : reg.districts[d].chunks)
                lw->chunkDistricts[chunk].push_back({static_cast<std::uint16_t>(r),
                                                     static_cast<std::uint16_t>(d),
                                                     static_cast<std::uint16_t>(tiles)});
    }
    for (std::uint32_t i = 0; i < map.items().size(); ++i) {
        const Placed& it = map.items()[i];
        if (it.rect().intersects(w.file.home.rect)) continue; // the game's home stands there
        const int lr = lw->data.regionOfWorld(map.regionAt({it.x, it.y}));
        if (lr >= 0) lw->regionItems[static_cast<std::size_t>(lr)].emplace_back(it.info, i);
    }
    for (auto& v : lw->regionItems) std::ranges::sort(v);
    lw->buildMs =
        std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - t0).count();
    return lw;
}

std::size_t LifeWorld::memoryBytes() const {
    std::size_t n = data.memoryBytes() + slotGroup.capacity() * 4 + groupCap.capacity() +
                    groupSpotsAt.capacity() * 4 + groupSlots.capacity() * 4;
    for (const RegionPaths& p : paths) n += p.memoryBytes();
    for (const auto& c : chunkDistricts) n += c.capacity() * sizeof(ChunkDistrict);
    for (const auto& v : regionItems) n += v.capacity() * 8;
    return n;
}

// -- construction and the camera -----------------------------------------------------------------

CityLife::CityLife(LifeWorld& w, std::uint64_t seed)
    : w_(&w), map_(&w.map()), seed_(seed), chains_(w.data, w.map(), w.paths, w.pathsOf) {
    pool_.resize(tl::kPool);
    desc_.resize(tl::kPool);
    tracks_.resize(tl::kPool);
    chunkNext_.assign(tl::kPool, -1);
    chunkOf_.assign(tl::kPool, -1);
    free_.reserve(tl::kPool);
    for (int i = static_cast<int>(tl::kPool) - 1; i >= 0; --i) free_.push_back(i);
    const auto chunks = static_cast<std::size_t>(map_->chunksX() * map_->chunksY());
    chunkHead_.assign(chunks, -1);
    chunkActive_.assign(chunks, 0);
    chunkSeen_.assign(chunks, -1e9);
    keys_ = std::make_unique<KeyIndex>(std::bit_ceil(tl::kPool * 4));
    desires_.reserve(4096);
    queue_.reserve(4096);
    activeChunks_.reserve(256);
    groupCount_.assign(w.groupCap.size(), 0);
    spotUse_.assign(w.slotGroup.size(), 0);
    // Walks and what each becomes standing still: a walk with goods stands with them.
    const auto& names = w.data.animNames;
    const auto named = [&](std::string_view n) {
        const auto it = std::ranges::find(names, n);
        return it == names.end() ? -1 : static_cast<int>(it - names.begin());
    };
    idleOf_.assign(names.size(), -1);
    for (const char* walk : {"move", "haul", "run", "march", "row"})
        if (const int k = named(walk); k >= 0) idleOf_[static_cast<std::size_t>(k)] = kAnimIdle;
    carryWalk_ = named("carry");
    if (const int k = named("carry"); k >= 0) {
        const int idle = named("carry_idle");
        idleOf_[static_cast<std::size_t>(k)] =
            static_cast<std::int16_t>(idle >= 0 ? idle : kAnimIdle);
    }
    itemState_.assign(map_->items().size(), 0);
    itemStateUntil_.assign(map_->items().size(), 0);
    running_.reserve(tl::kMaxRunningEvents);
    trails_.resize(static_cast<std::size_t>(tl::kMaxRunningEvents) * tl::kEventTrail);
    trailCum_.resize(trails_.size());
    trailStops_.resize(static_cast<std::size_t>(tl::kMaxRunningEvents));
    carrierPaths_.resize(chains_.size() * 16);
    carrierCum_.resize(chains_.size() * 16);
    plans_.resize(w.data.regions.size());
    planNext_.assign(w.data.regions.size(), 0);
    reactiveCool_.assign(w.data.regions.size(), -1e9);
    sounds_.reserve(256);
    counts_.reserve(256);
    // Tokens: each kind's line once (a lane, or the road between two nodes rasterised as courses).
    const world::RoadGraph& roads = w.world->roads;
    std::vector<std::uint32_t> path;
    world::PathScratch scratch;
    std::vector<TilePos> poly;
    std::vector<Tile16> tiles;
    for (const Token& t : w.data.tokens) {
        TokenState ts;
        if (!t.lane.empty()) {
            const auto lane = std::ranges::find(roads.lanes(), t.lane, &world::RoadLane::id);
            if (lane != roads.lanes().end())
                for (const TilePos p : lane->points) ts.line.push_back(centre(p));
        } else {
            const int a = roads.findNode(t.from);
            const int b = roads.findNode(t.to);
            if (a >= 0 && b >= 0 && roads.shortestPath(a, b, scratch, path)) {
                roads.polyline(path, poly);
                pathTiles(poly, map_->height(), tiles);
                for (const Tile16 p : tiles) ts.line.push_back(centre(p.pos()));
            }
        }
        if (ts.line.size() >= 2) {
            ts.cum.push_back(0);
            for (std::size_t i = 1; i < ts.line.size(); ++i)
                ts.cum.push_back(ts.cum.back() + std::sqrt(dist2(ts.line[i - 1], ts.line[i])));
            ts.length = ts.cum.back();
            const KindDef& k = w.data.kinds[static_cast<std::size_t>(t.kind)];
            const float speed =
                !t.lane.empty() ? tl::kShipSpeed : (k.cart ? tl::kCartSpeed : tl::kWalkSpeed);
            // A fishing boat works its ground at the lane's far end; a ship stays in port.
            ts.fishing = !t.lane.empty() && k.id.find("fishing") != std::string::npos;
            ts.farStay = ts.fishing ? tl::kFishingStay : tl::kPortStay;
            ts.period = 2.0f * ts.length / speed + tl::kPortStay + ts.farStay;
            ts.ok = ts.length > 1.0f;
            // Its rest stops as lengths along the line: a lane's ports by their points, a
            // route's nodes by the nearest point of the line.
            const auto lane = std::ranges::find(roads.lanes(), t.lane, &world::RoadLane::id);
            for (const std::string& r : t.rest) {
                std::size_t at = 0;
                if (lane != roads.lanes().end()) {
                    const auto port = std::ranges::find(lane->ports, r, &world::LanePort::id);
                    at = static_cast<std::size_t>(port->at);
                } else {
                    const Vec2 n =
                        centre(roads.nodes()[static_cast<std::size_t>(roads.findNode(r))].at);
                    float best = 1e30f;
                    for (std::size_t i = 0; i < ts.line.size(); ++i)
                        if (const float d = dist2(ts.line[i], n); d < best) {
                            best = d;
                            at = i;
                        }
                }
                ts.rest.push_back(ts.cum[std::min(at, ts.cum.size() - 1)]);
            }
            std::ranges::sort(ts.rest);
        }
        tokenPaths_.push_back(std::move(ts));
        for (int k = 0; k < t.count; ++k) tokenLast_.push_back({-1.0, 0.0});
    }
}

CityLife::~CityLife() = default;

void CityLife::setFocus(TilePos c, int halfW, int halfH) {
    setView({c.x - halfW, c.y - halfH, c.x + halfW, c.y + halfH});
}

void CityLife::setView(TileRect view) {
    view_ = view;
    const int m = tl::kLiveMargin;
    const TileRect a =
        view.empty()
            ? TileRect{}
            : TileRect{view.x0 - m, view.y0 - m, view.x1 + m, view.y1 + m}.clipped(map_->bounds());
    if (a.x0 == active_.x0 && a.y0 == active_.y0 && a.x1 == active_.x1 && a.y1 == active_.y1)
        return;
    // Who should be live is decided by chunk: an area that only slid within the chunks it
    // already touched changes nothing for the populations, so it is looked at again soon
    // (tokens and chains at its edge), not this very step. A pan costs a few reconciliations
    // a second instead of sixty.
    const auto chunks = [](const TileRect& r) {
        return r.empty() ? TileRect{}
                         : TileRect{r.x0 >> kChunkShift, r.y0 >> kChunkShift,
                                    (r.x1 - 1) >> kChunkShift, (r.y1 - 1) >> kChunkShift};
    };
    const TileRect before = chunks(active_);
    const TileRect now = chunks(a);
    const bool same = !a.empty() && !active_.empty() && before.x0 == now.x0 &&
                      before.y0 == now.y0 && before.x1 == now.x1 && before.y1 == now.y1;
    active_ = a;
    if (same)
        moved_ = true;
    else
        dirty_ = true;
}

bool CityLife::inView(Vec2 p) const {
    return p.x >= static_cast<float>(view_.x0) - 1 && p.y >= static_cast<float>(view_.y0) - 1 &&
           p.x < static_cast<float>(view_.x1) + 1 && p.y < static_cast<float>(view_.y1) + 1;
}

// -- the calendar --------------------------------------------------------------------------------

int CityLife::seasonFor(int day, int season) const {
    // No season given (-1: the regions' own pins are gone): the world calendar's for the day.
    if (season >= 0) return season;
    const int n = std::max(1, static_cast<int>(w_->data.seasons.size()));
    return (day / std::max(1, w_->data.seasonDays)) % n;
}

int CityLife::monthFor(int day, int season) const {
    // The calendar's one rule (core calendarDay): day n's own month while the seasons follow the
    // days; with a season kept, the month of that season on the same day of it.
    const Catalog& cat = map_->content().home();
    const int m =
        calendarDay(day, season, cat.seasonDays, static_cast<int>(w_->data.months.size())).month;
    return m >= 0 ? m : w_->data.monthOf(day);
}

bool CityLife::festivalOn(int region, int festival, int day, int season) const {
    if (festival < 0) return false;
    season = seasonFor(day, season);
    const Festival& f = w_->data.regions[static_cast<std::size_t>(region)]
                            .festivals[static_cast<std::size_t>(festival)];
    if (f.months != 0) return monthIn(f.months, monthFor(day, season));
    if (f.seasons != 0 && (f.seasons & (1u << season)) == 0) return false;
    const int seasonDay = day % std::max(1, w_->data.seasonDays);
    return f.day == 0 || f.day == seasonDay + 1;
}

bool CityLife::festivalToday(int region, int festival) const {
    return festivalOn(region, festival, clock_.day, clock_.season);
}

// citylife.filters_pass, with the weather the clock says.
bool CityLife::filterPasses(const LifeRegion& r, const Filter& f) const {
    const int region = static_cast<int>(&r - w_->data.regions.data());
    if (f.hours && !inHours(f.from, f.to, hour_)) return false;
    if (f.every > 0 && clock_.day % f.every != f.offset) return false;
    if (f.seasons != 0 && (f.seasons & (1u << clock_.season)) == 0) return false;
    if (!dayPasses(f, clock_.day, clock_.season)) return false;
    if (f.festival >= 0 && !festivalToday(region, f.festival)) return false;
    if (f.notFestival >= 0 && festivalToday(region, f.notFestival)) return false;
    if (f.weather == 1 && !clock_.rain) return false;
    if (f.weather == 0 && clock_.rain) return false;
    return true;
}

CityLife::TokenPhase CityLife::tokenPhase(std::size_t t, int k) const {
    const Token& tk = w_->data.tokens[t];
    const TokenState& ts = tokenPaths_[t];
    // Its clock runs only in its hours: the seconds under way since day 0 06:00, so it stops
    // where its hours end and goes on from there when they begin again.
    double active = now_;
    bool underway = tokenOn(tk);
    if (tk.hours) {
        const double a = std::fmod((tk.hourFrom - 6.0) * 30.0 + 7200.0, kDaySeconds);
        double len = std::fmod((tk.hourTo - tk.hourFrom) * 30.0 + 7200.0, kDaySeconds);
        if (len <= 0) len = kDaySeconds;
        const double u = now_ - a;
        const double into = u - std::floor(u / kDaySeconds) * kDaySeconds;
        active = std::floor(u / kDaySeconds) * len + std::min(into, len);
        underway = underway && into < len;
    }
    // by_month: the month's share of its instances is under way, a fresh draw each day.
    if (underway && !tk.share.empty()) {
        const int month = monthFor(clock_.day, clock_.season);
        const float share = static_cast<std::size_t>(month) < tk.share.size()
                                ? tk.share[static_cast<std::size_t>(month)]
                                : 1.0f;
        underway = unit(hashOf({tk.seed, static_cast<std::uint64_t>(k),
                                static_cast<std::uint64_t>(clock_.day)})) < share;
    }
    const double offset = static_cast<std::size_t>(k) < tk.offsets.size()
                              ? static_cast<double>(tk.offsets[static_cast<std::size_t>(k)])
                              : static_cast<double>(k) / tk.count;
    const double period = ts.period;
    return {std::fmod(active + offset * period + 1e7 * period, period), underway};
}

bool CityLife::tokenOn(const Token& tk) const {
    return filterPasses(w_->data.regions[static_cast<std::size_t>(tk.region)], tk.when);
}

bool CityLife::dayPasses(const Filter& f, int day, int season) const {
    if (!monthIn(f.months, monthFor(day, season))) return false;
    return f.seasonDay == 0 || day % std::max(1, w_->data.seasonDays) + 1 == f.seasonDay;
}

int CityLife::blockAt(int region, const Role& role) const {
    const LifeRegion& r = w_->data.regions[static_cast<std::size_t>(region)];
    for (std::size_t b = 0; b < role.schedule.size(); ++b)
        if (filterPasses(r, role.schedule[b].when)) return static_cast<int>(b);
    return -1;
}

// -- the step ------------------------------------------------------------------------------------

void CityLife::advanceAbstract(const LifeClock& clock) {
    const bool rainChanged = clock.rain != clock_.rain;
    clock_ = clock;
    clock_.season = seasonFor(clock.day, clock.season);
    now_ = clock.seconds();
    hour_ = static_cast<float>(clock.hour());
    sounds_.clear();
    stats_.spawnedThisStep = 0;
    builds_ = tl::kTableBuildsPerStep;
    // A jump of the clock (a script, the time or day set by hand) rebuilds the events from the
    // plan; a new day continues them, and so does the clock gliding to a pin (L-002: its steps
    // are larger than any step of a running clock, so they are told apart by the jump count).
    const bool first = lastNow_ <= -1e17;
    const bool jumped =
        first || (clock.epoch >= 0 ? clock.epoch != lastEpoch_ : std::abs(now_ - lastNow_) > 2.0);
    lastNow_ = now_;
    lastEpoch_ = clock.epoch;
    if (jumped || clock.day != day_) {
        day_ = clock.day;
        if (jumped) {
            std::ranges::fill(chunkSeen_, -1e18); // lingering is for a camera moving, not a jump
            for (std::size_t k = 0; k < pool_.size(); ++k)
                if ((pool_[k].flags & live_flag::kAlive) != 0 && pool_[k].source == Source::Cast)
                    release(static_cast<int>(k));
            running_.clear();
            for (auto& t : tokenLast_) t = {-1.0, 0.0};
        }
        for (std::size_t r = 0; r < plans_.size(); ++r) planDay(static_cast<int>(r), day_, !jumped);
    }
    // Chains never run backwards: gliding back to a pin, they wait for the clock to catch up.
    if (jumped || static_cast<long>(now_) >= chains_.tick())
        chains_.advanceTo(now_, clock_.season, monthFor(clock_.day, clock_.season),
                          [this](int region, int event) { return eventRunning(region, event); });
    updateEvents();
    updateTokens();
    if (rainChanged) {
        // Weather triggers (`rain`, `rain_stop`) in every region with life.
        for (std::size_t r = 0; r < w_->data.regions.size(); ++r) {
            const LifeRegion& reg = w_->data.regions[r];
            for (std::size_t e = 0; e < reg.events.size(); ++e) {
                const Event& ev = reg.events[e];
                if (ev.trigger != Trigger::Weather) continue;
                const bool fires = (ev.weather == "rain" && clock.rain) ||
                                   (ev.weather == "rain_stop" && !clock.rain);
                if (!fires) continue;
                Filter f = ev.when;
                if (!filterPasses(reg, f)) continue;
                if (unit(hashOf({seed_, 0x57, r, e, static_cast<std::uint64_t>(day_)})) >=
                    ev.chance)
                    continue;
                const double len =
                    ev.dur0 + (ev.dur1 - ev.dur0) * unit(hashOf({seed_, r, e, 0x44}));
                startEvent(static_cast<int>(r), static_cast<int>(e), now_, now_ + len, 0);
            }
        }
    }
    const int hi = clock.day * 48 + static_cast<int>(hour_ * 2.0f); // every half game hour
    if (hi != hourIndex_ || rainChanged) {
        hourIndex_ = hi;
        dirty_ = true;
    }
}

void CityLife::update(const LifeClock& clock, float dt) {
    advanceAbstract(clock);
    if (dirty_ || now_ - lastReconcile_ > (moved_ ? tl::kReconcileMoving : 2.0)) reconcile();
    spawnQueued(false);
    // Everyone's last position, for drawing between steps.
    for (LiveActor& a : pool_)
        if ((a.flags & live_flag::kAlive) != 0) {
            a.prev = a.pos;
            a.prevZ = a.z;
            a.prevStride = a.stride;
        }
    // Decisions in round-robin buckets; motion, puppets and fades every step so drawing is smooth.
    const auto bucket = static_cast<std::size_t>(frame_ % static_cast<std::uint32_t>(tl::kBuckets));
    const float slice = dt * static_cast<float>(tl::kBuckets);
    for (std::size_t i = 0; i < pool_.size(); ++i) {
        LiveActor& a = pool_[i];
        if ((a.flags & live_flag::kAlive) == 0) continue;
        const int k = static_cast<int>(i);
        if (a.state == ActState::Puppet) {
            puppet(k);
        } else {
            motion(k, dt);
            if (i % static_cast<std::size_t>(tl::kBuckets) == bucket) think(k, slice);
        }
        if ((pool_[i].flags & live_flag::kAlive) != 0) afterStep(k, dt);
    }
    ++frame_;
    if (frame_ % 30 == 0) {
        countDistricts();
        countBodies();
    }
    stats_.running = static_cast<int>(running_.size());
    stats_.chains = static_cast<int>(chains_.size());
}

void CityLife::settle(const LifeClock& clock) {
    // Everything placed where the clock has it, no step of anyone's day taken.
    advanceAbstract(clock);
    reconcile();
    // A jump is not watched: whoever was leaving is gone, and no longer holds the cap against
    // those arriving (a full area left behind would otherwise keep the new one empty).
    int live = 0;
    for (std::size_t k = 0; k < pool_.size(); ++k) {
        if ((pool_[k].flags & live_flag::kAlive) != 0 && pool_[k].state == ActState::Leave)
            release(static_cast<int>(k));
        live += (pool_[k].flags & live_flag::kAlive) != 0 ? 1 : 0;
    }
    stats_.live = live;
    builds_ = 1 << 20;
    spawnQueued(true);
    builds_ = tl::kTableBuildsPerStep;
    for (LiveActor& a : pool_)
        if ((a.flags & live_flag::kAlive) != 0 && (a.flags & live_flag::kFadeIn) != 0) {
            a.alpha = 1;
            a.flags = static_cast<std::uint8_t>(a.flags & ~live_flag::kFadeIn);
        }
    countDistricts();
}

// -- population: who should be live --------------------------------------------------------------

void CityLife::reconcile() {
    dirty_ = false;
    moved_ = false;
    lastReconcile_ = now_;
    // Active chunks (the area grown by the margin), and those left less than two seconds ago.
    activeChunks_.clear();
    const auto cx = static_cast<std::size_t>(map_->chunksX());
    for (std::size_t c = 0; c < chunkActive_.size(); ++c) {
        const int x0 = static_cast<int>(c % cx) * kChunk;
        const int y0 = static_cast<int>(c / cx) * kChunk;
        bool in = !active_.empty() && active_.intersects({x0, y0, x0 + kChunk, y0 + kChunk});
        // A chunk stays live two seconds after the area left it, so camera jitter does not churn.
        if (in)
            chunkSeen_[c] = now_;
        else if (now_ >= chunkSeen_[c] && now_ - chunkSeen_[c] < tl::kChunkLinger)
            in = true;
        chunkActive_[c] = in ? 1 : 0;
        if (in) activeChunks_.push_back(static_cast<std::uint32_t>(c));
    }
    desires_.clear();
    counts_.clear();
    // Population scale: what the cap allows, given the rest (chains, tokens, casts, figures).
    scale_ = 1;
    for (const std::uint32_t c : activeChunks_) desireChunk(c);
    std::size_t population = 0;
    float expected = 0;
    for (const Desire& d : desires_)
        if (d.source == Source::Population) ++population;
    for (const DistrictCount& dc : counts_) expected += dc.expected;
    // Figures with a day: their home chunk active.
    for (std::size_t r = 0; r < w_->data.regions.size(); ++r) {
        const LifeRegion& reg = w_->data.regions[r];
        const int p = w_->pathsOf[r];
        for (std::size_t f = 0; f < reg.figures.size(); ++f) {
            const Figure& fg = reg.figures[f];
            if (fg.role < 0 || p < 0) continue;
            const Role& role = reg.roles[static_cast<std::size_t>(fg.role)];
            if (blockAt(static_cast<int>(r), role) < 0) continue;
            // Home: the district named, else the first node its day goes to.
            TilePos home{-1, -1};
            if (fg.district >= 0) {
                const District* dd = nullptr;
                for (const District& d : reg.districts)
                    if (d.map == fg.district) dd = &d;
                if (dd != nullptr && !dd->chunks.empty()) {
                    const auto best = std::ranges::max_element(
                        dd->chunks, {}, [](const auto& c) { return c.second; });
                    home = {static_cast<int>(best->first % cx) * kChunk + kChunk / 2,
                            static_cast<int>(best->first / cx) * kChunk + kChunk / 2};
                }
            } else {
                for (const auto& [name, b] : role.routines) {
                    const Block& blk = w_->data.blocks[static_cast<std::size_t>(b)];
                    for (std::uint32_t s = blk.first; s < blk.first + blk.count && home.x < 0;
                         ++s) {
                        const Step& st = w_->data.steps[s];
                        if (st.target.kind == TargetKind::Node)
                            home = w_->paths[static_cast<std::size_t>(p)].nodeAt(st.target.node);
                    }
                    if (home.x >= 0) break;
                }
            }
            if (home.x < 0 || !map_->inBounds(home)) continue;
            const auto chunk = static_cast<std::uint32_t>(
                (home.y >> kChunkShift) * map_->chunksX() + (home.x >> kChunkShift));
            if (!chunkActive_[chunk]) continue;
            Desire d;
            d.key = hashOf({seed_, 0xF16, r, f});
            d.source = Source::Figure;
            d.region = static_cast<std::int16_t>(r);
            d.role = static_cast<std::int16_t>(fg.role);
            d.kind = static_cast<std::int16_t>(fg.kind);
            d.chunk = chunk;
            desires_.push_back(d);
        }
    }
    // Chain workers whose place is in the area: at work in the chain's hours, carriers on the way.
    for (std::size_t c = 0; c < chains_.size(); ++c) {
        const ChainRun& run = chains_.run(c);
        if (!run.ok()) continue;
        const int region = chains_.regionOf(c);
        const LifeRegion& reg = w_->data.regions[static_cast<std::size_t>(region)];
        // As the simulation decides it (season, month, event), so nobody works a closed chain.
        const bool on = chains_.working(
            c, static_cast<long>(now_), clock_.season, monthFor(clock_.day, clock_.season),
            [this](int rg, int event) { return eventRunning(rg, event); });
        for (std::size_t k = 0; k < run.workers().size(); ++k) {
            const ChainStage& s = run.chain().stages[static_cast<std::size_t>(run.stageOf(k))];
            const ChainWorker& wk = run.workers()[k];
            if (!on && wk.phase != WorkerPhase::Out && wk.phase != WorkerPhase::Back) continue;
            const TilePos at = run.place(s.kind == ChainStage::Kind::Carry ? s.from : s.slot).tile;
            const TilePos to = s.kind == ChainStage::Kind::Carry ? run.place(s.to).tile : at;
            const bool here = active_.contains(at) || active_.contains(to);
            if (!here || s.role < 0) continue;
            Desire d;
            d.key = hashOf({seed_, 0xC4A1, c, k});
            d.source = Source::Chain;
            d.region = static_cast<std::int16_t>(region);
            d.role = static_cast<std::int16_t>(s.role);
            d.kind = static_cast<std::int16_t>(reg.roles[static_cast<std::size_t>(s.role)].kind);
            d.a = static_cast<std::int32_t>(c);
            d.b = static_cast<std::int32_t>(k);
            desires_.push_back(d);
        }
    }
    // Tokens in the area, with their groups.
    {
        std::size_t inst = 0;
        for (std::size_t t = 0; t < w_->data.tokens.size(); ++t) {
            const Token& tk = w_->data.tokens[t];
            if (!tokenOn(tk)) {
                inst += static_cast<std::size_t>(tk.count);
                continue;
            }
            int members = 1;
            if (tk.group >= 0) {
                const Group& g = w_->data.regions[static_cast<std::size_t>(tk.region)]
                                     .groups[static_cast<std::size_t>(tk.group)];
                for (const GroupMember& m : g.members) members += m.count;
            }
            for (int k = 0; k < tk.count; ++k, ++inst)
                for (int m = 0; m < members && m < 64; ++m) {
                    TokenAt at;
                    if (!tokenAt(t, k, m, at) ||
                        !active_.contains(
                            TilePos{static_cast<int>(at.pos.x), static_cast<int>(at.pos.y)}))
                        continue;
                    Desire d;
                    d.key = hashOf({seed_, 0x70C, t, static_cast<std::uint64_t>(k),
                                    static_cast<std::uint64_t>(m)});
                    d.source = Source::Token;
                    d.region = static_cast<std::int16_t>(tk.region);
                    d.kind = static_cast<std::int16_t>(m == 0 || tk.group < 0 ? tk.kind
                                                                              : memberKind(tk, m));
                    d.a = static_cast<std::int32_t>(t);
                    d.b = static_cast<std::int32_t>(inst * 64 + static_cast<std::size_t>(m));
                    d.chunk = static_cast<std::uint32_t>(
                        (static_cast<int>(at.pos.y) >> kChunkShift) * map_->chunksX() +
                        (static_cast<int>(at.pos.x) >> kChunkShift));
                    desires_.push_back(d);
                }
        }
    }
    // Event casts whose route or place touches the area.
    for (std::size_t e = 0; e < running_.size(); ++e) {
        RunningEvent& re = running_[e];
        if (!re.active) continue;
        const Event& ev = w_->data.regions[static_cast<std::size_t>(re.region)]
                              .events[static_cast<std::size_t>(re.event)];
        int member = 0;
        const auto add = [&](int kind, int count) {
            for (int j = 0; j < count; ++j, ++member) {
                Desire d;
                d.key = hashOf({seed_, 0xE7, static_cast<std::uint64_t>(re.region),
                                static_cast<std::uint64_t>(re.event),
                                static_cast<std::uint64_t>(re.start * 8.0),
                                static_cast<std::uint64_t>(member)});
                d.source = Source::Cast;
                d.region = static_cast<std::int16_t>(re.region);
                d.kind = static_cast<std::int16_t>(kind);
                d.a = static_cast<std::int32_t>(e);
                d.b = member;
                if (kind >= 0) desires_.push_back(d);
            }
        };
        const LifeRegion& reg = w_->data.regions[static_cast<std::size_t>(re.region)];
        for (const CastEntry& c : ev.cast) {
            if (c.group >= 0) {
                const Group& g = reg.groups[static_cast<std::size_t>(c.group)];
                add(g.leader, 1);
                for (const GroupMember& m : g.members) add(m.kind, m.count);
            } else if (c.role >= 0) {
                add(reg.roles[static_cast<std::size_t>(c.role)].kind, c.count);
            } else if (c.kind >= 0) {
                add(c.kind, c.count);
            } else if (!c.rotate.empty()) {
                for (int j = 0; j < c.count; ++j) {
                    const auto gi = static_cast<std::size_t>(
                        (static_cast<std::size_t>(clock_.day) * static_cast<std::size_t>(c.count) +
                         static_cast<std::size_t>(j)) %
                        c.rotate.size());
                    const Group& g = reg.groups[static_cast<std::size_t>(c.rotate[gi])];
                    add(g.leader, 1);
                    for (const GroupMember& m : g.members) add(m.kind, m.count);
                }
            }
        }
    }
    // The cap: populations scale down proportionally when everything would not fit.
    const std::size_t others = desires_.size() - population;
    const float room = static_cast<float>(liveCap_) - static_cast<float>(others);
    float s = 1;
    if (forcedScale_ > 0)
        s = forcedScale_;
    else if (expected > room && expected > 0)
        s = std::max(0.0f, room / expected);
    if (std::abs(s - 1.0f) > 1e-4f) {
        // Again, at the scale (identities keep their numbers, so most stay).
        std::vector<Desire> rest(desires_.begin() + static_cast<std::ptrdiff_t>(population),
                                 desires_.end());
        desires_.clear();
        counts_.clear();
        scale_ = s;
        for (const std::uint32_t c : activeChunks_) desireChunk(c);
        desires_.insert(desires_.end(), rest.begin(), rest.end());
    }
    stats_.scale = scale_;
    // Rounding by hash can leave a few over the cap: the farthest people from the view wait.
    if (desires_.size() > static_cast<std::size_t>(liveCap_)) {
        const Vec2 c{static_cast<float>(view_.x0 + view_.x1) * 0.5f,
                     static_cast<float>(view_.y0 + view_.y1) * 0.5f};
        const auto cxs = static_cast<std::uint32_t>(map_->chunksX());
        for (Desire& d : desires_)
            d.order = d.source == Source::Population
                          ? dist2({static_cast<float>(static_cast<int>(d.chunk % cxs) * kChunk +
                                                      kHalfChunk),
                                   static_cast<float>(static_cast<int>(d.chunk / cxs) * kChunk +
                                                      kHalfChunk)},
                                  c)
                          : -1.0f; // the rest first: chains, tokens, casts, figures
        std::ranges::stable_sort(desires_, {}, &Desire::order);
        desires_.resize(static_cast<std::size_t>(liveCap_));
    }
    // Compare with who is live.
    for (LiveActor& a : pool_)
        if ((a.flags & live_flag::kAlive) != 0 && a.state != ActState::Leave)
            a.flags |= live_flag::kUnwanted;
    queue_.clear();
    queueHead_ = 0;
    const Vec2 vc{static_cast<float>(view_.x0 + view_.x1) * 0.5f,
                  static_cast<float>(view_.y0 + view_.y1) * 0.5f};
    for (Desire& d : desires_) {
        const int i = keys_->find(d.key);
        if (i >= 0) {
            LiveActor& a = pool_[static_cast<std::size_t>(i)];
            a.flags = static_cast<std::uint8_t>(a.flags & ~live_flag::kUnwanted);
            if (a.state == ActState::Leave) {
                // Wanted again before it was gone (the midday rest is over): it turns back.
                a.flags = static_cast<std::uint8_t>((a.flags & ~live_flag::kFadeOut) |
                                                    live_flag::kFadeIn);
                a.route = Route{};
                tracks_[i].n = 0;
                if (a.source == Source::Population || a.source == Source::Figure) {
                    chooseRoutine(static_cast<int>(i));
                } else {
                    a.state = ActState::Puppet;
                }
            }
            continue;
        }
        const auto ccx = static_cast<float>(static_cast<int>(d.chunk % cx) * kChunk + kHalfChunk);
        const auto ccy = static_cast<float>(static_cast<int>(d.chunk / cx) * kChunk + kHalfChunk);
        d.order = dist2({ccx, ccy}, vc);
        queue_.push_back(d);
    }
    std::ranges::stable_sort(queue_, {}, &Desire::order);
    for (std::size_t i = 0; i < pool_.size(); ++i) {
        LiveActor& a = pool_[i];
        if ((a.flags & live_flag::kAlive) != 0 && (a.flags & live_flag::kUnwanted) != 0) {
            // Puppets of tokens and casts leave by their own maths (out of the area, event over).
            if (a.source == Source::Token) continue;
            beginLeave(static_cast<int>(i));
        }
    }
    stats_.queued = static_cast<int>(queue_.size());
}

void CityLife::desireChunk(std::uint32_t chunk) {
    const auto& data = w_->data;
    const int h = static_cast<int>(hour_) % 24;
    for (const LifeWorld::ChunkDistrict& cd : w_->chunkDistricts[chunk]) {
        const LifeRegion& reg = data.regions[cd.region];
        const District& dist = reg.districts[cd.district];
        DistrictCount* count = nullptr;
        for (DistrictCount& dc : counts_)
            if (dc.region == cd.region && dc.district == cd.district) count = &dc;
        if (count == nullptr) {
            counts_.push_back({cd.region, cd.district, 0, 0, 0, 0});
            count = &counts_.back();
        }
        for (std::size_t p = 0; p < dist.populations.size(); ++p) {
            const Population& pop = dist.populations[p];
            if (!filterPasses(reg, pop.when)) continue;
            const float dens = pop.density < 0
                                   ? 1.0f
                                   : reg.densities[static_cast<std::size_t>(pop.density)]
                                                  [static_cast<std::size_t>(h)];
            const Role& role = reg.roles[static_cast<std::size_t>(pop.role)];
            const bool out = blockAt(cd.region, role) >= 0; // no block: indoors or away, not drawn
            const auto emit = [&](float n, int maxK, std::uint64_t place, int instance) {
                count->formula += n;
                if (!out) return;
                count->expected += n;
                const float ns = n * scale_;
                const auto whole = static_cast<int>(ns);
                const float frac = ns - static_cast<float>(whole);
                for (int k = 0; k < maxK; ++k) {
                    const std::uint64_t key = hashOf({seed_, 0x9097, cd.region, cd.district, p,
                                                      place, static_cast<std::uint64_t>(k)});
                    const bool exists =
                        k < whole ||
                        (k == whole && unit(hashOf({key, static_cast<std::uint64_t>(hourIndex_),
                                                    0xF4AC})) < frac);
                    if (!exists) continue;
                    Desire d;
                    d.key = key;
                    d.source = Source::Population;
                    d.region = static_cast<std::int16_t>(cd.region);
                    d.role = static_cast<std::int16_t>(pop.role);
                    d.district = static_cast<std::int16_t>(cd.district);
                    d.kind = static_cast<std::int16_t>(role.kind);
                    d.a = instance;
                    d.chunk = chunk;
                    desires_.push_back(d);
                }
            };
            if (pop.perItem >= 0) {
                for (const std::uint32_t inst : dist.instances[p]) {
                    const Placed& it = map_->items()[inst];
                    const auto ic = static_cast<std::uint32_t>(
                        (it.y >> kChunkShift) * map_->chunksX() + (it.x >> kChunkShift));
                    if (ic != chunk) continue;
                    emit(pop.count * dens, static_cast<int>(std::ceil(pop.count)) + 1,
                         0x10000000ULL + inst, static_cast<int>(inst));
                }
            } else {
                const float n = dens * pop.maxPerChunk * static_cast<float>(cd.tiles) /
                                static_cast<float>(kChunkArea);
                const float most =
                    pop.maxPerChunk * static_cast<float>(cd.tiles) / static_cast<float>(kChunkArea);
                emit(n, static_cast<int>(std::ceil(most)) + 1, chunk, -1);
            }
        }
    }
}

float CityLife::expectedFor(TileRect view, const LifeClock& c) {
    const LifeClock keepClock = clock_;
    const float keepHour = hour_;
    const int keepIndex = hourIndex_;
    const float keepScale = scale_;
    std::swap(desires_, scratchDesires_);
    std::swap(counts_, scratchCounts_);
    desires_.clear();
    counts_.clear();
    clock_ = c;
    clock_.season = seasonFor(c.day, c.season);
    hour_ = static_cast<float>(c.hour());
    hourIndex_ = c.day * 48 + static_cast<int>(hour_ * 2.0f);
    scale_ = 1;
    const int m = tl::kLiveMargin;
    const TileRect a =
        TileRect{view.x0 - m, view.y0 - m, view.x1 + m, view.y1 + m}.clipped(map_->bounds());
    const auto cx = static_cast<std::uint32_t>(map_->chunksX());
    for (std::uint32_t chunk = 0; chunk < chunkActive_.size(); ++chunk) {
        const int x0 = static_cast<int>(chunk % cx) * kChunk;
        const int y0 = static_cast<int>(chunk / cx) * kChunk;
        if (a.intersects({x0, y0, x0 + kChunk, y0 + kChunk})) desireChunk(chunk);
    }
    float total = 0;
    for (const DistrictCount& d : counts_) total += d.expected;
    clock_ = keepClock;
    hour_ = keepHour;
    hourIndex_ = keepIndex;
    scale_ = keepScale;
    std::swap(desires_, scratchDesires_);
    std::swap(counts_, scratchCounts_);
    return total;
}

// -- the pool ------------------------------------------------------------------------------------

int CityLife::allocate() {
    if (free_.empty()) return -1;
    const int i = free_.back();
    free_.pop_back();
    return i;
}

void CityLife::release(int i) {
    LiveActor& a = pool_[static_cast<std::size_t>(i)];
    unreserve(i);
    unlink(i);
    keys_->erase(a.key);
    const std::uint16_t gen = static_cast<std::uint16_t>(a.gen + 1);
    a = LiveActor{};
    a.gen = gen;
    free_.push_back(i);
}

bool CityLife::alive(Handle h) const {
    if (h.index >= pool_.size()) return false;
    const LiveActor& a = pool_[h.index];
    return (a.flags & live_flag::kAlive) != 0 && a.gen == h.gen;
}

void CityLife::link(int i) {
    LiveActor& a = pool_[static_cast<std::size_t>(i)];
    const TilePos t = a.tile.pos();
    if (!map_->inBounds(t)) return;
    const int c = (t.y >> kChunkShift) * map_->chunksX() + (t.x >> kChunkShift);
    if (chunkOf_[static_cast<std::size_t>(i)] == c) return;
    unlink(i);
    chunkOf_[static_cast<std::size_t>(i)] = c;
    chunkNext_[static_cast<std::size_t>(i)] = chunkHead_[static_cast<std::size_t>(c)];
    chunkHead_[static_cast<std::size_t>(c)] = i;
}

void CityLife::unlink(int i) {
    const int c = chunkOf_[static_cast<std::size_t>(i)];
    if (c < 0) return;
    int* p = &chunkHead_[static_cast<std::size_t>(c)];
    while (*p != -1 && *p != i) p = &chunkNext_[static_cast<std::size_t>(*p)];
    if (*p == i) *p = chunkNext_[static_cast<std::size_t>(i)];
    chunkOf_[static_cast<std::size_t>(i)] = -1;
    chunkNext_[static_cast<std::size_t>(i)] = -1;
}

void CityLife::spawnQueued(bool unbounded) {
    // A count per step, not a time budget, so a run is the same on any machine (the bench shows
    // what the count costs).
    int done = 0;
    while (queueHead_ < queue_.size()) {
        if (!unbounded && done >= tl::kSpawnsPerStep) break;
        if (stats_.live >= liveCap_ || free_.empty()) break;
        const Desire d = queue_[queueHead_++];
        if (keys_->find(d.key) >= 0) continue;
        const int i = allocate();
        materialise(i, d);
        if ((pool_[static_cast<std::size_t>(i)].flags & live_flag::kAlive) == 0) {
            free_.push_back(i); // nothing to show (a token far away, a place it cannot stand)
            continue;
        }
        ++done;
        ++stats_.live; // the cap is checked against everyone, those spawned this call too
    }
    stats_.spawnedThisStep = done;
    stats_.queued = static_cast<int>(queue_.size() - queueHead_);
    int live = 0;
    for (const LiveActor& a : pool_) live += (a.flags & live_flag::kAlive) != 0 ? 1 : 0;
    stats_.live = live;
}

// -- materialisation -----------------------------------------------------------------------------

void CityLife::materialise(int i, const Desire& d) {
    LiveActor& a = pool_[static_cast<std::size_t>(i)];
    const std::uint16_t gen = a.gen;
    a = LiveActor{};
    a.gen = gen;
    a.key = d.key;
    a.rng = d.key ^ seed_;
    a.source = d.source;
    a.region = static_cast<std::uint8_t>(d.region);
    a.role = d.role;
    a.district = d.district;
    a.home = d.source == Source::Population ? d.a : -1;
    a.a = d.a;
    a.b = d.b;
    const auto& data = w_->data;
    const LifeRegion& reg = data.regions[static_cast<std::size_t>(d.region)];
    a.kind = static_cast<std::uint16_t>(std::max<int>(0, d.kind));
    const KindDef& kind = data.kinds[a.kind];
    a.variant = static_cast<std::uint8_t>(next(a.rng) % static_cast<std::uint64_t>(kind.variants));
    a.speed = (kind.cart ? tl::kCartSpeed : tl::kWalkSpeed) * range(a, 0.9f, 1.1f);
    // Out of step with everyone else: its own animation pace and phase, its own side of the way.
    a.animTime = range(a, 0.0f, 4.0f);
    a.rate = range(a, tl::kRate0, tl::kRate1);
    a.lateral = range(a, -tl::kLateral, tl::kLateral);
    tracks_[static_cast<std::size_t>(i)].n = 0;
    if (d.role >= 0 && d.source != Source::Cast && d.source != Source::Token) {
        const Role& role = reg.roles[static_cast<std::size_t>(d.role)];
        if (role.speed > 0) a.speed = role.speed * range(a, 0.95f, 1.05f);
    }
    const int pi = w_->pathsOf[static_cast<std::size_t>(d.region)];
    if (d.source == Source::Chain || d.source == Source::Token || d.source == Source::Cast) {
        a.state = ActState::Puppet;
        a.flags = live_flag::kAlive;
        a.alpha = 1;
        materialising_ = true;
        puppet(i);
        materialising_ = false;
        if ((a.flags & live_flag::kAlive) == 0) return;
        a.prev = a.pos;
        a.prevZ = a.z;
        if (inView(a.pos) && d.source != Source::Token) {
            a.alpha = 0;
            a.flags |= live_flag::kFadeIn;
        }
        keys_->insert(a.key, i);
        link(i);
        return;
    }
    if (pi < 0) return;
    RegionPaths& paths = w_->paths[static_cast<std::size_t>(pi)];
    // Where its day starts: its own place (a per-item instance), else somewhere in its district
    // within its chunk that walkers can reach.
    TilePos start{-1, -1};
    if (a.home >= 0) {
        const Placed& it = map_->items()[static_cast<std::size_t>(a.home)];
        for (int y = it.y - 1; y <= it.y + it.h && start.x < 0; ++y)
            for (int x = it.x - 1; x <= it.x + it.w; ++x)
                if (map_->inBounds({x, y}) && paths.reachable({x, y}) && map_->walkable({x, y})) {
                    start = {x, y};
                    break;
                }
    }
    const auto cx = map_->chunksX();
    if (start.x < 0) {
        const int x0 = static_cast<int>(d.chunk % static_cast<std::uint32_t>(cx)) * kChunk;
        const int y0 = static_cast<int>(d.chunk / static_cast<std::uint32_t>(cx)) * kChunk;
        const int want =
            d.district >= 0 ? reg.districts[static_cast<std::size_t>(d.district)].map : -1;
        for (int tries = 0; tries < 48 && start.x < 0; ++tries) {
            const TilePos t{x0 + static_cast<int>(next(a.rng) % kChunk),
                            y0 + static_cast<int>(next(a.rng) % kChunk)};
            if (!map_->inBounds(t) || !paths.reachable(t) || !map_->walkable(t)) continue;
            if (want >= 0 && tries < 32 && map_->districtAt(t) != want) continue;
            start = t;
        }
    }
    if (start.x < 0) return; // no ground to stand on in this chunk
    a.tile = a.anchor = tile16(start);
    a.pos = a.prev = a.endPoint = centre(start);
    a.z = a.prevZ = static_cast<float>(map_->floorZ(start));
    a.flags = live_flag::kAlive;
    if (d.source == Source::Figure && !reg.figures.empty()) {
        for (const Figure& f : reg.figures)
            if (f.role == d.role && f.translucent) a.flags |= live_flag::kTranslucent;
    }
    a.alpha = 1;
    keys_->insert(a.key, i);
    link(i);
    chooseRoutine(i);
    if (a.depth == 0) return;
    // How far into its block it is now: the time since the block began, desynchronised by a
    // seeded minute so a role's people are not in step.
    const Role& role = reg.roles[static_cast<std::size_t>(a.role)];
    const Filter& f = role.schedule[a.sched].when;
    double elapsed =
        f.hours ? std::fmod(static_cast<double>(hour_ - f.from) + 24.0, 24.0) * kSecondsPerHour
                : static_cast<double>(hour_) * kSecondsPerHour;
    elapsed += static_cast<double>(range(a, 0.0f, 60.0f));
    runSteps(i, true, elapsed);
    a.prev = a.pos;
    a.prevZ = a.z;
    link(i);
    if (inView(a.pos) && a.state != ActState::Inside) {
        a.alpha = 0;
        a.flags |= live_flag::kFadeIn;
    }
}

void CityLife::beginLeave(int i) {
    LiveActor& a = pool_[static_cast<std::size_t>(i)];
    unreserve(i);
    a.flags = static_cast<std::uint8_t>(a.flags & ~live_flag::kUnwanted);
    if (!inView(a.pos) || a.state == ActState::Inside || a.alpha <= 0.0f) {
        release(i);
        return;
    }
    a.state = ActState::Leave;
    a.timer = tl::kLeaveTimeout;
    a.step = kNoStep;
    a.depth = 0;
    TilePos door;
    if (a.source != Source::Chain && a.source != Source::Cast &&
        nearestDoor(a.pos, tl::kDoorReach, door) >= 0 && planTo(i, door, centre(door), builds_))
        return;
    a.route = Route{};
    a.flags |= live_flag::kFadeOut;
}

// -- behaviour -----------------------------------------------------------------------------------

void CityLife::chooseRoutine(int i) {
    LiveActor& a = pool_[static_cast<std::size_t>(i)];
    a.depth = 0;
    a.step = kNoStep;
    if (a.role < 0) return;
    const LifeRegion& reg = w_->data.regions[a.region];
    const Role& role = reg.roles[static_cast<std::size_t>(a.role)];
    const int b = blockAt(a.region, role);
    a.sched = static_cast<std::uint8_t>(b < 0 ? 0xFF : b);
    if (b < 0) return;
    int routine = role.schedule[static_cast<std::size_t>(b)].routine;
    a.flags = static_cast<std::uint8_t>(a.flags & ~live_flag::kRain);
    if (clock_.rain && role.rainRoutine >= 0) {
        routine = role.rainRoutine;
        a.flags |= live_flag::kRain;
    }
    a.stack[0] = {static_cast<std::uint16_t>(routine), 0, 0};
    a.depth = 1;
    a.state = ActState::Idle;
    a.timer = 0;
}

bool CityLife::untilMet(const LiveActor& a) const {
    if (a.step == kNoStep) return false;
    const Step& s = w_->data.steps[a.step];
    if (s.until == Until::Clear) return !clock_.rain;
    if (s.until == Until::Rain) return clock_.rain;
    return false;
}

void CityLife::unreserve(int i) {
    LiveActor& a = pool_[static_cast<std::size_t>(i)];
    if (a.group >= 0 && groupCount_[static_cast<std::size_t>(a.group)] > 0)
        --groupCount_[static_cast<std::size_t>(a.group)];
    if (a.slot >= 0 && spotUse_[static_cast<std::size_t>(a.slot)] > 0)
        --spotUse_[static_cast<std::size_t>(a.slot)];
    a.group = -1;
    a.slot = -1;
}

void CityLife::reserve(int i, int group, int spot) {
    unreserve(i);
    if (group < 0) return;
    LiveActor& a = pool_[static_cast<std::size_t>(i)];
    a.group = group;
    ++groupCount_[static_cast<std::size_t>(group)];
    a.slot = spot;
    if (spot >= 0) ++spotUse_[static_cast<std::size_t>(spot)];
}

int CityLife::nearestDoor(Vec2 p, float reach, TilePos& goal) const {
    const auto& kinds = map_->slotKinds();
    const auto it = std::ranges::find(kinds, std::string_view("door"));
    if (it == kinds.end()) return -1;
    const int door = static_cast<int>(it - kinds.begin());
    float best = 1e9f;
    int found = -1;
    map_->forEachSlotNear(p, reach, door, [&](const WorldSlot& s) {
        const float d = dist2(s.at, p);
        if (d < best && map_->walkable(s.tile)) {
            best = d;
            found = static_cast<int>(&s - map_->slots().data());
            goal = s.tile;
        }
    });
    return found;
}

bool CityLife::planTo(int i, TilePos goal, Vec2 end, int& builds) {
    LiveActor& a = pool_[static_cast<std::size_t>(i)];
    const int pi = w_->pathsOf[a.region];
    if (pi < 0) return false;
    RegionPaths& paths = w_->paths[static_cast<std::size_t>(pi)];
    auto& desc = desc_[static_cast<std::size_t>(i)];
    const PlanResult r = paths.plan(a.tile.pos(), goal, a.route, desc, builds);
    if (r == PlanResult::Wait) waited_ = true;
    if (r != PlanResult::Ok) return false;
    startTrack(i, end);
    return true;
}

bool CityLife::resolve(int i, const Target& t, TilePos& goal, int& group, int& spot, Vec2& at,
                       float& z, std::uint8_t& face) {
    LiveActor& a = pool_[static_cast<std::size_t>(i)];
    group = -1;
    spot = -1;
    face = 0xFF;
    const int pi = w_->pathsOf[a.region];
    if (pi < 0) return false;
    const RegionPaths& paths = w_->paths[static_cast<std::size_t>(pi)];
    const auto standOn = [&](TilePos t0) -> bool {
        // The tile itself, else a neighbour walkers reach.
        if (map_->walkable(t0) && paths.reachable(t0)) {
            goal = t0;
            return true;
        }
        for (const TilePos s : kSteps) {
            const TilePos n{t0.x + s.x, t0.y + s.y};
            if (map_->inBounds(n) && map_->walkable(n) && paths.reachable(n)) {
                goal = n;
                return true;
            }
        }
        return false;
    };
    const auto useSlot = [&](int slotIndex) -> bool {
        const WorldSlot& s = map_->slots()[static_cast<std::size_t>(slotIndex)];
        if (!standOn(s.tile)) return false;
        group = static_cast<int>(w_->slotGroup[static_cast<std::size_t>(slotIndex)]);
        spot = slotIndex;
        at = goal == s.tile ? s.at : centre(goal);
        z = goal == s.tile ? static_cast<float>(s.z) : 0.0f;
        face = s.face;
        return true;
    };
    const auto freeGroup = [&](std::uint32_t g) { return groupCount_[g] < w_->groupCap[g]; };
    // The spot of a group to stand at: its least used (a free one while there is one).
    const auto spotOf = [&](std::uint32_t g) {
        std::uint32_t best = w_->groupSlots[w_->groupSpotsAt[g]];
        for (std::uint32_t k = w_->groupSpotsAt[g]; k < w_->groupSpotsAt[g + 1]; ++k)
            if (spotUse_[w_->groupSlots[k]] < spotUse_[best]) best = w_->groupSlots[k];
        return static_cast<int>(best);
    };
    at = {};
    z = 0;
    switch (t.kind) {
    case TargetKind::None: return false;
    case TargetKind::Here:
    case TargetKind::Each:
        goal = a.tile.pos();
        at = a.pos;
        return true;
    case TargetKind::Node: {
        // Somewhere about the node, not all on its one tile: a free tile a few steps off it
        // that walkers reach on the node's level.
        const TilePos n = paths.nodeAt(t.node);
        const int lv = map_->inBounds(n) ? map_->level(n) : 0;
        for (int k = 0; k < 6; ++k) {
            const int r = tl::kNodeSpread;
            const TilePos c{
                n.x + static_cast<int>(next(a.rng) % static_cast<std::uint64_t>(2 * r + 1)) - r,
                n.y + static_cast<int>(next(a.rng) % static_cast<std::uint64_t>(2 * r + 1)) - r};
            if (map_->inBounds(c) && map_->walkable(c) && paths.reachable(c) &&
                map_->level(c) == lv && paths.lineClear(n, c, 2 * r)) {
                goal = c;
                at = centre(c);
                return true;
            }
        }
        if (!standOn(n)) return false;
        at = centre(goal);
        return true;
    }
    case TargetKind::Flock: {
        // The node the herd of this chunk heads for this period: the same for every member.
        const auto cx = static_cast<int>(a.tile.x) >> kChunkShift;
        const auto cy = static_cast<int>(a.tile.y) >> kChunkShift;
        const Vec2 c{static_cast<float>(cx * kChunk + kHalfChunk),
                     static_cast<float>(cy * kChunk + kHalfChunk)};
        const float r2 = t.within * t.within;
        int count = 0;
        for (int n = 0; n < paths.nodeCount(); ++n)
            if (dist2(centre(paths.nodeAt(n)), c) <= r2 && paths.reachable(paths.nodeAt(n)))
                ++count;
        if (count == 0) return false;
        const auto pick = static_cast<int>(
            hashOf({seed_, 0xF10C, static_cast<std::uint64_t>(cx), static_cast<std::uint64_t>(cy),
                    static_cast<std::uint64_t>(hourIndex_ / 4)}) %
            static_cast<std::uint64_t>(count));
        int seen = 0;
        for (int n = 0; n < paths.nodeCount(); ++n) {
            if (dist2(centre(paths.nodeAt(n)), c) > r2 || !paths.reachable(paths.nodeAt(n)))
                continue;
            if (seen++ != pick) continue;
            // Each sheep a little apart from the next about the shared place.
            const TilePos np = paths.nodeAt(n);
            for (int k = 0; k < 6; ++k) {
                const TilePos q{np.x + static_cast<int>(next(a.rng) % 5) - 2,
                                np.y + static_cast<int>(next(a.rng) % 5) - 2};
                if (map_->inBounds(q) && map_->walkable(q) && paths.reachable(q) &&
                    paths.lineClear(np, q, 4)) {
                    goal = q;
                    at = {static_cast<float>(q.x) + range(a, 0.2f, 0.8f),
                          static_cast<float>(q.y) + range(a, 0.2f, 0.8f)};
                    return true;
                }
            }
            if (!standOn(np)) return false;
            at = centre(goal);
            return true;
        }
        return false;
    }
    case TargetKind::Roam: {
        // A random node within reach (reservoir choice over the nodes in the circle).
        const float r2 = t.within * t.within;
        int chosen = -1;
        int seen = 0;
        for (int n = 0; n < paths.nodeCount(); ++n) {
            const TilePos np = paths.nodeAt(n);
            if (dist2(centre(np), a.pos) > r2 || np == a.tile.pos() || !paths.reachable(np))
                continue;
            ++seen;
            if (next(a.rng) % static_cast<std::uint64_t>(seen) == 0) chosen = n;
        }
        if (chosen < 0 || !standOn(paths.nodeAt(chosen))) return false;
        at = centre(goal);
        return true;
    }
    case TargetKind::SlotKind: {
        const float reach = t.within > 0 ? t.within : tl::kDoorReach;
        float best = 1e9f;
        int found = -1;
        map_->forEachSlotNear(a.pos, reach, t.slotKind, [&](const WorldSlot& s) {
            const auto si = static_cast<std::size_t>(&s - map_->slots().data());
            if (!freeGroup(w_->slotGroup[si])) return;
            const float d = dist2(s.at, a.pos) + uniform(a) * 4.0f;
            if (d < best) {
                best = d;
                found = static_cast<int>(si);
            }
        });
        return found >= 0 && useSlot(spotOf(w_->slotGroup[static_cast<std::size_t>(found)]));
    }
    case TargetKind::Home: {
        int item = a.home;
        const Role& role = w_->data.regions[a.region].roles[static_cast<std::size_t>(a.role)];
        if (item < 0 && role.homeItem >= 0) {
            // The nearest instance of its home item in the region.
            const auto& items = w_->regionItems[a.region];
            float best = 1e9f;
            for (auto it = std::ranges::lower_bound(
                     items, std::pair<std::uint32_t, std::uint32_t>(
                                static_cast<std::uint32_t>(role.homeItem), 0));
                 it != items.end() && it->first == static_cast<std::uint32_t>(role.homeItem);
                 ++it) {
                const Placed& p = map_->items()[it->second];
                const float d = dist2(centre({p.x, p.y}), a.pos);
                if (d < best) {
                    best = d;
                    item = static_cast<int>(it->second);
                }
            }
            a.home = item;
        }
        if (item < 0) return false;
        const int name = t.beside ? -1 : (t.slot >= 0 ? t.slot : role.homeSlot);
        const Placed& p = map_->items()[static_cast<std::size_t>(item)];
        int found = -1;
        map_->forEachSlotNear(centre({p.x, p.y}), static_cast<float>(std::max(p.w, p.h)) + 2.0f, -1,
                              [&](const WorldSlot& s) {
                                  if (found < 0 && s.item == static_cast<std::uint32_t>(item) &&
                                      static_cast<int>(s.name) == name)
                                      found = static_cast<int>(&s - map_->slots().data());
                              });
        if (found < 0) {
            // No such slot on it: beside it.
            for (int y = p.y - 1; y <= p.y + p.h; ++y)
                for (int x = p.x - 1; x <= p.x + p.w; ++x)
                    if (map_->inBounds({x, y}) &&
                        (x < p.x || y < p.y || x >= p.x + p.w || y >= p.y + p.h) &&
                        standOn({x, y})) {
                        at = centre(goal);
                        return true;
                    }
            return false;
        }
        // Its own place; when every spot of it is taken, beside it.
        const std::uint32_t g = w_->slotGroup[static_cast<std::size_t>(found)];
        if (freeGroup(g)) return useSlot(spotOf(g));
        for (int y = p.y - 1; y <= p.y + p.h; ++y)
            for (int x = p.x - 1; x <= p.x + p.w; ++x)
                if (map_->inBounds({x, y}) &&
                    (x < p.x || y < p.y || x >= p.x + p.w || y >= p.y + p.h) && standOn({x, y})) {
                    at = centre(goal);
                    return true;
                }
        return false;
    }
    case TargetKind::Item: {
        const float reach = t.within > 0 ? t.within : tl::kSlotReach;
        if (t.slot >= 0) {
            float best = 1e9f;
            int found = -1;
            const auto consider = [&](const WorldSlot& s) {
                if (static_cast<int>(s.name) != t.slot ||
                    static_cast<int>(map_->items()[s.item].info) != t.item)
                    return;
                const auto si = static_cast<std::size_t>(&s - map_->slots().data());
                if (!freeGroup(w_->slotGroup[si])) return;
                const float d = dist2(s.at, a.pos) + uniform(a) * 4.0f;
                if (d < best) {
                    best = d;
                    found = static_cast<int>(si);
                }
            };
            map_->forEachSlotNear(a.pos, reach, -1, consider);
            if (found < 0 && t.within <= 0) {
                // Anywhere in the region.
                const auto& items = w_->regionItems[a.region];
                for (auto it = std::ranges::lower_bound(items,
                                                        std::pair<std::uint32_t, std::uint32_t>(
                                                            static_cast<std::uint32_t>(t.item), 0));
                     it != items.end() && it->first == static_cast<std::uint32_t>(t.item); ++it) {
                    const Placed& p = map_->items()[it->second];
                    map_->forEachSlotNear(centre({p.x, p.y}),
                                          static_cast<float>(std::max(p.w, p.h)) + 2.0f, -1,
                                          [&](const WorldSlot& s) {
                                              if (s.item == it->second) consider(s);
                                          });
                }
            }
            return found >= 0 && useSlot(spotOf(w_->slotGroup[static_cast<std::size_t>(found)]));
        }
        // Beside the nearest instance.
        const auto& items = w_->regionItems[a.region];
        float best = 1e9f;
        int item = -1;
        for (auto it = std::ranges::lower_bound(items, std::pair<std::uint32_t, std::uint32_t>(
                                                           static_cast<std::uint32_t>(t.item), 0));
             it != items.end() && it->first == static_cast<std::uint32_t>(t.item); ++it) {
            const Placed& p = map_->items()[it->second];
            const float d = dist2(centre({p.x, p.y}), a.pos) + uniform(a) * 9.0f;
            if (t.within > 0 && d > t.within * t.within) continue;
            if (d < best) {
                best = d;
                item = static_cast<int>(it->second);
            }
        }
        if (item < 0) return false;
        const Placed& p = map_->items()[static_cast<std::size_t>(item)];
        const int ring = 2 * (p.w + p.h) + 4;
        const int startAt = static_cast<int>(next(a.rng) % static_cast<std::uint64_t>(ring));
        for (int k = 0; k < ring; ++k) {
            const int r = (startAt + k) % ring;
            TilePos c;
            if (r < p.w + 2)
                c = {p.x - 1 + r, p.y - 1};
            else if (r < 2 * (p.w + 2))
                c = {p.x - 1 + (r - p.w - 2), p.y + p.h};
            else if (r < 2 * (p.w + 2) + p.h)
                c = {p.x - 1, p.y + (r - 2 * (p.w + 2))};
            else
                c = {p.x + p.w, p.y + (r - 2 * (p.w + 2) - p.h)};
            if (map_->inBounds(c) && map_->walkable(c) && paths.reachable(c)) {
                goal = c;
                at = centre(c);
                return true;
            }
        }
        return false;
    }
    }
    return false;
}

CityLife::Begin CityLife::beginStep(int i, std::uint32_t s, float& estimate) {
    LiveActor& a = pool_[static_cast<std::size_t>(i)];
    const Step& st = w_->data.steps[s];
    a.step = s;
    estimate = 0;
    const auto duration = [&](float fallback) {
        if (st.until == Until::Hour && st.untilHour >= 0)
            return static_cast<float>(
                std::fmod(static_cast<double>(st.untilHour - hour_) + 24.0, 24.0) *
                kSecondsPerHour);
        if (st.dur1 > 0) return range(a, st.dur0, st.dur1);
        return fallback;
    };
    const bool hold = st.until == Until::Clear || st.until == Until::Rain;
    const auto act = [&](ActState state, std::uint16_t anim, float fallback) {
        a.state = state;
        a.anim = anim;
        a.timer = hold ? 1e9f : duration(fallback);
        estimate = a.timer;
        return hold ? Begin::Hold : Begin::Timed;
    };
    switch (st.verb) {
    case Verb::Go:
    case Verb::Use: {
        if (st.verb == Verb::Use &&
            (st.target.kind == TargetKind::Here || st.target.kind == TargetKind::Each)) {
            if (st.state != ItemState::None || st.effect == Effect::OpenShutters) {
                const int item = map_->itemAt(a.tile.pos());
                if (item >= 0)
                    setItemState(static_cast<std::uint32_t>(item),
                                 st.effect == Effect::OpenShutters ? ItemState::Open : st.state,
                                 now_ + 60.0);
            }
            return act(ActState::Act, st.anim, 10.0f);
        }
        TilePos goal;
        int group = -1;
        int spot = -1;
        Vec2 at;
        float z = 0;
        std::uint8_t face = 0xFF;
        if (!resolve(i, st.target, goal, group, spot, at, z, face)) return Begin::Failed;
        if (goal == a.tile.pos()) {
            a.route = Route{};
            a.route.leg = Leg::Done;
            startTrack(i, at);
        } else {
            waited_ = false;
            if (!planTo(i, goal, at, builds_)) return waited_ ? Begin::Wait : Begin::Failed;
        }
        reserve(i, group, spot);
        a.face = face;
        a.anchor = tile16(goal);
        a.state = ActState::Travel;
        a.anim = kAnimMove;
        const int pi = w_->pathsOf[a.region];
        const float len = static_cast<float>(
            std::max(0, w_->paths[static_cast<std::size_t>(pi)].length(
                            a.route, a.tile.pos(), desc_[static_cast<std::size_t>(i)])));
        estimate = len / std::max(0.1f, a.speed);
        if (st.verb == Verb::Use) {
            a.timer = hold ? 1e9f : duration(10.0f);
            if (!hold) estimate += a.timer;
        }
        return Begin::Travel;
    }
    case Verb::Wait: return act(ActState::Act, kAnimIdle, 5.0f);
    case Verb::Wander:
        a.anchor = a.tile;
        a.zone = static_cast<std::int16_t>(st.zone);
        a.route = Route{};
        return act(ActState::Wander, kAnimMove, 30.0f);
    case Verb::Enter:
        unreserve(i);
        a.flags |= live_flag::kFadeOut;
        return act(ActState::Inside, kAnimIdle, 30.0f);
    case Verb::Take:
        a.goods = static_cast<std::int16_t>(st.goods);
        a.goodsCount = 1;
        return Begin::Instant;
    case Verb::Put:
        a.goods = -1;
        a.goodsCount = 0;
        return Begin::Instant;
    case Verb::Emit:
        if (sounds_.size() < sounds_.capacity() && st.sound >= 0)
            sounds_.push_back({st.sound, st.fx, a.pos, a.region});
        return Begin::Instant;
    case Verb::Follow: {
        int best = -1;
        float bd = tl::kFollowReach * tl::kFollowReach;
        for (std::size_t k = 0; k < pool_.size(); ++k) {
            const LiveActor& o = pool_[k];
            if ((o.flags & live_flag::kAlive) == 0 || static_cast<int>(k) == i ||
                o.kind != st.follow)
                continue;
            const float d = dist2(o.pos, a.pos);
            if (d < bd) {
                bd = d;
                best = static_cast<int>(k);
            }
        }
        if (best < 0) return Begin::Failed;
        a.follow = best;
        a.followGen = pool_[static_cast<std::size_t>(best)].gen;
        a.state = ActState::Follow;
        a.anim = kAnimMove;
        a.timer = st.dur1 > 0 ? range(a, st.dur0, st.dur1) : 1e9f;
        estimate = a.timer;
        return st.dur1 > 0 ? Begin::Timed : Begin::Hold;
    }
    case Verb::Pick: {
        float total = 0;
        for (std::uint32_t k = 0; k < st.count; ++k) total += w_->data.blocks[st.first + k].weight;
        float r = uniform(a) * total;
        std::uint32_t chosen = st.first;
        for (std::uint32_t k = 0; k < st.count; ++k) {
            r -= w_->data.blocks[st.first + k].weight;
            if (r <= 0) {
                chosen = st.first + k;
                break;
            }
        }
        if (st.count > 0 && a.depth < a.stack.size())
            a.stack[a.depth++] = {static_cast<std::uint16_t>(chosen), 0, 0};
        return Begin::Instant;
    }
    case Verb::Routine:
        if (a.depth < a.stack.size())
            a.stack[a.depth++] = {static_cast<std::uint16_t>(st.first), 0, 0};
        return Begin::Instant;
    case Verb::Each:
        return Begin::Instant; // city roles do not use it; events light their lamps themselves
    }
    return Begin::Instant;
}

void CityLife::endStep(int i) {
    LiveActor& a = pool_[static_cast<std::size_t>(i)];
    const Step* st = a.step == kNoStep ? nullptr : &w_->data.steps[a.step];
    if (st != nullptr && st->verb == Verb::Use && a.state == ActState::Travel) {
        // Arrived: now the use itself.
        a.state = ActState::Act;
        a.anim = st->anim;
        if (st->state != ItemState::None || st->effect == Effect::OpenShutters) {
            const int item =
                a.slot >= 0 ? static_cast<int>(map_->slots()[static_cast<std::size_t>(a.slot)].item)
                            : map_->itemAt(a.tile.pos());
            if (item >= 0)
                setItemState(static_cast<std::uint32_t>(item),
                             st->effect == Effect::OpenShutters ? ItemState::Open : st->state,
                             now_ + 60.0);
        }
        return;
    }
    if (st != nullptr && st->verb == Verb::Enter) {
        a.flags = static_cast<std::uint8_t>((a.flags & ~live_flag::kFadeOut) | live_flag::kFadeIn);
    }
    if (st != nullptr && st->verb == Verb::Go) {
        // Stays at its slot through the next steps (a `use here`), or lets it go when it walks on.
    }
    a.state = ActState::Idle;
    a.step = kNoStep;
    a.timer = 0;
}

bool CityLife::runSteps(int i, bool fastForward, double& budget) {
    LiveActor& a = pool_[static_cast<std::size_t>(i)];
    const auto& data = w_->data;
    for (int guard = 0; guard < 48; ++guard) {
        if (a.depth == 0) {
            if ((a.flags & live_flag::kInterrupt) != 0) {
                a.flags = static_cast<std::uint8_t>(a.flags & ~live_flag::kInterrupt);
                chooseRoutine(i);
                continue;
            }
            if ((a.flags & live_flag::kRain) != 0 && !clock_.rain) {
                chooseRoutine(i);
                if (a.depth == 0) return false;
                continue;
            }
            // Its routine ran out: potter about until the next block.
            a.step = kNoStep;
            a.anchor = a.tile;
            a.zone = -1;
            a.state = ActState::Wander;
            a.anim = kAnimMove;
            a.timer = range(a, tl::kIdle0, tl::kIdle1);
            return false;
        }
        LiveActor::Frame& f = a.stack[a.depth - 1];
        const Block& b = data.blocks[f.block];
        if (f.pc >= b.count) {
            if (b.loop && f.n < 250 && b.count > 0) {
                f.pc = 0;
                ++f.n;
                continue;
            }
            --a.depth;
            continue;
        }
        const std::uint32_t s = b.first + f.pc;
        ++f.pc;
        float est = 0;
        const Begin r = beginStep(i, s, est);
        switch (r) {
        case Begin::Instant: continue;
        case Begin::Failed:
            ++stats_.failedSteps;
            a.state = ActState::Act;
            a.anim = kAnimIdle;
            a.timer = range(a, tl::kFailPause0, tl::kFailPause1);
            a.step = kNoStep;
            if (fastForward) {
                budget -= a.timer;
                if (budget > 0) continue;
                a.timer = static_cast<float>(-budget);
            }
            return true;
        case Begin::Wait:
            --f.pc;
            a.state = ActState::Idle;
            a.timer = 0.05f;
            return true;
        case Begin::Hold: return true;
        case Begin::Timed:
        case Begin::Travel:
            if (!fastForward) return true;
            if (static_cast<double>(est) <= budget) {
                budget -= est;
                if (r == Begin::Travel) {
                    // Arrived at once: where the walk ends.
                    const TilePos g = a.route.leg == Leg::None ? a.tile.pos() : a.route.goal.pos();
                    a.tile = tile16(g);
                    a.pos = a.endPoint;
                    a.z = static_cast<float>(map_->floorZ(g));
                    a.route = Route{};
                    tracks_[static_cast<std::size_t>(i)].n = 0;
                    endStep(i);
                    if (a.state == ActState::Act) {
                        endStep(i);
                    }
                } else {
                    endStep(i);
                }
                if (a.state == ActState::Inside) a.flags |= live_flag::kFadeIn;
                continue;
            }
            // Part way through this step.
            if (r == Begin::Travel) {
                const Step& st = data.steps[s];
                const double walk =
                    static_cast<double>(est) - (st.verb == Verb::Use ? a.timer : 0.0);
                if (budget < walk) {
                    advanceBy(i, static_cast<float>(budget) * a.speed);
                } else {
                    // At the place, part way through the use.
                    advanceBy(i, 1e6f);
                    if (a.state == ActState::Travel) endStep(i);
                    a.timer -= static_cast<float>(budget - walk);
                }
            } else {
                a.timer -= static_cast<float>(budget);
            }
            budget = 0;
            return true;
        }
    }
    return true;
}

// -- motion: smooth, continuous, eased --------------------------------------------------------
//
// A walker's route is a staircase of tiles; it is walked as a continuous path: the track holds
// the route's next tiles, a position is the average of the staircase over a tile either side
// (diagonals instead of zigzags, corners rounded), kept only where the ground allows it, and a
// walker eases into its pace and out of it, keeps a little to one side of the way, and is moved
// every step (decisions are what the buckets slice).

void CityLife::startTrack(int i, Vec2 end) {
    LiveActor& a = pool_[static_cast<std::size_t>(i)];
    Track& tr = tracks_[static_cast<std::size_t>(i)];
    tr.t[0] = a.tile;
    tr.base = 0;
    tr.n = 1;
    tr.ended = false;
    a.s = 0;
    a.startOffset = {a.pos.x - (static_cast<float>(a.tile.x) + 0.5f),
                     a.pos.y - (static_cast<float>(a.tile.y) + 0.5f)};
    a.endPoint = end;
    fillTrack(i);
    if (tr.n == 1) {
        // Already on the goal's tile: a glide from where it stands to the spot.
        tr.t[1] = tr.t[0];
        tr.n = 2;
    }
}

void CityLife::fillTrack(int i) {
    LiveActor& a = pool_[static_cast<std::size_t>(i)];
    Track& tr = tracks_[static_cast<std::size_t>(i)];
    const int pi = w_->pathsOf[a.region];
    if (pi < 0) {
        tr.ended = true;
        return;
    }
    RegionPaths& paths = w_->paths[static_cast<std::size_t>(pi)];
    while (tr.n < tr.t.size() && !tr.ended) {
        TilePos nx;
        if (paths.next(a.route, tr.t[tr.n - 1u].pos(), desc_[static_cast<std::size_t>(i)], nx))
            tr.t[tr.n++] = tile16(nx);
        else
            tr.ended = true;
    }
}

bool CityLife::moving(int i) const {
    const Track& tr = tracks_[static_cast<std::size_t>(i)];
    if (tr.n == 0) return false;
    return !tr.ended ||
           pool_[static_cast<std::size_t>(i)].s < static_cast<float>(tr.base + tr.n - 1) - 1e-4f;
}

Vec2 CityLife::trackRaw(int i, float s) const {
    const LiveActor& a = pool_[static_cast<std::size_t>(i)];
    const Track& tr = tracks_[static_cast<std::size_t>(i)];
    const auto last = static_cast<float>(tr.n - 1);
    const float u = std::clamp(s - static_cast<float>(tr.base), 0.0f, last);
    const auto k = static_cast<std::size_t>(std::min(u, std::max(0.0f, last - 1.0f)));
    const float f = u - static_cast<float>(k);
    const auto point = [&](std::size_t j) {
        if (tr.ended && j + 1 == tr.n) return a.endPoint;
        return centre(tr.t[j].pos());
    };
    const Vec2 p0 = point(k);
    const Vec2 p1 = point(std::min<std::size_t>(k + 1, tr.n - 1u));
    return {p0.x + (p1.x - p0.x) * f, p0.y + (p1.y - p0.y) * f};
}

Vec2 CityLife::trackPoint(int i, float s, bool lateral) const {
    const LiveActor& a = pool_[static_cast<std::size_t>(i)];
    const Track& tr = tracks_[static_cast<std::size_t>(i)];
    const Vec2 raw = trackRaw(i, s);
    const float r = tl::kSmoothReach;
    Vec2 p{};
    for (const float o : {-r, -0.5f * r, 0.0f, 0.5f * r, r}) {
        const Vec2 q = trackRaw(i, s + o);
        p.x += q.x * 0.2f;
        p.y += q.y * 0.2f;
    }
    // Ends stay exact: the average blends back to the route at a track's start and its goal.
    const auto last = static_cast<float>(tr.base + tr.n - 1);
    const float edge = std::clamp(std::min(s, tr.ended ? last - s : r) / r, 0.0f, 1.0f);
    p = {raw.x + (p.x - raw.x) * edge, raw.y + (p.y - raw.y) * edge};
    // Where it stood off the start tile's centre, eased away over the first tiles.
    const float total = tr.ended ? last : tl::kLateralRamp;
    const float w = std::max(0.0f, 1.0f - s / std::max(1e-3f, std::min(tl::kLateralRamp, total)));
    p.x += a.startOffset.x * w;
    p.y += a.startOffset.y * w;
    if (lateral && a.lateral != 0.0f) {
        const Vec2 ahead = trackRaw(i, s + 0.5f);
        const Vec2 behind = trackRaw(i, s - 0.5f);
        const float dx = ahead.x - behind.x;
        const float dy = ahead.y - behind.y;
        const float len = std::sqrt(dx * dx + dy * dy);
        const float ramp = std::clamp(
            std::min(s, tr.ended ? last - s : tl::kLateralRamp) / tl::kLateralRamp, 0.0f, 1.0f);
        if (len > 1e-3f) {
            p.x += -dy / len * a.lateral * ramp;
            p.y += dx / len * a.lateral * ramp;
        }
    }
    return settleOnGround(raw, p);
}

// The point nearest `want` on the way from `raw` (which is on the route, so allowed) that is
// still on walkable ground at the route's level, without squeezing between two walls: a
// continuous retreat towards the route rather than a jump back to it.
Vec2 CityLife::settleOnGround(Vec2 raw, Vec2 want) const {
    const TilePos rt{static_cast<int>(std::floor(raw.x)), static_cast<int>(std::floor(raw.y))};
    if (!map_->inBounds(rt)) return raw;
    const int level = map_->level(rt);
    const auto ok = [&](Vec2 p) {
        const TilePos pt{static_cast<int>(std::floor(p.x)), static_cast<int>(std::floor(p.y))};
        if (pt == rt) return true;
        if (!map_->inBounds(pt) || !map_->walkable(pt) || map_->level(pt) != level) return false;
        if (std::abs(pt.x - rt.x) > 1 || std::abs(pt.y - rt.y) > 1) return false;
        return pt.x == rt.x || pt.y == rt.y ||
               (map_->walkable({pt.x, rt.y}) && map_->walkable({rt.x, pt.y}));
    };
    if (ok(want)) return want;
    float lo = 0;
    float hi = 1;
    for (int k = 0; k < 6; ++k) {
        const float mid = 0.5f * (lo + hi);
        if (ok({raw.x + (want.x - raw.x) * mid, raw.y + (want.y - raw.y) * mid}))
            lo = mid;
        else
            hi = mid;
    }
    return {raw.x + (want.x - raw.x) * lo, raw.y + (want.y - raw.y) * lo};
}

void CityLife::placeOnTrack(int i, float maxStep) {
    LiveActor& a = pool_[static_cast<std::size_t>(i)];
    Track& tr = tracks_[static_cast<std::size_t>(i)];
    // Tiles left behind leave the track (keeping one tile of the average behind).
    while (a.s - static_cast<float>(tr.base) >= 2.0f + tl::kSmoothReach && tr.n > 4) {
        std::copy(tr.t.begin() + 1, tr.t.begin() + tr.n, tr.t.begin());
        --tr.n;
        ++tr.base;
        fillTrack(i);
    }
    Vec2 p = trackPoint(i, a.s, true);
    if (maxStep > 0) {
        // Never faster than its pace where it is drawn: when the ground it may stand on changes
        // under the average, it catches up over a few steps instead of jumping.
        const float d = std::sqrt(dist2(p, a.pos));
        if (d > maxStep && d < 1.0f) {
            const Vec2 q{a.pos.x + (p.x - a.pos.x) * maxStep / d,
                         a.pos.y + (p.y - a.pos.y) * maxStep / d};
            const TilePos tq{static_cast<int>(std::floor(q.x)), static_cast<int>(std::floor(q.y))};
            if (map_->inBounds(tq) && map_->walkable(tq)) p = q;
        }
    }
    a.pos = p;
    const Vec2 raw = trackRaw(i, a.s);
    const TilePos t{static_cast<int>(std::floor(a.pos.x)), static_cast<int>(std::floor(a.pos.y))};
    a.tile = tile16(
        map_->inBounds(t) && map_->walkable(t)
            ? t
            : TilePos{static_cast<int>(std::floor(raw.x)), static_cast<int>(std::floor(raw.y))});
    // Height along stairs: between the floors of the route tiles it is between.
    const float u =
        std::clamp(a.s - static_cast<float>(tr.base), 0.0f, static_cast<float>(tr.n - 1));
    const auto k =
        static_cast<std::size_t>(std::min(u, std::max(0.0f, static_cast<float>(tr.n) - 2.0f)));
    const float f = u - static_cast<float>(k);
    const auto z0 = static_cast<float>(map_->floorZ(tr.t[k].pos()));
    const auto z1 =
        static_cast<float>(map_->floorZ(tr.t[std::min<std::size_t>(k + 1, tr.n - 1u)].pos()));
    a.z = z0 + (z1 - z0) * f;
    if (!moving(i)) {
        a.route.leg = Leg::Done;
        a.pos = a.endPoint;
        if (a.face != 0xFF) {
            // A slot's face (+x, +y, -x, -y) turns it as the slot says.
            static constexpr std::array<std::uint8_t, 4> kFacing{0, 1, 3, 2};
            static constexpr std::array<float, 4> kHeading{0.0f, 1.5707964f, 3.1415927f,
                                                           -1.5707964f};
            a.facing = kFacing[a.face % 4];
            a.heading = kHeading[a.face % 4];
        }
    }
    link(i);
}

void CityLife::motion(int i, float dt) {
    LiveActor& a = pool_[static_cast<std::size_t>(i)];
    if (!moving(i)) {
        a.speedNow = std::max(0.0f, a.speedNow - a.speed * dt / tl::kEaseSeconds);
        return;
    }
    const Track& tr = tracks_[static_cast<std::size_t>(i)];
    const float pace = a.speed * (a.state == ActState::Wander ? tl::kWanderPace : 1.0f);
    const float left = tr.ended ? static_cast<float>(tr.base + tr.n - 1) - a.s : 1e9f;
    const float target = left < tl::kBrakeTiles
                             ? std::max(tl::kBrakeFloor * pace, pace * left / tl::kBrakeTiles)
                             : pace;
    const float ease = pace * dt / tl::kEaseSeconds;
    a.speedNow = std::clamp(target, a.speedNow - ease, a.speedNow + ease);
    // Constant speed over the ground: the step along the track that moves it exactly this far
    // where it is drawn (diagonals, the outside of a turn), found by two refinements.
    const float want = a.speedNow * dt;
    float ds = want;
    const float end = tr.ended ? static_cast<float>(tr.base + tr.n - 1) : 1e9f;
    for (int k = 0; k < 2 && want > 1e-6f; ++k) {
        const Vec2 p = trackPoint(i, std::min(end, a.s + ds), true);
        const float got = std::sqrt(dist2(p, a.pos));
        if (got < 1e-6f) break;
        ds = std::clamp(ds * want / got, 0.5f * want, 2.0f * want);
    }
    a.s += ds;
    if (tr.ended) a.s = std::min(a.s, static_cast<float>(tr.base + tr.n - 1));
    placeOnTrack(i, tl::kCatchUp * std::max(a.speedNow, tl::kBrakeFloor * pace) * dt);
}

void CityLife::advanceBy(int i, float tiles) {
    LiveActor& a = pool_[static_cast<std::size_t>(i)];
    Track& tr = tracks_[static_cast<std::size_t>(i)];
    float left = tiles;
    for (int guard = 0; guard < 100000 && left > 0 && moving(i); ++guard) {
        const float step = std::min(left, 1.0f);
        a.s += step;
        left -= step;
        if (tr.ended) a.s = std::min(a.s, static_cast<float>(tr.base + tr.n - 1));
        while (a.s - static_cast<float>(tr.base) >= 2.0f + tl::kSmoothReach && tr.n > 4) {
            std::copy(tr.t.begin() + 1, tr.t.begin() + tr.n, tr.t.begin());
            --tr.n;
            ++tr.base;
            fillTrack(i);
        }
    }
    a.speedNow = moving(i) ? a.speed : 0.0f;
    placeOnTrack(i, 0);
}

std::uint16_t CityLife::shownAnim(const LiveActor& a) const {
    // The body decides: a walk only while it moves over the ground, its standing form (idle, or
    // standing with its load) while it does not; moving with a standing animation is walking.
    // Intent never shows: a step begun but not yet moving, a puppet held at its place, a walker
    // braking to its spot, all stand.
    const KindDef& k = w_->data.kinds[a.kind];
    const auto has = [&](int anim) { return anim >= 0 && k.has(static_cast<std::uint16_t>(anim)); };
    const std::uint16_t want = has(a.anim) ? a.anim : kAnimIdle;
    const std::int16_t standing = want < idleOf_.size() ? idleOf_[want] : std::int16_t{-1};
    if ((a.body & body_flag::kWalking) != 0) {
        if (standing >= 0) return want; // a walk, and walking
        return has(carryWalk_) && a.goods >= 0 ? static_cast<std::uint16_t>(carryWalk_) : kAnimMove;
    }
    if (standing < 0) return want;
    return has(standing) ? static_cast<std::uint16_t>(standing) : kAnimIdle;
}

void CityLife::judgeWindow(int i) {
    LiveActor& a = pool_[static_cast<std::size_t>(i)];
    const float net = std::sqrt(dist2(a.pos, a.mark));
    const float walked = a.stride - a.markStride;
    const bool puppet = a.state == ActState::Puppet;
    std::uint8_t b = static_cast<std::uint8_t>(a.body & body_flag::kWalking);
    // Marching: drawn walking for half the window while the body covered less ground than the
    // slowest walk is ever drawn at (its feet would step on the spot).
    if (a.walkTime >= 0.5f * a.markAge && a.walkDist < tl::kShownStop * a.walkTime)
        b |= body_flag::kMarching;
    // To and fro: walking and back where it began, two windows running (one is a U-turn: a
    // walk to a spot and back the way it came).
    if (walked > 4.0f * tl::kStillTiles && net < tl::kStillTiles)
        b |= (a.body & (body_flag::kTurned | body_flag::kOscillating)) != 0
                 ? body_flag::kOscillating
                 : body_flag::kTurned;
    // Stuck: under way at a walking pace (not braking to its spot) and getting nowhere.
    if (!puppet && moving(i) && a.speedNow > 2.0f * tl::kShownWalk && net < tl::kStillTiles)
        b |= body_flag::kStuck;
    // Going nowhere (stuck, or to and fro) counts towards the watchdog alike.
    const bool nowhere = (b & (body_flag::kStuck | body_flag::kOscillating)) != 0;
    a.stall = nowhere ? a.stall + a.markAge : 0.0f;
    if (nowhere) b |= static_cast<std::uint8_t>(a.body & body_flag::kGaveUp);
    a.body = b;
    a.mark = a.pos;
    a.markStride = a.stride;
    a.markAge = 0;
    a.walkTime = 0;
    a.walkDist = 0;
}

void CityLife::afterStep(int i, float dt) {
    LiveActor& a = pool_[static_cast<std::size_t>(i)];
    const float dx = a.pos.x - a.prev.x;
    const float dy = a.pos.y - a.prev.y;
    const float d = std::sqrt(dx * dx + dy * dy);
    a.animTime += dt * a.rate;
    // What is drawn follows the body: its speed over the ground, smoothed, with hysteresis.
    const float v = d > 1.5f || dt <= 0.0f ? 0.0f : d / dt;
    a.shown += (v - a.shown) * std::min(1.0f, dt / tl::kShownSmooth);
    // It starts being drawn walking once it has picked up speed, and stops the step its body
    // stops (the feet never step on a standing body).
    const bool walking = (a.body & body_flag::kWalking) != 0;
    if (walking ? v < tl::kShownStop : a.shown > tl::kShownWalk)
        a.body = static_cast<std::uint8_t>(a.body ^ body_flag::kWalking);
    a.markAge += dt;
    if ((a.body & body_flag::kWalking) != 0 && d <= 1.5f) {
        a.walkTime += dt;
        a.walkDist += d;
    }
    if (d > 1.5f) { // placed, not walked: a new window from here
        a.mark = a.pos;
        a.markStride = a.stride;
        a.markAge = a.walkTime = a.walkDist = 0;
        return;
    }
    if (a.markAge >= tl::kProgressWindow) judgeWindow(i);
    a.stride += d;
    if (a.source != Source::Population && a.source != Source::Figure) a.speedNow = d / dt;
    if (d > 1e-4f) {
        // The heading turns towards the way it moves at a bounded rate: no flips in one step.
        float turn = std::atan2(dy, dx) - a.heading;
        while (turn > 3.1415927f) turn -= 6.2831853f;
        while (turn < -3.1415927f) turn += 6.2831853f;
        const float most = tl::kTurnRate * dt;
        a.heading += std::clamp(turn, -most, most);
        if (a.heading > 3.1415927f) a.heading -= 6.2831853f;
        if (a.heading < -3.1415927f) a.heading += 6.2831853f;
    }
    // The sprite's four directions from the heading, turning only well past a sector's edge so
    // a walker on a diagonal does not flicker between two.
    static constexpr std::array<float, 4> kAxis{0.0f, 1.5707964f, -1.5707964f, 3.1415927f};
    const auto off = [&](std::uint8_t f) {
        float x = a.heading - kAxis[f];
        while (x > 3.1415927f) x -= 6.2831853f;
        while (x < -3.1415927f) x += 6.2831853f;
        return std::abs(x);
    };
    if (d > 1e-4f && off(a.facing) > 0.7853982f + tl::kTurnHold) {
        std::uint8_t best = 0;
        for (std::uint8_t f = 1; f < 4; ++f)
            if (off(f) < off(best)) best = f;
        a.facing = best;
    }
}

void CityLife::think(int i, float dt) {
    LiveActor& a = pool_[static_cast<std::size_t>(i)];
    // Fades.
    if ((a.flags & live_flag::kFadeOut) != 0) {
        a.alpha = std::max(0.0f, a.alpha - dt / tl::kFadeSeconds);
        if (a.alpha <= 0.0f && a.state == ActState::Leave) {
            release(i);
            return;
        }
    } else if ((a.flags & live_flag::kFadeIn) != 0 || a.alpha < 1.0f) {
        a.alpha = std::min(1.0f, a.alpha + dt / tl::kFadeSeconds);
        if (a.alpha >= 1.0f) a.flags = static_cast<std::uint8_t>(a.flags & ~live_flag::kFadeIn);
    }
    if (a.state == ActState::Leave) {
        a.timer -= dt;
        if ((a.flags & live_flag::kFadeOut) == 0 && (!moving(i) || a.timer <= 0))
            a.flags |= live_flag::kFadeOut;
        if (!inView(a.pos)) release(i);
        return;
    }
    if (a.source != Source::Population && a.source != Source::Figure) return;
    // The schedule: a new block restarts the day from where it stands.
    const Role& role = w_->data.regions[a.region].roles[static_cast<std::size_t>(a.role)];
    if ((a.flags & live_flag::kInterrupt) == 0) {
        const int b = blockAt(a.region, role);
        if (b < 0) {
            beginLeave(i);
            return;
        }
        const bool rainNow =
            clock_.rain && role.rainRoutine >= 0 && (a.flags & live_flag::kRain) == 0;
        if (b != a.sched || rainNow) {
            unreserve(i);
            a.flags = static_cast<std::uint8_t>(a.flags & ~live_flag::kFadeOut);
            if (a.state == ActState::Inside) a.flags |= live_flag::kFadeIn;
            a.route = Route{};
            tracks_[static_cast<std::size_t>(i)].n = 0;
            chooseRoutine(i);
        }
    }
    double none = 0;
    // The watchdog: wanting to move and getting nowhere is bounded. First the step is given up
    // (the day goes on with its next step, which plans afresh from where it stands); still
    // stuck, it leaves by the population rule (fades where it stands).
    if (a.stall >= tl::kStallLeave) {
        ++stats_.unstuck;
        beginLeave(i);
        return;
    }
    if (a.stall >= tl::kStallGiveUp && (a.body & body_flag::kGaveUp) == 0) {
        ++stats_.unstuck;
        a.body |= body_flag::kGaveUp; // once; still stuck after that, it leaves
        tracks_[static_cast<std::size_t>(i)].n = 0;
        endStep(i);
        runSteps(i, false, none);
        return;
    }
    switch (a.state) {
    case ActState::Idle:
        a.timer -= dt;
        if (a.timer <= 0) runSteps(i, false, none);
        break;
    case ActState::Travel:
        if (!moving(i)) {
            endStep(i);
            if (a.state == ActState::Idle) runSteps(i, false, none);
        }
        break;
    case ActState::Act:
    case ActState::Inside:
        a.timer -= dt;
        if (a.timer <= 0 || untilMet(a)) {
            endStep(i);
            runSteps(i, false, none);
        }
        break;
    case ActState::Wander: {
        a.timer -= dt;
        if (moving(i)) break;
        if (a.timer <= 0) {
            endStep(i);
            runSteps(i, false, none);
            break;
        }
        // A short walk to a free tile near its centre (or in its zone), now and then a pause.
        const int pi = w_->pathsOf[a.region];
        if (pi < 0) break;
        const RegionPaths& paths = w_->paths[static_cast<std::size_t>(pi)];
        const Step* st = a.step == kNoStep ? nullptr : &w_->data.steps[a.step];
        const int radius = std::max(
            1, static_cast<int>(st != nullptr && st->radius > 0 ? st->radius : tl::kIdleWander));
        a.anim = kAnimIdle;
        if (uniform(a) < tl::kWanderPause) break;
        for (int k = 0; k < tl::kWanderTries; ++k) {
            const TilePos c = a.anchor.pos();
            const auto span = static_cast<std::uint64_t>(2 * radius + 1);
            const TilePos t{c.x + static_cast<int>(next(a.rng) % span) - radius,
                            c.y + static_cast<int>(next(a.rng) % span) - radius};
            if (!map_->inBounds(t) || t == a.tile.pos() || !map_->walkable(t)) continue;
            if (a.zone >= 0 && map_->districtAt(t) != a.zone) continue;
            if (!paths.lineClear(a.tile.pos(), t, 2 * radius + 2)) continue;
            // Somewhere on the tile, not its exact centre; never a shuffle of a few steps (a
            // walk too short to cross the ground reads as walking in place).
            const Vec2 end{static_cast<float>(t.x) + range(a, 0.25f, 0.75f),
                           static_cast<float>(t.y) + range(a, 0.25f, 0.75f)};
            if (dist2(end, a.pos) < tl::kWanderHop * tl::kWanderHop) continue;
            a.route = Route{};
            a.route.leg = Leg::Line;
            a.route.start = a.tile;
            a.route.goal = tile16(t);
            startTrack(i, end);
            a.anim = kAnimMove;
            break;
        }
        break;
    }
    case ActState::Follow: {
        a.timer -= dt;
        // Lost when it is gone, or when its slot holds someone else now (L-115).
        const bool lost =
            a.follow < 0 ||
            (pool_[static_cast<std::size_t>(a.follow)].flags & live_flag::kAlive) == 0 ||
            pool_[static_cast<std::size_t>(a.follow)].gen != a.followGen;
        if (lost || a.timer <= 0) {
            a.follow = -1;
            endStep(i);
            runSteps(i, false, none);
            break;
        }
        const LiveActor& o = pool_[static_cast<std::size_t>(a.follow)];
        const Step& st = w_->data.steps[a.step];
        // Hysteresis: it sets off once it has fallen a tile behind and stops when close, so it
        // never dithers to and fro behind a leader who lingers.
        const float reach = st.spacing + (moving(i) ? 0.6f : 1.6f);
        if (dist2(o.pos, a.pos) > reach * reach) {
            if (!moving(i) || frame_ % 30 < static_cast<std::uint32_t>(tl::kBuckets))
                if (!planTo(i, o.tile.pos(), centre(o.tile.pos()), builds_))
                    tracks_[static_cast<std::size_t>(i)].n = 0;
            a.anim = kAnimMove;
        } else {
            a.anim = kAnimIdle;
            tracks_[static_cast<std::size_t>(i)].n = 0;
        }
        break;
    }
    case ActState::Puppet:
    case ActState::Leave: break;
    }
}

// -- puppets: chain workers, tokens and event casts ----------------------------------------------

bool CityLife::tokenAt(std::size_t t, int k, int member, TokenAt& out) const {
    const Token& tk = w_->data.tokens[t];
    const TokenState& ts = tokenPaths_[t];
    if (!ts.ok) return false;
    const KindDef& kd = w_->data.kinds[static_cast<std::size_t>(tk.kind)];
    const float speed =
        !tk.lane.empty() ? tl::kShipSpeed : (kd.cart ? tl::kCartSpeed : tl::kWalkSpeed);
    const TokenPhase cycle = tokenPhase(t, k);
    const double phase = cycle.phase;
    const double run = ts.length / speed;
    const double stay = tl::kPortStay;
    const double far = ts.farStay;
    double s = 0;
    bool back = false;
    bool working = false;
    out.moving = true;
    if (phase < stay) {
        out.moving = false;
    } else if (phase < stay + run) {
        s = (phase - stay) * speed;
    } else if (phase < stay + run + far) {
        s = ts.length;
        out.moving = ts.fishing;
        working = ts.fishing;
    } else {
        s = ts.length - (phase - stay - run - far) * speed;
        back = true;
    }
    bool flock = false;
    if (tk.group >= 0)
        flock = w_->data.regions[static_cast<std::size_t>(tk.region)]
                    .groups[static_cast<std::size_t>(tk.group)]
                    .formation == Formation::Cluster;
    if (!cycle.underway) {
        // Waiting (out of its hours, or not travelling today): at the last rest stop it passed,
        // or where it stopped when it has none.
        out.moving = false;
        working = false;
        if (back) {
            const auto it = std::ranges::lower_bound(ts.rest, static_cast<float>(s));
            if (it != ts.rest.end()) s = *it;
        } else {
            const auto it = std::ranges::upper_bound(ts.rest, static_cast<float>(s));
            if (it != ts.rest.begin()) s = *std::prev(it);
        }
    }
    if (member > 0)
        s += (back ? 1.0 : -1.0) * static_cast<double>(tl::kTrainSpacing) *
             (flock ? 1.0 : static_cast<double>(member));
    s = std::clamp(s, 0.0, static_cast<double>(ts.length));
    const bool lane = !tk.lane.empty();
    // The line's point at a length, and its corners rounded by an average over a tile or two
    // either side, kept where the vessel or the walker may be.
    const auto at = [&](double len) {
        len = std::clamp(len, 0.0, static_cast<double>(ts.length));
        const auto seg = static_cast<std::size_t>(
            std::ranges::upper_bound(ts.cum, static_cast<float>(len)) - ts.cum.begin());
        const std::size_t k1 = std::clamp<std::size_t>(seg, 1, ts.line.size() - 1);
        const float l0 = ts.cum[k1 - 1];
        const float l1 = ts.cum[k1];
        const float f = l1 > l0 ? (static_cast<float>(len) - l0) / (l1 - l0) : 0.0f;
        return Vec2{ts.line[k1 - 1].x + (ts.line[k1].x - ts.line[k1 - 1].x) * f,
                    ts.line[k1 - 1].y + (ts.line[k1].y - ts.line[k1 - 1].y) * f};
    };
    const auto fits = [&](Vec2 p) {
        const TilePos tp{static_cast<int>(std::floor(p.x)), static_cast<int>(std::floor(p.y))};
        if (!map_->inBounds(tp)) return false;
        if (!lane) return map_->walkable(tp);
        const int ter = map_->terrainAt(tp);
        return ter != world::kNone && map_->terrainInfo(ter).water;
    };
    const Vec2 raw = at(s);
    Vec2 p{};
    const double r = lane ? 1.5 : static_cast<double>(tl::kSmoothReach);
    for (const double o : {-r, -0.5 * r, 0.0, 0.5 * r, r}) {
        const Vec2 q = at(s + o);
        p.x += q.x * 0.2f;
        p.y += q.y * 0.2f;
    }
    if (!fits(p)) p = raw;
    if (working) {
        // A fishing boat works its ground: slow circles about the lane's end.
        const double w = phase - stay - run;
        const double ang = w * tl::kShipSpeed / tl::kFishingRadius + static_cast<double>(k);
        const Vec2 q{p.x + static_cast<float>(std::cos(ang)) * tl::kFishingRadius,
                     p.y + static_cast<float>(std::sin(ang)) * tl::kFishingRadius};
        const double ramp = std::min({1.0, w / 20.0, (far - w) / 20.0}); // ease out and back
        const Vec2 eased{p.x + (q.x - p.x) * static_cast<float>(ramp),
                         p.y + (q.y - p.y) * static_cast<float>(ramp)};
        if (fits(eased)) p = eased;
    }
    if (flock && member > 0) {
        // A flock about its drover rather than in file.
        const double ang = unit(hashOf({0xF7, t, static_cast<std::uint64_t>(k),
                                        static_cast<std::uint64_t>(member)})) *
                           6.2831853;
        const double rad = 0.6 + unit(hashOf({0xF8, t, static_cast<std::uint64_t>(member)})) * 1.6;
        const Vec2 q{p.x + static_cast<float>(std::cos(ang) * rad),
                     p.y + static_cast<float>(std::sin(ang) * rad)};
        if (fits(q)) p = q;
    }
    out.pos = p;
    const Vec2 ahead = at(s + (back ? -0.5 : 0.5));
    const float dx = ahead.x - raw.x;
    const float dy = ahead.y - raw.y;
    out.facing =
        std::abs(dx) >= std::abs(dy) ? facingOf(dx > 0 ? 1 : -1, 0) : facingOf(0, dy > 0 ? 1 : -1);
    return true;
}

int CityLife::memberKind(const Token& tk, int member) const {
    const Group& g = w_->data.regions[static_cast<std::size_t>(tk.region)]
                         .groups[static_cast<std::size_t>(tk.group)];
    int m = 1;
    for (const GroupMember& gm : g.members) {
        if (member < m + gm.count) return gm.kind;
        m += gm.count;
    }
    return tk.kind;
}

Vec2 CityLife::smoothAlong(std::span<const Tile16> line, float s) const {
    if (line.empty()) return {};
    const auto last = static_cast<float>(line.size() - 1);
    const auto raw = [&](float x) {
        x = std::clamp(x, 0.0f, last);
        const auto k = static_cast<std::size_t>(std::min(x, std::max(0.0f, last - 1.0f)));
        const float f = x - static_cast<float>(k);
        const Vec2 p0 = centre(line[k].pos());
        const Vec2 p1 = centre(line[std::min<std::size_t>(k + 1, line.size() - 1)].pos());
        return Vec2{p0.x + (p1.x - p0.x) * f, p0.y + (p1.y - p0.y) * f};
    };
    const Vec2 r0 = raw(s);
    const float r = tl::kSmoothReach;
    Vec2 p{};
    for (const float o : {-r, -0.5f * r, 0.0f, 0.5f * r, r}) {
        const Vec2 q = raw(s + o);
        p.x += q.x * 0.2f;
        p.y += q.y * 0.2f;
    }
    const float edge = std::clamp(std::min(s, last - s) / r, 0.0f, 1.0f);
    p = {r0.x + (p.x - r0.x) * edge, r0.y + (p.y - r0.y) * edge};
    return settleOnGround(r0, p);
}

float CityLife::atLength(std::span<const float> cum, float d) {
    if (cum.size() < 2) return 0;
    if (d <= 0) return 0;
    if (d >= cum.back()) return static_cast<float>(cum.size() - 1);
    const auto it = std::ranges::upper_bound(cum, d);
    const auto k = static_cast<std::size_t>(it - cum.begin()) - 1;
    const float span = cum[k + 1] - cum[k];
    return static_cast<float>(k) + (span > 1e-6f ? (d - cum[k]) / span : 0.0f);
}

const std::vector<Tile16>& CityLife::carrierPath(std::size_t key, TilePos from, TilePos to) {
    std::vector<Tile16>& path = carrierPaths_[key];
    if (!path.empty()) return path;
    const int pi = w_->pathsOf[static_cast<std::size_t>(chains_.regionOf(key / 16))];
    path.push_back(tile16(from));
    if (pi >= 0) {
        RegionPaths& paths = w_->paths[static_cast<std::size_t>(pi)];
        Route r;
        std::array<Tile16, tl::kMoveReach + 2> desc{};
        int builds = 4;
        if (paths.plan(from, to, r, desc, builds) == PlanResult::Ok) {
            TilePos cur = from;
            TilePos nx;
            while (path.size() < 4096 && paths.next(r, cur, desc, nx)) {
                path.push_back(tile16(nx));
                cur = nx;
            }
        }
    }
    std::vector<float>& cum = carrierCum_[key];
    cum.assign(1, 0.0f);
    for (std::size_t k = 1; k < path.size(); ++k)
        cum.push_back(cum.back() + std::sqrt(dist2(smoothAlong(path, static_cast<float>(k - 1)),
                                                   smoothAlong(path, static_cast<float>(k)))));
    return path;
}

void CityLife::puppet(int i) {
    LiveActor& a = pool_[static_cast<std::size_t>(i)];
    if ((a.flags & live_flag::kFadeIn) != 0) {
        a.alpha =
            std::min(1.0f, a.alpha + static_cast<float>(tuning::kStepSeconds) / tl::kFadeSeconds);
        if (a.alpha >= 1.0f) a.flags = static_cast<std::uint8_t>(a.flags & ~live_flag::kFadeIn);
    }
    const auto place = [&](Vec2 p) {
        const TilePos t{static_cast<int>(std::floor(p.x)), static_cast<int>(std::floor(p.y))};
        if (map_->inBounds(t)) {
            a.tile = tile16(t);
            a.z = static_cast<float>(map_->floorZ(t));
        }
        a.pos = p;
        link(i);
    };
    switch (a.source) {
    case Source::Chain: {
        const ChainRun& run = chains_.run(static_cast<std::size_t>(a.a));
        const auto k = static_cast<std::size_t>(a.b);
        const auto stage = static_cast<std::size_t>(run.stageOf(k));
        const ChainStage& s = run.chain().stages[stage];
        const ChainWorker& wk = run.workers()[k];
        if (s.kind != ChainStage::Kind::Carry) {
            place(centre(run.place(s.slot).tile));
            const bool working =
                wk.phase == WorkerPhase::Work || s.kind == ChainStage::Kind::Source;
            const KindDef& kd = w_->data.kinds[a.kind];
            std::uint16_t anim = kAnimIdle;
            for (const char* name : {"work", "serve", "work_low", "haul"}) {
                const auto it = std::ranges::find(w_->data.animNames, std::string_view(name));
                if (it != w_->data.animNames.end() &&
                    kd.has(static_cast<int>(it - w_->data.animNames.begin()))) {
                    anim = static_cast<std::uint16_t>(it - w_->data.animNames.begin());
                    break;
                }
            }
            a.anim = working ? anim : kAnimIdle;
            a.goods = -1;
            a.goodsCount = 0;
            break;
        }
        // A carrier: where the formula has it on the way between the two places.
        const TilePos from = run.place(s.from).tile;
        const TilePos to = run.place(s.to).tile;
        const double travel = std::max(1.0, run.travel(stage));
        double f = 0;
        if (wk.phase == WorkerPhase::Out) f = 1.0 - std::clamp(wk.t / travel, 0.0, 1.0);
        if (wk.phase == WorkerPhase::Back) f = std::clamp(wk.t / travel, 0.0, 1.0);
        const std::size_t key =
            static_cast<std::size_t>(a.a) * 16 + std::min<std::size_t>(stage, 15);
        const std::vector<Tile16>& path = carrierPath(key, from, to);
        const std::vector<float>& cum = carrierCum_[key];
        const float idx = atLength(cum, static_cast<float>(f) * cum.back());
        place(smoothAlong(path, idx));
        const bool walking = wk.phase == WorkerPhase::Out || wk.phase == WorkerPhase::Back;
        a.anim = walking ? kAnimMove : kAnimIdle;
        a.goods = static_cast<std::int16_t>(wk.phase == WorkerPhase::Out ? s.goods : -1);
        a.goodsCount = static_cast<std::uint8_t>(wk.phase == WorkerPhase::Out ? wk.hand : 0);
        break;
    }
    case Source::Token: {
        const Token& tk = w_->data.tokens[static_cast<std::size_t>(a.a)];
        const auto inst = static_cast<std::size_t>(a.b / 64);
        const int member = a.b % 64;
        std::size_t first = 0;
        for (std::size_t t = 0; t < static_cast<std::size_t>(a.a); ++t)
            first += static_cast<std::size_t>(w_->data.tokens[t].count);
        TokenAt at;
        if (!tokenAt(static_cast<std::size_t>(a.a), static_cast<int>(inst - first), member, at) ||
            !active_.contains(TilePos{static_cast<int>(at.pos.x), static_cast<int>(at.pos.y)})) {
            if (materialising_)
                a.flags = 0;
            else
                release(i);
            return;
        }
        // Its hours over in view, it stands at the last rest stop it passed: there it fades in,
        // rather than popping across the road.
        if (!materialising_ && dist2(at.pos, a.pos) > tl::kTokenJump * tl::kTokenJump) {
            a.alpha = 0;
            a.flags |= live_flag::kFadeIn;
        }
        place(at.pos);
        a.anim = at.moving ? kAnimMove : kAnimIdle;
        if (tk.carry >= 0 && member > 0) {
            a.goods = static_cast<std::int16_t>(tk.carry);
            a.goodsCount = 1;
        }
        break;
    }
    case Source::Cast: {
        if (a.a < 0 || static_cast<std::size_t>(a.a) >= running_.size()) {
            if (materialising_)
                a.flags = 0;
            else
                release(i);
            return;
        }
        const RunningEvent& re = running_[static_cast<std::size_t>(a.a)];
        if (re.event < 0 || now_ >= re.end) {
            if (materialising_) {
                a.flags = 0;
            } else if (inView(a.pos)) {
                a.state = ActState::Leave;
                a.flags |= live_flag::kFadeOut;
                a.timer = tl::kLeaveTimeout;
            } else {
                release(i);
            }
            return;
        }
        const auto slot = static_cast<std::size_t>(a.a);
        const auto line = trail(re);
        const auto elapsed = static_cast<float>(now_ - re.start);
        const Event& ev = w_->data.regions[static_cast<std::size_t>(re.region)]
                              .events[static_cast<std::size_t>(re.event)];
        std::uint16_t perform = kAnimIdle;
        for (std::uint32_t st = w_->data.blocks[ev.steps].first;
             st < w_->data.blocks[ev.steps].first + w_->data.blocks[ev.steps].count; ++st)
            if (w_->data.steps[st].verb == Verb::Use) perform = w_->data.steps[st].anim;
        // The formation of its first group.
        Formation form = Formation::Line;
        float spacing = 0.9f;
        for (const CastEntry& c : ev.cast)
            if (c.group >= 0) {
                const Group& g = w_->data.regions[static_cast<std::size_t>(re.region)]
                                     .groups[static_cast<std::size_t>(c.group)];
                form = g.formation;
                spacing = g.spacing;
                break;
            }
        const auto ring = [&]() {
            // Gathered: a loose ring round the place.
            const double ang = unit(hashOf({a.key, 1})) * 2.0 * std::numbers::pi;
            const double rad = 0.8 + unit(hashOf({a.key, 2})) * 2.2;
            Vec2 p{re.place.x + static_cast<float>(std::cos(ang) * rad),
                   re.place.y + static_cast<float>(std::sin(ang) * rad)};
            const TilePos t{static_cast<int>(std::floor(p.x)), static_cast<int>(std::floor(p.y))};
            if (!map_->inBounds(t) || !map_->walkable(t))
                p = line.size() >= 2 ? smoothAlong(line, static_cast<float>(line.size() - 1))
                                     : re.place;
            return p;
        };
        if (line.size() >= 2) {
            const std::span<const float> cum{trailCum_.data() + slot * tl::kEventTrail, re.trail};
            // The leader's way along the route, stopping at relay stations.
            const Stops& stops = trailStops_[slot];
            float t = elapsed;
            float d = 0;
            bool done = false;
            for (std::uint8_t j = 0; j < stops.n && !done; ++j) {
                const float dj = cum[stops.at[j]];
                const float reach = (dj - d) / tl::kFormationSpeed;
                if (t < reach) {
                    d += t * tl::kFormationSpeed;
                    done = true;
                } else {
                    t -= reach;
                    d = dj;
                    if (t < tl::kStationDwell)
                        done = true;
                    else
                        t -= tl::kStationDwell;
                }
            }
            if (!done) d = std::min(cum.back(), d + t * tl::kFormationSpeed);
            const int member = a.b;
            const int rank = form == Formation::Pairs ? member / 2 : member;
            const float mine = d - static_cast<float>(rank + 1) * spacing;
            if (d >= cum.back() - 1e-3f && mine >= cum.back() - 6.0f * spacing) {
                place(ring());
                a.anim = perform;
            } else if (form == Formation::Cluster) {
                const Vec2 c = smoothAlong(line, atLength(cum, d));
                const double ang = unit(hashOf({a.key, 3})) * 2.0 * std::numbers::pi;
                const double rad = unit(hashOf({a.key, 4})) * spacing;
                Vec2 p{c.x + static_cast<float>(std::cos(ang) * rad),
                       c.y + static_cast<float>(std::sin(ang) * rad)};
                const TilePos tp{static_cast<int>(std::floor(p.x)),
                                 static_cast<int>(std::floor(p.y))};
                if (!map_->inBounds(tp) || !map_->walkable(tp)) p = c;
                place(p);
                a.anim = done && d < cum.back() ? kAnimIdle : kAnimMove;
            } else {
                const float idx = atLength(cum, std::max(0.0f, mine));
                Vec2 p = smoothAlong(line, idx);
                if (form == Formation::Pairs) {
                    // Two abreast: either side of the way.
                    const Vec2 ahead = smoothAlong(line, idx + 0.5f);
                    const Vec2 behind = smoothAlong(line, idx - 0.5f);
                    const float dx = ahead.x - behind.x;
                    const float dy = ahead.y - behind.y;
                    const float len = std::sqrt(dx * dx + dy * dy);
                    const float side = (member % 2 == 0 ? 1.0f : -1.0f) * tl::kPairsOffset;
                    if (len > 1e-3f) {
                        const Vec2 q{p.x - dy / len * side, p.y + dx / len * side};
                        const TilePos tq{static_cast<int>(std::floor(q.x)),
                                         static_cast<int>(std::floor(q.y))};
                        if (map_->inBounds(tq) && map_->walkable(tq)) p = q;
                    }
                }
                place(p);
                a.anim = mine > 0 && !done ? kAnimMove : kAnimIdle;
            }
        } else {
            place(ring());
            a.anim = perform;
        }
        break;
    }
    case Source::Population:
    case Source::Figure: break;
    }
}

// -- events --------------------------------------------------------------------------------------

void CityLife::dayPlan(int region, int day, int season,
                       std::vector<std::tuple<int, double, double>>& out) const {
    out.clear();
    season = seasonFor(day, season);
    const LifeRegion& reg = w_->data.regions[static_cast<std::size_t>(region)];
    const auto secondsAt = [&](double hour) {
        // Hours before 06:00 belong to the calendar day's early morning.
        const double t = std::fmod((hour - 6.0) / 24.0 + 1.0, 1.0);
        const double cycle = t < tuning::kMidnight ? t : t - 1.0;
        return static_cast<double>(day) * kDaySeconds + cycle * kDaySeconds;
    };
    const auto festivalOnDay = [&](int f) { return festivalOn(region, f, day, season); };
    for (std::size_t e = 0; e < reg.events.size(); ++e) {
        const Event& ev = reg.events[e];
        if (ev.trigger != Trigger::Window && ev.trigger != Trigger::Calendar) continue;
        const Filter& f = ev.when;
        if (f.every > 0 && day % f.every != f.offset) continue;
        if (f.seasons != 0 && (f.seasons & (1u << season)) == 0) continue;
        if (!dayPasses(f, day, season)) continue;
        // A season's turn comes once, at its first dawn (a month's turn by its month).
        if (ev.seasonTurn && f.months == 0 && day % std::max(1, w_->data.seasonDays) != 0) continue;
        if (f.festival >= 0 && !festivalOnDay(f.festival)) continue;
        if (f.notFestival >= 0 && festivalOnDay(f.notFestival)) continue;
        if (ev.trigger == Trigger::Calendar && ev.festival < 0) continue;
        // lifereport's day draw: hash64("<region>:<event>:<day>") % 1000 >= chance * 1000 skips.
        const std::string key = reg.id + ":" + ev.id + ":" + std::to_string(day);
        if (ev.chance < 1.0f && static_cast<double>(worldgenHash(key) % 1000) >=
                                    static_cast<double>(ev.chance) * 1000.0)
            continue;
        float from = f.hours ? f.from : 0.0f;
        float to = f.hours ? f.to : 24.0f;
        if (!f.hours && ev.trigger == Trigger::Calendar) {
            const Festival& fe = reg.festivals[static_cast<std::size_t>(ev.festival)];
            from = fe.from;
            to = fe.to;
        }
        double span = std::fmod(static_cast<double>(to - from) + 24.0, 24.0);
        if (span <= 0) span = 24.0;
        const auto add = [&](double startHour, int occ) {
            const double len =
                ev.dur0 +
                (ev.dur1 - ev.dur0) * unit(hashOf({seed_, 0xD0, static_cast<std::uint64_t>(region),
                                                   e, static_cast<std::uint64_t>(day),
                                                   static_cast<std::uint64_t>(occ)}));
            const double start = secondsAt(startHour);
            out.emplace_back(static_cast<int>(e), start, start + len);
        };
        if (ev.every > 0) {
            const double stepH = ev.every / 3600.0; // `every` is in game seconds
            for (int occ = 0; occ < 48 && static_cast<double>(occ) * stepH < span; ++occ)
                add(std::fmod(static_cast<double>(from) + static_cast<double>(occ) * stepH, 24.0),
                    occ);
        } else {
            const double u = unit(hashOf({seed_, 0x0FF, static_cast<std::uint64_t>(region), e,
                                          static_cast<std::uint64_t>(day)}));
            add(std::fmod(static_cast<double>(from) + u * span, 24.0), 0);
        }
    }
    std::ranges::sort(out,
                      [](const auto& x, const auto& y) { return std::get<1>(x) < std::get<1>(y); });
    // Large events never overlap in a region: a later one waits for the earlier to end.
    double largeEnd = -1e18;
    for (auto& [e, start, end] : out) {
        if (reg.events[static_cast<std::size_t>(e)].size != EventSize::Large) continue;
        if (start < largeEnd) {
            const double len = end - start;
            start = largeEnd;
            end = start + len;
        }
        largeEnd = end;
    }
    std::ranges::sort(out,
                      [](const auto& x, const auto& y) { return std::get<1>(x) < std::get<1>(y); });
}

void CityLife::planDay(int region, int day, bool continuing) {
    // Today's plan and yesterday's (its late events run past midnight).
    auto& plan = plans_[static_cast<std::size_t>(region)];
    dayPlan(region, day, clock_.season, plan);
    if (day > 0) {
        std::vector<std::tuple<int, double, double>>& prev = planScratch_;
        const int yesterdaySeason =
            clock_.season; // seasons turn at dawn: close enough for overruns
        dayPlan(region, day - 1, yesterdaySeason, prev);
        for (const auto& e : prev)
            if (std::get<2>(e) > now_) plan.push_back(e);
        std::ranges::sort(
            plan, [](const auto& x, const auto& y) { return std::get<1>(x) < std::get<1>(y); });
    }
    std::size_t k = 0;
    // A day that simply turned has already started what began before now.
    if (continuing)
        while (k < plan.size() && std::get<1>(plan[k]) <= now_) ++k;
    planNext_[static_cast<std::size_t>(region)] = k;
}

bool CityLife::eventRunning(int region, int event) const {
    return std::ranges::any_of(running_, [&](const RunningEvent& r) {
        return r.region == region && r.event == event && now_ < r.end;
    });
}

std::span<const Tile16> CityLife::trail(const RunningEvent& e) const {
    const auto slot = static_cast<std::size_t>(&e - running_.data());
    return {trails_.data() + slot * tl::kEventTrail, e.trail};
}

void CityLife::buildTrail(RunningEvent& re) {
    const auto slot = static_cast<std::size_t>(&re - running_.data());
    Tile16* buf = trails_.data() + slot * tl::kEventTrail;
    re.trail = 0;
    const Event& ev = w_->data.regions[static_cast<std::size_t>(re.region)]
                          .events[static_cast<std::size_t>(re.event)];
    const int pi = w_->pathsOf[static_cast<std::size_t>(re.region)];
    if (pi < 0) return;
    RegionPaths& paths = w_->paths[static_cast<std::size_t>(pi)];
    std::array<Tile16, tl::kMoveReach + 2> desc{};
    Stops& stops = trailStops_[slot];
    stops.n = 0;
    for (std::size_t k = 0; k + 1 < ev.route.size(); ++k) {
        const TilePos a = paths.nodeAt(ev.route[k]);
        const TilePos b = paths.nodeAt(ev.route[k + 1]);
        // A relay station on the way: the courier stops there for a fresh horse.
        if (k > 0 && re.trail > 0 && stops.n < stops.at.size() && paths.isStation(ev.route[k]))
            stops.at[stops.n++] = static_cast<std::uint16_t>(re.trail - 1);
        Route r;
        int builds = 4;
        if (paths.plan(a, b, r, desc, builds) != PlanResult::Ok) continue;
        if (re.trail == 0) buf[re.trail++] = tile16(a);
        TilePos cur = a;
        TilePos nx;
        while (re.trail < tl::kEventTrail && paths.next(r, cur, desc, nx)) {
            buf[re.trail++] = tile16(nx);
            cur = nx;
        }
    }
    // Lengths along the smoothed way, so a procession keeps an even pace on diagonals too.
    float* cum = trailCum_.data() + slot * tl::kEventTrail;
    if (re.trail > 0) cum[0] = 0;
    const std::span<const Tile16> line{buf, re.trail};
    for (std::uint32_t k = 1; k < re.trail; ++k)
        cum[k] = cum[k - 1] + std::sqrt(dist2(smoothAlong(line, static_cast<float>(k - 1)),
                                              smoothAlong(line, static_cast<float>(k))));
    re.length = static_cast<float>(re.trail);
    if (re.trail > 0) {
        re.place = centre(buf[re.trail - 1].pos());
        return;
    }
    // No route: where its first step happens, else the middle of its zone.
    TilePos at{-1, -1};
    for (std::uint32_t s = w_->data.blocks[ev.steps].first;
         s < w_->data.blocks[ev.steps].first + w_->data.blocks[ev.steps].count && at.x < 0; ++s) {
        const Target& t = w_->data.steps[s].target;
        if (t.kind == TargetKind::Node) at = paths.nodeAt(t.node);
    }
    if (at.x < 0 && !ev.route.empty()) at = paths.nodeAt(ev.route.front());
    if (at.x < 0 && !ev.zones.empty()) {
        for (const District& d : w_->data.regions[static_cast<std::size_t>(re.region)].districts) {
            if (d.map != ev.zones.front() || d.chunks.empty()) continue;
            const auto best =
                std::ranges::max_element(d.chunks, {}, [](const auto& c) { return c.second; });
            const auto cx = static_cast<std::uint32_t>(map_->chunksX());
            const TilePos c{static_cast<int>(best->first % cx) * kChunk + kChunk / 2,
                            static_cast<int>(best->first / cx) * kChunk + kChunk / 2};
            float bd = 1e9f;
            for (int y = c.y - kChunk / 2; y < c.y + kChunk / 2; ++y)
                for (int x = c.x - kChunk / 2; x < c.x + kChunk / 2; ++x)
                    if (map_->inBounds({x, y}) && map_->districtAt({x, y}) == d.map &&
                        map_->walkable({x, y})) {
                        const float dd = dist2(centre({x, y}), centre(c));
                        if (dd < bd) {
                            bd = dd;
                            at = {x, y};
                        }
                    }
        }
    }
    re.place = at.x >= 0 ? centre(at) : Vec2{-1, -1};
}

void CityLife::startEvent(int region, int event, double start, double end, int occurrence) {
    if (eventRunning(region, event)) return;
    // A free slot (trail buffers are per slot).
    std::size_t slot = running_.size();
    for (std::size_t k = 0; k < running_.size(); ++k)
        if (running_[k].event < 0) {
            slot = k;
            break;
        }
    if (slot == running_.size()) {
        if (running_.size() >= static_cast<std::size_t>(tl::kMaxRunningEvents)) return;
        running_.emplace_back();
    }
    RunningEvent& re = running_[slot];
    re = RunningEvent{region, event, start, end, occurrence, 0, 0, {}, false};
    buildTrail(re);
    const Event& ev =
        w_->data.regions[static_cast<std::size_t>(region)].events[static_cast<std::size_t>(event)];
    if (ev.sfx >= 0 && sounds_.size() < sounds_.capacity())
        sounds_.push_back({ev.sfx, false, re.place, region});
    // Lamps and torches lit, sluices opened: the `each` steps' items near the place, in turn.
    for (std::uint32_t s = w_->data.blocks[ev.steps].first;
         s < w_->data.blocks[ev.steps].first + w_->data.blocks[ev.steps].count; ++s) {
        const Step& st = w_->data.steps[s];
        if (st.verb != Verb::Each || st.eachItem < 0) continue;
        ItemState state = st.state;
        if (state == ItemState::None && st.count > 0) {
            const Block& body = w_->data.blocks[st.first];
            for (std::uint32_t k = body.first; k < body.first + body.count; ++k)
                if (w_->data.steps[k].state != ItemState::None) state = w_->data.steps[k].state;
        }
        if (state == ItemState::None) continue;
        const auto& items = w_->regionItems[static_cast<std::size_t>(region)];
        std::vector<std::pair<float, std::uint32_t>> near;
        for (auto it =
                 std::ranges::lower_bound(items, std::pair<std::uint32_t, std::uint32_t>(
                                                     static_cast<std::uint32_t>(st.eachItem), 0));
             it != items.end() && it->first == static_cast<std::uint32_t>(st.eachItem); ++it) {
            const Placed& p = map_->items()[it->second];
            const int dd = map_->districtAt({p.x, p.y});
            const bool inZone =
                ev.zones.empty() || std::ranges::find(ev.zones, dd) != ev.zones.end();
            if (inZone)
                near.emplace_back(re.place.x < 0 ? 0.0f : dist2(centre({p.x, p.y}), re.place),
                                  it->second);
        }
        std::ranges::sort(near);
        const std::size_t n =
            std::min<std::size_t>(near.size(), static_cast<std::size_t>(st.eachMax) *
                                                   std::max<std::size_t>(1, ev.zones.size()));
        // Lit until the next 06:00; opened and fired for the event.
        const double until = state == ItemState::Lit
                                 ? (std::floor((end + kDaySeconds) / kDaySeconds) * kDaySeconds)
                                 : end;
        for (std::size_t k = 0; k < n; ++k) {
            const double when =
                start + (end - start) * static_cast<double>(k + 1) / static_cast<double>(n + 1);
            if (when <= now_) setItemState(near[k].second, state, until);
        }
    }
}

void CityLife::setItemState(std::uint32_t item, ItemState s, double until) {
    if (item >= itemState_.size()) return;
    itemState_[item] = static_cast<std::uint8_t>(itemState_[item] | static_cast<std::uint8_t>(s));
    itemStateUntil_[item] = static_cast<float>(until);
}

std::uint8_t CityLife::itemState(std::uint32_t item) const {
    if (item >= itemState_.size()) return 0;
    return static_cast<double>(itemStateUntil_[item]) > now_ ? itemState_[item] : 0;
}

void CityLife::updateEvents() {
    // Scheduled starts (all regions, seen or not: the plan is the truth).
    for (std::size_t r = 0; r < plans_.size(); ++r) {
        auto& plan = plans_[r];
        std::size_t& k = planNext_[r];
        while (k < plan.size() && std::get<1>(plan[k]) <= now_) {
            const auto [e, start, end] = plan[k];
            if (end > now_) startEvent(static_cast<int>(r), e, start, end, static_cast<int>(k));
            ++k;
        }
    }
    // Ends, and what follows them.
    for (std::size_t s = 0; s < running_.size(); ++s) {
        RunningEvent& re = running_[s];
        if (re.event < 0 || now_ < re.end) continue;
        const int region = re.region;
        const int ended = re.event;
        re.event = -1;
        const LifeRegion& reg = w_->data.regions[static_cast<std::size_t>(region)];
        for (std::size_t e = 0; e < reg.events.size(); ++e) {
            const Event& ev = reg.events[e];
            if (ev.trigger != Trigger::After || ev.after != ended) continue;
            const double len =
                ev.dur0 +
                (ev.dur1 - ev.dur0) * unit(hashOf({seed_, 0xAF, static_cast<std::uint64_t>(region),
                                                   e, static_cast<std::uint64_t>(now_)}));
            startEvent(region, static_cast<int>(e), now_, now_ + len, 0);
        }
    }
    // Chains raising events (the kiln firing, the crane lifting a drum).
    for (const auto& [c, stage] : chains_.completions()) {
        const int region = chains_.regionOf(static_cast<std::size_t>(c));
        const LifeRegion& reg = w_->data.regions[static_cast<std::size_t>(region)];
        const int local = reg.findChain(chains_.run(static_cast<std::size_t>(c)).chain().id);
        for (std::size_t e = 0; e < reg.events.size(); ++e) {
            const Event& ev = reg.events[e];
            if (ev.trigger != Trigger::Chain || ev.chain != local || ev.chainStage != stage)
                continue;
            const double len = ev.dur0 + (ev.dur1 - ev.dur0) * 0.5;
            startEvent(region, static_cast<int>(e), now_, now_ + len, 0);
        }
    }
    // Reactive moments among live actors (a dog at the sausage counter), at most one start per
    // kEventStartGap in the area and per region a cooldown.
    if (frame_ % 60 == 0 && now_ - lastStart_ > tl::kEventStartGap) {
        for (std::size_t r = 0; r < w_->data.regions.size(); ++r) {
            if (now_ - reactiveCool_[r] < tl::kReactiveCooldown) continue;
            const LifeRegion& reg = w_->data.regions[r];
            for (std::size_t e = 0; e < reg.events.size(); ++e) {
                const Event& ev = reg.events[e];
                if (ev.trigger != Trigger::Reactive || ev.reactKind < 0 || ev.reactItem < 0)
                    continue;
                if (ev.when.hours && !inHours(ev.when.from, ev.when.to, hour_)) continue;
                for (std::size_t k = 0; k < pool_.size(); ++k) {
                    LiveActor& a = pool_[k];
                    if ((a.flags & live_flag::kAlive) == 0 || a.region != r ||
                        a.kind != ev.reactKind || a.source != Source::Population ||
                        (a.flags & live_flag::kInterrupt) != 0)
                        continue;
                    bool near = false;
                    map_->forEachItemIn({static_cast<int>(a.pos.x - ev.reactWithin),
                                         static_cast<int>(a.pos.y - ev.reactWithin),
                                         static_cast<int>(a.pos.x + ev.reactWithin) + 1,
                                         static_cast<int>(a.pos.y + ev.reactWithin) + 1},
                                        [&](std::uint32_t, const Placed& p) {
                                            if (static_cast<int>(p.info) == ev.reactItem)
                                                near = true;
                                        });
                    if (!near) continue;
                    // The event's steps, run by this actor; then its day goes on.
                    unreserve(static_cast<int>(k));
                    a.flags |= live_flag::kInterrupt;
                    a.stack[0] = {static_cast<std::uint16_t>(ev.steps), 0, 0};
                    a.depth = 1;
                    a.state = ActState::Idle;
                    a.timer = 0;
                    a.route = Route{};
                    tracks_[k].n = 0;
                    const double len = ev.dur0 + (ev.dur1 - ev.dur0) * 0.5;
                    startEvent(static_cast<int>(r), static_cast<int>(e), now_, now_ + len, 0);
                    reactiveCool_[r] = now_;
                    lastStart_ = now_;
                    break;
                }
            }
        }
    }
    // Which running events touch the active area.
    for (RunningEvent& re : running_) {
        if (re.event < 0) {
            re.active = false;
            continue;
        }
        bool touch = re.place.x >= 0 && active_.contains(TilePos{static_cast<int>(re.place.x),
                                                                 static_cast<int>(re.place.y)});
        for (const Tile16 t : trail(re))
            if (!touch && active_.contains(t.pos())) touch = true;
        if (touch != re.active) dirty_ = true;
        re.active = touch;
    }
}

void CityLife::updateTokens() {
    if (frame_ % 60 != 0) return; // arrivals checked once a second
    std::size_t inst = 0;
    stats_.tokens = 0;
    for (std::size_t t = 0; t < w_->data.tokens.size(); ++t) {
        const Token& tk = w_->data.tokens[t];
        const TokenState& ts = tokenPaths_[t];
        const bool on = tokenOn(tk);
        for (int k = 0; k < tk.count; ++k, ++inst) {
            if (!ts.ok || !on) {
                tokenLast_[inst] = {-1.0, 0.0}; // a day off: no arrival on its first step back
                continue;
            }
            ++stats_.tokens;
            const TokenPhase tp = tokenPhase(t, k);
            if (!tp.underway) {
                tokenLast_[inst] = {-1.0, 0.0}; // waiting: no arrival on its first step again
                continue;
            }
            const KindDef& kd = w_->data.kinds[static_cast<std::size_t>(tk.kind)];
            const float speed =
                !tk.lane.empty() ? tl::kShipSpeed : (kd.cart ? tl::kCartSpeed : tl::kWalkSpeed);
            const double run = ts.length / speed;
            const double phase = tp.phase;
            auto& last = tokenLast_[inst];
            const double before = last[0];
            last[0] = phase;
            if (before < 0) continue;
            // Arrived at the far end, or back at the start.
            int at = -1;
            if (before < tl::kPortStay + run && phase >= tl::kPortStay + run)
                at = static_cast<int>(ts.line.size()) - 1;
            if (phase < before) at = 0;
            if (at < 0) continue;
            const Vec2 p = ts.line[static_cast<std::size_t>(at)];
            const int lr = w_->data.regionOfWorld(
                map_->regionAt({static_cast<int>(p.x), static_cast<int>(p.y)}));
            const int region = lr >= 0 ? lr : tk.region;
            const LifeRegion& reg = w_->data.regions[static_cast<std::size_t>(region)];
            for (std::size_t e = 0; e < reg.events.size(); ++e) {
                const Event& ev = reg.events[e];
                if (ev.trigger != Trigger::TokenArrived || ev.tokenKind != tk.kind) continue;
                if (unit(hashOf({seed_, 0xA7, t, static_cast<std::uint64_t>(k),
                                 static_cast<std::uint64_t>(now_)})) >= ev.chance)
                    continue;
                const double len = ev.dur0 + (ev.dur1 - ev.dur0) * 0.5;
                startEvent(region, static_cast<int>(e), now_, now_ + len, 0);
            }
        }
    }
}

// -- drawing and counting ------------------------------------------------------------------------

std::size_t CityLife::gather(TileRect rect, float alpha, std::span<DrawActor> out) const {
    std::size_t n = 0;
    const TileRect r = rect.clipped(map_->bounds());
    if (r.empty()) return 0;
    for (int cy = r.y0 >> kChunkShift; cy <= (r.y1 - 1) >> kChunkShift; ++cy)
        for (int cx = r.x0 >> kChunkShift; cx <= (r.x1 - 1) >> kChunkShift; ++cx) {
            for (int i = chunkHead_[static_cast<std::size_t>(cy * map_->chunksX() + cx)]; i >= 0;
                 i = chunkNext_[static_cast<std::size_t>(i)]) {
                const LiveActor& a = pool_[static_cast<std::size_t>(i)];
                if (a.alpha <= 0.0f || !r.contains(a.tile.pos())) continue;
                if (n >= out.size()) return n;
                // Between its last two steps (everyone moves every step).
                const float f = std::clamp(alpha, 0.0f, 1.0f);
                DrawActor& d = out[n++];
                d.handle = {static_cast<std::uint16_t>(i), a.gen};
                d.pos = {a.prev.x + (a.pos.x - a.prev.x) * f, a.prev.y + (a.pos.y - a.prev.y) * f};
                d.z = a.prevZ + (a.z - a.prevZ) * f;
                d.stride = a.prevStride + (a.stride - a.prevStride) * f;
                // Its speed over the ground while drawn walking (never under the renderer's
                // threshold, so a walk is always phased by the distance covered), else none.
                d.speed =
                    (a.body & body_flag::kWalking) != 0 ? std::max(a.shown, tl::kShownStop) : 0.0f;
                d.heading = a.heading;
                d.level = static_cast<std::uint8_t>(map_->level(a.tile.pos()));
                d.facing = a.facing;
                d.kind = a.kind;
                d.variant = a.variant;
                d.anim = shownAnim(a);
                d.animTime = a.animTime;
                d.alpha = a.alpha;
                d.goods = a.goods;
                d.goodsCount = a.goodsCount;
                d.translucent = (a.flags & live_flag::kTranslucent) != 0;
                d.role = a.role;
                d.region = a.region;
                const int item = map_->itemAt(a.tile.pos());
                d.item = item;
                d.floor =
                    item >= 0 && map_->info(map_->items()[static_cast<std::size_t>(item)]).landmark;
            }
        }
    return n;
}

void CityLife::countBodies() {
    stats_.marching = stats_.oscillating = stats_.stuck = stats_.waiting = stats_.lost = 0;
    for (const LiveActor& a : pool_) {
        if ((a.flags & live_flag::kAlive) == 0 || a.alpha <= 0.0f) continue;
        stats_.marching += (a.body & body_flag::kMarching) != 0 ? 1 : 0;
        stats_.oscillating += (a.body & body_flag::kOscillating) != 0 ? 1 : 0;
        stats_.stuck += (a.body & body_flag::kStuck) != 0 ? 1 : 0;
        stats_.waiting +=
            (a.body & body_flag::kWalking) == 0 && a.state != ActState::Inside ? 1 : 0;
        stats_.lost += a.stall > tl::kStallGiveUp + tl::kProgressWindow ? 1 : 0;
    }
}

void CityLife::countDistricts() {
    for (DistrictCount& dc : counts_) {
        dc.live = 0;
        dc.inside = 0;
    }
    int visible = 0;
    std::array<int, 5> by{};
    int live = 0;
    for (const LiveActor& a : pool_) {
        if ((a.flags & live_flag::kAlive) == 0) continue;
        ++live;
        ++by[static_cast<std::size_t>(a.source)];
        const bool vis = a.state != ActState::Inside && a.alpha > 0.0f;
        if (vis) ++visible;
        if (a.source != Source::Population || a.state == ActState::Leave) continue;
        for (DistrictCount& dc : counts_)
            if (dc.region == a.region && dc.district == a.district) {
                if (vis)
                    ++dc.live;
                else
                    ++dc.inside;
            }
    }
    stats_.live = live;
    stats_.visible = visible;
    stats_.bySource = by;
    int tablesBuilt = 0;
    for (const RegionPaths& p : w_->paths) tablesBuilt += p.tablesBuilt();
    stats_.tablesBuilt = tablesBuilt;
    int tokensLive = by[static_cast<std::size_t>(Source::Token)];
    stats_.tokensLive = tokensLive;
}

std::size_t CityLife::memoryBytes() const {
    return pool_.capacity() * sizeof(LiveActor) + desc_.capacity() * sizeof(desc_[0]) +
           (chunkHead_.capacity() + chunkNext_.capacity() + chunkOf_.capacity()) * sizeof(int) +
           keys_->keys.capacity() * 12 +
           (desires_.capacity() + queue_.capacity()) * sizeof(Desire) + groupCount_.capacity() +
           spotUse_.capacity() + itemState_.capacity() * 5 + trails_.capacity() * sizeof(Tile16) +
           chains_.memoryBytes();
}

} // namespace lc::life
