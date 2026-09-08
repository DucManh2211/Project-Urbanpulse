"""
main.py — Điểm khởi động chính của UrbanPulse API.

Chạy từ THƯ MỤC GỐC của project (nơi có thư mục src/):
    uvicorn src.api.main:app --reload
"""

from fastapi import FastAPI

from src.api.routers import forecast_router, route_router, risk_router, station_router

app = FastAPI(title="UrbanPulse API", version="1.0")

app.include_router(forecast_router.router, tags=["Forecast"])
app.include_router(route_router.router, tags=["Route"])
app.include_router(risk_router.router, tags=["Risk"])
app.include_router(station_router.router, tags=["Stations"])


@app.get("/")
async def root():
    return {"status": "UrbanPulse API đang hoạt động", "docs": "/docs"}
