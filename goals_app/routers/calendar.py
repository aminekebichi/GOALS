"""
GET /api/matches          — fixture list with predictions
GET /api/matches/{id}/players — per-match player performances + MOTM
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional
import pandas as pd

from goals_app.config import TEST_SEASON
from goals_app.services.feature_service import (
    load_season,
    load_fixtures_only,
    derive_match_results,
    compute_outfield_composite,
    compute_gk_composite,
    get_player_metric_contributions,
)
from goals_app.services import ml_service

router = APIRouter()


def _load_fixtures(season: str) -> pd.DataFrame:
    """
    Load fixtures for a season. Falls back to fixtures-only parquet when
    player data hasn't been scraped yet (e.g. future seasons).
    """
    try:
        outfield, _, fixtures = load_season(season)
        df = derive_match_results(outfield, fixtures)
    except FileNotFoundError:
        # Player parquets not available — use raw fixtures if present
        df = load_fixtures_only(season)

    df["round"] = pd.to_numeric(df["round"], errors="coerce")
    return df


@router.get("/matches")
async def get_matches(
    season: str = Query(default=TEST_SEASON),
    from_round: Optional[int] = Query(default=None),
    to_round: Optional[int] = Query(default=None),
):
    try:
        fixtures = _load_fixtures(season)
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
):
    try:
        outfield_df, gk_df, _ = load_season(season)
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
        })

    if not players:
        return {"match_id": match_id, "players": [], "motm": None}

    motm = max(players, key=lambda p: p["composite_score"])
    motm_id = motm["player_id"]
    for p in players:
        p["is_motm"] = p["player_id"] == motm_id

    return {"match_id": match_id, "players": players, "motm": motm}
