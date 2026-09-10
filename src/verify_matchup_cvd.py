"""Regenerate the colour-vision figures quoted in the game-card comment.

Why this file exists. PR #52 shipped "115 of 992 team/theme pairs sit under the
dE00 15 floor ... and 15 are effectively identical" as a permanent comment in
`src/dashboard_template.html`. Booth re-ran the stated method and got 71 and 9.
Neither number could be checked against anything, because the original was
computed in a browser against rendered pixels and no script was kept. The repo
has been here before: `src/verify_low_confidence_finding.py` exists because
Booth flagged exactly this on PR #18. Same fix.

Every choice the number depends on is named here rather than left to the reader:

  UNIT. A card renders one ORDERED matchup. `matchupColors(away, home)` darkens
  the away segment and lightens the home one, so (NE, SEA) and (SEA, NE) are
  different colour pairs. The 32 teams give 32*31 = 992 ordered matchups, which
  is every game that can appear on a card. Counting unordered pairs instead
  gives C(32,2) = 496 -- and 496 x 2 CVD types is also 992, which is not a
  coincidence but is a genuine trap: the same total, over different objects.
  Both are reported below so the two can never be confused again.

  SEVERITY. Machado, Oliveira & Fernandes (2009), severity 1.00 -- full
  dichromacy. Protanopia and deuteranopia only; tritanopia is ~1 in 10,000 and
  does not confuse red/green.

  WORST CASE. Per matchup, the score is the MINIMUM dE00 across the two CVD
  types. A bar is only as readable as its worst common reader.

  FLOOR. dE00 >= 15 is the dataviz skill's normal-vision floor for adjacent
  categorical fills, applied here under simulation. dE00 < 5 is "effectively
  identical".

  ARITHMETIC. Float throughout, in linear-light RGB for the CVD transform. The
  browser rounds to 8 bits at each step, which is why the original run could
  differ on pairs sitting near a threshold -- but rounding does not move a
  count by 44, and the shipped comment is corrected to what this prints.

Run: python src/verify_matchup_cvd.py
"""
from itertools import permutations, combinations
import math
import re
import sys
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent / 'dashboard_template.html'

# --- the palette and the transform, read from the template rather than copied
# so this file cannot drift from the code it describes ----------------------


def team_colors():
    src = TEMPLATE.read_text(encoding='utf-8')
    block = re.search(r'const TEAM_COLOR = \{(.*?)\};', src, re.S).group(1)
    pairs = re.findall(r"(\w+)\s*:\s*'(#[0-9A-Fa-f]{6})'", block)
    return dict(pairs)


def threshold():
    src = TEMPLATE.read_text(encoding='utf-8')
    return float(re.search(r'const CONTRAST_THRESHOLD\s*=\s*([\d.]+)', src).group(1))


CONTRAST_THRESHOLD = threshold()


def hex_to_rgb(h):
    h = h.lstrip('#')
    return [int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)]


def color_distance(a, b):
    (r1, g1, b1), (r2, g2, b2) = hex_to_rgb(a), hex_to_rgb(b)
    return math.sqrt((r1 - r2) ** 2 + (g1 - g2) ** 2 + (b1 - b2) ** 2)


def shade(h, amount):
    r, g, b = hex_to_rgb(h)
    target = 255.0 if amount > 0 else 0.0
    t = abs(amount)
    return [r + (target - r) * t, g + (target - g) * t, b + (target - b) * t]


def matchup_colors(away_hex, home_hex):
    """Port of matchupColors(). Returns float RGB 0-255, unrounded."""
    dist = color_distance(away_hex, home_hex)
    if dist < CONTRAST_THRESHOLD:
        push = 0.35 * (1 - dist / CONTRAST_THRESHOLD) + 0.2
        return shade(away_hex, -push), shade(home_hex, push)
    return [float(c) for c in hex_to_rgb(away_hex)], [float(c) for c in hex_to_rgb(home_hex)]


# --- Machado 2009, severity 1.0 -------------------------------------------
MACHADO = {
    'protanopia': [[0.152286, 1.052583, -0.204868],
                   [0.114503, 0.786281, 0.099216],
                   [-0.003882, -0.048116, 1.051998]],
    'deuteranopia': [[0.367322, 0.860646, -0.227968],
                     [0.280085, 0.672501, 0.047413],
                     [-0.011820, 0.042940, 0.968881]],
}


def srgb_to_linear(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def linear_to_srgb(c):
    c = max(0.0, min(1.0, c))
    return (c * 12.92 if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055) * 255.0


def simulate(rgb, kind):
    m = MACHADO[kind]
    lin = [srgb_to_linear(c) for c in rgb]
    out = [sum(m[i][j] * lin[j] for j in range(3)) for i in range(3)]
    return [linear_to_srgb(c) for c in out]


# --- sRGB -> Lab -> CIEDE2000 ---------------------------------------------
WHITE = (95.047, 100.0, 108.883)


def rgb_to_lab(rgb):
    r, g, b = (srgb_to_linear(c) for c in rgb)
    x = (0.4124564 * r + 0.3575761 * g + 0.1804375 * b) * 100
    y = (0.2126729 * r + 0.7151522 * g + 0.0721750 * b) * 100
    z = (0.0193339 * r + 0.1191920 * g + 0.9503041 * b) * 100

    def f(t):
        return t ** (1 / 3) if t > 216 / 24389 else (841 / 108) * t + 4 / 29

    fx, fy, fz = f(x / WHITE[0]), f(y / WHITE[1]), f(z / WHITE[2])
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def ciede2000(lab1, lab2):
    L1, a1, b1 = lab1
    L2, a2, b2 = lab2
    kL = kC = kH = 1.0
    C1, C2 = math.hypot(a1, b1), math.hypot(a2, b2)
    Cb = (C1 + C2) / 2
    G = 0.5 * (1 - math.sqrt(Cb ** 7 / (Cb ** 7 + 25 ** 7))) if Cb > 0 else 0.5
    a1p, a2p = (1 + G) * a1, (1 + G) * a2
    C1p, C2p = math.hypot(a1p, b1), math.hypot(a2p, b2)
    h1p = math.degrees(math.atan2(b1, a1p)) % 360 if (a1p or b1) else 0.0
    h2p = math.degrees(math.atan2(b2, a2p)) % 360 if (a2p or b2) else 0.0

    dLp = L2 - L1
    dCp = C2p - C1p
    if C1p * C2p == 0:
        dhp = 0.0
    elif abs(h2p - h1p) <= 180:
        dhp = h2p - h1p
    else:
        dhp = h2p - h1p - 360 if h2p > h1p else h2p - h1p + 360
    dHp = 2 * math.sqrt(C1p * C2p) * math.sin(math.radians(dhp) / 2)

    Lbp = (L1 + L2) / 2
    Cbp = (C1p + C2p) / 2
    if C1p * C2p == 0:
        hbp = h1p + h2p
    elif abs(h1p - h2p) <= 180:
        hbp = (h1p + h2p) / 2
    elif h1p + h2p < 360:
        hbp = (h1p + h2p + 360) / 2
    else:
        hbp = (h1p + h2p - 360) / 2

    T = (1 - 0.17 * math.cos(math.radians(hbp - 30))
         + 0.24 * math.cos(math.radians(2 * hbp))
         + 0.32 * math.cos(math.radians(3 * hbp + 6))
         - 0.20 * math.cos(math.radians(4 * hbp - 63)))
    dTheta = 30 * math.exp(-(((hbp - 275) / 25) ** 2))
    Rc = 2 * math.sqrt(Cbp ** 7 / (Cbp ** 7 + 25 ** 7)) if Cbp > 0 else 0.0
    Sl = 1 + (0.015 * (Lbp - 50) ** 2) / math.sqrt(20 + (Lbp - 50) ** 2)
    Sc = 1 + 0.045 * Cbp
    Sh = 1 + 0.015 * Cbp * T
    Rt = -math.sin(math.radians(2 * dTheta)) * Rc

    return math.sqrt((dLp / (kL * Sl)) ** 2 + (dCp / (kC * Sc)) ** 2
                     + (dHp / (kH * Sh)) ** 2
                     + Rt * (dCp / (kC * Sc)) * (dHp / (kH * Sh)))


def worst_dE(away_hex, home_hex):
    """Minimum dE00 across protanopia and deuteranopia, post-adjustment."""
    a, h = matchup_colors(away_hex, home_hex)
    return min(ciede2000(rgb_to_lab(simulate(a, k)), rgb_to_lab(simulate(h, k)))
               for k in MACHADO)


def report():
    tc = team_colors()
    teams = sorted(tc)
    print(f"teams: {len(teams)}   CONTRAST_THRESHOLD: {CONTRAST_THRESHOLD:g}")
    print("CVD: Machado 2009 severity 1.0, protanopia + deuteranopia")
    print("score per matchup: min dE00 across the two types, after matchupColors()\n")

    ordered = [(a, h, worst_dE(tc[a], tc[h])) for a, h in permutations(teams, 2)]
    under15 = [x for x in ordered if x[2] < 15]
    under5 = [x for x in ordered if x[2] < 5]

    print(f"UNIT A -- ordered matchups (away, home), every game a card can show")
    print(f"  total          : {len(ordered)}")
    print(f"  dE00 < 15      : {len(under15)}  ({len(under15) / len(ordered) * 100:.1f}%)")
    print(f"  dE00 < 5       : {len(under5)}\n")

    unordered = list(combinations(teams, 2))
    each = [(a, b, k, ciede2000(
        rgb_to_lab(simulate(matchup_colors(tc[a], tc[b])[0], k)),
        rgb_to_lab(simulate(matchup_colors(tc[a], tc[b])[1], k))))
        for a, b in unordered for k in MACHADO]
    u15 = [x for x in each if x[3] < 15]
    u5 = [x for x in each if x[3] < 5]
    print(f"UNIT B -- unordered pairs x 2 CVD types (Booth's reading; same total)")
    print(f"  total          : {len(each)}")
    print(f"  dE00 < 15      : {len(u15)}  ({len(u15) / len(each) * 100:.1f}%)")
    print(f"  dE00 < 5       : {len(u5)}\n")

    print("worst ordered matchups (away @ home, min dE00):")
    for a, h, d in sorted(ordered, key=lambda x: x[2])[:8]:
        print(f"  {a:>3} @ {h:<3}  {d:5.2f}")

    print("\nworst unordered pairs (min dE00 over both orderings and both types):")
    best = {}
    for a, h, d in ordered:
        key = tuple(sorted((a, h)))
        best[key] = min(best.get(key, 1e9), d)
    for (a, b), d in sorted(best.items(), key=lambda x: x[1])[:8]:
        print(f"  {a}/{b}  {d:5.2f}")

    # UNIT C is the one the comment quotes: distinct team pairs, worst case over
    # both orderings and both CVD types. It avoids the 992 collision entirely,
    # because its denominator is 496 and can be confused with nothing else.
    p15 = sorted(d for d in best.values() if d < 15)
    p5 = [d for d in best.values() if d < 5]
    print(f"\nUNIT C -- distinct team pairs, worst case over ordering and CVD type")
    print(f"  total          : {len(best)}")
    print(f"  dE00 < 15      : {len(p15)}  ({len(p15) / len(best) * 100:.1f}%)")
    print(f"  dE00 < 5       : {len(p5)}")

    near = sorted((d for d in best.values() if 14.0 < d < 16.0))
    print(f"\npairs within 1 dE00 of the 15 floor (why two honest runs can differ by one):")
    print("  " + ", ".join(f"{d:.2f}" for d in near) or "  none")
    return len(best), len(p15), len(p5)


if __name__ == '__main__':
    report()
    sys.exit(0)
