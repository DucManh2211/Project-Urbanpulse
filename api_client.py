"""
api_client.py — Gom toàn bộ lệnh gọi API vào 1 nơi duy nhất (Ngày 54).
Mọi trang Streamlit import từ đây, KHÔNG tự viết requests.get/post rải rác.

Khi deploy (Ngày 60), chỉ cần sửa API_BASE ở đây — không cần sửa từng trang.
"""

import requests
import os
API_BASE = os.getenv("API_BASE", "http://127.0.0.1:8000")

def get_stations() -> list[dict]:
    """GET /stations — trả về list dict, ném exception nếu lỗi (để trang tự xử lý hiển thị)."""
    response = requests.get(f"{API_BASE}/stations", timeout=10)
    response.raise_for_status()
    return response.json()


def get_stations_statistic() -> dict:
    response = requests.get(f"{API_BASE}/stations/statistic", timeout=10)
    response.raise_for_status()
    return response.json()


def create_station(name: str, city: str, aqi: int, latitude: float, longitude: float) -> dict:
    payload = {"name": name, "city": city, "aqi": aqi, "latitude": latitude, "longitude": longitude}
    response = requests.post(f"{API_BASE}/stations", json=payload, timeout=10)
    response.raise_for_status()
    return response.json()


def get_forecast() -> dict:
    response = requests.get(f"{API_BASE}/aqi/forecast", timeout=15)
    response.raise_for_status()
    return response.json()


def get_clean_route(start_lat: float, start_lon: float, end_lat: float, end_lon: float,
                     place: str = "Hoan Kiem, Hanoi, Vietnam") -> dict:
    payload = {
        "start_lat": start_lat, "start_lon": start_lon,
        "end_lat": end_lat, "end_lon": end_lon, "place": place,
    }
    # timeout dài hơn hẳn các hàm khác — lần đầu gọi phải tải graph osmnx, có thể mất
    # hàng chục giây (đã học ở Ngày 47 — endpoint route/clean là "nặng" nhất)
    response = requests.post(f"{API_BASE}/route/clean", json=payload, timeout=60)
    response.raise_for_status()
    return response.json()


def check_risk(aqi: float, hour: int, temperature: float, humidity: float, user_group: str) -> dict:
    payload = {
        "aqi": aqi, "hour": hour, "temperature": temperature,
        "humidity": humidity, "user_group": user_group,
    }
    response = requests.post(f"{API_BASE}/risk/check", json=payload, timeout=10)
    response.raise_for_status()
    return response.json()
