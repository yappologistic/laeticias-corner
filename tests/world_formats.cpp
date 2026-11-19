// Loaders of every world file format: good fixtures parse into the expected structs, failing
// fixtures are refused with an error naming the file, the object and the problem.

#include "world/atlas_pages.hpp"
#include "world/content.hpp"
#include "world/geometry.hpp"
#include "world/graph_file.hpp"
#include "world/layer_file.hpp"
#include "world/region_file.hpp"
#include "world/set_catalog.hpp"
#include "world/world_file.hpp"
#include "world_support.hpp"

#include <doctest.h>

#include <array>
#include <string>
#include <vector>

using namespace lc;
using namespace lc::world;
using lc::wtest::fixture;

namespace {

// The tiny layer of docs/design/world-tech.md §2.4 byte for byte: a 2 x 1 layer at grid
// (10, 20), one grass tile at level 1 in "corner/meadow" with an oak (variant 2), one transparent.
constexpr std::array<std::uint8_t, 68> kExample{
    0x4C, 0x43, 0x57, 0x4C, 0x01, 0x00, 0x00, 0x00, 0x0A, 0x00, 0x14, 0x00, 0x02, 0x00,
    0x01, 0x00, 0x01, 0x00, 0x01, 0x00, 0x01, 0x00, 0x00, 0x00, 0x05, 0x67, 0x72, 0x61,
    0x73, 0x73, 0x0D, 0x63, 0x6F, 0x72, 0x6E, 0x65, 0x72, 0x2F, 0x6D, 0x65, 0x61, 0x64,
    0x6F, 0x77, 0x03, 0x6F, 0x61, 0x6B, 0x00, 0x00, 0xFE, 0x00, 0x01, 0x01, 0x00, 0x01,
    0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x02, 0x00};

std::vector<std::uint8_t> kExampleBytes() {
    return {kExample.begin(), kExample.end()};
}

std::string layerError(const std::vector<std::uint8_t>& bytes, int gw = 448, int gh = 1280) {
    const auto r = parseLayer(bytes, gw, gh, "test.lcw");
    return r ? std::string() : r.error();
}

template <typename R>
std::string errorOf(const R& r) {
    return r ? std::string() : r.error();
}

} // namespace

TEST_CASE("layer: the world-tech example parses exactly") {
    const auto lf = parseLayer(kExample, 448, 1280, "example.lcw");
    REQUIRE_MESSAGE(lf.has_value(), errorOf(lf));
    CHECK(lf->x0 == 10);
    CHECK(lf->y0 == 20);
    CHECK(lf->w == 2);
    CHECK(lf->h == 1);
    CHECK(lf->terrains == std::vector<std::string>{"grass"});
    CHECK(lf->districts == std::vector<std::string>{"corner/meadow"});
    CHECK(lf->itemIds == std::vector<std::string>{"oak"});
    CHECK(lf->terrain == std::vector<std::uint8_t>{0, kCellTransparent});
    CHECK(lf->level == std::vector<std::uint8_t>{1, 1});
    CHECK(lf->district == std::vector<std::uint8_t>{0, 0});
    REQUIRE(lf->items.size() == 1);
    CHECK(lf->items[0].id == 0);
    CHECK(lf->items[0].x == 0);
    CHECK(lf->items[0].variant == 2);
    CHECK(wtest::writeLayer(*lf) == kExampleBytes());
}

TEST_CASE("layer: level byte fields") {
    constexpr std::uint8_t b = 0x5B; // level 11, aux 1, impassable
    CHECK(levelOf(b) == 11);
    CHECK(auxOf(b) == 1);
    CHECK(impassableBit(b));
    CHECK_FALSE(impassableBit(0x3F));
}

TEST_CASE("layer: every truncation is refused without a crash") {
    for (std::size_t n = 0; n < kExample.size(); ++n) {
        const std::vector<std::uint8_t> cut(kExample.begin(),
                                            kExample.begin() + static_cast<std::ptrdiff_t>(n));
        CHECK_FALSE(layerError(cut).empty());
    }
}

TEST_CASE("layer: broken files are refused with a precise reason") {
    struct Case {
        const char* what;
        std::size_t at;
        std::uint8_t value;
        const char* expect;
    };
    const std::vector<Case> cases{
        {"magic", 0, 'X', "bad magic"},
        {"version", 4, 2, "version 2"},
        {"reserved", 6, 1, "reserved header"},
        {"rect", 8, 0xC0, "leaves the 448 x 1280 grid"}, // x0 = 448
        {"empty", 12, 0, "empty layer rect"},
        {"reserved count", 22, 1, "reserved table count"},
        {"terrain value", 48, 3, "plane T: value 3 at grid (10, 20)"},
        {"run past end", 49, 1, "passes the end"},
        {"level bit 7", 52, 0x81, "reserved bit 7 set at grid (10, 20)"},
        {"district value", 54, 4, "plane D: value 4 at grid (10, 20)"},
        {"item id", 60, 1, "id index 1"},
        {"item x", 62, 2, "outside the layer rect"},
        {"item flags", 67, 1, "reserved flags"},
    };
    for (const Case& c : cases) {
        CAPTURE(c.what);
        auto bytes = kExampleBytes();
        if (c.at == 8) bytes[9] = 0x01; // x0 = 0x1C0 = 448
        bytes[c.at] = c.value;
        const std::string err = layerError(bytes);
        CHECK(err.find("test.lcw") == 0);
        CHECK_MESSAGE(err.find(c.expect) != std::string::npos, err);
    }
    auto trailing = kExampleBytes();
    trailing.push_back(0);
    CHECK(layerError(trailing).find("trailing bytes") != std::string::npos);
    CHECK(layerError(kExampleBytes(), 11, 21).find("leaves the 11 x 21 grid") != std::string::npos);
}

TEST_CASE("layer: writer and reader round-trip a busy layer") {
    LayerFile lf = wtest::blankLayer(5, 7, 40, 30, {"a", "b", "c"}, {"r/x", "r/y"}, {"i0", "i1"});
    for (int y = 7; y < 37; ++y)
        for (int x = 5; x < 45; ++x) {
            const int k = (x * 7 + y * 13) % 11;
            if (k == 0) continue; // transparent
            wtest::setCell(lf, x, y, k == 1 ? kCellNoGround : static_cast<std::uint8_t>(k % 3),
                           static_cast<std::uint8_t>((k * 5) & 0x7F),
                           static_cast<std::uint8_t>(k % 2));
        }
    for (int i = 0; i < 300; ++i)
        wtest::addItem(lf, 5 + i % 40, 7 + i % 30, std::uint16_t(i % 2), 3);
    const auto bytes = wtest::writeLayer(lf);
    const auto back = parseLayer(bytes, 448, 1280, "busy.lcw");
    REQUIRE_MESSAGE(back.has_value(), errorOf(back));
    CHECK(back->terrain == lf.terrain);
    CHECK(back->level == lf.level);
    CHECK(back->district == lf.district);
    CHECK(back->items.size() == 300);
    CHECK(wtest::writeLayer(*back) == bytes);
}

TEST_CASE("world.json: the fixture parses") {
    const WorldFile wf = wtest::tstWorldFile();
    CHECK(wf.gridW == 64);
    CHECK(wf.gridH == 96);
    CHECK(wf.home.rect == TileRect{40, 60, 48, 68});
    CHECK(wf.home.level == 1);
    CHECK(wf.regions[std::size_t(wf.home.region)].id == "home");
    REQUIRE(wf.layers.size() == 2);
    CHECK(wf.layers[1].graph == "layers/town.graph.json");
    CHECK(wf.regions[1].kind == RegionKind::City);
    CHECK(wf.markers[0].region == 1);
    CHECK(wf.findRegion("wild") == 2);
    CHECK(wf.findRegion("nowhere") == -1);
}

TEST_CASE("world.json: failing fixtures") {
    const std::vector<std::pair<const char*, const char*>> cases{
        {"world_bad_version.json", "version 2 is not supported"},
        {"world_bad_chunk.json", "chunk 16 differs from the engine's 32"},
        {"world_bad_home.json", "home: the home rect leaves the grid"},
        {"world_bad_marker.json", "markers[0]: region 'nowhere' is not listed"},
        {"world_dup_layer.json", "layers[2]: empty or duplicated layer id 'base'"},
        {"world_bad_kind.json", "kind 'metropolis' is not home, city"},
    };
    for (const auto& [file, expect] : cases) {
        CAPTURE(file);
        const std::string err = errorOf(parseWorldFile(fixture(file), file));
        CHECK(err.find(file) == 0);
        CHECK_MESSAGE(err.find(expect) != std::string::npos, err);
    }
    CHECK(errorOf(parseWorldFile("{\"version\": 1,", "w.json")).find("not valid JSON") !=
          std::string::npos);
}

TEST_CASE("graph: the fixture parses") {
    const auto g = parseGraphFile(fixture("graph_ok.json"), "graph_ok.json", "town", 64, 96);
    REQUIRE_MESSAGE(g.has_value(), errorOf(g));
    REQUIRE(g->nodes.size() == 5);
    CHECK(g->nodes[0].kind == NodeKind::Portal);
    CHECK(g->nodes[2].kind == NodeKind::Dest);
    CHECK(g->nodes[1].kind == NodeKind::Plain);
    REQUIRE(g->edges.size() == 5);
    CHECK(g->edges[3].kind == EdgeKind::Stair);
    CHECK(g->edges[3].via.size() == 3);
    CHECK(g->edges[3].a == 3);
    CHECK(g->edges[3].b == 4);
    REQUIRE(g->lanes.size() == 1);
    CHECK(g->lanes[0].ports[0].slot == "tst.house:door");
    CHECK(g->lanes[0].ports[1].at == 2);
    CHECK(std::string(edgeKindName(EdgeKind::Towpath)) == "towpath");
    CHECK(std::string(nodeKindName(NodeKind::Plain)) == "plain");
}

TEST_CASE("graph: failing fixtures") {
    const std::vector<std::pair<const char*, const char*>> cases{
        {"graph_bad_node.json", "edges[5]: node 'nowhere' does not exist"},
        {"graph_bad_kind.json", "edges[0]: kind 'highway' is not one of street"},
        {"graph_bad_port.json", "ports[1]: at: 3 is outside 0..2"},
        {"graph_dup_node.json", "nodes[5] 'a': empty or duplicated node id"},
        {"graph_bad_at.json", "nodes[1] 'a': at x: 64 is outside 0..63"},
    };
    for (const auto& [file, expect] : cases) {
        CAPTURE(file);
        const std::string err = errorOf(parseGraphFile(fixture(file), file, "town", 64, 96));
        CHECK(err.find(file) == 0);
        CHECK_MESSAGE(err.find(expect) != std::string::npos, err);
    }
    CHECK(errorOf(parseGraphFile(fixture("graph_ok.json"), "g.json", "base", 64, 96))
              .find("layer 'town' differs from 'base'") != std::string::npos);
}

TEST_CASE("region files cut short or corrupted anywhere are refused or read, never a crash") {
    const std::string text = fixture("region_ok.json");
    for (std::size_t k = 0; k < text.size(); k += 1 + text.size() / 400) {
        CAPTURE(k);
        CHECK_NOTHROW((void)parseRegionFile(text.substr(0, k), "cut.json", "town", 64, 96));
        std::string flipped = text;
        flipped[k] = static_cast<char>(flipped[k] ^ 0x5A);
        CHECK_NOTHROW((void)parseRegionFile(flipped, "flipped.json", "town", 64, 96));
    }
}

TEST_CASE("region: the fixture parses, unknown sections stay raw") {
    const auto r = parseRegionFile(fixture("region_ok.json"), "region_ok.json", "town", 64, 96);
    REQUIRE_MESSAGE(r.has_value(), errorOf(r));
    CHECK(r->name == "Testtown");
    CHECK(r->native == "Τεστ");
    CHECK(r->theme.grading[3][0] == doctest::Approx(0.42));
    CHECK(r->theme.hazeStrength == doctest::Approx(0.15));
    REQUIRE(r->theme.beds.size() == 2);
    CHECK(r->theme.beds[0].to == doctest::Approx(18.5));
    CHECK(r->theme.beds[1].from == doctest::Approx(18.5));
    REQUIRE(r->theme.zones.size() == 1);
    CHECK(r->theme.zones[0].rect == TileRect{4, 4, 10, 10});
    CHECK(r->theme.musicNight == "music/tst/night.ogg");
    REQUIRE(r->districts.size() == 2);
    CHECK(r->districts[0].populations.size() == 1);
    CHECK(r->districts[1].populations.empty());
    REQUIRE(r->densities.size() == 1);
    CHECK(r->densities[0].second[8] == doctest::Approx(1.0));
    REQUIRE(r->card("hall") != nullptr);
    CHECK(r->card("hall")->epithet == "Where the town meets");
    CHECK(r->card("nothing") == nullptr);
    CHECK(r->strings[0].first == "first_visit");
    CHECK(r->journal == std::vector<std::string>{"landmark:*"});
    CHECK(r->life.contains("future_section"));
    CHECK(r->life.contains("lanes_tokens"));
    CHECK(r->life.at("events").size() == 1);
    CHECK_FALSE(r->life.contains("cards"));
}

TEST_CASE("region: failing fixtures") {
    const std::vector<std::pair<const char*, const char*>> cases{
        {"region_bad_hours.json", "beds[0]: hours: '6' is not hh:mm"},
        {"region_bad_density.json", "densities: daytime: expected 24 hourly values"},
        {"region_bad_id.json", "id 'other' differs from the region 'town'"},
        {"region_bad_zone.json", "zones[0]: rect: 64 is outside 0..63"},
        {"region_bad_card.json", "cards: hall: missing 'text'"},
    };
    for (const auto& [file, expect] : cases) {
        CAPTURE(file);
        const std::string err = errorOf(parseRegionFile(fixture(file), file, "town", 64, 96));
        CHECK(err.find(file) == 0);
        CHECK_MESSAGE(err.find(expect) != std::string::npos, err);
    }
}

TEST_CASE("set catalog: the fixture parses") {
    const auto c = parseSetCatalog(fixture("set_ok.json"), "set_ok.json", "tst");
    REQUIRE_MESSAGE(c.has_value(), errorOf(c));
    REQUIRE(c->terrain.size() == 4);
    CHECK(c->terrain[0].base);
    CHECK(c->terrain[1].under == "tst.grass");
    CHECK(c->terrain[1].paved);
    CHECK(c->terrain[2].water == false); // "channel" is not one of worldgen's water names
    CHECK(c->terrain[3].water);          // stated
    REQUIRE(c->items.size() == 7);
    const SetItem& hall = c->items[2];
    CHECK(hall.landmark);
    CHECK(hall.rotations == std::vector<int>{0});
    CHECK(hall.slots.size() == 2);
    CHECK(hall.slots[1].cap == 2);
    CHECK(hall.emitters[0].second == "tst.flame");
    CHECK(c->items[1].rise == 1);
    CHECK(c->items[1].axis == 'y');
    CHECK(c->items[1].rotations == std::vector<int>{0, 1, 2, 3});
    CHECK(c->items[4].count == 16); // connect layouts always have 16 masks
    CHECK(c->items[6].on == Surface::Water);
    CHECK(c->actors[1].sizeW == 3);
    CHECK(c->goods[0].stack == 3);
    CHECK(c->art.fx == std::vector<std::string>{"tst.flame"});
    CHECK(waterByName("world.sea"));
    CHECK(waterByName("parsa.water_channel"));
    CHECK(waterByName("water"));
    CHECK_FALSE(waterByName("world.sand"));
}

TEST_CASE("set catalog: failing fixtures") {
    const std::vector<std::pair<const char*, const char*>> cases{
        {"set_bad_id.json", "items[0] 'house': id 'house' is not 'tst.<name>'"},
        {"set_bad_axis.json", "'tst.stair': a stair or ramp (rise > 0) needs an axis"},
        {"set_bad_under.json", "'tst.paving': an overlay must name the base"},
        {"set_dup.json", "items[7]: id 'tst.house' is duplicated in this catalog"},
        {"set_bad_layout.json", "layout 'spin' is not rotate, variant or connect"},
    };
    for (const auto& [file, expect] : cases) {
        CAPTURE(file);
        const std::string err = errorOf(parseSetCatalog(fixture(file), file, "tst"));
        CHECK(err.find(file) == 0);
        CHECK_MESSAGE(err.find(expect) != std::string::npos, err);
    }
    CHECK(errorOf(parseSetCatalog(fixture("set_ok.json"), "s.json", "parsa"))
              .find("set 'tst' differs from 'parsa'") != std::string::npos);
}

TEST_CASE("geometry: the fixture parses") {
    const auto g = parseGeometry(fixture("geom_ok.json"), "geom_ok.json", "tst");
    REQUIRE_MESSAGE(g.has_value(), errorOf(g));
    CHECK(g->tileW == 64);
    REQUIRE(g->items.size() == 6);
    const GeomItem* hall = nullptr;
    const GeomItem* stair = nullptr;
    for (const GeomItem& i : g->items) {
        if (i.id == "tst.hall") hall = &i;
        if (i.id == "tst.grand_stair") stair = &i;
    }
    REQUIRE(hall != nullptr);
    const GeomVariant* v = hall->variant("r0");
    REQUIRE(v != nullptr);
    CHECK(hall->variant("r1") == nullptr);
    CHECK(v->pieces.size() == 4);
    CHECK(v->pieces[2].rect == TileRect{0, 3, 8, 4});
    CHECK(v->walk.size() == 10);
    REQUIRE(v->slots.size() == 2);
    const GeomSlot& throne = v->slots[0].id == "throne" ? v->slots[0] : v->slots[1];
    CHECK(throne.spots[0].off.y == -8);
    CHECK(throne.spots[0].z == 6);
    CHECK(throne.spots[0].face == 1);
    CHECK(v->emitters[0].second.y == -80);
    REQUIRE(stair != nullptr);
    const GeomVariant* sv = stair->variant("r0");
    CHECK(sv->walkZ.size() == 3);
    CHECK(sv->pieces[1].floor);
    CHECK_FALSE(sv->pieces[0].floor);
    REQUIRE(g->actors.size() == 1);
    CHECK(g->actors[0].carryAt.size() == 2);
}

TEST_CASE("geometry: failing fixtures") {
    const std::vector<std::pair<const char*, const char*>> cases{
        {"geom_bad_face.json", "door[0]: face 'north' is not +x, +y, -x or -y"},
        {"geom_bad_floor.json", "floor_pieces: 3 is outside 0..2"},
        {"geom_bad_walkz.json", "walk_z: 0,0: not a walk tile"},
        {"geom_bad_piece.json", "pieces[0]: w: 9 is outside 1..8"},
        {"geom_bad_key.json", "'x1' is not a variant key"},
    };
    for (const auto& [file, expect] : cases) {
        CAPTURE(file);
        const std::string err = errorOf(parseGeometry(fixture(file), file, "tst"));
        CHECK(err.find(file) == 0);
        CHECK_MESSAGE(err.find(expect) != std::string::npos, err);
    }
}

TEST_CASE("content: ids join across catalogs, geometry is checked against them") {
    const auto content = wtest::tstContent();
    Diagnostics diag;
    content->validate(diag);
    CHECK_MESSAGE(diag.errors.empty(), (diag.errors.empty() ? "" : diag.errors[0]));
    const int hall = content->findItem("tst.hall");
    REQUIRE(hall >= 0);
    CHECK(content->item(hall).landmark);
    CHECK(content->geometry(hall, 0, 0) != nullptr);
    CHECK(content->geometry(hall, 1, 0) == nullptr);
    const int oak = content->findItem("oak");
    REQUIRE(oak >= 0);
    CHECK(content->item(oak).homeType >= 0);
    CHECK(content->findItem("tst.nothing") == -1);
    const int wall = content->findItem("tst.wall");
    CHECK(content->item(wall).variantKey(0, 5) == "m5");
    CHECK(content->geometry(wall, 0, 5) != nullptr);
    CHECK(content->item(content->findItem("tst.house")).footprint(1).w == 2);
    CHECK(content->terrain("tst.pool").water);
    CHECK(content->terrain("grass").known);
    CHECK(content->terrain("grass").faces.size() == 2);
    CHECK(content->terrain("meadow").under == "grass");
    const TerrainInfo sea = content->terrain("world.sea");
    CHECK_FALSE(sea.known);
    CHECK(sea.water);
    CHECK(sea.set == "world");
    REQUIRE(content->actorGeometry("tst.walker") != nullptr);
}

TEST_CASE("content: an id defined twice is a load error naming both files") {
    auto a = parseSetCatalog(fixture("set_ok.json"), "first.json", "tst");
    auto b = parseSetCatalog(fixture("set_ok.json"), "second.json", "tst");
    REQUIRE(a.has_value());
    REQUIRE(b.has_value());
    std::vector<SetCatalog> sets;
    sets.push_back(std::move(*a));
    sets.push_back(std::move(*b));
    const auto c = Content::build(wtest::homeCatalog(), HomeContract{}, std::move(sets), {});
    REQUIRE_FALSE(c.has_value());
    CHECK(c.error() == "terrain 'tst.grass' is defined in both first.json and second.json");
}

TEST_CASE("content: geometry that disagrees with its catalog is reported") {
    auto set = parseSetCatalog(fixture("set_ok.json"), "set_ok.json", "tst");
    auto geom = parseGeometry(fixture("geom_cross.json"), "geom_cross.json", "tst");
    REQUIRE(set.has_value());
    REQUIRE_MESSAGE(geom.has_value(), errorOf(geom));
    std::vector<SetCatalog> sets;
    sets.push_back(std::move(*set));
    std::vector<GeometryFile> geoms;
    geoms.push_back(std::move(*geom));
    const auto c =
        Content::build(wtest::homeCatalog(), HomeContract{}, std::move(sets), std::move(geoms));
    REQUIRE(c.has_value());
    Diagnostics diag;
    c->validate(diag);
    const auto has = [&](const std::string& s) {
        return std::ranges::any_of(
            diag.errors, [&](const std::string& e) { return e.find(s) != std::string::npos; });
    };
    CHECK(has("geom_cross.json: tst.hall r0: pieces do not partition the 10 x 4 footprint"));
    CHECK(has("tst.hall r0: catalog slot 'guard' has no geometry"));
    CHECK(has("tst.hall r0: geometry slot 'bench' is not in the catalog"));
    CHECK(has("tst.house r0: walk tile (2, 0) is outside the footprint"));
    CHECK(has("tst.ghost: geometry for an item no catalog has"));
    CHECK(has("tst.stool r2: not a variant"));
    CHECK(has("item 'tst.grand_stair': a landmark without geometry") == false);
}

TEST_CASE("atlas pages: one key space across pages, duplicates refused") {
    AtlasPages pages;
    REQUIRE(loadSetPages(pages, wtest::fixturesDir() / "atlas_ok", "tst").has_value());
    CHECK(pages.pages().size() == 2);
    CHECK(pages.size() == 4);
    const PageSprite* s = pages.find("item/tst.hall/shadow/r0/f0");
    REQUIRE(s != nullptr);
    CHECK(s->page == 1);
    CHECK(s->oy == -20);
    CHECK(pages.find("item/tst.none/base/r0/f0") == nullptr);
    AtlasPages dup;
    const auto r = loadSetPages(dup, wtest::fixturesDir() / "atlas_dup", "tst");
    REQUIRE_FALSE(r.has_value());
    CHECK(r.error().find("item/tst.house/base/r0/f0: the key is also on") != std::string::npos);
    AtlasPages bad;
    CHECK(errorOf(
              bad.add(R"({"version": 1, "image": "other.png", "sprites": {}})", "p.json", "tst", 0))
              .find("image 'other.png' should be 'tst.0.png'") != std::string::npos);
    CHECK(errorOf(bad.add(R"({"version": 1, "image": "tst.0.png", "sprites": {"k": {"x": 4000,
        "y": 0, "w": 200, "h": 10, "ox": 0, "oy": 0}}})",
                          "p.json", "tst", 0))
              .find("k: the sprite leaves a 4096 x 4096 page") != std::string::npos);
}
