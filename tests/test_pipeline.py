"""
Unit Tests — Financial Data Pipeline
-------------------------------------
Tests cover:
  • fetch_market_data()  — success, API failure, empty payload
  • store_snapshot()     — correct stored-procedure call
  • run_pipeline()       — end-to-end with mocks (no real API / DB)
"""

from unittest.mock import patch, MagicMock
import pytest

# ---------------------------------------------------------------------------
# fetch_market_data tests
# ---------------------------------------------------------------------------

class TestFetchMarketData:
    """Validate API response parsing without hitting the real endpoint."""

    SAMPLE_RESPONSE = {
        "data": {
            "market_price_usd": 87432.15,
            "market_cap_usd": 1_720_000_000_000,
            "blocks": 890_123,
            "market_dominance_percentage": 61.34,
        }
    }

    @patch("pipeline.requests.get")
    def test_success(self, mock_get):
        """A 200 response returns a correctly shaped dict."""
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: self.SAMPLE_RESPONSE,
        )

        from pipeline import fetch_market_data
        result = fetch_market_data("bitcoin")

        assert result is not None
        assert result["price"] == 87432.15
        assert result["market_cap"] == 1_720_000_000_000
        assert result["blocks"] == 890_123
        assert result["dominance"] == 61.34

    @patch("pipeline.requests.get")
    def test_api_failure_returns_none(self, mock_get):
        """A non-200 status code returns None gracefully."""
        mock_get.return_value = MagicMock(status_code=500)

        from pipeline import fetch_market_data
        assert fetch_market_data("bitcoin") is None

    @patch("pipeline.requests.get")
    def test_empty_payload_returns_none(self, mock_get):
        """A 200 response with empty 'data' key returns None."""
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"data": None},
        )

        from pipeline import fetch_market_data
        assert fetch_market_data("bitcoin") is None


# ---------------------------------------------------------------------------
# store_snapshot tests
# ---------------------------------------------------------------------------

class TestStoreSnapshot:
    """Ensure the stored procedure is called with correct arguments."""

    def test_calls_stored_procedure(self):
        from pipeline import store_snapshot

        mock_cursor = MagicMock()
        market_data = {
            "price": 87432.15,
            "market_cap": 1_720_000_000_000,
            "blocks": 890_123,
            "dominance": 61.34,
        }

        store_snapshot(mock_cursor, asset_id=1, market_data=market_data)

        mock_cursor.callproc.assert_called_once_with(
            "sp_insert_snapshot",
            (1, 87432.15, 1_720_000_000_000, 890_123, 61.34),
        )


# ---------------------------------------------------------------------------
# run_pipeline integration test (fully mocked)
# ---------------------------------------------------------------------------

class TestRunPipeline:
    """End-to-end pipeline test — no real network or database calls."""

    SAMPLE_DATA = {
        "price": 87432.15,
        "market_cap": 1_720_000_000_000,
        "blocks": 890_123,
        "dominance": 61.34,
    }

    @patch("pipeline.mysql.connector.connect")
    @patch("pipeline.fetch_market_data")
    def test_pipeline_commits_on_success(self, mock_fetch, mock_connect):
        """Pipeline should commit after storing all snapshots."""
        mock_fetch.return_value = self.SAMPLE_DATA

        mock_conn = MagicMock()
        mock_conn.is_connected.return_value = True
        mock_connect.return_value = mock_conn

        from pipeline import run_pipeline
        run_pipeline()

        # Should have been called once per tracked asset
        assert mock_fetch.call_count >= 1
        mock_conn.commit.assert_called_once()
        mock_conn.close.assert_called_once()

    @patch("pipeline.mysql.connector.connect")
    @patch("pipeline.fetch_market_data")
    def test_pipeline_skips_failed_fetches(self, mock_fetch, mock_connect):
        """If fetch returns None, store_snapshot should NOT be called."""
        mock_fetch.return_value = None

        mock_conn = MagicMock()
        mock_conn.is_connected.return_value = True
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        from pipeline import run_pipeline
        run_pipeline()

        mock_cursor.callproc.assert_not_called()
