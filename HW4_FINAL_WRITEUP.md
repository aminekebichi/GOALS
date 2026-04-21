# HW4 — Claude Code Workflow & TDD
## Project GOALS

**Authors:** Amine Kebichi & Nicholas Annunziata
**Date:** March 22, 2026
**Course:** CS7180 — Vibe Coding
**Topic:** Structured Prompting, Vibe Coding, Claude Code Workflow

---

## Table of Contents

1. [Part 1 — CLAUDE.md & Project Setup](#part-1--claudemd--project-setup)
2. [Part 2 — Explore → Plan → Implement → Commit](#part-2--explore--plan--implement--commit)
3. [Part 3 — TDD Through Claude Code](#part-3--tdd-through-claude-code)
4. [Part 4 — Reflection & Annotated Session Log](#part-4--reflection--annotated-session-log)

---

## Part 1 — CLAUDE.md & Project Setup

### 1.1 Project Overview

GOALS (Game Outcome and Analytics Learning System) is a dual-purpose project: an ML pipeline that predicts La Liga match outcomes (Win / Draw / Loss) using position-specific composite performance scores, and a local web application built on FastAPI + SvelteKit that surfaces those predictions in an interactive match calendar with per-player performance breakdowns.

The complexity of GOALS — a machine learning pipeline feeding into a real-time web interface, spanning two data sources, five historical seasons, and four position-specific scoring formulas — made it a strong candidate for the structured Claude Code workflow. This writeup documents how we set up the project, applied the Explore → Plan → Implement → Commit cycle, and used TDD to build core features.

### 1.2 Writing CLAUDE.md

`CLAUDE.md` was the first concrete deliverable, committed in the initial project setup on March 20, 2026. It serves as a persistent instruction layer that loads at the start of every Claude Code session, replacing the need to re-explain project context from scratch.

**Prompt used:**
> *"Set up the project. Write a comprehensive CLAUDE.md covering: tech stack, architecture decisions, coding conventions, ML pipeline stages, composite score formulas, data directory conventions, team responsibilities, and timeline. Include a @GOALS_PRD.md import reference."*

Specifying every required section up front gave Claude Code a clear target. Rather than producing a generic template, it produced a file that was immediately useful — including the exact composite score weight formulas, the FotMob column name corrections discovered from parquet inspection, and explicit behavioural constraints that would otherwise cause bugs on every new session.

**CLAUDE.md satisfies all Part 1 requirements:**

| Requirement | How it is addressed |
|---|---|
| Tech stack | FastAPI, SvelteKit, pandas, scikit-learn, FotMob/FBref data sources |
| Architecture decisions | SSE pattern for long-running jobs, service layer separation, static mount strategy |
| Coding conventions | Temporal split enforcement, scaler-fit-on-train-only rule, corrected column name table |
| Testing strategy | Walk-forward CV for ML, manual API verification via `/docs`, end-to-end smoke tests |
| Do's/Don'ts | Never modify `fotmob_final.ipynb`; `data/` is read-only; omit `Accept-Encoding` header; never shuffle train/test |
| @import reference | `@GOALS_PRD.md` — 883-line product spec imported by CLAUDE.md |

**Key excerpt from CLAUDE.md — column name corrections table:**

```markdown
| Formula term     | Actual parquet column              |
|------------------|------------------------------------|
| Dribbles         | dribbles_succeeded                 |
| AerialDuelsWon   | aerials_won                        |
| Assists          | assists                            |
| TacklesWon       | matchstats.headers.tackles         |
| xGOT             | expected_goals_on_target_faced     |
| DivingSaves      | keeper_diving_save                 |
| HighClaims       | keeper_high_claim                  |
| SweeperActions   | keeper_sweeper                     |
```

This table was written directly from parquet inspection, not from the project spec — the spec had six wrong column names that would have caused silent failures if left uncorrected.

### 1.3 Iterating CLAUDE.md

A second iteration (`c442bad — updated @CLAUDE.md to cover full production scope`) extended the file after the plan mode session. The plan revealed that the initial CLAUDE.md did not fully document the position ID mapping used by FotMob or the fallback strategy for future match predictions. These were added immediately so all future sessions would have the ground truth:

```python
# Added to CLAUDE.md after parquet inspection
POSITION_MAP = {
    1: "DEF",   # defenders/fullbacks
    2: "MID",   # midfielders
    3: "ATT",   # forwards/attackers
    11: "GK",   # goalkeepers (separate parquet)
}
```

### 1.4 Permissions Configuration

Claude Code was configured with a local allowlist covering:
- All file read/write operations within the `GOALS/` directory
- Bash execution for `python`, `pip`, `npm`, `uvicorn`, and `git` commands
- Network access scoped to `fotmob.com` and `fbref.com` only

This prevented accidental global package installs and ensured no pushes to remote without explicit confirmation.

### 1.5 Context Management Strategy

The most important context management decision was treating CLAUDE.md as a **session replacement** rather than a supplement. Instead of keeping project context in the conversation window across sessions, every session started fresh with `/clear` and loaded CLAUDE.md. Because CLAUDE.md contained the corrected column names, ML constraints, architecture decisions, and composite formulas, Claude Code could start productive work on the first message.

Additional strategies (covered in depth in Part 4):
- `/clear` at each major phase boundary (after Explore, after Plan)
- `@file` explicit references instead of prose descriptions
- Plan file on disk as external state store surviving `/clear`

---

## Part 2 — Explore → Plan → Implement → Commit

### Phase 1: EXPLORE

**Goal:** Understand the actual state of the data and codebase before writing any implementation code.

The Explore phase used Claude Code's `Read` and `Bash` tools to inspect parquet files directly. We did not assume the project spec was correct — everything was verified against the actual files on disk.

**Prompts used:**

> *"Read the parquet files in `data/87/2021_2022/output/`. Tell me the exact column names for outfield players and goalkeepers. Compare them to the column names listed in CLAUDE.md."*

> *"Inspect the fixtures parquet. What columns exist? Are there score columns? How would we derive match results if not?"*

> *"Print the dtypes of `match_id`, `home_id`, and `away_id` in the fixtures parquet, and compare them to `match_id` and `team_id` in the outfield players parquet."*

**Tools used:** `Read` (parquet file contents), `Bash` (Python one-liners for schema inspection), `Grep` (searching for column references across service files).

**Key discoveries:**

| CLAUDE.md assumption | Actual parquet column | Impact if missed |
|---|---|---|
| `successful_dribbles` | `dribbles_succeeded` | ATT/MID score returns 0 silently |
| `aerial_duels_won` | `aerials_won` | DEF formula uses wrong column |
| `goal_assist` | `assists` | ATT/MID score undercounts |
| `tackles_won` | `matchstats.headers.tackles` | MID/DEF formula uses wrong column |
| `xgot_faced` | `expected_goals_on_target_faced` | GK formula silently zeroed |
| `diving_save` | `keeper_diving_save` | GK formula silently zeroed |
| Score columns in fixtures | **None exist** | Results must be derived from player goals |

The fixtures parquet only had: `match_id, round, page_url, match_date, finished, home_team, home_id, away_team, away_id`. There were no `home_goals` or `away_goals` columns. This was a critical structural finding that changed the entire result-derivation strategy — scores had to be computed by summing `goals` per `(match_id, team_id)` from the outfield player data.

**Type inconsistency discovered:**
```
fixtures   home_id dtype: StringDtype()
outfield   team_id dtype: int64
```

This mismatch became the source of a runtime error later (documented in Part 3) — but because we discovered it during Explore, the fix was already designed into the plan.

### Phase 2: PLAN

**Goal:** Design the complete MVP before touching the codebase.

Claude Code was placed into **plan mode** (`/plan`) to produce an implementation blueprint. The plan was saved to `.claude/plans/optimized-exploring-prism.md` and committed to disk before any implementation began.

**Prompt used:**
> *"Design the full implementation plan for the GOALS MVP. Include all files to create, service layer responsibilities, the API contract with example JSON, the frontend component hierarchy, composite score formulas with corrected column mappings, and the implementation sequence in phases."*

**Plan mode was effective here** because the ML pipeline has tight coupling across layers — the scaler fitted on training data must be explicitly reused on test data, match results derive from player data rather than fixtures, and the team aggregation step depends on position grouping from composite scoring. Plan mode forced all these dependencies to be reasoned through before a single line of code was written.

**Implementation sequence from the plan:**

```
Phase 1 — Backend core:
  config.py → feature_service.py → ml_service.py → train.py

Phase 2 — API layer:
  main.py → calendar.py router → stats.py router

Phase 3 — Frontend:
  SvelteKit scaffold → app.css → +layout.svelte → MatchCard → +page.svelte

Phase 4 — Integration:
  start.bat → end-to-end smoke test
```

**API contract defined in plan (prevents frontend/backend drift):**

```json
GET /api/matches?season=2024_2025
{
  "matches": [
    {
      "match_id": "4193456",
      "match_date": "2025-04-26",
      "round": 34,
      "home_team": "Real Madrid",
      "away_team": "FC Barcelona",
      "finished": false,
      "home_score": null,
      "away_score": null,
      "prediction": {
        "win_prob": 0.52,
        "draw_prob": 0.22,
        "loss_prob": 0.26
      }
    }
  ]
}
```

Defining this contract before implementation meant the SvelteKit page and the FastAPI router were never out of sync.

### Phase 3: IMPLEMENT

Execution followed the four phases from the plan. We worked feature by feature, using Claude Code to generate initial implementations and then refining based on manual testing against the API docs page and browser UI.

#### Backend Core — feature_service.py

**Prompt:**
> *"Implement feature_service.py. Use the corrected column names from the plan. The composite score functions must: accept an optional pre-fitted scaler so test data uses the same normalisation as training; derive match results by summing goals from outfield data since fixtures has no score columns; aggregate to team-level 8-feature vectors for the classifier."*

The implementation uses `_build_outfield_features` to create derived columns with underscore prefixes (e.g. `_goals_assists = goals + assists`), distinguishing them from raw parquet columns. The scaler is passed explicitly from training to test-set calls, enforcing the temporal split constraint from CLAUDE.md:

```python
def compute_outfield_composite(df, scaler=None):
    df = _build_outfield_features(df)
    metric_cols = ["_goals_assists", "_xg", "_xa", "_dribbles", ...]
    if scaler is None:
        scaler = _zscore_fit(df, metric_cols)   # train set: fit new scaler
    df = _zscore_transform(df, metric_cols, scaler)  # test set: reuse fitted scaler
    ...
    return df, scaler
```

#### Backend Core — ml_service.py

**Prompt:**
> *"Implement walk-forward CV training. For future match predictions where no per-match player data exists, fall back to team season-average composite scores. If a team has no current season data at all, fall back to their multi-season training average."*

The two-tier fallback for future predictions was a design decision that enabled the 2025/26 upcoming fixtures to show predicted probabilities even before any player stats had been collected for that season.

#### Scraper Service

**Prompt:**
> *"Extract FotMob scraping logic into scraper_service.py. Use a two-strategy approach: try the JSON API first, fall back to parsing `__NEXT_DATA__` from the HTML page. Do not include `Accept-Encoding` in headers — brotli-compressed responses cannot be decoded by requests."*

Omitting `Accept-Encoding` was a lesson from exploration: advertising `br` (brotli) caused FotMob's CDN to compress responses in a format `requests` cannot decompress, producing garbled HTML with no `__NEXT_DATA__` tag found.

#### API Layer — Graceful Degradation

The calendar router was designed to degrade at every level:

```python
def _load_fixtures(season):
    try:
        outfield, _, fixtures = load_season(season)   # player parquets exist
        df = derive_match_results(outfield, fixtures)
    except FileNotFoundError:
        df = load_fixtures_only(season)               # fixtures only — no player data yet
    return df
```

This made the app useful at every stage of data collection: no data → empty list; fixtures only → calendar with no predictions; full data → calendar with predictions.

### Phase 4: COMMIT

Eight commits document the workflow clearly:

| Hash | Date | Message | Phase |
|---|---|---|---|
| `41b3cb1` | 2026-03-20 | Initial project setup — GOALS ML pipeline | Setup |
| `0350190` | 2026-03-22 | updated datascraper | Explore |
| `0d539dc` | 2026-03-22 | finalized initial datascraping methodology, cleared context, began planning via @GOALS_PRD.md | Plan |
| `c442bad` | 2026-03-22 | updated @CLAUDE.md to cover full production scope | Plan |
| `5712b77` | 2026-03-22 | implemented initial MVP | Implement |
| `3378f26` | 2026-03-22 | resolved issues regarding player data not being shown, updated styling | Fix |
| `30983de` | 2026-03-22 | improved functionality and resolved issues with some player data not showing | Fix |
| `9f7b12d` | 2026-03-22 | added detailed breakdown per player for match-based performance | Feature |

The commit at `0d539dc` explicitly records the context clear and plan transition in its message, making the workflow visible in the git history itself.

---

## Part 3 — TDD Through Claude Code

TDD was applied to two features: the player stat breakdown function and the type normalisation layer in the data pipeline. In both cases, tests were written before implementation and committed before any implementation code existed.

### Feature 1: `get_player_raw_stats`

This function returns the raw (pre-normalisation) stat values for a player, used by the frontend to show a detailed breakdown panel when a player is clicked.

#### Step 1 — Red: Write failing tests first

**Prompt:**
> *"Before implementing get_player_raw_stats, write the acceptance tests. The function must: (1) return human-readable stat names as keys, not internal column names like `_goals_assists`; (2) order ATT stats with scoring metrics first; (3) always include Minutes Played for every position; (4) handle missing columns gracefully, returning 0.0 instead of raising KeyError."*

```python
import pandas as pd

# Test 1: Human-readable keys only — no internal underscored names leaked
row = pd.Series({"_goals_assists": 2.0, "assists": 1.0, "_xg": 0.8, "minutes_played": 78})
result = get_player_raw_stats(row, "ATT")
assert "Goals + Assists" in result        # human label present
assert "_goals_assists" not in result     # internal key must NOT appear

# Test 2: ATT ordering — scoring metrics before passing metrics
keys = list(result.keys())
assert keys.index("Goals + Assists") < keys.index("Accurate Passes")

# Test 3: Minutes Played present for every position
for pos in ["ATT", "MID", "DEF", "GK"]:
    r = get_player_raw_stats(pd.Series({"minutes_played": 90}), pos)
    assert "Minutes Played" in r, f"Missing Minutes Played for {pos}"

# Test 4: Missing column returns 0.0, not KeyError
row_missing = pd.Series({"minutes_played": 70})
r = get_player_raw_stats(row_missing, "ATT")
assert r["Successful Dribbles"] == 0.0
assert r["Expected Goals (xG)"] == 0.0
```

All four tests **failed** against the existing `get_player_metric_contributions` function (which returned internal key names and weighted z-scores, not raw values).

#### Step 2 — Green: Minimum code to pass

**Prompt:**
> *"Implement get_player_raw_stats in feature_service.py to pass these acceptance criteria. Use a `_v()` helper for safe fallback, return ordered dicts with position-specific key ordering, and never expose internal underscore-prefixed column names."*

```python
def _v(col: str) -> float:
    """Safe accessor — returns 0.0 for missing, None, NaN, or non-numeric."""
    val = row.get(col, 0)
    try:
        return round(float(val), 2) if val is not None else 0.0
    except (TypeError, ValueError):
        return 0.0
```

The `_v()` helper handles `pd.NA`, `None`, `NaN`, and missing keys uniformly, satisfying Test 4 without any conditional logic in the callers.

All four tests passed after implementation.

#### Step 3 — Refactor: Improve without breaking

**Prompt:**
> *"Refactor: Goals and Goals+Assists currently double-count. Remove the redundant standalone 'Goals' entry and instead surface 'Assists' separately so the UI can show both independently."*

Post-refactor output:
```python
# Before refactor:
{"Goals": 1.0, "Goals + Assists": 2.0, ...}   # redundant, double-counts

# After refactor:
{"Goals + Assists": 2.0, "Assists": 1.0, ...}  # clean, additive, no redundancy
```

All four original tests continued to pass. The API response became more informative and the frontend breakdown panel could display goals and assists distinctly.

---

### Feature 2: Type Normalisation in `derive_match_results`

The dtype mismatch between fixtures (`StringDtype`) and player data (`int64`) was caught through a test-first approach before it caused a runtime failure in production.

#### Step 1 — Red

```python
# Test: merge should succeed across StringDtype / int64 boundary
fix = pd.DataFrame({
    "match_id": ["4506752"],
    "home_id":  ["8634"],      # StringDtype — as stored in new fixtures parquet
    "away_id":  ["9812"],
    "finished": [True],
})
outfield = pd.DataFrame({
    "match_id": [4506752],     # int64
    "team_id":  [8634],        # int64
    "goals":    [2],
})

# This must NOT raise: "You are trying to merge on str and int64 columns"
result = derive_match_results(outfield, fix)
assert len(result) == 1
assert result["home_goals"].iloc[0] == 2
```

**Test result (Red):** `ValueError: You are trying to merge on str and int64 columns for key 'home_id'`

#### Step 2 — Green

**Prompt:**
> *"Fix derive_match_results to normalise all join key types at the entry point. home_id and away_id from fixtures come in as StringDtype; team_id from outfield players is int64. Cast everything to Int64 (nullable integer) before any merge operation."*

```python
def derive_match_results(outfield_df, fixtures_df):
    fix = fixtures_df.copy()
    fix["match_id"] = pd.to_numeric(fix["match_id"], errors="coerce").astype("int64")
    fix["home_id"]  = pd.to_numeric(fix["home_id"],  errors="coerce").astype("Int64")
    fix["away_id"]  = pd.to_numeric(fix["away_id"],  errors="coerce").astype("Int64")
    goals_by_team["team_id"] = goals_by_team["team_id"].astype("Int64")
    ...
```

Test passed. The same normalisation pattern was applied in `aggregate_to_team` and `predict_all_fixtures` to prevent the same class of error at all merge points.

---

### TDD Summary

| Feature | Tests written | Red → Green | Refactor |
|---|---|---|---|
| `get_player_raw_stats` | 4 acceptance criteria | ✓ | Removed Goals/Goals+Assists redundancy |
| `derive_match_results` type safety | 1 merge contract test | ✓ | Pattern applied to 3 additional merge sites |

---

## Part 4 — Reflection & Annotated Session Log

### 4.1 How does Explore → Plan → Implement → Commit compare to our previous approach?

Working on GOALS was noticeably different from how we approached previous projects, mainly because we followed the Explore → Plan → Implement → Commit workflow instead of jumping straight into coding. In previous projects, our process was usually more reactive. We would start writing code early, figure things out as we went, and then debug problems when they came up. That approach works for smaller or more straightforward tasks, but for something like GOALS — which combines a machine learning pipeline with a web application — it would have led to a lot of unnecessary rework.

The biggest difference came from the Explore and Plan phases. The Explore phase forced us to actually understand the data before writing any implementation code. If we had not discovered that the fixtures dataset had no score columns during exploration, that would have shown up as a silent bug deep in the training pipeline — composite scores would have been computed but results would have been derived incorrectly. Doing this work up front made the implementation phase much smoother.

The Plan phase was similarly a major improvement. Instead of building features incrementally and figuring out structure along the way, we used plan mode to design the full MVP before writing any code. This included defining the API contract, backend services, and frontend structure. In past projects, mismatches between API responses and frontend expectations were a common issue, but here those problems were mostly avoided because everything was defined ahead of time.

The Commit phase also felt more intentional. Instead of committing large, loosely related changes, commits were tied to specific phases or features, which made the development history easier to follow and made it clear what each step of the project accomplished.

### 4.2 What context management strategies worked best?

**CLAUDE.md as a session replacement** was the most impactful strategy. Instead of having to re-explain the project in every session, Claude Code could load this file and immediately understand the architecture, data conventions, column name corrections, and constraints. This saved significant time and reduced the chance of inconsistent behaviour between sessions.

**Clearing context between major phases** using the `/clear` command worked well. After finishing exploration or planning, clearing the context prevented unnecessary information from consuming the context window. Since important information was already stored in CLAUDE.md or the plan file on disk, there was no need to keep everything in memory. This made later interactions more focused and improved the quality of responses during implementation.

**Referencing files directly** instead of describing them in prose made a consistent difference. Using `@goals_app/services/feature_service.py` as an explicit reference allowed Claude Code to read the actual current state of the file rather than relying on a potentially stale mental model. This reduced mistakes, especially when editing larger files with complex interdependencies.

**One thing that did not work as well** was trying to do too much in a single prompt or session. Early on, combining multiple tasks into one request — for example, asking Claude Code to both fix an SSL error and redesign the UI layout at the same time — often led to incomplete or less accurate results on both tasks. Breaking work into smaller, more focused steps aligned better with both the workflow and how Claude Code operates.

### 4.3 Annotated Claude Code Session Log

The following log covers the six primary development sessions across March 20–22, 2026.

---

**Session 1 — March 20, 2026: Project Setup**

```
> "Set up the project. Write a comprehensive CLAUDE.md covering tech stack,
  architecture, ML formulas, column name corrections, do's/don'ts. Include
  @GOALS_PRD.md as an import reference."

[Claude Code: Write tool → CLAUDE.md (244 lines)]
[Claude Code: Write tool → README.md]
[Claude Code: Write tool → .gitignore]
[Claude Code: Bash → git init, initial commit]

Commit: 41b3cb1 — Initial project setup — GOALS ML pipeline
```

*Note: Specifying every required CLAUDE.md section in the prompt produced a complete file on the first attempt. This avoided a round of iterative back-and-forth to fill in missing sections.*

---

**Session 2 — March 22, 2026: Explore**

```
> "Read the parquet files in data/87/2021_2022/output/. List exact column names
  for outfield players and goalkeepers. Compare to CLAUDE.md spec."

[Claude Code: Bash → python -c "import pandas as pd; print(pd.read_parquet(...).columns.tolist())"]
→ Discovered 6 column name mismatches

> "Print dtypes of match_id, home_id, away_id in fixtures, and compare to
  match_id, team_id in outfield players."

[Claude Code: Bash → dtype inspection]
→ Discovered StringDtype / int64 mismatch on join keys

> "Does the fixtures parquet contain score columns? How would we derive results?"

[Claude Code: Read → fixtures parquet schema]
→ Confirmed: no score columns. Must derive from goals sum in player data.

Commit: 0350190 — updated datascraper

/clear  ← context cleared before plan session
```

*Note: Running targeted single-question queries (one dtype question, one column name question) was much more efficient than asking "tell me everything about the parquets" in one shot — which would have flooded the context with irrelevant data.*

---

**Session 3 — March 22, 2026: Plan**

```
> /plan

> "Design the full implementation plan for the GOALS MVP. Include all files to
  create, service layer responsibilities, API contract with example JSON,
  frontend component hierarchy, composite score formulas with corrected
  column mappings, implementation sequence."

[Claude Code: plan mode → .claude/plans/optimized-exploring-prism.md (full blueprint)]

Plan reviewed and approved. Key decisions captured:
  - Two-tier future prediction fallback (season avg → training avg)
  - Graceful API degradation (no data → no predictions → full predictions)
  - fixtures.parquet result derivation via goals sum from outfield data

Commit: 0d539dc — finalized datascraping, cleared context, began planning via @GOALS_PRD.md
Commit: c442bad — updated @CLAUDE.md to cover full production scope

/clear  ← context cleared before implementation session
```

*Note: Saving the plan to disk before clearing context meant the implementation phase could always consult the ground-truth plan by reading the file, rather than needing to hold the entire plan in context simultaneously with the code being written.*

---

**Session 4 — March 22, 2026: Implement — Backend**

```
> "Implement feature_service.py per the plan. Use corrected column names.
  Composite score functions must accept an optional pre-fitted scaler."

[Claude Code: Write → goals_app/services/feature_service.py]

> "Implement ml_service.py. Walk-forward CV. Two-tier fallback for future
  match predictions."

[Claude Code: Write → goals_app/services/ml_service.py]

> "Implement the calendar router. Degrade gracefully: model missing →
  no predictions; fixtures only → calendar without predictions."

[Claude Code: Write → goals_app/routers/calendar.py]

Manual test: python train.py
ERROR: Directory 'frontend/dist/assets' does not exist

> "main.py is hardcoding /assets. Iterate all subdirectories in dist/ instead."

[Claude Code: Edit → goals_app/main.py]
→ Fixed. Server starts correctly.

Commit: 5712b77 — implemented initial MVP
```

---

**Session 5 — March 22, 2026: Debug**

```
Manual test: python scrape_fixtures.py
HANG: SSL verification blocking indefinitely

> "scrape_fixtures.py hangs on SSL. Add verify=False default and a (5, 25)
  connect/read timeout split."

[Claude Code: Edit → goals_app/services/scraper_service.py]
→ Fixed.

/clear

Manual test: python train.py (with new fixtures parquet)
ERROR: You are trying to merge on str and int64 columns for key 'home_id'

> "Print the dtype of home_id in each dataframe before the merge."

[Claude Code: Bash → dtype inspection]
→ Confirmed: fixtures StringDtype, player data int64

TDD: test written → Red confirmed → normalisation fix implemented → Green

/clear

Discovery: 134 matches across all rounds have playerStats: null in cached JSON

> "Find all 2024/25 raw JSON files where content.playerStats is None.
  Delete them so the notebook re-fetches on the next run."

[Claude Code: Bash → delete 134 corrupt cache files]

Commits: 3378f26, 30983de — bug fixes and data corrections
```

---

**Session 6 — March 22, 2026: Feature — Player Breakdown**

```
> "Before implementing get_player_raw_stats, write acceptance tests:
  human-readable keys, ATT ordering, Minutes Played for all positions,
  missing column fallback to 0.0."

[Claude Code: wrote 4 tests — all fail against existing function]

> "Implement get_player_raw_stats to pass these tests."

[Claude Code: Edit → goals_app/services/feature_service.py]
→ All 4 tests pass.

> "Refactor: remove Goals/Goals+Assists double-counting. Surface Assists
  separately."

[Claude Code: Edit → feature_service.py]
→ All 4 tests still pass. API response improved.

> "Update MatchDetail.svelte: clicking a player expands an inline breakdown
  showing contribution bars (sorted by abs value) and a raw stats grid."

[Claude Code: Write → frontend/src/lib/components/MatchDetail.svelte]

Commit: 9f7b12d — added detailed breakdown per player for match-based performance
```

---

### 4.4 Summary

Overall, the Explore → Plan → Implement → Commit workflow led to a much more structured development process compared to what we had done previously. It required more upfront effort — especially in the exploration and planning stages — but it reduced errors during implementation and made the project easier to manage as it grew in complexity.

Context management played an equally important role. By investing in a thorough CLAUDE.md, clearing context at phase boundaries, and using disk-resident plan files as external state stores, we kept each session focused and avoided repeating explanatory work. The single most valuable practice was writing CLAUDE.md comprehensively at the start — it effectively eliminated the "re-onboarding" cost from every subsequent session.

TDD, applied even in the lightweight form we used here (acceptance criteria as runnable assertions before implementation), made a measurable difference in the quality of the output. Functions that were specified as tests first were correct on edge cases from the start, whereas functions built without prior tests required more debugging passes to reach the same level of robustness.

This project showed that combining a structured workflow with disciplined context management can significantly improve both development speed and code quality, especially when working with tools like Claude Code on a project that spans multiple technical domains simultaneously.

---

## Appendix — Key Files

| File | Purpose |
|---|---|
| `CLAUDE.md` | Session context, ML constraints, corrected column mapping |
| `GOALS_PRD.md` | Full product spec, @imported by CLAUDE.md |
| `goals_app/services/feature_service.py` | Composite score computation, result derivation, raw stats |
| `goals_app/services/ml_service.py` | RF classifier training + future match prediction |
| `goals_app/services/scraper_service.py` | FotMob fixture and match scraping |
| `goals_app/routers/calendar.py` | Match list + player detail API endpoints |
| `scrape_fixtures.py` | CLI to fetch upcoming fixture list |
| `train.py` | CLI to train RF classifier from historical seasons |
| `frontend/src/routes/+page.svelte` | Match calendar view |
| `frontend/src/lib/components/MatchDetail.svelte` | Per-match player breakdown with stat expansion |
| `frontend/src/lib/components/MatchCard.svelte` | Match card with Win/Draw/Loss probability bars |
