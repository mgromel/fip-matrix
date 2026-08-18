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
# Apricot / aqua / lime, chosen by the maintainer. Worst-pair separation, with the
# metric named because the two disagree: ΔE76 gives 63.6 for normal vision and 24.8
# for the worst dichromat (protanopia); the stricter ΔE2000 gives 30.8 and 12.6
# (deuteranopia). Dichromat figures use a Viénot-Brettel-Mollon (1999) simulation
# over protanopia, deuteranopia and tritanopia.
#
# So ΔE76 clears the project's 15 floor under CVD but ΔE2000 does not, which is
# exactly the case where a secondary encoding is required rather than optional —
# Compact mode's ○ ◐ ● and the labelled legend below provide it, so status never
# rests on hue alone.
#
# The trade is contrast: these are pastels, so on the light surface they measure
# 1.3-2.0:1 and read soft, while on the dark surface they are 8.4-12.8:1 and pop.
# Level 3 is the faintest in light mode at 1.32:1; darkening each hue a step would
# raise light-mode contrast if the cells ever feel too weak.
#
# Blue is not in this scale on purpose. It is the chrome hue (theme primaryColor,
# and SEQUENTIAL below), and that separation is what stops a button or a chart bar
# from being read as a status.

STATUS_LABELS = {
    0: "No data",
    1: "Resource in development / future use",
    2: "Available resource / future use",
    3: "Available resource / current use",
}

STATUS_COLORS = {0: None, 1: "#f0a182", 2: "#6ec7c2", 3: "#b0f05c"}

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

# The three status hues are reserved. A chart series painted in one of them would
# read as a status, so both series sit clear of all three: nearest is SERIES_ALT to
# the apricot level 1 at ΔE76 29.2 / ΔE2000 21.3, against the project's 15 floor.
#
# Chart marks have to survive both surfaces, which rules out pastels — a pastel
# cannot clear 3:1 against a near-white and a near-black background at once. So
# these are mid-tones: 3.9:1 and 4.4:1 on light, 4.4:1 and 3.9:1 on dark. SERIES
# is a deeper member of the same blue family as the chrome and the SEQUENTIAL ramp,
# which is deliberate — blue means "chart or chrome" here, never a status.
#
# The pair separates at ΔE76 86.9 / ΔE2000 45.2, and still at 44.5 under the worst
# simulated dichromat, which matters for the one two-series chart (Metadata vs
# Data), where the two colours are the only thing telling the series apart.
#
# tools/check_palette.py asserts every figure in this block.
SERIES = "#2f85c2"  # single-series magnitude
SERIES_ALT = "#c2553f"  # only where the chart has its own legend (Metadata vs Data)
CATEGORICAL = [SERIES, SERIES_ALT]

SERIES_FILL = "rgba(47,133,194,0.12)"  # area fill under SERIES lines, SERIES at 12%

# Continuous magnitude: one hue (pastel blue, 245-250°), light to dark, verified
# monotone in OKLCH lightness (0.944 -> 0.498) with a 5.4° hue spread. Blue is the
# app's chrome hue, not a status hue, so the ramp cannot be read as a status: the
# nearest reserved colour is the aqua SERIES at ΔE 27.6, well clear of the 15
# floor. Endpoints clear 3:1 on the surface they are read against — the pale end
# on dark (14.8:1), the deep end on light (5.9:1).
SEQUENTIAL = ["#e3eefa", "#c2dbf2", "#9dc4e6", "#75a9d6", "#4e88bd", "#2f6699"]

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
