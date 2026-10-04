"""Visual Template Creator: add/move/resize/rotate text, image, logo, rectangle, circle and
gradient elements, edit their colors/fonts/opacity, and save as a reusable template."""
from __future__ import annotations

import copy

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPen
from PySide6.QtWidgets import (QCheckBox, QColorDialog, QComboBox, QDialog, QDoubleSpinBox, QFileDialog,
                               QFormLayout, QFrame, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QListWidget,
                               QListWidgetItem, QMessageBox, QPushButton, QSlider, QSpinBox, QVBoxLayout, QWidget)

from core.fonts import PRESETS
from core.qimage_util import pil_to_qpixmap
from core.renderer import render_quote
from core.template_engine import blank_template, save_template

PREVIEW_QUOTE = {"text": "Your quote appears like this. Edit elements on the right.", "author": "Author Name"}
CANVAS_PX = 420
NEW_ELEMENT_FACTORIES = {
    "Text": lambda: {"type": "text", "text": "New text", "box": [0.3, 0.45, 0.4, 0.1], "font": "Modern",
                     "color": "#FFFFFF", "align": "center", "valign": "middle", "max_size": 0.06, "min_size": 0.02,
                     "opacity": 1.0, "rotation": 0},
    "Image": lambda: {"type": "image", "path": "", "box": [0.3, 0.3, 0.4, 0.3], "opacity": 1.0, "rotation": 0},
    "Logo": lambda: {"type": "brand", "position": "auto", "scale": 1.0},
    "Rectangle": lambda: {"type": "rect", "box": [0.2, 0.2, 0.6, 0.15], "color": "#FFFFFF", "opacity": 1.0,
                          "radius": 0.0, "rotation": 0},
    "Circle": lambda: {"type": "circle", "box": [0.35, 0.35, 0.3, 0.3], "color": "#FFFFFF", "opacity": 1.0, "rotation": 0},
    "Gradient block": lambda: {"type": "gradient", "box": [0.1, 0.1, 0.8, 0.3], "colors": ["#5B2BFF", "#FF5F6D"],
                               "angle": 90, "opacity": 1.0, "radius": 0.02, "rotation": 0},
}
ELEMENT_LABELS = {"background": "Background", "quote": "Quote text", "author": "Author text", "text": "Custom text",
                  "image": "Image", "brand": "Logo / Brand", "rect": "Rectangle", "circle": "Circle", "gradient": "Gradient"}


class Canvas(QLabel):
    """Shows the rendered template and lets you drag the selected element to move it."""
    element_moved = Signal(float, float)  # dx, dy in 0..1 fractions

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(CANVAS_PX, CANVAS_PX)
        self.setStyleSheet("background:#0c0c10; border-radius: 12px;")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._drag_origin: QPointF | None = None
        self.movable = False

    def mousePressEvent(self, ev: QMouseEvent):
        if self.movable:
            self._drag_origin = ev.position()

    def mouseMoveEvent(self, ev: QMouseEvent):
        if self.movable and self._drag_origin is not None:
            d = ev.position() - self._drag_origin
            self._drag_origin = ev.position()
            self.element_moved.emit(d.x() / CANVAS_PX, d.y() / CANVAS_PX)

    def mouseReleaseEvent(self, ev: QMouseEvent):
        self._drag_origin = None


class ColorBtn(QPushButton):
    changed = Signal(str)

    def __init__(self, color="#FFFFFF"):
        super().__init__()
        self.setFixedSize(34, 26)
        self.set_color(color)
        self.clicked.connect(self._pick)

    def set_color(self, c):
        self._c = c
        self.setStyleSheet(f"background:{c}; border:1px solid #343948; border-radius:6px;")

    def _pick(self):
        c = QColorDialog.getColor(QColor(self._c))
        if c.isValid():
            self.set_color(c.name())
            self.changed.emit(self._c)


class TemplateEditorDialog(QDialog):
    def __init__(self, template: dict | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Template Creator")
        self.resize(980, 640)
        self.template = copy.deepcopy(template) if template else blank_template("New Template")
        if self.template.get("builtin"):
            self.template["id"] = ""
            self.template["name"] += " (copy)"
        self.selected_index = 1 if len(self.template["elements"]) > 1 else 0
        self._build()
        self._refresh_elements_list()
        self._select(self.selected_index)

    # ---------------------------------------------------------------- layout
    def _build(self):
        root = QHBoxLayout(self)

        left = QVBoxLayout()
        left.addWidget(QLabel("Preview — drag to move the selected element", objectName="subtitle"))
        self.canvas = Canvas()
        self.canvas.element_moved.connect(self._on_drag)
        left.addWidget(self.canvas)
        meta = QFormLayout()
        self.name_edit = QLineEdit(self.template["name"])
        self.name_edit.textChanged.connect(self._touch)
        meta.addRow("Template name", self.name_edit)
        self.tags_edit = QLineEdit(", ".join(self.template.get("tags", [])))
        self.tags_edit.setPlaceholderText("e.g. bold, dark, short  (used by Smart template selection)")
        self.tags_edit.textChanged.connect(self._touch)
        meta.addRow("Tags", self.tags_edit)
        left.addLayout(meta)
        btn_row = QHBoxLayout()
        save_btn = QPushButton("SAVE AS TEMPLATE", objectName="primary")
        save_btn.clicked.connect(self._save)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        btn_row.addStretch(1)
        btn_row.addWidget(save_btn)
        left.addLayout(btn_row)
        root.addLayout(left, 1)

        mid = QVBoxLayout()
        mid.addWidget(QLabel("Elements", objectName="h2"))
        add_row = QHBoxLayout()
        self.add_combo = QComboBox()
        self.add_combo.addItems(list(NEW_ELEMENT_FACTORIES.keys()))
        add_btn = QPushButton("+ Add")
        add_btn.clicked.connect(self._add_element)
        add_row.addWidget(self.add_combo, 1)
        add_row.addWidget(add_btn)
        mid.addLayout(add_row)
        self.elements_list = QListWidget()
        self.elements_list.currentRowChanged.connect(self._select)
        mid.addWidget(self.elements_list, 1)
        del_row = QHBoxLayout()
        up_btn, down_btn, del_btn = QPushButton("↑ Forward"), QPushButton("↓ Backward"), QPushButton("Delete", objectName="danger")
        up_btn.clicked.connect(lambda: self._reorder(-1))
        down_btn.clicked.connect(lambda: self._reorder(1))
        del_btn.clicked.connect(self._delete_element)
        del_row.addWidget(up_btn)
        del_row.addWidget(down_btn)
        del_row.addWidget(del_btn)
        mid.addLayout(del_row)
        root.addLayout(mid, 1)

        right = QVBoxLayout()
        right.addWidget(QLabel("Properties", objectName="h2"))
        self.props_container = QVBoxLayout()
        props_widget = QWidget()
        props_widget.setLayout(self.props_container)
        right.addWidget(props_widget)
        right.addStretch(1)
        root.addLayout(right, 1)

    # ---------------------------------------------------------------- elements
    def _touch(self, *_):
        self.template["name"] = self.name_edit.text() or "Untitled"
        self.template["tags"] = [t.strip().lower() for t in self.tags_edit.text().split(",") if t.strip()]
        self._render_preview()

    def _refresh_elements_list(self):
        self.elements_list.blockSignals(True)
        self.elements_list.clear()
        for el in self.template["elements"]:
            label = ELEMENT_LABELS.get(el["type"], el["type"])
            self.elements_list.addItem(QListWidgetItem(label))
        self.elements_list.blockSignals(False)

    def _add_element(self):
        factory = NEW_ELEMENT_FACTORIES[self.add_combo.currentText()]
        el = factory()
        if el["type"] == "image" and not el.get("path"):
            path, _ = QFileDialog.getOpenFileName(self, "Choose image", "", "Images (*.png *.jpg *.jpeg *.webp)")
            if not path:
                return
            el["path"] = path
        self.template["elements"].append(el)
        self._refresh_elements_list()
        self.elements_list.setCurrentRow(len(self.template["elements"]) - 1)

    def _delete_element(self):
        i = self.selected_index
        if 0 <= i < len(self.template["elements"]) and self.template["elements"][i]["type"] != "background":
            del self.template["elements"][i]
            self._refresh_elements_list()
            self.elements_list.setCurrentRow(max(0, i - 1))

    def _reorder(self, delta):
        i = self.selected_index
        j = i + delta
        els = self.template["elements"]
        if 0 <= i < len(els) and 0 <= j < len(els) and els[i]["type"] != "background" and els[j]["type"] != "background":
            els[i], els[j] = els[j], els[i]
            self._refresh_elements_list()
            self.elements_list.setCurrentRow(j)

    def _select(self, index):
        if index < 0 or index >= len(self.template["elements"]):
            return
        self.selected_index = index
        self.canvas.movable = self.template["elements"][index]["type"] != "background"
        self._build_property_form(self.template["elements"][index])
        self._render_preview()

    def _on_drag(self, dx, dy):
        el = self.template["elements"][self.selected_index]
        if "box" in el:
            x, y, w, h = el["box"]
            el["box"] = [min(max(x + dx, -0.5), 1.5 - w), min(max(y + dy, -0.5), 1.5 - h), w, h]
            if hasattr(self, "box_x_spin"):
                self.box_x_spin.blockSignals(True); self.box_x_spin.setValue(el["box"][0]); self.box_x_spin.blockSignals(False)
                self.box_y_spin.blockSignals(True); self.box_y_spin.setValue(el["box"][1]); self.box_y_spin.blockSignals(False)
            self._render_preview()

    # ---------------------------------------------------------------- property form
    def _clear_props(self):
        while self.props_container.count():
            item = self.props_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _frac_spin(self, value, lo=-0.5, hi=1.5):
        s = QDoubleSpinBox()
        s.setRange(lo, hi)
        s.setSingleStep(0.01)
        s.setDecimals(3)
        s.setValue(value)
        return s

    def _build_property_form(self, el):
        self._clear_props()
        form = QFormLayout()
        t = el["type"]
        form.addRow(QLabel(f"Type: {ELEMENT_LABELS.get(t, t)}", objectName="muted"))

        if "box" in el:
            x, y, w, h = el["box"]
            self.box_x_spin, self.box_y_spin = self._frac_spin(x), self._frac_spin(y)
            self.box_w_spin, self.box_h_spin = self._frac_spin(w, 0.02, 1.5), self._frac_spin(h, 0.02, 1.5)
            for label, spin in [("X", self.box_x_spin), ("Y", self.box_y_spin), ("Width", self.box_w_spin), ("Height", self.box_h_spin)]:
                spin.valueChanged.connect(self._on_box_change)
                form.addRow(label, spin)
        if "rotation" in el:
            rot = QSpinBox(); rot.setRange(-180, 180); rot.setValue(int(el.get("rotation", 0)))
            rot.valueChanged.connect(lambda v: self._set(el, "rotation", v))
            form.addRow("Rotation°", rot)
        if "opacity" in el:
            op = QSlider(Qt.Orientation.Horizontal); op.setRange(0, 100); op.setValue(int(el.get("opacity", 1.0) * 100))
            op.valueChanged.connect(lambda v: self._set(el, "opacity", v / 100.0))
            form.addRow("Opacity", op)
        if t == "text":
            txt = QLineEdit(el.get("text", ""))
            txt.textChanged.connect(lambda v: self._set(el, "text", v))
            form.addRow("Text", txt)
        if t in ("text", "quote", "author"):
            font_combo = QComboBox(); font_combo.addItems(list(PRESETS.keys()))
            font_combo.setCurrentText(el.get("font", "Modern"))
            font_combo.currentTextChanged.connect(lambda v: self._set(el, "font", v))
            form.addRow("Font", font_combo)
            align = QComboBox(); align.addItems(["left", "center", "right"])
            align.setCurrentText(el.get("align", "center"))
            align.currentTextChanged.connect(lambda v: self._set(el, "align", v))
            form.addRow("Align", align)
            col = ColorBtn(el.get("color", "#FFFFFF"))
            col.changed.connect(lambda v: self._set(el, "color", v))
            form.addRow("Color", col)
        if t in ("rect", "circle"):
            col = ColorBtn(el.get("color", "#FFFFFF"))
            col.changed.connect(lambda v: self._set(el, "color", v))
            form.addRow("Fill color", col)
            if t == "rect":
                rad = QDoubleSpinBox(); rad.setRange(0, 1); rad.setSingleStep(0.02); rad.setValue(el.get("radius", 0))
                rad.valueChanged.connect(lambda v: self._set(el, "radius", v))
                form.addRow("Corner radius", rad)
        if t == "gradient":
            c1, c2 = (el.get("colors") or ["#5B2BFF", "#FF5F6D"])[:2]
            b1, b2 = ColorBtn(c1), ColorBtn(c2)
            b1.changed.connect(lambda v: self._set(el, "colors", [v, (el.get("colors") or ["#000", "#fff"])[1]]))
            b2.changed.connect(lambda v: self._set(el, "colors", [(el.get("colors") or ["#000", "#fff"])[0], v]))
            row = QHBoxLayout(); row.addWidget(b1); row.addWidget(b2)
            wrap = QWidget(); wrap.setLayout(row)
            form.addRow("Colors", wrap)
            ang = QSpinBox(); ang.setRange(0, 360); ang.setValue(el.get("angle", 90))
            ang.valueChanged.connect(lambda v: self._set(el, "angle", v))
            form.addRow("Angle°", ang)
        if t == "image":
            btn = QPushButton("Choose image…")
            btn.clicked.connect(lambda: self._pick_image(el))
            form.addRow("File", btn)
        if t == "brand":
            note = QLabel("Uses the brand name/logo/colors set in the Style & Brand tab.", objectName="muted")
            note.setWordWrap(True)
            form.addRow(note)
            pos = QComboBox(); pos.addItems(["auto", "top-left", "top-right", "bottom-left", "bottom-right", "bottom-center", "top-center"])
            pos.setCurrentText(el.get("position", "auto"))
            pos.currentTextChanged.connect(lambda v: self._set(el, "position", v))
            form.addRow("Placement override", pos)
        holder = QWidget()
        holder.setLayout(form)
        self.props_container.addWidget(holder)

    def _on_box_change(self, *_):
        el = self.template["elements"][self.selected_index]
        el["box"] = [self.box_x_spin.value(), self.box_y_spin.value(), self.box_w_spin.value(), self.box_h_spin.value()]
        self._render_preview()

    def _set(self, el, key, value):
        el[key] = value
        self._render_preview()

    def _pick_image(self, el):
        path, _ = QFileDialog.getOpenFileName(self, "Choose image", "", "Images (*.png *.jpg *.jpeg *.webp)")
        if path:
            el["path"] = path
            self._render_preview()

    # ---------------------------------------------------------------- preview + save
    def _render_preview(self):
        try:
            img, _ = render_quote(PREVIEW_QUOTE, self.template, {}, (CANVAS_PX * 2, CANVAS_PX * 2), seed=1)
            self.canvas.setPixmap(pil_to_qpixmap(img).scaled(CANVAS_PX, CANVAS_PX, Qt.AspectRatioMode.KeepAspectRatio,
                                                              Qt.TransformationMode.SmoothTransformation))
        except Exception as exc:
            self.canvas.setText(f"Preview error:\n{exc}")

    def _save(self):
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Name required", "Give the template a name first.")
            return
        self.template["name"] = self.name_edit.text().strip()
        save_template(self.template)
        self.accept()
