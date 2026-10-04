"""Style, branding, background and output settings panels."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QColorDialog, QComboBox, QFileDialog, QFormLayout,
                               QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton, QRadioButton, QScrollArea,
                               QSlider, QSpinBox, QVBoxLayout, QWidget)
from PySide6.QtCore import Qt

from core.background_manager import scan_folder
from core.batch_processor import SIZE_PRESETS
from core.fonts import PRESETS, families


class ColorButton(QPushButton):
    changed = Signal(str)

    def __init__(self, color="#FFFFFF", parent=None):
        super().__init__(parent)
        self.setFixedSize(40, 28)
        self.set_color(color)
        self.clicked.connect(self.pick)

    def set_color(self, hexval: str):
        self._color = hexval
        self.setStyleSheet(f"background:{hexval}; border:1px solid #343948; border-radius:6px;")

    def color(self):
        return self._color

    def pick(self):
        c = QColorDialog.getColor(initial=self.palette().color(self.backgroundRole()))
        if c.isValid():
            self.set_color(c.name())
            self.changed.emit(self._color)


def _card(title):
    card = QFrame(objectName="card")
    v = QVBoxLayout(card)
    v.addWidget(QLabel(title, objectName="h2"))
    return card, v


class StylePanel(QWidget):
    """Typography + Branding, in one scrollable panel."""
    changed = Signal()

    def __init__(self, project: dict, parent=None):
        super().__init__(parent)
        self.project = project
        self._build()
        self._load()

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        v = QVBoxLayout(inner)
        v.setSpacing(14)

        # ---- Typography
        card, cv = _card("Typography")
        form = QFormLayout()
        self.font_mode = QComboBox()
        self.font_mode.addItems(["Use each template's own font"] + list(PRESETS.keys()) + ["Custom family…"])
        self.font_mode.currentTextChanged.connect(self._on_font_mode)
        form.addRow("Font style", self.font_mode)
        self.font_family = QComboBox()
        self.font_family.setEditable(True)
        self.font_family.addItems(families())
        self.font_family.setVisible(False)
        form.addRow("", self.font_family)
        self.align = QComboBox()
        self.align.addItems(["Template default", "left", "center", "right"])
        form.addRow("Alignment", self.align)
        self.case = QComboBox()
        self.case.addItems(["none", "upper", "title", "lower"])
        form.addRow("Letter case", self.case)
        self.quote_marks = QCheckBox('Wrap quote text in " marks')
        self.quote_marks.setChecked(True)
        form.addRow("", self.quote_marks)
        cv.addLayout(form)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Size"))
        self.size_slider = self._slider(50, 160, 100)
        row1.addWidget(self.size_slider)
        cv.addLayout(row1)
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Letter spacing"))
        self.tracking_slider = self._slider(0, 30, 0)
        row2.addWidget(self.tracking_slider)
        cv.addLayout(row2)
        row3 = QHBoxLayout()
        row3.addWidget(QLabel("Line spacing"))
        self.leading_slider = self._slider(90, 180, 120)
        row3.addWidget(self.leading_slider)
        cv.addLayout(row3)
        row4 = QHBoxLayout()
        row4.addWidget(QLabel("Text color"))
        self.text_color_btn = ColorButton("#FFFFFF")
        self.text_use_template = QCheckBox("Use template's color")
        self.text_use_template.setChecked(True)
        self.text_use_template.toggled.connect(lambda on: self.text_color_btn.setEnabled(not on))
        self.text_color_btn.setEnabled(False)
        row4.addWidget(self.text_color_btn)
        row4.addWidget(self.text_use_template)
        row4.addStretch(1)
        cv.addLayout(row4)
        row5 = QHBoxLayout()
        row5.addWidget(QLabel("Opacity"))
        self.opacity_slider = self._slider(20, 100, 100)
        row5.addWidget(self.opacity_slider)
        cv.addLayout(row5)
        v.addWidget(card)

        # ---- Branding
        bcard, bv = _card("Branding")
        self.brand_enabled = QCheckBox("Show branding on generated images")
        self.brand_enabled.setChecked(True)
        bv.addWidget(self.brand_enabled)
        bform = QFormLayout()
        self.brand_name = QLineEdit("One More Step")
        bform.addRow("Brand name", self.brand_name)
        colors_row = QHBoxLayout()
        self.word_color_btns = [ColorButton(c) for c in ("#E63946", "#FFFFFF", "#2F6BFF")]
        for b in self.word_color_btns:
            colors_row.addWidget(b)
        colors_row.addWidget(QLabel("(one color per word — set as many as your brand name has words)", objectName="muted"))
        colors_row.addStretch(1)
        bform.addRow("Word colors", colors_row)
        logo_row = QHBoxLayout()
        self.logo_path = QLineEdit()
        self.logo_path.setPlaceholderText("No logo selected (optional)")
        self.logo_path.setReadOnly(True)
        logo_btn = QPushButton("Upload logo (PNG/SVG)…")
        logo_btn.clicked.connect(self._pick_logo)
        clear_logo = QPushButton("Clear")
        clear_logo.clicked.connect(lambda: self.logo_path.setText(""))
        logo_row.addWidget(self.logo_path, 1)
        logo_row.addWidget(logo_btn)
        logo_row.addWidget(clear_logo)
        bform.addRow("Logo", logo_row)
        self.brand_position = QComboBox()
        self.brand_position.addItems(["top-left", "top-right", "bottom-left", "bottom-right", "bottom-center", "top-center"])
        self.brand_position.setCurrentText("bottom-center")
        bform.addRow("Placement", self.brand_position)
        self.brand_font = QComboBox()
        self.brand_font.addItems(list(PRESETS.keys()))
        self.brand_font.setCurrentText("Bold")
        bform.addRow("Brand font", self.brand_font)
        bv.addLayout(bform)
        row6 = QHBoxLayout()
        row6.addWidget(QLabel("Brand opacity"))
        self.brand_opacity_slider = self._slider(10, 100, 90)
        row6.addWidget(self.brand_opacity_slider)
        bv.addLayout(row6)
        v.addWidget(bcard)
        v.addStretch(1)
        scroll.setWidget(inner)
        outer.addWidget(scroll)

        for w in [self.font_mode, self.font_family, self.align, self.case, self.brand_position, self.brand_font]:
            w.currentTextChanged.connect(self.changed.emit)
        for w in [self.quote_marks, self.brand_enabled, self.text_use_template]:
            w.toggled.connect(self.changed.emit)
        for w in [self.size_slider, self.tracking_slider, self.leading_slider, self.opacity_slider, self.brand_opacity_slider]:
            w.valueChanged.connect(self.changed.emit)
        self.brand_name.textChanged.connect(self.changed.emit)
        self.logo_path.textChanged.connect(self.changed.emit)
        self.text_color_btn.changed.connect(lambda *_: self.changed.emit())
        for b in self.word_color_btns:
            b.changed.connect(lambda *_: self.changed.emit())

    def _slider(self, lo, hi, val):
        s = QSlider(Qt.Orientation.Horizontal)
        s.setRange(lo, hi)
        s.setValue(val)
        return s

    def _on_font_mode(self, text):
        self.font_family.setVisible(text == "Custom family…")

    def _pick_logo(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choose logo", "", "Images (*.png *.svg *.webp)")
        if path:
            self.logo_path.setText(path)

    def _load(self):
        t, br = self.project.get("typography", {}), self.project.get("brand", {})
        if t.get("font_preset"):
            self.font_mode.setCurrentText(t["font_preset"])
        if t.get("font_family"):
            self.font_mode.setCurrentText("Custom family…")
            self.font_family.setCurrentText(t["font_family"])
        self.align.setCurrentText(t.get("align") or "Template default")
        self.case.setCurrentText(t.get("case", "none"))
        self.quote_marks.setChecked(t.get("quote_marks", True))
        self.size_slider.setValue(int(t.get("size_pct", 100)))
        self.tracking_slider.setValue(int((t.get("letter_spacing") or 0) * 100))
        self.leading_slider.setValue(int((t.get("line_spacing") or 1.2) * 100))
        self.opacity_slider.setValue(int(t.get("opacity", 100)))
        self.brand_enabled.setChecked(br.get("enabled", True))
        self.brand_name.setText(br.get("name", "One More Step"))
        for b, c in zip(self.word_color_btns, br.get("colors", []) + ["#FFFFFF"] * 3):
            b.set_color(c)
        self.logo_path.setText(br.get("logo", ""))
        self.brand_position.setCurrentText(br.get("position", "bottom-center"))
        self.brand_font.setCurrentText(br.get("font", "Bold"))
        self.brand_opacity_slider.setValue(int(br.get("opacity", 90)))

    def apply_to(self, project: dict):
        mode = self.font_mode.currentText()
        t = {"font_preset": mode if mode in PRESETS else None,
             "font_family": self.font_family.currentText() if mode == "Custom family…" else None,
             "weight": None,
             "align": None if self.align.currentText() == "Template default" else self.align.currentText(),
             "case": self.case.currentText(), "quote_marks": self.quote_marks.isChecked(),
             "size_pct": self.size_slider.value(), "letter_spacing": self.tracking_slider.value() / 100.0,
             "line_spacing": self.leading_slider.value() / 100.0, "opacity": self.opacity_slider.value(),
             "color": None if self.text_use_template.isChecked() else self.text_color_btn.color()}
        project["typography"] = t
        project["brand"] = {"enabled": self.brand_enabled.isChecked(), "name": self.brand_name.text(),
                            "color_mode": "per_word", "colors": [b.color() for b in self.word_color_btns],
                            "logo": self.logo_path.text(), "position": self.brand_position.currentText(),
                            "opacity": self.brand_opacity_slider.value(), "size_pct": 100,
                            "font": self.brand_font.currentText(), "letter_spacing": 0.14, "legibility_pill": True}


class BackgroundPanel(QWidget):
    changed = Signal()

    def __init__(self, project: dict, parent=None):
        super().__init__(parent)
        self.project = project
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        card, cv = _card("Backgrounds")
        cv.addWidget(QLabel("Point to a folder of photos. Sub-folders become categories "
                            "(nature/, city/, ocean/, …). Leave empty to use the template's built-in style.",
                            objectName="subtitle"))
        row = QHBoxLayout()
        self.folder_path = QLineEdit()
        self.folder_path.setReadOnly(True)
        browse = QPushButton("Choose folder…")
        browse.clicked.connect(self._browse)
        clear = QPushButton("Clear")
        clear.clicked.connect(lambda: (self.folder_path.setText(""), self._rescan()))
        row.addWidget(self.folder_path, 1)
        row.addWidget(browse)
        row.addWidget(clear)
        cv.addLayout(row)
        self.summary = QLabel("", objectName="muted")
        cv.addWidget(self.summary)
        form = QFormLayout()
        self.category = QComboBox()
        self.category.addItem("Random (all)")
        form.addRow("Use", self.category)
        cv.addLayout(form)
        v.addWidget(card)
        v.addStretch(1)
        self.folder_path.setText(project.get("background", {}).get("folder", ""))
        self._rescan()
        if project.get("background", {}).get("category"):
            idx = self.category.findText(project["background"]["category"])
            if idx >= 0:
                self.category.setCurrentIndex(idx)
        self.category.currentTextChanged.connect(self.changed.emit)

    def _browse(self):
        path = QFileDialog.getExistingDirectory(self, "Choose backgrounds folder")
        if path:
            self.folder_path.setText(path)
            self._rescan()
            self.changed.emit()

    def _rescan(self):
        folder = self.folder_path.text()
        self.category.blockSignals(True)
        self.category.clear()
        self.category.addItem("Random (all)")
        if folder:
            cats = scan_folder(folder)
            total = sum(len(v) for v in cats.values())
            if total == 0:
                self.summary.setText("No images found in that folder — generated backgrounds will be used instead.")
            else:
                self.summary.setText(f"{total} images across {len(cats)} categor{'y' if len(cats)==1 else 'ies'}.")
                for cat in sorted(cats):
                    self.category.addItem(cat)
        else:
            self.summary.setText("No folder selected — each template will use its own generated background style.")
        self.category.blockSignals(False)

    def apply_to(self, project: dict):
        project["background"] = {"folder": self.folder_path.text(), "mode": "random", "category": self.category.currentText()}


class OutputPanel(QWidget):
    changed = Signal()

    def __init__(self, project: dict, parent=None):
        super().__init__(parent)
        self.project = project
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)

        scard, sv = _card("Image size")
        self.size_group = QButtonGroup(self)
        self.size_buttons = {}
        for label in SIZE_PRESETS:
            rb = QRadioButton(label)
            self.size_group.addButton(rb)
            sv.addWidget(rb)
            self.size_buttons[label] = rb
        custom_row = QHBoxLayout()
        self.custom_rb = QRadioButton("Custom:")
        self.size_group.addButton(self.custom_rb)
        self.custom_w = QSpinBox(); self.custom_w.setRange(200, 6000); self.custom_w.setValue(1080)
        self.custom_h = QSpinBox(); self.custom_h.setRange(200, 6000); self.custom_h.setValue(1080)
        custom_row.addWidget(self.custom_rb)
        custom_row.addWidget(self.custom_w)
        custom_row.addWidget(QLabel("×"))
        custom_row.addWidget(self.custom_h)
        custom_row.addWidget(QLabel("px"))
        custom_row.addStretch(1)
        sv.addLayout(custom_row)
        v.addWidget(scard)

        ocard, ov = _card("Export & organization")
        form = QFormLayout()
        self.out_folder = QLineEdit()
        browse = QPushButton("Choose…")
        browse.clicked.connect(self._browse_out)
        orow = QHBoxLayout()
        orow.addWidget(self.out_folder, 1)
        orow.addWidget(browse)
        form.addRow("Output folder", orow)
        self.date_sub = QCheckBox("Organize into a dated sub-folder (e.g. output/2026-09-29/)")
        self.date_sub.setChecked(True)
        form.addRow("", self.date_sub)
        self.fmt = QComboBox()
        self.fmt.addItems(["PNG", "JPG", "WEBP"])
        form.addRow("Format", self.fmt)
        self.quality = QSlider(Qt.Orientation.Horizontal)
        self.quality.setRange(50, 100)
        self.quality.setValue(92)
        qrow = QHBoxLayout()
        qrow.addWidget(self.quality)
        self.quality_label = QLabel("92")
        self.quality.valueChanged.connect(lambda v: self.quality_label.setText(str(v)))
        qrow.addWidget(self.quality_label)
        form.addRow("Quality (JPG/WEBP)", qrow)
        self.fname_mode = QComboBox()
        self.fname_mode.addItem("Brand + number  (one_more_step_001.png)", "brand")
        self.fname_mode.addItem("From quote text  (keep-going.png)", "quote_text")
        form.addRow("Filenames", self.fname_mode)
        self.brand_slug = QLineEdit("one_more_step")
        form.addRow("Filename prefix", self.brand_slug)
        self.variations = QSpinBox()
        self.variations.setRange(1, 10)
        form.addRow("Variations per quote", self.variations)
        self.save_previews = QCheckBox("Save small JPG previews (previews/)")
        self.save_previews.setChecked(True)
        form.addRow("", self.save_previews)
        self.captions_enabled = QCheckBox("Generate a caption + hashtags .txt for each image (captions/)")
        self.captions_enabled.setChecked(True)
        form.addRow("", self.captions_enabled)
        self.hashtag_count = QSpinBox()
        self.hashtag_count.setRange(0, 20)
        self.hashtag_count.setValue(10)
        form.addRow("Hashtags per caption", self.hashtag_count)
        ov.addLayout(form)
        v.addWidget(ocard)
        v.addStretch(1)

        self._load()
        for w in [self.date_sub, self.fmt, self.fname_mode, self.captions_enabled, self.save_previews]:
            (w.toggled if hasattr(w, "toggled") else w.currentTextChanged).connect(self.changed.emit)
        self.size_group.buttonToggled.connect(lambda *_: self.changed.emit())

    def _browse_out(self):
        path = QFileDialog.getExistingDirectory(self, "Choose output folder")
        if path:
            self.out_folder.setText(path)
            self.changed.emit()

    def _load(self):
        out = self.project.get("output", {})
        size = self.project.get("size", {})
        preset = size.get("preset")
        if preset in self.size_buttons:
            self.size_buttons[preset].setChecked(True)
        else:
            self.custom_rb.setChecked(True)
            self.custom_w.setValue(size.get("width", 1080))
            self.custom_h.setValue(size.get("height", 1080))
        self.out_folder.setText(out.get("folder", ""))
        self.date_sub.setChecked(out.get("date_subfolder", True))
        self.fmt.setCurrentText(out.get("format", "PNG"))
        self.quality.setValue(out.get("quality", 92))
        idx = self.fname_mode.findData(out.get("filename_mode", "brand"))
        if idx >= 0:
            self.fname_mode.setCurrentIndex(idx)
        self.brand_slug.setText(out.get("brand_slug", "one_more_step"))
        self.variations.setValue(out.get("variations", 1))
        self.save_previews.setChecked(out.get("save_previews", True))
        caps = self.project.get("captions", {})
        self.captions_enabled.setChecked(caps.get("enabled", True))
        self.hashtag_count.setValue(caps.get("hashtag_count", 10))

    def current_size(self) -> tuple[int, int]:
        for label, dims in SIZE_PRESETS.items():
            if self.size_buttons[label].isChecked():
                return dims
        return (self.custom_w.value(), self.custom_h.value())

    def apply_to(self, project: dict):
        chosen = next((label for label, rb in self.size_buttons.items() if rb.isChecked()), None)
        w, h = self.current_size()
        project["size"] = {"preset": chosen or "Custom", "width": w, "height": h}
        project["output"] = {"folder": self.out_folder.text(), "format": self.fmt.currentText(),
                             "quality": self.quality.value(), "filename_mode": self.fname_mode.currentData(),
                             "brand_slug": self.brand_slug.text() or "one_more_step",
                             "variations": self.variations.value(), "date_subfolder": self.date_sub.isChecked(),
                             "save_previews": self.save_previews.isChecked()}
        project["captions"] = {"enabled": self.captions_enabled.isChecked(), "hashtag_count": self.hashtag_count.value()}
