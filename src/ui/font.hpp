#pragma once
// Text and icon glyphs rasterised with stb_truetype into one UI texture (which also carries a
// white texel for untextured shapes).

#include "render/batch.hpp"
#include "render/sdl_ptr.hpp"

#include <array>
#include <filesystem>
#include <string_view>
#include <vector>

namespace lc {

enum class Face : std::uint8_t { Body, Title, Icon, Count };

struct Glyph {
    char32_t cp = 0;
    float x0 = 0, y0 = 0, x1 = 0, y1 = 0; // quad relative to the pen on the baseline
    UvRect uv;
    float advance = 0;
};

// Decodes one UTF-8 sequence starting at text[i], advancing i; invalid bytes yield U+FFFD.
[[nodiscard]] char32_t nextCodepoint(std::string_view text, std::size_t& i);

class Font {
public:
    // Loads the font files; returns false (and logs) when one is missing.
    bool load(const std::filesystem::path& fontsDir);
    // Rasterises every face for this UI scale; cheap to call when the scale is unchanged.
    bool build(SDL_Renderer* renderer, float scale);

    [[nodiscard]] float measure(Face face, std::string_view text) const;
    [[nodiscard]] float ascent(Face face) const { return faces_[idx(face)].ascent; }
    [[nodiscard]] float lineHeight(Face face) const { return faces_[idx(face)].lineHeight; }
    // Draws with the pen's baseline at y; returns the advance.
    float draw(Batch& batch, Face face, std::string_view text, float x, float y,
               SDL_FColor color) const;
    void drawIcon(Batch& batch, char32_t cp, float cx, float cy, SDL_FColor color) const;

    [[nodiscard]] SDL_Texture* texture() const { return texture_.get(); }
    [[nodiscard]] UvRect whiteUv() const { return white_; }

private:
    struct FaceData {
        std::vector<unsigned char> ttf;
        std::vector<Glyph> glyphs; // sorted by codepoint
        float ascent = 0;
        float lineHeight = 0;
        float pixelSize = 0;
    };
    static std::size_t idx(Face f) { return static_cast<std::size_t>(f); }
    [[nodiscard]] const Glyph* find(Face face, char32_t cp) const;

    std::array<FaceData, static_cast<std::size_t>(Face::Count)> faces_;
    TexturePtr texture_;
    UvRect white_;
    float scale_ = 0;
};

} // namespace lc
