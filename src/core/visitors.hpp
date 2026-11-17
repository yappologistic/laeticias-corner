#pragma once
// Visitor simulation: who shows up is decided by visitors[].needs; critters then wander
// inside their habitat near whatever attracted them.

#include "core/catalog.hpp"
#include "core/iso.hpp"
#include "core/rng.hpp"
#include "core/world.hpp"

#include <cstdint>
#include <span>
#include <vector>

namespace lc {

// front faces +x (down-right), back faces -y (up-right); the mirrored pair covers +y and -x.
enum class Facing : std::uint8_t { Front, FrontMirrored, Back, BackMirrored };

struct Critter {
    std::uint8_t visitor = 0;
    Vec2 pos;        // continuous tile coordinates
    Vec2 target;     // where it is walking to
    float timer = 0; // idle time left
    float alpha = 0; // fades in on arrival, out on departure
    float animTime = 0;
    float hover = 0; // base flight height in world px (air habitat only)
    bool moving = false;
    bool leaving = false;
    Facing facing = Facing::Front;
};

struct VisitorEvent {
    enum class Kind : std::uint8_t { Arrived, Call };
    Kind kind = Kind::Arrived;
    int visitor = 0;
    bool firstSighting = false;
    Vec2 pos;
};

// How many of this visitor the corner currently attracts (0 when its needs are unmet or it is
// the wrong time of day).
[[nodiscard]] int desiredCount(const VisitorDef& def, const World& world, bool night);
// Whether a critter of this habitat may stand on the tile containing p.
[[nodiscard]] bool habitatAllows(Habitat h, const World& world, const Catalog& cat, Vec2 p);

class Visitors {
public:
    explicit Visitors(const Catalog& cat);

    // Advances everyone; events() holds what happened during this call.
    void update(const World& world, const Catalog& cat, bool night, float dt, Rng& rng);
    // Spawns the desired population at once (used after loading) without arrival events.
    void populate(const World& world, const Catalog& cat, bool night, Rng& rng);

    [[nodiscard]] std::span<const Critter> critters() const { return critters_; }
    [[nodiscard]] std::span<const VisitorEvent> events() const { return events_; }
    [[nodiscard]] bool seen(int visitor) const { return seen_[static_cast<std::size_t>(visitor)]; }
    void markSeen(int visitor) { seen_[static_cast<std::size_t>(visitor)] = true; }
    [[nodiscard]] int present(int visitor) const;

private:
    bool spawn(const World& world, const Catalog& cat, int visitor, Rng& rng, bool instant);
    bool pickTarget(const World& world, const Catalog& cat, Critter& c, Rng& rng) const;
    [[nodiscard]] bool pickAnchor(const World& world, const Catalog& cat, int visitor, Rng& rng,
                                  TilePos& out) const;

    std::vector<Critter> critters_;
    std::vector<VisitorEvent> events_;
    std::vector<bool> seen_;
    std::vector<float> cooldown_;
};

} // namespace lc
