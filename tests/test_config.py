"""
tests/test_config.py

Unit tests for goals_app/config.py.
These tests validate the constants that drive the entire ML pipeline:
wrong seasons or position maps would silently break training.
"""

from pathlib import Path

import pytest

from goals_app.config import (
    ARTIFACTS_DIR,
    DATA_ROOT,
    FOTMOB_DIR,
    POSITION_MAP,
    TEST_SEASON,
    TRAIN_SEASONS,
)


# ---------------------------------------------------------------------------
# Path sanity
# ---------------------------------------------------------------------------

class TestPaths:
    def test_data_root_is_path(self):
        assert isinstance(DATA_ROOT, Path)

    def test_artifacts_dir_is_path(self):
        assert isinstance(ARTIFACTS_DIR, Path)

    def test_fotmob_dir_is_under_data_root(self):
        assert str(DATA_ROOT) in str(FOTMOB_DIR)

    def test_artifacts_dir_contains_ml(self):
        """Artifacts must live inside goals_app/ml/ so they stay git-ignored."""
        assert "ml" in ARTIFACTS_DIR.parts


# ---------------------------------------------------------------------------
# Season lists
# ---------------------------------------------------------------------------

class TestSeasons:
    def test_train_seasons_has_three_entries(self):
        assert len(TRAIN_SEASONS) == 3

    def test_train_seasons_are_strings(self):
        assert all(isinstance(s, str) for s in TRAIN_SEASONS)

    def test_train_season_format(self):
        """Seasons must use underscore separator, e.g. '2021_2022'."""
        for season in TRAIN_SEASONS:
            assert "_" in season, f"Season {season!r} missing underscore separator"

    def test_test_season_not_in_train_seasons(self):
        """Test season must be held out — never used for fitting."""
        assert TEST_SEASON not in TRAIN_SEASONS

    def test_train_seasons_are_chronologically_ordered(self):
        assert TRAIN_SEASONS == sorted(TRAIN_SEASONS)

    def test_seasons_are_unique(self):
        assert len(TRAIN_SEASONS) == len(set(TRAIN_SEASONS))


# ---------------------------------------------------------------------------
# Position map
# ---------------------------------------------------------------------------

class TestPositionMap:
    def test_all_position_ids_present(self):
        """FotMob uses position_ids 1, 2, 3, 11."""
        assert set(POSITION_MAP.keys()) == {1, 2, 3, 11}

    def test_position_map_values(self):
        assert POSITION_MAP[1] == "DEF"
        assert POSITION_MAP[2] == "MID"
        assert POSITION_MAP[3] == "ATT"
        assert POSITION_MAP[11] == "GK"

    def test_position_map_values_are_strings(self):
        assert all(isinstance(v, str) for v in POSITION_MAP.values())

    def test_position_map_has_four_groups(self):
        assert len(set(POSITION_MAP.values())) == 4
