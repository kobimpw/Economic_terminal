"""
PredictorCore - Główny Orkiestrator
==================================

Ten moduł zawiera główną klasę PredictorCore, która koordynuje
wszystkie moduły predykcji, analizy i integracji z API.

PredictorCore służy jako główny interfejs dla aplikacji terminala,
delegując pracę do wyspecjalizowanych modułów przy zachowaniu zunifikowanego API.

Przykład użycia:
    from src.core import PredictorCore
    
    predictor = PredictorCore(api_key="twój_klucz_fred_api")
    predictor.fetch_data("UMCSENT")
    results = predictor.analyze_arima(order=(1,1,1))
"""

import os
from typing import Dict, List, Optional, Tuple

import pandas as pd
from dotenv import load_dotenv

from src.core.data_fetcher import FredDataFetcher
from src.integrations.news_api import NewsAPIClient
from src.integrations.perplexity_api import PerplexityClient
from src.analysis.market_correlation import MarketCorrelationAnalyzer
from src.utils import get_logger

load_dotenv()

logger = get_logger(__name__)


class PredictorCore:
    """
    Main orchestrator for the Advanced Macro Trading Terminal.
    
    This class coordinates data fetching, prediction models, external API
    integrations, and market analysis. It provides a unified interface
    that maintains backward compatibility with the original API.
    
    Attributes:
        fred (FredDataFetcher): FRED data fetching component.
        news_client (NewsAPIClient): News API integration.
        perplexity_client (PerplexityClient): Perplexity AI integration.
        series_id (Optional[str]): Currently loaded series ID.
        df (Optional[pd.DataFrame]): Currently loaded data.
        inferred_freq (Optional[str]): Detected data frequency.
    """
    
    def __init__(self, api_key: str):
        """
        Initialize PredictorCore with all components.
        
        Args:
            api_key: FRED API key for data access.
        """
        # Core components
        self.data_fetcher = FredDataFetcher(api_key)
        
        # API integrations
        self.news_client = NewsAPIClient()
        self.perplexity_client = PerplexityClient()
        
        # State
        self.series_id: Optional[str] = None
        self.df: Optional[pd.DataFrame] = None
        self.inferred_freq: Optional[str] = None
        self.last_results: Optional[Dict] = None
        self._release_cache: Dict = {}
        
        logger.info("PredictorCore initialized with all components")
    
    # =========================================================================
    # DATA FETCHING (delegated to FredDataFetcher)
    # =========================================================================
    
    def fetch_data(
        self,
        series_id: str,
        start_date: str = "2015-01-01",
        end_date: Optional[str] = None,
        n_test: int = 12
    ) -> pd.DataFrame:
        """
        Fetch data from FRED with robust frequency handling.
        
        Args:
            series_id: FRED series ID.
            start_date: Start date for data retrieval.
            end_date: End date (defaults to today).
            n_test: Number of test observations.
            
        Returns:
            DataFrame with 'value' column and DatetimeIndex.
        """
        self.df = self.data_fetcher.fetch_data(series_id, start_date, end_date, n_test)
        self.series_id = self.data_fetcher.series_id
        self.inferred_freq = self.data_fetcher.inferred_freq
        return self.df
    
    def get_next_release(self, series_id: str) -> str:
        """Get next release date for an indicator."""
        return self.data_fetcher.get_next_release(series_id)
    
    def get_historical_releases(self, series_id: str) -> Optional[pd.DataFrame]:
        """Get historical release dates."""
        return self.data_fetcher.get_historical_releases(series_id)
    
    def organize_by_release_date(self, series_dict: Dict[str, str]) -> Dict[str, List[Dict]]:
        """Organize indicators by release date for calendar view."""
        return self.data_fetcher.organize_by_release_date(series_dict)
    
    # =========================================================================
    # PREDICTION MODELS
    # =========================================================================
    
    def analyze_arima(
        self,
        order: Tuple[int, int, int] = (1, 1, 1),
        n_test: int = 12,
        h_future: int = 6
    ) -> Dict:
        """
        Run ARIMA analysis on currently loaded data.
        
        Args:
            order: ARIMA order (p, d, q).
            n_test: Number of test observations.
            h_future: Number of future periods to forecast.
            
        Returns:
            Dictionary with analysis results.
        """
        self._ensure_data_loaded()
        from src.models.arima_model import ARIMAAnalyzer
        analyzer = ARIMAAnalyzer(self.df["value"], self.inferred_freq)
        self.last_results = analyzer.analyze(order, n_test, h_future)
        return self.last_results
    
    def analyze_moving_average(
        self,
        windows: List[int] = [3],
        n_test: int = 12,
        h_future: int = 6
    ) -> Dict:
        """
        Run Moving Average analysis on currently loaded data.
        
        Args:
            windows: List of window sizes for ensemble.
            n_test: Number of test observations.
            h_future: Number of future periods to forecast.
            
        Returns:
            Dictionary with analysis results.
        """
        self._ensure_data_loaded()
        from src.models.moving_average import MovingAverageAnalyzer
        analyzer = MovingAverageAnalyzer(self.df["value"], self.inferred_freq)
        self.last_results = analyzer.analyze(windows, n_test, h_future)
        return self.last_results
    
    def analyze_monte_carlo(
        self,
        simulations: int = 1000,
        n_test: int = 12,
        h_future: int = 6
    ) -> Dict:
        """
        Run Monte Carlo simulation on currently loaded data.
        
        Args:
            simulations: Number of simulation paths.
            n_test: Number of test observations.
            h_future: Number of future periods to forecast.
            
        Returns:
            Dictionary with analysis results.
        """
        self._ensure_data_loaded()
        from src.models.monte_carlo import MonteCarloSimulator
        simulator = MonteCarloSimulator(self.df["value"], self.inferred_freq)
        self.last_results = simulator.analyze(simulations, n_test, h_future)
        return self.last_results
    
    def find_best_model(
        self,
        n_test: int = 12,
        h_future: int = 6
    ) -> Dict:
        """
        Run all three models and select the best one based on error metrics.
        
        The best model is selected using a weighted score combining:
        - RMSE (lower is better)
        - MAPE (lower is better) 
        
        For models without AIC/BIC (Monte Carlo, Moving Average), only RMSE and MAPE are used.
        
        Args:
            n_test: Number of test observations.
            h_future: Number of future periods to forecast.
            
        Returns:
            Dictionary with best model results and comparison data.
        """
        self._ensure_data_loaded()
        
        results = {}
        scores = {}
        
        # ARIMA with different orders
        from src.models.arima_model import ARIMAAnalyzer
        arima_orders = [(1, 1, 1), (2, 1, 1), (1, 1, 2), (2, 1, 2)]
        for order in arima_orders:
            try:
                analyzer = ARIMAAnalyzer(self.df["value"], self.inferred_freq)
                result = analyzer.analyze(order, n_test, h_future)
                model_name = f"ARIMA{order}"
                results[model_name] = result
                
                # Calculate score (lower is better)
                rmse = result["stats"].get("RMSE", float("inf"))
                mape = result["stats"].get("MAPE", float("inf"))
                aic = result["stats"].get("AIC", 0)
                bic = result["stats"].get("BIC", 0)
                
                # Normalize and combine (RMSE and MAPE weighted, AIC/BIC as tiebreaker)
                scores[model_name] = rmse * 0.4 + mape * 0.4 + (aic / 10000) * 0.1 + (bic / 10000) * 0.1
                logger.debug(f"{model_name}: RMSE={rmse:.4f}, MAPE={mape:.2f}%, score={scores[model_name]:.4f}")
            except Exception as e:
                logger.warning(f"ARIMA{order} failed: {e}")
        
        # Moving Average
        try:
            from src.models.moving_average import MovingAverageAnalyzer
            analyzer = MovingAverageAnalyzer(self.df["value"], self.inferred_freq)
            result = analyzer.analyze([3, 6, 12], n_test, h_future)
            model_name = "MovingAverage"
            results[model_name] = result
            
            rmse = result["stats"].get("RMSE", float("inf"))
            mape = result["stats"].get("MAPE", float("inf"))
            scores[model_name] = rmse * 0.5 + mape * 0.5
            logger.debug(f"{model_name}: RMSE={rmse:.4f}, MAPE={mape:.2f}%, score={scores[model_name]:.4f}")
        except Exception as e:
            logger.warning(f"MovingAverage failed: {e}")
        
        # Monte Carlo
        try:
            from src.models.monte_carlo import MonteCarloSimulator
            simulator = MonteCarloSimulator(self.df["value"], self.inferred_freq)
            result = simulator.analyze(1000, n_test, h_future)
            model_name = "MonteCarlo"
            results[model_name] = result
            
            rmse = result["stats"].get("RMSE", float("inf"))
            mape = result["stats"].get("MAPE", float("inf"))
            scores[model_name] = rmse * 0.5 + mape * 0.5
            logger.debug(f"{model_name}: RMSE={rmse:.4f}, MAPE={mape:.2f}%, score={scores[model_name]:.4f}")
        except Exception as e:
            logger.warning(f"MonteCarlo failed: {e}")
        
        if not scores:
            raise ValueError("All models failed to fit")
        
        # Select best model
        best_model_name = min(scores, key=scores.get)
        best_result = results[best_model_name]
        
        logger.info(f"Best model: {best_model_name} (score={scores[best_model_name]:.4f})")
        
        # Add comparison info
        best_result["best_model"] = best_model_name
        best_result["model_comparison"] = {
            name: {
                "score": scores[name],
                "rmse": results[name]["stats"].get("RMSE", 0),
                "mape": results[name]["stats"].get("MAPE", 0),
                "aic": results[name]["stats"].get("AIC", None),
                "bic": results[name]["stats"].get("BIC", None),
            }
            for name in results
        }
        
        self.last_results = best_result
        return best_result
    
    # =========================================================================
    # MARKET ANALYSIS
    # =========================================================================
    
    def get_market_correlation(self, series_id: str) -> Dict:
        """
        Calculate correlation with major ETFs.
        
        Args:
            series_id: FRED series ID for reference.
            
        Returns:
            Dictionary with correlation data for each ETF.
        """
        self._ensure_data_loaded()
        historical_releases = self.get_historical_releases(series_id)
        analyzer = MarketCorrelationAnalyzer(
            self.df["value"],
            historical_releases
        )
        return analyzer.get_correlation(series_id)
    
    def get_market_glance(self) -> Dict:
        """
        Get market overview with sparkline data.
        
        Returns:
            Dictionary with ETF prices and changes.
        """
        analyzer = MarketCorrelationAnalyzer()
        return analyzer.get_market_glance()
    
    # =========================================================================
    # API INTEGRATIONS
    # =========================================================================
    
    def get_perplexity_research(
        self,
        series_id: str,
        indicator_name: Optional[str] = None
    ) -> Dict:
        """
        Get AI-powered research from Perplexity.
        
        Args:
            series_id: FRED series ID.
            indicator_name: Human-readable indicator name.
            
        Returns:
            Dictionary with AI analysis and sources.
        """
        return self.perplexity_client.get_research(series_id, indicator_name)
    
    def get_news_sentiment(
        self,
        series_id: str,
        query: Optional[str] = None
    ) -> Dict:
        """
        Get news articles with sentiment analysis.
        
        Args:
            series_id: FRED series ID.
            query: Custom search query (optional).
            
        Returns:
            Dictionary with articles and sentiment scores.
        """
        return self.news_client.get_sentiment(series_id, query)
    
    # =========================================================================
    # INTERNAL HELPERS
    # =========================================================================
    
    def _ensure_data_loaded(self) -> None:
        """Ensure data is loaded before analysis."""
        if self.df is None or self.df.empty:
            raise ValueError(
                "No data loaded. Call fetch_data() first."
            )
    
    # =========================================================================
    # LEGACY COMPATIBILITY
    # =========================================================================
    
    @property
    def fred(self):
        """Legacy compatibility: access to FRED client."""
        return self.data_fetcher.fred


# For backwards compatibility
__all__ = ["PredictorCore"]
