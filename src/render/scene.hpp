#pragma once
// Draws the diorama: ground, cliffs, shadows, depth-sorted objects and critters, effects, and
// day/night grading (ambient multiply with per-sprite exposure, ground light pools,
// occlusion-correct emissive glow).
//
// Everything scales with the view, not the map: the ground comes from a per-chunk cache, and the
// objects near the camera are gathered into a region (the view plus a margin) whose depth order,
// lights and effect sources are rebuilt only when the world changes or the view leaves it. Each
// frame then culls that region to the view.

#include "core/actors.hpp"
#include "core/catalog.hpp"
#include "core/clock.hpp"
#include "core/condition.hpp"
#include "core/rng.hpp"
#include "core/tuning.hpp"
#include "core/weather.hpp"
#include "core/world.hpp"
#include "platform/batch.hpp"
#include "platform/sdl_ptr.hpp"
#include "render/atlas.hpp"
#include "render/camera.hpp"
#include "render/depth.hpp"
#include "render/draw.hpp"
#include "render/fx.hpp"
#include "render/ground.hpp"
#include "render/order.hpp"
#include "render/sprites.hpp"

#include <memory>
#include <optional>
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
    std::span<const Actor> actors;
    int resident = -1;                      // her actor, for butterflies on her hat
    const Weather* weather = nullptr;       // cloud shadows, wet ground, rain on her umbrella
    std::span<const Ghost> ghosts;          // what the tool would do: one, or a line, brush or area
    std::span<const NearInstance> outlines; // nook areas to outline (the hovered nook, or all)
    float grid = 0;                         // opacity of the tile grid over open land (0: off)
    bool footprints = false;                // every item's footprint, softly marked
    const Camera* camera = nullptr;
    Vec2 screen;
    Lighting light;
    float rainbow = 0;        // the rainbow's visibility, 0..1
    bool fireflySync = false; // fireflies blink in unison
};

struct SceneStats {
    std::size_t regionItems = 0;
    std::size_t drawnItems = 0;
    std::size_t targetBytes = 0;
    std::size_t groundBytes = 0;
    int groundSlotsRendered = 0;
    int groundChunksCached = 0;
};

class Scene {
public:
    Scene(SDL_Renderer* renderer, Atlas& atlas, const Catalog& cat);

    // Another world opens: every cache keyed by world revisions and every passing effect goes.
    void resetWorld();
    void onPlaced(const Item& item, Rng& rng);
    void onRemoved(const Item& item);
    // A few sparkles rising from a spot on the ground (continuous tile coordinates).
    void burst(Vec2 tile, Rng& rng);
    // A growing item reached its next stage: the place pop, without sparkles.
    void popAt(TilePos origin);
    // Something picked from a bed rises and fades (`crop`: which produce frame).
    void produce(const Item& bed, int crop);
    // A newly found nook: its area pulses and sparkles.
    void flourish(const NearInstance& nook, const World& world, Rng& rng);
    // A land stage just opened (its tiles are open already): the brambles clear in a wave from
    // the open land outwards and the revealed items pop up as it passes. Returns its length.
    float landWave(const World& world, const Catalog& cat, int stage,
                   std::span<const Item> revealed);
    // Spawns and advances effects near the camera. Called once per simulation step. Rain and
    // snow fall where the weather has them; the wind leans smoke, leaves and trees.
    void update(float dt, const World& world, std::span<const Actor> actors, const Weather& weather,
                Rng& rng);
    // A heart rising from an actor that was petted.
    void heart(const Actor& a);
    // Trees near a tile shake and drop a few leaves (something was placed beside them).
    void rustle(Vec2 tile, Rng& rng);
    // A fish arcs out of a water tile.
    void fishJump(Vec2 tile);
    // A shooting star crosses the sky.
    void shootingStar(Rng& rng);
    // Chimney smoke of the item at `origin` thickens (cooking), or stops doing so.
    void cooking(std::optional<TilePos> origin) { cooking_ = origin; }
    // Where an actor's head is, in world pixels (speech bubbles, hats).
    [[nodiscard]] Vec2 headOf(const Actor& a) const;
    // The actor under a world-pixel point, topmost first, if any.
    [[nodiscard]] std::optional<int> actorAt(std::span<const Actor> actors, Vec2 world) const;
    // The season's sprite looks, falling things and whether rain falls as snow (-1: plain).
    void setSeason(int season);
    // Reduce motion (living-corner R10.8): particles at 30 %, no streaks, moths, z's, pulse
    // ring or gust wave; land opens in a short fade.
    void setReduceMotion(bool on) {
        reduceMotion_ = on;
        thin_ = on ? tuning::kReduceMotionParticles : 1.0f;
    }
    // The floating island (cliffs, waterfalls and sky around the land), or land that meets the
    // world around it (no rims: the world renderer draws what lies beyond).
    void setFloating(bool on);
    [[nodiscard]] bool floating() const { return floating_; }
    // Renders the frame's layers and composites them onto `out` (the window when null).
    void draw(const FrameParams& p, SDL_Texture* out = nullptr);

    // Inside the world's frame (world mode): the scene draws into the world renderer's target
    // with its transform, moved from world px to this map's px by `offset` (world = map + offset),
    // one phase at each of the renderer's turns. embedBegin first, every frame.
    struct Embed {
        SDL_Texture* target = nullptr;
        Xform xf; // world px -> target px
        int w = 0;
        int h = 0;
        Vec2 offset;
    };
    void embedBegin(const FrameParams& p, const Embed& e);
    // The ground, the shadow layer, markers, things on the ground and swimmers.
    void embedGround(const FrameParams& p);
    // Items, actors and ghosts in depth order, and the particles over them.
    void embedObjects(const FrameParams& p);
    // Multiplies the target by the light map: `ambient` with the light pools of lamps and fire.
    void embedLight(const FrameParams& p, Rgb ambient);
    void embedGlow(const FrameParams& p);
    // The rainbow and shooting stars over the composited view (window px).
    void embedSky(const FrameParams& p);
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
    // How far item sprites reach from their anchors, world px.
    [[nodiscard]] const Reach& itemReach() const { return itemReach_; }
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
    enum class EntryKind : std::uint8_t { Actor, Ghost, Fade };
    struct Entry {
        EntryKind kind;
        std::uint32_t index;
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
    struct Pulse {
        NearInstance area;
        float start;
    };
    struct WaveTile {
        TilePos tile;
        float start; // when its brambles begin to clear
        std::optional<SpriteId> thicket;
        bool cleared = false;
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
    // Shared by draw() and embedBegin(): the region around the view and this frame's state.
    void beginFrame(const FrameParams& p);
    [[nodiscard]] const FrameSet& baseFrames(const Item& item, int slot) const;
    void ensureTargets(int w, int h, bool own);
    [[nodiscard]] int slotFor(const World& world, const Item& item) const;
    [[nodiscard]] FRect spriteRect(const Item& item, int slot) const;
    [[nodiscard]] FRect actorRect(const Actor& a) const;
    [[nodiscard]] std::size_t animOf(const Actor& a) const;
    [[nodiscard]] bool flying(const Actor& a) const;
    [[nodiscard]] bool glows(const Actor& a) const;
    [[nodiscard]] Vec2 actorAnchor(const Actor& a) const;
    // A world px point on the nearest pixel of this frame's target.
    [[nodiscard]] Vec2 snapped(Vec2 world) const;
    [[nodiscard]] float popOf(TilePos origin) const;
    [[nodiscard]] OrderItem itemBox(const Placed& p, std::uint32_t id) const;
    void buildDynamic(const FrameParams& p);
    void sprite(SpriteId id, Vec2 anchor, SDL_FColor color, bool mirror = false, Vec2 pivot = {},
                Vec2 scale = {1, 1});
    void drawItem(const Item& item, int slot, float alpha, SDL_FColor tint, bool silhouette,
                  float scaleY = 1.0f);
    void drawEntry(const FrameParams& p, const Entry& e, bool silhouette);
    void drawEntries(const FrameParams& p, bool silhouette);
    [[nodiscard]] bool nearGlow(const FRect& r) const;
    void drawActor(const Actor& a, bool silhouette);
    void drawMoths(const FrameParams& p);
    void drawSky(const FrameParams& p, Vec2 scale);
    void drawShadows(const FrameParams& p);
    void drawMarkers(const FrameParams& p);
    // Tiles of a nook's area (around its anchor, not under it), in the given colour.
    void drawArea(const World& world, const NearInstance& area, SDL_FColor color);
    void drawParticles(bool ground);
    void drawLighting(const FrameParams& p, Rgb ambient);
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
    SDL_Texture* into_ = nullptr; // the target this frame draws into (world_ or the world's)
    bool floating_ = true;
    TexturePtr white_; // one white texel, for flat multiplies
    int targetW_ = 0;
    int targetH_ = 0;
    Xform xf_; // world -> target for this frame
    SDL_BlendMode blend_ = SDL_BLENDMODE_BLEND;
    Vec2 topLeft_; // world px at the window's top-left corner
    FRect view_;   // world px the target covers
    float now_ = 0;
    float night_ = 0; // exposure grading strength this frame
    int season_ = -1;
    Reach itemReach_; // how far item sprites reach from their anchor

    // The region: objects near the camera in draw order, and what derives from them.
    TileRect region_;
    std::uint64_t regionRevision_ = ~0ULL;
    std::vector<Placed> placed_;     // in draw order
    std::vector<OrderItem> boxes_;   // per placed item: its box (draw-order.md §1.2)
    std::vector<OrderItem> sorting_; // per gathered item, while sorting
    std::vector<std::uint32_t> order_;
    std::vector<std::uint32_t> identity_; // the placed items' own order: 0, 1, 2 ...
    OrderGraph graph_;                    // by gathered item, then by place in the order
    std::vector<Placed> gathered_;
    PageOrder sorter_;
    ScreenGrid grid_;                     // region items' screen boxes, in draw order
    ActorMerge merge_;                    // this frame's actors, ghosts and fades among them
    std::vector<OrderItem> dynamicBoxes_; // per dynamic_ entry
    std::vector<float> actorRank_;        // per actor: its place in the frame's order, -1: none
    std::vector<Light> lights_;
    std::vector<FRect> glowRects_;
    struct Chimney {
        Vec2 at;
        TilePos origin;
    };
    std::vector<Chimney> chimneys_;
    struct Fall {
        Vec2 foot; // where its mist rises, world px
    };
    std::vector<Fall> falls_;
    std::vector<Vec2> moths_; // lamp heads, world px
    struct Rustle {
        TilePos tile;
        float end;
    };
    std::vector<Rustle> rustles_;
    struct Star {
        float start = -1;
        Vec2 from; // window fractions
        Vec2 dir;
    };
    Star star_;
    std::optional<TilePos> cooking_;
    std::span<const Actor> actors_; // this frame's, for hats
    int resident_ = -1;
    const Weather* weather_ = nullptr;
    const World* map_ = nullptr; // the world being drawn this frame
    Wind wind_;
    float sway_ = 0;      // wind-driven sway clock for trees and grass
    float sleepTick_ = 0; // z's rise from sleepers every few seconds
    bool fireflySync_ = false;
    bool reduceMotion_ = false;
    float thin_ = 1.0f; // particle rate factor
    std::vector<std::uint32_t> trees_;
    std::vector<TilePos> water_;
    std::size_t drawnItems_ = 0;

    std::vector<Entry> dynamic_;
    std::vector<Fade> fades_;
    std::vector<Pop> pops_;
    std::vector<Pulse> pulses_;
    std::vector<WaveTile> wave_;
    float waveEnd_ = 0;
    Particles particles_;
};

} // namespace lc
