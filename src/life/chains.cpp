#include "life/chains.hpp"

#include "core/tuning.hpp"

#include <algorithm>
#include <climits>
#include <cmath>

namespace lc::life {

namespace tl = tuning::life;

namespace {

constexpr long kDay = 720;

// lifesim._hour: the clock starts at 06:00.
float hourOf(long t) {
    return std::fmod(6.0f + 24.0f * static_cast<float>(t % kDay) / static_cast<float>(kDay), 24.0f);
}

// citylife._node_for over grid tiles (neighbours in plan order: +c, -c, +r, -r).
int nodeFor(const RegionPaths& paths, int cols, std::span<const TilePos> tiles,
            std::span<const TilePos> beside, bool post) {
    const auto plan = [&](TilePos g) { return TilePos{cols - 1 - g.y, g.x}; };
    const auto grid = [&](TilePos p) { return TilePos{p.y, cols - 1 - p.x}; };
    static constexpr std::array<TilePos, 4> kPlanSteps{{{1, 0}, {-1, 0}, {0, 1}, {0, -1}}};
    for (const TilePos t : tiles) {
        if (paths.label(t) >= 0) return paths.label(t);
        const TilePos p = plan(t);
        for (const TilePos s : kPlanSteps) {
            const TilePos n = grid({p.x + s.x, p.y + s.y});
            if (paths.label(n) >= 0) return paths.label(n);
        }
    }
    if (post)
        for (const TilePos t : beside)
            if (paths.label(t) >= 0) return paths.label(t);
    return -1;
}

// citylife._ring in plan order, as grid tiles, walkable ones only (the `beside` spots).
void ringOf(const world::WorldMap& m, const world::Placed& it, std::vector<TilePos>& out) {
    out.clear();
    const int cols = m.height();
    const auto grid = [&](TilePos p) { return TilePos{p.y, cols - 1 - p.x}; };
    const TilePos o{cols - 1 - (it.y + it.h - 1), it.x}; // plan top-left
    const int pw = it.h;
    const int ph = it.w;
    const auto add = [&](int c, int r) {
        const TilePos g = grid({c, r});
        if (m.inBounds(g) && m.walkable(g)) out.push_back(g);
    };
    for (int c = o.x - 1; c < o.x + pw + 1; ++c) {
        add(c, o.y - 1);
        add(c, o.y + ph);
    }
    for (int r = o.y; r < o.y + ph; ++r) {
        add(o.x - 1, r);
        add(o.x + pw, r);
    }
}

} // namespace

ChainRun::ChainRun(const LifeData& data, const LifeRegion& region, const Chain& chain,
                   const world::WorldMap& map, const RegionPaths& paths)
    : chain_(&chain) {
    const int cols = map.height();
    const auto& layers = map.layers();
    const auto layerIt = std::ranges::find(layers, region.id);
    const int layer = layerIt == layers.end() ? -2 : static_cast<int>(layerIt - layers.begin());
    std::vector<TilePos> tiles;
    std::vector<TilePos> ring;
    std::vector<int> dist;
    // lifesim._node: the place of a slot reference.
    const auto resolve = [&](const std::string& ref, const std::string& near) {
        ChainPlace pl;
        if (ref.starts_with("node:") || ref.starts_with("portal:")) {
            pl.node = paths.findNode(ref.substr(ref.find(':') + 1));
            if (pl.node >= 0) pl.tile = paths.nodeAt(pl.node);
            return pl;
        }
        const auto dot = ref.rfind('.');
        const std::string itemId = ref.substr(0, dot);
        const std::string slot = dot == std::string::npos ? std::string{} : ref.substr(dot + 1);
        const int info = map.content().findItem(itemId);
        if (info < 0) return pl;
        const auto& names = map.slotNames();
        const auto nameIt = std::ranges::find(names, slot);
        const int name = nameIt == names.end() ? -1 : static_cast<int>(nameIt - names.begin());
        const auto& kinds = map.slotKinds();
        struct Inst {
            std::uint32_t item;
            int node;
            TilePos tile;
            int slot;
            TilePos planOrigin;
        };
        std::vector<Inst> insts;
        for (std::uint32_t i = 0; i < map.items().size(); ++i) {
            const world::Placed& it = map.items()[i];
            if (static_cast<int>(it.info) != info || static_cast<int>(it.layer) != layer) continue;
            ringOf(map, it, ring);
            tiles.clear();
            int firstSlot = -1;
            bool mooring = false;
            if (slot == "beside") {
                tiles = ring;
            } else if (name >= 0) {
                const auto& slots = map.slots();
                for (std::size_t s = 0; s < slots.size(); ++s)
                    if (slots[s].item == i && slots[s].name == name) {
                        tiles.push_back(slots[s].tile);
                        if (firstSlot < 0) firstSlot = static_cast<int>(s);
                        mooring = kinds[slots[s].kind] == "mooring";
                    }
            }
            const bool post = mooring && it.w * it.h <= 4;
            const int node = nodeFor(paths, cols, tiles, ring, post);
            if (node < 0) continue;
            // Where a worker stands: the first spot one can stand on, else the ring.
            TilePos stand = tiles.empty() ? TilePos{it.x, it.y} : tiles.front();
            for (const TilePos t : tiles)
                if (map.walkable(t)) {
                    stand = t;
                    break;
                }
            if (!map.walkable(stand) && !ring.empty()) stand = ring.front();
            insts.push_back({i, node, stand, firstSlot, {cols - 1 - (it.y + it.h - 1), it.x}});
        }
        if (insts.empty()) return pl;
        const int nearNode = near.empty() ? -1 : paths.findNode(near);
        if (nearNode >= 0) {
            paths.distances(nearNode, dist);
            std::ranges::stable_sort(insts, [&](const Inst& a, const Inst& b) {
                const int da = dist[static_cast<std::size_t>(a.node)] == INT_MAX
                                   ? (1 << 30)
                                   : dist[static_cast<std::size_t>(a.node)];
                const int db = dist[static_cast<std::size_t>(b.node)] == INT_MAX
                                   ? (1 << 30)
                                   : dist[static_cast<std::size_t>(b.node)];
                if (da != db) return da < db;
                if (a.planOrigin.x != b.planOrigin.x) return a.planOrigin.x < b.planOrigin.x;
                return a.planOrigin.y < b.planOrigin.y;
            });
        }
        pl.node = insts.front().node;
        pl.item = static_cast<int>(insts.front().item);
        pl.tile = insts.front().tile;
        pl.slot = insts.front().slot;
        return pl;
    };
    // lifesim keys the places by reference: a reference named again with another `near` takes
    // the later stage's instance for every stage (its dict is overwritten); so does this.
    const auto resolvePlace = [&](const std::string& ref, const std::string& near) {
        const ChainPlace pl = resolve(ref, near);
        for (auto& [r, p] : places_)
            if (r == ref) {
                p = pl;
                return;
            }
        places_.emplace_back(ref, pl);
    };
    // The chain's continuity, as lifesim checks it.
    std::string last;
    for (std::size_t i = 0; i < chain.stages.size(); ++i) {
        const ChainStage& s = chain.stages[i];
        if (s.kind == ChainStage::Kind::Carry) {
            if (i > 0 && !last.empty() && s.from != last)
                errors_.push_back("stage " + std::to_string(i) + " carries from '" + s.from +
                                  "' but the goods are at '" + last + "'");
            resolvePlace(s.from, s.near);
            resolvePlace(s.to, s.near);
            last = s.to;
        } else {
            if (i > 0 && !last.empty() && s.slot != last && s.kind != ChainStage::Kind::Source)
                errors_.push_back("stage " + std::to_string(i) + " works at '" + s.slot +
                                  "' but the goods are at '" + last + "'");
            resolvePlace(s.slot, s.near);
            last = s.out.empty() ? s.slot : s.out;
        }
    }
    for (const auto& [ref, pl] : places_)
        if (pl.node < 0)
            errors_.push_back("slot '" + ref + "' cannot be reached on the path graph");
    stats_.assign(chain.stages.size(), {});
    doneNow_.assign(chain.stages.size(), 0);
    perDay_.assign(4, 0);
    for (std::size_t i = 0; i < chain.stages.size(); ++i) {
        const ChainStage& s = chain.stages[i];
        double tr = 0;
        switch (s.kind) {
        case ChainStage::Kind::Carry: {
            keys_.emplace_back(counter(s.from, s.goods), counter(s.to, s.goods));
            const int a = this->place(s.from).node;
            const int b = this->place(s.to).node;
            if (a >= 0 && b >= 0) {
                paths.distances(a, dist);
                if (dist[static_cast<std::size_t>(b)] == INT_MAX) {
                    errors_.push_back("no path from '" + s.from + "' to '" + s.to + "'");
                } else {
                    const Role* role =
                        s.role >= 0 ? &region.roles[static_cast<std::size_t>(s.role)] : nullptr;
                    const std::string kind =
                        role != nullptr && role->kind >= 0
                            ? data.kinds[static_cast<std::size_t>(role->kind)].id
                            : s.by;
                    const bool cart = kind.find("cart") != std::string::npos ||
                                      kind.find("sledge") != std::string::npos;
                    const double speed = role != nullptr && role->speedExact > 0
                                             ? role->speedExact
                                             : (cart ? 0.6 : 0.9);
                    tr = dist[static_cast<std::size_t>(b)] / speed;
                }
            }
            for (int w = 0; w < s.workers; ++w) workerStage_.push_back(static_cast<int>(i));
            break;
        }
        case ChainStage::Kind::Transform:
            keys_.emplace_back(counter(s.slot, s.needs), counter(s.out, s.goods));
            workerStage_.push_back(static_cast<int>(i));
            break;
        case ChainStage::Kind::Source:
        case ChainStage::Kind::Sink:
            keys_.emplace_back(counter(s.slot, s.goods), -1);
            workerStage_.push_back(static_cast<int>(i));
            break;
        }
        travel_.push_back(tr);
    }
    workers_.assign(workerStage_.size(), {});
}

const ChainPlace& ChainRun::place(const std::string& ref) const {
    static const ChainPlace kNone;
    for (const auto& [r, p] : places_)
        if (r == ref) return p;
    return kNone;
}

int ChainRun::counter(const std::string& ref, int goods) {
    for (std::size_t i = 0; i < counters_.size(); ++i)
        if (counters_[i].ref == ref && counters_[i].goods == goods) return static_cast<int>(i);
    counters_.push_back({ref, goods, 0});
    return static_cast<int>(counters_.size() - 1);
}

bool ChainRun::hoursOn(long t) const {
    return inHours(chain_->from, chain_->to, hourOf(t));
}

bool ChainRun::on(long t, int season, int month) const {
    if (chain_->seasons != 0 && (chain_->seasons & (1u << season)) == 0) return false;
    return monthIn(chain_->months, month) && hoursOn(t);
}

double ChainRun::pace(int month) const {
    const auto m = static_cast<std::size_t>(month);
    return m < chain_->pace.size() ? static_cast<double>(chain_->pace[m]) : 1.0;
}

bool ChainRun::tick(long t, bool on, double pace) {
    constexpr int kCap = tl::kChainCap;
    if (t == kDay) resetStats(); // lifesim judges the chain once it has filled
    std::ranges::fill(doneNow_, 0);
    const double period = chain_->period / pace;
    for (std::size_t k = 0; k < workers_.size(); ++k) {
        const auto i = static_cast<std::size_t>(workerStage_[k]);
        const ChainStage& s = chain_->stages[i];
        ChainWorker& st = workers_[k];
        ChainStats& sm = stats_[i];
        if (s.kind == ChainStage::Kind::Carry) {
            int& src = counters_[static_cast<std::size_t>(keys_[i].first)].count;
            int& dst = counters_[static_cast<std::size_t>(keys_[i].second)].count;
            if (st.phase == WorkerPhase::Idle) {
                if (!on) continue;
                ++sm.work;
                const int room = kCap - dst;
                if (src > 0 && room > 0) {
                    const int n = std::min({s.units, src, room});
                    src -= n;
                    st = {travel_[i], WorkerPhase::Out, n};
                } else if (src == 0) {
                    ++sm.starve;
                } else {
                    ++sm.block;
                }
            } else if (st.phase == WorkerPhase::Out) {
                ++sm.work;
                st.t -= 1;
                if (st.t <= 0) {
                    if (kCap - dst >= st.hand) {
                        dst += st.hand;
                        sm.done += st.hand;
                        doneNow_[i] = 1;
                        st = {travel_[i], WorkerPhase::Back, 0};
                    } else {
                        ++sm.block;
                    }
                }
            } else if (st.phase == WorkerPhase::Back) {
                st.t -= 1;
                if (st.t <= 0) st.phase = WorkerPhase::Idle;
            }
            continue;
        }
        if (!on) continue;
        ++sm.work;
        if (s.kind == ChainStage::Kind::Sink) {
            int& c = counters_[static_cast<std::size_t>(keys_[i].first)].count;
            const double dur = s.dur >= 0 ? s.dur : period / 3;
            if (c > 0) {
                st.t += 1;
                if (st.t >= dur) {
                    --c;
                    st.t = 0;
                    ++sm.done;
                    doneNow_[i] = 1;
                    const auto day = static_cast<std::size_t>(t / kDay);
                    if (day < perDay_.size()) ++perDay_[day];
                }
            } else {
                ++sm.starve;
            }
        } else if (s.kind == ChainStage::Kind::Transform) {
            int& in = counters_[static_cast<std::size_t>(keys_[i].first)].count;
            int& out = counters_[static_cast<std::size_t>(keys_[i].second)].count;
            const double dur = s.dur >= 0 ? s.dur : period / 2;
            if (st.phase == WorkerPhase::Idle) {
                if (out >= kCap) {
                    ++sm.block;
                } else if (in > 0) {
                    --in;
                    st.phase = WorkerPhase::Work;
                    st.t = dur;
                } else {
                    ++sm.starve;
                }
            } else {
                st.t -= 1;
                if (st.t <= 0) {
                    if (out < kCap) {
                        ++out;
                        ++sm.done;
                        doneNow_[i] = 1;
                        st.phase = WorkerPhase::Idle;
                    } else {
                        ++sm.block;
                    }
                }
            }
        } else {
            int& out = counters_[static_cast<std::size_t>(keys_[i].first)].count;
            if (out >= kCap) {
                ++sm.block;
                continue;
            }
            st.t += 1;
            if (st.t >= period) {
                ++out;
                ++made_;
                ++sm.done;
                doneNow_[i] = 1;
                st.t = 0;
            }
        }
    }
    for (const Counter& c : counters_)
        if (c.count < 0 || c.count > kCap) {
            errors_.push_back("slot '" + c.ref + "' holds " + std::to_string(c.count));
            return false;
        }
    return true;
}

ChainRun::Snapshot ChainRun::snapshot() const {
    Snapshot s;
    for (const Counter& c : counters_) s.counts.push_back(c.count);
    s.workers = workers_;
    s.made = 0; // `made` is a statistic; the cycle compares the state only
    return s;
}

void ChainRun::restore(const Snapshot& s) {
    for (std::size_t i = 0; i < counters_.size() && i < s.counts.size(); ++i)
        counters_[i].count = s.counts[i];
    workers_ = s.workers;
}

void ChainRun::clear() {
    for (Counter& c : counters_) c.count = 0;
    workers_.assign(workers_.size(), {});
}

Chains::Chains(const LifeData& data, const world::WorldMap& map, std::vector<RegionPaths>& paths,
               const std::vector<int>& pathsOfRegion)
    : data_(&data) {
    for (std::size_t r = 0; r < data.regions.size(); ++r) {
        const int p = pathsOfRegion[r];
        if (p < 0) continue;
        const LifeRegion& region = data.regions[r];
        for (std::size_t c = 0; c < region.chains.size(); ++c) {
            runs_.emplace_back(data, region, region.chains[c], map,
                               paths[static_cast<std::size_t>(p)]);
            region_.push_back(static_cast<int>(r));
            regionChain_.push_back(static_cast<int>(c));
        }
    }
    days_.resize(runs_.size());
    cycleStart_.assign(runs_.size(), -1);
    cycleLen_.assign(runs_.size(), 0);
    // Every chain's daily cycle found now (a few days each), so nothing grows in play.
    for (std::size_t i = 0; i < runs_.size(); ++i) dayStart(i, tl::kPeriodicSearchDays);
}

bool Chains::gated(std::size_t i) const {
    return runs_[i].chain().event >= 0;
}

void Chains::dayStart(std::size_t i, long day) {
    ChainRun& r = runs_[i];
    if (!r.ok()) return;
    if (gated(i)) {
        r.clear();
        return;
    }
    auto& days = days_[i];
    const auto d = static_cast<std::size_t>(day);
    if (cycleStart_[i] >= 0 && day >= cycleStart_[i]) {
        const long k = cycleStart_[i] + (day - cycleStart_[i]) % cycleLen_[i];
        r.restore(days[static_cast<std::size_t>(k)]);
        return;
    }
    if (d < days.size()) {
        r.restore(days[d]);
        return;
    }
    // Days not seen yet: simulate whole days from the last one kept, recording each 06:00, until
    // this day or the cycle.
    const long seasonDays = std::max(1, data_->seasonDays);
    const auto seasons = static_cast<long>(std::max<std::size_t>(1, data_->seasons.size()));
    if (days.empty()) {
        r.clear();
        days.push_back(r.snapshot());
    } else {
        r.restore(days.back());
    }
    // A chain whose days differ through the year (seasons, months, pace) repeats only by whole
    // years: two equal mornings in its closed season say nothing about its open one.
    const Chain& c = r.chain();
    const long year = seasonDays * seasons;
    const long step = c.seasons != 0 || c.months != 0 || !c.pace.empty() ? year : 1;
    while (days.size() <= d) {
        const long k = static_cast<long>(days.size()) - 1;
        const auto season = static_cast<int>((k / seasonDays) % seasons);
        const int month = data_->monthOf(static_cast<int>(k));
        for (long t = k * kDay; t < (k + 1) * kDay; ++t)
            r.tick(t, r.on(t, season, month), r.pace(month));
        days.push_back(r.snapshot());
        const long n = static_cast<long>(days.size()) - 1;
        for (long lag = step; lag <= std::max(12L, year) && lag <= n; lag += step)
            if (days[static_cast<std::size_t>(n)] == days[static_cast<std::size_t>(n - lag)]) {
                cycleStart_[i] = static_cast<int>(n - lag);
                cycleLen_[i] = static_cast<int>(lag);
                break;
            }
        if (cycleStart_[i] >= 0) {
            dayStart(i, day);
            return;
        }
        if (static_cast<long>(days.size()) > tl::kPeriodicSearchDays) {
            // No cycle in the search window: the last 12 days stand for every later day.
            cycleStart_[i] = static_cast<int>(days.size()) - 13;
            cycleLen_[i] = 12;
            dayStart(i, day);
            return;
        }
    }
    r.restore(days[d]);
}

std::size_t Chains::memoryBytes() const {
    std::size_t n = runs_.capacity() * sizeof(ChainRun);
    for (const auto& d : days_)
        for (const auto& s : d)
            n += s.counts.capacity() * sizeof(int) + s.workers.capacity() * sizeof(ChainWorker);
    return n;
}

std::vector<std::string> Chains::problems() const {
    std::vector<std::string> out;
    for (std::size_t i = 0; i < runs_.size(); ++i)
        for (const std::string& e : runs_[i].errors())
            out.push_back(data_->regions[static_cast<std::size_t>(region_[i])].id + ": chain " +
                          runs_[i].chain().id + ": " + e);
    return out;
}

} // namespace lc::life
