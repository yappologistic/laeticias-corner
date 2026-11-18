// Scripted runs: synthesised input and state checks (the language is documented in script.hpp).

#include "app/app_impl.hpp"

#include <cmath>
#include <format>

namespace lc {
namespace {

constexpr int kDragSteps = 8;     // frames a scripted drag takes
constexpr int kRevealRetries = 3; // frames to wait for a drawer tile to scroll into view
constexpr std::string_view kPhotoDir = "photos";

std::string scaleName(float s) {
    return std::format("{:g}", s);
}

} // namespace

std::optional<Vec2> App::resolve(const ScriptPoint& p) {
    switch (p.kind) {
    case ScriptPoint::Kind::Pixel: return Vec2{p.x, p.y};
    case ScriptPoint::Kind::Tile:
        return camera_.worldToScreen(cat_.iso().toWorld(p.x + 0.5f, p.y + 0.5f), screen());
    case ScriptPoint::Kind::Widget:
        if (p.widget.starts_with("actor:")) {
            // The middle of the first actor of that kind (a visitor id, or the resident's).
            const std::string id = p.widget.substr(6);
            for (const Actor& a : actors_.all()) {
                if ((a.flags & actor_flag::kAlive) == 0 || cat_.kinds[a.kind].id != id ||
                    a.alpha < 0.5f)
                    continue;
                const Vec2 head = scene_->headOf(a);
                Vec2 foot = cat_.iso().toWorld(a.pos.x, a.pos.y);
                foot.y -= a.lift;
                return camera_.worldToScreen({(head.x + foot.x) * 0.5f, (head.y + foot.y) * 0.5f},
                                             screen());
            }
            return std::nullopt;
        }
        return hud_.widgetCentre(p.widget, ui_);
    }
    return std::nullopt;
}

void App::pushMouseMotion(Vec2 px) {
    SDL_Event e{};
    e.type = SDL_EVENT_MOUSE_MOTION;
    e.motion.windowID = SDL_GetWindowID(window_.get());
    e.motion.x = px.x / density_;
    e.motion.y = px.y / density_;
    e.motion.xrel = (px.x - mouse_.x) / density_;
    e.motion.yrel = (px.y - mouse_.y) / density_;
    if (!SDL_PushEvent(&e)) SDL_Log("script: %s", SDL_GetError());
}

void App::pushButton(Vec2 px, bool down, const ScriptCommand& c) {
    SDL_Event e{};
    e.type = down ? SDL_EVENT_MOUSE_BUTTON_DOWN : SDL_EVENT_MOUSE_BUTTON_UP;
    e.button.windowID = SDL_GetWindowID(window_.get());
    e.button.button = static_cast<Uint8>(c.right    ? SDL_BUTTON_RIGHT
                                         : c.middle ? SDL_BUTTON_MIDDLE
                                                    : SDL_BUTTON_LEFT);
    e.button.down = down;
    e.button.clicks = 1;
    e.button.x = px.x / density_;
    e.button.y = px.y / density_;
    if (!SDL_PushEvent(&e)) SDL_Log("script: %s", SDL_GetError());
}

void App::pushKey(std::string_view combo, bool down) {
    SDL_Keymod mod = SDL_KMOD_NONE;
    std::string name(combo);
    for (const auto& [prefix, m] :
         {std::pair{"ctrl+", SDL_KMOD_LCTRL}, std::pair{"shift+", SDL_KMOD_LSHIFT},
          std::pair{"alt+", SDL_KMOD_LALT}}) {
        for (auto pos = name.find(prefix); pos != std::string::npos; pos = name.find(prefix)) {
            name.erase(pos, std::string_view(prefix).size());
            mod = static_cast<SDL_Keymod>(mod | m);
        }
    }
    if (name == "equals" || name == "plus")
        name = "=";
    else if (name == "minus")
        name = "-";
    else if (name == "ctrl")
        name = "left ctrl";
    else if (name == "shift")
        name = "left shift";
    else if (name == "alt")
        name = "left alt";
    SDL_Event e{};
    e.type = down ? SDL_EVENT_KEY_DOWN : SDL_EVENT_KEY_UP;
    e.key.windowID = SDL_GetWindowID(window_.get());
    e.key.key = SDL_GetKeyFromName(name.c_str());
    e.key.scancode = SDL_GetScancodeFromKey(e.key.key, nullptr);
    // A held modifier key shows in the modifier state of later events, as with real input.
    if (e.key.key == SDLK_LCTRL) mod = static_cast<SDL_Keymod>(mod | (down ? SDL_KMOD_LCTRL : 0));
    if (e.key.key == SDLK_LSHIFT) mod = static_cast<SDL_Keymod>(mod | (down ? SDL_KMOD_LSHIFT : 0));
    if (e.key.key == SDLK_LALT) mod = static_cast<SDL_Keymod>(mod | (down ? SDL_KMOD_LALT : 0));
    e.key.mod = mod;
    e.key.down = down;
    if (e.key.key == SDLK_UNKNOWN)
        SDL_Log("script: unknown key '%s'", name.c_str());
    else if (!SDL_PushEvent(&e))
        SDL_Log("script: %s", SDL_GetError());
}

std::optional<std::string> App::check(const ScriptCommand& c) {
    const auto& a = c.args;
    const std::string& what = a[0];
    const auto mismatch = [&](const std::string& actual) {
        return std::format("expected {} {} but found {}", what, a.back(), actual);
    };
    const auto yesNo = [&](bool v) -> std::optional<std::string> {
        const bool want =
            a[1] == "yes" || a[1] == "on" || a[1] == "open" || a[1] == "true" || a[1] == "ok";
        return want == v ? std::nullopt : std::optional(mismatch(v ? "yes" : "no"));
    };
    const auto equal = [&](const std::string& have, const std::string& want) {
        return have == want ? std::nullopt : std::optional(mismatch(have));
    };
    const auto tileOf = [&]() -> std::optional<TilePos> {
        if (c.a.kind == ScriptPoint::Kind::Tile)
            return TilePos{static_cast<int>(c.a.x), static_cast<int>(c.a.y)};
        const auto px = resolve(c.a);
        if (!px) return std::nullopt;
        return cat_.iso().tileAt(camera_.screenToWorld(*px, screen()));
    };
    if (what == "tile" || what == "item") {
        const auto t = tileOf();
        if (!t || !world_.hasGround(*t)) return std::string("point is off the map");
        if (what == "tile")
            return equal(cat_.terrain[static_cast<std::size_t>(world_.terrainAt(*t))].id, a[2]);
        const Item* it = world_.itemAt(*t);
        return equal(it ? cat_.items[it->type].id : "none", a[2]);
    }
    if (what == "count") {
        if (a.size() != 3) return std::string("expect count ITEM N");
        int have = 0;
        if (a[1] == "all")
            have = static_cast<int>(world_.items().size());
        else if (const auto idx = cat_.findItem(a[1]))
            have = world_.itemCount(*idx);
        else
            return "unknown item " + a[1];
        return equal(std::to_string(have), a[2]);
    }
    if (what == "present") {
        if (a.size() != 3) return std::string("expect present VISITOR N");
        const auto v = cat_.findVisitor(a[1]);
        if (!v) return "unknown visitor " + a[1];
        return equal(std::to_string(actors_.present(*v)), a[2]);
    }
    if (what == "habitat") {
        // Everyone stands where it may (on its reserved seat counts: she sits on the bench).
        int bad = 0;
        for (const Actor& ac : actors_.all()) {
            if ((ac.flags & actor_flag::kAlive) == 0 || (ac.flags & actor_flag::kLeaving) != 0 ||
                ac.state == ActorState::Inside)
                continue;
            const ActorKind& k = cat_.kinds[ac.kind];
            const TilePos t{static_cast<int>(std::floor(ac.pos.x)),
                            static_cast<int>(std::floor(ac.pos.y))};
            const bool seated = ac.reserved && world_.itemAt(t) != nullptr &&
                                world_.itemAt(t)->pos == TilePos{ac.resX, ac.resY};
            const bool ok =
                k.visitor >= 0
                    ? habitatAllows(cat_.visitors[static_cast<std::size_t>(k.visitor)].habitat,
                                    world_, cat_, ac.pos) ||
                          passable(world_, cat_, k.move, t, true)
                    : passable(world_, cat_, Locomotion::Walk, t);
            if (!ok && !seated) ++bad;
        }
        return yesNo(bad == 0);
    }
    if (what == "actor") {
        // expect actor KIND ANIM|moving|inside|any [ITEM]: one of that kind is doing that now
        // (and, with ITEM, on or beside that item: its reserved slot is on one).
        if (a.size() < 3) return std::string("expect actor KIND ANIM|moving|inside|any [ITEM]");
        const auto kind = std::ranges::find(cat_.kinds, a[1], &ActorKind::id);
        if (kind == cat_.kinds.end()) return "unknown actor kind " + a[1];
        const auto ki = static_cast<std::uint16_t>(kind - cat_.kinds.begin());
        const auto item = a.size() > 3 ? cat_.findItem(a[3]) : std::nullopt;
        if (a.size() > 3 && !item) return "unknown item " + a[3];
        for (const Actor& ac : actors_.all()) {
            if ((ac.flags & actor_flag::kAlive) == 0 || ac.kind != ki) continue;
            const std::string& anim = kind->anims[ac.overlay > 0 ? ac.overlayAnim : ac.anim];
            const bool doing = a[2] == "any" ||
                               (a[2] == "moving" && ac.state == ActorState::Travel) ||
                               (a[2] == "inside" && ac.state == ActorState::Inside) ||
                               (ac.state == ActorState::Act && anim == a[2]) ||
                               ((ac.flags & actor_flag::kOnHat) != 0 && a[2] == "hat");
            const bool at = !item || (ac.reserved && ac.resType == *item);
            if (doing && at) return std::nullopt;
        }
        return std::format("no {} is {}{}", a[1], a[2], a.size() > 3 ? " at a " + a[3] : "");
    }
    if (what == "bubble") {
        const bool showing = speech_.showing(simTime_) != nullptr;
        return yesNo(showing);
    }
    if (what == "raining") return yesNo(raining());
    if (what == "weather") {
        static constexpr std::string_view kModes[] = {"natural", "rain", "clear"};
        return equal(std::string(kModes[static_cast<std::size_t>(weather_.mode())]), a[1]);
    }
    if (what == "event") {
        // expect event SHOW yes|no: an event of that show is running now.
        static constexpr std::pair<std::string_view, EventShow> kShows[] = {
            {"rainbow", EventShow::Rainbow},
            {"gust", EventShow::Gust},
            {"chorus", EventShow::Chorus},
            {"smoke", EventShow::Smoke},
            {"firefly_sync", EventShow::FireflySync},
            {"frog_chorus", EventShow::FrogChorus}};
        if (a.size() != 3) return std::string("expect event SHOW yes|no");
        for (const auto& [n, show] : kShows)
            if (n == a[1])
                return events_.active(show) == (a[2] == "yes")
                           ? std::nullopt
                           : std::optional(std::format("event {} is {}running", a[1],
                                                       events_.active(show) ? "" : "not "));
        return "unknown event show " + a[1];
    }
    if (what == "lively") {
        // expect lively MIN CAP HMIN HCAP SHARE: of the samples taken since `set lively reset`,
        // at least SHARE had MIN..CAP purposeful movers in view and HMIN..HCAP happenings in the
        // last minute.
        if (a.size() != 6) return std::string("expect lively MIN CAP HMIN HCAP SHARE");
        const LivelyReport r =
            lively_.check(std::stoi(a[1]), std::stoi(a[2]), std::stoi(a[3]), std::stoi(a[4]));
        SDL_Log("script: lively: %d samples, %d too quiet, %d too busy, movers %d..%d, "
                "happenings up to %d a minute",
                r.samples, r.quiet, r.busy, r.moversMin, r.moversMax, r.happeningsMax);
        return r.samples > 0 && r.share() >= std::stof(a[5])
                   ? std::nullopt
                   : std::optional(std::format("lively: only {:.0f}% of {} samples within the rule",
                                               r.share() * 100.0f, r.samples));
    }
    if (what == "tool") {
        static constexpr std::string_view kNames[] = {"none", "place", "paint", "remove", "move"};
        return equal(std::string(kNames[static_cast<std::size_t>(tool_)]), a[1]);
    }
    if (what == "drawer") return yesNo(drawerOpen_);
    if (what == "profiler") return yesNo(profilerOn_);
    if (what == "grid") return yesNo(grid_);
    if (what == "footprints") return yesNo(footprintsHeld_);
    if (what == "carrying") return yesNo(carry_.has_value());
    if (what == "pipette") return yesNo(pipette_);
    if (what == "brush") return equal(std::to_string(brush_), a[1]);
    if (what == "journal") return yesNo(journalOpen_);
    if (what == "photo") return yesNo(photo_);
    if (what == "undo") return yesNo(editor_.canUndo());
    if (what == "redo") return yesNo(editor_.canRedo());
    if (what == "muted") return yesNo(muted_);
    if (what == "rain") return yesNo(weather_.mode() == WeatherMode::Rain);
    if (what == "saved") {
        writer_.flush(); // what has been saved by now is on disk
        std::error_code ec;
        return yesNo(fs::is_regular_file(worldDir() / kWorldFile, ec));
    }
    if (what == "file") {
        if (a.size() != 3) return std::string("expect file PATH yes|no");
        writer_.flush();
        std::error_code ec;
        const bool want = a[2] == "yes";
        return fs::exists(saveDir_ / a[1], ec) == want
                   ? std::nullopt
                   : std::optional(std::format("expected {} to {}exist", a[1], want ? "" : "not "));
    }
    if (what == "widget") {
        if (a.size() != 3) return std::string("expect widget NAME yes|no");
        const bool have = hud_.widgetCentre(a[1], ui_).has_value();
        return have == (a[2] == "yes")
                   ? std::nullopt
                   : std::optional(std::format("widget {} {}shown", a[1], have ? "" : "not "));
    }
    if (what == "wish") {
        const auto w = cat_.findWish(a[1]);
        if (!w || a.size() != 3) return std::string("expect wish ID open|done|waiting");
        static constexpr std::string_view kStates[] = {"waiting", "open", "done"};
        return equal(std::string(kStates[static_cast<std::size_t>(
                         progress_.wishes[static_cast<std::size_t>(*w)].state)]),
                     a[2]);
    }
    if (what == "season") return equal(cat_.seasons[static_cast<std::size_t>(season())].id, a[1]);
    if (what == "day") return equal(std::to_string(clock_.day()), a[1]);
    if (what == "harvests") return equal(std::to_string(progress_.harvests), a[1]);
    if (what == "growth") {
        const Item* it = world_.itemAt({static_cast<int>(c.a.x), static_cast<int>(c.a.y)});
        return equal(it ? std::to_string(it->stage) : std::string("none"), a[2]);
    }
    if (what == "stage") return equal(std::to_string(progress_.stage), a[1]);
    if (what == "wishes") return equal(std::to_string(progress_.open.size()), a[1]);
    if (what == "ribbon") return yesNo(hud_.ribbonShowing());
    if (what == "nook") {
        const auto n = cat_.findNook(a[1]);
        if (!n || a.size() != 3) return std::string("expect nook ID yes|no");
        const bool found = progress_.nooks[static_cast<std::size_t>(*n)] != 0;
        return found == (a[2] == "yes")
                   ? std::nullopt
                   : std::optional(std::format("nook {} {}found", a[1], found ? "" : "not "));
    }
    if (what == "sketch") {
        static constexpr std::string_view kTabs[] = {"wishes", "visitors", "nooks"};
        return equal(std::string(kTabs[static_cast<std::size_t>(hud_.sketchTab())]), a[1]);
    }
    if (what == "zoom") return equal(scaleName(camera_.zoom()), a[1]);
    if (what == "stem") {
        // expect stem FILE MIN: in an audio capture, the stem has faded in at least that far.
        if (a.size() != 3 || !opts_.audioOut) return std::string("expect stem FILE MIN (capture)");
        const float level = mixer_.stemLevel(mixer_.loopIndex(a[1]));
        return level >= std::stof(a[2])
                   ? std::nullopt
                   : std::optional(std::format("stem {} at {:.2f}", a[1], level));
    }
    if (what == "toast") {
        if (a.size() == 2 && (a[1] == "yes" || a[1] == "no")) return yesNo(hud_.toastShowing());
        // expect toast WORDS...: the toast showing now contains them.
        std::string want;
        for (std::size_t i = 1; i < a.size(); ++i) want += (i > 1 ? " " : "") + a[i];
        return hud_.toastText().find(want) != std::string_view::npos
                   ? std::nullopt
                   : std::optional(
                         std::format("toast is \"{}\", not \"{}\"", hud_.toastText(), want));
    }
    if (what == "panning") return yesNo(std::ranges::any_of(keyPan_, [](bool k) { return k; }));
    if (what == "phase") return equal(std::string(phaseId(clock_.phase())), a[1]);
    if (what == "seen") {
        const auto v = cat_.findVisitor(a[1]);
        if (!v) return "unknown visitor " + a[1];
        const bool want = a.size() < 3 || a[2] == "yes";
        return actors_.seen(*v) == want
                   ? std::nullopt
                   : std::optional(std::format("visitor {} {}seen", a[1], want ? "not " : ""));
    }
    if (what == "photos") {
        int n = 0;
        std::error_code ec;
        for (auto it = fs::directory_iterator(saveDir_ / kPhotoDir, ec);
             !ec && it != fs::directory_iterator(); ++it)
            n += it->path().extension() == ".png" ? 1 : 0;
        return equal(std::to_string(n), a[1]);
    }
    if (what == "luma" || what == "color") {
        const auto r = parseScriptRect(a[1]);
        if (!r) return "bad rectangle " + a[1];
        const SDL_Rect rect{r->x, r->y, r->w, r->h};
        const SurfacePtr px{SDL_RenderReadPixels(renderer_.get(), &rect)};
        if (!px) return std::string("cannot read pixels: ") + SDL_GetError();
        double sum[3] = {0, 0, 0};
        for (int y = 0; y < px->h; ++y)
            for (int x = 0; x < px->w; ++x) {
                Uint8 cr = 0, cg = 0, cb = 0, ca = 0;
                if (!SDL_ReadSurfacePixel(px.get(), x, y, &cr, &cg, &cb, &ca))
                    return std::string("cannot read pixels: ") + SDL_GetError();
                sum[0] += cr;
                sum[1] += cg;
                sum[2] += cb;
            }
        const double n = static_cast<double>(px->w) * px->h;
        const double m[3] = {sum[0] / n, sum[1] / n, sum[2] / n};
        if (what == "luma") {
            const double l = 0.2126 * m[0] + 0.7152 * m[1] + 0.0722 * m[2];
            const double lo = std::stod(a[2]);
            const double hi = std::stod(a[3]);
            return l >= lo && l <= hi ? std::nullopt
                                      : std::optional(std::format(
                                            "expected luma of {} within {}..{} but found {:.1f}",
                                            a[1], a[2], a[3], l));
        }
        const double tol = std::stod(a[5]);
        for (int k = 0; k < 3; ++k)
            if (std::abs(m[k] - std::stod(a[static_cast<std::size_t>(2 + k)])) > tol)
                return std::format("expected colour of {} near {} {} {} but found {:.0f} {:.0f} "
                                   "{:.0f}",
                                   a[1], a[2], a[3], a[4], m[0], m[1], m[2]);
        return std::nullopt;
    }
    return "unknown expectation '" + what + "'";
}

// Runs the script for one frame. Returns false when the script asks to stop.
bool App::scriptStep() {
    if (scriptWait_ > 0) {
        --scriptWait_;
        return true;
    }
    while (scriptPos_ < script_.size()) {
        const ScriptCommand& c = script_[scriptPos_];
        const auto fail = [&](const std::string& why) {
            SDL_Log("script line %d: %s", c.line, why.c_str());
            exitCode_ = 1;
            return false;
        };
        const auto next = [&] {
            ++scriptPos_;
            scriptPhase_ = 0;
            scriptRetries_ = 0;
        };
        // A drawer tile off the current page is scrolled into view, then tried again.
        const auto at = [&](const ScriptPoint& p) -> std::optional<Vec2> { return resolve(p); };
        const auto pending = [&](const ScriptPoint& p) {
            if (p.kind != ScriptPoint::Kind::Widget || scriptRetries_ >= kRevealRetries ||
                !hud_.reveal(p.widget, ui_))
                return false;
            ++scriptRetries_;
            return true;
        };
        using K = ScriptCommand::Kind;
        switch (c.kind) {
        case K::Move:
        case K::Press:
        case K::Release: {
            const auto p = at(c.a);
            if (!p) return pending(c.a) || fail("cannot resolve point");
            pushMouseMotion(*p);
            if (c.kind != K::Move) pushButton(*p, c.kind == K::Press, c);
            next();
            return true;
        }
        case K::Click: {
            const auto p = at(c.a);
            if (!p) return pending(c.a) || fail("cannot resolve point");
            if (scriptPhase_ == 0) {
                pushMouseMotion(*p);
                pushButton(*p, true, c);
                scriptPhase_ = 1;
            } else {
                pushButton(*p, false, c);
                next();
            }
            return true;
        }
        case K::Drag: {
            if (scriptPhase_ == 0) {
                const auto p = at(c.a);
                if (!p) return pending(c.a) || fail("cannot resolve point");
                // Resolve the end point now: dragging may move the camera.
                const auto q = at(c.b);
                if (!q) return fail("cannot resolve point");
                pushMouseMotion(*p);
                pushButton(*p, true, c);
                script_[scriptPos_].a = {ScriptPoint::Kind::Pixel, p->x, p->y, {}};
                script_[scriptPos_].b = {ScriptPoint::Kind::Pixel, q->x, q->y, {}};
                scriptPhase_ = 1;
                return true;
            }
            const float k = static_cast<float>(scriptPhase_) / kDragSteps;
            const Vec2 p{c.a.x + (c.b.x - c.a.x) * k, c.a.y + (c.b.y - c.a.y) * k};
            if (scriptPhase_ <= kDragSteps) {
                pushMouseMotion(p);
                ++scriptPhase_;
            } else {
                pushButton({c.b.x, c.b.y}, false, c);
                next();
            }
            return true;
        }
        case K::Key:
            if (scriptPhase_ == 0) {
                pushKey(c.args[0], true);
                scriptPhase_ = 1;
            } else {
                pushKey(c.args[0], false);
                next();
            }
            return true;
        case K::KeyDown:
        case K::KeyUp:
            pushKey(c.args[0], c.kind == K::KeyDown);
            next();
            return true;
        case K::Wheel: {
            const auto p = c.hasPoint ? at(c.a) : std::optional(mouse_);
            if (!p) return fail("cannot resolve point");
            if (c.hasPoint) pushMouseMotion(*p);
            SDL_Event e{};
            e.type = SDL_EVENT_MOUSE_WHEEL;
            e.wheel.windowID = SDL_GetWindowID(window_.get());
            e.wheel.y = c.amount;
            e.wheel.mouse_x = p->x / density_;
            e.wheel.mouse_y = p->y / density_;
            if (!SDL_PushEvent(&e)) SDL_Log("script: %s", SDL_GetError());
            next();
            return true;
        }
        case K::Wait:
            scriptWait_ = static_cast<int>(c.amount) - 1;
            next();
            if (scriptWait_ >= 0) return true;
            scriptWait_ = 0;
            continue;
        case K::Shot:
            // Taken after this frame renders; see run().
            return true;
        case K::Set:
            if (c.args[0] == "clock") {
                const auto pin = parsePin(c.args[1]);
                if (!pin) return fail("unknown clock value " + c.args[1]);
                clock_.setPin(*pin, true);
            } else if (c.args[0] == "unlock") {
                progress_.unlockEverything(cat_);
            } else if (c.args[0] == "played") {
                // "+S" moves it on by S; a plain number sets it (never backwards).
                const double v = std::stod(c.args[1]);
                played_ = c.args[1].starts_with('+') ? played_ + v : std::max(played_, v);
            } else if (c.args[0] == "season") {
                seasonPin_ = c.args[1] == "auto" ? -1 : cat_.findSeason(c.args[1]).value_or(-2);
                if (seasonPin_ < -1) return fail("unknown season " + c.args[1]);
                seasonByPin_ = true; // as the calendar's pin: the grade glides quickly
            } else if (c.args[0] == "wish") {
                // set wish ID open: offered now, as if its giver had asked.
                const auto w = cat_.findWish(c.args[1]);
                if (!w) return fail("unknown wish " + c.args[1]);
                WishProgress& wp = progress_.wishes[static_cast<std::size_t>(*w)];
                if (wp.state == WishState::Waiting) {
                    wp.state = WishState::Open;
                    progress_.open.push_back(*w);
                    progression_.evaluate(world_, progress_, facts(), played_);
                }
            } else if (c.args[0] == "grow") {
                growBeds(std::stof(c.args[1]));
            } else if (c.args[0] == "day") {
                clock_.setDay(std::stoi(c.args[1]));
            } else if (c.args[0] == "weather") {
                static constexpr std::pair<std::string_view, WeatherMode> kModes[] = {
                    {"natural", WeatherMode::Natural},
                    {"rain", WeatherMode::Rain},
                    {"clear", WeatherMode::Clear}};
                bool ok = false;
                for (const auto& [n, m] : kModes)
                    if (n == c.args[1]) {
                        weather_.setMode(m);
                        ok = true;
                    }
                if (!ok) return fail("unknown weather " + c.args[1]);
            } else if (c.args[0] == "camera") {
                // set camera TX TY ZOOM: look at a tile at one of the zoom levels.
                if (c.args.size() != 4) return fail("set camera TX TY ZOOM");
                camera_.place(cat_.iso().toWorld(std::stof(c.args[1]), std::stof(c.args[2])),
                              std::stof(c.args[3]), screen());
            } else if (c.args[0] == "look") {
                // set look KIND ZOOM: the camera on the first actor of that kind.
                if (c.args.size() != 3) return fail("set look KIND ZOOM");
                bool found = false;
                for (const Actor& a : actors_.all())
                    if ((a.flags & actor_flag::kAlive) != 0 && cat_.kinds[a.kind].id == c.args[1]) {
                        camera_.place(cat_.iso().toWorld(a.pos.x, a.pos.y), std::stof(c.args[2]),
                                      screen());
                        found = true;
                        break;
                    }
                if (!found) return fail("no " + c.args[1] + " to look at");
            } else if (c.args[0] == "shower") {
                weather_.shower();
            } else if (c.args[0] == "lively") {
                lively_.reset();
            } else if (c.args[0] == "chatter") {
                profile_.chatty = c.args[1] != "quiet";
            } else if (c.args[0] == "time") {
                // The clock to a time of day (0..1), keeping its pin state.
                clock_.setTime(std::stod(c.args[1]));
            } else if (c.args[0] == "land") {
                const int to =
                    std::min(std::stoi(c.args[1]), static_cast<int>(cat_.stages.size()) - 1);
                while (progress_.stage < to) openLand(++progress_.stage, false);
            } else {
                weather_.setMode(c.args[1] == "on" ? WeatherMode::Rain : WeatherMode::Natural);
            }
            next();
            continue;
        case K::Expect:
            if (c.a.kind == ScriptPoint::Kind::Widget && !resolve(c.a) && pending(c.a)) return true;
            if (const auto err = check(c)) return fail(*err);
            next();
            continue;
        case K::Fast: {
            // Simulation only, step after step; with an expectation, until it holds.
            const auto steps = static_cast<long long>(c.amount / tuning::kStepSeconds);
            std::optional<std::string> err = c.args.empty() ? std::nullopt : check(c);
            for (long long n = 0; n < steps && (c.args.empty() || err); ++n) {
                step(static_cast<float>(tuning::kStepSeconds));
                if (opts_.audioOut) {
                    // The mix keeps time with the simulation, so a capture can cover minutes.
                    updateAudio();
                    captureAudio(1);
                }
                if (!c.args.empty()) err = check(c);
            }
            if (!c.args.empty() && err) return fail("fast-forwarded in vain: " + *err);
            next();
            return true;
        }
        case K::WaitFor: {
            // Frames left in scriptPhase_ (counted up from 0).
            const auto err = check(c);
            if (!err) {
                next();
                continue;
            }
            if (++scriptPhase_ >= static_cast<int>(c.amount))
                return fail("waited in vain: " + *err);
            return true;
        }
        case K::Place: {
            const auto type = cat_.findItem(c.args[0]);
            if (!type) return fail("unknown item " + c.args[0]);
            const auto& def = cat_.items[static_cast<std::size_t>(*type)];
            const int v = static_cast<int>(c.amount);
            if (v < 0 || v >= def.count) return fail("variant out of range");
            // As the build drawer would: only unlocked pieces can be placed.
            if (progress_.items[static_cast<std::size_t>(*type)] == 0)
                return fail(c.args[0] + " is not unlocked");
            const Item item =
                makeItem(cat_, *type, v, {static_cast<int>(c.a.x), static_cast<int>(c.a.y)});
            const bool fresh = world_.itemCount(*type) == 0;
            editor_.begin();
            const auto r = editor_.place(world_, cat_, item);
            editor_.commit();
            if (r != PlaceResult::Ok) return fail("cannot place " + c.args[0] + " there");
            scene_->onPlaced(item, rng_);
            disturbed(item.rect(), item.type, fresh);
            markDirty();
            next();
            continue;
        }
        case K::Paint: {
            const auto terrain = cat_.findTerrain(c.args[0]);
            if (!terrain) return fail("unknown terrain " + c.args[0]);
            if (progress_.terrain[static_cast<std::size_t>(*terrain)] == 0)
                return fail(c.args[0] + " is not unlocked");
            const ScriptPoint& b = c.hasPoint ? c.b : c.a;
            editor_.begin();
            for (int y = static_cast<int>(std::min(c.a.y, b.y));
                 y <= static_cast<int>(std::max(c.a.y, b.y)); ++y)
                for (int x = static_cast<int>(std::min(c.a.x, b.x));
                     x <= static_cast<int>(std::max(c.a.x, b.x)); ++x)
                    if (editor_.paint(world_, cat_, {x, y}, *terrain) == PaintResult::Ok &&
                        *terrain == cat_.waterTerrain)
                        disturbed({x, y, x + 1, y + 1}, -1, false);
            editor_.commit();
            markDirty();
            next();
            continue;
        }
        case K::Quit: return false;
        }
    }
    return false; // the script ran out: done
}

} // namespace lc
