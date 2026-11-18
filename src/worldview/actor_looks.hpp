#pragma once
// What the world draws for city life's people, animals, carts and ships (src/life/): every kind's
// frames per variant, animation and facing, resolved once from the set pages' keys
// (`walker/<kind>/v<k>/<anim>_<front|back>/f<n>`, `figure/<id>/<anim>_<front|back>/f<n>`,
// `ship/…`, `cart/…`), the carry points of the geometry files, and the goods carried and stacked
// (`goods/<id>`, `goods/<id>/s<1-3>`). Walk frames are chosen by the distance walked, so feet
// never slide and frames change evenly at any pace; the rest play by time.

#include "life/city.hpp"
#include "world/content.hpp"
#include "worldview/page_atlas.hpp"

#include <array>
#include <cstdint>
#include <optional>
#include <vector>

namespace lc::worldview {

// The frame of an `n`-frame cycle playing at `fps`: walking, by the tiles walked (`moving`), so
// frames change every `kActorWalkPace / fps` tiles whatever the pace; otherwise by `time`.
[[nodiscard]] int cycleFrame(bool moving, float stride, float time, float fps, int n);

class ActorLooks {
public:
    ActorLooks(const PageAtlas& pages, const life::LifeData& data, const world::Content& content);

    struct Drawn {
        const SpriteRef* sprite = nullptr;
        bool mirror = false;
        Vec2 carry; // px from the feet to where goods sit (mirrored already)
    };
    // The frame an actor shows now; nullopt when its kind has no art.
    [[nodiscard]] std::optional<Drawn> resolve(const life::DrawActor& d) const;
    // Goods in hand (count 1) or a stack of 1-3 at a slot; null when there is no art.
    [[nodiscard]] const SpriteRef* goods(int goods, int stack) const;
    // Kinds the life uses that have no frames at all (not drawn).
    [[nodiscard]] const std::vector<std::string>& missing() const { return missing_; }

private:
    struct Anim {
        std::array<std::vector<SpriteRef>, 2> frames; // front, back
        std::array<std::vector<Vec2>, 2> carry;       // per frame, empty: the default point
        float fps = 0;
    };
    struct Kind {
        int variants = 0;               // variants with art
        std::vector<std::int16_t> slot; // per LifeData::animNames: index into `anims`, -1
        std::vector<Anim> anims;        // [variant * slots + slot]
        int slots = 0;
        std::int16_t idle = -1;
        std::int16_t move = -1;
    };
    std::vector<Kind> kinds_;
    std::vector<std::array<std::optional<SpriteRef>, 4>> goods_; // in hand, s1..s3
    std::vector<std::string> missing_;
};

} // namespace lc::worldview
