"""
Advanced Macro Trading Terminal - FastAPI Backend
Professional REST API for economic indicator analysis
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from src.core.predictor import PredictorCore
import os
import sqlite3
import subprocess
from dotenv import load_dotenv
from datetime import datetime, date
from collections import defaultdict

# Load environment variables
load_dotenv()

# Get API key from environment
FRED_API_KEY = os.getenv("FRED_API_KEY", "")

# Ścieżki do baz danych (nowa struktura - folder data/)
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
STOCKS_DB_PATH = os.path.join(DATA_DIR, "gielda_earning.db")
ECONOMIC_DB_PATH = os.path.join(DATA_DIR, "economic_calendar.db")

# Ensure DATA_DIR exists
os.makedirs(DATA_DIR, exist_ok=True)

app = FastAPI(title="Macro Trading Terminal", version="3.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Templates and static files
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# Mount static files
static_dir = os.path.join(BASE_DIR, "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Indicators dictionary with display names
# Indicators loaded from config
from config import INDICATORS

# Global predictor instance
_predictor = None
# Cache for precomputed best models
PRECOMPUTED_MODELS: Dict[str, Any] = {}

def get_predictor() -> PredictorCore:
    """Get or create PredictorCore instance"""
    global _predictor
    if _predictor is None:
        if not FRED_API_KEY:
            raise HTTPException(status_code=500, detail="FRED_API_KEY not configured in .env")
        _predictor = PredictorCore(FRED_API_KEY)
    return _predictor



def precompute_all_models():
    """
    Launch background worker to precompute models.
    Uses subprocess to avoid blocking the main server thread/GIL.
    """
    import subprocess
    import sys
    
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "precompute_worker.py")
    
    # Check if worker is already running (simple check)
    # Windows doesn't have easy 'pgrep', so we just blindly launch or rely on lock file.
    # For this MVP, we just launch.
    
    try:
        if os.name == 'nt':
            # Windows: CREATE_NO_WINDOW to hide console
            subprocess.Popen([sys.executable, script_path], 
                             creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            subprocess.Popen([sys.executable, script_path])
            
        print("[*] Background precomputation worker started")
    except Exception as e:
        print(f"[!] Failed to start precomputation worker: {e}")

# Start precomputation on module load
precompute_all_models()



# ============================================
# REQUEST MODELS
# ============================================

class AnalysisRequest(BaseModel):
    series_id: str
    model_type: str = "ARIMA"
    order: Optional[List[int]] = [1, 1, 1]
    windows: Optional[List[int]] = [3, 6, 12]
    simulations: Optional[int] = 1000
    n_test: int = 12
    h_future: int = 6


# ============================================
# HTML ROUTES
# ============================================

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serve main HTML page"""
    return templates.TemplateResponse("index.html", {"request": request})


# ============================================
# API ROUTES
# ============================================

@app.get("/api/calendar")
async def get_calendar():
    """Get calendar of indicators grouped by release date (Chronological)"""
    try:
        core = get_predictor()
        from dateutil import parser
        import concurrent.futures
        
        # Build calendar data
        calendar_data = {}
        
        # Helper function for parallel execution
        def fetch_date(sid, meta):
            # DISABLED SCRAPING: To prevent loading hangs
            # return sid, meta, "TBD"
            try:
                # next_date = core.get_next_release(sid) # SKIPPED
                 return sid, meta, "TBD"
            except Exception as e:
                print(f"Error fetching release for {sid}: {e}")
                return sid, meta, "TBD"

        # Run fetching in parallel threads
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_sid = {executor.submit(fetch_date, sid, meta): sid for sid, meta in INDICATORS.items()}
            for future in concurrent.futures.as_completed(future_to_sid):
                results.append(future.result())

        # Process results
        for sid, meta, next_date in results:
            try:
                # Normalize date key to ISO format for sorting
                date_key = "9999-12-31" # Default for TBD/Error (end of list)
                display_date = next_date
                
                if next_date not in ["TBD", "N/A", "Error"]:
                    try:
                        # Try parsing date
                        dt = parser.parse(next_date, fuzzy=True)
                        date_key = dt.strftime("%Y-%m-%d")
                        display_date = date_key # Use ISO for key
                    except:
                        # If parsing fails or TBD, default to today to ensure it's visible in Daily AI
                        date_key = date.today().strftime("%Y-%m-%d")
                else:
                    # If date is TBD/Error, pin to today so it's visible in Daily AI as "Active Indicators"
                    date_key = date.today().strftime("%Y-%m-%d")
                
                if date_key not in calendar_data:
                    calendar_data[date_key] = []
                
                calendar_data[date_key].append({
                    "series_id": sid,
                    "name": meta["name"],
                    "display_name": meta["display_name"],
                    "category": meta["category"],
                    "release_text": next_date, # Keep original text for display
                    "sort_date": date_key
                })
            except Exception as e:
                print(f"Error processing {sid}: {e}")
                continue
        
        # ====== DODAJ DANE SPÓŁEK S&P 500 ======
        if os.path.exists(STOCKS_DB_PATH):
            try:
                conn = sqlite3.connect(STOCKS_DB_PATH)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                # Fetch earnings for today and future
                today_str = date.today().strftime("%Y-%m-%d")
                cursor.execute("SELECT * FROM sp500_earning WHERE \"Earnings Date\" >= ? ORDER BY \"Earnings Date\" LIMIT 50", (today_str,))
                for row in cursor.fetchall():
                    stock = dict(row)
                    d_key = stock.get("Earnings Date", "9999-12-31")
                    if d_key not in calendar_data:
                        calendar_data[d_key] = []
                    
                    calendar_data[d_key].append({
                        "type": "stock",
                        "series_id": f"STOCK_{stock.get('ticker')}",
                        "ticker": stock.get("ticker"),
                        "name": stock.get("company_name"),
                        "display_name": f"{stock.get('ticker')} - {stock.get('company_name')}",
                        "market_cap": stock.get("market_cap"),
                        "price": stock.get("price"),
                        "change_pct": stock.get("change%"),
                        "revenue": stock.get("revenue"),
                        "price_target": stock.get("Price Target"),
                        "analysts": stock.get("analysts"),
                        "link": stock.get("link"),
                        "category": "Earnings",
                        "release_text": stock.get("Earnings Date"),
                        "sort_date": d_key
                    })
                conn.close()
            except Exception as e:
                print(f"Error merging stocks: {e}")
        
        # ====== DODAJ KALENDARZ EKONOMICZNY ======
        if os.path.exists(ECONOMIC_DB_PATH):
            try:
                conn = sqlite3.connect(ECONOMIC_DB_PATH)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                today_str = date.today().strftime("%Y-%m-%d")
                cursor.execute("SELECT * FROM economic_events WHERE Date >= ? ORDER BY Date LIMIT 50", (today_str,))
                for row in cursor.fetchall():
                    event = dict(row)
                    d_key = event.get("Date")
                    if d_key not in calendar_data:
                        calendar_data[d_key] = []
                        
                    calendar_data[d_key].append({
                        "type": "economic",
                        "series_id": f"ECON_{event.get('Event')[:30]}",
                        "name": event.get("Event"),
                        "display_name": event.get("Event"),
                        "category": "Economic Calendar",
                        "time": event.get("Time"),
                        "country": event.get("Country"),
                        "actual": event.get("Actual"),
                        "previous": event.get("Previous"),
                        "consensus": event.get("Consensus"),
                        "forecast": event.get("Forecast"),
                        "link": event.get("Link"),
                        "release_text": f"{event.get('Time')} {event.get('Country')}",
                        "sort_date": d_key
                    })
                conn.close()
            except Exception as e:
                print(f"Error merging economic calendar: {e}")
        
        print("DEBUG: Calendar fetch complete, returning data")
        
        # Sort calendar by date key
        sorted_keys = sorted(calendar_data.keys())
        sorted_calendar = {k: calendar_data[k] for k in sorted_keys}
        
        return sorted_calendar
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/calendar/stocks")
async def get_stocks_calendar():
    """Get S&P 500 earnings calendar from SQLite database"""
    try:
        if not os.path.exists(STOCKS_DB_PATH):
            return {"error": "Database not found. Run tickery.py first."}
        
        today_str = date.today().strftime("%Y-%m-%d")
        conn = sqlite3.connect(STOCKS_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sp500_earning WHERE \"Earnings Date\" >= ? ORDER BY \"Earnings Date\"", (today_str,))
        stocks = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return {"count": len(stocks), "stocks": stocks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/calendar/economic")
async def get_economic_calendar():
    """Get economic calendar from SQLite database"""
    try:
        if not os.path.exists(ECONOMIC_DB_PATH):
            return {"error": "Database not found. Run TE.py first."}
        
        today_str = date.today().strftime("%Y-%m-%d")
        conn = sqlite3.connect(ECONOMIC_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM economic_events WHERE Date >= ? ORDER BY Date", (today_str,))
        events = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return {"count": len(events), "events": events}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/refresh/stocks")
async def refresh_stocks_data():
    """Refresh S&P 500 stocks data using StocksScraper"""
    try:
        from src.integrations import StocksScraper
        
        scraper = StocksScraper(db_path=STOCKS_DB_PATH)
        df = scraper.run()
        
        if not df.empty:
            return {"status": "success", "message": f"Stocks data refreshed successfully ({len(df)} stocks)"}
        else:
            return {"status": "error", "message": "No data retrieved"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/refresh/economic")
async def refresh_economic_data():
    """Refresh economic calendar data using EconomicCalendarScraper"""
    try:
        from src.integrations import EconomicCalendarScraper
        
        scraper = EconomicCalendarScraper(db_path=ECONOMIC_DB_PATH, headless=True)
        df = scraper.run()
        
        if not df.empty:
            return {"status": "success", "message": f"Economic calendar refreshed successfully ({len(df)} events)"}
        else:
            return {"status": "error", "message": "No data retrieved"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/precomputed/{series_id}")
async def get_precomputed_model(series_id: str):
    """
    Get precomputed best model results for a FRED series.
    Returns cached results if available, otherwise computes on-demand.
    """
    try:
        # Check cache first
        if series_id in PRECOMPUTED_MODELS and "result" in PRECOMPUTED_MODELS[series_id]:
            cached = PRECOMPUTED_MODELS[series_id]
            return {
                "cached": True,
                "best_model": cached["best_model"],
                "computed_at": cached["computed_at"],
                "result": cached["result"]
            }
        
        # Check disk cache (JSON file)
        import json
        json_path = os.path.join(DATA_DIR, "precomputed_models.json")
        if os.path.exists(json_path):
            try:
                # Optimized: Only read if we assume it might be there. 
                # Reading whole file every request is slow, but better than recomputing.
                # Ideally we should load this into memory periodically or on demand.
                with open(json_path, 'r') as f:
                    disk_cache = json.load(f)
                    if series_id in disk_cache and "result" in disk_cache[series_id]:
                        # Update memory cache
                        PRECOMPUTED_MODELS[series_id] = disk_cache[series_id]
                        cached = disk_cache[series_id]
                        return {
                            "cached": True,
                            "source": "disk",
                            "best_model": cached["best_model"],
                            "computed_at": cached["computed_at"],
                            "result": cached["result"]
                        }
            except Exception as e:
                print(f"Error reading precompute cache: {e}")

        
        # Compute on-demand if not cached
        core = get_predictor()
        core.fetch_data(series_id)
        result = core.find_best_model(n_test=12, h_future=6)
        
        # Cache the result
        PRECOMPUTED_MODELS[series_id] = {
            "result": result,
            "best_model": result.get("best_model", "unknown"),
            "computed_at": datetime.now().isoformat()
        }
        
        return {
            "cached": False,
            "best_model": result.get("best_model"),
            "result": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/precomputed")
async def get_all_precomputed():
    """Get status of all precomputed models."""
    return {
        "count": len(PRECOMPUTED_MODELS),
        "ready": sum(1 for v in PRECOMPUTED_MODELS.values() if "result" in v),
        "errors": sum(1 for v in PRECOMPUTED_MODELS.values() if "error" in v),
        "models": {
            sid: {
                "best_model": v.get("best_model", "pending" if "error" not in v else "error"),
                "computed_at": v.get("computed_at"),
                "error": v.get("error")
            }
            for sid, v in PRECOMPUTED_MODELS.items()
        }
    }

@app.post("/api/analyze")
async def analyze(req: AnalysisRequest):
    """Run analysis on indicator with selected model"""
    try:
        core = get_predictor()
        core.fetch_data(req.series_id, n_test=req.n_test)
        
        if req.model_type == "ARIMA":
            order = tuple(req.order) if req.order else (1, 1, 1)
            results = core.analyze_arima(
                order=order,
                n_test=req.n_test,
                h_future=req.h_future
            )
        elif req.model_type == "MovingAverage":
            results = core.analyze_moving_average(
                windows=req.windows or [3],
                n_test=req.n_test,
                h_future=req.h_future
            )
        elif req.model_type == "MonteCarlo":
            results = core.analyze_monte_carlo(
                simulations=req.simulations or 1000,
                n_test=req.n_test,
                h_future=req.h_future
            )
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported model type: {req.model_type}")
        
        # Add metadata
        results["series_id"] = req.series_id
        results["series_name"] = INDICATORS.get(req.series_id, {}).get("display_name", req.series_id)
        results["fred_link"] = f"https://fred.stlouisfed.org/series/{req.series_id}"
        
        return results
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/correlation/{series_id}")
async def get_correlation(series_id: str):
    """Get market correlation analysis for indicator"""
    try:
        core = get_predictor()
        # core.fetch_data(series_id) # Assumes data already fetched by analyze, but safest to fetch if missing
        if core.series_id != series_id or core.df is None:
             core.fetch_data(series_id)
             
        correlations = core.get_market_correlation(series_id)
        return correlations
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/market_glance")
async def get_market_glance():
    """Get Top ETF overview"""
    try:
        core = get_predictor()
        return core.get_market_glance()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class ResearchRequest(BaseModel):
    series_id: str
    query: Optional[str] = None

@app.post("/api/research")
async def post_research(req: ResearchRequest):
    """Get Perplexity AI research with custom query (POST)"""
    try:
        core = get_predictor()
        indicator_name = INDICATORS.get(req.series_id, {}).get("display_name", req.series_id)
        custom_query = req.query if req.query else indicator_name
        return core.get_perplexity_research(req.series_id, custom_query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/research/{series_id}")
async def get_research(series_id: str):
    """Get Perplexity AI research (GET - for backward compatibility)"""
    try:
        core = get_predictor()
        indicator_name = INDICATORS.get(series_id, {}).get("display_name", series_id)
        return core.get_perplexity_research(series_id, indicator_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/news/{series_id}")
async def get_news(series_id: str):
    """Get news sentiment analysis for indicator"""
    try:
        core = get_predictor()
        # Don't pass indicator_name - let get_news_sentiment use its internal search_terms_map
        return core.get_news_sentiment(series_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "fred_api": bool(FRED_API_KEY),
        "perplexity_api": bool(os.getenv("PERPLEXITY_API_KEY")),
        "news_api": bool(os.getenv("NEWS_API_KEY")),
        "timestamp": datetime.now().isoformat()
    }


# ============================================
# YAHOO FINANCE CHART DATA
# ============================================

@app.get("/api/stocks/chart/{ticker}")
async def get_stock_chart(ticker: str):
    """Get 1-year price history for a stock from Yahoo Finance"""
    try:
        import yfinance as yf
        
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1y")
        
        if hist.empty:
            return {"error": f"No data found for {ticker}"}
        
        # Convert to separate arrays for frontend Chart.js
        dates = [idx.strftime("%Y-%m-%d") for idx, _ in hist.iterrows()]
        prices = [round(row["Close"], 2) for _, row in hist.iterrows()]
        
        return {
            "ticker": ticker,
            "period": "1y",
            "count": len(dates),
            "dates": dates,
            "prices": prices
        }
    except ImportError:
        return {"error": "yfinance not installed. Run: pip install yfinance"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# DAILY AI SUMMARY
# ============================================

class DailySummaryRequest(BaseModel):
    date: str
    events: List[Dict[str, Any]]

@app.post("/api/ai/daily-summary")
async def generate_daily_summary(req: DailySummaryRequest):
    """Generate AI analytical article for a specific day's events"""
    try:
        import requests
        
        PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
        if not PERPLEXITY_API_KEY:
            return {"error": "PERPLEXITY_API_KEY not configured"}
        
        # Build events description
        events_text = ""
        for i, event in enumerate(req.events, 1):
            events_text += f"\n{i}. {event.get('display_name', event.get('name', 'Unknown'))}"
            if event.get('type') == 'stock':
                events_text += f" (Ticker: {event.get('ticker', '')}, Earnings - Market Cap: {event.get('market_cap', 'N/A')}, Price Target: {event.get('price_target', 'N/A')})"
            elif event.get('type') == 'economic':
                events_text += f" (Economic - Previous: {event.get('previous', 'N/A')}, Consensus: {event.get('consensus', 'N/A')})"
            else:
                events_text += f" (FRED ID: {event.get('series_id', '')}, Category: {event.get('category', '')})"
        
        prompt = f"""You are a top-tier financial analyst writing a premium daily market briefing.

**SCENARIO CONTEXT:**
Date: {req.date}.
Data status: The events listed below are CONFIRMED FACTS.
Goal: Write ONE cohesive, in-depth analytical article split into 5 distinct sections.

**Instructions:**
1. **Structure**: The output must be 5 separate sections that flow logically (e.g., Macro Overview -> Specific Data Deep Dive -> Sector Impact -> Market Sentiment -> Forward Outlook).
2. **Content**:
   - Each section must be ~150-200 words (substantial analysis, not short tweets).
   - Each section must start with a **Balanced but Engaging HOOK** (a strong opening sentence).
   - The analysis must be deep, professional, and actionable for institutional investors.
   - Use the provided event data as the core, but use your knowledge to explain *why* it matters (historical context, correlations).
   - **IMPORTANT**: Do NOT use Markdown bolding (like **text**) or brackets in the final output. Use plain text only.

3. **Format per Section**:
   - Start with `---POST X---`
   - [Hook Sentence]
   - [Deep Analysis Paragraphs - PLAIN TEXT, NO MARKDOWN BOLDING]
   - [Hashtags]
   - [Source Link] - Use a VALID Data Source URL if a specific news article is not found:
     * For Stocks: `https://stockanalysis.com/stocks/[TICKER]/`
     * For FRED data: `https://fred.stlouisfed.org/series/[FRED_ID]`
     * For Economic data: `https://tradingeconomics.com/united-states/calendar`
     * Do NOT invent fake news URLs.
   - End with `---END POST X---`

**Confirmed Events for {req.date} (with IDs for links):**
{events_text}

Generate the 5 sections now. Ensure they read like a single high-quality newsletter split into cards. PLAIN TEXT ONLY."""

        headers = {
            "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "sonar",
            "messages": [
                {"role": "system", "content": "You are a professional financial analyst specializing in macroeconomic analysis and equity markets. Write detailed, well-structured analytical reports."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 4000,
            "temperature": 0.9  # High temperature for creative analysis
        }
        
        response = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            return {
                "date": req.date,
                "events_count": len(req.events),
                "article": content,
                "generated_at": datetime.now().isoformat()
            }
        else:
            return {"error": f"API error: {response.status_code}", "details": response.text}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/calendar/events-by-date/{target_date}")
async def get_events_by_date(target_date: str):
    """Get all events for a specific date"""
    try:
        events = []
        
        # Get FRED events
        core = get_predictor()
        from dateutil import parser
        
        for sid, meta in INDICATORS.items():
            try:
                next_date = core.get_next_release(sid)
                if next_date not in ["TBD", "N/A", "Error"]:
                    dt = parser.parse(next_date, fuzzy=True)
                    if dt.strftime("%Y-%m-%d") == target_date:
                        events.append({
                            "type": "fred",
                            "series_id": sid,
                            "name": meta["name"],
                            "display_name": meta["display_name"],
                            "category": meta["category"]
                        })
            except:
                continue
        
        # Get stocks
        if os.path.exists(STOCKS_DB_PATH):
            conn = sqlite3.connect(STOCKS_DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM sp500_earning WHERE "Earnings Date" = ?', (target_date,))
            for row in cursor.fetchall():
                stock = dict(row)
                events.append({
                    "type": "stock",
                    "series_id": f"STOCK_{stock.get('ticker', '')}",
                    "name": stock.get("company_name", ""),
                    "display_name": f"{stock.get('ticker', '')} - {stock.get('company_name', '')}",
                    "category": "Earnings",
                    "ticker": stock.get("ticker", ""),
                    "market_cap": stock.get("market_cap", ""),
                    "price_target": stock.get("Price Target", "")
                })
            conn.close()
        
        # Get economic events
        if os.path.exists(ECONOMIC_DB_PATH):
            conn = sqlite3.connect(ECONOMIC_DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM economic_events WHERE Date = ?", (target_date,))
            for row in cursor.fetchall():
                event = dict(row)
                events.append({
                    "type": "economic",
                    "series_id": f"ECON_{event.get('Event', '')[:30]}",
                    "name": event.get("Event", ""),
                    "display_name": event.get("Event", ""),
                    "category": "Economic Calendar",
                    "time": event.get("Time", ""),
                    "previous": event.get("Previous", ""),
                    "consensus": event.get("Consensus", ""),
                    "forecast": event.get("Forecast", "")
                })
            conn.close()
        
        return {"date": target_date, "count": len(events), "events": events}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# MAIN
# ============================================

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 50)
    print("  Macro Trading Terminal v3.0")
    print("=" * 50)
    print(f"  FRED API: {'OK' if FRED_API_KEY else 'MISSING'}")
    print(f"  Perplexity: {'OK' if os.getenv('PERPLEXITY_API_KEY') else 'MISSING'}")
    print(f"  News API: {'OK' if os.getenv('NEWS_API_KEY') else 'MISSING'}")
    print("=" * 50)
    print("=" * 50)
    print("  Starting server at http://localhost:8001")
    print("=" * 50)
    
    uvicorn.run(app, host="0.0.0.0", port=8001)
