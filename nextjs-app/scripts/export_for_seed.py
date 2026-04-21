"""
export_for_seed.py

Reads notebook-produced parquets and exports seed_data.json for seed_db.ts.

Usage:
    python nextjs-app/scripts/export_for_seed.py
Outputs:
    nextjs-app/scripts/seed_data.json
"""

import json
import math
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
PREDICTIONS     = ROOT / "data/processed/datasets/match_predictions_test.parquet"
OUTFIELD_RAW    = ROOT / "data/47/2024_2025/output/outfield_players.parquet"
OUTFIELD_TRAIN  = ROOT / "data/processed/datasets/outfield_train_scaled.parquet"
OUTFIELD_TEST   = ROOT / "data/processed/datasets/outfield_test_scaled.parquet"
GK_TRAIN        = ROOT / "data/processed/datasets/gk_train_scaled.parquet"
GK_TEST         = ROOT / "data/processed/datasets/gk_test_scaled.parquet"
OUT_FILE        = Path(__file__).parent / "seed_data.json"


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


# ── Matches ───────────────────────────────────────────────────────────────────
preds = pd.read_parquet(PREDICTIONS)

# Derive actual goals per match by summing player goals per team from outfield parquet
try:
    of_raw = pd.read_parquet(OUTFIELD_RAW, columns=["match_id", "home_team", "away_team", "team_name", "goals"])
    of_raw["match_id"] = of_raw["match_id"].astype(str)
    team_goals = of_raw.groupby(["match_id", "team_name"])["goals"].sum().reset_index()
    # Build score_map: match_id → {home_goals, away_goals}
    home_info = of_raw[["match_id", "home_team"]].drop_duplicates().set_index("match_id")["home_team"]
    away_info = of_raw[["match_id", "away_team"]].drop_duplicates().set_index("match_id")["away_team"]
    score_map = {}
    for mid, grp in team_goals.groupby("match_id"):
        goal_dict = dict(zip(grp["team_name"], grp["goals"]))
        home = home_info.get(mid)
        away = away_info.get(mid)
        if home and away:
            score_map[mid] = {
                "home_goals": safe_int(goal_dict.get(home, 0)),
                "away_goals": safe_int(goal_dict.get(away, 0)),
            }
except Exception as e:
    print(f"Warning: could not derive scores from outfield data: {e}")
    score_map = {}

OUTCOME_LABEL = {"H": "Home Win", "D": "Draw", "A": "Away Win"}

matches = []
for _, row in preds.iterrows():
    mid = str(row["match_id"])
    scores = score_map.get(mid, {})
    date = pd.Timestamp(row["match_date"])
    matches.append({
        "id":         mid,
        "homeTeam":   str(row["home_team"]),
        "awayTeam":   str(row["away_team"]),
        "date":       date.isoformat(),
        "season":     str(row["season"]),
        "homeGoals":  scores.get("home_goals"),
        "awayGoals":  scores.get("away_goals"),
        "winProb":    safe_float(row["prob_H"]),
        "drawProb":   safe_float(row["prob_D"]),
        "lossProb":   safe_float(row["prob_A"]),
        "prediction": OUTCOME_LABEL.get(str(row.get("predicted", "")), None),
    })

print(f"Matches: {len(matches)}")

# ── Players ───────────────────────────────────────────────────────────────────
POSITION_MAP = {1: "defender", 2: "midfielder", 3: "forward"}

of = pd.concat([pd.read_parquet(OUTFIELD_TRAIN), pd.read_parquet(OUTFIELD_TEST)], ignore_index=True)
gk = pd.concat([pd.read_parquet(GK_TRAIN), pd.read_parquet(GK_TEST)], ignore_index=True)

# Fix position_group using position_id_int — notebook incorrectly set all outfield to 'midfielder'
of["position_group"] = of["position_id_int"].map(POSITION_MAP).fillna(of["position_group"])

# Aggregate per player per season — mean composite score
of_agg = (
    of.groupby(["player_id", "player_name", "team_name", "position_group", "season"])
    ["composite_score"].mean().reset_index()
)
gk_agg = (
    gk.groupby(["player_id", "player_name", "team_name", "season"])
    ["composite_score"].mean().reset_index()
)
gk_agg["position_group"] = "goalkeeper"

POS_SCORE = {"forward": "attScore", "midfielder": "midScore",
             "defender": "defScore", "goalkeeper": "gkScore"}

players = []
seen = set()
for _, row in pd.concat([of_agg, gk_agg], ignore_index=True).iterrows():
    pid   = str(row["player_id"])
    seas  = str(row["season"])
    key   = (pid, seas)
    if key in seen:
        continue
    seen.add(key)
    pos = str(row["position_group"])
    score_key = POS_SCORE.get(pos)
    entry = {
        "id":       f"{pid}_{seas}",   # unique across seasons
        "name":     str(row["player_name"]),
        "team":     str(row["team_name"]),
        "position": pos,
        "season":   seas,
        "attScore": None, "midScore": None,
        "defScore": None, "gkScore":  None,
    }
    if score_key:
        entry[score_key] = safe_float(row["composite_score"])
    players.append(entry)

print(f"Players: {len(players)}")

# ── Metrics ───────────────────────────────────────────────────────────────────
metrics = [
    {"modelType": "RandomForest",        "accuracy": 0.5480, "f1": 0.5353, "rmse": None},
    {"modelType": "LogisticRegression",  "accuracy": 0.5560, "f1": 0.5494, "rmse": None},
]

# ── Write ─────────────────────────────────────────────────────────────────────
payload = {"matches": matches, "players": players, "metrics": metrics}
OUT_FILE.write_text(json.dumps(payload, indent=2, default=str))
print(f"Written to {OUT_FILE}")
