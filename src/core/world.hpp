#pragma once
// The map: terrain and item occupancy stored in square chunks, plus placed items indexed by the
// chunk of their origin so area queries only touch nearby chunks. Nothing here walks the whole map
// except construction.

#include "core/catalog.hpp"
#include "core/iso.hpp"

#include <array>
#include <cstdint>
#include <optional>
#include <span>
#include <vector>

namespace lc {

struct Item {
    std::uint16_t type = 0;
    std::uint8_t variant = 0; // rotation k for rotate layouts, look for variant layouts
    std::uint8_t w = 1;       // footprint after rotation
    std::uint8_t h = 1;
    TilePos pos; // origin tile: smallest tx, ty of the footprint
    friend bool operator==(const Item&, const Item&) = default;

    [[nodiscard]] TileRect rect() const { return {pos.x, pos.y, pos.x + w, pos.y + h}; }
};

struct Footprint {
    int w = 1;
    int h = 1;
};

[[nodiscard]] Footprint footprintOf(const ItemDef& def, int variant);
[[nodiscard]] Item makeItem(const Catalog& cat, int type, int variant, TilePos origin);

// Largest footprint side the catalog allows; area queries widen by this much.
inline constexpr int kMaxFootprint = 8;
inline constexpr int kChunkShift = 5;
inline constexpr int kChunk = 1 << kChunkShift; // tiles per chunk side
inline constexpr int kChunkArea = kChunk * kChunk;
// Terrain value of a tile with no ground at all: open sky around the land. Tools never paint it;
// it lets a landmass have any outline, and the cliff rim follows it.
inline constexpr std::uint8_t kNoGround = 0xFF;

class World {
public:
    explicit World(const Catalog& cat);
    // A map of another size than the catalog's (benchmarks, tests, migrated saves).
    World(const Catalog& cat, int width, int height);

    [[nodiscard]] int width() const { return w_; }
    [[nodiscard]] int height() const { return h_; }
    [[nodiscard]] TileRect bounds() const { return {0, 0, w_, h_}; }
    [[nodiscard]] bool inBounds(TilePos p) const {
        return p.x >= 0 && p.y >= 0 && p.x < w_ && p.y < h_;
    }
    // Precondition for terrainAt/isWater: inBounds(p).
    [[nodiscard]] int terrainAt(TilePos p) const { return chunkOf(p).terrain[local(p)]; }
    [[nodiscard]] bool hasGround(TilePos p) const {
        return inBounds(p) && terrainAt(p) != kNoGround;
    }
    [[nodiscard]] bool isWater(TilePos p) const { return terrainAt(p) == water_; }
    // `terrain` is a catalog terrain index or kNoGround.
    void setTerrain(TilePos p, int terrain);

    [[nodiscard]] std::span<const Item> items() const { return items_; }
    [[nodiscard]] std::optional<std::size_t> itemIndexAt(TilePos p) const;
    [[nodiscard]] const Item* itemAt(TilePos p) const;
    // Precondition: every footprint tile is in bounds and free.
    void addItem(const Item& item);
    Item removeItem(std::size_t index);

    // Calls f(const Item&) for every item whose footprint intersects r.
    template <typename F>
    void forEachItemIn(TileRect r, F&& f) const {
        r = r.clipped(bounds());
        if (r.empty()) return;
        const TileRect origins{r.x0 - (kMaxFootprint - 1), r.y0 - (kMaxFootprint - 1), r.x1, r.y1};
        forEachChunkIn(origins, [&](int cx, int cy) {
            for (const std::uint32_t i : chunks_[chunkIndex(cx, cy)].items)
                if (items_[i].rect().intersects(r)) f(items_[i]);
        });
    }
    // Calls f(cx, cy) for every chunk overlapping r (tile coordinates), row by row.
    template <typename F>
    void forEachChunkIn(TileRect r, F&& f) const {
        r = r.clipped(bounds());
        if (r.empty()) return;
        for (int cy = r.y0 >> kChunkShift; cy <= (r.y1 - 1) >> kChunkShift; ++cy)
            for (int cx = r.x0 >> kChunkShift; cx <= (r.x1 - 1) >> kChunkShift; ++cx) f(cx, cy);
    }
    [[nodiscard]] int chunksX() const { return cw_; }
    [[nodiscard]] int chunksY() const { return ch_; }
    // Bumped whenever a tile in the chunk, or a neighbour its edges depend on, changes terrain.
    [[nodiscard]] std::uint32_t chunkTerrainRevision(int cx, int cy) const {
        return chunks_[chunkIndex(cx, cy)].terrainRev;
    }
    // True once anything in the chunk was edited since the world was made (saves skip the rest).
    [[nodiscard]] bool chunkTouched(int cx, int cy) const {
        const Chunk& c = chunks_[chunkIndex(cx, cy)];
        return c.terrainRev != 0 || c.itemRev != 0;
    }
    [[nodiscard]] std::span<const std::uint32_t> chunkItems(int cx, int cy) const {
        return chunks_[chunkIndex(cx, cy)].items;
    }
    // Per-chunk tallies, so needs can be measured over an area without visiting its tiles.
    [[nodiscard]] int chunkTerrainCount(int cx, int cy, int terrain) const {
        return chunks_[chunkIndex(cx, cy)].terrainCounts[static_cast<std::size_t>(terrain)];
    }
    [[nodiscard]] int chunkItemCount(int cx, int cy, int type) const {
        return chunks_[chunkIndex(cx, cy)].itemCounts[static_cast<std::size_t>(type)];
    }

    [[nodiscard]] int terrainCount(int terrain) const {
        return terrainCounts_[static_cast<std::size_t>(terrain)];
    }
    [[nodiscard]] int itemCount(int type) const {
        return itemCounts_[static_cast<std::size_t>(type)];
    }
    // Bumped on every change so views can cache derived data.
    [[nodiscard]] std::uint64_t revision() const { return revision_; }
    // Bounding rectangle of the tiles that have ground.
    [[nodiscard]] TileRect landBounds() const;

    // Same-kind neighbour mask (N=1, E=2, S=4, W=8). Neighbours without ground count as "same"
    // for terrain so overlays run cleanly into the cliff rim instead of rounding off.
    [[nodiscard]] int terrainMask(TilePos p) const;
    [[nodiscard]] int itemMask(TilePos p, int type) const;

private:
    struct Chunk {
        std::array<std::uint8_t, kChunkArea> terrain{};
        std::array<std::uint32_t, kChunkArea> occupancy{}; // item index + 1, 0 = free
        std::vector<std::uint32_t> items;                  // items whose origin lies here
        std::vector<int> terrainCounts;
        std::vector<int> itemCounts;
        std::uint32_t terrainRev = 0;
        std::uint32_t itemRev = 0;
    };

    [[nodiscard]] std::size_t chunkIndex(int cx, int cy) const {
        return static_cast<std::size_t>(cy) * static_cast<std::size_t>(cw_) +
               static_cast<std::size_t>(cx);
    }
    [[nodiscard]] Chunk& chunkOf(TilePos p) {
        return chunks_[chunkIndex(p.x >> kChunkShift, p.y >> kChunkShift)];
    }
    [[nodiscard]] const Chunk& chunkOf(TilePos p) const {
        return chunks_[chunkIndex(p.x >> kChunkShift, p.y >> kChunkShift)];
    }
    [[nodiscard]] static std::size_t local(TilePos p) {
        return static_cast<std::size_t>(((p.y & (kChunk - 1)) << kChunkShift) |
                                        (p.x & (kChunk - 1)));
    }
    void setOccupancy(const Item& item, std::uint32_t value);
    void bumpTerrain(TilePos p);

    int w_;
    int h_;
    int cw_;
    int ch_;
    int water_;
    std::vector<Chunk> chunks_;
    std::vector<Item> items_;
    std::vector<int> terrainCounts_;
    std::vector<int> itemCounts_;
    std::uint64_t revision_ = 0;
    mutable std::optional<TileRect> land_; // cached; reset when ground appears or vanishes
};

} // namespace lc
