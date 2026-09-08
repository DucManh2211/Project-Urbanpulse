from pathlib import Path
import pandas as pd

from prophet import Prophet

from sklearn.metrics import mean_absolute_error
from sklearn.metrics import mean_squared_error

import mlflow
import mlflow.prophet


# =====================================================
# PATH
# =====================================================

BASE_DIR = Path(__file__).resolve().parents[2]

DATA_DIR = BASE_DIR / "data" / "processed"
FORECAST_DIR = BASE_DIR / "data" / "forecast"

FORECAST_DIR.mkdir(parents=True, exist_ok=True)

# =====================================================
# MLFLOW
# =====================================================

mlflow.set_tracking_uri(
    f"sqlite:///{BASE_DIR/'mlflow.db'}"
)

mlflow.set_experiment(
    "UrbanPulse_AQI_Forecast"
)

# =====================================================
# LOAD DATA
# =====================================================

files = sorted(DATA_DIR.glob("processed*.csv"))

if len(files) == 0:
    raise FileNotFoundError("Không tìm thấy dữ liệu processed.")

latest_file = files[-1]

print(f"Using dataset: {latest_file.name}")

df = pd.read_csv(latest_file)

df["datetime"] = pd.to_datetime(df["datetime"])

# =====================================================
# TRAIN / TEST
# =====================================================

split_date = pd.Timestamp("2026-07-10")

train = (
    df[df["datetime"] <= split_date]
    [["datetime", "european_aqi"]]
    .rename(
        columns={
            "datetime": "ds",
            "european_aqi": "y"
        }
    )
)

test = (
    df[df["datetime"] > split_date]
    [["datetime", "european_aqi"]]
    .rename(
        columns={
            "datetime": "ds",
            "european_aqi": "y"
        }
    )
)

# =====================================================
# PARAMETER
# =====================================================

configs = [

    (0.05, "additive"),

    (0.50, "additive"),

    (0.05, "multiplicative"),

    (0.50, "multiplicative")

]

results = []

best_rmse = float("inf")

best_forecast = None

# =====================================================
# TRAIN
# =====================================================

for cps, seasonality in configs:

    print("=" * 60)

    print(f"Training Prophet")

    print(f"CPS = {cps}")

    print(f"Seasonality = {seasonality}")

    with mlflow.start_run(
            run_name=f"Prophet_{cps}_{seasonality}"
    ):

        model = Prophet(

            changepoint_prior_scale=cps,

            seasonality_mode=seasonality

        )

        model.fit(train)

        forecast = model.predict(
            test[["ds"]]
        )

        mae = mean_absolute_error(

            test["y"],

            forecast["yhat"]

        )

        rmse = (

            mean_squared_error(

                test["y"],

                forecast["yhat"]

            ) ** 0.5

        )

        print(f"MAE  = {mae:.2f}")

        print(f"RMSE = {rmse:.2f}")

        # --------------------------
        # Log Parameter
        # --------------------------

        mlflow.log_param(
            "model",
            "Prophet"
        )

        mlflow.log_param(
            "changepoint_prior_scale",
            cps
        )

        mlflow.log_param(
            "seasonality_mode",
            seasonality
        )

        mlflow.log_param(
            "train_end",
            str(split_date.date())
        )

        # --------------------------
        # Log Metric
        # --------------------------

        mlflow.log_metric(
            "MAE",
            mae
        )

        mlflow.log_metric(
            "RMSE",
            rmse
        )

        # --------------------------
        # Save Model
        # --------------------------

        mlflow.prophet.log_model(

            model,

            artifact_path="model"

        )

        # --------------------------
        # Save Forecast
        # --------------------------

        forecast_save = forecast.copy()

        forecast_save["Actual"] = test["y"].values

        csv_name = f"forecast_{cps}_{seasonality}.csv"

        csv_path = FORECAST_DIR / csv_name

        forecast_save.to_csv(

            csv_path,

            index=False

        )

        mlflow.log_artifact(

            str(csv_path),

            artifact_path="forecast"

        )

        results.append({

            "changepoint_prior_scale": cps,

            "seasonality_mode": seasonality,

            "MAE": mae,

            "RMSE": rmse

        })

        if rmse < best_rmse:

            best_rmse = rmse

            best_forecast = forecast_save

# =====================================================
# RESULT
# =====================================================

result = pd.DataFrame(results)

result = result.sort_values("RMSE")

print()

print("=" * 60)

print(result)

print("=" * 60)

result.to_csv(

    FORECAST_DIR / "prophet_result.csv",

    index=False

)

best_forecast.to_csv(

    FORECAST_DIR / "best_prophet_prediction.csv",

    index=False

)

print()

print("Best RMSE :", best_rmse)

print("Done.")