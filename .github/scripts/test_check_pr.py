#!/usr/bin/env python3
"""Tests for check_pr.py: descriptions that must pass and descriptions that must fail.

Run: python3 .github/scripts/test_check_pr.py
"""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import check_pr  # noqa: E402

TEMPLATE = (pathlib.Path(__file__).resolve().parents[1] / "pull_request_template.md").read_text(
    encoding="utf-8")

BUILD_OK = """```
$ cmake --preset release && cmake --build --preset release -j4
$ ctest --preset release
100% tests passed out of 412
$ cmake --preset asan && cmake --build --preset asan -j4 && ctest --preset asan
100% tests passed out of 412
```"""
SHOT = ("![before](https://github.com/user-attachments/assets/0b1c2d3e-before)\n"
        "![after](https://github.com/user-attachments/assets/0b1c2d3e-after)\n"
        "Made with `laeticias-corner --script shots.lcs --size 1280x800 --seed 1`.")


def body(issue="Closes #42",
         what="The cat no longer naps on a bench that was removed under it.",
         kinds=("Bug fix", "Engine code"),
         build=BUILD_OK,
         platform="Linux 6.x, GCC 16.2, SDL 3.4.20",
         repro="tests/scripts/cat_bench.lcs fails before (expect actor cat nap bench), passes after.",
         shots="n/a", bench="n/a", regen="n/a",
         tool="none", model="none", produced="none",
         read=True, terms=True, drop=()):
    labels = [label for label in check_pr.KINDS.values()]
    kind_lines = "\n".join(f"- [{'x' if any(label.startswith(k) for k in kinds) else ' '}] {label}"
                           for label in labels)
    parts = {
        "Issue": f"## Issue\n\n{issue}\n",
        "What changes": f"## What changes\n\n{what}\n",
        "Kind of change": f"## Kind of change\n\n{kind_lines}\n",
        "Proof of work": "## Proof of work\n\n" + "".join(
            f"### {name}\n\n{text}\n\n" for name, text in [
                ("Build and test", build), ("Platform", platform), ("Reproduction", repro),
                ("Before and after", shots), ("Benchmark", bench), ("Regeneration", regen)]
            if name not in drop),
        "AI assistance": (f"## AI assistance\n\n- Tool or harness: {tool}\n"
                          f"- Model and version: {model}\n- What it produced: {produced}\n\n"
                          f"- [{'x' if read else ' '}] I have read every line of this change, "
                          "built it and run it myself, and I answer for it.\n"),
        "Contribution terms": (f"## Contribution terms\n\n- [{'x' if terms else ' '}] I agree to "
                               "the contribution terms in CONTRIBUTING.md: my contribution is\n"
                               "  licensed under the project's licences.\n"),
    }
    return "\n".join(text for name, text in parts.items() if name not in drop)


class TemplateMatchesChecker(unittest.TestCase):
    """The checker and the template must name the same headings, boxes and fields."""

    def test_headings_boxes_and_fields(self):
        for name in check_pr.REQUIRED_SECTIONS:
            self.assertIn(f"\n## {name}\n", TEMPLATE)
        for name in check_pr.PROOF_SUBSECTIONS:
            self.assertIn(f"\n### {name}\n", TEMPLATE)
        for label in check_pr.KINDS.values():
            self.assertIn(f"- [ ] {label}", TEMPLATE)
        for name in check_pr.AI_FIELDS:
            self.assertIn(f"- {name}:", TEMPLATE)
        self.assertIn("- [ ] I have read every line", TEMPLATE)
        self.assertIn("- [ ] I agree to the contribution terms", TEMPLATE)

    def test_template_filled_in_passes(self):
        """The real template with every answer written under its heading passes."""
        answers = {
            "## Issue\n": "Closes #7\n",
            "## What changes\n": "The hens walk into the coop at dusk instead of at night.\n",
            "### Build and test\n": BUILD_OK + "\n",
            "### Platform\n": "Linux 6.x, GCC 16.2, SDL 3.4.20\n",
            "### Reproduction\n": "tests/scripts/hens_dusk.lcs fails before, passes after.\n",
            "### Before and after\n": "n/a\n",
            "### Benchmark\n": "n/a\n",
            "### Regeneration\n": "n/a\n",
        }
        text = TEMPLATE
        for head, answer in answers.items():
            text = text.replace(head, head + answer, 1)
        text = text.replace("- [ ] Bug fix", "- [x] Bug fix").replace(
            "- [ ] Engine code", "- [x] Engine code")
        for name in check_pr.AI_FIELDS:
            text = text.replace(f"- {name}:", f"- {name}: none")
        text = text.replace("- [ ] I have read", "- [x] I have read").replace(
            "- [ ] I agree", "- [x] I agree")
        self.assertEqual(check_pr.check(text, ["src/core/actors.cpp"]), [])


class MustPass(unittest.TestCase):
    def ok(self, text, files=()):
        self.assertEqual(check_pr.check(text, list(files)), [])

    def test_engine_bug_fix_without_ai(self):
        self.ok(body(), ["src/core/actors.cpp", "tests/scripts/cat_bench.lcs"])

    def test_art_change_with_images_and_ai(self):
        self.ok(body(kinds=("Art generator", "Changes what is seen"),
                     build=BUILD_OK.replace("asan", "release"), shots=SHOT, repro="n/a",
                     regen="tools/artgen/build.sh; validation passed; a second run is identical.",
                     tool="a coding agent in the terminal", model="example-model-4.1 (2026-05-01)",
                     produced="the first draft of the shading function; I rewrote the tests"),
                ["tools/artgen/props.py", "assets/atlas.png", "assets/atlas.json"])

    def test_documentation_only(self):
        self.ok(body(kinds=("Documentation only",), build="n/a", platform="n/a", repro="n/a",
                     what="Fixes the build command in docs/contributing/getting-started.md."),
                ["docs/contributing/getting-started.md"])

    def test_small_fix_without_issue(self):
        self.ok(body(issue="Small fix: a typo in a tooltip string.", kinds=("Interface text",),
                     repro="n/a"), ["src/ui/strings.hpp"])

    def test_html_image_and_windows_line_ends(self):
        text = body(kinds=("Changes what is seen", "Engine code"), repro="n/a",
                    shots='<img width="640" alt="after" src="https://example.org/after.png">')
        self.ok(text.replace("\n", "\r\n"), ["src/render/sprites.cpp"])

    def test_audio_change_needs_no_image(self):
        self.ok(body(kinds=("Audio generator",), repro="n/a",
                     build=BUILD_OK.replace("asan", "release"),
                     regen="tools/audiogen/generate.sh rain; validate.py: all files pass."),
                ["tools/audiogen/weather.py", "assets/audio/amb/rain.ogg"])


class MustFail(unittest.TestCase):
    def fails(self, text, files=(), expect=""):
        problems = check_pr.check(text, list(files))
        self.assertTrue(problems, "expected a failure")
        if expect:
            self.assertTrue(any(expect in p for p in problems), problems)

    def test_untouched_template(self):
        self.fails(TEMPLATE, ["src/core/actors.cpp"])

    def test_empty_description(self):
        self.fails("", expect="missing")

    def test_missing_ai_section(self):
        self.fails(body(drop=("AI assistance",)), expect="## AI assistance")

    def test_blank_ai_field(self):
        self.fails(body(model=""), expect="Model and version")

    def test_vague_model(self):
        self.fails(body(tool="a chat assistant", model="the latest one", produced="tests"),
                   expect="exact model")

    def test_ai_used_but_nothing_produced(self):
        self.fails(body(tool="an editor plug-in", model="model-7b-v2", produced="none"),
                   expect="which parts")

    def test_read_statement_not_ticked(self):
        self.fails(body(read=False), expect="I have read every line")

    def test_terms_not_ticked(self):
        self.fails(body(terms=False), expect="contribution terms")

    def test_asset_change_without_images(self):
        self.fails(body(kinds=("Art generator",), repro="n/a", regen="done, validated"),
                   ["assets/atlas.png"], expect="needs attached images")

    def test_visible_box_without_images(self):
        self.fails(body(kinds=("Changes what is seen", "Engine code"), repro="n/a"),
                   ["src/render/sprites.cpp"], expect="needs attached images")

    def test_no_ctest(self):
        self.fails(body(build="I built it and it works."), expect="ctest")

    def test_engine_without_asan(self):
        self.fails(body(build=BUILD_OK.replace("asan", "release")), expect="asan")

    def test_bug_fix_without_reproduction(self):
        self.fails(body(repro="n/a"), expect="Reproduction")

    def test_placeholder_text(self):
        self.fails(body(what="..."), expect="What changes")

    def test_missing_subsection(self):
        self.fails(body(drop=("Benchmark",)), expect="### Benchmark")

    def test_no_issue(self):
        self.fails(body(issue="Implements the thing we talked about."), expect="## Issue")

    def test_docs_only_box_with_other_kinds_and_no_build(self):
        self.fails(body(kinds=("Documentation only", "Engine code"), build="n/a"),
                   expect="Build and test")

    def test_performance_without_bench(self):
        self.fails(body(kinds=("Performance", "Engine code"), repro="n/a"), expect="Benchmark")

    def test_generator_change_without_regeneration(self):
        self.fails(body(kinds=("Engine code",), repro="n/a"), ["tools/worldgen/worldgen/build.py"],
                   expect="Regeneration")

    def test_tool_none_but_model_named(self):
        self.fails(body(tool="none", model="model-7b-v2"), expect="tool is")


if __name__ == "__main__":
    unittest.main()
