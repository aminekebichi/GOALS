"""
Shared pytest fixtures for the GOALS test suite.

All fixtures are purely in-memory — no parquet files or trained models required.
"""

import numpy as np
import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# Outfield player DataFrame (2 matches, 2 teams, 10 players each match)
# ---------------------------------------------------------------------------

@pytest.fixture
def outfield_df():
    """
    20 rows: 2 matches × 2 teams × 5 players each.
    Covers all three outfield positions (DEF=1, MID=2, ATT=3).
    """
    rng = np.random.default_rng(42)
    n = 20
    return pd.DataFrame({
        "match_id":                         np.repeat([1, 2], n // 2),
        "team_id":                          np.tile([10, 10, 10, 20, 20], 4)[:n],
        "player_id":                        np.arange(n),
        "player_name":                      [f"Player_{i}" for i in range(n)],
        "team_name":                        np.tile(["TeamA", "TeamA", "TeamA", "TeamB", "TeamB"], 4)[:n],
        "position_id":                      np.tile([1.0, 2.0, 3.0, 2.0, 1.0], 4)[:n],
        "minutes_played":                   rng.integers(60, 90, n),
        "goals":                            rng.integers(0, 3, n).astype(float),
        "assists":                          rng.integers(0, 2, n).astype(float),
        "expected_goals":                   rng.uniform(0.0, 1.5, n),
        "expected_assists":                 rng.uniform(0.0, 0.8, n),
        "dribbles_succeeded":               rng.integers(0, 6, n).astype(float),
        "ShotsOnTarget":                    rng.integers(0, 5, n).astype(float),
        "chances_created":                  rng.integers(0, 4, n).astype(float),
        "recoveries":                       rng.integers(0, 12, n).astype(float),
        "accurate_passes":                  rng.integers(10, 70, n).astype(float),
        "matchstats.headers.tackles":       rng.integers(0, 6, n).astype(float),
        "interceptions":                    rng.integers(0, 5, n).astype(float),
        "aerials_won":                      rng.integers(0, 6, n).astype(float),
        "clearances":                       rng.integers(0, 8, n).astype(float),
        "shot_blocks":                      rng.integers(0, 4, n).astype(float),
    })


@pytest.fixture
def gk_df():
    """4 rows: 2 matches × 2 teams × 1 GK each."""
    rng = np.random.default_rng(7)
    n = 4
    return pd.DataFrame({
        "match_id":                             [1, 1, 2, 2],
        "team_id":                              [10, 20, 10, 20],
        "player_id":                            [200, 201, 200, 201],
        "player_name":                          ["GK_A", "GK_B", "GK_A", "GK_B"],
        "team_name":                            ["TeamA", "TeamB", "TeamA", "TeamB"],
        "minutes_played":                       [90, 90, 90, 90],
        "saves":                                rng.integers(1, 8, n).astype(float),
        "expected_goals_on_target_faced":       rng.uniform(0.5, 2.5, n),
        "keeper_diving_save":                   rng.integers(0, 3, n).astype(float),
        "saves_inside_box":                     rng.integers(0, 5, n).astype(float),
        "keeper_high_claim":                    rng.integers(0, 3, n).astype(float),
        "keeper_sweeper":                       rng.integers(0, 2, n).astype(float),
    })


@pytest.fixture
def fixtures_df():
    """2 fixtures matching the outfield/gk DataFrames above."""
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
# Deterministic goal scenario (makes W/D/L assertions exact)
# ---------------------------------------------------------------------------

@pytest.fixture
def goals_outfield_df():
    """
    Match 1: TeamA scores 2, TeamB scores 1  → home WIN
    Match 2: TeamA scores 1, TeamB scores 1  → DRAW
    """
    return pd.DataFrame({
        "match_id": [1, 1, 2, 2],
        "team_id":  [10, 20, 10, 20],
        "goals":    [2.0, 1.0, 1.0, 1.0],
    })


@pytest.fixture
def goals_fixtures_df():
    return pd.DataFrame({
        "match_id": [1, 2],
        "home_id":  [10, 20],
        "away_id":  [20, 10],
    })
