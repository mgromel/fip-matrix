"""The convergence matrix grid.

Two render paths share one pivot:

``Colour``
    A pandas ``Styler`` paints cell backgrounds. Empty cells get **no** CSS rule
    and the community columns are formatted to blank strings, which is what keeps
    the payload small: for the full 741x83 selection that is 54 KB of CSS instead
    of 1.4 MB, and 80 K display characters instead of 572 K.

``Compact``
    Plain glyph strings, no ``Styler`` in the pipeline at all, so Streamlit never
    serialises any CSS. Flat cost regardless of selection size.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from config import CELL_CSS, CELL_GLYPH, MATRIX_META, STYLE_BUDGET
from utils import build_matrix, community_columns

_GRID_HEIGHT = 620
_COMMUNITY_WIDTH = 44


def _status_block(flat: pd.DataFrame) -> np.ndarray:
    """The community sub-block as int8, for indexing the lookup arrays."""
    return flat.iloc[:, len(MATRIX_META) :].to_numpy(dtype="int8")


def _styled(flat: pd.DataFrame):
    """Colour path — one vectorized ``apply``, not a closure per cell."""
    css = np.empty(flat.shape, dtype=object)
    css[:] = ""
    css[:, len(MATRIX_META) :] = CELL_CSS[_status_block(flat)]
    css_df = pd.DataFrame(css, index=flat.index, columns=flat.columns)
    return (
        flat.style
        .apply(lambda _: css_df, axis=None)
        # Blank the numbers rather than hiding them with `color: transparent`,
        # which would need a CSS rule on every single cell.
        .format("", subset=community_columns(flat))
    )


def _glyphs(flat: pd.DataFrame) -> pd.DataFrame:
    # Built as a new object-dtype block rather than assigned in place, which
    # would coerce the float64 community columns cell by cell.
    glyphs = pd.DataFrame(
        CELL_GLYPH[_status_block(flat)],
        index=flat.index,
        columns=community_columns(flat),
    )
    return pd.concat([flat.iloc[:, : len(MATRIX_META)], glyphs], axis=1)


def _column_config(communities: list[str]) -> dict:
    config = {
        MATRIX_META[0]: st.column_config.TextColumn("FIP question", width=110, pinned=True),
        MATRIX_META[1]: st.column_config.TextColumn(
            "FAIR Supporting Resource", width=300, pinned=True
        ),
        MATRIX_META[2]: st.column_config.LinkColumn(
            "",
            width=52,
            display_text="🔗",
            help="Nanopublication describing this FAIR Enabling Resource",
            pinned=True,
        ),
    }
    config.update(
        {c: st.column_config.Column(c, width=_COMMUNITY_WIDTH) for c in communities}
    )
    return config


def render_matrix(fdf: pd.DataFrame, aggfunc: str = "min") -> None:
    if fdf.empty:
        st.info("No declarations match the current selection.")
        return

    flat = build_matrix(fdf, aggfunc)
    communities = community_columns(flat)
    n_cells = len(flat) * len(communities)

    # Pick the initial mode from the size of the first render, then let the user
    # own the control. A silent flip between colour and glyphs reads as a bug.
    if "cell_mode" not in st.session_state:
        st.session_state["cell_mode"] = "Colour" if n_cells <= STYLE_BUDGET else "Compact"

    left, right = st.columns([1, 3], vertical_alignment="center")
    with left:
        mode = st.segmented_control(
            "Cells",
            ["Colour", "Compact"],
            key="cell_mode",
            help="Compact draws glyphs instead of cell backgrounds — much faster "
            "on wide selections, and the only mode with no size ceiling.",
        ) or "Colour"
    with right:
        st.caption(
            f"{len(flat):,} resource rows × {len(communities)} communities "
            f"({n_cells:,} cells)"
        )

    if mode == "Colour" and n_cells > STYLE_BUDGET:
        st.caption(
            f"⚡ This selection is {n_cells:,} cells. Switch to **Compact** if "
            "scrolling feels heavy."
        )

    st.dataframe(
        _styled(flat) if mode == "Colour" else _glyphs(flat),
        height=_GRID_HEIGHT,
        row_height=30,
        hide_index=True,
        width="stretch",
        column_config=_column_config(communities),
    )
