#include "worldview/page_atlas.hpp"

#include "platform/process.hpp"
#include "worldview/cells.hpp"
#include "worldview/tuning.hpp"

#include <algorithm>
#include <array>
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

PageAtlas::PageAtlas(SDL_Renderer* renderer, const Atlas& home, const world::AtlasPages& pages,
                     std::filesystem::path atlasDir, bool async, std::size_t budget)
    : renderer_(renderer), home_(home), index_(pages), async_(async), budget_(budget) {

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
    pages_.push_back(std::move(h));
    Page g;
    g.set = "generated";
    g.state = State::Fixed;
    pages_.push_back(std::move(g));
    for (const world::AtlasPage& ap : pages.pages()) {
        Page p;
        p.set = ap.set;
        p.file = atlasDir / ap.image;
        p.own = ap.index < 0;
        p.scale = ap.scale;
        if (const auto size = pngSize(p.file)) {
            p.w = size->first;
            p.h = size->second;
        } else {
            SDL_Log("atlas: cannot read %s; its sprites are skipped", p.file.string().c_str());
        }
        pages_.push_back(std::move(p));
    }
    // While the ceiling holds every page on disk, each has a texture of its own size (a page is
    // seldom a full 4096 x 4096) and nothing is ever given up: pages the view does not need yet
    // load ahead in the background, and a journey to any city finds its art resident. Sets that
    // outgrow the ceiling stream through equal slots instead, least recently used out first; a
    // view always gets what it needs (freeSlot). The shadow pages (a set's shadows at half
    // size) are small and always kept.
    const auto bytesOf = [](const Page& p) {
        return static_cast<std::size_t>(p.w) * static_cast<std::size_t>(p.h) * 4;
    };
    std::size_t fixed = bytesOf(pages_[kHomePage]);
    std::size_t colour = 0;
    std::size_t need = 0;
    for (const Page& p : pages_) {
        if (p.state == State::Fixed) continue;
        (p.own ? fixed : colour) += bytesOf(p);
        need += p.own ? 0 : 1;
    }
    if (fixed + colour <= budget_) {
        for (Page& p : pages_) p.own = p.state != State::Fixed;
        slotLimit_ = 0;
        budget_ = fixed + colour;
    } else {
        const std::size_t room = budget_ > fixed ? (budget_ - fixed) / kSlotBytes : 1;
        slotLimit_ = std::clamp<std::size_t>(need, 1, std::max<std::size_t>(1, room));
        budget_ = fixed + slotLimit_ * kSlotBytes;
    }
    if (async_) {
        for (Page& p : pages_)
            if (p.own && p.w > 0) p.owned = makeTexture(p.w, p.h);
        for (std::size_t i = 0; i < slotLimit_; ++i)
            if (makeSlot() < 0) break;
        worker_ = std::jthread([this](const std::stop_token& st) { work(st); });
    }
}

TexturePtr PageAtlas::makeTexture(int w, int h) {
    TexturePtr t{SDL_CreateTexture(renderer_, kTextureFormat, uploadAccess(renderer_), w, h)};
    if (!t || !SDL_SetTextureBlendMode(t.get(), SDL_BLENDMODE_BLEND)) {
        SDL_Log("atlas: cannot create a page texture: %s", SDL_GetError());
        return {};
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
    return t;
}

int PageAtlas::makeSlot() {
    TexturePtr t = makeTexture(world::kMaxPageSide, world::kMaxPageSide);
    if (!t) return -1;
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
        return SpriteRef{kHomePage, s.uv, s.w, s.h, s.ox, s.oy};
    }
    const world::PageSprite* ps = index_.find(key);
    if (ps == nullptr) return std::nullopt;
    const auto page = static_cast<std::uint16_t>(ps->page + 2);
    if (pages_[page].w <= 0 || pages_[page].h <= 0) return std::nullopt;
    const auto [fw, fh] = textureSize(pages_[page]);
    return SpriteRef{page,
                     {ps->x / fw, ps->y / fh, (ps->x + ps->w) / fw, (ps->y + ps->h) / fh},
                     static_cast<float>(ps->w),
                     static_cast<float>(ps->h),
                     static_cast<float>(ps->ox),
                     static_cast<float>(ps->oy)};
}

std::optional<SpriteRef> PageAtlas::findShadow(std::string_view key) const {
    const world::PageSprite* ps = index_.findShadow(key);
    if (ps == nullptr) return std::nullopt;
    const auto page = static_cast<std::uint16_t>(ps->page + 2);
    const Page& p = pages_[page];
    if (p.w <= 0 || p.h <= 0) return std::nullopt;
    const auto fw = static_cast<float>(p.w);
    const auto fh = static_cast<float>(p.h);
    const float k = 1.0f / p.scale; // world px per texel of the page
    return SpriteRef{page,
                     {ps->x / fw, ps->y / fh, (ps->x + ps->w) / fw, (ps->y + ps->h) / fh},
                     static_cast<float>(ps->w) * k,
                     static_cast<float>(ps->h) * k,
                     static_cast<float>(ps->ox) * k,
                     static_cast<float>(ps->oy) * k};
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
    const auto [fw, fh] = textureSize(p);
    p.shadows.push_back({static_cast<int>(std::lround(s.uv.u0 * fw)),
                         static_cast<int>(std::lround(s.uv.v0 * fh)),
                         static_cast<int>(std::lround(s.w * p.scale)),
                         static_cast<int>(std::lround(s.h * p.scale))});
}

void PageAtlas::want(std::string_view set) {
    for (Page& p : pages_)
        if (p.state != State::Fixed && p.set == set) p.wanted = true;
}

SurfacePtr PageAtlas::decode(const Page& p, float* peak, std::vector<std::uint64_t>& opaque) const {
    SurfacePtr loaded{SDL_LoadPNG(p.file.string().c_str())};
    SurfacePtr px;
    if (loaded) px.reset(SDL_ConvertSurface(loaded.get(), kTextureFormat));
    if (!px) {
        SDL_Log("atlas: cannot decode %s: %s", p.file.string().c_str(), SDL_GetError());
        return px;
    }
    // ARGB8888: alpha is the top byte of each 32-bit pixel.
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
    // What is drawn where, a bit per pixel: picking asks it (draw-order.md 4.5). Nobody picks
    // a shadow.
    if (p.own) return px;
    const auto words = static_cast<std::size_t>((px->w + 63) / 64);
    opaque.assign(words * static_cast<std::size_t>(px->h), 0);
    for (int y = 0; y < px->h; ++y) {
        const auto* row =
            reinterpret_cast<const std::uint32_t*>(static_cast<const std::uint8_t*>(px->pixels) +
                                                   static_cast<std::ptrdiff_t>(y) * px->pitch);
        std::uint64_t* bits = opaque.data() + static_cast<std::size_t>(y) * words;
        for (int x = 0; x < px->w; ++x)
            if ((row[x] >> 24) != 0) bits[x >> 6] |= std::uint64_t{1} << (x & 63);
    }
    return px;
}

bool PageAtlas::drawsAt(const SpriteRef& s, float x, float y) const {
    if (s.page >= pages_.size()) return true;
    const Page& p = pages_[s.page];
    if (p.opaque.empty() || p.w <= 0 || p.h <= 0) return true;
    const auto [fw, fh] = textureSize(p);
    const int px = static_cast<int>(std::floor(s.uv.u0 * fw + x));
    const int py = static_cast<int>(std::floor(s.uv.v0 * fh + y));
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
    if (p.own && !p.owned) p.owned = makeTexture(p.w, p.h); // synchronous runs: when needed
    if (p.own && !p.owned) {
        p.pixels.reset();
        p.state = State::Unloaded;
        return;
    }
    if (!p.own && p.slot < 0) {
        p.slot = freeSlot(now_);
        if (p.slot < 0) {
            p.pixels.reset();
            p.state = State::Unloaded;
            return;
        }
        slotPage_[static_cast<std::size_t>(p.slot)] = static_cast<int>(&p - pages_.data());
    }
    SDL_Texture* tex = p.own ? p.owned.get() : slots_[static_cast<std::size_t>(p.slot)].get();
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

void PageAtlas::update(double now) {
    now_ = now;
    uploads_ = 0;
    uploadedBytes_ = 0;
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
            held += p.state != State::Fixed && p.state != State::Unloaded && !p.own ? 1 : 0;
        for (std::size_t i = 0; i < pages_.size() && !waiting; ++i) {
            const Page& p = pages_[i];
            if (p.state != State::Unloaded || p.w <= 0) continue;
            if (inFlight >= tuning::kPagesInFlight) break;
            if (!p.own && held >= slotLimit_) continue; // no slot free for it
            held += p.own ? 0 : 1;
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
        if (p.state == State::Fixed || p.own) fixed += bytes;
        // A page with a texture of its own is never given up: it is not among what may go.
        use.push_back({kSlotBytes, p.lastUsed, p.state == State::Resident && !p.own, p.wanted});
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
        if (p.state == State::Fixed || p.own) {
            // The home page, the generated one and pages with their own textures are there, in the
            // budget too.
            const auto fixed = static_cast<std::size_t>(p.w) * static_cast<std::size_t>(p.h) * 4;
            s.bytes += p.state == State::Fixed || p.owned ? fixed : 0;
            s.budget += fixed;
        }
        if (p.state == State::Fixed) continue;
        if (p.state == State::Resident)
            ++s.resident;
        else if (p.state != State::Unloaded)
            ++s.streaming;
    }
    return s;
}

} // namespace lc::worldview
