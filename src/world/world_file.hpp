#pragma once
// `assets/world/world.json` (docs/design/world-tech.md §2.3): grid size, the home placement, the
// layers in composition order, the regions and the overview markers.

#include "core/iso.hpp"

#include <cstdint>
#include <expected>
#include <string>
#include <string_view>
#include <vector>

namespace lc::world {

enum class RegionKind : std::uint8_t { Home, City, Town, Stretch, Seam };

struct LayerRef {
    std::string id;
    std::string file;  // relative to the world directory
    std::string graph; // relative to the world directory
};

struct RegionRef {
    std::string id;
    std::string set; // "home" or a set id
    RegionKind kind = RegionKind::Stretch;
    std::string time; // the moment: rome, athens, parsa, timeless, none
    std::string life; // region file, relative to the assets directory
};

struct Marker {
    int region = 0; // index into WorldFile::regions
    TilePos at;
    std::string icon;
};

struct HomePlacement {
    TileRect rect; // grid tiles of the player's region
    int level = 0;
    int region = 0; // index into WorldFile::regions
};

struct WorldFile {
    int gridW = 0;
    int gridH = 0;
    int chunk = 32;
    HomePlacement home;
    std::vector<LayerRef> layers;
    std::vector<RegionRef> regions;
    std::vector<Marker> markers;

    [[nodiscard]] int findRegion(std::string_view id) const; // -1 when absent
};

[[nodiscard]] std::expected<WorldFile, std::string> parseWorldFile(std::string_view text,
                                                                   std::string_view file);

} // namespace lc::world
