"""Background images: scanning folders/categories, cover-fitting, and procedural fallbacks."""
from __future__ import annotations

import random
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps

IMG_EXT = {".jpg", ".jpeg", ".png", ".webp"}
PROCEDURAL_KINDS = ["nature", "sunset", "mountains", "ocean", "city", "abstract", "dark"]


def scan_folder(root: str | Path) -> dict[str, list[str]]:
    """Return {category: [image paths]}. Sub-folders are categories; loose images go to 'general'."""
    root = Path(root)
    cats: dict[str, list[str]] = {}
    if not root.is_dir():
        return cats
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.suffix.lower() in IMG_EXT:
            rel = p.relative_to(root)
            cat = rel.parts[0].lower() if len(rel.parts) > 1 else "general"
            cats.setdefault(cat, []).append(str(p))
    return cats


class BackgroundPicker:
    """Shuffle-bag picker: every image is used once before any repeats."""

    def __init__(self, root: str | Path, rng: random.Random):
        self.cats = scan_folder(root)
        self.rng = rng
        self.bags: dict[str, list[str]] = {}

    def categories(self) -> list[str]:
        return sorted(self.cats)

    def has_images(self, category: str | None = None) -> bool:
        return bool(self._pool(category))

    def _pool(self, category):
        if category and category not in ("", "Random (all)"):
            return self.cats.get(category.lower(), [])
        return [p for v in self.cats.values() for p in v]

    def pick(self, category: str | None = None) -> str | None:
        pool = self._pool(category)
        if not pool:
            return None
        key = (category or "*").lower()
        bag = self.bags.get(key)
        if not bag:
            bag = pool[:]
            self.rng.shuffle(bag)
            self.bags[key] = bag
        return bag.pop()


def cover_fit(img: Image.Image, w: int, h: int) -> Image.Image:
    scale = max(w / img.width, h / img.height)
    nw, nh = max(1, round(img.width * scale)), max(1, round(img.height * scale))
    img = img.resize((nw, nh), Image.LANCZOS if scale < 1 else Image.BICUBIC)
    left, top = (nw - w) // 2, (nh - h) // 2
    return img.crop((left, top, left + w, top + h))


def load_background(path: str, w: int, h: int) -> Image.Image:
    """Raises on corrupt / unsupported files - the caller decides how to recover."""
    with Image.open(path) as im:
        im = ImageOps.exif_transpose(im)
        im = im.convert("RGB")
        if im.width > w * 2 and im.height > h * 2:  # pre-shrink huge photos
            im.thumbnail((w * 2, h * 2), Image.LANCZOS)
        return cover_fit(im, w, h)


# ---------------------------------------------------------------- procedural backgrounds
def _vgrad(w, h, stops):
    ys = np.linspace(0, 1, h)
    pos = [s[0] for s in stops]
    chans = [np.interp(ys, pos, [s[1][c] for s in stops]) for c in range(3)]
    col = np.stack(chans, axis=1)[:, None, :]
    return np.broadcast_to(col, (h, w, 3)).copy()


def _ridge(w, h, base, amp, rng, rough=1.6):
    x = np.linspace(0, 1, w)
    y = np.zeros(w)
    for o in range(1, 7):
        y += rng.uniform(0.6, 1.0) * np.sin(2 * np.pi * x * o * rng.uniform(0.7, 1.4) + rng.uniform(0, 6.28)) / (o ** rough)
    y = (y - y.min()) / (np.ptp(y) + 1e-9)
    return (base + amp * (y - 0.5)) * h


def _layer(arr, ridge, color, haze=0.0, haze_color=(255, 255, 255)):
    h, w = arr.shape[:2]
    yy = np.arange(h)[:, None]
    mask = yy >= ridge[None, :]
    depth = np.clip((yy - ridge[None, :]) / (h * 0.35), 0, 1)[..., None]
    col = np.array(color, float)
    fill = col * (1 - 0.25 * depth) * (1 - haze) + np.array(haze_color, float) * haze
    arr[mask] = np.broadcast_to(fill, arr.shape)[mask]


def _glow(arr, cx, cy, r, color, strength=1.0):
    h, w = arr.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / r
    a = np.clip(1 - d, 0, 1) ** 2 * strength
    arr[:] = arr * (1 - a[..., None]) + np.array(color, float) * a[..., None]


def procedural_background(kind: str, w: int, h: int, seed: int = 0) -> Image.Image:
    rng = np.random.default_rng(seed)
    kind = kind if kind in PROCEDURAL_KINDS else "nature"
    if kind == "nature":
        arr = _vgrad(w, h, [(0, (120, 175, 225)), (0.55, (215, 235, 245)), (1, (240, 245, 230))])
        _glow(arr, w * rng.uniform(0.2, 0.8), h * 0.25, w * 0.5, (255, 250, 220), 0.7)
        for i, (base, col) in enumerate([(0.55, (110, 150, 120)), (0.65, (70, 120, 80)), (0.76, (40, 90, 55)), (0.88, (22, 60, 38))]):
            _layer(arr, _ridge(w, h, base, 0.12, rng), col, haze=0.25 * (3 - i) / 3, haze_color=(220, 235, 240))
    elif kind == "mountains":
        arr = _vgrad(w, h, [(0, (30, 45, 85)), (0.5, (120, 140, 175)), (1, (220, 205, 200))])
        for i, (base, col) in enumerate([(0.5, (95, 105, 140)), (0.62, (65, 75, 110)), (0.75, (40, 48, 78)), (0.9, (18, 22, 40))]):
            _layer(arr, _ridge(w, h, base, 0.28, rng, 1.1), col, haze=0.3 * (3 - i) / 3, haze_color=(210, 200, 215))
    elif kind == "sunset":
        arr = _vgrad(w, h, [(0, (40, 30, 90)), (0.35, (200, 70, 110)), (0.6, (250, 160, 80)), (1, (255, 214, 140))])
        _glow(arr, w * rng.uniform(0.3, 0.7), h * 0.62, w * 0.6, (255, 230, 150), 0.9)
        for base, col in [(0.72, (80, 40, 80)), (0.84, (40, 20, 50)), (0.94, (16, 8, 26))]:
            _layer(arr, _ridge(w, h, base, 0.08, rng), col)
    elif kind == "ocean":
        hor = 0.55
        arr = _vgrad(w, h, [(0, (25, 60, 120)), (hor - 0.001, (170, 210, 235)), (hor, (30, 110, 160)), (1, (5, 30, 70))])
        yy = np.arange(h)[:, None]
        waves = np.sin(yy * 0.07 + np.arange(w)[None, :] * 0.004 * rng.uniform(1, 3)) * (yy > h * hor)
        arr += waves[..., None] * 10
        _glow(arr, w * 0.5, h * hor, w * 0.4, (255, 245, 220), 0.5)
    elif kind == "city":
        arr = _vgrad(w, h, [(0, (10, 12, 35)), (0.6, (70, 50, 110)), (1, (230, 120, 110))])
        img = Image.fromarray(np.clip(arr, 0, 255).astype("uint8"))
        d = ImageDraw.Draw(img)
        x = 0
        while x < w:
            bw = int(rng.integers(w // 22, w // 8))
            bh = int(rng.integers(int(h * 0.12), int(h * 0.42)))
            d.rectangle([x, h - bh, x + bw, h], fill=(12, 12, 24))
            for wy in range(h - bh + 20, h - 10, 34):
                for wx in range(x + 12, x + bw - 12, 26):
                    if rng.random() < 0.28:
                        d.rectangle([wx, wy, wx + 9, wy + 14], fill=(255, 214, 120))
            x += bw + int(rng.integers(0, 8))
        arr = np.asarray(img, float)
    elif kind == "abstract":
        img = Image.new("RGB", (w, h), tuple(int(v) for v in rng.integers(20, 90, 3)))
        d = ImageDraw.Draw(img)
        for _ in range(9):
            r = int(rng.integers(w // 5, w // 2))
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=tuple(int(v) for v in rng.integers(40, 255, 3)))
        img = img.filter(ImageFilter.GaussianBlur(w // 7))
        arr = np.asarray(img, float)
    else:  # dark
        arr = _vgrad(w, h, [(0, (8, 8, 14)), (1, (24, 24, 36))])
        _glow(arr, w * rng.uniform(0.2, 0.8), h * rng.uniform(0.2, 0.8), w * 0.7, (60, 70, 110), 0.5)
    arr = arr + rng.normal(0, 3.0, arr.shape[:2])[..., None]  # subtle film grain
    return Image.fromarray(np.clip(arr, 0, 255).astype("uint8"), "RGB")


def generate_samples(dest: str | Path, per_category: int = 4, size=(1440, 2160)) -> int:
    """Write procedural sample photos into dest/<category>/ so the app works out of the box."""
    dest = Path(dest)
    n = 0
    for kind in PROCEDURAL_KINDS:
        folder = dest / kind
        folder.mkdir(parents=True, exist_ok=True)
        for i in range(per_category):
            f = folder / f"sample_{kind}_{i + 1:02d}.jpg"
            if not f.exists():
                procedural_background(kind, size[0], size[1], seed=i * 97 + sum(map(ord, kind))).save(f, quality=90)
                n += 1
    return n
