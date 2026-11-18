#include "worldview/page_atlas.hpp"

#include "worldview/cells.hpp"
#include "worldview/tuning.hpp"

#include <algorithm>
#include <array>
#include <fstream>

namespace lc::worldview {

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
        if (const auto size = pngSize(p.file)) {
            p.w = size->first;
            p.h = size->second;
        } else {
            SDL_Log("atlas: cannot read %s; its sprites are skipped", p.file.string().c_str());
        }
        pages_.push_back(std::move(p));
    }
    if (async_) worker_ = std::jthread([this](const std::stop_token& st) { work(st); });
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
    const Page& p = pages_[page];
    if (p.w <= 0 || p.h <= 0) return std::nullopt;
    const auto fw = static_cast<float>(p.w);
    const auto fh = static_cast<float>(p.h);
    return SpriteRef{page,
                     {ps->x / fw, ps->y / fh, (ps->x + ps->w) / fw, (ps->y + ps->h) / fh},
                     static_cast<float>(ps->w),
                     static_cast<float>(ps->h),
                     static_cast<float>(ps->ox),
                     static_cast<float>(ps->oy)};
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
    const auto fw = static_cast<float>(p.w);
    const auto fh = static_cast<float>(p.h);
    p.shadows.push_back({static_cast<int>(std::lround(s.uv.u0 * fw)),
                         static_cast<int>(std::lround(s.uv.v0 * fh)), static_cast<int>(s.w),
                         static_cast<int>(s.h)});
}

void PageAtlas::want(std::string_view set) {
    for (Page& p : pages_)
        if (p.state != State::Fixed && p.set == set) p.wanted = true;
}

SurfacePtr PageAtlas::decode(const Page& p, float* peak) const {
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
    return px;
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
        SurfacePtr px = decode(pages_[page], &peak);
        const std::scoped_lock lock(mutex_);
        done_.push_back({page, std::move(px), peak});
    }
}

void PageAtlas::upload(Page& p, int rows) {
    if (!p.owned) {
        p.owned.reset(
            SDL_CreateTexture(renderer_, kTextureFormat, SDL_TEXTUREACCESS_STREAMING, p.w, p.h));
        if (!p.owned || !SDL_SetTextureBlendMode(p.owned.get(), SDL_BLENDMODE_BLEND)) {
            SDL_Log("atlas: cannot create a page texture: %s", SDL_GetError());
            p.owned.reset();
            p.pixels.reset();
            p.state = State::Unloaded;
            return;
        }
    }
    const int n = std::min(rows, p.h - p.uploadedRows);
    const SDL_Rect r{0, p.uploadedRows, p.w, n};
    const auto* src = static_cast<const std::uint8_t*>(p.pixels->pixels) +
                      static_cast<std::ptrdiff_t>(p.uploadedRows) * p.pixels->pitch;
    if (!SDL_UpdateTexture(p.owned.get(), &r, src, p.pixels->pitch))
        SDL_Log("atlas: upload failed: %s", SDL_GetError());
    p.uploadedRows += n;
    ++uploads_;
    if (p.uploadedRows < p.h) return;
    p.pixels.reset();
    p.texture = p.owned.get();
    p.state = State::Resident;
    p.lastUsed = now_;
    ++generation_;
}

void PageAtlas::update(double now) {
    now_ = now;
    uploads_ = 0;
    for (std::size_t i = 0; i < pages_.size(); ++i) {
        Page& p = pages_[i];
        if (p.state != State::Unloaded || !p.wanted || p.w <= 0) continue;
        if (!async_) {
            p.pixels = decode(p, &p.shadowPeak);
            if (!p.pixels) continue;
            p.uploadedRows = 0;
            upload(p, p.h);
            continue;
        }
        p.state = State::Queued;
        const std::scoped_lock lock(mutex_);
        queue_.push_back(static_cast<std::uint16_t>(i));
        wake_.notify_one();
    }
    if (async_) {
        {
            const std::scoped_lock lock(mutex_);
            for (Decoded& d : done_) {
                Page& p = pages_[d.page];
                p.pixels = std::move(d.pixels);
                p.shadowPeak = d.peak;
                p.uploadedRows = 0;
                p.state = p.pixels ? State::Decoded : State::Unloaded;
            }
            done_.clear();
        }
        // One page at a time, a slice per frame, so no frame blocks on a whole page.
        Page* up = nullptr;
        for (Page& p : pages_)
            if (p.state == State::Uploading) up = &p;
        for (Page& p : pages_)
            if (up == nullptr && p.state == State::Decoded) {
                p.state = State::Uploading;
                up = &p;
            }
        if (up != nullptr) upload(*up, tuning::kUploadRowsPerFrame);
    }
    for (Page& p : pages_)
        if (p.wanted && p.state == State::Resident) p.lastUsed = now;
    evict(now);
    for (Page& p : pages_) p.wanted = false;
}

void PageAtlas::evict(double now) {
    std::vector<PageUse> use;
    use.reserve(pages_.size());
    std::size_t fixed = 0;
    for (const Page& p : pages_) {
        const auto bytes = static_cast<std::size_t>(p.w) * static_cast<std::size_t>(p.h) * 4;
        if (p.state == State::Fixed) fixed += bytes;
        use.push_back({bytes, p.lastUsed, p.state == State::Resident, p.wanted});
    }
    const std::size_t budget = budget_ > fixed ? budget_ - fixed : 0;
    for (const int i : pagesToEvict(use, now, tuning::kPageIdleSeconds, budget)) {
        Page& p = pages_[static_cast<std::size_t>(i)];
        p.owned.reset();
        p.texture = nullptr;
        p.state = State::Unloaded;
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
    PageStats s;
    s.uploads = uploads_;
    for (const Page& p : pages_) {
        const auto bytes = static_cast<std::size_t>(p.w) * static_cast<std::size_t>(p.h) * 4;
        switch (p.state) {
        case State::Fixed: s.bytes += bytes; break;
        case State::Resident:
            s.bytes += bytes;
            ++s.resident;
            break;
        case State::Uploading:
            s.bytes += bytes;
            ++s.streaming;
            break;
        case State::Queued:
        case State::Decoded: ++s.streaming; break;
        case State::Unloaded: break;
        }
    }
    return s;
}

} // namespace lc::worldview
