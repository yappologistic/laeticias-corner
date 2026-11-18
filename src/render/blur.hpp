#pragma once
// A blurred, low-resolution copy of the frame for the interface's glass panels: the caller draws
// the scene into the first level, then a dual-filter (Kawase) chain halves it a few times and
// grows it back with offset linear taps. Render targets are reused across frames.

#include "core/iso.hpp"
#include "platform/sdl_ptr.hpp"

#include <array>

namespace lc {

class Blur {
public:
    explicit Blur(SDL_Renderer* renderer) : renderer_(renderer) {}

    // Sizes the chain for a `screen`-sized frame and a blur of about `radius` pixels, and makes
    // its first level the render target. The caller then draws the frame scaled by sourceScale().
    // Returns false (and logs) when the targets cannot be made; the window is the target again.
    bool begin(Vec2 screen, float radius);
    [[nodiscard]] Vec2 sourceScale() const { return scale_; }
    // Blurs what was drawn since begin() and makes the window the render target again.
    void end();
    // The blurred frame, addressed with screen-space UVs (x / screen width, y / screen height);
    // nullptr unless begin() and end() succeeded since the last invalidate().
    [[nodiscard]] SDL_Texture* result() const { return ready_ ? levels_[0].get() : nullptr; }
    void invalidate() { ready_ = false; }
    [[nodiscard]] int drawCalls() const { return drawCalls_; }
    [[nodiscard]] int levels() const { return count_; }
    // Texture memory of the chain.
    [[nodiscard]] std::size_t bytes() const;

    static constexpr int kMaxLevels = 6;

private:
    void pass(int from, int to);

    SDL_Renderer* renderer_;
    std::array<TexturePtr, kMaxLevels> levels_; // level i holds the frame at 1 / 2^(i+1)
    int count_ = 0;
    int baseW_ = 0; // size of the smallest level; level i is base * 2^(count-1-i)
    int baseH_ = 0;
    Vec2 scale_;
    bool ready_ = false;
    int drawCalls_ = 0;
};

} // namespace lc
