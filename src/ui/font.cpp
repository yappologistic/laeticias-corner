#include "ui/font.hpp"

#include "ui/theme.hpp"

#include <stb_truetype.h>

#include <algorithm>
#include <cmath>
#include <fstream>
#include <iterator>

namespace lc {
namespace {

constexpr char32_t kTextExtras[] = {0xB7,   0xD7,   0xE9,   0x2014, 0x2018,
                                    0x2019, 0x201C, 0x201D, 0x2026, 0x2212};
// Kerning is kept for printable ASCII pairs, which is all interface text needs.
constexpr char32_t kKernFirst = 32;
constexpr char32_t kKernLast = 126;
constexpr std::size_t kKernSpan = kKernLast - kKernFirst + 1;

std::vector<int> textCodepoints() {
    std::vector<int> cps;
    for (int c = 32; c < 127; ++c) cps.push_back(c);
    for (char32_t c : kTextExtras) cps.push_back(static_cast<int>(c));
    return cps;
}

} // namespace

char32_t nextCodepoint(std::string_view s, std::size_t& i) {
    const auto byte = [&](std::size_t k) { return static_cast<unsigned char>(s[k]); };
    const unsigned char c = byte(i++);
    if (c < 0x80) return c;
    int extra = 0;
    char32_t cp = 0;
    if ((c & 0xE0) == 0xC0) {
        extra = 1;
        cp = c & 0x1F;
    } else if ((c & 0xF0) == 0xE0) {
        extra = 2;
        cp = c & 0x0F;
    } else if ((c & 0xF8) == 0xF0) {
        extra = 3;
        cp = c & 0x07;
    } else {
        return 0xFFFD;
    }
    for (int k = 0; k < extra; ++k) {
        if (i >= s.size() || (byte(i) & 0xC0) != 0x80) return 0xFFFD;
        cp = (cp << 6) | (byte(i++) & 0x3F);
    }
    return cp;
}

bool Font::load(const std::filesystem::path& dir) {
    const std::filesystem::path files[] = {dir / "Nunito-SemiBold.ttf",
                                           dir / "Nunito-ExtraBold.ttf", dir / "lucide.ttf"};
    bool ok = true;
    for (std::size_t f = 0; f < faces_.size(); ++f) {
        std::ifstream in(files[f], std::ios::binary);
        faces_[f].ttf.assign(std::istreambuf_iterator<char>(in), {});
        if (faces_[f].ttf.empty()) {
            SDL_Log("font: cannot read %s", files[f].string().c_str());
            ok = false;
        }
    }
    return ok;
}

bool Font::build(SDL_Renderer* renderer, float scale) {
    if (texture_ && scale == scale_) return true;
    for (const auto& f : faces_)
        if (f.ttf.empty()) return false;
    scale_ = scale;

    const std::vector<int> text = textCodepoints();
    std::vector<int> icons;
    for (char32_t c : theme::icon::kAll) icons.push_back(static_cast<int>(c));
    const float sizes[] = {theme::kTextBody * scale, theme::kTextTitle * scale,
                           theme::kIcon * scale};
    const std::vector<int>* sets[] = {&text, &text, &icons};

    for (int dim = 512; dim <= 4096; dim *= 2) {
        // Four extra rows at the bottom hold the white texel block.
        std::vector<unsigned char> bitmap(static_cast<std::size_t>(dim * (dim + 4)), 0);
        stbtt_pack_context ctx;
        if (!stbtt_PackBegin(&ctx, bitmap.data(), dim, dim, 0, 1, nullptr)) return false;
        bool packed = true;
        std::array<std::vector<stbtt_packedchar>, 3> chars;
        for (std::size_t f = 0; f < faces_.size() && packed; ++f) {
            chars[f].resize(sets[f]->size());
            stbtt_pack_range range{};
            range.font_size = sizes[f];
            range.array_of_unicode_codepoints = const_cast<int*>(sets[f]->data());
            range.num_chars = static_cast<int>(sets[f]->size());
            range.chardata_for_range = chars[f].data();
            packed = stbtt_PackFontRanges(&ctx, faces_[f].ttf.data(), 0, &range, 1) != 0;
        }
        stbtt_PackEnd(&ctx);
        if (!packed) continue;

        const auto fw = static_cast<float>(dim);
        const auto fh = static_cast<float>(dim + 4);
        for (std::size_t f = 0; f < faces_.size(); ++f) {
            FaceData& face = faces_[f];
            stbtt_fontinfo info;
            if (!stbtt_InitFont(&info, face.ttf.data(),
                                stbtt_GetFontOffsetForIndex(face.ttf.data(), 0)))
                return false;
            int asc = 0;
            int desc = 0;
            int gap = 0;
            stbtt_GetFontVMetrics(&info, &asc, &desc, &gap);
            const float px = stbtt_ScaleForPixelHeight(&info, sizes[f]);
            face.ascent = static_cast<float>(asc) * px;
            face.descent = static_cast<float>(desc) * px;
            face.lineHeight = static_cast<float>(asc - desc + gap) * px;
            face.kern.clear();
            if (sets[f] == &text) {
                face.kern.resize(kKernSpan * kKernSpan);
                for (std::size_t a = 0; a < kKernSpan; ++a)
                    for (std::size_t b = 0; b < kKernSpan; ++b)
                        face.kern[a * kKernSpan + b] =
                            static_cast<float>(stbtt_GetCodepointKernAdvance(
                                &info, static_cast<int>(kKernFirst + a),
                                static_cast<int>(kKernFirst + b))) *
                            px;
            }
            face.glyphs.clear();
            for (std::size_t g = 0; g < chars[f].size(); ++g) {
                const auto& c = chars[f][g];
                face.glyphs.push_back(
                    {static_cast<char32_t>((*sets[f])[g]),
                     c.xoff,
                     c.yoff,
                     c.xoff2,
                     c.yoff2,
                     {static_cast<float>(c.x0) / fw, static_cast<float>(c.y0) / fh,
                      static_cast<float>(c.x1) / fw, static_cast<float>(c.y1) / fh},
                     c.xadvance});
            }
            std::ranges::sort(face.glyphs, {}, &Glyph::cp);
        }
        for (int y = dim; y < dim + 4; ++y)
            for (int x = 0; x < 4; ++x) bitmap[static_cast<std::size_t>(y * dim + x)] = 255;
        white_ = {1.0f / fw, (static_cast<float>(dim) + 1.0f) / fh, 3.0f / fw,
                  (static_cast<float>(dim) + 3.0f) / fh};

        SurfacePtr surface{SDL_CreateSurface(dim, dim + 4, SDL_PIXELFORMAT_RGBA32)};
        if (!surface) return false;
        for (int y = 0; y < dim + 4; ++y) {
            auto* row = static_cast<unsigned char*>(surface->pixels) +
                        static_cast<std::ptrdiff_t>(y) * surface->pitch;
            for (int x = 0; x < dim; ++x) {
                unsigned char* p = row + static_cast<std::ptrdiff_t>(x) * 4;
                p[0] = p[1] = p[2] = 255;
                p[3] = bitmap[static_cast<std::size_t>(y * dim + x)];
            }
        }
        texture_ = uploadTexture(renderer, surface.get());
        if (!texture_) return false;
        if (!SDL_SetTextureScaleMode(texture_.get(), SDL_SCALEMODE_LINEAR))
            SDL_Log("font: %s", SDL_GetError());
        return true;
    }
    SDL_Log("font: glyphs do not fit at scale %.2f", static_cast<double>(scale));
    return false;
}

const Glyph* Font::find(Face face, char32_t cp) const {
    const auto& g = faces_[idx(face)].glyphs;
    const auto it = std::ranges::lower_bound(g, cp, {}, &Glyph::cp);
    return it != g.end() && it->cp == cp ? &*it : nullptr;
}

float Font::kerning(Face face, char32_t a, char32_t b) const {
    const auto& k = faces_[idx(face)].kern;
    if (k.empty() || a < kKernFirst || a > kKernLast || b < kKernFirst || b > kKernLast) return 0;
    return k[(a - kKernFirst) * kKernSpan + (b - kKernFirst)];
}

float Font::measure(Face face, std::string_view text) const {
    float w = 0;
    char32_t prev = 0;
    for (std::size_t i = 0; i < text.size();) {
        const char32_t cp = nextCodepoint(text, i);
        const Glyph* g = find(face, cp);
        if (g == nullptr) g = find(face, '?');
        if (g == nullptr) continue;
        w += kerning(face, prev, g->cp) + g->advance;
        prev = g->cp;
    }
    return w;
}

float Font::draw(Batch& batch, Face face, std::string_view text, float x, float y,
                 SDL_FColor color) const {
    batch.use(texture_.get(), SDL_BLENDMODE_BLEND, SDL_SCALEMODE_LINEAR);
    float pen = std::round(x);
    const float base = std::round(y);
    char32_t prev = 0;
    for (std::size_t i = 0; i < text.size();) {
        const Glyph* g = find(face, nextCodepoint(text, i));
        if (g == nullptr) g = find(face, '?'); // never draw a missing-glyph box
        if (g == nullptr) continue;
        pen += kerning(face, prev, g->cp);
        prev = g->cp;
        // Each glyph lands on whole pixels: its bitmap was rasterised on the pixel grid, and
        // fractional placement would blur it and make spacing look uneven.
        if (g->x1 > g->x0)
            batch.quad(
                SDL_FRect{std::round(pen + g->x0), base + g->y0, g->x1 - g->x0, g->y1 - g->y0},
                g->uv, color);
        pen += g->advance;
    }
    return pen - std::round(x);
}

void Font::drawIcon(Batch& batch, char32_t cp, float cx, float cy, SDL_FColor color) const {
    const Glyph* g = find(Face::Icon, cp);
    if (g == nullptr) return;
    batch.use(texture_.get(), SDL_BLENDMODE_BLEND, SDL_SCALEMODE_LINEAR);
    // Icons are drawn on a shared em square, so they are centred by that square rather than by
    // their ink (a minus sign has almost no ink box and would ride up otherwise).
    const FaceData& f = faces_[idx(Face::Icon)];
    const float baseline = std::round(cy + (f.ascent + f.descent) * 0.5f);
    const float pen = std::round(cx - g->advance * 0.5f);
    batch.quad(SDL_FRect{pen + g->x0, baseline + g->y0, g->x1 - g->x0, g->y1 - g->y0}, g->uv,
               color);
}

} // namespace lc
