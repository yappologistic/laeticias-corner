# Third-party software and fonts

Everything here keeps its own licence. All of it is compatible with distributing the game under
the project's licences ([`LICENSING.md`](LICENSING.md)).

## Included in this repository

| Part | Version | Licence | Licence text | Used for |
|---|---|---|---|---|
| [stb_truetype](https://github.com/nothings/stb) | v1.28 | MIT or public domain (your choice) | `third_party/stb/LICENSE` | rasterising interface text |
| [stb_vorbis](https://github.com/nothings/stb) | v1.24 | MIT or public domain (your choice) | `third_party/stb/LICENSE` | decoding music and ambience |
| [doctest](https://github.com/doctest/doctest) | 2.4.12 | MIT | `third_party/doctest/LICENSE.txt` | unit tests (not part of the game) |
| [Nunito](https://github.com/googlefonts/nunito) SemiBold and ExtraBold | static instances | SIL Open Font License 1.1 | `assets/fonts/Nunito-OFL.txt` | interface text |
| [Noto Sans](https://github.com/notofonts/latin-greek-cyrillic) Medium and Bold | static instances | SIL Open Font License 1.1 | `assets/fonts/Noto-OFL.txt` | Greek, extended Latin and IPA fallback |
| [Noto Sans Old Persian](https://github.com/notofonts/old-persian) | Regular | SIL Open Font License 1.1 | `assets/fonts/Noto-OFL.txt` | Old Persian cuneiform |
| [Lucide](https://lucide.dev) icon font | `lucide-static` 1.74.0 | ISC; some glyphs MIT (from Feather) | `assets/fonts/lucide-LICENSE.txt` | interface icons |

The vendored code is unmodified; `third_party/stb/stb_impl.c` is the project's own file that
compiles both stb implementations. `third_party/README.md` and `assets/fonts/README.md` give the
upstream sources in more detail.

The world generator's previews draw labels with Nunito (`tools/worldgen/worldgen/preview.py`);
the Open Font License allows images made with a font to be used freely.

## Needed to build, not included

| Part | Version | Licence |
|---|---|---|
| [SDL](https://libsdl.org) 3 | ≥ 3.4 | zlib |
| [nlohmann/json](https://github.com/nlohmann/json) | ≥ 3.11 | MIT |
| CMake, Ninja, GCC or Clang | see `README.md` | their own (build tools only) |

## Needed to regenerate assets, not included

The generators under `tools/` install these from PyPI into a local virtual environment, pinned in
each tool's `requirements.txt`:

| Part | Version | Licence | Tools |
|---|---|---|---|
| [NumPy](https://numpy.org) | 2.5.5 | BSD-3-Clause | artgen, audiogen, worldgen |
| [Pillow](https://python-pillow.org) | 13.0.0 | MIT-CMU (HPND) | artgen, worldgen |
| [SciPy](https://scipy.org) | 1.18.1 | BSD-3-Clause | audiogen |

The audio validator (`tools/audiogen/validate.py`) calls an installed `ffmpeg` as an independent
loudness and format meter; it is not needed to build or play.

## No outside media

No art or audio in the game comes from third-party samples, photographs or images, and none was
made with outside generative models. Every sprite, sound and piece of music is computed by the
project's own deterministic generators under `tools/` from code and fixed seeds.
