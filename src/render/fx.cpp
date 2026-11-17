#include "render/fx.hpp"

#include "core/tuning.hpp"

#include <cmath>

namespace lc {

void Particles::spawn(Fx kind, Vec2 pos, Vec2 vel, float life, float sway) {
    if (count_ == kCapacity) return;
    pool_[count_++] = Particle{pos, vel, 0.0f, life, sway, kind, false};
}

void Particles::update(float dt, const World& world) {
    for (std::size_t i = 0; i < count_; ++i) {
        Particle& p = pool_[i];
        p.age += dt;
        p.pos.x += p.vel.x * dt;
        p.pos.y += p.vel.y * dt;
        if (p.kind == Fx::Leaf || p.kind == Fx::Petal || p.kind == Fx::Snow)
            p.pos.x += std::sin(p.age * 2.6f + p.sway) * tuning::kLeafSway * iso_.tileH() * dt;
    }
    // Separate pass so particles spawned by landing raindrops start fresh this step.
    std::size_t i = 0;
    while (i < count_) {
        if (pool_[i].age < pool_[i].life) {
            ++i;
            continue;
        }
        const Particle done = pool_[i];
        pool_[i] = pool_[--count_]; // swap-remove; the moved particle is checked next
        const TilePos t = iso_.tileAt(done.pos);
        if (done.kind != Fx::Raindrop || done.landed || !world.hasGround(t)) continue;
        if (world.isWater(t)) {
            spawn(Fx::Ripple, done.pos, {0, 0}, tuning::kRippleSeconds);
        } else if (count_ < kCapacity) {
            pool_[count_++] =
                Particle{done.pos, {0, 0}, 0.0f, tuning::kSplashSeconds, 0.0f, Fx::Raindrop, true};
        }
    }
}

} // namespace lc
