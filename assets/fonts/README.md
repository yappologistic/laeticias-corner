# Fonts

| File | Source | Licence |
|---|---|---|
| `Nunito-SemiBold.ttf`, `Nunito-ExtraBold.ttf` | Nunito by The Nunito Project Authors, static instances (wght 600 and 800) served by Google Fonts | SIL Open Font License 1.1, `Nunito-OFL.txt` |
| `NotoSans-Medium.ttf`, `NotoSans-Bold.ttf` | Noto Sans by the Noto Project Authors (static Medium and Bold): fallback for the Greek, extended Latin and IPA letters Nunito lacks (world names and cards) | SIL Open Font License 1.1, `Noto-OFL.txt` |
| `NotoSansOldPersian-Regular.ttf` | Noto Sans Old Persian: Old Persian cuneiform (left to right, no shaping) | SIL Open Font License 1.1, `Noto-OFL.txt` |
| `lucide.ttf` | Lucide icon font, `lucide-static` 1.74.0 | ISC (some glyphs MIT, from Feather), `lucide-LICENSE.txt` |

The UI renders the icon font through the same text path as Nunito; icons are addressed by
codepoint in `src/ui/theme.hpp`.

Text the fonts cannot draw is never shown as "?": scripts that need shaping or right-to-left
layout (Persian and Arabic script) are not baked, and a `native` line in them is left out in
favour of its transliteration. `tests/test_coverage.cpp` checks every string of every region file
and catalog against the baked coverage.
