#include "app/identity.hpp"

#include "app/version.hpp"
#include "ui/strings.hpp"

#include <format>
#include <string>

namespace lc {

void setAppMetadata() {
    const std::string name(strings::kWindowTitle);
    const std::string version(build::kVersion);
    if (!SDL_SetAppMetadata(name.c_str(), version.c_str(), LC_APP_ID) ||
        !SDL_SetAppMetadataProperty(SDL_PROP_APP_METADATA_TYPE_STRING, "game"))
        SDL_Log("app metadata: %s", SDL_GetError());
}

SurfacePtr loadWindowIcon(const std::filesystem::path& dir) {
    const auto file = [&dir](int size) {
        return (dir / std::format("icon-{}.png", size)).string();
    };
    SurfacePtr icon{SDL_LoadPNG(file(kIconBase).c_str())};
    if (!icon) {
        SDL_Log("window icon: %s", SDL_GetError());
        return icon;
    }
    for (const int size : kIconSizes) {
        if (size == kIconBase || size > kIconLargest) continue;
        // SDL_AddSurfaceAlternateImage takes its own reference: ours is released at scope end.
        const SurfacePtr alt{SDL_LoadPNG(file(size).c_str())};
        if (!alt || !SDL_AddSurfaceAlternateImage(icon.get(), alt.get()))
            SDL_Log("window icon %d px: %s", size, SDL_GetError());
    }
    return icon;
}

} // namespace lc
