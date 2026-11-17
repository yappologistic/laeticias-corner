# Writes an unreadable save file for the corrupt-save scripted test.
file(WRITE "${FILE}" "{\"version\": 1, \"terrain\": [0, 0, oops")
