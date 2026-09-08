"""
pages/3_⚠️_Risk.py — Phân loại rủi ro sức khỏe cá nhân hóa.
"""

import streamlit as st
import plotly.express as px
import requests

from api_client import check_risk

st.set_page_config(page_title="UrbanPulse — Risk", page_icon="⚠️")

st.title("⚠️ Kiểm tra mức rủi ro sức khỏe")

with st.form("risk_form"):
    c1, c2 = st.columns(2)
    aqi = c1.number_input("AQI hiện tại", min_value=0, max_value=500, value=110)
    hour = c2.number_input("Giờ trong ngày", min_value=0, max_value=23, value=8)

    c3, c4 = st.columns(2)
    temperature = c3.number_input("Nhiệt độ (°C)", value=30.0)
    humidity = c4.number_input("Độ ẩm (%)", min_value=0, max_value=100, value=70)

    user_group = st.selectbox("Nhóm đối tượng", ["healthy", "child", "elderly"])

    submitted = st.form_submit_button("Kiểm tra", type="primary")

if submitted:
    try:
        result = check_risk(aqi, int(hour), temperature, humidity, user_group)
        risk_level = result["risk_level"]
        probs = result["probabilities"]

        level_display = {
            "Thap": ("🟢 Thấp", "success"),
            "TrungBinh": ("🟠 Trung bình", "warning"),
            "Cao": ("🔴 Cao", "error"),
            "NguyHiem": ("🟣 Nguy hiểm", "error"),
        }
        label, style = level_display.get(risk_level, (risk_level, "info"))

        getattr(st, style)(f"Mức rủi ro: {label}")

        # Biểu đồ Plotly xác suất từng lớp (Ngày 53)
        order = ["Thap", "TrungBinh", "Cao", "NguyHiem"]
        labels = [k for k in order if k in probs]
        values = [probs[k] for k in labels]

        fig = px.bar(
            x=labels, y=values,
            labels={"x": "Mức độ", "y": "Xác suất"},
            color=values, color_continuous_scale="RdYlGn_r",
            title="Xác suất theo từng mức rủi ro",
        )
        fig.update_layout(yaxis_range=[0, 1], coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)

    except requests.exceptions.ConnectionError:
        st.error("Không kết nối được API. Kiểm tra uvicorn đã chạy chưa.")
    except requests.exceptions.HTTPError as e:
        detail = e.response.json().get("detail", str(e)) if e.response is not None else str(e)
        st.error(f"Lỗi từ server: {detail}")
