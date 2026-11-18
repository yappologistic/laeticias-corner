#pragma once
// The overview: a small isometric map of the whole world (docs/design/world-tech.md §4.7),
// generated from the world data on a worker thread at load: every tile at 1/16 scale, raised by
// its level and by what stands on it, coloured by the mean colour of its art (or the catalog's
// colour), so the far zoom draws one texture instead of the world.

#include "platform/sdl_ptr.hpp"
#include "world/world_map.hpp"
#include "worldview/page_atlas.hpp"
#include "worldview/world_sprites.hpp"

#include <atomic>
#include <cstdint>
#include <thread>
#include <vector>

namespace lc::worldview {

struct OverviewImage {
    int w = 0;
    int h = 0;
    Vec2 origin;                       // world px at pixel (0, 0)
    float scale = 1;                   // overview px per world px
    std::vector<std::uint32_t> pixels; // ARGB8888, w * h
};

// Builds the image; `pages` supplies the art's pixels (decoded here, then dropped).
[[nodiscard]] OverviewImage makeOverview(const world::WorldMap& map, const WorldSprites& sprites,
                                         const PageAtlas& pages);

class Overview {
public:
    // Starts building at once (on a worker thread when `async`).
    Overview(const world::WorldMap& map, const WorldSprites& sprites, const PageAtlas& pages,
             bool async);
    // Uploads a slice of rows per call once the image is ready; true when the texture is whole.
    bool upload(SDL_Renderer* renderer);
    [[nodiscard]] SDL_Texture* texture() const { return complete_ ? texture_.get() : nullptr; }
    // The image is made (the worker no longer reads the map).
    [[nodiscard]] bool built() const { return ready_; }
    [[nodiscard]] const OverviewImage& image() const { return image_; }
    [[nodiscard]] std::size_t bytes() const;

private:
    OverviewImage image_;
    std::atomic<bool> ready_{false};
    TexturePtr texture_;
    int uploaded_ = 0;
    bool complete_ = false;
    std::jthread worker_;
};

} // namespace lc::worldview
