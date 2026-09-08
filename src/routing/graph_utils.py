"""
graph_utils.py — Tải và CACHE graph đường phố osmnx trong RAM.

QUAN TRỌNG: dùng graph_from_point() thay vì graph_from_place() —
graph_from_place() cần gọi Nominatim API để "dịch" tên địa danh (VD:
"Hoan Kiem, Hanoi, Vietnam") thành tọa độ/ranh giới, và Nominatim đang
bị ConnectionResetError liên tục trên máy này (khác Overpass API, vẫn
hoạt động bình thường qua curl). graph_from_point() chỉ cần tọa độ có
sẵn, gọi thẳng Overpass, bỏ qua hoàn toàn bước Nominatim.
"""

import time
import osmnx as ox

ox.settings.timeout = 300

_graph_cache: dict[str, "ox.MultiDiGraph"] = {}

MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 5

# Tọa độ trung tâm sẵn có cho các khu vực hay dùng trong dự án —
# tránh phải gọi Nominatim để tra tọa độ từ tên địa danh.
PLACE_CENTERS = {
    "Hoan Kiem, Hanoi, Vietnam": (21.0285, 105.8542),
    "Hanoi, Vietnam": (21.0285, 105.8542),
}

DEFAULT_RADIUS_METERS = 3000  # bán kính tải graph quanh tâm, đủ cho khu vực trung tâm


def get_graph(place: str = "Hoan Kiem, Hanoi, Vietnam", radius_m: int = DEFAULT_RADIUS_METERS):
    """
    Trả về graph đường phố quanh tâm của `place`, tự động cache theo tên khu vực.
    Dùng graph_from_point() (không cần Nominatim) thay vì graph_from_place().

    Nếu `place` chưa có trong PLACE_CENTERS, thêm tọa độ tương ứng vào dict đó
    trước khi gọi hàm này (tra tọa độ 1 lần thủ công qua Google Maps, không
    cần Nominatim).
    """
    cache_key = f"{place}_{radius_m}"
    if cache_key in _graph_cache:
        return _graph_cache[cache_key]

    if place not in PLACE_CENTERS:
        raise ValueError(
            f"Chưa có tọa độ tâm cho '{place}' trong PLACE_CENTERS. "
            f"Thêm tọa độ (lat, lon) thủ công vào dict PLACE_CENTERS trong graph_utils.py."
        )

    lat, lon = PLACE_CENTERS[place]

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"[graph_utils] Đang tải graph quanh ({lat}, {lon}), "
                  f"bán kính {radius_m}m (lần thử {attempt}/{MAX_RETRIES})...")
            G = ox.graph_from_point((lat, lon), dist=radius_m, network_type="drive")
            _graph_cache[cache_key] = G
            print(f"[graph_utils] Đã cache graph '{place}': "
                  f"{len(G.nodes)} node, {len(G.edges)} cạnh")
            return G
        except Exception as e:
            last_error = e
            print(f"[graph_utils] Lỗi lần thử {attempt}: {e}")
            if attempt < MAX_RETRIES:
                print(f"[graph_utils] Thử lại sau {RETRY_DELAY_SECONDS} giây...")
                time.sleep(RETRY_DELAY_SECONDS)

    raise RuntimeError(
        f"Không thể tải graph cho '{place}' sau {MAX_RETRIES} lần thử. "
        f"Lỗi cuối cùng: {last_error}"
    )