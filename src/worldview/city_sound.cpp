#include "worldview/city_sound.hpp"

#include "worldview/soundscape.hpp"
#include "worldview/tuning.hpp"

#include <algorithm>
#include <cmath>
#include <format>
#include <numbers>

namespace lc::worldview {
namespace {

using nlohmann::json;

std::string text(const json& j, const char* key) {
    const auto it = j.find(key);
    return it != j.end() && it->is_string() ? it->get<std::string>() : std::string();
}

float hours(const std::string& hhmm) {
    if (hhmm.size() < 4) return 0;
    const auto colon = hhmm.find(':');
    if (colon == std::string::npos) return 0;
    return std::stof(hhmm.substr(0, colon)) + std::stof(hhmm.substr(colon + 1)) / 60.0f;
}

unsigned seasonMask(const json& j, const life::LifeData& life) {
    const auto it = j.find("seasons");
    if (it == j.end() || !it->is_array()) return ~0u;
    unsigned m = 0;
    for (const json& s : *it)
        if (s.is_string())
            for (std::size_t k = 0; k < life.seasons.size(); ++k)
                if (life.seasons[k] == s.get<std::string>()) m |= 1u << k;
    return m;
}

// The nearer the louder: full within a few tiles, nothing beyond `reach`.
float near(float d, float reach) {
    const float k = std::clamp(1.0f - d / reach, 0.0f, 1.0f);
    return k * k;
}

} // namespace

CitySound::CitySound(const world::LoadedWorld& world, const life::LifeData& life,
                     const std::filesystem::path& audioDir, std::uint64_t seed)
    : world_(world), life_(life), audioDir_(audioDir), rng_(seed ^ 0x5157A7E5C0DEULL) {
    const world::WorldMap& map = *world.map;
    regions_.resize(world.regions.size());
    for (std::size_t r = 0; r < world.regions.size(); ++r) {
        const json& s = world.regions[r].theme.sound;
        if (!s.is_object()) continue;
        RegionSound& rs = regions_[r];
        rs.any = true;
        rs.crowd = family(text(s, "crowd"));
        rs.wind = family(text(s, "wind"));
        if (const auto rain = s.find("rain"); rain != s.end() && rain->is_object()) {
            rs.rain = family(text(*rain, "family"));
            const std::string snow = text(*rain, "snow");
            if (!snow.empty()) rs.snow = loop("amb/world/" + snow + ".ogg");
        }
        if (const auto n = s.find("nature"); n != s.end() && n->is_object()) {
            const char* phases[3] = {"dawn", "dusk", "night"};
            for (std::size_t p = 0; p < 3; ++p)
                if (const std::string f = text(*n, phases[p]); !f.empty()) rs.nature[p] = loop(f);
        }
        if (const auto c = s.find("cicadas"); c != s.end() && c->is_object()) {
            rs.cicadas = family(text(*c, "family"));
            if (const auto h = c->find("hours"); h != c->end() && h->is_array() && h->size() == 2)
                rs.cicadaHours = {hours((*h)[0].get<std::string>()),
                                  hours((*h)[1].get<std::string>()), seasonMask(*c, life)};
            rs.cicadaClear = text(*c, "weather") != "any";
        }
        if (const auto calls = s.find("calls"); calls != s.end() && calls->is_array())
            for (const json& c : *calls) {
                RegionSound::Call call;
                call.effect = effect(text(c, "file"));
                if (const auto h = c.find("hours"); h != c.end() && h->is_array() && h->size() == 2)
                    call.when = {hours((*h)[0].get<std::string>()),
                                 hours((*h)[1].get<std::string>()), seasonMask(c, life)};
                else
                    call.when.seasons = seasonMask(c, life);
                rs.calls.push_back(call);
            }
        rs.voices.resize(life.kinds.size());
        if (const auto v = s.find("voices"); v != s.end() && v->is_object())
            for (const auto& [kind, files] : v->items()) {
                const int k = life.findKind(kind);
                if (k < 0 || !files.is_array()) continue;
                for (const json& f : files)
                    if (f.is_string())
                        rs.voices[static_cast<std::size_t>(k)].push_back(
                            effect(f.get<std::string>()));
            }
    }
    districts_.resize(map.districtCount());
    for (std::size_t d = 0; d < map.districtCount(); ++d) {
        const int r = map.districtRegion(static_cast<int>(d));
        if (r < 0) continue;
        std::string name = map.districtName(static_cast<int>(d));
        if (const auto slash = name.find('/'); slash != std::string::npos)
            name = name.substr(slash + 1);
        const world::RegionFile& rf = world.regions[static_cast<std::size_t>(r)];
        const auto it = std::ranges::find(rf.districts, name, &world::RegionDistrict::id);
        if (it == rf.districts.end() || !it->sound.is_object()) continue;
        const json& s = it->sound;
        DistrictSound& ds = districts_[d];
        ds.any = true;
        ds.wind = family(text(s, "wind"));
        if (const auto c = s.find("crowd"); c != s.end() && c->is_object()) {
            ds.crowd = family(text(*c, "family"));
            ds.crowdFull = c->value("full", 0.0f);
        }
        if (const auto sf = s.find("surfaces"); sf != s.end() && sf->is_object()) {
            std::vector<std::pair<float, std::string>> all;
            for (const auto& [k, v] : sf->items())
                if (v.is_number()) all.emplace_back(v.get<float>(), k);
            std::ranges::sort(all, std::greater<>{});
            for (std::size_t i = 0; i < std::min<std::size_t>(2, all.size()); ++i)
                ds.surfaces[i] = {family("rain." + all[i].second), all[i].first};
        }
        if (const auto st = s.find("steps"); st != s.end() && st->is_object()) {
            const auto list = [&](const char* key, std::vector<int>& out) {
                if (const auto a = st->find(key); a != st->end() && a->is_array())
                    for (const json& f : *a)
                        if (f.is_string()) out.push_back(effect(f.get<std::string>()));
            };
            list("files", ds.steps);
            list("hooves", ds.hooves);
            list("stairs", ds.stairs);
        }
        if (const std::string cart = text(s, "cart"); !cart.empty()) ds.cart = loop(cart);
    }
    // Roles' work sounds, read beside the life's own compiled roles (by id).
    roles_.resize(life.regions.size());
    for (std::size_t lr = 0; lr < life.regions.size(); ++lr) {
        const life::LifeRegion& reg = life.regions[lr];
        roles_[lr].resize(reg.roles.size());
        if (reg.worldRegion < 0) continue;
        const json& raw = world.regions[static_cast<std::size_t>(reg.worldRegion)].life;
        const auto rolesIt = raw.find("roles");
        if (rolesIt == raw.end() || !rolesIt->is_array()) continue;
        for (const json& role : *rolesIt) {
            const auto snd = role.find("sound");
            if (snd == role.end() || !snd->is_object()) continue;
            const int ri = reg.findRole(text(role, "id"));
            if (ri < 0) continue;
            RoleSound& rs = roles_[lr][static_cast<std::size_t>(ri)];
            if (const std::string f = text(*snd, "oneshot"); !f.empty()) rs.oneshot = effect(f);
            if (const std::string f = text(*snd, "loop"); !f.empty()) rs.loop = loop(f);
        }
    }
    // The life's own sounds: event ambience beds are loops, the rest one-shots.
    eventLoop_.assign(life.sounds.size(), -1);
    lifeEffect_.assign(life.sounds.size(), -1);
    for (std::size_t i = 0; i < life.sounds.size(); ++i) {
        const std::string& f = life.sounds[i];
        if (f.ends_with(".ogg"))
            eventLoop_[i] = loop(f);
        else if (f.ends_with(".wav"))
            lifeEffect_[i] = effect(f);
    }
    out_.resize(loops_.size());
    work_.resize(loops_.size());
    shots_.reserve(64);
    pending_.reserve(256);
}

int CitySound::loop(const std::string& file) {
    if (file.empty() || !std::filesystem::exists(audioDir_ / file)) return -1;
    const auto it = std::ranges::find(loops_, file);
    if (it != loops_.end()) return static_cast<int>(it - loops_.begin());
    loops_.push_back(file);
    return static_cast<int>(loops_.size() - 1);
}

int CitySound::effect(const std::string& file) {
    if (file.empty() || !std::filesystem::exists(audioDir_ / file)) return -1;
    const auto it = std::ranges::find(effects_, file);
    if (it != effects_.end()) return static_cast<int>(it - effects_.begin());
    effects_.push_back(file);
    return static_cast<int>(effects_.size() - 1);
}

CitySound::Family CitySound::family(const std::string& name) {
    // "crowd.latin" -> amb/world/crowd_latin_<n>.ogg, "rain" -> amb/world/rain_<n>.ogg.
    Family f;
    if (name.empty()) return f;
    std::string base = name;
    std::ranges::replace(base, '.', '_');
    for (int n = 1; n <= 4; ++n) {
        const int l = loop(std::format("amb/world/{}_{}.ogg", base, n));
        if (l < 0) break;
        f.level[static_cast<std::size_t>(f.count++)] = l;
    }
    return f;
}

void CitySound::playFamily(const Family& f, float position, float gain, float pan) {
    // Two neighbouring levels at most, cross-faded with equal power on a fractional position.
    if (f.count == 0 || gain <= 0) return;
    const float p = std::clamp(position, 0.0f, static_cast<float>(f.count - 1));
    const int lo = static_cast<int>(std::floor(p));
    const int hi = std::min(lo + 1, f.count - 1);
    const float t = p - static_cast<float>(lo);
    const auto add = [&](int l, float g) {
        Out& o = out_[static_cast<std::size_t>(f.level[static_cast<std::size_t>(l)])];
        if (g > o.gain) o = {g, pan};
    };
    add(lo, gain * std::cos(t * std::numbers::pi_v<float> * 0.5f));
    if (hi != lo) add(hi, gain * std::sin(t * std::numbers::pi_v<float> * 0.5f));
}

float CitySound::rand01() {
    rng_ += 0x9E3779B97F4A7C15ULL;
    std::uint64_t z = rng_;
    z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL;
    z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL;
    return static_cast<float>((z ^ (z >> 31)) >> 40) / static_cast<float>(1ULL << 24);
}

CitySound::Shot CitySound::placed(int fx, Vec2 at, float reach, float gain) const {
    const float dx = at.x - in_.centre.x;
    const float dy = at.y - in_.centre.y;
    const float pan = std::clamp((dx - dy) * 0.5f / std::max(1.0f, in_.halfView), -1.0f, 1.0f);
    return {fx, gain * near(std::hypot(dx, dy), reach), pan, 1.0f};
}

void CitySound::addLifeSounds(std::span<const life::LifeSound> sounds) {
    for (const life::LifeSound& s : sounds)
        if (!s.fx && pending_.size() < pending_.capacity()) pending_.push_back(s);
}

void CitySound::update(const Input& in) {
    in_ = in;
    for (Out& o : out_) o = {};
    shots_.clear();
    const world::WorldMap& map = *world_.map;
    const TilePos c{static_cast<int>(std::floor(in.centre.x)),
                    static_cast<int>(std::floor(in.centre.y))};
    const bool inside = map.inBounds(c);
    const int region = inside ? map.regionAt(c) : -1;
    const int district = inside ? map.districtAt(c) : -1;
    const RegionSound* rs = region >= 0 && regions_[static_cast<std::size_t>(region)].any
                                ? &regions_[static_cast<std::size_t>(region)]
                                : nullptr;
    const DistrictSound* ds = district >= 0 &&
                                      static_cast<std::size_t>(district) < districts_.size() &&
                                      districts_[static_cast<std::size_t>(district)].any
                                  ? &districts_[static_cast<std::size_t>(district)]
                                  : nullptr;
    const float hour = gameHour(in.clock);
    const float away = std::clamp(in.away, 0.0f, 1.0f);
    const bool raining = in.rain > tuning::kCityRainOn;

    // Who is in view: people (not animals, carts or ships) make the crowd.
    int people = 0;
    for (const life::DrawActor& d : in.actors) {
        const life::KindDef& k = life_.kinds[d.kind];
        if (k.cart || k.sprite.starts_with("ship/")) continue;
        if (rs != nullptr && !rs->voices[d.kind].empty()) continue; // an animal
        ++people;
    }
    people_ = people;

    if (rs != nullptr && away > 0) {
        // The crowd: a handful, a market, a festival; within a level by the square root.
        const Family& crowd = ds != nullptr && ds->crowd.count > 0 ? ds->crowd : rs->crowd;
        const float full = ds != nullptr && ds->crowdFull > 0 ? ds->crowdFull : rs->crowdFull;
        const auto n = static_cast<float>(people);
        crowdLevel_ =
            n <= tuning::kCrowdHandful
                ? 0.0f
                : (n <= tuning::kCrowdMarket
                       ? (n - tuning::kCrowdHandful) /
                             (tuning::kCrowdMarket - tuning::kCrowdHandful)
                       : 1.0f + std::min(1.0f, (n - tuning::kCrowdMarket) / tuning::kCrowdMarket));
        const float g = std::min(1.0f, std::sqrt(n / std::max(1.0f, full))) *
                        (raining ? tuning::kCrowdRain : 1.0f) * away;
        if (people > 0) playFamily(crowd, crowdLevel_, g);
        // Wind by strength, the district's place (street, sea, mountain) over the region's.
        playFamily(ds != nullptr && ds->wind.count > 0 ? ds->wind : rs->wind, in.wind * 3.0f,
                   tuning::kCityWind * away);
        // Rain, or snow; surfaces under it by their share of the district.
        if (raining) {
            if (in.snow && rs->snow >= 0) {
                out_[static_cast<std::size_t>(rs->snow)] = {in.rain * away, 0};
            } else {
                playFamily(rs->rain, in.rain * 2.0f, away);
                if (ds != nullptr) {
                    const float sum = ds->surfaces[0].share + ds->surfaces[1].share;
                    const float dense = std::clamp((in.rain - 0.33f) / 0.33f, 0.0f, 1.0f);
                    for (const auto& sf : ds->surfaces)
                        if (sum > 0)
                            playFamily(sf.family, dense,
                                       away * sf.share / sum * tuning::kRainSurface);
                }
            }
        }
        // The climate's beds at dawn, dusk and night.
        const int phase = inHours(hour, tuning::kDawnFrom, tuning::kDawnTo)   ? 0
                          : inHours(hour, tuning::kDuskFrom, tuning::kDuskTo) ? 1
                          : inHours(hour, tuning::kDuskTo, tuning::kDawnFrom) ? 2
                                                                              : -1;
        if (phase >= 0 && rs->nature[static_cast<std::size_t>(phase)] >= 0)
            out_[static_cast<std::size_t>(rs->nature[static_cast<std::size_t>(phase)])] = {
                tuning::kNatureBed * away, 0};
        // Cicadas in their hours and season, louder towards the afternoon's heat.
        const Window& w = rs->cicadaHours;
        if (rs->cicadas.count > 0 && (w.seasons >> in.season & 1u) != 0 &&
            inHours(hour, w.from, w.to) && (!rs->cicadaClear || !raining)) {
            const float mid = (w.from + w.to) * 0.5f;
            const float heat = 1.0f - std::abs(hour - mid) / std::max(0.5f, (w.to - w.from) * 0.5f);
            playFamily(rs->cicadas, heat * 2.0f, tuning::kCicadas * away);
        }
    }

    // Running events' ambience, by nearness to where they happen.
    if (in.city != nullptr) {
        in.city->forEachLoop([&](const life::LifeLoop& l) {
            if (l.sound < 0 || eventLoop_[static_cast<std::size_t>(l.sound)] < 0) return;
            const Shot s = placed(0, l.at, tuning::kEventReach + in.halfView, l.gain);
            Out& o = out_[static_cast<std::size_t>(eventLoop_[static_cast<std::size_t>(l.sound)])];
            if (s.gain > o.gain) o = {s.gain, s.pan};
        });
    }

    // Work loops while someone works (the nearest worker of each), at 10 Hz; carts on the move.
    tick_ -= in.dt;
    if (in.city != nullptr && tick_ <= 0) {
        tick_ = tuning::kCitySlowTick;
        for (auto& w : work_) w = {0.0f, 0};
        const float reach = tuning::kWorkReach + in.halfView * 0.5f;
        in.city->forEachInfo([&](const life::CityLife::Info& a) {
            if (a.state != life::ActState::Act || a.role < 0 || a.region < 0) return;
            const RoleSound& r =
                roles_[static_cast<std::size_t>(a.region)][static_cast<std::size_t>(a.role)];
            if (r.loop < 0 && r.oneshot < 0) return;
            const Shot s = placed(0, a.pos, reach, 1.0f);
            if (s.gain <= 0) return;
            if (r.loop >= 0 && s.gain > work_[static_cast<std::size_t>(r.loop)].first)
                work_[static_cast<std::size_t>(r.loop)] = {
                    s.gain, static_cast<int>(std::lround(s.pan * 1000))};
            // Now and then a sound of the work itself (a stylus, a vendor's call).
            if (r.oneshot >= 0 && rand01() < tuning::kCitySlowTick / tuning::kWorkShotEvery &&
                shots_.size() < tuning::kShotsPerUpdate)
                shots_.push_back(placed(r.oneshot, a.pos, reach, tuning::kWorkShot));
        });
        // Animals call now and then.
        for (const life::DrawActor& d : in.actors) {
            if (rs == nullptr || rs->voices[d.kind].empty()) continue;
            if (rand01() >= tuning::kCitySlowTick / tuning::kVoiceEvery ||
                shots_.size() >= tuning::kShotsPerUpdate)
                continue;
            const std::vector<int>& v = rs->voices[d.kind];
            const int fx =
                v[static_cast<std::size_t>(rand01() * static_cast<float>(v.size())) % v.size()];
            if (fx >= 0) shots_.push_back(placed(fx, d.pos, in.halfView * 2.0f, tuning::kVoice));
        }
    }
    for (std::size_t l = 0; l < work_.size(); ++l)
        if (work_[l].first > 0) {
            Out& o = out_[l];
            const float g = work_[l].first * tuning::kWorkLoop * away;
            if (g > o.gain) o = {g, static_cast<float>(work_[l].second) / 1000.0f};
        }
    if (ds != nullptr && ds->cart >= 0) {
        float g = 0;
        for (const life::DrawActor& d : in.actors)
            if (life_.kinds[d.kind].cart && d.speed > tuning::kActorMoving)
                g = std::max(g, placed(0, d.pos, tuning::kStepReach * 2.0f, 1.0f).gain);
        out_[static_cast<std::size_t>(ds->cart)].gain =
            std::max(out_[static_cast<std::size_t>(ds->cart)].gain, g * tuning::kCart * away);
    }

    // Footsteps and hooves near the view's centre at close zoom, one per step walked.
    std::array<Walker, 16> next{};
    std::size_t nn = 0;
    if (in.scale >= tuning::kStepZoom && ds != nullptr) {
        for (const life::DrawActor& d : in.actors) {
            if (nn == next.size()) break;
            if (d.speed <= tuning::kActorMoving) continue;
            const Shot s = placed(0, d.pos, tuning::kStepReach, 1.0f);
            if (s.gain <= 0) continue;
            next[nn++] = {d.handle, d.stride};
            const auto prev = std::find_if(
                walkers_.begin(), walkers_.begin() + static_cast<std::ptrdiff_t>(walkerCount_),
                [&](const Walker& w) { return w.handle == d.handle; });
            if (prev == walkers_.begin() + static_cast<std::ptrdiff_t>(walkerCount_)) continue;
            if (std::floor(prev->stride / tuning::kStepTiles) ==
                std::floor(d.stride / tuning::kStepTiles))
                continue;
            const bool animal = rs != nullptr && !rs->voices[d.kind].empty();
            const std::vector<int>& files = animal ? ds->hooves : ds->steps;
            if (files.empty() || shots_.size() >= tuning::kShotsPerUpdate) continue;
            Shot sh =
                placed(files[static_cast<std::size_t>(rand01() * static_cast<float>(files.size())) %
                             files.size()],
                       d.pos, tuning::kStepReach, tuning::kStep);
            sh.gain *= 1.0f + (rand01() - 0.5f) * 0.35f; // +-1.5 dB
            sh.pitch = 1.0f + (rand01() - 0.5f) * 0.06f;
            if (sh.effect >= 0) shots_.push_back(sh);
        }
    }
    walkers_ = next;
    walkerCount_ = nn;

    // The life's one-shots (events starting, steps that emit) where they happen.
    for (const life::LifeSound& s : pending_) {
        if (s.sound < 0 || shots_.size() >= tuning::kShotsPerUpdate) continue;
        const int fx = lifeEffect_[static_cast<std::size_t>(s.sound)];
        if (fx >= 0) {
            const Shot sh = placed(fx, s.at, tuning::kEventReach + in.halfView, tuning::kLifeShot);
            if (sh.gain > 0.01f) shots_.push_back(sh);
        }
    }
    pending_.clear();

    // A bird or an animal of the place's hours, now and then.
    callIn_ -= in.dt;
    if (rs != nullptr && callIn_ <= 0) {
        callIn_ = tuning::kCallMin + rand01() * (tuning::kCallMax - tuning::kCallMin);
        // One of those in season and in its hours, each as likely (reservoir pick).
        int pick = -1;
        int seen = 0;
        for (const RegionSound::Call& call : rs->calls)
            if (call.effect >= 0 && (call.when.seasons >> in.season & 1u) != 0 &&
                inHours(hour, call.when.from, call.when.to) &&
                rand01() * static_cast<float>(++seen) < 1.0f)
                pick = call.effect;
        if (pick >= 0 && !raining && shots_.size() < tuning::kShotsPerUpdate)
            shots_.push_back({pick, tuning::kCall * away, rand01() * 1.6f - 0.8f, 1.0f});
    }
}

} // namespace lc::worldview
