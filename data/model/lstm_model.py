import os
os.environ["MLFLOW_ALLOW_FILE_STORE"] = "true"

import sys
from pathlib import Path
from datetime import timedelta

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import mlflow
from sklearn.preprocessing import MinMaxScaler
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
WINDOW_SIZE = 24
VAL_RATIO = 0.2
HIDDEN_SIZE = 32
NUM_LAYERS = 1
LR = 0.001
N_EPOCHS = 50


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


def create_sliding_window(series, window_size):
    X, y = [], []
    for i in range(len(series) - window_size):
        X.append(series[i: i + window_size])
        y.append(series[i + window_size])
    return np.array(X), np.array(y)


class LSTMModel(nn.Module):
    def __init__(self, input_size=1, hidden_size=32, num_layers=1):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=input_size, hidden_size=hidden_size,
            num_layers=num_layers, batch_first=True
        )
        self.linear = nn.Linear(hidden_size, 1)

    def forward(self, x):
        out, (hn, cn) = self.lstm(x)
        out = out[:, -1, :]
        out = self.linear(out)
        return out


def main():
    df = load_latest_processed()
    df_train, df_test = train_test_split_by_date(df)

    scaler = MinMaxScaler(feature_range=(0, 1))
    scaled_train = scaler.fit_transform(df_train[["european_aqi"]].values)
    scaled_test = scaler.transform(df_test[["european_aqi"]].values)

    X_train_full, y_train_full = create_sliding_window(scaled_train.flatten(), WINDOW_SIZE)
    X_test, y_test = create_sliding_window(scaled_test.flatten(), WINDOW_SIZE)

    X_train_full_t = torch.tensor(X_train_full.reshape(-1, WINDOW_SIZE, 1)).float()
    X_test_t = torch.tensor(X_test.reshape(-1, WINDOW_SIZE, 1)).float()
    y_train_full_t = torch.tensor(y_train_full).float().reshape(-1, 1)
    y_test_t = torch.tensor(y_test).float().reshape(-1, 1)

    val_size = int(len(X_train_full_t) * VAL_RATIO)
    X_train_t = X_train_full_t[:-val_size]
    y_train_t = y_train_full_t[:-val_size]
    X_val_t = X_train_full_t[-val_size:]
    y_val_t = y_train_full_t[-val_size:]

    print(f"Train: {X_train_t.shape[0]} | Val: {X_val_t.shape[0]} | Test: {X_test_t.shape[0]}")

    # ---- Naive baseline (cùng horizon 1h để so sánh loss scale, tham khảo) ----
    naive_pred_scaled = scaled_test.flatten()[WINDOW_SIZE - 1: -1]
    naive_actual = scaler.inverse_transform(naive_pred_scaled.reshape(-1, 1))
    y_test_actual_ref = scaler.inverse_transform(y_test_t.numpy().reshape(-1, 1))
    # đảm bảo cùng độ dài để so sánh
    min_len = min(len(naive_actual), len(y_test_actual_ref))
    naive_mae = mean_absolute_error(y_test_actual_ref[:min_len], naive_actual[:min_len])
    naive_rmse = mean_squared_error(y_test_actual_ref[:min_len], naive_actual[:min_len]) ** 0.5
    print(f"[Naive 1h] MAE={naive_mae:.2f}, RMSE={naive_rmse:.2f}")

    model = LSTMModel(input_size=1, hidden_size=HIDDEN_SIZE, num_layers=NUM_LAYERS)
    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=LR)

    best_val_loss = float("inf")
    best_model_state = None
    best_epoch = -1

    with mlflow.start_run(run_name=f"LSTM_window{WINDOW_SIZE}_hidden{HIDDEN_SIZE}"):
        mlflow.log_param("model_type", "LSTM")
        mlflow.log_param("window_size", WINDOW_SIZE)
        mlflow.log_param("hidden_size", HIDDEN_SIZE)
        mlflow.log_param("num_layers", NUM_LAYERS)
        mlflow.log_param("learning_rate", LR)
        mlflow.log_param("n_epochs", N_EPOCHS)
        mlflow.log_param("val_split_ratio", VAL_RATIO)
        mlflow.log_param("test_days", TEST_DAYS)

        for epoch in range(N_EPOCHS):
            model.train()
            optimizer.zero_grad()
            y_pred = model(X_train_t)
            loss = criterion(y_pred, y_train_t)
            loss.backward()
            optimizer.step()

            model.eval()
            with torch.no_grad():
                val_pred = model(X_val_t)
                val_loss = criterion(val_pred, y_val_t).item()

            mlflow.log_metric("train_loss", loss.item(), step=epoch)
            mlflow.log_metric("val_loss", val_loss, step=epoch)

            if val_loss < best_val_loss:
                best_val_loss = val_loss
                best_model_state = model.state_dict()
                best_epoch = epoch

            if epoch % 10 == 0:
                print(f"Epoch {epoch}: train_loss={loss.item():.4f}, val_loss={val_loss:.4f}")

        print(f"\n>>> Model tốt nhất ở epoch {best_epoch}, val_loss={best_val_loss:.4f}")
        model.load_state_dict(best_model_state)

        model.eval()
        with torch.no_grad():
            pred_scaled = model(X_test_t).numpy()

        pred_actual = scaler.inverse_transform(pred_scaled)
        y_test_actual = scaler.inverse_transform(y_test_t.numpy().reshape(-1, 1))

        mae = mean_absolute_error(y_test_actual, pred_actual)
        rmse = mean_squared_error(y_test_actual, pred_actual) ** 0.5

        print(f"\n=== KẾT QUẢ CUỐI CÙNG (test, đánh giá 1 lần) ===")
        print(f"LSTM MAE={mae:.2f}, RMSE={rmse:.2f}")
        print(f"So với Naive (RMSE={naive_rmse:.2f}): {'THẮNG' if rmse < naive_rmse else 'THUA'}")

        mlflow.log_param("best_epoch", best_epoch)
        mlflow.log_metric("best_val_loss", best_val_loss)
        mlflow.log_metric("MAE", mae)
        mlflow.log_metric("RMSE", rmse)

        model_path = MODEL_DIR / "lstm_model_weights.pth"
        torch.save(model.state_dict(), model_path)
        mlflow.log_artifact(str(model_path))
        print(f"Đã lưu model: {model_path}")


if __name__ == "__main__":
    main()
