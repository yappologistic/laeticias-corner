#pragma once
// Placement rules and command-based undo/redo. Every edit goes through Editor so that a
// click, a drag or a scripted action is exactly one undo step.

#include "core/world.hpp"

#include <cstddef>
#include <span>
#include <vector>

namespace lc {

enum class PlaceResult { Ok, OutOfBounds, Wild, Occupied, NeedsLand, NeedsWater };
enum class PaintResult { Ok, Unchanged, OutOfBounds, Wild, BlockedByItem };

[[nodiscard]] PlaceResult canPlace(const World& world, const Catalog& cat, const Item& item);
[[nodiscard]] PaintResult canPaint(const World& world, const Catalog& cat, TilePos p, int terrain);

struct Op {
    enum class Kind : std::uint8_t { Terrain, Add, Remove };
    Kind kind = Kind::Terrain;
    TilePos pos;  // Terrain only
    int from = 0; // Terrain only
    int to = 0;   // Terrain only
    Item item;    // Add / Remove

    static Op terrain(TilePos p, int from, int to) {
        Op op;
        op.pos = p;
        op.from = from;
        op.to = to;
        return op;
    }
    static Op items(Kind kind, const Item& item) {
        Op op;
        op.kind = kind;
        op.item = item;
        return op;
    }
};

class Editor {
public:
    explicit Editor(std::size_t maxSteps) : maxSteps_(maxSteps) {}

    // Groups subsequent edits into one undo step until commit(). Empty groups are dropped.
    void begin();
    void commit();
    // Undoes the open group's edits and closes it without leaving an undo step; returns them as
    // applied (inverted), for feedback.
    std::span<const Op> abort(World& world);
    [[nodiscard]] bool inGroup() const { return grouping_; }

    PlaceResult place(World& world, const Catalog& cat, const Item& item);
    // Removes the item covering p; returns false when there is none.
    bool remove(World& world, TilePos p);
    PaintResult paint(World& world, const Catalog& cat, TilePos p, int terrain);

    [[nodiscard]] bool canUndo() const { return !undo_.empty(); }
    [[nodiscard]] bool canRedo() const { return !redo_.empty(); }
    // Return the ops as they were applied (inverted for undo), for feedback; empty if nothing.
    std::span<const Op> undo(World& world);
    std::span<const Op> redo(World& world);

private:
    void record(const Op& op);
    void push(std::vector<Op>&& step);

    std::size_t maxSteps_;
    bool grouping_ = false;
    std::vector<Op> pending_;
    std::vector<std::vector<Op>> undo_;
    std::vector<std::vector<Op>> redo_;
    std::vector<Op> applied_;
};

} // namespace lc
