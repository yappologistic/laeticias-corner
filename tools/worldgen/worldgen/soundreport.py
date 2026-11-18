"""`build.sh --sounds`: what every region plays by season, by day (12:00) and by night (00:00)
in the season's middle month, its nature beds, zones, timed loops, festival music and turn cues,
and which audio files no region file names (`out/worldgen/sounds.md`)."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from . import climates as C
from . import sound, soundplan

# Files the engine plays by family or by manifest tag without a region naming them
# (city_sound.cpp: open sea, wind in trees, drips after rain, layers by fresh water).
ENGINE_FAMILIES = ("sea.open", "wind.trees", "wind.bare")
ENGINE_TAGS = (("rain", "drip"), ("layer", "water"))


def short(f: str) -> str:
    return f.removeprefix("amb/").removeprefix("sfx/").removesuffix(".ogg").removesuffix(".wav")


def used_files(docs: list[dict], root: Path) -> tuple[set[str], set[str]]:
    """(files the region files name, files the engine plays on its own)."""
    files, families = sound.manifests(root)
    named: set[str] = set()
    for doc in docs:
        for _w, name, kind in sound.audio_names(doc):
            if kind == "file":
                named.add(name)
            else:
                named.update(families.get(name, []))
    engine: set[str] = set()
    for fam in ENGINE_FAMILIES:
        engine.update(families.get(fam, []))
    for m in sorted((root / "assets/audio").glob("*/manifest.json")):
        for e in json.loads(m.read_text()).get("files", []):
            tags = set(e.get("tags", []))
            if any(set(t) <= tags for t in ENGINE_TAGS):
                engine.add(e["file"])
    return named, engine


def run(b) -> Path:
    root = b.root
    docs = [json.loads(f.read_text()) for f in sorted((root / "assets/regions").glob("*.json"))]
    world = b.composed()
    lines = ["# What every region sounds like (`build.sh --sounds`)", "",
             "Beds as the engine chooses them (a season's own beds replace the plain ones for "
             "their hours and months), in the season's middle month, at 12:00 and 00:00; the "
             "nature bed at night (`nature_seasons`, `nature_snow` while snow lies); zones, timed "
             "loops, festival music and the turns' cues. Paths without `amb/` and `.ogg`.", ""]
    head = "| region | climate | " + " | ".join(f"{s} day / night" for s in C.SEASONS) + \
        " | nature at night (sp/su/au/wi; snow) |"
    lines += [head, "|" + "---|" * (3 + len(C.SEASONS)) + ""]
    detail = []
    for doc in docs:
        rid = doc["id"]
        cells = []
        for s, ms in soundplan.SEASON_MONTHS.items():
            m = ms[1]
            day = " + ".join(short(f) for f in soundplan.beds_at(doc, s, m, 12.0)) or "**none**"
            night = " + ".join(short(f) for f in soundplan.beds_at(doc, s, m, 0.0)) or "**none**"
            cells.append(f"{day} / {night}")
        snd = doc.get("theme", {}).get("sound", {})
        ns = snd.get("nature_seasons") or {}
        nat = "/".join(short(ns.get(s, {}).get("night", "")) or "—" for s in C.SEASONS) if ns else "—"
        if snd.get("nature_snow"):
            nat += "; " + short(snd["nature_snow"]["night"])
        lines.append(f"| {rid} | {snd.get('climate', '')} | " + " | ".join(cells) + f" | {nat} |")
        amb = doc.get("theme", {}).get("ambience", {})
        zones = Counter(short(z["file"]) for z in amb.get("zones", []))
        loops = Counter(f"{short(x['file'])}" + (f" ({x['months'][0]}–{x['months'][-1]})"
                                                 if x.get("months") else "")
                        for x in amb.get("loops", []))
        fest = sorted({f"{e['id']}: {short((e.get('ambience') or {}).get('file', '') or e.get('sfx', ''))}"
                       for e in doc.get("events", [])
                       if (e.get("ambience") or {}).get("file") in soundplan.FESTIVAL_FILES
                       or e.get("sfx") in soundplan.FESTIVAL_FILES})
        turns = sorted({f"{e['turn']}: {short(e.get('sfx') or (e.get('ambience') or {}).get('file', ''))}"
                        for e in doc.get("events", []) if e.get("turn")})
        work = sorted({f"{r['id']}: {short(r['sound']['loop'])}" for r in doc.get("roles", [])
                       if r.get("sound", {}).get("loop")})
        calls = sorted({short(c["file"]) for c in snd.get("calls", [])})
        f = soundplan.facts(world, rid)
        errs = soundplan.check(doc) + soundplan.check_world(doc, f)
        detail += [f"### {rid}", "",
                   f"- sea within hearing: {'yes' if f['hears_sea'] else 'no'}; season sting: "
                   f"{short(snd.get('stings', {}).get('season', '—'))}",
                   "- zones: " + (", ".join(f"{k} ×{v}" for k, v in sorted(zones.items())) or "—"),
                   "- loops on placed kinds: " + (", ".join(f"{k} ×{v}" for k, v in sorted(loops.items())) or "—"),
                   "- work loops (roles): " + (", ".join(work) or "—"),
                   "- festival music: " + (", ".join(fest) or "—"),
                   "- turn cues: " + (", ".join(turns) or "—"),
                   "- calls: " + (", ".join(calls) or "—")]
        if errs:
            detail.append("- **problems:** " + "; ".join(f"{w}: {m}" for _lv, w, m in errs))
        detail.append("")
    named, engine = used_files(docs, root)
    files, _fam = sound.manifests(root)
    home = json.loads((root / "assets/catalog.json").read_text()).get("audio", {})
    homefiles = {x for k, v in home.items() if isinstance(v, list) for x in v
                 if isinstance(x, str)}
    homeset = {e["file"] for e in json.loads((root / "assets/audio/home/manifest.json")
                                             .read_text()).get("files", [])}
    spare = sorted(f for f in files if f not in named and f not in engine and f not in homefiles
                   and f not in homeset and not f.startswith("music/"))
    lines += ["", f"{len(named & files)} manifest files are named by region files; {len(engine)} "
              f"more are played by the engine on its own (open sea, wind in trees, drips, the "
              "frogs' layer); the home set's own files (the corner's visitors, steps, watering) "
              "are the home catalog's and not listed.", "", "## Audio files no region uses", ""]
    lines += [f"- `{f}`" for f in spare] or ["- none"]
    lines += ["", "## Per region", ""] + detail
    out = b.reports / "sounds.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n")
    return out
