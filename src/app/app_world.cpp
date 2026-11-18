// The game inside the world (docs/design/world-tech.md §4): the prebuilt world loaded through
// src/world and drawn through src/worldview as the one scene, with the home region at its place
// drawn by the game's own scene at the world renderer's turns.

#include "app/app_impl.hpp"

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
                                                        worldview::Hole{home.rect, box});
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
