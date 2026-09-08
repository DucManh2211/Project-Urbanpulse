import os
os.environ["MLFLOW_ALLOW_FILE_STORE"] = "true"

import sys
from pathlib import Path
from datetime import timedelta

import pandas as pd
import mlflow
from prophet import Prophet
from sklearn.metrics import mean_absolute_error, mean_squared_error

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DATA_DIR = PROJECT_ROOT / "data"
PROCESSED_DIR = DATA_DIR / "processed"
FORECAST_DIR = DATA_DIR / "forecast"
FORECAST_DIR.mkdir(parents=True, exist_ok=True)

mlflow.set_tracking_uri(f"file://{PROJECT_ROOT}/mlruns")
mlflow.set_experiment("UrbanPulse_AQI_Forecast")

TEST_DAYS = 14  # dùng 14 ngày cuối làm test, phần còn lại làm train


def load_latest_processed():
    files = sorted(PROCESSED_DIR.glob("processed_*.csv"))
    if not files:
        raise FileNotFoundError("Không tìm thấy file processed_*.csv trong data/processed")
    latest = files[-1]
    print(f"Đang đọc: {latest.name}")
    df = pd.read_csv(latest)
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.sort_values("datetime").reset_index(drop=True)
    return df


def train_test_split_by_date(df, test_days=TEST_DAYS):
    split_date = df["datetime"].max() - timedelta(days=test_days)
    train = df[df["datetime"] <= split_date]
    test = df[df["datetime"] > split_date]
    print(f"Split date: {split_date} | Train: {len(train)} dòng | Test: {len(test)} dòng")
    return train, test


def run_prophet(df_train, df_test, cps, seasonality):
    model = Prophet(changepoint_prior_scale=cps, seasonality_mode=seasonality)
    model.fit(df_train)
    forecast = model.predict(df_test[["ds"]])

    mae = mean_absolute_error(df_test["y"], forecast["yhat"])
    rmse = mean_squared_error(df_test["y"], forecast["yhat"]) ** 0.5
    return mae, rmse, model, forecast


def main():
    data = load_latest_processed()
    train, test = train_test_split_by_date(data)

    df_train = train[["datetime", "european_aqi"]].rename(columns={"datetime": "ds", "european_aqi": "y"})
    df_test = test[["datetime", "european_aqi"]].rename(columns={"datetime": "ds", "european_aqi": "y"})

    # Naive baseline: "giữ nguyên giá trị AQI cuối tập train" cho toàn bộ đoạn test
    last_train_value = df_train["y"].iloc[-1]
    naive_pred = [last_train_value] * len(df_test)
    naive_mae = mean_absolute_error(df_test["y"], naive_pred)
    naive_rmse = mean_squared_error(df_test["y"], naive_pred) ** 0.5

    with mlflow.start_run(run_name="Naive_Baseline_Prophet_horizon"):
        mlflow.log_param("model_type", "Naive Baseline")
        mlflow.log_param("method", "giu gia tri cuoi train cho toan bo test")
        mlflow.log_param("test_days", TEST_DAYS)
        mlflow.log_metric("MAE", naive_mae)
        mlflow.log_metric("RMSE", naive_rmse)
    print(f"[Naive] MAE={naive_mae:.2f}, RMSE={naive_rmse:.2f}")

    configs = [
        (0.05, "additive"),
        (0.5, "additive"),
        (0.05, "multiplicative"),
        (0.5, "multiplicative"),
    ]

    results = []
    best_rmse = float("inf")
    best_forecast = None
    best_cfg = None

    for cps, seasonality in configs:
        mae, rmse, model, forecast = run_prophet(df_train, df_test, cps, seasonality)
        results.append({"cps": cps, "seasonality": seasonality, "MAE": mae, "RMSE": rmse})

        with mlflow.start_run(run_name=f"Prophet_cps{cps}_{seasonality}"):
            mlflow.log_param("model_type", "Prophet")
            mlflow.log_param("changepoint_prior_scale", cps)
            mlflow.log_param("seasonality_mode", seasonality)
            mlflow.log_param("test_days", TEST_DAYS)
            mlflow.log_metric("MAE", mae)
            mlflow.log_metric("RMSE", rmse)

        print(f"[Prophet] cps={cps}, seasonality={seasonality} -> MAE={mae:.2f}, RMSE={rmse:.2f}")

        if rmse < best_rmse:
            best_rmse = rmse
            best_forecast = forecast
            best_cfg = (cps, seasonality)

    df_results = pd.DataFrame(results).sort_values("RMSE")
    print("\n=== BẢNG SO SÁNH PROPHET ===")
    print(df_results.to_string(index=False))
    print(f"\nCấu hình tốt nhất: {best_cfg}, RMSE={best_rmse:.2f}")
    print(f"So với Naive (RMSE={naive_rmse:.2f}): {'THẮNG' if best_rmse < naive_rmse else 'THUA'}")

    forecast_path = FORECAST_DIR / "prophet_forecast.csv"
    best_forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]].to_csv(forecast_path, index=False)
    print(f"Đã lưu forecast: {forecast_path}")


if __name__ == "__main__":
    main()