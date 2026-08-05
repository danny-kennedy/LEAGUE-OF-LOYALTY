"""
avatars.py
-----------
Procedural pixel-art game-character avatars, one per player, deterministic by name.

Each avatar is drawn on a tiny 16x18 pixel grid (so it reads as crisp retro pixel
art when scaled up with nearest-neighbour) and returned as a base64 PNG data-URI,
ready to drop into an <img> tag. No external assets, no network — lightweight.

Public API:
    avatar_data_uri(name, scale=6) -> "data:image/png;base64,...."
"""
from __future__ import annotations

import base64
import colorsys
import hashlib
from functools import lru_cache
from io import BytesIO

from PIL import Image, ImageDraw

GW, GH = 16, 18  # grid cells

# palettes -------------------------------------------------------------------
TRIM = ["#F5D76E", "#FFFFFF", "#2D2D3A", "#8ECAE6", "#FFB703", "#FF6B6B"]
SKIN = ["#F1C27D", "#FFD9A8", "#E0AC69", "#C68642", "#8D5524"]
ARCHES = ["knight", "mage", "ranger", "goblin", "robot", "king", "pirate"]


def _seed(name: str) -> int:
    return int(hashlib.md5(name.upper().strip().encode()).hexdigest(), 16)


def _hue_rgba(s: int, light=0.56, sat=0.62) -> tuple:
    r, g, b = colorsys.hls_to_rgb((s % 360) / 360.0, light, sat)
    return (int(r * 255), int(g * 255), int(b * 255), 255)


def _scale(rgba: tuple, f: float) -> tuple:
    return (int(rgba[0] * f), int(rgba[1] * f), int(rgba[2] * f), 255)


def _rgba(hex_color: str) -> tuple:
    h = hex_color.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 255)


def _px(d, x0, y0, x1, y1, color):
    d.rectangle([x0, y0, x1, y1], fill=color)


def _draw(name: str) -> Image.Image:
    s = _seed(name)
    arch = ARCHES[(s >> 11) % len(ARCHES)]
    body_c = _hue_rgba(s >> 3)
    body_d = _scale(body_c, 0.72)
    trim_c = _rgba(TRIM[(s >> 8) % len(TRIM)])
    skin_hex = SKIN[(s >> 13) % len(SKIN)]

    DARK = (43, 43, 58, 255)
    if arch == "goblin":
        skin = (122, 199, 79, 255); skin_d = _scale(skin, 0.72)
    elif arch == "robot":
        skin = (184, 192, 204, 255); skin_d = _scale(skin, 0.72)
    else:
        skin = _rgba(skin_hex); skin_d = _scale(skin, 0.72)

    img = Image.new("RGBA", (GW, GH), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # ---- shadow ----
    _px(d, 4, 17, 11, 17, (0, 0, 0, 60))
    # ---- legs & feet ----
    _px(d, 5, 14, 6, 16, body_d); _px(d, 9, 14, 10, 16, body_d)
    _px(d, 4, 16, 6, 16, DARK);   _px(d, 9, 16, 11, 16, DARK)
    # ---- arms ----
    _px(d, 3, 8, 3, 12, body_d);  _px(d, 12, 8, 12, 12, body_d)
    _px(d, 3, 12, 3, 12, skin);   _px(d, 12, 12, 12, 12, skin)   # hands
    # ---- body / tunic ----
    _px(d, 4, 8, 11, 15, body_c)
    _px(d, 4, 12, 11, 12, trim_c)                                 # belt
    # ---- head ----
    _px(d, 5, 2, 10, 7, skin)
    img.putpixel((5, 2), (0, 0, 0, 0)); img.putpixel((10, 2), (0, 0, 0, 0))
    _px(d, 7, 7, 8, 7, skin_d)                                    # neck shade

    # ---- face ----
    eye = (30, 30, 40, 255)
    if arch == "robot":
        eye = (0, 220, 210, 255)
        _px(d, 6, 4, 6, 4, eye); _px(d, 9, 4, 9, 4, eye)
        _px(d, 6, 6, 9, 6, DARK)                                  # mouth grid
    else:
        _px(d, 6, 4, 6, 5, eye); _px(d, 9, 4, 9, 5, eye)
        _px(d, 7, 6, 8, 6, skin_d)                                # smile
        img.putpixel((5, 5), (255, 150, 150, 130))               # blush
        img.putpixel((10, 5), (255, 150, 150, 130))

    # ---- headgear per archetype ----
    if arch == "knight":
        _px(d, 4, 1, 11, 3, (154, 164, 178, 255))
        _px(d, 4, 3, 4, 5, (154, 164, 178, 255)); _px(d, 11, 3, 11, 5, (154, 164, 178, 255))
        _px(d, 7, 4, 8, 4, (120, 130, 145, 255))                 # visor slit
        _px(d, 7, 0, 8, 0, trim_c)                               # plume
    elif arch == "mage":
        _px(d, 7, 0, 8, 0, body_c); _px(d, 6, 1, 9, 1, body_c)
        _px(d, 5, 2, 10, 2, body_c); _px(d, 4, 3, 11, 3, trim_c)  # brim
        img.putpixel((8, 2), trim_c)                             # star
        _px(d, 5, 7, 10, 8, (240, 240, 240, 255))                # beard
        _px(d, 6, 4, 6, 5, eye); _px(d, 9, 4, 9, 5, eye)
    elif arch == "ranger":
        _px(d, 4, 1, 11, 2, trim_c)
        _px(d, 4, 2, 4, 6, trim_c); _px(d, 11, 2, 11, 6, trim_c)  # hood sides
    elif arch == "goblin":
        _px(d, 3, 3, 4, 4, skin); _px(d, 11, 3, 12, 4, skin)      # pointy ears
        _px(d, 7, 1, 8, 2, body_d)                               # tuft
        img.putpixel((8, 6), (255, 255, 255, 255))               # tooth
    elif arch == "robot":
        _px(d, 8, 0, 8, 1, trim_c); img.putpixel((8, 0), (255, 80, 80, 255))  # antenna
        _px(d, 6, 9, 9, 10, _scale(body_c, 0.85))               # chest panel
    elif arch == "king":
        _px(d, 4, 1, 11, 2, (245, 200, 60, 255))                 # crown band
        for cx in (4, 6, 8, 10):
            _px(d, cx, 0, cx, 0, (245, 200, 60, 255))            # spikes
        img.putpixel((8, 1), (230, 60, 60, 255))                 # gem
    elif arch == "pirate":
        _px(d, 4, 1, 11, 3, (210, 70, 70, 255))                  # bandana
        _px(d, 3, 2, 3, 3, (210, 70, 70, 255))                   # knot
        img.putpixel((9, 4), (20, 20, 20, 255))                  # eyepatch
        img.putpixel((9, 5), (20, 20, 20, 255))
        _px(d, 5, 3, 8, 3, (20, 20, 20, 255))                    # strap

    return img


@lru_cache(maxsize=256)
def avatar_data_uri(name: str, scale: int = 6) -> str:
    img = _draw(name or "?").resize((GW * scale, GH * scale), Image.NEAREST)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def archetype_of(name: str) -> str:
    return ARCHES[(_seed(name) >> 11) % len(ARCHES)]


def _cloud(d, cx, cy, s):
    for dx, dy, r in [(-10, 2, 8), (0, -3, 11), (12, 2, 9), (2, 4, 10)]:
        d.ellipse([cx + (dx - r) * s, cy + (dy - r) * s,
                   cx + (dx + r) * s, cy + (dy + r) * s], fill=(255, 255, 255))


@lru_cache(maxsize=4)
def backdrop_data_uri(w: int = 420, h: int = 190) -> str:
    """A pixel arcade scene: sky, sun, clouds, mountains, pines, grass."""
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    top, bot = (98, 172, 236), (200, 234, 255)
    for y in range(h):                                   # sky gradient
        t = y / h
        d.line([(0, y), (w, y)],
               fill=tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3)))
    d.ellipse([16, 16, 58, 58], fill=(255, 224, 120))    # sun
    d.ellipse([24, 24, 50, 50], fill=(255, 240, 175))
    _cloud(d, 150, 34, 1.0); _cloud(d, 320, 24, 0.8); _cloud(d, 250, 60, 0.6)

    gy = h - 40                                          # ground line
    # far mountains
    for bx in range(-40, w + 80, 130):
        d.polygon([(bx, gy), (bx + 65, gy - 78), (bx + 130, gy)], fill=(126, 152, 165))
    for bx in range(20, w + 80, 120):
        d.polygon([(bx, gy), (bx + 60, gy - 54), (bx + 120, gy)], fill=(96, 140, 130))
    # pine tree line
    for tx in range(6, w, 26):
        th = 20 + (tx * 7 % 10)
        d.polygon([(tx, gy), (tx + 9, gy - th), (tx + 18, gy)], fill=(44, 110, 70))
        d.polygon([(tx + 2, gy - 8), (tx + 9, gy - th - 6), (tx + 16, gy - 8)],
                  fill=(58, 130, 84))
    # grass
    d.rectangle([0, gy, w, h], fill=(122, 190, 96))
    d.rectangle([0, gy, w, gy + 3], fill=(150, 212, 120))

    buf = BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
