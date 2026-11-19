#pragma once
// The shader path's compiled fragment shaders (SPIR-V, committed beside their GLSL sources in
// assets/shaders/ and embedded at build time by cmake/embed_shaders.cmake).

#include <cstdint>
#include <span>
#include <string_view>

namespace lc::gpu {

// The blob for a shader's file stem ("final"); empty when there is none.
[[nodiscard]] std::span<const std::uint8_t> shader(std::string_view name);

} // namespace lc::gpu
