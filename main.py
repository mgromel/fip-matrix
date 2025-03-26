import pandas as pd
import streamlit as st
import numpy as np
import datetime
import plotly.express as px

st.set_page_config(layout="wide")
st.title('Interactive FIP convergence matrix')
df = pd.read_csv('./new_matrix.csv')

available_fers = df[df['resourcetype'] == 'https://w3id.org/fair/fip/terms/Available-FAIR-Enabling-Resource']
tbd_fers = df[df['resourcetype'] == 'https://w3id.org/fair/fip/terms/FAIR-Enabling-Resource-to-be-Developed']

available_fers_mappings = {
    'https://w3id.org/fair/fip/terms/declares-current-use-of' : 3,
    'https://w3id.org/fair/fip/terms/declares-planned-use-of' : 2,
    'https://w3id.org/fair/fip/terms/declares-planned-replacement-of': 3
}

tbd_fers_mappings ={
    'https://w3id.org/fair/fip/terms/declares-current-use-of' : None,
    'https://w3id.org/fair/fip/terms/declares-planned-use-of' : 1,
    'https://w3id.org/fair/fip/terms/declares-planned-replacement-of': None
}

available_fers['mapped_values'] = available_fers['rel'].map(available_fers_mappings)
tbd_fers['mapped_values'] = tbd_fers['rel'].map(tbd_fers_mappings)

mapped_df = pd.concat([available_fers, tbd_fers])


min_start = datetime.datetime.strptime(min(mapped_df['startdate'].dropna(axis=0)), '%Y-%m-%d').date()
max_start = datetime.datetime.strptime(max(mapped_df['startdate'].dropna(axis=0)), '%Y-%m-%d').date()
min_end = datetime.datetime.strptime(min(mapped_df['enddate'].dropna(axis=0)), '%Y-%m-%d').date()
max_end = datetime.datetime.strptime(max(mapped_df['enddate'].dropna(axis=0)), '%Y-%m-%d').date()

# fill empty dates if start date is na: fill with min_start, if enddate is na: fill with max_end
mapped_df['startdate'].fillna(min_start, inplace=True)
mapped_df['enddate'].fillna(max_end, inplace=True)

#there was a mess with date type, code below fixes it with pd.to_datetime conversion
mapped_df['startdate'] = pd.to_datetime(mapped_df['startdate']).dt.date
mapped_df['enddate'] = pd.to_datetime(mapped_df['enddate']).dt.date
#####

princ = np.unique(mapped_df['q'])
comm = np.unique(mapped_df['c'])
st.header("Select time period for the FIP matrix")

col1, col2 = st.columns(2)
with col1:
    star = st.date_input('Start date', value=min_start, min_value=min_start, max_value=max_start)
    fip_questions = st.multiselect('FIP questions:', options=princ, default=princ[0:5])

with col2:
    end = st.date_input('End date', value=max_end, min_value=min_end, max_value=max_end)
    communities = st.multiselect('Communities:', options=comm)

filtered_df = mapped_df[(mapped_df['startdate'] >= star) & (mapped_df['enddate'] <= end)]


if len(communities) > 0 and len(fip_questions) > 0:
    filtered_df = filtered_df.query('q in @fip_questions and c in @communities')
elif len(communities) > 0 and len(fip_questions) == 0:
    filtered_df = filtered_df.query('c in @communities')
elif len(communities) == 0 and len(fip_questions) > 0:
    filtered_df = filtered_df.query('q in @fip_questions')
else:
    filtered_df = filtered_df

filtered_df = filtered_df.rename(columns={'q':'FIP questions', 'reslabel':'FAIR Supporting Resource', 'res_np':'Link'})

pivot_raw = pd.pivot_table(filtered_df, values='mapped_values', index=['FIP questions', 'FAIR Supporting Resource', 'Link'], columns=['c'], aggfunc='min', fill_value=0)
pivot_styled = pivot_raw.style.map(lambda x: 
                       f"background-color: {'#8de879' if x >= 3 else ('#e5fa98' if x == 2 else ('#fcebe6' if x == 0 else ('lightblue' if x == 1 else 'white')))}; color: {'white' if x is None else 'transparent'};")

st.dataframe(pivot_styled, 
             use_container_width=True,
             column_config={
                "Link" : st.column_config.LinkColumn(
                    help='Links to nanopublications of each FER',
                    display_text='🔗'
                )
             })


dat = [0,1,2,3]
idx = ['No data','Resource in development/future use','Available resource/future use','Available resource/current use']
leg = pd.DataFrame(dat, index=idx, columns=['LEGEND'])

st.dataframe(leg.style.map(lambda x: 
                       f"background-color: {'#8de879' if x >= 3 else ('#e5fa98' if x == 2 else ('#fcebe6' if x == 0 else ('lightblue' if x == 1 else 'white')))}; color: {'white' if x is None else 'transparent'};"))