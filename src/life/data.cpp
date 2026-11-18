#include "life/data.hpp"

#include <algorithm>
#include <charconv>
#include <cmath>
#include <unordered_set>

namespace lc::life {

using nlohmann::json;
using world::Placed;

bool KindDef::has(int anim) const {
    return std::ranges::find(anims, static_cast<std::uint16_t>(anim)) != anims.end();
}

float KindDef::fpsOf(int anim) const {
    for (std::size_t i = 0; i < anims.size(); ++i)
        if (anims[i] == anim) return fps[i];
    return 4.0f;
}

float parseHour(std::string_view s) {
    const auto colon = s.find(':');
    if (colon == std::string_view::npos) return -1;
    int h = 0;
    int m = 0;
    const std::string text(s);
    const char* p = text.c_str();
    const auto a = std::from_chars(p, p + colon, h);
    const auto b = std::from_chars(p + colon + 1, p + text.size(), m);
    if (a.ec != std::errc{} || b.ec != std::errc{} || h < 0 || h > 24 || m < 0 || m > 59) return -1;
    return static_cast<float>(h) + static_cast<float>(m) / 60.0f;
}

std::uint64_t worldgenHash(std::string_view text) {
    std::uint64_t h = 0xCBF29CE484222325ULL;
    for (const char c : text) h = (h ^ static_cast<unsigned char>(c)) * 0x100000001B3ULL;
    h = (h ^ (h >> 30)) * 0xBF58476D1CE4E5B9ULL;
    h = (h ^ (h >> 27)) * 0x94D049BB133111EBULL;
    return h ^ (h >> 31);
}

// citylife.in_hours: [a, b) when a <= b, else wrapping; a == b holds no hour.
bool inHours(float from, float to, float h) {
    return from <= to ? (h >= from && h < to) : (h >= from || h < to);
}

namespace {

template <typename T>
int indexOf(const std::vector<T>& v, std::string_view id) {
    for (std::size_t i = 0; i < v.size(); ++i)
        if (v[i].id == id) return static_cast<int>(i);
    return kNoIndex;
}

int intern(std::vector<std::string>& names, std::string_view s) {
    const auto it = std::ranges::find(names, s);
    if (it != names.end()) return static_cast<int>(it - names.begin());
    names.emplace_back(s);
    return static_cast<int>(names.size() - 1);
}

std::string str(const json& o, const char* key) {
    const auto it = o.find(key);
    return it != o.end() && it->is_string() ? it->get<std::string>() : std::string{};
}

float num(const json& o, const char* key, float fallback) {
    const auto it = o.find(key);
    return it != o.end() && it->is_number() ? it->get<float>() : fallback;
}

// The one compile pass over all regions: shared tables plus the region being read.
class Compiler {
public:
    Compiler(const LoadedWorld& w, LifeData& out) : w_(w), map_(*w.map), d_(out) {}

    void kinds();
    void tiles();
    void region(const world::RegionFile& file, int worldRegion);

private:
    void problem(const std::string& what) { d_.problems.push_back(region_ + ": " + what); }
    int goods(const std::string& id, const std::string& where);
    int sound(const std::string& s) { return s.empty() ? kNoIndex : intern(d_.sounds, s); }
    int anim(const std::string& s) { return s.empty() ? kAnimIdle : intern(d_.animNames, s); }
    int node(const std::string& id, const std::string& where);
    int item(const std::string& id, const std::string& where);
    int slotName(const std::string& s, const std::string& where);
    int district(const std::string& id, const std::string& where);
    void filter(const json& o, Filter& f, const std::string& where);
    Target target(const json& t, const std::string& where);
    void dur(const json& s, Step& st);
    std::uint32_t block(const json& steps, bool loop, const std::string& where,
                        const std::vector<std::pair<std::string, int>>* routines);
    void step(const json& s, std::size_t at, const std::string& where,
              const std::vector<std::pair<std::string, int>>* routines);
    int role(const json& r, const std::string& id, int kind);
    int strollRole(const std::string& kind, const std::string& where);
    void districts(const world::RegionFile& file);
    void groups(const json& life);
    void chains(const json& life);
    void festivals(const json& life);
    void events(const json& life);
    void figures(const json& life);
    void tokens(const json& life, int lifeRegion);
    [[nodiscard]] std::string districtOf(const Placed& it) const;

    const LoadedWorld& w_;
    const WorldMap& map_;
    LifeData& d_;
    LifeRegion* r_ = nullptr;
    std::string region_;
    std::string layerName_;
    std::unordered_map<std::string, int> nodes_;
    // Per map district: tiles, and tiles per chunk.
    std::vector<int> districtTiles_;
    std::vector<std::vector<std::pair<std::uint32_t, int>>> districtChunks_;
};

void Compiler::kinds() {
    d_.animNames = {"idle", "move"};
    for (const world::SetCatalog& sc : map_.content().sets())
        for (const world::SetActor& a : sc.actors) {
            KindDef k;
            k.id = a.id;
            k.name = a.name;
            k.sprite = a.sprite;
            k.variants = std::max(1, a.variants);
            for (std::size_t i = 0; i < a.anims.size(); ++i) {
                k.anims.push_back(
                    static_cast<std::uint16_t>(intern(d_.animNames, a.anims[i].first)));
                k.fps.push_back(a.anims[i].second);
                k.strides.push_back(i < a.strides.size() ? a.strides[i] : 0.0f);
            }
            k.cart =
                a.id.find("cart") != std::string::npos || a.id.find("sledge") != std::string::npos;
            d_.kindIndex.emplace(k.id, static_cast<int>(d_.kinds.size()));
            d_.kinds.push_back(std::move(k));
        }
    for (const world::SetCatalog& sc : map_.content().sets())
        for (const world::SetGoods& g : sc.goods) intern(d_.goods, g.id);
    for (const SeasonDef& s : map_.content().home().seasons) d_.seasons.push_back(s.id);
    if (!map_.content().home().seasons.empty())
        d_.seasonDays = map_.content().home().seasons.front().days;
}

void Compiler::tiles() {
    districtTiles_.assign(map_.districtCount(), 0);
    districtChunks_.assign(map_.districtCount(), {});
    for (int cy = 0; cy < map_.chunksY(); ++cy)
        for (int cx = 0; cx < map_.chunksX(); ++cx) {
            std::array<int, 256> count{};
            for (int y = cy * kChunk; y < std::min((cy + 1) * kChunk, map_.height()); ++y)
                for (int x = cx * kChunk; x < std::min((cx + 1) * kChunk, map_.width()); ++x) {
                    const int dist = map_.districtAt({x, y});
                    if (dist != world::kNone) ++count[static_cast<std::size_t>(dist)];
                }
            const auto chunk = static_cast<std::uint32_t>(cy * map_.chunksX() + cx);
            for (std::size_t dd = 0; dd < map_.districtCount(); ++dd)
                if (count[dd] > 0) {
                    districtTiles_[dd] += count[dd];
                    districtChunks_[dd].emplace_back(chunk, count[dd]);
                }
        }
}

int Compiler::goods(const std::string& id, const std::string& where) {
    if (id.empty()) return kNoIndex;
    const auto it = std::ranges::find(d_.goods, id);
    if (it != d_.goods.end()) return static_cast<int>(it - d_.goods.begin());
    problem(where + ": goods '" + id + "' are in no set catalog (drawn as its stand-in, if any)");
    return intern(d_.goods, id);
}

int Compiler::node(const std::string& id, const std::string& where) {
    auto it = nodes_.find(id);
    if (it == nodes_.end() && id.starts_with(layerName_ + ":"))
        it = nodes_.find(id.substr(layerName_.size() + 1));
    if (it != nodes_.end()) return it->second;
    problem(where + ": node '" + id + "' is not in the " + layerName_ + " graph");
    return kNoIndex;
}

int Compiler::item(const std::string& id, const std::string& where) {
    const int i = map_.content().findItem(id);
    if (i < 0) problem(where + ": item '" + id + "' is in no catalog");
    return i;
}

int Compiler::slotName(const std::string& s, const std::string& where) {
    const auto& names = map_.slotNames();
    const auto it = std::ranges::find(names, s);
    if (it != names.end()) return static_cast<int>(it - names.begin());
    problem(where + ": slot '" + s + "' is on no placed item");
    return kNoIndex;
}

int Compiler::district(const std::string& id, const std::string& where) {
    const int dd = map_.findDistrict(region_ + "/" + id);
    if (dd < 0) problem(where + ": district '" + id + "' is not on the map");
    return dd;
}

void Compiler::filter(const json& o, Filter& f, const std::string& where) {
    if (const auto h = o.find("hours"); h != o.end() && h->is_array() && h->size() == 2) {
        f.from = parseHour((*h)[0].get<std::string>());
        f.to = parseHour((*h)[1].get<std::string>());
        f.hours = f.from >= 0 && f.to >= 0;
        if (!f.hours) problem(where + ": hours are not hh:mm");
    }
    if (const auto dd = o.find("days"); dd != o.end() && dd->is_object()) {
        f.every = static_cast<std::uint8_t>(std::clamp(dd->value("every", 1), 1, 255));
        f.offset = static_cast<std::uint8_t>(dd->value("offset", 0) % f.every);
    }
    if (const auto s = o.find("season"); s != o.end()) {
        const auto add = [&](const std::string& name) {
            const auto it = std::ranges::find(d_.seasons, name);
            if (it == d_.seasons.end())
                problem(where + ": season '" + name + "' is not a season");
            else
                f.seasons |= static_cast<std::uint8_t>(1u << (it - d_.seasons.begin()));
        };
        if (s->is_string()) add(s->get<std::string>());
        if (s->is_array())
            for (const json& v : *s) add(v.get<std::string>());
    }
    if (const std::string fest = str(o, "festival"); !fest.empty()) {
        f.festival = r_->findFestival(fest);
        if (f.festival < 0) problem(where + ": festival '" + fest + "' is not in the calendar");
    }
    if (const std::string fest = str(o, "not_festival"); !fest.empty())
        f.notFestival = r_->findFestival(fest);
    if (const std::string wx = str(o, "weather"); !wx.empty()) f.weather = wx == "clear" ? 0 : 1;
}

Target Compiler::target(const json& t, const std::string& where) {
    Target out;
    if (!t.is_object()) return out;
    out.within = num(t, "within", 0);
    if (t.value("here", false)) {
        out.kind = TargetKind::Here;
    } else if (t.value("each", false)) {
        out.kind = TargetKind::Each;
    } else if (t.contains("node") && str(t, "node") == "next") {
        out.kind = TargetKind::None; // "the next route node": events walk their routes themselves
    } else if (t.contains("node")) {
        out.kind = TargetKind::Node;
        out.node = node(str(t, "node"), where);
        if (out.node < 0) out.kind = TargetKind::None;
    } else if (t.contains("home")) {
        out.kind = TargetKind::Home;
        out.beside = str(t, "home") == "beside";
        if (!out.beside) out.slot = slotName(str(t, "home"), where);
    } else if (t.contains("slot_kind")) {
        out.kind = TargetKind::SlotKind;
        const auto& kinds = map_.slotKinds();
        const auto it = std::ranges::find(kinds, str(t, "slot_kind"));
        out.slotKind = it == kinds.end() ? kNoIndex : static_cast<int>(it - kinds.begin());
        if (out.slotKind < 0) {
            problem(where + ": no placed item has a slot of kind '" + str(t, "slot_kind") + "'");
            out.kind = TargetKind::None;
        }
    } else if (t.contains("item")) {
        out.kind = TargetKind::Item;
        out.item = item(str(t, "item"), where);
        if (t.contains("slot") && str(t, "slot") != "beside")
            out.slot = slotName(str(t, "slot"), where);
        if (out.item < 0) out.kind = TargetKind::None;
    } else {
        problem(where + ": a target names no place");
    }
    return out;
}

void Compiler::dur(const json& s, Step& st) {
    const auto it = s.find("dur");
    if (it == s.end()) return;
    if (it->is_array() && it->size() == 2) {
        st.dur0 = (*it)[0].get<float>();
        st.dur1 = (*it)[1].get<float>();
    } else if (it->is_number()) {
        st.dur0 = st.dur1 = it->get<float>();
    }
}

std::uint32_t Compiler::block(const json& steps, bool loop, const std::string& where,
                              const std::vector<std::pair<std::string, int>>* routines) {
    const auto b = static_cast<std::uint32_t>(d_.blocks.size());
    d_.blocks.push_back({});
    const auto first = static_cast<std::uint32_t>(d_.steps.size());
    const std::size_t n = steps.is_array() ? steps.size() : 0;
    d_.steps.resize(first + n);
    d_.blocks[b] = {first, static_cast<std::uint32_t>(n), loop};
    for (std::size_t i = 0; i < n; ++i)
        step(steps[i], first + i, where + " step " + std::to_string(i), routines);
    return b;
}

void Compiler::step(const json& s, std::size_t at, const std::string& where,
                    const std::vector<std::pair<std::string, int>>* routines) {
    Step st;
    dur(s, st);
    if (const auto u = s.find("until"); u != s.end() && u->is_object()) {
        if (u->contains("hour")) {
            st.until = Until::Hour;
            st.untilHour = parseHour(str(*u, "hour"));
        } else if (u->contains("weather")) {
            st.until = str(*u, "weather") == "clear" ? Until::Clear : Until::Rain;
        }
    }
    st.anim = static_cast<std::uint16_t>(anim(str(s, "anim")));
    if (const std::string e = str(s, "effect"); e == "open_shutters")
        st.effect = Effect::OpenShutters;
    else if (e == "unload")
        st.effect = Effect::Unload;
    if (const std::string state = str(s, "state"); state == "lit")
        st.state = ItemState::Lit;
    else if (state == "open")
        st.state = ItemState::Open;
    else if (state == "firing")
        st.state = ItemState::Firing;
    if (s.contains("go")) {
        st.verb = Verb::Go;
        st.target = target(s["go"], where);
    } else if (s.contains("use")) {
        st.verb = Verb::Use;
        st.target = target(s["use"], where);
    } else if (s.contains("take")) {
        st.verb = Verb::Take;
        st.goods = goods(str(s, "take"), where);
    } else if (s.contains("put")) {
        st.verb = Verb::Put;
        st.goods = goods(str(s, "put"), where);
    } else if (s.contains("wander")) {
        st.verb = Verb::Wander;
        const json& wd = s["wander"];
        st.radius = num(wd, "radius", 4);
        if (wd.contains("zone")) st.zone = district(str(wd, "zone"), where);
    } else if (s.contains("wait")) {
        st.verb = Verb::Wait;
        if (s["wait"].is_object()) dur(s["wait"], st);
    } else if (s.contains("enter")) {
        st.verb = Verb::Enter;
        st.target = target(s["enter"], where);
    } else if (s.contains("follow")) {
        st.verb = Verb::Follow;
        const std::string kind = str(s["follow"], "actor");
        st.follow = d_.findKind(kind);
        if (st.follow < 0) problem(where + ": follows '" + kind + "', which is no actor kind");
        st.spacing = num(s, "spacing", 1.0f);
    } else if (s.contains("emit")) {
        st.verb = Verb::Emit;
        const json& e = s["emit"];
        st.fx = e.contains("fx") && !e.contains("sfx");
        st.sound = sound(st.fx ? str(e, "fx") : str(e, "sfx"));
    } else if (s.contains("pick")) {
        st.verb = Verb::Pick;
        const json& opts = s["pick"];
        std::vector<std::pair<std::uint32_t, float>> made; // block, weight
        for (std::size_t k = 0; k < opts.size(); ++k) {
            const json& o = opts[k];
            const std::string w = where + " option " + std::to_string(k);
            std::uint32_t b = 0;
            if (o.contains("steps")) {
                b = block(o["steps"], false, w, routines);
            } else if (o.contains("routine") && routines != nullptr) {
                const auto r = std::ranges::find(*routines, str(o, "routine"),
                                                 &std::pair<std::string, int>::first);
                if (r == routines->end()) {
                    problem(w + ": routine '" + str(o, "routine") + "' is not defined");
                    continue;
                }
                // A routine named as an option runs as a nested routine step.
                Step call;
                call.verb = Verb::Routine;
                call.first = static_cast<std::uint32_t>(r->second);
                call.count = 1;
                b = static_cast<std::uint32_t>(d_.blocks.size());
                d_.blocks.push_back({static_cast<std::uint32_t>(d_.steps.size()), 1, false, 1});
                d_.steps.push_back(call);
            } else {
                json one = json::array();
                one.push_back(o);
                b = block(one, false, w, routines);
            }
            made.emplace_back(b, num(o, "weight", 1.0f));
        }
        // The options are consecutive blocks: copies of the ones just made, with their weights.
        st.first = static_cast<std::uint32_t>(d_.blocks.size());
        st.count = static_cast<std::uint32_t>(made.size());
        for (const auto& [b, weight] : made) {
            Block copy = d_.blocks[b];
            copy.weight = weight;
            d_.blocks.push_back(copy);
        }
    } else if (s.contains("each")) {
        st.verb = Verb::Each;
        const json& e = s["each"];
        st.eachItem = item(str(e, "item"), where);
        st.eachMax = e.value("max", 3);
        st.first =
            block(s.contains("do") ? s["do"] : json::array(), false, where + " each", routines);
        st.count = 1;
    } else if (s.contains("routine") && routines != nullptr) {
        st.verb = Verb::Routine;
        const auto r =
            std::ranges::find(*routines, str(s, "routine"), &std::pair<std::string, int>::first);
        if (r == routines->end()) {
            problem(where + ": routine '" + str(s, "routine") + "' is not defined");
            st.verb = Verb::Wait;
        } else {
            st.first = static_cast<std::uint32_t>(r->second);
            st.count = 1;
        }
    } else if (s.contains("say")) {
        st.verb = Verb::Wait; // speech belongs to the resident; a city actor pauses
    } else {
        problem(where + ": a step with no verb this engine knows");
    }
    d_.steps[at] = st;
}

int Compiler::role(const json& r, const std::string& id, int kind) {
    Role role;
    role.id = id;
    role.name = str(r, "name");
    role.kind = kind;
    role.card = str(r, "card");
    const std::string where = "role " + id;
    if (const auto h = r.find("home"); h != r.end() && h->is_object()) {
        role.homeItem = item(str(*h, "item"), where);
        if (str(*h, "slot") != "beside") role.homeSlot = slotName(str(*h, "slot"), where);
    }
    if (const auto loc = r.find("locomotion"); loc != r.end()) {
        role.speedExact = loc->value("speed", 0.0);
        role.speed = static_cast<float>(role.speedExact);
    }
    // Blocks for every routine first, so `routine` and pick options can name any of them.
    const json routines = r.value("routines", json::object());
    for (auto it = routines.begin(); it != routines.end(); ++it) {
        role.routines.emplace_back(it.key(), static_cast<int>(d_.blocks.size()));
        d_.blocks.push_back({});
    }
    for (std::size_t k = 0; k < role.routines.size(); ++k) {
        const json& rt = routines[role.routines[k].first];
        const std::uint32_t b = block(rt.value("steps", json::array()), rt.value("loop", false),
                                      where + " routine " + role.routines[k].first, &role.routines);
        d_.blocks[static_cast<std::size_t>(role.routines[k].second)] = d_.blocks[b];
    }
    const auto routineOf = [&](const std::string& name) {
        const auto it = std::ranges::find(role.routines, name, &std::pair<std::string, int>::first);
        if (it == role.routines.end()) {
            problem(where + ": routine '" + name + "' is not defined");
            return kNoIndex;
        }
        return it->second;
    };
    for (const json& b : r.value("schedule", json::array())) {
        ScheduleBlock sb;
        filter(b, sb.when, where + " schedule");
        sb.routine = routineOf(str(b, "routine"));
        if (sb.routine >= 0) role.schedule.push_back(sb);
    }
    for (const json& in : r.value("interrupts", json::array()))
        if (in.value("when", json::object()).value("weather", "") == "rain")
            role.rainRoutine = routineOf(str(in, "routine"));
    r_->roles.push_back(std::move(role));
    return static_cast<int>(r_->roles.size() - 1);
}

// A population of a kind with no role (the stretches' and towns' travellers, shepherds, boats):
// it strolls node to node on the region's graph and lingers, all day, as worldgen's core life
// describes it. One synthesised role per region and kind.
int Compiler::strollRole(const std::string& kind, const std::string& where) {
    const std::string id = "kind:" + kind;
    if (const int found = r_->findRole(id); found >= 0) return found;
    const int k = d_.findKind(kind);
    if (k < 0) {
        problem(where + ": population of '" + kind + "', which is no role or actor kind");
        return kNoIndex;
    }
    Role role;
    role.id = id;
    role.name = d_.kinds[static_cast<std::size_t>(k)].name;
    role.kind = k;
    // What kind of thing it is decides how it spends the day: herds graze and drift together,
    // birds linger and wander, people walk the roads from place to place.
    const auto is = [&](std::initializer_list<const char*> words) {
        return std::ranges::any_of(
            words, [&](const char* w) { return kind.find(w) != std::string::npos; });
    };
    const bool herd = is({"sheep", "goat", "cattle", "cow", "flock"});
    const bool bird =
        is({"gull", "eagle", "stork", "pigeon", "swift", "crane", "heron", "ibis", "bird"});
    const auto first = static_cast<std::uint32_t>(d_.steps.size());
    Step go;
    go.verb = Verb::Go;
    go.target.kind = herd ? TargetKind::Flock : TargetKind::Roam;
    go.target.within = 24;
    Step linger;
    linger.verb = Verb::Wander;
    linger.radius = herd ? 3.0f : bird ? 6.0f : 3.0f;
    linger.dur0 = herd ? 40.0f : bird ? 20.0f : 10.0f;
    linger.dur1 = herd ? 90.0f : bird ? 40.0f : 30.0f;
    role.routines.emplace_back("stroll", static_cast<int>(d_.blocks.size()));
    if (bird) {
        d_.steps.push_back(linger);
        d_.blocks.push_back({first, 1, true, 1});
    } else {
        d_.steps.push_back(go);
        d_.steps.push_back(linger);
        d_.blocks.push_back({first, 2, true, 1});
    }
    role.schedule.push_back({Filter{}, role.routines.back().second});
    r_->roles.push_back(std::move(role));
    return static_cast<int>(r_->roles.size() - 1);
}

std::string Compiler::districtOf(const Placed& it) const {
    // citylife._district_at: the origin tile (plan top-left), then the ring, in plan order.
    const int cols = map_.height();
    const auto plan = [&](TilePos g) { return TilePos{cols - 1 - g.y, g.x}; };
    const auto grid = [&](TilePos p) { return TilePos{p.y, cols - 1 - p.x}; };
    const TilePos o = plan({it.x, it.y + it.h - 1});
    const int pw = it.h;
    const int ph = it.w;
    std::vector<TilePos> order{grid(o)};
    for (int c = o.x - 1; c < o.x + pw + 1; ++c) {
        order.push_back(grid({c, o.y - 1}));
        order.push_back(grid({c, o.y + ph}));
    }
    for (int r = o.y; r < o.y + ph; ++r) {
        order.push_back(grid({o.x - 1, r}));
        order.push_back(grid({o.x + pw, r}));
    }
    for (const TilePos t : order) {
        if (!map_.inBounds(t)) continue;
        const int dd = map_.districtAt(t);
        if (dd == world::kNone) continue;
        const std::string& name = map_.districtName(dd);
        if (name.starts_with(region_ + "/")) return name.substr(region_.size() + 1);
    }
    return {};
}

void Compiler::districts(const world::RegionFile& file) {
    for (const world::RegionDistrict& rd : file.districts) {
        District dist;
        dist.id = rd.id;
        const std::string where = "district " + rd.id;
        dist.map = district(rd.id, where);
        static constexpr std::array<std::pair<const char*, Area>, 6> kAreas{
            {{"centre", Area::Centre},
             {"town", Area::Town},
             {"country", Area::Country},
             {"road", Area::Road},
             {"sea", Area::Sea},
             {"wild", Area::Wild}}};
        for (const auto& [name, v] : kAreas)
            if (rd.area == name) dist.area = v;
        if (dist.map >= 0) {
            dist.tiles = districtTiles_[static_cast<std::size_t>(dist.map)];
            dist.chunks = districtChunks_[static_cast<std::size_t>(dist.map)];
        }
        if (const auto& j = rd.populations; j.is_array()) {
            for (const json& p : j) {
                Population pop;
                const std::string name = p.contains("role") ? str(p, "role") : str(p, "actor");
                pop.role = p.contains("role") ? r_->findRole(name) : strollRole(name, where);
                if (pop.role < 0) {
                    problem(where + ": population of '" + name + "', which is no role");
                    continue;
                }
                const std::string dens = p.value("density", std::string("always"));
                const auto di = std::ranges::find(r_->densityNames, dens);
                if (di == r_->densityNames.end()) {
                    if (dens != "always")
                        problem(where + ": density '" + dens + "' is not defined");
                    pop.density = -1;
                } else {
                    pop.density = static_cast<int>(di - r_->densityNames.begin());
                }
                pop.maxPerChunk = num(p, "max_per_chunk", 0);
                pop.count = num(p, "count", 1);
                if (p.contains("per_item")) pop.perItem = item(str(p, "per_item"), where);
                filter(p.value("when", json::object()), pop.when, where);
                dist.populations.push_back(pop);
            }
        }
        r_->districts.push_back(std::move(dist));
    }
    // Instances for per-item populations: placed in this region's layer, in this district by
    // citylife's rule.
    const auto& layers = map_.layers();
    const auto layerIt = std::ranges::find(layers, layerName_);
    const int layerIndex =
        layerIt == layers.end() ? -1 : static_cast<int>(layerIt - layers.begin());
    std::unordered_map<int, std::vector<std::uint32_t>> byItem;
    for (District& dist : r_->districts)
        for (const Population& p : dist.populations)
            if (p.perItem >= 0) byItem[p.perItem];
    if (!byItem.empty())
        for (std::uint32_t i = 0; i < map_.items().size(); ++i) {
            const Placed& it = map_.items()[i];
            if (static_cast<int>(it.layer) != layerIndex) continue;
            const auto found = byItem.find(static_cast<int>(it.info));
            if (found != byItem.end()) found->second.push_back(i);
        }
    for (District& dist : r_->districts) {
        dist.instances.resize(dist.populations.size());
        for (std::size_t k = 0; k < dist.populations.size(); ++k) {
            const Population& p = dist.populations[k];
            if (p.perItem < 0) continue;
            for (const std::uint32_t i : byItem[p.perItem])
                if (districtOf(map_.items()[i]) == dist.id) dist.instances[k].push_back(i);
        }
    }
}

void Compiler::groups(const json& life) {
    for (const json& g : life.value("groups", json::array())) {
        Group gr;
        gr.id = str(g, "id");
        const std::string where = "group " + gr.id;
        if (g.contains("leader")) gr.leader = d_.findKind(str(g["leader"], "actor"));
        for (const json& m : g.value("members", json::array())) {
            GroupMember gm;
            if (m.contains("role")) {
                const int ro = r_->findRole(str(m, "role"));
                gm.kind = ro < 0 ? kNoIndex : r_->roles[static_cast<std::size_t>(ro)].kind;
            } else {
                gm.kind = d_.findKind(str(m, "actor"));
            }
            if (gm.kind < 0) {
                problem(where + ": member '" +
                        (m.contains("role") ? str(m, "role") : str(m, "actor")) +
                        "' is no actor kind or role");
                continue;
            }
            gm.count = m.value("count", 1);
            gm.carry = m.contains("carry") ? goods(str(m, "carry"), where) : kNoIndex;
            gr.members.push_back(gm);
        }
        if (gr.leader < 0 && !gr.members.empty()) gr.leader = gr.members.front().kind;
        const json f = g.value("formation", json());
        const std::string kind = f.is_string()   ? f.get<std::string>()
                                 : f.is_object() ? str(f, "kind")
                                                 : std::string("line");
        gr.formation = kind == "pairs"     ? Formation::Pairs
                       : kind == "cluster" ? Formation::Cluster
                                           : Formation::Line;
        if (f.is_object())
            gr.spacing =
                gr.formation == Formation::Cluster ? num(f, "radius", 2) : num(f, "spacing", 0.9f);
        else if (gr.formation == Formation::Cluster)
            gr.spacing = 2;
        r_->groups.push_back(std::move(gr));
    }
}

void Compiler::festivals(const json& life) {
    for (const json& f : life.value("festivals", json::array())) {
        Festival fe;
        fe.id = str(f, "id");
        Filter tmp;
        json season = json::object();
        if (f.contains("season")) season["season"] = f["season"];
        filter(season, tmp, "festival " + fe.id);
        fe.seasons = tmp.seasons;
        fe.day = f.value("day", 0);
        if (const auto h = f.find("hours"); h != f.end() && h->is_array() && h->size() == 2) {
            fe.from = parseHour((*h)[0].get<std::string>());
            fe.to = parseHour((*h)[1].get<std::string>());
        }
        r_->festivals.push_back(std::move(fe));
    }
}

void Compiler::chains(const json& life) {
    for (const json& c : life.value("chains", json::array())) {
        Chain ch;
        ch.id = str(c, "id");
        ch.name = str(c, "name");
        ch.period = c.value("period", 120.0);
        const std::string where = "chain " + ch.id;
        if (const auto h = c.find("hours"); h != c.end() && h->is_array() && h->size() == 2) {
            ch.from = parseHour((*h)[0].get<std::string>());
            ch.to = parseHour((*h)[1].get<std::string>());
        }
        Filter tmp;
        filter(c, tmp, where);
        ch.seasons = tmp.seasons;
        for (const json& s : c.value("stages", json::array())) {
            ChainStage st;
            st.by = str(s, "by");
            st.role = r_->findRole(st.by);
            st.near = str(s, "near");
            st.label = str(s, "label");
            st.units = s.value("units", 1);
            st.workers = s.value("workers", 1);
            st.dur = s.value("dur", -1.0);
            if (s.contains("carry")) {
                st.kind = ChainStage::Kind::Carry;
                st.goods = goods(str(s, "carry"), where);
                st.from = str(s, "from");
                st.to = str(s, "to");
            } else {
                st.slot = str(s, "slot");
                st.out = s.contains("out") ? str(s, "out") : st.slot;
                if (s.contains("sink")) {
                    st.kind = ChainStage::Kind::Sink;
                    st.goods = goods(str(s, "sink"), where);
                } else if (s.contains("needs")) {
                    st.kind = ChainStage::Kind::Transform;
                    st.needs = goods(str(s, "needs"), where);
                    st.goods = goods(str(s, "makes"), where);
                } else {
                    st.kind = ChainStage::Kind::Source;
                    st.goods = goods(str(s, "makes"), where);
                }
            }
            ch.stages.push_back(std::move(st));
        }
        r_->chains.push_back(std::move(ch));
    }
    // Chains bound to an event are resolved after the events are read.
}

void Compiler::events(const json& life) {
    const json list = life.value("events", json::array());
    for (const json& e : list) {
        Event ev;
        ev.id = str(e, "id");
        r_->events.push_back(ev);
    }
    for (std::size_t i = 0; i < list.size(); ++i) {
        const json& e = list[i];
        Event& ev = r_->events[i];
        const std::string where = "event " + ev.id;
        const json t = e.value("trigger", json::object());
        const std::string on = str(t, "on");
        ev.trigger = on == "calendar"        ? Trigger::Calendar
                     : on == "after"         ? Trigger::After
                     : on == "token_arrived" ? Trigger::TokenArrived
                     : on == "chain"         ? Trigger::Chain
                     : on == "weather"       ? Trigger::Weather
                     : on == "reactive"      ? Trigger::Reactive
                                             : Trigger::Window;
        filter(t, ev.when, where);
        ev.chance = num(t, "chance", 1);
        ev.every = t.value("every", 0.0);
        ev.festival = ev.when.festival;
        if (ev.trigger == Trigger::After) ev.after = r_->findEvent(str(t, "event"));
        if (ev.trigger == Trigger::TokenArrived) ev.tokenKind = d_.findKind(str(t, "actor"));
        if (ev.trigger == Trigger::Chain) {
            ev.chain = r_->findChain(str(t, "chain"));
            ev.chainStage = t.value("stage", -1);
        }
        if (ev.trigger == Trigger::Weather) ev.weather = str(t, "kind");
        if (ev.trigger == Trigger::Reactive) {
            const json nr = t.value("when", json::object()).value("near", json::object());
            ev.reactKind = d_.findKind(str(nr, "actor"));
            ev.reactItem = map_.content().findItem(str(nr, "item"));
            ev.reactWithin = num(nr, "within", 2);
            if (nr.contains("goods")) ev.reactGoods = goods(str(nr, "goods"), where);
        }
        if (const auto dd = e.find("duration");
            dd != e.end() && dd->is_array() && dd->size() == 2) {
            ev.dur0 = (*dd)[0].get<float>();
            ev.dur1 = (*dd)[1].get<float>();
        }
        const std::string size = str(e, "size");
        ev.size = size == "large"    ? EventSize::Large
                  : size == "medium" ? EventSize::Medium
                                     : EventSize::Small;
        ev.rarity = str(e, "rarity");
        ev.card = str(e, "card");
        ev.glow = e.value("glow", false);
        for (const json& c : e.value("cast", json::array())) {
            CastEntry ce;
            ce.count = c.value("count", 1);
            if (c.contains("group")) {
                ce.group = r_->findGroup(str(c, "group"));
                if (ce.group < 0) problem(where + ": cast group '" + str(c, "group") + "' unknown");
            } else if (c.contains("role")) {
                ce.role = r_->findRole(str(c, "role"));
                if (ce.role < 0) problem(where + ": cast role '" + str(c, "role") + "' unknown");
            } else if (c.contains("actor")) {
                ce.kind = d_.findKind(str(c, "actor"));
                if (ce.kind < 0) problem(where + ": cast actor '" + str(c, "actor") + "' unknown");
            } else if (c.contains("rotate")) {
                for (const json& g : c["rotate"]) {
                    const int gi = r_->findGroup(g.get<std::string>());
                    if (gi >= 0) ce.rotate.push_back(gi);
                }
                ce.spacing = num(c, "spacing_s", 40);
            }
            ev.cast.push_back(std::move(ce));
        }
        for (const json& n : e.value("route", json::array())) {
            const int nd = node(n.get<std::string>(), where + " route");
            if (nd >= 0) ev.route.push_back(nd);
        }
        if (e.contains("zone")) {
            const int z = district(str(e, "zone"), where);
            if (z >= 0) ev.zones.push_back(z);
        }
        for (const json& z : e.value("zones", json::array())) {
            const int zz = district(z.get<std::string>(), where);
            if (zz >= 0) ev.zones.push_back(zz);
        }
        if (const std::string sfx = str(e, "sfx"); !sfx.empty()) ev.sfx = sound(sfx);
        if (const auto amb = e.find("ambience"); amb != e.end() && amb->is_object()) {
            ev.ambience = sound(str(*amb, "file"));
            ev.ambienceGain = num(*amb, "gain", 1);
        }
        ev.steps = block(e.value("steps", json::array()), false, where, nullptr);
    }
}

void Compiler::figures(const json& life) {
    for (const json& f : life.value("figures", json::array())) {
        Figure fg;
        fg.actor = str(f, "actor");
        fg.kind = fg.actor.empty() ? kNoIndex : d_.findKind(fg.actor);
        const std::string p = str(f, "presence");
        static constexpr std::array<std::pair<const char*, FigurePresence>, 9> kNames{{
            {"present", FigurePresence::Present},
            {"memory", FigurePresence::Memory},
            {"visitor", FigurePresence::Visitor},
            {"reenactor", FigurePresence::Reenactor},
            {"tale", FigurePresence::Tale},
            {"apparition", FigurePresence::Apparition},
            {"relief", FigurePresence::Relief},
            {"shrine", FigurePresence::Shrine},
            {"statue", FigurePresence::Statue},
        }};
        for (const auto& [name, v] : kNames)
            if (p == name) fg.presence = v;
        fg.translucent = f.value("translucent", false) || fg.presence == FigurePresence::Memory;
        fg.imagined = f.value("imagined", false);
        fg.card = str(f, "card");
        if (f.contains("district"))
            fg.district = district(str(f, "district"), "figure " + fg.actor);
        if (f.contains("schedule") && f.contains("routines")) {
            if (fg.kind < 0)
                problem("figure '" + fg.actor + "' has a day but is no actor kind");
            else
                fg.role = role(f, "figure:" + fg.actor, fg.kind);
        }
        r_->figures.push_back(std::move(fg));
    }
}

void Compiler::tokens(const json& life, int lifeRegion) {
    for (const json& t : life.value("lanes_tokens", json::array())) {
        Token tk;
        tk.kind = d_.findKind(str(t, "actor"));
        if (tk.kind < 0) {
            problem("token '" + str(t, "actor") + "' is no actor kind");
            continue;
        }
        tk.region = lifeRegion;
        tk.count = t.value("count", 1);
        tk.lane = str(t, "lane");
        if (const auto rt = t.find("route"); rt != t.end() && rt->is_object()) {
            tk.from = str(*rt, "start");
            tk.to = str(*rt, "end");
        }
        if (t.contains("group")) tk.group = r_->findGroup(str(t, "group"));
        if (t.contains("carry")) tk.carry = goods(str(t, "carry"), "token");
        tk.variant = t.value("variant", -1);
        d_.tokens.push_back(std::move(tk));
    }
}

void Compiler::region(const world::RegionFile& file, int worldRegion) {
    const json& life = file.life;
    const bool hasLife =
        !file.districts.empty() ||
        (life.is_object() && (life.contains("roles") || life.contains("lanes_tokens")));
    if (!hasLife) return;
    d_.regions.push_back({});
    r_ = &d_.regions.back();
    r_->id = file.id;
    r_->worldRegion = worldRegion;
    region_ = file.id;
    // The region's layer: the one named like the region (cities and towns), else none.
    nodes_.clear();
    // The region's layer: the one named like it (cities and towns), else the base (stretches).
    layerName_ = file.id;
    if (std::ranges::find(w_.graphs, file.id, &world::GraphFile::layer) == w_.graphs.end())
        layerName_ = "base";
    for (std::size_t g = 0; g < w_.graphs.size(); ++g)
        if (w_.graphs[g].layer == layerName_) {
            r_->layer = static_cast<int>(g);
            for (std::size_t n = 0; n < w_.graphs[g].nodes.size(); ++n)
                nodes_.emplace(w_.graphs[g].nodes[n].id, static_cast<int>(n));
        }
    if (life.is_object() && life.contains("season") && life["season"].is_string()) {
        const auto it = std::ranges::find(d_.seasons, life["season"].get<std::string>());
        if (it != d_.seasons.end()) r_->season = static_cast<int>(it - d_.seasons.begin());
    }
    for (const auto& [name, curve] : file.densities) {
        r_->densityNames.push_back(name);
        r_->densities.push_back(curve);
    }
    if (life.is_object()) {
        festivals(life);
        for (const json& r : life.value("roles", json::array())) {
            const std::string kind = str(r, "actor");
            const int k = d_.findKind(kind);
            if (k < 0) problem("role " + str(r, "id") + ": actor '" + kind + "' is no actor kind");
            role(r, str(r, "id"), k);
        }
        groups(life);
    }
    districts(file);
    if (life.is_object()) {
        chains(life);
        events(life);
        for (std::size_t c = 0; c < r_->chains.size(); ++c) {
            const json& cj = life["chains"][c];
            if (cj.contains("event")) r_->chains[c].event = r_->findEvent(str(cj, "event"));
        }
        figures(life);
        tokens(life, static_cast<int>(d_.regions.size() - 1));
        // Pending goods: stand-ins drawn until the set catalogs have them (kept for the report).
        if (const auto p = life.find("pending"); p != life.end() && p->contains("goods"))
            for (auto it = (*p)["goods"].begin(); it != (*p)["goods"].end(); ++it)
                intern(d_.goods, it.key());
    }
}

} // namespace

int LifeRegion::findRole(std::string_view key) const {
    return indexOf(roles, key);
}
int LifeRegion::findGroup(std::string_view key) const {
    return indexOf(groups, key);
}
int LifeRegion::findFestival(std::string_view key) const {
    return indexOf(festivals, key);
}
int LifeRegion::findEvent(std::string_view key) const {
    return indexOf(events, key);
}
int LifeRegion::findChain(std::string_view key) const {
    return indexOf(chains, key);
}

int LifeData::findKind(std::string_view id) const {
    const auto it = kindIndex.find(std::string(id));
    return it == kindIndex.end() ? kNoIndex : it->second;
}

int LifeData::findGoods(std::string_view id) const {
    const auto it = std::ranges::find(goods, id);
    return it == goods.end() ? kNoIndex : static_cast<int>(it - goods.begin());
}

int LifeData::findRegion(std::string_view id) const {
    return indexOf(regions, id);
}

int LifeData::regionOfWorld(int worldRegion) const {
    if (worldRegion < 0 || worldRegion >= static_cast<int>(worldToLife.size())) return kNoIndex;
    return worldToLife[static_cast<std::size_t>(worldRegion)];
}

std::size_t LifeData::memoryBytes() const {
    std::size_t n = steps.capacity() * sizeof(Step) + blocks.capacity() * sizeof(Block) +
                    kinds.capacity() * sizeof(KindDef);
    for (const LifeRegion& r : regions) {
        n += r.roles.capacity() * sizeof(Role) + r.districts.capacity() * sizeof(District) +
             r.events.capacity() * sizeof(Event) + r.chains.capacity() * sizeof(Chain);
        for (const District& d : r.districts) {
            n += d.chunks.capacity() * sizeof(d.chunks[0]) +
                 d.populations.capacity() * sizeof(Population);
            for (const auto& v : d.instances) n += v.capacity() * sizeof(std::uint32_t);
        }
        for (const Role& ro : r.roles) n += ro.schedule.capacity() * sizeof(ScheduleBlock);
    }
    return n;
}

LifeData compileLife(const LoadedWorld& w) {
    LifeData d;
    Compiler c(w, d);
    c.kinds();
    c.tiles();
    d.worldToLife.assign(w.file.regions.size(), kNoIndex);
    for (std::size_t i = 0; i < w.regions.size(); ++i) {
        if (w.regions[i].id.empty()) continue;
        const std::size_t before = d.regions.size();
        c.region(w.regions[i], static_cast<int>(i));
        if (d.regions.size() > before) d.worldToLife[i] = static_cast<int>(d.regions.size() - 1);
    }
    return d;
}

} // namespace lc::life
