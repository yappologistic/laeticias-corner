#pragma once
// Shared fixtures: the real catalog from the source tree and scratch directories in the build tree.

#include "core/catalog.hpp"

#include <filesystem>
#include <string>

namespace lc::test {

[[nodiscard]] const std::string& catalogText();
[[nodiscard]] const Catalog& catalog();
[[nodiscard]] std::filesystem::path assetsDir();
// A fresh, empty directory under the build tree.
[[nodiscard]] std::filesystem::path tempDir(const std::string& name);

} // namespace lc::test
