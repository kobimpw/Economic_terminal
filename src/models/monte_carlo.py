"""
Symulator Monte Carlo
=====================

Ten moduł zapewnia symulację Monte Carlo do prognozowania szeregów czasowych.
Generuje wiele losowych ścieżek cenowych na podstawie historycznych stóp zwrotu
i dostarcza probabilistyczne prognozy z przedziałami ufności opartymi na percentylach.

Przykład użycia:
    from src.models import MonteCarloSimulator
    
    simulator = MonteCarloSimulator(data, inferred_freq="MS")
    results = simulator.analyze(simulations=1000, n_test=12, h_future=6)
"""

from typing import Dict

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error

from src.utils import get_logger

logger = get_logger(__name__)


class MonteCarloSimulator:
    """
    Monte Carlo simulation for probabilistic time series forecasting.
    
    This class generates random price paths based on historical return
    distributions and provides forecasts with confidence intervals
    based on simulation percentiles.
    
    Attributes:
        data (pd.Series): Time series data for analysis.
        inferred_freq (str): Inferred frequency of the data.
    """
    
    def __init__(self, data: pd.Series, inferred_freq: str):
        """
        Initialize the Monte Carlo simulator.
        
        Args:
            data: Time series data as pandas Series with DatetimeIndex.
            inferred_freq: Frequency of the time series (e.g., 'MS' for monthly).
        """
        self.data = data
        self.inferred_freq = inferred_freq
        logger.debug(f"Initialized MonteCarloSimulator with {len(data)} observations")
    
    def analyze(
        self,
        simulations: int = 1000,
        n_test: int = 12,
        h_future: int = 6
    ) -> Dict:
        """
        Perform Monte Carlo simulation with percentile-based confidence bands.
        
        This method:
        1. Calculates historical return statistics (mean, std)
        2. Backtests on test period using rolling simulation
        3. Runs full simulation paths for future forecast
        4. Calculates percentile-based confidence intervals
        
        Args:
            simulations: Number of simulation paths to generate.
            n_test: Number of observations to use for testing.
            h_future: Number of future periods to forecast.
            
        Returns:
            Dictionary containing:
            - model: Model identifier string
            - stats: Dictionary with return statistics and metrics
            - comparison: Actual vs predicted for test period
            - forecast: Future forecast with percentile bands
            - historical: Full historical data
            - opinion: Model quality assessment
        """
        logger.info(f"Running Monte Carlo: simulations={simulations}, n_test={n_test}, h_future={h_future}")
        
        returns = self.data.pct_change().dropna()
        
        mu = returns.mean()
        sigma = returns.std()
        
        logger.debug(f"Return statistics: mean={mu:.6f}, std={sigma:.6f}")
        
        # Test phase: backtest using rolling window
        test_preds = []
        for i in range(n_test):
            train_data = self.data.iloc[:-(n_test - i)]
            train_returns = train_data.pct_change().dropna()
            mu_train = train_returns.mean()
            sigma_train = train_returns.std()
            last_price = train_data.iloc[-1]
            
            # Simulate 1 step ahead
            sims = [
                last_price * (1 + np.random.normal(mu_train, sigma_train))
                for _ in range(simulations)
            ]
            test_preds.append(np.mean(sims))
        
        fc_test = pd.Series(test_preds, index=self.data.index[-n_test:])
        test_actual = self.data.iloc[-n_test:]
        
        # Calculate metrics
        mae = mean_absolute_error(test_actual, fc_test)
        rmse = np.sqrt(mean_squared_error(test_actual, fc_test))
        
        logger.info(f"MC metrics: MAE={mae:.4f}, RMSE={rmse:.4f}")
        
        # Future forecast with full simulation paths
        last_price = self.data.iloc[-1]
        all_paths = []
        
        for _ in range(simulations):
            prices = [last_price]
            for _ in range(h_future):
                prices.append(prices[-1] * (1 + np.random.normal(mu, sigma)))
            all_paths.append(prices[1:])
        
        all_paths = np.array(all_paths)
        fc_future = np.mean(all_paths, axis=0)
        
        # Percentile-based confidence intervals
        p5 = np.percentile(all_paths, 5, axis=0)
        p25 = np.percentile(all_paths, 25, axis=0)
        p75 = np.percentile(all_paths, 75, axis=0)
        p95 = np.percentile(all_paths, 95, axis=0)
        
        # Generate future dates
        future_index = pd.date_range(
            start=self.data.index[-1],
            periods=h_future + 1,
            freq=self.inferred_freq
        )[1:]
        
        # Differences
        test_diff = test_actual.diff().fillna(0)
        fc_test_diff = fc_test.diff().fillna(0)
        
        # Generate opinion
        opinion = self._generate_opinion(simulations, sigma, rmse)
        
        return {
            "model": f"Monte Carlo ({simulations} sims)",
            "stats": {
                "Mean Return": float(mu),
                "Volatility": float(sigma),
                "MAE": float(mae),
                "RMSE": float(rmse),
                "Simulations": simulations
            },
            "comparison": {
                "dates": test_actual.index.strftime("%Y-%m-%d").tolist(),
                "actual": test_actual.tolist(),
                "predict": fc_test.tolist(),
                "actual_diff": test_diff.tolist(),
                "predict_diff": fc_test_diff.tolist(),
                "diff_error": (test_diff - fc_test_diff).tolist()
            },
            "forecast": {
                "dates": future_index.strftime("%Y-%m-%d").tolist(),
                "values": fc_future.tolist(),
                "sigma_1_up": p75.tolist(),     # 75th percentile
                "sigma_1_down": p25.tolist(),   # 25th percentile
                "sigma_2_up": p95.tolist(),     # 95th percentile
                "sigma_2_down": p5.tolist(),    # 5th percentile
            },
            "historical": self._get_chart_historical(months=120),
            "opinion": opinion
        }
    
    def _generate_opinion(self, simulations: int, sigma: float, rmse: float) -> str:
        """
        Generate opinion about Monte Carlo simulation quality.
        
        Args:
            simulations: Number of simulation paths.
            sigma: Historical volatility (std of returns).
            rmse: Root Mean Squared Error on test set.
            
        Returns:
            Opinion string with quality assessment.
        """
        opinion = (
            f"Symulacja Monte Carlo ({simulations} ścieżek). "
            f"Zmienność: {sigma:.4%}, RMSE: {rmse:.4f}. "
        )
        
        if sigma < 0.02:
            opinion += "Niskie ryzyko."
        else:
            opinion += "Wysoka zmienność - szerokie przedziały ufności."
        
        return opinion
    
    def _get_chart_historical(self, months: int = 120) -> dict:
        """
        Zwraca dane historyczne ograniczone do ostatnich N miesięcy.
        """
        from datetime import datetime
        from dateutil.relativedelta import relativedelta
        
        cutoff_date = datetime.now() - relativedelta(months=months)
        filtered = self.data[self.data.index >= cutoff_date]
        
        if filtered.empty:
            filtered = self.data
        
        return {
            "dates": filtered.index.strftime("%Y-%m-%d").tolist(),
            "values": filtered.tolist()
        }
