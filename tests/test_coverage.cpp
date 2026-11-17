// Catalog-vs-assets coverage. Missing content is reported (the art and audio sets are built in
// parallel with the engine); set LAETICIA_STRICT_COVERAGE=1 to make gaps fail the run. Broken
// content (unreadable files, wrong formats, sprites outside the image) always fails.

#include "audio/decode.hpp"
#include "render/atlas.hpp"
#include "render/sprites.hpp"
#include "test_support.hpp"

#include <SDL3/SDL.h>

#include <doctest.h>

#include <charconv>
#include <cstdlib>
#include <filesystem>

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
    const SurfacePtr image{SDL_LoadPNG((dir / manifest->image).string().c_str())};
    REQUIRE_MESSAGE(image != nullptr, "atlas image unreadable: " << SDL_GetError());
    for (const auto& [key, r] : manifest->sprites) {
        CHECK_MESSAGE(r.x + r.w <= image->w, key << " lies outside the image");
        CHECK_MESSAGE(r.y + r.h <= image->h, key << " lies outside the image");
    }
    std::vector<std::string> missing;
    for (const auto& key : requiredSpriteKeys(test::catalog()))
        if (!manifest->sprites.contains(key)) missing.push_back(key);
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
