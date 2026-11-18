#include "worldview/overview.hpp"

#include "worldview/tuning.hpp"

#include <algorithm>
#include <array>
#include <cmath>

namespace lc::worldview {
namespace {

constexpr int kUploadRows = 256; // rows of the overview uploaded per frame
constexpr float kFaceShade = 0.72f;
constexpr std::array<float, 3> kPlaceholderColour{0.69f, 0.63f, 0.55f};

using Colour = std::array<float, 3>;

struct Request {
    SDL_Rect rect;
    std::size_t out;
};

std::uint32_t pack(Colour c) {
    const auto b = [](float v) {
        return static_cast<std::uint32_t>(std::lround(std::clamp(v, 0.0f, 1.0f) * 255.0f));
    };
    return 0xFF000000u | (b(c[0]) << 16) | (b(c[1]) << 8) | b(c[2]);
}

Colour scaled(Colour c, float k) {
    return {c[0] * k, c[1] * k, c[2] * k};
}

// Alpha-weighted mean colours of sprite rects, one decoded page at a time.
class Means {
public:
    explicit Means(const PageAtlas& pages) : pages_(pages), requests_(pages.pageCount()) {}

    std::size_t add(const SpriteRef& s) {
        const auto [pw, ph] = pages_.pageSize(s.page);
        const std::size_t out = colours_.size();
        colours_.push_back({-1, -1, -1});
        requests_[s.page].push_back(
            {{static_cast<int>(std::lround(s.uv.u0 * static_cast<float>(pw))),
              static_cast<int>(std::lround(s.uv.v0 * static_cast<float>(ph))),
              static_cast<int>(s.w), static_cast<int>(s.h)},
             out});
        return out;
    }

    void run() {
        for (std::size_t p = 0; p < requests_.size(); ++p) {
            if (requests_[p].empty()) continue;
            const SurfacePtr px = pages_.decodePage(static_cast<std::uint16_t>(p));
            if (!px) continue;
            for (const Request& r : requests_[p]) {
                double sum[3] = {0, 0, 0};
                double weight = 0;
                for (int y = r.rect.y; y < r.rect.y + r.rect.h && y < px->h; ++y) {
                    const auto* row = reinterpret_cast<const std::uint32_t*>(
                        static_cast<const std::uint8_t*>(px->pixels) +
                        static_cast<std::ptrdiff_t>(y) * px->pitch);
                    for (int x = r.rect.x; x < r.rect.x + r.rect.w && x < px->w; ++x) {
                        const std::uint32_t v = row[x];
                        const double a = static_cast<double>(v >> 24) / 255.0;
                        sum[0] += a * static_cast<double>((v >> 16) & 0xFF);
                        sum[1] += a * static_cast<double>((v >> 8) & 0xFF);
                        sum[2] += a * static_cast<double>(v & 0xFF);
                        weight += a;
                    }
                }
                if (weight > 0)
                    colours_[r.out] = {static_cast<float>(sum[0] / weight / 255.0),
                                       static_cast<float>(sum[1] / weight / 255.0),
                                       static_cast<float>(sum[2] / weight / 255.0)};
            }
        }
    }

    [[nodiscard]] bool has(std::size_t i) const { return colours_[i][0] >= 0; }
    [[nodiscard]] Colour get(std::size_t i) const { return colours_[i]; }

private:
    const PageAtlas& pages_;
    std::vector<std::vector<Request>> requests_;
    std::vector<Colour> colours_;
};

} // namespace

OverviewImage makeOverview(const world::WorldMap& map, const WorldSprites& sprites,
                           const PageAtlas& pages) {
    const Iso iso = map.content().home().iso();
    const int lvl = map.content().tileLevel();
    constexpr int D = tuning::kOverviewDivisor;
    const int gw = map.width();
    const int gh = map.height();

    // Colours: terrain from its art (the full overlay or the first base variant), items from
    // their sprite; the catalog's colour where there is no art.
    Means means(pages);
    std::vector<std::size_t> terrainReq(map.terrainCount(), SIZE_MAX);
    std::vector<Colour> terrainFlat(map.terrainCount());
    for (std::size_t t = 0; t < map.terrainCount(); ++t) {
        const TerrainLook& l = sprites.terrain(static_cast<int>(t));
        const bool overlay = !map.terrainInfo(static_cast<int>(t)).base;
        terrainFlat[t] = {l.flat.r, l.flat.g, l.flat.b};
        if (overlay && l.hasOverlay())
            terrainReq[t] = means.add(l.overlay[15].f.front());
        else if (!overlay && !l.base.empty())
            terrainReq[t] = means.add(l.base.front());
    }
    const auto items = map.items();
    std::vector<std::size_t> itemReq(items.size(), SIZE_MAX);
    std::vector<int> itemRaise(items.size(), 0);
    for (std::size_t i = 0; i < items.size(); ++i) {
        const VariantLook& look = sprites.item(items[i]);
        const SpriteRef& s = look.pieces.empty() ? look.base.f.front() : look.pieces.front();
        itemRaise[i] = std::clamp(static_cast<int>(s.oy) / D, 0, 15);
        if (look.look != Look::Placeholder && s.page != PageAtlas::kGeneratedPage)
            itemReq[i] = means.add(s);
    }
    means.run();
    const auto terrainColour = [&](int t) {
        const std::size_t r = terrainReq[static_cast<std::size_t>(t)];
        return r != SIZE_MAX && means.has(r) ? means.get(r)
                                             : terrainFlat[static_cast<std::size_t>(t)];
    };

    OverviewImage img;
    const int raiseMax = (15 * lvl) / D + 16;
    img.scale = 1.0f / static_cast<float>(D);
    img.origin = {-static_cast<float>(gh) * iso.hw, -static_cast<float>(raiseMax * D)};
    img.w = static_cast<int>((static_cast<float>(gw + gh) * iso.hw) / static_cast<float>(D)) + 4;
    img.h = static_cast<int>((static_cast<float>(gw + gh) * iso.hh) / static_cast<float>(D)) +
            raiseMax + 4;
    img.pixels.assign(static_cast<std::size_t>(img.w) * static_cast<std::size_t>(img.h), 0);
    const int tw = std::max(2, static_cast<int>(2 * iso.hw) / D);
    const int th = std::max(1, static_cast<int>(2 * iso.hh) / D);
    const auto levelAt = [&](int x, int y) {
        return x < 0 || y < 0 || x >= gw || y >= gh || map.terrainAt({x, y}) == world::kNone
                   ? 0
                   : map.level({x, y});
    };
    // Back to front along the diagonals, so raised tiles hide what lies behind them.
    for (int s = 0; s <= gw + gh - 2; ++s)
        for (int tx = std::max(0, s - (gh - 1)); tx <= std::min(gw - 1, s); ++tx) {
            const TilePos p{tx, s - tx};
            const int t = map.terrainAt(p);
            if (t == world::kNone) continue;
            const int level = map.level(p);
            Colour c = terrainColour(t);
            if (sprites.terrain(t).water)
                c = scaled(c, 1.0f - tuning::kWaterDepthTint *
                                         static_cast<float>(world::auxOf(map.levelByte(p))));
            int raise = level * lvl / D;
            if (const int i = map.itemAt(p); i >= 0) {
                const auto k = static_cast<std::size_t>(i);
                if (itemReq[k] != SIZE_MAX && means.has(itemReq[k]))
                    c = means.get(itemReq[k]);
                else if (sprites.item(items[k]).look == Look::Placeholder)
                    c = kPlaceholderColour;
                raise += itemRaise[k];
            }
            // Light from the upper left: brighter where the tile stands above its back neighbours.
            const float lit =
                1.0f +
                0.05f * static_cast<float>(std::clamp(level - levelAt(p.x - 1, p.y), -3, 3)) +
                0.03f * static_cast<float>(std::clamp(level - levelAt(p.x, p.y - 1), -3, 3));
            const std::uint32_t top = pack(scaled(c, lit));
            const std::uint32_t side = pack(scaled(c, lit * kFaceShade));
            const Vec2 w = iso.toWorld(p);
            const int cx = static_cast<int>((w.x - img.origin.x) / static_cast<float>(D));
            const int cy = static_cast<int>((w.y - img.origin.y) / static_cast<float>(D)) - raise;
            for (int y = cy; y < cy + th + raise; ++y) {
                if (y < 0 || y >= img.h) continue;
                for (int x = cx - tw / 2; x < cx + tw / 2; ++x) {
                    if (x < 0 || x >= img.w) continue;
                    img.pixels[static_cast<std::size_t>(y) * static_cast<std::size_t>(img.w) +
                               static_cast<std::size_t>(x)] = y < cy + th ? top : side;
                }
            }
        }
    return img;
}

Overview::Overview(const world::WorldMap& map, const WorldSprites& sprites, const PageAtlas& pages,
                   bool async) {
    if (!async) {
        image_ = makeOverview(map, sprites, pages);
        ready_ = true;
        return;
    }
    worker_ = std::jthread([this, &map, &sprites, &pages] {
        image_ = makeOverview(map, sprites, pages);
        ready_.store(true, std::memory_order_release);
    });
}

bool Overview::upload(SDL_Renderer* renderer) {
    if (complete_ || !ready_.load(std::memory_order_acquire)) return complete_;
    if (!texture_) {
        texture_.reset(SDL_CreateTexture(renderer, kTextureFormat, uploadAccess(renderer), image_.w,
                                         image_.h));
        if (!texture_ || !SDL_SetTextureBlendMode(texture_.get(), SDL_BLENDMODE_BLEND)) {
            SDL_Log("overview: %s", SDL_GetError());
            texture_.reset();
            return false;
        }
    }
    const int n = std::min(kUploadRows, image_.h - uploaded_);
    const SDL_Rect r{0, uploaded_, image_.w, n};
    if (!SDL_UpdateTexture(texture_.get(), &r,
                           image_.pixels.data() + static_cast<std::size_t>(uploaded_) *
                                                      static_cast<std::size_t>(image_.w),
                           image_.w * 4))
        SDL_Log("overview: %s", SDL_GetError());
    uploaded_ += n;
    complete_ = uploaded_ >= image_.h;
    if (complete_) {
        // The pixels live on in the texture only.
        image_.pixels.clear();
        image_.pixels.shrink_to_fit();
    }
    return complete_;
}

std::size_t Overview::bytes() const {
    return static_cast<std::size_t>(image_.w) * static_cast<std::size_t>(image_.h) * 4;
}

} // namespace lc::worldview
