#include "core/events.hpp"

#include "core/rng.hpp"
#include "core/tuning.hpp"
#include "core/world.hpp"

#include <algorithm>
#include <cmath>

namespace lc {

EventScheduler::EventScheduler(const Catalog& cat, std::uint64_t seed)
    : cat_(&cat), seed_(seed ^ 0xE7E47ULL), due_(cat.events.size(), 0.0),
      last_(cat.events.size(), -1e9), lastDay_(cat.events.size(), -1),
      drawn_(cat.events.size(), 0) {
    running_.reserve(cat.events.size());
    fired_.reserve(cat.events.size() * 2);
    for (std::size_t e = 0; e < cat.events.size(); ++e)
        if (cat.events[e].on == EventOn::Window || cat.events[e].on == EventOn::Reactive)
            due_[e] = gap(static_cast<int>(e));
}

double EventScheduler::gap(int e) {
    // The k-th draw of an event's own stream: a pure function of the seed, the event and k.
    const EventDef& d = cat_->events[static_cast<std::size_t>(e)];
    Rng r(seed_ ^ (static_cast<std::uint64_t>(e) << 40) ^ drawn_[static_cast<std::size_t>(e)]++);
    if (d.mean > 0) return -std::log(1.0 - static_cast<double>(r.uniform())) * d.mean;
    return d.every0 + (d.every1 - d.every0) * static_cast<double>(r.uniform());
}

double EventScheduler::duration(int e) {
    const EventDef& d = cat_->events[static_cast<std::size_t>(e)];
    if (d.dur1 <= d.dur0) return d.dur0;
    Rng r(seed_ ^ (static_cast<std::uint64_t>(e) << 40) ^ 0xD0ULL ^
          drawn_[static_cast<std::size_t>(e)]++);
    return d.dur0 + (d.dur1 - d.dur0) * static_cast<double>(r.uniform());
}

bool EventScheduler::filters(const EventDef& d, const EventEnv& env) const {
    if (((d.phases >> static_cast<int>(env.phase)) & 1) == 0) return false;
    if (((d.seasons >> env.season) & 1) == 0) return false;
    if (d.weather >= 0 && (d.weather == 1) != env.facts.raining) return false;
    return d.when < 0 || cat_->conditions.eval(d.when, *env.world, env.facts);
}

void EventScheduler::start(int e, double now, Vec2 at) {
    const auto i = static_cast<std::size_t>(e);
    last_[i] = now;
    std::erase_if(running_, [&](const Running& r) { return r.event == e; });
    const double len = duration(e);
    const EventDef& d = cat_->events[i];
    running_.push_back(
        {e, now, now + len, d.every1 > 0 && d.on == EventOn::Rain ? now : now + 1e9});
    fired_.push_back({e, at, false});
}

void EventScheduler::update(const EventEnv& env) {
    const double now = env.now;
    const bool rain = env.facts.raining;
    if (rain && !wasRaining_) rainSince_ = now;
    const bool stopped = !rain && wasRaining_;
    if (stopped) rainEnded_ = now;
    for (std::size_t i = 0; i < cat_->events.size(); ++i) {
        const EventDef& d = cat_->events[i];
        const int e = static_cast<int>(i);
        const bool running =
            std::ranges::any_of(running_, [&](const Running& r) { return r.event == e; });
        if (d.daily && lastDay_[i] == env.day) continue;
        if (now - last_[i] < d.cooldown) continue;
        switch (d.on) {
        case EventOn::Window:
            if (now < due_[i]) break;
            if (!filters(d, env)) {
                due_[i] = now + gap(e); // this window passes without it
                break;
            }
            // Scheduled starts keep apart; a deferred one waits a little and tries again.
            if (now - lastScheduled_ < tuning::kEventSpacing) {
                due_[i] = lastScheduled_ + tuning::kEventSpacing + tuning::kEventRetry;
                break;
            }
            lastScheduled_ = now;
            start(e, now, {-1, -1});
            due_[i] = now + gap(e);
            break;
        case EventOn::Hours: {
            const bool in = d.from <= d.to ? env.hour >= d.from && env.hour < d.to
                                           : env.hour >= d.from || env.hour < d.to;
            if (in && !running && filters(d, env)) {
                start(e, now, {-1, -1});
                running_.back().end = 1e18; // lasts while the hours do
            }
            if (!in) std::erase_if(running_, [&](const Running& r) { return r.event == e; });
            break;
        }
        case EventOn::Rain:
            if ((rain || now - rainEnded_ < d.dur0) && !running && filters(d, env)) {
                start(e, now, {-1, -1});
                running_.back().end = 1e18; // ends `duration` after the rain stops
            }
            break;
        case EventOn::RainStop:
            if (stopped && now - rainSince_ >= d.minRain && filters(d, env))
                start(e, now, {-1, -1});
            break;
        case EventOn::Reactive:
            if (now >= due_[i] && !running && filters(d, env)) {
                start(e, now, {-1, -1});
                due_[i] = now + gap(e);
            }
            break;
        case EventOn::Placed:
        case EventOn::Cook: break; // started by placed() and cooked()
        case EventOn::Season:
            if (env.seasonDawn) start(e, now, {-1, -1});
            break;
        }
        if (!fired_.empty() && fired_.back().event == e && !fired_.back().pulse)
            lastDay_[i] = env.day;
    }
    // Running events end, and repeat inside themselves (the frog's croak every few seconds).
    for (Running& r : running_) {
        const EventDef& d = cat_->events[static_cast<std::size_t>(r.event)];
        if (d.on == EventOn::Rain && !rain && r.end > 1e17) r.end = rainEnded_ + d.dur0;
        if (d.on == EventOn::Rain && d.when >= 0 &&
            !cat_->conditions.eval(d.when, *env.world, env.facts))
            r.end = now;
        if (now >= r.nextPulse && now < r.end) {
            fired_.push_back({r.event, {-1, -1}, true});
            r.nextPulse = now + gap(r.event);
        }
    }
    std::erase_if(running_, [&](const Running& r) { return now >= r.end; });
    wasRaining_ = rain;
}

void EventScheduler::placed(const World& world, TileRect rect, double now) {
    for (std::size_t i = 0; i < cat_->events.size(); ++i) {
        const EventDef& d = cat_->events[i];
        if (d.on != EventOn::Placed || now - last_[i] < d.cooldown) continue;
        // Something carrying the tag within reach of what changed.
        const int r = static_cast<int>(std::ceil(d.within));
        const TileRect around{rect.x0 - r, rect.y0 - r, rect.x1 + r, rect.y1 + r};
        Vec2 at{-1, -1};
        world.forEachItemIn(around, [&](const Item& it) {
            if (at.x >= 0 || it.rect() == rect) return;
            const auto& tags = cat_->items[it.type].tags;
            if (std::ranges::find(tags, d.nearTag) != tags.end())
                at = {static_cast<float>(it.pos.x) + 0.5f, static_cast<float>(it.pos.y) + 0.5f};
        });
        if (at.x >= 0) start(static_cast<int>(i), now, at);
    }
}

void EventScheduler::cooked(double now) {
    for (std::size_t i = 0; i < cat_->events.size(); ++i)
        if (cat_->events[i].on == EventOn::Cook) start(static_cast<int>(i), now, {-1, -1});
}

bool EventScheduler::active(EventShow show) const {
    return std::ranges::any_of(running_, [&](const Running& r) {
        return cat_->events[static_cast<std::size_t>(r.event)].show == show;
    });
}

float EventScheduler::gain(EventShow show) const {
    float g = 1.0f;
    for (const Running& r : running_) {
        const EventDef& d = cat_->events[static_cast<std::size_t>(r.event)];
        if (d.show == show) g = std::max(g, d.gain);
    }
    return g;
}

float EventScheduler::progress(EventShow show, double now) const {
    for (const Running& r : running_) {
        const EventDef& d = cat_->events[static_cast<std::size_t>(r.event)];
        if (d.show == show && r.end > r.start && r.end < 1e17)
            return static_cast<float>(std::clamp((now - r.start) / (r.end - r.start), 0.0, 1.0));
    }
    return -1.0f;
}

} // namespace lc
