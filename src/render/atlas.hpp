#pragma once
// The single sprite atlas: the art manifest plus a strip of engine-made sprites (placeholders,
// light pool, soft shadow), uploaded as one texture.

#include "core/iso.hpp"
#include "render/batch.hpp"
#include "render/sdl_ptr.hpp"

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

struct Sprite {
    UvRect uv;
    float w = 0;
    float h = 0;
    float ox = 0;
    float oy = 0;
};

class Atlas {
public:
    // Never fails: missing or broken art leaves only the engine sprites (and one log line).
    Atlas(SDL_Renderer* renderer, const std::filesystem::path& assetsDir);

    [[nodiscard]] std::optional<SpriteId> find(std::string_view key) const;
    // find() or the given placeholder; a miss is logged once per key.
    [[nodiscard]] SpriteId resolve(std::string_view key, SpriteId placeholder);
    // Logs a missing optional sprite once.
    void reportMissing(std::string_view key);
    [[nodiscard]] const Sprite& sprite(SpriteId id) const { return sprites_[id]; }
    [[nodiscard]] SDL_Texture* texture() const { return texture_.get(); }
    [[nodiscard]] bool hasArt() const { return artCount_ > 0; }

    [[nodiscard]] SpriteId placeholderTile() const { return placeholderTile_; }
    [[nodiscard]] SpriteId placeholderBox() const { return placeholderBox_; }
    [[nodiscard]] SpriteId white() const { return white_; }
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
    std::vector<Sprite> sprites_;
    std::vector<SpriteRect> rects_;
    std::unordered_map<std::string, SpriteId> byKey_;
    std::unordered_set<std::string> logged_;
    std::unordered_map<std::uint64_t, float> normalized_; // by rect origin: shared rects once
    std::size_t artCount_ = 0;
    SpriteId placeholderTile_ = 0;
    SpriteId placeholderBox_ = 0;
    SpriteId white_ = 0;
    SpriteId lightBlob_ = 0;
    SpriteId softShadow_ = 0;
};

} // namespace lc
