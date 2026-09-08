"""
route_service.py — Đã cập nhật: hàm find_clean_route() giờ trả thêm
short_route_coords / clean_route_coords để frontend vẽ được polyline thật
lên bản đồ, thay vì chỉ có số liệu tóm tắt.
"""

import networkx as nx
import osmnx as ox

from src.routing.graph_utils import get_graph
from src.routing.idw import idw_at_point


def assign_aqi_weights(G, stations: list[dict]):
    for u, v, data in G.edges(data=True):
        mid_lat = (G.nodes[u]["y"] + G.nodes[v]["y"]) / 2
        mid_lon = (G.nodes[u]["x"] + G.nodes[v]["x"]) / 2
        aqi_est = idw_at_point(mid_lat, mid_lon, stations)
        data["aqi_weight"] = data["length"] * (1 + aqi_est / 100)
    return G


def route_to_coords(G, route: list) -> list[list[float]]:
    """Chuyển 1 route (list node id) thành list tọa độ [lat, lon] để vẽ polyline."""
    return [[G.nodes[node]["y"], G.nodes[node]["x"]] for node in route]


def find_clean_route(start_lat: float, start_lon: float,
                      end_lat: float, end_lon: float,
                      stations: list[dict],
                      place: str = "Hoan Kiem, Hanoi, Vietnam") -> dict:
    G = get_graph(place)

    sample_edge = next(iter(G.edges(data=True)))[2]
    if "aqi_weight" not in sample_edge:
        assign_aqi_weights(G, stations)

    orig = ox.nearest_nodes(G, X=start_lon, Y=start_lat)
    dest = ox.nearest_nodes(G, X=end_lon, Y=end_lat)

    short_route = nx.shortest_path(G, orig, dest, weight="length")
    clean_route = nx.shortest_path(G, orig, dest, weight="aqi_weight")

    short_len = nx.shortest_path_length(G, orig, dest, weight="length")
    clean_len = sum(
        G[u][v][0]["length"] for u, v in zip(clean_route[:-1], clean_route[1:])
    )

    percent_longer = (clean_len / short_len - 1) * 100 if short_len > 0 else 0.0

    return {
        "short_distance_m": round(short_len, 1),
        "clean_distance_m": round(clean_len, 1),
        "percent_longer": round(percent_longer, 1),
        "node_count_short": len(short_route),
        "node_count_clean": len(clean_route),
        "short_route_coords": route_to_coords(G, short_route),
        "clean_route_coords": route_to_coords(G, clean_route),
    }