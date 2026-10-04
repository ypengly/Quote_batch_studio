"""Save/load .qbsproj project files (JSON) holding quotes, templates-in-use, branding, output settings, etc."""
from __future__ import annotations

import json
from pathlib import Path

SCHEMA_VERSION = 1
EXT = ".qbsproj"


def default_project(name: str = "Untitled Project") -> dict:
    return {
        "schema_version": SCHEMA_VERSION, "name": name, "quotes": [],
        "template_ids": [], "template_mode": "random",
        "typography": {"font_preset": None, "font_family": None, "weight": None, "size_pct": 100,
                       "letter_spacing": None, "line_spacing": None, "align": None, "color": None,
                       "opacity": 100, "case": "none", "quote_marks": True},
        "brand": {"enabled": True, "name": "One More Step", "color_mode": "per_word",
                  "colors": ["#E63946", "#FFFFFF", "#2F6BFF"], "logo": "", "position": "bottom-center",
                  "opacity": 90, "size_pct": 100, "font": "Bold", "letter_spacing": 0.14, "legibility_pill": True},
        "size": {"preset": "Instagram Post (1080x1080)", "width": 1080, "height": 1080},
        "background": {"folder": "", "mode": "random", "category": "Random (all)"},
        "captions": {"enabled": True, "hashtag_count": 10},
        "output": {"folder": "", "format": "PNG", "quality": 92, "filename_mode": "brand", "brand_slug": "one_more_step",
                  "variations": 1, "date_subfolder": True, "save_previews": True},
        "show_author": True,
    }


def save_project(project: dict, path: str | Path) -> Path:
    path = Path(path)
    if path.suffix.lower() != EXT:
        path = path.with_suffix(EXT)
    project = dict(project)
    project["schema_version"] = SCHEMA_VERSION
    path.write_text(json.dumps(project, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def load_project(path: str | Path) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    merged = default_project(data.get("name", "Untitled Project"))
    for k, v in data.items():
        if isinstance(v, dict) and isinstance(merged.get(k), dict):
            merged[k].update(v)
        else:
            merged[k] = v
    return merged


def list_projects(folder: str | Path) -> list[Path]:
    folder = Path(folder)
    return sorted(folder.glob(f"*{EXT}")) if folder.is_dir() else []
