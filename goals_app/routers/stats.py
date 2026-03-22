"""
GET /api/players

Returns player composite scores for a given season, filtered by position.
Includes per-metric contributions for the breakdown panel.
"""

from fastapi import APIRouter, Query
from typing import Optional
import pandas as pd

from goals_app.config import TEST_SEASON
from goals_app.services.feature_service import (
    load_season,
    compute_outfield_composite,
    compute_gk_composite,
    get_player_metric_contributions,
)

router = APIRouter()


@router.get("/players")
async def get_players(
    season: str = Query(default=TEST_SEASON),
    position: str = Query(default="all"),
    search: Optional[str] = Query(default=None),
):
    outfield_df, gk_df, _ = load_season(season)

    # Compute composite scores (fit scaler on the season data — for display only)
    outfield_scored, _ = compute_outfield_composite(outfield_df)
    gk_scored, _ = compute_gk_composite(gk_df)

    # Aggregate: sum scores per player across all matches they played
    outfield_agg = (
        outfield_scored.groupby(["player_id", "player_name", "team_name", "position_group"])
        .agg(
            composite_score=("composite_score", "sum"),
            matches_played=("match_id", "nunique"),
        )
        .reset_index()
    )

    gk_agg = (
        gk_scored.groupby(["player_id", "player_name", "team_name", "position_group"])
        .agg(
            composite_score=("composite_score", "sum"),
            matches_played=("match_id", "nunique"),
        )
        .reset_index()
    )

    all_players = pd.concat([outfield_agg, gk_agg], ignore_index=True)

    # Filter by position
    pos_upper = position.upper()
    if pos_upper != "ALL":
        all_players = all_players[all_players["position_group"] == pos_upper]

    # Search filter
    if search:
        mask = (
            all_players["player_name"].str.contains(search, case=False, na=False)
            | all_players["team_name"].str.contains(search, case=False, na=False)
        )
        all_players = all_players[mask]

    all_players = all_players.sort_values("composite_score", ascending=False).reset_index(drop=True)

    # Build per-player metric contributions using last match data
    # (use mean z-scores across all matches for the breakdown)
    outfield_scored_mean = (
        outfield_scored.groupby(["player_id"])[[c for c in outfield_scored.columns if c.endswith("_z")]]
        .mean()
        .reset_index()
    )
    gk_scored_mean = (
        gk_scored.groupby(["player_id"])[[c for c in gk_scored.columns if c.endswith("_z")]]
        .mean()
        .reset_index()
    )

    outfield_mean_map = outfield_scored_mean.set_index("player_id").to_dict(orient="index")
    gk_mean_map = gk_scored_mean.set_index("player_id").to_dict(orient="index")

    players = []
    for _, row in all_players.iterrows():
        pid = row["player_id"]
        pos = row["position_group"]

        if pos == "GK":
            z_row = gk_mean_map.get(pid, {})
        else:
            z_row = outfield_mean_map.get(pid, {})

        z_series = pd.Series(z_row)
        contributions = get_player_metric_contributions(z_series, pos)

        players.append({
            "player_id": str(pid),
            "player_name": row["player_name"],
            "team_name": row["team_name"],
            "position": pos,
            "composite_score": round(float(row["composite_score"]), 3),
            "matches_played": int(row["matches_played"]),
            "metric_contributions": contributions,
        })

    return {"players": players}
