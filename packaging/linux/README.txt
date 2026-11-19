Laeticia's Corner - pre-alpha build for Linux (x86_64)
======================================================

A cosy isometric pixel-art world you decorate at your own pace. This is an early pre-alpha:
it runs and is playable, and it has rough edges.

Starting the game
-----------------
Unpack the archive anywhere and run the game from its folder:

  tar xzf laeticias-corner-*-linux-x86_64.tar.gz
  ./laeticias-corner-*-linux-x86_64/laeticias-corner

Keep the assets folder and libSDL3.so.0 beside the program. It runs on X11 and Wayland, with
PipeWire, PulseAudio or ALSA for sound, on distributions with glibc 2.35 or newer, or
RHEL/AlmaLinux 9 (for example Ubuntu 22.04+, Debian 12+, Fedora 36+). Nothing else needs to be
installed: the C++ runtime is built in and SDL comes in the archive.

The build is not signed. You can check the download against SHA256SUMS.txt from the release
page:  sha256sum -c SHA256SUMS.txt --ignore-missing

Saves
-----
Your worlds, settings and window position are saved on their own in
  ~/.local/share/Laeticia/laeticias-corner/   (or $XDG_DATA_HOME/Laeticia/laeticias-corner/)
Postcards (P in the game) go to your Pictures folder, under "Laeticia's Corner".

Controls
--------
Drag or WASD to look around, mouse wheel to zoom, B for the build drawer, M for the map,
J for the sketchbook, Esc for the menu. The full list is in the project's README.

Reporting a bug
---------------
https://github.com/yappologistic/laeticias-corner/issues (the "Bug report" form). Please say
which version you have (./laeticias-corner --version), your distribution and desktop (X11 or
Wayland), what you did, what happened, and add a screenshot and the terminal output.

Licences
--------
Code: MPL-2.0 (LICENSE). Art, audio, world data and text: CC BY-NC-SA 4.0 (LICENSE-ASSETS).
Details in LICENSING.md; the libraries and fonts inside are listed in THIRD-PARTY.md and
their licence texts are in the licenses folder and in assets/fonts.
