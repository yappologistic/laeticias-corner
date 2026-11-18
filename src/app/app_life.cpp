// The living corner in the app: actors, weather, events and the resident's speech fed from the
// game's state each step, and what they do turned into sound, effects and bubbles.

#include "app/app_impl.hpp"
#include "core/growth.hpp"
#include "core/land.hpp"
#include "ui/strings.hpp"

#include <algorithm>
#include <cmath>
#include <format>

namespace lc {
namespace {

constexpr std::string_view kPetSound = "sfx/pet.wav";
constexpr std::string_view kFlapSound = "sfx/flap.wav";
constexpr std::string_view kGoodsSound = "sfx/pick.wav";
constexpr std::string_view kDiscoverSound = "sfx/discover.wav";

Vec2 middle(TilePos t) {
    return {static_cast<float>(t.x) + 0.5f, static_cast<float>(t.y) + 0.5f};
}

} // namespace

Vec2 App::viewTile() const {
    return cat_.iso().toTile(camera_.position());
}

float App::rainHere() const {
    return weather_.rainAt(viewTile());
}

bool App::raining() const {
    return weather_.raining(viewTile());
}

void App::cycleWeather() {
    // As it comes, rain here, clear here.
    switch (weather_.mode()) {
    case WeatherMode::Natural: weather_.setMode(WeatherMode::Rain); break;
    case WeatherMode::Rain: weather_.setMode(WeatherMode::Clear); break;
    case WeatherMode::Clear: weather_.setMode(WeatherMode::Natural); break;
    }
    markDirty();
}

ActorEnv App::actorEnv() const {
    ActorEnv env;
    env.world = &world_;
    env.area = activeArea();
    env.gates = gates_;
    env.clock = clock_.time();
    env.pinned = clock_.pin() != ClockPin::Auto;
    env.phase = clock_.phase();
    env.season = season();
    env.day = clock_.day();
    env.facts = facts();
    env.weather = &weather_;
    env.snow = cat_.seasons[static_cast<std::size_t>(season())].snow;
    env.prefer = prefer_;
    env.nooks = nookPlaces_;
    env.now = played_;
    return env;
}

void App::refreshNooks() {
    // Nook areas weigh what actors choose (`prefer`) and are places to stroll to; gathered again
    // only when the world or the set of nooks changes.
    const auto here = progression_.nookHere();
    if (world_.revision() == nookRevision_ && std::ranges::equal(here, nookSeen_)) return;
    nookRevision_ = world_.revision();
    nookSeen_.assign(here.begin(), here.end());
    prefer_.clear();
    nookPlaces_.clear();
    std::vector<NearInstance> found;
    for (std::size_t n = 0; n < cat_.nooks.size(); ++n) {
        if (here[n] == 0) continue;
        const NookDef& def = cat_.nooks[n];
        cat_.conditions.instances(def.near, world_, found);
        for (const NearInstance& in : found) {
            nookPlaces_.push_back({static_cast<int>(n), in});
            for (const auto& [who, activity] : def.prefer)
                prefer_.push_back({who < 0 ? cat_.residentKind : who, activity, in});
        }
    }
}

void App::updateLife(float dt) {
    const Uint64 start = SDL_GetPerformanceCounter();
    const auto msSince = [](Uint64 t) {
        return static_cast<double>(SDL_GetPerformanceCounter() - t) * 1000.0 /
               static_cast<double>(SDL_GetPerformanceFrequency());
    };
    weather_.update(dt, season(), openBounds(cat_, progress_.stage, world_));
    refreshNooks();
    if (world_.revision() != fallRevision_) {
        // Water at the rims falls over them: the waterfall's bed comes from there. The rim tiles
        // (ground with no ground beyond it to the south-east or south-west) never change, so
        // they are found once per map and each edit looks at them alone (Q3-09).
        fallRevision_ = world_.revision();
        if (rimTiles_.empty() || rimOf_ != world_.bounds()) {
            rimOf_ = world_.bounds();
            rimTiles_.clear();
            for (int y = 0; y < world_.height(); ++y)
                for (int x = 0; x < world_.width(); ++x)
                    if (world_.hasGround({x, y}) &&
                        (!world_.hasGround({x + 1, y}) || !world_.hasGround({x, y + 1})))
                        rimTiles_.push_back({x, y});
        }
        fallCount_ = 0;
        Vec2 sum;
        for (const TilePos t : rimTiles_) {
            if (!world_.isWater(t) || world_.isWild(t)) continue;
            ++fallCount_;
            sum = {sum.x + static_cast<float>(t.x) + 0.5f, sum.y + static_cast<float>(t.y) + 0.5f};
        }
        if (fallCount_ > 0)
            fallCentre_ = {sum.x / static_cast<float>(fallCount_),
                           sum.y / static_cast<float>(fallCount_)};
    }
    const ActorEnv env = actorEnv();
    const int blockBefore = actors_.resident() >= 0
                                ? actors_.all()[static_cast<std::size_t>(actors_.resident())].sched
                                : -1;
    const Uint64 t0 = SDL_GetPerformanceCounter();
    actors_.update(env, dt);
    actorMs_ = msSince(t0);
    actors_.lookAt(tool_ == Tool::None ? hover_ : std::nullopt);
    handleActorEvents();
    if (actors_.resident() >= 0 &&
        actors_.all()[static_cast<std::size_t>(actors_.resident())].sched != blockBefore)
        lively_.happening(simTime_); // her day turned to its next part

    // Events: the season's first dawn, rain reaching or leaving the view, the rest by schedule.
    const Phase phase = clock_.phase();
    EventEnv ev;
    ev.world = &world_;
    ev.facts = env.facts;
    ev.phase = phase;
    ev.season = season();
    ev.day = clock_.day();
    ev.hour = static_cast<float>(std::fmod(6.0 + 24.0 * clock_.time(), 24.0));
    ev.seasonDawn = phase == Phase::Dawn && lastPhase_ == Phase::Night &&
                    clock_.pin() == ClockPin::Auto &&
                    seasonOf(clock_.day(), cat_.seasonDays).day == 0;
    ev.now = simTime_;
    lastPhase_ = phase;
    events_.update(ev, dt);
    handleWorldEvents();
    const bool rain = raining(); // the view: rain reaching or leaving it is a happening
    if (rain != rainWas_) lively_.happening(simTime_);
    rainWas_ = rain;
    scene_->cooking(events_.active(EventShow::Smoke) ? actors_.residentHome() : std::nullopt);

    // Her idle remarks (when chatty), and a word when a bed has been ripe a while.
    if (profile_.chatty && simTime_ >= idleLineAt_ && actors_.residentAvailable()) {
        idleLineAt_ = simTime_ + rng_.range(tuning::kIdleLineMin, tuning::kIdleLineMax);
        const Actor& r = actors_.all()[static_cast<std::size_t>(actors_.resident())];
        const auto& names = cat_.kinds[r.kind].anims;
        // Her remark fits the moment: rain where she is, the evening, or an ordinary day
        // (Q3-16); a moment without lines of its own passes quietly.
        const bool wet = weather_.raining(r.pos);
        const Phase ph = clock_.phase();
        const int context = wet ? cat_.resident.context("idle_rain")
                            : ph == Phase::Night || ph == Phase::Dusk
                                ? cat_.resident.context("idle_night")
                                : cat_.resident.context("idle");
        if (context >= 0 && (r.state != ActorState::Act || names[r.anim] != "read"))
            (void)speak(context, SpeechWeight::Idle);
    }
    if (anyRipe_ && ripeDay_ != clock_.day()) {
        ripeDay_ = clock_.day();
        ripeSince_ = played_;
    }
    if (ripeSince_ >= 0 && played_ - ripeSince_ > tuning::kRipeLineDelay) {
        ripeSince_ = -1;
        if (anyRipe_ && progress_.lastHarvestDay != clock_.day())
            (void)speak(cat_.resident.context("harvest_ready"), SpeechWeight::Routine);
    }
    if (simTime_ >= livelyAt_) {
        livelyAt_ = simTime_ + 1.0;
        lively_.sample(moversInView(), simTime_);
    }
    lifeMs_ = msSince(start) - actorMs_;
}

void App::handleActorEvents() {
    for (const ActorEvent& e : actors_.events()) {
        const ActorKind& k = cat_.kinds[static_cast<std::size_t>(e.kind_)];
        switch (e.kind) {
        case ActorEvent::Kind::Arrived: {
            const auto& def =
                cat_.visitors[static_cast<std::size_t>(e.arg >= 0 ? e.arg : k.visitor)];
            lively_.happening(simTime_);
            if (!e.first) break;
            hud_.toast(std::string(strings::kToastNewVisitor) + def.name);
            play(kDiscoverSound);
            if (!k.voice.empty()) playAt(k.voice, tuning::kVoiceLevel, e.pos, true);
            markDirty();
            // She remarks on a first sighting she can see, and goes to sketch it.
            if (actors_.residentAvailable()) {
                const Actor& r = actors_.all()[static_cast<std::size_t>(actors_.resident())];
                if (std::hypot(r.pos.x - e.pos.x, r.pos.y - e.pos.y) <= tuning::kFirstSightReach) {
                    (void)speak(cat_.resident.context("first_" + def.id), SpeechWeight::Important);
                    actors_.visit(actorEnv(), e.pos, -1, tuning::kFirstSightReach, true);
                }
            }
            break;
        }
        case ActorEvent::Kind::Voice:
            if (!k.voice.empty()) playAt(k.voice, tuning::kVoiceLevel, e.pos, true);
            break;
        case ActorEvent::Kind::Say: {
            // Rain that falls as snow has its own words.
            int ctx = e.arg;
            if (snowing() && ctx == cat_.resident.context("rain_start"))
                ctx = std::max(ctx, cat_.resident.context("snow_start"));
            const bool important = ctx == cat_.resident.context("click") ||
                                   ctx == cat_.resident.context("home_lost") ||
                                   ctx == cat_.resident.context("nook_found");
            (void)speak(ctx, important ? SpeechWeight::Important : SpeechWeight::Routine);
            break;
        }
        case ActorEvent::Kind::Emit:
            playAt(cat_.emitSounds[static_cast<std::size_t>(e.arg)], tuning::kSfxLevel, e.pos);
            break;
        case ActorEvent::Kind::Effect:
            switch (static_cast<Effect>(e.arg)) {
            case Effect::WaterBed:
                // Her morning watering: a quarter of a stage, once per bed per day.
                if (const auto idx = world_.itemIndexAt(e.item)) {
                    const ItemDef& def = cat_.items[world_.items()[*idx].type];
                    if (def.growth.stages > 0 &&
                        grow(world_, cat_, *idx, tuning::kWaterBoost * def.growth.seconds, 1.0f))
                        scene_->popAt(world_.items()[*idx].pos);
                    markDirty();
                }
                break;
            case Effect::Cook:
                events_.cooked(simTime_);
                lively_.happening(simTime_);
                break;
            case Effect::TossPebble:
                if (const Item* it = world_.itemAt(e.item);
                    it != nullptr && !cat_.items[it->type].clickSound.empty())
                    playAt(cat_.items[it->type].clickSound, tuning::kSfxLevel, middle(e.item));
                break;
            case Effect::CallHens:
            case Effect::ReactLine:
            case Effect::None: break;
            }
            break;
        case ActorEvent::Kind::Pet: {
            const Actor& a = actors_.all()[static_cast<std::size_t>(e.actor)];
            scene_->heart(a);
            const std::string_view sound = !k.petSound.empty() ? std::string_view(k.petSound)
                                           : !k.voice.empty()  ? std::string_view(k.voice)
                                                               : kPetSound;
            playAt(sound, tuning::kVoiceLevel, e.pos, true);
            break;
        }
        case ActorEvent::Kind::Startle:
            playAt(kFlapSound, tuning::kSfxLevel, e.pos, true);
            if (!k.voice.empty()) playAt(k.voice, tuning::kVoiceLevel, e.pos, true);
            break;
        case ActorEvent::Kind::Goods:
            playAt(kGoodsSound, tuning::kUiSfxLevel, e.pos, true);
            lively_.happening(simTime_);
            break;
        }
    }
    actors_.clearEvents();
}

void App::handleWorldEvents() {
    for (const FiredEvent& f : events_.fired()) {
        const EventDef& d = cat_.events[static_cast<std::size_t>(f.event)];
        // A start (not a repeat inside one, and not the player's own doing) is a happening.
        if (!f.pulse && d.on != EventOn::Placed) lively_.happening(simTime_);
        const bool sound = !d.sfx.empty();
        switch (d.show) {
        case EventShow::Rainbow:
        case EventShow::OwlCall:
            if (sound) play(d.sfx, tuning::kSfxLevel * d.gain);
            break;
        case EventShow::ShootingStar:
            scene_->shootingStar(rng_);
            if (sound) play(d.sfx, tuning::kSfxLevel * d.gain);
            break;
        case EventShow::Rustle:
            scene_->rustle(f.at, rng_);
            if (sound) playAt(d.sfx, tuning::kSfxLevel * d.gain, f.at, true);
            break;
        case EventShow::Gust:
            weather_.gust();
            if (sound) play(d.sfx, tuning::kSfxLevel * d.gain);
            break;
        case EventShow::FishJump: {
            // From open water in view (nothing floating on it).
            const TileRect vis = scene_->visibleTiles(camera_, screen(), world_);
            int count = 0;
            TilePos at{-1, -1};
            for (int y = vis.y0; y < vis.y1; ++y)
                for (int x = vis.x0; x < vis.x1; ++x)
                    if (world_.isWater({x, y}) && !world_.isWild({x, y}) &&
                        world_.itemAt({x, y}) == nullptr && rng_.range(0, count++) == 0)
                        at = {x, y};
            if (count == 0) break;
            const Vec2 t{static_cast<float>(at.x) + rng_.range(0.3f, 0.7f),
                         static_cast<float>(at.y) + rng_.range(0.3f, 0.7f)};
            scene_->fishJump(t);
            if (sound) playAt(d.sfx, tuning::kSfxLevel * d.gain, t);
            break;
        }
        case EventShow::FrogChorus:
            // The frog croaks every few seconds while it rains and for a minute after.
            if (d.who >= 0) (void)actors_.call(d.who);
            break;
        case EventShow::Season: {
            // A pinned season does not change with the calendar, so nothing is announced.
            if (seasonPin_ >= 0) break;
            if (sound) play(d.sfx, tuning::kSfxLevel * d.gain);
            const SeasonDef& s = cat_.seasons[static_cast<std::size_t>(season())];
            if (!speakText(s.line, SpeechWeight::Important)) hud_.toast(signedLine(s.line, -1));
            break;
        }
        case EventShow::Chorus:
        case EventShow::FireflySync:
        case EventShow::Smoke: break; // states, read where they show
        }
    }
    events_.clearFired();
    handleActorEvents(); // a frog's croak asked for above
}

float App::panOf(Vec2 tile) const {
    const Vec2 px = camera_.worldToScreen(cat_.iso().toWorld(tile.x, tile.y), screen());
    return std::clamp(px.x / std::max(1.0f, screen().x) * 2.0f - 1.0f, -tuning::kPanLimit,
                      tuning::kPanLimit);
}

float App::distanceGain(Vec2 tile) const {
    // Full within a few tiles of the view centre, fading to nothing a little beyond the view.
    const TileRect vis = scene_->visibleTiles(camera_, screen(), world_);
    const float half =
        0.5f * std::hypot(static_cast<float>(vis.x1 - vis.x0), static_cast<float>(vis.y1 - vis.y0));
    const Vec2 c = viewTile();
    const float d = std::hypot(tile.x - c.x, tile.y - c.y);
    const float far = std::max(tuning::kPositionalNear + 1.0f, 1.2f * half);
    return std::clamp(1.0f - (d - tuning::kPositionalNear) / (far - tuning::kPositionalNear), 0.0f,
                      1.0f);
}

void App::playAt(std::string_view file, float gain, Vec2 tile, bool jitter) {
    const int idx = mixer_.sfxIndex(file);
    if (idx < 0) return;
    std::erase_if(recentSounds_,
                  [&](const Played& p) { return simTime_ - p.at > tuning::kVoiceBusy; });
    if (std::ranges::any_of(recentSounds_, [&](const Played& p) {
            return p.sfx == idx && simTime_ - p.at < tuning::kMergeSeconds;
        }))
        return;
    if (recentSounds_.size() >= tuning::kMaxPositional) return;
    const float g = gain * tuning::kPositionalLevel * distanceGain(tile);
    if (g < 0.01f) return;
    const float pitch =
        jitter ? 1.0f + rng_.range(-tuning::kPitchJitter, tuning::kPitchJitter) : 1.0f;
    mixer_.play(idx, g, pitch, panOf(tile));
    recentSounds_.push_back({idx, simTime_});
}

bool App::residentOnScreen() const {
    if (actors_.resident() < 0 || !scene_) return false;
    const Actor& r = actors_.all()[static_cast<std::size_t>(actors_.resident())];
    if (r.alpha < 0.5f) return false;
    const Vec2 px = camera_.worldToScreen(scene_->headOf(r), screen());
    return px.x >= 0 && px.y >= 0 && px.x < screen().x && px.y < screen().y;
}

bool App::speak(int context, SpeechWeight weight) {
    if (context < 0 || photo_ || !actors_.residentAvailable() || !residentOnScreen()) return false;
    if (!speech_.offer(context, weight, simTime_)) return false;
    // One of her soft murmurs with every bubble.
    const auto& voices = cat_.resident.voice;
    if (!voices.empty()) {
        const Actor& r = actors_.all()[static_cast<std::size_t>(actors_.resident())];
        playAt(voices[static_cast<std::size_t>(rng_.range(0, static_cast<int>(voices.size()) - 1))],
               tuning::kVoiceLevel, r.pos);
    }
    return true;
}

bool App::speakText(std::string_view text, SpeechWeight weight) {
    if (photo_ || !actors_.residentAvailable() || !residentOnScreen()) return false;
    return speech_.offerText(text, weight, simTime_);
}

void App::disturbed(TileRect rect, int type, bool fresh) {
    actors_.disturb(actorEnv(), rect, type, fresh);
    events_.placed(world_, rect, simTime_);
    handleActorEvents();
    handleWorldEvents();
}

std::optional<int> App::actorUnder(Vec2 px) const {
    if (!scene_) return std::nullopt;
    return scene_->actorAt(drawActors_, view_.screenToWorld(px, screen()));
}

int App::moversInView() const {
    const TileRect vis = scene_->visibleTiles(camera_, screen(), world_);
    int n = 0;
    for (const Actor& a : actors_.all())
        if (actors_.purposeful(a) && vis.contains(TilePos{static_cast<int>(std::floor(a.pos.x)),
                                                          static_cast<int>(std::floor(a.pos.y))}))
            ++n;
    return n;
}

} // namespace lc
