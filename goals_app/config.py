from pathlib import Path

DATA_ROOT = Path(__file__).parent.parent / "data"
ARTIFACTS_DIR = Path(__file__).parent / "ml" / "artifacts"

TRAIN_SEASONS = ["2021_2022", "2022_2023", "2023_2024"]
TEST_SEASON = "2024_2025"

# Supported FotMob leagues
LEAGUE_MAP = {
    47: {"name": "Premier League", "slug": "premier-league"},
    87: {"name": "La Liga",        "slug": "laliga"},
}
DEFAULT_LEAGUE_ID = 47

# Per-league FotMob data directories
FOTMOB_DIRS = {league_id: DATA_ROOT / str(league_id) for league_id in LEAGUE_MAP}

# Convenience alias — points to the default league
FOTMOB_DIR = FOTMOB_DIRS[DEFAULT_LEAGUE_ID]

# FotMob position_id → composite score group
# Verified against actual parquet data:
#   1 = DEF (defenders/fullbacks)
#   2 = MID (midfielders)
#   3 = ATT (forwards/attackers)
#   11 = GK (goalkeepers, separate parquet)
POSITION_MAP = {
    1: "DEF",
    2: "MID",
    3: "ATT",
    11: "GK",
}
