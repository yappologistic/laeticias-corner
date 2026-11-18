#include "world_support.hpp"

#include "world/geometry.hpp"
#include "world/set_catalog.hpp"

#include <doctest.h>

#include <algorithm>
#include <stdexcept>

namespace lc::wtest {

using namespace lc::world;

std::filesystem::path assetsDir() {
    return LC_WORLD_ASSETS_DIR;
}

std::filesystem::path fixturesDir() {
    return LC_WORLD_FIXTURES_DIR;
}

std::string fixture(const std::string& name) {
    auto text = readTextFile(fixturesDir() / name);
    if (!text) throw std::runtime_error(text.error());
    return *text;
}

const Catalog& homeCatalog() {
    static const Catalog cat = [] {
        auto c = loadCatalog(assetsDir() / "catalog.json");
        if (!c) throw std::runtime_error(c.error());
        return std::move(*c);
    }();
    return cat;
}

const LoadedWorld& realWorld() {
    static const LoadedWorld w = [] {
        auto l = loadWorld(assetsDir(), homeCatalog());
        if (!l) throw std::runtime_error(l.error());
        return std::move(*l);
    }();
    return w;
}

namespace {

void u16(std::vector<std::uint8_t>& out, int v) {
    out.push_back(static_cast<std::uint8_t>(v & 0xFF));
    out.push_back(static_cast<std::uint8_t>((v >> 8) & 0xFF));
}

void rle(std::vector<std::uint8_t>& out, const std::vector<std::uint8_t>& plane) {
    std::size_t i = 0;
    while (i < plane.size()) {
        std::size_t j = i;
        while (j < plane.size() && plane[j] == plane[i] && j - i < 256) ++j;
        out.push_back(plane[i]);
        out.push_back(static_cast<std::uint8_t>(j - i - 1));
        i = j;
    }
}

} // namespace

std::vector<std::uint8_t> writeLayer(const LayerFile& lf) {
    std::vector<std::uint8_t> out{'L', 'C', 'W', 'L'};
    u16(out, 1);
    u16(out, 0);
    u16(out, lf.x0);
    u16(out, lf.y0);
    u16(out, lf.w);
    u16(out, lf.h);
    u16(out, static_cast<int>(lf.terrains.size()));
    u16(out, static_cast<int>(lf.districts.size()));
    u16(out, static_cast<int>(lf.itemIds.size()));
    u16(out, 0);
    for (const auto* table : {&lf.terrains, &lf.districts, &lf.itemIds})
        for (const std::string& s : *table) {
            out.push_back(static_cast<std::uint8_t>(s.size()));
            out.insert(out.end(), s.begin(), s.end());
        }
    rle(out, lf.terrain);
    rle(out, lf.level);
    rle(out, lf.district);
    const auto n = static_cast<std::uint32_t>(lf.items.size());
    for (int s = 0; s < 32; s += 8) out.push_back(static_cast<std::uint8_t>((n >> s) & 0xFF));
    for (const LayerItem& it : lf.items) {
        u16(out, it.id);
        u16(out, it.x);
        u16(out, it.y);
        out.push_back(it.variant);
        out.push_back(it.flags);
    }
    return out;
}

LayerFile blankLayer(int x0, int y0, int w, int h, std::vector<std::string> terrains,
                     std::vector<std::string> districts, std::vector<std::string> itemIds) {
    LayerFile lf;
    lf.x0 = x0;
    lf.y0 = y0;
    lf.w = w;
    lf.h = h;
    lf.terrains = std::move(terrains);
    lf.districts = std::move(districts);
    lf.itemIds = std::move(itemIds);
    const auto cells = static_cast<std::size_t>(w * h);
    lf.terrain.assign(cells, kCellTransparent);
    lf.level.assign(cells, 0);
    lf.district.assign(cells, 0);
    return lf;
}

void setCell(LayerFile& lf, int x, int y, std::uint8_t terrain, std::uint8_t level,
             std::uint8_t district) {
    const auto c = static_cast<std::size_t>((y - lf.y0) * lf.w + (x - lf.x0));
    lf.terrain[c] = terrain;
    lf.level[c] = level;
    lf.district[c] = district;
}

void addItem(LayerFile& lf, int x, int y, std::uint16_t id, std::uint8_t variant) {
    lf.items.push_back({id, static_cast<std::uint16_t>(x - lf.x0),
                        static_cast<std::uint16_t>(y - lf.y0), variant, 0});
}

std::unique_ptr<Content> tstContent() {
    const auto text = readTextFile(assetsDir() / "catalog.json");
    REQUIRE(text.has_value());
    auto contract = parseHomeContract(*text, "catalog.json", homeCatalog().tileH);
    REQUIRE(contract.has_value());
    auto set = parseSetCatalog(fixture("set_ok.json"), "set_ok.json", "tst");
    REQUIRE_MESSAGE(set.has_value(), (set ? "" : set.error()));
    auto geom = parseGeometry(fixture("geom_ok.json"), "geom_ok.json", "tst");
    REQUIRE_MESSAGE(geom.has_value(), (geom ? "" : geom.error()));
    std::vector<SetCatalog> sets;
    sets.push_back(std::move(*set));
    std::vector<GeometryFile> geoms;
    geoms.push_back(std::move(*geom));
    auto c = Content::build(homeCatalog(), *contract, std::move(sets), std::move(geoms));
    REQUIRE_MESSAGE(c.has_value(), (c ? "" : c.error()));
    return std::make_unique<Content>(std::move(*c));
}

WorldFile tstWorldFile() {
    auto wf = parseWorldFile(fixture("world_ok.json"), "world_ok.json");
    REQUIRE_MESSAGE(wf.has_value(), (wf ? "" : wf.error()));
    return *wf;
}

} // namespace lc::wtest
