"""
tests/test_scraper_service.py

Unit tests for goals_app/services/scraper_service.py.

All HTTP calls are mocked — these tests never hit FotMob.
Topics covered:
  - _season_dir_to_url  (string conversion)
  - _get                (HTTP wrapper)
  - _try_json_api       (JSON API path + fallback without season param)
  - _try_html_page      (HTML scraping + BeautifulSoup extraction)
  - scrape_fixtures     (end-to-end: JSON path, HTML fallback, error, parquet output)
"""

import json
from unittest.mock import MagicMock, patch, call

import pandas as pd
import pytest
import requests

from goals_app.services.scraper_service import (
    BASE_URL,
    LEAGUE_SLUGS,
    _get,
    _season_dir_to_url,
    _try_html_page,
    _try_json_api,
    scrape_fixtures,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_response(json_data=None, text="", status_code=200):
    """Build a MagicMock that behaves like a requests.Response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text
    if json_data is not None:
        resp.json.return_value = json_data
    resp.raise_for_status.return_value = None
    return resp


def _sample_matches():
    return [
        {
            "id": 1001,
            "round": 1,
            "pageUrl": "/match/1001",
            "status": {"utcTime": "2024-08-18T15:00:00+00:00", "finished": True},
            "home": {"name": "Real Madrid", "id": 10},
            "away": {"name": "Barcelona", "id": 20},
        },
        {
            "id": 1002,
            "round": 2,
            "pageUrl": "/match/1002",
            "status": {"utcTime": "2024-08-25T15:00:00+00:00", "finished": False},
            "home": {"name": "Barcelona", "id": 20},
            "away": {"name": "Real Madrid", "id": 10},
        },
    ]


def _make_next_data_html(matches: list) -> str:
    """Wrap matches in a minimal __NEXT_DATA__ HTML page."""
    next_data = json.dumps({
        "props": {
            "pageProps": {
                "fixtures": {"allMatches": matches}
            }
        }
    })
    return f'<html><body><script id="__NEXT_DATA__">{next_data}</script></body></html>'


# ---------------------------------------------------------------------------
# _season_dir_to_url
# ---------------------------------------------------------------------------

class TestSeasonDirToUrl:
    def test_converts_underscore_to_slash(self):
        assert _season_dir_to_url("2024_2025") == "2024/2025"

    def test_converts_older_season(self):
        assert _season_dir_to_url("2021_2022") == "2021/2022"

    def test_no_underscore_returned_unchanged(self):
        assert _season_dir_to_url("2024") == "2024"


# ---------------------------------------------------------------------------
# _get (HTTP wrapper)
# ---------------------------------------------------------------------------

class TestGet:
    def test_returns_response_on_success(self):
        mock_resp = _mock_response(json_data={"ok": True})
        with patch("goals_app.services.scraper_service.requests.get", return_value=mock_resp):
            result = _get("https://example.com", {})
        assert result is mock_resp

    def test_calls_raise_for_status(self):
        mock_resp = _mock_response()
        with patch("goals_app.services.scraper_service.requests.get", return_value=mock_resp):
            _get("https://example.com", {})
        mock_resp.raise_for_status.assert_called_once()

    def test_raises_http_error_on_bad_status(self):
        mock_resp = _mock_response()
        mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError("404")
        with patch("goals_app.services.scraper_service.requests.get", return_value=mock_resp):
            with pytest.raises(requests.exceptions.HTTPError):
                _get("https://example.com", {})

    def test_passes_timeout_to_requests(self):
        mock_resp = _mock_response()
        with patch(
            "goals_app.services.scraper_service.requests.get", return_value=mock_resp
        ) as mock_get:
            _get("https://example.com", {"X-Test": "1"})
        _, kwargs = mock_get.call_args
        assert "timeout" in kwargs


# ---------------------------------------------------------------------------
# _try_json_api
# ---------------------------------------------------------------------------

class TestTryJsonApi:
    def test_returns_matches_from_fixtures_key(self):
        matches = _sample_matches()
        mock_resp = _mock_response(json_data={"fixtures": {"allMatches": matches}})
        with patch("goals_app.services.scraper_service.requests.get", return_value=mock_resp):
            result = _try_json_api(87, "2024/2025")
        assert result == matches

    def test_returns_matches_from_allMatches_key(self):
        matches = _sample_matches()
        mock_resp = _mock_response(json_data={"allMatches": matches})
        with patch("goals_app.services.scraper_service.requests.get", return_value=mock_resp):
            result = _try_json_api(87, "2024/2025")
        assert result == matches

    def test_returns_matches_from_matches_allMatches_key(self):
        matches = _sample_matches()
        mock_resp = _mock_response(json_data={"matches": {"allMatches": matches}})
        with patch("goals_app.services.scraper_service.requests.get", return_value=mock_resp):
            result = _try_json_api(87, "2024/2025")
        assert result == matches

    def test_falls_back_to_no_season_param_when_empty_response(self):
        """If first response has no fixtures, a second request without season is made."""
        matches = _sample_matches()
        resp_empty = _mock_response(json_data={})
        resp_with  = _mock_response(json_data={"allMatches": matches})
        with patch(
            "goals_app.services.scraper_service.requests.get",
            side_effect=[resp_empty, resp_with],
        ):
            result = _try_json_api(87, "2024/2025")
        assert result == matches

    def test_returns_none_on_network_exception(self):
        with patch(
            "goals_app.services.scraper_service.requests.get",
            side_effect=requests.exceptions.ConnectionError("down"),
        ):
            result = _try_json_api(87, "2024/2025")
        assert result is None

    def test_returns_none_when_both_responses_empty(self):
        resp_empty = _mock_response(json_data={})
        with patch(
            "goals_app.services.scraper_service.requests.get",
            side_effect=[resp_empty, resp_empty],
        ):
            result = _try_json_api(87, "2024/2025")
        assert result is None


# ---------------------------------------------------------------------------
# _try_html_page
# ---------------------------------------------------------------------------

class TestTryHtmlPage:
    def test_returns_matches_from_next_data(self):
        matches = _sample_matches()
        mock_resp = _mock_response(text=_make_next_data_html(matches))
        with patch("goals_app.services.scraper_service.requests.get", return_value=mock_resp):
            result = _try_html_page(87, "2024/2025", "laliga")
        assert result == matches

    def test_returns_none_when_no_next_data_tag(self):
        mock_resp = _mock_response(text="<html><body><p>No data here</p></body></html>")
        with patch("goals_app.services.scraper_service.requests.get", return_value=mock_resp):
            result = _try_html_page(87, "2024/2025", "laliga")
        assert result is None

    def test_returns_none_on_network_exception(self):
        with patch(
            "goals_app.services.scraper_service.requests.get",
            side_effect=Exception("network error"),
        ):
            result = _try_html_page(87, "2024/2025", "laliga")
        assert result is None

    def test_returns_none_when_next_data_has_no_fixtures(self):
        next_data = json.dumps({"props": {"pageProps": {}}})
        html = f'<html><body><script id="__NEXT_DATA__">{next_data}</script></body></html>'
        mock_resp = _mock_response(text=html)
        with patch("goals_app.services.scraper_service.requests.get", return_value=mock_resp):
            result = _try_html_page(87, "2024/2025", "laliga")
        assert result is None

    def test_uses_correct_url_format(self):
        mock_resp = _mock_response(text="<html></html>")
        with patch(
            "goals_app.services.scraper_service.requests.get", return_value=mock_resp
        ) as mock_get:
            _try_html_page(87, "2024/2025", "laliga")
        called_url = mock_get.call_args[0][0]
        assert "leagues/87" in called_url
        assert "laliga" in called_url


# ---------------------------------------------------------------------------
# scrape_fixtures (end-to-end)
# ---------------------------------------------------------------------------

class TestScrapeFixtures:
    def test_returns_dataframe(self, tmp_path):
        matches = _sample_matches()
        with (
            patch("goals_app.services.scraper_service._try_json_api", return_value=matches),
            patch("goals_app.services.scraper_service.FOTMOB_DIR", tmp_path),
        ):
            result = scrape_fixtures(87, "2024_2025")
        assert isinstance(result, pd.DataFrame)

    def test_correct_row_count(self, tmp_path):
        matches = _sample_matches()
        with (
            patch("goals_app.services.scraper_service._try_json_api", return_value=matches),
            patch("goals_app.services.scraper_service.FOTMOB_DIR", tmp_path),
        ):
            result = scrape_fixtures(87, "2024_2025")
        assert len(result) == len(matches)

    def test_has_required_columns(self, tmp_path):
        matches = _sample_matches()
        with (
            patch("goals_app.services.scraper_service._try_json_api", return_value=matches),
            patch("goals_app.services.scraper_service.FOTMOB_DIR", tmp_path),
        ):
            result = scrape_fixtures(87, "2024_2025")
        required = {"match_id", "round", "match_date", "finished",
                    "home_team", "away_team", "home_id", "away_id"}
        assert required.issubset(set(result.columns))

    def test_saves_parquet_file(self, tmp_path):
        matches = _sample_matches()
        with (
            patch("goals_app.services.scraper_service._try_json_api", return_value=matches),
            patch("goals_app.services.scraper_service.FOTMOB_DIR", tmp_path),
        ):
            scrape_fixtures(87, "2024_2025")
        parquet_path = tmp_path / "2024_2025" / "output" / "fixtures.parquet"
        assert parquet_path.exists()

    def test_saved_parquet_is_readable(self, tmp_path):
        matches = _sample_matches()
        with (
            patch("goals_app.services.scraper_service._try_json_api", return_value=matches),
            patch("goals_app.services.scraper_service.FOTMOB_DIR", tmp_path),
        ):
            scrape_fixtures(87, "2024_2025")
        parquet_path = tmp_path / "2024_2025" / "output" / "fixtures.parquet"
        loaded = pd.read_parquet(parquet_path)
        assert len(loaded) == len(matches)

    def test_finished_flag_correct(self, tmp_path):
        matches = _sample_matches()
        with (
            patch("goals_app.services.scraper_service._try_json_api", return_value=matches),
            patch("goals_app.services.scraper_service.FOTMOB_DIR", tmp_path),
        ):
            result = scrape_fixtures(87, "2024_2025")
        assert result["finished"].iloc[0] == True
        assert result["finished"].iloc[1] == False

    def test_team_names_extracted(self, tmp_path):
        matches = _sample_matches()
        with (
            patch("goals_app.services.scraper_service._try_json_api", return_value=matches),
            patch("goals_app.services.scraper_service.FOTMOB_DIR", tmp_path),
        ):
            result = scrape_fixtures(87, "2024_2025")
        assert "Real Madrid" in result["home_team"].values
        assert "Barcelona" in result["away_team"].values

    def test_uses_html_fallback_when_json_fails(self, tmp_path):
        matches = _sample_matches()
        with (
            patch("goals_app.services.scraper_service._try_json_api", return_value=None),
            patch("goals_app.services.scraper_service._try_html_page", return_value=matches),
            patch("goals_app.services.scraper_service.time.sleep"),
            patch("goals_app.services.scraper_service.FOTMOB_DIR", tmp_path),
        ):
            result = scrape_fixtures(87, "2024_2025")
        assert len(result) == len(matches)

    def test_sleep_called_between_json_and_html_fallback(self, tmp_path):
        matches = _sample_matches()
        with (
            patch("goals_app.services.scraper_service._try_json_api", return_value=None),
            patch("goals_app.services.scraper_service._try_html_page", return_value=matches),
            patch("goals_app.services.scraper_service.time.sleep") as mock_sleep,
            patch("goals_app.services.scraper_service.FOTMOB_DIR", tmp_path),
        ):
            scrape_fixtures(87, "2024_2025")
        mock_sleep.assert_called_once()

    def test_raises_runtime_error_when_both_sources_fail(self, tmp_path):
        with (
            patch("goals_app.services.scraper_service._try_json_api", return_value=None),
            patch("goals_app.services.scraper_service._try_html_page", return_value=None),
            patch("goals_app.services.scraper_service.time.sleep"),
            patch("goals_app.services.scraper_service.FOTMOB_DIR", tmp_path),
        ):
            with pytest.raises(RuntimeError, match="Could not fetch fixtures"):
                scrape_fixtures(87, "2024_2025")

    def test_uses_laliga_slug_for_league_87(self, tmp_path):
        matches = _sample_matches()
        with (
            patch("goals_app.services.scraper_service._try_json_api", return_value=matches) as mock_json,
            patch("goals_app.services.scraper_service.FOTMOB_DIR", tmp_path),
        ):
            scrape_fixtures(87, "2024_2025")
        mock_json.assert_called_once_with(87, "2024/2025")

    def test_unknown_league_defaults_to_laliga_slug(self, tmp_path):
        """LEAGUE_SLUGS.get(999, 'laliga') should fall back to 'laliga'."""
        matches = _sample_matches()
        with (
            patch("goals_app.services.scraper_service._try_json_api", return_value=None),
            patch("goals_app.services.scraper_service._try_html_page", return_value=matches) as mock_html,
            patch("goals_app.services.scraper_service.time.sleep"),
            patch("goals_app.services.scraper_service.FOTMOB_DIR", tmp_path),
        ):
            scrape_fixtures(999, "2024_2025")
        # slug arg to _try_html_page should be "laliga" (the default fallback)
        _, _, slug = mock_html.call_args[0]
        assert slug == "laliga"

    def test_match_date_is_datetime(self, tmp_path):
        matches = _sample_matches()
        with (
            patch("goals_app.services.scraper_service._try_json_api", return_value=matches),
            patch("goals_app.services.scraper_service.FOTMOB_DIR", tmp_path),
        ):
            result = scrape_fixtures(87, "2024_2025")
        assert pd.api.types.is_datetime64_any_dtype(result["match_date"])

    # ------------------------------------------------------------------
    # TDD — RED: features that should exist but don't yet
    # ------------------------------------------------------------------

    def test_home_id_and_away_id_are_numeric(self, tmp_path):
        """
        home_id and away_id should be stored as integers so they can be
        joined to player parquets on team_id without casting.

        Currently scrape_fixtures stores them as  str(home.get("id", ""))
        which causes silent type mismatches in feature_service joins.

        FIX: in scraper_service.py change:
               "home_id": str(home.get("id", "")),
               "away_id": str(away.get("id", "")),
             to:
               "home_id": home.get("id"),
               "away_id": away.get("id"),
        """
        matches = _sample_matches()
        with (
            patch("goals_app.services.scraper_service._try_json_api", return_value=matches),
            patch("goals_app.services.scraper_service.FOTMOB_DIR", tmp_path),
        ):
            result = scrape_fixtures(87, "2024_2025")
        assert pd.api.types.is_integer_dtype(result["home_id"]), (
            f"home_id dtype is {result['home_id'].dtype} — expected integer"
        )
        assert pd.api.types.is_integer_dtype(result["away_id"]), (
            f"away_id dtype is {result['away_id'].dtype} — expected integer"
        )


# ---------------------------------------------------------------------------
# LEAGUE_SLUGS constant
# ---------------------------------------------------------------------------

class TestLeagueSlugs:
    def test_laliga_id_present(self):
        assert 87 in LEAGUE_SLUGS

    def test_premier_league_id_present(self):
        assert 47 in LEAGUE_SLUGS

    def test_bundesliga_id_present(self):
        assert 54 in LEAGUE_SLUGS

    def test_laliga_slug_value(self):
        assert LEAGUE_SLUGS[87] == "laliga"
