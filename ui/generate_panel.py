"""Bulk generation: GENERATE ALL button, progress bar, pause/resume/cancel, results summary."""
from __future__ import annotations

import os
import subprocess
import sys
import time

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import (QFileDialog, QFrame, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
                               QMessageBox, QProgressBar, QPushButton, QVBoxLayout, QWidget)

from core.batch_processor import BatchRun, build_plan


class GeneratePanel(QWidget):
    generation_finished = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.run: BatchRun | None = None
        self.timer = QTimer(self)
        self.timer.setInterval(120)
        self.timer.timeout.connect(self._tick)
        self._t_start = 0.0
        self._build()

    def _build(self):
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(14)

        card = QFrame(objectName="card")
        cv = QVBoxLayout(card)
        cv.addWidget(QLabel("Generate", objectName="h2"))
        self.summary_label = QLabel("Add some quotes and pick templates to get started.", objectName="subtitle")
        self.summary_label.setWordWrap(True)
        cv.addWidget(self.summary_label)

        btn_row = QHBoxLayout()
        self.go_btn = QPushButton("🚀  GENERATE ALL", objectName="primary")
        self.go_btn.clicked.connect(self.start)
        btn_row.addWidget(self.go_btn, 1)
        self.pause_btn = QPushButton("⏸ Pause")
        self.pause_btn.clicked.connect(self.toggle_pause)
        self.pause_btn.setEnabled(False)
        self.cancel_btn = QPushButton("✕ Cancel", objectName="danger")
        self.cancel_btn.clicked.connect(self.cancel)
        self.cancel_btn.setEnabled(False)
        btn_row.addWidget(self.pause_btn)
        btn_row.addWidget(self.cancel_btn)
        cv.addLayout(btn_row)

        self.progress = QProgressBar()
        self.progress.setValue(0)
        cv.addWidget(self.progress)
        self.status_label = QLabel("", objectName="muted")
        cv.addWidget(self.status_label)
        v.addWidget(card)

        results_card = QFrame(objectName="card")
        rv = QVBoxLayout(results_card)
        rv.addWidget(QLabel("Results", objectName="h2"))
        self.results_label = QLabel("Nothing generated yet.", objectName="subtitle")
        rv.addWidget(self.results_label)
        self.failed_list = QListWidget()
        self.failed_list.setMaximumHeight(140)
        self.failed_list.setVisible(False)
        rv.addWidget(self.failed_list)
        actions = QHBoxLayout()
        self.open_output_btn = QPushButton("Open output folder →")
        self.open_output_btn.clicked.connect(self._open_output)
        self.open_output_btn.setEnabled(False)
        actions.addWidget(self.open_output_btn)
        actions.addStretch(1)
        rv.addLayout(actions)
        v.addWidget(results_card)
        v.addStretch(1)

    def set_context(self, quotes, templates, template_ids, mode, size, project):
        self._quotes, self._templates, self._template_ids = quotes, templates, template_ids
        self._mode, self._size, self._project = mode, size, project
        n_q = sum(1 for q in quotes if q.get("selected", True))
        n_t = len(template_ids) or len(templates)
        var = project.get("output", {}).get("variations", 1)
        total = n_q * var
        self.summary_label.setText(f"{n_q} quote{'s' if n_q != 1 else ''} selected · {n_t} template"
                                    f"{'s' if n_t != 1 else ''} · {var} variation{'s' if var != 1 else ''} each "
                                    f"→ {total} image{'s' if total != 1 else ''} will be generated.")
        self.go_btn.setEnabled(total > 0 and bool(project.get("output", {}).get("folder")))
        if total > 0 and not project.get("output", {}).get("folder"):
            self.summary_label.setText(self.summary_label.text() + "\n⚠ Choose an output folder in the Output tab first.")

    def start(self):
        out_dir = self._project.get("output", {}).get("folder")
        if not out_dir:
            QMessageBox.warning(self, "No output folder", "Choose an output folder in the Output tab first.")
            return
        os.makedirs(out_dir, exist_ok=True)
        plan = build_plan(self._quotes, self._templates, self._template_ids, self._mode, self._size,
                          self._project, variations=self._project.get("output", {}).get("variations", 1))
        if not plan.items:
            QMessageBox.information(self, "Nothing to generate", "Select at least one quote and one template.")
            return
        self.run = BatchRun(plan, out_dir)
        self.run.start()
        self._t_start = time.time()
        self.progress.setMaximum(self.run.total())
        self.progress.setValue(0)
        self.go_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.pause_btn.setText("⏸ Pause")
        self.cancel_btn.setEnabled(True)
        self.failed_list.setVisible(False)
        self.failed_list.clear()
        self.results_label.setText("Generating…")
        self.open_output_btn.setEnabled(False)
        self.timer.start()

    def toggle_pause(self):
        if not self.run:
            return
        if self.run.paused:
            self.run.resume()
            self.pause_btn.setText("⏸ Pause")
        else:
            self.run.pause()
            self.pause_btn.setText("▶ Resume")

    def cancel(self):
        if self.run:
            self.run.cancel()
        self.timer.stop()
        self._finish(cancelled=True)

    def _tick(self):
        if not self.run:
            return
        results = self.run.poll()
        for r in results:
            if not r["ok"]:
                item = QListWidgetItem(f"Quote #{r['index']}: {r['error']}")
                self.failed_list.addItem(item)
        done = self.run.completed()
        self.progress.setValue(done)
        total = self.run.total()
        elapsed = time.time() - self._t_start
        rate = done / elapsed if elapsed > 0 and done else 0
        remain = (total - done) / rate if rate else 0
        mm, ss = divmod(int(remain), 60)
        state = "Paused" if self.run.paused else "Generating…"
        self.status_label.setText(f"{state}   {done} / {total} images   ·   estimated remaining: {mm:02d}:{ss:02d}")
        if self.run.is_finished():
            self.timer.stop()
            self._finish()

    def _finish(self, cancelled=False):
        if not self.run:
            return
        ok, failed = self.run.completed() - len(self.run.failed), len(self.run.failed)
        self.run.shutdown()
        self.go_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.cancel_btn.setEnabled(False)
        self.open_output_btn.setEnabled(ok > 0)
        if cancelled:
            self.results_label.setText(f"Cancelled — {ok} image{'s' if ok != 1 else ''} saved before stopping.")
        else:
            self.results_label.setText(f"Generation complete!\n{ok} successful\n{failed} failed")
            self.failed_list.setVisible(failed > 0)
        self.generation_finished.emit()

    def _open_output(self):
        folder = self._project.get("output", {}).get("folder", "")
        if not folder:
            return
        try:
            if sys.platform.startswith("win"):
                os.startfile(folder)  # noqa
            elif sys.platform == "darwin":
                subprocess.Popen(["open", folder])
            else:
                subprocess.Popen(["xdg-open", folder])
        except Exception:
            QMessageBox.information(self, "Output folder", folder)
