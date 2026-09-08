"""
idw.py — Nội suy Inverse Distance Weighting, tái sử dụng nguyên logic từ Tuần 5.
Dùng để ước lượng AQI tại 1 tọa độ bất kỳ (VD điểm giữa 1 cạnh đường) dựa trên
khoảng cách tới các trạm đo thật.
"""

import numpy as np


def idw_at_point(lat: float, lon: float, stations: list[dict],
                  power: int = 2, epsilon: float = 1e-6) -> float:
    """
    stations: list các dict có key "lat", "lon", "aqi"
    Trả về AQI ước lượng tại (lat, lon).
    """
    if not stations:
        raise ValueError("Danh sách stations rỗng — không có dữ liệu để nội suy.")

    weights, values = [], []
    for s in stations:
        dist = np.sqrt((lat - s["lat"]) ** 2 + (lon - s["lon"]) ** 2)
        weights.append(1 / (dist ** power + epsilon))
        values.append(s["aqi"])

    weights = np.array(weights)
    values = np.array(values)
    return float(np.sum(weights * values) / np.sum(weights))
