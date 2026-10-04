"""Batch generation: builds a job list, runs it across worker processes, reports progress,
supports pause/resume/cancel, and can resume a run that was interrupted (app crash / closed)."""
from __future__ import annotations

import json
import multiprocessing as mp
import random
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path

from .background_manager import BackgroundPicker
from .captions import generate_caption
from .filenames import build as build_filename
from .filenames import sanitize, unique
from .renderer import render_quote
from .template_engine import TemplateChooser

SIZE_PRESETS = {
    "Instagram / Facebook Post (1080x1080)": (1080, 1080),
    "Portrait (1080x1350)": (1080, 1350),
    "Story / Reel (1080x1920)": (1080, 1920),
    "Facebook Landscape (1200x630)": (1200, 630),
}


@dataclass
class JobItem:
    index: int
    quote: dict
    template_id: str
    seed: int
    variant_label: str | None = None


@dataclass
class BatchPlan:
    items: list[JobItem]
    settings: dict
    size: tuple[int, int]
    templates_by_id: dict
    bg_root: str | None


def build_plan(quotes: list[dict], templates: dict, template_ids: list[str], mode: str, size: tuple[int, int],
              settings: dict, variations: int = 1, seed: int | None = None) -> BatchPlan:
    chosen = [templates[t] for t in template_ids if t in templates] or list(templates.values())
    rng = random.Random(seed)
    chooser = TemplateChooser(chosen, mode, rng)
    items: list[JobItem] = []
    idx = 1
    for q in quotes:
        if not q.get("selected", True):
            continue
        used_this_quote: set[str] = set()
        for v in range(max(1, variations)):
            t = chooser.next(q, exclude=used_this_quote if variations > 1 else None)
            used_this_quote.add(t["id"])
            label = chr(ord("a") + v) if variations > 1 else None
            items.append(JobItem(idx, q, t["id"], rng.randint(0, 2**31), label))
        idx += 1
    return BatchPlan(items, settings, size, templates, settings.get("background", {}).get("folder") or None)


def _render_one(args):
    item, settings, size, template, bg_path, out_dir, date_sub, fmt, quality, fname_mode, brand_slug, save_captions, save_previews, hashtag_count = args
    try:
        img, warnings = render_quote(item.quote, template, settings, size, bg_path, item.seed)
        folder = Path(out_dir) / date_sub if date_sub else Path(out_dir)
        folder.mkdir(parents=True, exist_ok=True)
        base = build_filename(fname_mode, item.index, item.quote, brand_slug, item.variant_label)
        ext = {"PNG": ".png", "JPG": ".jpg", "WEBP": ".webp"}.get(fmt, ".png")
        fname = unique(lambda n: folder / n, base, ext)
        out_path = folder / fname
        save_kwargs = {"quality": quality, "optimize": True} if fmt in ("JPG", "WEBP") else {}
        if fmt == "JPG":
            img = img.convert("RGB")
        img.save(out_path, {"PNG": "PNG", "JPG": "JPEG", "WEBP": "WEBP"}[fmt], **save_kwargs)
        if save_previews:
            pv_dir = folder / "previews"
            pv_dir.mkdir(exist_ok=True)
            pv = img.copy()
            pv.thumbnail((480, 480))
            pv.convert("RGB").save(pv_dir / f"{out_path.stem}_preview.jpg", "JPEG", quality=80)
        if save_captions:
            cap_dir = folder / "captions"
            cap_dir.mkdir(exist_ok=True)
            (cap_dir / f"{out_path.stem}.txt").write_text(
                generate_caption(item.quote, random.Random(item.seed), settings.get("brand", {}).get("name", "")),
                encoding="utf-8")
        return {"ok": True, "index": item.index, "path": str(out_path), "warnings": warnings, "quote_id": item.quote.get("id")}
    except Exception as exc:
        return {"ok": False, "index": item.index, "quote_id": item.quote.get("id"),
                "error": f"{type(exc).__name__}: {exc}", "trace": traceback.format_exc()}


class BatchRun:
    """Runs a BatchPlan with a worker pool; poll() to drain results; supports pause/resume/cancel
    and writing a resumable state file so a killed run can be continued later."""

    def __init__(self, plan: BatchPlan, out_dir: str, workers: int | None = None, state_path: str | None = None):
        self.plan, self.out_dir = plan, out_dir
        self.workers = workers or max(1, min(8, (mp.cpu_count() or 2) - 1))
        self.state_path = Path(state_path) if state_path else Path(out_dir) / ".qbs_run_state.json"
        self.done: dict[int, dict] = {}
        self.failed: list[dict] = []
        self.paused = False
        self.cancelled = False
        self._pool = None
        self._pending = []
        self._started = False

    def _remaining_items(self):
        return [it for it in self.plan.items if it.index not in self.done]

    def _task_args(self, item: JobItem):
        s = self.plan.settings
        out = s.get("output", {})
        bg_path = None
        if self._bg_picker:
            cat = s.get("background", {}).get("category", "Random (all)")
            bg_path = self._bg_picker.pick(cat)
        return (item, s, self.plan.size, self.plan.templates_by_id[item.template_id], bg_path, self.out_dir,
                time.strftime("%Y-%m-%d") if out.get("date_subfolder", True) else "", out.get("format", "PNG"),
                out.get("quality", 92), out.get("filename_mode", "brand"), out.get("brand_slug", "one_more_step"),
                s.get("captions", {}).get("enabled", True), out.get("save_previews", True),
                s.get("captions", {}).get("hashtag_count", 10))

    def start(self):
        self._bg_picker = BackgroundPicker(self.plan.bg_root, random.Random(1)) if self.plan.bg_root else None
        self._pool = mp.Pool(processes=self.workers)
        self._pending = [self._pool.apply_async(_render_one, (self._task_args(it),)) for it in self._remaining_items()]
        self._started = True
        self._save_state()

    def total(self) -> int:
        return len(self.plan.items)

    def completed(self) -> int:
        return len(self.done) + len(self.failed)

    def poll(self) -> list[dict]:
        """Non-blocking: returns newly finished results since the last call."""
        if not self._started or self.paused:
            return []
        finished = [r for r in self._pending if r.ready()]
        self._pending = [r for r in self._pending if not r.ready()]
        results = []
        for r in finished:
            res = r.get()
            results.append(res)
            if res["ok"]:
                self.done[res["index"]] = res
            else:
                self.failed.append(res)
        if results:
            self._save_state()
        return results

    def is_finished(self) -> bool:
        return self._started and not self._pending and not self.paused

    def pause(self):
        self.paused = True

    def resume(self):
        if self.paused:
            self.paused = False

    def cancel(self):
        self.cancelled = True
        if self._pool:
            self._pool.terminate()
        self._save_state()

    def shutdown(self):
        if self._pool:
            self._pool.close()

    def _save_state(self):
        try:
            Path(self.out_dir).mkdir(parents=True, exist_ok=True)
            self.state_path.write_text(json.dumps({
                "total": self.total(), "done_indices": list(self.done), "failed": self.failed,
                "size": self.plan.size, "template_ids": list(self.plan.templates_by_id),
            }), encoding="utf-8")
        except OSError:
            pass

    @staticmethod
    def load_state(out_dir: str) -> dict | None:
        p = Path(out_dir) / ".qbs_run_state.json"
        if p.exists():
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                return None
        return None
