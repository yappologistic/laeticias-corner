#pragma once
// Fixtures for the world runtime tests: the real home catalog and world (loaded once), fixture
// files, a layer writer (the engine only reads layers; worldgen writes them) and a small synthetic
// world built from the "tst" fixture set.

#include "core/catalog.hpp"
#include "world/content.hpp"
#include "world/layer_file.hpp"
#include "world/loader.hpp"
#include "world/world_file.hpp"
#include "world/world_map.hpp"

#include <cstdint>
#include <filesystem>
#include <memory>
#include <string>
#include <vector>

namespace lc::wtest {

[[nodiscard]] std::filesystem::path assetsDir();
[[nodiscard]] std::filesystem::path fixturesDir();
[[nodiscard]] std::string fixture(const std::string& name);
[[nodiscard]] const Catalog& homeCatalog();
// The committed world, loaded once for the whole run.
[[nodiscard]] const world::LoadedWorld& realWorld();

// Serialises a layer exactly as tools/worldgen/worldgen/layer.py write_lcw does.
[[nodiscard]] std::vector<std::uint8_t> writeLayer(const world::LayerFile& lf);

// A layer over a rect, every cell transparent, with the given tables.
[[nodiscard]] world::LayerFile blankLayer(int x0, int y0, int w, int h,
                                          std::vector<std::string> terrains,
                                          std::vector<std::string> districts,
                                          std::vector<std::string> itemIds);
void setCell(world::LayerFile& lf, int x, int y, std::uint8_t terrain, std::uint8_t level,
             std::uint8_t district);
void addItem(world::LayerFile& lf, int x, int y, std::uint16_t id, std::uint8_t variant);

// Home catalog + the "tst" set and its geometry from the fixtures.
[[nodiscard]] std::unique_ptr<world::Content> tstContent();
// tests/fixtures/world/world_ok.json (grid 64 x 96, home 8 x 8 at (40, 60) level 1).
[[nodiscard]] world::WorldFile tstWorldFile();

} // namespace lc::wtest
