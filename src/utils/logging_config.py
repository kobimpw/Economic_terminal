"""
Moduł Konfiguracji Logowania
============================

Ten moduł zapewnia scentralizowaną konfigurację logowania dla aplikacji terminala.
Konfiguruje formatery, handlery i dostarcza funkcję fabryczną do tworzenia loggerów.

Użycie:
    from src.utils import setup_logging, get_logger
    
    setup_logging(level="DEBUG")
    logger = get_logger(__name__)
    logger.info("Aplikacja uruchomiona")
"""

import logging
import sys
from datetime import datetime
from typing import Optional


# Default log format
DEFAULT_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Color codes for terminal output
COLORS = {
    "DEBUG": "\033[36m",      # Cyan
    "INFO": "\033[32m",       # Green
    "WARNING": "\033[33m",    # Yellow
    "ERROR": "\033[31m",      # Red
    "CRITICAL": "\033[35m",   # Magenta
    "RESET": "\033[0m"        # Reset
}


class ColoredFormatter(logging.Formatter):
    """
    Custom formatter that adds colors to log levels in terminal output.
    
    Attributes:
        use_colors (bool): Whether to use ANSI color codes in output.
    """
    
    def __init__(
        self,
        fmt: str = DEFAULT_FORMAT,
        datefmt: str = DEFAULT_DATE_FORMAT,
        use_colors: bool = True
    ):
        """
        Initialize the colored formatter.
        
        Args:
            fmt: Log message format string.
            datefmt: Date format string.
            use_colors: Whether to use ANSI colors (disable for file output).
        """
        super().__init__(fmt, datefmt)
        self.use_colors = use_colors
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format the log record with optional colors.
        
        Args:
            record: The log record to format.
            
        Returns:
            Formatted log string with or without colors.
        """
        if self.use_colors and record.levelname in COLORS:
            record.levelname = (
                f"{COLORS[record.levelname]}{record.levelname}{COLORS['RESET']}"
            )
        return super().format(record)


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    use_colors: bool = True
) -> None:
    """
    Configure logging for the entire application.
    
    Sets up console handler with optional colors and an optional file handler.
    This function should be called once at application startup.
    
    Args:
        level: Logging level as string (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_file: Optional path to log file. If None, only console output is used.
        use_colors: Whether to use colored output in console.
        
    Example:
        >>> setup_logging(level="DEBUG", log_file="app.log")
        >>> logger = get_logger("my_module")
        >>> logger.info("This will be logged to console and file")
    """
    # Convert string level to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()
    
    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_formatter = ColoredFormatter(use_colors=use_colors)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # Optional file handler (no colors)
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(numeric_level)
        file_formatter = logging.Formatter(DEFAULT_FORMAT, DEFAULT_DATE_FORMAT)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    
    # Suppress noisy third-party loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("yfinance").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for the specified module.
    
    This is a convenience function that returns a properly named logger.
    Call setup_logging() before using this function.
    
    Args:
        name: Name of the module (typically __name__).
        
    Returns:
        A configured Logger instance.
        
    Example:
        >>> logger = get_logger(__name__)
        >>> logger.debug("Debug message")
        >>> logger.info("Info message")
        >>> logger.warning("Warning message")
        >>> logger.error("Error message")
    """
    return logging.getLogger(name)
