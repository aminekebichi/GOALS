# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

# GOALS — Game Outcome and Analytics Learning System

**Course:** EECE5644 — Introduction to Machine Learning and Pattern Recognition
**Team:** Amine Kebichi (regression + evaluation), Nathaniel Maw (clustering + classification)
**Deadline:** Final report + presentation — **April 18, 2026**

---

## Project Overview

GOALS is two things in one repo:

1. **ML Pipeline** — predicts La Liga match outcomes (Win/Draw/Loss) via position-specific composite performance scores built from FBref (season-level) + FotMob (match-level) player stats.
2. **Web App** (`goals_app/` + `frontend/`) — a local FastAPI + Svelte UI that wraps the pipeline, replacing manual notebook runs. Full spec in `GOALS_PRD.md`.

---

## Development Commands

### Backend (FastAPI)

```bash
# Install dependencies (from repo root, inside venv)
pip install fastapi uvicorn[standard] python-multipart sse-starlette \
    pandas polars pyarrow scikit-learn joblib rapidfuzz httpx aiofiles

# Run dev server with auto-reload
uvicorn goals_app.main:app --host 127.0.0.1 --port 8000 --reload

# API docs available at
http://localhost:8000/docs
```

### Frontend (SvelteKit)

```bash
cd frontend

# Install dependencies
npm install

# Dev server (proxies /api → localhost:8000)
npm run dev

# Production build (output goes to frontend/dist/, served by FastAPI)
npm run build
```

### One-click Launcher (production)

```bash
# From repo root — activates venv, builds frontend, starts uvicorn, opens browser
start.bat
```

### Jupyter (ML notebooks)

```bash
jupyter notebook                    # open any notebook in notebooks/
jupyter nbconvert --to notebook --execute notebooks/04_regression.ipynb
```

---

## Repository Structure

```
GOALS/
├── CLAUDE.md                        # This file
├── GOALS_PRD.md                     # Web app product requirements
├── start.bat                        # One-click launcher
│
├── goals_app/                       # FastAPI application
│   ├── main.py                      # App factory, router registration, static file mount
│   ├── config.py                    # DATA_ROOT, ARTIFACTS_DIR, path constants
│   ├── routers/
│   │   ├── scraper.py               # /api/scraper/start, /api/scraper/progress, /api/scraper/status
│   │   ├── calendar.py              # /api/matches, /api/matches/{id}
│   │   ├── stats.py                 # /api/players, /api/players/{id}/radar, /api/teams/form
│   │   └── settings.py              # /api/status, /api/pipeline/train, /api/pipeline/progress, /api/pipeline/metrics
│   ├── services/
│   │   ├── scraper_service.py       # Async functions extracted from fotmob_final.ipynb
│   │   ├── merge_service.py         # FBref + FotMob fuzzy join
│   │   ├── feature_service.py       # Z-score normalization + composite score computation
│   │   └── ml_service.py            # Train/predict (Ridge, RF regressor, RF classifier)
│   └── ml/
│       └── artifacts/               # git-ignored; written by ml_service.py
│           ├── ridge_{att,mid,def,gk}.pkl
│           ├── rf_regressor.pkl
│           ├── rf_classifier.pkl
│           ├── scaler.pkl
│           └── metrics.json
│
├── frontend/                        # SvelteKit application
│   ├── src/
│   │   ├── app.css                  # CSS variables — color palette lives here
│   │   ├── lib/components/          # MatchCard, ProbabilityBar, RadarChart, ProgressStream, etc.
│   │   ├── lib/stores/              # scraperStore.js, pipelineStore.js (SSE state)
│   │   └── routes/
│   │       ├── +layout.svelte       # Sidebar nav
│   │       ├── +page.svelte         # / → Match Calendar
│   │       ├── scraper/+page.svelte
│   │       ├── stats/+page.svelte
│   │       └── settings/+page.svelte
│   └── vite.config.js               # Proxies /api → localhost:8000 in dev
│
├── data/                            # READ-ONLY by the app
│   ├── FBref/premier_league/{season}/ # standard.csv, shooting.csv, misc.csv, goalkeeping.csv, playing_time.csv
│   ├── FBref/la_liga/{season}/
│   └── 47/{season}/                 # FotMob Premier League — scraped per season
│       ├── raw/                     # Cached JSON per match_id
│       └── output/                  # outfield_players.parquet, goalkeepers.parquet, fixtures.parquet
│
├── notebooks/                       # ML pipeline (run manually or via Settings page)
│   ├── 01_data_merge.ipynb
│   ├── 02_eda.ipynb
│   ├── 03_feature_engineering.ipynb
│   ├── 04_regression.ipynb
│   ├── 05_clustering.ipynb
│   └── 06_classification.ipynb
│
├── fotmob_final.ipynb               # Original FotMob scraper — do not modify
└── GOALS_notebook.ipynb             # FBref scraper — data already collected
```

**Season folder name conventions:**
- FBref: `2021-2022`, `2022-2023`, `2023-2024`, `2024-2025`
- FotMob: `2021_2022`, `2022_2023`, `2023_2024`, `2024_2025`

---

## Architecture

### Web App Data Flow

```
Browser (Svelte SPA)
  └─ HTTP + SSE ──► FastAPI (goals_app, port 8000)
                        ├─ routers/ ──► services/ ──► data/ (parquet/CSV, read-only)
                        │                         └──► ml/artifacts/ (pkl/json, read-write)
                        └─ static/ ──── frontend/dist/ (compiled Svelte)
```

FastAPI serves both the API (`/api/*`) and the compiled Svelte app (all other routes) from a single process. No separate Node server in production.

### SSE Pattern

Long-running operations (scraping 10–40 min, pipeline training) use Server-Sent Events:
- Client calls a `POST` endpoint → gets back a `job_id`.
- Client opens `GET /api/.../progress/{job_id}` as an `EventSource`.
- Server streams `{"type": "progress"|"stage"|"complete"|"error", ...}` events.
- `ProgressStream.svelte` handles all SSE consumption; `scraperStore.js` and `pipelineStore.js` hold job state.

### Service Layer

Each service is independently importable Python — no FastAPI dependency:

| Service | Responsibility |
|---------|---------------|
| `scraper_service.py` | Async FotMob fetching; idempotent (skips cached match IDs); `MAX_CONCURRENT=4` |
| `merge_service.py` | Fuzzy join FBref CSV + FotMob parquet on `(player_name, date, team)`; `rapidfuzz` threshold ≥ 85 |
| `feature_service.py` | Z-score normalize (fit on train only), compute ATT/MID/DEF/GK scores, aggregate to team level |
| `ml_service.py` | Walk-forward CV training, artifact serialization, `metrics.json` write |

### ML Pipeline Stages

```
DATA COLLECTION → MERGE → FEATURE ENGINEERING → REGRESSION TRAINING → CLASSIFICATION TRAINING → PREDICT
```

- **Train seasons:** 2021/22, 2022/23, 2023/24
- **Test season:** 2024/25 (held out — never used for fitting or CV)
- **CV strategy:** Walk-forward chronological within training seasons

---

## ML Specification

### Composite Score Formulas

All metrics z-score normalized (fit on train set only) before applying weights.

**ATT:**
```
ATT = 0.25*(Goals + Assists) + 0.20*xG + 0.15*xA + 0.15*Dribbles
    + 0.10*Shots + 0.10*ChancesCreated + 0.05*Recoveries
```

**MID:**
```
MID = 0.20*ProgPass + 0.20*ChancesCreated + 0.15*xA + 0.15*(Goals + Assists)
    + 0.15*TacklesWon + 0.10*Interceptions + 0.05*Recoveries
```

**DEF:**
```
DEF = 0.25*TacklesWon + 0.20*AerialDuelsWon + 0.20*Clearances
    + 0.15*Interceptions + 0.10*Blocks + 0.10*ProgPass
```

**GK:**
```
GK = 0.30*Saves + 0.25*xGOT + 0.15*DivingSaves + 0.15*SavesInsideBox
   + 0.10*HighClaims + 0.05*SweeperActions
```

**FotMob column mappings:**

| Formula term | parquet column |
|---|---|
| `Goals + Assists` | `goals` + `goal_assist` |
| `xG` | `expected_goals` |
| `xA` | `expected_assists` |
| `Dribbles` | `successful_dribbles` |
| `ChancesCreated` | `chances_created` |
| `Recoveries` | `recoveries` |
| `ProgPass` | `accurate_passes` (prefer FBref `progressive_passes`) |
| `TacklesWon` | `tackles_won` |
| `Interceptions` | `interceptions` |
| `AerialDuelsWon` | `aerial_duels_won` |
| `Clearances` | `clearances` |
| `Blocks` | `shot_blocks` |
| `Saves` | `saves` |
| `xGOT` | `xgot_faced` |
| `DivingSaves` | `diving_save` |
| `SavesInsideBox` | `saves_inside_box` |
| `HighClaims` | `high_claim` |
| `SweeperActions` | `acted_as_sweeper` |

**Team aggregation:** Sum composite scores of starting XI per position group → 4 values per team → 8 features total for classification (home ATT/MID/DEF/GK + away ATT/MID/DEF/GK).

### Models

| Notebook | Model | Target | Evaluation |
|----------|-------|--------|------------|
| `04_regression.ipynb` | Ridge, Random Forest Regressor | Composite score (continuous) | RMSE, MAE, R² |
| `05_clustering.ipynb` | K-Means | Player archetypes | Silhouette, Elbow |
| `06_classification.ipynb` | RF Classifier (+ LR, optional SVM) | Win/Draw/Loss | Accuracy, Macro F1, confusion matrix |

Always use `class_weight='balanced'` for classifiers (La Liga: ~45-50% home wins, ~25% draws, ~25-30% away wins).

---

## Key Constraints

1. **Never random-shuffle train/test** — always temporal split. Shuffling leaks future match results.
2. **Scaler fit on train only** — apply the same `StandardScaler` to test; never refit on test data.
3. **FotMob rate limiting** — `scraper_service.py` uses jitter + retries; do not raise `MAX_CONCURRENT` above 4.
4. **Player name mismatches** — FBref uses accented names; FotMob may differ. `rapidfuzz` threshold ≥ 85.
5. **FBref is season-level, FotMob is match-level** — FBref stats are contextual features; FotMob stats drive per-match composite scores.
6. **`fotmob_final.ipynb` is untouched** — scraper logic is extracted into `scraper_service.py`; original notebook is never modified.
7. **`data/` is read-only** by the app — only `scraper_service.py` writes new parquet files under `data/47/`.
8. **`goals_app/ml/artifacts/` is git-ignored** — models are regenerated locally via the Settings page.

---

## UI Color Palette

Defined in `frontend/src/app.css`:

```css
--bg-primary:        #0A0E1A;
--bg-secondary:      #111827;
--bg-tertiary:       #1C2333;
--accent-primary:    #FF4B44;   /* La Liga red-orange — CTAs */
--accent-secondary:  #FF7A00;   /* gradient pair */
--text-primary:      #F0F2F8;
--text-secondary:    #8B95A8;
--color-win:         #FF4B44;
--color-draw:        #C9A84C;
--color-loss:        #4488FF;
```

---

## Data Status

| Source | League | Seasons | Status |
|--------|--------|---------|--------|
| FBref | La Liga | 2021–2025 | ✅ Complete |
| FBref | Premier League | 2021–2025 | ✅ Complete |
| FBref | Bundesliga | 2021–2025 | ✅ Complete |
| FotMob | Premier League (47) | 2021–2025 | ⏳ Scraping in progress |
| FotMob | La Liga (87) | — | Not targeted |

To scrape Premier League via notebook: open `fotmob_final.ipynb`, set `LEAGUE_ID=47` and `SEASON='2021/2022'` (repeat for each season). Via app: use the `/scraper` page.

---

## Team Responsibilities

| Area | Owner |
|------|-------|
| FotMob La Liga scrape + `scraper_service.py` | Amine |
| Web app backend (`goals_app/`) | Amine |
| Data merge (01) + EDA (02) | Both |
| Feature engineering (03) + `feature_service.py` | Both |
| Regression (04) + `ml_service.py` | Amine |
| Clustering (05) | Nathaniel |
| Classification (06) | Nathaniel |
| Frontend (`frontend/`) | Both |
| Final report | Both |

---

## Timeline

| Date | Milestone |
|------|-----------|
| March 20, 2026 | Milestone 3 begins |
| ~March 25, 2026 | Web app scaffold + scraper UI working |
| ~March 28, 2026 | FotMob La Liga scrape complete + data merge done |
| ~April 4, 2026 | ML pipeline backend + Settings page working |
| ~April 5, 2026 | Regression + clustering results ready |
| ~April 10, 2026 | Calendar + Stats UI complete |
| ~April 12, 2026 | Classification complete, full pipeline validated |
| ~April 14, 2026 | App polish + end-to-end integration test |
| **April 18, 2026** | **Final report + presentation due** |
