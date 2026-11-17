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
    std::vector<std::optional<Vec2>> light; // centre of the emissive pixels
};

enum class CritterAnim : std::uint8_t { MoveFront, MoveBack, IdleFront, IdleBack };
enum class Fx : std::uint8_t { Smoke, Ripple, Sparkle, Raindrop, Leaf, Count };

// How far ground sprites (terrain, cliffs) reach beyond their tile's diamond, in world px.
struct Reach {
    float left = 0;
    float right = 0;
    float top = 0;
    float bottom = 0;
};

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
    SpriteId tileArea = 0;       // soft white diamond, tinted for nook areas
    SpriteId placeholder = 0;    // drawn for anything that has no art
    float shadowOpacity = 0.35f; // opacity of the composited shadow layer
    Reach groundReach;
};

[[nodiscard]] SpriteTables buildSpriteTables(Atlas& atlas, const Catalog& cat);

enum class Thumb : std::uint8_t { Terrain, Item, Visitor };

// First frame of a catalog entry's art for interface thumbnails. Falls back to the placeholder
// when the entry has no frames or the index is out of range, so the UI never crashes on it.
[[nodiscard]] SpriteId thumbnail(const SpriteTables& t, Thumb kind, int index);

// The f0 key of every sprite the contract requires for this catalog (for coverage reports).
// Optional layers (shadows) are not listed.
[[nodiscard]] std::vector<std::string> requiredSpriteKeys(const Catalog& cat);

} // namespace lc
