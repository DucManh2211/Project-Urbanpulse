"""
pages/1_📈_Forecast.py — Trang dự báo AQI 24h tới.

ĐÃ CẬP NHẬT: thêm ghi chú rõ ràng về việc dự báo chỉ áp dụng cho 1 vị trí
cố định (nơi dữ liệu lịch sử được thu thập ở Tháng 1) — tránh gây hiểu
lầm rằng đây là dự báo cho vị trí bất kỳ người dùng chọn.
"""

import streamlit as st
import requests

from api_client import get_forecast

st.set_page_config(page_title="UrbanPulse — Forecast", page_icon="📈")

st.title("📈 Dự báo AQI 24h tới")

st.write(
    "Model XGBoost (Tháng 1) dự báo AQI dựa trên 168 giờ dữ liệu lịch sử gần nhất "
    "đã nạp vào database."
)

st.info(
    "📍 **Lưu ý về phạm vi dự báo:** dữ liệu lịch sử hiện chỉ được thu thập tại "
    "**1 vị trí cố định** (khu vực Hoàn Kiếm, tọa độ 21.028, 105.834). Dự báo dưới đây "
    "áp dụng cho đúng khu vực này — khác với trang Route/Stations, tính năng này "
    "chưa hỗ trợ chọn vị trí tùy ý."
)

if st.button("Lấy dự báo mới nhất", type="primary"):
    with st.spinner("Đang gọi model dự báo..."):
        try:
            data = get_forecast()
            col1, col2 = st.columns(2)
            col1.metric("AQI dự báo", f"{data['predicted_aqi']:.0f}")
            col2.write(f"**Dựa trên dữ liệu tới:** {data['based_on_datetime']}")
            st.write(f"**Thời điểm dự báo:** {data['forecast_datetime']}")
            st.caption("📍 Vị trí: Hoàn Kiếm, Hà Nội (21.028, 105.834)")

            aqi = data["predicted_aqi"]
            if aqi <= 50:
                st.success("Mức AQI dự báo: Tốt 🟢")
            elif aqi <= 100:
                st.warning("Mức AQI dự báo: Trung bình 🟠")
            else:
                st.error("Mức AQI dự báo: Không tốt cho sức khỏe 🔴")

        except requests.exceptions.ConnectionError:
            st.error("Không kết nối được API. Kiểm tra uvicorn đã chạy chưa.")
        except requests.exceptions.HTTPError as e:
            detail = e.response.json().get("detail", str(e)) if e.response is not None else str(e)
            st.error(
                f"{detail}\n\n"
                f"Gợi ý: chạy `python -m src.api.seed_history_from_csv` để nạp đủ "
                f"168 giờ lịch sử trước khi dự báo."
            )