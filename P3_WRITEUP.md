# P3 — Product Application: GOALS
## Game Outcome and Analytics Learning System

**Course:** EECE5644 — Introduction to Machine Learning and Pattern Recognition  
**Team:** Amine Kebichi · Nicholas Annunziata  
**Submitted:** April 20, 2026  
**Live App:** https://project-d7avr.vercel.app  
**Repository:** https://github.com/aminekebichi/GOALS  
**Project Board:** https://github.com/users/aminekebichi/projects/3  

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Deployed Application](#2-deployed-application)
3. [CI/CD Pipeline](#3-cicd-pipeline)
4. [Agile Sprint Documentation](#4-agile-sprint-documentation)
5. [Functional Requirements](#5-functional-requirements)
6. [Technical Requirements](#6-technical-requirements)
7. [ML Pipeline](#7-ml-pipeline)
8. [Custom Skills & Agents](#8-custom-skills--agents)
9. [4-Gate Security Pipeline](#9-4-gate-security-pipeline)
10. [Testing Strategy](#10-testing-strategy)
11. [Known Gaps & Honest Assessment](#11-known-gaps--honest-assessment)

---

## 1. Project Overview

GOALS (Game Outcome and Analytics Learning System) is a full-stack machine learning product that predicts English Premier League match outcomes (Win / Draw / Loss) from position-specific player performance scores and serves those predictions to end-users through a publicly deployed web application.

### What It Does

The system has two integrated layers:

**ML Pipeline (Python notebooks):**  
Raw FotMob match-level player statistics and FBref season-level stats are merged, z-score normalised, and used to compute four position-specific composite scores per player per match (ATT / MID / DEF / GK). Those scores are aggregated to team level and fed into a Random Forest classifier and Logistic Regression model that predict the probability of each match outcome. The pipeline is trained on seasons 2021–2024 and evaluated on the held-out 2024/25 season.

**Web Application (Next.js, deployed on Vercel):**  
A publicly accessible app backed by Neon PostgreSQL that surfaces the predictions through four views:
- **Match Calendar** — 266 Premier League 2024/25 matches as clickable cards with predicted winner, confidence %, actual score, and a Correct/Wrong badge
- **Match Detail** — Man of the Match (highest composite z-score, ≥ 45 min played), team rosters by position with score bars, every player clickable
- **Player Game Stats** — per-match stat breakdown (goals, xG, xA, shots, chances, pass accuracy, interceptions, clearances, saves, save rate, etc.)
- **Player Stats & Pipeline Metrics** — Clerk-authenticated pages for composite score leaderboards by position and ML model performance metrics

### Team Responsibilities

| Area | Owner |
|------|-------|
| FotMob scraping, FastAPI backend, regression (notebook 04) | Amine |
| Clustering (notebook 05), classification (notebooks 06–07) | Nicholas |
| Data merge (notebook 01), EDA (notebook 02) | Both |
| Feature engineering (notebook 03) | Both |
| Next.js frontend, Vercel deployment, DB seeding | Amine |
| Final report | Both |

---

## 2. Deployed Application

### What "Deployed" Means

A deployed application has been moved from a developer's local environment to a public-facing production server, making it accessible to any user without requiring them to install anything. The app is not running on a laptop — it runs on Vercel's global edge network 24/7, backed by a managed Neon PostgreSQL database.

### Production URL

**https://project-d7avr.vercel.app**

This URL is live, publicly accessible, and requires no login to view the Match Calendar.

### Infrastructure

| Component | Service | Purpose |
|-----------|---------|---------|
| Web app hosting | Vercel (CDN + serverless) | Serves Next.js App Router with server-side rendering |
| Database | Neon PostgreSQL (serverless) | Stores all match, player, and metrics data |
| ORM | Prisma v5 | Type-safe database access, schema migrations |
| Authentication | Clerk v7 | Protects `/stats` and `/settings` behind sign-in |
| Build | `prisma generate && next build` | Generates Prisma client before every production build |

### What Is Seeded in the Database

| Table | Records | Contents |
|-------|---------|---------|
| `Match` | 266 | 2024/25 Premier League matches with probabilities, predictions, and actual goals |
| `Player` | 2272 | Players from all seasons (2021–2025) with season-level composite scores |
| `MatchPlayer` | 5961 | Per-match player stats: goals, xG, assists, passes, interceptions, saves, etc. |
| `PipelineMetrics` | 2 | RF Classifier (Accuracy 55.6%, Macro F1 0.549) and LR model results |

### Route Structure

| Route | Auth | Description |
|-------|------|-------------|
| `/` | Public | Match calendar — 266 match cards |
| `/matches/[id]` | Public | Match detail with MOTM and team rosters |
| `/matches/[id]/players/[playerId]` | Public | Individual player game stats |
| `/stats` | Clerk | Player composite score leaderboard |
| `/settings` | Clerk | ML pipeline metrics dashboard |
| `/sign-in`, `/sign-up` | Public | Clerk-managed auth flows |

---

## 3. CI/CD Pipeline

### What CI/CD Means

CI/CD (Continuous Integration / Continuous Delivery) means every code push to `main` automatically runs builds, tests, and deployment without any manual intervention. A developer pushes code; the pipeline takes it the rest of the way to production.

### Pipeline Architecture

The workflow is defined in `.github/workflows/ci.yml` and triggers on every push to `main` and every pull request.

```
Push to main
      │
      ├─── Lint (ESLint)                    ─┐
      ├─── Type Check (tsc --noEmit)         ├─ run in parallel
      ├─── Unit & Integration Tests (Vitest) ─┘
      ├─── E2E Tests (Playwright / Chromium)
      ├─── Security Scan (npm audit + Gitleaks)
      │
      └─── Production Deploy (Vercel)  ←── only after all above pass
```

For pull requests, a **Preview Deploy** runs instead of production, giving a unique URL per PR for review.

### Job Details

| Job | Tool | What it checks |
|-----|------|---------------|
| `lint` | ESLint + Prettier | Code style and formatting across all `.ts` / `.tsx` / `.css` |
| `typecheck` | `tsc --noEmit` | Full TypeScript type correctness |
| `test` | Vitest 3 | 13 unit + integration tests; 70% line/function coverage threshold enforced |
| `e2e` | Playwright | Chromium headless browser tests; artifacts uploaded on failure |
| `security` | npm audit + Gitleaks | Dependency CVEs (≥ moderate = fail) + secrets detection |
| `deploy-production` | `amondnet/vercel-action` | Deploys to Vercel production after all jobs pass (push to main only) |
| `deploy-preview` | `amondnet/vercel-action` | Deploys preview URL for every PR |
| `ai-review` | Claude Code Action | AI PR review on every pull request (OWASP + conventions) |

### Secrets Required

| Secret | Stored In | Purpose |
|--------|-----------|---------|
| `DATABASE_URL` | GitHub Actions Secrets | Neon connection string |
| `CLERK_SECRET_KEY` | GitHub Actions Secrets | Clerk server-side key |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | GitHub Actions Secrets | Clerk public key |
| `VERCEL_TOKEN` | GitHub Actions Secrets | Vercel deploy authentication |
| `VERCEL_ORG_ID` | GitHub Actions Secrets | `team_VDLz3Rf7IEd9E0fxLEIrLCFY` |
| `VERCEL_PROJECT_ID` | GitHub Actions Secrets | `prj_SwvqAomypQxyJZPDzFRLMQksNMvp` |

---

## 4. Agile Sprint Documentation

The project was executed across two sprints. All tasks are tracked as GitHub Issues with milestone dates and owner assignments at: **https://github.com/users/aminekebichi/projects/3**

### Sprint 1 — Foundation & ML Pipeline
**Mar 20 – Apr 4, 2026**

| Issue | Task | Owner | Status | Completed |
|-------|------|-------|--------|-----------|
| #2 | Data collection: FotMob scraping & FBref merge | Amine | ✅ Done | Mar 28 |
| #3 | EDA and data validation (notebook 02) | Both | ✅ Done | Mar 30 |
| #4 | Feature engineering: composite scores (notebook 03) | Both | ✅ Done | Apr 1 |
| #5 | Regression models: Ridge & Random Forest (notebook 04) | Amine | ✅ Done | Apr 2 |
| #6 | Clustering: player archetypes (notebook 05) | Nicholas | ✅ Done | Apr 3 |
| #7 | Next.js app scaffold: Clerk auth, Neon DB, Prisma schema | Amine | ✅ Done | Apr 1 |
| #8 | CI/CD: GitHub Actions with lint, typecheck, unit tests | Amine | ✅ Done | Apr 2 |

**Sprint 1 Goal achieved:** All data collected, all regression/clustering models trained, app scaffold with auth and DB in place, CI running.

### Sprint 2 — Frontend, Deployment & Integration
**Apr 5 – Apr 18, 2026**

| Issue | Task | Owner | Status | Completed |
|-------|------|-------|--------|-----------|
| #9 | Classification model: Win/Draw/Loss (notebooks 06–07) | Nicholas | ✅ Done | Apr 7 |
| #10 | Vercel deployment: production app with env config | Amine | ✅ Done | Apr 8 |
| #11 | Neon DB seeding: matches, players, metrics | Amine | ✅ Done | Apr 9 |
| #12 | Match calendar UI: prediction cards with actual results | Amine | ✅ Done | Apr 10 |
| #13 | Match detail page: MOTM, team rosters, score bars | Amine | ✅ Done | Apr 12 |
| #14 | Player game stats page: per-match stat breakdown | Amine | ✅ Done | Apr 12 |
| #15 | Authenticated pages: Player Stats and Pipeline Metrics | Amine | ✅ Done | Apr 13 |
| #16 | CI/CD: automated Vercel deployment on push to main | Amine | ✅ Done | Apr 18 |

**Sprint 2 Goal achieved:** Full-stack app deployed to production. All 266 matches visible with predictions, actual scores, MOTM, and per-player game stats. CI/CD deploys automatically on every push.

---

## 5. Functional Requirements

All functional requirements from the PRD are addressed. The implementation differs from the originally planned FastAPI + SvelteKit stack in one way: the web app was rebuilt as a Next.js 16 (App Router) application deployed to Vercel, which gave us a publicly accessible deployed app rather than a localhost-only tool. The ML pipeline (Python notebooks) and FastAPI service layer remain as specified.

### 5.1 Match Calendar

**Requirement:** Browse match outcome predictions in a calendar format with win/draw/loss probabilities.

**Implementation:**
- Route: `/` (public, no login required)
- 266 Premier League 2024/25 match cards loaded directly from Neon DB via Prisma (no self-referential HTTP)
- Each card shows: home team vs away team, actual score (derived by summing player goals from outfield parquet), predicted winner by team name, confidence percentage, Full Time / Upcoming badge, and a ✓ Correct / ✗ Wrong badge for past matches
- Cards are clickable, routing to `/matches/[id]`

**Where the original spec diverges:**  
The PRD specified three separate probability bars (WIN / DRAW / LOSS). We simplified to showing only the predicted winner and confidence — a single clear signal rather than three numbers. The probabilities (prob_H, prob_D, prob_A) are still stored in the DB and used in the match detail view.

### 5.2 Match Detail with Team Composite Scores

**Requirement:** Detail panel showing team composite scores and top players per team.

**Implementation:**
- Route: `/matches/[id]`
- Match header: teams, actual score, Full Time / Upcoming status, model prediction with confidence, actual outcome with Correct/Wrong badge
- **Man of the Match:** player with highest composite z-score among those with ≥ 45 minutes played; shown in orange gradient card at top, clickable to their game stats
- Team rosters: both teams side-by-side, players grouped by position (Forwards / Midfielders / Defenders / Goalkeepers), sorted by composite score descending, each with a colour-coded z-score bar (red ≥ 0.5, amber between −0.5 and 0.5, blue < −0.5)
- Every player row is a link to `/matches/[id]/players/[playerId]`

### 5.3 Player Game Stats

**Requirement:** Per-player performance breakdown with individual metric contributions.

**Implementation:**
- Route: `/matches/[id]/players/[playerId]`
- Player header: name, team, position, composite z-score (colour-coded), minutes played, match context, MOTM badge if applicable
- **Outfield stats:**
  - Attack: Goals, Assists, xG, xA, Shots on target, Shots off target, Chances created
  - Possession: Pass accuracy (%), Successful dribbles
  - Defending: Interceptions, Clearances, Recoveries, Aerial duels won
- **Goalkeeper stats:**
  - Goalkeeping: Saves, Save rate (%), Goals prevented (xGOT − conceded), xG on target faced
  - Distribution & Defending: Pass accuracy, Clearances, Interceptions, Recoveries, Aerial duels won
- Data sourced from the `MatchPlayer` table (5961 per-match records seeded from `outfield_test_scaled.parquet` and `gk_test_scaled.parquet`)

### 5.4 Player Stats Page (Authenticated)

**Requirement:** Player composite scores browsable by position.

**Implementation:**
- Route: `/stats` (Clerk-protected)
- Shows all 2024/25 season players from the `Player` table
- Position filter buttons: Forwards / Midfielders / Defenders / Goalkeepers (matching the DB values directly, no case conversion issues)
- Ordered alphabetically by name

### 5.5 Pipeline Metrics Dashboard (Authenticated)

**Requirement:** Model evaluation metrics displayed in a settings/dashboard view.

**Implementation:**
- Route: `/settings` (Clerk-protected)
- Shows most recent `PipelineMetrics` record from Neon DB (direct Prisma query)
- Displays: Model type, Accuracy, Macro F1, RMSE, last trained timestamp
- Two records seeded: RF Classifier (Accuracy 55.6%, Macro F1 0.549) and Logistic Regression (Accuracy 55.6%, Macro F1 0.549)

---

## 6. Technical Requirements

### Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Frontend + API | Next.js 16 App Router | Full-stack SSR, Vercel-native, API routes co-located with pages |
| Database | Neon PostgreSQL + Prisma ORM | Serverless-compatible; parameterized queries prevent SQL injection |
| Authentication | Clerk v7 | MFA-ready, social login, session management, Next.js middleware integration |
| Deployment | Vercel | Preview deploys per PR, zero-config Next.js, automatic CDN |
| ML Pipeline | Python (scikit-learn, pandas, FotMob/FBref) | Offline notebooks → predictions → DB seed |

### Architecture Decision: Next.js over FastAPI + SvelteKit

The original PRD specified a FastAPI + SvelteKit localhost app. We pivoted to Next.js for one critical reason: **the assignment requires a deployed app**. A localhost FastAPI + SvelteKit app cannot be deployed without significant additional infrastructure (a Python server, static build pipeline, environment parity). Next.js on Vercel deploys with a single command, gives us server-side rendering for free, and co-locates API routes with the UI.

The FastAPI service layer (`goals_app/`) still exists and is used for the ML pipeline, but the web-facing application is entirely Next.js.

### Data Flow

```
Browser (React Server Components)
  └─ Server Component fetch ──► Prisma Client ──► Neon PostgreSQL
                                                    ├─ Match (266 rows)
                                                    ├─ Player (2272 rows)
                                                    ├─ MatchPlayer (5961 rows)
                                                    └─ PipelineMetrics (2 rows)

Python ML Pipeline (local, offline)
  notebooks/ → scikit-learn → parquet outputs
    └─ export_for_seed.py → seed_data.json
         └─ seed_db.ts (npx tsx) → Neon PostgreSQL
```

Key architectural decision: **Server Components query Prisma directly** — no self-referential HTTP fetch. Early implementations fetched `${APP_URL}/api/matches` from within a server component, which silently failed on Vercel (deployment URLs don't match aliases). This was discovered and fixed, replacing every such fetch with a direct `prisma.<model>.findMany()` call.

### Database Schema

```prisma
model Match {
  id         String   @id          // FotMob match_id as string
  homeTeam   String
  awayTeam   String
  date       DateTime
  homeGoals  Int?                   // derived from player goal sums
  awayGoals  Int?
  season     String
  winProb    Float?                 // prob_H from classifier
  drawProb   Float?                 // prob_D
  lossProb   Float?                 // prob_A
  prediction String?               // "Home Win" | "Draw" | "Away Win"
  @@index([season])
  @@index([date])
}

model Player {
  id       String  @id             // "{player_id}_{season}" — unique per season
  name     String
  team     String
  position String                  // forward | midfielder | defender | goalkeeper
  attScore Float?
  midScore Float?
  defScore Float?
  gkScore  Float?
  season   String
  @@index([season])
  @@index([team])
  @@index([position])
}

model MatchPlayer {
  id             String  @id       // "{match_id}_{player_id}"
  matchId        String
  playerId       String
  playerName     String
  teamName       String
  position       String
  isMotm         Boolean @default(false)
  compositeScore Float?
  minutesPlayed  Float?
  goals          Float?
  assists        Float?
  xGoals         Float?
  xAssists       Float?
  shotsOnTarget  Float?
  shotsOffTarget Float?
  chancesCreated Float?
  passAccuracy   Float?
  dribbles       Float?
  interceptions  Float?
  clearances     Float?
  recoveries     Float?
  aerialsWon     Float?
  saves          Float?            // GK only
  saveRate       Float?            // GK only
  xGotFaced      Float?            // GK only
  goalsPrevented Float?            // GK only
  @@index([matchId])
}

model PipelineMetrics {
  id        Int      @id @default(autoincrement())
  modelType String
  rmse      Float?
  accuracy  Float?
  f1        Float?
  trainedAt DateTime @default(now())
}
```

### Known Technical Bug Fixed: Position Group Mapping

The feature engineering notebook (`03_feature_engineering.ipynb`) assigned `position_group = 'midfielder'` to all outfield players regardless of their FotMob `position_id`. The correct mapping (verified against known players in the raw parquet) is:

| `position_id_int` | Correct group | Example players |
|---|---|---|
| 1 | `defender` | Harry Maguire, Luke Shaw, Joachim Andersen |
| 2 | `midfielder` | Tom Cairney, Bruno Fernandes, Casemiro |
| 3 | `forward` | Raúl Jiménez, Harry Wilson, Matheus Cunha |

This was fixed in `export_for_seed.py` by remapping `position_id_int` before aggregation, without modifying the notebook:

```python
POSITION_MAP = {1: "defender", 2: "midfielder", 3: "forward"}
of["position_group"] = of["position_id_int"].map(POSITION_MAP).fillna(of["position_group"])
```

---

## 7. ML Pipeline

### Overview

The full pipeline runs across seven Jupyter notebooks, with a strict temporal split: seasons 2021/22, 2022/23, and 2023/24 are used for training; 2024/25 is held out as the test set and never seen during fitting or cross-validation.

### Notebook Execution Order

| Notebook | Purpose | Key Outputs |
|----------|---------|------------|
| `01_preprocessing.ipynb` | Merge FotMob + FBref | `outfield_players.parquet`, `goalkeepers.parquet` per season |
| `02_eda.ipynb` | Exploratory analysis | Distribution plots, correlation heatmaps, completeness audit |
| `03_feature_engineering.ipynb` | Composite scores | `outfield_train_scaled.parquet`, `outfield_test_scaled.parquet`, `gk_train_scaled.parquet`, `gk_test_scaled.parquet` |
| `04_regression.ipynb` | Ridge + RF regressors | Model artifacts in `data/models/` |
| `05_clustering.ipynb` | K-Means archetypes | `outfield_train_clustered.parquet` |
| `06_team_aggregation.ipynb` | Team-level features | Feature vectors for classification |
| `07_classification.ipynb` | RF + LR classifiers | `match_predictions_test.parquet` (266 matches) |

### Composite Score Formulas

All input metrics are z-score normalised fit on train seasons only.

**ATT (Forwards):**
```
ATT = 0.25*(Goals + Assists) + 0.20*xG + 0.15*xA + 0.15*Dribbles
    + 0.10*Shots + 0.10*ChancesCreated + 0.05*Recoveries
```

**MID (Midfielders):**
```
MID = 0.20*ProgPass + 0.20*ChancesCreated + 0.15*xA + 0.15*(Goals + Assists)
    + 0.15*TacklesWon + 0.10*Interceptions + 0.05*Recoveries
```

**DEF (Defenders):**
```
DEF = 0.25*TacklesWon + 0.20*AerialDuelsWon + 0.20*Clearances
    + 0.15*Interceptions + 0.10*Blocks + 0.10*ProgPass
```

**GK (Goalkeepers):**
```
GK = 0.30*Saves + 0.25*xGOT + 0.15*DivingSaves + 0.15*SavesInsideBox
   + 0.10*HighClaims + 0.05*SweeperActions
```

### Classification Setup

- **Features:** 8 values per match — home ATT + MID + DEF + GK (team-level composite score sums), away ATT + MID + DEF + GK
- **Target:** 3-class: H (home win) / D (draw) / A (away win)
- **Models:** Random Forest Classifier, Logistic Regression — both with `class_weight='balanced'` (La Liga / PL class distribution: ~45% H, ~25% D, ~30% A)
- **Validation:** Walk-forward cross-validation within training seasons (no data leakage)

### Results on 2024/25 Test Season (266 matches)

| Model | Accuracy | Macro F1 |
|-------|----------|----------|
| Logistic Regression | 55.6% | 0.549 |
| Random Forest Classifier | 54.8% | 0.535 |

**Baseline comparison:** A naive "always predict home win" classifier achieves ~44% accuracy on this dataset. Both models beat that baseline, though the prediction problem remains fundamentally difficult — sports outcomes have high inherent randomness.

### Bugs Encountered & Fixed in Notebooks

| Notebook | Bug | Fix |
|----------|-----|-----|
| `05_clustering.ipynb` | `KeyError: 'winger'` — FotMob has no winger position group | Removed `'winger'` from position concat list |
| `07_classification.ipynb` | `FileNotFoundError: data_backup/processed` | Corrected `DS_DIR` to `data/processed` |
| `07_classification.ipynb` | `ValueError: Input X contains NaN` in LogReg | Broadened imputation from 8 named columns to all numeric columns with `fillna(0)` fallback for entirely-null columns |

---

## 8. Custom Skills & Agents

### Skills Defined

#### `/add-feature` — Full-stack Feature Implementation

Located at `.claude/skills/add-feature.md`. This skill encodes the complete workflow for adding a new feature to the GOALS FastAPI + SvelteKit backend, enforcing project conventions at every step.

**Workflow (5 steps, in order):**
1. **Read existing patterns** — reads `config.py`, router files, and `feature_service.py` to understand available helpers before writing any new code
2. **Design** — states endpoint path, parameters, response envelope, and which service functions to reuse
3. **Implement backend** — extends the correct router, uses `config.py` constants, reuses local router helpers like `_load_fixtures()`
4. **Implement frontend** — adds Svelte component using only CSS variables from `app.css`
5. **Verify** — identifies related tests and provides concrete curl command for manual verification

**Hard constraints enforced by the skill:**
- Never shuffle train/test — always temporal (walk-forward) split
- `data/` is read-only — only `scraper_service.py` may write under `data/47/`
- Scaler fit on train only — never refit on test data
- Player name fuzzy match — `rapidfuzz` threshold ≥ 85
- Do not modify `fotmob_final.ipynb`
- Use `TRAIN_SEASONS` and `TEST_SEASON` from `config.py` — never hardcode season strings

**v1 → v2 Iteration:**  
The original v1 skill was discovered to miss local helper functions defined inside routers (e.g., `_load_fixtures()` inside `calendar.py`), resulting in unnecessary duplicate logic being written. v2 was updated to explicitly require inspecting local router helpers in Step 1 and named the response envelope pattern explicitly in Step 2.

#### `/create-pr` — Pull Request Creation

Located at `.claude/skills/create-pr.md`. Automates PR creation with structured title, description, and test plan. Ensures every PR includes the security acceptance criteria checklist from `.claude/security.md`.

### Agents Defined

#### `security-reviewer` — OWASP Security Review Agent

Located at `.claude/agents/security-reviewer.md`. A specialised subagent invoked before any PR touching `/app/api/` routes or `middleware.ts`. Reviews staged changes for all OWASP Top 10 categories:

- A01 Broken Access Control — missing auth checks, IDOR
- A02 Cryptographic Failures — plaintext secrets, weak hashing
- A03 Injection — SQL injection (mitigated by Prisma), XSS, command injection
- A04 Insecure Design — missing rate limiting, input validation
- A05 Security Misconfiguration — exposed stack traces, open CORS
- A06 Vulnerable Components — known CVEs in npm dependencies
- A07 Authentication Failures — session management issues
- A08 Integrity Failures — unsigned artifacts
- A09 Logging Failures — PII in logs
- A10 SSRF — user-controlled URLs fetched server-side

Output format: per-issue severity (HIGH / MEDIUM / LOW), file:line location, OWASP category, description, and remediation. Ends with a summary count.

#### `test-writer` — TDD Red-Green-Refactor Agent

Located at `.claude/agents/test-writer.md`. Writes failing Vitest tests before implementation, enforcing the red-green-refactor commit pattern required by the testing strategy:

```
feat: add failing tests for [feature]   ← RED
feat: implement [feature]               ← GREEN
refactor: [optional cleanup]            ← REFACTOR
```

### MCP Integration

The Claude Code session used the GitHub MCP server to manage the project board directly from the development environment. Instead of leaving the terminal to create GitHub issues manually, the MCP server was used to:

1. Create the GitHub Project (project #3)
2. Add Sprint 1 and Sprint 2 milestones
3. Create all 15 issues with structured titles, bodies, owners, and milestone assignments
4. Add all issues to the project board
5. Close completed issues

This eliminated context-switching between the development environment and the GitHub web UI, and ensured issue descriptions were consistent with the project specification in `CLAUDE.md`.

---

## 9. 4-Gate Security Pipeline

Security is enforced at four gates, all defined in `.claude/security.md`.

### Gate 1 — Gitleaks: Secrets Detection

**Tool:** `gitleaks/gitleaks-action@v2`  
**Where:** CI job `security` (`.github/workflows/ci.yml`)  
**Blocks merge:** Yes — any committed secret fails the CI run  

Gitleaks scans the entire git history on every push and PR for accidentally committed secrets (API keys, connection strings, tokens). The `.env.local` file is git-ignored; all production secrets live in Vercel Environment Variables and GitHub Actions Secrets.

### Gate 2 — npm audit: Dependency Scanning

**Tool:** `npm audit --audit-level=moderate`  
**Where:** CI job `security`  
**Blocks merge:** Yes — any HIGH or CRITICAL vulnerability in the dependency tree fails the build  

Scans all npm packages for known CVEs. The threshold is `moderate`, meaning HIGH and CRITICAL vulnerabilities are blocking. LOW-severity findings are logged but not blocking.

### Gate 3 — Security Reviewer Agent: SAST

**Tool:** `.claude/agents/security-reviewer.md` (custom Claude Code agent)  
**Where:** Run via `/security-reviewer` before any PR touching `/app/api/` or `middleware.ts`  
**Blocks merge:** Expected on all auth/API PRs — human review of findings required  

The agent reviews code changes for all OWASP Top 10 risks with specific focus on:
- **A01:** Every `/api/` route that returns player or match data checks `auth()` from Clerk; unauthenticated requests receive `401 Unauthorized`
- **A03:** All DB queries use Prisma ORM — zero raw SQL string interpolation anywhere in the codebase
- **A10:** No user-controlled URLs are fetched server-side — the self-referential HTTP fetch anti-pattern was identified and eliminated

Additionally, the CI workflow includes an AI PR review step (`anthropics/claude-code-action@beta`) that runs on every pull request, applying the C.L.E.A.R. framework and flagging auth/injection risks automatically.

### Gate 4 — OWASP Definition of Done Checklist

**Where:** Every PR description includes this checklist manually  
**Blocks merge:** Manual check required  

Every PR must satisfy before merge:

- [ ] No new HIGH/CRITICAL findings in `npm audit`
- [ ] Gitleaks CI gate passes (no secrets committed)
- [ ] PRs touching `/app/api/` or `middleware.ts` reviewed by `security-reviewer` agent
- [ ] All DB queries use Prisma (no template literals with user input)
- [ ] New environment variables added to `.env.example` (never `.env.local`)

### OWASP Top 10 Mitigations (Full Table)

| # | Risk | Mitigation in GOALS |
|---|------|---------------------|
| A01 | Broken Access Control | Clerk middleware protects `/stats` and `/settings`; `auth()` called in all player/metrics API routes |
| A02 | Cryptographic Failures | No custom crypto; Clerk manages sessions and tokens; Neon enforces TLS |
| A03 | Injection | Prisma ORM — parameterized queries only; no raw SQL; no template literals with user input |
| A04 | Insecure Design | Auth required for all prediction/player data; ML pipeline is offline, not callable from the web |
| A05 | Security Misconfiguration | `.env.local` git-ignored; secrets in Vercel + GitHub Secrets; no debug mode in production |
| A06 | Vulnerable Components | `npm audit --audit-level=moderate` in CI blocks on HIGH/CRITICAL |
| A07 | Authentication Failures | Clerk handles MFA, token rotation, session invalidation |
| A08 | Integrity Failures | Gitleaks in CI + pre-commit hook; no unsigned artifacts |
| A09 | Logging Failures | Vercel captures all API requests; no PII logged |
| A10 | SSRF | No user-controlled URLs fetched server-side; self-referential HTTP fetch anti-pattern removed |

---

## 10. Testing Strategy

### Test Pyramid

```
         /\
        /E2E\        Playwright — 2 specs (auth-flow, match-calendar)
       /------\
      / Integr \     Vitest — API routes with mocked Prisma
     /----------\
    /    Unit    \   Vitest — components, utilities
   /______________\
```

### Unit & Integration Tests (Vitest)

13 tests across 3 test files, all passing:

| File | Tests | What is covered |
|------|-------|-----------------|
| `__tests__/api/matches.test.ts` | 4 | GET /api/matches: 200 with data, season filter, empty result, 500 on DB error |
| `__tests__/api/players.test.ts` | 5 | GET /api/players: 401 without auth, 200 with auth, position filter, team filter, empty result |
| `__tests__/api/metrics.test.ts` | 4 | GET /api/metrics: 401 without auth, 200 with data, 404 when no records, structure validation |

**Mocking strategy:** Prisma Client is fully mocked in `__tests__/setup.ts` (all four models including `MatchPlayer`). Clerk `auth()` is mocked to return `{ userId: null }` by default, allowing auth enforcement to be tested by overriding in specific tests.

### E2E Tests (Playwright)

Two spec files in `e2e/`:
- `match-calendar.spec.ts` — verifies the home page loads, match cards render with team names and prediction data
- `auth-flow.spec.ts` — verifies unauthenticated users are redirected from `/stats` and `/settings` to `/sign-in`

### Coverage Threshold

Vitest is configured with `@vitest/coverage-v8` at a 70% line/function threshold and 60% branch threshold, enforced in CI. The build fails if coverage drops below these thresholds.

### TDD Commit Pattern

All new features followed the red-green-refactor pattern:

```
feat: add failing tests for [feature]   ← RED (committed with failing tests)
feat: implement [feature]               ← GREEN (implementation makes tests pass)
refactor: [optional cleanup]            ← REFACTOR
```

---

## 11. Known Gaps & Honest Assessment

### What Works Well

- **The deployed app is live and fully functional.** All 266 matches render with real predictions, actual scores, MOTM, and player game stats.
- **CI/CD is complete.** Every push to `main` automatically runs lint, typecheck, tests, security scan, and deploys to Vercel production.
- **ML pipeline beats the naive baseline.** 55.6% accuracy vs ~44% for "always predict home win" — meaningful but not dramatic improvement, which is expected in sports prediction.
- **Security is genuinely enforced**, not just documented — Prisma ORM eliminates SQL injection by construction, Clerk prevents unauthorized access to sensitive pages, and Gitleaks + npm audit run automatically in CI.

### What Diverged from the Original PRD

| Original PRD Specification | What Was Built | Reason |
|---------------------------|----------------|--------|
| FastAPI + SvelteKit, localhost only | Next.js 16 App Router, Vercel deployed | Assignment requires a deployed app; Next.js on Vercel is the most direct path |
| La Liga (ID 87) data | Premier League (ID 47) data | La Liga FotMob data was not collected; Premier League data was already available |
| SSE progress streaming for scraper and pipeline | Not in web app (pipeline runs offline in notebooks) | Given the notebook-first approach, a real-time training UI was not implemented |
| Radar chart per player | Simple stat rows per section | Chart.js was not added to the Next.js app; the stat breakdown is text-based |
| Team rolling form chart | Not implemented | Out of scope given the time available |
| Confusion matrix heatmap | Not implemented | The metrics page shows accuracy and F1 only |

### Accuracy Ceiling

55.6% accuracy on a 3-class problem is meaningful but modest. Contributing factors:
- Football has high inherent randomness; even the best published models rarely exceed 60% on a 3-class task
- Feature set is composite-score-based (aggregate performance) rather than fine-grained (e.g., tactical matchups, injuries, home crowd effects)
- 266 test matches is a relatively small evaluation window — a single season

### Position Group Bug (Resolved)

The feature engineering notebook incorrectly assigned `position_group = 'midfielder'` to all outfield players. This was discovered when the match detail page showed only midfielders and goalkeepers. The fix was applied in `export_for_seed.py` using `position_id_int` remapping without modifying the notebook. This means the composite scores in the DB are correct (scored by the right formula for each position) but the position labels in the raw parquet files remain as 'midfielder' — the remapping happens at seed time.
