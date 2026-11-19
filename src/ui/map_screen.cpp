#include "ui/map_screen.hpp"

#include "ui/strings.hpp"
#include "ui/theme.hpp"

#include <algorithm>
#include <cmath>

namespace lc {
namespace {

float smooth(float t) {
    return t * t * (3 - 2 * t);
}

SDL_FColor withAlpha(SDL_FColor c, float a) {
    return {c.r, c.g, c.b, c.a * a};
}

float radiusOf(MapMarker m) {
    switch (m) {
    case MapMarker::Home: return theme::kMapHomeDot;
    case MapMarker::City: return theme::kMapCityDot;
    case MapMarker::Town: return theme::kMapTownDot;
    }
    return theme::kMapTownDot;
}

} // namespace

Vec2 mapPixel(Vec2 t, int gridH, float scale) {
    return {(static_cast<float>(gridH) - t.y) * scale, t.x * scale};
}

Vec2 mapTile(Vec2 p, int gridH, float scale) {
    return {p.y / scale, static_cast<float>(gridH) - p.x / scale};
}

Vec2 MapScreen::toScreen(Vec2 p) const {
    return {image_.x + p.x * k_, image_.y + p.y * k_};
}

Vec2 MapScreen::markerAt(const MapModel& m, int place) const {
    return toScreen(m.places[static_cast<std::size_t>(place)].at);
}

void MapScreen::update(float x, float y, bool inside, bool pressed, bool released,
                       const MapModel& m, const Font& font, Vec2 screen, float s, float dt) {
    (void)font;
    clicked_.reset();
    scale_ = s;
    screen_ = screen;
    const float step = dt / theme::kTransition;
    t_ = open_ ? std::min(1.0f, t_ + step) : std::max(0.0f, t_ - step);
    const float margin = theme::kMargin * s;
    const float pad = theme::kPanelPad * s;
    const float header = theme::kMapHeader * s;
    const float iw = m.image != nullptr ? m.image->w : 1.0f;
    const float ih = m.image != nullptr ? m.image->h : 1.0f;
    const float availW = screen.x - 2 * margin - 2 * pad;
    const float availH = screen.y - 2 * margin - 2 * pad - header;
    k_ = std::max(1e-3f, std::min(availW / iw, availH / ih));
    // Enlarged, the art is drawn at a whole scale (crisp pixels): markers use the same one.
    if (k_ >= 1.0f) k_ = std::floor(k_);
    // The panel hugs the art, centred in the window.
    const float fw = iw * k_ + 2 * pad;
    const float fh = ih * k_ + 2 * pad + header;
    frame_ = {std::round((screen.x - fw) * 0.5f), std::round((screen.y - fh) * 0.5f), fw, fh};
    image_ = {frame_.x + pad, frame_.y + header + pad, iw * k_, ih * k_};
    hovered_ = -1;
    if (!open_ || !inside) {
        if (released) pressed_ = -1;
        return;
    }
    // The nearest marker within reach of the pointer.
    float best = theme::kMapReach * s;
    for (std::size_t i = 0; i < m.places.size(); ++i) {
        const Vec2 c = toScreen(m.places[i].at);
        const float d = std::hypot(c.x - x, c.y - y);
        if (d <= best) {
            best = d;
            hovered_ = static_cast<int>(i);
        }
    }
    if (pressed) pressed_ = hovered_;
    if (released) {
        if (pressed_ >= 0 && pressed_ == hovered_) clicked_ = hovered_;
        pressed_ = -1;
    }
}

void MapScreen::draw(Painter& p, const MapModel& m) const {
    const float a = smooth(t_);
    if (a <= 0) return;
    const float s = scale_;
    const Font& f = p.font();
    p.glass(frame_, theme::kPanelRadius * s, a, theme::kGlass);
    p.endGlass();
    const float pad = theme::kPanelPad * s;
    p.text(Face::Title, strings::kMapTitle, frame_.x + pad, frame_.y + pad + f.ascent(Face::Title),
           withAlpha(theme::kInk, a));
    const float hw = f.measure(Face::Body, strings::kMapHint);
    p.text(Face::Body, strings::kMapHint, frame_.x + frame_.w - pad - hw,
           frame_.y + pad + f.ascent(Face::Title), withAlpha(theme::kInkMuted, a));
    if (m.image != nullptr) p.thumbnail(*m.image, image_, k_, a);
    p.endLayer();
    // Towns' lights after dark, warm points under the markers.
    for (const MapLight& l : m.lights) {
        const Vec2 c = toScreen(l.at);
        const float r = (1.5f + 2.0f * l.strength) * s;
        p.roundRect({c.x - r, c.y - r, 2 * r, 2 * r}, r,
                    withAlpha(theme::kMapLight, a * std::min(1.0f, 0.35f + 0.65f * l.strength)));
    }
    // Where the view is now, then the places.
    const Vec2 v = toScreen(m.view);
    p.roundRect({v.x - theme::kMapViewRing * s, v.y - theme::kMapViewRing * s,
                 2 * theme::kMapViewRing * s, 2 * theme::kMapViewRing * s},
                theme::kMapViewRing * s, withAlpha(theme::kMapView, a), 2.0f * s);
    for (std::size_t i = 0; i < m.places.size(); ++i) {
        const MapPlace& pl = m.places[i];
        const Vec2 c = toScreen(pl.at);
        const bool hot = static_cast<int>(i) == hovered_;
        const float r = radiusOf(pl.marker) * s * (hot ? 1.35f : 1.0f);
        p.roundRect({c.x - r - s, c.y - r - s, 2 * (r + s), 2 * (r + s)}, r + s,
                    withAlpha(theme::kMapDotRim, a));
        p.roundRect({c.x - r, c.y - r, 2 * r, 2 * r}, r,
                    withAlpha(pl.marker == MapMarker::Home ? theme::kAccent : theme::kMapDot, a));
    }
    if (hovered_ < 0) return;
    // The hovered place's name, its native form and its moment, in a tip above the marker.
    const MapPlace& pl = m.places[static_cast<std::size_t>(hovered_)];
    const Vec2 c = toScreen(pl.at);
    const float tp = theme::kTipPad * s;
    float w = f.measure(Face::Title, pl.name);
    float h = f.lineHeight(Face::Title);
    for (const std::string_view line : {pl.native, pl.era}) {
        if (line.empty()) continue;
        w = std::max(w, f.measure(Face::Body, line));
        h += f.lineHeight(Face::Body);
    }
    Box b{c.x - w * 0.5f - tp, c.y - theme::kMapReach * s - h - 2 * tp, w + 2 * tp, h + 2 * tp};
    // Kept inside the map's frame; a tip wider than the frame starts at its left edge.
    b.x = std::max(frame_.x, std::min(b.x, frame_.x + frame_.w - b.w));
    if (b.y < frame_.y) b.y = c.y + theme::kMapReach * s;
    p.glass(b, theme::kTipRadius * s, a, theme::kGlassTip);
    p.endGlass();
    float y = b.y + tp;
    p.text(Face::Title, pl.name, b.x + tp, y + f.ascent(Face::Title), withAlpha(theme::kInk, a));
    y += f.lineHeight(Face::Title);
    for (const std::string_view line : {pl.native, pl.era}) {
        if (line.empty()) continue;
        p.text(Face::Body, line, b.x + tp, y + f.ascent(Face::Body),
               withAlpha(theme::kInkMuted, a));
        y += f.lineHeight(Face::Body);
    }
    p.endLayer();
}

} // namespace lc
