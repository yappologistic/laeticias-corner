#pragma once
// Day/dusk/night/dawn cycle with optional pinning, plus the lighting it implies.

#include <cstdint>
#include <optional>
#include <span>
#include <string_view>

namespace lc {

enum class Phase : std::uint8_t { Day, Dusk, Night, Dawn };
enum class ClockPin : std::uint8_t { Auto, Day, Dusk, Night, Dawn };

[[nodiscard]] std::string_view phaseId(Phase p);
[[nodiscard]] std::string_view pinId(ClockPin p);
[[nodiscard]] std::optional<ClockPin> parsePin(std::string_view id);

struct Rgb {
    float r = 1;
    float g = 1;
    float b = 1;
};

struct Lighting {
    Rgb ambient; // multiplied over the world
    Rgb skyTop;  // background gradient
    Rgb skyBottom;
    float glow = 0;  // strength of emissive layers and light pools, 0..1
    float night = 0; // 0 = full day, 1 = deep night (drives music/ambience crossfade)
};

class Clock {
public:
    void update(double dt);
    void setTime(double t);
    // Pin to a phase (or Auto). With instant=false the time glides there.
    void setPin(ClockPin pin, bool instant);
    [[nodiscard]] double time() const { return t_; }
    [[nodiscard]] ClockPin pin() const { return pin_; }
    [[nodiscard]] Phase phase() const;
    // Calendar day, counted from 0, at most tuning::kMaxCalendarDay. While the clock runs a new
    // day begins at midnight; while it is pinned the calendar keeps turning in play time, one day
    // per day length, so pinning never holds the seasons (and what comes with them) back.
    [[nodiscard]] int day() const { return day_; }
    void setDay(int day);
    // How often the time or the day was set outright (a jump), so followers can tell a jump
    // from the clock running or gliding to a pin.
    [[nodiscard]] std::uint32_t jumps() const { return jumps_; }

private:
    void nextDay();

    double t_ = 0.2; // a fresh corner starts mid-morning
    ClockPin pin_ = ClockPin::Auto;
    int day_ = 0;
    double pinnedDay_ = 0; // share of a calendar day played while pinned
    std::uint32_t jumps_ = 0;
};

[[nodiscard]] Phase phaseAt(double t);
[[nodiscard]] double phaseCentre(Phase p);
// `rain` 0..1: how hard it rains where the camera looks.
[[nodiscard]] Lighting lightingAt(double t, float rain);

// The calendar: seasons of `days[i]` days each, repeating (docs/design/living-corner.md R4.1).
struct SeasonDay {
    int season = 0;
    int day = 0; // within the season, from 0
};
[[nodiscard]] SeasonDay seasonOf(int day, std::span<const int> days);

// The one answer to "which season and month is it today" (every region shares the calendar; a
// region's climate, `Catalog::findClimate`, says what that season and month bring there): the
// season follows the days, or is `pinned` (a kept season, >= 0); the month is that season's
// month for the day of the season (the catalog's `calendar.months`, -1 when it has none).
struct CalendarDay {
    int season = 0;
    int seasonDay = 0; // from 0
    int month = -1;
};
[[nodiscard]] CalendarDay calendarDay(int day, int pinned, std::span<const int> seasonDays,
                                      int months);

} // namespace lc
