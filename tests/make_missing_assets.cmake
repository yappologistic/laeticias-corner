# Builds an assets directory without the cliff sprites (everything else linked to the real
# assets) for the missing-art scripted run.
file(REMOVE_RECURSE "${OUT}")
file(MAKE_DIRECTORY "${OUT}")
file(READ "${SRC}/atlas.json" json)
string(JSON json REMOVE "${json}" sprites edge/cliff_se)
string(JSON json REMOVE "${json}" sprites edge/cliff_sw)
file(WRITE "${OUT}/atlas.json" "${json}")
foreach(entry catalog.json atlas.png fonts audio)
  file(CREATE_LINK "${SRC}/${entry}" "${OUT}/${entry}" SYMBOLIC)
endforeach()
