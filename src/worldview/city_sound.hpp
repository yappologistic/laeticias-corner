#pragma once
// What the living world sounds like where the view is, from the region files' `sound` data
// (world-loose-ends.md §2, out/reports/audio-atmosphere.md "How the engine should mix") and what
// the simulation shows: the crowd of the region's character by how many people are in view, the
// wind family of the district by the wind's strength, rain and its surfaces by the rain's
// intensity, the climate's dawn, dusk and night beds, cicadas in their hours, work loops only
// while someone works, running events' ambience by nearness, the life's one-shots where they
// happen, footsteps and hooves near the view at close zoom, and animals' voices now and then.
// The year is heard too (out/reports/audio-seasons.md §5): the nature beds of the season (and
// of snow lying), calls of their months, night voices, water by the sea's state and the water in
// view, wind in leafy or bare trees, drips after rain, and the region's stings at sunrise,
// nightfall, a storm's end and a new season's first dawn. Every intensity family cross-fades two
// neighbouring levels with equal power. Pure logic (no SDL): the game turns gains, pans and
// shots into mixer calls.

#include "life/city.hpp"
#include "world/loader.hpp"
#include "worldview/tuning.hpp"

#include <array>
#include <cstdint>
#include <filesystem>
#include <span>
#include <string>
#include <vector>

namespace lc::worldview {

class CitySound {
public:
    CitySound(const world::LoadedWorld& world, const life::LifeData& life,
              const std::filesystem::path& audioDir, std::uint64_t seed);

    // Everything it may play (load before use): loops and one-shot effects.
    [[nodiscard]] const std::vector<std::string>& loops() const { return loops_; }
    [[nodiscard]] const std::vector<std::string>& effects() const { return effects_; }

    struct Input {
        Vec2 centre;            // the view's centre, grid tiles
        float halfView = 16;    // half the view's width, tiles (panning and reach)
        float scale = 1;        // window px per world px (footsteps at 2x and closer)
        float away = 1;         // the world's share of the view (1 - the home's)
        float wind = 0.3f;      // 0..1
        float rain = 0;         // 0..1 where the view is
        bool snow = false;      // winter's rain
        bool snowCover = false; // snow lies where the view is (the climate's snow that month)
        double clock = 0.2;     // time of day, 0..1
        int season = 0;         // the home catalog's index
        int month = -1;         // the calendar month (-1: every month's calls)
        float dt = 0;
        std::span<const life::DrawActor> actors; // drawn this frame
        const life::CityLife* city = nullptr;
    };
    void update(const Input& in);
    // The life's one-shots of a step (call after every step: they last one step).
    void addLifeSounds(std::span<const life::LifeSound> sounds);

    struct Out {
        float gain = 0;
        float pan = 0;
    };
    [[nodiscard]] std::span<const Out> out() const { return out_; }
    struct Shot {
        int effect = -1;
        float gain = 1;
        float pan = 0;
        float pitch = 1;
    };
    // One-shots to play this update.
    [[nodiscard]] std::span<const Shot> shots() const { return shots_; }
    // People in view as the crowd counts them, and the crowd's level position (0..2), for tests.
    [[nodiscard]] int people() const { return people_; }
    [[nodiscard]] float crowdLevel() const { return crowdLevel_; }
    // One line per region whose seasonal nature beds were guessed from the world manifest's tags
    // because its file does not name them (`nature_seasons`, `nature_snow`): missing data.
    [[nodiscard]] const std::vector<std::string>& guesses() const { return guesses_; }
    // The music's gain while a sting plays (1 otherwise).
    [[nodiscard]] float musicDuck() const { return duckFor_ > 0 ? tuning::kStingDuck : 1.0f; }
    // The nature bed a region plays at that season and phase (0 dawn, 1 dusk, 2 night, 3 day),
    // with snow lying or not, in its plain districts (file; empty: none), for tests and the
    // report.
    [[nodiscard]] std::string natureOf(int region, int season, int phase, bool snow) const;

private:
    struct Family {
        std::array<int, 4> level{-1, -1, -1, -1}; // loop indices, quiet to loud
        int count = 0;
    };
    struct Window {
        float from = 0;
        float to = 24;
        unsigned seasons = ~0u;   // bit per season
        std::uint16_t months = 0; // bit per calendar month; 0: every month
    };
    struct RegionSound {
        bool any = false;
        Family crowd;
        Family wind;
        Family rain;
        int snow = -1;
        std::array<int, 3> nature{-1, -1, -1}; // dawn, dusk, night
        // A season's own nature beds (dawn, dusk, night, day), -1 where the plain one plays;
        // and those while snow lies (day, night).
        std::vector<std::array<int, 4>> natureBy;
        std::array<int, 2> natureSnow{-1, -1};
        std::array<int, 4> stings{-1, -1, -1, -1}; // sunrise, nightfall, storm's end, season
        Family cicadas;
        Window cicadaHours;
        bool cicadaClear = true;
        struct Call {
            int effect = -1;
            Window when;
        };
        std::vector<Call> calls;
        std::vector<std::vector<int>> voices; // per life kind: effects
        float crowdFull = 30;
    };
    struct DistrictSound {
        bool any = false;
        bool sea = false; // open water (the district's area)
        Family wind;
        std::array<int, 3> nature{-1, -1, -1}; // the district's own plain beds
        Family water;                          // the water family heard where it shows
        float waterLevel = -1;                 // fixed level (a river's speed), -1: sea state
        float leaves = 0;                      // share of trees (wind in their crowns)
        Family crowd;
        float crowdFull = 0;
        struct Surface {
            Family family;
            float share = 0;
        };
        std::array<Surface, 2> surfaces; // the two largest under the rain
        std::vector<int> steps;
        std::vector<int> hooves;
        std::vector<int> stairs;
        int cart = -1;
    };
    struct RoleSound {
        int oneshot = -1;
        int loop = -1;
    };

    int loop(const std::string& file);
    int effect(const std::string& file);
    [[nodiscard]] int natureFile(const RegionSound& rs, const DistrictSound* ds, int season,
                                 int phase, bool snow) const;
    void listenWater();
    void stings(const RegionSound& rs, float hour, bool raining, bool heard);
    Family family(const std::string& name);
    void playFamily(const Family& f, float position, float gain, float pan = 0);
    [[nodiscard]] float rand01();
    [[nodiscard]] Shot placed(int effect, Vec2 at, float reach, float gain) const;

    const world::LoadedWorld& world_;
    const life::LifeData& life_;
    std::filesystem::path audioDir_;
    std::vector<std::string> loops_;
    std::vector<std::string> effects_;
    std::vector<RegionSound> regions_;          // per world region
    std::vector<DistrictSound> districts_;      // per world district
    std::vector<std::vector<RoleSound>> roles_; // per life region, per role
    std::vector<int> eventLoop_;                // per life sound: loop index, -1
    std::vector<int> lifeEffect_;               // per life sound: effect index, -1
    std::vector<Out> out_;
    std::vector<Shot> shots_;
    std::vector<life::LifeSound> pending_;
    Input in_;
    std::uint64_t rng_;
    int people_ = 0;
    float crowdLevel_ = 0;
    float tick_ = 0;   // the slow pass (work loops, voices) runs at 10 Hz
    float callIn_ = 0; // seconds until the next bird or animal call
    struct Walker {
        life::Handle handle;
        float stride = 0;
    };
    std::array<Walker, 16> walkers_{}; // the nearest walkers' strides at the last update
    std::size_t walkerCount_ = 0;
    std::vector<std::pair<float, int>> work_; // per loop: nearest worker's gain and pan source
    Family seaOpen_;                          // open water away from any shore
    Family treesLeafy_;                       // wind in leafy crowns, and in bare ones
    Family treesBare_;
    std::vector<int> drips_; // effects: drops from leaves and eaves after rain
    struct Layer {
        int loop = -1;
        int phase = -1;       // its phase of the day (-1: any)
        unsigned seasons = 0; // bit per season (0: any)
    };
    std::vector<Layer> layers_; // over the nature beds where rivers and lakes show
    unsigned winter_ = 0;       // bit per season whose trees are bare
    struct Heard {
        const Family* family = nullptr;
        float share = 0;
        float level = -1;
    };
    std::array<Heard, 6> water_{}; // the water families in view and their share (10 Hz)
    float waterIn_ = 0;            // s until the water in view is listened for again
    float sinceRain_ = 1e9f;       // s since the rain in view stopped
    float rainFor_ = 0;            // s the rain in view has lasted
    float dripIn_ = 0;
    float lastHour_ = -1;
    int stingSeason_ = -1; // the season whose turn has been heard
    float duckFor_ = 0;    // s left of the music's duck under a sting
    int lastCall_ = -1;
    std::vector<std::string> guesses_;
};

} // namespace lc::worldview
