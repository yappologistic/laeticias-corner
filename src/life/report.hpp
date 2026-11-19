#pragma once
// Text reports of city life for tools and tests: the chains as lifesim would report them (the
// cross-check with tools/worldgen), and the life dump (`--life-dump`): the live actors of the
// active area and the district counts at chosen game hours, as JSON that
// tests/world_tools/life_picture.py draws over the district map.

#include "life/city.hpp"

#include <string>
#include <vector>

namespace lc::life {

// Every region's chains simulated from empty for `days` days at one tick per second from 06:00,
// with lifesim's rules and nothing else (no seasons, no events), as JSON keyed "<region>/<chain>"
// in tests/world_tools/life_chains.py's format.
[[nodiscard]] std::string chainReport(const LifeWorld& w, int days = 4);

// One dump of the live state: clock, focus, active area, districts (data population and live
// counts), live actors (kind, role, district, position, level, step, goods, flags), running
// events with their routes, chain stocks in the area. Deterministic text for byte comparison.
[[nodiscard]] std::string lifeDump(const CityLife& life, std::string_view label);

// Where the walk data and the life disagree, one line each with its grid tile: road edges
// walkers cannot use (a course over unwalkable ground, or a step no walker can make: left out of
// walking), and slot spots on unwalkable ground or where the region's walkers never reach (no one
// is sent there), regions whose walkable land is mostly out of their walkers' reach, and
// walkable decks over water with no floor height (walkers stand on the deck's highest point, or
// at the water). For the worldgen and art agents; the engine routes around every one.
[[nodiscard]] std::vector<std::string> walkProblems(const LifeWorld& w);

// How the live actors of a rect stand on the floor over their last step (tests and the
// scripts' `expect city floor`): walkers drawn walking off their course's floor band (below the
// lowest or above the highest floor of their tile and the tiles they can step to, by more than
// the slack), ships off their water's level, steps that changed a height or a place by more than
// the gates' bounds, and walkers on raised floors (decks, stairs, walk runs: the check had
// something to see). `scratch` is reused (two gathers of the rect).
struct FloorCheck {
    int offFloor = 0;
    int offWater = 0;
    int jumps = 0; // height
    int hops = 0;  // place
    int raised = 0;
    int afloat = 0;
    float worstStep = 0; // px
    float worstMove = 0; // tiles
    TilePos firstBad{-1, -1};
};
[[nodiscard]] FloorCheck checkFloors(const CityLife& life, TileRect rect,
                                     std::vector<DrawActor>& scratch);

} // namespace lc::life
