#pragma once
// What the world draws for each terrain, face material and item, resolved from atlas keys once at
// load so drawing never builds strings, plus the generated page: flat ground and faces for
// terrain without art (the catalog's colour), and a labelled box sized to its footprint for every
// item without art, unless its catalog names a home stand-in. What fell back is counted for the
// missing-art report.

#include "render/atlas.hpp"
#include "ui/font.hpp"
#include "world/world_map.hpp"
#include "worldview/cells.hpp"
#include "worldview/page_atlas.hpp"

#include <array>
#include <optional>
#include <string>
#include <utility>
#include <vector>

namespace lc::worldview {

struct Frames {
    std::vector<SpriteRef> f;
    [[nodiscard]] bool empty() const { return f.empty(); }
    [[nodiscard]] const SpriteRef& at(float time, float fps) const {
        if (f.size() <= 1 || fps <= 0) return f.front();
        return f[static_cast<std::size_t>(time * fps) % f.size()];
    }
};

struct TerrainLook {
    std::vector<SpriteRef> base;    // the base drawn first: this terrain's variants or its under's
    std::array<Frames, 16> overlay; // overlays: by same-terrain neighbour mask (empty: no art)
    std::array<Frames, 16> foam;    // water: by land-neighbour mask, where the art has foam
    float fps = 0;
    SDL_FColor flat{1, 1, 1, 1};     // the whole tile when there is no art
    SDL_FColor flatBase{1, 1, 1, 1}; // under an overlay that has art, when the base has none
    bool water = false;
    std::array<int, 4> faces{-1, -1, -1, -1}; // material per aux value, -1: none
    [[nodiscard]] bool hasOverlay() const { return !overlay[0].empty(); }
    [[nodiscard]] bool animated() const {
        return fps > 0 && hasOverlay() && overlay[0].f.size() > 1;
    }
};

struct MaterialLook {
    std::string id;
    std::array<std::vector<SpriteRef>, 2> band; // south-east, south-west: v0.. (empty: flat)
    std::array<std::optional<SpriteRef>, 2> top;
    SDL_FColor flat{1, 1, 1, 1};
};

enum class Look : std::uint8_t { Art, StandIn, Placeholder };

struct VariantLook {
    Frames base;                   // the whole sprite (unsplit items, stand-ins, placeholders)
    std::vector<SpriteRef> pieces; // split landmarks: one per geometry piece
    std::optional<SpriteRef> shadow;
    std::optional<SpriteRef> glow;
    Look look = Look::Art;
};

struct MissingArt {
    std::string id;
    int count = 0; // placed items or tiles
    Look look = Look::Placeholder;
};

class WorldSprites {
public:
    // Resolves every look and builds the generated page into `pages`. `home` is the home atlas
    // (its shadow sprites are normalised here, as the scene does); `font` labels placeholders.
    WorldSprites(SDL_Renderer* renderer, Atlas& home, PageAtlas& pages, const world::WorldMap& map,
                 Font& font);

    [[nodiscard]] const TerrainLook& terrain(int t) const {
        return terrains_[static_cast<std::size_t>(t)];
    }
    [[nodiscard]] const TerrainLook& noGround() const { return noGround_; }
    [[nodiscard]] const MaterialLook& material(int m) const {
        return materials_[static_cast<std::size_t>(m)];
    }
    // The look of a placed item (its variant, or its neighbour mask for connect layouts).
    [[nodiscard]] const VariantLook& item(const world::Placed& it) const;
    [[nodiscard]] float itemFps(const world::Placed& it) const { return fps_[it.info]; }

    // Engine sprites on the generated page, white, tinted by vertex colour.
    [[nodiscard]] const SpriteRef& diamond() const { return diamond_; }
    [[nodiscard]] const SpriteRef& face(int side) const {
        return face_[static_cast<std::size_t>(side)];
    }
    [[nodiscard]] const SpriteRef& white() const { return white_; }
    [[nodiscard]] const MaterialLook& waterFace() const { return waterFace_; }

    // How far ground and item sprites reach from their tile's top vertex (raise included).
    [[nodiscard]] const Reach& groundReach() const { return groundReach_; }
    [[nodiscard]] const Reach& itemReach() const { return itemReach_; }
    [[nodiscard]] float homeShadowPeak() const { return homeShadowPeak_; }

    // Placed items drawn as stand-ins or placeholders, and terrain and faces without art.
    [[nodiscard]] const std::vector<MissingArt>& missingItems() const { return missingItems_; }
    [[nodiscard]] const std::vector<MissingArt>& missingTerrain() const { return missingTerrain_; }
    [[nodiscard]] const std::vector<std::string>& flatMaterials() const { return flatMaterials_; }
    [[nodiscard]] int placeholdersPlaced() const { return placeholdersPlaced_; }

private:
    struct Box {
        std::uint32_t info;
        int variant;
        int fw;
        int fh;
        int x = 0; // place on the generated page
        int y = 0;
        int w = 0;
        int h = 0;
        float ox = 0;
        float oy = 0;
        float height = 0;
        float labelW = 0;
    };

    void resolveTerrain(const world::WorldMap& map, PageAtlas& pages);
    void resolveItems(const world::WorldMap& map, Atlas& home, PageAtlas& pages);
    int internMaterial(const std::string& id, PageAtlas& pages);
    void buildPage(SDL_Renderer* renderer, const world::WorldMap& map, PageAtlas& pages,
                   Font& font);
    void count(const world::WorldMap& map);

    Iso iso_;
    int level_;
    std::vector<TerrainLook> terrains_;
    TerrainLook noGround_;
    std::vector<MaterialLook> materials_;
    MaterialLook waterFace_;
    std::vector<std::vector<VariantLook>> items_; // per Content item, per variant or mask
    std::vector<float> fps_;
    VariantLook unknown_; // a variant the catalog does not have
    std::vector<Box> boxes_;
    SpriteRef diamond_;
    std::array<SpriteRef, 2> face_{};
    SpriteRef white_;
    Reach groundReach_;
    Reach itemReach_;
    float homeShadowPeak_ = -1;
    std::vector<MissingArt> missingItems_;
    std::vector<MissingArt> missingTerrain_;
    std::vector<std::string> flatMaterials_;
    int placeholdersPlaced_ = 0;
};

} // namespace lc::worldview
