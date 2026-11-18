#include "worldview/actor_looks.hpp"

#include "worldview/tuning.hpp"

#include <cmath>
#include <format>

namespace lc::worldview {
namespace {

constexpr int kMaxFrames = 64;

// Frames of one look: `<prefix>/f0`, `/f1`, ... while they exist.
std::vector<SpriteRef> frames(const PageAtlas& pages, const std::string& prefix) {
    std::vector<SpriteRef> out;
    for (int f = 0; f < kMaxFrames; ++f) {
        const auto s = pages.find(std::format("{}/f{}", prefix, f));
        if (!s) break;
        out.push_back(*s);
    }
    return out;
}

} // namespace

ActorLooks::ActorLooks(const PageAtlas& pages, const life::LifeData& data,
                       const world::Content& content) {
    kinds_.resize(data.kinds.size());
    for (std::size_t k = 0; k < data.kinds.size(); ++k) {
        const life::KindDef& def = data.kinds[k];
        Kind& kind = kinds_[k];
        kind.slots = static_cast<int>(def.anims.size());
        kind.slot.assign(data.animNames.size(), -1);
        const world::GeomActor* geom = content.actorGeometry(def.id);
        const auto carryOf = [&](const std::string& name) -> std::vector<Vec2> {
            if (geom == nullptr) return {};
            for (const auto& [anim, offs] : geom->carryAt)
                if (anim == name) {
                    std::vector<Vec2> v;
                    for (const Offset& o : offs)
                        v.push_back({static_cast<float>(o.x), static_cast<float>(o.y)});
                    return v;
                }
            return {};
        };
        // Variants: walkers, carts and ships have `/v<k>`; figures have one look and none.
        for (int v = 0; v < std::max(1, def.variants); ++v) {
            std::vector<Anim> anims(def.anims.size());
            bool any = false;
            for (std::size_t a = 0; a < def.anims.size(); ++a) {
                const std::string& name = data.animNames[def.anims[a]];
                Anim& an = anims[a];
                an.fps = def.fps[a];
                an.cycle = a < def.strides.size() ? def.strides[a] : 0.0f;
                for (int side = 0; side < 2; ++side) {
                    const std::string facing = name + (side == 0 ? "_front" : "_back");
                    std::vector<SpriteRef> f =
                        frames(pages, std::format("{}/v{}/{}", def.sprite, v, facing));
                    if (f.empty() && v == 0)
                        f = frames(pages, std::format("{}/{}", def.sprite, facing));
                    if (f.empty() && side == 0)
                        f = frames(pages, std::format("{}/v{}/{}", def.sprite, v, name));
                    an.frames[static_cast<std::size_t>(side)] = std::move(f);
                    an.carry[static_cast<std::size_t>(side)] = carryOf(facing);
                }
                // A look with only front frames turns away as itself.
                if (an.frames[1].empty()) {
                    an.frames[1] = an.frames[0];
                    an.carry[1] = an.carry[0];
                }
                any = any || !an.frames[0].empty();
            }
            if (!any) break;
            kind.anims.insert(kind.anims.end(), anims.begin(), anims.end());
            ++kind.variants;
        }
        if (kind.variants == 0) {
            missing_.push_back(def.id);
            continue;
        }
        for (std::size_t a = 0; a < def.anims.size(); ++a)
            if (!kind.anims[a].frames[0].empty())
                kind.slot[def.anims[a]] = static_cast<std::int16_t>(a);
        kind.idle = kind.slot[life::kAnimIdle];
        kind.move = kind.slot[life::kAnimMove];
        if (kind.idle < 0) kind.idle = kind.move;
        if (kind.move < 0) kind.move = kind.idle;
        // A kind with neither stands in its first look with art.
        if (kind.idle < 0)
            for (std::size_t a = 0; a < def.anims.size() && kind.idle < 0; ++a)
                if (!kind.anims[a].frames[0].empty())
                    kind.idle = kind.move = static_cast<std::int16_t>(a);
    }
    goods_.resize(data.goods.size());
    for (std::size_t g = 0; g < data.goods.size(); ++g) {
        goods_[g][0] = pages.find("goods/" + data.goods[g]);
        for (int s = 1; s <= 3; ++s)
            goods_[g][static_cast<std::size_t>(s)] =
                pages.find(std::format("goods/{}/s{}", data.goods[g], s));
    }
}

int cycleFrame(bool moving, float walked, float time, float fps, float cycle, int n) {
    if (n <= 1) return 0;
    const float phase = !moving     ? time * fps
                        : cycle > 0 ? walked / cycle * static_cast<float>(n)
                                    : walked / tuning::kActorWalkPace * fps;
    return ((static_cast<int>(std::floor(phase)) % n) + n) % n;
}

std::optional<ActorLooks::Drawn> ActorLooks::resolve(const life::DrawActor& d) const {
    const Kind& kind = kinds_[d.kind];
    if (kind.variants == 0) return std::nullopt;
    const bool moving = d.speed > tuning::kActorMoving;
    std::int16_t slot = d.anim < kind.slot.size() ? kind.slot[d.anim] : -1;
    if (slot < 0) slot = moving ? kind.move : kind.idle;
    const int v = d.variant < kind.variants ? d.variant : 0;
    const Anim* an = &kind.anims[static_cast<std::size_t>(v * kind.slots + slot)];
    if (an->frames[0].empty()) an = &kind.anims[static_cast<std::size_t>(slot)];
    const std::size_t side = d.facing < 2 ? 0 : 1;
    const std::vector<SpriteRef>& f = an->frames[side];
    if (f.empty()) return std::nullopt;
    const int i =
        cycleFrame(moving, d.stride, d.animTime, an->fps, an->cycle, static_cast<int>(f.size()));
    const bool mirror = d.facing == 1 || d.facing == 3;
    const std::vector<Vec2>& c = an->carry[side];
    Vec2 carry = c.empty() ? tuning::kCarryAt : c[static_cast<std::size_t>(i) % c.size()];
    if (mirror) carry.x = -carry.x;
    return Drawn{&f[static_cast<std::size_t>(i)], mirror, carry};
}

const SpriteRef* ActorLooks::goods(int goods, int stack) const {
    if (goods < 0 || static_cast<std::size_t>(goods) >= goods_.size()) return nullptr;
    const auto& g = goods_[static_cast<std::size_t>(goods)];
    const std::optional<SpriteRef>& s = g[static_cast<std::size_t>(std::clamp(stack, 0, 3))];
    if (s) return &*s;
    if (const std::optional<SpriteRef>& one = g[0]) return &*one;
    return nullptr;
}

} // namespace lc::worldview
