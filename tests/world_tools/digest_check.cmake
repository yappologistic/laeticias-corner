# Cross-checks the engine's world digest against tools/worldgen's reader on today's data: runs
# world_digest.py with worldgen's virtualenv into the build tree, then the digest test case
# against that file. The world builders change the data all the time, so the reference is made
# at test time rather than committed. Without the virtualenv the test is skipped (exit 77).
# Inputs: PY (venv python), SCRIPT (world_digest.py), OUT (json to write), TESTS (lc_world_tests).
if(NOT EXISTS "${PY}")
  message("skipped: no worldgen virtualenv at ${PY} (tools/worldgen/build.sh --test creates it)")
  cmake_language(EXIT 77)
endif()
execute_process(COMMAND "${PY}" "${SCRIPT}" OUTPUT_FILE "${OUT}" RESULT_VARIABLE rc)
if(NOT rc EQUAL 0)
  message(FATAL_ERROR "world_digest.py failed (${rc})")
endif()
execute_process(COMMAND "${CMAKE_COMMAND}" -E env "LC_WORLD_DIGEST=${OUT}"
                        "${TESTS}" "--test-case=real world: the digest*" RESULT_VARIABLE rc)
if(NOT rc EQUAL 0)
  message(FATAL_ERROR "the engine's digest differs from worldgen's")
endif()
