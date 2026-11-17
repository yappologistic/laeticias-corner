#include "render/fx.hpp"

#include <cmath>

namespace lc {

void Particles::spawn(Fx kind, Vec2 pos, Vec2 vel, float life, float sway) {
    if (count_ == kCapacity) return;
    pool_[count_++] = Particle{pos, vel, 0.0f, life, sway, kind};
}

void Particles::update(float dt, const World& world) {
    std::size_t i = 0;
    while (i < count_) {
        Particle& p = pool_[i];
        p.age += dt;
        p.pos.x += p.vel.x * dt;
        p.pos.y += p.vel.y * dt;
        if (p.kind == Fx::Leaf) p.pos.x += std::sin(p.age * 2.6f + p.sway) * 6.0f * dt;
        if (p.age < p.life) {
            ++i;
            continue;
        }
        const Particle done = p;
        pool_[i] = pool_[--count_]; // swap-remove; the moved particle is visited next
        if (done.kind == Fx::Raindrop && world.inBounds(tileAt(done.pos)) &&
            world.isWater(tileAt(done.pos))) {
            spawn(Fx::Ripple, done.pos, {0, 0}, 0.8f);
        }
    }
}

} // namespace lc
