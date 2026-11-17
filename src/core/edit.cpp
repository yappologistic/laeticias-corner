#include "core/edit.hpp"

#include <ranges>

namespace lc {
namespace {

bool surfaceAllows(Surface s, bool water) {
    switch (s) {
    case Surface::Land: return !water;
    case Surface::Water: return water;
    case Surface::Any: return true;
    }
    return false;
}

// Applies op in the given direction without validation: ops are only ever replayed in the exact
// state they were recorded from, which keeps undo/redo exact.
void apply(World& world, const Op& op, bool forward) {
    switch (op.kind) {
    case Op::Kind::Terrain: world.setTerrain(op.pos, forward ? op.to : op.from); break;
    case Op::Kind::Add:
    case Op::Kind::Remove:
        if ((op.kind == Op::Kind::Add) == forward)
            world.addItem(op.item);
        else if (const auto idx = world.itemIndexAt(op.item.pos))
            world.removeItem(*idx);
        break;
    }
}

Op inverted(const Op& op) {
    Op inv = op;
    if (op.kind == Op::Kind::Terrain)
        std::swap(inv.from, inv.to);
    else
        inv.kind = op.kind == Op::Kind::Add ? Op::Kind::Remove : Op::Kind::Add;
    return inv;
}

} // namespace

PlaceResult canPlace(const World& world, const Catalog& cat, const Item& item) {
    const auto& def = cat.items[item.type];
    for (int y = item.pos.y; y < item.pos.y + item.h; ++y) {
        for (int x = item.pos.x; x < item.pos.x + item.w; ++x) {
            if (!world.inBounds({x, y})) return PlaceResult::OutOfBounds;
        }
    }
    for (int y = item.pos.y; y < item.pos.y + item.h; ++y) {
        for (int x = item.pos.x; x < item.pos.x + item.w; ++x) {
            if (world.itemAt({x, y}) != nullptr) return PlaceResult::Occupied;
        }
    }
    for (int y = item.pos.y; y < item.pos.y + item.h; ++y) {
        for (int x = item.pos.x; x < item.pos.x + item.w; ++x) {
            if (!surfaceAllows(def.on, world.isWater({x, y})))
                return def.on == Surface::Water ? PlaceResult::NeedsWater : PlaceResult::NeedsLand;
        }
    }
    return PlaceResult::Ok;
}

PaintResult canPaint(const World& world, const Catalog& cat, TilePos p, int terrain) {
    if (!world.inBounds(p)) return PaintResult::OutOfBounds;
    if (world.terrainAt(p) == terrain) return PaintResult::Unchanged;
    if (const Item* it = world.itemAt(p)) {
        const bool water = terrain == cat.waterTerrain;
        if (!surfaceAllows(cat.items[it->type].on, water)) return PaintResult::BlockedByItem;
    }
    return PaintResult::Ok;
}

void Editor::begin() {
    commit();
    grouping_ = true;
}

void Editor::commit() {
    grouping_ = false;
    if (!pending_.empty()) push(std::move(pending_));
    pending_.clear();
}

void Editor::push(std::vector<Op>&& step) {
    undo_.push_back(std::move(step));
    if (undo_.size() > maxSteps_) undo_.erase(undo_.begin());
    redo_.clear();
}

void Editor::record(const Op& op) {
    if (grouping_) {
        pending_.push_back(op);
    } else {
        push(std::vector<Op>{op});
    }
}

PlaceResult Editor::place(World& world, const Catalog& cat, const Item& item) {
    const auto r = canPlace(world, cat, item);
    if (r != PlaceResult::Ok) return r;
    world.addItem(item);
    record(Op::items(Op::Kind::Add, item));
    return r;
}

bool Editor::remove(World& world, TilePos p) {
    const auto idx = world.itemIndexAt(p);
    if (!idx) return false;
    const Item removed = world.removeItem(*idx);
    record(Op::items(Op::Kind::Remove, removed));
    return true;
}

PaintResult Editor::paint(World& world, const Catalog& cat, TilePos p, int terrain) {
    const auto r = canPaint(world, cat, p, terrain);
    if (r != PaintResult::Ok) return r;
    const int from = world.terrainAt(p);
    world.setTerrain(p, terrain);
    record(Op::terrain(p, from, terrain));
    return r;
}

std::span<const Op> Editor::undo(World& world) {
    commit();
    applied_.clear();
    if (undo_.empty()) return {};
    auto step = std::move(undo_.back());
    undo_.pop_back();
    for (const Op& op : std::views::reverse(step)) {
        apply(world, op, false);
        applied_.push_back(inverted(op));
    }
    redo_.push_back(std::move(step));
    return applied_;
}

std::span<const Op> Editor::redo(World& world) {
    commit();
    applied_.clear();
    if (redo_.empty()) return {};
    auto step = std::move(redo_.back());
    redo_.pop_back();
    for (const Op& op : step) {
        apply(world, op, true);
        applied_.push_back(op);
    }
    undo_.push_back(std::move(step));
    return applied_;
}

void Editor::clear() {
    grouping_ = false;
    pending_.clear();
    undo_.clear();
    redo_.clear();
}

} // namespace lc
