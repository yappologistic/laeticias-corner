#include "worldview/soundscape.hpp"

#include "worldview/tuning.hpp"

#include <nlohmann/json.hpp>

#include <algorithm>
#include <cmath>
#include <fstream>
#include <numbers>
#include <set>

namespace lc::worldview {
namespace {

constexpr double kRate = 44100.0; // CLAUDE.md "Audio": every file is 44.1 kHz

float approachLinear(float v, float target, float step) {
    return v < target ? std::min(target, v + step) : std::max(target, v - step);
}

} // namespace

float gameHour(double clock) {
    const double h = std::fmod(6.0 + 24.0 * clock, 24.0);
    return static_cast<float>(h < 0 ? h + 24.0 : h);
}

bool inHours(float h, float from, float to) {
    return from <= to ? (h >= from && h < to) : (h >= from || h < to);
}

int Soundscape::fileIndex(const std::string& file) {
    const auto it = std::ranges::find(files_, file);
    if (it != files_.end()) return static_cast<int>(it - files_.begin());
    files_.push_back(file);
    manifestGain_.push_back(1.0f);
    return static_cast<int>(files_.size()) - 1;
}

Soundscape::Soundscape(const world::LoadedWorld& world, const std::filesystem::path& audioDir)
    : world_(world) {
    const world::WorldFile& wf = world.file;
    music_.resize(wf.regions.size());
    beds_.resize(world.regions.size());
    zoneFile_.resize(world.regions.size());
    const Catalog& cat = world.content->home();
    std::size_t mostBeds = 0;
    for (std::size_t r = 0; r < world.regions.size(); ++r) {
        const world::Theme& t = world.regions[r].theme;
        std::vector<Bed>& beds = beds_[r];
        const auto add = [&](const world::AmbienceBed& b, int season) {
            Bed bed{fileIndex(b.file), b.from, b.to, season, 0, b.weather == "rain"};
            for (const std::string& m : b.months)
                for (std::size_t k = 0; k < cat.months.size() && k < 16; ++k)
                    if (cat.months[k] == m) bed.months |= static_cast<std::uint16_t>(1u << k);
            bed.first = beds.size();
            for (std::size_t i = 0; i < beds.size(); ++i)
                if (beds[i].file == bed.file) {
                    bed.first = i;
                    break;
                }
            beds.push_back(bed);
        };
        for (const world::AmbienceBed& b : t.beds) add(b, -1);
        for (const auto& [id, list] : t.seasonBeds) {
            const auto s = std::ranges::find(cat.seasons, id, &SeasonDef::id);
            if (s == cat.seasons.end()) continue;
            for (const world::AmbienceBed& b : list)
                add(b, static_cast<int>(s - cat.seasons.begin()));
        }
        mostBeds = std::max(mostBeds, beds.size());
        for (const world::AmbienceZone& z : t.zones) zoneFile_[r].push_back(fileIndex(z.file));
        for (const world::ItemLoop& l : t.loops) {
            const int item = world.content->findItem(l.item);
            if (item >= 0)
                sources_.push_back({fileIndex(l.file), static_cast<int>(r), item, l.when});
        }
        if (!t.musicDay.empty()) music_[r].day = fileIndex(t.musicDay);
        if (!t.musicNight.empty()) music_[r].night = fileIndex(t.musicNight);
    }
    placed_.assign(sources_.size(), {0.0f, 0.0f});
    // Phrase starts and suggested gains from each set's manifest.
    std::set<std::string> sets;
    for (const world::RegionRef& r : wf.regions) sets.insert(r.set);
    for (const std::string& set : sets) {
        std::ifstream in(audioDir / set / "manifest.json");
        if (!in) continue;
        const nlohmann::json m = nlohmann::json::parse(in, nullptr, false);
        if (!m.is_object() || !m.contains("files") || !m["files"].is_array()) continue;
        for (const nlohmann::json& f : m["files"]) {
            if (!f.is_object() || !f.contains("file") || !f["file"].is_string()) continue;
            const auto it = std::ranges::find(files_, f["file"].get<std::string>());
            if (it == files_.end()) continue;
            const auto idx = static_cast<std::size_t>(it - files_.begin());
            if (f.contains("gain") && f["gain"].is_number())
                manifestGain_[idx] = f["gain"].get<float>();
            if (!f.contains("music") || !f["music"].is_object()) continue;
            const nlohmann::json& starts = f["music"].value("phrase_starts_s", nlohmann::json());
            if (!starts.is_array()) continue;
            for (Music& mu : music_)
                if (mu.day == static_cast<int>(idx) && mu.phrases.empty())
                    for (const nlohmann::json& s : starts)
                        if (s.is_number())
                            mu.phrases.push_back(
                                static_cast<std::uint64_t>(s.get<double>() * kRate));
        }
    }
    out_.assign(files_.size(), {});
    panWeight_.assign(files_.size(), 0.0f);
    bedGain_.assign(mostBeds, 0.0f);
}

bool Soundscape::plays(const std::vector<Bed>& beds, const Bed& b, int season, int month,
                       float hour, bool rain) const {
    const auto inMonth = [&](const Bed& x) {
        return x.months == 0 || month < 0 || ((x.months >> month) & 1u) != 0;
    };
    if (!inHours(hour, b.from, b.to) || (b.rain && !rain)) return false;
    if (b.season >= 0) return b.season == season && inMonth(b);
    if (b.rain) return true;
    // A plain bed gives way to the season's own bed for the hours (and months) it covers.
    for (const Bed& x : beds)
        if (x.season == season && !x.rain && inMonth(x) && inHours(hour, x.from, x.to))
            return false;
    return true;
}

std::vector<std::string> Soundscape::bedsOf(int region, int season, int month, float hour,
                                            bool rain) const {
    std::vector<std::string> out;
    if (region < 0 || static_cast<std::size_t>(region) >= beds_.size()) return out;
    const std::vector<Bed>& beds = beds_[static_cast<std::size_t>(region)];
    for (const Bed& b : beds)
        if (plays(beds, b, season, month, hour, rain))
            out.push_back(files_[static_cast<std::size_t>(b.file)]);
    return out;
}

void Soundscape::placeLoops(Vec2 c) {
    // Each loop sounds as loud as its nearest placed source around the view and from where its
    // sources in reach are, weighted by how loud each is (L-113: two fountains either side of
    // the view are heard from the middle, not from whichever is nearer). Distances are measured
    // from a footprint's centre.
    const world::WorldMap& m = *world_.map;
    const int reach = static_cast<int>(tuning::kLoopReach);
    const TilePos ct{static_cast<int>(std::floor(c.x)), static_cast<int>(std::floor(c.y))};
    for (std::size_t s = 0; s < sources_.size(); ++s) {
        float loudest = 0;
        float sum = 0;
        float panSum = 0;
        m.forEachItemIn({ct.x - reach, ct.y - reach, ct.x + reach, ct.y + reach},
                        [&](std::uint32_t, const world::Placed& it) {
                            if (static_cast<int>(it.info) != sources_[s].item) return;
                            const Vec2 p{static_cast<float>(it.x) + static_cast<float>(it.w) * 0.5f,
                                         static_cast<float>(it.y) +
                                             static_cast<float>(it.h) * 0.5f};
                            const float d = std::hypot(p.x - c.x, p.y - c.y);
                            if (d >= tuning::kLoopReach) return;
                            const float k = 1.0f - d / tuning::kLoopReach;
                            const float g = k * k;
                            loudest = std::max(loudest, g);
                            sum += g;
                            panSum += g * ((p.x - c.x) - (p.y - c.y)) * 0.5f;
                        });
        placed_[s] = {loudest, sum > 0 ? panSum / sum : 0.0f};
    }
}

float zonePan(TileRect rect, Vec2 centre, float halfView) {
    // From the zone's nearest point, fading to the middle as the listener goes in: a bed the
    // listener stands in surrounds them (L-113).
    const Vec2 near{std::clamp(centre.x, static_cast<float>(rect.x0), static_cast<float>(rect.x1)),
                    std::clamp(centre.y, static_cast<float>(rect.y0), static_cast<float>(rect.y1))};
    const float d = std::hypot(near.x - centre.x, near.y - centre.y);
    if (d <= 0) return 0;
    const float p = ((near.x - centre.x) - (near.y - centre.y)) * 0.5f / std::max(1.0f, halfView);
    return std::clamp(p, -1.0f, 1.0f) * std::min(1.0f, d / tuning::kZoneReach);
}

void Soundscape::update(const Input& in) {
    seeks_.clear();
    for (Out& o : out_) o = {};
    std::vector<float>& panWeight = panWeight_;
    std::ranges::fill(panWeight, 0.0f);
    const float h = gameHour(in.clock);
    const auto weight = [&](std::size_t r) { return r < in.weights.size() ? in.weights[r] : 0.0f; };
    // Seams: everything else ducks under their drone.
    float seam = 0;
    for (std::size_t r = 0; r < world_.regions.size(); ++r)
        if (world_.regions[r].theme.seam) seam += weight(r);
    const float duck = 1.0f - tuning::kSeamDuck * std::min(1.0f, seam);
    const float pan = std::max(1.0f, in.halfView);
    const bool rain = in.rain > tuning::kCityRainOn;
    const float fade = in.dt / tuning::kBedFadeSeconds;
    const float muffle = 1.0f - tuning::kSnowBedDuck * std::clamp(in.snowCover, 0.0f, 1.0f);
    for (std::size_t r = 0; r < world_.regions.size(); ++r) {
        const world::Theme& t = world_.regions[r].theme;
        const float w = weight(r);
        // Every region's beds keep fading whether heard or not, so the view arriving finds them
        // settled; a season's or an hour's change crossfades with equal power.
        std::vector<Bed>& beds = beds_[r];
        for (std::size_t b = 0; b < beds.size(); ++b) {
            Bed& bed = beds[b];
            const float target = plays(beds, bed, in.season, in.month, h, rain) ? 1.0f : 0.0f;
            bed.level = bed.level < 0 ? target : approachLinear(bed.level, target, fade);
            bedGain_[b] = 0;
            const float g = std::sin(bed.level * std::numbers::pi_v<float> * 0.5f);
            // One file heard through two beds (the plain night and a season's) is one sound.
            bedGain_[bed.first] = std::max(bedGain_[bed.first], g);
        }
        // Where no music plays (the land and sea between) the beds carry the place alone, a
        // little louder (QA5 Q5-S-01: the stretches read as dropouts beside the cities).
        const bool stretch = music_[r].day < 0 && music_[r].night < 0 &&
                             world_.file.regions[r].kind != world::RegionKind::Home;
        const float level = tuning::kBedLevel * (stretch ? tuning::kStretchLift : 1.0f);
        if (w > 0)
            for (std::size_t b = 0; b < beds.size(); ++b)
                if (bedGain_[b] > 0)
                    out_[static_cast<std::size_t>(beds[b].file)].gain +=
                        w * bedGain_[b] * level * (t.seam ? 1.0f : duck) * muffle;
        for (std::size_t zi = 0; zi < t.zones.size(); ++zi) {
            const world::AmbienceZone& z = t.zones[zi];
            if (!inHours(h, z.from, z.to)) continue;
            // Full inside the zone, falling off over kZoneReach tiles outside it.
            const float dx = std::max({static_cast<float>(z.rect.x0) - in.centre.x, 0.0f,
                                       in.centre.x - static_cast<float>(z.rect.x1)});
            const float dy = std::max({static_cast<float>(z.rect.y0) - in.centre.y, 0.0f,
                                       in.centre.y - static_cast<float>(z.rect.y1)});
            const float d = std::hypot(dx, dy);
            if (d >= tuning::kZoneReach) continue;
            const float g = (1.0f - d / tuning::kZoneReach) * z.gain * tuning::kZoneLevel * duck;
            const auto f = static_cast<std::size_t>(zoneFile_[r][zi]);
            const float p = zonePan(z.rect, in.centre, pan);
            out_[f].gain += g;
            out_[f].pan += p * g;
            panWeight[f] += g;
        }
    }
    // Item loops, refreshed a few times a second.
    placeTimer_ -= in.dt;
    if (placeTimer_ <= 0) {
        placeTimer_ = tuning::kLoopRefresh;
        placeLoops(in.centre);
    }
    for (std::size_t s = 0; s < sources_.size(); ++s) {
        const Source& src = sources_[s];
        const bool on = src.when == "always" || (src.when == "lit" && in.night > 0.3f) ||
                        (src.when == "afternoon" && inHours(h, 12.0f, 17.0f));
        if (!on || placed_[s].first <= 0) continue;
        const auto f = static_cast<std::size_t>(src.file);
        const float g = placed_[s].first * tuning::kItemLoopLevel * duck;
        out_[f].gain += g;
        out_[f].pan += std::clamp(placed_[s].second / pan, -1.0f, 1.0f) * g;
        panWeight[f] += g;
    }
    // Music: a city, or the home, holding more than half the weight; held with a margin.
    int best = -1;
    float bestW = 0;
    for (std::size_t r = 0; r < world_.file.regions.size(); ++r) {
        const world::RegionKind k = world_.file.regions[r].kind;
        if (k != world::RegionKind::City && k != world::RegionKind::Home) continue;
        if (weight(r) > bestW) {
            bestW = weight(r);
            best = static_cast<int>(r);
        }
    }
    if (musicRegion_ >= 0 && weight(static_cast<std::size_t>(musicRegion_)) <
                                 tuning::kMusicThreshold - tuning::kMusicHysteresis)
        musicRegion_ = -1;
    if (best >= 0 && bestW > tuning::kMusicThreshold + tuning::kMusicHysteresis)
        musicRegion_ = best;
    const float step = in.dt / tuning::kMusicFadeSeconds;
    for (std::size_t r = 0; r < music_.size(); ++r) {
        Music& mu = music_[r];
        const bool on = static_cast<int>(r) == musicRegion_;
        if (mu.day < 0 && mu.night < 0) {
            if (world_.file.regions[r].kind == world::RegionKind::Home)
                homeMusic_ = approachLinear(homeMusic_, on ? 1.0f : 0.0f, step);
            continue;
        }
        if (on && mu.level <= 0 && !mu.phrases.empty()) {
            // Coming back: from a phrase boundary, a different one each time.
            const std::uint64_t at = mu.phrases[phraseTurn_++ % mu.phrases.size()];
            for (const int f : {mu.day, mu.night})
                if (f >= 0) seeks_.emplace_back(f, at);
        }
        mu.level = approachLinear(mu.level, on ? 1.0f : 0.0f, step);
        if (mu.level <= 0) continue;
        const float n = std::clamp(in.night, 0.0f, 1.0f);
        const float music = mu.level * tuning::kMusic * in.musicDuck;
        if (mu.day >= 0) out_[static_cast<std::size_t>(mu.day)].gain += music * (1 - n);
        if (mu.night >= 0) out_[static_cast<std::size_t>(mu.night)].gain += music * n;
    }
    const int home = world_.file.home.region;
    homeWeight_ = home >= 0 ? weight(static_cast<std::size_t>(home)) : 1.0f;
    for (std::size_t f = 0; f < out_.size(); ++f) {
        out_[f].gain = std::min(1.0f, out_[f].gain * manifestGain_[f]);
        out_[f].pan = panWeight[f] > 0 ? out_[f].pan / panWeight[f] : 0.0f;
    }
}

} // namespace lc::worldview
