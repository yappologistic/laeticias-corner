#include "render/atlas.hpp"

#include "core/catalog.hpp"

#include <nlohmann/json.hpp>

#include <algorithm>
#include <cmath>
#include <optional>

namespace lc {
namespace {

struct Rgba {
    std::uint8_t r, g, b, a;
};

void put(SDL_Surface* s, int x, int y, Rgba c) {
    auto* row = static_cast<std::uint8_t*>(s->pixels) + static_cast<std::ptrdiff_t>(y) * s->pitch;
    std::uint8_t* px = row + static_cast<std::ptrdiff_t>(x) * 4;
    px[0] = c.r;
    px[1] = c.g;
    px[2] = c.b;
    px[3] = c.a;
}

std::uint8_t toByte(float v) {
    return static_cast<std::uint8_t>(std::lround(std::clamp(v, 0.0f, 1.0f) * 255.0f));
}

} // namespace

std::expected<AtlasManifest, std::string> parseAtlasManifest(std::string_view text) {
    try {
        const auto root = nlohmann::json::parse(text);
        if (root.value("version", 0) != 1) return std::unexpected("atlas: unsupported version");
        AtlasManifest m;
        m.image = root.value("image", std::string("atlas.png"));
        const auto& sprites = root.at("sprites");
        if (!sprites.is_object()) return std::unexpected("atlas: 'sprites' is not an object");
        for (const auto& [key, s] : sprites.items()) {
            // Whole numbers only (a float cast to int past its range is undefined), each within
            // its limit, so `x + w` and `y + h` can never wrap (a hand-edited manifest).
            const auto value = [&](const char* name, long long lo,
                                   long long hi) -> std::optional<int> {
                if (!s.is_object() || !s.contains(name) || !s[name].is_number_integer())
                    return std::nullopt;
                const auto& v = s[name];
                if (v.is_number_unsigned() && v.get<unsigned long long>() > 1ULL << 62)
                    return std::nullopt;
                const long long n = v.get<long long>();
                if (n < lo || n > hi) return std::nullopt;
                return static_cast<int>(n);
            };
            const auto x = value("x", 0, kAtlasMaxSide - 1);
            const auto y = value("y", 0, kAtlasMaxSide - 1);
            const auto w = value("w", 1, kAtlasMaxSide);
            const auto h = value("h", 1, kAtlasMaxSide);
            const auto ox = value("ox", -kAtlasMaxOffset, kAtlasMaxOffset);
            const auto oy = value("oy", -kAtlasMaxOffset, kAtlasMaxOffset);
            if (!x || !y || !w || !h || !ox || !oy) {
                m.refused.push_back(key + ": not whole numbers within the atlas's limits");
                continue;
            }
            m.sprites.emplace(key, SpriteRect{*x, *y, *w, *h, *ox, *oy});
        }
        return m;
    } catch (const nlohmann::json::exception& e) {
        return std::unexpected(std::string("atlas: ") + e.what());
    }
}

SpriteId Atlas::add(int x, int y, int w, int h, int ox, int oy) {
    rects_.push_back({x, y, w, h, ox, oy});
    sprites_.push_back({nullptr,
                        {},
                        static_cast<float>(w),
                        static_cast<float>(h),
                        static_cast<float>(ox),
                        static_cast<float>(oy)});
    return static_cast<SpriteId>(sprites_.size() - 1);
}

Atlas::Atlas(SDL_Renderer* renderer, const std::filesystem::path& assetsDir, Iso iso) : iso_(iso) {
    // Load what art exists; any failure degrades to placeholders.
    SurfacePtr art;
    AtlasManifest manifest;
    if (auto text = readTextFile(assetsDir / "atlas.json")) {
        if (auto m = parseAtlasManifest(*text)) {
            manifest = std::move(*m);
            const auto imagePath = (assetsDir / manifest.image).string();
            if (SurfacePtr loaded{SDL_LoadPNG(imagePath.c_str())}) {
                art.reset(SDL_ConvertSurface(loaded.get(), SDL_PIXELFORMAT_RGBA32));
            }
            if (!art) SDL_Log("atlas: cannot load %s: %s", imagePath.c_str(), SDL_GetError());
        } else {
            SDL_Log("%s", m.error().c_str());
        }
    } else {
        SDL_Log("atlas: %s; drawing placeholders", text.error().c_str());
    }

    // Engine sprites, in proportion to the tile cell so they match the art at any density.
    const int tw = static_cast<int>(iso.tileW());
    const int th = static_cast<int>(iso.tileH());
    const int boxW = std::max(4, tw / 2);
    const int boxH = std::max(6, th * 3 / 2);
    const int blob = std::max(16, 2 * tw);
    const int shW = std::max(6, tw * 7 / 16);
    const int shH = std::max(3, tw * 3 / 16);
    const int stripH = std::max({th, boxH, blob, shH});
    const int stripW = tw + 2 + boxW + 2 + blob + 2 + shW;

    const int artW = art ? art->w : 0;
    const int artH = art ? art->h : 0;
    const int width = std::max(artW, stripW);
    const int stripY = artH;
    pixels_.reset(SDL_CreateSurface(width, artH + stripH, SDL_PIXELFORMAT_RGBA32));
    if (!pixels_) {
        SDL_Log("atlas: cannot create surface: %s", SDL_GetError());
        return;
    }
    if (!SDL_ClearSurface(pixels_.get(), 0, 0, 0, 0)) SDL_Log("atlas: %s", SDL_GetError());
    std::size_t artCount = 0;
    if (art) {
        if (!SDL_SetSurfaceBlendMode(art.get(), SDL_BLENDMODE_NONE) ||
            !SDL_BlitSurface(art.get(), nullptr, pixels_.get(), nullptr)) {
            SDL_Log("atlas: blit failed: %s", SDL_GetError());
        }
        for (const std::string& why : manifest.refused)
            SDL_Log("atlas: sprite %s; drawn as a placeholder", why.c_str());
        for (const auto& [key, r] : manifest.sprites) {
            // In 64 bits: the parse bounds each value, and this stays right whatever it allows.
            if (static_cast<long long>(r.x) + r.w > artW ||
                static_cast<long long>(r.y) + r.h > artH) {
                SDL_Log("atlas: sprite '%s' lies outside the image; ignored", key.c_str());
                continue;
            }
            byKey_.emplace(key, add(r.x, r.y, r.w, r.h, r.ox, r.oy));
        }
        artCount = byKey_.size();
    }

    SDL_Surface* s = pixels_.get();
    int x = 0;
    // Placeholder diamond, rasterised like ground tiles: loud magenta checker so missing art is
    // obvious.
    const int hw = tw / 2;
    const int hh = th / 2;
    placeholderTile_ = add(x, stripY, tw, th, hw, 0);
    placeholderEdgeSE_ = add(x, stripY, tw, th, 0, -hh);
    placeholderEdgeSW_ = add(x, stripY, tw, th, tw, -hh);
    for (int y = 0; y < th; ++y) {
        const int row = y < hh ? y : th - 1 - y;
        const int half = 2 * row + 1; // 2, 6, 10 ... px wide rows, mirrored
        for (int px = hw - half; px < hw + half; ++px) {
            if (px < 1 || px >= tw - 1) continue;
            const bool check = ((px * 8 / tw) + (y * 4 / th)) % 2 == 0;
            put(s, x + px, stripY + y, check ? Rgba{255, 0, 220, 255} : Rgba{40, 0, 40, 255});
        }
    }
    x += tw + 2;
    placeholderBox_ = add(x, stripY, boxW, boxH, boxW / 2, boxH * 3 / 4);
    for (int y = 0; y < boxH; ++y) {
        for (int px = 0; px < boxW; ++px) {
            const bool edge = px == 0 || y == 0 || px == boxW - 1 || y == boxH - 1;
            const bool check = ((px * 4 / boxW) + (y * 6 / boxH)) % 2 == 0;
            put(s, x + px, stripY + y,
                edge ? Rgba{40, 0, 40, 255}
                     : (check ? Rgba{255, 0, 220, 255} : Rgba{90, 0, 90, 255}));
        }
    }
    x += boxW + 2;
    const float br = static_cast<float>(blob) * 0.5f;
    lightBlob_ = add(x, stripY, blob, blob, blob / 2, blob / 2);
    for (int y = 0; y < blob; ++y) {
        for (int px = 0; px < blob; ++px) {
            const float dx = (static_cast<float>(px) + 0.5f - br) / br;
            const float dy = (static_cast<float>(y) + 0.5f - br) / br;
            const float k = std::max(0.0f, 1.0f - std::sqrt(dx * dx + dy * dy));
            put(s, x + px, stripY + y, {255, 255, 255, toByte(k * k * (3 - 2 * k))});
        }
    }
    x += blob + 2;
    softShadow_ = add(x, stripY, shW, shH, shW / 2, shH / 2);
    for (int y = 0; y < shH; ++y) {
        for (int px = 0; px < shW; ++px) {
            const float dx = (static_cast<float>(px) + 0.5f - static_cast<float>(shW) * 0.5f) /
                             (static_cast<float>(shW) * 0.5f);
            const float dy = (static_cast<float>(y) + 0.5f - static_cast<float>(shH) * 0.5f) /
                             (static_cast<float>(shH) * 0.5f);
            const float k = std::max(0.0f, 1.0f - (dx * dx + dy * dy));
            put(s, x + px, stripY + y, {0, 0, 0, toByte(std::min(1.0f, k * 1.6f))});
        }
    }

    luma_.resize(sprites_.size());
    for (std::size_t i = 0; i < sprites_.size(); ++i) {
        const auto& r = rects_[i];
        double sum = 0;
        double weight = 0;
        for (int y = 0; y < r.h; ++y) {
            const auto* row = static_cast<const std::uint8_t*>(s->pixels) +
                              static_cast<std::ptrdiff_t>(r.y + y) * s->pitch;
            for (int px = 0; px < r.w; ++px) {
                const std::uint8_t* p = row + static_cast<std::ptrdiff_t>(r.x + px) * 4;
                const double a = p[3] / 255.0;
                sum += a * (0.2126 * p[0] + 0.7152 * p[1] + 0.0722 * p[2]) / 255.0;
                weight += a;
            }
        }
        luma_[i] = weight > 0 ? static_cast<float>(sum / weight) : 0.0f;
    }

    // The pixels stay RGBA for the CPU-side work; the texture gets the shared fast layout.
    texture_ = uploadTexture(renderer, s);
    if (!texture_) return;
    const auto fw = static_cast<float>(s->w);
    const auto fh = static_cast<float>(s->h);
    for (std::size_t i = 0; i < sprites_.size(); ++i) {
        const auto& r = rects_[i];
        sprites_[i].texture = texture_.get();
        sprites_[i].uv = {static_cast<float>(r.x) / fw, static_cast<float>(r.y) / fh,
                          static_cast<float>(r.x + r.w) / fw, static_cast<float>(r.y + r.h) / fh};
    }
    SDL_Log("atlas: %zu sprites loaded", artCount);
}

std::size_t Atlas::textureBytes() const {
    return pixels_ ? static_cast<std::size_t>(pixels_->w) * static_cast<std::size_t>(pixels_->h) * 4
                   : 0;
}

std::optional<SpriteId> Atlas::find(std::string_view key) const {
    const auto it = byKey_.find(std::string(key));
    if (it == byKey_.end()) return std::nullopt;
    return it->second;
}

SpriteId Atlas::resolve(std::string_view key, SpriteId placeholder) {
    if (const auto id = find(key)) return *id;
    reportMissing(key);
    return placeholder;
}

void Atlas::reportMissing(std::string_view key) {
    if (logged_.emplace(key).second)
        SDL_Log("atlas: missing sprite '%.*s'", static_cast<int>(key.size()), key.data());
}

std::uint8_t Atlas::alphaAt(int x, int y) const {
    const auto* row = static_cast<const std::uint8_t*>(pixels_->pixels) +
                      static_cast<std::ptrdiff_t>(y) * pixels_->pitch;
    return row[static_cast<std::ptrdiff_t>(x) * 4 + 3];
}

std::optional<Vec2> Atlas::alphaCentroid(SpriteId id) const {
    if (!pixels_) return std::nullopt;
    const auto& r = rects_[id];
    double sx = 0;
    double sy = 0;
    double sum = 0;
    for (int y = 0; y < r.h; ++y) {
        for (int x = 0; x < r.w; ++x) {
            const double a = alphaAt(r.x + x, r.y + y);
            sx += a * (x + 0.5);
            sy += a * (y + 0.5);
            sum += a;
        }
    }
    if (sum <= 0) return std::nullopt;
    return Vec2{static_cast<float>(sx / sum) - static_cast<float>(r.ox),
                static_cast<float>(sy / sum) - static_cast<float>(r.oy)};
}

float Atlas::normalizeAlpha(SpriteId id) {
    const auto& r = rects_[id];
    const auto key = (static_cast<std::uint64_t>(r.x) << 32) | static_cast<std::uint32_t>(r.y);
    if (const auto it = normalized_.find(key); it != normalized_.end()) return it->second;
    if (!pixels_ || !texture_) return 1.0f;
    std::uint8_t peak = 0;
    for (int y = 0; y < r.h; ++y)
        for (int x = 0; x < r.w; ++x) peak = std::max(peak, alphaAt(r.x + x, r.y + y));
    normalized_.emplace(key, static_cast<float>(peak) / 255.0f);
    if (peak == 0 || peak == 255) return static_cast<float>(peak) / 255.0f;
    auto* base = static_cast<std::uint8_t*>(pixels_->pixels);
    for (int y = 0; y < r.h; ++y) {
        std::uint8_t* row = base + static_cast<std::ptrdiff_t>(r.y + y) * pixels_->pitch;
        for (int x = 0; x < r.w; ++x) {
            std::uint8_t& a = row[static_cast<std::ptrdiff_t>(r.x + x) * 4 + 3];
            a = static_cast<std::uint8_t>(std::min(255, a * 255 / peak));
        }
    }
    const SDL_Rect rect{r.x, r.y, r.w, r.h};
    const auto* first = base + static_cast<std::ptrdiff_t>(r.y) * pixels_->pitch +
                        static_cast<std::ptrdiff_t>(r.x) * 4;
    std::vector<std::uint8_t> converted(static_cast<std::size_t>(r.w * r.h * 4));
    if (!SDL_ConvertPixels(r.w, r.h, SDL_PIXELFORMAT_RGBA32, first, pixels_->pitch, kTextureFormat,
                           converted.data(), r.w * 4) ||
        !SDL_UpdateTexture(texture_.get(), &rect, converted.data(), r.w * 4))
        SDL_Log("atlas: %s", SDL_GetError());
    return static_cast<float>(peak) / 255.0f;
}

} // namespace lc
