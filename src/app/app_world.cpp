// The game inside the world (docs/design/world-tech.md §4): the prebuilt world loaded through
// src/world and drawn through src/worldview as the one scene, with the home region at its place
// drawn by the game's own scene at the world renderer's turns.

#include "app/app_impl.hpp"
#include "ui/strings.hpp"

#include <algorithm>
#include <format>

namespace lc {

bool App::loadWorldData() {
    if (!fs::exists(assets_ / "world" / "world.json")) return true; // the floating island
    const Uint64 t0 = SDL_GetPerformanceCounter();
    auto loaded = world::loadWorld(assets_, cat_);
    if (!loaded) {
        SDL_Log("world: %s", loaded.error().c_str());
        return false;
    }
    loaded_ = std::make_unique<world::LoadedWorld>(std::move(*loaded));
    for (const std::string& e : loaded_->diagnostics.errors) SDL_Log("world: %s", e.c_str());
    if (!loaded_->diagnostics.warnings.empty())
        SDL_Log("world: %zu warnings (worldinfo validate lists them)",
                loaded_->diagnostics.warnings.size());
    const world::HomePlacement& home = loaded_->file.home;
    const Iso iso = cat_.iso();
    const int lvl = loaded_->content->tileLevel();
    const Vec2 o = iso.toWorld(TilePos{home.rect.x0, home.rect.y0});
    homeOffset_ = {o.x, o.y - static_cast<float>(home.level * lvl)};
    scene_->setFloating(false);
    figures_ = world::placeFigures(*loaded_);
    journal_.assign(loaded_->file.regions.size(), {});
    visited_.assign(loaded_->file.regions.size(), 0);
    hooks_.ground = [this](const worldview::FrameInfo& fi) {
        scene_->embedBegin(sceneFrame_, {fi.target, fi.xf, fi.w, fi.h, homeOffset_});
        scene_->embedGround(sceneFrame_);
    };
    hooks_.objects = [this](const worldview::FrameInfo&) { scene_->embedObjects(sceneFrame_); };
    hooks_.light = [this](const worldview::FrameInfo& fi) {
        scene_->embedLight(sceneFrame_, {fi.ambient.r, fi.ambient.g, fi.ambient.b});
    };
    hooks_.glow = [this](const worldview::FrameInfo&) { scene_->embedGlow(sceneFrame_); };
    hooks_.overlay = [this](const worldview::FrameInfo&) { scene_->embedSky(sceneFrame_); };
    // Each set's arrival motif (audiogen's `sfx/<set>/arrive.wav`), loaded with the effects.
    for (const world::RegionRef& r : loaded_->file.regions) {
        const std::string f = "sfx/" + r.set + "/arrive.wav";
        if (r.set != "home" && std::ranges::find(arriveFiles_, f) == arriveFiles_.end() &&
            fs::exists(assets_ / "audio" / f))
            arriveFiles_.push_back(f);
    }
    arriveFiles_.emplace_back(sfx::kArriveHome);
    arriveFiles_.emplace_back(sfx::kSeamChime);
    SDL_Log("world: loaded in %.0f ms (%zu layers, %zu regions)",
            msBetween(t0, SDL_GetPerformanceCounter()), loaded_->layers.size(),
            loaded_->file.regions.size());
    return true;
}

void App::createWorldView() {
    if (!loaded_ || worldView_) return;
    // The home goes into the world's map once, before anything reads it on another thread: its
    // terrain (every home terrain id interned, so later edits only write bytes) and wild land.
    // Its items stay the game's (core World); the world's map never holds them.
    world::HomeDelta delta = world::homeDeltaFrom(world_, cat_);
    delta.items.clear();
    for (const TerrainDef& t : cat_.terrain)
        if (std::ranges::find(delta.palette, t.id) == delta.palette.end())
            delta.palette.push_back(t.id);
    world::Diagnostics diag;
    if (auto r = loaded_->map->applyHome(delta, diag); !r)
        SDL_Log("world: home: %s", r.error().c_str());
    homeSynced_ = world_.revision();
    const world::HomePlacement& home = loaded_->file.home;
    const Iso iso = cat_.iso();
    // The home's screen box in world px: its ground and whatever stands on it.
    const Reach& r = scene_->itemReach();
    const auto f = [](int v) { return static_cast<float>(v); };
    const int w = home.rect.x1 - home.rect.x0;
    const int h = home.rect.y1 - home.rect.y0;
    const FRect box{iso.toWorld(0.0f, f(h)).x - r.right + homeOffset_.x, homeOffset_.y - r.bottom,
                    iso.toWorld(f(w), 0.0f).x + r.left + homeOffset_.x,
                    iso.toWorld(f(w), f(h)).y + r.top + homeOffset_.y};
    worldView_ = std::make_unique<worldview::WorldView>(renderer_.get(), *loaded_, assets_, *atlas_,
                                                        font_, measuring() && !opts_.headless,
                                                        worldview::Hole{home.rect, box}, figures_);
    setupMap();
}

void App::syncHome() {
    if (!worldView_ || world_.revision() == homeSynced_) return;
    // The overview is built from the map on a worker at first; edits wait until it is done.
    if (!worldView_->overviewBuilt()) return;
    homeSynced_ = world_.revision();
    if (!loaded_->map->updateHomeTerrain(world::homeDeltaFrom(world_, cat_)))
        SDL_Log("world: the home's terrain does not fit the world's copy");
    // The world's cells draw the home's rim tiles under the scene's: redraw them when it changes.
    rimScratch_.clear();
    const int w = world_.width();
    const int h = world_.height();
    for (int i = 0; i < w; ++i) {
        rimScratch_.push_back(world_.terrainAt({i, 0}));
        rimScratch_.push_back(world_.terrainAt({i, h - 1}));
    }
    for (int i = 0; i < h; ++i) {
        rimScratch_.push_back(world_.terrainAt({0, i}));
        rimScratch_.push_back(world_.terrainAt({w - 1, i}));
    }
    if (worldView_ && rimScratch_ != rimTerrain_) worldView_->holeChanged();
    std::swap(rimScratch_, rimTerrain_);
}

void App::drawScene(const FrameParams& p, SDL_Texture* out) {
    if (!worldView_) {
        scene_->draw(p, out);
        return;
    }
    sceneFrame_ = p;
    const Vec2 c = p.camera->position();
    worldview::ViewSpec v;
    v.centre = {c.x + homeOffset_.x, c.y + homeOffset_.y};
    v.scale = p.camera->scale();
    v.screen = p.screen;
    if (!SDL_SetRenderTarget(renderer_.get(), out)) SDL_Log("render: %s", SDL_GetError());
    worldView_->draw(v, clock_.time(), p.light, frameDt_, static_cast<double>(simTime_), hooks_);
}

void App::compositeScene(const FrameParams& p, Vec2 scale, bool smooth) {
    if (worldView_)
        worldView_->composite(scale, smooth);
    else
        scene_->composite(p, scale, smooth);
}

int App::sceneDrawCalls() const {
    return scene_->drawCalls() + (worldView_ ? worldView_->stats().drawCalls : 0);
}

TileRect App::cameraLand() const {
    if (!loaded_) return {};
    // The whole grid, in home tiles: the camera may roam over all the land and sea.
    const TileRect g{0, 0, loaded_->map->width(), loaded_->map->height()};
    const TileRect h = loaded_->file.home.rect;
    return {g.x0 - h.x0, g.y0 - h.y0, g.x1 - h.x0, g.y1 - h.y0};
}

} // namespace lc

namespace lc {

void App::setupMap() {
    const world::WorldFile& wf = loaded_->file;
    if (SurfacePtr png{SDL_LoadPNG((assets_ / "world" / "overview.png").string().c_str())}) {
        mapTexture_ = uploadTexture(renderer_.get(), png.get());
        if (mapTexture_) {
            if (!SDL_SetTextureScaleMode(mapTexture_.get(), SDL_SCALEMODE_LINEAR))
                SDL_Log("map: %s", SDL_GetError());
            mapSprite_ = {mapTexture_.get(),
                          {0, 0, 1, 1},
                          static_cast<float>(png->w),
                          static_cast<float>(png->h),
                          0,
                          0};
            mapScale_ = static_cast<float>(png->w) / static_cast<float>(wf.gridH);
        }
    } else {
        SDL_Log("map: %s", SDL_GetError());
    }
    // One marker per region (its first), home and cities first so they draw under no town.
    allPlaces_.clear();
    for (const world::Marker& mk : wf.markers) {
        const world::RegionRef& r = wf.regions[static_cast<std::size_t>(mk.region)];
        if (std::ranges::any_of(allPlaces_, [&](const Place& p) { return p.region == mk.region; }))
            continue;
        const MapMarker kind = r.kind == world::RegionKind::Home   ? MapMarker::Home
                               : r.kind == world::RegionKind::City ? MapMarker::City
                                                                   : MapMarker::Town;
        allPlaces_.push_back({mk.region, kind, mk.at});
    }
    std::ranges::stable_sort(allPlaces_, {}, [](const Place& p) { return p.marker; });
}

const world::RegionFile* App::regionFile(int region) const {
    if (!loaded_ || region < 0 || std::cmp_greater_equal(region, loaded_->regions.size()))
        return nullptr;
    const world::RegionFile& f = loaded_->regions[static_cast<std::size_t>(region)];
    return f.id.empty() ? nullptr : &f;
}

std::string_view App::regionName(int region) const {
    if (loaded_ && region == loaded_->file.home.region) return worldName_;
    if (const world::RegionFile* f = regionFile(region); f != nullptr && !f->name.empty())
        return f->name;
    return {};
}

const MapModel& App::mapModel() {
    mapPlaces_.clear();
    mapShown_.clear();
    for (const Place& p : allPlaces_) {
        // The home and the cities from the start; towns once they have been visited.
        if (p.marker == MapMarker::Town && visited_[static_cast<std::size_t>(p.region)] == 0)
            continue;
        const world::RegionFile* f = regionFile(p.region);
        std::string_view era;
        if (f != nullptr) {
            const auto dot = f->caption.find(" · ");
            if (dot != std::string::npos) era = std::string_view(f->caption).substr(dot + 4);
        }
        const std::string_view native =
            f != nullptr && font_.hasAll(f->native) && regionName(p.region) != f->native
                ? std::string_view(f->native)
                : std::string_view{};
        mapPlaces_.push_back(
            {regionName(p.region), native, era,
             mapPixel({static_cast<float>(p.at.x) + 0.5f, static_cast<float>(p.at.y) + 0.5f},
                      loaded_->file.gridH, mapScale_),
             p.marker});
        mapShown_.push_back(p.region);
    }
    const Vec2 t = cat_.iso().toTile(camera_.position());
    const TileRect h = loaded_->file.home.rect;
    mapModel_ = {mapTexture_ ? &mapSprite_ : nullptr, mapPlaces_,
                 mapPixel({t.x + static_cast<float>(h.x0), t.y + static_cast<float>(h.y0)},
                          loaded_->file.gridH, mapScale_)};
    return mapModel_;
}

void App::toggleMap() {
    if (!loaded_) return;
    map_.open(!map_.isOpen());
    play(map_.isOpen() ? sfx::kOpen : sfx::kClose, tuning::kUiSfxLevel);
    if (map_.isOpen()) {
        drawerOpen_ = false;
        setTool(Tool::None, -1);
    }
}

bool App::away() const {
    if (!loaded_) return false;
    const Vec2 t = cat_.iso().toTile(camera_.position());
    return t.x < 0 || t.y < 0 || t.x >= static_cast<float>(world_.width()) ||
           t.y >= static_cast<float>(world_.height());
}

void App::travelTo(int region) {
    if (!loaded_ || travel_.region >= 0) return;
    travel_ = {region, 0, false};
    map_.open(false);
}

void App::updateWorld(float dt) {
    if (!worldView_) return;
    // Fast travel: fade out, jump, wait (briefly) for the destination to stream, fade in.
    if (travel_.region >= 0) {
        travel_.t += dt;
        if (!travel_.jumped && travel_.t >= tuning::kTravelFadeOut) {
            travel_.jumped = true;
            const world::WorldFile& wf = loaded_->file;
            const auto mk = std::ranges::find(wf.markers, travel_.region, &world::Marker::region);
            if (travel_.region == wf.home.region || mk == wf.markers.end()) {
                frameCamera();
            } else {
                camera_.place(gridToHome({static_cast<float>(mk->at.x) + 0.5f,
                                          static_cast<float>(mk->at.y) + 0.5f}),
                              kZoomLevels[kDefaultZoomLevel], screen());
            }
            camera_.beginStep();
            view_ = camera_;
            worldView_->jumped(
                {camera_.position().x + homeOffset_.x, camera_.position().y + homeOffset_.y});
            const world::RegionRef& r = wf.regions[static_cast<std::size_t>(travel_.region)];
            play(r.kind == world::RegionKind::Home ? std::string_view(sfx::kArriveHome)
                                                   : arriveMotif(r.set),
                 tuning::kSfxLevel);
            travel_.t = tuning::kTravelFadeOut;
        }
        const float held = travel_.t - tuning::kTravelFadeOut;
        if (travel_.jumped && (worldView_->settled() || held >= tuning::kTravelHold) &&
            travelFadeIn_ < 0)
            travelFadeIn_ = travel_.t;
        if (travelFadeIn_ >= 0 && travel_.t - travelFadeIn_ >= tuning::kTravelFadeIn) {
            travel_ = {};
            travelFadeIn_ = -1;
        }
    }
    const worldview::PlaceTracker& pl = worldView_->places();
    if (pl.region() >= 0 && visited_[static_cast<std::size_t>(pl.region())] == 0) {
        visited_[static_cast<std::size_t>(pl.region())] = 1;
        markDirty();
    }
    if (pl.arrived()) noteArrival();
    if (journalDirty_) {
        journalDirty_ = false;
        buildJournal();
    }
    if (pl.eraChanged()) {
        play(sfx::kSeamChime, tuning::kSfxLevel);
        if (!seamExplained_) {
            seamExplained_ = true;
            hud_.toast(std::string(strings::kSeamLine));
            markDirty();
        }
    }
    // Away from the home region the building tools rest.
    if (away()) {
        if (tool_ != Tool::None) setTool(Tool::None, -1);
        drawerOpen_ = false;
    }
}

float App::travelVeil() const {
    if (travel_.region < 0) return 0;
    if (!travel_.jumped) return std::clamp(travel_.t / tuning::kTravelFadeOut, 0.0f, 1.0f);
    if (travelFadeIn_ < 0) return 1;
    return 1.0f - std::clamp((travel_.t - travelFadeIn_) / tuning::kTravelFadeIn, 0.0f, 1.0f);
}

std::string_view App::arriveMotif(std::string_view set) const {
    for (const std::string& f : arriveFiles_)
        if (f.find("/" + std::string(set) + "/") != std::string::npos) return f;
    return {};
}

void App::fillWorldModel(HudModel& m) const {
    if (!worldView_) return;
    m.world = true;
    m.away = away();
    const worldview::PlaceTracker& pl = worldView_->places();
    const int here = pl.place() >= 0 ? pl.place() : pl.region();
    if (m.away) m.place = regionName(here);
    if (const int c = pl.caption(); c >= 0 && pl.captionAlpha() > 0) {
        m.captionAlpha = pl.captionAlpha();
        if (const world::RegionFile* f = regionFile(c)) {
            m.caption = f->caption.empty() ? std::string_view(f->name) : f->caption;
            // The native form below, unless the caption says it already or the interface font
            // cannot draw its script.
            if (m.caption.find(f->native) == std::string_view::npos && font_.hasAll(f->native))
                m.captionSub = f->native;
        } else {
            m.caption = regionName(c);
        }
    }
    if (m.away && m.hint.empty() && !photo_) m.hint = strings::kAwayHint;
    if (cardOpen_) {
        m.cardTitle = card_.title;
        if (font_.hasAll(card_.native)) m.cardNative = card_.native;
        m.cardEpithet = card_.epithet;
        m.cardText = card_.text;
    }
    m.places = journalPlaces_;
    // What the pointer rests on out in the world: its name.
    if (m.worldTip.empty() && tool_ == Tool::None && mouseInside_ && !hud_.wantsMouse())
        if (const auto c = cardAt(mouse_)) {
            hoverName_.assign(entryName(*c, hoverName_));
            m.worldTip = hoverName_;
        }
}

} // namespace lc

namespace lc {

std::optional<App::CardRef> App::cardAt(Vec2 px) const {
    // The corner's own things answer on its land; the world's everywhere else.
    if (!worldView_ || hover_) return std::nullopt;
    const Vec2 w = view_.screenToWorld(px, screen());
    const auto picked = worldView_->pick({w.x + homeOffset_.x, w.y + homeOffset_.y});
    if (!picked) return std::nullopt;
    const world::WorldMap& m = *loaded_->map;
    CardRef r;
    if (picked->figure) {
        const world::FigurePlace& f = figures_[picked->index];
        r = {f.region, "figure:" + f.actor, f.card};
    } else {
        const world::Placed& it = m.items()[picked->index];
        const world::ItemInfo& info = m.info(it);
        r = {m.regionAt({it.x, it.y}), "landmark:" + info.id, info.card};
    }
    if (regionFile(r.region) == nullptr) return std::nullopt;
    return r;
}

std::string_view App::entryName(const CardRef& c, std::string& storage) const {
    const world::RegionFile* f = regionFile(c.region);
    if (const world::Card* card = f != nullptr ? f->card(c.card) : nullptr;
        card != nullptr && !card->title.empty())
        return card->title;
    // No card text: the catalog's name.
    const std::string_view id = std::string_view(c.entry).substr(c.entry.find(':') + 1);
    for (const world::SetCatalog& s : loaded_->content->sets()) {
        for (const world::SetActor& a : s.actors)
            if (a.id == id) return a.name;
        for (const world::SetItem& it : s.items)
            if (it.id == id) return it.name;
    }
    storage.assign(id);
    return storage;
}

std::string_view App::nativeName(const CardRef& c) const {
    // A figure's own name in its set is the original-language form (Hadrianus); show it when
    // the card calls them otherwise. Landmarks' catalog names are descriptions, not forms.
    if (!c.entry.starts_with("figure:")) return {};
    const std::string_view id = std::string_view(c.entry).substr(7);
    const world::RegionFile* f = regionFile(c.region);
    const world::Card* card = f != nullptr ? f->card(c.card) : nullptr;
    for (const world::SetCatalog& s : loaded_->content->sets())
        for (const world::SetActor& a : s.actors)
            if (a.id == id &&
                (card == nullptr || (a.name != card->title && a.name != card->epithet)))
                return a.name;
    return {};
}

void App::recordEntry(const CardRef& c, bool found) {
    if (c.region < 0 || std::cmp_greater_equal(c.region, journal_.size())) return;
    auto& list = journal_[static_cast<std::size_t>(c.region)];
    const auto it = std::ranges::find(list, c.entry, &JournalItem::entry);
    if (it == list.end()) {
        list.push_back({c.entry, c.card, found});
        markDirty();
        journalDirty_ = true;
    } else if (found && !it->found) {
        it->found = true;
        markDirty();
        journalDirty_ = true;
    }
}

bool App::openCardAt(Vec2 px) {
    const auto c = cardAt(px);
    if (!c) return false;
    std::string storage;
    const world::RegionFile* f = regionFile(c->region);
    const world::Card* card = f->card(c->card);
    card_.title.assign(entryName(*c, storage));
    card_.native.assign(nativeName(*c));
    card_.epithet = card != nullptr ? card->epithet : std::string{};
    card_.text = card != nullptr ? card->text : std::string{};
    cardOpen_ = true;
    recordEntry(*c, true);
    play(sfx::kOpen, tuning::kUiSfxLevel);
    return true;
}

void App::closeCard() {
    if (!cardOpen_) return;
    cardOpen_ = false;
    play(sfx::kClose, tuning::kUiSfxLevel);
}

void App::noteArrival() {
    // What is in view on arrival counts as seen; a click on it finds it.
    worldView_->visibleCards(pickedScratch_);
    const world::WorldMap& m = *loaded_->map;
    for (const worldview::WorldView::Picked& p : pickedScratch_) {
        CardRef r;
        if (p.figure) {
            const world::FigurePlace& f = figures_[p.index];
            r = {f.region, "figure:" + f.actor, f.card};
        } else {
            const world::Placed& it = m.items()[p.index];
            r = {m.regionAt({it.x, it.y}), "landmark:" + m.info(it).id, m.info(it).card};
        }
        if (regionFile(r.region) != nullptr) recordEntry(r, false);
    }
}

void App::buildJournal() {
    journalEntries_.clear();
    journalPlaces_.clear();
    journalSummaries_.clear();
    journalNames_.clear();
    if (!loaded_) return;
    // Places in the order of the map's markers, each with what it holds.
    std::size_t total = 0;
    for (const auto& list : journal_) total += list.size();
    journalNames_.reserve(total);
    std::vector<std::pair<std::size_t, std::size_t>> spans;
    for (const Place& p : allPlaces_) {
        const auto& list = journal_[static_cast<std::size_t>(p.region)];
        if (list.empty() || p.marker == MapMarker::Home) continue;
        const std::size_t begin = journalEntries_.size();
        for (const JournalItem& j : list) {
            const CardRef c{p.region, j.entry, j.card};
            std::string& storage = journalNames_.emplace_back();
            const world::RegionFile* f = regionFile(p.region);
            const world::Card* card = f != nullptr ? f->card(j.card) : nullptr;
            journalEntries_.push_back(
                {entryName(c, storage),
                 card != nullptr ? std::string_view(card->epithet) : std::string_view{}, j.found});
        }
        const auto found = std::ranges::count_if(list, &JournalItem::found);
        const world::RegionFile* f = regionFile(p.region);
        const std::size_t cards = f != nullptr ? f->cards.size() : list.size();
        journalSummaries_.push_back(std::vformat(
            strings::kJournalFound, std::make_format_args(found, std::max(cards, list.size()))));
        spans.emplace_back(begin, journalEntries_.size() - begin);
        journalPlaces_.push_back({regionName(p.region), {}, {}});
    }
    for (std::size_t i = 0; i < journalPlaces_.size(); ++i) {
        journalPlaces_[i].summary = journalSummaries_[i];
        journalPlaces_[i].entries =
            std::span(journalEntries_).subspan(spans[i].first, spans[i].second);
    }
}

} // namespace lc

namespace lc {

std::optional<Vec2> App::gridPoint(std::string_view name) const {
    const world::WorldMap& m = *loaded_->map;
    Vec2 at{-1, -1};
    float lift = 0;
    if (name.starts_with("grid:")) {
        const std::string_view xy = name.substr(5);
        const auto comma = xy.find(',');
        if (comma == std::string_view::npos) return std::nullopt;
        at = {std::stof(std::string(xy.substr(0, comma))) + 0.5f,
              std::stof(std::string(xy.substr(comma + 1))) + 0.5f};
    } else if (name.starts_with("landmark:")) {
        const int info = m.content().findItem(name.substr(9));
        for (const world::Placed& it : m.items())
            if (static_cast<int>(it.info) == info) {
                const TileRect r = it.rect();
                at = {static_cast<float>(r.x0 + r.x1) * 0.5f,
                      static_cast<float>(r.y0 + r.y1) * 0.5f};
                lift = tuning::kLandmarkPointLift;
                break;
            }
    } else if (name.starts_with("figure:")) {
        for (const world::FigurePlace& f : figures_)
            if (f.actor == name.substr(7)) {
                at = f.at;
                lift = tuning::kFigurePointLift;
            }
    }
    if (at.x < 0) return std::nullopt;
    const TilePos t{static_cast<int>(std::floor(at.x)), static_cast<int>(std::floor(at.y))};
    if (!m.inBounds(t)) return std::nullopt;
    Vec2 w = gridToHome(at);
    w.y -= lift;
    return camera_.worldToScreen(w, screen());
}

Vec2 App::gridToHome(Vec2 tile) const {
    const TileRect h = loaded_->file.home.rect;
    Vec2 w =
        cat_.iso().toWorld(tile.x - static_cast<float>(h.x0), tile.y - static_cast<float>(h.y0));
    // A tile above or below the home's level is drawn that much higher or lower.
    const world::WorldMap& m = *loaded_->map;
    const TilePos t{static_cast<int>(std::floor(tile.x)), static_cast<int>(std::floor(tile.y))};
    if (m.inBounds(t))
        w.y -= static_cast<float>((m.level(t) - loaded_->file.home.level) *
                                  loaded_->content->tileLevel());
    return w;
}

} // namespace lc

namespace lc {

WorldProgress App::worldState() const {
    WorldProgress w;
    if (!loaded_) return w;
    const world::WorldFile& wf = loaded_->file;
    const Vec2 t = cat_.iso().toTile(camera_.position());
    w.camera =
        Vec2{t.x + static_cast<float>(wf.home.rect.x0), t.y + static_cast<float>(wf.home.rect.y0)};
    w.zoom = camera_.zoom();
    for (std::size_t r = 0; r < wf.regions.size(); ++r) {
        if (visited_[r] != 0) w.visited.push_back(wf.regions[r].id);
        std::vector<std::string> found;
        std::vector<std::string> seen;
        for (const JournalItem& j : journal_[r]) (j.found ? found : seen).push_back(j.entry);
        if (!found.empty()) w.found.emplace_back(wf.regions[r].id, std::move(found));
        if (!seen.empty()) w.seen.emplace_back(wf.regions[r].id, std::move(seen));
    }
    if (seamExplained_) w.flags.emplace_back(kFlagSeamExplained);
    return w;
}

void App::adoptWorldState(const WorldProgress& w) {
    seamExplained_ = std::ranges::find(w.flags, kFlagSeamExplained) != w.flags.end();
    journalDirty_ = true;
    cardOpen_ = false;
    if (!loaded_) return;
    const world::WorldFile& wf = loaded_->file;
    std::ranges::fill(visited_, std::uint8_t{0});
    for (auto& list : journal_) list.clear();
    for (const std::string& id : w.visited)
        if (const int r = wf.findRegion(id); r >= 0) visited_[static_cast<std::size_t>(r)] = 1;
    // Entries name their card through the catalogs and the figures; unknown ones are dropped.
    const auto add = [&](const auto& lists, bool found) {
        for (const auto& [id, entries] : lists) {
            const int r = wf.findRegion(id);
            if (r < 0) continue;
            for (const std::string& e : entries) {
                std::string card;
                if (e.starts_with("landmark:")) {
                    const int i = loaded_->content->findItem(std::string_view(e).substr(9));
                    if (i < 0) continue;
                    card = loaded_->content->item(i).card;
                } else if (e.starts_with("figure:")) {
                    const auto f = std::ranges::find(figures_, std::string_view(e).substr(7),
                                                     &world::FigurePlace::actor);
                    if (f == figures_.end()) continue;
                    card = f->card;
                } else {
                    continue;
                }
                recordEntry({r, e, card}, found);
            }
        }
    };
    add(w.found, true);
    add(w.seen, false);
    if (w.camera) {
        // Clamped to the grid if the world changed under it.
        const Vec2 at{std::clamp(w.camera->x, 0.0f, static_cast<float>(wf.gridW)),
                      std::clamp(w.camera->y, 0.0f, static_cast<float>(wf.gridH))};
        savedCamera_ = gridToHome(at);
        savedZoom_ = w.zoom;
    }
}

} // namespace lc
