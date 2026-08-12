"""Plotly figure builders.

Pure functions: each takes a frame and returns a ``go.Figure``, so every chart can
be built and inspected in a plain REPL. Nothing here touches ``st`` beyond caching.

Colour rules applied throughout:
  * the three status hues come from ``config`` and are reserved — a chart series
    never borrows one, and nothing else is ever painted in them;
  * single-series charts use one colour, never a value-ramp across nominal
    categories;
  * chrome is translucent grey so figures read on both the light and dark surface.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from config import (
    EMPTY_CELL,
    GRID,
    SEQUENTIAL,
    SERIES,
    SERIES_ALT,
    SERIES_FILL,
    STATUS_COLORS,
    STATUS_LABELS,
)

_FONT = 'system-ui, -apple-system, "Segoe UI", sans-serif'
_STATUS_ORDER = [3, 2, 1]  # most mature first, so stacks read left-to-right


def _base(fig: go.Figure, height: int, legend: bool = False) -> go.Figure:
    """Shared chrome: transparent surface, recessive hairline grid, no clutter."""
    fig.update_layout(
        height=height,
        margin=dict(l=8, r=8, t=8, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=_FONT, size=13),
        showlegend=legend,
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
            title_text="", bgcolor="rgba(0,0,0,0)",
        ),
        hoverlabel=dict(font_family=_FONT, font_size=12),
        bargap=0.28,
    )
    fig.update_xaxes(showgrid=False, zeroline=False, showline=False, ticks="")
    fig.update_yaxes(showgrid=False, zeroline=False, showline=False, ticks="")
    return fig


def _value_axis(fig: go.Figure, axis: str = "x") -> go.Figure:
    """Hairline solid grid on the measure axis only."""
    update = fig.update_xaxes if axis == "x" else fig.update_yaxes
    update(showgrid=True, gridcolor=GRID, gridwidth=1, griddash="solid")
    return fig


# --- Overview ---------------------------------------------------------------


def declaration_mix(counts: pd.Series) -> go.Figure:
    """One 100% stacked bar. A 3-slice donut would be harder to read and the
    shares here are far apart, so a single proportional bar wins."""
    total = counts.sum()
    fig = go.Figure()
    # Status colours reused deliberately — these segments *are* the status scale.
    tones = {
        "Current use": STATUS_COLORS[3],
        "Planned use": STATUS_COLORS[2],
        "Planned replacement": STATUS_COLORS[1],
    }
    for label in ["Current use", "Planned use", "Planned replacement"]:
        if label not in counts.index:
            continue
        value = int(counts[label])
        share = value / total
        fig.add_bar(
            x=[share], y=[""], orientation="h", name=label,
            marker=dict(color=tones[label], line=dict(width=2, color="rgba(0,0,0,0)")),
            text=[f"{label}<br>{share:.0%}" if share > 0.12 else ""],
            textposition="inside", insidetextanchor="middle",
            # Dark ink: the status colours are pastels in both themes, so the
            # segment itself is the background here, not the page.
            textfont=dict(color="#0b0b0b", size=12),
            hovertemplate=f"<b>{label}</b><br>%{{customdata:,}} declarations"
                          f"<br>{share:.1%} of total<extra></extra>",
            customdata=[value],
        )
    fig.update_layout(barmode="stack", bargap=0.2)
    fig.update_xaxes(visible=False, range=[0, 1])
    fig.update_yaxes(visible=False)
    return _base(fig, 76, legend=False)


def coverage_by_family(counts: pd.Series) -> go.Figure:
    """Declarations per FAIR family. One series, one colour, direct-labelled."""
    names = {"F": "Findable", "A": "Accessible", "I": "Interoperable", "R": "Reusable"}
    fig = go.Figure(
        go.Bar(
            x=counts.values,
            y=[names.get(i, i) for i in counts.index],
            orientation="h",
            marker=dict(color=SERIES, cornerradius=4),
            text=[f"{v:,}" for v in counts.values],
            textposition="outside",
            cliponaxis=False,
            hovertemplate="<b>%{y}</b><br>%{x:,} declarations<extra></extra>",
        )
    )
    fig.update_xaxes(visible=False, range=[0, counts.max() * 1.18])
    fig.update_yaxes(autorange="reversed")
    return _base(fig, 180)


def top_resources(counts: pd.Series, height: int = 320) -> go.Figure:
    """Most widely adopted resources, measured in distinct communities."""
    labels = [_short(i) for i in counts.index]
    fig = go.Figure(
        go.Bar(
            x=counts.values, y=labels, orientation="h",
            marker=dict(color=SERIES, cornerradius=4),
            text=[f"{v}" for v in counts.values],
            textposition="outside",
            cliponaxis=False,
            customdata=list(counts.index),
            hovertemplate="<b>%{customdata}</b><br>%{x} communities<extra></extra>",
        )
    )
    fig.update_xaxes(visible=False, range=[0, counts.max() * 1.15])
    fig.update_yaxes(autorange="reversed")
    return _base(fig, height)


def fip_growth(series: pd.Series) -> go.Figure:
    """Cumulative distinct FIPs. Raw per-quarter counts look broken because
    publication arrives in campaign bursts; the cumulative curve is honest."""
    fig = go.Figure(
        go.Scatter(
            x=series.index, y=series.values,
            mode="lines", line=dict(color=SERIES, width=2, shape="spline"),
            fill="tozeroy", fillcolor=SERIES_FILL,
            hovertemplate="<b>%{y} FIPs</b><br>%{x|%b %Y}<extra></extra>",
        )
    )
    fig.update_layout(hovermode="x unified")
    fig.update_xaxes(showgrid=False)
    _value_axis(fig, "y")
    return _base(fig, 220)


# --- Analytics --------------------------------------------------------------


def question_community_heatmap(fdf: pd.DataFrame) -> go.Figure:
    """The matrix at a glance — one Heatmap trace, so cost is flat in cell count.

    Uses ``max`` (best status declared) rather than the grid's ``min``: this is a
    summary of what a community has achieved, not a per-resource audit.
    """
    grid = pd.pivot_table(
        fdf, values="mapped_values", index="q", columns="c",
        aggfunc="max", fill_value=0, observed=True,
    )
    # otypes is required so an empty selection doesn't blow up on size-0 input.
    labels = np.vectorize(STATUS_LABELS.get, otypes=[object])(
        grid.to_numpy(dtype="int8")
    )

    # Four discrete bands, not a continuous interpolation.
    bands, colours = [], [EMPTY_CELL, STATUS_COLORS[1], STATUS_COLORS[2], STATUS_COLORS[3]]
    for i, colour in enumerate(colours):
        bands += [[i / 4, colour], [(i + 1) / 4, colour]]

    fig = go.Figure(
        go.Heatmap(
            z=grid.to_numpy(), x=list(grid.columns), y=[str(q) for q in grid.index],
            colorscale=bands, zmin=-0.5, zmax=3.5, showscale=False,
            xgap=1, ygap=1, customdata=labels,
            hovertemplate="<b>%{x}</b><br>%{y}<br>%{customdata}<extra></extra>",
        )
    )
    fig.update_xaxes(tickangle=-60, tickfont=dict(size=9))
    fig.update_yaxes(autorange="reversed", tickfont=dict(size=10))
    fig.update_layout(margin=dict(l=8, r=8, t=8, b=8))
    return _base(fig, max(320, 22 * len(grid.index) + 150))


def status_by_principle(fdf: pd.DataFrame) -> go.Figure:
    """Where effort concentrates, and how mature it is, in one figure."""
    principle = fdf["q"].astype(str).str.replace(r"-(MD|D)$", "", regex=True)
    counts = (
        fdf.assign(principle=principle)
        .dropna(subset=["mapped_values"])
        .groupby(["principle", "mapped_values"], observed=True)
        .size()
        .unstack(fill_value=0)
    )
    counts = counts.loc[counts.sum(axis=1).sort_values(ascending=True).index]

    fig = go.Figure()
    for status in _STATUS_ORDER:
        if status not in counts.columns:
            continue
        fig.add_bar(
            x=counts[status].values, y=list(counts.index), orientation="h",
            name=STATUS_LABELS[status],
            marker=dict(color=STATUS_COLORS[status], line=dict(width=2, color="rgba(0,0,0,0)")),
            hovertemplate=f"<b>%{{y}}</b><br>{STATUS_LABELS[status]}"
                          "<br>%{x:,} declarations<extra></extra>",
        )
    fig.update_layout(barmode="stack")
    _value_axis(fig, "x")
    return _base(fig, max(300, 30 * len(counts) + 90), legend=True)


def community_coverage(fdf: pd.DataFrame, n: int = 12) -> go.Figure:
    """Both ends of the coverage distribution, side by side on a shared scale.

    A single top-N ranking hides the interesting half: with a narrow question
    selection most communities sit at 100%, so the leaderboard becomes a wall of
    ties while the communities with real gaps never appear.
    """
    n_q = fdf["q"].nunique() or 1
    share = (fdf.groupby("c", observed=True)["q"].nunique() / n_q).sort_values(
        ascending=False
    )
    share = share[share > 0]
    if share.empty:
        return _base(go.Figure(), 300)

    def bar(data, col, fig):
        fig.add_trace(
            go.Bar(
                x=data.values, y=list(data.index), orientation="h",
                marker=dict(color=SERIES, cornerradius=4),
                text=[f"{v:.0%}" for v in data.values],
                textposition="outside", cliponaxis=False, showlegend=False,
                hovertemplate="<b>%{y}</b><br>%{x:.0%} of selected questions"
                              "<extra></extra>",
            ),
            row=1, col=col,
        )

    # Too few communities to split meaningfully — show them all in one panel.
    if len(share) < 6:
        fig = make_subplots(rows=1, cols=1)
        bar(share, 1, fig)
        fig.update_xaxes(visible=False, range=[0, 1.16])
        fig.update_yaxes(autorange="reversed", tickfont=dict(size=11))
        return _base(fig, max(280, 26 * len(share) + 80))

    n = min(n, len(share) // 2)  # halving keeps the two panels disjoint
    top = share.head(n)
    # Worst first in the right panel: that is the end worth acting on.
    bottom = share.tail(n).sort_values()

    fig = make_subplots(
        rows=1, cols=2, horizontal_spacing=0.22,
        subplot_titles=("<b>Most complete</b>", "<b>Least complete</b>"),
    )
    bar(top, 1, fig)
    bar(bottom, 2, fig)
    fig.update_xaxes(visible=False, range=[0, 1.16])  # shared scale, comparable
    fig.update_yaxes(autorange="reversed", tickfont=dict(size=11))
    for note in fig.layout.annotations:
        note.font.size = 14

    fig = _base(fig, max(300, 26 * n + 120))
    # _base() sets an 8px top margin, which clips the subplot titles — they are
    # annotations sitting above the plot area, so they need room reserved.
    fig.update_layout(margin=dict(l=8, r=8, t=40, b=8))
    return fig


def metadata_vs_data(fdf: pd.DataFrame) -> go.Figure:
    """The MD-vs-D asymmetry is a core FIP concept and nothing else here shows it.
    A dumbbell reads the gap directly; a grouped bar makes you subtract."""
    q = fdf["q"].astype(str)
    scope = np.where(q.str.endswith("-MD"), "Metadata",
                     np.where(q.str.endswith("-D"), "Data", "Both"))
    principle = q.str.replace(r"-(MD|D)$", "", regex=True)
    counts = (
        fdf.assign(scope=scope, principle=principle)
        .groupby(["principle", "scope"], observed=True)
        .size()
        .unstack(fill_value=0)
    )
    for col in ("Metadata", "Data"):
        if col not in counts:
            counts[col] = 0
    counts = counts[counts[["Metadata", "Data"]].sum(axis=1) > 0]
    counts = counts.loc[counts[["Metadata", "Data"]].sum(axis=1).sort_values().index]

    fig = go.Figure()
    for a, b, y in zip(counts["Metadata"], counts["Data"], counts.index):
        fig.add_trace(go.Scatter(
            x=[a, b], y=[y, y], mode="lines",
            line=dict(color=GRID, width=2), showlegend=False, hoverinfo="skip",
        ))
    for name, colour in (("Metadata", SERIES), ("Data", SERIES_ALT)):
        fig.add_trace(go.Scatter(
            x=counts[name], y=list(counts.index), mode="markers+text", name=name,
            marker=dict(color=colour, size=11),
            text=[f"{v:,}" for v in counts[name]],
            textposition="top center", textfont=dict(size=10),
            hovertemplate=f"<b>%{{y}}</b><br>{name}: %{{x:,}}<extra></extra>",
        ))
    _value_axis(fig, "x")
    fig.update_yaxes(tickfont=dict(size=11))
    return _base(fig, max(300, 34 * len(counts) + 90), legend=True)


def supercommunity_treemap(fdf: pd.DataFrame) -> go.Figure:
    """Area = declarations, colour = mean status. Identity comes from the labels,
    which frees colour to carry a second measure — 15 categorical hues would not
    be distinguishable anyway."""
    n_q = fdf["q"].nunique() or 1
    scoped = fdf.dropna(subset=["sc"])
    grouped = (
        scoped.groupby(["sc", "c"], observed=True)
        .agg(n=("mapped_values", "size"), answered=("q", "nunique"))
        .reset_index()
    )
    grouped = grouped[grouped["n"] > 0]
    if grouped.empty:
        return _base(go.Figure(), 320)
    grouped["coverage"] = grouped["answered"] / n_q

    parent_names = grouped["sc"].astype(str)
    child_names = grouped["c"].astype(str)
    roots = list(dict.fromkeys(parent_names))
    # A supercommunity's own coverage is the union of its members' questions,
    # not the mean of their coverages.
    root_coverage = (scoped.groupby("sc", observed=True)["q"].nunique() / n_q).to_dict()

    # Explicit ids are essential here. Plotly falls back to using `labels` as node
    # ids, and two names (eLTER-RI, DiSSCo) exist BOTH as a supercommunity and as
    # a community — so a node became its own parent and the whole tree silently
    # rendered as nothing. Path-style ids keep the two roles distinct.
    ids = [f"sc/{name}" for name in roots] + [
        f"sc/{parent}/{child}" for parent, child in zip(parent_names, child_names)
    ]
    parents = [""] * len(roots) + [f"sc/{parent}" for parent in parent_names]
    labels = roots + list(child_names)

    # Identity comes from the tile labels, which frees colour to carry a second
    # measure. Coverage is the right one: it is independent of area (a small
    # community can answer every question), so the two channels say different
    # things instead of double-encoding size.
    coverage = [root_coverage.get(name, 0.0) for name in roots] + list(grouped["coverage"])

    fig = go.Figure(
        go.Treemap(
            ids=ids,
            labels=labels,
            parents=parents,
            values=[0] * len(roots) + list(grouped["n"]),
            branchvalues="remainder",
            marker=dict(
                colors=coverage,
                colorscale=SEQUENTIAL,
                cmin=0,
                cmax=1,
                line=dict(width=2, color="rgba(0,0,0,0)"),
                colorbar=dict(
                    title=dict(text="Question coverage", side="top", font=dict(size=11)),
                    orientation="h", y=-0.02, yanchor="top", x=0.5, xanchor="center",
                    len=0.55, thickness=10, outlinewidth=0,
                    tickformat=".0%", tickfont=dict(size=10),
                ),
            ),
            customdata=[[c] for c in coverage],
            textfont=dict(size=12),
            tiling=dict(pad=2),
            hovertemplate="<b>%{label}</b><br>%{value:,} declarations"
            "<br>%{customdata[0]:.0%} question coverage<extra></extra>",
        )
    )
    fig = _base(fig, 420)
    fig.update_layout(margin=dict(l=8, r=8, t=8, b=52))  # room for the colorbar
    return fig


def adoption_timeline(fdf: pd.DataFrame) -> go.Figure:
    """Cumulative distinct FIPs in the selection, by quarter."""
    quarter = fdf["date_ts"].dt.tz_localize(None).dt.to_period("Q").dt.to_timestamp()
    series = fdf.assign(quarter=quarter).groupby("quarter")["fip_index"].nunique().cumsum()
    # Clip the future-dated tail so the curve doesn't imply data we don't have.
    now = pd.Timestamp.now(tz="UTC").tz_localize(None)
    series = series[series.index <= now]
    if series.empty:
        return _base(go.Figure(), 240)

    fig = go.Figure(
        go.Scatter(
            x=series.index, y=series.values, mode="lines",
            line=dict(color=SERIES, width=2),
            fill="tozeroy", fillcolor=SERIES_FILL,
            hovertemplate="<b>%{y} FIPs</b><br>%{x|%b %Y}<extra></extra>",
        )
    )
    fig.update_layout(hovermode="x unified")
    _value_axis(fig, "y")
    return _base(fig, 240)


# --- helpers ----------------------------------------------------------------


def _short(label: str, limit: int = 42) -> str:
    """Resource labels are `ACRONYM | Long expansion` — keep the acronym."""
    head = str(label).split("|")[0].strip()
    return head if len(head) <= limit else head[: limit - 1] + "…"


__all__ = [
    "adoption_timeline",
    "community_coverage",
    "coverage_by_family",
    "declaration_mix",
    "fip_growth",
    "metadata_vs_data",
    "question_community_heatmap",
    "status_by_principle",
    "supercommunity_treemap",
    "top_resources",
]
