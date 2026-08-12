"""Page chrome: header, statistics band, legend and logos."""

from __future__ import annotations

import base64
from pathlib import Path

import streamlit as st

from config import ASSETS, STATUS_COLORS, STATUS_LABELS

_LOGOS = ["parc_logo.png", "GFF_logo.png"]


# Hover text for the (?) icon beside each Analytics heading. Each one covers what
# the chart shows, how it is computed, how to read it, and what it leaves out.
CHART_HELP = {
    "heatmap": """
**What it shows.** One cell per community per FIP question, coloured by the most
mature status that community has declared.

**How it is built.** Rows are the FIP questions in canonical FAIR order
(Findable → Accessible → Interoperable → Reusable, most split into a Data `-D`
and a Metadata `-MD` variant); columns are the communities in your selection.
Cells aggregate with **max**, unlike the Matrix tab which uses `min` — so a cell
answers *"what is the best this community has achieved here?"* rather than
auditing every individual resource.

**How to read it.** An empty cell means no declaration at all for that pair. Scan
for vertical gaps (a question nobody answers) and horizontal gaps (a community
with patchy coverage).
""",
    "principle": """
**What it shows.** Where communities concentrate their effort, and how mature
that effort is.

**How it is built.** Declarations grouped by FAIR principle — the `-D` and `-MD`
variants of each question are merged, so `F1-D` and `F1-MD` both count as F1 —
then split by declared status. Principles are ordered by total volume.

**How to read it.** Bar length is the amount of activity; the segments show its
maturity. A long bar that is mostly "future use" means a principle with a lot of
intent but little delivery.

**Caveats.** This counts *declarations*, not communities: one community naming
five resources for a principle contributes five. Declarations with no mappable
status are excluded.
""",
    "md_vs_d": """
**What it shows.** The gap between how communities handle their **data** and
their **metadata**.

**How it is built.** Most FAIR principles are asked twice — once about the data
itself (`-D`) and once about its metadata (`-MD`). Each row is a principle; the
two dots are the declaration counts for each variant and the connecting line is
the distance between them.

**How to read it.** A long line means data and metadata practice diverge sharply
for that principle — typically metadata running ahead. Dots close together mean
the two are treated alike.

**Caveats.** Questions asked only once (such as A2, F2 and F3) have no `-D`/`-MD`
split and so do not appear.
""",
    "coverage": """
**What it shows.** Both ends of the completeness distribution — the communities
that answer the most of the FIP questionnaire, and the ones that answer the
least.

**How it is built.** For each community, the share of the FIP questions **in your
current selection** answered at least once — regardless of status, and regardless
of how many resources were named. The two panels share one scale, so bar lengths
are directly comparable across them. The left panel runs best-first; the right
runs worst-first, since that is the end worth acting on.

**How to read it.** 100% means a declaration exists for every selected question.
Both extremes are shown deliberately: a single top-N ranking hides the
interesting half, because with a narrow selection most communities tie at 100%
while the ones with real gaps never appear.

**Caveats.** The denominator is your selection, so narrowing the FIP-questions
filter moves every bar: reaching 100% across 5 questions is common, across all 21
it is not. With fewer than six communities in the selection the split is dropped
and all of them are shown in one panel.
""",
    "resources": """
**What it shows.** The FAIR Enabling Resources — standards, identifiers,
vocabularies, repositories and services — on which the selected communities have
most converged.

**How it is built.** The 15 resources declared by the greatest number of
**distinct communities**.

**How to read it.** The measure is community count, not declaration count, so a
resource named once each by 40 communities outranks one named 40 times by a
single community. This is a convergence measure, not a popularity one.

**Caveats.** Labels are trimmed to the resource acronym; hover a bar for the full
name.
""",
    "supercommunities": """
**What it shows.** Communities grouped by supercommunity — the umbrella project
or research infrastructure declared in their nanopublications (ENVRI, PARC,
Galaxy, JERICO and others).

**How it is built.** Rectangle **area** is declaration count; **colour** is
question coverage, the share of the selected FIP questions answered. The two
channels are independent on purpose. A supercommunity's own coverage is the
*union* of its members' questions, not the average of their coverages.

**How to read it.** A small dark tile is a thorough small community; a large pale
one is a big but patchy contributor.

**Caveats.** About 20% of declarations come from communities belonging to no
supercommunity and do not appear here. The hierarchy is also not strict —
eLTER-RI and DiSSCo are each a supercommunity in their own right *and* a member
of ENVRI.
""",
    "timeline": """
**What it shows.** How the body of published FIPs in your selection has grown.

**How it is built.** Cumulative count of distinct FIPs by quarter, dated by the
nanopublication's creation timestamp. The curve only ever rises.

**How to read it.** Steep sections are publication campaigns rather than steady
accumulation — 118 FIPs appeared in 2024 against 4 in 2023, which is why this is
cumulative: a raw per-quarter series looks broken.

**Caveats.** Future-dated records are clipped at today, so the line never implies
data that does not exist yet.
""",
}


def sidebar_header() -> None:
    """Title and subtitle at the top of the sidebar, which frees the whole main
    column for the tabs and their content.

    Sized explicitly rather than with a markdown heading level: the app title
    should outrank the tabs (1.6rem), and Streamlit scales its own headings down
    inside the sidebar.
    """
    st.markdown(
        """
        <style>
          #app-title {
            font-size: 2.1rem;
            font-weight: 700;
            line-height: 1.15;
            letter-spacing: -0.4px;
            margin: 0.2rem 0 0.5rem;
          }
        </style>
        <div id="app-title">Interactive FIP Matrix</div>
        """,
        unsafe_allow_html=True,
    )
    st.caption(
        "FAIR convergence across communities, built from "
        "[FAIR Implementation Profile](https://www.go-fair.org/how-to-go-fair/fair-implementation-profile/) "
        "nanopublications."
    )
    st.divider()


def tab_styles() -> None:
    """Make the tabs read as primary navigation rather than a minor control.

    Streamlit has no theme option for tab sizing, so this targets the tab's
    `data-testid` and the standard `aria-selected` ARIA attribute — chosen over
    generated class names, which change between releases.
    """
    st.markdown(
        """
        <style>
          [data-testid="stTabs"] [data-testid="stTab"] {
            font-size: 1.6rem;
            font-weight: 600;
            padding: 0.7rem 1.8rem;
            letter-spacing: 0.1px;
          }
          /* The label sits in a nested element that carries its own size */
          [data-testid="stTabs"] [data-testid="stTab"] p,
          [data-testid="stTabs"] [data-testid="stTab"] div,
          [data-testid="stTabs"] [data-testid="stTab"] span {
            font-size: inherit !important;
            font-weight: inherit !important;
          }
          [data-testid="stTabs"] [data-testid="stTab"][aria-selected="true"] {
            font-weight: 700;
          }
          /* Thicker underline for the active tab */
          [data-testid="stTabs"] [data-baseweb="tab-highlight"] {
            height: 4px;
          }
          [data-testid="stTabs"] [data-baseweb="tab-list"] {
            gap: 0.75rem;
            margin-bottom: 1rem;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )


def stat_band(stats: dict) -> None:
    """Headline numbers for the whole dataset: identity, breadth, depth, volume,
    completeness — in that reading order."""
    cols = st.columns(5)

    with cols[0]:
        st.metric(
            "FIPs published",
            f"{stats['fips']:,}",
            help="Distinct FAIR Implementation Profiles.",
            chart_data=stats["fip_growth"],
            chart_type="area",
            border=True,
        )
    with cols[1]:
        st.metric(
            "Communities",
            f"{stats['communities']:,}",
            help=f"Grouped into {stats['supercommunities']} supercommunities.",
            border=True,
        )
    with cols[2]:
        st.metric(
            "FAIR Enabling Resources",
            f"{stats['resources']:,}",
            help="Distinct standards, repositories and services declared.",
            border=True,
        )
    with cols[3]:
        st.metric(
            "Declarations",
            f"{stats['declarations']:,}",
            help="One row per community-question-resource statement.",
            border=True,
        )
    with cols[4]:
        st.metric(
            "Question coverage",
            f"{stats['coverage']:.0%}",
            help=(
                f"Share of the {stats['communities']} x {stats['questions']} "
                "community-question pairs with at least one declaration."
            ),
            border=True,
        )

    st.caption(
        f"Declarations recorded {stats['first_date']:%b %Y} - "
        f"{stats['last_date']:%b %Y}. Some carry forward-looking end dates."
    )


def legend() -> None:
    """Compact inline legend. Colour never carries the meaning alone — every
    swatch is labelled."""
    swatches = []
    for status in (3, 2, 1):
        swatches.append(
            f'<span style="display:inline-flex;align-items:center;gap:.4rem;'
            f'margin-right:1.4rem;white-space:nowrap">'
            f'<span style="width:.85rem;height:.85rem;border-radius:3px;'
            f'background:{STATUS_COLORS[status]};display:inline-block"></span>'
            f'<span>{STATUS_LABELS[status]}</span></span>'
        )
    swatches.append(
        '<span style="display:inline-flex;align-items:center;gap:.4rem;white-space:nowrap">'
        '<span style="width:.85rem;height:.85rem;border-radius:3px;'
        'border:1px solid rgba(128,128,128,.45);display:inline-block"></span>'
        f'<span>{STATUS_LABELS[0]}</span></span>'
    )
    st.markdown(
        '<div style="display:flex;flex-wrap:wrap;gap:.25rem 0;font-size:.82rem;'
        f'opacity:.85;padding:.35rem 0">{"".join(swatches)}</div>',
        unsafe_allow_html=True,
    )


@st.cache_data(show_spinner=False)
def _img_to_base64(path: str, _mtime: float) -> str:
    return base64.b64encode(Path(path).read_bytes()).decode()


def sidebar_logos() -> None:
    """Partner logos at the foot of the sidebar.

    `position: sticky` rather than `fixed`: the block sits in normal flow after
    the filters and settles against the bottom of the sidebar when there is room,
    so it needs no page padding, no z-index, and no overlay above the grid. The
    PNGs are base64-encoded once and cached rather than re-read every rerun.
    """
    logos = []
    for name in _LOGOS:
        path = ASSETS / name
        if path.exists():
            logos.append(_img_to_base64(str(path), path.stat().st_mtime))
    if not logos:
        return

    images = "".join(
        f'<img src="data:image/png;base64,{data}" alt="Partner logo"/>' for data in logos
    )
    st.markdown(
        f"""
        <style>
          #sidebar-logos {{
            position: sticky;
            bottom: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 26px;
            margin-top: 1.5rem;
            padding: 14px 0 10px;
            background-color: var(--secondary-background-color, var(--background-color));
            border-top: 1px solid rgba(128, 128, 128, 0.22);
          }}
          #sidebar-logos img {{
            height: 34px;
            object-fit: contain;
          }}
        </style>

        <div id="sidebar-logos">{images}</div>
        """,
        unsafe_allow_html=True,
    )
