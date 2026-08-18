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
├── tools/
│   └── check_palette.py        # Verifies every colour figure quoted below
├── data/
│   └── new_matrix.csv          # Auto-updated data file
└── .github/workflows/
    └── sync_fip_matrix.yml     # Data sync workflow
```

## 🎨 Status scale

| Status | Meaning | Colour | Compact |
|---|---|---|---|
| 0 | No data | *unfilled* | |
| 1 | Resource in development / future use | `#f0a182` apricot | ○ |
| 2 | Available resource / future use | `#2f6699` blue | ◐ |
| 3 | Available resource / current use | `#b0f05c` lime | ● |

Cells are 44px and isolated in a 96%-empty grid, where hue separation reads far
more easily than lightness, so the scale is treated as categorical rather than as
a single-hue ramp.

Every figure below is produced by the checker, so none of it is written by hand:

```bash
python tools/check_palette.py
```

It reads the palette from `config.py` and the theme from `.streamlit/config.toml`,
so it cannot fall out of step with them. It exits non-zero when a rule is broken.
`PASS`/`FAIL` lines are the rules; `INFO` lines are documented trade-offs.

Worst-pair separation, stated per metric so the figures cannot drift apart again:

| | normal vision | worst dichromat |
|---|---|---|
| ΔE76 | 63.6 | 24.8 (protanopia) |
| ΔE2000 | 30.8 | 12.6 (deuteranopia) |

Dichromat figures come from a Viénot–Brettel–Mollon (1999) simulation over
protanopia, deuteranopia and tritanopia. On ΔE76 the worst dichromat pair clears
the project's ΔE 15 floor; on the stricter ΔE2000 it falls short at 12.6. So the
scale does not rest on colour alone: Compact mode's ○ ◐ ● and the labelled legend
carry the same information as a secondary encoding.

These are pastels, so the trade is contrast. On the light surface the three
measure 1.3–2.0:1 and read soft; on the dark surface they are 8.4–12.8:1 and pop.
Level 3 is the faintest in light mode at 1.32:1 — darken each hue a step if the
cells ever feel too weak.

Blue is deliberately absent here. Blue means "chrome or chart" throughout the app
— the theme `primaryColor`, the `SEQUENTIAL` ramp and the `SERIES` mark colour all
sit in one blue family — so keeping it out of the status scale is what stops a
button or a chart bar from being read as a status.

The grid has two render modes. **Colour** paints cell backgrounds; **Compact**
draws glyphs and involves no CSS at all, which keeps wide selections fast. It is
selected automatically for large selections and can be overridden.

## 📈 Chart palette

| Token | Colour | Used for |
|---|---|---|
| `SERIES` | `#2f85c2` blue | single-series magnitude |
| `SERIES_ALT` | `#c2553f` brick | only where a chart has its own legend (Metadata vs Data) |
| `SEQUENTIAL` | `#e3eefa` → `#2f6699` | continuous magnitude, one hue, monotone in OKLCH lightness |

Chart marks are mid-tones, not pastels, because they must clear 3:1 against both a
near-white and a near-black background — no pastel does both. The pair separates at
ΔE2000 45.2, and still at 44.5 under the worst simulated dichromat, which matters
because colour is the only thing distinguishing the two series.

One chart reuses the status colours directly for its stacked segments. That is
intentional: those segments *are* the status scale.

## 🚀 Run locally

```bash
pip install -r requirements.txt
streamlit run main.py
```

Run from the repository root. The CSV is resolved relative to `config.py`, so the
app is not sensitive to the working directory.
