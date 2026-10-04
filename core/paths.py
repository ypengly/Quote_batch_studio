"""Central place for locating app folders (works from source and from a PyInstaller build)."""
import shutil
import sys
from pathlib import Path

FROZEN = getattr(sys, "frozen", False)
BUNDLE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
# Writable folder: next to the .exe when packaged, the project folder otherwise.
DATA_DIR = Path(sys.executable).resolve().parent if FROZEN else Path(__file__).resolve().parent.parent

TEMPLATES_DIR = DATA_DIR / "templates"
ASSETS_DIR = DATA_DIR / "assets"
BACKGROUNDS_DIR = ASSETS_DIR / "backgrounds"
FONTS_DIR = ASSETS_DIR / "fonts"
LOGOS_DIR = ASSETS_DIR / "logos"
OUTPUT_DIR = DATA_DIR / "output"
PROJECTS_DIR = DATA_DIR / "projects"
EXAMPLES_DIR = DATA_DIR / "examples"
USER_DIR = Path.home() / ".quotebatch_studio"


def ensure_user_dirs() -> None:
    """Create writable folders; on first run of a packaged build copy bundled defaults next to the exe."""
    if FROZEN and BUNDLE_DIR != DATA_DIR:
        for name in ("templates", "assets", "examples", "projects"):
            src, dst = BUNDLE_DIR / name, DATA_DIR / name
            if src.exists() and not dst.exists():
                shutil.copytree(src, dst)
    for d in (TEMPLATES_DIR, BACKGROUNDS_DIR, FONTS_DIR, LOGOS_DIR, OUTPUT_DIR, PROJECTS_DIR, EXAMPLES_DIR, USER_DIR):
        d.mkdir(parents=True, exist_ok=True)
