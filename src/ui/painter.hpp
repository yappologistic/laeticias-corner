#pragma once
// Anti-aliased UI shapes, text and sprite thumbnails drawn through one batch.

#include "render/atlas.hpp"
#include "render/batch.hpp"
#include "ui/font.hpp"

#include <string_view>

namespace lc {

struct Box {
    float x = 0;
    float y = 0;
    float w = 0;
    float h = 0;
    [[nodiscard]] bool contains(float px, float py) const {
        return px >= x && py >= y && px < x + w && py < y + h;
    }
    [[nodiscard]] float cx() const { return x + w * 0.5f; }
    [[nodiscard]] float cy() const { return y + h * 0.5f; }
};

class Painter {
public:
    Painter(Batch& batch, const Font& font, const Atlas& atlas)
        : batch_(batch), font_(font), atlas_(atlas) {}

    // Rounded rectangle with a feathered edge; a large feather gives a soft shadow.
    void roundRect(Box b, float radius, SDL_FColor color, float feather = 1.0f);
    void text(Face face, std::string_view s, float x, float baseline, SDL_FColor color);
    // Word-wraps into at most maxLines lines; returns the height used.
    float wrapped(Face face, std::string_view s, float x, float top, float width, int maxLines,
                  SDL_FColor color);
    void icon(char32_t cp, float cx, float cy, SDL_FColor color);
    // Draws an atlas sprite scaled by an integer factor to fit the box, centred.
    void thumbnail(SpriteId id, Box b, float alpha);

    [[nodiscard]] const Font& font() const { return font_; }
    void flush() { batch_.flush(); }

private:
    Batch& batch_;
    const Font& font_;
    const Atlas& atlas_;
};

} // namespace lc
