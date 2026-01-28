"""
Analizator Średniej Kroczącej
============================

Ten moduł zapewnia analizę średniej kroczącej do prognozowania szeregów czasowych.
Wspiera wiele rozmiarów okien i uśrednianie zespołowe dla bardziej solidnych prognoz.

Model średniej kroczącej jest prostym, ale skutecznym poziomem bazowym
dla stabilnych szeregów czasowych z wyraźnymi trendami.

Przykład użycia:
    from src.models import MovingAverageAnalyzer
    
    analyzer = MovingAverageAnalyzer(data, inferred_freq="MS")
    results = analyzer.analyze(windows=[3, 6, 12], n_test=12, h_future=6)
"""

from typing import Dict, List, Union

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error

from src.utils import get_logger

logger = get_logger(__name__)


class MovingAverageAnalyzer:
    """
    Moving Average model analyzer for time series forecasting.
    
    This class supports multiple window sizes and creates an ensemble
    prediction by averaging across all windows.
    
    Attributes:
        data (pd.Series): Time series data for analysis.
        inferred_freq (str): Inferred frequency of the data.
    """
    
    def __init__(self, data: pd.Series, inferred_freq: str):
        """
        Initialize the Moving Average analyzer.
        
        Args:
            data: Time series data as pandas Series with DatetimeIndex.
            inferred_freq: Frequency of the time series (e.g., 'MS' for monthly).
        """
        self.data = data
        self.inferred_freq = inferred_freq
        logger.debug(f"Initialized MovingAverageAnalyzer with {len(data)} observations")
    
    def analyze(
        self,
        windows: Union[List[int], int] = [3],
        n_test: int = 12,
        h_future: int = 6
    ) -> Dict:
        """
        Perform Moving Average analysis with multiple window support.
        
        This method:
        1. Calculates predictions for each window size
        2. Creates ensemble by averaging across windows
        3. Evaluates on test data
        4. Generates future forecast
        
        Args:
            windows: List of window sizes or single window size.
            n_test: Number of observations to use for testing.
            h_future: Number of future periods to forecast.
            
        Returns:
            Dictionary containing:
            - model: Model identifier string
            - stats: Dictionary of model statistics (MAE, RMSE, MAPE)
            - comparison: Actual vs predicted for test period
            - forecast: Future forecast with confidence bands
            - historical: Full historical data
            - opinion: Model quality assessment
        """
        # Support single window as int
        if isinstance(windows, int):
            windows = [windows]
        
        logger.info(f"Running MA analysis: windows={windows}, n_test={n_test}, h_future={h_future}")
        
        all_test_preds = []
        all_future_preds = []
        
        for window in windows:
            # Test phase predictions
            test_preds = []
            for i in range(n_test):
                hist = self.data.iloc[:-(n_test - i)]
                test_preds.append(hist.tail(window).mean())
            all_test_preds.append(test_preds)
            
            # Future prediction
            last_val = self.data.tail(window).mean()
            all_future_preds.append([last_val] * h_future)
        
        # Ensemble: average across all windows
        fc_test = pd.Series(
            np.mean(all_test_preds, axis=0),
            index=self.data.index[-n_test:]
        )
        fc_future = np.mean(all_future_preds, axis=0)
        
        test_actual = self.data.iloc[-n_test:]
        
        # Calculate metrics
        mae = mean_absolute_error(test_actual, fc_test)
        rmse = np.sqrt(mean_squared_error(test_actual, fc_test))
        mape = (
            np.mean(np.abs((test_actual - fc_test) / test_actual)) * 100
            if (test_actual != 0).all()
            else 999
        )
        
        logger.info(f"MA metrics: MAE={mae:.4f}, RMSE={rmse:.4f}, MAPE={mape:.2f}%")
        
        # Generate future dates
        future_index = pd.date_range(
            start=self.data.index[-1],
            periods=h_future + 1,
            freq=self.inferred_freq
        )[1:]
        
        # Differences
        test_diff = test_actual.diff().fillna(0)
        fc_test_diff = fc_test.diff().fillna(0)
        
        # Model name
        model_name = (
            f"MA({','.join(map(str, windows))})"
            if len(windows) > 1
            else f"MA({windows[0]})"
        )
        
        # Generate opinion
        opinion = self._generate_opinion(model_name, mape, rmse)
        
        return {
            "model": model_name,
            "stats": {
                "MAE": float(mae),
                "RMSE": float(rmse),
                "MAPE": float(mape),
                "Windows": windows
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
                "sigma_1_up": [v + rmse for v in fc_future],
                "sigma_1_down": [v - rmse for v in fc_future],
                "sigma_2_up": [v + 2 * rmse for v in fc_future],
                "sigma_2_down": [v - 2 * rmse for v in fc_future],
            },
            "historical": self._get_chart_historical(months=120),
            "opinion": opinion
        }
    
    def _generate_opinion(self, model_name: str, mape: float, rmse: float) -> str:
        """
        Generate opinion about Moving Average model quality.
        
        Args:
            model_name: Name of the model (e.g., "MA(3)" or "MA(3,6,12)").
            mape: Mean Absolute Percentage Error.
            rmse: Root Mean Squared Error.
            
        Returns:
            Opinion string with quality assessment.
        """
        opinion = f"Model średniej kroczącej {model_name}. RMSE: {rmse:.4f}, MAPE: {mape:.2f}%. "
        
        if mape < 10:
            opinion += "Dobry dla stabilnych trendów."
        else:
            opinion += "Wysoka zmienność - rozważ ARIMA."
        
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
