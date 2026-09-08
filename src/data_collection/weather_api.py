import requests
import pandas as pd
def get_weather_data(
        latitude=21.028,
        longitude=105.834,
        start_date="2021-06-20",
        end_date="2026-07-20"
):
    url = "https://archive-api.open-meteo.com/v1/archive"

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "hourly":
            "temperature_2m,"
            "relative_humidity_2m,"
            "precipitation,"
            "wind_speed_10m",
        "timezone": "auto"
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    df = pd.DataFrame(response.json()["hourly"])
    return df
