# HW5 Retrospective — Custom Skill + MCP Integration

**Project:** GOALS — Game Outcome and Analytics Learning System  
**Course:** EECE5644  
**Author:** Amine Kebichi  
**Date:** April 4, 2026

---

## Part 1: How the Custom Skill Changed the Workflow

The `/add-feature` skill encodes the full-stack feature workflow that previously lived only in my head: read existing patterns → design the endpoint → implement backend → implement frontend → verify. Before the skill, every new GOALS endpoint required me to manually recall that convention, check which service helpers existed, and remember project-specific safety constraints (temporal split, read-only `data/`, scaler fitting rules). That overhead was small per task but accumulated across the ~8 remaining endpoints still to build.

**Tasks that became easier:**

- **`/api/players/{id}/radar`** — The skill's Step 1 pointed me straight to `get_player_metric_contributions()` in `feature_service.py`. Without the skill I might have reimplemented the weighted z-score aggregation from scratch. The skill made "look for existing helpers first" a non-optional step.

- **`/api/teams/form`** — Running v1 exposed a gap: I had to discover `_load_fixtures()` (a local router helper in `calendar.py`) on my own. That gap informed v2, which now says explicitly to check for local helpers *inside routers* before writing new loading logic. This kind of institutional knowledge is exactly what a skill should capture.

**v1 → v2 iteration summary:**

| Gap found in v1 | Change made in v2 |
|---|---|
| Missed `_load_fixtures()` local helper | Step 1 now says to scan router files for local helpers before writing new ones |
| Response envelope was inconsistent | Step 2 names the `{"resource_key": [...]}` pattern explicitly |
| Verification step was vague | Step 5 now has a concrete curl template with host/port |
| `config.py` constants weren't checked first | Step 1 now leads with `config.py`; Step 3 repeats the constraint |

The skill acts as a living checklist. Each iteration makes implicit project knowledge explicit, so the next feature takes less cognitive overhead and produces more consistent output.

---

## Part 2: What GitHub MCP Integration Enables

### Setup

**Prerequisites:** Node.js installed, GitHub personal access token with `repo` + `issues` scopes.

```bash
# 1. Set token in your shell (or add to .env / shell profile)
export GITHUB_TOKEN=ghp_<your-token-here>

# 2. Register the MCP server
claude mcp add github-mcp -- npx -y @modelcontextprotocol/server-github

# 3. Verify it's running
claude mcp list
# → github-mcp   npx -y @modelcontextprotocol/server-github   running
```

### What it enables that wasn't possible before

Without MCP, GitHub operations required leaving Claude Code entirely: opening the browser, navigating to the repo, creating issues manually, then switching back. With the GitHub MCP, Claude Code becomes a single pane for both code and project management.

**Demonstrated task — creating milestone issues for remaining notebook work:**

With the MCP active, I ran:
> "Use the GitHub MCP to create issues for the three remaining notebook implementations that need to be done before April 18."

Claude Code used the MCP tools to:
1. List existing issues on `aminekebichi/GOALS` (confirmed connection)
2. Create three issues:
   - *"Implement 01_data_merge.ipynb — FBref + FotMob fuzzy join"* (label: `ml-pipeline`)
   - *"Implement 04_regression.ipynb — Ridge + RF Regressor with walk-forward CV"* (label: `ml-pipeline`)
   - *"Implement 06_classification.ipynb — RF Classifier with balanced class weights"* (label: `ml-pipeline`)

The issues were created with body text generated from the CLAUDE.md ML spec — something that would have taken 10–15 minutes of manual copy-paste. The MCP collapsed that to a single prompt.

**Other workflows the GitHub MCP enables:**
- Checking open issues before starting work (avoids duplicate effort with Nathaniel)
- Creating a PR and auto-populating the description from recent commits
- Searching issues for a keyword to find prior decisions ("why did we set rapidfuzz threshold to 85?")

---

## Part 3: What I Would Build Next

**More skills:**
- `/ml-notebook <n>` — Implements one of the 6 stub notebooks following the GOALS ML spec (temporal split, walk-forward CV, artifact serialization). The spec is already in CLAUDE.md; the skill would route the right constraints to the right notebook number.
- `/review` — Audits a git diff against GOALS-specific constraints: no data shuffle, scaler fit on train only, no hardcoded paths. Faster than re-reading CLAUDE.md before every PR.

**Hooks:**
- A `pre-commit` hook that runs a lightweight check for the pattern `train_test_split` with `shuffle=True` — our biggest ML safety risk. If found, block the commit with a message: "Temporal split required — never shuffle match data."
- A `post-tool-call` hook on file writes to `data/` that warns if any file outside `data/47/*/raw/` or `data/47/*/output/` is being written (enforces read-only constraint at the tooling level).

**Sub-agents:**
- A parallel notebook execution agent: given a list of notebook numbers, launch one sub-agent per notebook, each with its own context window, and aggregate results (RMSE, accuracy, confusion matrix) into a summary table. The six notebooks are independent enough that this would cut total ML pipeline execution time significantly.
- A `scraper-monitor` sub-agent that runs in the background during a long FotMob scrape, polling for progress and surfacing rate-limit errors without blocking the main conversation.

---

## Summary

The `/add-feature` skill made full-stack feature development more consistent and less cognitively demanding. The v1 → v2 iteration — driven by real task runs — shows how skills improve through use, not just design. The GitHub MCP collapsed the boundary between code editing and project management, enabling issue creation, PR authoring, and repo queries without leaving Claude Code. Together, these tools move the GOALS development loop closer to the ideal: describe what you want, let the tooling handle the how.
