#pragma once
// Draws the diorama: ground, cliffs, shadows, depth-sorted objects and critters, effects, and
// day/night grading (ambient multiply, light pools, occlusion-correct emissive glow).

#include "core/catalog.hpp"
#include "core/clock.hpp"
#include "core/rng.hpp"
#include "core/visitors.hpp"
#include "core/world.hpp"
#include "render/atlas.hpp"
#include "render/batch.hpp"
#include "render/camera.hpp"
#include "render/fx.hpp"
#include "render/sdl_ptr.hpp"
#include "render/sprites.hpp"

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
    float time = 0; // seconds of simulation, drives animation
};

class Scene {
public:
    Scene(SDL_Renderer* renderer, Atlas& atlas, const Catalog& cat);

    void onPlaced(const Item& item, float now, Rng& rng);
    void onRemoved(const Item& item, float now);
    // Spawns and advances effects. Called once per simulation step.
    void update(float dt, const World& world, bool rain, Rng& rng);
    void draw(const FrameParams& p);

    [[nodiscard]] int drawCalls() const { return batch_.drawCalls(); }
    [[nodiscard]] const SpriteTables& sprites() const { return tables_; }
    [[nodiscard]] const Atlas& atlas() const { return atlas_; }

private:
    struct Rect {
        float x0, y0, x1, y1;
    };
    struct Placed {
        Item item;
        int slot = 0;  // sprite variant or connect mask
        Rect screen{}; // world-px bounding box of the base sprite
        bool tree = false;
        bool occludesGlow = false; // overlaps a glowing item, so the glow pass must draw it
    };
    enum class EntryKind : std::uint8_t { Static, Critter, Ghost, Fade };
    struct Entry {
        EntryKind kind;
        std::uint16_t index;
        int after;                 // dynamic entries: drawn after this many static entries
        float depth;               // tie-break among dynamic entries at the same slot
        bool occludesGlow = false; // overlaps a glowing item
    };
    struct Fade {
        Item item;
        int slot;
        float start;
    };
    struct Light {
        Vec2 pos;
        float radius;
    };

    void rebuild(const World& world);
    void ensureTargets(int w, int h);
    [[nodiscard]] int slotFor(const World& world, const Item& item) const;
    [[nodiscard]] Rect spriteRect(const Item& item, int slot) const;
    void buildOrder(const FrameParams& p);
    void sprite(SpriteId id, Vec2 anchor, SDL_FColor color, bool mirror = false, Vec2 pivot = {},
                Vec2 scale = {1, 1});
    void drawItem(const Item& item, int slot, float alpha, SDL_FColor tint, bool silhouette,
                  float scaleY = 1.0f);
    void drawEntries(const FrameParams& p, bool silhouette);
    [[nodiscard]] bool nearGlow(const Rect& r) const;
    void drawCritter(const Critter& c, bool silhouette);
    void drawGround(const World& world);
    void renderGroundCache(const World& world);
    void drawShadows(const FrameParams& p);
    void drawMarkers(const FrameParams& p);
    void drawParticles(bool ground);
    void drawLighting(const FrameParams& p);
    void drawGlow(const FrameParams& p);

    SDL_Renderer* renderer_;
    Atlas& atlas_;
    const Catalog& cat_;
    SpriteTables tables_;
    Batch batch_;
    TexturePtr worldTarget_;
    TexturePtr lightTarget_;
    TexturePtr glowTarget_;
    TexturePtr shadowTarget_;
    // Terrain and cliffs change rarely, so they are cached in one texture and redrawn only when
    // the world or a terrain animation frame changes.
    TexturePtr ground_;
    Rect groundRect_{};
    std::uint64_t groundKey_ = ~0ULL;
    int targetW_ = 0;
    int targetH_ = 0;
    Vec2 origin_; // world px of the target's top-left pixel
    float now_ = 0;

    std::uint64_t revision_ = ~0ULL;
    std::vector<Placed> placed_; // in draw order
    std::vector<Entry> entries_;
    std::vector<Light> lights_;
    std::vector<Rect> glowRects_;
    std::vector<Vec2> chimneys_;
    std::vector<TilePos> water_;
    std::vector<float> popStart_; // per origin tile
    std::vector<Fade> fades_;
    Particles particles_;
    Rect view_{};
};

} // namespace lc
