
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from pydantic import BaseModel

from app.database import get_db
from app.services.prediction_service import PredictionService
from app.security import get_current_user


router = APIRouter(
    tags=["predictive-maintenance"],
    responses={404: {"description": "Not found"}},
)

class ForecastRequest(BaseModel):
    equipment_id: int
    horizon_days: Optional[int] = 90

@router.post("/forecast", response_model=Dict[str, Any])
async def get_equipment_forecast(
    request: ForecastRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Generate AI Forecast for specific equipment.
    Returns RUL prediction, MTBF forecast, and downtime estimates.
    """
    try:
        result = PredictionService.get_full_forecast(db, request.equipment_id)
        if "error" in result:
             # If it's a data error, we still return the structure but with error details, 
             # likely handled by frontend. Or we could raise HTTPException.
             # Service returns dict with error key for graceful handling.
             pass
             
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
