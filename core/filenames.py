"""Filename generation and sanitizing."""
from __future__ import annotations

import re
import unicodedata

STOPWORDS = {"a", "an", "the", "is", "are", "am", "to", "of", "in", "on", "and", "or", "but", "it", "you",
             "your", "my", "i", "that", "this", "for", "with", "be", "if", "so", "at", "as", "s", "t"}


def sanitize(name: str, max_len: int = 60) -> str:
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    name = re.sub(r"[^A-Za-z0-9\- ]+", "", name).strip().lower()
    name = re.sub(r"[\s_]+", "-", name).strip("-")
    return (name[:max_len].rsplit("-", 1)[0] if len(name) > max_len else name) or "quote"


def from_quote_text(text: str, max_words: int = 6) -> str:
    words = re.findall(r"[A-Za-z']+", text.lower())
    kept = [w for w in words if w not in STOPWORDS] or words
    return sanitize("-".join(kept[:max_words]))


def build(mode: str, index: int, quote: dict, brand_slug: str = "one_more_step", variant: str | None = None) -> str:
    idx = f"{index:03d}"
    if mode == "quote_text":
        base = from_quote_text(quote.get("text", "")) or f"quote-{idx}"
    else:
        base = f"{brand_slug}_{idx}" if mode != "quote_text" else base
        base = f"{brand_slug}_{idx}"
    if variant:
        base += f"_{variant}"
    return base


def unique(path_factory, name: str, ext: str) -> str:
    """path_factory(filename) -> Path; appends -2, -3, ... until the path doesn't exist."""
    candidate = f"{name}{ext}"
    n = 2
    while path_factory(candidate).exists():
        candidate = f"{name}-{n}{ext}"
        n += 1
    return candidate
