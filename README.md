# QuoteBatch Studio

**Turn your quotes into beautiful posts — in bulk.**

A desktop app (Python + PySide6) for creators who need to turn dozens or hundreds of
quotes into polished, on-brand social-media images in one batch.

Paste 100 quotes → choose templates → click **GENERATE ALL** → get 100 ready-to-post images,
each with a matching caption + hashtag file.

![screenshot placeholder](docs_screenshot.png)

---

## Features

- Paste quotes, or import `.txt` / `.csv` / `.json`
- Full quote editor: edit, delete, duplicate, reorder, select/deselect, author, category
- 10 built-in templates (Minimal, Cinematic, Nature, Gradient, Luxury, Soft, Bold, Photo,
  Editorial, and a branded "One More Step" template) plus a visual **Template Creator**
- Fixed / Random / Rotate / **Smart** (rule-based, no AI required) template selection
- Local background photo folders with categories (`backgrounds/nature/`, `backgrounds/ocean/`, …) —
  or generated built-in background art if you don't supply your own photos
- Automatic smart text fitting — quotes always fit, never overflow, never get cut off
- Full typography controls: font family/preset, size, weight, letter/line spacing, alignment, color, opacity
- Branding: name, per-word color (e.g. **ONE** red / **MORE** white / **STEP** blue), logo, placement, opacity
- Common social sizes (1080×1080, 1080×1350, 1080×1920, 1200×630) + custom
- Live preview that updates as you edit
- Multiple **variations** per quote (1/3/5/10) across different templates
- Bulk generation with progress bar, time estimate, **pause / resume / cancel**, and resume-after-interruption
- Organized output: `output/<date>/`, `captions/`, `previews/`
- Smart filenames (brand+number, or derived from the quote text)
- Caption + hashtag generator (offline, rule-based)
- PNG / JPG / WEBP export with quality control
- Project save/open (`.qbsproj`) — remembers quotes, templates, branding, output settings
- Runs fully offline — no API keys, no internet connection required

---

## 1. Install

Requires **Python 3.11+**.

```bash
cd quote_batch_studio
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

pip install -r requirements.txt
```

## 2. Run

```bash
python app.py
```

The first run creates `output/`, `projects/`, and copies the bundled `templates/`, `assets/`
and `examples/` folders if they're missing. A handful of sample background photos are
already included under `assets/backgrounds/<category>/` so the app works immediately —
drop in your own photos alongside them (or replace them).

## 3. Try the example project

**File → Open Project…** and choose `projects/one_more_step/one_more_step.qbsproj`. It's
pre-loaded with the quotes from `examples/sample_quotes.txt`, the bundled sample backgrounds,
and the "One More Step" branding (red/white/blue). Click **Generate** → **GENERATE ALL**.

You can also import `examples/sample_quotes.csv` or `examples/sample_quotes.json` from the
Quotes tab to see the CSV/JSON import paths.

---

## Adding your own fonts

Drop `.ttf` / `.otf` / `.ttc` files into `assets/fonts/`. QuoteBatch Studio also sees fonts
already installed on your system (Windows: `C:\Windows\Fonts`). The Style & Brand tab lets
you choose a style preset (Bold, Elegant, Minimal, Editorial, Handwritten, Modern, Serif,
Sans-serif) or type an exact installed font family name. If a chosen font can't be found,
the app falls back automatically and tells you in the preview.

## Adding your own backgrounds

Point the **Backgrounds** tab at any folder. Sub-folders become categories automatically:

```text
my_backgrounds/
    nature/
    city/
    ocean/
    sunset/
```

Loose images directly in the folder become a `general` category. JPG, PNG and WEBP are
supported, and a folder with hundreds of images is fine — each image is used once before
any repeats (no two early posts sharing a background by chance).

## Creating your own templates

**Templates → + New Template…** opens the visual Template Creator: add text, image, logo,
rectangle, circle or gradient elements; drag to move, and use the property panel to resize,
rotate, recolor, or change fonts/opacity. **SAVE AS TEMPLATE** adds it to your library
immediately (saved as plain JSON under `templates/`, so you can also hand-edit a copy —
see `tools/build_templates.py` for the format the 10 built-in templates use).

---

## Packaging a Windows `.exe`

From Windows, inside your activated virtual environment:

```bash
pip install pyinstaller
pyinstaller --noconfirm --windowed --name "QuoteBatch Studio" ^
  --add-data "templates;templates" ^
  --add-data "assets;assets" ^
  --add-data "examples;examples" ^
  --add-data "projects;projects" ^
  app.py
```

The build appears in `dist/QuoteBatch Studio/`. The app detects when it's running as a
packaged `.exe` and keeps its writable data (`output/`, `projects/`, `templates/`, `assets/`)
next to the executable rather than inside the bundle, so it behaves the same as running
from source. Zip the whole `dist/QuoteBatch Studio/` folder to share it — there's no separate
installer step required.

If Windows SmartScreen flags the unsigned `.exe` the first time it's run, that's expected
for an app built locally without a code-signing certificate; choose "More info → Run anyway".

---

## Project structure

```text
quote_batch_studio/
├── app.py                   # entry point
├── requirements.txt
├── README.md
│
├── core/                    # all non-UI logic (Qt-free, except qimage_util.py)
│   ├── paths.py              # where data lives (source vs packaged .exe)
│   ├── fonts.py               # font discovery, presets, caching
│   ├── text_fitter.py         # smart text fitting / wrapping / balancing
│   ├── background_manager.py  # background scanning + built-in procedural backgrounds
│   ├── template_engine.py     # template load/save + fixed/random/rotate/smart selection
│   ├── renderer.py            # draws one quote + template -> PIL image
│   ├── quote_io.py            # paste/TXT/CSV/JSON parsing
│   ├── captions.py            # caption + hashtag generation
│   ├── filenames.py           # smart filenames + sanitizing
│   ├── batch_processor.py     # multiprocessing batch runner (pause/resume/cancel/resume-after-crash)
│   ├── project_manager.py     # .qbsproj save/load
│   └── qimage_util.py         # PIL <-> QPixmap bridge
│
├── ui/                       # PySide6 widgets
│   ├── theme.py
│   ├── main_window.py
│   ├── quote_editor.py
│   ├── template_browser.py
│   ├── template_editor.py     # visual Template Creator
│   ├── settings.py            # Style & Brand / Backgrounds / Output panels
│   ├── preview.py
│   └── generate_panel.py
│
├── templates/                 # the 10 built-in templates (JSON) + any you create
├── assets/
│   ├── backgrounds/            # sample backgrounds, organized by category
│   ├── fonts/                  # drop your own font files here
│   └── logos/
├── examples/                   # sample_quotes.txt / .csv / .json
├── projects/one_more_step/     # example project
└── output/                     # generated images land here by default
```

## Troubleshooting

- **"Font not found" warning in the preview** — the chosen font isn't installed and isn't in
  `assets/fonts/`; the app substitutes a close fallback automatically and keeps going.
- **A quote shows a "text shrunk to fit" warning** — an extremely long quote; it still renders
  completely (that's the point of smart text fitting), just smaller than your preferred size.
- **A background folder shows "No images found"** — make sure the images are directly inside
  the folder or one level deep in category sub-folders, and are `.jpg`/`.jpeg`/`.png`/`.webp`.
- **Generation is slow** — batch rendering uses multiple CPU cores automatically; very large
  background photos are downscaled on load to keep things fast.
