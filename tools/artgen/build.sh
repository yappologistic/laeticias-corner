#!/bin/sh
# Regenerate assets/atlas.png + assets/atlas.json (and validate). Options: --tile W (tile width,
# default from the catalog), --out DIR (write the atlas and previews there), --preview (write
# preview scenes, to out/artgen/ by default). Creates the pinned virtualenv on first use.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
if [ ! -x "$here/.venv/bin/python" ]; then
    python3 -m venv "$here/.venv"
    "$here/.venv/bin/pip" install --quiet -r "$here/requirements.txt"
fi
exec "$here/.venv/bin/python" "$here/generate.py" "$@"
