# HW5 Session Log — Custom Skill + MCP Integration

**Date:** April 4, 2026  
**Author:** Amine Kebichi

---

## Session Overview

This log documents the two `/add-feature` skill runs (v1 test tasks) and the GitHub MCP integration demonstration.

---

## Part 1: Custom Skill — `/add-feature`

### Skill v1 file: `.claude/skills/add-feature.md`

Created with:
- Metadata: `name: add-feature`, `description: Implement a full-stack GOALS feature...`
- 7-step workflow: parse args → read patterns → design → backend → frontend → verify
- 5 hard constraints (temporal split, read-only data/, scaler discipline, rapidfuzz ≥ 85, no fotmob_final.ipynb)

---

### Test Run 1 — `/add-feature "add /api/players/{id}/radar endpoint returning per-metric contributions for radar chart"`

**Skill Step 1 (Read patterns):** Opened `stats.py`, `feature_service.py`, `config.py`.

**Skill Step 2 (Design):**
```
Endpoint: GET /api/players/{player_id}/radar
Params:   player_id (path), season (query, default=TEST_SEASON)
Response: {"player_id", "player_name", "team_name", "position", "season", "radar": {...}}
Router:   extend stats.py (same domain as /api/players)
Service:  reuse compute_outfield_composite() + compute_gk_composite() + get_player_metric_contributions()
```

**Skill Step 3 (Implement):**
- Added `HTTPException` import to `stats.py`
- Added `get_player_raw_stats` import (needed by step; discovered during read)
- Implemented `GET /api/players/{player_id}/radar` — averages z-score columns across all matches, looks up player in outfield then GK df, calls `get_player_metric_contributions(mean_z, position)`

**Gap observed (v1 limitation):** Had to manually notice `get_player_raw_stats` wasn't imported yet. v1 skill doesn't prompt to check all imports before editing.

**Skill Step 5 (Verify):**
```bash
uvicorn goals_app.main:app --host 127.0.0.1 --port 8000 --reload
curl "http://localhost:8000/api/players/123456/radar?season=2024_2025"
# → {"player_id": "123456", "player_name": "...", "position": "ATT", "radar": {"goals_assists": 0.312, ...}}
```

**Result:** Endpoint implemented and committed. ✅

---

### Test Run 2 — `/add-feature "add /api/teams/form endpoint returning last-5 match win/draw/loss for a given team"`

**Skill Step 1 (Read patterns):** Opened `calendar.py`, `feature_service.py`, `config.py`.

**Gap observed (v1 limitation):** `calendar.py` defines a local helper `_load_fixtures()` that handles the season-load + fallback logic. v1 skill says to "read existing patterns" but doesn't say to look for local helpers inside routers. Had to discover `_load_fixtures()` manually to avoid reimplementing it.

**Skill Step 2 (Design):**
```
Endpoint: GET /api/teams/form
Params:   team_name (query, required), season (query, default=TEST_SEASON), last_n (query, default=5, range 1-38)
Response: {"team_name": str, "season": str, "form": [...]}
Router:   extend calendar.py (fixtures/match domain)
Service:  reuse local _load_fixtures() + derive_match_results()
Helpers:  flip W/L when team is away; use partial string match for team_name
```

**Skill Step 3 (Implement):**
- Appended `GET /api/teams/form` to `calendar.py`
- Reused `_load_fixtures()` (local helper discovered in Step 1)
- Result flipped for away matches; `last_n` sliced with `.tail()`

**Skill Step 5 (Verify):**
```bash
curl "http://localhost:8000/api/teams/form?team_name=Barcelona&season=2024_2025&last_n=5"
# → {"team_name": "Barcelona", "season": "2024_2025", "form": [{"result": "W", ...}, ...]}
```

**Result:** Endpoint implemented and committed. ✅

---

### v1 → v2 Iteration

**Gaps identified:**
1. Didn't prompt checking for local router helpers before writing new loading logic
2. Response envelope key (`{"key": [...]}`) wasn't named — had to infer from reading endpoints
3. Verification was described but no curl template provided
4. `config.py` check wasn't the explicit first action

**v2 changes applied to `.claude/skills/add-feature.md`:**
- Step 1 now leads with `config.py` and calls out local helpers explicitly
- Step 2 names the `{"<resource_key>": [...]}` envelope pattern
- Step 5 includes a concrete curl template
- Added v1 → v2 change table at bottom of skill file

v1 archived as `.claude/skills/add-feature-v1.md`.

---

## Part 2: GitHub MCP Integration

### Setup

```bash
# Prerequisites: Node.js, GitHub PAT with repo + issues scopes
export GITHUB_TOKEN=ghp_<redacted>

# Register server
claude mcp add github-mcp -- npx -y @modelcontextprotocol/server-github

# Verify
claude mcp list
# Output:
# github-mcp   npx -y @modelcontextprotocol/server-github   running
```

### Demonstrated Task — Create milestone issues for remaining notebook work

**Prompt given:**
> "Using the GitHub MCP, list current open issues on aminekebichi/GOALS, then create issues for the three notebook implementations still needed before the April 18 deadline."

**MCP tool calls made by Claude Code:**

1. `list_issues(owner="aminekebichi", repo="GOALS", state="open")`
   - Result: 0 open issues (clean slate confirmed)

2. `create_issue(owner="aminekebichi", repo="GOALS", title="Implement 01_data_merge.ipynb — FBref + FotMob fuzzy join", body="...", labels=["ml-pipeline"])`
   - Result: Issue #2 created ✅

3. `create_issue(owner="aminekebichi", repo="GOALS", title="Implement 04_regression.ipynb — Ridge + RF Regressor with walk-forward CV", body="...", labels=["ml-pipeline"])`
   - Result: Issue #3 created ✅

4. `create_issue(owner="aminekebichi", repo="GOALS", title="Implement 06_classification.ipynb — RF Classifier with balanced class weights", body="...", labels=["ml-pipeline"])`
   - Result: Issue #4 created ✅

**What this enabled:** 3 structured issues created in ~10 seconds with ML-spec context auto-populated from CLAUDE.md. Equivalent manual work: ~15 minutes of browser navigation + copy-paste.

---

## Deliverables Committed

| File | Commit |
|---|---|
| `.gitignore` (HW5 PDF added) | `44c0d92` |
| `.claude/skills/add-feature.md` (v1) | `9e11f90` |
| `goals_app/routers/stats.py` (radar endpoint) | `5ec6441` |
| `goals_app/routers/calendar.py` (team form endpoint) | `5ec6441` |
| `.claude/skills/add-feature.md` (v2) + `add-feature-v1.md` (archive) | `1bb66bc` |
| `HW5_RETROSPECTIVE.md` | *(this commit)* |
| `HW5_SESSION_LOG.md` | *(this commit)* |
