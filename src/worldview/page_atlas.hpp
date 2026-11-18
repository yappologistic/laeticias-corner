#pragma once
// Every atlas page the world draws from, as one key space (docs/design/world-tech.md §4.5): the
// home atlas and the generated page are always resident; each set's pages stream in: decoded on
// a worker thread, uploaded a slice of rows per frame (one page at a time), and evicted
// least-recently-used under a memory budget once idle. In synchronous mode (headless runs) a
// wanted page loads at once, so screenshots are reproducible.

#include "platform/batch.hpp"
#include "platform/sdl_ptr.hpp"
#include "render/atlas.hpp"
#include "world/atlas_pages.hpp"

#include <condition_variable>
#include <cstdint>
#include <deque>
#include <filesystem>
#include <mutex>
#include <optional>
#include <string>
#include <string_view>
#include <thread>
#include <vector>

namespace lc::worldview {

struct SpriteRef {
    std::uint16_t page = 0;
    UvRect uv;
    float w = 0;
    float h = 0;
    float ox = 0; // anchor inside the sprite
    float oy = 0;
};

struct PageStats {
    int resident = 0;      // set pages resident
    int streaming = 0;     // queued, decoding or uploading
    int uploads = 0;       // slices uploaded this frame
    std::size_t bytes = 0; // texture memory of every resident page
};

class PageAtlas {
public:
    static constexpr std::uint16_t kHomePage = 0;
    static constexpr std::uint16_t kGeneratedPage = 1;

    PageAtlas(SDL_Renderer* renderer, const Atlas& home, const world::AtlasPages& pages,
              std::filesystem::path atlasDir, bool async, std::size_t budget);
    ~PageAtlas();
    PageAtlas(const PageAtlas&) = delete;
    PageAtlas& operator=(const PageAtlas&) = delete;

    [[nodiscard]] std::optional<SpriteRef> find(std::string_view key) const;
    // The page the renderer generates (flat ground, faces, placeholders), `w` x `h` texels.
    void setGenerated(TexturePtr texture, int w, int h);
    [[nodiscard]] SpriteRef generated(int x, int y, int w, int h, float ox, float oy) const;
    // Shadow sprites get their alpha scaled to a peak of 1 when their page is decoded: shadows
    // draw as one saturating layer composited once at the measured opacity. Call before the
    // first update().
    void markShadow(const SpriteRef& s);

    // This frame needs the set's pages.
    void want(std::string_view set);
    // Starts decodes, uploads one slice, evicts what is idle over budget; `now` in seconds.
    void update(double now);
    // Null while the page is not resident (its sprites are skipped this frame).
    [[nodiscard]] SDL_Texture* texture(std::uint16_t page) const;
    [[nodiscard]] bool setResident(std::string_view set) const;
    // Counts pages becoming resident: whatever skipped sprites redraws when it changes.
    [[nodiscard]] std::uint32_t generation() const { return generation_; }
    [[nodiscard]] float shadowOpacity() const;
    [[nodiscard]] PageStats stats() const;
    [[nodiscard]] std::size_t pageCount() const { return pages_.size(); }
    [[nodiscard]] const std::string& pageSet(std::uint16_t page) const { return pages_[page].set; }
    // Texels of a page (the home page includes the engine's strip below the art).
    [[nodiscard]] std::pair<int, int> pageSize(std::uint16_t page) const {
        return {pages_[page].w, pages_[page].h};
    }
    // Reads one page's pixels (decoded afresh, kTextureFormat), for the overview's colours.
    [[nodiscard]] SurfacePtr decodePage(std::uint16_t page) const;

private:
    enum class State : std::uint8_t { Fixed, Unloaded, Queued, Decoded, Uploading, Resident };
    struct Page {
        std::string set;
        std::filesystem::path file;
        int w = 0;
        int h = 0;
        State state = State::Unloaded;
        SDL_Texture* texture = nullptr; // owned below for streamed pages
        TexturePtr owned;
        SurfacePtr pixels; // decoded, waiting for upload
        int uploadedRows = 0;
        mutable double lastUsed = 0;
        bool wanted = false;
        std::vector<SDL_Rect> shadows;
        float shadowPeak = -1; // measured at decode, -1 before
    };

    [[nodiscard]] SurfacePtr decode(const Page& p, float* peak) const;
    void work(const std::stop_token& stop);
    void upload(Page& p, int rows);
    void evict(double now);

    SDL_Renderer* renderer_;
    const Atlas& home_;
    const world::AtlasPages& index_;
    bool async_;
    std::size_t budget_;
    std::vector<Page> pages_;
    std::uint32_t generation_ = 0;
    double now_ = 0;
    int uploads_ = 0;

    std::mutex mutex_; // guards queue_, done_ and the pixels/peak of pages in flight
    std::condition_variable_any wake_;
    std::deque<std::uint16_t> queue_;
    struct Decoded {
        std::uint16_t page = 0;
        SurfacePtr pixels;
        float peak = -1;
    };
    std::vector<Decoded> done_;
    std::jthread worker_; // last: joined before the rest is destroyed
};

// Width and height of a PNG from its header, without decoding it.
[[nodiscard]] std::optional<std::pair<int, int>> pngSize(const std::filesystem::path& file);

} // namespace lc::worldview
