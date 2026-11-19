Laeticia's Corner - pre-alpha build for Windows (64-bit)
=========================================================

A cosy isometric pixel-art world you decorate at your own pace. This is an early pre-alpha:
it runs and is playable, and it has rough edges.

Starting the game
-----------------
Unpack the whole folder anywhere (do not run it from inside the zip), then double-click
laeticias-corner.exe. Keep the assets folder and SDL3.dll beside the program.

Windows 10 (version 1903 or newer) or Windows 11, 64-bit.

"Windows protected your PC"
---------------------------
The build is not signed, so Microsoft Defender SmartScreen may stop it the first time.
Click "More info", then "Run anyway". You can check the download against SHA256SUMS.txt
from the release page first:  certutil -hashfile laeticias-corner-...-windows-x64.zip SHA256

Saves
-----
Your worlds, settings and window position are saved on their own in
  %APPDATA%\Laeticia\laeticias-corner\
Postcards (P in the game) go to your Pictures folder, under "Laeticia's Corner".

Controls
--------
Drag or WASD to look around, mouse wheel to zoom, B for the build drawer, M for the map,
J for the sketchbook, Esc for the menu. The full list is in the project's README.

Reporting a bug
---------------
https://github.com/yappologistic/laeticias-corner/issues (the "Bug report" form). Please say
which version you have (shown by running "laeticias-corner.exe --version" in a terminal,
or the name of the zip), what you did, what happened, and add a screenshot.

Licences
--------
Code: MPL-2.0 (LICENSE). Art, audio, world data and text: CC BY-NC-SA 4.0 (LICENSE-ASSETS).
Details in LICENSING.md; the libraries and fonts inside are listed in THIRD-PARTY.md and
their licence texts are in the licenses folder and in assets\fonts.
