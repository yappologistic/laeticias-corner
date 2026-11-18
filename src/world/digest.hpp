#pragma once
// A digest of what a loaded world contains, computed the same way by tests/world_tools/
// world_digest.py from tools/worldgen's reader, so the two implementations can be compared byte
// for byte. Per 32 x 32 chunk (index cy * chunksX + cx), four FNV-1a 64 hashes over its tiles in
// row order (y, then x):
//   terrain:  each tile's terrain id then a 0 byte (just the 0 byte without ground)
//   level:    each tile's level byte
//   district: each tile's district name then a 0 byte (just the 0 byte without one)
//   items:    the items whose origin lies in the chunk, sorted by (y, x, id, variant): id, a 0
//             byte, x and y as little-endian u16, the variant byte
// plus item counts by id, the ids skipped as unknown, and per-layer graph sizes.

#include "world/loader.hpp"

#include <array>
#include <cstdint>
#include <expected>
#include <map>
#include <string>
#include <string_view>
#include <vector>

namespace lc::world {

struct GraphSize {
    int nodes = 0;
    int edges = 0;
    int lanes = 0;
    friend bool operator==(const GraphSize&, const GraphSize&) = default;
};

struct WorldDigest {
    int gridW = 0;
    int gridH = 0;
    int chunk = 0;
    std::vector<std::string> layers;
    std::vector<std::array<std::uint64_t, 4>> chunks; // terrain, level, district, items
    std::map<std::string, int> itemCounts;
    std::map<std::string, int> unresolved;
    std::map<std::string, GraphSize> graphs;
    int mergedNodes = 0; // nodes after merging portals
    int itemsTotal = 0;
};

[[nodiscard]] WorldDigest digestOf(const LoadedWorld& world);
[[nodiscard]] std::string toJson(const WorldDigest& d);
[[nodiscard]] std::expected<WorldDigest, std::string> parseDigest(std::string_view text,
                                                                  std::string_view file);
// Differences, one line each (empty when equal); chunk lines name the chunk and its grid rect.
[[nodiscard]] std::vector<std::string> compareDigests(const WorldDigest& expected,
                                                      const WorldDigest& actual);

} // namespace lc::world
