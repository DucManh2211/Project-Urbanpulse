"""
graph_utils.py — Tải và CACHE graph đường phố osmnx trong RAM.

QUAN TRỌNG: ưu tiên đọc từ file .graphml có sẵn (commit sẵn trong repo)
thay vì gọi Overpass API lúc runtime — vì môi trường Render (free tier)
bị chặn kết nối tới overpass-api.de (Connection refused), trong khi
máy local vẫn tải được bình thường. File .graphml được tạo 1 lần từ
local, commit vào repo, dùng chung cho cả local lẫn Render.
"""

import time
from pathlib import Path

import osmnx as ox

ox.settings.timeout = 300

_graph_cache: dict[str, "ox.MultiDiGraph"] = {}

MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 5

# Đặt đúng tên file bạn vừa tạo ở Bước 1, nằm ở GỐC REPO
GRAPHML_PATH = Path(__file__).resolve().parents[2] / "hanoi_hoankiem_3km.graphml"

PLACE_CENTERS = {
    "Hoan Kiem, Hanoi, Vietnam": (21.0285, 105.8542),
    "Hanoi, Vietnam": (21.0285, 105.8542),
}

DEFAULT_RADIUS_METERS = 3000


def get_graph(place: str = "Hoan Kiem, Hanoi, Vietnam", radius_m: int = DEFAULT_RADIUS_METERS):
    cache_key = f"{place}_{radius_m}"
    if cache_key in _graph_cache:
        return _graph_cache[cache_key]

    # ƯU TIÊN 1: đọc từ file .graphml có sẵn — không gọi mạng
    if GRAPHML_PATH.exists():
        print(f"[graph_utils] Đọc graph có sẵn từ file: {GRAPHML_PATH}")
        G = ox.load_graphml(GRAPHML_PATH)
        _graph_cache[cache_key] = G
        print(f"[graph_utils] Đã cache graph '{place}': {len(G.nodes)} node, {len(G.edges)} cạnh")
        return G

    # ƯU TIÊN 2 (fallback): nếu không có file, thử gọi Overpass trực tiếp
    print(f"[graph_utils] Không tìm thấy {GRAPHML_PATH}, thử gọi Overpass API...")
    if place not in PLACE_CENTERS:
        raise ValueError(f"Chưa có tọa độ tâm cho '{place}' trong PLACE_CENTERS.")
    lat, lon = PLACE_CENTERS[place]

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"[graph_utils] Đang tải graph quanh ({lat}, {lon}), "
                  f"bán kính {radius_m}m (lần thử {attempt}/{MAX_RETRIES})...")
            G = ox.graph_from_point((lat, lon), dist=radius_m, network_type="drive")
            _graph_cache[cache_key] = G
            return G
        except Exception as e:
            last_error = e
            print(f"[graph_utils] Lỗi lần thử {attempt}: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY_SECONDS)

    raise RuntimeError(
        f"Không thể tải graph cho '{place}' — file cache không có, "
        f"và Overpass API cũng lỗi sau {MAX_RETRIES} lần thử: {last_error}"
    )