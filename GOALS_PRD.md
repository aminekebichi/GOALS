# GOALS Web Application — Product Requirements Document

**Project:** GOALS (Game Outcome and Analytics Learning System)
**App Type:** Local web application wrapping the GOALS ML pipeline
**Tech Stack:** FastAPI + Svelte
**Version:** 1.0
**Last Updated:** 2026-03-22

---

## Table of Contents

1. [Overview](#1-overview)
2. [Tech Stack](#2-tech-stack)
3. [Repository Layout](#3-repository-layout)
4. [Architecture](#4-architecture)
5. [Feature Specifications](#5-feature-specifications)
6. [UI/UX Design](#6-uiux-design)
7. [Data & Storage](#7-data--storage)
8. [API Design](#8-api-design)
9. [Implementation Sequence](#9-implementation-sequence)

---

## 1. Overview

### What It Is

GOALS Web App is a local-first web application that wraps the entire GOALS ML pipeline behind a browser UI. It eliminates the need to run Jupyter notebooks manually for scraping, training, and predicting La Liga match outcomes.

### What It Replaces

| Before (manual) | After (app) |
|-----------------|-------------|
| Edit config cells in `fotmob_final.ipynb`, run 4× per season | Scraper page with season selector + one-click start |
| Run `04_regression.ipynb` + `06_classification.ipynb` manually | Settings page with "Train Pipeline" button + live progress |
| Parse raw parquet/CSV to interpret results | Match Calendar with visual probability bars per outcome |
| No player-level insight without notebook exploration | Stats section with composite score grids and radar charts |

### Goals

1. **Operationalize** the ML pipeline for interactive use without requiring notebook knowledge.
2. **Visualize** match outcome predictions in a calendar format with win/draw/loss probabilities.
3. **Expose** player and team composite scores from the feature engineering stage.
4. **Centralize** data status and model health in a single Settings view.

### Non-Goals

- No remote deployment — this is a local tool running on `localhost`.
- No user authentication.
- No database — all persistence is flat files (parquet, CSV, pickle).
- No support for leagues other than La Liga (ID 87) in v1.

---

## 2. Tech Stack

### Backend — FastAPI

**Why FastAPI:**
- Native `async` support — critical for non-blocking scraper runs (10–40 min per season).
- Built-in Server-Sent Events (SSE) for streaming scraper and training progress to the frontend.
- First-class Python integration — ML pipeline (scikit-learn, pandas, polars) runs in the same process.
- Auto-generated OpenAPI docs at `/docs` — useful during development.

**Backend dependencies:**

```
fastapi>=0.111.0
uvicorn[standard]>=0.29.0
python-multipart>=0.0.9
sse-starlette>=2.1.0         # SSE streaming
pandas>=2.2.0
polars>=0.20.0
pyarrow>=15.0.0
scikit-learn>=1.4.0
joblib>=1.4.0                # model serialization
rapidfuzz>=3.8.0             # fuzzy player name matching
httpx>=0.27.0                # async HTTP (FotMob scraper)
aiofiles>=23.2.1
```

### Frontend — Svelte

**Why Svelte:**
- Compiles to vanilla JS — no virtual DOM overhead, fast initial load.
- Minimal boilerplate for reactive state (stores, bindings).
- SvelteKit routing gives a clean `/`, `/scraper`, `/stats`, `/settings` structure.
- Easy integration with native `EventSource` API for SSE consumption.

**Frontend dependencies:**

```
@sveltejs/kit>=2.5.0
svelte>=4.2.0
vite>=5.2.0
chart.js>=4.4.0              # radar + bar charts
```

### Launcher

A single `start.bat` at repo root:
1. Activates the Python virtual environment.
2. Runs `npm run build` in `frontend/` (if dist is stale).
3. Starts `uvicorn goals_app.main:app --host 127.0.0.1 --port 8000`.
4. Opens `http://localhost:8000` in the default browser.

FastAPI serves the compiled Svelte `dist/` as static files at `/`, so no separate Node server is needed in production.

---

## 3. Repository Layout

New directories are added alongside the existing structure. Nothing in `data/`, `notebooks/`, or existing notebooks is modified.

```
GOALS/
├── CLAUDE.md
├── GOALS_PRD.md                        # This document
├── start.bat                           # One-click launcher
│
├── goals_app/                          # FastAPI application
│   ├── main.py                         # App factory, static file mount, router registration
│   ├── config.py                       # Paths, constants (DATA_ROOT, ARTIFACTS_DIR, etc.)
│   ├── routers/
│   │   ├── scraper.py                  # POST /api/scraper/start, GET /api/scraper/progress
│   │   ├── calendar.py                 # GET /api/matches, GET /api/matches/{id}
│   │   ├── stats.py                    # GET /api/players, GET /api/teams
│   │   └── settings.py                 # GET /api/status, POST /api/pipeline/train, GET /api/pipeline/progress
│   ├── services/
│   │   ├── scraper_service.py          # Functions extracted from fotmob_final.ipynb
│   │   ├── merge_service.py            # FBref + FotMob join logic
│   │   ├── feature_service.py          # Composite score computation
│   │   └── ml_service.py              # Train + predict (regression + classification)
│   └── ml/
│       └── artifacts/                  # Persisted model files (git-ignored)
│           ├── ridge_att.pkl
│           ├── ridge_mid.pkl
│           ├── ridge_def.pkl
│           ├── ridge_gk.pkl
│           ├── rf_regressor.pkl
│           ├── rf_classifier.pkl
│           ├── scaler.pkl
│           └── metrics.json            # Last training evaluation metrics
│
├── frontend/                           # SvelteKit application
│   ├── package.json
│   ├── svelte.config.js
│   ├── vite.config.js
│   ├── src/
│   │   ├── app.html
│   │   ├── app.css                     # Global CSS variables (color palette)
│   │   ├── lib/
│   │   │   ├── components/
│   │   │   │   ├── MatchCard.svelte
│   │   │   │   ├── ProbabilityBar.svelte
│   │   │   │   ├── RadarChart.svelte
│   │   │   │   ├── ProgressStream.svelte
│   │   │   │   ├── StatusBadge.svelte
│   │   │   │   └── DataStatusGrid.svelte
│   │   │   └── stores/
│   │   │       ├── scraperStore.js
│   │   │       └── pipelineStore.js
│   │   └── routes/
│   │       ├── +layout.svelte          # Sidebar nav, global styles
│   │       ├── +page.svelte            # / → Match Calendar
│   │       ├── scraper/
│   │       │   └── +page.svelte
│   │       ├── stats/
│   │       │   └── +page.svelte
│   │       └── settings/
│   │           └── +page.svelte
│   └── static/
│       └── favicon.ico
│
├── data/                               # READ-ONLY by the app
│   ├── FBref/ ...
│   └── 87/ ...
│
├── notebooks/                          # ML pipeline notebooks
│   └── ...
│
├── fotmob_final.ipynb                  # Original scraper — untouched
└── GOALS_notebook.ipynb
```

---

## 4. Architecture

### Data Flow

```
┌─────────────────────────────────────────────────────────┐
│                     Browser (Svelte)                    │
│  /scraper   /  (calendar)   /stats   /settings          │
└────────────────────┬────────────────────────────────────┘
                     │ HTTP + SSE (localhost:8000)
┌────────────────────▼────────────────────────────────────┐
│                  FastAPI (goals_app)                     │
│                                                         │
│  routers/        services/           ml/artifacts/      │
│  ├ scraper  ──►  scraper_service ──► data/87/**         │
│  ├ calendar ──►  ml_service      ──► rf_classifier.pkl  │
│  ├ stats    ──►  feature_service ──► scaler.pkl         │
│  └ settings ──►  merge_service   ──► metrics.json       │
└─────────────────────────────────────────────────────────┘
                     │
           ┌─────────▼──────────┐
           │   data/ (disk)     │
           │  FBref CSV + GZ    │
           │  87/**/parquet     │
           └────────────────────┘
```

### Scraper Extraction Strategy

`scraper_service.py` contains all scraping logic copied from `fotmob_final.ipynb`, refactored into importable async functions. The original notebook is **not modified**.

Key functions extracted:
- `fetch_league_fixtures(league_id, season) -> list[dict]`
- `fetch_match_details(match_id) -> dict`
- `parse_outfield_players(raw_json) -> pd.DataFrame`
- `parse_goalkeepers(raw_json) -> pd.DataFrame`
- `save_season(league_id, season, output_dir)` — idempotent, skips already-cached match IDs

The scraper uses the same rate-limiting logic as the notebook: jitter + retries, `MAX_CONCURRENT=4`.

### ML Lifecycle

```
1. DATA COLLECTION   fotmob_final.ipynb  (or /scraper page)
        │
        ▼
2. MERGE             merge_service.py    FBref season stats + FotMob match stats
        │                               joined on (player_name fuzzy, date, team)
        ▼
3. FEATURE ENG.      feature_service.py  Z-score normalize → compute ATT/MID/DEF/GK scores
        │                               → aggregate to team level per match
        ▼
4. TRAIN             ml_service.py       Ridge + RF regressor (composite scores)
        │                               RF classifier (Win/Draw/Loss)
        ▼
5. PREDICT           ml_service.py       Load artifacts → predict 2024/25 matches
        │
        ▼
6. DISPLAY           calendar router    Serve predictions to Svelte frontend
```

### Data Caching

- Raw FotMob JSON is cached per match ID under `data/87/{season}/raw/` — scraper skips already-present files.
- Parquet outputs in `data/87/{season}/output/` are regenerated only when the scraper re-runs.
- Model artifacts in `goals_app/ml/artifacts/` are regenerated only when "Train Pipeline" is triggered.
- The frontend caches API responses in Svelte stores for the lifetime of the browser session; no service worker.

---

## 5. Feature Specifications

### 5.1 Scraper Page (`/scraper`)

**Purpose:** Trigger FotMob La Liga data collection for one or more seasons without touching the notebook.

**UI Elements:**

| Element | Behavior |
|---------|----------|
| League selector (read-only) | Always "La Liga (ID 87)" — v1 is La Liga only |
| Season checkboxes | `2021/2022`, `2022/2023`, `2023/2024`, `2024/2025` — multi-select |
| Data status badges | Per-season: `✅ Complete` / `⚠ Partial` / `❌ Missing` based on parquet presence |
| "Start Scrape" button | Disabled if no season selected; turns to "Stop" once started |
| Progress stream panel | SSE-driven log output — one line per match fetched, with match count + ETA |
| Summary card | After completion: matches fetched, players processed, time elapsed |

**SSE Progress Events:**

```
data: {"type": "progress", "season": "2021_2022", "done": 42, "total": 380, "message": "Fetched match 1234567"}
data: {"type": "complete", "season": "2021_2022", "matches": 380, "players": 8142}
data: {"type": "error", "message": "Rate limit hit — retrying in 5s"}
```

**Backend:** `POST /api/scraper/start` with `{"seasons": ["2021_2022", ...]}` → returns `job_id`.
`GET /api/scraper/progress/{job_id}` → SSE stream.

---

### 5.2 Match Calendar (`/`) — Default Route

**Purpose:** Browse La Liga 2024/25 matches with ML-predicted outcome probabilities.

**Layout:** Vertical scroll feed, grouped by matchday (Jornada). Each matchday header shows the date range.

**MatchCard Component:**

```
┌──────────────────────────────────────────────────────┐
│  Real Madrid  vs  FC Barcelona         Apr 26, 2025  │
│                                                      │
│  WIN   ████████████████████░░░░░░░░░   52%           │
│  DRAW  ████████░░░░░░░░░░░░░░░░░░░░░   22%           │
│  LOSS  ██████░░░░░░░░░░░░░░░░░░░░░░░   26%           │
│                                                      │
│  [View Details ›]                                    │
└──────────────────────────────────────────────────────┘
```

- WIN bar: `--color-win` (`#FF4B44`)
- DRAW bar: `--color-draw` (`#C9A84C`)
- LOSS bar: `--color-loss` (`#4488FF`)
- If match result is known (past match), a small result badge overlays: `FT 3-1`

**Detail Panel (slide-in drawer):**

Opens on "View Details" click. Contains:
- Team composite scores side-by-side (ATT / MID / DEF / GK per team, as a grouped bar chart)
- Top 5 players per team sorted by composite score
- Model confidence note (entropy of the probability distribution)

**Filters (top bar):**
- Matchday range slider
- Team filter (multi-select dropdown)
- Toggle: "Show only upcoming" / "Show all"

**Backend:** `GET /api/matches?season=2024_2025&from_jornada=1&to_jornada=38&team=`

---

### 5.3 Stats Section (`/stats`)

**Purpose:** Explore player and team-level composite scores derived from the feature engineering pipeline.

#### Players Tab (default)

- **Composite Score Grid:** Sortable table — columns: Player, Team, Position, ATT/MID/DEF/GK score (relevant column highlighted per position), Matches Played.
- **Search bar:** Fuzzy filter by player name.
- **Position filter:** All / ATT / MID / DEF / GK tabs.
- **Radar Chart:** Click any player row → radar chart appears showing their normalized metric breakdown (the 6–8 sub-metrics that compose their score, e.g., for ATT: Goals+Assists, xG, xA, Dribbles, Shots, ChancesCreated, Recoveries).

#### Teams Tab

- **Rolling Form Chart:** Line chart per team showing average composite score (summed XI) over the last N matchdays. N is adjustable (5 / 10 / All).
- **Team Comparison:** Select up to 3 teams to overlay their rolling form on the same chart.
- **Season selector:** 2021/22 – 2024/25 (only seasons with scraped FotMob data available).

**Backend:**
- `GET /api/players?season=2024_2025&position=ATT&search=Mbappe`
- `GET /api/players/{player_id}/radar?season=2024_2025`
- `GET /api/teams/form?season=2024_2025&window=10&teams=Real+Madrid,FC+Barcelona`

---

### 5.4 Settings (`/settings`)

**Purpose:** Inspect data collection status, trigger ML pipeline training, and view model evaluation metrics.

#### Data Status Grid

Table with one row per (source, league, season):

| Source | Season | Matches | Players | Status |
|--------|--------|---------|---------|--------|
| FotMob | 2021/22 | 380 | 8,142 | ✅ Complete |
| FotMob | 2022/23 | 380 | 7,901 | ✅ Complete |
| FotMob | 2023/24 | 380 | 8,034 | ✅ Complete |
| FotMob | 2024/25 | — | — | ❌ Missing |
| FBref | 2021/22 – 2024/25 | — | — | ✅ Complete |

Status is computed live from filesystem presence of parquet files.

#### Pipeline Train Button

- **"Train Pipeline"** button: disabled if any required data is missing.
- On click: `POST /api/pipeline/train` → starts background job → SSE stream at `GET /api/pipeline/progress/{job_id}`.
- Progress stream shows stage-by-stage status: Merge → Feature Engineering → Regression Training → Classification Training → Evaluation.
- On completion: metrics panel updates automatically.

**SSE Progress Events:**

```
data: {"type": "stage", "stage": "merge", "message": "Joining FBref + FotMob..."}
data: {"type": "stage", "stage": "features", "message": "Computing composite scores..."}
data: {"type": "stage", "stage": "regression", "message": "Training Ridge + RF regressors..."}
data: {"type": "stage", "stage": "classification", "message": "Training RF classifier..."}
data: {"type": "complete", "metrics": {...}}
```

#### Model Metrics Panel

Displayed after training, sourced from `goals_app/ml/artifacts/metrics.json`:

**Regression (per position):**

| Model | Position | RMSE | MAE | R² |
|-------|----------|------|-----|-----|
| Ridge | ATT | — | — | — |
| Ridge | MID | — | — | — |
| Ridge | DEF | — | — | — |
| Ridge | GK | — | — | — |
| Random Forest | ATT | — | — | — |
| … | … | … | … | … |

**Classification:**

| Model | Accuracy | Macro F1 |
|-------|----------|----------|
| Random Forest | — | — |

Confusion matrix displayed as a 3×3 heatmap (Win/Draw/Loss).

---

## 6. UI/UX Design

### Color Palette (La Liga Dark Theme)

```css
:root {
  /* Backgrounds */
  --bg-primary:    #0A0E1A;   /* page background */
  --bg-secondary:  #111827;   /* cards, panels */
  --bg-tertiary:   #1C2333;   /* inputs, hover states */

  /* Accent */
  --accent-primary:   #FF4B44;  /* La Liga red-orange — CTAs, highlights */
  --accent-secondary: #FF7A00;  /* gradient pair for accent elements */

  /* Text */
  --text-primary:   #F0F2F8;
  --text-secondary: #8B95A8;

  /* Outcome colors */
  --color-win:  #FF4B44;
  --color-draw: #C9A84C;
  --color-loss: #4488FF;

  /* State */
  --color-success: #34D399;
  --color-warning: #FBBF24;
  --color-error:   #F87171;
}
```

### Typography

- **Font family:** `Inter` (loaded from Google Fonts or local)
- **Heading 1:** 28px / 700 / `--text-primary`
- **Heading 2:** 20px / 600 / `--text-primary`
- **Body:** 14px / 400 / `--text-primary`
- **Caption / meta:** 12px / 400 / `--text-secondary`
- **Monospace (metrics, IDs):** `JetBrains Mono` or `Courier New`

### Layout System

- **Sidebar navigation:** Fixed left, 220px wide, collapses to icon-only at `<768px`.
  - Nav items: Calendar (home icon), Scraper (download icon), Stats (chart icon), Settings (gear icon).
- **Main content area:** Fluid, max-width 1200px, centered, padding `24px`.
- **Card component:** `background: var(--bg-secondary)`, `border-radius: 12px`, `padding: 20px`, subtle `box-shadow: 0 2px 8px rgba(0,0,0,0.4)`.
- **Grid:** 12-column CSS grid; cards span 4, 6, or 12 columns depending on context.

### Component List

| Component | Location | Description |
|-----------|----------|-------------|
| `MatchCard.svelte` | Calendar | Match row with probability bars |
| `ProbabilityBar.svelte` | MatchCard | Single outcome bar (label + fill + %) |
| `RadarChart.svelte` | Stats/Players | Chart.js radar for metric breakdown |
| `ProgressStream.svelte` | Scraper, Settings | SSE log viewer with auto-scroll |
| `StatusBadge.svelte` | Scraper, Settings | `✅ / ⚠ / ❌` pill badge |
| `DataStatusGrid.svelte` | Settings | Full data status table |
| `ConfusionMatrix.svelte` | Settings | 3×3 heatmap using CSS grid + color scale |
| `Sidebar.svelte` | Layout | Fixed nav with active-route highlighting |

### Interaction Principles

- **No page reloads** — all navigation is client-side SvelteKit routing.
- **Optimistic UI** — show skeleton loaders while API calls are in flight.
- **Streaming updates** — SSE panels auto-scroll to latest log line; no manual refresh.
- **Destructive actions** — "Train Pipeline" shows a confirmation modal (training overwrites existing artifacts).

---

## 7. Data & Storage

### Existing `data/` Directory (Read-Only)

The app reads these files but never writes to them except through the scraper service (which writes to `data/87/`).

**FotMob outputs consumed by the app:**

| File | Schema highlights |
|------|------------------|
| `data/87/{season}/output/outfield_players.parquet` | `match_id`, `player_id`, `player_name`, `team_name`, `position`, `goals`, `goal_assist`, `expected_goals`, `expected_assists`, `successful_dribbles`, `chances_created`, `recoveries`, `tackles_won`, `interceptions`, `aerial_duels_won`, `clearances`, `shot_blocks`, `accurate_passes` |
| `data/87/{season}/output/goalkeepers.parquet` | `match_id`, `player_id`, `player_name`, `team_name`, `saves`, `xgot_faced`, `diving_save`, `saves_inside_box`, `high_claim`, `acted_as_sweeper` |
| `data/87/{season}/output/fixtures.parquet` | `match_id`, `date`, `home_team`, `away_team`, `home_score`, `away_score`, `result` (`W`/`D`/`L` from home perspective), `jornada` |

**FBref outputs consumed by the app:**

| File | Schema highlights |
|------|------------------|
| `data/FBref/la_liga/{season}/standard.csv` | `player`, `team`, `position`, `age`, `games`, `goals`, `assists`, `xg`, `xa`, `progressive_passes`, … |

### Model Artifacts (`goals_app/ml/artifacts/`)

Written by `ml_service.py` during training; read during prediction. Git-ignored.

| File | Content |
|------|---------|
| `scaler.pkl` | `sklearn.preprocessing.StandardScaler` fit on train set metrics |
| `ridge_att.pkl` | Ridge regressor for ATT composite score |
| `ridge_mid.pkl` | Ridge regressor for MID composite score |
| `ridge_def.pkl` | Ridge regressor for DEF composite score |
| `ridge_gk.pkl` | Ridge regressor for GK composite score |
| `rf_regressor.pkl` | Random Forest regressor (ensemble, all positions) |
| `rf_classifier.pkl` | Random Forest classifier for Win/Draw/Loss |
| `metrics.json` | Evaluation results from last training run (RMSE, MAE, R², Accuracy, Macro F1, confusion matrix) |

**`metrics.json` schema:**

```json
{
  "trained_at": "2026-03-22T14:30:00",
  "train_seasons": ["2021_2022", "2022_2023", "2023_2024"],
  "test_season": "2024_2025",
  "regression": {
    "ridge": {
      "ATT": {"rmse": 0.0, "mae": 0.0, "r2": 0.0},
      "MID": {"rmse": 0.0, "mae": 0.0, "r2": 0.0},
      "DEF": {"rmse": 0.0, "mae": 0.0, "r2": 0.0},
      "GK":  {"rmse": 0.0, "mae": 0.0, "r2": 0.0}
    },
    "random_forest": {
      "ATT": {"rmse": 0.0, "mae": 0.0, "r2": 0.0}
    }
  },
  "classification": {
    "random_forest": {
      "accuracy": 0.0,
      "macro_f1": 0.0,
      "confusion_matrix": [[0,0,0],[0,0,0],[0,0,0]]
    }
  }
}
```

---

## 8. API Design

All endpoints are prefixed `/api/`. The Svelte frontend proxies these during dev via Vite's `proxy` config; in production FastAPI serves both API and static files.

### Scraper Endpoints

#### `POST /api/scraper/start`

Start a scraping job for one or more seasons.

**Request:**
```json
{
  "seasons": ["2021_2022", "2022_2023", "2023_2024", "2024_2025"]
}
```

**Response `202 Accepted`:**
```json
{
  "job_id": "scrape_abc123",
  "seasons": ["2021_2022", "2022_2023", "2023_2024", "2024_2025"],
  "status": "started"
}
```

---

#### `GET /api/scraper/progress/{job_id}`

SSE stream for scraper job progress.

**Response:** `text/event-stream`

```
data: {"type": "progress", "season": "2021_2022", "done": 42, "total": 380, "message": "Fetched match 1234567"}

data: {"type": "complete", "season": "2021_2022", "matches": 380, "players": 8142}

data: {"type": "error", "message": "Rate limit hit — retrying in 5s"}
```

---

#### `GET /api/scraper/status`

Returns filesystem-derived data availability per season.

**Response `200`:**
```json
{
  "seasons": [
    {
      "season": "2021_2022",
      "status": "complete",
      "matches": 380,
      "players": 8142,
      "last_updated": "2026-03-20T10:00:00"
    },
    {
      "season": "2024_2025",
      "status": "missing",
      "matches": null,
      "players": null,
      "last_updated": null
    }
  ]
}
```

---

### Calendar Endpoints

#### `GET /api/matches`

**Query params:** `season` (default `2024_2025`), `from_jornada` (int), `to_jornada` (int), `team` (string, optional)

**Response `200`:**
```json
{
  "matches": [
    {
      "match_id": "4193456",
      "date": "2025-04-26",
      "jornada": 34,
      "home_team": "Real Madrid",
      "away_team": "FC Barcelona",
      "home_score": null,
      "away_score": null,
      "result": null,
      "prediction": {
        "win_prob": 0.52,
        "draw_prob": 0.22,
        "loss_prob": 0.26,
        "predicted_outcome": "W"
      }
    }
  ]
}
```

---

#### `GET /api/matches/{match_id}`

Detailed match view including team composite scores and top players.

**Response `200`:**
```json
{
  "match_id": "4193456",
  "date": "2025-04-26",
  "jornada": 34,
  "home_team": "Real Madrid",
  "away_team": "FC Barcelona",
  "home_score": null,
  "away_score": null,
  "result": null,
  "prediction": {
    "win_prob": 0.52,
    "draw_prob": 0.22,
    "loss_prob": 0.26,
    "model_entropy": 1.51
  },
  "home_scores": {"ATT": 2.31, "MID": 1.87, "DEF": 1.94, "GK": 1.22},
  "away_scores": {"ATT": 2.18, "MID": 1.76, "DEF": 1.61, "GK": 0.98},
  "home_top_players": [
    {"name": "Kylian Mbappé", "position": "ATT", "composite_score": 0.84}
  ],
  "away_top_players": [
    {"name": "Robert Lewandowski", "position": "ATT", "composite_score": 0.79}
  ]
}
```

---

### Stats Endpoints

#### `GET /api/players`

**Query params:** `season` (default `2024_2025`), `position` (`ATT`/`MID`/`DEF`/`GK`/`all`), `search` (string, fuzzy), `sort_by` (default `composite_score`), `order` (`desc`/`asc`), `limit` (default `50`)

**Response `200`:**
```json
{
  "players": [
    {
      "player_id": "p_98123",
      "name": "Kylian Mbappé",
      "team": "Real Madrid",
      "position": "ATT",
      "composite_score": 2.84,
      "matches_played": 28
    }
  ],
  "total": 312
}
```

---

#### `GET /api/players/{player_id}/radar`

**Query params:** `season`

**Response `200`:**
```json
{
  "player_id": "p_98123",
  "name": "Kylian Mbappé",
  "position": "ATT",
  "metrics": {
    "goals_assists": 0.92,
    "xg": 0.88,
    "xa": 0.71,
    "dribbles": 0.84,
    "shots": 0.79,
    "chances_created": 0.65,
    "recoveries": 0.41
  }
}
```

---

#### `GET /api/teams/form`

**Query params:** `season`, `window` (int, matchdays, default `10`), `teams` (comma-separated team names)

**Response `200`:**
```json
{
  "teams": [
    {
      "team": "Real Madrid",
      "form": [
        {"jornada": 25, "composite_score": 9.14},
        {"jornada": 26, "composite_score": 8.87}
      ]
    }
  ]
}
```

---

### Settings Endpoints

#### `GET /api/status`

Returns combined data status (same as `/api/scraper/status` but includes FBref).

**Response `200`:**
```json
{
  "fotmob": [...],
  "fbref": [
    {"season": "2021-2022", "status": "complete"},
    {"season": "2024-2025", "status": "complete"}
  ],
  "artifacts": {
    "trained": true,
    "trained_at": "2026-03-22T14:30:00",
    "models": ["ridge_att", "ridge_mid", "ridge_def", "ridge_gk", "rf_regressor", "rf_classifier"]
  }
}
```

---

#### `POST /api/pipeline/train`

Trigger full ML pipeline training. Merges data, engineers features, trains and evaluates all models.

**Request:** `{}` (no body required)

**Response `202 Accepted`:**
```json
{
  "job_id": "train_xyz789",
  "status": "started"
}
```

---

#### `GET /api/pipeline/progress/{job_id}`

SSE stream for training pipeline progress.

**Response:** `text/event-stream`

```
data: {"type": "stage", "stage": "merge", "message": "Joining FBref + FotMob on 3 seasons..."}

data: {"type": "stage", "stage": "features", "message": "Computing ATT/MID/DEF/GK scores..."}

data: {"type": "stage", "stage": "regression", "message": "Training Ridge regressors (CV)..."}

data: {"type": "stage", "stage": "classification", "message": "Training RF classifier (class_weight=balanced)..."}

data: {"type": "complete", "metrics": {"classification": {"accuracy": 0.54, "macro_f1": 0.49}}}
```

---

#### `GET /api/pipeline/metrics`

Returns the contents of `goals_app/ml/artifacts/metrics.json` if it exists.

**Response `200`:** See `metrics.json` schema in Section 7.
**Response `404`:** `{"detail": "No trained model found. Run pipeline training first."}`

---

## 9. Implementation Sequence

The implementation is divided into 4 phases, aligned with the project timeline.

### Phase 1 — Scaffold + Scraper UI (Target: ~March 25, 2026)

**Goal:** Working app with scraper page functional end-to-end.

1. Create `goals_app/` package structure: `main.py`, `config.py`, `routers/`, `services/`, `ml/artifacts/`.
2. Create `frontend/` SvelteKit project: `npm create svelte@latest`.
3. Configure Vite proxy (`/api` → `localhost:8000`) for dev.
4. Mount compiled Svelte `dist/` as static files in FastAPI (`main.py`).
5. Write `scraper_service.py` by extracting and refactoring functions from `fotmob_final.ipynb`.
6. Implement `routers/scraper.py`: `POST /api/scraper/start`, `GET /api/scraper/progress/{job_id}`, `GET /api/scraper/status`.
7. Build `Scraper.svelte` page with season checkboxes, status badges, and `ProgressStream.svelte` consuming SSE.
8. Write `start.bat`.
9. **Verify:** Run scraper for La Liga 2024/25 via the UI; confirm parquet files written to `data/87/2024_2025/output/`.

### Phase 2 — ML Pipeline Backend (Target: ~April 4, 2026)

**Goal:** Full training pipeline callable from Settings; predictions available in API.

1. Write `merge_service.py`: join FBref CSV + FotMob parquet on (fuzzy player name, date, team) using `rapidfuzz` threshold ≥ 85.
2. Write `feature_service.py`: z-score normalization (fit on train seasons only), compute ATT/MID/DEF/GK composite scores using formulas from `CLAUDE.md`, aggregate to team level.
3. Write `ml_service.py`:
   - Train Ridge + RF regressors with walk-forward CV; save `ridge_*.pkl`, `rf_regressor.pkl`, `scaler.pkl`.
   - Train RF classifier (`class_weight='balanced'`); save `rf_classifier.pkl`.
   - Compute and write `metrics.json`.
4. Implement `routers/settings.py`: `GET /api/status`, `POST /api/pipeline/train`, `GET /api/pipeline/progress/{job_id}`, `GET /api/pipeline/metrics`.
5. Build `Settings.svelte` page: `DataStatusGrid.svelte`, train button, `ProgressStream.svelte`, metrics tables, `ConfusionMatrix.svelte`.
6. **Verify:** Train pipeline via UI; confirm artifacts written; inspect metrics in Settings panel.

### Phase 3 — Calendar + Stats UI (Target: ~April 10, 2026)

**Goal:** Full prediction calendar and player/team stats browsable in the frontend.

1. Implement `routers/calendar.py`: `GET /api/matches`, `GET /api/matches/{match_id}` (loads fixtures parquet + runs classifier on 2024/25 matches).
2. Implement `routers/stats.py`: `GET /api/players`, `GET /api/players/{player_id}/radar`, `GET /api/teams/form`.
3. Build `+page.svelte` (Calendar): matchday grouping, `MatchCard.svelte`, `ProbabilityBar.svelte`, detail drawer.
4. Build `Stats.svelte`: Players tab with composite score table + `RadarChart.svelte`; Teams tab with rolling form line chart.
5. Add `Sidebar.svelte` layout with active-route highlighting.
6. Apply full color palette from Section 6 (`app.css` variables).
7. **Verify:** Browse 2024/25 matchdays; open a match detail; view player radar; compare team form.

### Phase 4 — Polish + Integration Testing (Target: ~April 14, 2026)

**Goal:** App is stable, visually complete, and all pipeline stages are verified end-to-end.

1. Add skeleton loaders for all API-dependent components.
2. Add error boundaries (500/404 API responses shown as inline error cards, not blank screens).
3. Confirm `start.bat` works from a clean environment (venv activated, `npm run build` runs, browser opens).
4. End-to-end test: scrape → train → browse calendar → verify predictions are non-trivial.
5. Add `goals_app/ml/artifacts/` to `.gitignore`.
6. Review `metrics.json` for sanity: classification accuracy should beat a naive "always home win" baseline (~45%).

---

*End of GOALS_PRD.md*
