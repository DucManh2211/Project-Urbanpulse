"""
database.py — Tầng kết nối PostgreSQL cho toàn bộ API Tháng 2.

Có 2 bảng:
- AQIHistory: lưu dữ liệu AQI+thời tiết theo giờ, dùng làm NGUỒN LỊCH SỬ
  để forecast_service tính lag/rolling feature khi gọi /aqi/forecast.
- Station: bảng trạm đo (đúng như bạn đã làm ở Tuần 8, giữ nguyên schema gốc).
"""

import os
from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://hoangducmanh@127.0.0.1:5432/urbanpulse"  # fallback khi chạy local
)

engine = create_engine(DATABASE_URL)
Base = declarative_base()


class AQIHistory(Base):
    __tablename__ = "aqi_history"

    id = Column(Integer, primary_key=True)
    datetime = Column(DateTime, unique=True, index=True)  # unique: tránh trùng giờ
    european_aqi = Column(Float)
    temperature_2m = Column(Float)
    relative_humidity_2m = Column(Float)
    wind_speed_10m = Column(Float)
    precipitation = Column(Float)


class Station(Base):
    __tablename__ = "stations"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    city = Column(String)
    aqi = Column(Integer)
    status = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)


Base.metadata.create_all(engine)

SessionLocal = sessionmaker(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
