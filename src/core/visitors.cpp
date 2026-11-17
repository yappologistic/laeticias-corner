#include "core/visitors.hpp"

#include "core/tuning.hpp"

#include <algorithm>
#include <cmath>

namespace lc {
namespace {

bool timeAllows(VisitTime t, bool night) {
    switch (t) {
    case VisitTime::Any: return true;
    case VisitTime::Day: return !night;
    case VisitTime::Night: return night;
    }
    return false;
}

float speedOf(Habitat h) {
    switch (h) {
    case Habitat::Land: return tuning::kLandSpeed;
    case Habitat::Water: return tuning::kWaterSpeed;
    case Habitat::Air: return tuning::kAirSpeed;
    }
    return 1;
}

Facing facingFor(Vec2 d) {
    if (std::abs(d.x) >= std::abs(d.y)) return d.x >= 0 ? Facing::Front : Facing::BackMirrored;
    return d.y >= 0 ? Facing::FrontMirrored : Facing::Back;
}

TilePos tileOf(Vec2 p) {
    return {static_cast<int>(std::floor(p.x)), static_cast<int>(std::floor(p.y))};
}

bool pathClear(Habitat h, const World& world, const Catalog& cat, Vec2 a, Vec2 b) {
    if (h == Habitat::Air) return true;
    const float len = std::hypot(b.x - a.x, b.y - a.y);
    const int steps = std::max(1, static_cast<int>(len / 0.2f));
    for (int i = 1; i <= steps; ++i) {
        const float k = static_cast<float>(i) / static_cast<float>(steps);
        if (!habitatAllows(h, world, cat, {a.x + (b.x - a.x) * k, a.y + (b.y - a.y) * k}))
            return false;
    }
    return true;
}

bool inArea(const TileRect& area, Vec2 p) {
    return area.contains(tileOf(p));
}

} // namespace

void tallyArea(const World& world, const Catalog& cat, TileRect area, Tally& out) {
    out.terrain.assign(cat.terrain.size(), 0);
    out.items.assign(cat.items.size(), 0);
    world.forEachChunkIn(area, [&](int cx, int cy) {
        for (std::size_t t = 0; t < out.terrain.size(); ++t)
            out.terrain[t] += world.chunkTerrainCount(cx, cy, static_cast<int>(t));
        for (std::size_t i = 0; i < out.items.size(); ++i)
            out.items[i] += world.chunkItemCount(cx, cy, static_cast<int>(i));
    });
}

int desiredCount(const VisitorDef& def, const Tally& tally, bool night) {
    if (!timeAllows(def.time, night)) return 0;
    const auto terrain = [&](int i) { return tally.terrain[static_cast<std::size_t>(i)]; };
    const auto items = [&](int i) { return tally.items[static_cast<std::size_t>(i)]; };
    // The weakest need sets how strongly the area attracts this visitor.
    double ratio = 1e9;
    for (const auto& n : def.terrainNeeds)
        ratio = std::min(ratio, static_cast<double>(terrain(n.index)) / n.count);
    for (const auto& n : def.itemNeeds)
        ratio = std::min(ratio, static_cast<double>(items(n.index)) / n.count);
    if (!def.anyItems.empty()) {
        long long sum = 0;
        for (const auto& n : def.anyItems) sum += static_cast<long long>(items(n.index)) * n.count;
        ratio = std::min(ratio, static_cast<double>(sum) / def.anyTotal);
    }
    if (ratio < 1.0) return 0;
    const double count = std::floor(ratio * tuning::kVisitorsPerNeed);
    return static_cast<int>(std::clamp(count, 1.0, static_cast<double>(def.max)));
}

bool habitatAllows(Habitat h, const World& world, const Catalog& cat, Vec2 p) {
    const TilePos t = tileOf(p);
    if (!world.hasGround(t)) return false;
    if (h == Habitat::Air) return true;
    const Item* item = world.itemAt(t);
    if (item != nullptr && !cat.items[item->type].walkable) return false;
    return world.isWater(t) == (h == Habitat::Water);
}

Visitors::Visitors(const Catalog& cat)
    : seen_(cat.visitors.size(), false), cooldown_(cat.visitors.size(), 0.0f) {
    std::size_t cap = 0;
    for (const auto& v : cat.visitors) cap += static_cast<std::size_t>(v.max);
    critters_.reserve(cap);
    events_.reserve(cap + cat.visitors.size());
    tally_.terrain.reserve(cat.terrain.size());
    tally_.items.reserve(cat.items.size());
}

int Visitors::present(int visitor) const {
    return static_cast<int>(std::ranges::count_if(
        critters_, [&](const Critter& c) { return c.visitor == visitor && !c.leaving; }));
}

bool Visitors::pickAnchor(const World& world, const Catalog& cat, int visitor, Rng& rng,
                          TilePos& out) const {
    const auto& def = cat.visitors[static_cast<std::size_t>(visitor)];
    // Reservoir sampling over everything in the area that attracts this visitor: no allocation.
    int seen = 0;
    const auto offer = [&](TilePos p) {
        if (rng.range(0, seen++) == 0) out = p;
    };
    const auto matches = [&](const std::vector<Amount>& list, int type) {
        return std::ranges::any_of(list, [&](const Amount& a) { return a.index == type; });
    };
    world.forEachItemIn(area_, [&](const Item& it) {
        if (area_.contains(it.pos) &&
            (matches(def.itemNeeds, it.type) || matches(def.anyItems, it.type)))
            offer(it.pos);
    });
    for (const auto& n : def.terrainNeeds) {
        world.forEachChunkIn(area_, [&](int cx, int cy) {
            if (world.chunkTerrainCount(cx, cy, n.index) == 0) return;
            const TileRect r =
                TileRect{cx * kChunk, cy * kChunk, (cx + 1) * kChunk, (cy + 1) * kChunk}.clipped(
                    area_.clipped(world.bounds()));
            for (int y = r.y0; y < r.y1; ++y)
                for (int x = r.x0; x < r.x1; ++x)
                    if (world.terrainAt({x, y}) == n.index) offer({x, y});
        });
    }
    return seen > 0;
}

bool Visitors::pickTarget(const World& world, const Catalog& cat, Critter& c, Rng& rng) const {
    const auto& def = cat.visitors[c.visitor];
    TilePos anchor = tileOf(c.pos);
    // Mostly drift around the current spot, sometimes head back to what attracted us.
    if (rng.chance(tuning::kReturnToAnchorChance))
        (void)pickAnchor(world, cat, c.visitor, rng, anchor);
    for (int attempt = 0; attempt < tuning::kTargetAttempts; ++attempt) {
        const int r = tuning::kWanderRadius;
        const Vec2 cand{static_cast<float>(anchor.x + rng.range(-r, r)) + rng.range(0.2f, 0.8f),
                        static_cast<float>(anchor.y + rng.range(-r, r)) + rng.range(0.2f, 0.8f)};
        if (inArea(area_, cand) && habitatAllows(def.habitat, world, cat, cand) &&
            pathClear(def.habitat, world, cat, c.pos, cand)) {
            c.target = cand;
            return true;
        }
    }
    return false;
}

bool Visitors::escape(const World& world, const Catalog& cat, Critter& c) const {
    const auto& def = cat.visitors[c.visitor];
    const TilePos t = tileOf(c.pos);
    float best = 1e9f;
    for (int dy = -1; dy <= 1; ++dy) {
        for (int dx = -1; dx <= 1; ++dx) {
            const Vec2 cand{static_cast<float>(t.x + dx) + 0.5f,
                            static_cast<float>(t.y + dy) + 0.5f};
            if ((dx == 0 && dy == 0) || !habitatAllows(def.habitat, world, cat, cand)) continue;
            const float d = std::hypot(cand.x - c.pos.x, cand.y - c.pos.y);
            if (d < best) {
                best = d;
                c.target = cand;
            }
        }
    }
    if (best >= 1e9f) return false;
    c.moving = true;
    return true;
}

bool Visitors::spawn(const World& world, const Catalog& cat, int visitor, Rng& rng, float alpha) {
    const auto& def = cat.visitors[static_cast<std::size_t>(visitor)];
    TilePos anchor;
    if (!pickAnchor(world, cat, visitor, rng, anchor)) return false;
    for (int attempt = 0; attempt < tuning::kSpawnAttempts; ++attempt) {
        const int r = attempt < tuning::kSpawnAttempts / 2 ? 1 : tuning::kWanderRadius;
        const Vec2 p{static_cast<float>(anchor.x + rng.range(-r, r)) + rng.range(0.25f, 0.75f),
                     static_cast<float>(anchor.y + rng.range(-r, r)) + rng.range(0.25f, 0.75f)};
        if (!inArea(area_, p) || !habitatAllows(def.habitat, world, cat, p)) continue;
        Critter c;
        c.visitor = static_cast<std::uint8_t>(visitor);
        c.pos = c.target = p;
        c.alpha = alpha;
        c.timer = rng.range(0.2f, tuning::kIdleMin);
        c.animTime = rng.range(0.0f, 10.0f);
        c.hover =
            def.habitat == Habitat::Air ? rng.range(tuning::kHoverMin, tuning::kHoverMax) : 0.0f;
        c.facing = static_cast<Facing>(rng.range(0, 3));
        critters_.push_back(c);
        return true;
    }
    return false;
}

void Visitors::populate(const World& world, const Catalog& cat, bool night, Rng& rng,
                        TileRect area) {
    critters_.clear();
    area_ = area;
    tallyArea(world, cat, area_, tally_);
    tallyRevision_ = world.revision();
    for (std::size_t v = 0; v < cat.visitors.size(); ++v) {
        // Kinds never seen arrive the normal way, so their first sighting is still an event.
        if (!seen(static_cast<int>(v))) continue;
        const int want = desiredCount(cat.visitors[v], tally_, night);
        for (int i = 0; i < want; ++i) (void)spawn(world, cat, static_cast<int>(v), rng, 1.0f);
        cooldown_[v] = tuning::kArrivalInterval;
    }
}

void Visitors::update(const World& world, const Catalog& cat, bool night, float dt, Rng& rng,
                      TileRect area) {
    events_.clear();
    const bool moved = area != area_;
    if (moved) {
        area_ = area;
        std::erase_if(critters_, [&](const Critter& c) { return !inArea(area_, c.pos); });
    }
    if (moved || tallyRevision_ != world.revision()) {
        tallyArea(world, cat, area_, tally_);
        tallyRevision_ = world.revision();
    }

    for (std::size_t v = 0; v < cat.visitors.size(); ++v) {
        const auto& def = cat.visitors[v];
        const int vi = static_cast<int>(v);
        const int want = desiredCount(def, tally_, night);
        int have = present(vi);
        if (moved && seen(vi)) {
            // Familiar faces are simply there when the view comes back.
            for (; have < want && spawn(world, cat, vi, rng, 0.0f); ++have) {}
        }
        cooldown_[v] = std::max(0.0f, cooldown_[v] - dt);
        // The first visitor of a kind shows up quickly once its needs are met.
        if (have == 0 && want > 0)
            cooldown_[v] = std::min(cooldown_[v], tuning::kFirstArrivalDelay);
        if (have < want && cooldown_[v] <= 0.0f) {
            if (spawn(world, cat, vi, rng, 0.0f)) {
                const bool first = !seen(vi);
                markSeen(vi);
                events_.push_back({VisitorEvent::Kind::Arrived, vi, first, critters_.back().pos});
            }
            cooldown_[v] = tuning::kArrivalInterval;
        } else if (have > want && cooldown_[v] <= 0.0f) {
            const auto it = std::ranges::find_if(
                critters_, [&](const Critter& c) { return c.visitor == v && !c.leaving; });
            if (it != critters_.end()) it->leaving = true;
            cooldown_[v] = tuning::kDepartureInterval;
        }
        if (have > 0 && !def.voice.empty() && rng.chance(tuning::kVoiceChancePerSecond * dt)) {
            const auto it =
                std::ranges::find_if(critters_, [&](const Critter& c) { return c.visitor == v; });
            if (it != critters_.end())
                events_.push_back({VisitorEvent::Kind::Call, vi, false, it->pos});
        }
    }

    for (Critter& c : critters_) {
        const auto& def = cat.visitors[c.visitor];
        c.animTime += dt;
        // The ground changed under it (an edit): walk off to an allowed tile, or leave.
        if (!c.leaving && !habitatAllows(def.habitat, world, cat, c.pos) &&
            !(c.moving && habitatAllows(def.habitat, world, cat, c.target)) &&
            !escape(world, cat, c))
            c.leaving = true;
        const float fade = dt / tuning::kFadeSeconds;
        c.alpha = c.leaving ? c.alpha - fade : std::min(1.0f, c.alpha + fade);

        if (c.moving) {
            const Vec2 d{c.target.x - c.pos.x, c.target.y - c.pos.y};
            const float dist = std::hypot(d.x, d.y);
            const float step = speedOf(def.habitat) * dt;
            const Vec2 next = dist <= step
                                  ? c.target
                                  : Vec2{c.pos.x + d.x / dist * step, c.pos.y + d.y / dist * step};
            // Never step onto a tile that became off-limits since the walk was planned.
            if (!(tileOf(next) == tileOf(c.pos)) && !habitatAllows(def.habitat, world, cat, next)) {
                c.moving = false;
                c.timer = tuning::kIdleMin * 0.25f;
            } else if (dist <= step) {
                c.pos = c.target;
                c.moving = false;
                const float idleMax =
                    def.habitat == Habitat::Air ? tuning::kAirIdleMax : tuning::kIdleMax;
                c.timer = rng.range(tuning::kIdleMin * 0.5f, idleMax);
            } else {
                c.pos = next;
                c.facing = facingFor(d);
            }
        } else {
            c.timer -= dt;
            if (c.timer <= 0) {
                if (pickTarget(world, cat, c, rng)) {
                    c.moving = true;
                } else {
                    c.timer = rng.range(tuning::kIdleMin, tuning::kIdleMax);
                }
            }
        }
    }
    std::erase_if(critters_, [](const Critter& c) { return c.leaving && c.alpha <= 0.0f; });
}

} // namespace lc
