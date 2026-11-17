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
#include <unordered_map>
#include <vector>

namespace lc {

class GroundCache {
public:
    GroundCache(SDL_Renderer* renderer, const Atlas& atlas, const Catalog& cat,
                const SpriteTables& tables, std::size_t budgetBytes);

    // Draws the ground inside `view` (world px) into `target` with the target's transform.
    // Leaves `target` as the render target.
    void draw(Batch& batch, const World& world, const FRect& view, const Xform& target,
              SDL_Texture* targetTexture, float now);

    [[nodiscard]] std::size_t bytes() const;
    [[nodiscard]] int slotsRendered() const { return rendered_; }
    // Chunk side in tiles at a level (0: native resolution, 1: overview).
    [[nodiscard]] static int chunkTiles(int level) { return kBaseChunk << level; }

    static constexpr int kBaseChunk = 16;

private:
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
    std::unordered_map<std::uint64_t, int> byKey_;
    std::uint64_t frame_ = 0;
    int rendered_ = 0;
};

} // namespace lc
