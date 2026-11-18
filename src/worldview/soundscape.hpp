#pragma once
// What the world sounds like where the view is (docs/design/world-tech.md §4.6, §4.12): each
// region's ambience beds by its theme weight, the hour, the season and month (a season's own
// beds replace the plain ones, crossfaded with equal power), seams ducking the others under their
// drone, zones (a forum, a harbour) by how near the view is, loops placed by items (fountains,
// braziers) as loud as the nearest one and from where those in reach are, and the music region's
// piece: the city (or the home) holding more
// than half the weight, faded out over four seconds when the view leaves and started on a phrase
// boundary (the audio manifests' phrase starts) when it comes back. Pure logic (no SDL): the game
// turns the gains and seeks into mixer calls.

#include "world/loader.hpp"

#include <cstdint>
#include <filesystem>
#include <span>
#include <string>
#include <utility>
#include <vector>

namespace lc::worldview {

class Soundscape {
public:
    // Reads the sets' audio manifests (`<audio>/<set>/manifest.json`) for phrase starts and gains.
    Soundscape(const world::LoadedWorld& world, const std::filesystem::path& audioDir);

    // Every loop it may play (load them all before the mixer opens).
    [[nodiscard]] const std::vector<std::string>& files() const { return files_; }

    struct Input {
        std::span<const float> weights; // per region, low-passed (ThemeMixer)
        Vec2 centre;                    // the view's centre, grid tiles
        float halfView = 16;            // half the view's width, tiles (for panning)
        double clock = 0.2;             // time of day, 0..1
        float night = 0;                // 0 day .. 1 night
        float dt = 0;
        int season = 0;      // the home catalog's season index (the world calendar's)
        int month = -1;      // the calendar month (-1: every month's beds)
        float rain = 0;      // 0..1 where the view is (beds that play only under rain)
        float snowCover = 0; // 0..1 snow lying where the view is: beds are muffled
        float musicDuck = 1; // the music's gain under a sting
    };
    void update(const Input& in);

    struct Out {
        float gain = 0;
        float pan = 0;
    };
    [[nodiscard]] std::span<const Out> out() const { return out_; }
    // Loops to start from a sample this update (index into files(), sample): phrase starts.
    [[nodiscard]] std::span<const std::pair<int, std::uint64_t>> seeks() const { return seeks_; }
    // How much the home's own music and ambience sound (0..1): its share of the view.
    [[nodiscard]] float homeMusic() const { return homeMusic_; }
    [[nodiscard]] float homeWeight() const { return homeWeight_; }
    // The region whose music plays (a city or the home), -1 for none.
    [[nodiscard]] int musicRegion() const { return musicRegion_; }
    // The beds a region plays at that season, month, hour and weather (files), as update()
    // chooses them before their fades.
    [[nodiscard]] std::vector<std::string> bedsOf(int region, int season, int month, float hour,
                                                  bool rain) const;

private:
    int fileIndex(const std::string& file);
    void placeLoops(Vec2 centre);

    const world::LoadedWorld& world_;
    std::vector<std::string> files_;
    std::vector<Out> out_;
    std::vector<float> panWeight_; // per file, this update's
    struct Bed {
        int file = -1;
        float from = 0;
        float to = 24;
        int season = -1;          // -1: the region's plain beds; else that season's own
        std::uint16_t months = 0; // bit per calendar month; 0: every month
        bool rain = false;        // only under rain (a layer: never replaced by a season's)
        std::size_t first = 0;    // the region's first bed of the same file (gains merge there)
        float level = -1;         // its fade, 0..1 (-1: not yet heard: no fade in at start)
    };
    [[nodiscard]] bool plays(const std::vector<Bed>& beds, const Bed& b, int season, int month,
                             float hour, bool rain) const;
    std::vector<std::vector<Bed>> beds_;     // per region
    std::vector<float> bedGain_;             // scratch: one region's beds' gains this update
    std::vector<std::vector<int>> zoneFile_; // per region, per zone
    std::vector<std::vector<std::uint16_t>> zoneMonths_; // per region, per zone: month bits
    std::vector<std::pair<int, std::uint64_t>> seeks_;
    struct Music {
        int day = -1; // file indices
        int night = -1;
        std::vector<std::uint64_t> phrases; // samples
        float level = 0;                    // its envelope, 0..1
    };
    std::vector<Music> music_;        // per region (cities and the home)
    std::vector<float> manifestGain_; // per file
    struct Source {
        int file = -1;
        int region = -1;
        int item = -1; // content item index
        std::string when;
        float from = 0; // a worked loop's hours
        float to = 24;
        std::uint16_t months = 0; // bit per calendar month; 0: every month
    };
    std::vector<Source> sources_;
    std::vector<std::pair<float, float>> placed_; // per source: gain, pan (refreshed at 10 Hz)
    float placeTimer_ = 0;
    int musicRegion_ = -1;
    float homeMusic_ = 1;
    float homeWeight_ = 1;
    std::uint32_t phraseTurn_ = 0;
};

// Game hours (CLAUDE.md: hour = 6 + 24 t) and whether `h` lies in [from, to), over midnight when
// from > to.
[[nodiscard]] float gameHour(double clock);
[[nodiscard]] bool inHours(float h, float from, float to);
// Pan (-1..1) of an ambience zone heard from `centre`: toward its nearest point, none inside.
[[nodiscard]] float zonePan(TileRect rect, Vec2 centre, float halfView);

} // namespace lc::worldview
