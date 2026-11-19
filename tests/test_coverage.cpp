// Catalog-vs-assets coverage. Missing content is reported (the art and audio sets are built in
// parallel with the engine); set LAETICIA_STRICT_COVERAGE=1 to make gaps fail the run. Broken
// content (unreadable files, wrong formats, sprites outside the image) always fails.

#include "audio/decode.hpp"
#include "render/atlas.hpp"
#include "render/sprites.hpp"
#include "test_support.hpp"
#include "ui/font.hpp"

#include <SDL3/SDL.h>

#include <doctest.h>
#include <nlohmann/json.hpp>

#include <charconv>
#include <cstdlib>
#include <filesystem>
#include <format>
#include <fstream>
#include <functional>
#include <iterator>
#include <map>
#include <set>

using namespace lc;

namespace {

bool strict() {
    const char* v = std::getenv("LAETICIA_STRICT_COVERAGE");
    return v != nullptr && std::string_view(v) == "1";
}

void reportMissing(const std::string& what, const std::vector<std::string>& missing) {
    if (missing.empty()) {
        MESSAGE(what << ": complete");
        return;
    }
    std::string list;
    for (const auto& m : missing) list += "\n  " + m;
    if (strict()) {
        FAIL(what << ": " << missing.size() << " missing" << list);
    } else {
        MESSAGE(what << ": " << missing.size() << " missing" << list);
    }
}

} // namespace

TEST_CASE("coverage: catalog vs atlas") {
    const auto dir = test::assetsDir();
    const auto text = readTextFile(dir / "atlas.json");
    if (!text) {
        reportMissing("atlas", {"atlas.json"});
        return;
    }
    const auto manifest = parseAtlasManifest(*text);
    REQUIRE_MESSAGE(manifest.has_value(), manifest.error());
    for (const std::string& why : manifest->refused) FAIL_CHECK("atlas.json: " << why);
    const SurfacePtr image{SDL_LoadPNG((dir / manifest->image).string().c_str())};
    REQUIRE_MESSAGE(image != nullptr, "atlas image unreadable: " << SDL_GetError());
    for (const auto& [key, r] : manifest->sprites) {
        CHECK_MESSAGE(r.x + r.w <= image->w, key << " lies outside the image");
        CHECK_MESSAGE(r.y + r.h <= image->h, key << " lies outside the image");
    }
    std::vector<std::string> missing;
    for (const auto& key : requiredSpriteKeys(test::catalog())) {
        // "a|b": either form of an actor animation will do.
        const auto bar = key.find('|');
        const bool have = bar == std::string::npos
                              ? manifest->sprites.contains(key)
                              : manifest->sprites.contains(key.substr(0, bar)) ||
                                    manifest->sprites.contains(key.substr(bar + 1));
        if (!have) missing.push_back(key);
    }
    // Frame sequences must not have gaps (f0, f1, f3 would silently drop f3). Keys with other
    // suffixes belong to later contract additions and are not frames of this catalog.
    for (const auto& [key, r] : manifest->sprites) {
        const auto f = key.rfind("/f");
        if (f == std::string::npos) continue;
        int n = 0;
        const char* first = key.data() + f + 2;
        const char* last = key.data() + key.size();
        const auto [end, ec] = std::from_chars(first, last, n);
        if (ec != std::errc{} || end != last || n == 0) continue;
        CHECK_MESSAGE(manifest->sprites.contains(key.substr(0, f) + "/f" + std::to_string(n - 1)),
                      key << " has a gap before it");
    }
    reportMissing("atlas", missing);
}

TEST_CASE("coverage: the world's sea and rivers keep their beach's width round a bend") {
    // They lie over a whole diamond of sand, cut back from land: the sand between the tile's
    // edge and the water is a beach. At a corner both of whose edges face land the beach must be
    // as wide as along those edges; rounded off, it widened into a point at every bend (issue
    // #2). Measured along the rows through the left and right vertices (the run of empty texels
    // from the diamond's edge to the water) against the same run half way along each edge. The
    // edges' own wobble moves a run by up to about a tenth of the half-width.
    const Iso iso = test::catalog().iso();
    const int hw = static_cast<int>(iso.hw);
    const int hh = static_cast<int>(iso.hh);
    const auto dir = test::assetsDir() / "atlas";
    const auto text = readTextFile(dir / "world.0.json");
    REQUIRE_MESSAGE(text.has_value(), "world.0.json unreadable");
    const auto manifest = parseAtlasManifest(*text);
    REQUIRE_MESSAGE(manifest.has_value(), manifest.error());
    const SurfacePtr image{SDL_LoadPNG((dir / manifest->image).string().c_str())};
    REQUIRE_MESSAGE(image != nullptr, "world.0.png unreadable: " << SDL_GetError());
    const auto half = [&](int y) { // the raster's half-width on row y (2:1, rows 2, 6, ... wide)
        const int yy = y < hh ? y : 2 * hh - 1 - y;
        return (2 * yy + 1) * hw / (2 * hh);
    };
    int checked = 0;
    for (const std::string terrain : {"world.river", "world.sea"})
        for (int mask = 0; mask < 16; ++mask) {
            const std::string key = std::format("terrain/{}/m{}/f0", terrain, mask);
            const auto it = manifest->sprites.find(key);
            REQUIRE_MESSAGE(it != manifest->sprites.end(), key << " missing");
            const SpriteRect& r = it->second;
            const auto empty = [&](int x, int y) { // (x, y) from the top vertex
                const int px = r.ox + x;
                const int py = r.oy + y;
                if (px < 0 || py < 0 || px >= r.w || py >= r.h) return true;
                Uint8 cr = 0, cg = 0, cb = 0, ca = 0;
                return SDL_ReadSurfacePixel(image.get(), r.x + px, r.y + py, &cr, &cg, &cb, &ca) &&
                       ca == 0;
            };
            // From the diamond's left (dx 1) or right (dx -1) edge on row y, inward to the water.
            const auto beach = [&](int y, int dx) {
                int x = dx > 0 ? -half(y) : half(y) - 1;
                int n = 0;
                for (; -half(y) <= x && x < half(y) && empty(x, y); x += dx) ++n;
                return n;
            };
            for (const int dx : {1, -1}) {
                // The left vertex joins the W (8) and S (4) edges, the right the N (1) and E (2).
                const int edges = dx > 0 ? 8 | 4 : 1 | 2;
                if ((mask & edges) != 0) continue;
                const int corner = std::max(beach(hh - 1, dx), beach(hh, dx));
                const int along = std::max(beach(hh / 2 - 1, dx), beach(hh + hh / 2, dx));
                CHECK_MESSAGE(corner <= along + hw / 10,
                              std::format("{} {} corner: a beach of {} px against {}", key,
                                          dx > 0 ? "left" : "right", corner, along));
                ++checked;
            }
        }
    CHECK(checked > 0);
}

TEST_CASE("coverage: catalog vs audio") {
    const auto& cat = test::catalog();
    const auto dir = test::assetsDir() / "audio";
    std::vector<std::string> missing;
    for (const auto& f : cat.audio.sfx) {
        if (!std::filesystem::exists(dir / f)) {
            missing.push_back(f);
            continue;
        }
        const auto info = probeWav(dir / f);
        REQUIRE_MESSAGE(info.has_value(), info.error());
        CHECK_MESSAGE(info->rate == 44100, f << " must be 44.1 kHz");
        CHECK_MESSAGE(info->channels == 1, f << " must be mono");
        CHECK_MESSAGE(info->bits == 16, f << " must be 16-bit");
        CHECK_MESSAGE(info->peak <= 0.7080f, f << " peaks above -3 dB"); // 10^(-3/20)
    }
    for (const auto* list : {&cat.audio.music, &cat.audio.ambience}) {
        for (const auto& f : *list) {
            const auto bytes = readBinaryFile(dir / f);
            if (!bytes) {
                missing.push_back(f);
                continue;
            }
            const auto info = probeOgg(*bytes);
            REQUIRE_MESSAGE(info.has_value(), f << ": " << info.error());
            CHECK_MESSAGE(info->rate == 44100, f << " must be 44.1 kHz");
            CHECK_MESSAGE(info->channels == 2, f << " must be stereo");
        }
    }
    reportMissing("audio", missing);
}

TEST_CASE("coverage: the interface's fonts draw every string the world shows") {
    // No card, caption, map label or journal line may show a missing glyph. Text in a script that
    // needs shaping or right-to-left layout (Arabic script: a `native` form, a native caption) is
    // left out by the game, which shows the transliteration instead; everything else must be
    // covered.
    const std::filesystem::path assets = LC_TEST_ASSETS_DIR;
    Font font;
    REQUIRE(font.load(assets / "fonts"));
    // Every glyph the fonts lack is Arabic script (or a joiner).
    const auto arabic = [&](std::string_view s) {
        for (std::size_t i = 0; i < s.size();) {
            const char32_t c = nextCodepoint(s, i);
            if (font.covers(c) || c == 0x200C || c == 0x200D) continue;
            if (!((c >= 0x600 && c <= 0x6FF) || (c >= 0x750 && c <= 0x77F) ||
                  (c >= 0xFB50 && c <= 0xFDFF) || (c >= 0xFE70 && c <= 0xFEFF)))
                return false;
        }
        return true;
    };
    std::vector<std::string> missing;
    std::function<void(const nlohmann::json&, const std::string&, const std::string&)> scan =
        [&](const nlohmann::json& j, const std::string& key, const std::string& where) {
            if (j.is_string()) {
                const auto& s = j.get_ref<const std::string&>();
                if (font.coversAll(s)) return;
                if (arabic(s)) return;
                missing.push_back(where + " " + key + ": " + s);
            } else if (j.is_object()) {
                for (const auto& [k, v] : j.items()) scan(v, k, where);
            } else if (j.is_array()) {
                for (const auto& v : j) scan(v, key, where);
            }
        };
    std::vector<std::filesystem::path> files{assets / "catalog.json"};
    for (const auto& e : std::filesystem::directory_iterator(assets / "regions"))
        if (e.path().extension() == ".json") files.push_back(e.path());
    for (const auto& e : std::filesystem::directory_iterator(assets / "sets"))
        if (std::filesystem::exists(e.path() / "catalog.json"))
            files.push_back(e.path() / "catalog.json");
    for (const auto& f : files) {
        std::ifstream in(f);
        const nlohmann::json j = nlohmann::json::parse(in, nullptr, false);
        REQUIRE_FALSE(j.is_discarded());
        scan(j, "", f.filename().string());
    }
    // The interface's own text (src/ui/strings.hpp): every string literal in it.
    {
        std::ifstream in(assets.parent_path() / "src" / "ui" / "strings.hpp");
        REQUIRE(in);
        const std::string text((std::istreambuf_iterator<char>(in)), {});
        for (std::size_t i = text.find('"'); i != std::string::npos; i = text.find('"', i + 1)) {
            std::string lit;
            std::size_t j = i + 1;
            for (; j < text.size() && text[j] != '"'; ++j) {
                if (text[j] == '\\' && j + 1 < text.size()) ++j;
                lit += text[j];
            }
            scan(lit, "", "strings.hpp");
            i = j;
        }
    }
    // Every character that would be drawn as a box or "?" (none but the Arabic script the game
    // leaves out), and what the fonts are asked for, by block, for the record.
    std::set<char32_t> uncovered;
    std::map<std::string, int> blocks;
    for (const auto& f : files) {
        std::ifstream in(f);
        const std::string text((std::istreambuf_iterator<char>(in)), {});
        for (std::size_t i = 0; i < text.size();) {
            const char32_t c = nextCodepoint(text, i);
            if (c < 0x80) continue;
            const char* block = c < 0x250                     ? "Latin-1 and Latin Extended"
                                : c < 0x370                   ? "IPA and modifiers"
                                : c < 0x400                   ? "Greek"
                                : c < 0x600                   ? "Cyrillic and others"
                                : c < 0x780                   ? "Arabic"
                                : c < 0x1E00                  ? "other"
                                : c < 0x1F00                  ? "Latin Extended Additional"
                                : c < 0x2000                  ? "Greek Extended (polytonic)"
                                : c < 0x2070                  ? "punctuation"
                                : c < 0x10000                 ? "symbols"
                                : c >= 0x103A0 && c < 0x103E0 ? "Old Persian cuneiform"
                                                              : "other (beyond the BMP)";
            ++blocks[block];
            if (!font.covers(c)) uncovered.insert(c);
        }
    }
    for (const auto& [block, n] : blocks) MESSAGE(block << ": " << n << " characters shown");
    for (const char32_t c : uncovered) {
        const bool arabicScript = (c >= 0x600 && c <= 0x6FF) || c == 0x200C || c == 0x200D;
        MESSAGE(std::format("not in the fonts: U+{:04X}{}", static_cast<unsigned>(c),
                            arabicScript ? " (Arabic script, left out)" : ""));
        CHECK(arabicScript);
    }
    // What the painter itself draws: the ellipsis of a cut line.
    CHECK(font.coversAll("…"));
    for (const std::string& m : missing) MESSAGE("not drawable: " << m);
    CHECK(missing.empty());
    CHECK(files.size() > 40);
}
