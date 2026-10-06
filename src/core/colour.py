"""Colour arithmetic every sport's page checks its colours with.

The same method the NFL's team colours were measured by
(`src/research/verify_matchup_cvd.py`, decided 2026-09-21), moved here so a
sport can use it without importing another sport:

- WCAG 2 relative luminance and contrast ratio;
- colour-vision simulation, Machado, Oliveira & Fernandes (2009) at severity
  1.0, protanopia and deuteranopia (tritanopia is about 1 in 10,000 and does
  not confuse red with green);
- CIEDE2000 colour difference (dE00) from sRGB through CIE Lab (D65).

Standard library only, floats throughout. Say which ruler a figure is on:
the dashboard's chart tests use OKLab distance, not dE00.
"""
from __future__ import annotations

import math
from collections.abc import Sequence

RGB = Sequence[float]

MACHADO: dict[str, tuple[tuple[float, float, float], ...]] = {
    'protanopia': ((0.152286, 1.052583, -0.204868),
                   (0.114503, 0.786281, 0.099216),
                   (-0.003882, -0.048116, 1.051998)),
    'deuteranopia': ((0.367322, 0.860646, -0.227968),
                     (0.280085, 0.672501, 0.047413),
                     (-0.011820, 0.042940, 0.968881)),
}
WHITE = (95.047, 100.0, 108.883)


def hex_to_rgb(h: str) -> tuple[float, float, float]:
    h = h.lstrip('#')
    if len(h) != 6:
        raise ValueError(f'not a #RRGGBB colour: {h!r}')
    return float(int(h[0:2], 16)), float(int(h[2:4], 16)), float(int(h[4:6], 16))


def srgb_to_linear(c: float) -> float:
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def linear_to_srgb(c: float) -> float:
    c = max(0.0, min(1.0, c))
    return (c * 12.92 if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055) * 255.0


def luminance(rgb: RGB) -> float:
    r, g, b = (srgb_to_linear(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: RGB, b: RGB) -> float:
    """WCAG 2 contrast ratio, 1 to 21."""
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def simulate(rgb: RGB, kind: str) -> tuple[float, float, float]:
    m = MACHADO[kind]
    lin = [srgb_to_linear(c) for c in rgb]
    r, g, b = (linear_to_srgb(sum(m[i][j] * lin[j] for j in range(3))) for i in range(3))
    return r, g, b


def rgb_to_lab(rgb: RGB) -> tuple[float, float, float]:
    r, g, b = (srgb_to_linear(c) for c in rgb)
    x = (0.4124564 * r + 0.3575761 * g + 0.1804375 * b) * 100
    y = (0.2126729 * r + 0.7151522 * g + 0.0721750 * b) * 100
    z = (0.0193339 * r + 0.1191920 * g + 0.9503041 * b) * 100

    def f(t: float) -> float:
        return t ** (1 / 3) if t > 216 / 24389 else (841 / 108) * t + 4 / 29

    fx, fy, fz = f(x / WHITE[0]), f(y / WHITE[1]), f(z / WHITE[2])
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def ciede2000(lab1: RGB, lab2: RGB) -> float:
    L1, a1, b1 = lab1
    L2, a2, b2 = lab2
    C1, C2 = math.hypot(a1, b1), math.hypot(a2, b2)
    Cb = (C1 + C2) / 2
    G = 0.5 * (1 - math.sqrt(Cb ** 7 / (Cb ** 7 + 25 ** 7))) if Cb > 0 else 0.5
    a1p, a2p = (1 + G) * a1, (1 + G) * a2
    C1p, C2p = math.hypot(a1p, b1), math.hypot(a2p, b2)
    h1p = math.degrees(math.atan2(b1, a1p)) % 360 if (a1p or b1) else 0.0
    h2p = math.degrees(math.atan2(b2, a2p)) % 360 if (a2p or b2) else 0.0
    dLp, dCp = L2 - L1, C2p - C1p
    if C1p * C2p == 0:
        dhp = 0.0
    elif abs(h2p - h1p) <= 180:
        dhp = h2p - h1p
    else:
        dhp = h2p - h1p - 360 if h2p > h1p else h2p - h1p + 360
    dHp = 2 * math.sqrt(C1p * C2p) * math.sin(math.radians(dhp) / 2)
    Lbp, Cbp = (L1 + L2) / 2, (C1p + C2p) / 2
    if C1p * C2p == 0:
        hbp = h1p + h2p
    elif abs(h1p - h2p) <= 180:
        hbp = (h1p + h2p) / 2
    elif h1p + h2p < 360:
        hbp = (h1p + h2p + 360) / 2
    else:
        hbp = (h1p + h2p - 360) / 2
    T = (1 - 0.17 * math.cos(math.radians(hbp - 30)) + 0.24 * math.cos(math.radians(2 * hbp))
         + 0.32 * math.cos(math.radians(3 * hbp + 6)) - 0.20 * math.cos(math.radians(4 * hbp - 63)))
    dTheta = 30 * math.exp(-(((hbp - 275) / 25) ** 2))
    Rc = 2 * math.sqrt(Cbp ** 7 / (Cbp ** 7 + 25 ** 7)) if Cbp > 0 else 0.0
    Sl = 1 + (0.015 * (Lbp - 50) ** 2) / math.sqrt(20 + (Lbp - 50) ** 2)
    Sc, Sh = 1 + 0.045 * Cbp, 1 + 0.015 * Cbp * T
    Rt = -math.sin(math.radians(2 * dTheta)) * Rc
    return math.sqrt((dLp / Sl) ** 2 + (dCp / Sc) ** 2 + (dHp / Sh) ** 2 + Rt * (dCp / Sc) * (dHp / Sh))


#: The dashboard's `CONTRAST_THRESHOLD` (src/dashboard/app.js): two colours
#: closer than this in plain RGB distance are pushed apart on a game's bar.
PUSH_THRESHOLD = 90.0


def matchup_push(away: str, home: str, threshold: float = PUSH_THRESHOLD
                 ) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    """What the board's `matchupColors(away, home)` draws: when the two
    colours are close, the away one darkened and the home one lightened, the
    closer the more. Float RGB, unrounded, as the NFL's script measures it."""
    a, h = hex_to_rgb(away), hex_to_rgb(home)
    dist = math.dist(a, h)
    if dist >= threshold:
        return a, h
    push = 0.35 * (1 - dist / threshold) + 0.2

    def shade(rgb: tuple[float, float, float], amount: float) -> tuple[float, float, float]:
        target = 255.0 if amount > 0 else 0.0
        r, g, b = (c + (target - c) * abs(amount) for c in rgb)
        return r, g, b

    return shade(a, -push), shade(h, push)


def de00(a: RGB, b: RGB) -> float:
    """dE00 between two sRGB colours under normal vision."""
    return ciede2000(rgb_to_lab(a), rgb_to_lab(b))


def worst_cvd_de00(a: RGB, b: RGB) -> float:
    """The smaller dE00 of the pair under protanopia and under deuteranopia."""
    return min(ciede2000(rgb_to_lab(simulate(a, k)), rgb_to_lab(simulate(b, k))) for k in MACHADO)
