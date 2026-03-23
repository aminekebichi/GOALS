# GOALS — Setup Guide

Run all commands from `C:\Users\amine\OneDrive\Documents\git_workspace\GOALS` in PowerShell.

---

## 1. Install Python dependencies

```powershell
python -m pip install fastapi uvicorn joblib scikit-learn pandas pyarrow aiofiles beautifulsoup4 requests
```

---

## 2. Build the frontend

```powershell
cd frontend
npm install --legacy-peer-deps
npm run build
cd ..
```

---

## 3. Train the model

> Only run this after at least one season of FotMob La Liga data is scraped.
> Currently available: `2021_2022`. Once the other seasons are scraped via
> `fotmob_final.ipynb`, rerun with all seasons (the default).

```powershell
# With only 2021/22 available:
python train.py --seasons 2021_2022

# After all seasons are scraped (2022/23, 2023/24, 2024/25):
python train.py
```

---

## 4. Start the server

```powershell
uvicorn goals_app.main:app --host 127.0.0.1 --port 8000 --reload
```

Then open **http://localhost:8000** in your browser.

---

## Scraping future fixtures (run this first)

To see upcoming matches in the calendar, scrape the fixture list for any season:

```powershell
# 2024/25 La Liga (default)
python scrape_fixtures.py

# Any other season
python scrape_fixtures.py --season 2023_2024
```

This is a fast, lightweight scrape (seconds, not minutes). It fetches the full fixture
list — played and unplayed — and saves it to `data/87/{season}/output/fixtures.parquet`.
Predictions for upcoming matches are generated automatically using team averages from
the training data.

---

## Scraping player stats for past seasons

Before training on the full dataset, scrape La Liga data for the missing seasons
by running `fotmob_final.ipynb` three times with these settings:

| Run | `LEAGUE_ID` | `SEASON`    |
|-----|-------------|-------------|
| 1   | `87`        | `2022/2023` |
| 2   | `87`        | `2023/2024` |
| 3   | `87`        | `2024/2025` |

Then retrain: `python train.py`
