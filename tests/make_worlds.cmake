# Writes COUNT worlds under DIR/worlds (world-01...), each a copy of SAVE with the picture THUMB:
# a worlds screen with more cards than one frame uploads pictures for. DIR is emptied first.
file(REMOVE_RECURSE "${DIR}")
foreach(i RANGE 1 ${COUNT})
  string(LENGTH "${i}" len)
  set(slug "world-${i}")
  if(len LESS 2)
    set(slug "world-0${i}")
  endif()
  file(MAKE_DIRECTORY "${DIR}/worlds/${slug}")
  file(COPY_FILE "${SAVE}" "${DIR}/worlds/${slug}/world.json")
  file(COPY_FILE "${THUMB}" "${DIR}/worlds/${slug}/thumb.png")
endforeach()
