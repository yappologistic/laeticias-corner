# Fails unless FILE holds exactly CONTENT, and checks that a file EXISTS when given.
file(READ "${FILE}" got)
if(NOT got STREQUAL CONTENT)
  message(FATAL_ERROR "${FILE} changed: '${got}'")
endif()
if(DEFINED EXISTS AND NOT EXISTS "${EXISTS}")
  message(FATAL_ERROR "${EXISTS} is missing")
endif()
