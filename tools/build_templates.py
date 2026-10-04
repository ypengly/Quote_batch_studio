"""Regenerates the 10 built-in templates in ../templates/. Run: python tools/build_templates.py
(Templates are plain JSON - you can also edit them by hand or in the in-app Template Editor.)"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "templates"


def bg(kind="solid", color="#000000", colors=None, angle=135, photo_kind="nature", overlay=0.0, ov_color="#000000",
       ov_colors=None, blur=0.0, vignette=0.0):
    fill = {"kind": kind, "color": color, "colors": colors or [], "angle": angle}
    ov = {"color": ov_color, "opacity": overlay}
    if ov_colors:
        ov["colors"], ov["angle"], ov["opacity"] = ov_colors, 90, 1.0
    return {"type": "background", "fill": fill, "overlay": ov, "blur": blur, "vignette": vignette, "photo_kind": photo_kind}


def quote(box, font, color, align="center", valign="middle", max_size=0.1, min_size=0.038, ls=1.18, sp=0.0,
          case="none", marks=True, weight=None, shadow=None):
    e = {"type": "quote", "box": box, "font": font, "weight": weight, "color": color, "align": align, "valign": valign,
         "max_size": max_size, "min_size": min_size, "line_spacing": ls, "letter_spacing": sp, "case": case,
         "quote_marks": marks, "opacity": 1.0}
    if shadow:
        e["shadow"] = shadow
    return e


def author(box, font, color, align="center", size=0.032, sp=0.06, prefix="\u2014 "):
    return {"type": "author", "box": box, "font": font, "color": color, "align": align, "valign": "middle",
            "max_size": size, "min_size": 0.02, "letter_spacing": sp, "prefix": prefix}


def rect(box, color, opacity=1.0, radius=0.0, **kw):
    return {"type": "rect", "box": box, "color": color, "opacity": opacity, "radius": radius, **kw}


def circle(box, color, opacity=1.0, **kw):
    return {"type": "circle", "box": box, "color": color, "opacity": opacity, **kw}


def brand(pos="auto", scale=1.0):
    return {"type": "brand", "position": pos, "scale": scale}


SHADOW = {"blur": 0.012, "dy": 0.006, "opacity": 0.6, "color": "#000000"}
T = []


def add(order, id_, name, desc, tags, elements):
    T.append({"id": id_, "name": name, "description": desc, "tags": tags, "order": order, "elements": elements})


add(1, "template_01", "Minimal", "Large centered typography on a calm paper background.", ["minimal", "light", "long"], [
    bg("solid", "#F4F0E8"),
    quote([0.12, 0.18, 0.76, 0.58], "Minimal", "#1B1B1B", max_size=0.1, weight=400),
    rect([0.46, 0.79, 0.08, 0.004], "#1B1B1B", 0.8),
    author([0.15, 0.81, 0.7, 0.05], "Minimal", "#555555"), brand("auto")])

add(2, "template_02", "Cinematic", "Dark cinematic frame with letterbox bars and strong white type.", ["cinematic", "dark", "emotional"], [
    bg("photo", photo_kind="city", overlay=0.5, vignette=0.55),
    rect([0, 0, 1, 0.1], "#000000"), rect([0, 0.9, 1, 0.1], "#000000"),
    quote([0.1, 0.2, 0.8, 0.6], "Bold", "#FFFFFF", max_size=0.105, weight=700, shadow=SHADOW, ls=1.12),
    author([0.1, 0.8, 0.8, 0.05], "Modern", "#E0E0E0", sp=0.12), brand("bottom-center")])

add(3, "template_03", "Nature", "Landscape background with a soft dark overlay.", ["nature", "photo"], [
    bg("photo", photo_kind="nature", overlay=0.38, vignette=0.3),
    quote([0.1, 0.2, 0.8, 0.55], "Elegant", "#FFFFFF", max_size=0.1, weight=500, shadow=SHADOW),
    author([0.1, 0.78, 0.8, 0.05], "Elegant", "#F0F0F0", sp=0.1), brand("auto")])

add(4, "template_04", "Gradient", "Modern gradient with bold typography.", ["gradient", "bold", "short"], [
    bg("gradient", colors=["#5B2BFF", "#C81CDE", "#FF5F6D"], angle=125),
    circle([0.55, -0.15, 0.7, 0.7], "#FFFFFF", 0.07), circle([-0.2, 0.6, 0.6, 0.6], "#FFFFFF", 0.06),
    quote([0.1, 0.18, 0.8, 0.6], "Bold", "#FFFFFF", max_size=0.115, weight=800, ls=1.1, shadow={"blur": 0.01, "dy": 0.005, "opacity": 0.25}),
    author([0.1, 0.8, 0.8, 0.05], "Modern", "#FFFFFF", sp=0.1), brand("auto")])

add(5, "template_05", "Luxury", "Elegant dark background, gold frame and refined serif type.", ["luxury", "dark", "emotional"], [
    bg("gradient", colors=["#0C0C0E", "#1D1A16"], angle=90),
    rect([0.05, 0.05, 0.9, 0.9], "#C9A961", 1.0, outline="#C9A961", outline_width=0.004, no_fill=True),
    rect([0.07, 0.07, 0.86, 0.86], "#C9A961", 0.5, outline="#C9A961", outline_width=0.0015, no_fill=True),
    quote([0.14, 0.2, 0.72, 0.52], "Elegant", "#EBDDB0", max_size=0.088, weight=500, ls=1.25, sp=0.01),
    rect([0.44, 0.76, 0.12, 0.003], "#C9A961"),
    author([0.15, 0.78, 0.7, 0.05], "Elegant", "#C9A961", sp=0.2), brand("bottom-center")])

add(6, "template_06", "Soft", "Warm, peaceful colors and clean typography.", ["soft", "light", "long"], [
    bg("gradient", colors=["#FFE8D6", "#F7C6D0", "#D9C2F0"], angle=125),
    circle([0.6, 0.05, 0.5, 0.5], "#FFFFFF", 0.28), circle([-0.15, 0.62, 0.5, 0.5], "#FFFFFF", 0.22),
    quote([0.12, 0.2, 0.76, 0.55], "Modern", "#5B3A4A", max_size=0.085, weight=500, ls=1.28),
    author([0.15, 0.78, 0.7, 0.05], "Modern", "#8A6577", sp=0.08), brand("auto")])

add(7, "template_07", "Bold", "Oversized uppercase typography with graphic elements.", ["bold", "short"], [
    bg("solid", "#FFD60A"),
    rect([0, 0.86, 1, 0.14], "#111111"),
    circle([0.72, 0.06, 0.34, 0.34], "#111111", 1.0, outline="#111111", outline_width=0.05, no_fill=True),
    rect([0.07, 0.07, 0.16, 0.014], "#111111"),
    quote([0.07, 0.16, 0.86, 0.62], "Bold", "#111111", align="left", valign="middle", max_size=0.15, min_size=0.045, weight=900, ls=1.02, case="upper", marks=False),
    author([0.07, 0.79, 0.86, 0.05], "Bold", "#111111", align="left", sp=0.1), brand("bottom-right")])

add(8, "template_08", "Photo", "Full-screen photo with a bottom gradient and left-aligned overlay text.", ["photo"], [
    bg("photo", photo_kind="sunset", overlay=0.15, ov_colors=["#00000000", "#000000D0"]),
    quote([0.08, 0.42, 0.84, 0.4], "Modern", "#FFFFFF", align="left", valign="bottom", max_size=0.095, weight=700, shadow=SHADOW),
    rect([0.08, 0.845, 0.1, 0.006], "#FFFFFF"),
    author([0.08, 0.86, 0.6, 0.04], "Modern", "#EEEEEE", align="left", sp=0.1), brand("top-left")])

add(9, "template_09", "Editorial", "Magazine-style composition with rules and a large quote mark.", ["editorial", "light", "long"], [
    bg("solid", "#EFEBE4"),
    rect([0.08, 0.08, 0.84, 0.004], "#111111"), rect([0.08, 0.92, 0.84, 0.004], "#111111"),
    {"type": "text", "text": "\u201c", "box": [0.06, 0.06, 0.3, 0.3], "font": "Editorial", "weight": 700, "color": "#C8372D",
     "size": 0.36, "align": "left", "valign": "top", "max_size": 0.36, "min_size": 0.2, "opacity": 1.0},
    quote([0.1, 0.3, 0.8, 0.46], "Editorial", "#141414", align="left", valign="top", max_size=0.085, min_size=0.036, weight=700, ls=1.2, marks=False),
    author([0.1, 0.8, 0.8, 0.05], "Editorial", "#C8372D", align="left", sp=0.14, prefix=""), brand("bottom-right")])

add(10, "template_10", "One More Step", "Branded template for the One More Step page (ONE red, MORE white, STEP blue).", ["onemorestep", "branded", "dark"], [
    bg("gradient", colors=["#090C16", "#151C33"], angle=90, vignette=0.35),
    brand("top-center", 1.7),
    rect([0.3, 0.155, 0.13, 0.006], "#E63946"), rect([0.435, 0.155, 0.13, 0.006], "#FFFFFF"), rect([0.57, 0.155, 0.13, 0.006], "#2F6BFF"),
    quote([0.1, 0.22, 0.8, 0.52], "Modern", "#FFFFFF", max_size=0.09, weight=700, ls=1.22),
    author([0.1, 0.76, 0.8, 0.05], "Modern", "#AEB6D0", sp=0.1),
    brand("bottom-center", 0.85)])

OUT.mkdir(exist_ok=True)
for t in T:
    (OUT / f"{t['id']}.json").write_text(json.dumps(t, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"wrote {len(T)} templates to {OUT}")
