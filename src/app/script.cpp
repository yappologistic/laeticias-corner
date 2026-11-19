#include "app/script.hpp"

#include <algorithm>
#include <charconv>
#include <sstream>

namespace lc {
namespace {

bool number(std::string_view s, float& out) {
    const auto [p, ec] = std::from_chars(s.data(), s.data() + s.size(), out);
    return ec == std::errc{} && p == s.data() + s.size();
}

std::expected<ScriptPoint, std::string> point(std::string_view tok) {
    ScriptPoint p;
    if (tok.starts_with("ui:")) {
        p.kind = ScriptPoint::Kind::Widget;
        p.widget = std::string(tok.substr(3));
        if (p.widget.empty()) return std::unexpected("empty widget name");
        return p;
    }
    for (const std::string_view prefix : {"grid:", "map:", "landmark:", "figure:", "life:"})
        if (tok.starts_with(prefix) && tok.size() > prefix.size()) {
            p.kind = ScriptPoint::Kind::Widget; // resolved by name each frame, like actors
            p.widget = std::string(tok);
            return p;
        }
    if (tok.starts_with("actor:") && tok.size() > 6) {
        p.kind = ScriptPoint::Kind::Widget; // resolved like a widget, by name, each frame
        p.widget = std::string(tok);
        return p;
    }
    if (tok.starts_with('@')) {
        p.kind = ScriptPoint::Kind::Tile;
        tok.remove_prefix(1);
    }
    const auto comma = tok.find(',');
    if (comma == std::string_view::npos || !number(tok.substr(0, comma), p.x) ||
        !number(tok.substr(comma + 1), p.y))
        return std::unexpected("bad point '" + std::string(tok) + "'");
    return p;
}

} // namespace

std::optional<ScriptRect> parseScriptRect(std::string_view tok) {
    ScriptRect r;
    int* fields[4] = {&r.x, &r.y, &r.w, &r.h};
    for (int i = 0; i < 4; ++i) {
        const auto comma = tok.find(',');
        const std::string_view part = tok.substr(0, comma);
        const auto [p, ec] = std::from_chars(part.data(), part.data() + part.size(), *fields[i]);
        if (ec != std::errc{} || p != part.data() + part.size()) return std::nullopt;
        if ((i < 3) == (comma == std::string_view::npos)) return std::nullopt;
        tok = comma == std::string_view::npos ? std::string_view{} : tok.substr(comma + 1);
    }
    if (r.w <= 0 || r.h <= 0) return std::nullopt;
    return r;
}

std::expected<std::vector<ScriptCommand>, std::string> parseScript(std::string_view text) {
    std::vector<ScriptCommand> out;
    std::istringstream in{std::string(text)};
    std::string raw;
    int lineNo = 0;
    while (std::getline(in, raw)) {
        ++lineNo;
        std::istringstream ls(raw);
        std::vector<std::string> tok;
        for (std::string t; ls >> t;) tok.push_back(t);
        if (tok.empty() || tok[0].starts_with('#')) continue;
        const auto err = [&](const std::string& what) {
            return std::unexpected("script line " + std::to_string(lineNo) + ": " + what);
        };
        ScriptCommand c;
        c.line = lineNo;
        const std::string& cmd = tok[0];
        const auto pointAt = [&](std::size_t i,
                                 ScriptPoint& dst) -> std::expected<void, std::string> {
            if (i >= tok.size()) return std::unexpected(std::string("missing point"));
            auto p = point(tok[i]);
            if (!p) return std::unexpected(p.error());
            dst = std::move(*p);
            return {};
        };
        if (cmd == "move" || cmd == "click" || cmd == "drag" || cmd == "press" ||
            cmd == "release") {
            c.kind = cmd == "move"      ? ScriptCommand::Kind::Move
                     : cmd == "click"   ? ScriptCommand::Kind::Click
                     : cmd == "press"   ? ScriptCommand::Kind::Press
                     : cmd == "release" ? ScriptCommand::Kind::Release
                                        : ScriptCommand::Kind::Drag;
            if (auto r = pointAt(1, c.a); !r) return err(r.error());
            std::size_t next = 2;
            if (c.kind == ScriptCommand::Kind::Drag) {
                if (auto r = pointAt(2, c.b); !r) return err(r.error());
                next = 3;
            }
            if (next < tok.size()) {
                if ((tok[next] != "right" && tok[next] != "middle") ||
                    c.kind == ScriptCommand::Kind::Move)
                    return err("unexpected '" + tok[next] + "'");
                (tok[next] == "right" ? c.right : c.middle) = true;
                ++next;
            }
            if (next != tok.size()) return err("too many arguments");
        } else if (cmd == "key" || cmd == "keydown" || cmd == "keyup") {
            if (tok.size() != 2) return err(cmd + " takes one combo");
            c.kind = cmd == "key"       ? ScriptCommand::Kind::Key
                     : cmd == "keydown" ? ScriptCommand::Kind::KeyDown
                                        : ScriptCommand::Kind::KeyUp;
            c.args = {tok[1]};
        } else if (cmd == "wheel") {
            c.kind = ScriptCommand::Kind::Wheel;
            if (tok.size() < 2 || tok.size() > 3 || !number(tok[1], c.amount))
                return err("wheel DY [P]");
            if (tok.size() == 3) {
                if (auto r = pointAt(2, c.a); !r) return err(r.error());
                c.hasPoint = true;
            }
        } else if (cmd == "wait") {
            c.kind = ScriptCommand::Kind::Wait;
            if (tok.size() != 2 || !number(tok[1], c.amount) || c.amount < 0 ||
                c.amount > kScriptMaxWait)
                return err("wait N (0 to 5000000 frames)");
        } else if (cmd == "shot") {
            if (tok.size() != 2) return err("shot FILE");
            c.kind = ScriptCommand::Kind::Shot;
            c.args = {tok[1]};
        } else if (cmd == "set") {
            static constexpr std::string_view kKeys[] = {
                "clock",  "rain", "unlock",    "played",  "land",  "season",
                "day",    "grow", "weather",   "chatter", "time",  "lively",
                "shower", "city", "city_dump", "session", "clouds"};
            static constexpr std::string_view kNumeric[] = {"played", "grow", "day", "time",
                                                            "session"};
            if (tok.size() == 3 && std::ranges::find(kNumeric, tok[1]) != std::end(kNumeric)) {
                float v = 0;
                const std::string_view n = tok[2].starts_with('+')
                                               ? std::string_view(tok[2]).substr(1)
                                               : std::string_view(tok[2]);
                if (!number(n, v)) return err("set " + tok[1] + " expects a number");
            }
            if (tok.size() == 4 && tok[1] == "wish") {
                if (tok[3] != "open") return err("set wish ID open");
            } else if (tok.size() == 4 && (tok[1] == "look" || tok[1] == "world")) {
                float v = 0;
                if (!number(tok[3], v)) return err("set " + tok[1] + " PLACE ZOOM");
            } else if (tok.size() == 5 && (tok[1] == "camera" || tok[1] == "world")) {
                for (std::size_t i = 2; i < 5; ++i) {
                    float v = 0;
                    if (!number(tok[i], v)) return err("set " + tok[1] + " TX TY ZOOM");
                }
            } else if (tok.size() != 3 || std::ranges::find(kKeys, tok[1]) == std::end(kKeys)) {
                return err(
                    "set clock|rain|weather|clouds|unlock|played|land|season|day|grow|chatter|"
                    "time|lively|city|city_dump|session VALUE, set camera|world TX TY ZOOM, set "
                    "world PLACE ZOOM, set look KIND ZOOM or set wish ID open");
            }
            c.kind = ScriptCommand::Kind::Set;
            c.args.assign(tok.begin() + 1, tok.end());
        } else if (cmd == "fast") {
            c.kind = ScriptCommand::Kind::Fast;
            if (tok.size() < 2 || !number(tok[1], c.amount) || c.amount <= 0 || c.amount > 86400)
                return err("fast SECONDS [WHAT ARGS]");
            c.args.assign(tok.begin() + 2, tok.end());
        } else if (cmd == "expect" || cmd == "waitfor") {
            const bool wait = cmd == "waitfor";
            if (wait && (tok.size() < 4 || !number(tok[1], c.amount) || c.amount < 1 ||
                         c.amount > kScriptMaxWait))
                return err("waitfor N WHAT ARGS");
            if (tok.size() < 3) return err("expect WHAT ARGS");
            c.kind = wait ? ScriptCommand::Kind::WaitFor : ScriptCommand::Kind::Expect;
            c.args.assign(tok.begin() + (wait ? 2 : 1), tok.end());
            if (c.args[0] == "tile" || c.args[0] == "item" || c.args[0] == "growth") {
                if (c.args.size() != 3) return err("expect " + c.args[0] + " P VALUE");
                if (auto r = pointAt(wait ? 3 : 2, c.a); !r) return err(r.error());
            } else if (c.args[0] == "contrast") {
                float v = 0;
                if (c.args.size() != 3 || !parseScriptRect(c.args[1]) || !number(c.args[2], v))
                    return err("expect contrast X,Y,W,H MIN");
            } else if (c.args[0] == "luma_mark") {
                if (c.args.size() != 3 || !parseScriptRect(c.args[2]))
                    return err("expect luma_mark NAME X,Y,W,H");
            } else if (c.args[0] == "luma_like") {
                float v = 0;
                if (c.args.size() != 4 || !parseScriptRect(c.args[2]) || !number(c.args[3], v))
                    return err("expect luma_like NAME X,Y,W,H TOLERANCE");
            } else if (c.args[0] == "target_alpha") {
                float v = 0;
                if (c.args.size() != 3 || !parseScriptRect(c.args[1]) || !number(c.args[2], v))
                    return err("expect target_alpha X,Y,W,H MOST");
            } else if (c.args[0] == "luma" || c.args[0] == "color") {
                const std::size_t want = c.args[0] == "luma" ? 4 : 6;
                if (c.args.size() != want || !parseScriptRect(c.args[1]))
                    return err(c.args[0] == "luma" ? "expect luma X,Y,W,H MIN MAX"
                                                   : "expect color X,Y,W,H R G B TOL");
                for (std::size_t i = 2; i < want; ++i) {
                    float v = 0;
                    if (!number(c.args[i], v)) return err("bad number '" + c.args[i] + "'");
                }
            }
        } else if (cmd == "place" || cmd == "paint") {
            c.kind = cmd == "place" ? ScriptCommand::Kind::Place : ScriptCommand::Kind::Paint;
            if (tok.size() < 3 || tok.size() > 4) return err(cmd + " ID @TX,TY [V or @TX2,TY2]");
            c.args = {tok[1]};
            if (auto r = pointAt(2, c.a); !r || c.a.kind != ScriptPoint::Kind::Tile)
                return err(cmd + " needs a tile point @TX,TY");
            if (tok.size() == 4) {
                if (cmd == "place") {
                    if (!number(tok[3], c.amount)) return err("place: bad variant");
                } else if (auto r = pointAt(3, c.b); !r || c.b.kind != ScriptPoint::Kind::Tile) {
                    return err("paint needs tile points");
                } else {
                    c.hasPoint = true;
                }
            }
        } else if (cmd == "type") {
            if (tok.size() < 2) return err("type TEXT");
            c.kind = ScriptCommand::Kind::Type;
            for (std::size_t i = 1; i < tok.size(); ++i) c.args.push_back(tok[i]);
        } else if (cmd == "quit") {
            c.kind = ScriptCommand::Kind::Quit;
        } else {
            return err("unknown command '" + cmd + "'");
        }
        out.push_back(std::move(c));
    }
    return out;
}

} // namespace lc
