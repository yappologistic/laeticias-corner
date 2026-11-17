# Makes (MODE=prepare) or removes (MODE=cleanup) a directory the game cannot write to.
if(MODE STREQUAL "prepare")
  file(MAKE_DIRECTORY "${DIR}")
  file(CHMOD "${DIR}" DIRECTORY_PERMISSIONS OWNER_READ OWNER_EXECUTE GROUP_READ GROUP_EXECUTE)
else()
  file(CHMOD "${DIR}" DIRECTORY_PERMISSIONS OWNER_READ OWNER_WRITE OWNER_EXECUTE)
  file(REMOVE_RECURSE "${DIR}")
endif()
