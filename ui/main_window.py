"""Main application window: navigation between Quotes / Templates / Style & Brand /
Backgrounds / Output / Generate, a persistent live-preview sidebar, and the project menu."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QFileDialog, QFrame, QHBoxLayout, QLabel, QMainWindow, QMessageBox,
                               QPushButton, QStackedWidget, QVBoxLayout, QWidget)

from core import project_manager
from core.paths import PROJECTS_DIR, TEMPLATES_DIR, ensure_user_dirs
from core.template_engine import load_templates
from ui.generate_panel import GeneratePanel
from ui.preview import PreviewPanel
from ui.quote_editor import QuoteEditorWidget
from ui.settings import BackgroundPanel, OutputPanel, StylePanel
from ui.template_browser import TemplateBrowserWidget
from ui.template_editor import TemplateEditorDialog

NAV_ITEMS = [("quotes", "📝  Quotes"), ("templates", "🎨  Templates"), ("style", "✍️  Style & Brand"),
            ("backgrounds", "🖼️  Backgrounds"), ("output", "📦  Output & Export"), ("generate", "🚀  Generate")]


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        ensure_user_dirs()
        self.setWindowTitle("QuoteBatch Studio")
        self.resize(1360, 860)
        self.project = project_manager.default_project()
        self.current_project_path: Path | None = None
        self.templates = load_templates(TEMPLATES_DIR)
        self.selected_template_ids = list(self.templates.keys())
        self.template_mode = "random"

        self._build()
        self._wire()
        self._reload_all_settings_panels_from_project()
        self._update_preview()

    # ---------------------------------------------------------------- layout
    def _build(self):
        root = QWidget(objectName="root")
        self.setCentralWidget(root)
        outer = QHBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        nav = QFrame(objectName="navbar")
        nav.setFixedWidth(220)
        nv = QVBoxLayout(nav)
        nv.setContentsMargins(16, 20, 16, 20)
        nv.setSpacing(4)
        title = QLabel("QuoteBatch\nStudio", objectName="h1")
        nv.addWidget(title)
        subtitle = QLabel("Turn your quotes into\nbeautiful posts — in bulk.", objectName="subtitle")
        subtitle.setWordWrap(True)
        nv.addWidget(subtitle)
        nv.addSpacing(16)
        self.nav_buttons = {}
        for key, label in NAV_ITEMS:
            b = QPushButton(label, objectName="nav")
            b.setCheckable(True)
            b.clicked.connect(lambda _, k=key: self.go_to(k))
            nv.addWidget(b)
            self.nav_buttons[key] = b
        nv.addStretch(1)
        for label, slot in [("New Project", self.new_project), ("Open Project…", self.open_project),
                            ("Save Project", self.save_project), ("Save Project As…", self.save_project_as)]:
            b = QPushButton(label)
            b.clicked.connect(slot)
            nv.addWidget(b)
        self.project_label = QLabel("Untitled Project", objectName="muted")
        self.project_label.setWordWrap(True)
        nv.addWidget(self.project_label)
        outer.addWidget(nav)

        center = QWidget()
        cv = QVBoxLayout(center)
        cv.setContentsMargins(24, 24, 24, 24)
        self.stack = QStackedWidget()
        self.quote_editor = QuoteEditorWidget()
        self.template_browser = TemplateBrowserWidget()
        self.style_panel = StylePanel(self.project)
        self.background_panel = BackgroundPanel(self.project)
        self.output_panel = OutputPanel(self.project)
        self.generate_panel = GeneratePanel()
        for w in [self.quote_editor, self.template_browser, self.style_panel, self.background_panel,
                 self.output_panel, self.generate_panel]:
            self.stack.addWidget(w)
        cv.addWidget(self.stack)
        outer.addWidget(center, 1)

        right = QWidget()
        right.setFixedWidth(340)
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 24, 24, 24)
        self.preview_panel = PreviewPanel()
        rv.addWidget(self.preview_panel, 1)
        outer.addWidget(right)

        self.go_to("quotes")
        self.statusBar().showMessage("Ready.")

    def go_to(self, key):
        for k, b in self.nav_buttons.items():
            b.setChecked(k == key)
            b.setObjectName("navActive" if k == key else "nav")
            b.style().unpolish(b)
            b.style().polish(b)
        idx = [k for k, _ in NAV_ITEMS].index(key)
        self.stack.setCurrentIndex(idx)
        if key == "generate":
            self._sync_generate_context()

    # ---------------------------------------------------------------- wiring
    def _wire(self):
        self.quote_editor.quotes_changed.connect(self._on_quotes_changed)
        self.quote_editor.selection_changed.connect(self._update_preview)
        self.template_browser.selection_changed.connect(self._on_template_selection)
        self.template_browser.edit_template.connect(self._edit_template)
        self.template_browser.new_template.connect(self._new_template)
        self.style_panel.changed.connect(self._update_preview)
        self.background_panel.changed.connect(self._on_settings_touched)
        self.output_panel.changed.connect(self._on_settings_touched)
        self.generate_panel.generation_finished.connect(lambda: self.statusBar().showMessage("Generation finished.", 5000))

    def _on_quotes_changed(self):
        self._update_preview()

    def _on_template_selection(self, ids, mode):
        self.selected_template_ids = ids
        self.template_mode = mode
        self._update_preview()

    def _on_settings_touched(self):
        self.background_panel.apply_to(self.project)
        self.output_panel.apply_to(self.project)

    def _current_quote(self):
        row = self.quote_editor.selected_row()
        if row is not None and row < len(self.quote_editor.quotes):
            return self.quote_editor.quotes[row]
        return self.quote_editor.quotes[0] if self.quote_editor.quotes else None

    def _current_template(self):
        if self.selected_template_ids:
            return self.templates.get(self.selected_template_ids[0])
        return next(iter(self.templates.values()), None)

    def _update_preview(self, *_):
        self.style_panel.apply_to(self.project)
        self.background_panel.apply_to(self.project)
        self.output_panel.apply_to(self.project)
        quote = self._current_quote()
        template = self._current_template()
        size = self.output_panel.current_size()
        self.preview_panel.request(quote, template, self.project, size)

    def _sync_generate_context(self):
        self.style_panel.apply_to(self.project)
        self.background_panel.apply_to(self.project)
        self.output_panel.apply_to(self.project)
        size = self.output_panel.current_size()
        self.generate_panel.set_context(self.quote_editor.quotes, self.templates, self.selected_template_ids,
                                        self.template_mode, size, self.project)

    # ---------------------------------------------------------------- templates
    def _new_template(self):
        dlg = TemplateEditorDialog(None, self)
        if dlg.exec():
            self.template_browser.reload()
            self.templates = load_templates(TEMPLATES_DIR)

    def _edit_template(self, tpl_id):
        tpl = self.templates.get(tpl_id)
        if not tpl:
            return
        dlg = TemplateEditorDialog(tpl, self)
        if dlg.exec():
            self.template_browser.reload()
            self.templates = load_templates(TEMPLATES_DIR)
            self._update_preview()

    # ---------------------------------------------------------------- project menu
    def _reload_all_settings_panels_from_project(self):
        self.quote_editor.set_quotes(self.project.get("quotes", []) or [])
        ids = self.project.get("template_ids") or list(self.templates.keys())
        self.template_browser.set_selection(ids, self.project.get("template_mode", "random"))
        self.selected_template_ids, self.template_mode = ids, self.project.get("template_mode", "random")

    def _collect_project(self) -> dict:
        self.project["quotes"] = self.quote_editor.quotes
        self.project["template_ids"] = self.selected_template_ids
        self.project["template_mode"] = self.template_mode
        self.style_panel.apply_to(self.project)
        self.background_panel.apply_to(self.project)
        self.output_panel.apply_to(self.project)
        return self.project

    def new_project(self):
        if QMessageBox.question(self, "New project", "Start a new project? Unsaved changes will be lost.") != QMessageBox.StandardButton.Yes:
            return
        self.project = project_manager.default_project()
        self.current_project_path = None
        self.project_label.setText("Untitled Project")
        self._rebuild_settings_panels()

    def _rebuild_settings_panels(self):
        idx = self.stack.currentIndex()
        for w in [self.style_panel, self.background_panel, self.output_panel]:
            w.setParent(None)
        self.style_panel = StylePanel(self.project)
        self.background_panel = BackgroundPanel(self.project)
        self.output_panel = OutputPanel(self.project)
        self.stack.insertWidget(2, self.style_panel)
        self.stack.insertWidget(3, self.background_panel)
        self.stack.insertWidget(4, self.output_panel)
        self.style_panel.changed.connect(self._update_preview)
        self.background_panel.changed.connect(self._on_settings_touched)
        self.output_panel.changed.connect(self._on_settings_touched)
        self._reload_all_settings_panels_from_project()
        self.stack.setCurrentIndex(idx)
        self._update_preview()

    def open_project(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open project", str(PROJECTS_DIR), "QuoteBatch project (*.qbsproj)")
        if not path:
            return
        try:
            self.project = project_manager.load_project(path)
        except Exception as exc:
            QMessageBox.warning(self, "Couldn't open project", str(exc))
            return
        self.current_project_path = Path(path)
        self.project_label.setText(self.project.get("name", Path(path).stem))
        self._rebuild_settings_panels()
        self.statusBar().showMessage(f"Opened {Path(path).name}", 5000)

    def save_project(self):
        if not self.current_project_path:
            return self.save_project_as()
        data = self._collect_project()
        project_manager.save_project(data, self.current_project_path)
        self.statusBar().showMessage(f"Saved {self.current_project_path.name}", 5000)

    def save_project_as(self):
        PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
        path, _ = QFileDialog.getSaveFileName(self, "Save project as", str(PROJECTS_DIR / "my_project.qbsproj"),
                                              "QuoteBatch project (*.qbsproj)")
        if not path:
            return
        data = self._collect_project()
        data["name"] = Path(path).stem
        saved = project_manager.save_project(data, path)
        self.current_project_path = saved
        self.project_label.setText(data["name"])
        self.statusBar().showMessage(f"Saved {saved.name}", 5000)

    def closeEvent(self, ev):
        if self.generate_panel.run and not self.generate_panel.run.is_finished():
            if QMessageBox.question(self, "Generation in progress", "A batch is still generating. Quit anyway?") != QMessageBox.StandardButton.Yes:
                ev.ignore()
                return
            self.generate_panel.run.cancel()
        ev.accept()
