"""Renders one quote + one template into a PIL image."""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

from .background_manager import load_background, procedural_background
from .fonts import PRESETS, load_font, resolve
from .text_fitter import fit_text, line_width

DEFAULT_BRAND = {
    "enabled": True, "name": "One More Step", "color_mode": "per_word",
    "colors": ["#E63946", "#FFFFFF", "#2F6BFF"], "logo": "", "position": "bottom-center",
    "opacity": 90, "size_pct": 100, "font": "Bold", "letter_spacing": 0.14, "legibility_pill": True,
}


def hex_rgba(value: str, default=(255, 255, 255, 255)) -> tuple[int, int, int, int]:
    try:
        v = value.lstrip("#")
        if len(v) == 3:
            v = "".join(c * 2 for c in v)
        r, g, b = int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16)
        a = int(v[6:8], 16) if len(v) >= 8 else 255
        return r, g, b, a
    except Exception:
        return default


def smartify(text: str) -> str:
    """Curly quotes / apostrophes and clean spaces."""
    text = re.sub(r"\s+", " ", text.replace("\r", " ")).strip() if "\n" not in text else "\n".join(
        re.sub(r"[ \t]+", " ", l).strip() for l in text.strip().splitlines())
    text = re.sub(r"(\w)'(\w)", "\\1\u2019\\2", text)
    text = re.sub(r"(^|[\s(\[])'", "\\1\u2018", text)
    text = text.replace("'", "\u2019")
    out, open_q = [], True
    for ch in text:
        if ch == '"':
            out.append("\u201c" if open_q else "\u201d")
            open_q = not open_q
        else:
            out.append(ch)
    return "".join(out)


def strip_outer_quotes(text: str) -> str:
    t = text.strip()
    pairs = [('"', '"'), ("\u201c", "\u201d"), ("'", "'"), ("\u2018", "\u2019")]
    for a, b in pairs:
        if len(t) > 2 and t[0] == a and t[-1] == b and t.count(a) <= 1:
            return t[1:-1].strip()
    return t


def apply_case(text: str, mode: str) -> str:
    if mode == "upper":
        return text.upper()
    if mode == "title":
        return text.title()
    if mode == "lower":
        return text.lower()
    return text


# ------------------------------------------------------------------ low-level drawing
def gradient_array(w, h, colors, angle=90):
    """RGBA float array. colors: list of hex (alpha allowed). angle in degrees (0 = left->right, 90 = top->bottom)."""
    cols = [hex_rgba(c) for c in (colors or ["#000000", "#FFFFFF"])]
    if len(cols) == 1:
        cols = cols * 2
    a = np.deg2rad(angle)
    dx, dy = np.cos(a), np.sin(a)
    xs = (np.arange(w) - w / 2)[None, :]
    ys = (np.arange(h) - h / 2)[:, None]
    proj = xs * dx + ys * dy
    span = abs(w * dx) / 2 + abs(h * dy) / 2 or 1
    t = np.clip((proj / span + 1) / 2, 0, 1)
    pos = np.linspace(0, 1, len(cols))
    return np.stack([np.interp(t, pos, [c[i] for c in cols]) for i in range(4)], axis=-1)


def apply_opacity(layer: Image.Image, opacity: float) -> Image.Image:
    if opacity >= 0.999:
        return layer
    a = layer.getchannel("A").point(lambda v: int(v * max(0.0, opacity)))
    layer = layer.copy()
    layer.putalpha(a)
    return layer


def paste_layer(canvas: Image.Image, layer: Image.Image, cx: float, cy: float, rotation=0.0, opacity=1.0):
    layer = apply_opacity(layer, opacity)
    if rotation:
        layer = layer.rotate(-rotation, expand=True, resample=Image.BICUBIC)
    canvas.paste(layer, (int(round(cx - layer.width / 2)), int(round(cy - layer.height / 2))), layer)


def add_shadow(layer: Image.Image, blur: float, dx: float, dy: float, color, opacity: float, pad: int) -> Image.Image:
    """layer already has `pad` transparent margin. Returns layer with a soft shadow beneath."""
    alpha = layer.getchannel("A")
    sh = Image.new("RGBA", layer.size, (color[0], color[1], color[2], 0))
    sh.putalpha(alpha.point(lambda v: int(v * opacity)))
    sh = ImageChops.offset(sh, int(dx), int(dy))
    if blur > 0:
        sh = sh.filter(ImageFilter.GaussianBlur(blur))
    sh.alpha_composite(layer)
    return sh


def draw_shape(canvas, el, W, H):
    x, y, w, h = el["box"]
    px, py, pw, ph = x * W, y * H, max(1, w * W), max(1, h * H)
    pw, ph = int(round(pw)), int(round(ph))
    ss = 2 if (el["type"] == "circle" or el.get("radius", 0) > 0) and pw * ph < 3_000_000 else 1
    fill = el.get("fill", "solid")
    if fill == "gradient" or el["type"] == "gradient":
        arr = gradient_array(pw * ss, ph * ss, el.get("colors"), el.get("angle", 90))
        layer = Image.fromarray(np.clip(arr, 0, 255).astype("uint8"), "RGBA")
        mask = Image.new("L", layer.size, 0)
        md = ImageDraw.Draw(mask)
        if el["type"] == "circle":
            md.ellipse([0, 0, layer.width - 1, layer.height - 1], fill=255)
        else:
            md.rounded_rectangle([0, 0, layer.width - 1, layer.height - 1], radius=el.get("radius", 0) * min(pw, ph) * ss, fill=255)
        layer.putalpha(ImageChops.multiply(layer.getchannel("A"), mask))
    else:
        layer = Image.new("RGBA", (pw * ss, ph * ss), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        col = hex_rgba(el.get("color", "#FFFFFF"))
        ow = int(el.get("outline_width", 0) * min(pw, ph) * ss) if el.get("outline") else 0
        kw = dict(fill=col if not el.get("no_fill") else None, outline=hex_rgba(el["outline"]) if el.get("outline") else None, width=max(ow, 1) if el.get("outline") else 0)
        if el["type"] == "circle":
            d.ellipse([0, 0, layer.width - 1, layer.height - 1], **kw)
        else:
            d.rounded_rectangle([0, 0, layer.width - 1, layer.height - 1], radius=el.get("radius", 0) * min(pw, ph) * ss, **kw)
    if ss > 1:
        layer = layer.resize((pw, ph), Image.LANCZOS)
    paste_layer(canvas, layer, px + pw / 2, py + ph / 2, el.get("rotation", 0), el.get("opacity", 1.0))


def draw_text_layer(fit, box_w, box_h, align, valign, color, letter_spacing, pad):
    layer = Image.new("RGBA", (int(box_w) + 2 * pad, int(box_h) + 2 * pad), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    asc, desc = fit.font.getmetrics()
    block_h = fit.line_pitch * (len(fit.lines) - 1) + asc + desc
    y = pad + {"top": 0, "middle": (box_h - block_h) / 2, "bottom": box_h - block_h}.get(valign, (box_h - block_h) / 2)
    for line in fit.lines:
        lw = line_width(fit.font, line, letter_spacing)
        x = pad + {"left": 0, "center": (box_w - lw) / 2, "right": box_w - lw}.get(align, (box_w - lw) / 2)
        if letter_spacing:
            cx = x
            for ch in line:
                d.text((cx, y), ch, font=fit.font, fill=color, anchor="la")
                cx += fit.font.getlength(ch) + letter_spacing
        else:
            d.text((x, y), line, font=fit.font, fill=color, anchor="la")
        y += fit.line_pitch
    return layer


def render_text_element(canvas, el, text, ctx, warnings, dynamic=True):
    W, H = canvas.size
    side = min(W, H)
    x, y, w, h = el["box"]
    bw, bh = max(8, w * W), max(8, h * H)
    ty = ctx["typo"] if dynamic else {}
    font_spec = ty.get("font_family") or ty.get("font_preset") or el.get("font", "Sans-serif")
    weight = ty.get("weight") or el.get("weight")
    path, warn = resolve(font_spec, weight)
    if warn:
        warnings.append(warn)
    ls = el.get("letter_spacing", 0.0) if ty.get("letter_spacing") is None else ty["letter_spacing"]
    lsp = el.get("line_spacing", 1.2) if ty.get("line_spacing") is None else ty["line_spacing"]
    k = ty.get("size_pct", 100) / 100.0
    max_s, min_s = max(8, int(el.get("max_size", 0.08) * side * k)), max(8, int(el.get("min_size", 0.03) * side * min(k, 1.0)))
    min_s = min(min_s, max_s)
    fit = fit_text(text, path, bw, bh, max_s, min_s, lsp, ls)
    warnings.extend(fit.warnings)
    color = hex_rgba(ty.get("color") or el.get("color", "#FFFFFF"))
    align = ty.get("align") or el.get("align", "center")
    pad = int(side * 0.03)
    layer = draw_text_layer(fit, bw, bh, align, el.get("valign", "middle"), color, fit.letter_spacing, pad)
    sh = el.get("shadow")
    if sh:
        layer = add_shadow(layer, sh.get("blur", 0.006) * side, sh.get("dx", 0) * side, sh.get("dy", 0.004) * side,
                           hex_rgba(sh.get("color", "#000000")), sh.get("opacity", 0.5), pad)
    opacity = el.get("opacity", 1.0) * (ty.get("opacity", 100) / 100.0 if dynamic else 1.0)
    paste_layer(canvas, layer, x * W + bw / 2, y * H + bh / 2, el.get("rotation", 0), opacity)


def draw_brand(canvas, el, brand, warnings, dynamic_pos=True):
    if not brand.get("enabled") or (not brand.get("name") and not brand.get("logo")):
        return
    W, H = canvas.size
    side = min(W, H)
    size = max(10, int(side * 0.032 * el.get("scale", 1.0) * brand.get("size_pct", 100) / 100))
    path, warn = resolve(brand.get("font", "Bold"))
    if warn:
        warnings.append(warn)
    font = load_font(path, size)
    sp = brand.get("letter_spacing", 0.14) * size
    name = (brand.get("name") or "").strip()
    words = name.upper().split()
    colors = brand.get("colors") or ["#FFFFFF"]
    if brand.get("color_mode") == "single":
        colors = colors[:1]
    space = font.getlength(" ") + sp
    widths = [line_width(font, wd, sp) for wd in words]
    text_w = sum(widths) + space * max(0, len(words) - 1)
    asc, desc = font.getmetrics()
    text_h = asc + desc
    logo = None
    if brand.get("logo"):
        try:
            with Image.open(brand["logo"]) as lg:
                lg = lg.convert("RGBA")
            lh = int(text_h * 1.7)
            logo = lg.resize((max(1, int(lg.width * lh / lg.height)), lh), Image.LANCZOS)
        except Exception:
            warnings.append("Logo file missing or unreadable - brand drawn without logo")
    gap = int(size * 0.5) if (logo and words) else 0
    total_w = text_w + (logo.width + gap if logo else 0)
    total_h = max(text_h, logo.height if logo else 0)
    pad = int(size * 0.7)
    layer = Image.new("RGBA", (int(total_w) + 2 * pad, int(total_h) + 2 * pad), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    x = pad
    if logo:
        layer.alpha_composite(logo, (x, pad + (total_h - logo.height) // 2))
        x += logo.width + gap
    for i, wd in enumerate(words):
        col = hex_rgba(colors[i % len(colors)])
        cx, ty = x, pad + (total_h - text_h) / 2
        for ch in wd:
            d.text((cx, ty), ch, font=font, fill=col, anchor="la")
            cx += font.getlength(ch) + sp
        x += widths[i] + space
    pos = el.get("position", "auto")
    pos = brand.get("position", "bottom-center") if pos == "auto" else pos
    m = side * 0.05
    lw, lh = layer.size
    v, hz = ("top" if pos.startswith("top") else "bottom" if pos.startswith("bottom") else "mid"), \
            ("left" if pos.endswith("left") else "right" if pos.endswith("right") else "center")
    cx = {"left": m + lw / 2 - pad, "right": W - m - lw / 2 + pad, "center": W / 2}[hz]
    cy = {"top": m + lh / 2 - pad, "bottom": H - m - lh / 2 + pad, "mid": H / 2}[v]
    # legibility: dark pill on bright areas, soft shadow otherwise
    x0, y0 = int(cx - lw / 2), int(cy - lh / 2)
    region = canvas.crop((max(0, x0), max(0, y0), min(W, x0 + lw), min(H, y0 + lh))).convert("L")
    bright = region.width > 0 and float(np.asarray(region).mean()) > 165
    if brand.get("legibility_pill", True) and bright:
        pill = Image.new("RGBA", (lw, lh), (0, 0, 0, 0))
        ImageDraw.Draw(pill).rounded_rectangle([pad * 0.35, pad * 0.35, lw - pad * 0.35, lh - pad * 0.35], radius=lh // 2, fill=(15, 15, 20, 175))
        pill.alpha_composite(layer)
        layer = pill
    else:
        layer = add_shadow(layer, size * 0.18, 0, size * 0.08, (0, 0, 0), 0.55, pad)
    paste_layer(canvas, layer, cx, cy, 0, brand.get("opacity", 90) / 100.0)


def build_background(el, size, bg_path, seed, warnings):
    W, H = size
    fill = el.get("fill", {"kind": "solid", "color": "#000000"})
    kind = fill.get("kind", "solid")
    img = None
    if bg_path:
        try:
            img = load_background(bg_path, W, H)
        except Exception:
            warnings.append(f"Background unreadable ({Path(bg_path).name}) - used a generated one")
    if img is None and (kind == "photo" or bg_path):
        img = procedural_background(el.get("photo_kind", "nature"), W, H, seed).convert("RGB")
    if img is None:
        if kind == "gradient":
            arr = gradient_array(W, H, fill.get("colors"), fill.get("angle", 135))
            img = Image.fromarray(np.clip(arr[..., :3], 0, 255).astype("uint8"), "RGB")
        else:
            img = Image.new("RGB", (W, H), hex_rgba(fill.get("color", "#000000"))[:3])
    if el.get("blur", 0) > 0:
        img = img.filter(ImageFilter.GaussianBlur(el["blur"] * min(W, H)))
    ov = el.get("overlay") or {}
    if ov.get("opacity", 0) > 0:
        if ov.get("colors"):  # gradient overlay
            arr = gradient_array(W, H, ov["colors"], ov.get("angle", 90))
            lay = Image.fromarray(np.clip(arr, 0, 255).astype("uint8"), "RGBA")
            lay = apply_opacity(lay, ov["opacity"])
            img.paste(lay, (0, 0), lay)
        else:
            img = Image.blend(img, Image.new("RGB", (W, H), hex_rgba(ov.get("color", "#000000"))[:3]), min(1.0, ov["opacity"]))
    vig = el.get("vignette", 0)
    if vig > 0:
        yy, xx = np.mgrid[0:H, 0:W]
        d = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) / 1.414
        f = 1 - vig * np.clip(d, 0, 1) ** 2
        img = Image.fromarray(np.clip(np.asarray(img, float) * f[..., None], 0, 255).astype("uint8"), "RGB")
    return img


def render_quote(quote: dict, template: dict, settings: dict, size: tuple[int, int], bg_path: str | None = None,
                 seed: int = 0, scale: float = 1.0):
    """Returns (PIL.Image RGB, [warnings])."""
    W, H = max(64, int(size[0] * scale)), max(64, int(size[1] * scale))
    warnings: list[str] = []
    typo = settings.get("typography", {})
    brand = {**DEFAULT_BRAND, **settings.get("brand", {})}
    ctx = {"typo": typo}
    els = template.get("elements", [])
    bg_el = next((e for e in els if e.get("type") == "background"), None) or {"fill": {"kind": "solid", "color": "#000000"}}
    canvas = build_background(bg_el, (W, H), bg_path, seed, warnings)
    text = strip_outer_quotes(quote.get("text", ""))
    author = (quote.get("author") or "").strip()
    show_author = settings.get("show_author", True) and author and author.lower() not in ("unknown", "anonymous", "-")
    has_brand_el = False
    for el in els:
        t = el.get("type")
        try:
            if t == "background":
                continue
            if t in ("rect", "circle", "gradient"):
                draw_shape(canvas, el, W, H)
            elif t == "quote":
                case = typo.get("case") or el.get("case", "none")
                body = apply_case(smartify(text), case)
                if el.get("quote_marks", False) and typo.get("quote_marks", True):
                    body = f"\u201c{body}\u201d"
                render_text_element(canvas, el, body, ctx, warnings)
            elif t == "author":
                if show_author:
                    render_text_element(canvas, el, (el.get("prefix", "\u2014 ")) + author, ctx, warnings, dynamic=False)
            elif t == "text":
                render_text_element(canvas, el, el.get("text", ""), ctx, warnings, dynamic=False)
            elif t in ("image", "logo"):
                p = el.get("path") if t == "image" else brand.get("logo")
                if not p:
                    continue
                with Image.open(p) as im:
                    im = im.convert("RGBA")
                x, y, w, h = el["box"]
                bw, bh = int(w * W), int(h * H)
                im.thumbnail((max(1, bw), max(1, bh)), Image.LANCZOS)
                paste_layer(canvas, im, (x + w / 2) * W, (y + h / 2) * H, el.get("rotation", 0), el.get("opacity", 1.0))
            elif t == "brand":
                has_brand_el = True
                draw_brand(canvas, el, brand, warnings)
        except Exception as exc:  # one broken element must not kill the whole image
            warnings.append(f"Element '{t}' skipped: {exc}")
    if not has_brand_el and settings.get("force_brand", False):
        draw_brand(canvas, {"position": "auto"}, brand, warnings)
    return canvas, list(dict.fromkeys(warnings))
