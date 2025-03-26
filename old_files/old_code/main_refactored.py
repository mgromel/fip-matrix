import pandas as pd
import streamlit as st
import numpy as np
import datetime
import plotly.express as px

# --- Config
st.set_page_config(layout="wide", page_title='FIP Matrix', page_icon='🔍')
st.title('Interactive FIP convergence matrix')

# --- Load and preprocess data
@st.cache_data(persist='disk')
def load_and_prepare_data(path):
    df = pd.read_csv(path)
    df['mapped_values'] = df.apply(map_relation_value, axis=1)
    df = fill_and_convert_dates(df)
    return df

def map_relation_value(row):
    available_map = {
        'https://w3id.org/fair/fip/terms/declares-current-use-of': 3,
        'https://w3id.org/fair/fip/terms/declares-planned-use-of': 2,
        'https://w3id.org/fair/fip/terms/declares-planned-replacement-of': 3
    }
    tbd_map = {
        'https://w3id.org/fair/fip/terms/declares-current-use-of': None,
        'https://w3id.org/fair/fip/terms/declares-planned-use-of': 1,
        'https://w3id.org/fair/fip/terms/declares-planned-replacement-of': None
    }
    if row['resourcetype'] == 'https://w3id.org/fair/fip/terms/Available-FAIR-Enabling-Resource':
        return available_map.get(row['rel'], None)
    elif row['resourcetype'] == 'https://w3id.org/fair/fip/terms/FAIR-Enabling-Resource-to-be-Developed':
        return tbd_map.get(row['rel'], None)
    return None

def fill_and_convert_dates(df):
    min_start = pd.to_datetime(df['startdate'].dropna()).min().date()
    max_end = pd.to_datetime(df['enddate'].dropna()).max().date()

    df['startdate'] = pd.to_datetime(df['startdate'].fillna(min_start)).dt.date
    df['enddate'] = pd.to_datetime(df['enddate'].fillna(max_end)).dt.date
    return df

df = load_and_prepare_data('./new_matrix.csv')

# --- Filters and inputs
princ = sorted(df['q'].dropna().unique())
comm = sorted(df['c'].dropna().unique())

col1, col2 = st.columns(2)
with col1:
    min_date, max_date = df['startdate'].min(), df['enddate'].max()
    star = st.date_input('Start date', value=min_date, min_value=min_date, max_value=max_date)
    fip_questions = st.multiselect('FIP questions:', options=princ, default=princ[:5])
with col2:
    end = st.date_input('End date', value=max_date, min_value=min_date, max_value=max_date)
    communities = st.multiselect('Communities:', options=comm)

# --- Filter dataframe
@st.cache_data
def filter_data(df, star, end, fip_q, comms):
    filtered = df[(df['startdate'] >= star) & (df['enddate'] <= end)]
    if fip_q:
        filtered = filtered[filtered['q'].isin(fip_q)]
    if comms:
        filtered = filtered[filtered['c'].isin(comms)]
    return filtered

filtered_df = filter_data(df, star, end, fip_questions, communities)

# --- Pivot and display
filtered_df = filtered_df.rename(columns={'q': 'FIP questions', 'reslabel': 'FAIR Supporting Resource', 'res_np': 'Link'})
pivot_raw = pd.pivot_table(
    filtered_df, values='mapped_values',
    index=['FIP questions', 'FAIR Supporting Resource', 'Link'],
    columns='c', aggfunc='min', fill_value=0
)

def style_fip_matrix(val):
    color_map = {
        0: '#fcebe6',
        1: 'lightblue',
        2: '#e5fa98',
        3: '#8de879'
    }
    return f"background-color: {color_map.get(val, 'white')}; color: transparent;"

st.dataframe(
    pivot_raw.style.map(style_fip_matrix),
    use_container_width=True,
    column_config={
        "Link": st.column_config.LinkColumn(help='Links to nanopublications of each FER', display_text='🔗')
    }
)

# --- Legend
legend = pd.DataFrame([0,1,2,3], index=[
    'No data','Resource in development/future use','Available resource/future use','Available resource/current use'
], columns=['LEGEND'])
legend.index.name='FAIR Supporting Resource status'

st.dataframe(legend.style.map(style_fip_matrix), use_container_width=False)
