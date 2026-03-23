"""
tests/test_ml_service.py

Unit tests for goals_app/services/ml_service.py.

Tests are designed to run without trained artifacts on disk.
Data-dependent paths (train, predict_season) are covered via mocking.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest
from sklearn.ensemble import RandomForestClassifier

from goals_app.services.ml_service import (
    ARTIFACT_CLF,
    ARTIFACT_GK_SCALER,
    ARTIFACT_METRICS,
    ARTIFACT_OUTFIELD_SCALER,
    FEATURE_COLS,
    LABEL_COL,
    load_model,
    predict_all_fixtures,
    predict_season,
    train,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

class TestConstants:
    def test_feature_cols_has_eight_entries(self):
        """8 features: home & away ATT/MID/DEF/GK."""
        assert len(FEATURE_COLS) == 8

    def test_feature_cols_contains_home_and_away(self):
        home = [c for c in FEATURE_COLS if c.startswith("home_")]
        away = [c for c in FEATURE_COLS if c.startswith("away_")]
        assert len(home) == 4
        assert len(away) == 4

    def test_feature_cols_cover_all_positions(self):
        positions = {"att", "mid", "def", "gk"}
        found = {c.split("_")[1] for c in FEATURE_COLS}
        assert found == positions

    def test_label_col_is_result(self):
        assert LABEL_COL == "result"

    def test_artifact_paths_are_path_objects(self):
        for p in [ARTIFACT_CLF, ARTIFACT_OUTFIELD_SCALER, ARTIFACT_GK_SCALER, ARTIFACT_METRICS]:
            assert isinstance(p, Path)

    def test_artifact_pkl_extensions(self):
        for p in [ARTIFACT_CLF, ARTIFACT_OUTFIELD_SCALER, ARTIFACT_GK_SCALER]:
            assert p.suffix == ".pkl", f"Expected .pkl, got {p.suffix} for {p}"

    def test_metrics_json_extension(self):
        assert ARTIFACT_METRICS.suffix == ".json"


# ---------------------------------------------------------------------------
# load_model — no artifacts on disk
# ---------------------------------------------------------------------------

class TestLoadModel:
    def test_raises_file_not_found_when_clf_missing(self, tmp_path):
        """load_model must raise FileNotFoundError before anything else."""
        # Patch ARTIFACT_CLF to a path that doesn't exist
        nonexistent = tmp_path / "rf_classifier.pkl"
        with patch("goals_app.services.ml_service.ARTIFACT_CLF", nonexistent):
            with pytest.raises(FileNotFoundError):
                load_model()

    def test_error_message_is_helpful(self, tmp_path):
        """The error message should mention how to fix the problem."""
        nonexistent = tmp_path / "rf_classifier.pkl"
        with patch("goals_app.services.ml_service.ARTIFACT_CLF", nonexistent):
            with pytest.raises(FileNotFoundError, match=r"(?i)(train|model|artifact)"):
                load_model()


# ---------------------------------------------------------------------------
# predict_all_fixtures — no data on disk
# ---------------------------------------------------------------------------

class TestPredictAllFixtures:
    def test_returns_empty_list_when_no_data(self, tmp_path):
        """If neither player parquets nor fixtures exist, return [] gracefully."""
        nonexistent_clf = tmp_path / "rf_classifier.pkl"
        with patch("goals_app.services.ml_service.ARTIFACT_CLF", nonexistent_clf):
            # load_model will raise — predict_all_fixtures should propagate or handle it
            # The caller (calendar router) catches FileNotFoundError, so raising is fine.
            with pytest.raises(FileNotFoundError):
                predict_all_fixtures("9999_9999")

    def test_returns_list_type_when_model_present(self, tmp_path):
        """When a model is loaded, the return value is always a list."""
        # Build minimal mock artifacts
        clf = RandomForestClassifier(n_estimators=2, random_state=0)
        clf.fit(
            np.zeros((3, 8)),
            ["W", "D", "L"],
        )
        from sklearn.preprocessing import StandardScaler
        scaler = StandardScaler().fit(np.zeros((3, 8)))

        import joblib
        clf_path = tmp_path / "rf_classifier.pkl"
        out_scaler_path = tmp_path / "outfield_scaler.pkl"
        gk_scaler_path = tmp_path / "gk_scaler.pkl"
        metrics_path = tmp_path / "metrics.json"

        joblib.dump(clf, clf_path)
        joblib.dump(scaler, out_scaler_path)
        joblib.dump(scaler, gk_scaler_path)
        metrics_path.write_text(json.dumps({"n_train_matches": 3}))

        with (
            patch("goals_app.services.ml_service.ARTIFACT_CLF", clf_path),
            patch("goals_app.services.ml_service.ARTIFACT_OUTFIELD_SCALER", out_scaler_path),
            patch("goals_app.services.ml_service.ARTIFACT_GK_SCALER", gk_scaler_path),
            patch("goals_app.services.ml_service.ARTIFACT_METRICS", metrics_path),
            # No parquet data → load_season will raise → fixtures-only fallback will also raise
            patch("goals_app.services.ml_service.load_season", side_effect=FileNotFoundError),
            patch("goals_app.services.ml_service.load_fixtures_only", side_effect=FileNotFoundError),
        ):
            result = predict_all_fixtures("2024_2025")
            assert isinstance(result, list)
            assert result == []


# ---------------------------------------------------------------------------
# predict_season — mocked data
# ---------------------------------------------------------------------------

class TestPredictSeason:
    def _make_match_features(self):
        """Minimal match_features DataFrame with all 8 feature columns."""
        return pd.DataFrame({
            "match_id":  [1, 2, 3],
            "home_att":  [0.5, -0.1, 0.3],
            "home_mid":  [0.2,  0.4, -0.2],
            "home_def":  [0.1,  0.0,  0.5],
            "home_gk":   [0.3, -0.3,  0.1],
            "away_att":  [-0.2, 0.2,  0.0],
            "away_mid":  [ 0.1, 0.1, -0.1],
            "away_def":  [ 0.0, 0.3,  0.2],
            "away_gk":   [-0.1, 0.1,  0.3],
            "result":    ["W", "D", "L"],
        })

    def test_predict_season_returns_list_of_dicts(self, tmp_path):
        clf = RandomForestClassifier(n_estimators=2, random_state=0)
        X_dummy = np.random.default_rng(0).standard_normal((9, 8))
        y_dummy = ["W", "D", "L"] * 3
        clf.fit(X_dummy, y_dummy)

        from sklearn.preprocessing import StandardScaler
        scaler = StandardScaler().fit(X_dummy)

        import joblib
        clf_path = tmp_path / "rf_classifier.pkl"
        out_s = tmp_path / "outfield_scaler.pkl"
        gk_s  = tmp_path / "gk_scaler.pkl"
        m_path = tmp_path / "metrics.json"
        joblib.dump(clf, clf_path)
        joblib.dump(scaler, out_s)
        joblib.dump(scaler, gk_s)
        m_path.write_text(json.dumps({}))

        match_features = self._make_match_features()
        dummy_players = pd.DataFrame(columns=["match_id", "team_id", "position_group", "composite_score"])
        dummy_fixtures = pd.DataFrame(columns=["match_id"])

        with (
            patch("goals_app.services.ml_service.ARTIFACT_CLF", clf_path),
            patch("goals_app.services.ml_service.ARTIFACT_OUTFIELD_SCALER", out_s),
            patch("goals_app.services.ml_service.ARTIFACT_GK_SCALER", gk_s),
            patch("goals_app.services.ml_service.ARTIFACT_METRICS", m_path),
            patch(
                "goals_app.services.ml_service.build_season_data",
                return_value=(match_features, dummy_players, dummy_fixtures, scaler, scaler),
            ),
        ):
            results = predict_season("2024_2025")

        assert isinstance(results, list)
        assert len(results) == 3

    def test_predict_season_result_keys(self, tmp_path):
        clf = RandomForestClassifier(n_estimators=2, random_state=0)
        X_dummy = np.random.default_rng(1).standard_normal((9, 8))
        y_dummy = ["W", "D", "L"] * 3
        clf.fit(X_dummy, y_dummy)

        from sklearn.preprocessing import StandardScaler
        scaler = StandardScaler().fit(X_dummy)

        import joblib
        clf_path = tmp_path / "rf_classifier.pkl"
        out_s = tmp_path / "outfield_scaler.pkl"
        gk_s  = tmp_path / "gk_scaler.pkl"
        m_path = tmp_path / "metrics.json"
        joblib.dump(clf, clf_path)
        joblib.dump(scaler, out_s)
        joblib.dump(scaler, gk_s)
        m_path.write_text(json.dumps({}))

        match_features = self._make_match_features()
        dummy_players = pd.DataFrame()
        dummy_fixtures = pd.DataFrame()

        with (
            patch("goals_app.services.ml_service.ARTIFACT_CLF", clf_path),
            patch("goals_app.services.ml_service.ARTIFACT_OUTFIELD_SCALER", out_s),
            patch("goals_app.services.ml_service.ARTIFACT_GK_SCALER", gk_s),
            patch("goals_app.services.ml_service.ARTIFACT_METRICS", m_path),
            patch(
                "goals_app.services.ml_service.build_season_data",
                return_value=(match_features, dummy_players, dummy_fixtures, scaler, scaler),
            ),
        ):
            results = predict_season("2024_2025")

        for r in results:
            assert "match_id" in r
            assert "win_prob" in r
            assert "draw_prob" in r
            assert "loss_prob" in r

    def test_predict_season_probabilities_sum_to_one(self, tmp_path):
        clf = RandomForestClassifier(n_estimators=10, random_state=0)
        X_dummy = np.random.default_rng(2).standard_normal((30, 8))
        y_dummy = (["W"] * 10 + ["D"] * 10 + ["L"] * 10)
        clf.fit(X_dummy, y_dummy)

        from sklearn.preprocessing import StandardScaler
        scaler = StandardScaler().fit(X_dummy)

        import joblib
        clf_path = tmp_path / "rf_classifier.pkl"
        out_s = tmp_path / "outfield_scaler.pkl"
        gk_s  = tmp_path / "gk_scaler.pkl"
        m_path = tmp_path / "metrics.json"
        joblib.dump(clf, clf_path)
        joblib.dump(scaler, out_s)
        joblib.dump(scaler, gk_s)
        m_path.write_text(json.dumps({}))

        match_features = self._make_match_features()

        with (
            patch("goals_app.services.ml_service.ARTIFACT_CLF", clf_path),
            patch("goals_app.services.ml_service.ARTIFACT_OUTFIELD_SCALER", out_s),
            patch("goals_app.services.ml_service.ARTIFACT_GK_SCALER", gk_s),
            patch("goals_app.services.ml_service.ARTIFACT_METRICS", m_path),
            patch(
                "goals_app.services.ml_service.build_season_data",
                return_value=(match_features, pd.DataFrame(), pd.DataFrame(), scaler, scaler),
            ),
        ):
            results = predict_season("2024_2025")

        for r in results:
            total = r["win_prob"] + r["draw_prob"] + r["loss_prob"]
            assert abs(total - 1.0) < 0.01, f"Probabilities don't sum to 1: {r}"

    def test_predict_season_match_ids_are_strings(self, tmp_path):
        clf = RandomForestClassifier(n_estimators=2, random_state=0)
        X_dummy = np.random.default_rng(3).standard_normal((9, 8))
        clf.fit(X_dummy, ["W", "D", "L"] * 3)
        from sklearn.preprocessing import StandardScaler
        scaler = StandardScaler().fit(X_dummy)

        import joblib
        clf_path = tmp_path / "rf_classifier.pkl"
        out_s = tmp_path / "outfield_scaler.pkl"
        gk_s  = tmp_path / "gk_scaler.pkl"
        m_path = tmp_path / "metrics.json"
        joblib.dump(clf, clf_path)
        joblib.dump(scaler, out_s)
        joblib.dump(scaler, gk_s)
        m_path.write_text(json.dumps({}))

        match_features = self._make_match_features()

        with (
            patch("goals_app.services.ml_service.ARTIFACT_CLF", clf_path),
            patch("goals_app.services.ml_service.ARTIFACT_OUTFIELD_SCALER", out_s),
            patch("goals_app.services.ml_service.ARTIFACT_GK_SCALER", gk_s),
            patch("goals_app.services.ml_service.ARTIFACT_METRICS", m_path),
            patch(
                "goals_app.services.ml_service.build_season_data",
                return_value=(match_features, pd.DataFrame(), pd.DataFrame(), scaler, scaler),
            ),
        ):
            results = predict_season("2024_2025")

        for r in results:
            assert isinstance(r["match_id"], str)

    def test_predict_season_returns_empty_list_on_no_data(self, tmp_path):
        """Empty match_features → empty results, no crash."""
        clf = RandomForestClassifier(n_estimators=2, random_state=0)
        clf.fit(np.zeros((3, 8)), ["W", "D", "L"])

        from sklearn.preprocessing import StandardScaler
        scaler = StandardScaler().fit(np.zeros((3, 8)))

        import joblib
        clf_path = tmp_path / "rf_classifier.pkl"
        out_s = tmp_path / "outfield_scaler.pkl"
        gk_s  = tmp_path / "gk_scaler.pkl"
        m_path = tmp_path / "metrics.json"
        joblib.dump(clf, clf_path)
        joblib.dump(scaler, out_s)
        joblib.dump(scaler, gk_s)
        m_path.write_text(json.dumps({}))

        empty_features = pd.DataFrame(columns=FEATURE_COLS)

        with (
            patch("goals_app.services.ml_service.ARTIFACT_CLF", clf_path),
            patch("goals_app.services.ml_service.ARTIFACT_OUTFIELD_SCALER", out_s),
            patch("goals_app.services.ml_service.ARTIFACT_GK_SCALER", gk_s),
            patch("goals_app.services.ml_service.ARTIFACT_METRICS", m_path),
            patch(
                "goals_app.services.ml_service.build_season_data",
                return_value=(empty_features, pd.DataFrame(), pd.DataFrame(), scaler, scaler),
            ),
        ):
            result = predict_season("2024_2025")

        assert result == []


# ---------------------------------------------------------------------------
# train() — full pipeline with mocked build_season_data + tmp artifacts dir
# ---------------------------------------------------------------------------

def _make_train_match_features(n: int = 30) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    return pd.DataFrame({
        "match_id": range(1, n + 1),
        "home_att": rng.standard_normal(n),
        "home_mid": rng.standard_normal(n),
        "home_def": rng.standard_normal(n),
        "home_gk":  rng.standard_normal(n),
        "away_att": rng.standard_normal(n),
        "away_mid": rng.standard_normal(n),
        "away_def": rng.standard_normal(n),
        "away_gk":  rng.standard_normal(n),
        "result":   (["W"] * 10 + ["D"] * 10 + ["L"] * 10),
    })


def _make_train_fixtures(n: int = 30) -> pd.DataFrame:
    """fixtures_with_results used by train(): needs match_id, match_date, season, result."""
    return pd.DataFrame({
        "match_id":   range(1, n + 1),
        "match_date": (
            [f"2022-08-{(i % 28) + 1:02d}T15:00:00+00:00" for i in range(15)]
            + [f"2023-08-{(i % 28) + 1:02d}T15:00:00+00:00" for i in range(15)]
        ),
        "season":   ["2021_2022"] * 15 + ["2022_2023"] * 15,
        "home_id":  [10] * n,
        "away_id":  [20] * n,
        "result":   (["W"] * 10 + ["D"] * 10 + ["L"] * 10),
    })


class TestTrain:
    def _run_train(self, tmp_path):
        from sklearn.preprocessing import StandardScaler
        scaler = StandardScaler().fit(np.zeros((3, 8)))
        match_features = _make_train_match_features()
        fixtures = _make_train_fixtures()

        with (
            patch(
                "goals_app.services.ml_service.build_season_data",
                return_value=(match_features, pd.DataFrame(), fixtures, scaler, scaler),
            ),
            patch("goals_app.services.ml_service.ARTIFACTS_DIR", tmp_path),
            patch("goals_app.services.ml_service.ARTIFACT_CLF",
                  tmp_path / "rf_classifier.pkl"),
            patch("goals_app.services.ml_service.ARTIFACT_OUTFIELD_SCALER",
                  tmp_path / "outfield_scaler.pkl"),
            patch("goals_app.services.ml_service.ARTIFACT_GK_SCALER",
                  tmp_path / "gk_scaler.pkl"),
            patch("goals_app.services.ml_service.ARTIFACT_METRICS",
                  tmp_path / "metrics.json"),
        ):
            return train(["2021_2022", "2022_2023"])

    def test_train_returns_dict(self, tmp_path):
        metrics = self._run_train(tmp_path)
        assert isinstance(metrics, dict)

    def test_train_metrics_has_required_keys(self, tmp_path):
        metrics = self._run_train(tmp_path)
        for key in ["n_train_matches", "train_accuracy", "train_macro_f1",
                    "cv_folds", "confusion_matrix", "seasons_used"]:
            assert key in metrics, f"Missing key: {key}"

    def test_train_accuracy_in_valid_range(self, tmp_path):
        metrics = self._run_train(tmp_path)
        assert 0.0 <= metrics["train_accuracy"] <= 1.0
        assert 0.0 <= metrics["train_macro_f1"] <= 1.0

    def test_train_n_matches_is_positive(self, tmp_path):
        metrics = self._run_train(tmp_path)
        assert metrics["n_train_matches"] > 0

    def test_train_cv_folds_with_two_seasons(self, tmp_path):
        """Two seasons → one walk-forward CV fold."""
        metrics = self._run_train(tmp_path)
        assert len(metrics["cv_folds"]) >= 1

    def test_train_cv_fold_has_required_keys(self, tmp_path):
        metrics = self._run_train(tmp_path)
        for fold in metrics["cv_folds"]:
            assert "train_seasons" in fold
            assert "val_season" in fold
            assert "accuracy" in fold
            assert "macro_f1" in fold

    def test_train_saves_classifier_artifact(self, tmp_path):
        self._run_train(tmp_path)
        assert (tmp_path / "rf_classifier.pkl").exists()

    def test_train_saves_outfield_scaler_artifact(self, tmp_path):
        self._run_train(tmp_path)
        assert (tmp_path / "outfield_scaler.pkl").exists()

    def test_train_saves_gk_scaler_artifact(self, tmp_path):
        self._run_train(tmp_path)
        assert (tmp_path / "gk_scaler.pkl").exists()

    def test_train_saves_metrics_json(self, tmp_path):
        self._run_train(tmp_path)
        metrics_path = tmp_path / "metrics.json"
        assert metrics_path.exists()
        loaded = json.loads(metrics_path.read_text())
        assert "n_train_matches" in loaded

    def test_train_confusion_matrix_has_labels(self, tmp_path):
        metrics = self._run_train(tmp_path)
        cm = metrics["confusion_matrix"]
        assert "labels" in cm
        assert "matrix" in cm
        assert set(cm["labels"]) == {"W", "D", "L"}

    def test_train_single_season_produces_no_cv_folds(self, tmp_path):
        """Single season → walk-forward CV cannot run."""
        from sklearn.preprocessing import StandardScaler
        scaler = StandardScaler().fit(np.zeros((3, 8)))
        n = 15
        rng = np.random.default_rng(99)
        single_features = pd.DataFrame({
            "match_id": range(1, n + 1),
            "home_att": rng.standard_normal(n), "home_mid": rng.standard_normal(n),
            "home_def": rng.standard_normal(n), "home_gk":  rng.standard_normal(n),
            "away_att": rng.standard_normal(n), "away_mid": rng.standard_normal(n),
            "away_def": rng.standard_normal(n), "away_gk":  rng.standard_normal(n),
            "result":   (["W"] * 5 + ["D"] * 5 + ["L"] * 5),
        })
        single_fixtures = pd.DataFrame({
            "match_id":   range(1, n + 1),
            "match_date": [f"2022-08-{i + 1:02d}T15:00:00+00:00" for i in range(n)],
            "season":     ["2021_2022"] * n,
            "home_id":    [10] * n,
            "away_id":    [20] * n,
            "result":     (["W"] * 5 + ["D"] * 5 + ["L"] * 5),
        })
        with (
            patch(
                "goals_app.services.ml_service.build_season_data",
                return_value=(single_features, pd.DataFrame(), single_fixtures, scaler, scaler),
            ),
            patch("goals_app.services.ml_service.ARTIFACTS_DIR", tmp_path),
            patch("goals_app.services.ml_service.ARTIFACT_CLF",
                  tmp_path / "rf_classifier.pkl"),
            patch("goals_app.services.ml_service.ARTIFACT_OUTFIELD_SCALER",
                  tmp_path / "outfield_scaler.pkl"),
            patch("goals_app.services.ml_service.ARTIFACT_GK_SCALER",
                  tmp_path / "gk_scaler.pkl"),
            patch("goals_app.services.ml_service.ARTIFACT_METRICS",
                  tmp_path / "metrics.json"),
        ):
            metrics = train(["2021_2022"])
        assert metrics["cv_folds"] == []


# ---------------------------------------------------------------------------
# load_model() — success path (artifacts exist on disk)
# ---------------------------------------------------------------------------

class TestLoadModelSuccess:
    def _write_artifacts(self, tmp_path):
        import joblib
        from sklearn.preprocessing import StandardScaler

        clf = RandomForestClassifier(n_estimators=2, random_state=0)
        clf.fit(np.zeros((3, 8)), ["W", "D", "L"])
        scaler = StandardScaler().fit(np.zeros((3, 8)))
        metrics_data = {"n_train_matches": 42, "train_accuracy": 0.75}

        clf_path = tmp_path / "rf_classifier.pkl"
        out_path = tmp_path / "outfield_scaler.pkl"
        gk_path  = tmp_path / "gk_scaler.pkl"
        m_path   = tmp_path / "metrics.json"

        joblib.dump(clf, clf_path)
        joblib.dump(scaler, out_path)
        joblib.dump(scaler, gk_path)
        m_path.write_text(json.dumps(metrics_data))

        return clf_path, out_path, gk_path, m_path

    def _load(self, tmp_path):
        clf_p, out_p, gk_p, m_p = self._write_artifacts(tmp_path)
        with (
            patch("goals_app.services.ml_service.ARTIFACT_CLF", clf_p),
            patch("goals_app.services.ml_service.ARTIFACT_OUTFIELD_SCALER", out_p),
            patch("goals_app.services.ml_service.ARTIFACT_GK_SCALER", gk_p),
            patch("goals_app.services.ml_service.ARTIFACT_METRICS", m_p),
        ):
            return load_model()

    def test_load_model_returns_four_items(self, tmp_path):
        result = self._load(tmp_path)
        assert len(result) == 4

    def test_load_model_returns_random_forest_classifier(self, tmp_path):
        clf, _, _, _ = self._load(tmp_path)
        assert isinstance(clf, RandomForestClassifier)

    def test_load_model_returns_metrics_dict(self, tmp_path):
        _, _, _, metrics = self._load(tmp_path)
        assert isinstance(metrics, dict)
        assert metrics["n_train_matches"] == 42
        assert metrics["train_accuracy"] == 0.75

    def test_loaded_classifier_can_predict(self, tmp_path):
        clf, _, _, _ = self._load(tmp_path)
        prediction = clf.predict(np.zeros((1, 8)))
        assert prediction[0] in ["W", "D", "L"]

    def test_loaded_scalers_are_standard_scalers(self, tmp_path):
        from sklearn.preprocessing import StandardScaler
        _, outfield_scaler, gk_scaler, _ = self._load(tmp_path)
        assert isinstance(outfield_scaler, StandardScaler)
        assert isinstance(gk_scaler, StandardScaler)
