#pragma once
// Terrain and cliff rim, cached per chunk. Each visible chunk is rendered once into a slot of a
// shared page texture and redrawn only when its terrain (or a water frame) changes; slots are
// evicted least-recently-used under a fixed memory budget, so cost follows the view, never the
// map. The overview level caches chunks twice as large at half resolution, so a slot covers the
// same pixels at either level. When a frame needs more slots than the budget allows, the rest of
// the ground is drawn directly.

#include "core/catalog.hpp"
#include "core/world.hpp"
#include "platform/batch.hpp"
#include "platform/sdl_ptr.hpp"
#include "render/atlas.hpp"
#include "render/draw.hpp"
#include "render/sprites.hpp"

#include <cstdint>
#include <functional>
#include <optional>
#include <unordered_map>
#include <vector>

namespace lc {

// The bramble sprite on a wild tile (a stable choice per tile), or none on one tile in five.
[[nodiscard]] std::optional<SpriteId> thicketAt(const SpriteTables& tables, TilePos p);

// The home's ground drawn as the world's is on the shader path (render/gpu/decoder.hpp): from
// the home page's packed twin, through the same decode, with the same climate row and snow, so
// the corner and the land round it wear one snow.
struct GroundDecode {
    SDL_Texture* page = nullptr;               // the home page's packed twin
    const std::vector<bool>* packed = nullptr; // per home sprite: its texels are packed words
    std::function<void(Batch&, bool)> use;     // the decode on (packed sprites) or off
    SDL_BlendMode replace = SDL_BLENDMODE_BLEND;
    float row = 0;  // the remap row (the vertex colour's green)
    float snow = 0; // the snow cover (its blue)
    // On the looks that draw water: the stamp on or off (gpu::Post::stamp) and its blend, so
    // the ground keeps its water marks where it lies over the world's rim tiles or a chunk's
    // border lies over its neighbour. Empty: no stamp.
    std::function<void(Batch&, bool)> stamp;
    SDL_BlendMode stampBlend = SDL_BLENDMODE_INVALID;
};

class GroundCache {
public:
    GroundCache(SDL_Renderer* renderer, const Atlas& atlas, const Catalog& cat,
                const SpriteTables& tables, std::size_t budgetBytes);

    // Draws the ground inside `view` (world px) into `target` with the target's transform.
    // Leaves `target` as the render target.
    void draw(Batch& batch, const World& world, const FRect& view, const Xform& target,
              SDL_Texture* targetTexture, float now);

    // Every cached chunk is drawn afresh (the sprites changed, say for a new season).
    void invalidate();
    // Draw through the packed decode (or not: nullopt); cached chunks are drawn again when what
    // it changes changes.
    void setDecode(std::optional<GroundDecode> d);
    // Cliffs and waterfalls under rims that face open sky (the floating island); none when the
    // land around is the world's.
    void setRims(bool on) {
        if (rims_ != on) invalidate();
        rims_ = on;
    }
    [[nodiscard]] std::size_t bytes() const;
    [[nodiscard]] int slotsRendered() const { return rendered_; }
    // Chunks held in the cache now.
    [[nodiscard]] int chunksCached() const { return static_cast<int>(byKey_.size()); }
    // Chunk side in tiles at a level (0: native resolution, 1: overview).
    [[nodiscard]] static int chunkTiles(int level) { return kBaseChunk << level; }

    static constexpr int kBaseChunk = 16;

private:
    void put(Batch& batch, SpriteId id, Vec2 a, const Xform& x, SDL_FColor c) const;
    std::optional<GroundDecode> decode_;
    struct Slot {
        std::uint64_t key = ~0ULL; // level and chunk coordinates
        std::uint32_t revision = 0;
        std::uint64_t anim = 0;
        bool animated = false;
        std::uint64_t used = 0; // frame it was last drawn
        int page = 0;
        int x = 0; // pixel position in the page
        int y = 0;
    };

    // Draws one tile (cliffs below its open rims, then base, then overlay).
    void drawTile(Batch& batch, const World& world, TilePos p, const Xform& x, float now) const;
    void drawChunk(Batch& batch, const World& world, int level, int cx, int cy, const Xform& x,
                   float now) const;
    // A free or evictable slot, or -1 when every slot is in use this frame.
    int acquire();
    [[nodiscard]] FRect chunkBox(int level, int cx, int cy) const;
    [[nodiscard]] std::uint32_t revisionOf(const World& world, int level, int cx, int cy) const;
    [[nodiscard]] bool hasAnimated(const World& world, int level, int cx, int cy) const;

    SDL_Renderer* renderer_;
    const Atlas& atlas_;
    const Catalog& cat_;
    const SpriteTables& tables_;
    Iso iso_;
    float waterFps_; // waterfalls move with the water
    bool rims_ = true;
    int slotW_ = 0;
    int slotH_ = 0;
    int slotsX_ = 0; // per page
    int slotsY_ = 0;
    std::size_t pageBytes_ = 0;
    std::size_t maxPages_ = 0;
    std::vector<TexturePtr> pages_;
    // Overview chunks are drawn here at full resolution, then halved into their slot in one
    // filtered copy, so tile edges never pick up filtering seams.
    TexturePtr scratch_;
    std::vector<Slot> slots_;
    std::vector<int> free_; // slots holding nothing (after an invalidation), reused first
    std::unordered_map<std::uint64_t, int> byKey_;
    std::uint64_t frame_ = 0;
    int rendered_ = 0;
};

} // namespace lc
