#include "render/atlas.hpp"

#include "core/catalog.hpp"

#include <nlohmann/json.hpp>

#include <algorithm>
#include <cmath>

namespace lc {
namespace {

constexpr int kStripHeight = 64;
constexpr int kStripMinWidth = 192;

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
        for (const auto& [key, s] : root.at("sprites").items()) {
            SpriteRect r{s.at("x").get<int>(), s.at("y").get<int>(),  s.at("w").get<int>(),
                         s.at("h").get<int>(), s.at("ox").get<int>(), s.at("oy").get<int>()};
            if (r.w <= 0 || r.h <= 0 || r.x < 0 || r.y < 0)
                return std::unexpected("atlas: sprite '" + key + "' has an invalid rectangle");
            m.sprites.emplace(key, r);
        }
        return m;
    } catch (const nlohmann::json::exception& e) {
        return std::unexpected(std::string("atlas: ") + e.what());
    }
}

SpriteId Atlas::add(int x, int y, int w, int h, int ox, int oy) {
    rects_.push_back({x, y, w, h, ox, oy});
    sprites_.push_back({{},
                        static_cast<float>(w),
                        static_cast<float>(h),
                        static_cast<float>(ox),
                        static_cast<float>(oy)});
    return static_cast<SpriteId>(sprites_.size() - 1);
}

Atlas::Atlas(SDL_Renderer* renderer, const std::filesystem::path& assetsDir) {
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

    const int artW = art ? art->w : 0;
    const int artH = art ? art->h : 0;
    const int width = std::max(artW, kStripMinWidth);
    const int stripY = artH;
    pixels_.reset(SDL_CreateSurface(width, artH + kStripHeight, SDL_PIXELFORMAT_RGBA32));
    if (!pixels_) {
        SDL_Log("atlas: cannot create surface: %s", SDL_GetError());
        return;
    }
    if (!SDL_ClearSurface(pixels_.get(), 0, 0, 0, 0)) SDL_Log("atlas: %s", SDL_GetError());
    if (art) {
        if (!SDL_SetSurfaceBlendMode(art.get(), SDL_BLENDMODE_NONE) ||
            !SDL_BlitSurface(art.get(), nullptr, pixels_.get(), nullptr)) {
            SDL_Log("atlas: blit failed: %s", SDL_GetError());
        }
        for (const auto& [key, r] : manifest.sprites) {
            if (r.x + r.w > artW || r.y + r.h > artH) {
                SDL_Log("atlas: sprite '%s' lies outside the image; ignored", key.c_str());
                continue;
            }
            byKey_.emplace(key, add(r.x, r.y, r.w, r.h, r.ox, r.oy));
        }
        artCount_ = byKey_.size();
    }

    SDL_Surface* s = pixels_.get();
    // Placeholder diamond: loud magenta checker so missing art is obvious.
    placeholderTile_ = add(0, stripY, 32, 16, 16, 0);
    for (int y = 0; y < 16; ++y) {
        const int half = y < 8 ? 2 * y + 1 : 2 * (15 - y) + 1; // rows 2, 6 ... 30 px wide
        for (int x = 16 - half; x < 16 + half; ++x) {
            const bool check = ((x / 4) + (y / 2)) % 2 == 0;
            put(s, x, stripY + y, check ? Rgba{255, 0, 220, 255} : Rgba{40, 0, 40, 255});
        }
    }
    placeholderBox_ = add(34, stripY, 16, 24, 8, 18);
    for (int y = 0; y < 24; ++y) {
        for (int x = 0; x < 16; ++x) {
            const bool edge = x == 0 || y == 0 || x == 15 || y == 23;
            const bool check = ((x / 4) + (y / 4)) % 2 == 0;
            put(s, 34 + x, stripY + y,
                edge ? Rgba{40, 0, 40, 255}
                     : (check ? Rgba{255, 0, 220, 255} : Rgba{90, 0, 90, 255}));
        }
    }
    white_ = add(52, stripY, 4, 4, 0, 0);
    for (int y = 0; y < 4; ++y)
        for (int x = 0; x < 4; ++x) put(s, 52 + x, stripY + y, {255, 255, 255, 255});
    lightBlob_ = add(58, stripY, 64, 64, 32, 32);
    for (int y = 0; y < 64; ++y) {
        for (int x = 0; x < 64; ++x) {
            const float dx = (static_cast<float>(x) + 0.5f - 32.0f) / 32.0f;
            const float dy = (static_cast<float>(y) + 0.5f - 32.0f) / 32.0f;
            const float k = std::max(0.0f, 1.0f - std::sqrt(dx * dx + dy * dy));
            put(s, 58 + x, stripY + y, {255, 255, 255, toByte(k * k * (3 - 2 * k))});
        }
    }
    softShadow_ = add(124, stripY, 14, 6, 7, 3);
    for (int y = 0; y < 6; ++y) {
        for (int x = 0; x < 14; ++x) {
            const float dx = (static_cast<float>(x) + 0.5f - 7.0f) / 7.0f;
            const float dy = (static_cast<float>(y) + 0.5f - 3.0f) / 3.0f;
            const float k = std::max(0.0f, 1.0f - (dx * dx + dy * dy));
            put(s, 124 + x, stripY + y, {0, 0, 0, toByte(std::min(1.0f, k * 1.6f))});
        }
    }

    texture_.reset(SDL_CreateTextureFromSurface(renderer, s));
    if (!texture_) {
        SDL_Log("atlas: cannot create texture: %s", SDL_GetError());
        return;
    }
    if (!SDL_SetTextureScaleMode(texture_.get(), SDL_SCALEMODE_NEAREST))
        SDL_Log("atlas: %s", SDL_GetError());
    const auto fw = static_cast<float>(s->w);
    const auto fh = static_cast<float>(s->h);
    for (std::size_t i = 0; i < sprites_.size(); ++i) {
        const auto& r = rects_[i];
        sprites_[i].uv = {static_cast<float>(r.x) / fw, static_cast<float>(r.y) / fh,
                          static_cast<float>(r.x + r.w) / fw, static_cast<float>(r.y + r.h) / fh};
    }
    SDL_Log("atlas: %zu sprites loaded", artCount_);
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
    if (!SDL_UpdateTexture(texture_.get(), &rect, first, pixels_->pitch))
        SDL_Log("atlas: %s", SDL_GetError());
    return static_cast<float>(peak) / 255.0f;
}

} // namespace lc
