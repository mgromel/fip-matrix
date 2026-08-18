"""Verify every colour claim the README and config.py make.

The palette lives in config.py and the theme in .streamlit/config.toml; this
script reads both rather than restating any hex, so it cannot drift from them.

Run from anywhere:

    python tools/check_palette.py

Exit code 0 if every hard check passes, 1 otherwise. Lines marked INFO are
documented trade-offs rather than failures, and say so inline.

No dependencies beyond the standard library and config.py's own numpy.
"""

from __future__ import annotations

import itertools
import math
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config import (  # noqa: E402
    SEQUENTIAL,
    SERIES,
    SERIES_ALT,
    SERIES_FILL,
    STATUS_COLORS,
    STATUS_LABELS,
)

# --- Thresholds --------------------------------------------------------------
# The project's stated rules, in one place so a change is a deliberate edit.

DE_FLOOR = 15.0  # minimum separation between any two meaning-bearing colours
CONTRAST_SERIES = 3.0  # chart marks, on the surface they are read against
CONTRAST_INK = 4.5  # a button label against its own primaryColor fill
HUE_SPREAD = 15.0  # degrees a single-hue ramp may wander

# --- Colour space ------------------------------------------------------------


def channels(hex_colour: str) -> list[float]:
    h = hex_colour.lstrip("#")
    return [int(h[i : i + 2], 16) / 255 for i in (0, 2, 4)]


def _to_linear(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _from_linear(c: float) -> float:
    return c * 12.92 if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


def linear_rgb(hex_colour: str) -> list[float]:
    return [_to_linear(c) for c in channels(hex_colour)]


def to_hex(rgb: list[float]) -> str:
    clamped = [max(0.0, min(1.0, c)) for c in rgb]
    return "#%02x%02x%02x" % tuple(round(_from_linear(c) * 255) for c in clamped)


def relative_luminance(hex_colour: str) -> float:
    r, g, b = linear_rgb(hex_colour)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: str, b: str) -> float:
    """WCAG 2.x contrast ratio."""
    la, lb = relative_luminance(a), relative_luminance(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def lab(hex_colour: str) -> tuple[float, float, float]:
    """CIELAB under D65."""
    r, g, b = linear_rgb(hex_colour)
    x = 0.4124 * r + 0.3576 * g + 0.1805 * b
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    z = 0.0193 * r + 0.1192 * g + 0.9505 * b

    def f(t: float) -> float:
        return t ** (1 / 3) if t > 216 / 24389 else (841 / 108) * t + 4 / 29

    fx, fy, fz = f(x / 0.95047), f(y / 1.0), f(z / 1.08883)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def oklch(hex_colour: str) -> tuple[float, float, float]:
    """OKLCH lightness, chroma, hue -- the space SEQUENTIAL is checked in."""
    r, g, b = linear_rgb(hex_colour)
    lms = (
        0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b,
        0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b,
        0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b,
    )
    l_, m_, s_ = (math.copysign(abs(v) ** (1 / 3), v) for v in lms)
    lightness = 0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_
    a = 1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
    b_ = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_
    return lightness, math.hypot(a, b_), math.degrees(math.atan2(b_, a)) % 360


def de76(a: str, b: str) -> float:
    return math.dist(lab(a), lab(b))


def de2000(a: str, b: str) -> float:
    """CIEDE2000. Stricter than dE76, and the two disagree, so both are reported."""
    l1, a1, b1 = lab(a)
    l2, a2, b2 = lab(b)
    c1, c2 = math.hypot(a1, b1), math.hypot(a2, b2)
    c_bar = (c1 + c2) / 2
    g = 0.5 * (1 - math.sqrt(c_bar**7 / (c_bar**7 + 25**7))) if c_bar else 0.5
    a1p, a2p = (1 + g) * a1, (1 + g) * a2
    c1p, c2p = math.hypot(a1p, b1), math.hypot(a2p, b2)
    h1 = math.degrees(math.atan2(b1, a1p)) % 360
    h2 = math.degrees(math.atan2(b2, a2p)) % 360

    d_lp, d_cp = l2 - l1, c2p - c1p
    if c1p * c2p == 0:
        d_h = 0.0
    elif abs(h2 - h1) <= 180:
        d_h = h2 - h1
    else:
        d_h = h2 - h1 + (360 if h2 <= h1 else -360)
    d_hp = 2 * math.sqrt(c1p * c2p) * math.sin(math.radians(d_h) / 2)

    l_bar, c_bar_p = (l1 + l2) / 2, (c1p + c2p) / 2
    if c1p * c2p == 0:
        h_bar = h1 + h2
    elif abs(h1 - h2) <= 180:
        h_bar = (h1 + h2) / 2
    else:
        h_bar = (h1 + h2 + (360 if h1 + h2 < 360 else -360)) / 2

    t = (
        1
        - 0.17 * math.cos(math.radians(h_bar - 30))
        + 0.24 * math.cos(math.radians(2 * h_bar))
        + 0.32 * math.cos(math.radians(3 * h_bar + 6))
        - 0.20 * math.cos(math.radians(4 * h_bar - 63))
    )
    s_l = 1 + (0.015 * (l_bar - 50) ** 2) / math.sqrt(20 + (l_bar - 50) ** 2)
    s_c = 1 + 0.045 * c_bar_p
    s_h = 1 + 0.015 * c_bar_p * t
    r_c = 2 * math.sqrt(c_bar_p**7 / (c_bar_p**7 + 25**7)) if c_bar_p else 0.0
    delta_theta = 30 * math.exp(-(((h_bar - 275) / 25) ** 2))
    r_t = -math.sin(math.radians(2 * delta_theta)) * r_c
    return math.sqrt(
        (d_lp / s_l) ** 2
        + (d_cp / s_c) ** 2
        + (d_hp / s_h) ** 2
        + r_t * (d_cp / s_c) * (d_hp / s_h)
    )


# --- Colour-vision deficiency ------------------------------------------------
# Vienot, Brettel & Mollon (1999) dichromat projection, applied to linear RGB.

RGB_TO_LMS = (
    (17.8824, 43.5161, 4.11935),
    (3.45565, 27.1554, 3.86714),
    (0.0299566, 0.184309, 1.46709),
)
LMS_TO_RGB = (
    (0.0809444479, -0.130504409, 0.116721066),
    (-0.0102485335, 0.0540193266, -0.113614708),
    (-0.000365296938, -0.00412161469, 0.693511405),
)
CVD_KINDS = ("protanopia", "deuteranopia", "tritanopia")


def _apply(matrix, vector):
    return [sum(row[i] * vector[i] for i in range(3)) for row in matrix]


def simulate_cvd(hex_colour: str, kind: str) -> str:
    long_, med, short = _apply(RGB_TO_LMS, linear_rgb(hex_colour))
    if kind == "protanopia":
        long_ = 2.02344 * med - 2.52581 * short
    elif kind == "deuteranopia":
        med = 0.494207 * long_ + 1.24827 * short
    elif kind == "tritanopia":
        short = -0.395913 * long_ + 0.801109 * med
    else:
        raise ValueError("unknown CVD kind: " + kind)
    return to_hex(_apply(LMS_TO_RGB, [long_, med, short]))


# --- Reporting ---------------------------------------------------------------

METRICS = (("dE76", de76), ("dE2000", de2000))

failures: list[str] = []


def check(passed: bool, line: str) -> None:
    print("  {}  {}".format("PASS" if passed else "FAIL", line))
    if not passed:
        failures.append(line)


def info(line: str) -> None:
    print("  INFO  " + line)


def detail(line: str) -> None:
    print("  ....  " + line)


def heading(text: str) -> None:
    print("\n" + text + "\n" + "-" * len(text))


def worst_pair(colours, metric):
    """Smallest separation in the set, with the two colours responsible."""
    return min((metric(a, b), a, b) for a, b in itertools.combinations(colours, 2))


def main() -> int:
    theme = tomllib.loads(
        (ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8")
    )["theme"]
    # Each surface pairs its background with the ink a button label uses on it.
    surfaces = {
        "light": (theme["backgroundColor"], "#ffffff"),
        "dark": (theme["dark"]["backgroundColor"], "#000000"),
    }
    primary = {"light": theme["primaryColor"], "dark": theme["dark"]["primaryColor"]}
    status = {k: v for k, v in STATUS_COLORS.items() if v}
    reserved = list(status.values())

    print("Palette check for " + ROOT.name)
    detail("status  " + ", ".join("{}:{}".format(k, v) for k, v in status.items()))
    detail("series  {}, {}".format(SERIES, SERIES_ALT))
    detail("chrome  light {}, dark {}".format(primary["light"], primary["dark"]))

    heading("Status scale separation")
    for name, metric in METRICS:
        normal, a, b = worst_pair(reserved, metric)
        per_kind = [
            (kind, worst_pair([simulate_cvd(c, kind) for c in reserved], metric)[0])
            for kind in CVD_KINDS
        ]
        cvd_worst, cvd_kind = min((v, k) for k, v in per_kind)
        detail(
            name
            + " per dichromat: "
            + ", ".join("{} {:.1f}".format(k, v) for k, v in per_kind)
        )
        check(
            normal >= DE_FLOOR,
            "{} normal vision worst pair {:.1f} ({} vs {})".format(name, normal, a, b),
        )
        if cvd_worst >= DE_FLOOR:
            check(True, "{} worst dichromat {:.1f} ({})".format(name, cvd_worst, cvd_kind))
        else:
            info(
                "{} worst dichromat {:.1f} ({}) is under the {:.0f} floor, so the "
                "STATUS_GLYPHS secondary encoding is required rather than "
                "optional".format(name, cvd_worst, cvd_kind, DE_FLOOR)
            )

    heading("Status cell contrast (pastels: soft on light, strong on dark)")
    for level, colour in status.items():
        ratios = "  ".join(
            "{} {:5.2f}:1".format(mode, contrast(colour, bg))
            for mode, (bg, _) in surfaces.items()
        )
        info("{} level {}  {}   {}".format(colour, level, ratios, STATUS_LABELS[level]))

    heading("Chart series")
    for name, metric in METRICS:
        gap = metric(SERIES, SERIES_ALT)
        check(gap >= DE_FLOOR, "{} SERIES vs SERIES_ALT {:.1f}".format(name, gap))
    # The two-series chart (Metadata vs Data) has nothing but colour separating
    # the series, so the pair has to hold up for a dichromat as well.
    pair_cvd = min(
        metric(simulate_cvd(SERIES, kind), simulate_cvd(SERIES_ALT, kind))
        for kind in CVD_KINDS
        for _, metric in METRICS
    )
    check(pair_cvd >= DE_FLOOR, "series pair under worst dichromat {:.1f}".format(pair_cvd))
    # The reserved-hue rule: a series painted in a status hue reads as a status.
    for label, colour in (("SERIES", SERIES), ("SERIES_ALT", SERIES_ALT)):
        for level, reserved_colour in status.items():
            gap = de76(colour, reserved_colour)
            check(
                gap >= DE_FLOOR,
                "{} {} vs status {} {} dE76 {:.1f}".format(
                    label, colour, level, reserved_colour, gap
                ),
            )
        for mode, (bg, _) in surfaces.items():
            ratio = contrast(colour, bg)
            check(
                ratio >= CONTRAST_SERIES,
                "{} {} on {} surface {:.2f}:1".format(label, colour, mode, ratio),
            )

    heading("SERIES_FILL tracks SERIES")
    expected = "rgba(%d,%d,%d," % tuple(round(c * 255) for c in channels(SERIES))
    check(
        SERIES_FILL.replace(" ", "").startswith(expected),
        "{} is {} plus alpha".format(SERIES_FILL, SERIES),
    )

    heading("Chrome (primaryColor) is legible and clear of every status hue")
    for mode, colour in primary.items():
        ink = surfaces[mode][1]
        ratio = contrast(colour, ink)
        check(
            ratio >= CONTRAST_INK,
            "{} {} vs {} label ink {:.2f}:1".format(mode, colour, ink, ratio),
        )
        for level, reserved_colour in status.items():
            gap = de76(colour, reserved_colour)
            check(
                gap >= DE_FLOOR,
                "{} {} vs status {} dE76 {:.1f}".format(mode, colour, level, gap),
            )

    heading("SEQUENTIAL ramp")
    lightness, hues = [], []
    for colour in SEQUENTIAL:
        light, chroma, hue = oklch(colour)
        lightness.append(light)
        hues.append(hue)
        detail("{}  OKLCH L {:.4f}  C {:.4f}  H {:6.1f}".format(colour, light, chroma, hue))
    check(
        all(x > y for x, y in zip(lightness, lightness[1:])),
        "monotone lightness {:.3f} -> {:.3f}".format(lightness[0], lightness[-1]),
    )
    spread = max(hues) - min(hues)
    check(spread <= HUE_SPREAD, "hue spread {:.1f} deg".format(spread))
    for level, reserved_colour in status.items():
        gap = min(de76(c, reserved_colour) for c in SEQUENTIAL)
        check(gap >= DE_FLOOR, "nearest point to status {} dE76 {:.1f}".format(level, gap))
    # Each end is read against the surface it stands out on, not against both.
    for colour, mode in ((SEQUENTIAL[0], "dark"), (SEQUENTIAL[-1], "light")):
        ratio = contrast(colour, surfaces[mode][0])
        check(
            ratio >= CONTRAST_SERIES,
            "{} on {} surface {:.2f}:1".format(colour, mode, ratio),
        )

    print()
    if failures:
        print("FAILED: {} check(s)".format(len(failures)))
        for line in failures:
            print("  - " + line)
        return 1
    print("All hard checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
