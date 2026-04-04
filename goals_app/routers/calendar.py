"""
GET /api/matches          — fixture list with predictions
GET /api/matches/{id}/players — per-match player performances + MOTM
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional
import pandas as pd

from goals_app.config import TEST_SEASON, DEFAULT_LEAGUE_ID, LEAGUE_MAP
from goals_app.services.feature_service import (
    load_season,
    load_fixtures_only,
    derive_match_results,
    compute_outfield_composite,
    compute_gk_composite,
    get_player_metric_contributions,
    get_player_raw_stats,
)
from goals_app.services import ml_service

router = APIRouter()


def _load_fixtures(season: str, league_id: int = DEFAULT_LEAGUE_ID) -> pd.DataFrame:
    """
    Load fixtures for a season. Falls back to fixtures-only parquet when
    player data hasn't been scraped yet (e.g. future seasons).
    """
    try:
        outfield, _, fixtures = load_season(season, league_id)
        df = derive_match_results(outfield, fixtures)
    except FileNotFoundError:
        # Player parquets not available — use raw fixtures if present
        df = load_fixtures_only(season, league_id)

    df["round"] = pd.to_numeric(df["round"], errors="coerce")
    return df


@router.get("/matches")
async def get_matches(
    season: str = Query(default=TEST_SEASON),
    league_id: int = Query(default=DEFAULT_LEAGUE_ID),
    from_round: Optional[int] = Query(default=None),
    to_round: Optional[int] = Query(default=None),
):
    try:
        fixtures = _load_fixtures(season, league_id)
    except FileNotFoundError:
        return {"matches": []}

    if from_round is not None:
        fixtures = fixtures[fixtures["round"] >= from_round]
    if to_round is not None:
        fixtures = fixtures[fixtures["round"] <= to_round]

    fixtures = fixtures.sort_values(["round", "match_date"]).reset_index(drop=True)

    predictions: dict[str, dict] = {}
    try:
        preds = ml_service.predict_all_fixtures(season)
        for p in preds:
            predictions[p["match_id"]] = {
                "win_prob": p["win_prob"],
                "draw_prob": p["draw_prob"],
                "loss_prob": p["loss_prob"],
            }
    except FileNotFoundError:
        pass
    except Exception:
        pass

    matches = []
    for _, row in fixtures.iterrows():
        mid = str(row["match_id"])
        pred = predictions.get(mid)

        match_date = row.get("match_date", None)
        if pd.notna(match_date):
            match_date = str(match_date)[:10]
        else:
            match_date = None

        finished = bool(row.get("finished", False))
        home_goals = int(row["home_goals"]) if "home_goals" in row and pd.notna(row.get("home_goals")) else None
        away_goals = int(row["away_goals"]) if "away_goals" in row and pd.notna(row.get("away_goals")) else None

        matches.append({
            "match_id": mid,
            "match_date": match_date,
            "season": season,
            "round": int(row["round"]) if pd.notna(row.get("round")) else None,
            "home_team": row.get("home_team"),
            "away_team": row.get("away_team"),
            "finished": finished,
            "home_score": home_goals if finished else None,
            "away_score": away_goals if finished else None,
            "prediction": pred,
        })

    return {"matches": matches}


@router.get("/matches/{match_id}/players")
async def get_match_players(
    match_id: str,
    season: str = Query(default=TEST_SEASON),
    league_id: int = Query(default=DEFAULT_LEAGUE_ID),
):
    try:
        outfield_df, gk_df, _ = load_season(season, league_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Season {season} not found")

    # Fit scaler on full season so z-scores are season-relative
    outfield_scored, _ = compute_outfield_composite(outfield_df)
    gk_scored, _ = compute_gk_composite(gk_df)

    try:
        mid_int = int(match_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid match_id")

    match_out = outfield_scored[outfield_scored["match_id"] == mid_int]
    match_gk = gk_scored[gk_scored["match_id"] == mid_int]

    if match_out.empty and match_gk.empty:
        # Unplayed match — no player data yet
        return {"match_id": match_id, "players": [], "motm": None}

    players = []

    for _, row in match_out.iterrows():
        pos = str(row.get("position_group", "MID"))
        players.append({
            "player_id": str(row.get("player_id", "")),
            "player_name": str(row.get("player_name", "")),
            "team_name": str(row.get("team_name", "")),
            "position": pos,
            "composite_score": round(float(row.get("composite_score", 0)), 3),
            "minutes_played": int(row.get("minutes_played", 0) or 0),
            "metric_contributions": get_player_metric_contributions(row, pos),
            "raw_stats": get_player_raw_stats(row, pos),
        })

    for _, row in match_gk.iterrows():
        players.append({
            "player_id": str(row.get("player_id", "")),
            "player_name": str(row.get("player_name", "")),
            "team_name": str(row.get("team_name", "")),
            "position": "GK",
            "composite_score": round(float(row.get("composite_score", 0)), 3),
            "minutes_played": int(row.get("minutes_played", 0) or 0),
            "metric_contributions": get_player_metric_contributions(row, "GK"),
            "raw_stats": get_player_raw_stats(row, "GK"),
        })

    if not players:
        return {"match_id": match_id, "players": [], "motm": None}

    motm = max(players, key=lambda p: p["composite_score"])
    motm_id = motm["player_id"]
    for p in players:
        p["is_motm"] = p["player_id"] == motm_id

    return {"match_id": match_id, "players": players, "motm": motm}


@router.get("/teams/form")
async def get_team_form(
    team_name: str = Query(..., description="Exact or partial team name to look up"),
    season: str = Query(default=TEST_SEASON),
    league_id: int = Query(default=DEFAULT_LEAGUE_ID),
    last_n: int = Query(default=5, ge=1, le=38),
):
    """
    Return last N match results (W/D/L) for a given team, from the home team's perspective.
    Useful for displaying a form guide strip in the UI.
    """
    try:
        fixtures = _load_fixtures(season, league_id)
    except FileNotFoundError:
        return {"team_name": team_name, "season": season, "form": []}

    # Match both home and away appearances case-insensitively
    team_lower = team_name.lower()
    home_mask = fixtures["home_team"].str.lower().str.contains(team_lower, na=False)
    away_mask = fixtures["away_team"].str.lower().str.contains(team_lower, na=False)
    team_fixtures = fixtures[home_mask | away_mask].copy()

    # Keep only finished matches that have result data
    if "result" in team_fixtures.columns:
        team_fixtures = team_fixtures[team_fixtures["result"].notna()]
    elif "home_goals" in team_fixtures.columns:
        team_fixtures = team_fixtures[team_fixtures["home_goals"].notna()]
    else:
        return {"team_name": team_name, "season": season, "form": []}

    team_fixtures = team_fixtures.sort_values(["round", "match_date"]).tail(last_n)

    form = []
    for _, row in team_fixtures.iterrows():
        is_home = str(row.get("home_team", "")).lower().find(team_lower) >= 0

        if "result" in row and pd.notna(row["result"]):
            home_result = row["result"]  # W/D/L from home perspective
        else:
            hg = row.get("home_goals", 0) or 0
            ag = row.get("away_goals", 0) or 0
            if hg > ag:
                home_result = "W"
            elif hg < ag:
                home_result = "L"
            else:
                home_result = "D"

        # Flip result if team was playing away
        if not is_home:
            home_result = {"W": "L", "L": "W", "D": "D"}[home_result]

        match_date = row.get("match_date", None)
        if pd.notna(match_date):
            match_date = str(match_date)[:10]

        form.append({
            "match_id": str(row.get("match_id", "")),
            "match_date": match_date,
            "round": int(row["round"]) if pd.notna(row.get("round")) else None,
            "home_team": row.get("home_team"),
            "away_team": row.get("away_team"),
            "home_score": int(row["home_goals"]) if "home_goals" in row and pd.notna(row.get("home_goals")) else None,
            "away_score": int(row["away_goals"]) if "away_goals" in row and pd.notna(row.get("away_goals")) else None,
            "result": home_result,  # W/D/L from the requested team's perspective
        })

    resolved_name = (
        team_fixtures.iloc[0]["home_team"]
        if not team_fixtures.empty and str(team_fixtures.iloc[0].get("home_team", "")).lower().find(team_lower) >= 0
        else team_fixtures.iloc[0]["away_team"] if not team_fixtures.empty else team_name
    )

    return {"team_name": resolved_name, "season": season, "form": form}
