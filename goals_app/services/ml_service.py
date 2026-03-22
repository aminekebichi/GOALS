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

from goals_app.config import ARTIFACTS_DIR, TRAIN_SEASONS, TEST_SEASON
from goals_app.services.feature_service import build_season_data

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
