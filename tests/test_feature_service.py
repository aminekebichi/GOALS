"""
tests/test_feature_service.py

Unit tests for goals_app/services/feature_service.py.

All tests use in-memory DataFrames — no parquet files required.
Topics covered:
  - Composite weight integrity (weights sum to 1.0)
  - Safe column accessor (_col)
  - Feature builder columns (_build_outfield_features, _build_gk_features)
  - Z-score scaler fit/transform
  - Outfield & GK composite score computation
  - Position group assignment
  - Scaler reuse (train → test, no refit)
  - Match result derivation (W / D / L)
  - Team-level aggregation (home_att, away_def, …)
  - load_multiple_seasons raises on empty season list
  - get_player_metric_contributions returns all expected keys
"""

import numpy as np
import pandas as pd
import pytest
from sklearn.preprocessing import StandardScaler
from unittest.mock import patch

from goals_app.services.feature_service import (
    ATT_WEIGHTS,
    DEF_WEIGHTS,
    GK_WEIGHTS,
    MID_WEIGHTS,
    _build_gk_features,
    _build_outfield_features,
    _col,
    _zscore_fit,
    _zscore_transform,
    aggregate_to_team,
    build_season_data,
    compute_gk_composite,
    compute_outfield_composite,
    derive_match_results,
    get_player_metric_contributions,
    load_fixtures_only,
    load_multiple_seasons,
    load_season,
)


# ---------------------------------------------------------------------------
# Weight integrity
# ---------------------------------------------------------------------------

class TestWeightSums:
    """Weights for each position must sum to 1.0 — otherwise the composite
    score scale drifts and cross-position comparisons are meaningless."""

    def test_att_weights_sum_to_one(self):
        assert abs(sum(ATT_WEIGHTS.values()) - 1.0) < 1e-9

    def test_mid_weights_sum_to_one(self):
        assert abs(sum(MID_WEIGHTS.values()) - 1.0) < 1e-9

    def test_def_weights_sum_to_one(self):
        assert abs(sum(DEF_WEIGHTS.values()) - 1.0) < 1e-9

    def test_gk_weights_sum_to_one(self):
        assert abs(sum(GK_WEIGHTS.values()) - 1.0) < 1e-9

    def test_all_weights_are_positive(self):
        for role, weights in [
            ("ATT", ATT_WEIGHTS),
            ("MID", MID_WEIGHTS),
            ("DEF", DEF_WEIGHTS),
            ("GK",  GK_WEIGHTS),
        ]:
            for metric, w in weights.items():
                assert w > 0, f"{role}.{metric} weight must be positive, got {w}"


# ---------------------------------------------------------------------------
# _col — safe column accessor
# ---------------------------------------------------------------------------

class TestColAccessor:
    def test_returns_column_values_when_present(self):
        df = pd.DataFrame({"goals": [1.0, 2.0, 3.0]})
        result = _col(df, "goals")
        pd.testing.assert_series_equal(result, df["goals"].fillna(0))

    def test_returns_zeros_when_column_missing(self):
        df = pd.DataFrame({"other": [1, 2, 3]})
        result = _col(df, "nonexistent_col")
        assert (result == 0).all()
        assert len(result) == 3

    def test_fills_nan_with_zero(self):
        df = pd.DataFrame({"x": [1.0, float("nan"), 3.0]})
        result = _col(df, "x")
        assert result[1] == 0.0

    def test_returns_series_with_correct_index(self):
        df = pd.DataFrame({"a": [10, 20]}, index=[5, 6])
        result = _col(df, "nonexistent")
        assert list(result.index) == [5, 6]


# ---------------------------------------------------------------------------
# _build_outfield_features
# ---------------------------------------------------------------------------

class TestBuildOutfieldFeatures:
    EXPECTED_COLS = [
        "_goals_assists", "_xg", "_xa", "_dribbles", "_shots",
        "_chances_created", "_recoveries", "_prog_pass", "_tackles",
        "_interceptions", "_aerials_won", "_clearances", "_shot_blocks",
    ]

    def test_adds_all_derived_columns(self, outfield_df):
        result = _build_outfield_features(outfield_df)
        for col in self.EXPECTED_COLS:
            assert col in result.columns, f"Missing derived column: {col}"

    def test_goals_assists_is_sum(self, outfield_df):
        result = _build_outfield_features(outfield_df)
        expected = outfield_df["goals"].fillna(0) + outfield_df["assists"].fillna(0)
        pd.testing.assert_series_equal(result["_goals_assists"], expected, check_names=False)

    def test_does_not_mutate_input(self, outfield_df):
        original_cols = set(outfield_df.columns)
        _build_outfield_features(outfield_df)
        assert set(outfield_df.columns) == original_cols

    def test_handles_missing_optional_columns(self):
        """Only match_id and position_id are truly required; everything else is optional."""
        minimal = pd.DataFrame({
            "match_id": [1, 2],
            "position_id": [2.0, 3.0],
        })
        result = _build_outfield_features(minimal)
        # All derived cols default to zero when source cols are absent
        for col in self.EXPECTED_COLS:
            assert col in result.columns
            assert (result[col] == 0).all(), f"{col} should be 0 when source missing"


# ---------------------------------------------------------------------------
# _build_gk_features
# ---------------------------------------------------------------------------

class TestBuildGKFeatures:
    EXPECTED_COLS = [
        "_saves", "_xgot_faced", "_diving_saves",
        "_saves_inside_box", "_high_claims", "_sweeper_actions",
    ]

    def test_adds_all_derived_columns(self, gk_df):
        result = _build_gk_features(gk_df)
        for col in self.EXPECTED_COLS:
            assert col in result.columns, f"Missing GK derived column: {col}"

    def test_saves_mapped_correctly(self, gk_df):
        result = _build_gk_features(gk_df)
        pd.testing.assert_series_equal(
            result["_saves"], gk_df["saves"].fillna(0), check_names=False
        )

    def test_does_not_mutate_input(self, gk_df):
        original_cols = set(gk_df.columns)
        _build_gk_features(gk_df)
        assert set(gk_df.columns) == original_cols


# ---------------------------------------------------------------------------
# Z-score fit / transform
# ---------------------------------------------------------------------------

class TestZScore:
    def test_fit_returns_standard_scaler(self, outfield_df):
        df = _build_outfield_features(outfield_df)
        scaler = _zscore_fit(df, ["_goals_assists", "_xg"])
        assert isinstance(scaler, StandardScaler)

    def test_transform_adds_z_columns(self, outfield_df):
        df = _build_outfield_features(outfield_df)
        cols = ["_goals_assists", "_xg"]
        scaler = _zscore_fit(df, cols)
        df_z = _zscore_transform(df, cols, scaler)
        assert "_goals_assists_z" in df_z.columns
        assert "_xg_z" in df_z.columns

    def test_z_scores_have_approx_zero_mean(self, outfield_df):
        df = _build_outfield_features(outfield_df)
        cols = ["_goals_assists", "_xg"]
        scaler = _zscore_fit(df, cols)
        df_z = _zscore_transform(df, cols, scaler)
        assert abs(df_z["_goals_assists_z"].mean()) < 1e-9

    def test_transform_does_not_refit(self, outfield_df):
        """Applying a pre-fitted scaler to a single row should not crash."""
        df = _build_outfield_features(outfield_df)
        cols = ["_goals_assists", "_xg"]
        scaler = _zscore_fit(df, cols)
        single_row = df.iloc[[0]].copy()
        result = _zscore_transform(single_row, cols, scaler)
        assert "_goals_assists_z" in result.columns


# ---------------------------------------------------------------------------
# compute_outfield_composite
# ---------------------------------------------------------------------------

class TestComputeOutfieldComposite:
    def test_returns_composite_score_column(self, outfield_df):
        result, _ = compute_outfield_composite(outfield_df)
        assert "composite_score" in result.columns

    def test_returns_fitted_scaler(self, outfield_df):
        _, scaler = compute_outfield_composite(outfield_df)
        assert isinstance(scaler, StandardScaler)

    def test_composite_score_finite(self, outfield_df):
        result, _ = compute_outfield_composite(outfield_df)
        assert result["composite_score"].notna().all()
        assert np.isfinite(result["composite_score"]).all()

    def test_position_group_assigned(self, outfield_df):
        result, _ = compute_outfield_composite(outfield_df)
        assert "position_group" in result.columns
        valid_groups = {"ATT", "MID", "DEF"}
        assert set(result["position_group"].unique()).issubset(valid_groups)

    def test_def_players_get_def_group(self, outfield_df):
        result, _ = compute_outfield_composite(outfield_df)
        def_rows = result[result["position_id"] == 1.0]
        assert (def_rows["position_group"] == "DEF").all()

    def test_mid_players_get_mid_group(self, outfield_df):
        result, _ = compute_outfield_composite(outfield_df)
        mid_rows = result[result["position_id"] == 2.0]
        assert (mid_rows["position_group"] == "MID").all()

    def test_att_players_get_att_group(self, outfield_df):
        result, _ = compute_outfield_composite(outfield_df)
        att_rows = result[result["position_id"] == 3.0]
        assert (att_rows["position_group"] == "ATT").all()

    def test_unknown_position_defaults_to_mid(self):
        df = pd.DataFrame({
            "match_id": [1], "team_id": [10], "player_id": [99],
            "player_name": ["?"], "team_name": ["X"],
            "position_id": [99.0],  # unknown
            "minutes_played": [90],
        })
        result, _ = compute_outfield_composite(df)
        assert result["position_group"].iloc[0] == "MID"

    def test_reuses_provided_scaler(self, outfield_df):
        """When a scaler is passed in, no refitting should occur."""
        _, scaler_train = compute_outfield_composite(outfield_df)
        # Slightly different data — if refitting occurred, means_ would change
        test_df = outfield_df.copy()
        test_df["goals"] = test_df["goals"] * 100
        result, returned_scaler = compute_outfield_composite(test_df, scaler=scaler_train)
        # Should return the same scaler object (not a new one)
        assert returned_scaler is scaler_train


# ---------------------------------------------------------------------------
# compute_gk_composite
# ---------------------------------------------------------------------------

class TestComputeGKComposite:
    def test_returns_composite_score_column(self, gk_df):
        result, _ = compute_gk_composite(gk_df)
        assert "composite_score" in result.columns

    def test_position_group_is_gk(self, gk_df):
        result, _ = compute_gk_composite(gk_df)
        assert (result["position_group"] == "GK").all()

    def test_composite_score_finite(self, gk_df):
        result, _ = compute_gk_composite(gk_df)
        assert np.isfinite(result["composite_score"]).all()

    def test_returns_fitted_scaler(self, gk_df):
        _, scaler = compute_gk_composite(gk_df)
        assert isinstance(scaler, StandardScaler)


# ---------------------------------------------------------------------------
# derive_match_results
# ---------------------------------------------------------------------------

class TestDeriveMatchResults:
    def test_home_win_detected(self, goals_outfield_df, goals_fixtures_df):
        """Match 1: TeamA(home)=2 goals, TeamB(away)=1 goal → W"""
        result = derive_match_results(goals_outfield_df, goals_fixtures_df)
        match1 = result[result["match_id"] == 1].iloc[0]
        assert match1["result"] == "W"

    def test_draw_detected(self, goals_outfield_df, goals_fixtures_df):
        """Match 2: TeamA(away)=1 goal, TeamB(home)=1 goal → D"""
        result = derive_match_results(goals_outfield_df, goals_fixtures_df)
        match2 = result[result["match_id"] == 2].iloc[0]
        assert match2["result"] == "D"

    def test_away_win_detected(self):
        """Away team scores more → L (from home perspective)."""
        outfield = pd.DataFrame({
            "match_id": [1, 1],
            "team_id":  [10, 20],
            "goals":    [0.0, 2.0],
        })
        fixtures = pd.DataFrame({
            "match_id": [1],
            "home_id":  [10],
            "away_id":  [20],
        })
        result = derive_match_results(outfield, fixtures)
        assert result.iloc[0]["result"] == "L"

    def test_home_goals_column_added(self, goals_outfield_df, goals_fixtures_df):
        result = derive_match_results(goals_outfield_df, goals_fixtures_df)
        assert "home_goals" in result.columns
        assert "away_goals" in result.columns

    def test_goals_values_correct(self, goals_outfield_df, goals_fixtures_df):
        result = derive_match_results(goals_outfield_df, goals_fixtures_df)
        match1 = result[result["match_id"] == 1].iloc[0]
        assert match1["home_goals"] == 2
        assert match1["away_goals"] == 1

    def test_result_only_contains_valid_labels(self, goals_outfield_df, goals_fixtures_df):
        result = derive_match_results(goals_outfield_df, goals_fixtures_df)
        assert set(result["result"].unique()).issubset({"W", "D", "L"})


# ---------------------------------------------------------------------------
# aggregate_to_team
# ---------------------------------------------------------------------------

class TestAggregateToTeam:
    EXPECTED_FEATURE_COLS = [
        "home_att", "home_mid", "home_def", "home_gk",
        "away_att", "away_mid", "away_def", "away_gk",
    ]

    def _make_player_scores(self, outfield_df, gk_df):
        """Helper: compute composite scores and combine outfield + GK."""
        out_scored, _ = compute_outfield_composite(outfield_df)
        gk_scored, _ = compute_gk_composite(gk_df)
        cols = ["match_id", "team_id", "position_group", "composite_score"]
        for c in cols:
            if c not in out_scored.columns:
                out_scored[c] = None
            if c not in gk_scored.columns:
                gk_scored[c] = None
        return pd.concat([out_scored[cols], gk_scored[cols]], ignore_index=True)

    def test_returns_all_feature_columns(self, outfield_df, gk_df, fixtures_df):
        player_scores = self._make_player_scores(outfield_df, gk_df)
        fixtures_with_results = derive_match_results(outfield_df, fixtures_df)
        result = aggregate_to_team(player_scores, fixtures_with_results)
        for col in self.EXPECTED_FEATURE_COLS:
            assert col in result.columns, f"Missing column: {col}"

    def test_one_row_per_match(self, outfield_df, gk_df, fixtures_df):
        player_scores = self._make_player_scores(outfield_df, gk_df)
        fixtures_with_results = derive_match_results(outfield_df, fixtures_df)
        result = aggregate_to_team(player_scores, fixtures_with_results)
        assert len(result) == fixtures_df["match_id"].nunique()

    def test_feature_values_are_numeric(self, outfield_df, gk_df, fixtures_df):
        player_scores = self._make_player_scores(outfield_df, gk_df)
        fixtures_with_results = derive_match_results(outfield_df, fixtures_df)
        result = aggregate_to_team(player_scores, fixtures_with_results)
        for col in self.EXPECTED_FEATURE_COLS:
            assert pd.api.types.is_numeric_dtype(result[col]), f"{col} not numeric"

    def test_result_column_preserved(self, outfield_df, gk_df, fixtures_df):
        player_scores = self._make_player_scores(outfield_df, gk_df)
        fixtures_with_results = derive_match_results(outfield_df, fixtures_df)
        result = aggregate_to_team(player_scores, fixtures_with_results)
        assert "result" in result.columns


# ---------------------------------------------------------------------------
# load_multiple_seasons — error handling
# ---------------------------------------------------------------------------

class TestLoadMultipleSeasons:
    def test_raises_value_error_when_no_seasons_found(self):
        """If none of the seasons exist on disk, raise ValueError not a silent empty."""
        with pytest.raises(ValueError, match="No seasons found"):
            load_multiple_seasons(["9999_9999", "8888_8888"])


# ---------------------------------------------------------------------------
# get_player_metric_contributions
# ---------------------------------------------------------------------------

class TestGetPlayerMetricContributions:
    def _zero_row(self):
        """A Series with all _*_z columns set to 0."""
        cols = [
            "_goals_assists_z", "_xg_z", "_xa_z", "_dribbles_z", "_shots_z",
            "_chances_created_z", "_recoveries_z", "_prog_pass_z", "_tackles_z",
            "_interceptions_z", "_aerials_won_z", "_clearances_z", "_shot_blocks_z",
            "_saves_z", "_xgot_faced_z", "_diving_saves_z", "_saves_inside_box_z",
            "_high_claims_z", "_sweeper_actions_z",
        ]
        return pd.Series({c: 0.0 for c in cols})

    def test_att_returns_expected_keys(self):
        result = get_player_metric_contributions(self._zero_row(), "ATT")
        assert set(result.keys()) == set(ATT_WEIGHTS.keys())

    def test_mid_returns_expected_keys(self):
        result = get_player_metric_contributions(self._zero_row(), "MID")
        assert set(result.keys()) == set(MID_WEIGHTS.keys())

    def test_def_returns_expected_keys(self):
        result = get_player_metric_contributions(self._zero_row(), "DEF")
        assert set(result.keys()) == set(DEF_WEIGHTS.keys())

    def test_gk_returns_expected_keys(self):
        result = get_player_metric_contributions(self._zero_row(), "GK")
        assert set(result.keys()) == set(GK_WEIGHTS.keys())

    def test_all_zero_input_gives_zero_contributions(self):
        for pos in ["ATT", "MID", "DEF", "GK"]:
            result = get_player_metric_contributions(self._zero_row(), pos)
            assert all(v == 0.0 for v in result.values()), \
                f"Position {pos}: expected all zeros, got {result}"

    def test_unknown_position_returns_empty_dict(self):
        result = get_player_metric_contributions(self._zero_row(), "UNKNOWN")
        assert result == {}

    def test_contributions_are_rounded_to_three_decimal_places(self):
        row = self._zero_row()
        row["_goals_assists_z"] = 1.123456789
        result = get_player_metric_contributions(row, "ATT")
        # All values should have at most 3 decimal places
        for k, v in result.items():
            assert round(v, 3) == v, f"Key {k} value {v} not rounded to 3dp"


# ---------------------------------------------------------------------------
# aggregate_to_team — missing position group fallback (line 355)
# ---------------------------------------------------------------------------

class TestAggregateToTeamMissingPosition:
    def test_missing_position_groups_filled_with_zero(self):
        """If no GK/MID/DEF players appear in the data, those columns must be 0."""
        player_scores = pd.DataFrame({
            "match_id":        [1, 1, 2, 2],
            "team_id":         [10, 20, 10, 20],
            "position_group":  ["ATT", "ATT", "ATT", "ATT"],  # only ATT
            "composite_score": [1.0, 0.8, 0.9, 0.7],
        })
        fixtures_with_results = pd.DataFrame({
            "match_id": [1, 2],
            "home_id":  [10, 20],
            "away_id":  [20, 10],
            "result":   ["W", "D"],
        })
        result = aggregate_to_team(player_scores, fixtures_with_results)

        for col in ["home_gk", "home_mid", "home_def", "away_gk", "away_mid", "away_def"]:
            assert col in result.columns, f"Missing column: {col}"
            assert (result[col] == 0).all(), f"{col} should be 0 when position absent"


# ---------------------------------------------------------------------------
# load_season (I/O functions — mocked parquet reads)
# ---------------------------------------------------------------------------

class TestLoadSeason:
    def test_returns_three_dataframes(self, outfield_df, gk_df, fixtures_df):
        with patch(
            "goals_app.services.feature_service.pd.read_parquet",
            side_effect=[outfield_df, gk_df, fixtures_df],
        ):
            out, gk, fix = load_season("2024_2025")
        assert isinstance(out, pd.DataFrame)
        assert isinstance(gk, pd.DataFrame)
        assert isinstance(fix, pd.DataFrame)

    def test_outfield_has_correct_row_count(self, outfield_df, gk_df, fixtures_df):
        with patch(
            "goals_app.services.feature_service.pd.read_parquet",
            side_effect=[outfield_df, gk_df, fixtures_df],
        ):
            out, _, _ = load_season("2024_2025")
        assert len(out) == len(outfield_df)

    def test_raises_file_not_found_for_missing_parquet(self):
        with patch(
            "goals_app.services.feature_service.pd.read_parquet",
            side_effect=FileNotFoundError("no file"),
        ):
            with pytest.raises(FileNotFoundError):
                load_season("9999_9999")


# ---------------------------------------------------------------------------
# load_fixtures_only
# ---------------------------------------------------------------------------

class TestLoadFixturesOnly:
    def test_returns_dataframe_when_file_exists(self, fixtures_df, tmp_path):
        season_dir = tmp_path / "2024_2025" / "output"
        season_dir.mkdir(parents=True)
        fixtures_path = season_dir / "fixtures.parquet"
        fixtures_df.to_parquet(fixtures_path, index=False)

        with patch("goals_app.services.feature_service.FOTMOB_DIR", tmp_path):
            result = load_fixtures_only("2024_2025")

        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(fixtures_df)

    def test_has_same_columns_as_saved(self, fixtures_df, tmp_path):
        season_dir = tmp_path / "2024_2025" / "output"
        season_dir.mkdir(parents=True)
        fixtures_df.to_parquet(season_dir / "fixtures.parquet", index=False)

        with patch("goals_app.services.feature_service.FOTMOB_DIR", tmp_path):
            result = load_fixtures_only("2024_2025")

        assert set(result.columns) == set(fixtures_df.columns)

    def test_raises_file_not_found_when_missing(self, tmp_path):
        with patch("goals_app.services.feature_service.FOTMOB_DIR", tmp_path):
            with pytest.raises(FileNotFoundError, match="No fixtures found"):
                load_fixtures_only("9999_9999")


# ---------------------------------------------------------------------------
# load_multiple_seasons — success paths (mocked)
# ---------------------------------------------------------------------------

class TestLoadMultipleSeasonsMocked:
    def test_concatenates_two_seasons(self, outfield_df, gk_df, fixtures_df):
        with patch(
            "goals_app.services.feature_service.load_season",
            return_value=(outfield_df.copy(), gk_df.copy(), fixtures_df.copy()),
        ):
            out, gk, fix = load_multiple_seasons(["2022_2023", "2023_2024"])
        assert len(out) == 2 * len(outfield_df)
        assert len(gk) == 2 * len(gk_df)
        assert len(fix) == 2 * len(fixtures_df)

    def test_season_column_added_to_all_frames(self, outfield_df, gk_df, fixtures_df):
        with patch(
            "goals_app.services.feature_service.load_season",
            return_value=(outfield_df.copy(), gk_df.copy(), fixtures_df.copy()),
        ):
            out, gk, fix = load_multiple_seasons(["2022_2023"])
        assert "season" in out.columns
        assert "season" in gk.columns
        assert "season" in fix.columns

    def test_season_column_value_is_season_string(self, outfield_df, gk_df, fixtures_df):
        with patch(
            "goals_app.services.feature_service.load_season",
            return_value=(outfield_df.copy(), gk_df.copy(), fixtures_df.copy()),
        ):
            out, _, _ = load_multiple_seasons(["2024_2025"])
        assert (out["season"] == "2024_2025").all()

    def test_skips_missing_season_silently(self, outfield_df, gk_df, fixtures_df):
        """One bad season should not crash — only the good one is returned."""
        def mock_load(season):
            if season == "9999_9999":
                raise FileNotFoundError
            return (outfield_df.copy(), gk_df.copy(), fixtures_df.copy())

        with patch("goals_app.services.feature_service.load_season", side_effect=mock_load):
            out, _, _ = load_multiple_seasons(["9999_9999", "2024_2025"])
        assert len(out) == len(outfield_df)

    def test_raises_value_error_when_all_seasons_missing(self):
        with patch(
            "goals_app.services.feature_service.load_season",
            side_effect=FileNotFoundError,
        ):
            with pytest.raises(ValueError, match="No seasons found"):
                load_multiple_seasons(["9999_9999", "8888_8888"])


# ---------------------------------------------------------------------------
# build_season_data (high-level pipeline helper)
# ---------------------------------------------------------------------------

class TestBuildSeasonData:
    def _mock_load(self, outfield_df, gk_df, fixtures_df):
        return patch(
            "goals_app.services.feature_service.load_multiple_seasons",
            return_value=(outfield_df.copy(), gk_df.copy(), fixtures_df.copy()),
        )

    def test_returns_five_tuple(self, outfield_df, gk_df, fixtures_df):
        with self._mock_load(outfield_df, gk_df, fixtures_df):
            result = build_season_data(["2024_2025"])
        assert len(result) == 5

    def test_match_features_has_all_feature_columns(self, outfield_df, gk_df, fixtures_df):
        with self._mock_load(outfield_df, gk_df, fixtures_df):
            match_features, *_ = build_season_data(["2024_2025"])
        for col in ["home_att", "home_mid", "home_def", "home_gk",
                    "away_att", "away_mid", "away_def", "away_gk"]:
            assert col in match_features.columns, f"Missing: {col}"

    def test_all_players_has_composite_score(self, outfield_df, gk_df, fixtures_df):
        with self._mock_load(outfield_df, gk_df, fixtures_df):
            _, all_players, *_ = build_season_data(["2024_2025"])
        assert "composite_score" in all_players.columns

    def test_all_players_has_position_group(self, outfield_df, gk_df, fixtures_df):
        with self._mock_load(outfield_df, gk_df, fixtures_df):
            _, all_players, *_ = build_season_data(["2024_2025"])
        assert "position_group" in all_players.columns

    def test_returns_standard_scalers(self, outfield_df, gk_df, fixtures_df):
        with self._mock_load(outfield_df, gk_df, fixtures_df):
            _, _, _, outfield_scaler, gk_scaler = build_season_data(["2024_2025"])
        assert isinstance(outfield_scaler, StandardScaler)
        assert isinstance(gk_scaler, StandardScaler)

    def test_fixtures_with_results_has_result_column(self, outfield_df, gk_df, fixtures_df):
        with self._mock_load(outfield_df, gk_df, fixtures_df):
            _, _, fixtures_with_results, *_ = build_season_data(["2024_2025"])
        assert "result" in fixtures_with_results.columns

    def test_adds_unknown_season_when_column_missing(self, outfield_df, gk_df, fixtures_df):
        fixtures_no_season = fixtures_df.drop(columns=["season"])
        with patch(
            "goals_app.services.feature_service.load_multiple_seasons",
            return_value=(outfield_df.copy(), gk_df.copy(), fixtures_no_season),
        ):
            result = build_season_data(["2024_2025"])
        assert result is not None  # Should not raise

    def test_accepts_prefit_outfield_scaler(self, outfield_df, gk_df, fixtures_df):
        prefit = StandardScaler().fit(np.zeros((5, 13)))  # 13 outfield metric cols
        with self._mock_load(outfield_df, gk_df, fixtures_df):
            _, _, _, returned_scaler, _ = build_season_data(
                ["2024_2025"], outfield_scaler=prefit
            )
        assert returned_scaler is prefit
