#!/usr/bin/env python
"""
scrape_fixtures.py — Fetch Premier League fixture list from FotMob.

Saves all matches (played + upcoming) for a season to:
  data/47/{season}/output/fixtures.parquet

This is a lightweight scrape — player stats are NOT fetched here.
Run fotmob_final.ipynb to collect per-match player data.

Usage:
    python scrape_fixtures.py                         # 2025/26 Premier League (current season)
    python scrape_fixtures.py --season 2024_2025
    python scrape_fixtures.py --league 47 --season 2025_2026
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from goals_app.services.scraper_service import scrape_fixtures


def main():
    parser = argparse.ArgumentParser(
        description="Scrape Premier League fixture list from FotMob"
    )
    parser.add_argument(
        "--league", type=int, default=47,
        help="FotMob league ID (default: 47 = Premier League)",
    )
    parser.add_argument(
        "--season", default="2025_2026",
        help="Season in YYYY_YYYY format (default: 2025_2026)",
    )
    args = parser.parse_args()

    print("=" * 55)
    print("GOALS — Fixture Scraper")
    print("=" * 55)
    print(f"League : {args.league}")
    print(f"Season : {args.season}")
    print()

    try:
        df = scrape_fixtures(league_id=args.league, season=args.season)
    except Exception as e:
        print(f"\nERROR: {e}")
        sys.exit(1)

    print()
    print("=" * 55)
    print("Done. Run the calendar to see upcoming fixtures:")
    print("  uvicorn goals_app.main:app --host 127.0.0.1 --port 8000 --reload")
    print("=" * 55)

    # Preview upcoming matches
    upcoming = df[~df["finished"]].sort_values("match_date").head(5)
    if not upcoming.empty:
        print("\nNext fixtures:")
        for _, row in upcoming.iterrows():
            date = str(row["match_date"])[:10] if row["match_date"] is not None else "TBD"
            print(f"  Rd {str(row['round']).rjust(2)}  {date}  "
                  f"{row['home_team']} vs {row['away_team']}")


if __name__ == "__main__":
    main()
