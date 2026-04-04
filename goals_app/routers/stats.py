"""
GET /api/players

Returns player composite scores for a given season, filtered by position.
Includes per-metric contributions for the breakdown panel.
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional
import pandas as pd

from goals_app.config import TEST_SEASON
from goals_app.services.feature_service import (
    load_season,
    compute_outfield_composite,
    compute_gk_composite,
    get_player_metric_contributions,
    get_player_raw_stats,
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

        matches_played = int(row["matches_played"])
        composite_score = round(float(row["composite_score"]), 3)
        players.append({
            "player_id": str(pid),
            "player_name": row["player_name"],
            "team_name": row["team_name"],
            "position": pos,
            "composite_score": composite_score,
            "matches_played": matches_played,
            "per_match_average": round(composite_score / matches_played, 3),
            "metric_contributions": contributions,
        })

    return {"players": players}


@router.get("/players/{player_id}/radar")
async def get_player_radar(
    player_id: str,
    season: str = Query(default=TEST_SEASON),
):
    """
    Return season-averaged metric contributions for a player, suitable for a radar chart.
    Contributions are weighted z-scores (same values shown in the breakdown panel but
    averaged across all matches in the season).
    """
    try:
        outfield_df, gk_df, _ = load_season(season)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Season {season} not found")

    outfield_scored, _ = compute_outfield_composite(outfield_df)
    gk_scored, _ = compute_gk_composite(gk_df)

    # Determine which df contains this player
    def _find_player(df: pd.DataFrame) -> Optional[pd.Series]:
        match = df[df["player_id"].astype(str) == player_id]
        if match.empty:
            return None
        z_cols = [c for c in match.columns if c.endswith("_z")]
        return match[z_cols + ["player_name", "team_name", "position_group"]].mean(numeric_only=True), match.iloc[0]

    result = _find_player(outfield_scored)
    is_gk = False
    if result is None:
        gk_match = gk_scored[gk_scored["player_id"].astype(str) == player_id]
        if gk_match.empty:
            raise HTTPException(status_code=404, detail=f"Player {player_id} not found in season {season}")
        z_cols = [c for c in gk_match.columns if c.endswith("_z")]
        mean_z = gk_match[z_cols].mean()
        sample_row = gk_match.iloc[0]
        position = "GK"
        is_gk = True
    else:
        mean_z, sample_row = result
        position = str(sample_row.get("position_group", "MID"))

    contributions = get_player_metric_contributions(mean_z, position)

    return {
        "player_id": player_id,
        "player_name": str(sample_row.get("player_name", "")),
        "team_name": str(sample_row.get("team_name", "")),
        "position": position,
        "season": season,
        "radar": contributions,
    }
