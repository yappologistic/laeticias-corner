# Compares two determinism runs: the screenshot and thumbnail byte for byte, and the world save
# byte for byte apart from its creation time (the wall clock is the one input not from the seed).
foreach(f determinism.png save/worlds/laeticias-corner/thumb.png)
  execute_process(COMMAND ${CMAKE_COMMAND} -E compare_files "${A}/${f}" "${B}/${f}"
                  RESULT_VARIABLE differ)
  if(differ)
    message(FATAL_ERROR "${f} differs between the two runs")
  endif()
endforeach()
set(save save/worlds/laeticias-corner/world.json)
file(READ "${A}/${save}" ja)
file(READ "${B}/${save}" jb)
string(REGEX REPLACE "\"created\": *\"[^\"]*\"" "" ja "${ja}")
string(REGEX REPLACE "\"created\": *\"[^\"]*\"" "" jb "${jb}")
if(NOT ja STREQUAL jb)
  message(FATAL_ERROR "${save} differs between the two runs")
endif()
message(STATUS "determinism: screenshots, thumbnails and saves match")
