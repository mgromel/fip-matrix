"""Static configuration: paths, FIP vocabulary, status semantics and palette."""

from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent

# Written daily by .github/workflows/sync_fip_matrix.yml — this path is a contract
# with that workflow (`curl -o data/new_matrix.csv`). Do not move the file.
CSV_PATH = ROOT / "data" / "new_matrix.csv"
ASSETS = ROOT / "assets"

# --- FIP vocabulary ---------------------------------------------------------

TERMS = "https://w3id.org/fair/fip/terms/"

RES_AVAILABLE = TERMS + "Available-FAIR-Enabling-Resource"
RES_TO_DEVELOP = TERMS + "FAIR-Enabling-Resource-to-be-Developed"

REL_CURRENT = TERMS + "declares-current-use-of"
REL_PLANNED = TERMS + "declares-planned-use-of"
REL_REPLACEMENT = TERMS + "declares-planned-replacement-of"

REL_LABELS = {
    REL_CURRENT: "Current use",
    REL_PLANNED: "Planned use",
    REL_REPLACEMENT: "Planned replacement",
}

# resourcetype x rel -> status. Anything not covered here maps to "no status" and
# is invisible in the matrix (see utils.data_quality for how many rows that is).
AVAILABLE_MAP = {REL_CURRENT: 3, REL_PLANNED: 2, REL_REPLACEMENT: 3}
TBD_MAP = {REL_CURRENT: None, REL_PLANNED: 1, REL_REPLACEMENT: None}

# --- Status scale -----------------------------------------------------------
# Level 0 is deliberately unfilled — "no declaration" should recede into the
# surface rather than read as a fourth category. That also keeps 96% of cells out
# of the CSS payload entirely.
#
# The other three are treated as CATEGORICAL, not as a single-hue ordinal ramp.
# A ramp is the textbook choice for an ordered scale, but these cells are 44px
# and isolated in a 96%-empty grid, where hue separation is far easier to see
# than lightness separation.
#
# Cool-sky / tan / celadon, chosen by the maintainer. Measured against the
# validator: worst-pair ΔE 16.3 for normal vision (clears the 15 floor) and 7.8
# under simulated colour-vision deficiency. That CVD figure sits in the 6-8 band,
# which is permitted only alongside a secondary encoding — Compact mode's ○ ◐ ●
# and the labelled legend below provide it, so status never rests on hue alone.
#
# The trade is contrast: these are pastels, so on the light surface they measure
# 1.4-2.3:1 and read soft, while on the dark surface they are 7.3-11.9:1 and
# pop. Darkening each hue a step would raise light-mode contrast if the cells
# ever feel too faint. For reference, the previous blue/pink/green scored ΔE 26.5
# normal / 11.3 CVD with every hue above 3:1 on both surfaces.
#
# Blue stays at level 1 and green at level 3, matching the app's original reading.

STATUS_LABELS = {
    0: "No data",
    1: "Resource in development / future use",
    2: "Available resource / future use",
    3: "Available resource / current use",
}

STATUS_COLORS = {0: None, 1: "#47afff", 2: "#d8b083", 3: "#86eaaf"}

# Compact mode has no colour, so order is carried by fill instead. This is also
# the secondary encoding that keeps status from depending on hue alone.
STATUS_GLYPHS = {0: None, 1: "○", 2: "◐", 3: "●"}

# Precomputed lookup arrays, indexed by status 0-3. An empty CSS string at index 0
# makes pandas emit no rule at all for empty cells.
CELL_CSS = np.array(
    ["" if c is None else f"background-color:{c};" for c in STATUS_COLORS.values()],
    dtype=object,
)
CELL_GLYPH = np.array(list(STATUS_GLYPHS.values()), dtype=object)

# --- Chart palette ----------------------------------------------------------

# The three status hues are reserved. A chart series painted in one of them
# would read as a status, so the series colours sit clear of all three (nearest
# normal-vision ΔE 12.0) and clear 3:1 on both surfaces. They also validate as a
# pair in both modes, which matters for the one two-series chart.
SERIES = "#7a5cf0"  # single-series magnitude
SERIES_ALT = "#00a0a0"  # only where the chart has its own legend (Metadata vs Data)
CATEGORICAL = [SERIES, SERIES_ALT]

SERIES_FILL = "rgba(122,92,240,0.12)"  # area fill under SERIES lines

# Continuous magnitude: one hue (SERIES violet, 287°), light to dark, verified
# monotone in OKLCH lightness with a 1.8° hue spread. Deliberately not a blue,
# pink or green ramp — those hues belong to the status scale.
SEQUENTIAL = ["#e5e3ff", "#c9c5ff", "#aca3ff", "#9180f7", "#785bed", "#5d40c0"]

# Chrome drawn in translucent grey so it reads correctly on either surface
# without the figure having to know which theme it is in.
GRID = "rgba(128,128,128,0.18)"
EMPTY_CELL = "rgba(128,128,128,0.10)"

# --- Rendering budgets ------------------------------------------------------

# Above this many pivot cells the styled path stops being worth it: pandas and
# Streamlit both walk every cell when translating a Styler, and the browser
# rescans the whole CSS blob per visible cell. Compact mode has no Styler at all
# and so no ceiling. Well under pandas' own styler.render.max_elements (262,144).
STYLE_BUDGET = 20_000

MATRIX_META = ["FIP question", "FAIR Supporting Resource", "Link"]
