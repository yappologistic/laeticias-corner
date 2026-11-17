#pragma once
// The sprite atlas: the art manifest plus a strip of engine-made sprites (placeholders, light
// pool, soft shadow) sized from the tile cell, uploaded as one texture. Every Sprite carries its
// texture, so more pages can be added later without touching the code that draws them.

#include "core/iso.hpp"
#include "platform/sdl_ptr.hpp"
#include "platform/sprite.hpp"

#include <cstdint>
#include <expected>
#include <filesystem>
#include <map>
#include <optional>
#include <string>
#include <string_view>
#include <unordered_map>
#include <unordered_set>
#include <vector>

namespace lc {

struct SpriteRect {
    int x = 0;
    int y = 0;
    int w = 0;
    int h = 0;
    int ox = 0;
    int oy = 0;
};

struct AtlasManifest {
    std::string image;
    std::map<std::string, SpriteRect, std::less<>> sprites;
};

// Pure parse of atlas.json (no SDL), shared with the coverage test.
[[nodiscard]] std::expected<AtlasManifest, std::string> parseAtlasManifest(std::string_view json);

using SpriteId = std::uint16_t;

class Atlas {
public:
    // Never fails: missing or broken art leaves only the engine sprites (and one log line).
    Atlas(SDL_Renderer* renderer, const std::filesystem::path& assetsDir, Iso iso);

    [[nodiscard]] std::optional<SpriteId> find(std::string_view key) const;
    // find() or the given placeholder; a miss is logged once per key.
    [[nodiscard]] SpriteId resolve(std::string_view key, SpriteId placeholder);
    // Logs a missing optional sprite once.
    void reportMissing(std::string_view key);
    [[nodiscard]] const Sprite& sprite(SpriteId id) const { return sprites_[id]; }
    [[nodiscard]] std::size_t size() const { return sprites_.size(); }
    [[nodiscard]] Iso iso() const { return iso_; }
    // Mean luminance (0..1, of the sRGB values) of a sprite's opaque pixels; night grading uses
    // it to keep pale sprites from out-shining the lights.
    [[nodiscard]] float luma(SpriteId id) const { return luma_[id]; }
    [[nodiscard]] std::size_t textureBytes() const;

    [[nodiscard]] SpriteId placeholderTile() const { return placeholderTile_; }
    // The tile placeholder anchored like edge/cliff_se and edge/cliff_sw: it covers the empty
    // tile beside the rim, so a missing cliff shows instead of hiding under the ground.
    [[nodiscard]] SpriteId placeholderEdgeSE() const { return placeholderEdgeSE_; }
    [[nodiscard]] SpriteId placeholderEdgeSW() const { return placeholderEdgeSW_; }
    [[nodiscard]] SpriteId placeholderBox() const { return placeholderBox_; }
    [[nodiscard]] SpriteId lightBlob() const { return lightBlob_; }
    [[nodiscard]] SpriteId softShadow() const { return softShadow_; }

    // Centre of a sprite's opaque pixels relative to its anchor; places light pools on the
    // emissive pixels.
    [[nodiscard]] std::optional<Vec2> alphaCentroid(SpriteId id) const;
    // Rescales a sprite's alpha so its peak is 1 and returns the original peak. Shadows are drawn
    // as a saturating mask and composited once at that opacity, so overlaps never double-darken.
    float normalizeAlpha(SpriteId id);

private:
    SpriteId add(int x, int y, int w, int h, int ox, int oy);
    [[nodiscard]] std::uint8_t alphaAt(int x, int y) const;

    SurfacePtr pixels_;
    TexturePtr texture_;
    Iso iso_;
    std::vector<Sprite> sprites_;
    std::vector<float> luma_;
    std::vector<SpriteRect> rects_;
    std::unordered_map<std::string, SpriteId> byKey_;
    std::unordered_set<std::string> logged_;
    std::unordered_map<std::uint64_t, float> normalized_; // by rect origin: shared rects once
    SpriteId placeholderTile_ = 0;
    SpriteId placeholderEdgeSE_ = 0;
    SpriteId placeholderEdgeSW_ = 0;
    SpriteId placeholderBox_ = 0;
    SpriteId lightBlob_ = 0;
    SpriteId softShadow_ = 0;
};

} // namespace lc
