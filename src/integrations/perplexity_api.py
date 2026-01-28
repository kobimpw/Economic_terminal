"""
Klient Perplexity AI
====================

Ten moduł zapewnia integrację z Perplexity AI do generowania
analiz wskaźników ekonomicznych wspomaganych sztuczną inteligencją.

Funkcjonalności:
- Analiza wskaźników ekonomicznych w języku naturalnym
- Integracja ze źródłami danych FRED
- Wsparcie dla cytatów z odpowiedzi Perplexity
- Obsługa limitów i błędów

Przykład użycia:
    from src.integrations import PerplexityClient
    
    client = PerplexityClient(api_key="twój_klucz_api")
    results = client.get_research("UMCSENT", indicator_name="Consumer Sentiment")
"""

import os
from datetime import datetime
from typing import Dict, Optional

import requests

from src.utils import get_logger, APIConnectionError

logger = get_logger(__name__)


class PerplexityClient:
    """
    Client for Perplexity AI API integration.
    
    This class provides methods for generating AI-powered research
    and analysis of economic indicators using Perplexity's API.
    
    Attributes:
        api_key (str): Perplexity API key.
        base_url (str): Base URL for Perplexity API.
        model (str): Perplexity model to use.
    """
    
    BASE_URL = "https://api.perplexity.ai/chat/completions"
    DEFAULT_MODEL = "sonar"
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize the Perplexity AI client.
        
        Args:
            api_key: Perplexity API key. If not provided, reads from env var.
            model: Perplexity model to use. Defaults to "sonar".
        """
        self.api_key = api_key or os.getenv("PERPLEXITY_API_KEY", "")
        self.model = model or self.DEFAULT_MODEL
        
        if not self.api_key:
            logger.warning("Perplexity API key not configured")
    
    def get_research(
        self,
        series_id: str,
        indicator_name: Optional[str] = None,
        temperature: float = 0.4,
        max_tokens: int = 1000
    ) -> Dict:
        """
        Get AI-powered research from Perplexity with FRED link context.
        
        Generates a comprehensive analysis of the economic indicator
        including current trends, drivers, and short-term forecast.
        
        Args:
            series_id: FRED series ID (e.g., "UMCSENT").
            indicator_name: Human-readable name of the indicator.
            temperature: Model temperature for response generation.
            max_tokens: Maximum tokens in response.
            
        Returns:
            Dictionary containing:
            - summary: AI-generated analysis text
            - outlook: Status indicator (ANALYZED/ERROR)
            - sources: List of citations/sources
            - timestamp: When the research was generated
            
        Raises:
            APIConnectionError: If the API request fails.
        """
        if not self.api_key:
            logger.error("Perplexity API key not configured")
            return self._error_response("API key not configured")
        
        query = indicator_name or series_id
        fred_link = f"https://fred.stlouisfed.org/series/{series_id}"
        
        logger.info(f"Requesting Perplexity research for {series_id}")
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a professional macroeconomic analyst. "
                            "Provide concise, data-driven analysis with citations."
                        )
                    },
                    {
                        "role": "user",
                        "content": self._build_prompt(query, fred_link)
                    }
                ],
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            
            response = requests.post(
                self.BASE_URL,
                json=payload,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                citations = data.get("citations", [])
                
                logger.info(f"Perplexity research generated for {series_id}")
                
                return {
                    "summary": content,
                    "outlook": "ANALYZED",
                    "sources": citations if citations else ["Perplexity AI Online Search"],
                    "timestamp": datetime.now().isoformat()
                }
            else:
                # Handle API error
                error_msg = self._parse_error(response)
                logger.warning(f"Perplexity API error {response.status_code}: {error_msg}")
                
                return {
                    "summary": f"⚠️ Research service error ({response.status_code}): {error_msg}",
                    "outlook": "ERROR",
                    "sources": [],
                    "timestamp": datetime.now().isoformat()
                }
                
        except requests.RequestException as e:
            logger.error(f"Perplexity API request failed: {e}")
            raise APIConnectionError(
                f"Perplexity API request failed: {e}",
                api_name="Perplexity AI"
            )
        except Exception as e:
            logger.error(f"Perplexity API error: {e}")
            return self._error_response(str(e))
    
    def _build_prompt(self, query: str, fred_link: str) -> str:
        """
        Build the analysis prompt for Perplexity.
        
        Args:
            query: Indicator name or ID.
            fred_link: Link to FRED data source.
            
        Returns:
            Formatted prompt string.
        """
        return f"""Analyze the current state and short-term forecast for the {query} indicator of the US economy.

Reference data source: {fred_link}

Provide:
1. Current trend (3 bullet points)
2. Key drivers and recent developments
3. Short-term forecast (next 3-6 months)
4. Include markdown links to sources

Keep it concise and actionable."""
    
    def _parse_error(self, response: requests.Response) -> str:
        """
        Parse error message from API response.
        
        Args:
            response: HTTP response object.
            
        Returns:
            Error message string.
        """
        try:
            error_data = response.json()
            return error_data.get("error", {}).get("message", response.text)
        except Exception:
            return response.text
    
    def _error_response(self, error_msg: str) -> Dict:
        """
        Generate error response dictionary.
        
        Args:
            error_msg: Error message.
            
        Returns:
            Error response dictionary.
        """
        return {
            "summary": f"Research service temporarily unavailable: {error_msg}",
            "outlook": "ERROR",
            "sources": [],
            "timestamp": datetime.now().isoformat()
        }
