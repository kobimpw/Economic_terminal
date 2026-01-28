"""
Analizator Korelacji Rynkowych
==============================

Ten moduł zapewnia analizę korelacji rynkowych między wskaźnikami ekonomicznymi
a głównymi ETF-ami i indeksami. Oblicza korelacje, współczynniki beta
oraz dostarcza dane przeglądu rynku.

Funkcjonalności:
- Analiza korelacji z sektorowymi ETF-ami
- Obliczanie współczynnika Beta dla każdego sektora
- Przegląd rynku z danymi do wykresów sparkline
- Porównanie korelacji natychmiastowej vs długoterminowej

Przykład użycia:
    from src.analysis import MarketCorrelationAnalyzer
    
    analyzer = MarketCorrelationAnalyzer(indicator_data)
    correlations = analyzer.get_correlation("UMCSENT")
    market_data = analyzer.get_market_glance()
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import yfinance as yf

from src.utils import get_logger

logger = get_logger(__name__)


# ETF tickers and names for correlation analysis
SECTOR_ETFS: Dict[str, str] = {
    "^GSPC": "S&P 500",
    "SPY": "S&P 500 ETF",
    "XLI": "Industrials",
    "XLV": "Healthcare",
    "XLK": "Technology",
    "XLF": "Financials",
    "XLRE": "Real Estate",
    "XLU": "Utilities",
    "XLB": "Materials",
    "XLP": "Consumer Staples",
    "XLY": "Consumer Discretionary",
    "XLC": "Communication",
    "XLE": "Energy"
}

# Default tickers for analysis
DEFAULT_TICKERS: List[str] = [
    "^GSPC", "XLI", "XLV", "XLK", "XLF", "XLRE",
    "XLU", "XLB", "XLP", "XLY", "XLC", "XLE"
]

# Tickers for market glance (ETFs only, no index)
GLANCE_TICKERS: List[str] = [
    "SPY", "XLI", "XLV", "XLF", "XLRE", "XLE",
    "XLU", "XLK", "XLB", "XLP", "XLY", "XLC"
]


class MarketCorrelationAnalyzer:
    """
    Analyzer for market correlations between indicators and ETFs.
    
    This class calculates correlations and beta coefficients between
    economic indicators and sector ETFs, helping understand market reactions.
    
    Attributes:
        indicator_data (pd.Series): Economic indicator time series.
        historical_releases (Optional[pd.DataFrame]): Historical release dates.
    """
    
    def __init__(
        self,
        indicator_data: Optional[pd.Series] = None,
        historical_releases: Optional[pd.DataFrame] = None
    ):
        """
        Initialize the market correlation analyzer.
        
        Args:
            indicator_data: Economic indicator time series.
            historical_releases: DataFrame with historical release dates.
        """
        self.indicator_data = indicator_data
        self.historical_releases = historical_releases
        logger.debug("Initialized MarketCorrelationAnalyzer")
    
    def get_correlation(
        self,
        series_id: str,
        tickers: Optional[List[str]] = None,
        years_back: int = 3
    ) -> Dict:
        """
        Calculate correlation and beta with major ETFs.
        
        Analyzes both long-term correlation using all data and
        immediate correlation on release dates (if available).
        
        Args:
            series_id: FRED series ID for logging/reference.
            tickers: List of ETF tickers. Defaults to major sectors.
            years_back: Years of historical data to use.
            
        Returns:
            Dictionary mapping ticker to correlation data:
            - name: Human-readable ETF name
            - long_term_correlation: Correlation over full period
            - immediate_correlation: Correlation on release dates (if available)
            - beta: Beta coefficient
            - strength: "High", "Medium", or "Low"
            - direction: "Positive" or "Negative"
            - interpretation: Human-readable summary
        """
        if self.indicator_data is None or self.indicator_data.empty:
            logger.warning("No indicator data provided for correlation analysis")
            return {}
        
        tickers = tickers or DEFAULT_TICKERS
        
        logger.info(f"Calculating market correlations for {series_id}")
        
        try:
            # Get market data
            start_date = (datetime.now() - timedelta(days=365 * years_back)).strftime("%Y-%m-%d")
            raw_data = yf.download(
                tickers,
                start=start_date,
                progress=False,
                auto_adjust=True
            )
            
            # Handle MultiIndex columns from yfinance
            if isinstance(raw_data.columns, pd.MultiIndex):
                market_data = raw_data["Close"] if "Close" in raw_data.columns.get_level_values(0) else raw_data
            else:
                market_data = raw_data[["Close"]] if "Close" in raw_data.columns else raw_data
            
            if market_data.empty:
                logger.warning("No market data retrieved")
                return {}
            
            results = {}
            
            for ticker in tickers:
                if ticker not in market_data.columns:
                    continue
                
                result = self._calculate_ticker_correlation(
                    ticker,
                    market_data[ticker]
                )
                
                if result:
                    results[ticker] = result
            
            logger.info(f"Calculated correlations for {len(results)} tickers")
            return results
            
        except Exception as e:
            logger.error(f"Error calculating market correlation: {e}")
            return {}
    
    def _calculate_ticker_correlation(
        self,
        ticker: str,
        ticker_series: pd.Series
    ) -> Optional[Dict]:
        """
        Calculate correlation for a single ticker.
        
        Args:
            ticker: Ticker symbol.
            ticker_series: Price series for the ticker.
            
        Returns:
            Dictionary with correlation data or None if insufficient data.
        """
        # Calculate returns
        indicator_returns = self.indicator_data.pct_change().dropna()
        ticker_returns = ticker_series.pct_change().dropna()
        
        # Align data
        combined = pd.concat(
            [indicator_returns, ticker_returns],
            axis=1,
            join="inner"
        ).dropna()
        
        if len(combined) < 10:
            return None
        
        # Long-term correlation
        long_term_corr = combined.corr().iloc[0, 1] if len(combined.columns) > 1 else 0
        
        # Beta calculation
        cov = combined.iloc[:, 0].cov(combined.iloc[:, 1])
        var = combined.iloc[:, 1].var()
        beta = cov / var if var != 0 else 0
        
        # Immediate correlation (on release dates)
        immediate_corr = self._calculate_immediate_correlation(
            indicator_returns,
            ticker_returns
        )
        
        # Interpretation
        corr_strength = "High" if abs(long_term_corr) > 0.5 else "Medium" if abs(long_term_corr) > 0.2 else "Low"
        direction = "Positive" if long_term_corr > 0 else "Negative"
        
        return {
            "name": SECTOR_ETFS.get(ticker, ticker),
            "long_term_correlation": float(long_term_corr),
            "immediate_correlation": float(immediate_corr) if immediate_corr else None,
            "beta": float(beta),
            "strength": corr_strength,
            "direction": direction,
            "interpretation": f"{direction} {corr_strength.lower()} correlation"
        }
    
    def _calculate_immediate_correlation(
        self,
        indicator_returns: pd.Series,
        ticker_returns: pd.Series
    ) -> Optional[float]:
        """
        Calculate correlation on release dates.
        
        Args:
            indicator_returns: Indicator return series.
            ticker_returns: Ticker return series.
            
        Returns:
            Immediate correlation or None if insufficient data.
        """
        if self.historical_releases is None:
            return None
        
        release_dates = self.historical_releases.index
        release_returns = []
        market_returns = []
        
        for date in release_dates:
            if date in ticker_returns.index and date in indicator_returns.index:
                release_returns.append(indicator_returns[date])
                market_returns.append(ticker_returns[date])
        
        if len(release_returns) > 5:
            return np.corrcoef(release_returns, market_returns)[0, 1]
        
        return None
    
    def get_market_glance(self, days_back: int = 45) -> Dict:
        """
        Get market overview with sparkline data for major ETFs.
        
        Fetches recent price data and calculates daily changes
        for quick market overview.
        
        Args:
            days_back: Number of days of data to fetch.
            
        Returns:
            Dictionary mapping ticker to:
            - price: Current price
            - change: Daily change percentage
            - data: List of prices for sparkline
            - dates: List of dates for sparkline
        """
        logger.info("Fetching market glance data")
        
        try:
            start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
            raw_data = yf.download(
                GLANCE_TICKERS,
                start=start_date,
                progress=False,
                group_by="ticker",
                auto_adjust=True
            )
            
            results = {}
            
            for ticker in GLANCE_TICKERS:
                try:
                    # Handle yfinance multi-index
                    if isinstance(raw_data.columns, pd.MultiIndex):
                        if ticker in raw_data.columns.levels[0]:
                            data = raw_data[ticker]["Close"]
                        else:
                            continue
                    else:
                        if ticker == GLANCE_TICKERS[0]:
                            data = raw_data["Close"]
                        else:
                            continue
                    
                    data = data.dropna().tail(22)  # Approx 1 month trading days
                    
                    if data.empty:
                        continue
                    
                    current_price = data.iloc[-1]
                    prev_close = data.iloc[-2] if len(data) > 1 else current_price
                    change_pct = ((current_price - prev_close) / prev_close) * 100
                    
                    results[ticker] = {
                        "price": float(current_price),
                        "change": float(change_pct),
                        "data": data.tolist(),
                        "dates": data.index.strftime("%m-%d").tolist()
                    }
                    
                except Exception as e:
                    logger.debug(f"Error processing {ticker}: {e}")
                    continue
            
            logger.info(f"Retrieved market glance for {len(results)} tickers")
            return results
            
        except Exception as e:
            logger.error(f"Error fetching market glance: {e}")
            return {}
