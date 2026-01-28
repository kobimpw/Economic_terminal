"""
Klient News API
===============

Ten moduł zapewnia integrację z News API do pobierania i analizowania
artukułów prasowych związanych ze wskaźnikami ekonomicznymi.
Zawiera analizę sentymentu opartą na słowach kluczowych.

Funkcjonalności:
- Pobieranie ostatnich artykułów dla tematów ekonomicznych
- Ocena sentymentu oparta na NLP (analiza słów kluczowych)
- Konfigurowalne zapytania dla każdego wskaźnika
- Priorytetyzacja premiuḿowych źródeł informacji

Przykład użycia:
    from src.integrations import NewsAPIClient
    
    client = NewsAPIClient(api_key="twój_klucz_api")
    results = client.get_sentiment("T10Y2Y")
"""

import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import requests

from src.utils import get_logger, APIConnectionError

logger = get_logger(__name__)


# Premium news domains for financial news
NEWS_DOMAINS = (
    "bloomberg.com,wsj.com,ft.com,reuters.com,finance.yahoo.com,cnbc.com,marketwatch.com,"
    "forbes.com,businessinsider.com,barrons.com,kiplinger.com,thestreet.com,usnews.com,"
    "cnn.com,foxbusiness.com,seekingalpha.com,morningstar.com,benzinga.com,zacks.com,"
    "tipranks.com,tradingview.com,finviz.com,stockrover.com,vectorvest.com,chartmill.com,"
    "stocktwits.com,fool.com,investors.com,economist.com,marketplace.org,npr.org,"
    "calculatedriskblog.com,politico.com,axios.com,foxnews.com,washingtonexaminer.com,"
    "realclearpolitics.com,nytimes.com,washingtonpost.com,vox.com,theatlantic.com,"
    "theguardian.com,csis.org,stratfor.com,carnegieendowment.org,brookings.edu,"
    "thediplomat.com,foreignaffairs.com,nationalinterest.org,propublica.org,theintercept.com,"
    "nationalreview.com,reason.com,theblaze.com,nymag.com,newsmax.com,simplywall.st,"
    "msn.com,allbusiness.com,quora.com,reddit.com,ogj.com"
)

# Mapping of FRED series IDs to search terms
SEARCH_TERMS_MAP: Dict[str, str] = {
    "T10Y2Y": "treasury yield OR yield curve OR bond spread",
    "UMCSENT": "consumer sentiment OR consumer confidence",
    "HSN1F": "home sales OR housing market",
    "RRSFS": "retail sales OR consumer spending",
    "TOTALSA": "vehicle sales OR auto sales",
    "PERMIT": "building permits OR housing construction",
    "TCU": "capacity utilization OR manufacturing",
    "INDPRO": "industrial production OR manufacturing output",
    "CFNAI": "chicago fed OR economic activity",
    "JTSHIL": "job hires OR employment",
    "JTSJOL": "job openings OR JOLTS",
    "CCSA": "unemployment claims OR jobless claims",
    "TEMPHELPS": "temporary employment OR staffing",
    "CCLACBW027SBOG": "consumer credit OR lending",
    "WLCFLPCL": "bank credit OR commercial lending",
    "STLFSI4": "financial stress OR market volatility",
    "USALOLITOAASTSAM": "leading indicator OR economic outlook",
    "UNRATE": "unemployment rate OR jobs report",
}

# Sentiment analysis keywords
POSITIVE_WORDS: List[str] = [
    "rise", "growth", "strong", "beat", "good", "positive", "gain",
    "up", "surge", "boost", "improve", "better", "exceed", "optimistic",
    "recovery", "rebound", "bullish", "expansion", "profit"
]

NEGATIVE_WORDS: List[str] = [
    "fall", "drop", "weak", "miss", "bad", "negative", "decline",
    "down", "plunge", "concern", "worse", "below", "pessimistic", "risk",
    "recession", "contraction", "bearish", "loss", "crisis"
]


class NewsAPIClient:
    """
    Client for News API integration with sentiment analysis.
    
    This class fetches news articles and performs keyword-based
    sentiment analysis to score articles and calculate overall sentiment.
    
    Attributes:
        api_key (str): News API key.
        base_url (str): Base URL for News API.
    """
    
    BASE_URL = "https://newsapi.org/v2/everything"
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the News API client.
        
        Args:
            api_key: News API key. If not provided, reads from NEWS_API_KEY env var.
        """
        self.api_key = api_key or os.getenv("NEWS_API_KEY", "")
        if not self.api_key:
            logger.warning("News API key not configured")
    
    def get_sentiment(
        self,
        series_id: str,
        query: Optional[str] = None,
        days_back: int = 14,
        page_size: int = 30
    ) -> Dict:
        """
        Get news articles with sentiment analysis for an indicator.
        
        Fetches recent news articles related to the economic indicator
        and performs keyword-based sentiment scoring.
        
        Args:
            series_id: FRED series ID (e.g., "T10Y2Y", "UMCSENT").
            query: Custom search query. If None, uses default mapping.
            days_back: Number of days to look back for articles.
            page_size: Maximum number of articles to fetch.
            
        Returns:
            Dictionary containing:
            - articles: List of articles with sentiment scores
            - overall: Overall sentiment score (0-100)
            - overall_label: Sentiment label (Positive/Neutral/Negative)
            - count: Number of articles found
            - query_used: The search query used
            
        Raises:
            APIConnectionError: If the API request fails.
        """
        if not self.api_key:
            logger.error("News API key not configured")
            return self._error_response("API key not configured")
        
        # Get search query for this indicator
        search_query = query or SEARCH_TERMS_MAP.get(series_id, series_id)
        
        logger.info(f"Fetching news for {series_id}: query='{search_query}'")
        
        try:
            params = {
                "q": search_query,
                "apiKey": self.api_key,
                "pageSize": page_size,
                "sortBy": "relevancy",
                "language": "en",
                "from": (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
            }
            
            response = requests.get(self.BASE_URL, params=params, timeout=15)
            
            if response.status_code != 200:
                logger.warning(f"News API error: {response.status_code}")
                return self._error_response(f"API error: {response.status_code}")
            
            data = response.json()
            articles = data.get("articles", [])
            
            if not articles:
                logger.info(f"No articles found for {series_id}")
                return {
                    "articles": [],
                    "overall": 50,
                    "overall_label": "Neutral",
                    "count": 0,
                    "message": "No recent articles found",
                    "query_used": search_query
                }
            
            # Analyze sentiment for each article
            scored_articles = []
            total_sentiment = 0
            
            for art in articles:
                scored_article = self._analyze_article(art)
                scored_articles.append(scored_article)
                total_sentiment += scored_article["sentiment"]
            
            # Sort by date (newest first)
            scored_articles.sort(key=lambda x: x["publishedAt"], reverse=True)
            
            avg_sentiment = total_sentiment / len(scored_articles)
            
            logger.info(f"Found {len(scored_articles)} articles, avg sentiment: {avg_sentiment:.1f}")
            
            return {
                "articles": scored_articles,
                "overall": int(avg_sentiment),
                "overall_label": self._get_sentiment_label(avg_sentiment),
                "count": len(scored_articles),
                "query_used": search_query
            }
            
        except requests.RequestException as e:
            logger.error(f"News API request failed: {e}")
            raise APIConnectionError(
                f"News API request failed: {e}",
                api_name="News API"
            )
        except Exception as e:
            logger.error(f"News API error: {e}")
            return self._error_response(str(e))
    
    def _analyze_article(self, article: Dict) -> Dict:
        """
        Analyze sentiment for a single article.
        
        Uses keyword matching to calculate a sentiment score.
        
        Args:
            article: Article data from News API.
            
        Returns:
            Dictionary with article data and sentiment score.
        """
        title = article.get("title") or ""
        description = article.get("description") or ""
        text = (title + " " + description).lower()
        
        # Count sentiment words
        pos_count = sum(1 for w in POSITIVE_WORDS if w in text)
        neg_count = sum(1 for w in NEGATIVE_WORDS if w in text)
        
        # Calculate score (0-100 scale)
        score = 50 + (pos_count - neg_count) * 8
        score = max(0, min(100, score))
        
        return {
            "title": article.get("title", "No title"),
            "url": article.get("url", ""),
            "source": article.get("source", {}).get("name", "Unknown"),
            "publishedAt": article.get("publishedAt", ""),
            "sentiment": int(score),
            "sentiment_label": self._get_sentiment_label(score)
        }
    
    def _get_sentiment_label(self, score: float) -> str:
        """
        Convert sentiment score to label.
        
        Args:
            score: Sentiment score (0-100).
            
        Returns:
            Label: "Positive", "Negative", or "Neutral".
        """
        if score > 60:
            return "Positive"
        elif score < 40:
            return "Negative"
        return "Neutral"
    
    def _error_response(self, error_msg: str) -> Dict:
        """
        Generate error response dictionary.
        
        Args:
            error_msg: Error message.
            
        Returns:
            Error response dictionary.
        """
        return {
            "articles": [],
            "overall": 50,
            "overall_label": "Neutral",
            "count": 0,
            "error": error_msg
        }
