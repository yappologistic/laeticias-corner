#pragma once
// The global layer list (docs/design/draw-order.md §2): every drawable class the game has, in
// exactly one band, the bands drawn in this order at every zoom level by the home scene and the
// world renderer alike. A draw site names its band before it draws (Batch counts draw calls per
// band, and one made with no band is counted as such and fails the tests); no site decides an
// order of its own. A new class goes into this list in the same change that adds it: a thing
// something can stand in front of is a box in Depth; flat on the ground is GroundDecals or
// WaterSurface; light is Glow; about the world but not of it (an outline, a bubble) is Markers.

#include <array>
#include <cstdint>
#include <string_view>

namespace lc {

enum class Band : std::uint8_t {
    Sky,            // B0 sky gradient, stars, the sky behind the world's edges
    FarBackdrop,    // B1 backdrop strips behind the north and east edges; the sea beyond the grid
    Ground,         // B2 terrain, water, faces under tile edges, cap bands; the home's ground
    GroundDecals,   // B3 paths, wet ground, snow cover, grid, nook areas, tile highlights
    WaterSurface,   // B4 shore foam, ripples, rain rings, petals on water, fish under it
    Shadows,        // B5 cast shadows of items, pieces and actors, cloud shadows: one layer
    Depth,          // B6 items, pieces, raised ground, actors, goods, flyers, effects with depth,
                    //    ghosts and fades, the home as one element: sorted (§1.3, §1.4)
    OccluderFade,   // B7 a roof faded over the pointer: drawn at its element's rank, instead of it
    Weather,        // B8 rain streaks and splashes, snowflakes, mist banks
    Grading,        // B9 the clock's ambient times the region's grade; haze
    Glow,           // B10 glow layers, emissive actors, light pools: additive, occluded (§4.4)
    SkyEffects,     // B11 rainbow, shooting stars, lightning flash
    Markers,        // B12 hover outlines, bubbles and hearts, card anchors, the placement cursor
    ScreenOverlays, // B13 the haze composite, the postcard frame, the photo bar's guides
    Interface,      // B14 glass panels, drawer, docks, tray, sketchbook, cards, toasts, profiler
    Debug,          // B15 the debug views (§6.5)
};

inline constexpr std::size_t kBandCount = 16;
// Batch's tag for "no band named yet": a draw made with it is a fault the tests catch.
inline constexpr std::uint8_t kNoBand = 0xFF;

[[nodiscard]] constexpr std::uint8_t bandTag(Band b) {
    return static_cast<std::uint8_t>(b);
}

[[nodiscard]] constexpr std::string_view bandName(Band b) {
    constexpr std::array<std::string_view, kBandCount> kNames{
        "sky",     "backdrop", "ground",    "decals",  "water", "shadows",
        "depth",   "fade",     "weather",   "grading", "glow",  "sky effects",
        "markers", "overlays", "interface", "debug"};
    return kNames[static_cast<std::size_t>(b)];
}

} // namespace lc
