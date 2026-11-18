#include "world/content.hpp"

#include "world/json_util.hpp"

#include <algorithm>
#include <set>

namespace lc::world {

using namespace detail;

std::expected<HomeContract, std::string> parseHomeContract(std::string_view text,
                                                           std::string_view file, int tileH) {
    const std::string f(file);
    try {
        const json doc = parseDocument(text, f);
        HomeContract c;
        c.tileLevel = intOr(field(doc, "tile", f), "level", tileH / 2, f + ": tile", 1, 4096);
        if (has(doc, "sets")) c.sets = asStrings(doc.at("sets"), f + ": sets");
        c.world = stringOr(doc, "world", "", f);
        if (has(doc, "terrain")) {
            const json& ts = asArray(doc.at("terrain"), f + ": terrain");
            for (std::size_t i = 0; i < ts.size(); ++i) {
                const std::string tc = f + ": terrain[" + std::to_string(i) + "]";
                HomeTerrainExtra t;
                t.id = asString(field(ts[i], "id", tc), tc + ": id");
                t.under = stringOr(ts[i], "under", "", tc);
                if (has(ts[i], "faces")) t.faces = asStrings(ts[i].at("faces"), tc + ": faces");
                c.terrain.push_back(std::move(t));
            }
        }
        return c;
    } catch (const Invalid& e) {
        return std::unexpected(e.what());
    }
}

Footprint ItemInfo::footprint(int variant) const {
    if (layout == Layout::Rotate && variant % 2 == 1) return {footH, footW};
    return {footW, footH};
}

std::string ItemInfo::variantKey(int variant, int mask) const {
    return layout == Layout::Connect ? "m" + std::to_string(mask) : "r" + std::to_string(variant);
}

std::expected<Content, std::string> Content::build(const Catalog& home,
                                                   const HomeContract& contract,
                                                   std::vector<SetCatalog> sets,
                                                   std::vector<GeometryFile> geometry) {
    Content c;
    c.home_ = &home;
    c.tileLevel_ = contract.tileLevel;
    c.tileW_ = home.tileW;
    c.tileH_ = home.tileH;
    std::unordered_map<std::string, std::string> source; // id -> file, for clash messages
    const auto claim = [&](const std::string& id, const std::string& file) -> bool {
        const auto [it, fresh] = source.emplace(id, file);
        return fresh;
    };
    const std::string homeFile = "assets/catalog.json";
    const std::string& homeBase = home.terrain[static_cast<std::size_t>(home.baseTerrain)].id;
    for (const auto& t : home.terrain) {
        TerrainInfo info{.id = t.id,
                         .set = "home",
                         .known = true,
                         .base = t.base,
                         .water = t.water,
                         .paved = t.paved,
                         .under = {},
                         .faces = {}};
        const auto extra = std::ranges::find(contract.terrain, t.id, &HomeTerrainExtra::id);
        if (extra != contract.terrain.end()) {
            info.under = extra->under;
            info.faces = extra->faces;
        }
        if (!t.base && info.under.empty()) info.under = homeBase;
        claim(t.id, homeFile);
        c.terrainIndex_.emplace(t.id, static_cast<int>(c.terrain_.size()));
        c.terrain_.push_back(std::move(info));
    }
    for (std::size_t i = 0; i < home.items.size(); ++i) {
        const ItemDef& d = home.items[i];
        ItemInfo info;
        info.id = d.id;
        info.set = "home";
        info.homeType = static_cast<int>(i);
        info.footW = d.footprintW;
        info.footH = d.footprintH;
        info.layout = d.layout;
        info.count = d.count;
        info.on = d.on;
        info.walkable = d.walkable;
        info.crossing = d.crossing;
        info.rotations = {0};
        if (d.layout == Layout::Rotate) {
            info.rotations.clear();
            for (int k = 0; k < d.count; ++k) info.rotations.push_back(k);
        }
        claim(d.id, homeFile);
        c.itemIndex_.emplace(d.id, static_cast<int>(c.items_.size()));
        c.items_.push_back(std::move(info));
    }
    for (const SetCatalog& sc : sets) {
        for (const SetTerrain& t : sc.terrain) {
            if (!claim(t.id, sc.file))
                return std::unexpected("terrain '" + t.id + "' is defined in both " +
                                       source.at(t.id) + " and " + sc.file);
            c.terrainIndex_.emplace(t.id, static_cast<int>(c.terrain_.size()));
            c.terrain_.push_back({.id = t.id,
                                  .set = sc.set,
                                  .known = true,
                                  .base = t.base,
                                  .water = t.water,
                                  .paved = t.paved,
                                  .under = t.under,
                                  .faces = t.faces});
        }
        for (const SetItem& d : sc.items) {
            if (!claim(d.id, sc.file))
                return std::unexpected("item '" + d.id + "' is defined in both " + source.at(d.id) +
                                       " and " + sc.file);
            ItemInfo info;
            info.id = d.id;
            info.set = sc.set;
            info.footW = d.footW;
            info.footH = d.footH;
            info.layout = d.layout;
            info.count = d.count;
            info.on = d.on;
            info.walkable = d.walkable;
            info.landmark = d.landmark;
            info.occluder = d.occluder;
            info.rotations = d.rotations;
            info.rise = d.rise;
            info.axis = d.axis;
            info.height = d.height;
            info.card = d.card;
            info.slots = d.slots;
            c.itemIndex_.emplace(d.id, static_cast<int>(c.items_.size()));
            c.items_.push_back(std::move(info));
        }
        for (const SetActor& a : sc.actors)
            if (!claim(a.id, sc.file))
                return std::unexpected("actor '" + a.id + "' is defined in both " +
                                       source.at(a.id) + " and " + sc.file);
        for (const SetGoods& g : sc.goods)
            if (!claim(g.id, sc.file))
                return std::unexpected("goods '" + g.id + "' are defined in both " +
                                       source.at(g.id) + " and " + sc.file);
        c.edgeMaterials_.insert(c.edgeMaterials_.end(), sc.art.edges.begin(), sc.art.edges.end());
    }
    for (GeometryFile& g : geometry) {
        for (GeomItem& gi : g.items) {
            const auto it = c.itemIndex_.find(gi.id);
            if (it != c.itemIndex_.end() && c.items_[static_cast<std::size_t>(it->second)].geom < 0)
                c.items_[static_cast<std::size_t>(it->second)].geom =
                    static_cast<int>(c.geomItems_.size());
            c.geomFiles_.push_back(g.file);
            c.geomItems_.push_back(std::move(gi));
        }
        for (GeomActor& a : g.actors) c.geomActors_.push_back(std::move(a));
    }
    c.sets_ = std::move(sets);
    return c;
}

TerrainInfo Content::terrain(std::string_view id) const {
    const auto it = terrainIndex_.find(id);
    if (it != terrainIndex_.end()) return terrain_[static_cast<std::size_t>(it->second)];
    const auto dot = id.find('.');
    return {.id = std::string(id),
            .set = dot == std::string_view::npos ? "home" : std::string(id.substr(0, dot)),
            .known = false,
            .base = false,
            .water = waterByName(id),
            .paved = false,
            .under = {},
            .faces = {}};
}

int Content::findItem(std::string_view id) const {
    const auto it = itemIndex_.find(id);
    return it == itemIndex_.end() ? -1 : it->second;
}

const GeomActor* Content::actorGeometry(std::string_view id) const {
    const auto it = std::ranges::find(geomActors_, id, &GeomActor::id);
    return it == geomActors_.end() ? nullptr : &*it;
}

const GeomVariant* Content::geometry(int itemIndex, int variant, int mask) const {
    const ItemInfo& info = item(itemIndex);
    if (info.geom < 0) return nullptr;
    return geomItems_[static_cast<std::size_t>(info.geom)].variant(info.variantKey(variant, mask));
}

bool Content::setLoaded(std::string_view id) const {
    const auto dot = id.find('.');
    if (dot == std::string_view::npos) return true;
    const std::string_view set = id.substr(0, dot);
    return std::ranges::any_of(sets_, [&](const SetCatalog& s) { return s.set == set; });
}

void Content::validate(Diagnostics& diag) const {
    const auto out = [&](std::string line) { diag.error(std::move(line)); };
    for (const TerrainInfo& t : terrain_) {
        if (!t.base && !t.under.empty()) {
            const auto u = terrainIndex_.find(t.under);
            if (u == terrainIndex_.end()) {
                std::string line =
                    "terrain '" + t.id + "': its base '" + t.under + "' is in no catalog";
                if (setLoaded(t.under))
                    diag.error(std::move(line));
                else
                    diag.warn(std::move(line));
            } else if (!terrain_[static_cast<std::size_t>(u->second)].base) {
                out("terrain '" + t.id + "': its base '" + t.under + "' is an overlay");
            }
        }
        for (const auto& f : t.faces) {
            if (std::ranges::find(edgeMaterials_, f) != edgeMaterials_.end()) continue;
            std::string line =
                "terrain '" + t.id + "': face material '" + f + "' is in no set's art.edges";
            if (setLoaded(f))
                diag.error(std::move(line));
            else
                diag.warn(std::move(line));
        }
    }
    for (std::size_t g = 0; g < geomItems_.size(); ++g) {
        const GeomItem& gi = geomItems_[g];
        const std::string where = geomFiles_[g] + ": " + gi.id;
        const int idx = findItem(gi.id);
        if (idx < 0) {
            out(where + ": geometry for an item no catalog has");
            continue;
        }
        const ItemInfo& info = item(idx);
        if (info.geom != static_cast<int>(g)) {
            out(where + ": geometry given twice");
            continue;
        }
        std::set<std::string> catSlots;
        for (const auto& s : info.slots) catSlots.insert(s.id);
        std::set<std::string> catEmit;
        if (const auto* sc = [&]() -> const SetCatalog* {
                for (const auto& s : sets_)
                    if (s.set == info.set) return &s;
                return nullptr;
            }()) {
            const auto d = std::ranges::find(sc->items, info.id, &SetItem::id);
            if (d != sc->items.end())
                for (const auto& [name, fx] : d->emitters) catEmit.insert(name);
        }
        for (const GeomVariant& v : gi.variants) {
            const std::string vw = where + " " + v.key;
            const int n = std::stoi(v.key.substr(1));
            if (info.layout == Layout::Connect ? v.key[0] != 'm'
                                               : v.key[0] != 'r' || n >= info.count) {
                out(vw + ": not a variant of a " +
                    std::string(info.layout == Layout::Connect ? "connect" : "rotate or variant") +
                    " layout with " + std::to_string(info.count) + " variants");
                continue;
            }
            const Footprint fp = info.footprint(v.key[0] == 'r' ? n : 0);
            const TileRect foot{0, 0, fp.w, fp.h};
            if (!v.pieces.empty()) {
                std::vector<int> cover(static_cast<std::size_t>(fp.w * fp.h), 0);
                bool inside = true;
                for (const GeomPiece& p : v.pieces) {
                    if (!foot.contains(p.rect)) {
                        inside = false;
                        continue;
                    }
                    for (int y = p.rect.y0; y < p.rect.y1; ++y)
                        for (int x = p.rect.x0; x < p.rect.x1; ++x)
                            ++cover[static_cast<std::size_t>(y * fp.w + x)];
                }
                if (!inside || std::ranges::any_of(cover, [](int k) { return k != 1; }))
                    out(vw + ": pieces do not partition the " + std::to_string(fp.w) + " x " +
                        std::to_string(fp.h) + " footprint");
            } else if (fp.w > kMaxPieceSide || fp.h > kMaxPieceSide) {
                out(vw + ": a footprint over 8 x 8 must be split into pieces");
            }
            for (const TilePos t : v.walk)
                if (!foot.contains(t))
                    out(vw + ": walk tile (" + std::to_string(t.x) + ", " + std::to_string(t.y) +
                        ") is outside the footprint");
            std::set<std::string> have;
            for (const GeomSlot& s : v.slots) have.insert(s.id);
            for (const auto& s : catSlots)
                if (!have.contains(s)) out(vw + ": catalog slot '" + s + "' has no geometry");
            for (const auto& s : have)
                if (!catSlots.contains(s))
                    out(vw + ": geometry slot '" + s + "' is not in the catalog");
            std::set<std::string> em;
            for (const auto& [name, at] : v.emitters) em.insert(name);
            if (info.homeType < 0 && em != catEmit)
                out(vw + ": emitters differ from the catalog's");
        }
    }
    for (const ItemInfo& info : items_)
        if (info.landmark && info.geom < 0)
            out("item '" + info.id + "': a landmark without geometry");
}

std::size_t Content::memoryBytes() const {
    std::size_t n =
        terrain_.capacity() * sizeof(TerrainInfo) + items_.capacity() * sizeof(ItemInfo);
    for (const auto& g : geomItems_)
        for (const auto& v : g.variants)
            n += sizeof(GeomVariant) + v.pieces.capacity() * sizeof(GeomPiece) +
                 v.walk.capacity() * sizeof(TilePos) + v.walkZ.capacity() * sizeof(v.walkZ[0]) +
                 v.slots.capacity() * (sizeof(GeomSlot) + sizeof(GeomSpot));
    for (const auto& s : sets_)
        n += s.items.capacity() * sizeof(SetItem) + s.actors.capacity() * sizeof(SetActor) +
             s.terrain.capacity() * sizeof(SetTerrain);
    return n;
}

} // namespace lc::world
