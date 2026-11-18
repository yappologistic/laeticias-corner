#pragma once
// Strict JSON access shared by the world loaders (internal): every failure throws Invalid with a
// message naming the file, the object and the field; the public parse functions catch it and
// return it as their error.

#include "core/iso.hpp"

#include <nlohmann/json.hpp>

#include <array>
#include <cstdint>
#include <stdexcept>
#include <string>
#include <string_view>
#include <vector>

namespace lc::world::detail {

using nlohmann::json;

struct Invalid : std::runtime_error {
    using std::runtime_error::runtime_error;
};

[[noreturn]] void fail(const std::string& msg);

// Parses a whole document; a syntax error names the file and the byte offset.
[[nodiscard]] json parseDocument(std::string_view text, const std::string& file);
// The document must be an object with "version": 1 (newer versions are refused).
void requireVersion1(const json& doc, const std::string& file);

// Functions returning a reference take their context as a string_view: GCC flags a reference
// returned from a call with a temporary std::string argument as possibly dangling.
[[nodiscard]] const json& field(const json& obj, const char* key, std::string_view ctx);
[[nodiscard]] bool has(const json& obj, const char* key);

[[nodiscard]] int asInt(const json& v, const std::string& ctx, long long lo, long long hi);
[[nodiscard]] float asFloat(const json& v, const std::string& ctx);
[[nodiscard]] bool asBool(const json& v, const std::string& ctx);
[[nodiscard]] std::string asString(const json& v, const std::string& ctx);
[[nodiscard]] std::vector<std::string> asStrings(const json& v, const std::string& ctx);
[[nodiscard]] const json& asArray(const json& v, std::string_view ctx);
[[nodiscard]] const json& asObject(const json& v, std::string_view ctx);
// [x, y] of integers inside [0, w) x [0, h).
[[nodiscard]] TilePos asTile(const json& v, const std::string& ctx, int w, int h);
// [a, b] of integers in [lo, hi].
[[nodiscard]] std::array<int, 2> asIntPair(const json& v, const std::string& ctx, long long lo,
                                           long long hi);

[[nodiscard]] int intOr(const json& obj, const char* key, int fallback, const std::string& ctx,
                        long long lo, long long hi);
[[nodiscard]] float floatOr(const json& obj, const char* key, float fallback,
                            const std::string& ctx);
[[nodiscard]] bool boolOr(const json& obj, const char* key, bool fallback, const std::string& ctx);
[[nodiscard]] std::string stringOr(const json& obj, const char* key, const std::string& fallback,
                                   const std::string& ctx);

// `<set>.<name>` with `<name>` of [a-z0-9_]+ and `<set>` the expected set.
void requireSetId(const std::string& id, const std::string& set, const std::string& ctx);

} // namespace lc::world::detail
