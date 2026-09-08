# 🌫️ UrbanPulse — Dự báo & Điều hướng Chất lượng Không khí Hà Nội

**Demo trực tiếp:** [project-urbanpulse-cqzyqsy6hih6fhsdhyu7zj.streamlit.app](https://project-urbanpulse-cqzyqsy6hih6fhsdhyu7zj.streamlit.app)
**API backend (Swagger UI):** `https://project-urbanpulse.onrender.com/docs`

> ⚠️ Backend chạy trên Render free tier — nếu không có ai dùng trong 15 phút, server sẽ "ngủ". Request đầu tiên sau đó có thể mất 30–50 giây để khởi động lại. Đây là giới hạn của gói miễn phí, không phải lỗi ứng dụng.

---

## 📌 Giới thiệu

UrbanPulse là hệ thống end-to-end thu thập, dự báo và trực quan hóa chất lượng không khí (AQI) tại Hà Nội, đồng thời gợi ý lộ trình di chuyển ít phơi nhiễm ô nhiễm nhất. Dự án được xây dựng trong 3 tháng, đi từ thu thập dữ liệu thô đến một web app triển khai công khai.

**Tính năng chính:**
- 📈 Dự báo AQI 24h tới bằng mô hình học máy (XGBoost), so sánh với Prophet, LSTM và baseline thống kê
- 🗺️ Tìm lộ trình "sạch nhất" giữa 2 điểm, dựa trên nội suy AQI không gian (IDW) và thuật toán Dijkstra có trọng số
- ⚠️ Phân loại mức rủi ro sức khỏe theo nhóm đối tượng (trẻ em / người già / người khỏe mạnh)
- 🌐 REST API đầy đủ (FastAPI + PostgreSQL), giao diện web (Streamlit), theo dõi thí nghiệm (MLflow)

---

## 🏗️ Kiến trúc hệ thống

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│  Open-Meteo API  │────▶│  Thu thập dữ liệu │────▶│  PostgreSQL (Render) │
│ (AQI + Thời tiết)│     │ (schedule/seed)   │     │  aqi_history, stations│
└─────────────────┘     └──────────────────┘     └──────────┬───────────┘
                                                              │
                          ┌───────────────────────────────────┼──────────────────┐
                          │                                    │                  │
                    ┌─────▼──────┐                    ┌────────▼───────┐   ┌──────▼──────┐
                    │  XGBoost    │                    │  Dijkstra+IDW  │   │ RandomForest │
                    │ (Forecast)  │                    │ (Route)        │   │ (Risk)       │
                    └─────┬──────┘                    └────────┬───────┘   └──────┬──────┘
                          │                                    │                   │
                          └────────────────┬───────────────────┴───────────────────┘
                                           │
                                  ┌────────▼─────────┐
                                  │   FastAPI (Render) │
                                  │  /aqi/forecast      │
                                  │  /route/clean       │
                                  │  /route/safe        │
                                  │  /risk/check        │
                                  │  /stations (CRUD)   │
                                  └────────┬─────────┘
                                           │
                                  ┌────────▼─────────┐
                                  │ Streamlit Cloud    │
                                  │ Forecast / Route /  │
                                  │ Risk                │
                                  └────────────────────┘
```

**Cấu trúc thư mục:**
```
Project UrbanPulse/
├── app.py                        # Điểm vào chính của Streamlit
├── api_client.py                 # Hàm gọi API dùng chung cho các trang Streamlit
├── hanoi_hoankiem_3km.graphml    # Graph đường phố cache sẵn (né Overpass bị chặn trên Render)
├── mlflow.db                     # Backend store của MLflow (SQLite)
├── requirements.txt               # Dependency cho Streamlit Cloud (frontend)
├── requirements-backend.txt       # Dependency cho Render (FastAPI backend)
│
├── pages/                         # Các trang Streamlit (multi-page app)
│   ├── 1_📈_Forecast.py
│   ├── 2_🗺️_Route.py
│   └── 3_⚠️_Risk.py
│
├── cache/                         # Cache tạm (osmnx/geocoder), có thể xóa an toàn
├── mlruns/                        # Lịch sử thí nghiệm MLflow (params, metrics, model)
├── models/                        # Model risk classifier (.joblib)
│
├── data/
│   ├── raw/                       # Dữ liệu AQI + thời tiết thô (CSV)
│   ├── processed/                 # Dữ liệu đã resample + feature engineering
│   ├── model/                     # xgboost_model.json (model chính thức phục vụ API)
│   └── forecast/                  # Kết quả dự báo xuất ra (Prophet, v.v.)
│
└── src/
    ├── data_collection/           # Gọi Open-Meteo API (aqi_api.py, weather_api.py), schedule thu thập
    ├── preprocessing/             # clean.py, feature_engineering.py
    ├── model/                     # prophet_model.py, xgboost_model.py, lstm_model.py
    ├── evaluation/                # Đánh giá, so sánh mô hình
    ├── api/                       # FastAPI: main.py, database.py, schemas.py, routers/
    ├── forecast/                  # forecast_service.py — nối XGBoost (Tháng 1) vào API (Tháng 2)
    ├── risk/                      # risk_service.py — nối Random Forest vào API
    └── routing/                   # graph_utils.py, idw.py, route_service.py — Dijkstra + IDW
```

---

## 📊 Kết quả mô hình dự báo — bài học quan trọng nhất của dự án

### Vòng 1 — Dữ liệu ~20 ngày (Tháng 1, giai đoạn đầu)

| Model | RMSE | So với Naive baseline |
|---|---|---|
| Naive baseline | 4.12 | — |
| XGBoost (target 6h) | 10.18 | Thua 2.5× |
| LSTM | 14.44–17.45 | Thua 3.5–4× |
| Prophet | 20.71 | Thua 5× |

**Insight:** với dữ liệu quá ngắn, phép đoán đơn giản "AQI tới = AQI hiện tại" vượt trội mọi mô hình ML. Đây không phải thất bại kỹ thuật — sau khi loại bỏ 3 lớp data leakage khác nhau (feature trùng target, scaler fit sai, off-by-one trong sliding window) và tuning có hệ thống, kết luận vẫn giữ nguyên: **thiếu dữ liệu là nút thắt thật sự**, không phải thuật toán hay tham số.

### Vòng 2 — Dữ liệu 5 năm (sau khi mở rộng thu thập)

| Model | Horizon | RMSE | So với Naive |
|---|---|---|---|
| Naive baseline | 24h | 11.64 | — |
| **XGBoost (tuned)** | **24h** | **11.01** | **Thắng 5.4%** ✅ |
| LSTM (univariate) | 24h | 14.49 | Thua |
| LSTM (multivariate) | 24h | 14.66 | Thua |
| Prophet (best config) | ~14 ngày | 17.06 vs Naive 24.16 | Thắng 29% |

**Kết luận:** với đủ dữ liệu, XGBoost khai thác được tổ hợp lag dài hạn (1h/24h/168h) + thời tiết (gió, mưa, nhiệt độ) + tính mùa vụ (`month` bắt đầu có đóng góp thật) để vượt qua baseline — nhưng biên độ thắng vẫn khiêm tốn, phản ánh đúng độ khó thực sự của bài toán dự báo AQI đô thị. **XGBoost được chọn làm mô hình chính thức phục vụ API.**

Toàn bộ thí nghiệm được theo dõi bằng **MLflow** (`mlruns/`), gồm cả naive baseline làm mốc so sánh — không chỉ so 3 mô hình ML với nhau.

---

## 🗺️ Kiểm chứng thuật toán Route (Dijkstra + IDW)

Route "sạch nhất" được kiểm chứng bằng 2 kịch bản đối lập, log chi tiết AQI từng cạnh:

- **Route ngắn (~1.2km), AQI khu vực đồng đều (65–70):** `short_route == clean_route` — đúng, vì không có gì để né.
- **Route dài hơn, có điểm AQI cực đoan (400) trên đường đi:** `short_route ≠ clean_route` — thuật toán chủ động đi vòng để né vùng ô nhiễm.

Cả 2 kết quả xác nhận thuật toán hoạt động đúng theo lý thuyết đồ thị có trọng số, không phải ngẫu nhiên.

---

## 🛠️ Công nghệ sử dụng

| Nhóm | Công nghệ |
|---|---|
| Thu thập & xử lý dữ liệu | Open-Meteo API, Pandas, NumPy |
| Mô hình dự báo | XGBoost, Prophet, PyTorch (LSTM) |
| Mô hình phân loại | Scikit-learn (Random Forest) |
| Định tuyến không gian | NetworkX (Dijkstra), OSMnx, IDW tự cài đặt |
| Backend | FastAPI, SQLAlchemy, PostgreSQL |
| Frontend | Streamlit, Folium |
| Theo dõi thí nghiệm | MLflow |
| Triển khai | Render (backend + PostgreSQL), Streamlit Community Cloud (frontend) |

---

## ⚠️ Giới hạn hiện tại — nhìn thẳng, không né tránh

1. **Dữ liệu lịch sử (`AQIHistory`) không tự cập nhật trên cloud.** `schedule_collect_df.py` chỉ chạy khi bật thủ công trên máy local — dự báo hiện dựa trên dữ liệu tại thời điểm nạp gần nhất, chưa phản ánh AQI thời gian thực. Hướng cải thiện: deploy thêm cron job trên Render.
2. **Route chỉ hỗ trợ khu vực Hoàn Kiếm (bán kính 3km).** Graph đường phố được cache sẵn từ 1 lần tải cục bộ do Render free tier bị chặn kết nối tới Overpass API công cộng — mở rộng khu vực khác cần tải file `.graphml` mới từ máy có kết nối ổn định.
3. **Trạm AQI phục vụ nội suy IDW hiện là dữ liệu mẫu/thủ công**, chưa có script tự động thu thập AQI đa điểm chạy định kỳ trên cloud.
4. **Render free tier "ngủ" sau 15 phút** — ảnh hưởng trải nghiệm lần truy cập đầu.

---

## 🚀 Chạy dự án ở local

```bash
# 1. Cài đặt
pip install -r requirements-backend.txt
pip install -r requirements.txt

# 2. Khởi tạo database & nạp dữ liệu lịch sử
python -m src.api.seed_history_from_csv

# 3. Chạy backend
uvicorn src.api.main:app --reload

# 4. Chạy frontend (terminal khác)
streamlit run app.py
```

---

## 📅 Lộ trình phát triển

- **Tháng 1:** Thu thập dữ liệu, xử lý time series, xây dựng & đánh giá 3 mô hình dự báo (Prophet/XGBoost/LSTM), MLflow tracking
- **Tháng 2:** Thuật toán định tuyến (Dijkstra + IDW), phân loại rủi ro (Random Forest), REST API (FastAPI + PostgreSQL)
- **Tháng 3:** Giao diện Streamlit, triển khai production (Render + Streamlit Cloud)

---

## 👤 Tác giả

Hoàng Đức Mạnh — dự án cá nhân, xây dựng trong 3 tháng như một bài tập thực hành end-to-end Data Science / ML Engineering.