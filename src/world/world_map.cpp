#include "world/world_map.hpp"

#include "world/tuning.hpp"

#include <algorithm>
#include <climits>
#include <cmath>
#include <map>
#include <tuple>

namespace lc::world {

namespace {

std::string at(TilePos p) {
    return "grid (" + std::to_string(p.x) + ", " + std::to_string(p.y) + ")";
}

std::string setOf(const std::string& id) {
    const auto dot = id.find('.');
    return dot == std::string::npos ? "home" : id.substr(0, dot);
}

bool hasCatalog(const Content& c, const std::string& set) {
    return set == "home" ||
           std::ranges::any_of(c.sets(), [&](const SetCatalog& s) { return s.set == set; });
}

} // namespace

HomeDelta homeDeltaFrom(const lc::World& home, const Catalog& cat) {
    HomeDelta d;
    d.w = home.width();
    d.h = home.height();
    std::vector<int> paletteOf(cat.terrain.size(), -1);
    d.terrain.resize(static_cast<std::size_t>(d.w * d.h));
    d.wild.resize(d.terrain.size());
    for (int y = 0; y < d.h; ++y)
        for (int x = 0; x < d.w; ++x) {
            const std::size_t i = static_cast<std::size_t>(y * d.w + x);
            const int t = home.terrainAt({x, y});
            d.wild[i] = home.isWild({x, y}) ? 1 : 0;
            if (t == kNoGround) {
                d.terrain[i] = kNone;
                continue;
            }
            int& slot = paletteOf[static_cast<std::size_t>(t)];
            if (slot < 0) {
                slot = static_cast<int>(d.palette.size());
                d.palette.push_back(cat.terrain[static_cast<std::size_t>(t)].id);
            }
            d.terrain[i] = static_cast<std::uint8_t>(slot);
        }
    for (const Item& it : home.items())
        d.items.push_back({cat.items[it.type].id, it.pos.x, it.pos.y, it.variant});
    return d;
}

WorldMap::WorldMap(const WorldFile& wf, const Content& content, std::span<const LayerInput> layers,
                   Diagnostics& diag)
    : content_(&content), w_(wf.gridW), h_(wf.gridH), cw_((wf.gridW + kChunk - 1) >> kChunkShift),
      ch_((wf.gridH + kChunk - 1) >> kChunkShift), levelPx_(content.tileLevel()),
      hw_(static_cast<float>(content.home().tileW) * 0.5f),
      hh_(static_cast<float>(content.home().tileH) * 0.5f), home_(wf.home) {
    for (const RegionRef& r : wf.regions) {
        regionIds_.push_back(r.id);
        regionKinds_.push_back(r.kind);
    }
    chunks_.resize(static_cast<std::size_t>(cw_) * static_cast<std::size_t>(ch_));
    for (Chunk& c : chunks_) {
        c.terrain.fill(kNone);
        c.district.fill(kNone);
    }
    std::vector<std::uint8_t> dead;
    struct Skipped {
        int count = 0;
        TilePos first;
        std::string layer;
    };
    std::map<std::string, Skipped> unresolved;
    std::map<std::tuple<std::string, std::string, int>, Skipped> badVariant;
    std::map<std::pair<std::string, std::string>, Skipped> dropped; // (by layer, of layer)
    for (const LayerInput& in : layers) {
        const LayerFile& lf = *in.file;
        const std::string file = "layers/" + in.id + ".lcw";
        std::array<std::uint8_t, 256> tmap{};
        std::array<std::uint8_t, 256> dmap{};
        bool full = false;
        for (std::size_t i = 0; i < lf.terrains.size() && !full; ++i) {
            const int t = internTerrain(lf.terrains[i]);
            full = t < 0;
            tmap[i] = static_cast<std::uint8_t>(t);
        }
        for (std::size_t i = 0; i < lf.districts.size() && !full; ++i) {
            const int d = internDistrict(lf.districts[i]);
            full = d < 0;
            dmap[i] = static_cast<std::uint8_t>(d);
        }
        if (full) {
            diag.error(file + ": the world would hold more than 255 terrain ids or districts; "
                              "layer skipped");
            continue;
        }
        if (layers_.size() >= kHomeLayer) {
            diag.error(file + ": more than 254 layers; layer skipped");
            continue;
        }
        const auto li = static_cast<std::uint8_t>(layers_.size());
        layers_.push_back(in.id);
        const TileRect lr{lf.x0, lf.y0, lf.x0 + lf.w, lf.y0 + lf.h};
        const auto setCell = [&](int x, int y) {
            return lf.terrain[static_cast<std::size_t>((y - lf.y0) * lf.w + (x - lf.x0))] !=
                   kCellTransparent;
        };
        for (std::size_t i = 0; i < items_.size(); ++i) {
            if (dead[i]) continue;
            const TileRect ov = items_[i].rect().clipped(lr);
            bool hit = false;
            for (int y = ov.y0; y < ov.y1 && !hit; ++y)
                for (int x = ov.x0; x < ov.x1 && !hit; ++x) hit = setCell(x, y);
            if (!hit) continue;
            dead[i] = 1;
            Skipped& s = dropped[{in.id, layers_[items_[i].layer]}];
            if (s.count++ == 0) s.first = {items_[i].x, items_[i].y};
        }
        for (int y = 0; y < lf.h; ++y)
            for (int x = 0; x < lf.w; ++x) {
                const auto c = static_cast<std::size_t>(y * lf.w + x);
                const std::uint8_t v = lf.terrain[c];
                if (v == kCellTransparent) continue;
                const TilePos p{lf.x0 + x, lf.y0 + y};
                Chunk& ch = chunk(p);
                const std::size_t l = local(p);
                ch.terrain[l] = v == kCellNoGround ? kNone : tmap[v];
                ch.level[l] = lf.level[c];
                ch.district[l] = v == kCellNoGround ? kNone : dmap[lf.district[c]];
            }
        std::vector<int> resolved(lf.itemIds.size());
        for (std::size_t i = 0; i < lf.itemIds.size(); ++i)
            resolved[i] = content.findItem(lf.itemIds[i]);
        for (const LayerItem& li2 : lf.items) {
            const TilePos origin{lf.x0 + li2.x, lf.y0 + li2.y};
            const std::string& id = lf.itemIds[li2.id];
            const int idx = resolved[li2.id];
            if (idx < 0) {
                Skipped& s = unresolved[id];
                if (s.count++ == 0) {
                    s.first = origin;
                    s.layer = file;
                }
                continue;
            }
            const ItemInfo& info = content.item(idx);
            if (info.layout != Layout::Connect && li2.variant >= info.count) {
                Skipped& s = badVariant[{file, id, li2.variant}];
                if (s.count++ == 0) s.first = origin;
            }
            const Footprint fp = info.footprint(li2.variant);
            Placed p;
            p.info = static_cast<std::uint32_t>(idx);
            p.x = static_cast<std::int16_t>(origin.x);
            p.y = static_cast<std::int16_t>(origin.y);
            p.w = static_cast<std::uint8_t>(fp.w);
            p.h = static_cast<std::uint8_t>(fp.h);
            p.variant = li2.variant;
            p.layer = li;
            items_.push_back(p);
            dead.push_back(0);
        }
    }
    for (const auto& [id, s] : unresolved) {
        unresolved_.emplace_back(id, s.count);
        const std::string set = setOf(id);
        const std::string line =
            s.layer + ": item id '" + id + "' is in no catalog" +
            (hasCatalog(content, set) ? "" : " (set '" + set + "' has no catalog yet)") + ": " +
            std::to_string(s.count) + " placed, skipped; first at " + at(s.first);
        if (hasCatalog(content, set))
            diag.error(line);
        else
            diag.warn(line);
    }
    for (const auto& [key, s] : badVariant) {
        const auto& [file, id, v] = key;
        diag.error(file + ": " + id + " placed with variant " + std::to_string(v) + ", but its " +
                   "catalog has " + std::to_string(content.item(content.findItem(id)).count) +
                   " (" + std::to_string(s.count) + " placed, first at " + at(s.first) + ")");
    }
    for (const auto& [key, s] : dropped)
        diag.warn("layers/" + key.first + ".lcw drops " + std::to_string(s.count) + " item(s) of " +
                  key.second + " under its cells (first at " + at(s.first) + ")");
    std::size_t keep = 0;
    for (std::size_t i = 0; i < items_.size(); ++i)
        if (!dead[i]) items_[keep++] = items_[i];
    items_.resize(keep);
    for (Placed& it : items_) {
        if (inBounds({it.x, it.y})) it.level = static_cast<std::uint8_t>(level({it.x, it.y}));
        if (!bounds().contains(it.rect()))
            diag.error(content.item(int(it.info)).id + " at " + at({it.x, it.y}) +
                       ": its footprint leaves the grid");
        stairHead(it, diag);
    }
    homeBegin_ = static_cast<std::uint32_t>(items_.size());
    rebuildAll(diag);
}

int WorldMap::internTerrain(const std::string& id) {
    for (std::size_t i = 0; i < terrains_.size(); ++i)
        if (terrains_[i].id == id) return static_cast<int>(i);
    if (terrains_.size() >= kNone) return -1;
    terrains_.push_back(content_->terrain(id));
    return static_cast<int>(terrains_.size()) - 1;
}

int WorldMap::internDistrict(const std::string& name) {
    for (std::size_t i = 0; i < districts_.size(); ++i)
        if (districts_[i].name == name) return static_cast<int>(i);
    if (districts_.size() >= kNone) return -1;
    const auto slash = name.find('/');
    const auto r = std::ranges::find(regionIds_, name.substr(0, slash));
    districts_.push_back({name, slash == std::string::npos || r == regionIds_.end()
                                    ? -1
                                    : static_cast<int>(r - regionIds_.begin())});
    return static_cast<int>(districts_.size()) - 1;
}

int WorldMap::findDistrict(std::string_view name) const {
    const auto it = std::ranges::find(districts_, name, &District::name);
    return it == districts_.end() ? -1 : static_cast<int>(it - districts_.begin());
}

int WorldMap::findSlotKind(std::string_view kind) const {
    const auto it = std::ranges::find(slotKinds_, kind);
    return it == slotKinds_.end() ? -1 : static_cast<int>(it - slotKinds_.begin());
}

bool WorldMap::walkTileOf(const Placed& it, TilePos p) const {
    const GeomVariant* g = geometry(it);
    if (g == nullptr) return false;
    const TilePos rel{p.x - it.x, p.y - it.y};
    return std::ranges::find(g->walk, rel) != g->walk.end();
}

void WorldMap::stairHead(Placed& it, Diagnostics& diag) const {
    const ItemInfo& inf = info(it);
    if (inf.rise == 0) return;
    // Per side of the footprint: tiles beyond it at the head's level minus tiles at the foot's.
    const int foot = it.level;
    const int up = foot + inf.rise;
    const auto score = [&](int d) {
        const TileRect r = it.rect();
        const bool alongX = d % 2 == 0;
        const int edge = d == 0 ? r.x1 : d == 2 ? r.x0 - 1 : d == 1 ? r.y1 : r.y0 - 1;
        int s = 0;
        for (int k = alongX ? r.y0 : r.x0; k < (alongX ? r.y1 : r.x1); ++k) {
            const TilePos q = alongX ? TilePos{edge, k} : TilePos{k, edge};
            if (!inBounds(q) || terrainAt(q) == kNone) continue;
            s += level(q) == up ? 1 : level(q) == foot ? -1 : 0;
        }
        return s;
    };
    const std::string where = inf.id + " at " + at({it.x, it.y});
    if (inf.layout == Layout::Rotate && !inf.landmark) {
        // Kit faces +y at r0 and turns clockwise; its foot is on the side it faces (worldgen's
        // stair(face=...)), so the head is the opposite side. The catalog axis is not used.
        constexpr std::array<std::int8_t, 4> kHead{3, 0, 1, 2};
        it.head = kHead[static_cast<std::size_t>(it.variant % 4)];
        if (score(it.head) <= 0)
            diag.error(where + ": the tiles beyond its head are not " + std::to_string(inf.rise) +
                       " level(s) above its foot");
        return;
    }
    char axis = inf.axis;
    if (inf.layout == Layout::Rotate && it.variant % 2 == 1) axis = axis == 'x' ? 'y' : 'x';
    const int a = axis == 'x' ? 0 : 1;
    const int fwd = score(a);
    const int back = score(a + 2);
    if (fwd != back && std::max(fwd, back) > 0) {
        it.head = static_cast<std::int8_t>(fwd > back ? a : a + 2);
        return;
    }
    diag.error(where + ": neither end along its axis " + std::string(1, axis) + " stands " +
               std::to_string(inf.rise) + " level(s) above its foot; walkers cannot climb it");
}

void WorldMap::rebuildAll(Diagnostics& diag) {
    index(bounds(), 0, diag);
    slots_.clear();
    buildSlots(0, homeBegin_, diag);
    buildSlotIndex();
    homeSlotBegin_ = static_cast<std::uint32_t>(slots_.size());
    buildSlots(homeBegin_, static_cast<std::uint32_t>(items_.size()), diag);
}

void WorldMap::index(TileRect area, std::uint32_t from, Diagnostics& diag) {
    area = area.clipped(bounds());
    forEachChunkIn(area, [&](int cx, int cy) {
        Chunk& c = chunks_[chunkIndex(cx, cy)];
        std::erase_if(c.items, [&](std::uint32_t i) { return i >= from; });
        std::erase_if(c.big, [&](std::uint32_t i) { return i >= from; });
    });
    for (std::uint32_t i = from; i < items_.size(); ++i) {
        const Placed& it = items_[i];
        if (underHome(i)) continue;
        if (isBig(it)) {
            forEachChunkIn(it.rect(),
                           [&](int cx, int cy) { chunks_[chunkIndex(cx, cy)].big.push_back(i); });
        } else if (inBounds({it.x, it.y})) {
            chunk({it.x, it.y}).items.push_back(i);
        }
    }
    for (int y = area.y0; y < area.y1; ++y)
        for (int x = area.x0; x < area.x1; ++x) chunk({x, y}).occupancy[local({x, y})] = 0;
    std::vector<std::uint32_t> over;
    forEachItemIn(area, [&](std::uint32_t i, const Placed&) { over.push_back(i); });
    std::ranges::sort(over);
    for (const std::uint32_t i : over) {
        const Placed& it = items_[i];
        const TileRect r = it.rect().clipped(area);
        for (int y = r.y0; y < r.y1; ++y)
            for (int x = r.x0; x < r.x1; ++x) {
                std::uint32_t& o = chunk({x, y}).occupancy[local({x, y})];
                if (o != 0) {
                    const Placed& prev = items_[o - 1];
                    if (walkTileOf(prev, {x, y})) {
                        o = i + 1; // furniture on a landmark's walk tile takes the tile
                    } else if (!walkTileOf(it, {x, y})) {
                        diag.error(info(it).id + " at " + at({it.x, it.y}) + " overlaps " +
                                   info(prev).id + " at " + at({prev.x, prev.y}) + " on " +
                                   at({x, y}));
                    }
                    continue;
                }
                o = i + 1;
            }
    }
    const TileRect around{area.x0 - 1, area.y0 - 1, area.x1 + 1, area.y1 + 1};
    forEachItemIn(around, [&](std::uint32_t i, const Placed& it) {
        if (info(it).layout != Layout::Connect) return;
        std::uint8_t mask = 0;
        constexpr std::array<std::pair<TilePos, std::uint8_t>, 4> kBits{
            {{{0, -1}, kMaskN}, {{1, 0}, kMaskE}, {{0, 1}, kMaskS}, {{-1, 0}, kMaskW}}};
        for (const auto& [d, bit] : kBits) {
            const TilePos q{it.x + d.x, it.y + d.y};
            if (!inBounds(q)) continue;
            const int o = itemAt(q);
            if (o >= 0 && items_[std::size_t(o)].info == it.info) mask |= bit;
        }
        items_[i].mask = mask;
    });
    const TileRect walkArea = around.clipped(bounds());
    for (int y = walkArea.y0; y < walkArea.y1; ++y)
        for (int x = walkArea.x0; x < walkArea.x1; ++x) {
            const TilePos p{x, y};
            Chunk& c = chunk(p);
            const std::size_t l = local(p);
            std::uint8_t bits = 0;
            const std::uint8_t t = c.terrain[l];
            if (t != kNone) {
                const bool water = terrains_[t].water;
                const int o = static_cast<int>(c.occupancy[l]) - 1;
                if (o < 0) {
                    if (!water && !impassableBit(c.level[l])) bits = kWalk;
                } else {
                    const Placed& it = items_[std::size_t(o)];
                    const ItemInfo& inf = info(it);
                    const GeomVariant* g = geometry(it);
                    const TilePos rel{x - it.x, y - it.y};
                    const bool walkTile = g && std::ranges::find(g->walk, rel) != g->walk.end();
                    const bool walkZ = g && std::ranges::any_of(g->walkZ, [&](const auto& e) {
                                           return e.first == rel;
                                       });
                    if (inf.rise > 0) {
                        if (!g || g->walk.empty() || walkTile) bits = kWalk | kFloor;
                    } else if (inf.walkable) {
                        // A deck stands at its floor (`walk_z`), not at the water under it.
                        bits = static_cast<std::uint8_t>(kWalk | (water ? kDeck : 0) |
                                                         (walkZ ? kFloor : 0));
                    } else if (walkTile) {
                        bits = static_cast<std::uint8_t>(kWalk | (walkZ ? kFloor : 0));
                    }
                }
            }
            if (!homeWild_.empty() && home_.rect.contains(p) &&
                homeWild_[static_cast<std::size_t>(
                    (y - home_.rect.y0) * (home_.rect.x1 - home_.rect.x0) + (x - home_.rect.x0))])
                bits = 0;
            c.walk[l] = bits;
        }
}

void WorldMap::buildSlots(std::uint32_t begin, std::uint32_t end, Diagnostics& diag) {
    const auto intern = [](std::vector<std::string>& names, const std::string& s) {
        const auto it = std::ranges::find(names, s);
        if (it != names.end()) return static_cast<std::uint16_t>(it - names.begin());
        names.push_back(s);
        return static_cast<std::uint16_t>(names.size() - 1);
    };
    int outside = 0;
    const auto add = [&](std::uint32_t item, std::uint16_t name, std::uint16_t kind, Vec2 pos,
                         int z, std::uint8_t face, int cap) {
        const TilePos tile{static_cast<int>(std::floor(pos.x)),
                           static_cast<int>(std::floor(pos.y))};
        if (!inBounds(tile)) {
            ++outside;
            return;
        }
        slots_.push_back({item, name, kind, pos, tile, static_cast<std::int16_t>(z), face,
                          static_cast<std::uint8_t>(std::clamp(cap, 1, 255))});
    };
    const Catalog& home = content_->home();
    for (std::uint32_t i = begin; i < end; ++i) {
        const Placed& it = items_[i];
        const ItemInfo& inf = info(it);
        if (inf.homeType >= 0) {
            const ItemDef& def = home.items[static_cast<std::size_t>(inf.homeType)];
            for (const SlotDef& s : def.slots) {
                const auto v = static_cast<std::size_t>(it.variant);
                if (s.where == SlotWhere::Beside || v >= s.spots.size()) continue;
                const std::uint16_t name = intern(slotNames_, home.slotNames[std::size_t(s.name)]);
                const std::uint16_t kind = intern(slotKinds_, home.slotKinds[std::size_t(s.kind)]);
                const float lift = v < s.lift.size() ? s.lift[v] : 0.0f;
                const std::uint8_t face = v < s.face.size() ? s.face[v] : kFaceFree;
                for (const Vec2 spot : s.spots[v])
                    add(i, name, kind, {float(it.x) + spot.x, float(it.y) + spot.y},
                        static_cast<int>(lift), face, s.cap);
            }
            continue;
        }
        const GeomVariant* g = geometry(it);
        if (g == nullptr) continue;
        for (const GeomSlot& gs : g->slots) {
            const auto b = std::ranges::find(inf.slots, gs.id, &SlotBehaviour::id);
            const std::uint16_t name = intern(slotNames_, gs.id);
            const std::uint16_t kind = intern(slotKinds_, b != inf.slots.end() ? b->kind : "");
            const int cap = b != inf.slots.end() ? b->cap : 1;
            for (const GeomSpot& s : gs.spots) {
                const float u = static_cast<float>(s.off.x) / hw_;
                const float v = static_cast<float>(s.off.y) / hh_;
                const Vec2 pos{float(it.x + s.t.x) + 0.5f + (u + v) * 0.5f,
                               float(it.y + s.t.y) + 0.5f + (v - u) * 0.5f};
                add(i, name, kind, pos, s.z, s.face, cap);
            }
        }
    }
    if (outside > 0)
        diag.warn(std::to_string(outside) + " slot spot(s) lie outside the grid and were left out");
}

void WorldMap::buildSlotIndex() {
    const auto chunkOf = [&](const WorldSlot& s) {
        return chunkIndex(s.tile.x >> kChunkShift, s.tile.y >> kChunkShift);
    };
    std::ranges::stable_sort(slots_, {}, chunkOf);
    slotChunkStart_.assign(chunks_.size() + 1, 0);
    for (const WorldSlot& s : slots_) ++slotChunkStart_[chunkOf(s) + 1];
    for (std::size_t c = 0; c < chunks_.size(); ++c) slotChunkStart_[c + 1] += slotChunkStart_[c];
    slotIndexKinds_ = slotKinds_.size();
    const std::size_t keys = districts_.size() * slotIndexKinds_;
    slotDistrictStart_.assign(keys + 1, 0);
    slotByDistrict_.clear();
    const auto keyOf = [&](const WorldSlot& s) -> std::size_t {
        const int d = districtAt(s.tile);
        return d == kNone ? keys : static_cast<std::size_t>(d) * slotIndexKinds_ + s.kind;
    };
    for (const WorldSlot& s : slots_)
        if (const std::size_t k = keyOf(s); k < keys) ++slotDistrictStart_[k + 1];
    for (std::size_t k = 0; k < keys; ++k) slotDistrictStart_[k + 1] += slotDistrictStart_[k];
    slotByDistrict_.resize(slotDistrictStart_[keys]);
    std::vector<std::uint32_t> fill(slotDistrictStart_.begin(), slotDistrictStart_.end() - 1);
    for (std::uint32_t i = 0; i < slots_.size(); ++i)
        if (const std::size_t k = keyOf(slots_[i]); k < keys) slotByDistrict_[fill[k]++] = i;
}

int WorldMap::floorZ(TilePos p) const {
    const Chunk& c = chunk(p);
    const std::size_t l = local(p);
    if (!(c.walk[l] & kFloor)) return levelOf(c.level[l]) * levelPx_;
    const Placed& it = items_[c.occupancy[l] - 1];
    const ItemInfo& inf = info(it);
    const TilePos rel{p.x - it.x, p.y - it.y};
    if (const GeomVariant* g = geometry(it))
        for (const auto& [t, z] : g->walkZ)
            if (t == rel) return it.level * levelPx_ + z;
    if (inf.rise > 0 && it.head >= 0) {
        const int n = it.head % 2 == 0 ? it.w : it.h;
        const int i = it.head == 0   ? rel.x
                      : it.head == 2 ? it.w - 1 - rel.x
                      : it.head == 1 ? rel.y
                                     : it.h - 1 - rel.y;
        return it.level * levelPx_ + inf.rise * levelPx_ * (2 * i + 1) / (2 * n);
    }
    return it.level * levelPx_;
}

int WorldMap::edgeZ(TilePos p, int dir) const {
    const Chunk& c = chunk(p);
    const std::size_t l = local(p);
    if (!(c.walk[l] & kFloor)) return levelOf(c.level[l]) * levelPx_;
    const Placed& it = items_[c.occupancy[l] - 1];
    const ItemInfo& inf = info(it);
    const TilePos rel{p.x - it.x, p.y - it.y};
    // A stair meets its foot and head at their levels: `walk_z` is a tread's middle, and a first
    // tread drawn 10-14 px up must still be stepped onto from the ground.
    const bool stair = inf.rise > 0 && it.head >= 0;
    if (stair && dir == it.head) return (it.level + inf.rise) * levelPx_;
    if (stair && dir == (it.head + 2) % 4) return it.level * levelPx_;
    if (const GeomVariant* g = geometry(it))
        for (const auto& [t, z] : g->walkZ)
            if (t == rel) return it.level * levelPx_ + z;
    if (stair) return INT_MIN; // the sides of a stair are parapets
    return it.level * levelPx_;
}

float WorldMap::floorAt(Vec2 p) const {
    const TilePos t{static_cast<int>(std::floor(p.x)), static_cast<int>(std::floor(p.y))};
    if (!inBounds(t)) return 0.0f;
    const auto z = static_cast<float>(floorZ(t));
    const float fx = p.x - static_cast<float>(t.x) - 0.5f;
    const float fy = p.y - static_cast<float>(t.y) - 0.5f;
    std::array<WalkStep, 4> steps{};
    const int n = walkNeighbours(t, steps);
    float out = z;
    for (int i = 0; i < n; ++i) {
        const WalkStep& s = steps[static_cast<std::size_t>(i)];
        const int dx = s.to.x - t.x;
        const int dy = s.to.y - t.y;
        const float toward = dx != 0 ? fx * static_cast<float>(dx) : fy * static_cast<float>(dy);
        if (toward > 0) out += static_cast<float>(s.dz) * toward;
    }
    return out;
}

int WorldMap::walkNeighbours(TilePos p, std::array<WalkStep, 4>& out) const {
    if (!walkable(p)) return 0;
    const std::uint8_t bitsA = chunk(p).walk[local(p)];
    const int occA = itemAt(p);
    const int zA = floorZ(p);
    int n = 0;
    for (int d = 0; d < 4; ++d) {
        const TilePos q{p.x + kSteps[std::size_t(d)].x, p.y + kSteps[std::size_t(d)].y};
        if (!walkable(q)) continue;
        const std::uint8_t bitsB = chunk(q).walk[local(q)];
        const bool inside = (bitsA & kFloor) && (bitsB & kFloor) && occA == itemAt(q);
        if (!inside) {
            const int za = edgeZ(p, d);
            const int zb = edgeZ(q, (d + 2) % 4);
            if (za == INT_MIN || zb == INT_MIN) continue;
            const int tol = ((bitsA | bitsB) & kDeck) ? levelPx_ : levelPx_ / 2;
            if (std::abs(za - zb) > tol) continue;
        }
        out[std::size_t(n++)] = {q, floorZ(q) - zA};
    }
    return n;
}

void WorldMap::piecesIn(TileRect r, std::vector<DrawPiece>& out) const {
    out.clear();
    forEachItemIn(r, [&](std::uint32_t i, const Placed& it) {
        const GeomVariant* g = geometry(it);
        if (g == nullptr || g->pieces.empty()) {
            out.push_back({i, -1, false, it.level, it.rect()});
            return;
        }
        for (std::size_t k = 0; k < g->pieces.size(); ++k) {
            const GeomPiece& gp = g->pieces[k];
            const TileRect pr{it.x + gp.rect.x0, it.y + gp.rect.y0, it.x + gp.rect.x1,
                              it.y + gp.rect.y1};
            if (pr.intersects(r))
                out.push_back({i, static_cast<std::int16_t>(k), gp.floor, it.level, pr});
        }
    });
    std::ranges::sort(out, [](const DrawPiece& a, const DrawPiece& b) {
        const int da = a.rect.x0 + a.rect.x1 + a.rect.y0 + a.rect.y1;
        const int db = b.rect.x0 + b.rect.x1 + b.rect.y0 + b.rect.y1;
        return std::tie(da, a.item, a.piece) < std::tie(db, b.item, b.piece);
    });
}

float WorldMap::themeRadius(int region) const {
    switch (regionKinds_[static_cast<std::size_t>(region)]) {
    case RegionKind::City: return tuning::kThemeRadiusCity;
    case RegionKind::Town: return tuning::kThemeRadiusTown;
    case RegionKind::Seam: return tuning::kThemeRadiusSeam;
    case RegionKind::Home:
    case RegionKind::Stretch: return tuning::kThemeRadiusStretch;
    }
    return tuning::kThemeRadiusStretch;
}

int WorldMap::themeWeights(Vec2 centre, std::span<RegionWeight> out) const {
    constexpr int kSide = tuning::kThemeSamplesPerSide;
    constexpr int kHalf = kSide / 2;
    std::array<RegionWeight, kSide * kSide> acc{};
    int used = 0;
    float total = 0;
    for (int j = 0; j < kSide; ++j)
        for (int i = 0; i < kSide; ++i) {
            const float dx = static_cast<float>(i - kHalf) * tuning::kThemeSampleSpacing;
            const float dy = static_cast<float>(j - kHalf) * tuning::kThemeSampleSpacing;
            const TilePos t{static_cast<int>(std::floor(centre.x + dx)),
                            static_cast<int>(std::floor(centre.y + dy))};
            if (!inBounds(t)) continue;
            const int region = regionAt(t);
            if (region < 0) continue;
            const float x = 1.0f - std::sqrt(dx * dx + dy * dy) / themeRadius(region);
            if (x <= 0) continue;
            const float w = x * x * (3.0f - 2.0f * x);
            int k = 0;
            while (k < used && acc[std::size_t(k)].region != region) ++k;
            if (k == used) acc[std::size_t(used++)] = {region, 0.0f};
            acc[std::size_t(k)].weight += w;
            total += w;
        }
    if (total <= 0) return 0;
    std::sort(acc.begin(), acc.begin() + used, [](const RegionWeight& a, const RegionWeight& b) {
        return a.weight != b.weight ? a.weight > b.weight : a.region < b.region;
    });
    const int n = std::min(used, static_cast<int>(out.size()));
    for (int k = 0; k < n; ++k)
        out[std::size_t(k)] = {acc[std::size_t(k)].region, acc[std::size_t(k)].weight / total};
    return n;
}

bool WorldMap::updateHomeTerrain(const HomeDelta& delta) {
    const TileRect hr = home_.rect;
    const int hw = hr.x1 - hr.x0;
    const int hh = hr.y1 - hr.y0;
    const auto cells = static_cast<std::size_t>(hw * hh);
    if (delta.w != hw || delta.h != hh || delta.terrain.size() != cells ||
        (!delta.wild.empty() && delta.wild.size() != cells) || !homeCleared_)
        return false;
    std::vector<int> palette;
    for (const std::string& id : delta.palette) {
        const auto it = std::ranges::find(terrains_, id, &TerrainInfo::id);
        if (it == terrains_.end()) return false;
        palette.push_back(static_cast<int>(it - terrains_.begin()));
    }
    for (int y = 0; y < hh; ++y)
        for (int x = 0; x < hw; ++x) {
            const std::uint8_t v = delta.terrain[static_cast<std::size_t>(y * hw + x)];
            if (v != kNone && v >= palette.size()) return false;
            const auto t = static_cast<std::uint8_t>(v == kNone ? kNone : palette[v]);
            const TilePos p{hr.x0 + x, hr.y0 + y};
            std::uint8_t& cell = chunk(p).terrain[local(p)];
            if (cell != t) cell = t;
        }
    if (homeWild_ != delta.wild) homeWild_ = delta.wild;
    return true;
}

std::expected<void, std::string> WorldMap::applyHome(const HomeDelta& delta, Diagnostics& diag) {
    const TileRect hr = home_.rect;
    const int hw = hr.x1 - hr.x0;
    const int hh = hr.y1 - hr.y0;
    if (delta.w != hw || delta.h != hh)
        return std::unexpected("the home delta is " + std::to_string(delta.w) + " x " +
                               std::to_string(delta.h) + ", the home region " + std::to_string(hw) +
                               " x " + std::to_string(hh));
    const auto cells = static_cast<std::size_t>(hw * hh);
    if (delta.terrain.size() != cells || (!delta.wild.empty() && delta.wild.size() != cells))
        return std::unexpected("the home delta's planes do not cover its map");
    std::vector<int> palette;
    for (const std::string& id : delta.palette) {
        const int t = internTerrain(id);
        if (t < 0) return std::unexpected("the world would hold more than 255 terrain ids");
        palette.push_back(t);
    }
    for (const std::uint8_t v : delta.terrain)
        if (v != kNone && v >= palette.size())
            return std::unexpected("the home delta names palette entry " + std::to_string(v) +
                                   " of " + std::to_string(palette.size()));
    const int homeDistrict = internDistrict(regionIds_[std::size_t(home_.region)] + "/home");
    if (homeDistrict < 0) return std::unexpected("the world would hold more than 255 districts");

    const bool full = !homeCleared_;
    homeCleared_ = true;
    items_.resize(homeBegin_);
    for (int y = 0; y < hh; ++y)
        for (int x = 0; x < hw; ++x) {
            const TilePos p{hr.x0 + x, hr.y0 + y};
            const std::uint8_t v = delta.terrain[static_cast<std::size_t>(y * hw + x)];
            Chunk& c = chunk(p);
            const std::size_t l = local(p);
            c.level[l] = static_cast<std::uint8_t>(home_.level);
            if (v == kNone) {
                c.terrain[l] = kNone;
                c.district[l] = kNone;
                continue;
            }
            c.terrain[l] = static_cast<std::uint8_t>(palette[v]);
            if (c.district[l] == kNone) c.district[l] = static_cast<std::uint8_t>(homeDistrict);
        }
    homeWild_ = delta.wild;
    std::vector<std::uint8_t> taken(cells, 0);
    for (const HomeItem& hi : delta.items) {
        const std::string where = "home item " + hi.id + " at (" + std::to_string(hi.x) + ", " +
                                  std::to_string(hi.y) + ")";
        const int idx = content_->findItem(hi.id);
        if (idx < 0) {
            diag.warn(where + ": no catalog has it; skipped");
            continue;
        }
        const ItemInfo& inf = content_->item(idx);
        if (hi.variant < 0 || hi.variant >= std::max(inf.count, 1) || hi.variant > 0xFF) {
            diag.warn(where + ": variant " + std::to_string(hi.variant) + " out of range; skipped");
            continue;
        }
        const Footprint fp = inf.footprint(hi.variant);
        const TileRect r{hi.x, hi.y, hi.x + fp.w, hi.y + fp.h};
        if (!TileRect{0, 0, hw, hh}.contains(r)) {
            diag.warn(where + ": leaves the home region; skipped");
            continue;
        }
        bool clash = false;
        for (int y = r.y0; y < r.y1; ++y)
            for (int x = r.x0; x < r.x1; ++x)
                clash |= taken[static_cast<std::size_t>(y * hw + x)] != 0;
        if (clash) {
            diag.warn(where + ": overlaps another home item; skipped");
            continue;
        }
        for (int y = r.y0; y < r.y1; ++y)
            for (int x = r.x0; x < r.x1; ++x) taken[static_cast<std::size_t>(y * hw + x)] = 1;
        Placed p;
        p.info = static_cast<std::uint32_t>(idx);
        p.x = static_cast<std::int16_t>(hr.x0 + hi.x);
        p.y = static_cast<std::int16_t>(hr.y0 + hi.y);
        p.w = static_cast<std::uint8_t>(fp.w);
        p.h = static_cast<std::uint8_t>(fp.h);
        p.variant = static_cast<std::uint8_t>(hi.variant);
        p.layer = kHomeLayer;
        p.level = static_cast<std::uint8_t>(home_.level);
        stairHead(p, diag);
        items_.push_back(p);
    }
    if (full) {
        rebuildAll(diag);
    } else {
        index(hr, homeBegin_, diag);
        slots_.resize(homeSlotBegin_);
        buildSlots(homeBegin_, static_cast<std::uint32_t>(items_.size()), diag);
    }
    return {};
}

std::size_t WorldMap::memoryBytes() const {
    std::size_t n = chunks_.capacity() * sizeof(Chunk);
    for (const Chunk& c : chunks_)
        n += (c.items.capacity() + c.big.capacity()) * sizeof(std::uint32_t);
    n += items_.capacity() * sizeof(Placed) + slots_.capacity() * sizeof(WorldSlot);
    n += (slotChunkStart_.capacity() + slotByDistrict_.capacity() + slotDistrictStart_.capacity()) *
         sizeof(std::uint32_t);
    n += terrains_.capacity() * sizeof(TerrainInfo) + districts_.capacity() * sizeof(District);
    for (const District& d : districts_) n += d.name.capacity();
    n += homeWild_.capacity();
    return n;
}

} // namespace lc::world
