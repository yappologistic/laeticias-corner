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

} // namespace lc
