# Daily PnL Tracking (Value/Momentum) — Streamlit App

This repo contains a Streamlit dashboard + a daily runner that exports `signals.csv`, `positions.csv`, and `daily_summary.csv`.

## Quick start (local)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Real data input

Place per-ticker CSV files in `data/` named like `data/BRK-B.csv`.

Expected columns:
- `Date` (YYYY-MM-DD)
- `Open`, `High`, `Low`, `Close`, `Volume`

## Daily automation (cron)

Export daily CSV outputs to `outputs/`:

```bash
python run_daily.py
```

Example cron (17:00 UTC):

```cron
0 17 * * * cd /path/to/repo && ./.venv/bin/python run_daily.py >> outputs/daily_pnl.log 2>&1
```

## Deploy to Streamlit Community Cloud

1. Push this repo to GitHub.
2. In Streamlit Cloud, create a new app.
3. Select `app.py` as the entrypoint.
4. Add secrets/env vars if you later integrate a data API.
