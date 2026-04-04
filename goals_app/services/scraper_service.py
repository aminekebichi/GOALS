"""
scraper_service.py

Fetches Premier League fixture lists (played + upcoming) from FotMob.

Strategy (tried in order):
  1. FotMob internal JSON API  — fast, no HTML parsing
  2. FotMob HTML page          — parses __NEXT_DATA__ script tag
  3. Both attempts use SSL verification disabled as a fallback
     (handles corporate proxies / antivirus MITM interception)
"""

import json
import time
import random
import requests
import urllib3
import pandas as pd
from bs4 import BeautifulSoup

from goals_app.config import FOTMOB_DIR

# Suppress InsecureRequestWarning when verify=False is used
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

LEAGUE_SLUGS = {
    87: "laliga",
    47: "premier-league",
    54: "bundesliga",
}

BASE_URL = "https://www.fotmob.com"

# Mimic a real browser as closely as possible
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,*/*",
    "Accept-Language": "en-US,en;q=0.9",
    # Intentionally omit Accept-Encoding — requests handles gzip/deflate
    # automatically; advertising 'br' (brotli) causes FotMob to respond with
    # brotli-compressed data that requests cannot decompress, garbling the body.
    "Referer": "https://www.fotmob.com/",
}

JSON_HEADERS = {
    "User-Agent": HEADERS["User-Agent"],
    "Accept": "application/json, */*",
    "Referer": "https://www.fotmob.com/",
    "x-mas": "eyJib2R5Ijp7InVybCI6Ii9hcGkvbGVhZ3Vlcz9pZD04NyJ9fQ==",
}


def _season_dir_to_url(season: str) -> str:
    """'2024_2025' -> '2024/2025'"""
    return season.replace("_", "/")


def _get(url: str, headers: dict, verify: bool = False) -> requests.Response:
    """
    GET with a (5s connect, 25s read) timeout split.
    Defaults verify=False to avoid Windows certificate-store hang.
    """
    resp = requests.get(url, headers=headers, timeout=(5, 25), verify=verify)
    resp.raise_for_status()
    return resp


def _try_json_api(league_id: int, season_url: str) -> list[dict] | None:
    """
    Attempt FotMob's internal JSON API endpoint.
    Returns allMatches list or None if unavailable.
    """
    url = f"{BASE_URL}/api/leagues?id={league_id}&season={requests.utils.quote(season_url)}"
    print(f"  [1/2] Trying JSON API: {url}")
    try:
        resp = _get(url, JSON_HEADERS)
        data = resp.json()
        matches = (
            data.get("fixtures", {}).get("allMatches")
            or data.get("allMatches")
            or data.get("matches", {}).get("allMatches")
        )
        if matches:
            return matches
        # API responded but no fixtures key — try without season param
        url_no_season = f"{BASE_URL}/api/leagues?id={league_id}"
        resp2 = _get(url_no_season, JSON_HEADERS)
        data2 = resp2.json()
        matches2 = (
            data2.get("fixtures", {}).get("allMatches")
            or data2.get("allMatches")
        )
        return matches2 or None
    except Exception as e:
        print(f"    JSON API failed: {e}")
    return None


def _try_html_page(league_id: int, season_url: str, slug: str) -> list[dict] | None:
    """
    Fall back to scraping the FotMob HTML fixtures page.
    Extracts allMatches from the embedded __NEXT_DATA__ JSON.
    """
    url = f"{BASE_URL}/leagues/{league_id}/fixtures/{slug}?season={season_url}"
    print(f"  [2/2] Trying HTML page: {url}")
    try:
        resp = _get(url, HEADERS)
        tag = BeautifulSoup(resp.text, "html.parser").find(
            "script", {"id": "__NEXT_DATA__"}
        )
        if not tag:
            print("    __NEXT_DATA__ tag not found in HTML response.")
            return None
        page_props = json.loads(tag.string).get("props", {}).get("pageProps", {})
        matches = (
            page_props.get("fixtures", {}).get("allMatches")
            or page_props.get("allMatches")
            or page_props.get("initialProps", {}).get("allMatches")
        )
        return matches or None
    except Exception as e:
        print(f"    HTML page failed: {e}")
    return None


def scrape_fixtures(league_id: int = 47, season: str = "2024_2025") -> pd.DataFrame:
    """
    Fetch all fixtures (played + upcoming) for a league/season from FotMob.

    Saves data/{league_id}/{season}/output/fixtures.parquet
    Returns the fixtures DataFrame.

    Columns: match_id, round, page_url, match_date, finished,
             home_team, home_id, away_team, away_id
    """
    slug = LEAGUE_SLUGS.get(league_id, "premier-league")
    season_url = _season_dir_to_url(season)

    # --- Try JSON API first, then HTML fallback ---
    all_matches = _try_json_api(league_id, season_url)
    if not all_matches:
        time.sleep(random.uniform(1.0, 2.0))
        all_matches = _try_html_page(league_id, season_url, slug)

    if not all_matches:
        raise RuntimeError(
            f"Could not fetch fixtures for league={league_id} season={season}.\n"
            "Both JSON API and HTML scraping failed.\n"
            "FotMob may be blocking requests or their page structure changed.\n"
            "Try opening the following URL in your browser and checking it loads:\n"
            f"  {BASE_URL}/leagues/{league_id}/fixtures/{slug}?season={season_url}"
        )

    rows = []
    for m in all_matches:
        status = m.get("status", {})
        home = m.get("home", {})
        away = m.get("away", {})
        rows.append({
            "match_id":   m.get("id"),
            "round":      m.get("round"),
            "page_url":   m.get("pageUrl", ""),
            "match_date": status.get("utcTime", ""),
            "finished":   bool(status.get("finished", False)),
            "home_team":  home.get("name", ""),
            "home_id":    home.get("id"),
            "away_team":  away.get("name", ""),
            "away_id":    away.get("id"),
        })

    df = pd.DataFrame(rows)
    df["match_date"] = pd.to_datetime(df["match_date"], utc=True, errors="coerce")

    out_dir = FOTMOB_DIR / season / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "fixtures.parquet"
    df.to_parquet(out_path, index=False)

    played   = int(df["finished"].sum())
    upcoming = int((~df["finished"]).sum())
    print(f"Saved {len(df)} fixtures to {out_path}")
    print(f"  {played} played  |  {upcoming} upcoming")

    return df
