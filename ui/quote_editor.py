"""Quote input + editable quote list (paste box, TXT/CSV/JSON import, table with
edit/delete/duplicate/reorder/select, add author/category, + Add Quote)."""
from __future__ import annotations

import copy

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QFileDialog, QFrame, QHBoxLayout, QHeaderView,
                               QLabel, QMessageBox, QPlainTextEdit, QPushButton, QTableWidget, QTableWidgetItem,
                               QVBoxLayout, QWidget)

from core import quote_io
from core.quote_io import new_quote

COLS = ["✓", "#", "Quote", "Author", "Category", ""]


class QuoteEditorWidget(QWidget):
    quotes_changed = Signal()
    selection_changed = Signal(dict)  # emits the quote dict currently focused, for live preview

    def __init__(self, parent=None):
        super().__init__(parent)
        self.quotes: list[dict] = []
        self._build()

    # ---------------------------------------------------------------- UI
    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(14)

        paste_card = QFrame(objectName="card")
        pv = QVBoxLayout(paste_card)
        row = QHBoxLayout()
        row.addWidget(QLabel("Paste your quotes", objectName="h2"))
        row.addStretch(1)
        for label, slot in [("Import TXT/CSV/JSON…", self.import_file), ("Add from pasted text ⬇", self.add_from_paste)]:
            b = QPushButton(label)
            b.clicked.connect(slot)
            row.addWidget(b)
        pv.addLayout(row)
        pv.addWidget(QLabel("One quote per paragraph (blank line between quotes), or one per line.", objectName="subtitle"))
        self.paste_box = QPlainTextEdit()
        self.paste_box.setPlaceholderText(
            "You're not behind. There is no schedule everyone else is following.\n\n"
            "You don't need the whole map. You need the next step.\n\n"
            "Stop waiting to feel ready. Ready is a myth for people who never start.")
        self.paste_box.setFixedHeight(140)
        pv.addWidget(self.paste_box)
        root.addWidget(paste_card)

        list_card = QFrame(objectName="card")
        lv = QVBoxLayout(list_card)
        head = QHBoxLayout()
        self.count_label = QLabel("0 quotes", objectName="h2")
        head.addWidget(self.count_label)
        head.addStretch(1)
        for label, slot in [("+ Add Quote", self.add_blank), ("Duplicate", self.duplicate_selected),
                            ("Delete", self.delete_selected), ("Move up", self.move_up),
                            ("Move down", self.move_down), ("Select all", self.select_all),
                            ("Select none", self.select_none)]:
            b = QPushButton(label)
            b.clicked.connect(slot)
            head.addWidget(b)
        lv.addLayout(head)

        self.table = QTableWidget(0, len(COLS))
        self.table.setHorizontalHeaderLabels(COLS)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked | QAbstractItemView.EditTrigger.EditKeyPressed)
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        for c in (0, 1, 5):
            hh.setSectionResizeMode(c, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setColumnWidth(3, 120)
        self.table.setColumnWidth(4, 110)
        self.table.itemChanged.connect(self._on_item_changed)
        self.table.itemSelectionChanged.connect(self._on_selection)
        lv.addWidget(self.table)
        root.addWidget(list_card, 1)

    # ---------------------------------------------------------------- data <-> table
    def set_quotes(self, quotes: list[dict]):
        self.quotes = quotes
        self._refresh_table()

    def _refresh_table(self):
        self.table.blockSignals(True)
        self.table.setRowCount(len(self.quotes))
        for r, q in enumerate(self.quotes):
            chk = QCheckBox()
            chk.setChecked(q.get("selected", True))
            chk.stateChanged.connect(lambda st, row=r: self._toggle_selected(row, st))
            cell = QWidget()
            cl = QHBoxLayout(cell)
            cl.addWidget(chk)
            cl.setContentsMargins(8, 0, 0, 0)
            cl.setAlignment(Qt.AlignmentFlag.AlignLeft)
            self.table.setCellWidget(r, 0, cell)
            self.table.setItem(r, 1, self._ro_item(str(r + 1)))
            preview = q["text"].replace("\n", " \u21b5 ")
            self.table.setItem(r, 2, QTableWidgetItem(preview))
            self.table.setItem(r, 3, QTableWidgetItem(q.get("author", "")))
            self.table.setItem(r, 4, QTableWidgetItem(q.get("category", "")))
            del_btn = QPushButton("✕", objectName="iconBtn")
            del_btn.setFixedWidth(28)
            del_btn.clicked.connect(lambda _, row=r: self.delete_row(row))
            self.table.setCellWidget(r, 5, del_btn)
        self.table.blockSignals(False)
        self.count_label.setText(f"{len(self.quotes)} quote{'s' if len(self.quotes) != 1 else ''}  ·  "
                                  f"{sum(1 for q in self.quotes if q.get('selected', True))} selected")
        self.quotes_changed.emit()

    def _ro_item(self, text):
        it = QTableWidgetItem(text)
        it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
        return it

    def _toggle_selected(self, row, state):
        if 0 <= row < len(self.quotes):
            self.quotes[row]["selected"] = bool(state)
            self.count_label.setText(f"{len(self.quotes)} quotes  ·  "
                                      f"{sum(1 for q in self.quotes if q.get('selected', True))} selected")
            self.quotes_changed.emit()

    def _on_item_changed(self, item: QTableWidgetItem):
        row, col = item.row(), item.column()
        if row >= len(self.quotes):
            return
        if col == 2:
            self.quotes[row]["text"] = item.text().replace(" \u21b5 ", "\n")
        elif col == 3:
            self.quotes[row]["author"] = item.text()
        elif col == 4:
            self.quotes[row]["category"] = item.text()
        self.quotes_changed.emit()

    def move_up(self):
        rows = sorted({i.row() for i in self.table.selectedIndexes()})
        if not rows or rows[0] == 0:
            return
        for r in rows:
            self.quotes[r - 1], self.quotes[r] = self.quotes[r], self.quotes[r - 1]
        self._refresh_table()
        self._reselect_rows([r - 1 for r in rows])

    def move_down(self):
        rows = sorted({i.row() for i in self.table.selectedIndexes()}, reverse=True)
        if not rows or rows[0] == len(self.quotes) - 1:
            return
        for r in rows:
            self.quotes[r + 1], self.quotes[r] = self.quotes[r], self.quotes[r + 1]
        self._refresh_table()
        self._reselect_rows([r + 1 for r in rows])

    def _reselect_rows(self, rows):
        self.table.clearSelection()
        for r in rows:
            if 0 <= r < self.table.rowCount():
                self.table.selectRow(r)

    def _on_selection(self):
        rows = sorted({i.row() for i in self.table.selectedIndexes()})
        if rows and rows[0] < len(self.quotes):
            self.selection_changed.emit(self.quotes[rows[0]])

    def selected_row(self) -> int | None:
        rows = sorted({i.row() for i in self.table.selectedIndexes()})
        return rows[0] if rows else None

    # ---------------------------------------------------------------- actions
    def add_from_paste(self):
        text = self.paste_box.toPlainText().strip()
        if not text:
            QMessageBox.information(self, "Nothing to add", "Paste some quotes into the box first.")
            return
        new = quote_io.parse_pasted_text(text)
        self.quotes.extend(new)
        self.paste_box.clear()
        self._refresh_table()

    def import_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import quotes", "", "Quote files (*.txt *.csv *.json)")
        if not path:
            return
        try:
            new = quote_io.load_file(path)
        except Exception as exc:
            QMessageBox.warning(self, "Import failed", f"Couldn't read that file:\n{exc}")
            return
        if not new:
            QMessageBox.information(self, "No quotes found", "That file didn't contain any quotes.")
            return
        self.quotes.extend(new)
        self._refresh_table()

    def add_blank(self):
        self.quotes.append(new_quote("New quote — click to edit"))
        self._refresh_table()
        self.table.editItem(self.table.item(len(self.quotes) - 1, 2))

    def delete_row(self, row: int):
        if 0 <= row < len(self.quotes):
            del self.quotes[row]
            self._refresh_table()

    def delete_selected(self):
        rows = sorted({i.row() for i in self.table.selectedIndexes()}, reverse=True)
        if not rows:
            QMessageBox.information(self, "Nothing selected", "Select one or more rows first.")
            return
        for r in rows:
            del self.quotes[r]
        self._refresh_table()

    def duplicate_selected(self):
        rows = sorted({i.row() for i in self.table.selectedIndexes()})
        if not rows:
            return
        for r in reversed(rows):
            dup = copy.deepcopy(self.quotes[r])
            dup["id"] = new_quote("")["id"]
            self.quotes.insert(r + 1, dup)
        self._refresh_table()

    def select_all(self):
        for q in self.quotes:
            q["selected"] = True
        self._refresh_table()

    def select_none(self):
        for q in self.quotes:
            q["selected"] = False
        self._refresh_table()

    def selected_quotes(self) -> list[dict]:
        return [q for q in self.quotes if q.get("selected", True)]
