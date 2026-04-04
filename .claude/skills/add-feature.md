---
name: add-feature
description: Implement a full-stack GOALS feature — FastAPI endpoint + service function + optional Svelte frontend component — following existing project conventions. v2 adds explicit envelope, local helper discovery, and concrete verification commands.
---

You are implementing a new feature for the GOALS web app (FastAPI + SvelteKit, La Liga match prediction).

The user's feature request is: $ARGUMENTS

## Workflow

Follow these steps in order. Do not skip steps.

### Step 1 — Read existing patterns

Before writing any code, read these files:
- `goals_app/config.py` — path constants (`FOTMOB_DIR`, `ARTIFACTS_DIR`, `TRAIN_SEASONS`, `TEST_SEASON`). **Use these constants; never hardcode paths or season strings.**
- `goals_app/routers/calendar.py` — response envelope (`{"matches": [...]}` / `{"players": [...]}`) and any local helper functions defined inside the router (e.g. `_load_fixtures()`). Check for helpers **before** calling service functions directly.
- `goals_app/routers/stats.py` — a second router example; note how it imports from `feature_service`
- `goals_app/services/feature_service.py` — available helpers: `load_season()`, `load_fixtures_only()`, `compute_outfield_composite()`, `compute_gk_composite()`, `get_player_metric_contributions()`, `get_player_raw_stats()`, `derive_match_results()`, `aggregate_to_team()`
- `goals_app/main.py` — how routers are registered (prefix `/api`, tag list)

### Step 2 — Design (state your plan before coding)

Write a concise plan covering:
- Endpoint path + HTTP method
- Query/path parameters and their defaults (use `TEST_SEASON` from `config.py` as the default `season` param)
- Response envelope: `{"<resource_key>": [...]}` — mirror the key name pattern used in existing endpoints
- Which router file to extend (prefer extending an existing one unless a full new domain is introduced)
- Which service function(s) to call or create; note any local router helpers to reuse

### Step 3 — Implement backend

- Extend the correct router file (or create a new one and register it in `main.py` with prefix `/api`)
- Import from `config.py` for constants — never hardcode
- Reuse local router helpers (e.g. `_load_fixtures`) before writing new loading logic
- Implement any new service logic in the relevant service file; return a `(result, scaler)` tuple if fitting a scaler

### Step 4 — Implement frontend (only if the feature has a visible UI component)

- Add a Svelte component in `frontend/src/lib/components/` or extend the relevant route page
- Use only CSS variables from `frontend/src/app.css` — no hardcoded hex colors
- Fetch from `/api/<path>` — the Vite dev proxy (`vite.config.js`) forwards this to `localhost:8000` automatically; no base-URL config needed
- Follow existing store patterns in `frontend/src/lib/stores/` for reactive state

### Step 5 — Verify

- Identify related test files in `tests/`; suggest or add a test for the new endpoint
- Provide the exact commands to manually verify:
  ```bash
  uvicorn goals_app.main:app --host 127.0.0.1 --port 8000 --reload
  # Then in another terminal:
  curl "http://localhost:8000/api/<your-path>?season=2024_2025"
  ```

## Hard Constraints

- **Never** shuffle train/test — always temporal (walk-forward) split
- **`data/` is read-only** — only `scraper_service.py` may write under `data/87/`
- **Scaler fit on train only** — never refit on test data; pass scaler as argument to `compute_*` functions
- **Player name fuzzy match** — `rapidfuzz` threshold ≥ 85
- **Do not modify** `fotmob_final.ipynb`
- **Use `TRAIN_SEASONS` and `TEST_SEASON`** from `config.py` — never hardcode season strings

## v1 → v2 Changes

| Issue observed in v1 | Fix in v2 |
|---|---|
| Missed local `_load_fixtures()` helper in `calendar.py`; reimplemented loading logic unnecessarily | Step 1 now explicitly says to look for local helpers inside routers before writing new code |
| Response envelope key was inconsistent (had to guess from reading existing endpoints) | Step 2 now names the `{"<resource_key>": [...]}` pattern explicitly |
| Verification was vague ("suggest the exact test command") | Step 5 now provides a concrete curl template with the right host/port |
| Didn't remind to use `config.py` constants first | Step 1 now leads with `config.py` and Step 3 repeats the constraint |
