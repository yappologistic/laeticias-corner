#pragma once
// Text reports of city life for tools and tests: the chains as lifesim would report them (the
// cross-check with tools/worldgen), and the life dump (`--life-dump`): the live actors of the
// active area and the district counts at chosen game hours, as JSON that
// tests/world_tools/life_picture.py draws over the district map.

#include "life/city.hpp"

#include <string>

namespace lc::life {

// Every region's chains simulated from empty for `days` days at one tick per second from 06:00,
// with lifesim's rules and nothing else (no seasons, no events), as JSON keyed "<region>/<chain>"
// in tests/world_tools/life_chains.py's format.
[[nodiscard]] std::string chainReport(const LifeWorld& w, int days = 4);

// One dump of the live state: clock, focus, active area, districts (data population and live
// counts), live actors (kind, role, district, position, level, step, goods, flags), running
// events with their routes, chain stocks in the area. Deterministic text for byte comparison.
[[nodiscard]] std::string lifeDump(const CityLife& life, std::string_view label);

} // namespace lc::life
