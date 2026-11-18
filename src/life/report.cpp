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
    // Slot spots: a walker stands on the spot or beside it (a seat on its item is used from
    // the tile next to it), as resolve() does; a spot with neither is never used.
    std::vector<std::tuple<std::uint32_t, std::uint16_t, int, int>> seen;
    for (const world::WorldSlot& s : m.slots()) {
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

} // namespace lc::life
