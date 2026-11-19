# Writes OUT, a C++ source defining lc::build's version, commit and platform. Run in script mode
# (cmake -P) on every build, so the commit is the one built, not the one configured; the file is
# replaced only when its text changes, so an unchanged commit rebuilds nothing.
execute_process(COMMAND git rev-parse --short=12 HEAD WORKING_DIRECTORY "${SOURCE_DIR}"
                OUTPUT_VARIABLE commit OUTPUT_STRIP_TRAILING_WHITESPACE
                RESULT_VARIABLE failed ERROR_QUIET)
if(failed)
  set(commit "unknown") # a source tree without git
else()
  # The index's file times first, so a file only touched does not count as changed.
  execute_process(COMMAND git update-index -q --refresh WORKING_DIRECTORY "${SOURCE_DIR}"
                  OUTPUT_QUIET ERROR_QUIET)
  execute_process(COMMAND git diff-index --quiet HEAD -- WORKING_DIRECTORY "${SOURCE_DIR}"
                  RESULT_VARIABLE dirty ERROR_QUIET)
  if(dirty)
    string(APPEND commit "-modified")
  endif()
endif()
file(WRITE "${OUT}.tmp" "#include \"app/version.hpp\"

namespace lc::build {

const std::string_view kVersion = \"${VERSION}\";
const std::string_view kCommit = \"${commit}\";
const std::string_view kPlatform = \"${PLATFORM}\";

} // namespace lc::build
")
file(COPY_FILE "${OUT}.tmp" "${OUT}" ONLY_IF_DIFFERENT)
file(REMOVE "${OUT}.tmp")
