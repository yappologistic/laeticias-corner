# Cross-checks the engine against tools/worldgen on today's data: runs a worldgen-side script with
# worldgen's virtualenv into the build tree, then one test case against its output. The world
# builders change the data all the time, so the reference is made at test time rather than
# committed. Without the virtualenv the test is skipped (exit 77).
# Inputs: PY (venv python), SCRIPT (the worldgen-side script), OUT (json to write), TESTS (the
# doctest binary), ENV (the variable naming OUT for the case), CASE (the test case filter).
# Used by world_digest (world_digest.py) and life_chains (life_chains.py).
if(NOT EXISTS "${PY}")
  message("skipped: no worldgen virtualenv at ${PY} (tools/worldgen/build.sh --test creates it)")
  cmake_language(EXIT 77)
endif()
execute_process(COMMAND "${PY}" "${SCRIPT}" OUTPUT_FILE "${OUT}" RESULT_VARIABLE rc)
if(NOT rc EQUAL 0)
  message(FATAL_ERROR "${SCRIPT} failed (${rc})")
endif()
execute_process(COMMAND "${CMAKE_COMMAND}" -E env "${ENV}=${OUT}" "${TESTS}" "--test-case=${CASE}"
                RESULT_VARIABLE rc)
if(NOT rc EQUAL 0)
  message(FATAL_ERROR "the engine disagrees with tools/worldgen (${CASE})")
endif()
