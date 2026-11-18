# The benchmark wrote one report beside the save, with its verdict, renderer, display and the
# frame-time statistics of every leg of the tour.
file(GLOB reports "${DIR}/benchmark-*.txt")
list(LENGTH reports n)
if(NOT n EQUAL 1)
  message(FATAL_ERROR "expected one benchmark report in ${DIR}, found ${n}")
endif()
file(READ "${reports}" text)
foreach(want "Verdict: " "Renderer: " "Window: 1280x720" "Whole frame" "GPU done" "fast panning"
        "night with lights and rain" "panels open")
  string(FIND "${text}" "${want}" at)
  if(at EQUAL -1)
    message(FATAL_ERROR "the report lacks '${want}':\n${text}")
  endif()
endforeach()
