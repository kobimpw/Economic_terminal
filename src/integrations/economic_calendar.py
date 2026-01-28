"""
Economic Calendar Scraper - Trading Economics
==============================================

Module for scraping economic calendar from TradingEconomics.com.
Uses Selenium to handle dynamic pages and extract data.

This version uses the improved logic from TE.py but wrapped in a class.
"""

import os
import re
import sqlite3
import time
from datetime import datetime, timedelta
from typing import Optional, Tuple

import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from src.utils import get_logger

logger = get_logger(__name__)

# Default database path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "economic_calendar.db")


class EconomicCalendarScraper:
    """
    Scraper for economic calendar from TradingEconomics.com.
    """
    
    def __init__(self, db_path: Optional[str] = None, headless: bool = True):
        self.db_path = db_path or DB_PATH
        self.headless = headless
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
    
    def _setup_driver(self) -> webdriver.Chrome:
        """Configure Chrome browser."""
        options = Options()
        if self.headless:
            options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )
        return driver
    
    def _get_calendar_url(self, country: str = "united states") -> Tuple[str, str, str]:
        """Generate URL with filtering parameters for the next month."""
        base_url = "https://tradingeconomics.com/calendar"
        today = datetime.now()
        
        # Next month
        if today.month == 12:
            start_date = datetime(today.year + 1, 1, 1)
        else:
            start_date = datetime(today.year, today.month + 1, 1)
        
        if start_date.month == 12:
            end_date = datetime(start_date.year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = datetime(start_date.year, start_date.month + 1, 1) - timedelta(days=1)
        
        url = f"{base_url}?country={country.replace(' ', '+')}"
        
        return url, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")
    
    def _dismiss_overlays(self, driver: webdriver.Chrome) -> None:
        """Dismisses cookie consent pop-ups and other overlays."""
        try:
            cookie_selectors = [
                "//button[contains(., 'Accept')]",
                "//button[contains(., 'Agree')]",
                "//button[contains(., 'Consent')]",
                "//*[contains(@class, 'fc-cta-consent')]",
                "//*[contains(@class, 'fc-button')]//p[contains(., 'Consent')]/..",
            ]
            
            for selector in cookie_selectors:
                try:
                    elements = driver.find_elements(By.XPATH, selector)
                    for el in elements:
                        if el.is_displayed():
                            el.click()
                            time.sleep(0.5)
                            return
                except:
                    continue
            
            # Hide overlay via JS
            driver.execute_script("""
                var overlays = document.querySelectorAll(
                    '.fc-dialog-overlay, .fc-consent-root, [class*="consent"], [class*="cookie"], [class*="gdpr"]'
                );
                overlays.forEach(function(el) { el.style.display = 'none'; });
                var ads = document.querySelectorAll('[id*="google_ads"], [class*="ad-"], iframe[src*="ads"]');
                ads.forEach(function(el) { el.style.display = 'none'; });
            """)
            time.sleep(0.3)
            
        except Exception as e:
            logger.warning(f"Warning while dismissing overlays: {e}")
    
    def _extract_calendar(self, driver: webdriver.Chrome) -> pd.DataFrame:
        """Extracts data from the calendar table."""
        wait = WebDriverWait(driver, 15)
        wait.until(EC.presence_of_element_located((By.ID, "calendar")))
        time.sleep(2)
        
        calendar_table = driver.find_element(By.ID, "calendar")
        rows = calendar_table.find_elements(By.TAG_NAME, "tr")
        
        logger.info(f"Found {len(rows)} rows in table")
        
        date_class_pattern = re.compile(r'^(\d{4}-\d{2}-\d{2})$')
        time_pattern = r'^\d{1,2}:\d{2}\s*(AM|PM)?$'
        
        result_rows = []
        
        for row in rows:
            cells = row.find_elements(By.TAG_NAME, "td")
            if not cells:
                continue
            
            # Look for date in CSS classes
            row_date = None
            for cell in cells:
                cell_classes = cell.get_attribute("class") or ""
                for css_class in cell_classes.split():
                    match = date_class_pattern.match(css_class)
                    if match:
                        row_date = match.group(1)
                        break
                if row_date:
                    break
            
            cell_texts = [cell.text.strip() for cell in cells]
            
            if not row_date or len(cell_texts) < 5:
                continue
            
            col0 = cell_texts[0] if len(cell_texts) > 0 else ""
            col1 = cell_texts[1] if len(cell_texts) > 1 else ""
            
            is_time = re.match(time_pattern, col0, re.IGNORECASE)
            
            if is_time and len(cell_texts) >= 5:
                # Extract link
                event_link = ''
                if len(cells) > 4:
                    try:
                        link_el = cells[4].find_element(By.TAG_NAME, 'a')
                        event_link = link_el.get_attribute('href') or ''
                    except:
                        pass
                
                result_rows.append({
                    'Date': row_date,
                    'Time': col0,
                    'Country': col1,
                    'Event': cell_texts[4] if len(cell_texts) > 4 else '',
                    'Link': event_link,
                    'Actual': cell_texts[5] if len(cell_texts) > 5 else '',
                    'Previous': cell_texts[6] if len(cell_texts) > 6 else '',
                    'Consensus': cell_texts[7] if len(cell_texts) > 7 else '',
                    'Forecast': cell_texts[8] if len(cell_texts) > 8 else '',
                })
        
        logger.info(f"Extracted {len(result_rows)} data rows")
        
        if result_rows:
            df = pd.DataFrame(result_rows)
            df = df[df['Event'].str.strip() != '']
            df = df[df['Event'] != 'nan']
            return df
        
        return pd.DataFrame(columns=[
            'Date', 'Time', 'Country', 'Event', 'Link',
            'Actual', 'Previous', 'Consensus', 'Forecast'
        ])
    
    def scrape(self, country: str = "united states") -> pd.DataFrame:
        """Main scraping method."""
        logger.info("Starting browser...")
        driver = self._setup_driver()
        
        try:
            url, start_date, end_date = self._get_calendar_url(country)
            logger.info(f"URL: {url}")
            logger.info(f"Range: {start_date} - {end_date}")
            
            driver.get(url)
            time.sleep(4)
            
            self._dismiss_overlays(driver)
            time.sleep(1)
            
            df = self._extract_calendar(driver)
            
            # Filter US only
            if 'Country' in df.columns:
                df = df[df['Country'].str.strip() == 'US'].copy()
                logger.info(f"Filtered to {len(df)} US events")
            
            # Drop duplicates
            df = df.drop_duplicates(subset=['Date', 'Time', 'Event'], keep='first')
            df = df.reset_index(drop=True)
            
            return df
            
        finally:
            driver.quit()
            logger.info("Browser closed")
    
    def save_to_db(self, df: pd.DataFrame) -> bool:
        """Saves DataFrame to SQLite database."""
        try:
            conn = sqlite3.connect(self.db_path)
            df.to_sql('economic_events', conn, if_exists='replace', index=False)
            conn.close()
            logger.info(f"Saved data to {self.db_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving to db: {e}")
            return False
    
    def run(self) -> pd.DataFrame:
        """Main entry point - scrapes and saves."""
        df = self.scrape()
        if not df.empty:
            self.save_to_db(df)
        return df


if __name__ == "__main__":
    scraper = EconomicCalendarScraper(headless=True)
    df = scraper.run()
    print(f"\n=== US Economic Calendar ({len(df)} events) ===")
    print(df.head(20))
