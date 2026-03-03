import os
import requests
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv

from export_report import export_to_csv
from logger import get_logger

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------
load_dotenv()
logger = get_logger('pipeline')

API_KEY  = os.getenv('BLOCKCHAIR_API_KEY')
DB_HOST  = os.getenv('DB_HOST')
DB_USER  = os.getenv('DB_USER')
DB_PASS  = os.getenv('DB_PASSWORD')
DB_NAME  = os.getenv('DB_NAME')

BASE_URL = "https://api.blockchair.com"

# Each dict maps a Blockchair coin slug to its asset_id in the DB.
# To track a new coin: add a row to `assets` and append here.
ASSETS = [
    {'coin': 'bitcoin',  'asset_id': 1},
    {'coin': 'ethereum', 'asset_id': 2},
]

# ---------------------------------------------------------------------------
# Pipeline helpers
# ---------------------------------------------------------------------------

def fetch_market_data(coin: str) -> dict | None:
    """Fetch live stats from the Blockchair API for a single coin."""
    url = f"{BASE_URL}/{coin}/stats"
    logger.info("Fetching data for %s ...", coin.upper())

    response = requests.get(url, params={'key': API_KEY}, timeout=30)
    if response.status_code != 200:
        logger.error("API returned status %s for %s", response.status_code, coin)
        return None

    data = response.json().get('data')
    if not data:
        logger.error("Empty payload received for %s", coin)
        return None

    return {
        'price':      data['market_price_usd'],
        'market_cap': data['market_cap_usd'],
        'blocks':     data['blocks'],
        'dominance':  data['market_dominance_percentage'],
    }


def store_snapshot(cursor, asset_id: int, market_data: dict):
    """Call the stored procedure to persist a single market snapshot."""
    cursor.callproc('sp_insert_snapshot', (
        asset_id,
        market_data['price'],
        market_data['market_cap'],
        market_data['blocks'],
        market_data['dominance'],
    ))

# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------

def run_pipeline():
    """Fetch data for every tracked asset and store it via stored procedure."""
    connection = None
    try:
        connection = mysql.connector.connect(
            host=DB_HOST, user=DB_USER, password=DB_PASS, database=DB_NAME
        )
        cursor = connection.cursor()

        for asset in ASSETS:
            market_data = fetch_market_data(asset['coin'])
            if market_data is None:
                continue

            store_snapshot(cursor, asset['asset_id'], market_data)
            logger.info(
                "%s snapshot stored — $%s",
                asset['coin'].upper(),
                f"{market_data['price']:,.2f}",
            )

        connection.commit()
        logger.info("All snapshots committed successfully.")

    except Error as e:
        logger.error("Database error: %s", e)
    except Exception as e:
        logger.exception("Unexpected error: %s", e)
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()
            logger.info("MySQL connection closed.")


if __name__ == "__main__":
    run_pipeline()

    logger.info("Generating updated CSV report...")
    export_to_csv()