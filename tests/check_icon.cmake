# The committed application icon (assets/icon/) is what tools/artgen/icon.py draws, byte for byte.
# Skipped (exit 77) without the art tool's virtualenv, which tools/artgen/build.sh creates.
if(NOT EXISTS "${PY}")
  message("${PY} is missing: skipped")
  cmake_language(EXIT 77)
endif()
execute_process(COMMAND "${PY}" "${SCRIPT}" --check RESULT_VARIABLE r)
if(NOT r EQUAL 0)
  message(FATAL_ERROR "assets/icon/ is stale: tools/artgen/build.sh --icon")
endif()
