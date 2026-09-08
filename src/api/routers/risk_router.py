"""
risk_router.py — Endpoint POST /risk/check
"""

from fastapi import APIRouter, HTTPException

from src.api.schemas import RiskCheckRequest, RiskCheckResponse
from src.risk.risk_service import classify_risk

router = APIRouter()


@router.post("/risk/check", response_model=RiskCheckResponse)
def check_risk(req: RiskCheckRequest):
    try:
        result = classify_risk(
            aqi=req.aqi, hour=req.hour, temperature=req.temperature,
            humidity=req.humidity, user_group=req.user_group,
        )
    except FileNotFoundError as e:
        raise HTTPException(500, str(e))
    return result
