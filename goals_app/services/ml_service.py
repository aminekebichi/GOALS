"""
ml_service.py

Train RF classifier + save; load + predict.
Walk-forward chronological CV within training seasons.
"""

import json
import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, f1_score, confusion_matrix

from goals_app.config import ARTIFACTS_DIR, TRAIN_SEASONS, TEST_SEASON, FOTMOB_DIR
from goals_app.services.feature_service import (
    build_season_data,
    load_season,
    load_fixtures_only,
    compute_outfield_composite,
    compute_gk_composite,
    derive_match_results,
    aggregate_to_team,
)

FEATURE_COLS = [
    "home_att", "home_mid", "home_def", "home_gk",
    "away_att", "away_mid", "away_def", "away_gk",
]
LABEL_COL = "result"
ARTIFACT_CLF = ARTIFACTS_DIR / "rf_classifier.pkl"
ARTIFACT_OUTFIELD_SCALER = ARTIFACTS_DIR / "outfield_scaler.pkl"
ARTIFACT_GK_SCALER = ARTIFACTS_DIR / "gk_scaler.pkl"
ARTIFACT_METRICS = ARTIFACTS_DIR / "metrics.json"


def train(seasons: list[str] = TRAIN_SEASONS) -> dict:
    """
    Load training seasons, compute features, train RF classifier with
    walk-forward CV, save artifacts, return metrics dict.
    """
    print(f"Loading seasons: {seasons}")
    match_features, _, fixtures_with_results, outfield_scaler, gk_scaler = build_season_data(seasons)

    # Drop rows with missing result or features
    df = match_features.dropna(subset=FEATURE_COLS + [LABEL_COL])
    df = df[df[LABEL_COL].isin(["W", "D", "L"])].copy()

    # Sort chronologically
    fixtures_with_results["match_date"] = pd.to_datetime(fixtures_with_results["match_date"], utc=True)
    date_map = fixtures_with_results.set_index("match_id")["match_date"].to_dict()
    df["match_date"] = df["match_id"].map(date_map)
    df = df.sort_values("match_date").reset_index(drop=True)

    X = df[FEATURE_COLS].values
    y = df[LABEL_COL].values

    # Walk-forward CV: split by season
    # Seasons available in the data
    season_map = fixtures_with_results.set_index("match_id")["season"].to_dict()
    df["season"] = df["match_id"].map(season_map)
    available_seasons = sorted(df["season"].dropna().unique())

    cv_results = []
    if len(available_seasons) > 1:
        for i in range(1, len(available_seasons)):
            train_seasons_cv = available_seasons[:i]
            val_season = available_seasons[i]
            train_mask = df["season"].isin(train_seasons_cv)
            val_mask = df["season"] == val_season

            X_tr, y_tr = X[train_mask], y[train_mask]
            X_val, y_val = X[val_mask], y[val_mask]

            clf_cv = RandomForestClassifier(
                n_estimators=100, class_weight="balanced", random_state=42
            )
            clf_cv.fit(X_tr, y_tr)
            y_pred = clf_cv.predict(X_val)

            acc = accuracy_score(y_val, y_pred)
            f1 = f1_score(y_val, y_pred, average="macro", zero_division=0)
            cv_results.append({
                "train_seasons": list(train_seasons_cv),
                "val_season": val_season,
                "accuracy": round(acc, 4),
                "macro_f1": round(f1, 4),
            })
            print(f"  CV fold {i}: train={train_seasons_cv} val={val_season} "
                  f"acc={acc:.3f} f1={f1:.3f}")

    # Final model trained on all available seasons
    print(f"Training final model on all {len(df)} matches...")
    clf = RandomForestClassifier(n_estimators=200, class_weight="balanced", random_state=42)
    clf.fit(X, y)

    final_preds = clf.predict(X)
    final_acc = accuracy_score(y, final_preds)
    final_f1 = f1_score(y, final_preds, average="macro", zero_division=0)
    cm = confusion_matrix(y, final_preds, labels=["W", "D", "L"]).tolist()

    metrics = {
        "n_train_matches": len(df),
        "seasons_used": list(available_seasons),
        "train_accuracy": round(final_acc, 4),
        "train_macro_f1": round(final_f1, 4),
        "confusion_matrix": {"labels": ["W", "D", "L"], "matrix": cm},
        "cv_folds": cv_results,
    }

    # Save artifacts
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(clf, ARTIFACT_CLF)
    joblib.dump(outfield_scaler, ARTIFACT_OUTFIELD_SCALER)
    joblib.dump(gk_scaler, ARTIFACT_GK_SCALER)
    with open(ARTIFACT_METRICS, "w") as f:
        json.dump(metrics, f, indent=2)

    print(f"Artifacts saved to {ARTIFACTS_DIR}")
    print(f"Train accuracy: {final_acc:.3f}  Macro F1: {final_f1:.3f}")
    return metrics


def load_model() -> tuple:
    """
    Load trained artifacts. Raises FileNotFoundError with clear message if not trained.
    Returns (clf, outfield_scaler, gk_scaler, metrics_dict).
    """
    if not ARTIFACT_CLF.exists():
        raise FileNotFoundError(
            f"No trained model found at {ARTIFACT_CLF}. Run `python train.py` first."
        )
    clf = joblib.load(ARTIFACT_CLF)
    outfield_scaler = joblib.load(ARTIFACT_OUTFIELD_SCALER)
    gk_scaler = joblib.load(ARTIFACT_GK_SCALER)
    with open(ARTIFACT_METRICS) as f:
        metrics = json.load(f)
    return clf, outfield_scaler, gk_scaler, metrics


def predict_all_fixtures(season: str) -> list[dict]:
    """
    Predict every fixture in a season — both played and unplayed.

    - Played matches: use actual per-match composite scores.
    - Unplayed matches: use each team's season-average composite scores as proxy.
    - If a team has no data this season yet: fall back to their average across
      all available training seasons.

    Returns list of {match_id, win_prob, draw_prob, loss_prob}.
    """
    clf, outfield_scaler, gk_scaler, _ = load_model()
    classes = list(clf.classes_)

    def _proba(feature_row) -> dict:
        X = [[
            feature_row["home_att"], feature_row["home_mid"],
            feature_row["home_def"], feature_row["home_gk"],
            feature_row["away_att"], feature_row["away_mid"],
            feature_row["away_def"], feature_row["away_gk"],
        ]]
        p = dict(zip(classes, clf.predict_proba(X)[0]))
        return {
            "win_prob": round(p.get("W", 0), 4),
            "draw_prob": round(p.get("D", 0), 4),
            "loss_prob": round(p.get("L", 0), 4),
        }

    # ----------------------------------------------------------------
    # Load season player data — fall back to fixtures-only if not scraped
    # ----------------------------------------------------------------
    played_lookup: dict = {}
    team_avg: dict = {}

    try:
        outfield_df, gk_df, fixtures_df = load_season(season)

        outfield_scored, _ = compute_outfield_composite(outfield_df, outfield_scaler)
        gk_scored, _ = compute_gk_composite(gk_df, gk_scaler)

        player_cols = ["match_id", "team_id", "position_group", "composite_score"]
        for col in player_cols:
            if col not in outfield_scored.columns:
                outfield_scored[col] = None
            if col not in gk_scored.columns:
                gk_scored[col] = None

        all_players = pd.concat(
            [outfield_scored[player_cols], gk_scored[player_cols]],
            ignore_index=True,
        )

        # Per-match features for played matches
        fixtures_with_results = derive_match_results(outfield_df, fixtures_df)
        match_features = aggregate_to_team(all_players, fixtures_with_results)
        played_lookup = {
            str(r["match_id"]): r
            for _, r in match_features[FEATURE_COLS + ["match_id"]].iterrows()
        }

        # Season-average per team (proxy for unplayed matches)
        avg_pivot = (
            all_players.groupby(["team_id", "position_group"])["composite_score"]
            .mean()
            .reset_index()
            .pivot_table(index="team_id", columns="position_group",
                         values="composite_score", fill_value=0)
            .reset_index()
        )
        avg_pivot.columns.name = None
        for col in ["ATT", "MID", "DEF", "GK"]:
            if col not in avg_pivot.columns:
                avg_pivot[col] = 0.0
        avg_pivot["team_id"] = pd.to_numeric(avg_pivot["team_id"], errors="coerce").astype("Int64")
        team_avg = avg_pivot.set_index("team_id").to_dict(orient="index")

    except FileNotFoundError:
        # Player parquets not scraped yet — try fixtures-only
        try:
            fixtures_df = load_fixtures_only(season)
        except FileNotFoundError:
            return []  # Nothing to show at all

    # ----------------------------------------------------------------
    # Fallback: training-season averages for teams with no current data
    # ----------------------------------------------------------------
    fallback_avg: dict = {}
    try:
        available_train = [
            s for s in TRAIN_SEASONS
            if (FOTMOB_DIR / s / "output" / "outfield_players.parquet").exists()
            and s != season
        ]
        if available_train:
            _, all_players_train, _, _, _ = build_season_data(
                available_train, outfield_scaler, gk_scaler
            )
            fb_pivot = (
                all_players_train.groupby(["team_id", "position_group"])["composite_score"]
                .mean()
                .reset_index()
                .pivot_table(index="team_id", columns="position_group",
                             values="composite_score", fill_value=0)
                .reset_index()
            )
            fb_pivot.columns.name = None
            for col in ["ATT", "MID", "DEF", "GK"]:
                if col not in fb_pivot.columns:
                    fb_pivot[col] = 0.0
            fb_pivot["team_id"] = pd.to_numeric(fb_pivot["team_id"], errors="coerce").astype("Int64")
            fallback_avg = fb_pivot.set_index("team_id").to_dict(orient="index")
    except Exception:
        pass

    # ----------------------------------------------------------------
    # Predict every fixture
    # ----------------------------------------------------------------
    fixtures_df["home_id"] = pd.to_numeric(fixtures_df["home_id"], errors="coerce").astype("Int64")
    fixtures_df["away_id"] = pd.to_numeric(fixtures_df["away_id"], errors="coerce").astype("Int64")

    results = []
    for _, fix in fixtures_df.iterrows():
        mid = str(fix["match_id"])

        if mid in played_lookup:
            row = played_lookup[mid]
            results.append({"match_id": mid, **_proba(row)})
            continue

        # Unplayed — look up team averages
        home_id = fix["home_id"]
        away_id = fix["away_id"]

        def _team_vec(tid):
            d = team_avg.get(tid) or fallback_avg.get(tid)
            if d is None:
                return None
            return {"att": d.get("ATT", 0), "mid": d.get("MID", 0),
                    "def": d.get("DEF", 0), "gk": d.get("GK", 0)}

        home_vec = _team_vec(home_id)
        away_vec = _team_vec(away_id)

        if home_vec is None or away_vec is None:
            continue  # No data for this team at all

        feature_row = {
            "home_att": home_vec["att"], "home_mid": home_vec["mid"],
            "home_def": home_vec["def"], "home_gk": home_vec["gk"],
            "away_att": away_vec["att"], "away_mid": away_vec["mid"],
            "away_def": away_vec["def"], "away_gk": away_vec["gk"],
        }
        results.append({"match_id": mid, **_proba(feature_row)})

    return results


def predict_season(season: str) -> list[dict]:
    """
    Load a season's data, compute features using saved scalers, predict probabilities.
    Returns list of {match_id, win_prob, draw_prob, loss_prob}.
    """
    clf, outfield_scaler, gk_scaler, _ = load_model()

    match_features, _, _, _, _ = build_season_data(
        [season],
        outfield_scaler=outfield_scaler,
        gk_scaler=gk_scaler,
    )

    df = match_features.dropna(subset=FEATURE_COLS).copy()
    if df.empty:
        return []

    X = df[FEATURE_COLS].values
    # classes_ order: alphabetical by default — [D, L, W]
    classes = list(clf.classes_)
    probas = clf.predict_proba(X)

    results = []
    for i, row in df.iterrows():
        proba_dict = dict(zip(classes, probas[df.index.get_loc(i)]))
        results.append({
            "match_id": str(row["match_id"]),
            "win_prob": round(proba_dict.get("W", 0), 4),
            "draw_prob": round(proba_dict.get("D", 0), 4),
            "loss_prob": round(proba_dict.get("L", 0), 4),
        })
    return results
