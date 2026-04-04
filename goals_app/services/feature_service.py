"""
feature_service.py

Loads FotMob parquet data, computes position-specific composite scores,
derives match results, and aggregates to team-level feature vectors.

Column name corrections (actual parquet vs CLAUDE.md):
  - dribbles_succeeded       (not successful_dribbles)
  - aerials_won              (not aerial_duels_won)
  - assists                  (not goal_assist)
  - matchstats.headers.tackles  (not tackles_won)
  - keeper_diving_save       (not diving_save)
  - keeper_high_claim        (not high_claim)
  - keeper_sweeper           (not acted_as_sweeper)
  - expected_goals_on_target_faced  (not xgot_faced)
"""

import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.preprocessing import StandardScaler
from typing import Optional

from goals_app.config import FOTMOB_DIRS, DEFAULT_LEAGUE_ID, POSITION_MAP


# ---------------------------------------------------------------------------
# Composite score weight definitions
# ---------------------------------------------------------------------------

ATT_WEIGHTS = {
    "goals_assists": 0.25,
    "xg": 0.20,
    "xa": 0.15,
    "dribbles": 0.15,
    "shots": 0.10,
    "chances_created": 0.10,
    "recoveries": 0.05,
}

MID_WEIGHTS = {
    "prog_pass": 0.20,
    "chances_created": 0.20,
    "xa": 0.15,
    "goals_assists": 0.15,
    "tackles": 0.15,
    "interceptions": 0.10,
    "recoveries": 0.05,
}

DEF_WEIGHTS = {
    "tackles": 0.25,
    "aerials_won": 0.20,
    "clearances": 0.20,
    "interceptions": 0.15,
    "shot_blocks": 0.10,
    "prog_pass": 0.10,
}

GK_WEIGHTS = {
    "saves": 0.30,
    "xgot_faced": 0.25,
    "diving_saves": 0.15,
    "saves_inside_box": 0.15,
    "high_claims": 0.10,
    "sweeper_actions": 0.05,
}


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _fotmob_dir(league_id: int = DEFAULT_LEAGUE_ID):
    """Return the FotMob data directory for the given league."""
    from goals_app.config import FOTMOB_DIRS
    return FOTMOB_DIRS.get(league_id, FOTMOB_DIRS[DEFAULT_LEAGUE_ID])


def load_season(
    season: str, league_id: int = DEFAULT_LEAGUE_ID
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load outfield_players, goalkeepers, and fixtures parquets for a season."""
    base = _fotmob_dir(league_id) / season / "output"
    outfield = pd.read_parquet(base / "outfield_players.parquet")
    gk = pd.read_parquet(base / "goalkeepers.parquet")
    fixtures = pd.read_parquet(base / "fixtures.parquet")
    return outfield, gk, fixtures


def load_fixtures_only(season: str, league_id: int = DEFAULT_LEAGUE_ID) -> pd.DataFrame:
    """Load just the fixtures parquet — works even when player parquets don't exist yet."""
    path = _fotmob_dir(league_id) / season / "output" / "fixtures.parquet"
    if not path.exists():
        raise FileNotFoundError(f"No fixtures found for season {season} at {path}")
    return pd.read_parquet(path)


def load_multiple_seasons(
    seasons: list[str], league_id: int = DEFAULT_LEAGUE_ID
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Concatenate outfield, gk, and fixtures across multiple seasons."""
    outfields, gks, fixtures_list = [], [], []
    for s in seasons:
        try:
            o, g, f = load_season(s, league_id)
            o["season"] = s
            g["season"] = s
            f["season"] = s
            outfields.append(o)
            gks.append(g)
            fixtures_list.append(f)
        except FileNotFoundError:
            pass  # Season not yet scraped — skip silently
    if not outfields:
        raise ValueError(f"No seasons found for: {seasons}")
    return (
        pd.concat(outfields, ignore_index=True),
        pd.concat(gks, ignore_index=True),
        pd.concat(fixtures_list, ignore_index=True),
    )


# ---------------------------------------------------------------------------
# Column accessors (safe fallbacks to 0 if column missing)
# ---------------------------------------------------------------------------

def _col(df: pd.DataFrame, name: str) -> pd.Series:
    return df[name].fillna(0) if name in df.columns else pd.Series(0, index=df.index)


# ---------------------------------------------------------------------------
# Composite score computation
# ---------------------------------------------------------------------------

def _build_outfield_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add derived metric columns used by composite score formulas.
    Works on the raw outfield parquet column names.
    """
    out = df.copy()
    out["_goals_assists"] = _col(df, "goals") + _col(df, "assists")
    out["_xg"] = _col(df, "expected_goals")
    out["_xa"] = _col(df, "expected_assists")
    out["_dribbles"] = _col(df, "dribbles_succeeded")
    out["_shots"] = _col(df, "ShotsOnTarget")
    out["_chances_created"] = _col(df, "chances_created")
    out["_recoveries"] = _col(df, "recoveries")
    out["_prog_pass"] = _col(df, "accurate_passes")
    out["_tackles"] = _col(df, "matchstats.headers.tackles")
    out["_interceptions"] = _col(df, "interceptions")
    out["_aerials_won"] = _col(df, "aerials_won")
    out["_clearances"] = _col(df, "clearances")
    out["_shot_blocks"] = _col(df, "shot_blocks")
    return out


def _build_gk_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["_saves"] = _col(df, "saves")
    out["_xgot_faced"] = _col(df, "expected_goals_on_target_faced")
    out["_diving_saves"] = _col(df, "keeper_diving_save")
    out["_saves_inside_box"] = _col(df, "saves_inside_box")
    out["_high_claims"] = _col(df, "keeper_high_claim")
    out["_sweeper_actions"] = _col(df, "keeper_sweeper")
    return out


def _zscore_fit(df: pd.DataFrame, cols: list[str]) -> StandardScaler:
    scaler = StandardScaler()
    data = df[cols].fillna(0).values
    scaler.fit(data)
    return scaler


def _zscore_transform(df: pd.DataFrame, cols: list[str], scaler: StandardScaler) -> pd.DataFrame:
    out = df.copy()
    data = df[cols].fillna(0).values
    transformed = scaler.transform(data)
    for i, c in enumerate(cols):
        out[c + "_z"] = transformed[:, i]
    return out


def compute_outfield_composite(
    df: pd.DataFrame,
    scaler: Optional[StandardScaler] = None,
) -> tuple[pd.DataFrame, StandardScaler]:
    """
    Compute composite scores for outfield players.
    Returns (df_with_scores, fitted_scaler).
    If scaler is provided, use it (test set); otherwise fit a new one (train set).
    """
    df = _build_outfield_features(df)

    metric_cols = [
        "_goals_assists", "_xg", "_xa", "_dribbles", "_shots",
        "_chances_created", "_recoveries", "_prog_pass", "_tackles",
        "_interceptions", "_aerials_won", "_clearances", "_shot_blocks",
    ]

    if scaler is None:
        scaler = _zscore_fit(df, metric_cols)
    df = _zscore_transform(df, metric_cols, scaler)

    # Map position_id to group
    pos_map = {1.0: "DEF", 2.0: "MID", 3.0: "ATT"}
    df["position_group"] = df["position_id"].map(pos_map).fillna("MID")

    def att_score(row):
        return (
            ATT_WEIGHTS["goals_assists"] * row["_goals_assists_z"]
            + ATT_WEIGHTS["xg"] * row["_xg_z"]
            + ATT_WEIGHTS["xa"] * row["_xa_z"]
            + ATT_WEIGHTS["dribbles"] * row["_dribbles_z"]
            + ATT_WEIGHTS["shots"] * row["_shots_z"]
            + ATT_WEIGHTS["chances_created"] * row["_chances_created_z"]
            + ATT_WEIGHTS["recoveries"] * row["_recoveries_z"]
        )

    def mid_score(row):
        return (
            MID_WEIGHTS["prog_pass"] * row["_prog_pass_z"]
            + MID_WEIGHTS["chances_created"] * row["_chances_created_z"]
            + MID_WEIGHTS["xa"] * row["_xa_z"]
            + MID_WEIGHTS["goals_assists"] * row["_goals_assists_z"]
            + MID_WEIGHTS["tackles"] * row["_tackles_z"]
            + MID_WEIGHTS["interceptions"] * row["_interceptions_z"]
            + MID_WEIGHTS["recoveries"] * row["_recoveries_z"]
        )

    def def_score(row):
        return (
            DEF_WEIGHTS["tackles"] * row["_tackles_z"]
            + DEF_WEIGHTS["aerials_won"] * row["_aerials_won_z"]
            + DEF_WEIGHTS["clearances"] * row["_clearances_z"]
            + DEF_WEIGHTS["interceptions"] * row["_interceptions_z"]
            + DEF_WEIGHTS["shot_blocks"] * row["_shot_blocks_z"]
            + DEF_WEIGHTS["prog_pass"] * row["_prog_pass_z"]
        )

    score_fn = {"ATT": att_score, "MID": mid_score, "DEF": def_score}

    scores = []
    for _, row in df.iterrows():
        fn = score_fn.get(row["position_group"], mid_score)
        scores.append(fn(row))
    df["composite_score"] = scores

    return df, scaler


def compute_gk_composite(
    df: pd.DataFrame,
    scaler: Optional[StandardScaler] = None,
) -> tuple[pd.DataFrame, StandardScaler]:
    """Compute GK composite scores."""
    df = _build_gk_features(df)

    metric_cols = [
        "_saves", "_xgot_faced", "_diving_saves",
        "_saves_inside_box", "_high_claims", "_sweeper_actions",
    ]

    if scaler is None:
        scaler = _zscore_fit(df, metric_cols)
    df = _zscore_transform(df, metric_cols, scaler)

    df["position_group"] = "GK"
    df["composite_score"] = (
        GK_WEIGHTS["saves"] * df["_saves_z"]
        + GK_WEIGHTS["xgot_faced"] * df["_xgot_faced_z"]
        + GK_WEIGHTS["diving_saves"] * df["_diving_saves_z"]
        + GK_WEIGHTS["saves_inside_box"] * df["_saves_inside_box_z"]
        + GK_WEIGHTS["high_claims"] * df["_high_claims_z"]
        + GK_WEIGHTS["sweeper_actions"] * df["_sweeper_actions_z"]
    )

    return df, scaler


# ---------------------------------------------------------------------------
# Match result derivation
# ---------------------------------------------------------------------------

def derive_match_results(outfield_df: pd.DataFrame, fixtures_df: pd.DataFrame) -> pd.DataFrame:
    """
    Derive home_goals, away_goals, result (W/D/L from home perspective)
    by summing goals per (match_id, team_id) from outfield player data,
    then joining to fixtures on home_id / away_id.
    """
    goals_by_team = (
        outfield_df.groupby(["match_id", "team_id"])["goals"]
        .sum()
        .reset_index()
        .rename(columns={"goals": "team_goals"})
    )
    # Normalize team_id to int64 for consistent joins
    goals_by_team["team_id"] = goals_by_team["team_id"].astype("int64")

    fix = fixtures_df.copy()
    # Normalize all join key types
    fix["match_id"]  = pd.to_numeric(fix["match_id"],  errors="coerce").astype("int64")
    fix["home_id"]   = pd.to_numeric(fix["home_id"],   errors="coerce").astype("Int64")
    fix["away_id"]   = pd.to_numeric(fix["away_id"],   errors="coerce").astype("Int64")
    goals_by_team["match_id"] = pd.to_numeric(goals_by_team["match_id"], errors="coerce").astype("int64")
    goals_by_team["team_id"]  = goals_by_team["team_id"].astype("Int64")

    # Join home goals
    home_goals = goals_by_team.rename(columns={"team_id": "home_id", "team_goals": "home_goals"})
    fix = fix.merge(home_goals, on=["match_id", "home_id"], how="left")

    # Join away goals
    away_goals = goals_by_team.rename(columns={"team_id": "away_id", "team_goals": "away_goals"})
    fix = fix.merge(away_goals, on=["match_id", "away_id"], how="left")

    fix["home_goals"] = fix["home_goals"].fillna(0)
    fix["away_goals"] = fix["away_goals"].fillna(0)

    def result(row):
        if row["home_goals"] > row["away_goals"]:
            return "W"
        elif row["home_goals"] < row["away_goals"]:
            return "L"
        else:
            return "D"

    fix["result"] = fix.apply(result, axis=1)
    return fix


# ---------------------------------------------------------------------------
# Team-level aggregation
# ---------------------------------------------------------------------------

def aggregate_to_team(
    player_scores_df: pd.DataFrame,
    fixtures_with_results: pd.DataFrame,
) -> pd.DataFrame:
    """
    For each match, sum ATT/MID/DEF/GK composite scores per team.
    Returns a df with columns:
      match_id, home_att, home_mid, home_def, home_gk,
                away_att, away_mid, away_def, away_gk, result
    """
    # Sum per (match_id, team_id, position_group)
    agg = (
        player_scores_df.groupby(["match_id", "team_id", "position_group"])["composite_score"]
        .sum()
        .reset_index()
    )

    # Pivot to wide: one row per (match_id, team_id)
    pivot = agg.pivot_table(
        index=["match_id", "team_id"],
        columns="position_group",
        values="composite_score",
        fill_value=0,
    ).reset_index()
    pivot.columns.name = None

    # Ensure all position columns exist
    for col in ["ATT", "MID", "DEF", "GK"]:
        if col not in pivot.columns:
            pivot[col] = 0.0

    # Normalize all join key types
    pivot["match_id"] = pd.to_numeric(pivot["match_id"], errors="coerce").astype("int64")
    pivot["team_id"]  = pd.to_numeric(pivot["team_id"],  errors="coerce").astype("Int64")

    # Join to fixtures to get home/away split
    fix = fixtures_with_results[["match_id", "home_id", "away_id", "result"]].copy()
    fix["match_id"] = pd.to_numeric(fix["match_id"], errors="coerce").astype("int64")
    fix["home_id"]  = pd.to_numeric(fix["home_id"],  errors="coerce").astype("Int64")
    fix["away_id"]  = pd.to_numeric(fix["away_id"],  errors="coerce").astype("Int64")

    home = pivot.rename(columns={
        "team_id": "home_id",
        "ATT": "home_att", "MID": "home_mid", "DEF": "home_def", "GK": "home_gk",
    })
    away = pivot.rename(columns={
        "team_id": "away_id",
        "ATT": "away_att", "MID": "away_mid", "DEF": "away_def", "GK": "away_gk",
    })

    match_features = fix.merge(home[["match_id", "home_id", "home_att", "home_mid", "home_def", "home_gk"]],
                               on=["match_id", "home_id"], how="left")
    match_features = match_features.merge(away[["match_id", "away_id", "away_att", "away_mid", "away_def", "away_gk"]],
                                          on=["match_id", "away_id"], how="left")

    for col in ["home_att", "home_mid", "home_def", "home_gk",
                "away_att", "away_mid", "away_def", "away_gk"]:
        match_features[col] = match_features[col].fillna(0)

    return match_features


# ---------------------------------------------------------------------------
# Player metric contributions (for API response)
# ---------------------------------------------------------------------------

def get_player_metric_contributions(row: pd.Series, position: str) -> dict:
    """
    Returns {metric_name: weight * z_score} per sub-metric for breakdown display.
    Expects row to have the _*_z columns from compute_outfield_composite.
    """
    if position == "ATT":
        return {
            "goals_assists": round(ATT_WEIGHTS["goals_assists"] * row.get("_goals_assists_z", 0), 3),
            "xg": round(ATT_WEIGHTS["xg"] * row.get("_xg_z", 0), 3),
            "xa": round(ATT_WEIGHTS["xa"] * row.get("_xa_z", 0), 3),
            "dribbles": round(ATT_WEIGHTS["dribbles"] * row.get("_dribbles_z", 0), 3),
            "shots": round(ATT_WEIGHTS["shots"] * row.get("_shots_z", 0), 3),
            "chances_created": round(ATT_WEIGHTS["chances_created"] * row.get("_chances_created_z", 0), 3),
            "recoveries": round(ATT_WEIGHTS["recoveries"] * row.get("_recoveries_z", 0), 3),
        }
    elif position == "MID":
        return {
            "prog_pass": round(MID_WEIGHTS["prog_pass"] * row.get("_prog_pass_z", 0), 3),
            "chances_created": round(MID_WEIGHTS["chances_created"] * row.get("_chances_created_z", 0), 3),
            "xa": round(MID_WEIGHTS["xa"] * row.get("_xa_z", 0), 3),
            "goals_assists": round(MID_WEIGHTS["goals_assists"] * row.get("_goals_assists_z", 0), 3),
            "tackles": round(MID_WEIGHTS["tackles"] * row.get("_tackles_z", 0), 3),
            "interceptions": round(MID_WEIGHTS["interceptions"] * row.get("_interceptions_z", 0), 3),
            "recoveries": round(MID_WEIGHTS["recoveries"] * row.get("_recoveries_z", 0), 3),
        }
    elif position == "DEF":
        return {
            "tackles": round(DEF_WEIGHTS["tackles"] * row.get("_tackles_z", 0), 3),
            "aerials_won": round(DEF_WEIGHTS["aerials_won"] * row.get("_aerials_won_z", 0), 3),
            "clearances": round(DEF_WEIGHTS["clearances"] * row.get("_clearances_z", 0), 3),
            "interceptions": round(DEF_WEIGHTS["interceptions"] * row.get("_interceptions_z", 0), 3),
            "shot_blocks": round(DEF_WEIGHTS["shot_blocks"] * row.get("_shot_blocks_z", 0), 3),
            "prog_pass": round(DEF_WEIGHTS["prog_pass"] * row.get("_prog_pass_z", 0), 3),
        }
    elif position == "GK":
        return {
            "saves": round(GK_WEIGHTS["saves"] * row.get("_saves_z", 0), 3),
            "xgot_faced": round(GK_WEIGHTS["xgot_faced"] * row.get("_xgot_faced_z", 0), 3),
            "diving_saves": round(GK_WEIGHTS["diving_saves"] * row.get("_diving_saves_z", 0), 3),
            "saves_inside_box": round(GK_WEIGHTS["saves_inside_box"] * row.get("_saves_inside_box_z", 0), 3),
            "high_claims": round(GK_WEIGHTS["high_claims"] * row.get("_high_claims_z", 0), 3),
            "sweeper_actions": round(GK_WEIGHTS["sweeper_actions"] * row.get("_sweeper_actions_z", 0), 3),
        }
    return {}


def get_player_raw_stats(row: pd.Series, position: str) -> dict:
    """
    Returns raw (pre-normalisation) stat values for a player row.
    Includes every metric used in the composite formula plus useful
    supplementary stats, with human-readable labels.
    Expects row to have the _* prefixed columns added by _build_*_features.
    """
    def _v(col: str) -> float:
        val = row.get(col, 0)
        try:
            return round(float(val), 2) if val is not None else 0.0
        except (TypeError, ValueError):
            return 0.0

    if position == "GK":
        return {
            "Saves":              _v("_saves"),
            "xGoT Faced":         _v("_xgot_faced"),
            "Diving Saves":       _v("_diving_saves"),
            "Saves Inside Box":   _v("_saves_inside_box"),
            "High Claims":        _v("_high_claims"),
            "Sweeper Actions":    _v("_sweeper_actions"),
            "Minutes Played":     _v("minutes_played"),
        }

    # Shared outfield stats
    shared = {
        "Goals":                _v("_goals_assists") - _v("_xa"),   # rough; use raw col
        "Assists":              _v("assists") if "assists" in row.index else 0.0,
        "Goals + Assists":      _v("_goals_assists"),
        "Expected Goals (xG)":  _v("_xg"),
        "Expected Assists (xA)":_v("_xa"),
        "Successful Dribbles":  _v("_dribbles"),
        "Shots on Target":      _v("_shots"),
        "Chances Created":      _v("_chances_created"),
        "Ball Recoveries":      _v("_recoveries"),
        "Accurate Passes":      _v("_prog_pass"),
        "Tackles":              _v("_tackles"),
        "Interceptions":        _v("_interceptions"),
        "Aerials Won":          _v("_aerials_won"),
        "Clearances":           _v("_clearances"),
        "Shot Blocks":          _v("_shot_blocks"),
        "Minutes Played":       _v("minutes_played"),
    }

    # Keep only the stats relevant to this position at the top, then the rest
    pos_primary = {
        "ATT": ["Goals + Assists", "Expected Goals (xG)", "Expected Assists (xA)",
                "Successful Dribbles", "Shots on Target", "Chances Created",
                "Ball Recoveries", "Minutes Played"],
        "MID": ["Accurate Passes", "Chances Created", "Expected Assists (xA)",
                "Goals + Assists", "Tackles", "Interceptions",
                "Ball Recoveries", "Minutes Played"],
        "DEF": ["Tackles", "Aerials Won", "Clearances", "Interceptions",
                "Shot Blocks", "Accurate Passes", "Minutes Played"],
    }
    order = pos_primary.get(position, list(shared.keys()))
    # Return ordered dict: primary keys first, then any extras
    result = {k: shared[k] for k in order if k in shared}
    for k, v in shared.items():
        if k not in result:
            result[k] = v
    return result


# ---------------------------------------------------------------------------
# High-level pipeline helper
# ---------------------------------------------------------------------------

def build_season_data(
    seasons: list[str],
    outfield_scaler: Optional[StandardScaler] = None,
    gk_scaler: Optional[StandardScaler] = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, StandardScaler, StandardScaler]:
    """
    Load seasons, compute composite scores, derive results, aggregate to team level.
    Returns (match_features, player_scores_full, fixtures_with_results,
             fitted_outfield_scaler, fitted_gk_scaler)
    """
    outfield_df, gk_df, fixtures_df = load_multiple_seasons(seasons)

    # Add season column to fixtures if missing
    if "season" not in fixtures_df.columns:
        fixtures_df["season"] = "unknown"

    # Compute composite scores
    outfield_scored, outfield_scaler = compute_outfield_composite(outfield_df, outfield_scaler)
    gk_scored, gk_scaler = compute_gk_composite(gk_df, gk_scaler)

    # Combine for team aggregation
    # Unify columns needed: match_id, team_id, position_group, composite_score
    player_cols = ["match_id", "team_id", "player_name", "player_id",
                   "team_name", "position_group", "composite_score",
                   "minutes_played", "season"]
    # Some of these may not be in gk scored — add defaults
    for col in player_cols:
        if col not in outfield_scored.columns:
            outfield_scored[col] = None
        if col not in gk_scored.columns:
            gk_scored[col] = None

    all_players = pd.concat(
        [outfield_scored[player_cols], gk_scored[player_cols]],
        ignore_index=True
    )

    # Derive match results from outfield goals only
    fixtures_with_results = derive_match_results(outfield_df, fixtures_df)

    # Aggregate to team level
    match_features = aggregate_to_team(all_players, fixtures_with_results)

    return match_features, all_players, fixtures_with_results, outfield_scaler, gk_scaler
