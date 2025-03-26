import pandas as pd
from datetime import datetime
import streamlit as st
from config import AVAILABLE_MAP, TBD_MAP

@st.cache_data
def load_and_prepare_data(path):
    df = pd.read_csv(path)
    df['mapped_values'] = df.apply(map_relation_value, axis=1)
    df = fill_and_convert_dates(df)
    return df

def map_relation_value(row):
    if row['resourcetype'] == 'https://w3id.org/fair/fip/terms/Available-FAIR-Enabling-Resource':
        return AVAILABLE_MAP.get(row['rel'], None)
    elif row['resourcetype'] == 'https://w3id.org/fair/fip/terms/FAIR-Enabling-Resource-to-be-Developed':
        return TBD_MAP.get(row['rel'], None)
    return None

def fill_and_convert_dates(df):
    min_start = pd.to_datetime(df['startdate'].dropna()).min().date()
    max_end = pd.to_datetime(df['enddate'].dropna()).max().date()

    df['startdate'] = pd.to_datetime(df['startdate'].fillna(min_start)).dt.date
    df['enddate'] = pd.to_datetime(df['enddate'].fillna(max_end)).dt.date
    return df

@st.cache_data
def filter_data(df, star, end, fip_q=None, comms=None):
    filtered = df[(df['startdate'] >= star) & (df['enddate'] <= end)]
    if fip_q:
        filtered = filtered[filtered['q'].isin(fip_q)]
    if comms:
        filtered = filtered[filtered['c'].isin(comms)]
    return filtered
