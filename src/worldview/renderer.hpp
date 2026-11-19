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
#include "life/city.hpp"
#include "platform/batch.hpp"
#include "render/atlas.hpp"
#include "render/draw.hpp"
#include "render/order.hpp"
#include "ui/font.hpp"
#include "world/figures.hpp"
#include "world/loader.hpp"
#include "worldview/actor_looks.hpp"
#include "worldview/camera.hpp"
#include "worldview/cell_cache.hpp"
#include "worldview/cover.hpp"
#include "worldview/gather.hpp"
#include "worldview/overview.hpp"
#include "worldview/page_atlas.hpp"
#include "worldview/places.hpp"
#include "worldview/theme.hpp"
#include "worldview/weather_field.hpp"
#include "worldview/world_sprites.hpp"

#include <array>
#include <filesystem>
#include <functional>
#include <memory>
#include <optional>
#include <span>
#include <string>
#include <vector>

namespace lc::worldview {

enum class Lod : std::uint8_t { Native, Half, Quarter, Overview };

struct FrameStats {
    Lod lod = Lod::Native;
    bool lodHeld = false;   // a coarser level stood in while the native one was made ready
    int drawCalls = 0;      // composing the frame
    int buildDrawCalls = 0; // rendering cells into the cache
    int spritesDrawn = 0;   // items, pieces and occluding tiles drawn live
    int placeholders = 0;   // of them, drawn as placeholders (no art yet)
    int spritesCulled = 0;  // in the gathered region but off screen
    int cellsBuilt = 0;     // native cells (re)built this frame
    int impostorsBuilt = 0;
    int cellsCached = 0;
    int cellsPending = 0; // visible cells still to build (shown from a coarser level)
    // Pop-in, as the player would see it: the share of the view those cells cover, how many of
    // them had no coarser cell either (the overview map shows through), live sprites left out
    // because their page was still streaming, and whether the gathered objects fell short of
    // the view (things missing along an edge).
    float pendingShare = 0;
    int cellsBare = 0;
    int spritesMissing = 0;
    bool regionShort = false;
    // Cache work done on the main thread this frame.
    int blocksBuilt = 0;         // impostor blocks drawn
    double buildMs = 0;          // ground cells and impostor blocks
    double uploadMs = 0;         // page slices
    std::size_t uploadBytes = 0; // page pixels uploaded
    double gatherMs = 0;         // a region gathered at once (nothing gathered there yet)
    int prefetchPending = 0;     // cells of the neighbouring levels and the ring still to build
    int regionElements = 0;
    int actorsDrawn = 0; // city life's people, animals, carts and ships
    double actorMs = 0;  // gathering, resolving and merging them
    bool regionRebuilt = false;
    std::size_t cellBytes = 0;
    std::size_t targetBytes = 0;
    std::size_t overviewBytes = 0;
    PageStats pages;
    [[nodiscard]] std::size_t textureBytes() const {
        return cellBytes + targetBytes + overviewBytes + pages.bytes;
    }
    // Something in view is not what it should be yet.
    [[nodiscard]] bool popIn() const {
        return cellsPending > 0 || spritesMissing > 0 || regionShort || lodHeld;
    }
};

// Where a frame looks: the centre in world px, window px per world px, the window size; where
// the view is heading while a zoom, a flight or a journey is under way (its destination is made
// ready on the way); and the world px under the pointer, about which a turn of the wheel zooms
// (the wider levels are built ahead around it).
struct ViewSpec {
    Vec2 centre;
    float scale = 1;
    Vec2 screen{1280, 800};
    bool heading = false;
    Vec2 arrival;
    float arrivalScale = 1;
    Vec2 pointer;
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

// The game's scene (the home region, its actors and effects) drawn at its turns in the frame,
// while the home is in view (else the world grades itself). Each draws into FrameInfo::target
// and leaves it bound; any may be empty.
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
              const std::filesystem::path& assets, Atlas& home, bool async, Hole hole = {},
              const std::vector<world::FigurePlace>& figures = {});
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
    // And nothing is being built or loaded ahead of need either: the steady state.
    [[nodiscard]] bool idle() const {
        return settled() && stats_.prefetchPending == 0 && stats_.pages.streaming == 0;
    }

    [[nodiscard]] const FrameStats& stats() const { return stats_; }
    [[nodiscard]] const ThemeMixer& theme() const { return theme_; }
    [[nodiscard]] const WorldSprites& sprites() const { return *sprites_; }
    [[nodiscard]] const PageAtlas& pages() const { return *pages_; }
    // The place the view is in and its era caption (world-tech §4.8).
    [[nodiscard]] const PlaceTracker& places() const { return places_; }
    // The era caption showing now (empty when none) and its opacity.
    [[nodiscard]] std::string caption() const;
    [[nodiscard]] float captionAlpha() const { return places_.captionAlpha(); }
    [[nodiscard]] static Lod lodFor(float scale);
    [[nodiscard]] const Hole& hole() const { return hole_; }
    // What is drawn under a world px point, topmost first: an item that has a card, or a figure.
    struct Picked {
        bool figure = false;
        std::uint32_t index = 0; // map item, or index into the figures given
    };
    [[nodiscard]] std::optional<Picked> pick(Vec2 worldPx) const;
    // Everything with a card, and every figure, on screen in the last frame (once each).
    void visibleCards(std::vector<Picked>& out) const;
    // Figures without art (not drawn).
    [[nodiscard]] int figuresMissing() const { return figuresMissing_; }
    // What the world's textures may hold: the pages' slots, the cell cache at this window size,
    // the targets and the overview.
    [[nodiscard]] std::size_t textureBudget() const;
    // Ids with no art of their own: placeholder items, flat terrain and faces, figures, and ids
    // the layers place that no catalog defines (not drawn).
    [[nodiscard]] int missingArt() const;
    // Placeholders on screen in the last frame: where (world px, at their anchor) and what.
    void placeholdersInView(std::vector<std::pair<Vec2, std::uint32_t>>& out) const;
    // The weather drawn over the world (cloud shadows, wet ground, rain and snow) from now on;
    // null draws none. The home's hole is left to the game's scene, which draws the same cells.
    void setWeather(const WeatherField* weather) { weather_ = weather; }
    // The season whose looks the world wears (the home catalog's index; -1: plain).
    void setSeason(int season);
    // Nothing reads the map on a worker but the gatherer (which never looks inside the hole).
    [[nodiscard]] bool overviewBuilt() const { return !overview_ || overview_->built(); }
    // The hole's tiles changed in the map (its rim is drawn into the cells): redraw them.
    void holeChanged();
    // City life drawn from now on, in the world's painter's order (null: none). Its looks are
    // resolved on the first call. `alpha` places actors between the last two simulation steps.
    void setLife(const life::CityLife* city);
    void setLifeAlpha(float alpha) { lifeAlpha_ = alpha; }
    [[nodiscard]] const ActorLooks* actorLooks() const { return looks_.get(); }
    // The actors drawn under a world px point in the last frame, frontmost first (into `out`).
    void actorsAt(Vec2 worldPx, std::vector<life::Handle>& out) const;
    // Of the people drawn over the impostors in the last frame (half and quarter scale), how
    // many have more than `px` rows drawn inside something in front of them: worked out one by
    // one from the map's items, their boxes and the comparator, not from the top field that cut
    // them, so tests can hold the one against the other.
    [[nodiscard]] int coarseActorsCovered(float px) const;
    [[nodiscard]] int coarseActorsDrawn() const { return static_cast<int>(coarse_.size()); }
    // Pairs drawn in the last frame that overlap on screen yet go against the comparator (the
    // order oracle, draw-order.md §6.1), and cycles its sorts had to break: both zero when right.
    [[nodiscard]] int orderViolations() const;
    [[nodiscard]] int orderCycles() const;
    // People drawn in the last frame (native level) standing on a floor or deck lower than its
    // surface, by the art's geometry: walking through a bridge rather than on it. Boats excluded.
    [[nodiscard]] int sunkActors() const;
    // The actors drawn in the last frame.
    [[nodiscard]] std::span<const life::DrawActor> actorsDrawn() const {
        return std::span(actorBuf_).first(actorCount_);
    }

private:
    struct Target {
        TexturePtr texture;
        int w = 0;
        int h = 0;
    };

    void warmUp();
    [[nodiscard]] bool put(const SpriteRef& s, Vec2 anchor, const Xform& x, SDL_FColor c,
                           SDL_BlendMode mode, bool mirror = false);
    // One tile: faces down to its neighbours, the ground, foam, face caps. False when a sprite's
    // page was not resident.
    bool drawTile(TilePos p, const Xform& x, float now, bool* animated);
    // The overview image, built on first need in synchronous runs.
    Overview& overview();
    bool drawTiles(const FRect& px, const Xform& x, float now, bool* animated);
    // Open sea beyond the grid, deep and fading into haze with the distance from its edge.
    // (`haze`: the haze over it, drawn after all of the water.)
    bool drawBeyond(TilePos p, const Xform& x, bool haze);
    bool drawElem(const Elem& e, const Xform& x, float now);
    // `actors`: with the live people's shadows (the frame, not a cached picture). `visible`:
    // the order's positions drawn this frame (empty: look at all of them).
    bool drawShadows(const Gathered& g, const FRect& clip, const Xform& x, Target& layer,
                     Target& onto, bool actors, std::span<const std::uint32_t> visible = {});
    // Cells (cells.hpp): each frame says what it wants, in order of need: the view's own
    // cells, those of a destination it is heading for, a ring around the view leaning the way
    // it moves, and the wider levels about the pointer. They are built within a time budget
    // per frame; drawing only composites what exists.
    static constexpr int kRankView = 0;
    static constexpr int kRankArrival = 1;
    static constexpr int kRankRing = 2;
    static constexpr int kRankAhead = 3;
    struct CellWant {
        CellKey key;
        int rank = 0;
    };
    void planCells(int level, const FRect& view, const ViewSpec& spec, const FRect& seen);
    void wantCells(const FRect& rect, int level, int rank);
    void buildCells();
    // The step of its water's loop a cell shows `ahead` steps from now (0 for a still cell).
    [[nodiscard]] int cellFrame(int level, int cx, int cy, int ahead);
    // The slot to show for a cell: its own, or its last built step (-1: none).
    [[nodiscard]] int shownSlot(CellKey k);
    // Every cell of a level over `view` is built (the cache is not touched).
    [[nodiscard]] bool cellsReady(int level, const FRect& view);
    // Most of the native level over `view` is there: its ground cells and its objects.
    [[nodiscard]] bool nativeMostlyReady(const FRect& view);
    // Milliseconds of a frame that building cells of this rank may use.
    [[nodiscard]] double buildLimit(int rank) const;
    // What the cell cache may hold at this window size.
    [[nodiscard]] static std::size_t cellBudget(Vec2 screen);
    void buildGround(CellKey key, int slot);
    // Impostors: their blocks are gathered on the worker, then drawn as time allows.
    void requestImpostor(CellKey key, int slot, int rank);
    void drawBlock(CellKey key, int slot, int block, const Gathered& g);
    void progressImpostors();
    // The native level's objects: re-gathered on the worker before the view leaves them, and
    // gathered ahead for a destination the view is heading to.
    void updateRegion(const FRect& view);
    // Takes over a finished gather that covers `view`.
    void adoptRegion(const FRect& view);
    void gatherAhead(const FRect& view);
    [[nodiscard]] static TileRect regionAround(const TileRect& need, float k);
    void drawCells(int level, const FRect& view, const Xform& x);
    void drawOverview(const Xform& x);
    void drawBackdrops(const FRect& view, const Xform& x, bool night);
    void wantSets(const FRect& view, bool prefetch);
    void ensure(Target& t, int w, int h);
    [[nodiscard]] std::size_t targetBytes() const;
    void fullQuad(int w, int h, SDL_FColor c, SDL_BlendMode mode);
    // City life: this frame's actors gathered, resolved and (at the native level) merged into
    // the region's order; drawn one by one at their turns.
    void prepareActors(const FRect& view, Lod lod);
    void prepareActorsTimed(const FRect& view, Lod lod);
    void drawActor(std::uint32_t i, const Xform& x);
    // `s` above (or below) the line where the roof over `foot` has its underside at `z` px.
    bool putCut(const SpriteRef& s, Vec2 anchor, const Xform& x, const FRect& foot, float z,
                bool upper);
    // `s` with the rows [hide.from, hide.to) of world px left out (two quads at most).
    bool putRows(const SpriteRef& s, Vec2 anchor, const Xform& x, SDL_FColor c, bool mirror,
                 RowBand hide);
    void drawActorShadows(const Xform& x);
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
    std::unique_ptr<TopField> tops_; // what covers whom at the coarser levels
    Hole hole_;
    const Atlas& homeAtlas_;
    CellCache cells_;
    Batch batch_;
    ThemeMixer theme_;
    PlaceTracker places_;
    bool themed_ = false;
    int season_ = -1;
    int sea_ = -1;   // the terrain beyond the grid (the deep sea), -1: none
    FRect lastView_; // world px the last frame showed
    Vec2 velocity_;  // world px the view moved since the frame before
    bool jumped_ = true;
    std::uint64_t animStep_ = 0; // the step of the water's loop this frame
    int animPeriod_ = 1;         // steps in the water's loop
    // What glows, by map chunk (CSR), for the coarser levels: their impostors hold no glow, so
    // lit windows, lamps and fires are drawn live over them (the native level draws its own).
    struct GlowSource {
        const SpriteRef* sprite = nullptr;
        Vec2 anchor; // world px, raised by the level
    };
    std::vector<GlowSource> glow_;
    const WeatherField* weather_ = nullptr;
    Sprite blob_;
    std::optional<SpriteId> raindrop_;
    std::optional<SpriteId> snowflake_;
    void drawWeatherGround(const FRect& view, const Xform& x);
    void drawRain(const FRect& view, const Xform& x, double now);
    std::vector<std::uint32_t> glowStart_; // per chunk, then one past the end
    void buildGlow();
    void drawCoarseGlow(const FRect& view, const Xform& x, float strength);
    std::vector<FigureLook> figures_;     // resolved once, before the gatherer's worker starts
    std::vector<std::uint32_t> figureOf_; // figures_ entry -> index into the figures given
    int figuresMissing_ = 0;
    float animFps_ = 0;

    Target view_;    // the world at the level's resolution, graded, then composited
    Target shadow_;  // the shadow layer
    Target scratch_; // impostor blocks at full resolution
    Target scratchShadow_;
    Target half_; // impostor downsampling
    int viewW_ = 0;
    int viewH_ = 0;
    float res_ = 1; // target px per world px this frame

    // The native level's region: elements around the view in draw order, and the next one.
    std::unique_ptr<Prep> prep_;
    Gathered region_;
    Gathered next_;
    TileRect regionRect_;
    TileRect pendingRect_;
    bool regionPending_ = false;
    Gathered ahead_; // gathered for a destination, taken over once the view is there
    TileRect aheadRect_;
    bool aheadPending_ = false;
    bool aheadReady_ = false;
    Gathered block_;
    struct Building {
        CellKey key;
        int slot = 0;
        std::uint32_t done = 0; // blocks drawn
        int rank = 0;
    };
    std::vector<Building> building_;
    std::vector<CellWant> wants_;
    std::vector<std::pair<std::uint16_t, std::uint32_t>> shadows_; // page, place in the order
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

    const life::CityLife* life_ = nullptr;
    std::unique_ptr<ActorLooks> looks_;
    float lifeAlpha_ = 1;
    std::vector<life::DrawActor> actorBuf_;
    std::size_t actorCount_ = 0;
    struct ActorDraw {
        const SpriteRef* sprite = nullptr;
        Vec2 anchor; // world px: the feet
        bool mirror = false;
        SDL_FColor colour{1, 1, 1, 1};
        const SpriteRef* goods = nullptr;
        Vec2 goodsAt;
        float drawn = -1; // its place in the frame's sequence (-1: not drawn)
        RowBand hidden;   // world px rows covered by what stands in front (coarser levels)
        DepthBox box;
    };
    std::vector<ActorDraw> actorDraw_;
    std::vector<OrderItem> mergeActors_;
    std::vector<std::uint32_t> actorOf_; // merge entry -> actorDraw_/actorBuf_ index
    std::vector<std::uint32_t> coarse_;  // actors drawn over impostors, in draw order
    ActorMerge coarseMerge_;             // their order among themselves (no static order)
    mutable std::vector<std::pair<float, life::Handle>> actorHits_; // actorsAt's scratch
    // How far an actor's art reaches from its feet, px: twice the largest in today's sets (112
    // sideways, 152 up with goods, 51 down), and widened by anything larger that is drawn.
    Reach actorReach_{256, 256, 320, 128};
    struct Shower {
        Vec2 centre; // tiles
        float invR2 = 0;
        float intensity = 0;
    };
    std::vector<Shower> showers_; // drawRain's scratch
    ActorMerge merge_;
    bool mergeIndexed_ = false;
    Lod lastLod_ = Lod::Native; // the level the last frame was drawn at

    // Backdrop sprites by region (day, night), resolved at load; empty when the set has none.
    std::vector<std::array<std::vector<SpriteRef>, 2>> backdrops_;
    FrameStats stats_;
};

} // namespace lc::worldview
