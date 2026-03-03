import os
import csv
import mysql.connector
from dotenv import load_dotenv

from logger import get_logger

load_dotenv()
logger = get_logger('export_report')

DB_HOST = os.getenv('DB_HOST')
DB_USER = os.getenv('DB_USER')
DB_PASS = os.getenv('DB_PASSWORD')
DB_NAME = os.getenv('DB_NAME')


def export_to_csv(filename: str = 'market_report.csv'):
    """Query the latest snapshots (all assets) and export to CSV."""
    logger.info("Connecting to database for report generation...")

    connection = None
    try:
        connection = mysql.connector.connect(
            host=DB_HOST, user=DB_USER, password=DB_PASS, database=DB_NAME
        )
        cursor = connection.cursor()

        query = """
            SELECT 
                a.name       AS 'Asset',
                s.price_usd  AS 'Price (USD)',
                s.price_change_pct AS 'Change (%%)',
                s.market_cap_usd   AS 'Market Cap',
                s.dominance_pct    AS 'Dominance (%%)',
                s.snapshot_time    AS 'Timestamp'
            FROM market_snapshots s
            JOIN assets a ON s.asset_id = a.asset_id
            ORDER BY s.snapshot_time DESC;
        """

        cursor.execute(query)
        records = cursor.fetchall()
        headers = [col[0] for col in cursor.description]

        with open(filename, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(records)

        logger.info("Report exported to %s (%d rows).", filename, len(records))

    except Exception as e:
        logger.error("Export failed: %s", e)
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()


if __name__ == "__main__":
    export_to_csv()