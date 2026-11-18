#pragma once
// 2:1 isometric projection maths shared by rendering, picking and the camera (see CLAUDE.md
// "Projection"). The tile cell size comes from the catalog; nothing here assumes a size.

#include <algorithm>
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

// Half-open rectangle of tiles [x0, x1) x [y0, y1).
struct TileRect {
    int x0 = 0;
    int y0 = 0;
    int x1 = 0;
    int y1 = 0;
    [[nodiscard]] constexpr bool empty() const { return x1 <= x0 || y1 <= y0; }
    [[nodiscard]] constexpr bool contains(TilePos p) const {
        return p.x >= x0 && p.y >= y0 && p.x < x1 && p.y < y1;
    }
    [[nodiscard]] constexpr bool contains(const TileRect& r) const {
        return r.x0 >= x0 && r.y0 >= y0 && r.x1 <= x1 && r.y1 <= y1;
    }
    [[nodiscard]] constexpr bool intersects(const TileRect& r) const {
        return x0 < r.x1 && r.x0 < x1 && y0 < r.y1 && r.y0 < y1;
    }
    [[nodiscard]] constexpr TileRect clipped(const TileRect& r) const {
        return {std::max(x0, r.x0), std::max(y0, r.y0), std::min(x1, r.x1), std::min(y1, r.y1)};
    }
    [[nodiscard]] constexpr int width() const { return x1 - x0; }
    [[nodiscard]] constexpr int height() const { return y1 - y0; }
    friend constexpr bool operator==(const TileRect&, const TileRect&) = default;
};

// Float rectangle [x0, x1) x [y0, y1): world-pixel boxes and fractional footprints.
struct FRect {
    float x0 = 0;
    float y0 = 0;
    float x1 = 0;
    float y1 = 0;
    [[nodiscard]] constexpr bool overlaps(const FRect& o) const {
        return x0 < o.x1 && o.x0 < x1 && y0 < o.y1 && o.y0 < y1;
    }
};

// World pixels are float: at the largest planned maps (about 1024 x 512 tiles of 64 x 32 px) the
// extents stay below 2^16, where float still resolves 1/256 px.
struct Iso {
    float hw = 32; // half tile width in world px
    float hh = 16; // half tile height

    // Top vertex of tile (tx, ty) in world pixels; also valid for fractional tile coordinates.
    [[nodiscard]] constexpr Vec2 toWorld(float tx, float ty) const {
        return {(tx - ty) * hw, (tx + ty) * hh};
    }
    [[nodiscard]] constexpr Vec2 toWorld(TilePos p) const {
        return toWorld(static_cast<float>(p.x), static_cast<float>(p.y));
    }
    // Continuous inverse of toWorld; floor the result to get the tile under a world pixel.
    [[nodiscard]] constexpr Vec2 toTile(Vec2 w) const {
        const float u = w.x / hw;
        const float v = w.y / hh;
        return {(u + v) * 0.5f, (v - u) * 0.5f};
    }
    [[nodiscard]] TilePos tileAt(Vec2 world) const {
        const Vec2 t = toTile(world);
        return {static_cast<int>(std::floor(t.x)), static_cast<int>(std::floor(t.y))};
    }
    [[nodiscard]] constexpr float tileW() const { return 2 * hw; }
    [[nodiscard]] constexpr float tileH() const { return 2 * hh; }
};

// Neighbour bits for connection masks.
inline constexpr int kMaskN = 1;
inline constexpr int kMaskE = 2;
inline constexpr int kMaskS = 4;
inline constexpr int kMaskW = 8;

} // namespace lc
