"""
station_router.py — CRUD trạm đo, NÂNG CẤP từ bản list Python (Tuần 8 gốc)
sang dùng PostgreSQL thật qua SQLAlchemy — dữ liệu giờ sống sót qua restart.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.api.database import get_db, Station
from src.api.schemas import StationCreate, StationUpdate, StationResponse, StationStatistics

router = APIRouter()


def write_aqi_status(n: int) -> str:
    if 0 <= n <= 50:
        return "Good"
    elif n <= 100:
        return "Moderate"
    elif n <= 150:
        return "Unhealthy for Sensitive Groups"
    elif n <= 200:
        return "Unhealthy"
    elif n <= 300:
        return "Very Unhealthy"
    else:
        return "Hazardous"


@router.get("/stations/search", response_model=list[StationResponse])
def search_stations(
    city: Optional[str] = Query(None, description="Tên thành phố cần tìm"),
    min_aqi: Optional[int] = Query(None, ge=0),
    max_aqi: Optional[int] = Query(None, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(Station)
    if city is not None:
        query = query.filter(Station.city == city)
    if min_aqi is not None:
        query = query.filter(Station.aqi >= min_aqi)
    if max_aqi is not None:
        query = query.filter(Station.aqi <= max_aqi)
    return query.all()


# QUAN TRỌNG: route cụ thể (/statistic, /search) PHẢI đứng TRƯỚC /{station_id}
# — đúng bug bạn đã tự debug thành công ở Ngày 46, giữ đúng thứ tự này.
@router.get("/stations/statistic", response_model=StationStatistics)
def station_statistic(db: Session = Depends(get_db)):
    stations = db.query(Station).all()
    if not stations:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Chưa có trạm nào trong database")

    aqis = [s.aqi for s in stations]
    return {
        "total_stations": len(stations),
        "average_aqi": sum(aqis) / len(aqis),
        "max_aqi": max(aqis),
        "min_aqi": min(aqis),
    }


@router.get("/stations", response_model=list[StationResponse])
def get_stations(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    if skip < 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="skip must be >= 0")
    if limit <= 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="limit must be > 0")
    return db.query(Station).offset(skip).limit(limit).all()


@router.get("/stations/{station_id}", response_model=StationResponse)
def get_station_by_id(station_id: int, db: Session = Depends(get_db)):
    station = db.query(Station).filter(Station.id == station_id).first()
    if station is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="station_id not found")
    return station


@router.post("/stations", response_model=StationResponse, status_code=status.HTTP_201_CREATED)
def create_station(new: StationCreate, db: Session = Depends(get_db)):
    station = Station(
        name=new.name,
        city=new.city,
        aqi=new.aqi,
        status=write_aqi_status(new.aqi),
        latitude=new.latitude,
        longitude=new.longitude,
    )
    db.add(station)
    db.commit()
    db.refresh(station)  # lấy lại id vừa được database tự sinh (auto-increment)
    return station


@router.put("/stations/{station_id}", response_model=StationResponse)
def update_station(station_id: int, new: StationUpdate, db: Session = Depends(get_db)):
    station = db.query(Station).filter(Station.id == station_id).first()
    if station is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="station_id not found")

    if new.name is not None:
        station.name = new.name
    if new.city is not None:
        station.city = new.city
    if new.latitude is not None:
        station.latitude = new.latitude
    if new.longitude is not None:
        station.longitude = new.longitude
    if new.aqi is not None:
        station.aqi = new.aqi
        station.status = write_aqi_status(new.aqi)

    db.commit()
    db.refresh(station)
    return station


@router.delete("/stations/{station_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_station(station_id: int, db: Session = Depends(get_db)):
    station = db.query(Station).filter(Station.id == station_id).first()
    if station is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="station_id not found")
    db.delete(station)
    db.commit()
