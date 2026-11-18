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
#include "worldview/gather.hpp"
#include "worldview/order.hpp"
#include "worldview/overview.hpp"
#include "worldview/page_atlas.hpp"
#include "worldview/theme.hpp"
#include "worldview/world_sprites.hpp"

#include <array>
#include <filesystem>
#include <functional>
#include <memory>
#include <string>
#include <vector>

namespace lc::worldview {

enum class Lod : std::uint8_t { Native, Half, Quarter, Overview };

struct FrameStats {
    Lod lod = Lod::Native;
    int drawCalls = 0;      // composing the frame
    int buildDrawCalls = 0; // rendering cells into the cache
    int spritesDrawn = 0;   // items, pieces and occluding tiles drawn live
    int spritesCulled = 0;  // in the gathered region but off screen
    int cellsBuilt = 0;     // native cells (re)built this frame
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

// Where a frame looks: the centre in world px, window px per world px, the window size, and the
// destination of a flight in progress (gathered on the way).
struct ViewSpec {
    Vec2 centre;
    float scale = 1;
    Vec2 screen{1280, 800};
    bool flying = false;
    Vec2 arrival;
    float arrivalScale = 1;
};

// What a frame draws into, for the game's own scene drawn inside it.
struct FrameInfo {
    SDL_Texture* target = nullptr;
    Xform xf;   // world px -> target px
    FRect view; // world px the target covers
    int w = 0;  // target px in use
    int h = 0;
    Lod lod = Lod::Native;
    SDL_FColor ambient{1, 1, 1, 1}; // the clock's light times the themes' grade
    float scale = 1;                // window px per world px
    Vec2 topLeft;                   // world px at the window's top-left corner
};

// The game's scene (the home region, its actors and effects) drawn at its turns in the frame.
// Each draws into FrameInfo::target and leaves it bound; any may be empty.
struct Hooks {
    std::function<void(const FrameInfo&)> ground;  // after the world's ground, before its shadows
    std::function<void(const FrameInfo&)> objects; // at the home's turn in the painter's order
    std::function<void(const FrameInfo&)> light;   // grades the target (else: flat ambient)
    std::function<void(const FrameInfo&)> glow;    // after the world's glow
    std::function<void(const FrameInfo&)> overlay; // on the output, over the composited world
};

class WorldView {
public:
    // `async`: stream pages and build cells within budgets (interactive and bench runs);
    // otherwise everything a frame needs is loaded and built before it is drawn. `hole`: tiles
    // the game's scene draws itself (the home region), left out of cells and gathering.
    WorldView(SDL_Renderer* renderer, const world::LoadedWorld& world,
              const std::filesystem::path& assets, Atlas& home, Font& font, bool async,
              Hole hole = {});
    ~WorldView();
    WorldView(const WorldView&) = delete;
    WorldView& operator=(const WorldView&) = delete;

    // Draws the frame into the current render target. `clock` is the time of day (0..1),
    // `now` seconds since start (animation, page idling).
    void draw(const WorldCamera& camera, double clock, float dt, double now);
    // The same for the game: its view, its light (season-graded) and its scene's hooks.
    void draw(const ViewSpec& view, double clock, const Lighting& light, float dt, double now,
              const Hooks& hooks);
    // Composites the last frame again onto the current target, scaled by `scale` (a blurred
    // copy for the glass panels); `smooth` filters it.
    void composite(Vec2 scale, bool smooth);
    // The camera jumped: themes snap instead of fading.
    void jumped(const WorldCamera& camera);
    void jumped(Vec2 centre);
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
    [[nodiscard]] const Hole& hole() const { return hole_; }
    // The season whose looks the world wears (the home catalog's index; -1: plain).
    void setSeason(int season);
    // Nothing reads the map on a worker but the gatherer (which never looks inside the hole).
    [[nodiscard]] bool overviewBuilt() const { return !overview_ || overview_->built(); }
    // The hole's tiles changed in the map (its rim is drawn into the cells): redraw them.
    void holeChanged();

private:
    struct Target {
        TexturePtr texture;
        int w = 0;
        int h = 0;
    };

    void warmUp();
    [[nodiscard]] bool put(const SpriteRef& s, Vec2 anchor, const Xform& x, SDL_FColor c,
                           SDL_BlendMode mode, bool mirror = false);
    [[nodiscard]] bool putFace(const SpriteRef& s, int side, Vec2 anchor, const Xform& x,
                               SDL_FColor c);
    // One tile: faces down to its neighbours, the ground, foam, face caps. False when a sprite's
    // page was not resident.
    bool drawTile(TilePos p, const Xform& x, float now, bool* animated);
    // The overview image, built on first need in synchronous runs.
    Overview& overview();
    bool drawTiles(const FRect& px, const Xform& x, float now, bool* animated);
    bool drawElem(const Elem& e, const Xform& x, float now);
    bool drawShadows(const Gathered& g, const FRect& clip, const Xform& x, Target& layer,
                     Target& onto);
    void buildGround(CellKey key, int slot, double now);
    // Impostors: their blocks are gathered on the worker, then drawn a few per frame.
    void requestImpostor(CellKey key, int slot);
    void drawBlock(CellKey key, int slot, int block, const Gathered& g);
    void progressImpostors();
    // The native level's objects: re-gathered on the worker before the view leaves them.
    // `needed`: drawn this frame, so something must exist even if it has to be gathered now.
    void updateRegion(const FRect& view, bool needed);
    void drawCells(int level, const FRect& view, const Xform& x, double now);
    void drawOverview(const Xform& x);
    void drawBackdrops(const FRect& view, const Xform& x, bool night);
    void wantSets(const FRect& view, bool prefetch);
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
    Hole hole_;
    CellCache cells_;
    Batch batch_;
    ThemeMixer theme_;
    bool themed_ = false;
    int season_ = -1;
    float animFps_ = 0;

    Target view_;    // the world at the level's resolution, graded, then composited
    Target shadow_;  // the shadow layer
    Target scratch_; // impostor blocks at full resolution
    Target scratchShadow_;
    Target half_; // impostor downsampling
    int viewW_ = 0;
    int viewH_ = 0;

    // The native level's region: elements around the view in draw order, and the next one.
    std::unique_ptr<Prep> prep_;
    Gathered region_;
    Gathered next_;
    TileRect regionRect_;
    TileRect pendingRect_;
    bool regionPending_ = false;
    Gathered block_;
    struct Building {
        CellKey key;
        int slot = 0;
        std::uint32_t done = 0; // blocks drawn
    };
    std::vector<Building> building_;
    std::vector<std::pair<std::uint16_t, std::uint32_t>> shadows_; // page, element: by page
    std::vector<CellKey> keys_;
    struct Composite {
        CellKey key;
        CellKey from; // the cell drawn for it: itself, or a coarser one while it builds
        int slot = 0;
    };
    std::vector<Composite> composite_;
    std::vector<bool> setSeen_;
    // The last frame's composite onto the window, for composite().
    struct Present {
        Vec2 origin;
        Vec2 topLeft;
        float scale = 1;
        float res = 1;
        Rgb skyTop;
        Rgb skyBottom;
        Grade grade;
        Vec2 screen;
        bool valid = false;
    };
    Present present_;

    // Backdrop sprites by region (day, night), resolved at load; empty when the set has none.
    std::vector<std::array<std::vector<SpriteRef>, 2>> backdrops_;
    FrameStats stats_;
};

} // namespace lc::worldview
