#include "ui/font.hpp"

#include "ui/theme.hpp"

#include <stb_truetype.h>

#include <algorithm>
#include <cmath>
#include <fstream>
#include <iterator>
#include <span>
#include <utility>

namespace lc {
namespace {

constexpr char32_t kTextExtras[] = {0xB7,   0xD7,   0xE9,   0x2014, 0x2018,
                                    0x2019, 0x201C, 0x201D, 0x2026, 0x2212};
// Kerning is kept for printable ASCII pairs, which is all interface text needs.
constexpr char32_t kKernFirst = 32;
constexpr char32_t kKernLast = 126;
constexpr std::size_t kKernSpan = kKernLast - kKernFirst + 1;

// What the interface writes: Latin with every accent, macron and dot its transliterations use,
// Greek with its accents, basic Cyrillic (names the player types), Old Persian cuneiform; from the
// fallback faces where the main one lacks a letter. Scripts that need shaping or right-to-left
// layout (Arabic script) are not baked: such a line is left out and its transliteration stands
// (callers check coversAll); nothing is ever drawn as "?".
constexpr std::pair<char32_t, char32_t> kWorldRanges[] = {
    {0xA1, 0x2FF},    {0x370, 0x3FF},   {0x400, 0x45F},    {0x1E00, 0x1EFF},
    {0x1F00, 0x1FFF}, {0x2010, 0x2027}, {0x103A0, 0x103DF}};

bool inFont(const stbtt_fontinfo& f, char32_t c) {
    return stbtt_FindGlyphIndex(&f, static_cast<int>(c)) != 0;
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
    const auto read = [&](const std::filesystem::path& file, std::vector<unsigned char>& out) {
        std::ifstream in(file, std::ios::binary);
        out.assign(std::istreambuf_iterator<char>(in), {});
        if (out.empty()) SDL_Log("font: cannot read %s", file.string().c_str());
        return !out.empty();
    };
    bool ok = true;
    for (std::size_t f = 0; f < faces_.size(); ++f) ok &= read(files[f], faces_[f].ttf);
    // Fallbacks of the same weight for the text faces; a missing one only narrows the coverage.
    const std::array<std::filesystem::path, 2> body{dir / "NotoSans-Medium.ttf",
                                                    dir / "NotoSansOldPersian-Regular.ttf"};
    const std::array<std::filesystem::path, 2> title{dir / "NotoSans-Bold.ttf",
                                                     dir / "NotoSansOldPersian-Regular.ttf"};
    for (const Face face : {Face::Body, Face::Title}) {
        faces_[idx(face)].fallbacks.clear();
        for (const auto& file : face == Face::Body ? body : title) {
            std::vector<unsigned char> data;
            if (read(file, data)) faces_[idx(face)].fallbacks.push_back(std::move(data));
        }
    }
    if (ok) planFaces();
    return ok;
}

void Font::planFaces() {
    // Each text face bakes ASCII and the extras from its main file, then every character of the
    // world ranges from the first file (main, then fallbacks) that has it. A character either text
    // face cannot draw is dropped from both, so has() and covers() agree for every face.
    std::array<std::vector<std::pair<int, int>>, 2> picks; // per text face: (codepoint, file)
    for (const Face face : {Face::Body, Face::Title}) {
        FaceData& d = faces_[idx(face)];
        std::vector<stbtt_fontinfo> infos(1 + d.fallbacks.size());
        if (!stbtt_InitFont(&infos[0], d.ttf.data(), stbtt_GetFontOffsetForIndex(d.ttf.data(), 0)))
            return;
        for (std::size_t k = 0; k < d.fallbacks.size(); ++k)
            if (!stbtt_InitFont(&infos[k + 1], d.fallbacks[k].data(),
                                stbtt_GetFontOffsetForIndex(d.fallbacks[k].data(), 0)))
                return;
        auto& out = picks[idx(face)];
        for (int c = 32; c < 127; ++c) out.emplace_back(c, 0);
        for (char32_t c : kTextExtras) out.emplace_back(static_cast<int>(c), 0);
        for (const auto& [lo, hi] : kWorldRanges)
            for (char32_t c = lo; c <= hi; ++c) {
                if (std::ranges::any_of(kTextExtras, [&](char32_t e) { return e == c; })) continue;
                for (std::size_t k = 0; k < infos.size(); ++k)
                    if (inFont(infos[k], c)) {
                        out.emplace_back(static_cast<int>(c), static_cast<int>(k));
                        break;
                    }
            }
    }
    const auto has = [](const std::vector<std::pair<int, int>>& v, int c) {
        return std::ranges::any_of(v, [&](const auto& p) { return p.first == c; });
    };
    for (const Face face : {Face::Body, Face::Title}) {
        FaceData& d = faces_[idx(face)];
        const auto& other = picks[idx(face == Face::Body ? Face::Title : Face::Body)];
        d.plan.assign(1 + d.fallbacks.size(), {});
        for (const auto& [c, file] : picks[idx(face)])
            if (has(other, c)) d.plan[static_cast<std::size_t>(file)].push_back(c);
    }
    FaceData& icons = faces_[idx(Face::Icon)];
    icons.plan.assign(1, {});
    for (char32_t c : theme::icon::kAll) icons.plan[0].push_back(static_cast<int>(c));
}

bool Font::covers(char32_t cp) const {
    for (const auto& file : faces_[idx(Face::Body)].plan)
        if (std::ranges::find(file, static_cast<int>(cp)) != file.end()) return true;
    return false;
}

bool Font::coversAll(std::string_view utf8) const {
    for (std::size_t i = 0; i < utf8.size();) {
        const char32_t cp = nextCodepoint(utf8, i);
        if (cp != ' ' && !covers(cp)) return false;
    }
    return true;
}

bool Font::build(SDL_Renderer* renderer, float scale) {
    if (texture_ && scale == scale_) return true;
    for (const auto& f : faces_)
        if (f.ttf.empty()) return false;
    scale_ = scale;

    const float sizes[] = {theme::kTextBody * scale, theme::kTextTitle * scale,
                           theme::kIcon * scale};
    // A face's files: its main one, then its fallbacks, each with the characters it bakes.
    const auto file = [&](std::size_t f, std::size_t k) -> const std::vector<unsigned char>& {
        return k == 0 ? faces_[f].ttf : faces_[f].fallbacks[k - 1];
    };

    for (int dim = 512; dim <= 4096; dim *= 2) {
        // Four extra rows at the bottom hold the white texel block.
        std::vector<unsigned char> bitmap(static_cast<std::size_t>(dim * (dim + 4)), 0);
        stbtt_pack_context ctx;
        if (!stbtt_PackBegin(&ctx, bitmap.data(), dim, dim, 0, 1, nullptr)) return false;
        bool packed = true;
        std::array<std::vector<std::vector<stbtt_packedchar>>, 3> chars;
        for (std::size_t f = 0; f < faces_.size() && packed; ++f) {
            chars[f].resize(faces_[f].plan.size());
            for (std::size_t k = 0; k < faces_[f].plan.size() && packed; ++k) {
                std::vector<int>& cps = faces_[f].plan[k];
                if (cps.empty()) continue;
                chars[f][k].resize(cps.size());
                stbtt_pack_range range{};
                range.font_size = sizes[f];
                range.array_of_unicode_codepoints = cps.data();
                range.num_chars = static_cast<int>(cps.size());
                range.chardata_for_range = chars[f][k].data();
                packed = stbtt_PackFontRanges(&ctx, file(f, k).data(), 0, &range, 1) != 0;
            }
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
            if (f != idx(Face::Icon)) {
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
            for (std::size_t k = 0; k < chars[f].size(); ++k)
                for (std::size_t g = 0; g < chars[f][k].size(); ++g) {
                    const auto& c = chars[f][k][g];
                    face.glyphs.push_back(
                        {static_cast<char32_t>(face.plan[k][g]),
                         c.xoff,
                         c.yoff,
                         c.xoff2,
                         c.yoff2,
                         {static_cast<float>(c.x0) / fw, static_cast<float>(c.y0) / fh,
                          static_cast<float>(c.x1) / fw, static_cast<float>(c.y1) / fh},
                         c.xadvance});
                }
            std::ranges::sort(face.glyphs, {}, &Glyph::cp);
            face.ascii.fill(0);
            for (std::size_t g = 0; g < face.glyphs.size() && face.glyphs[g].cp < 128; ++g)
                face.ascii[face.glyphs[g].cp] = static_cast<std::uint16_t>(g + 1);
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

bool Font::has(char32_t cp) const {
    return find(Face::Body, cp) != nullptr && find(Face::Title, cp) != nullptr;
}

bool Font::hasAll(std::string_view utf8) const {
    for (std::size_t i = 0; i < utf8.size();) {
        const char32_t cp = nextCodepoint(utf8, i);
        if (cp != ' ' && !has(cp)) return false;
    }
    return true;
}

const Glyph* Font::find(Face face, char32_t cp) const {
    const auto& g = faces_[idx(face)].glyphs;
    if (cp < 128) {
        const std::uint16_t at = faces_[idx(face)].ascii[cp];
        return at != 0 ? &g[at - 1] : nullptr;
    }
    const auto it = std::ranges::lower_bound(g, cp, {}, &Glyph::cp);
    return it != g.end() && it->cp == cp ? &*it : nullptr;
}

float Font::kerning(Face face, char32_t a, char32_t b) const {
    const auto& k = faces_[idx(face)].kern;
    if (k.empty() || a < kKernFirst || a > kKernLast || b < kKernFirst || b > kKernLast) return 0;
    return k[(a - kKernFirst) * kKernSpan + (b - kKernFirst)];
}

void Font::extend(Face face, std::string_view more, Run& run) const {
    for (std::size_t i = 0; i < more.size();) {
        const char32_t cp = nextCodepoint(more, i);
        const Glyph* g = find(face, cp);
        if (g == nullptr) continue; // callers keep to what covers() allows
        run.width += kerning(face, run.prev, g->cp) + g->advance;
        run.prev = g->cp;
    }
}

float Font::measure(Face face, std::string_view text) const {
    Run run;
    extend(face, text, run);
    return run.width;
}

float Font::draw(Batch& batch, Face face, std::string_view text, float x, float y,
                 SDL_FColor color) const {
    batch.use(texture_.get(), SDL_BLENDMODE_BLEND, SDL_SCALEMODE_LINEAR);
    float pen = std::round(x);
    const float base = std::round(y);
    char32_t prev = 0;
    for (std::size_t i = 0; i < text.size();) {
        const Glyph* g = find(face, nextCodepoint(text, i));
        if (g == nullptr) continue; // never a missing-glyph box or a "?"
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
