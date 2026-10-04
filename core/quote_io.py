"""Parsing quotes from pasted text, TXT, CSV, JSON; and reading/writing project quote lists."""
from __future__ import annotations

import csv
import json
import re
import uuid
from pathlib import Path


def new_quote(text: str, author: str = "", category: str = "") -> dict:
    return {"id": uuid.uuid4().hex[:8], "text": text.strip(), "author": author.strip(),
            "category": category.strip(), "selected": True}


def parse_pasted_text(raw: str) -> list[dict]:
    """Blank-line-separated paragraphs = quotes. Falls back to one quote per non-empty line
    if there isn't a single blank line anywhere (so single-line-per-quote pastes still work)."""
    raw = raw.replace("\r\n", "\n").replace("\r", "\n")
    if "\n\n" in raw.strip():
        chunks = re.split(r"\n\s*\n", raw.strip())
    else:
        chunks = raw.strip().split("\n")
    return [new_quote(c.strip()) for c in chunks if c.strip()]


def parse_txt_file(path: str | Path) -> list[dict]:
    return parse_pasted_text(Path(path).read_text(encoding="utf-8-sig", errors="replace"))


def parse_csv_file(path: str | Path) -> list[dict]:
    quotes = []
    with open(path, newline="", encoding="utf-8-sig", errors="replace") as f:
        sample = f.read(4096)
        f.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        except csv.Error:
            dialect = csv.excel
        reader = csv.DictReader(f, dialect=dialect)
        if not reader.fieldnames:
            raise ValueError("CSV file has no header row")
        cols = {c.lower().strip(): c for c in reader.fieldnames}
        qcol = cols.get("quote") or cols.get("text") or reader.fieldnames[0]
        acol = cols.get("author")
        ccol = cols.get("category") or cols.get("tag")
        for row in reader:
            text = (row.get(qcol) or "").strip()
            if text:
                quotes.append(new_quote(text, row.get(acol, "") if acol else "", row.get(ccol, "") if ccol else ""))
    if not quotes:
        raise ValueError("No quotes found in CSV (expected a 'quote' column)")
    return quotes


def parse_json_file(path: str | Path) -> list[dict]:
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    items = data.get("quotes", data) if isinstance(data, dict) else data
    if not isinstance(items, list):
        raise ValueError("JSON must be a list of quotes, or {\"quotes\": [...]}")
    out = []
    for it in items:
        if isinstance(it, str):
            out.append(new_quote(it))
        elif isinstance(it, dict):
            out.append(new_quote(it.get("text") or it.get("quote", ""), it.get("author", ""), it.get("category", "")))
    return [q for q in out if q["text"]]


def load_file(path: str | Path) -> list[dict]:
    ext = Path(path).suffix.lower()
    if ext == ".csv":
        return parse_csv_file(path)
    if ext == ".json":
        return parse_json_file(path)
    if ext == ".txt":
        return parse_txt_file(path)
    raise ValueError(f"Unsupported file type: {ext} (use .txt, .csv, or .json)")


def export_json(quotes: list[dict], path: str | Path) -> None:
    Path(path).write_text(json.dumps(quotes, indent=2, ensure_ascii=False), encoding="utf-8")


def export_csv(quotes: list[dict], path: str | Path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["text", "author", "category"])
        w.writeheader()
        for q in quotes:
            w.writerow({"text": q.get("text", ""), "author": q.get("author", ""), "category": q.get("category", "")})
