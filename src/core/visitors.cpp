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

} // namespace

int desiredCount(const VisitorDef& def, const World& world, bool night) {
    if (!timeAllows(def.time, night)) return 0;
    // The weakest need sets how strongly the corner attracts this visitor.
    double ratio = 1e9;
    for (const auto& n : def.terrainNeeds)
        ratio = std::min(ratio, static_cast<double>(world.terrainCount(n.index)) / n.count);
    for (const auto& n : def.itemNeeds)
        ratio = std::min(ratio, static_cast<double>(world.itemCount(n.index)) / n.count);
    if (!def.anyItems.empty()) {
        int sum = 0;
        for (const auto& n : def.anyItems) sum += world.itemCount(n.index) * n.count;
        ratio = std::min(ratio, static_cast<double>(sum) / def.anyTotal);
    }
    if (ratio < 1.0) return 0;
    const int count = static_cast<int>(std::floor(ratio * tuning::kVisitorsPerNeed));
    return std::clamp(count, 1, def.max);
}

bool habitatAllows(Habitat h, const World& world, const Catalog& cat, Vec2 p) {
    const TilePos t{static_cast<int>(std::floor(p.x)), static_cast<int>(std::floor(p.y))};
    if (!world.inBounds(t)) return false;
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
}

int Visitors::present(int visitor) const {
    return static_cast<int>(std::ranges::count_if(
        critters_, [&](const Critter& c) { return c.visitor == visitor && !c.leaving; }));
}

bool Visitors::pickAnchor(const World& world, const Catalog& cat, int visitor, Rng& rng,
                          TilePos& out) const {
    const auto& def = cat.visitors[static_cast<std::size_t>(visitor)];
    // Reservoir sampling over everything that attracts this visitor: no allocation.
    int seen = 0;
    const auto offer = [&](TilePos p) {
        if (rng.range(0, seen++) == 0) out = p;
    };
    for (const Item& it : world.items()) {
        const auto matches = [&](const std::vector<Amount>& list) {
            return std::ranges::any_of(list, [&](const Amount& a) { return a.index == it.type; });
        };
        if (matches(def.itemNeeds) || matches(def.anyItems)) offer(it.pos);
    }
    if (!def.terrainNeeds.empty()) {
        for (int y = 0; y < world.height(); ++y)
            for (int x = 0; x < world.width(); ++x)
                for (const auto& n : def.terrainNeeds)
                    if (world.terrainAt({x, y}) == n.index) offer({x, y});
    }
    return seen > 0;
}

bool Visitors::pickTarget(const World& world, const Catalog& cat, Critter& c, Rng& rng) const {
    const auto& def = cat.visitors[c.visitor];
    TilePos anchor{static_cast<int>(c.pos.x), static_cast<int>(c.pos.y)};
    // Mostly drift around the current spot, sometimes head back to what attracted us.
    if (rng.chance(0.35f)) (void)pickAnchor(world, cat, c.visitor, rng, anchor);
    for (int attempt = 0; attempt < 8; ++attempt) {
        const int r = tuning::kWanderRadius;
        const Vec2 cand{static_cast<float>(anchor.x + rng.range(-r, r)) + rng.range(0.2f, 0.8f),
                        static_cast<float>(anchor.y + rng.range(-r, r)) + rng.range(0.2f, 0.8f)};
        if (habitatAllows(def.habitat, world, cat, cand) &&
            pathClear(def.habitat, world, cat, c.pos, cand)) {
            c.target = cand;
            return true;
        }
    }
    return false;
}

bool Visitors::spawn(const World& world, const Catalog& cat, int visitor, Rng& rng, bool instant) {
    const auto& def = cat.visitors[static_cast<std::size_t>(visitor)];
    TilePos anchor;
    if (!pickAnchor(world, cat, visitor, rng, anchor)) return false;
    for (int attempt = 0; attempt < 16; ++attempt) {
        const int r = attempt < 8 ? 1 : tuning::kWanderRadius;
        const Vec2 p{static_cast<float>(anchor.x + rng.range(-r, r)) + rng.range(0.25f, 0.75f),
                     static_cast<float>(anchor.y + rng.range(-r, r)) + rng.range(0.25f, 0.75f)};
        if (!habitatAllows(def.habitat, world, cat, p)) continue;
        Critter c;
        c.visitor = static_cast<std::uint8_t>(visitor);
        c.pos = c.target = p;
        c.alpha = instant ? 1.0f : 0.0f;
        c.timer = rng.range(0.2f, tuning::kIdleMin);
        c.animTime = rng.range(0.0f, 10.0f);
        c.hover = def.habitat == Habitat::Air ? rng.range(8.0f, 18.0f) : 0.0f;
        c.facing = static_cast<Facing>(rng.range(0, 3));
        critters_.push_back(c);
        return true;
    }
    return false;
}

void Visitors::populate(const World& world, const Catalog& cat, bool night, Rng& rng) {
    critters_.clear();
    for (std::size_t v = 0; v < cat.visitors.size(); ++v) {
        const int want = desiredCount(cat.visitors[v], world, night);
        for (int i = 0; i < want; ++i) (void)spawn(world, cat, static_cast<int>(v), rng, true);
        cooldown_[v] = tuning::kArrivalInterval;
    }
}

void Visitors::update(const World& world, const Catalog& cat, bool night, float dt, Rng& rng) {
    events_.clear();

    for (std::size_t v = 0; v < cat.visitors.size(); ++v) {
        const auto& def = cat.visitors[v];
        const int vi = static_cast<int>(v);
        const int want = desiredCount(def, world, night);
        const int have = present(vi);
        cooldown_[v] = std::max(0.0f, cooldown_[v] - dt);
        // The first visitor of a kind shows up quickly once its needs are met.
        if (have == 0 && want > 0)
            cooldown_[v] = std::min(cooldown_[v], tuning::kFirstArrivalDelay);
        if (have < want && cooldown_[v] <= 0.0f) {
            if (spawn(world, cat, vi, rng, false)) {
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
            events_.push_back({VisitorEvent::Kind::Call, vi, false, it->pos});
        }
    }

    for (Critter& c : critters_) {
        const auto& def = cat.visitors[c.visitor];
        c.animTime += dt;
        if (!habitatAllows(def.habitat, world, cat, c.pos)) c.leaving = true;
        const float fade = dt / tuning::kFadeSeconds;
        c.alpha = c.leaving ? c.alpha - fade : std::min(1.0f, c.alpha + fade);

        if (c.moving) {
            const Vec2 d{c.target.x - c.pos.x, c.target.y - c.pos.y};
            const float dist = std::hypot(d.x, d.y);
            const float step = speedOf(def.habitat) * dt;
            if (dist <= step) {
                c.pos = c.target;
                c.moving = false;
                const float idleMax =
                    def.habitat == Habitat::Air ? tuning::kAirIdleMax : tuning::kIdleMax;
                c.timer = rng.range(tuning::kIdleMin * 0.5f, idleMax);
            } else {
                c.pos.x += d.x / dist * step;
                c.pos.y += d.y / dist * step;
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
