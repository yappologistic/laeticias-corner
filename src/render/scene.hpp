#pragma once
// Draws the diorama: ground, cliffs, shadows, depth-sorted objects and critters, effects, and
// day/night grading (ambient multiply with per-sprite exposure, ground light pools,
// occlusion-correct emissive glow).
//
// Everything scales with the view, not the map: the ground comes from a per-chunk cache, and the
// objects near the camera are gathered into a region (the view plus a margin) whose depth order,
// lights and effect sources are rebuilt only when the world changes or the view leaves it. Each
// frame then culls that region to the view.

#include "core/catalog.hpp"
#include "core/clock.hpp"
#include "core/rng.hpp"
#include "core/visitors.hpp"
#include "core/world.hpp"
#include "platform/batch.hpp"
#include "platform/sdl_ptr.hpp"
#include "render/atlas.hpp"
#include "render/camera.hpp"
#include "render/depth.hpp"
#include "render/draw.hpp"
#include "render/fx.hpp"
#include "render/ground.hpp"
#include "render/sprites.hpp"

#include <memory>
#include <span>
#include <vector>

namespace lc {

struct Ghost {
    enum class Mode : std::uint8_t { None, Item, Tile, Remove };
    Mode mode = Mode::None;
    Item item;          // Item: the piece being placed
    TilePos tile;       // Tile / Remove: tile under the cursor
    bool valid = false; // tints the ghost and its tile markers
};

struct FrameParams {
    const World* world = nullptr;
    std::span<const Critter> critters;
    Ghost ghost;
    const Camera* camera = nullptr;
    Vec2 screen;
    Lighting light;
};

struct SceneStats {
    std::size_t regionItems = 0;
    std::size_t drawnItems = 0;
    std::size_t targetBytes = 0;
    std::size_t groundBytes = 0;
    int groundSlotsRendered = 0;
};

class Scene {
public:
    Scene(SDL_Renderer* renderer, Atlas& atlas, const Catalog& cat);

    void onPlaced(const Item& item, Rng& rng);
    void onRemoved(const Item& item);
    // Spawns and advances effects near the camera. Called once per simulation step.
    void update(float dt, const World& world, std::span<const Critter> critters, bool rain,
                Rng& rng);
    // Renders the frame's layers and composites them onto the window.
    void draw(const FrameParams& p);
    // Composites the layers rendered by the last draw() onto the current render target, scaled
    // by `scale`; `smooth` filters the world linearly (for blurred copies).
    void composite(const FrameParams& p, Vec2 scale, bool smooth);

    // Tile rectangle the camera currently sees (plus sprite overhang), clipped to the map.
    [[nodiscard]] TileRect visibleTiles(const Camera& camera, Vec2 screen,
                                        const World& world) const;
    // How far cliff faces reach below the south rims, in world px (for framing).
    [[nodiscard]] float cliffDepth() const { return tables_.groundReach.bottom; }
    [[nodiscard]] int drawCalls() const { return batch_.drawCalls(); }
    [[nodiscard]] const SpriteTables& sprites() const { return tables_; }
    [[nodiscard]] const Atlas& atlas() const { return atlas_; }
    [[nodiscard]] SceneStats stats() const;

private:
    struct Placed {
        Item item;
        int slot = 0; // sprite variant or connect mask
        FRect screen; // world-px box of the base sprite
        bool tree = false;
        bool occludesGlow = false; // overlaps a glowing item, so the glow pass must draw it
    };
    enum class EntryKind : std::uint8_t { Critter, Ghost, Fade };
    struct Entry {
        EntryKind kind;
        std::uint32_t index;
        std::uint32_t after;       // drawn after this many region items
        float depth;               // tie-break among dynamic entries at the same slot
        bool occludesGlow = false; // overlaps a glowing item
    };
    struct Fade {
        Item item;
        int slot;
        float start;
    };
    struct Pop {
        TilePos origin;
        float start;
    };
    struct Light {
        Vec2 pos;
        float radius;
    };
    struct Target {
        TexturePtr texture;
        int w = 0; // allocated size; the frame uses the top-left targetW_ x targetH_
        int h = 0;
    };

    void rebuild(const World& world, TileRect region);
    void ensureTargets(int w, int h);
    [[nodiscard]] int slotFor(const World& world, const Item& item) const;
    [[nodiscard]] FRect spriteRect(const Item& item, int slot) const;
    [[nodiscard]] FRect critterRect(const Critter& c) const;
    [[nodiscard]] float popOf(TilePos origin) const;
    void buildDynamic(const FrameParams& p);
    void sprite(SpriteId id, Vec2 anchor, SDL_FColor color, bool mirror = false, Vec2 pivot = {},
                Vec2 scale = {1, 1});
    void drawItem(const Item& item, int slot, float alpha, SDL_FColor tint, bool silhouette,
                  float scaleY = 1.0f);
    void drawEntry(const FrameParams& p, const Entry& e, bool silhouette);
    void drawEntries(const FrameParams& p, bool silhouette);
    [[nodiscard]] bool nearGlow(const FRect& r) const;
    void drawCritter(const Critter& c, bool silhouette);
    void drawShadows(const FrameParams& p);
    void drawMarkers(const FrameParams& p);
    void drawParticles(bool ground);
    void drawLighting(const FrameParams& p);
    void drawGlow(const FrameParams& p);
    void fullQuad(SDL_Texture* texture, SDL_BlendMode mode, SDL_FColor color);
    [[nodiscard]] SDL_FColor exposed(SpriteId id, SDL_FColor c) const;

    SDL_Renderer* renderer_;
    Atlas& atlas_;
    const Catalog& cat_;
    Iso iso_;
    SpriteTables tables_;
    Batch batch_;
    std::unique_ptr<GroundCache> ground_;
    Target world_;
    Target light_;
    Target glow_;
    Target shadow_;
    int targetW_ = 0;
    int targetH_ = 0;
    Xform xf_; // world -> target for this frame
    SDL_BlendMode blend_ = SDL_BLENDMODE_BLEND;
    Vec2 topLeft_; // world px at the window's top-left corner
    FRect view_;   // world px the target covers
    float now_ = 0;
    float night_ = 0; // exposure grading strength this frame
    Reach itemReach_; // how far item sprites reach from their anchor

    // The region: objects near the camera in draw order, and what derives from them.
    TileRect region_;
    std::uint64_t regionRevision_ = ~0ULL;
    std::vector<Placed> placed_;
    std::vector<FRect> footprints_;
    std::vector<FRect> screens_;
    std::vector<std::uint32_t> order_;
    std::vector<Placed> gathered_;
    DepthSorter sorter_;
    ScreenGrid grid_; // region items' screen boxes, in draw order
    std::vector<Light> lights_;
    std::vector<FRect> glowRects_;
    std::vector<Vec2> chimneys_;
    std::vector<std::uint32_t> trees_;
    std::vector<TilePos> water_;
    std::size_t drawnItems_ = 0;

    std::vector<Entry> dynamic_;
    std::vector<Fade> fades_;
    std::vector<Pop> pops_;
    Particles particles_;
};

} // namespace lc
