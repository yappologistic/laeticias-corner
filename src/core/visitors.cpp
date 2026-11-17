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

TilePos tileOf(Vec2 p) {
    return {static_cast<int>(std::floor(p.x)), static_cast<int>(std::floor(p.y))};
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

int desiredCount(const VisitorDef& def, const Tally& tally, bool night, VisitorGate gate) {
    if (!gate.allowed || !timeAllows(def.time, night)) return 0;
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
    return static_cast<int>(std::clamp(count, 1.0, static_cast<double>(def.max + gate.extra)));
}

bool habitatAllows(Habitat h, const World& world, const Catalog& cat, Vec2 p) {
    const TilePos t = tileOf(p);
    if (!world.hasGround(t) || world.isWild(t)) return false;
    if (h == Habitat::Air) return true;
    const Item* item = world.itemAt(t);
    if (item != nullptr && !cat.items[item->type].walkable) return false;
    if (h != Habitat::Shore) return world.isWater(t) == (h == Habitat::Water);
    // The shore: water beside open land, or land beside water.
    const bool water = world.isWater(t);
    for (const TilePos d : {TilePos{1, 0}, TilePos{-1, 0}, TilePos{0, 1}, TilePos{0, -1}}) {
        const TilePos q{t.x + d.x, t.y + d.y};
        if (world.hasGround(q) && !world.isWild(q) && world.isWater(q) != water) return true;
    }
    return false;
}

} // namespace lc
