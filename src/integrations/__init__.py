"""
Integrations Module
===================

Contains clients for external API services and scrapers:
- NewsAPIClient: News API for sentiment analysis
- PerplexityClient: Perplexity AI for research
- StocksScraper: S&P 500 earnings data from stockanalysis.com
- EconomicCalendarScraper: Economic calendar from TradingEconomics
"""

from .news_api import NewsAPIClient
from .perplexity_api import PerplexityClient
from .stocks_scraper import StocksScraper
from .economic_calendar import EconomicCalendarScraper

__all__ = [
    "NewsAPIClient",
    "PerplexityClient",
    "StocksScraper",
    "EconomicCalendarScraper",
]

