#pragma once
// Everything the world can contain, from every catalog: the home catalog (assets/catalog.json, via
// core's parser) and the set catalogs, joined with the geometry files. Ids are unique across all
// of them (a clash is a load error naming both files).

#include "core/catalog.hpp"
#include "core/world.hpp"
#include "world/diagnostics.hpp"
#include "world/geometry.hpp"
#include "world/set_catalog.hpp"

#include <array>
#include <cstdint>
#include <expected>
#include <optional>
#include <string>
#include <string_view>
#include <unordered_map>
#include <vector>

namespace lc::world {

// Fields of assets/catalog.json the core parser leaves to the world (CLAUDE.md "Content
// contract": tile.level, sets, world, terrain faces).
struct HomeTerrainExtra {
    std::string id;
    std::string under; // the base an overlay is drawn over (default: the home base terrain)
    std::vector<std::string> faces;
};
struct HomeContract {
    int tileLevel = 16;            // px per elevation level
    std::vector<std::string> sets; // set catalogs to load
    std::string world;             // world.json, relative to the assets directory
    std::vector<HomeTerrainExtra> terrain;
};
[[nodiscard]] std::expected<HomeContract, std::string>
parseHomeContract(std::string_view text, std::string_view file, int tileH);

struct TerrainInfo {
    std::string id;
    std::string set;    // "home" or the set
    bool known = false; // defined in a catalog; unknown terrain draws the placeholder
    bool base = false;
    bool water = false;
    bool paved = false;
    float fps = 0; // animated overlays (water)
    std::string under;
    std::vector<std::string> faces;
    std::optional<std::array<std::uint8_t, 3>> colour; // set catalogs' flat look, when stated
};

struct ItemInfo {
    std::string id;
    std::string set;
    int homeType = -1; // index into the home Catalog's items, -1 for set items
    int footW = 1;     // at r0
    int footH = 1;
    Layout layout = Layout::Variant;
    int count = 1;
    Surface on = Surface::Land;
    bool walkable = false;
    bool crossing = false; // walkers may cross water on it
    bool landmark = false;
    bool occluder = false;
    std::vector<int> rotations;
    int rise = 0;
    char axis = 0; // at r0
    int height = 0;
    float fps = 0; // animated looks
    std::string card;
    std::string standIn;              // home item drawn in its place while the set has no art
    std::vector<SlotBehaviour> slots; // set items; home slots live in the home catalog
    int geom = -1;                    // index into Content::geometry(), -1 when none

    [[nodiscard]] Footprint footprint(int variant) const;
    // The geometry key of a placed variant: "r<k>", or "m<mask>" for connect layouts.
    [[nodiscard]] std::string variantKey(int variant, int mask) const;
};

class Content {
public:
    // `sets` and `geometry` in load order. Fails on ids defined twice, naming both sources.
    [[nodiscard]] static std::expected<Content, std::string>
    build(const Catalog& home, const HomeContract& contract, std::vector<SetCatalog> sets,
          std::vector<GeometryFile> geometry);

    [[nodiscard]] const Catalog& home() const { return *home_; }
    [[nodiscard]] int tileLevel() const { return tileLevel_; }
    // A terrain id's description; unknown ids get one with known = false.
    [[nodiscard]] TerrainInfo terrain(std::string_view id) const;
    [[nodiscard]] int findItem(std::string_view id) const; // -1 when no catalog has it
    [[nodiscard]] const ItemInfo& item(int i) const { return items_[static_cast<std::size_t>(i)]; }
    [[nodiscard]] const std::vector<ItemInfo>& items() const { return items_; }
    [[nodiscard]] const std::vector<SetCatalog>& sets() const { return sets_; }
    [[nodiscard]] const std::vector<GeomItem>& geometry() const { return geomItems_; }
    [[nodiscard]] const GeomActor* actorGeometry(std::string_view id) const;
    [[nodiscard]] const GeomVariant* geometry(int item, int variant, int mask) const;

    // Cross-file checks that do not stop a load: overlays over unknown bases, faces no art
    // block lists, geometry for unknown items or variants, pieces that do not partition their
    // footprint, walk tiles outside it, catalog slots and emitters without geometry and the
    // reverse. One line per problem, naming the file and the entry; a reference into a set that
    // has no catalog yet is a warning, everything else an error.
    void validate(Diagnostics& diag) const;
    [[nodiscard]] std::size_t memoryBytes() const;

private:
    struct Hash {
        using is_transparent = void;
        std::size_t operator()(std::string_view s) const {
            return std::hash<std::string_view>{}(s);
        }
    };
    const Catalog* home_ = nullptr;
    int tileLevel_ = 16;
    int tileW_ = 64;
    int tileH_ = 32;
    std::vector<TerrainInfo> terrain_;
    std::unordered_map<std::string, int, Hash, std::equal_to<>> terrainIndex_;
    std::vector<ItemInfo> items_;
    std::unordered_map<std::string, int, Hash, std::equal_to<>> itemIndex_;
    std::vector<SetCatalog> sets_;
    std::vector<GeomItem> geomItems_;
    std::vector<std::string> geomFiles_; // per geometry item, the file it came from
    std::vector<GeomActor> geomActors_;
    std::vector<std::string> edgeMaterials_; // every art block's edges

    [[nodiscard]] bool setLoaded(std::string_view id) const; // the id's set has a catalog
};

} // namespace lc::world
