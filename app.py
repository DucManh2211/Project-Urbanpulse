"""
app.py — Trang Home (entrypoint). Chạy: streamlit run app.py

Tổng hợp Ngày 49-54:
- Ngày 49: gọi GET /stations, xử lý lỗi kết nối
- Ngày 50: form sidebar thêm trạm mới (POST /stations)
- Ngày 51: bản đồ Folium
- Ngày 52: lưu dữ liệu vào st.session_state để các trang trong pages/ dùng lại,
           không phải gọi lại API
- Ngày 54: dùng api_client.py thay vì tự viết requests trực tiếp
"""

import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import requests

from api_client import API_BASE, get_stations, create_station

st.set_page_config(page_title="UrbanPulse — Home", page_icon="🌫️", layout="wide")

# Lưu API_BASE vào session_state — các trang trong pages/ đọc lại từ đây (Ngày 52)
if "API_BASE" not in st.session_state:
    st.session_state["API_BASE"] = API_BASE

st.title("🌫️ UrbanPulse — Giám sát chất lượng không khí Hà Nội")


# ============================================================
# SIDEBAR — Form thêm trạm mới (Ngày 50)
# ============================================================

st.sidebar.header("➕ Thêm trạm mới")

with st.sidebar.form("add_station_form", clear_on_submit=True):
    name = st.text_input("Tên trạm")
    city = st.text_input("Thành phố", value="Hanoi")
    aqi = st.number_input("AQI", min_value=0, max_value=500, value=50)
    lat = st.number_input("Latitude", value=21.028, format="%.4f", min_value=-90.0, max_value=90.0)
    lon = st.number_input("Longitude", value=105.854, format="%.4f", min_value=-180.0, max_value=180.0)
    submitted = st.form_submit_button("Thêm trạm")

    if submitted:
        if not name.strip():
            st.sidebar.error("Tên trạm không được để trống.")
        else:
            try:
                new_station = create_station(name, city, int(aqi), lat, lon)
                st.sidebar.success(f"Đã thêm trạm '{new_station['name']}' (id={new_station['id']})")
                # Xóa cache để phần thân trang gọi lại API, hiển thị trạm mới ngay
                st.session_state.pop("stations", None)
            except requests.exceptions.ConnectionError:
                st.sidebar.error("Không kết nối được API. Kiểm tra uvicorn đã chạy chưa.")
            except requests.exceptions.HTTPError as e:
                detail = e.response.json().get("detail", str(e)) if e.response is not None else str(e)
                st.sidebar.error(f"Lỗi từ server: {detail}")


# ============================================================
# THÂN TRANG — Lấy dữ liệu (có cache qua session_state, Ngày 52)
# ============================================================

if "stations" not in st.session_state:
    try:
        st.session_state["stations"] = get_stations()
    except requests.exceptions.ConnectionError:
        st.error(
            "Không kết nối được tới API. "
            "Kiểm tra server FastAPI đã chạy chưa (uvicorn src.api.main:app --reload)."
        )
        st.stop()  # dừng luôn phần code phía dưới, tránh lỗi tiếp theo do stations chưa có
    except requests.exceptions.HTTPError as e:
        st.error(f"API trả về lỗi: {e}")
        st.stop()

stations = st.session_state["stations"]

st.header("Danh sách trạm đo")

if not stations:
    st.info("Chưa có trạm nào trong database. Thêm trạm ở sidebar bên trái.")
else:
    df = pd.DataFrame(stations)

    col1, col2, col3 = st.columns(3)
    col1.metric("Tổng số trạm", len(df))
    col2.metric("AQI trung bình", f"{df['aqi'].mean():.0f}")
    col3.metric("AQI cao nhất", int(df["aqi"].max()))

    st.dataframe(df, use_container_width=True)

    # ============================================================
    # BẢN ĐỒ (Ngày 51)
    # ============================================================
    st.header("Bản đồ AQI")

    center = [df["latitude"].mean(), df["longitude"].mean()]
    m = folium.Map(location=center, zoom_start=13)

    def get_color(aqi_value):
        if aqi_value <= 50:
            return "green"
        elif aqi_value <= 100:
            return "orange"
        return "red"

    for s in stations:
        folium.CircleMarker(
            location=[s["latitude"], s["longitude"]],
            radius=9,
            popup=f"{s['name']}: AQI={s['aqi']} ({s['status']})",
            tooltip=s["name"],
            color="black",
            weight=1,
            fill=True,
            fill_color=get_color(s["aqi"]),
            fill_opacity=0.85,
        ).add_to(m)

    st_folium(m, width=None, height=500, use_container_width=True)

st.sidebar.divider()
if st.sidebar.button("🔄 Tải lại dữ liệu trạm"):
    st.session_state.pop("stations", None)
    st.rerun()
