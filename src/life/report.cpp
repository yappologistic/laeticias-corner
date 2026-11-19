#include "life/report.hpp"

#include <nlohmann/json.hpp>

#include <algorithm>
#include <array>
#include <cmath>
#include <format>
#include <map>
#include <tuple>

namespace lc::life {

using ojson = nlohmann::ordered_json;
namespace tl = tuning::life;

namespace {

double round6(double v) {
    return std::round(v * 1e6) / 1e6;
}
double round2(double v) {
    return std::round(v * 100.0) / 100.0;
}

const char* sourceName(Source s) {
    switch (s) {
    case Source::Population: return "population";
    case Source::Figure: return "figure";
    case Source::Chain: return "chain";
    case Source::Token: return "token";
    case Source::Cast: return "cast";
    }
    return "?";
}

const char* stateName(ActState s) {
    switch (s) {
    case ActState::Idle: return "idle";
    case ActState::Travel: return "travel";
    case ActState::Act: return "act";
    case ActState::Wander: return "wander";
    case ActState::Inside: return "inside";
    case ActState::Follow: return "follow";
    case ActState::Puppet: return "puppet";
    case ActState::Leave: return "leave";
    }
    return "?";
}

const char* verbName(Verb v) {
    switch (v) {
    case Verb::Go: return "go";
    case Verb::Use: return "use";
    case Verb::Take: return "take";
    case Verb::Put: return "put";
    case Verb::Wander: return "wander";
    case Verb::Wait: return "wait";
    case Verb::Enter: return "enter";
    case Verb::Follow: return "follow";
    case Verb::Emit: return "emit";
    case Verb::Pick: return "pick";
    case Verb::Each: return "each";
    case Verb::Routine: return "routine";
    }
    return "?";
}

} // namespace

std::string chainReport(const LifeWorld& w, int days) {
    // Region order as worldgen's LAYERS lists them does not matter: keys are sorted.
    std::map<std::string, ojson> out;
    const auto& paths = w.paths;
    for (std::size_t r = 0; r < w.data.regions.size(); ++r) {
        const LifeRegion& reg = w.data.regions[r];
        const int p = w.pathsOf[r];
        if (p < 0) continue;
        for (const Chain& c : reg.chains) {
            ChainRun run(w.data, reg, c, w.map(), paths[static_cast<std::size_t>(p)]);
            run.setDays(days);
            ojson j;
            ojson counts = ojson::object();
            ojson stages = ojson::array();
            ojson travel = ojson::array();
            if (run.ok()) {
                for (long t = 0; t < static_cast<long>(days) * 720; ++t)
                    run.tick(t, run.hoursOn(t), 1.0); // lifesim: hours only, one pace
                std::map<std::string, int> sorted;
                for (const ChainRun::Counter& k : run.counters())
                    sorted[k.ref + "|" + w.data.goods[static_cast<std::size_t>(k.goods)]] = k.count;
                for (const auto& [k, v] : sorted) counts[k] = v;
                for (const ChainStats& s : run.stats())
                    stages.push_back({s.work, s.starve, s.block, s.done});
                for (std::size_t s = 0; s < c.stages.size(); ++s)
                    travel.push_back(round6(run.travel(s)));
            }
            j["count"] = counts;
            j["errors"] = run.errors();
            j["per_day"] =
                run.ok() ? run.perDay() : std::vector<long>(static_cast<std::size_t>(days), 0);
            j["stages"] = stages;
            j["travel"] = travel;
            out[reg.id + "/" + c.id] = std::move(j);
        }
    }
    ojson all = ojson::object();
    for (auto& [k, v] : out) all[k] = std::move(v);
    return all.dump(1) + "\n";
}

std::string lifeDump(const CityLife& life, std::string_view label) {
    const LifeWorld& w = life.lifeWorld();
    const LifeData& data = w.data;
    const WorldMap& map = w.map();
    const LifeClock& c = life.clock();
    ojson j;
    j["label"] = label;
    j["day"] = c.day;
    j["hour"] = round2(c.hour());
    j["season"] = c.season < static_cast<int>(data.seasons.size())
                      ? data.seasons[static_cast<std::size_t>(c.season)]
                      : "";
    j["rain"] = c.rain;
    j["view"] = {life.view().x0, life.view().y0, life.view().x1, life.view().y1};
    j["active"] = {life.activeRect().x0, life.activeRect().y0, life.activeRect().x1,
                   life.activeRect().y1};
    const LifeStats& s = life.stats();
    j["stats"] = {{"live", s.live},
                  {"visible", s.visible},
                  {"population", s.bySource[0]},
                  {"figures", s.bySource[1]},
                  {"chain_workers", s.bySource[2]},
                  {"tokens_live", s.bySource[3]},
                  {"cast", s.bySource[4]},
                  {"tokens", s.tokens},
                  {"running_events", s.running},
                  {"queued", s.queued},
                  {"walking_in_place", s.marching},
                  {"to_and_fro", s.oscillating},
                  {"stuck", s.stuck},
                  {"waiting", s.waiting},
                  {"unstuck", s.unstuck},
                  {"scale", round2(s.scale)}};
    ojson districts = ojson::array();
    std::vector<DistrictCount> counts = life.districtCounts();
    std::ranges::sort(counts, [](const DistrictCount& a, const DistrictCount& b) {
        return a.region != b.region ? a.region < b.region : a.district < b.district;
    });
    for (const DistrictCount& d : counts) {
        const LifeRegion& reg = data.regions[static_cast<std::size_t>(d.region)];
        const District& dist = reg.districts[static_cast<std::size_t>(d.district)];
        static constexpr std::array<const char*, 6> kAreas{"centre", "town", "country",
                                                           "road",   "sea",  "wild"};
        districts.push_back({{"region", reg.id},
                             {"district", dist.id},
                             {"area", kAreas[static_cast<std::size_t>(dist.area)]},
                             {"map", dist.map},
                             {"expected", round2(d.expected)},
                             {"formula", round2(d.formula)},
                             {"live", d.live},
                             {"inside", d.inside}});
    }
    j["districts"] = districts;
    // Actors, in a stable order (identity keys) so two runs dump byte for byte.
    struct Row {
        std::uint64_t key;
        ojson v;
    };
    std::vector<Row> rows;
    life.forEachInfo([&](const CityLife::Info& in) {
        const LifeRegion& reg = data.regions[static_cast<std::size_t>(in.region)];
        ojson a;
        a["kind"] = data.kinds[static_cast<std::size_t>(in.kind)].id;
        a["source"] = sourceName(in.source);
        a["role"] = in.role >= 0 && in.source != Source::Token && in.source != Source::Cast
                        ? ojson(reg.roles[static_cast<std::size_t>(in.role)].id)
                        : ojson(nullptr);
        a["region"] = reg.id;
        a["district"] = in.district >= 0
                            ? ojson(reg.districts[static_cast<std::size_t>(in.district)].id)
                            : ojson(nullptr);
        a["x"] = round2(in.pos.x);
        a["y"] = round2(in.pos.y);
        a["level"] = in.level;
        a["walkable"] = map.inBounds(in.tile) && map.walkable(in.tile);
        a["state"] = stateName(in.state);
        a["step"] = in.step >= 0
                        ? ojson(verbName(data.steps[static_cast<std::size_t>(in.step)].verb))
                        : ojson(nullptr);
        a["goods"] =
            in.goods >= 0 ? ojson(data.goods[static_cast<std::size_t>(in.goods)]) : ojson(nullptr);
        a["count"] = in.goodsCount;
        a["visible"] = in.visible;
        rows.push_back({in.key, std::move(a)});
    });
    std::ranges::sort(rows, {}, &Row::key);
    ojson actors = ojson::array();
    for (Row& r : rows) actors.push_back(std::move(r.v));
    j["actors"] = actors;
    ojson events = ojson::array();
    for (const RunningEvent& e : life.running()) {
        if (e.event < 0) continue;
        const LifeRegion& reg = data.regions[static_cast<std::size_t>(e.region)];
        ojson route = ojson::array();
        const auto t = life.trail(e);
        for (std::size_t k = 0; k < t.size(); k += 4) route.push_back({t[k].x, t[k].y});
        if (!t.empty()) route.push_back({t.back().x, t.back().y});
        events.push_back({{"region", reg.id},
                          {"id", reg.events[static_cast<std::size_t>(e.event)].id},
                          {"start", round2(e.start)},
                          {"end", round2(e.end)},
                          {"place", {round2(e.place.x), round2(e.place.y)}},
                          {"active", e.active},
                          {"route", route}});
    }
    j["events"] = events;
    ojson stocks = ojson::array();
    life.forEachStock(life.activeRect(), [&](const world::WorldSlot& sl, int goods, int count) {
        stocks.push_back({{"x", round2(sl.at.x)},
                          {"y", round2(sl.at.y)},
                          {"goods", data.goods[static_cast<std::size_t>(goods)]},
                          {"count", count}});
    });
    j["stocks"] = stocks;
    // The ground under the area (and a margin): district, walkable, water, level per tile, so a
    // picture needs nothing else.
    const TileRect a = life.activeRect();
    const TileRect m = TileRect{a.x0 - 16, a.y0 - 16, a.x1 + 16, a.y1 + 16}.clipped(map.bounds());
    std::string tiles;
    tiles.reserve(static_cast<std::size_t>(m.width() * m.height()) * 4);
    std::map<int, std::string> names;
    for (int y = m.y0; y < m.y1; ++y)
        for (int x = m.x0; x < m.x1; ++x) {
            const int d = map.districtAt({x, y});
            const int t = map.terrainAt({x, y});
            const bool water = t != world::kNone && map.terrainInfo(t).water;
            const int code = (d == world::kNone ? 255 : d) * 64 + (map.walkable({x, y}) ? 32 : 0) +
                             (water ? 16 : 0) + std::min(15, map.level({x, y}));
            tiles += std::to_string(code);
            tiles += ' ';
            if (d != world::kNone) names[d] = map.districtName(d);
        }
    ojson dn = ojson::object();
    for (const auto& [k, v] : names) dn[std::to_string(k)] = v;
    j["ground"] = {{"rect", {m.x0, m.y0, m.x1, m.y1}}, {"names", dn}, {"tiles", tiles}};
    return j.dump(1) + "\n";
}

std::vector<std::string> walkProblems(const LifeWorld& w) {
    std::vector<std::string> out;
    const world::WorldMap& m = w.map();
    for (std::size_t r = 0; r < w.data.regions.size(); ++r) {
        const int pi = w.pathsOf[r];
        if (pi < 0) continue;
        const RegionPaths& rp = w.paths[static_cast<std::size_t>(pi)];
        const std::string& region = w.data.regions[r].id;
        for (std::size_t e = 0; e < rp.edges().size() && rp.blockedEdges() > 0; ++e) {
            const RegionPaths::Edge& ed = rp.edges()[e];
            if (!ed.blocked) continue;
            const auto c = rp.course(static_cast<int>(e));
            std::array<world::WalkStep, 4> steps{};
            for (std::size_t k = 0; k < c.size(); ++k) {
                const TilePos t = c[k].pos();
                bool legal = true;
                if (k > 0) {
                    const int n = m.walkNeighbours(c[k - 1].pos(), steps);
                    legal = std::any_of(steps.begin(), steps.begin() + n,
                                        [&](const world::WalkStep& s) { return s.to == t; });
                }
                if (!m.walkable(t) || !legal) {
                    out.push_back(
                        std::format("{}: graph edge {} - {}: {} at grid ({}, {}), level {}", region,
                                    rp.nodeId(ed.a), rp.nodeId(ed.b),
                                    !m.walkable(t) ? "course over unwalkable ground"
                                                   : "a step no walker can make",
                                    t.x, t.y, m.level(t)));
                    break;
                }
            }
        }
    }
    // Districts with people to place and no ground their region's walkers reach: nobody of
    // them ever appears (gulls over the open sea would need to fly).
    for (std::size_t r = 0; r < w.data.regions.size(); ++r) {
        const int pi = w.pathsOf[r];
        const LifeRegion& reg = w.data.regions[r];
        for (const District& d : reg.districts) {
            if (d.populations.empty() || d.map < 0) continue;
            bool ground = false;
            for (const auto& [chunk, tiles] : d.chunks) {
                const int cx = static_cast<int>(chunk) % m.chunksX();
                const int cy = static_cast<int>(chunk) / m.chunksX();
                for (int y = cy * kChunk; y < (cy + 1) * kChunk && !ground; ++y)
                    for (int x = cx * kChunk; x < (cx + 1) * kChunk && !ground; ++x) {
                        const TilePos t{x, y};
                        ground = m.inBounds(t) && m.districtAt(t) == d.map && m.walkable(t) &&
                                 pi >= 0 && w.paths[static_cast<std::size_t>(pi)].reachable(t);
                    }
                if (ground) break;
            }
            if (ground) continue;
            const TilePos at =
                d.chunks.empty()
                    ? TilePos{0, 0}
                    : TilePos{static_cast<int>(d.chunks.front().first) % m.chunksX() * kChunk,
                              static_cast<int>(d.chunks.front().first) / m.chunksX() * kChunk};
            out.push_back(std::format("{}: district {}: {} populations but no ground its walkers "
                                      "reach, first chunk at grid ({}, {})",
                                      reg.id, d.id, d.populations.size(), at.x, at.y));
        }
    }
    // Walkable decks over water with no floor height in their geometry (the art tool's
    // `walk_z`): walkers on them stand on the deck's highest point (`tops`: the rail), or at the
    // water's level, through the deck, where it has none.
    std::map<std::string, std::pair<int, TilePos>> decks;
    for (const world::Placed& it : m.items()) {
        const world::ItemInfo& inf = m.info(it);
        const int t = m.terrainAt({it.x, it.y});
        if (!inf.walkable || t == world::kNone || !m.terrainInfo(t).water) continue;
        const world::GeomVariant* g = m.geometry(it);
        if (g != nullptr && !g->walkZ.empty()) continue;
        ++decks.try_emplace(inf.id, 0, TilePos{it.x, it.y}).first->second.first;
    }
    for (const auto& [id, e] : decks)
        out.push_back(std::format("{}: {} walkable decks over water with no floor height "
                                  "(geometry walk_z): walkers stand on its top (tops) or the "
                                  "water, first at grid ({}, {})",
                                  id, e.first, e.second.x, e.second.y));
    // Slot spots: a walker stands on the spot or beside it (a seat on its item is used from
    // the tile next to it), as resolve() does; a spot with neither is never used.
    std::vector<std::tuple<std::uint32_t, std::uint16_t, int, int>> seen;
    for (const world::WorldSlot& s : m.slots()) {
        if (m.slotKinds()[s.kind] == "mooring") continue; // a boat's place, on the water
        const world::Placed& it = m.items()[s.item];
        const int lr = w.data.regionOfWorld(m.regionAt({it.x, it.y}));
        if (lr < 0 || w.pathsOf[static_cast<std::size_t>(lr)] < 0) continue;
        const RegionPaths& rp =
            w.paths[static_cast<std::size_t>(w.pathsOf[static_cast<std::size_t>(lr)])];
        const auto stand = [&](TilePos t) {
            return m.inBounds(t) && m.walkable(t) && rp.reachable(t);
        };
        bool ok = stand(s.tile);
        for (const TilePos d : world::kSteps) ok = ok || stand({s.tile.x + d.x, s.tile.y + d.y});
        if (ok) continue;
        const auto key = std::tuple{s.item, s.name, s.tile.x, s.tile.y};
        if (std::ranges::find(seen, key) != seen.end()) continue;
        seen.push_back(key);
        const bool walkable = m.inBounds(s.tile) && m.walkable(s.tile);
        out.push_back(std::format("{}: slot {} of {} at grid ({}, {}): {}",
                                  w.data.regions[static_cast<std::size_t>(lr)].id,
                                  m.slotNames()[s.name], m.info(it).id, s.tile.x, s.tile.y,
                                  walkable ? "no walker of the region reaches it"
                                           : "nowhere to stand at or beside it"));
    }
    return out;
}

FloorCheck checkFloors(const CityLife& life, TileRect rect, std::vector<DrawActor>& scratch) {
    FloorCheck out;
    const world::WorldMap& m = life.lifeWorld().map();
    const auto& kinds = life.lifeWorld().data.kinds;
    scratch.resize(std::max<std::size_t>(scratch.size(), 4096));
    // Each actor at the start and at the end of its last step, by drawing it at both ends.
    const std::size_t half = scratch.size() / 2;
    const std::span<DrawActor> before(scratch.data(), half);
    const std::span<DrawActor> after(scratch.data() + half, half);
    const std::size_t n0 = life.gather(rect, 0.0f, before);
    const std::size_t n1 = life.gather(rect, 1.0f, after);
    const auto bad = [&](TilePos t) {
        if (out.firstBad.x < 0) out.firstBad = t;
    };
    for (std::size_t i = 0; i < n1; ++i) {
        const DrawActor& d = after[i];
        const TilePos t{static_cast<int>(std::floor(d.pos.x)),
                        static_cast<int>(std::floor(d.pos.y))};
        if (d.alpha < 1.0f || !m.inBounds(t)) continue;
        if (i < n0 && before[i].handle == d.handle && before[i].alpha >= 1.0f) {
            const float dz = std::abs(d.z - before[i].z);
            const float dp = std::hypot(d.pos.x - before[i].pos.x, d.pos.y - before[i].pos.y);
            out.worstStep = std::max(out.worstStep, dz);
            out.worstMove = std::max(out.worstMove, dp);
            if (dz > tl::kFloorStepPx) ++out.jumps, bad(t);
            if (dp > tl::kFloorStepTiles) ++out.hops, bad(t);
        }
        if (kinds[d.kind].ship) {
            ++out.afloat;
            if (std::abs(d.z - static_cast<float>(m.level(t) * m.levelPx())) > tl::kFloorSlackPx)
                ++out.offWater, bad(t);
            continue;
        }
        if (d.speed <= 0 || !m.walkable(t)) continue;
        std::array<world::WalkStep, 4> steps{};
        const int ns = m.walkNeighbours(t, steps);
        const int own = m.floorZ(t);
        float lo = static_cast<float>(own);
        float hi = lo;
        for (int j = 0; j < ns; ++j) {
            const auto z = static_cast<float>(m.floorZ(steps[static_cast<std::size_t>(j)].to));
            lo = std::min(lo, z);
            hi = std::max(hi, z);
        }
        out.raised += own != m.level(t) * m.levelPx() ? 1 : 0;
        if (d.z < lo - tl::kFloorSlackPx || d.z > hi + tl::kFloorSlackPx) ++out.offFloor, bad(t);
    }
    return out;
}

} // namespace lc::life
