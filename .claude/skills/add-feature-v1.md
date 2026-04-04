---
name: add-feature
description: Implement a full-stack GOALS feature — FastAPI endpoint + service function + optional Svelte frontend component — following existing project conventions.
---

You are implementing a new feature for the GOALS web app (FastAPI + SvelteKit, La Liga match prediction).

The user's feature request is: $ARGUMENTS

## Workflow

Follow these steps in order. Do not skip steps.

### Step 1 — Read existing patterns

Before writing any code, read the following files to understand current conventions:
- `goals_app/routers/calendar.py` — response envelope pattern, query params, router setup
- `goals_app/routers/stats.py` — another router example
- `goals_app/services/feature_service.py` — available helpers: `load_season()`, `compute_outfield_composite()`, `compute_gk_composite()`, `get_player_raw_stats()`, `get_player_metric_contributions()`
- `goals_app/config.py` — path constants (FOTMOB_DIR, ARTIFACTS_DIR, TRAIN_SEASONS, TEST_SEASON)
- `goals_app/main.py` — how routers are registered

### Step 2 — Design (state your plan before coding)

Write a 3–5 line plan covering:
- Endpoint path and HTTP method
- Request parameters (query/path)
- Response shape (mirror the envelope from existing endpoints)
- Which service function(s) to call or create
- Whether a new router file is needed or if an existing one should be extended

### Step 3 — Implement backend

- Add the route to the correct router file
- If a new router is needed, register it in `goals_app/main.py`
- Implement the service function in the relevant service file, reusing existing helpers
- Use path constants from `config.py` — never hardcode paths

### Step 4 — Implement frontend (only if the feature has a UI component)

- Add a Svelte component in `frontend/src/lib/components/` or extend an existing route page
- Follow the color palette defined in `frontend/src/app.css` (CSS variables only — no hardcoded hex)
- Keep components reactive; use existing store patterns from `frontend/src/lib/stores/`

### Step 5 — Verify

- Check `tests/` for related test files; suggest or add a test for the new endpoint
- State the exact command to manually verify: `uvicorn goals_app.main:app --reload` then the curl command

## Hard Constraints

- **Never** shuffle train/test split — always temporal (walk-forward)
- **`data/` is read-only** — only `scraper_service.py` may write under `data/47/`
- **Scaler fit on train only** — never refit on test data
- **Player name fuzzy match** — `rapidfuzz` threshold ≥ 85
- **Do not touch** `fotmob_final.ipynb`
- **Do not hardcode seasons** — use `TRAIN_SEASONS` and `TEST_SEASON` from `config.py`
