"""Smart text fitting: choose the largest font size whose wrapped, balanced text fits a box."""
from __future__ import annotations

from dataclasses import dataclass, field

from .fonts import load_font


@dataclass
class FitResult:
    lines: list[str]
    font: object
    size: int
    line_pitch: float
    letter_spacing: float
    block_w: float
    block_h: float
    warnings: list[str] = field(default_factory=list)


def line_width(font, text: str, spacing: float) -> float:
    if not text:
        return 0.0
    if spacing == 0:
        return font.getlength(text)
    return sum(font.getlength(c) + spacing for c in text) - spacing


def _break_long_word(font, word, max_w, spacing):
    parts, cur = [], ""
    for ch in word:
        if cur and line_width(font, cur + ch, spacing) > max_w:
            parts.append(cur)
            cur = ch
        else:
            cur += ch
    if cur:
        parts.append(cur)
    return parts


def wrap(font, text: str, max_w: float, spacing: float = 0.0, break_words: bool = False) -> list[str] | None:
    """Greedy wrap. Returns None if a single word is wider than max_w (unless break_words)."""
    lines: list[str] = []
    for para in text.split("\n"):
        words = para.split()
        if not words:
            lines.append("")
            continue
        cur = ""
        for w in words:
            if line_width(font, w, spacing) > max_w:
                if not break_words:
                    return None
                pieces = _break_long_word(font, w, max_w, spacing)
                if cur:
                    lines.append(cur)
                lines.extend(pieces[:-1])
                cur = pieces[-1]
                continue
            trial = w if not cur else cur + " " + w
            if line_width(font, trial, spacing) <= max_w:
                cur = trial
            else:
                lines.append(cur)
                cur = w
        lines.append(cur)
    return lines


def balance(font, text: str, max_w: float, spacing: float, n_lines: int) -> list[str]:
    """Shrink the wrap width while keeping the same line count -> even, poster-like line lengths."""
    best = wrap(font, text, max_w, spacing, True)
    if len(best) < 2 or "\n" in text:
        return best
    lo, hi = max_w * 0.35, max_w
    for _ in range(14):
        mid = (lo + hi) / 2
        trial = wrap(font, text, mid, spacing)
        if trial is not None and len(trial) <= n_lines:
            best, hi = trial, mid
        else:
            lo = mid
    return best


def fit_text(text: str, font_path, box_w: float, box_h: float, max_size: int, min_size: int,
             line_spacing: float = 1.2, letter_spacing_em: float = 0.0, floor_ratio: float = 0.6) -> FitResult:
    """Find the biggest size (max_size..min_size) that fits. If even min_size overflows the box,
    keep shrinking down to floor_ratio*min_size and report a warning; last resort hard-breaks words."""
    text = text.strip()
    warnings: list[str] = []

    def attempt(size, break_words=False):
        font = load_font(font_path, size)
        sp = letter_spacing_em * size
        lines = wrap(font, text, box_w, sp, break_words)
        if lines is None:
            return None
        asc, desc = font.getmetrics()
        pitch = size * line_spacing
        h = pitch * (len(lines) - 1) + asc + desc
        w = max((line_width(font, l, sp) for l in lines), default=0)
        return font, sp, lines, pitch, w, h

    def search(lo, hi, break_words=False):
        best = None
        lo, hi = int(lo), int(hi)
        while lo <= hi:
            mid = (lo + hi) // 2
            r = attempt(mid, break_words)
            if r and r[5] <= box_h and r[4] <= box_w:
                best, lo = (mid, r), mid + 1
            else:
                hi = mid - 1
        return best

    found = search(min_size, max_size)
    if not found:
        floor = max(8, int(min_size * floor_ratio))
        found = search(floor, min_size - 1)
        if found:
            warnings.append("Long quote: text is smaller than the preferred minimum size")
    if not found:
        floor = max(8, int(min_size * floor_ratio))
        found = search(floor, min_size, break_words=True) or search(6, floor, break_words=True)
        warnings.append("Very long quote: text shrunk to fit and some words were split")
    if not found:  # absolute last resort
        r = attempt(6, True)
        found = (6, r)
    size, (font, sp, lines, pitch, w, h) = found
    if size < max(min_size * 0.75, 10):
        warnings.append(f"Text size is small ({size}px)")
    lines = balance(font, text, box_w, sp, len(lines))
    asc, desc = font.getmetrics()
    h = pitch * (len(lines) - 1) + asc + desc
    w = max((line_width(font, l, sp) for l in lines), default=0)
    return FitResult(lines, font, size, pitch, sp, w, h, warnings)
