#include "worldview/page_atlas.hpp"

#include "platform/process.hpp"
#include "worldview/cells.hpp"
#include "worldview/tuning.hpp"

#include <nlohmann/json.hpp>

#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <fstream>

namespace lc::worldview {
namespace {

constexpr std::size_t kSlotBytes =
    static_cast<std::size_t>(world::kMaxPageSide) * world::kMaxPageSide * 4;

} // namespace

std::optional<std::pair<int, int>> pngSize(const std::filesystem::path& file) {
    // Signature (8 bytes), IHDR length and type (8), then width and height, big-endian.
    std::ifstream in(file, std::ios::binary);
    std::array<unsigned char, 24> h{};
    if (!in.read(reinterpret_cast<char*>(h.data()), h.size())) return std::nullopt;
    if (h[1] != 'P' || h[2] != 'N' || h[3] != 'G' || h[12] != 'I' || h[13] != 'H')
        return std::nullopt;
    const auto be = [&](std::size_t i) {
        return static_cast<int>((static_cast<unsigned>(h[i]) << 24) |
                                (static_cast<unsigned>(h[i + 1]) << 16) |
                                (static_cast<unsigned>(h[i + 2]) << 8) | h[i + 3]);
    };
    return std::pair{be(16), be(20)};
}

SDL_TextureAccess uploadAccess(SDL_Renderer* renderer) {
    const char* name = SDL_GetRendererName(renderer);
    return name != nullptr && std::string_view(name) == SDL_SOFTWARE_RENDERER
               ? SDL_TEXTUREACCESS_STREAMING
               : SDL_TEXTUREACCESS_STATIC;
}

void PageAtlas::readSide(Page& p) const {
    // `<page>.p.json`: the packed twin's name and the sprites kept as colour on it.
    std::filesystem::path side = p.file.parent_path() / p.file.stem();
    side += ".p.json";
    std::ifstream in(side);
    if (!in) return;
    try {
        const nlohmann::json j = nlohmann::json::parse(in);
        p.packedFile = p.file.parent_path() / j.value("packed", std::string());
        for (const nlohmann::json& k : j.value("colour_only", nlohmann::json::array()))
            if (k.is_string()) p.colourOnly.push_back(k.get<std::string>());
        std::ranges::sort(p.colourOnly);
    } catch (const nlohmann::json::exception& e) {
        SDL_Log("atlas: %s: %s; its colour page is used", side.string().c_str(), e.what());
        p.packedFile.clear();
    }
    if (!p.packedFile.empty() && pngSize(p.packedFile) != pngSize(p.file)) {
        SDL_Log("atlas: %s is not its colour page's size; the colour page is used",
                p.packedFile.string().c_str());
        p.packedFile.clear();
    }
}

PageAtlas::PageAtlas(SDL_Renderer* renderer, const Atlas& home, const world::AtlasPages& pages,
                     std::filesystem::path atlasDir, bool async, std::size_t budget, bool packed)
    : renderer_(renderer), home_(home), index_(pages), async_(async), packed_(packed),
      slotFormat_(packed ? SDL_PIXELFORMAT_ABGR8888 : kTextureFormat), budget_(budget) {

    Page h;
    h.set = "home";
    h.file = atlasDir.parent_path() / "atlas.png";
    h.state = State::Fixed;
    h.texture = home.sprite(home.placeholderTile()).texture;
    float tw = 0;
    float th = 0;
    if (h.texture != nullptr && SDL_GetTextureSize(h.texture, &tw, &th)) {
        h.w = static_cast<int>(tw);
        h.h = static_cast<int>(th);
    }
    // The home page, packed: its twin is decoded on a worker and uploaded in slices into a
    // target of its own that starts as a copy of the colour page (the engine's strip below the
    // art stays); until the last slice the colour page serves (homePackedReady()).
    if (packed_ && h.texture != nullptr) {
        readSide(h);
        if (!h.packedFile.empty()) {
            if (const auto size = pngSize(h.packedFile)) h.homeArtRowsPlanned = size->second;
            const std::filesystem::path file = h.packedFile;
            const SDL_PixelFormat format = slotFormat_;
            homeJob_ = std::async(std::launch::async, [file, format] {
                const SurfacePtr loaded{SDL_LoadPNG(file.string().c_str())};
                return SurfacePtr{loaded ? SDL_ConvertSurface(loaded.get(), format) : nullptr};
            });
        }
    }
    pages_.push_back(std::move(h));
    Page g;
    g.set = "generated";
    g.state = State::Fixed;
    pages_.push_back(std::move(g));
    for (const world::AtlasPage& ap : pages.pages()) {
        Page p;
        p.set = ap.set;
        p.file = atlasDir / ap.image;
        if (packed_) readSide(p);
        if (const auto size = pngSize(p.file)) {
            p.w = size->first;
            p.h = size->second;
        } else {
            SDL_Log("atlas: cannot read %s; its sprites are skipped", p.file.string().c_str());
        }
        pages_.push_back(std::move(p));
    }
    // A slot for every page on disk while the ceiling holds them all: then nothing is ever
    // evicted, pages the view does not need yet load ahead in the background, and a journey to
    // any city finds its art resident. Sets that outgrow the ceiling stream as before, least
    // recently used out first; a view always gets what it needs (freeSlot).
    const std::size_t need = pages_.size() - 2;
    const std::size_t fixed = static_cast<std::size_t>(pages_[kHomePage].w) *
                              static_cast<std::size_t>(pages_[kHomePage].h) * 4;
    const std::size_t room = budget_ > fixed ? (budget_ - fixed) / kSlotBytes : 1;
    slotLimit_ = std::clamp<std::size_t>(need, 1, std::max<std::size_t>(1, room));
    budget_ = fixed + slotLimit_ * kSlotBytes;
    if (async_) {
        for (std::size_t i = 0; i < slotLimit_; ++i)
            if (makeSlot() < 0) break;
        worker_ = std::jthread([this](const std::stop_token& st) { work(st); });
    }
}

int PageAtlas::makeSlot() {
    TexturePtr t{SDL_CreateTexture(renderer_, slotFormat_, uploadAccess(renderer_),
                                   world::kMaxPageSide, world::kMaxPageSide)};
    if (!t || !SDL_SetTextureBlendMode(t.get(), SDL_BLENDMODE_BLEND)) {
        SDL_Log("atlas: cannot create a page texture: %s", SDL_GetError());
        return -1;
    }
    // Touch it: one texel written and drawn, read back so the driver allocates it now.
    const std::uint32_t texel = 0;
    const SDL_Rect one{0, 0, 1, 1};
    const SDL_FRect dot{0, 0, 1, 1};
    if (!SDL_UpdateTexture(t.get(), &one, &texel, 4) ||
        !SDL_RenderTexture(renderer_, t.get(), &dot, &dot))
        SDL_Log("atlas: %s", SDL_GetError());
    if (const SurfacePtr px{SDL_RenderReadPixels(renderer_, &one)}; !px)
        SDL_Log("atlas: %s", SDL_GetError());
    slots_.push_back(std::move(t));
    slotPage_.push_back(-1);
    return static_cast<int>(slots_.size() - 1);
}

int PageAtlas::freeSlot(double now) {
    for (std::size_t i = 0; i < slots_.size(); ++i)
        if (slotPage_[i] < 0) return static_cast<int>(i);
    // Synchronous runs make their slots as they need them, up to what the budget holds.
    if (slots_.size() < slotLimit_) return makeSlot();
    evict(now);
    for (std::size_t i = 0; i < slots_.size(); ++i)
        if (slotPage_[i] < 0) return static_cast<int>(i);
    // Nothing idle long enough: the least recently used page this frame does not want.
    int lru = -1;
    for (std::size_t i = 0; i < slots_.size(); ++i) {
        const Page& p = pages_[static_cast<std::size_t>(slotPage_[i])];
        if (p.state == State::Resident && !p.wanted &&
            (lru < 0 ||
             p.lastUsed < pages_[static_cast<std::size_t>(slotPage_[static_cast<std::size_t>(lru)])]
                              .lastUsed))
            lru = static_cast<int>(i);
    }
    if (lru >= 0) {
        Page& p = pages_[static_cast<std::size_t>(slotPage_[static_cast<std::size_t>(lru)])];
        p.slot = -1;
        p.texture = nullptr;
        p.state = State::Unloaded;
        p.opaque = {}; // its mask goes with it (memory follows the resident pages)
        slotPage_[static_cast<std::size_t>(lru)] = -1;
        return lru;
    }
    // Every slot holds a page the view needs: one more rather than stall (said once).
    if (!overLogged_) {
        SDL_Log("atlas: a view needs more pages than its budget of %zu; making one more",
                slotLimit_);
        overLogged_ = true;
    }
    return makeSlot();
}

PageAtlas::~PageAtlas() {
    worker_.request_stop();
    wake_.notify_all();
}

std::optional<SpriteRef> PageAtlas::find(std::string_view key) const {
    if (const auto id = home_.find(key)) {
        const Sprite& s = home_.sprite(*id);
        const Page& hp = pages_[kHomePage];
        // Packed where the home page has its words: in its art rows and not colour-only.
        const bool words = !hp.packedFile.empty() && hp.h > 0 &&
                           s.uv.v1 * static_cast<float>(hp.h) <=
                               static_cast<float>(hp.homeArtRowsPlanned) + 0.5f &&
                           !std::ranges::binary_search(hp.colourOnly, key);
        return SpriteRef{kHomePage, s.uv, s.w, s.h, s.ox, s.oy, words};
    }
    const world::PageSprite* ps = index_.find(key);
    if (ps == nullptr) return std::nullopt;
    const auto page = static_cast<std::uint16_t>(ps->page + 2);
    const Page& pg = pages_[page];
    if (pg.w <= 0 || pg.h <= 0) return std::nullopt;
    // Streamed pages live in square slots: texture coordinates are over the slot.
    const auto fw = static_cast<float>(world::kMaxPageSide);
    const auto fh = static_cast<float>(world::kMaxPageSide);
    return SpriteRef{page,
                     {ps->x / fw, ps->y / fh, (ps->x + ps->w) / fw, (ps->y + ps->h) / fh},
                     static_cast<float>(ps->w),
                     static_cast<float>(ps->h),
                     static_cast<float>(ps->ox),
                     static_cast<float>(ps->oy),
                     !pg.packedFile.empty() && !std::ranges::binary_search(pg.colourOnly, key)};
}

std::vector<bool> PageAtlas::homePackedSprites() const {
    const Page& hp = pages_[kHomePage];
    std::vector<bool> out(home_.size(), false);
    if (hp.packedFile.empty() || hp.h <= 0) return out;
    for (std::size_t id = 0; id < out.size(); ++id)
        out[id] = home_.sprite(static_cast<SpriteId>(id)).uv.v1 * static_cast<float>(hp.h) <=
                  static_cast<float>(hp.homeArtRowsPlanned) + 0.5f;
    for (const std::string& key : hp.colourOnly)
        if (const auto id = home_.find(key); id && *id < out.size()) out[*id] = false;
    return out;
}

void PageAtlas::setGenerated(TexturePtr texture, int w, int h) {
    Page& g = pages_[kGeneratedPage];
    g.owned = std::move(texture);
    g.texture = g.owned.get();
    g.w = w;
    g.h = h;
}

SpriteRef PageAtlas::generated(int x, int y, int w, int h, float ox, float oy) const {
    const Page& g = pages_[kGeneratedPage];
    const auto fw = static_cast<float>(g.w);
    const auto fh = static_cast<float>(g.h);
    return {kGeneratedPage,
            {static_cast<float>(x) / fw, static_cast<float>(y) / fh, static_cast<float>(x + w) / fw,
             static_cast<float>(y + h) / fh},
            static_cast<float>(w),
            static_cast<float>(h),
            ox,
            oy};
}

void PageAtlas::markShadow(const SpriteRef& s) {
    Page& p = pages_[s.page];
    if (p.state == State::Fixed) return;
    const auto fw = static_cast<float>(world::kMaxPageSide);
    const auto fh = static_cast<float>(world::kMaxPageSide);
    p.shadows.push_back({static_cast<int>(std::lround(s.uv.u0 * fw)),
                         static_cast<int>(std::lround(s.uv.v0 * fh)), static_cast<int>(s.w),
                         static_cast<int>(s.h)});
}

void PageAtlas::want(std::string_view set) {
    for (Page& p : pages_)
        if (p.state != State::Fixed && p.set == set) p.wanted = true;
}

SurfacePtr PageAtlas::decode(const Page& p, float* peak, std::vector<std::uint64_t>& opaque) const {
    const std::filesystem::path& file = p.packedFile.empty() ? p.file : p.packedFile;
    SurfacePtr loaded{SDL_LoadPNG(file.string().c_str())};
    SurfacePtr px;
    if (loaded) px.reset(SDL_ConvertSurface(loaded.get(), slotFormat_));
    if (!px) {
        SDL_Log("atlas: cannot decode %s: %s", file.string().c_str(), SDL_GetError());
        return px;
    }
    // ARGB8888 and ABGR8888: alpha is the top byte of each 32-bit pixel (in a packed page's
    // words it is data: a pixel there is drawn when its word is not zero).
    const bool packedWords = !p.packedFile.empty();
    float sum = 0;
    int count = 0;
    for (const SDL_Rect& r : p.shadows) {
        std::uint32_t top = 0;
        for (int y = r.y; y < r.y + r.h && y < px->h; ++y) {
            const auto* row = reinterpret_cast<const std::uint32_t*>(
                static_cast<const std::uint8_t*>(px->pixels) +
                static_cast<std::ptrdiff_t>(y) * px->pitch);
            for (int x = r.x; x < r.x + r.w && x < px->w; ++x) top = std::max(top, row[x] >> 24);
        }
        if (top == 0) continue;
        sum += static_cast<float>(top) / 255.0f;
        ++count;
        if (top == 255) continue;
        for (int y = r.y; y < r.y + r.h && y < px->h; ++y) {
            auto* row =
                reinterpret_cast<std::uint32_t*>(static_cast<std::uint8_t*>(px->pixels) +
                                                 static_cast<std::ptrdiff_t>(y) * px->pitch);
            for (int x = r.x; x < r.x + r.w && x < px->w; ++x) {
                const std::uint32_t a = std::min<std::uint32_t>(255, (row[x] >> 24) * 255 / top);
                row[x] = (row[x] & 0x00FFFFFFu) | (a << 24);
            }
        }
    }
    *peak = count > 0 ? sum / static_cast<float>(count) : -1.0f;
    // What is drawn where, a bit per pixel: picking asks it (draw-order.md 4.5).
    const auto words = static_cast<std::size_t>((px->w + 63) / 64);
    opaque.assign(words * static_cast<std::size_t>(px->h), 0);
    for (int y = 0; y < px->h; ++y) {
        const auto* row =
            reinterpret_cast<const std::uint32_t*>(static_cast<const std::uint8_t*>(px->pixels) +
                                                   static_cast<std::ptrdiff_t>(y) * px->pitch);
        std::uint64_t* bits = opaque.data() + static_cast<std::size_t>(y) * words;
        for (int x = 0; x < px->w; ++x)
            if (packedWords ? row[x] != 0 : (row[x] >> 24) != 0)
                bits[x >> 6] |= std::uint64_t{1} << (x & 63);
    }
    return px;
}

bool PageAtlas::drawsAt(const SpriteRef& s, float x, float y) const {
    if (s.page >= pages_.size()) return true;
    const Page& p = pages_[s.page];
    if (p.opaque.empty() || p.w <= 0 || p.h <= 0) return true;
    const int px = static_cast<int>(std::floor(s.uv.u0 * static_cast<float>(p.w) + x));
    const int py = static_cast<int>(std::floor(s.uv.v0 * static_cast<float>(p.h) + y));
    if (px < 0 || py < 0 || px >= p.w || py >= p.h) return false;
    const auto words = static_cast<std::size_t>((p.w + 63) / 64);
    return ((p.opaque[static_cast<std::size_t>(py) * words + static_cast<std::size_t>(px >> 6)] >>
             (px & 63)) &
            1u) != 0;
}

SurfacePtr PageAtlas::decodePage(std::uint16_t page) const {
    SurfacePtr loaded{SDL_LoadPNG(pages_[page].file.string().c_str())};
    if (!loaded) return {};
    return SurfacePtr{SDL_ConvertSurface(loaded.get(), kTextureFormat)};
}

void PageAtlas::work(const std::stop_token& stop) {
    for (;;) {
        std::uint16_t page = 0;
        {
            std::unique_lock lock(mutex_);
            if (!wake_.wait(lock, stop, [&] { return !queue_.empty(); })) return;
            page = queue_.front();
            queue_.pop_front();
        }
        // Pages in the queue are only read here; their shadow list is fixed before streaming.
        float peak = -1;
        std::vector<std::uint64_t> opaque;
        SurfacePtr px = decode(pages_[page], &peak, opaque);
        const std::scoped_lock lock(mutex_);
        done_.push_back({page, std::move(px), peak, std::move(opaque)});
    }
}

void PageAtlas::upload(Page& p, int rows) {
    if (p.slot < 0) {
        p.slot = freeSlot(now_);
        if (p.slot < 0) {
            p.pixels.reset();
            p.state = State::Unloaded;
            return;
        }
        slotPage_[static_cast<std::size_t>(p.slot)] = static_cast<int>(&p - pages_.data());
    }
    SDL_Texture* tex = slots_[static_cast<std::size_t>(p.slot)].get();
    const int n = std::min(rows, p.h - p.uploadedRows);
    const SDL_Rect r{0, p.uploadedRows, p.w, n};
    const auto* src = static_cast<const std::uint8_t*>(p.pixels->pixels) +
                      static_cast<std::ptrdiff_t>(p.uploadedRows) * p.pixels->pitch;
    if (!SDL_UpdateTexture(tex, &r, src, p.pixels->pitch))
        SDL_Log("atlas: upload failed: %s", SDL_GetError());
    p.uploadedRows += n;
    ++uploads_;
    uploadedBytes_ += static_cast<std::size_t>(p.w) * static_cast<std::size_t>(n) * 4;
    if (p.uploadedRows < p.h) return;
    p.pixels.reset();
    p.texture = tex;
    p.state = State::Resident;
    p.lastUsed = now_;
    ++generation_;
}

void PageAtlas::updateHome() {
    Page& h = pages_[kHomePage];
    if (homeJob_.valid() &&
        (!async_ || homeJob_.wait_for(std::chrono::seconds(0)) == std::future_status::ready)) {
        homeWords_ = homeJob_.get();
        TexturePtr t;
        if (homeWords_ && homeWords_->w == h.w && homeWords_->h <= h.h)
            t.reset(SDL_CreateTexture(renderer_, slotFormat_, SDL_TEXTUREACCESS_TARGET, h.w, h.h));
        const SDL_FRect all{0, 0, static_cast<float>(h.w), static_cast<float>(h.h)};
        SDL_Texture* was = SDL_GetRenderTarget(renderer_);
        if (t && SDL_SetTextureBlendMode(h.texture, SDL_BLENDMODE_NONE) &&
            SDL_SetRenderTarget(renderer_, t.get()) &&
            SDL_RenderTexture(renderer_, h.texture, &all, &all) &&
            SDL_SetRenderTarget(renderer_, was) &&
            SDL_SetTextureBlendMode(h.texture, SDL_BLENDMODE_BLEND) &&
            SDL_SetTextureBlendMode(t.get(), SDL_BLENDMODE_BLEND)) {
            homeTarget_ = std::move(t);
            homeRows_ = 0;
        } else {
            SDL_Log("atlas: the home's packed page could not be made (%s); its colour is used",
                    SDL_GetError());
            if (!SDL_SetRenderTarget(renderer_, was)) SDL_Log("atlas: %s", SDL_GetError());
            h.packedFile.clear();
            homeWords_.reset();
        }
    }
    if (!homeTarget_ || !homeWords_) return;
    // Slices within the ahead budget (synchronous runs: all at once).
    const Uint64 t0 = SDL_GetPerformanceCounter();
    while (homeRows_ < homeWords_->h) {
        const int n = std::min(tuning::kUploadRows, homeWords_->h - homeRows_);
        const SDL_Rect r{0, homeRows_, h.w, n};
        if (!SDL_UpdateTexture(homeTarget_.get(), &r,
                               static_cast<const std::uint8_t*>(homeWords_->pixels) +
                                   static_cast<std::ptrdiff_t>(homeRows_) * homeWords_->pitch,
                               homeWords_->pitch))
            SDL_Log("atlas: upload failed: %s", SDL_GetError());
        homeRows_ += n;
        uploadedBytes_ += static_cast<std::size_t>(h.w) * static_cast<std::size_t>(n) * 4;
        if (async_ && msBetween(t0, SDL_GetPerformanceCounter()) >= tuning::kUploadMsAhead) break;
    }
    if (homeRows_ < homeWords_->h) return;
    h.homeArtRows = homeWords_->h;
    h.owned = std::move(homeTarget_);
    h.texture = h.owned.get();
    homeWords_.reset();
    ++generation_;
}

void PageAtlas::update(double now) {
    now_ = now;
    uploads_ = 0;
    uploadedBytes_ = 0;
    updateHome();
    // At most two pages between the disk and their slot (one uploading, one decoding): each
    // decoded page holds 64 MiB until it is uploaded.
    int inFlight = 0;
    for (const Page& p : pages_)
        inFlight +=
            p.state == State::Queued || p.state == State::Decoded || p.state == State::Uploading
                ? 1
                : 0;
    const auto start = [&](std::size_t i) {
        Page& p = pages_[i];
        ++inFlight;
        if (!async_) {
            p.pixels = decode(p, &p.shadowPeak, p.opaque);
            if (!p.pixels) return;
            p.uploadedRows = 0;
            upload(p, p.h);
            return;
        }
        p.state = State::Queued;
        const std::scoped_lock lock(mutex_);
        queue_.push_back(static_cast<std::uint16_t>(i));
        wake_.notify_one();
    };
    for (std::size_t i = 0; i < pages_.size(); ++i) {
        const Page& p = pages_[i];
        if (p.state != State::Unloaded || !p.wanted || p.w <= 0) continue;
        if (async_ && inFlight >= tuning::kPagesInFlight) break;
        start(i);
    }
    if (async_) {
        // With nothing the view needs left to load, pages load ahead into slots that are free:
        // never at the cost of a page that is resident.
        bool waiting = false;
        for (const Page& p : pages_)
            waiting =
                waiting || (p.wanted && p.state != State::Resident && p.state != State::Fixed);
        std::size_t held = 0;
        for (const Page& p : pages_)
            held += p.state != State::Fixed && p.state != State::Unloaded ? 1 : 0;
        for (std::size_t i = 0; i < pages_.size() && !waiting; ++i) {
            const Page& p = pages_[i];
            if (p.state != State::Unloaded || p.w <= 0) continue;
            if (inFlight >= tuning::kPagesInFlight || held >= slotLimit_) break;
            ++held;
            start(i);
        }
        {
            const std::scoped_lock lock(mutex_);
            for (Decoded& d : done_) {
                Page& p = pages_[d.page];
                p.pixels = std::move(d.pixels);
                p.shadowPeak = d.peak;
                p.opaque = std::move(d.opaque);
                p.uploadedRows = 0;
                p.state = p.pixels ? State::Decoded : State::Unloaded;
            }
            done_.clear();
        }
        // One page at a time, in slices, within a time budget per frame (at least one slice):
        // no frame blocks on a whole page. A page the view waits for goes first and faster.
        const Uint64 t0 = SDL_GetPerformanceCounter();
        for (;;) {
            Page* up = nullptr;
            for (Page& p : pages_)
                if (p.state == State::Uploading) up = &p;
            for (Page& p : pages_)
                if (up == nullptr && p.state == State::Decoded && p.wanted) up = &p;
            for (Page& p : pages_)
                if (up == nullptr && p.state == State::Decoded) up = &p;
            if (up == nullptr) break;
            up->state = State::Uploading;
            const double limit = up->wanted ? tuning::kUploadMsWanted : tuning::kUploadMsAhead;
            upload(*up, tuning::kUploadRows);
            if (msBetween(t0, SDL_GetPerformanceCounter()) >= limit) break;
        }
    }
    wantedPending_ = 0;
    for (Page& p : pages_) {
        if (p.wanted && p.state == State::Resident) p.lastUsed = now;
        if (p.wanted && p.state != State::Resident && p.state != State::Fixed && p.w > 0)
            ++wantedPending_;
    }
    // Only a view that needed more pages than the budget holds leaves anything to release.
    if (slots_.size() > slotLimit_) evict(now);
    for (Page& p : pages_) p.wanted = false;
}

void PageAtlas::evict(double now) {
    std::vector<PageUse> use;
    use.reserve(pages_.size());
    std::size_t fixed = 0;
    for (const Page& p : pages_) {
        const auto bytes = static_cast<std::size_t>(p.w) * static_cast<std::size_t>(p.h) * 4;
        if (p.state == State::Fixed) fixed += bytes;
        use.push_back({kSlotBytes, p.lastUsed, p.state == State::Resident, p.wanted});
    }
    const std::size_t budget = budget_ > fixed ? budget_ - fixed : 0;
    for (const int i : pagesToEvict(use, now, tuning::kPageIdleSeconds, budget)) {
        Page& p = pages_[static_cast<std::size_t>(i)];
        slotPage_[static_cast<std::size_t>(p.slot)] = -1;
        p.slot = -1;
        p.texture = nullptr;
        p.state = State::Unloaded;
        p.opaque = {};
    }
}

SDL_Texture* PageAtlas::texture(std::uint16_t page) const {
    const Page& p = pages_[page];
    p.lastUsed = now_;
    return p.state == State::Fixed || p.state == State::Resident ? p.texture : nullptr;
}

bool PageAtlas::setResident(std::string_view set) const {
    bool any = false;
    for (const Page& p : pages_) {
        if (p.set != set || p.state == State::Fixed) continue;
        if (p.state != State::Resident) return false;
        any = true;
    }
    return any;
}

float PageAtlas::shadowOpacity() const {
    float sum = 0;
    int n = 0;
    for (const Page& p : pages_)
        if (p.state == State::Resident && p.shadowPeak >= 0) {
            sum += p.shadowPeak;
            ++n;
        }
    return n > 0 ? sum / static_cast<float>(n) : tuning::kShadowOpacity;
}

PageStats PageAtlas::stats() const {
    // Texture memory: the fixed pages and every slot made (resident or free).
    PageStats s;
    s.uploads = uploads_;
    s.wanted = wantedPending_;
    s.budget = slotLimit_ * kSlotBytes;
    s.bytes = slots_.size() * kSlotBytes;
    for (const Page& p : pages_) {
        if (p.state == State::Fixed) {
            // The home page and the generated one are always there, in the budget too.
            const auto fixed = static_cast<std::size_t>(p.w) * static_cast<std::size_t>(p.h) * 4;
            s.bytes += fixed;
            s.budget += fixed;
        } else if (p.state == State::Resident)
            ++s.resident;
        else if (p.state != State::Unloaded)
            ++s.streaming;
    }
    return s;
}

} // namespace lc::worldview
