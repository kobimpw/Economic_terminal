
import time
import sys
import os

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("--- Starting Diagnosis ---")

t0 = time.time()
print("Importing app...")
from app import app, get_predictor, INDICATORS
t1 = time.time()
print(f"Import app took: {t1-t0:.4f}s")

t2 = time.time()
print("Initializing PredictorCore...")
core = get_predictor()
t3 = time.time()
print(f"PredictorCore init took: {t3-t2:.4f}s")

t4 = time.time()
print("Simulating get_calendar...")
# Mock async call
import asyncio
from app import get_calendar

async def test_calendar():
    start = time.time()
    await get_calendar()
    end = time.time()
    print(f"get_calendar took: {end-start:.4f}s")

asyncio.run(test_calendar())

print(f"Total time: {time.time()-t0:.4f}s")
print("--- Diagnosis Complete ---")
