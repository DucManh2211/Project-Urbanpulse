"""
schemas.py — Toàn bộ Pydantic schema dùng chung cho API Tháng 2.
Gộp Station (Tuần 8 gốc), Route (Tuần 6), Risk (Tuần 7) vào 1 file duy nhất
để dễ import, tránh rải rác nhiều file nhỏ.
"""

from pydantic import BaseModel, Field

class StationCreate(BaseModel):
    name: str
    city: str
    aqi: int = Field(ge=0, le=500)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class StationUpdate(BaseModel):
    name: str | None = None
    city: str | None = None
    aqi: int | None = Field(default=None, ge=0, le=500)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


class StationResponse(BaseModel):
    id: int
    name: str
    city: str
    aqi: int
    status: str
    latitude: float
    longitude: float

    class Config:
        from_attributes = True  # cho phép trả thẳng object SQLAlchemy, Pydantic tự đọc attribute


class StationStatistics(BaseModel):
    total_stations: int
    average_aqi: float
    max_aqi: int
    min_aqi: int

class RouteRequest(BaseModel):
    start_lat: float = Field(ge=-90, le=90)
    start_lon: float = Field(ge=-180, le=180)
    end_lat: float = Field(ge=-90, le=90)
    end_lon: float = Field(ge=-180, le=180)
    place: str = Field(
        default="Hoan Kiem, Hanoi, Vietnam",
        description="Khu vực để tải graph đường phố (osmnx). Vùng càng nhỏ, tải càng nhanh.",
    )
    user_group: str = Field(default="healthy", description="child, elderly, hoặc healthy")

class RouteResponse(BaseModel):
    short_distance_m: float
    clean_distance_m: float
    percent_longer: float
    node_count_short: int
    node_count_clean: int
    short_route_coords: list[list[float]]  # [[lat, lon], [lat, lon], ...] theo đúng thứ tự đi
    clean_route_coords: list[list[float]]

class RiskCheckRequest(BaseModel):
    aqi: float = Field(ge=0, le=500)
    hour: int = Field(ge=0, le=23)
    temperature: float
    humidity: float = Field(ge=0, le=100)
    user_group: str = Field(default="healthy", description="child, elderly, hoặc healthy")


class RiskCheckResponse(BaseModel):
    risk_level: str
    probabilities: dict[str, float]


class ForecastInfo(BaseModel):
    """Thông tin dự báo, lồng trong RouteSafeResponse."""
    based_on_datetime: str
    forecast_datetime: str
    predicted_aqi: float


class RiskInfo(BaseModel):
    """Thông tin phân loại rủi ro, lồng trong RouteSafeResponse."""
    risk_level: str
    probabilities: dict[str, float]


class RouteSafeResponse(BaseModel):
    route: RouteResponse
    forecast: ForecastInfo | None = None
    risk: RiskInfo | None = None
    warnings: list[str] = []