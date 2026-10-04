"""Live preview panel: renders the currently focused quote with the current settings."""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import QFrame, QLabel, QSizePolicy, QVBoxLayout, QWidget

from core.qimage_util import pil_to_qpixmap
from core.renderer import render_quote


class PreviewPanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent, objectName="card")
        self.setMinimumWidth(300)
        v = QVBoxLayout(self)
        v.addWidget(QLabel("Live preview", objectName="h2"))
        self.image_label = QLabel(alignment=Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumSize(260, 260)
        self.image_label.setStyleSheet("background:#0c0c10; border-radius: 12px;")
        self.image_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        v.addWidget(self.image_label, 1)
        self.info_label = QLabel("", objectName="subtitle")
        self.info_label.setWordWrap(True)
        v.addWidget(self.info_label)

        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(180)
        self._debounce.timeout.connect(self._render_now)
        self._pending = None
        self._last_pixmap_src = None

    def request(self, quote: dict | None, template: dict | None, settings: dict, size: tuple[int, int]):
        if not quote or not template:
            self.image_label.setText("Select a quote and a template\nto see a preview here.")
            self.image_label.setPixmap(self._blank())
            self.info_label.setText("")
            return
        self._pending = (quote, template, settings, size)
        self._debounce.start()

    def _blank(self):
        from PySide6.QtGui import QPixmap
        return QPixmap()

    def _render_now(self):
        if not self._pending:
            return
        quote, template, settings, size = self._pending
        try:
            img, warnings = render_quote(quote, template, settings, size, seed=hash(quote.get("id", "")) & 0xFFFF)
            self._last_pixmap_src = pil_to_qpixmap(img)
            self._rescale()
            self.info_label.setText(f"Template: {template.get('name','?')}   ·   {size[0]}×{size[1]}px" +
                                    ("\n⚠ " + "; ".join(warnings) if warnings else ""))
        except Exception as exc:
            self.image_label.setText(f"Preview error:\n{exc}")

    def _rescale(self):
        if self._last_pixmap_src is None:
            return
        target = self.image_label.size()
        self.image_label.setPixmap(self._last_pixmap_src.scaled(
            max(50, target.width() - 4), max(50, target.height() - 4),
            Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        self._rescale()
