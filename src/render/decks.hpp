#pragma once
// The home's crossings as decks (docs/design/draw-order.md §1.5 d), the same way the world's
// have them: a walkable item's `deck` is the floor whoever crosses it stands on, a railed one
// (a footbridge, rotate layout) is drawn in two halves cut along its span so a walker on the
// deck goes between its rails, and whatever swims under it stays under it. Pure logic (no SDL).

#include "core/catalog.hpp"
#include "core/world.hpp"
#include "render/depth.hpp"

namespace lc {

// Whether a walkable item is drawn in two halves along its span (its rails).
[[nodiscard]] bool railed(const ItemDef& def);

// The deck under a point (tile coordinates) in px above the ground: its tile's walkable item's
// `deck`, blended half way toward each neighbour's one can step to (not the open water beside a
// footbridge) at the shared edge, so a walker rises onto it and off it smoothly.
[[nodiscard]] float deckAt(const World& world, const Catalog& cat, Vec2 pos);

// The box of a walkable item, whole (`part` -1) or one half of a railed one (0 the far half,
// 1 the near half): from just over the water to the deck, the near half from over the deck to
// the rails' top (`top`, px), so a walker on the deck is after the far half and before the near.
[[nodiscard]] DepthBox crossingBox(const ItemDef& def, const Item& item, int part, float top,
                                   std::uint64_t id, float hh);

// The line, world px y = a + b·x, a railed crossing's sprite is cut along: its span through
// the tile's centre at the deck's height. The near half lies below it.
struct CutLine {
    float a = 0;
    float b = 0;
};
[[nodiscard]] CutLine crossingCut(const ItemDef& def, const Item& item, Iso iso);

} // namespace lc
