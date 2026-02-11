import streamlit as st
import pandas as pd
from config import COLOR_MAP
from utils import load_and_prepare_data, filter_data
import base64
from pathlib import Path

st.set_page_config(layout="wide", page_title='FIP Matrix', page_icon='🔍')
st.title('Interactive FIP Matrix')

# --- Load data
df = load_and_prepare_data('./data/new_matrix.csv')

# --- Inputs
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

filtered_df = filter_data(df, star, end, fip_questions, communities)
filtered_df = filtered_df.rename(columns={'q': 'FIP questions', 'reslabel': 'FAIR Supporting Resource', 'res_np': 'Link'})

pivot_raw = pd.pivot_table(
    filtered_df,
    values='mapped_values',
    index=['FIP questions', 'FAIR Supporting Resource', 'Link'],
    columns='c',
    aggfunc='min',
    fill_value=0
)

def style_fip_matrix(val):
    return f"background-color: {COLOR_MAP.get(val, 'white')}; color: transparent;"

st.dataframe(
    pivot_raw.style.map(style_fip_matrix),
    use_container_width=True,
    column_config={
        "Link": st.column_config.LinkColumn(help='Links to nanopublications of each FER', display_text='🔗')
    }
)

# --- Legend
legend = pd.DataFrame([0, 1, 2, 3], index=[
    'No data','Resource in development/future use','Available resource/future use','Available resource/current use'
], columns=['LEGEND'])
legend.index.name='FAIR Supporting Resource status'

st.dataframe(legend.style.map(style_fip_matrix), use_container_width=False)


# --- Footer
def img_to_base64(img_path):
    with open(img_path, "rb") as f:
        return base64.b64encode(f.read()).decode()

assets = Path(__file__).parent / "assets"

logos = [
    img_to_base64(assets / "parc_logo.png"),
    img_to_base64(assets / "gff_logo.png"),
    # img_to_base64(assets / "xxx.png"),
]

st.markdown(
    f"""
    <style>
    .footer {{
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: rgb(14, 17, 23);
        border-top: 1px solid #212121;
        padding: 10px 0;
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 40px;
        z-index: 100;
    }}
    .footer img {{
        height: 45px;
    }}
    </style>

    <div class="footer">
        {''.join([f'<img src="data:image/png;base64,{logo}"/>' for logo in logos])}
    </div>
    """,
    unsafe_allow_html=True
)