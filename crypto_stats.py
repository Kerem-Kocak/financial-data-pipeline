import os
import requests
from datetime import datetime
from dotenv import load_dotenv

from logger import get_logger

# Load credentials securely — never hardcode keys
load_dotenv()
logger = get_logger('crypto_stats')

API_KEY = os.getenv('BLOCKCHAIR_API_KEY')
COIN = 'bitcoin'
URL = f"https://api.blockchair.com/{COIN}/stats"

def fetch_market_data():
    logger.info("Fetching data for %s ...", COIN.upper())
    
    try:
        response = requests.get(URL, params={'key': API_KEY}, timeout=30)
        
        if response.status_code == 200:
            stats = response.json()['data']
            
            price     = stats['market_price_usd']
            market_cap = stats['market_cap_usd']
            blocks    = stats['blocks']
            dominance = stats['market_dominance_percentage']
            
            logger.info("Current Price:    $%s",  f"{price:,.2f}")
            logger.info("Market Cap:       $%s",  f"{market_cap:,.0f}")
            logger.info("Total Blocks:     %s",   f"{blocks:,}")
            logger.info("Market Dominance: %s%%", dominance)
            logger.info("Timestamp:        %s",   datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        else:
            logger.error("API returned status code %s", response.status_code)
            
    except Exception as e:
        logger.exception("An error occurred: %s", e)

if __name__ == "__main__":
    fetch_market_data()