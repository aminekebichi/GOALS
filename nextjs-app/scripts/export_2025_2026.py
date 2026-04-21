"""
export_2025_2026.py

Generates seed data for the 2025/26 Premier League season:
  - All 380 fixtures (played + upcoming) with probabilities
  - Actual goals derived from FotMob player stats (played matches only)
  - Per-match player composite scores for the 239 matches with player data
  - Season-level player averages

Usage:
    python nextjs-app/scripts/export_2025_2026.py
Outputs:
    nextjs-app/scripts/seed_2025_2026.json
"""

import json
import math
import sys
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

from goals_app.services.ml_service import predict_all_fixtures, load_model
from goals_app.services.feature_service import (
    load_season,
    compute_outfield_composite,
    compute_gk_composite,
)

SEASON = "2025_2026"
OUT_FILE = Path(__file__).parent / "seed_2025_2026.json"

POS_GROUP_TO_POSITION = {
    "DEF": "defender",
    "MID": "midfielder",
    "ATT": "forward",
    "GK": "goalkeeper",
}
POS_SCORE_KEY = {
    "forward": "attScore",
    "midfielder": "midScore",
    "defender": "defScore",
    "goalkeeper": "gkScore",
}


def safe_float(v):
    try:
        f = float(v)
        return None if math.isnan(f) else round(f, 4)
    except (TypeError, ValueError):
        return None


def safe_int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


# ── Load model and 2025/26 data ───────────────────────────────────────────────
print("Loading model artifacts...")
_, outfield_scaler, gk_scaler, _ = load_model()

print(f"Loading {SEASON} season data...")
outfield_df, gk_df, fixtures_df = load_season(SEASON)

# ── Compute composite scores (apply saved scalers, never refit) ───────────────
print("Computing composite scores...")
outfield_scored, _ = compute_outfield_composite(outfield_df, outfield_scaler)
gk_scored, _ = compute_gk_composite(gk_df, gk_scaler)

outfield_scored["position"] = outfield_scored["position_group"].map(POS_GROUP_TO_POSITION).fillna("midfielder")
gk_scored["position"] = "goalkeeper"

# ── Predictions for all 380 fixtures ─────────────────────────────────────────
print("Generating predictions for all fixtures...")
predictions = predict_all_fixtures(SEASON)
pred_map = {str(p["match_id"]): p for p in predictions}
print(f"  Predictions generated: {len(pred_map)}")

# ── Derive actual goals from player stats ─────────────────────────────────────
# Group goals by (match_id, team_name) from outfield data
goal_by_match_team: dict = {}
for _, row in outfield_df.iterrows():
    mid = str(int(row["match_id"]))
    team = str(row.get("team_name", ""))
    g = row.get("goals", 0)
    g = 0 if (g is None or (isinstance(g, float) and math.isnan(g))) else g
    if mid not in goal_by_match_team:
        goal_by_match_team[mid] = {}
    goal_by_match_team[mid][team] = goal_by_match_team[mid].get(team, 0) + g

score_map: dict = {}
for _, fix in fixtures_df[fixtures_df["finished"]].iterrows():
    mid = str(int(fix["match_id"]))
    if mid not in goal_by_match_team:
        continue  # played but no player data scraped
    home = str(fix["home_team"])
    away = str(fix["away_team"])
    teams = goal_by_match_team[mid]
    score_map[mid] = {
        "home_goals": safe_int(teams.get(home, 0)),
        "away_goals": safe_int(teams.get(away, 0)),
    }

print(f"  Scores derived for {len(score_map)} played matches")
print(f"  Upcoming matches: {(~fixtures_df['finished']).sum()}")

# ── Build matches list (all 380 fixtures) ─────────────────────────────────────
matches = []
for _, fix in fixtures_df.iterrows():
    mid = str(int(fix["match_id"]))
    pred = pred_map.get(mid, {})
    win_p = pred.get("win_prob")
    draw_p = pred.get("draw_prob")
    loss_p = pred.get("loss_prob")

    prediction = None
    if all(v is not None for v in [win_p, draw_p, loss_p]):
        prediction = max(
            [("Home Win", win_p), ("Draw", draw_p), ("Away Win", loss_p)],
            key=lambda x: x[1],
        )[0]

    scores = score_map.get(mid, {})
    date = pd.Timestamp(fix["match_date"])
    matches.append({
        "id":         mid,
        "homeTeam":   str(fix["home_team"]),
        "awayTeam":   str(fix["away_team"]),
        "date":       date.isoformat(),
        "season":     SEASON,
        "homeGoals":  scores.get("home_goals"),
        "awayGoals":  scores.get("away_goals"),
        "winProb":    safe_float(win_p),
        "drawProb":   safe_float(draw_p),
        "lossProb":   safe_float(loss_p),
        "prediction": prediction,
    })

print(f"Matches: {len(matches)}")

# ── Build players list (season averages from 2025/26 data) ───────────────────
of_agg = (
    outfield_scored
    .groupby(["player_id", "player_name", "team_name", "position"])["composite_score"]
    .mean()
    .reset_index()
)
gk_agg = (
    gk_scored
    .groupby(["player_id", "player_name", "team_name"])["composite_score"]
    .mean()
    .reset_index()
)
gk_agg["position"] = "goalkeeper"

players = []
seen = set()
for _, row in pd.concat([of_agg, gk_agg], ignore_index=True).iterrows():
    pid = str(int(row["player_id"]))
    key = (pid, SEASON)
    if key in seen:
        continue
    seen.add(key)
    pos = str(row["position"])
    score_key = POS_SCORE_KEY.get(pos)
    entry = {
        "id":       f"{pid}_{SEASON}",
        "name":     str(row["player_name"]),
        "team":     str(row["team_name"]),
        "position": pos,
        "season":   SEASON,
        "attScore": None, "midScore": None,
        "defScore": None, "gkScore":  None,
    }
    if score_key:
        entry[score_key] = safe_float(row["composite_score"])
    players.append(entry)

print(f"Players: {len(players)}")

# ── Build matchPlayers list (only matches with player data) ───────────────────
match_ids_with_data = set(outfield_scored["match_id"].astype(int).astype(str))

# Index GK data by match_id for fast lookup
gk_by_match: dict = {}
for _, r in gk_scored.iterrows():
    mid = str(int(r["match_id"]))
    gk_by_match.setdefault(mid, []).append(r)

match_players = []
for mid in match_ids_with_data:
    mid_int = int(mid)

    of_match = outfield_scored[outfield_scored["match_id"] == mid_int]
    gk_match = gk_by_match.get(mid, [])

    rows = []

    for _, r in of_match.iterrows():
        pid = str(int(r["player_id"]))
        # pass_accuracy: derive from accurate_passes / accurate_passes_total
        passes = r.get("accurate_passes", None)
        passes_total = r.get("accurate_passes_total", None)
        pass_acc = None
        if passes is not None and passes_total is not None and passes_total > 0:
            try:
                pass_acc = round(float(passes) / float(passes_total), 4)
            except (TypeError, ValueError, ZeroDivisionError):
                pass_acc = None

        rows.append({
            "id":             f"{mid}_{pid}",
            "matchId":        mid,
            "playerId":       pid,
            "playerName":     str(r.get("player_name", "")),
            "teamName":       str(r.get("team_name", "")),
            "position":       str(r.get("position", "midfielder")),
            "compositeScore": safe_float(r.get("composite_score")),
            "minutesPlayed":  safe_float(r.get("minutes_played")),
            "goals":          safe_float(r.get("goals")),
            "assists":        safe_float(r.get("assists")),
            "xGoals":         safe_float(r.get("expected_goals")),
            "xAssists":       safe_float(r.get("expected_assists")),
            "shotsOnTarget":  safe_float(r.get("ShotsOnTarget")),
            "shotsOffTarget": safe_float(r.get("ShotsOffTarget")),
            "chancesCreated": safe_float(r.get("chances_created")),
            "passAccuracy":   pass_acc,
            "dribbles":       safe_float(r.get("dribbles_succeeded")),
            "interceptions":  safe_float(r.get("interceptions")),
            "clearances":     safe_float(r.get("clearances")),
            "recoveries":     safe_float(r.get("recoveries")),
            "aerialsWon":     safe_float(r.get("aerials_won")),
            "saves": None, "saveRate": None, "xGotFaced": None, "goalsPrevented": None,
            "isMotm": False,
        })

    for r in gk_match:
        pid = str(int(r["player_id"]))
        saves = r.get("saves", None)
        conceded = r.get("goals_conceded", None)
        save_rate = None
        if saves is not None and conceded is not None:
            try:
                total_shots = float(saves) + float(conceded)
                save_rate = round(float(saves) / total_shots, 4) if total_shots > 0 else None
            except (TypeError, ValueError):
                save_rate = None

        rows.append({
            "id":             f"{mid}_{pid}",
            "matchId":        mid,
            "playerId":       pid,
            "playerName":     str(r.get("player_name", "")),
            "teamName":       str(r.get("team_name", "")),
            "position":       "goalkeeper",
            "compositeScore": safe_float(r.get("composite_score")),
            "minutesPlayed":  safe_float(r.get("minutes_played")),
            "goals":          safe_float(r.get("goals", 0)),
            "assists":        safe_float(r.get("expected_assists")),
            "xGoals":         None,
            "xAssists":       safe_float(r.get("expected_assists")),
            "shotsOnTarget":  None, "shotsOffTarget": None,
            "chancesCreated": safe_float(r.get("chances_created")),
            "passAccuracy":   None,
            "dribbles":       None,
            "interceptions":  safe_float(r.get("interceptions")),
            "clearances":     safe_float(r.get("clearances")),
            "recoveries":     safe_float(r.get("recoveries")),
            "aerialsWon":     safe_float(r.get("aerials_won")),
            "saves":          safe_float(r.get("saves")),
            "saveRate":       save_rate,
            "xGotFaced":      safe_float(r.get("expected_goals_on_target_faced")),
            "goalsPrevented": safe_float(r.get("goals_prevented")),
            "isMotm": False,
        })

    # Mark MOTM: highest composite score among players with >= 45 minutes
    eligible = [
        p for p in rows
        if p["minutesPlayed"] is not None and p["minutesPlayed"] >= 45
        and p["compositeScore"] is not None
    ]
    if eligible:
        motm = max(eligible, key=lambda p: p["compositeScore"])
        motm["isMotm"] = True

    match_players.extend(rows)

print(f"Match players: {len(match_players)}")

# ── Write output ─────────────────────────────────────────────────────────────
payload = {
    "matches": matches,
    "players": players,
    "matchPlayers": match_players,
    "metrics": [],  # no new metrics — keep existing pipeline metrics
}
OUT_FILE.write_text(json.dumps(payload, indent=2, default=str))
print(f"Written to {OUT_FILE}")
