#pragma once
// Atlas keys resolved once per catalog entry, so drawing never builds strings or hashes.

#include "core/catalog.hpp"
#include "render/atlas.hpp"

#include <array>
#include <optional>
#include <string>
#include <vector>

namespace lc {

struct FrameSet {
    std::vector<SpriteId> frames; // empty only for optional layers that have no art

    [[nodiscard]] bool empty() const { return frames.empty(); }
    [[nodiscard]] SpriteId at(float time, float fps, std::uint32_t phase = 0) const {
        if (frames.size() <= 1 || fps <= 0) return frames.front();
        const auto n = static_cast<std::uint32_t>(time * fps) + phase;
        return frames[n % frames.size()];
    }
};

struct ItemSprites {
    // Indexed by variant (r<k>) or, for connect layouts, by neighbour mask (m<mask>).
    std::vector<FrameSet> base;
    std::vector<FrameSet> shadow;
    std::vector<FrameSet> glow;
    std::vector<std::optional<Vec2>> smoke; // chimney point relative to the anchor
    std::vector<std::optional<Vec2>> light; // centre of the emissive pixels
};

enum class CritterAnim : std::uint8_t { MoveFront, MoveBack, IdleFront, IdleBack };
enum class Fx : std::uint8_t { Smoke, Ripple, Sparkle, Raindrop, Leaf, Count };

struct SpriteTables {
    std::vector<std::vector<SpriteId>> terrainBase;       // base terrain variants
    std::vector<std::array<FrameSet, 16>> terrainOverlay; // overlay terrain by mask
    std::vector<ItemSprites> items;
    std::vector<std::array<FrameSet, 4>> critters;
    std::array<FrameSet, static_cast<std::size_t>(Fx::Count)> fx;
    SpriteId cliffSE = 0;
    SpriteId cliffSW = 0;
    SpriteId tileOk = 0;
    SpriteId tileBad = 0;
};

[[nodiscard]] SpriteTables buildSpriteTables(Atlas& atlas, const Catalog& cat);

// The f0 key of every sprite the contract requires for this catalog (for coverage reports).
[[nodiscard]] std::vector<std::string> requiredSpriteKeys(const Catalog& cat);

} // namespace lc
