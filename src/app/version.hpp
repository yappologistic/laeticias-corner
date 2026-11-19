#pragma once
// What this build is: its version, the commit it was built from and the system it was built for.

#include <string_view>

namespace lc::build {

extern const std::string_view kVersion;  // 0.1.0, with a pre-release suffix while there is one
extern const std::string_view kCommit;   // short hash, "-modified" with uncommitted changes
extern const std::string_view kPlatform; // windows-x64, linux-x86_64, ...

} // namespace lc::build
