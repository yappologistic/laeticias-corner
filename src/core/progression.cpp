#include "core/progression.hpp"

#include "core/land.hpp"
#include "core/tuning.hpp"

#include <algorithm>

namespace lc {

Progression::Progression(const Catalog& cat)
    : cat_(cat), trueSince_(cat.wishes.size(), -1.0), grantAt_(cat.wishes.size(), -1.0),
      status_(cat.wishes.size()), nookHere_(cat.nooks.size(), 0), rare_(cat.visitors.size()) {
    events_.reserve(16);
    instances_.reserve(64);
}

int Progression::extraVisitors(int visitor) const {
    int extra = 0;
    for (std::size_t n = 0; n < cat_.nooks.size(); ++n)
        if (nookHere_[n] != 0)
            for (const Amount& c : cat_.nooks[n].caps)
                if (c.index == visitor) extra += c.count;
    return extra;
}

float Progression::nookGrowth(const World& world, TileRect rect) const {
    float mul = 1.0f;
    for (std::size_t n = 0; n < cat_.nooks.size(); ++n) {
        const NookDef& def = cat_.nooks[n];
        if (nookHere_[n] == 0 || def.growth == 1.0f) continue;
        cat_.conditions.instances(def.near, world, instances_);
        for (const NearInstance& in : instances_) {
            const TileRect area{in.footprint.x0 - in.within, in.footprint.y0 - in.within,
                                in.footprint.x1 + in.within, in.footprint.y1 + in.within};
            if (area.intersects(rect)) {
                mul = std::max(mul, def.growth);
                break;
            }
        }
    }
    return mul;
}

bool Progression::offerable(int wish, const World& world, const Progress& p, const CondFacts& facts,
                            double played) const {
    const auto w = static_cast<std::size_t>(wish);
    const WishDef& def = cat_.wishes[w];
    const WishProgress& wp = p.wishes[w];
    if (wp.state != WishState::Waiting) return false;
    if (wp.snoozedUntil >= 0 && played < wp.snoozedUntil) return false;
    if (!std::ranges::all_of(def.after, [&](int a) {
            return p.wishes[static_cast<std::size_t>(a)].state == WishState::Done;
        }))
        return false;
    // Every piece the goal needs must be unlocked, so a wish never asks for the impossible.
    for (const int s : def.needed) {
        const Selector& sel = cat_.conditions.selector(s);
        const auto& unlocked = sel.terrain ? p.terrain : p.items;
        if (!std::ranges::any_of(sel.ids,
                                 [&](int id) { return unlocked[static_cast<std::size_t>(id)]; }))
            return false;
    }
    // The giver must be about: a visitor in the home region; Laeticia (not yet walking about)
    // is up in every phase but night.
    if (def.giver >= 0) {
        if (std::cmp_greater_equal(def.giver, facts.present.size()) ||
            facts.present[static_cast<std::size_t>(def.giver)] <= 0)
            return false;
    } else if (facts.phase == Phase::Night) {
        return false;
    }
    return def.gate < 0 || cat_.conditions.eval(def.gate, world, facts);
}

void Progression::refresh(int wish, const World& world, const CondFacts& facts, double played) {
    const auto w = static_cast<std::size_t>(wish);
    const WishDef& def = cat_.wishes[w];
    const bool holds = cat_.conditions.eval(def.goal, world, facts);
    if (!holds)
        trueSince_[w] = -1;
    else if (trueSince_[w] < 0)
        trueSince_[w] = played;
    WishStatus& st = status_[w];
    st.ready = holds;
    st.count = -1;
    if (const auto c = cat_.conditions.countProgress(def.goal, world)) {
        st.count = c->first;
        st.min = c->second;
    }
    st.waiting = -1;
    if (!holds) {
        CondFacts waiting = facts;
        waiting.waiting = true;
        if (cat_.conditions.eval(def.goal, world, waiting))
            st.waiting = cat_.conditions.firstWaiting(def.goal, facts).value_or(-1);
    }
}

void Progression::evaluate(const World& world, Progress& p, const CondFacts& facts, double played) {
    // Nooks first: wishes and recipes may name them.
    for (std::size_t n = 0; n < cat_.nooks.size(); ++n) {
        nookHere_[n] = cat_.conditions.eval(cat_.nooks[n].condition, world, facts) ? 1 : 0;
        if (nookHere_[n] != 0 && p.nooks[n] == 0) {
            p.nooks[n] = 1;
            events_.push_back({ProgressEvent::Kind::NookFound, static_cast<int>(n), false});
        }
    }
    CondFacts f = facts;
    f.nookHere = nookHere_;
    for (const int w : p.open) refresh(w, world, f, played);
    for (std::size_t v = 0; v < cat_.visitors.size(); ++v) {
        const VisitorDef& def = cat_.visitors[v];
        if (!def.rare) continue;
        rare_[v].holds =
            ((def.seasons >> f.season) & 1) != 0 && cat_.conditions.eval(def.recipe, world, f);
    }
}

int Progression::rareRate(int visitor) const {
    int rate = 1;
    for (std::size_t n = 0; n < cat_.nooks.size(); ++n)
        if (nookHere_[n] != 0)
            for (const Amount& r : cat_.nooks[n].rareRate)
                if (r.index == visitor) rate *= r.count;
    return rate;
}

void Progression::tickRare(const CondFacts& facts, double played, Rng& rng) {
    for (std::size_t v = 0; v < cat_.visitors.size(); ++v) {
        Rare& r = rare_[v];
        if (!cat_.visitors[v].rare) continue;
        if (!r.holds) {
            // It leaves as soon as the recipe stops holding.
            r.since = -1;
            r.here = false;
            continue;
        }
        const bool seen = v < facts.seen.size() && facts.seen[v] != 0;
        if (r.here) {
            // The visit is timed from the first sighting; once over, it stays away a while.
            if (!seen) r.leaves = played + r.stay;
            if (played >= r.leaves) {
                r.here = false;
                r.since = -1;
                r.awayUntil = played + rng.range(tuning::kRareAwayMin, tuning::kRareAwayMax);
            }
            continue;
        }
        if (played < r.awayUntil) continue;
        if (r.since < 0) {
            r.since = played;
            r.delay = rng.range(tuning::kRareDelayMin, tuning::kRareDelayMax) /
                      static_cast<float>(rareRate(static_cast<int>(v)));
        }
        if (played - r.since >= r.delay) {
            r.here = true;
            r.stay = rng.range(tuning::kRareStayMin, tuning::kRareStayMax);
            r.leaves = played + r.stay;
        }
    }
}

void Progression::grant(int wish, Progress& p, double played) {
    const auto w = static_cast<std::size_t>(wish);
    p.wishes[w].state = WishState::Done;
    p.wishes[w].snoozedUntil = -1;
    std::erase(p.open, wish);
    p.granted.push_back(wish);
    p.unlock(cat_.wishes[w].reward, true);
    p.lastOffer = played; // the next offer waits from the grant too
    trueSince_[w] = -1;
    grantAt_[w] = -1;
    status_[w] = {};
    events_.push_back({ProgressEvent::Kind::WishGranted, wish, false});
}

void Progression::offer(const World& world, Progress& p, const CondFacts& facts, double played) {
    if (std::cmp_greater_equal(p.open.size(), tuning::kMaxOpenWishes)) return;
    const double gap = p.open.empty() ? tuning::kWishOfferGapEmpty : tuning::kWishOfferGap;
    if (played - p.lastOffer < gap) return;
    // The first offerable wish in catalog order (the gentle storyline), wishes that were snoozed
    // and have come back ranking after the rest.
    int pick = -1;
    for (int pass = 0; pass < 2 && pick < 0; ++pass)
        for (std::size_t w = 0; w < cat_.wishes.size() && pick < 0; ++w) {
            const bool returned = p.wishes[w].snoozedUntil >= 0;
            if (returned == (pass == 1) && offerable(static_cast<int>(w), world, p, facts, played))
                pick = static_cast<int>(w);
        }
    if (pick < 0) return;
    const auto w = static_cast<std::size_t>(pick);
    p.wishes[w].state = WishState::Open;
    p.wishes[w].snoozedUntil = -1;
    p.open.push_back(pick);
    p.lastOffer = played;
    refresh(pick, world, facts, played);
    const bool already = status_[w].ready;
    if (already) grantAt_[w] = played + tuning::kWishAlreadyDoneDelay;
    events_.push_back({ProgressEvent::Kind::WishOffered, pick, already});
}

void Progression::tick(const World& world, Progress& p, const CondFacts& facts, double played,
                       bool offering, Rng& rng) {
    tickRare(facts, played, rng);
    if (played >= nextOffer_) {
        nextOffer_ = played + tuning::kWishPacingTick;
        // The hold is measured between evaluations, so goals are looked at again here too.
        evaluate(world, p, facts, played);
        if (offering) offer(world, p, facts, played);
    }
    // Land opens as the sketchbook fills; several stages reached at once open one by one.
    const int next = nextStagePages(cat_, p.stage);
    if (next >= 0 && facts.counters[static_cast<std::size_t>(Counter::Pages)] >= next &&
        played >= stageReady_) {
        ++p.stage;
        stageReady_ = played + tuning::kLandStageGap;
        events_.push_back({ProgressEvent::Kind::StageOpens, p.stage, false});
    }
    // Backwards: granting removes wishes from the open list.
    for (std::size_t i = p.open.size(); i-- > 0;) {
        const int wish = p.open[i];
        const auto w = static_cast<std::size_t>(wish);
        if (grantAt_[w] >= 0) {
            if (played >= grantAt_[w]) grant(wish, p, played);
        } else if (trueSince_[w] >= 0 && played - trueSince_[w] >= tuning::kWishGrantHold) {
            grant(wish, p, played);
        }
    }
}

void Progression::snooze(int wish, Progress& p, double played) {
    const auto w = static_cast<std::size_t>(wish);
    if (p.wishes[w].state != WishState::Open) return;
    p.wishes[w].state = WishState::Waiting;
    p.wishes[w].snoozedUntil = played + tuning::kWishSnooze;
    std::erase(p.open, wish);
    trueSince_[w] = -1;
    grantAt_[w] = -1;
    status_[w] = {};
}

} // namespace lc
