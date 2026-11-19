// The game inside the world (docs/design/world-tech.md §4): the prebuilt world loaded through
// src/world and drawn through src/worldview as the one scene, with the home region at its place
// drawn by the game's own scene at the world renderer's turns.

#include "app/app_impl.hpp"
#include "core/land.hpp"
#include "ui/strings.hpp"

#include <algorithm>
#include <format>
#include <numbers>

namespace lc {

bool App::loadWorldData(WorldLoad load) {
    if (!load.world) {
        SDL_Log("world: %s", load.world.error().c_str());
        return false;
    }
    loaded_ = std::make_unique<world::LoadedWorld>(std::move(*load.world));
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
    hooks_.glow = [this](const worldview::FrameInfo& fi) {
        scene_->embedGlow(sceneFrame_, fi.target);
    };
    hooks_.overlay = [this](const worldview::FrameInfo&) { scene_->embedSky(sceneFrame_); };
    hooks_.lamps = [this] {
        lamps_.clear();
        scene_->forEachLamp([this](Vec2 at, float reach) {
            lamps_.push_back({{at.x + homeOffset_.x, at.y + homeOffset_.y}, reach});
        });
        return std::span<const worldview::HomeLamp>(lamps_);
    };
    // Each set's arrival motif (audiogen's `sfx/<set>/arrive.wav`), loaded with the effects.
    for (const world::RegionRef& r : loaded_->file.regions) {
        const std::string f = "sfx/" + r.set + "/arrive.wav";
        if (r.set != "home" && std::ranges::find(arriveFiles_, f) == arriveFiles_.end() &&
            fs::exists(assets_ / "audio" / f))
            arriveFiles_.push_back(f);
    }
    arriveFiles_.emplace_back(sfx::kArriveHome);
    arriveFiles_.emplace_back(sfx::kSeamChime);
    soundscape_ = std::make_unique<worldview::Soundscape>(*loaded_, assets_ / "audio");
    viewWeather_ = std::make_unique<worldview::WeatherField>(*loaded_, seed_);
    homeWeather_ = std::make_unique<worldview::WeatherField>(*loaded_, seed_);
    themeWeights_.assign(loaded_->file.regions.size(), 0.0f);
    SDL_Log("world: loaded in %.0f ms (%zu layers, %zu regions)", load.ms, loaded_->layers.size(),
            loaded_->file.regions.size());
    return true;
}

void App::applyHomeToMap() {
    // The home goes into the world's map: its terrain (every home terrain id interned, so
    // later edits only write bytes) and wild land. Its items stay the game's (core World); the
    // world's map never holds them. The first time, the map drops whatever the world's layers
    // placed on the home's land and renumbers its items and slots.
    world::HomeDelta delta = world::homeDeltaFrom(world_, cat_);
    delta.items.clear();
    for (const TerrainDef& t : cat_.terrain)
        if (std::ranges::find(delta.palette, t.id) == delta.palette.end())
            delta.palette.push_back(t.id);
    world::Diagnostics diag;
    if (auto r = loaded_->map->applyHome(delta, diag); !r)
        SDL_Log("world: home: %s", r.error().c_str());
    homeSynced_ = world_.revision();
}

void App::createWorldView() {
    if (!loaded_ || worldView_) return;
    // Once more with the world that was opened, before anything reads the map on another thread.
    applyHomeToMap();
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
    worldView_ = std::make_unique<worldview::WorldView>(
        renderer_.get(), *loaded_, assets_, *atlas_, streams(), worldview::Hole{home.rect, box},
        // Living figures walk with city life.
        city_ ? std::vector<world::FigurePlace>{} : figures_);
    worldView_->setWeather(viewWeather_.get());
    (void)worldView_->setQuality(wantedQuality());
    worldView_->setClouds(gpu::parseClouds(profile_.clouds).value_or(gpu::Clouds::On));
    if (city_) worldView_->setLife(city_->city.get());
    setupMap();
}

void App::syncHome() {
    if (!worldView_ || world_.revision() == homeSynced_) return;
    // The overview is built from the map on a worker at first; edits wait until it is done.
    if (!worldView_->overviewBuilt()) return;
    homeSynced_ = world_.revision();
    worldView_->homeTerrainChanged(); // before the map's copy changes (a worker may read it)
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
    if (out == nullptr) out = screenTarget(); // the window, or what stands in for it
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
    // Where the view is going, so it is ready on arrival: a journey's destination while the
    // veil comes down, else the level a zoom under way ends at.
    if (const auto to = travelDestination()) {
        v.heading = true;
        v.arrival = {to->centre.x + homeOffset_.x, to->centre.y + homeOffset_.y};
        v.arrivalScale = to->scale;
    } else if (!camera_.settled()) {
        const Vec2 end = camera_.arrival(p.screen);
        v.heading = true;
        v.arrival = {end.x + homeOffset_.x, end.y + homeOffset_.y};
        v.arrivalScale = camera_.zoom();
    }
    const Vec2 at = mouseInside_ ? p.camera->screenToWorld(mouse_, p.screen) : c;
    v.pointer = {at.x + homeOffset_.x, at.y + homeOffset_.y};
    if (!SDL_SetRenderTarget(renderer_.get(), out)) SDL_Log("render: %s", SDL_GetError());
    worldView_->setLifeAlpha(alpha_);
    scene_->beginFrameStats();
    scene_->setGroundDecode(worldView_->homeGroundDecode());
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
    // After dark the towns' lights show on the map (the shader path's light data).
    mapLights_.clear();
    if (const float glow = lighting().glow; worldView_ && glow > 0.01f && map_.showing()) {
        worldView_->mapLights(mapLightTiles_);
        for (const auto& [tile, k] : mapLightTiles_)
            mapLights_.push_back({mapPixel(tile, loaded_->file.gridH, mapScale_), k * glow});
    }
    mapModel_ = {mapTexture_ ? &mapSprite_ : nullptr, mapPlaces_,
                 mapPixel({t.x + static_cast<float>(h.x0), t.y + static_cast<float>(h.y0)},
                          loaded_->file.gridH, mapScale_),
                 mapLights_};
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

void App::cornerToast(std::string text) {
    if (!away()) {
        hud_.toast(std::move(text), true);
        return;
    }
    if (cornerToasts_.size() == tuning::kCornerToastsKept)
        cornerToasts_.erase(cornerToasts_.begin());
    cornerToasts_.push_back(std::move(text));
}

bool App::away() const {
    if (!loaded_) return false;
    const Vec2 t = cat_.iso().toTile(camera_.position());
    return t.x < 0 || t.y < 0 || t.x >= static_cast<float>(world_.width()) ||
           t.y >= static_cast<float>(world_.height());
}

void App::travelTo(int region) {
    if (!loaded_ || travel_.region >= 0) return;
    follow_.reset(); // the journey takes the camera away from whoever it followed
    closeCard();     // and the place's card stays behind
    travel_ = {region, 0, false};
    map_.open(false);
}

std::optional<App::Destination> App::travelDestination() const {
    if (travel_.region < 0 || travel_.jumped) return std::nullopt;
    const world::WorldFile& wf = loaded_->file;
    const auto mk = std::ranges::find(wf.markers, travel_.region, &world::Marker::region);
    if (travel_.region == wf.home.region || mk == wf.markers.end()) {
        // Home is framed clear of the interface, as frameCamera() will frame it.
        Camera framed = camera_;
        const Box safe = hud_.safeArea();
        framed.frame({safe.x, safe.y, safe.x + safe.w, safe.y + safe.h}, screen(),
                     openBounds(cat_, progress_.stage, world_));
        return Destination{framed.position(), framed.zoom()};
    }
    return Destination{
        gridToHome({static_cast<float>(mk->at.x) + 0.5f, static_cast<float>(mk->at.y) + 0.5f}),
        kZoomLevels[kDefaultZoomLevel]};
}

void App::updateWorld(float dt) {
    if (!worldView_) return;
    if (!away() && !cornerToasts_.empty()) {
        for (std::string& t : cornerToasts_) hud_.toast(std::move(t), true);
        cornerToasts_.clear();
    }
    followActor(dt);
    eventsSeenIn_ -= dt;
    if (eventsSeenIn_ <= 0) {
        eventsSeenIn_ = 1.0f;
        noteEvents();
    }
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
        // Whether the destination is whole is known once a frame of it has been drawn, and its
        // people are all there (city life fills the new area under the veil).
        const bool peopled = !city_ || !city_->city->arriving();
        const float hold = startVeil_ ? tuning::kStartHold : tuning::kTravelHold;
        if (travel_.jumped && held > 0 && ((worldView_->settled() && peopled) || held >= hold) &&
            travelFadeIn_ < 0)
            travelFadeIn_ = travel_.t;
        if (travelFadeIn_ >= 0 && travel_.t - travelFadeIn_ >= tuning::kTravelFadeIn) {
            travel_ = {};
            travelFadeIn_ = -1;
            startVeil_ = false;
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
        pipette_ = false;
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
    // Away from home its own panels rest: no wish tray (the wishes wait for the return).
    if (m.away) m.wishes = {};
    if (cardOpen_) {
        m.cardTitle = card_.title;
        if (font_.hasAll(card_.native)) m.cardNative = card_.native;
        m.cardEpithet = card_.epithet;
        m.cardText = card_.text;
    }
    m.places = journalPlaces_;
    // What the pointer rests on out in the world: its name.
    if (m.worldTip.empty() && tool_ == Tool::None && mouseInside_ && !hud_.wantsMouse()) {
        if (const auto pick = pickCard(mouse_)) {
            // Asked every frame while the pointer rests: the name is made when what is under
            // it changes, not each time.
            if (!(hoverPick_ == pick)) {
                hoverPick_ = pick;
                std::string storage;
                hoverCardName_.assign(entryName(cardOf(*pick), storage));
            }
            m.worldTip = hoverCardName_;
        } else if (const auto h = actorAt(mouse_)) {
            // Ordinary people by what they do (a potter, a courier); animals by their kind.
            if (const auto in = actorInfo(*h)) {
                const life::LifeData& d = city_->life->data;
                hoverName_ = in->role >= 0 ? d.regions[static_cast<std::size_t>(in->region)]
                                                 .roles[static_cast<std::size_t>(in->role)]
                                                 .name
                                           : d.kinds[static_cast<std::size_t>(in->kind)].name;
                m.worldTip = hoverName_;
            }
        }
    }
    if (follow_ && m.hint.empty() && !photo_)
        m.hint = strings::kFollowHint;
    else if (cardOpen_ && cardActor_.index != 0xFFFF && m.hint.empty() && !photo_)
        m.hint = strings::kFollowOffer;
}

} // namespace lc

namespace lc {

std::optional<life::CityLife::Info> App::actorInfo(life::Handle h) const {
    std::optional<life::CityLife::Info> out;
    if (!city_ || !city_->city->alive(h)) return out;
    city_->city->forEachInfo([&](const life::CityLife::Info& in) {
        if (in.handle == h) out = in;
    });
    return out;
}

const life::Figure* App::figureOf(const life::CityLife::Info& in) const {
    // A named figure by its kind, whether on its own day or walking in an event's cast.
    if (in.region < 0) return nullptr;
    for (const life::Figure& f :
         city_->life->data.regions[static_cast<std::size_t>(in.region)].figures)
        if (f.kind == in.kind) return &f;
    return nullptr;
}

std::optional<life::Handle> App::actorAt(Vec2 px) const {
    // Of the people under the pointer the frontmost, unless a named figure is among them.
    if (!worldView_ || !city_) return std::nullopt;
    const Vec2 w = view_.screenToWorld(px, screen());
    std::vector<life::Handle>& hits = actorHits_; // kept: asked every frame under the pointer
    worldView_->actorsAt({w.x + homeOffset_.x, w.y + homeOffset_.y}, hits);
    if (hits.empty()) return std::nullopt;
    for (const life::Handle h : hits)
        if (const auto in = actorInfo(h); in && figureOf(*in) != nullptr) return h;
    return hits.front();
}

std::optional<App::CardPick> App::pickCard(Vec2 px) const {
    // The corner's own things answer on its land; the world's everywhere else.
    if (!worldView_ || hover_) return std::nullopt;
    // A living figure (city life) under the pointer: its card from its region's figures.
    if (const auto h = actorAt(px))
        if (const auto in = actorInfo(*h))
            if (const life::Figure* f = figureOf(*in)) {
                const int region =
                    city_->life->data.regions[static_cast<std::size_t>(in->region)].worldRegion;
                if (regionFile(region) != nullptr) return CardPick{region, f, nullptr, -1, *h};
            }
    const Vec2 w = view_.screenToWorld(px, screen());
    const auto picked = worldView_->pick({w.x + homeOffset_.x, w.y + homeOffset_.y});
    if (!picked) return std::nullopt;
    CardPick r;
    if (picked->figure) {
        r.placed = &figures_[picked->index];
        r.region = r.placed->region;
    } else {
        const world::Placed& it = loaded_->map->items()[picked->index];
        r.item = static_cast<int>(picked->index);
        r.region = loaded_->map->regionAt({it.x, it.y});
    }
    if (regionFile(r.region) == nullptr) return std::nullopt;
    return r;
}

App::CardRef App::cardOf(const CardPick& p) const {
    if (p.living != nullptr)
        return {p.region, "figure:" + p.living->actor, p.living->card, p.actor};
    if (p.placed != nullptr) return {p.region, "figure:" + p.placed->actor, p.placed->card, {}};
    const world::WorldMap& m = *loaded_->map;
    const world::ItemInfo& info = m.info(m.items()[static_cast<std::size_t>(p.item)]);
    return {p.region, "landmark:" + info.id, info.card, {}};
}

std::optional<App::CardRef> App::cardAt(Vec2 px) const {
    if (const auto p = pickCard(px)) return cardOf(*p);
    return std::nullopt;
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
    // the card calls them otherwise (Q5-E-13: not "Kūruš (a memory)" under "Kūruš", nor
    // "Hermon, stonecutter" under "Hermon"). Landmarks' catalog names are descriptions.
    if (!c.entry.starts_with("figure:")) return {};
    const std::string_view id = std::string_view(c.entry).substr(7);
    const world::RegionFile* f = regionFile(c.region);
    const world::Card* card = f != nullptr ? f->card(c.card) : nullptr;
    for (const world::SetCatalog& s : loaded_->content->sets())
        for (const world::SetActor& a : s.actors)
            if (a.id == id &&
                (card == nullptr || !namedAlready(a.name, card->title, card->epithet)))
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
    cardActor_ = c->actor;
    recordEntry(*c, true);
    play(sfx::kOpen, tuning::kUiSfxLevel);
    return true;
}

void App::closeCard() {
    if (!cardOpen_) return;
    cardOpen_ = false;
    cardActor_ = {};
    play(sfx::kClose, tuning::kUiSfxLevel);
}

void App::followActor(float dt) {
    if (!follow_) return;
    const auto in = actorInfo(*follow_);
    if (!in) {
        follow_.reset(); // gone indoors or out of the area
        return;
    }
    // The camera eases onto them (critically damped, framerate-independent).
    Vec2 to = gridToHome(in->pos);
    to.y -= tuning::kFollowLift;
    const Vec2 at = camera_.position();
    const float k = 1.0f - std::exp(-dt * std::numbers::ln2_v<float> / tuning::kFollowHalfLife);
    camera_.nudge({(to.x - at.x) * k * camera_.scale(), (to.y - at.y) * k * camera_.scale()},
                  screen());
}

void App::noteEvents() {
    // Events running where the view is are witnessed: their card joins the region's journal.
    if (!city_) return;
    const TileRect v = cameraTiles();
    const life::LifeData& d = city_->life->data;
    for (const life::RunningEvent& e : city_->city->running()) {
        if (!e.active || e.event < 0) continue;
        const TilePos p{static_cast<int>(e.place.x), static_cast<int>(e.place.y)};
        if (!v.contains(p)) continue;
        const life::LifeRegion& lr = d.regions[static_cast<std::size_t>(e.region)];
        const world::RegionFile* f = regionFile(lr.worldRegion);
        if (f == nullptr) continue;
        const std::string& id = lr.events[static_cast<std::size_t>(e.event)].id;
        std::string card;
        if (const auto evs = f->life.find("events"); evs != f->life.end() && evs->is_array())
            for (const auto& ev : *evs)
                if (ev.value("id", "") == id) card = ev.value("card", "");
        if (card.empty() || f->card(card) == nullptr) continue;
        recordEntry({lr.worldRegion, "event:" + id, card, {}}, true);
    }
}

void App::noteArrival() {
    // What is in view on arrival counts as seen; a click on it finds it.
    worldView_->visibleCards(pickedScratch_);
    const world::WorldMap& m = *loaded_->map;
    for (const worldview::WorldView::Picked& p : pickedScratch_) {
        CardRef r;
        if (p.figure) {
            const world::FigurePlace& f = figures_[p.index];
            r = {f.region, "figure:" + f.actor, f.card, {}};
        } else {
            const world::Placed& it = m.items()[p.index];
            r = {m.regionAt({it.x, it.y}), "landmark:" + m.info(it).id, m.info(it).card, {}};
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
            const CardRef c{p.region, j.entry, j.card, {}};
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
                } else if (e.starts_with("event:")) {
                    const world::RegionFile* f = regionFile(r);
                    const std::string_view ev = std::string_view(e).substr(6);
                    if (const auto evs = f != nullptr ? f->life.find("events")
                                                      : nlohmann::json::const_iterator{};
                        f != nullptr && evs != f->life.end() && evs->is_array())
                        for (const auto& x : *evs)
                            if (x.value("id", "") == ev) card = x.value("card", "");
                    if (card.empty()) continue;
                } else {
                    continue;
                }
                recordEntry({r, e, card, {}}, found);
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

namespace lc {

void App::loadWorldAudio() {
    if (!soundscape_) return;
    mixer_.loadMore(assets_ / "audio", arriveFiles_, soundscape_->files());
    soundLoops_.clear();
    for (const std::string& f : soundscape_->files()) soundLoops_.push_back(mixer_.loopIndex(f));
    markDryLoops(soundscape_->files());
    for (std::size_t i = 0; i < soundLoops_.size(); ++i)
        if (soundscape_->isMusic(static_cast<int>(i))) mixer_.setLoopMusic(soundLoops_[i]);
}

void App::loadCityAudio() {
    if (!soundscape_ || !city_) return;
    citySound_ = std::make_unique<worldview::CitySound>(*loaded_, city_->life->data,
                                                        assets_ / "audio", seed_);
    mixer_.loadMore(assets_ / "audio", citySound_->effects(), citySound_->loops());
    cityLoops_.clear();
    cityFx_.clear();
    for (const std::string& f : citySound_->loops()) cityLoops_.push_back(mixer_.loopIndex(f));
    for (const std::string& f : citySound_->effects()) cityFx_.push_back(mixer_.sfxIndex(f));
    markDryLoops(citySound_->loops());
    for (const std::string& g : citySound_->guesses()) SDL_Log("sound: %s", g.c_str());
}

void App::markDryLoops(std::span<const std::string> files) {
    // The snow beds are muffled already: snow's low-pass leaves them as they are.
    for (const std::string& f : files)
        if (f.contains("snow")) mixer_.setLoopDry(mixer_.loopIndex(f), true);
}

bool App::snowLiesHere() const {
    // Snow lies where the view is: the climate there that month (the season's snow without a
    // world).
    return viewWeather_ ? viewWeather_->snow()
                        : cat_.seasons[static_cast<std::size_t>(season())].snow;
}

void App::updateWorldAudio(float night) {
    if (!soundscape_ || !worldView_) return;
    const worldview::ThemeMixer& theme = worldView_->theme();
    // Behind the front door the title drifts over the corner: its sound is the home's.
    const bool door = menus_.frontDoorOpen();
    const int homeRegion = loaded_->file.home.region;
    for (std::size_t r = 0; r < themeWeights_.size(); ++r)
        themeWeights_[r] = door ? (static_cast<int>(r) == homeRegion ? 1.0f : 0.0f)
                                : theme.weight(static_cast<int>(r));
    const Vec2 t = cat_.iso().toTile(camera_.position());
    const TileRect h = loaded_->file.home.rect;
    worldview::Soundscape::Input in;
    in.weights = themeWeights_;
    in.centre = {t.x + static_cast<float>(h.x0), t.y + static_cast<float>(h.y0)};
    in.halfView = screen().x * 0.5f / camera_.scale() / cat_.iso().tileW();
    in.clock = clock_.time();
    in.night = night;
    in.dt = frameDt_;
    // The year where the view is: the world calendar's season and month, rain and snow there.
    in.season = season();
    in.month = calendarMonth();
    in.rain = rainHere();
    const bool snowLies = snowLiesHere();
    in.snowCover = snowLies ? 1.0f : 0.0f;
    in.musicDuck = citySound_ ? citySound_->musicDuck() : 1.0f;
    soundscape_->update(in);
    // The soundscape and the city sound may name the same file: their wants combine (the
    // louder wins) before the mixer, so one never silences the other.
    loopWants_.begin(Mixer::maxLoops());
    const auto out = soundscape_->out();
    for (std::size_t i = 0; i < out.size(); ++i)
        loopWants_.want(soundLoops_[i], out[i].gain, out[i].pan);
    const auto apply = [&] {
        loopWants_.forEach([&](int loop, const LoopWants::Want& w) {
            mixer_.setLoopGain(loop, w.gain);
            mixer_.setLoopPan(loop, w.pan);
        });
    };
    for (const auto& [file, sample] : soundscape_->seeks())
        mixer_.seekLoop(soundLoops_[static_cast<std::size_t>(file)], sample);
    if (!citySound_ || !city_) {
        apply();
        return;
    }
    // The living city: crowds, wind, rain, work and events as the simulation shows them.
    worldview::CitySound::Input ci;
    ci.centre = in.centre;
    ci.halfView = in.halfView;
    ci.scale = camera_.scale();
    ci.away = 1.0f - soundscape_->homeWeight();
    ci.wind = weather_.wind().strength;
    ci.rain = rainHere();
    ci.snow = cat_.seasons[static_cast<std::size_t>(season())].snow;
    ci.snowCover = snowLies;
    ci.clock = clock_.time();
    ci.season = season();
    ci.month = in.month;
    ci.music = soundscape_->cityMusicLevel();
    ci.dt = frameDt_;
    ci.actors = worldView_->actorsDrawn();
    ci.city = city_->city.get();
    citySound_->update(ci);
    const auto co = citySound_->out();
    for (std::size_t i = 0; i < co.size(); ++i)
        loopWants_.want(cityLoops_[i], co[i].gain, co[i].pan);
    apply();
    for (const worldview::CitySound::Shot& sh : citySound_->shots())
        if (sh.effect >= 0 && cityFx_[static_cast<std::size_t>(sh.effect)] >= 0)
            mixer_.play(cityFx_[static_cast<std::size_t>(sh.effect)], sh.gain, sh.pitch, sh.pan);
}

std::optional<std::string> App::checkSound(std::span<const std::string> a) {
    // expect sound beds: every region plays a bed, loaded in the mixer, in each month of each
    // season by day (12:00) and by night (00:00). expect sound FILE|FAMILY MIN MAX: the gain
    // (x100) the world's sound sets that loop (or that family's loops together) to now.
    if (a.size() == 4 && a[0] == "mixer") {
        // expect mixer FILE MIN MAX: the gain (x100) the mixer was last asked for that loop,
        // whatever system asked.
        const int loop = mixer_.loopIndex(a[1]);
        if (loop < 0) return "the mixer has no " + a[1];
        const long v = std::lround(mixer_.loopTarget(loop) * 100.0f);
        if (v >= std::stol(a[2]) && v <= std::stol(a[3])) return std::nullopt;
        return std::format("expected mixer {} in {}..{} but found {}", a[1], a[2], a[3], v);
    }
    if (!soundscape_ || !loaded_) return std::string("no world sound");
    if (a.size() == 2 && a[1] == "beds") {
        int first = 0; // the season's first month
        for (std::size_t k = 0; k < cat_.seasons.size(); ++k) {
            for (int d = 0; d < cat_.seasonDays[k]; ++d)
                for (const float hour : {12.0f, 0.0f})
                    for (std::size_t r = 0; r < loaded_->file.regions.size(); ++r) {
                        const int month =
                            first + d < static_cast<int>(cat_.months.size()) ? first + d : -1;
                        const auto beds = soundscape_->bedsOf(
                            static_cast<int>(r), static_cast<int>(k), month, hour, false);
                        if (std::ranges::none_of(beds, [&](const std::string& f) {
                                return mixer_.loopIndex(f) >= 0;
                            }))
                            return std::format("{} plays no bed in {} (month {}) at {:02}:00",
                                               loaded_->file.regions[r].id, cat_.seasons[k].id,
                                               month, static_cast<int>(hour));
                    }
            first += cat_.seasonDays[k];
        }
        return std::nullopt;
    }
    if (a.size() != 4) return std::string("expect sound beds | expect sound FILE|FAMILY MIN MAX");
    std::string family = a[1];
    std::ranges::replace(family, '.', '_');
    const bool isFamily = !a[1].contains('/');
    const auto matches = [&](const std::string& f) {
        return isFamily ? f.starts_with("amb/world/" + family + "_") : f == a[1];
    };
    float g = 0;
    bool known = false;
    for (std::size_t i = 0; i < soundscape_->files().size(); ++i)
        if (matches(soundscape_->files()[i])) {
            known = true;
            g += soundscape_->out()[i].gain;
        }
    if (citySound_)
        for (std::size_t i = 0; i < citySound_->loops().size(); ++i)
            if (matches(citySound_->loops()[i])) {
                known = true;
                g += citySound_->out()[i].gain;
            }
    if (!known) return "the world plays no " + a[1];
    const long v = std::lround(g * 100.0f);
    if (v >= std::stol(a[2]) && v <= std::stol(a[3])) return std::nullopt;
    return std::format("expected sound {} in {}..{} but found {}", a[1], a[2], a[3], v);
}

float App::homeMusic() const {
    return soundscape_ ? soundscape_->homeMusic() : 1.0f;
}

float App::homeAmbience() const {
    return soundscape_ ? soundscape_->homeWeight() : 1.0f;
}

} // namespace lc

namespace lc {

void App::drawPlaceholderLabels(Painter& p) {
    // The debug overlay names what is drawn as a placeholder (the world itself stays quiet).
    if (!worldView_) return;
    worldView_->placeholdersInView(placeholderScratch_);
    const Font& f = p.font();
    for (const auto& [anchor, info] : placeholderScratch_) {
        const std::string& id = loaded_->content->item(static_cast<int>(info)).id;
        const Vec2 s =
            view_.worldToScreen({anchor.x - homeOffset_.x, anchor.y - homeOffset_.y}, screen());
        const float w = f.measure(Face::Body, id);
        p.text(Face::Body, id, std::round(s.x - w * 0.5f) + 1, std::round(s.y) + 1,
               theme::kCaptionShadow);
        p.text(Face::Body, id, std::round(s.x - w * 0.5f), std::round(s.y), theme::kWarn);
    }
}

} // namespace lc

namespace lc {

int App::calendarMonth() const {
    // The world calendar's month of the day (a kept season keeps its own months); -1 without one.
    return calendarDay(clock_.day(), seasonPin_, cat_.seasonDays,
                       static_cast<int>(cat_.months.size()))
        .month;
}

void App::followWorldWeather() {
    if (!viewWeather_) return;
    // One weather for the whole map: the home takes the world field's cells over its land, and
    // the view's field is what the renderer draws everywhere else.
    const SeasonDef& sd = cat_.seasons[static_cast<std::size_t>(season())];
    // Each region's snow by its climate, that month.
    const worldview::SeasonClimate sc{sd.showers, sd.clouds, sd.snow, calendarMonth(),
                                      clock_.day()};
    const TileRect h = loaded_->file.home.rect;
    const int m = tuning::kWorldWeatherMargin;
    homeWeather_->update(played_, weather_.wind(), sc, {h.x0 - m, h.y0 - m, h.x1 + m, h.y1 + m},
                         WeatherMode::Natural);
    homeCells_.assign(homeWeather_->cells().begin(), homeWeather_->cells().end());
    for (WeatherCell& c : homeCells_)
        c.centre = {c.centre.x - static_cast<float>(h.x0), c.centre.y - static_cast<float>(h.y0)};
    weather_.follow(homeCells_);
    const TileRect v = cameraTiles();
    viewWeather_->update(played_, weather_.wind(), sc, {v.x0 - m, v.y0 - m, v.x1 + m, v.y1 + m},
                         weather_.mode());
    if (worldView_) {
        worldView_->setWind(weather_.wind().dir, weather_.wind().strength, profile_.reduceMotion);
        // The clock's 0 is 06:00: the time of day from midnight for the snow's morning.
        worldView_->setCalendar(calendarMonth(),
                                static_cast<float>(std::fmod(clock_.time() + 0.25, 1.0)));
    }
}

TileRect App::cameraTiles() const {
    // The grid tiles under the window (a box around the view's diamond).
    const TileRect h = loaded_->file.home.rect;
    const float s = view_.scale();
    const Vec2 c = view_.position();
    const Vec2 half{screen().x * 0.5f / s, screen().y * 0.5f / s};
    const Iso iso = cat_.iso();
    float x0 = 1e9f, y0 = 1e9f, x1 = -1e9f, y1 = -1e9f;
    for (const Vec2 corner : {Vec2{c.x - half.x, c.y - half.y}, Vec2{c.x + half.x, c.y - half.y},
                              Vec2{c.x - half.x, c.y + half.y}, Vec2{c.x + half.x, c.y + half.y}}) {
        const Vec2 t = iso.toTile(corner);
        x0 = std::min(x0, t.x);
        y0 = std::min(y0, t.y);
        x1 = std::max(x1, t.x);
        y1 = std::max(y1, t.y);
    }
    return {static_cast<int>(std::floor(x0)) + h.x0, static_cast<int>(std::floor(y0)) + h.y0,
            static_cast<int>(std::ceil(x1)) + h.x0, static_cast<int>(std::ceil(y1)) + h.y0};
}

} // namespace lc
