"""
forecast_service.py — Cầu nối giữa model XGBoost đã train ở Tháng 1
và API ở Tháng 2 (Tuần 8).

Vì XGBoost cần lag_168 (168 giờ lịch sử liên tục), hàm predict_forecast_24h()
nhận vào 1 DataFrame lịch sử (lấy từ database), tự tính lại đúng bộ feature
bằng cách TÁI SỬ DỤNG feature_engineering.feature_data() của Tháng 1 —
không viết lại logic feature từ đầu, tránh lệch feature giữa lúc train và lúc serve.
"""

import sys
from pathlib import Path

import pandas as pd
import xgboost as xgb

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.preprocessing.feature_engineering import feature_data  # noqa: E402

MODEL_PATH = PROJECT_ROOT / "data" / "model" / "xgboost_model.json"

# Phải khớp CHÍNH XÁC với FEATURE_COLS trong xgboost_model.py (Tháng 1)
FEATURE_COLS = [
    "hour", "dayofweek", "month", "isweekend",
    "aqi_lag_1", "aqi_lag_24", "aqi_lag_168",
    "rolling_mean_24", "rolling_std_24",
    "temperature_2m", "relative_humidity_2m", "wind_speed_10m", "precipitation",
]

# QUAN TRỌNG: aqi_lag_168 = shift(168). Với ĐÚNG 168 dòng, dòng cuối cùng
# cần giá trị ở vị trí -1 (không tồn tại) -> toàn bộ shift(168) ra NaN,
# dropna() sẽ xóa sạch dữ liệu. Cần TỐI THIỂU 169 dòng để còn lại đúng 1 dòng
# hợp lệ sau dropna(). Lấy dư thêm biên an toàn 24 dòng cho rolling_mean_24/std_24.
MIN_HISTORY_HOURS = 168 + 24 + 1  # = 193, đủ dư để chắc chắn còn dòng hợp lệ sau dropna()

_model = None  # cache model trong RAM, load 1 lần duy nhất (đúng nguyên tắc Ngày 47)


def load_model() -> xgb.XGBRegressor:
    global _model
    if _model is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Không tìm thấy model tại {MODEL_PATH}. "
                f"Chạy lại src/model/xgboost_model.py để train và lưu model trước."
            )
        _model = xgb.XGBRegressor()
        _model.load_model(str(MODEL_PATH))
        print(f"[forecast_service] Đã load model từ {MODEL_PATH}")
    return _model


def predict_forecast_24h(history_df: pd.DataFrame) -> dict:
    """
    history_df cần các cột: datetime, european_aqi, temperature_2m,
    relative_humidity_2m, wind_speed_10m, precipitation
    Tối thiểu MIN_HISTORY_HOURS dòng, sắp xếp theo thời gian (hàm sẽ tự sort lại).

    Trả về dự báo AQI tại thời điểm (dòng cuối cùng + 24h).
    """
    if len(history_df) < MIN_HISTORY_HOURS:
        raise ValueError(
            f"Cần tối thiểu {MIN_HISTORY_HOURS} giờ lịch sử liên tục để tính đủ "
            f"lag_168 và rolling_24 (còn lại ít nhất 1 dòng sau dropna), "
            f"hiện chỉ có {len(history_df)} giờ."
        )

    df = history_df.copy()
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.sort_values("datetime").reset_index(drop=True)

    # Tái sử dụng ĐÚNG logic feature engineering của Tháng 1 — không viết lại
    featured = feature_data(df)

    if featured.empty:
        raise ValueError(
            "Sau khi tính lag/rolling, không còn dòng dữ liệu nào hợp lệ "
            "(có thể do thiếu dữ liệu ở đầu chuỗi bị dropna() loại bỏ). "
            f"Thử tăng MIN_HISTORY_HOURS (hiện tại: {MIN_HISTORY_HOURS})."
        )

    latest_row = featured.iloc[[-1]]  # dòng cuối cùng = thời điểm "hiện tại"

    missing = [c for c in FEATURE_COLS if c not in latest_row.columns]
    if missing:
        raise KeyError(f"Thiếu cột feature: {missing}")

    X = latest_row[FEATURE_COLS]

    model = load_model()
    pred = float(model.predict(X)[0])

    based_on = latest_row["datetime"].iloc[0]
    forecast_time = based_on + pd.Timedelta(hours=24)

    return {
        "based_on_datetime": based_on.isoformat(),
        "forecast_datetime": forecast_time.isoformat(),
        "predicted_aqi": round(pred, 1),
    }