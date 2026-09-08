"""
route_router.py — Endpoint POST /route/clean

Lấy toàn bộ trạm AQI hiện có trong database (bảng Station) làm dữ liệu
nội suy IDW, sau đó tìm đường sạch nhất giữa 2 điểm.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session
import pandas as pd

from src.api.database import get_db, Station, AQIHistory
from src.api.schemas import RouteRequest, RouteResponse, RouteSafeResponse, ForecastInfo, RiskInfo
from src.routing.route_service import find_clean_route
from src.forecast.forecast_service import predict_forecast_24h, MIN_HISTORY_HOURS
from src.risk.risk_service import classify_risk

router = APIRouter()


@router.post("/route/clean", response_model=RouteResponse)
def get_clean_route(req: RouteRequest, db: Session = Depends(get_db)):
    stations_db = db.query(Station).all()
    if not stations_db:
        raise HTTPException(
            400,
            "Chưa có trạm AQI nào trong database — cần POST /stations trước "
            "để có dữ liệu nội suy IDW cho tuyến đường.",
        )

    stations = [{"lat": s.latitude, "lon": s.longitude, "aqi": s.aqi} for s in stations_db]

    try:
        result = find_clean_route(
            start_lat=req.start_lat, start_lon=req.start_lon,
            end_lat=req.end_lat, end_lon=req.end_lon,
            stations=stations, place=req.place,
        )
    except Exception as e:
        raise HTTPException(500, f"Lỗi khi tính route: {e}")

    return result


@router.post("/route/safe", response_model=RouteSafeResponse)
def get_safe_route(req: RouteRequest, db: Session = Depends(get_db)):
    warnings: list[str] = []

    # ---- 1. ROUTE (bắt buộc) — tái sử dụng đúng logic /route/clean ----
    stations_db = db.query(Station).all()
    if not stations_db:
        raise HTTPException(
            400,
            "Chưa có trạm AQI nào trong database — cần POST /stations trước "
            "để có dữ liệu nội suy IDW cho tuyến đường.",
        )
    stations = [{"lat": s.latitude, "lon": s.longitude, "aqi": s.aqi} for s in stations_db]

    try:
        route_result = find_clean_route(
            start_lat=req.start_lat, start_lon=req.start_lon,
            end_lat=req.end_lat, end_lon=req.end_lon,
            stations=stations, place=req.place,
        )
    except Exception as e:
        # Route là phần lõi — lỗi ở đây thì trả lỗi thẳng, không "che giấu"
        raise HTTPException(500, f"Lỗi khi tính route: {e}")

    # ---- 2. FORECAST (không bắt buộc — degrade gracefully nếu thiếu dữ liệu) ----
    forecast_info = None
    try:
        rows = (
            db.query(AQIHistory)
            .order_by(desc(AQIHistory.datetime))
            .limit(MIN_HISTORY_HOURS)
            .all()
        )
        if len(rows) < MIN_HISTORY_HOURS:
            warnings.append(
                f"Không đủ {MIN_HISTORY_HOURS} giờ lịch sử để dự báo AQI "
                f"(hiện có {len(rows)}) — bỏ qua phần forecast."
            )
        else:
            df = pd.DataFrame([{
                "datetime": r.datetime, "european_aqi": r.european_aqi,
                "temperature_2m": r.temperature_2m,
                "relative_humidity_2m": r.relative_humidity_2m,
                "wind_speed_10m": r.wind_speed_10m,
                "precipitation": r.precipitation,
            } for r in rows])
            forecast_result = predict_forecast_24h(df)
            forecast_info = ForecastInfo(**forecast_result)
    except Exception as e:
        warnings.append(f"Không thể tính forecast: {e}")

    # ---- 3. RISK (không bắt buộc — chỉ chạy nếu forecast đã có) ----
    risk_info = None
    if forecast_info is not None:
        try:
            latest_row = db.query(AQIHistory).order_by(desc(AQIHistory.datetime)).first()
            risk_result = classify_risk(
                aqi=forecast_info.predicted_aqi,
                hour=datetime.now().hour,
                temperature=latest_row.temperature_2m if latest_row else 25.0,
                humidity=latest_row.relative_humidity_2m if latest_row else 60.0,
                user_group=req.user_group,
            )
            risk_info = RiskInfo(**risk_result)
        except Exception as e:
            warnings.append(f"Không thể phân loại rủi ro: {e}")
    else:
        warnings.append("Bỏ qua phân loại rủi ro vì chưa có forecast.")

    return RouteSafeResponse(
        route=RouteResponse(**route_result),
        forecast=forecast_info,
        risk=risk_info,
        warnings=warnings,
    )
