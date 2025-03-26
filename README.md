# FIP Matrix App

A Streamlit-based interactive application for visualizing FAIR convergence data from nanopublications.

## 🔁 Data Synchronization

This app automatically fetches the latest `new_matrix.csv` from the [peta-pico/dsw-nanopub-api](https://github.com/peta-pico/dsw-nanopub-api) repository every hour using GitHub Actions.  
The CSV is saved in the `data/` directory and used live in the app.

## 📦 Structure

```
.
├── app/
│   ├── main.py          # Streamlit app
│   └── utils.py         # Data logic
├── data/
│   └── new_matrix.csv   # Auto-updated data file
├── .github/workflows/
│   └── sync_fip_matrix.yml  # Data sync workflow
```

## 🚀 Run locally

```bash
streamlit run app/main.py
```
