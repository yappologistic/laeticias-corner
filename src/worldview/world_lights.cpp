#include "worldview/world_lights.hpp"

#include "render/gpu/tuning.hpp"

#include <nlohmann/json.hpp>

#include <algorithm>
#include <cmath>
#include <optional>

namespace lc::worldview {
namespace {

using json = nlohmann::json;

float hash01(std::uint32_t x) {
    x ^= x >> 16;
    x *= 0x7feb352dU;
    x ^= x >> 15;
    x *= 0x846ca68bU;
    x ^= x >> 16;
    return static_cast<float>(x) / 4294967295.0f;
}

// "hh:mm", "dusk" or "dawn" as game hours.
std::optional<float> hourOf(const json& v) {
    if (!v.is_string()) return std::nullopt;
    const std::string s = v.get<std::string>();
    if (s == "dusk") return gpu::tuning::kDuskHour;
    if (s == "dawn") return gpu::tuning::kDawnHour;
    if (s.size() != 5 || s[2] != ':') return std::nullopt;
    const auto digit = [&](std::size_t i) { return s[i] >= '0' && s[i] <= '9' ? s[i] - '0' : -1; };
    const int h = digit(0) * 10 + digit(1);
    const int m = digit(3) * 10 + digit(4);
    if (digit(0) < 0 || digit(1) < 0 || digit(3) < 0 || digit(4) < 0 || h > 24 || m > 59)
        return std::nullopt;
    return static_cast<float>(h) + static_cast<float>(m) / 60.0f;
}

Rgb hexColour(const json& v, Rgb fallback) {
    if (!v.is_string()) return fallback;
    const std::string s = v.get<std::string>();
    if (s.size() != 7 || s[0] != '#') return fallback;
    const auto byte = [&](std::size_t i) {
        return static_cast<float>(std::stoi(s.substr(i, 2), nullptr, 16)) / 255.0f;
    };
    return {byte(1), byte(3), byte(5)};
}

float hoursSince(float from, float to) {
    const float d = std::fmod(to - from + 48.0f, 24.0f);
    return d;
}

// Where a light's pool lies: under the flame for a small item; on the ground line in front of a
// larger one (lights on its visible faces: windows, doors, wall torches).
Vec2 groundUnder(Vec2 flame, const world::Placed& it, Iso iso, float raise) {
    const auto f = [](int v) { return static_cast<float>(v); };
    if (it.w * it.h <= 1) {
        const Vec2 c = iso.toWorld(f(it.x) + f(it.w) * 0.5f, f(it.y) + f(it.h) * 0.5f);
        return {c.x, c.y - raise};
    }
    const Vec2 l = iso.toWorld(f(it.x), f(it.y + it.h));
    const Vec2 b = iso.toWorld(f(it.x + it.w), f(it.y + it.h));
    const Vec2 r = iso.toWorld(f(it.x + it.w), f(it.y));
    const float x = std::clamp(flame.x, l.x, r.x);
    const float y = x <= b.x ? l.y + (x - l.x) * (b.y - l.y) / std::max(1.0f, b.x - l.x)
                             : b.y + (x - b.x) * (r.y - b.y) / std::max(1.0f, r.x - b.x);
    return {x, std::max(flame.y, y - raise)};
}

} // namespace

LightProfile parseLightProfile(std::string_view id, const json& j) {
    LightProfile p;
    p.id = std::string(id);
    if (!j.is_object()) return p;
    if (const auto k = j.find("kind"); k != j.end() && k->is_string())
        p.kind = k->get<std::string>();
    p.colour = hexColour(j.value("colour", json()), p.colour);
    if (const auto r = j.find("radius"); r != j.end() && r->is_number()) p.radius = r->get<float>();
    if (const auto s = j.find("strength"); s != j.end() && s->is_number())
        p.strength = s->get<float>();
    if (const auto fl = j.find("flicker"); fl != j.end() && fl->is_object()) {
        if (const auto st = fl->find("style"); st != fl->end() && st->is_string())
            p.flicker = gpu::parseFlicker(st->get<std::string>()).value_or(gpu::Flicker::Steady);
        if (const auto hz = fl->find("hz"); hz != fl->end() && hz->is_array() && hz->size() == 2 &&
                                            (*hz)[0].is_number() && (*hz)[1].is_number()) {
            p.hzLo = (*hz)[0].get<float>();
            p.hzHi = (*hz)[1].get<float>();
        }
        if (const auto d = fl->find("depth"); d != fl->end() && d->is_number())
            p.depth = std::clamp(d->get<float>(), 0.0f, 0.08f);
    }
    if (const auto hs = j.find("hours"); hs != j.end() && hs->is_array())
        for (const json& w : *hs) {
            if (!w.is_array() || w.size() != 2) continue;
            const auto on = hourOf(w[0]);
            const auto off = hourOf(w[1]);
            if (on && off) p.hours.emplace_back(*on, *off);
        }
    if (const auto r = j.find("rain"); r != j.end() && r->is_string()) {
        const std::string s = r->get<std::string>();
        p.rain = s == "dim" ? LightRain::Dim : (s == "out" ? LightRain::Out : LightRain::Sheltered);
    }
    if (const auto o = j.find("only"); o != j.end() && o->is_string()) {
        p.only = o->get<std::string>();
        p.festivalOnly = true;
    }
    if (const auto fs = j.find("festivals"); fs != j.end() && fs->is_object())
        for (const auto& [fid, k] : fs->items())
            if (k.is_number()) p.festivals.emplace_back(fid, k.get<float>());
    p.staggered = p.kind == "window" || p.kind == "door";
    return p;
}

float hoursOn(const LightProfile& p, float hour, std::uint32_t seed) {
    using gpu::tuning::kStaggerHours;
    using gpu::tuning::kWindowFadeHours;
    float best = 0;
    for (const auto& [on0, off0] : p.hours) {
        float on = on0;
        float off = off0;
        if (p.staggered) {
            // One by one: lit within the stagger after the hour, out a little either side.
            on += hash01(seed) * kStaggerHours;
            off += (hash01(seed ^ 0x2545f491U) - 0.5f) * kStaggerHours * 0.5f;
        }
        const float span = hoursSince(on, off);
        const float into = hoursSince(on, hour);
        if (span <= 0 || into >= span + kWindowFadeHours) continue;
        const float rise = std::clamp(into / kWindowFadeHours, 0.0f, 1.0f);
        const float fall =
            std::clamp((span + kWindowFadeHours - into) / kWindowFadeHours, 0.0f, 1.0f);
        best = std::max(best, std::min(rise, fall));
    }
    return best;
}

WorldLights::WorldLights(const world::LoadedWorld& world, const WorldSprites& sprites, Hole hole)
    : map_(*world.map), iso_(map_.content().home().iso()) {
    const world::Content& content = map_.content();
    const float lvl = static_cast<float>(content.tileLevel());
    governed_.assign(map_.items().size(), false);
    struct Pending {
        WorldLight light;
        std::size_t chunk = 0;
    };
    std::vector<Pending> pending;
    std::vector<bool> regionGoverned(world.regions.size(), false);
    for (std::size_t r = 0; r < world.regions.size(); ++r) {
        const world::RegionFile& rf = world.regions[r];
        if (rf.id.empty() || !rf.life.is_object()) continue;
        const json& lights = rf.life.value("lights", json::object());
        const json& points = rf.life.value("light_points", json::array());
        if (!points.is_array() || points.empty()) continue;
        regionGoverned[r] = true;
        // This region's profiles, by name, appended to the world's.
        std::vector<std::pair<std::string, std::uint16_t>> names;
        if (const auto ps = lights.find("profiles"); ps != lights.end() && ps->is_object())
            for (const auto& [id, pj] : ps->items()) {
                names.emplace_back(id, static_cast<std::uint16_t>(profiles_.size()));
                profiles_.push_back(parseLightProfile(id, pj));
                profiles_.back().region = static_cast<int>(r);
            }
        for (const json& pt : points) {
            if (!pt.is_array() || pt.size() < 4 || !pt[0].is_number_integer() ||
                !pt[1].is_number_integer() || !pt[2].is_string() || !pt[3].is_string()) {
                ++unmatched_;
                continue;
            }
            const TilePos at{pt[0].get<int>(), pt[1].get<int>()};
            const std::string& itemId = pt[2].get_ref<const std::string&>();
            const std::string& profileId = pt[3].get_ref<const std::string&>();
            const auto prof =
                std::ranges::find(names, profileId, &std::pair<std::string, std::uint16_t>::first);
            const int idx = map_.inBounds(at) ? map_.itemAt(at) : -1;
            if (prof == names.end() || idx < 0 || hole.tiles.contains(at)) {
                ++unmatched_;
                continue;
            }
            const auto item = static_cast<std::uint32_t>(idx);
            const world::Placed& it = map_.items()[item];
            if (it.x != at.x || it.y != at.y || map_.info(it).id != itemId) {
                ++unmatched_;
                continue;
            }
            const float raise = static_cast<float>(it.level) * lvl;
            const Vec2 anchor = iso_.toWorld(TilePos{it.x, it.y});
            Vec2 flame{anchor.x, anchor.y - raise - 24.0f};
            bool placed = false;
            if (pt.size() >= 5 && pt[4].is_string()) {
                if (const world::GeomVariant* g = map_.geometry(it))
                    for (const auto& [name, off] : g->emitters)
                        if (name == pt[4].get_ref<const std::string&>()) {
                            flame = {anchor.x + static_cast<float>(off.x),
                                     anchor.y - raise + static_cast<float>(off.y)};
                            placed = true;
                        }
            }
            if (!placed)
                if (const std::optional<SpriteRef>& gl = sprites.item(it).glow)
                    flame = {anchor.x - gl->ox + gl->w * 0.5f,
                             anchor.y - raise - gl->oy + gl->h * 0.5f};
            WorldLight l;
            l.at = flame;
            l.ground = groundUnder(flame, it, iso_, raise);
            l.profile = prof->second;
            l.seed = static_cast<std::uint32_t>(at.x) * 73856093U ^
                     static_cast<std::uint32_t>(at.y) * 19349663U ^
                     static_cast<std::uint32_t>(prof->second) * 83492791U;
            named_.push_back({item, prof->second, l.seed});
            pending.push_back({l, static_cast<std::size_t>((at.y >> kChunkShift) * map_.chunksX() +
                                                           (at.x >> kChunkShift))});
        }
    }
    for (std::size_t i = 0; i < map_.items().size(); ++i) {
        const world::Placed& it = map_.items()[i];
        const int r = map_.regionAt(TilePos{it.x, it.y});
        governed_[i] = r >= 0 && static_cast<std::size_t>(r) < regionGoverned.size() &&
                       regionGoverned[static_cast<std::size_t>(r)];
    }
    std::ranges::sort(named_);
    const auto chunks = static_cast<std::size_t>(map_.chunksX() * map_.chunksY());
    start_.assign(chunks + 1, 0);
    for (const Pending& p : pending) ++start_[p.chunk + 1];
    for (std::size_t c = 0; c < chunks; ++c) start_[c + 1] += start_[c];
    lights_.resize(pending.size());
    std::vector<std::uint32_t> fill(start_.begin(), start_.end() - 1);
    for (const Pending& p : pending) lights_[fill[p.chunk]++] = p.light;
}

void WorldLights::resolve(const life::CityLife& life) {
    resolvedFor_ = &life;
    const life::LifeData& d = life.lifeWorld().data;
    nights_.assign(profiles_.size(), {});
    for (std::size_t i = 0; i < profiles_.size(); ++i) {
        const LightProfile& p = profiles_[i];
        Night& n = nights_[i];
        if (p.region < 0 || static_cast<std::size_t>(p.region) >= d.worldToLife.size()) continue;
        n.lifeRegion = d.worldToLife[static_cast<std::size_t>(p.region)];
        if (n.lifeRegion < 0) continue;
        const life::LifeRegion& lr = d.regions[static_cast<std::size_t>(n.lifeRegion)];
        const auto festival = [&](std::string_view id) {
            for (std::size_t f = 0; f < lr.festivals.size(); ++f)
                if (lr.festivals[f].id == id) return static_cast<int>(f);
            return -1;
        };
        for (const auto& [id, k] : p.festivals) {
            const int f = id == "*" ? -2 : festival(id);
            if (f != -1) n.festivals.emplace_back(f, k);
        }
        if (p.only.starts_with("event:")) {
            const std::string_view ev = std::string_view(p.only).substr(6);
            for (std::size_t e = 0; e < lr.events.size(); ++e)
                if (lr.events[e].id == ev) n.onlyEvent = static_cast<int>(e);
        } else if (!p.only.empty()) {
            n.onlyFestival = festival(p.only);
        }
    }
}

void WorldLights::update(double clock, double now, const life::CityLife* life) {
    hour_ = static_cast<float>(std::fmod(6.0 + 24.0 * (clock - std::floor(clock)), 24.0));
    now_ = now;
    factor_.assign(profiles_.size(), 1.0f); // keeps its capacity: no allocation once sized
    if (life != nullptr && life != resolvedFor_) resolve(*life);
    for (std::size_t i = 0; i < profiles_.size(); ++i) {
        const LightProfile& p = profiles_[i];
        if (life == nullptr || nights_.empty()) {
            factor_[i] = p.festivalOnly ? 0.0f : 1.0f;
            continue;
        }
        const Night& n = nights_[i];
        // The evening's day: after midnight the night still belongs to the day before.
        const life::LifeClock& c = life->clock();
        const int day = hour_ < 6.0f ? std::max(0, c.day - 1) : c.day;
        const auto on = [&](int f) { return life->festivalOn(n.lifeRegion, f, day, c.season); };
        float k = 1.0f;
        for (const auto& [f, factor] : n.festivals) {
            bool any = false;
            if (f == -2) {
                const auto& fs = life->lifeWorld()
                                     .data.regions[static_cast<std::size_t>(n.lifeRegion)]
                                     .festivals;
                for (std::size_t j = 0; j < fs.size() && !any; ++j) any = on(static_cast<int>(j));
            } else {
                any = on(f);
            }
            if (any) k = std::max(k, factor);
        }
        if (p.festivalOnly) {
            bool lit = n.onlyFestival >= 0 && on(n.onlyFestival);
            for (const life::RunningEvent& e : life->running())
                lit =
                    lit || (n.onlyEvent >= 0 && e.region == n.lifeRegion && e.event == n.onlyEvent);
            k = lit ? k : 0.0f;
        }
        factor_[i] = k;
    }
}

int WorldLights::profileOf(int region, std::string_view id) const {
    for (std::size_t i = 0; i < profiles_.size(); ++i)
        if (profiles_[i].region == region && profiles_[i].id == id) return static_cast<int>(i);
    return -1;
}

Vec2 WorldLights::tileOf(const WorldLight& l) const {
    return iso_.toTile(l.ground);
}

float WorldLights::baseOf(std::uint16_t profile, std::uint32_t seed, float rain) const {
    const LightProfile& p = profiles_[profile];
    const float night =
        profile < factor_.size() ? factor_[profile] : (p.festivalOnly ? 0.0f : 1.0f);
    if (night <= 0) return 0;
    float k = hoursOn(p, hour_, seed) * night;
    if (k <= 0) return 0;
    if (p.rain == LightRain::Out && rain >= gpu::tuning::kRainOut) return 0;
    if (p.rain == LightRain::Dim)
        k *= 1.0f - (1.0f - gpu::tuning::kRainDim) * std::min(1.0f, rain / gpu::tuning::kRainOut);
    return k * p.strength;
}

float WorldLights::flickerOf(std::uint16_t profile, std::uint32_t seed) const {
    const LightProfile& p = profiles_[profile];
    return gpu::flicker(p.flicker, p.hzLo, p.hzHi, p.depth, seed, now_);
}

Rgb WorldLights::colourOf(std::uint16_t profile, std::uint32_t seed, float rain) const {
    const float k = baseOf(profile, seed, rain);
    if (k <= 0) return {0, 0, 0};
    const Rgb c = profiles_[profile].colour;
    const float f = k * flickerOf(profile, seed);
    return {c.r * f, c.g * f, c.b * f};
}

bool WorldLights::glowOn(std::uint32_t item) const {
    if (item >= governed_.size() || !governed_[item]) return true;
    auto it = std::ranges::lower_bound(named_, item, {}, &Named::item);
    for (; it != named_.end() && it->item == item; ++it) {
        const LightProfile& p = profiles_[it->profile];
        const float night =
            it->profile < factor_.size() ? factor_[it->profile] : (p.festivalOnly ? 0.0f : 1.0f);
        if (night > 0 && hoursOn(p, hour_, it->seed) > 0) return true;
    }
    return false;
}

} // namespace lc::worldview
