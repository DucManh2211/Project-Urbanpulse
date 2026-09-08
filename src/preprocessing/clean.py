import pandas as pd

def check_data_quality(df):
    print("Missing value")
    print(df.isnull().sum())
    print()
    print("Duplicate")
    print(df.duplicated().sum())
    print()
    diff = df["datetime"].sort_values().diff()
    missing = diff[diff > pd.Timedelta(hours=1)]
    print("Missing timestamp")
    print(len(missing))

def process_data(df):
    df = df.copy()
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.sort_values("datetime")
    df = df.drop_duplicates()
    check_data_quality(df)
    return df