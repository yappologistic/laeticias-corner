#include "core/condition.hpp"

#include "core/catalog.hpp"
#include "core/world.hpp"

#include <nlohmann/json.hpp>

#include <algorithm>
#include <stdexcept>

namespace lc {
namespace {

using nlohmann::json;

constexpr std::array<std::string_view, 4> kPhases{"day", "dusk", "night", "dawn"};
constexpr std::array<std::string_view, kCounters> kCounterNames{"wishes", "seen",     "nooks",
                                                                "pages",  "harvests", "stage"};
constexpr int kMaxWithin = 4;
constexpr int kMaxHas = 8;

[[noreturn]] void fail(const std::string& msg) {
    throw std::runtime_error(msg);
}

int intField(const json& j, const char* key, int fallback, const std::string& ctx) {
    if (!j.contains(key)) return fallback;
    if (!j[key].is_number_integer()) fail(ctx + ": '" + key + "' must be an integer");
    return j[key].get<int>();
}

const std::string& stringOf(const json& j, const std::string& ctx) {
    if (!j.is_string()) fail(ctx + ": expected a string");
    return j.get_ref<const std::string&>();
}

bool hasBit(std::uint8_t mask, int bit) {
    return ((mask >> bit) & 1) != 0;
}

} // namespace

int ConditionSet::compileSelector(const json& j, const Catalog& cat, const std::string& ctx) {
    Selector s;
    int keys = 0;
    const auto addItem = [&](const std::string& id) {
        const auto i = cat.findItem(id);
        if (!i) fail(ctx + ": unknown item '" + id + "'");
        s.ids.push_back(*i);
    };
    const auto addTerrain = [&](const std::string& id) {
        const auto t = cat.findTerrain(id);
        if (!t) fail(ctx + ": unknown terrain '" + id + "'");
        s.ids.push_back(*t);
    };
    if (j.contains("item")) {
        ++keys;
        addItem(stringOf(j["item"], ctx));
    }
    if (j.contains("items")) {
        ++keys;
        if (!j["items"].is_array() || j["items"].empty())
            fail(ctx + ": 'items' must be a non-empty list");
        for (const auto& id : j["items"]) addItem(stringOf(id, ctx));
    }
    if (j.contains("tag")) {
        ++keys;
        s.tag = true;
        const auto& tag = stringOf(j["tag"], ctx);
        const auto t = cat.findTag(tag);
        if (!t) fail(ctx + ": no item carries the tag '" + tag + "'");
        for (std::size_t i = 0; i < cat.items.size(); ++i)
            if (std::ranges::find(cat.items[i].tags, *t) != cat.items[i].tags.end())
                s.ids.push_back(static_cast<int>(i));
    }
    if (j.contains("terrain")) {
        ++keys;
        s.terrain = true;
        addTerrain(stringOf(j["terrain"], ctx));
    }
    if (j.contains("terrains")) {
        ++keys;
        s.terrain = true;
        if (!j["terrains"].is_array() || j["terrains"].empty())
            fail(ctx + ": 'terrains' must be a non-empty list");
        for (const auto& id : j["terrains"]) addTerrain(stringOf(id, ctx));
    }
    if (keys != 1)
        fail(ctx + ": a selector needs exactly one of item, items, tag, terrain, terrains");
    s.match.assign(s.terrain ? cat.terrain.size() : cat.items.size(), 0);
    for (const int i : s.ids) s.match[static_cast<std::size_t>(i)] = 1;
    selectors_.push_back(std::move(s));
    return static_cast<int>(selectors_.size()) - 1;
}

int ConditionSet::compile(const json& j, const Catalog& cat, std::span<const std::string> nookIds,
                          const std::string& ctx) {
    if (!j.is_object() || j.size() != 1) fail(ctx + ": a condition is an object with one key");
    const std::string key = j.begin().key();
    const json& v = j.begin().value();
    CondNode n;
    const auto minMax = [&](const json& o, CondNode& out) {
        out.max = intField(o, "max", -1, ctx);
        out.min = intField(o, "min", o.contains("max") ? 0 : 1, ctx);
        if (out.min < 0 || (out.max >= 0 && out.max < out.min) || out.max < -1)
            fail(ctx + ": min and max are out of order");
    };
    if (key == "all" || key == "any") {
        n.kind = key == "all" ? CondKind::All : CondKind::Any;
        if (!v.is_array()) fail(ctx + ": '" + key + "' takes a list");
        std::vector<int> kids;
        for (const auto& c : v) kids.push_back(compile(c, cat, nookIds, ctx));
        n.first = static_cast<int>(children_.size());
        n.count = static_cast<int>(kids.size());
        children_.insert(children_.end(), kids.begin(), kids.end());
    } else if (key == "not") {
        n.kind = CondKind::Not;
        const int kid = compile(v, cat, nookIds, ctx);
        n.first = static_cast<int>(children_.size());
        n.count = 1;
        children_.push_back(kid);
    } else if (key == "count") {
        n.kind = CondKind::Count;
        if (!v.is_object()) fail(ctx + ": 'count' takes a selector");
        json sel = v;
        sel.erase("min");
        sel.erase("max");
        n.selector = compileSelector(sel, cat, ctx);
        minMax(v, n);
    } else if (key == "variety") {
        n.kind = CondKind::Variety;
        if (!v.is_object() || !v.contains("tag")) fail(ctx + ": 'variety' needs a tag");
        n.selector = compileSelector(json{{"tag", v["tag"]}}, cat, ctx);
        n.min = intField(v, "min", 1, ctx);
    } else if (key == "near") {
        n.kind = CondKind::Near;
        if (!v.is_object() || !v.contains("anchor") || !v.contains("has") || !v["has"].is_array())
            fail(ctx + ": 'near' needs an anchor and a has list");
        n.selector = compileSelector(v["anchor"], cat, ctx);
        n.within = intField(v, "within", 1, ctx);
        n.anchors = intField(v, "anchors", 1, ctx);
        if (n.within < 1 || n.within > kMaxWithin) fail(ctx + ": 'within' must be 1..4");
        if (n.anchors < 1) fail(ctx + ": 'anchors' must be at least 1");
        if (v["has"].empty() || v["has"].size() > static_cast<std::size_t>(kMaxHas))
            fail(ctx + ": 'has' needs 1 to 8 entries");
        std::vector<Has> entries;
        for (const auto& h : v["has"]) {
            if (!h.is_object()) fail(ctx + ": 'has' entries are selectors");
            json sel = h;
            sel.erase("min");
            sel.erase("max");
            CondNode mm;
            minMax(h, mm);
            entries.push_back({compileSelector(sel, cat, ctx), mm.min, mm.max});
        }
        n.first = static_cast<int>(has_.size());
        n.count = static_cast<int>(entries.size());
        has_.insert(has_.end(), entries.begin(), entries.end());
    } else if (key == "time") {
        n.kind = CondKind::Time;
        if (!v.is_array() || v.empty()) fail(ctx + ": 'time' takes a list of phases");
        for (const auto& p : v) {
            const auto it = std::ranges::find(kPhases, stringOf(p, ctx));
            if (it == kPhases.end()) fail(ctx + ": unknown phase '" + p.get<std::string>() + "'");
            n.mask |= static_cast<std::uint8_t>(1u << (it - kPhases.begin()));
        }
    } else if (key == "season") {
        n.kind = CondKind::Season;
        if (!v.is_array() || v.empty()) fail(ctx + ": 'season' takes a list of seasons");
        for (const auto& s : v) {
            const auto i = cat.findSeason(stringOf(s, ctx));
            if (!i) fail(ctx + ": unknown season '" + s.get<std::string>() + "'");
            n.mask |= static_cast<std::uint8_t>(1u << *i);
        }
    } else if (key == "weather") {
        n.kind = CondKind::Weather;
        const auto& w = stringOf(v, ctx);
        if (w != "rain" && w != "clear") fail(ctx + ": weather is 'rain' or 'clear'");
        n.mask = w == "rain" ? 1 : 0;
    } else if (key == "visitor") {
        n.kind = CondKind::Visitor;
        if (!v.is_object() || !v.contains("id")) fail(ctx + ": 'visitor' needs an id");
        const auto i = cat.findVisitor(stringOf(v["id"], ctx));
        if (!i) fail(ctx + ": unknown visitor '" + v["id"].get<std::string>() + "'");
        n.id = *i;
        n.min = intField(v, "min", 1, ctx);
    } else if (key == "seen") {
        n.kind = CondKind::Seen;
        const auto i = cat.findVisitor(stringOf(v, ctx));
        if (!i) fail(ctx + ": unknown visitor '" + v.get<std::string>() + "'");
        n.id = *i;
    } else if (key == "nook") {
        n.kind = CondKind::Nook;
        const auto& id = stringOf(v, ctx);
        const auto it = std::ranges::find(nookIds, id);
        if (it == nookIds.end()) fail(ctx + ": unknown nook '" + id + "'");
        n.id = static_cast<int>(it - nookIds.begin());
    } else if (key == "progress") {
        n.kind = CondKind::Progress;
        n.progress.fill(-1);
        if (!v.is_object() || v.empty()) fail(ctx + ": 'progress' takes counters");
        for (const auto& [k, x] : v.items()) {
            const auto it = std::ranges::find(kCounterNames, k);
            if (it == kCounterNames.end()) fail(ctx + ": unknown progress counter '" + k + "'");
            if (!x.is_number_integer() || x.get<int>() < 0)
                fail(ctx + ": progress '" + k + "' must be a whole number");
            n.progress[static_cast<std::size_t>(it - kCounterNames.begin())] = x.get<int>();
        }
    } else {
        fail(ctx + ": unknown condition '" + key + "'");
    }
    nodes_.push_back(n);
    return static_cast<int>(nodes_.size()) - 1;
}

int ConditionSet::countMatches(int sel, const World& world) const {
    const Selector& s = selector(sel);
    int total = 0;
    for (const int i : s.ids) {
        if (s.terrain)
            // Wild tiles always hold the base terrain and do not exist for conditions.
            total += world.terrainCount(i) - (i == base_ ? world.wildCount() : 0);
        else
            total += world.itemCount(i);
    }
    return total;
}

bool ConditionSet::anchorPasses(const CondNode& n, const World& world, TileRect fp,
                                const void* anchorItem) const {
    const TileRect area =
        TileRect{fp.x0 - n.within, fp.y0 - n.within, fp.x1 + n.within, fp.y1 + n.within}.clipped(
            world.bounds());
    std::array<int, kMaxHas> counts{};
    // Without upper bounds an anchor passes as soon as every minimum is met.
    bool bounded = false;
    int unmet = 0;
    for (int h = 0; h < n.count; ++h) {
        const Has& e = has_[static_cast<std::size_t>(n.first + h)];
        bounded = bounded || e.max >= 0;
        unmet += e.min > 0 ? 1 : 0;
    }
    // One pass over the area's tiles (at most 12 x 12): its terrain, and through occupancy the
    // items on it, each counted once, at the first of its tiles the scan meets.
    for (int y = area.y0; y < area.y1; ++y)
        for (int x = area.x0; x < area.x1; ++x) {
            const TilePos p{x, y};
            if (fp.contains(p) || !world.hasGround(p) || world.isWild(p)) continue;
            const auto t = static_cast<std::size_t>(world.terrainAt(p));
            const Item* it = world.itemAt(p);
            const bool first = it != nullptr && it != anchorItem &&
                               x == std::max(it->pos.x, area.x0) &&
                               y == std::max(it->pos.y, area.y0);
            for (int h = 0; h < n.count; ++h) {
                const Selector& sel =
                    selector(has_[static_cast<std::size_t>(n.first + h)].selector);
                if (sel.terrain ? sel.match[t] != 0 : first && sel.match[it->type] != 0) {
                    int& c = counts[static_cast<std::size_t>(h)];
                    if (++c == has_[static_cast<std::size_t>(n.first + h)].min) --unmet;
                }
            }
            if (!bounded && unmet == 0) return true;
        }
    for (int h = 0; h < n.count; ++h) {
        const Has& e = has_[static_cast<std::size_t>(n.first + h)];
        const int c = counts[static_cast<std::size_t>(h)];
        if (c < e.min || (e.max >= 0 && c > e.max)) return false;
    }
    return true;
}

int ConditionSet::nearPass(const CondNode& n, const World& world, int stopAt,
                           std::vector<NearInstance>* out) const {
    const Selector& a = selector(n.selector);
    int passed = 0;
    const auto pass = [&](TileRect fp) {
        ++passed;
        if (out != nullptr) out->push_back({fp, n.within});
        return stopAt > 0 && passed >= stopAt;
    };
    for (int cy = 0; cy < world.chunksY(); ++cy)
        for (int cx = 0; cx < world.chunksX(); ++cx) {
            // Chunk tallies skip every chunk without a candidate anchor.
            bool any = false;
            for (const int t : a.ids)
                any = any || (a.terrain ? world.chunkTerrainCount(cx, cy, t)
                                        : world.chunkItemCount(cx, cy, t)) > 0;
            if (!any) continue;
            if (!a.terrain) {
                for (const std::uint32_t i : world.chunkItems(cx, cy)) {
                    const Item& it = world.items()[i];
                    if (a.match[it.type] != 0 && anchorPasses(n, world, it.rect(), &it) &&
                        pass(it.rect()))
                        return passed;
                }
                continue;
            }
            const TileRect r =
                TileRect{cx * kChunk, cy * kChunk, (cx + 1) * kChunk, (cy + 1) * kChunk}.clipped(
                    world.bounds());
            for (int y = r.y0; y < r.y1; ++y)
                for (int x = r.x0; x < r.x1; ++x) {
                    const TilePos p{x, y};
                    if (world.terrainAt(p) == kNoGround || world.isWild(p) ||
                        a.match[static_cast<std::size_t>(world.terrainAt(p))] == 0)
                        continue;
                    const TileRect fp{x, y, x + 1, y + 1};
                    if (anchorPasses(n, world, fp, nullptr) && pass(fp)) return passed;
                }
        }
    return passed;
}

bool ConditionSet::eval(int i, const World& world, const CondFacts& f) const {
    const CondNode& n = node(i);
    const auto child = [&](int k) { return children_[static_cast<std::size_t>(n.first + k)]; };
    switch (n.kind) {
    case CondKind::All:
        for (int k = 0; k < n.count; ++k)
            if (!eval(child(k), world, f)) return false;
        return true;
    case CondKind::Any:
        for (int k = 0; k < n.count; ++k)
            if (eval(child(k), world, f)) return true;
        return false;
    case CondKind::Not: return !eval(child(0), world, f);
    case CondKind::Count: {
        const int c = countMatches(n.selector, world);
        return c >= n.min && (n.max < 0 || c <= n.max);
    }
    case CondKind::Variety: {
        int kinds = 0;
        for (const int id : selector(n.selector).ids) kinds += world.itemCount(id) > 0 ? 1 : 0;
        return kinds >= n.min;
    }
    case CondKind::Near: return nearPass(n, world, n.anchors, nullptr) >= n.anchors;
    case CondKind::Time: return f.waiting || hasBit(n.mask, static_cast<int>(f.phase));
    case CondKind::Season: return f.waiting || hasBit(n.mask, f.season);
    case CondKind::Weather: return f.waiting || (n.mask != 0) == f.raining;
    case CondKind::Visitor:
        return n.id >= 0 && std::cmp_less(n.id, f.present.size()) &&
               f.present[static_cast<std::size_t>(n.id)] >= n.min;
    case CondKind::Seen:
        return std::cmp_less(n.id, f.seen.size()) && f.seen[static_cast<std::size_t>(n.id)] != 0;
    case CondKind::Nook:
        return std::cmp_less(n.id, f.nookHere.size()) &&
               f.nookHere[static_cast<std::size_t>(n.id)] != 0;
    case CondKind::Progress:
        for (std::size_t k = 0; k < kCounters; ++k)
            if (n.progress[k] >= 0 && f.counters[k] < n.progress[k]) return false;
        return true;
    }
    return false;
}

void ConditionSet::instances(int nearNode, const World& world,
                             std::vector<NearInstance>& out) const {
    out.clear();
    (void)nearPass(node(nearNode), world, 0, &out);
}

int ConditionSet::nookNear(int root) const {
    const CondNode& n = node(root);
    if (n.kind == CondKind::Near) return root;
    if (n.kind != CondKind::All) return -1;
    int found = -1;
    for (int k = 0; k < n.count; ++k) {
        const int c = children_[static_cast<std::size_t>(n.first + k)];
        if (node(c).kind != CondKind::Near) continue;
        if (found >= 0) return -1;
        found = c;
    }
    return found;
}

std::optional<int> ConditionSet::firstWaiting(int i, const CondFacts& f) const {
    const CondNode& n = node(i);
    switch (n.kind) {
    case CondKind::Time:
        return hasBit(n.mask, static_cast<int>(f.phase)) ? std::nullopt : std::optional(i);
    case CondKind::Season: return hasBit(n.mask, f.season) ? std::nullopt : std::optional(i);
    case CondKind::Weather: return (n.mask != 0) == f.raining ? std::nullopt : std::optional(i);
    case CondKind::All:
    case CondKind::Any:
    case CondKind::Not:
        for (int k = 0; k < n.count; ++k)
            if (const auto w = firstWaiting(children_[static_cast<std::size_t>(n.first + k)], f))
                return w;
        return std::nullopt;
    default: return std::nullopt;
    }
}

std::optional<std::pair<int, int>> ConditionSet::countProgress(int i, const World& world) const {
    const CondNode& n = node(i);
    if (n.kind != CondKind::Count) return std::nullopt;
    return std::pair{countMatches(n.selector, world), n.min};
}

void ConditionSet::needed(int i, std::vector<int>& out) const {
    const CondNode& n = node(i);
    switch (n.kind) {
    case CondKind::All:
    case CondKind::Any:
        for (int k = 0; k < n.count; ++k)
            needed(children_[static_cast<std::size_t>(n.first + k)], out);
        break;
    case CondKind::Count:
        if (n.min > 0) out.push_back(n.selector);
        break;
    case CondKind::Variety: out.push_back(n.selector); break;
    case CondKind::Near:
        out.push_back(n.selector);
        for (int h = 0; h < n.count; ++h) {
            const Has& e = has_[static_cast<std::size_t>(n.first + h)];
            if (e.min > 0) out.push_back(e.selector);
        }
        break;
    default: break;
    }
}

} // namespace lc
