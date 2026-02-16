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

FOOTER_HEIGHT = 55  

import streamlit.components.v1 as components

footer_html = f"""
<style>
  #app-footer {{
    position: fixed;
    left: 0;
    right: 0;
    bottom: 0;
    height: 70px;
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 40px;
    z-index: 10000;
    background: #f9f9f9;
  }}

  #app-footer img {{
    height: 45px;
    object-fit: contain;
  }}

  #app-footer::before {{
    content: "";
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 1px;
    background: #e0e0e0;
  }}

  #app-footer.light {{
    background: #f9f9f9 !important;
  }}
  #app-footer.light::before {{
    background: #e0e0e0;
  }}

  #app-footer.dark {{
    background: #0e1117 !important;
  }}
  #app-footer.dark::before {{
    background: #30363d;
  }}
</style>

<div id="app-footer" class="light">
  {''.join([f'<img src="data:image/png;base64,{l}" alt="logo"/>' for l in logos])}
</div>

<script>
console.log("Script starting...");

(function () {{
  const parentDoc = window.parent.document;
  
  function initFooter() {{
    // Footer is in parent document, not iframe
    const footer = parentDoc.getElementById("app-footer");
    if (!footer) {{
      console.log("Footer not found, retrying...");
      return false;
    }}

    console.log("Footer found!");

    function parseRGB(str) {{
      const m = str.match(/\\d+(\\.\\d+)?/g);
      if (!m || m.length < 3) return null;
      return [Number(m[0]), Number(m[1]), Number(m[2])];
    }}

    function luminance(rgb) {{
      const [r, g, b] = rgb;
      return 0.2126*r + 0.7152*g + 0.0722*b;
    }}

    function pickThemeByTextColor() {{
      const el =
        parentDoc.querySelector('section[data-testid="stMain"]') ||
        parentDoc.querySelector('[data-testid="stAppViewContainer"]') ||
        parentDoc.querySelector('.stApp') ||
        parentDoc.body;

      const colorStr = window.parent.getComputedStyle(el).color;
      console.log("Text color:", colorStr);
      const rgb = parseRGB(colorStr) || [0,0,0];
      const lum = luminance(rgb);
      console.log("Luminance:", lum);

      return lum > 128 ? "dark" : "light";
    }}

    function pickTheme() {{
      try {{
        if (window.parent.matchMedia && window.parent.matchMedia('(prefers-color-scheme: dark)').matches) {{
          console.log("System prefers dark");
        }}
      }} catch (e) {{}}

      return pickThemeByTextColor();
    }}

    function applyTheme() {{
      const theme = pickTheme();
      console.log("Applying theme:", theme);
      footer.classList.remove("light","dark");
      footer.classList.add(theme);
    }}

    applyTheme();

    const obs = new MutationObserver(() => {{
      console.log("DOM mutation detected, reapplying theme");
      applyTheme();
    }});
    obs.observe(parentDoc.documentElement, {{ attributes: true, childList: true, subtree: true }});

    try {{
      const mq = window.parent.matchMedia('(prefers-color-scheme: dark)');
      if (mq && mq.addEventListener) mq.addEventListener('change', applyTheme);
      else if (mq && mq.addListener) mq.addListener(applyTheme);
    }} catch (e) {{}}

    window.parent.addEventListener("resize", applyTheme);
    
    return true;
  }}

  let retries = 0;
  const maxRetries = 50;
  const retryInterval = setInterval(() => {{
    if (initFooter() || retries++ > maxRetries) {{
      clearInterval(retryInterval);
      if (retries > maxRetries) {{
        console.log("Footer initialization failed after max retries");
      }}
    }}
  }}, 100);
}})();
</script>
"""

components.html(footer_html, height=0)

st.markdown(
    """
    <style>
      section[data-testid="stMain"] .block-container {
        padding-bottom: 94px !important;
      }
    </style>
    """,
    unsafe_allow_html=True
)