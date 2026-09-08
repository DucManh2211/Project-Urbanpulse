"""
seed_history_from_csv.py — Nạp dữ liệu lịch sử đã thu thập ở Tháng 1
(file processed_*.csv mới nhất) vào bảng aqi_history trong PostgreSQL.

Chạy 1 LẦN DUY NHẤT sau khi đã tạo database, để có sẵn lịch sử phục vụ
endpoint /aqi/forecast (không cần đợi schedule_collect_df.py chạy đủ 168 giờ).

Cách chạy:
    python -m src.api.seed_history_from_csv
"""

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.api.database import SessionLocal, AQIHistory, Base, engine  # noqa: E402

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
REQUIRED_COLS = [
    "datetime", "european_aqi", "temperature_2m",
    "relative_humidity_2m", "wind_speed_10m", "precipitation",
]


def main():
    Base.metadata.create_all(engine)

    files = sorted(PROCESSED_DIR.glob("processed_*.csv"))
    if not files:
        raise FileNotFoundError(f"Không tìm thấy file processed_*.csv trong {PROCESSED_DIR}")

    latest = files[-1]
    print(f"Đang nạp dữ liệu từ: {latest.name}")

    df = pd.read_csv(latest)
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise KeyError(f"File CSV thiếu cột: {missing}")

    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df[REQUIRED_COLS].drop_duplicates(subset=["datetime"]).sort_values("datetime")

    session = SessionLocal()
    existing_datetimes = {r[0] for r in session.query(AQIHistory.datetime).all()}

    inserted, skipped = 0, 0
    for _, row in df.iterrows():
        if row["datetime"] in existing_datetimes:
            skipped += 1
            continue
        session.add(AQIHistory(
            datetime=row["datetime"],
            european_aqi=row["european_aqi"],
            temperature_2m=row["temperature_2m"],
            relative_humidity_2m=row["relative_humidity_2m"],
            wind_speed_10m=row["wind_speed_10m"],
            precipitation=row["precipitation"],
        ))
        inserted += 1

        # Commit theo batch 500 dòng để tránh 1 transaction quá lớn
        if inserted % 500 == 0:
            session.commit()
            print(f"  Đã nạp {inserted} dòng...")

    session.commit()
    session.close()

    print(f"\nHoàn tất: {inserted} dòng mới được nạp, {skipped} dòng bỏ qua (đã tồn tại).")


if __name__ == "__main__":
    main()
