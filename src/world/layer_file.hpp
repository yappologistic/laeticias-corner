#pragma once
// Reader for world layer files `.lcw` (docs/design/world-tech.md §2.4, as tools/worldgen writes
// them): a rect of cells, each transparent or fully set, with three RLE planes and an item list.

#include <cstdint>
#include <expected>
#include <span>
#include <string>
#include <string_view>
#include <vector>

namespace lc::world {

// Terrain plane values beside table indices.
inline constexpr std::uint8_t kCellTransparent = 0xFE;
inline constexpr std::uint8_t kCellNoGround = 0xFF;

// The level byte: bits 0-3 level, 4-5 aux (sea depth band, river flow, face material index),
// bit 6 impassable, bit 7 reserved (0).
inline constexpr std::uint8_t kLevelMask = 0x0F;
inline constexpr std::uint8_t kImpassable = 0x40;
inline constexpr std::uint8_t kLevelReserved = 0x80;
[[nodiscard]] constexpr int levelOf(std::uint8_t b) {
    return b & kLevelMask;
}
[[nodiscard]] constexpr int auxOf(std::uint8_t b) {
    return (b >> 4) & 3;
}
[[nodiscard]] constexpr bool impassableBit(std::uint8_t b) {
    return (b & kImpassable) != 0;
}

struct LayerItem {
    std::uint16_t id = 0; // index into LayerFile::itemIds
    std::uint16_t x = 0;  // origin tile, relative to the layer rect
    std::uint16_t y = 0;
    std::uint8_t variant = 0; // rotation k or look
    std::uint8_t flags = 0;   // reserved, 0
};

struct LayerFile {
    int x0 = 0; // grid rect of the layer
    int y0 = 0;
    int w = 0;
    int h = 0;
    std::vector<std::string> terrains;
    std::vector<std::string> districts; // "<region>/<name>"
    std::vector<std::string> itemIds;
    std::vector<std::uint8_t> terrain; // w * h, x fastest: table index, transparent or no ground
    std::vector<std::uint8_t> level;   // level bytes (ignored where transparent)
    std::vector<std::uint8_t> district;
    std::vector<LayerItem> items;
};

// Parses and checks a layer as the engine requires: magic, version, sizes, every run inside its
// plane, every value inside its table, the rect inside a `gridW` x `gridH` grid, no trailing
// bytes. The error names the file and, where there is one, the grid tile.
[[nodiscard]] std::expected<LayerFile, std::string>
parseLayer(std::span<const std::uint8_t> data, int gridW, int gridH, std::string_view file);

} // namespace lc::world
