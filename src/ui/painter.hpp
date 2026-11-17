#pragma once
// Anti-aliased UI shapes, glass panels, text and sprite thumbnails drawn through one batch.

#include "core/iso.hpp"
#include "platform/batch.hpp"
#include "platform/sprite.hpp"
#include "ui/font.hpp"
#include "ui/theme.hpp"

#include <array>
#include <cstddef>
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

// Lines `s` takes when word-wrapped to `width`, at most maxLines (the last one is cut short with
// an ellipsis when drawn).
[[nodiscard]] int wrapLines(const Font& font, Face face, std::string_view s, float width,
                            int maxLines);

// The blurred scene behind the interface, sampled with screen-space UVs. A null texture makes
// glass fall back to a plain translucent fill. `brightness` (0 dark .. 1 bright) deepens the
// glass over a bright scene so text keeps its contrast.
struct Backdrop {
    SDL_Texture* texture = nullptr;
    Vec2 screen;
    float brightness = 0;
};

// Interface drawing goes in layers so the whole frame needs only a handful of texture switches:
// queue a layer's glass panels with glass(), draw them with endGlass(), draw the layer's content,
// then endLayer() draws the sprite thumbnails queued meanwhile. Panels in one layer must not
// overlap; a later layer draws over earlier ones.
class Painter {
public:
    Painter(Batch& batch, const Font& font, Backdrop backdrop, float scale)
        : batch_(batch), font_(font), backdrop_(backdrop), scale_(scale) {}

    // Rounded rectangle with a feathered edge; a large feather gives a soft shadow.
    void roundRect(Box b, float radius, SDL_FColor color, float feather = 1.0f);
    // Rounded rectangle shaded from `top` to `bottom`.
    void gradient(Box b, float radius, SDL_FColor top, SDL_FColor bottom);
    // Light line `width` px wide just inside the outline, shaded from `top` to `bottom`.
    void rim(Box b, float radius, float width, SDL_FColor top, SDL_FColor bottom);
    void glass(Box b, float radius, float alpha, const theme::Glass& style);
    void endGlass();
    void text(Face face, std::string_view s, float x, float baseline, SDL_FColor color);
    // Word-wraps into at most maxLines lines; returns the height used.
    float wrapped(Face face, std::string_view s, float x, float top, float width, int maxLines,
                  SDL_FColor color);
    void icon(char32_t cp, float cx, float cy, SDL_FColor color);
    // Queues a sprite centred in the box at scale min(fit, maxScale): whole multiples when that
    // is 1 or more (crisp pixels), smooth fractions below.
    void thumbnail(const Sprite& sprite, Box b, float maxScale, float alpha,
                   SDL_FColor tint = {1, 1, 1, 1});
    void endLayer();

    [[nodiscard]] const Font& font() const { return font_; }

private:
    enum class Fill : std::uint8_t { Flat, Backdrop };
    struct Pane {
        Box box;
        float radius;
        float alpha;
        const theme::Glass* style;
    };
    struct Thumb {
        Sprite sprite;
        Box box;
        float maxScale;
        SDL_FColor color;
    };

    void shape(Box b, float radius, float feather, SDL_FColor top, SDL_FColor bottom, Fill fill);

    Batch& batch_;
    const Font& font_;
    Backdrop backdrop_;
    float scale_;
    std::array<Pane, 16> panes_{};
    std::size_t paneCount_ = 0;
    std::array<Thumb, 64> thumbs_{};
    std::size_t thumbCount_ = 0;
};

} // namespace lc
