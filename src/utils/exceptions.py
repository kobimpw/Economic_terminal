"""
Moduł Własnych Wyjątków
======================

Ten moduł definiuje własne klasy wyjątków dla aplikacji terminala.
Używanie specyficznych wyjątków pozwala na bardziej precyzyjną obsługę błędów
oraz lepsze komunikaty dla użytkowników.

Hierarchia wyjątków:
    TerminalBaseException
    ├── DataFetchError       - Błędy pobierania danych z FRED
    ├── APIConnectionError   - Błędy połączenia z zewnętrznymi API
    ├── ModelFitError        - Błędy podczas dopasowywania modelu
    └── ValidationError      - Błędy walidacji danych
"""

from typing import Optional


class TerminalBaseException(Exception):
    """
    Base exception class for all terminal-related errors.
    
    All custom exceptions in this application inherit from this class,
    allowing for easy catching of all terminal-specific errors.
    
    Attributes:
        message (str): Human-readable error description.
        details (Optional[dict]): Additional context about the error.
    """
    
    def __init__(self, message: str, details: Optional[dict] = None):
        """
        Initialize the base exception.
        
        Args:
            message: Human-readable error description.
            details: Optional dictionary with additional error context.
        """
        self.message = message
        self.details = details or {}
        super().__init__(self.message)
    
    def __str__(self) -> str:
        """Return string representation of the exception."""
        if self.details:
            return f"{self.message} | Details: {self.details}"
        return self.message


class DataFetchError(TerminalBaseException):
    """
    Exception raised when data fetching from FRED fails.
    
    This includes network errors, invalid series IDs, or data parsing issues.
    
    Example:
        >>> raise DataFetchError(
        ...     "Failed to fetch data for UMCSENT",
        ...     details={"series_id": "UMCSENT", "status_code": 404}
        ... )
    """
    
    def __init__(
        self,
        message: str,
        series_id: Optional[str] = None,
        details: Optional[dict] = None
    ):
        """
        Initialize the data fetch error.
        
        Args:
            message: Human-readable error description.
            series_id: The FRED series ID that failed to fetch.
            details: Optional dictionary with additional error context.
        """
        self.series_id = series_id
        error_details = details or {}
        if series_id:
            error_details["series_id"] = series_id
        super().__init__(message, error_details)


class APIConnectionError(TerminalBaseException):
    """
    Exception raised when connection to external API fails.
    
    This is used for News API, Perplexity AI, or other external services.
    
    Example:
        >>> raise APIConnectionError(
        ...     "News API connection failed",
        ...     api_name="News API",
        ...     details={"status_code": 500, "response": "Internal Server Error"}
        ... )
    """
    
    def __init__(
        self,
        message: str,
        api_name: Optional[str] = None,
        status_code: Optional[int] = None,
        details: Optional[dict] = None
    ):
        """
        Initialize the API connection error.
        
        Args:
            message: Human-readable error description.
            api_name: Name of the API that failed (e.g., "News API", "Perplexity").
            status_code: HTTP status code if applicable.
            details: Optional dictionary with additional error context.
        """
        self.api_name = api_name
        self.status_code = status_code
        error_details = details or {}
        if api_name:
            error_details["api_name"] = api_name
        if status_code:
            error_details["status_code"] = status_code
        super().__init__(message, error_details)


class ModelFitError(TerminalBaseException):
    """
    Exception raised when a prediction model fails to fit.
    
    This includes ARIMA convergence failures, invalid data, or numerical issues.
    
    Example:
        >>> raise ModelFitError(
        ...     "ARIMA model failed to converge",
        ...     model_type="ARIMA",
        ...     details={"order": (1, 1, 1), "n_observations": 50}
        ... )
    """
    
    def __init__(
        self,
        message: str,
        model_type: Optional[str] = None,
        details: Optional[dict] = None
    ):
        """
        Initialize the model fit error.
        
        Args:
            message: Human-readable error description.
            model_type: Type of model that failed (ARIMA, MA, Monte Carlo).
            details: Optional dictionary with additional error context.
        """
        self.model_type = model_type
        error_details = details or {}
        if model_type:
            error_details["model_type"] = model_type
        super().__init__(message, error_details)


class ValidationError(TerminalBaseException):
    """
    Exception raised when input validation fails.
    
    This is used for invalid parameters, malformed requests, or data issues.
    
    Example:
        >>> raise ValidationError(
        ...     "Invalid ARIMA order",
        ...     field="order",
        ...     details={"provided": (0, 0, 0), "expected": "positive integers"}
        ... )
    """
    
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        details: Optional[dict] = None
    ):
        """
        Initialize the validation error.
        
        Args:
            message: Human-readable error description.
            field: Name of the field that failed validation.
            details: Optional dictionary with additional error context.
        """
        self.field = field
        error_details = details or {}
        if field:
            error_details["field"] = field
        super().__init__(message, error_details)
