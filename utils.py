"""Data layer: loading, preparation, filtering, pivoting and aggregation.

The frame returned by :func:`load_matrix` is cached with ``st.cache_resource`` and
shared across sessions — **treat it as immutable**. Every transformation here
returns a copy (``assign``, ``rename``, boolean masks, ``pivot_table``).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from config import (
    AVAILABLE_MAP,
    CSV_PATH,
    MATRIX_META,
    REL_LABELS,
    RES_AVAILABLE,
    RES_TO_DEVELOP,
    STATUS_LABELS,
    TBD_MAP,
)

# Columns we never use; `nochoice` is 100% NaN upstream.
_DROP_COLS = ["nochoice"]


# --- Loading ----------------------------------------------------------------


@st.cache_resource(show_spinner="Loading FIP data…")
def load_matrix(path: str, _mtime: float) -> pd.DataFrame:
    """Read and prepare the matrix CSV.

    ``_mtime`` is part of the cache key only, so the daily CSV refresh is picked
    up without restarting the server.
    """
    df = pd.read_csv(path)
    df = df.drop(columns=[c for c in _DROP_COLS if c in df.columns])

    df["mapped_values"] = _map_status(df)
    df = _fill_and_convert_dates(df)
    df["date_ts"] = pd.to_datetime(df["date"], format="ISO8601", utc=True)

    # The `sort` column already encodes canonical FAIR order (F -> A -> I -> R);
    # plain alphabetical sorting would put A1.1 before F1, which is wrong for
    # this audience. Make `q` an ordered category so every pivot, axis and
    # multiselect inherits that order for free.
    order = df[["sort", "q"]].drop_duplicates().sort_values("sort")["q"].tolist()
    df["q"] = pd.Categorical(df["q"], categories=order, ordered=True)

    for col in ("c", "sc", "rel", "resourcetype"):
        df[col] = df[col].astype("category")

    return df


def get_data() -> pd.DataFrame:
    return load_matrix(str(CSV_PATH), CSV_PATH.stat().st_mtime)


def _map_status(df: pd.DataFrame) -> pd.Series:
    """resourcetype x rel -> ordinal status (vectorized)."""
    out = pd.Series(np.nan, index=df.index, dtype="float64")
    available = df["resourcetype"].eq(RES_AVAILABLE)
    to_develop = df["resourcetype"].eq(RES_TO_DEVELOP)
    out[available] = df.loc[available, "rel"].map(AVAILABLE_MAP)
    out[to_develop] = df.loc[to_develop, "rel"].map(TBD_MAP)
    return out


def _fill_and_convert_dates(df: pd.DataFrame) -> pd.DataFrame:
    min_start = pd.to_datetime(df["startdate"].dropna()).min().date()
    max_end = pd.to_datetime(df["enddate"].dropna()).max().date()
    df["startdate"] = pd.to_datetime(df["startdate"].fillna(min_start)).dt.date
    df["enddate"] = pd.to_datetime(df["enddate"].fillna(max_end)).dt.date
    return df


# --- Filtering --------------------------------------------------------------


def filter_data(
    df, start, end, questions=None, communities=None, supercommunities=None
) -> pd.DataFrame:
    """Apply the sidebar selection. Deliberately uncached — it runs in ~0.3 ms,
    far less than the ~12 ms it would cost to hash the frame for a cache key.

    An empty selection means "no restriction on this dimension", matching the
    behaviour the app has always had for communities.
    """
    mask = (df["startdate"] >= start) & (df["enddate"] <= end)
    if questions:
        mask &= df["q"].isin(questions)
    if communities:
        mask &= df["c"].isin(communities)
    if supercommunities:
        mask &= df["sc"].isin(supercommunities)
    return df[mask]


# --- Matrix -----------------------------------------------------------------


def build_matrix(fdf: pd.DataFrame, aggfunc: str = "min") -> pd.DataFrame:
    """Pivot the selection into the flat matrix frame the grid renders.

    Returned with a RangeIndex rather than the natural MultiIndex: styling a
    MultiIndexed frame makes pandas do a tuple ``get_loc`` per cell, and a flat
    index also lets the three label columns be pinned in the grid.
    """
    pivot = pd.pivot_table(
        fdf,
        values="mapped_values",
        index=["q", "reslabel", "res_np"],
        columns="c",
        aggfunc=aggfunc,
        fill_value=0,
        observed=True,
    )
    flat = pivot.reset_index()
    flat.columns = MATRIX_META + list(pivot.columns)
    flat[MATRIX_META[0]] = flat[MATRIX_META[0]].astype(str)
    return flat


def community_columns(flat: pd.DataFrame) -> list[str]:
    return list(flat.columns[len(MATRIX_META) :])


# --- Global statistics ------------------------------------------------------


@st.cache_data(show_spinner=False)
def global_stats(_df: pd.DataFrame, _mtime: float) -> dict:
    """Headline numbers for the whole dataset (independent of the selection)."""
    n_q = _df["q"].nunique()
    n_c = _df["c"].nunique()
    answered = _df.groupby(["c", "q"], observed=True).ngroups

    quarter = _df["date_ts"].dt.tz_localize(None).dt.to_period("Q").dt.to_timestamp()
    growth = (
        _df.assign(quarter=quarter)
        .groupby("quarter")["fip_index"]
        .nunique()
        .cumsum()
    )

    unmapped = int(_df["mapped_values"].isna().sum())

    return {
        "fips": int(_df["fip_index"].nunique()),
        "communities": int(n_c),
        "supercommunities": int(_df["sc"].nunique()),
        "resources": int(_df["reslabel"].nunique()),
        "declarations": int(len(_df)),
        "questions": int(n_q),
        "coverage": answered / (n_q * n_c),
        "fip_growth": growth,
        "first_date": _df["date_ts"].min(),
        "last_date": _df["date_ts"].max(),
        "unmapped": unmapped,
        "unmapped_share": unmapped / len(_df),
    }


@st.cache_data(show_spinner=False)
def declaration_mix(_df: pd.DataFrame, _mtime: float) -> pd.Series:
    counts = _df["rel"].value_counts()
    counts.index = [REL_LABELS.get(i, i) for i in counts.index]
    return counts


@st.cache_data(show_spinner=False)
def coverage_by_family(_df: pd.DataFrame, _mtime: float) -> pd.Series:
    """Declarations per FAIR family, in F-A-I-R order."""
    family = _df["q"].astype(str).str[0]
    counts = family.value_counts()
    return counts.reindex([f for f in "FAIR" if f in counts.index])


@st.cache_data(show_spinner=False)
def top_resources(_df: pd.DataFrame, _mtime: float, n: int = 5) -> pd.Series:
    """Most widely adopted resources, measured in distinct communities."""
    return top_resources_in(_df, n)


# --- Selection aggregates ---------------------------------------------------


def top_resources_in(fdf: pd.DataFrame, n: int = 15) -> pd.Series:
    return fdf.groupby("reslabel", observed=True)["c"].nunique().nlargest(n)


def selection_table(fdf: pd.DataFrame) -> pd.DataFrame:
    """Long-form table twin of the Analytics charts, so no value is reachable
    only by hovering a mark."""
    out = fdf.dropna(subset=["mapped_values"]).assign(
        Status=lambda d: d["mapped_values"].astype("int8").map(STATUS_LABELS)
    )
    out = out[["q", "c", "sc", "reslabel", "Status", "res_np"]].rename(
        columns={
            "q": "FIP question",
            "c": "Community",
            "sc": "Supercommunity",
            "reslabel": "FAIR Supporting Resource",
            "res_np": "Nanopublication",
        }
    )
    return out.sort_values(["FIP question", "Community"]).reset_index(drop=True)
