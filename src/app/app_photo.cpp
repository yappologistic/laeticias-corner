// Postcards (docs/design/living-corner.md R12): photo mode's frame and caption drawn over the
// view, the postcard taken at window resolution, where the files go and the folder they open.

#include "app/app_impl.hpp"
#include "ui/strings.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdlib>
#include <ctime>
#include <format>

namespace lc {
namespace {

constexpr std::string_view kPostcardsDir = "postcards";
constexpr std::string_view kPicturesSub = "Laeticia's Corner";
constexpr SDL_FColor kPlainBorder{0.96f, 0.93f, 0.84f, 1.0f};  // the Plain frame's cream
constexpr float kPlainWidth = 2.0f;                            // art px
constexpr SDL_FColor kCaptionBand{0.04f, 0.05f, 0.045f, 0.5f}; // under a Plain caption

// The top-left part of a sprite, `w` x `h` art pixels of it (an edge tile cut to fit).
Sprite crop(const Sprite& s, float w, float h) {
    Sprite c = s;
    c.w = std::min(w, s.w);
    c.h = std::min(h, s.h);
    c.uv.u1 = s.uv.u0 + (s.uv.u1 - s.uv.u0) * (c.w / s.w);
    c.uv.v1 = s.uv.v0 + (s.uv.v1 - s.uv.v0) * (c.h / s.h);
    return c;
}

SDL_FColor withAlphaOf(SDL_FColor c, float a) {
    return {c.r, c.g, c.b, c.a * a};
}

// A horizontal slice of a sprite from x0 to x1 (art px).
Sprite slice(const Sprite& s, float x0, float x1) {
    Sprite c = s;
    c.w = x1 - x0;
    const float du = s.uv.u1 - s.uv.u0;
    c.uv.u0 = s.uv.u0 + du * (x0 / s.w);
    c.uv.u1 = s.uv.u0 + du * (x1 / s.w);
    return c;
}

} // namespace

fs::path App::postcardDir() const {
    // Beside the save when a save directory was named (always so in tests), else the player's
    // Pictures folder, else the preference folder (R12.4).
    const char* env = std::getenv("LAETICIA_SAVE_DIR");
    if (opts_.saveDir || (env != nullptr && *env != '\0')) // set but empty is unset, as for saves
        return saveDir_ / kPostcardsDir / slug_;
    if (const char* pictures = SDL_GetUserFolder(SDL_FOLDER_PICTURES))
        return fs::path(pictures) / kPicturesSub / slug_;
    return saveDir_ / kPostcardsDir / slug_;
}

void App::openPostcardsFolder() {
    const fs::path dir = postcardDir();
    std::error_code ec;
    fs::create_directories(dir, ec);
    // Automated runs never reach the desktop: they only say where it would open.
    if (opts_.headless) {
        SDL_Log("postcards: folder %s", dir.string().c_str());
        return;
    }
    const std::string url = "file://" + fs::absolute(dir, ec).string();
    if (!SDL_OpenURL(url.c_str())) SDL_Log("postcards: %s", SDL_GetError());
}

void App::cycleFrame(int d) {
    // Only unlocked frames are offered; the choice is remembered.
    const int n = static_cast<int>(cat_.frames.size());
    if (n == 0) return;
    int f = std::max(0, frameIndex_);
    for (int k = 0; k < n; ++k) {
        f = (f + d + n) % n;
        if (progress_.frames[static_cast<std::size_t>(f)] != 0) break;
    }
    frameIndex_ = f;
    profile_.frame = cat_.frames[static_cast<std::size_t>(f)].id;
    profileChanged();
    play(sfx::kRotate, tuning::kUiSfxLevel);
}

int App::postcardFrame() const {
    if (const auto f = cat_.findFrame(profile_.frame);
        f && progress_.frames[static_cast<std::size_t>(*f)] != 0)
        return *f;
    return cat_.frames.empty() ? -1 : 0;
}

void App::updatePostcardDate() {
    // Formatted only when one of the dates changes, so photo mode allocates nothing per frame.
    const SeasonDay sd = seasonOf(clock_.day(), cat_.seasonDays);
    const std::time_t now = std::time(nullptr);
    std::tm local{};
#if defined(_WIN32)
    (void)localtime_s(&local, &now);
#else
    (void)localtime_r(&now, &local);
#endif
    const int day = local.tm_mday;
    const std::int64_t key =
        ((static_cast<std::int64_t>(clock_.day()) * 8 + season()) * 400 + local.tm_yday) * 4000 +
        local.tm_year;
    if (key == captionKey_) return;
    captionKey_ = key;
    const int year = local.tm_year + 1900;
    const std::string_view month =
        strings::kMonths[static_cast<std::size_t>(std::clamp(local.tm_mon, 0, 11))];
    const int seasonDay = sd.day + 1;
    captionDate_ =
        std::vformat(strings::kPostcardDate,
                     std::make_format_args(cat_.seasons[static_cast<std::size_t>(season())].name,
                                           seasonDay, day, month, year));
}

void App::drawPostcard(Painter& p) {
    const Vec2 sc = screen();
    const int f = postcardFrame();
    if (f != framePartsOf_) {
        // The frame's nine pieces and plate, looked up once per frame chosen.
        framePartsOf_ = f;
        framePlain_ = true;
        if (f >= 0) {
            static constexpr std::string_view kParts[] = {"tl", "tr", "bl", "br",   "t",
                                                          "b",  "l",  "r",  "plate"};
            framePlain_ = false;
            for (std::size_t i = 0; i < std::size(kParts); ++i) {
                const auto sid = atlas_->find(std::format(
                    "frame/{}/{}", cat_.frames[static_cast<std::size_t>(f)].id, kParts[i]));
                if (!sid) {
                    framePlain_ = true; // Plain, or art missing: the engine's cream border
                    break;
                }
                frameParts_[i] = atlas_->sprite(*sid);
            }
        }
    }
    // Frames are pixel art at the world's whole-number zoom, so they match it.
    const float k = std::max(1.0f, std::floor(view_.scale() + 1e-3f));
    float inset = kPlainWidth * k;
    const bool plain = framePlain_;
    const auto part = [&](std::size_t i) -> const Sprite& { return frameParts_[i]; };
    if (plain) {
        const float w = kPlainWidth * k;
        p.roundRect({0, 0, sc.x, w}, 0, kPlainBorder, 0);
        p.roundRect({0, sc.y - w, sc.x, w}, 0, kPlainBorder, 0);
        p.roundRect({0, 0, w, sc.y}, 0, kPlainBorder, 0);
        p.roundRect({sc.x - w, 0, w, sc.y}, 0, kPlainBorder, 0);
    } else {
        const Sprite& tl = part(0);
        const Sprite& tr = part(1);
        const Sprite& bl = part(2);
        const Sprite& br = part(3);
        const Sprite& top = part(4);
        const Sprite& bottom = part(5);
        const Sprite& left = part(6);
        const Sprite& right = part(7);
        const auto put = [&](const Sprite& s, float x, float y) {
            p.thumbnail(s, {x, y, s.w * k, s.h * k}, k, 1.0f);
        };
        // Edges tiled between the corners, the last tile cut to fit.
        const auto tile = [&](const Sprite& e, bool across, float from, float to, float at) {
            const float step = (across ? e.w : e.h) * k;
            const int n = static_cast<int>(std::ceil((to - from) / step));
            for (int i = 0; i < n; ++i) {
                const float pos = from + static_cast<float>(i) * step;
                const float room = (to - pos) / k;
                if (across)
                    put(crop(e, room, e.h), pos, at);
                else
                    put(crop(e, e.w, room), at, pos);
            }
        };
        tile(top, true, tl.w * k, sc.x - tr.w * k, 0);
        tile(bottom, true, bl.w * k, sc.x - br.w * k, sc.y - bottom.h * k);
        tile(left, false, tl.h * k, sc.y - bl.h * k, 0);
        tile(right, false, tr.h * k, sc.y - br.h * k, sc.x - right.w * k);
        put(tl, 0, 0);
        put(tr, sc.x - tr.w * k, 0);
        put(bl, 0, sc.y - bl.h * k);
        put(br, sc.x - br.w * k, sc.y - br.h * k);
        inset = std::max(left.w, bottom.h) * k;
    }
    p.endLayer();
    if (!profile_.caption) return;
    // The caption: the world's name, then the in-game and the real date, bottom left.
    updatePostcardDate();
    const Font& font = p.font();
    const float s = uiScale_;
    const float pad = theme::kToastPad * s;
    // A name from a hand-edited save may be any length: cut short to the window (H3-020).
    const std::string_view name = elide(font, Face::Title, worldName_,
                                        sc.x - 2 * (inset + theme::kMargin * s + pad), captionCut_);
    const float w =
        std::max(font.measure(Face::Title, name), font.measure(Face::Body, captionDate_)) + 2 * pad;
    const float h = font.lineHeight(Face::Title) + font.lineHeight(Face::Body) + pad;
    const Box b{inset + theme::kMargin * s, sc.y - inset - theme::kMargin * s - h, w, h};
    captionTop_ = b.y;
    if (plain) {
        p.roundRect(b, theme::kTileRadius * s, kCaptionBand);
    } else {
        // The frame's plate, at a whole-number scale tall enough for the text, its middle
        // repeated to the caption's width.
        const Sprite& plate = part(8);
        const float pk = std::max(k, std::ceil(h / std::max(1.0f, plate.h)));
        const float cap = std::floor(plate.w * 0.25f);
        const Sprite l = slice(plate, 0, cap);
        const Sprite mid = slice(plate, cap, plate.w - cap);
        const Sprite r = slice(plate, plate.w - cap, plate.w);
        const float ph = plate.h * pk;
        const float py = b.y + (h - ph) * 0.5f;
        p.thumbnail(l, {b.x - cap * pk * 0.5f, py, cap * pk, ph}, pk, 1.0f);
        float x = b.x - cap * pk * 0.5f + cap * pk;
        const float end = b.x + b.w + cap * pk * 0.5f - cap * pk;
        while (x < end) {
            const Sprite piece = crop(mid, (end - x) / pk, mid.h);
            p.thumbnail(piece, {x, py, piece.w * pk, ph}, pk, 1.0f);
            x += piece.w * pk;
        }
        p.thumbnail(r, {end, py, cap * pk, ph}, pk, 1.0f);
        p.endLayer();
    }
    const SDL_FColor ink = plain ? theme::kInk : SDL_FColor{0.18f, 0.14f, 0.10f, 1.0f};
    p.text(Face::Title, name, b.x + pad, b.y + pad * 0.5f + font.ascent(Face::Title), ink);
    p.text(Face::Body, captionDate_, b.x + pad,
           b.y + pad * 0.5f + font.lineHeight(Face::Title) + font.ascent(Face::Body),
           withAlphaOf(ink, plain ? 0.8f : 0.85f));
}

void App::capturePhoto() {
    // At window resolution, with the frame and caption, never the bar; the world save is not
    // touched. The pixels are read here; the PNG is made on a worker (H3-019).
    settlePhoto(true); // one at a time, so the last one's file is there for the name below
    SurfacePtr pixels{SDL_RenderReadPixels(renderer_.get(), nullptr)};
    if (!pixels) {
        SDL_Log("postcard: %s", SDL_GetError());
        hud_.toast(std::string(strings::kPostcardFailed));
        return;
    }
    const fs::path dir = postcardDir();
    std::error_code ec;
    fs::create_directories(dir, ec);
    const std::string base = postcardStem(slug_, std::time(nullptr));
    fs::path file = dir / (base + ".png");
    for (int n = 2; fs::exists(file, ec) && n < 10000; ++n)
        file = dir / (base + "-" + std::to_string(n) + ".png");
    play(sfx::kShutter);
    hud_.flash();
    photoFile_ = file;
    // SDL's error text is the worker's own, so it comes back with the outcome.
    photoJob_ = std::async(std::launch::async, [px = std::move(pixels), path = file.string()] {
        return SDL_SavePNG(px.get(), path.c_str()) ? std::string() : std::string(SDL_GetError());
    });
}

void App::settlePhoto(bool wait) {
    if (!photoJob_.valid()) return;
    if (!wait && photoJob_.wait_for(std::chrono::seconds(0)) != std::future_status::ready) return;
    if (const std::string why = photoJob_.get(); why.empty()) {
        hud_.toast(std::string(strings::kPostcardSaved));
        SDL_Log("postcard: saved %s", photoFile_.string().c_str());
    } else {
        SDL_Log("postcard: %s: %s", photoFile_.string().c_str(), why.c_str());
        hud_.toast(std::string(strings::kPostcardFailed));
    }
}

} // namespace lc
