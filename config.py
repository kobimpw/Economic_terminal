"""
Configuration file for Advanced Macro Trading Terminal
Contains all series definitions, API settings, and default parameters
"""

# Economic Indicators Dictionary
SERIES_DICT = {
    "consumer_sentiment": "UMCSENT",
    "new_housing_sales": "HSN1F",
    "real_retail": "RRSFS",
    "vehicle_sales": "TOTALSA",
    "permits": "PERMIT",
    "capacity_utilization": "TCU",
    "industrial_production": "INDPRO",
    "OECD_composite": "USALOLITOAASTSAM",
    "chicago_fed_nationality": "CFNAI",
    "nonfarm": "JTSHIL",
    "jobopen": "JTSJOL",
    "continues_claims": "CCSA",
    "temporary": "TEMPHELPS",
    "consumer_credit": "CCLACBW027SBOG",
    "bank_credit": "WLCFLPCL",
    "financial_stress": "STLFSI4",
    "yield_curve_spread": "T10Y2Y",
    "unrate": "UNRATE",  # Unemployment Rate
    "sp500": "SP500"
}

# Human-readable names for indicators
SERIES_NAMES = {
    "UMCSENT": "Consumer Sentiment",
    "HSN1F": "New Housing Sales",
    "RRSFS": "Real Retail Sales",
    "TOTALSA": "Vehicle Sales",
    "PERMIT": "Building Permits",
    "TCU": "Capacity Utilization",
    "INDPRO": "Industrial Production",
    "USALOLITOAASTSAM": "OECD Composite Leading Indicator",
    "CFNAI": "Chicago Fed National Activity Index",
    "JTSHIL": "Nonfarm Job Hires",
    "JTSJOL": "Job Openings",
    "CCSA": "Continued Unemployment Claims",
    "TEMPHELPS": "Temporary Help Services",
    "CCLACBW027SBOG": "Consumer Credit",
    "WLCFLPCL": "Bank Credit",
    "STLFSI4": "St. Louis Fed Financial Stress Index",
    "T10Y2Y": "10Y-2Y Treasury Yield Spread",
    "UNRATE": "Unemployment Rate",
    "SP500": "SPX"
}

# Sector ETFs for correlation analysis
SECTOR_ETFS = {
    "^GSPC": "S&P 500",
    "XLI": "Industrials",
    "XLV": "Healthcare",
    "XLK": "Technology",
    "XLF": "Financials",
    "XLRE": "Real Estate",
    "XLU": "Utilities",
    "XLB": "Materials",
    "XLP": "Consumer Staples",
    "XLY": "Consumer Discretionary",
    "XLC": "Communication Services",
    "XLE": "Energy"
}

# Default model parameters
DEFAULT_PARAMS = {
    "ARIMA": {
        "order": (1, 1, 1),
        "n_test": 12,
        "h_future": 6
    },
    "Moving Average": {
        "windows": [3],
        "n_test": 12,
        "h_future": 6
    },
    "Monte Carlo": {
        "simulations": 1000,
        "n_test": 12,
        "h_future": 6
    }
}

# Chart period options
CHART_PERIODS = {
    "12M": 12,
    "2Y": 24,
    "5Y": 60,
    "10Y": 120,
    "Max": None
}

# Streamlit page configuration
PAGE_CONFIG = {
    "page_title": "Advanced Macro Trading Terminal",
    "page_icon": "📊",
    "layout": "wide",
    "initial_sidebar_state": "expanded"
}

# Color scheme (Bloomberg-inspired)
COLORS = {
    "primary": "#FF6B00",      # Orange
    "background": "#0A0E27",   # Dark blue
    "card_bg": "#1A1F3A",      # Card background
    "text": "#FFFFFF",         # White text
    "text_secondary": "#A0A0A0",  # Gray text
    "positive": "#00FF88",     # Green
    "negative": "#FF4444",     # Red
    "neutral": "#FFD700"       # Gold
}

# Cache TTL (in seconds)
CACHE_TTL = {
    "release_dates": 3600,     # 1 hour
    "market_data": 1800,       # 30 minutes
    "news": 900,               # 15 minutes
    "perplexity": 3600         # 1 hour
}

# Indicators dictionary with display names and metadata
INDICATORS = {
    "UMCSENT": {"name": "Consumer Sentiment", "display_name": "Consumer Sentiment", "category": "Consumer"},
    "HSN1F": {"name": "New Home Sales", "display_name": "New Home Sales", "category": "Housing"},
    "RRSFS": {"name": "Real Retail Sales", "display_name": "Real Retail Sales", "category": "Consumer"},
    "TOTALSA": {"name": "Vehicle Sales", "display_name": "Vehicle Sales", "category": "Consumer"},
    "PERMIT": {"name": "Building Permits", "display_name": "Building Permits", "category": "Housing"},
    "TCU": {"name": "Capacity Utilization", "display_name": "Capacity Utilization", "category": "Production"},
    "INDPRO": {"name": "Industrial Production", "display_name": "Industrial Production", "category": "Production"},
    "USALOLITOAASTSAM": {"name": "OECD Leading Indicator", "display_name": "OECD Composite Leading Indicator", "category": "Leading"},
    "CFNAI": {"name": "Chicago Fed Activity", "display_name": "Chicago Fed National Activity Index", "category": "Production"},
    "JTSHIL": {"name": "JOLTS Hires", "display_name": "Nonfarm Job Hires", "category": "Labor"},
    "JTSJOL": {"name": "JOLTS Job Openings", "display_name": "Job Openings (JOLTS)", "category": "Labor"},
    "CCSA": {"name": "Continued Claims", "display_name": "Continued Unemployment Claims", "category": "Labor"},
    "TEMPHELPS": {"name": "Temp Help Services", "display_name": "Temporary Help Services", "category": "Labor"},
    "CCLACBW027SBOG": {"name": "Consumer Credit", "display_name": "Consumer Credit", "category": "Credit"},
    "WLCFLPCL": {"name": "Bank Credit", "display_name": "Commercial Bank Credit", "category": "Credit"},
    "STLFSI4": {"name": "Financial Stress Index", "display_name": "St. Louis Fed Financial Stress Index", "category": "Financial"},
    "T10Y2Y": {"name": "Yield Curve (10Y-2Y)", "display_name": "10Y-2Y Treasury Yield Spread", "category": "Rates"},
    "UNRATE": {"name": "Unemployment Rate", "display_name": "Unemployment Rate", "category": "Labor"}
}

