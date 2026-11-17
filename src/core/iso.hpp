#pragma once
// 2:1 isometric projection maths shared by rendering, picking and the camera (see CLAUDE.md).

#include <cmath>

namespace lc {

struct TilePos {
    int x = 0;
    int y = 0;
    friend constexpr bool operator==(TilePos, TilePos) = default;
};

struct Vec2 {
    float x = 0;
    float y = 0;
};

inline constexpr int kHalfTileW = 16;
inline constexpr int kHalfTileH = 8;

// Top vertex of tile (tx, ty) in world pixels; also valid for fractional tile coordinates.
[[nodiscard]] constexpr Vec2 tileToWorld(float tx, float ty) {
    return {(tx - ty) * kHalfTileW, (tx + ty) * kHalfTileH};
}

// Continuous inverse of tileToWorld; floor the result to get the tile under a world pixel.
[[nodiscard]] constexpr Vec2 worldToTile(Vec2 w) {
    const float u = w.x / kHalfTileW;
    const float v = w.y / kHalfTileH;
    return {(u + v) * 0.5f, (v - u) * 0.5f};
}

[[nodiscard]] inline TilePos tileAt(Vec2 world) {
    const Vec2 t = worldToTile(world);
    return {static_cast<int>(std::floor(t.x)), static_cast<int>(std::floor(t.y))};
}

// Neighbour bits for connection masks.
inline constexpr int kMaskN = 1;
inline constexpr int kMaskE = 2;
inline constexpr int kMaskS = 4;
inline constexpr int kMaskW = 8;

} // namespace lc
