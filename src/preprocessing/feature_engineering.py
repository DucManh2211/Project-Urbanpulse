import pandas as pd

def feature_data(df):
    df = df.copy()
    df["hour"] = df["datetime"].dt.hour
    df["dayofweek"] = df["datetime"].dt.dayofweek
    df["month"] = df["datetime"].dt.month
    df["isweekend"] = df["datetime"].dt.dayofweek >= 5
    df["aqi_lag_1"] = df["european_aqi"].shift(1)
    df["aqi_lag_24"] = df["european_aqi"].shift(24)
    df["aqi_lag_168"] = df["european_aqi"].shift(168)
    df["rolling_mean_3"] = (
        df["european_aqi"]
        .rolling(3)
        .mean()
    )
    df["rolling_mean_24"] = (
        df["european_aqi"]
        .rolling(24)
        .mean()
    )
    df["rolling_std_24"] = (
        df["european_aqi"]
        .rolling(24)
        .std()
    )
    df = df.dropna()
    return df
