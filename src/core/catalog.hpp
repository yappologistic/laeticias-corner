#pragma once
// The content contract (assets/catalog.json) parsed and validated into plain structs.

#include "core/iso.hpp"

#include <cstdint>
#include <expected>
#include <filesystem>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

namespace lc {

enum class Surface : std::uint8_t { Land, Water, Any };
enum class Layout : std::uint8_t { Variant, Rotate, Connect };
enum class Habitat : std::uint8_t { Land, Water, Air };
enum class VisitTime : std::uint8_t { Any, Day, Night };

struct TerrainDef {
    std::string id;
    std::string name;
    bool base = false;
    bool water = false;
    int variants = 1;
    float fps = 0;
    std::string sound; // sfx path, empty when silent
};

struct CategoryDef {
    std::string id;
    std::string name;
};

struct Offset {
    int x = 0;
    int y = 0;
};

struct ItemDef {
    std::string id;
    std::string name;
    int category = 0;
    int footprintW = 1;
    int footprintH = 1;
    Layout layout = Layout::Variant;
    int count = 1; // variants for variant/rotate layouts; 16 masks for connect
    Surface on = Surface::Land;
    std::string sound; // sfx path
    bool walkable = false;
    bool glow = false;
    std::vector<Offset> smokeAt; // chimney top per variant, from the anchor; empty = no smoke
    float fps = 0;
};

struct Amount {
    int index = 0;
    int count = 0;
};

struct VisitorDef {
    std::string id;
    std::string name;
    Habitat habitat = Habitat::Land;
    VisitTime time = VisitTime::Any;
    std::vector<Amount> terrainNeeds; // every entry must be met
    std::vector<Amount> itemNeeds;    // every entry must be met
    std::vector<Amount> anyItems;     // weighted sum over these items must reach anyTotal
    int anyTotal = 0;
    int max = 1;
    bool glow = false; // emissive: drawn after night grading
    std::string voice; // sfx path, empty when silent
    std::string blurb;
};

struct AudioList {
    std::vector<std::string> music;
    std::vector<std::string> ambience;
    std::vector<std::string> sfx;
};

// Map limits: a continuous world of about 1024 x 512 tiles is planned; these leave headroom
// while keeping tile indices and pixel extents far from overflow.
inline constexpr int kMaxMapSide = 4096;
inline constexpr long long kMaxMapTiles = 1LL << 22;

struct Catalog {
    int tileW = 64;
    int tileH = 32;
    int mapW = 40;
    int mapH = 40;
    std::vector<TerrainDef> terrain;
    std::vector<CategoryDef> categories;
    std::vector<ItemDef> items;
    std::vector<VisitorDef> visitors;
    AudioList audio;
    int baseTerrain = 0;
    int waterTerrain = 0;

    [[nodiscard]] Iso iso() const {
        return {static_cast<float>(tileW) * 0.5f, static_cast<float>(tileH) * 0.5f};
    }
    [[nodiscard]] std::optional<int> findTerrain(std::string_view id) const;
    [[nodiscard]] std::optional<int> findItem(std::string_view id) const;
    [[nodiscard]] std::optional<int> findCategory(std::string_view id) const;
    [[nodiscard]] std::optional<int> findVisitor(std::string_view id) const;
};

// Parses and validates; the error names the offending entry.
[[nodiscard]] std::expected<Catalog, std::string> parseCatalog(std::string_view json);
[[nodiscard]] std::expected<Catalog, std::string> loadCatalog(const std::filesystem::path& file);

[[nodiscard]] std::expected<std::string, std::string> readTextFile(const std::filesystem::path& p);

} // namespace lc
