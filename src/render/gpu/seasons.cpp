#include "render/gpu/seasons.hpp"

#include <nlohmann/json.hpp>

#include <algorithm>
#include <string>

namespace lc::gpu {

RampSeasons parseRamps(const nlohmann::json& ramps) {
    RampSeasons r;
    r.green.fill(-1);
    static constexpr std::array<const char*, 4> kStates{"fresh", "dry", "dormant", "turn"};
    int snowSteps = 0;
    for (const nlohmann::json& x : ramps.value("ramps", nlohmann::json::array())) {
        const int id = x.value("id", 0);
        if (id <= 0 || id >= kRampIds) continue;
        const auto i = static_cast<std::size_t>(id);
        const std::string cls = x.value("class", "");
        if (cls == "grass") r.green[i] = static_cast<std::int8_t>(GreenClass::Grass);
        if (cls == "foliage_deciduous")
            r.green[i] = static_cast<std::int8_t>(GreenClass::Deciduous);
        r.water[i] = cls == "water";
        if (const auto l = x.find("L"); l != x.end() && l->is_array())
            for (std::size_t k = 0; k < l->size() && k < 8; ++k)
                if ((*l)[k].is_number()) r.lightness[i][k] = (*l)[k].get<float>();
        if (cls == "snow" && x.value("steps", 0) > snowSteps) {
            snowSteps = x.value("steps", 0);
            r.snow = static_cast<std::uint8_t>(id);
        }
        if (const auto s = x.find("states"); s != x.end() && s->is_object())
            for (std::size_t k = 0; k < kStates.size(); ++k)
                if (const auto v = s->find(kStates[k]); v != s->end() && v->is_number_integer())
                    r.states[i][k] = static_cast<std::uint8_t>(std::clamp(v->get<int>(), 0, 255));
    }
    return r;
}

void remapRow(const RampSeasons& r, const ClimateDef& climate, int month,
              std::span<std::uint8_t, kRampIds> out) {
    for (int id = 0; id < kRampIds; ++id) {
        const auto i = static_cast<std::size_t>(id);
        out[i] = static_cast<std::uint8_t>(id);
        if (r.green[i] < 0) continue;
        const auto& row = climate.greens[static_cast<std::size_t>(r.green[i])];
        if (month < 0 || static_cast<std::size_t>(month) >= row.size()) continue;
        // Fresh 0, dry 1, dormant 2, turn 3; leafless takes the duller of what the ramp has.
        int k = -1;
        switch (row[static_cast<std::size_t>(month)]) {
        case GreenState::Green: break;
        case GreenState::Fresh: k = 0; break;
        case GreenState::Dry: k = 1; break;
        case GreenState::Dormant: k = 2; break;
        case GreenState::Turn: k = 3; break;
        case GreenState::Bare: k = 2; break;
        }
        if (k == 2 && r.states[i][2] == 0) k = 1; // no dormant state: dry
        if (k >= 0 && r.states[i][static_cast<std::size_t>(k)] != 0)
            out[i] = r.states[i][static_cast<std::size_t>(k)];
    }
}

float snowCover(const ClimateDef& climate, int month, float dayFraction, int level) {
    const int months = static_cast<int>(climate.snowLine.size());
    if (months == 0 || month < 0) return 0;
    // How much lies at this level in a month: half on the line's own level (a ragged edge, not
    // a step), all above it.
    const auto lies = [&](int m) {
        const int line = climate.snowLine[static_cast<std::size_t>((m % months + months) % months)];
        return line < 0 || level < line ? 0.0f : level == line ? 0.5f : 1.0f;
    };
    const float now = lies(month);
    const float before = lies(month - 1);
    const float t = std::clamp(dayFraction / kSnowMorning, 0.0f, 1.0f);
    const float k = t * t * (3.0f - 2.0f * t);
    return before + (now - before) * k;
}

std::vector<SeasonTile> seasonField(int w, int h, std::span<const std::uint8_t> climate,
                                    std::span<const std::uint8_t> level,
                                    std::span<const std::uint8_t> natural) {
    const auto n = static_cast<std::size_t>(w) * static_cast<std::size_t>(h);
    std::vector<SeasonTile> out(n);
    if (climate.size() < n || level.size() < n || natural.size() < n) return out;
    std::vector<std::uint32_t> queue;
    queue.reserve(n);
    const auto each = [&](std::uint32_t i, auto&& f) {
        const int x = static_cast<int>(i % static_cast<std::uint32_t>(w));
        const int y = static_cast<int>(i / static_cast<std::uint32_t>(w));
        if (x > 0) f(i - 1);
        if (x + 1 < w) f(i + 1);
        if (y > 0) f(i - static_cast<std::uint32_t>(w));
        if (y + 1 < h) f(i + static_cast<std::uint32_t>(w));
    };
    // The land's level: natural tiles their own, built ones the nearest natural tile's.
    std::vector<std::uint8_t> done(n, 0);
    for (std::uint32_t i = 0; i < n; ++i)
        if (natural[i] != 0) {
            out[i].landLevel = level[i];
            done[i] = 1;
            queue.push_back(i);
        }
    for (std::size_t q = 0; q < queue.size(); ++q) {
        const std::uint32_t v = queue[q];
        each(v, [&](std::uint32_t u) {
            if (done[u] != 0) return;
            done[u] = 1;
            out[u].landLevel = out[v].landLevel;
            queue.push_back(u);
        });
    }
    for (std::uint32_t i = 0; i < n; ++i)
        if (done[i] == 0) out[i].landLevel = level[i]; // no natural ground at all: its own
    // The other climate: from every tile beside a different climate, inward up to the band.
    queue.clear();
    std::ranges::fill(done, 0);
    for (std::uint32_t i = 0; i < n; ++i) {
        if (climate[i] == kNoClimate) continue;
        each(i, [&](std::uint32_t u) {
            if (done[i] == 0 && climate[u] != kNoClimate && climate[u] != climate[i]) {
                out[i].other = climate[u];
                out[i].distance = 0;
                done[i] = 1;
                queue.push_back(i);
            }
        });
    }
    for (std::size_t q = 0; q < queue.size(); ++q) {
        const std::uint32_t v = queue[q];
        if (out[v].distance + 1 >= kSeasonBand) continue;
        each(v, [&](std::uint32_t u) {
            if (done[u] != 0 || climate[u] != climate[v]) return;
            done[u] = 1;
            out[u].other = out[v].other;
            out[u].distance = static_cast<std::uint8_t>(out[v].distance + 1);
            queue.push_back(u);
        });
    }
    return out;
}

float otherShare(int distance, float noise) {
    const float d = static_cast<float>(distance) + noise * static_cast<float>(kSeasonBand) * 1.1f;
    const float t = std::clamp(d / static_cast<float>(kSeasonBand), 0.0f, 1.0f);
    return 0.5f * (1.0f - t * t * (3.0f - 2.0f * t));
}

} // namespace lc::gpu
