#include "core/progression.hpp"

#include "core/tuning.hpp"

#include <algorithm>

namespace lc {

Progression::Progression(const Catalog& cat)
    : cat_(cat), trueSince_(cat.wishes.size(), -1.0), grantAt_(cat.wishes.size(), -1.0),
      status_(cat.wishes.size()) {
    events_.reserve(16);
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
    for (const int w : p.open) refresh(w, world, facts, played);
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
                       bool offering) {
    if (played >= nextOffer_) {
        nextOffer_ = played + tuning::kWishPacingTick;
        // The hold is measured between evaluations, so goals are looked at again here too.
        evaluate(world, p, facts, played);
        if (offering) offer(world, p, facts, played);
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
