"""FIP Matrix — interactive FAIR convergence explorer.

Entry point for Streamlit Community Cloud; must stay at the repository root.
Run locally with ``streamlit run main.py``.
"""

import streamlit as st

import charts
import ui
import utils
from config import CSV_PATH
from matrix import render_matrix

st.set_page_config(
    layout="wide",
    page_title="FIP Matrix",
    page_icon="🔍",
    initial_sidebar_state="expanded",
)

df = utils.get_data()
mtime = CSV_PATH.stat().st_mtime

questions_all = list(df["q"].cat.categories)  # canonical FAIR order, not alphabetical
communities_all = sorted(df["c"].dropna().unique())
supercommunities_all = sorted(df["sc"].dropna().unique())
min_date, max_date = df["startdate"].min(), df["enddate"].max()

# --- Filters ----------------------------------------------------------------
# One form, one rerun. Previously each of the four widgets triggered its own full
# script run and re-sent the entire matrix payload.

with st.sidebar:
    ui.sidebar_header()
    st.subheader("Filters")
    with st.form("filters", border=False):
        start = st.date_input(
            "Start date", value=min_date, min_value=min_date, max_value=max_date
        )
        end = st.date_input(
            "End date", value=max_date, min_value=min_date, max_value=max_date
        )
        selected_questions = st.multiselect(
            "FIP questions", options=questions_all, default=questions_all[:5]
        )
        selected_supercommunities = st.multiselect(
            "Supercommunities",
            options=supercommunities_all,
            placeholder="All supercommunities",
        )
        selected_communities = st.multiselect(
            "Communities", options=communities_all, placeholder="All communities"
        )
        st.form_submit_button("Apply", type="primary", width="stretch")

    st.caption("Leave a field empty to include everything in that dimension.")
    ui.sidebar_logos()

fdf = utils.filter_data(
    df,
    start,
    end,
    selected_questions,
    selected_communities,
    selected_supercommunities,
)

# --- Page -------------------------------------------------------------------

ui.tab_styles()

tab_overview, tab_matrix, tab_analytics = st.tabs(
    ["Overview", "Matrix", "Analytics"],
    # Lazy execution: only the open tab's body runs, so the matrix payload is not
    # built while the user is reading the charts, and vice versa.
    on_change="rerun",
    key="active_tab",
)

with tab_overview:
    if tab_overview.open:
        stats = utils.global_stats(df, mtime)
        ui.stat_band(stats)

        st.subheader("Declarations by type")
        st.plotly_chart(
            charts.declaration_mix(utils.declaration_mix(df, mtime)),
            config={"displayModeBar": False},
        )

        left, right = st.columns(2)
        with left:
            st.subheader("Coverage by FAIR family")
            st.caption("Declarations across all communities, by principle family.")
            st.plotly_chart(
                charts.coverage_by_family(utils.coverage_by_family(df, mtime)),
                config={"displayModeBar": False},
            )
        with right:
            st.subheader("Most adopted resources")
            st.caption("Measured in distinct communities declaring the resource.")
            st.plotly_chart(
                charts.top_resources(utils.top_resources(df, mtime, 5), height=180),
                config={"displayModeBar": False},
            )

        with st.expander("Data quality"):
            st.markdown(
                f"""
- **{stats['unmapped']:,} of {stats['declarations']:,} declarations
  ({stats['unmapped_share']:.1%}) carry no status** and are therefore invisible in
  the matrix. Their `resourcetype` is either the bare `FAIR-Enabling-Resource`
  term or missing, and neither is covered by the status mapping.
- The matrix aggregates duplicate declarations with **`min`**, so a community
  declaring both current *and* planned use of the same resource shows the weaker
  status. The Analytics heatmap uses `max` instead, since it summarises what a
  community has achieved rather than auditing each resource.
- Declarations with no `startdate`/`enddate` are backfilled with the dataset-wide
  earliest and latest dates, so they always fall inside the selected window.
"""
            )

with tab_matrix:
    if tab_matrix.open:
        ui.legend()
        render_matrix(fdf)

with tab_analytics:
    if tab_analytics.open:
        if fdf.empty:
            st.info("No declarations match the current selection.")
        else:
            st.caption(
                f"{len(fdf):,} declarations · {fdf['c'].nunique()} communities · "
                f"{fdf['q'].nunique()} FIP questions · "
                f"{fdf['reslabel'].nunique()} resources"
            )

            st.subheader(
                "FIP question × community", help=ui.CHART_HELP["heatmap"]
            )
            ui.legend()
            st.plotly_chart(
                charts.question_community_heatmap(fdf),
                config={"displayModeBar": False},
            )

            left, right = st.columns(2)
            with left:
                st.subheader(
                    "Status by FAIR principle", help=ui.CHART_HELP["principle"]
                )
                st.plotly_chart(
                    charts.status_by_principle(fdf),
                    config={"displayModeBar": False},
                )
            with right:
                st.subheader("Metadata vs data", help=ui.CHART_HELP["md_vs_d"])
                st.plotly_chart(
                    charts.metadata_vs_data(fdf), config={"displayModeBar": False}
                )

            st.subheader("Community coverage", help=ui.CHART_HELP["coverage"])
            st.plotly_chart(
                charts.community_coverage(fdf), config={"displayModeBar": False}
            )

            st.subheader("Most adopted resources", help=ui.CHART_HELP["resources"])
            st.plotly_chart(
                charts.top_resources(utils.top_resources_in(fdf, 15), height=460),
                config={"displayModeBar": False},
            )

            st.subheader(
                "Supercommunities", help=ui.CHART_HELP["supercommunities"]
            )
            st.plotly_chart(
                charts.supercommunity_treemap(fdf), config={"displayModeBar": False}
            )

            st.subheader("Adoption over time", help=ui.CHART_HELP["timeline"])
            st.plotly_chart(
                charts.adoption_timeline(fdf), config={"displayModeBar": False}
            )

            with st.expander("Table view"):
                st.dataframe(
                    utils.selection_table(fdf),
                    hide_index=True,
                    width="stretch",
                    height=380,
                )
