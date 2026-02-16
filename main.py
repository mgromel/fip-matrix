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

FOOTER_HEIGHT = 45  

st.markdown(
    f"""
    <style>
      :root {{
        --footer-h: {FOOTER_HEIGHT}px;
      }}

      /* Zrób miejsce na fixed footer (najważniejsze!) */
      section[data-testid="stMain"] .block-container {{
        padding-bottom: calc(var(--footer-h) + 24px) !important;
      }}

      #app-footer {{
        position: fixed;
        left: 0; right: 0; bottom: 0;
        height: var(--footer-h);
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 40px;
        z-index: 10000;
        background: rgba(0,0,0,0); /* zostanie nadpisane klasą light/dark */
        pointer-events: none; /* żeby footer nie blokował scroll/klików pod spodem */
      }}

      #app-footer img {{
        height: 45px;
        object-fit: contain;
        pointer-events: auto; /* jakbyś chciał linkować loga */
      }}

      /* Border jako overlay – pewniejsze niż border-top */
      #app-footer::before {{
        content: "";
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 1px;
        background: transparent;
      }}

      #app-footer.light {{
        background: #f9f9f9 !important;
      }}
      #app-footer.light::before {{
        background: #e0e0e0 !important;
      }}

      #app-footer.dark {{
        background: #0e1117 !important;
      }}
      #app-footer.dark::before {{
        background: #30363d !important;
      }}
    </style>

    <div id="app-footer" class="light">
      {''.join([f'<img src="data:image/png;base64,{l}" alt="logo"/>' for l in logos])}
    </div>

    <script>
      (function() {{
        const doc = window.parent.document;
        const footer = doc.getElementById("app-footer");
        if (!footer) return;

        function getLuminance(rgbStr) {{
          const m = rgbStr.match(/\\d+/g);
          if (!m || m.length < 3) return 255;
          const r = parseInt(m[0]), g = parseInt(m[1]), b = parseInt(m[2]);
          return 0.2126*r + 0.7152*g + 0.0722*b;
        }}

        function setThemeClass() {{
          // Streamlit czasem ustawia tło na wrapperach, nie na body
          const main = doc.querySelector('section[data-testid="stMain"]');
          const target = main || doc.body;

          const bg = window.getComputedStyle(target).backgroundColor;
          const lum = getLuminance(bg);

          footer.classList.remove("light","dark");
          footer.classList.add(lum > 128 ? "light" : "dark");
        }}

        setThemeClass();

        // Obserwuj zmiany atrybutów i stylów (przełączenia motywu, rerender)
        const obs = new MutationObserver(() => setThemeClass());
        obs.observe(doc.documentElement, {{ attributes: true, childList: true, subtree: true }});
        obs.observe(doc.body, {{ attributes: true, childList: true, subtree: true }});

        window.addEventListener("resize", setThemeClass);
      }})();
    </script>
    """,
    unsafe_allow_html=True
)