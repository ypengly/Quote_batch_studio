"""Dark theme stylesheet + palette constants shared across the UI."""

BG0 = "#121319"
BG1 = "#191b22"
BG2 = "#20232d"
BG3 = "#2a2e3a"
BORDER = "#343948"
ACCENT = "#7C5CFF"
ACCENT2 = "#5B2BFF"
TEXT = "#EDEEF2"
SUBTEXT = "#9AA0B4"
DANGER = "#E5484D"
SUCCESS = "#3DD68C"
WARN = "#F5A623"

QSS = f"""
* {{ font-family: 'Segoe UI', 'Inter', 'Helvetica Neue', Arial, sans-serif; color: {TEXT}; }}
QMainWindow, QWidget#root {{ background: {BG0}; }}
QWidget {{ background: transparent; }}
QLabel#h1 {{ font-size: 20px; font-weight: 700; }}
QLabel#h2 {{ font-size: 14px; font-weight: 600; color: {TEXT}; }}
QLabel#subtitle {{ color: {SUBTEXT}; font-size: 12px; }}
QLabel#muted {{ color: {SUBTEXT}; }}

QFrame#card {{ background: {BG1}; border: 1px solid {BORDER}; border-radius: 14px; }}
QFrame#navbar {{ background: {BG1}; border-right: 1px solid {BORDER}; }}

QPushButton {{
    background: {BG2}; border: 1px solid {BORDER}; border-radius: 10px;
    padding: 8px 16px; font-weight: 600; font-size: 13px;
}}
QPushButton:hover {{ background: {BG3}; border-color: {ACCENT}; }}
QPushButton:pressed {{ background: {BG1}; }}
QPushButton:disabled {{ color: {SUBTEXT}; background: {BG1}; }}
QPushButton#primary {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {ACCENT2}, stop:1 {ACCENT});
    border: none; color: white; padding: 12px 22px; font-size: 14px; border-radius: 12px;
}}
QPushButton#primary:hover {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #6a3fff, stop:1 #8f73ff); }}
QPushButton#primary:disabled {{ background: {BG2}; color: {SUBTEXT}; }}
QPushButton#danger {{ border-color: {DANGER}; color: {DANGER}; }}
QPushButton#danger:hover {{ background: rgba(229,72,77,0.12); }}
QPushButton#nav {{
    text-align: left; background: transparent; border: none; border-radius: 10px;
    padding: 10px 14px; font-weight: 600; color: {SUBTEXT};
}}
QPushButton#nav:hover {{ background: {BG2}; color: {TEXT}; }}
QPushButton#navActive {{ text-align: left; background: {BG2}; border: none; border-left: 3px solid {ACCENT};
    border-radius: 10px; padding: 10px 14px 10px 11px; font-weight: 700; color: {TEXT}; }}
QPushButton#chip {{ border-radius: 14px; padding: 5px 12px; font-size: 12px; background: {BG2}; }}
QPushButton#chipActive {{ border-radius: 14px; padding: 5px 12px; font-size: 12px;
    background: {ACCENT}; border-color: {ACCENT}; color: white; }}
QPushButton#iconBtn {{ border-radius: 8px; padding: 4px 8px; font-size: 12px; }}

QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background: {BG2}; border: 1px solid {BORDER}; border-radius: 8px; padding: 6px 8px; selection-background-color: {ACCENT};
}}
QTextEdit:focus, QLineEdit:focus, QPlainTextEdit:focus {{ border-color: {ACCENT}; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{ background: {BG2}; border: 1px solid {BORDER}; selection-background-color: {ACCENT}; }}

QTableWidget {{ background: {BG1}; border: 1px solid {BORDER}; border-radius: 10px; gridline-color: {BORDER}; }}
QHeaderView::section {{ background: {BG2}; border: none; border-bottom: 1px solid {BORDER}; padding: 6px; font-weight: 600; }}
QTableWidget::item:selected {{ background: rgba(124,92,255,0.25); }}

QScrollArea {{ border: none; }}
QScrollBar:vertical {{ background: {BG0}; width: 10px; margin: 0; }}
QScrollBar::handle:vertical {{ background: {BG3}; border-radius: 5px; min-height: 24px; }}
QScrollBar:horizontal {{ background: {BG0}; height: 10px; }}
QScrollBar::handle:horizontal {{ background: {BG3}; border-radius: 5px; min-width: 24px; }}

QProgressBar {{ background: {BG2}; border: 1px solid {BORDER}; border-radius: 8px; text-align: center; height: 22px; }}
QProgressBar::chunk {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {ACCENT2}, stop:1 {ACCENT}); border-radius: 7px; }}

QSlider::groove:horizontal {{ height: 4px; background: {BG3}; border-radius: 2px; }}
QSlider::handle:horizontal {{ background: {ACCENT}; width: 16px; height: 16px; margin: -6px 0; border-radius: 8px; }}

QCheckBox, QRadioButton {{ spacing: 8px; }}
QCheckBox::indicator, QRadioButton::indicator {{ width: 16px; height: 16px; border-radius: 4px; border: 1px solid {BORDER}; background: {BG2}; }}
QCheckBox::indicator:checked, QRadioButton::indicator:checked {{ background: {ACCENT}; border-color: {ACCENT}; }}

QToolTip {{ background: {BG3}; color: {TEXT}; border: 1px solid {BORDER}; padding: 4px 8px; border-radius: 6px; }}
QSplitter::handle {{ background: {BORDER}; width: 1px; }}
QListWidget {{ background: {BG1}; border: 1px solid {BORDER}; border-radius: 10px; }}
QListWidget::item:selected {{ background: rgba(124,92,255,0.25); border-radius: 6px; }}
QStatusBar {{ background: {BG1}; border-top: 1px solid {BORDER}; color: {SUBTEXT}; }}
"""
