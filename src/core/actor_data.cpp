#include "core/actor_data.hpp"

#include "core/actors.hpp"
#include "core/catalog.hpp"
#include "core/tuning.hpp"

#include <nlohmann/json.hpp>

#include <algorithm>
#include <array>
#include <stdexcept>

namespace lc {
namespace {

using nlohmann::json;

[[noreturn]] void fail(const std::string& msg) {
    throw std::runtime_error(msg);
}

constexpr std::array<std::string_view, 4> kPhases{"day", "dusk", "night", "dawn"};
constexpr std::array<std::string_view, 15> kVerbs{"go",   "use",   "take",    "put",    "wander",
                                                  "wait", "enter", "exit",    "follow", "say",
                                                  "emit", "pick",  "routine", "each",   "if"};

// "hh:mm" in game hours.
float parseHour(const json& j, const std::string& ctx) {
    if (!j.is_string()) fail(ctx + ": an hour is \"hh:mm\"");
    const std::string s = j.get<std::string>();
    const auto colon = s.find(':');
    if (colon == std::string::npos) fail(ctx + ": an hour is \"hh:mm\"");
    try {
        const int h = std::stoi(s.substr(0, colon));
        const int m = std::stoi(s.substr(colon + 1));
        if (h < 0 || h > 24 || m < 0 || m > 59) fail(ctx + ": hour out of range");
        return static_cast<float>(h) + static_cast<float>(m) / 60.0f;
    } catch (const std::logic_error&) {
        fail(ctx + ": an hour is \"hh:mm\"");
    }
}

std::uint8_t phaseMask(const json& list, const std::string& ctx) {
    if (!list.is_array() || list.empty()) fail(ctx + ": expected a list of phases");
    std::uint8_t mask = 0;
    for (const auto& p : list) {
        const auto it =
            p.is_string() ? std::ranges::find(kPhases, p.get<std::string>()) : kPhases.end();
        if (it == kPhases.end()) fail(ctx + ": unknown phase " + p.dump());
        mask |= static_cast<std::uint8_t>(1u << (it - kPhases.begin()));
    }
    return mask;
}

int intern(std::vector<std::string>& names, const std::string& s) {
    const auto it = std::ranges::find(names, s);
    if (it != names.end()) return static_cast<int>(it - names.begin());
    names.push_back(s);
    return static_cast<int>(names.size()) - 1;
}

std::pair<float, float> range(const json& j, const char* key, const std::string& ctx) {
    if (!j.contains(key)) return {0.0f, 0.0f};
    const json& r = j[key];
    if (r.is_number()) return {r.get<float>(), r.get<float>()};
    if (!r.is_array() || r.size() != 2 || !r[0].is_number() || !r[1].is_number() ||
        r[0].get<float>() < 0 || r[1].get<float>() < r[0].get<float>())
        fail(ctx + ": '" + key + "' is [min, max] seconds");
    return {r[0].get<float>(), r[1].get<float>()};
}

// A visitor's habitat as locomotion, with its speed (living-world.md §2.5).
std::pair<std::string, float> habitatMove(const std::string& h) {
    if (h == "water") return {"swim", tuning::kWaterSpeed};
    if (h == "air") return {"fly", tuning::kAirSpeed};
    if (h == "shore") return {"shore", tuning::kLandSpeed};
    return {"walk", tuning::kLandSpeed};
}

// Reads a visitor entry as an actor kind in the canonical form (living-world.md §2.5), so one
// compiler handles both.
json visitorKind(const json& v) {
    const std::string id = v.at("id").get<std::string>();
    json k = json::object();
    k["id"] = id;
    const auto [mode, speed] = habitatMove(v.at("habitat").get<std::string>());
    k["locomotion"] = {{"mode", mode}, {"speed", speed}};
    // Its home: where it goes in (hens, bees) and what "near home" measures from.
    if (v.contains("home"))
        k["home"] = v["home"];
    else if (v.contains("needs") && v["needs"].contains("items") && !v["needs"]["items"].empty())
        k["home"] = v["needs"]["items"].begin().key();
    const bool shelters = v.value("hide_in_rain", false);
    k["line"] = v.value("line", false);
    for (const char* key : {"startle", "pet", "voice", "watches_pointer"})
        if (v.contains(key)) k[key] = v[key];

    const auto activity = [&](const json& a) {
        json opt = json::object();
        const std::string aid = a.at("id").get<std::string>();
        opt["as"] = aid;
        opt["weight"] = a.value("weight", 1.0);
        for (const char* key : {"time", "seasons", "needs_sitting"})
            if (a.contains(key)) opt[key] = a[key];
        json use = {{"use", {{"here", true}}}};
        for (const char* key : {"anim", "dur", "every", "call_anim"})
            if (a.contains(key)) use[key] = a[key];
        json steps = json::array();
        if (!a.contains("at")) {
            json w = {{"wander", {{"radius", tuning::kWanderRadius}}}, {"as", aid}};
            if (a.contains("dur")) w["dur"] = a["dur"];
            steps.push_back(w);
        } else {
            json at = a["at"];
            const std::string key = at.begin().key();
            if (a.contains("spot")) at["spot"] = a["spot"];
            if (a.contains("within")) {
                at["within"] = a["within"];
                at["near"] = "home";
            }
            if (key == "here") {
                steps.push_back(use);
            } else if (key == "resident") {
                json f = {{"follow", {{"resident", true}}}};
                if (a.value("spot", std::string{}) == "on") f["on"] = true;
                if (a.contains("dur")) f["dur"] = a["dur"];
                steps.push_back(f);
            } else if (a.value("anim", std::string{}) == "enter") {
                steps.push_back({{"go", at}, {"as", aid}});
                json e = {{"enter", {{"here", true}}}};
                if (a.contains("dur")) e["dur"] = a["dur"];
                steps.push_back(e);
            } else {
                steps.push_back({{"go", at}, {"as", aid}});
                steps.push_back(use);
            }
        }
        opt["steps"] = steps;
        return opt;
    };
    const json& acts = v.contains("activities") ? v["activities"]
                                                : json::array({{{"id", "wander"}, {"weight", 1}}});
    json main = {{"loop", true}};
    json steps = json::array();
    if (v.contains("cycle")) {
        for (const auto& cid : v["cycle"])
            for (const auto& a : acts)
                if (a.at("id") == cid) steps.push_back({{"pick", json::array({activity(a)})}});
    } else {
        json options = json::array();
        for (const auto& a : acts) options.push_back(activity(a));
        steps.push_back({{"pick", options}});
    }
    main["steps"] = steps;
    json routines = {{"main", main}};
    // Leaving: walk into the home item when it has one, else fade where it stands.
    if (k.contains("home"))
        routines["leave"] = {
            {"steps", json::array({{{"go", {{"home", true}}}}, {{"enter", {{"here", true}}}}})}};
    if (shelters) {
        json hide = json::array();
        if (k.contains("home")) hide.push_back({{"go", {{"home", true}}}});
        hide.push_back({{"enter", {{"here", true}}}, {"until", {{"weather", "clear"}}}});
        routines["shelter"] = {{"steps", hide}};
        k["interrupts"] = json::array(
            {{{"when", {{"weather", "rain"}}}, {"routine", "shelter"}, {"priority", 2}}});
    }
    k["routines"] = routines;
    return k;
}

class Compiler {
public:
    Compiler(Catalog& cat, ActorProgram& p) : cat_(cat), p_(p) {}

    void kind(const json& k, int visitor) {
        ActorKind d;
        d.id = k.at("id").get<std::string>();
        ctx_ = (visitor >= 0 ? "visitor '" : "resident '") + d.id + "'";
        d.visitor = visitor;
        d.sprite = k.value("sprite", "critter/" + d.id);
        const json& loco = k.contains("locomotion") ? k["locomotion"] : json::object();
        const std::string mode = loco.value("mode", std::string("walk"));
        if (mode == "walk")
            d.move = Locomotion::Walk;
        else if (mode == "swim")
            d.move = Locomotion::Swim;
        else if (mode == "shore")
            d.move = Locomotion::Shore;
        else if (mode == "fly")
            d.move = Locomotion::Fly;
        else
            fail(ctx_ + ": unknown locomotion '" + mode + "'");
        d.speed = loco.value("speed", tuning::kLandSpeed);
        if (d.speed <= 0) fail(ctx_ + ": speed must be positive");
        if (k.contains("home")) {
            const auto h = cat_.findItem(k["home"].get<std::string>());
            if (!h) fail(ctx_ + ": unknown home item");
            d.home = *h;
        }
        d.line = k.value("line", false);
        d.watches = k.value("watches_pointer", false);
        if (k.contains("voice") && k["voice"].is_string())
            d.voice = "sfx/" + k["voice"].get<std::string>() + ".wav";
        anims_ = &d.anims;
        kind_ = &d;
        d.anims = {"move", "idle"};
        if (k.contains("startle")) {
            const json& s = k["startle"];
            d.startleRadius = s.value("radius", 0.0f);
            if (s.contains("anim")) d.startleAnim = anim(s["anim"].get<std::string>());
            if (s.contains("only_from")) {
                d.startleFrom = 0;
                for (const auto& a : s["only_from"])
                    d.startleFrom |= 1u << anim(a.get<std::string>());
            }
        }
        if (k.contains("pet")) {
            const json& pt = k["pet"];
            if (pt.contains("anim")) d.petAnim = anim(pt["anim"].get<std::string>());
            if (pt.contains("sound")) d.petSound = "sfx/" + pt["sound"].get<std::string>() + ".wav";
        }
        // Routines are named per kind; their bodies may refer to each other in any order.
        const json& routines = k.at("routines");
        if (!routines.is_object() || routines.empty()) fail(ctx_ + ": routines by name");
        names_.clear();
        for (const auto& [name, r] : routines.items()) {
            names_.push_back(name);
            Routine rt;
            rt.name = name;
            rt.loop = r.value("loop", false);
            d.routines.push_back(static_cast<int>(p_.routines.size()));
            p_.routines.push_back(rt);
        }
        base_ = d.routines.front();
        std::size_t i = 0;
        for (const auto& [name, r] : routines.items()) {
            if (!r.contains("steps")) fail(ctx_ + " routine '" + name + "': missing 'steps'");
            const int b = block(r["steps"], ctx_ + " routine '" + name + "'");
            p_.routines[static_cast<std::size_t>(d.routines[i++])].block = b;
        }
        const auto routineIndex = [&](const std::string& name, const std::string& where) {
            const auto it = std::ranges::find(names_, name);
            if (it == names_.end()) fail(where + ": unknown routine '" + name + "'");
            return base_ + static_cast<int>(it - names_.begin());
        };
        if (visitor >= 0) d.main = routineIndex("main", ctx_);
        if (k.contains("schedule")) {
            for (const auto& s : k["schedule"]) {
                ScheduleBlock sb;
                const json& h = s.at("hours");
                if (!h.is_array() || h.size() != 2) fail(ctx_ + ": schedule hours [from, to]");
                sb.from = parseHour(h[0], ctx_);
                sb.to = parseHour(h[1], ctx_);
                sb.routine = routineIndex(s.at("routine").get<std::string>(), ctx_ + " schedule");
                d.schedule.push_back(sb);
            }
        }
        if (k.contains("interrupts")) {
            for (const auto& it : k["interrupts"]) {
                Interrupt in;
                const json& w = it.at("when");
                if (w.contains("weather") && w["weather"] == "rain")
                    in.on = Interrupt::On::Rain;
                else if (w.contains("event") && w["event"] == "placed_nearby")
                    in.on = Interrupt::On::PlacedNearby;
                else if (w.contains("event") && w["event"] == "harvest")
                    in.on = Interrupt::On::Harvest;
                else
                    fail(ctx_ + ": an interrupt is on rain or the placed_nearby or harvest event");
                in.routine = routineIndex(it.at("routine").get<std::string>(), ctx_ + " interrupt");
                in.priority = it.value("priority", 1);
                in.chance = it.value("chance", 1.0f);
                in.cooldown = it.value("cooldown", 0.0f);
                in.delay = it.value("delay", 0.0f);
                d.interrupts.push_back(in);
            }
            std::ranges::stable_sort(d.interrupts, [](const Interrupt& a, const Interrupt& b) {
                return a.priority > b.priority;
            });
        }
        if (k.contains("roles")) {
            const json& r = k["roles"];
            const auto role = [&](const char* key) -> std::uint8_t {
                return r.contains(key) ? anim(r[key].get<std::string>()) : std::uint8_t{0xFF};
            };
            d.carryAnim = role("carry");
            d.rainAnim = role("rain");
            d.waveAnim = role("wave");
        }
        // Conventional names: "sleep" means asleep; swimmers that go ashore waddle there.
        if (const auto it = std::ranges::find(d.anims, "sleep"); it != d.anims.end())
            d.sleepAnim = static_cast<std::uint8_t>(it - d.anims.begin());
        if (d.move == Locomotion::Swim && usesBank_) d.waddleAnim = anim("waddle");
        if (d.anims.size() > 32) fail(ctx_ + ": too many animations");
        cat_.kinds.push_back(std::move(d));
    }

private:
    std::uint8_t anim(const std::string& name) {
        if (name.empty() || name == "enter") fail(ctx_ + ": '" + name + "' is not an animation");
        return static_cast<std::uint8_t>(intern(*anims_, name));
    }

    int targetOf(const json& t, const std::string& ctx) {
        if (!t.is_object() || t.empty()) fail(ctx + ": a target is an object");
        Target d;
        bool kindSet = false;
        const auto set = [&](Target::Kind k) {
            if (kindSet) fail(ctx + ": a target has one kind");
            d.kind = k;
            kindSet = true;
        };
        for (const auto& [key, v] : t.items()) {
            if (key == "item") {
                set(Target::Kind::Items);
                d.ids.push_back(item(v, ctx));
            } else if (key == "items") {
                set(Target::Kind::Items);
                for (const auto& i : v) d.ids.push_back(item(i, ctx));
            } else if (key == "tag") {
                // A tag narrows a slot kind; on its own it picks the items carrying it.
                const auto tag = cat_.findTag(v.get<std::string>());
                if (!tag) fail(ctx + ": unknown tag '" + v.get<std::string>() + "'");
                d.id = *tag;
                if (!t.contains("slot_kind")) set(Target::Kind::Tag);
            } else if (key == "slot_kind") {
                set(Target::Kind::SlotKind);
                d.slotKind = intern(cat_.slotKinds, v.get<std::string>());
            } else if (key == "home") {
                set(Target::Kind::Home);
                if (v.is_string()) d.slot = slotName(v.get<std::string>(), ctx);
            } else if (key == "here" || key == "each" || key == "bank" || key == "shore" ||
                       key == "resident" || key == "bedroll") {
                static constexpr std::pair<std::string_view, Target::Kind> kSimple[] = {
                    {"here", Target::Kind::Here},         {"each", Target::Kind::Each},
                    {"bank", Target::Kind::Bank},         {"shore", Target::Kind::Shore},
                    {"resident", Target::Kind::Resident}, {"bedroll", Target::Kind::Bedroll}};
                for (const auto& [n, kk] : kSimple)
                    if (n == key) set(kk);
                if (key == "bank") usesBank_ = true;
            } else if (key == "poi") {
                set(Target::Kind::Poi);
                const std::string s = v.get<std::string>();
                if (s == "stroll")
                    d.poi = Poi::Stroll;
                else if (s == "new_items")
                    d.poi = Poi::NewItems;
                else if (s == "visitors")
                    d.poi = Poi::Visitors;
                else if (s == "nooks")
                    d.poi = Poi::Nooks;
                else
                    fail(ctx + ": unknown poi set '" + s + "'");
            } else if (key == "nook") {
                set(Target::Kind::Nook);
                const auto n = cat_.findNook(v.get<std::string>());
                if (!n) fail(ctx + ": unknown nook " + v.dump());
                d.id = *n;
            } else if (key == "slot") {
                d.slot = slotName(v.get<std::string>(), ctx);
            } else if (key == "spot") {
                const std::string s = v.get<std::string>();
                if (s != "on" && s != "beside") fail(ctx + ": spot is on or beside");
                d.spot = s == "on" ? Spot::On : Spot::Beside;
            } else if (key == "within") {
                d.within = v.get<float>();
            } else if (key == "near") {
                const std::string s = v.get<std::string>();
                if (s != "home" && s != "self") fail(ctx + ": near is home or self");
                d.nearHome = s == "home";
            } else if (key == "max" || key == "order") {
                // `each` options, read by the step
            } else {
                fail(ctx + ": unknown target key '" + key + "'");
            }
        }
        if (!kindSet) fail(ctx + ": the target names nothing to go to");
        p_.targets.push_back(std::move(d));
        return static_cast<int>(p_.targets.size()) - 1;
    }

    int item(const json& v, const std::string& ctx) const {
        const auto i = v.is_string() ? cat_.findItem(v.get<std::string>()) : std::nullopt;
        if (!i) fail(ctx + ": unknown item " + v.dump());
        return *i;
    }

    int slotName(const std::string& s, const std::string& ctx) const {
        const auto it = std::ranges::find(cat_.slotNames, s);
        if (it == cat_.slotNames.end()) fail(ctx + ": no item has a slot '" + s + "'");
        return static_cast<int>(it - cat_.slotNames.begin());
    }

    void untilOf(const json& u, Step& s, const std::string& ctx) {
        if (!u.is_object() || u.size() != 1) fail(ctx + ": 'until' has one key");
        const auto& key = u.begin().key();
        const json& v = u.begin().value();
        if (key == "hour") {
            s.until = Until::Hour;
            s.hour = parseHour(v, ctx);
        } else if (key == "phase") {
            s.until = Until::Phase;
            s.phases = phaseMask(v, ctx);
        } else if (key == "weather") {
            const std::string w = v.get<std::string>();
            if (w != "clear" && w != "rain") fail(ctx + ": until weather is clear or rain");
            s.until = w == "clear" ? Until::Clear : Until::Rain;
        } else {
            fail(ctx + ": unknown 'until' key '" + key + "'");
        }
    }

    int goods(const json& v, const std::string& ctx) const {
        const auto it = v.is_string()
                            ? std::ranges::find(cat_.goods, v.get<std::string>(), &GoodsDef::id)
                            : cat_.goods.end();
        if (it == cat_.goods.end()) fail(ctx + ": unknown goods " + v.dump());
        return static_cast<int>(it - cat_.goods.begin());
    }

    int line(const std::string& context, const std::string& ctx) const {
        if (!cat_.resident.enabled) fail(ctx + ": 'say' needs the resident");
        const auto it = std::ranges::find(cat_.resident.contexts, context);
        if (it == cat_.resident.contexts.end()) fail(ctx + ": no lines for '" + context + "'");
        return static_cast<int>(it - cat_.resident.contexts.begin());
    }

    int step(const json& j, const std::string& ctx) {
        if (!j.is_object()) fail(ctx + ": a step is an object");
        Step s;
        int verbs = 0;
        for (std::size_t v = 0; v < kVerbs.size(); ++v)
            if (j.contains(kVerbs[v])) {
                s.verb = static_cast<Verb>(v);
                ++verbs;
            }
        if (verbs != 1) fail(ctx + ": a step has exactly one verb");
        const std::string verb(kVerbs[static_cast<std::size_t>(s.verb)]);
        const std::string sctx = ctx + " '" + verb + "'";
        const json& v = j[verb];
        const auto [d0, d1] = range(j, "dur", sctx);
        s.dur0 = d0;
        s.dur1 = d1;
        const auto [e0, e1] = range(j, "every", sctx);
        s.every0 = e0;
        s.every1 = e1;
        if (j.contains("anim")) s.anim = anim(j["anim"].get<std::string>());
        if (j.contains("call_anim")) {
            s.callAnim = anim(j["call_anim"].get<std::string>());
            if (kind_->callAnim == 0xFF) kind_->callAnim = s.callAnim;
        }
        if (j.contains("until")) untilOf(j["until"], s, sctx);
        if (j.contains("as")) s.activity = intern(cat_.activityNames, j["as"].get<std::string>());
        if (j.contains("effect")) {
            const std::string e = j["effect"].get<std::string>();
            static constexpr std::pair<std::string_view, Effect> kEffects[] = {
                {"water_bed", Effect::WaterBed},
                {"call_hens", Effect::CallHens},
                {"toss_pebble", Effect::TossPebble},
                {"cook", Effect::Cook},
                {"react_line", Effect::ReactLine}};
            for (const auto& [n, eff] : kEffects)
                if (n == e) s.effect = eff;
            if (s.effect == Effect::None) fail(sctx + ": unknown effect '" + e + "'");
        }
        switch (s.verb) {
        case Verb::Go:
        case Verb::Use:
        case Verb::Enter:
        case Verb::Exit:
            s.target = targetOf(v, sctx);
            if (j.contains("else")) s.orElse = targetOf(j["else"], sctx + " else");
            break;
        case Verb::Take:
        case Verb::Put: s.a = goods(v, sctx); break;
        case Verb::Wander:
            s.radius = v.value("radius", static_cast<float>(tuning::kWanderRadius));
            if (s.radius < 1) fail(sctx + ": radius must be at least 1");
            break;
        case Verb::Wait:
            if (v.is_object()) {
                const auto [w0, w1] = range(v, "dur", sctx);
                s.dur0 = w0;
                s.dur1 = w1;
                if (v.contains("until")) untilOf(v["until"], s, sctx);
            }
            if (s.dur1 <= 0 && s.until == Until::None) fail(sctx + ": wait needs dur or until");
            break;
        case Verb::Follow:
            // Without a resident such an option is simply never available.
            if (!v.contains("resident")) fail(sctx + ": only the resident can be followed");
            s.onHat = j.value("on", false);
            s.radius = j.value("spacing", 1.0f);
            break;
        case Verb::Say: s.a = line(v.get<std::string>(), sctx); break;
        case Verb::Emit: {
            if (!v.contains("sfx")) fail(sctx + ": emit names an sfx");
            const std::string file = "sfx/" + v["sfx"].get<std::string>() + ".wav";
            if (std::ranges::find(cat_.audio.sfx, file) == cat_.audio.sfx.end())
                fail(sctx + ": sound '" + file + "' is not listed under audio.sfx");
            s.a = intern(cat_.emitSounds, file);
            break;
        }
        case Verb::Pick: {
            if (!v.is_array() || v.empty()) fail(sctx + ": pick needs options");
            // Options are compiled first (they may hold steps), then laid out contiguously.
            std::vector<PickOption> opts;
            for (const auto& o : v) opts.push_back(option(o, sctx));
            s.a = static_cast<int>(p_.options.size());
            s.b = static_cast<int>(opts.size());
            for (const auto& o : opts) p_.options.push_back(o);
            break;
        }
        case Verb::Routine: {
            const auto it = std::ranges::find(names_, v.get<std::string>());
            if (it == names_.end()) fail(sctx + ": unknown routine " + v.dump());
            s.a = base_ + static_cast<int>(it - names_.begin());
            break;
        }
        case Verb::Each:
            s.target = targetOf(v, sctx);
            s.b = v.value("max", 6);
            s.nearest = v.value("order", std::string{}) == "nearest";
            if (s.b < 1 || s.b > 16) fail(sctx + ": max must be within 1..16");
            s.a = block(j.at("do"), sctx + " do");
            break;
        case Verb::If:
            s.cond = condition(v, sctx);
            s.a = block(j.at("do"), sctx + " do");
            s.b = j.contains("else") ? block(j["else"], sctx + " else") : -1;
            break;
        }
        p_.steps.push_back(s);
        return static_cast<int>(p_.steps.size()) - 1;
    }

    PickOption option(const json& o, const std::string& ctx) {
        if (!o.is_object()) fail(ctx + ": a pick option is an object");
        PickOption opt;
        opt.weight = o.value("weight", 1.0f);
        if (opt.weight < 0) fail(ctx + ": weight must be >= 0");
        if (o.contains("when")) opt.cond = condition(o["when"], ctx + " when");
        if (o.contains("time")) opt.phases = phaseMask(o["time"], ctx);
        if (o.contains("seasons")) {
            opt.seasons = 0;
            for (const auto& s : o["seasons"]) {
                const auto i = s.is_string() ? cat_.findSeason(s.get<std::string>()) : std::nullopt;
                if (!i) fail(ctx + ": unknown season " + s.dump());
                opt.seasons |= static_cast<std::uint8_t>(1u << *i);
            }
        }
        opt.needsSitting = o.value("needs_sitting", 0.0f);
        if (o.contains("as")) opt.activity = intern(cat_.activityNames, o["as"].get<std::string>());
        if (o.contains("steps")) {
            opt.block = block(o["steps"], ctx);
        } else {
            // The option is itself one step (`routine` included).
            json body = o;
            for (const char* key : {"weight", "when", "time", "seasons", "needs_sitting", "as"})
                body.erase(key);
            opt.block = block(json::array({body}), ctx);
        }
        return opt;
    }

    int block(const json& list, const std::string& ctx) {
        if (!list.is_array() || list.empty()) fail(ctx + ": steps must be a non-empty list");
        std::vector<int> ids;
        for (const auto& s : list) ids.push_back(step(s, ctx));
        Block b{static_cast<int>(p_.blockSteps.size()), static_cast<int>(ids.size())};
        p_.blockSteps.insert(p_.blockSteps.end(), ids.begin(), ids.end());
        p_.blocks.push_back(b);
        return static_cast<int>(p_.blocks.size()) - 1;
    }

    int condition(const json& c, const std::string& ctx) {
        std::vector<std::string> nookIds;
        nookIds.reserve(cat_.nooks.size());
        for (const auto& n : cat_.nooks) nookIds.push_back(n.id);
        return cat_.conditions.compile(c, cat_, nookIds, ctx);
    }

    Catalog& cat_;
    ActorProgram& p_;
    std::string ctx_;
    std::vector<std::string>* anims_ = nullptr;
    ActorKind* kind_ = nullptr;
    std::vector<std::string> names_; // routine names of the kind being compiled
    int base_ = 0;                   // its first routine index
    bool usesBank_ = false;
};

} // namespace

int ActorKind::findRoutine(std::string_view name, const ActorProgram& p) const {
    for (const int r : routines)
        if (p.routines[static_cast<std::size_t>(r)].name == name) return r;
    return -1;
}

namespace {

// How many frames running `block` can stack up (itself and everything it pushes); a routine that
// reaches itself again is refused, since it would nest without end.
int blockDepth(const ActorProgram& p, int block, std::vector<int>& path, const std::string& ctx) {
    if (std::ranges::find(path, block) != path.end())
        fail(ctx + ": a routine reaches itself again (endless nesting)");
    path.push_back(block);
    int deepest = 0;
    const Block& b = p.blocks[static_cast<std::size_t>(block)];
    for (int k = 0; k < b.count; ++k) {
        const Step& s =
            p.steps[static_cast<std::size_t>(p.blockSteps[static_cast<std::size_t>(b.first + k)])];
        const auto child = [&](int c) {
            if (c >= 0) deepest = std::max(deepest, blockDepth(p, c, path, ctx));
        };
        switch (s.verb) {
        case Verb::Pick:
            for (int o = 0; o < s.b; ++o) child(p.options[static_cast<std::size_t>(s.a + o)].block);
            break;
        case Verb::If:
            child(s.a);
            child(s.b);
            break;
        case Verb::Each: child(s.a); break;
        case Verb::Routine: child(p.routines[static_cast<std::size_t>(s.a)].block); break;
        default: break;
        }
    }
    path.pop_back();
    return 1 + deepest;
}

} // namespace

void compileActors(const json& root, Catalog& cat) {
    ActorProgram program;
    std::size_t i = 0;
    for (const auto& v : root.at("visitors")) {
        Compiler fresh(cat, program); // per-kind state starts clean
        fresh.kind(visitorKind(v), static_cast<int>(i++));
    }
    if (cat.resident.enabled) {
        json k = root.at("resident");
        if (!k.contains("locomotion"))
            k["locomotion"] = {{"mode", "walk"}, {"speed", tuning::kResidentSpeedOther}};
        Compiler fresh(cat, program);
        fresh.kind(k, -1);
        cat.residentKind = static_cast<int>(cat.kinds.size()) - 1;
        if (cat.kinds.back().schedule.empty()) fail("resident: needs a schedule");
        // A nook's `routine` effect names one of her routines (her data runs it while the
        // nook exists).
        for (const auto& n : root.at("nooks"))
            for (const auto& e : n.value("effects", json::array()))
                if (e.contains("routine") &&
                    cat.kinds.back().findRoutine(e["routine"].get<std::string>(), program) < 0)
                    fail("nook '" + n.at("id").get<std::string>() +
                         "': the resident has no routine '" + e["routine"].get<std::string>() +
                         "'");
    }
    // Every routine must fit the runtime's stack of frames (Q3-12): deeper data would be cut off
    // silently while running, so it is refused here, naming the routine.
    std::vector<int> path;
    for (const ActorKind& k : cat.kinds)
        for (const int r : k.routines) {
            const Routine& routine = program.routines[static_cast<std::size_t>(r)];
            const std::string ctx = "kind '" + k.id + "' routine '" + routine.name + "'";
            const int depth = blockDepth(program, routine.block, path, ctx);
            if (depth > kActorStack)
                fail(ctx + ": nests " + std::to_string(depth) + " levels deep; at most " +
                     std::to_string(kActorStack));
        }
    cat.program = std::move(program);
}

} // namespace lc
