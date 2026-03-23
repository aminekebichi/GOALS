"""
tests/test_api.py

Integration tests for the FastAPI endpoints.

All file I/O is mocked — these tests validate API contracts (status codes,
response shape, field types) without requiring parquet data on disk.

Endpoints covered:
  GET /api/matches
  GET /api/matches/{match_id}/players
  GET /api/players
"""

from unittest.mock import patch

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from goals_app.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Shared mock data helpers
# ---------------------------------------------------------------------------

def _mock_outfield_df():
    return pd.DataFrame({
        "match_id":       [1, 1, 2, 2],
        "team_id":        [10, 20, 10, 20],
        "player_id":      [1, 2, 1, 2],
        "player_name":    ["Alice", "Bob", "Alice", "Bob"],
        "team_name":      ["TeamA", "TeamB", "TeamA", "TeamB"],
        "position_id":    [3.0, 2.0, 3.0, 2.0],
        "minutes_played": [90, 90, 90, 90],
        "goals":          [1.0, 0.0, 0.0, 1.0],
        "assists":        [0.0, 1.0, 0.0, 0.0],
        "expected_goals": [0.8, 0.1, 0.2, 0.7],
        "expected_assists": [0.1, 0.4, 0.0, 0.2],
        "dribbles_succeeded": [2.0, 1.0, 1.0, 3.0],
        "ShotsOnTarget":  [2.0, 0.0, 1.0, 2.0],
        "chances_created": [1.0, 2.0, 0.0, 1.0],
        "recoveries":     [3.0, 5.0, 4.0, 2.0],
        "accurate_passes": [30.0, 45.0, 28.0, 40.0],
        "matchstats.headers.tackles": [1.0, 3.0, 2.0, 4.0],
        "interceptions":  [0.0, 2.0, 1.0, 1.0],
        "aerials_won":    [1.0, 2.0, 0.0, 3.0],
        "clearances":     [0.0, 3.0, 1.0, 2.0],
        "shot_blocks":    [0.0, 1.0, 0.0, 1.0],
    })


def _mock_gk_df():
    return pd.DataFrame({
        "match_id":    [1, 1, 2, 2],
        "team_id":     [10, 20, 10, 20],
        "player_id":   [100, 101, 100, 101],
        "player_name": ["GK_A", "GK_B", "GK_A", "GK_B"],
        "team_name":   ["TeamA", "TeamB", "TeamA", "TeamB"],
        "minutes_played": [90, 90, 90, 90],
        "saves":       [3.0, 5.0, 2.0, 4.0],
        "expected_goals_on_target_faced": [1.2, 0.8, 0.5, 1.5],
        "keeper_diving_save": [1.0, 0.0, 0.0, 1.0],
        "saves_inside_box":   [2.0, 3.0, 2.0, 3.0],
        "keeper_high_claim":  [1.0, 0.0, 1.0, 2.0],
        "keeper_sweeper":     [0.0, 1.0, 0.0, 0.0],
    })


def _mock_fixtures_df():
    return pd.DataFrame({
        "match_id":   [1, 2],
        "home_id":    [10, 20],
        "away_id":    [20, 10],
        "home_team":  ["TeamA", "TeamB"],
        "away_team":  ["TeamB", "TeamA"],
        "match_date": ["2024-08-18", "2024-08-25"],
        "round":      [1, 2],
        "finished":   [True, True],
        "season":     ["2024_2025", "2024_2025"],
    })


# ---------------------------------------------------------------------------
# GET /api/matches
# ---------------------------------------------------------------------------

class TestGetMatches:
    def _patch_season(self):
        return patch(
            "goals_app.routers.calendar.load_season",
            return_value=(_mock_outfield_df(), _mock_gk_df(), _mock_fixtures_df()),
        )

    def _patch_predictions(self):
        return patch(
            "goals_app.routers.calendar.ml_service.predict_all_fixtures",
            return_value=[
                {"match_id": "1", "win_prob": 0.50, "draw_prob": 0.25, "loss_prob": 0.25},
                {"match_id": "2", "win_prob": 0.30, "draw_prob": 0.35, "loss_prob": 0.35},
            ],
        )

    def test_returns_200(self):
        with self._patch_season(), self._patch_predictions():
            response = client.get("/api/matches?season=2024_2025")
        assert response.status_code == 200

    def test_response_has_matches_key(self):
        with self._patch_season(), self._patch_predictions():
            response = client.get("/api/matches?season=2024_2025")
        assert "matches" in response.json()

    def test_matches_is_a_list(self):
        with self._patch_season(), self._patch_predictions():
            response = client.get("/api/matches?season=2024_2025")
        assert isinstance(response.json()["matches"], list)

    def test_match_has_required_fields(self):
        with self._patch_season(), self._patch_predictions():
            response = client.get("/api/matches?season=2024_2025")
        matches = response.json()["matches"]
        assert len(matches) > 0
        required = {"match_id", "match_date", "round", "home_team", "away_team", "finished"}
        for m in matches:
            missing = required - set(m.keys())
            assert not missing, f"Match missing fields: {missing}"

    def test_prediction_block_included_when_model_loaded(self):
        with self._patch_season(), self._patch_predictions():
            response = client.get("/api/matches?season=2024_2025")
        matches = response.json()["matches"]
        pred_matches = [m for m in matches if m.get("prediction") is not None]
        assert len(pred_matches) > 0

    def test_prediction_has_three_probability_keys(self):
        with self._patch_season(), self._patch_predictions():
            response = client.get("/api/matches?season=2024_2025")
        matches = response.json()["matches"]
        for m in matches:
            if m.get("prediction"):
                pred = m["prediction"]
                assert "win_prob" in pred
                assert "draw_prob" in pred
                assert "loss_prob" in pred

    def test_returns_empty_matches_when_no_data(self):
        with patch(
            "goals_app.routers.calendar.load_season",
            side_effect=FileNotFoundError,
        ), patch(
            "goals_app.routers.calendar.load_fixtures_only",
            side_effect=FileNotFoundError,
        ):
            response = client.get("/api/matches?season=9999_9999")
        assert response.status_code == 200
        assert response.json() == {"matches": []}

    def test_from_round_filter(self):
        with self._patch_season(), self._patch_predictions():
            response = client.get("/api/matches?season=2024_2025&from_round=2")
        matches = response.json()["matches"]
        for m in matches:
            if m["round"] is not None:
                assert m["round"] >= 2

    def test_to_round_filter(self):
        with self._patch_season(), self._patch_predictions():
            response = client.get("/api/matches?season=2024_2025&to_round=1")
        matches = response.json()["matches"]
        for m in matches:
            if m["round"] is not None:
                assert m["round"] <= 1

    def test_null_match_date_returns_none_not_crash(self):
        """calendar.py line 81: null match_date should return None, not throw."""
        fix = _mock_fixtures_df().copy()
        fix["match_date"] = None
        with (
            patch("goals_app.routers.calendar.load_season",
                  return_value=(_mock_outfield_df(), _mock_gk_df(), fix)),
            patch("goals_app.routers.calendar.ml_service.predict_all_fixtures",
                  return_value=[]),
        ):
            response = client.get("/api/matches?season=2024_2025")
        assert response.status_code == 200
        for m in response.json()["matches"]:
            assert m["match_date"] is None

    def test_file_not_found_from_predictions_still_returns_matches(self):
        """calendar.py lines 67-68: FileNotFoundError from predictions is silently swallowed."""
        with (
            patch("goals_app.routers.calendar.load_season",
                  return_value=(_mock_outfield_df(), _mock_gk_df(), _mock_fixtures_df())),
            patch("goals_app.routers.calendar.ml_service.predict_all_fixtures",
                  side_effect=FileNotFoundError("no model")),
        ):
            response = client.get("/api/matches?season=2024_2025")
        assert response.status_code == 200
        assert len(response.json()["matches"]) > 0

    def test_generic_exception_from_predictions_still_returns_matches(self):
        """calendar.py lines 69-70: any other exception is also swallowed gracefully."""
        with (
            patch("goals_app.routers.calendar.load_season",
                  return_value=(_mock_outfield_df(), _mock_gk_df(), _mock_fixtures_df())),
            patch("goals_app.routers.calendar.ml_service.predict_all_fixtures",
                  side_effect=RuntimeError("unexpected")),
        ):
            response = client.get("/api/matches?season=2024_2025")
        assert response.status_code == 200
        assert len(response.json()["matches"]) > 0

    # ------------------------------------------------------------------
    # TDD — RED: features that should exist but don't yet
    # ------------------------------------------------------------------

    def test_each_match_includes_season_field(self):
        """
        Each match object should carry the season it belongs to so the
        frontend can display / filter without a separate request.

        FIX: add  "season": season  to the match dict in calendar.py
             inside the  for _, row in fixtures.iterrows():  loop.
        """
        with self._patch_season(), self._patch_predictions():
            response = client.get("/api/matches?season=2024_2025")
        matches = response.json()["matches"]
        assert len(matches) > 0
        for m in matches:
            assert "season" in m, (
                "Match object is missing 'season' key — add it in calendar.py"
            )


# ---------------------------------------------------------------------------
# GET /api/matches/{match_id}/players
# ---------------------------------------------------------------------------

class TestGetMatchPlayers:
    def _patch_season(self):
        return patch(
            "goals_app.routers.calendar.load_season",
            return_value=(_mock_outfield_df(), _mock_gk_df(), _mock_fixtures_df()),
        )

    def test_returns_200_for_played_match(self):
        with self._patch_season():
            response = client.get("/api/matches/1/players?season=2024_2025")
        assert response.status_code == 200

    def test_response_has_players_and_motm(self):
        with self._patch_season():
            response = client.get("/api/matches/1/players?season=2024_2025")
        data = response.json()
        assert "players" in data
        assert "motm" in data

    def test_players_list_is_non_empty_for_played_match(self):
        with self._patch_season():
            response = client.get("/api/matches/1/players?season=2024_2025")
        players = response.json()["players"]
        assert len(players) > 0

    def test_player_has_required_fields(self):
        with self._patch_season():
            response = client.get("/api/matches/1/players?season=2024_2025")
        players = response.json()["players"]
        required = {"player_id", "player_name", "team_name", "position",
                    "composite_score", "minutes_played", "metric_contributions"}
        for p in players:
            missing = required - set(p.keys())
            assert not missing, f"Player missing fields: {missing}"

    def test_exactly_one_motm_flag(self):
        with self._patch_season():
            response = client.get("/api/matches/1/players?season=2024_2025")
        players = response.json()["players"]
        motm_count = sum(1 for p in players if p.get("is_motm"))
        assert motm_count == 1

    def test_motm_has_highest_composite_score(self):
        with self._patch_season():
            response = client.get("/api/matches/1/players?season=2024_2025")
        data = response.json()
        players = data["players"]
        motm_player = next(p for p in players if p["is_motm"])
        max_score = max(p["composite_score"] for p in players)
        assert motm_player["composite_score"] == max_score

    def test_returns_400_for_invalid_match_id(self):
        with self._patch_season():
            response = client.get("/api/matches/not-a-number/players?season=2024_2025")
        assert response.status_code == 400

    def test_returns_404_when_season_not_found(self):
        with patch(
            "goals_app.routers.calendar.load_season",
            side_effect=FileNotFoundError,
        ):
            response = client.get("/api/matches/1/players?season=9999_9999")
        assert response.status_code == 404

    def test_unplayed_match_returns_empty_players(self):
        with self._patch_season():
            # match_id 9999 doesn't exist in mock data
            response = client.get("/api/matches/9999/players?season=2024_2025")
        data = response.json()
        assert data["players"] == []
        assert data["motm"] is None


# ---------------------------------------------------------------------------
# GET /api/players
# ---------------------------------------------------------------------------

class TestGetPlayers:
    def _patch_season(self):
        return patch(
            "goals_app.routers.stats.load_season",
            return_value=(_mock_outfield_df(), _mock_gk_df(), _mock_fixtures_df()),
        )

    def test_returns_200(self):
        with self._patch_season():
            response = client.get("/api/players?season=2024_2025")
        assert response.status_code == 200

    def test_response_has_players_key(self):
        with self._patch_season():
            response = client.get("/api/players?season=2024_2025")
        assert "players" in response.json()

    def test_players_sorted_by_composite_score_descending(self):
        with self._patch_season():
            response = client.get("/api/players?season=2024_2025")
        scores = [p["composite_score"] for p in response.json()["players"]]
        assert scores == sorted(scores, reverse=True)

    def test_player_has_required_fields(self):
        with self._patch_season():
            response = client.get("/api/players?season=2024_2025")
        players = response.json()["players"]
        required = {"player_id", "player_name", "team_name", "position",
                    "composite_score", "matches_played", "metric_contributions"}
        for p in players:
            missing = required - set(p.keys())
            assert not missing, f"Player missing fields: {missing}"

    def test_position_filter_att(self):
        with self._patch_season():
            response = client.get("/api/players?season=2024_2025&position=ATT")
        players = response.json()["players"]
        for p in players:
            assert p["position"] == "ATT"

    def test_position_filter_gk(self):
        with self._patch_season():
            response = client.get("/api/players?season=2024_2025&position=GK")
        players = response.json()["players"]
        for p in players:
            assert p["position"] == "GK"

    def test_position_filter_case_insensitive(self):
        with self._patch_season():
            lower = client.get("/api/players?season=2024_2025&position=att")
            upper = client.get("/api/players?season=2024_2025&position=ATT")
        assert lower.json() == upper.json()

    def test_search_filter_by_player_name(self):
        with self._patch_season():
            response = client.get("/api/players?season=2024_2025&search=Alice")
        players = response.json()["players"]
        assert all("alice" in p["player_name"].lower() for p in players)

    def test_search_filter_by_team_name(self):
        with self._patch_season():
            response = client.get("/api/players?season=2024_2025&search=TeamA")
        players = response.json()["players"]
        assert all(
            "teama" in p["team_name"].lower() or "teama" in p["player_name"].lower()
            for p in players
        )

    def test_search_no_results_returns_empty_list(self):
        with self._patch_season():
            response = client.get("/api/players?season=2024_2025&search=zzznomatch999")
        assert response.json()["players"] == []

    def test_matches_played_is_positive_integer(self):
        with self._patch_season():
            response = client.get("/api/players?season=2024_2025")
        for p in response.json()["players"]:
            assert isinstance(p["matches_played"], int)
            assert p["matches_played"] > 0

    # ------------------------------------------------------------------
    # TDD — RED: features that should exist but don't yet
    # ------------------------------------------------------------------

    def test_player_has_per_match_average_field(self):
        """
        Each player object should include 'per_match_average' —
        composite_score / matches_played — so the frontend can rank
        players fairly regardless of how many games they appeared in.

        FIX: in stats.py, inside the  for _, row in all_players.iterrows():
             loop add:
               "per_match_average": round(
                   float(row["composite_score"]) / int(row["matches_played"]), 3
               )
        """
        with self._patch_season():
            response = client.get("/api/players?season=2024_2025")
        players = response.json()["players"]
        assert len(players) > 0
        for p in players:
            assert "per_match_average" in p, (
                "Player object is missing 'per_match_average' — add it in stats.py"
            )

    def test_per_match_average_equals_score_divided_by_matches(self):
        """per_match_average must equal composite_score / matches_played."""
        with self._patch_season():
            response = client.get("/api/players?season=2024_2025")
        for p in response.json()["players"]:
            expected = round(p["composite_score"] / p["matches_played"], 3)
            assert abs(p["per_match_average"] - expected) < 0.001, (
                f"per_match_average mismatch for {p['player_name']}: "
                f"got {p['per_match_average']}, expected {expected}"
            )
