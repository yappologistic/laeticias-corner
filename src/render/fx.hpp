#pragma once
// Fixed-capacity particle pool for smoke, ripples, rain, leaves and sparkles.

#include "core/iso.hpp"
#include "core/rng.hpp"
#include "core/world.hpp"
#include "render/sprites.hpp"

#include <array>
#include <span>

namespace lc {

struct Particle {
    Vec2 pos; // world px
    Vec2 vel; // world px per second
    float age = 0;
    float life = 1;
    float sway = 0; // leaves drift sideways with a per-particle phase
    Fx kind = Fx::Sparkle;
    bool landed = false; // raindrops: falling streak (frame 0) until they land, then a splash
};

class Particles {
public:
    static constexpr std::size_t kCapacity = 4096;

    explicit Particles(Iso iso) : iso_(iso) {}

    // Drops the particle silently when the pool is full.
    void spawn(Fx kind, Vec2 pos, Vec2 vel, float life, float sway = 0);
    // Raindrops landing on water leave a ripple, on land a short splash; off the map, nothing.
    void update(float dt, const World& world);
    void clear() { count_ = 0; }
    [[nodiscard]] std::span<const Particle> all() const { return {pool_.data(), count_}; }

private:
    Iso iso_;
    std::array<Particle, kCapacity> pool_{};
    std::size_t count_ = 0;
};

} // namespace lc
