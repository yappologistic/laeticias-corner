#pragma once
// Pure rules of the ground's drawing (out/reports/art-smooth-land.md §3.3–§4): which bands of
// face hang under a tile edge once tiles may slope, the light of a slope's facets, the parts of
// falling water, and the slow field that keeps large grounds from reading as wallpaper.

#include "core/iso.hpp"
#include "world/slopes.hpp"
#include "world/world_map.hpp"

#include <array>
#include <string_view>
#include <vector>

namespace lc::worldview {

// The face under one front edge of a tile (art §3.4). `aS`, `aFar`: the levels of the tile's own
// corners on that edge (`S`, the diamond's bottom vertex, and the edge's far end); `bS`, `bFar`:
// the neighbour's corners at the same two points. Bands are counted down from the tile's level:
// band b spans levels `level - b` to `level - b - 1`.
struct EdgeFace {
    int first = 0;  // the first whole band (0, or 1 under a wedge)
    int last = 0;   // one past the last; first == last: no whole band
    int wedge = -1; // 0: high at S (`w0`), 1: high at the far end (`w1`), -1: none
    [[nodiscard]] bool empty() const { return first >= last && wedge < 0; }
    // The cap (`/top`) replaces the uppermost whole band when no wedge stands over it.
    [[nodiscard]] bool capped() const { return wedge < 0 && first < last; }
};
[[nodiscard]] EdgeFace edgeFace(int level, int aS, int aFar, int bS, int bFar);

// The light of each fan triangle of a slope over the light of flat ground (the art's baked sun,
// `0.42 + 0.58 max(0, n.S)` with S from the upper left), for warping flat sprites onto it so
// they match the baked slope art. `levelUnits`: a level's height in units where a tile edge is 1.
// With a sun (grid axes, toward it; `strength` 0..1), the same light as the shader path's relight
// gives the slope art under that sun (render/gpu/tuning.hpp: the ratio to the baked light, mixed
// by strength, kept between 1 / kRelightMax and kRelightLift).
[[nodiscard]] std::array<float, 8> slopeLight(world::Slope s, float levelUnits,
                                              const float* sun = nullptr, float strength = 0);

// Water stepping down across one front edge (art §4): what each band of the drop draws.
enum class FallPart : std::uint8_t { Rapid, Top, Mid, Foot };
// The part of band `b` (0 at the top) of a drop of `drop` levels (drop >= 1).
[[nodiscard]] FallPart fallPart(int drop, int b);

// The overlay mask of tile p of terrain t: its same-terrain neighbours (N 1, E 2, S 4, W 8);
// waters count as one water for each other's edges, and the sea runs on beyond the grid.
[[nodiscard]] int overlayMask(const world::WorldMap& m, TilePos p, int t);
// The same with the neighbours of terrain `except` (and the grid's outside when `except` is the
// sea's) not counting as the same: shallows round off against the deep sea drawn under them.
[[nodiscard]] int overlayMaskExcept(const world::WorldMap& m, TilePos p, int t, int except);
// Water that flows (rivers, canals, channels, streams): its level byte's aux is its direction.
[[nodiscard]] bool flowingWater(std::string_view terrainId);

// What decides how water steps down (art §4), per terrain: water that flows (its level byte's
// aux is its direction), and water whose base has a face material of its own (its bank).
struct WaterKinds {
    std::vector<bool> channel;
    std::vector<bool> bank;
};
// The drop in levels of the fall from water tile p over its side toward kSteps[dir], 0 for none:
// a lower water neighbour (beyond the grid, the sea at level 0), or lower land where the water
// leaves by that side (its flow) or its bank has no face to show. A fall is drawn as falling
// water; every other drop of a water tile shows its bank's face.
[[nodiscard]] int fallDrop(const world::WorldMap& m, const WaterKinds& w, TilePos p, int dir);

// A slow, smooth field over the grid in [0, 1] (two octaves of value noise, about 7 and 17
// tiles across): the ground's lightness leans with it so that no stretch of ground repeats its
// tile like wallpaper at any zoom. Continuous everywhere (sampled at sprite corners).
[[nodiscard]] float groundMacro(Vec2 tile);

} // namespace lc::worldview
