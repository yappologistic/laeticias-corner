#include "world/json_util.hpp"

#include <algorithm>

namespace lc::world::detail {

void fail(const std::string& msg) {
    throw Invalid{msg};
}

json parseDocument(std::string_view text, const std::string& file) {
    try {
        return json::parse(text);
    } catch (const json::parse_error& e) {
        fail(file + ": not valid JSON (byte " + std::to_string(e.byte) + ")");
    }
}

void requireVersion1(const json& doc, const std::string& file) {
    if (!doc.is_object()) fail(file + ": the document must be an object");
    const int v = asInt(field(doc, "version", file), file + ": version", 0, 1 << 30);
    if (v != 1) fail(file + ": version " + std::to_string(v) + " is not supported (1 is)");
}

const json& field(const json& obj, const char* key, std::string_view ctx) {
    if (!obj.is_object()) fail(std::string(ctx) + ": expected an object");
    const auto it = obj.find(key);
    if (it == obj.end()) fail(std::string(ctx) + ": missing '" + key + "'");
    return *it;
}

bool has(const json& obj, const char* key) {
    return obj.is_object() && obj.contains(key);
}

int asInt(const json& v, const std::string& ctx, long long lo, long long hi) {
    if (!v.is_number_integer()) fail(ctx + ": expected an integer, got " + v.dump());
    const auto n = v.get<long long>();
    if (n < lo || n > hi)
        fail(ctx + ": " + std::to_string(n) + " is outside " + std::to_string(lo) + ".." +
             std::to_string(hi));
    return static_cast<int>(n);
}

float asFloat(const json& v, const std::string& ctx) {
    if (!v.is_number()) fail(ctx + ": expected a number, got " + v.dump());
    return v.get<float>();
}

bool asBool(const json& v, const std::string& ctx) {
    if (!v.is_boolean()) fail(ctx + ": expected true or false, got " + v.dump());
    return v.get<bool>();
}

std::string asString(const json& v, const std::string& ctx) {
    if (!v.is_string()) fail(ctx + ": expected a string, got " + v.dump());
    return v.get<std::string>();
}

std::vector<std::string> asStrings(const json& v, const std::string& ctx) {
    std::vector<std::string> out;
    const json& a = asArray(v, ctx);
    out.reserve(a.size());
    for (std::size_t i = 0; i < a.size(); ++i)
        out.push_back(asString(a[i], ctx + "[" + std::to_string(i) + "]"));
    return out;
}

// asArray and asObject return their argument, which always refers into a parsed document that
// outlives the call, never a temporary.
const json& asArray(const json& v, std::string_view ctx) {
    if (!v.is_array()) fail(std::string(ctx) + ": expected a list");
    return v; // NOLINT(bugprone-return-const-ref-from-parameter)
}

const json& asObject(const json& v, std::string_view ctx) {
    if (!v.is_object()) fail(std::string(ctx) + ": expected an object");
    return v; // NOLINT(bugprone-return-const-ref-from-parameter)
}

TilePos asTile(const json& v, const std::string& ctx, int w, int h) {
    if (!v.is_array() || v.size() != 2) fail(ctx + ": expected [x, y]");
    const int x = asInt(v[0], ctx + " x", 0, w - 1);
    const int y = asInt(v[1], ctx + " y", 0, h - 1);
    return {x, y};
}

std::array<int, 2> asIntPair(const json& v, const std::string& ctx, long long lo, long long hi) {
    if (!v.is_array() || v.size() != 2) fail(ctx + ": expected a pair [a, b]");
    return {asInt(v[0], ctx, lo, hi), asInt(v[1], ctx, lo, hi)};
}

int intOr(const json& obj, const char* key, int fallback, const std::string& ctx, long long lo,
          long long hi) {
    return has(obj, key) ? asInt(obj.at(key), ctx + ": " + key, lo, hi) : fallback;
}

float floatOr(const json& obj, const char* key, float fallback, const std::string& ctx) {
    return has(obj, key) ? asFloat(obj.at(key), ctx + ": " + key) : fallback;
}

bool boolOr(const json& obj, const char* key, bool fallback, const std::string& ctx) {
    return has(obj, key) ? asBool(obj.at(key), ctx + ": " + key) : fallback;
}

std::string stringOr(const json& obj, const char* key, const std::string& fallback,
                     const std::string& ctx) {
    return has(obj, key) ? asString(obj.at(key), ctx + ": " + key) : fallback;
}

void requireSetId(const std::string& id, const std::string& set, const std::string& ctx) {
    const auto dot = id.find('.');
    const bool nameOk = dot != std::string::npos && dot + 1 < id.size() &&
                        std::ranges::all_of(id.substr(dot + 1), [](char c) {
                            return (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '_';
                        });
    if (!nameOk || id.compare(0, dot, set) != 0 || dot != set.size())
        fail(ctx + ": id '" + id + "' is not '" + set + ".<name>' with a name of [a-z0-9_]");
}

} // namespace lc::world::detail
