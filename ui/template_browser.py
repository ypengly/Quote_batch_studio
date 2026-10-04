"""Template library grid: thumbnails, multi-select, rotation-mode selector, and template
management actions (new / edit / duplicate / delete)."""
from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (QButtonGroup, QFrame, QGridLayout, QHBoxLayout, QLabel, QMessageBox,
                               QPushButton, QRadioButton, QScrollArea, QSizePolicy, QVBoxLayout, QWidget)

from core import template_engine
from core.paths import TEMPLATES_DIR
from core.qimage_util import pil_to_qpixmap
from core.renderer import render_quote

THUMB_QUOTE = {"text": "Your quote appears like this.", "author": "Author Name"}
MODES = [("random", "Random"), ("fixed", "Fixed (first selected)"), ("rotate", "Rotate through selected"),
        ("smart", "Smart (auto-match by quote)")]


class TemplateTile(QFrame):
    clicked = Signal(str)
    edit_requested = Signal(str)
    delete_requested = Signal(str)

    def __init__(self, tpl: dict, parent=None):
        super().__init__(parent, objectName="card")
        self.tpl_id = tpl["id"]
        self.setFixedSize(178, 232)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        v = QVBoxLayout(self)
        v.setContentsMargins(8, 8, 8, 8)
        v.setSpacing(6)
        self.thumb = QLabel(alignment=Qt.AlignmentFlag.AlignCenter)
        self.thumb.setFixedSize(160, 160)
        self.thumb.setStyleSheet("border-radius: 10px; background: #111;")
        self.set_thumbnail(tpl)
        v.addWidget(self.thumb)
        name = QLabel(tpl["name"])
        name.setStyleSheet("font-weight:700; font-size:12px;")
        v.addWidget(name)
        row = QHBoxLayout()
        row.setSpacing(4)
        edit_b = QPushButton("Edit", objectName="iconBtn")
        edit_b.clicked.connect(lambda: self.edit_requested.emit(self.tpl_id))
        row.addWidget(edit_b)
        if tpl.get("builtin"):
            tag = QLabel("built-in", objectName="muted")
            tag.setStyleSheet("font-size:10px;")
            row.addWidget(tag)
        else:
            del_b = QPushButton("Delete", objectName="danger")
            del_b.setFixedHeight(24)
            del_b.clicked.connect(lambda: self.delete_requested.emit(self.tpl_id))
            row.addWidget(del_b)
        v.addLayout(row)
        self._selected = False
        self._apply_style()

    def set_thumbnail(self, tpl):
        try:
            img, _ = render_quote(THUMB_QUOTE, tpl, {}, (320, 320), seed=hash(tpl["id"]) & 0xFFFF)
            self.thumb.setPixmap(pil_to_qpixmap(img).scaled(160, 160, Qt.AspectRatioMode.KeepAspectRatio,
                                                            Qt.TransformationMode.SmoothTransformation))
        except Exception:
            self.thumb.setText("preview\nunavailable")

    def set_selected(self, sel: bool):
        self._selected = sel
        self._apply_style()

    def _apply_style(self):
        border = "2px solid #7C5CFF" if self._selected else "1px solid #343948"
        self.setStyleSheet(f"QFrame#card {{ border: {border}; border-radius: 14px; }}")

    def mousePressEvent(self, ev):
        self.clicked.emit(self.tpl_id)
        super().mousePressEvent(ev)


class TemplateBrowserWidget(QWidget):
    selection_changed = Signal(list, str)  # (selected_ids, mode)
    edit_template = Signal(str)
    new_template = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.templates: dict[str, dict] = {}
        self.tiles: dict[str, TemplateTile] = {}
        self.selected_ids: set[str] = set()
        self.mode = "random"
        self._build()
        self.reload()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(14)

        mode_card = QFrame(objectName="card")
        mv = QVBoxLayout(mode_card)
        top = QHBoxLayout()
        top.addWidget(QLabel("Template rotation", objectName="h2"))
        top.addStretch(1)
        new_b = QPushButton("+ New Template…")
        new_b.clicked.connect(self.new_template.emit)
        top.addWidget(new_b)
        mv.addLayout(top)
        row = QHBoxLayout()
        self.mode_group = QButtonGroup(self)
        for key, label in MODES:
            rb = QRadioButton(label)
            rb.setChecked(key == "random")
            rb.toggled.connect(lambda checked, k=key: checked and self._set_mode(k))
            self.mode_group.addButton(rb)
            row.addWidget(rb)
        row.addStretch(1)
        mv.addLayout(row)
        sel_row = QHBoxLayout()
        self.sel_label = QLabel("All templates selected", objectName="subtitle")
        sel_row.addWidget(self.sel_label)
        sel_row.addStretch(1)
        all_b, none_b = QPushButton("Select all"), QPushButton("Select none")
        all_b.clicked.connect(self.select_all)
        none_b.clicked.connect(self.select_none)
        sel_row.addWidget(all_b)
        sel_row.addWidget(none_b)
        mv.addLayout(sel_row)
        root.addWidget(mode_card)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        self.grid = QGridLayout(inner)
        self.grid.setSpacing(12)
        scroll.setWidget(inner)
        root.addWidget(scroll, 1)

    def _set_mode(self, mode):
        self.mode = mode
        self._emit()

    def reload(self, keep_selection=True):
        self.templates = template_engine.load_templates(TEMPLATES_DIR)
        prev = self.selected_ids if keep_selection else set()
        for i in reversed(range(self.grid.count())):
            self.grid.itemAt(i).widget().setParent(None)
        self.tiles.clear()
        cols = 4
        for i, tpl in enumerate(self.templates.values()):
            tile = TemplateTile(tpl)
            tile.clicked.connect(self.toggle_tile)
            tile.edit_requested.connect(self.edit_template.emit)
            tile.delete_requested.connect(self._delete)
            self.grid.addWidget(tile, i // cols, i % cols)
            self.tiles[tpl["id"]] = tile
        self.selected_ids = {t for t in prev if t in self.templates} or set(self.templates.keys())
        self._refresh_tile_styles()
        self._emit()

    def toggle_tile(self, tpl_id):
        if tpl_id in self.selected_ids and len(self.selected_ids) > 1:
            self.selected_ids.remove(tpl_id)
        else:
            self.selected_ids.add(tpl_id)
        self._refresh_tile_styles()
        self._emit()

    def select_all(self):
        self.selected_ids = set(self.templates.keys())
        self._refresh_tile_styles()
        self._emit()

    def select_none(self):
        if self.templates:
            first = next(iter(self.templates))
            self.selected_ids = {first}
        self._refresh_tile_styles()
        self._emit()

    def _refresh_tile_styles(self):
        for tid, tile in self.tiles.items():
            tile.set_selected(tid in self.selected_ids)
        n = len(self.selected_ids)
        self.sel_label.setText("All templates selected" if n == len(self.templates) else f"{n} template{'s' if n != 1 else ''} selected")

    def _delete(self, tpl_id):
        if QMessageBox.question(self, "Delete template", "Delete this custom template? This can't be undone.") == QMessageBox.StandardButton.Yes:
            template_engine.delete_template(tpl_id, TEMPLATES_DIR)
            self.reload()

    def _emit(self):
        self.selection_changed.emit(sorted(self.selected_ids), self.mode)

    def set_selection(self, ids: list[str], mode: str):
        self.selected_ids = set(ids) or set(self.templates.keys())
        self.mode = mode
        for key, label in MODES:
            pass
        self._refresh_tile_styles()
