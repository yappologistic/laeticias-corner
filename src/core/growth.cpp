#include "core/growth.hpp"

#include "core/tuning.hpp"

#include <algorithm>

namespace lc {

float growthRate(const World& world, const Catalog& cat, TileRect rect, bool raining,
                 float seasonGrowth, float nook) {
    float season = seasonGrowth;
    if (season < 1.0f) {
        // A greenhouse (or anything sheltering) nearby keeps the beds growing through winter.
        bool sheltered = false;
        world.forEachItemIn({rect.x0 - 8, rect.y0 - 8, rect.x1 + 8, rect.y1 + 8},
                            [&](const Item& it) {
                                const int r = cat.items[it.type].shelter;
                                if (r > 0 && TileRect{it.pos.x - r, it.pos.y - r,
                                                      it.pos.x + it.w + r, it.pos.y + it.h + r}
                                                 .intersects(rect))
                                    sheltered = true;
                            });
        if (sheltered) season = 1.0f;
    }
    return season * (raining ? tuning::kRainGrowth : 1.0f) * nook;
}

bool grow(World& world, const Catalog& cat, std::size_t index, float seconds, float rate) {
    const Item& it = world.items()[index];
    const Growth& g = cat.items[it.type].growth;
    if (g.stages == 0 || it.stage + 1 >= g.stages || rate <= 0.0f) return false;
    float progress = it.growth + seconds * rate / g.seconds;
    int stage = it.stage;
    bool next = false;
    while (progress >= 1.0f && stage + 1 < g.stages) {
        progress -= 1.0f;
        ++stage;
        next = true;
    }
    if (stage + 1 >= g.stages) progress = 0.0f; // ripe stays ripe
    world.setGrowth(index, stage, progress);
    return next;
}

bool ripe(const Catalog& cat, const Item& item) {
    const Growth& g = cat.items[item.type].growth;
    return g.harvest && g.stages > 0 && item.stage + 1 == g.stages;
}

void harvest(World& world, std::size_t index) {
    world.setGrowth(index, 0, 0.0f);
}

} // namespace lc
