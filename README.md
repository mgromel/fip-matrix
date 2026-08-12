# FIP Matrix App

A Streamlit-based interactive application for visualizing FAIR convergence data from nanopublications.

Three views over the same selection:

- **Overview** — headline statistics for the whole dataset.
- **Matrix** — the convergence matrix: FAIR Enabling Resources × communities.
- **Analytics** — interactive Plotly charts of the current selection.

## 🔁 Data Synchronization

This app automatically fetches the latest `new_matrix.csv` from the [peta-pico/dsw-nanopub-api](https://github.com/peta-pico/dsw-nanopub-api) repository **once a day** (`cron: '0 0 * * *'`) using GitHub Actions.
The CSV is saved to `data/new_matrix.csv` and used live in the app.

> `data/new_matrix.csv` is a contract with `.github/workflows/sync_fip_matrix.yml` —
> the workflow's `curl -o` writes to exactly that path and will not create the
> directory. Don't move or rename either.

## 📦 Structure

```
.
├── main.py                     # Streamlit entry point (must stay at the root)
├── config.py                   # Paths, FIP vocabulary, status scale, palette
├── utils.py                    # Loading, filtering, pivoting, aggregation
├── matrix.py                   # The convergence matrix grid
├── charts.py                   # Plotly figure builders
├── ui.py                       # Header, statistics band, legend, logos
├── .streamlit/config.toml      # Theme (light + dark)
├── data/
│   └── new_matrix.csv          # Auto-updated data file
└── .github/workflows/
    └── sync_fip_matrix.yml     # Data sync workflow
```

## 🎨 Status scale

| Status | Meaning | Colour | Compact |
|---|---|---|---|
| 0 | No data | *unfilled* | |
| 1 | Resource in development / future use | `#47afff` cool sky | ○ |
| 2 | Available resource / future use | `#d8b083` tan | ◐ |
| 3 | Available resource / current use | `#86eaaf` celadon | ● |

Cells are 44px and isolated in a 96%-empty grid, where hue separation reads far
more easily than lightness, so the scale is treated as categorical rather than as
a single-hue ramp. Worst-pair separation is ΔE 16.3 for normal vision and 7.8
under simulated colour-vision deficiency; the second figure calls for a secondary
encoding, which Compact mode's ○ ◐ ● and the labelled legend provide — status
never depends on colour alone.

The grid has two render modes. **Colour** paints cell backgrounds; **Compact**
draws glyphs and involves no CSS at all, which keeps wide selections fast. It is
selected automatically for large selections and can be overridden.

## 🚀 Run locally

```bash
pip install -r requirements.txt
streamlit run main.py
```

Run from the repository root. The CSV is resolved relative to `config.py`, so the
app is not sensitive to the working directory.
