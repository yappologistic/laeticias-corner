#pragma once
// Owning wrappers for SDL handles.

#include <SDL3/SDL.h>

#include <memory>

namespace lc {

template <auto Fn>
struct SdlDeleter {
    template <typename T>
    void operator()(T* p) const {
        Fn(p);
    }
};

using WindowPtr = std::unique_ptr<SDL_Window, SdlDeleter<SDL_DestroyWindow>>;
using RendererPtr = std::unique_ptr<SDL_Renderer, SdlDeleter<SDL_DestroyRenderer>>;
using TexturePtr = std::unique_ptr<SDL_Texture, SdlDeleter<SDL_DestroyTexture>>;
using SurfacePtr = std::unique_ptr<SDL_Surface, SdlDeleter<SDL_DestroySurface>>;
using AudioStreamPtr = std::unique_ptr<SDL_AudioStream, SdlDeleter<SDL_DestroyAudioStream>>;
using SdlBuffer = std::unique_ptr<void, SdlDeleter<SDL_free>>;

// Every texture and render target uses this layout: matching formats (and the common window
// format) let renderers, the software one especially, take their fast copy paths.
inline constexpr SDL_PixelFormat kTextureFormat = SDL_PIXELFORMAT_ARGB8888;

// Uploads a surface as a texture in kTextureFormat. Streaming access on purpose: the software
// renderer run-length encodes static textures, after which every copy from deep in a large atlas
// walks the encoding from the top (over twenty times slower). Returns null (and logs) on failure.
[[nodiscard]] inline TexturePtr uploadTexture(SDL_Renderer* renderer, SDL_Surface* surface) {
    const SurfacePtr pixels{SDL_ConvertSurface(surface, kTextureFormat)};
    TexturePtr t;
    if (pixels)
        t.reset(SDL_CreateTexture(renderer, kTextureFormat, SDL_TEXTUREACCESS_STREAMING, pixels->w,
                                  pixels->h));
    if (!t || !SDL_UpdateTexture(t.get(), nullptr, pixels->pixels, pixels->pitch) ||
        !SDL_SetTextureBlendMode(t.get(), SDL_BLENDMODE_BLEND)) {
        SDL_Log("texture upload failed: %s", SDL_GetError());
        t.reset();
    }
    return t;
}

} // namespace lc
