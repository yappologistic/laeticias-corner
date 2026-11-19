#pragma once
// The resident world (docs/design/world-tech.md §2.1, §4.2): layers composed into one grid kept
// whole in memory, in 32 x 32 chunks like core's World: terrain, level byte and district per tile,
// item occupancy and walkability, items indexed by the chunk of their origin (footprints over 8 x 8
// also listed in every chunk they cover), slots with world positions. Queries on the hot paths do
// not allocate. The prebuilt world is immutable; only the home rect changes (applyHome).

#include "core/world.hpp"
#include "world/content.hpp"
#include "world/diagnostics.hpp"
#include "world/layer_file.hpp"
#include "world/slopes.hpp"
#include "world/world_file.hpp"

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <expected>
#include <memory>
#include <span>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

namespace lc::world {

// Terrain and district value of a tile without ground (or never set by any layer).
inline constexpr std::uint8_t kNone = 0xFF;
inline constexpr std::uint8_t kHomeLayer = 0xFF;

// Directions as core's slot faces: 0 +x, 1 +y, 2 -x, 3 -y.
inline constexpr std::array<TilePos, 4> kSteps{{{1, 0}, {0, 1}, {-1, 0}, {0, -1}}};

struct Placed {
    std::uint32_t info = 0; // index into Content::items()
    std::int16_t x = 0;     // origin tile: smallest tx, ty of the footprint
    std::int16_t y = 0;
    std::uint8_t w = 1; // footprint after rotation
    std::uint8_t h = 1;
    std::uint8_t variant = 0;
    std::uint8_t mask = 0;  // connect layouts: same-item neighbours (N 1, E 2, S 4, W 8)
    std::uint8_t layer = 0; // index into WorldMap::layers(), kHomeLayer for the player's items
    std::uint8_t level = 0; // ground level under the origin tile
    std::int8_t head = -1;  // stairs and ramps: direction of the high end, -1 otherwise
    [[nodiscard]] TileRect rect() const { return {x, y, x + w, y + h}; }
};

// One element for the depth sort: a whole item or one piece of a split one.
struct DrawPiece {
    std::uint32_t item = 0;
    std::int16_t piece = -1; // index into the variant's pieces, -1: the whole item
    bool floor = false;      // a walk-run floor: drawn before actors standing on it
    std::uint8_t level = 0;
    TileRect rect; // grid footprint of the element
};

struct WorldSlot {
    std::uint32_t item = 0;
    std::uint16_t name = 0; // WorldMap::slotNames()
    std::uint16_t kind = 0; // WorldMap::slotKinds()
    Vec2 at;                // continuous tile coordinates (x.5 is a tile centre)
    TilePos tile;
    std::int16_t z = 0; // px above the floor
    std::uint8_t face = 0xFF;
    std::uint8_t cap = 1;
};

struct WalkStep {
    TilePos to;
    int dz = 0; // floor height change, px
};

struct RegionWeight {
    int region = -1; // index into WorldFile::regions
    float weight = 0;
};

// The player's region as the save holds it (save v3 "home" block): home-relative, x fastest.
struct HomeItem {
    std::string id;
    int x = 0;
    int y = 0;
    int variant = 0;
};
struct HomeDelta {
    int w = 0;
    int h = 0;
    std::vector<std::string> palette;
    std::vector<std::uint8_t> terrain; // palette index per tile, kNone: no ground
    std::vector<std::uint8_t> wild;    // 1: land not opened yet (no walking); empty: none
    std::vector<HomeItem> items;
};
// The home block of a core World (the save's home map) as a delta.
[[nodiscard]] HomeDelta homeDeltaFrom(const lc::World& home, const Catalog& cat);

struct LayerInput {
    std::string id;
    const LayerFile* file = nullptr;
};

class WorldMap {
public:
    // Composes the layers in order (world-tech §2.4): a set cell overwrites the cell below, and
    // a lower item whose footprint touches a set cell of a higher layer is dropped. Item ids no
    // catalog has are skipped, one diagnostic per id. `content` must outlive the map.
    WorldMap(const WorldFile& wf, const Content& content, std::span<const LayerInput> layers,
             Diagnostics& diag);

    [[nodiscard]] int width() const { return w_; }
    [[nodiscard]] int height() const { return h_; }
    [[nodiscard]] TileRect bounds() const { return {0, 0, w_, h_}; }
    [[nodiscard]] int chunksX() const { return cw_; }
    [[nodiscard]] int chunksY() const { return ch_; }
    [[nodiscard]] bool inBounds(TilePos p) const {
        return p.x >= 0 && p.y >= 0 && p.x < w_ && p.y < h_;
    }
    [[nodiscard]] const Content& content() const { return *content_; }
    [[nodiscard]] const std::vector<std::string>& layers() const { return layers_; }
    // Placed item ids no catalog has, with how many were skipped, sorted by id.
    [[nodiscard]] const std::vector<std::pair<std::string, int>>& unresolved() const {
        return unresolved_;
    }

    // Tiles. Preconditions: inBounds(p).
    [[nodiscard]] int terrainAt(TilePos p) const { return chunk(p).terrain[local(p)]; } // or kNone
    [[nodiscard]] const TerrainInfo& terrainInfo(int t) const {
        return terrains_[static_cast<std::size_t>(t)];
    }
    [[nodiscard]] std::size_t terrainCount() const { return terrains_.size(); }
    [[nodiscard]] std::uint8_t levelByte(TilePos p) const { return chunk(p).level[local(p)]; }
    [[nodiscard]] int level(TilePos p) const { return levelOf(levelByte(p)); }
    [[nodiscard]] int levelPx() const { return levelPx_; } // one level's height, px
    [[nodiscard]] int districtAt(TilePos p) const {
        return chunk(p).district[local(p)];
    } // or kNone
    [[nodiscard]] const std::string& districtName(int d) const {
        return districts_[static_cast<std::size_t>(d)].name;
    }
    [[nodiscard]] std::size_t districtCount() const { return districts_.size(); }
    [[nodiscard]] int districtRegion(int d) const {
        return districts_[static_cast<std::size_t>(d)].region;
    }
    [[nodiscard]] int findDistrict(std::string_view name) const; // -1 when absent
    // Region index (WorldFile::regions) of the tile's district, -1 when none.
    [[nodiscard]] int regionAt(TilePos p) const {
        const int d = districtAt(p);
        return d == kNone ? -1 : districts_[static_cast<std::size_t>(d)].region;
    }

    // Items.
    [[nodiscard]] std::span<const Placed> items() const { return items_; }
    [[nodiscard]] const ItemInfo& info(const Placed& it) const {
        return content_->item(int(it.info));
    }
    [[nodiscard]] int itemAt(TilePos p) const { // -1 when free; precondition: inBounds(p)
        return static_cast<int>(chunk(p).occupancy[local(p)]) - 1;
    }
    // Calls f(index, const Placed&) once for every item whose footprint intersects r.
    template <typename F>
    void forEachItemIn(TileRect r, F&& f) const;
    // Items and pieces of split items overlapping r, ordered by depth key (footprint centre
    // x + y, then item, then piece) for DepthSorter. `out` is cleared and reused.
    void piecesIn(TileRect r, std::vector<DrawPiece>& out) const;
    [[nodiscard]] const GeomVariant* geometry(const Placed& it) const {
        return content_->geometry(int(it.info), it.variant, it.mask);
    }

    // Walking.
    [[nodiscard]] bool walkable(TilePos p) const {
        return inBounds(p) && (chunk(p).walk[local(p)] & kWalk) != 0;
    }
    // Height of the floor a walker stands on, px above level 0 (stairs and walk floors included).
    [[nodiscard]] int floorZ(TilePos p) const;
    // The floor under a continuous point (tile coordinates): its tile's floor, blended toward
    // each neighbour it can step to as the point nears their shared edge (the two sides meet
    // half way), so a height carried along any course is continuous.
    [[nodiscard]] float floorAt(Vec2 p) const;
    // A boat's room under a span at p, px (the geometry's `pass` of the item over it), INT_MAX
    // where nothing spans the water (open water, or a pier or ground no boat passes).
    [[nodiscard]] int boatRoomAt(TilePos p) const;
    // The 4-neighbours a walker on p may step to, with their floor height change.
    [[nodiscard]] int walkNeighbours(TilePos p, std::array<WalkStep, 4>& out) const;

    // The ground's surface (art-smooth-land.md §3): one answer to "how high is the ground here".
    // Shape of a tile's surface (Flat until shapeSlopes ran). Precondition: inBounds(p).
    [[nodiscard]] Slope slopeAt(TilePos p) const { return Slope(chunk(p).slope[local(p)]); }
    // Height of the ground at a continuous point (tile coordinates), px above level 0: the tile's
    // level less what its slope falls there, continuous across tiles wherever surfaces meet.
    // Off the grid and on tiles without ground: 0 (the sea's level). Floors of items (stairs,
    // decks, walk floors) are floorAt's.
    [[nodiscard]] float surfaceZ(Vec2 p) const;
    // The height a walker stands at on a continuous point: floorAt with the ground's surface in
    // place of the tile's level (a stair's, deck's or walk floor's own height; elsewhere
    // surfaceZ), meeting each neighbour it may step to half way at their shared edge, so it is
    // continuous along any course. City life switches to it from floorAt (engine-terrain.md).
    [[nodiscard]] float walkZ(Vec2 p) const;
    // Level of corner `c` (0 N, 1 E, 2 S, 3 W: the diamond's top, right, bottom, left vertex) of
    // the tile's surface; off the grid and without ground, 0.
    [[nodiscard]] int cornerLevel(TilePos p, int c) const;
    // Whether p's surface and its neighbour's toward kSteps[dir] meet along their shared edge
    // (both corners at one height on both sides): a one-level step there is ground a walker
    // may cross (the contract's walk rule for slopes, §3.2).
    [[nodiscard]] bool surfacesMeet(TilePos p, int dir) const;
    // Shapes every tile by the corner rule (§3.1): a tile may slope when its terrain is listed in
    // its set's `art.slopes`, it is not water, its face material is one of `natural` (masonry
    // stays a wall) and nothing on it needs flat ground (anything but a one-tile plant, rock or
    // prop nobody uses); a corner of such a tile is one level low when a tile touching it stands
    // exactly one level lower (a stair, ramp, deck or walked-on item there never pulls it down:
    // its floor meets the tile at the tile's level).
    void shapeSlopes(std::span<const std::string> natural);

    // Slots.
    [[nodiscard]] std::span<const WorldSlot> slots() const { return slots_; }
    [[nodiscard]] const std::vector<std::string>& slotNames() const { return slotNames_; }
    [[nodiscard]] const std::vector<std::string>& slotKinds() const { return slotKinds_; }
    [[nodiscard]] int findSlotKind(std::string_view kind) const; // -1 when absent
    // f(const WorldSlot&) for slots of `kind` (-1: any) within `radius` tiles of `centre`.
    template <typename F>
    void forEachSlotNear(Vec2 centre, float radius, int kind, F&& f) const;
    // f(const WorldSlot&) for slots of `kind` (-1: any) on tiles of `district`.
    template <typename F>
    void forEachSlotInDistrict(int district, int kind, F&& f) const;

    // Region themes (world-tech §4.6): region weights around a point, heaviest first, summing
    // to 1. Returns how many were written (at most out.size()).
    [[nodiscard]] int themeWeights(Vec2 centre, std::span<RegionWeight> out) const;

    // The player's region: drops every prebuilt item touching the home rect (the home is the last
    // layer) and writes the delta's tiles and items over it. Unknown ids are skipped with a
    // diagnostic; a delta of another size is refused.
    [[nodiscard]] std::expected<void, std::string> applyHome(const HomeDelta& delta,
                                                             Diagnostics& diag);
    [[nodiscard]] TileRect homeRect() const { return home_.rect; }
    // After the home was applied: its terrain and wild land follow the player's edits, writing
    // only the bytes that changed (readers on other threads never look inside the home rect).
    // False when the delta does not fit or names a terrain the first applyHome did not know.
    bool updateHomeTerrain(const HomeDelta& delta);

    // Bytes held by the map's own storage (chunks, items, slots, tables).
    [[nodiscard]] std::size_t memoryBytes() const;

private:
    static constexpr std::uint8_t kWalk = 1;
    static constexpr std::uint8_t kDeck = 2;  // a walkable item on water: steps of one level
    static constexpr std::uint8_t kFloor = 4; // floor height from the occupying item

    struct Chunk {
        std::array<std::uint8_t, kChunkArea> terrain{};
        std::array<std::uint8_t, kChunkArea> level{};
        std::array<std::uint8_t, kChunkArea> district{};
        std::array<std::uint8_t, kChunkArea> walk{};
        std::array<std::uint8_t, kChunkArea> slope{};      // Slope
        std::array<std::uint32_t, kChunkArea> occupancy{}; // item index + 1, 0 = free
        std::vector<std::uint32_t> items; // items whose origin lies here (footprints <= 8 x 8)
        std::vector<std::uint32_t> big;   // larger items overlapping this chunk
    };
    struct District {
        std::string name;
        int region = -1;
    };

    [[nodiscard]] std::size_t chunkIndex(int cx, int cy) const {
        return static_cast<std::size_t>(cy) * static_cast<std::size_t>(cw_) +
               static_cast<std::size_t>(cx);
    }
    [[nodiscard]] const Chunk& chunk(TilePos p) const {
        return chunks_[chunkIndex(p.x >> kChunkShift, p.y >> kChunkShift)];
    }
    [[nodiscard]] Chunk& chunk(TilePos p) {
        return chunks_[chunkIndex(p.x >> kChunkShift, p.y >> kChunkShift)];
    }
    [[nodiscard]] static std::size_t local(TilePos p) {
        return static_cast<std::size_t>(((p.y & (kChunk - 1)) << kChunkShift) |
                                        (p.x & (kChunk - 1)));
    }
    [[nodiscard]] static bool isBig(const Placed& it) {
        return it.w > kMaxFootprint || it.h > kMaxFootprint;
    }
    template <typename F>
    void forEachChunkIn(TileRect r, F&& f) const;

    int internTerrain(const std::string& id);
    int internDistrict(const std::string& name);
    [[nodiscard]] bool walkTileOf(const Placed& it, TilePos p) const;
    [[nodiscard]] int edgeZ(TilePos p, int dir) const; // INT_MIN: no way out on that side
    void shapeSlopesIn(TileRect area);
    void stairHead(Placed& it, Diagnostics& diag) const;
    // Rebuilds chunk item lists, occupancy, connect masks and walk bits over `area`: list
    // entries from `from` on are dropped from the chunks over `area`, then items_[from..] added.
    void index(TileRect area, std::uint32_t from, Diagnostics& diag);
    // Appends the slots of items [begin, end) to slots_.
    void buildSlots(std::uint32_t begin, std::uint32_t end, Diagnostics& diag);
    // Sorts the prebuilt slots by chunk and builds both slot indices.
    void buildSlotIndex();
    void rebuildAll(Diagnostics& diag);
    [[nodiscard]] float themeRadius(int region) const;

    const Content* content_;
    int w_;
    int h_;
    int cw_;
    int ch_;
    int levelPx_;
    float hw_; // half tile width and height, px
    float hh_;
    HomePlacement home_;
    std::vector<std::string> regionIds_;
    std::vector<RegionKind> regionKinds_;
    std::vector<std::string> layers_;
    std::vector<std::pair<std::string, int>> unresolved_;
    std::vector<Chunk> chunks_;
    std::vector<TerrainInfo> terrains_;
    std::vector<District> districts_;
    std::vector<Placed> items_;
    std::uint32_t homeBegin_ = 0; // items_[homeBegin_..] are the player's
    bool homeCleared_ = false;    // the home has been applied once
    // A prebuilt item touching the home rect once the home is applied: kept in the list and its
    // slots (the composed world and every index stay as loaded; city life keeps indices, L-018)
    // but no longer on the map's tiles, so the game's home stands there alone.
    [[nodiscard]] bool underHome(std::uint32_t i) const {
        return homeCleared_ && i < homeBegin_ && items_[i].rect().intersects(home_.rect);
    }
    std::vector<std::uint8_t> homeWild_;
    std::vector<std::array<bool, 4>> slopeFaces_; // per terrain, per aux: a natural face
    std::vector<WorldSlot> slots_;                // prebuilt slots sorted by chunk, then the home's
    std::uint32_t homeSlotBegin_ = 0;
    std::vector<std::uint32_t> slotChunkStart_;    // CSR over chunks of prebuilt slots
    std::vector<std::uint32_t> slotByDistrict_;    // prebuilt slot indices by (district, kind)
    std::vector<std::uint32_t> slotDistrictStart_; // CSR over district * kinds + kind
    std::size_t slotIndexKinds_ = 0;               // kinds when the index was built
    std::vector<std::string> slotNames_;
    std::vector<std::string> slotKinds_;
};

template <typename F>
void WorldMap::forEachChunkIn(TileRect r, F&& f) const {
    r = r.clipped(bounds());
    if (r.empty()) return;
    for (int cy = r.y0 >> kChunkShift; cy <= (r.y1 - 1) >> kChunkShift; ++cy)
        for (int cx = r.x0 >> kChunkShift; cx <= (r.x1 - 1) >> kChunkShift; ++cx) f(cx, cy);
}

template <typename F>
void WorldMap::forEachItemIn(TileRect r, F&& f) const {
    r = r.clipped(bounds());
    if (r.empty()) return;
    const TileRect origins{r.x0 - (kMaxFootprint - 1), r.y0 - (kMaxFootprint - 1), r.x1, r.y1};
    forEachChunkIn(origins, [&](int cx, int cy) {
        for (const std::uint32_t i : chunks_[chunkIndex(cx, cy)].items)
            if (items_[i].rect().intersects(r)) f(i, items_[i]);
    });
    // A big item is listed in every chunk it covers: report it from the chunk holding the top
    // corner of its overlap with r only.
    forEachChunkIn(r, [&](int cx, int cy) {
        for (const std::uint32_t i : chunks_[chunkIndex(cx, cy)].big) {
            const TileRect ov = items_[i].rect().clipped(r);
            if (ov.empty() || (ov.x0 >> kChunkShift) != cx || (ov.y0 >> kChunkShift) != cy)
                continue;
            f(i, items_[i]);
        }
    });
}

template <typename F>
void WorldMap::forEachSlotNear(Vec2 centre, float radius, int kind, F&& f) const {
    const float r2 = radius * radius;
    const auto test = [&](const WorldSlot& s) {
        const float dx = s.at.x - centre.x;
        const float dy = s.at.y - centre.y;
        if ((kind < 0 || s.kind == kind) && dx * dx + dy * dy <= r2) f(s);
    };
    const TileRect box{static_cast<int>(std::floor(centre.x - radius)),
                       static_cast<int>(std::floor(centre.y - radius)),
                       static_cast<int>(std::floor(centre.x + radius)) + 1,
                       static_cast<int>(std::floor(centre.y + radius)) + 1};
    forEachChunkIn(box, [&](int cx, int cy) {
        const std::size_t c = chunkIndex(cx, cy);
        for (std::uint32_t k = slotChunkStart_[c]; k < slotChunkStart_[c + 1]; ++k) test(slots_[k]);
    });
    for (std::size_t k = homeSlotBegin_; k < slots_.size(); ++k) test(slots_[k]);
}

template <typename F>
void WorldMap::forEachSlotInDistrict(int district, int kind, F&& f) const {
    if (district < 0 || district >= static_cast<int>(districts_.size())) return;
    const std::size_t kinds = slotIndexKinds_;
    const std::size_t k0 = kind < 0 ? 0 : static_cast<std::size_t>(kind);
    const std::size_t k1 = kind < 0 ? kinds : k0 + 1;
    for (std::size_t k = k0; k < std::min(k1, kinds); ++k) {
        const std::size_t key = static_cast<std::size_t>(district) * kinds + k;
        if (key + 1 >= slotDistrictStart_.size()) break;
        for (std::uint32_t s = slotDistrictStart_[key]; s < slotDistrictStart_[key + 1]; ++s)
            f(slots_[slotByDistrict_[s]]);
    }
    for (std::size_t s = homeSlotBegin_; s < slots_.size(); ++s) {
        const WorldSlot& slot = slots_[s];
        if ((kind < 0 || slot.kind == kind) && inBounds(slot.tile) &&
            districtAt(slot.tile) == district)
            f(slot);
    }
}

} // namespace lc::world
