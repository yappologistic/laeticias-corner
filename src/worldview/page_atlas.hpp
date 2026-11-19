#pragma once
// Every atlas page the world draws from, as one key space (docs/design/world-tech.md §4.5): the
// home atlas and the generated page are always resident; each set's pages stream in: decoded on
// a worker thread, uploaded in slices within a time budget per frame (one page at a time) into
// page-sized texture slots, the pages a view needs first and the rest ahead of need while slots
// are free, and evicted least-recently-used under a memory budget once idle.
// The slots are made (and touched, so the driver allocates them) when streaming starts, as a GPU
// stalls a frame for every fresh 64 MB texture. In synchronous mode (headless runs) a wanted
// page loads at once, so screenshots are reproducible.

#include "platform/batch.hpp"
#include "platform/sdl_ptr.hpp"
#include "render/atlas.hpp"
#include "world/atlas_pages.hpp"

#include <condition_variable>
#include <cstdint>
#include <deque>
#include <filesystem>
#include <future>
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
    bool packed = false; // its page is a packed page and it is not colour-only: decode it
};

struct PageStats {
    int resident = 0;       // set pages resident
    int streaming = 0;      // queued, decoding or uploading
    int wanted = 0;         // of them (or not started yet), pages the view needs
    int uploads = 0;        // slices uploaded this frame
    std::size_t bytes = 0;  // texture memory of every resident page
    std::size_t budget = 0; // the fixed pages and the slots the sets on disk need
};

class PageAtlas {
public:
    static constexpr std::uint16_t kHomePage = 0;
    static constexpr std::uint16_t kGeneratedPage = 1;

    // `packed`: the sets' pages are their packed twins (`<page>.p.png`, raw words; a sprite
    // listed colour-only in `<page>.p.json` keeps its colour there), in ABGR slots so a shader
    // reads the words in order; the decoder (render/gpu/decoder.hpp) draws them.
    PageAtlas(SDL_Renderer* renderer, const Atlas& home, const world::AtlasPages& pages,
              std::filesystem::path atlasDir, bool async, std::size_t budget, bool packed);
    ~PageAtlas();
    PageAtlas(const PageAtlas&) = delete;
    PageAtlas& operator=(const PageAtlas&) = delete;

    [[nodiscard]] std::optional<SpriteRef> find(std::string_view key) const;
    // A shadow from its set's shadow page (half-size art: the sprite's size and anchor are
    // given in world px, twice its texels); none when the set has no shadow page or not this
    // key, and the colour pages' own shadow is used.
    [[nodiscard]] std::optional<SpriteRef> findShadow(std::string_view key) const;
    // A page of reduced art is drawn enlarged, so filtered (the others texel for texel).
    [[nodiscard]] bool smooth(std::uint16_t page) const { return pages_[page].scale != 1.0f; }
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
    // Whether a sprite draws a pixel at (x, y) of itself (sprite pixels from its top-left): its
    // page's opacity, kept from the decode while the page is resident; true when unknown (a
    // fixed page, or one not decoded here), so picking falls back to the sprite's box.
    [[nodiscard]] bool drawsAt(const SpriteRef& s, float x, float y) const;
    // Null while the page is not resident (its sprites are skipped this frame).
    [[nodiscard]] SDL_Texture* texture(std::uint16_t page) const;
    // The home page is its packed twin (packed mode, and it could be made).
    [[nodiscard]] bool homePacked() const { return !pages_[kHomePage].packedFile.empty(); }
    // ... and its packed twin is uploaded (until then the colour page serves, drawn plain).
    [[nodiscard]] bool homePackedReady() const { return pages_[kHomePage].homeArtRows > 0; }
    // Per home atlas sprite id: drawn from packed words (in the art rows, not colour-only).
    [[nodiscard]] std::vector<bool> homePackedSprites() const;
    [[nodiscard]] bool setResident(std::string_view set) const;
    // Counts pages becoming resident: whatever skipped sprites redraws when it changes.
    [[nodiscard]] std::uint32_t generation() const { return generation_; }
    [[nodiscard]] float shadowOpacity() const;
    [[nodiscard]] PageStats stats() const;
    // Page pixels uploaded by the last update(), in bytes.
    [[nodiscard]] std::size_t uploadedBytes() const { return uploadedBytes_; }
    [[nodiscard]] std::size_t pageCount() const { return pages_.size(); }
    [[nodiscard]] const std::string& pageSet(std::uint16_t page) const { return pages_[page].set; }
    // What a report calls the page: its file without the extension ("athens.1"), else its set.
    [[nodiscard]] std::string pageName(std::uint16_t page) const {
        const Page& p = pages_[page];
        return p.file.empty() ? p.set : p.file.stem().string();
    }
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
        std::filesystem::path packedFile;    // the packed twin, empty when the page has none
        std::vector<std::string> colourOnly; // its sprites kept as colour, sorted
        int homeArtRows = 0;        // the home page: rows of packed art uploaded (0: not yet)
        int homeArtRowsPlanned = 0; // ... rows of art its twin has (the strip is below them)
        int w = 0;
        int h = 0;
        State state = State::Unloaded;
        SDL_Texture* texture = nullptr; // a slot's, or owned (the generated page)
        TexturePtr owned;
        int slot = -1; // the texture slot of a streamed page while it holds one
        // Its art at this share of its size (a shadow page: 0.5).
        float scale = 1;
        // In a texture of its own size (`owned`) that is never given up: every shadow page, and
        // every page while the budget holds them all. Otherwise it streams through a slot.
        bool own = false;
        SurfacePtr pixels; // decoded, waiting for upload
        int uploadedRows = 0;
        mutable double lastUsed = 0;
        bool wanted = false;
        std::vector<SDL_Rect> shadows;
        float shadowPeak = -1;             // measured at decode, -1 before
        std::vector<std::uint64_t> opaque; // 1 bit per pixel (drawn: alpha > 0), for picking
    };

    void readSide(Page& p) const;
    void updateHome();
    [[nodiscard]] SurfacePtr decode(const Page& p, float* peak,
                                    std::vector<std::uint64_t>& opaque) const;
    void work(const std::stop_token& stop);
    void upload(Page& p, int rows);
    void evict(double now);
    [[nodiscard]] int freeSlot(double now);
    int makeSlot();
    // What a page's texture coordinates are over: its own texture, or the slot it streams into.
    [[nodiscard]] static std::pair<float, float> textureSize(const Page& p) {
        return p.own ? std::pair{static_cast<float>(p.w), static_cast<float>(p.h)}
                     : std::pair{static_cast<float>(world::kMaxPageSide),
                                 static_cast<float>(world::kMaxPageSide)};
    }
    // A page texture of this size, touched so the driver has it before a frame needs it.
    [[nodiscard]] TexturePtr makeTexture(int w, int h);

    SDL_Renderer* renderer_;
    const Atlas& home_;
    const world::AtlasPages& index_;
    bool async_;
    bool packed_;
    SDL_PixelFormat slotFormat_;
    std::size_t budget_;
    std::size_t slotLimit_ = 1; // page slots the budget holds beside the fixed pages
    bool overLogged_ = false;
    std::vector<Page> pages_;
    std::vector<TexturePtr> slots_; // kMaxPageSide square, shared by the streamed pages
    std::vector<int> slotPage_;     // page in each slot, -1 free
    std::uint32_t generation_ = 0;
    double now_ = 0;
    int uploads_ = 0;
    std::size_t uploadedBytes_ = 0;
    int wantedPending_ = 0;

    // The home page's packed twin: decoding on a worker, then uploading in slices.
    std::future<SurfacePtr> homeJob_;
    SurfacePtr homeWords_;
    TexturePtr homeTarget_;
    int homeRows_ = 0;
    std::mutex mutex_; // guards queue_, done_ and the pixels/peak of pages in flight
    std::condition_variable_any wake_;
    std::deque<std::uint16_t> queue_;
    struct Decoded {
        std::uint16_t page = 0;
        SurfacePtr pixels;
        float peak = -1;
        std::vector<std::uint64_t> opaque;
    };
    std::vector<Decoded> done_;
    std::jthread worker_; // last: joined before the rest is destroyed
};

// Textures filled once from pixels: static on GPU renderers (no CPU copy kept), streaming on the
// software renderer (whose static textures are run-length encoded, slow to draw from deep in a
// large page; see platform/sdl_ptr.hpp).
[[nodiscard]] SDL_TextureAccess uploadAccess(SDL_Renderer* renderer);

// Width and height of a PNG from its header, without decoding it.
[[nodiscard]] std::optional<std::pair<int, int>> pngSize(const std::filesystem::path& file);

} // namespace lc::worldview
