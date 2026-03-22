"""
GET /api/matches

Returns La Liga fixtures for a given season with win/draw/loss predictions.
If model artifacts don't exist, prediction is null.
"""

from fastapi import APIRouter, Query
from typing import Optional
import pandas as pd

from goals_app.config import FOTMOB_DIR, TEST_SEASON
from goals_app.services.feature_service import load_season, derive_match_results
from goals_app.services import ml_service

router = APIRouter()


def _load_fixtures(season: str) -> pd.DataFrame:
    """Load fixtures with derived goals/results. Normalizes column types."""
    outfield, _, fixtures = load_season(season)
    fixtures_with_results = derive_match_results(outfield, fixtures)
    # Normalize types that parquet may store as strings
    fixtures_with_results["round"] = pd.to_numeric(fixtures_with_results["round"], errors="coerce")
    return fixtures_with_results


@router.get("/matches")
async def get_matches(
    season: str = Query(default=TEST_SEASON),
    from_round: Optional[int] = Query(default=None),
    to_round: Optional[int] = Query(default=None),
):
    fixtures = _load_fixtures(season)

    if from_round is not None:
        fixtures = fixtures[fixtures["round"] >= from_round]
    if to_round is not None:
        fixtures = fixtures[fixtures["round"] <= to_round]

    fixtures = fixtures.sort_values(["round", "match_date"]).reset_index(drop=True)

    # Try to load predictions
    predictions: dict[str, dict] = {}
    try:
        preds = ml_service.predict_season(season)
        for p in preds:
            predictions[p["match_id"]] = {
                "win_prob": p["win_prob"],
                "draw_prob": p["draw_prob"],
                "loss_prob": p["loss_prob"],
            }
    except FileNotFoundError:
        pass  # Model not trained yet — predictions stay null
    except Exception:
        pass

    matches = []
    for _, row in fixtures.iterrows():
        mid = str(row["match_id"])
        pred = predictions.get(mid)

        # Parse date
        match_date = row.get("match_date", None)
        if pd.notna(match_date):
            match_date = str(match_date)[:10]  # ISO date only
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
