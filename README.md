# 🌍 UrbanPulse - Hệ Thống Dự Báo Chất Lượng Không Khí (AQI)

> **Mục tiêu:** Xây dựng quy trình tự động thu thập dữ liệu thời tiết & chất lượng không khí (AQI), tiền xử lý, trích xuất đặc trưng và ứng dụng các mô hình Machine Learning/Deep Learning để dự báo chỉ số AQI trong tương lai.

---

## 📌 Tính Năng Chính

1. **Data Pipeline Tự Động:** Tự động lấy dữ liệu thời tiết & chất lượng không khí qua Open-Meteo API theo chu kỳ mỗi giờ bằng `schedule`[cite: 1, 2, 3].
2. **Feature Engineering:** Tạo các đặc trưng lag (`aqi_lag_1`, `aqi_lag_24`), cửa sổ trượt rolling mean/std, cùng các yếu tố thời gian (`hour`, `dayofweek`, `isweekend`)[cite: 8].
3. **Mô Hình Hóa Đa Dạng:**
   - **XGBoost Regressor:** Dự báo theo cấu trúc bảng kèm phân tích Feature Importance[cite: 6].
   - **LSTM (Multivariate):** Mạng Nơ-ron Chuỗi Thời Gian (Deep Learning) xử lý đa biến[cite: 4].
   - **Facebook Prophet:** Mô hình phân tích xu hướng và tính chu kỳ[cite: 5].
4. **MLOps Tracking:** Quản lý thử nghiệm, siêu tham số và lưu trữ chỉ số đánh giá (MAE, RMSE) tập trung bằng **MLflow**[cite: 4, 5, 6].

---

## 🛠️ Công Nghệ Sử Dụng

- **Ngôn ngữ:** Python 3.13
- **Thư viện chính:** `PyTorch`, `XGBoost`, `Prophet`, `Scikit-Learn`, `Pandas`[cite: 4, 5, 6]
- **MLOps:** `MLflow` (Tracking & Artifact Logging)[cite: 4, 5, 6]
- **Thu thập dữ liệu:** `Requests`, `Schedule`, `Open-Meteo API`[cite: 1, 2, 3]

---

## 📂 Cấu Trúc Dự Án

```text
Project UrbanPulse/
├── data/
│   ├── forecast/                      # Lưu kết quả dự báo của Prophet (.csv)
│   ├── model/                         # Lưu weights mô hình (.pth, .json)
│   ├── processed/                     # Lưu các tập dữ liệu đã làm sạch & tạo feature
│   └── raw/                           # Lưu dữ liệu thô thu thập từ API
├── mlruns/                            # Lưu thông tin Tracking của MLflow
├── src/
│   ├── __init__.py
│   ├── data_collection/               # Thu thập dữ liệu
│   │   ├── __init__.py
│   │   ├── aqi_api.py                 # Lấy dữ liệu chất lượng không khí
│   │   ├── schedule_collect_df.py     # Tự động hóa lấy dữ liệu định kỳ
│   │   └── weather_api.py             # Lấy dữ liệu thời tiết
│   ├── evaluation/                    # Đánh giá mô hình
│   ├── model/                         # Huấn luyện mô hình
│   │   ├── __init__.py
│   │   ├── lstm_model.py              # Huấn luyện PyTorch LSTM
│   │   ├── prophet_model.py           # Huấn luyện Facebook Prophet
│   │   └── xgboost_model.py           # Huấn luyện XGBoost Regressor
│   └── preprocessing/                 # Tiền xử lý dữ liệu
│       ├── __init__.py
│       ├── clean.py                   # Kiểm tra & làm sạch dữ liệu
│       └── feature_engineering.py     # Tạo lag features, rolling windows
├── mlflow.db                          # Cơ sở dữ liệu SQLite của MLflow
├── requirements.txt                   # Khai báo các thư viện phụ thuộc
└── README.md                          # Tài liệu hướng dẫn & Báo cáo dự án