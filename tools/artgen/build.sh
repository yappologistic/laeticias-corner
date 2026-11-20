#!/bin/sh
# Regenerate assets/atlas.png + assets/atlas.json (and validate). Options: --tile W (tile width,
# default from the catalog), --out DIR (write the atlas and previews there), --preview (write
# preview scenes, to out/artgen/ by default). --icon instead draws the application icon into
# assets/icon/ (icon.py; --check compares with the committed files). Creates the pinned
# virtualenv on first use.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
if [ ! -x "$here/.venv/bin/python" ]; then
    python3 -m venv "$here/.venv"
    "$here/.venv/bin/pip" install --quiet -r "$here/requirements.txt"
fi
if [ "$1" = "--icon" ]; then
    shift
    exec "$here/.venv/bin/python" "$here/icon.py" "$@"
fi
exec "$here/.venv/bin/python" "$here/generate.py" "$@"
