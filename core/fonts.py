"""Font discovery and resolution.

Scans assets/fonts plus system font folders once (cached on disk), so worker
processes can resolve "Family + weight" to a file quickly.
"""
from __future__ import annotations

import json
import os
import re
import sys
from functools import lru_cache
from pathlib import Path

from PIL import ImageFont

from .paths import FONTS_DIR, USER_DIR

FONT_EXT = {".ttf", ".otf", ".ttc"}
WEIGHTS = {"thin": 100, "extralight": 200, "ultralight": 200, "light": 300, "regular": 400, "book": 400,
           "normal": 400, "roman": 400, "medium": 500, "semibold": 600, "demibold": 600, "bold": 700,
           "extrabold": 800, "ultrabold": 800, "heavy": 800, "black": 900}
WEIGHT_NAMES = {"Light": 300, "Regular": 400, "Medium": 500, "Semibold": 600, "Bold": 700, "Black": 900}

# preset -> (candidate families in order of preference, default weight, italic)
PRESETS = {
    "Bold": (["Anton", "Bebas Neue", "Oswald", "Montserrat", "Poppins", "Impact", "Arial Black", "Segoe UI", "DejaVu Sans"], 800),
    "Elegant": (["Cormorant Garamond", "Playfair Display", "Georgia", "Palatino Linotype", "Times New Roman", "DejaVu Serif"], 400),
    "Minimal": (["Inter", "Helvetica Neue", "Segoe UI", "Arial", "DejaVu Sans"], 300),
    "Editorial": (["Playfair Display", "Libre Baskerville", "Georgia", "Times New Roman", "DejaVu Serif"], 700),
    "Handwritten": (["Caveat", "Dancing Script", "Pacifico", "Segoe Script", "Ink Free", "Lucida Handwriting", "Comic Sans MS"], 400),
    "Modern": (["Poppins", "Montserrat", "Raleway", "Segoe UI", "Arial", "DejaVu Sans"], 600),
    "Serif": (["Merriweather", "Lora", "Georgia", "Times New Roman", "DejaVu Serif"], 400),
    "Sans-serif": (["Open Sans", "Roboto", "Segoe UI", "Arial", "Helvetica", "DejaVu Sans"], 400),
}


def _system_font_dirs() -> list[Path]:
    dirs = [FONTS_DIR]
    if sys.platform.startswith("win"):
        dirs.append(Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts")
        local = os.environ.get("LOCALAPPDATA")
        if local:
            dirs.append(Path(local) / "Microsoft/Windows/Fonts")
    elif sys.platform == "darwin":
        dirs += [Path("/Library/Fonts"), Path("/System/Library/Fonts"), Path.home() / "Library/Fonts"]
    else:
        dirs += [Path("/usr/share/fonts"), Path.home() / ".fonts", Path.home() / ".local/share/fonts"]
    return [d for d in dirs if d.exists()]


def _weight_of(style: str) -> tuple[int, bool]:
    s = style.lower().replace(" ", "").replace("-", "")
    italic = "italic" in s or "oblique" in s
    for key in sorted(WEIGHTS, key=len, reverse=True):
        if key in s:
            return WEIGHTS[key], italic
    return 400, italic


def _signature(dirs) -> str:
    n, newest = 0, 0.0
    for d in dirs:
        for root, _, files in os.walk(d):
            for f in files:
                if Path(f).suffix.lower() in FONT_EXT:
                    n += 1
                    try:
                        newest = max(newest, os.path.getmtime(os.path.join(root, f)))
                    except OSError:
                        pass
    return f"{n}:{newest:.0f}"


def _scan(dirs) -> dict:
    index: dict[str, list] = {}
    for d in dirs:
        for root, _, files in os.walk(d):
            for f in files:
                p = Path(root) / f
                if p.suffix.lower() not in FONT_EXT:
                    continue
                try:
                    family, style = ImageFont.truetype(str(p), 20).getname()
                except Exception:
                    continue  # corrupt / unsupported font file
                w, it = _weight_of(style)
                index.setdefault(family, []).append([w, it, str(p)])
    return index


@lru_cache(maxsize=1)
def font_index() -> dict:
    """{family: [[weight, italic, path], ...]} cached in ~/.quotebatch_studio/fonts_cache.json."""
    dirs = _system_font_dirs()
    cache = USER_DIR / "fonts_cache.json"
    sig = _signature(dirs)
    try:
        data = json.loads(cache.read_text(encoding="utf-8"))
        if data.get("sig") == sig:
            return data["index"]
    except Exception:
        pass
    index = _scan(dirs)
    try:
        USER_DIR.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps({"sig": sig, "index": index}), encoding="utf-8")
    except OSError:
        pass
    return index


def refresh_font_index() -> None:
    font_index.cache_clear()
    try:
        (USER_DIR / "fonts_cache.json").unlink()
    except OSError:
        pass
    font_index()
    load_font.cache_clear()


def families() -> list[str]:
    return sorted(font_index().keys(), key=str.lower)


def find_family(name: str) -> str | None:
    low = name.lower()
    for fam in font_index():
        if fam.lower() == low:
            return fam
    return None


def path_for(family: str, weight: int = 400, italic: bool = False) -> str | None:
    fam = find_family(family)
    if not fam:
        return None
    faces = font_index()[fam]
    pool = [f for f in faces if bool(f[1]) == italic] or faces
    return min(pool, key=lambda f: (abs(f[0] - weight), f[2]))[2]


def resolve(font_spec: str | dict | None, weight: int | None = None) -> tuple[str | None, str | None]:
    """Return (font_path, warning). font_spec: preset name, family name, .ttf path or {'family','weight'}."""
    warn = None
    if isinstance(font_spec, dict):
        weight = weight or font_spec.get("weight")
        font_spec = font_spec.get("family") or font_spec.get("preset")
    spec = (font_spec or "Sans-serif")
    if spec in PRESETS:
        cands, w = PRESETS[spec]
        w = weight or w
        for fam in cands:
            p = path_for(fam, w)
            if p:
                return p, None
    else:
        if Path(spec).is_file():
            return spec, None
        p = path_for(spec, weight or 400)
        if p:
            return p, None
        warn = f"Font '{spec}' not found - used fallback"
    for fam in ("DejaVu Sans", "Arial", "Segoe UI", "FreeSans"):
        p = path_for(fam, weight or 400)
        if p:
            return p, warn
    any_fam = next(iter(font_index().values()), None)
    if any_fam:
        return any_fam[0][2], warn
    return None, (warn or "No fonts found - using Pillow default font")


@lru_cache(maxsize=256)
def load_font(path: str | None, size: int):
    size = max(6, int(size))
    if path:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default(size)
