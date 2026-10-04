"""Template library: load/save JSON templates and choose templates (fixed / random / rotation / smart)."""
from __future__ import annotations

import copy
import json
import random
import re
from pathlib import Path

from .paths import TEMPLATES_DIR

NATURE_WORDS = {"tree", "trees", "mountain", "mountains", "ocean", "sea", "river", "sun", "sunrise", "sunset", "rain",
                "storm", "flower", "flowers", "forest", "sky", "garden", "seed", "seeds", "wave", "waves", "wind",
                "bloom", "grow", "roots", "earth", "moon", "stars", "star", "sunshine", "nature", "climb", "summit"}
EMOTION_WORDS = {"heart", "love", "pain", "cry", "tears", "hurt", "broken", "alone", "lonely", "grief", "lost", "fear",
                 "soul", "heal", "healing", "sad", "sorry", "miss", "loss", "goodbye", "scars", "worthy", "enough",
                 "feel", "feelings", "hope"}


def load_templates(folder: Path | str = TEMPLATES_DIR) -> dict[str, dict]:
    tpls: list[dict] = []
    for f in sorted(Path(folder).glob("*.json")):
        try:
            t = json.loads(f.read_text(encoding="utf-8"))
            if "elements" in t:
                t.setdefault("id", f.stem)
                t.setdefault("name", f.stem)
                t.setdefault("tags", [])
                t.setdefault("builtin", not f.stem.startswith("custom_"))
                tpls.append(t)
        except Exception:
            continue  # ignore broken template files instead of crashing
    tpls.sort(key=lambda t: (t.get("order", 1000), t["name"]))
    return {t["id"]: t for t in tpls}


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_") or "template"


def save_template(tpl: dict, folder: Path | str = TEMPLATES_DIR) -> Path:
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    tpl = copy.deepcopy(tpl)
    if not tpl.get("id") or tpl.get("builtin", False):
        tpl["id"] = "custom_" + slug(tpl.get("name", "template"))
    tpl["builtin"] = False
    path = folder / f"{tpl['id']}.json"
    path.write_text(json.dumps(tpl, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def delete_template(tpl_id: str, folder: Path | str = TEMPLATES_DIR) -> bool:
    if not tpl_id.startswith("custom_"):
        return False
    try:
        (Path(folder) / f"{tpl_id}.json").unlink()
        return True
    except OSError:
        return False


def blank_template(name="My Template") -> dict:
    return {"id": "", "name": name, "description": "Custom template", "tags": [], "elements": [
        {"type": "background", "fill": {"kind": "gradient", "colors": ["#1f2937", "#111827"], "angle": 135},
         "overlay": {"color": "#000000", "opacity": 0.0}, "blur": 0, "vignette": 0.0, "photo_kind": "nature"},
        {"type": "quote", "box": [0.1, 0.25, 0.8, 0.5], "font": "Modern", "weight": None, "color": "#FFFFFF",
         "align": "center", "valign": "middle", "max_size": 0.09, "min_size": 0.035, "line_spacing": 1.2,
         "letter_spacing": 0.0, "case": "none", "quote_marks": True, "opacity": 1.0},
        {"type": "author", "box": [0.1, 0.78, 0.8, 0.06], "font": "Modern", "color": "#CCCCCC", "align": "center",
         "max_size": 0.032, "min_size": 0.02, "letter_spacing": 0.05},
        {"type": "brand", "position": "auto", "scale": 1.0}]}


def smart_pick(quote: dict, templates: list[dict], rng: random.Random, last_id: str | None = None) -> dict:
    """Local rule-based selection - no AI. Short -> bold, long -> minimal, emotional -> cinematic, nature -> nature."""
    text = quote.get("text", "")
    cat = (quote.get("category") or "").lower()
    words = re.findall(r"[a-z']+", (text + " " + cat).lower())
    wset, n = set(words), len(text.split())
    if wset & NATURE_WORDS or cat in ("nature", "ocean", "mountains", "sunset"):
        want = ["nature", "photo"]
    elif wset & EMOTION_WORDS or cat in ("emotional", "love", "healing"):
        want = ["cinematic", "luxury"]
    elif n <= 8:
        want = ["bold", "gradient"]
    elif n >= 22:
        want = ["minimal", "soft", "editorial"]
    else:
        want = ["gradient", "luxury", "soft", "editorial", "photo", "cinematic"]
    for tag in want:
        cands = [t for t in templates if tag in t.get("tags", []) and t["id"] != last_id]
        if cands:
            return rng.choice(cands)
    cands = [t for t in templates if t["id"] != last_id] or templates
    return rng.choice(cands)


class TemplateChooser:
    """Stateful template selection for a batch."""

    def __init__(self, templates: list[dict], mode: str, rng: random.Random):
        self.templates, self.mode, self.rng = templates, mode, rng
        self.i = 0
        self.bag: list[dict] = []
        self.last: str | None = None

    def next(self, quote: dict, exclude: set[str] | None = None) -> dict:
        exclude = exclude or set()
        pool = [t for t in self.templates if t["id"] not in exclude] or self.templates
        if self.mode == "fixed":
            t = self.templates[0] if not exclude else pool[0]
        elif self.mode == "rotate":
            for _ in range(len(self.templates)):
                t = self.templates[self.i % len(self.templates)]
                self.i += 1
                if t["id"] not in exclude or len(pool) == len(self.templates):
                    break
        elif self.mode == "smart":
            t = smart_pick(quote, pool, self.rng, self.last)
        else:  # random: shuffle-bag, never same template twice in a row
            for _ in range(3):
                if not self.bag:
                    self.bag = self.templates[:]
                    self.rng.shuffle(self.bag)
                cand = [b for b in self.bag if b["id"] in {p["id"] for p in pool}]
                if not cand:
                    self.bag = []
                    continue
                t = cand[0] if not (cand[0]["id"] == self.last and len(cand) > 1) else cand[1]
                self.bag.remove(t)
                break
            else:
                t = self.rng.choice(pool)
        self.last = t["id"]
        return t
