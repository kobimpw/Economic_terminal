"""
Pobieranie Danych z FRED
========================

Ten moduł zapewnia narzędzia do pobierania danych z FRED (Federal Reserve Economic Data).
Obsługuje pobieranie szeregów czasowych, wykrywanie częstotliwości, scrapowanie dat publikacji
oraz organizację kalendarza wskaźników.

Funkcjonalności:
- Solidna obsługa różnych częstotliwości danych (dzienne, miesięczne itp.)
- Scrapowanie dat publikacji z cache'owaniem
- Pobieranie historycznych dat publikacji
- Organizacja kalendarza dat publikacji

Przykład użycia:
    from src.core import FredDataFetcher
    
    fetcher = FredDataFetcher(api_key="twój_klucz_fred_api")
    data = fetcher.fetch_data("UMCSENT", start_date="2015-01-01")
    next_release = fetcher.get_next_release("UMCSENT")
"""

import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import pandas as pd
import requests
from bs4 import BeautifulSoup
from dateutil import parser as date_parser
from fredapi import Fred

from src.utils import get_logger, DataFetchError

logger = get_logger(__name__)


class FredDataFetcher:
    """
    Fetcher for FRED economic data with release date tracking.
    
    This class handles data retrieval from FRED API, including
    frequency detection, data cleaning, and release date scraping.
    
    Attributes:
        fred (Fred): FRED API client.
        series_id (Optional[str]): Currently loaded series ID.
        df (Optional[pd.DataFrame]): Currently loaded data.
        inferred_freq (Optional[str]): Detected data frequency.
    """
    
    def __init__(self, api_key: str):
        """
        Initialize the FRED data fetcher.
        
        Args:
            api_key: FRED API key.
        """
        self.fred = Fred(api_key=api_key)
        self.series_id: Optional[str] = None
        self.df: Optional[pd.DataFrame] = None
        self.inferred_freq: Optional[str] = None
        self._release_cache: Dict[str, Tuple[str, datetime]] = {}
        
        logger.debug("Initialized FredDataFetcher")
    
    def fetch_data(
        self,
        series_id: str,
        start_date: str = "2015-01-01",
        end_date: Optional[str] = None,
        n_test: int = 12
    ) -> pd.DataFrame:
        """
        Fetch data from FRED with robust frequency handling.
        
        Handles various data frequencies including daily, weekly, monthly,
        and irregular series with automatic frequency detection and filling.
        
        Args:
            series_id: FRED series ID (e.g., "UMCSENT", "T10Y2Y").
            start_date: Start date for data retrieval.
            end_date: End date (defaults to today).
            n_test: Number of test observations (for reference).
            
        Returns:
            DataFrame with 'value' column and DatetimeIndex.
            
        Raises:
            DataFetchError: If data retrieval fails.
        """
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        
        logger.info(f"Fetching data for {series_id}: {start_date} to {end_date}")
        
        try:
            s = self.fred.get_series(
                series_id,
                observation_start=start_date,
                observation_end=end_date
            )
            s.name = "value"
            self.series_id = series_id
            
            # 1. First cleanup: Remove duplicates and sort
            s = s[~s.index.duplicated(keep="first")].sort_index()
            
            # 2. Try to infer frequency
            self.inferred_freq = pd.infer_freq(s.index)
            
            # 3. Handle irregular/missing frequency
            if not self.inferred_freq:
                s, self.inferred_freq = self._handle_irregular_frequency(s)
            
            # 4. Final cleaning
            if self.inferred_freq:
                s = s.asfreq(self.inferred_freq).ffill()
            
            # Fill any remaining NaNs
            s = s.bfill().ffill()
            
            self.df = s.to_frame()
            
            logger.info(f"Fetched {len(self.df)} observations, freq={self.inferred_freq}")
            return self.df
            
        except Exception as e:
            logger.error(f"Error fetching data for {series_id}: {e}")
            raise DataFetchError(
                f"Failed to fetch data: {e}",
                series_id=series_id
            )
    
    def _handle_irregular_frequency(
        self,
        s: pd.Series
    ) -> Tuple[pd.Series, str]:
        """
        Handle irregular time series frequency.
        
        Attempts to detect and normalize irregular frequencies
        by trying business day, daily, or monthly resampling.
        
        Args:
            s: Time series with irregular frequency.
            
        Returns:
            Tuple of (normalized series, detected frequency).
        """
        # Try Business Day first
        filled_s = s.asfreq("B")
        if pd.infer_freq(filled_s.index) == "B":
            return filled_s.ffill(), "B"
        
        # Check if mostly daily
        diffs = s.index.to_series().diff().dt.days
        if diffs.mode()[0] == 1:
            return s.asfreq("D").ffill(), "D"
        
        # Monthly fallback
        return s.resample("MS").mean(), "MS"
    
    def get_next_release(self, series_id: str) -> str:
        """
        Scrape next release date from FRED website.
        
        Uses caching to avoid excessive requests. Cache expires after 1 hour.
        
        Args:
            series_id: FRED series ID.
            
        Returns:
            Next release date as string, or "TBD"/"N/A" if not found.
        """
        # Check cache
        if series_id in self._release_cache:
            cached_date, cached_time = self._release_cache[series_id]
            if (datetime.now() - cached_time).seconds < 3600:
                return cached_date
        
        logger.debug(f"Scraping release date for {series_id}")
        
        try:
            url = f"https://fred.stlouisfed.org/series/{series_id}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            response = requests.get(url, headers=headers, timeout=3)
            soup = BeautifulSoup(response.content, "html.parser")
            
            # Primary selector
            element = soup.select_one("#mobile-meta-col > p:nth-child(4) > a > span > span")
            if element:
                date_text = element.get_text(strip=True)
                self._release_cache[series_id] = (date_text, datetime.now())
                return date_text
            
            # Fallback 1: Look for "Next Release:" text
            meta_col = soup.select_one("#mobile-meta-col")
            if meta_col:
                text = meta_col.get_text()
                if "Next Release:" in text:
                    parts = text.split("Next Release:")[1].split("\n")[0].strip()
                    self._release_cache[series_id] = (parts, datetime.now())
                    return parts
            
            # Fallback 2: Look for any date-like pattern
            for p in soup.find_all("p"):
                if "Next Release" in p.get_text():
                    date_text = p.get_text().split("Next Release:")[-1].strip()
                    self._release_cache[series_id] = (date_text, datetime.now())
                    return date_text
            
            return "TBD"
            
        except Exception as e:
            logger.warning(f"Error scraping release date for {series_id}: {e}")
            return "N/A"
    
    def get_historical_releases(self, series_id: str) -> Optional[pd.DataFrame]:
        """
        Get historical release dates using FRED API.
        
        Retrieves all revisions and extracts the first release date
        for each observation.
        
        Args:
            series_id: FRED series ID.
            
        Returns:
            DataFrame with first release dates, or None if unavailable.
        """
        logger.debug(f"Fetching historical releases for {series_id}")
        
        try:
            releases = self.fred.get_series_all_releases(series_id)
            if releases is None or releases.empty:
                return None
            
            releases_df = releases.reset_index()
            releases_df.columns = ["date", "realtime_start", "value"]
            
            # Get first release for each observation
            first_releases = releases_df.sort_values("realtime_start").groupby("date").first()
            return first_releases
            
        except Exception as e:
            logger.warning(f"Could not fetch historical releases for {series_id}: {e}")
            return None
    
    def organize_by_release_date(
        self,
        series_dict: Dict[str, str]
    ) -> Dict[str, List[Dict]]:
        """
        Organize indicators by their next release date for calendar view.
        
        Args:
            series_dict: Dictionary mapping indicator names to FRED series IDs.
            
        Returns:
            Dictionary with dates as keys and list of indicator info as values.
            Sorted chronologically with TBD/Error at the end.
        """
        logger.info(f"Organizing {len(series_dict)} indicators by release date")
        
        calendar: Dict[str, List[Dict]] = {}
        
        for name, series_id in series_dict.items():
            try:
                next_release = self.get_next_release(series_id)
                date_key = self._parse_release_date(next_release)
                
                if date_key not in calendar:
                    calendar[date_key] = []
                
                calendar[date_key].append({
                    "name": name,
                    "series_id": series_id,
                    "release_text": next_release
                })
                
            except Exception as e:
                logger.warning(f"Error organizing {series_id}: {e}")
                if "Error" not in calendar:
                    calendar["Error"] = []
                calendar["Error"].append({
                    "name": name,
                    "series_id": series_id,
                    "release_text": "Error fetching"
                })
        
        # Sort calendar by date
        return self._sort_calendar(calendar)
    
    def _parse_release_date(self, release_text: str) -> str:
        """
        Parse release date text to standardized format.
        
        Args:
            release_text: Release date string from FRED.
            
        Returns:
            Date key in YYYY-MM-DD format, or "TBD".
        """
        if release_text in ["TBD", "N/A"]:
            return "TBD"
        
        # Try YYYY-MM-DD format
        date_match = re.search(r"(\d{4}-\d{2}-\d{2})", release_text)
        if date_match:
            return date_match.group(1)
        
        # Try fuzzy parsing
        try:
            parsed = date_parser.parse(release_text, fuzzy=True)
            return parsed.strftime("%Y-%m-%d")
        except Exception:
            return release_text
    
    def _sort_calendar(
        self,
        calendar: Dict[str, List[Dict]]
    ) -> Dict[str, List[Dict]]:
        """
        Sort calendar dictionary by date.
        
        Puts TBD and Error entries at the end.
        
        Args:
            calendar: Unsorted calendar dictionary.
            
        Returns:
            Sorted calendar dictionary.
        """
        sorted_calendar = {}
        sorted_keys = sorted([k for k in calendar.keys() if k not in ["TBD", "Error"]])
        
        for key in sorted_keys:
            sorted_calendar[key] = calendar[key]
        
        if "TBD" in calendar:
            sorted_calendar["TBD"] = calendar["TBD"]
        if "Error" in calendar:
            sorted_calendar["Error"] = calendar["Error"]
        
        return sorted_calendar
