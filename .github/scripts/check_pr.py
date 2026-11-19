#!/usr/bin/env python3
"""Checks a pull request's description against .github/pull_request_template.md.

usage: check_pr.py --body-file BODY.md [--files-file CHANGED.txt]

CHANGED.txt lists the changed paths, one per line. Prints every problem found and exits 1 if
there is any, 0 otherwise. The rules are explained in docs/contributing/proof-of-work.md;
tests: test_check_pr.py beside this file. Standard library only, so it runs anywhere.
"""
from __future__ import annotations

import argparse
import os
import re
import sys

REQUIRED_SECTIONS = ["Issue", "What changes", "Kind of change", "Proof of work", "AI assistance",
                     "Contribution terms"]
PROOF_SUBSECTIONS = ["Build and test", "Platform", "Reproduction", "Before and after",
                     "Benchmark", "Regeneration"]
KINDS = {
    "bug": "Bug fix",
    "engine": "Engine code",
    "catalog": "Home content in the catalog",
    "art": "Art generator",
    "audio": "Audio generator",
    "world": "World data",
    "text": "Interface text or layout",
    "visible": "Changes what is seen on screen",
    "perf": "Performance",
    "docs": "Documentation only",
}
AI_FIELDS = ["Tool or harness", "Model and version", "What it produced"]

IMAGE = re.compile(
    r"!\[[^\]]*\]\([^)\s]+\)"                        # markdown image
    r"|<img\s[^>]*src\s*=\s*[\"']?[^\s\"'>]+"       # html image
    r"|https://github\.com/user-attachments/assets/[\w-]+"
    r"|https://(?:private-)?user-images\.githubusercontent\.com/\S+"
    r"|https?://\S+\.(?:png|jpe?g|gif|webp)\b",
    re.I,
)
IMAGE_EXT = re.compile(r"\.(png|jpe?g|gif|webp)$", re.I)
GENERATOR_PATHS = ("tools/artgen/", "tools/audiogen/", "tools/worldgen/")
PLACEHOLDER = re.compile(r"^(?:\.\.\.|…|todo|tbd|xxx|\?+|-|<(?!img\b)[^>]*>|\[[^\]]*\])$", re.I)
NA = re.compile(r"^(?:n/?a|none|not applicable)\.?$", re.I)
NONE = re.compile(r"^(?:none|no|n/?a|nothing|not used|no ai|no tool)\.?$", re.I)


def strip_comments(text: str) -> str:
    return re.sub(r"<!--.*?-->", "", text, flags=re.S)


def split_sections(body: str, level: int) -> dict[str, str]:
    """Heading text (lower case) -> the text under it, up to the next heading of that level or
    higher."""
    marks = "#" * level
    pattern = re.compile(rf"^{marks}(?!#)\s*(.+?)\s*#*\s*$", re.M)
    higher = re.compile(rf"^#{{1,{level - 1}}}(?!#)\s", re.M) if level > 1 else None
    found: dict[str, str] = {}
    heads = list(pattern.finditer(body))
    for i, m in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(body)
        chunk = body[m.end():end]
        if higher:
            h = higher.search(chunk)
            if h:
                chunk = chunk[:h.start()]
        found.setdefault(m.group(1).strip().lower(), chunk)
    return found


def content(text: str) -> str:
    """The section's text without headings below it, blank lines or surrounding space."""
    lines = [ln.strip() for ln in text.splitlines()]
    return "\n".join(ln for ln in lines if ln and not ln.startswith("#")).strip()


def is_empty(text: str) -> bool:
    c = content(text)
    return not c or all(PLACEHOLDER.match(ln.strip()) for ln in c.splitlines())


def ticked(text: str, label: str) -> bool:
    for m in re.finditer(r"^\s*[-*]\s*\[([ xX])\]\s*(.+)$", text, re.M):
        if m.group(2).strip().lower().startswith(label.lower()):
            return m.group(1).lower() == "x"
    return False


def field(text: str, name: str) -> str | None:
    m = re.search(rf"^\s*[-*]?\s*{re.escape(name)}\s*:[ \t]*(.*)$", text, re.M | re.I)
    return m.group(1).strip() if m else None


def needs_images(files: list[str]) -> list[str]:
    hits = []
    for f in files:
        if IMAGE_EXT.search(f) or f.startswith(("docs/images/", "tools/artgen/",
                                                "tools/worldgen/regions/")):
            hits.append(f)
        elif f.startswith("assets/") and not f.startswith("assets/audio/"):
            hits.append(f)
    return hits


def check(body: str, files: list[str]) -> list[str]:
    problems: list[str] = []
    body = strip_comments(body or "").replace("\r\n", "\n")
    top = split_sections(body, 2)
    for name in REQUIRED_SECTIONS:
        if name.lower() not in top:
            problems.append(f'The section "## {name}" is missing (use the template).')
    if problems:
        return problems

    kinds_text = top["kind of change"]
    kinds = {k for k, label in KINDS.items() if ticked(kinds_text, label)}
    docs_only = kinds == {"docs"}

    issue = content(top["issue"])
    if not (re.search(r"(?:^|\s|\()#\d+\b", issue)
            or re.search(r"https://github\.com/[\w.-]+/[\w.-]+/issues/\d+", issue)
            or re.match(r"small fix:\s*\S+(?:\s+\S+){2,}", issue, re.I)):
        problems.append('"## Issue" must link the accepted issue ("Closes #123"), or start with '
                        '"Small fix:" and a sentence for a small fix.')

    if len(content(top["what changes"])) < 20 or is_empty(top["what changes"]):
        problems.append('"## What changes" is empty or too short.')

    if not kinds:
        problems.append('"## Kind of change": tick at least one box.')

    proof = split_sections(top["proof of work"], 3)
    for name in PROOF_SUBSECTIONS:
        key = name.lower()
        if key not in proof:
            problems.append(f'The subsection "### {name}" under "## Proof of work" is missing.')
        elif is_empty(proof[key]):
            problems.append(f'"### {name}" is empty: answer it, or write "n/a" where the guide '
                            "allows.")
    if any(name.lower() not in proof for name in PROOF_SUBSECTIONS):
        return problems

    def na(key: str) -> bool:
        return bool(NA.match(content(proof[key])))

    build = content(proof["build and test"])
    if not docs_only:
        if na("build and test"):
            problems.append('"### Build and test" may only be "n/a" for documentation-only '
                            "changes.")
        elif not is_empty(proof["build and test"]):
            if "ctest" not in build.lower():
                problems.append('"### Build and test" must show the ctest command you ran.')
            if not re.search(r"tests? passed|passed|\bok\b", build, re.I):
                problems.append('"### Build and test" must include the result lines (for example '
                                '"100% tests passed").')
            if "engine" in kinds and "asan" not in build.lower():
                problems.append('Engine changes: "### Build and test" must include the asan '
                                "preset's run.")
        if na("platform"):
            problems.append('"### Platform" may only be "n/a" for documentation-only changes.')

    if "bug" in kinds and na("reproduction"):
        problems.append('Bug fixes: "### Reproduction" must give the failing test or script and '
                        "its results before and after.")

    visual_files = needs_images(files)
    shots = proof["before and after"]
    if visual_files or "visible" in kinds:
        if not IMAGE.search(shots):
            why = (f"files under image or asset paths changed ({', '.join(visual_files[:3])}"
                   f"{', ...' if len(visual_files) > 3 else ''})" if visual_files
                   else '"Changes what is seen on screen" is ticked')
            problems.append(f'"### Before and after" needs attached images: {why}.')

    if "perf" in kinds and (na("benchmark") or "bench" not in content(proof["benchmark"]).lower()):
        problems.append('Performance changes: "### Benchmark" must give --bench output before and '
                        "after.")

    generator = {"art", "audio", "world"} & kinds or any(f.startswith(GENERATOR_PATHS)
                                                         for f in files)
    if generator and na("regeneration"):
        problems.append('Generator changes: "### Regeneration" must say what you regenerated, '
                        "that the outputs are committed, and the validation result.")

    ai = top["ai assistance"]
    values = {}
    for name in AI_FIELDS:
        v = field(ai, name)
        if v is None:
            problems.append(f'"## AI assistance": the line "{name}:" is missing.')
        elif not v or PLACEHOLDER.match(v):
            problems.append(f'"## AI assistance": fill in "{name}:" (write "none" if no AI tool '
                            "was used).")
        else:
            values[name] = v
    if len(values) == len(AI_FIELDS):
        used = not NONE.match(values["Tool or harness"])
        if used:
            model = values["Model and version"]
            if NONE.match(model) or not re.search(r"\d", model):
                problems.append('"## AI assistance": give the exact model identifier and version '
                                "as the tool reports it.")
            if NONE.match(values["What it produced"]):
                problems.append('"## AI assistance": say which parts the tool produced.')
        elif not NONE.match(values["Model and version"]):
            problems.append('"## AI assistance": a model is named but the tool is "none".')
    if not ticked(ai, "I have read every line"):
        problems.append('"## AI assistance": tick "I have read every line of this change, built '
                        'it and run it myself, and I answer for it."')

    if not ticked(top["contribution terms"], "I agree to the contribution terms"):
        problems.append('"## Contribution terms": tick the box to agree to the contribution '
                        "terms.")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--body-file", required=True)
    ap.add_argument("--files-file")
    a = ap.parse_args()
    with open(a.body_file, encoding="utf-8") as f:
        body = f.read()
    files: list[str] = []
    if a.files_file:
        with open(a.files_file, encoding="utf-8") as f:
            files = [ln.strip() for ln in f if ln.strip()]
    problems = check(body, files)
    report = ("The pull request description is complete." if not problems else
              "The pull request description needs changes "
              "(see docs/contributing/proof-of-work.md):\n" +
              "\n".join(f"- {p}" for p in problems))
    print(report)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write(report + "\n")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
