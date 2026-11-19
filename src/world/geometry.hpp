#pragma once
// Geometry the art tool emits per item and rendered variant (`assets/atlas/<set>.geom.json`,
// docs/design/world-tech.md §1.10): pieces of split landmarks, walk tiles and their floor heights,
// slot spots, emitter points, and actors' carry points.

#include "core/catalog.hpp"
#include "core/iso.hpp"

#include <cstdint>
#include <expected>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

namespace lc::world {

inline constexpr std::uint8_t kFaceFree = 0xFF; // otherwise 0 +x, 1 +y, 2 -x, 3 -y (as core)
inline constexpr int kMaxPieceSide = 8;

struct GeomSpot {
    TilePos t;  // tile offset from the origin tile (may lie outside the footprint)
    Offset off; // pixels from that tile's centre
    int z = 0;  // pixels above the ground
    std::uint8_t face = kFaceFree;
};

struct GeomSlot {
    std::string id;
    std::vector<GeomSpot> spots;
};

struct GeomPiece {
    TileRect rect;      // footprint tiles, relative to the origin tile
    bool floor = false; // a stair floor: drawn before the actors standing on it
    int under = 0;      // room under it above the item's level, px (a deck's underside), 0: none
};

struct GeomVariant {
    std::string key;               // "r<k>" or "m<mask>"
    int h = 0;                     // sprite height above the anchor, px
    std::vector<GeomPiece> pieces; // empty: not split
    std::vector<TilePos> walk;
    std::vector<TilePos> water; // tiles of open water inside the item (a basin, a harbour)
    std::vector<std::pair<TilePos, int>> walkZ; // floor height above the item's level, px
    // Overhead above walk tiles: the lowest voxel over the headroom, px above the item's level.
    std::vector<std::pair<TilePos, int>> roof;
    int under = 0; // an unsplit crossing's room under it, px (pieces carry their own)
    // The highest point over each footprint tile, px above the item's level, rows by dy
    // (`tops`, draw-order.md §3.4; a walk tile's is its floor); empty when not given.
    std::vector<std::uint16_t> tops;
    int topsW = 0;
    [[nodiscard]] int topAt(TilePos t) const {
        if (t.x < 0 || t.y < 0 || t.x >= topsW || topsW == 0) return -1;
        const auto i = static_cast<std::size_t>(t.y * topsW + t.x);
        return i < tops.size() ? tops[i] : -1;
    }
    std::vector<GeomSlot> slots;
    std::vector<std::pair<std::string, Offset>> emitters; // from the anchor, px
};

struct GeomItem {
    std::string id;
    std::vector<GeomVariant> variants;
    [[nodiscard]] const GeomVariant* variant(std::string_view key) const;
};

struct GeomActor {
    std::string id;
    std::vector<std::pair<std::string, std::vector<Offset>>> carryAt; // per animation, per frame
};

struct GeometryFile {
    std::string set;
    std::string file;
    int tileW = 0;
    int tileH = 0;
    std::vector<GeomItem> items;
    std::vector<GeomActor> actors;
};

[[nodiscard]] std::expected<GeometryFile, std::string>
parseGeometry(std::string_view text, std::string_view file, std::string_view set);

} // namespace lc::world
