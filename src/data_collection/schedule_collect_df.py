from pathlib import Path
import sys
import time
from datetime import datetime

import pandas as pd
import schedule

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data_collection.weather_api import get_weather_data
from src.data_collection.aqi_api import get_aqi_data
from src.preprocessing.clean import process_data
from src.preprocessing.feature_engineering import feature_data


DATA_DIR = PROJECT_ROOT / "data"

RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

RAW_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def collect_data():
    try:
        print("Collecting data...")
        weather = get_weather_data()
        aqi = get_aqi_data()
        weather.rename(columns={"time": "datetime"}, inplace=True)
        aqi.rename(columns={"time": "datetime"}, inplace=True)

        weather["datetime"] = pd.to_datetime(weather["datetime"])
        aqi["datetime"] = pd.to_datetime(aqi["datetime"])
        merged = pd.merge(
            weather,
            aqi,
            on="datetime",
            how="inner"
        )
        raw_file = RAW_DIR / f"raw_{datetime.now():%Y%m%d_%H%M%S}.csv"

        merged.to_csv(
            raw_file,
            index=False
        )
        cleaned = process_data(merged)
        featured = feature_data(cleaned)
        processed_file = (
            PROCESSED_DIR /
            f"processed_{datetime.now():%Y%m%d_%H%M%S}.csv"
        )
        featured.to_csv(
            processed_file,
            index=False
        )
        print(f"Processed data saved:\n{processed_file}")
        print(featured.head())

    except Exception as e:
        print("ERROR:", e)


collect_data()

schedule.every().hour.do(collect_data)

print("Scheduler started...")

while True:
    schedule.run_pending()
    time.sleep(1)