"""
pages/2_🗺️_Route.py — ĐÃ CẬP NHẬT: vẽ đường thật (polyline) cho cả tuyến
ngắn nhất (xanh dương) và tuyến sạch nhất (xanh lá đậm), thay vì chỉ
hiện marker điểm đầu/cuối như trước.
"""

import streamlit as st
import folium
from streamlit_folium import st_folium
import requests

from api_client import get_stations, get_clean_route

st.set_page_config(page_title="UrbanPulse — Route", page_icon="🗺️")

st.title("🗺️ Tìm đường sạch nhất")

if "stations" not in st.session_state:
    st.info("Chưa có dữ liệu trạm trong phiên làm việc — đang tự tải lại...")
    try:
        st.session_state["stations"] = get_stations()
    except requests.exceptions.ConnectionError:
        st.error("Không kết nối được API. Kiểm tra uvicorn đã chạy chưa.")
        st.stop()
    except requests.exceptions.HTTPError as e:
        st.error(f"API trả về lỗi: {e}")
        st.stop()

stations = st.session_state["stations"]

if not stations:
    st.warning("Chưa có trạm nào trong database — cần có ít nhất 1 trạm để tính route.")
    st.stop()

st.caption(f"Đang dùng {len(stations)} trạm (đã cache, không gọi lại API /stations).")


with st.form("route_form"):
    st.subheader("Điểm xuất phát")
    c1, c2 = st.columns(2)
    start_lat = c1.number_input("Start latitude", value=21.030, format="%.4f")
    start_lon = c2.number_input("Start longitude", value=105.850, format="%.4f")

    st.subheader("Điểm đến")
    c3, c4 = st.columns(2)
    end_lat = c3.number_input("End latitude", value=21.025, format="%.4f")
    end_lon = c4.number_input("End longitude", value=105.858, format="%.4f")

    place = st.text_input("Khu vực tải bản đồ (osmnx)", value="Hoan Kiem, Hanoi, Vietnam")

    submitted = st.form_submit_button("Tìm đường", type="primary")


# ---- Tính toán, chỉ khi submit ----
if submitted:
    with st.spinner("Đang tính toán tuyến đường (lần đầu có thể mất 10-30 giây)..."):
        try:
            result = get_clean_route(start_lat, start_lon, end_lat, end_lon, place)
            st.session_state["route_result"] = result
            st.session_state["route_points"] = {
                "start_lat": start_lat, "start_lon": start_lon,
                "end_lat": end_lat, "end_lon": end_lon,
            }
        except requests.exceptions.ConnectionError:
            st.error("Không kết nối được API. Kiểm tra uvicorn đã chạy chưa.")
        except requests.exceptions.Timeout:
            st.error("Yêu cầu quá lâu (server có thể đang tải graph osmnx). Thử lại sau vài giây.")
        except requests.exceptions.HTTPError as e:
            detail = e.response.json().get("detail", str(e)) if e.response is not None else str(e)
            st.error(f"Lỗi từ server: {detail}")


# ---- Hiển thị, đặt ngoài khối submitted để không "biến mất" khi tương tác bản đồ ----
if "route_result" in st.session_state:
    result = st.session_state["route_result"]
    pts = st.session_state["route_points"]

    col1, col2, col3 = st.columns(3)
    col1.metric("Đường ngắn nhất", f"{result['short_distance_m']:.0f} m")
    col2.metric("Đường sạch nhất", f"{result['clean_distance_m']:.0f} m")
    col3.metric("Chênh lệch", f"+{result['percent_longer']:.1f}%")

    st.caption(
        f"🔵 Đường ngắn nhất đi qua {result['node_count_short']} node — "
        f"🟢 Đường sạch nhất đi qua {result['node_count_clean']} node."
    )

    center = [(pts["start_lat"] + pts["end_lat"]) / 2, (pts["start_lon"] + pts["end_lon"]) / 2]
    m = folium.Map(location=center, zoom_start=14)

    # ĐÂY LÀ PHẦN MỚI — vẽ 2 đường thật lên bản đồ
    folium.PolyLine(
        locations=result["short_route_coords"],
        color="blue", weight=5, opacity=0.8,
        tooltip="Đường ngắn nhất",
    ).add_to(m)

    folium.PolyLine(
        locations=result["clean_route_coords"],
        color="green", weight=5, opacity=0.8,
        tooltip="Đường sạch nhất (tránh AQI cao)",
        dash_array="10",  # nét đứt, dễ phân biệt khi 2 đường trùng đoạn
    ).add_to(m)

    folium.Marker([pts["start_lat"], pts["start_lon"]], tooltip="Điểm đầu",
                  icon=folium.Icon(color="blue", icon="play")).add_to(m)
    folium.Marker([pts["end_lat"], pts["end_lon"]], tooltip="Điểm cuối",
                  icon=folium.Icon(color="darkgreen", icon="stop")).add_to(m)

    for s in stations:
        color = "green" if s["aqi"] <= 50 else "orange" if s["aqi"] <= 100 else "red"
        folium.CircleMarker(
            location=[s["latitude"], s["longitude"]], radius=6,
            tooltip=f"{s['name']}: AQI={s['aqi']}",
            fill=True, fill_color=color, color="black", fill_opacity=0.7,
        ).add_to(m)

    # Tự động zoom vừa khít với toàn bộ tuyến đường
    all_coords = result["short_route_coords"] + result["clean_route_coords"]
    m.fit_bounds(all_coords)

    st_folium(m, width=None, height=500, use_container_width=True, key="route_map")

    st.caption("🔵 Nét liền xanh dương = đường ngắn nhất | 🟢 Nét đứt xanh lá = đường sạch nhất")