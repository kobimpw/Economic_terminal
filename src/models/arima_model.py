"""
Analizator Modelu ARIMA
=======================

Ten moduł zapewnia analizę modelu ARIMA (AutoRegressive Integrated Moving Average)
do prognozowania szeregów czasowych wskaźników ekonomicznych.

Model ARIMA jest dopasowywany na danych historycznych, oceniany na okresie testowym,
a następnie używany do prognozowania przyszłych wartości z przedziałami ufności.

Przykład użycia:
    from src.models import ARIMAAnalyzer
    
    analyzer = ARIMAAnalyzer(data, inferred_freq="MS")
    results = analyzer.analyze(order=(1, 1, 1), n_test=12, h_future=6)
"""

import warnings
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error
from src.utils import get_logger

logger = get_logger(__name__)


class ARIMAAnalyzer:
    """
    ARIMA model analyzer for time series forecasting.
    
    This class handles the complete ARIMA analysis workflow:
    - Train/test split
    - Model fitting
    - Forecast generation
    - Metrics calculation
    - Opinion generation
    
    Attributes:
        data (pd.Series): Time series data for analysis.
        inferred_freq (str): Inferred frequency of the data (e.g., 'MS', 'D').
    """
    
    def __init__(self, data: pd.Series, inferred_freq: str):
        """
        Initialize the ARIMA analyzer.
        
        Args:
            data: Time series data as pandas Series with DatetimeIndex.
            inferred_freq: Frequency of the time series (e.g., 'MS' for monthly).
        """
        self.data = data
        self.inferred_freq = inferred_freq
        logger.debug(f"Initialized ARIMAAnalyzer with {len(data)} observations")
    
    def analyze(
        self,
        order: Tuple[int, int, int] = (1, 1, 1),
        n_test: int = 12,
        h_future: int = 6
    ) -> Dict:
        """
        Perform complete ARIMA analysis with diagnostics.
        
        This method:
        1. Splits data into train/test sets
        2. Fits ARIMA on training data
        3. Evaluates on test data
        4. Refits on full data for future forecast
        5. Generates confidence intervals and opinion
        
        Args:
            order: ARIMA order as tuple (p, d, q).
            n_test: Number of observations to use for testing.
            h_future: Number of future periods to forecast.
            
        Returns:
            Dictionary containing:
            - model: Model identifier string
            - stats: Dictionary of model statistics (AIC, BIC, MAE, RMSE, MAPE)
            - params: Model parameters
            - pvalues: P-values for parameters
            - tstats: T-statistics for parameters
            - comparison: Actual vs predicted for test period
            - forecast: Future forecast with confidence bands
            - historical: Full historical data
            - opinion: AI-generated model quality assessment
        """
        logger.info(f"Running ARIMA{order} analysis: n_test={n_test}, h_future={h_future}")
        
        train = self.data.iloc[:-n_test]
        test = self.data.iloc[-n_test:]

        # Fit model on training data
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore")
            # Lazy import to speed up startup
            from statsmodels.tsa.arima.model import ARIMA
            model = ARIMA(train, order=order)
            res = model.fit()
            logger.debug(f"ARIMA model fitted on training data: AIC={res.aic:.2f}")

        # Test phase predictions
        fc_test = res.forecast(steps=n_test)
        mae = mean_absolute_error(test, fc_test)
        rmse = np.sqrt(mean_squared_error(test, fc_test))
        mape = np.mean(np.abs((test - fc_test) / test)) * 100 if (test != 0).all() else 999
        
        logger.info(f"Test metrics: MAE={mae:.4f}, RMSE={rmse:.4f}, MAPE={mape:.2f}%")

        # Fit on full data for future forecast
        # Fit on full data for future forecast
        # Lazy import (redundant if already imported but safe)
        from statsmodels.tsa.arima.model import ARIMA
        full_model = ARIMA(self.data, order=order)
        res_full = full_model.fit()
        fc_future = res_full.forecast(steps=h_future)

        # Generate future dates
        future_index = pd.date_range(
            start=self.data.index[-1],
            periods=h_future + 1,
            freq=self.inferred_freq
        )[1:]

        # Generate AI opinion
        metrics = {
            "MAE": mae,
            "RMSE": rmse,
            "MAPE": mape,
            "AIC": res_full.aic,
            "BIC": res_full.bic
        }
        opinion = self._generate_opinion(res_full, metrics)

        # Calculate differences for diff analysis
        test_diff = test.diff().fillna(0)
        fc_test_diff = pd.Series(fc_test).diff().fillna(0)

        return {
            "model": f"ARIMA{order}",
            "stats": {
                "AIC": float(res_full.aic),
                "BIC": float(res_full.bic),
                "HQIC": float(res_full.hqic),
                "MAE": float(mae),
                "RMSE": float(rmse),
                "MAPE": float(mape),
                "sigma": float(rmse)
            },
            "params": {k: float(v) for k, v in res_full.params.to_dict().items()},
            "pvalues": {k: float(v) for k, v in res_full.pvalues.to_dict().items()},
            "tstats": {k: float(v) for k, v in res_full.tvalues.to_dict().items()},
            "comparison": {
                "dates": test.index.strftime("%Y-%m-%d").tolist(),
                "actual": test.tolist(),
                "predict": fc_test.tolist(),
                "actual_diff": test_diff.tolist(),
                "predict_diff": fc_test_diff.tolist(),
                "diff_error": (test_diff - fc_test_diff).tolist()
            },
            "forecast": {
                "dates": future_index.strftime("%Y-%m-%d").tolist(),
                "values": fc_future.tolist(),
                "sigma_1_up": (fc_future + rmse).tolist(),
                "sigma_1_down": (fc_future - rmse).tolist(),
                "sigma_2_up": (fc_future + 2 * rmse).tolist(),
                "sigma_2_down": (fc_future - 2 * rmse).tolist(),
            },
            "historical": self._get_chart_historical(months=120),
            "opinion": opinion
        }
    
    def _generate_opinion(self, model_res, metrics: Dict) -> str:
        """
        Generate AI-style opinion about model quality.
        
        Evaluates MAPE, statistical significance, and information criteria
        to provide a comprehensive quality assessment.
        
        Args:
            model_res: Fitted ARIMA model result object.
            metrics: Dictionary with MAE, RMSE, MAPE, AIC, BIC.
            
        Returns:
            Markdown-formatted opinion string.
        """
        msg = "**Analiza Jakości Modelu ARIMA:**\n\n"
        
        mape = metrics.get("MAPE", 100)
        if mape < 5:
            msg += "✅ **Doskonałe dopasowanie** - MAPE < 5%. Model wykazuje bardzo wysoką precyzję.\n"
        elif mape < 10:
            msg += "✅ **Dobre dopasowanie** - MAPE < 10%. Model jest wiarygodny do prognozowania.\n"
        elif mape < 15:
            msg += "⚠️ **Zadowalające dopasowanie** - MAPE < 15%. Używaj z ostrożnością.\n"
        else:
            msg += "❌ **Słabe dopasowanie** - MAPE > 15%. Model ma ograniczoną wartość predykcyjną.\n"
        
        # Statistical significance
        sig_count = sum(1 for p in model_res.pvalues if p < 0.05)
        total_params = len(model_res.pvalues)
        msg += f"\n**Istotność statystyczna:** {sig_count}/{total_params} parametrów istotnych (p < 0.05).\n"
        
        if sig_count < total_params / 2:
            msg += "⚠️ Większość parametrów nieistotna - rozważ uproszczenie modelu.\n"
        
        # Information criteria
        aic = metrics.get("AIC", 0)
        bic = metrics.get("BIC", 0)
        msg += f"\n**Kryteria informacyjne:** AIC={aic:.2f}, BIC={bic:.2f}\n"
        msg += "💡 Niższe wartości AIC/BIC wskazują na lepszy model.\n"
        
        return msg
    
    def _get_chart_historical(self, months: int = 120) -> dict:
        """
        Zwraca dane historyczne ograniczone do ostatnich N miesięcy.
        
        Dla danych dziennych (np. T10Y2Y) zapobiega to zwracaniu tysięcy punktów.
        
        Args:
            months: Liczba miesięcy do zwrócenia (domyślnie 12)
            
        Returns:
            Słownik z datami i wartościami dla ostatnich N miesięcy
        """
        from datetime import datetime
        from dateutil.relativedelta import relativedelta
        
        cutoff_date = datetime.now() - relativedelta(months=months)
        
        # Filtruj dane do ostatnich N miesięcy
        filtered = self.data[self.data.index >= cutoff_date]
        
        # Jeśli brak danych po filtrze, zwróć wszystko
        if filtered.empty:
            filtered = self.data
        
        return {
            "dates": filtered.index.strftime("%Y-%m-%d").tolist(),
            "values": filtered.tolist()
        }

