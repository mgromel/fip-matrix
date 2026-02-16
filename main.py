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
    img_to_base64(assets / "GFF_logo.png"),
    # img_to_base64(assets / "xxx.png"),
]

st.markdown(
    f"""
    <style>
    .footer {{
        position: fixed;
        left: 0; bottom: 0;
        width: 100%;
        padding: 10px 0;
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 40px;
        z-index: 100;
        border-top: 1px solid;
 
    }}
    .footer img {{
        height: 45px;
        object-fit: contain;
    }}

    .footer.light {{
        background: #f9f9f9;
        border-top-color: #d6d4d4;
    }}
    .footer.dark {{
        background: #0e1117;
        border-top-color: #d6d4d4;
    }}
    </style>

    <div class="footer" id="app-footer">
        {''.join([f'<img src="data:image/png;base64,{l}"/>' for l in logos])}
    </div>

    <script>
    (function() {{
        const footer = window.parent.document.getElementById("app-footer");
        if (!footer) return;

        function setThemeClass() {{
            const body = window.parent.document.body;
            const bg = window.parent.getComputedStyle(body).backgroundColor;

            // bg w formacie "rgb(r, g, b)" – liczymy jasność
            const m = bg.match(/\\d+/g);
            if (!m || m.length < 3) return;
            const r = parseInt(m[0]), g = parseInt(m[1]), b = parseInt(m[2]);
            const luminance = 0.2126*r + 0.7152*g + 0.0722*b;

            footer.classList.remove("light","dark");
            footer.classList.add(luminance > 128 ? "light" : "dark");
        }}

        setThemeClass();
        // reaguj na zmiany (np. przełączenie motywu)
        const obs = new MutationObserver(setThemeClass);
        obs.observe(window.parent.document.body, {{ attributes: true, childList: true, subtree: true }});
        window.addEventListener("resize", setThemeClass);
    }})();
    </script>
    """,
    unsafe_allow_html=True
)