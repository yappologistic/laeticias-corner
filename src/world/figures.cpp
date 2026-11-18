#include "world/figures.hpp"

#include <algorithm>
#include <cmath>
#include <set>

namespace lc::world {
namespace {

constexpr float kFigureHead = 48.0f;  // px above the feet: what must stay in view
constexpr float kFigureHalfW = 12.0f; // and to either side
constexpr int kFrontReach = 24;       // tiles in front searched for landmarks that could hide one

// The first `go` target of the figure's first routine, if it names something we can find.
std::optional<Vec2> routineTarget(const LoadedWorld& w, int region, const nlohmann::json& fig) {
    const auto routines = fig.find("routines");
    if (routines == fig.end() || !routines->is_object() || routines->empty()) return std::nullopt;
    // The first scheduled routine, else the first listed.
    std::string first = routines->begin().key();
    if (const auto sch = fig.find("schedule"); sch != fig.end() && sch->is_array() &&
                                               !sch->empty() && (*sch)[0].contains("routine") &&
                                               (*sch)[0]["routine"].is_string())
        first = (*sch)[0]["routine"].get<std::string>();
    const auto r = routines->find(first);
    if (r == routines->end() || !r->contains("steps") || !(*r)["steps"].is_array())
        return std::nullopt;
    const WorldMap& m = *w.map;
    for (const nlohmann::json& step : (*r)["steps"]) {
        const auto go = step.find("go");
        if (go == step.end() || !go->is_object()) continue;
        if (const auto node = go->find("node"); node != go->end() && node->is_string()) {
            const std::string id = w.file.regions[static_cast<std::size_t>(region)].id + ":" +
                                   node->get<std::string>();
            if (const int n = w.roads.findNode(id); n >= 0) {
                const TilePos t = w.roads.nodes()[static_cast<std::size_t>(n)].at;
                return Vec2{static_cast<float>(t.x) + 0.5f, static_cast<float>(t.y) + 0.5f};
            }
        }
        const auto item = go->find("item");
        if (item == go->end() || !item->is_string()) continue;
        const int info = m.content().findItem(item->get<std::string>());
        if (info < 0) continue;
        const std::string slot = go->value("slot", std::string{});
        // A slot of an instance of that item in the region, else the instance's middle.
        for (const WorldSlot& s : m.slots()) {
            const Placed& p = m.items()[s.item];
            if (static_cast<int>(p.info) != info || m.regionAt(s.tile) != region) continue;
            if (slot.empty() || m.slotNames()[s.name] == slot) return s.at;
        }
        for (const Placed& p : m.items())
            if (static_cast<int>(p.info) == info && m.regionAt({p.x, p.y}) == region) {
                const TileRect r2 = p.rect();
                return Vec2{static_cast<float>(r2.x0 + r2.x1) * 0.5f,
                            static_cast<float>(r2.y1) + 0.5f};
            }
    }
    return std::nullopt;
}

} // namespace

std::vector<FigurePlace> placeFigures(const LoadedWorld& w) {
    std::vector<FigurePlace> out;
    const WorldMap& m = *w.map;
    std::set<std::pair<int, int>> taken;
    // A landmark in front of a figure on screen would hide it: one whose footprint lies further
    // along +x or +y (drawn after it) and whose screen box (footprint diamond raised by its
    // catalog height) covers the figure's head.
    const float hw = m.content().home().iso().hw;
    const float hh = m.content().home().iso().hh;
    const float lvl = static_cast<float>(m.content().tileLevel());
    const auto screenOf = [&](float x, float y) { return Vec2{(x - y) * hw, (x + y) * hh}; };
    const auto hidden = [&](TilePos p) {
        const Vec2 f = screenOf(static_cast<float>(p.x) + 0.5f, static_cast<float>(p.y) + 0.5f);
        const float headY = f.y - static_cast<float>(m.level(p)) * lvl - kFigureHead;
        bool covered = false;
        m.forEachItemIn({p.x - 2, p.y - 2, p.x + kFrontReach, p.y + kFrontReach},
                        [&](std::uint32_t, const Placed& it) {
                            const ItemInfo& inf = m.info(it);
                            const TileRect r = it.rect();
                            if (covered || !inf.landmark || (r.x0 <= p.x && r.y0 <= p.y)) return;
                            const auto fx = [](int v) { return static_cast<float>(v); };
                            const float x0 = screenOf(fx(r.x0), fx(r.y1)).x;
                            const float x1 = screenOf(fx(r.x1), fx(r.y0)).x;
                            const float y1 = screenOf(fx(r.x1), fx(r.y1)).y - fx(it.level) * lvl;
                            const float y0 = screenOf(fx(r.x0), fx(r.y0)).y - fx(it.level) * lvl -
                                             static_cast<float>(inf.height);
                            // Any of the figure's width, from its feet to its head.
                            covered = f.x + kFigureHalfW > x0 && f.x - kFigureHalfW < x1 &&
                                      f.y > y0 && headY < y1;
                        });
        return covered;
    };
    // A free walkable tile near `want`, by rings, so figures never share a tile.
    const auto settle = [&](Vec2 want, int region) -> std::optional<TilePos> {
        const TilePos c{static_cast<int>(std::floor(want.x)), static_cast<int>(std::floor(want.y))};
        for (int ring = 0; ring <= 16; ++ring)
            for (int dy = -ring; dy <= ring; ++dy)
                for (int dx = -ring; dx <= ring; ++dx) {
                    if (std::max(std::abs(dx), std::abs(dy)) != ring) continue;
                    const TilePos p{c.x + dx, c.y + dy};
                    // Open ground only: standing still inside a hall, nobody would see them.
                    if (!m.inBounds(p) || !m.walkable(p) || m.itemAt(p) >= 0 ||
                        m.regionAt(p) != region || taken.contains({p.x, p.y}) || hidden(p))
                        continue;
                    return p;
                }
        return std::nullopt;
    };
    for (std::size_t r = 0; r < w.regions.size(); ++r) {
        const RegionFile& f = w.regions[r];
        const auto figs = f.life.find("figures");
        if (f.id.empty() || figs == f.life.end() || !figs->is_array()) continue;
        const int region = static_cast<int>(r);
        const auto mk = std::ranges::find(w.file.markers, region, &Marker::region);
        const Vec2 home = mk != w.file.markers.end() ? Vec2{static_cast<float>(mk->at.x) + 0.5f,
                                                            static_cast<float>(mk->at.y) + 0.5f}
                                                     : Vec2{-1, -1};
        int n = 0;
        for (const nlohmann::json& fig : *figs) {
            if (!fig.is_object() || !fig.contains("actor") || !fig["actor"].is_string()) continue;
            const std::string actor = fig["actor"].get<std::string>();
            const SetActor* a = nullptr;
            for (const SetCatalog& s : m.content().sets())
                for (const SetActor& sa : s.actors)
                    if (sa.id == actor) a = &sa;
            if (a == nullptr) continue;
            std::optional<Vec2> want = routineTarget(w, region, fig);
            if (!want && home.x >= 0) {
                // Spread around the marker on a loose spiral.
                const float ang = static_cast<float>(n) * 2.39996f;
                const float rad = 2.0f + 1.1f * std::sqrt(static_cast<float>(n));
                want = Vec2{home.x + std::cos(ang) * rad, home.y + std::sin(ang) * rad};
            }
            ++n;
            if (!want) continue;
            const auto t = settle(*want, region);
            if (!t) continue;
            taken.insert({t->x, t->y});
            out.push_back({region,
                           actor,
                           fig.value("card", std::string{}),
                           a->sprite,
                           {static_cast<float>(t->x) + 0.5f, static_cast<float>(t->y) + 0.5f},
                           m.level(*t)});
        }
    }
    return out;
}

} // namespace lc::world
