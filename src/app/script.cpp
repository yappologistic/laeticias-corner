#include "app/script.hpp"

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
        if (cmd == "move" || cmd == "click" || cmd == "drag") {
            c.kind = cmd == "move" ? ScriptCommand::Kind::Move
                                   : (cmd == "click" ? ScriptCommand::Kind::Click
                                                     : ScriptCommand::Kind::Drag);
            if (auto r = pointAt(1, c.a); !r) return err(r.error());
            std::size_t next = 2;
            if (c.kind == ScriptCommand::Kind::Drag) {
                if (auto r = pointAt(2, c.b); !r) return err(r.error());
                next = 3;
            }
            if (next < tok.size()) {
                if (tok[next] != "right" || c.kind == ScriptCommand::Kind::Move)
                    return err("unexpected '" + tok[next] + "'");
                c.right = true;
                ++next;
            }
            if (next != tok.size()) return err("too many arguments");
        } else if (cmd == "key") {
            if (tok.size() != 2) return err("key takes one combo");
            c.kind = ScriptCommand::Kind::Key;
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
            if (tok.size() != 2 || !number(tok[1], c.amount) || c.amount < 0) return err("wait N");
        } else if (cmd == "shot") {
            if (tok.size() != 2) return err("shot FILE");
            c.kind = ScriptCommand::Kind::Shot;
            c.args = {tok[1]};
        } else if (cmd == "set") {
            if (tok.size() != 3 || (tok[1] != "clock" && tok[1] != "rain"))
                return err("set clock|rain VALUE");
            c.kind = ScriptCommand::Kind::Set;
            c.args = {tok[1], tok[2]};
        } else if (cmd == "expect") {
            if (tok.size() < 3) return err("expect WHAT ARGS");
            c.kind = ScriptCommand::Kind::Expect;
            c.args.assign(tok.begin() + 1, tok.end());
            if (c.args[0] == "tile" || c.args[0] == "item") {
                if (c.args.size() != 3) return err("expect " + c.args[0] + " P VALUE");
                if (auto r = pointAt(2, c.a); !r) return err(r.error());
            }
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
