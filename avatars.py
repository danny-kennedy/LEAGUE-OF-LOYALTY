"""
avatars.py
-----------
Procedural pixel-art game-character avatars. Each player's look is driven by
(archetype, gender) which live in player_profiles.csv, so a player's avatar can be
changed just by editing that sheet. Colour is derived from the player's name+pod so
every player is visually unique even when two share an archetype.

Public API:
    list_archetypes()                                  -> [keys...]
    archetype_display(key, gender)                     -> "Valkyrie" / "Wizard" ...
    avatar_data_uri(archetype, gender, seed, scale=6)  -> "data:image/png;base64,..."
    backdrop_data_uri(theme)                           -> scene PNG data-URI
"""
from __future__ import annotations

import base64
import colorsys
import hashlib
from functools import lru_cache
from io import BytesIO

from PIL import Image, ImageDraw

GW, GH = 16, 18

ARCH_NAME = {
    "knight":  ("Knight", "Valkyrie"),
    "mage":    ("Wizard", "Sorceress"),
    "ranger":  ("Ranger", "Huntress"),
    "royal":   ("King", "Queen"),
    "pirate":  ("Pirate", "Corsair"),
    "ninja":   ("Ninja", "Kunoichi"),
    "viking":  ("Viking", "Shieldmaiden"),
    "robot":   ("Mecha", "Gynoid"),
    "goblin":  ("Goblin", "Sprite"),
    "druid":   ("Druid", "Enchantress"),
    "samurai": ("Samurai", "Onna-Musha"),
    "pharaoh": ("Pharaoh", "Cleopatra"),
    "bard":    ("Bard", "Muse"),
    "paladin": ("Paladin", "Templar"),
}
ARCHES = list(ARCH_NAME.keys())
COVERING = {"ninja", "robot", "pharaoh"}

SKIN = ["#F1C27D", "#FFD9A8", "#E0AC69", "#C68642", "#8D5524"]
HAIR = [(58, 40, 30), (30, 30, 36), (188, 146, 66), (150, 60, 40), (96, 64, 44)]
TRIM = ["#F5D76E", "#FFFFFF", "#2D2D3A", "#8ECAE6", "#FFB703", "#FF6B6B"]


def list_archetypes():
    return list(ARCHES)


def archetype_display(key, gender):
    m, f = ARCH_NAME.get((key or "knight").lower(), ("Adventurer", "Adventurer"))
    return f if str(gender).upper().startswith("F") else m


def _seed(text):
    return int(hashlib.md5(str(text).upper().strip().encode()).hexdigest(), 16)


def _hue(s, light=0.56, sat=0.62):
    r, g, b = colorsys.hls_to_rgb((s % 360) / 360.0, light, sat)
    return (int(r * 255), int(g * 255), int(b * 255), 255)


def _scale(c, f):
    return (int(c[0] * f), int(c[1] * f), int(c[2] * f), 255)


def _rgba(h):
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 255)


def _px(d, x0, y0, x1, y1, c):
    d.rectangle([x0, y0, x1, y1], fill=c)


def _draw(archetype, gender, seed):
    arch = (archetype or "knight").lower()
    if arch not in ARCH_NAME:
        arch = "knight"
    female = str(gender).upper().startswith("F")

    body = _hue(seed >> 3)
    body_d = _scale(body, 0.72)
    trim = _rgba(TRIM[(seed >> 8) % len(TRIM)])
    hair = HAIR[(seed >> 4) % len(HAIR)] + (255,)
    if arch == "goblin":
        skin = (122, 199, 79, 255)
    elif arch == "robot":
        skin = (188, 196, 208, 255)
    else:
        skin = _rgba(SKIN[(seed >> 13) % len(SKIN)])
    skin_d = _scale(skin, 0.75)
    DARK = (40, 40, 55, 255)

    img = Image.new("RGBA", (GW, GH), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    _px(d, 4, 17, 11, 17, (0, 0, 0, 55))
    _px(d, 5, 14, 6, 16, body_d); _px(d, 9, 14, 10, 16, body_d)
    _px(d, 4, 16, 6, 16, DARK); _px(d, 9, 16, 11, 16, DARK)
    _px(d, 3, 8, 3, 12, body_d); _px(d, 12, 8, 12, 12, body_d)
    _px(d, 3, 12, 3, 12, skin); _px(d, 12, 12, 12, 12, skin)
    _px(d, 4, 8, 11, 15, body)
    _px(d, 4, 12, 11, 12, trim)

    if female and arch not in COVERING:
        _px(d, 4, 3, 4, 10, hair); _px(d, 11, 3, 11, 10, hair)
        _px(d, 5, 2, 10, 2, hair)

    _px(d, 5, 2, 10, 7, skin)
    img.putpixel((5, 2), (0, 0, 0, 0)); img.putpixel((10, 2), (0, 0, 0, 0))
    _px(d, 7, 7, 8, 7, skin_d)

    eye = (0, 220, 210, 255) if arch == "robot" else (34, 34, 46, 255)
    _px(d, 6, 4, 6, 5, eye); _px(d, 9, 4, 9, 5, eye)
    if female:
        img.putpixel((5, 4), eye); img.putpixel((10, 4), eye)
        _px(d, 7, 6, 8, 6, (222, 96, 110, 255))
        img.putpixel((5, 5), (255, 150, 150, 130)); img.putpixel((10, 5), (255, 150, 150, 130))
    else:
        _px(d, 7, 6, 8, 6, skin_d)

    GREY = (156, 166, 180, 255)
    if arch == "knight":
        _px(d, 4, 1, 11, 3, GREY); _px(d, 4, 3, 4, 5, GREY); _px(d, 11, 3, 11, 5, GREY)
        _px(d, 7, 4, 8, 4, _scale(GREY, 0.7)); _px(d, 7, 0, 8, 0, trim)
    elif arch == "mage":
        _px(d, 7, 0, 8, 0, body); _px(d, 6, 1, 9, 1, body)
        _px(d, 5, 2, 10, 2, body); _px(d, 4, 3, 11, 3, trim); img.putpixel((8, 2), trim)
        _px(d, 6, 4, 6, 5, eye); _px(d, 9, 4, 9, 5, eye)
        if not female:
            _px(d, 5, 7, 10, 8, (238, 238, 238, 255))
    elif arch == "ranger":
        _px(d, 4, 1, 11, 2, trim); _px(d, 4, 2, 4, 6, trim); _px(d, 11, 2, 11, 6, trim)
    elif arch == "royal":
        _px(d, 4, 1, 11, 2, (245, 200, 60, 255))
        for cx in (4, 6, 8, 10):
            img.putpixel((cx, 0), (245, 200, 60, 255))
        img.putpixel((8, 1), (230, 60, 60, 255))
    elif arch == "pirate":
        _px(d, 4, 1, 11, 3, (206, 66, 66, 255)); _px(d, 3, 2, 3, 3, (206, 66, 66, 255))
        img.putpixel((9, 4), (18, 18, 18, 255)); img.putpixel((9, 5), (18, 18, 18, 255))
        _px(d, 5, 3, 8, 3, (18, 18, 18, 255))
    elif arch == "ninja":
        _px(d, 4, 2, 11, 7, DARK); _px(d, 4, 4, 11, 5, skin)
        _px(d, 6, 4, 6, 5, eye); _px(d, 9, 4, 9, 5, eye); _px(d, 4, 3, 11, 3, trim)
    elif arch == "viking":
        _px(d, 4, 2, 11, 3, (150, 120, 80, 255))
        _px(d, 3, 1, 4, 2, (238, 238, 238, 255)); _px(d, 11, 1, 12, 2, (238, 238, 238, 255))
    elif arch == "robot":
        _px(d, 8, 0, 8, 1, trim)
        img.putpixel((8, 0), (255, 120, 200, 255) if female else (255, 90, 90, 255))
        _px(d, 6, 6, 9, 6, DARK); _px(d, 6, 9, 9, 10, _scale(body, 0.85))
    elif arch == "goblin":
        _px(d, 3, 3, 4, 4, skin); _px(d, 11, 3, 12, 4, skin)
        _px(d, 7, 1, 8, 2, body_d); img.putpixel((8, 6), (255, 255, 255, 255))
    elif arch == "druid":
        _px(d, 4, 2, 11, 3, (70, 130, 70, 255))
        img.putpixel((4, 1), (90, 160, 80, 255)); img.putpixel((11, 1), (90, 160, 80, 255))
        img.putpixel((7, 1), (120, 200, 90, 255)); img.putpixel((8, 1), (120, 200, 90, 255))
    elif arch == "samurai":
        _px(d, 4, 2, 11, 3, DARK); _px(d, 6, 0, 9, 0, (230, 190, 70, 255))
        img.putpixel((7, 1), (230, 190, 70, 255)); img.putpixel((8, 1), (230, 190, 70, 255))
    elif arch == "pharaoh":
        _px(d, 4, 2, 11, 6, (70, 110, 200, 255))
        for xx in (5, 7, 9):
            _px(d, xx, 2, xx, 6, (235, 205, 70, 255))
        _px(d, 5, 2, 10, 2, (235, 205, 70, 255))
        _px(d, 6, 4, 6, 5, eye); _px(d, 9, 4, 9, 5, eye)
    elif arch == "bard":
        _px(d, 4, 2, 11, 3, (140, 70, 160, 255)); _px(d, 11, 1, 12, 2, (240, 230, 90, 255))
    elif arch == "paladin":
        _px(d, 4, 2, 11, 3, GREY)
        img.putpixel((7, 0), (255, 240, 150, 255)); img.putpixel((8, 0), (255, 240, 150, 255))
        _px(d, 3, 2, 3, 3, (255, 255, 255, 255)); _px(d, 12, 2, 12, 3, (255, 255, 255, 255))
    return img


@lru_cache(maxsize=512)
def avatar_data_uri(archetype, gender, seed, scale=6):
    img = _draw(archetype, gender, _seed(seed)).resize((GW * scale, GH * scale), Image.NEAREST)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def _cloud(d, cx, cy, s, col=(255, 255, 255)):
    for dx, dy, r in [(-10, 2, 8), (0, -3, 11), (12, 2, 9), (2, 4, 10)]:
        d.ellipse([cx + (dx - r) * s, cy + (dy - r) * s,
                   cx + (dx + r) * s, cy + (dy + r) * s], fill=col)


def _grad(d, w, h, top, bot):
    for y in range(h):
        t = y / h
        d.line([(0, y), (w, y)],
               fill=tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3)))


@lru_cache(maxsize=8)
def backdrop_data_uri(theme="arcade", w=420, h=190):
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    gy = h - 40

    if theme == "stadium":
        _grad(d, w, h, (46, 34, 92), (232, 132, 120))
        d.ellipse([w - 90, 20, w - 30, 80], fill=(255, 196, 120))
        for bx in range(-40, w + 80, 120):
            d.polygon([(bx, gy), (bx + 60, gy - 46), (bx + 120, gy)], fill=(70, 58, 120))
        d.rectangle([0, gy, w, h], fill=(88, 70, 130))
        d.rectangle([0, gy, w, gy + 3], fill=(150, 120, 190))
        for lx in range(20, w, 60):
            d.rectangle([lx, gy + 6, lx + 2, h], fill=(120, 100, 160))
    elif theme == "cosmos":
        _grad(d, w, h, (10, 12, 40), (36, 24, 70))
        rnd = 1234567
        for _ in range(70):
            rnd = (1103515245 * rnd + 12345) & 0x7fffffff; x = rnd % w
            rnd = (1103515245 * rnd + 12345) & 0x7fffffff; y = rnd % (gy - 4)
            d.point((x, y), fill=(255, 255, 255))
        d.ellipse([40, 24, 84, 68], fill=(226, 224, 250))
        d.ellipse([52, 24, 96, 68], fill=(10, 12, 40))
        d.rectangle([0, gy, w, h], fill=(28, 22, 58)); d.rectangle([0, gy, w, gy + 3], fill=(120, 90, 200))
    elif theme == "lava":
        _grad(d, w, h, (26, 12, 16), (86, 24, 20))
        for bx in range(-30, w + 60, 110):
            d.polygon([(bx, gy), (bx + 55, gy - 70), (bx + 110, gy)], fill=(40, 22, 26))
        d.rectangle([0, gy, w, h], fill=(150, 40, 18))
        d.rectangle([0, gy, w, gy + 4], fill=(255, 170, 40)); d.rectangle([0, gy + 4, w, gy + 7], fill=(255, 100, 20))
        for gx in range(10, w, 34):
            d.point((gx, gy - 6), fill=(255, 210, 90))
    else:
        _grad(d, w, h, (98, 172, 236), (200, 234, 255))
        d.ellipse([16, 16, 58, 58], fill=(255, 224, 120)); d.ellipse([24, 24, 50, 50], fill=(255, 240, 175))
        _cloud(d, 150, 34, 1.0); _cloud(d, 320, 24, 0.8); _cloud(d, 250, 60, 0.6)
        for bx in range(-40, w + 80, 130):
            d.polygon([(bx, gy), (bx + 65, gy - 78), (bx + 130, gy)], fill=(126, 152, 165))
        for bx in range(20, w + 80, 120):
            d.polygon([(bx, gy), (bx + 60, gy - 54), (bx + 120, gy)], fill=(96, 140, 130))
        for tx in range(6, w, 26):
            th = 20 + (tx * 7 % 10)
            d.polygon([(tx, gy), (tx + 9, gy - th), (tx + 18, gy)], fill=(44, 110, 70))
        d.rectangle([0, gy, w, h], fill=(122, 190, 96)); d.rectangle([0, gy, w, gy + 3], fill=(150, 212, 120))

    buf = BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
