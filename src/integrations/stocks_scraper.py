"""
Stocks Scraper - S&P 500 Earnings
==================================

Scrapes S&P 500 stocks list and earnings dates/price targets from stockanalysis.com.
"""

import os
import sqlite3
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
from typing import Optional, List, Dict, Any

from src.utils import get_logger

logger = get_logger(__name__)

# Default database path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "gielda_earning.db")


class StocksScraper:
    """
    Scraper for S&P 500 stock data and earnings.
    """
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or DB_PATH
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    def scrape_sp500_list(self) -> pd.DataFrame:
        """Get the list of S&P 500 stocks from stockanalysis.com."""
        url = 'https://stockanalysis.com/list/sp-500-stocks/'
        logger.info(f"Fetching S&P 500 list from {url}")
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            table_body = soup.select_one('#main-table > tbody')
            if not table_body:
                logger.error("Could not find S&P 500 table body")
                return pd.DataFrame()
            
            rows = table_body.find_all('tr')
            container = []
            for row in rows:
                cells = row.find_all('td')
                clean_row = [td.text.strip() for td in cells]
                container.append(clean_row)
            
            column_names = ['nr', 'ticker', 'company_name', 'market_cap', 'price', 'change_pct', 'revenue']
            df = pd.DataFrame(container, columns=column_names)
            
            # Add link to stock page
            df['link'] = df['ticker'].apply(lambda x: f'https://stockanalysis.com/stocks/{x.lower()}/')
            
            return df
        except Exception as e:
            logger.error(f"Error scraping S&P 500 list: {e}")
            return pd.DataFrame()

    def scrape_stock_overview(self, ticker: str) -> Dict[str, Any]:
        """Get earnings date and price target for a specific ticker."""
        url = f'https://stockanalysis.com/stocks/{ticker.lower()}/'
        # logger.debug(f"Fetching overview for {ticker}")
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            tables = soup.find_all('table')
            if len(tables) < 2:
                return {}
            
            rows = tables[1].find_all('tr')
            results = {}
            
            # Market data from overview table
            # Row mapping (based on previous script logic):
            # 6: Analysts, 7: Price Target, 8: Earnings Date
            
            # Price Target
            if len(rows) > 7:
                cells = rows[7].find_all('td')
                if len(cells) >= 2:
                    results["Price Target"] = cells[1].text.strip()
            
            # Analyst Rating
            if len(rows) > 6:
                cells = rows[6].find_all('td')
                if len(cells) >= 2:
                    results["analysts"] = cells[1].text.strip()
            
            # Earnings Date
            if len(rows) > 8:
                cells = rows[8].find_all('td')
                if len(cells) >= 2:
                    date_str = cells[1].text.strip()
                    try:
                        # Feb 25, 2026 -> 2026-02-25
                        date_obj = datetime.strptime(date_str, '%b %d, %Y')
                        results["Earnings Date"] = date_obj.strftime('%Y-%m-%d')
                    except:
                        results["Earnings Date"] = date_str
            
            return results
        except Exception as e:
            # logger.error(f"Error scraping {ticker}: {e}")
            return {}

    def run(self, limit: Optional[int] = None) -> pd.DataFrame:
        """Main execution method."""
        logger.info("Starting S&P 500 data refresh...")
        df_sp500 = self.scrape_sp500_list()
        
        if df_sp500.empty:
            return pd.DataFrame()
        
        if limit:
            df_sp500 = df_sp500.head(limit)
        
        tickers = df_sp500['ticker'].tolist()
        overviews = []
        
        total = len(tickers)
        for i, ticker in enumerate(tickers, 1):
            if i % 10 == 0:
                logger.info(f"Progress: {i}/{total} stocks processed...")
            
            data = self.scrape_stock_overview(ticker)
            overviews.append(data)
            # time.sleep(0.1) # Be nice
            
        df_overview = pd.DataFrame(overviews)
        df_final = pd.concat([df_sp500, df_overview], axis=1)
        
        # Save to DB
        try:
            conn = sqlite3.connect(self.db_path)
            df_final.to_sql('sp500_earning', conn, if_exists='replace', index=False)
            conn.close()
            logger.info(f"Saved {len(df_final)} stocks to {self.db_path}")
        except Exception as e:
            logger.error(f"Error saving stocks to DB: {e}")
            
        return df_final


if __name__ == "__main__":
    scraper = StocksScraper()
    # Test with 10 stocks
    df = scraper.run(limit=10)
    print(df)
