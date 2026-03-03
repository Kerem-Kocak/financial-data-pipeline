"""
Unit Tests — CSV Export Module
-------------------------------
Tests cover:
  • CSV file creation with correct headers and rows
  • Graceful handling of database errors
"""

from unittest.mock import patch, MagicMock
import csv
import os
import pytest


class TestExportToCsv:
    """Validate CSV export logic with a mocked database connection."""

    SAMPLE_ROWS = [
        ("Bitcoin",  87432.15, 2.5,  1_720_000_000_000, 61.34, "2026-03-04 12:00:00"),
        ("Ethereum", 3215.42,  -1.2, 385_000_000_000,   17.89, "2026-03-04 12:00:00"),
    ]

    COLUMN_DESCRIPTIONS = [
        ("Asset",),
        ("Price (USD)",),
        ("Change (%)",),
        ("Market Cap",),
        ("Dominance (%)",),
        ("Timestamp",),
    ]

    @patch("export_report.mysql.connector.connect")
    def test_csv_file_created_with_correct_data(self, mock_connect, tmp_path):
        """Export should write headers + data rows to the target CSV."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = self.SAMPLE_ROWS
        mock_cursor.description = self.COLUMN_DESCRIPTIONS

        mock_conn = MagicMock()
        mock_conn.is_connected.return_value = True
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        output_file = str(tmp_path / "test_report.csv")

        from export_report import export_to_csv
        export_to_csv(filename=output_file)

        assert os.path.exists(output_file)

        with open(output_file, newline='', encoding='utf-8') as f:
            reader = list(csv.reader(f))

        # Header row
        assert reader[0] == ["Asset", "Price (USD)", "Change (%)",
                             "Market Cap", "Dominance (%)", "Timestamp"]
        # Data rows
        assert len(reader) == 3  # 1 header + 2 data rows
        assert reader[1][0] == "Bitcoin"
        assert reader[2][0] == "Ethereum"

    @patch("export_report.mysql.connector.connect")
    def test_handles_db_error_gracefully(self, mock_connect):
        """Export should not raise if the database connection fails."""
        mock_connect.side_effect = Exception("Connection refused")

        from export_report import export_to_csv
        # Should not raise
        export_to_csv(filename="should_not_exist.csv")

        assert not os.path.exists("should_not_exist.csv")
