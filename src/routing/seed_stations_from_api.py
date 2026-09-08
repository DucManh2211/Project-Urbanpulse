"""
seed_stations_from_api.py — Lấy AQI THẬT từ Open-Meteo tại nhiều điểm lưới
quanh khu vực đang test route (Hoàn Kiếm, bán kính ~3km), ghi vào bảng
Station qua chính API UrbanPulse (POST /stations) — không nhập tay nữa.

Chạy 1 lần (hoặc định kỳ) để bảng Station có dữ liệu thật thay vì trạm giả.

Cách chạy (server FastAPI phải đang chạy trước):
    python seed_stations_from_api.py
"""

import time
import numpy as np
import requests

API_BASE = "http://127.0.0.1:8000"

# Vùng bao quanh khu vực Hoàn Kiếm — khớp với bán kính graph_utils.py đang dùng (3km)
LAT_MIN, LAT_MAX = 21.010, 21.045
LON_MIN, LON_MAX = 105.830, 105.875
GRID_STEP = 0.01  # ~1km mỗi ô lưới, dày hơn lưới cũ vì phạm vi nhỏ hơn


def get_current_aqi(lat: float, lon: float) -> float | None:
    url = "https://air-quality-api.open-meteo.com/v1/air-quality"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "european_aqi",
        "timezone": "auto",
    }
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()["current"].get("european_aqi")


def seed_stations():
    lats = np.arange(LAT_MIN, LAT_MAX, GRID_STEP)
    lons = np.arange(LON_MIN, LON_MAX, GRID_STEP)

    created, failed = 0, 0
    for i, lat in enumerate(lats):
        for j, lon in enumerate(lons):
            try:
                aqi = get_current_aqi(round(lat, 4), round(lon, 4))
                if aqi is None:
                    print(f"Bỏ qua ({lat:.4f}, {lon:.4f}): API không trả AQI")
                    continue

                payload = {
                    "name": f"Station_{i}_{j}",
                    "city": "Hanoi",
                    "aqi": int(round(aqi)),
                    "latitude": round(lat, 4),
                    "longitude": round(lon, 4),
                }
                resp = requests.post(f"{API_BASE}/stations", json=payload, timeout=10)
                resp.raise_for_status()
                created += 1
                print(f"✓ Đã tạo trạm ({lat:.4f}, {lon:.4f}) AQI={payload['aqi']}")

                time.sleep(0.3)  # tránh gọi Open-Meteo quá dồn dập
            except Exception as e:
                failed += 1
                print(f"✗ Lỗi tại ({lat:.4f}, {lon:.4f}): {e}")

    print(f"\nHoàn tất: {created} trạm được tạo, {failed} lỗi.")


if __name__ == "__main__":
    seed_stations()