#pragma once
// Draws the prebuilt world (docs/design/world-tech.md §4.3–§4.7) at four levels of detail:
//
// - native (zoom 1 and up): the ground (terrain at its level, faces stacked under raised edges,
//   water and foam) from level-0 cells cached once into textures; shadows composited as one
//   layer; items and landmark pieces depth-sorted with the raised tiles that hide them, gathered
//   for a region around the view and re-sorted only when the view leaves it; glow after grading;
// - half and quarter scale: level-1 and level-2 cell impostors of everything static;
// - the overview: one generated map of the whole world.
//
// Cells are built within a per-frame budget (all at once in synchronous runs); a cell not built
// yet shows its coarser level, so nothing flashes. Atlas pages stream by the sets of the regions
// around the view. Region themes grade the view with the clock and cross-fade by position.

#include "core/clock.hpp"
#include "platform/batch.hpp"
#include "render/atlas.hpp"
#include "render/draw.hpp"
#include "ui/font.hpp"
#include "world/loader.hpp"
#include "worldview/camera.hpp"
#include "worldview/cell_cache.hpp"
#include "worldview/order.hpp"
#include "worldview/overview.hpp"
#include "worldview/page_atlas.hpp"
#include "worldview/theme.hpp"
#include "worldview/world_sprites.hpp"

#include <array>
#include <filesystem>
#include <memory>
#include <string>
#include <vector>

namespace lc::worldview {

enum class Lod : std::uint8_t { Native, Half, Quarter, Overview };

struct FrameStats {
    Lod lod = Lod::Native;
    int drawCalls = 0;
    int spritesDrawn = 0;  // items, pieces and occluding tiles drawn live
    int spritesCulled = 0; // in the gathered region but off screen
    int cellsBuilt = 0;    // native cells (re)built this frame
    int impostorsBuilt = 0;
    int cellsCached = 0;
    int cellsPending = 0; // visible cells still to build (shown from a coarser level)
    int regionElements = 0;
    bool regionRebuilt = false;
    std::size_t cellBytes = 0;
    std::size_t targetBytes = 0;
    std::size_t overviewBytes = 0;
    PageStats pages;
    [[nodiscard]] std::size_t textureBytes() const {
        return cellBytes + targetBytes + overviewBytes + pages.bytes;
    }
};

class WorldView {
public:
    // `async`: stream pages and build cells within budgets (interactive and bench runs);
    // otherwise everything a frame needs is loaded and built before it is drawn.
    WorldView(SDL_Renderer* renderer, const world::LoadedWorld& world,
              const std::filesystem::path& assets, Atlas& home, Font& font, bool async);
    ~WorldView();
    WorldView(const WorldView&) = delete;
    WorldView& operator=(const WorldView&) = delete;

    // Draws the frame into the current render target. `clock` is the time of day (0..1),
    // `now` seconds since start (animation, page idling).
    void draw(const WorldCamera& camera, double clock, float dt, double now);
    // The camera jumped: themes snap instead of fading.
    void jumped(const WorldCamera& camera);
    // Nothing is left to stream or build for the last frame's view.
    [[nodiscard]] bool settled() const;

    [[nodiscard]] const FrameStats& stats() const { return stats_; }
    [[nodiscard]] const ThemeMixer& theme() const { return theme_; }
    [[nodiscard]] const WorldSprites& sprites() const { return *sprites_; }
    [[nodiscard]] const PageAtlas& pages() const { return *pages_; }
    // The era caption showing now (empty when none) and its opacity.
    [[nodiscard]] std::string caption() const;
    [[nodiscard]] float captionAlpha() const { return theme_.captionAlpha(); }
    [[nodiscard]] static Lod lodFor(float scale);

private:
    struct Elem {
        const VariantLook* look = nullptr;
        std::uint32_t item = 0;
        std::int16_t piece = -1; // -1: the whole sprite
        bool ground = false;     // a raised tile drawn over what it hides
        bool first = false;      // the item's first element: draws its shadow and glow
        TilePos tile;
        Vec2 anchor;
    };
    struct Target {
        TexturePtr texture;
        int w = 0;
        int h = 0;
    };

    [[nodiscard]] bool put(const SpriteRef& s, Vec2 anchor, const Xform& x, SDL_FColor c,
                           SDL_BlendMode mode, bool mirror = false);
    // One tile: faces down to its neighbours, the ground, foam, face caps. False when a sprite's
    // page was not resident.
    bool drawTile(TilePos p, const Xform& x, float now, bool* animated);
    bool drawTiles(const FRect& px, const Xform& x, float now, bool* animated);
    // Elements whose sprites meet `clip` among the items over `tiles`, with the raised tiles
    // that hide them, into elems_/items_ (cleared first).
    void gather(TileRect tiles, const FRect& clip);
    void sortGathered();
    bool drawElem(const Elem& e, const Xform& x, float now);
    bool drawShadows(std::span<const std::uint32_t> order, const FRect& clip, const Xform& x,
                     Target& layer, Target& onto);
    void buildCell(CellKey key, int slot, double now);
    void drawCells(int level, const FRect& view, const Xform& x, double now);
    void drawOverview(const Xform& x);
    void drawBackdrops(const FRect& view, const Xform& x, bool night);
    void wantSets(const FRect& view);
    void ensure(Target& t, int w, int h);
    [[nodiscard]] std::size_t targetBytes() const;
    void fullQuad(int w, int h, SDL_FColor c, SDL_BlendMode mode);
    [[nodiscard]] float shadowOpacity() const;

    SDL_Renderer* renderer_;
    const world::LoadedWorld& world_;
    const world::WorldMap& map_;
    Iso iso_;
    int lvl_;
    bool async_;
    std::unique_ptr<PageAtlas> pages_;
    std::unique_ptr<WorldSprites> sprites_;
    std::unique_ptr<Overview> overview_;
    CellCache cells_;
    Batch batch_;
    ThemeMixer theme_;
    bool themed_ = false;
    float animFps_ = 0;

    Target view_;    // the world at the level's resolution, graded, then composited
    Target shadow_;  // the shadow layer
    Target scratch_; // impostor blocks at full resolution
    Target scratchShadow_;
    Target half_; // impostor downsampling
    int viewW_ = 0;
    int viewH_ = 0;

    // The native level's region: elements around the view in draw order.
    TileRect region_;
    std::vector<Elem> regionElems_;
    std::vector<OrderItem> regionItems_;
    std::vector<std::uint32_t> regionOrder_;
    // Scratch for gathering (regions and impostor blocks).
    std::vector<world::DrawPiece> pieces_;
    std::vector<Elem> elems_;
    std::vector<OrderItem> items_;
    std::vector<std::uint32_t> order_;
    std::vector<std::uint32_t> stamp_; // per map item: gathering pass it was last seen in
    std::uint32_t pass_ = 0;
    PageOrder sorter_;
    std::vector<CellKey> keys_;
    std::vector<bool> setSeen_;

    // Backdrop sprites by region (day, night), resolved at load; empty when the set has none.
    std::vector<std::array<std::vector<SpriteRef>, 2>> backdrops_;
    FrameStats stats_;
};

} // namespace lc::worldview
