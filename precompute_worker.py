
"""
Precompute Model Worker
=======================

This script runs in the background to calculate best forecasting models
for all indicators in the system. It saves results to a JSON file
which is then read by the main application.
"""

import os
import sys
import json
import logging
import time
from datetime import datetime

# Setup path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import INDICATORS
from src.core.predictor import PredictorCore
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("precompute.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("precompute_worker")

# Constants
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
OUTPUT_FILE = os.path.join(DATA_DIR, "precomputed_models.json")

def main():
    logger.info("Starting background model precomputation...")
    load_dotenv()
    
    api_key = os.getenv("FRED_API_KEY")
    if not api_key:
        logger.error("FRED_API_KEY not found. Exiting.")
        return

    predictor = PredictorCore(api_key)
    
    # Load existing results if valid
    results = {}
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, 'r') as f:
                content = f.read()
                if content:
                    results = json.loads(content)
        except Exception as e:
            logger.warning(f"Could not load existing Cache: {e}")

    total = len(INDICATORS)
    logger.info(f"Processsing {total} indicators...")
    
    for i, (series_id, info) in enumerate(INDICATORS.items(), 1):
        if series_id in results and "result" in results[series_id]:
            # Skip if already computed recently (e.g. today)
            # For now, we'll recompute if it's been more than 24h or force recompute
            # Implementing simple check:
            last_computed = results[series_id].get("computed_at", "")
            if last_computed.startswith(datetime.now().strftime("%Y-%m-%d")):
                logger.info(f"[{i}/{total}] Skipping {series_id} (already computed today)")
                continue

        try:
            logger.info(f"[{i}/{total}] Computing model for {series_id}...")
            predictor.fetch_data(series_id)
            
            # Find best model
            result = predictor.find_best_model(n_test=12, h_future=6)
            
            # Serialize for JSON
            # Need to convert numpy types and non-serializable objects
            # predictor.find_best_model already returns mostly dicts, but let's be safe
            
            results[series_id] = {
                "result": result,
                "best_model": result.get("best_model", "unknown"),
                "computed_at": datetime.now().isoformat()
            }
            
            # Save intermediate results
            with open(OUTPUT_FILE, 'w') as f:
                json.dump(results, f, indent=2)
                
            logger.info(f"  → {series_id}: Success ({result.get('best_model')})")
            
        except Exception as e:
            logger.error(f"  → {series_id}: Failed ({e})")
            results[series_id] = {"error": str(e)}

    logger.info("Precomputation complete.")

if __name__ == "__main__":
    main()
