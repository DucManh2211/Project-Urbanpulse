"""
forecast_router.py — Endpoint /aqi/forecast, /aqi/history

GET  /aqi/forecast        : lấy 168 giờ gần nhất từ DB, gọi forecast_service dự báo
POST /aqi/history         : ghi 1 điểm dữ liệu AQI+thời tiết mới vào DB
                             (dùng để "nạp" dữ liệu lịch sử, thay cho schedule_collect_df.py
                             chỉ lưu CSV như trước)
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session
from pydantic import BaseModel
import pandas as pd

from src.api.database import get_db, AQIHistory
from src.forecast.forecast_service import predict_forecast_24h, MIN_HISTORY_HOURS

router = APIRouter()


class AQIHistoryCreate(BaseModel):
    datetime: datetime
    european_aqi: float
    temperature_2m: float
    relative_humidity_2m: float
    wind_speed_10m: float
    precipitation: float


@router.post("/aqi/history", status_code=201)
def add_history_point(payload: AQIHistoryCreate, db: Session = Depends(get_db)):
    existing = db.query(AQIHistory).filter(AQIHistory.datetime == payload.datetime).first()
    if existing:
        raise HTTPException(409, "Đã có dữ liệu cho thời điểm này")

    record = AQIHistory(**payload.dict())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/aqi/forecast")
def get_forecast(db: Session = Depends(get_db)):
    rows = (
        db.query(AQIHistory)
        .order_by(desc(AQIHistory.datetime))
        .limit(MIN_HISTORY_HOURS)
        .all()
    )

    if len(rows) < MIN_HISTORY_HOURS:
        raise HTTPException(
            400,
            f"Chỉ có {len(rows)}/{MIN_HISTORY_HOURS} giờ lịch sử trong database. "
            f"Cần nạp thêm dữ liệu qua POST /aqi/history trước khi dự báo được.",
        )

    df = pd.DataFrame([{
        "datetime": r.datetime,
        "european_aqi": r.european_aqi,
        "temperature_2m": r.temperature_2m,
        "relative_humidity_2m": r.relative_humidity_2m,
        "wind_speed_10m": r.wind_speed_10m,
        "precipitation": r.precipitation,
    } for r in rows])

    try:
        result = predict_forecast_24h(df)
    except (ValueError, KeyError) as e:
        raise HTTPException(400, str(e))

    return result
