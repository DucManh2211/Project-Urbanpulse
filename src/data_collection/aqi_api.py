import requests
import pandas as pd

def get_aqi_data(
        latitude=21.028,
        longitude=105.834,
        start_date="2021-06-20",
        end_date="2026-07-20"
):
    url = "https://air-quality-api.open-meteo.com/v1/air-quality"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "hourly":
            "european_aqi,"
            "pm10,"
            "pm2_5,"
            "carbon_monoxide,"
            "nitrogen_dioxide,"
            "ozone",
        "timezone": "auto"
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    df = pd.DataFrame(response.json()["hourly"])
    return df