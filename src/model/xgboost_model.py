import os
os.environ["MLFLOW_ALLOW_FILE_STORE"] = "true"

import sys
from pathlib import Path
from datetime import timedelta

import pandas as pd
import xgboost as xgb
import mlflow
import mlflow.sklearn
from sklearn.metrics import mean_absolute_error, mean_squared_error

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DATA_DIR = PROJECT_ROOT / "data"
PROCESSED_DIR = DATA_DIR / "processed"
MODEL_DIR = DATA_DIR / "model"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

mlflow.set_tracking_uri(f"file://{PROJECT_ROOT}/mlruns")
mlflow.set_experiment("UrbanPulse_AQI_Forecast")

TEST_DAYS = 14
TARGET_HORIZON = 24  # dự báo AQI 6 giờ tới

FEATURE_COLS = [
    "hour", "dayofweek", "month", "isweekend",
    "aqi_lag_1", "aqi_lag_24", "aqi_lag_168",
    "rolling_mean_24", "rolling_std_24",
    "temperature_2m", "relative_humidity_2m", "wind_speed_10m", "precipitation",
]


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


def build_target(df, horizon=TARGET_HORIZON):
    df = df.copy()
    df["target"] = df["european_aqi"].shift(-horizon)
    df = df.dropna(subset=["target"]).reset_index(drop=True)
    return df


def train_test_split_by_date(df, test_days=TEST_DAYS):
    split_date = df["datetime"].max() - timedelta(days=test_days)
    train = df[df["datetime"] <= split_date]
    test = df[df["datetime"] > split_date]
    print(f"Split date: {split_date} | Train: {len(train)} dòng | Test: {len(test)} dòng")
    return train, test


def main():
    data = load_latest_processed()
    data = build_target(data)

    missing_cols = [c for c in FEATURE_COLS if c not in data.columns]
    if missing_cols:
        raise KeyError(f"Thiếu cột feature trong processed data: {missing_cols}")

    train, test = train_test_split_by_date(data)

    X_train, y_train = train[FEATURE_COLS], train["target"]
    X_test, y_test = test[FEATURE_COLS], test["target"]

    # ---- Naive baseline: "target = giá trị AQI hiện tại" ----
    naive_pred = test["european_aqi"]
    naive_mae = mean_absolute_error(y_test, naive_pred)
    naive_rmse = mean_squared_error(y_test, naive_pred) ** 0.5

    with mlflow.start_run(run_name=f"Naive_Baseline_target{TARGET_HORIZON}h"):
        mlflow.log_param("model_type", "Naive Baseline")
        mlflow.log_param("target_horizon_hours", TARGET_HORIZON)
        mlflow.log_param("test_days", TEST_DAYS)
        mlflow.log_metric("MAE", naive_mae)
        mlflow.log_metric("RMSE", naive_rmse)
    print(f"[Naive] MAE={naive_mae:.2f}, RMSE={naive_rmse:.2f}")

    # ---- XGBoost ----
    params = {"max_depth": 5, "learning_rate": 0.03, "n_estimators": 500}

    model = xgb.XGBRegressor(
        base_score=0.5,
        booster="gbtree",
        objective="reg:squarederror",
        early_stopping_rounds=50,
        random_state=42,
        **params,
    )
    model.fit(
        X_train, y_train,
        eval_set=[(X_train, y_train), (X_test, y_test)],
        verbose=100,
    )
    preds = model.predict(X_test)

    mae = mean_absolute_error(y_test, preds)
    rmse = mean_squared_error(y_test, preds) ** 0.5
    print(f"\n[XGBoost] MAE={mae:.2f}, RMSE={rmse:.2f}")
    print(f"So với Naive (RMSE={naive_rmse:.2f}): {'THẮNG' if rmse < naive_rmse else 'THUA'}")

    importance = pd.Series(model.feature_importances_, index=FEATURE_COLS).sort_values(ascending=False)
    print("\n=== FEATURE IMPORTANCE ===")
    print(importance)

    with mlflow.start_run(run_name=f"XGBoost_target{TARGET_HORIZON}h_depth{params['max_depth']}_lr{params['learning_rate']}"):
        mlflow.log_param("model_type", "XGBoost")
        mlflow.log_param("target_horizon_hours", TARGET_HORIZON)
        mlflow.log_param("test_days", TEST_DAYS)
        for k, v in params.items():
            mlflow.log_param(k, v)
        mlflow.log_param("features", ",".join(FEATURE_COLS))

        mlflow.log_metric("MAE", mae)
        mlflow.log_metric("RMSE", rmse)
        for feat, score in importance.items():
            mlflow.log_metric(f"importance_{feat}", score)

        mlflow.sklearn.log_model(model, "xgb_model")

    model_path = MODEL_DIR / "xgboost_model.json"
    model.save_model(model_path)
    print(f"Đã lưu model: {model_path}")


if __name__ == "__main__":
    main()